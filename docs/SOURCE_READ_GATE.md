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

## Public implementation boundary

The dependency-free Python resolver in this repository demonstrates **decision resolution**, not external connector I/O.

This document publishes the source-read contract and its validation evidence, but the public minimal resolver does not fetch GitHub, Drive, or other external systems and therefore does not independently enforce this gate.

See also:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`VALIDATION.md`](VALIDATION.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
