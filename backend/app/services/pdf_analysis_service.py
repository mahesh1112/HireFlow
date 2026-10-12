"""
PDF Analysis Service — orchestrates AI-enriched analysis and deterministic
computations needed to populate the HireFlow candidate PDF report.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type

from app.services.resume_parser import QuotaExhaustedError

logger = structlog.get_logger()


# ─── Data container for the full PDF report ───────────────────────────────────

@dataclass
class PDFReportData:
    # Header / Hero
    candidate_name: str = "Unknown Candidate"
    job_title: str = ""
    current_title: str = ""
    location: str = "Not specified"
    years_of_experience: float = 0.0
    education_level: str = "Not specified"
    match_score: float = 0.0
    status: str = "POOR"

    # Executive Summary
    executive_summary: str = ""

    # Career Trajectory
    career_timeline: list[dict] = field(default_factory=list)  # [{year, title, company}]
    promotion_frequency: str = "N/A"
    career_breaks: str = "0 breaks, 0 months"
    cities_worked: str = ""

    # Tenure
    avg_tenure_overall: float = 0.0
    avg_tenure_last3: float = 0.0
    longest_tenure: float = 0.0

    # AI-enriched sections
    role_type_breakdown: dict = field(default_factory=lambda: {
        "Leadership": 0, "Individual Contributor": 0, "Management": 0
    })
    global_market_exposure: dict = field(default_factory=lambda: {
        "North America": 0, "EMEA": 0, "APAC": 0
    })
    company_type_breakdown: dict = field(default_factory=lambda: {
        "Enterprise": 50, "Mid Market": 50
    })
    industry_exposure: list[dict] = field(default_factory=list)  # [{industry, percentage}]
    key_achievements: list[str] = field(default_factory=list)
    skills_categorized: dict = field(default_factory=lambda: {
        "Strategic": [], "Technical": [], "Functional": [], "Leadership": []
    })
    technical_stack: dict = field(default_factory=dict)

    # Strengths / Weaknesses (from screening + AI)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    # Why Shortlist
    why_shortlist: str = ""
    verdict: str = "CONSIDER"

    # Analysis Score Cards
    analysis_scores: dict = field(default_factory=lambda: {
        "alignment": {"score": 50, "fitness": "Medium", "bullets": []},
        "divergence": {"score": 50, "fitness": "Medium", "bullets": []},
        "compatibility": {"score": 50, "fitness": "Medium", "bullets": []},
        "concerns": {"score": 50, "fitness": "Medium", "bullets": []},
    })

    # Screening category scores (for reference)
    skills_match_score: float = 0.0
    experience_relevance_score: float = 0.0
    career_progression_score: float = 0.0
    achievements_score: float = 0.0

    # Meta
    generated_date: str = field(default_factory=lambda: date.today().isoformat())


# ─── Analysis Prompt ──────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """You are a Recruitment Intelligence Agent for HireFlow.
Analyze the candidate's resume data against the job description and produce a
structured JSON analysis report. Be factual and evidence-based — every claim
must come from the resume.

═══ SCORE-TEXT CONSISTENCY (CRITICAL) ═══
The candidate already has a Fit Score of {fit_score}/100. Your analysis MUST align:
  - Fit >= 75: Positive tone throughout. Verdict = RECOMMEND or STRONGLY RECOMMEND.
    Emphasize strengths, frame gaps constructively ("would benefit from" not "lacks").
  - Fit 60-74: Balanced-positive tone. Verdict = RECOMMEND or CONSIDER.
    Acknowledge strengths first, then note gaps constructively.
  - Fit 40-59: Balanced tone. Verdict = CONSIDER.
    Fair assessment of both strengths and development areas.
  - Fit < 40: Identify gaps honestly but constructively. Verdict = PASS.
NEVER contradict the screening score with your tone. A 75+ candidate should NOT
have a mostly negative analysis. A 30-score candidate should NOT get glowing praise.

═══ SKILL MATCHING PHILOSOPHY ═══
Apply ecosystem/partial matching:
  - ".NET" covers ".NET 10.0", ".NET Core", ".NET Framework"
  - "Angular" covers "Angular 18", "Angular 14"
  - "C#" covers "C# 14", "C# 12"
  - "AWS" covers "AWS Lambda", "AWS S3" and vice-versa
  - "React" covers "React.js", "ReactJS"
  - "SQL" covers "T-SQL", "PL/SQL", "MySQL", "PostgreSQL"
When discussing skills, credit ecosystem familiarity. Use "partial match" or
"ecosystem experience" rather than "missing" when the candidate has related tech.

