# HANDOFF — generic legacy local reconcile

Status: implemented and verified; MAIN integration pending.

- Base: a40eb065da1bb21d231d2644449e2ecd8a2f98d6.
- Branch: codex/main-legacy-local-reconcile-20261009.
- Code commit: 7ced0b50b8cabb5a8becc50374cd6f8216d212ff.
- Isolated worktree: C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki.
- Exact code/test paths and SHA256: handoff.json. This documentation commit follows the code commit; final docs HEAD is reported to MAIN externally.

## Delivered

Explicit pathless localprepare CLI + bounded inactive inventory + actual SEC/issuer/cache facts + one-transaction facts/restoration + ensure zero-fetch composition + same-byte local official dedup correction. Unknown/withdrawn/damaged retirement never auto-restores. Unknown publication blocks historical success and duplicate fetch. Repeat calls are semantically idempotent; existing reader/query and provider re-download contracts remain.

Default source-query remains read only. MAIN-owned source_reader_cli/source_availability DTO files and source_reader are untouched. No production/main/Dayu/RF/raw/config/install writes, push or merge. No overlay and no live supplier/model calls.

## Concentrated proof

Final command covered test_legacy_local_reconcile, test_official_source_flow, test_source_catalog_canonical_writer, test_source_facts, test_dayu_fiscal_metadata, test_source_catalog_acquisition, test_single_intent_latest_acquisition.

166 PASS /39.34s; `concentrated-delivery.log`. Own short pytest TEMP; finally TEMP/TMP restored and directory absent. Exact modified/new paths Ruff --no-cache and git diff --check passed. Normal code hooks Ruff and host-assumption guard passed; mypy/config-doctor correctly skipped by path scope. Initial 6 RED, dedup2 RED, SEC inline whitespace2 RED and discovery1 RED are retained. Caller fixture errors and old32-span port migration are recorded in findings/progress; no identity/economics assertions were removed.

## Actual existing originals proof

`actual_originals_node.py` → `actual_originals_receipt.json` / `actual_originals_node.log`: exit0, four cases,56.248s.

| Original | Actual result |
| --- | --- |
| MSFT FY26Q1/Q2/Q3 HTML | Actual MAIN FF commit a1e97fa462f6fc381f18ce39641224310c7228a8 v2 reuse_only returns same source/document/hash; current public source reader verifies actual bytes and US/FY26 manifest. Wrong legacy HK/FY metadata corrected in isolated catalog. Repeats add no assertions/restores. Publication-minus-one-day requests refuse. |
| 中微 FY24年报 PDF | Honest local_metadata_incomplete/publication gap; remains retired; 0 repeated download. No independent publication/issuer proof fabricated from catalog date/filename/mtime. |

Socket connection guard recorded0 network attempts; supplier/model/download counters0. All raw/meta/source sidecars and production source_catalog/source_acquisition/local_ocr configs had equal before/after SHA. Independent temporary catalog removed, original bytes untouched, TEMP/TMP/PYTHONPATH restored. Final receipt contains hashes and small public bundles/receipts, no full raw payload.

Actual public-contract/inline-markup RED receipts are retained: physical-key count excluded from public DTO; SEC whitespace normalized generically while preserving form `/A`. Initial caller fixture receipts are retained separately, not claimed as production failures.

## Integration notes

MAIN merges this code/doc series and separate FF thin package, then owns production/main integration. INTERFACE.md pins exact public request/result/internal transaction API. This package emits no optional historical availability proof; source_reader2.2 is MAIN-owned. New company_raw/dayu_portfolio issuer-group discovery delegates to existing source registration; generic directory roots require explicit registrations. Future CN primary publication/issuer facts can close the honest gap through the same sourcefacts mechanism, without raw/Dayu changes or global reactivation.
