from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Tuple

# The ordered names of the material-boundary signals from step 5
# ("Long-context re-sync") of docs/ARCHITECTURE.md. Order here only drives
# the order signals are reported in; any active signal is treated
# identically regardless of position.
SIGNAL_FIELDS: Tuple[str, ...] = (
    "current_or_latest",
    "continuation",
    "important_confirmation",
    "implementation",
    "publication_or_release",
    "production_change",
    "permission_change",
    "price_spec_version_change",
    "explicit_source_continuation",
)


@dataclass(frozen=True)
class ResyncGateRequest:
    """Pure, in-memory description of one step-5 Re-sync Gate check.

    This models the material-boundary list in the "Long-context re-sync"
    section of docs/ARCHITECTURE.md as a deterministic decision function. It
    performs no I/O, retrieval, writeback, or mutation of its own: every
    signal is an explicit boolean supplied by the caller for whether that
    condition applies to the current turn.

    Each field corresponds 1:1 to one bullet under step 5:

    - ``current_or_latest`` -- current / latest status
    - ``continuation`` -- continuation of previous work
    - ``important_confirmation`` -- important confirmation
    - ``implementation`` -- implementation
    - ``publication_or_release`` -- publication / release
    - ``production_change`` -- production change
    - ``permission_change`` -- permission change
    - ``price_spec_version_change`` -- price / specification / version change
    - ``explicit_source_continuation`` -- continuation of a task that
      explicitly designated a saved source

    This module does not detect, classify, or discover any of these
    conditions itself.
    """

    current_or_latest: bool = False
    continuation: bool = False
    important_confirmation: bool = False
    implementation: bool = False
    publication_or_release: bool = False
    production_change: bool = False
    permission_change: bool = False
    price_spec_version_change: bool = False
    explicit_source_continuation: bool = False


def validate_request(request: Any) -> Tuple[str, ...]:
    """Return a sorted tuple of data errors in ``request``, if any.

    The first check is on the shape of ``request`` itself: anything other
    than a ``ResyncGateRequest`` instance -- ``None``, a ``dict``, a plain
    object, etc. -- fails closed right here instead of raising
    ``AttributeError`` when its fields are read below. Only once ``request``
    is confirmed to be a ``ResyncGateRequest`` is each signal field checked
    for being an actual boolean. A malformed request never raises; it fails
    closed via ``evaluate`` returning ``RESYNC_REQUIRED`` instead.
    """

    if not isinstance(request, ResyncGateRequest):
        return ("request must be a ResyncGateRequest instance",)

    errors = [
        f"{name} must be a bool"
        for name in SIGNAL_FIELDS
        if not isinstance(getattr(request, name), bool)
    ]

    return tuple(sorted(set(errors)))


def evaluate(request: Any) -> dict:
    """Resolve the step-5 Re-sync Gate outcome for one turn.

    ``request`` is expected to be a ``ResyncGateRequest``, but is not
    assumed to be one: any other type (``None``, a ``dict``, a plain
    object, ...) is rejected by ``validate_request`` and fails closed below
    rather than raising.

    Returns a dict with a ``state`` key drawn from:

    - ``RESYNC_REQUIRED`` -- at least one material-boundary signal is
      active, or the request is malformed (``reason == "malformed_input"``
      in the malformed case, with an ``errors`` tuple). A well-formed
      request with one or more active signals reports
      ``reason == "material_boundary"`` and a ``signals`` tuple naming every
      active signal, in ``SIGNAL_FIELDS`` order.
    - ``NOT_REQUIRED`` -- the request is well-formed and no signal is
      active.

    This function does not perform retrieval, writeback, external I/O, tool
    calls, or any other authority-bearing action. It only classifies
    caller-supplied booleans into ``RESYNC_REQUIRED`` or ``NOT_REQUIRED``;
    the caller decides what either outcome leads to.
    """

    errors = validate_request(request)
    if errors:
        return {"state": "RESYNC_REQUIRED", "reason": "malformed_input", "errors": errors}

    active = tuple(name for name in SIGNAL_FIELDS if getattr(request, name))

    if active:
        return {"state": "RESYNC_REQUIRED", "reason": "material_boundary", "signals": active}

    return {"state": "NOT_REQUIRED"}
