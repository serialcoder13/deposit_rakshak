"""
routers/tenancies.py: tenancy detail, invites (accept / decline / join),
maintenance issues, inspections, and starting the AI comparison
(SPEC §7 Tenancy, Inspections, Reports; UI_ITERATIONS 2B).
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import get_current_user, require_tenancy_role
from app.db import get_session
from app.journey import latest_run, stage_info
from app.models import (
    AgentRun,
    AgentRunStatus,
    CaptureSlot,
    Inspection,
    InspectionStatus,
    InspectionType,
    InviteStatus,
    MaintenanceCategory,
    MaintenanceReport,
    Photo,
    Property,
    Room,
    Tenancy,
    User,
)
from app.util import ev, normalise_phone, now_iso

router = APIRouter(prefix="/api", tags=["tenancies"])


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------

class InspectionSummary(BaseModel):
    id: str
    type: str
    status: str
    photo_count: int
    slot_count: int
    signed_by_owner_at: Optional[str]
    signed_by_tenant_at: Optional[str]
    lock_hash: Optional[str]


class RunSummary(BaseModel):
    id: str
    status: str
    started_at: str
    finished_at: Optional[str]


class ReportOut(BaseModel):
    id: str
    slot_id: Optional[str]
    slot_label: Optional[str]
    item_id: Optional[str]
    description: str
    reported_at: str
    category: str


class NextAction(BaseModel):
    title: str
    cta: str


class SlotBrief(BaseModel):
    id: str
    label: str
    room: str


class TenancyDetail(BaseModel):
    id: str
    property_id: str
    owner_id: str
    tenant_id: Optional[str]
    start_date: str
    deposit: float
    monthly_rent: float
    invite_code: str
    inspections: List[InspectionSummary]
    maintenance_reports: List[ReportOut]
    latest_run: Optional[RunSummary]
    # additions for the role-aware UI
    my_role: str
    address: str
    city: str
    owner_name: str
    tenant_name: str
    tenant_phone: str
    invite_status: str
    stage: str
    stage_index: int
    next_action: NextAction
    slots: List[SlotBrief]


class IssueCreate(BaseModel):
    description: str
    category: MaintenanceCategory
    slot_id: Optional[str] = None
    item_id: Optional[str] = None


class InspectionCreate(BaseModel):
    type: InspectionType


class JoinBody(BaseModel):
    invite_code: str


class CompareResponse(BaseModel):
    run_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slots_for_property(session: Session, property_id: str) -> List[tuple]:
    """[(slot, room_name)] in capture order."""
    rooms = {r.id: r.name for r in session.exec(select(Room).where(Room.property_id == property_id)).all()}
    if not rooms:
        return []
    slots = session.exec(select(CaptureSlot).where(CaptureSlot.room_id.in_(list(rooms)))).all()  # type: ignore[attr-defined]
    return [(s, rooms[s.room_id]) for s in sorted(slots, key=lambda s: s.order)]


def _role(tenancy: Tenancy, user: User) -> str:
    return "owner" if tenancy.owner_id == user.id else "tenant"


def _invite_for_me(session: Session, tenancy_id: str, user: User) -> Tenancy:
    tenancy = session.get(Tenancy, tenancy_id)
    if tenancy is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if tenancy.tenant_phone != user.phone:
        raise HTTPException(status_code=403, detail="This invite is for a different phone number")
    if ev(tenancy.invite_status) != "pending":
        raise HTTPException(status_code=409, detail="This invite was already accepted")
    return tenancy


def build_tenancy_detail(session: Session, tenancy: Tenancy, user: User) -> TenancyDetail:
    role = _role(tenancy, user)
    prop = session.get(Property, tenancy.property_id)
    owner = session.get(User, tenancy.owner_id)
    tenant = session.get(User, tenancy.tenant_id) if tenancy.tenant_id else None
    slots = _slots_for_property(session, tenancy.property_id)
    slot_label = {s.id: s.label for s, _ in slots}

    inspections = session.exec(select(Inspection).where(Inspection.tenancy_id == tenancy.id)).all()
    reports = session.exec(select(MaintenanceReport).where(MaintenanceReport.tenancy_id == tenancy.id)).all()
    run = latest_run(session, tenancy.id)
    info = stage_info(session, tenancy, role)

    return TenancyDetail(
        id=tenancy.id,
        property_id=tenancy.property_id,
        owner_id=tenancy.owner_id,
        tenant_id=tenancy.tenant_id,
        start_date=tenancy.start_date,
        deposit=tenancy.deposit,
        monthly_rent=tenancy.monthly_rent,
        invite_code=tenancy.invite_code,
        inspections=[
            InspectionSummary(
                id=i.id,
                type=ev(i.type),
                status=ev(i.status),
                photo_count=len(session.exec(select(Photo).where(Photo.inspection_id == i.id)).all()),
                slot_count=len(slots),
                signed_by_owner_at=i.signed_by_owner_at,
                signed_by_tenant_at=i.signed_by_tenant_at,
                lock_hash=i.lock_hash,
            )
            for i in inspections
        ],
        maintenance_reports=[
            ReportOut(
                id=r.id,
                slot_id=r.slot_id,
                slot_label=slot_label.get(r.slot_id or ""),
                item_id=r.item_id,
                description=r.description,
                reported_at=r.reported_at,
                category=ev(r.category),
            )
            for r in sorted(reports, key=lambda r: r.reported_at, reverse=True)
        ],
        latest_run=RunSummary(id=run.id, status=ev(run.status), started_at=run.started_at, finished_at=run.finished_at)
        if run else None,
        my_role=role,
        address=prop.address if prop else "",
        city=prop.city if prop else "",
        owner_name=(owner.name if owner and owner.name else "Owner"),
        tenant_name=(tenant.name if tenant and tenant.name else tenancy.tenant_name) or tenancy.tenant_phone,
        tenant_phone=tenancy.tenant_phone,
        invite_status=ev(tenancy.invite_status),
        stage=info["stage"],
        stage_index=info["stage_index"],
        next_action=NextAction(**info["next_action"]),
        slots=[SlotBrief(id=s.id, label=s.label, room=room) for s, room in slots],
    )


# ---------------------------------------------------------------------------
# Tenancy
# ---------------------------------------------------------------------------

@router.get("/tenancies/{tenancy_id}", response_model=TenancyDetail)
def get_tenancy(
    tenancy_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tenancy = require_tenancy_role(tenancy_id, ["owner", "tenant"], session, current_user)
    return build_tenancy_detail(session, tenancy, current_user)


@router.post("/tenancies/{tenancy_id}/accept", response_model=TenancyDetail)
def accept_invite(
    tenancy_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """The invited phone accepts: becomes the tenant."""
    tenancy = _invite_for_me(session, tenancy_id, current_user)
    tenancy.tenant_id = current_user.id
    tenancy.invite_status = InviteStatus.accepted
    session.add(tenancy)
    session.commit()
    session.refresh(tenancy)
    return build_tenancy_detail(session, tenancy, current_user)


@router.post("/tenancies/{tenancy_id}/decline")
def decline_invite(
    tenancy_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """The invited phone declines: the pending tenancy is removed."""
    tenancy = _invite_for_me(session, tenancy_id, current_user)
    session.delete(tenancy)
    session.commit()
    return {"ok": True}


@router.post("/tenancies/join", response_model=TenancyDetail)
def join_by_code(
    body: JoinBody,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Accept an invite by its code (fallback when the owner typed a different number)."""
    tenancy = session.exec(
        select(Tenancy).where(Tenancy.invite_code == body.invite_code.strip().upper())
    ).first()
    if tenancy is None:
        raise HTTPException(status_code=404, detail="Invite code not found")
    if ev(tenancy.invite_status) != "pending":
        raise HTTPException(status_code=409, detail="This invite was already accepted")
    if tenancy.owner_id == current_user.id:
        raise HTTPException(status_code=422, detail="You own this property")
    tenancy.tenant_id = current_user.id
    tenancy.tenant_phone = current_user.phone
    tenancy.invite_status = InviteStatus.accepted
    session.add(tenancy)
    session.commit()
    session.refresh(tenancy)
    return build_tenancy_detail(session, tenancy, current_user)


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

