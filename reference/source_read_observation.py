"""Source Read Observation: deterministic, pure/local binding of
caller-supplied source identity, version metadata, and raw payload bytes.

This module exists so that "what was read" can later be compared for
equality -- across turns, across processes, or across a staging/canonical
boundary -- without re-transmitting the payload and without this module
ever touching a network, a filesystem, a clock, or a permission system
itself. Every value it hashes is supplied by the caller in memory; nothing
here is discovered, fetched, or persisted.

It performs no I/O, no authentication, no permission checks, no
current-time acquisition, no persistence, no semantic truth creation, and
no connector discovery. A successful ``OBSERVED`` result means only that
the three caller-supplied values hash the way this module deterministically
says they hash -- it does not mean, and must not be read to imply, that the
source is trusted, authentic, fresh, that the caller was authorized to read
it, that the payload is complete, or that any of this was externally
proven. See docs/SOURCE_READ_OBSERVATION.md for the full boundary.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ObservationRequest:
    """Pure, in-memory description of one caller-supplied source read.

    source_id      -- caller-supplied identifier for the source (e.g. a repo
                       path, document id, or URL). Must be a non-empty,
                       UTF-8-encodable str.
    source_version -- caller-supplied version/revision marker for the source
                       (e.g. a commit sha, ETag, or revision id). Must be a
                       non-empty, UTF-8-encodable str.
    raw_payload    -- the exact bytes the caller read from the source. Must
                       be bytes; may be empty (e.g. an empty file).
    """

    source_id: Any = None
    source_version: Any = None
    raw_payload: Any = None


def _encode_utf8_or_none(value: str) -> Optional[bytes]:
    """Encode ``value`` as UTF-8, returning ``None`` instead of raising.

    A ``str`` is a sequence of Unicode code points, which may include lone
    surrogates (U+D800-U+DFFF) that do not correspond to any Unicode scalar
    value -- for example a string reconstructed from ``surrogateescape``
    decoding, or one built directly from ``chr(0xD800)``. Such a string is a
    perfectly well-typed ``str`` (``type(value) is str`` holds), but it has
    no UTF-8 representation. This helper isolates the one place that boundary
    is crossed, so callers can fail closed on it instead of letting
    ``UnicodeEncodeError`` escape from inside a hashing routine.
    """

    try:
        return value.encode("utf-8")
    except UnicodeEncodeError:
        return None


def validate_request(request: Any) -> List[str]:
    """Exact-type, fail-closed validation of an ObservationRequest.

    The top-level ``request`` object itself is checked with
    ``type(request) is ObservationRequest`` *before* any field is
    accessed. A caller that hands this function ``None``, a ``dict``, an
    unrelated object, or even an ``ObservationRequest`` subclass gets a
    single ``DATA_ERROR``-worthy message back -- never an ``AttributeError``
    from reaching for ``.source_id`` on something that doesn't have it.

    Once the top-level type is confirmed exact, field checks use
    ``type(x) is ...`` rather than ``isinstance`` for the same reason: a
    subclass (an ``int`` subclass standing in for a version, a
    ``bytearray``/``memoryview`` standing in for ``bytes``, a ``bool`` --
    itself an ``int`` subclass -- standing in for either) is rejected
    rather than silently accepted.

    ``source_id`` and ``source_version`` additionally must be UTF-8
    encodable: a ``str`` containing a lone surrogate code point is exactly
    typed and non-empty but cannot be turned into bytes, so it fails closed
    to ``DATA_ERROR`` here rather than raising ``UnicodeEncodeError`` later
    inside ``observe()``.
    """

    if type(request) is not ObservationRequest:
        return [f"request must be ObservationRequest, got {type(request).__name__}"]

    errors: List[str] = []

    if type(request.source_id) is not str:
        errors.append(f"source_id must be str, got {type(request.source_id).__name__}")
    elif not request.source_id:
        errors.append("source_id must not be empty")
    elif _encode_utf8_or_none(request.source_id) is None:
        errors.append("source_id must be UTF-8 encodable")

    if type(request.source_version) is not str:
        errors.append(
            f"source_version must be str, got {type(request.source_version).__name__}"
        )
    elif not request.source_version:
        errors.append("source_version must not be empty")
    elif _encode_utf8_or_none(request.source_version) is None:
        errors.append("source_version must be UTF-8 encodable")

    if type(request.raw_payload) is not bytes:
        errors.append(
            f"raw_payload must be bytes, got {type(request.raw_payload).__name__}"
        )

    return errors


def _length_prefixed(*parts: bytes) -> bytes:
    """Concatenate ``parts`` with explicit length prefixes.

    Plain concatenation is ambiguous: ``("ab", "c")`` and ``("a", "bc")``
    would hash identically. Prefixing each part with its own byte length
    makes the encoding injective, so the version-binding hash below cannot
    collide across different (source_id, source_version) splits.
    """

    encoded = bytearray()
    for part in parts:
        encoded += f"{len(part)}:".encode("ascii")
        encoded += part
    return bytes(encoded)


def observe(request: Any) -> Dict[str, Any]:
    """Bind a caller-supplied source read into deterministic SHA-256 hashes.

    Returns a dict with a ``state`` key:

    - ``DATA_ERROR`` -- the request failed exact-type or UTF-8-encodability
      validation, including the case where ``request`` itself is not
      exactly an ``ObservationRequest`` (see ``validate_request``). No
      hashes are computed; ``errors`` lists what was wrong. This never
      raises, even when ``request`` is ``None``, a ``dict``, an unrelated
      object, an ``ObservationRequest`` subclass, or an otherwise
      well-typed ``ObservationRequest`` whose ``source_id`` or
      ``source_version`` contains a lone surrogate that cannot be encoded
      as UTF-8.
    - ``OBSERVED``   -- the request validated. The result carries three
      independent digests:

      - ``source_identity_hash``        -- SHA-256 of ``source_id`` alone.
      - ``source_version_binding_hash`` -- SHA-256 of ``source_id`` and
        ``source_version`` bound together via length-prefixed encoding
        (see ``_length_prefixed``), so it changes whenever either field
        changes and cannot be spoofed by shuffling characters between them.
      - ``raw_payload_hash``            -- SHA-256 of ``raw_payload`` as
        supplied, unmodified.

    This function is pure: identical inputs always produce identical
    output, and it has no side effects.
    """

    errors = validate_request(request)
    if errors:
        return {"state": "DATA_ERROR", "errors": sorted(set(errors))}

    source_id_bytes = request.source_id.encode("utf-8")
    source_version_bytes = request.source_version.encode("utf-8")

    return {
        "state": "OBSERVED",
        "source_identity_hash": hashlib.sha256(source_id_bytes).hexdigest(),
        "source_version_binding_hash": hashlib.sha256(
            _length_prefixed(source_id_bytes, source_version_bytes)
        ).hexdigest(),
        "raw_payload_hash": hashlib.sha256(request.raw_payload).hexdigest(),
    }
