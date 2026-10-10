# MAIN model / summarize subject integration 03

## Delivery scope

Worktree: `C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki`.
Only `automation/narrative_model.py`, `automation/narrative_summarize.py`, two new owned tests, and this evidence directory were written. No contracts, batch, source adapter, quality helper, verification, catalog, transport, PWF shared file, P7, RF or audit changes. No commit.

## Frozen API / versions

- `PROJECTION_MODEL_REQUEST_SCHEMA = "narrative-model-request/2"`
- `PROJECTION_NARRATIVE_PROMPT_VERSION = "official-json/1.0.0"`
- `NarrativeModelRequest.from_selection` accepts shared `NarrativeSelectResult` 2.0/3.0. Official JSON gets an explicit `subject` header: `subject_id`, `subject_sha256`, `language`, `title`, `document_kind`. It never uses a projected ID as `source_id`.
- `decode_model_draft` expects the prompt version for the selected subject, parses the new `SubjectSummaryDraft`, and validates its whole identity before recovering individual claims. Actual parent-span citations are restored through the existing alias map. Both draft types use shared `project_summary_claim_quality`; each own typed draft is replaced independently.
- `NarrativeSummarizeHandler` compares full subject bindings plus metadata and uses the existing caller/context once; supplied billing metrics survive successful and invalid-result outcomes unchanged. It emits strict summary3 for official JSON and summary2 for raw.

MAIN generation must pass the new prompt/schema constants as the actual projection execution versions. This leaf does not select a provider, recreate a ledger/Worker, or introduce reuse/publication authorization.

## Semantics

Every selected span keeps its field-level role. Compact default roles have per-row overrides; a question cannot become a company statement by group membership. Groups contain only member aliases, without joining quotations, and group membership is isolated by actual parent source plus selected group identity. A narrower answer is valid with partial-context diagnostic; full-group declaration requires all members, then ordinary role validation still applies. Unknown provider extensions are dropped; translation contradictions and whole-subject identity mismatches remain failures. Language stays original.

For official JSON, no evidence or `unknown` language returns typed `SUMMARY_INPUT_UNAVAILABLE` before model configuration/call. A genuine complete `skipped_no_narrative` produces `summary_not_needed` without a model; shared contracts allow `unknown` only in that projection skip case. Completed model drafts require real `zh`, `en`, or `mixed`.

## TDD and validation

`red.log` records the initial 33-test RED with a fixture source-class mismatch. After aligning the fixture with strict 3.0 actual parent/projection and coverage fields, `red-contract-aligned.log` records 27 failures / 6 passes before implementation. Some original negative controls passed via the old wrong-prompt rejection; the final tests were strengthened to match specific role/citation/group errors. Nine more targeted controls were added for language, cross-parent group labels, complete mixed-role group, actual HTTP request serialization, and raw byte-canonical goldens.

Final `green.log`: **145 PASS**, 5.25 seconds; **42 new** and **103 directly affected legacy** tests. `ruff.log`: exit0. `mypy.log`: exit0, two source files. Three pre-change raw fixtures retain exact input SHA, JSON SHA, instruction SHA and decoded draft SHA (1, 3 and 160 spans), recorded in `before.json` and permanent tests.

Only owned temporary test/cache directories were used and removed. The repository's Windows basetemp relocation explicitly logged `removed=true`. Zero provider/LLM calls, zero dollars, no production writes. One pre-existing `asyncio_mode` warning results from deliberately disabled plugin autoload; no configuration was changed.

Reproduce from worktree:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -B -m pytest -p pytest_timeout -p no:cacheprovider -q tests/unit/test_official_json_model_subject.py tests/unit/test_official_json_summarize_subject.py tests/unit/test_narrative_model_request.py tests/unit/test_narrative_model_aliases.py tests/unit/test_narrative_summarize_handler.py tests/unit/test_narrative_partial_summary.py tests/unit/test_narrative_model_usage.py
python -B -m ruff check --no-cache src/company_wiki/automation/narrative_model.py src/company_wiki/automation/narrative_summarize.py tests/unit/test_official_json_model_subject.py tests/unit/test_official_json_summarize_subject.py
```

For mypy, use an owned TEMP cache and clean it, as captured in `static.json`. MAIN should rerun its major-node integrated tests after its other concurrent pieces land. This leaf proves typed model/summarize and offline HTTP serialization; it does not claim real end-to-end provider execution or complete publication/reuse correctness.
