# ADR-001：系统定位为增量知识编译器

> 现行范围已由 [ADR 适用范围说明](README.md) 收窄为 source records、EvidenceSpan、source/extraction quality 与来源投影。

- 状态：accepted
- 日期：2026-07-10
- 背景：系统最初设计为"批量生成 Markdown"的脚本集合，导致来源不可追溯、状态不可验证、知识不可重算。
- 决策：将系统重新定义为**增量知识编译器**。四层架构：
  1. **Raw + Source Manifest**：不可变原始证据，最终真源
  2. **Accepted Knowledge Ledger**（SQLite）：机器可重放的知识账本
  3. **Wiki/Index/Log**（Markdown）：用户可读、Git 可版本化的 materialized view
  4. **Runtime State**（SQLite）：队列、租约、成本、outbox 等可重建运行状态
- 不采用的方案：继续在 Scheduler/stage1-6/ingest_v2 之间逐点修补
- 保护的不变量：证据守恒、提交守恒、复现守恒
- 影响范围：所有数据流、存储和发布路径
- 迁移策略：从 `ingest_v2` 提取可用逻辑到 canonical core；旧脚本通过 adapter 调用
- 回滚/修订方式：新 ADR 修订，不改历史
- 验证：clean clone + 受管数据清单可重建同一系统状态
