# MB-CWP 模块归属清单（本轮交付时点）

基线 `08dfe8bf1`；本轮 tip 见 handoff。`src/company_wiki` 共 489 个 Python 文件（本轮新增 10：stream/canonical/readiness/link/recovery CLI 与模块、cn_primary_issuer；`source_catalog` 251）。本清单回答卡上"活动入口、逻辑模块、公开面、状态owner、依赖方向、兼容/退休分类"的交付要求；与 `review/cwp_architecture.md` §1/§5 不一致处以本清单为准（标注差异）。

## 1. 活动交付入口（全部有归属）

### 1.1 wheel console scripts（pyproject `[project.scripts]`，11 个）

| 入口 | 模块 owner | 依赖层 | base 可启动 |
|---|---|---|---|
| company-wiki-source-export | `source_contract.cli` | contract | 是 |
| company-wiki-collect-announcement | `source_catalog.announcement_cli` | catalog | 是 |
| company-wiki-source-catalog | `source_catalog.cli` | catalog+extras | 否（需 catalog extra：bs4） |
| company-wiki-source-read | `source_catalog.source_reader_cli` | catalog | 是 |
| company-wiki-source-query | `source_catalog.source_query_cli` | catalog | 是 |
| company-wiki-company-sources | `source_catalog.company_source_index_cli` | catalog | 是 |
| company-wiki-source-export-v2 | `source_catalog.source_export_v2_cli` | catalog | 是 |
| company-wiki-identify | `source_catalog.identity_cli` | catalog+extras | 否（需 catalog extra：bs4） |
| company-wiki-transcript-import | `source_catalog.transcript_import_cli` | catalog | 是 |
| company-wiki-narrative-read | `automation.narrative_transport_cli` | automation+extras | 否（需 catalog extra：lxml/bs4/pptx） |
| company-wiki-narrative-batch | `automation.narrative_batch_cli` | automation+extras | 否（同上） |

### 1.2 公开 module CLI（非 console script，同 wheel 交付）

| 入口 | owner |
|---|---|
| `python -m company_wiki.source_catalog.processed_document_cli` | source_catalog processed-document port |
| `python -m company_wiki.source_catalog.financial_statements.cli` | source_catalog financial_statements |
| `python -m company_wiki.source_catalog.source_stream_cli` | source_catalog 大原件流式读取（本轮恢复；2.2 双回执协议） |
| `python -m company_wiki.source_catalog.public_document_browser_cli` | source_catalog pathless 文档浏览（主线已有） |
| `python -m company_wiki.source_catalog.public_canonical_browser_cli` | source_catalog canonical issuer→document 浏览（本轮 T-CANON 移植；Dashboard `cwp.py:213` 消费） |
| `python -m company_wiki.source_catalog.public_source_readiness_cli` | source_catalog SourceRef readiness 诊断（本轮 T-B33 移植） |
| `python -m company_wiki.source_catalog.public_legacy_source_link_cli` | source_catalog legacy path key→exact source（本轮 T-B33 移植） |
| `python -m company_wiki.source_catalog.public_legacy_source_recovery_cli` | source_catalog legacy 原件 preview/apply 恢复（本轮 T-B33 移植；只读 preview 默认） |

### 1.3 进程入口（子进程组合，owner 启动）

- `automation.narrative_worker_factory.create_runtime` — AUTO worker 子进程唯一组装点（handler registry、共享 PdfReading、normalization、预算工厂注入点）。
- `automation.narrative_batch.run_batch` / `narrative_batch_cli` — 有限批次协调（单 AUTO ledger/outbox）。
- `source_catalog._paragraph_worker`、`document_normalization.isolated_ocr` — 受限子进程 worker（OCR/段落），由 owner 拉起。
- `scripts/source_catalog_worker.ps1`（经 `source_catalog/control.py` launcher 字段）— 历史启动器，`tests/contract/test_layer_public_boundaries.py:240-302` 已限边；不构成新入口。

### 1.4 base/extra 适用表（CWP-04 交付）

- base（7 个 console + 0 个 module CLI）：source-export、collect-announcement、source-read、source-query、company-sources、source-export-v2、transcript-import。测试：`tests/contract/test_module_owner_isolation.py::test_base_console_modules_import_without_optional_sdks`（13 个可选 SDK 全部拒载）。
- catalog extra 才可启动：source-catalog、identify、processed-document、financial-statements、narrative-read、narrative-batch（lxml/bs4/python-pptx 经 `document_normalization` 急切导入链与 `security_listing_evidence`）。
- pdf extra：真实 PDF 解析（pymupdf 缺失 → `PDF_DEPENDENCY_UNAVAILABLE` 具名失败，`test_optional_pdf_dependency_does_not_affect_non_pdf_composition` 已证）。
- 安装证明：`tests/contract/test_installed_public_entrypoints.py`（wheel 构建→精确路径安装→13 入口启动→包内资源加载→site-packages 导入身份）。

## 2. 七责任 × 模块归属（canonical / 兼容 / 退休）

