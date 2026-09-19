"""Adversarial, direct-entry tests for fresh Source Read Evidence Binding."""

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock
import inspect
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from source_read_observation import ObservationRequest  # noqa: E402
from source_read_evidence import SourceReadEvidence, derive_evidence  # noqa: E402
import source_read_evidence_binding as binding  # noqa: E402

BindingRequest = binding.SourceReadEvidenceBindingRequest
verify_binding = binding.verify_binding
FIELDS = (
    "source_id",
    "source_identity_hash",
    "source_version_binding_hash",
    "raw_payload_hash",
)
ERROR = {"state": "DATA_ERROR"}
MATCHED = {"state": "BINDING_MATCHED"}


def observed():
    return ObservationRequest(
        source_id="repo:example/file.py", source_version="v1",
        raw_payload=b"private synthetic payload"
    )


def evidence(request=None):
    return derive_evidence(request if request is not None else observed())["evidence"]


def binding_request(supplied=None, observation=None):
    return BindingRequest(
        observation_request=observation if observation is not None else observed(),
        supplied_evidence=supplied if supplied is not None else evidence(),
    )


def altered(original, field, value):
    values = {key: getattr(original, key) for key in FIELDS}
    values[field] = value
    return SourceReadEvidence(**values)


class HostileString(str):
    def __eq__(self, other):
        raise AssertionError("hostile eq must never execute")


class AlwaysEqualString(str):
    def __eq__(self, other):
        return True


class EqBomb:
    def __eq__(self, other):
        raise AssertionError("malicious eq must never execute")


class DataDescriptor:
    def __init__(self, name, value, reads, raising=False, raise_on_object=None):
        self.name = name
        self.value = value
        self.reads = reads
        self.raising = raising
        self.raise_on_object = raise_on_object

    def __get__(self, instance, owner):
        if instance is None:
            return self
        self.reads.append(self.name)
        if self.raising or instance is self.raise_on_object:
            raise AssertionError("synthetic field read exception")
        return self.value

    def __set__(self, instance, value):
        raise AttributeError("readonly synthetic descriptor")


