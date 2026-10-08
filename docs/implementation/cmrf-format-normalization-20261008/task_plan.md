# R6-FORMAT Task Plan — HTML/PPTX 确定性规范化与定位回放

- 卡片: `docs/plans/cross-market-rf-e2e-2026-10-08/harness_lanes/cwp_format_normalization.md`（canonical，只读）
- 工作树: `C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/cwp-formats`
- 分支: `codex/cmrf-format-normalization-20261008`，基线 `eaad25a4bb2e6bbe5a8e110ec629dde4c5ddbda2`（worktrees.json 登记一致，工作树干净）
- PWF 根: 本目录（`docs/implementation/cmrf-format-normalization-20261008/`），不写共享计划目录。

## 独占写入范围（对齐卡片）

- `src/company_wiki/document_normalization/`（新增包）
- `tests/document_normalization/`（新增测试包 + run_real_originals.py）
- `docs/implementation/cmrf-format-normalization-20261008/`（本 PWF + HANDOFF + handoff.json）

只读 import：`source_catalog/narrative_document.py`、`narrative_replay.py`、`source_contract/evidence_span.py`。不改 source_catalog/automation/source_contract/config/CI/依赖。

## 冻结接口（卡片原文，实现不得偏离）

```python
normalize_document(original: bytes, *, source_id: str, source_sha256: str,
                   mime_type: str, limits: NormalizationLimits) -> NormalizedDocument
replay_unit(original: bytes, *, source_sha256: str,
            unit: NarrativeUnit, limits: NormalizationLimits) -> str
```

导出包：`company_wiki.document_normalization`。复用 `NarrativeUnit/DocumentStructure/EvidenceCoordinates`，不造第二套 EvidenceSpan。metadata 统一 `normalization_schema="cwp-document-normalization/1"` + 版本化 `source_locator`（HTML `cwp-html-dom/1`，PPTX `cwp-pptx-shape/1`）。unit_id 绑定 source_id/source_sha256/parser版本/versioned locator/规范化文本SHA/unit_kind，跨进程稳定。

## 阶段

1. [x] 读卡 + 既有代码 + 定位真实原件;建 PWF。
2. [x] RED:基线无 `document_normalization` 包,`pytest tests/document_normalization` exit=4
   (ModuleNotFoundError);语义反例由机制测试覆盖(所有权双计、隐藏泄漏、空成功、回放冒用)。
3. [x] GREEN:limits/OpaqueAsset/NormalizedDocument DTO + HTML 解析 + PPTX 解析 + replay;
   64 测试全绿。
4. [x] 真实原件大节点:微软 SEC 10-K HTML(8.1MB)→ 5,215 units、coverage True、~5.1s;
   MSFT 图片型 PPTX(4.0MB)→ 22 slides、诚实 partial(22 opaque + 22 image assets、
   media bytes 逐一 SHA 验证)。报告:`real_originals_report.json`。
5. [x] 收尾:HANDOFF.md / handoff.json / 分支提交。

## 设计决策(实现细则,已定稿)

- 解析器: HTML 用 bs4 + stdlib `html.parser`;PPTX 用 zipfile 预扫描(穿越/成员数/
  累计解压/媒体预算)+ python-pptx 对象模型。
- 所有权:字符串归最近 block owner;`td/th` 走 cell 模式(cell 内块皆为包装,文本并入
  cell unit;嵌套 table 的 cell 自成单元);`html` 仅聚合不成 unit;body 的松散文本成
  段落 unit;无 html 根记 `no_html_root` error(防非 HTML 字节空成功)。
- 索引约定对齐现有 PDF 解析:page/slide 1-based;table/row/column 0-based;
  source_role `company_filing`。
- 资源上限超限 → 抛 `NormalizationLimitError`(含字段名与上限),绝不静默截断;
  ZIP 成员上限固定 10,000;deadline 用 `time.monotonic()` 绝对值,协作式检查。
- 无 OCR/模型/网络/磁盘写;不落地全文 MD 与拆页图片;`OpaqueAsset.original_bytes`
  仅内存且 repr 不含字节。
- 性能:真实 10-K 全链(parse 5.1s + 单 unit 回放 ~7.5s);cell 坐标查表已加
  表/行级缓存(修复前 17.9s → 4–5s)。

## 默认 limits(可按部署调整,但必须有限)

`max_source_bytes=64MiB`、`max_total_uncompressed_bytes=512MiB`、
`max_text_output_bytes=16MiB`、`max_units=20000`、`max_pages=5000`、
`max_media_bytes=256MiB`、`deadline=None`(可选绝对 monotonic)。

## 已核实的既有能力与接线事实（详见 findings）

- canonical Worker 现拒 HTML/PPTX：`automation/narrative_select.py:300` 只接受 `application/pdf`；MAIN 负责接线。
- bs4 4.14.3 / lxml 6.1.1 / python-pptx 1.0.2 已在 requirements，无需新增第三方依赖。
- 真实原件（已验 SHA，只读）：
  - HTML: `companies/微软/raw/financial_reports/annual/微软_10-K_2025.htm`，8,158,067 B，`99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe`（SEC inline XBRL 10-K FY2025，经 catalog.sqlite3 locations 只读查询定位，storage=company_wiki_verified_raw）。
  - PPTX: `revenue-forecast/output/cross-market-rf-e2e-2026-10-08/objects/c0/c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`，4,016,522 B，SHA 同名（MSFT FY2027 segments metrics，图片型；delivery_archive_index.json 登记为 retained_object）。
- `source_reader`(filing_reuse)为只读内存返回,无 DB 写;测试入口默认直接用上述路径 + 先验 SHA,不依赖固定本机目录(路径作为 CLI 参数)。
