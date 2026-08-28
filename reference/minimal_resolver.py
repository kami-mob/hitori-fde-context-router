from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

AUTHORITATIVE = {"LOCKED", "ACTIVE", "SUPERSEDED"}
CURRENT_CAPABLE = {"LOCKED", "ACTIVE"}


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value in (None, ""):
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _scope_key(record: Dict[str, Any]) -> Tuple[str, str, str]:
    scope = record.get("scope") or {}
    return (
        str(scope.get("domain", "")),
        str(scope.get("subject", "")),
        str(scope.get("field", "")),
    )


def validate_registry(records: Iterable[Dict[str, Any]]) -> List[str]:
    records = list(records)
    errors: List[str] = []
    by_id: Dict[str, Dict[str, Any]] = {}

    for idx, record in enumerate(records):
        decision_id = record.get("decision_id")
        if decision_id:
            if decision_id in by_id:
                errors.append(f"duplicate decision_id: {decision_id}")
            by_id[decision_id] = record

        if record.get("status") not in {
            "LOCKED", "ACTIVE", "PROPOSED", "HYPOTHESIS", "SUPERSEDED", "ARCHIVED"
        }:
            errors.append(f"unknown status at index {idx}: {record.get('status')}")

        for field in ("effective_from", "last_verified"):
            try:
                _parse_date(record.get(field))
            except Exception:
                errors.append(f"malformed {field} at index {idx}")

    graph: Dict[str, str] = {}
    for record in records:
        predecessor_id = record.get("supersedes")
        if not predecessor_id:
            continue

        decision_id = record.get("decision_id")
        if not decision_id:
            errors.append("relation-bearing successor missing decision_id")
            continue

        predecessor = by_id.get(predecessor_id)
        if predecessor is None:
            errors.append(f"dangling supersedes: {decision_id}->{predecessor_id}")
            continue

        if predecessor.get("status") not in AUTHORITATIVE:
            errors.append(f"non-authoritative predecessor: {decision_id}->{predecessor_id}")

        if _scope_key(predecessor) != _scope_key(record):
            errors.append(f"cross-scope supersedes: {decision_id}->{predecessor_id}")

        predecessor_date = _parse_date(predecessor.get("effective_from"))
        successor_date = _parse_date(record.get("effective_from"))
        if predecessor_date and successor_date and successor_date < predecessor_date:
            errors.append(f"invalid timing: {decision_id}->{predecessor_id}")

        graph[decision_id] = predecessor_id

    for start in graph:
        seen = set()
        current = start
        while current in graph:
            if current in seen:
                errors.append(f"cycle detected from: {start}")
                break
            seen.add(current)
            current = graph[current]

    successors_by_predecessor: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        predecessor_id = record.get("supersedes")
        if predecessor_id:
            successors_by_predecessor.setdefault(predecessor_id, []).append(record)

    for record in records:
        if record.get("status") == "SUPERSEDED" and record.get("decision_id"):
            successors = [
                successor
                for successor in successors_by_predecessor.get(record["decision_id"], [])
                if successor.get("status") in AUTHORITATIVE
                and _scope_key(successor) == _scope_key(record)
            ]
            if not successors:
                errors.append(f"orphan SUPERSEDED: {record['decision_id']}")

    return sorted(set(errors))


def resolve_current(
    records: Iterable[Dict[str, Any]],
    *,
    domain: str,
    subject: str,
    field: str,
    as_of: str,
    verify_after_days: int = 30,
) -> Dict[str, Any]:
    records = list(records)
    target_scope = (domain, subject, field)
    scope_records = [record for record in records if _scope_key(record) == target_scope]

    if not scope_records:
        return {"state": "UNKNOWN", "reason": "no_records_for_scope"}

    errors = validate_registry(scope_records)
    if errors:
        return {"state": "DATA_ERROR", "errors": errors}

    as_of_date = _parse_date(as_of)
    assert as_of_date is not None

    effective_records = []
    for record in scope_records:
        if record.get("status") not in CURRENT_CAPABLE:
            continue
        effective_from = _parse_date(record.get("effective_from"))
        if effective_from is None or effective_from <= as_of_date:
            effective_records.append(record)

    superseded_ids = {
        record.get("supersedes")
        for record in effective_records
        if record.get("supersedes")
    }
    survivors = [
        record
        for record in effective_records
        if record.get("decision_id") not in superseded_ids
    ]

    if len(survivors) == 0:
        return {"state": "UNKNOWN", "reason": "no_current_survivor"}

    if len(survivors) > 1:
        return {
            "state": "CONFLICT",
            "reason": "multiple_current_survivors",
            "decision_ids": [record.get("decision_id") for record in survivors],
        }

    selected = survivors[0]
    last_verified = _parse_date(selected.get("last_verified"))
    if last_verified is None:
        return {"state": "VERIFY", "reason": "missing_last_verified", "record": selected}

    age_days = (as_of_date - last_verified).days
    if age_days > verify_after_days:
        return {
            "state": "VERIFY",
            "reason": "stale_selected_record",
            "age_days": age_days,
            "record": selected,
        }

    return {"state": "RESOLVED", "record": selected}
