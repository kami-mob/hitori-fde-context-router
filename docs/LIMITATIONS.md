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

## The public reference code is deliberately bounded

This repository now contains five dependency-free Python reference surfaces:

- `reference/minimal_resolver.py` demonstrates the **decision-resolution contract**.
- `reference/source_read_gate.py` demonstrates **pure/local Source Read Gate outcome logic** from caller-supplied request metadata and `read_log`.
- `reference/context_router_preflight.py` demonstrates the **pure/local composition** of the two functions above, sequencing them in the conditional order [`ARCHITECTURE.md`](ARCHITECTURE.md) specifies for steps 0 and 1. See [`CONTEXT_ROUTER_PREFLIGHT.md`](CONTEXT_ROUTER_PREFLIGHT.md).
- `reference/context_selection.py` demonstrates **step 2 planning** — deciding which already-scored, already-tiered candidates belong in the HOT/WARM/COLD read plan. See [`CONTEXT_SELECTION.md`](CONTEXT_SELECTION.md).
- `runtime/selective_recall.py` demonstrates the **step 3 runtime boundary** — validating a `SELECTED` plan and invoking only a caller-supplied loader for IDs already present in that plan. See [`SELECTIVE_RECALL_RUNTIME.md`](SELECTIVE_RECALL_RUNTIME.md).

The first four surfaces do **not**:

- connect to external repositories or document stores
- fetch a user-designated document
- independently verify that an external source was actually read
- detect every product-level continuation/source designation automatically
- enforce the Source Read Gate end-to-end at the connector or product integration layer
- score, classify, or determine relevance of any candidate context on their own

`source_read_gate.py` can model continuation, source availability, AND/OR requirements, and no-external-read constraints when those facts are supplied by the caller. It does not discover or prove those facts itself.

`context_router_preflight.py` adds no behavior beyond sequencing the two composed
functions: it introduces no I/O, retrieval, external model invocation, agentic execution,
HOT/WARM/COLD loading, or production runtime, and it does not change either composed
function's own contract or test coverage. A `PASS` from the composition's gate stage is
not proof that an external read happened; that evidence is still supplied by the caller
via `read_log`, exactly as in `source_read_gate.py` alone.

`context_selection.py` can only be as accurate as the relevance scoring, tier
assignment, and condition/explicit-source flags the caller supplies for each
candidate; it does not itself judge what is relevant, what tier something belongs
in, or whether an explicit source designation is genuine. It decides what a step 2
plan should contain; it does not itself load, fetch, or retrieve any selected content.

`runtime/selective_recall.py` is intentionally one layer narrower than a connector or
retrieval system. It calls only the caller-supplied `loader(candidate_id)` for IDs already
present in a validated plan, but it does not choose a connector, authenticate a source,
verify source provenance, judge loader correctness, or independently prove that an
external read occurred. Any actual filesystem/network/connector I/O is implemented by
the caller's loader. Loader behavior therefore remains part of the surrounding product
boundary, including timeout policy, authentication, source identity, and secret-safe
error handling. The reference records `str(exception)` for a failed loader call; callers
must not place credentials or other sensitive material in loader exception messages that
may be propagated in the returned failure mapping.

The Explicit Source Read Gate described in [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md) is therefore both a public behavioral contract and a small reproducible decision model, but it is not a complete retrieval or connector implementation. The Selective Recall runtime similarly demonstrates a bounded execution boundary without turning this repository into a complete production retrieval stack.

## Canonical sources still matter

A resolver can only be as reliable as the records it receives.

If authoritative sources are missing, stale, contradictory, or improperly classified, the correct result may be `UNKNOWN`, `CONFLICT`, `VERIFY`, or `DATA_ERROR` rather than a useful value.

If a user explicitly designates a source and that source is unavailable, a similar record elsewhere should not automatically be treated as equivalent evidence.

Likewise, the Source Read Gate reference model can only evaluate the `read_log` and source-status information it receives. Incorrect caller-supplied evidence can produce an incorrect gate result.

A Selective Recall plan also depends on caller-supplied candidate metadata. If the wrong IDs were selected upstream, the runtime's plan-bounded loading cannot correct that semantic mistake on its own.

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
- proof that an arbitrary caller-supplied loader is safe, correct, or source-authentic

## Public examples are synthetic

The public package deliberately removes real company, customer, infrastructure, production, authentication, workspace-specific source, and internal-code details.

This improves safety and portability, but means the public examples are smaller than the operational environment that motivated the design.

## Licensing

No open-source license is declared in this version. Repository visibility and software reuse rights are separate decisions. Licensing should be selected explicitly before third-party reuse is encouraged.
