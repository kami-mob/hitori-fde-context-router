import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from source_read_gate import GateRequest  # noqa: E402
from context_router_preflight import resolve_with_source_read_gate  # noqa: E402


def load_records():
    with open(ROOT / "reference" / "sample_decisions.json", encoding="utf-8") as f:
        return json.load(f)


RESOLVED_KWARGS = dict(domain="demo", subject="starter", field="price", as_of="2026-08-28")


class TestContextRouterPreflight(unittest.TestCase):
    def test_not_applicable_gate_proceeds_to_resolver(self):
        result = resolve_with_source_read_gate(
            GateRequest(), load_records(), **RESOLVED_KWARGS
        )
        self.assertEqual(result["stage"], "resolution")
        self.assertEqual(result["state"], "RESOLVED")
        self.assertEqual(result["record"]["value"], 200)
        self.assertEqual(result["gate"]["state"], "NOT_APPLICABLE")

    def test_pass_gate_proceeds_to_resolver(self):
        gate_request = GateRequest(
            declared_sources=("repo:decisions.json",),
            read_log=("repo:decisions.json",),
        )
        result = resolve_with_source_read_gate(gate_request, load_records(), **RESOLVED_KWARGS)
        self.assertEqual(result["stage"], "resolution")
        self.assertEqual(result["state"], "RESOLVED")
        self.assertEqual(result["gate"]["state"], "PASS")

    def test_verify_gate_short_circuits_without_calling_resolver(self):
        gate_request = GateRequest(declared_sources=("repo:decisions.json",))
        with mock.patch(
            "context_router_preflight.resolve_current"
        ) as mocked_resolve:
            result = resolve_with_source_read_gate(gate_request, load_records(), **RESOLVED_KWARGS)
        mocked_resolve.assert_not_called()
        self.assertEqual(result["stage"], "source_read_gate")
        self.assertEqual(result["state"], "VERIFY")
        self.assertEqual(result["reason"], "not_yet_read")
        self.assertNotIn("record", result)

    def test_unknown_gate_short_circuits_without_calling_resolver(self):
        gate_request = GateRequest(
            declared_sources=("repo:missing.py",),
            unavailable_sources=("repo:missing.py",),
        )
        with mock.patch(
            "context_router_preflight.resolve_current"
        ) as mocked_resolve:
            result = resolve_with_source_read_gate(gate_request, load_records(), **RESOLVED_KWARGS)
        mocked_resolve.assert_not_called()
        self.assertEqual(result["stage"], "source_read_gate")
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "required_source_unavailable")

    def test_data_error_gate_short_circuits_without_calling_resolver(self):
        gate_request = GateRequest(declared_sources=("a",), mode="XOR")
        with mock.patch(
            "context_router_preflight.resolve_current"
        ) as mocked_resolve:
            result = resolve_with_source_read_gate(gate_request, load_records(), **RESOLVED_KWARGS)
        mocked_resolve.assert_not_called()
        self.assertEqual(result["stage"], "source_read_gate")
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("unknown mode: XOR", result["errors"])

    def test_gate_pass_does_not_mask_resolver_own_fail_closed_state(self):
        # The gate passing must not be mistaken for the resolver also having
        # a clean answer: an unrelated resolver-level UNKNOWN must still
        # surface unchanged.
        gate_request = GateRequest(
            declared_sources=("repo:decisions.json",),
            read_log=("repo:decisions.json",),
        )
        result = resolve_with_source_read_gate(
            gate_request,
            load_records(),
            domain="demo",
            subject="starter",
            field="unknown-field",
            as_of="2026-08-28",
        )
        self.assertEqual(result["stage"], "resolution")
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["gate"]["state"], "PASS")

    def test_continuation_carryover_reaches_resolver_when_satisfied(self):
        gate_request = GateRequest(
            continued_from_previous=True,
            previous_declared_sources=("repo:decisions.json",),
            previous_mode="ALL",
            read_log=("repo:decisions.json",),
        )
        result = resolve_with_source_read_gate(gate_request, load_records(), **RESOLVED_KWARGS)
        self.assertEqual(result["stage"], "resolution")
        self.assertEqual(result["state"], "RESOLVED")


if __name__ == "__main__":
    unittest.main()
