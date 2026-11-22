"""
schemas.py — Pydantic response models shared by backend routers and
referenced by frontend/src/api.ts.

Three canonical shapes required by BOB_PLAYBOOK integration contracts:
  1. InspectionDetail  (GET /api/inspections/{id})
  2. TenancyReport     (GET /api/tenancies/{id}/report)
  3. AgentStepEvent    (SSE events on GET /api/runs/{id}/events)
"""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel

from app.models import (
    AgentRunStatus,
    AgentStepKind,
    ChangeType,
    FindingClassification,
    FindingStatus,
    InspectionStatus,
    InspectionType,
    MaintenanceCategory,
)


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

class SlotNoteOut(BaseModel):
    id: str
    slot_id: str
    author_id: str
    author_name: str
    text: str
    created_at: str


class SlotPhotoOut(BaseModel):
    id: str
    url: str
    sha256: str
    captured_at: str
    taken_by: str


class SlotDetail(BaseModel):
    id: str
    label: str
    guidance: str
    order: int
    item_id: Optional[str]
    photo: Optional[SlotPhotoOut]
    notes: List[SlotNoteOut]
    captured: bool
    room: str = ""
    ghost_url: Optional[str] = None  # move-in photo for this slot (move_out / checkin only); plain <img src>


# ---------------------------------------------------------------------------
# 1. InspectionDetail — GET /api/inspections/{id}
# ---------------------------------------------------------------------------

class InspectionDetail(BaseModel):
    id: str
    tenancy_id: str
    type: InspectionType
    status: InspectionStatus
    signed_by_owner_at: Optional[str]
    signed_by_tenant_at: Optional[str]
    lock_hash: Optional[str]
    slots: List[SlotDetail]


# ---------------------------------------------------------------------------
# Finding output (used in TenancyReport)
# ---------------------------------------------------------------------------

class CostBreakdown(BaseModel):
    rate_inr: float
    quantity: float
    depreciation_factor: float
    est_cost: float
    owner_override_cost: Optional[float]
    owner_note: Optional[str]
    cost_basis: str = ""          # "rate_card" | "replacement_value" | "not_charged"
    effective_cost: float = 0.0   # owner override if set, else est_cost
    item_age_years_at_move_out: Optional[float] = None
    useful_life_years: Optional[float] = None
    replacement_cost: Optional[float] = None


class EvidenceOut(BaseModel):
    id: str
    kind: str        # "move_in_note" | "maintenance_report"
    text: str
    date: str
    author: str = ""


class FindingOut(BaseModel):
    id: str
    run_id: str
    slot_id: str
    slot_label: str
    item_id: str
    item_type: str
    before_photo_url: Optional[str]
    after_photo_url: Optional[str]
    change_type: ChangeType
    classification: FindingClassification
    severity: int
    confidence: float
    region_description: str
    reasoning: str
    cited_evidence: List[str]  # list of note/report IDs
    evidence: List[EvidenceOut] = []  # the cited notes/reports, resolved for display
    bbox_after: Optional[List[float]] = None
    room: str = ""
    cost: CostBreakdown
    status: FindingStatus
    tenant_note: Optional[str]
    owner_note: Optional[str]


class TotalsOut(BaseModel):
    damage_pct: float
    proposed: float
    agreed: float
    disputed: float
    in_dispute: float
    refund_due: float
    deposit: float


class RunSummaryOut(BaseModel):
    run_id: str
    status: AgentRunStatus
    started_at: str
    finished_at: Optional[str]
    summary_en: Optional[str]
    summary_kn: Optional[str]


class MaintenanceReportOut(BaseModel):
    id: str
    slot_id: Optional[str]
    item_id: Optional[str]
    description: str
    reported_at: str
    category: MaintenanceCategory


# ---------------------------------------------------------------------------
# 2. TenancyReport — GET /api/tenancies/{id}/report
# ---------------------------------------------------------------------------

class TenancyReport(BaseModel):
    tenancy_id: str
    my_role: str = ""
    address: str = ""
    owner_name: str = ""
    tenant_name: str = ""
    move_in_lock_hash: Optional[str] = None
    move_out_lock_hash: Optional[str] = None
    property_score: float
    damage_pct: float
    totals: TotalsOut
    findings: List[FindingOut]
    maintenance_reports: List[MaintenanceReportOut]
    latest_run: Optional[RunSummaryOut]


# ---------------------------------------------------------------------------
# 3. AgentStepEvent — SSE payload for GET /api/runs/{id}/events
# ---------------------------------------------------------------------------

class AgentStepEvent(BaseModel):
    seq: int
    kind: AgentStepKind
    label: str
    tool_name: Optional[str]
    payload: Any  # arbitrary JSON from the agent
