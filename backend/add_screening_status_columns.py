"""
One-time migration: add screening_status and screening_error columns
to job_descriptions table.

Run with:  python add_screening_status_columns.py
"""
import asyncio
from sqlalchemy import text
from app.database import engine


async def migrate():
    async with engine.begin() as conn:
        # Add screening_status column (nullable, no default)
        await conn.execute(text(
            "ALTER TABLE job_descriptions "
            "ADD COLUMN IF NOT EXISTS screening_status VARCHAR(20) DEFAULT NULL"
        ))
        # Add screening_error column (nullable text)
        await conn.execute(text(
            "ALTER TABLE job_descriptions "
            "ADD COLUMN IF NOT EXISTS screening_error TEXT DEFAULT NULL"
        ))
    print("Migration complete: screening_status and screening_error columns added.")


if __name__ == "__main__":
    asyncio.run(migrate())
