# R1 contract debt repair (isolated worktree)

## Goal
Repair the four validated R5 RED contracts on codex/r1-contract-debt based on45195e96. Keep the mother checkout and running RF source code/data frozen. No network, live LLM, installs or Dayu operations.

## Phases
1. Capture isolated baseline31 tests and import/config/original integrity — complete.
2. Add meaningful projection/behavior/golden evolution RED tests before implementation — complete.
3. Repair narrow store projections, pure identity boundary and versioned current golden — complete.
4. Run scoped GREEN checks and independent agent review; fix findings — complete (195 GREEN, PASS_CONTENT_BOUND, zero open blocking findings).
5. Commit only owned changes; write exact handoff MD/JSON — in_progress.

## Next Step
Run normal commit hooks for the reviewed source content, then write exact branch/commit handoff.

## Constraints
- Only this worktree changes; existing untracked .planning history remains intact.
- Use mother CodeGraph index for shared451 starting structure, per ROOT direction; worktree has no index.
- No all7k suite or paid E2E. Existing focused migration/terminal/paid-recovery/wire tests only.
- Independent reviewer slot coordinated by ROOT after implementation.

## Errors
- Default sandbox git status sees worktree metadata incorrectly; approved read confirms the requested clean branch. All worktree writes and hard-link tests use approved execution.
