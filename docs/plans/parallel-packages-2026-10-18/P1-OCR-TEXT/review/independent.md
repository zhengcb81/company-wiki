# P1-OCR-TEXT 独立审查报告（round 2）

> **交付来源说明**：本报告由独立 reviewer agent `4267adef`（非本卡作者、非 ROOT）在回复中交付，作者逐字转录，未增删结论；两条 SHA256 由该 agent 本人以 `Get-FileHash -Algorithm SHA256` 对原始字节重算。round 1 的 FAIL 原件（其全部发现已由本报告判定 FIXED）保留在 git 提交 `cd095a70` 的同一路径 `docs/plans/parallel-packages-2026-10-18/P1-OCR-TEXT/review/independent.md`。

---

## Verdict: PASS

复跑（本轮亲自执行）：`pytest tests/unit/test_p1_ocr_text -q -p no:cacheprovider --tb=line` → **40 passed**；`ruff check` → All checks passed!；`mypy` → Success: no issues in 2 source files；`git status --porcelain` → 干净树；`git diff 4045787f HEAD --name-only` → 25 个文件。round-1 的 2 个 MAJOR 均已修复；仅 1 个新 MINOR（证据数字），按规则（仅 BLOCKER/MAJOR 判 FAIL）判 PASS。

round-1 findings：
- #1 FIXED — handoff.json 存在，顶层 17 键与 INTERFACES §8 清单一一对应；changed_paths(24) ≡ file_bindings(24) 一一对应；全部 24 条 sha256+bytes 独立重算 0 不符（含两源文件 19095/16115 B、red 16276 B、green 1349 B、handoff.md 5632 B）；git diff 25 = 24 + handoff.json 自身（§8 反递归条款允许）；handoff.md 已提交（树干净）。
- #2 FIXED — 探针：`two_column_with_header` → `cols 2`，text=`'PAGE HEADER\nLeft one\nLeft two\nLeft three\nPAGE FOOTER\nRight one\nRight two'`（页眉在首、左栏正文列优先有序、页脚落左栏尾、无 "Left oneRight one" 粘连）；`two_column`→2 列列优先、`indented_paragraph`→1 列。新增夹具 two_column_with_header.json + 反例测试 test_full_width_header_and_footer_do_not_collapse_two_columns（test_ocr_page_text.py:452，断言 cols==2、列成员、正文顺序、页眉/页脚位置）通过；known_limits 已更正（handoff.md:32、handoff.json known_limits[3]）。
- #3 FIXED — red 日志首条失败 `test_ocr_page_text.py:57: AssertionError: two-column page must split into 2 columns` 与已提交测试第 57 行精确一致（:83、:104 亦逐一吻合）；尾部 `40 failed`；全部断言级（AssertionError + 6 处 "DID NOT RAISE ValueError"，12 处大小写敏感命中为各重复一次），ImportError/ModuleNotFoundError = 0。
- #4 NOT FIXED（原 14737 已改正，但同类错误回归）— handoff.md:26 称"最大 header_footer.json = 460 字节"，而本次修复新增的 two_column_with_header.json = 582 字节才是当前最大（handoff.json file_bindings 数字正确）。列为新 MINOR（下同）。
- #5 FIXED — test_document_with_a_failed_page_marks_surviving_page_partial（test_pdf_ocr_page_adapter.py:346）存在且通过，断言 surviving.parse_status == PARTIAL、failed == FAILED；red 日志中该测试实现前确为失败；handoff.md:17 明示文档级语义。
- #6 FIXED — test_limit_also_marks_lines_already_deferred_for_another_reason（test_ocr_page_text.py:488）通过，断言第 2 行 `["low_confidence","limit"]`（保留原原因 + 追加 limit）；handoff.md:15。
- #7 FIXED — handoff.json known_limits 与 handoff.md:16 披露 column_overflow 暂归 p1_page_limit、待 ROOT 在 §3 增补专用码（round-1 要求的披露充分）。
- #8 FIXED — known_limits 披露 reason 字段与 p1_page_empty 超出 §5.1 字段表/§3 码表（handoff.md:13/32、handoff.json known_limits[4]）。
- #9 FIXED — 误导性 §6.13/§6.15 注释已删除；现存 §6.1–§6.11、§6.14 与 card §6 反例序号逐一对应（§6.12/§6.13 仅缺标签，覆盖仍在 — NIT）。
- #10 FIXED — test_adapter_does_not_mutate_manifest_or_pages（test_pdf_ocr_page_adapter.py:387）存在、通过、red 日志实现前失败；manifest.to_dict()+deepcopy(pages) 前后比对。

card §10 七项 scope：
1. 接口一致性 PASS — status ⊆ INTERFACES §2 五值；diagnostics 码 ⊆ §3（column_overflow 归并已披露待裁决）；interface_versions = cwp-ocr-page-text/1 + pdf-ocr-page-adapter/1；handoff §8 必填键 17/17。
2. defer 语义未绕过 PASS — 未接受行全部保留（原样 text/box、≥1 defer_reasons、char=null），多原因并列有测试（:500）。
3. 无不可见丢失 PASS — 页级逐行存在性测试 + 文档级 partial 测试 + adapter 逐行 `page_text[start:end]==line_text` 强校验，全绿。
4. 无公司/文档类型特判 PASS — 两源文件仅 math/statistics/unicodedata/包内契约导入；唯一 mime 引用是 GREEN 提交 8ce77823 既有的 `application/pdf` 前置校验（契约守卫，非几何特判），无公司名/文件名分支。
5. 确定性 PASS — canonical JSON 两次调用字节一致专测通过；defer 原因固定序重建。
6. 输入不变性 PASS — test_input_result_is_not_mutated（:349）与 manifest/pages 不变性测试（:387）均通过。
7. 测试真能红 PASS — red 日志 40 failed 全断言级、行号与已提交测试精确对应、首条 :57，针对实现前 stub 7be453e1。

附加核对：写集 25 文件 ⊆ card §4（2 源文件 + tests/unit/test_p1_ocr_text/** + docs/.../P1-OCR-TEXT/**），禁写清单 0 触碰；无新增 QualityFlag（7 值均为既有枚举）；无新增依赖（仅标准库 + 包内契约，requirements 未动）；无 -k/--ignore/skip/xfail（grep 0 命中，addopts 干净，40 collected = 40 run = 40 passed）。

NEW findings：
- MINOR — handoff.md:26：夹具"最大 header_footer.json = 460 字节"不实，当前最大为 two_column_with_header.json = 582 字节。条款：card §9 / README §6.8 诚实性。修复：改为 582（以 handoff.json file_bindings 为准）。
- NIT — handoff.md:5 "三个提交" vs 分支实际 4 个（第 4 个 cd095a70 即交接提交自身，按 §8 反递归不得自列，建议注明）。
- NIT — adapter 测试缺 §6.12/§6.13 注释标签（覆盖完整，仅编号注释不全）。

## Bound to SHA256
- src/company_wiki/document_normalization/ocr_page_text.py → 29d0690a9459b5165534519343c95d45fe4f1e2ce724f6dfa6960128c85ab389
- src/company_wiki/parser_adapters/pdf_ocr_page_adapter.py → 02712372c3da28450d12c11bb4e351fcca5ed29630ad98f9266a1c900f5bedab

（小写十六进制，Get-FileHash -Algorithm SHA256 对原始字节重算；未修改任何交付文件，review/independent.md 的 round-1 原件未被覆盖。）
