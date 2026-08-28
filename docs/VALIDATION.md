# Validation

## Validation strategy

The design was validated in layers rather than relying on one large end-to-end prompt.

### Deterministic resolution tests

Covered cases include:

- current authoritative decision
- future-effective decision gating
- superseded predecessor
- unknown subject / field
- multiple authoritative survivors
- duplicate provenance
- malformed supersession
- dangling relation
- cycle
- cross-scope relation
- invalid timing
- stale selected record
- semantic conflict evidence

### Property / randomized tests

Randomized records were used to exercise combinations of:

- scopes
- statuses
- timing
- relation shapes
- unrelated malformed records

The purpose was not to prove all possible future inputs, but to detect structural regressions beyond a small hand-written fixture set.

### Scope-isolation tests

Runtime resolution was checked to ensure that malformed data in an unrelated scope does not necessarily block a valid target scope, while offline full-registry validation still reports the global defect.

### Safety tests

Production and permission-related safety triggers were checked independently of resolution states such as `RESOLVED`, `UNKNOWN`, `CONFLICT`, and `VERIFY`.

### Long-context / re-sync tests

The system was tested for scenarios where conversation history is long or a task is resumed later. Expected behavior is to re-sync with canonical current state rather than relying only on conversational memory.

## Sanitized validation results

The private implementation reached the following checkpoints before this public reference package was prepared:

### External Context OS reference implementation

- deterministic tests: **127/127 PASS**
- randomized/property tests: **3,200/3,200 PASS**
- semantic consistency checks: **PASS**

### Context Router shadow implementation

- static invariants: **PASS**
- deterministic tests: **29/29 PASS**
- property tests: **85,000/85,000 PASS**

### Limited low-risk pilot

A one-decision-point, context-only pilot was used before considering broader rollout.

Observed gates:

- baseline regression: PASS
- resolution tests: PASS
- safety tests: PASS
- offline integrity: PASS
- rollback test: PASS
- no broad COLD read observed
- no source drift observed

### Scripted operational observation

Ten operational scenarios were exercised after limited application:

- scenarios passed: **10/10**
- false VERIFY: 0
- false CONFLICT: 0
- stale revival: 0
- safety miss: 0
- broad COLD read: 0
- unrelated constant read: 0
- runtime exception: 0

## Interpretation

These results are evidence that the tested implementation behaved consistently under the tested scenarios.

They are **not** a mathematical proof of all future AI behavior, all models, all workspaces, or all external-memory structures.

The strongest claim supported by the evidence is:

> A resolution-first, selective-recall architecture can be implemented and regression-tested so that old decisions, ambiguous provenance, stale state, unrelated context, and conditional safety rules are handled explicitly instead of being left to implicit model judgment.