@router.post("/tenancies/{tenancy_id}/issues")
def create_issue(
    tenancy_id: str,
    body: IssueCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """File a maintenance or check-in report (tenant only, SPEC §3)."""
    tenancy = require_tenancy_role(tenancy_id, ["tenant"], session, current_user)
    item_id = body.item_id
    if body.slot_id and not item_id:
        slot = session.get(CaptureSlot, body.slot_id)
        item_id = slot.item_id if slot else None
    report = MaintenanceReport(
        tenancy_id=tenancy.id,
        item_id=item_id,
        slot_id=body.slot_id,
        description=body.description.strip(),
        reported_at=now_iso(),
        category=body.category,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return {"id": report.id, "ok": True}


# ---------------------------------------------------------------------------
# Inspections
# ---------------------------------------------------------------------------

@router.post("/tenancies/{tenancy_id}/inspections")
def create_inspection(
    tenancy_id: str,
    body: InspectionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Start (or resume) an inspection of the given type.
    Returns the existing unlocked one of that type instead of creating a duplicate.
    Needs an accepted tenant. A move_out needs a locked move_in (SPEC §7).
    """
    tenancy = require_tenancy_role(tenancy_id, ["owner", "tenant"], session, current_user)
    if ev(tenancy.invite_status) != "accepted":
        raise HTTPException(status_code=409, detail="The tenant has not accepted the invite yet")

    type_ = ev(body.type)
    existing = [
        i for i in session.exec(select(Inspection).where(Inspection.tenancy_id == tenancy_id)).all()
        if ev(i.type) == type_
    ]
    open_one = next((i for i in existing if ev(i.status) != "locked"), None)
    if open_one:
        return {"id": open_one.id, "type": type_, "status": ev(open_one.status), "resumed": True}

    if type_ == "move_in" and existing:
        raise HTTPException(status_code=409, detail="The move-in record is already sealed")

    if type_ == "move_out":
        sealed_move_in = any(
            ev(i.type) == "move_in" and ev(i.status) == "locked"
            for i in session.exec(select(Inspection).where(Inspection.tenancy_id == tenancy_id)).all()
        )
        if not sealed_move_in:
            raise HTTPException(status_code=409, detail="A sealed move-in record is required before move-out")

    inspection = Inspection(tenancy_id=tenancy_id, type=body.type)
    session.add(inspection)
    session.commit()
    session.refresh(inspection)
    return {"id": inspection.id, "type": type_, "status": ev(inspection.status), "resumed": False}


# ---------------------------------------------------------------------------
# Compare (agent run)
# ---------------------------------------------------------------------------

@router.post("/tenancies/{tenancy_id}/compare", response_model=CompareResponse)
def start_compare(
    tenancy_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Start the agent comparison run (SPEC §7). Returns run_id immediately."""
    require_tenancy_role(tenancy_id, ["owner", "tenant"], session, current_user)

    running = latest_run(session, tenancy_id)
    if running and ev(running.status) == "running":
        return CompareResponse(run_id=running.id)  # one run at a time: rejoin it

    inspections = session.exec(select(Inspection).where(Inspection.tenancy_id == tenancy_id)).all()
    if not any(ev(i.type) == "move_in" and ev(i.status) == "locked" for i in inspections):
        raise HTTPException(status_code=409, detail="Seal the move-in record first")
    move_outs = [i for i in inspections if ev(i.type) == "move_out"]
    if not move_outs or not any(
        session.exec(select(Photo).where(Photo.inspection_id == m.id)).first() for m in move_outs
    ):
        raise HTTPException(status_code=409, detail="Take the move-out photos first")

    run = AgentRun(tenancy_id=tenancy_id, status=AgentRunStatus.running, started_at=now_iso())
    session.add(run)
    session.commit()
    session.refresh(run)

    from app.agent.loop import run_agent
    from app.db import engine as db_engine

    background_tasks.add_task(run_agent, run.id, tenancy_id, db_engine)
    return CompareResponse(run_id=run.id)
