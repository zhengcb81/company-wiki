# Legacy caller reachability inventory v1

Status: CW-3.1 Phase 1 audit evidence (2026-07-19)

This inventory separates source/evidence production from the historical
research Wiki system. It is a reachability contract, not authorization to run
any legacy writer. Historical source, Wiki, graph, database, and output files
remain untouched.

## Canonical production entry points

| Trigger | Target | Mode | Allowed responsibility |
|---|---|---|---|
| `company-wiki-source-export` | `company_wiki.source_contract.cli:main` | explicit CLI | versioned source/evidence export |
| `company-wiki-collect-announcement` | `company_wiki.source_contract.announcement_cli:main` | explicit CLI | announcement discovery and immutable source registration |
| `company-wiki-source-catalog` | `company_wiki.source_catalog.cli:main` | explicit CLI | scan, normalize, source-only summarize, query, quality, export, worker control |
| `company-wiki-identify` | `company_wiki.source_catalog.identity_cli:main` | explicit CLI | listed-company identity resolution |
| `scripts/source_catalog_worker_at_logon.vbs` | hidden `source_catalog_worker_at_logon.ps1` host | Windows logon | no-console startup handoff |
| `scripts/source_catalog_worker_at_logon.ps1` | `scripts/source_catalog_worker.ps1` → source-catalog CLI | Windows logon | fixed source-only worker cycle |
| `scripts/source_catalog_control.cmd` | `scripts/source_catalog_control.ps1` → source-catalog CLI | explicit desktop/control UI | worker status, start, pause, resume, stop |

The Windows launchers and packaged console entries above do not import or call
`scripts/scheduler.py`, an assessment/valuation module, a research review
queue, or a Wiki writer.

## Legacy direct-script policy surface

There are 50 explicitly guarded `scripts/*.py` tools, excluding the two policy modules
`sitecustomize.py` and `writer_policy.py`. All are fail-closed by default today;
the old two-factor environment override can still enable them unless a script
is permanently retired below.

### R1 — research/Wiki orchestration: must retire

These entry points generate, review, or orchestrate research semantics or
legacy Wiki writes. They have no permitted company-wiki production use.

| Scripts | Trigger/reachability | Historical effect | Replacement |
|---|---|---|---|
| `scheduler.py`, `full_pipeline.py`, `batch_process.py` | direct CLI; scheduler also has `--daemon`; `full_pipeline` dynamically launches stage scripts | automatic legacy collect→ingest→assess→judgment/Wiki pipeline | source-catalog `worker`; downstream research belongs to StockWiki |
| `batch_assessment.py`, `auto_synthesis.py`, `investment_judgment.py`, `valuation_engine.py`, `generate_slides.py` | direct CLI or imported callable | assessment, synthesis, investment thesis, valuation, formal research output | no company-wiki replacement; StockWiki owns these semantics |
| `ingest_v2.py`, `batch_ingest.py`, `enrich_wiki.py`, `consolidate.py` | direct CLI or orchestrator subprocess | write/enrich/consolidate legacy company/sector/theme Wiki state | source-catalog `scan`, `normalize`, `export-indexes`; no research Wiki write |
| `stage3_analyze.py`, `stage4_review.py`, `stage5_ingest.py`, `stage6_synthesize.py` | direct CLI or `full_pipeline.py` subprocess | analyze/review/ingest/synthesize legacy research artifacts | source-catalog parse/quality/query/export only; research workflow moves downstream |
| `review_queue.py` | direct CLI or scheduler import | review queue for LLM-generated research/Wiki content | source extraction quality is exposed through `extraction-quality`; investment review belongs to StockWiki |

R1 retirement requirements:

- the two legacy environment variables must not restore execution;
- direct CLI must exit before configuration, API keys, network, database, or
  file writes;
- imported orchestrator permission checks must also reject execution;
- rejection must name the source-only replacement or the StockWiki boundary;
- historical code and output files are retained.

### S1 — source acquisition/parser compatibility: keep default-blocked, audit before routing

These scripts may still contain upstream source acquisition or deterministic
parsing capability. They are not approved production entry points, but must
not be permanently retired until their useful source-only behavior is either
routed through the canonical source catalog or explicitly archived.

