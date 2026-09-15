from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from context_selection import ContextCandidate, select_context  # noqa: E402


class TestContextSelection(unittest.TestCase):
    def test_hot_relevant_selected_by_default(self):
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="active-decision", tier="HOT", relevant=True)],
        )
        self.assertEqual(result["stage"], "context_selection")
        self.assertEqual(result["state"], "SELECTED")
        self.assertEqual(result["selected"]["HOT"], ("active-decision",))
        self.assertEqual(result["plan"], ("active-decision",))

    def test_hot_irrelevant_excluded_by_default(self):
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="unrelated-current-state", tier="HOT", relevant=False)],
        )
        self.assertEqual(result["selected"]["HOT"], ())
        self.assertEqual(result["plan"], ())

    def test_warm_excluded_when_condition_not_active(self):
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="production-change-rules", tier="WARM", condition="production_change")],
        )
        self.assertEqual(result["selected"]["WARM"], ())

    def test_warm_included_when_condition_active(self):
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="production-change-rules", tier="WARM", condition="production_change")],
            active_conditions=("production_change",),
        )
        self.assertEqual(result["selected"]["WARM"], ("production-change-rules",))
        self.assertEqual(result["plan"], ("production-change-rules",))

    def test_warm_without_condition_never_fires_by_default(self):
        # A WARM candidate with no declared condition has nothing that can
        # require it, so it must never be selected -- even with unrelated
        # active_conditions supplied.
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="historical-rationale", tier="WARM", condition=None)],
            active_conditions=("production_change",),
        )
        self.assertEqual(result["selected"]["WARM"], ())

    def test_cold_excluded_even_when_relevant(self):
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="old-archive", tier="COLD", relevant=True)],
            active_conditions=("production_change",),
        )
        self.assertEqual(result["selected"]["COLD"], ())

    def test_cold_included_via_explicit_source(self):
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="user-designated-doc", tier="COLD", explicit_source=True)],
        )
        self.assertEqual(result["selected"]["COLD"], ("user-designated-doc",))
        self.assertEqual(result["plan"], ("user-designated-doc",))

    def test_cold_included_via_explicitly_required_without_explicit_source(self):
        # explicitly_required is an independent task-necessity signal: it
        # must select COLD context on its own, with no Source Read Gate
        # designation (explicit_source stays False/default).
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="old-migration-log", tier="COLD", explicitly_required=True)],
        )
        self.assertEqual(result["selected"]["COLD"], ("old-migration-log",))
        self.assertEqual(result["plan"], ("old-migration-log",))

    def test_cold_excluded_when_neither_flag_set(self):
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="old-archive", tier="COLD")],
        )
        self.assertEqual(result["selected"]["COLD"], ())

    def test_cold_included_when_both_flags_set(self):
        result = select_context(
            {"state": "RESOLVED"},
            [
                ContextCandidate(
                    id="both-flags",
                    tier="COLD",
                    explicit_source=True,
                    explicitly_required=True,
                )
            ],
        )
        self.assertEqual(result["selected"]["COLD"], ("both-flags",))

    def test_explicitly_required_has_no_effect_on_hot_or_warm(self):
        # explicitly_required only lifts the COLD default; HOT and WARM
        # already have their own explicit selection mechanisms and must
        # not be affected by this independent signal.
        result = select_context(
            {"state": "RESOLVED"},
            [
                ContextCandidate(
                    id="hot-but-irrelevant",
                    tier="HOT",
                    relevant=False,
                    explicitly_required=True,
                ),
                ContextCandidate(
                    id="warm-condition-not-active",
                    tier="WARM",
                    condition="production_change",
                    explicitly_required=True,
                ),
            ],
        )
        self.assertEqual(result["selected"]["HOT"], ())
        self.assertEqual(result["selected"]["WARM"], ())

    def test_explicit_source_overrides_hot_relevance_and_warm_condition(self):
        result = select_context(
            {"state": "UNKNOWN"},
            [
                ContextCandidate(id="hot-but-irrelevant", tier="HOT", relevant=False, explicit_source=True),
                ContextCandidate(id="warm-no-condition-met", tier="WARM", condition="permission_change", explicit_source=True),
            ],
        )
        self.assertEqual(result["selected"]["HOT"], ("hot-but-irrelevant",))
        self.assertEqual(result["selected"]["WARM"], ("warm-no-condition-met",))

    def test_safety_trigger_independent_of_resolution_state(self):
        # ARCHITECTURE.md step 3: a safety trigger must still fire when the
        # resolution state is UNKNOWN/CONFLICT/VERIFY. Selection here must
        # not branch on `resolution` at all.
        candidates = [ContextCandidate(id="permission-change-rules", tier="WARM", condition="permission_change")]
        for resolution_state in ({"state": "UNKNOWN"}, {"state": "CONFLICT"}, {"state": "VERIFY"}, None):
            result = select_context(resolution_state, candidates, active_conditions=("permission_change",))
            self.assertEqual(result["selected"]["WARM"], ("permission-change-rules",))

    def test_plan_order_is_hot_then_warm_then_cold_and_deterministic(self):
        candidates = [
            ContextCandidate(id="cold-explicit", tier="COLD", explicit_source=True),
            ContextCandidate(id="warm-active", tier="WARM", condition="production_change"),
            ContextCandidate(id="hot-1", tier="HOT", relevant=True),
            ContextCandidate(id="hot-2", tier="HOT", relevant=True),
        ]
        first = select_context({"state": "RESOLVED"}, candidates, active_conditions=("production_change",))
        second = select_context({"state": "RESOLVED"}, candidates, active_conditions=("production_change",))
        expected_plan = ("hot-1", "hot-2", "warm-active", "cold-explicit")
        self.assertEqual(first["plan"], expected_plan)
        self.assertEqual(second["plan"], expected_plan)

    def test_resolution_is_passed_through_unchanged_for_traceability(self):
        resolution = {"state": "RESOLVED", "record": {"decision_id": "PRICE-002"}}
        result = select_context(resolution, [])
        self.assertEqual(result["resolution"], resolution)

    def test_duplicate_id_is_data_error(self):
        result = select_context(
            {"state": "RESOLVED"},
            [
                ContextCandidate(id="dup", tier="HOT", relevant=True),
                ContextCandidate(id="dup", tier="WARM", condition="x"),
            ],
        )
        self.assertEqual(result["stage"], "context_selection")
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("duplicate candidate id: dup", result["errors"])

    def test_unknown_tier_is_data_error(self):
        result = select_context(
            {"state": "RESOLVED"},
            [ContextCandidate(id="mystery", tier="LUKEWARM", relevant=True)],
        )
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("unknown tier for mystery: LUKEWARM", result["errors"])

    def test_empty_candidates_selects_nothing(self):
        result = select_context({"state": "RESOLVED"}, [])
        self.assertEqual(result["state"], "SELECTED")
        self.assertEqual(result["plan"], ())
        self.assertEqual(result["selected"], {"HOT": (), "WARM": (), "COLD": ()})


if __name__ == "__main__":
    unittest.main()
