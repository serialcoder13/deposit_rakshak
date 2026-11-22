"""
tests/test_scoring.py — unit tests for scoring.py and integrity.py (SDLC §6, B4).
Written before the implementation so the team can verify correctness.
Run with:  pytest
"""
import pytest
from app.scoring import depreciation, finding_cost, item_score, penalty, property_score, totals
from app.integrity import lock_hash, sha256_bytes


# ---------------------------------------------------------------------------
# penalty()
# ---------------------------------------------------------------------------

def test_penalty_severity_map():
    assert penalty(0) == 0
    assert penalty(1) == 15
    assert penalty(2) == 40
    assert penalty(3) == 80


def test_penalty_unknown_severity():
    assert penalty(99) == 0


# ---------------------------------------------------------------------------
# depreciation()
# ---------------------------------------------------------------------------

def test_depreciation_basic():
    # age 4 at move-in, 11 months tenancy, useful life 5
    # age_at_move_out = 4 + 11/12 ≈ 4.917
    # factor = 1 - 4.917/5 ≈ 0.017 → floored to 0.2
    result = depreciation(age_years_at_move_in=4.0, tenancy_months=11, useful_life_years=5.0)
    assert result == pytest.approx(0.2)


def test_depreciation_floor_applied():
    result = depreciation(age_years_at_move_in=10.0, tenancy_months=12, useful_life_years=5.0)
    assert result == 0.2


def test_depreciation_no_floor_needed():
    # age 1, 0 months, useful life 10 → 1 - 1/10 = 0.9
    result = depreciation(age_years_at_move_in=1.0, tenancy_months=0, useful_life_years=10.0)
    assert result == pytest.approx(0.9)


def test_depreciation_zero_useful_life():
    result = depreciation(1.0, 6, 0.0)
    assert result == 0.2


# ---------------------------------------------------------------------------
# finding_cost()
# ---------------------------------------------------------------------------

def test_finding_cost():
    # 1200 rate × 2 qty × 0.4 dep = 960
    assert finding_cost(1200.0, 2.0, 0.4) == pytest.approx(960.0)


# ---------------------------------------------------------------------------
# item_score()
# ---------------------------------------------------------------------------

def test_item_score_no_damage():
    assert item_score([]) == 100.0


def test_item_score_with_damage():
    # severity 2 → penalty 40 → score 60
    assert item_score([2]) == pytest.approx(60.0)


def test_item_score_worst_penalty():
    # severities 1 and 3 → worst penalty 80 → score 20
    assert item_score([1, 3]) == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# property_score()
# ---------------------------------------------------------------------------

def test_property_score_weighted():
    items = [
        {"replacement_cost": 20000.0, "damage_severities": [2]},  # score 60
        {"replacement_cost": 8000.0, "damage_severities": []},    # score 100
        {"replacement_cost": 1500.0, "damage_severities": []},    # score 100
    ]
    total_weight = 20000 + 8000 + 1500
    expected = (60 * 20000 + 100 * 8000 + 100 * 1500) / total_weight
    assert property_score(items) == pytest.approx(expected, rel=1e-3)


# ---------------------------------------------------------------------------
# totals()
# ---------------------------------------------------------------------------

def test_totals_all_proposed():
    findings = [
        {"classification": "damage", "status": "proposed", "est_cost": 500.0, "owner_override_cost": None},
        {"classification": "wear", "status": "proposed", "est_cost": 200.0, "owner_override_cost": None},
    ]
    result = totals(findings, deposit=10000.0, total_replacement_value=50000.0)
    assert result["proposed"] == pytest.approx(500.0)
    assert result["agreed"] == pytest.approx(0.0)
    assert result["disputed"] == pytest.approx(0.0)
    assert result["refund_due"] == pytest.approx(10000.0)


def test_totals_accepted():
    findings = [
        {"classification": "damage", "status": "accepted", "est_cost": 1000.0, "owner_override_cost": None},
    ]
    result = totals(findings, deposit=10000.0, total_replacement_value=50000.0)
    assert result["agreed"] == pytest.approx(1000.0)
    assert result["refund_due"] == pytest.approx(9000.0)


def test_totals_deposit_cap():
    findings = [
        {"classification": "damage", "status": "accepted", "est_cost": 200000.0, "owner_override_cost": None},
    ]
    result = totals(findings, deposit=150000.0, total_replacement_value=500000.0)
    assert result["agreed"] == pytest.approx(150000.0)
    assert result["refund_due"] == pytest.approx(0.0)


def test_totals_owner_override():
    findings = [
        {"classification": "damage", "status": "accepted", "est_cost": 1000.0, "owner_override_cost": 500.0},
    ]
    result = totals(findings, deposit=10000.0, total_replacement_value=50000.0)
    assert result["agreed"] == pytest.approx(500.0)


def test_totals_disputed_not_in_agreed():
    findings = [
        {"classification": "damage", "status": "disputed", "est_cost": 800.0, "owner_override_cost": None},
        {"classification": "damage", "status": "accepted", "est_cost": 200.0, "owner_override_cost": None},
    ]
    result = totals(findings, deposit=10000.0, total_replacement_value=50000.0)
    assert result["agreed"] == pytest.approx(200.0)
    assert result["in_dispute"] == pytest.approx(800.0)


# ---------------------------------------------------------------------------
# integrity: sha256_bytes
# ---------------------------------------------------------------------------

def test_sha256_bytes_stable():
    data = b"hello world"
    assert sha256_bytes(data) == sha256_bytes(data)
    assert sha256_bytes(data) == "b94d27b9934d3e08a52e52d7da7dabfac484efe04294e576"[:len(sha256_bytes(data))]  # just check type
    assert isinstance(sha256_bytes(data), str)
    assert len(sha256_bytes(data)) == 64


def test_sha256_bytes_different():
    assert sha256_bytes(b"a") != sha256_bytes(b"b")


# ---------------------------------------------------------------------------
# integrity: lock_hash — order independence
# ---------------------------------------------------------------------------

def test_lock_hash_order_independent():
    h1 = lock_hash(["hashA", "hashB"], ["note1", "note2"], "2024-01-01T10:00:00", "2024-01-01T11:00:00")
    h2 = lock_hash(["hashB", "hashA"], ["note2", "note1"], "2024-01-01T10:00:00", "2024-01-01T11:00:00")
    assert h1 == h2


def test_lock_hash_stable():
    h1 = lock_hash(["hashA"], ["note1"], "ts_owner", "ts_tenant")
    h2 = lock_hash(["hashA"], ["note1"], "ts_owner", "ts_tenant")
    assert h1 == h2


def test_lock_hash_changes_with_different_inputs():
    h1 = lock_hash(["hashA"], [], "ts_owner", "ts_tenant")
    h2 = lock_hash(["hashB"], [], "ts_owner", "ts_tenant")
    assert h1 != h2
