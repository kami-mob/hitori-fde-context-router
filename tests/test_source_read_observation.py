import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from source_read_observation import (  # noqa: E402
    ObservationRequest,
    observe,
    validate_request,
)


class TestSourceReadObservation(unittest.TestCase):
    def test_valid_request_is_observed(self):
        result = observe(
            ObservationRequest(
                source_id="repo:example/file.py",
                source_version="deadbeef",
                raw_payload=b"hello world",
            )
        )
        self.assertEqual(result["state"], "OBSERVED")
        for key in (
            "source_identity_hash",
            "source_version_binding_hash",
            "raw_payload_hash",
        ):
            self.assertIn(key, result)
            self.assertEqual(len(result[key]), 64)
            int(result[key], 16)  # hex digest

    def test_observation_is_deterministic(self):
        request = ObservationRequest(
            source_id="doc:spec.md", source_version="v3", raw_payload=b"payload"
        )
        self.assertEqual(observe(request), observe(request))

    def test_identity_hash_matches_plain_sha256_of_source_id(self):
        result = observe(
            ObservationRequest(
                source_id="repo:example/file.py",
                source_version="deadbeef",
                raw_payload=b"",
            )
        )
        expected = hashlib.sha256(b"repo:example/file.py").hexdigest()
        self.assertEqual(result["source_identity_hash"], expected)

    def test_payload_hash_matches_plain_sha256_of_raw_bytes(self):
        payload = b"the exact bytes that were read"
        result = observe(
            ObservationRequest(
                source_id="repo:example/file.py",
                source_version="deadbeef",
                raw_payload=payload,
            )
        )
        self.assertEqual(result["raw_payload_hash"], hashlib.sha256(payload).hexdigest())

    def test_version_binding_hash_is_a_known_vector(self):
        # Locks the length-prefixed encoding scheme: changing it would
        # silently change every previously-recorded binding hash.
        source_id = "repo:example/file.py"
        source_version = "deadbeef"
        expected = hashlib.sha256(
            f"{len(source_id.encode('utf-8'))}:".encode("ascii")
            + source_id.encode("utf-8")
            + f"{len(source_version.encode('utf-8'))}:".encode("ascii")
            + source_version.encode("utf-8")
        ).hexdigest()

        result = observe(
            ObservationRequest(
                source_id=source_id, source_version=source_version, raw_payload=b""
            )
        )
        self.assertEqual(result["source_version_binding_hash"], expected)

    def test_empty_raw_payload_is_allowed(self):
        result = observe(
            ObservationRequest(
                source_id="repo:empty.py", source_version="v1", raw_payload=b""
            )
        )
        self.assertEqual(result["state"], "OBSERVED")
        self.assertEqual(result["raw_payload_hash"], hashlib.sha256(b"").hexdigest())

    def test_version_binding_hash_changes_when_version_changes(self):
        base = ObservationRequest(
            source_id="repo:file.py", source_version="v1", raw_payload=b"x"
        )
        bumped = ObservationRequest(
            source_id="repo:file.py", source_version="v2", raw_payload=b"x"
        )
        result_base = observe(base)
        result_bumped = observe(bumped)
        self.assertEqual(
            result_base["source_identity_hash"], result_bumped["source_identity_hash"]
        )
        self.assertNotEqual(
            result_base["source_version_binding_hash"],
            result_bumped["source_version_binding_hash"],
        )

    def test_version_binding_hash_changes_when_identity_changes(self):
        first = observe(
            ObservationRequest(
                source_id="repo:a.py", source_version="v1", raw_payload=b"x"
            )
        )
        second = observe(
            ObservationRequest(
                source_id="repo:b.py", source_version="v1", raw_payload=b"x"
            )
        )
        self.assertNotEqual(
            first["source_version_binding_hash"], second["source_version_binding_hash"]
        )

    def test_no_concatenation_ambiguity_between_id_and_version(self):
        # ("ab", "c") and ("a", "bc") must not collide despite identical
        # naive concatenation ("abc").
        first = observe(
            ObservationRequest(source_id="ab", source_version="c", raw_payload=b"")
        )
        second = observe(
            ObservationRequest(source_id="a", source_version="bc", raw_payload=b"")
        )
        self.assertNotEqual(
            first["source_version_binding_hash"], second["source_version_binding_hash"]
        )

    def test_default_request_is_data_error(self):
        result = observe(ObservationRequest())
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("source_id must be str, got NoneType", result["errors"])
        self.assertIn("source_version must be str, got NoneType", result["errors"])
        self.assertIn("raw_payload must be bytes, got NoneType", result["errors"])

    def test_empty_source_id_is_data_error(self):
        result = observe(
            ObservationRequest(source_id="", source_version="v1", raw_payload=b"x")
        )
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("source_id must not be empty", result["errors"])

    def test_empty_source_version_is_data_error(self):
        result = observe(
            ObservationRequest(
                source_id="repo:file.py", source_version="", raw_payload=b"x"
            )
        )
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("source_version must not be empty", result["errors"])

    def test_wrong_type_source_id_is_data_error(self):
        for bad in (123, b"repo:file.py", None, 1.5):
            with self.subTest(bad=bad):
                result = observe(
                    ObservationRequest(
                        source_id=bad, source_version="v1", raw_payload=b"x"
                    )
                )
                self.assertEqual(result["state"], "DATA_ERROR")

    def test_wrong_type_raw_payload_is_data_error(self):
        for bad in ("not bytes", bytearray(b"x"), memoryview(b"x"), 42, None):
            with self.subTest(bad=bad):
                result = observe(
                    ObservationRequest(
                        source_id="repo:file.py", source_version="v1", raw_payload=bad
                    )
                )
                self.assertEqual(result["state"], "DATA_ERROR")

    def test_bool_is_not_accepted_in_place_of_str_or_bytes(self):
        # bool is an int subclass; exact-type checks must still reject it.
        result = observe(
            ObservationRequest(source_id=True, source_version="v1", raw_payload=b"x")
        )
        self.assertEqual(result["state"], "DATA_ERROR")

    def test_str_subclass_is_rejected_by_exact_type_check(self):
        class LoudStr(str):
            pass

        result = observe(
            ObservationRequest(
                source_id=LoudStr("repo:file.py"),
                source_version="v1",
                raw_payload=b"x",
            )
        )
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("source_id must be str, got LoudStr", result["errors"])

    def test_multiple_errors_are_collected_at_once(self):
        errors = validate_request(
            ObservationRequest(source_id=1, source_version=2, raw_payload="x")
        )
        self.assertEqual(len(errors), 3)

    def test_no_hashes_are_computed_on_data_error(self):
        result = observe(ObservationRequest())
        self.assertNotIn("source_identity_hash", result)
        self.assertNotIn("source_version_binding_hash", result)
        self.assertNotIn("raw_payload_hash", result)

    # -- Malformed top-level request objects must fail closed, not raise --

    def test_none_request_is_data_error_not_raise(self):
        result = observe(None)
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("request must be ObservationRequest, got NoneType", result["errors"])

    def test_dict_request_is_data_error_not_raise(self):
        payload = {
            "source_id": "repo:file.py",
            "source_version": "v1",
            "raw_payload": b"x",
        }
        result = observe(payload)
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("request must be ObservationRequest, got dict", result["errors"])

    def test_unrelated_object_request_is_data_error_not_raise(self):
        class Unrelated:
            source_id = "repo:file.py"
            source_version = "v1"
            raw_payload = b"x"

        result = observe(Unrelated())
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("request must be ObservationRequest, got Unrelated", result["errors"])

    def test_observation_request_subclass_is_data_error_not_raise(self):
        class ObservationRequestSubclass(ObservationRequest):
            pass

        subclass_instance = ObservationRequestSubclass(
            source_id="repo:file.py", source_version="v1", raw_payload=b"x"
        )
        result = observe(subclass_instance)
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn(
            "request must be ObservationRequest, got ObservationRequestSubclass",
            result["errors"],
        )

    def test_string_request_is_data_error_not_raise(self):
        result = observe("not a request")
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("request must be ObservationRequest, got str", result["errors"])

    def test_malformed_top_level_request_produces_no_hashes(self):
        for bad in (None, {}, object(), "nope", 7):
            with self.subTest(bad=bad):
                result = observe(bad)
                self.assertEqual(result["state"], "DATA_ERROR")
                self.assertNotIn("source_identity_hash", result)
                self.assertNotIn("source_version_binding_hash", result)
                self.assertNotIn("raw_payload_hash", result)

    def test_malformed_top_level_request_does_not_touch_fields(self):
        # A request-shaped object whose field access raises must still
        # fail closed on the top-level type check before any field is
        # ever read.
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

        result = observe(ExplodesOnFieldAccess())
        self.assertEqual(result["state"], "DATA_ERROR")

    def test_validate_request_top_level_check_matches_observe(self):
        for bad in (None, {}, object(), "nope", 7):
            with self.subTest(bad=bad):
                errors = validate_request(bad)
                self.assertEqual(len(errors), 1)
                self.assertIn("request must be ObservationRequest, got", errors[0])

    # -- Malformed Unicode (lone surrogates) must fail closed, not raise --

    def test_lone_surrogate_source_id_is_data_error_not_raise(self):
        # "\udc80" is a lone low surrogate: a syntactically valid Python
        # str (type(x) is str holds) that has no UTF-8 representation, the
        # kind of value that can appear after surrogateescape decoding of
        # non-UTF-8 bytes. This must fail closed, never raise
        # UnicodeEncodeError out of observe().
        result = observe(
            ObservationRequest(
                source_id="repo:\udc80bad.py",
                source_version="v1",
                raw_payload=b"x",
            )
        )
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("source_id must be UTF-8 encodable", result["errors"])

    def test_lone_surrogate_source_version_is_data_error_not_raise(self):
        result = observe(
            ObservationRequest(
                source_id="repo:file.py",
                source_version="v\ud800",
                raw_payload=b"x",
            )
        )
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertIn("source_version must be UTF-8 encodable", result["errors"])

    def test_lone_surrogate_in_both_fields_reports_both_errors(self):
        errors = validate_request(
            ObservationRequest(
                source_id="\udc00",
                source_version="\udfff",
                raw_payload=b"x",
            )
        )
        self.assertIn("source_id must be UTF-8 encodable", errors)
        self.assertIn("source_version must be UTF-8 encodable", errors)
        self.assertEqual(len(errors), 2)

    def test_lone_surrogate_produces_no_hashes(self):
        result = observe(
            ObservationRequest(
                source_id="\ud800", source_version="v1", raw_payload=b"x"
            )
        )
        self.assertEqual(result["state"], "DATA_ERROR")
        self.assertNotIn("source_identity_hash", result)
        self.assertNotIn("source_version_binding_hash", result)
        self.assertNotIn("raw_payload_hash", result)

    def test_surrogate_pair_forming_valid_codepoint_is_not_a_lone_surrogate(self):
        # A str built from a valid non-BMP character does not contain a
        # lone surrogate at the Python str level (Python strings are
        # sequences of code points, not UTF-16 code units), so it must
        # observe normally rather than being rejected.
        emoji = "\U0001f600"  # a single valid code point, not a surrogate
        result = observe(
            ObservationRequest(
                source_id=f"repo:{emoji}.py", source_version="v1", raw_payload=b"x"
            )
        )
        self.assertEqual(result["state"], "OBSERVED")

    # -- Valid non-ASCII input must observe and hash normally --

    def test_valid_non_ascii_source_id_is_observed(self):
        source_id = "repo:日本語/ファイル.py"  # Japanese
        result = observe(
            ObservationRequest(
                source_id=source_id, source_version="v1", raw_payload=b"x"
            )
        )
        self.assertEqual(result["state"], "OBSERVED")
        self.assertEqual(
            result["source_identity_hash"],
            hashlib.sha256(source_id.encode("utf-8")).hexdigest(),
        )

    def test_valid_non_ascii_source_version_is_observed(self):
        source_version = "révision-été"  # accented Latin
        result = observe(
            ObservationRequest(
                source_id="repo:file.py",
                source_version=source_version,
                raw_payload=b"x",
            )
        )
        self.assertEqual(result["state"], "OBSERVED")

    def test_valid_non_ascii_round_trips_to_known_vector(self):
        source_id = "über/été.md"
        source_version = "\U0001f600-v2"
        expected = hashlib.sha256(
            f"{len(source_id.encode('utf-8'))}:".encode("ascii")
            + source_id.encode("utf-8")
            + f"{len(source_version.encode('utf-8'))}:".encode("ascii")
            + source_version.encode("utf-8")
        ).hexdigest()

        result = observe(
            ObservationRequest(
                source_id=source_id, source_version=source_version, raw_payload=b""
            )
        )
        self.assertEqual(result["state"], "OBSERVED")
        self.assertEqual(result["source_version_binding_hash"], expected)

    def test_non_ascii_and_ascii_do_not_collide(self):
        ascii_only = observe(
            ObservationRequest(
                source_id="repo:cafe.py", source_version="v1", raw_payload=b"x"
            )
        )
        accented = observe(
            ObservationRequest(
                source_id="repo:café.py", source_version="v1", raw_payload=b"x"
            )
        )
        self.assertNotEqual(
            ascii_only["source_identity_hash"], accented["source_identity_hash"]
        )


if __name__ == "__main__":
    unittest.main()
