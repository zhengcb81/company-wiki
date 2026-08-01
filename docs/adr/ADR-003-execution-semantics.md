# ADR-003：至少一次执行 + 幂等效果

> 现行范围见 [ADR 适用范围说明](README.md)：语义继续适用于上游 source/parser/export effect，不再围绕投资 claim。

- 状态：accepted
- 日期：2026-07-10
- 背景：LLM/API、SQLite 与多文件写入之间不存在天然分布式事务。"Exactly once" 表述过度。
- 决策：采用**至少一次执行 + 幂等效果 + 可恢复提交日志**。以 `source_id + pipeline_version + claim_id` 去重。相同语义版本只产生一次有效 effect。
- 不采用的方案：分布式事务、exactly-once 语义
- 保护的不变量：提交守恒、证据守恒
- 影响范围：IngestService、WikiRepository、delivery outbox
- 迁移策略：新实现从一开始采用此语义
- 回滚/修订方式：新 ADR 修订
- 验证：重复运行零增量变化；中断后从正确 step 恢复
