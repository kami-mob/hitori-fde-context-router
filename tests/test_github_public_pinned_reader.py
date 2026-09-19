"""Synthetic no-network tests for pinned, public-only GitHub Contents reads."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import urlsplit, parse_qs
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from github_public_pinned_reader import (  # noqa: E402
    PinnedPublicGitHubReader, PublicReadError, MAX_RESPONSE, MAX_CONTENT,
)
from source_read_acquisition_handoff import (  # noqa: E402
    AcquisitionRequest, acquire_declared_sources, FetchedSource,
)

SHA = "a" * 40
OWNER = "fiction-lab"
REPO = "demo-docs"
PATH = "docs/fiction.txt"
OTHER = "docs/second.txt"
ID = f"github:{OWNER}/{REPO}:{PATH}"


class Response:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, n):
        self.calls.append(n)
        return self.body[:n]


def blob(raw):
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw
    ).hexdigest()


def payload(raw=b"synthetic document bytes", path=PATH, **changes):
    item = {
        "type": "file",
        "encoding": "base64",
        "path": path,
        "size": len(raw),
        "sha": blob(raw),
        "content": base64.b64encode(raw).decode("ascii"),
    }
    item.update(changes)
    return json.dumps(item).encode("utf-8")


def reader(response=None, *, paths=(PATH,), calls=None):
    def transport(request, timeout):
        if calls is not None:
            calls.append((request, timeout))
        return response or Response(payload())
    return PinnedPublicGitHubReader(OWNER, REPO, SHA, paths, transport)


class TestPublicPinnedGitHubReader(unittest.TestCase):
    def test_exact_pinned_https_get_and_sha_checked_receipt(self):
        calls = []
        response = Response(payload())
        got = reader(response, calls=calls)(ID)
        self.assertEqual(type(got), FetchedSource)
        self.assertEqual((got.source_id, got.source_version, got.raw_payload),
                         (ID, SHA, b"synthetic document bytes"))
        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        url = urlsplit(request.full_url)
        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.netloc, "api.github.com")
        self.assertEqual(
            url.path, f"/repos/{OWNER}/{REPO}/contents/{PATH}"
        )
        self.assertEqual(parse_qs(url.query), {"ref": [SHA]})
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(timeout, 5)
        self.assertEqual(response.calls, [MAX_RESPONSE + 1])
        self.assertNotIn("Authorization", request.headers)

    def test_hand_off_actual_adapter_to_existing_gate_without_raw_return(self):
        calls = []
        response = Response(payload())
        result = acquire_declared_sources(
            AcquisitionRequest((ID,)), reader(response, calls=calls),
        )
        self.assertEqual(result, {
            "state": "PASS", "stage": "local_source_read_gate",
            "evidence_scope": "CALLER_SUPPLIED_ADAPTER", "read_count": 1,
        })
        self.assertEqual(len(calls), 1)
        self.assertNotIn("document", repr(result))
        self.assertNotIn(PATH, repr(result))

    def test_adapter_cannot_read_source_not_explicitly_allowed(self):
        calls = []
        instance = reader(calls=calls)
        for source in (
            f"github:{OWNER}/{REPO}:{OTHER}",
            "github:another/demo-docs:docs/fiction.txt",
            f"github:{OWNER}/other-repo:{PATH}",
            ID + "?token=secret",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(PublicReadError, "source_read_failed"):
                    instance(source)
        self.assertEqual(calls, [])

    def test_reject_malformed_config_before_any_network(self):
        bad_configs = (
            {"owner": "fiction-lab/../bad"},
            {"owner": ".."},
            {"repository": "demo docs"},
            {"repository": ".."},
            {"commit_sha": "main"},
            {"commit_sha": "F" * 40},
            {"allowed_paths": ()},
            {"allowed_paths": [PATH]},
            {"allowed_paths": (PATH, PATH)},
            {"allowed_paths": ("../secret",)},
            {"allowed_paths": ("/root",)},
            {"allowed_paths": ("docs//file",)},
            {"allowed_paths": ("docs/./file",)},
            {"allowed_paths": ("docs/../file",)},
            {"allowed_paths": ("docs/file?ref=main",)},
            {"_transport": object()},
        )
        base = dict(owner=OWNER, repository=REPO, commit_sha=SHA,
                    allowed_paths=(PATH,), _transport=lambda req, timeout: Response(payload()))
        for case in bad_configs:
            with self.subTest(case=repr(case)[:60]):
                with self.assertRaises(PublicReadError):
                    PinnedPublicGitHubReader(**{**base, **case})

    def test_reject_wrong_http_status_with_non_disclosing_error(self):
        for status in (301, 302, 401, 403, 404, 429, 500):
            with self.subTest(status=status):
                with self.assertRaisesRegex(PublicReadError, "^source_read_failed$"):
                    reader(Response(payload(), status))(ID)

    def test_reject_payload_shape_corruption(self):
        cases = (
            payload(type="dir"),
            payload(encoding="none"),
            payload(path="private/unknown"),
            payload(size="13"),
            payload(size=True),
            payload(size=MAX_CONTENT + 1),
            payload(sha="b" * 40),
            payload(sha="invalid"),
            payload(content="***"),
            payload(content="QUJD", size=2, sha=blob(b"ABC")),
            b"null", b"[]", b"{broken", b"not json", b"\xff",
        )
        for case in cases:
            with self.subTest(payload_size=len(case)):
                with self.assertRaisesRegex(PublicReadError, "^source_read_failed$"):
                    reader(Response(case))(ID)

    def test_bounded_http_body_rejects_oversized_payload(self):
        with self.assertRaisesRegex(PublicReadError, "^source_read_failed$"):
            reader(Response(b"x" * (MAX_RESPONSE + 1)))(ID)

    def test_max_size_empty_and_base64_linebreak_roundtrip(self):
        for raw in (b"", b"Z" * MAX_CONTENT):
            with self.subTest(length=len(raw)):
                encoded = base64.b64encode(raw).decode("ascii")
                data = payload(raw, content="\n".join(
                    encoded[j:j+70] for j in range(0, len(encoded), 70)
                ))
                # The API's base64 linebreaks are insignificant. An actual
                # unencoded payload over the limit is rejected above.
                self.assertEqual(reader(Response(data))(ID).raw_payload, raw)

    def test_timeout_or_transport_error_yields_verify_via_handoff(self):
        for exception in (TimeoutError("secret request"), OSError("private details")):
            calls = []
            def transport(request, timeout):
                calls.append(request.full_url)
                raise exception
            adapter = PinnedPublicGitHubReader(OWNER, REPO, SHA, (PATH,), transport)
            self.assertEqual(
                acquire_declared_sources(AcquisitionRequest((ID,)), adapter),
                {"state":"VERIFY", "stage":"acquisition"},
            )
            self.assertEqual(len(calls), 1)

    def test_no_external_read_stops_before_adapter_network(self):
        calls = []
        adapter = reader(calls=calls)
        self.assertEqual(
            acquire_declared_sources(AcquisitionRequest((ID,), no_external_read=True), adapter),
            {"state":"VERIFY", "stage":"acquisition"},
        )
        self.assertEqual(calls, [])

    def test_callback_errors_never_expose_returned_http_text(self):
        secret = b"very-private-synthetic-body"
        result = acquire_declared_sources(
            AcquisitionRequest((ID,)), reader(Response(secret)),
        )
        self.assertEqual(result, {"state":"VERIFY", "stage":"acquisition"})
        self.assertNotIn(secret.decode(), repr(result))

    def test_no_custom_authorization_or_base_url(self):
        fields = set(PinnedPublicGitHubReader.__dataclass_fields__)
        self.assertEqual(
            fields, {"owner", "repository", "commit_sha", "allowed_paths", "_transport"},
        )


if __name__ == "__main__":
    unittest.main()
