# P2-OFFICE-TABLE 交接

PLAN_ID=parallel-packages-2026-10-18/P2-OFFICE-TABLE　分支 `codex/p2-office-table-20261018`
基线 `4045787f6bf77722d8125911f3475ecff9bca9b0`
提交：`f8c91996`（实现）→ `b61ed0c5`（独立审查 #1 修复）→ `46e9052c`（交接）
→ `ac1aa4cb`（真实验证编号修复）→ `c1f2e96c`（真实验证记录）→ `87fd5f82`（删区计数修复）
→ `bde0a685`（QA 标记定位符修复 + 复审附录）

## 1. 交付物

- **新增** `src/company_wiki/document_normalization/office_table_structure.py`：纯模块，
  `parse_office_tables(original, *, source_sha256, limits) -> dict` 产出 `cwp-office-table/1`；
  `replay_office_tables(original, structure) -> dict` 重算并逐项比对，任一处不等抛 `ValueError`。
- **新增** `tests/unit/test_p2_office_table/**`：**70 个用例** + 8 个合成 OOXML 夹具（含 `sha256.json` 清单）。
- **零改动** `narrative_formats.py`（本卡不需要登记常量，`git status` 为空）；
  `docx_parser.py` 与 `pptx_parser.py` 在 `git diff --stat` 中出现 **0** 次。

冻结接口按卡 §5 逐字实现：`P2_OFFICE_TABLE_SCHEMA="cwp-office-table/1"`、
`P2_OFFICE_TABLE_VERSION="1.0.0"`、`OfficeTableLimits(64, 20000, 200000, 20000)`（frozen dataclass）。

## 2. 关键实现决定（供 ROOT 复核）

1. **locator 只引用、不改写**。DOCX 逐格 locator 与 `docx_parser.table()` 逐字符相同：
   `|t=<表>|r=<w:tr 下标>|c=<w:tc 下标>|p=<可见首段下标>`，`r`/`c` 是 **XML 子元素下标**而非网格
   坐标（与结构的 `row/column` 网格坐标故意不同）。`parse_docx` 不产 unit 的格 ⇒ locator `null`；
   首段空、次段有字 ⇒ `p=1`。段落含 QA 标记（`问：`）被 `emit` 切分时 ⇒ 记首段 `|ch=` 后缀
   （`bde0a685`）。表编号 `t=` 复刻解析器遍历：`w:sdt`/`customXml`/`ins`/`moveTo` 经 `sdtContent`
   下降，单元格只认直接 `w:tbl` 子元素，`w:del`/`w:moveFrom` 删区的表以 `None` 占位消耗索引
   （`ac1aa4cb` + `87fd5f82`，两处均由真实/差分验证抓出）。
2. **`null` 与 `1` 严格区分**。无 `w:gridSpan` ⇒ `column_span=1`；`gridSpan` 越界、非正
   `gridSpan`、PPTX 合并互斥冲突 ⇒ `column_span/row_span=null` + `p2_span_out_of_grid`/
   `p2_merge_unresolved` + 整表 `partial`。
3. **不猜表头**。DOCX 表头行只来自 `w:trPr/w:tblHeader`；加粗/居中/字号一律不采纳。
   PPTX 恒 `{"rows": [], "source": "none"}`。
4. **纵向合并**。`w:vMerge` 无 `val`/`=continue` ⇒ `vertical_continue`（占一个网格行位，
   `row_span=1`）；`=restart` ⇒ `vertical_start`；找不到上方起始格 ⇒ 保留 `vertical_continue`
   + `p2_merge_unresolved`，**不伪造**起始格。DOCX 覆盖格文本为空、PPTX 覆盖格保留原文——
   有意不对称，依据既有解析器行为（报告 D7）。
5. **分页只认真实标记**。仅单元格本段的 `w:lastRenderedPageBreak` 记入 `page_break_hints`
   （不穿透嵌套 `w:tbl`）；`w:sectPr`/页高猜测不算证据；无标记 ⇒ `unknown` + `p2_continuation_unknown`。
   PPTX ⇒ `not_applicable`。`continuation_of` 仅在同一 `package_part`、前表 `repeated_header=true`
   且表头行文本相同才填。
6. **限额按产出格计数，不截断半张表**；超限整张丢弃，置 `partial` + `p2_table_limit`。
7. **依赖缺失如实报**。缺 `python-pptx` ⇒ `unavailable` + `dependency_unavailable`，不猜不抛。
   DOCX 只用 `zipfile + lxml`，**未引入 `python-docx`**。

