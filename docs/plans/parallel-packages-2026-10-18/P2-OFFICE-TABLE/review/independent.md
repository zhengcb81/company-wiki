# P2-OFFICE-TABLE 独立审查报告

审查者：独立审查 agent（**非作者、非 ROOT**）。作者在同一 worktree 内实现并交接；本报告作者未参与该卡实现，仅依据 `card.md`、`INTERFACES.md`、`README.md` 与既有 `docx_parser.py` / `pptx_parser.py` 判定。
审查日期：2026-10-18。
Worktree：`C:\Users\郑曾波\Projects\company-wiki-p2-office-table`
Branch：`codex/p2-office-table-20261018`
Baseline：`4045787f6bf77722d8125911f3475ecff9bca9b0`
**被审实现 commit：`f8c91996cb12286d527c95be240b0ada3423f560`**
本报告绑定的是**审查后修复完成的工作树**（未提交，交作者提交）；SHA-256 见文末。

审查期间作者仍在同一文件内改动（`replay_office_tables` 的自哈希兜底），一度造成写冲突。经与作者/派发方确认后，作者停止编辑，本审查者成为唯一写入者，对 `f8c91996` 的缺陷自行修复，作者仅读。

---

## 0. 结论速览

`f8c91996` 在**合并语义主干、locator 保真、表头不猜、诊断码词表、限额不截半表、确定性**上是对的，但存在 **7 个真实缺陷**，其中 3 个属"把未知写成已知"（`null` 与 `""`/`1` 混用）这一类——正是卡 §10 点名最可能出错的一类。缺陷已全部在工作树内修复，并新增 19 条回归用例锁死。修复后四条验收命令全部 exit 0。

---

## 1. 逐项判定（对照审查任务 1–8）

| # | 焦点 | 判定 | 说明 |
|---|---|---|---|
| 1 | 合并语义与 OOXML 规范一致 | **修复后通过** | DOCX `gridSpan` / `vMerge`(无 val、`continue`、`restart`) 正确；PPTX `gridSpan`/`hMerge`/`vMerge` 与互斥冲突正确。发现 2 处偏离（缺陷 D2、D5）。 |
| 2 | `null` 与 `1` 是否混用 | **修复后通过（曾有 3 处缺陷）** | D1 脚注 `""` 冒充已知；D2 `hMerge` 溢出把未知写成 `1`；D5 非法 `gridSpan` 被 `max(1, span)` 静默改成 1 并破坏合并链。 |
| 3 | 是否用格式猜表头 | **通过（零缺陷）** | 加粗+居中首行仍为 `{"rows":[],"source":"none"}`；仅 `w:trPr/w:tblHeader` 生效；PPTX 恒 `{"rows":[],"source":"none"}`。无任何 heuristic。 |
| 4 | 是否破坏既有 locator | **通过（零缺陷）** | 6 个夹具上结构与 `parse_docx` 产出的 locator 集合**逐字符相等**（不只子集）；`p=1` 位移、空段落 `null`、仅 `lastRenderedPageBreak` 单元格 `null` 均正确。PPTX 与 `parse_pptx` 一致。 |
| 5 | 回放是否真能发现差异 | **修复后通过（曾有缺陷 D6）** | 手工改 `column_span` 可检出；但 `f8c91996` 对 `header`/`grid`/`footnotes`/`continuation`/`text` 的篡改**完全检不出**（旧结构被重算结果覆盖后原样返回）。已改为逐字段比对 + 兜底后置。 |
| 6 | 诊断码是否在 INTERFACES 词表内 | **通过（零缺陷）** | 仅出现 `p2_span_out_of_grid`、`p2_merge_unresolved`、`p2_footnote_unresolved`、`p2_continuation_unknown`、`p2_table_limit`、`dependency_unavailable`；顶层 status 仅 `ok`/`partial`/`unavailable`。 |
| 7 | 有界工作，不截半表 | **修复后通过（曾有缺陷 D3）** | 超限一律 `partial` + `p2_table_limit`，且从不输出半张表；但 `work_used`/`max_cells` 曾按 XML 位置计数（缺陷 D3）。 |
| 8 | 确定性、输入不被改 | **通过（零缺陷）** | 同输入两次 `structure_sha256` 相同；`original` 字节与 `limits` 对象均未被修改。 |

结构诚实性专项（段落级 locator、仅分页符单元格、无 `w:p` 单元格、首段空白后段有字）全部**通过**，见 §4。
续表、脚注、依赖卫生三项：脚注有缺陷（D1），其余通过，见 §4。

---

## 2. 缺陷明细（file:line 指 `f8c91996`）

