"""
journey.py: where a tenancy is in its life cycle (UI_ITERATIONS "The two journeys").

The frontend shows one "next action" per role from this stage.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlmodel import Session, select

from app.models import AgentRun, CaptureSlot, Finding, Inspection, Photo, Room, Tenancy
from app.util import ev

STAGES: List[str] = [
    "invite_pending",     # 0  owner invited, tenant has not accepted
    "move_in_capture",    # 1  move-in photos being taken
    "move_in_signing",    # 2  all photos taken, waiting for signatures
    "living",             # 3  move-in sealed, tenancy running
    "move_out_capture",   # 4  move-out photos being taken
    "ai_check",           # 5  agent is running
    "review",             # 6  findings to accept or dispute
    "settled",            # 7  every charged finding accepted (or nothing charged)
]

# One next action per role per stage: (title, cta)
NEXT_ACTION: Dict[str, Dict[str, tuple]] = {
    "invite_pending": {
        "owner": ("Waiting for your tenant to accept", "Resend invite"),
        "tenant": ("You have an invite", "Accept invite"),
    },
    "move_in_capture": {
        "owner": ("Record the flat", "Start move-in photos"),
        "tenant": ("Your owner is recording the flat", "View progress"),
    },
    "move_in_signing": {
        "owner": ("Sign the move-in record", "Review and sign"),
        "tenant": ("Review the move-in photos and sign", "Review and sign"),
    },
    "living": {
        "owner": ("Move-in record sealed", "Start move-out"),
        "tenant": ("Your deposit is protected", "Report an issue"),
    },
    "move_out_capture": {
        "owner": ("Finish the move-out photos", "Continue move-out"),
        "tenant": ("Move-out photos in progress", "View progress"),
    },
    "ai_check": {
        "owner": ("AI is checking the flat", "Watch live"),
        "tenant": ("AI is checking the flat", "Watch live"),
    },
    "review": {
        "owner": ("Review the AI findings", "Open report"),
        "tenant": ("Accept or dispute each finding", "Open report"),
    },
    "settled": {
        "owner": ("Deposit settled", "View settlement"),
        "tenant": ("Deposit settled", "View settlement"),
    },
}


def _slot_count(session: Session, property_id: str) -> int:
    room_ids = [r.id for r in session.exec(select(Room).where(Room.property_id == property_id)).all()]
    if not room_ids:
        return 0
    return len(session.exec(select(CaptureSlot).where(CaptureSlot.room_id.in_(room_ids))).all())  # type: ignore[attr-defined]


def _photo_count(session: Session, inspection_id: str) -> int:
    return len(session.exec(select(Photo).where(Photo.inspection_id == inspection_id)).all())


def latest_run(session: Session, tenancy_id: str) -> Optional[AgentRun]:
    runs = session.exec(select(AgentRun).where(AgentRun.tenancy_id == tenancy_id)).all()
    return max(runs, key=lambda r: r.started_at) if runs else None


def latest_inspection(session: Session, tenancy_id: str, type_: str) -> Optional[Inspection]:
    rows = [i for i in session.exec(select(Inspection).where(Inspection.tenancy_id == tenancy_id)).all()
            if ev(i.type) == type_]
    if not rows:
        return None
    locked = [i for i in rows if ev(i.status) == "locked"]
    return locked[-1] if locked else rows[-1]


def compute_stage(session: Session, tenancy: Tenancy) -> str:
    if ev(tenancy.invite_status) != "accepted":
        return "invite_pending"

    move_in = latest_inspection(session, tenancy.id, "move_in")
    if move_in is None:
        return "move_in_capture"
    if ev(move_in.status) != "locked":
        slots = _slot_count(session, tenancy.property_id)
        if ev(move_in.status) == "awaiting_signatures" or (slots and _photo_count(session, move_in.id) >= slots):
            return "move_in_signing"
        return "move_in_capture"

    move_out = latest_inspection(session, tenancy.id, "move_out")
    if move_out is None:
        return "living"

    run = latest_run(session, tenancy.id)
    if run is None or ev(run.status) == "failed":
        return "move_out_capture"
    if ev(run.status) == "running":
        return "ai_check"

    findings = session.exec(select(Finding).where(Finding.run_id == run.id)).all()
    open_items = [
        f for f in findings
        if ev(f.classification) == "damage" and ev(f.status) in ("proposed", "needs_review", "disputed")
    ] + [f for f in findings if ev(f.status) == "needs_review"]
    return "review" if open_items else "settled"


def stage_info(session: Session, tenancy: Tenancy, role: str) -> dict:
    stage = compute_stage(session, tenancy)
    title, cta = NEXT_ACTION[stage][role]
    return {"stage": stage, "stage_index": STAGES.index(stage), "next_action": {"title": title, "cta": cta}}
