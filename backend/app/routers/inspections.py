"""
routers/inspections.py — Inspection CRUD, photo upload, notes, sign/lock, ghost overlay
(SPEC §7 Inspections, §6 Integrity)
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth import get_current_user, require_tenancy_role
from app.db import get_session
from app.integrity import lock_hash
from app.util import ev
from app.models import (
    CaptureSlot,
    Inspection,
    InspectionStatus,
    InspectionType,
    Photo,
    SlotNote,
    Tenancy,
    User,
)
from app.schemas import InspectionDetail, SlotDetail, SlotNoteOut, SlotPhotoOut

router = APIRouter(prefix="/api/inspections", tags=["inspections"])

PHOTOS_DIR = Path("data/photos")


def _get_inspection_or_404(inspection_id: str, session: Session) -> Inspection:
    obj = session.get(Inspection, inspection_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return obj


def _require_not_locked(inspection: Inspection) -> None:
    if inspection.status == InspectionStatus.locked:
        raise HTTPException(status_code=409, detail="Inspection is locked")


def _require_access(inspection: Inspection, user: User, session: Session) -> str:
    """Return 'owner' or 'tenant'; raise 403 if the user has no access."""
    tenancy = session.get(Tenancy, inspection.tenancy_id)
    if tenancy is None:
        raise HTTPException(status_code=404, detail="Tenancy not found")
    if tenancy.owner_id == user.id:
        return "owner"
    if tenancy.tenant_id == user.id:
        return "tenant"
    raise HTTPException(status_code=403, detail="Not a member of this tenancy")


def _build_detail(inspection: Inspection, session: Session) -> InspectionDetail:
    """Build an InspectionDetail from DB rows."""
    # Slots for the tenancy's property
    tenancy = session.get(Tenancy, inspection.tenancy_id)
    if tenancy is None:
        raise HTTPException(status_code=404, detail="Tenancy not found")

    from app.models import Room, Property
    prop = session.get(Property, tenancy.property_id)
    rooms = session.exec(select(Room).where(Room.property_id == prop.id)).all() if prop else []
    room_ids = [r.id for r in rooms]
    room_names = {r.id: r.name for r in rooms}

    all_slots = []
    for rid in room_ids:
        all_slots += session.exec(select(CaptureSlot).where(CaptureSlot.room_id == rid)).all()
    all_slots.sort(key=lambda s: s.order)

    # Ghost photos: the sealed move-in photo per slot, for move_out / checkin capture
    ghosts: dict = {}
    if ev(inspection.type) != "move_in":
        move_in = next(
            (i for i in session.exec(select(Inspection).where(Inspection.tenancy_id == tenancy.id)).all()
             if ev(i.type) == "move_in" and ev(i.status) == "locked"),
            None,
        )
        if move_in:
            for p in session.exec(select(Photo).where(Photo.inspection_id == move_in.id)).all():
                ghosts[p.slot_id] = p.url

    author_names = {u.id: (u.name or "") for u in session.exec(
        select(User).where(User.id.in_([tenancy.owner_id, tenancy.tenant_id or ""]))  # type: ignore[attr-defined]
    ).all()}

    slot_details: List[SlotDetail] = []
    for slot in all_slots:
        photo = session.exec(
            select(Photo).where(
                Photo.inspection_id == inspection.id,
                Photo.slot_id == slot.id,
            )
        ).first()
        notes = session.exec(
            select(SlotNote).where(
                SlotNote.inspection_id == inspection.id,
                SlotNote.slot_id == slot.id,
            )
        ).all()
        notes_out = [
            SlotNoteOut(
                id=n.id,
                slot_id=n.slot_id,
                author_id=n.author_id,
                author_name=author_names.get(n.author_id, ""),
                text=n.text,
                created_at=n.created_at,
            )
            for n in notes
        ]
        photo_out = (
            SlotPhotoOut(
                id=photo.id,
                url=photo.url,
                sha256=photo.sha256,
                captured_at=photo.captured_at,
                taken_by=photo.taken_by,
            )
            if photo
            else None
        )
        slot_details.append(
            SlotDetail(
                id=slot.id,
                label=slot.label,
                guidance=slot.guidance,
                order=slot.order,
                item_id=slot.item_id,
                photo=photo_out,
                notes=notes_out,
                captured=photo is not None,
                room=room_names.get(slot.room_id, ""),
                ghost_url=ghosts.get(slot.id),
            )
        )

    return InspectionDetail(
        id=inspection.id,
        tenancy_id=inspection.tenancy_id,
        type=inspection.type,
        status=inspection.status,
        signed_by_owner_at=inspection.signed_by_owner_at,
        signed_by_tenant_at=inspection.signed_by_tenant_at,
        lock_hash=inspection.lock_hash,
        slots=slot_details,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{inspection_id}", response_model=InspectionDetail)
def get_inspection(
    inspection_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    inspection = _get_inspection_or_404(inspection_id, session)
    _require_access(inspection, current_user, session)
    return _build_detail(inspection, session)


@router.post("/{inspection_id}/photos")
async def upload_photo(
    inspection_id: str,
    slot_id: str = Form(...),
    sha256: str = Form(...),
    captured_at: str = Form(...),
    device_meta: str = Form(default="{}"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Upload a photo for a slot.
    Server re-hashes the bytes and rejects on mismatch (SPEC §6).
    Stores the file as data/photos/<sha256>.jpg.
    """
    inspection = _get_inspection_or_404(inspection_id, session)
    _require_not_locked(inspection)
    _require_access(inspection, current_user, session)

    # The slot must belong to this tenancy's property
    if slot_id not in {sd.id for sd in _build_detail(inspection, session).slots}:
        raise HTTPException(status_code=422, detail="Unknown slot for this property")

    data = await file.read()
    server_hash = hashlib.sha256(data).hexdigest()
    if server_hash != sha256.lower():
        raise HTTPException(status_code=422, detail="SHA-256 mismatch: upload rejected")

    # Store file
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    dest = PHOTOS_DIR / f"{server_hash}.jpg"
    if not dest.exists():
        dest.write_bytes(data)

    # Remove any previous photo for this slot in this inspection
    existing = session.exec(
        select(Photo).where(
            Photo.inspection_id == inspection_id,
            Photo.slot_id == slot_id,
        )
    ).first()
    if existing:
        session.delete(existing)
        session.flush()

    photo = Photo(
        inspection_id=inspection_id,
        slot_id=slot_id,
        taken_by=current_user.id,
        url=f"/api/photos/{server_hash}.jpg",
        sha256=server_hash,
        captured_at=captured_at,
        device_meta=device_meta,
    )
    session.add(photo)

    # A changed photo invalidates any signature already given
    if ev(inspection.status) == "awaiting_signatures":
        inspection.signed_by_owner_at = None
        inspection.signed_by_tenant_at = None
        inspection.status = InspectionStatus.draft
    session.add(inspection)
    session.commit()
    return {"id": photo.id, "sha256": server_hash, "url": photo.url}


