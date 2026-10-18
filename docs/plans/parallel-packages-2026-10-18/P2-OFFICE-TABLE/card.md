# P2-OFFICE-TABLE：DOCX/PPTX 表格结构与定位回放

状态：READY，2026-10-18。范围是**只读解析 + 纯结构产物**：在不改动既有 unit 与 locator 的前提下，把合并单元格、表头、脚注、分页/续表线索固定成可回放结构。生产接线由 ROOT 做。
PLAN_ID=parallel-packages-2026-10-18/P2-OFFICE-TABLE。

## 1. 真实问题

- `document_normalization/docx_parser.py` 的 `table()` 只按"行 × 单元格 → 每段一个 unit"展开，locator 形如 `cwp-docx-body/1|t=3|r=2|c=1|p=0`。它把首行文字塞进 `table_headers` 元数据，但**没有**读取 `w:gridSpan`、`w:vMerge`、`w:tblHeader`、`w:tblGrid`，也没有读 `word/footnotes.xml`。
- 于是合并单元格在数据里表现为"同一个值重复出现在 r2c1、r2c2"，下游无法区分"照抄两格"与"横向合并"；重复表头行被当成普通数据行；脚注文本整段丢失；表格被分页切断时没有任何线索。
- `document_normalization/pptx_parser.py` 用 `cwp-pptx-shape/2|s=..|p=..|c=r,c|par=i` 记录单元格，但同样不读 `a:tc/@gridSpan`、`@hMerge`、`@vMerge`、`a:tblGrid`。
- 结果：任何"表格结构是否被正确理解"的验收都只能看文字，不能看结构；也不能从结构回放到原字节。

## 2. 目标

1. 新增纯模块 `office_table_structure.py`，从 `original: bytes` 直接解析 DOCX/PPTX 包，产出 `cwp-office-table/1`：表格、行列网格、合并跨度、表头行、脚注、分页/续表线索、逐格 locator。
2. 逐格 locator 复用既有写法，**不新增、不改写**已有 unit 的 locator 字符串；结构产物只引用它们。
3. 提供 `replay_office_tables`：给定原字节 + 结构，重算并逐项比对，任何差异抛带码异常。
4. 全程无 IO（除入参字节）、无网络、无模型；不实例化 python-docx，DOCX 用 `zipfile + lxml`，PPTX 用既有 `python-pptx`（可选依赖，缺失时如实报 `unavailable`）。

## 3. 非目标（明确不做）

- 不改 `docx_parser.py`/`pptx_parser.py` 的任何现有输出、unit 数量、locator、parser 版本；本卡**不要求**这两个文件任何改动。
- 不产出 `du4-table-observation/1`，不改 `document_understanding/table_measurements/**`；投影由 ROOT 决定。
- 不做表头语义判断（不按加粗/居中/字号猜表头）；PPTX 没有 `tblHeader` 属性就是 `none`。
- 不做数值解析、单位换算、币种推断、财务表分类。
- 不读 PDF、不做 OCR（那是 P1 的范围）。
- 不新增 `QualityFlag` 枚举值；不改 `units.py` 里的任何版本常量。

## 4. 独占写集

**新增（本卡独占）**

- `src/company_wiki/document_normalization/office_table_structure.py`
- `src/company_wiki/automation/narrative_formats.py`：**仅可选、仅增量**，只允许追加"office table 结构版本"常量登记（例如 `OFFICE_TABLE_STRUCTURE_VERSIONS = frozenset({"cwp-office-table/1"})` 之类的一行），不得改 `parser_component` 现有分支、不得改任何 parser 版本、不得新增路由。若不需要，保持零改动并在交接里写明。
- `tests/unit/test_p2_office_table/**`（含 `fixtures/**`）
- `docs/plans/parallel-packages-2026-10-18/P2-OFFICE-TABLE/**`

**禁写**

