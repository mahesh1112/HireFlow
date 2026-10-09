"""
Admin endpoints for stats, logs, and system management.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.models.job import JobDescription
from app.models.screening import ScreeningResult
from app.utils.auth import get_current_user
from app.services.pinecone_service import pinecone_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics for the current recruiter."""
    # Total resumes
    resumes_count = await db.execute(
        select(func.count(Resume.id)).where(Resume.user_id == current_user.id)
    )
    total_resumes = resumes_count.scalar() or 0

    # Total jobs
    jobs_count = await db.execute(
        select(func.count(JobDescription.job_id)).where(
            JobDescription.user_id == current_user.id
        )
    )
    total_jobs = jobs_count.scalar() or 0

    # Get user's job IDs for screening stats
    job_ids_result = await db.execute(
        select(JobDescription.job_id).where(JobDescription.user_id == current_user.id)
    )
    job_ids = [row[0] for row in job_ids_result.fetchall()]

    total_screenings = 0
    total_shortlisted = 0
    avg_fit_score = 0.0
    shortlist_rate = 0.0
    top_skills_matched = []
    top_skills_missing = []

    if job_ids:
        # Total screenings
        screening_count = await db.execute(
            select(func.count(ScreeningResult.result_id)).where(
                ScreeningResult.job_id.in_(job_ids)
            )
        )
        total_screenings = screening_count.scalar() or 0

        # Shortlisted
        shortlisted_count = await db.execute(
            select(func.count(ScreeningResult.result_id)).where(
                ScreeningResult.job_id.in_(job_ids),
                ScreeningResult.is_shortlisted == True,  # noqa
            )
        )
        total_shortlisted = shortlisted_count.scalar() or 0

        # Avg fit score (passed candidates only)
        avg_result = await db.execute(
            select(func.avg(ScreeningResult.fit_score)).where(
                ScreeningResult.job_id.in_(job_ids),
                ScreeningResult.passed_knockouts == True,  # noqa
            )
        )
        avg_fit_score = round(float(avg_result.scalar() or 0), 1)

        # Shortlist rate
        passed_count = await db.execute(
            select(func.count(ScreeningResult.result_id)).where(
                ScreeningResult.job_id.in_(job_ids),
                ScreeningResult.passed_knockouts == True,  # noqa
            )
        )
        passed = passed_count.scalar() or 0
        shortlist_rate = round((passed / total_screenings * 100) if total_screenings > 0 else 0, 1)

        # Top skills (aggregate from results)
        results_sample = await db.execute(
            select(ScreeningResult.skills_matched, ScreeningResult.skills_missing)
            .where(ScreeningResult.job_id.in_(job_ids))
            .limit(100)
        )
        matched_counts: dict[str, int] = {}
        missing_counts: dict[str, int] = {}
        total_results = 0

        for row in results_sample.fetchall():
            total_results += 1
            for sm in (row[0] or []):
                skill = sm.get("required_skill", "")
                if skill:
                    matched_counts[skill] = matched_counts.get(skill, 0) + 1
            for sm in (row[1] or []):
                skill = sm.get("required_skill", "")
                if skill:
                    missing_counts[skill] = missing_counts.get(skill, 0) + 1

        if total_results > 0:
            top_skills_matched = sorted(
                [
                    {"skill": k, "percentage": round(v / total_results * 100)}
                    for k, v in matched_counts.items()
                ],
                key=lambda x: x["percentage"],
                reverse=True,
            )[:8]
            top_skills_missing = sorted(
                [
                    {"skill": k, "percentage": round(v / total_results * 100)}
                    for k, v in missing_counts.items()
                ],
                key=lambda x: x["percentage"],
                reverse=True,
            )[:8]

    # Recent jobs
    recent_jobs_result = await db.execute(
        select(JobDescription)
        .where(JobDescription.user_id == current_user.id)
        .order_by(JobDescription.created_at.desc())
        .limit(5)
    )
    recent_jobs = recent_jobs_result.scalars().all()

    return {
        "total_resumes": total_resumes,
        "total_jobs": total_jobs,
        "total_screenings": total_screenings,
        "total_shortlisted": total_shortlisted,
        "avg_fit_score": avg_fit_score,
        "shortlist_rate": shortlist_rate,
        "recent_jobs": [
            {
                "job_id": j.job_id,
                "job_title": j.job_title,
                "screening_count": j.screening_count,
                "created_at": j.created_at.isoformat(),
            }
            for j in recent_jobs
        ],
        "top_skills_matched": top_skills_matched,
        "top_skills_missing": top_skills_missing,
    }


@router.get("/logs")
async def get_logs(
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
):
    """Return activity log (stub — would integrate with structured logging in production)."""
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "message": "Log streaming available in production via structured logging.",
    }


@router.post("/reprocess")
async def reprocess_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-queue failed resumes for processing."""
    from app.models.resume import Resume
    result = await db.execute(
        select(Resume).where(
            Resume.user_id == current_user.id,
            Resume.parse_status == "failed",
        )
    )
    failed = result.scalars().all()
    for r in failed:
        r.parse_status = "pending"
    await db.commit()
    return {"message": f"Queued {len(failed)} failed resumes for reprocessing"}
