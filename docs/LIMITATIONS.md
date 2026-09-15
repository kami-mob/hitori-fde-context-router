# Limitations and Non-Claims

This public reference is intentionally conservative about what the evidence proves.

## It does not modify model internals

Context Router is an external architecture and operating pattern. It does not install a new reasoning engine inside an AI model and does not override platform safety or product behavior.

## It does not guarantee correctness

Explicit resolution, source-read gates, and fail-closed states reduce some classes of ambiguity, but they do not guarantee that:

- every future request is classified correctly
- every explicit source designation is recognized perfectly
- every external source is complete
- every source connector remains available
- every live system value is current
- every safety condition is detected without suitable metadata or rules
- every model follows an instruction perfectly

## The public reference code does not perform external source I/O

This repository now contains three dependency-free Python reference models:

- `reference/minimal_resolver.py` demonstrates the **decision-resolution contract**.
- `reference/source_read_gate.py` demonstrates **pure/local Source Read Gate outcome logic** from caller-supplied request metadata and `read_log`.
- `reference/context_router_preflight.py` demonstrates the **pure/local composition** of the two functions above, sequencing them in the conditional order [`ARCHITECTURE.md`](ARCHITECTURE.md) specifies for steps 0 and 1. See [`CONTEXT_ROUTER_PREFLIGHT.md`](CONTEXT_ROUTER_PREFLIGHT.md).

They do **not**:

- connect to external repositories or document stores
- fetch a user-designated document
- independently verify that an external source was actually read
- detect every product-level continuation/source designation automatically
- enforce the Source Read Gate end-to-end at the connector or product integration layer

`source_read_gate.py` can model continuation, source availability, AND/OR requirements, and no-external-read constraints when those facts are supplied by the caller. It does not discover or prove those facts itself.

`context_router_preflight.py` adds no behavior beyond sequencing the two composed
functions: it introduces no I/O, retrieval, external model invocation, agentic execution,
HOT/WARM/COLD loading, or production runtime, and it does not change either composed
function's own contract or test coverage. A `PASS` from the composition's gate stage is
not proof that an external read happened; that evidence is still supplied by the caller
via `read_log`, exactly as in `source_read_gate.py` alone.

The Explicit Source Read Gate described in [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md) is therefore both a public behavioral contract and a small reproducible decision model, but it is not a complete retrieval or connector implementation.

## Canonical sources still matter

A resolver can only be as reliable as the records it receives.

If authoritative sources are missing, stale, contradictory, or improperly classified, the correct result may be `UNKNOWN`, `CONFLICT`, `VERIFY`, or `DATA_ERROR` rather than a useful value.

If a user explicitly designates a source and that source is unavailable, a similar record elsewhere should not automatically be treated as equivalent evidence.

Likewise, the Source Read Gate reference model can only evaluate the `read_log` and source-status information it receives. Incorrect caller-supplied evidence can produce an incorrect gate result.

## Volatile state requires live verification

Fast-changing operational state should be checked against an appropriate live source when material to the task. A historical context record is not a substitute for live verification.

## Test results are implementation evidence, not universal benchmarks

Reported validation counts demonstrate regression coverage for the tested implementation. They should not be interpreted as:

- a benchmark against other memory systems
- a guaranteed token-cost reduction
- a guaranteed usage-limit reduction
- proof that another implementation will produce identical results
- proof that every future phrasing of an explicit-source request will be routed correctly
- proof that all external source connectors will fail closed identically
- proof that the public pure/local gate model guarantees an external read actually happened

## Public examples are synthetic

The public package deliberately removes real company, customer, infrastructure, production, authentication, workspace-specific source, and internal-code details.

This improves safety and portability, but means the public examples are smaller than the operational environment that motivated the design.

## Licensing

No open-source license is declared in this version. Repository visibility and software reuse rights are separate decisions. Licensing should be selected explicitly before third-party reuse is encouraged.