## 3. 验收

四条命令全部 exit 0（日志在本目录）：`green-20261018-pathcheck.log`（指向本 worktree）、
`green-20261018-pytest.log`（**70 passed**，0 skipped）、`static-20261018-ruff-mypy.log`（全过）。
RED 收据 `red-20261018-baseline.log`：实现前以"今日 row×cell 行为"为基线跑同一套用例，
**27 failed / 19 passed**，失败均为断言消息，不是 `ImportError`。

**独立审查**（非作者，`review/independent.md`）：审查 #1 PASS（绑 `b61ed0c5`，查出 D1–D7
七缺陷全修，46→67 用例）；复审 PASS（`RE-REVIEW VERDICT: PASS`，§9，绑最终 SHA）。复审用
32 例差分探针验证编号遍历与解析器 0 分歧，并独立复现真实验证数字。全程共修 **9 个缺陷**：
D1 脚注 `null`↔`""`、D2 PPTX `hMerge` 溢出记成 1、D3 预算按 XML 位置计数、D4 嵌套表分页
线索串表、D5 `gridSpan="0"` 污染合并链、D6 回放只比 4 字段、D7 PPTX 覆盖格文本被清空、
D8 删区表未消耗解析器索引、D9 QA 标记段落 locator 缺 `|ch=` 后缀。每处均有对旧代码红、
对新代码绿的回归用例。

**真实验证**（ROOT 交付后追加；数字以复审 §9 独立复现为准）：语料 190 个唯一真实包
（`companies/` 180 个唯一 DOCX，其中 95 个含表；`docs/…/ci-docx-investigation` 证据 8 个；
`.venv` 模板 2 个；0 PPTX 在 companies），全量解析 0 错误、回放 190/190 通过。
修复前 `body.iter` 编号在 190 包语料上使 **644/2511（25.6%）** 结构 locator 不在
`parse_docx` 输出中；仅 **1 个文件**漂移（阿里巴巴 20190919：iter 34 张 vs 解析器 31 张，
根因 `w:sdt` 包裹嵌套表）。终态 **2519/2519 逐字符一致、0 漂移**（companies 语料 2500/2500）。
解析器独有 2565 个 locator（382 个单元格）全部是同 `t/r/c` 下的后续段落（`p>j`），属设计预期。

## 4. 未做与已知限制

- **未把结构接进生产选择/摘要**：`cwp-office-table/1` 尚未被任何生产路径消费；接线是 ROOT 的工作。
- **真实 DOCX 续表仍未验证**：`w:lastRenderedPageBreak` 只在 Word 分页预览后写入；190 包中
  `continuation.status` 为 `unknown` 154 / `ok` 1 / `not_applicable` 2——**无一例真实
  `repeated_header` 续表**，该路径仍只有合成证据。删区计数修复（`87fd5f82`）在真实语料
  0 触发，属前瞻性修复。
- **真实验证的边界**：只比对了 locator 逐字符一致；34 个文件含合并格（`vertical_continue`
  164 / `vertical_start` 40）未逐一人工核对语义；真实 PPTX 样本 2 个（1 个含表、0 个在
  companies），PPTX 侧仍是合成夹具证据为主。
- **未做 `du4-table-observation/1` 投影**，未改 `document_understanding/table_measurements/**`。
- `work_used.chars` 只计单元格文本（脚注另受 `max_footnote_chars` 约束）；`w:tblGrid`/`a:tblGrid`
  缺失时 `grid.columns=null`，无法判越界只能不报；非正 `w:gridSpan` 落 `p2_span_out_of_grid`
  （卡无规定，审查裁定）；`continuation_of` 的"表头相同"只比单元格文本序列。
- 不做数值解析、单位换算、币种推断、财务表分类；不读 PDF、不做 OCR。真实验证只**读**了原件
  字节（哈希去重后解析，`original_reads=190`），未写任何原件；未联网、未调模型、未读密钥、
  未写 config/DB/`output/`。

## 5. ROOT 待办（2 项）

1. 决定是否把 `cwp-office-table/1` 投影到 `du4-table-observation/1`（本卡只产出前者）。
2. 若结构需进入摘要选择，由 ROOT 在 source owner 内接线，不在本卡。
   （原第 2 项"真实原件核对 locator"已完成：2519/2519 一致；复跑方法见 §3。）
