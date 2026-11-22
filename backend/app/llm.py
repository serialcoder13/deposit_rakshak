"""
llm.py: the ONLY module that talks to the LLM provider (SPEC §8, ARCHITECTURE ADR 7).

Provider: DeepSeek (OpenAI-compatible chat completions, accepts image_url parts).
Thinking is switched off: deepseek-flash reasons by default, which is slow and can
return an empty answer for short JSON.

Public API
    async vision_compare(before_bytes, after_bytes, context) -> dict
    async chat_with_tools(messages, tools, system) -> dict
        {"text", "tool_calls": [{"id","name","arguments"}], "stop", "raw_message"}
"""
from __future__ import annotations

import base64
import json
import re
from typing import Any, Dict, List

import httpx

from app.config import settings

_BASE = settings.llm_api_url.rstrip("/")
_URL = f"{_BASE}/chat/completions"
_HEADERS = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}


def _provider_extras() -> Dict[str, Any]:
    return {"thinking": {"type": "disabled"}} if settings.llm_provider == "deepseek" else {}


def _image_data_url(image_bytes: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()


def parse_json_loose(raw: str) -> Any:
    """Parse model JSON, tolerating code fences, prose around it and trailing commas."""
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidate = re.sub(r",\s*([}\]])", r"\1", text[start:end + 1])
        return json.loads(candidate)
    raise json.JSONDecodeError("no JSON object found", text, 0)


async def _post(payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(_URL, headers=_HEADERS, json={**payload, **_provider_extras()})
        if resp.status_code >= 400:
            raise RuntimeError(f"LLM HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()


async def vision_compare(before_bytes: bytes, after_bytes: bytes, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare the move-in (BEFORE) and move-out (AFTER) photos of one capture slot.
    Returns JSON matching SPEC §9. Retries once on invalid JSON.

    context keys: slot_label, item_type, material, age_years, tenancy_months
    """
    from app.agent.prompts import VISION_CONTRACT, VISION_SYSTEM

    user_text = (
        f"Slot: {context.get('slot_label', '')}. Item: {context.get('item_type', '')} "
        f"({context.get('material', '')}), about {context.get('age_years', 0)} years old at move-in. "
        f"Tenancy length: {context.get('tenancy_months', 0)} months.\n\n{VISION_CONTRACT}"
    )
    payload = {
        "model": settings.llm_vision_model,
        "messages": [
            {"role": "system", "content": VISION_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "BEFORE (move-in photo):"},
                    {"type": "image_url", "image_url": {"url": _image_data_url(before_bytes)}},
                    {"type": "text", "text": "AFTER (move-out photo):"},
                    {"type": "image_url", "image_url": {"url": _image_data_url(after_bytes)}},
                    {"type": "text", "text": user_text},
                ],
            },
        ],
        "max_tokens": 1500,
        "temperature": 0.1,
    }

    last_raw = ""
    for _ in range(2):
        data = await _post(payload, timeout=90.0)
        last_raw = data["choices"][0]["message"].get("content") or ""
        try:
            result = parse_json_loose(last_raw)
            if isinstance(result, dict):
                result.setdefault("pair_usable", True)
                result.setdefault("mismatch_reason", None)
                result.setdefault("changes", [])
                return result
        except json.JSONDecodeError:
            continue
    raise ValueError(f"vision model returned invalid JSON twice: {last_raw[:200]}")


async def chat_with_tools(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], system: str) -> Dict[str, Any]:
    """One tool-use turn. Returns the normalised response plus the raw assistant message for history."""
    all_messages: List[Dict[str, Any]] = ([{"role": "system", "content": system}] if system else []) + messages
    payload: Dict[str, Any] = {
        "model": settings.llm_model,
        "messages": all_messages,
        "max_tokens": 4000,
        "temperature": 0.2,
    }
    if tools:
        payload["tools"] = [{"type": "function", "function": t} for t in tools]
        payload["tool_choice"] = "auto"

    data = await _post(payload, timeout=120.0)
    choice = data["choices"][0]
    message = choice["message"]

    tool_calls = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function", {})
        try:
            args = parse_json_loose(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {"_invalid_json": fn.get("arguments", "")}
        tool_calls.append({"id": tc.get("id", ""), "name": fn.get("name", ""), "arguments": args})

    raw_message: Dict[str, Any] = {"role": "assistant", "content": message.get("content") or ""}
    if message.get("tool_calls"):
        raw_message["tool_calls"] = message["tool_calls"]

    return {
        "text": message.get("content"),
        "tool_calls": tool_calls,
        "stop": choice.get("finish_reason", "stop"),
        "raw_message": raw_message,
    }
