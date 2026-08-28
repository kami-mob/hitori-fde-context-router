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

### Explicit Source Read Gate tests

A separate source-grounding failure class was tested after natural use exposed a case where an explicitly designated saved source could be bypassed by conversational summaries or prior context.

The dedicated sanitized regression set covered:

- explicit repository source request
- explicit document source request
- multi-source AND semantics
- multi-source OR semantics
- saved-material request without an exact path
- exact repository/path request
- missing source with memory substitution blocked
- "use only the current attachment" constraint
- standalone question where no external read is required
- continuation turn inheriting the prior explicit source designation

Result: **10/10 PASS**.

A post-sync live dogfood smoke then checked five operational gates:

- **P1 — Actual source read:** designated source was actually fetched/read before source-grounded claims
- **P2 — No memory substitution:** prior chat/project summary/model memory was not treated as the designated source
- **P3 — Fail closed:** unavailable exact evidence remained unsupported instead of being reconstructed from memory
- **P4 — Bounded retrieval:** no unrelated COLD sweep was introduced
- **P5 — Source-grounded answer:** reported status matched the source actually read

Result: **P1–P5 PASS**.

The public repository does not include workspace-specific source names, paths, product settings, or private operational logs from those tests.

## Sanitized validation results

The private implementation reached the following checkpoints before and during preparation of this public reference package:

### External Context OS reference implementation

- deterministic tests: **127/127 PASS**
- randomized/property tests: **3,200/3,200 PASS**
- semantic consistency checks: **PASS**

### Explicit Source Read Gate integration

- dedicated source-read regression: **10/10 PASS**
- post-sync live dogfood smoke: **P1–P5 PASS**
- memory substitution on the tested missing-source case: **blocked**
- unrelated broad COLD read in the tested smoke: **0**

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

They are **not** a mathematical proof of all future AI behavior, all models, all workspaces, all connectors, or all external-memory structures.

The strongest claim supported by the evidence is:

> A resolution-first, selective-recall architecture can be implemented and regression-tested so that old decisions, ambiguous provenance, stale state, unrelated context, conditional safety rules, and explicit user-selected source requirements are handled explicitly instead of being left entirely to implicit model judgment.
