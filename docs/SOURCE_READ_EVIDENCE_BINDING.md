# Source Read Evidence Binding

## Purpose

Given a caller-supplied `ObservationRequest` and `SourceReadEvidence`, verify
that every one of the four evidence fields matches one fresh internal
`derive_evidence(observation_request)` call. This is pure in-memory
reference logic, not a network/connector read or a source authorization gate.

## Public API

`reference/source_read_evidence_binding.py` exports exactly
`SourceReadEvidenceBindingRequest(observation_request, supplied_evidence)`
(a frozen two-field dataclass) and `verify_binding(request)` (one argument).
There is no caller-supplied fresh evidence parameter, alternate API, or cache.

The only results are the exact dictionaries `{"state":"BINDING_MATCHED"}`
and `{"state":"DATA_ERROR"}`. Neither result includes source identity,
payload, source version, hash, exception, field name, repr, or failure reason.

## Fail-closed sequence

1. Reject every non-exact `SourceReadEvidenceBindingRequest` type before
   accessing any field. Safe-read **both** wrapper attributes, one attempt
   each even when the first raises. Missing/raising access returns DATA_ERROR.
2. Require `type(supplied_evidence) is SourceReadEvidence`: subclasses,
   duck-typed objects and dicts are not equivalent.
3. Safe-read **all four** supplied evidence attributes in order, one
   attempt per field, even when an earlier one raises. Only after all four
   read attempts, reject missing/raising fields or any field whose type is
   not exactly the built-in `str`. Invalid supplied evidence never derives.
4. For valid supplied evidence, invoke the imported
   `derive_evidence(observation_request)` internally exactly once. Catch
   ordinary exceptions and report only generic DATA_ERROR. Require the
   result to be exactly `dict`, the state to be exactly built-in `str`
   with value `EVIDENCED`, and the fresh evidence object to be exactly
   `SourceReadEvidence`.
5. Safe-read **all four** fresh evidence fields once each before any
   exact-`str` type validation. Missing, raising, malformed, subclassed
   or hostile fields return generic DATA_ERROR.
6. Only after both sets of fields pass exact-type checks, compare
   corresponding values via unbound `str.__eq__(supplied, fresh) is True`.
   All four matches return BINDING_MATCHED; any mismatch or unexpected
   comparison exception returns generic DATA_ERROR.

Frozen dataclass annotations are **not runtime field validators**: the
implementation and tests deliberately handle exact-instance records made
with `object.__new__`, invalid field objects, hostile equality, and
descriptors patched onto the exact dataclass itself.

## Tests and integration limits

Run the binding tests independently:

```bash
python tests/test_source_read_evidence_binding.py
```

The `Reference Tests` GitHub Actions workflow additionally runs this
command as its own CI step; a successful legacy Source Read Evidence test
alone is not evidence that the binding test ran. Full reference regression
and `python -m compileall reference runtime tests` are required as well.

BINDING_MATCHED means only that the four caller-supplied in-memory fields
match a fresh derivation of a caller-supplied observation request. It is
**not** a Source Read Gate PASS, authentic source, actual external read,
authorized access, freshness, completeness, permission, or production
attestation. The module performs no I/O, persistence, connector discovery,
network call, credential access, clock read, or Source Read Gate evaluation.

The GitHub author/editor and CI runner may perform ordinary repository
file operations and tests to develop and verify this module; those
operations are not behavior of the pure/local binding module itself.
