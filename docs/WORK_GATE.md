# Work Gate

## What this is

[`reference/work_gate.py`](../reference/work_gate.py) is a small,
dependency-free pure/local reference for step 4 ("Safety independence") of
[`ARCHITECTURE.md`](ARCHITECTURE.md):

```text
Resolution state ───────────────┐
                               ├─> Work gate
Production / Permission trigger┘
```

> Safety is not a successful-resolution side effect. A production or
> permission trigger must still fire when the decision state is `UNKNOWN`,
> `CONFLICT`, or `VERIFY`.

`work_gate.py` models that rule as a single deterministic function: given a
caller-supplied upstream decision state and two explicit safety triggers, it
returns a fail-closed `PROCEED` / `REVIEW_REQUIRED` outcome.

## What it does

`evaluate(request)`:

1. Validates the shape of `request` before touching any of its fields.
   `request` that is not itself a `WorkGateRequest` instance -- `None`, a
   `dict`, a plain object, or any other non-`WorkGateRequest` value -- fails
   closed as `REVIEW_REQUIRED` with `reason == "malformed_input"` instead of
   raising `AttributeError`. Once `request` is confirmed to be a
   `WorkGateRequest`, a non-string `decision_state`, or a non-boolean
   trigger, fails closed the same way, before either trigger or the decision
   state is interpreted.
2. Checks whether `production_trigger` or `permission_trigger` fired. If
   either did, the result is `REVIEW_REQUIRED` with
   `reason == "safety_trigger"` and a `triggers` tuple naming which one(s)
   fired -- **regardless of the decision state**, including a decision that
   already reached `"RESOLVED"`. A live safety condition is never masked by
   an otherwise-successful decision.
3. Otherwise, checks the decision state itself. Only the literal value
   `"RESOLVED"` proceeds. Every other value -- `"UNKNOWN"`, `"CONFLICT"`,
   `"VERIFY"`, `"DATA_ERROR"`, `None`, or any other non-success string -- is
   treated identically as `REVIEW_REQUIRED` with
   `reason == "decision_not_resolved"`.

`decision_state` is meant to be fed the `state` value already produced by an
upstream stage such as
[`minimal_resolver.resolve_current`](../reference/minimal_resolver.py) or
[`context_router_preflight.resolve_with_source_read_gate`](../reference/context_router_preflight.py).
This module does not call either of those itself and does not reach into a
nested result dict; it takes the plain state string (or `None`) so it stays
the smallest possible check layered on top of whatever already produced a
decision outcome.

`production_trigger` and `permission_trigger` are plain booleans supplied by
the caller. This module does not detect, classify, or discover either
condition -- it only reacts to what it is told.

## Return shape

Every result has a `state` key of `PROCEED` or `REVIEW_REQUIRED`:

- `state == "PROCEED"` -- the decision reached `"RESOLVED"` and neither
  safety trigger fired. Includes `decision_state` for traceability.
- `state == "REVIEW_REQUIRED"` -- the gate failed closed. `reason` is one
  of `"malformed_input"` (with an `errors` tuple -- populated whether
  `request` was not a `WorkGateRequest` at all or was one with a badly
  typed field), `"safety_trigger"` (with a `triggers` tuple and the
  `decision_state` that was in force), or `"decision_not_resolved"` (with
  the `decision_state` that was in force).

## What this is not

- It performs no I/O. It does not call the upstream resolver, gate, or
  context-selection modules itself; both the decision state and the two
  triggers are supplied by the caller.
- It does not execute work, invoke tools, mutate production or permission
  state, discover connectors, retrieve context, or invoke an external
  model. It only classifies its inputs into `PROCEED` or `REVIEW_REQUIRED`;
  the caller decides what either outcome leads to.
- It does not create authority: a `PROCEED` result is not itself permission
  to act, and this module has no way to grant, escalate, or record one.
- It does not change the behavior, contract, or test coverage of any
  existing reference module. `tests/test_work_gate.py` covers only this new
  module's own boundary.

## Run locally

```bash
python tests/test_work_gate.py
python tests/test_resolver.py
python tests/test_context_router_preflight.py
python tests/test_context_selection.py
python tests/test_selective_recall_runtime.py
python -m unittest discover -s tests -p test_source_read_gate.py
python -m compileall reference runtime tests
```

Expected result: all tests pass.

See also:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`DECISION_RESOLUTION_SPEC.md`](DECISION_RESOLUTION_SPEC.md)
- [`CONTEXT_ROUTER_PREFLIGHT.md`](CONTEXT_ROUTER_PREFLIGHT.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
