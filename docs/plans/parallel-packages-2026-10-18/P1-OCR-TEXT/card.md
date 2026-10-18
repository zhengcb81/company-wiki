# P1-OCR-TEXT：扫描页 OCR 行的有界正文与页内顺序

状态：READY，2026-10-18。范围是**纯组件**：把已有的 OCR 行观察变成可定位正文，并对不确定部分显式 defer。生产接线由 ROOT 做。
PLAN_ID=parallel-packages-2026-10-18/P1-OCR-TEXT。

## 1. 真实问题

- 现有 OCR 只服务 PPTX 不透明图片：`document_normalization/ocr_composition.py` 的 `enrich_pptx` 把 `ImageOCRResult` 内联进已解析幻灯片（`cwp-pptx-image-ocr/1`、parser `2.0.0`）。扫描件 PDF 没有"整页 OCR → 页内阅读顺序 → 可定位正文"的路径。
- `parser_adapters/pdf_page_aware.py` 的 `adapt_pdf_pages` 只接受已经抽好的 `text` 页，不接 OCR 行；扫描页要么整页无正文，要么由上游把识别行按返回顺序硬拼，顺序与真实阅读顺序无关。
- `local_ocr.py` 的 `OCRLine` 只有 `text/box/confidence`，没有列聚类、行分组、阅读顺序，也没有"低置信度 → defer"的语义。`ocr_region_recovery.py` 的成因说明：低于 `text_score` 的行在合成前就被丢弃，属于"看不见的丢失"。
- 结果：即使 OCR 跑通，也无法回答"这一行在页面的哪个位置、属于哪一列、是否可信"，无法生成可回放的 locator。

## 2. 目标

1. 新增纯函数 `order_page_lines`：输入 `ImageOCRResult`，输出 `cwp-ocr-page-text/1`，给出列划分、阅读顺序、每行的字符区间与 accepted/deferred 判定。
2. 低置信、几何交叉、越界、超限的行**不进入正文**，但保留在结果里并带 `defer_reasons`，供下游如实报告。
3. 新增纯适配器 `adapt_ocr_pages`：把 OCR 页（以及可混排的纯文本页）映射到既有 `ParserResult`/`EvidenceCoordinates`，正确设置 `ParseStatus` 与既有 `QualityFlag`。
4. 全程无 IO、无模型、无网络；同一输入输出字节确定。

## 3. 非目标（明确不做）

- 不实现 OCR 引擎、不下载模型、不调用任何 provider；只消费已产出的 `ImageOCRResult`。
- 不做版面分析（表格检测、图片/文字分离、竖排/旋转识别）；这些保持 `not_evaluated`。
- 不改 `narrative_reading`/`narrative_ocr_groups` 等 `source_catalog/narrative_*`；不决定哪些页/哪些行最终进摘要。
- 不改 `pdf_page_aware.py` 现有行为，不改变 `cwp-docx-body/1`、`cwp-pptx-shape/2` 任何 locator。
- 不新增 `QualityFlag` 枚举值；不新增预算/许可/审批对象。
- 不跑真实扫描件 PDF；真实原件验证归 ROOT 的生产 E2E。

## 4. 独占写集

**新增（本卡独占）**

- `src/company_wiki/document_normalization/ocr_page_text.py`
- `src/company_wiki/parser_adapters/pdf_ocr_page_adapter.py`
- `tests/unit/test_p1_ocr_text/**`（含 `fixtures/**`）
- `docs/plans/parallel-packages-2026-10-18/P1-OCR-TEXT/**`

**可选窄改（仅当共享辅助函数确实需要）**

- `src/company_wiki/document_normalization/ocr_composition.py`：只允许抽出/复用既有纯辅助（如 `adapter_identity` 的调用形状），不得改变 `enrich_pptx` 的现有输出、locator 或 parser 版本。

**禁写**

- `src/company_wiki/document_normalization/__init__.py`、`units.py`、`errors.py`、`limits.py`、`document.py`、`replay.py`、`docx_parser.py`、`pptx_parser.py`、`local_ocr.py`、`ocr_region_recovery.py`、`isolated_ocr.py`
- `src/company_wiki/source_catalog/**`（整目录）、`src/company_wiki/automation/**`、`src/company_wiki/document_understanding/**`
- `src/company_wiki/parser_adapters/__init__.py`、`pdf_page_aware.py`、`pdf_extract_v3.py`
- ROOT 独占清单：`narrative_reading.py`、`narrative_operating_relations.py`、`narrative_antecedent.py`、`operating_states/relations.py`、`operating_states/product_reference.py`、`tests/unit/du11_source_closure/**`、`docs/plans/du11-*/**`、`docs/plans/document-understanding-2026-10-13/**`
- 其余三卡的写集（见 README 第 2 节）

## 5. 冻结接口

### 5.1 `order_page_lines`

