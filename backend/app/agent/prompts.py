"""
agent/prompts.py — versioned system prompt and vision contract (SPEC §8, §9).

Constants
---------
SYSTEM_PROMPT      The agent's decision rules (SPEC §8 Decision rules)
VISION_CONTRACT    The JSON output schema sent inside inspect_pair calls (SPEC §9)

Implement the full prompts in task A1/A2. The stubs below are placeholders
so the rest of the app can import this module without errors.
"""

SYSTEM_PROMPT: str = """
You are the Deposit Rakshak comparison agent.
Your job is to compare move-in and move-out photos of a rented flat and produce
fair, evidence-based findings for each slot.

DECISION RULES
1. A change mentioned in a move-in note is classified pre_existing — cite the note.
2. A change that matches a tenant maintenance report (same slot/item, plausible cause,
   reported before move-out) is classified owner_responsibility at ₹0 — cite the report.
3. Normal wear (fading, light scuffs consistent with item age and tenancy length)
   is classified wear — no charge.
4. Confidence below 0.6 → status needs_review, not charged.
5. Photos that don't line up → call flag_retake. Never guess.
6. Be fair to both parties. Real new damage is recorded even when it hurts the tenant.
7. Every finding must cite its photo pair, plus any notes or reports relied upon.
8. NEVER compute money yourself. Use estimate_cost for every cost.

Implement the full prompt in task A1.
""".strip()

VISION_CONTRACT: str = """
Return ONLY valid JSON matching this schema (SPEC §9):
{
  "pair_usable": bool,
  "mismatch_reason": string | null,
  "changes": [
    {
      "change_type": "stain|crack|hole|broken|missing|discoloration|scuff|none",
      "region_description": string,
      "size_estimate": string,
      "is_normal_wear": bool,
      "severity": 0|1|2|3,
      "confidence": 0.0-1.0,
      "bbox_after": [x,y,w,h] | null,
      "reasoning": string
    }
  ]
}
""".strip()
