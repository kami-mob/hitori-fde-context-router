from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Tuple

# Who is asserting the content being considered for writeback.
ORIGINS: Tuple[str, ...] = ("USER_CONFIRMED", "AI_PROPOSAL")

# The authoritative-capable statuses a writeback candidate may be requested
# at. Mirrors the status vocabulary already used by
# reference/minimal_resolver.py (docs/DECISION_RESOLUTION_SPEC.md).
REQUESTED_STATUSES: Tuple[str, ...] = ("PROPOSED", "ACTIVE", "LOCKED")

# The only requested_status an AI_PROPOSAL origin may ever produce a
# candidate at. ACTIVE and LOCKED are authoritative-capable statuses
# (reference/minimal_resolver.py); letting an AI proposal request either
# would be exactly the silent promotion step 6 of ARCHITECTURE.md forbids.
AI_PROPOSAL_ALLOWED_STATUS = "PROPOSED"


@dataclass(frozen=True)
class WritebackGateRequest:
    """Pure, in-memory description of one step-6 Writeback Gate check.

    This models the "Writeback" rule in docs/ARCHITECTURE.md as a
    deterministic decision function. It performs no persistence, retrieval,
    or other I/O of its own: ``origin``, ``requested_status``, and
    ``important`` are all supplied by the caller.

    ``origin`` is expected to be one of ``ORIGINS``: ``"USER_CONFIRMED"``
    for content the user has confirmed, or ``"AI_PROPOSAL"`` for a
    writeback the AI itself is proposing.

    ``requested_status`` is expected to be one of ``REQUESTED_STATUSES``:
    the status the caller wants the writeback candidate recorded at.

    ``important`` is an explicit boolean supplied by the caller for whether
    the content is one of the "important confirmed decisions" step 6 names
    (selected implementation direction, current version, approved price,
    next action, superseded decision relationship, implementation status).
    This module does not detect, classify, or discover importance itself.
    """

    origin: str = "AI_PROPOSAL"
    requested_status: str = "PROPOSED"
    important: bool = False


def validate_request(request: Any) -> Tuple[str, ...]:
    """Return a sorted tuple of data errors in ``request``, if any.

    The first check is on the shape of ``request`` itself: anything other
    than a ``WritebackGateRequest`` instance -- ``None``, a ``dict``, a
    plain object, etc. -- fails closed right here instead of raising
    ``AttributeError`` when its fields are read below. Only once ``request``
    is confirmed to be a ``WritebackGateRequest`` are its individual fields
    checked: whether ``origin`` is one of ``ORIGINS``, whether
    ``requested_status`` is one of ``REQUESTED_STATUSES``, and whether
    ``important`` is an actual boolean. A malformed request never raises;
    it fails closed via ``evaluate`` returning ``REVIEW_REQUIRED`` instead.
    """

    if not isinstance(request, WritebackGateRequest):
        return ("request must be a WritebackGateRequest instance",)

    errors = []

    if request.origin not in ORIGINS:
        errors.append(f"origin must be one of {ORIGINS}")

    if request.requested_status not in REQUESTED_STATUSES:
        errors.append(f"requested_status must be one of {REQUESTED_STATUSES}")

    if not isinstance(request.important, bool):
        errors.append("important must be a bool")

    return tuple(sorted(set(errors)))


def evaluate(request: Any) -> Dict[str, Any]:
    """Resolve the step-6 Writeback Gate outcome for one candidate.

    ``request`` is expected to be a ``WritebackGateRequest``, but is not
    assumed to be one: any other type (``None``, a ``dict``, a plain
    object, ...) is rejected by ``validate_request`` and fails closed below
    rather than raising.

    Returns a dict with a ``state`` key drawn from:

    - ``REVIEW_REQUIRED`` -- the gate fails closed. This is returned when:

      - the request is malformed (``reason == "malformed_input"``, with an
        ``errors`` tuple), which covers both a ``request`` that is not a
        ``WritebackGateRequest`` at all and one with a badly typed or
        out-of-range field;
      - ``origin == "AI_PROPOSAL"`` and ``requested_status`` is anything
        other than ``"PROPOSED"`` (``reason ==
        "ai_proposal_authoritative_status"``) -- an AI proposal is never
        allowed to request an authoritative-capable status, regardless of
        ``important``, since that would silently promote proposal status
        to authoritative status.

    - ``WRITEBACK_CANDIDATE`` -- the request is well-formed, is not an
      AI proposal requesting an authoritative-capable status, and
      ``important`` is ``True``.
    - ``NOT_REQUIRED`` -- the request is well-formed and ``important`` is
      ``False``.

    This function does not persist, retrieve, or otherwise write back
    anything itself, and it does not decide what the caller does with a
    ``WRITEBACK_CANDIDATE`` outcome. It only classifies caller-supplied
    inputs into ``REVIEW_REQUIRED``, ``WRITEBACK_CANDIDATE``, or
    ``NOT_REQUIRED``; the caller decides what any outcome leads to.
    """

    errors = validate_request(request)
    if errors:
        return {"state": "REVIEW_REQUIRED", "reason": "malformed_input", "errors": errors}

    if request.origin == "AI_PROPOSAL" and request.requested_status != AI_PROPOSAL_ALLOWED_STATUS:
        return {
            "state": "REVIEW_REQUIRED",
            "reason": "ai_proposal_authoritative_status",
            "origin": request.origin,
            "requested_status": request.requested_status,
        }

    if request.important:
        return {
            "state": "WRITEBACK_CANDIDATE",
            "origin": request.origin,
            "requested_status": request.requested_status,
        }

    return {"state": "NOT_REQUIRED"}
