# hitori-fde-context-router

[![Reference Tests](https://github.com/kami-mob/hitori-fde-context-router/actions/workflows/reference-tests.yml/badge.svg)](https://github.com/kami-mob/hitori-fde-context-router/actions/workflows/reference-tests.yml)

**Save a lot, read little, resolve correctly, re-sync when it matters.**

A sanitized public reference implementation and validation record for a **resolution-first Context Router** for AI external memory.

## 日本語で60秒

AIの外に記録を増やしても、それだけでは「今どの判断が有効か」を正しく選べるとは限りません。

古い判断、未確定案、将来発効の方針、別subjectの似た情報が同時に存在すると、検索で関連情報を見つけても current decision を取り違えることがあります。

さらに、ユーザーが「このGitHubファイルを見て」「この保存済み資料を読んで」と明示しているのに、AIが会話要約や内部Memoryだけで答えると、**指定された根拠を実際には読んでいない**という別のsource-grounding failureが起こります。

このreferenceでは、明示Sourceがある場合は **Explicit Source Read Gate** を先に通し、その後に **Resolution Kernel**、**Context Router**、**Selective Recall**、**Work Gate** を分離して扱います。

```text
User Request
    ↓
Explicit Source Read Gate (when designated)
    ↓
Resolution Kernel
    ↓
Context Router (selection plan)
    ↓
Selective Recall (load only the plan)
    ↓
Work Gate (decision state + Production / Permission triggers)
    ↓
Work
```

通常は必要なContextだけを読みます。ただしユーザーがSourceを明示した場合、そのSourceの実読を`read little`の名目で省略しません。

このpublic referenceでは、decision resolution、Explicit Source Read Gate、steps 0–1のpreflight、HOT/WARM/COLDのselection planning、**選択済みplanだけをcaller-supplied loaderへ渡す最小Selective Recall runtime boundary**に加えて、**caller-supplied decision stateとProduction / Permission triggerを独立に評価するpure/local Work Gate**を公開しています。Work Gateの`PROCEED`は分類結果であり、それ自体が実行権限を与えるものではありません。

日本語の補足は [`docs/FAQ_JA.md`](docs/FAQ_JA.md) を参照してください。

---

## If you have 60 seconds

1. Read the architecture below.
2. See [`docs/SOURCE_READ_GATE.md`](docs/SOURCE_READ_GATE.md) for the explicit-source grounding contract.
3. See [`docs/DECISION_RESOLUTION_SPEC.md`](docs/DECISION_RESOLUTION_SPEC.md) for the resolution contract.
4. See [`docs/CONTEXT_SELECTION.md`](docs/CONTEXT_SELECTION.md) for the step 2 Context Router planning reference, then [`docs/SELECTIVE_RECALL_RUNTIME.md`](docs/SELECTIVE_RECALL_RUNTIME.md) for the bounded step 3 loading boundary, and [`docs/WORK_GATE.md`](docs/WORK_GATE.md) for the step 4 safety-independence boundary.
5. Run the reference suites: `python tests/test_resolver.py`, `python -m unittest discover -s tests -p test_source_read_gate.py`, `python tests/test_context_router_preflight.py`, `python tests/test_context_selection.py`, `python tests/test_selective_recall_runtime.py`, and `python tests/test_work_gate.py`.
6. Read [`docs/VALIDATION.md`](docs/VALIDATION.md) for public reproducible checks and sanitized evidence from the larger private implementation.
7. Read [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) before interpreting the results.

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
Context Router (selection plan)
    ↓
Selective Recall (caller-supplied loader)
    ↓
Work Gate (safety independence)
    ↓
Work
```

When an explicit source is designated, the Source Read Gate requires actual read/fetch before source-grounded claims and blocks memory substitution if that source is unavailable. The public `source_read_gate.py` models the decision logic around this contract; it does not itself perform the external read.

After the Resolution Kernel, the Context Router's step 2 decides which HOT / WARM / COLD candidates belong in the read plan. [`reference/context_selection.py`](reference/context_selection.py) is a pure/local reference for that planning step: given already-scored, already-tiered candidates, it deterministically decides which of them are selected. [`runtime/selective_recall.py`](runtime/selective_recall.py) is the separate step 3 boundary: it validates a `SELECTED` plan and invokes only a caller-supplied loader for the IDs already present in that plan, in plan order. It does not score relevance, discover connectors, expand into unrelated COLD context, invoke an external model, or perform production mutation. See [`docs/CONTEXT_SELECTION.md`](docs/CONTEXT_SELECTION.md) and [`docs/SELECTIVE_RECALL_RUNTIME.md`](docs/SELECTIVE_RECALL_RUNTIME.md).

[`reference/work_gate.py`](reference/work_gate.py) is the separate step 4 safety-independence boundary. Given a caller-supplied upstream decision state plus explicit production and permission trigger booleans, it fails closed on malformed input, forces `REVIEW_REQUIRED` when either trigger is active regardless of decision success, and returns `PROCEED` only for literal `RESOLVED` with no active trigger. It performs no I/O or work execution and does not create authority. See [`docs/WORK_GATE.md`](docs/WORK_GATE.md).

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

This repository contains only generalized specifications, synthetic examples, and minimal reference implementations.

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
- `docs/SOURCE_READ_GATE.md` — explicit-source grounding contract and pure/local gate model
- `docs/DECISION_RESOLUTION_SPEC.md` — current-decision resolution rules
- `docs/CONTEXT_ROUTER_PREFLIGHT.md` — pure/local composition of the gate and the resolver (steps 0–1)
- `docs/CONTEXT_SELECTION.md` — pure/local Context Router planning reference (step 2)
- `docs/SELECTIVE_RECALL_RUNTIME.md` — bounded Selective Recall runtime contract (step 3)
- `docs/WORK_GATE.md` — pure/local Work Gate contract for safety independence (step 4)
- `docs/VALIDATION.md` — validation methodology and sanitized results
- `docs/LIMITATIONS.md` — what the evidence does and does not prove
- `docs/SHARING_GUIDE.md` — wording for referencing this work accurately
- `docs/FAQ_JA.md` — Japanese FAQ / first-reader guide
- `reference/minimal_resolver.py` — dependency-free minimal decision resolver
- `reference/source_read_gate.py` — dependency-free Source Read Gate outcome model; no external I/O
- `reference/context_router_preflight.py` — pure/local composition sequencing `source_read_gate.evaluate` then `minimal_resolver.resolve_current`; no new I/O or behavior
- `reference/context_selection.py` — dependency-free Context Router step 2 planner over caller-scored, caller-tiered candidates
- `runtime/selective_recall.py` — dependency-free step 3 boundary that executes only a validated selection plan through a caller-supplied loader
- `reference/work_gate.py` — dependency-free step 4 classifier over a caller-supplied decision state and explicit safety triggers
- `reference/sample_decisions.json` — synthetic decision records
- `tests/test_resolver.py` — deterministic decision-resolution reference cases
- `tests/test_source_read_gate.py` — Source Read Gate suite including resolver regression guards
- `tests/test_context_router_preflight.py` — composition boundary tests for the gate-then-resolver sequencing
- `tests/test_context_selection.py` — Context Selection planner tests (HOT/WARM/COLD selection rules and carve-outs)
- `tests/test_selective_recall_runtime.py` — Selective Recall plan-validation / bounded-loading tests
- `tests/test_work_gate.py` — Work Gate fail-closed and safety-independence tests
- `.github/workflows/reference-tests.yml` — CI for all public Python reference suites plus compileall
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

These are aggregate validation results from larger private/integration layers, not a claim that every future environment will behave identically.

## Reference implementation

The code in this repository is intentionally small.

- `reference/minimal_resolver.py` demonstrates the decision-resolution contract.
- `reference/source_read_gate.py` demonstrates pure/local Source Read Gate outcome logic from caller-supplied request metadata and `read_log`.
- `reference/context_router_preflight.py` demonstrates the conditional sequencing from [`ARCHITECTURE.md`](docs/ARCHITECTURE.md): it composes the two functions above, calling the resolver only when the gate reaches `PASS` or `NOT_APPLICABLE`, and otherwise returning the gate's own fail-closed outcome unchanged. See [`docs/CONTEXT_ROUTER_PREFLIGHT.md`](docs/CONTEXT_ROUTER_PREFLIGHT.md).
- `reference/context_selection.py` demonstrates the Context Router's step 2 planning logic: given a resolution result and caller-supplied, already-scored, already-tiered candidates, it decides which HOT / WARM / COLD candidates are selected. See [`docs/CONTEXT_SELECTION.md`](docs/CONTEXT_SELECTION.md).
- `runtime/selective_recall.py` demonstrates the step 3 execution boundary: it validates the selection result, then invokes the caller-supplied loader only for IDs already present in the plan. See [`docs/SELECTIVE_RECALL_RUNTIME.md`](docs/SELECTIVE_RECALL_RUNTIME.md).
- `reference/work_gate.py` demonstrates the step 4 safety-independence boundary: it validates the request shape, evaluates explicit production/permission triggers independently of resolution success, and fails closed unless the decision is `RESOLVED` with no active trigger. See [`docs/WORK_GATE.md`](docs/WORK_GATE.md).

This repository now contains six dependency-free Python reference surfaces. The resolver, Source Read Gate, preflight, Context Selection, and Work Gate do not perform external connector I/O. The Selective Recall runtime contains no connector discovery or connector-specific code; if its caller-supplied loader performs I/O, that I/O is the caller's responsibility. In particular, `source_read_gate.py` does **not** prove that a repository or document was really fetched; the caller supplies the read evidence that the model evaluates. The runtime also does not independently prove the provenance, safety, or correctness of a loader implementation. The Work Gate likewise does not detect production/permission conditions on its own and a `PROCEED` result is not permission to execute work.

Run locally:

```bash
python tests/test_work_gate.py
python tests/test_selective_recall_runtime.py
python tests/test_context_selection.py
python tests/test_context_router_preflight.py
python tests/test_resolver.py
python -m unittest discover -s tests -p test_source_read_gate.py
python -m compileall reference runtime tests
```

The Source Read Gate unittest suite contains 32 tests in this reference, including regression guards for the existing decision resolver. The Context Selection suite contains 18 tests, the Context Router Preflight suite contains 7 tests, the Selective Recall runtime suite contains 12 tests, and the Work Gate suite contains 18 tests.

The GitHub Actions workflow in this repository ([`.github/workflows/reference-tests.yml`](.github/workflows/reference-tests.yml)) runs the resolver, Source Read Gate, preflight, Context Selection, Selective Recall, and Work Gate suites plus `compileall` on pull requests and pushes.

## Status

Public reference v0.1.

No license is declared yet. Until a license is added, standard copyright applies; public visibility does not itself grant reuse rights.
