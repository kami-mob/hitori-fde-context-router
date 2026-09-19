# Limitations and Non-Claims

This public reference is intentionally conservative about what the evidence proves.

## It does not modify model internals

Context Router is an external architecture and operating pattern. It does not install a new reasoning engine inside an AI model and does not override platform safety or product behavior.

## It does not guarantee correctness

Explicit resolution, source-read gates, and fail-closed states reduce some classes of ambiguity, but they do not guarantee that:

- every future request is classified correctly
- every explicit source designation is recognized perfectly
- every external source is complete
- every source connector remains available
- every live system value is current
- every safety condition is detected without suitable metadata or rules
- every caller supplies correct production/permission trigger metadata
- every caller supplies correct material-boundary metadata for re-sync decisions
- every model follows an instruction perfectly

## The public reference code is deliberately bounded

This repository contains thirteen standard-library Python reference surfaces, including one bounded public-network reader; only that reader performs direct network I/O:

- `reference/minimal_resolver.py` demonstrates the **decision-resolution contract**.
- `reference/source_read_gate.py` demonstrates **pure/local Source Read Gate outcome logic** from caller-supplied request metadata and `read_log`.
- `reference/source_read_observation.py` demonstrates **pure/local deterministic value binding** over caller-supplied source identity, version, and exact raw payload bytes. See [`SOURCE_READ_OBSERVATION.md`](SOURCE_READ_OBSERVATION.md).
- `reference/source_read_evidence.py` demonstrates **pure/local immutable hash-only carriage** derived from a fresh Source Read Observation result. See [`SOURCE_READ_EVIDENCE.md`](SOURCE_READ_EVIDENCE.md).
- `reference/source_read_evidence_binding.py` demonstrates **pure/local comparison** of supplied evidence with one fresh internal derivation. See [`SOURCE_READ_EVIDENCE_BINDING.md`](SOURCE_READ_EVIDENCE_BINDING.md).
- `reference/context_router_preflight.py` demonstrates the **pure/local composition** of the two functions above, sequencing them in the conditional order [`ARCHITECTURE.md`](ARCHITECTURE.md) specifies for steps 0 and 1. See [`CONTEXT_ROUTER_PREFLIGHT.md`](CONTEXT_ROUTER_PREFLIGHT.md).
- `reference/context_selection.py` demonstrates **step 2 planning** — deciding which already-scored, already-tiered candidates belong in the HOT/WARM/COLD read plan. See [`CONTEXT_SELECTION.md`](CONTEXT_SELECTION.md).
- `runtime/selective_recall.py` demonstrates the **step 3 runtime boundary** — validating a `SELECTED` plan and invoking only a caller-supplied loader for IDs already present in that plan. See [`SELECTIVE_RECALL_RUNTIME.md`](SELECTIVE_RECALL_RUNTIME.md).
- `reference/work_gate.py` demonstrates the **step 4 safety-independence boundary** — validating a caller-supplied request and classifying the upstream decision state together with explicit production/permission triggers. See [`WORK_GATE.md`](WORK_GATE.md).
- `reference/resync_gate.py` demonstrates the **step 5 material-boundary classifier** — validating caller-supplied re-sync signals and deterministically returning `RESYNC_REQUIRED` / `NOT_REQUIRED`. See [`RESYNC_GATE.md`](RESYNC_GATE.md).
- `reference/writeback_gate.py` demonstrates the **step 6 writeback-candidate classifier** — validating caller-supplied origin/status/importance while blocking AI-proposed `ACTIVE` / `LOCKED` status. See [`WRITEBACK_GATE.md`](WRITEBACK_GATE.md).

The resolver, Source Read Gate, Source Read Observation, Source Read Evidence, Source Read Evidence Binding, preflight, Context Selection, Work Gate, Re-sync Gate, and Writeback Gate surfaces do **not**:

- connect to external repositories or document stores
- fetch a user-designated document
- independently verify that an external source was actually read
- detect every product-level continuation/source designation automatically
- enforce the Source Read Gate end-to-end at the connector or product integration layer
- score, classify, or determine relevance of any candidate context on their own
- discover production/permission safety conditions from the environment on their own
- detect every material re-sync boundary from the conversation or environment on their own
- fetch canonical current state or perform writeback on their own
- promote an AI proposal to `ACTIVE` / `LOCKED`, persist a candidate, or create authoritative write permission

`source_read_gate.py` can model continuation, source availability, AND/OR requirements, and no-external-read constraints when those facts are supplied by the caller. It does not discover or prove those facts itself.

`source_read_observation.py` binds only values the caller already supplied. Its source identity hash, source-version binding hash, and raw-payload hash do not prove that an external read occurred, that the named source produced those bytes, or that the source is authentic, fresh, authorized, complete, or otherwise trustworthy. The module deliberately performs no connector selection, authentication, network/filesystem I/O, permission lookup, clock read, persistence, or normalization of raw payload bytes. Its UTF-8 check exists only to keep malformed text fail-closed before hashing.

