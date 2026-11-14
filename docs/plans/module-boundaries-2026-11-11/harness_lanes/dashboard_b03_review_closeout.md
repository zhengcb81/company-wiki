# Dashboard B03 independent-review closeout

## Assignment

Close the stale B03 repair handoff as an evidence-only task. Do not merge its old product branch into Dashboard main. The current Dashboard main keeps the modular `application/ops`, owner adapters, and `apps/web/src/features` structure; the old branch's concentrated `application/service.py`, `adapters/iqs.py`, and `views/QuickScan.tsx` implementation must not be restored.

## Baseline and observed gap

- Current Dashboard main observed by ROOT: `ff6e764f1e4da3aa9de73d1469770a653b8af654`.
- Historical branch: `codex/dashboard-iqs-b03-company-result@8f126ed1`; it has 19 branch-only commits while main has 196 commits not present on that branch. The branch is neither an ancestor nor a fast-forward candidate.
- Its working tree's `.codegraph/config.json` drift was restored. The remaining uncommitted files are confined to the B03 repair-chain script and its own `.planning/.../X-IQS-B03-COMPANY-RESULT-REPAIR-01` handoff/evidence directory.
- `evidence/review-r1.md` still contains literal `[ROUND4_VERDICT]` and `[R1_FINAL_VERDICT]` markers; `handoff.json` says `r1_owner_completeness_authority=PENDING_ROUND4`. R2 reports `CLEAN / 0 OPEN (round 2)`. Do not treat R1 as passed or the handoff as complete.
- Existing recorded B03 functionality is represented on current main through the modular Dashboard paths. Reconfirm the exact mapping against current code and tests; do not infer that every historical commit should be carried forward.

## Allowed scope

- Read the B03 handoff, source/review receipts, and current Dashboard/StockWiki public contracts.
- Use a separate clean checkout/worktree for any rerun. Do not change the shared B03 checkout while another harness may be inspecting it.
- Write only B03 closeout evidence in its own handoff directory. If the evidence needs a durable coordination summary, report it to ROOT; do not write into Dashboard product source or StockWiki source.

## Required closeout

1. Bind the independent R1 review to the exact source commits it actually inspected. Reproduce the reviewer's original NEW-2 and HIGH-2 probes from the receipt, including the schema-2-to-3 trigger migration and release-of-record import/publication cases.
2. If the original source snapshots and commands are reproducible, rerun the focused StockWiki and controlled-chain checks in isolated disposable roots. Do not touch a production database or user data.
3. Review the second-level receipts and hashes. If a check cannot be rerun because its historical dependency is unavailable, mark it `NOT_RUN` with the reason; do not turn an old green receipt into a new pass.
4. Replace the literal verdict markers only when the independent reviewer supplies an explicit final verdict tied to the actual reviewed SHA. Otherwise mark the package `INCOMPLETE / NOT ACCEPTED`, explain the missing evidence, and stop.
5. Produce accurate final `handoff.md` and `handoff.json` with exact reviewed refs, commands, results, limitations, and no false claim of merge or acceptance.
6. An independent reviewer other than the implementer must review the final evidence-only diff and its source bindings. Fix evidence errors; do not modify product code in this task.

## Acceptance

- No product-code changes in Dashboard, StockWiki, IQS, or service repositories.
- The old implementation is not merged into Dashboard main; current public module boundaries remain intact.
- R1 and R2 statuses in the final handoff agree with the review files and are bound to precise source SHAs.
- Any unavailable check remains explicitly open/NOT_RUN.
- The handoff distinguishes: historical feature behavior represented in modular main, old branch commits not merged, and any unresolved evidence obligation.
- Temporary test roots are absent after the run; no original company material is changed.

## Handoff interface

Return the final handoff paths, exact source refs, changed-path list, reviewer's independent role, test commands/results, temporary-root cleanup receipt, and remaining open items. Do not merge or push product code. ROOT decides whether the evidence-only closeout can be archived and whether the old local branch/worktree can be retired.
