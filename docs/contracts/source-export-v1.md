# Source Export v1

Source Export v1 是 company-wiki 的只读 consumer handoff。CLI 验证 immutable raw、Source Manifest v1 与 Evidence Span v1，随后把确定性 bundle 作为一行 canonical JSON 写到 stdout；它不创建 export 文件、不写 StockWiki，也不生成 accepted investment conclusion、评级或估值状态。

## CLI

```text
company-wiki-source-export export \
  --root REPOSITORY_ROOT \
  --manifests manifests.jsonl \
  --spans evidence-spans.jsonl
```

也可使用模块入口：

```text
python -m company_wiki.source_contract.cli export ...
```

- `--root` 是 manifest 中 `original_path` 的根目录；CLI 会重新读取并验证最终 bundle 的所有 raw。
- `--manifests`、`--spans` 是可重复参数，文件格式为 UTF-8 JSONL，每行一个严格 v1 object。
- `--base previous-export.json` 启用 add-only incremental merge。base 中的旧 manifest 也必须重新通过 raw 验证。
- CLI 没有 `--output`、publish、approve 或跨仓写入命令。成功只向 stdout 输出一行，失败只向 stderr 输出诊断并返回 exit code 2，因此进程崩溃不会留下半成品文件。

## Bundle 字段

| 字段 | 规则 |
|---|---|
| `schema_version` | 固定为 `1.0.0`。 |
| `export_id` | `urn:company-wiki:source-export:sha256:<bundle_sha256>`。 |
| `bundle_sha256` | 对下述非自引用 payload 的 canonical JSON 计算 SHA-256。 |
| `source_manifest_schema_version` | 当前固定为 Source Manifest `1.0.0`。 |
| `evidence_span_schema_version` | 当前固定为 Evidence Span `1.0.0`。 |
| `counts` | `source_manifests` 和 `evidence_spans` 的精确计数。 |
| `manifests` | 按 `source_id` 排序的严格 manifest 数组。 |
| `evidence_spans` | 按 `span_id` 排序的严格 span 数组。 |

hash payload 包含 `schema_version`、两个下游 schema version、`counts`、`manifests` 和 `evidence_spans`，不包含 `export_id` 与 `bundle_sha256` 本身。bundle 不包含运行时间、主机路径、随机 ID 或 export 模式，因此相同最终 record 集合产生相同 bytes、hash 和 ID。

## Incremental 与 replay

incremental 语义是 `base ∪ new records`，不是更新或覆盖：

- exact duplicate 按 ID 幂等去重；
- 同 ID 但 canonical record 不同会失败；
- 同一 `source_id + locator` 出现不同输出 span 会失败；
- span 引用 bundle 外 source 时作为 orphan 失败；
- 无新增记录的 replay 与 base 逐字节相同；
- 从空集合完整构建与通过 base incremental 得到同一最终集合时，输出必须逐字节相同。

## Raw fail-closed

输出前会对最终集合中的每个 manifest 执行路径、size 和 SHA-256 校验。raw 被删除、移动、替换或同尺寸篡改都会阻断 export；base 不会绕过该检查。CLI 只读 raw、JSONL 和可选 base，不修改源目录、输入文件、数据库或 Git 状态。

## 职责边界

bundle 只传递上游 source identity、parser output 和 extraction quality。StockWiki 可以保存 ID/hash 引用并独立进行 research review；评级、估值、accepted/rejected investment conclusion 和正式报告不属于 Source Export v1。

