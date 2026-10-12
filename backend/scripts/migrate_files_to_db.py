"""
One-time migration: reads resume files from disk into resumes.resume_file (BYTEA).

Run ONCE after deploying the new schema columns (unit_id, job_position_id, resume_file, file_mimetype).

Usage:
    cd /app
    python -m scripts.migrate_files_to_db
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.resume import Resume


async def migrate() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Resume).where(
                Resume.file_path.isnot(None),
                Resume.resume_file.is_(None),
            )
        )
        resumes = result.scalars().all()
        print(f"Found {len(resumes)} resumes to migrate from disk to BYTEA")

        migrated = 0
        skipped = 0

        for r in resumes:
            try:
                with open(r.file_path, "rb") as f:
                    r.resume_file = f.read()
                r.file_mimetype = r.content_type
                migrated += 1
                if migrated % 10 == 0:
                    print(f"  Migrated {migrated}/{len(resumes)}…")
            except FileNotFoundError:
                print(f"  WARN: File not found for resume {r.id}: {r.file_path}")
                skipped += 1
            except Exception as exc:
                print(f"  ERROR for resume {r.id}: {exc}")
                skipped += 1

        await db.commit()
        print(f"\nMigration complete: {migrated} migrated, {skipped} skipped")


if __name__ == "__main__":
    asyncio.run(migrate())