| 责任 | 模块 | 状态 | 状态 owner / 公开面 | 允许依赖 |
|---|---|---|---|---|
| 契约 | `source_contract`（14 文件） | canonical | SourceRef/VerifiedContent/SourceChunkSink/SourceVersionPort/SourceExportBundleV2；schemas 包数据 | 标准库+契约资源；`announcement_collector/cli` 两个模块是受控兼容 shim（惰性转发 source_catalog） |
| 中立模型 | `document_model`（7） | canonical | NarrativeUnit/DocumentStructure/NarrativeEvidencePackage；本轮起 owned wire metadata 构造期快照，`reading_layout`/`native_source_view` 为借用上下文 | source_contract |
| 规范化 | `document_normalization`（29） | canonical | normalize_document/normalize_verified_document/replay_*；OCR 配置只经 `NarrativeNormalization.from_snapshot/from_project/deferred_from_project` | 契约+中立模型+共享预算；子进程 OCR adapter |
| PDF adapter | `parser_adapters`（6） | canonical | adapt_pdf_pages/adapt_pdf_extract_v3/validate_native_pdf | 契约、canonical_ingest.ParserResult、解析依赖 |
| DU | `document_understanding`（81） | canonical | understand_units/build_observation/build_dependency_packages/build_summary_input；新进程隔离 probe 保留 | 契约+中立模型+共享预算；不读原件、不调模型 |
| Catalog/原件 | `source_catalog`（242，含本轮 stream CLI） | canonical | lazy SourceCatalog/SourceVersionReader；query_ref/open_described_version/stream_version/verify_version；financial_statements 三表 CLI；本轮恢复 source_stream_cli | 下层五包+共享基础设施；不依赖 automation |
| AUTO/发布 | `automation`（66） | canonical | register_narrative_handlers/run_batch/NarrativeTransportReader/WorkerRuntime；单 AUTO DB 任务状态 owner | 仅经来源/处理/发布契约调用上游；中立类型直连 source_contract（本轮） |
| legacy writer | `ingest.py`、`legacy_research_ingest.py` | **退休（冻结）** | 冻结历史 writer；`collect_news.py`/`ingest.py` 按 AGENTS 不作新入口；src 内无人导入（已核） | 不得新增调用 |
| legacy wiki | `wiki_repository.py` | **兼容（只读）** | legacy Wiki 投影，只读兼容 | — |
| legacy 调度/存储 | `scheduler.py`、`run_store.py`、`migration.py`、`deployment.py` | **兼容（历史执行包）** | 旧执行包读取/迁移兼容；不新增调度 | — |
| legacy 研究语义 | `domain.py`、`graph_adapter.py`、`quality.py`、`routing.py`、`proposal.py`、`question_model.py`、`question_registry.py`、`source_registry.py` | **退休（冻结）** | 研究/评估语义归 StockWiki；仅兼容引用 | 不得新增研究 writer |
| 配置 | `config.py`、`model_config.py` | canonical（共享配置） | `Config.load(validation_scope=)`、models.yaml 单一 profile 源 | — |
| 进程/IO 基础 | `atomic_file.py`/`_atomic_file.py`、`bounded_process.py`/`_bounded_process.py`、`file_mutex.py`/`_file_mutex.py`、`process_tree.py`/`_process_tree.py`、`id_scope.py`/`_id_scope.py`、`file_usage.py`、`_atomic_path.py` | canonical | 公开薄名 → `_` 实现名重导出（`tests/contract/test_layer_public_boundaries.py` 限定六条历史 shim 边） | 标准库 |
| 共享值 | `canonical_ingest.py`、`narrative_subject.py`、`wire_json.py`、`implementation_identity.py`、`resource_budget.py` | canonical | wire JSON/主题绑定/算法身份/预算（本轮加 `document_work_budget_factory`） | resource_budget→implementation_identity（唯一根间边） |

## 3. 简明依赖规则

1. `source_contract` 不 import 任何其它 company_wiki 包（除受控 announcement shim 惰性转发）。
2. `document_model`、`document_normalization`、`parser_adapters`、`document_understanding` 只依赖 source_contract/共享值，互不依赖，不依赖 source_catalog/automation。
3. `source_catalog` 可依赖下层五包；不依赖 automation。automation 可依赖 source_catalog 公开面与 source_contract；中立类型（SourceRef/VerifiedContent/SourceReadError）一律直连 `company_wiki.source_contract`（本轮起 automation 层已迁移）。
4. 物理 DB/路径/CAS 只由 source_catalog 持有；AUTO DB 只由 automation 持有；互不写对方状态。
5. OCR/预算等部署配置只在 composition root（transport CLI、worker factory、batch CLI）读取一次后注入；算法模块不得反查 reader/catalog/环境。
6. 根模块间唯一允许的内部边：`resource_budget → implementation_identity`；其余根模块互不依赖（AST 已核）。
7. 上游 shim（`_`→公开名、legacy compat 重导出）按 `test_layer_public_boundaries.py` 现行白名单保留，不新增。

## 4. 与 cwp_architecture.md 的差异更正

- §1 中 "`source_catalog`（241）" 现为 242 文件（stream CLI 回归）。
- §3 CWP-01/02/03/04 已在本轮关闭（见 handoff 各项）。
- §5 阶段 2（中立模型 owned/borrowed）本轮以别名变异测试关闭；阶段 1（契约 CWP-03）关闭；阶段 3（规范化注入）关闭；阶段 4（预算注入）关闭；阶段 7（安装验收）关闭。阶段 5（DU）无新缺口证据，保留现有新进程隔离；阶段 6（Catalog）单 DB/CAS 未动。
