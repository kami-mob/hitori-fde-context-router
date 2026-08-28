# Limitations and Non-Claims

This public reference is intentionally conservative about what the evidence proves.

## It does not modify model internals

Context Router is an external architecture and operating pattern. It does not install a new reasoning engine inside an AI model and does not override platform safety or product behavior.

## It does not guarantee correctness

Explicit resolution and fail-closed states reduce some classes of ambiguity, but they do not guarantee that:

- every future request is classified correctly
- every external source is complete
- every live system value is current
- every safety condition is detected without suitable metadata or rules
- every model follows an instruction perfectly

## Canonical sources still matter

A resolver can only be as reliable as the records it receives.

If authoritative sources are missing, stale, contradictory, or improperly classified, the correct result may be `UNKNOWN`, `CONFLICT`, `VERIFY`, or `DATA_ERROR` rather than a useful value.

## Volatile state requires live verification

Fast-changing operational state should be checked against an appropriate live source when material to the task. A historical context record is not a substitute for live verification.

## Test results are implementation evidence, not universal benchmarks

Reported private validation counts demonstrate regression coverage for the tested implementation. They should not be interpreted as:

- a benchmark against other memory systems
- a guaranteed token-cost reduction
- a guaranteed usage-limit reduction
- proof that another implementation will produce identical results

## Public examples are synthetic

The public package deliberately removes real company, customer, infrastructure, production, authentication, and internal-code details.

This improves safety and portability, but means the public examples are smaller than the private operational environment that motivated the design.

## Licensing

No open-source license is declared in this version. Repository visibility and software reuse rights are separate decisions. Licensing should be selected explicitly before third-party reuse is encouraged.