═══ CONSTRUCTIVE FRAMING ═══
Use: "ecosystem familiarity with X", "adjacent experience", "would benefit from deeper exposure to Y"
Avoid: "lacks", "no evidence", "fails to demonstrate", "missing critical skills"

CANDIDATE DATA:
{resume_json}

JOB DESCRIPTION:
Title: {job_title}
Requirements: {jd_full}
Required Skills: {required_skills}
Min Experience: {min_exp_years} years
Education Required: {education_required}

EXISTING SCREENING SCORES:
Fit Score: {fit_score}/100
Skills Match: {skills_match}/100 (weight: 45%)
Experience Relevance: {experience_relevance}/100 (weight: 30%)
Career Progression: {career_progression}/100 (weight: 15% — bonus)
Achievements: {achievements}/100 (weight: 10% — bonus)
Strengths: {strengths}
Weaknesses: {weaknesses}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "executive_summary": "2-3 factual sentences: who this candidate is, expertise area, years of experience, and value proposition. Tone MUST match the fit score.",
  "role_type_breakdown": {{
    "Leadership": <0-100 percentage of career in leadership roles>,
    "Individual Contributor": <0-100>,
    "Management": <0-100>
  }},
  "global_market_exposure": {{
    "North America": <0-100 based on client/project locations>,
    "EMEA": <0-100>,
    "APAC": <0-100>
  }},
  "company_type_breakdown": {{
    "Enterprise": <0-100>,
    "Mid Market": <0-100>
  }},
  "industry_exposure": [
    {{"industry": "string", "percentage": <number>}}
  ],
  "key_achievements": ["up to 5 quantified achievements from resume — include numbers/metrics"],
  "skills_categorized": {{
    "Strategic": ["high-level thinking, architecture, planning skills"],
    "Technical": ["tools, languages, frameworks, platforms"],
    "Functional": ["domain-specific or process-oriented skills"],
    "Leadership": ["people, team, communication skills"]
  }},
  "technical_stack": {{
    "Languages": ["Python", "Java"],
    "Cloud": ["AWS", "GCP"],
    "Frameworks": ["FastAPI", "React"],
    "Databases": ["PostgreSQL"],
    "DevOps": ["Docker", "Kubernetes"],
    "Other": ["Git"]
  }},
  "why_shortlist": "2-3 persuasive but honest sentences. For high scorers, be enthusiastic. For low scorers, note what partial value they bring.",
  "verdict": "STRONGLY RECOMMEND or RECOMMEND or CONSIDER or PASS — MUST match the fit score range above",
  "analysis_scores": {{
    "alignment": {{"score": <0-100>, "fitness": "High or Medium or Low", "bullets": ["3-4 plain-language explanations"]}},
    "divergence": {{"score": <0-100 lower is better>, "fitness": "High or Medium or Low", "bullets": ["3-4 explanations"]}},
    "compatibility": {{"score": <0-100>, "fitness": "High or Medium or Low", "bullets": ["3-4 explanations"]}},
    "concerns": {{"score": <0-100 lower is better>, "fitness": "High or Medium or Low", "bullets": ["3-4 explanations"]}}
  }}
}}
"""


class PDFAnalysisService:
    """Generates all data needed for the HireFlow candidate PDF report."""

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

    # ─── Main Entry Point ─────────────────────────────────────────────────

    def generate_report_data(
        self,
        screening_result: dict,
        parsed_data: dict,
        job_data: dict,
    ) -> PDFReportData:
        """
        Build a complete PDFReportData from screening result, resume parsed_data,
        and job description data.
        """
        report = PDFReportData()

        # ── Populate basic fields from screening result ───────────────
        report.candidate_name = screening_result.get("candidate_name") or parsed_data.get("candidate_name") or "Unknown Candidate"
        report.location = screening_result.get("candidate_location") or parsed_data.get("location") or "Not specified"
        report.years_of_experience = screening_result.get("total_exp_years") or parsed_data.get("total_exp_years") or 0
        report.match_score = screening_result.get("fit_score", 0)
        report.status = screening_result.get("status", "POOR")
        report.job_title = job_data.get("job_title", "")
        report.strengths = screening_result.get("strengths") or []
        report.weaknesses = screening_result.get("weaknesses") or []

        # Scores
        report.skills_match_score = screening_result.get("skills_match_score", 0)
        report.experience_relevance_score = screening_result.get("experience_relevance_score", 0)
        report.career_progression_score = screening_result.get("career_progression_score", 0)
        report.achievements_score = screening_result.get("achievements_score", 0)

        # ── Education level ───────────────────────────────────────────
        education = parsed_data.get("education", [])
        if education:
            degrees = [e.get("degree", "") for e in education if e.get("degree")]
            report.education_level = degrees[0] if degrees else "Not specified"
        else:
            report.education_level = "Not specified"

        # ── Current/target title ──────────────────────────────────────
        experience = parsed_data.get("experience", [])
        if experience:
            report.current_title = experience[0].get("title", "Professional")
        else:
            report.current_title = "Professional"

        # ── Deterministic computations ────────────────────────────────
        report.career_timeline = self._compute_career_timeline(experience)
        tenure_stats = self._compute_tenure_stats(experience)
        report.avg_tenure_overall = tenure_stats["overall"]
        report.avg_tenure_last3 = tenure_stats["last3"]
        report.longest_tenure = tenure_stats["longest"]
        report.promotion_frequency = self._compute_promotion_frequency(experience, report.years_of_experience)
        report.career_breaks = self._compute_career_breaks(parsed_data.get("employment_gaps", []))
        report.cities_worked = self._compute_cities(experience)

        # ── AI-enriched analysis ──────────────────────────────────────
        try:
            ai_data = self._call_llm_analysis(parsed_data, job_data, screening_result)
            report.executive_summary = ai_data.get("executive_summary", "")
            report.role_type_breakdown = ai_data.get("role_type_breakdown", report.role_type_breakdown)
            report.global_market_exposure = ai_data.get("global_market_exposure", report.global_market_exposure)
            report.company_type_breakdown = ai_data.get("company_type_breakdown", report.company_type_breakdown)
            report.industry_exposure = ai_data.get("industry_exposure", [])
            report.key_achievements = ai_data.get("key_achievements", [])
            report.skills_categorized = ai_data.get("skills_categorized", report.skills_categorized)
            report.technical_stack = ai_data.get("technical_stack", {})
            report.why_shortlist = ai_data.get("why_shortlist", "")
            report.verdict = ai_data.get("verdict", self._derive_verdict(report.match_score))
            report.analysis_scores = ai_data.get("analysis_scores", report.analysis_scores)
        except Exception as exc:
            logger.warning("LLM analysis failed, using fallback", error=str(exc))
            self._apply_fallback(report, parsed_data, screening_result)

        return report

    # ─── Deterministic Helpers ────────────────────────────────────────────

    @staticmethod
    def _compute_career_timeline(experience: list[dict]) -> list[dict]:
        """Extract last 3 roles for the career trajectory timeline."""
        timeline = []
        for exp in experience[:3]:
            start = exp.get("duration_start", "")
            year = ""
            if start:
                year = str(start)[:4]  # extract YYYY
            timeline.append({
                "year": year,
                "title": exp.get("title", "Unknown Role"),
                "company": exp.get("company", "Unknown Company"),
            })
        return timeline

    @staticmethod
    def _compute_tenure_stats(experience: list[dict]) -> dict:
        """Calculate overall avg, last-3 avg, and longest tenure."""
        durations = [e.get("duration_years", 0) or 0 for e in experience if e.get("duration_years")]
        if not durations:
            return {"overall": 0.0, "last3": 0.0, "longest": 0.0}
        overall = round(sum(durations) / len(durations), 1)
        last3 = round(sum(durations[:3]) / min(3, len(durations)), 1)
        longest = round(max(durations), 1)
        return {"overall": overall, "last3": last3, "longest": longest}

    @staticmethod
    def _compute_promotion_frequency(experience: list[dict], total_years: float) -> str:
        num_roles = len(experience)
        if num_roles <= 1 or total_years <= 0:
            return "N/A"
        freq = round(total_years / (num_roles - 1), 1)
        return f"Every {freq} years"

    @staticmethod
    def _compute_career_breaks(gaps: list[dict]) -> str:
        if not gaps:
            return "0 breaks, 0 months"
        total_months = sum(g.get("duration_months", 0) for g in gaps)
        return f"{len(gaps)} break{'s' if len(gaps) != 1 else ''}, {total_months} months"

    @staticmethod
    def _compute_cities(experience: list[dict]) -> str:
        cities = []
        seen = set()
        for exp in experience:
            loc = exp.get("location")
            if loc and loc.lower() not in seen:
                seen.add(loc.lower())
                cities.append(loc)
        if not cities:
            return "Not specified"
        return " → ".join(cities[:5])

    # ─── Groq AI Call ────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_llm_analysis(self, parsed_data: dict, job_data: dict, screening_result: dict) -> dict:
        from app.config import settings

        # Build concise resume JSON (limit token usage)
        resume_json = json.dumps({
            "candidate_name": parsed_data.get("candidate_name"),
            "location": parsed_data.get("location"),
            "total_exp_years": parsed_data.get("total_exp_years"),
            "recent_skills": parsed_data.get("recent_skills", [])[:20],
            "all_skills": parsed_data.get("all_skills", [])[:30],
            "education": parsed_data.get("education", []),
            "experience": [
                {
                    "title": e.get("title"),
                    "company": e.get("company"),
                    "location": e.get("location"),
                    "duration_years": e.get("duration_years"),
                    "description": (e.get("description") or "")[:200],
                    "achievements": e.get("achievements", [])[:3],
                    "skills_used": e.get("skills_used", [])[:10],
                }
                for e in parsed_data.get("experience", [])[:6]
            ],
            "certifications": parsed_data.get("certifications", []),
        }, indent=2)

        required_skills = ", ".join(
            s["skill"] if isinstance(s, dict) else str(s)
            for s in job_data.get("required_skills", [])[:10]
        )

        prompt = ANALYSIS_PROMPT.format(
            resume_json=resume_json,
            job_title=job_data.get("job_title", ""),
            jd_full=(job_data.get("job_description_full") or "")[:2000],
            required_skills=required_skills,
            min_exp_years=job_data.get("required_min_exp_years", 0),
            education_required=job_data.get("education_required", "Not specified"),
            fit_score=screening_result.get("fit_score", 0),
            skills_match=screening_result.get("skills_match_score", 0),
            experience_relevance=screening_result.get("experience_relevance_score", 0),
            career_progression=screening_result.get("career_progression_score", 0),
            achievements=screening_result.get("achievements_score", 0),
            strengths=json.dumps(screening_result.get("strengths", [])),
            weaknesses=json.dumps(screening_result.get("weaknesses", [])),
        )

        response = self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_completion_tokens=4096,
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

    # ─── Fallback (no AI) ────────────────────────────────────────────────

    def _apply_fallback(self, report: PDFReportData, parsed_data: dict, screening_result: dict):
        """Populate AI-enriched fields with deterministic fallbacks."""
        report.executive_summary = screening_result.get("match_explanation") or "AI analysis unavailable."

        # Key achievements from experience
        achievements = []
        for exp in parsed_data.get("experience", []):
            for ach in exp.get("achievements", []):
                achievements.append(ach)
                if len(achievements) >= 5:
                    break
            if len(achievements) >= 5:
                break
        report.key_achievements = achievements or ["No quantified achievements found in resume."]

        # Skills: put all under Technical
        all_skills = parsed_data.get("all_skills", [])
        report.skills_categorized = {
            "Strategic": [],
            "Technical": all_skills[:15],
            "Functional": [],
            "Leadership": [],
        }
        report.technical_stack = {"Tools & Technologies": all_skills[:20]}

        report.why_shortlist = f"Fit score of {report.match_score}/100. {screening_result.get('match_explanation', '')}"
        report.verdict = self._derive_verdict(report.match_score)

        # Map existing 4 category scores to analysis cards
        report.analysis_scores = {
            "alignment": {
                "score": round(report.skills_match_score),
                "fitness": "High" if report.skills_match_score >= 70 else ("Medium" if report.skills_match_score >= 40 else "Low"),
                "bullets": report.strengths[:3] or ["Data unavailable"],
            },
            "divergence": {
                "score": round(100 - report.experience_relevance_score),
                "fitness": "Low" if report.experience_relevance_score >= 70 else ("Medium" if report.experience_relevance_score >= 40 else "High"),
                "bullets": report.weaknesses[:3] or ["No major divergence noted"],
            },
            "compatibility": {
                "score": round(report.career_progression_score),
                "fitness": "High" if report.career_progression_score >= 70 else ("Medium" if report.career_progression_score >= 40 else "Low"),
                "bullets": ["Based on career progression analysis"],
            },
            "concerns": {
                "score": round(100 - report.achievements_score),
                "fitness": "Low" if report.achievements_score >= 70 else ("Medium" if report.achievements_score >= 40 else "High"),
                "bullets": report.weaknesses[:3] or ["No major concerns identified"],
            },
        }

    @staticmethod
    def _derive_verdict(score: float) -> str:
        if score >= 90:
            return "STRONGLY RECOMMEND"
        if score >= 75:
            return "RECOMMEND"
        if score >= 60:
            return "CONSIDER"
        return "PASS"


pdf_analysis_service = PDFAnalysisService()
