"""
One-time script to re-parse all resumes that were parsed with the old fallback
(missing skills, 0 experience). Uses the improved fallback parser.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.resume import Resume


async def reparse_all():
    from app.api.resumes import _process_resume

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Resume).where(Resume.parse_status == "completed")
        )
        resumes = result.scalars().all()

        # Re-parse ALL resumes to apply corrected experience extraction
        to_reparse = list(resumes)
        for r in to_reparse:
            r.parse_status = "pending"

        await db.commit()
        print(f"Found {len(to_reparse)} resumes to re-parse (out of {len(resumes)} total)")

    # Process each resume
    for i, r in enumerate(to_reparse, 1):
        print(f"  [{i}/{len(to_reparse)}] Re-parsing {r.filename} (id={r.id})...")
        try:
            await _process_resume(r.id, "")
            # Read back updated data
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Resume).where(Resume.id == r.id))
                updated = result.scalar_one_or_none()
                if updated:
                    print(f"    -> name={updated.candidate_name}, exp={updated.total_exp_years}yrs, "
                          f"skills={len(updated.all_skills or [])} found, "
                          f"parse_method={updated.parsed_data.get('_parse_method', 'groq')}")
        except Exception as e:
            print(f"    -> FAILED: {e}")

    print("\nDone! You can now re-run screening.")


if __name__ == "__main__":
    asyncio.run(reparse_all())