### D1 — 脚注"存在但无文本"被写成 `""`，且不报诊断（`null`↔`""` 混用）

`office_table_structure.py:402-415`（`_docx_footnote_texts`）
`w:footnote/@w:id` 存在但正文为空时，实现存入 `""`，随后 `:503` 判定"命中"，于是 `footnote_refs[].text == ""`、`footnotes[].text == ""`，且**不产生** `p2_footnote_unresolved`。
卡 §5.5 明文："id 存在但文本取不到 → `p2_footnote_unresolved`，`text=null`，**不编造**"；INTERFACES §1 明文 `""` 不得代替未知。
实测（修复前）：`footnote_refs == [{'footnote_id':'3','text':''}]`，诊断只有 `p2_continuation_unknown`。
**改法**：只登记真正有可见文本的脚注；空文本与缺失 id 同路径 → `text=null` + `p2_footnote_unresolved`。顺带跳过 `w:type="separator"/"continuationSeparator"/"continuationNotice"`（这些是版式分隔符，不是内容）。

### D2 — PPTX `@hMerge="1"` 越过 `a:tblGrid` 时报 `column_span=1` 且整表 `ok`

`office_table_structure.py:857-860`（`hMerge` 分支无条件 `column_span = 1`）
`@gridSpan` 越界有 `p2_span_out_of_grid` + `column_span=None`，但 `hMerge` 溢出落入同一句规则（卡 §5.3 规则 3、4 并列）却被写成"确认为 1"。同类问题：`@gridSpan` 越界时 `column_span=NULL` 但整体 status 仍 `ok`（DOCX 同情形为 `partial`）。
实测（修复前）：`r0c2 column_span=1, merge="horizontal", status="ok"`，无任何诊断。
**改法**：新增 `_pptx_hmerge_overflows`——本行内找不到仍覆盖该列的 origin，或该位置本身已越出 `a:tblGrid`，即判溢出 → `column_span=None` + `p2_span_out_of_grid`，整表 `partial`。（PPTX 的 status 升级原代码已具备，只是此前该分支根本不发诊断。）

### D3 — `work_used` 与 `max_cells` 按 XML 位置计数，不按产出格

`office_table_structure.py:633-641`（`_docx_table_work`）+ `:391-395`
卡 §5.1 定义 `work_used` 为"实际处理量"；一个 `gridSpan=2` 的格在 `cells` 里是 1 格，预算却记 2，预算与它描述的结构自相矛盾。纵向合并延续格也不该计文本字符。
**改法**：DOCX 一律按**产出格**计数（`gridSpan` 格记 1；`vMerge=continue` 格计格但计 0 字符），使"整表保留或整表丢弃"在两种计数下都成立。实测 `max_cells=2` 现保留 `[1,2]` 结构而不是 `[1]`。

### D4 — 嵌套表格内的 `w:lastRenderedPageBreak` 被算成外层表的 hint

`office_table_structure.py:539-542`（`paragraph_node.findall(".//" + W + LAST_RENDERED_PAGE_BREAK)`）
`.//` 会穿透嵌套 `w:tbl`，把子表的换页线索记到外层表的 `cell_id` 上，直接伪造 `repeated_header`/续表关系。卡 §5.4 的 hint 是"该格的 `cell_id`"。
**改法**：新增 `_paragraph_has_page_break`，只遍历该段落自身的行内包裹（`w:r`/超链接等），不进入嵌套 `w:tbl`。

### D5 — `w:gridSpan w:val="0"` 被 `max(1, span)` 静默改成 1，并破坏合并链

`office_table_structure.py:448`
卡 §5.3 没有规定非正 `gridSpan`。`max(1, grid_span)` 既把它写成"确认为 1"，又让 `open_vertical.pop(...)` 把一个本来还开着的 `vMerge` 链**关掉**（状态被污染，后续 continue 会误报/误判）。
**改法**（取值歧义的裁定，已写入模块 docstring）：非正 `gridSpan` 视为"宽度未知" → `column_span=None` + `p2_span_out_of_grid` + 整表 `partial`；它仍占 1 个网格位置（`occupied=1`），因此**不推进也不关闭**上方合并链。选择 `p2_span_out_of_grid` 而非 `p2_merge_unresolved` 的理由：这是"宽度不在合法域"，不是"合并链断裂"；且与越界 `gridSpan` 同码，下游处理一致。

### D6 — 回放只比 4 个字段，其余篡改被静默覆盖（回放不完整）

