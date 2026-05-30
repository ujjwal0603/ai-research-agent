"""
Authentication routes — register, login, refresh, and profile.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_auth_manager
from api.middleware.auth import get_current_user
from database.connection import get_db
from schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Register ────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    auth=Depends(get_auth_manager),
    session: AsyncSession = Depends(get_db),
):
    """Create a new user account and return access + refresh tokens."""
    from database.models import User

    # Check email uniqueness
    existing = await session.execute(
        select(User).where(User.email == body.email)
    )
    if existing.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user_id = uuid.uuid4()
    hashed_pw = auth.hash_password(body.password)

    user = User(
        id=user_id,
        email=body.email,
        name=body.full_name,
        password_hash=hashed_pw,
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.commit()

    claims = {"sub": str(user_id), "email": user.email, "full_name": user.name}
    access = auth.create_access_token(claims)
    refresh = auth.create_refresh_token(claims)

    logger.info("Registered user %s (%s)", user_id, body.email)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=auth.access_token_expire_minutes * 60,
    )


# ── Login ───────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth=Depends(get_auth_manager),
    session: AsyncSession = Depends(get_db),
):
    """Validate credentials and return token pair."""
    from database.models import User

    result = await session.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalars().first()

    if user is None or not auth.verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    await session.commit()

    claims = {"sub": str(user.id), "email": user.email, "full_name": user.name}
    access = auth.create_access_token(claims)
    refresh = auth.create_refresh_token(claims)

    logger.info("User logged in: %s", user.email)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=auth.access_token_expire_minutes * 60,
    )


# ── Refresh ─────────────────────────────────────────


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    auth=Depends(get_auth_manager),
):
    """Exchange a valid refresh token for a new token pair."""
    payload = auth.decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — expected a refresh token",
        )

    claims = {
        "sub": payload["sub"],
        "email": payload.get("email", ""),
        "full_name": payload.get("full_name", ""),
    }
    new_access = auth.create_access_token(claims)
    new_refresh = auth.create_refresh_token(claims)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=auth.access_token_expire_minutes * 60,
    )


# ── Me (protected) ─────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's profile."""
    from database.models import User

    result = await session.execute(
        select(User).where(User.id == uuid.UUID(current_user["user_id"]))
    )
    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.name,
        created_at=user.created_at,
        is_active=True,
    )
