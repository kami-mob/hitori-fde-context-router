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

The public repository contains eleven small dependency-free Python reference surfaces.

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

### Source Read Observation value-binding boundary

```bash
python tests/test_source_read_observation.py
```

The suite contains **35 tests** for the pure/local Source Read Observation boundary. It covers:

- exact top-level `ObservationRequest` type checking before any field access;
- fail-closed handling of `None`, `dict`, unrelated objects, strings, and `ObservationRequest` subclasses;
- exact field-type checks for `source_id`, `source_version`, and raw `bytes`;
- fail-closed UTF-8 encodability checks for malformed Python Unicode strings containing lone surrogates;
- preservation of valid non-ASCII text such as CJK, accented Latin, and emoji;
- deterministic source-identity, source-version-binding, and raw-payload SHA-256 values, including a known-vector lock for the length-prefixed identity/version encoding;
- no hashes emitted on malformed input.

These tests prove only deterministic binding and fail-closed local validation for caller-supplied in-memory values. They do **not** prove that an external source was actually read, that the named source produced the supplied bytes, or that the source is authentic, fresh, authorized, complete, or externally proven.

### Source Read Evidence boundary

```bash
python tests/test_source_read_evidence.py
```

The suite contains **17 tests** for the pure/local Source Read Evidence boundary. It covers:

- deriving evidence from a fresh Source Read Observation on every call;
- immutable evidence containing exactly `source_id` plus the three observation hashes;
- no raw payload bytes or raw source-version string in the evidence object;
- no caller-supplied precomputed hash input;
- fail-closed handling of malformed top-level requests, request subclasses, malformed field types, and non-UTF-8 source identifiers;
- deterministic repeated derivation for the same valid request;
- no Source Read Gate interaction or PASS generation.

These tests prove only local derivation and data-minimized carriage of a fresh caller-supplied observation result. They do **not** prove that an external source was actually read, that the named source produced the bytes, or that the source is authentic, fresh, authorized, complete, externally proven, or sufficient for Source Read Gate `PASS`.

### Source Read Evidence Binding boundary

```bash
python tests/test_source_read_evidence_binding.py
```

The suite contains **20 tests** for the pure/local Source Read Evidence
Binding check. It verifies the exact request/evidence types, safe reading of
both wrapper fields, completion of all four supplied and all four freshly
derived evidence-field reads before type validation, rejection of malformed
exact dataclass instances, raising descriptors and hostile comparison values,
and exactly one internal derivation for a valid supplied record. Invalid
supplied evidence is rejected without deriving anything. Only the generic
`DATA_ERROR` and exact `BINDING_MATCHED` result mappings are returned.

This suite establishes local value agreement between caller-supplied evidence
and a fresh internal derivation of a caller-supplied observation request.
It does **not** establish a real external read, provenance, authenticity,
authorization, freshness, completeness, Source Read Gate `PASS`, or
production/integration correctness. It is invoked as an independent command
by the public Reference Tests workflow.

### Bounded Source Read acquisition and public GitHub reader

```bash
python tests/test_source_read_acquisition_handoff.py
python tests/test_github_public_pinned_reader.py
# Optional: makes one public network request; not part of default CI
python tests/test_github_public_pinned_live_smoke.py
```

The adapter-fed acquisition handoff suite contains **17** synthetic tests
for explicit source allowlists, ALL/ANY behavior, no-external-read mode,
invalid receipts, exceptions, evidence binding before modeled gate evaluation
and non-disclosing failure results. The pinned public GitHub reader suite
contains **12** mocked-HTTPS tests covering fixed host, exact commit/path
binding, no credential header, size limits, base64 decoding, Git blob digest
checks, malformed responses and integration with the local handoff. Default
public CI runs these tests **independently**, without network access.

