# D3 acceptance boundary recheck

Reviewed 2026-11-02 UTC. This is a read-only audit; no product changes, original reads, provider calls, or full-suite reruns. The directory suffix is the parent-assigned scratch name, not the review date.

## Conclusion

The actual selected RF/FF/ET/CWP combinations and installed entry evidence are real, not replaced by mocks of the whole pipeline. The D3 evidence does not prove that every cross-repository test was reassigned. One concrete AUDIT integration ownership omission remains. No production runtime coupling defect was reproduced in this review's scope (AUDIT runtime, ROOT combination, CI/hooks); other reviewers cover source consumers and acquisition.

## Findings

### A1 — P2: CWP-to-AUDIT real bundle tests were left outside ROOT combination ownership

- `revenue-forecast-audit/tests/test_du6_current_cwp_bundles.py:16-27` retains `CWP_SOURCE_REPO` and `@unittest.skipUnless(CWP, ...)`, then injects the CWP `src` path.
- Lines 54-58 import the producer's `NarrativeBundle`; lines 62-78 import producer implementations and dynamically load `company-wiki/tests/integration/test_official_json_transport_subject.py` as the fixture. This is exactly the consumer-test-to-producer-internals dependency D2.3 said to move to ROOT.
- `company-wiki/tools/run_source_system_tests.py:24-39` has no AUDIT current node; its CLI has no audit-root argument. The two tests are still in AUDIT ordinary `unittest discover` and become skips when the neighbor isn't explicitly supplied.
- `.planning/decoupling-implementation-20261102/audit-isolated.json` shows that the cited 43 passes only ran `tests/test_audit_run.py` and `tests/test_financial_measure_typed_contract.py`. They do not prove removal of this dependency or exercise actual v2/v3 bundle import.
- Root cause: static production-import inspection was mistaken for complete consumer-test ownership, and the isolated acceptance selected representative tests without an explicit remaining cross-repo inventory.
- Small direct verification: only the two `CurrentPublicBundleTests` ran with explicit CWP and host Python. Result **2 passed in 3.57s**. A first sandbox run had 1 pass/1 failure because `os.link` was denied in sandbox TEMP; the same two tests passed under the supported host execution. That environment failure is not a product failure.
- Implication: this is an acceptance/test-ownership omission, not proof that current AUDIT import is broken. The underlying assertions remain useful.
- Repair: move these two real producer fixture tests to a ROOT-owned AUDIT integration node, select `--audit-root` explicitly, retain assertions, and keep AUDIT's source-independent v2/v3 portable bundle tests in ordinary discovery. Since AUDIT has no remote, local ROOT acceptance should explicitly include it; remote coverage must state that it omits AUDIT unless a declared artifact/checkout is supplied. Do not pretend a missing checkout skip is acceptance or invent an unrequested public remote. No need to run a full company analysis or full suite.

### A2 — P3 clarification: production interface changes do not automatically trigger the combination workflow

- `.github/workflows/source-system.yml:3-15` triggers only on `integration/**`, the ROOT runner and the workflow itself, plus manual `workflow_dispatch`.
- A change only to `src/company_wiki/source_catalog/source_reader_cli.py`, `narrative_transport_cli.py`, or a wire contract will run ordinary CWP CI but not this combination job. RF/FF quality workflows contain no downstream dispatch.
- D2.3 (`DECOUPLING_FIRST.md:57`) says interface changes and major nodes run related combinations. `integration/README.md` explicitly describes a manual ROOT command and major-node use. Consequently this is **not a contradiction proving current acceptance false**: manual major-node combination is allowed and the reported D3 ran it.
- The precise limitation should remain explicit: future interface edits require ROOT to run the affected combination; current CI path routing does not enforce that. Optionally add a narrow list of public adapter/contract paths, without triggering all multi-repo tests on every implementation/doc commit. No new manual sign-off or approval gate is necessary.

## Confirmed boundaries and limits

