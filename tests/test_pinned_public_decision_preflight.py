"""No-network tests of one SHA-pinned public-file read to local decision resolution."""
from pathlib import Path
import base64
import hashlib
import json
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

import pinned_public_decision_preflight as preflight  # noqa: E402
from github_public_pinned_reader import PinnedPublicGitHubReader  # noqa: E402
from source_read_acquisition_handoff import FetchedSource  # noqa: E402

OWNER = "fiction-lab"
REPOSITORY = "demo-decisions"
COMMIT = "a" * 40
PATH = "reference/demo.json"
SOURCE = f"github:{OWNER}/{REPOSITORY}:{PATH}"
RESOLVED = {
    "decision_id": "SYN-002",
    "scope": {"domain": "demo", "subject": "starter", "field": "price"},
    "status": "ACTIVE",
    "effective_from": "2026-08-01",
    "last_verified": "2026-08-28",
    "value": 200,
}
OLD = {
    "decision_id": "SYN-001",
    "scope": {"domain": "demo", "subject": "starter", "field": "price"},
    "status": "SUPERSEDED",
    "effective_from": "2026-07-01",
    "last_verified": "2026-07-15",
    "value": 100,
}
RESOLVED["supersedes"] = "SYN-001"


def blob_hash(payload):
    return hashlib.sha1(
        b"blob " + str(len(payload)).encode("ascii") + bytes([0]) + payload
    ).hexdigest()


def records_bytes(records=None):
    if records is None:
        records = [OLD, RESOLVED]
    return json.dumps(records, ensure_ascii=False).encode("utf-8")


class Response:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, length):
        return self.payload[:length]


def api_response(payload, **override):
    obj = {
        "type": "file",
        "encoding": "base64",
        "content": base64.b64encode(payload).decode("ascii"),
        "sha": blob_hash(payload),
        "size": len(payload),
        "path": PATH,
    }
    obj.update(override)
    return Response(json.dumps(obj).encode("utf-8"))


def request(payload=None, *, adapter=None, blob=None, **kwargs):
    raw = records_bytes() if payload is None else payload
    if adapter is None:
        adapter = PinnedPublicGitHubReader(
            OWNER, REPOSITORY, COMMIT, (PATH,),
            lambda req, timeout: api_response(raw),
        )
    defaults = dict(
        reader=adapter,
        source_id=SOURCE,
        expected_blob_sha=blob if blob is not None else blob_hash(raw),
        domain="demo", subject="starter", field="price", as_of="2026-08-28",
    )
    defaults.update(kwargs)
    return preflight.PinnedPublicDecisionRequest(**defaults)


