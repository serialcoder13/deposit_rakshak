"""
seed.py — wipe and reseed the demo database (SPEC §14).

Run with:  python -m app.seed

Safe to run repeatedly: it drops all rows and recreates the demo data.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def _months_ago_date(n: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=n * 30)
    return dt.date().isoformat()


def seed() -> None:
    # Ensure data dirs exist
    Path("data/photos").mkdir(parents=True, exist_ok=True)

    from sqlmodel import Session, SQLModel, delete

    from app.db import engine
    from app.models import (
        CaptureSlot,
        Finding,
        AgentRun,
        AgentStep,
        Inspection,
        InviteStatus,
        Item,
        ItemType,
        MaintenanceCategory,
        MaintenanceReport,
        Photo,
        Property,
        RateCard,
        ChangeType,
        RateCardUnit,
        Room,
        SlotNote,
        Tenancy,
        User,
    )

    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        # ----- wipe (order matters for FK constraints) -----
        for model in [
            AgentStep, Finding, AgentRun,
            SlotNote, Photo,
            MaintenanceReport,
            Inspection,
            Tenancy,
            CaptureSlot,
            Item,
            Room,
            Property,
            RateCard,
            User,
        ]:
            s.exec(delete(model))  # type: ignore[arg-type]
        s.commit()

        # ----- Users (SPEC §14) -----
        owner = User(id=str(uuid.uuid4()), phone="9999990001", name="Ravi")
        tenant = User(id=str(uuid.uuid4()), phone="9999990002", name="Meera")
        s.add(owner)
        s.add(tenant)
        s.flush()

        # ----- Property -----
        prop = Property(
            id=str(uuid.uuid4()),
            owner_id=owner.id,
            address="Flat 4B, 12th Cross, Koramangala 5th Block",
            city="Bengaluru",
            preset="Single room",
        )
        s.add(prop)
        s.flush()

        # ----- Room -----
        room = Room(id=str(uuid.uuid4()), property_id=prop.id, name="Hackathon Room", order=1)
        s.add(room)
        s.flush()

        # ----- Items (SPEC §14) -----
        item_wall = Item(
            id=str(uuid.uuid4()),
            room_id=room.id,
            type=ItemType.wall,
            material="paint",
            age_years_at_move_in=4.0,
            useful_life_years=5.0,
            replacement_cost=20000.0,
        )
        item_table = Item(
            id=str(uuid.uuid4()),
            room_id=room.id,
            type=ItemType.table,
            material="wood",
            age_years_at_move_in=6.0,
            useful_life_years=10.0,
            replacement_cost=8000.0,
        )
        item_cushion = Item(
            id=str(uuid.uuid4()),
            room_id=room.id,
            type=ItemType.cushion,
            material="fabric",
            age_years_at_move_in=2.0,
            useful_life_years=3.0,
            replacement_cost=1500.0,
        )
        s.add(item_wall)
        s.add(item_table)
        s.add(item_cushion)
        s.flush()

        # ----- Capture Slots (SPEC §14) -----
        slot_wall_a = CaptureSlot(
            id=str(uuid.uuid4()),
            room_id=room.id,
            item_id=item_wall.id,
            label="Wall A",
            order=1,
            guidance="Stand at the door, face the window wall. Phone in landscape.",
        )
        slot_table = CaptureSlot(
            id=str(uuid.uuid4()),
            room_id=room.id,
            item_id=item_table.id,
            label="Table top",
            order=2,
            guidance="Shoot from directly above the table surface. Include all corners.",
        )
        slot_window = CaptureSlot(
            id=str(uuid.uuid4()),
            room_id=room.id,
            item_id=item_wall.id,
            label="Window wall",
            order=3,
            guidance="Stand facing the window. Capture the full wall including the sill.",
        )
        slot_sofa = CaptureSlot(
            id=str(uuid.uuid4()),
            room_id=room.id,
            item_id=item_cushion.id,
            label="Sofa",
            order=4,
            guidance="Shoot the sofa front-on. Include all cushions.",
        )
        s.add(slot_wall_a)
        s.add(slot_table)
        s.add(slot_window)
        s.add(slot_sofa)
        s.flush()

        # ----- Tenancy (started 11 months ago) -----
        start_date = _months_ago_date(11)
        tenancy = Tenancy(
            id=str(uuid.uuid4()),
            property_id=prop.id,
            owner_id=owner.id,
            tenant_id=tenant.id,
            tenant_phone=tenant.phone,
            tenant_name=tenant.name,
            invite_status=InviteStatus.accepted,
            created_at=_now_iso(),
            start_date=start_date,
            deposit=150000.0,
            monthly_rent=15000.0,
            invite_code="DEMO0001",
        )
        s.add(tenancy)
        s.flush()

        # ----- Maintenance report (SPEC §14) — 2 months ago -----
        report = MaintenanceReport(
            id=str(uuid.uuid4()),
            tenancy_id=tenancy.id,
            slot_id=slot_window.id,
            item_id=item_wall.id,
            description="Damp stain spreading near window, seepage from outside wall",
            reported_at=_days_ago(60),
            category=MaintenanceCategory.seepage,
        )
        s.add(report)
        s.flush()

        # ----- Rate card rows (rate_inr = 0 for now; team fills checked rates) -----
        # (SPEC §10 table)
        rate_rows = [
            # stain / table
            RateCard(change_type=ChangeType.stain, item_type=ItemType.table, severity=1, unit=RateCardUnit.job, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.stain, item_type=ItemType.table, severity=2, unit=RateCardUnit.job, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.stain, item_type=ItemType.table, severity=3, unit=RateCardUnit.job, rate_inr=0.0, source=""),
            # crack / wall
            RateCard(change_type=ChangeType.crack, item_type=ItemType.wall, severity=1, unit=RateCardUnit.sqft, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.crack, item_type=ItemType.wall, severity=2, unit=RateCardUnit.sqft, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.crack, item_type=ItemType.wall, severity=3, unit=RateCardUnit.sqft, rate_inr=0.0, source=""),
            # stain / wall
            RateCard(change_type=ChangeType.stain, item_type=ItemType.wall, severity=1, unit=RateCardUnit.sqft, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.stain, item_type=ItemType.wall, severity=2, unit=RateCardUnit.sqft, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.stain, item_type=ItemType.wall, severity=3, unit=RateCardUnit.sqft, rate_inr=0.0, source=""),
            # hole / wall
            RateCard(change_type=ChangeType.hole, item_type=ItemType.wall, severity=1, unit=RateCardUnit.piece, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.hole, item_type=ItemType.wall, severity=2, unit=RateCardUnit.piece, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.hole, item_type=ItemType.wall, severity=3, unit=RateCardUnit.piece, rate_inr=0.0, source=""),
            # discoloration / cushion
            RateCard(change_type=ChangeType.discoloration, item_type=ItemType.cushion, severity=1, unit=RateCardUnit.piece, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.discoloration, item_type=ItemType.cushion, severity=2, unit=RateCardUnit.piece, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.discoloration, item_type=ItemType.cushion, severity=3, unit=RateCardUnit.piece, rate_inr=0.0, source=""),
            # broken / tile
            RateCard(change_type=ChangeType.broken, item_type=ItemType.tile, severity=1, unit=RateCardUnit.piece, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.broken, item_type=ItemType.tile, severity=2, unit=RateCardUnit.piece, rate_inr=0.0, source=""),
            RateCard(change_type=ChangeType.broken, item_type=ItemType.tile, severity=3, unit=RateCardUnit.piece, rate_inr=0.0, source=""),
        ]
        for r in rate_rows:
            s.add(r)
        s.commit()

    print("✅ Seed complete.")
    print(f"   Owner  phone: 9999990001  OTP: 123456")
    print(f"   Tenant phone: 9999990002  OTP: 123456")
    print(f"   Tenancy invite code: DEMO0001")
    print(f"   Any other 10-digit number can sign up (OTP 123456).")
    print(f"   Rate card rows have rate_inr=0: costs fall back to replacement value x severity x depreciation")
    print(f"   until the team fills in checked rates (PUT /api/rate-card).")


if __name__ == "__main__":
    seed()
