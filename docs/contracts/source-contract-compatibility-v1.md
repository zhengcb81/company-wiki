# Source Contract Compatibility Policy v1

This document defines how StockWiki and any other read-only consumer discover,
pin, and negotiate the three company-wiki upstream source contracts. It does not
authorize company-wiki to create downstream research state or write to a
consumer repository.

The machine-readable source of truth is
`source_contract/schemas/source_contract_compatibility.v1.json`. Its
`policy_schema_version` is `1.0.0`; consumers may pin the canonical JSON with
`compatibility_policy_sha256()`.

## Published contract set

The policy is atomic across `source_manifest`, `evidence_span`, and
`source_export`. Every consumer capability declaration must include all three.
The current and supported versions are listed explicitly under `contracts` in
the packaged policy; an absent version is unsupported. Every supported version
must also appear in at least one `compatible_version_sets` entry, which is the
producer's explicit matrix of complete manifest/span/export combinations.

## Versioning and negotiation

Wire versions are stable semantic versions in exact `MAJOR.MINOR.PATCH` form.
Pre-release versions, build metadata, ranges, wildcards, and aliases such as
`latest` are not production capabilities.

Negotiation is `exact_highest`: company-wiki selects the highest published entry
in `compatible_version_sets` whose three exact versions all appear in the
consumer declaration. It never builds an unlisted cross-product from three
independent intersections. If no complete version set matches, negotiation of
the whole three-contract set must fail closed. A shared major number alone is
not compatibility: v1 schemas reject unknown fields, so a producer must never
silently send a newer shape to a strict consumer.

Patch releases may only clarify validation or repair behavior without changing
valid wire values. Additive or otherwise non-breaking wire changes require a
new minor version and an explicit supported version entry. Removing or changing
an existing field, identity, locator, hash rule, or meaning requires a new major
version. Producers retain an older serializer while that exact version remains
in the support window.

## Compatibility window

Before an older minor version can be removed, both conditions must be true:

1. Its published notice period has elapsed and is at least 180 days.
2. Two subsequent minor releases have been published after that minor.

Removal therefore occurs only after the later boundary. The policy fields are
`minimum_deprecation_notice_days: 180` and
`minimum_minor_overlap_releases: 2`. At initial publication only version
`1.0.0` exists, so the current explicit window contains only `1.0.0`; the rule
governs future releases and does not invent unavailable versions.

## Deprecation notices

`deprecation_notices` is the machine-readable notification channel. Each entry
must name the contract and still-supported version, use status `deprecated`,
provide canonical `announced_on` and `sunset_on` dates, point to a newer
supported `replacement_version`, and include a reason plus migration guide.
The current version cannot be deprecated. The sunset must be at least 180 days
after announcement, and the retiring version remains negotiable until removal.

There are no deprecations in policy v1. Consumers should treat an invalid,
unknown, shortened, or internally inconsistent notice as a contract error and
fail closed.

## Migration

Consumers should load and validate the packaged policy, declare exact versions
for all three contracts, call `negotiate_contract_versions()`, and persist the
negotiated mapping together with the policy SHA-256. When a deprecation notice
appears, add support for its replacement before `sunset_on`, then update the
pinned mapping. Consumers must not reinterpret extraction-quality status as a
downstream investment decision.
