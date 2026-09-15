import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from source_read_gate import GateRequest, evaluate  # noqa: E402
from minimal_resolver import resolve_current  # noqa: E402


class TestSourceReadGate(unittest.TestCase):
    def test_no_source_declared_is_not_applicable(self):
        result = evaluate(GateRequest())
        self.assertEqual(result["state"], "NOT_APPLICABLE")

    def test_single_source_read_passes(self):
        result = evaluate(
            GateRequest(declared_sources=("repo:file.py",), read_log=("repo:file.py",))
        )
        self.assertEqual(result["state"], "PASS")

    def test_single_source_not_yet_read_verifies(self):
        result = evaluate(GateRequest(declared_sources=("repo:file.py",)))
        self.assertEqual(result["state"], "VERIFY")
        self.assertEqual(result["reason"], "not_yet_read")
        self.assertEqual(result["missing"], ("repo:file.py",))

    def test_memory_is_not_substituted_for_a_real_read(self):
        # A source the model merely "recalls" (never in read_log) must not
        # satisfy the requirement, even if it once appeared in a prior turn.
        result = evaluate(
            GateRequest(
                declared_sources=("doc:spec.md",),
                read_log=("doc:unrelated.md",),
            )
        )
        self.assertEqual(result["state"], "VERIFY")

    def test_unavailable_required_source_fails_closed_to_unknown(self):
        result = evaluate(
            GateRequest(
                declared_sources=("repo:missing.py",),
                unavailable_sources=("repo:missing.py",),
            )
        )
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "required_source_unavailable")

    def test_and_semantics_require_every_source(self):
        request = GateRequest(
            declared_sources=("a", "b"),
            mode="ALL",
            read_log=("a",),
        )
        result = evaluate(request)
        self.assertEqual(result["state"], "VERIFY")
        self.assertEqual(result["missing"], ("b",))

        result = evaluate(
            GateRequest(declared_sources=("a", "b"), mode="ALL", read_log=("a", "b"))
        )
        self.assertEqual(result["state"], "PASS")

    def test_and_semantics_unknown_when_one_required_source_is_unavailable(self):
        # ALL mode: one unavailable required source breaks the whole
        # requirement even though the other source is fine, because ALL can
        # never be fully satisfied once any member is unreachable.
        result = evaluate(
            GateRequest(
                declared_sources=("a", "b"),
                mode="ALL",
                unavailable_sources=("b",),
            )
        )
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "required_source_unavailable")
        self.assertEqual(result["unavailable"], ("b",))

    def test_or_semantics_need_only_one_source(self):
        result = evaluate(
            GateRequest(declared_sources=("a", "b"), mode="ANY", read_log=("b",))
        )
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["satisfied"], ("b",))

    def test_or_semantics_unknown_when_all_candidates_unavailable(self):
        result = evaluate(
            GateRequest(
                declared_sources=("a", "b"),
                mode="ANY",
                unavailable_sources=("a", "b"),
            )
        )
        self.assertEqual(result["state"], "UNKNOWN")

    def test_or_semantics_verify_not_unknown_when_only_some_unavailable(self):
        # ANY mode: with one candidate still reachable, the requirement is
        # not impossible yet, so this must stay VERIFY, not UNKNOWN.
        result = evaluate(
            GateRequest(
                declared_sources=("a", "b"),
                mode="ANY",
                unavailable_sources=("a",),
            )
        )
        self.assertEqual(result["state"], "VERIFY")

    def test_no_external_read_with_existing_evidence_still_passes(self):
        # Already-present allowed evidence in read_log satisfies the
        # requirement; no_external_read blocks a *new* prohibited read, it
        # does not retract a read that already happened.
        result = evaluate(
            GateRequest(
                declared_sources=("web:page",),
                read_log=("web:page",),
                no_external_read=True,
            )
        )
        self.assertEqual(result["state"], "PASS")

    def test_no_external_read_blocks_new_retrieval_when_not_yet_read(self):
        result = evaluate(
            GateRequest(
                declared_sources=("web:page",),
                no_external_read=True,
            )
        )
        self.assertEqual(result["state"], "VERIFY")
        self.assertEqual(result["reason"], "no_external_read_constraint")
        self.assertEqual(result["missing"], ("web:page",))

    def test_no_external_read_partial_all_mode_blocks_only_the_missing_part(self):
        result = evaluate(
            GateRequest(
                declared_sources=("a", "b"),
                mode="ALL",
                read_log=("a",),
                no_external_read=True,
            )
        )
        self.assertEqual(result["state"], "VERIFY")
        self.assertEqual(result["reason"], "no_external_read_constraint")
        self.assertEqual(result["missing"], ("b",))

    def test_no_external_read_any_mode_with_existing_evidence_passes(self):
        result = evaluate(
            GateRequest(
                declared_sources=("a", "b"),
                mode="ANY",
                read_log=("b",),
                no_external_read=True,
            )
        )
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["satisfied"], ("b",))

    def test_unavailable_still_wins_over_no_external_read(self):
        # Unavailability is an absolute fact about the source, independent
        # of the read-policy constraint, so it should take precedence.
        result = evaluate(
            GateRequest(
                declared_sources=("repo:missing.py",),
                unavailable_sources=("repo:missing.py",),
                no_external_read=True,
            )
        )
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertEqual(result["reason"], "required_source_unavailable")

    def test_continuation_carries_prior_designation_forward(self):
        result = evaluate(
            GateRequest(
                continued_from_previous=True,
                previous_declared_sources=("repo:file.py",),
                previous_mode="ALL",
                read_log=("repo:file.py",),
            )
        )
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["sources"], ("repo:file.py",))

    def test_continuation_drops_when_source_changed_this_turn(self):
        result = evaluate(
            GateRequest(
                continued_from_previous=True,
                source_changed_this_turn=True,
                previous_declared_sources=("repo:file.py",),
                read_log=("repo:file.py",),
            )
        )
        self.assertEqual(result["state"], "NOT_APPLICABLE")

    def test_new_declaration_overrides_continuation(self):
        result = evaluate(
            GateRequest(
                declared_sources=("repo:new.py",),
                continued_from_previous=True,
                previous_declared_sources=("repo:old.py",),
                read_log=("repo:old.py",),
            )
        )
        self.assertEqual(result["state"], "VERIFY")
        self.assertEqual(result["missing"], ("repo:new.py",))

    def test_new_declaration_ignores_malformed_inactive_previous_mode(self):
        # A garbled previous_mode must not block a fresh, well-formed
        # declaration that supersedes it: only the effective (current)
        # requirement is validated.
        result = evaluate(
            GateRequest(
                declared_sources=("repo:new.py",),
                mode="ALL",
                previous_mode="XOR",
                previous_declared_sources=("repo:old.py",),
                read_log=("repo:new.py",),
            )
        )
        self.assertEqual(result["state"], "PASS")

    def test_dropped_continuation_ignores_malformed_previous_mode(self):
        # Once source_changed_this_turn drops the prior designation and no
        # new source is declared, the previous field set is inert; its
        # invalid mode must not surface as a data error.
        result = evaluate(
            GateRequest(
                continued_from_previous=True,
                source_changed_this_turn=True,
                previous_mode="XOR",
                previous_declared_sources=("repo:old.py",),
                read_log=("repo:old.py",),
            )
        )
        self.assertEqual(result["state"], "NOT_APPLICABLE")

    def test_current_declaration_ignores_duplicate_inactive_previous_sources(self):
        result = evaluate(
            GateRequest(
                declared_sources=("repo:new.py",),
                previous_declared_sources=("repo:old.py", "repo:old.py"),
                read_log=("repo:new.py",),
            )
        )
        self.assertEqual(result["state"], "PASS")

    def test_active_previous_mode_is_still_validated(self):
        # When continuation *is* the effective source of truth, its own
        # mode must still be checked.
        result = evaluate(
            GateRequest(
                continued_from_previous=True,
                previous_declared_sources=("repo:old.py",),
                previous_mode="XOR",
                read_log=("repo:old.py",),
            )
        )
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("unknown previous_mode: XOR", result["errors"])

    def test_bounded_retrieval_flags_extra_reads_without_blocking(self):
        result = evaluate(
            GateRequest(
                declared_sources=("repo:file.py",),
                read_log=("repo:file.py", "cold:unrelated_archive.md"),
            )
        )
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["extra_reads"], ("cold:unrelated_archive.md",))

    def test_malformed_request_reports_data_error(self):
        result = evaluate(GateRequest(declared_sources=("a",), mode="XOR"))
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("unknown mode: XOR", result["errors"])

    def test_duplicate_declared_sources_reports_data_error(self):
        result = evaluate(GateRequest(declared_sources=("a", "a")))
        self.assertEqual(result["state"], "DATA_ERROR")


