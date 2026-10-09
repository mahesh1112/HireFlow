"""
Job description and screening endpoints.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, delete
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.job import JobDescription
from app.models.resume import Resume
from app.models.screening import ScreeningResult
from app.models.unit import BusinessUnit, UserUnit
from app.utils.auth import get_current_user
from app.utils.unit_auth import get_current_user_units
from app.services.resume_parser import resume_parser
from app.services.embedding_service import embedding_service
from app.services.pinecone_service import pinecone_service
from app.services.knockout_engine import check_knockouts
from app.services.scoring_engine import scoring_engine
from app.config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    job_description_text: str
    job_title: str | None = None
    company: str | None = None
    # Lifecycle metadata (all optional for backward compat)
    business_unit_id: str | None = None
    experience: str | None = None       # "0-2 yrs" | "2-5 yrs" | "5-10 yrs" | "10+ yrs"
    employee_type: str | None = None    # "Full-time" | "Contract" | "Internship"
    location_office: str | None = None  # "Kothrud" | "Baner" | "Hinjewadi"
    remote_job: bool = False
    hiring_leads: list[str] = []
    recruiter_id: str | None = None
    valid_till: str | None = None       # ISO date string for end date


class ScreenRequest(BaseModel):
    max_candidates: int = 20


class UpdateJobStatusRequest(BaseModel):
    action: str  # "activate" | "pause" | "fill"
    valid_till: str | None = None  # Optional custom date for extend/activate


class UpdateJobRequest(BaseModel):
    job_title: str | None = None
    company: str | None = None
    business_unit_id: str | None = None
    experience: str | None = None
    employee_type: str | None = None
    location_office: str | None = None
    remote_job: bool | None = None
    hiring_leads: list[str] | None = None
    recruiter_id: str | None = None
    valid_till: str | None = None
    job_description_text: str | None = None


# ─── Background: Screen all candidates ───────────────────────────────────────

async def _set_screening_status(
    job_id: str, status: str, error: str | None = None
) -> None:
    """Helper to update the screening_status on a job from a background task."""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        job_result = await db.execute(
            select(JobDescription).where(JobDescription.job_id == job_id)
        )
        job = job_result.scalar_one_or_none()
        if job:
            job.screening_status = status
            job.screening_error = error
            await db.commit()


async def _screen_candidates(
    job_id: str,
    user_id: str,
    max_candidates: int,
    unit_ids: list[str],
) -> None:
    """
    Full screening pipeline:
    1. Parse & embed the JD
    2. Semantic search in Pinecone scoped to unit(s) for candidate pool
    3. Apply knockout filters
    4. Score remaining candidates with LLM
    5. Rank and persist results
    """
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Fetch job
            job_result = await db.execute(
                select(JobDescription).where(JobDescription.job_id == job_id)
            )
            job = job_result.scalar_one_or_none()
            if not job:
                await _set_screening_status(job_id, "failed", "Job not found")
                return

            # Derive top 3 mandatory skills, excluding any nice-to-have skills
            nice_lower = {s.lower() for s in (job.nice_to_have_skills or [])}
            mandatory_skills = [
                s["skill"] for s in (job.required_skills or [])
                if s["skill"].lower() not in nice_lower
            ]
            parsed_jd = {
                "job_title": job.job_title,
                "required_min_exp_years": job.required_min_exp_years,
                "required_skills": job.required_skills,
                "nice_to_have_skills": job.nice_to_have_skills,
                "education_required": job.education_required,
                "locations_accepted": job.locations_accepted,
                "willingness_to_relocate": job.willingness_to_relocate,
                "top_3_mandatory_skills": mandatory_skills[:3],
                "job_description_full": job.job_description_full,
            }

            # Generate JD embeddings
            jd_vectors = embedding_service.embed_jd(parsed_jd)

            # Search Pinecone for top candidate pool (3× the required shortlist)
            # Filter by unit_id(s) for strict cross-unit isolation (Gap 11.13)
            candidate_pool_size = min(max_candidates * 3, 100)

            if len(unit_ids) == 1:
                pinecone_filter = {"unit_id": {"$eq": unit_ids[0]}}
            elif len(unit_ids) > 1:
                pinecone_filter = {"unit_id": {"$in": unit_ids}}
            else:
                # Backward compat: user has no units assigned yet
                pinecone_filter = {"user_id": {"$eq": user_id}}

            semantic_matches = pinecone_service.search_by_jd(
                jd_vectors,
                top_k=candidate_pool_size,
                filters=pinecone_filter,
            )

            # If Pinecone not available, fall back to DB query scoped to unit(s)
            if not semantic_matches:
                if unit_ids:
                    fallback_filter = Resume.unit_id.in_(unit_ids)
                else:
                    fallback_filter = Resume.user_id == user_id

                resume_result = await db.execute(
                    select(Resume)
                    .where(
                        fallback_filter,
                        Resume.parse_status == "completed",
                    )
                    .limit(candidate_pool_size)
                )
                resumes = resume_result.scalars().all()
                semantic_matches = [
                    {"resume_id": r.id, "similarity_score": 0.5, "metadata": {}}
                    for r in resumes
                ]

            if not semantic_matches:
                logger.warning("No candidates found for screening", job_id=job_id)
                await _set_screening_status(
                    job_id, "failed", "No candidates found with uploaded resumes"
                )
                return

            # Fetch resume records for matched candidates
            resume_ids = [m["resume_id"] for m in semantic_matches]
            resume_result = await db.execute(
                select(Resume).where(Resume.id.in_(resume_ids))
            )
            resume_map = {r.id: r for r in resume_result.scalars().all()}

            # Score candidates concurrently (with rate limiting)
            semaphore = asyncio.Semaphore(3)
            results: list[ScreeningResult] = []

            async def score_one(match: dict) -> ScreeningResult | None:
                async with semaphore:
                    resume = resume_map.get(match["resume_id"])
                    if not resume or not resume.parsed_data:
                        return None

                    parsed_resume = resume.parsed_data

                    # 1. Knockout filters (deterministic, fast)
                    passed, failures = check_knockouts(parsed_resume, parsed_jd)

                    if not passed:
                        # Still generate basic skills analysis for knocked-out candidates
                        ko_score = scoring_engine.score_candidate_deterministic(
                            parsed_resume, parsed_jd
                        )
                        return ScreeningResult(
                            resume_id=resume.id,
                            job_id=job_id,
                            fit_score=0,
                            status="POOR",
                            passed_knockouts=False,
                            knockout_failures=failures,
                            skills_match_score=ko_score["category_scores"]["skills_match"],
                            experience_relevance_score=ko_score["category_scores"]["experience_relevance"],
                            career_progression_score=ko_score["category_scores"]["career_progression"],
                            achievements_score=ko_score["category_scores"]["measurable_achievements"],
                            strengths=ko_score["strengths"],
                            weaknesses=ko_score["weaknesses"],
                            skills_matched=ko_score["skills_matched"],
                            skills_missing=ko_score["skills_missing"],
                            match_explanation=f"Knocked out: {'; '.join(f['rule'] for f in failures)}",
                            candidate_name=resume.candidate_name,
                            candidate_email=resume.candidate_email,
                            candidate_location=resume.candidate_location,
                            total_exp_years=resume.total_exp_years or 0,
                        )

                    # 2. AI scoring — run sync LLM call in a thread to avoid
                    #    blocking the async event loop
                    try:
                        score_data = await asyncio.to_thread(
                            scoring_engine.score_candidate, parsed_resume, parsed_jd
                        )
                    except Exception as exc:
                        logger.warning("LLM scoring failed, using deterministic", error=str(exc))
                        score_data = scoring_engine.score_candidate_deterministic(
                            parsed_resume, parsed_jd
                        )

                    return ScreeningResult(
                        resume_id=resume.id,
                        job_id=job_id,
                        fit_score=score_data["fit_score"],
                        status=score_data["status"],
                        passed_knockouts=True,
                        knockout_failures=[],
                        skills_match_score=score_data["category_scores"]["skills_match"],
                        experience_relevance_score=score_data["category_scores"]["experience_relevance"],
                        career_progression_score=score_data["category_scores"]["career_progression"],
                        achievements_score=score_data["category_scores"]["measurable_achievements"],
                        strengths=score_data["strengths"],
                        weaknesses=score_data["weaknesses"],
                        skills_matched=score_data["skills_matched"],
                        skills_missing=score_data["skills_missing"],
                        match_explanation=score_data["match_explanation"],
                        candidate_name=resume.candidate_name,
                        candidate_email=resume.candidate_email,
                        candidate_location=resume.candidate_location,
                        total_exp_years=resume.total_exp_years or 0,
                        screening_time_ms=score_data["screening_time_ms"],
                    )

            scored = await asyncio.gather(*[score_one(m) for m in semantic_matches])
            valid_results = [r for r in scored if r is not None]

            if not valid_results:
                logger.warning(
                    "Screening produced 0 results — all resumes may lack parsed data",
                    job_id=job_id,
                    semantic_matches=len(semantic_matches),
                )
                job.screening_status = "failed"
                job.screening_error = (
                    f"0 of {len(semantic_matches)} candidates could be scored. "
                    "Resumes may not be parsed yet — try re-uploading them."
                )
                await db.commit()
                return

            # Sort: passed_knockouts first, then by fit_score
            valid_results.sort(
                key=lambda r: (0 if r.passed_knockouts else 1, -r.fit_score)
            )

            # Assign ranks to top candidates who passed
            rank = 1
            for r in valid_results:
                if r.passed_knockouts:
                    r.rank = rank
                    rank += 1

            # Delete old screening results for this job before persisting new ones
            await db.execute(
                delete(ScreeningResult).where(ScreeningResult.job_id == job_id)
            )

            # Persist results
            for r in valid_results:
                db.add(r)

            # Update job screening count and mark completed
            job.screening_count += 1
            job.screening_status = "completed"
            job.screening_error = None
            await db.commit()

            logger.info(
                "Screening complete",
                job_id=job_id,
                total=len(valid_results),
                passed=sum(1 for r in valid_results if r.passed_knockouts),
            )

        except Exception as exc:
            logger.error("Screening pipeline failed", job_id=job_id, error=str(exc))
            # Mark the job as failed so the frontend stops polling
            try:
                await _set_screening_status(job_id, "failed", str(exc))
            except Exception:
                logger.error("Failed to update screening status", job_id=job_id)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_job(
    data: CreateJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not data.job_description_text.strip():
        raise HTTPException(status_code=400, detail="Job description text is required")

    # Parse JD with LLM (graceful fallback if API is down)
    parsed_jd = None
    try:
        parsed_jd = resume_parser.parse_jd(data.job_description_text)
    except Exception as exc:
        logger.warning("LLM JD parsing failed, using fallback", error=str(exc))

    if not parsed_jd:
        # Fallback: extract basic skills from JD text using keyword matching
        import re as _re
        jd_lower = data.job_description_text.lower()
        # Common tech skills to look for in JD text
        _COMMON_SKILLS = [
            "python", "java", "javascript", "typescript", "react", "angular", "vue",
            "node.js", "nodejs", "express", "django", "flask", "fastapi", "spring",
            "aws", "azure", "gcp", "docker", "kubernetes", "sql", "postgresql",
            "mongodb", "redis", "git", "ci/cd", "rest", "graphql", "html", "css",
            "c++", "c#", ".net", "go", "rust", "swift", "kotlin", "ruby", "php",
            "machine learning", "deep learning", "data science", "terraform",
            "jenkins", "linux", "agile", "scrum", "jira", "figma",
        ]
        found_skills = [s for s in _COMMON_SKILLS if s in jd_lower]
        # Try to extract experience requirement from text (e.g., "5+ years", "3-5 years")
        exp_match = _re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?experience", jd_lower)
        fallback_exp = int(exp_match.group(1)) if exp_match else 0
        # If not found in JD text, derive from the form's experience field (e.g. "5-10 yrs" → 5)
        if fallback_exp == 0 and data.experience:
            exp_field_match = _re.search(r"(\d+)", data.experience)
            if exp_field_match:
                fallback_exp = int(exp_field_match.group(1))

        parsed_jd = {
            "job_title": data.job_title or "Software Engineer",
            "required_skills": [
                {"skill": s.title(), "proficiency": "Intermediate", "years_required": 1}
                for s in found_skills[:10]
            ],
            "nice_to_have_skills": [s.title() for s in found_skills[10:]],
            "required_min_exp_years": fallback_exp,
            "_parse_method": "fallback",
        }

    # Generate next HARB_<N> job ID
    max_result = await db.execute(
        select(func.max(JobDescription.job_id))
        .where(JobDescription.job_id.like("HARB_%"))
    )
    max_id = max_result.scalar()
    if max_id:
        try:
            next_num = int(max_id.split("_")[1]) + 1
        except (IndexError, ValueError):
            next_num = 1
    else:
        next_num = 1
    new_job_id = f"HARB_{next_num:03d}"

    now = datetime.now(timezone.utc)
    # Parse valid_till from request or default to now + 30 days
    if data.valid_till:
        try:
            parsed_valid_till = datetime.fromisoformat(data.valid_till.replace("Z", "+00:00"))
            if parsed_valid_till.tzinfo is None:
                parsed_valid_till = parsed_valid_till.replace(tzinfo=timezone.utc)
        except ValueError:
            parsed_valid_till = now + timedelta(days=30)
    else:
        parsed_valid_till = now + timedelta(days=30)

    # Form experience field ("4-6 yrs") takes precedence over AI-parsed value
    req_min_exp = parsed_jd.get("required_min_exp_years", 0)
    if data.experience:
        import re as _re2
        _exp_match = _re2.search(r"(\d+)", data.experience)
        if _exp_match:
            req_min_exp = int(_exp_match.group(1))

    job = JobDescription(
        job_id=new_job_id,
        user_id=current_user.id,
        job_title=data.job_title or parsed_jd.get("job_title", "Software Engineer"),
        company=data.company or parsed_jd.get("company"),
        location=parsed_jd.get("location"),
        required_min_exp_years=req_min_exp,
        preferred_min_exp_years=parsed_jd.get("preferred_min_exp_years"),
        required_skills=parsed_jd.get("required_skills", []),
        nice_to_have_skills=parsed_jd.get("nice_to_have_skills", []),
        education_required=parsed_jd.get("education_required"),
        locations_accepted=parsed_jd.get("locations_accepted", []),
        willingness_to_relocate=parsed_jd.get("willingness_to_relocate"),
        job_description_full=data.job_description_text,
        # Lifecycle fields
        business_unit_id=data.business_unit_id,
        experience=data.experience,
        employee_type=data.employee_type,
        location_office=data.location_office,
        remote_job=data.remote_job,
        hiring_leads=data.hiring_leads,
        recruiter_id=data.recruiter_id,
        valid_till=parsed_valid_till,
        status="active",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Auto-assign creator to business unit (for unit-scoped access)
    if data.business_unit_id:
        existing_uu = await db.execute(
            select(UserUnit).where(
                UserUnit.user_id == current_user.id,
                UserUnit.unit_id == data.business_unit_id,
            )
        )
        if not existing_uu.scalar_one_or_none():
            db.add(UserUnit(user_id=current_user.id, unit_id=data.business_unit_id))
            await db.commit()

    return _job_to_dict(job)


@router.get("")
async def list_jobs(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * page_size
    count_result = await db.execute(
        select(func.count(JobDescription.job_id)).where(
            JobDescription.user_id == current_user.id
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(JobDescription)
        .where(JobDescription.user_id == current_user.id)
        .order_by(JobDescription.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    jobs_list = result.scalars().all()

    # Batch-resolve unit names and recruiter names for the list
    unit_ids = {j.business_unit_id for j in jobs_list if j.business_unit_id}
    recruiter_ids = {j.recruiter_id for j in jobs_list if j.recruiter_id}

    unit_map: dict[str, str] = {}
    if unit_ids:
        u_result = await db.execute(
            select(BusinessUnit.id, BusinessUnit.unit_name).where(BusinessUnit.id.in_(unit_ids))
        )
        unit_map = {r[0]: r[1] for r in u_result.fetchall()}

    recruiter_map: dict[str, str] = {}
    if recruiter_ids:
        r_result = await db.execute(
            select(User.id, User.name).where(User.id.in_(recruiter_ids))
        )
        recruiter_map = {r[0]: r[1] for r in r_result.fetchall()}

    now = datetime.now(timezone.utc)
    items = []
    for j in jobs_list:
        d = _job_to_dict(j)
        d["unit_name"] = unit_map.get(j.business_unit_id) if j.business_unit_id else None
        d["recruiter_name"] = recruiter_map.get(j.recruiter_id) if j.recruiter_id else None
        # Auto-expire: if valid_till past and status still active, show as expired
        if j.valid_till and j.valid_till < now and j.status == "active":
            d["status"] = "expired"
        items.append(d)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{job_id}/unit-resumes")
async def get_unit_resumes_for_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_unit_ids: list[str] = Depends(get_current_user_units),
):
    """
    Return unit-scoped resumes for a given job position (R1.5).
    Only resumes uploaded to the recruiter's unit(s) for this position are shown.
    Cross-unit resumes are never returned (R1.2).
    """
    if not user_unit_ids:
        return []

    result = await db.execute(
        select(Resume)
        .where(
            Resume.job_position_id == job_id,
            Resume.unit_id.in_(user_unit_ids),
            Resume.parse_status == "completed",
        )
        .order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()

    return [
        {
            "id": r.id,
            "filename": r.filename,
            "candidate_name": r.candidate_name,
            "candidate_email": r.candidate_email,
            "candidate_location": r.candidate_location,
            "total_exp_years": r.total_exp_years,
            "unit_id": r.unit_id,
            "parse_status": r.parse_status,
            "created_at": r.created_at.isoformat(),
        }
        for r in resumes
    ]


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_dict = _job_to_dict(job)

    # Resolve unit name
    if job.business_unit_id:
        unit_result = await db.execute(
            select(BusinessUnit).where(BusinessUnit.id == job.business_unit_id)
        )
        unit = unit_result.scalar_one_or_none()
        job_dict["unit_name"] = unit.unit_name if unit else None
    else:
        job_dict["unit_name"] = None

    # Resolve recruiter name
    if job.recruiter_id:
        rec_result = await db.execute(
            select(User.id, User.name).where(User.id == job.recruiter_id)
        )
        rec = rec_result.first()
        job_dict["recruiter_name"] = rec[1] if rec else None
    else:
        job_dict["recruiter_name"] = None

    # Resolve hiring lead names
    if job.hiring_leads:
        leads_result = await db.execute(
            select(User.id, User.name).where(User.id.in_(job.hiring_leads))
        )
        job_dict["hiring_lead_names"] = [
            {"id": r[0], "name": r[1]} for r in leads_result.fetchall()
        ]
    else:
        job_dict["hiring_lead_names"] = []

    return job_dict


@router.patch("/{job_id}/status")
async def update_job_status(
    job_id: str,
    data: UpdateJobStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    now = datetime.now(timezone.utc)
    if data.action == "activate":
        job.status = "active"
        if data.valid_till:
            try:
                parsed_valid_till = datetime.fromisoformat(data.valid_till.replace("Z", "+00:00"))
                if parsed_valid_till.tzinfo is None:
                    parsed_valid_till = parsed_valid_till.replace(tzinfo=timezone.utc)
                job.valid_till = parsed_valid_till
            except ValueError:
                job.valid_till = now + timedelta(days=30)
        else:
            job.valid_till = now + timedelta(days=30)
    elif data.action == "pause":
        job.status = "paused"
    elif data.action == "fill":
        job.status = "filled"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {data.action}")

    await db.commit()
    await db.refresh(job)
    return _job_to_dict(job)


@router.patch("/{job_id}")
async def update_job(
    job_id: str,
    data: UpdateJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update only provided fields
    if data.job_title is not None:
        job.job_title = data.job_title
    if data.company is not None:
        job.company = data.company
    if data.business_unit_id is not None:
        job.business_unit_id = data.business_unit_id or None
    if data.experience is not None:
        job.experience = data.experience or None
        # Also update required_min_exp_years from the form's experience field
        if data.experience:
            import re as _re2
            _exp_match = _re2.search(r"(\d+)", data.experience)
            if _exp_match:
                job.required_min_exp_years = int(_exp_match.group(1))
    if data.employee_type is not None:
        job.employee_type = data.employee_type or None
    if data.location_office is not None:
        job.location_office = data.location_office or None
    if data.remote_job is not None:
        job.remote_job = data.remote_job
    if data.hiring_leads is not None:
        job.hiring_leads = data.hiring_leads
    if data.recruiter_id is not None:
        job.recruiter_id = data.recruiter_id or None
    if data.valid_till is not None:
        try:
            job.valid_till = datetime.fromisoformat(data.valid_till.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid valid_till date format")

    if data.job_description_text is not None:
        job.job_description_full = data.job_description_text
        # Auto re-parse JD to extract updated skills
        if data.job_description_text.strip():
            try:
                parsed_jd = resume_parser.parse_jd(data.job_description_text)
                job.required_skills = parsed_jd.get("required_skills", job.required_skills)
                job.nice_to_have_skills = parsed_jd.get("nice_to_have_skills", job.nice_to_have_skills)
                # Prefer form experience over AI-parsed
                req_min_exp = parsed_jd.get("required_min_exp_years", job.required_min_exp_years)
                if job.experience:
                    import re as _re3
                    _exp_m = _re3.search(r"(\d+)", job.experience)
                    if _exp_m:
                        req_min_exp = int(_exp_m.group(1))
                job.required_min_exp_years = req_min_exp
                if parsed_jd.get("education_required"):
                    job.education_required = parsed_jd["education_required"]
                if parsed_jd.get("locations_accepted"):
                    job.locations_accepted = parsed_jd["locations_accepted"]
            except Exception as exc:
                logger.warning("Auto re-parse failed after JD text update", error=str(exc))

    await db.commit()
    await db.refresh(job)
    return _job_to_dict(job)


@router.post("/{job_id}/screen", status_code=status.HTTP_202_ACCEPTED)
async def screen_candidates(
    job_id: str,
    data: ScreenRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_unit_ids: list[str] = Depends(get_current_user_units),
):
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Count available resumes in user's unit(s) for progress display
    if user_unit_ids:
        count_filter = or_(
            Resume.user_id == current_user.id,
            Resume.unit_id.in_(user_unit_ids),
        )
    else:
        count_filter = Resume.user_id == current_user.id

    count_result = await db.execute(
        select(func.count(Resume.id)).where(
            count_filter,
            Resume.parse_status == "completed",
        )
    )
    total_resumes = count_result.scalar() or 0

    # Mark as processing before starting background task
    job.screening_status = "processing"
    job.screening_error = None
    await db.commit()

    background_tasks.add_task(
        _screen_candidates, job_id, current_user.id, data.max_candidates, user_unit_ids
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "total_resumes": total_resumes,
        "processed_resumes": 0,
        "created_at": job.created_at.isoformat(),
    }


@router.post("/{job_id}/reparse", status_code=status.HTTP_200_OK)
async def reparse_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-parse a job's JD text to extract skills and requirements (e.g. after LLM was down)."""
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.job_description_full:
        raise HTTPException(status_code=400, detail="No JD text to parse")

    # Try Gemini first, fall back to keyword extraction
    parsed_jd = None
    try:
        parsed_jd = resume_parser.parse_jd(job.job_description_full)
    except Exception as exc:
        logger.warning("Gemini JD re-parse failed, using fallback", job_id=job_id, error=str(exc))

    if not parsed_jd:
        import re as _re
        jd_lower = job.job_description_full.lower()
        _COMMON_SKILLS = [
            "python", "java", "javascript", "typescript", "react", "angular", "vue",
            "node.js", "nodejs", "express", "django", "flask", "fastapi", "spring",
            "aws", "azure", "gcp", "docker", "kubernetes", "sql", "postgresql",
            "mongodb", "redis", "git", "ci/cd", "rest", "graphql", "html", "css",
            "c++", "c#", ".net", "go", "rust", "swift", "kotlin", "ruby", "php",
            "machine learning", "deep learning", "data science", "terraform",
            "jenkins", "linux", "agile", "scrum", "jira", "figma",
        ]
        found_skills = [s for s in _COMMON_SKILLS if s in jd_lower]
        # Try to extract experience from JD text first
        exp_match = _re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?experience", jd_lower)
        fallback_exp = int(exp_match.group(1)) if exp_match else 0
        # If not found in JD text, derive from the form's experience field (e.g. "5-10 yrs" → 5)
        if fallback_exp == 0 and job.experience:
            exp_field_match = _re.search(r"(\d+)", job.experience)
            if exp_field_match:
                fallback_exp = int(exp_field_match.group(1))
        parsed_jd = {
            "required_skills": [
                {"skill": s.title(), "proficiency": "Intermediate", "years_required": 1}
                for s in found_skills[:10]
            ],
            "nice_to_have_skills": [s.title() for s in found_skills[10:]],
            "required_min_exp_years": fallback_exp,
            "_parse_method": "fallback",
        }

    # Update job with re-parsed data
    job.required_skills = parsed_jd.get("required_skills", job.required_skills)
    job.nice_to_have_skills = parsed_jd.get("nice_to_have_skills", job.nice_to_have_skills)

    # Prefer the form's experience field over AI-parsed value
    req_min_exp = parsed_jd.get("required_min_exp_years", job.required_min_exp_years)
    if job.experience:
        import re as _re2
        _exp_match = _re2.search(r"(\d+)", job.experience)
        if _exp_match:
            req_min_exp = int(_exp_match.group(1))
    job.required_min_exp_years = req_min_exp
    if parsed_jd.get("preferred_min_exp_years"):
        job.preferred_min_exp_years = parsed_jd["preferred_min_exp_years"]
    if parsed_jd.get("education_required"):
        job.education_required = parsed_jd["education_required"]
    if parsed_jd.get("locations_accepted"):
        job.locations_accepted = parsed_jd["locations_accepted"]

    await db.commit()
    await db.refresh(job)
    logger.info("Job re-parsed", job_id=job_id, skills=len(job.required_skills))
    return _job_to_dict(job)