`source_read_evidence.py` adds no new provenance or trust semantics. It invokes `observe()` freshly and freezes only `source_id` plus the three resulting hashes when the observation succeeds. It excludes raw payload bytes and the raw source-version string and accepts no caller-supplied precomputed hash. An `EVIDENCED` result is not proof of a real read and is not a Source Read Gate `PASS`; this module never evaluates the gate.

`source_read_evidence_binding.py` checks only local equality of caller-supplied evidence and evidence freshly re-derived from a caller-supplied observation request. Its exact-type and safe-read guards can return generic `DATA_ERROR` for malformed, stale or forged in-memory records, but they do not prove that anyone fetched the stated external source or that its identity, contents, authorization, timeliness, completeness or provenance were authentic. A `BINDING_MATCHED` result is neither Source Read Gate `PASS` nor permission to act. The module cannot read from connectors or access a production environment, and its 20 passing synthetic tests are not end-to-end operational validation.

`context_router_preflight.py` adds no behavior beyond sequencing the two composed
functions: it introduces no I/O, retrieval, external model invocation, agentic execution,
HOT/WARM/COLD loading, or production runtime, and it does not change either composed
function's own contract or test coverage. A `PASS` from the composition's gate stage is
not proof that an external read happened; that evidence is still supplied by the caller
via `read_log`, exactly as in `source_read_gate.py` alone.

`context_selection.py` can only be as accurate as the relevance scoring, tier
assignment, and condition/explicit-source flags the caller supplies for each
candidate; it does not itself judge what is relevant, what tier something belongs
in, or whether an explicit source designation is genuine. It decides what a step 2
plan should contain; it does not itself load, fetch, or retrieve any selected content.

`runtime/selective_recall.py` is intentionally one layer narrower than a connector or
retrieval system. It calls only the caller-supplied `loader(candidate_id)` for IDs already
present in a validated plan, but it does not choose a connector, authenticate a source,
verify source provenance, judge loader correctness, or independently prove that an
external read occurred. Any actual filesystem/network/connector I/O is implemented by
the caller's loader. Loader behavior therefore remains part of the surrounding product
boundary, including timeout policy, authentication, source identity, and secret-safe
error handling. The reference records `str(exception)` for a failed loader call; callers
must not place credentials or other sensitive material in loader exception messages that
may be propagated in the returned failure mapping.

`reference/work_gate.py` is likewise a local classification boundary, not a detector or executor. It trusts the caller to supply the upstream `decision_state`, `production_trigger`, and `permission_trigger` values. It can fail closed on malformed request shape and can preserve the independence of an explicitly supplied safety trigger, but it cannot prove that a real production/permission condition was detected upstream. Its `PROCEED` result means only that the supplied decision state is `RESOLVED` and neither supplied trigger is active; it does not grant permission to execute work, mutate production or permissions, merge code, or bypass any surrounding governance.

`reference/resync_gate.py` is also a local classification boundary. It trusts the caller to supply nine material-boundary booleans. It can fail closed on malformed request shape or field types and can deterministically report every supplied active signal, but it cannot prove that a real current/latest, continuation, implementation, publication, production, permission, price/spec/version, or explicit-source-continuation boundary was detected correctly. Its `RESYNC_REQUIRED` result does not perform or authorize retrieval or writeback, and `NOT_REQUIRED` does not prove that the caller omitted no real boundary.

`reference/writeback_gate.py` is likewise only a classifier. It trusts the caller to label origin, requested status, and importance correctly. It can block the explicit `AI_PROPOSAL -> ACTIVE/LOCKED` path and fail closed on malformed input, but it cannot independently prove that a user really confirmed a decision, determine whether content is important, persist a record, validate a storage destination, or grant authority to write. `WRITEBACK_CANDIDATE` is therefore not evidence that a write occurred or that an authoritative status is valid.

The Explicit Source Read Gate described in [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md) is therefore both a public behavioral contract and a small reproducible decision model, but it is not a complete retrieval or connector implementation. The Selective Recall runtime similarly demonstrates a bounded execution boundary without turning this repository into a complete production retrieval stack. The Work Gate demonstrates safety-independent classification without becoming a production authorization system. The Re-sync Gate demonstrates material-boundary classification without becoming a canonical-state retrieval or writeback engine. The Writeback Gate demonstrates an authority-sensitive candidate boundary without becoming a persistence or approval system.

## Adapter-fed local gate and public HTTPS reader boundary

The public acquisition handoff accepts a **caller-selected adapter** and
locally verifies a receipt before recording the declared source for the
existing in-memory Source Read Gate model. Its `PASS` label
`CALLER_SUPPLIED_ADAPTER` is not independent evidence that the callback
performed a real read, that the source was authentic or fresh, or that the
caller had access permission. Fabricated but internally consistent values
can pass local comparison. Connector authentication, permission validation,
revision trust, audit trails and downstream operational decisions remain
outside this reference.

