"""Bounded source-read handoff through one explicitly supplied acquisition adapter.

A caller selects and authorizes the adapter OUTSIDE this module. A PASS here
is a local gate outcome for adapter-reported values, never independent proof
of authentication, genuine external I/O, provenance, freshness or permission.
No connector credentials, URLs, payloads or exceptions appear in results.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from source_read_observation import ObservationRequest
from source_read_evidence import SourceReadEvidence, derive_evidence
from source_read_evidence_binding import (
    SourceReadEvidenceBindingRequest, verify_binding,
)
from source_read_gate import GateRequest, evaluate

__all__ = ["AcquisitionRequest", "FetchedSource", "acquire_declared_sources"]


@dataclass(frozen=True)
class AcquisitionRequest:
    declared_sources: Any = ()
    mode: Any = "ALL"
    no_external_read: Any = False


@dataclass(frozen=True)
class FetchedSource:
    source_id: Any
    source_version: Any
    raw_payload: Any


def _text(value: Any) -> bool:
    if type(value) is not str or not value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def acquire_declared_sources(request: Any, fetcher: Any) -> dict[str, Any]:
    """Read only selected sources, locally bind each read, then evaluate gate.

    fetcher(source_id) is an already-authenticated/authorized, externally
    supplied adapter boundary. This function CANNOT validate that assertion.
    It neither discovers a connector nor opens a network connection itself.
    A failed callback is not automatically retried or declared unavailable.
    """
    error = {"state": "DATA_ERROR", "stage": "acquisition"}
    verify = {"state": "VERIFY", "stage": "acquisition"}
    if type(request) is not AcquisitionRequest:
        return error
    try:
        sources = request.declared_sources
        mode = request.mode
        no_external_read = request.no_external_read
    except Exception:
        return error
    if (
        type(sources) is not tuple
        or not sources
        or any(not _text(source) for source in sources)
        or len(set(sources)) != len(sources)
        or type(mode) is not str
        or mode not in ("ALL", "ANY")
        or type(no_external_read) is not bool
        or not callable(fetcher)
    ):
        return error
    if no_external_read:
        return verify

    completed: list[str] = []
    for source in sources:
        try:
            receipt = fetcher(source)
        except Exception:
            return verify
        if type(receipt) is not FetchedSource:
            return error
        try:
            returned_id = receipt.source_id
            revision = receipt.source_version
            raw = receipt.raw_payload
        except Exception:
            return error
        if (
            not _text(returned_id)
            or not str.__eq__(returned_id, source) is True
            or not _text(revision)
            or type(raw) is not bytes
        ):
            return error
        observation = ObservationRequest(
            source_id=returned_id, source_version=revision, raw_payload=raw,
        )
        try:
            derived = derive_evidence(observation)
            if type(derived) is not dict or derived.get("state") != "EVIDENCED":
                return error
            supplied = derived.get("evidence")
            if type(supplied) is not SourceReadEvidence:
                return error
            bound = verify_binding(
                SourceReadEvidenceBindingRequest(
                    observation_request=observation, supplied_evidence=supplied,
                )
            )
            if type(bound) is not dict or bound != {"state": "BINDING_MATCHED"}:
                return error
        except Exception:
            return error
        completed.append(source)
        if mode == "ANY":
            break

    gate = evaluate(GateRequest(
        declared_sources=sources, mode=mode, read_log=tuple(completed),
    ))
    if type(gate) is not dict or gate.get("state") != "PASS":
        return error
    # Raw bytes, versions, hashes, source IDs and adapter exception text never
    # leave this reference handoff. A caller must independently establish
    # provenance, access rights and live source availability.
    return {
        "state": "PASS", "stage": "local_source_read_gate",
        "evidence_scope": "CALLER_SUPPLIED_ADAPTER", "read_count": len(completed),
    }
