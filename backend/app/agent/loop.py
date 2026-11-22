"""
agent/loop.py — the tool-use loop (SPEC §8, ARCHITECTURE §4.2).

Responsibilities
----------------
- Run at most 40 iterations within a 3-minute hard limit
- Call llm.chat_with_tools with the agent tools
- Dispatch tool calls via agent/tools.py, running up to 4 concurrently
- Write an AgentStep row (thought, tool_call, tool_result, error) for every event
- On finish, call scoring.totals() and persist the scores to the AgentRun row

Implement in task A3.
"""
from __future__ import annotations

from typing import Any, Dict


async def run_agent(run_id: str, tenancy_id: str, session_factory: Any) -> None:
    """
    Entry point called by BackgroundTasks.

    1. Load the tenancy and its move-in / move-out inspections.
    2. Build the initial message and tool schemas.
    3. Drive the tool-use loop.
    4. On finish or error, update AgentRun.status and write summary rows.
    """
    raise NotImplementedError("agent.loop.run_agent — implement in task A3")
