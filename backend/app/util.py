"""
util.py: small shared helpers (enum values, time, phone numbers).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional

from fastapi import HTTPException


def ev(value: Any) -> Any:
    """Plain value of an enum member (str(enum) gives 'Cls.member', not the value)."""
    return value.value if isinstance(value, Enum) else value


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalise_phone(raw: str) -> str:
    """
    Return a 10-digit Indian mobile number.
    Accepts spaces, dashes, a +91 / 91 prefix or a leading 0. Raises 422 otherwise.
    """
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 10:
        raise HTTPException(status_code=422, detail="Enter a 10-digit mobile number")
    return digits


def pretty_phone(phone: str) -> str:
    """98765 00002 style, for messages."""
    return f"{phone[:5]} {phone[5:]}" if len(phone) == 10 else phone


def months_between(start_iso: str, end_iso: Optional[str] = None) -> float:
    """Tenancy length in months (fractional), from an ISO date to an ISO date or today."""
    try:
        start = date.fromisoformat(start_iso[:10])
    except ValueError:
        return 0.0
    end = date.fromisoformat(end_iso[:10]) if end_iso else datetime.now(timezone.utc).date()
    return max(0.0, round((end - start).days / 30.44, 1))
