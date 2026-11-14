# RFAUDIT-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\revenue-forecast-audit`。这是独立审查技能仓，不属于 RF 产品代码仓。

## 目标与边界

清理审查技能计划的入口/当前状态和8个已交付工区的历史负担；给下一个公司循环提供唯一可读的任务入口。不得改 revenue-forecast 的产品文件，不改技能源码或 `runs/`，不创建远端。

## 起始事实

- `main@fa0564fb` clean、无 remote、0 个 non-ancestor refs；owner需起步重核。
- 根循环计划为 `docs/plans/company-pool-cycle-2026-10-09/task_plan.md`，包含多段相互覆盖的旧“Next Step”；`skill-build-2026-10-08`已完成，W20-AUDIT已完成，`r4-owner-closure`为READY_NOT_STARTED，D4已完成。
- 18 个注册 worktree：17 clean，唯一未跟踪内容在 `_harness_worktrees/w08/audit-evidence/.planning/w08-audit-evidence/`，需先核 handoff/owner 并保留其唯一证据。
- Projects下 `revenue-forecast-audit` 主仓加 8 个交付目录，共 9 个候选。无 remote，不能声称或尝试推送。
- 9个候选目录：`revenue-forecast-audit`、`revenue-forecast-audit-du5-summary`、`revenue-forecast-audit-du6-import`、`revenue-forecast-audit-du67-integration`、`revenue-forecast-audit-du8-integration`、`revenue-forecast-audit-du8-measures`、`revenue-forecast-audit-w15-portable`、`revenue-forecast-audit-w17-coverage`、`revenue-forecast-audit-w20-checkpoints`。

## 执行步骤

1. 在根循环计划建立单一 `START_HERE.md` 或当前状态段，链接 `skill-build`、W09/W11/W13-W23、W20与R4 owner closure；历史计划只标状态并链接，不删除。
2. 把固定公司池循环的当前公司、已完成步骤、打开问题、唯一下一步归并一次；旧快照移到明确的历史小节，保留全部handoff和review evidence。
3. 对18 worktree、9 Projects目录逐项核 owner/branch/HEAD/dirty、PWF、handoff、唯一测试证据；先处理W08未跟踪目录去向，未经owner确认不得清理。
4. owner只清理已结案且clean、完整证据已归主仓的工区；报告释放空间。无 remote 只做本地提交并注明推送阻塞，不创建仓库或改变远端配置。
5. 在唯一入口写出接续公司循环的顺序、每轮报告与四路审查的交付接口、到何种条件暂停/重复；不自动扩大公司清单。

## 完成条件与审查

一个 canonical 状态入口能说明全部已完成与剩余步骤；18 worktree和9目录均有清晰处置；W08独有数据保留或有经验证的归档；skill源码、运行结果和用户数据不变。PWF-only执行链接/JSON/`git diff --check`；独立 reviewer 按最终 HEAD和交接复核、发现问题全部修正；owner本地提交并交 `handoff.md/json`，说明无remote。
