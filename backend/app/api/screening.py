"""
Screening results management: shortlisting, export, bulk actions, PDF reports.
"""
from __future__ import annotations

import csv
import io
import re as _re
from datetime import date as _date

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.job import JobDescription
from app.models.resume import Resume
from app.models.screening import ScreeningResult
from app.utils.auth import get_current_user

_logger = structlog.get_logger()

router = APIRouter(prefix="/screening-results", tags=["Screening Results"])


class ResultActionRequest(BaseModel):
    action: str  # "shortlist" | "reject"


class ExportRequest(BaseModel):
    job_id: str
    format: str = "csv"  # "csv" | "pdf"


@router.get("")
async def list_all_results(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all screening results for the current user's jobs."""
    # Get user's job IDs
    job_result = await db.execute(
        select(JobDescription.job_id).where(
            JobDescription.user_id == current_user.id
        )
    )
    job_ids = [row[0] for row in job_result.fetchall()]

    if not job_ids:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count(ScreeningResult.result_id)).where(
            ScreeningResult.job_id.in_(job_ids)
        )
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(ScreeningResult)
        .where(ScreeningResult.job_id.in_(job_ids))
        .order_by(ScreeningResult.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    results = result.scalars().all()

    return {
        "items": [_result_to_dict(r) for r in results],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{result_id}/pdf")
async def generate_candidate_pdf(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a dark-themed PDF candidate analysis report."""
    from app.services.pdf_analysis_service import pdf_analysis_service
    from app.services.pdf_builder import PDFReportBuilder

    # 1. Fetch screening result
    result = await db.execute(
        select(ScreeningResult).where(ScreeningResult.result_id == result_id)
    )
    screening = result.scalar_one_or_none()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening result not found")

    # 2. Fetch job description & verify ownership
    job_result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == screening.job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=403, detail="You do not have access to this screening result")

    # 3. Fetch resume for parsed_data
    resume_result = await db.execute(
        select(Resume).where(Resume.id == screening.resume_id)
    )
    resume = resume_result.scalar_one_or_none()
    if not resume or not resume.parsed_data:
        raise HTTPException(status_code=422, detail="Resume has not been parsed yet. Cannot generate report.")

    # 4. Build data dicts for the analysis service
    screening_dict = {
        "candidate_name": screening.candidate_name,
        "candidate_email": screening.candidate_email,
        "candidate_location": screening.candidate_location,
        "total_exp_years": screening.total_exp_years,
        "fit_score": screening.fit_score,
        "status": screening.status,
        "skills_match_score": screening.skills_match_score,
        "experience_relevance_score": screening.experience_relevance_score,
        "career_progression_score": screening.career_progression_score,
        "achievements_score": screening.achievements_score,
        "strengths": screening.strengths or [],
        "weaknesses": screening.weaknesses or [],
        "match_explanation": screening.match_explanation or "",
        "skills_matched": screening.skills_matched or [],
        "skills_missing": screening.skills_missing or [],
    }

    job_dict = {
        "job_title": job.job_title,
        "company": job.company,
        "location": job.location,
        "required_min_exp_years": job.required_min_exp_years,
        "required_skills": job.required_skills or [],
        "nice_to_have_skills": job.nice_to_have_skills or [],
        "education_required": job.education_required,
        "job_description_full": job.job_description_full,
    }

    parsed_data = resume.parsed_data

    # 5. Generate report data (deterministic + AI enrichment)
    try:
        report_data = pdf_analysis_service.generate_report_data(
            screening_result=screening_dict,
            parsed_data=parsed_data,
            job_data=job_dict,
        )
    except Exception as exc:
        _logger.error("PDF analysis failed", error=str(exc), result_id=result_id)
        raise HTTPException(status_code=500, detail="Failed to generate report analysis")

    # 6. Build PDF
    try:
        builder = PDFReportBuilder()
        pdf_bytes = builder.build(report_data)
    except Exception as exc:
        _logger.error("PDF rendering failed", error=str(exc), result_id=result_id)
        raise HTTPException(status_code=500, detail="Failed to render PDF report")

    # 7. Generate filename
    name = (screening.candidate_name or "Candidate").strip()
    name_clean = _re.sub(r"[^a-zA-Z0-9]", "", name)
    role_clean = _re.sub(r"[^a-zA-Z0-9]", "", job.job_title or "Role")
    today = _date.today().isoformat()
    filename = f"HireFlow_{name_clean}_{role_clean}_{today}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


@router.get("/{result_id}")
async def get_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScreeningResult).where(ScreeningResult.result_id == result_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Result not found")
    return _result_to_dict(r)


@router.post("/{result_id}/actions")
async def update_result_action(
    result_id: str,
    data: ResultActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScreeningResult).where(ScreeningResult.result_id == result_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Result not found")

    if data.action == "shortlist":
        r.is_shortlisted = True
    elif data.action == "reject":
        r.is_shortlisted = False
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {data.action}")

    await db.commit()
    return {"message": f"Candidate {data.action}ed successfully"}


@router.post("/export")
async def export_results(
    data: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify job ownership
    job_result = await db.execute(
        select(JobDescription).where(
            JobDescription.job_id == data.job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(ScreeningResult)
        .where(ScreeningResult.job_id == data.job_id)
        .order_by(ScreeningResult.rank.asc(), ScreeningResult.fit_score.desc())
    )
    results = result.scalars().all()

    if data.format == "csv":
        return _export_csv(results, job.job_title)
    else:
        raise HTTPException(status_code=400, detail="Only CSV export is currently supported")


def _export_csv(results: list[ScreeningResult], job_title: str) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)

    # Headers
    writer.writerow([
        "Rank", "Name", "Email", "Location", "Experience (yrs)",
        "Fit Score", "Status", "Passed Filters",
        "Skills Match", "Experience Relevance", "Career Progression", "Achievements",
        "Strengths", "Gaps", "Explanation",
    ])

    for r in results:
        writer.writerow([
            r.rank if r.rank else "N/A",
            r.candidate_name or "",
            r.candidate_email or "",
            r.candidate_location or "",
            r.total_exp_years,
            r.fit_score,
            r.status,
            "Yes" if r.passed_knockouts else "No",
            r.skills_match_score,
            r.experience_relevance_score,
            r.career_progression_score,
            r.achievements_score,
            " | ".join(r.strengths or []),
            " | ".join(r.weaknesses or []),
            r.match_explanation or "",
        ])

    output.seek(0)
    filename = f"shortlist_{job_title.replace(' ', '_')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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
