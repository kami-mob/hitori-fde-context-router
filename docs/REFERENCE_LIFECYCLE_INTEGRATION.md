# Reference Lifecycle Integration

## What this is

[`tests/test_reference_lifecycle_integration.py`](../tests/test_reference_lifecycle_integration.py)
is a synthetic, in-memory integration test suite that proves two full
end-to-end chains across the existing step-0-through-step-6 reference
interfaces described in [`ARCHITECTURE.md`](ARCHITECTURE.md):

- [`reference/source_read_gate.py`](../reference/source_read_gate.py) (step 0)
- [`reference/minimal_resolver.py`](../reference/minimal_resolver.py) (step 1)
- [`reference/context_selection.py`](../reference/context_selection.py) (step 2)
- [`runtime/selective_recall.py`](../runtime/selective_recall.py) (step 3)
- [`reference/work_gate.py`](../reference/work_gate.py) (step 4)
- [`reference/resync_gate.py`](../reference/resync_gate.py) (step 5)
- [`reference/writeback_gate.py`](../reference/writeback_gate.py) (step 6)

It adds no new behavior, orchestrator, or product code of its own: each test
calls the existing, unmodified functions from those modules directly, in the
order `ARCHITECTURE.md` already specifies, and asserts on their already
documented return contracts. The only new code is the test file itself plus
a small in-memory `RecordingLoader` used as the Selective Recall step's
caller-supplied loader; it holds no filesystem, network, or connector
access and resolves every id from an in-process dict.

## The two chains

### Chain A: `VERIFY` at step 0 still reaches, and is fails-closed by, step 4

`test_verify_chain_source_read_gate_through_work_gate_review_required`:

1. **Step 0** -- `source_read_gate.evaluate` on a declared source with an
   empty `read_log` returns `VERIFY` / `not_yet_read`: the requirement is
   real but not yet satisfied.
2. **Step 2** -- `context_selection.select_context` is called with that
   `VERIFY` result passed through as `resolution`. Selection itself does
   not inspect or branch on it (per `ARCHITECTURE.md` step 3's Safety
   independence: a router/selector step must not be silently skipped just
   because an upstream decision is unresolved); the returned plan is the
   deterministic HOT/WARM/COLD selection over the supplied candidates,
   including the `explicit_source` COLD carve-out.
3. **Step 3** -- `selective_recall.load_selected_context` loads exactly the
   plan's ids, in plan order, through the in-memory `RecordingLoader`. The
   COLD candidate that step 2 excluded is asserted to never be loaded.
4. **Step 4** -- `work_gate.evaluate` is given `decision_state` equal to the
   step-0 gate's own state (`"VERIFY"`, never having reached `RESOLVED`)
   and returns `REVIEW_REQUIRED` / `decision_not_resolved`, independent of
   whatever steps 2-3 already did.

### Chain B: `RESOLVED` flows all the way to a `WRITEBACK_CANDIDATE` classification

`test_resolved_chain_through_writeback_gate_classification`:

1. **Step 1** -- `minimal_resolver.resolve_current` resolves a two-record,
   fully in-memory supersession chain (`SUPERSEDED` -> `ACTIVE`) to
   `RESOLVED`.
2. **Step 2** -- `context_selection.select_context` plans a HOT decision
   candidate and a WARM candidate gated on a supplied
   `production_change` condition.
3. **Step 3** -- `selective_recall.load_selected_context` loads that plan,
   in order, through the same kind of in-memory loader.
4. **Step 4** -- `work_gate.evaluate` on `decision_state="RESOLVED"` with no
   safety trigger returns `PROCEED`.
5. **Step 5** -- `resync_gate.evaluate` with a supplied
   `production_change=True` signal returns `RESYNC_REQUIRED` /
   `material_boundary`, showing that a material-boundary signal still
   forces a re-sync even after steps 1-4 all already succeeded.
6. **Step 6** -- `writeback_gate.evaluate` is exercised at both ends of the
   authority boundary: an `AI_PROPOSAL` requesting `ACTIVE` or `LOCKED`
   fails closed as `REVIEW_REQUIRED` / `ai_proposal_authoritative_status`
   (subject to `subTest` for each status), while an important
   `USER_CONFIRMED` request at `ACTIVE` classifies as
   `WRITEBACK_CANDIDATE`.

## What this is not

- It introduces no runtime, orchestrator, agent loop, or product code. Every
  call in both chains targets a function that already existed in
  `reference/` or `runtime/` before this test file was added.
- It performs no real I/O. The only "loader" in either chain is the
  in-memory `RecordingLoader` defined in the test file itself; every record,
  candidate, and signal in both chains is a literal supplied inline in the
  test.
- It does not change the behavior, return shape, or existing test coverage
  of any of the seven modules it calls. Their own suites (listed below)
  remain the authority on each module's individual contract; this file only
  proves that the existing contracts still compose correctly end to end.
- It does not decide, encode, or grant any authority of its own. `PROCEED`,
  `RESYNC_REQUIRED`, and `WRITEBACK_CANDIDATE` here are the same
  non-authoritative classification outputs described in
  [`WORK_GATE.md`](WORK_GATE.md), [`RESYNC_GATE.md`](RESYNC_GATE.md), and
  [`WRITEBACK_GATE.md`](WRITEBACK_GATE.md); nothing in this suite performs
  or authorizes a production, permission, or writeback action.

## Run locally

```bash
python tests/test_reference_lifecycle_integration.py
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
- [`SOURCE_READ_GATE.md`](SOURCE_READ_GATE.md)
- [`DECISION_RESOLUTION_SPEC.md`](DECISION_RESOLUTION_SPEC.md)
- [`CONTEXT_SELECTION.md`](CONTEXT_SELECTION.md)
- [`SELECTIVE_RECALL_RUNTIME.md`](SELECTIVE_RECALL_RUNTIME.md)
- [`WORK_GATE.md`](WORK_GATE.md)
- [`RESYNC_GATE.md`](RESYNC_GATE.md)
- [`WRITEBACK_GATE.md`](WRITEBACK_GATE.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
