# 当前交接 — D5 已接收；ROOT 恢复 T4/SEM

**唯一入口**：先读 [CURRENT_STATUS.md](CURRENT_STATUS.md) 和 [CURRENT_STATUS.json](CURRENT_STATUS.json)，再按 [task_plan.md](task_plan.md) 执行。长期目标只看 [MAINLINE_LOOP_GOAL.md](MAINLINE_LOOP_GOAL.md)。截至 2026-11-06，D5 已验收并入主线；不要重新派发 D5 卡或把旧 handoff 中的 OPEN/PENDING 当现状。

## 已验收的 D5

- CWP producer port：`a28692a6c49125143d2240b4a6d6df2ba29a28a1`；StockWiki consumers：`6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e`。两个候选版本均通过快进进入各自主线。
- CWP/StockWiki/FF 固定组合套件 `run-6`：18 passed，0 skipped/failed/errors；包含 13 个 CWP contract 用例、StockWiki 三入口和真实样本 E2E、FF V2/V1 路由边界。
- 真实 PDF SHA/大小/mtime 稳定；隔离 scratch 已清理；候选 worktree 运行前后干净；StockWiki transport 内容匹配被审查 commit（按 Git clean-filter blob 比较，正确处理 Windows CRLF/LF）。
- ROOT runner 范围单测 15 passed，Ruff 通过；主线 CWP 合并后 contract suite 13 passed。最终独立审查 PASS。
- 证据入口：[ROOT D5 closeout](review/decoupling-recheck-20261104/root-d5-final/README.md)；机器测试收据 [run-6/report.json](review/decoupling-recheck-20261104/root-d5-final/run-6/report.json)。
- StockWiki 仓库没有 Git remote，记录为本地并线；不得把本地并线说成已推送。CWP push/精确 CI 状态以 closeout 的发布字段为准，没核实就不要填绿。

## 当前 ROOT 唯一下一步：T4 source-note-parent + SEM-QUAL-01

1. 先重读 task_plan 中 T4/SEM 原问题和 `findings.md` 里的源头证据，不再重新调查已接受的 D5。
2. 在真实改动前先写最小 RED 回归，覆盖来源父链丢失及计划/条件句被改写成已发生事实的根因；避免把两个问题用关键词补丁混成单一规则。
3. 在拥有该字段/语义的责任层实施通用修复，保留 issuer、期间、as-of、否定、计划条件限定和 locator；不增加公司名特判、材料许可门或重复 SHA 检验。
4. 跑所属模块聚焦单测/集成测试，再对一份隔离真实 H1 跑端到端；验证原件 SHA 不变、测试目录恢复。仅在该大节点请求一次独立审查。
5. 通过后提交、按仓库 remote 状态推送并更新 CURRENT_STATUS、task_plan、findings、progress、handoff。此节点不并入新版摘要、缓存恢复或 RF 采用工作。

## 接下来仍未完成的工作

T4/SEM 通过后，按 task_plan 顺序实施新版真实摘要与内容召回验收；随后做付费中断/同 run/跨 run 缓存恢复，再验证 Revenue Forecast 实际消费同一份摘要 artifact，最后恢复固定公司审查循环。各阶段分别记录真实范围、预算、证据、测试恢复和独立大节点审查。D5 组合测试不等价于这些产品验收。

## 明确未声称的能力

D5 没有建立第二套缓存，也没有证明存在可复用的通用 CWP normalized-unit 持久缓存；当前 port 按请求读取/解析。缓存恢复仍是后续独立任务。D5 测试使用一份真实本地材料，但不代表市场/文种读取策略或八家公司循环已验收。

## 边界

只修改职责 owner 的范围；保留公司原始文档与所有无关未跟踪历史产物。StockWiki 继续拥有投资语义，CWP 只负责来源和通用解析，FF 的 V1 继续显式隔离兼容。不要修改 Dayu/IQS 或其它仍在施工的外部项目。
