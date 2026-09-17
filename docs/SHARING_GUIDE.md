# Sharing Guide

Use this repository as technical evidence for a **resolution-first Context Router** design for AI external memory, including an explicit-source grounding contract, bounded selective recall, a pure/local Work Gate for safety-independent classification, and a pure/local Re-sync Gate for material-boundary classification.

## One-sentence description

A public reference showing how an AI workflow can honor explicitly designated sources, resolve the current authoritative decision before broader context retrieval, selectively load HOT / WARM / COLD context, evaluate explicit production/permission triggers independently of decision success, and classify when a material boundary requires canonical re-sync.

## Short description

Context Router addresses failure modes that retrieval alone does not solve: external memory may contain old decisions, proposals, future-effective records, stale summaries, and unrelated domains that all look relevant. A separate source-grounding failure also occurs when a user explicitly asks the AI to inspect a saved source but the system answers from conversational memory or summaries instead of actually reading that source.

The design therefore combines an **Explicit Source Read Gate**, a **Resolution Kernel**, selective recall, a **Work Gate**, and a **Re-sync Gate**, using explicit `RESOLVED / UNKNOWN / CONFLICT / VERIFY / DATA_ERROR` outcomes and explicit material-boundary classification instead of silent guessing.

The public Source Read Gate code is deliberately bounded: it evaluates caller-supplied source/read state and does not itself connect to or fetch from external systems. The Selective Recall runtime loads only an already-selected plan through a caller-supplied loader. The public Work Gate is also deliberately bounded: it classifies a caller-supplied decision state together with explicit production/permission trigger booleans, and does not detect those conditions, execute work, or grant authority itself. The public Re-sync Gate similarly classifies caller-supplied material-boundary booleans; it does not detect those boundaries itself, fetch canonical state, perform writeback, invoke tools, or grant authority.

## Evidence you may cite

The sanitized public repository contains:

- architecture and decision-resolution specification
- Explicit Source Read Gate contract
- dependency-free minimal Python decision resolver
- dependency-free pure/local Source Read Gate outcome model
- pure/local Context Router preflight composition
- dependency-free Context Selection planner
- bounded Selective Recall runtime boundary
- dependency-free pure/local Work Gate safety-independence classifier
- dependency-free pure/local Re-sync Gate material-boundary classifier
- synthetic fixture data
- reproducible public suites for resolver, Source Read Gate, preflight, Context Selection, Selective Recall, Work Gate, and Re-sync Gate
- GitHub Actions CI for all published public reference suites plus compileall
- sanitized aggregate validation results from a larger implementation
- dedicated private/integration source-read regression evidence: 10/10 PASS
- post-sync live dogfood source-read smoke: P1–P5 PASS
- explicit limitations and non-claims

## Accurate claim

> A resolution-first, selective-recall architecture can be implemented and regression-tested so that explicit user-selected source requirements, old decisions, ambiguous provenance, stale state, unrelated context, conditional safety rules, and material re-sync boundaries are handled explicitly rather than being left only to implicit model judgment.

For the public Source Read Gate code specifically, an accurate narrower claim is:

> A dependency-free local model can deterministically evaluate declared-source requirements, caller-supplied read evidence, source availability, AND/OR semantics, continuation metadata, and no-external-read constraints without performing external I/O.

For the public Work Gate code specifically, an accurate narrower claim is:

> A dependency-free local classifier can fail closed on malformed request objects and keep explicitly supplied production/permission triggers independent of upstream decision success without executing work or creating authority.

For the public Re-sync Gate code specifically, an accurate narrower claim is:

> A dependency-free local classifier can fail closed on malformed request objects or field types and deterministically classify caller-supplied material-boundary signals as `RESYNC_REQUIRED` or `NOT_REQUIRED` without retrieving canonical state, performing writeback, or creating authority.

## Claims to avoid

Do not describe this repository as proof that:

- all AI hallucinations are prevented
- token or usage cost is guaranteed to decrease
- all models will behave identically
- the public reference code is the complete production implementation
- `source_read_gate.py` itself performs external connector I/O, proves that a real fetch occurred, or enforces the Source Read Gate end-to-end
- every future phrasing of an explicit-source request will be recognized correctly
- every future context structure is covered
- `work_gate.py` itself detects production/permission conditions from the environment
- a Work Gate `PROCEED` result grants permission to execute, merge, mutate production, or change permissions
- `resync_gate.py` itself detects every material boundary from conversation/environment state
- a Re-sync Gate result itself performs, authorizes, or proves a canonical re-sync or writeback

## Commercial boundary

This repository provides **Why / What / Evidence**. Complete workspace installation templates, migration packages, operational playbooks, and non-public operational evidence are intentionally maintained separately.
