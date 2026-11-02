# R7 invest E2E and evidence simplification — frozen for independent review

Canonical repository: `C:/Users/郑曾波/Projects/invest-skills`, base `a789cd07`.
11 exact delta files and SHA, full commands/results/logs, fixture migration and protected-file hashes are in the sibling JSON. No Git/index/deploy operation performed.

## What was fixed

The old frozen Biren forecast was an impossible schema3.7/engine4.0.0 pair and claimed host_signed without an actual signature. The explicit generator now computes a genuine canonical3.7/4.3.0 result from the identical embedded input. It is truthfully unattested. The generator is an opt-in maintenance CLI, never run automatically by the normal harness. RF compatibility and strong validators were not relaxed.

The harness no longer requires global registration after strong validation. Each invocation uses a fresh owned temporary directory and isolated index; parent/child networking is blocked and no dotenv or signer is used. Historical `e2e/.runs` is never read, enumerated, reused or cleaned.

Critically, the old `collect_steps_3_to_8` was dead code: main never called it. Both runs now execute those checks, including a fresh public validation of every emitted execution member and state transition. Two latent assertions were migrated to the actual current receipt shape and trimmed-text hash contract. A persisted live-phase sentinel catches future disconnection; tampering with a financial intermediate fails its public read.

The generic evidence quote10–500-character permission is removed; nonempty text, actual source/capture/content/excerpt hash and currency/unit/period constraints remain. At exactly three unchanged-value adjacent call pairs, revenue_reference is the single strong owner. The legacy branch without that reference still validates and all other independent public entries retain validation. No skip flag or new permit was introduced.

## Economic baseline was preserved

355 shared numeric leaves of the old/current RF artifact were compared: zero differences. The input SHA is unchanged. All12 fixed revenue/profit/valuation/SOTP scenario values and modulecounts are exactly equal to the old golden. The only artifact changes are genuine engine/version/hash/attestation metadata and an explanatory confidence diagnostic (confidence is not a calibrated probability). Updated golden fields are explicitly listed in JSON; no assumption, manifest, financial or valuation number changed.

Even `--update-golden` refuses existing economic/module drift before refreshing metadata. Technical metadata was first generated against a temporary copy of the old baseline, compared, then frozen. The canonical default fixture/golden branch was subsequently tested normally.

## Verification

- New initial RED:6F4P/1.77s; first GREEN10P/1.26s.
- Expanded controls:19P1fixtureF/10.65s; sole new Windows test omitted child `-X utf8`, causing stderr decode failure. Only that case rerun after explicit UTF8:1P/0.47s. This is not described as a single20P invocation.
- Existing directly affected three files:38P+3subtests/15.54s.
- Eight changed Python files: Ruff PASS.
- Offline technical migration: real CLI double-run PASS/5.52s; all phases and unchanged numeric baseline.
- Final normal canonical CLI: real double-run PASS/5.71s; phases3–8 both runs,9determinism and10exactgolden PASS; owned run tree removed.

The persisted tests are under the existing CI-covered invest-core/framework test directories. Real CLI negatives cover invalid pair, false signature claim, currency/unit and revenue mutation. Four protected RF WIP SHA and frozen Biren manifest are byte-identical. No full-suite, model, download or paid call.

## Cleanup and next

Owned scratch initially did not exist. Its baseline/log/migration/freeze evidence is embedded in JSON before cleanup. Measured final cleanup receipt follows below after exact containment/nonreparse validation. Generator registry uses stdlib TemporaryDirectory; no separately measured byte-count claim is made.

ROOT should obtain independent review of these11 files, then own normal commit/push/CI. This is a frozen implementation, not remote-CI acceptance or a new research-analysis round.

Measured cleanup: 69 files / 5846675.0 bytes removed from the exact explicitly named literal target after nonreparse checks; owned `tmp/r7ie` restored to absent. Separate `R7-invest-E2E-cleanup.json` records the receipt.

Cleanup-command disclosure: the optional PowerShell Split-Path parent guard emitted a nonterminating parameter-set error. The target remained the exact resolved, explicitly named owned directory. A subsequent fail-fast IO.Path parent check confirmed its containment and absence; see receipt. No guessed directory or history was deleted.
