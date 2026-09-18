# Writeback Gate

## What this is

[`reference/writeback_gate.py`](../reference/writeback_gate.py) is a small,
dependency-free pure/local reference for step 6 ("Writeback") of
[`ARCHITECTURE.md`](ARCHITECTURE.md):

> Important confirmed decisions should be persisted outside the transient
> AI conversation.
>
> Examples:
> - selected implementation direction
> - current version
> - approved price
> - next action
> - superseded decision relationship
> - implementation status
>
> The AI may propose a writeback, but proposal status must not be silently
> promoted to authoritative status.

`writeback_gate.py` models that rule as a single deterministic function:
given a caller-supplied `origin`, `requested_status`, and `important`
signal, it returns a fail-closed `WRITEBACK_CANDIDATE` / `NOT_REQUIRED` /
`REVIEW_REQUIRED` outcome.

## What it does

`evaluate(request)`:

1. Validates the shape of `request` before touching any of its fields.
   `request` that is not itself a `WritebackGateRequest` instance -- `None`,
   a `dict`, a plain object, or any other non-`WritebackGateRequest` value
   -- fails closed as `REVIEW_REQUIRED` with `reason == "malformed_input"`
   instead of raising `AttributeError`. Once `request` is confirmed to be a
   `WritebackGateRequest`, an `origin` outside `ORIGINS`, a
   `requested_status` outside `REQUESTED_STATUSES`, or a non-boolean
   `important`, fails closed the same way, before any field is
   interpreted.
2. Checks whether `origin == "AI_PROPOSAL"` while `requested_status` is
   anything other than `"PROPOSED"`. If so, the result is
   `REVIEW_REQUIRED` with `reason ==
   "ai_proposal_authoritative_status"` -- **regardless of `important`**.
   An AI proposal is never allowed to request an authoritative-capable
   status (`"ACTIVE"` or `"LOCKED"`); doing so would be exactly the silent
   promotion from proposal status to authoritative status that step 6
   forbids.
3. Otherwise, checks `important`. If `True`, the result is
   `WRITEBACK_CANDIDATE`, naming the `origin` and `requested_status` that
   were in force. If `False`, the result is `NOT_REQUIRED`.

`origin` is expected to be one of `ORIGINS`: `"USER_CONFIRMED"` for content
the user has confirmed, or `"AI_PROPOSAL"` for a writeback the AI itself is
proposing. `requested_status` is expected to be one of
`REQUESTED_STATUSES` (`"PROPOSED"`, `"ACTIVE"`, `"LOCKED"`) -- the same
status vocabulary already used by
[`minimal_resolver.py`](../reference/minimal_resolver.py)
(see [`DECISION_RESOLUTION_SPEC.md`](DECISION_RESOLUTION_SPEC.md)).
`important` is an explicit boolean supplied by the caller for whether the
content is one of the "important confirmed decisions" step 6 names. This
module does not detect, classify, or discover importance, origin, or
status itself -- it only reacts to what it is told.

## Return shape

Every result has a `state` key of `WRITEBACK_CANDIDATE`, `NOT_REQUIRED`,
or `REVIEW_REQUIRED`:

- `state == "WRITEBACK_CANDIDATE"` -- the request is well-formed, is not
  an AI proposal requesting an authoritative-capable status, and
  `important` is `True`. Includes `origin` and `requested_status` for
  traceability.
- `state == "NOT_REQUIRED"` -- the request is well-formed and `important`
  is `False`.
- `state == "REVIEW_REQUIRED"` -- the gate failed closed. `reason` is one
  of `"malformed_input"` (with an `errors` tuple -- populated whether
  `request` was not a `WritebackGateRequest` at all or was one with a
  badly typed or out-of-range field) or
  `"ai_proposal_authoritative_status"` (with the `origin` and
  `requested_status` that were in force).

## What this is not

- It performs no I/O. It does not persist, retrieve, or otherwise write
  back anything itself; `origin`, `requested_status`, and `important` are
  all supplied by the caller.
- It does not decide what a `WRITEBACK_CANDIDATE` outcome leads to -- no
  persistence, mutation, or external call follows from this module. It
  only classifies its inputs into `WRITEBACK_CANDIDATE`, `NOT_REQUIRED`,
  or `REVIEW_REQUIRED`; the caller decides what any outcome leads to.
- It does not create authority: a `WRITEBACK_CANDIDATE` result is not
  itself an authoritative record, and this module has no way to grant,
  escalate, or record one. An `AI_PROPOSAL` origin can never reach this
  gate with an authoritative-capable `requested_status`.
- It does not change the behavior, contract, or test coverage of any
  existing reference module. `tests/test_writeback_gate.py` covers only
  this new module's own boundary.

## Run locally

```bash
python tests/test_writeback_gate.py
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
- [`RESYNC_GATE.md`](RESYNC_GATE.md)
- [`WORK_GATE.md`](WORK_GATE.md)
- [`DECISION_RESOLUTION_SPEC.md`](DECISION_RESOLUTION_SPEC.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
