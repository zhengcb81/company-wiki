# 证据粒度提案：表格级 + 新闻免 span（Phase 3）

> 状态：提案（供上游 schema/parser 评审，不直接实施）｜ 2026-08-07
> 决策依据：D2=表格级（用户拍板）、D3=新闻免 span（用户拍板）

## 现状与问题

- `evidence_spans` 25,985,291 行（治理后 retired 已归档 25.7M，剩 active 约 0.3M 行 + 新增）。单元格级粒度（`loc:v1/page:N/table:T/row:R/column:C`）是体积倍数主因：财报逐页逐段落逐表格单元格拆解，单份大财报可达 ~8,000 span（findings 发现 5）。
- 空间构成（findings 发现 4）：span_json 平均 799B + URN/locator/parser 字段 ~364B ≈ 1.16KB/行；~13.5GB 为索引/页结构。**粒度越细，行数与索引体积越大**。
- 若全量按现状粒度归一化（pending 20,728），DB 粗估 100 GB+。

## 提案 1：表格证据降为表格级

- parser（`pdf_page_aware_core`）配置化证据粒度：`table_cell`（现状）→ `table_level`（整表一条 span）。
- 表格 span 的 locator 从 `loc:v1/page:N/table:T/row:R/column:C` 变为 `loc:v1/page:N/table:T`（row/column 维度过时——locator 语义变化，属 schema 契约演进，需 `EvidenceCoordinates`/`locator()` 版本化）。
- 段落证据保持段落级不变（研究引用段落文本是核心）。
- **兼容性**：新 `parser_version` 下旧 locator 不重写（旧 span 保持有效，StockWiki 引用不破）；`UNIQUE(source_id, locator)` 与新粒度共存。
- **预期**：表格 span 量降 ~95%（每表 1 条 vs 每单元格 1 条）；全库 span 总量降 ~60–80%（表格单元格占大头）；对应 DB 体积降幅 30–50%。

## 提案 2：新闻免 span

- `original_news`（pending 903 份）不产 `evidence_spans`，只产 `normalized.md`（全文可查、可溯源到源文件）。
- 理由：新闻无表格结构，单元格级证据无意义；段落级对新闻的增量价值低（D3 用户拍板"免 span"）。
- **预期**：新闻类 903 份归一化不产生证据行，DB 体积减少。

## 迁移路径（二选一，建议 B）

| 方案 | 做法 | 取舍 |
|---|---|---|
| A 新库重建 | 新粒度 + 新参数建新库，旧库归档 | 干净但停机窗口长、迁移复杂 |
| B 分批重解析（建议） | 复用 normalizer 替换语义，按文档分批用新粒度重解析（DELETE 旧 span + INSERT 新） | 停机可控、幂等、与现有 worker 调度衔接 |

## 验收

- 粒度统计：按 locator 类型分布（表格级后每文档 span 数、全库 span 总量、DB 体积）。
- 回归：contract 测试全绿（`pytest tests/contract`）；`UNIQUE(source_id, locator)` 不冲突；旧 locator 引用仍有效。
- 消费方：invest-*/revenue evidence 契约兼容（表格级引用的 `target/locator/excerpt` 语义更新文档）。

## 关联

- ADR-009（决策 D2/D3 记录）；task_plan Phase 3/4。