`office_table_structure.py:1039-1082`（`for field in ("locator","merge","row_span","column_span")`）
手工篡改 `header`/`grid`/`column_widths`/`package_part`/`native_index`/`footnotes`/`continuation`/`text`/`text_refs`/`footnote_refs`/`cell_id` 时，回放**不报错**，而是返回 `recomputed`——调用方拿到的是正确结构，篡改被悄悄吞掉，`f8c91996` 因此无法完成卡 §5.5 的"任何差异抛异常"。
实测（修复前）：4 类篡改全部 `NOT DETECTED`。
**改法**：按卡 §5.5 顺序**逐字段显式比对**（表级 8 个字段 + 格级 9 个字段 + `table_id`/`cell_id`/`cells` 长度），消息严格用卡定格式 `<table_id> <cell_id> <field> expected <v> observed <v>`；作者/前序补丁的"声明哈希 vs 所供表"自哈希兜底**后置为最后一道**，因此已知字段永远是精确消息胜出，兜底只接住本版本不认识的键。

### D7 — PPTX `@vMerge="1"` 单元格文本被清空，与既有 `pptx_parser` 不一致

`office_table_structure.py:765`（`text = _pptx_cell_text(cell) if v_merge != "1" else ""`）
看起来像是照搬 DOCX"被覆盖格无文本"的语义，但 **PresentationML 不同**：`a:tc` 仍存文本，`pptx_parser` 也会为它产出 unit。
实测（`parse_pptx` 直跑该夹具）：
```
cwp-pptx-shape/2|s=1|p=0|c=1,0 -> 幽灵文本
```
而结构里同 locator 的 `text` 是 `""`。卡要求 `text` 为该格首个可见段落原文，且 locator 与既有解析器一致——清空文本等于让结构与 locator 的来源自相矛盾。
**改法**：保留文本，覆盖关系仅由 `merge` 表达；DOCX/PPTX 的这个不对称作为显式决定写进测试 `test_pptx_vertical_continuation_keeps_the_parser_text_of_its_cell`。

---

## 3. 修复后实测的回放消息（卡 §5.5 要求的原样）

被篡改结构：`tests/unit/test_p2_office_table` 夹具，`row0 = [a][b](tblHeader)`，`row1 = [c grid_span=2]`，`r1c0` 原 `column_span=2`。

**格级字段（手工把 `r1c0` 的 `column_span` 改成 1）：**
```
replay mismatch: tbl-0 r1c0 column_span expected 1 observed 2
```

**表级字段（手工把 `header` 改成 `{"rows":[1],"source":"tblHeader"}`）：**
```
replay mismatch: tbl-0 header expected {"rows":[1],"source":"tblHeader"} observed {"rows":[0],"source":"tblHeader"}
```

**未知→已知的典型（越界格 `column_span` 原为 `null`，改成 1）：**
```
replay mismatch: tbl-0 r0c0 column_span expected 1 observed null
```

**逐字节原样重放：** 通过，且 `structure_sha256` 不变（实测 `6997c2f0…690012`，两次相等；`replay == structure`）。

---

## 4. 结构诚实性 / 续表 / 脚注 / 依赖卫生实测

- 仅 `w:lastRenderedPageBreak` 的单元格：`locator=null` 且计入 `continuation.page_break_hints` ✅
- 无 `w:p` 的单元格：`locator=null`、`text=""` ✅
- 首段空白、后段有字：`locator=…|p=1`（不是 `p=0`）✅
- `w:sectPr` / 猜测页高**未**被当作分页证据；无 `w:lastRenderedPageBreak` → `status="unknown"` + `p2_continuation_unknown` ✅
- PPTX → `status="not_applicable"`、`page_break_hints=[]`、`footnotes=[]` ✅
- `continuation_of` 仅在同一 `package_part`、前表 `repeated_header=true` 且表头行文本相同才填，否则 `null` ✅
- 脚注三种情形（修复后）：

| 情形 | `footnote_refs` | `footnotes` | 诊断 detail | status |
|---|---|---|---|---|
| 缺 part | `[{'footnote_id':'3','text':None}]` | `[]` | `part_absent` | `ok` |
| id 不在 part 内 | 同上 | `[]` | `footnote 3 not found` | `ok` |
| id 在但无文本 | 同上 | `[]` | `footnote 3 not found` | `ok` |

- 依赖卫生：模块内 **0** 处 `import docx`/`python-docx`、0 处 `requests`/`urllib`/`socket`/`httpx`、0 处 `Path(`；唯一 `open(` 是 `ZipFile.open`（对 `io.BytesIO` 的内存包），无文件系统 IO。DOCX 走 `zipfile + lxml` ✅

---

## 5. 测试诚实性核查