class TestResolverRegression(unittest.TestCase):
    """Existing minimal_resolver behavior, re-run here as a regression guard
    so that adding the Source Read Gate module cannot silently change the
    unrelated decision-resolution contract."""

    @staticmethod
    def load():
        with open(ROOT / "reference" / "sample_decisions.json", encoding="utf-8") as f:
            return json.load(f)

    def test_current(self):
        result = resolve_current(
            self.load(), domain="demo", subject="starter", field="price", as_of="2026-08-28"
        )
        self.assertEqual(result["state"], "RESOLVED")
        self.assertEqual(result["record"]["value"], 200)

    def test_future_successor_not_early(self):
        records = self.load()
        records.append({
            "decision_id": "PRICE-003",
            "scope": {"domain": "demo", "subject": "starter", "field": "price"},
            "status": "ACTIVE",
            "effective_from": "2026-09-01",
            "supersedes": "PRICE-002",
            "last_verified": "2026-08-28",
            "value": 300,
        })
        result = resolve_current(
            records, domain="demo", subject="starter", field="price", as_of="2026-08-28"
        )
        self.assertEqual(result["state"], "RESOLVED")
        self.assertEqual(result["record"]["decision_id"], "PRICE-002")

    def test_future_successor_after_effective(self):
        records = self.load()
        records.append({
            "decision_id": "PRICE-003",
            "scope": {"domain": "demo", "subject": "starter", "field": "price"},
            "status": "ACTIVE",
            "effective_from": "2026-09-01",
            "supersedes": "PRICE-002",
            "last_verified": "2026-09-01",
            "value": 300,
        })
        result = resolve_current(
            records, domain="demo", subject="starter", field="price", as_of="2026-09-02"
        )
        self.assertEqual(result["state"], "RESOLVED")
        self.assertEqual(result["record"]["decision_id"], "PRICE-003")

    def test_unknown_field(self):
        result = resolve_current(
            self.load(), domain="demo", subject="starter", field="unknown", as_of="2026-08-28"
        )
        self.assertEqual(result["state"], "UNKNOWN")

    def test_multiple_survivors_conflict(self):
        records = self.load()
        records.append({
            "decision_id": "PRICE-X",
            "scope": {"domain": "demo", "subject": "starter", "field": "price"},
            "status": "ACTIVE",
            "effective_from": "2026-08-20",
            "last_verified": "2026-08-28",
            "value": 200,
        })
        result = resolve_current(
            records, domain="demo", subject="starter", field="price", as_of="2026-08-28"
        )
        self.assertEqual(result["state"], "CONFLICT")

    def test_dangling_fails_closed(self):
        records = self.load()
        records.append({
            "decision_id": "BROKEN",
            "scope": {"domain": "demo", "subject": "starter", "field": "price"},
            "status": "ACTIVE",
            "effective_from": "2026-08-20",
            "supersedes": "DOES-NOT-EXIST",
            "last_verified": "2026-08-28",
            "value": 1,
        })
        result = resolve_current(
            records, domain="demo", subject="starter", field="price", as_of="2026-08-28"
        )
        self.assertEqual(result["state"], "DATA_ERROR")

    def test_unrelated_scope_isolation(self):
        records = self.load() + [{
            "decision_id": "BAD",
            "scope": {"domain": "other", "subject": "x", "field": "y"},
            "status": "ACTIVE",
            "effective_from": "2026-08-20",
            "supersedes": "MISSING",
            "last_verified": "2026-08-28",
            "value": "bad",
        }]
        result = resolve_current(
            records, domain="demo", subject="starter", field="price", as_of="2026-08-28"
        )
        self.assertEqual(result["state"], "RESOLVED")


if __name__ == "__main__":
    unittest.main()
