# P2-OFFICE-TABLE 交接

PLAN_ID=parallel-packages-2026-10-18/P2-OFFICE-TABLE　分支 `codex/p2-office-table-20261018`
基线 `4045787f6bf77722d8125911f3475ecff9bca9b0`
提交：`f8c91996`（实现）+ `9d0b4bb9`（独立审查修复）

## 1. 交付物

- **新增** `src/company_wiki/document_normalization/office_table_structure.py`：纯模块，
  `parse_office_tables(original, *, source_sha256, limits) -> dict` 产出 `cwp-office-table/1`；
  `replay_office_tables(original, structure) -> dict` 重算并逐项比对，任一处不等抛 `ValueError`。
- **新增** `tests/unit/test_p2_office_table/**`：67 个用例 + 8 个合成 OOXML 夹具（含 `sha256.json` 清单）。
- **零改动** `narrative_formats.py`（本卡不需要登记常量，`git status` 为空）；
  `docx_parser.py` 与 `pptx_parser.py` 在 `git diff --stat` 中出现 **0** 次。

冻结接口按卡 §5 逐字实现：`P2_OFFICE_TABLE_SCHEMA="cwp-office-table/1"`、
`P2_OFFICE_TABLE_VERSION="1.0.0"`、`OfficeTableLimits(64, 20000, 200000, 20000)`（frozen dataclass）。

## 2. 关键实现决定（供 ROOT 复核）

1. **locator 只引用、不改写**。DOCX 逐格 locator 与 `docx_parser.table()` 逐字符相同：
   `|t=<表>|r=<w:tr 下标>|c=<w:tc 下标>|p=<可见首段在所有 w:p 子元素中的下标>`。
   `r`/`c` 是 **XML 子元素下标**而非网格坐标（这是既有解析器行为；卡要求结构里的 `row/column`
   是网格坐标，两者在合并表里故意不同）。`parse_docx` 不产 unit 的格：无可见文本或没有 `w:p`
   ⇒ locator `null`；首段空、次段有字 ⇒ `p=1`。PPTX 逐格 locator 与 `pptx_parser` 一致且经实测比对。
2. **`null` 与 `1` 严格区分**。无 `w:gridSpan` ⇒ `column_span=1`（确认为 1）；`gridSpan` 超出
   `w:tblGrid` 列数、PPTX `gridSpan`/`hMerge` 溢出、非正 `gridSpan`、以及 PPTX 合并信号互斥冲突
   ⇒ `column_span/row_span=null`（未知），并记 `p2_span_out_of_grid` / `p2_merge_unresolved`，整表 `partial`。
3. **不猜表头**。DOCX 表头行只来自 `w:trPr/w:tblHeader`（`w:val` 为 false/off/0 视为无）；
   加粗/居中/字号一律不采纳。PPTX 恒 `{"rows": [], "source": "none"}`。
4. **纵向合并**。`w:vMerge` 无 `w:val` 或 `=continue` ⇒ `vertical_continue`（仍占一个网格行位，
   `row_span=1`）；`=restart` ⇒ `vertical_start`；找不到上方起始格 ⇒ `p2_merge_unresolved` 并保留
   `vertical_continue`，**不伪造**起始格。PPTX 只有延续格带 `vMerge="1"`，起始格由其正上方延续格反推。
   DOCX 覆盖格文本为空、PPTX 覆盖格保留原文——这是**有意不对称**，依据是既有解析器行为（见报告 D7）。
5. **分页只认真实标记**。只有单元格**本段自身**的 `w:lastRenderedPageBreak` 记入 `page_break_hints`
   （不穿透嵌套 `w:tbl`）；`w:sectPr` 与页高猜测都不算证据。无标记 ⇒ `status="unknown"` 并记
   `p2_continuation_unknown`。PPTX ⇒ `not_applicable`。`continuation_of` 仅在同一 `package_part` 内、
   前表 `repeated_header=true` 且表头行文本相同时填前表 `table_id`。
6. **限额按产出格计数，不截断半张表**。`work_used` / `max_cells` 计产出格（`gridSpan` 格记 1，
   延续格计格但不计字符）；超 `max_tables`/`max_cells`/`max_text_chars` 时整张丢弃，置 `partial`
   并记 `p2_table_limit`。
7. **依赖缺失如实报**。缺 `python-pptx` 时 PPTX 返回 `status="unavailable"` + `dependency_unavailable`，
   不猜结构、不抛错。DOCX 只用 `zipfile + lxml`，**未引入 `python-docx`**。

## 3. 验收

四条命令全部 exit 0（日志在本目录）：`green-20261018-pathcheck.log`（`company_wiki.__path__`
指向本 worktree）、`green-20261018-pytest.log`（**67 passed**，0 skipped）、
`static-20261018-ruff-mypy.log`（ruff / mypy 均通过）。
RED 收据 `red-20261018-baseline.log`：实现前以"今日 row×cell 行为"为基线跑同一套用例，
**27 failed / 19 passed**，失败均为断言消息（如 `assert [3, 1, 1] == [1, 1, 1]`、
`DID NOT RAISE ValueError`），不是 `ImportError`。

独立审查（非作者）：`review/independent.md`，**VERDICT: PASS**，报告绑定修复后文件 SHA-256。
查出的 7 个缺陷（D1 脚注 `null`↔`""`、D2 PPTX `hMerge` 溢出记成 1、D3 预算按 XML 位置计数、
D4 嵌套表分页线索串表、D5 `gridSpan="0"` 静默变 1 并污染合并链、D6 回放只比 4 个字段、
D7 PPTX 覆盖格文本被清空）已全部修复并加 19 条回归用例锁死；用例数 46 → 67。

## 4. 未做与已知限制

- **未把结构接进生产选择/摘要**：`cwp-office-table/1` 尚未被 `normalize_document`、
  `narrative_formats`、摘要选择或导出消费；接线是 ROOT 的工作。
- **未验证真实 DOCX 续表**：全部结论来自合成包。真实 Word 文件只有在分页预览后才会写
  `w:lastRenderedPageBreak`，因此真实财报的 `continuation.status` 很可能普遍是 `unknown`；
  本卡没有用任何生产原件验证过，也未声称验证过。
- **未做 `du4-table-observation/1` 投影**，未改 `document_understanding/table_measurements/**`。
- `work_used.chars` 只计单元格文本，不含脚注文本（脚注另受 `max_footnote_chars` 约束）。
- `a:tblGrid` 缺失时 `grid.columns=null`，此时无法判定合并是否越界，只能不报（不猜）。
- 非正 `w:gridSpan` 落到 `p2_span_out_of_grid`（卡无规定，属审查裁定）。
- `continuation_of` 判"表头相同"只比单元格文本序列，未比列宽/合并结构。
- 不做数值解析、单位换算、币种推断、财务表分类；不读 PDF、不做 OCR。
- 未读任何生产原件、未联网、未调模型、未读密钥、未写 config/DB/`output/`。

## 5. ROOT 待办（3 项）

1. 决定是否把 `cwp-office-table/1` 投影到 `du4-table-observation/1`（本卡只产出前者）。
2. 在真实 DOCX/PPTX 上核对逐格 locator 与既有 unit 是否仍然一致（本卡只用合成夹具验证过）。
3. 若结构需要进入摘要选择，由 ROOT 在 source owner 内接线，不在本卡。
