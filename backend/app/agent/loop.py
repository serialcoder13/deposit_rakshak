"""
agent/loop.py: the tool-use loop (SPEC §8, ARCHITECTURE §4.2).

- at most 40 model turns and 3 minutes
- tool calls from one turn run concurrently (max 4 at a time)
- every call and result is written as an AgentStep for the live trace
- a successful run is saved to data/last_run.json; DEMO_MODE=1 replays
  data/demo_run.json (or last_run.json) without calling the LLM
"""
from __future__ import annotations

import asyncio
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List

from sqlmodel import Session, select

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    TOOL_SCHEMAS,
    RunContext,
    call_label,
    execute,
    load_context,
    result_label,
    t_finish,
)
from app.config import settings
from app.llm import chat_with_tools
from app.models import (
    AgentRun,
    AgentRunStatus,
    AgentStep,
    ChangeType,
    Finding,
    FindingClassification,
    FindingStatus,
    MaintenanceReport,
    SlotNote,
)
from app.util import ev, now_iso

MAX_TURNS = 40
TIME_LIMIT_S = 180
PARALLEL = 4
DATA = Path("data")


def _set_status(ctx: RunContext, status: AgentRunStatus) -> None:
    with ctx.session() as s:
        run = s.get(AgentRun, ctx.run_id)
        run.status = status
        run.finished_at = now_iso()
        s.add(run)
        s.commit()


async def run_agent(run_id: str, tenancy_id: str, engine: Any) -> None:
    """Entry point for BackgroundTasks."""
    ctx = load_context(run_id, tenancy_id, engine)
    try:
        demo = DATA / "demo_run.json" if (DATA / "demo_run.json").exists() else DATA / "last_run.json"
        if settings.demo_mode and demo.exists():
            await _replay(ctx, json.loads(demo.read_text()))
        else:
            await _agent(ctx)
            _save_recording(ctx)
        _set_status(ctx, AgentRunStatus.done)
    except Exception as e:  # noqa: BLE001  (show any failure in the trace)
        ctx.step("error", f"The AI check stopped: {str(e)[:200]}", payload={"error": str(e)[:1000]})
        _set_status(ctx, AgentRunStatus.failed)


async def _agent(ctx: RunContext) -> None:
    ready = [p for p in ctx.pairs.values() if p["before_photo_id"] and p["after_photo_id"]]
    ctx.step("thought", f"Starting the move-out check: {len(ready)} of {len(ctx.pairs)} slots have both photos",
             payload={"slots": len(ctx.pairs), "ready": len(ready)})

    messages: List[Dict[str, Any]] = [{
        "role": "user",
        "content": (f"Inspect this tenancy at move-out. Tenancy length: {ctx.tenancy_months} months. "
                    f"There are {len(ctx.pairs)} capture slots. Start with list_pairs."),
    }]
    sem = asyncio.Semaphore(PARALLEL)
    started = time.monotonic()
    nudges = 0

    async def run_one(call: dict) -> dict:
        async with sem:
            try:
                return await execute(call["name"], call["arguments"], ctx)
            except Exception as e:  # noqa: BLE001
                return {"error": str(e)[:300]}

    for _ in range(MAX_TURNS):
        if time.monotonic() - started > TIME_LIMIT_S:
            ctx.step("error", "Time limit reached, wrapping up")
            break
        resp = await chat_with_tools(messages, TOOL_SCHEMAS, SYSTEM_PROMPT)
        messages.append(resp["raw_message"])
        text = (resp.get("text") or "").strip()
        if text and resp["tool_calls"]:
            ctx.step("thought", text[:300])

        calls = resp["tool_calls"]
        if not calls:
            if ctx.finished:
                break
            nudges += 1
            if nudges > 2:
                break
            messages.append({"role": "user", "content": "Continue: record the remaining findings, then call finish."})
            continue

        for c in calls:
            ctx.step("tool_call", call_label(c["name"], c["arguments"], ctx), c["name"], c["arguments"])
        results = await asyncio.gather(*(run_one(c) for c in calls))
        for c, r in zip(calls, results):
            ctx.step("tool_result", result_label(c["name"], r), c["name"], r)
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(r, default=str)[:8000]})
        if ctx.finished:
            break

    if not ctx.finished:  # safety net: always close with totals
        r = await t_finish(ctx, "", "")
        ctx.step("tool_result", result_label("finish", r), "finish", r)


