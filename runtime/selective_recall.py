from __future__ import annotations
from typing import Any, Callable, Dict, List, Tuple


class LoadError(Exception):
    """Wraps whatever a caller-supplied loader raised for one candidate id.

    Not raised by this module during normal operation: a loader failure is
    caught per id and recorded in the returned ``failed`` mapping instead of
    propagating, so this type exists mainly so callers have a stable name to
    reference if they want to re-raise or inspect a recorded failure.
    """


def _validate_plan(plan_result: Any) -> List[str]:
    """Validate that ``plan_result`` is a well-formed, SELECTED context-selection plan.

    Only shape is checked here: whether ``plan_result`` came from
    ``reference/context_selection.py``'s ``select_context`` with a
    ``"SELECTED"`` state, and whether ``plan`` is a flat sequence of unique,
    non-empty string ids. Any other stage, any non-``SELECTED`` state (for
    example the upstream planner's own ``"DATA_ERROR"``), or a malformed
    ``plan`` is rejected here rather than partially acted on.
    """

    errors: List[str] = []

    if not isinstance(plan_result, dict):
        return ["plan_result is not a dict"]

    if plan_result.get("stage") != "context_selection":
        errors.append(f"unexpected stage: {plan_result.get('stage')!r}")
        return errors

    if plan_result.get("state") != "SELECTED":
        errors.append(f"plan state is not SELECTED: {plan_result.get('state')!r}")
        return errors

    plan = plan_result.get("plan")
    if not isinstance(plan, (tuple, list)):
        errors.append("plan is missing or is not a tuple/list of candidate ids")
        return errors

    if not all(isinstance(candidate_id, str) and candidate_id for candidate_id in plan):
        errors.append("plan contains a non-string or empty candidate id")

    if len(set(plan)) != len(plan):
        errors.append("plan contains a duplicate candidate id")

    return errors


def load_selected_context(
    plan_result: Dict[str, Any],
    loader: Callable[[str], Any],
) -> Dict[str, Any]:
    """Load exactly the candidates a Context Selection plan already selected.

    This is the runtime boundary for ARCHITECTURE.md step 3 (Selective
    Recall): it consumes the ``plan_result`` produced by
    ``reference/context_selection.py``'s ``select_context`` and a
    caller-supplied ``loader`` (a callable that turns one candidate id into
    its loaded value, however the caller wants to source that -- file read,
    lookup in an in-memory map, etc.), and does nothing beyond invoking
    ``loader`` once per id already present in ``plan_result["plan"]``, in
    that same order.

    It does not decide *what* to load -- that decision was already made by
    ``select_context``. This function performs no relevance scoring, no
    autonomous search or connector discovery, no expansion beyond the
    supplied plan (in particular no additional COLD candidates get loaded
    just because they exist), and no external model invocation or
    production mutation of its own; ``loader`` is the only place any I/O
    happens, and it is entirely caller-supplied.

    Returns a dict with a ``stage`` key of ``"selective_recall"`` and a
    ``state`` key:

    - ``"DATA_ERROR"`` -- ``plan_result`` is not a well-formed, ``SELECTED``
      context-selection plan (wrong stage, non-``SELECTED`` state, or a
      malformed ``plan``). ``errors`` lists what was wrong and ``loader`` is
      never invoked.
    - ``"LOADED"``  -- every id in the plan loaded successfully; ``loaded``
      maps each id to ``loader``'s return value, in plan order, and
      ``failed`` is empty.
    - ``"PARTIAL"`` -- ``loader`` raised for one or more ids. Each such id is
      fail-closed: it is omitted from ``loaded`` entirely (no fallback or
      partial value is substituted) and recorded in ``failed`` mapping that
      id to ``str(exception)``. Ids that already loaded successfully, and
      ids later in the plan, are unaffected -- one id's failure does not
      abort the rest of the plan.
    """

    errors = _validate_plan(plan_result)
    if errors:
        return {"stage": "selective_recall", "state": "DATA_ERROR", "errors": errors}

    plan: Tuple[str, ...] = tuple(plan_result["plan"])
    loaded: Dict[str, Any] = {}
    failed: Dict[str, str] = {}

    for candidate_id in plan:
        try:
            loaded[candidate_id] = loader(candidate_id)
        except Exception as exc:
            failed[candidate_id] = str(exc)

    return {
        "stage": "selective_recall",
        "state": "PARTIAL" if failed else "LOADED",
        "plan": plan,
        "loaded": loaded,
        "failed": failed,
    }
