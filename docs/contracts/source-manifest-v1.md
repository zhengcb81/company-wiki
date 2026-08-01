# Source Manifest v1

`source_manifest` 是 company-wiki 向 StockWiki 等消费者发布的上游来源身份合同。当前 schema version 为 `1.0.0`，JSON Schema ID 为 `urn:company-wiki:schema:source-manifest:1.0.0`。

## 字段

| 字段 | 类型 | 规则 |
|---|---|---|
| `schema_version` | string | 固定为 `1.0.0`。 |
| `source_id` | string | `urn:company-wiki:source:sha256:<content_sha256>`；只由原始字节决定，不包含路径。 |
| `entity_ids` | string[] | 至少一个稳定实体 ID；NFC、去重、按 Unicode 排序。 |
| `original_path` | string | 仓库根目录内的 NFC/POSIX 相对路径；禁止绝对路径、反斜杠、空段、`.` 和 `..`。 |
| `content_sha256` | string | 原始文件字节的小写 64 位 SHA-256。 |
| `source_type` | enum | 监管财报、公告、IR、研报、原创/聚合新闻、招股书或 other。 |
| `published_date` | string/null | 来源发布日期，规范 `YYYY-MM-DD`；未知时为 null。 |
| `retrieved_at` | string | 调用方显式提供的 UTC `YYYY-MM-DDTHH:MM:SSZ`；不使用当前时钟默认值。 |
| `collector_name` | string | 采集器稳定名称。 |
| `collector_version` | string | 采集器 semantic version，不允许 `latest`。 |
| `mime_type` | string | 小写 `type/subtype`。 |
| `byte_size` | integer | 必须大于 0；空文件不能成为来源。 |
| `immutable_status` | enum | `verified` 或 `quarantined`；从文件构建时固定为 verified。 |

## 身份与重放

- 相同字节在不同路径产生相同 `source_id`/`content_sha256`，但保留各自 `original_path`。
- `SourceManifest.from_file` 只读取真实普通文件；missing、空文件、根目录外路径或散列期间发生变化均 fail closed。
- `verify_file` 同时复验规范路径、byte size 和 SHA-256；任一变化都返回确定性 mismatch，不改写 raw。
- `canonical_json()` 使用 UTF-8、键排序、无多余空白，便于消费者计算稳定工件 hash。

## 语义边界

`source_type` 不接受 `model_inference`：模型输出不是原始来源。`immutable_status=verified` 只表示来源字节、位置和元数据通过上游校验，不代表证据支持任何投资命题，也不是 accepted investment conclusion。

company-wiki 不在 manifest 中写评级、估值、review decision 或报告状态；StockWiki 只读消费 `source_id`/hash，并独立拥有全部下游研究状态。
