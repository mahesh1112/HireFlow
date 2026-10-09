from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import timedelta

from app.database import get_db
from app.models.user import User
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    company: str | None
    role: str
    created_at: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email is already taken
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    if len(data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters",
        )

    user = User(
        email=data.email,
        name=data.name,
        company=data.company,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token(
        {"sub": user.id},
        expires_delta=timedelta(hours=settings.JWT_EXPIRY_HOURS),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "company": user.company,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
        },
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token({"sub": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "company": user.company,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
        },
    }


@router.post("/logout")
async def logout():
    # JWT is stateless — client should discard the token
    return {"message": "Successfully logged out"}


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "company": current_user.company,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat(),
    }


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user),
):
    token = create_access_token({"sub": current_user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "company": current_user.company,
            "role": current_user.role,
            "created_at": current_user.created_at.isoformat(),
        },
    }
