# W05 delivery to MAIN

## Scope / branch

`codex/fresh-native-documents-20261009`, base `cba23b8eb27cf63b47517d62539b3fe3d86bd63b`. Normal commit exact SHA is returned in the lane message; MAIN records it in the frozen main PWF after acceptance. Ten source modules are listed in `selected_installation_delta.json`; seven test/support files and this own PWF package. No install, merge or push performed here.

## Executable major acceptance

Use normal OS execution in this worktree, do not forward production credentials to the isolated subprocess. Tests themselves select only OS bootstrap vars plus synthetic loopback keys.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest tests/document_normalization -q --tb=short
python -m pytest tests/contract/test_official_transcript_layouts.py tests/contract/test_transcript_material.py tests/contract/test_transcript_json_material.py tests/contract/test_official_capture_recovery.py tests/contract/test_zr509_html_capture.py tests/unit/test_narrative_evidence.py tests/unit/test_narrative_language.py tests/unit/test_narrative_generation.py tests/unit/test_narrative_format_pipeline.py tests/unit/test_narrative_select_handler.py tests/unit/test_narrative_verify_handler.py tests/unit/test_native_document_pipeline.py tests/integration/test_official_source_flow.py tests/integration/test_native_document_pipeline.py -q --tb=short
```

Existing normalization tests import bare conftest, so run the first package in a separate pytest process. No new CI gate introduced. Results:103/103 normalization and243/243 pipeline; latest source-ordinal edits independently rechecked4/4 native unit/E2E. Focused ruff and existing evidence/language mypy are green; normal repository commit hooks run normally.

## Real source proof

`real_msft_observation.json`: immutable273436-byte MSFT SHA bdc90bf78dbf55ec3f1d789f1f76ebd2e97c7aab51dcc24a262f5d512fb47656,481 original extracted lines, true body90–414,515 parsed units,41 selected and41 replayed without failure. SHA and mtime unchanged. Earlier Trace Id defect observation and genuine RED logs retained. No real original copied into Git or modified, no true-source model/API request.

## Cleanup / source integrity

Integration suite starts with baseline sentinel in independent `cwW05-*` TEMP, imports DOCX + HTML, runs real isolated Worker subprocesses against loopback server, checks public replay/roles/language/claims and exact source bytes, repeats without extra calls, preserves baseline then removes owned test directory. Current cwW05 TEMP residue count0. No production raw, catalog, config, sealed/mFresh, installed skills, W03 model caller/summary, FF/ET/RF, CI/hooks changed.

## Pending MAIN decisions / limitations

- Independent M2 source review, merge/push and exact selected-copy install belong MAIN. Delta manifest hashes describe this lane's LF working bytes; ordinary Windows checkout may use CRLF, so compute installation SHA from actually tested source bytes.
- M3 real CN DOCX official acquisition and real MSFT RF evidence consumption remain pending at MAIN. This lane does not write any investment research state or declare those roots closed from synthetic tests.
- Second issuer true HTML original was unavailable in assigned inputs; second generic labelled speaker layout is synthetic, not claimed real generalization.
- Ordinary DOCX paragraphs, direct tables/cells, Q/A and inline Q/A, duplicate headings and tracked edits supported. Images/opaque objects, header/footer and complex unparsed table wrappers remain explicit extraction coverage gaps. No OCR, relationship fetching, translation or full Markdown artifact introduced.
- Natural transcript without observed END/shutdown remains partial with named transcript_end_missing. Known legacy explicit complete-heading layout retains EOF semantics, and old0.1.1 spans remain replayable. New0.2.0 generation does not silently reuse old parsing.