- 无删除用例、无 `pytest.mark.skip`/`xfail`、无用 `try/except` 吞 `ValueError`（`Select-String` 扫描 0 命中）。
- 未把 `null` 断言放宽成 `1`；新增用例全部断言 `None`。
- 作者新增的两条回放用例（`test_replay_detects_a_changed_text_even_outside_the_compared_field_set`、`test_replay_charges_the_declared_hash_against_the_supplied_tables`）**保留未删未改**；第二条在逐字段比对下已冗余（字段比对先命中），但按指示保留作为兜底回归。
- `tests/unit/test_p2_office_table/fixtures/**` 字节**未改动**（manifest 未变，`test_committed_fixtures_equal_freshly_generated_bytes` 绿）。
- **唯一一处修正了我自己写的用例**：我最初写的 `test_pptx_vertical_continuation_never_reports_the_hidden_cell_text` 断言 PPTX 覆盖格文本应为 `""`。直跑 `parse_pptx` 证明既有解析器对该格**产出** `幽灵文本`，故该断言与卡 §5.3"text 为该格首个可见段落原文"+ locator 一致性冲突——是用例错、实现对。已改写为 `…keeps_the_parser_text_of_its_cell`，并**加强**为同时比对 `parse_pptx` 同 locator 的原文（见 D7）。这不是放宽断言：它把一条错误期望换成了可执行的一致性证明。

## 6. 四条验收命令（修复后）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `python -B -c "import company_wiki; print(list(company_wiki.__path__))"` | 0 | 指向本 worktree `…\company-wiki-p2-office-table\src\company_wiki` |
| `python -m pytest tests/unit/test_p2_office_table -q -p no:cacheprovider` | 0 | **67 passed**，0 failed，0 skipped |
| `python -m ruff check src/company_wiki/document_normalization/office_table_structure.py tests/unit/test_p2_office_table` | 0 | All checks passed! |
| `python -m mypy src/company_wiki/document_normalization/office_table_structure.py` | 0 | Success: no issues found in 1 source file |

用例数逐文件核对（实测 `--collect-only`）：

| 文件 | `f8c91996` | 修复后 |
|---|---|---|
| `test_boundaries.py` | 6 | 6 |
| `test_docx_footnotes.py` | 3 | 3 |
| `test_docx_structure.py` | 15 | 15 |
| `test_fixtures_manifest.py` | 2 | 2 |
| `test_locator_compatibility.py` | 5 | 5 |
| `test_pptx_structure.py` | 6 | 6 |
| `test_replay_and_determinism.py` | 9 | 11（作者 +2） |
| `test_review_regressions.py`（本审查新增） | — | 19 |
| **合计** | **46** | **67** |

**RED 证据**：把 `office_table_structure.py` 回退到 `f8c91996`（`git stash`）后单跑新的 `test_review_regressions.py` = **13 failed, 6 passed**；失败全部是语义断言（例如 `assert [{'footnote_id':'3','text':''}] == [{'footnote_id':'3','text':None}]`、`assert 'p2_span_out_of_grid' in [...]`、`Regex pattern did not match … Expected 'header'`），**没有一条是 ImportError**。恢复修复版后该文件 19 passed，且恢复后的文件哈希与表中一致（`223A8869…AA20942`），确认 stash/restore 未污染工作树。

## 7. 本审查改动的文件与 SHA-256（`Get-FileHash -Algorithm SHA256`）

| 文件 | SHA-256（修复后） | `f8c91996` 原值 |
|---|---|---|
| `src/company_wiki/document_normalization/office_table_structure.py` | `223A886999BDB429B17F7AF03F9B0D4145B7F69BB8C2C230BD8B8D150AA20942` | `CAB0322F5F584B31BA926ADF6A72C20BE311528591AFF9C1A80F3D6D36202EAE` |
| `tests/unit/test_p2_office_table/test_replay_and_determinism.py` | `27E5434835C5C3D283E7FE184B0B78E9CF193209D0A958CBFCBCC2377A5397EC` | `E2EF0569266C4B3C8958377D83A1B3C6B954ADF7F1369E43799B637C7AA6F5B0` |
| `tests/unit/test_p2_office_table/test_review_regressions.py`（新增） | `AF65300F42357BD27EB176EA5801714A429B4A56C56F683412567CC9E4EC1A77` | 不存在 |

未改动的旁证：`tests/unit/test_p2_office_table/fixtures/sha256.json` = `EB2A6547E845892D223DA3770F15245F1AC027DD307285F2220146160C3A3B50`（与 commit 一致，夹具未被重写）。

`git status` 仅上述 3 个文件（+ 作者未提交的 `handoff.md`，非本审查所写）。**未触碰**卡 §4 任何禁写路径、README §4 任何 ROOT 独占路径、`docx_parser.py`、`pptx_parser.py`；未 git commit。

