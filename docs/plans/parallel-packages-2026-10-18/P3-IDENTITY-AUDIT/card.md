# P3-IDENTITY-AUDIT：来源身份、期间、单位与 SHA 的只读审计

状态：READY，2026-10-18。范围是**独立只读 CLI 工具**：把"导出说的事实"与"读取拿到的事实"逐字段比对，输出机器可读收据。不改运行时、不接生产。
PLAN_ID=parallel-packages-2026-10-18/P3-IDENTITY-AUDIT。

## 1. 真实问题

- `company-wiki-source-export-v2` 输出 `SourceExportBundleV2`（`schema_version="2.0.0"`），含 23 个 manifest 字段与 `bundle_sha256`；`company-wiki-source-read` 输出字节 + 收据（`2.1`，带 availability 时 `2.2`）。两条路径各自正确，但**没有任何工具**在同一个对象上核对"导出的 identity/period 与读到的 manifest 一致、span 文本与原文同区间字节一致、单位记号没被改写、未知发布日期仍是未知"。
- 现存测试（`tests/unit/test_canonical_import_reference.py`、`tests/integration/test_current_consumer_asof_contract.py` 等）覆盖各自切片，但不是一个可对任意 catalog 复跑、产出 JSON 收据的审计入口。
- 一旦导出侧与读取侧漂移（例如 canonical identity 投影改了 `security_id` 宽度、availability 证据缺失被写成日期），现在只能靠人工比对两段 JSON。

## 2. 目标

1. 新增 `tools/identity_audit/`：给定 catalog 配置与一份 request JSON，逐 source 产出 `identity-audit-receipt/1`。
2. 检查项固定六类：**ref**、**bytes**、**identity**、**period**、**availability**、**span/unit**。
3. 任何未知（缺字段、缺 availability 证据、无单位记号）如实标 `not_applicable`/`unknown`，**不得**折算成通过或 0。
4. 只读：唯一写操作是 `--out` 指向的一个 JSON 文件；catalog 以只读方式打开，前后哈希不变。

## 3. 非目标（明确不做）

- 不改 `source_reader.py`、`source_export_v2_cli.py`、`reader.py`、`source_availability.py` 或任何运行时模块；不新增 CLI 入口到 `pyproject.toml`。
- 不校验消费端（FF/RF）行为——那是 P4；本卡不 import P4，也不读 FF/RF 目录。
- 不重新解析 PDF/DOCX、不做 OCR、不做表格结构。
- 不判断"这份材料是否值得读/是否支持某结论"；不产出任何投资语义。
- 不修数据：发现问题只报告，不改 catalog、不改 manifest、不写侧车。

## 4. 独占写集

- `tools/identity_audit/**`（新建：`__init__.py`、`cli.py`、`core.py`、`export.py`、`receipt.py`、`README.md`）
- `tests/unit/test_identity_audit/**`（新建，含 `fixtures/**`）
- `docs/plans/parallel-packages-2026-10-18/P3-IDENTITY-AUDIT/**`

**禁写**：`src/**`（整目录，含 `source_catalog`、`document_normalization`、`parser_adapters`、`document_understanding`、`automation`）；`tests/integration/**`、`tests/unit` 下其他目录；`tools/` 下除 `identity_audit/` 之外的任何路径；`pyproject.toml`；`.githooks/**`；ROOT 独占清单（`narrative_reading.py`、`narrative_operating_relations.py`、`narrative_antecedent.py`、`operating_states/relations.py`、`operating_states/product_reference.py`、`tests/unit/du11_source_closure/**`、`docs/plans/du11-*/**`、`docs/plans/document-understanding-2026-10-13/**`）与其余三卡写集。

## 5. 冻结接口

### 5.1 CLI

```powershell
python -m tools.identity_audit --config <catalog yaml> --request <request.json> [--out <receipt.json>] [--pretty]
```

- 成功/失败都向 stdout 打**一行** JSON（同 `source_reader_cli` 风格：`ensure_ascii=True, sort_keys=True, separators=(",",":")`）；日志与进度只走 stderr。
- `--out` 写入用"临时文件 + `os.replace`"，内容与 stdout 等价（`--pretty` 只影响可读格式，不影响字段）。
- 退出码：`0` = 全部适用检查通过；`2` = 至少一项 `fail`；`3` = `blocked/unavailable`。
- 参数错误 → 退出码 `3`、`status="blocked"`、`reason="invalid_argument"`，不打印 usage 到 stdout。

### 5.2 request（`identity-audit-request/1`）

```json
{"schema_version":"identity-audit-request/1",
 "source_refs":[{"document_id":"...","source_id":"...","content_sha256":"<64hex>",
                 "byte_size":123,"mime_type":"application/pdf","schema_version":"2.0"}],
 "evidence_spans":[{"schema_version":"1.0.0","span_id":"...","source_id":"...",
                    "locator":"...","coordinates":{"page_number":null,"paragraph_index":null,
                    "table_index":null,"row_index":null,"column_index":null,
                    "char_start":0,"char_end":12},
                    "raw_text":"...","structured_value":null,
                    "parser_name":"...","parser_version":"...",
                    "parse_status":"parsed","quality_flags":[]}],
 "expect":{"market":"CN","security_id":"688012","fiscal_year":2026,
           "fiscal_period":"H1","period_end":"2026-06-30",
           "published_date":null}}
```

