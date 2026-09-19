"""Opt-in one-GET smoke for exact PUBLIC decision bytes, not default CI.

Pinned to a previously reviewed public commit and expected blob. This does
not read a private repository, use credentials or authorize any decision.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from github_public_pinned_reader import PinnedPublicGitHubReader  # noqa: E402
from pinned_public_decision_preflight import (  # noqa: E402
    PinnedPublicDecisionRequest, resolve_pinned_public_decision,
)

OWNER = "kami-mob"
REPOSITORY = "hitori-fde-context-router"
COMMIT = "5cb73718af6c7bf8993761a901b79ef0bc50025e"
PATH = "reference/sample_decisions.json"
EXPECTED_BLOB = "1d3efdfef9bc18418cd93cf11e488ad6c1e85f3f"
SOURCE_ID = f"github:{OWNER}/{REPOSITORY}:{PATH}"


class OnePublicDecisionReadSmoke(unittest.TestCase):
    def test_pinned_public_snapshot_resolves_from_one_real_get(self):
        reader = PinnedPublicGitHubReader(OWNER, REPOSITORY, COMMIT, (PATH,))
        req = PinnedPublicDecisionRequest(
            reader=reader,
            source_id=SOURCE_ID,
            expected_blob_sha=EXPECTED_BLOB,
            domain="demo",
            subject="starter",
            field="price",
            as_of="2026-08-28",
        )
        # This call invokes one public-only GitHub HTTPS GET and parses the
        # returned SHA-verified bytes. It does not fetch any other source.
        result = resolve_pinned_public_decision(req)
        self.assertEqual(result, {
            "state": "RESOLVED",
            "stage": "local_public_snapshot_resolution",
            "evidence_scope": "PINNED_PUBLIC_FILE_BYTES",
            "decision_id": "PRICE-002",
            "value": 200,
        })


if __name__ == "__main__":
    unittest.main()
