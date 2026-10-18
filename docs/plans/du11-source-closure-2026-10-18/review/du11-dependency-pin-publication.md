# DU11 published dependency triplet — two-stage ROOT receipt

Status: FINAL_TRIPLET_PUSHED_CI_SUCCESS. Final RF remote `main` exactly equals `9669c4d79cff7bf3e023dbd6cb74c411f4bef7bf` after a successful normal push. Only `compatibility/current.json` and `docs/plans/du11-dependency-pin-2026-10-18/release.md` entered either release commit. No RF runtime, checkout tools, public versions, registry hashes, frozen baselines, user configuration or installed compatibility files changed.

## Final implementation triplet

| Owner | Published implementation pin |
|---|---|
| CWP | `0ccdc6896ee58063ff827e9ceab16043c7550e0c` |
| RF | `f8002f5fc8f56533c814f1616b7ecb68016f35e4` |
| FF | `e8740748f91999cb24169b42f8e789726ed50482` |

Each producer was confirmed published before pinning. RF pins its implementation base, while CI skips its own sibling and tests checkout HEAD. No floating branch, unpublished commit or recursive documentation HEAD is pinned. ROOT reports exact CWP CI39094787278 and FF CI39095654355 success. These are engineering release facts, not real semantic/content C sign-off.

## Stage 1 — CWP/RF update, preserve then-published FF

Normal commit/push `e73646395c3b0aea0bca054ffdcc46b2f1e66c45`, remote verified exactly. Existing focused checks 28 PASS/9.09s; owned Temp restored. Normal gate: Ruff PASS, types11 PASS, 416 PASS+36subtests/70.53s; push exit0/83.56s. Exact RF quality [39094965965](https://github.com/zhengcb81/revenue-forecast/actions/runs/39094965965) completed/success, independently checked anonymously. Stage 1 deliberately retained FF5001 until FF's new producer was published. All original receipts remain in adjacent `du11-dependency-pin-before/tests/push/ci.*`; full historical report data remains nested in JSON.

## Stage 2 — final FF update

After ROOT confirmed remote FF `e8740748f91999cb24169b42f8e789726ed50482`, only filing pin, note and update date changed in the manifest, plus the same release record. Normal commit/push `9669c4d79cff7bf3e023dbd6cb74c411f4bef7bf`; `git ls-remote origin refs/heads/main` exactly matched. Focused checks 28 PASS/9.23s; owned Temp restored. Normal gate: Ruff PASS, types11 PASS, 416 PASS+36subtests/73.74s; push exit0/84.594s. No force, manual stash/reset or hook bypass. Exact final quality [39095818018](https://github.com/zhengcb81/revenue-forecast/actions/runs/39095818018) completed/success, independently checked anonymously for the full final commit. Stage-2 commands/logs/XML/cleanup remain in adjacent `du11-dependency-pin-stage2-*`.

## Unrelated state and remaining boundary

Three existing assurance WIP paths were excluded from staging. Stage 1 observed weekly_manifest change from `c41959e3cd5925c87c00164c089671e62ba193cf21c5f5de4b152515ba45a239` to `49803e12057c3fd284797a67678ce47a0829db40dbcebafc92af7c9d53d22324`; this task did not write/restore it and does not attribute its writer. Stage-2 beginning and final observations of all three files match exactly; daily alert remains `8d4a7e41b2d4067e0dd82f504c582f245fe01ea5ff548f13f9c1f0fb8706791c`, weekly alert `a05699bf906b1cf3e78eda8cf98c4c1b3105e7f9ddf418aac39640d9fa11e7c2`, weekly manifest the observed49803e12 value. Output was not read, staged or modified. Normal pre-commit isolation/restoration is recorded without a manual stash.

The agents/claude-junction/codex installed roots lack compatibility/current.json; installable skill closure excludes this repository-only control plane, so none is added/synced. No new approval/cache/identity or installation subsystem was introduced. Final exact RF CI is successful and this pin task is complete; do not initiate another documentation-only producer/pin cycle. General source antecedent/semantic quality and formal content C remain ROOT's separate PWF work.

Method note: first stage report assembly briefly failed on platform-default GBK decoding of an existing UTF-8 receipt, corrected with explicit UTF-8 before writes; no behavior test or release repeated for that tool-only error.
