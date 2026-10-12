"""
Unit tests for the knockout filter engine.
Tests each rule independently with realistic resume/JD data.
"""
import pytest
from app.services.knockout_engine import check_knockouts


# ─── Sample JD ────────────────────────────────────────────────────────────────
BASE_JD = {
    "job_title": "Senior Backend Engineer",
    "required_min_exp_years": 5,
    "required_skills": [
        {"skill": "Python", "proficiency": "Advanced", "years_required": 5},
        {"skill": "FastAPI", "proficiency": "Advanced", "years_required": 3},
        {"skill": "AWS", "proficiency": "Intermediate", "years_required": 2},
    ],
    "top_3_mandatory_skills": ["Python", "FastAPI", "AWS"],
    "nice_to_have_skills": ["Docker", "Kubernetes"],
    "education_required": "B.Tech Computer Science",
    "locations_accepted": ["Bangalore", "Remote"],
    "willingness_to_relocate": "Preferred",
}

# ─── Sample Resumes ───────────────────────────────────────────────────────────
GOOD_CANDIDATE = {
    "candidate_name": "John Doe",
    "total_exp_years": 7,
    "recent_skills": ["Python", "FastAPI", "AWS", "PostgreSQL"],
    "all_skills": ["Python", "FastAPI", "AWS", "PostgreSQL", "Docker"],
    "location": "Bangalore, India",
    "education": [{"degree": "B.Tech Computer Science", "institution": "IIT", "year": 2017}],
    "experience": [
        {
            "title": "Senior Backend Engineer",
            "company": "TechCorp",
            "duration_start": "2022-01",
            "duration_end": "Present",
            "duration_years": 2,
            "skills_used": ["Python", "FastAPI", "AWS"],
            "achievements": ["Reduced latency by 40%"],
        }
    ],
    "employment_gaps": [],
}


# ─── Tests: Experience ────────────────────────────────────────────────────────

class TestExperienceFilter:
    def test_passes_with_sufficient_experience(self):
        passed, failures = check_knockouts(GOOD_CANDIDATE, BASE_JD)
        assert passed
        assert not any(f["rule"] == "EXPERIENCE_MISMATCH" for f in failures)

    def test_fails_with_very_low_experience(self):
        resume = {**GOOD_CANDIDATE, "total_exp_years": 1}
        passed, failures = check_knockouts(resume, BASE_JD)
        assert not passed
        assert any(f["rule"] == "EXPERIENCE_MISMATCH" for f in failures)

    def test_passes_with_buffer_experience(self):
        # 3 years for 5-year requirement → within 60% buffer
        resume = {**GOOD_CANDIDATE, "total_exp_years": 3}
        passed, failures = check_knockouts(resume, BASE_JD)
        exp_failures = [f for f in failures if f["rule"] == "EXPERIENCE_MISMATCH"]
        assert not exp_failures  # 3 >= 5 * 0.6 = 3

    def test_no_requirement_always_passes(self):
        jd = {**BASE_JD, "required_min_exp_years": 0}
        resume = {**GOOD_CANDIDATE, "total_exp_years": 0}
        passed, failures = check_knockouts(resume, jd)
        assert not any(f["rule"] == "EXPERIENCE_MISMATCH" for f in failures)


# ─── Tests: Skills ────────────────────────────────────────────────────────────

class TestSkillsFilter:
    def test_passes_with_all_mandatory_skills(self):
        passed, failures = check_knockouts(GOOD_CANDIDATE, BASE_JD)
        assert not any(f["rule"] == "MISSING_MANDATORY_SKILLS" for f in failures)

    def test_fails_when_missing_mandatory_skill(self):
        resume = {
            **GOOD_CANDIDATE,
            "recent_skills": ["Python", "Django"],  # Missing FastAPI and AWS
        }
        passed, failures = check_knockouts(resume, BASE_JD)
        assert any(f["rule"] == "MISSING_MANDATORY_SKILLS" for f in failures)

    def test_partial_skill_match(self):
        # Candidate has Python but not FastAPI or AWS in recent
        resume = {
            **GOOD_CANDIDATE,
            "recent_skills": ["Python", "PostgreSQL"],
        }
        _, failures = check_knockouts(resume, BASE_JD)
        skill_failures = [f for f in failures if f["rule"] == "MISSING_MANDATORY_SKILLS"]
        assert skill_failures
        assert "FastAPI" in skill_failures[0]["reason"] or "AWS" in skill_failures[0]["reason"]

    def test_passes_when_no_mandatory_skills_required(self):
        jd = {**BASE_JD, "top_3_mandatory_skills": [], "required_skills": []}
        passed, failures = check_knockouts(GOOD_CANDIDATE, jd)
        assert not any(f["rule"] == "MISSING_MANDATORY_SKILLS" for f in failures)


