from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "runtime"))

import context_selection  # noqa: E402
import minimal_resolver  # noqa: E402
import resync_gate  # noqa: E402
import selective_recall  # noqa: E402
import source_read_gate  # noqa: E402
import work_gate  # noqa: E402
import writeback_gate  # noqa: E402


class RecordingLoader:
    """An in-memory Selective Recall loader that records call order.

    No filesystem, network, or connector I/O of any kind: every value is
    resolved from ``values`` (or a synthetic default), entirely in process.
    """

    def __init__(self, values=None):
        self.values = values or {}
        self.calls = []

    def __call__(self, candidate_id):
        self.calls.append(candidate_id)
        return self.values.get(candidate_id, f"loaded:{candidate_id}")


class TestReferenceLifecycleIntegration(unittest.TestCase):
    """End-to-end chains across the existing step-0-through-step-6 modules.

    Each test only calls functions already defined in ``reference/`` and
    ``runtime/``, in the sequence ``docs/ARCHITECTURE.md`` specifies; it adds
    no orchestrator, no product code, and no I/O beyond the in-memory loader
    defined above.
    """

    def test_verify_chain_source_read_gate_through_work_gate_review_required(self):
        # Step 0: Source Read Gate -- a declared source that has not been
        # read yet fails closed as VERIFY rather than PASS.
        gate_result = source_read_gate.evaluate(
            source_read_gate.GateRequest(declared_sources=("repo:pricing-doc",))
        )
        self.assertEqual(gate_result["state"], "VERIFY")
        self.assertEqual(gate_result["reason"], "not_yet_read")

        # Step 2: Context Selection carries the gate's outcome through
        # unchanged and untouched -- selection here is driven only by tier
        # and active_conditions, matching ARCHITECTURE.md step 3's Safety
        # independence rule that downstream steps must not be silently
        # skipped just because an upstream decision is unresolved.
        candidates = [
            context_selection.ContextCandidate(id="active-decision", tier="HOT", relevant=True),
            context_selection.ContextCandidate(
                id="permission-rules", tier="WARM", condition="permission_change"
            ),
            context_selection.ContextCandidate(
                id="user-designated-doc", tier="COLD", explicit_source=True
            ),
            context_selection.ContextCandidate(id="unrelated-archive", tier="COLD", relevant=True),
        ]
        plan_result = context_selection.select_context(
            gate_result, candidates, active_conditions=("permission_change",)
        )
        self.assertEqual(plan_result["state"], "SELECTED")
        self.assertEqual(plan_result["resolution"], gate_result)
        self.assertEqual(
            plan_result["plan"],
            ("active-decision", "permission-rules", "user-designated-doc"),
        )

        # Step 3: Selective Recall loads exactly the plan, in plan order,
        # through a caller-supplied in-memory loader; the excluded COLD
        # candidate is never attempted.
        loader = RecordingLoader()
        recall_result = selective_recall.load_selected_context(plan_result, loader)
        self.assertEqual(recall_result["state"], "LOADED")
        self.assertEqual(
            loader.calls,
            ["active-decision", "permission-rules", "user-designated-doc"],
        )
        self.assertNotIn("unrelated-archive", recall_result["loaded"])

        # Step 4: Work Gate -- the decision never reached RESOLVED (the
        # source-read requirement from step 0 is still outstanding), so the
        # gate fails closed regardless of what steps 2-3 already did.
        work_result = work_gate.evaluate(
            work_gate.WorkGateRequest(decision_state=gate_result["state"])
        )
        self.assertEqual(work_result["state"], "REVIEW_REQUIRED")
        self.assertEqual(work_result["reason"], "decision_not_resolved")

    def test_resolved_chain_through_writeback_gate_classification(self):
        # Step 1: Resolution Kernel resolves cleanly over synthetic
        # in-memory records -- no file or network I/O.
        records = [
            {
                "decision_id": "PRICE-010",
                "scope": {"domain": "demo", "subject": "widget", "field": "price"},
                "status": "SUPERSEDED",
                "effective_from": "2026-01-01",
                "last_verified": "2026-01-10",
                "value": 10,
            },
            {
                "decision_id": "PRICE-011",
                "scope": {"domain": "demo", "subject": "widget", "field": "price"},
                "status": "ACTIVE",
                "effective_from": "2026-02-01",
                "supersedes": "PRICE-010",
                "last_verified": "2026-08-01",
                "value": 20,
            },
        ]
        resolution = minimal_resolver.resolve_current(
            records, domain="demo", subject="widget", field="price", as_of="2026-08-15"
        )
        self.assertEqual(resolution["state"], "RESOLVED")
        self.assertEqual(resolution["record"]["decision_id"], "PRICE-011")

        # Step 2: Context Selection over the resolved decision.
        candidates = [
            context_selection.ContextCandidate(id="active-decision", tier="HOT", relevant=True),
            context_selection.ContextCandidate(
                id="production-change-rules", tier="WARM", condition="production_change"
            ),
        ]
        plan_result = context_selection.select_context(
            resolution, candidates, active_conditions=("production_change",)
        )
        self.assertEqual(plan_result["state"], "SELECTED")
        self.assertEqual(plan_result["plan"], ("active-decision", "production-change-rules"))

        # Step 3: Selective Recall over the same kind of in-memory loader.
        loader = RecordingLoader()
        recall_result = selective_recall.load_selected_context(plan_result, loader)
        self.assertEqual(recall_result["state"], "LOADED")
        self.assertEqual(loader.calls, ["active-decision", "production-change-rules"])

        # Step 4: Work Gate proceeds -- the decision is RESOLVED and neither
        # safety trigger fired.
        work_result = work_gate.evaluate(
            work_gate.WorkGateRequest(decision_state=resolution["state"])
        )
        self.assertEqual(work_result["state"], "PROCEED")

        # Step 5: Re-sync Gate -- a supplied production-change signal forces
        # a re-sync even though decision and work both already succeeded.
        resync_result = resync_gate.evaluate(resync_gate.ResyncGateRequest(production_change=True))
        self.assertEqual(resync_result["state"], "RESYNC_REQUIRED")
        self.assertEqual(resync_result["reason"], "material_boundary")
        self.assertEqual(resync_result["signals"], ("production_change",))

        # Step 6: Writeback Gate classification. An AI proposal may never
        # request an authoritative-capable status, at either ACTIVE or
        # LOCKED -- that would be the silent promotion ARCHITECTURE.md's
        # step 6 forbids.
        for requested_status in ("ACTIVE", "LOCKED"):
            with self.subTest(requested_status=requested_status):
                ai_result = writeback_gate.evaluate(
                    writeback_gate.WritebackGateRequest(
                        origin="AI_PROPOSAL",
                        requested_status=requested_status,
                        important=True,
                    )
                )
                self.assertEqual(ai_result["state"], "REVIEW_REQUIRED")
                self.assertEqual(ai_result["reason"], "ai_proposal_authoritative_status")

        # An important, user-confirmed decision is a legitimate writeback
        # candidate.
        user_result = writeback_gate.evaluate(
            writeback_gate.WritebackGateRequest(
                origin="USER_CONFIRMED", requested_status="ACTIVE", important=True
            )
        )
        self.assertEqual(user_result["state"], "WRITEBACK_CANDIDATE")
        self.assertEqual(user_result["origin"], "USER_CONFIRMED")
        self.assertEqual(user_result["requested_status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
