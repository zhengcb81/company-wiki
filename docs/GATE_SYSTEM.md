# 旧 Gate 流水线已退休

G4 已删除旧 `scripts/gate_system/`、`config/pipeline_rules.yaml` 和专属框架测试。`scripts/full_pipeline.py` 只保留退休说明：直接运行、帮助或旧参数均返回 78；导入不会初始化配置、模型、网络或处理目录。没有恢复旧流水线的授权或审核步骤。

当前来源入口是 `company-wiki-source-catalog`、`company-wiki-source-read`、`company-wiki-source-query` 和 `company-wiki-source-export-v2`。文档登记、解析、证据定位和有限叙述处理按当前配置执行；来源 SHA、身份、期间、定位和实际资源上限属于相应层的责任。

- [来源目录与当前命令](source-catalog.md)
- [运维说明](OPERATIONS.md)
- [当前总计划](plans/narrative-evidence-pilot-2026-09-26/task_plan.md)

投资研究状态和估值属于 StockWiki。当前 PDF classify/extract/validate 责任测试仍保留，不依赖旧 Gate 框架。

旧操作手册保留在 [Git 历史](https://github.com/zhengcb81/company-wiki/blob/7fb29b94e8fd5c4584963b846714bafdc1f63baf/docs/GATE_SYSTEM.md)，不作为当前施工或运行指令。
