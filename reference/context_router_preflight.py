from __future__ import annotations
from typing import Any, Dict, Iterable

from source_read_gate import GateRequest, evaluate
from minimal_resolver import resolve_current

# Gate states that permit the current-decision resolver to run: either the
# gate's requirement was actually satisfied (PASS), or no explicit source was
# in force for this turn at all (NOT_APPLICABLE).
GATE_PROCEED_STATES = {"PASS", "NOT_APPLICABLE"}

# Gate states that must fail closed: the caller does not get a resolver
# opinion in place of unresolved, impossible, or malformed source evidence.
GATE_FAIL_CLOSED_STATES = {"VERIFY", "UNKNOWN", "DATA_ERROR"}


def resolve_with_source_read_gate(
    gate_request: GateRequest,
    records: Iterable[Dict[str, Any]],
    *,
    domain: str,
    subject: str,
    field: str,
    as_of: str,
    verify_after_days: int = 30,
) -> Dict[str, Any]:
    """Run the Explicit Source Read Gate before the current-decision resolver.

    This is a pure/local composition of two existing reference models
    (``source_read_gate.evaluate`` and ``minimal_resolver.resolve_current``):
    no new I/O, retrieval, or model invocation is introduced here.

    The gate is evaluated first. ``resolve_current`` is only invoked when the
    gate outcome is ``PASS`` (the declared source requirement was satisfied)
    or ``NOT_APPLICABLE`` (no explicit source was in force this turn), which
    matches the conditional gate placement in ``docs/ARCHITECTURE.md``.

    When the gate resolves to ``VERIFY``, ``UNKNOWN``, or ``DATA_ERROR``, the
    resolver is never called and that gate outcome is returned as-is: a
    blocked or unresolved source-read requirement is not silently replaced by
    a resolver opinion formed without the evidence the user required.

    Returns a dict with a ``stage`` key:

    - ``"source_read_gate"`` -- the gate did not reach a proceed state. The
      gate's own outcome dict (``state`` plus its detail fields such as
      ``reason``, ``missing``, ``unavailable``, or ``errors``) is merged in
      directly.
    - ``"resolution"`` -- the gate proceeded, so ``resolve_current`` ran. The
      resolver's outcome dict (``state`` plus its own detail fields such as
      ``record``, ``decision_ids``, or ``errors``) is merged in directly, and
      the gate's own outcome is attached under ``gate`` for traceability. A
      resolver state of ``VERIFY``, ``UNKNOWN``, ``CONFLICT``, or
      ``DATA_ERROR`` at this stage is the resolver's own fail-closed result,
      not one manufactured by this composition.
    """

    gate_result = evaluate(gate_request)

    if gate_result["state"] not in GATE_PROCEED_STATES:
        return {"stage": "source_read_gate", **gate_result}

    resolution = resolve_current(
        records,
        domain=domain,
        subject=subject,
        field=field,
        as_of=as_of,
        verify_after_days=verify_after_days,
    )
    return {"stage": "resolution", "gate": gate_result, **resolution}
