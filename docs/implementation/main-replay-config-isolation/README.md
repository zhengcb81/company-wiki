# MAIN replay configuration isolation

Base: `8479b8ad1eae5031ca6d01d5e540824cafa4a60f`.
Branch: `codex/main-replay-config-isolation-20261009`.
Preserved selector branch: `codex/main-ocr-selection-20261009` at `760ed472fc002820371da5d622d4540296f680a6`.

## Change

Replay exports runtime code without host `config/`, then creates fixture catalog/acquisition configuration. Its declared normalization profile is `offline_fixture_no_ocr`, PPTX parser `1.1.0`, and no local OCR configuration. Live retains the previous explicit Git HEAD configuration export and reports the selected profile, HEAD, config hash and parser version. Production defaults and the independent real configured MAIN node are unchanged.

The E2E probe records bounded actual AUTO evidence before result assertions, receipt decoding errors and subprocess deadline exceptions. Runner retains those JUnit properties in each checkpoint. Evidence includes receipt status/error/artifact pin/native budget, run accounting limits and hashes, run-owned job/attempt states/times/error codes, scalar selection counters/parser versions, and run-owned reservations with actual usage status and conservative charged amounts. Public read quality is saved separately after the actual read and exact replay check. Missing fields/databases/legacy config presence remain unknown.

The snapshot opens SQLite `mode=ro` with `query_only`, performs no migrations/updates, extracts scalar JSON paths, caps rows at 9 while preserving exact total counts, and caps serialized metadata at 32 KiB. It does not copy DB/raw text, prompts, full bindings, credentials, lease tokens or error detail. The existing capability classifier is unchanged: unpublished `PARSER_INCOMPLETE` requires independently checked opaque-page proof; deadline/refusal/unclassified partial remains FAIL.

## Reproduce concentrated tests

From a normal checkout (benchmark files materialized):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH=(Join-Path (Get-Location) 'src')
python -B -m pytest tests/unit/test_replay_config_isolation.py tests/unit/test_cross_market_suite.py -q -p no:cacheprovider
python -B -m ruff check --no-cache tools/cross_market_suite/runner.py tools/cross_market_suite/runtime_evidence.py tests/unit/test_replay_config_isolation.py tests/e2e/test_cross_market_rf_pipeline.py
```

The one CLI test creates one synthetic image-only PPTX and its own root/config/catalog/AUTO/jobs, imports it through `official_source_cli` with an honest local-document capture receipt, then runs public `narrative_batch_cli` under an external-network prohibition, zero budget and no OCR configuration. No vendor endpoint is used. Its native failure is the expected capability exclusion, not product success. The root is removed only after subprocess termination and assertions; an owned marker/containment/no-links check guards cleanup.

This sparse implementation worktree used read-only primary benchmark spec/points for the old tool compatibility test through `pytest.main`; it did not materialize or alter benchmark files. Config-isolation tests declare their own tiny benchmark/identity/host OCR fixtures.

## Actual results

- Meaningful RED: 5 failures in 1.21s (implicit replay config, unattested live snapshot, missing capture, missing report retention). Earlier fixture setup/name mistakes are recorded in progress.
- Concentrated GREEN: 35 passed in 5.93s (new responsibilities + existing strict failure/blocking compatibility + actual tiny CLI).
- Final legacy unknown boundary: 6 passed / 1 CLI deselected in 0.89s, no repeated CLI. This adds one distinct regression case, yielding 36 distinct passing tests.
- Ruff `--no-cache`: PASS. `git diff --check`: PASS.
- Successful tiny batch: 3.307511s; native parser1.1.0, select `PARSER_INCOMPLETE`, summary/verify `DEPENDENCY_TERMINAL`; all three jobs dead_letter; no artifact, no reservations, all native token/cost/unknown/unsettled fields0. See `tiny-cli-actual.json` for actual commands, exact times, hashes and cleanup.
- First actual tiny batch: 3.914318s, same native terminal failure and zero ledger. The test failed afterward because metadata reader used the old manifest shape. See `tiny-cli-first-actual.json`: parser metadata stays null and protection assertions are marked unexecuted. After correcting the reader to `source_inputs` (with legacy fallback), the successful run above passed. Both owned roots are absent.

The previous 71 report and its actual partial remain unchanged; its deleted stage/ledger evidence cannot be reconstructed. Original 22-page source was not read, rewritten or re-OCRed. No supplier call, full22 OCR, whole71 replay or investment/economic acceptance occurred here. MAIN owns the independent configured product node.