- `src/company_wiki/document_normalization/docx_parser.py`、`pptx_parser.py`、`__init__.py`、`units.py`、`errors.py`、`limits.py`、`document.py`、`replay.py`、`local_ocr.py`、`ocr_composition.py`、`ocr_region_recovery.py`、`isolated_ocr.py`、`pdf_table_observations/**`、`layout_snapshots/**`
- `src/company_wiki/source_catalog/**`（整目录）、`src/company_wiki/document_understanding/**`、`src/company_wiki/parser_adapters/**`
- `tools/**`、`tests/integration/**`
- ROOT 独占清单：`narrative_reading.py`、`narrative_operating_relations.py`、`narrative_antecedent.py`、`operating_states/relations.py`、`operating_states/product_reference.py`、`tests/unit/du11_source_closure/**`、`docs/plans/du11-*/**`、`docs/plans/document-understanding-2026-10-13/**`
- 其余三卡的写集

## 5. 冻结接口

```python
P2_OFFICE_TABLE_SCHEMA = "cwp-office-table/1"
P2_OFFICE_TABLE_VERSION = "1.0.0"

@dataclass(frozen=True)
class OfficeTableLimits:
    max_tables: int = 64
    max_cells: int = 20000
    max_text_chars: int = 200000
    max_footnote_chars: int = 20000

def parse_office_tables(
    original: bytes,
    *,
    source_sha256: str,
    limits: OfficeTableLimits = OfficeTableLimits(),
) -> dict[str, object]: ...

def replay_office_tables(
    original: bytes,
    structure: Mapping[str, object],
) -> dict[str, object]: ...
```

`parse_office_tables` 必须校验 `sha256(original) == source_sha256`，不等抛 `ValueError("source_sha256 mismatch")`。`format` 由 ZIP 内是否存在 `word/document.xml` / `ppt/presentation.xml` 判定，都不是则抛 `ValueError("unsupported_office_format")`。

### 5.1 输出（`cwp-office-table/1`）

| 字段 | 类型 | 语义 |
|---|---|---|
| `schema_version` | str | `cwp-office-table/1` |
| `format` | str | `docx|pptx` |
| `source_sha256` | str | 原字节哈希 |
| `parser` | `{name,version}` | `{"cwp_office_table_structure","1.0.0"}` |
| `tables` | list | 见 5.2 |
| `structure_sha256` | str | 对 `tables` 的 canonical JSON 计算，不含本字段 |
| `status` | str | `ok|partial|unavailable` |
| `diagnostics` | list | `[{code, table_id, detail}]` |
| `work_used` | `{tables,cells,chars}` | 实际处理量 |

### 5.2 单表

| 字段 | 类型 | 语义 |
|---|---|---|
| `table_id` | str | `"tbl-0"`…，按包内出现顺序，0 起 |
| `package_part` | str | `word/document.xml` 或 `ppt/slides/slideN.xml` |
| `native_index` | int | 同 `package_part` 内第几个表，0 起 |
| `grid` | `{rows:int, columns:int}` | `columns` 来自 `w:tblGrid`/`a:tblGrid`；缺失时 `null` |
| `column_widths` | `list[int]|null` | 原始单位（DOCX twips / PPTX EMU），不换算 |
| `header` | `{rows:list[int], source:str}` | `source∈{tblHeader, none}`；PPTX 恒 `none` |
| `cells` | list | 见 5.3 |
| `footnotes` | list | `[{footnote_id, text, text_refs}]`；无脚注 part 为 `[]` |
| `continuation` | `{page_break_hints, repeated_header, continuation_of, status}` | 见 5.4 |
| `diagnostics` | list | 该表专属诊断 |

### 5.3 单元格

```json
{"cell_id":"r2c1","row":2,"column":1,
 "row_span":1,"column_span":2,
 "merge":"none|horizontal|vertical_start|vertical_continue|both",
 "locator":"cwp-docx-body/1|t=0|r=2|c=1|p=0",
 "text_refs":[{"unit_id":"...","char_start":0,"char_end":12}],
 "footnote_refs":[{"footnote_id":"3","text":"..."}],
 "text":"<该格首个可见段落原文>"}
```

- `row/column` 为**网格坐标**（0 起），不是 XML 子元素下标；合并被覆盖的格子不出现在 `cells` 里，由 `row_span/column_span` 表达。
- `locator` 必须与既有解析器对同一格产生的 locator 逐字符相同；无法产生（例如空单元格无段落）时为 `null`。
- `text_refs` 由调用方后续用 `bind_office_table_units` 填充；本函数返回时可为 `[]`。
- `text` 只做 NFC + 去首尾空白，不合并跨格文字、不补标点。

