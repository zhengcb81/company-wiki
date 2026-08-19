# Evidence Span v1

`evidence_span` 是 company-wiki 向 StockWiki 发布的上游解析结果契约。它把一个确定性的 parser output 绑定到已发布 `source_manifest` 的不可变 `source_id` 和稳定 locator；它不是研究证据裁决、accepted investment conclusion、评级或估值工件。

## 顶层字段

| 字段 | 规则 |
|---|---|
| `schema_version` | 固定为 `1.0.0`。 |
| `span_id` | `urn:company-wiki:evidence-span:sha256:<hash>`；hash 输入为 `source_id`、`locator`、`output_sha256` 的规范 JSON。 |
| `source_id` | 必须是 Source Manifest v1 的 `urn:company-wiki:source:sha256:<hash>`。 |
| `locator` | 由 `coordinates` 按固定顺序唯一生成的 `loc:v1/...`，反序列化时必须完全匹配。 |
| `coordinates` | 固定形状的页、段、表格和字符定位对象，所有键必须存在，未使用的维度为 `null`。 |
| `raw_text` | parser 输出的 NFC 原文字符串或 `null`。 |
| `structured_value` | 任意确定性 JSON 值或 `null`；禁止 NaN、Infinity、非字符串 object key 和自定义对象。 |
| `parser_name` | 非空、去首尾空白的 parser 标识。 |
| `parser_version` | 显式 semantic version；禁止 `latest` 等可漂移标签。 |
| `output_sha256` | 对 `{raw_text, structured_value}` 规范 JSON 计算的 SHA-256。 |
| `parse_status` | 仅允许 `parsed`、`partial`、`failed`、`quarantined`，只描述解析状态。 |
| `quality_flags` | 排序、去重的 extraction quality flag 列表。 |

## Coordinates 与 locator

`coordinates` 必须包含以下全部键：

- `page_number`：PDF/版式页码，1-based；
- `paragraph_index`：页内段落索引；无 `page_number` 时表示 normalized document 的全局段落索引，0-based；
- `table_index`：页内表格索引；无 `page_number` 时表示 normalized document 的全局表格索引，0-based；
- `row_index`、`column_index`：表内行列，0-based，依赖 `table_index`；
- `char_start`、`char_end`：normalized-document 字符流中的全局 `[start, end)`，0-based、end exclusive，两个端点必须同时出现且 `char_end > char_start`。

至少一个维度非空。段落与表格维度互斥。locator 按 `page → paragraph → table → row → column → chars` 固定顺序生成，例如：

```text
loc:v1/page:3/paragraph:5
loc:v1/page:12/table:2/row:3/column:1/chars:900-913
loc:v1/chars:144-172
```

## 身份与重放

规范 JSON 使用 UTF-8、NFC 字符串、递归 key 排序、无多余空白和 JSON 原生值。`output_sha256` 只随 parser 输出变化；`span_id` 只随 source、locator 或 output 变化。因此 parser 升级但输出完全相同时，`span_id` 保持稳定，而 `parser_version` 仍在记录中保留审计轨迹。

## 状态与质量旗标

- `parsed`：至少 `raw_text` 或 `structured_value` 非空；flags 可为空。
- `partial`：必须保留至少一种输出，并提供至少一个 flag 解释不完整性。
- `failed`：不得伪造输出，两个输出字段均为 `null`，且必须提供错误 flag。
- `quarantined`：可以保留可疑输出，但必须提供至少一个 flag，消费者不得把它当作已通过解析质检。

v1 flags 包括 OCR 使用/低置信度、布局或表结构歧义、截断、编码修复、单位或日期推断、locator 不稳定、parser warning/error、不支持格式、密码保护、空输出和首页身份矛盾（`homepage_identity_contradiction`——PDF 首页与 sidecar 声明的 title/publisher 冲突的 review 信号）。它们只描述 extraction quality；不允许使用 `accepted`、`rejected`、`buy`、`sell`、`rating`、`valuation` 等研究语义。

## 职责边界

company-wiki 负责 source identity、定位确定性、parser output hash 和解析质量。StockWiki 可以只读消费 span 并独立生成 evidence candidate、执行人工 research review 和维护下游状态；StockWiki 的结论变化不得反向改写本契约、manifest 或 raw source。

