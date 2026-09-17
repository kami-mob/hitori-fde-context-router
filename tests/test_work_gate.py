from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from work_gate import WorkGateRequest, evaluate  # noqa: E402


class TestWorkGate(unittest.TestCase):
    def test_resolved_decision_with_no_triggers_proceeds(self):
        result = evaluate(WorkGateRequest(decision_state="RESOLVED"))
        self.assertEqual(result["state"], "PROCEED")
        self.assertEqual(result["decision_state"], "RESOLVED")

    def test_no_decision_state_fails_closed(self):
        result = evaluate(WorkGateRequest())
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "decision_not_resolved")
        self.assertIsNone(result["decision_state"])

    def test_unknown_decision_fails_closed(self):
        result = evaluate(WorkGateRequest(decision_state="UNKNOWN"))
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "decision_not_resolved")

    def test_conflict_decision_fails_closed(self):
        result = evaluate(WorkGateRequest(decision_state="CONFLICT"))
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "decision_not_resolved")

    def test_verify_decision_fails_closed(self):
        result = evaluate(WorkGateRequest(decision_state="VERIFY"))
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "decision_not_resolved")

    def test_data_error_decision_fails_closed(self):
        result = evaluate(WorkGateRequest(decision_state="DATA_ERROR"))
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "decision_not_resolved")

    def test_other_non_success_value_fails_closed(self):
        # Any decision_state that is not the literal success value is
        # treated the same as the known fail-closed states: there is no
        # allowlist of "acceptable" non-success values.
        result = evaluate(WorkGateRequest(decision_state="SOMETHING_ELSE"))
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "decision_not_resolved")

    def test_production_trigger_forces_review_even_on_resolved_decision(self):
        # A successful decision must never mask a live production trigger:
        # safety is independent of decision success.
        result = evaluate(
            WorkGateRequest(decision_state="RESOLVED", production_trigger=True)
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "safety_trigger")
        self.assertEqual(result["triggers"], ("production",))
        self.assertEqual(result["decision_state"], "RESOLVED")

    def test_permission_trigger_forces_review_even_on_resolved_decision(self):
        result = evaluate(
            WorkGateRequest(decision_state="RESOLVED", permission_trigger=True)
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "safety_trigger")
        self.assertEqual(result["triggers"], ("permission",))

    def test_both_triggers_are_both_reported(self):
        result = evaluate(
            WorkGateRequest(
                decision_state="RESOLVED",
                production_trigger=True,
                permission_trigger=True,
            )
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "safety_trigger")
        self.assertEqual(result["triggers"], ("production", "permission"))

    def test_trigger_forces_review_on_top_of_unresolved_decision(self):
        # Safety triggers apply on top of every decision state, not only a
        # successful one: an UNKNOWN decision plus a live production trigger
        # is still reported as a safety trigger, not silently downgraded to
        # the (also true) decision_not_resolved reason.
        result = evaluate(
            WorkGateRequest(decision_state="UNKNOWN", production_trigger=True)
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "safety_trigger")
        self.assertEqual(result["triggers"], ("production",))

    def test_malformed_decision_state_type_fails_closed(self):
        result = evaluate(WorkGateRequest(decision_state=123))  # type: ignore[arg-type]
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("decision_state must be a string or None", result["errors"])

    def test_malformed_production_trigger_type_fails_closed(self):
        result = evaluate(
            WorkGateRequest(decision_state="RESOLVED", production_trigger="yes")  # type: ignore[arg-type]
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("production_trigger must be a bool", result["errors"])

    def test_malformed_permission_trigger_type_fails_closed(self):
        result = evaluate(
            WorkGateRequest(decision_state="RESOLVED", permission_trigger=1)  # type: ignore[arg-type]
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("permission_trigger must be a bool", result["errors"])

    def test_multiple_malformed_fields_are_all_reported(self):
        result = evaluate(
            WorkGateRequest(
                decision_state=123,  # type: ignore[arg-type]
                production_trigger="yes",  # type: ignore[arg-type]
                permission_trigger=1,  # type: ignore[arg-type]
            )
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertEqual(
            set(result["errors"]),
            {
                "decision_state must be a string or None",
                "production_trigger must be a bool",
                "permission_trigger must be a bool",
            },
        )

    def test_malformed_input_wins_over_reporting_a_fired_trigger(self):
        # Malformed shape is checked first: a bad production_trigger type
        # cannot itself be trusted as "fired", so this must fail closed via
        # malformed_input rather than safety_trigger.
        result = evaluate(
            WorkGateRequest(decision_state="RESOLVED", production_trigger="true")  # type: ignore[arg-type]
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")

    def test_none_request_fails_closed_instead_of_raising(self):
        # A caller passing None (e.g. a missing/uninitialized request) must
        # never raise AttributeError from reading request.decision_state;
        # it fails closed as malformed_input like any other bad shape.
        result = evaluate(None)  # type: ignore[arg-type]
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("request must be a WorkGateRequest instance", result["errors"])

    def test_non_request_object_fails_closed_instead_of_raising(self):
        # A caller passing a dict (or any other non-WorkGateRequest object)
        # -- for example forgetting to construct the dataclass -- must also
        # fail closed rather than raising when its fields are read.
        result = evaluate(
            {"decision_state": "RESOLVED", "production_trigger": False, "permission_trigger": False}  # type: ignore[arg-type]
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("request must be a WorkGateRequest instance", result["errors"])


if __name__ == "__main__":
    unittest.main()
