"""
agent/tools.py — all agent tools (SPEC §8, Tools table).

Each tool has:
  - an async Python function
  - a JSON-schema definition exported for the LLM
  - routing through execute(name, args, ctx)

Tools
-----
list_pairs          DB — slots with before/after photo IDs, flags missing photos
inspect_pair        Vision LLM — sends image pair, returns structured JSON
get_item            DB — type, material, age at move-out, useful life, cost
get_slot_notes      DB — notes from move-in with author and time
get_maintenance_reports  DB — tenant issue reports with dates
estimate_cost       Code — rate card × quantity × depreciation (scoring.py)
flag_retake         DB — marks a pair as needing retake
record_finding      DB — saves a finding with classification and cited evidence
finish              DB — closes the run, triggers scoring.totals()

Implement in task A2.
"""
from __future__ import annotations

from typing import Any, Dict, List


TOOL_SCHEMAS: List[Dict[str, Any]] = []
"""JSON-schema definitions sent to the LLM — populated during A2."""


async def execute(name: str, args: Dict[str, Any], ctx: Any) -> Any:
    """
    Dispatch a tool call by name.

    ctx carries the DB session, run_id, tenancy_id, and move-out inspection_id.
    """
    raise NotImplementedError(f"agent.tools.execute({name!r}) — implement in task A2")
