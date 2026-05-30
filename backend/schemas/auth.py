"""
Authentication request/response schemas.

Covers user registration, login, JWT token pairs, and user profile.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration payload."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="Password (8-128 chars)"
    )
    full_name: str = Field(
        ..., min_length=1, max_length=255, description="User full name"
    )


class LoginRequest(BaseModel):
    """Username/password login payload."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """JWT token pair returned after successful auth."""

    access_token: str = Field(..., description="Short-lived access JWT")
    refresh_token: str = Field(..., description="Long-lived refresh JWT")
    token_type: str = Field(default="bearer", description="Token scheme")
    expires_in: int = Field(..., description="Access token TTL in seconds")


class RefreshRequest(BaseModel):
    """Refresh token exchange payload."""

    refresh_token: str = Field(..., description="Current refresh JWT")


class UserResponse(BaseModel):
    """Public user profile."""

    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="Display name")
    created_at: Optional[datetime] = Field(
        default=None, description="Account creation time"
    )
    is_active: bool = Field(default=True, description="Account active flag")
