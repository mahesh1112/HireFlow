"""
Business unit and user-unit assignment endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.unit import BusinessUnit, UserUnit
from app.utils.auth import get_current_user
import structlog

logger = structlog.get_logger()

router = APIRouter(tags=["Units"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class AssignUnitsRequest(BaseModel):
    unit_ids: list[str]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/units")
async def list_units(
    db: AsyncSession = Depends(get_db),
):
    """List all available business units."""
    result = await db.execute(
        select(BusinessUnit).order_by(BusinessUnit.unit_name)
    )
    units = result.scalars().all()
    return [
        {"id": u.id, "unit_slug": u.unit_slug, "unit_name": u.unit_name}
        for u in units
    ]


@router.get("/users/me/units")
async def get_my_units(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the business units the current user belongs to."""
    result = await db.execute(
        select(BusinessUnit)
        .join(UserUnit, UserUnit.unit_id == BusinessUnit.id)
        .where(UserUnit.user_id == current_user.id)
        .order_by(BusinessUnit.unit_name)
    )
    units = result.scalars().all()
    return [
        {"id": u.id, "unit_slug": u.unit_slug, "unit_name": u.unit_name}
        for u in units
    ]


@router.post("/users/me/units", status_code=status.HTTP_200_OK)
async def assign_my_units(
    data: AssignUnitsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Self-assign the current user to one or more business units.
    Replaces all existing unit assignments.
    """
    if not data.unit_ids:
        # Allow clearing all unit assignments
        await db.execute(
            delete(UserUnit).where(UserUnit.user_id == current_user.id)
        )
        await db.commit()
        return {"assigned": []}

    # Validate all provided unit_ids exist
    result = await db.execute(
        select(BusinessUnit).where(BusinessUnit.id.in_(data.unit_ids))
    )
    valid_units = result.scalars().all()
    valid_ids = {u.id for u in valid_units}
    invalid_ids = [uid for uid in data.unit_ids if uid not in valid_ids]
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid unit IDs: {invalid_ids}",
        )

    # Replace existing assignments atomically
    await db.execute(
        delete(UserUnit).where(UserUnit.user_id == current_user.id)
    )
    for uid in data.unit_ids:
        db.add(UserUnit(user_id=current_user.id, unit_id=uid))

    await db.commit()
    logger.info("User units assigned", user_id=current_user.id, unit_ids=data.unit_ids)

    return {"assigned": data.unit_ids}


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all active users for recruiter/hiring-lead selector dropdowns."""
    result = await db.execute(
        select(User.id, User.name, User.email)
        .where(User.is_active == True)  # noqa: E712
        .order_by(User.name)
    )
    return [{"id": r[0], "name": r[1], "email": r[2]} for r in result.fetchall()]
