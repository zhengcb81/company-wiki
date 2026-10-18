# 并行施工包固定接口 / 2026-10-18 / 1

本文件是 P1–P4 四张卡的**共用约定**，不是第二套运行时契约、权限合同或研究结论。各卡在自己的目录内实现，只 import 标准库、既有公共契约（`company_wiki.source_contract`、`company_wiki.document_normalization.local_ocr` 的既有类型）与自身模块；**四卡之间不得互相 import**。

## 1. 通用数据规范

- 编码：UTF-8，无 BOM。JSON 输出用 `json.dumps(..., ensure_ascii=True, sort_keys=True, separators=(",", ":"))` 单行；需要人读时另存 `--pretty` 副本，两者内容等价。
- 大小上限：单个 JSON 收据 ≤ 16 MiB；超限即 `status="blocked"`、`reason="receipt_too_large"`，不得截断后冒充完整。
- 重复键、非有限浮点（NaN/Infinity）、非 UTF-8 字节：一律拒绝，`status="blocked"`、`reason="invalid_json"`。
- 未知值用 `null`，**不得**用 `""`、`0`、`[]` 或 "已处理" 代替。未知与"确认为空"是两件事。
- 所有哈希：小写十六进制 SHA-256，对**原始字节**计算；文本比较前不做换行归一化，除非该字段明确声明为 `normalized_text`。

## 2. 状态词表（全包唯一）

| 值 | 含义 | 用在哪 |
|---|---|---|
| `ok` | 全部适用检查通过 | 收据顶层 |
| `partial` | 有可用结果，但有单元被 defer/截断/未知 | 收据顶层、页、表 |
| `fail` | 至少一项适用检查不通过 | 审计/契约卡 |
| `blocked` | 输入非法、超限、或前置不可满足，无法给出结论 | 任何卡 |
| `unavailable` | 依赖（catalog/文件/消费端）不可读 | P3/P4 |
| `not_applicable` | 该检查对该对象不成立（如 PPTX 无分页） | 单项检查 |
| `not_evaluated` | 本卡未运行该检查（缺真实材料/未接生产） | 单项检查、`not_run` |

规则：顶层 `status` 只取前五个；`not_applicable`/`not_evaluated` 只出现在单项检查里，且必须带 `reason`。

## 3. 错误码

前缀固定：`p1_`、`p2_`、`p3_`、`p4_`。码值 snake_case，只增不改。

| 码 | 卡 | 触发 |
|---|---|---|
| `p1_line_confidence_low` | P1 | 行置信度低于阈值，已 defer |
| `p1_order_ambiguous` | P1 | 两行几何交叉，阅读顺序不可判定 |
| `p1_bbox_invalid` | P1 | 框越界/非有限/宽高为 0 |
| `p1_page_limit` | P1 | 行数或字符数超限 |
| `p2_span_out_of_grid` | P2 | gridSpan 超出 tblGrid 列数 |
| `p2_merge_unresolved` | P2 | vMerge/合并链断裂，无法归并 |
| `p2_footnote_unresolved` | P2 | footnoteReference 找不到 footnote 文本 |
| `p2_continuation_unknown` | P2 | 无分页提示，续表关系不可判定 |
| `p2_table_limit` | P2 | 表/格/字符超限 |
| `p3_ref_mismatch` | P3 | SourceRef 与 catalog 行不一致 |
| `p3_bytes_mismatch` | P3 | 读到字节的 SHA 与 ref 不符 |
| `p3_span_ungrounded` | P3 | span 文本与原文同区间字节不符 |
| `p3_identity_conflict` | P3 | 导出与读取两侧身份字段冲突 |
| `p3_period_conflict` | P3 | 期间字段冲突或伪造日期 |
| `p3_unit_mismatch` | P3 | 单位记号集合/区间不一致 |
| `p3_availability_fabricated` | P3 | 未知可用性被写成确定日期 |
| `p4_consumer_field_missing` | P4 | 消费端观测缺必需字段 |
| `p4_consumer_unit_rescaled` | P4 | 引用值单位被静默换算 |
| `p4_unknown_availability_lost` | P4 | 消费端丢失 `source_availability_unknown` |
| `p4_network_attempted` | P4 | 捕获到网络调用 |
| `p4_model_attempted` | P4 | 捕获到模型/供应商调用 |

公共码（不带卡前缀）：`invalid_json`、`invalid_argument`、`limit_exceeded`、`receipt_too_large`、`dependency_unavailable`、`not_configured`。

## 4. 偏移与单位

- `char_start/char_end`：对 `unit.text` 或原文解码文本的 **Python `str` 字符**偏移，左闭右开；不是 UTF-8 字节偏移。
- 需要字节时单独给 `byte_start/byte_end`，且必须由 `text[char_start:char_end].encode("utf-8")` 自证一致。
- `box`：`[x0, y0, x1, y1]`，非负有限浮点，`x1 > x0`、`y1 > y0`，坐标原点在页面左上。
- `confidence`：`[0.0, 1.0]` 有限浮点；未知不给 0，给 `null`。
- 单位记号（unit token）：原文里出现的货币/量纲写法，例如 `单位：百万元`、`人民币千元`、`%`、`USD`、`million`。**不做换算、不补缺、不推断数量级。**

## 5. 质量旗标

只能使用 `company_wiki.source_contract.evidence_span.QualityFlag` 已有的值，本包固定会用到的有：`ocr_used`、`low_ocr_confidence`、`layout_ambiguous`、`table_structure_ambiguous`、`truncated`、`unit_inferred`、`date_inferred`、`locator_unstable`、`parser_warning`。

