"""
integrity.py — tamper-evidence helpers (SPEC §6).

Pure functions; no database access; unit tested independently.

sha256_bytes(data)              → hex digest of raw bytes
lock_hash(photo_hashes,         → stable hex digest that locks an inspection
          note_texts,
          owner_signed_at,
          tenant_signed_at)
"""
import hashlib
from typing import List


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase hex SHA-256 of *data*."""
    return hashlib.sha256(data).hexdigest()


def lock_hash(
    photo_hashes: List[str],
    note_texts: List[str],
    owner_signed_at: str,
    tenant_signed_at: str,
) -> str:
    """
    Compute the inspection lock hash.

    Order-independent: inputs are sorted before hashing so that the hash
    is stable regardless of the order items were added.
    """
    parts = (
        sorted(photo_hashes)
        + sorted(note_texts)
        + sorted([owner_signed_at, tenant_signed_at])
    )
    combined = "|".join(parts).encode()
    return hashlib.sha256(combined).hexdigest()
