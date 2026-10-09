# Progress

2026-10-09: MAIN card and worktree AGENTS read; clean branch/base verified. Applied planning-with-files skill; PWF selected only at this package documentation root. Structural exploration used main CodeGraph first. No code edits yet; no external model or network calls.

2026-10-09 RED: python -X utf8 -B -m pytest tests/document_normalization/test_local_pptx_ocr.py -k "current_pptx or image_body" -q -p no:cacheprovider --basetemp=docs/implementation/main-local-pptx-ocr/.test-temp-red. Exit1; 2FAIL/0.70s: {256,260}!={1,2}, normalize_document unexpected ocr parameter. Owned pytest relocated root restored by repository cleanup hook. Began versioned pure PPTX changes; HTML1.0.0 unchanged.

## 2026-10-09 implementation checkpoints

- Initial responsibility RED: 2 failed / 0.70s (actual slide IDs 256/260 instead of display pages 1/2; missing explicit OCR composition interface). Test fixture built valid package bytes; no remote requests.
- Versioning/composition/replay checkpoint: 80 tests passed / 10.89s, exit 0. Follow-up efficiency + adapter subset: 17 passed / 3.66s, exit 0.
- Efficiency test: initial three media -> 3 calls; 10 selected spans / two media -> 2 calls; forged shape/media/box refused. Models/config/dependency failures remain named, never skip-success.
- First real runner attempt refused installed API mismatch (RapidOCR engine_type requires Enum); corrected to verified EngineType with matching fake test. No successful output artifact.
- Second real attempt completed all image recognition, then refused legacy benchmark alias src_presentation as invalid EvidenceSpan source ID. No successful output artifact. MAIN notified; awaiting public official PPTX import support to generate a real TEMP-catalog SourceRef. No fake canonical ID.
- QA original images viewed at pages 1, 3, 7, 10, 12, 18 in owned cwocr-qjn2cp9j temp. Pages 7/12 are dense body; page18 adds numeric table check; 3/10 were candidate agenda/divider, not counted as dense body acceptance. Cleanup remains mandatory after final QA comparison.

## 2026-10-09 concentrated real acceptance

- MAIN public official source flow first reached 28 PASS and stable interface; then the TEMP public-import + SourceVersionReader read succeeded. Actual SourceRef2.0 receipt retained with unknown published date and legacy-alias mapping.
- Fixed-deck command: python -X utf8 -B docs/implementation/main-local-pptx-ocr/run_real_with_temp_import.py --main-project C:/Users/郑曾波/Projects/company-wiki --suite C:/Users/郑曾波/Projects/company-wiki/benchmarks/cross_market_rf/cases.json --object-root C:/Users/郑曾波/Projects/revenue-forecast/output/cross-market-rf-e2e-2026-10-08 --ocr-config <owned verified_local_config.json>. Exit0, parent hard240s; full145.549077s, selected replay16.570420s, 1067 lines/22 pages,0network/POST. TEMP finally removed and raw unchanged.
- Bounded numeric follow-up command: run_real_numeric_qa.py with explicit archive object/config/import receipt. Exit0;6 selected excerpts,2 inferences14.822453s,0network; no full-deck rerun.
- Actual visual differences and significant omitted body lines documented in REAL_VALIDATION.md; coverage remains false. QA images + marker finally removed from exact owned root; all3modelSHA unchanged.
- Concentrated deterministic suite:81PASS/14.51s before the final explicit-empty-version and current-global-adapter legacy protection regression. Final gate result follows below.

## Final targeted compatibility gate

- `python -X utf8 -B -m pytest tests/document_normalization/test_local_pptx_ocr.py tests/document_normalization/test_local_ocr_adapter.py -k 'explicit_unknown or legacy_pptx or offline_engine' -q -p no:cacheprovider`: exit0,4PASS/0.49s,15deselected. Checks final no-inference preflight, explicit unknown/empty version refusal and old replay under configured global OCR. No broadened test or full-deck rerun.
- Normal Git hooks inspection: core.hooksPath resolves worktree .githooks; pre-commit=false and commit-msg=false. Missing hooks recorded; no hook bypass or false pass.

- First scoped git add refused owned documentation outside the existing sparse-checkout definition; no commit ran. Retried staging these explicitly assigned paths with git add --sparse, without changing sparse configuration or bypassing hooks.

## Delivery

- Final Ruff scoped implementation/tests/all3 real runners: exit0, All checks passed. `git diff --check`: exit0.
- Normal implementation commit: a9534e5fb52e00c60b6b8cc5e015b4990f0eec6c, base 964886f887347c7a789402347f9ecd3172cf8c8c, branch codex/main-local-pptx-ocr-20261009. No hooks were bypassed; required hook files are absent, so no hook pass is claimed.
- Final documentation follow-up adds HANDOFF/handoff.json and stamps this tested implementation head; its containing commit is the delivery head resolved by Git. This avoids a self-referential commit hash in its own tracked manifest. No code changes after implementation commit. No merge/push/install.
