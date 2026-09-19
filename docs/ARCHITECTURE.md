# Architecture

## Problem

When an AI works with external memory, retrieval quality is only one part of correctness. A relevant record may still be the wrong record to act on.

Typical failure modes include:

- selecting a historical decision as current
- treating a proposal as approved
- applying a future-effective decision too early
- mixing values from different subjects/entities
- reading unrelated domains unnecessarily
- treating a stale state summary as absolute truth
- failing to load safety rules when a risky condition actually applies
- answering from conversational memory or summaries even though the user explicitly requested a specific saved source

## Architecture

```text
User Request
    ↓
0. Explicit Source Read Gate (conditional)
    ↓
1. Resolution Kernel
    ↓
2. Context Router
    ↓
3. Selective Recall
   HOT / WARM / COLD
    ↓
4. Work Gate
   Resolution state + Production / Permission trigger
    ↓
Work
    ↓
5. Re-sync when material
    ↓
6. Writeback candidate classification
```

## 0. Explicit Source Read Gate

When the user explicitly designates a repository, file, document, saved post, or other source, that designation becomes a retrieval requirement.

The system should:

- actually search/fetch/read the designated source before making claims presented as grounded in it
- not substitute conversation history, project summaries, cached context, or model memory as if the source had been read
- return `VERIFY` / `UNKNOWN` for source-dependent claims when the required source cannot be accessed, found, or read
- preserve bounded retrieval instead of expanding into unrelated COLD history
- carry the source designation across continuation turns for the same work item unless the user changes it
- respect AND / OR semantics when multiple sources are specified
- respect explicit constraints such as "use only this attachment" or "do not read external sources"

This gate has priority over the normal `read little` optimization. It does not mean "read everything"; it means the user's explicitly selected evidence must not be silently replaced by a more convenient source.

See [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md) for the full public contract.

### Reference composition of steps 0 and 1

[`reference/context_router_preflight.py`](../reference/context_router_preflight.py) is a pure/local
reference that sequences step 0 and step 1 exactly as specified above: it evaluates the
Source Read Gate first and only calls the Resolution Kernel when the gate reaches `PASS`
(the requirement was satisfied) or `NOT_APPLICABLE` (no explicit source was in force). A
gate outcome of `VERIFY`, `UNKNOWN`, or `DATA_ERROR` is returned unchanged and the resolver
is never invoked, so an unresolved or malformed source-read requirement is never quietly
replaced by a resolver opinion formed without the required evidence. It composes the two
existing functions without adding new I/O, retrieval, or behavior of its own. See
[`CONTEXT_ROUTER_PREFLIGHT.md`](CONTEXT_ROUTER_PREFLIGHT.md) for the full composition
contract.

### Source Read Observation support boundary

[`reference/source_read_observation.py`](../reference/source_read_observation.py) is a separate pure/local support surface beneath the Source Read Gate. It accepts only caller-supplied in-memory `source_id`, `source_version`, and exact raw `bytes`, validates the request fail-closed (including malformed top-level objects and non-UTF-8-encodable text), and returns deterministic SHA-256 bindings for source identity, identity+version, and raw payload.

This surface does **not** perform the external read, choose or authenticate a connector, verify that the named source produced the supplied bytes, check freshness or permissions, establish completeness, or create source authenticity/provenance. An `OBSERVED` result means only that the supplied values passed the local contract and were deterministically bound. See [`SOURCE_READ_OBSERVATION.md`](SOURCE_READ_OBSERVATION.md).

### Source Read Evidence support boundary

[`reference/source_read_evidence.py`](../reference/source_read_evidence.py) is a separate pure/local support surface layered on Source Read Observation. It accepts one caller-supplied `ObservationRequest`, invokes the existing `observe()` function freshly on every call, and only when that result is `OBSERVED` constructs a frozen evidence record containing `source_id` plus the three observation hashes.

The record deliberately excludes raw payload bytes and the raw source-version string. It does not accept caller-supplied precomputed hashes, perform external I/O, authenticate or authorize a source, establish freshness or completeness, or evaluate the Source Read Gate. An `EVIDENCED` result is therefore only immutable hash-only carriage of a local observation result; it is not proof that a real read occurred and is not a Source Read Gate `PASS`. See [`SOURCE_READ_EVIDENCE.md`](SOURCE_READ_EVIDENCE.md).

### Source Read Evidence Binding support boundary

[`reference/source_read_evidence_binding.py`](../reference/source_read_evidence_binding.py)
is a separate pure/local check layered on Source Read Evidence. It accepts one
caller-supplied observation request and an exact `SourceReadEvidence` record,
calls `derive_evidence()` internally once after the supplied evidence passes
strict type/field checks, and compares all four local evidence values against
that fresh derivation. A `BINDING_MATCHED` result means only those values match;
malformed or mismatched inputs yield generic `DATA_ERROR`.

