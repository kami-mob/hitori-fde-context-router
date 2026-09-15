# Sharing Guide

Use this repository as technical evidence for a **resolution-first Context Router** design for AI external memory, including an explicit-source grounding contract and a pure/local Source Read Gate outcome model.

## One-sentence description

A public reference showing how an AI workflow can honor explicitly designated sources, resolve the current authoritative decision before broader context retrieval, then selectively load HOT / WARM / COLD context.

## Short description

Context Router addresses failure modes that retrieval alone does not solve: external memory may contain old decisions, proposals, future-effective records, stale summaries, and unrelated domains that all look relevant. A separate source-grounding failure also occurs when a user explicitly asks the AI to inspect a saved source but the system answers from conversational memory or summaries instead of actually reading that source.

The design therefore combines an **Explicit Source Read Gate**, a **Resolution Kernel**, and selective recall, using explicit `RESOLVED / UNKNOWN / CONFLICT / VERIFY / DATA_ERROR` outcomes instead of silent guessing.

The public Source Read Gate code is deliberately bounded: it evaluates caller-supplied source/read state and does not itself connect to or fetch from external systems.

## Evidence you may cite

The sanitized public repository contains:

- architecture and decision-resolution specification
- Explicit Source Read Gate contract
- dependency-free minimal Python decision resolver
- dependency-free pure/local Source Read Gate outcome model
- synthetic fixture data
- reproducible decision-resolution reference cases
- a 32-test Source Read Gate unittest suite including resolver regression guards
- GitHub Actions CI for both public reference models
- sanitized aggregate validation results from a larger implementation
- dedicated private/integration source-read regression evidence: 10/10 PASS
- post-sync live dogfood source-read smoke: P1–P5 PASS
- explicit limitations and non-claims

## Accurate claim

> A resolution-first, selective-recall architecture can be implemented and regression-tested so that explicit user-selected source requirements, old decisions, ambiguous provenance, stale state, unrelated context, and conditional safety rules are handled explicitly rather than being left only to implicit model judgment.

For the public Source Read Gate code specifically, an accurate narrower claim is:

> A dependency-free local model can deterministically evaluate declared-source requirements, caller-supplied read evidence, source availability, AND/OR semantics, continuation metadata, and no-external-read constraints without performing external I/O.

## Claims to avoid

Do not describe this repository as proof that:

- all AI hallucinations are prevented
- token or usage cost is guaranteed to decrease
- all models will behave identically
- the public reference code is the complete production implementation
- `source_read_gate.py` itself performs external connector I/O, proves that a real fetch occurred, or enforces the Source Read Gate end-to-end
- every future phrasing of an explicit-source request will be recognized correctly
- every future context structure is covered

## Commercial boundary

This repository provides **Why / What / Evidence**. Complete workspace installation templates, migration packages, operational playbooks, and non-public operational evidence are intentionally maintained separately.
