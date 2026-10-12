"""
Deterministic knockout filter engine.
Immediately disqualifies candidates that don't meet hard requirements.
"""
from __future__ import annotations

from datetime import datetime
import structlog

logger = structlog.get_logger()

MAX_GAP_MONTHS = 12
RECENT_YEARS_THRESHOLD = 3
EXPERIENCE_BUFFER_RATIO = 0.6  # allow up to 40% below required (e.g. 5yr req → 3yr min)


def check_knockouts(
    parsed_resume: dict,
    parsed_jd: dict,
) -> tuple[bool, list[dict]]:
    """
    Run all knockout rules against a candidate.

    Returns:
        passed: True if the candidate passes all filters.
        failures: List of {rule, reason} dicts for transparency.
    """
    failures: list[dict] = []

    _check_experience(parsed_resume, parsed_jd, failures)
    _check_top_skills(parsed_resume, parsed_jd, failures)
    _check_recent_relevance(parsed_resume, parsed_jd, failures)
    _check_employment_gaps(parsed_resume, failures)
    _check_location(parsed_resume, parsed_jd, failures)
    _check_education(parsed_resume, parsed_jd, failures)

    return len(failures) == 0, failures


# ─── Individual Rules ──────────────────────────────────────────────────────────

def _check_experience(resume: dict, jd: dict, failures: list) -> None:
    required = jd.get("required_min_exp_years", 0)
    if required <= 0:
        return  # no requirement

    candidate_years = resume.get("total_exp_years", 0) or 0
    min_acceptable = required * EXPERIENCE_BUFFER_RATIO

    if candidate_years < min_acceptable:
        failures.append(
            {
                "rule": "EXPERIENCE_MISMATCH",
                "reason": (
                    f"Candidate has {candidate_years:.1f} years of experience, "
                    f"but the role requires {required}+ years "
                    f"(minimum threshold: {min_acceptable:.1f} years)."
                ),
            }
        )


def _check_top_skills(resume: dict, jd: dict, failures: list) -> None:
    top_3 = jd.get("top_3_mandatory_skills", [])
    if not top_3:
        # Fall back to first 3 required skills
        top_3 = [s["skill"] for s in jd.get("required_skills", [])[:3]]
    if not top_3:
        return

    # Filter out any nice-to-have skills that may have leaked into top_3
    nice_to_have_lower = {s.lower() for s in jd.get("nice_to_have_skills", [])}
    top_3 = [s for s in top_3 if s.lower() not in nice_to_have_lower]
    if not top_3:
        return

    recent_skills_lower = {s.lower() for s in resume.get("recent_skills", [])}
    all_skills_lower = {s.lower() for s in resume.get("all_skills", [])}
    combined_skills = recent_skills_lower | all_skills_lower

    missing_mandatory = []
    for skill in top_3:
        if not _skill_present(skill, combined_skills):
            missing_mandatory.append(skill)

    # Only knock out if majority of top skills are missing (not just one)
    if missing_mandatory and len(missing_mandatory) > len(top_3) // 2:
        failures.append(
            {
                "rule": "MISSING_MANDATORY_SKILLS",
                "reason": (
                    f"Missing mandatory skills: "
                    + ", ".join(missing_mandatory)
                ),
            }
        )


def _check_recent_relevance(resume: dict, jd: dict, failures: list) -> None:
    """Check if the last 2 years of experience align with JD requirements."""
    nice_to_have_lower = {s.lower() for s in jd.get("nice_to_have_skills", [])}
    required_skills_lower = {
        s["skill"].lower() for s in jd.get("required_skills", [])
        if s["skill"].lower() not in nice_to_have_lower
    }
    if not required_skills_lower:
        return

    current_year = datetime.now().year
    recent_experience = [
        exp
        for exp in resume.get("experience", [])
        if _is_recent(exp.get("duration_end", ""), years=2)
    ]

    if not recent_experience:
        return  # No recent experience → already handled by experience check

    recent_skills_lower = set()
    for exp in recent_experience:
        for skill in exp.get("skills_used", []):
            recent_skills_lower.add(skill.lower())

    # Check overlap
    overlap = sum(
        1
        for skill in required_skills_lower
        if _skill_present(skill, recent_skills_lower)
    )
    overlap_ratio = overlap / len(required_skills_lower) if required_skills_lower else 1

    if overlap_ratio < 0.2 and len(required_skills_lower) >= 3:
        failures.append(
            {
                "rule": "RECENT_EXPERIENCE_IRRELEVANT",
                "reason": (
                    f"Recent experience (last 2 years) has low overlap ({overlap_ratio:.0%}) "
                    "with role requirements. May indicate career pivot or stale skills."
                ),
            }
        )

    _ = current_year  # suppress unused warning


def _check_employment_gaps(resume: dict, failures: list) -> None:
    for gap in resume.get("employment_gaps", []):
        duration = gap.get("duration_months", 0) or 0
        if duration > MAX_GAP_MONTHS:
            failures.append(
                {
                    "rule": "EMPLOYMENT_GAP",
                    "reason": (
                        f"Employment gap of {duration:.1f} months detected "
                        f"({gap.get('start', '?')} – {gap.get('end', '?')}). "
                        "Unexplained gaps >12 months are flagged for review."
                    ),
                }
            )


def _check_location(resume: dict, jd: dict, failures: list) -> None:
    accepted_locations = [loc.lower() for loc in jd.get("locations_accepted", [])]
    if not accepted_locations or "remote" in accepted_locations:
        return  # no restriction or remote allowed

    candidate_location = (resume.get("location") or "").lower()
    if not candidate_location:
        return  # can't verify, allow through

    if not any(loc in candidate_location or candidate_location in loc for loc in accepted_locations):
        # Check relocation
        relocate = (jd.get("willingness_to_relocate") or "").lower()
        if "preferred" in relocate or "yes" in relocate:
            return  # relocation welcome

        failures.append(
            {
                "rule": "LOCATION_MISMATCH",
                "reason": (
                    f"Candidate location '{resume.get('location')}' does not match "
                    f"accepted locations: {', '.join(jd.get('locations_accepted', []))}."
                ),
            }
        )


def _check_education(resume: dict, jd: dict, failures: list) -> None:
    education_required = jd.get("education_required") or ""
    if not education_required:
        return

    education_lower = education_required.lower()
    # Extract key education keywords
    keywords = [kw for kw in ["b.tech", "b.e", "bachelor", "master", "phd", "mba"] if kw in education_lower]
    if not keywords:
        return

    candidate_degrees = " ".join(
        f"{e.get('degree', '')} {e.get('institution', '')}".lower()
        for e in resume.get("education", [])
    )

    if not any(kw in candidate_degrees for kw in keywords):
        failures.append(
            {
                "rule": "EDUCATION_REQUIREMENT_NOT_MET",
                "reason": (
                    f"Education requirement '{education_required}' not found in candidate profile."
                ),
            }
        )


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _skill_present(skill: str, skill_set: set[str]) -> bool:
    """Fuzzy skill matching (handles abbreviations and partial matches)."""
    skill_lower = skill.lower()
    if skill_lower in skill_set:
        return True
    # Check partial match
    return any(
        skill_lower in s or s in skill_lower
        for s in skill_set
        if len(skill_lower) > 2 and len(s) > 2
    )


def _is_recent(duration_end: str, years: int = 2) -> bool:
    """Check if a job's end date is within the last N years."""
    if not duration_end or duration_end.lower() in ("present", "current", "now"):
        return True

    current_year = datetime.now().year
    try:
        end_year = int(duration_end[:4])
        return (current_year - end_year) <= years
    except (ValueError, IndexError):
        return True
