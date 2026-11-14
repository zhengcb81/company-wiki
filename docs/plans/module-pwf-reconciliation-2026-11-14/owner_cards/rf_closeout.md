# RF-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\revenue-forecast`；由 RF owner 完成本仓计划、代码和 Git 操作。

## 目标与边界

统一 RF 的活动 PWF 入口、合并历史状态冲突、对账分支/worktree 和 Projects 顶层路径；完成后更新 RF 主线次序。不得改 CWP、Dashboard、StockWiki 或其他仓；不重跑公司预测来证明文档状态。

## 起始事实

- `main@ec5ba0044b3252d2fc58c4a50c2fe9bc234cf5ad` = `origin/main`；ROOT 已提权读到 tracked clean。先重新核一次真实状态。
- 61 个注册 worktree、19 个本地非祖先 refs。`dashboard-rf-*` 分支虽然名字含 Dashboard，仍由 RF owner 在 RF 仓内处理；涉及 Dashboard 合同的差异交给双方协调，不跨仓改 Dashboard。
- MB-RF `task_plan.md` 与 `handoff.md` 同时写“未合入/已合入”；W20状态待对照实际收据。先前所报 `revenue_report.py`、`test_output_report.py`、`input-schema.md` dirty 已被 `ec5ba004` 吸收，不得重复报告为未提交。
- Projects的14个 RF core 候选目录：`revenue-forecast`、`revenue-forecast-dashboard-owner-release-20261109`、`revenue-forecast-du11-citation-closure`、`revenue-forecast-du5-units`、`revenue-forecast-du6-targets`、`revenue-forecast-du67-integration`、`revenue-forecast-du8-comparison`、`revenue-forecast-r1-boundary`、`revenue-forecast-r1-local-observation`、`revenue-forecast-r1-research`、`revenue-forecast-r1-targets`、`revenue-forecast-w14-clean-chain`、`revenue-forecast-w16-basis`、`revenue-forecast-w20-adoption`。9个 `revenue-forecast-audit*` 路径属于独立 RFAudit，不归本卡清理。

## 执行步骤

1. RF owner 选定唯一 canonical status/START_HERE，指向当前 `main@HEAD`、活动计划、关闭收据、依赖和下一步；MB-RF、W20 等冲突按提交和 handoff 的绑定 ref 对齐，历史计划保留并加状态链接。
2. 对 19 refs、61 worktree 和 RF 专属顶层目录建逐项账目：归属、branch/HEAD、dirty/untracked、提交差异、PWF/handoff、配置或测试引用、最终分类。
3. 按当前 RF 公开模块接口，owner 本仓适配可用分支；不按 `not merged` 机械合并，不覆盖当前 main、不重新跑预测、不把历史执行输出当代码。代码并线由 RF owner 完成。
4. 只删除经确认结案且无唯一源代码、测试证据、用户资料、运行状态或配置引用的 RF-owned 工区；逐路径记录空间收据。RFAudit 目录全部留给其独立 owner。
5. 更新 RF 未来主线计划，把本仓未完成的模型/报告/来源职责按依赖排序；依赖其他 owner 的事项写成公开接口等待项，不由 RF 跨界修复。

## 完成条件与审查

MB-RF 与 W20 状态无冲突；19 refs、61 worktree、RF core 顶层路径全部有 owner 处置；保留/清理证据可追踪；当前 main/remote HEAD明确。若改代码，运行受影响回归和一次相关 RF 大套件；纯文档改动做 PWF/JSON/link/`git diff --check`。独立 reviewer 绑定最终 HEAD；修复所有问题后由 RF owner commit/push，并交 `handoff.md/json`。
