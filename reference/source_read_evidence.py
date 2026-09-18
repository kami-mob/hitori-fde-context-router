"""Source Read Evidence: the smallest pure/local surface for carrying a
validated Source Read Observation forward as structured, immutable evidence.

[`source_read_observation.py`](source_read_observation.py) binds a
caller-supplied source read into deterministic hashes. This module adds
nothing to that binding -- it only re-shapes a *fresh* ``OBSERVED`` result
into an immutable record that omits the raw payload and the raw version
string, so the record can be carried or compared without re-exposing either.

This module performs no I/O, no persistence, no caching, and no connector
discovery. It does not accept caller-supplied hashes: the only hashes it
ever returns are the ones ``observe()`` computes itself, freshly, from the
``ObservationRequest`` it is handed. It does not modify, evaluate, or
satisfy the Source Read Gate -- see docs/SOURCE_READ_EVIDENCE.md for the
full boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from source_read_observation import ObservationRequest, observe

__all__ = ["SourceReadEvidence", "derive_evidence"]


@dataclass(frozen=True)
class SourceReadEvidence:
    """Immutable, hash-only record of one validated Source Read Observation.

    Carries ``source_id`` in the clear (it is an identifier, not secret
    material) plus the three digests ``observe()`` computed. It never
    carries ``raw_payload`` or ``source_version``: those are exactly the
    two fields this record exists to avoid re-exposing.
    """

    source_id: str
    source_identity_hash: str
    source_version_binding_hash: str
    raw_payload_hash: str


def derive_evidence(request: Any) -> Dict[str, Any]:
    """Derive immutable evidence from a fresh Source Read Observation.

    ``observe(request)`` is invoked freshly on every call -- nothing is
    cached or memoized across calls, so evidence always reflects the
    request as handed to this call, not a prior one.

    Returns a dict with a ``state`` key:

    - ``DATA_ERROR`` -- ``observe(request)`` did not reach ``OBSERVED``.
      This covers every case ``observe()`` itself fails closed on: ``request``
      not being exactly an ``ObservationRequest`` (including ``None``, a
      ``dict``, an unrelated object, or an ``ObservationRequest`` subclass),
      a field failing exact-type validation, or ``source_id``/
      ``source_version`` being well-typed but not UTF-8 encodable. ``errors``
      carries the same messages ``observe()`` produced. No
      ``SourceReadEvidence`` is constructed, and ``request.source_id`` is
      never accessed in this branch, so a request-shaped object whose field
      access raises still fails closed rather than propagating an exception.
    - ``EVIDENCED`` -- the observation reached ``OBSERVED``. ``evidence`` is
      a ``SourceReadEvidence`` built only from ``request.source_id`` and the
      three hashes ``observe()`` just computed. No caller-supplied hash is
      ever accepted in place of one it computes.

    An ``EVIDENCED`` result carries forward exactly what ``observe()``
    already established -- see docs/SOURCE_READ_OBSERVATION.md for what an
    ``OBSERVED`` result does and does not mean. It is not, by itself, a
    ``PASS`` for the Source Read Gate: this module does not call, evaluate,
    or otherwise touch ``source_read_gate.py``.
    """

    observation = observe(request)
    if observation.get("state") != "OBSERVED":
        return {
            "state": "DATA_ERROR",
            "errors": observation.get(
                "errors", ["observation did not reach OBSERVED"]
            ),
        }

    return {
        "state": "EVIDENCED",
        "evidence": SourceReadEvidence(
            source_id=request.source_id,
            source_identity_hash=observation["source_identity_hash"],
            source_version_binding_hash=observation["source_version_binding_hash"],
            raw_payload_hash=observation["raw_payload_hash"],
        ),
    }
