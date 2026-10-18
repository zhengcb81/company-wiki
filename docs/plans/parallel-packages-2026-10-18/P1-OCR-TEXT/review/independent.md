# P1-OCR-TEXT 独立审查报告（round 1）

- 审查者：独立 reviewer（非本卡作者、非 ROOT），package `parallel-packages-2026-10-18`
- 对象：worktree `C:\Users\郑曾波\Projects\company-wiki-p1-ocr-text`，分支 `codex/p1-ocr-text-20261018`，基线 `4045787f6bf77722d8125911f3475ecff9bca9b0`
- 范围：card §10 的 7 项 + 写集/旗标/依赖/计数核对。本报告只报告，不修改任何交付文件。
- 复跑结果（本轮亲自执行）：`pytest tests/unit/test_p1_ocr_text -q --tb=line` → **36 passed, 0 skipped**；`ruff check` → All checks passed；`mypy` → Success: no issues in 2 source files；`git diff 4045787f HEAD --name-only` → 20 个文件，全部 ⊆ card §4 写集；另存的 RED 提交 `7be453e1`（含实现前 stub）在临时归档树复跑 → **36 failed**，断言消息与现存 red 日志一致。

## Verdict: FAIL

原因：2 个 MAJOR（#1、#2）。按审查规则（任一 BLOCKER/MAJOR 即 FAIL）。

## Findings

### #1 — MAJOR — `docs/plans/parallel-packages-2026-10-18/P1-OCR-TEXT/handoff.json` 不存在（§8 handoff 字段全部无法核验）

- **违反条款**：INTERFACES §8（第 107 行）："每卡在自己目录写 `handoff.md`（人读，≤80 行）与 `handoff.json`（机器读）。`handoff.json` 必填：{schema_version, lane, status, baseline_commit, branch, commits, changed_paths, file_bindings, interface_versions, tests, red_receipt, fixtures, not_run, known_limits, root_integration_steps, scope_proof, independent_review}"；card §7 完成定义第 5 条（第 167 行）："`handoff.md`/`handoff.json` 齐全，`file_bindings` 覆盖全部改动文件"；README §6 第 96–97 行第 2、3 项（"新建文件与 `handoff.json` 中 `file_bindings` 的 SHA-256 逐一相等"、"`red_receipt` 指向真实失败日志"）→ "任一项不满足即 REJECTED"。
- **具体事实**：卡片目录仅有 `card.md`、`handoff.md`、三份日志；`handoff.md:28` 写 "（`red-2026-10-18.log`，SHA/字节见 `handoff.json`）"、`handoff.md:30` 写 "`file_bindings` 逐一重算……"，均指向不存在的文件（悬空引用）；`handoff.md` 本身尚未提交（`git status` 显示 `?? docs/.../handoff.md`），违反 INTERFACES §8 "先提交实现，再单独提交交接" 的可追溯性。
- **时序说明（按 ROOT 反馈如实记录）**：round-1 阶段 `independent_review` 字段确实无法填写（card §10 反自引用要求对最终 SHA 复审），该字段的延后是流程设计的一部分；但 `file_bindings`/`red_receipt`/`fixtures`/`tests`/`scope_proof` 等其余 §8 字段并不依赖本审查，现阶段缺失使 README §6.2/6.3 无法核验。
- **要求的修复**：`handoff.json` **必须在强制复审（对最终文件 SHA 的 review #2）/交付之前存在**，含按 `Get-FileHash` 重算的 `file_bindings`（path/sha256/bytes 与 20 个改动文件逐一相等）、真实 `red_receipt`、`fixtures`、`scope_proof`、`not_run`，并以 `independent_review` 引用本报告；`handoff.md` 需单独提交。

### #2 — MAJOR — 全宽页眉/页脚 + 多栏正文时列聚类整体坍缩，正文顺序被重排，违反 card §6 第 3 条的"底线"，且 handoff 的 known_limits 声明不实

