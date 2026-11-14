# DASHBOARD-D00-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\investment-dashboard`；产品和 Git 收尾均由 Dashboard D00 owner 执行。

## 目标与边界

对齐 Dashboard D00 总状态、各模块 PWF、CWP 后续卡基线、未并线支线和 Projects 工区；写清 Dashboard 仍未完成的产品路线。不得改 CWP/FF/RF/StockWiki/IQS 代码；不得将旧集中式实现合并回 modular main。

## 起始事实

- 主线 `main@50602dee7c6fbecaa744004a4184bdc6bc7b2765` = `origin/main`；tracked clean，`.workbuddy-ai/` 保留。
- D00 canonical入口为 `.planning/unified-dashboard-2026-10-26/START_HERE.md`；当前有 80 个注册 worktree、92 个 local branch refs。
- `START_HERE.md`、`DELIVERY_STATUS.md`、`COMPLETION_PLAN.md` 的状态快照为 11-04；CWP 三张 Dashboard 卡基线还写 `ff6e764f`，需先对齐 `50602dee` 并核实际代码状态。
- Dashboard仍 `PARTIALLY_IMPLEMENTED_NOT_COMPLETE`；真实 owner chain、E08、指标/三表映射、job executor、性能和用户验收仍有缺口；E14 为暂停项。
- Projects顶层目录候选：`investment-dashboard`、`investment-dashboard-e15`、`investment-dashboard-owner-adapters-20261109`；另有注册工区可能位于 `.worktrees`、`.codex/worktrees` 或其他 Projects 路径。

## 执行步骤

1. D00更新唯一主状态入口的 as-of、HEAD、完成/未完成、暂停项和下一步；模块 M0–M9 子PWF各自仍是子计划，不复制一份第二总状态。
2. 逐张核 CWP C01、B-real、B03 卡在当前 main 的实际状态、测试/独审与依赖；刷新基线和剩余工作，保留其 owner-only 写域。此前三份文档交接提交只作为历史，不据此认定卡已完成。
3. 对 92 refs、80 worktree 和其他两个 Projects候选逐项建立 disposition：branch/HEAD、独有提交/路径、dirty文件、PWF/handoff、运行配置引用、归属和保留/删除理由。不能因名字像旧任务就删除；dirty worktree先交当前 owner。
4. 由 Dashboard owner 在其 repo 内适配可用分支、跑模块回归并逐个 merge/push；任何 CWP/FF/RF接口变化各自给对应 owner 开明示 handoff，不跨仓实现。
5. 只删除已经验明无活动WIP、无唯一产物且已进入main/有完整收据的Dashboard工区；保留 `.workbuddy-ai/` 与所有用户/研究/业务数据。
6. 更新 Dashboard 剩余主线路线和最终用户验收点，使其可以独立交给后续 harness。

## 完成条件与审查

D00可从START_HERE定位唯一现状、每个模块子计划和下一步；旧11-04描述已标历史或更新；3张CWP卡基线对齐；92 refs、80 worktree、所有 Projects候选均有处理状态。代码改动运行相关Dashboard回归；PWF-only做链接/JSON/`git diff --check`。由独立 reviewer 按最终 main HEAD审查并要求修复所有发现，再由D00 owner提交/推送和提交 `handoff.md/json`。
