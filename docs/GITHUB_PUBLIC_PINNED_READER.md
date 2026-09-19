# Pinned public GitHub source reader — read-only prototype

This reference implements **one concrete HTTPS read of a PUBLIC GitHub file**
using the fixed GitHub Contents API at an explicitly supplied 40-character,
lowercase immutable commit SHA. It requires no GitHub token and provides
**no access to private repositories or permission escalation**.

`PinnedPublicGitHubReader(owner, repository, commit_sha, allowed_paths)`
is callable with `github:<owner>/<repository>:<path>`. Its constructor
requires a nonempty explicit allowlist of conservative relative file paths
(no traversal, query, arbitrary URL, or implicit branch ref). The adapter
accepts only a source identifier exactly matching its configured owner,
repository and allowed path.

For each allowed request it makes one fixed HTTPS GET to
`api.github.com/repos/<owner>/<repository>/contents/<path>?ref=<commit>`.
It sets a five-second request timeout and refuses HTTP redirects. It reads
at most 196609 response bytes and rejects oversized responses. A successful
response must be HTTP 200 and a single JSON file object with base64 content,
an exact matching path, a nonnegative declared content size no larger than
131072 bytes, and a 40-character lowercase Git object blob SHA. It decodes
base64 strictly, checks decoded length, and compares Git blob SHA to the
returned bytes. It returns a `FetchedSource` carrying only the exact
requested source identifier, pinned commit and decoded file bytes.

The existing `acquire_declared_sources(request, reader)` handoff then
locally derives Source Read Evidence, checks its binding and only after
that records the source for local Source Read Gate evaluation. No requests
are made when the handoff is configured `no_external_read=True`.
The adapter does not automatically retry failed or denied HTTP requests.
Errors are opaque, without URL, payload, request header or remote error text.

## Boundaries

This fixed-host, public-only adapter is a limited, read-only working
connector prototype. It is **not** a general private GitHub connector,
an authorization or installation-scope verifier, a credential handler, a
Microsoft 365/Salesforce integration, or a production-ready source
provenance attestation. GitHub object hashes and HTTPS validate a narrower
technical claim than independently verifying human authorization and
freshness of an evolving source. A pinned commit remains intentionally
immutable: the caller must explicitly select/review a newer commit.
The local Gate PASS establishes only that the selected reader supplied
a locally consistent response; never substitute it for user authorization,
a separate live-access check or permission/production approval.

The default adapter uses the standard-library HTTPS client; its optional
injected transport exists solely to support deterministic, no-network
tests. No custom host or bearer-token field is accepted. The default CI suite mocks HTTP responses and cannot prove real network
access. A separate, single-read public-only HTTPS smoke was executed on the
public reference candidate branch: GitHub Actions run [`35444084250`](https://github.com/kami-mob/hitori-fde-context-router/actions/runs/35444084250) ran
`python tests/test_github_public_pinned_live_smoke.py` and passed its one
real public GitHub Contents GET for an explicitly pinned public reference
file. The smoke verified the returned file bytes against an independently
checked expected Git object blob SHA and then passed the already-read
receipt through the local acquisition handoff without a second HTTP GET.
The smoke file remains opt-in; a network call is NOT a requirement of
regular deterministic CI. This single public-read result does NOT show
private repo access, permission detection, Microsoft 365/Salesforce access,
source freshness or deployed product behavior.

## Reproducible tests

```bash
python tests/test_github_public_pinned_reader.py
# Opt-in; requires public GitHub network access and no token:
python tests/test_github_public_pinned_live_smoke.py
python tests/test_source_read_acquisition_handoff.py
python tests/test_source_read_evidence_binding.py
python -m compileall reference runtime tests
```

Only this new adapter (when using its default transport) makes network
requests. The underlying acquisition handoff, Binding and Source Read
Gate remain independent, locally testable and fail-closed. No token, secret,
customer data or actual organizational source appears in the test fixture.
