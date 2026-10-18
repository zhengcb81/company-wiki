# P1-OCR-TEXT 交接

## 结论

- 状态：`FROZEN_AWAITING_ROOT_REVIEW`。基线 `4045787f6bf77722d8125911f3475ecff9bca9b0`，分支 `codex/p1-ocr-text-20261018`。三个**实现**提交：RED `7be453e1`（实现前 stub + 36 反例）、GREEN `8ce77823`（实现 + 静态检查）、审查修复 `3bee7420`；第 4 个提交 `cd095a70` 是交接提交自身，按 INTERFACES §8"不得把自身交付 commit 写进同一 commit 的交接"不列入 `handoff.json.commits`。
- 交付：纯组件 `order_page_lines`（`cwp-ocr-page-text/1`）与纯适配器 `adapt_ocr_pages`（`pdf-ocr-page-adapter/1`）。`parser_adapters/__init__.py` 未改（新适配器不从包级导出）。
- TDD：先 RED（实现前 stub 上全数断言级失败），再实现 GREEN。RED 日志已按审查 #3 用"当前已提交测试 + 实现前 stub"重新生成，行号与已提交测试逐一精确对应（首条 `:57` = `test_ocr_page_text.py:57`）。
- 独立审查：`review/independent.md` 为非作者 agent `bc126045` 原件（round 1 **FAIL**：2 MAJOR + 5 MINOR + 3 NIT）。MAJOR #2（全宽页眉页脚致多栏坍缩并重排正文）与 MINOR #5/#6/#9/#10 已在 `3bee7420` 修复并复跑 40 绿；MAJOR #1（缺 `handoff.json`）由本文件与 `handoff.json` 履行；round 2 对最终 SHA 复审结论见 `handoff.json.independent_review`。
- **未接生产、未跑真实扫描件**：没有接入任何真实 PDF 入口，没有跑过真实扫描件，没有验证真实 OCR 输出质量；扫描件质量不得视为已通过。

## 接口

- `order_page_lines(result, *, limits=PageOrderLimits(), font_size=None) -> dict`。输出 9 个字段 + `reason`：`reason` 仅按卡 §5.1 第 75 行在空页取 `"p1_page_empty"`，其余 `null`（字段表未列，但第 75 行明文要求）。
- 列切分：边界取自**同一视觉行内**相邻行的横向间隔（合并跨行重叠边界为一条带）。这样全宽页眉/页脚（独占一行）不会把列右缘推满而吞掉正文的分栏，从而满足 §6 第 3 条"不实现页边检测也至少不改变其余行顺序"的底线——已用 `two_column_with_header.json` 反例验证（2 列保持、正文列优先顺序不变、页眉页脚只落其列首尾）。同一视觉行分段直接拼接使 `char` 区间连续不重叠。
- 规则 6：limit 切点之后**阅读顺序上**的每一行都补 `limit`，并保留其原有 defer 原因（如 `["low_confidence","limit"]`），不再跳过已 defer 的行。
- `work_used = {"lines": 已接受行数, "chars": len(text)}`。`defer_reasons` 仅 5 词表；`diagnostics.code` 仅 INTERFACES §3；`column_overflow` 无专属码归入 `p1_page_limit`（明细注明列数超限）。
- `adapt_ocr_pages(manifest, pages)`：`parse_status` 按卡 §5.2 文档级读法——无任一页产出 accepted 正文则该页 `failed`；**只要存在全 defer 页，其余存活页一律 `partial`**（不再读作干净 `parsed`）；全 clean → `parsed`。行偏移经 `page_start` 并入 `normalized_text`，与 `pdf_page_aware` 段落绑定一致。
- 质量旗标仅既有值：`ocr_used`/`low_ocr_confidence`/`layout_ambiguous`/`truncated`/`locator_unstable`/`parser_warning`（纯文本页 `quality_score<0.30`，复用 `pdf_page_aware` 阈值）。`locator_unstable` = 页码序列非 `1..N`；重复/≤0 按 §5.2 失败语义抛 `ValueError`。
- 解析器身份：`parser_name="pdf_ocr_page_adapter"`、`parser_version="1.0.0"`、适配器 id `pdf-ocr-page-adapter/1`；接线时是否统一为 `pdf_page_aware_core` 由 ROOT 决定。

## 证据

- 验收四条命令均 exit 0：`import company_wiki` 指向本 worktree；`pytest tests/unit/test_p1_ocr_text -q` → **40 passed, 0 failed, 0 skipped**（`green-2026-10-18.log`）；`ruff` → `All checks passed!`；`mypy` → `Success: no issues found in 2 source files`（`static-2026-10-18.log`）。
- RED：`--tb=line` → **40 failed**，全部断言级而非 `ImportError`，行号与已提交测试精确对应（`red-2026-10-18.log`）。SHA/字节见 `handoff.json.red_receipt` 与 `file_bindings`。
- 用例 40（卡 §6 14 条反例全覆盖 + 适配器失败语义 + 文档级 partial + 两条输入不变性 + 确定性 + socket 零网络）；0 skip；无 `-k`/`--ignore`/`skip`。
- `file_bindings` 逐一 `Get-FileHash -Algorithm SHA256` 重算，覆盖 2 生产模块、17 测试/夹具、3 日志、审查报告与本文件（`handoff.json` 因自引用除外，见 INTERFACES §8"先提交实现，再单独提交交接"）。夹具全部合成 JSON，最大 `two_column_with_header.json` = **582 字节**（远低于 64 KiB；以 `handoff.json.file_bindings` 为准，旧稿 14737 与 460 两处误记均按审查 #4 更正）。
- `scope_proof`：生产数据/配置/DB/原件写入 0，密钥读取 0，网络 0，模型 0，禁写路径 0；`git diff --stat 4045787f HEAD --name-only` 全部 ⊆ 卡 §4 写集（审查复核通过）。

## 未做

- `not_run`：真实扫描件 PDF 回放；真实 OCR 引擎产出的 `ImageOCRResult` 质量评估；`order_page_lines` 接入真实 PDF 入口；`adapt_ocr_pages` 接在 `pdf_page_aware` 之前；原件 SHA 前后核对。均归 ROOT 生产 E2E。
- `known_limits`：未实现页眉页脚检测（页眉页脚仍进入正文，落在其几何列的首/尾；已由 `two_column_with_header.json` 反例证明不改变其余行顺序、不吞并分栏——原稿"仅保证不改变顺序"的未经验证声明已按审查 #2b 更正）；未处理竖排/旋转；未跑真实扫描件；`reason` 字段与 `p1_page_empty` 超出 §5.1 字段表/§3 码表（卡第 75 行明文要求）。
- 需 ROOT 裁决：接线时 `parser_name` 是否统一为 `pdf_page_aware_core`；§3 是否增补空页/列溢出专用码；`locator_unstable` 与 `ValueError` 语义冲突的最终取舍。
