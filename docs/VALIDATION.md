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

The larger private/integration regression set covered:

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

## Public reproducible reference checks

The public repository contains six small dependency-free Python reference surfaces.

### Decision resolver

```bash
python tests/test_resolver.py
```

This exercises the existing synthetic decision-resolution reference cases.

### Source Read Gate outcome model

```bash
python -m unittest discover -s tests -p test_source_read_gate.py
```

The Source Read Gate suite contains **32 tests**. It covers the pure/local gate model plus regression guards for the existing decision resolver, including:

- explicit source present / absent from `read_log`
- ALL / ANY semantics
- fail-closed unavailable-source handling
- no-memory-substitution behavior in the modeled inputs
- continuation carryover and source-change behavior
- validation scoped only to the effective current/continuation requirement
- stale inactive metadata not causing spurious `DATA_ERROR`
- `no_external_read` allowing already-present evidence while blocking a needed new retrieval
- bounded-retrieval `extra_reads` reporting
- malformed active request handling

The suite does **not** perform external connector I/O. A passing test proves the local decision logic for supplied inputs, not that a real external fetch happened.

### Context Router preflight composition

```bash
python tests/test_context_router_preflight.py
```

The suite contains **7 tests**. It guards only the gate-then-resolver sequencing boundary described in [`CONTEXT_ROUTER_PREFLIGHT.md`](CONTEXT_ROUTER_PREFLIGHT.md) — that the resolver runs when the gate reaches `PASS` or `NOT_APPLICABLE`, and that the gate's own outcome is returned unchanged (and the resolver is never called) for `VERIFY`, `UNKNOWN`, or `DATA_ERROR`. It does not re-validate the resolver's or the gate's own internal behavior; the existing resolver and Source Read Gate suites above still cover that.

### Context Selection planner

```bash
python tests/test_context_selection.py
```

The suite contains **18 tests**. It covers the step 2 planning rules described in [`CONTEXT_SELECTION.md`](CONTEXT_SELECTION.md): `HOT` selection by `relevant`, `WARM` selection by an active `condition`, `COLD` exclusion by default, the `explicit_source` carve-out across all tiers, the `explicitly_required` carve-out scoped to `COLD` only, deterministic HOT-then-WARM-then-COLD plan ordering, and `DATA_ERROR` on duplicate ids or an unknown tier. This is a planning check only; the module performs no retrieval or loading of any candidate's content.

### Selective Recall runtime boundary

```bash
python tests/test_selective_recall_runtime.py
```

The suite contains **12 tests**. It covers the step 3 boundary described in [`SELECTIVE_RECALL_RUNTIME.md`](SELECTIVE_RECALL_RUNTIME.md):

- plan IDs are loaded exactly once and in plan order;
- an empty plan performs no load;
- candidates excluded upstream are not loaded merely because they exist elsewhere;
- one loader failure is recorded per ID without substituting fallback content or aborting later IDs;
- malformed, wrong-stage, non-`SELECTED`, missing-plan, non-string-ID, and duplicate-ID plans fail closed before loader invocation;
- an end-to-end synthetic case consumes the real `select_context` output and does not load an excluded COLD candidate.

The test loader is synthetic and in-memory. These tests prove plan-bounded orchestration behavior; they do not prove connector authentication, source provenance, network reliability, or correctness of an arbitrary caller-supplied loader.

### Work Gate safety-independence boundary

```bash
python tests/test_work_gate.py
```

The suite contains **18 tests**. It covers the step 4 boundary described in [`WORK_GATE.md`](WORK_GATE.md), including:

- literal `RESOLVED` with no active trigger returns `PROCEED`;
- `UNKNOWN`, `CONFLICT`, `VERIFY`, `DATA_ERROR`, no decision, and other non-success states fail closed as `REVIEW_REQUIRED`;
- production and permission triggers force `REVIEW_REQUIRED` even when the decision is already `RESOLVED`;
- both active triggers are reported together;
- malformed decision/trigger field types fail closed before trigger interpretation;
- `None`, a `dict`, and other non-`WorkGateRequest` object shapes fail closed as `malformed_input` rather than raising due to field access.

These tests exercise only a pure/local classifier over caller-supplied values. They do not prove that the caller detected a real production or permission condition correctly, and a `PROCEED` result is not execution authority.

A syntax/bytecode check is also supported:

```bash
python -m compileall reference runtime tests
```

### Current CI scope

The GitHub Actions workflow in this repository ([`.github/workflows/reference-tests.yml`](../.github/workflows/reference-tests.yml)) invokes the decision resolver, Source Read Gate, Context Router preflight, Context Selection, Selective Recall runtime, and Work Gate suites, followed by `python -m compileall reference runtime tests`, on pull requests and pushes.

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

The public reproducible tests and the larger private/integration aggregate evidence are separate evidence classes and should not be conflated.

The strongest claim supported by the evidence is:

> A resolution-first, selective-recall architecture can be implemented and regression-tested so that old decisions, ambiguous provenance, stale state, unrelated context, conditional safety rules, explicit user-selected source requirements, and bounded selected-context loading are handled explicitly instead of being left entirely to implicit model judgment.
