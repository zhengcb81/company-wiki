# 当前状态 — D5 全局解耦已验收；恢复 T4/SEM 主线

唯一入口：[当前状态](CURRENT_STATUS.md) / [机器状态](CURRENT_STATUS.json)；详细顺序见 [task_plan](task_plan.md)，交接见 [HANDOFF](HANDOFF.md)，固定长期目标见 [MAINLINE_LOOP_GOAL](MAINLINE_LOOP_GOAL.md)。

**截至 2026-11-06：D5 全局解耦 ACCEPTED，当前主线不再等待外包卡。** CWP 的 pathless 规范化文档 port 与 StockWiki 三个默认消费入口已进入各自主线；FF schema 2.0 走 V2/pathless，显式 V1 兼容仍保留并有独立边界测试。最终跨仓套件 18 passed、0 skipped、0 failed/errors，独立审查 PASS。完整证据：[ROOT D5 closeout](review/decoupling-recheck-20261104/root-d5-final/README.md)。

**当前唯一下一步：**恢复既有 T4 source-note-parent + SEM-QUAL-01，先写限定词与来源父链回归测试，再在所属责任层根修，并用一份隔离真实 H1 验收。完成后才恢复新版真实摘要、缓存恢复、RF 实际采用以及固定公司循环。D5 通过不代签这些产品任务。

## D5 接收结果

- 候选实现版本：CWP `a28692a6c49125143d2240b4a6d6df2ba29a28a1`；StockWiki `6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e`。两者均通过快进并入本地主线；StockWiki 当前无 Git remote，无法推送远端。
- run-6 固定跨仓套件：CWP 13 个处理 port 合同用例、StockWiki 三入口消费与真实样本 E2E 2 例、FF V2/V1 路由 3 例；合计 **18 passed**，无跳过、失败或错误。ROOT runner 定向单测 **15 passed**，Ruff 通过；合并后 CWP 合同测试再跑 **13 passed**。
- 真实只读原件：中大力德投资者关系记录 PDF，113,954 bytes，SHA-256 `ef78655e0980ce0ae50a5c9ab77457a024a9a5999ab4c0dff0556dc144efa4ef`，测试前后 SHA/大小/mtime 一致。隔离 scratch 已恢复。
- StockWiki transport 配置 `config/cwp_source_index.transport.json` 在测试期间 SHA 稳定，并以 Git clean-filter blob 比较确认内容与审查 HEAD 一致；Windows CRLF/LF 转换不误报，真实内容修改仍被回归测试拒绝。候选工作树运行前后均干净。
- 独立最终审查绑定上述准确 HEAD 与 `run-6/report.json`，结论 PASS。审查静态检查 runner 门与报告；runner scope 单测由 ROOT 独立运行 15 项通过。
- D5 没有新建第二套缓存；本次没有证明存在可复用的通用持久化 normalized-unit cache。跨请求/跨运行缓存恢复仍 OPEN，按主线顺序后续验收。

## 以前已关闭

- P0 CI 根因修复：已完成并发布；当前不因历史 CI 失败而重跑长时间全量套件。
- P0-D / D4-01～D4-06：按冻结范围完成，独立审查及强制组合通过。范围详情和历史收据保留在 [D4 closeout](review/d4-closeout-20261104/README.md)。D4 本身不等于 D5；现在 D5 也已经独立验收。

## 后续状态

| 阶段 | 状态 | 顺序与边界 |
|---|---|---|
| T4 + SEM-QUAL-01 | **NEXT / OPEN** | 来源父链与限定条件绑定根修，先 RED 测试，再一份真实隔离 H1 |
| 新版真实摘要与质量验收 | OPEN / 等 T4 | 用真实材料核查召回、归属限定、财务碎片/套话占位、业务信息遗漏 |
| 缓存恢复 | OPEN / 等新摘要基线 | 付费中断、同 run 与跨 run 恢复；按实际配置记账，不声称 D5 已验证 |
| RF 实际采用 | OPEN / 等新摘要和恢复 | 证明同一摘要 artifact 进入 RF 参数、公式与报告 |
| 固定公司审查循环 | OPEN / 最后 | 依长期目标完成固定名单与新公司泛化，不以局部工程测试替代完整审查 |

继续保留原始文件、历史失败和未跟踪 WIP；本轮只合并 D5 明确交付，不清理其它产物，不修改 Dayu/IQS。后续仍只在大节点做独审和组合测试，避免逐小节点增加审查。