`collect_news.py`, `collect_reports.py`, `run_downloader.py`,
`build_extracts.py`, `stage1_extract.py`, `stage2_structure.py`,
`fix_report_dates.py`

Expected future replacement: source-catalog acquisition adapters, scanner,
normalizer, page-aware parser, EvidenceSpan/extraction-quality contracts, and
the documented A-share/dayu CLI routing. No legacy Wiki write may be carried
forward.

### RO1 — possible read-only compatibility: keep default-blocked pending proof

`audit_config.py`, `search.py`, `status_tracker.py`

These names suggest diagnostics/query behavior, but the current broad writer
inventory still guards them. A later slice must prove physical zero-write and
source-only output before exposing any read-only compatibility entry.

### W1 — other legacy Wiki/state maintenance: keep frozen; retire by later caller class

`graph.py`, `test_framework.py`

These are not called by the canonical startup/control/console routes. They
remain default-blocked. Later work units must split genuine read-only source
diagnostics from legacy Wiki/state mutations before changing their policy.

### R2 — semantic maintenance and mixed legacy writers: must retire

CW-3.2 audited the first semantic-maintenance slice. These direct CLIs remain
historical source only; they must not be restored by compatibility variables.

| Scripts | Prohibited effect | Replacement/boundary |
|---|---|---|
| `query.py`, `refine.py` | synthesize/archive answers into research Wiki pages or overwrite timeline summaries | source-catalog evidence query is locator-bound and zero-write; research synthesis belongs to StockWiki |
| `evolve_questions.py`, `question_evolver.py`, `expire_tracker.py` | maintain research questions or assign investment-information half-lives/expiry judgments | question/claim state and investment freshness judgments belong to StockWiki |
| `reprocess.py` | remove and rebuild legacy company/sector/theme Wiki timeline entries | immutable source catalog and versioned source-oriented export; no legacy research Wiki rewrite |
| `auto_discover.py` | mix company discovery with topic/question graph mutation and Wiki scaffolding | `company-wiki-identify` for identity; research taxonomy/questions belong to StockWiki |
| `tag_segments.py` | LLM sentiment/importance/research taxonomy written to legacy segment state | page-aware EvidenceSpan and extraction-quality contracts only |
| `maintenance.py` | orchestrate legacy cleanup, reprocess, question/assessment enrichment and Wiki quality reports | source-catalog worker fixed source-only stages; no legacy maintenance pipeline |

`maintenance.py` was not in the original 49-file explicit-guard inventory: it
has a direct `main` but delegates mutations via subprocess, so the old scanner
did not classify it as a writer. Normal Python startup was protected only by
`sitecustomize.py`; CW-3.2 requires an explicit guard so `python -S` also fails
before argument/config/network/write initialization.

`cross_verify.py` is excluded from R2 pending a source-quality migration audit:
multi-source diagnostics may be an upstream responsibility, but the legacy
implementation lacks stable source IDs/locators. `test_framework.py` is also
excluded: it writes isolated test artifacts, and any nested R1 pipeline call is
independently blocked by the target script's permanent-retirement policy.

### R3 — destructive/reset maintenance: must retire

These direct CLIs expose irreversible or history-rewriting operations that are
not part of the source-catalog runtime:

| Script | Legacy mutation | Safe replacement/boundary |
|---|---|---|
| `cleanup_deprecated.py` | deletes code under `scripts/models/**` and archived tests under `tests/archive/**` | explicit human code maintenance with reviewed deletion manifest; never a production worker capability |
| `cleanup_junk.py` | unlinks `companies/*/raw/news/*.md` and rewrites Wiki timelines | immutable raw; duplicate/rejection decisions remain indexed and UI deletion is explicit, never automatic raw cleanup |
| `cleanup_log.py` | rewrites append-only `log.md` after making a backup | logs remain append-only; isolated test artifacts belong outside the production log |
| `reset_ingested.py` | deletes legacy `.ingested/*.hash` markers, including a bulk mode | canonical catalog uses versioned document/artifact status and replay, not marker deletion |

