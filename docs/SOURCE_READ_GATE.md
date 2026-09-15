# Explicit Source Read Gate

## Why this gate exists

External-memory systems can fail even when their stored context is accurate.

A specific failure class occurs when a user explicitly asks an AI to inspect a saved source—such as a repository file, document, or other named source—but the AI answers from conversational memory, a summary, or previously loaded context instead of actually reading the designated source.

That is a **source-grounding failure**.

The problem is not that memory is always wrong. The problem is that the user explicitly selected the evidence that should ground the answer, and the system silently substituted something else.

## Contract

When the user explicitly designates a source, that designation becomes a retrieval requirement.

The source-read gate has priority over the normal `read little` optimization.

### Required behavior

1. **Read before claiming**
   - If the user says to inspect a named repository, file, document, saved post, or other explicit source, the system must actually search/fetch/read that source before making claims presented as grounded in it.

2. **Do not substitute memory**
   - Conversation history, project summaries, cached context, or model memory must not be treated as if the designated source had been read.

3. **Fail closed when the source is unavailable**
   - If the designated source cannot be accessed, found, or read, source-dependent claims remain `VERIFY` or `UNKNOWN` rather than being reconstructed from memory.

4. **Preserve bounded retrieval**
   - An explicit source read is not a reason to sweep unrelated archives or COLD history. Read the designated source and only the additional directly relevant context needed to resolve the task.

5. **Carry source designation through continuation**
   - When a source was explicitly designated in the immediately preceding turn and the same work item continues, that designation remains part of the task unless the user changes it.

6. **Respect AND / OR semantics**
   - If the user requires source A **and** source B, read both when both are necessary.
   - If the user allows source A **or** source B, search minimally until the required evidence is found.

7. **Respect explicit no-external-read constraints**
   - If the user says to use only the current attachment or not to read external sources, do not expand retrieval beyond that constraint.

## Integration with the Context Router

The gate is conditional and sits before source-grounded work:

```text
User Request
    ↓
Explicit source designated?
    ├─ No  → normal resolution / selective recall
    └─ Yes → Source Read Gate
                 ↓
              actual read
                 ↓
          Resolution Kernel
                 ↓
          Context Router
                 ↓
          HOT / WARM / COLD
                 ↓
               Work
```

The gate does **not** mean "read everything." It means "do not replace the source the user explicitly selected with an easier source."

## Resolution states

Typical fail-closed outcomes include:

- `VERIFY` — the source should be checked before a claim can be trusted
- `UNKNOWN` — the required evidence is unavailable or insufficient

A missing explicit source should not be silently converted into a confident answer merely because similar information exists elsewhere.

## Sanitized validation evidence

The larger private implementation added a dedicated 10-scenario regression set covering explicit repository/document reads, multi-source AND/OR behavior, continuation carryover, missing-source handling, and bounded retrieval.

Result: **10/10 PASS**.

A post-sync live dogfood smoke then checked five gates:

- P1 actual source read
- P2 no memory substitution
- P3 fail closed on unavailable evidence
- P4 bounded retrieval
- P5 source-grounded answer

Result: **P1–P5 PASS**.

These are sanitized aggregate results. They do not expose workspace-specific sources, project names, paths, or production configuration.

## Reference implementation

[`reference/source_read_gate.py`](../reference/source_read_gate.py) is a dependency-free, pure/local model of the contract above. Given a declared source requirement and a `read_log` of what was actually read, `evaluate()` returns a deterministic outcome:

- `NOT_APPLICABLE` — no explicit source is in force for this turn
- `PASS` — the requirement is satisfied by `read_log`
- `VERIFY` — required evidence has not been read yet, or an explicit no-external-read constraint blocks the one remaining read that would be needed. Evidence already present in `read_log` still counts even under the constraint: `no_external_read` blocks a *new* prohibited retrieval, it does not retract a read that already happened.
- `UNKNOWN` — the requirement can never be satisfied given `unavailable_sources`. In `mode="ALL"` this means *at least one* required source is unavailable (one missing link breaks the whole requirement); in `mode="ANY"` it means *every* candidate source is unavailable (no candidate remains that could ever satisfy it).
- `DATA_ERROR` — the *effective* request is malformed. Only the source requirement actually in force this turn is validated — a current declaration overriding a continuation, or a continuation whose source changed, is not blocked by stale/invalid data left over in the other (inactive) field set.

The function also models AND/OR semantics (`mode="ALL"` / `mode="ANY"`), continuation carryover across turns, the no-external-read constraint, and surfaces unnecessary reads outside the declared requirement (`extra_reads`) without blocking on them, matching the bounded-retrieval rule.

Run locally:

```bash
python -m unittest discover -s tests -p test_source_read_gate.py
```

Expected result: all tests pass, including the existing `minimal_resolver` regression cases re-run from within that suite.

## Public implementation boundary

The dependency-free Python resolver and the source-read gate model in this repository demonstrate **decision resolution** and **gate-outcome logic**, not external connector I/O.

This document publishes the source-read contract and its validation evidence, but neither the minimal resolver nor `source_read_gate.py` fetches GitHub, Drive, or other external systems. Whether a designated source was actually read is supplied to `evaluate()` by the caller (`read_log`); this module does not perform or verify the read itself, so it does not independently enforce the gate end-to-end.

See also:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`VALIDATION.md`](VALIDATION.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