class NoteCreate(BaseModel):
    slot_id: str
    text: str


@router.post("/{inspection_id}/notes")
def add_note(
    inspection_id: str,
    body: NoteCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    inspection = _get_inspection_or_404(inspection_id, session)
    _require_not_locked(inspection)
    _require_access(inspection, current_user, session)

    note = SlotNote(
        inspection_id=inspection_id,
        slot_id=body.slot_id,
        author_id=current_user.id,
        text=body.text,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return {"id": note.id, "ok": True}


@router.post("/{inspection_id}/sign")
def sign_inspection(
    inspection_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Sign the inspection. Locks when both parties have signed (SPEC §6).
    Requires every slot to have a photo.
    """
    inspection = _get_inspection_or_404(inspection_id, session)
    if inspection.status == InspectionStatus.locked:
        raise HTTPException(status_code=409, detail="Already locked")

    role = _require_access(inspection, current_user, session)

    # Verify all slots have photos
    detail = _build_detail(inspection, session)
    missing = [s.label for s in detail.slots if not s.captured]
    if missing:
        raise HTTPException(status_code=409, detail=f"Missing photos for slots: {missing}")

    now = datetime.now(timezone.utc).isoformat()
    tenancy = session.get(Tenancy, inspection.tenancy_id)
    if tenancy is not None and ev(tenancy.invite_status) != "accepted":
        raise HTTPException(status_code=409, detail="The tenant has not accepted the invite yet")
    if role == "owner":
        inspection.signed_by_owner_at = now
    else:
        inspection.signed_by_tenant_at = now

    if inspection.signed_by_owner_at and inspection.signed_by_tenant_at:
        # Both signed — compute lock hash
        photos = session.exec(
            select(Photo).where(Photo.inspection_id == inspection_id)
        ).all()
        notes = session.exec(
            select(SlotNote).where(SlotNote.inspection_id == inspection_id)
        ).all()
        h = lock_hash(
            photo_hashes=[p.sha256 for p in photos],
            note_texts=[n.text for n in notes],
            owner_signed_at=inspection.signed_by_owner_at,
            tenant_signed_at=inspection.signed_by_tenant_at,
        )
        inspection.lock_hash = h
        inspection.status = InspectionStatus.locked
    else:
        inspection.status = InspectionStatus.awaiting_signatures

    session.add(inspection)
    session.commit()
    return {
        "status": inspection.status,
        "lock_hash": inspection.lock_hash,
        "signed_by_owner_at": inspection.signed_by_owner_at,
        "signed_by_tenant_at": inspection.signed_by_tenant_at,
    }


@router.get("/{inspection_id}/ghost/{slot_id}")
def get_ghost(
    inspection_id: str,
    slot_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Return the move-in photo for a slot (used as a ghost overlay during move-out).
    Finds the locked move-in inspection for the same tenancy.
    """
    inspection = _get_inspection_or_404(inspection_id, session)
    _require_access(inspection, current_user, session)

    tenancy_id = inspection.tenancy_id
    move_in = session.exec(
        select(Inspection).where(
            Inspection.tenancy_id == tenancy_id,
            Inspection.type == InspectionType.move_in,
            Inspection.status == InspectionStatus.locked,
        )
    ).first()
    if move_in is None:
        raise HTTPException(status_code=404, detail="No locked move-in inspection")

    photo = session.exec(
        select(Photo).where(
            Photo.inspection_id == move_in.id,
            Photo.slot_id == slot_id,
        )
    ).first()
    if photo is None:
        raise HTTPException(status_code=404, detail="No move-in photo for this slot")

    file_path = PHOTOS_DIR / f"{photo.sha256}.jpg"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Photo file not found")
    return FileResponse(str(file_path), media_type="image/jpeg")
