import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from minimal_resolver import resolve_current


def load():
    with open(ROOT / "reference" / "sample_decisions.json", encoding="utf-8") as f:
        return json.load(f)


def test_current():
    result = resolve_current(
        load(), domain="demo", subject="starter", field="price", as_of="2026-08-28"
    )
    assert result["state"] == "RESOLVED"
    assert result["record"]["value"] == 200


def test_future_successor_not_early():
    records = load()
    records.append({
        "decision_id": "PRICE-003",
        "scope": {"domain": "demo", "subject": "starter", "field": "price"},
        "status": "ACTIVE",
        "effective_from": "2026-09-01",
        "supersedes": "PRICE-002",
        "last_verified": "2026-08-28",
        "value": 300,
    })
    result = resolve_current(
        records, domain="demo", subject="starter", field="price", as_of="2026-08-28"
    )
    assert result["state"] == "RESOLVED"
    assert result["record"]["decision_id"] == "PRICE-002"


def test_future_successor_after_effective():
    records = load()
    records.append({
        "decision_id": "PRICE-003",
        "scope": {"domain": "demo", "subject": "starter", "field": "price"},
        "status": "ACTIVE",
        "effective_from": "2026-09-01",
        "supersedes": "PRICE-002",
        "last_verified": "2026-09-01",
        "value": 300,
    })
    result = resolve_current(
        records, domain="demo", subject="starter", field="price", as_of="2026-09-02"
    )
    assert result["state"] == "RESOLVED"
    assert result["record"]["decision_id"] == "PRICE-003"


def test_unknown_field():
    result = resolve_current(
        load(), domain="demo", subject="starter", field="unknown", as_of="2026-08-28"
    )
    assert result["state"] == "UNKNOWN"


def test_multiple_survivors_conflict():
    records = load()
    records.append({
        "decision_id": "PRICE-X",
        "scope": {"domain": "demo", "subject": "starter", "field": "price"},
        "status": "ACTIVE",
        "effective_from": "2026-08-20",
        "last_verified": "2026-08-28",
        "value": 200,
    })
    result = resolve_current(
        records, domain="demo", subject="starter", field="price", as_of="2026-08-28"
    )
    assert result["state"] == "CONFLICT"


def test_dangling_fails_closed():
    records = load()
    records.append({
        "decision_id": "BROKEN",
        "scope": {"domain": "demo", "subject": "starter", "field": "price"},
        "status": "ACTIVE",
        "effective_from": "2026-08-20",
        "supersedes": "DOES-NOT-EXIST",
        "last_verified": "2026-08-28",
        "value": 1,
    })
    result = resolve_current(
        records, domain="demo", subject="starter", field="price", as_of="2026-08-28"
    )
    assert result["state"] == "DATA_ERROR"


def test_unrelated_scope_isolation():
    records = load() + [{
        "decision_id": "BAD",
        "scope": {"domain": "other", "subject": "x", "field": "y"},
        "status": "ACTIVE",
        "effective_from": "2026-08-20",
        "supersedes": "MISSING",
        "last_verified": "2026-08-28",
        "value": "bad",
    }]
    result = resolve_current(
        records, domain="demo", subject="starter", field="price", as_of="2026-08-28"
    )
    assert result["state"] == "RESOLVED"


def run():
    tests = [
        test_current,
        test_future_successor_not_early,
        test_future_successor_after_effective,
        test_unknown_field,
        test_multiple_survivors_conflict,
        test_dangling_fails_closed,
        test_unrelated_scope_isolation,
    ]
    for test in tests:
        test()
    print(f"{len(tests)}/{len(tests)} PASS")


if __name__ == "__main__":
    run()