**合并判定（必须按此实现）**

1. DOCX 横向：`w:tcPr/w:gridSpan/@w:val` → `column_span`；无该元素 → `1`（确认为 1，不是 `null`）。
2. DOCX 纵向：`w:tcPr/w:vMerge` 无 `w:val` 或 `w:val="continue"` → 紧邻上方同列的 `vertical_start` 格继续，本格 `merge="vertical_continue"` 且仍占一个网格行位；`w:val="restart"` → `vertical_start`。
3. PPTX：`a:tc/@gridSpan` → `column_span`；`@hMerge="1"` → 横向继续；`@vMerge="1"` → 纵向继续；三者互斥冲突时记 `p2_merge_unresolved`，该格 `merge="none"` 且 `column_span/row_span=null`（未知，不是 1）。
4. `gridSpan` 使占用超出 `grid.columns` → `p2_span_out_of_grid`，`column_span=null`，整表 `status="partial"`。
5. 纵向合并找不到上方的 `vertical_start`（例如表格起始行就是 continue）→ `p2_merge_unresolved`，`merge="vertical_continue"` 保留原样，不伪造起始格。

### 5.4 续表

- DOCX：单元格段落内的 `w:lastRenderedPageBreak` 记为 `page_break_hints`（该格的 `cell_id`，按出现顺序）。同一表在 hint 之后仍继续、且 `header.rows` 非空 → `repeated_header=true`；有 hint 但无重复表头 → `repeated_header=false`、`continuation_of=null`、`status="unknown"`。
- 无 `w:lastRenderedPageBreak`（很常见，取决于是否在 Word 里分页预览过）→ `status="unknown"`。**不得**把 `w:sectPr` 或猜测的页高当分页证据。
- PPTX：无页面概念 → `status="not_applicable"`、`page_break_hints=[]`。
- `continuation_of` 只在"同一 `package_part` 内，前一张表以 `repeated_header=true` 结束且本表以相同表头行开头"时填前表 `table_id`，否则 `null`。

### 5.5 脚注

- DOCX：读 `word/footnotes.xml`，`w:footnote/@w:id` → 文本；单元格段落里 `w:footnoteReference/@w:id` → `footnote_refs`。
- part 不存在 → `footnotes=[]` + `p2_footnote_unresolved`（`detail="part_absent"`，仍 `status` 不变）。
- id 存在但文本取不到 → `p2_footnote_unresolved`，`text=null`，**不编造**。
- PPTX：`footnotes=[]`，`not_applicable`。

**回放** `replay_office_tables`：重算 `tables`，比对 `structure_sha256` 与逐格 `locator`/`merge`/`row_span`/`column_span`。任一不等抛 `ValueError`，消息形如 `"replay mismatch: tbl-0 r2c1 column_span expected 2 observed null"`。接受的结构必须 `schema_version` 精确匹配，否则 `ValueError("unsupported structure version")`。

## 6. TDD 要求

**A：真实 RED（≥16 用例，实现前失败且是语义失败）**

- DOCX 2×2 含 `gridSpan=2` 的单元格：现在会被读成两格 → 结构必须是 1 格 + `column_span=2`。
- DOCX `vMerge restart/continue` 三行：必须 `vertical_start` + 两个 `vertical_continue`，且 `cells` 只有起始格带 `text`。
- 起始行就是 `vMerge continue` → `p2_merge_unresolved`，不得生成伪起始格。
- `gridSpan=5` 而 `tblGrid` 只有 3 列 → `p2_span_out_of_grid`，`column_span=null`。
- `w:tblHeader` 表头行 → `header={rows:[0],source:"tblHeader"}`；无该元素 → `source:"none"`（不得按加粗猜）。
- 表格中间 `w:lastRenderedPageBreak` + 重复表头 → `repeated_header=true`、`continuation_of` 指前表。
- 无 `lastRenderedPageBreak` → `continuation.status="unknown"`。
- 脚注：引用 id 3 且 `footnotes.xml` 有 id 3 → 文本绑定；缺 part → `p2_footnote_unresolved` 且 `text=null`。
- PPTX 表含 `hMerge` → 横向合并；含 `vMerge` → 纵向；两者同格 → `p2_merge_unresolved`。
- PPTX 表 → `continuation.status="not_applicable"`。
- locator 一致性：DOCX 结构与 `parse_docx` 对同一格产生的 locator 逐字符相等（用真实最小 DOCX 夹具跑一次 `parse_docx` 对照，不修改它）。
- 超 `max_tables`/`max_cells`/`max_text_chars` → `partial` + `p2_table_limit`，不截断半张表；非 ZIP/加密/缺 `word/document.xml`、`sha256` 不符 → `ValueError`。
- 回放：结构被改一个 `column_span` → `ValueError`；原样重放 → 通过且 `structure_sha256` 不变。
- 确定性：同输入两次 `structure_sha256` 相同；`original` 与 `limits` 不被修改。

