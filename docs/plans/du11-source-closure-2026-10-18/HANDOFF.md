# 当前交接 — D4/D5 已接收；ROOT 收口 T4/SEM

**唯一入口**：先读 [CURRENT_STATUS.md](CURRENT_STATUS.md) 和 [CURRENT_STATUS.json](CURRENT_STATUS.json)，再按 [task_plan.md](task_plan.md) 执行。长期目标只看 [MAINLINE_LOOP_GOAL.md](MAINLINE_LOOP_GOAL.md)。截至 2026-11-06，D5 已验收并入主线；不要重新派发 D5 卡或把旧 handoff 中的 OPEN/PENDING 当现状。

## 已验收的 D5

- CWP producer port：`a28692a6c49125143d2240b4a6d6df2ba29a28a1`；StockWiki consumers：`6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e`。两个候选版本均通过快进进入各自主线。
- CWP/StockWiki/FF 固定组合套件 `run-6`：18 passed，0 skipped/failed/errors；包含 13 个 CWP contract 用例、StockWiki 三入口和真实样本 E2E、FF V2/V1 路由边界。
- 真实 PDF SHA/大小/mtime 稳定；隔离 scratch 已清理；候选 worktree 运行前后干净；StockWiki transport 内容匹配被审查 commit（按 Git clean-filter blob 比较，正确处理 Windows CRLF/LF）。
- ROOT runner 范围单测 15 passed，Ruff 通过；主线 CWP 合并后 contract suite 13 passed。最终独立审查 PASS。
- 证据入口：[ROOT D5 closeout](review/decoupling-recheck-20261104/root-d5-final/README.md)；机器测试收据 [run-6/report.json](review/decoupling-recheck-20261104/root-d5-final/run-6/report.json)。
- StockWiki 仓库没有 Git remote，记录为本地并线；不得把本地并线说成已推送。CWP push/精确 CI 状态以 closeout 的发布字段为准，没核实就不要填绿。
- CWP ROOT 接收 commit `c28b122075748d99547fb0a7e2fd4adcd7490269` 与本机 `origin/master` tracking ref 相同；本次未能直接查询实时远端或该 head 的 exact CI。`e7469d68` 的已知 CI 只绑定 D4 head，不能冒作 c28 的 CI。

## 当前 ROOT 唯一下一步：完成 T4/SEM 大节点收口

1. 现有本地实现覆盖 note 父链重置与中英文跨 span 条件限定词绑定；RED→GREEN 与聚焦测试结果记于 `progress.md`，当前变更尚未提交。
2. 审阅 `.planning/t4-sem-h1-20261106-attempt2/h1.json`：12/12 必需原文单元精确覆盖，112 spans、102 native members；解释与旧基线 101 的成员数差异，并核对 12 个 locator 和 9 个结构/context 观察。不得把 `OBSERVED_NOT_COMPANY_OR_ECONOMIC_ACCEPTANCE` 写成业务验收通过。
3. 由独立审查者对当前源码差异、回归用例和真实 H1 证据做一次大节点审查；先修复发现的问题再收口。最终 Ruff 状态尚未确认。
4. 将审查报告、摘要收据和测试清理结果写入 `review/T4-SEM-closeout-20261106/`；确认原件未变并只清理由本次建立的测试 scratch，恢复其初始不存在状态。
5. 通过后再提交、推送并更新 CURRENT_STATUS、task_plan、findings、progress、handoff。此节点不并入新版摘要、缓存恢复或 RF 采用工作。

## 接下来仍未完成的工作

T4/SEM 通过后，按 task_plan 顺序实施新版真实摘要与内容召回验收；随后做付费中断/同 run/跨 run 缓存恢复，再验证 Revenue Forecast 实际消费同一份摘要 artifact，最后恢复固定公司审查循环。各阶段分别记录真实范围、预算、证据、测试恢复和独立大节点审查。D5 组合测试不等价于这些产品验收。

## 明确未声称的能力

D5 没有建立第二套缓存，也没有证明存在可复用的通用 CWP normalized-unit 持久缓存；当前 port 按请求读取/解析。缓存恢复仍是后续独立任务。D5 测试使用一份真实本地材料，但不代表市场/文种读取策略或八家公司循环已验收。

## 边界

只修改职责 owner 的范围；保留公司原始文档与所有无关未跟踪历史产物。StockWiki 继续拥有投资语义，CWP 只负责来源和通用解析，FF 的 V1 继续显式隔离兼容。不要修改 Dayu/IQS 或其它仍在施工的外部项目。
