# Sharing Guide

Use this repository as technical evidence for a **resolution-first Context Router** design for AI external memory, including an explicit-source grounding contract.

## One-sentence description

A public reference showing how an AI workflow can honor explicitly designated sources, resolve the current authoritative decision before broader context retrieval, then selectively load HOT / WARM / COLD context.

## Short description

Context Router addresses failure modes that retrieval alone does not solve: external memory may contain old decisions, proposals, future-effective records, stale summaries, and unrelated domains that all look relevant. A separate source-grounding failure also occurs when a user explicitly asks the AI to inspect a saved source but the system answers from conversational memory or summaries instead of actually reading that source.

The design therefore combines an **Explicit Source Read Gate**, a **Resolution Kernel**, and selective recall, using explicit `RESOLVED / UNKNOWN / CONFLICT / VERIFY / DATA_ERROR` outcomes instead of silent guessing.

## Evidence you may cite

The sanitized public repository contains:

- architecture and decision-resolution specification
- Explicit Source Read Gate contract
- dependency-free minimal Python decision resolver
- synthetic fixture data
- reproducible 7/7 public reference tests
- GitHub Actions CI
- sanitized aggregate validation results from a larger implementation
- dedicated source-read regression evidence: 10/10 PASS
- post-sync live dogfood source-read smoke: P1–P5 PASS
- explicit limitations and non-claims

## Accurate claim

> A resolution-first, selective-recall architecture can be implemented and regression-tested so that explicit user-selected source requirements, old decisions, ambiguous provenance, stale state, unrelated context, and conditional safety rules are handled explicitly rather than being left only to implicit model judgment.

## Claims to avoid

Do not describe this repository as proof that:

- all AI hallucinations are prevented
- token or usage cost is guaranteed to decrease
- all models will behave identically
- the public minimal resolver is the complete production implementation
- the public minimal resolver itself performs external connector I/O or enforces the Source Read Gate
- every future phrasing of an explicit-source request will be recognized correctly
- every future context structure is covered

## Commercial boundary

This repository provides **Why / What / Evidence**. Complete workspace installation templates, migration packages, operational playbooks, and non-public operational evidence are intentionally maintained separately.
