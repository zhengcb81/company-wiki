# WP03 lint amendment — STOP

## Trigger and exact change
ROOT's normal commit was correctly stopped by the existing pre-commit gate. No commit or hook bypass occurred.
Original integration log: evidence/integration/rf-publication/normal-commit.log; SHA-256 da20b69e2af5a9d70b7b5e065ff4a1f629912be6fecbef08b551c4f1881b83ca.

Only three source/test files changed:
- scripts/revenue_backtest.py: removed now-unused ENGINE_VERSION and FORECAST_SCHEMA_VERSION imports.
- tests/test_w04_public_consumer.py: explanation of the existing path bootstrap and three statement-local noqa: E402 markers.
- tests/test_w04_snapshot_delivery.py: the same explanation and four statement-local noqa: E402 markers.
No lint configuration or forecast/snapshot/consumer logic changed.

CodeGraph was queried before editing. An AST scan of all 466 current RF Python files found zero import or qualified-attribute consumers of these two names through revenue_backtest, with no parse errors. Both constants remain defined at their existing canonical modules. Three-file AST comparison is identical after removing only the two expected import aliases from the old backtest AST; both test ASTs are identical without normalization.

## Verification
- One full Ruff invocation on all nine WP03 delivered source/test files, no rule selection: PASS, ruff 0.15.18.
- Existing pre-commit mypy scope (scripts/contracts/, scripts/schema_compatibility.py, scripts/filing_fetch_client.py, scripts/trust_anchor.py): PASS, 10 source files, mypy 1.19.0.
- Only the two new W04 test modules: PASS, 30 tests in 0.77 s, pytest 9.1.1.
- git diff --check: PASS.

Exact commands, exit codes, complete output logs and log hashes are in check-results.json and the four .log files. Three changed source hashes are in source-amendment.json; all nine delivered source hashes are in artifact-manifest.json.

## Boundaries and handoff
Git index SHA before and after is f5d1226e3dd940b58591fcfe97368137a515623eb38e182b74dbcbd2d3d1d027: unchanged. No add/commit/push/install was performed.
Original handoff manifest remains f8caa96ce87de895dbd97057028ce10b74da13d9f3ad9a1e206661c56d4ccda8. The original review/handoff files remain historical evidence; this amendment is a new evidence record.
Fresh owned C:/tmp/w04rf-lint-20261011 was validated within C:/tmp with no reparse points, then removed to restore its pretest absent state. Shared WP01 fixture, canonical RF assurance/output WIP, old runs/raw/config/Dayu and sibling WIP were not changed.
Provider/HTTP/model/paid calls: 0. Prior mother budget 413778 remains unchanged.

Not rerun: 204 affected regressions, prior 284/551 suites, large cross-repository E2E, economic forecast acceptance, commit/push/install. ROOT owns those remaining publication and acceptance actions.
STOP: source writes complete. ROOT may inspect the amendment and resume the normal commit gate.
