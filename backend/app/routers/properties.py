"""
routers/properties.py — GET/POST /api/properties, GET /api/properties/{id}
(SPEC §7 Property and setup)

Also: GET /api/properties/presets, POST /api/properties (from a preset),
POST /api/properties/{id}/tenancies (invite a tenant by phone).
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.auth import get_current_user
from app.db import get_session
from app.models import CaptureSlot, InviteStatus, Item, Property, Room, Tenancy, User
from app.templates import PRESETS, create_property_from_preset, preset_preview
from app.util import ev, normalise_phone, now_iso

router = APIRouter(prefix="/api/properties", tags=["properties"])


# ---------------------------------------------------------------------------
# Response shapes (inline — shared canonical shapes are in schemas.py)
# ---------------------------------------------------------------------------

class SlotOut(BaseModel):
    id: str
    label: str
    guidance: str
    order: int
    item_id: str | None


class ItemOut(BaseModel):
    id: str
    type: str
    material: str
    age_years_at_move_in: float
    useful_life_years: float
    replacement_cost: float


class RoomOut(BaseModel):
    id: str
    name: str
    order: int
    items: List[ItemOut]
    slots: List[SlotOut]


class PropertyOut(BaseModel):
    id: str
    owner_id: str
    address: str
    city: str


class PropertyDetailOut(PropertyOut):
    rooms: List[RoomOut]


class PropertyCreate(BaseModel):
    address: str = Field(min_length=3)
    city: str = "Bengaluru"
    preset: str = "1BHK"
    item_age_years: float = Field(default=3, ge=0, le=50)


class TenancyCreate(BaseModel):
    tenant_phone: str
    tenant_name: Optional[str] = None
    deposit: float = Field(gt=0)
    monthly_rent: float = Field(gt=0)
    start_date: Optional[str] = None  # ISO date, defaults to today


class TenancyCreated(BaseModel):
    tenancy_id: str
    property_id: str
    tenant_phone: str
    invite_status: str
    invite_code: str
    tenant_already_registered: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/presets")
def list_presets():
    """Layout presets for the property wizard, with the rooms and slots each creates."""
    return preset_preview()


@router.post("", response_model=PropertyDetailOut)
def create_property(
    body: PropertyCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Create a property from a preset. The caller becomes the owner."""
    if body.preset not in PRESETS:
        raise HTTPException(status_code=422, detail=f"preset must be one of {list(PRESETS)}")
    prop = create_property_from_preset(
        session, current_user.id, body.address, body.city, body.preset, body.item_age_years
    )
    session.commit()
    return get_property(prop.id, current_user, session)


@router.post("/{property_id}/tenancies", response_model=TenancyCreated)
def invite_tenant(
    property_id: str,
    body: TenancyCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Owner invites a tenant by phone. The tenancy stays pending until the tenant accepts."""
    prop = session.get(Property, property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can invite a tenant")

    phone = normalise_phone(body.tenant_phone)
    if phone == current_user.phone:
        raise HTTPException(status_code=422, detail="You cannot invite your own number")

    open_tenancies = [
        t for t in session.exec(select(Tenancy).where(Tenancy.property_id == property_id)).all()
        if not t.end_date
    ]
    if open_tenancies:
        raise HTTPException(status_code=409, detail="This property already has an active or pending tenancy")

    start = body.start_date or date.today().isoformat()
    try:
        date.fromisoformat(start[:10])
    except ValueError:
        raise HTTPException(status_code=422, detail="start_date must be YYYY-MM-DD")

    tenancy = Tenancy(
        property_id=prop.id,
        owner_id=current_user.id,
        tenant_phone=phone,
        tenant_name=(body.tenant_name or "").strip(),
        invite_status=InviteStatus.pending,
        created_at=now_iso(),
        start_date=start[:10],
        deposit=body.deposit,
        monthly_rent=body.monthly_rent,
    )
    session.add(tenancy)
    session.commit()
    session.refresh(tenancy)
    existing = session.exec(select(User).where(User.phone == phone)).first()
    return TenancyCreated(
        tenancy_id=tenancy.id,
        property_id=prop.id,
        tenant_phone=phone,
        invite_status=ev(tenancy.invite_status),
        invite_code=tenancy.invite_code,
        tenant_already_registered=existing is not None,
    )


@router.get("", response_model=List[PropertyOut])
def list_properties(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return all properties owned by the current user."""
    props = session.exec(select(Property).where(Property.owner_id == current_user.id)).all()
    return [PropertyOut(id=p.id, owner_id=p.owner_id, address=p.address, city=p.city) for p in props]


@router.get("/{property_id}", response_model=PropertyDetailOut)
def get_property(
    property_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return a property with its rooms, items and slots."""
    prop = session.get(Property, property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.owner_id != current_user.id:
        is_tenant = session.exec(
            select(Tenancy).where(Tenancy.property_id == prop.id, Tenancy.tenant_id == current_user.id)
        ).first()
        if is_tenant is None:
            raise HTTPException(status_code=403, detail="Not your property")

    rooms = session.exec(select(Room).where(Room.property_id == prop.id)).all()
    rooms_out: List[RoomOut] = []
    for room in sorted(rooms, key=lambda r: r.order):
        items = session.exec(select(Item).where(Item.room_id == room.id)).all()
        slots = session.exec(
            select(CaptureSlot).where(CaptureSlot.room_id == room.id)
        ).all()
        rooms_out.append(
            RoomOut(
                id=room.id,
                name=room.name,
                order=room.order,
                items=[
                    ItemOut(
                        id=i.id,
                        type=i.type,
                        material=i.material,
                        age_years_at_move_in=i.age_years_at_move_in,
                        useful_life_years=i.useful_life_years,
                        replacement_cost=i.replacement_cost,
                    )
                    for i in items
                ],
                slots=[
                    SlotOut(id=sl.id, label=sl.label, guidance=sl.guidance, order=sl.order, item_id=sl.item_id)
                    for sl in sorted(slots, key=lambda x: x.order)
                ],
            )
        )

    return PropertyDetailOut(
        id=prop.id,
        owner_id=prop.owner_id,
        address=prop.address,
        city=prop.city,
        rooms=rooms_out,
    )
