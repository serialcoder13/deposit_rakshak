"""
routers/runs.py — GET /api/runs/{id}/events (SSE), GET /api/tenancies/{id}/report
(SPEC §7 Reports, runs and findings; ARCHITECTURE §4.2)
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.auth import get_current_user, require_tenancy_role
from app.db import get_session
from app.models import (
    AgentRun,
    AgentStep,
    CaptureSlot,
    Finding,
    FindingClassification,
    Item,
    MaintenanceReport,
    Photo,
    Tenancy,
    User,
)
from app.schemas import (
    CostBreakdown,
    FindingOut,
    MaintenanceReportOut,
    RunSummaryOut,
    TenancyReport,
    TotalsOut,
)
from app import scoring

router = APIRouter(prefix="/api", tags=["runs"])


# ---------------------------------------------------------------------------
# SSE stream
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}/events")
async def run_events(
    run_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Server-Sent Events stream of AgentStep rows for the given run.
    Streams all existing steps, then polls for new ones until the run is done or failed.
    Ends with a synthetic 'done' or 'failed' event.
    """
    run = session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    # Verify access
    require_tenancy_role(run.tenancy_id, ["owner", "tenant"], session, current_user)

    async def event_generator():
        last_seq = -1
        max_polls = 180  # 3 minutes at 1s intervals
        poll = 0

        while poll < max_polls:
            # Re-read steps from DB each iteration
            with Session(session.bind) as s:  # type: ignore[arg-type]
                steps = s.exec(
                    select(AgentStep)
                    .where(AgentStep.run_id == run_id, AgentStep.seq > last_seq)
                    .order_by(AgentStep.seq)
                ).all()
                current_run = s.get(AgentRun, run_id)

            for step in steps:
                data = {
                    "seq": step.seq,
                    "kind": step.kind,
                    "label": step.label,
                    "tool_name": step.tool_name,
                    "payload": json.loads(step.payload),
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_seq = step.seq

            if current_run and current_run.status in ("done", "failed"):
                yield f"data: {json.dumps({'seq': last_seq + 1, 'kind': current_run.status, 'label': current_run.status, 'tool_name': None, 'payload': {}})}\n\n"
                return

            await asyncio.sleep(1)
            poll += 1

        yield f"data: {json.dumps({'seq': last_seq + 1, 'kind': 'error', 'label': 'timeout', 'tool_name': None, 'payload': {}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
    Return the full tenancy report: findings, scores, totals, summaries.
    Totals are recomputed on each read so disputes reflect immediately.
    """
    tenancy = require_tenancy_role(tenancy_id, ["owner", "tenant"], session, current_user)

    findings = session.exec(
        select(Finding).where(Finding.move_out_inspection_id.in_(  # type: ignore[attr-defined]
            select(Finding.move_out_inspection_id)
        ))
    ).all()

    # Get findings via run
    runs = session.exec(select(AgentRun).where(AgentRun.tenancy_id == tenancy_id)).all()
    run_ids = [r.id for r in runs]
    findings = session.exec(
        select(Finding).where(Finding.run_id.in_(run_ids))  # type: ignore[attr-defined]
    ).all() if run_ids else []

    # Build finding outputs
    findings_out = []
    all_items_for_score = []
    total_replacement = 0.0

    # Collect item data for scoring
    items_by_id: dict = {}
    all_item_rows = session.exec(select(Item)).all()
    for it in all_item_rows:
        items_by_id[it.id] = it
        total_replacement += it.replacement_cost

    for f in findings:
        slot = session.get(CaptureSlot, f.slot_id)
        item = items_by_id.get(f.item_id)
        before_photo = session.get(Photo, f.before_photo_id) if f.before_photo_id else None
        after_photo = session.get(Photo, f.after_photo_id) if f.after_photo_id else None

        try:
            cited = json.loads(f.cited_evidence)
        except Exception:
            cited = []

        findings_out.append(
            FindingOut(
                id=f.id,
                run_id=f.run_id,
                slot_id=f.slot_id,
                slot_label=slot.label if slot else "",
                item_id=f.item_id,
                item_type=item.type if item else "",
                before_photo_url=before_photo.url if before_photo else None,
                after_photo_url=after_photo.url if after_photo else None,
                change_type=f.change_type,
                classification=f.classification,
                severity=f.severity,
                confidence=f.confidence,
                region_description=f.region_description,
                reasoning=f.reasoning,
                cited_evidence=cited,
                cost=CostBreakdown(
                    rate_inr=0.0,  # resolved from rate card in task B7
                    quantity=f.quantity,
                    depreciation_factor=f.depreciation_factor,
                    est_cost=f.est_cost,
                    owner_override_cost=f.owner_override_cost,
                    owner_note=f.owner_note,
                ),
                status=f.status,
                tenant_note=f.tenant_note,
                owner_note=f.owner_note,
            )
        )

    # Scoring
    findings_dicts = [
        {
            "classification": str(f.classification),
            "status": str(f.status),
            "est_cost": f.est_cost,
            "owner_override_cost": f.owner_override_cost,
        }
        for f in findings
    ]
    totals_data = scoring.totals(findings_dicts, tenancy.deposit, total_replacement)

    # Property score (grouped by item)
    from collections import defaultdict
    item_damage: dict = defaultdict(list)
    for f in findings:
        if str(f.classification) == "damage":
            item_damage[f.item_id].append(f.severity)

    score_items = [
        {"replacement_cost": it.replacement_cost, "damage_severities": item_damage.get(it.id, [])}
        for it in all_item_rows
    ]
    prop_score = scoring.property_score(score_items) if score_items else 100.0

    # Latest run
    latest_run = None
    if runs:
        run = max(runs, key=lambda r: r.started_at)
        latest_run = RunSummaryOut(
            run_id=run.id,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            summary_en=run.summary_en,
            summary_kn=run.summary_kn,
        )

    reports = session.exec(
        select(MaintenanceReport).where(MaintenanceReport.tenancy_id == tenancy_id)
    ).all()

    return TenancyReport(
        tenancy_id=tenancy_id,
        property_score=prop_score,
        damage_pct=totals_data["damage_pct"],
        totals=TotalsOut(
            damage_pct=totals_data["damage_pct"],
            proposed=totals_data["proposed"],
            agreed=totals_data["agreed"],
            disputed=totals_data["disputed"],
            in_dispute=totals_data["in_dispute"],
            refund_due=totals_data["refund_due"],
            deposit=tenancy.deposit,
        ),
        findings=findings_out,
        maintenance_reports=[
            MaintenanceReportOut(
                id=r.id,
                slot_id=r.slot_id,
                item_id=r.item_id,
                description=r.description,
                reported_at=r.reported_at,
                category=r.category,
            )
            for r in reports
        ],
        latest_run=latest_run,
    )
