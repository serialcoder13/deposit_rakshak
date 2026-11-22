"""
routers/properties.py — GET/POST /api/properties, GET /api/properties/{id}
(SPEC §7 Property and setup)

MVP uses seed data; create/update UI is stretch.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import get_current_user
from app.db import get_session
from app.models import CaptureSlot, Item, Property, Room, User

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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
