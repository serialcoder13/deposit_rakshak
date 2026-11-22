"""
routers/findings.py — PATCH /api/findings/{id}, GET/PUT /api/rate-card
(SPEC §7 Reports, runs and findings)
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import get_current_user, require_tenancy_role
from app.db import get_session
from app.models import AgentRun, Finding, FindingStatus, RateCard, Tenancy, User

router = APIRouter(prefix="/api", tags=["findings"])


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class FindingPatch(BaseModel):
    # Tenant fields
    status: Optional[FindingStatus] = None
    tenant_note: Optional[str] = None
    # Owner fields
    owner_override_cost: Optional[float] = None
    owner_note: Optional[str] = None


class RateCardRow(BaseModel):
    id: str
    change_type: str
    item_type: str
    severity: int
    unit: str
    rate_inr: float
    source: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.patch("/findings/{finding_id}")
def patch_finding(
    finding_id: str,
    body: FindingPatch,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Tenant: update status (accepted | disputed) and tenant_note.
    Owner:  update owner_override_cost and owner_note.
    (SPEC §7, §3)
    """
    finding = session.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Resolve tenancy via AgentRun
    run = session.get(AgentRun, finding.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    tenancy = require_tenancy_role(run.tenancy_id, ["owner", "tenant"], session, current_user)

    is_owner = tenancy.owner_id == current_user.id
    is_tenant = tenancy.tenant_id == current_user.id

    if is_tenant:
        if body.status is not None:
            if body.status not in (FindingStatus.accepted, FindingStatus.disputed):
                raise HTTPException(status_code=422, detail="Tenant can only accept or dispute")
            finding.status = body.status
        if body.tenant_note is not None:
            finding.tenant_note = body.tenant_note

    if is_owner:
        if body.owner_override_cost is not None:
            finding.owner_override_cost = body.owner_override_cost
        if body.owner_note is not None:
            finding.owner_note = body.owner_note

    session.add(finding)
    session.commit()
    return {"id": finding.id, "status": finding.status, "ok": True}


@router.get("/rate-card", response_model=List[RateCardRow])
def get_rate_card(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(select(RateCard)).all()
    return [
        RateCardRow(
            id=r.id,
            change_type=r.change_type,
            item_type=r.item_type,
            severity=r.severity,
            unit=r.unit,
            rate_inr=r.rate_inr,
            source=r.source,
        )
        for r in rows
    ]


@router.put("/rate-card")
def update_rate_card(
    rows: List[RateCardRow],
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Replace rate_inr and source for existing rows (owner only in a real app; open for now)."""
    for row_in in rows:
        rc = session.get(RateCard, row_in.id)
        if rc:
            rc.rate_inr = row_in.rate_inr
            rc.source = row_in.source
            session.add(rc)
    session.commit()
    return {"ok": True}
