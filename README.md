# hitori-fde-context-router

[![Reference Resolver Tests](https://github.com/kami-mob/hitori-fde-context-router/actions/workflows/reference-tests.yml/badge.svg)](https://github.com/kami-mob/hitori-fde-context-router/actions/workflows/reference-tests.yml)

**Save a lot, read little, resolve correctly, re-sync when it matters.**

A sanitized public reference implementation and validation record for a **resolution-first Context Router** for AI external memory.

## 日本語で60秒

AIの外に記録を増やしても、それだけでは「今どの判断が有効か」を正しく選べるとは限りません。

古い判断、未確定案、将来発効の方針、別subjectの似た情報が同時に存在すると、検索で関連情報を見つけても current decision を取り違えることがあります。

さらに、ユーザーが「このGitHubファイルを見て」「この保存済み資料を読んで」と明示しているのに、AIが会話要約や内部Memoryだけで答えると、**指定された根拠を実際には読んでいない**という別のsource-grounding failureが起こります。

このreferenceでは、明示Sourceがある場合は **Explicit Source Read Gate** を先に通し、その後に **Resolution Kernel** と **Context Router** を使います。

```text
User Request
    ↓
Explicit Source Read Gate (when designated)
    ↓
Resolution Kernel
    ↓
Context Router
    ↓
HOT / WARM / COLD
    ↓
Work
```

通常は必要なContextだけを読みます。ただしユーザーがSourceを明示した場合、そのSourceの実読を`read little`の名目で省略しません。

最小Python実装、synthetic data、再現可能な7ケースのテスト、GitHub Actions CI、より大きなprivate実装で得た匿名化済みaggregate validation、Source Read Gateの公開contract、そしてlimitationsを公開しています。

日本語の補足は [`docs/FAQ_JA.md`](docs/FAQ_JA.md) を参照してください。

---

## If you have 60 seconds

1. Read the architecture below.
2. See [`docs/SOURCE_READ_GATE.md`](docs/SOURCE_READ_GATE.md) for the explicit-source grounding contract.
3. See [`docs/DECISION_RESOLUTION_SPEC.md`](docs/DECISION_RESOLUTION_SPEC.md) for the resolution contract.
4. Run `python tests/test_resolver.py` to reproduce the public 7/7 reference tests.
5. Read [`docs/VALIDATION.md`](docs/VALIDATION.md) for sanitized evidence from the larger private implementation.
6. Read [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) before interpreting the results.

## Problem

External memory can contain:

- old and new decisions at the same time
- proposals that were never approved
- future-effective decisions
- different subjects with similar values
- stale state files
- unrelated domains
- high-risk rules that should only be read when triggered
- explicit user-selected sources that must not be replaced by conversational memory or summaries

Selective recall alone is not enough. An AI can retrieve relevant-looking information and still choose the wrong current decision. It can also answer from convenient prior context even when the user explicitly asked it to inspect a particular saved source.

## Architecture

```text
User Request
    ↓
Explicit Source Read Gate (conditional)
    ↓
Resolution Kernel
    ↓
Context Router
    ↓
HOT / WARM / COLD
    ↓
Work
```

When an explicit source is designated, the Source Read Gate requires actual read/fetch before source-grounded claims and blocks memory substitution if that source is unavailable.

Before broad retrieval, the Resolution Kernel identifies:

1. domain / project
2. subject / entity
3. field / decision point
4. authoritative status
5. effective timing
6. supersession relations
7. relation integrity
8. unique survivor / provenance
9. selected-record freshness
10. independent safety triggers

## Core resolution rule

```text
0 authoritative survivors  -> UNKNOWN
1 authoritative survivor   -> freshness evaluation
2+ authoritative survivors -> CONFLICT
```

`PROPOSED` and `HYPOTHESIS` records are never promoted to the current decision automatically.

For explicit-source failures, unavailable or unreadable required evidence should remain `VERIFY` / `UNKNOWN` rather than being silently reconstructed from memory.

## Public scope

This repository contains only generalized specifications, synthetic examples, and a minimal reference implementation.

It intentionally does **not** contain:

- real company or customer data
- employee names
- internal paths or infrastructure identifiers
- production configuration
- credentials or tokens
- real Salesforce / Power Automate definitions
- internal source code
- private decision records
- production backups

## Repository boundary

This public repository focuses on **Why / What / Evidence**.

Operational templates, workspace-specific installation materials, migration packages, and private production evidence are maintained separately.

## Contents

- `docs/ARCHITECTURE.md` — architecture and routing model
- `docs/SOURCE_READ_GATE.md` — explicit-source grounding contract
- `docs/DECISION_RESOLUTION_SPEC.md` — current-decision resolution rules
- `docs/VALIDATION.md` — validation methodology and sanitized results
- `docs/LIMITATIONS.md` — what the evidence does and does not prove
- `docs/SHARING_GUIDE.md` — wording for referencing this work accurately
- `docs/FAQ_JA.md` — Japanese FAQ / first-reader guide
- `reference/minimal_resolver.py` — dependency-free minimal resolver
- `reference/sample_decisions.json` — synthetic decision records
- `tests/test_resolver.py` — deterministic reference tests
- `.github/workflows/reference-tests.yml` — CI for the public reference
- `PUBLICATION_CHECKLIST.md` — publication safety boundary

## Evidence summary

Private/internal implementations were validated separately before this sanitized reference was prepared. Sanitized aggregate results include:

- ChatGPT Context OS deterministic tests: **127/127 PASS**
- ChatGPT Context OS property tests: **3,200/3,200 PASS**
- semantic consistency: **PASS**
- Explicit Source Read Gate dedicated regression: **10/10 PASS**
- Explicit Source Read Gate live dogfood smoke: **P1–P5 PASS**
- Codex Context Router shadow deterministic tests: **29/29 PASS**
- Codex Context Router property tests: **85,000/85,000 PASS**
- limited Pilot 01 internal execution: **PASS**
- scripted operation observation: **10/10 PASS**
- false VERIFY / false CONFLICT / stale revival / safety miss / COLD broad read: **0** in that observation window

These are aggregate validation results, not a claim that every future environment will behave identically.

## Reference implementation

The code in this repository is intentionally small. It demonstrates the decision-resolution contract, not the complete private production system.

The public Python resolver does **not** perform external connector I/O and does not independently enforce the Source Read Gate. The gate is published here as an architecture/operating contract with sanitized validation evidence.

Run locally:

```bash
python tests/test_resolver.py
```

Expected result:

```text
7/7 PASS
```

## Status

Public reference v0.1.

No license is declared yet. Until a license is added, standard copyright applies; public visibility does not itself grant reuse rights.
