"""
AI-powered scoring engine using Groq LLM.
Calculates weighted fit scores across 4 dimensions and generates
explainable insights for recruiters.
"""
from __future__ import annotations

import json
import re
import time
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type

from app.services.resume_parser import QuotaExhaustedError

from app.services.knockout_engine import _skill_present

logger = structlog.get_logger()
SCORING_WEIGHTS = {
    "skills_match": 0.45,
    "experience_relevance": 0.30,
    "career_progression": 0.15,
    "measurable_achievements": 0.10,
}

SCORE_PROMPT = """
You are a senior technical recruiter scoring resumes with **SMART SKILL INFERENCE**.

═══ CORE PHILOSOPHY ═══
1. **ECOSYSTEM MATCHING**: LLM automatically infers related skills - NO HARDCODED LISTS
   - Parent tech present → child versions/tools = AUTO-MATCH (0.75+ confidence)
   - Examples (INFER SIMILAR): .NET→.NET Core/v10; Azure→ServiceBus/ADF; Angular→v18/Material
   
2. **PROTECT CORE MATCHES**: If mandatory skills + experience match → MINIMUM 75/100 baseline
3. **BONUS-ONLY DIMENSIONS**: Career/Achievements = pure upside, never penalize

═══ WEIGHTED SCORING ═══
CORE (75%): Skills_Match(45%) + Experience_Relevance(30%)
BONUS (25%): Career_Progression(15%) + Achievements(10%)

═══ SKILL MATCH RULES (LLM INFERENCE REQUIRED) ═══
1. **MANDATORY SKILLS** (JD-listed): Scan resume for EXACT or ECOSYSTEM matches
   - Found parent → infer children as matched (e.g., "Azure" matches "Azure Data Factory")
   - Use LLM semantic understanding across backend/frontend/cloud/DevOps stacks
   
2. **CONFIDENCE THRESHOLDS**:
   - Exact match: 1.0
   - Strong ecosystem (Angular→Material): 0.85  
   - Weak adjacency (React→Angular): 0.4
   - No relation: 0.0
   
3. **BASELINE PROTECTION**: 3+ mandatory skills OR strong experience → skills_match ≥75

═══ DIMENSION SCORING ═══
1. SKILLS_MATCH (0-100):
   - 80%+ mandatory skills matched → 85+
   - 50-79% matched → 70-84  
   - <50% → <70 (RARE if experience strong)
   
2. EXPERIENCE_RELEVANCE (0-100):
   - Years ≥ required → 80+
   - Relevant domain/role → +10-20 bonus
   
3. CAREER_PROGRESSION (Floor: 50):
   - Any progression → 60-90 (never <50)
   
4. ACHIEVEMENTS (Floor: 40):  
   - Any metrics → 50-90 (never <40)

═══ OUTPUT JSON (MUST BE VALID) ═══
{{
  "scores": {{
    "skills_match": <INT>,
    "experience_relevance": <INT>,
    "career_progression": <INT>,
    "measurable_achievements": <INT>
  }},
  "total_score": <weighted 0-100>,
  "skills_matched": [
    {{"jd_skill": "Azure", "resume_evidence": "Azure certified", "confidence": 0.95, "ecosystem_bonus": ["Data Factory inferred"]}}
  ],
  "skills_missing": [  // ONLY true gaps, never ecosystem
    {{"jd_skill": "X", "found_related": false}}
  ],
  "strengths": ["3 evidence-based positives"],
  "recommendation": "SHORTLIST / INTERVIEW / HOLD / REJECT",
  "reasoning": "2 sentences. Positive if core matches."
}}

JOB DESCRIPTION:
{jd_summary}

CANDIDATE RESUME: 
{resume_text}
"""


