"""Fix experience values for all resumes using the corrected extraction logic."""
import asyncio
import sys
import os
import re
import logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.resume import Resume
from app.utils.file_handler import extract_text_from_bytes


def extract_experience(text: str) -> float:
    """Extract total experience years from resume text."""
    text_lower = text.lower()
    fallback_exp = 0.0

    # Strategy 1: Explicit "X years of experience/expertise"
    exp_patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:total\s+)?(?:professional\s+)?(?:experience|expertise)",
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:in|of)\s+(?:software|it|development|engineering|web|data)",
    ]
    for pat in exp_patterns:
        m = re.search(pat, text_lower)
        if m:
            fallback_exp = float(m.group(1))
            break

    # Strategy 2: Sum "Total Experience X.X years" entries (Naukri-style resumes)
    if fallback_exp == 0:
        total_exp_entries = re.findall(
            r"total\s+experience[:\s]*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
            text_lower,
        )
        if total_exp_entries:
            fallback_exp = sum(float(x) for x in total_exp_entries)

    # Round to nearest 0.5
    fallback_exp = round(fallback_exp * 2) / 2
    return fallback_exp


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Resume))
        resumes = result.scalars().all()

        print(f"Processing {len(resumes)} resumes...\n")

        for r in resumes:
            text = ""
            try:
                if r.resume_file:
                    text = extract_text_from_bytes(
                        r.resume_file, r.file_mimetype or r.content_type
                    )
            except Exception:
                pass

            if not text:
                print(f"  {r.filename}: [no text] - skipping")
                continue

            new_exp = extract_experience(text)
            old_exp = r.total_exp_years or 0

            # Also update parsed_data
            if r.parsed_data:
                r.parsed_data = {**r.parsed_data, "total_exp_years": new_exp}

            r.total_exp_years = new_exp

            changed = "CHANGED" if abs(old_exp - new_exp) > 0.01 else "ok"
            print(f"  {r.filename}: {old_exp} -> {new_exp} yrs [{changed}]")

        await db.commit()
        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
