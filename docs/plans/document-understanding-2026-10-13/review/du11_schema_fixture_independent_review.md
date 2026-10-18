# DU11 schema-fixture / parallel-push independent review

Conclusion: **PASS for the three test-only corrections**, bound to final file SHA in companion JSON. No confirmed unresolved defect in this delta. This is not a complete push/remote CI result, source-quality acceptance, supplier C or whole-project completion.

Independent reviewer: `/root/du10_gold_reception_review`. Read-only source/diff/schema/log review; no tests repeated, no production edits, no configuration/environment/key inspection, no commit/push. Execution evidence is explicitly reused from ET's focused102-test run, not claimed as this reviewer's independent rerun.

## Original four failures and correct responsibility

The normal push log `.planning/shared-reading-production/du11/push-92976930.log` records4FAIL/6569PASS/24SKIP in542.35s. The hook returned nonzero and blocked push. The failures are three obsolete fixture expectations, not evidence that historical unknown costs should be discarded or that paid response storage should be removed:

1. `test_ci_push_selection.py` expected one combined invocation although the actual reviewed full-push path starts two isolated phases. Its assertion failed on2versus1.
2. `test_narrative_run_ownership.py` compared every `SELECT *` reservation tuple across schema migration, rejecting the new twentieth nullable column even when all historical values were identical.
3. Two tests in `test_replay_config_isolation.py` used positional19-value INSERT against the current20-column table, so fixture setup failed before reaching their isolation assertions.

## 1. Parallel push coverage and failures remain strict

`tools/pre_push_gate.py::main` still sends full `tests/unit` once and the complete remaining nonunit `FAST_CONTRACT_CASES` once. `_run_parallel_pytest_gates` waits for both futures, returns a failing child code, and records wrapper exceptions as failure. Each child retains its own temporary directory and subprocess deadline. The delta changes no production gate, test list, timeout, skip marker or case selector.

The corrected test parameterizes **units failing** and **contracts failing**, each expecting nonzero7 even when the other phase is green. It requires exactly two invocations, the unit command's exact target suffix`[tests/unit]`, exact equality of smoke targets to all nonunit FAST cases, uniqueness of smoke targets and no duplicate unit cases in smoke. The assertion is independent of thread completion order. Existing8parallel-phase tests additionally verify simultaneous startup, either-phase/both-phase failure, wrapper exception propagation, full-dispatch case union and real distinct temporary scratch cleanup. The focused execution includes those tests. Nothing was removed to get green.

## 2. Real migration verifies old19fields and genuinely nullable v7 response

`migrations.py` declares `SCHEMA_VERSION=7`; `_DDL_V7_STATEMENTS` is exactly `ALTER TABLE narrative_model_reservations ADD COLUMN paid_response_json TEXT`. The real migration executes it only at version6, then validates expected structure and database integrity. This is additive nullable storage, not fabricated historical paid bytes, a second reservation or a fee rewrite.

The changed ownership test builds a populated historical v3 database without running the current migration algorithm, preserving its unknown reservation, attempt, runtime and owner facts. It then calls actual `migrations.migrate_database` with only a backup hook. It still requires every applied version4throughcurrent, exact backup bytes, identical table inventory and exact equality of every unrelated table. For reservations it now requires:

- Existing column names, in original order, plus exactly `paid_response_json`.
- New column is nullable and has no declared default (`notnull=0`,default`None`).
- Every row's **entire old19-field prefix** equals its original row, including unknown usage, reserved amount90, bounds, times, request/attempt/run IDs and unknown error code.
- Every new value is truly SQLNULL. Old responses cannot be invented.

The owner/generation upgrade checks and read-only denial remain intact. The reservation table was not exempted from validation; its old tuple width was replaced with stronger explicit additive-column validation. This test is present and passed in ET's focused XML, so v7 is actually executed by production migration rather than asserted only from schema strings. Existing separate v6 migration tests remain unchanged and available; they were not newly rerun for this review.

## 3. Replay fixture uses named columns without weakening unknown accounting

`native_db` still constructs the database through actual `AutomationStore` migration. Its INSERT now names exactly the original19reservation columns, which is the correct fixture contract for additive schema evolution. Immediately afterward it verifies all19stored values, including usage`unknown`, original20+30token bounds, reserved40microUSD, no known usage/response/output and the original timeout state; it separately requires new `paid_response_json` to beNULL.

The consuming tests still require unknown charging conservatively at50tokens/40microUSD, unknown reservation count1, null artifact, partial stage, native parser1.1.0/no OCR config and byte-identical database after capture. Their private-text/runtime-ID redaction and bounded evidence size checks remain. No paid usage was refunded, transformed to zero, called known or hidden behind a fake response. The second old-binding/OCR-unknown test still runs through the same corrected fixture.

## Focused execution and scope limits

ET's `schema-fixture-green.xml/log/json` and `schema-fixture-review.json` agree:102PASS,0FAIL,0ERROR,1JUnit `record_property` compatibility warning; pytest16.67s, outer process21.147s, exit0. Scope is the three changed files plus existing temporary-scope and parallel-phase tests. Three actual test-file SHA values match this review's reads. ET reports Ruff/diff checks PASS and both outer scratch and relocated basetemp removed. The log explicitly records relocated cleanup removed=true. No repeated full suite is needed to establish this narrow test repair; the next normal push remains ROOT's responsibility.

No source changes or original/config writes were made for this review. Final receipt records actual source/test/evidence hashes and static test-name retention. If any of the three test bytes changes afterward, this conclusion does not automatically cover it.
