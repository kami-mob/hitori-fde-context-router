from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from resync_gate import SIGNAL_FIELDS, ResyncGateRequest, evaluate  # noqa: E402


class TestResyncGate(unittest.TestCase):
    def test_no_signals_is_not_required(self):
        result = evaluate(ResyncGateRequest())
        self.assertEqual(result, {"state": "NOT_REQUIRED"})

    def test_each_signal_alone_requires_resync(self):
        # Every one of the nine step-5 material-boundary signals must be
        # sufficient on its own; none is treated as optional or ignorable.
        for name in SIGNAL_FIELDS:
            with self.subTest(signal=name):
                result = evaluate(ResyncGateRequest(**{name: True}))
                self.assertEqual(result["state"], "RESYNC_REQUIRED")
                self.assertEqual(result["reason"], "material_boundary")
                self.assertEqual(result["signals"], (name,))

    def test_multiple_active_signals_are_all_reported_in_order(self):
        result = evaluate(
            ResyncGateRequest(
                permission_change=True,
                current_or_latest=True,
                implementation=True,
            )
        )
        self.assertEqual(result["state"], "RESYNC_REQUIRED")
        self.assertEqual(result["reason"], "material_boundary")
        self.assertEqual(
            result["signals"],
            ("current_or_latest", "implementation", "permission_change"),
        )

    def test_all_signals_active(self):
        result = evaluate(ResyncGateRequest(**{name: True for name in SIGNAL_FIELDS}))
        self.assertEqual(result["state"], "RESYNC_REQUIRED")
        self.assertEqual(result["reason"], "material_boundary")
        self.assertEqual(result["signals"], SIGNAL_FIELDS)

    def test_none_request_fails_closed_instead_of_raising(self):
        # A caller passing None (e.g. a missing/uninitialized request) must
        # never raise AttributeError from reading its fields; it fails
        # closed as malformed_input like any other bad shape.
        result = evaluate(None)  # type: ignore[arg-type]
        self.assertEqual(result["state"], "RESYNC_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("request must be a ResyncGateRequest instance", result["errors"])

    def test_non_request_object_fails_closed_instead_of_raising(self):
        # A caller passing a dict (or any other non-ResyncGateRequest
        # object) -- for example forgetting to construct the dataclass --
        # must also fail closed rather than raising when its fields are
        # read.
        result = evaluate({"current_or_latest": True})  # type: ignore[arg-type]
        self.assertEqual(result["state"], "RESYNC_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("request must be a ResyncGateRequest instance", result["errors"])

    def test_malformed_single_field_type_fails_closed(self):
        result = evaluate(ResyncGateRequest(continuation="yes"))  # type: ignore[arg-type]
        self.assertEqual(result["state"], "RESYNC_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertIn("continuation must be a bool", result["errors"])

    def test_multiple_malformed_fields_are_all_reported(self):
        result = evaluate(
            ResyncGateRequest(
                current_or_latest=1,  # type: ignore[arg-type]
                production_change="true",  # type: ignore[arg-type]
            )
        )
        self.assertEqual(result["state"], "RESYNC_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")
        self.assertEqual(
            set(result["errors"]),
            {
                "current_or_latest must be a bool",
                "production_change must be a bool",
            },
        )

    def test_malformed_input_wins_over_reporting_an_active_signal(self):
        # Malformed shape is checked first: a bad current_or_latest type
        # cannot itself be trusted as "active", so this must fail closed
        # via malformed_input rather than material_boundary.
        result = evaluate(
            ResyncGateRequest(current_or_latest="true", implementation=True)  # type: ignore[arg-type]
        )
        self.assertEqual(result["state"], "RESYNC_REQUIRED")
        self.assertEqual(result["reason"], "malformed_input")


if __name__ == "__main__":
    unittest.main()
