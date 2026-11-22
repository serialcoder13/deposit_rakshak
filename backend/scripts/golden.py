"""
scripts/golden.py — Run vision_compare on every before/after pair in tests/golden/
and print the JSON result to stdout. (BOB_PLAYBOOK A1)

Usage:
  cd backend
  python scripts/golden.py

Expects pairs named like:
  tests/golden/01_before.jpg  tests/golden/01_after.jpg
  tests/golden/02_before.jpg  tests/golden/02_after.jpg
  ...

Implement after completing llm.py (task A1).
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.llm import vision_compare


async def main() -> None:
    golden_dir = Path(__file__).parent.parent / "tests" / "golden"
    pairs = sorted(golden_dir.glob("*_before.jpg"))

    if not pairs:
        print("No golden pairs found in tests/golden/. Add *_before.jpg / *_after.jpg pairs.")
        return

    for before_path in pairs:
        prefix = before_path.stem.replace("_before", "")
        after_path = golden_dir / f"{prefix}_after.jpg"
        if not after_path.exists():
            print(f"[SKIP] {before_path.name}: no matching after file")
            continue

        before_bytes = before_path.read_bytes()
        after_bytes = after_path.read_bytes()
        context = {
            "slot_label": prefix,
            "item_type": "wall",
            "material": "paint",
            "age_years": 4,
            "tenancy_months": 11,
        }

        print(f"\n--- {prefix} ---")
        try:
            result = await vision_compare(before_bytes, after_bytes, context)
            print(json.dumps(result, indent=2))
        except Exception as exc:
            print(f"ERROR: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