- 不得新增枚举值（那是跨层契约变更，交 ROOT）。
- 不得用旗标表达"我认为这段是投资要点"之类的语义判断。

## 6. 版本号（全包唯一）

| 常量 | 值 | 归属 |
|---|---|---|
| `P1_PAGE_TEXT_SCHEMA` | `cwp-ocr-page-text/1` | P1 |
| `P1_PAGE_TEXT_VERSION` | `1.0.0` | P1 |
| `P2_OFFICE_TABLE_SCHEMA` | `cwp-office-table/1` | P2 |
| `P2_OFFICE_TABLE_VERSION` | `1.0.0` | P2 |
| `P3_REQUEST_SCHEMA` | `identity-audit-request/1` | P3 |
| `P3_RECEIPT_SCHEMA` | `identity-audit-receipt/1` | P3 |
| `P4_COMMANDS_SCHEMA` | `p4-consumer-commands/1` | P4 |
| `P4_RECEIPT_SCHEMA` | `p4-contract-receipt/1` | P4 |
| `HANDOFF_SCHEMA` | `parallel-packages-handoff/1` | 全包 |

只读引用的既有版本：`SOURCE_REF_SCHEMA_VERSION="2.0"`、`SOURCE_READ_RECEIPT_SCHEMA_VERSION="2.1"`、`AVAILABILITY_RECEIPT_SCHEMA_VERSION="2.2"`、`AVAILABILITY_EVIDENCE_SCHEMA_VERSION="source-availability-evidence/1"`、`SOURCE_EXPORT_V2_SCHEMA_VERSION="2.0.0"`、`EVIDENCE_SPAN_SCHEMA_VERSION="1.0.0"`、`cwp-docx-body/1`、`cwp-pptx-shape/2`。这些由 CWP 生产方拥有，本包**不得**修改或重新定义。

## 7. 收据通用外壳

每卡的主收据都带这 6 个字段，其余按卡自定义：

```json
{
  "schema_version": "<该卡 RECEIPT_SCHEMA>",
  "status": "ok|partial|fail|blocked|unavailable",
  "generated_at": "2026-10-18T08:00:00Z",
  "inputs": {"<path-or-id>": {"sha256": "...", "bytes": 0}},
  "counts": {"checked": 0, "passed": 0, "failed": 0, "not_applicable": 0, "not_evaluated": 0},
  "limitations": ["未运行真实原件；仅合成夹具"]
}
```

时间：UTC ISO-8601，秒级，带 `Z`；同一收据内所有时间同源（不得混本机时区）。

## 8. 交接文件

每卡在自己目录写 `handoff.md`（人读，≤80 行）与 `handoff.json`（机器读）。`handoff.json` 必填：

```json
{
  "schema_version": "parallel-packages-handoff/1",
  "lane": "P1-OCR-TEXT|P2-OFFICE-TABLE|P3-IDENTITY-AUDIT|P4-CONSUMER-CONTRACT",
  "status": "FROZEN_AWAITING_ROOT_REVIEW|BLOCKED_BY_SCOPE|PARTIAL",
  "baseline_commit": "<派发时 ROOT 写入>",
  "branch": "codex/...",
  "commits": ["<sha>"],
  "changed_paths": ["..."],
  "file_bindings": [{"path": "...", "sha256": "...", "bytes": 0}],
  "interface_versions": {"p1_page_text": "cwp-ocr-page-text/1"},
  "tests": [{"command": "...", "exit_code": 0, "passed": 0, "failed": 0, "skipped": 0,
             "receipt": "relative/path.log", "receipt_sha256": "..."}],
  "red_receipt": {"path": "...", "sha256": "...", "first_failure": "断言摘要，≤300字"},
  "fixtures": [{"path": "...", "sha256": "...", "kind": "synthetic|retained_real_observation"}],
  "not_run": ["..."],
  "known_limits": ["..."],
  "root_integration_steps": ["..."],
  "scope_proof": {"production_writes": 0, "config_writes": 0, "db_writes": 0,
                  "original_reads": 0, "original_writes": 0,
                  "network_calls": 0, "model_calls": 0, "key_reads": 0,
                  "forbidden_paths_touched": []},
  "independent_review": {"reviewer": "not-self", "verdict": "PASS|FAIL",
                         "report": "relative/path.md", "bound_files_sha256": ["..."]}
}
```

`file_bindings` 必须覆盖该卡**每一个**新增/修改文件；`changed_paths` 与之一一对应。不得把自身交付 commit 的 SHA 写进同一 commit 的交接里造成递归——先提交实现，再单独提交交接。

## 9. 独立性规则

1. 四卡代码互不 import；测试互不 import。
2. 共享逻辑只能来自已发布契约；不得在本包内另建"公共工具"再让四卡引用。
3. 若某卡发现必须修改 `document_normalization/__init__.py`、`units.py`、`errors.py`、`limits.py`、`document.py`、`replay.py` 或 `source_catalog/**`：停止并写 `BLOCKED_BY_SCOPE`，不自行扩展写集。
4. 若两张卡同时需要同一路径：后开工者停，报 ROOT 重新分派；不得改写对方文件。

## 10. 验收命令模板

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -B -c "import company_wiki; print(list(company_wiki.__path__))"   # 必须指向本 worktree
python -m pytest <本卡测试目录> -q -p no:cacheprovider
python -m ruff check <本卡新增/修改的 .py>
python -m mypy <本卡新增的生产模块 .py>
```

`pytest` 必须显式给路径，**禁止**裸跑全仓、禁止 `-k` 缩小范围、禁止 `--ignore`。所有日志落在本卡 PWF 目录，命名 `red-*.log` / `green-*.log` / `static-*.log`。
