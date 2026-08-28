# Publication Checklist

Target public repository: `kami-mob/hitori-fde-context-router`

## Repository creation

- [x] Re-create a new **public** repository named `hitori-fde-context-router`
- [x] Do not initialize with a license
- [x] Do not copy the previous public repository history
- [x] Publish only sanitized public-reference material

## Commit metadata privacy gate

- [x] GitHub account setting `Keep my email addresses private` enabled by the repository owner
- [x] GitHub account setting `Block command line pushes that expose my email` enabled by the repository owner
- [x] Previous public repository with pre-privacy commit history deleted
- [x] Replacement repository created with a new repository ID and empty history
- [x] First replacement-repository commit inspected through GitHub: normalized author/committer email fields are not exposed
- [x] Latest reviewed commit uses GitHub `users.noreply.github.com` metadata rather than the private account email

Commit metadata privacy is a separate gate from file-content sanitization.

## Sanitization gate

Confirmed in the replacement public tree:

- [x] no real company, customer, employee, or internal project names
- [x] no private account email address or phone number in repository files
- [x] no private network paths, IP addresses, hostnames, or file shares
- [x] no organization, tenant, account, or user identifiers used as operational secrets
- [x] no credentials, API keys, tokens, secrets, or authentication material
- [x] no production backups or secure directories
- [x] no real Salesforce metadata or Power Automate definitions
- [x] no internal source code
- [x] no real decision records
- [x] no raw screenshots from internal environments
- [x] Explicit Source Read Gate update contains only generalized contract and sanitized aggregate evidence
- [x] no workspace-specific project name, private canonical repository name, or internal evidence path introduced by the Source Read Gate update
- [x] public synthetic fixture values are decoupled from current private decision values

### 2026-08-29 policy audit correction

A publication-policy audit found that the public fixture was labeled synthetic but reused two values that matched current private commercial decision values. No private identifiers, paths, or labels were exposed, but this did not meet the stricter synthetic-evidence boundary.

Current-tree correction completed:

- [x] replaced matching fixture values with unrelated fictional values
- [x] aligned public reference tests with the new fictional values
- [x] verified the prior matching values no longer appear in the current public repository search
- [x] kept the public resolver behavior and 7-case test intent unchanged
- [x] re-ran public CI successfully after the correction

### Reachable-history remediation

The 5-pass re-evaluation found that the old synthetic fixture values were still visible in commits reachable from `main`, even though the current tree was already corrected.

A public Git repository's reachable branch history is part of its publication surface. Therefore current-tree correction alone is not considered sufficient.

Remediation requirement:

- [ ] rebuild `main` from a clean ancestor before the offending fixture commit, using the current sanitized tree
- [ ] force-update `main` to the rebuilt commit so the offending fixture commits are no longer reachable from the public branch
- [ ] verify the `main` commit chain no longer contains the offending fixture commit
- [ ] verify current tree still contains only fictional fixture values
- [ ] verify commit metadata privacy on the rebuilt head
- [ ] re-run public CI on the rebuilt history

Until the items above pass, publication state is `PUBLIC_SYNC_PENDING_HISTORY_REWRITE`.

Sensitive-term searches found no matches for checked private project/repository markers, internal decision ID markers, or the private email marker in the current tree.

## Evidence gate

The repository contains enough material for a third party to inspect the technical claim:

- [x] architecture
- [x] resolution specification
- [x] Explicit Source Read Gate contract
- [x] minimal reference resolver
- [x] synthetic fixture data
- [x] deterministic tests
- [x] CI workflow
- [x] sanitized validation summary
- [x] sanitized source-read regression and live-smoke evidence
- [x] limitations / non-claims
- [x] Japanese first-reader FAQ
- [x] sharing / claim guidance

## Publication policy audit

Current public content was checked against the applicable publication boundaries:

- [x] security/confidentiality boundary
- [x] public GitHub Why / What / Evidence boundary
- [x] claim accuracy / non-claims
- [x] public-vs-private implementation distinction
- [x] synthetic-data boundary for current tree
- [x] commercial boundary
- [x] commit metadata privacy
- [x] public CI
- [ ] reachable `main` history boundary

Audit result until history rewrite completes: **PENDING_HISTORY_REWRITE**.

## Ongoing public evidence synchronization gate

Public evidence must not silently drift behind the implementation and validation evidence it describes.

For future private/internal changes:

- [x] assess whether the change affects an existing public claim, architecture description, behavioral contract, validation result, limitation, publication status, or sharing guidance
- [x] if public impact exists, verify the proposed public content against the applicable publication/content policies **before** treating synchronization as authorized
- [x] if public impact exists, update the relevant sanitized public evidence before treating the public-facing change as complete
- [x] preserve the sanitization and privacy boundary during synchronization
- [x] preserve existing claim limits, non-claims, commercial boundary, and sharing guidance
- [x] ensure synthetic fixtures do not reuse current private decision values / IDs / paths
- [x] treat the current tree and reachable default-branch history as publication surfaces
- [x] re-run public CI after the synchronized update
- [x] update this checklist when the public evidence/status materially changes
- [x] if the change has no public impact, do not copy private implementation detail merely for symmetry

A requirement to synchronize does **not** itself grant permission to publish the underlying private content. If the proposed public wording would violate an applicable publication, privacy, security, claim, or commercial-boundary rule, keep the private detail private and either generalize the public explanation accurately or leave the public evidence in **sync pending** state.

If a public-impacting change cannot yet be synchronized safely or the required checks are incomplete, the public evidence should be treated as **sync pending**, not current/completed.

This gate is a maintenance rule, not permission to publish private implementation details.

## Commercial boundary

Public repository explains and demonstrates the **Why / What / Evidence**.

Do not include complete paid implementation material such as:

- production-ready workspace bootstrap templates
- complete AGENTS / start-router templates
- end-user migration package
- installation walkthrough designed for nontechnical users
- complete HOT/WARM/COLD project templates
- complete troubleshooting playbook
- paid-kit sample project bundle

The public Source Read Gate material documents the behavioral contract and evidence only. Workspace-specific instructions, connector configuration, source maps, and operational logs remain outside the public repository.

## Final release gate

- [x] replacement repository exists and is public
- [x] old public commit history removed by repository replacement
- [x] replacement first-commit privacy verified
- [x] sanitized reference tree restored
- [x] Explicit Source Read Gate public documentation added
- [x] README / Architecture / Validation / Limitations / FAQ / Sharing Guide aligned with the gate
- [x] public URL / repository metadata rechecked
- [x] Description configured
- [x] private project/repository marker search re-run after Source Read Gate update
- [x] synthetic fixture/private-value collision corrected in current tree
- [ ] offending synthetic fixture commits removed from reachable `main` history
- [x] ongoing public evidence synchronization gate documented
- [x] publication/content-policy review is part of the ongoing synchronization gate
- [ ] promotion status restored to public-ready after history rewrite verification

## Current status

**PUBLIC_SYNC_PENDING_HISTORY_REWRITE**

Validation date: 2026-08-29
Policy audit: **PENDING_HISTORY_REWRITE**
Current-tree CI: **Reference Resolver Tests — SUCCESS**

The synthetic-value correction does not change the public Python resolver or its expected deterministic result (`7/7 PASS`).

### Non-blocking discoverability item

Repository Topics are currently empty. This does not affect privacy, correctness, or the release gate, but adding Topics later can improve GitHub discoverability.
