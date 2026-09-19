"""Pure/local comparison of supplied Source Read Evidence with fresh derivation.

This module validates in-memory caller-supplied values. It does not fetch
a source, authenticate a caller, evaluate Source Read Gate, or assert that
a read was real, current, authorized, complete or trustworthy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from source_read_evidence import SourceReadEvidence, derive_evidence

__all__ = ["SourceReadEvidenceBindingRequest", "verify_binding"]

_FIELDS = (
    "source_id",
    "source_identity_hash",
    "source_version_binding_hash",
    "raw_payload_hash",
)
_MISSING = object()


@dataclass(frozen=True)
class SourceReadEvidenceBindingRequest:
    """Pair one observation request with evidence supplied by the caller."""

    observation_request: Any = None
    supplied_evidence: Any = None


def _read_once(obj: Any, name: str) -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return _MISSING


def _read_four(obj: SourceReadEvidence) -> tuple[tuple[Any, ...], bool]:
    """Attempt ALL fields exactly once, before type-checking any field."""
    values = tuple(_read_once(obj, name) for name in _FIELDS)
    if any(value is _MISSING for value in values):
        return values, False
    return values, all(type(value) is str for value in values)


def verify_binding(request: Any) -> dict[str, str]:
    """Return only BINDING_MATCHED or identical, non-disclosing DATA_ERROR.

    Reject malformed supplied evidence before calling derive_evidence.
    Derive internally exactly once on valid supplied evidence, then compare
    all four exact built-in str fields against freshly derived evidence.
    """
    if type(request) is not SourceReadEvidenceBindingRequest:
        return {"state": "DATA_ERROR"}

    # Attempt both wrapper reads even when the first is missing or raises.
    observation_request = _read_once(request, "observation_request")
    supplied_evidence = _read_once(request, "supplied_evidence")
    if observation_request is _MISSING or supplied_evidence is _MISSING:
        return {"state": "DATA_ERROR"}
    if type(supplied_evidence) is not SourceReadEvidence:
        return {"state": "DATA_ERROR"}

    supplied, supplied_ok = _read_four(supplied_evidence)
    if not supplied_ok:
        return {"state": "DATA_ERROR"}

    try:
        result = derive_evidence(observation_request)
    except Exception:
        return {"state": "DATA_ERROR"}
    if type(result) is not dict:
        return {"state": "DATA_ERROR"}

    state = result.get("state", _MISSING)
    fresh_evidence = result.get("evidence", _MISSING)
    if type(state) is not str or str.__eq__(state, "EVIDENCED") is not True:
        return {"state": "DATA_ERROR"}
    if type(fresh_evidence) is not SourceReadEvidence:
        return {"state": "DATA_ERROR"}

    fresh, fresh_ok = _read_four(fresh_evidence)
    if not fresh_ok:
        return {"state": "DATA_ERROR"}

    try:
        matched = all(
            str.__eq__(supplied_value, fresh_value) is True
            for supplied_value, fresh_value in zip(supplied, fresh)
        )
    except Exception:
        return {"state": "DATA_ERROR"}
    return {"state": "BINDING_MATCHED"} if matched else {"state": "DATA_ERROR"}