class ScoringEngine:
    """Score candidates using Groq LLM and compute the weighted fit score."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from groq import Groq
            from app.config import settings

            if not settings.GROQ_API_KEY:
                raise RuntimeError("GROQ_API_KEY not configured")
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_llm(self, prompt: str) -> dict:
        from app.config import settings
        response = self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_completion_tokens=2048,
        )
        text = response.choices[0].message.content
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise

    def score_candidate(
        self, parsed_resume: dict, parsed_jd: dict
    ) -> dict:
        """
        Score a single candidate against a JD.

        Returns a dict with all scoring fields ready to store in ScreeningResult.
        """
        start_ms = int(time.time() * 1000)

        # Build concise summaries to reduce token usage
        jd_summary = self._build_jd_summary(parsed_jd)
        resume_summary = self._build_resume_summary(parsed_resume)

        prompt = SCORE_PROMPT.format(
            jd_summary=jd_summary, resume_text=resume_summary
        )

        scoring_data = self._call_llm(prompt)

        raw_scores = scoring_data.get("scores", {})
        category_scores = {
            "skills_match": float(raw_scores.get("skills_match", 50)),
            "experience_relevance": float(raw_scores.get("experience_relevance", 50)),
            "career_progression": float(raw_scores.get("career_progression", 50)),
            "measurable_achievements": float(raw_scores.get("measurable_achievements", 50)),
        }

        fit_score = self._compute_weighted_score(category_scores)
        status = self._get_status(fit_score)
        elapsed_ms = int(time.time() * 1000) - start_ms

        # Map new prompt output fields → DB schema fields
        skills_matched = [
            {
                "required_skill": sm.get("jd_skill", ""),
                "candidate_skill": sm.get("resume_evidence", ""),
                "match_confidence": float(sm.get("confidence", 0.5)),
                "years_in_profile": 0,
                "ecosystem_bonus": sm.get("ecosystem_bonus", []),
            }
            for sm in scoring_data.get("skills_matched", [])
        ]
        skills_missing = [
            {
                "required_skill": sm.get("jd_skill", ""),
                "candidate_has": bool(sm.get("found_related", False)),
                "importance": "high",
            }
            for sm in scoring_data.get("skills_missing", [])
        ]

        # Derive weaknesses from missing skills (prompt doesn't return weaknesses)
        weaknesses = []
        if skills_missing:
            true_missing = [s["required_skill"] for s in skills_missing if not s["candidate_has"]]
            if true_missing:
                weaknesses.append(f"Would benefit from deeper exposure to: {', '.join(true_missing[:4])}")

        return {
            "fit_score": round(fit_score, 1),
            "status": status,
            "category_scores": category_scores,
            "strengths": scoring_data.get("strengths", []),
            "weaknesses": weaknesses,
            "skills_matched": skills_matched,
            "skills_missing": skills_missing,
            "match_explanation": scoring_data.get("reasoning", ""),
            "screening_time_ms": elapsed_ms,
        }

    # ─── Fallback Deterministic Scorer ────────────────────────────────────────

    def score_candidate_deterministic(
        self, parsed_resume: dict, parsed_jd: dict
    ) -> dict:
        """
        Lightweight deterministic scoring when LLM is unavailable.
        Uses keyword matching and heuristics.
        """
        start_ms = int(time.time() * 1000)

        # 1. Skills Match (40%)
        nice_to_have = parsed_jd.get("nice_to_have_skills", [])
        nice_lower_set = {s.lower() for s in nice_to_have}
        # Filter out nice-to-have from required skills to avoid penalizing candidates
        required_skills = [
            s["skill"] for s in parsed_jd.get("required_skills", [])
            if s["skill"].lower() not in nice_lower_set
        ]
        recent_skills_lower = {s.lower() for s in parsed_resume.get("recent_skills", [])}
        all_skills_lower = {s.lower() for s in parsed_resume.get("all_skills", [])}

        if required_skills:
            recent_matches = sum(
                1 for s in required_skills if _skill_present(s, recent_skills_lower)
            )
            all_matches = sum(
                1 for s in required_skills if _skill_present(s, all_skills_lower)
            )
            skills_match = min(100, (recent_matches / len(required_skills)) * 75
                                    + (all_matches / len(required_skills)) * 25)
            # Bonus for nice-to-have skills
            if nice_to_have:
                nice_matches = sum(1 for s in nice_to_have if _skill_present(s, all_skills_lower))
                skills_match = min(100, skills_match + (nice_matches / len(nice_to_have)) * 10)
        else:
            # No required skills: score based on total skill count (more skills = better)
            total_skills = len(all_skills_lower)
            skills_match = min(80, 30 + total_skills * 5)

        # 2. Experience Relevance (25%)
        required_exp = parsed_jd.get("required_min_exp_years", 0) or 0
        candidate_exp = parsed_resume.get("total_exp_years", 0) or 0
        if required_exp > 0:
            exp_ratio = min(candidate_exp / required_exp, 1.5)
            experience_relevance = min(100, exp_ratio * 70)
        else:
            # No requirement: score based on candidate experience (more = better, diminishing)
            experience_relevance = min(90, 30 + candidate_exp * 6)

        # 3. Career Progression (15%) — BONUS dimension, floor at 50
        num_roles = len(parsed_resume.get("experience", []))
        if num_roles > 0:
            career_progression = min(100, 50 + num_roles * 10)
        else:
            career_progression = min(70, 30 + candidate_exp * 5)

        # 4. Achievements (10%) — BONUS dimension, floor at 40
        total_achievements = sum(
            len(e.get("achievements", []))
            for e in parsed_resume.get("experience", [])
        )
        if total_achievements > 0:
            achievements_score = min(100, 45 + total_achievements * 5)
        else:
            achievements_score = min(50, 30 + len(all_skills_lower) * 2)

        category_scores = {
            "skills_match": round(skills_match),
            "experience_relevance": round(experience_relevance),
            "career_progression": round(career_progression),
            "measurable_achievements": round(achievements_score),
        }
        fit_score = self._compute_weighted_score(category_scores)
        status = self._get_status(fit_score)

        # Build basic skills matched/missing lists
        skills_matched = [
            {
                "required_skill": s,
                "candidate_skill": s,
                "match_confidence": 0.9 if _skill_present(s, recent_skills_lower) else 0.6,
                "years_in_profile": candidate_exp,
            }
            for s in required_skills
            if _skill_present(s, all_skills_lower)
        ]
        skills_missing = [
            {"required_skill": s, "candidate_has": False, "importance": "high"}
            for s in required_skills
            if not _skill_present(s, all_skills_lower)
        ]

        # ── Build detailed strengths ──────────────────────────────────────
        strengths = []
        if skills_matched:
            matched_names = [s["required_skill"] for s in skills_matched]
            strengths.append(
                f"Matches {len(matched_names)} of {len(required_skills)} required skills: {', '.join(matched_names[:5])}"
            )
        if candidate_exp >= required_exp and required_exp > 0:
            strengths.append(
                f"Meets experience requirement with {candidate_exp} years (required: {required_exp})"
            )
        elif candidate_exp > 0:
            strengths.append(f"Brings {candidate_exp} years of professional experience")
        recent = list(parsed_resume.get("recent_skills", []))[:5]
        if recent:
            strengths.append(f"Recent hands-on experience with: {', '.join(recent)}")
        education = parsed_resume.get("education", [])
        if education:
            degrees = [e.get("degree", "") for e in education if e.get("degree")]
            if degrees:
                strengths.append(f"Educational background: {degrees[0]}")
        if num_roles >= 3:
            strengths.append(f"Demonstrated career progression across {num_roles} roles")

        # ── Build detailed weaknesses (JD-aware) ──────────────────────────
        weaknesses = []
        if skills_missing:
            missing_names = [s["required_skill"] for s in skills_missing[:4]]
            weaknesses.append(f"Missing required skills: {', '.join(missing_names)}")

        gaps = parsed_resume.get("employment_gaps", [])
        total_gap_months = sum(g.get("duration_months", 0) for g in gaps) if gaps else 0

        if required_exp > 0 and candidate_exp < required_exp:
            gap = round(required_exp - candidate_exp, 1)
            weakness_msg = (
                f"Experience gap: has {candidate_exp} years, "
                f"role requires {required_exp} ({gap} years short)"
            )
            # Combine employment gaps with experience shortfall for context
            if total_gap_months >= 6:
                weakness_msg += (
                    f"; {total_gap_months} months of employment gaps "
                    f"may further reduce effective experience"
                )
            weaknesses.append(weakness_msg)
        elif total_gap_months >= 12:
            # Only flag large employment gaps when candidate meets experience requirement
            weaknesses.append(
                f"Despite meeting experience requirement, has {total_gap_months} months "
                f"of employment gaps across {len(gaps)} period(s)"
            )

        if total_achievements == 0:
            weaknesses.append("No quantified achievements found in resume")

        # Build match explanation — tone MUST align with score
        matched_names = [s["required_skill"] for s in skills_matched]
        if fit_score >= 70:
            explanation_parts = [f"Strong candidate (score: {fit_score:.0f}/100)."]
            if matched_names:
                explanation_parts.append(
                    f"Covers {len(matched_names)} of {len(required_skills)} required skills including {', '.join(matched_names[:4])}."
                )
            if candidate_exp >= required_exp and required_exp > 0:
                explanation_parts.append(
                    f"Solid experience at {candidate_exp} years (required: {required_exp})."
                )
            elif candidate_exp > 0:
                explanation_parts.append(f"Brings {candidate_exp} years of relevant experience.")
            match_explanation = " ".join(explanation_parts)
        elif fit_score >= 50:
            explanation_parts = [f"Potential fit (score: {fit_score:.0f}/100)."]
            if matched_names:
                explanation_parts.append(
                    f"Matches {len(matched_names)} of {len(required_skills)} required skills ({', '.join(matched_names[:4])})."
                )
            if skills_missing:
                missing_names = [s["required_skill"] for s in skills_missing[:2]]
                explanation_parts.append(
                    f"Would benefit from deeper exposure to {', '.join(missing_names)}."
                )
            if candidate_exp > 0:
                explanation_parts.append(f"Has {candidate_exp} years of experience.")
            match_explanation = " ".join(explanation_parts)
        else:
            gap_parts = [f"Significant gaps identified (score: {fit_score:.0f}/100)."]
            if skills_missing:
                missing_names = [s["required_skill"] for s in skills_missing[:3]]
                gap_parts.append(f"Would need to develop: {', '.join(missing_names)}.")
            if required_exp > 0 and candidate_exp < required_exp:
                gap_parts.append(
                    f"Has {candidate_exp} years experience; role targets {required_exp} years."
                )
            match_explanation = " ".join(gap_parts)

        elapsed_ms = int(time.time() * 1000) - start_ms
        return {
            "fit_score": round(fit_score, 1),
            "status": status,
            "category_scores": category_scores,
            "strengths": strengths[:5],
            "weaknesses": weaknesses[:4],
            "skills_matched": skills_matched,
            "skills_missing": skills_missing,
            "match_explanation": match_explanation,
            "screening_time_ms": elapsed_ms,
        }

    # ─── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_weighted_score(scores: dict) -> float:
        return (
            scores["skills_match"] * SCORING_WEIGHTS["skills_match"]
            + scores["experience_relevance"] * SCORING_WEIGHTS["experience_relevance"]
            + scores["career_progression"] * SCORING_WEIGHTS["career_progression"]
            + scores["measurable_achievements"] * SCORING_WEIGHTS["measurable_achievements"]
        )

    @staticmethod
    def _get_status(score: float) -> str:
        if score >= 86:
            return "EXCELLENT"
        if score >= 61:
            return "GOOD"
        if score >= 31:
            return "ADEQUATE"
        return "POOR"

    @staticmethod
    def _build_jd_summary(jd: dict) -> str:
        # Separate required from nice-to-have to prevent scorer confusion
        nice_lower = {s.lower() for s in jd.get("nice_to_have_skills", [])}
        required_only = [
            s["skill"] for s in jd.get("required_skills", [])[:10]
            if s["skill"].lower() not in nice_lower
        ]
        nice_to_have = list(jd.get("nice_to_have_skills", [])[:8])
        top3 = jd.get("top_3_mandatory_skills", [])
        return (
            f"Title: {jd.get('job_title')}\n"
            f"Min Experience: {jd.get('required_min_exp_years')} years\n"
            f"REQUIRED Skills (must-have, evaluate strictly): {', '.join(required_only)}\n"
            f"Nice-to-have Skills (bonus only, do NOT penalize if missing): {', '.join(nice_to_have)}\n"
            f"Education: {jd.get('education_required', 'Not specified')}\n"
            f"Top 3 Non-Negotiable Skills: {', '.join(top3)}"
        )

    @staticmethod
    def _build_resume_summary(resume: dict) -> str:
        recent_skills = ", ".join(resume.get("recent_skills", [])[:15])
        exp_lines = "\n".join(
            f"- {e.get('title')} at {e.get('company')} ({e.get('duration_years', 0):.1f} yrs): "
            + ", ".join(e.get("achievements", [])[:2])
            for e in resume.get("experience", [])[:5]
        )
        return (
            f"Name: {resume.get('candidate_name')}\n"
            f"Total Experience: {resume.get('total_exp_years')} years\n"
            f"Recent Skills: {recent_skills}\n"
            f"Experience:\n{exp_lines}\n"
            f"Education: {'; '.join(e.get('degree', '') for e in resume.get('education', []))}"
        )


scoring_engine = ScoringEngine()
