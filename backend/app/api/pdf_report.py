"""
PDF Report endpoint — generates a dark-themed candidate analysis PDF.
"""
from __future__ import annotations

import re
from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.job import JobDescription
from app.models.resume import Resume
from app.models.screening import ScreeningResult
from app.utils.auth import get_current_user
from app.services.pdf_analysis_service import pdf_analysis_service
from app.services.pdf_builder import PDFReportBuilder

logger = structlog.get_logger()

router = APIRouter(prefix="/screening-results", tags=["PDF Reports"])


@router.get("/{result_id}/pdf")
async def generate_candidate_pdf(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a dark-themed PDF candidate analysis report."""

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
        logger.error("PDF analysis failed", error=str(exc), result_id=result_id)
        raise HTTPException(status_code=500, detail="Failed to generate report analysis")

    # 6. Build PDF
    try:
        builder = PDFReportBuilder()
        pdf_bytes = builder.build(report_data)
    except Exception as exc:
        logger.error("PDF rendering failed", error=str(exc), result_id=result_id)
        raise HTTPException(status_code=500, detail="Failed to render PDF report")

    # 7. Generate filename
    name = (screening.candidate_name or "Candidate").strip()
    name_clean = re.sub(r"[^a-zA-Z0-9]", "", name)
    role_clean = re.sub(r"[^a-zA-Z0-9]", "", job.job_title or "Role")
    today = date.today().isoformat()
    filename = f"HireFlow_{name_clean}_{role_clean}_{today}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
