# FC-1201 Independent Reviewer Report

> Reviewer: `reviewer-fc1201-independent`
> Reviewed: 2026-08-12 (ISO 2026-08-12T20:55+08:00)
> Decision: **ACCEPTED**
> Replay: clean git worktree `C:/Users/郑曾波/Projects/.fcap-review/fc-1201` at wiki `88175217` (worktree removed post-review). RED-at-base used a separate `fc-1201-base` worktree (also removed).

## 1. Triplet

| repo | base | reviewed |
|---|---|---|
| revenue | `44cd28ab` | `44cd28ab` (unchanged) |
| filing  | `592fae61` | `592fae61` (unchanged) |
| wiki    | `f6eb5841` | `88175217` (feat `0c6c2c9` + receipt seal) |

## 2. Steps performed

### 2.1 Diff check (receipt vs reality)
`git diff f6eb584..0c6c2c9 --stat` = 7 files, EXACT match to receipt `changed_files`:
- `src/company_wiki/source_catalog/architecture_gate.py` (+18/-7) — allowlist shrink + frozen-ratchet/backlog comments
- `src/company_wiki/source_catalog/resolver.py` (5 lines) — comment token removal (zero behavior)
- `src/company_wiki/source_catalog/observability.py` (2 lines) — comment token removal
- `src/company_wiki/source_catalog/entity_resolver.py` (2 lines) — docstring token removal
- `tests/contract/test_fc1201_root_hardcode_gate.py` (+128, new) — 5 contract tests
- `assurance/fc/FC-1201/00_wu_card.md` (+60, new)
- `assurance/fc/FC-1201/03_change_contract.md` (+34, new)

Review HEAD vs feat (`0c6c2c9..8817521`) = 1 file: `11_implementer_receipt.json` (receipt seal only).

**NO** `scanner.py` / `config.py` / `canonical_writer.py` / `cli.py` / production yaml change. Confirmed.

### 2.2 Focused tests
- `test_fc1201_root_hardcode_gate.py` → **5 passed** (2.72s)
- `test_architecture_gate.py` + `test_future_root_config_only.py` → **12 passed** (1.11s)
- EX-08 (future-root config-only) stays green after allowlist shrink.

### 2.3 RED-at-base proof (CRITICAL)
Separate worktree at base `f6eb584`, new test file copied in. Result: **3 failed, 2 passed** (KILL CONFIRMED):
- `test_fc1201_allowlist_ratchet_frozen` FAIL — base allowlist had 19 files (incl resolver/observability/entity_resolver); `added=['entity_resolver.py','observability.py','resolver.py']`.
- `test_fc1201_comment_only_files_left_allowlist` FAIL — 3 files still in base allowlist.
- `test_fc1201_cleaned_files_are_token_free` FAIL — `resolver.py:679` still contains `company_raw` comment.
- The 2 passing tests (gate-green, detection) pass at base too — expected.

Tests have teeth; base genuinely had the 3 files in the allowlist and carried token comments.

### 2.4 Mutation replay
| id | mutation | predicted | result |
|---|---|---|---|
| M1 | re-add `resolver.py` to `_ROOT_HARDCODE_ALLOWED_FILES` | ratchet_frozen + comment_only_files_left FAIL | **KILL CONFIRMED** (2 failed, 3 passed) |
| M2 | remove `dayu_portfolio` from `_ROOT_HARDCODE_TOKENS` | gate_still_detects_new_hardcode FAIL | **KILL CONFIRMED** (1 failed, 4 passed) |

Both reverted cleanly; worktree `git diff` empty; focused suite 5/5 green post-revert.

### 2.5 Full wiki suite
`PYTHONIOENCODING=utf-8 python -B -m pytest tests/ -q`
→ **2241 passed, 1 skipped, 0 failed** in 433.58s (7m13s).

Zero new failures. Pre-existing PORT-01 (`test_check_unique_test_symbols`) passes under utf-8. No worker_bootstrap flake observed.

### 2.6 Gate integrity
- `resolver.py` / `observability.py` / `entity_resolver.py` → **NOT** in `_ROOT_HARDCODE_ALLOWED_FILES`.
- None of the 3 cleaned files contain any of the 4 tokens.
- `no_root_specific_hardcode()` → `ok=True, 0 violations`.
- Frozen backlog (8 files) verified to still carry tokens — allowlist is load-bearing, not vestigial.

### 2.7 Ruff
`ruff check` on 4 production modules + new test → All checks passed.

## 3. Findings

| id | sev | blocking? | issue |
|---|---|---|---|
| F1 | info | no | canonical_writer.py + cli.py deferred (loader-blocked / inherent identity). Honestly documented in WU card §1 + contract §2 as FC-1201 follow-up / R9 prep. Bounded by frozen allowlist + ratchet. |
| F2 | info | no | Gate uses raw substring match (no AST); comment-only mentions count as violations unless allowlisted. Pre-existing FC-304 design; v1 AST scanner is R9 backlog. Not a regression. |
| F3 | low | no | Test isolation relies on per-file `sys.path.insert`; company_wiki is also editable-installed pointing at the main checkout, so a test that skips the insert would silently test the main checkout. FC-1201 test does insert correctly; repo-wide convention. |

All findings are non-blocking (info/low). No medium+ issues found.

## 4. Honesty of deferral

The deferred canonical_writer/cli refactors are explicitly recorded in:
- WU card §1 (table rows for canonical_writer.py + cli.py marked **DEFERRED** with loader-blocked reasoning citing `config.py:75-84`).
- WU card §2 deliverable 6 (DEFERRED items contract).
- Change contract §2 invariants (canonical_writer/cli refactors DEFERRED).

The frozen allowlist + ratchet test make the backlog bounded and auditable — no silent drop. Verified the deferred files still genuinely carry tokens, so they cannot leave the allowlist without tripping the gate.

## 5. Verdict

**ACCEPTED.** Diff matches receipt, focused + full suites green with zero new failures, RED-at-base proven, both mutations killed, gate integrity holds, deferred work honestly documented. Worktrees cleaned up; main checkout git state untouched.
