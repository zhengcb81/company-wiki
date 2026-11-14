# CWP-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\company-wiki`。这是 ROOT 本仓责任。

## 目标

收敛 company-wiki 自己的 PWF 状态、未提交/未并线 refs 和多余 Projects 工区；保留模块边界。完成后明确 CWP 当前唯一下一步并链回父计划。不得操作 StockWiki、Dashboard、FF、RF、ET、SID 或 IQS 仓库。

## 起始事实

- `master@1f9f3dcf3`，远端已对齐；本仓 tracked 工作区干净。
- 已观测 8 个注册 worktree、13 个 `master` 非祖先 refs。
- Projects 顶层候选目录：`company-wiki`、`company-wiki-et-live-20261004`、`company-wiki-gates`、`company-wiki-r1-local-observation`、`company-wiki-storage-audit-20261003`。
- 当前唯一总控清理计划为 `docs/plans/module-pwf-reconciliation-2026-11-14/`；业务主线入口为 `docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md/json`，native goal 仍 paused。

## 独占范围

只写 CWP 仓自己的 `docs/plans/`、本仓源码/测试（确需适配 CWP 自身支线时）及本仓精确列出的工区。保留 `.ff_jobs`、`.mimosa`、`.workbuddy-ai`、API keys、原件、用户数据和历史 PWF 证据。不得用 `git clean -fdx`、整仓 reset、目录通配删除；不得重建或覆盖其他模块的内部实现。

## 步骤与验收

1. 对 13 个非祖先 refs、8 个 worktree 与四个额外 Projects 目录逐项关联 PWF、handoff、owner、HEAD、dirty paths、与 `master` 的独有路径/补丁；已在 CWP `master` 等价吸收的只记 `ABSORBED`。
2. `d00-return5` 与 `b34-prospectus` 的 dirty/owner 状态尚未完整归因，先标 `UNCLASSIFIED_HOLD`，不推断为活动或可删。两者物理目录位于 `Projects/investment-dashboard/.worktrees/`，本卡禁止删除、移动、checkout 或清理这两个物理目录；CWP owner 只记录其 CWP Git branch、HEAD 和 dirty 摘要，后续由 Dashboard owner 协调目录处置，或双方 owner 正式交接后再处理。CWP 仓内以 CWP 代码路径为准。
3. 仅在确认 owner 已完成、最终源码在 CWP 主线、无唯一证据且工区 clean 后，逐路径移除物理位于 CWP 所有目录内的 CWP 工区/目录。保留 `.planning` 历史、独有审查和原始材料，除非确认纯可重建产物并列出收据。
4. 更新当前总控 PWF：列明 CWP 自己已完成和未完成内容，并明确真正下一项 CWP 主线工作；父计划公司循环保持 paused，不提前执行。
5. 若本仓代码改变，运行关联单测和本仓边界 suite；若仅 PWF 更新，跑 `git diff --check`、校验新增/修改 JSON 和相对链接即可。
6. 独立 reviewer 按最终 HEAD 检查 13 refs、8 worktrees 与 5 顶层路径均有状态；清理路径无未解释 WIP；模块 owner 边界未破坏。问题修好后提交并推送 `master`。

## 交接

交付 `docs/plans/module-pwf-reconciliation-2026-11-14/review/cwp-closeout-handoff.md/json`，包含每个 ref/worktree/目录的唯一处置、diff/dirty 摘要、测试、独审 SHA、释放的文件数/字节、最终本地/远端 SHA、CWP 下一步及尚待其他模块 owner 的公开接口依赖。
