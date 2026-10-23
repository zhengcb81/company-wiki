# W09 ROOT publication complete

Final machine receipt: `publication-final.json`. This supersedes intermediate “next push” execution notes in the RF publication PWF. No implementation or publication operation remains in this finite W09 node.

## Actual commits and remote

- Normal merge commit **`9dcce3049c23e974790b66d24455c1c08378447b`**, parents `10bf611166013bd68ce14bfa19bb70e89a92dd5b` + actual author `eb7c2deec3650889a10220fdfe8fccb168b28c72`.
- Current main/doc commit **`599d17b89d8baee42ce203747496731ace2d0148`**. Normal push succeeded; fresh `ls-remote origin refs/heads/main` exactly matches.
- Actual current-head [quality CI40040969386](https://github.com/zhengcb81/revenue-forecast/actions/runs/40040969386) **completed/success**, created2026-10-23T23:40:20Z, updated23:41:21Z, observed23:41:29Z. This is not a prior run's green.

## Quality and production adoption

-7 independently reviewed promotion files adopted byte-exact at formal RF paths; committed LF content also matches. Actual import owner is RF `scripts/research/authoring_projection.py`.
-13 generic authoring controls +3 existing CI-entry tests:16PASS against formal paths.2 new tests are in existing `SMOKE_TESTS`; no new gate framework, pin or compatibility change.
- Normal configured pre-commit passed Ruff/mypy/host guard. Normal pre-push performed full existing gate: Ruff all checks, mypy12source0issues, **595PASS/1SKIP/36subtests in45.28s**. Entire push52.68s. No force/skip/alternate hooks.
- Runtime source helper/CLI and3references selectively synchronized with existing `--file` plan/apply/check.3 requested roots resolve to2 physical installations because `.claude` aliases `.agents`; **10 actual file writes**. Both physical installations match all **103 owned runtime files**, selected and unselected drift0.2 engineering tests were not installed. Configuration/output byte hashes andmtime unchanged.

## Preservation and scope

- All3 assurance WIP have originalSHA+mtime, not committed. Normal pre-commit auto-stash restored identical bytes; only its incidentalmtime was reset to the recorded baseline after SHA equality.147 preexisting output files have unchangedSHA+mtime and remain unpublished.
- Author worktree remains at eb7c2dee with clean status;28 original reviewed artifacts retain exactSHA. All author delivery and Git history retained. The earlier proposed exclusion was rejected before mutation; the implemented alternative deletes nothing. The full incoming research delivery remains in RF; later deduplication is ROOT responsibility.
- START_HERE only gains current-entry clarification at the top; original author body retained as an exact byte suffix. It points to mother CURRENT_STATUS and RF `docs/plans/w09-root-publication-20261024/task_plan.md`.
- Own formal test temporary directory restored to its initially absent state, with cleanup receipt. Prior27MiB isolated attempt, originalREDs and captures remain. No key reads, model/API provider calls, downloads, fee-ledger or unknown-hold reset.

Mother PWF remains ROOT-owned. W08 new-summary adoption and W12 four-way wholecompany review remain open; these source/method engineering greens do not certify fullcompany economics.
