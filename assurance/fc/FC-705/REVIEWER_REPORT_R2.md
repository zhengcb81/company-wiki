# FC-705 R2 Independent Review — Verdict: ACCEPTED

- Reviewer: reviewer-fc705-r2-independent (independent of the implementer; fresh clean worktree at HEAD f20a64f)
- Reviewed at: 2026-08-11
- Implementer receipt (r2): `assurance/fc/FC-705/11_implementer_receipt.json` (sha256 901bd997... on-disk / e63bc9fc... LF-canonical)
- Reviewer receipt (r2): `assurance/fc/FC-705/12_reviewer_receipt_r2.json` (one-step-lag self-hash c84b8506...)
- r1 verdict: CHANGES_REQUIRED (F1 major: gate unsatisfiable on main()-produced ledgers; F2 minor: receipt base hash erroneous) — both fixed in r2

## 1. Receipt chain and sealing hashes (r2)

| Item | Expected | Verified |
|---|---|---|
| base wiki | f610c1a752194953ed242f5cb3e17529650d0dba | EXISTS (git cat-file -e OK; `git rev-parse f610c1a` expands to it; it is the parent of 5e770e2) — F2 CLOSED |
| result wiki | 2735afdfac9a80b1c7c8fc02014da3cb43bd8179 | EXISTS, `git merge-base --is-ancestor f610c1a752 2735afd` → ANCESTRY-OK |
| revenue base == result | 76d1602a27bb70f7d901d44a5b3775f27d0dc5b9 | exists; revenue-forecast HEAD — unchanged by FC-705 |
| filing base == result | 85731b20f730da6ecc85084a2b7f04a10e75a1f9 | exists; filing-fetch HEAD — unchanged |
| plan_sha256 | 158fc1e1e4231e3c2dc71822a58931fdca64eff79fc0d4e27b8276a397f4c78a | MATCH — `git show 2d64186:...task_plan.md` (frozen plan, FC-704 precedent) |
| command_registry_sha256 | 215b8077169126b2c4a5eca9d8d6237f291757c2559f6ae6e0ae8ff1c806b089 | MATCH — `compatibility/command_registry.json` recomputed on disk |
| diff scope | F1 fix = 2 files | `git diff 6ada6fe 2735afd` = legacy_close_gate.py + test_legacy_observation.py only (34 insertions / 9 deletions); `git diff 2735afd f20a64f` = receipt only; full feature diff additionally carries IMPLEMENTATION_PLAN_FC705.md (plan doc, FC-704 precedent) |

The r2 receipt vs r1 receipt diff contains ONLY: corrected base wiki hash (F2), updated result triplet, LEG-10g scenario, mutation/note/provisional text — no evidence rewrites.

## 2. F1 fix read (commit 2735afd)

`close_gate_allowed` now:
- filters `completed = [p for p in numbered if p.get("ended_at") is not None]` — an OPEN window never counts (it is still accumulating);
- applies the `REQUIRED_CONSECUTIVE_WINDOWS` count, the last-two tail slice, consecutiveness, hits==0, and >=24h checks all on COMPLETED windows;
- returns the new reason "need 2 COMPLETED zero-hit observation windows, have N (an open window is still accumulating and never counts)".

`test_leg10g` simulates the exact main() bookkeeping (new period closes the previous): period 1 opens → not allowed; period 2 opens/closes 1 → not allowed (one completed); period 3 opens/closes 2 → ALLOWED exactly when the second zero-hit window completes.

## 3. Fresh replays (clean worktree, python -B, __pycache__ cleared)

- `pytest tests/contract/test_legacy_observation.py -q` → **16 passed** (15 r1 + leg10g)
- `ruff check` on the 3 changed files → **All checks passed**
- Full suite not rerun per instructions (r1 recorded 2183 passed / 2 pre-existing PORT-01 GBK failures; r2 change confined to gate module + tests)

## 4. Mutation replay — M1 kills leg10b AND leg10g (r1 F1 demand met)

- Mutation: completed-count guard `len(completed) < REQUIRED_CONSECUTIVE_WINDOWS` → `len(completed) < 1`
- Result: `pytest -k "leg10b or leg10g"` → **2 failed / 14 deselected** — BOTH `test_leg10b_single_window_not_allowed` AND `test_leg10g_gate_fires_after_two_completed_zero_hit_windows` fail (IndexError at `last_two[1]`). The two-COMPLETED-window requirement is load-bearing on both the pure contract and the main()-flow test.
- Reverted byte-identical: 16/16 green again, worktree `git diff` empty.

## 5. Live replays (main checkout C:/Users/郑曾波/Projects/company-wiki, branch fcap @ f20a64f = reviewed code, read-only)

- Current-state (`--period 4`, temp period file in %TEMP%): **4/4 canaries reused_exact** (CN 601899 FY24/25, HK 03690 FY24, US AAPL FY25), **legacy_bridge_hits=6**, shadow_diffs=0, **close_allowed=false** with the NEW r2 reason string — the live binary runs the fixed gate. Honest.
- Drill (`observe_canary_matrix(config, drill=True)`): **4/4 reused_exact, legacy_bridge_hits=0, shadow_diffs=0**, snapshot_policy_hash 2d3d2ee8... preserved — cutover remains READY for the canary cohort.
- Zero-write: mode=ro + query_only (sqlite-enforced); git status shows no new modifications from this review (llm_cost_log.csv + r1 files pre-date it). Catalog hash drift = ambient background worker WAL checkpointing, not the observer.

## 6. Validator

`python tools/receipt_validator.py --receipt C:/Users/郑曾波/Projects/company-wiki/assurance/fc/FC-705/11_implementer_receipt.json` → **"OK: 1 receipt(s) valid"**, exit 0.

## 7. Findings disposition

- F1 (major, close-gate-unsatisfiable): **CLOSED** — completed-windows-only evaluation + leg10g main()-bookkeeping test + M1 kill of both leg10b/leg10g + live reason-string proof.
- F2 (minor, receipt base hash): **CLOSED** — corrected to f610c1a752..., verified to exist and be the true base.
- F3 (informational, reason wording): acknowledged, no action required (r1 marked optional; new count message is accurate; residual branch only fires for completed-but-unparseable dates).

## 8. Verdict

**ACCEPTED** — no unresolved findings. FC-705's close gate is now satisfiable through the observer's own bookkeeping flow, the receipt seal chain is fully verified, and the canary-cohort cutover drill remains ready.
