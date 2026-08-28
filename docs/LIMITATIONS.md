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

## The public minimal resolver does not perform external source I/O

The dependency-free Python resolver in this repository demonstrates the **decision-resolution contract**.

It does **not**:

- connect to external repositories or document stores
- fetch a user-designated document
- verify that an external source was actually read
- enforce continuation-turn source carryover at the product integration layer

The Explicit Source Read Gate published in [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md) is therefore an architecture/operating contract plus sanitized validation evidence from a larger implementation, not a claim that `reference/minimal_resolver.py` alone provides source-grounded retrieval.

## Canonical sources still matter

A resolver can only be as reliable as the records it receives.

If authoritative sources are missing, stale, contradictory, or improperly classified, the correct result may be `UNKNOWN`, `CONFLICT`, `VERIFY`, or `DATA_ERROR` rather than a useful value.

If a user explicitly designates a source and that source is unavailable, a similar record elsewhere should not automatically be treated as equivalent evidence.

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

## Public examples are synthetic

The public package deliberately removes real company, customer, infrastructure, production, authentication, workspace-specific source, and internal-code details.

This improves safety and portability, but means the public examples are smaller than the operational environment that motivated the design.

## Licensing

No open-source license is declared in this version. Repository visibility and software reuse rights are separate decisions. Licensing should be selected explicitly before third-party reuse is encouraged.
