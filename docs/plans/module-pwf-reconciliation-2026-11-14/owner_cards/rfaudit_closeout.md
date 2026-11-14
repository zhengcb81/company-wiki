# RFAUDIT-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\revenue-forecast-audit`。这是独立审查技能仓，不属于 RF 产品代码仓。

**PWF 读取入口与交付落点：**读取 `docs/plans/company-pool-cycle-2026-10-09/task_plan.md`、同目录 `progress.md`/`findings.md`，以及 `docs/plans/r4-owner-closure-20261102/`、`docs/plans/w20-audit-checkpoints-2026-10-28/` 的最终 handoff。最终交接固定写入 `docs/plans/module-pwf-reconciliation-2026-11-14/review/rfaudit-closeout-handoff.md` 和 `rfaudit-closeout-handoff.json`；独立审查报告写 `rfaudit-closeout-review.md`（目录不存在时创建）；本仓无 remote，不推送。

## 目标与边界

清理审查技能计划的入口/当前状态和8个已交付工区的历史负担；给下一个公司循环提供唯一可读的任务入口。不得改 revenue-forecast 的产品文件，不改技能源码或 `runs/`，不创建远端。

## 独立执行与交接约定

- 开工先读本仓 `AGENTS.md`（若存在）、上方列出的 PWF 入口和此卡；再用实时 Git 状态重核 branch、HEAD/remote、tracked/untracked、registered worktree 与 refs。本卡中的日期/HEAD/count 是调查快照，不是授权或删除依据；新状态不同则先更新快照，基于实时确认的本仓目标主线继续，不回滚新工作，也不假设主线名一定是 `main`。
- 只在本卡唯一写入仓做文件和 Git 修改。看到其他仓路径/分支时只记录归属，不能在那里 checkout、stage、restore、commit、merge、push、删除或移动。若本仓有在途改动与本卡写集合重叠，标 `UNCLASSIFIED_HOLD` 并交当前 owner 协调，不覆盖。
- 删除/吸收决定逐项写依据；名字像临时目录、dirty/untracked、branch 非祖先都不能单独证明可删/该并。没查清 owner/PWF/内容/配置引用时保持 `UNCLASSIFIED_HOLD`。
- disposition 统一用 `ACTIVE_KEEP`（仍在用/有后续任务）、`EVIDENCE_KEEP`（唯一审查、运行或用户资料）、`ABSORBED`（已由目标主线等价吸收，附 commit 和等价证据）、`UNCLASSIFIED_HOLD`（归属/用途/内容未查清，原样保留）、`DELETE_AFTER_OWNER_CONFIRMATION`（本卡指定模块 owner 已依据收据确认结案，且无唯一内容、dirty 工作或配置引用；这是该 owner 的分类结论，不要求 ROOT 再签一次。若实际属于其他 owner，则保留并标 `UNCLASSIFIED_HOLD`）。
- 在上方指定的固定位置交 `handoff.md` 与 `handoff.json`，不要写到其他仓或覆盖历史 handoff。至少包含：仓库路径、canonical PWF、base/final branch+HEAD、remote HEAD（或明确无 remote）、每个 branch/worktree/Projects候选的 disposition 和依据、未提交例外、精确清理路径/文件数/字节、测试命令及结果、独立 reviewer 结论与绑定 HEAD、剩余项及唯一下一步。
- `handoff.json` 必须是可解析的裸 JSON（不带 Markdown 围栏），`schema_version` 固定为 `1`，顶层键固定为 `schema_version`、`lane`、`repo_root`、`canonical_pwf`、`base`、`final`、`dispositions`、`dirty_exceptions`、`cleanup`、`tests`、`independent_review`、`remaining_items`、`next_step`；`base/final` 含 `branch/head/remote_head`（无 remote 时 `remote_head: null`），`dispositions` 每项含 `kind/path/status/reason/evidence`，`cleanup` 含 `paths/file_count/bytes`，`tests` 每项含 `command/result`，`independent_review` 含 `reviewer_agent/reviewed_head/result/report_path`。独立 review Markdown 记录审查范围、绑定 HEAD、发现及关闭状态、最终 PASS/FAIL。
- 最终大节点由未参与实施的另一名 agent/harness 审查完整变更和交接，结论绑定已提交的最终 HEAD。若发现问题，作者修复、复测并提交新 HEAD，再由 reviewer 复核该 HEAD；通过后才交接。只设这一个审查节点，必要修复后的复核除外。代码变更跑本卡指定回归；文档-only按 JSON/link/`git diff --check`检查。

## 起始事实

- `main@fa0564fb` clean、无 remote、0 个 non-ancestor refs；owner需起步重核。
- 根循环计划为 `docs/plans/company-pool-cycle-2026-10-09/task_plan.md`，包含多段相互覆盖的旧“Next Step”；`skill-build-2026-10-08`已完成，W20-AUDIT已完成，`r4-owner-closure`为READY_NOT_STARTED，D4已完成。
- 18 个注册 worktree：17 clean，唯一未跟踪内容在 `_harness_worktrees/w08/audit-evidence/.planning/w08-audit-evidence/`，需先核 handoff/owner 并保留其唯一证据。
- Projects下 `revenue-forecast-audit` 主仓加 8 个交付目录，共 9 个候选。无 remote，不能声称或尝试推送。
- 9个候选目录：`revenue-forecast-audit`、`revenue-forecast-audit-du5-summary`、`revenue-forecast-audit-du6-import`、`revenue-forecast-audit-du67-integration`、`revenue-forecast-audit-du8-integration`、`revenue-forecast-audit-du8-measures`、`revenue-forecast-audit-w15-portable`、`revenue-forecast-audit-w17-coverage`、`revenue-forecast-audit-w20-checkpoints`。

## 执行步骤

1. 将 `docs/plans/company-pool-cycle-2026-10-09/task_plan.md` 固定为唯一 canonical 状态入口，在顶部增加当前状态/唯一下一步，并链接 `skill-build`、W09/W11/W13-W23、W20 与 R4 owner closure；同目录 `progress.md`/`findings.md` 和其它历史计划只保留证据、标明状态并链接回该入口，不另建 `START_HERE` 或第二状态入口。
2. 把固定公司池循环的当前公司、已完成步骤、打开问题、唯一下一步归并一次；旧快照移到明确的历史小节，保留全部handoff和review evidence。
3. 对18 worktree、9 Projects目录逐项核 owner/branch/HEAD/dirty、PWF、handoff、唯一测试证据；先处理W08未跟踪目录去向，未经owner确认不得清理。
4. owner只清理已结案且clean、完整证据已归主仓的工区；报告释放空间。无 remote 只做本地提交并注明推送阻塞，不创建仓库或改变远端配置。
5. 在唯一入口写出接续公司循环的顺序、每轮报告与四路审查的交付接口、到何种条件暂停/重复；不自动扩大公司清单。

## 完成条件与审查

一个 canonical 状态入口能说明全部已完成与剩余步骤；18 worktree和9目录均有清晰处置；W08独有数据保留或有经验证的归档；skill源码、运行结果和用户数据不变。PWF-only执行链接/JSON/`git diff --check`；owner本地提交候选版本后，由独立 reviewer 按该 HEAD和交接复核、发现问题全部修正并复核新 HEAD；通过后交 handoff，说明无remote。