A separate opt-in test of **one** public GitHub Contents HTTPS GET at a fixed
public commit completed successfully in public GitHub Actions run
[`35444084250`](https://github.com/kami-mob/hitori-fde-context-router/actions/runs/35444084250). It checked the
returned file bytes against an independently recorded Git blob SHA and
passed the already-read receipt through the local handoff, without a
second HTTP request. This proves the narrowly scoped public read worked
in that environment at that time; it is not evidence of access to
private GitHub data, enterprise connectors, caller authorization,
freshness of changing branches, ongoing network reliability, or a
deployed agent. The local Gate `PASS` remains explicitly labeled
`CALLER_SUPPLIED_ADAPTER` and is not independent provenance attestation.

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

### Re-sync Gate material-boundary classifier

```bash
python tests/test_resync_gate.py
```

The suite contains **9 top-level unittest methods**, including a per-signal subtest loop that checks each of the nine step-5 material-boundary fields independently. It covers the boundary described in [`RESYNC_GATE.md`](RESYNC_GATE.md), including:

- no active signal returns `NOT_REQUIRED`;
- each current/latest, continuation, important-confirmation, implementation, publication/release, production, permission, price/spec/version, or explicit-source-continuation signal independently returns `RESYNC_REQUIRED`;
- multiple active signals are reported deterministically in declared order;
- all nine active signals are preserved;
- `None`, a `dict`, and other non-`ResyncGateRequest` object shapes fail closed as `RESYNC_REQUIRED / malformed_input` instead of raising;
- non-boolean signal fields fail closed before any malformed value is interpreted as an active boundary.

These tests exercise only a pure/local classifier over caller-supplied material-boundary metadata. They do not prove that the surrounding system detected a real boundary correctly, fetched canonical state, performed a re-sync, or wrote anything back. `RESYNC_REQUIRED` / `NOT_REQUIRED` are classification outcomes only.

### Writeback Gate authority boundary

```bash
python tests/test_writeback_gate.py
```

The suite contains **15 tests**. It covers the step 6 boundary described in [`WRITEBACK_GATE.md`](WRITEBACK_GATE.md), including:

- important `USER_CONFIRMED` input at `ACTIVE` / `LOCKED` can become a local `WRITEBACK_CANDIDATE`;
- important `AI_PROPOSAL` input can become a candidate only at `PROPOSED`;
- `AI_PROPOSAL` requesting `ACTIVE` / `LOCKED` fails closed as `REVIEW_REQUIRED`, regardless of importance;
- well-formed non-important input returns `NOT_REQUIRED`;
- `None`, `dict`, unknown origin/status values, and non-boolean importance fail closed as `REVIEW_REQUIRED / malformed_input` without raising.

These tests prove only the local classification contract. They do not prove that a real user confirmation occurred, that importance was classified correctly, that any record was persisted, or that an authoritative status was granted. `WRITEBACK_CANDIDATE` is not write permission.

A syntax/bytecode check is also supported:

```bash
python -m compileall reference runtime tests
```

### Current CI scope

The GitHub Actions workflow in this repository ([`.github/workflows/reference-tests.yml`](../.github/workflows/reference-tests.yml)) invokes the decision resolver, Source Read Gate, Source Read Observation, Source Read Evidence, Context Router preflight, Context Selection, Selective Recall runtime, Work Gate, Re-sync Gate, Writeback Gate, and synthetic lifecycle-integration suites, followed by `python -m compileall reference runtime tests`, on pull requests and pushes.

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

> A resolution-first, selective-recall architecture can be implemented and regression-tested so that old decisions, ambiguous provenance, stale state, unrelated context, conditional safety rules, explicit user-selected source requirements, bounded selected-context loading, explicit material-boundary re-sync classification, and a bounded writeback-candidate authority check are handled instead of being left entirely to implicit model judgment.

## Cross-surface lifecycle integration evidence

The public reference also includes a synthetic, fully in-memory composition suite:

```bash
python tests/test_reference_lifecycle_integration.py
```

It contains two chain-level tests over the existing published interfaces. One carries a Source Read Gate `VERIFY` result through Context Selection and plan-bounded Selective Recall to a fail-closed Work Gate `REVIEW_REQUIRED`. The other carries a synthetic `RESOLVED` decision through Context Selection, Selective Recall, Work Gate `PROCEED`, a caller-supplied material signal producing `RESYNC_REQUIRED`, and the Writeback Gate authority boundary where AI-proposed `ACTIVE` / `LOCKED` requests fail closed and important `USER_CONFIRMED` input remains only a `WRITEBACK_CANDIDATE`.

These tests prove that the already-published pure/local interfaces can compose under those supplied synthetic inputs. They do **not** prove real connector I/O, source provenance, environment detection, production execution, autonomous orchestration, persistence, or permission to act. See [`REFERENCE_LIFECYCLE_INTEGRATION.md`](REFERENCE_LIFECYCLE_INTEGRATION.md) and [`LIMITATIONS.md`](LIMITATIONS.md).
