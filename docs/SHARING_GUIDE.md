# Sharing Guide

Use this repository as technical evidence for a **resolution-first Context Router** design for AI external memory, including an explicit-source grounding contract, a pure/local Source Read Observation value-binding boundary, a pure/local Source Read Evidence hash-only carriage boundary, bounded selective recall, a pure/local Work Gate for safety-independent classification, a pure/local Re-sync Gate for material-boundary classification, and a pure/local Writeback Gate for authority-sensitive writeback-candidate classification.

## One-sentence description

A public reference showing how an AI workflow can honor explicitly designated sources, resolve the current authoritative decision before broader context retrieval, selectively load HOT / WARM / COLD context, evaluate explicit production/permission triggers independently of decision success, classify when a material boundary requires canonical re-sync, and classify important writeback candidates without letting AI proposals silently become authoritative.

## Short description

Context Router addresses failure modes that retrieval alone does not solve: external memory may contain old decisions, proposals, future-effective records, stale summaries, and unrelated domains that all look relevant. A separate source-grounding failure also occurs when a user explicitly asks the AI to inspect a saved source but the system answers from conversational memory or summaries instead of actually reading that source.

The design therefore combines an **Explicit Source Read Gate**, a **Resolution Kernel**, selective recall, a **Work Gate**, a **Re-sync Gate**, and a **Writeback Gate**, using explicit `RESOLVED / UNKNOWN / CONFLICT / VERIFY / DATA_ERROR` outcomes plus explicit re-sync and writeback-candidate classification instead of silent guessing.

The public Source Read Gate code is deliberately bounded: it evaluates caller-supplied source/read state and does not itself connect to or fetch from external systems. The Source Read Observation surface is also deliberately bounded: it validates and hashes caller-supplied source identity/version/raw bytes, but does not prove a real read, source authenticity, freshness, authorization, completeness, or external provenance. Source Read Evidence only freezes a fresh observation result into a hash-only record; it does not prove a real read and does not satisfy the Source Read Gate. The Selective Recall runtime loads only an already-selected plan through a caller-supplied loader. The public Work Gate is also deliberately bounded: it classifies a caller-supplied decision state together with explicit production/permission trigger booleans, and does not detect those conditions, execute work, or grant authority itself. The public Re-sync Gate similarly classifies caller-supplied material-boundary booleans; it does not detect those boundaries itself, fetch canonical state, perform writeback, invoke tools, or grant authority. The public Writeback Gate classifies caller-supplied origin/status/importance, blocks AI-proposed `ACTIVE` / `LOCKED` status, and does not persist records, infer confirmation, or grant authority.

## Evidence you may cite

The sanitized public repository contains:

- architecture and decision-resolution specification
- Explicit Source Read Gate contract
- dependency-free minimal Python decision resolver
- dependency-free pure/local Source Read Gate outcome model
- dependency-free pure/local Source Read Observation value-binding model
- dependency-free pure/local Source Read Evidence hash-only carriage model
- pure/local Context Router preflight composition
- dependency-free Context Selection planner
- bounded Selective Recall runtime boundary
- dependency-free pure/local Work Gate safety-independence classifier
- dependency-free pure/local Re-sync Gate material-boundary classifier
- dependency-free pure/local Writeback Gate authority-boundary classifier
- synthetic fixture data
- reproducible public suites for resolver, Source Read Gate, Source Read Observation, Source Read Evidence, preflight, Context Selection, Selective Recall, Work Gate, Re-sync Gate, Writeback Gate, and synthetic lifecycle integration
- GitHub Actions CI for all published public reference suites plus compileall
- sanitized aggregate validation results from a larger implementation
- dedicated private/integration source-read regression evidence: 10/10 PASS
- post-sync live dogfood source-read smoke: P1–P5 PASS
- explicit limitations and non-claims

## Accurate claim

> A resolution-first, selective-recall architecture can be implemented and regression-tested so that explicit user-selected source requirements, old decisions, ambiguous provenance, stale state, unrelated context, conditional safety rules, material re-sync boundaries, and writeback authority boundaries are handled explicitly rather than being left only to implicit model judgment.

For the public Source Read Gate code specifically, an accurate narrower claim is:

> A dependency-free local model can deterministically evaluate declared-source requirements, caller-supplied read evidence, source availability, AND/OR semantics, continuation metadata, and no-external-read constraints without performing external I/O.

For the public Source Read Observation code specifically, an accurate narrower claim is:

> A dependency-free local model can fail closed on malformed caller-supplied source metadata and deterministically bind source identity, source version, and exact raw payload bytes into SHA-256 values without performing external I/O or claiming authenticity, freshness, authorization, completeness, or provenance.

For the public Source Read Evidence code specifically, an accurate narrower claim is:

> A dependency-free local model can derive immutable hash-only evidence from a fresh Source Read Observation result without re-exposing raw payload bytes or the raw source-version string, while making no claim that a real read occurred or that the Source Read Gate is satisfied.

For the public Work Gate code specifically, an accurate narrower claim is:

> A dependency-free local classifier can fail closed on malformed request objects and keep explicitly supplied production/permission triggers independent of upstream decision success without executing work or creating authority.

For the public Re-sync Gate code specifically, an accurate narrower claim is:

> A dependency-free local classifier can fail closed on malformed request objects or field types and deterministically classify caller-supplied material-boundary signals as `RESYNC_REQUIRED` or `NOT_REQUIRED` without retrieving canonical state, performing writeback, or creating authority.

For the public Writeback Gate code specifically, an accurate narrower claim is:

> A dependency-free local classifier can fail closed on malformed writeback metadata, permit AI-proposed candidates only at `PROPOSED`, and classify important caller-supplied input without persisting records or granting authoritative status.

## Claims to avoid

Do not describe this repository as proof that:

- all AI hallucinations are prevented
- token or usage cost is guaranteed to decrease
- all models will behave identically
- the public reference code is the complete production implementation
- `source_read_gate.py` itself performs external connector I/O, proves that a real fetch occurred, or enforces the Source Read Gate end-to-end
- `source_read_observation.py` proves that supplied bytes came from the named external source, or proves source authenticity, freshness, authorization, completeness, or connector provenance
- `source_read_evidence.py` proves a real source read occurred, establishes authenticity/freshness/authorization/completeness, or makes the Source Read Gate pass
- every future phrasing of an explicit-source request will be recognized correctly
- every future context structure is covered
- `work_gate.py` itself detects production/permission conditions from the environment
- a Work Gate `PROCEED` result grants permission to execute, merge, mutate production, or change permissions
- `resync_gate.py` itself detects every material boundary from conversation/environment state
- a Re-sync Gate result itself performs, authorizes, or proves a canonical re-sync or writeback
- `writeback_gate.py` itself proves user confirmation, persists a record, or makes `WRITEBACK_CANDIDATE` authoritative

## Commercial boundary

This repository provides **Why / What / Evidence**. Complete workspace installation templates, migration packages, operational playbooks, and non-public operational evidence are intentionally maintained separately.

## Cross-surface lifecycle integration wording

Safe wording for the new public evidence:

> The public reference includes synthetic, in-memory chain-level tests showing that its published step-0-through-step-6 interfaces compose under representative fail-closed and resolved inputs.

Keep the limitation attached when relevant: these tests do not prove real connector I/O, production execution, autonomous orchestration, persistence, or authority. Avoid shortening the claim to “end-to-end production validation” or “the full system is proven.”
