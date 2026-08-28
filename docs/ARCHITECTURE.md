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

## Architecture

```text
User Request
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
