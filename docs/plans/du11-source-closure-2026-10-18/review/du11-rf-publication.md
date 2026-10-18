# RF DU11 normal main publication and narrow skill sync

Status: **PUSHED; exact-head remote CI SUCCESS**. Initial in-progress observation was followed by the actual completed result, without predicting success beforehand.

## Mainline

- Preflight main and freshly fetched origin/main both `568fb9256885eb31a0f76d9ead59fd0f98575073`.
- Normal `git merge --ff-only d578da58b01b6cb9d3145ca88c0c292911398607` succeeded; accepted author's source/history preserved.
- Copied ROOT's exact 18-distinct-case reception record, first harness errors, publication/availability boundary, internal E2E restore receipt and outer Temp NOT_CLEAN into RF's independent `docs/plans/du11-root-reception-2026-10-18/` PWF.
- Normal documentation commit: `f8002f5fc8f56533c814f1616b7ecb68016f35e4`. Only that reception directory staged; no assurance WIP/output staged. Normal pre-commit temporarily isolated/restored unstaged files itself; no manual stash/reset or hook bypass.
- Normal `git push origin main` exited 0 in 80.537s. Gate Ruff PASS, 11 public-contract type files PASS, **416 passed + 36 subtests / 65.46s**, normal hook GREEN. Log/receipt: `du11-rf-normal-push.log/json`.
- `git ls-remote origin refs/heads/main` independently returned exact `f8002f5fc8f56533c814f1616b7ecb68016f35e4`. No force push or merge race.

## WIP preservation

The same three actual byte hashes were verified before merge, after commit, before push and after push:

| Existing file | SHA-256 |
|---|---|
| `assurance/runs/daily_alert.jsonl` | `8d4a7e41b2d4067e0dd82f504c582f245fe01ea5ff548f13f9c1f0fb8706791c` |
| `assurance/runs/weekly_alert.jsonl` | `0304c1de7d4ce35af30a349d322873b2dd625c26e50c309952dc00c1d835c70f` |
| `assurance/runs/weekly_manifest.json` | `c103bff9b985fb91f8df94b03ebad2d27d99e5a9b15d661b6b9c7b780b94bf3e` |

Existing untracked output remained untouched. No source-original/config/database/assurance contents were copied into the reception plan.

## Installed skill files

`.claude/skills/revenue-forecast` is a junction to `.agents/skills/revenue-forecast`; `.codex/skills/revenue-forecast` is the second physical root. Checked aliases, resolved roots and per-file resolved containment. Before any write both existing files in every alias matched **exact baseline blob bytes**, and the new module was absent. No unknown install frontier was overwritten.

Only these three runtime paths were updated, once per physical root, **six writes total**:

- `scripts/source_narrative_context.py`
- `scripts/research/input_evidence.py`
- `scripts/narrative_citation_context.py`

Every result was read back equal to accepted main bytes. No whole installer, directory replacement, config/output/other-file mutation. Complete old/new hashes and alias resolution: `du11-rf-install-sync.json`; preflight: `du11-rf-publication-preflight.json`.

## Remote CI / remaining scope

Anonymous GitHub API (no credentials) returned exact-head quality run [39092538354](https://github.com/zhengcb81/revenue-forecast/actions/runs/39092538354), initially `in_progress`, conclusion null. A later finite check observed **completed / success**, exact `f8002f5fc8f56533c814f1616b7ecb68016f35e4`, updated `2026-10-18T03:08:42Z`. Actual response fields are retained in `du11-rf-ci.json`. No credential extraction or speculative CI acceptance was used.

RF engineering integration and installation synchronization are complete. Real latest-CWP cross-page company quality and projected `/3` entry-2 publication/availability remain OPEN. The rejected reviewer Temp was not retried/deleted. Author worktree remains untouched; no force/skip/hook modification used. No paid/model calls or credential extraction.