class TestSourceReadEvidenceBinding(unittest.TestCase):
    def test_public_surface_and_frozen_wrapper(self):
        self.assertEqual(
            binding.__all__, ["SourceReadEvidenceBindingRequest", "verify_binding"]
        )
        self.assertEqual(
            list(inspect.signature(verify_binding).parameters), ["request"]
        )
        wrapper = binding_request()
        self.assertEqual(set(vars(wrapper)), {"observation_request", "supplied_evidence"})
        with self.assertRaises(FrozenInstanceError):
            wrapper.supplied_evidence = None

    def test_matching_evidence_and_exact_result(self):
        self.assertEqual(verify_binding(binding_request()), MATCHED)
        self.assertEqual(set(verify_binding(binding_request())), {"state"})

    def test_fresh_derivation_happens_once_for_valid_supplied(self):
        wrapped = binding_request()
        real = binding.derive_evidence
        with mock.patch.object(binding, "derive_evidence", wraps=real) as spy:
            self.assertEqual(verify_binding(wrapped), MATCHED)
            spy.assert_called_once_with(wrapped.observation_request)

    def test_valid_supplied_stale_or_changed_read_is_generic_error(self):
        for request in (
            ObservationRequest("repo:other", "v1", b"private synthetic payload"),
            ObservationRequest("repo:example/file.py", "v2", b"private synthetic payload"),
            ObservationRequest("repo:example/file.py", "v1", b"different payload"),
        ):
            with self.subTest(request=request):
                self.assertEqual(
                    verify_binding(BindingRequest(request, evidence())),
                    ERROR
                )

    def test_each_supplied_field_mismatch_is_generic_error(self):
        original = evidence()
        for field in FIELDS:
            with self.subTest(field=field):
                wrong = altered(original, field, "unmatched synthetic value")
                self.assertEqual(verify_binding(binding_request(wrong)), ERROR)

    def test_invalid_top_level_types_rejected_without_derive(self):
        class Subclass(BindingRequest):
            pass

        class Shaped:
            observation_request = observed()
            supplied_evidence = evidence()

        for value in (None, {}, [], object(), Shaped(), Subclass(observed(), evidence())):
            with self.subTest(kind=type(value).__name__):
                with mock.patch.object(binding, "derive_evidence") as spy:
                    self.assertEqual(verify_binding(value), ERROR)
                    spy.assert_not_called()

    def test_malformed_exact_wrapper_never_derives(self):
        malformed = object.__new__(BindingRequest)
        with mock.patch.object(binding, "derive_evidence") as spy:
            self.assertEqual(verify_binding(malformed), ERROR)
            spy.assert_not_called()

    def test_wrapper_both_fields_attempted_when_one_raises(self):
        for failing in ("observation_request", "supplied_evidence"):
            with self.subTest(failing=failing):
                original = binding_request()
                reads = []
                descriptors = [
                    mock.patch.object(
                        BindingRequest,
                        field,
                        DataDescriptor(
                            field, getattr(original, field), reads, field == failing
                        ),
                        create=True,
                    ) for field in ("observation_request", "supplied_evidence")
                ]
                with descriptors[0], descriptors[1]:
                    with mock.patch.object(binding, "derive_evidence") as spy:
                        self.assertEqual(verify_binding(original), ERROR)
                        spy.assert_not_called()
                self.assertEqual(
                    reads, ["observation_request", "supplied_evidence"]
                )

    def test_wrong_supplied_top_level_type_skips_derivation(self):
        class Shaped:
            pass

        class Subclass(SourceReadEvidence):
            pass

        good = evidence()
        shaped = Shaped()
        for name in FIELDS:
            setattr(shaped, name, getattr(good, name))
        sub = Subclass(*(getattr(good, name) for name in FIELDS))
        for wrong in (None, {}, shaped, sub, object()):
            with self.subTest(kind=type(wrong).__name__):
                with mock.patch.object(binding, "derive_evidence") as spy:
                    self.assertEqual(verify_binding(BindingRequest(observed(), wrong)), ERROR)
                    spy.assert_not_called()

    def test_malformed_exact_supplied_evidence_does_not_derive(self):
        malformed = object.__new__(SourceReadEvidence)
        with mock.patch.object(binding, "derive_evidence") as spy:
            self.assertEqual(verify_binding(binding_request(malformed)), ERROR)
            spy.assert_not_called()

    def test_supplied_wrong_type_and_equality_traps_skip_derive(self):
        base = evidence()
        for field in FIELDS:
            for wrong in (None, 42, b"raw", HostileString("x"), AlwaysEqualString("x"), EqBomb()):
                with self.subTest(field=field, wrong=type(wrong).__name__):
                    with mock.patch.object(binding, "derive_evidence") as spy:
                        self.assertEqual(
                            verify_binding(binding_request(altered(base, field, wrong))),
                            ERROR
                        )
                        spy.assert_not_called()

    def test_supplied_missing_raising_descriptor_all_fields_read_once(self):
        base = evidence()
        for failing in FIELDS:
            with self.subTest(failing=failing):
                reads = []
                patchers = [
                    mock.patch.object(
                        SourceReadEvidence, field,
                        DataDescriptor(field, getattr(base, field), reads, field == failing),
                        create=True
                    ) for field in FIELDS
                ]
                with patchers[0], patchers[1], patchers[2], patchers[3]:
                    with mock.patch.object(binding, "derive_evidence") as spy:
                        self.assertEqual(verify_binding(binding_request(base)), ERROR)
                        spy.assert_not_called()
                self.assertEqual(reads, list(FIELDS))

    def test_supplied_all_fields_read_once_before_type_validation(self):
        base = evidence()
        reads = []
        patchers = [
            mock.patch.object(
                SourceReadEvidence, field,
                DataDescriptor(
                    field, 123 if field == "source_identity_hash" else getattr(base, field),
                    reads,
                ),
                create=True,
            ) for field in FIELDS
        ]
        with patchers[0], patchers[1], patchers[2], patchers[3]:
            with mock.patch.object(binding, "derive_evidence") as spy:
                self.assertEqual(verify_binding(binding_request(base)), ERROR)
                spy.assert_not_called()
        self.assertEqual(reads, list(FIELDS))

    def test_missing_raising_fresh_field_is_generic_error(self):
        good = evidence()
        wrapped = binding_request(good)
        malformed = object.__new__(SourceReadEvidence)
        with mock.patch.object(
            binding, "derive_evidence",
            return_value={"state": "EVIDENCED", "evidence": malformed},
        ) as spy:
            self.assertEqual(verify_binding(wrapped), ERROR)
            spy.assert_called_once()
        for failing in FIELDS:
            with self.subTest(failing=failing):
                reads = []
                fresh = SourceReadEvidence(*(getattr(good, field) for field in FIELDS))
                self.assertIsNot(fresh, good)
                patchers = [
                    mock.patch.object(
                        SourceReadEvidence, field,
                        DataDescriptor(
                            field, getattr(good, field), reads,
                            raise_on_object=fresh if field == failing else None,
                        ),
                        create=True,
                    ) for field in FIELDS
                ]
                with patchers[0], patchers[1], patchers[2], patchers[3]:
                    with mock.patch.object(
                        binding, "derive_evidence",
                        return_value={"state": "EVIDENCED", "evidence": fresh},
                    ) as spy:
                        self.assertEqual(verify_binding(wrapped), ERROR)
                        spy.assert_called_once()
                self.assertEqual(reads, list(FIELDS) + list(FIELDS))

    def test_malformed_fresh_field_types_are_generic_error(self):
        base = evidence()
        for field in FIELDS:
            for wrong in (123, None, HostileString("x"), AlwaysEqualString("x"), EqBomb()):
                with self.subTest(field=field, kind=type(wrong).__name__):
                    fresh = altered(base, field, wrong)
                    with mock.patch.object(
                        binding, "derive_evidence",
                        return_value={"state": "EVIDENCED", "evidence": fresh},
                    ) as spy:
                        self.assertEqual(verify_binding(binding_request(base)), ERROR)
                        spy.assert_called_once()

    def test_wrong_derive_result_never_leaks(self):
        base = evidence()
        class Subclass(SourceReadEvidence):
            pass
        sub = Subclass(*(getattr(base, name) for name in FIELDS))
        for value in (
            None, {}, [], "EVIDENCED", {"state": "BOUND", "evidence": base},
            {"state": "EVIDENCED"}, {"state": 123, "evidence": base},
            {"state": HostileString("EVIDENCED"), "evidence": base},
            {"state": "EVIDENCED", "evidence": None},
            {"state": "EVIDENCED", "evidence": sub},
        ):
            with self.subTest(kind=repr(type(value))):
                with mock.patch.object(binding, "derive_evidence", return_value=value) as spy:
                    self.assertEqual(verify_binding(binding_request(base)), ERROR)
                    spy.assert_called_once()

    def test_derive_exception_is_generic_error(self):
        for exc in (ValueError("private payload"), RuntimeError("private version")):
            with self.subTest(kind=type(exc).__name__):
                with mock.patch.object(binding, "derive_evidence", side_effect=exc) as spy:
                    self.assertEqual(verify_binding(binding_request()), ERROR)
                    spy.assert_called_once()

    def test_invalid_observation_is_generic_error(self):
        for bad in (None, {}, ObservationRequest(), object()):
            with self.subTest(kind=type(bad).__name__):
                base = evidence()
                self.assertEqual(verify_binding(BindingRequest(bad, base)), ERROR)

    def test_no_gate_or_io_imports(self):
        import ast
        source = (ROOT / "reference" / "source_read_evidence_binding.py").read_text()
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertFalse(
            imported & {"os", "pathlib", "requests", "socket", "subprocess",
                        "source_read_gate", "time", "datetime"}
        )
        self.assertNotIn("source_read_gate", binding.__dict__)

    def test_generic_results_contain_no_private_details(self):
        secret = "synthetic-confidential-token"
        bad = altered(evidence(), "source_id", secret)
        result = verify_binding(binding_request(bad))
        self.assertEqual(result, ERROR)
        self.assertNotIn(secret, repr(result))
        self.assertEqual(set(result), {"state"})


if __name__ == "__main__":
    unittest.main()
