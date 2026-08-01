# ADR 适用范围说明

> 2026-07-16 起，company-wiki 定位为 StockWiki 的上游来源系统。本说明是 ADR-001～ADR-006 的现行 scope note；旧 ADR 原文保留为历史决策证据，但不得被解释为继续建设第二套投资研究系统。

## 现行边界

company-wiki 的 canonical 对象仅限 immutable raw、source manifest/SourceRecord、EvidenceSpan、source/extraction quality、全文索引、解析诊断和 source-oriented projection。跨仓集成使用版本化只读 export；company-wiki 不写 StockWiki。

投资命题 review、accepted/rejected 投资结论、Question/Claim 研究状态、估值/SOTP、研究 Wiki 和正式报告属于 StockWiki。ADR 文件中的 `状态：accepted` 只表示该 ADR 曾被接受；上游数据中的 accepted 也只能表示 source/extraction quality，不表示 accepted investment conclusion。

## 既有 ADR 的收敛关系

| ADR | 现行处理 | 2026-07-16 后的解释 |
|---|---|---|
| ADR-001 | 收窄 | 增量编译器只编译 source records、evidence spans、解析质量与来源投影；不维护研究 knowledge ledger。 |
| ADR-002 | 继续 | Canonical IngestService 仍是唯一摄取入口，但输出是 manifest/span/index/export，不直接写研究 Wiki。 |
| ADR-003 | 收窄 | 至少一次执行、幂等效果与恢复日志继续适用；幂等键围绕 source identity、parser/version 和 export effect，不围绕投资 claim。 |
| ADR-004 | 收窄 | Company/Sector/Theme 可作来源路由元数据；SourceRecord、EvidenceSpan 继续。Question、Claim/Event、KnowledgePatch 的投资研究语义移交 StockWiki。 |
| ADR-005 | 收窄/待退役 | single writer 仅允许 source catalog、解析状态、原文索引和 extraction diagnostics 投影；legacy 研究 Wiki writer 冻结并进入 caller 归零流程。 |
| ADR-006 | 收窄 | proposal-first 只治理 collector/parser、source schema、来源实体映射和上游自动化；不得自动演化投资研究状态或报告。 |

## 修订规则

- 新 ADR 必须引用本 scope note，并声明是否影响 source contract 的 schema version 或兼容窗口。
- 若旧 ADR 与本说明冲突，以本说明和根目录 `task_plan.md` 的 BOUNDARY-0 为准。
- 恢复研究型 writer、估值链或跨仓写入必须由新的 owner 决策与独立审核明确授权，不能以旧 `accepted` 状态推断许可。