- **文件:行**：`src/company_wiki/document_normalization/ocr_page_text.py:376-394`（`_cluster_columns` 以"当前列右边缘（列内 max x1）"为基准量间距）；证据性声明 `handoff.md:36`。
- **违反条款**：card §6 反例第 3 条（card.md:132）："页眉/页脚（跨整行宽、y 在页边）→ 不得被当正文行插进段落中间；**若不实现页边检测，必须至少不改变其余行顺序**，并把该情形写进 `known_limits`"；以及 §6 第 1 条（card.md:130）："两栏页面……必须判 `ambiguous_order` 或正确分列，不得串行拼接"。
- **实测证据（临时探针，未改任何交付文件）**：两栏正文（L1–L3 @x[50,300]，R1–R2 @x[500,750]）+ 全宽页眉 `PAGE HEADER [50,10,750,30]` + 全宽页脚，输入同一几何仅增删页眉页脚两行：
  - 无页眉：`ncols=2`，正文顺序 `L1\nL2\nL3\nR1\nR2`（列优先，符合 §6.1）；
  - 有页眉页脚：`ncols=1`，输出 `PAGE HEADER\nL1R1\nL2R2\nL3\nPAGE FOOTER`，`status="ok"`、全部 `defer_reasons=[]`、无任何 diagnostic。全宽行把列内 `col_right` 推到 750，右栏 `x0=500 - 750 < gap` 从而并入同一列 → 两栏页未被正确分列，且"其余行顺序"由列优先变行优先交错（R1 跑到 L2 之前），两栏片段被粘成 `L1R1` 单行。
  - 这正是真实扫描件最常见的版式；测试未覆盖该组合（`header_footer.json` 是单栏五段，`two_column.json` 无页眉），`test_header_and_footer_do_not_reorder_body_rows`（test_ocr_page_text.py:96）不断言列数，因此无法发现。
- **handoff 声明不实**：`handoff.md:36` 称 "§6 第 3 条仅保证不改变其余行顺序并已入 known_limits" —— 上述实测表明多栏页下该保证不成立（known_limits 只写了"未实现页眉页脚检测"，未记录"全宽行会合并列并重排正文"）。
- **附注（供 ROOT 裁决）**：card 规则 1 的字面实现与本底线存在张力——若改用"相邻行 x0 间距"切列，`indented_paragraph.json` 的缩进行 x0 差 40 = `column_gap_em(2)×em(20)` 恰好触发切列，会破坏 §6 第 2 条；即在冻结规则内两者难以同时满足。这与 handoff 已上报的 `locator_unstable` 冲突同类，应作为卡片规则冲突上报 ROOT，而非在 `known_limits` 中声称底线成立。
- **要求的修复**：(a) 为"全宽行 + 多栏"补反例测试并使其实现满足 §6 第 3 条底线（或按 §9.3 上报卡片冲突请求裁定）；(b) 修正 `handoff.md:36` 的 known_limits 表述；(c) 该情形下现状 `status="ok"` 且零 diagnostic 至少应显式 defer/标记，避免"看不见的错误"。

### #3 — MINOR — red 日志行号与已提交测试文件不对应（provenance 需重生成）

- **文件:行**：`docs/plans/parallel-packages-2026-10-18/P1-OCR-TEXT/red-2026-10-18.log:18`（报告 `test_ocr_page_text.py:63`）vs 已提交文件（`7be453e1..HEAD` 该文件无 diff）同一断言在 `test_ocr_page_text.py:57`；后续条目漂移 6–7 行（:89→:83、:110→:104、:446→:439），而 adapter 测试行号逐一精确吻合（:88、:111、:150、:222、:335 等）。
- **条款**：README §6 第 97 行 "`red_receipt` 指向真实失败日志，且失败发生在实现之前；日志里能看到断言消息而不是仅有 ImportError"。
- **实测**：日志格式经独立复现确认为真实 `--tb=line` 输出；RED 提交含实现前 stub（`ocr_page_text.py` 65 行占位返回空壳、adapter 35 行返回空 `PageAwarePDFResult`），失败为断言级而非 ImportError；我将 `7be453e1` 归档到临时目录复跑得 36 failed、断言文本一致——**实质满足 §6.3**。作者说明漂移源于 RED 采集后删除未用 import/局部变量（ruff F401）。
- **要求的修复**：按作者承诺，用当前已提交测试文件 + 实现前 stub 重新生成 `red-2026-10-18.log` 并更新 `handoff.json.red_receipt`，使行号精确对应，消除 provenance 缺口。

### #4 — MINOR — `handoff.md:30` 夹具体积数字不实

- **违反条款**：card §9（第 196 行）"必须报告：实际 `sha256`（重新计算，不抄自报）……"与 README §6 第 102 行诚实性要求。
- **事实**：`handoff.md:30` 称 "夹具……最大 14737 字节"；11 个 `fixtures/*.json` 实测最大为 `header_footer.json` = **460 字节**（133/276/51/460/302/301/349/374/278/275/458）。14737 恰为 `red-2026-10-18.log` 的字节数，疑似串写。合规结论不受影响（460 与 14737 均 ≤ 64 KiB），但证据数字错误。
- **要求的修复**：改为实测值（或以 `handoff.json.file_bindings[].bytes` 为准），由 `Get-FileHash/Length` 重算。