- `source_refs` 字段必须与 `SourceRef` 精确一致（`_REF_FIELDS`），多/少字段即 `invalid_request`。
- `evidence_spans` 用 `EvidenceSpan.from_dict` 解析；非法即 `invalid_request`。
- `expect` 可省；给出时只用于 identity/period 的**比对**，不用于"填值"。

### 5.3 收据（`identity-audit-receipt/1`）

顶层：`schema_version`、`status`、`generated_at`、`inputs`（config/request 的 sha256 与 bytes）、`counts`、`limitations`（INTERFACES 第 7 节外壳）+ `sources`。

每个 source：

```json
{"document_id":"...","source_id":"...","content_sha256":"...",
 "checks":{
  "ref":{"status":"pass|fail","detail":{"byte_size":123,"mime_type":"..."}},
  "bytes":{"status":"pass|fail","detail":{"sha256":"...","bytes":123}},
  "identity":{"status":"pass|fail|not_applicable",
              "observed":{"document_kind":null,"canonical_entity_id":"...","market":"CN",
                          "security_id":"688012","form_type":null,"title":"...","language":"zh"},
              "expected":{"market":"CN","security_id":"688012"}},
  "period":{"status":"pass|fail|not_applicable",
            "observed":{"fiscal_year":2026,"fiscal_period":"H1","period_end":"2026-06-30",
                        "published_date":null,"unknown_source":"nullable_manifest"}},
  "availability":{"status":"pass|source_availability_unknown",
                  "detail":{"evidence":null,"reason":"no_verified_capture_evidence"}},
  "spans":[{"span_id":"...","status":"pass|fail|not_applicable","reason":null,
            "detail":{"char_start":0,"char_end":12,"unit_status":"pass"}}],
  "unit":{"status":"pass|fail|not_applicable",
          "tokens":[{"text":"百万元","char_start":140,"char_end":143}],
          "reason":"no_unit_token_in_span"}}
}
```

### 5.4 判定规则（必须按此实现）

1. **ref**：`SourceVersionReader.query_ref` 返回的 `byte_size`/`mime_type` 与 request 相等 → `pass`；否则 `fail` + `p3_ref_mismatch`。
2. **bytes**：`open_described_version` 拿到字节后重算 `sha256`，与 `content_sha256` 相等且 `len(bytes)==byte_size` → `pass`；否则 `fail` + `p3_bytes_mismatch`。
3. **identity**：取 manifest 的 `document_kind/canonical_entity_id/market/security_id/form_type/title/language`；并用 `canonical_security_code(security_id, market)` 复算规范化身份，必须与 manifest 的 `security_id` 一致。`expect` 的键分三种：缺键 = 不设期望；显式 `null` = 期望未知（manifest 必须也是 `null`）；具体值 = 必须相等。任一侧 `null` 与另一侧非 `null` → `fail` + `p3_identity_conflict`；跨市场不得互相借用。
4. **period**：比对 `fiscal_year/fiscal_period/period_end/published_date`。`published_date=null` 时禁止用 `retrieved_at` 或本地下载时间顶替（本工具根本不读这两个字段）。manifest 的 `published_date` 非空但 availability 证据为 `null` → **不算伪造**（observed 值本身合法），记 `detail.date_provenance="unverified"`，`status` 仍 `pass`；只有与 `expect` 冲突、或日期不是合法 ISO 日期（`YYYY-MM-DD`）时才 `fail` + `p3_period_conflict`。任何路径都不得把 `null` 写成日期。
5. **availability**：`verified_availability_evidence(catalog, ref)` 返回 `None` → `status="source_availability_unknown"`、`evidence=null`；返回 dict → `pass`，并把 `schema_version`/`source_url`/`captured_at` 原样放进 `evidence`。
6. **span**：仅当 `mime_type=="text/plain"`、`raw_text` 非空、`structured_value==None`、且 `page/paragraph/table/row/column` 全为 `null` 时做区间校验：把原文字节解码为 `str`，取 `[char_start:char_end]`，必须与 `raw_text` 逐字符相等 → `pass`；否则 `fail` + `p3_span_ungrounded`。其它形状一律 `not_applicable` + `reason="not_groundable_shape"`（不得假装通过）。
7. **unit**：对通过校验的 span 文本（或全文不可得时跳过）扫描单位记号，闭集正则：`单位[:：]\s*(人民币)?(百万元|千万元|万元|千元|亿元|元)`、`(人民币|RMB|CNY|USD|HKD|million|billion|thousand)`、`[%％]`。命中则记录 `text/char_start/char_end`；同一 span 在 `raw_text` 与原文切片中的记号序列（文本+相对区间）必须一致 → `pass`；无命中 → `not_applicable` + `reason="no_unit_token_in_span"`；不一致 → `fail` + `p3_unit_mismatch`。**不做换算、不推断数量级、不补币种。**
8. 单 source 任一 `fail` → 该 source `status="fail"`；任一 `blocked` → 顶层 `blocked`；否则 `pass` 或 `unavailable`。