# ---------------------------------------------------------------------------
# Demo recording and replay
# ---------------------------------------------------------------------------

def _save_recording(ctx: RunContext) -> None:
    with ctx.session() as s:
        steps = s.exec(select(AgentStep).where(AgentStep.run_id == ctx.run_id).order_by(AgentStep.seq)).all()
        findings = s.exec(select(Finding).where(Finding.run_id == ctx.run_id)).all()
        run = s.get(AgentRun, ctx.run_id)
        rec = {
            "steps": [{"kind": ev(x.kind), "label": x.label, "tool_name": x.tool_name, "payload": json.loads(x.payload)} for x in steps],
            "findings": [{
                "slot_label": ctx.slot_label(f.slot_id),
                **{k: ev(getattr(f, k)) for k in (
                    "change_type", "classification", "severity", "confidence", "region_description", "reasoning",
                    "quantity", "rate_inr", "cost_basis", "bbox_after", "depreciation_factor", "est_cost", "status")},
            } for f in findings],
            "summary_en": run.summary_en,
            "summary_kn": run.summary_kn,
        }
    DATA.mkdir(exist_ok=True)
    (DATA / "last_run.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1, default=str))


async def _replay(ctx: RunContext, rec: dict) -> None:
    """Replay a recorded run through the same trace; findings are matched to slots by label."""
    by_label = {p["label"]: p for p in ctx.pairs.values()}
    pending = list(rec.get("findings", []))
    for st in rec.get("steps", []):
        await asyncio.sleep(random.uniform(0.4, 0.9))
        ctx.step(st["kind"], st["label"], st.get("tool_name"), st.get("payload"))
        if st.get("tool_name") == "record_finding" and st["kind"] == "tool_result" and pending:
            _insert_finding(ctx, pending.pop(0), by_label)
    for f in pending:
        _insert_finding(ctx, f, by_label)
    with ctx.session() as s:
        run = s.get(AgentRun, ctx.run_id)
        run.summary_en, run.summary_kn = rec.get("summary_en"), rec.get("summary_kn")
        s.add(run)
        s.commit()


def _insert_finding(ctx: RunContext, f: dict, by_label: dict) -> None:
    p = by_label.get(f["slot_label"])
    if p is None:
        return
    with ctx.session() as s:
        cited: list = []
        if f["classification"] == "pre_existing":
            cited = [n.id for n in s.exec(select(SlotNote).where(
                SlotNote.inspection_id == ctx.move_in_id, SlotNote.slot_id == p["slot_id"])).all()]
        elif f["classification"] == "owner_responsibility":
            cited = [r.id for r in s.exec(select(MaintenanceReport).where(MaintenanceReport.tenancy_id == ctx.tenancy_id)).all()
                     if r.slot_id == p["slot_id"] or (p["item_id"] and r.item_id == p["item_id"])]
        s.add(Finding(
            run_id=ctx.run_id, move_out_inspection_id=ctx.move_out_id, item_id=p["item_id"], slot_id=p["slot_id"],
            before_photo_id=p["before_photo_id"], after_photo_id=p["after_photo_id"],
            change_type=ChangeType(f["change_type"]), classification=FindingClassification(f["classification"]),
            severity=f["severity"], confidence=f["confidence"], region_description=f["region_description"],
            reasoning=f["reasoning"], quantity=f["quantity"], rate_inr=f["rate_inr"], cost_basis=f["cost_basis"],
            bbox_after=f["bbox_after"], depreciation_factor=f["depreciation_factor"], est_cost=f["est_cost"],
            status=FindingStatus(f["status"]),
            cited_evidence=json.dumps(cited),
        ))
        s.commit()
