# Legacy 归档计划 — 非活动执行入口

> 2026-09-06同步：原始痛点当前审计与后续步骤见[新审计目录](../plans/painpoint-outcome-audit-2026-09-05/README.md)。本目录16份原文继续只作历史输入，研究型writer和未经重构的并发LLM仍禁止，不因新计划重新启用。

状态核对：2026-09-04。此目录保留早期Wiki架构、审查、计划与当时测试结果，不把旧勾选或pending改写成今天的验收。

本次已全文阅读规划及其完成说明：`PLAN.md`、`REFACTORING_PLAN.md`、`IMPROVEMENT_PLAN.md`、`IMPLEMENTATION_STEPS.md`、`GAP_FIX_PLAN.md`、`KARPATHY_GAPS_PLAN.md`、`LLM_INTEGRATION_PLAN.md`、`CODE_REVIEW.md`、`PHASE1_COMPLETE.md`、`PHASE2_COMPLETE.md`。

重要处置：

- 原Wiki自我进化、投资综合评估、Query答案回写研究页面等目标已被2026-07-16职责边界取代，不应为“补全旧计划”恢复这些writer。
- `REFACTORING_PLAN`/`PHASE2_COMPLETE`中的scripts/models主实现说法不是现行架构；[AGENTS](../../AGENTS.md)明确scripts/graph.py为规范实现，scripts/models为弃用类型化版本。
- 旧异步/并行LLM、2x/3x性能目标与无需值守的成功标准不是当前已证事实；LLMClient非线程安全，未重构前不能并发化。
- 旧固定路径、自动调度和下载/迁移/回填命令仅供历史追溯；本轮不执行。测试次数、公司数量、覆盖率与时限均保留原日期，未进行本次重验。
- `KARPATHY_GAPS_PLAN`的pending与其他旧完成报告冲突，按历史方案迭代解释，不生成重复队列。当前范围入口是 [PLANNING_STATUS](../../PLANNING_STATUS.md)。

另已全文阅读其余6份关联归档：`BUGFIX_REPORT.md`、`HARDCODE_FIXES.md`、`TESTING.md`、`source_suggestions.md`、`KARPATHY_COMPARISON.md`、`KARPATHY_COMPARISON_V2.md`。这些是历史调查/测试说明/方案输入，并非活动三件套；其旧模型比较评分、脚本建议或跨仓配置修改步骤未作当日技术重验，不据其自动实施。本目录原有16份Markdown阅读覆盖完成，历史原文字节保留。
