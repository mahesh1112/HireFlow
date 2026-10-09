"""
Unit tests for the deterministic scoring engine.
Tests the weighted score calculation and status tier assignments.
"""
import pytest
from app.services.scoring_engine import ScoringEngine, WEIGHTS


engine = ScoringEngine()

BASE_JD = {
    "job_title": "Senior Backend Engineer",
    "required_min_exp_years": 5,
    "required_skills": [
        {"skill": "Python", "proficiency": "Advanced", "years_required": 5},
        {"skill": "FastAPI", "proficiency": "Advanced", "years_required": 3},
    ],
    "nice_to_have_skills": ["Docker"],
    "education_required": "B.Tech",
    "top_3_mandatory_skills": ["Python", "FastAPI", "AWS"],
    "job_description_full": "Looking for a senior backend engineer...",
}

STRONG_RESUME = {
    "candidate_name": "Alice Smith",
    "total_exp_years": 8,
    "recent_skills": ["Python", "FastAPI", "AWS", "Docker"],
    "all_skills": ["Python", "FastAPI", "AWS", "Docker", "PostgreSQL"],
    "experience": [
        {
            "title": "Lead Engineer",
            "company": "BigTech",
            "duration_start": "2020-01",
            "duration_end": "Present",
            "duration_years": 4,
            "achievements": ["Led team of 10", "3x throughput", "60% cost reduction"],
            "skills_used": ["Python", "FastAPI", "AWS"],
        },
        {
            "title": "Backend Engineer",
            "company": "StartupXYZ",
            "duration_start": "2016-01",
            "duration_end": "2019-12",
            "duration_years": 4,
            "achievements": ["Built 5 microservices"],
            "skills_used": ["Python", "Django"],
        },
    ],
    "education": [{"degree": "B.Tech Computer Science", "institution": "IIT", "year": 2016}],
    "employment_gaps": [],
}

WEAK_RESUME = {
    "candidate_name": "Bob Jones",
    "total_exp_years": 1,
    "recent_skills": ["JavaScript"],
    "all_skills": ["JavaScript", "HTML"],
    "experience": [
        {
            "title": "Junior Developer",
            "company": "WebShop",
            "duration_start": "2023-01",
            "duration_end": "Present",
            "duration_years": 1,
            "achievements": [],
            "skills_used": ["JavaScript"],
        }
    ],
    "education": [],
    "employment_gaps": [],
}


class TestWeightedScore:
    def test_weights_sum_to_one(self):
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_compute_weighted_score_perfect(self):
        scores = {
            "skills_match": 100,
            "experience_relevance": 100,
            "career_progression": 100,
            "measurable_achievements": 100,
        }
        result = engine._compute_weighted_score(scores)
        assert result == pytest.approx(100.0)

    def test_compute_weighted_score_zero(self):
        scores = {
            "skills_match": 0,
            "experience_relevance": 0,
            "career_progression": 0,
            "measurable_achievements": 0,
        }
        result = engine._compute_weighted_score(scores)
        assert result == pytest.approx(0.0)

    def test_skills_weight_most_important(self):
        # Skills alone at 100, rest 0
        scores_skills = {
            "skills_match": 100,
            "experience_relevance": 0,
            "career_progression": 0,
            "measurable_achievements": 0,
        }
        # Experience alone at 100, rest 0
        scores_exp = {
            "skills_match": 0,
            "experience_relevance": 100,
            "career_progression": 0,
            "measurable_achievements": 0,
        }
        assert engine._compute_weighted_score(scores_skills) > engine._compute_weighted_score(scores_exp)


class TestStatusTiers:
    def test_excellent_tier(self):
        assert engine._get_status(100) == "EXCELLENT"
        assert engine._get_status(86) == "EXCELLENT"
        assert engine._get_status(90) == "EXCELLENT"

    def test_good_tier(self):
        assert engine._get_status(85) == "GOOD"
        assert engine._get_status(61) == "GOOD"
        assert engine._get_status(75) == "GOOD"

    def test_adequate_tier(self):
        assert engine._get_status(60) == "ADEQUATE"
        assert engine._get_status(31) == "ADEQUATE"
        assert engine._get_status(45) == "ADEQUATE"

    def test_poor_tier(self):
        assert engine._get_status(30) == "POOR"
        assert engine._get_status(0) == "POOR"
        assert engine._get_status(15) == "POOR"


class TestDeterministicScoring:
    def test_strong_candidate_scores_higher(self):
        strong = engine.score_candidate_deterministic(STRONG_RESUME, BASE_JD)
        weak = engine.score_candidate_deterministic(WEAK_RESUME, BASE_JD)
        assert strong["fit_score"] > weak["fit_score"]

    def test_strong_candidate_status_not_poor(self):
        result = engine.score_candidate_deterministic(STRONG_RESUME, BASE_JD)
        assert result["status"] != "POOR"

    def test_weak_candidate_status_poor_or_adequate(self):
        result = engine.score_candidate_deterministic(WEAK_RESUME, BASE_JD)
        assert result["status"] in ("POOR", "ADEQUATE")

    def test_returns_required_fields(self):
        result = engine.score_candidate_deterministic(STRONG_RESUME, BASE_JD)
        required_fields = [
            "fit_score", "status", "category_scores", "strengths",
            "weaknesses", "skills_matched", "skills_missing",
            "match_explanation", "screening_time_ms",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_fit_score_in_range(self):
        result = engine.score_candidate_deterministic(STRONG_RESUME, BASE_JD)
        assert 0 <= result["fit_score"] <= 100

    def test_category_scores_in_range(self):
        result = engine.score_candidate_deterministic(STRONG_RESUME, BASE_JD)
        for key, val in result["category_scores"].items():
            assert 0 <= val <= 100, f"{key} out of range: {val}"

    def test_skills_matched_are_subset_of_required(self):
        result = engine.score_candidate_deterministic(STRONG_RESUME, BASE_JD)
        required = {s["skill"].lower() for s in BASE_JD["required_skills"]}
        for sm in result["skills_matched"]:
            assert sm["required_skill"].lower() in required
