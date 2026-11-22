"""
routers/auth.py: POST /api/auth/otp/request, POST /api/auth/otp/verify,
GET /api/me, PATCH /api/me (SPEC §7 Auth, UI_ITERATIONS 2B).

Any 10-digit number can sign up. The OTP is settings.demo_otp (123456).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import create_token, get_current_user
from app.config import settings
from app.db import get_session
from app.journey import stage_info
from app.models import Property, Tenancy, User
from app.util import ev, normalise_phone

router = APIRouter(prefix="/api/auth", tags=["auth"])
me_router = APIRouter(prefix="/api", tags=["auth"])


# ---------------------------------------------------------------------------
# Bodies
# ---------------------------------------------------------------------------

class OtpRequest(BaseModel):
    phone: str


class OtpVerify(BaseModel):
    phone: str
    otp: str


class MePatch(BaseModel):
    name: str


class NextAction(BaseModel):
    title: str
    cta: str


class TenancyRole(BaseModel):
    tenancy_id: str
    role: str  # "owner" | "tenant"
    property_id: str
    address: str
    city: str
    deposit: float
    monthly_rent: float
    start_date: str
    other_party_name: str
    tenant_phone: str
    invite_status: str
    stage: str
    stage_index: int
    next_action: NextAction


class PendingInvite(BaseModel):
    tenancy_id: str
    address: str
    city: str
    owner_name: str
    deposit: float
    monthly_rent: float
    start_date: str


class MeResponse(BaseModel):
    id: str
    phone: str
    name: str
    is_new_user: bool
    tenancies: List[TenancyRole]
    pending_invites: List[PendingInvite]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_user(session: Session, phone: str) -> User:
    user = session.exec(select(User).where(User.phone == phone)).first()
    if user is None:
        user = User(phone=phone, name="")
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _user_json(user: User) -> dict:
    return {"id": user.id, "phone": user.phone, "name": user.name}


def _tenancy_role(session: Session, t: Tenancy, role: str) -> TenancyRole:
    prop = session.get(Property, t.property_id)
    if role == "owner":
        other = session.get(User, t.tenant_id) if t.tenant_id else None
        other_name = (other.name if other and other.name else t.tenant_name) or t.tenant_phone
    else:
        other = session.get(User, t.owner_id)
        other_name = other.name if other and other.name else "Owner"
    info = stage_info(session, t, role)
    return TenancyRole(
        tenancy_id=t.id,
        role=role,
        property_id=t.property_id,
        address=prop.address if prop else "",
        city=prop.city if prop else "",
        deposit=t.deposit,
        monthly_rent=t.monthly_rent,
        start_date=t.start_date,
        other_party_name=other_name,
        tenant_phone=t.tenant_phone,
        invite_status=ev(t.invite_status),
        stage=info["stage"],
        stage_index=info["stage_index"],
        next_action=NextAction(**info["next_action"]),
    )


def build_me(session: Session, user: User) -> MeResponse:
    roles: List[TenancyRole] = []
    for t in session.exec(select(Tenancy).where(Tenancy.owner_id == user.id)).all():
        roles.append(_tenancy_role(session, t, "owner"))
    for t in session.exec(select(Tenancy).where(Tenancy.tenant_id == user.id)).all():
        roles.append(_tenancy_role(session, t, "tenant"))

    invites: List[PendingInvite] = []
    pending = session.exec(select(Tenancy).where(Tenancy.tenant_phone == user.phone)).all()
    for t in pending:
        if ev(t.invite_status) != "pending" or t.owner_id == user.id:
            continue
        prop = session.get(Property, t.property_id)
        owner = session.get(User, t.owner_id)
        invites.append(PendingInvite(
            tenancy_id=t.id,
            address=prop.address if prop else "",
            city=prop.city if prop else "",
            owner_name=(owner.name if owner and owner.name else "Owner"),
            deposit=t.deposit,
            monthly_rent=t.monthly_rent,
            start_date=t.start_date,
        ))

    return MeResponse(
        id=user.id,
        phone=user.phone,
        name=user.name,
        is_new_user=not user.name,
        tenancies=roles,
        pending_invites=invites,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/otp/request")
def otp_request(body: OtpRequest, session: Session = Depends(get_session)):
    """Any valid number works. No SMS is sent; the OTP is always DEMO_OTP."""
    phone = normalise_phone(body.phone)
    user = _get_or_create_user(session, phone)
    return {"ok": True, "phone": phone, "is_new_user": not user.name, "hint": f"Use OTP {settings.demo_otp}"}


@router.post("/otp/verify")
def otp_verify(body: OtpVerify, session: Session = Depends(get_session)):
    """Verify the OTP, creating the user on first login. Returns a JWT and the user."""
    phone = normalise_phone(body.phone)
    if body.otp.strip() != settings.demo_otp:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    user = _get_or_create_user(session, phone)
    return {"token": create_token(user.id), "user": _user_json(user), "is_new_user": not user.name}


@me_router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """The user, their tenancies (with role, address, stage and next action) and pending invites."""
    return build_me(session, current_user)


@me_router.patch("/me", response_model=MeResponse)
def patch_me(body: MePatch, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    current_user.name = name[:60]
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return build_me(session, current_user)
