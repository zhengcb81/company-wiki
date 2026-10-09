# Fresh cohort storage preparation — HANDOFF

Status: storage preparation complete; fresh research has not run. Retain all three environments through execution and four independent reviews. MAIN owns launch, final budget/config freeze and cleanup.

## Retained environments

Owned root: `C:/Users/郑曾波/AppData/Local/Temp/mFresh-me8cejn4`.

| Company environment | Public SourceRefs | Necessary archive raw copies | Initial bytes | Observed preparation peak bytes | Conservative preparation bound bytes |
|---|---:|---:|---:|---:|---:|
| CN-688012 | 5 | 0 | 826,552 | 829,557 | 1,714,981 |
| HK-00700 | 5 | 3 | 8,092,496 | 10,726,393 | 19,285,880 |
| US-MSFT | 10 | 4 | 6,834,465 | 10,608,251 | 16,456,481 |
| Total | 20 | 7 | 15,753,513 | 19,525,413 | 37,457,342 |

The initial total is 15.02 MiB, observed peak 18.62 MiB and conservative bound 35.72 MiB, below the 256 MiB per-environment and 512 MiB cohort limits. The observed total is the sum of per-environment sampled maxima; the conservative bound includes temporary official-import copies and catalog/journal allowance. Existing readonly raw bytes outside this owned root are referenced, not copied or counted as newly occupied storage. No 222 MB production catalog was copied.

Each company subdirectory owns `config/source_catalog.yaml`, `config/source_acquisition.yaml`, `config/filing_fetch_company_wiki.json`, `config/local_ocr.json`, `companies/`, `catalog/catalog.sqlite3`, catalog staging, `provider-state/dayu`, `state/ff`, `state/et`, subprocess `temp`, future `auto/narrative.sqlite3`, `work`, `rf/registry` and `rf/output`. Each catalog uses one owned writable `company_raw` root and explicit existing readonly roots. All three AUTO database paths are still absent. Reserved FF/ET paths do not invent a new state/cache API; actual ET subprocess temporary retrieval is directed through owned TEMP/TMP. Producer code, models, installed skills and existing sources remain readonly.

## Public preparation and one representative read

`prepare_environment.py` executed 35 recorded public operations, exit 0. It used the existing source catalog registration, sourcefacts, generic local prepare and official local-document import entry points. No production row/DB copying or consumer-side raw joining was used. `prepare_operations.json` preserves bounded receipts; `environment_manifest.json` and each `environments/<company>.json` preserve SourceRefs, current manifests, exact source groups, config paths and gaps.

- CN: five existing readonly sources (FY25 annual, 2026H1, 2025H1, 2026Q1 and IPO prospectus). FY24 annual, conditional financing metadata and SSE Q&A wrapper remain gap records without fake SourceRefs.
- HK: two readonly annuals and three necessary owned archive imports (H1 report, earnings release and corporate overview).
- US: three readonly sources (FY24/FY25 annuals and third-party TXT), three existing quarterly SEC originals with isolated public local-prepare facts correction, and four owned archive imports (official release, call HTML, metrics HTML and FY27 metric-transition PPTX). A separate text-supplement gap remains.

Representative only: the current installed FF v2 `reuse_only` selected CN FY2025 annual with `resolution_outcome=reused_existing`, two CWP calls and zero downloads. Public `source_reader_cli` then returned receipt 2.1, status ok, exactly 9,165,875 bytes with SHA-256 `d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5`. FF's candidate byte verification was pending until this actual verified open; `public_representative_receipt.json` records both stages. No second all-source verify pass was run.

Preparation activity: provider requests 0, download events 0, model requests 0, OCR inference 0 and executor runs 0. The CLI network guard recorded no attempt and was removed in finally; future launch will not inherit it. Earlier readonly Tencent metadata-page browsing produced no new publication fact; it is not a source acquisition or availability receipt.

## Scope and runtime handoff

`environments/<company>.scope.draft.json` and `.launch_env.json` provide owned path/config references, resolved identity, information date 2026-10-08, current installed entry points and environment variable names/presence only. Config mirrors are under `configs/<company>/`. No API key values or LLM config contents were copied. The LLM file is only a reference to MAIN's actual `config.yaml`.

Batch `--project-root` must be the matching owned company root. Each root has an exact 943-byte copy of the existing nonsecret local OCR config, SHA-256 `9b8a7df81ca62ebc4bb9c2d60d45c247b291564a4a38f5648e5f4b3edb59889b`; this keeps future batch generation and public narrative replay on the same config. This preparation did not initialize an OCR adapter or invoke inference, and did not copy model files. Model paths refer to the existing readonly installed models.

Observed code HEAD references are CWP `9704909f38c2466fd6d13e24de4dcbf5a0137af4`, FF `5ef8056bdba4be9134bb6c90f9bd457ee5f38253` and RF `28dbb91056c1b16759ab814018e19025415fb4ec`. These are preparation observations, not a final executor freeze. MAIN must freeze actual installed hashes/HEADs, forecast horizon, current authoritative mother-ledger usage and cumulative/per-run budgets after its running node is terminal. Draft numeric budgets remain null; no historical fees or unknown charges were reset or copied into another ledger. The prepared scopes are explicitly drafts, not completed audit/executor contracts.

## Source clock and coverage limits

Twenty registered SourceRefs do not mean twenty sources are date-eligible for every request. Unknown HK H1/overview and third-party MSFT TXT publication stays null. Official FY26Q4 call HTML is a distinct source with its own primary URL/date; its proof is not borrowed by TXT. Original URLs and primary-page correspondence must be checked during the actual research executor where needed.

Default public read receipt is 2.1. The current optional availability producer accepts existing canonical DownloadReceipt sidecars bound to exact bytes; old archive indexes/capture dates are not accepted proof. This package adds no availability adapter, fake primary_archive proof or 2.2 receipt.

CN FY24 original remains an honest metadata gap, with no duplicate download or blanket reactivation. SSE JSON Q&A remains a wrapper-format gap, not an ET transcript or a successfully imported PDF. MSFT FY26 annual 10-K is only an explicit subsequent owned FF/Dayu acquisition target; no download ran. Absence evidence is bounded to previously configured inventory and archive groups. Existing public date facts are retained; no filename/mtime/capture-date publication was invented.

## Preservation, failure receipt and cleanup

Production source catalog, acquisition and local OCR config hashes matched before/after; protected source input size/mtime checks were unchanged. Public registration/import verified the relevant raw bytes at its responsibility boundary; unchanged raw inventory hashes are retained without another full-read pass. No source original, Dayu state, production DB/config, installed skill, main PWF or old research report was written.

The first launcher was denied when creating a guard in sandbox-virtual TEMP, before any public operation. `caller_preparation_failure.log` retains the exact error. Its empty failed root `mFresh-hbng2p6k` was verified empty and removed with a native literal-path operation. The successful explicitly owned normal TEMP root above is retained; `prepare_partial_state.json` records guard removal and unchanged caller process environment. There is no remaining temporary overlay to restore.

Do not delete `mFresh-me8cejn4` before fresh execution and all four reviews finish. MAIN's eventual cleanup scope is only that resolved absolute owned root, after readers/processes close and against `environments/*.initial_inventory.json`; never move/delete readonly external roots. Research may add owned data, so preserve final evidence before cleanup. This phase6 package contains only lightweight code/config/reference/inventory/receipt documents; raw and databases remain in TEMP. The package is ready for MAIN's scoped commit; this agent did not stage/commit MAIN's concurrently owned changes.
