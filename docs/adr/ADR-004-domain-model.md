# ADR-004：统一领域模型

> 现行范围见 [ADR 适用范围说明](README.md)：SourceRecord/EvidenceSpan 保留，投资研究 Question/Claim/KnowledgePatch 移交 StockWiki。

- 状态：accepted
- 日期：2026-07-10
- 背景：当前知识以 Markdown 正则解析，没有稳定的实体 ID、来源谱系或问题状态。
- 决策：定义统一领域模型：
  - **Company/Sector/Theme**：三类一等实体，均有稳定 ID
  - **Topic**：实体下的主题（如"公司动态"、"催化剂日历"）
  - **Question**：有 owner、priority、status、answer_state、expiry
  - **SourceRecord**：不可变来源，SHA-256 身份
  - **EvidenceSpan**：来源中的证据片段
  - **Claim/Event**：事实/观点/预测，四类时间，corrects/supersedes 关系
  - **KnowledgePatch**：来源→知识的结构化提案
- 不采用的方案：继续用 Markdown 正则和裸字符串标识
- 保护的不变量：语义守恒、传播守恒
- 影响范围：所有数据模型、存储、投影
- 迁移策略：新表/字段先由 adapter 只读验证，再成为 canonical
- 回滚/修订方式：schema migration + PRAGMA user_version
- 验证：配置 round-trip、ID 稳定性、旧 DB 幂等迁移
