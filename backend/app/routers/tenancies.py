"""
routers/tenancies.py — GET /api/tenancies/{id}, POST issues, POST compare
(SPEC §7 Tenancy, Reports, runs)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import get_current_user, require_tenancy_role
from app.db import get_session
from app.models import (
    AgentRun,
    AgentRunStatus,
    CaptureSlot,
    Inspection,
    InspectionStatus,
    InspectionType,
    MaintenanceCategory,
    MaintenanceReport,
    Tenancy,
    User,
)

router = APIRouter(prefix="/api", tags=["tenancies"])


# ---------------------------------------------------------------------------
# Request / response bodies
# ---------------------------------------------------------------------------

class InspectionSummary(BaseModel):
    id: str
    type: str
    status: str


class RunSummary(BaseModel):
    id: str
    status: str
    started_at: str
    finished_at: Optional[str]


class ReportOut(BaseModel):
    id: str
    slot_id: Optional[str]
    item_id: Optional[str]
    description: str
    reported_at: str
    category: str


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


class IssueCreate(BaseModel):
    description: str
    category: MaintenanceCategory
    slot_id: Optional[str] = None
    item_id: Optional[str] = None


class CompareResponse(BaseModel):
    run_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/tenancies/{tenancy_id}", response_model=TenancyDetail)
def get_tenancy(
    tenancy_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tenancy = require_tenancy_role(tenancy_id, ["owner", "tenant"], session, current_user)

    inspections = session.exec(
        select(Inspection).where(Inspection.tenancy_id == tenancy_id)
    ).all()
    reports = session.exec(
        select(MaintenanceReport).where(MaintenanceReport.tenancy_id == tenancy_id)
    ).all()
    runs = session.exec(
        select(AgentRun).where(AgentRun.tenancy_id == tenancy_id)
    ).all()

    latest_run: Optional[RunSummary] = None
    if runs:
        run = max(runs, key=lambda r: r.started_at)
        latest_run = RunSummary(
            id=run.id,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )

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
            InspectionSummary(id=i.id, type=i.type, status=i.status) for i in inspections
        ],
        maintenance_reports=[
            ReportOut(
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


@router.post("/tenancies/{tenancy_id}/issues")
def create_issue(
    tenancy_id: str,
    body: IssueCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """File a maintenance or check-in report (tenant only, SPEC §3)."""
    tenancy = require_tenancy_role(tenancy_id, ["tenant"], session, current_user)

    report = MaintenanceReport(
        tenancy_id=tenancy.id,
        item_id=body.item_id,
        slot_id=body.slot_id,
        description=body.description,
        reported_at=datetime.now(timezone.utc).isoformat(),
        category=body.category,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return {"id": report.id, "ok": True}


@router.post("/tenancies/{tenancy_id}/inspections")
def create_inspection(
    tenancy_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Create a new inspection of the given type.
    A move_out requires a locked move_in first (SPEC §7).
    """
    require_tenancy_role(tenancy_id, ["owner", "tenant"], session, current_user)

    inspection_type_str = body.get("type", "")
    try:
        inspection_type = InspectionType(inspection_type_str)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid inspection type: {inspection_type_str}")

    if inspection_type == InspectionType.move_out:
        # Require a locked move_in
        move_in = session.exec(
            select(Inspection).where(
                Inspection.tenancy_id == tenancy_id,
                Inspection.type == InspectionType.move_in,
                Inspection.status == InspectionStatus.locked,
            )
        ).first()
        if move_in is None:
            raise HTTPException(status_code=409, detail="A locked move-in inspection is required before move-out")

    inspection = Inspection(tenancy_id=tenancy_id, type=inspection_type)
    session.add(inspection)
    session.commit()
    session.refresh(inspection)
    return {"id": inspection.id, "type": inspection.type, "status": inspection.status}


@router.post("/tenancies/{tenancy_id}/compare", response_model=CompareResponse)
def start_compare(
    tenancy_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Start the agent comparison run (SPEC §7). Returns run_id immediately."""
    require_tenancy_role(tenancy_id, ["owner", "tenant"], session, current_user)

    run = AgentRun(
        tenancy_id=tenancy_id,
        status=AgentRunStatus.running,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    # Agent loop is implemented in task A3
    from app.db import engine as db_engine
    from app.agent.loop import run_agent
    background_tasks.add_task(run_agent, run.id, tenancy_id, db_engine)

    return CompareResponse(run_id=run.id)
