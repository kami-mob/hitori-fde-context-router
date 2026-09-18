from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from writeback_gate import (  # noqa: E402
    ORIGINS,
    REQUESTED_STATUSES,
    WritebackGateRequest,
    evaluate,
)


class TestWritebackGate(unittest.TestCase):
    def test_important_user_confirmed_is_a_writeback_candidate(self):
        result = evaluate(
            WritebackGateRequest(
                origin="USER_CONFIRMED", requested_status="ACTIVE", important=True
            )
        )
        self.assertEqual(result["state"], "WRITEBACK_CANDIDATE")
        self.assertEqual(result["origin"], "USER_CONFIRMED")
        self.assertEqual(result["requested_status"], "ACTIVE")

    def test_important_user_confirmed_locked_is_a_writeback_candidate(self):
        result = evaluate(
            WritebackGateRequest(
                origin="USER_CONFIRMED", requested_status="LOCKED", important=True
            )
        )
        self.assertEqual(result["state"], "WRITEBACK_CANDIDATE")

    def test_non_important_user_confirmed_is_not_required(self):
        result = evaluate(
            WritebackGateRequest(
                origin="USER_CONFIRMED", requested_status="ACTIVE", important=False
            )
        )
        self.assertEqual(result, {"state": "NOT_REQUIRED"})

    def test_important_ai_proposal_at_proposed_is_a_writeback_candidate(self):
        result = evaluate(
            WritebackGateRequest(
                origin="AI_PROPOSAL", requested_status="PROPOSED", important=True
            )
        )
        self.assertEqual(result["state"], "WRITEBACK_CANDIDATE")
        self.assertEqual(result["origin"], "AI_PROPOSAL")
        self.assertEqual(result["requested_status"], "PROPOSED")

    def test_non_important_ai_proposal_at_proposed_is_not_required(self):
        result = evaluate(
            WritebackGateRequest(
                origin="AI_PROPOSAL", requested_status="PROPOSED", important=False
            )
        )
        self.assertEqual(result, {"state": "NOT_REQUIRED"})

    def test_ai_proposal_requesting_active_fails_closed(self):
        # An AI proposal must never be allowed to request an
        # authoritative-capable status: that would be exactly the silent
        # promotion step 6 of ARCHITECTURE.md forbids.
        result = evaluate(
            WritebackGateRequest(
                origin="AI_PROPOSAL", requested_status="ACTIVE", important=True
            )
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "ai_proposal_authoritative_status")
        self.assertEqual(result["origin"], "AI_PROPOSAL")
        self.assertEqual(result["requested_status"], "ACTIVE")

    def test_ai_proposal_requesting_locked_fails_closed(self):
        result = evaluate(
            WritebackGateRequest(
                origin="AI_PROPOSAL", requested_status="LOCKED", important=True
            )
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "ai_proposal_authoritative_status")

    def test_ai_proposal_requesting_active_fails_closed_even_if_not_important(self):
        # The authoritative-status restriction on AI_PROPOSAL is absolute:
        # it does not depend on importance.
        result = evaluate(
            WritebackGateRequest(
                origin="AI_PROPOSAL", requested_status="ACTIVE", important=False
            )
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "ai_proposal_authoritative_status")

    def test_none_request_fails_closed_instead_of_raising(self):
        # A caller passing None (e.g. a missing/uninitialized request) must
        # never raise AttributeError from reading its fields; it fails
        # closed as malformed_input like any other bad shape.
        result = evaluate(None)  # type: ignore[arg-type]
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("request must be a WritebackGateRequest instance", result["errors"])

    def test_non_request_object_fails_closed_instead_of_raising(self):
        # A caller passing a dict (or any other non-WritebackGateRequest
        # object) -- for example forgetting to construct the dataclass --
        # must also fail closed rather than raising when its fields are
        # read.
        result = evaluate(
            {"origin": "USER_CONFIRMED", "requested_status": "ACTIVE", "important": True}  # type: ignore[arg-type]
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("request must be a WritebackGateRequest instance", result["errors"])

    def test_unknown_origin_fails_closed(self):
        result = evaluate(
            WritebackGateRequest(origin="SOMETHING_ELSE", requested_status="PROPOSED")  # type: ignore[arg-type]
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn(f"origin must be one of {ORIGINS}", result["errors"])

    def test_unknown_requested_status_fails_closed(self):
        result = evaluate(
            WritebackGateRequest(origin="USER_CONFIRMED", requested_status="ARCHIVED")  # type: ignore[arg-type]
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn(
            f"requested_status must be one of {REQUESTED_STATUSES}", result["errors"]
        )

    def test_malformed_important_type_fails_closed(self):
        result = evaluate(
            WritebackGateRequest(
                origin="USER_CONFIRMED",
                requested_status="PROPOSED",
                important="yes",  # type: ignore[arg-type]
            )
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("important must be a bool", result["errors"])

    def test_multiple_malformed_fields_are_all_reported(self):
        result = evaluate(
            WritebackGateRequest(
                origin="NOPE",  # type: ignore[arg-type]
                requested_status="NOPE",  # type: ignore[arg-type]
                important=1,  # type: ignore[arg-type]
            )
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertEqual(
            set(result["errors"]),
            {
                f"origin must be one of {ORIGINS}",
                f"requested_status must be one of {REQUESTED_STATUSES}",
                "important must be a bool",
            },
        )

    def test_malformed_input_wins_over_authoritative_status_check(self):
        # Malformed shape is checked first: an unrecognized requested_status
        # cannot itself be trusted as "not PROPOSED", so this must fail
        # closed via malformed_input rather than
        # ai_proposal_authoritative_status.
        result = evaluate(
            WritebackGateRequest(
                origin="AI_PROPOSAL",
                requested_status="NOPE",  # type: ignore[arg-type]
                important=True,
            )
        )
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")


if __name__ == "__main__":
    unittest.main()