This support layer is **not** another Source Read Gate and does not change
the step-0-through-step-6 routing order. It does not perform a real external
read, authenticate source provenance, check permissions or freshness, or make
a source-read requirement `PASS`. See
[`SOURCE_READ_EVIDENCE_BINDING.md`](SOURCE_READ_EVIDENCE_BINDING.md) for its
exact in-memory API and boundary.

### Bounded adapter-fed acquisition and pinned public read

[`reference/source_read_acquisition_handoff.py`](../reference/source_read_acquisition_handoff.py)
is an optional support composition between an externally selected reader,
local evidence derivation, evidence binding and the Source Read Gate model.
It only invokes an explicitly supplied adapter for declared identifiers,
adds a locally verified receipt to the modeled read log, and exposes a
`PASS` marked `CALLER_SUPPLIED_ADAPTER`. It cannot authenticate the adapter
or independently prove that the named source was fetched or authorized.

[`reference/github_public_pinned_reader.py`](../reference/github_public_pinned_reader.py)
is one narrow read-only HTTP adapter: one file from the public GitHub
Contents API, with a fixed host, allowed path and explicit immutable commit.
A separate public-only opt-in smoke exercised one pinned external GET and
matched the expected Git blob SHA; ordinary CI tests use mocked HTTP.
Neither result grants private repository access or changes the step-0
through step-6 ordering or existing permission/production gates. See
[`SOURCE_READ_ACQUISITION_HANDOFF.md`](SOURCE_READ_ACQUISITION_HANDOFF.md)
and [`GITHUB_PUBLIC_PINNED_READER.md`](GITHUB_PUBLIC_PINNED_READER.md).

### One-source-byte-bound public decision reference

[`reference/pinned_public_decision_preflight.py`](../reference/pinned_public_decision_preflight.py) demonstrates a separate optional read-to-decision path. An independently selected expected Git blob digest must match the exact bytes returned by one explicitly pinned PUBLIC file read. The already-fetched receipt then passes the existing local Binding and Source Read Gate models, after which decision records are parsed ONLY from those same verified bytes and sent to the existing resolver for one declared domain/subject/field/date. The model does not permit an unrelated caller-supplied record list to substitute for the selected source. Its output is a non-authoritative local classification, not a new step, live permission attestation, production trigger, ACTIVE/LOCKED writeback or replacement for current-source freshness checks. See [`PINNED_PUBLIC_DECISION_PREFLIGHT.md`](PINNED_PUBLIC_DECISION_PREFLIGHT.md).

## 1. Resolution Kernel

Resolve the smallest relevant decision scope before broad context retrieval:

1. domain / project
2. subject / entity
3. field / decision point
4. decision status
5. effective timing
6. supersession graph integrity
7. unique survivor / provenance
8. selected-record freshness
9. independent safety triggers

The output is not always a value. Valid outcomes include:

- `RESOLVED`
- `UNKNOWN`
- `CONFLICT`
- `VERIFY`
- `DATA_ERROR`

Fail-closed states are intentional; uncertainty should not be hidden by fallback guessing.

## 2. Context Router

After resolution identifies the scope, the router decides what context is worth reading.

### HOT
Read by default when directly relevant.

Examples:
- current state for the target subject
- active decision record
- immediate handover / restart point

### WARM
Read only when a condition requires it.

Examples:
- production-change rules
- permission-change rules
- migration procedure
- historical rationale

### COLD
Historical or low-probability context. Do not sweep broadly during normal startup.

Examples:
- old archives
- completed migration logs
- unrelated project history

An explicit source read that is directly required by the user's request is not treated as a broad COLD sweep merely because that source would not otherwise be loaded by default.

### Reference planner for step 2

[`reference/context_selection.py`](../reference/context_selection.py) is a pure/local
reference for this step: given a resolution result and a list of candidates the caller
has already scored for relevance and tagged with a HOT/WARM/COLD tier, `select_context`
deterministically decides which of those candidates the rules above select, including
the `explicit_source` and `explicitly_required` carve-outs. This is planning only — it
answers "what should be read next," which is step 2 (Context Router) in the diagram
above. It does not itself load, fetch, or retrieve any selected content. See
[`CONTEXT_SELECTION.md`](CONTEXT_SELECTION.md) for the full contract.

## 3. Selective Recall runtime boundary

[`runtime/selective_recall.py`](../runtime/selective_recall.py) is the separate, dependency-free
reference boundary for carrying out an already-decided step 2 plan.

`load_selected_context(plan_result, loader)`:

- accepts only a well-formed `context_selection` result with `state == "SELECTED"`;
- rejects malformed/non-SELECTED plans with `DATA_ERROR` before the loader is called;
- calls the caller-supplied loader once for each ID already present in `plan`, in plan order;
- does not consult unrelated candidates or expand the plan into additional COLD context;
- records per-ID loader failures without substituting fallback content;
- performs no relevance scoring, connector discovery, external model invocation, or production mutation of its own.

The boundary deliberately does not decide where an ID lives or how it should be fetched. Any
filesystem, repository, document-store, connector, or other I/O is implemented by the caller's
loader. The runtime therefore constrains *which selected IDs may be attempted* without pretending
to prove that a particular external connector or source was used correctly.

See [`SELECTIVE_RECALL_RUNTIME.md`](SELECTIVE_RECALL_RUNTIME.md) for the full contract.

## 4. Safety independence / Work Gate

Safety is not a successful-resolution side effect.

A production or permission trigger must still fire when the decision state is `UNKNOWN`, `CONFLICT`, or `VERIFY`.

```text
Resolution state ───────────────┐
                               ├─> Work Gate
Production / Permission trigger┘
```

[`reference/work_gate.py`](../reference/work_gate.py) is a dependency-free pure/local reference for this boundary. `evaluate(request)` consumes only a caller-supplied decision state plus explicit `production_trigger` and `permission_trigger` booleans.

It follows three fail-closed rules:

- a request that is not a `WorkGateRequest`, or has malformed field types, returns `REVIEW_REQUIRED / malformed_input` rather than raising;
- either safety trigger returns `REVIEW_REQUIRED / safety_trigger` regardless of whether the decision state is already `RESOLVED`;
- when neither trigger fired, only the literal decision state `RESOLVED` returns `PROCEED`; every other state remains `REVIEW_REQUIRED`.

The Work Gate does not detect production or permission conditions itself, execute work, invoke tools, perform I/O, or create authority. In particular, `PROCEED` is only this local classifier's outcome; it is not permission to perform a production, permission, merge, or other governed action.

See [`WORK_GATE.md`](WORK_GATE.md) for the full contract.

## 5. Long-context re-sync

Conversation history is working context, not the final source of truth.

Re-sync to canonical state when the user asks for, or the task reaches, a material boundary such as:

- current / latest status
- continuation of previous work
- important confirmation
- implementation
- publication / release
- production change
- permission change
- price / specification / version change
- continuation of a task that explicitly designated a saved source

### Reference classifier for step 5

[`reference/resync_gate.py`](../reference/resync_gate.py) is a dependency-free pure/local reference for this boundary. `evaluate(request)` consumes nine caller-supplied booleans corresponding 1:1 to the material-boundary signals above.

It follows three bounded rules:

- a request that is not a `ResyncGateRequest`, or has any non-boolean signal field, fails closed as `RESYNC_REQUIRED / malformed_input` rather than raising;
- any active material-boundary signal returns `RESYNC_REQUIRED / material_boundary`, with every active signal reported deterministically;
- only a well-formed request with no active signal returns `NOT_REQUIRED`.

The Re-sync Gate does not detect those conditions itself, fetch canonical state, perform retrieval, write back records, invoke tools, or create authority. `RESYNC_REQUIRED` and `NOT_REQUIRED` are classification outcomes only; the surrounding system still decides how and whether to perform a canonical re-sync under its own source, safety, and authority rules.

See [`RESYNC_GATE.md`](RESYNC_GATE.md) for the full contract.

## 6. Writeback

Important confirmed decisions should be persisted outside the transient AI conversation.

Examples:
- selected implementation direction
- current version
- approved price
- next action
- superseded decision relationship
- implementation status

The AI may propose a writeback, but proposal status must not be silently promoted to authoritative status.

### Reference classifier for step 6

[`reference/writeback_gate.py`](../reference/writeback_gate.py) is a dependency-free pure/local classifier for this boundary. The caller supplies `origin` (`USER_CONFIRMED` / `AI_PROPOSAL`), `requested_status` (`PROPOSED` / `ACTIVE` / `LOCKED`), and an explicit `important` boolean.

- malformed request objects, invalid enum values, or non-boolean `important` fail closed as `REVIEW_REQUIRED / malformed_input`;
- an `AI_PROPOSAL` may produce a candidate only at `PROPOSED`; `ACTIVE` / `LOCKED` requests fail closed as `REVIEW_REQUIRED / ai_proposal_authoritative_status`;
- important well-formed input that passes that authority boundary returns `WRITEBACK_CANDIDATE`; non-important input returns `NOT_REQUIRED`.

The Writeback Gate performs no persistence, external I/O, mutation, status promotion, or authority creation. `WRITEBACK_CANDIDATE` is not an authoritative record and does not itself authorize any write. See [`WRITEBACK_GATE.md`](WRITEBACK_GATE.md) for the full contract.