## 8. 诚实限制（未做/未验证）

1. **未在真实 DOCX/PPTX 原件上验证**。全部夹具为合成最小包；真实 Word 的 `w:vMerge`+`gridSpan` 组合、`w:tblHeader` 多行、真实 `footnotes.xml`（含 `-1`/`0` 分隔符）均未跑过。卡 §7 第 7 条要求的"未验证真实 DOCX 续表"依旧成立。
2. `work_used.chars` 计的是**单元格文本**字符，不含脚注文本（脚注另受 `max_footnote_chars` 约束）。卡未定义 `chars` 的精确口径，此处沿用"格文本"这一较窄口径。
3. `a:tblGrid` 缺失时 `grid.columns=null`，此时无法判定 PPTX 合并是否越界，只能不报（不猜）。DOCX 同理。
4. 非正 `w:gridSpan` 的处理是**本审查的裁定**（卡无规定）：`p2_span_out_of_grid` + `column_span=null` + 不推进/不关闭合并链。若 ROOT 认为应并入 `p2_merge_unresolved`，只需改一处分支。
5. PPTX 覆盖格保留原文（D7）是与 DOCX 的**有意不对称**，依据是既有解析器行为；若 ROOT 后续要求"被覆盖格无文本"，须同时改 `pptx_parser`（不在本卡写集）。
6. `continuation_of` 的表头"相同"以**表头行单元格文本序列**判定，未比较列宽/合并结构；两个表头文本相同但合并结构不同的情况会被判为续表。
7. 本报告未验证 `narrative_formats.py`（该文件零改动）。

## 9. 交接状态

本审查者已停止写入，**把工作树交还作者**。变更全部留在工作区未提交，作者可直接 `git add -A` 后提交。作者此前未提交的 `handoff.md` 未被本审查者改动。

本报告自身：`docs/plans/parallel-packages-2026-10-18/P2-OFFICE-TABLE/review/independent.md`

VERDICT: PASS

## 9. 复审（post-review delta ac1aa4cb + c1f2e96c + 87fd5f82）