### #5 — MINOR — `parse_status` 的"文档级"与"页级"读法分歧，缺 [成功页 + 全 defer 页] 组合测试

- **文件:行**：`src/company_wiki/parser_adapters/pdf_ocr_page_adapter.py:252-253`、`:324-326`（逐页/逐结果判定）。
- **违反条款**：card §5.2（card.md:122）："`parse_status`：**全部页有 accepted 正文 → `parsed`；部分 → `partial`；无 accepted 正文 → `failed`**" —— 措辞是页集合的文档级语义；实现是页内行级（`PARTIAL if defer_reasons else PARSED`）。
- **后果**：文档 = [页1 全部 accepted, 页2 全部 defer] 时，输出为 `PARSED` + `FAILED`，**没有任何结果携带 `partial`**；36 个测试无一覆盖该组合（单页混合已有 `test_page_mixing_accepted_and_deferred_lines_is_partial`）。`handoff.md:16` 已披露"按页判定"，且 `PageAwarePDFResult` 无文档级状态字段、`pdf_page_aware` 同为逐结果模式，故不评 MAJOR。
- **要求的修复**：补该组合测试；若采文档级读法，任一页 `failed` 时存活页结果应为 `partial`；若冻结为页级读法，需在 handoff 明确该组合的行为并由 ROOT 裁决。

### #6 — MINOR — 规则 6 "该行起全部 `limit`" 对已带其它 defer 原因的行不成立

- **文件:行**：`src/company_wiki/document_normalization/ocr_page_text.py:315-319`（`if record["_reasons"]: continue` 先于 limit 分支）。
- **违反条款**：card §5.1 判定规则 6（card.md:111）："超过 `max_lines` 或累计 `max_chars` → **该行起全部 `limit`**"。
- **事实**：reading order 中 limit 触发点之后、已因 `low_confidence`/`ambiguous_order` 被 defer 的行不会再获得 `limit`（例：max_lines=1、行为序 [A(accepted), C(触发 limit), B(low_conf)] → B 仅 `["low_confidence"]`）。该行仍可见（无丢失），`status=partial` 与 `p1_page_limit` 诊断仍产生，故仅字面规则偏差 + 诊断计数少报。
- **要求的修复**：limit 触发后为所有后续行追加 `limit`（保留既有原因，多原因并列），或与 ROOT 确认豁免读法并补测试。

### #7 — MINOR — `column_overflow` 归入 `p1_page_limit`，与 §3 该码触发语义不符

- **文件:行**：`src/company_wiki/document_normalization/ocr_page_text.py:450-459`。
- **违反条款**：INTERFACES §3（INTERFACES.md:36）"`p1_page_limit` | P1 | **行数或字符数超限**"；card §5.1 表（card.md:88）"`diagnostics` …… code 见 INTERFACES 第 3 节"。列数超限既非行数也非字符数；§3 又无列溢出码且"只增不改"。
- **现状**：handoff.md:15、:36 已披露并请求 ROOT 决定是否增补专用码——披露充分，故 MINOR。
- **要求的修复**：ROOT 在 INTERFACES §3 增补（如 `p1_column_overflow`）后改映射，或书面追认现有归并；在此之前 detail 中已注明列数超限，保持可追溯。

### #8 — NIT — `reason` 字段与 `p1_page_empty` 超出 §5.1 字段表/§3 码表

`ocr_page_text.py:183` 对所有输出附 `reason`（非空页为 `null`），`p1_page_empty`（:82）不在 INTERFACES §3。card.md:75 明文要求空页 `reason="p1_page_empty"`，且 §1 "未知值用 null" 合规，handoff.md:12/36 已披露——建议 ROOT 在 §3/字段表补录该码。

### #9 — NIT — 测试注释编号与 card §6 反例序号错位

`test_ocr_page_text.py:322` 标 `§6.13` 实为列溢出（card §6 无此反例，13 条是适配器 ValueError），`:362` 标 `§6.15`（card §6 仅 14 条、确定性不在其中）。覆盖本身完整（14 条反例逐条有测试），仅注释误导。

### #10 — NIT — 未测 adapter 对 manifest/pages 的输入不变性

scope item 6 要求三类输入均不被变更。代码检查：`adapt_ocr_pages` 对 manifest/pages 只读（`pdf_ocr_page_adapter.py:190-348` 无任何对入参的写操作，Mapping 路径经 `dict(manifest)` 浅拷贝）；card §6 只强制 `ImageOCRResult` 不变性测试（已有 `test_input_result_is_not_mutated`）。建议补 manifest/pages 不变性断言以完整覆盖 scope item 6。