No canonical console/startup route calls these scripts. Unit tests import only
the pure discovery/verification functions from `cleanup_deprecated.py`; direct
CLI retirement must preserve that importability. The dormant packaged
deployment report mentions `cleanup_junk.py` as historical metadata but does
not execute it.

### R4 — legacy link/index/dashboard writers: must retire

CW-3.4 audited the legacy projection and maintenance CLIs that can regenerate
or mutate a second Wiki/index/dashboard state outside the canonical source
catalog:

| Script | Legacy output or mutation | Replacement/boundary |
|---|---|---|
| `build_links.py` | regenerates root `links.yml` from legacy Wiki/graph relationships | versioned source-catalog exports contain source/document/location relationships; investment taxonomy remains downstream |
| `fix_broken_links.py` | rewrites or removes PDF links inside legacy Wiki pages; default mode writes | exact source locations and canonical/equivalent duplicate annotations, without rewriting research pages |
| `fix_sources_count.py` | rewrites legacy Wiki frontmatter `sources_count`; default mode writes | source/export counts are derived from catalog records and never hand-maintained in research frontmatter |
| `generate_dashboard.py` | writes root `dashboard.md` using “research brain”, LLM-call and Wiki-rewrite health semantics | source-catalog `pipeline-status`/`worker-status` and extraction-quality only |
| `generate_index.py` | rewrites root `index.md` from core questions, industry-chain navigation and legacy Wiki summaries | versioned source-only CSV/Markdown export; formal research navigation belongs to StockWiki |
| `quality_dashboard.py` | scores core questions, comprehensive assessments and theme Wiki pages; optional arbitrary output path | extraction-quality contract and read-only pipeline status; investment semantic quality belongs downstream |
| `wikilinks.py` | can backfill links across legacy Wiki pages | source IDs, locators and explicit export relationships; pure historical engine imports remain testable |

All seven have an explicit direct-CLI guard before `main`, so permanent
retirement needs no algorithm changes and survives `python -S`. Existing
automatic/import callers are already-retired R1/R2 orchestrators; the only
additional dynamic caller is explicit `lint.py --fix`, whose nested script
must now fail closed. Unit tests import `WikilinkEngine`; direct CLI retirement
must not make module imports exit.

### R5 — legacy Wiki title-cluster credibility report: must retire

`cross_verify.py` reads derived legacy company Wiki timeline headings and
Markdown `[来源](...)` link text, clusters titles by string/event-keyword
similarity, and labels clusters high/medium/pending credibility solely from the
number of distinct link strings. It has no stable source/document ID, locator,
parser/version, content-integrity check, duplicate/equivalence handling, or
extraction-quality result. `--report` writes root `cross_verify_report.md`.

The only non-direct caller is `scheduler_steps.py`, reached by the already
retired R1 scheduler. The deterministic clustering helpers remain historical
and importable, but the CLI and its research-credibility labels cannot be
restored by compatibility variables. A future multi-source extraction-quality
service would require a separate locator-bound contract over canonical catalog
records; it must not reuse these credibility labels as source acceptance.

## Dormant packaged compatibility

- `src/company_wiki/scheduler.py` is a generic injectable job/step queue.
- `src/company_wiki/deployment.py` is its historical shadow/canary/full
  deployment manager.
- Production imports only connect `deployment.py` to `scheduler.py`; all other
  callers found in this audit are tests. Neither has a CLI, console entry, or
  startup launcher.
- `src/company_wiki/automation/` exposes a read-only `status/doctor/plan` CLI
  and frozen handler specifications, but production code creates no
  `HandlerExecutor`, registers no callable handler, and instantiates no
  automation worker.

These modules are shipped but not production-reachable. They must never be
wired into the source-catalog worker without a separate source-only contract.

## Evidence and update rule

Evidence sources for v1 are `pyproject.toml`, the four source-catalog Windows
launchers, `scripts/writer_policy.py`, `scripts/sitecustomize.py`,
`scripts/common.py`, `scripts/scheduler.py`, `scripts/full_pipeline.py`, the
package scheduler/deployment/automation modules, and the existing architecture
and writer-freeze tests.

Any change that adds a production console/startup entry, imports a legacy R1
module from `src/company_wiki/source_catalog`, or adds a callable automation
handler must update this inventory and its contract tests in the same work
unit.
