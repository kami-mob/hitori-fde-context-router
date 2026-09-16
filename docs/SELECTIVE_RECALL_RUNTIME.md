# Selective Recall Runtime Boundary

## What this is

[`runtime/selective_recall.py`](../runtime/selective_recall.py) is a small,
dependency-free reference for step 3 of [`ARCHITECTURE.md`](ARCHITECTURE.md)
— Selective Recall — implemented as a thin runtime boundary rather than a
planning function.

[`CONTEXT_SELECTION.md`](CONTEXT_SELECTION.md) already covers step 2 (the
Context Router): it decides *what* should be read next and returns a plan.
ARCHITECTURE.md is explicit that step 2's reference "does not perform step 3
(Selective Recall), the actual retrieval/loading of that content once
planned; that remains a runtime/product concern." This module is that
narrow boundary: given a plan already produced by
[`reference/context_selection.py`](../reference/context_selection.py)'s
`select_context` and a caller-supplied loader, it invokes the loader for
exactly the ids the plan already selected, in the plan's own order, and
nothing else.

## What it does

`load_selected_context(plan_result, loader)`:

1. Validates that `plan_result` is a well-formed, `SELECTED`
   context-selection plan: `stage == "context_selection"`, `state ==
   "SELECTED"`, and a `plan` that is a flat sequence of unique, non-empty
   string ids. Anything else — a different stage, a non-`SELECTED` state
   such as the upstream planner's own `DATA_ERROR`, or a malformed `plan`
   — is rejected with `state == "DATA_ERROR"` and `loader` is never called.
2. Otherwise calls `loader(candidate_id)` once for each id in `plan`, in
   plan order, and nothing else. It never consults `selected` (the
   per-tier breakdown) to decide what to load, and it never loads a
   candidate id that isn't already present in `plan` — in particular, a
   `COLD` candidate that `select_context` excluded is never loaded here
   just because it exists.
3. Each id's load is independent and fail-closed: if `loader` raises for a
   given id, that id is omitted from `loaded` (no fallback or partial value
   is substituted for it) and its error message is recorded in `failed`
   keyed by that id. A failure on one id does not stop the remaining ids
   in the plan from being attempted.
4. Returns `state == "LOADED"` when every id loaded successfully (`failed`
   is empty), or `state == "PARTIAL"` when one or more ids failed.

## What this is not

- It performs no relevance scoring and makes no selection decision of its
  own. Which candidates to load was already decided by `select_context`;
  this module only executes that decision.
- It performs no autonomous search or connector discovery. The only I/O
  that happens is inside the caller-supplied `loader`, which this module
  never inspects, wraps, or extends — it neither picks a connector nor
  decides how a given id is fetched.
- It never expands retrieval beyond the supplied plan. It does not sweep
  additional `COLD` (or any other) candidates, does not retry a failed
  loader call with a broader query, and does not infer related ids to load
  alongside the ones already selected.
- It performs no external model invocation and no production mutation. It
  is a pure, same-process orchestration loop over an already-decided plan
  and a caller-supplied callable.
- It does not compose with, call, or reimplement `select_context`; it
  consumes that function's output as opaque, caller-supplied data.

## Run locally

```bash
python tests/test_selective_recall_runtime.py
python tests/test_context_selection.py
python -m compileall runtime tests
```

Expected result: all tests pass.

See also:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`CONTEXT_SELECTION.md`](CONTEXT_SELECTION.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