**B：实现 + 集中 GREEN**；**C：静态检查 + 交接**。

夹具：合成最小 DOCX/PPTX ZIP（每个 ≤ 128 KiB），由测试内 `zipfile` 生成并保存到 `fixtures/**` 与其 `sha256` 清单；不得从生产目录复制真实材料。

禁止：删用例、`skip`、用 `try/except` 吞掉 `ValueError`、把 `null` 断言改成 `1`。

## 7. 验收命令与完成定义

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -B -c "import company_wiki; print(list(company_wiki.__path__))"
python -m pytest tests/unit/test_p2_office_table -q -p no:cacheprovider
python -m ruff check src/company_wiki/document_normalization/office_table_structure.py tests/unit/test_p2_office_table
python -m mypy src/company_wiki/document_normalization/office_table_structure.py
```

**完成定义**

1. 四条命令 exit 0；`python-docx` 未新增依赖（DOCX 用 `zipfile + lxml`，`lxml` 已是既有依赖）。
2. ≥16 用例全绿无跳过；RED/GREEN 日志在本卡目录。
3. `docx_parser.py`、`pptx_parser.py` 在 `git diff --stat` 中出现次数为 **0**。
4. `narrative_formats.py` 若被修改，diff 只有常量登记且交接列出 before/after；否则为 0 改动并写明。
5. 回放用例覆盖改字段与逐字节原样两种。
6. 独立审查 PASS 且绑定最终 SHA。
7. 写明"未把结构接进生产选择/摘要；未验证真实 DOCX 续表"。

## 8. 资源与安全边界

- 不读任何生产原件/原文；只解析测试内生成的合成 OOXML 包。
- 不联网、不调模型、不读密钥；不写 config/DB/`output/`/gold；不新增人工许可（`OfficeTableLimits` 只是调用内限额）。
- 单次解析内存上限由 `max_cells/max_text_chars` 约束，超限返回 `partial`；测试用 `tmp_path` 解包并清理。

## 9. 交接格式

`handoff.md` ≤80 行四段式。`handoff.json` 在 INTERFACES 第 8 节外壳上补充：

```json
{
  "lane": "P2-OFFICE-TABLE",
  "interface_versions": {"office_table": "cwp-office-table/1"},
  "locator_compatibility": {
    "docx": "cwp-docx-body/1|t=<i>|r=<row>|c=<col>|p=<para>",
    "pptx": "cwp-pptx-shape/2|s=<slide>|p=<shape path>|c=<row>,<col>|par=<i>"
  },
  "known_limits": ["PPTX 无表头属性", "DOCX 分页仅在 lastRenderedPageBreak 存在时可见"],
  "root_integration_steps": [
    "决定是否把 cwp-office-table/1 投影到 du4-table-observation/1",
    "在真实 DOCX/PPTX 回放时核对单元 locator 与既有解析器一致",
    "若需进入摘要选择，由 ROOT 在 source owner 内接线，不在本卡"
  ]
}
```

## 10. 独立审查要求

- 审查者 ≠ 作者、≠ ROOT。重点：合并语义是否与 OOXML 规范一致；`null` 与 `1` 是否被混用；是否用启发式猜表头；是否破坏既有 locator；回放是否真能发现差异（要求审查者手工改一个字段验证）；诊断码是否落在 INTERFACES 词表内。
- 发现项修完后对最终 SHA 复审；旧审查结论不得签新代码。报告写本卡目录 `review/independent.md`。
