"""
templates.py: property layout presets used by the property wizard (UI_ITERATIONS 2B).

Each preset creates rooms, items and capture slots. Replacement values are
DEFAULTS the owner can edit later; they are the basis for depreciation, not AI output.
"""
from __future__ import annotations

from typing import Dict, List

from sqlmodel import Session

from app.models import CaptureSlot, Item, ItemType, Property, Room

# item key -> (type, material, useful_life_years, default replacement_cost)
_ITEMS = {
    "walls": (ItemType.wall, "paint", 5, 25000),
    "floor": (ItemType.floor, "vitrified tiles", 15, 40000),
    "fan": (ItemType.fan, "ceiling fan", 10, 3000),
    "wardrobe": (ItemType.wardrobe, "wood laminate", 10, 30000),
    "tiles": (ItemType.tile, "ceramic tiles", 15, 15000),
    "geyser": (ItemType.geyser, "electric geyser", 8, 8000),
    "table": (ItemType.table, "wood", 10, 8000),
    "cushion": (ItemType.cushion, "fabric", 3, 1500),
}

# room name -> list of (slot label, guidance, item key); items are created from the keys used
_ROOMS: Dict[str, List[tuple]] = {
    "Living room": [
        ("Living room: main wall", "Stand at the entrance, face the longest wall. Phone in landscape.", "walls"),
        ("Living room: floor", "Stand in a corner and tilt down to show the whole floor.", "floor"),
        ("Living room: ceiling fan", "Stand under the fan and point up. Include the blades.", "fan"),
    ],
    "Bedroom": [
        ("{room}: main wall", "Stand at the door, face the wall opposite the bed.", "walls"),
        ("{room}: wardrobe", "Open both wardrobe doors and shoot front-on.", "wardrobe"),
        ("{room}: floor", "Stand in a corner and tilt down to show the floor.", "floor"),
    ],
    "Kitchen": [
        ("Kitchen: counter and tiles", "Face the counter. Include the dado tiles and the sink.", "tiles"),
        ("Kitchen: walls", "Stand at the door and face the far wall.", "walls"),
    ],
    "Bathroom": [
        ("{room}: tiles", "Stand at the door and shoot the wall and floor tiles.", "tiles"),
        ("{room}: geyser and fittings", "Shoot the geyser, taps and shower together.", "geyser"),
    ],
}

PRESETS: Dict[str, List[str]] = {
    "1BHK": ["Living room", "Bedroom", "Kitchen", "Bathroom"],
    "2BHK": ["Living room", "Bedroom 1", "Bedroom 2", "Kitchen", "Bathroom 1", "Bathroom 2"],
    "Single room": ["Single room"],
}

# The demo room (SPEC §14): 4 slots on one room
_SINGLE_ROOM = [
    ("Wall A", "Stand at the door, face the main wall. Phone in landscape.", "walls"),
    ("Table top", "Shoot from directly above the table. Include all corners.", "table"),
    ("Window wall", "Stand facing the window. Capture the full wall including the sill.", "walls"),
    ("Sofa", "Shoot the sofa front-on. Include all cushions.", "cushion"),
]


def _room_slots(room_name: str) -> List[tuple]:
    if room_name == "Single room":
        return _SINGLE_ROOM
    base = room_name.rstrip(" 0123456789").strip()
    rows = _ROOMS.get(base, _ROOMS["Living room"])
    return [(label.format(room=room_name), guidance, key) for label, guidance, key in rows]


def preset_preview() -> List[dict]:
    """What the wizard shows before creating: rooms and slot labels per preset."""
    return [
        {
            "key": key,
            "rooms": [{"name": r, "slots": [s[0] for s in _room_slots(r)]} for r in rooms],
            "slot_count": sum(len(_room_slots(r)) for r in rooms),
        }
        for key, rooms in PRESETS.items()
    ]


def create_property_from_preset(
    session: Session, owner_id: str, address: str, city: str, preset: str, item_age_years: float
) -> Property:
    """Create the property with rooms, items and slots. Caller commits."""
    prop = Property(owner_id=owner_id, address=address.strip(), city=city.strip() or "Bengaluru", preset=preset)
    session.add(prop)
    session.flush()

    order = 0
    for r_index, room_name in enumerate(PRESETS[preset], start=1):
        room = Room(property_id=prop.id, name=room_name, order=r_index)
        session.add(room)
        session.flush()

        items: Dict[str, Item] = {}
        for label, guidance, key in _room_slots(room_name):
            if key not in items:
                type_, material, life, cost = _ITEMS[key]
                items[key] = Item(
                    room_id=room.id,
                    type=type_,
                    material=material,
                    age_years_at_move_in=min(float(item_age_years), float(life)),
                    useful_life_years=float(life),
                    replacement_cost=float(cost),
                )
                session.add(items[key])
                session.flush()
            order += 1
            session.add(CaptureSlot(room_id=room.id, item_id=items[key].id, label=label, order=order, guidance=guidance))
    session.flush()
    return prop