@router.get("/{job_id}/screening-status")
async def get_screening_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    count_result = await db.execute(
        select(func.count(ScreeningResult.result_id)).where(
            ScreeningResult.job_id == job_id
        )
    )
    result_count = count_result.scalar() or 0

    count_resumes = await db.execute(
        select(func.count(Resume.id)).where(
            Resume.user_id == current_user.id,
            Resume.parse_status == "completed",
        )
    )
    total_resumes = count_resumes.scalar() or 0

    # Use the tracked screening_status field instead of inferring from result count.
    # This correctly handles failures and zero-result completions.
    screening_status = job.screening_status or ("completed" if result_count > 0 else "idle")

    response = {
        "job_id": job_id,
        "status": screening_status,
        "total_resumes": total_resumes,
        "processed_resumes": result_count,
        "created_at": job.created_at.isoformat(),
    }
    if screening_status == "failed" and job.screening_error:
        response["error"] = job.screening_error
    return response


@router.get("/{job_id}/screening-results")
async def get_screening_results(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify job ownership
    job_result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(ScreeningResult)
        .where(ScreeningResult.job_id == job_id)
        .order_by(ScreeningResult.rank.asc(), ScreeningResult.fit_score.desc())
    )
    results = result.scalars().all()

    return [_result_to_dict(r) for r in results]