The narrow pinned public GitHub reader is the only published reference
surface here that can perform a network request. It performs one read-only
public Contents API GET with a fixed HTTPS host, explicit path allowlist
and immutable commit; it does not accept a token or provide private access,
mutations or broader integration. One isolated, opt-in public GET was
observed successfully; routine CI uses mock HTTP and cannot establish
continuous network availability. The reader does not establish that
any evolving branch is currently up to date, that a user has private source
access, or that an actual M365/Salesforce/other enterprise connector is
configured. Its public response integrity checks are not a production
provenance or authorization attestation.

A local gate result from this experimental chain is not a product-level
approval, a complete real-source grounding guarantee or evidence that
STELLIGARE as a whole is deployed or suitable for unsupervised production.

## Same-file public read-to-decision reference is not execution authority

The optional pinned public snapshot preflight binds a local decision classification to the exact bytes of one explicitly selected public GitHub file and independently expected immutable blob hash, then uses the existing local Binding and Source Read Gate model. The caller still chooses the source, pin and expected digest; a compromised injected test transport cannot be independently attested as genuine by this code. The reference does not establish private repository access, Microsoft 365/Salesforce permissions, freshness of an evolving branch, completeness of a business decision registry, or an authenticated human approval. A single public synthetic HTTPS smoke is not an enterprise connector validation. Its `RESOLVED` is a classification of selected public bytes only, not a trusted product decision, ACTIVE/LOCKED writeback, production action or permission grant. No workflow is triggered or persistent state changed.

## Canonical sources still matter

A resolver can only be as reliable as the records it receives.

If authoritative sources are missing, stale, contradictory, or improperly classified, the correct result may be `UNKNOWN`, `CONFLICT`, `VERIFY`, or `DATA_ERROR` rather than a useful value.

If a user explicitly designates a source and that source is unavailable, a similar record elsewhere should not automatically be treated as equivalent evidence.

Likewise, the Source Read Gate reference model can only evaluate the `read_log` and source-status information it receives. Incorrect caller-supplied evidence can produce an incorrect gate result.

A Selective Recall plan also depends on caller-supplied candidate metadata. If the wrong IDs were selected upstream, the runtime's plan-bounded loading cannot correct that semantic mistake on its own.

A Work Gate result also depends on caller-supplied decision and trigger metadata. If a real safety condition exists but the caller supplies a false trigger value, this pure/local reference cannot discover the omission by itself.

A Re-sync Gate result likewise depends on caller-supplied material-boundary metadata. If a material boundary exists but the caller supplies all signals as false, this pure/local reference cannot discover the omission or force a real canonical read.

## Volatile state requires live verification

Fast-changing operational state should be checked against an appropriate live source when material to the task. A historical context record is not a substitute for live verification.

## Test results are implementation evidence, not universal benchmarks

Reported validation counts demonstrate regression coverage for the tested implementation. They should not be interpreted as:

- a benchmark against other memory systems
- a guaranteed token-cost reduction
- a guaranteed usage-limit reduction
- proof that another implementation will produce identical results
- proof that every future phrasing of an explicit-source request will be routed correctly
- proof that all external source connectors will fail closed identically
- proof that the public pure/local gate model guarantees an external read actually happened
- proof that an arbitrary caller-supplied loader is safe, correct, or source-authentic
- proof that production/permission triggers will always be detected correctly upstream
- proof that a Work Gate `PROCEED` result is execution authority
- proof that all material re-sync boundaries will always be detected correctly upstream
- proof that a Re-sync Gate result itself performs, authorizes, or proves a canonical re-sync
- proof that a Writeback Gate `WRITEBACK_CANDIDATE` result proves user confirmation, performs persistence, or grants authoritative status

## Public examples are synthetic

The public package deliberately removes real company, customer, infrastructure, production, authentication, workspace-specific source, and internal-code details.

This improves safety and portability, but means the public examples are smaller than the operational environment that motivated the design.

## Licensing

No open-source license is declared in this version. Repository visibility and software reuse rights are separate decisions. Licensing should be selected explicitly before third-party reuse is encouraged.

## Cross-surface lifecycle integration non-claim

The synthetic lifecycle integration suite composes the existing public interfaces in two representative in-memory chains. It is evidence about deterministic composition of caller-supplied inputs only. It does not add an orchestrator or production runtime, does not perform external reads, does not verify connector authentication or provenance, does not detect real production/permission/material-boundary conditions, and does not make `PROCEED`, `RESYNC_REQUIRED`, or `WRITEBACK_CANDIDATE` authoritative actions.

An accurate claim is: the published step-0-through-step-6 interfaces can be regression-tested together so that a supplied `VERIFY` state remains fail-closed through work classification and a supplied `RESOLVED` path preserves the documented selection, bounded loading, re-sync classification, and writeback authority boundaries. Do not describe this as end-to-end proof of a real external system or autonomous agent workflow.