class PinnedPublicDecisionPreflightTests(unittest.TestCase):
    def test_same_fetched_bytes_proceed_to_local_resolution_once(self):
        calls = []

        def transport(req, timeout):
            calls.append((req.full_url, timeout))
            return api_response(records_bytes())

        reader = PinnedPublicGitHubReader(
            OWNER, REPOSITORY, COMMIT, (PATH,), transport
        )
        result = preflight.resolve_pinned_public_decision(request(adapter=reader))
        self.assertEqual(result, {
            "state": "RESOLVED",
            "stage": "local_public_snapshot_resolution",
            "evidence_scope": "PINNED_PUBLIC_FILE_BYTES",
            "decision_id": "SYN-002",
            "value": 200,
        })
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 5)
        self.assertIn("?ref=" + COMMIT, calls[0][0])

    def test_no_external_read_prevents_all_callbacks(self):
        reader = PinnedPublicGitHubReader(
            OWNER, REPOSITORY, COMMIT, (PATH,),
            mock.Mock(side_effect=AssertionError("unexpected GET")),
        )
        self.assertEqual(
            preflight.resolve_pinned_public_decision(request(
                adapter=reader, no_external_read=True
            )),
            {"state": "VERIFY", "stage": "public_snapshot"},
        )
        reader._transport.assert_not_called()

    def test_wrong_expected_blob_does_not_resolve(self):
        with mock.patch.object(preflight, "resolve_current") as resolver:
            self.assertEqual(
                preflight.resolve_pinned_public_decision(
                    request(blob="b" * 40)
                ),
                {"state": "DATA_ERROR", "stage": "public_snapshot"},
            )
            resolver.assert_not_called()

    def test_scope_and_time_are_applied_only_to_fetched_records(self):
        self.assertEqual(
            preflight.resolve_pinned_public_decision(
                request(field="missing")
            ),
            {"state": "UNKNOWN", "stage": "local_public_snapshot_resolution"},
        )
        self.assertEqual(
            preflight.resolve_pinned_public_decision(
                request(as_of="2026-10-15", verify_after_days=30)
            ),
            {"state": "VERIFY", "stage": "local_public_snapshot_resolution"},
        )
        self.assertEqual(
            preflight.resolve_pinned_public_decision(
                request(as_of="2026-07-31")
            ),
            {"state": "UNKNOWN", "stage": "local_public_snapshot_resolution"},
        )

    def test_malformed_requests_never_invoke_network(self):
        transport = mock.Mock(side_effect=AssertionError("unexpected GET"))
        reader = PinnedPublicGitHubReader(
            OWNER, REPOSITORY, COMMIT, (PATH,), transport,
        )
        good = request(adapter=reader)
        bad = [
            None, {}, object(),
            request(adapter=reader, expected_blob_sha="main"),
            request(adapter=reader, expected_blob_sha="A" * 40),
            request(adapter=reader, source_id=SOURCE + "/other"),
            request(adapter=reader, as_of="2026-2-8"),
            request(adapter=reader, as_of="2026-02-31"),
            request(adapter=reader, verify_after_days=-1),
            request(adapter=reader, verify_after_days=True),
            request(adapter=reader, no_external_read=1),
            request(adapter=reader, domain=""),
            request(adapter=reader, field=5),
        ]
        class Subclass(preflight.PinnedPublicDecisionRequest):
            pass
        bad.append(Subclass(**vars(good)))
        for item in bad:
            with self.subTest(kind=repr(type(item))):
                self.assertEqual(
                    preflight.resolve_pinned_public_decision(item),
                    {"state": "DATA_ERROR", "stage": "public_snapshot"},
                )
        transport.assert_not_called()

    def test_invalid_json_and_structural_record_shapes_fail_closed(self):
        bad_payloads = [
            b"not-json",
            b"{}",
            b"[]",
            b'[{"decision_id":"foo","decision_id":"bar"}]',
            b"[NaN]",
            b'{"records":[]}',
            json.dumps([{"decision_id":"id","scope":None}]).encode(),
            records_bytes([RESOLVED] * 257),
            records_bytes([{"decision_id":5,"scope":RESOLVED["scope"],"status":"ACTIVE"}]),
            records_bytes([{"decision_id":"x","scope":[],"status":"ACTIVE"}]),
        ]
        for raw in bad_payloads:
            with self.subTest(kind=raw[:28]):
                self.assertEqual(
                    preflight.resolve_pinned_public_decision(request(payload=raw)),
                    {"state": "DATA_ERROR", "stage": "public_snapshot"},
                )

    def test_malicious_or_inconsistent_api_receipt_is_not_resolved(self):
        bad = api_response(records_bytes(), sha="b" * 40)
        reader = PinnedPublicGitHubReader(
            OWNER, REPOSITORY, COMMIT, (PATH,), lambda req, timeout: bad,
        )
        with mock.patch.object(preflight, "resolve_current") as resolver:
            self.assertEqual(
                preflight.resolve_pinned_public_decision(request(adapter=reader)),
                {"state": "VERIFY", "stage": "public_snapshot"},
            )
            resolver.assert_not_called()

    def test_read_callback_exception_is_verify_without_private_details(self):
        secret = "unrelated-private-secret"
        reader = PinnedPublicGitHubReader(
            OWNER, REPOSITORY, COMMIT, (PATH,),
            lambda req, timeout: (_ for _ in ()).throw(RuntimeError(secret)),
        )
        value = preflight.resolve_pinned_public_decision(request(adapter=reader))
        self.assertEqual(value, {"state": "VERIFY", "stage": "public_snapshot"})
        self.assertNotIn(secret, repr(value))

    def test_resolver_never_runs_if_local_binding_fails(self):
        with mock.patch.object(
            preflight, "acquire_declared_sources",
            return_value={"state":"DATA_ERROR", "stage":"acquisition"},
        ) as binding, mock.patch.object(
            preflight, "resolve_current"
        ) as resolver:
            self.assertEqual(
                preflight.resolve_pinned_public_decision(request()),
                {"state": "DATA_ERROR", "stage": "public_snapshot"},
            )
            binding.assert_called_once()
            resolver.assert_not_called()

    def test_resolver_conflict_is_not_silently_resolved(self):
        other = dict(RESOLVED, decision_id="SYN-003", supersedes=None)
        raw = records_bytes([OLD, RESOLVED, other])
        self.assertEqual(
            preflight.resolve_pinned_public_decision(request(payload=raw)),
            {"state": "CONFLICT", "stage": "local_public_snapshot_resolution"},
        )

    def test_unknown_or_unrecognized_resolver_outcome_never_authorizes(self):
        for state in ("PROCEED", "ACTIVE", None, 4):
            with self.subTest(state=state):
                with mock.patch.object(
                    preflight, "resolve_current", return_value={"state":state},
                ):
                    self.assertEqual(
                        preflight.resolve_pinned_public_decision(request()),
                        {"state": "DATA_ERROR", "stage": "public_snapshot"},
                    )

    def test_invalid_hostile_transport_does_not_leak_payload_or_call_twice(self):
        calls = []
        secret = "synthetic-private-string"
        def transport(req, timeout):
            calls.append(1)
            raise OSError(secret)
        reader = PinnedPublicGitHubReader(
            OWNER, REPOSITORY, COMMIT, (PATH,), transport
        )
        result = preflight.resolve_pinned_public_decision(request(adapter=reader))
        self.assertEqual(result, {"state": "VERIFY", "stage": "public_snapshot"})
        self.assertEqual(calls, [1])
        self.assertNotIn(secret, repr(result))


if __name__ == "__main__":
    unittest.main()
