# Pinned public decision snapshot preflight — local reference

This is a bounded, non-authoritative reference for resolving one decision from
the **same public file bytes** that were just fetched and checked. It closes
the illustrative gap where a Source Read Gate can report a read while a
caller independently supplies unrelated decision records to the resolver.

`PinnedPublicDecisionRequest(reader, source_id, expected_blob_sha, domain,
subject, field, as_of, verify_after_days=30, no_external_read=False)`
requires an exact `PinnedPublicGitHubReader`, one of its explicitly allowed
public file paths, an independently selected expected Git blob SHA-1, a
specific domain/subject/field and an explicit decision date. The reader
must itself have an explicitly pinned immutable commit. The requester must
select and authorize these inputs; this module cannot establish the
requester's permission, the accuracy of the expected digest, or that the
injected test transport actually contacted GitHub.

## One-read sequence

1. Validate configuration, requested source, expected digest, decision
   scope, date, freshness threshold and no-external-read instruction.
   Malformed input returns generic `DATA_ERROR` with no callback.
2. When `no_external_read=True`, return `VERIFY` with **zero reads**.
3. Otherwise call the configured public reader exactly **once**. HTTP
   failures return `VERIFY`, not proof that the source is permanently
   unavailable. The reader restricts host/path/commit, rejects redirects
   and validates the returned public Contents API blob.
4. Independently recompute the Git blob digest from the exact returned
   bytes and require it to match the caller-reviewed `expected_blob_sha`.
   This prevents an unexpected but otherwise valid repository revision
   from silently taking the place of the selected snapshot.
5. Pass the **already-fetched receipt** through the existing local Source
   Read Evidence Binding and modeled Source Read Gate without a second
   network request. Fail-closed if the binding or gate does not pass.
6. Parse decision records from those **same returned bytes**, not from a
   separately supplied record list. Reject oversized, malformed,
   duplicate-key, empty or invalidly shaped JSON before resolving.
7. Call the existing `minimal_resolver.resolve_current` only after the
   preceding checks succeed. Return a minimal local classification:
   `RESOLVED` includes only selected `decision_id` and its `value`;
   `VERIFY`, `UNKNOWN`, `CONFLICT` and `DATA_ERROR` remain distinct.
   Failures disclose no raw file bytes, source URL, internal exception
   or full decision record.

## What this proves — and does not prove

With a **real** `PinnedPublicGitHubReader` default HTTPS transport, this
demonstrates one explicitly selected immutable **public** source snapshot
flowing into a local decision-resolution classification. A separate
independent expected blob digest additionally binds the exact returned
bytes. A caller may inject a fake transport in synthetic tests: this
reference cannot independently attest that such a callback was
authenticated, that a private source was accessible, that a branch is
currently fresh, or that an operational decision is authorized. A
`RESOLVED` result does not confer an ACTIVE/LOCKED writeback, production
or permission authority. It must not trigger workflows or execute actions.

It is not a private-GitHub, M365 or Salesforce connector and has no
credential, deployment or permission-management behavior. The selected
JSON source **must already be public** and safe for the caller to read.
No organizational decision record, private URL or runtime secret is
stored here.

## Reproducible tests

```bash
python tests/test_pinned_public_decision_preflight.py
python tests/test_github_public_pinned_reader.py
python tests/test_source_read_acquisition_handoff.py
python tests/test_source_read_evidence_binding.py
python -m compileall reference runtime tests
```

The default public CI suite is synthetic/no-network. The separate,
opt-in public-only smoke script `tests/test_pinned_public_decision_live_smoke.py`
performs exactly one token-free pinned GitHub Contents GET for a previously
reviewed PUBLIC synthetic JSON fixture. It checks the received bytes against
an independently recorded expected blob SHA and resolves one decision from
those SAME bytes without a second GET. Run it only with explicit public
network availability, separately from default deterministic CI; record the
public run evidence before claiming the network check passed in this
repository. Even a passing public smoke does not demonstrate private
repository rights, dynamic source freshness, independent human permission
attestation, enterprise connector access or production action.
This module introduces no scheduler, credentials, retry, persistent state
or product-release action.
