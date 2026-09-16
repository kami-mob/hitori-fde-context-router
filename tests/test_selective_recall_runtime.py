from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "runtime"))

from context_selection import ContextCandidate, select_context  # noqa: E402
from selective_recall import load_selected_context  # noqa: E402


class RecordingLoader:
    """A loader stub that records call order and can be told to fail some ids."""

    def __init__(self, values=None, fail_ids=()):
        self.values = values or {}
        self.fail_ids = set(fail_ids)
        self.calls = []

    def __call__(self, candidate_id):
        self.calls.append(candidate_id)
        if candidate_id in self.fail_ids:
            raise ValueError(f"could not load {candidate_id}")
        return self.values.get(candidate_id, f"loaded:{candidate_id}")


class TestSelectiveRecallRuntime(unittest.TestCase):
    def _selected_plan(self, plan_ids):
        return {
            "stage": "context_selection",
            "state": "SELECTED",
            "resolution": {"state": "RESOLVED"},
            "selected": {"HOT": tuple(plan_ids), "WARM": (), "COLD": ()},
            "plan": tuple(plan_ids),
        }

    def test_loads_every_id_in_plan_order(self):
        loader = RecordingLoader()
        result = load_selected_context(self._selected_plan(["a", "b", "c"]), loader)

        self.assertEqual(result["stage"], "selective_recall")
        self.assertEqual(result["state"], "LOADED")
        self.assertEqual(loader.calls, ["a", "b", "c"])
        self.assertEqual(
            result["loaded"], {"a": "loaded:a", "b": "loaded:b", "c": "loaded:c"}
        )
        self.assertEqual(result["failed"], {})

    def test_empty_plan_loads_nothing_and_never_calls_loader(self):
        loader = RecordingLoader()
        result = load_selected_context(self._selected_plan([]), loader)

        self.assertEqual(result["state"], "LOADED")
        self.assertEqual(loader.calls, [])
        self.assertEqual(result["loaded"], {})
        self.assertEqual(result["failed"], {})

    def test_only_plan_ids_are_loaded_even_when_selected_has_more_tiers(self):
        # A COLD candidate that was excluded by select_context must never be
        # loaded just because it exists in `selected`; only what made it
        # into the flat `plan` is ever passed to the loader.
        candidates = [
            ContextCandidate(id="hot-1", tier="HOT", relevant=True),
            ContextCandidate(id="cold-excluded", tier="COLD", relevant=True),
        ]
        plan_result = select_context({"state": "RESOLVED"}, candidates)
        self.assertEqual(plan_result["plan"], ("hot-1",))

        loader = RecordingLoader()
        result = load_selected_context(plan_result, loader)

        self.assertEqual(loader.calls, ["hot-1"])
        self.assertEqual(result["loaded"], {"hot-1": "loaded:hot-1"})
        self.assertNotIn("cold-excluded", result["loaded"])

    def test_per_id_failure_is_fail_closed_and_does_not_abort_the_plan(self):
        loader = RecordingLoader(fail_ids=("b",))
        result = load_selected_context(self._selected_plan(["a", "b", "c"]), loader)

        self.assertEqual(result["state"], "PARTIAL")
        self.assertEqual(loader.calls, ["a", "b", "c"])
        self.assertEqual(result["loaded"], {"a": "loaded:a", "c": "loaded:c"})
        self.assertNotIn("b", result["loaded"])
        self.assertEqual(result["failed"], {"b": "could not load b"})

    def test_all_ids_failing_yields_partial_with_empty_loaded(self):
        loader = RecordingLoader(fail_ids=("a", "b"))
        result = load_selected_context(self._selected_plan(["a", "b"]), loader)

        self.assertEqual(result["state"], "PARTIAL")
        self.assertEqual(result["loaded"], {})
        self.assertEqual(set(result["failed"]), {"a", "b"})

    def test_rejects_non_dict_plan_result(self):
        loader = RecordingLoader()
        result = load_selected_context(None, loader)

        self.assertEqual(result["stage"], "selective_recall")
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("plan_result is not a dict", result["errors"])
        self.assertEqual(loader.calls, [])

    def test_rejects_wrong_stage(self):
        loader = RecordingLoader()
        plan_result = self._selected_plan(["a"])
        plan_result["stage"] = "something_else"
        result = load_selected_context(plan_result, loader)

        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("unexpected stage: 'something_else'", result["errors"])
        self.assertEqual(loader.calls, [])

    def test_rejects_data_error_plan_state(self):
        loader = RecordingLoader()
        plan_result = select_context(
            {"state": "RESOLVED"},
            [
                ContextCandidate(id="dup", tier="HOT", relevant=True),
                ContextCandidate(id="dup", tier="WARM", condition="x"),
            ],
        )
        self.assertEqual(plan_result["state"], "DATA_ERROR")

        result = load_selected_context(plan_result, loader)

        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("plan state is not SELECTED: 'DATA_ERROR'", result["errors"])
        self.assertEqual(loader.calls, [])

    def test_rejects_missing_plan_key(self):
        loader = RecordingLoader()
        plan_result = self._selected_plan(["a"])
        del plan_result["plan"]
        result = load_selected_context(plan_result, loader)

        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn(
            "plan is missing or is not a tuple/list of candidate ids", result["errors"]
        )
        self.assertEqual(loader.calls, [])

    def test_rejects_non_string_id_in_plan(self):
        loader = RecordingLoader()
        plan_result = self._selected_plan(["a"])
        plan_result["plan"] = ("a", 42)
        result = load_selected_context(plan_result, loader)

        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("plan contains a non-string or empty candidate id", result["errors"])
        self.assertEqual(loader.calls, [])

    def test_rejects_duplicate_id_in_plan(self):
        loader = RecordingLoader()
        plan_result = self._selected_plan(["a"])
        plan_result["plan"] = ("a", "a")
        result = load_selected_context(plan_result, loader)

        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("plan contains a duplicate candidate id", result["errors"])
        self.assertEqual(loader.calls, [])

    def test_end_to_end_with_real_context_selection_plan(self):
        candidates = [
            ContextCandidate(id="active-decision", tier="HOT", relevant=True),
            ContextCandidate(id="production-change-rules", tier="WARM", condition="production_change"),
            ContextCandidate(id="user-designated-doc", tier="COLD", explicit_source=True),
            ContextCandidate(id="old-archive", tier="COLD", relevant=True),
        ]
        plan_result = select_context(
            {"state": "RESOLVED"},
            candidates,
            active_conditions=("production_change",),
        )
        loader = RecordingLoader()
        result = load_selected_context(plan_result, loader)

        self.assertEqual(result["state"], "LOADED")
        self.assertEqual(
            loader.calls,
            ["active-decision", "production-change-rules", "user-designated-doc"],
        )
        self.assertNotIn("old-archive", result["loaded"])


if __name__ == "__main__":
    unittest.main()
