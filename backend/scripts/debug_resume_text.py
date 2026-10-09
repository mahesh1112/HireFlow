"""Debug: print extracted text from each resume to see what patterns exist."""
import asyncio
import sys
import os
import logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.resume import Resume
from app.utils.file_handler import extract_text_from_bytes
import re


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Resume).where(Resume.parse_status == "completed")
        )
        resumes = result.scalars().all()

    for r in resumes:
      try:
        print(f"\n{'='*60}")
        print(f"FILE: {r.filename}")
        print(f"CURRENT total_exp_years: {r.total_exp_years}")

        text = ""
        if r.resume_file:
            try:
                text = extract_text_from_bytes(r.resume_file, r.file_mimetype or r.content_type)
            except Exception as e:
                print(f"  [text extraction failed: {e}]")
                continue

        if not text:
            print("  [no text extracted]")
            continue

        text_lower = text.lower()

        # Show experience-related lines
        print(f"\nExperience-related lines:")
        for line in text.split("\n"):
            line_s = line.strip()
            if not line_s:
                continue
            ll = line_s.lower()
            if any(kw in ll for kw in ["experience", "years", "yrs", "exp"]):
                print(f"  >>> {line_s}")

        # Show all years found
        year_matches = re.findall(r"\b(20\d{2}|19\d{2})\b", text)
        print(f"\nYears found in text: {year_matches}")
        if year_matches:
            years = [int(y) for y in year_matches]
            print(f"  min={min(years)}, max={max(years)}, span={max(years)-min(years)}")

        # Test the explicit patterns
        exp_patterns = [
            (r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:total\s+)?(?:professional\s+)?experience", "pattern1"),
            (r"(?:total|overall|professional)\s+(?:experience|exp)[:\s]*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", "pattern2"),
            (r"experience[:\s]*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", "pattern3"),
            (r"total\s+experience[:\s]*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", "pattern4"),
        ]
        print(f"\nPattern matches:")
        for pat, name in exp_patterns:
            m = re.search(pat, text_lower)
            if m:
                print(f"  {name}: matched '{m.group()}' -> {m.group(1)}")
            else:
                print(f"  {name}: no match")
      except Exception as e:
        print(f"  [ERROR: {e}]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
