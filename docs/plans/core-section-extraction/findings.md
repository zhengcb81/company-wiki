# 研究发现 — 核心章节提取

> 调研日期：2026-08-06 ｜ 关联：`task_plan.md`、`progress.md`
> 行号会随代码漂移，动手前以实际代码为准。

## 发现 1：项目有两套平行、未打通的文档处理栈

| 栈 | 位置 | 章节能力 | 状态 |
|---|---|---|---|
| 规范栈 | `src/company_wiki/source_catalog/` | **无章节维度**，evidence_spans 只到 page/paragraph/table-cell；normalized.md 有 `#` 标题但无结构化章节索引 | 活跃，invest/revenue/filing-fetch 全靠它 |
| 遗留栈 | `scripts/section_discovery.py` + `stage2_structure.py` + `pdf_extract_v3.py` | 有完整中文标题章节发现 + 关键词映射 + DOC_TYPES.required_sections | 被 `writer_policy` 冻结，直接 CLI 需双因子 |

关键：已存在可复用的中文财报章节知识（标题正则 + required_sections 关键词 + doc_type→section 映射），但在遗留栈，规范栈零引用。

## 发现 2：遗留栈的章节知识是现成的、中文财报验证过的领域知识

- `scripts/section_discovery.py:19-26`：`SECTION_PATTERNS` —— `第X节/章`、`一、`、`（一）` 标题正则 + `discover_sections`/`get_section_content`。
- `scripts/stage2_structure.py:372-388`：`section_keywords` —— 管理层讨论与分析/经营情况讨论与分析→`management_discussion`(high)、业务概要/主要业务→`business_overview`(high)、业务与技术→high。
- `scripts/pdf_extract_v3.py:36-55`：`DOC_TYPES.required_sections` —— annual_report→[管理层讨论,财务报告]、semi_annual_report→[管理层讨论,主要会计数据]、**prospectus→[业务与技术,财务会计信息]**。
- 冻结的是"直接跑遗留 CLI 写研究产物"，**不是复用其无副作用的正则/关键词**。本计划独立重写（不 import 遗留代码），彻底干净。

## 发现 3：Spike 验证 — 独立正则在真实 normalized.md 上召回 100%

脚本 `_spike_sections.py`（项目根，临时，跑完待删），独立正则 `^\s*(第[一二三四五六七八九十百千]+[节章])\s+(.{2,40}?)$` + 关键词表，对真实 normalized.md：

| 文档 | 定位到的核心章节（全 HIGH 命中） |
|---|---|
| 年报 七一二 2018/2019（12 节全识别，零噪音） | 第三节 公司业务概要(业务)、**第四节 经营情况讨论与分析(MD&A)**、第十一节 财务报告 |
| 半年报 万华化学 2025（8 节全识别） | **第三节 管理层讨论与分析(MD&A)**、第八节 财务报告 |
| 招股书 七一二 IPO（17 章全识别） | **第六章 业务与技术(业务)**、第十一章 管理层讨论与分析、第四章 风险因素 |

关键验证点：
- MD&A 两种标题变体（管理层讨论 / 经营情况讨论）都被关键词覆盖 ✅
- 招股书用"第X**章**"非"节"，正则 `[节章]` 覆盖 ✅
- normalized.md 质量足够（百万字 body、章节标题清晰成行）✅
- 召回 100%、零噪音 ✅

## 发现 4：实现细节（artifact_role / worker / evidence 对齐）

- **artifact_role 是自由字符串，无 CHECK 枚举**（`store.py:121`）；UNIQUE 四元组 `(document_id,artifact_role,generator_name,generator_version)`（`store.py:132`）。加 `"sections"` 不改 DDL、不改 admission。
- **无专用 store 方法写 artifact** —— normalizer 直接在 `store.transaction()` 里裸 INSERT SQL（`normalizer.py:1601-1631`，`ON CONFLICT(...) DO UPDATE`）。section_extractor 照抄。
- **worker 集成**（首版不做，记 Phase 4）：`SourceOnlyStage` 枚举 `scheduler_policy.py:30-37` + `_STAGE_CONTRACTS:52-63` + `WorkerConfig` dataclass `worker.py:22-49`（`fingerprint_backfill_batch_size:42` 为范本）+ `load_worker_config` schema 分支 `worker.py:158-173`/构造 `:195-219` + run_cycle 批处理步骤 `worker.py:594-709`。加一个 stage 要改约 7 处。`_FORBIDDEN_DISPATCH_TOKENS`（`scheduler_policy.py:12-23`）禁投研词，`extract_sections`/`SECTION_EXTRACTING` 不触雷。
- **evidence 对齐**（首版不做，记 Phase 5）：`char_start/char_end` 只在 PyMuPDF 页面感知路径有（`parser_adapters/pdf_page_aware.py:340-366`，相对整篇 body 偏移）；docling `_docling_markdown`（`normalizer.py:898-963`）整页聚合、char 全 None → 只能退化 page 级 + 子串匹配。`list_spans`（`evidence_query.py:366`）无 page 过滤参数，按 page 筛要客户端过滤或扩契约。
- **关键语义**：normalizer 重跑会 `DELETE FROM evidence_spans WHERE document_id`（`normalizer.py:1576`）—— 所以 section evidence spans 会被清空、需重跑。section 提取必须在 normalize 之后（依赖链天然成立）。

## 发现 5：消费方现状（缺口即本功能价值）

- filing-fetch 交给 agent 的是 capture-ready handle（document_id + 路径），**只到"文件就位"为止**。
- `revenue-forecast` 的 `company_wiki_source.py` **不在 company-wiki 仓**（在 revenue-forecast skill 内），其 `page_or_section: str` 参数靠 agent **手工填**，不解析不切片。
- agent 读 normalized.md 是直接读 `derived/{sha[:2]}/{sha}/normalized.md` 整篇。
- ⇒ 消费方**强烈需要但缺** "MD&A 章节"结构化输入。本功能补这个缺口；消费方对接 = agent 通过 `sections-list` CLI 或 `SectionQueryService` Python API 读 sections artifact。

## 发现 6：单写者三件套（复用，不引新并发面）

- 进程级：`CatalogOperationLock(catalog_dir, operation=...)`（`service.py:108` / `lock.py:355`）
- SQLite 级：`store.transaction()` = `BEGIN IMMEDIATE`（`store.py:824-851`）
- 线程级：worker 单线程 `run_cycle`（`worker.py:580-727`）
- 只读：`EvidenceQueryService` 用独立只读连接（`evidence_query.py:388`），不经 transaction、不碰锁。
- ⇒ section_extractor 所有写走这条管道，所有读走独立只读连接，天然合规。

## 关键模板代码引用

| 用途 | file:line |
|---|---|
| `_atomic_write`（.tmp+os.replace） | `normalizer.py:1359-1366` |
| `_NORMALIZER_NAME` 命名风格 | `normalizer.py:44` |
| 选文档 SQL（JOIN artifacts existing WHERE IS NULL） | `normalizer.py:1412-1430` |
| artifact INSERT ON CONFLICT | `normalizer.py:1601-1631` |
| service lock 包装范本 | `service.py:108-123`（backfill_text_fingerprints） |
| CLI 子命令注册+dispatch 范本 | `cli.py:206-210` / `:649-650`（fingerprint-backfill） |
| 只读 CLI 范本 | `cli.py:312-319` / `:792-798`（evidence-list） |
| `ProcessingReport` / 版本常量 | `models.py:13,149-184` |
| 测试 fixture 模板 | `tests/contract/test_source_catalog_text_fingerprint.py:41-58` |
