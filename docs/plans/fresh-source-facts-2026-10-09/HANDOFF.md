# W06 source facts / local discovery delivery

## Owner and branch

Worktree `C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki`, branch `codex/fresh-source-facts-20261009`, base `284328bb6f48677dd2999541c14b4bfb54379a04`. MAIN owns independent integration review, merge/push and skill installation. This lane does not modify FF/ET/RF, W05 official_source_flow, Dayu, production catalog/config/raw, shared root PWF or CI/hooks.

## Root causes repaired

1. SEC DEI extraction formerly normalized end dates before establishing request relevance. Actual old FY2021/FY2022 `ixt:datemonthdayyearen` raised; the exception unconditionally vetoed missing FY2026 acquisition. Now actual CIK/year/period/form proof is extracted once before date normalization. Proven different period/form is excluded; unresolved scope, bad bytes and issuer conflict cannot become absence. Legacy actual transform is explicitly supported without guessing arbitrary declared transforms.
2.26 small Dayu metadata groups competed with16 raw read candidates. Groups now default256 and directory entries4096; raw candidate16, total256MiB and30s remain. Exhaustion is a named unavailable result, not an empty lake. No threshold increase to raw16.
3. Public quarterly originals actually contain `<title>10-Q</title>` but title/form facts were absent from the source-fact correction vocabulary. Existing append-only evidence JSON now supports nullable title plus the existing form column, maps title to source_title, and projects true non-null display titles across rescans. Null never becomes a permission or a filename guess. No SQL schema migration.
4. Storage traversal saw only `company/raw`; direct company originals were invisible. Both scanner v1 and adapter use one pure company layout selector; only direct files and raw descendants count. Wiki/projection, another company, symlink/reparse escapes are excluded. Same-content direct/raw copies become one SourceRef and no download.
5. Local budget originally missed registration metadata/hash and both ready public-reader branches. Optional callbacks/parameters pass one existing LocalReadBudget through all those actual reads. Original and metadata reads stop at remaining bytes and check deadline; growth is charged; attachment walks consume finite entries/groups. Budget exceptions are propagated, never swallowed as scan completion. A supplied public-read budget reports cancelled/budget_exceeded directly, preserving the cause; standalone default reads keep existing fallback diagnostics. Quarantined requested primaries produce local_original_registration_failed; failed attachments alone do not veto a healthy primary.

## Authorized source write set (14 files)

- assertion_service.py; resolver.py; dayu_fiscal_metadata.py; local_reconcile.py; local_inventory.py.
- source_group_scope.py; adapters/company_raw.py; scanner.py.
- service.py; registration_scope.py; adapter_dispatch.py; adapters/dayu.py; adapters/sidecar.py; source_reader.py.

All under `src/company_wiki/source_catalog/`. Optional defaults are None; existing complete scan, standalone reader and adapter calls keep their behavior. No consumer constructs physical paths. Existing SourceRef/manifest schema/key sets are unchanged. No private/public, manual review, expiry permit, canary, second ledger or new provider.

## TDD and acceptance

New contracts: test_title_source_fact, test_local_request_relevance, test_local_discovery_limits, test_company_source_layout, test_registration_read_budget; shared owned-source fixture. RED evidence retained: source facts/relevance, layout/budget, actual metadata pre-read漏账2failed, cached-ready漏传2failed, plus separately sealed original3-cause receipts in MAIN diagnosis. Fixture-only corrections are explicitly recorded in progress; vacuous disabled-root tests are not claimed as proof.

Final responsibility regression:196passed/2skipped (22.29s); resolver actual byte stability31passed/1skipped (3.98s). Skipped preexisting opt-in E2E does not replace our actual source replay. OS symlink privilege skip has an additional modeled link boundary test. Run commands are in green_responsibility_regression.txt and the test filenames above; resolver tests are `test_r4b03_stable_bytes.py` and `test_source_catalog_resolver.py`.

`python -X utf8 docs/plans/fresh-source-facts-2026-10-09/replay_actual_sources.py` reproduces real MSFT legacy-directory and missing FY2026 outcomes with no network. It opens the frozen original catalog read-only, backs up SQLite into its own TEMP, registers every external root read-only, appends title facts only in the clone, guards all socket connect/DNS attempts, verifies all protected originals/config/catalog SHA,size,mtime before/after, and deletes its TEMP.

Actual final receipt: candidate16 unchanged;32groups,40entries,7physical raw reads,52,643,200B;10.997s; FY2026 not_found/no_matching_local_period/blocks_download=false; actual2021/2022 legacy dates valid;3FY26 quarters title null→10-Q with idempotent corrections and unchanged capture JSON. Protected unchanged=true, own TEMP absent=true, network/download/model/original writes0. Receipt deliberately claims only known registered MSFT originals and finite configured issuer directories, not arbitrary Dropbox coverage.

## Boundaries and unresolved evidence

Matching-period bad SHA, wrong issuer, unsupported date, unknown public day and ambiguous scope remain genuine gaps. HK unknown publication dates and PDF creation dates are not changed or promoted. When primary provider publication evidence is absent, report unknown; this lane neither invents dates nor modifies historical frozen root matrices. RC10 still needs authoritative external publication event research by its owner.

This proves local source mechanism and common metadata restoration only. It does not claim whole RF analysis or all-market forecast acceptance; MAIN performs the next major integrated run using these committed artifacts.

## Committed delivery

Source/test commit: `fc1c1c0c8bff1eb6a1a1c499a48dfadeef702a0f`. Ordinary hooks passed (ruff, mypy contract modules, host assumption guard); no bypass, push, merge or installation. Final additional source contracts:38passed/1OS-symlink skipped in6.42s; final ready reader42passed in6.38s; failed-registration boundary/legacy restore44passed/1skipped in8.44s. Earlier full responsibility196passed/2skipped and resolver31passed/1skipped remain evidence, not summed as unique tests. MAIN owns one final independent acceptance of this exact source commit.
