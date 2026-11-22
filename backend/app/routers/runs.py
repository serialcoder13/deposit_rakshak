"""
routers/runs.py: agent run events (SSE + polling) and the tenancy report
(SPEC §7 Reports, runs and findings; §10 scoring; ARCHITECTURE §4.2).
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app import scoring
from app.auth import decode_token, get_current_user, require_tenancy_role
from app.db import engine, get_session
from app.journey import latest_inspection, latest_run
from app.models import (
    AgentRun,
    AgentStep,
    CaptureSlot,
    Finding,
    Item,
    MaintenanceReport,
    Photo,
    Property,
    Room,
    SlotNote,
    User,
)
from app.schemas import (
    CostBreakdown,
    EvidenceOut,
    FindingOut,
    MaintenanceReportOut,
    RunSummaryOut,
    TenancyReport,
    TotalsOut,
)
from app.util import ev, months_between

router = APIRouter(prefix="/api", tags=["runs"])


def _step_json(step: AgentStep) -> dict:
    try:
        payload = json.loads(step.payload)
    except Exception:
        payload = {}
    return {"seq": step.seq, "kind": ev(step.kind), "label": step.label, "tool_name": step.tool_name, "payload": payload}


def _user_from_request(request: Request, token: Optional[str], session: Session) -> User:
    """Bearer header, or ?token= (EventSource cannot send headers)."""
    raw = token
    auth = request.headers.get("authorization", "")
    if not raw and auth.lower().startswith("bearer "):
        raw = auth[7:]
    if not raw:
        raise HTTPException(status_code=401, detail="Missing token")
    user = session.get(User, decode_token(raw)["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Run events
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}/events")
async def run_events(
    run_id: str,
    request: Request,
    token: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
):
    """
    SSE stream of AgentStep rows. Auth: Bearer header or ?token=<jwt>.
    Streams existing steps, then new ones, then a final 'done' or 'failed' event.
    """
    user = _user_from_request(request, token, session)
    run = session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    require_tenancy_role(run.tenancy_id, ["owner", "tenant"], session, user)

    async def event_generator():
        last_seq = -1
        for _ in range(600):  # up to ~5 minutes at 0.5 s
            if await request.is_disconnected():
                return
            with Session(engine) as s:
                steps = s.exec(
                    select(AgentStep).where(AgentStep.run_id == run_id, AgentStep.seq > last_seq).order_by(AgentStep.seq)
                ).all()
                current = s.get(AgentRun, run_id)
                status = ev(current.status) if current else "failed"
            for step in steps:
                yield f"data: {json.dumps(_step_json(step))}\n\n"
                last_seq = step.seq
            if status in ("done", "failed"):
                yield f"data: {json.dumps({'seq': last_seq + 1, 'kind': status, 'label': status, 'tool_name': None, 'payload': {}})}\n\n"
                return
            yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'seq': last_seq + 1, 'kind': 'error', 'label': 'timeout', 'tool_name': None, 'payload': {}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs/{run_id}/steps")
def run_steps(
    run_id: str,
    after: int = -1,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Polling fallback for the trace: steps with seq > after, plus the run status."""
    run = session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    require_tenancy_role(run.tenancy_id, ["owner", "tenant"], session, current_user)
    steps = session.exec(
        select(AgentStep).where(AgentStep.run_id == run_id, AgentStep.seq > after).order_by(AgentStep.seq)
    ).all()
    return {
        "run_id": run.id,
        "tenancy_id": run.tenancy_id,
        "status": ev(run.status),
        "steps": [_step_json(s) for s in steps],
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@router.get("/tenancies/{tenancy_id}/report", response_model=TenancyReport)
def get_report(
    tenancy_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Findings of the latest run, scores, totals and summaries.
    Totals are recomputed on each read so disputes show immediately.
    """
    tenancy = require_tenancy_role(tenancy_id, ["owner", "tenant"], session, current_user)
    prop = session.get(Property, tenancy.property_id)
    owner = session.get(User, tenancy.owner_id)
    tenant = session.get(User, tenancy.tenant_id) if tenancy.tenant_id else None

    rooms = {r.id: r.name for r in session.exec(select(Room).where(Room.property_id == tenancy.property_id)).all()}
    items = session.exec(select(Item).where(Item.room_id.in_(list(rooms) or [""]))).all()  # type: ignore[attr-defined]
    items_by_id = {i.id: i for i in items}
    slots = {s.id: s for s in session.exec(select(CaptureSlot).where(CaptureSlot.room_id.in_(list(rooms) or [""]))).all()}  # type: ignore[attr-defined]
    total_replacement = sum(i.replacement_cost for i in items)
    months = months_between(tenancy.start_date, tenancy.end_date)

    run = latest_run(session, tenancy_id)
    findings = session.exec(select(Finding).where(Finding.run_id == run.id)).all() if run else []

    notes = {n.id: n for n in session.exec(select(SlotNote)).all()} if findings else {}
    reports = session.exec(select(MaintenanceReport).where(MaintenanceReport.tenancy_id == tenancy_id)).all()
    reports_by_id = {r.id: r for r in reports}
    names = {u.id: (u.name or "") for u in [owner, tenant] if u}

    def evidence_for(ids: List[str]) -> List[EvidenceOut]:
        out: List[EvidenceOut] = []
        for eid in ids:
            if eid in notes:
                n = notes[eid]
                out.append(EvidenceOut(id=eid, kind="move_in_note", text=n.text, date=n.created_at, author=names.get(n.author_id, "")))
            elif eid in reports_by_id:
                r = reports_by_id[eid]
                out.append(EvidenceOut(id=eid, kind="maintenance_report", text=f"{ev(r.category)}: {r.description}", date=r.reported_at, author=names.get(tenancy.tenant_id or "", "Tenant")))
        return out

    findings_out: List[FindingOut] = []
    for f in findings:
        slot = slots.get(f.slot_id)
        item = items_by_id.get(f.item_id)
        before = session.get(Photo, f.before_photo_id) if f.before_photo_id else None
        after = session.get(Photo, f.after_photo_id) if f.after_photo_id else None
        try:
            cited = json.loads(f.cited_evidence or "[]")
        except Exception:
            cited = []
        try:
            bbox = json.loads(f.bbox_after) if f.bbox_after else None
        except Exception:
            bbox = None
        effective = f.owner_override_cost if f.owner_override_cost is not None else f.est_cost
        findings_out.append(FindingOut(
            id=f.id,
            run_id=f.run_id,
            slot_id=f.slot_id,
            slot_label=slot.label if slot else "",
            item_id=f.item_id,
            item_type=ev(item.type) if item else "",
            before_photo_url=before.url if before else None,
            after_photo_url=after.url if after else None,
            change_type=f.change_type,
            classification=f.classification,
            severity=f.severity,
            confidence=f.confidence,
            region_description=f.region_description,
            reasoning=f.reasoning,
            cited_evidence=cited,
            evidence=evidence_for(cited),
            bbox_after=bbox,
            room=rooms.get(slot.room_id, "") if slot else "",
            cost=CostBreakdown(
                rate_inr=f.rate_inr,
                quantity=f.quantity,
                depreciation_factor=f.depreciation_factor,
                est_cost=f.est_cost,
                owner_override_cost=f.owner_override_cost,
                owner_note=f.owner_note,
                cost_basis=f.cost_basis,
                effective_cost=effective,
                item_age_years_at_move_out=round(item.age_years_at_move_in + months / 12, 1) if item else None,
                useful_life_years=item.useful_life_years if item else None,
                replacement_cost=item.replacement_cost if item else None,
            ),
            status=f.status,
            tenant_note=f.tenant_note,
            owner_note=f.owner_note,
        ))

    findings_dicts = [
        {
            "classification": ev(f.classification),
            "status": ev(f.status),
            "est_cost": f.est_cost,
            "owner_override_cost": f.owner_override_cost,
        }
        for f in findings
    ]
    t = scoring.totals(findings_dicts, tenancy.deposit, total_replacement)

    item_damage: dict = defaultdict(list)
    for f in findings:
        if ev(f.classification) == "damage":
            item_damage[f.item_id].append(f.severity)
    prop_score = scoring.property_score(
        [{"replacement_cost": i.replacement_cost, "damage_severities": item_damage.get(i.id, [])} for i in items]
    ) if items else 100.0

    move_in = latest_inspection(session, tenancy_id, "move_in")
    move_out = latest_inspection(session, tenancy_id, "move_out")
    role = "owner" if tenancy.owner_id == current_user.id else "tenant"

    return TenancyReport(
        tenancy_id=tenancy_id,
        my_role=role,
        address=prop.address if prop else "",
        owner_name=names.get(tenancy.owner_id, "") or "Owner",
        tenant_name=(names.get(tenancy.tenant_id or "", "") or tenancy.tenant_name or "Tenant"),
        move_in_lock_hash=move_in.lock_hash if move_in else None,
        move_out_lock_hash=move_out.lock_hash if move_out else None,
        property_score=prop_score,
        damage_pct=t["damage_pct"],
        totals=TotalsOut(**{k: t[k] for k in ("damage_pct", "proposed", "agreed", "disputed", "in_dispute", "refund_due")}, deposit=tenancy.deposit),
        findings=findings_out,
        maintenance_reports=[
            MaintenanceReportOut(id=r.id, slot_id=r.slot_id, item_id=r.item_id, description=r.description, reported_at=r.reported_at, category=r.category)
            for r in reports
        ],
        latest_run=RunSummaryOut(
            run_id=run.id, status=run.status, started_at=run.started_at, finished_at=run.finished_at,
            summary_en=run.summary_en, summary_kn=run.summary_kn,
        ) if run else None,
    )
