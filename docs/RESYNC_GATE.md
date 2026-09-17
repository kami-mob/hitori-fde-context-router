# Re-sync Gate

## What this is

[`reference/resync_gate.py`](../reference/resync_gate.py) is a small,
dependency-free pure/local reference for step 5 ("Long-context re-sync") of
[`ARCHITECTURE.md`](ARCHITECTURE.md):

> Conversation history is working context, not the final source of truth.
>
> Re-sync to canonical state when the user asks for, or the task reaches, a
> material boundary such as:
>
> - current / latest status
> - continuation of previous work
> - important confirmation
> - implementation
> - publication / release
> - production change
> - permission change
> - price / specification / version change
> - continuation of a task that explicitly designated a saved source

`resync_gate.py` models that rule as a single deterministic function: given
nine caller-supplied booleans, one per material-boundary signal above, it
returns a fail-closed `RESYNC_REQUIRED` / `NOT_REQUIRED` outcome.

## What it does

`evaluate(request)`:

1. Validates the shape of `request` before touching any of its fields.
   `request` that is not itself a `ResyncGateRequest` instance -- `None`, a
   `dict`, a plain object, or any other non-`ResyncGateRequest` value --
   fails closed as `RESYNC_REQUIRED` with `reason == "malformed_input"`
   instead of raising `AttributeError`. Once `request` is confirmed to be a
   `ResyncGateRequest`, any non-boolean signal field fails closed the same
   way, before any signal is interpreted.
2. Otherwise, checks whether any of the nine signal fields is `True`. If at
   least one is, the result is `RESYNC_REQUIRED` with
   `reason == "material_boundary"` and a `signals` tuple naming every
   active signal, in the order they are declared on `ResyncGateRequest`
   (`SIGNAL_FIELDS`).
3. If none of the nine signals is active, the result is `NOT_REQUIRED`.

Each field on `ResyncGateRequest` corresponds 1:1 to one bullet from step 5:
`current_or_latest`, `continuation`, `important_confirmation`,
`implementation`, `publication_or_release`, `production_change`,
`permission_change`, `price_spec_version_change`, and
`explicit_source_continuation`. This module does not detect, classify, or
discover any of these conditions itself -- it only reacts to what it is
told.

## Return shape

Every result has a `state` key of `RESYNC_REQUIRED` or `NOT_REQUIRED`:

- `state == "NOT_REQUIRED"` -- the request is well-formed and no
  material-boundary signal is active.
- `state == "RESYNC_REQUIRED"` -- the gate failed closed. `reason` is one
  of `"malformed_input"` (with an `errors` tuple -- populated whether
  `request` was not a `ResyncGateRequest` at all or was one with a badly
  typed field) or `"material_boundary"` (with a `signals` tuple naming
  every active signal).

## What this is not

- It performs no I/O. It does not call the upstream resolver, Work Gate, or
  context-selection modules itself; every signal is supplied by the
  caller.
- It does not perform retrieval, writeback, external I/O, or tool calls of
  its own, and it does not decide what the caller's re-sync should look
  like. It only classifies its inputs into `RESYNC_REQUIRED` or
  `NOT_REQUIRED`; the caller decides what either outcome leads to.
- It does not create authority: neither outcome is itself permission to
  perform a production, permission, merge, publication, or other governed
  action.
- It does not change the behavior, contract, or test coverage of any
  existing reference module. `tests/test_resync_gate.py` covers only this
  new module's own boundary.

## Run locally

```bash
python tests/test_resync_gate.py
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
- [`WORK_GATE.md`](WORK_GATE.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
