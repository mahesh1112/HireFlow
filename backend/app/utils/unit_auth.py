"""
Reusable FastAPI dependency for resolving the current user's business unit memberships.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.unit import UserUnit
from app.utils.auth import get_current_user


async def get_current_user_units(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[str]:
    """
    Returns a list of unit_ids the current user belongs to.
    Inject this dependency into any endpoint that needs unit-scoped access control.
    """
    result = await db.execute(
        select(UserUnit.unit_id).where(UserUnit.user_id == current_user.id)
    )
    return [row[0] for row in result.fetchall()]
