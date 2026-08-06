# 核心章节提取器（section_extractor）— 实施计划

> 状态：**核心三件套完成并通过真实库端到端验证（Phase 1-3 全绿，414 passed，Ruff+compileall 绿，三类真实文档 extract + sections-list 通过）** ｜ 创建：2026-08-06 ｜ 位置：docs/plans/core-section-extraction/
> 关联：`findings.md`（调研）、`progress.md`（进度）
> plan-mode 批准原版：`C:\Users\郑曾波\.claude\plans\abstract-churning-matsumoto.md`

## Context（为什么做）

用户要从年报/半年报/招股书抽取**核心章节**——管理层讨论与分析（MD&A）、业务概要/主营业务、招股书"业务与技术"——**用于投资研究分析**。经澄清，这**不是** CW-2.28 的 `text_fingerprint` 语义去重（已降级，让 worker 自然消化），而是规范栈缺失的**章节内容提取**。

规范栈 evidence_spans 无章节维度、消费方（invest/revenue/filing-fetch）读整篇靠 agent 手填章节字符串；遗留栈有完整中文财报章节正则但被冻结。**Spike 验证**：独立重写正则在真实 normalized.md 上召回 100%、零噪音（详见 findings.md）。

## 首版范围（核心三件套）

① 正则切分模块 ② `extract-sections` 写 artifact + CLI ③ `sections-list` 只读查询。**不含** worker 自动批、不含 evidence span 溯源（列后续）。**只处理已有 normalized.md 的文档**（不自己解析 PDF，未 normalize 的随 worker 解锁）。

## 设计

### 章节集（role 映射，spike 验证）
- `mda` ← 管理层讨论与分析 / 经营情况讨论与分析
- `business_overview` ← 业务概要 / 主要业务
- `business_and_technology` ← 业务与技术（招股书）
- 其他命中（财务报告/风险因素等）识别但标 low

### 产物
```
{catalog_dir}/derived/{sha[:2]}/{sha}/sections/
  index.json   # [{role, title, ordinal, char_start, char_end, page_start, page_end}]
  mda.md / business_overview.md / business_and_technology.md
```
+ artifacts 表一行 `artifact_role="sections"`，metadata_json 存 index 摘要。

## Phase 1：正则切分模块 — 状态：completed ✅（8 单元测试全绿）

**目标**：纯函数切片，零写盘，可独立单元测试。

- [ ] 新建 `src/company_wiki/source_catalog/section_extractor.py`：
  - 常量 `SECTION_EXTRACTOR_NAME`/`SECTION_ARTIFACT_ROLE="sections"`/`SECTION_RE`/`SECTION_KEYWORDS`
  - `SectionSlice` dataclass（role/title/ordinal/char_start/char_end/page_start/page_end/body）
  - `extract_sections_from_text(text) -> list[SectionSlice]`（剥 frontmatter + 正则 + 关键词映射）
- [ ] `models.py` 加 `SECTION_EXTRACTOR_VERSION = "1.0.0"`
- [ ] 单元测试：合成文本断言（MD&A 两变体、招股书"第X章"、子节"一、"、噪音过滤）
- **验证**：`pytest tests/contract/test_source_catalog_section_extractor.py -k regex`

## Phase 2：写入 + service + CLI + 集成测试 — 状态：completed ✅（集成测试 + 幂等 + force 全绿）

- [ ] `extract_sections_catalog(config, store, *, limit, document_id, document_kind, force, progress, should_stop) -> ProcessingReport`
  - 选文档 SQL（模仿 `normalizer.py:1412-1430`）：JOIN artifacts normalized（已有）LEFT JOIN artifacts sections（无）WHERE document_kind IN (...) AND sections.artifact_id IS NULL
  - 读 normalized.md → 切片 → `_atomic_write` 产物（模仿 `normalizer.py:1359-1366`）→ `store.transaction()` INSERT artifacts role='sections'（抄 `normalizer.py:1601-1631` SQL）
- [ ] `service.py` 加 `extract_sections(...)`，`CatalogOperationLock(operation="extract_sections")` 包装（模仿 `service.py:108-123`）
- [ ] `__init__.py` 导出 `SectionSlice`、`SECTION_EXTRACTOR_VERSION`
- [ ] `cli.py` 注册 `extract-sections --limit/--document-id/--document-kind/--force`（模仿 `fingerprint-backfill` :206-210/:649）
- [ ] 集成测试（tmp_path）：scan + normalize + extract_sections；断言 artifacts role='sections' 行 + index.json + **幂等**（重跑行数不变）
- **验证**：`pytest tests/contract/test_source_catalog_section_extractor.py`

## Phase 3：只读查询 + 回归 + 清理 — 状态：completed ✅（SectionQueryService + sections-list CLI + 414 全量回归 + 真实库三类文档端到端验证通过）

- [ ] `section_query.py` `SectionQueryService.list_sections(document_id)`（模仿 `EvidenceQueryService` 只读连接）
- [ ] `cli.py` 注册 `sections-list --document-id`（模仿 `evidence-list` :312-319/:792-798）
- [ ] 真实文档验证：七一二年报 / 万华半年报 / 七一二招股书 `extract-sections --document-id` + `sections-list`
- [ ] 全量回归：`pytest tests/contract/test_source_catalog_*.py` + Ruff + `compileall`
- [ ] 清理临时脚本 `_spike_sections.py`（`_observe_backfill.py` 待后台观测结束删）

## 复用的现有实现（不重写）

| 用途 | 来源 |
|---|---|
| artifact 写入 SQL（ON CONFLICT 四元组） | `normalizer.py:1601-1631` |
| 选文档 SQL（JOIN artifacts existing） | `normalizer.py:1412-1430` |
| `_atomic_write`（.tmp+os.replace） | `normalizer.py:1359-1366` |
| service lock 包装 | `service.py:108-123`（backfill_text_fingerprints） |
| 只读查询服务 | `EvidenceQueryService`（`evidence_query.py`） |
| `ProcessingReport` / 版本常量风格 | `models.py:13,149` |

## 约束（单写者/单线程，天然合规）

- 写 artifacts：`CatalogOperationLock` + `store.transaction()`（BEGIN IMMEDIATE）—— 复用 normalizer 已验证三件套，**不引入新并发面**
- **绝不 DELETE evidence_spans**（只 UPSERT artifacts；首版不写 evidence_spans）
- 只读查询走独立只读连接（不经 transaction）
- `extract-sections` CLI 与 worker 互斥；worker 在跑时 `CatalogOperationLockedError`（选空闲窗口）

## 风险

- worker 在跑时 extract-sections 秒败 → 手动触发，选空闲窗口
- 未 normalize 的文档无 normalized.md → 随 worker normalize 自然解锁
- 标题变体召回 → spike 已验证主流；上线后监控未命中，扩关键词

## 后续（非首版，记 ADR/TODO）

- Phase 4：worker 集成（normalize 后自动产 sections，改 `scheduler_policy.py`/`worker.py` 约 7 处 + config schema 升级）
- Phase 5：章节→evidence_spans 映射（PyMuPDF char 对齐，docling 退化页级）
- "主营业务分析"子节级精度（首版产 MD&A 整节，已含主营业务分析子节）
