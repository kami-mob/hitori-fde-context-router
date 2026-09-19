"""Read one exact pinned public GitHub JSON snapshot through the local decision gate.

The resolved record is parsed ONLY from the fetched and SHA-verified bytes.
No separate caller-supplied records, fallback source, writeback, decision
activation, independent permission attestation or production action exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re
from typing import Any

from github_public_pinned_reader import PinnedPublicGitHubReader
from source_read_acquisition_handoff import (
    AcquisitionRequest, FetchedSource, acquire_declared_sources,
)
from minimal_resolver import resolve_current

__all__ = ["PinnedPublicDecisionRequest", "resolve_pinned_public_decision"]

_BLOB_SHA = re.compile(r"[0-9a-f]{40}\Z")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_MAX_DECISIONS = 256
_MAX_JSON_BYTES = 131072


@dataclass(frozen=True)
class PinnedPublicDecisionRequest:
    reader: Any
    source_id: Any
    expected_blob_sha: Any
    domain: Any
    subject: Any
    field: Any
    as_of: Any
    verify_after_days: Any = 30
    no_external_read: Any = False


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate_json_key")
        output[key] = value
    return output


def _reject_json_constant(value: str) -> None:
    raise ValueError("invalid_json_constant")


def _valid_record(record: Any) -> bool:
    if type(record) is not dict:
        return False
    scope = record.get("scope")
    if type(scope) is not dict:
        return False
    if (
        type(record.get("decision_id")) is not str
        or not record["decision_id"]
        or type(record.get("status")) is not str
        or any(type(scope.get(key)) is not str or not scope[key]
               for key in ("domain", "subject", "field"))
    ):
        return False
    for key in ("effective_from", "last_verified", "supersedes"):
        value = record.get(key)
        if value is not None and type(value) is not str:
            return False
    return True


def resolve_pinned_public_decision(request: Any) -> dict[str, Any]:
    """Return only a non-authoritative local classification of pinned bytes.

    The caller independently approves the PUBLIC source, exact expected
    blob SHA and requested decision point. A fabricated test transport
    cannot be detected as genuine GitHub I/O by this reference.
    """
    error = {"state": "DATA_ERROR", "stage": "public_snapshot"}
    verify = {"state": "VERIFY", "stage": "public_snapshot"}
    if type(request) is not PinnedPublicDecisionRequest:
        return error
    try:
        (
            reader, source_id, expected_blob, domain, subject, field,
            as_of, max_age, no_read
        ) = (
            request.reader, request.source_id, request.expected_blob_sha,
            request.domain, request.subject, request.field, request.as_of,
            request.verify_after_days, request.no_external_read,
        )
        if (
            type(reader) is not PinnedPublicGitHubReader
            or type(source_id) is not str
            or type(expected_blob) is not str
            or _BLOB_SHA.fullmatch(expected_blob) is None
            or any(type(v) is not str or not v or len(v) > 100
                   for v in (domain, subject, field))
            or type(as_of) is not str
            or _DATE.fullmatch(as_of) is None
            or date.fromisoformat(as_of).isoformat() != as_of
            or type(max_age) is not int or not 0 <= max_age <= 3650
            or type(no_read) is not bool
        ):
            return error
        prefix = "github:" + reader.owner + "/" + reader.repository + ":"
        if not source_id.startswith(prefix):
            return error
        if source_id[len(prefix):] not in reader.allowed_paths:
            return error
    except Exception:
        return error

    if no_read:
        return verify

    # Exactly one external callback invocation. No fallback, retry or
    # independently supplied decision records can satisfy this contract.
    try:
        receipt = reader(source_id)
    except Exception:
        return verify
    if type(receipt) is not FetchedSource:
        return error
    try:
        raw = receipt.raw_payload
        if (
            type(receipt.source_id) is not str
            or receipt.source_id != source_id
            or type(receipt.source_version) is not str
            or receipt.source_version != reader.commit_sha
            or type(raw) is not bytes
            or len(raw) > _MAX_JSON_BYTES
        ):
            return error
        blob = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw
        ).hexdigest()
        if blob != expected_blob:
            return error

        # The local modeled gate must pass on the SAME receipt, without
        # invoking the actual network callback again.
        gate = acquire_declared_sources(
            AcquisitionRequest((source_id,)),
            lambda requested: receipt if requested == source_id else None,
        )
        if type(gate) is not dict or gate != {
            "state": "PASS",
            "stage": "local_source_read_gate",
            "evidence_scope": "CALLER_SUPPLIED_ADAPTER",
            "read_count": 1,
        }:
            return error

        records = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=_reject_json_constant,
        )
        if (
            type(records) is not list
            or not 0 < len(records) <= _MAX_DECISIONS
            or not all(_valid_record(record) for record in records)
        ):
            return error
        outcome = resolve_current(
            records, domain=domain, subject=subject, field=field,
            as_of=as_of, verify_after_days=max_age,
        )
        if type(outcome) is not dict:
            return error
        state = outcome.get("state")
        if type(state) is not str:
            return error
        if state == "RESOLVED":
            record = outcome.get("record")
            if type(record) is not dict or type(record.get("decision_id")) is not str:
                return error
            # Deliberately do not mark the record ACTIVE/LOCKED, write back,
            # expose the whole raw source or authorize an operational action.
            return {
                "state": "RESOLVED",
                "stage": "local_public_snapshot_resolution",
                "evidence_scope": "PINNED_PUBLIC_FILE_BYTES",
                "decision_id": record["decision_id"],
                "value": record.get("value"),
            }
        if state in ("UNKNOWN", "CONFLICT", "VERIFY", "DATA_ERROR"):
            return {"state": state, "stage": "local_public_snapshot_resolution"}
        return error
    except Exception:
        # No raw payload, decision data, URL or exception detail on failure.
        return error
