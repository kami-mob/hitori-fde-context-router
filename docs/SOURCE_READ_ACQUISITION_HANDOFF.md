# Source Read Acquisition Handoff — adapter-fed reference

This is a **bounded composition reference** between an explicitly selected
source, an externally supplied reader adapter, local Source Read Evidence
Binding, and the existing Source Read Gate. It does not implement a
connector, authenticate a user, inspect API permissions, confirm real
source provenance or authorize downstream work.

`AcquisitionRequest(declared_sources, mode="ALL", no_external_read=False)`
requires a nonempty tuple of unique, UTF-8-encodable source identifiers.
`acquire_declared_sources(request, fetcher)` receives a caller-supplied
callable `fetcher(source_id)` which is expected to perform one independently
authorized read and return an exact
`FetchedSource(source_id, source_version, raw_payload)` record. A caller
MUST enforce the actual connector's authorization, access scope, source
identity, revision trust, timeout, read limit and auditing outside this
module. The local reference cannot verify those properties.

## Bounded process

1. Validate the exact AcquisitionRequest type and active source tuple
   before any read. Reject duplicate, empty and malformed identifiers,
   unsupported ALL/ANY, invalid booleans, and non-callable adapters.
2. Never invoke the adapter when `no_external_read=True`.
3. Invoke the caller-supplied adapter at most once per selected source, in
   declared order; stop after the first locally successful source for ANY.
   No discovery, fallback to unrelated sources, timeout retry or
   automatic second attempt is performed here.
4. Accept only an exact FetchedSource value with the requested exact
   source ID, nonempty valid UTF-8 source version, and exact raw bytes.
   Failure, timeout and malformed receipts return generic
   `VERIFY` or `DATA_ERROR`; a callback exception is not proof that the
   requested source is permanently unavailable.
5. Derive a fresh local evidence record from the returned bytes,
   verify the record against the same observation request with the
   existing pure/local Source Read Evidence Binding check, and add that
   source to the local read log **only after** both checks succeed.
6. Evaluate the Source Read Gate for exactly the declared sources and
   just-completed local reads. A local PASS returns only `state=PASS`,
   `stage=local_source_read_gate`, `evidence_scope=CALLER_SUPPLIED_ADAPTER`,
   and `read_count`. Failures return generic `DATA_ERROR` or `VERIFY`,
   with no raw bytes, source IDs, version values, hashes or exception text.

## Trust boundary and excluded behavior

A caller can supply a fabricated receipt, spoof an adapter or return
stale but internally consistent bytes. This reference checks local
consistency, not whether an external service actually produced the bytes.
**Do not interpret its PASS as independent authentication, permission
grant, fresh trusted external provenance, a real connector-backed fetch,
end-to-end source-grounding proof or production authorization.** An actual
source integration needs a specifically selected authenticated connector,
independently confirmed permissions, accurate source identity, trusted
revision metadata, bounded network requests and audit evidence at the
caller/adapter boundary. Its failures must remain fail-closed.

This module performs no I/O itself. Only its explicitly supplied callback
may perform I/O in a surrounding authorized integration. This module does
not call the resolution kernel or change product workflows or permissions.
It does not inherit authority from any historical Claude Routine execution.

## Deterministic verification

```bash
python tests/test_source_read_acquisition_handoff.py
python tests/test_source_read_evidence_binding.py
python -m compileall reference runtime tests
```

The new test suite uses synthetic adapter callbacks only. The public Reference Tests workflow invokes it as a **direct CI step**
alongside all preexisting component and integration regressions. Live authenticated
connector checks are a separate unimplemented acceptance gate.