# ─── Tests: Employment Gaps ───────────────────────────────────────────────────

class TestEmploymentGapFilter:
    def test_passes_with_no_gaps(self):
        resume = {**GOOD_CANDIDATE, "employment_gaps": []}
        passed, failures = check_knockouts(resume, BASE_JD)
        assert not any(f["rule"] == "EMPLOYMENT_GAP" for f in failures)

    def test_passes_with_small_gap(self):
        resume = {
            **GOOD_CANDIDATE,
            "employment_gaps": [{"start": "2022-01", "end": "2022-03", "duration_months": 2}],
        }
        passed, failures = check_knockouts(resume, BASE_JD)
        assert not any(f["rule"] == "EMPLOYMENT_GAP" for f in failures)

    def test_fails_with_large_gap(self):
        resume = {
            **GOOD_CANDIDATE,
            "employment_gaps": [
                {"start": "2021-01", "end": "2022-05", "duration_months": 16}
            ],
        }
        passed, failures = check_knockouts(resume, BASE_JD)
        assert any(f["rule"] == "EMPLOYMENT_GAP" for f in failures)

    def test_fails_with_exactly_13_months(self):
        resume = {
            **GOOD_CANDIDATE,
            "employment_gaps": [
                {"start": "2021-01", "end": "2022-02", "duration_months": 13}
            ],
        }
        _, failures = check_knockouts(resume, BASE_JD)
        assert any(f["rule"] == "EMPLOYMENT_GAP" for f in failures)


# ─── Tests: Location ─────────────────────────────────────────────────────────

class TestLocationFilter:
    def test_passes_with_matching_location(self):
        passed, failures = check_knockouts(GOOD_CANDIDATE, BASE_JD)
        assert not any(f["rule"] == "LOCATION_MISMATCH" for f in failures)

    def test_passes_with_remote_allowed(self):
        jd = {**BASE_JD, "locations_accepted": ["Remote"]}
        resume = {**GOOD_CANDIDATE, "location": "Mumbai, India"}
        passed, failures = check_knockouts(resume, jd)
        assert not any(f["rule"] == "LOCATION_MISMATCH" for f in failures)

    def test_passes_with_no_location_restriction(self):
        jd = {**BASE_JD, "locations_accepted": []}
        resume = {**GOOD_CANDIDATE, "location": "Tokyo, Japan"}
        passed, failures = check_knockouts(resume, jd)
        assert not any(f["rule"] == "LOCATION_MISMATCH" for f in failures)


# ─── Tests: Education ─────────────────────────────────────────────────────────

class TestEducationFilter:
    def test_passes_with_required_degree(self):
        passed, failures = check_knockouts(GOOD_CANDIDATE, BASE_JD)
        assert not any(f["rule"] == "EDUCATION_REQUIREMENT_NOT_MET" for f in failures)

    def test_fails_with_no_education(self):
        resume = {**GOOD_CANDIDATE, "education": []}
        _, failures = check_knockouts(resume, BASE_JD)
        assert any(f["rule"] == "EDUCATION_REQUIREMENT_NOT_MET" for f in failures)

    def test_passes_when_no_education_required(self):
        jd = {**BASE_JD, "education_required": None}
        resume = {**GOOD_CANDIDATE, "education": []}
        passed, failures = check_knockouts(resume, jd)
        assert not any(f["rule"] == "EDUCATION_REQUIREMENT_NOT_MET" for f in failures)


# ─── Integration Test ─────────────────────────────────────────────────────────

class TestFullKnockout:
    def test_perfect_candidate_passes_all(self):
        passed, failures = check_knockouts(GOOD_CANDIDATE, BASE_JD)
        assert passed
        assert failures == []

    def test_weak_candidate_fails_multiple(self):
        resume = {
            "candidate_name": "Weak Candidate",
            "total_exp_years": 0.5,
            "recent_skills": ["HTML", "CSS"],
            "all_skills": ["HTML", "CSS"],
            "location": "New York, USA",
            "education": [],
            "experience": [],
            "employment_gaps": [
                {"start": "2020-01", "end": "2022-06", "duration_months": 30}
            ],
        }
        jd = {**BASE_JD, "locations_accepted": ["Bangalore"]}
        passed, failures = check_knockouts(resume, jd)
        assert not passed
        assert len(failures) >= 3
