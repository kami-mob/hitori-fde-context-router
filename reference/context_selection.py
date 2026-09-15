from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

HOT = "HOT"
WARM = "WARM"
COLD = "COLD"
VALID_TIERS = {HOT, WARM, COLD}

# Priority order the flat "plan" list is assembled in. This mirrors the
# ordering ARCHITECTURE.md's step 2 (Context Router) lists the tiers in:
# HOT / WARM / COLD.
TIER_ORDER = (HOT, WARM, COLD)


@dataclass(frozen=True)
class ContextCandidate:
    """One caller-described unit of context available to be selected.

    This module performs no retrieval and does not itself judge content
    relevance: the caller supplies each candidate already scored against
    the resolved scope (``relevant``) and already tagged with the tier
    ARCHITECTURE.md's Context Router step would assign it by default
    (``tier``). This module only decides, deterministically, which of the
    supplied candidates belong in the selection plan.

    ``condition`` names the trigger (e.g. ``"production_change"``,
    ``"permission_change"``) that must be active for a ``WARM`` candidate
    to be read; a ``WARM`` candidate with no ``condition`` is never
    selected by default, matching "read only when a condition requires
    it". It is ignored for ``HOT`` and ``COLD`` candidates.

    ``explicit_source`` marks a candidate the user explicitly designated
    (the Explicit Source Read Gate's requirement, step 0). Such a
    candidate is always selected regardless of tier, relevance, or
    condition: ARCHITECTURE.md is explicit that "an explicit source read
    that is directly required by the user's request is not treated as a
    broad COLD sweep merely because that source would not otherwise be
    loaded by default", and this carve-out applies uniformly across all
    tiers here rather than being special-cased to COLD alone.

    ``explicitly_required`` is a separate, independent signal: the
    current task explicitly needs this ``COLD`` context even though the
    user never designated it as a source. Unlike ``explicit_source`` it
    carries no Source Read Gate designation -- it is a task-necessity
    judgment supplied by the caller, not an evidentiary requirement -- so
    it only lifts the ``COLD`` "do not sweep broadly" default and has no
    effect on ``HOT`` or ``WARM`` candidates, which already have their
    own explicit selection mechanisms (``relevant`` and ``condition``).
    A candidate may set either flag, both, or neither; they are checked
    independently and neither implies the other.
    """

    id: str
    tier: str
    relevant: bool = False
    condition: Optional[str] = None
    explicit_source: bool = False
    explicitly_required: bool = False


def validate_candidates(candidates: Iterable[ContextCandidate]) -> List[str]:
    """Validate candidate shape only; never inspects retrieval content."""

    candidates = list(candidates)
    errors: List[str] = []
    seen_ids = set()

    for candidate in candidates:
        if candidate.id in seen_ids:
            errors.append(f"duplicate candidate id: {candidate.id}")
        seen_ids.add(candidate.id)

        if candidate.tier not in VALID_TIERS:
            errors.append(f"unknown tier for {candidate.id}: {candidate.tier}")

    return sorted(set(errors))


def _include(candidate: ContextCandidate, active_conditions: FrozenSet[str]) -> bool:
    if candidate.explicit_source:
        return True

    if candidate.tier == HOT:
        return candidate.relevant

    if candidate.tier == WARM:
        return candidate.condition is not None and candidate.condition in active_conditions

    # COLD: excluded by default. Two independent carve-outs can select
    # it: the explicit_source override already checked above (a
    # user-designated source), or explicitly_required (the task itself
    # explicitly needs this COLD context, with no designated source).
    return candidate.explicitly_required


def select_context(
    resolution: Any,
    candidates: Iterable[ContextCandidate],
    *,
    active_conditions: Iterable[str] = (),
) -> Dict[str, Any]:
    """Plan which supplied context candidates to read next (ARCHITECTURE.md step 2).

    ``resolution`` is the caller-supplied output of the Resolution Kernel
    (or its composition with the Source Read Gate, e.g.
    ``context_router_preflight.resolve_with_source_read_gate``). This
    function does not inspect or branch on it: it is only carried through
    on the returned plan under ``"resolution"`` for traceability. That is
    intentional, not an oversight -- ARCHITECTURE.md's step 3 (Safety
    independence) requires that a production or permission trigger "must
    still fire when the decision state is UNKNOWN, CONFLICT, or VERIFY",
    so WARM selection is driven only by ``active_conditions``, never by
    whether resolution succeeded.

    Selection rules, applied per candidate:

    - ``HOT``  -- selected iff ``relevant`` is true (read by default when
      directly relevant).
    - ``WARM`` -- selected iff ``condition`` is set and present in
      ``active_conditions`` (read only when a condition requires it).
    - ``COLD`` -- never selected by default (do not sweep broadly), unless
      ``explicitly_required`` is set on that candidate: an independent,
      caller-supplied signal that the current task explicitly needs this
      COLD context even without a designated source.
    - Any candidate with ``explicit_source`` set is always selected,
      overriding the tier rule above (and independent of
      ``explicitly_required``).

    Returns a dict with a ``stage`` key of ``"context_selection"`` and a
    ``state`` key:

    - ``"DATA_ERROR"`` -- malformed candidates (duplicate id or unknown
      tier); ``errors`` lists what was wrong and no selection is made.
    - ``"SELECTED"`` -- ``selected`` maps each tier to a tuple of the
      selected candidate ids (input order preserved), and ``plan`` is the
      flat, deterministic HOT-then-WARM-then-COLD concatenation of those
      same ids for callers that just want a single read order.

    This function performs no I/O, retrieval, or model invocation: it is a
    pure, in-memory filter over caller-supplied metadata.
    """

    candidates = list(candidates)
    errors = validate_candidates(candidates)
    if errors:
        return {"stage": "context_selection", "state": "DATA_ERROR", "errors": errors}

    active = frozenset(active_conditions)
    selected: Dict[str, Tuple[str, ...]] = {tier: () for tier in TIER_ORDER}
    for tier in TIER_ORDER:
        selected[tier] = tuple(
            candidate.id
            for candidate in candidates
            if candidate.tier == tier and _include(candidate, active)
        )

    plan = tuple(candidate_id for tier in TIER_ORDER for candidate_id in selected[tier])

    return {
        "stage": "context_selection",
        "state": "SELECTED",
        "resolution": resolution,
        "selected": selected,
        "plan": plan,
    }
