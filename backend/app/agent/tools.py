"""
agent/tools.py: the agent's tools (SPEC §8).

The model decides which tools to call; the code here enforces the rules:
- money is computed only by price() (rate card, else replacement value) with depreciation,
- confidence < 0.6 -> needs_review,
- "pre_existing" / "owner_responsibility" must cite a real note / report, else needs_review.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sqlmodel import Session, select

from app import scoring
from app.llm import vision_compare
from app.models import (
    AgentRun,
    AgentRunStatus,
    AgentStep,
    AgentStepKind,
    CaptureSlot,
    ChangeType,
    Finding,
    FindingClassification,
    FindingStatus,
    Inspection,
    Item,
    MaintenanceReport,
    Photo,
    RateCard,
    Room,
    SlotNote,
    Tenancy,
    User,
)
from app.util import ev, months_between, now_iso

PHOTOS_DIR = Path("data/photos")

CHANGE_TYPES = [c.value for c in ChangeType]
CLASSIFICATIONS = [c.value for c in FindingClassification]
_CHANGE_ALIASES = {
    "chip": "broken", "dent": "broken", "scratch": "scuff", "mark": "stain", "burn": "discoloration",
    "fading": "discoloration", "fade": "discoloration", "damp": "stain", "seepage": "stain", "tear": "broken",
}
CLASS_LABEL = {
    "damage": "Damage", "wear": "Normal wear", "pre_existing": "Already there",
    "owner_responsibility": "Owner's repair", "none": "No change",
}


# ---------------------------------------------------------------------------
# Run context
# ---------------------------------------------------------------------------

@dataclass
class RunContext:
    run_id: str
    tenancy_id: str
    engine: Any
    property_id: str = ""
    deposit: float = 0.0
    tenancy_months: float = 0.0
    move_in_id: Optional[str] = None
    move_out_id: Optional[str] = None
    pairs: Dict[str, dict] = field(default_factory=dict)       # slot_id -> pair info
    vision: Dict[str, dict] = field(default_factory=dict)      # slot_id -> vision result
    finished: bool = False
    seq: int = 0

    def session(self) -> Session:
        return Session(self.engine)

    def step(self, kind: str, label: str, tool_name: Optional[str] = None, payload: Any = None) -> None:
        with self.session() as s:
            s.add(AgentStep(
                run_id=self.run_id, seq=self.seq, kind=AgentStepKind(kind), label=label[:300],
                tool_name=tool_name, payload=json.dumps(payload or {}, default=str)[:20000], created_at=now_iso(),
            ))
            s.commit()
        self.seq += 1

    def slot_label(self, slot_id: str) -> str:
        return self.pairs.get(slot_id, {}).get("label", slot_id[:8])


def load_context(run_id: str, tenancy_id: str, engine: Any) -> RunContext:
    ctx = RunContext(run_id=run_id, tenancy_id=tenancy_id, engine=engine)
    with ctx.session() as s:
        t = s.get(Tenancy, tenancy_id)
        ctx.property_id, ctx.deposit = t.property_id, t.deposit
        ctx.tenancy_months = months_between(t.start_date, t.end_date)
        inspections = s.exec(select(Inspection).where(Inspection.tenancy_id == tenancy_id)).all()
        move_ins = [i for i in inspections if ev(i.type) == "move_in" and ev(i.status) == "locked"]
        move_outs = [i for i in inspections if ev(i.type) == "move_out"]
        ctx.move_in_id = move_ins[-1].id if move_ins else None
        ctx.move_out_id = move_outs[-1].id if move_outs else None

        rooms = {r.id: r.name for r in s.exec(select(Room).where(Room.property_id == ctx.property_id)).all()}
        slots = s.exec(select(CaptureSlot).where(CaptureSlot.room_id.in_(list(rooms) or [""]))).all()  # type: ignore[attr-defined]
        for slot in sorted(slots, key=lambda x: x.order):
            before = s.exec(select(Photo).where(Photo.inspection_id == ctx.move_in_id, Photo.slot_id == slot.id)).first()
            after = s.exec(select(Photo).where(Photo.inspection_id == ctx.move_out_id, Photo.slot_id == slot.id)).first()
            item = s.get(Item, slot.item_id) if slot.item_id else None
            ctx.pairs[slot.id] = {
                "slot_id": slot.id,
                "label": slot.label,
                "room": rooms.get(slot.room_id, ""),
                "item_id": slot.item_id,
                "item_type": ev(item.type) if item else "",
                "material": item.material if item else "",
                "age_years": item.age_years_at_move_in if item else 0,
                "before_photo_id": before.id if before else None,
                "after_photo_id": after.id if after else None,
                "before_sha": before.sha256 if before else None,
                "after_sha": after.sha256 if after else None,
            }
    return ctx


# ---------------------------------------------------------------------------
# Pricing (code only, never the model)
# ---------------------------------------------------------------------------

def price(s: Session, item: Optional[Item], change_type: str, severity: int, quantity: float, months: float) -> dict:
    if item is None or severity <= 0:
        return {"basis": "not_charged", "rate_inr": 0.0, "quantity": quantity, "depreciation": 1.0, "cost": 0.0,
                "explanation": "Nothing to charge"}
    dep = scoring.depreciation(item.age_years_at_move_in, months, item.useful_life_years)
    row = s.exec(select(RateCard).where(
        RateCard.change_type == ChangeType(change_type), RateCard.item_type == item.type, RateCard.severity == severity
    )).first()
    if row and row.rate_inr > 0:
        qty = max(0.1, min(float(quantity or 1), 200.0)) if ev(row.unit) != "job" else 1.0
        cost = scoring.finding_cost(row.rate_inr, qty, dep)
        return {"basis": "rate_card", "rate_inr": row.rate_inr, "quantity": qty, "depreciation": round(dep, 2),
                "cost": cost, "explanation": f"₹{row.rate_inr:g} per {ev(row.unit)} × {qty:g} × depreciation {dep:.2f}"}
    cost = scoring.replacement_basis_cost(item.replacement_cost, severity, dep)
    return {"basis": "replacement_value", "rate_inr": 0.0, "quantity": 1.0, "depreciation": round(dep, 2), "cost": cost,
            "explanation": f"Replacement value ₹{item.replacement_cost:,.0f} × {scoring.penalty(severity)}% (severity {severity}) "
                           f"× depreciation {dep:.2f}"}


def _norm_change(value: Any) -> str:
    v = str(value or "").strip().lower()
    v = _CHANGE_ALIASES.get(v, v)
    return v if v in CHANGE_TYPES else "scuff"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

async def t_list_pairs(ctx: RunContext) -> dict:
    return {"pairs": [
        {k: p[k] for k in ("slot_id", "label", "room", "item_id", "item_type")}
        | {"has_before": bool(p["before_photo_id"]), "has_after": bool(p["after_photo_id"])}
        for p in ctx.pairs.values()
    ], "tenancy_months": ctx.tenancy_months}


async def t_inspect_pair(ctx: RunContext, slot_id: str) -> dict:
    p = ctx.pairs.get(slot_id)
    if p is None:
        return {"error": f"unknown slot_id {slot_id}"}
    if not (p["before_sha"] and p["after_sha"]):
        return {"slot_id": slot_id, "label": p["label"], "pair_usable": False, "mismatch_reason": "missing photo", "changes": []}
    before = (PHOTOS_DIR / f"{p['before_sha']}.jpg").read_bytes()
    after = (PHOTOS_DIR / f"{p['after_sha']}.jpg").read_bytes()
    result = await vision_compare(before, after, {
        "slot_label": p["label"], "item_type": p["item_type"], "material": p["material"],
        "age_years": p["age_years"], "tenancy_months": ctx.tenancy_months,
    })
    changes = []
    for i, c in enumerate(result.get("changes") or []):
        ct = _norm_change(c.get("change_type"))
        if str(c.get("change_type", "")).lower() == "none":
            continue
        changes.append({
            "index": i,
            "change_type": ct,
            "region_description": str(c.get("region_description", ""))[:200],
            "size_estimate": str(c.get("size_estimate", ""))[:60],
            "is_normal_wear": bool(c.get("is_normal_wear", False)),
            "severity": max(0, min(3, int(c.get("severity", 1) or 0))),
            "confidence": max(0.0, min(1.0, float(c.get("confidence", 0.5) or 0))),
            "bbox_after": c.get("bbox_after"),
            "reasoning": str(c.get("reasoning", ""))[:300],
        })
    out = {"slot_id": slot_id, "label": p["label"], "pair_usable": bool(result.get("pair_usable", True)),
           "mismatch_reason": result.get("mismatch_reason"), "changes": changes}
    ctx.vision[slot_id] = out
    return out


async def t_get_item(ctx: RunContext, slot_id: str = "", item_id: str = "") -> dict:
    item_id = item_id or ctx.pairs.get(slot_id, {}).get("item_id") or ""
    with ctx.session() as s:
        item = s.get(Item, item_id) if item_id else None
        if item is None:
            return {"error": "item not found"}
        age_out = item.age_years_at_move_in + ctx.tenancy_months / 12
        return {"item_id": item.id, "type": ev(item.type), "material": item.material,
                "age_years_at_move_in": item.age_years_at_move_in, "age_years_at_move_out": round(age_out, 1),
                "useful_life_years": item.useful_life_years, "replacement_cost": item.replacement_cost,
                "depreciation": round(scoring.depreciation(item.age_years_at_move_in, ctx.tenancy_months, item.useful_life_years), 2)}


async def t_get_slot_notes(ctx: RunContext, slot_id: str) -> dict:
    with ctx.session() as s:
        t = s.get(Tenancy, ctx.tenancy_id)
        notes = s.exec(select(SlotNote).where(SlotNote.inspection_id == ctx.move_in_id, SlotNote.slot_id == slot_id)).all()
        return {"slot_id": slot_id, "label": ctx.slot_label(slot_id), "move_in_notes": [
            {"note_id": n.id, "text": n.text, "author_role": "owner" if n.author_id == t.owner_id else "tenant",
             "created_at": n.created_at} for n in notes]}


async def t_get_maintenance_reports(ctx: RunContext, slot_id: str) -> dict:
    item_id = ctx.pairs.get(slot_id, {}).get("item_id")
    with ctx.session() as s:
        rows = s.exec(select(MaintenanceReport).where(MaintenanceReport.tenancy_id == ctx.tenancy_id)).all()
        hits = [r for r in rows if r.slot_id == slot_id or (item_id and r.item_id == item_id)]
        return {"slot_id": slot_id, "label": ctx.slot_label(slot_id), "reports": [
            {"report_id": r.id, "category": ev(r.category), "description": r.description, "reported_at": r.reported_at,
             "same_slot": r.slot_id == slot_id} for r in hits]}


async def t_estimate_cost(ctx: RunContext, slot_id: str, change_type: str, severity: int, quantity: float = 1) -> dict:
    item_id = ctx.pairs.get(slot_id, {}).get("item_id")
    with ctx.session() as s:
        item = s.get(Item, item_id) if item_id else None
        result = price(s, item, _norm_change(change_type), max(0, min(3, int(severity))), quantity, ctx.tenancy_months)
    return {"slot_id": slot_id, "label": ctx.slot_label(slot_id), **result}


def _valid_citations(s: Session, ctx: RunContext, slot_id: str, ids: List[str], kind: str) -> List[str]:
    item_id = ctx.pairs.get(slot_id, {}).get("item_id")
    valid = []
    for i in ids:
        if kind == "note":
            n = s.get(SlotNote, i)
            if n and n.inspection_id == ctx.move_in_id and n.slot_id == slot_id:
                valid.append(i)
        else:
            r = s.get(MaintenanceReport, i)
            if r and r.tenancy_id == ctx.tenancy_id and (r.slot_id == slot_id or (item_id and r.item_id == item_id)):
                valid.append(i)
    return valid


def _upsert_finding(s: Session, ctx: RunContext, slot_id: str, change_type: str, classification: str) -> Finding:
    existing = s.exec(select(Finding).where(
        Finding.run_id == ctx.run_id, Finding.slot_id == slot_id,
        Finding.change_type == ChangeType(change_type), Finding.classification == FindingClassification(classification),
    )).first()
    if existing:
        return existing
    p = ctx.pairs[slot_id]
    return Finding(
        run_id=ctx.run_id, move_out_inspection_id=ctx.move_out_id, item_id=p["item_id"], slot_id=slot_id,
        before_photo_id=p["before_photo_id"], after_photo_id=p["after_photo_id"],
        change_type=ChangeType(change_type), classification=FindingClassification(classification),
    )


async def t_record_finding(
    ctx: RunContext, slot_id: str, change_type: str, classification: str, severity: int, confidence: float,
    region_description: str = "", reasoning: str = "", cited_evidence: Optional[List[str]] = None,
    quantity: float = 1, change_index: Optional[int] = None,
) -> dict:
    if slot_id not in ctx.pairs:
        return {"error": f"unknown slot_id {slot_id}"}
    change_type = _norm_change(change_type)
    classification = classification if classification in CLASSIFICATIONS else "damage"
    severity = max(0, min(3, int(severity or 0)))
    confidence = max(0.0, min(1.0, float(confidence or 0)))
    cited = [str(c) for c in (cited_evidence or [])]
    notes: List[str] = []

    with ctx.session() as s:
        if classification == "pre_existing":
            cited = _valid_citations(s, ctx, slot_id, cited, "note")
            if not cited:
                notes.append("No matching move-in note was found, so a person should check this.")
        elif classification == "owner_responsibility":
            cited = _valid_citations(s, ctx, slot_id, cited, "report")
            if not cited:
                notes.append("No matching maintenance report was found, so a person should check this.")
        else:
            cited = _valid_citations(s, ctx, slot_id, cited, "note") + _valid_citations(s, ctx, slot_id, cited, "report")

        item = s.get(Item, ctx.pairs[slot_id]["item_id"]) if ctx.pairs[slot_id]["item_id"] else None
        cost = price(s, item, change_type, severity, quantity, ctx.tenancy_months) if classification == "damage" \
            else {"basis": "not_charged", "rate_inr": 0.0, "quantity": 1.0, "depreciation": 1.0, "cost": 0.0}

        # bbox from the vision result for this slot
        bbox = None
        vision_changes = ctx.vision.get(slot_id, {}).get("changes", [])
        match = next((c for c in vision_changes if c["index"] == change_index), None) if change_index is not None else None
        match = match or next((c for c in vision_changes if c["change_type"] == change_type), None)
        if match and isinstance(match.get("bbox_after"), list) and len(match["bbox_after"]) == 4:
            bbox = json.dumps(match["bbox_after"])

        f = _upsert_finding(s, ctx, slot_id, change_type, classification)
        f.severity = severity
        f.confidence = confidence
        f.region_description = region_description[:200]
        f.reasoning = (reasoning + (" " + " ".join(notes) if notes else ""))[:600]
        f.cited_evidence = json.dumps(cited)
        f.quantity = cost["quantity"]
        f.rate_inr = cost["rate_inr"]
        f.depreciation_factor = cost["depreciation"]
        f.est_cost = cost["cost"]
        f.cost_basis = cost["basis"]
        f.bbox_after = bbox
        f.status = FindingStatus.needs_review if (confidence < 0.6 or notes) else FindingStatus.proposed
        s.add(f)
        s.commit()
        s.refresh(f)
        return {"finding_id": f.id, "label": ctx.slot_label(slot_id), "classification": classification,
                "status": ev(f.status), "charged_inr": f.est_cost, "cost_basis": f.cost_basis, "cited": cited}


async def t_flag_retake(ctx: RunContext, slot_id: str, reason: str = "") -> dict:
    if slot_id not in ctx.pairs:
        return {"error": f"unknown slot_id {slot_id}"}
    with ctx.session() as s:
        f = _upsert_finding(s, ctx, slot_id, "none", "none")
        f.severity, f.confidence = 0, 0.0
        f.reasoning = f"Retake needed: {reason or 'the photos do not show the same spot clearly'}"[:600]
        f.cost_basis, f.est_cost = "not_charged", 0.0
        f.status = FindingStatus.needs_review
        s.add(f)
        s.commit()
    return {"slot_id": slot_id, "label": ctx.slot_label(slot_id), "flagged": True}


_KN_TOTALS = "ಠೇವಣಿ ₹{deposit}. ಪ್ರಸ್ತಾವಿತ ಕಡಿತ ₹{proposed}. ಒಪ್ಪಿದರೆ ಹಿಂತಿರುಗಿಸಬೇಕಾದ ಮೊತ್ತ ₹{refund}."


def _inr(v: float) -> str:
    """Indian digit grouping: 150000 -> 1,50,000."""
    n = int(round(v))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return ("-" if n < 0 else "") + s


def current_totals(ctx: RunContext) -> dict:
    with ctx.session() as s:
        findings = s.exec(select(Finding).where(Finding.run_id == ctx.run_id)).all()
        items = s.exec(select(Item).where(Item.room_id.in_(  # type: ignore[attr-defined]
            [r.id for r in s.exec(select(Room).where(Room.property_id == ctx.property_id)).all()] or [""]))).all()
        return scoring.totals(
            [{"classification": ev(f.classification), "status": ev(f.status), "est_cost": f.est_cost,
              "owner_override_cost": f.owner_override_cost} for f in findings],
            ctx.deposit, sum(i.replacement_cost for i in items),
        ) | {"count": len(findings)}


async def t_finish(ctx: RunContext, summary_en: str = "", summary_kn: str = "") -> dict:
    t = current_totals(ctx)
    en_tail = (f" Deposit ₹{_inr(ctx.deposit)}. Proposed deduction ₹{_inr(t['proposed'])}. "
               f"Refund due if accepted: ₹{_inr(ctx.deposit - t['proposed'])}.")
    kn_tail = " " + _KN_TOTALS.format(deposit=_inr(ctx.deposit), proposed=_inr(t["proposed"]),
                                      refund=_inr(ctx.deposit - t["proposed"]))
    with ctx.session() as s:
        run = s.get(AgentRun, ctx.run_id)
        run.summary_en = ((summary_en or "The move-out inspection is complete.").strip() + en_tail)[:2000]
        run.summary_kn = ((summary_kn or "ಮನೆ ಬಿಡುವ ತಪಾಸಣೆ ಪೂರ್ಣಗೊಂಡಿದೆ.").strip() + kn_tail)[:2000]
        s.add(run)
        s.commit()
    ctx.finished = True
    return {"done": True, "findings": t["count"], "proposed_inr": t["proposed"], "refund_if_accepted_inr": ctx.deposit - t["proposed"]}


# ---------------------------------------------------------------------------
# Schemas + dispatch
# ---------------------------------------------------------------------------

def _obj(props: dict, required: List[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


_SLOT = {"type": "string", "description": "slot_id from list_pairs"}

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {"name": "list_pairs", "description": "List every capture slot with whether it has a move-in (before) and move-out (after) photo.",
     "parameters": _obj({}, [])},
    {"name": "inspect_pair", "description": "Vision check of one slot: compares the move-in and move-out photos and returns the changes seen.",
     "parameters": _obj({"slot_id": _SLOT}, ["slot_id"])},
    {"name": "get_item", "description": "Item behind a slot: type, material, age at move-in and move-out, useful life, replacement value.",
     "parameters": _obj({"slot_id": _SLOT}, ["slot_id"])},
    {"name": "get_slot_notes", "description": "Notes written on this slot during move-in (e.g. 'chip already here').",
     "parameters": _obj({"slot_id": _SLOT}, ["slot_id"])},
    {"name": "get_maintenance_reports", "description": "Issues the tenant reported during the tenancy for this slot or its item.",
     "parameters": _obj({"slot_id": _SLOT}, ["slot_id"])},
    {"name": "estimate_cost", "description": "Price a damage change. Computed by code from the rate card or replacement value, with depreciation.",
     "parameters": _obj({"slot_id": _SLOT, "change_type": {"type": "string", "enum": CHANGE_TYPES[:-1]},
                         "severity": {"type": "integer", "minimum": 1, "maximum": 3},
                         "quantity": {"type": "number", "description": "sq ft or pieces; 1 if unsure"}},
                        ["slot_id", "change_type", "severity"])},
    {"name": "record_finding", "description": "Save one finding for a real change. Cost is computed by code.",
     "parameters": _obj({
         "slot_id": _SLOT,
         "change_type": {"type": "string", "enum": CHANGE_TYPES[:-1]},
         "classification": {"type": "string", "enum": ["damage", "wear", "pre_existing", "owner_responsibility"]},
         "severity": {"type": "integer", "minimum": 0, "maximum": 3},
         "confidence": {"type": "number", "minimum": 0, "maximum": 1},
         "region_description": {"type": "string"},
         "reasoning": {"type": "string", "description": "one or two sentences citing the evidence"},
         "cited_evidence": {"type": "array", "items": {"type": "string"}, "description": "note_id / report_id values relied on"},
         "quantity": {"type": "number"},
         "change_index": {"type": "integer", "description": "index of the change from inspect_pair"},
     }, ["slot_id", "change_type", "classification", "severity", "confidence", "reasoning"])},
    {"name": "flag_retake", "description": "Mark a slot whose photos do not line up (different spot, too dark, blurred). No charge.",
     "parameters": _obj({"slot_id": _SLOT, "reason": {"type": "string"}}, ["slot_id", "reason"])},
    {"name": "finish", "description": "Close the inspection with a short summary for both parties (no amounts).",
     "parameters": _obj({"summary_en": {"type": "string"}, "summary_kn": {"type": "string", "description": "the same in Kannada"}},
                        ["summary_en", "summary_kn"])},
]

TOOLS: Dict[str, Callable[..., Any]] = {
    "list_pairs": t_list_pairs, "inspect_pair": t_inspect_pair, "get_item": t_get_item,
    "get_slot_notes": t_get_slot_notes, "get_maintenance_reports": t_get_maintenance_reports,
    "estimate_cost": t_estimate_cost, "record_finding": t_record_finding, "flag_retake": t_flag_retake,
    "finish": t_finish,
}


async def execute(name: str, args: Dict[str, Any], ctx: RunContext) -> Any:
    fn = TOOLS.get(name)
    if fn is None:
        return {"error": f"unknown tool {name}"}
    if "_invalid_json" in args:
        return {"error": "arguments were not valid JSON, call again"}
    import inspect
    allowed = set(inspect.signature(fn).parameters) - {"ctx"}
    try:
        return await fn(ctx, **{k: v for k, v in args.items() if k in allowed})
    except TypeError as e:
        return {"error": f"bad arguments: {e}"}


# ---------------------------------------------------------------------------
# Human labels for the live trace
# ---------------------------------------------------------------------------

def call_label(name: str, args: dict, ctx: RunContext) -> str:
    lab = ctx.slot_label(args.get("slot_id", "")) if args.get("slot_id") else ""
    return {
        "list_pairs": "Pairing move-in and move-out photos",
        "inspect_pair": f"Inspecting {lab}",
        "get_item": f"Looking up the age and value of {lab}",
        "get_slot_notes": f"Reading move-in notes for {lab}",
        "get_maintenance_reports": f"Checking the tenant's issue reports for {lab}",
        "estimate_cost": f"Pricing the {args.get('change_type', 'change')} on {lab}",
        "record_finding": f"Recording: {CLASS_LABEL.get(args.get('classification', ''), 'finding')} on {lab}",
        "flag_retake": f"Photos for {lab} need a retake",
        "finish": "Writing the summary",
    }.get(name, name)


def result_label(name: str, result: Any) -> str:
    if not isinstance(result, dict):
        return "done"
    if result.get("error"):
        return f"Problem: {result['error']}"
    lab = result.get("label", "")
    if name == "list_pairs":
        pairs = result.get("pairs", [])
        ready = sum(1 for p in pairs if p["has_before"] and p["has_after"])
        return f"{ready} of {len(pairs)} slots have both photos"
    if name == "inspect_pair":
        if not result.get("pair_usable", True):
            return f"{lab}: photos don't match ({result.get('mismatch_reason') or 'unclear'})"
        ch = result.get("changes", [])
        if not ch:
            return f"{lab}: no change"
        parts = ", ".join(f"{c['change_type']} (severity {c['severity']})" for c in ch[:3])
        return f"{lab}: {len(ch)} change{'s' if len(ch) > 1 else ''}: {parts}"
    if name == "get_slot_notes":
        notes = result.get("move_in_notes", [])
        return f"{lab}: \"{notes[0]['text']}\"" if notes else f"{lab}: no move-in notes"
    if name == "get_maintenance_reports":
        reps = result.get("reports", [])
        return (f"{lab}: tenant reported {reps[0]['category']} on {reps[0]['reported_at'][:10]}"
                if reps else f"{lab}: no issues reported")
    if name == "get_item":
        return f"{result.get('type', '')}: {result.get('age_years_at_move_out', '')} yrs old, depreciation {result.get('depreciation', '')}"
    if name == "estimate_cost":
        return f"{lab}: ₹{_inr(result.get('cost', 0))} ({result.get('explanation', '')})"
    if name == "record_finding":
        c = CLASS_LABEL.get(result.get("classification", ""), "")
        review = " · needs review" if result.get("status") == "needs_review" else ""
        return f"{lab}: {c}, ₹{_inr(result.get('charged_inr', 0))}{review}"
    if name == "flag_retake":
        return f"{lab}: flagged for retake"
    if name == "finish":
        return f"{result.get('findings', 0)} findings. Proposed deduction ₹{_inr(result.get('proposed_inr', 0))}"
    return "done"
