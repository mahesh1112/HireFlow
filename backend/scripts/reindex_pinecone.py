"""
One-time Pinecone re-indexing: re-upserts all parsed resumes with unit_id in metadata.

Run ONCE after deploying Gap 11.13 changes. Required so existing Pinecone vectors
(which only have user_id) are replaced by vectors with unit_id, enabling
unit-scoped semantic search filtering.

Usage:
    cd /app
    python -m scripts.reindex_pinecone
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.resume import Resume
from app.services.pinecone_service import pinecone_service
from app.services.embedding_service import embedding_service


async def reindex() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Resume).where(
                Resume.parse_status == "completed",
                Resume.parsed_data.isnot(None),
            )
        )
        resumes = result.scalars().all()

    print(f"Re-indexing {len(resumes)} parsed resumes in Pinecone with unit_id metadata")

    success = 0
    failed = 0

    for r in resumes:
        try:
            embeddings = embedding_service.embed_resume(r.parsed_data)
            metadata = {
                "candidate_name": r.candidate_name or "",
                "location": r.candidate_location or "",
                "total_exp_years": r.total_exp_years or 0,
                "all_skills": (r.all_skills or [])[:20],
                "user_id": r.user_id,
                "unit_id": r.unit_id or "",
                "job_position_id": r.job_position_id or "",
            }
            pinecone_service.upsert_resume(r.id, embeddings, metadata)
            success += 1
            if success % 10 == 0:
                print(f"  Re-indexed {success}/{len(resumes)}…")
        except Exception as exc:
            print(f"  ERROR for resume {r.id}: {exc}")
            failed += 1

    print(f"\nRe-indexing complete: {success} succeeded, {failed} failed")


if __name__ == "__main__":
    asyncio.run(reindex())
