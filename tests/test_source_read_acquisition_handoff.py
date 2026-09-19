"""Synthetic tests for adapter-fed Source Read acquisition; no real external I/O."""
from pathlib import Path
from unittest import mock
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

import source_read_acquisition_handoff as handoff  # noqa: E402

Request = handoff.AcquisitionRequest
Receipt = handoff.FetchedSource
acquire = handoff.acquire_declared_sources
PASS = {"state": "PASS", "stage": "local_source_read_gate",
        "evidence_scope": "CALLER_SUPPLIED_ADAPTER", "read_count": 1}
ERROR = {"state": "DATA_ERROR", "stage": "acquisition"}
VERIFY = {"state": "VERIFY", "stage": "acquisition"}


def receipt(source="synthetic:a", rev="commit-1", payload=b"fictional"):
    return Receipt(source, rev, payload)


def reader(log, **overrides):
    def get(source):
        log.append(source)
        return overrides.get(source, receipt(source))
    return get


class TestAcquisitionHandoff(unittest.TestCase):
    def test_single_read_is_locally_passed_without_payload_disclosure(self):
        calls = []
        result = acquire(Request(("synthetic:a",)), reader(calls))
        self.assertEqual(result, PASS)
        self.assertEqual(calls, ["synthetic:a"])
        self.assertNotIn("fictional", repr(result))
        self.assertNotIn("synthetic:a", repr(result))
        self.assertNotIn("commit-1", repr(result))

    def test_all_reads_exactly_declared_sources(self):
        calls = []
        result = acquire(Request(("synthetic:a", "synthetic:b"), "ALL"), reader(calls))
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["read_count"], 2)
        self.assertEqual(calls, ["synthetic:a", "synthetic:b"])

    def test_any_stops_after_first_success(self):
        calls = []
        result = acquire(Request(("synthetic:a", "synthetic:b"), "ANY"), reader(calls))
        self.assertEqual(result, PASS)
        self.assertEqual(calls, ["synthetic:a"])

    def test_no_external_read_never_calls_adapter_even_for_any(self):
        for mode in ("ALL", "ANY"):
            with self.subTest(mode=mode):
                adapter = mock.Mock(side_effect=AssertionError("adapter called"))
                self.assertEqual(acquire(Request(("synthetic:a",), mode, True), adapter), VERIFY)
                adapter.assert_not_called()

    def test_malformed_requests_never_call_adapter(self):
        class Subclass(Request):
            pass
        cases = (
            None, {}, object(), Subclass(("synthetic:a",)),
            Request(), Request(["synthetic:a"]), Request(("synthetic:a", "synthetic:a")),
            Request(("",)), Request((42,)), Request(("synthetic:a",), "XOR"),
            Request(("synthetic:a",), "ALL", 1),
            Request(("synthetic:" + chr(0xD800),)),
        )
        for case in cases:
            with self.subTest(kind=repr(type(case))):
                adapter = mock.Mock()
                expected = ERROR
                self.assertEqual(acquire(case, adapter), expected)
                adapter.assert_not_called()

    def test_missing_or_uncallable_adapter_rejected(self):
        self.assertEqual(acquire(Request(("synthetic:a",)), None), ERROR)

    def test_callback_exception_is_verify_not_unavailable_and_not_retried(self):
        fetch = mock.Mock(side_effect=RuntimeError("private credential 12345"))
        result = acquire(Request(("synthetic:a",)), fetch)
        self.assertEqual(result, VERIFY)
        self.assertNotIn("credential", repr(result))
        fetch.assert_called_once_with("synthetic:a")

    def test_all_stops_on_failed_second_read_without_retry(self):
        calls = []
        def fetch(source):
            calls.append(source)
            if source == "synthetic:b":
                raise TimeoutError("sensitive timeout details")
            return receipt(source)
        result = acquire(Request(("synthetic:a", "synthetic:b", "synthetic:c")), fetch)
        self.assertEqual(result, VERIFY)
        self.assertEqual(calls, ["synthetic:a", "synthetic:b"])

    def test_receipt_wrong_shape_or_source_id_fails_closed(self):
        class Subclass(Receipt):
            pass
        for invalid in (
            None, {}, object(), Subclass("synthetic:a", "v1", b"x"),
            receipt("synthetic:b"), receipt(source=5),
            receipt(rev=""), receipt(rev=2),
            receipt(payload=bytearray(b"x")),
        ):
            with self.subTest(kind=repr(invalid)[:60]):
                fetch = mock.Mock(return_value=invalid)
                self.assertEqual(acquire(Request(("synthetic:a",)), fetch), ERROR)
                fetch.assert_called_once()

    def test_bad_receipt_never_reaches_local_gate(self):
        with mock.patch.object(handoff, "evaluate") as gate:
            self.assertEqual(
                acquire(Request(("synthetic:a",)), lambda _: receipt("wrong")), ERROR,
            )
            gate.assert_not_called()

    def test_malformed_derivation_is_not_a_read_log_entry(self):
        with mock.patch.object(handoff, "derive_evidence", return_value={"state":"DATA_ERROR"}):
            with mock.patch.object(handoff, "evaluate") as gate:
                self.assertEqual(acquire(Request(("synthetic:a",)), lambda _: receipt()), ERROR)
                gate.assert_not_called()

    def test_binding_mismatch_never_counts_as_source_read(self):
        with mock.patch.object(
            handoff, "verify_binding", return_value={"state": "DATA_ERROR"}
        ):
            with mock.patch.object(handoff, "evaluate") as gate:
                self.assertEqual(acquire(Request(("synthetic:a",)), lambda _: receipt()), ERROR)
                gate.assert_not_called()

    def test_gate_fail_closed_cannot_be_upgraded(self):
        with mock.patch.object(handoff, "evaluate", return_value={"state": "VERIFY"}):
            self.assertEqual(acquire(Request(("synthetic:a",)), lambda _: receipt()), ERROR)

    def test_completed_reads_are_passed_to_gate_only_after_binding(self):
        seen = []
        real_evaluate = handoff.evaluate
        def capture(request):
            seen.append(request)
            return real_evaluate(request)
        with mock.patch.object(handoff, "evaluate", side_effect=capture) as spy:
            result = acquire(
                Request(("synthetic:a", "synthetic:b"), "ALL"),
                lambda src: receipt(src),
            )
        self.assertEqual(result["state"], "PASS")
        spy.assert_called_once()
        self.assertEqual(seen[0].read_log, ("synthetic:a", "synthetic:b"))
        self.assertEqual(seen[0].declared_sources, ("synthetic:a", "synthetic:b"))

    def test_exact_empty_payload_is_allowed(self):
        self.assertEqual(
            acquire(Request(("synthetic:a",)), lambda src: receipt(src, payload=b"")),
            PASS,
        )

    def test_no_untrusted_data_in_success_or_failure(self):
        secret = "fictional-but-private-secret"
        result = acquire(
            Request(("synthetic:a",)),
            lambda src: receipt(src, rev=secret, payload=secret.encode()),
        )
        self.assertEqual(result, PASS)
        self.assertNotIn(secret, repr(result))
        self.assertEqual(
            acquire(Request(("synthetic:a",)), lambda _: (_ for _ in ()).throw(
                ValueError(secret)
            )),
            VERIFY,
        )

    def test_missing_exact_receipt_attributes_fail_closed(self):
        broken = object.__new__(Receipt)
        self.assertEqual(acquire(Request(("synthetic:a",)), lambda _: broken), ERROR)


if __name__ == "__main__":
    unittest.main()
