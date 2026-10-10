# MAIN official JSON select handler — isolated TDD handoff

## Owned write set

- Worktree `C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki`.
- `src/company_wiki/automation/narrative_select.py` SHA256 `285230cade8ea127cd731b1b1fea68266ccee21c6a2f386ce62c682376a22c74`.
- `tests/integration/test_official_json_select_handler.py` SHA256 `128974509656dffaf492bfd1525b3bcb27dca297603dd43875fd49b82f61e7f0`.
- This evidence directory only. No commit; ROOT owns staging and MAIN composition.

## Actual API and responsibility boundary

`NarrativeSelectHandler(*, reader, pdf_parser=parse_pdf_bytes, selector=None, normalization=None, projection_catalog: Any | None = None)`.

Only an actual event subject `kind=official_json` opens `open_verified_projection(projection_catalog, projection_id=subject.item_key, expected_projection_sha256=subject.subject_sha256)`. This source adapter loads and exports once. Source ports verify all current parent bytes/state/layout/issuer/as-of. The handler does no direct SQL/path access and does not reread the first parent as the entire subject. Full verified `NarrativeSubject` is compared with event binding. No PDF or transcript fallback for projections.

`select_verified_projection` calls the unchanged real selector over per-field native evidence. Result public DTO is exact `narrative-select-result/3.0`: schema_version, subject_binding, source_metadata, parser, selector, selection, evidence_spans, prompt_review, summary_scope. Parser identity comes from actual source span `parser_name/parser_version`, currently `cwp_official_json/1.0.1`; no invented adapter key or pin. Native original role, source_role, true parent, locator, record group, times, and source_evidence_id survive selector processing. No provider translations enter selected evidence.

Captured and actually exported parent API pages count as pages_total/pages_read; no guessed TXT lines or tables. Missing pages remain coverage_complete=false/status=partial. `view.language=None` gives typed SOURCE_LANGUAGE_UNDETERMINED and zero model use; projected event metadata may explicitly say unknown, never defaults to zh/en. Prompt review is not_reviewed with null bindings: diagnostic, not an invented whole-parent review receipt. Old raw result/reader/normalizer/PDF/TXT wire remains unchanged.

## Actual validation

- Initial RED: 13 failures before implementation, includes two new-fixture errors recorded honestly in red.log.
- Fixture-corrected RED: 13 failures from missing projection dependency/import/branch (red-fixture-corrected.log). Empty native fields use a present attributable issuer record, not an impossible empty issuer page.
- First implementation: 66 PASS / 1 new-test failure. Existing HandlerResult is a mappingproxy; corrected test to assert immutable direct access and detached to_dict output isolation, no product relaxation.
- GREEN: 67 PASS in pytest 7.65s (13 new integration responsibilities, 28 unchanged legacy select handler responsibilities, 26 source adapter responsibilities).
- Ruff exit0, 0.177s; mypy exit0, 23.942s, exact own source only.
- All test/source catalogs are owned TemporaryDirectory environments. Runner own TEMP and Windows path-budget plugin TEMP both report removal. No production source/config/DB writes. 0 external API/LLM calls and $0 cost.
- Green saved-log SHA256 `c7a7db8bc33dd82e51b200c0c574fdfc0e92a153d65fc767114e0086d9a6c4f2` (bytes-preserving receipt).

## Test checkpoints

Real official source import, parser, projection persistence, source catalog, event contract, ExecutionSnapshot/JobExecutionContext, and actual selector execute together. Tests cover two true parents opened once each, answer-before-question, actual parser identity, public DTO shape, native two-issuer separation, translation exclusion, full and partial coverage, changed bytes or retired second parent refusal, no native-language fields, event relabeling (issuer/coverage/language) refusal, missing configured projection port, typed unknown layout port refusal with no fallback, and nested mutation isolation. The unknown-layout handler case deliberately injects the source port's named refusal; impossible layout persistence is not faked.

## Remaining MAIN work

ROOT owns production catalog factory composition and the rest of the DAG (summary/replay/verify/batch). P7 leaf implementation remains independently owned; its final parser producer version must receive the combined major-node rerun. This node is selected-evidence handler completion only and is not a claim that AUTO or full end-to-end integration is complete.


## Follow-up: exact native whitespace and source NFC display

Transport review identified that the initial adapter trimmed JSON fields while retaining full-field source locators. An old new-unit test even expected this trimming, exposing a responsibility-test gap. New byte-backed replay tests first failed, then the adapter introduced its private `_NativeProjectionUnit`: source-export text keeps all leading/trailing spaces, tabs, CRLF, newlines and NBSP. Existing PDF/TXT normalized unit rules remain unchanged. The real selector's transient matching representation is restored to original native evidence before export.

Source EvidenceSpan v1 explicitly displays NFC text; original decoded source identity remains pinned by decoded_sha256. An additional decomposed-Unicode test asserts that exact distinction and that this adapter makes no further rewrite. Replayed original decoded text, source locator, original decoded SHA and existing NFC display remain separately verified; comparison is not bypassed.

Adapter version is now `NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION=1.0.1` to prevent generations from reusing the prior trim semantics. Source SHA `fb78b6a5989bf6813b2082d6f8493850228d672284e47c181664813812f4aab5`. Adapter unit-test SHA `4896cf3df0c8cbd8e1c99567c2a25fa3780e42891ef13aeb7b582643c9f9eb31`; integration adapter-test SHA `b5328d2396fa783cb42c41ec707b54781aafd51054ad06197a02769139e21e1d`.

Final isolated result: 71 PASS / Ruff0 / mypy0, pytest9.65s and mypy21.818s; all owned TEMP removed, 0 external calls. See native-text-red.log, native-text-green.log (records old incorrect trim expectation), native-text-final-green.log/json and native-static.json. No commit. This supersedes source-adapter-02's 1.0.0 text behavior while leaving select.py wire SHA unchanged.
