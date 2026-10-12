"""
Resume upload, parsing, and management endpoints.
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.resume import Resume, UploadBatch
from app.models.job import JobDescription
from app.models.unit import UserUnit, BusinessUnit
from app.utils.auth import get_current_user
from app.utils.unit_auth import get_current_user_units
from app.utils.file_handler import (
    extract_text,
    cleanup_file,
    read_upload_file_bytes,
    extract_text_from_bytes,
)
from app.services.resume_parser import resume_parser
from app.services.embedding_service import embedding_service
from app.services.pinecone_service import pinecone_service
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/resumes", tags=["Resumes"])


# ─── Background: Parse + Embed a single resume ────────────────────────────────

async def _process_resume(resume_id: str, db_url: str) -> None:
    """Background task: parse + embed a resume after upload."""
    from app.database import AsyncSessionLocal
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Resume).where(Resume.id == resume_id))
            resume = result.scalar_one_or_none()
            if not resume:
                return

            # Update parse status
            resume.parse_status = "processing"
            await db.commit()

            # Extract text — prefer BYTEA, fall back to disk path for pre-migration resumes
            text = ""
            try:
                if resume.resume_file:
                    text = extract_text_from_bytes(
                        resume.resume_file,
                        resume.file_mimetype or resume.content_type,
                    )
                elif resume.file_path:
                    text = extract_text(resume.file_path, resume.content_type)
            except Exception as text_exc:
                logger.warning("Text extraction failed", resume_id=resume_id, error=str(text_exc))

            if not text and not resume.resume_file and not resume.file_path:
                logger.error("Resume has no file data", resume_id=resume_id)
                resume.parse_status = "failed"
                await db.commit()
                return

            # Parse with LLM (graceful fallback if API is down)
            parsed = None
            try:
                parsed = resume_parser.parse_resume(text)
            except Exception as parse_exc:
                logger.warning(
                    "LLM parsing failed, using fallback",
                    resume_id=resume_id,
                    error=str(parse_exc),
                )

            if not parsed:
                # Fallback: extract info from raw text using regex heuristics
                import re as _re
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                name_guess = lines[0] if lines else resume.filename
                email_match = _re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)

                # Extract experience years from text
                text_lower = text.lower()
                fallback_exp = 0.0

                # Strategy 1: Look for explicit "X years of experience/expertise" statements
                exp_patterns = [
                    r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:total\s+)?(?:professional\s+)?(?:experience|expertise)",
                    r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:in|of)\s+(?:software|it|development|engineering|web|data)",
                ]
                for pat in exp_patterns:
                    m = _re.search(pat, text_lower)
                    if m:
                        fallback_exp = float(m.group(1))
                        break

                # Strategy 2: Sum up "Total Experience X.X years" entries (e.g. Naukri-style resumes)
                if fallback_exp == 0:
                    total_exp_entries = _re.findall(
                        r"total\s+experience[:\s]*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
                        text_lower,
                    )
                    if total_exp_entries:
                        fallback_exp = sum(float(x) for x in total_exp_entries)

                # Round to nearest 0.5
                fallback_exp = round(fallback_exp * 2) / 2

                # Extract skills from text using keyword matching
                _COMMON_SKILLS = [
                    "python", "java", "javascript", "typescript", "react", "angular", "vue",
                    "node.js", "nodejs", "express", "django", "flask", "fastapi", "spring",
                    "aws", "azure", "gcp", "docker", "kubernetes", "sql", "postgresql",
                    "mongodb", "redis", "git", "ci/cd", "rest", "graphql", "html", "css",
                    "c++", "c#", ".net", "go", "rust", "swift", "kotlin", "ruby", "php",
                    "machine learning", "deep learning", "data science", "terraform",
                    "jenkins", "linux", "agile", "scrum", "jira", "figma",
                ]
                found_skills = [s.title() for s in _COMMON_SKILLS if s in text_lower]

                # Extract phone
                phone_match = _re.search(r"[\+]?\d[\d\s\-]{8,14}\d", text)

                # Extract location (look for common Indian cities)
                location_guess = None
                _CITIES = ["pune", "mumbai", "bangalore", "bengaluru", "hyderabad",
                           "chennai", "delhi", "noida", "gurgaon", "gurugram",
                           "kolkata", "ahmedabad", "jaipur", "kothrud", "baner",
                           "hinjewadi", "wakad", "remote"]
                for city in _CITIES:
                    if city in text_lower:
                        location_guess = city.title()
                        break

                parsed = {
                    "candidate_name": name_guess[:100],
                    "email": email_match.group() if email_match else None,
                    "phone": phone_match.group().strip() if phone_match else None,
                    "location": location_guess,
                    "total_exp_years": fallback_exp,
                    "recent_skills": found_skills[:15],
                    "all_skills": found_skills,
                    "education": [],
                    "experience": [],
                    "employment_gaps": [],
                    "certifications": [],
                    "_parse_method": "fallback",
                }

            # Generate embeddings (best-effort)
            pinecone_id = None
            try:
                embeddings = embedding_service.embed_resume(parsed)
                metadata = {
                    "candidate_name": parsed.get("candidate_name", ""),
                    "location": parsed.get("location", ""),
                    "total_exp_years": parsed.get("total_exp_years", 0),
                    "all_skills": parsed.get("all_skills", [])[:20],
                    "user_id": resume.user_id,
                    "unit_id": resume.unit_id or "",
                    "job_position_id": resume.job_position_id or "",
                }
                pinecone_id = pinecone_service.upsert_resume(
                    resume_id, embeddings, metadata
                )
            except Exception as embed_exc:
                logger.warning("Embedding/Pinecone failed", resume_id=resume_id, error=str(embed_exc))

            # Update resume record — always mark completed
            resume.parsed_data = parsed
            resume.parse_status = "completed"
            resume.candidate_name = parsed.get("candidate_name")
            resume.candidate_email = parsed.get("email")
            resume.candidate_location = parsed.get("location")
            resume.total_exp_years = parsed.get("total_exp_years", 0)
            resume.recent_skills = parsed.get("recent_skills", [])
            resume.all_skills = parsed.get("all_skills", [])
            resume.pinecone_id = pinecone_id

            await db.commit()
            logger.info("Resume processed", resume_id=resume_id, name=parsed.get("candidate_name"))

        except Exception as exc:
            logger.error("Resume processing failed", resume_id=resume_id, error=str(exc))
            async with AsyncSessionLocal() as err_db:
                err_result = await err_db.execute(select(Resume).where(Resume.id == resume_id))
                err_resume = err_result.scalar_one_or_none()
                if err_resume:
                    err_resume.parse_status = "failed"
                    await err_db.commit()


async def _process_batch(batch_id: str) -> None:
    """Process all resumes in a batch concurrently."""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Resume).where(Resume.batch_id == batch_id)
        )
        resumes = result.scalars().all()

    # Process up to 5 concurrently
    semaphore = asyncio.Semaphore(5)

    async def process_with_limit(resume_id: str):
        async with semaphore:
            await _process_resume(resume_id, "")

    await asyncio.gather(*[process_with_limit(r.id) for r in resumes])

    # Mark batch as complete
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UploadBatch).where(UploadBatch.batch_id == batch_id)
        )
        batch = result.scalar_one_or_none()
        if batch:
            batch.status = "completed"
            batch.processed_files = len(resumes)
            await db.commit()


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/bulk-upload", status_code=status.HTTP_202_ACCEPTED)
async def bulk_upload(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    unit_id: str | None = Form(None),
    job_position_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 files per upload")

    # Derive unit_id from job's business_unit_id if not provided
    if not unit_id:
        job_row = await db.execute(
            select(JobDescription.business_unit_id).where(
                JobDescription.job_id == job_position_id
            )
        )
        unit_id = job_row.scalar_one_or_none()

    # Validate user belongs to the unit (R1.2 enforcement at upload time)
    if unit_id:
        unit_check = await db.execute(
            select(UserUnit).where(
                UserUnit.user_id == current_user.id,
                UserUnit.unit_id == unit_id,
            )
        )
        if not unit_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this business unit",
            )

    # Create batch record
    batch = UploadBatch(
        user_id=current_user.id,
        total_files=len(files),
        status="processing",
    )
    db.add(batch)
    await db.flush()
    await db.refresh(batch)

    # Read files into memory and create resume records
    resume_ids = []
    skipped_files = []
    for file in files:
        try:
            file_bytes, content_type = await read_upload_file_bytes(file)

            # Dedup: check SHA-256 hash per job
            content_hash = hashlib.sha256(file_bytes).hexdigest()
            dup_result = await db.execute(
                select(Resume.id).where(
                    Resume.content_hash == content_hash,
                    Resume.job_position_id == job_position_id,
                ).limit(1)
            )
            if dup_result.scalar_one_or_none():
                skipped_files.append(file.filename or "resume")
                continue

            resume = Resume(
                user_id=current_user.id,
                batch_id=batch.batch_id,
                unit_id=unit_id,
                job_position_id=job_position_id,
                filename=file.filename or "resume",
                file_path=None,           # deprecated — no disk storage
                resume_file=file_bytes,   # stored in PostgreSQL BYTEA
                file_mimetype=content_type,
                file_size=len(file_bytes),
                content_type=content_type,
                content_hash=content_hash,
                upload_status="completed",
                parse_status="pending",
            )
            db.add(resume)
            await db.flush()
            resume_ids.append(resume.id)
        except HTTPException:
            batch.failed_files += 1

    await db.commit()
    await db.refresh(batch)

    # Trigger background processing
    background_tasks.add_task(_process_batch, batch.batch_id)

    return {
        "batch_id": batch.batch_id,
        "total_files": batch.total_files,
        "processed_files": 0,
        "failed_files": batch.failed_files,
        "skipped_files": skipped_files,
        "skipped_count": len(skipped_files),
        "status": "processing",
        "created_at": batch.created_at.isoformat(),
    }


@router.get("/batch/{batch_id}")
async def get_batch_status(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UploadBatch).where(
            UploadBatch.batch_id == batch_id,
            UploadBatch.user_id == current_user.id,
        )
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Count processed resumes
    count_result = await db.execute(
        select(func.count(Resume.id)).where(
            Resume.batch_id == batch_id,
            Resume.parse_status == "completed",
        )
    )
    processed = count_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(Resume.id)).where(
            Resume.batch_id == batch_id,
            Resume.parse_status == "failed",
        )
    )
    failed = failed_result.scalar() or 0

    total = batch.total_files
    all_done = (processed + failed) >= total

    return {
        "batch_id": batch.batch_id,
        "total_files": total,
        "processed_files": processed,
        "failed_files": failed,
        "status": "completed" if all_done else "processing",
        "created_at": batch.created_at.isoformat(),
    }


@router.get("")
async def list_resumes(
    page: int = 1,
    page_size: int = 20,
    parse_status: str | None = None,
    unit_id: str | None = None,
    job_position_id: str | None = None,
    is_indexed: bool | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_unit_ids: list[str] = Depends(get_current_user_units),
):
    offset = (page - 1) * page_size

    # Show resumes the user owns OR resumes in their unit(s) (R1.1 intra-unit visibility)
    if user_unit_ids:
        access_filter = or_(
            Resume.user_id == current_user.id,
            Resume.unit_id.in_(user_unit_ids),
        )
    else:
        access_filter = Resume.user_id == current_user.id

    # Build list of filter conditions
    conditions = [access_filter]

    if parse_status:
        conditions.append(Resume.parse_status == parse_status)
    if unit_id:
        conditions.append(Resume.unit_id == unit_id)
    if job_position_id:
        conditions.append(Resume.job_position_id == job_position_id)
    if is_indexed is True:
        conditions.append(Resume.pinecone_id.isnot(None))
    elif is_indexed is False:
        conditions.append(Resume.pinecone_id.is_(None))
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                Resume.candidate_name.ilike(search_term),
                Resume.filename.ilike(search_term),
            )
        )

    from sqlalchemy import and_
    combined_filter = and_(*conditions)

    count_result = await db.execute(
        select(func.count(Resume.id)).where(combined_filter)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Resume)
        .where(combined_filter)
        .order_by(Resume.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    resumes = result.scalars().all()

    # Resolve job titles and unit names in bulk
    job_ids = {r.job_position_id for r in resumes if r.job_position_id}
    unit_ids = {r.unit_id for r in resumes if r.unit_id}

    job_titles = {}
    if job_ids:
        rows = await db.execute(
            select(JobDescription.job_id, JobDescription.job_title)
            .where(JobDescription.job_id.in_(job_ids))
        )
        job_titles = dict(rows.fetchall())

    unit_names = {}
    if unit_ids:
        rows = await db.execute(
            select(BusinessUnit.id, BusinessUnit.unit_name)
            .where(BusinessUnit.id.in_(unit_ids))
        )
        unit_names = dict(rows.fetchall())

    return {
        "items": [
            {
                "id": r.id,
                "filename": r.filename,
                "file_size": r.file_size,
                "upload_status": r.upload_status,
                "parse_status": r.parse_status,
                "candidate_name": r.candidate_name,
                "candidate_email": r.candidate_email,
                "unit_id": r.unit_id,
                "unit_name": unit_names.get(r.unit_id),
                "job_position_id": r.job_position_id,
                "job_title": job_titles.get(r.job_position_id),
                "is_indexed": r.pinecone_id is not None,
                "created_at": r.created_at.isoformat(),
            }
            for r in resumes
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{resume_id}/file")
async def get_resume_file(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_unit_ids: list[str] = Depends(get_current_user_units),
):
    """
    Serve resume file bytes from PostgreSQL BYTEA storage.
    Access: user owns the resume OR user shares the resume's unit (R1.6).
    Uses 'inline' disposition so browsers open PDFs in their viewer.
    """
    if user_unit_ids:
        access_filter = or_(
            Resume.user_id == current_user.id,
            Resume.unit_id.in_(user_unit_ids),
        )
    else:
        access_filter = Resume.user_id == current_user.id

    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, access_filter)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.resume_file:
        raise HTTPException(
            status_code=404,
            detail="File content not available (may be stored on disk — re-upload to enable preview)",
        )

    media_type = resume.file_mimetype or resume.content_type or "application/octet-stream"
    filename = resume.filename or "resume"
    return Response(
        content=resume.resume_file,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{resume_id}")
async def get_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_unit_ids: list[str] = Depends(get_current_user_units),
):
    if user_unit_ids:
        access_filter = or_(
            Resume.user_id == current_user.id,
            Resume.unit_id.in_(user_unit_ids),
        )
    else:
        access_filter = Resume.user_id == current_user.id

    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, access_filter)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {
        "id": resume.id,
        "filename": resume.filename,
        "file_size": resume.file_size,
        "upload_status": resume.upload_status,
        "parse_status": resume.parse_status,
        "parsed_data": resume.parsed_data,
        "candidate_name": resume.candidate_name,
        "unit_id": resume.unit_id,
        "job_position_id": resume.job_position_id,
        "created_at": resume.created_at.isoformat(),
    }


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Remove from Pinecone
    pinecone_service.delete_resume(resume_id)

    # Only clean up disk file if one exists (backward compat for pre-BYTEA resumes)
    if resume.file_path:
        cleanup_file(resume.file_path)

    await db.delete(resume)
    await db.commit()


@router.post("/{resume_id}/parse", status_code=status.HTTP_202_ACCEPTED)
async def reparse_resume(
    resume_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume.parse_status = "pending"
    await db.commit()
    background_tasks.add_task(_process_resume, resume_id, "")
    return {"message": "Re-parse initiated", "resume_id": resume_id}


@router.post("/reparse-all", status_code=status.HTTP_202_ACCEPTED)
async def reparse_all_resumes(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-parse all resumes that were parsed with the fallback method (missing skills/experience)."""
    result = await db.execute(
        select(Resume).where(
            Resume.user_id == current_user.id,
            Resume.parse_status == "completed",
        )
    )
    resumes = result.scalars().all()

    # Only re-parse resumes that used fallback (have _parse_method or have 0 skills)
    to_reparse = []
    for r in resumes:
        if not r.parsed_data:
            to_reparse.append(r)
        elif r.parsed_data.get("_parse_method") == "fallback":
            to_reparse.append(r)
        elif not r.parsed_data.get("all_skills") and not r.parsed_data.get("recent_skills"):
            to_reparse.append(r)

    for r in to_reparse:
        r.parse_status = "pending"
    await db.commit()

    for r in to_reparse:
        background_tasks.add_task(_process_resume, r.id, "")

    return {
        "message": f"Re-parsing {len(to_reparse)} resumes",
        "total": len(to_reparse),
    }


