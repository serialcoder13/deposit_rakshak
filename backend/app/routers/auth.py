"""
routers/auth.py — POST /api/auth/otp/request, POST /api/auth/otp/verify, GET /api/me
(SPEC §7 Auth, ARCHITECTURE §8)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import create_token, get_current_user
from app.config import settings
from app.db import get_session
from app.models import Tenancy, User

router = APIRouter(prefix="/api/auth", tags=["auth"])
me_router = APIRouter(prefix="/api", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / response bodies
# ---------------------------------------------------------------------------

class OtpRequest(BaseModel):
    phone: str


class OtpVerify(BaseModel):
    phone: str
    otp: str


class TenancyRole(BaseModel):
    tenancy_id: str
    role: str  # "owner" | "tenant"


class MeResponse(BaseModel):
    id: str
    phone: str
    name: str
    tenancies: List[TenancyRole]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/otp/request")
def otp_request(body: OtpRequest, session: Session = Depends(get_session)):
    """
    Request an OTP for the given phone number.
    In demo mode, no SMS is sent; the OTP is always DEMO_OTP.
    """
    # Ensure user exists (auto-create for the demo)
    user = session.exec(select(User).where(User.phone == body.phone)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Phone number not found. Use a seeded number.")
    return {"ok": True, "demo": settings.demo_mode, "hint": f"Use OTP {settings.demo_otp}"}


@router.post("/otp/verify")
def otp_verify(body: OtpVerify, session: Session = Depends(get_session)):
    """
    Verify the OTP and return a JWT + user object.
    In DEMO_MODE the OTP is always DEMO_OTP (default 123456).
    """
    if body.otp != settings.demo_otp:
        raise HTTPException(status_code=401, detail="Invalid OTP")

    user = session.exec(select(User).where(User.phone == body.phone)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Phone number not found")

    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "phone": user.phone, "name": user.name}}


@me_router.get("/me", response_model=MeResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return the current user plus their tenancies with roles."""
    tenancies_as_owner = session.exec(
        select(Tenancy).where(Tenancy.owner_id == current_user.id)
    ).all()
    tenancies_as_tenant = session.exec(
        select(Tenancy).where(Tenancy.tenant_id == current_user.id)
    ).all()

    roles: List[TenancyRole] = []
    for t in tenancies_as_owner:
        roles.append(TenancyRole(tenancy_id=t.id, role="owner"))
    for t in tenancies_as_tenant:
        roles.append(TenancyRole(tenancy_id=t.id, role="tenant"))

    return MeResponse(
        id=current_user.id,
        phone=current_user.phone,
        name=current_user.name,
        tenancies=roles,
    )