**复审身份**：独立复审 agent（非作者、非 ROOT、非第 1 位审查者），受命对 `46e9052c..HEAD` 的
src/tests 增量做最终 SHA 复审。上一位复审 agent 中途崩溃未留报告，`87fd5f82` 由作者代提交，
按卡规则"旧审查结论不得签新代码"，该增量此前无任何存活报告背书。复审日期 2026-10-18。
全部探针与中间产物写在 `%TEMP%\p2_recheck\`（仓库外）；**未 git commit**；未改动
`handoff.md` / `handoff.json`（作者所有，见下方待修清单）；未触碰任何禁写路径。

### 9.1 编号分支全量复核（任务项 1）——通过，0 分歧

逐行比对 `docx_parser._DocxBody.table()`（docx_parser.py:356-402）与
`_DocxBody.body()`（:404-457）对 `t=` 的每一次自增，同
`office_table_structure._docx_table_order` 逐分支比对。
差分探针 32 例（29 个编号例 + 3 个 QA 例，`%TEMP%\p2_recheck\probe_numbering.py`），
每例同时断言三件事：(a) monkeypatch `_DocxBody.table` 记录的进入序列 ==
`_docx_table_order` 中非 None 位置；(b) `native_index` 序列 == 进入序列（即
`table_index=position`）；(c) 全部非 None 结构 locator ⊆ `parse_docx` 表格单元 locator。
覆盖分支：可见包装（`w:sdt` 有/无 `sdtContent`、`w:customXml`、`w:ins`、`w:moveTo`）、
删除区（`w:del`/`w:moveFrom`：平表、格内直嵌套表、格内 sdt 包嵌套表、del 内再包
sdt/customXml/ins/moveTo、del 套 del、del 套 sdt 套 del、**del 内 `w:p` 套表不计**）、
格内递归（三层直嵌套、可见格内 sdt 包裹嵌套表不计、可见格内 del 包表不计）、
空表计号、body 级 `w:p` 套表不计、kitchen-sink 混合。**全部与解析器逐位一致**。
`_parse_docx` 对 None 占位先 `continue` 再做限额判断，占位不消耗预算 ✓。

### 9.2 两条回归用例确实咬合（任务项 2）——通过

- 换入 `ac1aa4cb` 版模块（SHA-256 `E1F977D6…65EA30`，49893B）：
  `test_docx_deleted_region_tables_consume_the_parser_index` **失败**，消息：
  `AssertionError: deleted-region numbering drifted from the parser: ['cwp-docx-body/1|t=1|r=0|c=0|p=0']`
  （1 failed, 1 passed；`ac1aa4cb` 自带的嵌套用例通过）——即提交版给出 t=1 而解析器给 t=2。
- 换入 `46e9052c` 版模块（body.iter 时代，SHA-256 `223A8869…A20942`，47600B）：
  两用例**全失败**（2 failed）——
  `nested-table numbering drifted from the parser: ['cwp-docx-body/1|t=3|r=0|c=0|p=0']`
  （正是声称的 t=3 漂移）与同一 `t=1` 删除区消息。
- 恢复验证：换回 HEAD 内容后 `Get-FileHash`(工作区) = `0D8A18ED…A60972`，与换前**逐字节相同**；
  `git hash-object` = `90121754a804cfad0eda5adf573b4cd084609086` = `git rev-parse HEAD:path`；
  `git status` 干净；LF 内容 SHA-256 = `A9A0901A…F989C89`（= `sha256(git show HEAD:…)`）。
  EOL 说明：本仓 `core.autocrlf=true`，模块工作区为 CRLF（52433B = blob LF 51091B + 1342 CR），
  两种形式 clean 等价（`git diff --ignore-cr-at-eol` 为空），恢复后树与复审开始时完全一致。

### 9.3 真实文件对齐（任务项 3）——0 漂移；并查出 1 个潜在缺陷（已修）

语料 A（任务指定 `companies\**\*.docx|*.DOCX`）：181 文件 → **180 唯一**（1 重复：
分众传媒 20180829.DOCX == 分众传媒：2018年8月29日…DOCX）；含表 **95**；结构 locator
**2500，逐字符命中 2500，未命中 0**；解析/结构错误 0；解析器独有 **2565** 个 locator
（**382** 个单元格：171 格多 1 段、211 格多 ≥2 段），**100% 为同 t/r/c 且 p>j**（违规 0；
其中 4 条为更后段落本身再带 `|ch=` 切分，仍 p>j）；表 150；continuation
149 unknown / 1 ok；`vertical_continue` 164 / `vertical_start` 40；含纵向合并文件 34
（含横向/越界口径 35）；PPTX 0。

语料 C（重构作者"190 个唯一包"）：主仓全部 docx+pptx **193 文件 → 190 唯一**
= companies 180 + `docs/…/ci-docx-investigation` 证据 8（7 docx + 1 pptx）
+ `.venv`/`.venv-ci` 的 python-docx/pptx 模板 2。含表 100（99 docx + 1 pptx）；
locator **2519/2519，未命中 0**；表 157；continuation **154/1/2**；vc 164 / vs 40；错误 0。

- **声称 A 成立（实质）**：body.iter 旧编号在语料 C 上将产生 **644/2511（25.6%）**
  不在解析器输出中的结构 locator（语料 A：579）；含 sdt 嵌套表的真实文件恰 1 个
  （阿里巴巴 20190919 深度报告）：body.iter **34 张 vs 解析器 31 张**。
- **声称 B 成立**：190 包中 **0** 个含 body 级 `w:del`/`w:moveFrom` 表 → `87fd5f82`
  对本语料属前瞻性修复；合成 A/B 探针结论（t=[0,3]、旧版 t=1 错、新版 t=3 对）已由 9.2 实测复现。
- **声称 C 成立**：见 9.2。
- **缺陷 D-R1（复审查出，已修复）**：单元格首可见段落含**段中** QA 标记（如
  `前文 问：后文`）时，`docx_parser.emit`（docx_parser.py:310-339）对该段做 `|ch=` 切分，
  裸 `|p=…` locator 永远不会被解析器产出，而结构仍报裸 locator——探针失败消息：
  `structure locators absent from parse_docx: ['cwp-docx-body/1|t=0|r=0|c=0|p=0']`
  （qa_marker_after_space / qa_marker_after_punct 两例）。违反卡 §5.3（card.md:116、:158
  "逐字符相同"）与模块 docstring（:10-12）自身的承诺。属 delta 前遗留（f8c91996），真实语料
  未触发（首段带标记者 0，故 9.3 的 0 漂移不受影响），但输入合法、可复现。
  修复：`office_table_structure.py:52-53`（引入解析器自己的 `_QA_MARKER` 与
  `normalize_text`，单一事实来源）、`:333-359`（新增 `_docx_first_unit_suffix`，逐字镜像
  `emit` 的 starts/裁剪/跳空逻辑）、`:361-384`（`_docx_cell_locator` 追加首片 `|ch=` 后缀）。
  修复后 32/32 探针通过；**180 个语料文件的 `structure_sha256` 与 locator 逐个不变**
  （0/180 变化），回放收据不受影响。按写集限制**未新增套件用例**（用例数保持 69），
  复现配方：单格单段 `<w:t>前文 问：后文</w:t>`，期望 locator
  `cwp-docx-body/1|t=0|r=0|c=0|p=0|ch=0:2` ∈ `parse_docx` 输出。

### 9.4 handoff 声称核查（任务项 4，只读）——以下字符串需作者修正

1. handoff.md:12「68 个用例」、:48「**68 passed**，0 skipped」、handoff.json
   `tests[1].passed: 68` → 实测 **69 passed, 0 skipped**（复审未增删用例；收据
   `green-20261018-pytest.log` 内容 "68 passed" 亦过时——其 SHA 与 handoff 绑定一致，但内容过时）。
2. handoff.md:5「提交：f8c91996 + b61ed0c5 + ac1aa4cb」与 handoff.json `commits` → 缺
   `c1f2e96c`、`87fd5f82`；`changed_paths` 缺 `handoff.json` 自身（c1f2e96c 改了它）。
3. handoff.md:59-60「`companies/` 下 96 个唯一真实 DOCX…190 个唯一包」→ companies 下唯一
   DOCX 180、含表 95；190 唯一包只有把 docs/ 证据 8 个与 .venv 模板 2 个算进来才成立
   （"companies/ 下"表述不准确；`original_reads: 190` 数字本身可复现）。
4. handoff.md:61「修复前 24.8%（637/2540 前身）」→ 实测 644/2511 = 25.6%（语料 C）。
5. handoff.md:62「该文件 34 vs 25 张表」→ 实测 **34 vs 31**（body.iter 34 / 解析器与结构 31）。
6. handoff.md:64「2540/2540…0 漂移」→ 实测 2500/2500（companies）或 2519/2519（190 语料）；
   **0 漂移实质成立**，绝对数字 2540/96/159/165/41/37 在当前稳定语料（近 7 天零改动）上均不可复现。
7. handoff.md:66「剩余 276 个解析器独有 locator…」与 handoff.json `known_limits` 末条 →
   实测 2565 个（382 格；单元格口径 382、locator 口径 2565，均非 276）；"全部来自单元格多段落、
   p>j" **实质成立**（违规 0）。另注：语料中删除区表 0 例，"after ac1aa4cb 即 0 漂移"属偶然成立，
   一般情形自 `87fd5f82` 起才成立。
8. handoff.md:74-75、handoff.json `not_run[0]`「unknown 159 / ok 1 / not_applicable 2」→
   实测 154/1/2（190 语料）或 149/1/0（companies；companies 下无任何 PPTX）。
9. handoff.md:76-77「37 个含合并格，vertical_continue 165 / vertical_start 41」→
   实测 34 个文件（含横向/越界口径 35）/ 164 / 40。
10. handoff.md:78、handoff.json `not_run[1]`「真实 PPTX 样本仅 1 个」→ 190 语料中唯一
    PPTX 为 2（docs 证据 1 个含 2 表 + python-pptx 模板 1 个无表）；companies 下为 0。
11. handoff.json `file_bindings`：`office_table_structure.py` `e1f977d6…`/49893B 过时
    （`87fd5f82` 后即已过时：当时工作区 `0D8A18ED…`/LF `A9A0901A…`；本次复审修复后见 9.9）；
    `test_locator_compatibility.py` `80035d2f…`/7324B 过时（现 `632B6B40…`，11660B，
    blob `8375f4350c218101d2f895c2e4bd181003327159`）。其余 24 条绑定逐一核对**全部一致**。

### 9.5 作者新增的 D-R1 回归用例（handback 后独立复验）

本复审第一次交还工作树后，作者在其写集内新增**恰好一条**用例
`test_docx_qa_marker_cell_locator_carries_the_parser_piece_suffix`
（`tests/unit/test_p2_office_table/test_locator_compatibility.py:309-336`，+30 行），
把 §9.3 的 D-R1 修复锁进套件（§9.3 按当时写集限制未加用例；加在作者写集内合规）。
独立复验结论：

- **用例内容诚实**：夹具 `前文 问：后文` 单格单段；断言 (a) 裸 `|p=0` **不在** `parse_docx`
  输出集合中，(b) 结构 locator **在**该集合并以 `|ch=0:2` 结尾，(c) `text` 仍为整段
  （只有 locator 跟随切分）。无 skip/xfail、无 try/except、无 null→1 放宽。
- **确实咬合（实测）**：换入 `87fd5f82` 模块 blob（SHA-256 `A9A0901A…F989C89`，51091B）
  后单跑该用例 **失败**，消息：
  `AssertionError: cwp-docx-body/1|t=0|r=0|c=0|p=0`
  （`assert 'cwp-docx-body/1|t=0|r=0|c=0|p=0' in {'cwp-docx-body/1|t=0|r=0|c=0|p=0|ch=0:2', 'cwp-docx-body/1|t=0|r=0|c=0|p=0|ch=3:7'}`，
  失败于 :331 `assert locator in existing`）——正是 D-R1 症状（旧模块报裸 locator）。
- **模块复原验证**：换回后与复审绑定链三方核对**全部逐字符一致**——
  工作区 Get-FileHash `F5FE14A4563462DF803DC5474BA38ADACD905AF15091D47190EE943600136C94`、
  LF 内容 `9C83A3F9B5D0966FD1346384BFD20A630D077627D7EB41EB00514891689E7683`、
  `git hash-object` `e8356663efc3e3697f4cfcd0cb679bef8fecacd4`（见 §9.9）。
- 用例数 69 → **70**；模块相对 §9.9 绑定**零改动**。

### 9.6 验收门（任务项 5；按最终树复跑）——4/4 exit 0

- `python -B -c "import company_wiki; print(list(company_wiki.__path__))"` →
  本 worktree 的 `src\company_wiki` ✓
- `python -m pytest tests/unit/test_p2_office_table -q -p no:cacheprovider` →
  §9 签署时 69 passed；作者加用例后按最终树复跑 **70 passed, 0 skipped** ✓
- `python -m ruff check src/company_wiki/document_normalization/office_table_structure.py tests/unit/test_p2_office_table` → All checks passed ✓
- `python -m mypy src/company_wiki/document_normalization/office_table_structure.py` → Success ✓

### 9.7 测试诚实性（任务项 6）——通过

delta（46e9052c..HEAD，src+tests）仅 3 行删除（旧 `body.iter` 三行），0 个被删用例；
新增行中 skip/xfail/pytest.skip = 0，新增 try/except = 0（不存在吞 `ValueError`），
无 null→1 放宽断言；`assert … == [0, 2] / [0, 3]` 断言的是**非连续** native_index（真实行为）。

### 9.8 写集（任务项 7）——通过

`git diff --name-only 4045787f..HEAD` 共 28 个路径；禁写命中 **0**
（docx_parser.py / pptx_parser.py / narrative_formats.py / units.py / errors.py /
limits.py / document.py / replay.py / source_catalog/** / document_understanding/**
/ parser_adapters/** / tools/** / tests/integration/** 均不在其中）。

### 9.9 最终绑定 SHA-256（含作者新增用例后复验）

- `src/company_wiki/document_normalization/office_table_structure.py`（D-R1 修复；
  §9.5 复验后**零改动**）：工作区 Get-FileHash（CRLF 形态）=
  `F5FE14A4563462DF803DC5474BA38ADACD905AF15091D47190EE943600136C94`；
  LF 内容 SHA-256（= 提交后 `sha256(git show HEAD:…)`）=
  `9C83A3F9B5D0966FD1346384BFD20A630D077627D7EB41EB00514891689E7683`；
  `git hash-object` = `e8356663efc3e3697f4cfcd0cb679bef8fecacd4`。
- `tests/unit/test_p2_office_table/test_locator_compatibility.py`（**复审未改动**；
  含作者 §9.5 新增用例）：Get-FileHash =
  `DF2568D38F7C8B83A3CC89A8EF690553B125FC7274169E3733125A9EE2CF641D`；
  `git hash-object` = `6dc41a753f92b2b9c18cc150d71e858c8e56b220`。
  （取代 §9 首签时的 `632B6B40…`/`8375f435…`——该值对应加用例前的文件。）
- 本报告自身：`docs/plans/parallel-packages-2026-10-18/P2-OFFICE-TABLE/review/independent.md`
  （追加 §9 前 SHA-256 `7E44E7389C4D3DD192BCC4321EBB90097C47F9587B5B542F433DC4F5B823CA36`，
  与 handoff.json 旧绑定一致）。**报告文件无法在自身内绑定自身哈希**：§9 追加后的报告
  SHA-256 由作者在交接后自行计算并记入 handoff.json。

`git status` 三处 M：`office_table_structure.py`（= D-R1 修复，未提交）、
`test_locator_compatibility.py`（= 作者 §9.5 新增用例）、`review/independent.md`（= 本报告）；
无其他改动；未 git commit。

**交接状态**：复审者已停止写入，**把工作树交还作者**。9.4 的 handoff 修正属作者（handoff 为其所有）。

RE-REVIEW VERDICT: PASS