## 6. TDD 要求

**A：真实 RED（≥15 用例，实现前失败）**

- `query_ref` 返回 `byte_size` 与 request 不符 → `ref.fail`（不是异常冒出）。
- 字节被替换（同长度）→ `bytes.fail` + `p3_bytes_mismatch`。
- `security_id` 宽度不一致（`9896` vs `09896`，CN 6 位）→ `identity.fail`；同值不同市场（`CN`/`HK`）→ `fail`，不得借用 market。
- `expect` 给了 `fiscal_period` 而 manifest 为 `null` → `fail`，不得当 `pass`。
- `published_date=null` 且 availability 证据为 `None` → `availability.status="source_availability_unknown"` 且顶层仍可 `pass`。
- 未知日期被写成 `2026-08-01`（无证据）且 `expect.published_date=null` → `p3_period_conflict`。
- `raw_text` 与原文区间差一个字符 → `span.fail`。
- span 带 `page_number` → `not_applicable`（不许强行校验）。
- 单位记号在 `raw_text` 有、原文同区间没有 → `p3_unit_mismatch`。
- 无单位记号 → `not_applicable` 且 `reason` 明确。
- 空 `source_refs` → `blocked` + `invalid_request`（不是 `pass`）。
- `schema_version` 错 → `blocked`。
- request 有重复 JSON key → `blocked`（复用 `source_export_v2_cli` 的 `object_pairs_hook` 思路）。
- 只读证明：运行前后 catalog 文件 `sha256` 与 `mtime` 不变；`--out` 之外无新文件。
- 与 CLI 等价：同一夹具上，库调用结果与 `company-wiki-source-export-v2` 子进程输出逐字段相等（`SourceExportBundleV2.to_dict()` 对照）。

**B：实现 + 集中 GREEN**；**C：静态检查 + 交接**。

夹具：`tmp_path` 内生成最小 catalog（复用 `tests/unit` 既有 helper 的构造方式，但**复制**到本卡 `fixtures/**`，不 import 其他测试模块），并保存配置与 request 的 `sha256`。

禁止：删用例、`skip`、`try/except` 吞异常、把 `unknown` 断言改成 `pass`。

## 7. 验收命令与完成定义

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest tests/unit/test_identity_audit -q -p no:cacheprovider
python -m ruff check tools/identity_audit tests/unit/test_identity_audit
python -m mypy tools/identity_audit
python -m tools.identity_audit --config <fixture>/catalog.yaml --request <fixture>/request.json --pretty
```

**完成定义**

1. 四条命令 + 一次手工 CLI 调用 exit 0（手工那次用 `fixtures/`，输出 `receipt.json` 存本卡目录）。
2. ≥15 用例全绿无跳过；RED/GREEN 日志在本卡目录。
3. `git diff --stat` 中 `src/**` 出现 0 次。
4. 收据字段与 `identity-audit-receipt/1` 完全一致（把 `fixtures/receipt.json` 与 INTERFACES 对照，多一个字段都算超标）。
5. 独立审查 PASS 且绑定最终 SHA。
6. 写明"未对生产 catalog 运行；未验证 PDF span 区间"。

## 8. 资源与安全边界

- catalog 以只读打开；不 `VACUUM`、不迁移、不写 WAL 之外的文件；测试前后核对 `sha256`。
- 不读密钥；不联网；不构造模型客户端。
- `--out` 是唯一写；路径必须是普通文件（拒绝目录、拒绝 `..` 逃逸、拒绝重解析点）。
- 不写 `config/source_catalog.yaml`、生产 DB、`output/`、gold。
- 不新增人工许可或审批文件。
- 单次运行上限：`source_refs ≤ 500`、`evidence_spans ≤ 5000`、收据 ≤ 16 MiB；超限 `blocked` + `limit_exceeded`。

## 9. 交接格式

`handoff.md` ≤80 行四段式。`handoff.json` 在外壳上补充：

```json
{
  "lane": "P3-IDENTITY-AUDIT",
  "interface_versions": {"request": "identity-audit-request/1", "receipt": "identity-audit-receipt/1"},
  "entrypoint": "python -m tools.identity_audit",
  "known_limits": ["PDF/DOCX span 区间不校验", "单位只做记号一致性，不换算"],
  "root_integration_steps": [
    "用真实 catalog 复跑一次并保存收据（只读）",
    "把 receipt 的 counts 与 limitations 纳入发布前后对照",
    "不得把本工具接进生产 worker 或 CI 门禁，除非 ROOT 明确决定"
  ]
}
```

## 10. 独立审查要求

- 审查者 ≠ 作者、≠ ROOT。
- 重点：是否存在"未知→通过"的路径；`not_applicable` 是否被滥用为放行；只读是否真的只读（要求审查者改一个字节验证 `bytes.fail` 能触发）；收据是否有字段超纲；退出码与 `status` 是否一致。
- 修完对最终 SHA 复审；报告写 `review/independent.md`。