@router.post("/{job_id}/clear-screening", status_code=status.HTTP_200_OK)
async def clear_screening_results(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all screening results for a job."""
    job_result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        delete(ScreeningResult).where(ScreeningResult.job_id == job_id)
    )
    await db.commit()
    return {"job_id": job_id, "deleted": result.rowcount}


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    await db.commit()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _job_to_dict(job: JobDescription) -> dict:
    return {
        "job_id": job.job_id,
        "job_title": job.job_title,
        "company": job.company,
        "location": job.location,
        "required_min_exp_years": job.required_min_exp_years,
        "preferred_min_exp_years": job.preferred_min_exp_years,
        "required_skills": job.required_skills,
        "nice_to_have_skills": job.nice_to_have_skills,
        "education_required": job.education_required,
        "locations_accepted": job.locations_accepted,
        "willingness_to_relocate": job.willingness_to_relocate,
        "job_description_full": job.job_description_full,
        "screening_count": job.screening_count,
        "created_at": job.created_at.isoformat(),
        # Lifecycle fields
        "business_unit_id": job.business_unit_id,
        "experience": job.experience,
        "employee_type": job.employee_type,
        "location_office": job.location_office,
        "remote_job": job.remote_job,
        "hiring_leads": job.hiring_leads or [],
        "recruiter_id": job.recruiter_id,
        "valid_till": job.valid_till.isoformat() if job.valid_till else None,
        "status": job.status,
    }


def _result_to_dict(r: ScreeningResult) -> dict:
    return {
        "result_id": r.result_id,
        "resume_id": r.resume_id,
        "job_id": r.job_id,
        "rank": r.rank,
        "fit_score": r.fit_score,
        "status": r.status,
        "passed_knockouts": r.passed_knockouts,
        "knockout_failures": r.knockout_failures,
        "category_scores": {
            "skills_match": r.skills_match_score,
            "experience_relevance": r.experience_relevance_score,
            "career_progression": r.career_progression_score,
            "measurable_achievements": r.achievements_score,
        },
        "strengths": r.strengths,
        "weaknesses": r.weaknesses,
        "match_explanation": r.match_explanation,
        "skills_matched": r.skills_matched,
        "skills_missing": r.skills_missing,
        "candidate_name": r.candidate_name,
        "candidate_email": r.candidate_email,
        "candidate_location": r.candidate_location,
        "total_exp_years": r.total_exp_years,
        "is_shortlisted": r.is_shortlisted,
        "created_at": r.created_at.isoformat(),
        "screening_time_ms": r.screening_time_ms,
    }
