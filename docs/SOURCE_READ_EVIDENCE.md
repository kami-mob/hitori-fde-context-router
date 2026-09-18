# Source Read Evidence

## Why this exists

[Source Read Observation](SOURCE_READ_OBSERVATION.md) binds one
caller-supplied source read (`source_id`, `source_version`, `raw_payload`)
into three deterministic SHA-256 digests. That result is a plain dict:
nothing stops a caller from mutating it, re-attaching a different payload
to it, or forwarding the raw payload and raw version string onward when
only proof of the read needs to travel.

Source Read Evidence sits directly on top of that: it is the smallest
pure/local surface for turning a *fresh* `OBSERVED` result into an
immutable, hash-only record that can be carried or compared without
re-exposing the raw payload or the raw version string.

It answers one narrow question: *"given this exact source read, what is the
immutable, hash-only record of it?"* It does not answer, and is not
designed to answer, whether that record satisfies any read requirement.

## Contract

1. **Built only from a fresh observation**
   - `derive_evidence(request)` calls `observe(request)` itself, on every
     call. Nothing is cached or memoized across calls, so evidence always
     reflects the request handed to that call, not a prior one.
   - There is no parameter through which a caller can hand this module a
     pre-computed hash in place of one `observe()` derives. The only hashes
     that can ever appear in a `SourceReadEvidence` are ones `observe()`
     just computed from the caller-supplied `ObservationRequest`.

2. **Fail closed whenever the observation is not `OBSERVED`**
   - `derive_evidence()` does not repeat `observe()`'s validation; it
     inspects the `state` `observe()` returned. Anything other than
     `OBSERVED` -- `request` not being exactly an `ObservationRequest`
     (including `None`, a `dict`, an unrelated object, or an
     `ObservationRequest` subclass), a field failing exact-type validation,
     or `source_id`/`source_version` being well-typed but not UTF-8
     encodable -- produces `DATA_ERROR` here too, carrying the same
     `errors` `observe()` produced.
   - No `SourceReadEvidence` is constructed on `DATA_ERROR`, and
     `request.source_id` is never read in that branch: a request-shaped
     object whose field access raises still fails closed rather than
     propagating an exception, because the field is never touched.

3. **Immutable, hash-only evidence**
   - On success (`EVIDENCED`), the result carries a frozen
     `SourceReadEvidence` with exactly four fields: `source_id` (carried in
     the clear -- it is an identifier, not secret material),
     `source_identity_hash`, `source_version_binding_hash`, and
     `raw_payload_hash`.
   - `raw_payload` and `source_version` are never included. Those are
     exactly the two fields this record exists to avoid re-exposing.
   - The dataclass is `frozen=True`: reassigning a field after construction
     raises rather than silently mutating evidence that was already handed
     to a caller.

4. **No I/O, no persistence, no gate interaction**
   - This module performs no network, filesystem, authentication,
     permission, clock, or persistence work, and it does not discover
     connectors.
   - It does not call, evaluate, or otherwise touch
     [`source_read_gate.py`](../reference/source_read_gate.py). Deriving
     evidence is not a Source Read Gate `PASS`, and this module makes no
     attempt to produce one.

## What this does not mean

An `EVIDENCED` result is **not** a claim that:

- the underlying read satisfies the **Source Read Gate** (that gate is
  evaluated separately, from `read_log`, by
  [`source_read_gate.py`](../reference/source_read_gate.py))
- the source is **trusted**, the payload is **authentic**, or the read was
  **fresh**, **authorized**, or **complete** -- none of that is established
  by `observe()` either; see
  [`SOURCE_READ_OBSERVATION.md`](SOURCE_READ_OBSERVATION.md#what-this-does-not-mean)
  for the full list this module inherits unchanged
- any of this was **externally proven** -- this module never performs I/O
  and cannot see whether a read actually happened; it only re-shapes the
  hashes `observe()` computed from values the caller supplied

## Reference implementation

[`reference/source_read_evidence.py`](../reference/source_read_evidence.py)
is a dependency-free, pure/local model of the contract above.

`derive_evidence(request)` takes the same `ObservationRequest` that
[`source_read_observation.py`](../reference/source_read_observation.py)'s
`observe()` takes, and returns a dict with a `state` key:

- `DATA_ERROR` -- `observe(request)` did not reach `OBSERVED`. `errors`
  carries the same messages `observe()` produced. No exception is raised
  regardless of what `request` is.
- `EVIDENCED` -- the observation reached `OBSERVED`. `evidence` is a frozen
  `SourceReadEvidence(source_id, source_identity_hash,
  source_version_binding_hash, raw_payload_hash)` built only from that
  fresh result.

Run locally:

```bash
python tests/test_source_read_evidence.py
```

Expected result: all tests pass, including tests confirming evidence
hashes match a fresh, independent `observe()` call on the same request;
that evidence is derived freshly per call rather than cached across calls
with different requests; that the returned record is immutable; that it
never carries `raw_payload` or `source_version`; and that malformed
top-level requests (`None`, a `dict`, an unrelated object, an
`ObservationRequest` subclass, and a request-shaped object that raises on
field access) all fail closed to `DATA_ERROR` without raising and without
producing evidence.

## Public implementation boundary

This module demonstrates carrying a validated observation forward as an
immutable, hash-only record -- nothing more. It performs no network,
filesystem, authentication, permission, clock, or persistence work, it
does not discover connectors or mutate any production system, and it does
not modify or satisfy the Source Read Gate. Whether a `SourceReadEvidence`
record is accepted as sufficient proof of a read by some external system is
outside its scope; that policy belongs to the caller and to layers this
reference implementation does not model.

See also:

- [`SOURCE_READ_OBSERVATION.md`](SOURCE_READ_OBSERVATION.md)
- [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
