# Context Selection

## What this is

[`reference/context_selection.py`](../reference/context_selection.py) is a
small, dependency-free reference for step 2 of
[`ARCHITECTURE.md`](ARCHITECTURE.md) — the Context Router's HOT / WARM /
COLD selection — implemented as a deterministic, in-memory planning
function.

It composes with nothing else in this repository. The caller supplies
both the resolved scope (typically the output of
[`minimal_resolver.resolve_current`](../reference/minimal_resolver.py) or
[`context_router_preflight.resolve_with_source_read_gate`](../reference/context_router_preflight.py))
and a list of candidate context items already scored for relevance and
tagged with a tier; this module only decides which of those candidates
belong in the plan.

## What it does

`select_context(resolution, candidates, *, active_conditions=())`:

1. Validates the candidates (`reference/context_selection.py`'s
   `ContextCandidate`): no duplicate ids, no unknown tier. Any violation
   returns `state == "DATA_ERROR"` with the specific problems in `errors`
   and selects nothing.
2. Otherwise selects, per candidate:
   - **`HOT`** — selected iff `relevant` is true. Matches ARCHITECTURE.md:
     "Read by default when directly relevant."
   - **`WARM`** — selected iff the candidate's `condition` is set and is
     present in `active_conditions`. Matches "Read only when a condition
     requires it." A `WARM` candidate with no `condition` at all can never
     be triggered and is never selected.
   - **`COLD`** — never selected by default. Matches "Do not sweep broadly
     during normal startup." Two independent, caller-supplied carve-outs
     can select a `COLD` candidate anyway — see below.
   - Any candidate with `explicit_source` set is always selected,
     regardless of tier, `relevant`, or `condition`. This is the
     carve-out ARCHITECTURE.md states explicitly: "An explicit source
     read that is directly required by the user's request is not treated
     as a broad COLD sweep merely because that source would not otherwise
     be loaded by default." This override applies uniformly across all
     three tiers here, not just `COLD`.
   - Any `COLD` candidate with `explicitly_required` set is also
     selected, even when `explicit_source` is false. This is a *separate*
     signal from `explicit_source`: it does not carry a Source Read Gate
     designation (no source was named by the user), it is instead the
     caller's own judgment that the current task explicitly needs this
     `COLD` context. `explicit_source` and `explicitly_required` are
     independent — a candidate may set either, both, or neither — and
     `explicitly_required` has no effect outside `COLD`: `HOT` and `WARM`
     already have their own explicit mechanisms (`relevant` and
     `condition`).
3. Returns `state == "SELECTED"` with:
   - `selected` — a dict from tier name to a tuple of selected candidate
     ids, in the order the candidates were supplied.
   - `plan` — the flat `HOT`, then `WARM`, then `COLD` concatenation of
     those same ids, for a caller that just wants one read order.
   - `resolution` — the `resolution` argument, carried through unchanged.

## Why `resolution` is accepted but not inspected

`select_context` never branches on `resolution`; it only attaches it to
the returned plan for traceability, the same way
`context_router_preflight.resolve_with_source_read_gate` attaches the
gate's own outcome under `gate`.

This is intentional, not an omission. ARCHITECTURE.md's step 3 (Safety
independence) requires that "a production or permission trigger must
still fire when the decision state is `UNKNOWN`, `CONFLICT`, or
`VERIFY`." If `WARM` selection depended on the resolution having
succeeded, a safety-relevant `WARM` candidate (production-change rules,
permission-change rules) could silently drop out exactly when resolution
is uncertain — the opposite of what's required. Driving `WARM` selection
only from caller-supplied `active_conditions` keeps that independence
intact without this module needing to know what a resolution failure
even looks like.

## What this is not

- It performs no I/O. Whether a candidate is relevant, what tier it
  defaults to, and which conditions are currently active are all supplied
  by the caller; this module does not retrieve, score, or classify
  anything itself.
- It does not perform resolution. It consumes a resolution result as
  opaque, caller-supplied data; it does not call, wrap, or reimplement
  `minimal_resolver.resolve_current` or
  `context_router_preflight.resolve_with_source_read_gate`.
- It does not add external model invocation, agentic execution, a
  production runtime, or any mutation. It is a pure, same-process
  filter over in-memory metadata.

## Run locally

```bash
python tests/test_context_selection.py
python tests/test_context_router_preflight.py
python tests/test_resolver.py
python -m unittest discover -s tests -p test_source_read_gate.py
python -m compileall reference tests
```

Expected result: all tests pass.

See also:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`CONTEXT_ROUTER_PREFLIGHT.md`](CONTEXT_ROUTER_PREFLIGHT.md)
- [`DECISION_RESOLUTION_SPEC.md`](DECISION_RESOLUTION_SPEC.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
