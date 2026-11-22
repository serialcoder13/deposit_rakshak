"""
llm.py — DeepSeek LLM provider adapter (SPEC §8, ARCHITECTURE ADR 7).

DeepSeek exposes an OpenAI-compatible REST API, so we use httpx directly
(no SDK dependency) and keep everything in this one file.

Public API
----------
async vision_compare(before_bytes, after_bytes, context) -> dict
    Sends a before/after image pair with the vision contract (SPEC §9).
    Returns validated JSON. Retries once on invalid JSON.

async chat_with_tools(messages, tools, system) -> dict
    Sends a tool-use chat request and returns a normalised response:
    {"text": str | None, "tool_calls": [{"id", "name", "arguments"}], "stop": str}

Env vars used (via app.config.settings)
    LLM_API_KEY         DeepSeek API key
    LLM_MODEL           Chat model, default "deepseek-chat"
    LLM_VISION_MODEL    Vision model, default "deepseek-chat"
    LLM_API_URL         Base URL, default "https://api.deepseek.com"
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, List

import httpx

from app.config import settings

_BASE = settings.llm_api_url.rstrip("/")
_HEADERS = {
    "Authorization": f"Bearer {settings.llm_api_key}",
    "Content-Type": "application/json",
}


def _image_data_url(image_bytes: bytes) -> str:
    """Encode raw JPEG bytes as a base64 data URL."""
    b64 = base64.b64encode(image_bytes).decode()
    return f"data:image/jpeg;base64,{b64}"


async def vision_compare(
    before_bytes: bytes,
    after_bytes: bytes,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Call the DeepSeek vision model with the before/after pair and return
    structured JSON matching the contract in SPEC §9.

    context keys: slot_label, item_type, material, age_years, tenancy_months

    Raises ValueError if the model returns invalid JSON after one retry.
    """
    from app.agent.prompts import VISION_CONTRACT

    slot_label = context.get("slot_label", "")
    item_type = context.get("item_type", "")
    material = context.get("material", "")
    age_years = context.get("age_years", 0)
    tenancy_months = context.get("tenancy_months", 0)

    user_text = (
        f"Slot: {slot_label}. Item: {item_type} ({material}), "
        f"{age_years} years old at move-in, tenancy {tenancy_months} months.\n"
        f"{VISION_CONTRACT}"
    )

    payload = {
        "model": settings.llm_vision_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "BEFORE (move-in photo):"},
                    {"type": "image_url", "image_url": {"url": _image_data_url(before_bytes)}},
                    {"type": "text", "text": "AFTER (move-out photo):"},
                    {"type": "image_url", "image_url": {"url": _image_data_url(after_bytes)}},
                    {"type": "text", "text": user_text},
                ],
            }
        ],
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(2):
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{_BASE}/v1/chat/completions", headers=_HEADERS, json=payload)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            if attempt == 1:
                raise ValueError(f"DeepSeek returned invalid JSON after retry: {raw[:200]}")
            # strip markdown fences if present
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                continue  # will retry once

    raise ValueError("vision_compare failed to get valid JSON")


async def chat_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    system: str,
) -> Dict[str, Any]:
    """
    Call DeepSeek with tool-use (function calling) and return a normalised dict:
    {
        "text": str | None,
        "tool_calls": [{"id": str, "name": str, "arguments": dict}],
        "stop": str,  # "tool_calls" | "stop" | "length"
    }
    """
    all_messages: List[Dict[str, Any]] = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)

    payload: Dict[str, Any] = {
        "model": settings.llm_model,
        "messages": all_messages,
        "max_tokens": 2048,
    }
    if tools:
        # DeepSeek uses OpenAI function-calling format
        payload["tools"] = [
            {"type": "function", "function": t} for t in tools
        ]
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{_BASE}/v1/chat/completions", headers=_HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]
    message = choice["message"]
    stop_reason = choice.get("finish_reason", "stop")

    tool_calls = []
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function", {})
        try:
            args = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}
        tool_calls.append({"id": tc.get("id", ""), "name": fn.get("name", ""), "arguments": args})

    return {
        "text": message.get("content"),
        "tool_calls": tool_calls,
        "stop": stop_reason,
    }
