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
4. Work
    ↓
5. Re-sync / Writeback when material
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
above. It does not perform step 3 (Selective Recall), the actual retrieval/loading of
that content once planned; that remains a runtime/product concern outside this
repository. See [`CONTEXT_SELECTION.md`](CONTEXT_SELECTION.md) for the full contract.

## 3. Safety independence

Safety is not a successful-resolution side effect.

A production or permission trigger must still fire when the decision state is `UNKNOWN`, `CONFLICT`, or `VERIFY`.

```text
Resolution state ───────────────┐
                               ├─> Work gate
Production / Permission trigger┘
```

## 4. Long-context re-sync

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

## 5. Writeback

Important confirmed decisions should be persisted outside the transient AI conversation.

Examples:
- selected implementation direction
- current version
- approved price
- next action
- superseded decision relationship
- implementation status

The AI may propose a writeback, but proposal status must not be silently promoted to authoritative status.
