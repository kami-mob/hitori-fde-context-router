from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

ALL = "ALL"
ANY = "ANY"
VALID_MODES = {ALL, ANY}


@dataclass(frozen=True)
class GateRequest:
    """Pure, in-memory description of one turn's source-grounding situation.

    This models the *contract* described in docs/SOURCE_READ_GATE.md as a
    deterministic decision function. It performs no I/O: whether a source
    was actually read is supplied by the caller via ``read_log`` rather than
    discovered by this module, so it can be exercised without any connector.
    """

    declared_sources: Tuple[str, ...] = ()
    mode: str = ALL
    read_log: Tuple[str, ...] = ()
    unavailable_sources: Tuple[str, ...] = ()
    no_external_read: bool = False
    continued_from_previous: bool = False
    source_changed_this_turn: bool = False
    previous_declared_sources: Tuple[str, ...] = ()
    previous_mode: str = ALL


def _effective_sources(request: GateRequest) -> Tuple[Tuple[str, ...], str, Optional[str]]:
    """Resolve which source requirement is actually in force this turn.

    Returns ``(sources, mode, origin)`` where ``origin`` names the field set
    that is live -- ``"current"`` for this turn's own declaration,
    ``"previous"`` for an inherited continuation, or ``None`` when no
    requirement is in force. Only the live field set should be validated:
    stale data left over in the other set (e.g. a garbled ``previous_mode``
    after a new source was declared, or after continuation was dropped) must
    not affect the outcome.
    """

    if request.declared_sources:
        return request.declared_sources, request.mode, "current"

    if (
        request.continued_from_previous
        and not request.source_changed_this_turn
        and request.previous_declared_sources
    ):
        return request.previous_declared_sources, request.previous_mode, "previous"

    return (), request.mode, None


def validate_request(request: GateRequest) -> List[str]:
    """Validate only the source requirement that is actually effective.

    Malformed data in a field set that isn't live this turn (for example a
    bad ``previous_mode`` after the source was changed, or a duplicate in
    ``previous_declared_sources`` while a fresh ``declared_sources`` is in
    force) must not surface as an error: it cannot affect the outcome, so it
    isn't a data error for this evaluation.
    """

    sources, mode, origin = _effective_sources(request)
    errors: List[str] = []

    if origin == "current":
        if mode not in VALID_MODES:
            errors.append(f"unknown mode: {mode}")
        if len(set(sources)) != len(sources):
            errors.append("duplicate entries in declared_sources")
    elif origin == "previous":
        if mode not in VALID_MODES:
            errors.append(f"unknown previous_mode: {mode}")
        if len(set(sources)) != len(sources):
            errors.append("duplicate entries in previous_declared_sources")

    return sorted(set(errors))


def evaluate(request: GateRequest) -> Dict[str, Any]:
    """Resolve one turn's Source Read Gate outcome.

    Returns a dict with a ``state`` key drawn from:

    - ``NOT_APPLICABLE`` -- no explicit source is in force for this turn.
    - ``PASS``           -- the requirement is satisfied by ``read_log``.
    - ``VERIFY``         -- required evidence has not been read yet, or a
      no-external-read constraint blocks the one remaining read that would
      be needed to satisfy the requirement. Evidence already present in
      ``read_log`` still counts even under ``no_external_read``: the
      constraint blocks a new prohibited retrieval, it does not retract
      evidence that was already obtained.
    - ``UNKNOWN``        -- the requirement can never be satisfied given
      ``unavailable_sources``: in ``ALL`` mode this means at least one
      required source is unavailable (one missing link breaks the whole
      requirement); in ``ANY`` mode it means every candidate source is
      unavailable (no candidate remains that could ever satisfy it).
    - ``DATA_ERROR``     -- the *effective* request is malformed. Only the
      live source requirement (see ``_effective_sources``) is checked;
      inactive history in the other field set is ignored.

    Item 4 of the contract ("preserve bounded retrieval") is surfaced via
    ``extra_reads``: sources present in ``read_log`` that were not part of
    the effective requirement. Their presence never blocks resolution, but
    callers can use it to flag unnecessary broad reads.
    """

    errors = validate_request(request)
    if errors:
        return {"state": "DATA_ERROR", "errors": errors}

    sources, mode, _origin = _effective_sources(request)

    if not sources:
        return {"state": "NOT_APPLICABLE", "reason": "no_explicit_source_designated"}

    extra_reads = tuple(s for s in request.read_log if s not in sources)
    read = set(request.read_log)
    unavailable = set(request.unavailable_sources)

    if mode == ALL:
        missing = tuple(s for s in sources if s not in read)
        if not missing:
            return {"state": "PASS", "sources": sources, "extra_reads": extra_reads}

        blocked = tuple(s for s in missing if s in unavailable)
        if blocked:
            return {
                "state": "UNKNOWN",
                "reason": "required_source_unavailable",
                "sources": sources,
                "unavailable": blocked,
                "extra_reads": extra_reads,
            }

        if request.no_external_read:
            return {
                "state": "VERIFY",
                "reason": "no_external_read_constraint",
                "sources": sources,
                "missing": missing,
                "extra_reads": extra_reads,
            }

        return {
            "state": "VERIFY",
            "reason": "not_yet_read",
            "sources": sources,
            "missing": missing,
            "extra_reads": extra_reads,
        }

    # mode == ANY
    satisfied = tuple(s for s in sources if s in read)
    if satisfied:
        return {"state": "PASS", "sources": sources, "satisfied": satisfied, "extra_reads": extra_reads}

    if set(sources) <= unavailable:
        return {
            "state": "UNKNOWN",
            "reason": "all_candidate_sources_unavailable",
            "sources": sources,
            "extra_reads": extra_reads,
        }

    if request.no_external_read:
        return {
            "state": "VERIFY",
            "reason": "no_external_read_constraint",
            "sources": sources,
            "extra_reads": extra_reads,
        }

    return {
        "state": "VERIFY",
        "reason": "no_candidate_source_read_yet",
        "sources": sources,
        "extra_reads": extra_reads,
    }
