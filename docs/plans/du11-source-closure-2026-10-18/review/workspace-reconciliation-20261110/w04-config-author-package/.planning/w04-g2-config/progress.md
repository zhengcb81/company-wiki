# Progress

- 2026-10-11: Read ROOT amendment, isolated AGENTS/config/CLI/fixtures and existing tests. Isolated Git status was clean. Readonly preparation evidence remains STOP/untouched. No model/HTTP/provider invoked.
- Baseline file SHA recorded in baseline.json. TDD RED is next, before implementation.

- Actual first RED: 26 failed/2 passed; load_llm missing. Fixed one new fixture iteration mistake, then focused production CLI RED reproduced NARRATIVE_MODEL_CONFIG_INVALID before implementation (1 failed). red.log/red_cli.log and SHA receipts retained.
- Added shared LLM builder/selector/validator and strict load_llm. Full loader retains legacy pytest credential relaxation and search/wiki checks. CLI now uses load_llm. Only authorized existing mock adapted (return LLMConfig; no assertions changed). Main GREEN compatibility batch next.

- First major compatibility batch: 101 passed / 1 failed, lint PASS. Sole failure: isolated sparse config.yaml absent, not product failure. ROOT approved materializing exact HEAD config.yaml, no test assertions/config content changed. First exact SHA comparison rejected CRLF/LF difference before writes; normalized bytes identical, recorded raw and normalized provenance. Receipt sparse_checkout_repair.json. Final focused batch follows.

- Final compatibility GREEN: 102 passed, 13 existing unit-marker warnings, 17.75s / wall20.699s; lint PASS; diffcheck PASS. Reports, patch and bounded SHA manifest prepared. No live HTTP/provider/model/fees, no commit/push. STOP; ROOT integrates files and owns real G2.
