from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from source_read_observation import ObservationRequest, observe  # noqa: E402
from source_read_evidence import SourceReadEvidence, derive_evidence  # noqa: E402


class TestSourceReadEvidence(unittest.TestCase):
    def test_valid_request_is_evidenced(self):
        request = ObservationRequest(
            source_id="repo:example/file.py",
            source_version="deadbeef",
            raw_payload=b"hello world",
        )
        result = derive_evidence(request)
        self.assertEqual(result["state"], "EVIDENCED")
        evidence = result["evidence"]
        self.assertIsInstance(evidence, SourceReadEvidence)
        self.assertEqual(evidence.source_id, "repo:example/file.py")

    def test_evidence_hashes_match_a_fresh_observe_call(self):
        request = ObservationRequest(
            source_id="doc:spec.md", source_version="v3", raw_payload=b"payload"
        )
        expected = observe(request)
        result = derive_evidence(request)
        evidence = result["evidence"]
        self.assertEqual(
            evidence.source_identity_hash, expected["source_identity_hash"]
        )
        self.assertEqual(
            evidence.source_version_binding_hash,
            expected["source_version_binding_hash"],
        )
        self.assertEqual(evidence.raw_payload_hash, expected["raw_payload_hash"])

    def test_evidence_is_derived_freshly_not_cached(self):
        # Two distinct requests derived back-to-back must not leak state
        # between calls: each call's evidence must match its own request.
        first = derive_evidence(
            ObservationRequest(
                source_id="repo:a.py", source_version="v1", raw_payload=b"x"
            )
        )["evidence"]
        second = derive_evidence(
            ObservationRequest(
                source_id="repo:b.py", source_version="v1", raw_payload=b"y"
            )
        )["evidence"]
        third = derive_evidence(
            ObservationRequest(
                source_id="repo:a.py", source_version="v1", raw_payload=b"x"
            )
        )["evidence"]
        self.assertNotEqual(first.source_identity_hash, second.source_identity_hash)
        self.assertEqual(first, third)

    def test_evidence_is_deterministic(self):
        request = ObservationRequest(
            source_id="doc:spec.md", source_version="v3", raw_payload=b"payload"
        )
        self.assertEqual(derive_evidence(request), derive_evidence(request))

    def test_evidence_is_immutable(self):
        request = ObservationRequest(
            source_id="repo:file.py", source_version="v1", raw_payload=b"x"
        )
        evidence = derive_evidence(request)["evidence"]
        with self.assertRaises(Exception):
            evidence.source_id = "repo:other.py"

    def test_evidence_does_not_expose_raw_payload_or_source_version(self):
        request = ObservationRequest(
            source_id="repo:file.py",
            source_version="secret-version-marker",
            raw_payload=b"secret payload bytes",
        )
        evidence = derive_evidence(request)["evidence"]
        fields = vars(evidence)
        self.assertNotIn("raw_payload", fields)
        self.assertNotIn("source_version", fields)
        for value in fields.values():
            self.assertNotEqual(value, "secret-version-marker")
            self.assertNotEqual(value, b"secret payload bytes")

    def test_evidence_has_exactly_four_fields(self):
        request = ObservationRequest(
            source_id="repo:file.py", source_version="v1", raw_payload=b"x"
        )
        evidence = derive_evidence(request)["evidence"]
        self.assertEqual(
            set(vars(evidence).keys()),
            {
                "source_id",
                "source_identity_hash",
                "source_version_binding_hash",
                "raw_payload_hash",
            },
        )

    def test_default_request_is_data_error(self):
        result = derive_evidence(ObservationRequest())
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("source_id must be str, got NoneType", result["errors"])

    def test_none_request_is_data_error_not_raise(self):
        result = derive_evidence(None)
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("request must be ObservationRequest, got NoneType", result["errors"])
        self.assertNotIn("evidence", result)

    def test_dict_request_is_data_error_not_raise(self):
        payload = {
            "source_id": "repo:file.py",
            "source_version": "v1",
            "raw_payload": b"x",
        }
        result = derive_evidence(payload)
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("request must be ObservationRequest, got dict", result["errors"])

    def test_unrelated_object_request_is_data_error_not_raise(self):
        class Unrelated:
            source_id = "repo:file.py"
            source_version = "v1"
            raw_payload = b"x"

        result = derive_evidence(Unrelated())
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn(
            "request must be ObservationRequest, got Unrelated", result["errors"]
        )

    def test_observation_request_subclass_is_data_error_not_raise(self):
        class ObservationRequestSubclass(ObservationRequest):
            pass

        subclass_instance = ObservationRequestSubclass(
            source_id="repo:file.py", source_version="v1", raw_payload=b"x"
        )
        result = derive_evidence(subclass_instance)
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn(
            "request must be ObservationRequest, got ObservationRequestSubclass",
            result["errors"],
        )

    def test_malformed_top_level_request_does_not_touch_fields(self):
        # A request-shaped object whose field access raises must still fail
        # closed on observe()'s top-level type check before this module ever
        # reaches for .source_id to build evidence.
        class ExplodesOnFieldAccess:
            @property
            def source_id(self):
                raise AssertionError("field access must not happen")

            @property
            def source_version(self):
                raise AssertionError("field access must not happen")

            @property
            def raw_payload(self):
                raise AssertionError("field access must not happen")

        result = derive_evidence(ExplodesOnFieldAccess())
        self.assertEqual(result["state"], "DATA_ERROR")

    def test_lone_surrogate_source_id_is_data_error_not_raise(self):
        result = derive_evidence(
            ObservationRequest(
                source_id="repo:\udc80bad.py",
                source_version="v1",
                raw_payload=b"x",
            )
        )
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("source_id must be UTF-8 encodable", result["errors"])

    def test_wrong_type_raw_payload_is_data_error(self):
        for bad in ("not bytes", bytearray(b"x"), memoryview(b"x"), 42, None):
            with self.subTest(bad=bad):
                result = derive_evidence(
                    ObservationRequest(
                        source_id="repo:file.py", source_version="v1", raw_payload=bad
                    )
                )
                self.assertEqual(result["state"], "DATA_ERROR")
                self.assertNotIn("evidence", result)

    def test_no_caller_supplied_hash_is_accepted(self):
        # derive_evidence() takes only an ObservationRequest -- there is no
        # parameter through which a caller could hand it a pre-computed
        # hash in place of one observe() derives itself.
        import inspect

        signature = inspect.signature(derive_evidence)
        self.assertEqual(list(signature.parameters), ["request"])

    def test_empty_raw_payload_is_evidenced(self):
        result = derive_evidence(
            ObservationRequest(
                source_id="repo:empty.py", source_version="v1", raw_payload=b""
            )
        )
        self.assertEqual(result["state"], "EVIDENCED")


if __name__ == "__main__":
    unittest.main()
