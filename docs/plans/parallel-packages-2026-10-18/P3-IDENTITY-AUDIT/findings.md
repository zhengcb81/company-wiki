# P3-IDENTITY-AUDIT 侦察发现（实现前实测，非推测）

所有结论均在 worktree `company-wiki-p3-identity-audit`（基线 `4045787f`）用本机 Python 3.13.9
实测得出，脚本在 `%TEMP%` 下，不落仓库。

## 1. 读取侧接口（只读引用，不得修改）

- `SourceRef`（`source_reader.py:78`）字段序：`document_id, source_id, content_sha256,
  byte_size, mime_type, schema_version="2.0"`。request 的 `source_refs[]` 字段必须与之精确相等。
- `SourceVersionReader.query_ref(document_id, source_id, expected_sha256) -> SourceRef`。
  实测错误映射：
  - `expected_sha256` 不存在 → `SourceReadError("unavailable","expected_version_mismatch")`
  - `source_id` 不匹配 → `("not_found","document_source_mismatch")`
  - 非字符串/空 → `ValueError`（不是 SourceReadError）
- `open_described_version(ref, purpose="source_export") -> (VerifiedContent, manifest)`；
  `VerifiedContent.data: bytes`、`byte_size`。
  实测字节被替换（同长度）→ `SourceReadError("unavailable","no_verified_location")`，
  `detail="content_sha256_mismatch"`；长度不同 → `detail="byte_size_mismatch"`。
  **因此 `bytes.fail` 必须从字节自算 sha256 得出，不能依赖 `open_described_version` 抛异常**：
  一旦替换，读取侧直接拒读。本卡做法是：读取侧拒读时，若 request 的
  `content_sha256` 与 catalog 行不一致，则按 `p3_bytes_mismatch` 记 `bytes.fail`（见 §5）。
- `describe_version(ref)` 返回 23 键（实测）：`document_id, source_id, content_sha256,
  byte_size, mime_type, title, document_kind, published_date, source_url, retrieved_at,
  collector_name, collector_version, canonical_entity_id, display_name, market, security_id,
  fiscal_year, fiscal_period, period_end, form_type, provider, provider_document_id, language`。
  `fiscal_year` 是 `int`；其余字符串字段是 `str|None`（`claim()` 把空串折成 `None`）。
- `security_id` 在 **manifest** 里保留观测原值（实测 sidecar 写 `9896` → manifest `9896`）；
  `canonical_security_code("9896","CN") == "009896"`。所以 identity 检查要把
  "复算规范化码" 与 manifest 观测值比对，用来发现宽度漂移。
- `metadata_diagnostics(ref)` 存在但不在本卡写集/需要范围内。

## 2. availability

`verified_availability_evidence(catalog, ref) -> dict|None`。实测返回键（6 个）：
`schema_version="source-availability-evidence/1"`、`source_sha256`、`available_by`（YYYY-MM-DD）、
`basis="prior_verified_capture"`、`evidence_ref`、`locator`。

**card.md §5.4(5) 的 `source_url`/`captured_at` 与实际键不符**：实际证据里既没有
`source_url` 也没有 `captured_at`，只有 `available_by`。处理方式：把真实返回的
dict **原样**放进 `detail.evidence`（不增不改键），并在 `known_limits` 里写明
"card 文案的 source_url/captured_at 在当前契约中不存在，收据按实际键原样透传"。
无证据 → `status="source_availability_unknown"`、`detail={"evidence":null,
"reason":"no_verified_capture_evidence"}`。

实测触发条件：sidecar 里要有 `candidate` + `receipt` 两个 dict，receipt 需满足
`DownloadReceipt` 全部约束（`http_status` 2xx、`source_url` 必须 `https://`、
`retrieved_at` 形如 `2026-08-02T03:04:05Z`、`byte_size>0`、`adapter_version` semver），
且顶层 `content_sha256/byte_size/mime_type/retrieved_at/provider/provider_document_id/source_url/
adapter_name/adapter_version` 与 receipt 逐键相等。

## 3. 夹具构造（侧车 catalog）

最小可用夹具（实测通过）：

```
<root>/lake/<Entity>/doc.txt                 # 原文，text/plain 才能做 span 校验
<root>/lake/<Entity>/doc.txt.source.json     # sidecar schema_version="1.0"
<root>/config/source_catalog.yaml            # 或直接构造 CatalogConfig
```

sidecar 必需键（`_REQUIRED_IDENTITY` + `_REQUIRED_FACTS` + `_REQUIRED_PROVENANCE`）：
`canonical_entity_id, market, security_id` + `document_kind, fiscal_year, period_end,
content_sha256` + `provider, provider_document_id`。
`filing_date`（或 `published_at`）决定 manifest `published_date`；缺省则为 `null`。
`fiscal_period`、`form_type`、`language`、`source_title` 直接透传。

`SourceCatalog.scan()` 后：
`catalog.reader.fetchone("SELECT document_id, primary_source_id AS source_id FROM documents")`。
`.txt` 后缀 → `mime_type == "text/plain"`（`trace_parity._MIME_BY_SUFFIX`/`scanner`）。

**观测（`published_date` 缺省时）**：manifest `published_date` 为 `None`，但 sidecar 里
若显式写 `"published_date": null` 也同样是 `None`——两者不可区分，这正是
`unknown_source="nullable_manifest"` 要标注的事实。

## 4. 只读性质（实测）

