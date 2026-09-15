# Context Router Preflight

## What this is

[`reference/context_router_preflight.py`](../reference/context_router_preflight.py)
is a small pure/local composition of two reference models that already exist
in this repository:

- [`source_read_gate.evaluate`](../reference/source_read_gate.py) — the
  Explicit Source Read Gate outcome logic described in
  [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md).
- [`minimal_resolver.resolve_current`](../reference/minimal_resolver.py) —
  the current-decision resolver described in
  [`DECISION_RESOLUTION_SPEC.md`](DECISION_RESOLUTION_SPEC.md).

It adds no new behavior of its own: it only sequences the two existing
functions in the order [`ARCHITECTURE.md`](ARCHITECTURE.md) already
specifies — the gate sits at step 0, conditionally, before the Resolution
Kernel at step 1.

## What it does

`resolve_with_source_read_gate(gate_request, records, *, domain, subject,
field, as_of, verify_after_days=30)`:

1. Evaluates the gate via `evaluate(gate_request)`.
2. Calls `resolve_current(...)` only when the gate outcome is `PASS`
   (the declared source requirement was satisfied) or `NOT_APPLICABLE`
   (no explicit source was in force this turn).
3. Otherwise — `VERIFY`, `UNKNOWN`, or `DATA_ERROR` — returns the gate's own
   outcome unchanged and never calls the resolver.

This means an unresolved, impossible, or malformed source-read requirement
is never quietly papered over with a resolver opinion formed without the
evidence the user required. The resolver keeps its own independent
fail-closed states (`UNKNOWN`, `CONFLICT`, `VERIFY`, `DATA_ERROR`) once it
does run; the preflight step does not filter or reinterpret those.

## Return shape

The result always has a `stage` key:

- `stage == "source_read_gate"` — the gate did not reach a proceed state.
  The gate's outcome dict (`state`, and whichever of `reason`, `missing`,
  `unavailable`, or `errors` that outcome carries) is merged in directly.
- `stage == "resolution"` — the gate proceeded and the resolver ran. The
  resolver's outcome dict (`state`, and whichever of `record`,
  `decision_ids`, or `errors` that outcome carries) is merged in directly,
  with the gate's own outcome attached under `gate` for traceability.

## What this is not

- It performs no I/O. Like `source_read_gate.py`, whether a source was
  actually read is supplied by the caller via `read_log`; this module does
  not fetch, search, or verify anything.
- It does not add HOT/WARM/COLD loading, external model invocation,
  agentic execution, or a production runtime. It is a same-process function
  call between two existing pure functions.
- It does not change either composed function's own contract or test
  coverage; `tests/test_context_router_preflight.py` guards the composition
  boundary only, and re-running the existing suites (see below) shows the
  composed functions' own behavior is untouched.

## Run locally

```bash
python tests/test_context_router_preflight.py
python tests/test_resolver.py
python -m unittest discover -s tests -p test_source_read_gate.py
python -m compileall reference tests
```

Expected result: all tests pass.

See also:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md)
- [`DECISION_RESOLUTION_SPEC.md`](DECISION_RESOLUTION_SPEC.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
