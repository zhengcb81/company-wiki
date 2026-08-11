# FC-705 Independent Review — Verdict: changes_required

- Reviewer: reviewer-fc705-independent (independent of the implementer; fresh clean worktree at HEAD 6ada6fe)
- Reviewed at: 2026-08-11
- Implementer receipt: `assurance/fc/FC-705/11_implementer_receipt.json` (sha256 60d16b49...)
- Reviewer receipt: `assurance/fc/FC-705/12_reviewer_receipt.json` (one-step-lag self-hash 28cdc1b9...)

## 1. Triplets and sealing hashes

| Item | Expected | Verified |
|---|---|---|
| revenue base == result | 76d1602a27bb70f7d901d44a5b3775f27d0dc5b9 | exists; repo HEAD — unchanged by FC-705 |
| filing base == result | 85731b20f730da6ecc85084a2b7f04a10e75a1f9 | exists; filing-fetch HEAD — unchanged |
| wiki result | 5e770e202df5e1e597a506dd7171c6c3a554d9d9 | exists; receipt commit 6ada6fe on top |
| ancestry | base -> result | ANCESTRY-OK (against actual base f610c1a752) |
| plan_sha256 | 158fc1e1... | MATCH (frozen task_plan at revenue 2d64186; on-disk plan refreshed by status headers — FC-704 precedent) |
| command_registry_sha256 | 215b8077... | MATCH (compatibility/command_registry.json) |
| diff scope | 3 allowlisted files | 3 files + IMPLEMENTATION_PLAN_FC705.md (plan doc — FC-704 precedent); receipt commit = receipt only; zero unrelated changes |

Discrepancy (finding F2, minor): the implementer receipt's base_triplet.wiki hash f610c1a4dfb84c5b2ba87eebbbc0e39a37afbf6c does not exist anywhere; the actual base is f610c1a752194953ed242f5cb3e17529650d0dba (identical 7-char prefix, verified as the parent of the sealed result). The seal chain is fully verified against the real commit.

## 2. Fresh replays (clean worktree, python -B, __pycache__ cleared)

- `pytest tests/contract/test_legacy_observation.py -q` → **15 passed**
- Phase-7 cluster (legacy_observation + fc704 + fc703 + fc702 + fc701 + fc604) → **47 passed**
- `ruff check` on the 3 changed files → **All checks passed**
- PORT-01 spot-check: 2 failed / 3 passed — reproduces the implementer's recorded pre-existing Windows GBK failures; file untouched by FC-705
- Receipt validator: **OK: 1 receipt(s) valid** (exit 0)

## 3. Mutations (both killed, both reverted, worktree clean)

- M1 (single-window gate): test_leg10b FAILS (IndexError at `last_two[1]`) — the two-window requirement is load-bearing.
- M2 (writable SourceCatalog in the observer): test_leg11 FAILS on catalog hash change (cf8c85e4... -> 1e7032da...) — empirically proves the read-only facade is what prevents writes. SourceCatalog.store is lazy (no WAL/DDL on construction); _ReadOnlyCatalog overrides the store property with a fetchone/fetchall facade over a mode=ro + query_only connection; the fixture catalog is byte-identical before/after.

## 4. Live replays (production catalog, read-only; temp period file outside the repo)

- Current-state (period 4, temp ledger): 4/4 canaries reused_exact, legacy_bridge_hits=6 (production flags: v1 reader + bridge on), shadow_diffs=0, close_gate close_allowed=false — honest.
- Cutover drill (v2 active + bridge off, epoch/cohort pinned): 4/4 reused_exact, legacy_bridge_hits=0, shadow_diffs=0, policy_hash preserved (2d3d2ee8...) — cutover READY for the canary cohort.
- Zero-write: sqlite-enforced mode=ro + query_only; production legacy_periods.json / runtime_policy.json / catalog.sqlite3 untouched by this review (git status clean). Hash drift during live runs is the ambient background worker checkpointing WAL, not the observer.

## 5. Major finding — the close gate is unsatisfiable through the observer's own flow (F1)

`close_gate_allowed` can **never return True** on a ledger produced by `scripts/legacy_observer.py main()`:

- main() sets `ended_at` only on the PREVIOUS period when a new period is opened; the newest period always lacks `ended_at`.
- `close_gate_allowed` takes the last two periods INCLUDING the open one, and the open period always fails with "window not completed".
- Empirical proof with the real module: simulating the exact main() flow with all-zero-hit, >=24h windows for runs 1–5 yields `close_allowed=False` at every step ("need 2 completed observation windows" then "missing started_at/ended_at (window not completed)" forever). Evaluating the same ledger over the last two COMPLETED periods returns True after run 3 — so the windows ARE satisfiable; the evaluation is off-by-one (at run N+1 the completed pair is N-1 and N, but the gate evaluates [N, N+1]).
- The unit tests (leg10a–f) only exercise the pure function with hand-crafted fully-completed ledgers; no test covers the main() period-transition flow, so the defect is invisible to the suite.
- Impact: FC-705's core deliverable ("关闭条件" / close condition) can never authorize a bridge close; the Phase 7 exit gate criterion "可关" and the Phase 14 R8 wave entry condition ("两个>=24h zero-hit") are not achievable through the sanctioned mechanism.

Recovery: evaluate the last two COMPLETED periods (filter ended_at-set before taking the tail) or close the current window before evaluating; add a ledger-transition test. Re-review must rerun the affected suite.

## 6. Verdict

**changes_required** — the observation seam, zero-write guarantee, drill evidence, mutation kills, and live replays are all genuine and verified; but the close-gate wiring defect (F1) defeats the FC's central purpose and the receipt's base wiki hash (F2) is erroneous. Per protocol section 6: implementer must produce a new result triplet + receipt; the old reviewer receipt is superseded, not overwritten.
