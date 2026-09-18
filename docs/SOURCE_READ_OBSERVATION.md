# Source Read Observation

## Why this exists

The [Source Read Gate](SOURCE_READ_GATE.md) establishes *that* a designated
source must actually be read before source-dependent claims are made. It
takes what was read as a given (`read_log`, supplied by the caller) and
resolves whether the read requirement was satisfied.

Source Read Observation sits one layer below that: it is the smallest
pure/local surface for **binding** what was read -- a source identity, a
version/revision marker, and the exact raw payload bytes -- into a
deterministic record, so that record can later be compared for equality
without re-transmitting the payload.

It answers one narrow question: *"do these caller-supplied values hash the
way this function says they hash?"* It does not answer, and is not designed
to answer, whether the read was trustworthy, current, authorized, or real.

## Contract

1. **Caller-supplied values only**
   - `source_id`, `source_version`, and `raw_payload` are provided by the
     caller as in-memory values. This module never fetches, searches, or
     discovers a source itself.

2. **Exact-type, fail-closed validation -- request object first**
   - The top-level `request` argument itself is checked with
     `type(request) is ObservationRequest` *before* any field on it is
     read. A caller that hands `observe()` or `validate_request()` a
     `None`, a `dict`, an unrelated object, or even an `ObservationRequest`
     subclass gets back a single `DATA_ERROR`-worthy message -- never an
     `AttributeError` from reaching for `.source_id` on something that
     doesn't have it.
   - Once the request object itself is confirmed exact, its fields are
     checked the same way: `source_id` and `source_version` must be
     exactly `str` (non-empty); `raw_payload` must be exactly `bytes` (may
     be empty).
   - Type checks use `type(x) is ...`, not `isinstance`, throughout, so a
     `bool` (an `int` subclass), a `bytearray`/`memoryview` standing in for
     `bytes`, a `str` subclass, or an `ObservationRequest` subclass are all
     rejected rather than silently accepted or coerced.
   - Any violation -- at the request level or the field level -- fails
     closed to `DATA_ERROR` with no hashes computed and nothing raised.

3. **UTF-8 encodability, not just type, for text fields**
   - A well-typed, non-empty `str` is not automatically hashable as UTF-8:
     Python strings may contain lone surrogate code points (U+D800-U+DFFF)
     that correspond to no Unicode scalar value -- for example after
     `surrogateescape`-decoding non-UTF-8 bytes, or when built directly
     from `chr(0xD800)`. Encoding such a string raises
     `UnicodeEncodeError`.
   - `source_id` and `source_version` are each checked for UTF-8
     encodability *before* any hash is computed. A value that is exactly
     `str`, non-empty, but not UTF-8 encodable fails closed to
     `DATA_ERROR` with a dedicated message (`"... must be UTF-8
     encodable"`) instead of letting the encode error escape from inside
     `observe()`.
   - This check only rejects malformed Unicode (lone surrogates). Any
     valid Unicode text -- accented Latin, CJK, emoji, or any other
     character outside ASCII -- encodes to UTF-8 without issue and is
     hashed normally; valid inputs' hashes are unaffected by this rule.

4. **Deterministic binding, not storage**
   - `observe()` is a pure function: identical inputs always produce
     identical digests, and nothing is written anywhere.
   - Three independent SHA-256 digests are returned: one over the identity
     alone, one binding identity and version together (via length-prefixed
     encoding, so the two fields cannot be shuffled into a colliding pair),
     and one over the raw payload bytes as supplied.

5. **No claims beyond the hash**
   - A successful `OBSERVED` result means only that the supplied values
     hash the way this module deterministically says they hash. See
     "What this does not mean" below.

## What this does not mean

An `OBSERVED` result is **not** a claim that:

- the source is **trusted** or the payload is **authentic**
- the read is **fresh** (this module never reads a clock)
- the caller was **authorized** to read the source (no permission check)
- the payload is **complete** (no size, schema, or coverage check)
- any of this was **externally proven** (no connector, network, or
  filesystem I/O; the module cannot see whether a read actually happened,
  only bind the values it is handed)

Those properties, if needed, belong to layers outside this module -- an
authentication system, a freshness policy, or an external attestation --
none of which this reference implementation provides or simulates.

## Reference implementation

[`reference/source_read_observation.py`](../reference/source_read_observation.py)
is a dependency-free, pure/local model of the contract above.

`ObservationRequest(source_id, source_version, raw_payload)` describes one
caller-supplied read. `observe(request)` returns a dict with a `state` key:

- `DATA_ERROR` -- validation failed: `request` itself is not exactly an
  `ObservationRequest`, one of its fields failed exact-type validation, or
  `source_id`/`source_version` is a well-typed, non-empty `str` that is not
  UTF-8 encodable (a lone surrogate). `errors` lists what was wrong. No
  hashes are computed, and no exception is raised regardless of what
  `request` is.
- `OBSERVED` -- the request validated. The result carries:
  - `source_identity_hash` -- SHA-256 of `source_id` alone.
  - `source_version_binding_hash` -- SHA-256 binding `source_id` and
    `source_version` together via length-prefixed encoding.
  - `raw_payload_hash` -- SHA-256 of `raw_payload` as supplied, unmodified.

`validate_request(request)` is exposed separately for callers that want the
error list without computing hashes. It applies the same top-level,
fail-closed request check before touching any field, and the same
UTF-8-encodability check before any field is hashed.

Run locally:

```bash
python tests/test_source_read_observation.py
```

Expected result: all tests pass, including a known-vector test that locks
the length-prefixed encoding scheme used for `source_version_binding_hash`,
a set of tests that hand `observe()` malformed top-level objects (`None`, a
`dict`, an unrelated object, a `str`, and an `ObservationRequest`
subclass), and a set of tests covering malformed Unicode (lone surrogates
in `source_id` and `source_version`) alongside valid non-ASCII text (CJK,
accented Latin, emoji) -- all confirming the fail-closed cases return
`DATA_ERROR` without raising, and the valid cases hash exactly as before.

## Public implementation boundary

This module demonstrates deterministic **value binding**, not source
verification. It performs no network, filesystem, authentication,
permission, clock, or persistence work, and it does not discover
connectors or mutate any production system. Whether the bytes it is handed
were actually read from the named source -- and whether that source can be
trusted -- is outside its scope; those questions belong to the caller and
to layers this reference implementation does not model.

See also:

- [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
