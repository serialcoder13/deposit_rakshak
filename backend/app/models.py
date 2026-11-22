"""
models.py — every SQLModel table from SPEC §5.
IDs are UUID strings; times are UTC ISO 8601 (stored as str for SQLite simplicity).
Enums use Python str enums so they serialise to JSON without extra config.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ItemType(str, Enum):
    wall = "wall"
    floor = "floor"
    table = "table"
    fan = "fan"
    geyser = "geyser"
    wardrobe = "wardrobe"
    cushion = "cushion"
    tile = "tile"
    other = "other"


class InspectionType(str, Enum):
    move_in = "move_in"
    checkin = "checkin"
    move_out = "move_out"


class InspectionStatus(str, Enum):
    draft = "draft"
    awaiting_signatures = "awaiting_signatures"
    locked = "locked"


class MaintenanceCategory(str, Enum):
    seepage = "seepage"
    plumbing = "plumbing"
    electrical = "electrical"
    structural = "structural"
    other = "other"


class ChangeType(str, Enum):
    stain = "stain"
    crack = "crack"
    hole = "hole"
    broken = "broken"
    missing = "missing"
    discoloration = "discoloration"
    scuff = "scuff"
    none = "none"


class FindingClassification(str, Enum):
    damage = "damage"
    wear = "wear"
    pre_existing = "pre_existing"
    owner_responsibility = "owner_responsibility"
    none = "none"


class FindingStatus(str, Enum):
    proposed = "proposed"
    needs_review = "needs_review"
    accepted = "accepted"
    disputed = "disputed"


class AgentRunStatus(str, Enum):
    running = "running"
    done = "done"
    failed = "failed"


class AgentStepKind(str, Enum):
    thought = "thought"
    tool_call = "tool_call"
    tool_result = "tool_result"
    error = "error"


class RateCardUnit(str, Enum):
    sqft = "sqft"
    piece = "piece"
    job = "job"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    phone: str = Field(index=True, unique=True)
    name: str


class Property(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    owner_id: str = Field(foreign_key="user.id")
    address: str
    city: str


class Room(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    property_id: str = Field(foreign_key="property.id")
    name: str
    order: int = 0


class Item(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    room_id: str = Field(foreign_key="room.id")
    type: ItemType
    material: str = ""
    age_years_at_move_in: float = 0.0
    useful_life_years: float = 10.0
    replacement_cost: float = 0.0


class CaptureSlot(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    room_id: str = Field(foreign_key="room.id")
    item_id: Optional[str] = Field(default=None, foreign_key="item.id")
    label: str
    order: int = 0
    guidance: str = ""


class Tenancy(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    property_id: str = Field(foreign_key="property.id")
    owner_id: str = Field(foreign_key="user.id")
    tenant_id: Optional[str] = Field(default=None, foreign_key="user.id")
    start_date: str  # ISO date string
    end_date: Optional[str] = None
    deposit: float
    monthly_rent: float
    invite_code: str = Field(default_factory=lambda: str(uuid.uuid4())[:8].upper())


class Inspection(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenancy_id: str = Field(foreign_key="tenancy.id")
    type: InspectionType
    status: InspectionStatus = InspectionStatus.draft
    signed_by_owner_at: Optional[str] = None
    signed_by_tenant_at: Optional[str] = None
    lock_hash: Optional[str] = None


class Photo(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    inspection_id: str = Field(foreign_key="inspection.id")
    slot_id: str = Field(foreign_key="captureslot.id")
    taken_by: str = Field(foreign_key="user.id")
    url: str
    sha256: str
    captured_at: str  # ISO datetime string
    device_meta: str = "{}"  # JSON string


class SlotNote(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    inspection_id: str = Field(foreign_key="inspection.id")
    slot_id: str = Field(foreign_key="captureslot.id")
    author_id: str = Field(foreign_key="user.id")
    text: str
    created_at: str  # ISO datetime string


class MaintenanceReport(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenancy_id: str = Field(foreign_key="tenancy.id")
    item_id: Optional[str] = Field(default=None, foreign_key="item.id")
    slot_id: Optional[str] = Field(default=None, foreign_key="captureslot.id")
    description: str
    photo_id: Optional[str] = None  # optional FK to photo
    reported_at: str  # ISO datetime string
    category: MaintenanceCategory


class RateCard(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    change_type: ChangeType
    item_type: ItemType
    severity: int  # 1, 2, or 3
    unit: RateCardUnit
    rate_inr: float = 0.0
    source: str = ""


class Finding(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    run_id: str = Field(foreign_key="agentrun.id")
    move_out_inspection_id: str = Field(foreign_key="inspection.id")
    item_id: str = Field(foreign_key="item.id")
    slot_id: str = Field(foreign_key="captureslot.id")
    before_photo_id: Optional[str] = None
    after_photo_id: Optional[str] = None
    change_type: ChangeType
    classification: FindingClassification
    severity: int = 0  # 0–3
    confidence: float = 1.0
    region_description: str = ""
    reasoning: str = ""
    cited_evidence: str = "[]"  # JSON list of note/report IDs
    quantity: float = 1.0
    depreciation_factor: float = 1.0
    est_cost: float = 0.0
    owner_override_cost: Optional[float] = None
    status: FindingStatus = FindingStatus.proposed
    tenant_note: Optional[str] = None
    owner_note: Optional[str] = None


class AgentRun(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenancy_id: str = Field(foreign_key="tenancy.id")
    status: AgentRunStatus = AgentRunStatus.running
    started_at: str  # ISO datetime string
    finished_at: Optional[str] = None
    summary_en: Optional[str] = None
    summary_kn: Optional[str] = None


class AgentStep(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    run_id: str = Field(foreign_key="agentrun.id")
    seq: int
    kind: AgentStepKind
    label: str = ""
    tool_name: Optional[str] = None
    payload: str = "{}"  # JSON string
    created_at: str  # ISO datetime string
