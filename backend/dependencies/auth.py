"""
backend/dependencies/auth.py
============================
FastAPI dependency for verifying Supabase-issued JWTs.

The dependency decodes the Bearer JWT from the Authorization header using
the Supabase JWKS endpoint, then extracts user identity and role from the
token claims. When Supabase is not configured (development/test without a
Supabase project), the dependency falls back to an unauthenticated state
rather than crashing.

Usage
-----
    from backend.dependencies.auth import require_auth, CurrentUser

    @router.get("/protected")
    def protected(user: CurrentUser = Depends(require_auth)):
        return {"user_id": user.user_id, "role": user.role}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config.settings import get_settings

logger = logging.getLogger(__name__)

Role = Literal["INVESTOR", "ADMIN"]
AuthSource = Literal["supabase", "development_bypass"]
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """Verified caller identity extracted from a Supabase JWT."""

    user_id: str
    email: str
    role: Role
    auth_source: AuthSource = "supabase"


def _decode_token(token: str) -> dict:
    """Decode and verify our custom JWT, returning the claims dict."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """
    FastAPI dependency that requires a valid Supabase JWT.

    Raises HTTP 401 if the token is missing, expired, or invalid.
    """
    settings = get_settings()
    if settings.app_env == "development" and settings.auth_bypass_enabled:
        return CurrentUser(
            user_id=str(settings.dev_auth_user_id),
            email="dev@veyra.local",
            role="INVESTOR",
            auth_source="development_bypass",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = _decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, Exception) as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = claims.get("sub", "")
    email: str = claims.get("email", "")
    meta: dict = claims.get("user_metadata", {})
    raw_role = meta.get("role", "INVESTOR")
    role: Role = "ADMIN" if raw_role == "ADMIN" else "INVESTOR"

    return CurrentUser(user_id=user_id, email=email, role=role)


def require_admin(user: CurrentUser = Depends(require_auth)) -> CurrentUser:
    """FastAPI dependency that further requires ADMIN role."""
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user