```python
P1_PAGE_TEXT_SCHEMA = "cwp-ocr-page-text/1"
P1_PAGE_TEXT_VERSION = "1.0.0"

@dataclass(frozen=True)
class PageOrderLimits:
    max_lines: int = 2000
    max_chars: int = 20000
    max_columns: int = 4
    min_confidence: float = 0.60
    column_gap_em: float = 2.0
    line_tolerance_em: float = 0.60

def order_page_lines(
    result: ImageOCRResult,
    *,
    limits: PageOrderLimits = PageOrderLimits(),
    font_size: float | None = None,
) -> dict[str, object]: ...
```

输入只读；函数**不得**修改 `result` 或其内部 `lines`。`font_size` 未给时用"该页行高中位数"作为 em 基准；中位数不可得（行数 0）时返回 `status="unavailable"`、`reason="p1_page_empty"`。

输出字段（`cwp-ocr-page-text/1`）：

| 字段 | 类型 | 语义 |
|---|---|---|
| `schema_version` | str | 固定 `cwp-ocr-page-text/1` |
| `page` | `{width:int, height:int}` | 直接取自输入，不缩放 |
| `status` | str | `ok|partial|unavailable` |
| `columns` | list | `[{column_id, x0, x1, line_indexes}]`，从左到右 |
| `lines` | list | 见下 |
| `text` | str | **仅 accepted 行**按阅读顺序以 `"\n"` 连接；无 accepted 行为 `""` 且 `status="unavailable"` |
| `deferred_line_indexes` | list[int] | 未进入正文的行 |
| `diagnostics` | list | `[{code, detail}]`，code 见 INTERFACES 第 3 节 |
| `work_used` | `{lines:int, chars:int}` | 实际计费量，诚实报数 |

单行字段：

| 字段 | 类型 | 语义 |
|---|---|---|
| `line_index` | int | 输入 `lines` 的原下标，0 起 |
| `column_id` | str | `"col-0"`…；未归列时 `null` |
| `text` | str | 原样，不改写、不补字 |
| `box` | `[float,float,float,float]` | 原样 |
| `confidence` | float | 原样 |
| `char_start`/`char_end` | int/null | 在 `text` 中的字符区间（`str` 偏移，左闭右开）；deferred 行 `null` |
| `accepted` | bool | 是否进入 `text` |
| `defer_reasons` | list[str] | `low_confidence`、`ambiguous_order`、`bbox_invalid`、`limit`、`column_overflow` |

**判定规则（必须按此实现，不得自创）**

1. 列聚类：以行 `x0` 排序，相邻行横向间隔 ≥ `column_gap_em × font_size` 时切列；列数 > `max_columns` 时整页 `status="partial"` 并给所有未归列行 `column_overflow`。
2. 行排序：列内按 `(round(y0/tolerance), x0)`；`y0` 差 < `line_tolerance_em × font_size` 视为同一视觉行，按 `x0` 升序拼接。
3. 顺序歧义：同一视觉行内两行 `x` 区间互相交叉（A 左端 < B 左端 且 A 右端 > B 右端，反之亦然）且 `x` 重叠 > 50% → 两行都 `ambiguous_order`，都不进正文。
4. 低置信：`confidence < min_confidence` → `low_confidence`。阈值只有这一个来源，不得按公司/文档类型分叉。
5. 越界/非法框：箱体超出页面或非有限 → `bbox_invalid`（输入已由 `ImageOCRResult` 校验，本函数仍要防 `font_size` 推导出的比率非有限）。
6. 超限：超过 `max_lines` 或累计 `max_chars` → 该行起全部 `limit`，`status="partial"`，不得截断行内文字。
7. 确定性：同一输入两次调用的 canonical JSON 字节完全相同。

### 5.2 `adapt_ocr_pages`

```python
def adapt_ocr_pages(manifest: Mapping, pages: Sequence[Mapping]) -> PageAwarePDFResult: ...
```

- `pages[i]` 形状：`{page_number:int, ocr: <cwp-ocr-page-text/1 dict>}` 或 `{page_number:int, text:str, quality_score:float}`（混合允许）。
- 输出复用 `pdf_page_aware` 的 `ParserResult` 与 `EvidenceCoordinates`：OCR 页以 `char_start/char_end` 绑定到该页 `text`；`page_number` 必须 1 起且连续。
- `parse_status`：全部页有 accepted 正文 → `parsed`；部分 → `partial`；无 accepted 正文 → `failed`（不得返回空字符串冒充成功）。
- `quality_flags`（只用既有值）：任一 OCR 页 → `ocr_used`；存在 deferred `low_confidence` 行 → `low_ocr_confidence`；存在 `ambiguous_order` → `layout_ambiguous`；存在 `limit` → `truncated`；页序不连续/重复 → `locator_unstable`。
- 失败语义：manifest 与 pages 不匹配、页码重复或 ≤0、ocr 段 schema 不符 → 抛 `ValueError`（不吞异常、不降级为 partial）。

## 6. TDD 要求（先 RED 后 GREEN）

**A：先写反例并保存 RED**（≥14 个用例，全部在实现前失败且是语义失败）

