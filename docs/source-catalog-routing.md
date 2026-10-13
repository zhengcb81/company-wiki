# Storage root routing

Storage routes select an existing scanner adapter within one configured root.
They do not select document reading strategies (the DU shared engine owns those).

`routes` is ordered. For an original's root-relative path, the first route whose
`include` matches and whose `exclude` does not match wins. Overlap is valid and
resolved by that order, consistently in YAML 1.0, policy 2.x and policy 3.0.
`X/**` also matches the subtree root `X`, following `RootSpec.route_matches`.
A route without `adapter_id` or `admission_profile_id` inherits that root default.
If no route matches, the root default applies. A root with route adapters but
without a default scans only the paths assigned to a configured route adapter.

```yaml
roots:
  - root_id: research_sources
    path: ${PROJECT_ROOT}/sources
    kind: directory
    adapter_id: sidecar_filing_v1
    read_only: true
    reusable_for_filing: true
    routes:
      - include: ["Acme/**"]
        exclude: ["Acme/filings/**"]
        adapter_id: company_raw_v1
      - include: ["Acme/filings/**"]
        adapter_id: dayu_filing_v1
```

The first example adapter handles direct company originals and legacy raw
folders. The second handles provider filing groups; use a path whose issuer
folder matches the configured security identifier for issuer-local discovery.
Layout metadata belongs to the adapter, not to filing-fetch/RF consumers.

The original selects the owner for its metadata/attachments. A PDF-only include
must not route its `.source.json` to a different adapter. Each distinct configured
adapter enumerates once; an optional primary filter rejects non-owner originals
before their metadata is interpreted. Explicit registration paths are partitioned
before enumeration. Caller-owned metadata/walker/group/entry/byte/deadline budgets
remain shared across adapters; routing never creates another budget allowance.

Unknown adapter/profile names, wrong field types and policy routes that widen
root allowed document kinds remain configuration errors. The profile selected
by a route is carried on the effective RootSpec. It is informational source
processing policy, not a new per-document permission or investment acceptance.
Root containment, actual original SHA and downstream source read budgets still
belong to their existing owner layers. Normal readers resolve registered source
versions rather than running storage discovery again.
