from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

# The only decision state that is itself sufficient to proceed. Every other
# value -- including the other known fail-closed states (UNKNOWN, CONFLICT,
# VERIFY, DATA_ERROR), an unset decision, or any other non-success value --
# is treated as "not yet safe to proceed on decision grounds alone".
DECISION_PROCEED_STATE = "RESOLVED"


@dataclass(frozen=True)
class WorkGateRequest:
    """Pure, in-memory description of one step-4 Work Gate check.

    This models the "Safety independence" rule in docs/ARCHITECTURE.md as a
    deterministic decision function. It performs no I/O, retrieval, tool
    execution, or mutation of its own: the upstream decision outcome and the
    two safety triggers are all supplied by the caller.

    ``decision_state`` is expected to be the ``state`` value of an upstream
    resolution result (for example ``resolve_current`` or
    ``resolve_with_source_read_gate``), such as ``"RESOLVED"``, ``"UNKNOWN"``,
    ``"CONFLICT"``, ``"VERIFY"``, or ``"DATA_ERROR"``. It is left as a plain
    string (or ``None`` when no decision has been reached yet) rather than a
    nested dict so this gate stays the smallest possible pure/local check on
    top of whatever upstream stage already produced a decision outcome.

    ``production_trigger`` and ``permission_trigger`` are explicit booleans
    supplied by the caller for whether a production-change or
    permission-change condition applies to the current work item. This
    module does not detect, classify, or discover either condition itself.
    """

    decision_state: Optional[str] = None
    production_trigger: bool = False
    permission_trigger: bool = False


def validate_request(request: Any) -> Tuple[str, ...]:
    """Return a sorted tuple of data errors in ``request``, if any.

    The first check is on the shape of ``request`` itself: anything other
    than a ``WorkGateRequest`` instance -- ``None``, a ``dict``, a plain
    object, etc. -- fails closed right here instead of raising
    ``AttributeError`` when its fields are read below. Only once ``request``
    is confirmed to be a ``WorkGateRequest`` are its individual fields
    checked: whether ``decision_state`` is a string (or ``None``) and
    whether the two triggers are actual booleans. A malformed request never
    raises; it fails closed via ``evaluate`` returning ``REVIEW_REQUIRED``
    instead.
    """

    if not isinstance(request, WorkGateRequest):
        return ("request must be a WorkGateRequest instance",)

    errors = []

    if request.decision_state is not None and not isinstance(request.decision_state, str):
        errors.append("decision_state must be a string or None")

    if not isinstance(request.production_trigger, bool):
        errors.append("production_trigger must be a bool")

    if not isinstance(request.permission_trigger, bool):
        errors.append("permission_trigger must be a bool")

    return tuple(sorted(set(errors)))


def evaluate(request: Any) -> Dict[str, Any]:
    """Resolve the step-4 Work Gate outcome for one work item.

    ``request`` is expected to be a ``WorkGateRequest``, but is not assumed
    to be one: any other type (``None``, a ``dict``, a plain object, ...) is
    rejected by ``validate_request`` and fails closed below rather than
    raising.

    Returns a dict with a ``state`` key drawn from:

    - ``PROCEED`` -- the decision resolved successfully
      (``decision_state == "RESOLVED"``) and neither safety trigger fired.
    - ``REVIEW_REQUIRED`` -- the gate fails closed. This is returned when:

      - the request is malformed (``reason == "malformed_input"``), which
        covers both a ``request`` that is not a ``WorkGateRequest`` at all
        and a ``WorkGateRequest`` whose individual fields have the wrong
        type;
      - a production or permission trigger fired
        (``reason == "safety_trigger"``), regardless of whether the decision
        itself resolved successfully; a fired trigger always wins, so a
        successful decision can never mask a live safety condition;
      - no trigger fired but the decision did not reach ``RESOLVED``
        (``reason == "decision_not_resolved"``) -- this covers ``UNKNOWN``,
        ``CONFLICT``, ``VERIFY``, ``DATA_ERROR``, ``None``, and any other
        non-success value, all treated identically: a decision that is not
        a clean success is never enough to proceed on its own.

    This function does not execute work, invoke tools, mutate production or
    permission state, discover connectors, retrieve context, invoke an
    external model, or otherwise create authority of any kind. It only
    classifies caller-supplied inputs into ``PROCEED`` or
    ``REVIEW_REQUIRED``; the caller decides what either outcome leads to.
    """

    errors = validate_request(request)
    if errors:
        return {"state": "REVIEW_REQUIRED", "reason": "malformed_input", "errors": errors}

    fired = tuple(
        name
        for name, active in (
            ("production", request.production_trigger),
            ("permission", request.permission_trigger),
        )
        if active
    )

    if fired:
        return {
            "state": "REVIEW_REQUIRED",
            "reason": "safety_trigger",
            "triggers": fired,
            "decision_state": request.decision_state,
        }

    if request.decision_state == DECISION_PROCEED_STATE:
        return {"state": "PROCEED", "decision_state": request.decision_state}

    return {
        "state": "REVIEW_REQUIRED",
        "reason": "decision_not_resolved",
        "decision_state": request.decision_state,
    }