- 两栏页面被按返回顺序拼接 → 必须判 `ambiguous_order` 或正确分列，不得串行拼接。
- 单栏带缩进的段落（首行缩进 2em）→ 不得被切成两列。
- 页眉/页脚（跨整行宽、y 在页边）→ 不得被当正文行插进段落中间；若不实现页边检测，必须至少不改变其余行顺序，并把该情形写进 `known_limits`。
- 低置信行（0.42）夹在两行正常行之间 → 正文不得包含它，`deferred_line_indexes` 必须含它。
- 返回顺序完全乱序的行 → 输出顺序必须由几何决定，两次运行一致。
- 同一视觉行三段（左/中/右）→ 按 `x` 合并，`char` 区间连续且不重叠。
- 两行 `x` 互相交叉 → 两行都 defer。
- 空页（`lines=()`）→ `status="unavailable"`，`text=""`，不抛异常。
- 行数超 `max_lines`、字符超 `max_chars` → `partial` + `limit`，不截断行内文字。
- 页面宽高与 `box` 边界一致/越界 → `bbox_invalid`。
- `font_size` 给 `None` 与给显式值 → 排序结果一致（em 基准只影响容差，不改变列归属的既定用例）。
- 适配器：全 OCR 页 → `parsed` + `ocr_used`；混合页 → `partial`；全 defer → `failed`。
- 适配器：页码重复、`page_number=0`、ocr schema 版本错 → `ValueError`。
- 输入不变性：调用前后 `ImageOCRResult` 逐字段相等。

**B：实现并集中 GREEN**，一次跑完本卡全部单测；断言必须落在 `cwp-ocr-page-text/1` 字段上，不得只断言"不抛异常"。

**C：静态检查 + 交接**，见第 7 节。

禁止：删用例、`skip`、放宽阈值、把 `partial` 断言改成 `ok`、用 `try/except` 吞掉失败。

## 7. 验收命令与完成定义

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -B -c "import company_wiki; print(list(company_wiki.__path__))"
python -m pytest tests/unit/test_p1_ocr_text -q -p no:cacheprovider
python -m ruff check src/company_wiki/document_normalization/ocr_page_text.py src/company_wiki/parser_adapters/pdf_ocr_page_adapter.py tests/unit/test_p1_ocr_text
python -m mypy src/company_wiki/document_normalization/ocr_page_text.py src/company_wiki/parser_adapters/pdf_ocr_page_adapter.py
```

**完成定义（全部满足才算交付）**

1. 上述四条命令 exit 0；`requirements` 里没有新增依赖。
2. `tests/unit/test_p1_ocr_text` 至少 14 个用例，无跳过；RED 日志与 GREEN 日志都在本卡目录。
3. 输出通过 `json.dumps(..., sort_keys=True)` 两次调用字节相同（有专门用例）。
4. 未触碰第 4 节禁写清单任一路径（`git diff --stat` 可证）。
5. `handoff.md`/`handoff.json` 齐全，`file_bindings` 覆盖全部改动文件。
6. 独立审查 PASS，且审查报告绑定最终文件 SHA。
7. 明确写清"未接生产、未跑真实扫描件"，不得声称扫描件质量已通过。

## 8. 资源与安全边界

- 原件只读：本卡不读任何 PDF 原件；测试夹具是**合成** `ImageOCRResult` JSON（体积 ≤ 64 KiB/个）。
- 不读密钥、不联网、不调模型；`socket` 可用测试内 monkeypatch 断言零调用。
- 不写 `config/source_catalog.yaml`、生产 DB、`output/`、gold。
- 不新增人工许可/审批文件；不新增资源上限对象，`PageOrderLimits` 只是本组件的调用内限额。
- 测试用 `tmp_path`；结束后测试目录恢复原状。

## 9. 交接格式

`handoff.md` ≤80 行，按"结论 / 接口 / 证据 / 未做"四段写。`handoff.json` 用 INTERFACES 第 8 节外壳，并补充：

```json
{
  "lane": "P1-OCR-TEXT",
  "interface_versions": {"p1_page_text": "cwp-ocr-page-text/1", "adapter": "pdf-ocr-page-adapter/1"},
  "known_limits": ["未实现页眉页脚检测", "未处理竖排/旋转", "未跑真实扫描件"],
  "root_integration_steps": [
    "在真实 PDF 入口把 ImageOCRResult 交给 order_page_lines",
    "把 adapt_ocr_pages 接在 pdf_page_aware 之前，保持既有 locator 与 parser 版本",
    "真实扫描件回放时核对原件 SHA 前后不变"
  ]
}
```

必须报告：实际 `sha256`（重新计算，不抄自报）、RED→GREEN 命令与计数、`not_run`。

## 10. 独立审查要求

- 审查者必须**不是**本卡作者，也不是 ROOT。
- 审查范围：接口与 INTERFACES 是否一致；defer 语义是否被绕过；是否存在"看不见的丢失"（行被静默丢弃）；几何规则是否含公司/文档类型特判；确定性；输入不变性；测试是否真的能红。
- 审查发现的问题必须由作者修完并复跑，然后**对最终文件 SHA 复审**；旧 SHA 的审查结论不得签给新代码。
- 审查报告写本卡目录 `review/independent.md`，并在 `handoff.json.independent_review` 引用。
