"""
auth.py — OTP flow, JWT creation/validation, and FastAPI dependencies.
Only llm.py talks to the LLM. Only this file issues and verifies JWTs.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models import Tenancy, User

_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_token(user_id: str) -> str:
    """Return a signed JWT for the given user ID."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT; raise 401 on failure."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    """Resolve the Bearer token to a User row; 401 if missing or invalid."""
    payload = decode_token(credentials.credentials)
    user = session.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_tenancy_role(tenancy_id: str, roles: list[str], session: Session, user: User) -> Tenancy:
    """
    Return the Tenancy if the user holds one of the required roles on it.
    Raises 404 if the tenancy doesn't exist, 403 if the user has no access.
    """
    tenancy = session.get(Tenancy, tenancy_id)
    if tenancy is None:
        raise HTTPException(status_code=404, detail="Tenancy not found")

    user_role: Optional[str] = None
    if tenancy.owner_id == user.id:
        user_role = "owner"
    elif tenancy.tenant_id == user.id:
        user_role = "tenant"

    if user_role not in roles:
        raise HTTPException(status_code=403, detail="Insufficient role for this tenancy")

    return tenancy
