"""
Authentication manager — password hashing, JWT creation/verification,
and the ``get_current_user`` FastAPI dependency.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
import bcrypt

from config.settings import get_settings

logger = logging.getLogger(__name__)

# ── Password hashing context (bcrypt) ──────────────
# (passlib removed due to bcrypt >= 4.0.0 incompatibilities)

# ── OAuth2 bearer scheme ───────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class AuthManager:
    """Handles password hashing and JWT token lifecycle.

    Reads ``SECRET_KEY`` and ``ALGORITHM`` from application settings so
    the same instance can be shared as a singleton across routes.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.secret_key: str = settings.SECRET_KEY
        self.algorithm: str = settings.ALGORITHM
        self.access_token_expire_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days: int = settings.REFRESH_TOKEN_EXPIRE_DAYS
        logger.info("AuthManager initialised (algo=%s)", self.algorithm)

    # ── Password helpers ────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        """Return a bcrypt hash of *password*."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify *plain* against the bcrypt *hashed* value."""
        try:
            return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
        except ValueError:
            return False

    # ── Token creation ──────────────────────────────

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a short-lived access JWT.

        Args:
            data: Claims to embed (must include ``sub``).
            expires_delta: Custom TTL; defaults to settings value.

        Returns:
            Encoded JWT string.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta
            or timedelta(minutes=self.access_token_expire_minutes)
        )
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a long-lived refresh JWT.

        Args:
            data: Claims to embed (must include ``sub``).

        Returns:
            Encoded JWT string.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            days=self.refresh_token_expire_days
        )
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    # ── Token decoding ──────────────────────────────

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT, raising *HTTPException* on failure.

        Returns:
            The decoded claims dictionary.

        Raises:
            HTTPException 401: If the token is expired, malformed, or missing ``sub``.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            if payload.get("sub") is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing subject claim",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return payload
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError as exc:
            logger.warning("JWT decode error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


# ── Singleton (lazily created the first time it's needed) ──
_auth_manager: Optional[AuthManager] = None


def _get_auth_manager() -> AuthManager:
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


# ── FastAPI dependency ──────────────────────────────


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """FastAPI dependency: extract Bearer token, decode it, return user dict.

    The returned dict contains at minimum ``sub`` (user id) plus any
    other claims embedded in the JWT (e.g. ``email``, ``full_name``).

    Raises:
        HTTPException 401: If the token is invalid or expired.
    """
    auth = _get_auth_manager()
    payload = auth.decode_token(token)
    return {
        "user_id": payload["sub"],
        "email": payload.get("email", ""),
        "full_name": payload.get("full_name", ""),
        "token_type": payload.get("type", "access"),
    }