`SourceCatalog.reader` 是 `ReadOnlyCatalogReader`（`file:...?mode=ro` + `PRAGMA query_only=ON`），
且 `service.reader` 只在被访问时才建连接。实测：`open_described_version` 前后，
整个夹具目录（含 catalog 目录）文件集合、大小、mtime、sha256 **完全不变**，
`close()` 之后也没有新增 `-wal`/`-shm` 残留。`query_ref` 是纯 SELECT。
`SourceCatalog(config)` 构造本身不建库（`database_path` 只在 reader/store 被访问时才打开），
因此"catalog 不存在"时会以 `CatalogReaderUnavailable`/`sqlite3.Error` 形式失败 → `unavailable`。

## 5. bytes.fail 的可达性（重要设计约束）

读取侧 `open_described_version` 对内容不符是**拒读**而不是返回错误字节。因此
`bytes` 检查若只写 "`len(data)` 与 sha256 自算" 就永远只有 pass 分支。
本卡按 card §5.4(2) 的字面实现：

1. 先 `query_ref`（catalog 行必须与 request 的 `document_id/source_id/content_sha256` 一致；
   不一致本身先记 `ref.fail`/`unavailable`）。
2. `open_described_version` 取字节 → 自算 `sha256(data)` 与 `len(data)` 比对 → pass。
3. 读取侧拒读（`SourceReadError`）时，把 refusal 记进 `bytes.detail.refusal`
   （`status`/`reason`/`detail` 三字段），并给出 `bytes.status="fail"` +
   `p3_bytes_mismatch`——因为"catalog 声明的版本读不出与声明一致的字节"就是本检查的
   不通过，**不得**退化成 `unavailable` 或 `pass`。
4. 只读证明由独立测试完成：同长度替换一个字节 → `bytes.status=="fail"` 且
   `error_code=="p3_bytes_mismatch"`，且原件与 catalog 文件 sha256 前后不变。

## 6. span / unit

- `EvidenceSpan.from_dict` 要求 12 个键齐全（`schema_version, span_id, source_id, locator,
  coordinates, raw_text, structured_value, parser_name, parser_version, output_sha256,
  parse_status, quality_flags`），且 `span_id`/`output_sha256` 必须自洽
  （`evidence_span_id_for(source_id, locator, output_sha256_for(raw_text, structured_value))`）。
  测试里用 `EvidenceSpan.create(...)` 构造再 `.to_dict()`。
- `EvidenceCoordinates` 字段序 7 个，`page_number>=1`，其余 `>=0`；至少要有一个非 null；
  `char_start/char_end` 必须成对且 `char_end > char_start`；`row/column` 需要 `table_index`；
  `paragraph_index` 与 `table_index` 互斥。
- 可校验形状（与 `source_export_v2._is_groundable_text_shape` 一致）：
  `mime_type=="text/plain"` + `raw_text is not None` + `structured_value is None` +
  `char_start/char_end` 非 null + `page/paragraph/table/row/column` 全 null。
  其它形状 → `not_applicable` + `reason="not_groundable_shape"`。
- 单位闭集正则（card §5.4(7)）：
  `单位[:：]\s*(人民币)?(百万元|千万元|万元|千元|亿元|元)`、`(人民币|RMB|CNY|USD|HKD|million|billion|thousand)`、`[%％]`。
  实测原文 `"Acme 2026 H1 单位：百万元 营业收入 1,234\n"`：第一个正则在 `"单位：百万元"` 上命中
  （`text="单位：百万元"`，`char_start/char_end` 相对该文本），第二个正则会**再次**命中其中的
  `"百万元"` 吗？—— 不会：`百万元` 不在第二个正则的枚举里（只有 `万元`/`千元`/… 在第一个），
  两个正则的枚举集合不重叠，闭集扫描按 (start, end) 去重后无需处理重叠。实现仍按
  起点顺序扫描并对完全相同的区间去重，避免重复记号被算两次。

## 7. 与 `company-wiki-source-export-v2` 的等价性（card §6 最后一条）

CLI 形状：stdin 读 request JSON，stdout 一行 canonical JSON bundle。实测无 span 时
`open_version` 被 `verify_version` 取代（只校验不保留字节），`bundle_sha256` 与
`_payload_json` 自洽。本卡只对 **manifest 的 23 个字段**做逐字段相等断言（不含
`bundle_sha256`/`export_id`，它们绑定的是整包排序与 hash 负载，不是单一 source 的
读取事实），并在测试里用 `subprocess` 跑一次真实 CLI 取回 bundle 再比对。

> 注意：测试里跑子进程**不捕获** stdout/stderr（本环境 `child_process` 管道受限），
> 改为把输出重定向到 `tmp_path` 文件再读文件。

## 8. 与本卡无关但需遵守的仓库守卫

- `tests/conftest.py`：会话级 `production_config_integrity` 断言
  `config/source_catalog.yaml` 会话前后 sha256 不变；`hermetic_runtime` 阻断 socket。
  本卡夹具一律用 `tmp_path`，不碰生产配置。
- `pytest.ini` 只有 `addopts = -v --tb=short --strict-markers`，无 `--strict-config`。
- `tools/` 下没有 `__init__.py`（`tools/__init__.py` 不存在），但 `tools/g3_source_facts/`
  是一个包；`python -m tools.identity_audit` 依赖 namespace package 语义 + cwd 在仓库根。
  验收命令模板里的 `PYTHONPATH=src` 不含 `tools`，所以入口必须能从仓库根以
  `python -m tools.identity_audit` 运行（实测 `tools.*` 走隐式命名空间包可行）。