class BulkResumeRequest(BaseModel):
    resume_ids: list[str]


@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_resumes(
    data: BulkResumeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_unit_ids: list[str] = Depends(get_current_user_units),
):
    """Delete multiple resumes at once."""
    if not data.resume_ids:
        raise HTTPException(status_code=400, detail="No resume IDs provided")

    if user_unit_ids:
        access_filter = or_(
            Resume.user_id == current_user.id,
            Resume.unit_id.in_(user_unit_ids),
        )
    else:
        access_filter = Resume.user_id == current_user.id

    result = await db.execute(
        select(Resume).where(Resume.id.in_(data.resume_ids), access_filter)
    )
    resumes = result.scalars().all()

    for r in resumes:
        pinecone_service.delete_resume(r.id)
        if r.file_path:
            cleanup_file(r.file_path)
        await db.delete(r)

    await db.commit()
    return {"deleted": len(resumes)}


@router.post("/bulk-reparse", status_code=status.HTTP_202_ACCEPTED)
async def bulk_reparse_resumes(
    data: BulkResumeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_unit_ids: list[str] = Depends(get_current_user_units),
):
    """Re-parse multiple resumes at once."""
    if not data.resume_ids:
        raise HTTPException(status_code=400, detail="No resume IDs provided")

    if user_unit_ids:
        access_filter = or_(
            Resume.user_id == current_user.id,
            Resume.unit_id.in_(user_unit_ids),
        )
    else:
        access_filter = Resume.user_id == current_user.id

    result = await db.execute(
        select(Resume).where(Resume.id.in_(data.resume_ids), access_filter)
    )
    resumes = result.scalars().all()

    for r in resumes:
        r.parse_status = "pending"
    await db.commit()

    for r in resumes:
        background_tasks.add_task(_process_resume, r.id, "")

    return {
        "message": f"Re-parsing {len(resumes)} resumes",
        "total": len(resumes),
    }
