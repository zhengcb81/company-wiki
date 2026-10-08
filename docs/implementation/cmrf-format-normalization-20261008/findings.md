# R6-FORMAT Findings

## 实测根因（卡片口径 + 本线核实）

1. **Worker 格式路由拒绝**：`src/company_wiki/automation/narrative_select.py:300` 中
   `if payload.source_ref.mime_type != "application/pdf":` 直接跳过非 PDF 来源。SEC HTML
   (`text/html`) 与 PPTX 字节虽完整可读，但 canonical Worker 没有任何解析路径；研究者侧
   BS4/看图是临时人工行为，不是 CWP 能力。MAIN 负责接线；本线只提供纯解析与回放。
2. **放开 MIME 不够**：HTML 有隐藏祖先/inline XBRL ix:hidden、父子节点重复计数、
   导航/脚注混杂；PPTX 有整页图片、notes 混入正文、chart/SmartArt 非图片对象、
   媒体关系损坏。都需要结构化处理 + 资源上限 + 版本化回放，不能当纯文本抽取。

## 既有接口事实（只读核实）

- `NarrativeUnit`（`source_catalog/narrative_document.py:16`）：`unit_id` 必须以
  `urn:company-wiki:narrative-unit:sha256:` 开头；raw_text 非空、去首尾空白、NFC；
  metadata 为 frozen mapping。`to_evidence_span` 产出 `EvidenceSpan`（ParseStatus.PARSED），
  locator 由 `EvidenceCoordinates.locator()` 派生（v1 结构串）。
- `DocumentStructure.coverage_complete`：errors/opaque_pages/deferred_table_pages 非空即
  False；page_count 非零看 pages_read==page_count，否则看 line_count>0。HTML 用
  line_count 表达有效块计数；PPTX 用 page_count/pages_read/opaque_pages。
- `EvidenceCoordinates`：page_number≥1；paragraph_index≥0；row/column 需要同时给
  table_index；paragraph 与 table 互斥。现有 PDF 解析约定：page 1-based，
  table/row/column 0-based（`narrative_evidence.py:_emit_pdf_row`）。
- `QualityFlag` 现有枚举（`source_contract/evidence_span.py:45`）已够用：PARSER_WARNING、
  LAYOUT_AMBIGUOUS、TABLE_STRUCTURE_AMBIGUOUS、ENCODING_REPAIRED、UNSUPPORTED_FORMAT、
  PASSWORD_PROTECTED、TRUNCATED、EMPTY_OUTPUT 等；本线不新增枚举。
- 回放参照 `narrative_replay.py`：先验 SHA、单 parser 版本、roundtrip key
  (locator, text_sha, role, kind)。本线 replay_unit 语义相同但入口为单 unit + bytes。
- source_reader（`source_catalog/source_reader.py`）filing_reuse 只读，返回内存 bytes，
  不写 DB/receipt 文件；可安全用于真实原件定位。

## 真实原件登记（先验 SHA，均只读）

| 格式 | 路径 | 字节 | SHA-256 |
|---|---|---|---|
| SEC inline-XBRL HTML | `companies/微软/raw/financial_reports/annual/微软_10-K_2025.htm`（canonical CWP，root=company_raw） | 8,158,067 | `99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe` |
| 图片型 PPTX | `revenue-forecast/output/cross-market-rf-e2e-2026-10-08/objects/c0/c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`（retained_object） | 4,016,522 | `c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4` |

两份与 `delivery_archive_index.json` artifacts 登记一致（US-MSFT/fy2025_verified_raw.html、
US-MSFT/fy2027_segments_metrics.pptx）。旧 TEMP 根 `C:\...\Temp\cwp-rf-e2e-20261008` 已删除，
不再引用。

## 环境

- bs4 4.14.3 / lxml 6.1.1 / python-pptx 1.0.2 已安装且在 requirements.txt；本线零新依赖。
- tests 根 conftest 注入 `src` 到 sys.path，并施 socket 封禁（COMPANY_WIKI_NETWORK=blocked），
  与本线无网络要求一致。pytest 9.1.1。
- HTML 解析器选 stdlib `html.parser`（bs4 backend）：不自动插入 tbody（影响 DOM 路径稳定）、
  纯 Python 跨机一致；lxml 仅用于 python-pptx 内部与潜在 XML 读。

## 风险与开放项

- 8MB SEC HTML 用 html.parser 的耗时待测（大节点计时记录）；若不可接受需评估 lxml 并在
  parser_version 内固定其路径语义，交接注明。
- PPTX 图片页无法读取正文：诚实 partial（opaque_pages + OpaqueAsset），不伪称识图；
  OCR/视觉属 MAIN 的模型预算范围。
- HTML 财务表/经营表判别是启发式标志（financial_table/unknown + 依据），选择权留给 MAIN。

## 实现期发现(2026-10-08 收尾)

1. **所有权双计 bug(已修)**:第一版把后代 owner 的文本聚合进祖先 unit(真实 10-K
   9,614 units 里大量重复)。修正为单次有序扫描:字符串归最近 block owner,
   owner 后代独立成 unit。修后 5,215 units(1,316 段 + 3,899 cell),
   同文本多位置仍为多 unit。
2. **SEC 表格 cell 内是 `<p>` 包装**:严格最近-owner 语义会把 cell 文本归 p,
   表格失去稳定 table/row/column 身份。修正:`td/th` 走 cell 模式——cell 内块
   (p/div/li)皆为格式化包装,文本并入 cell unit;嵌套 table 的 cell 自成单元。
3. **python-pptx 对 external 关系访问 `target_partname` 抛 ValueError**(不返回
   None):防御式读取后按 external 具名缺口处理,不 fetch。
4. **`_cell_coordinates` O(n²)**:每个 cell 重新 find_all 全表(17.9s);
   表/行级缓存后 4–5s。
5. **空/非 HTML 输入**:无 html 根 → `no_html_root` error;无可见块 →
   `no_visible_text_blocks`;两者都保证 coverage False,不会"空成功"。
6. 真实 PPTX 是 22 页每页 1 张 PICTURE 的纯图 deck;python-pptx 的
   `pptx.Package` 不存在,入口是 `pptx.Presentation`。
7. tiny PNG fixture 必须经 PIL 生成(手拼 IHDR/IDAT 的 PNG python-pptx/PIL 拒识)。

## 最终数字(全部实测,报告见 real_originals_report.json)

- HTML(微软 10-K FY2025, 8,158,067 B): 5,215 units;85 表(69 financial /
  16 unknown;cell 计 3,382/517);coverage True;0 errors;parse 5.1s;
  逐类回放 ok(paragraph/cell)。
- PPTX(MSFT FY2027 segments, 4,016,522 B): 22/22 slides 读;0 文本 unit;
  22 opaque pages + 22 image assets;media 3,954,484 B;coverage False(诚实
  partial);parse 0.5s。
- 测试:64 passed / 0 failed;RED(基线)exit=4。
