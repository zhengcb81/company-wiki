# ADR-002：新建 Canonical IngestService

> 现行范围见 [ADR 适用范围说明](README.md)：唯一摄取入口继续，但 canonical 输出改为 manifest/span/index/export。

- 状态：accepted
- 日期：2026-07-10
- 背景：当前存在 `ingest_v2.py`、`full_pipeline.py`、`stage1-6`、`batch_process.py`、`batch_ingest.py` 等多个入口，互相竞争写入 wiki。
- 决策：新建 `src/company_wiki/ingest.py` 作为唯一规范摄取服务。`ingest_v2` 仅为迁移来源和兼容 CLI；`full_pipeline`/`stage1-6`/`batch_process`/`batch_ingest` 冻结并最终退役。
- 不采用的方案：保留多个入口并行运行
- 保护的不变量：提交守恒、控制守恒
- 影响范围：所有摄取入口、Scheduler、CLI
- 迁移策略：影子模式证明正确后，逐步替换旧入口
- 回滚/修订方式：旧入口保留为只读 adapter，不删除
- 验证：CodeGraph impact 确认生产调用已迁移