## 七项 scope 逐项结论

| # | 项 | 结论 |
|---|---|---|
| 1 | 与 INTERFACES 一致性（状态词表/§3 错误码/版本/偏移/§8 handoff 字段） | **FAIL** — 代码层一致（`ok/partial/unavailable` ⊆ §2 五值；diagnostics 仅 4 个 §3 码；`cwp-ocr-page-text/1`+`1.0.0` 与 §6 相符；char 偏移为 str 左闭右开且 adapter 逐行 slice 自证）；但 §8 handoff 字段因 `handoff.json` 缺失全部无法核验（F#1）；另有 F#7 码义偏差、F#8 码表外取值 |
| 2 | defer 语义未被绕过 | **PASS** — 两生产模块零 `try/except`；每个未接受行都保留在 `lines`（原样 text/box/confidence、`accepted=false`、≥1 个 `defer_reasons`）、进入 `deferred_line_indexes`、`char_start/char_end=null`；F#6 仅为规则 6 字面偏差，无行丢失 |
| 3 | 无不可见丢失 | **PASS** — 页级：`test_every_input_line_is_present_in_the_output_lines` + `_all_deferred` 路径全覆盖；adapter 级：全部 accepted 行逐行生成 `ParserResult` 且 `page_text[start:end]==line_text` 强校验，defer 经 `PARTIAL/FAILED` + §5.2 指定旗标如实上浮（bbox/列溢出无 §5.2 指定旗标，仅 partial，符合卡片旗标清单） |
| 4 | 几何规则无公司/文档类型特判 | **PASS** — 全文无公司名/mime/文件名/文档类型分支（grep 验证）；`min_confidence` 唯一来源 `PageOrderLimits`（card §5.1 规则 4）；`_LOW_QUALITY_THRESHOLD=0.30` 复用 `pdf_page_aware.py:39` 单源 |
| 5 | 确定性（两次调用 canonical JSON 字节一致） | **PASS** — 专测 `test_canonical_json_bytes_are_identical_across_two_calls`（`ensure_ascii/sort_keys/separators` 全参）；`defer_reasons` 经固定 `_DEFER_ORDER` 重建、`lines`/`deferred_line_indexes` 排序、诊断按固定序产出，无 set/dict 序依赖 |
| 6 | 输入不变性 | **PASS** — `order_page_lines` 只读（`tuple(result.lines)`、box 深拷贝为新 list），`test_input_result_is_not_mutated` 逐字段快照断言；adapter 对 manifest/pages 只读（F#10 为补测建议） |
| 7 | 测试真能红（断言级、非平凡） | **PASS（附 F#3 重生成要求）** — red 日志 36 failed 全为断言/`DID NOT RAISE` 级（格式经独立 `--tb=line` 复现确认为真）；RED 提交 `7be453e1` 含实现前 stub（非 ImportError），我归档复跑得 36 failed、断言一致；断言落在 `cwp-ocr-page-text/1` 字段（text/columns/char 区间/defer_reasons/diagnostics/flags），非"不抛异常"；行号漂移系 RED 采集后清理未用 import 所致，须重生成 |

**附加核对（全部通过）**：写集 ⊆ card §4（20 文件，禁写清单 0 触碰，README §4 ROOT 独占路径 0 触碰；额外未跟踪文件仅 `handoff.md` 与本报告）；无新增 `QualityFlag`（所用 7 值均在 `evidence_span.py:45-67` 既有枚举）；无新增依赖（仅标准库 + 既有包内契约）；无 `-k`/`--ignore`/`skip`/`xfail`（日志 `collected 36 items` 无 deselected，`pytest.ini` addopts 无忽略项）；计数 36 passed / 0 skipped 与 red、green 日志及本轮复跑三方一致；夹具均合成 JSON 且 ≤64 KiB；`static`/`green` 日志与复跑 exit 0 一致。

## Bound to SHA256

- `src/company_wiki/document_normalization/ocr_page_text.py` → `1d216d38d4707e9323235a62e4844dcffd49d38b8ab4a97bebe74b75035bf1a4`
- `src/company_wiki/parser_adapters/pdf_ocr_page_adapter.py` → `f6d08104292df062e048ee63b58f9501317d2232b975290ec470719068330c67`

（小写十六进制，本轮以 `Get-FileHash -Algorithm SHA256` 对原始字节重算，未抄自报。F#1、F#2 修完并复跑后，须对最终文件 SHA 出具 review #2；本报告结论不得签给变更后的代码。）
