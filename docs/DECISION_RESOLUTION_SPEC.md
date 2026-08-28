# Decision Resolution Specification

## Decision record model

A decision-bearing record may contain:

```text
decision_id
scope.domain
scope.subject
scope.field
status
effective_from
supersedes
last_verified
value
```

Reference statuses:

- `LOCKED`
- `ACTIVE`
- `PROPOSED`
- `HYPOTHESIS`
- `SUPERSEDED`
- `ARCHIVED`

Only authoritative current statuses should participate as current survivors. `PROPOSED` and `HYPOTHESIS` must not be promoted automatically.

## Scope first

Resolution begins by fixing:

```text
domain → subject/entity → field/decision point
```

A value from another subject or field is not a fallback candidate merely because it looks similar.

## Effective timing

A future-effective successor does not become current before `effective_from`.

For predecessor `A` and successor `B`:

```text
before B.effective_from : A remains current
on/after B.effective_from: B may become current
```

This prevents a current-state gap created by registering a successor early.

## Supersession integrity

A relation-bearing successor should have a stable `decision_id` and a valid `supersedes` link.

A valid relation requires, at minimum:

- referenced predecessor exists
- predecessor has a stable identity
- predecessor is authoritative or already superseded
- predecessor and successor share domain / subject / field
- successor timing is not earlier than predecessor timing
- no duplicate decision IDs
- no cycle

Malformed, dangling, cross-scope, cyclic, or invalid-timing relations fail closed.

## Unique survivor rule

After scope, status, timing, and relation filtering:

```text
0 survivors  → UNKNOWN
1 survivor   → freshness evaluation
2+ survivors → CONFLICT
```

Do not choose the newest effective date merely to make the conflict disappear.

Even if multiple survivors contain the same value, ambiguous provenance remains a conflict.

## Freshness

Freshness evaluates the selected record itself.

Signals can include:

- `last_verified`
- age since verification
- known semantic contradiction
- evidence that implementation has moved beyond the record

Reference guidance can use time thresholds, but time alone is not a universal truth rule. A recently edited file can still be semantically stale.

Possible result:

```text
RESOLVED → VERIFY
```

when the selected record needs live or canonical confirmation.

## Runtime vs offline validation

Runtime validation should focus on the requested scope. An unrelated malformed record should not necessarily block a valid current decision elsewhere.

Offline CI should validate the complete canonical registry and detect global integrity defects, including orphaned superseded records.

## Safety independence

Safety checks are evaluated independently of the decision outcome.

Examples:

- production deployment trigger
- permission / access-control trigger

A `CONFLICT` or `UNKNOWN` decision state does not disable safety requirements.
