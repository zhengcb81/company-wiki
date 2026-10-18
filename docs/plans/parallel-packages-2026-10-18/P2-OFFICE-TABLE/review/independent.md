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
