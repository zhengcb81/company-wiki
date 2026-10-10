# MAIN source adapter 02 — handoff

## Scope

Only these assigned new implementation files were written:

- `src/company_wiki/automation/narrative_official_json.py`
- `tests/unit/test_official_json_narrative_adapter.py`
- `tests/integration/test_official_json_narrative_adapter.py`

Small node evidence is here. No shared PWF three files, old source, parser/layout/import/projection, production configuration, provider/LLM, installation or commit were changed by this agent. Root owns integration/staging.

## Actual API

- `NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION = "1.0.0"`: bind this distinct producer version in MAIN generation/execution.
- `open_verified_projection(catalog, *, projection_id: str, expected_projection_sha256: str) -> VerifiedProjectionView`
- `select_verified_projection(view, *, title: str, selector=select_narrative_evidence) -> NarrativeEvidencePackage`
- View: neutral `NarrativeSubject`; detached original `export_dict()`; immutable native per-field `evidence_spans`; `language: str | None`; source-pagination `coverage_complete`; isolated source descriptor `adapter` copy.

`load_projection` then `build_projection_export` runs once. Selection does not reopen or parse parents. The source ports own current bytes/status/layout/issuer/as-of checks. The adapter never manufactures a SourceRef, a second parser, permission or task ledger.

The original export remains untouched. Derived native spans add original_role/source_role/language, qa_group_id/official_record_group_id, speaker_known=false when observed, source_evidence_id and observed dates. Each field keeps its own real parent/pointer/JSON token binding. Provider translations are excluded from native language/selection; investor questions remain questions. Unknown/unclassified fields stay unknown. Record links are associations, not contiguous mixed-role quotes.

The compatibility package source_id/SHA are a real parent FK anchor only. Authoritative work identity is `view.subject`. Never feed the anchor as the projection's sole identity in downstream DTOs/generation/artifact/read. No native or undetermined language returns no evidence and needs_review/partial without selector/model calls; it does not guess zh/en. Partial pagination overrides the generic DocumentStructure line-count completeness shortcut.

## Evidence

- `red.json` / `red.log`: actual missing-module RED, exit 2, before implementation.
- `first-implementation.*`: 22/23 passed; one new legacy TXT fixture lacked the parser's explicit transcript heading. Fixed fixture, not parser.
- `second-implementation.*`: 70/71 passed; one new whitespace test guessed a nonexistent `json:` prefix. Replaced with stronger exact source-locator equality, not a changed locator/parser.
- `pre-constant-green.*`: 71 passed before explicit adapter version.
- `green.*`: final 72 passed (26 new responsibilities + 46 unchanged legacy selector cases), exit 0. Exact final source/test SHA recorded.
- `ruff.log`, `mypy.log`, `static.json`: final Ruff exit 0 and mypy exit 0 on the frozen source SHA; isolated cache removed.

Real importer, parser, catalog persistence/close/reopen, SourceVersionReader, and selector are used in integration. Cases prove both-parent actual SHA/status refusal, true parent per span, two issuers sharing one raw, wrong/unknown cutoff exclusion, source-layout refusal, one source open per parent per export and no source reopen in select. Fixture 36395 is declared synthetic for automated CI; the four actual sealed examples were previously inspected read-only and are not silently copied into these tests.

Owned pytest TEMP and its path-budget relocated TEMP were cleaned. Real provider/model calls and cost are zero. One pytest warning is the known asyncio_mode setting with plugin autoload disabled; assertions and cleanup passed.

## Remaining MAIN integration

This is the thin adapter responsibility node, not completion of AUTO or real research. Root must still wire subject-aware event/select/summary/bundle, execution/generation and adapter-version binding, publish/terminal/pin/recovery/public reads, and language=None not_processed branch. Later independent reads/publish must re-open through the source port at their operation boundary; no view serves as permanent authorization. P7 owns opt-in projection 1.0.2 stability/deep snapshots; this adapter does not hardcode its producer version.
