"""
scoring.py — deterministic cost and score functions (SPEC §10).

Pure functions; no database access; no LLM calls; unit tested first.

Key rules
---------
- Penalty:  severity 0→0, 1→15, 2→40, 3→80 (% of replacement cost)
- Depreciation: max(0.2, 1 - age_at_move_out / useful_life_years)
- Only `damage` findings carry a penalty; wear/pre_existing/owner_responsibility/none → 0
- Deposit cap: proposed/agreed/disputed are each capped at the deposit amount
- Totals follow the status rules in SPEC §10
"""
from __future__ import annotations

from typing import Any, Dict, List


SEVERITY_PENALTY: Dict[int, int] = {0: 0, 1: 15, 2: 40, 3: 80}


def penalty(severity: int) -> int:
    """Return the percentage penalty for a given severity (0–3)."""
    return SEVERITY_PENALTY.get(severity, 0)


def depreciation(
    age_years_at_move_in: float,
    tenancy_months: float,
    useful_life_years: float,
) -> float:
    """
    Return the depreciation factor (0.2–1.0).

    age_at_move_out = age_years_at_move_in + tenancy_months / 12
    factor = max(0.2, 1 - age_at_move_out / useful_life_years)
    """
    age_at_move_out = age_years_at_move_in + tenancy_months / 12.0
    if useful_life_years <= 0:
        return 0.2
    factor = 1.0 - age_at_move_out / useful_life_years
    return max(0.2, factor)


def finding_cost(rate: float, quantity: float, dep_factor: float) -> float:
    """Return rate × quantity × depreciation_factor, rounded to 2 dp."""
    return round(rate * quantity * dep_factor, 2)


def item_score(finding_severities: List[int]) -> float:
    """
    100 minus the worst penalty among the item's *damage* findings.
    Receives a list of severity integers for damage findings on this item.
    """
    if not finding_severities:
        return 100.0
    worst = max(penalty(s) for s in finding_severities)
    return max(0.0, 100.0 - worst)


def property_score(
    items: List[Dict[str, Any]],
) -> float:
    """
    Weighted average of item scores, weighted by each item's replacement_cost.

    Each dict in `items` must have:
      - replacement_cost: float
      - damage_severities: List[int]  — severities of damage findings for this item
    """
    total_weight = sum(i["replacement_cost"] for i in items)
    if total_weight == 0:
        # All zero weights: unweighted average
        scores = [item_score(i["damage_severities"]) for i in items]
        return sum(scores) / len(scores) if scores else 100.0

    weighted_sum = sum(
        item_score(i["damage_severities"]) * i["replacement_cost"] for i in items
    )
    return round(weighted_sum / total_weight, 2)


def totals(
    findings: List[Dict[str, Any]],
    deposit: float,
    total_replacement_value: float,
) -> Dict[str, float]:
    """
    Compute the financial totals from a list of finding dicts.

    Each finding dict must have:
      - classification: str  ("damage", "wear", "pre_existing", "owner_responsibility", "none")
      - status: str          ("proposed", "needs_review", "accepted", "disputed")
      - est_cost: float
      - owner_override_cost: float | None

    Returns:
      damage_pct, proposed, agreed, disputed, in_dispute, refund_due
    """
    def effective_cost(f: Dict[str, Any]) -> float:
        if f.get("owner_override_cost") is not None:
            return float(f["owner_override_cost"])
        return float(f.get("est_cost", 0.0))

    damage_total = 0.0
    proposed_total = 0.0
    agreed_total = 0.0
    disputed_total = 0.0

    for f in findings:
        if f["classification"] != "damage":
            continue
        cost = effective_cost(f)
        damage_total += cost
        if f["status"] in ("proposed", "accepted"):
            proposed_total += cost
        if f["status"] == "accepted":
            agreed_total += cost
        if f["status"] == "disputed":
            disputed_total += cost

    damage_pct = (
        round(damage_total / total_replacement_value * 100, 2)
        if total_replacement_value > 0
        else 0.0
    )

    proposed_capped = min(proposed_total, deposit)
    agreed_capped = min(agreed_total, deposit)
    disputed_capped = min(disputed_total, deposit)

    return {
        "damage_pct": damage_pct,
        "proposed": round(proposed_capped, 2),
        "agreed": round(agreed_capped, 2),
        "disputed": round(disputed_capped, 2),
        "in_dispute": round(disputed_capped, 2),
        "refund_due": round(deposit - agreed_capped, 2),
    }


def replacement_basis_cost(replacement_cost: float, severity: int, dep_factor: float) -> float:
    """
    Fallback when the rate card has no checked rate for this change:
    replacement_cost × penalty% × depreciation. Still deterministic and explainable,
    and based on the owner's own replacement value, never on an AI number.
    """
    return round(replacement_cost * penalty(severity) / 100.0 * dep_factor, 2)
