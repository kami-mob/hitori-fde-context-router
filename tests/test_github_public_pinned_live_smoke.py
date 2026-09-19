"""Opt-in real HTTPS public GitHub smoke at a pinned public-only source.

This test needs outbound GitHub API access and is deliberately NOT part of
the everyday deterministic Reference Tests. It requests one public file,
never supplies a token and has no permission or production side effects.
"""
from pathlib import Path
import hashlib
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from github_public_pinned_reader import PinnedPublicGitHubReader  # noqa: E402
from source_read_acquisition_handoff import (  # noqa: E402
    AcquisitionRequest, acquire_declared_sources, FetchedSource,
)

OWNER = "kami-mob"
REPOSITORY = "hitori-fde-context-router"
COMMIT = "54f0ddc3a08c2f50118a384bd1738142584cde65"
PATH = "reference/minimal_resolver.py"
SOURCE_ID = f"github:{OWNER}/{REPOSITORY}:{PATH}"
EXPECTED_BLOB = "f27516c538a9b8a3c7c607e2833754e7c3b83611"


class PublicOnlyLiveRead(unittest.TestCase):
    def test_one_real_public_https_get_at_exact_pinned_commit(self):
        reader = PinnedPublicGitHubReader(
            OWNER, REPOSITORY, COMMIT, (PATH,)
        )
        received = reader(SOURCE_ID)  # exactly one external, public HTTPS GET
        self.assertEqual(type(received), FetchedSource)
        self.assertEqual(received.source_id, SOURCE_ID)
        self.assertEqual(received.source_version, COMMIT)
        self.assertTrue(received.raw_payload.startswith(b"from __future__"))
        actual_blob = hashlib.sha1(
            b"blob " + str(len(received.raw_payload)).encode("ascii")
            + bytes([0]) + received.raw_payload
        ).hexdigest()
        self.assertEqual(actual_blob, EXPECTED_BLOB)
        local_result = acquire_declared_sources(
            AcquisitionRequest((SOURCE_ID,)),
            lambda _: received,  # already-fetched response; no second HTTP GET
        )
        self.assertEqual(local_result, {
            "state": "PASS", "stage": "local_source_read_gate",
            "evidence_scope": "CALLER_SUPPLIED_ADAPTER", "read_count": 1,
        })


if __name__ == "__main__":
    unittest.main()
