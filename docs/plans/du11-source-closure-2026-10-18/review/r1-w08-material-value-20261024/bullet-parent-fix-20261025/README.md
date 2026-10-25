# Annual report bullet-parent context check

This bounded, read-only replay checks the frozen Wuxi AppTec annual14 selection against the current public source-selection path. It does not grade generated summaries or change the existing 8 pass / 6 partial / 0 missing content review.

The root cause was structural: the report labels the TIDES business parent with a dash bullet and places business facts under indented roman-numbered children. The native list ancestry finder previously recognized numbered parents only. The fix accepts source-marked bullet parents while retaining same-source, same-role, column, physical-overlap, indentation, list-marker, page-neighbour, and existing continuation limits.

## Evidence

- `independent-review.md` and `.json` record the final independent **PASS_NO_BLOCKER**. The review accepts source context and evidence integrity only; it does not change the 8 pass / 6 partial / 0 missing content result.
- `replay-receipt.json` binds the input scope, source index, original source ref, selector output, trace, runner and code-tree digest. The current production route reported a 112-span limit; no selector limit was passed or overridden. The 48,000-character and 16M work budgets remain unchanged.
- `parent-context-check-v3.json` is the authoritative structural check. It verifies the replay receipt's selection, trace, runner, observer and frozen checklist hashes, rechecks the full production Python source-tree digest, and confirms that the page-14 TIDES parent is selected as context-only and is in the required context for the relevant child packages. Its checks use explicit exceptions that remain active under `python -O` and `PYTHONOPTIMIZE`; its result file is created exclusively so an existing result cannot be overwritten. The earlier `parent-context-check.json` is preliminary; v2 records the same successful hashes but predates the optimization-safe fail-closed fix.
- `focused-regression.log`, `quality-checks.log`, and `diff-check.log` preserve the final command output: 155 related tests passed, Ruff passed, and `git diff --check` passed. The two-test RED that preceded the implementation is described in the PWF progress entry; its console output was not saved.
- `verifier-safety-check.log` records the initial optimized-mode no-overwrite checks. `optimized-overwrite-rejection-final.log` closes the independent review's evidence note by recording both expected refusals and the v3 result SHA before and after each run, showing byte-for-byte stability. `verification-final.log` records explicit exit codes for the final Ruff and diff checks; the earlier `diff-check.log` predates the PWF whitespace cleanup and has no captured exit code.
- The date for the Taixing peptide capacity build and the `>100,000L` total are selected as distinct evidence spans. The trace records adjacency, but no dependency is added between them; the evidence does not claim that this capacity was completed on that date.
- The on-disk annual report SHA is checked against the frozen `SourceRef`. The source tree/config/catalog remain stable, with no download, raw copy, model call, or content regrade.

## Reproduction

From the repository root, with the existing local Revenue Forecast audit scope and source index available:

```powershell
python docs/plans/du11-source-closure-2026-10-18/review/r1-w08-material-value-20261024/bullet-parent-fix-20261025/replay_all_targets.py `
  --trace-output docs/plans/du11-source-closure-2026-10-18/review/r1-w08-material-value-20261024/bullet-parent-fix-20261025/trace.json `
  --scope C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution_replays/r1-remediation-02/coordinator-effective-scope-budget-20261023.json `
  --source-index C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution_replays/r1-remediation-01/phase_b/research/source_refs_index.json `
  --oracle .planning/r1-w08-real-20261023/oracle.json `
  --output docs/plans/du11-source-closure-2026-10-18/review/r1-w08-material-value-20261024/bullet-parent-fix-20261025/selection.json `
  --code-root .
python docs/plans/du11-source-closure-2026-10-18/review/r1-w08-material-value-20261024/bullet-parent-fix-20261025/verify_parent_context.py
```

The replay runner refuses to overwrite an existing selection, trace, or receipt. The final verifier also refuses to overwrite its result. Reproduce in a fresh sibling evidence directory: copy the two runner scripts and the frozen inputs/README, then update only the output paths passed to the replay command so they point inside that new directory. Re-running in this populated evidence directory is expected to stop rather than replace evidence. This is source-selection evidence only; an independent content review is required before changing any target's pass/partial status.