- `integration/test_replaceable_readers.py` invokes a fresh process from an unrelated cwd; `integration/public_reading_probe.py` runs actual producer raw/narrative CLIs and compares results while hashing the temporary producer DB before/after. Wrappers relocate commands; fake commands are separately used for port unit tests.
- `integration/test_public_protocol_compatibility.py` uses both producer and previous portable golden bodies. RF is always present; Stock is explicitly optional and the runner reports consumer membership. Remote run does not falsely claim Stock coverage.
- Provider network substitutions in ROOT tests do not replace ET worker/importer/verified-read code; these are meaningful offline integration checks, not proof of paid providers or financial analysis quality.
- Source-system reports record selected versions/worktree diffs and cleanup; the old local report is pre-commit with follow-up receipts, not the final remote commit report. Incremental RF receipt and FF Linux fixes were separately tested in release records. No new artifact inconsistency was established.
- Pre-push remains a small local smoke, not implicit skill deployment or full multi-repo testing. Ordinary CWP CI and ROOT integration are explicitly split.
- AUDIT installed runtime local imports are package-local; `audit_run.py:765-767` imports its own `audit_blob_store`, not a producer implementation. `execution_request.py` consumes explicitly named native request versions through a local adapter; this alone is a valid protocol dependency, not private CWP coupling.
- Historical migrated test files include old canary/derived fixtures. Their exclusion is documented; this audit did not run those archived onsite cases or count preserved assertion ASTs as execution. Some mixed legacy test files also have newer assertions, so coverage claims must refer to actual selected nodes rather than all 25 migrated files.

## Evidence retained

- Host command: `C:/Miniconda/python.exe -B -X utf8 -m pytest C:/Users/郑曾波/Projects/revenue-forecast-audit/tests/test_du6_current_cwp_bundles.py -q -p no:cacheprovider -o addopts= --tb=short` with `CWP_SOURCE_REPO` explicitly set to the current CWP checkout, `PYTHONDONTWRITEBYTECODE=1`, plugin autoload disabled.
- Tool outcome: 2 passed / 3.57s, exit 0. Owned `TemporaryDirectory` cleanup passed as part of the fixture and explicit source-state emptiness assertion. No product file or production data was changed.
- Review inputs: current `DECOUPLING_FIRST.md`, D3 `release.md`, `independent/review.md`, runner/workflows, selected integration implementations, AUDIT current scripts/test, old isolated and installed execution receipts.

## Independent follow-up on ROOT's CWP internal-layer finding

**A3 — P2, confirmed: pure document normalization/shared reading still has an eager runtime dependency on the catalog/storage service.** ROOT's `probe_normalization_boundary.py` and `normalization-boundary.json` are valid import-boundary evidence. I independently reran its isolated-normalization and source-contract positive-control modes in fresh processes: normalization fails specifically at `document_normalization/document.py:17 -> source_catalog/__init__.py:16 -> .service`, while `source_contract.source_version` imports successfully with zero catalog modules. The source inspection confirms shared-engine `document_understanding/__init__.py:31 -> observation_adapter.py:25 -> document_normalization.form_fields` loads the normalization package first, triggering the same dependency. `document_normalization/units.py:17`, `docx_parser.py:17-18`, and lazy imports in the HTML/PPTX parsers also use catalog-owned `NarrativeUnit`, `DocumentStructure`, or the pure `AnonymousTurnObserver`. Normal import's 54 catalog modules is a symptom, not proof that any production database was opened; this audit does **not** claim DB I/O or a current parsing outage. It proves the lower-level parser and reading engine cannot import independently when an unrelated storage-service implementation is unavailable. That is an actual internal-layer decoupling omission even though the preceding D3 milestone concentrated on cross-repository ports.

The narrow root repair is to put the small immutable document DTOs (and the pure turn-structure helpers needed by normalization) in a dependency-neutral source/document contract module, then make catalog/normalization/engine consume that one owner. Preserve the old `source_catalog.narrative_document` imports as re-exports of the exact same class objects, rather than duplicating DTO classes or changing schema/unit IDs. Make the catalog package facade lazy so importing a leaf contract/helper does not import `SourceCatalog`, acquisition, cleanup and identity services. Avoid a cosmetic lazy-only patch that leaves the normalization layer defined by storage ownership; avoid moving the whole catalog or introducing a shared service SDK. Add a fresh-process import test blocking catalog runtime followed by a tiny real HTML/DOCX normalization and shared-engine use, plus old/new DTO identity and serialization equivalence and the existing public combination smoke. These are a small responsibility-boundary test set, not new runtime gates.

