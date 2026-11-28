# 全 12 模块逐仓目标架构、解耦重构、日志硬化与 E2E 实施蓝图

> **定位**：本文档是 [task_plan.md](task_plan.md) 的**逐仓施工设计详图**，为全部 12 个模块逐一规定：目标包结构与单向 DAG、公开 `Protocol` 端口边界、巨石拆分与伪技巧清退清单、全入口日志/脱敏接线表、硬编码消除方案、以及七维真实 E2E 与 CI 改造清单。
> **验收**　各仓按改动范围从 [验证规范](anti-trick-governance.md) 选取适用的行为证明与回归测试。文件规模用于定位职责混杂。
> **状态**　各仓实际候选、独审、测试和发布以[进度台账](progress.md)为准。阶段依赖和验收顺序见[总计划](task_plan.md)。

---

## M01. `company-wiki`（CWP，`master@67bd4ff4d`）

### 1. 目标分层架构与单向 DAG（彻底解体 267 文件扁平 `source_catalog` 与 18 个 SCC）
```text
src/company_wiki/
├── source_contract/          # Layer 0: 纯值/Schema/错误码/SourceRef（零 IO、零数据库、零上层导入）
├── document_model/           # Layer 0: NarrativeUnit / Locator 纯值模型（零 IO）
├── resource_budget/          # Layer 0: WorkBudget / ReadBudget / BudgetPolicy 纯值预算
├── common/                   # Layer 1: 唯一公共原语（atomic_file, bounded_process, file_mutex,
│                             #          diagnostic_logging, diagnostic_redaction, cli_runtime, settings）
├── catalog_storage/          # Layer 2: 唯一 SQLite Owner（connection_factory, reader, migrations,
│                             #          document_repo, version_repo, location_repo, identity_repo）
├── parser_adapters/          # Layer 2: PDF/OCR/Office/HTML 解析适配器（唯一允许懒加载可选重型 SDK）
├── document_normalization/   # Layer 3: 规范化流水线（只消费 parser_adapters + document_model）
├── document_understanding/   # Layer 3: 纯阅读引擎（只消费 document_model + profiles，零磁盘/DB）
├── acquisition/              # Layer 4: 采集编排（dayu/sid/et/sina 适配器经 bounded_process + catalog_storage 公开端口）
├── projection/               # Layer 4: 只读投影（query, browse, export_v2, narrative_evidence, processed_document）
├── automation/               # Layer 5: 有限叙述任务与 AUTO 账（unit_of_work + event/job/attempt/narrative_run repo + 生命周期监听器）
└── app/                      # Layer 6: 唯一组合根与 CLI 入口（装配全部 11 个 console_scripts + scheduled_reading）
```
- **严格依赖方向**：`Layer 0` ← `Layer 1` ← `Layer 2` ← `Layer 3` ← `Layer 4` ← `Layer 5` ← `Layer 6`；同层子包互访必须经该子包 `__init__.py` 显式 `__all__` 门面。
- **必须清退的 8 条 `_COMPATIBILITY_PORTS` 与 18 个 SCC**：
  1. `source_contract/announcement_collector.py` → 反转：在 `source_contract` 定义 `AnnouncementDownloadPort(Protocol)`，由 `acquisition` 实现并在 `app/cli` 注入；移除对 `source_catalog` 向上导入。
  2. `source_catalog/cli.py` & `incremental_cli.py` → `scheduled_reading`、以及 `source_catalog/narrative_transport_cli.py` → `automation`：全部迁入 `app/cli.py` 组合根；旧模块路径保留 3 行纯 CLI `__main__` 转发（不作为库导入目标）。
  3. `document_normalization/pdf_table_observations/adapter.py` → `document_understanding` 与 `document_understanding/decision_inventory.py` → `source_catalog`：把共享纯值契约下沉到 `document_model`，删除两个向上垫片。
  4. 破除 5 个核心大环：9 文件 `source_catalog` 环（拆存储仓储与查询投影）、9 文件 `narrative_*` 环（抽 `narrative_types.py` 纯值叶）、8 文件 `du.profiles` 环、7 文件 `du.structure` 环、5 文件 `du.operating_states` 环（抽 `models.py` 叶子模块，移除全部函数体循环导入）。
  5. `automation/store.py`（2,011L）拆为 `unit_of_work.py` + `event_repo.py` + `job_repo.py` + `attempt_repo.py` + `narrative_run_repo.py`，用 `AttemptLifecycleListener(Protocol)` 替换 `if job.job_type == "source.narrative_*"`（`:1303,1321`）。
  6. `source_catalog/store.py:624-631` (`read_pipeline_status`) 改走 `catalog_storage.reader.ReadOnlyCatalogReader`（唯一 SQLite 打开点，必挂 tolerant text decoding + URI 转义）。
  7. `dayu_cli_adapter.py:220-260` 彻底删除原始 `Popen(PIPE, PIPE)` 循环，改调公开 `common.bounded_process.run_bounded(...)`（显式环境白名单过滤 `RESEARCH_FEEDBACK_*` 与无关 API Key、Job Object 回收孙进程）。
  8. `tools/pre_push_gate.py`、`tools/run_source_system_tests.py` 改为导入公开 `company_wiki.bounded_process`；冻结的 `scripts/` 历史遗留 100+ 文件按用户决定隔离至 `legacy_scripts/` 并从活动源码边界剥离。

### 2. 硬编码清零与质量硬化
- 新建 `common/cli_runtime.py` 统一收口 10+ CLI 重复代码，并**强制执行 `max_request_bytes`**（修复 `source_query_cli.py:22,47`、`official_source_cli.py:21,39` 等 8 处死常量/无界读取）。
- `config/source_acquisition.yaml` 与 `acquisition_config.py`：用 env/配置解析替换硬编码 Windows `.venv/Scripts/python.exe` 与 `../StockInfoDLSimple`，三市场表改为配置驱动映射；移除 `runtime_config.py:464` `"~/company-wiki"`。
- `narrative_business_meaning.py` 硬编码双语领域词表迁移为版本化 JSON 策略资源文件（受 schema 校验）。
- `pyproject.toml` 分层启用 `mypy` 真实跨模块检查（逐层关闭 `follow_imports = "skip"`）。

### 3. 全入口日志与错误边界
- 修复 `runtime_feedback.py:120,341` & `runtime_trace.py:85`：移除 `warn_on_stderr=False`，日志写盘/轮转失败时输出单行脱敏 `stderr` 告警，不改业务退出码。
- 补齐 3 个 console script（`source_contract/cli.py:143`、`identity_cli.py:71`、`transcript_import_cli.py:238`）的 `record(..., error=exc)` 与 `scheduled_reading.py` 的 `@entry`。
- 升级 `tools/feedback_loop/triage_diagnostic.py:23-43`：允许所有 `company_wiki.*` 及各注册 owner 模块的已声明异常类名保留真实类型名，不再压扁为 `"OwnerException"`。
- 清理 83 处无日志 `from None`（优先 `_bounded_process.py:112`、`source_stream_cli.py:188`、`automation/store.py:998`），`dayu_cli_adapter.py:263,273` 报错先经 `redact_text` 脱敏。

### 4. 量化退出指标与七维 E2E / CI 改造
- **指标目标**：生产 SCC `18 → 0`；`_COMPATIBILITY_PORTS` `8 → 0`；`source_catalog` 外 `sqlite3.connect` `54 → 0`；延迟导入 `1,706 → 0`（除显式 `# optional-sdk:`）；单文件 `2,812 → ≤ 700 LOC`；无日志 `from None` `83 → 0`。
- **行为证明**：B-01（阻断 `sqlite3`/上层导入 `source_contract`/`document_model`/`document_understanding`）、B-02（纯 `Protocol` 替身驱动 `narrative_batch` 与 `processed_document`）、B-03（空目录 wheel 跑满 11 个 console scripts）。
- **CI/E2E**：`.github/workflows/ci.yml` 增加 **`windows-latest` 矩阵**，以 markers 取代 `CI_CONTRACT_CASES`，执行 `tests/e2e/` 与 `tests/integration/test_narrative_runtime_e2e.py`；`source-system.yml` 增加 `src/**` 触发路径；在 `test_layer_public_boundaries.py` 强制断言 `_BOUNDARIES.runtime_import_cycles() == ()`。

---

## M02. `filing-fetch`（FF，`main@4dd4e13ec`）

### 1. 目标分层架构与打包
```text
pyproject.toml                # 补齐 [build-system], [project] (requires-python >=3.11), [project.scripts]
src/filing_fetch/
├── domain/                   # Layer 0: contracts (v1/v2), errors, cwp_error_taxonomy (消费 CWP 导出 schema)
├── ports/                    # Layer 1: CatalogPort, TranscriptPort, StatementsPort, JobStorePort (Protocol)
├── adapters/                 # Layer 2: process_transport, cwp_cli_adapter, et_cli_adapter, json_job_store
├── use_cases/                # Layer 3: resolve_filing, close_gap, companion_transcript, job_runner, scheduled_refresh
├── assurance/                # Layer 3: t3_probes (从 tests/test_e2e_download.py 抽出的正式探针，消除 exec_module!)
├── observability/            # Layer 1: runtime_log (带锁轮转+stderr 兜底), redactor, feedback_outbox
└── cli/                      # Layer 4: fetch_filing_cli, fetch_statements_cli, ff_job_cli, ff_refresh_cli, ff_t3_receipt_cli
```
- **核心重构**：拆分 2,095 行 `scripts/fetch_filing.py` 到上述 5 层；删除 `ff_t3_receipt.py:350-379` `exec_module` 执行 `tests/`；删除 `ff_short_feedback.py:139-140` 对全局 `os.environ.pop` 变异（改传递显式 `env` 字典）；`ff_company_wiki_connection.py:89-93` 改调已安装 CWP 入口而非拼 `PYTHONPATH`；`test_e2e_isolated_wiki.py` 移除直导 CWP 私有 `CatalogOperationLock` 与复制生产 YAML。

### 2. 硬编码与日志硬化
- `ff_scheduled_windows.py:208-212` 补显式 `timeout=`（从 `FFSettings` 读取）；给 `ff_scheduled_refresh`/`ff_job`/`ff_configuration` 加输入字节上限；清理 3 个死 `pause_worker` 参数。
- `ff_job_store.py:348-355` (`JobStore.append_log`) 改为带文件锁的脱敏 `RotatingFileHandler`；`ff_runtime_log.py:134`、`ff_runtime_feedback.py:46,150`、`ff_short_feedback.py:128` 写失败输出单行脱敏 `stderr` 告警；脱敏 `fetch_statements:122`/`ff_job_runner:195`/`fetch_filing:2067` 的 `str(exc)`；清理 `ff_process_transport:145,153` 等 8 处无日志 `from None`。

### 3. 量化指标与 CI/E2E
- **指标目标**：`sys.path.insert` `14 → 0`；延迟导入 `100 → 0`；最大文件 `2,095 → ≤ 500 LOC`；无日志 `from None` `8 → 0`；`mypy` 覆盖 `2 文件 → 100% src/`。
- **CI/E2E**：`quality.yml` 增加 **`windows-latest` 矩阵**（激活 `test_s1_windows_tick_logging.py` 全部 4 用例）；废除 55 文件硬编码 `CI_TESTS`，纳入 **升级支持 schema 2.0** 的 `test_e2e_isolated_wiki.py`、`test_du11_transcript_reuse_e2e.py`、`host_assumption_guard.py` 与离线矩阵烟雾（改本地 `127.0.0.1:0` HTTP 替身，替换全局 socket `sitecustomize`）。

---

## M03. `earnings-transcripts`（ET，`main@672ed1012`）

### 1. 目标分层架构与打包
```text
pyproject.toml                # 新建 PEP 621 打包 + [project.scripts] (et-tool, et-scraper, et-audit, et-translate, et-reader)
src/earnings_transcripts/
├── contracts/                # Layer 0: schemas, config_schema (typed ETConfig), budget
├── providers/                # Layer 1: TranscriptProvider Protocol + fmp_provider, fool_provider, translator
├── storage/                  # Layer 1: atomic_io (fsync + Win32 replace retry), artifact_store, lock (contextmanager)
├── runtime/                  # Layer 2: supervisor (CREATE_NO_WINDOW + JobObject), worker (白名单 launcher), diagnostics
├── observability/            # Layer 1: logging_setup (统一包 logger), feedback_recorder, inbox_delivery, batch_journal
└── cli/                      # Layer 3: tool_cli, scraper_cli, audit_cli, translate_cli, reader_cli (组合根注入 AppContext)
```
- **核心重构**：修复 `reader.py:21,36` 实时 `NameError`；拆解 3 巨石（`transcript_feedback.py` 2,118L、`scraper.py` 1,949L、`transcript_api.py` 1,425L）；移除公开 `main()` 上 5–9 个 `_private` 测试注入参数（改传 `AppContext`）；删除 `tools/run_request_budget_e2e.py` 对 `tests.*` 导入与流劫持；收紧 `retrieval_worker.py:57-72` 为显式白名单 launcher；修复 `retrieval_runtime.py:317` Windows `CREATE_NO_WINDOW` + Job Object 与 `scraper.py:749` 原子写（`fsync` + 去 `exists()` TOCTOU）。

### 2. 硬编码与日志硬化
- 统一 `config.yaml` 与代码中的 FMP `/stable/` 端点、模型/URL/超时到强校验 `ETConfig`，删除 `config.yaml:107,140-152` 硬编码微软产品词，缓存键从 MD5 换 SHA-256。
- 删除 `scraper.py:249` `propagate=False` 使全部子模块汇聚同一轮转日志；补齐 `translate.py`/`reader.py`/`transcript_audit.py`/`make_interleaved.py` 轮转文件日志；`runtime_logging.py:48` 写失败输出 `stderr` 告警；脱敏 `translator.py:236` 并补 `exc_info=True`；修复 `retrieval_diagnostics.py:137` 保留非内建异常类与 `__context__`。

### 3. 量化指标与 CI/E2E
- **指标目标**：`sys.path.insert` `5 → 0`；公开 `main()` 私有参数 `9 → 0`；最大文件 `2,118 → ≤ 500 LOC`；CLI 日志覆盖 `2/6 → 6/6`。
- **CI/E2E**：废除 `ci.yml` 仅跑 4 文件+7 用例的残缺清单，改为 `[ubuntu-latest, windows-latest]` 矩阵执行 `ruff` + `compileall` + `mypy` + **完整 `pytest tests/`**；新增本地 `127.0.0.1:0` HTTP 真实子进程 E2E（覆盖 `reader.py` `GET /`、HTTP 200 断流强杀与孙进程回收、磁盘只读降级告警）。

---

## M04. `StockInfoDLSimple`（SID，`v2-clean-rewrite@5c6560502`）

### 1. 目标分层架构与打包
```text
pyproject.toml                # 新建 PEP 621 打包 + [project.scripts] (sid-batch, sid-cwp-adapter, sid-feedback-owner)
src/stockinfo_dl/
├── domain/                   # Layer 0: models, disclosure_matching, report_metadata (修 1990s/季度规则), exceptions
├── ports/                    # Layer 1: AnnouncementClient, PdfFetcher, FeedbackStore (Protocol)
├── adapters/                 # Layer 2: cninfo_http (统一单 HTTP 栈, 退 orgid.py), playwright_fallback, atomic_io
├── feedback/                 # Layer 2: layout, journal, publisher, owner_service (拆 964L feedback_publish.py)
├── observability/            # Layer 1: logging_setup (无导入副作用, 支持重配, 跨进程锁轮转+脱敏+CorrelationFilter)
└── cli/                      # Layer 3: batch_cli, cwp_adapter_cli (拆 327L _main), feedback_owner_cli
```
- **核心重构**：剥离 `company_wiki_adapter.py` 中旧 `StockDownloader` 与死 SPA 辅助函数；移除 `downloader.py`/`disclosure_matching.py` `_matches_*` 私有重导出别名；合并 3 份异常链提取器为单一环安全实现；删除 `runtime_steps.py:49` 硬读 `main.py` 与 `official_e2e_test.py:69` 失效 V1 导入。

### 2. 硬编码与日志硬化
- 修复 `cninfo_api.py:422-424` 无预算 `fetch_pdf` 补齐 `Content-Length` 截断校验，消除 `:487-489` 先 `unlink` 再 `replace` 窗口，全仓原子写加 Windows 重试。
- 建立强校验 `SidSettings`（缺失显式 `--config` 立即报错、清除 5 个死配置键、收敛 6 文件分散 CNINFO URL、让 `adapter_cli` 消费配置 `max_pages`）。
- 为 `feedback_owner.py`（消除 `:459` 异常擦除）与 `feedback_publish.py` 接入轮转日志；`main.py` 参数解析前即挂早期轮转日志；补齐 27 处 `exc_info=True` 与 11 处 `browser.py`/`orgid.py` 静默吞错。

### 3. 量化指标与 CI/E2E
- **指标目标**：`sys.path.insert` `1 → 0`；延迟导入 `30 → 0`；最大文件 `964 → ≤ 500 LOC`；`errNoExcInfo` `27 → 0`；静默 `except` `11 → 0`。
- **CI/E2E**：废除 `ci.yml` 7 文件+2 用例硬编码清单，升级为 `[ubuntu-latest, windows-latest]` 运行 `ruff` + `mypy` + 完整 `tests/unit` + 新增本地 `127.0.0.1:0` HTTP 子进程离线 E2E（截断 PDF、429/强杀幂等、坏 `--config`、只读日志目录告警、Windows 并发轮转）。

---

## M05. `revenue-forecast`（RF，`origin/main@782cfd9a`）

### 1. 目标分层架构与打包
```text
pyproject.toml                # 新建 PEP 621 打包 + [project.scripts] (rf-forecast, rf-prepare, rf-job, rf-catalog, rf-feedback)
src/revenue_forecast/
├── common/                   # Layer 0: atomic_io (唯一实现), strict_json, pathless_guard, settings
├── contracts/                # Layer 0: document_schema, validation (仅捕领域校验错，透传引擎内部错!)
├── engine/                   # Layer 1: forecast_calc, revenue_core (纯计算，零回调/零底部 E402 向上导 report!)
├── reporting/                # Layer 2: revenue_report (拆 2,137L 及 995L _validate), publication_registry
├── sources/                  # Layer 2: filing_fetch_client, cwp_reader_v2, source_preparation (隔离旧 legacy 适配)
├── catalog/                  # Layer 2: repository (CatalogRepository Protocol + 实现), lineage, importer, publication, compare
├── jobs/                     # Layer 3: models, store, runner (删 FakeStageRunner→tests/doubles/), facade, feedback
├── observability/            # Layer 1: local_diagnostics (跨进程锁+脱敏+stderr 兜底+完整字段), feedback_outbox
└── cli/                      # Layer 4: 统一 @observed_entry 覆盖全部 20+ CLI
```
- **核心重构**：将 1,512 行 `rf_job_facade.py` 拆为 `models`/`store`/`runner`/`facade`/`feedback`（破除 `rf_job_facade <-> rf_job_feedback` 环，将 `FakeStageRunner`/`SimulatedProcessDeath` 迁出至 `tests/doubles/`）；在 `catalog/repository.py` 定义公开 `CatalogRepository(Protocol)` 彻底消灭 `catalog._*`/`store._*` 跨文件私有调用与 `report_catalog*` 环；反转 `revenue_core` 依赖方向删除底部 `E402` 重导出与回调技巧（同步更新 `test_module_boundary_closure.py`）。

### 2. 硬编码与日志硬化
- `contracts/document.py:1210,1258,1316` 改为仅捕显式领域校验异常，内部 Bug 落日志并显式失败；清理生产代码中一次性 W09 / Q3-2026 硬编码与 `slo_probe.py:25,110` 硬编码 `"紫金矿业"` 及假 `bundle = exact[:]`；`cwp_catalog_status.py:51` 改读结构化错误码替代英文前缀匹配；`release_readiness.py:87` 移除 `stderr=DEVNULL`。
- 全部 20+ CLI 接入 `@observed_entry` 与轮转日志；修复 `rf_local_diagnostics.py:72-96` 锁忙/IO 错静默丢弃并补全 `attempt_id`/`code_version`/`input_ref` 与脱敏；修复 `rf_feedback_outbox.py:109` 双失败 `stderr` 告警、`company_wiki_source_reader_v2.py:201` `from None` 前置日志、`filing_fetch_client.py:277` 三表分支 stderr 捕获。

### 3. 量化指标与 CI/E2E
- **指标目标**：SCC `1 → 0`；私有导入 `22 → 0`；私有属性 `19 → 0`；延迟导入 `148 → 0`；生产代码测试替身 `2 → 0`；`sys.path.insert` `18 → 0`；CLI 日志覆盖 `4/20 → 20/20`；`mypy` `5 文件 → 100% src/`。
- **CI/E2E**：废除 75 项硬编码 `CI_TESTS` 改用 markers 自动发现；扩大 `windows-lifecycle` 覆盖 `test_zr902_daily_schedule.py` 与原子替换/长路径测试；新增零 `FakeStageRunner` 真实多阶段子进程强杀恢复 + 迟到旧子进程隔离 + 双写失败告警 E2E；`conftest.py` 全局隔离 `LOCALAPPDATA`/`RESEARCH_FEEDBACK_*`。

---

## M06. `revenue-forecast-audit`（Audit，`main@9e9e98096`）

### 1. 目标分层架构与打包
```text
pyproject.toml                # 新建 PEP 621 打包 + [project.scripts] (audit-run, audit-pool, audit-feedback, audit-sync)
src/rf_audit/
├── core/                     # Layer 0: config (typed AuditConfig), atomic_io (含 Win32 replace 重试), redactor, common_scales
├── capture/                  # Layer 1: input_freeze, runner, capture_state, capture_diagnostic, blob_store
├── pool/                     # Layer 1: sampling, reducer, planner, store (拆 1,339L pool_progress.py)
├── review/                   # Layer 2: contracts, execution_request, document_status_join, review_protocol,
│                             #          financial_measure_core/audit/evidence, summary_review_*
├── observability/            # Layer 1: diagnostics (强制写入点脱敏+跨进程锁+stderr 兜底), delivery, feedback_owner
└── cli/                      # Layer 3: 统一 cli_bootstrap 包装全部 14 个 CLI（skills/ 下保留薄入口同步壳）
```
- **核心重构**：修复 `feedback_owner.py:187` 实时 `NameError`（改为 `select_capture_events`）；拆分 `audit_run.py`（1,361L）与 `pool_progress.py`（1,339L）；破除 `tools/adoption_replay_support/` 6 文件顶层环；清除 16 处 `sys.path.insert`、`spec_from_file_location` 与 `financial_measure_evidence.py:542` `hasattr` 鸭子类型补丁。

### 2. 硬编码与日志硬化
- 升级 `tools/sync_skill.py`：从部署清单读取全部 4 套逻辑目的地（`.agents`/`.claude`/`.codex`/`.gemini/config`）并检测目标目录孤儿漂移文件；修复 `20\d{2}` 漏 1990s 与三币种硬编码；统一 4 处原子写加 Win32 重试；清除 `coverage_observations.py:58` 硬编码 W08 专用名。
- 为剩余 11+ CLI 全部接入轮转日志；`audit_diagnostics.py` 写入点强制脱敏并修复 `doRollover` 静默增长；放宽 `audit_run.py:1317` 捕获未预期异常；`feedback_owner.py:354` 错误输出移至 `stderr` 并保留脱敏原因；`run_pool_progress_e2e.py:218` 移除双 `DEVNULL`。

### 3. 量化指标与 CI/E2E
- **指标目标**：SCC `1 → 0`；`sys.path.insert` `16 → 0`；最大文件 `1,361 → ≤ 500 LOC`；CLI 日志覆盖 `3/14 → 14/14`；自动化门禁 `0 → 100%`。
- **CI/E2E**：新增本地 `tools/pre_push_gate.py`（`.githooks/pre-push`）与 `.github/workflows/ci.yml`（Ubuntu + Windows 矩阵），跑 `ruff` + `mypy` + `unittest discover` + `run_pool_progress_e2e.py`；新增 `tests/test_audit_full_chain_e2e.py` 串联全 7 步真实子进程与 **三家族 (`audit-finding`/`audit-operation`/`audit-capture`) `feedback_owner replay`** + `sync_skill` 孤儿漂移 E2E。

---

## M07. `StockWiki`（`master@0fbaf7ce3`）

### 1. 目标分层架构与单向 DAG
```text
stockwiki/
├── core/                     # Layer 0: settings (零个人路径), sqlite_uri (唯一转义 readonly_connect), contracts
├── storage/                  # Layer 1: 唯一 SQLite Owner — quick_scan_repo, entity_read_repo, observation_read_repo,
│                             #          identity_receipt_repo, assessment_repo (拆 2,565L), normalization_saga
├── domain/                   # Layer 2: assessment_policy, qualification, freshness, market_registry, documents
├── services/                 # Layer 3: work_delegation, onboarding, research_binding, pipeline_planner
├── observability/            # Layer 1: runtime_feedback (全 CLI 接 unavailable_detail + 轮转锁), usage_ledger
└── cli/ & web/               # Layer 4: pyproject.toml [project.scripts] 全部 CLI + ui (有界 POST + 500 脱敏)
```
- **核心重构**：**彻底删除** `_ReadStore`/`_ReadReceipts`/`_ReadOnlyObservationStore` 子类与 Store 外全部 66 处散落 `sqlite3.connect` / 裸 SQL；拆分 2,565 行 `public_company_assessments.py` 为 schema/repo/policy/projection；抽 `quick_scan_contracts` 破除 3 个运行时 SCC（含 `refresh <-> query <-> delivery`），撤销 `test_f05` 中的循环豁免并将边界扫描扩至 **100% `stockwiki/*.py`**；清零 `ui.py:47` 私有导入与 10 处根 CLI `sys.path.insert`；将 `SecurityIdNormalizationStore.complete()` 跨库步骤显式化为可重入 Saga 状态机并在 CI 注入断电回归。

### 2. 硬编码与日志硬化
- 用唯一 `core/sqlite_uri.py` 修复 `dashboard_onboarding.py:145` & `quick_scan_identity.py:151` 实时 `#`/`%` 错库 Bug；移除 `stockwiki/paths.py:11` 个人路径 `C:\Users\郑曾波\Projects`；删除 `dashboard_onboarding.py:502` 死三元与 `quick_scan_store.py:404-415` 3 块重复 `if`；修正 `_save_prepared():402` 越权 `commit()`；给 `ui.py:255` POST 加字节上限；移除 `check_c06_interop.py:15` 硬编码旧 SHA。
- 为 `cli.py`/`ui.py`/`quick_scan_dashboard_cli`/`quick_scan_query_v2_cli`/`feedback_owner` 接入轮转日志；`feedback_owner.py:29` 补 `CREATE_NO_WINDOW`；`ui.py` 开结构化访问日志且未捕获异常返 HTTP 500 脱敏错误码（不再返 400 + 裸 `str(exc)`）；清零 82 处无日志 `from None`（含 `public_company_assessments.py` 26 处）与 10 处静默吞错。

### 3. 量化指标与 CI/E2E
- **指标目标**：SCC `3 → 0`；Store 外 `sqlite3.connect` `66 → 0`；跨域私有导入 `290 → 0`（私有属性 `34 → 0`）；无日志 `from None` `82 → 0`；最大文件 `2,565 → ≤ 600 LOC`。
- **CI/E2E**：废除 `scripts/checks.py` 樱桃采摘 `SHORT_TESTS`，在 `ci.yml` 与本地预推门禁跑满全量 `tests/`（含跨库提交断电、`#`/`%` URI、Windows 轮转与归档保护、Git 无窗），并增加 `windows-latest` 矩阵。

---

## M08. `invest-quick-scan`（IQS，`origin/master@3094c5f7`）

### 1. 目标分层架构与打包（清退 145 个 `sys.modules` 垫片）
```text
pyproject.toml                # 新建 PEP 621 打包 + [project.scripts] (iqs-workbench, iqs-thin-scan, iqs-snapshot, iqs-query)
src/iqs_scan/
├── foundation/               # Layer 0: settings (Typed WorkbenchConfig), file_lock (统一可配置超时), runtime_log,
│                             #          runtime_feedback (保留脱敏诊断摘要), background_process (全覆盖 CREATE_NO_WINDOW)
├── contracts/                # Layer 0: contract_validation (拆分), question_sets, freshness_contract (去 legacy_oracle 跨仓导!)
├── providers/                # Layer 1: provider_transport (有界 response.read + IncompleteRead + 按题作用域), model_invocation
├── workbench/                # Layer 2: config_handler, query_handler, job_facade, batch_handler, prepare_handler,
│                             #          execution_handler (拆 5 个 >950L 巨石，不可变 RequestContext 替 copy.copy(self))
└── cli/                      # Layer 3: 薄组合根 CLI（废除 145 个 scripts/*.py sys.modules[__name__] 垫片）
```
- **核心重构**：彻底删除 `legacy_oracle.py:2-8` 对 `stockwiki.quick_scan_freshness` 的跨仓导入；删除 `tests/test_company_scan_native_e2e.py:48-72` 对 StockQA `tests.*` 的跨仓私有导入；扩大 `test_dashboard_module_boundaries.py` 扫描全包 `src/iqs_scan/`（不再只扫 6 文件）并撤销 `test_shared_public_boundaries.py:825` 永久豁免。

### 2. 硬编码与日志硬化
- 修复 `dashboard_jobs.py:156-168` 80ms 锁重试静默 `break`（接入统一 `foundation/file_lock.py` + 失败必落终态）；移除 `status_report.py:83-85` 个人路径与 `dashboard_service.py:109` 邻仓路径猜测；统一 `open_dashboard.py` 默认端口与 `WorkbenchConfig`（消除 8765 vs 8766 冲突）；移除硬编码 `DEFAULT_PACKAGE`、`"2026-10-18"` 日期、50 处硬编码模型与 28 处硬编码 URL；`provider_transport.py:48` 强制有界读取。
- `runtime_feedback.py:142` 改为保留脱敏后的结构化诊断消息；补齐 `open_dashboard.py` 访问/启动日志与 `CREATE_NO_WINDOW`；修复 `dashboard_http.py:146` 传 `error=exc`；清理 52 处无日志 `from None`。

### 3. 量化指标与 CI/E2E
- **指标目标**：`sys.modules` 垫片 `145 → 0`；跨仓内部导入 `2 → 0`；延迟导入 `280 → 0`；无日志 `from None` `52 → 0`；最大文件 `1,529 → ≤ 600 LOC`。
- **CI/E2E**：废除 `quality.yml` 仅跑 7 文件+1 用例的清单，升级 `[ubuntu-latest, windows-latest]` 跑满 `fast` + `integration` + `e2e`；新增独立真实 HTTP workbench E2E（真实 `open_dashboard` 监听端口 `0` + 本地替身：200ms 锁竞争不困 `'preparing'`、`IncompleteRead`、连续两题独立诊断记录、POST 断流强杀恢复零重复付费、只读日志目录告警）。

---

## M09. `investment-dashboard`（Dashboard，`release-de59feed@de59feed`）

### 1. 目标分层架构（解散 629 行 `DashboardService` 与 37 个 `lambda` 闭包）
```text
backend/dashboard/
├── core/                     # Layer 0: settings (DashboardSettings), errors (OwnerPortError 必带 cause), logging_setup
├── ports/                    # Layer 1: IdentityPort, ResearchPort, CatalogPort, QuickScanPort, ForecastPort, JobPort (Protocol)
├── storage/                  # Layer 1: 唯一 SQLite/文件存储（含 feedback_owner 只读查询，消除 scripts/feedback_owner 直连 SQLite）
├── adapters/                 # Layer 2: 各 owner 适配器无环单向依赖（ChainedIdentityAdapter 替 self._fallback._read();
│                             #          StockWikiResearchAdapter 构造注入 IdentityPort; 拆 1,082L iqs/quickscan.py 为
│                             #          quickscan_link/projection/feedback; 清理 adapters 21 文件环与 35 私有导入）
├── use_cases/                # Layer 3: 独立构造注入服务（ScreenEvaluator, CompanyOverviewService, CapabilityObserver,
│                             #          StatementScopeBuilder）直连 ops/m*.py —— 零 37 lambda 包装！
├── observability/            # Layer 1: request_feedback (跨进程文件锁 + Win32 rollover 保护 + 写后发头防幽灵 correlation_id)
├── transport/                # Layer 4: http.py (缺失 dist fail-fast; HostGuard 记日志; 流式子进程记 child_result)
└── composition.py & main.py  # Layer 5: 唯一组合根（禁吞 adapters.factory ImportError; 禁 --data-dir 退回 Path.home()）
apps/web/src/
├── shared/                   # api.ts (非 JSON 5xx 与超时保 correlationId), components.tsx (<Load> 必展示 correlationId)
└── features/                 # OriginalPreview.tsx (展示 correlationId), Overview.tsx (补 openDestination),
                              # ScreenBuilder.tsx (修快照比对), Documents.tsx (通过 shared 端口解除跨 feature 直导)
```
- 清理 `scripts/f2_dash_feedback_sample.py` 对 `tests._owner_stub` 的导入，归档清理 `handoffs/` 中残留的 9 处跨仓导入历史脚本；对齐 `main`/`origin/main`/`release-de59feed`/PWF 四路分叉并纳入 `npm run build` 自动化发布校验。

### 2. 日志与全链路 `correlation_id` 闭环
- 修复 `request_feedback.py:345-368` (`_RuntimeLog`)：改为带跨进程文件锁 + Windows `PermissionError` rollover 保护的持久处理器（不再每请求开合 5 次无锁 handler）；给 `main.py`/uvicorn/adapters 接轮转日志。
- 彻底根治幽灵 `correlation_id`：`http.py:317` 仅在旁路写盘确认后发射关联头（或显式标 `X-Dashboard-Diagnostic-Recorded: false`）；`main.py:89` 仅在 `diagnostic_written=True` 时打印；前端 `OriginalPreview.tsx:37-41`、`<Load>`、`api.ts:80,106`、`capabilities.ts:46` 全部透传并展示 `correlationId`。
- 为 `adapters/common.py:fail()` 增加强制 `cause` 参数；`cwp_stream.py:115` 接入 `request_feedback.child_result()` 保留流中断后子进程退出码与脱敏 stderr；修复 `service.py:353,529` 吞 `OwnerPortError` 与 `feedback_owner.py:283` 吞错返 exit 0。

### 3. 量化指标与 CI/E2E
- **指标目标**：`lambda` 伪端口 `37 → 0`；adapters SCC `1(21 文件) → 0`；跨文件私有导入 `35 → 0`；生产导入 `tests/` `1 → 0`；4 路版本分叉 → 唯一主线+自动化 `dist` 构建。
- **CI/E2E**：修复 `pyproject.toml:27` `testpaths`（纳入 `tests/adapters` 与根级 `tests/test_*.py`）；扩展 `feedback-contracts.yml`（Ubuntu + Windows）执行 `npm ci && npm run typecheck && npm run test && npm run build` + 全量后端单元/适配器/契约测试 + Playwright 真实浏览器 E2E；将 10 个 `tests/e2e/m*/` 重复服务启动器合并到 `tests/support/factory.py`，新增真实 Chromium 200/206 断流展示 `correlationId`、缺 `dist`/坏 `--data-dir` fail-fast 与 owner 故障注入 E2E。

---

## M10. `StockQAbyLLM`（StockQA，`origin/master@86f633d8`）

### 1. 目标分层架构（解体 7,085 行上帝类与 23 文件巨环）
```text
src/stockqa/
├── core/                     # Layer 0: models, exceptions, settings (ProviderCatalog/RuntimeLimits/PathConfig),
│                             #          dispatch_context (显式不可变上下文，取代 9 全局 ContextVar 与 WeakKeyDictionary)
├── ports/                    # Layer 1: WorkStorePort, OwnerAuthorityPort, BudgetPort, LLMProviderPort (每 Protocol ≤ 15 方法!)
├── storage/                  # Layer 2: 唯一 SQLite Owner — sqlite_engine (含 ReadOnlySQLiteEngine 组合!), migrations,
│                             #          work_item_repo, attempt_repo, budget_ledger_repo, delivery_outbox_repo,
│                             #          owner_refresh_repo, question_pack_repo, research_output_repo (彻底撤 21 文件白名单!)
├── providers/                # Layer 2: llm_client (拆 1,955L, 删重复 MODULE_API_PROTOCOL), llm_provider, async_llm_provider (去 get_event_loop)
├── quick_scan/               # Layer 3: admission, consent, execution, refresh_inspect (组合 ReadOnlySQLiteEngine，删继承+__getattribute__!),
│                             #          delivery_seal, feedback_owner
├── runners/                  # Layer 4: llm_runner (拆 3,687L 及 883L _run_single_company; 删 copy.copy(self) 改私有字段),
│                             #          qa_engine (原子写结果), basic_runner
├── observability/            # Layer 1: logging_setup (控制台改 stderr! 尾段截断保堆栈! 补全脱敏正则!), execution_feedback
└── cli/                      # Layer 5: bootstrap 组合根 + 全部 15 个 CLI 注册至 pyproject.toml [project.scripts]
```
- **强制清除的全部伪解耦技巧**：删除 17 个 `api_work_store_* = _*` 别名与重复 `MODULE_API_PROTOCOL`；撤销 `test_quick_scan_module_boundaries.py` 21 文件 `STORE_SQL_ADAPTERS` 豁免与全局 `sqlite3.connect` 豁免；用 `ReadOnlySQLiteEngine` 组合替换 `ReadOnlyWorkView(QuickScanWorkStore)` 继承+`__getattribute__`；替换 9 个全局 `ContextVar` 与 `WeakKeyDictionary`；消除 `main_with_llm.py:17` 与 `quick_scan_shared_company.py:136` `sys.path.insert`。

### 2. 硬编码与日志硬化
- 集中全部硬编码模型（30 处）、URL（15 处）、`max_output_tokens=8192`（5 处）、租约/超时/CWD 状态文件名到 `Settings`；替换 `asyncio.get_event_loop()` 与裸 `raise Exception`；`qa_engine.py:1034` 改为原子写（`fsync` + `os.replace`）；修复 `config_manager.py:71-87` 补 `from e` 与 `quick_scan_owner_research.py:91` 重复条件；清理 `pyproject.toml:15` 与 `README.md` 占位符。
- `logger.py:588` 控制台流改为 **`sys.stderr`**（删除 6 个 JSON CLI 的 `redirect_stdout` 黑客）；全部 15 个 CLI 与 `feedback_owner.py` 启用轮转文件日志；统一 `quick_scan_owner_research`/`work_decision_authority` 到包 logger 脱离 `propagate=False` 黑洞；`logger.py:407` 2000 字符截断改为**保留尾段堆栈**并补全 URL userinfo/`ghp_`/`AIza` 脱敏；修复 `llm_runner.py:1686` 坏 checkpoint 显式报错落日志、`:2676` 补 `run_id`/`attempt_id`、3 处外部子进程记录脱敏 stderr 尾段、60 处 `exc_info=True`、`async_llm_provider.py:508` 不吞异常。

### 3. 量化指标与 CI/E2E
- **指标目标**：SCC `1(23 文件) → 0`；`STORE_SQL_ADAPTERS` `21 → 0`；延迟导入 `384 → 0`；外部私有属性 `46 → 0`；最大文件 `7,085 → ≤ 600 LOC`；CLI 轮转日志 `4/15 → 15/15`；`errNoExcInfo` `60 → 0`。
- **CI/E2E**：PR/push CI 纳入 `test_q05_content_boundary.py`、全量 `test_execution_failure_diagnostics.py`、全量 `test_execution_feedback_intake.py`、`test_external_context_cli_e2e.py`（25 子进程强杀测试）、`test_live_wal_refresh_readers.py` 并增加 **`windows-latest` 矩阵**；将 `test_quick_scan_cli.py` 内存 `Mock()` HTTP 升级为本地 `127.0.0.1:0` `ThreadingHTTPServer`；新增坏 checkpoint 与 11 二级 CLI 日志活性 E2E。

---

## M11. `industry-research`（IR，`origin/main@77f3c7dd5`）

### 1. 目标分层架构与打包
```text
pyproject.toml                # 新建 PEP 621 打包 + [project.scripts] (ir-quick-scan, ir-deepseek, ir-report, ir-feedback-owner)
src/industry_research/
├── core/                     # Layer 0: settings (Typed DeepSeekConfig + IndustryCatalog，零个人路径!), schemas (统一 evaluation_basis!)
├── quick_scan/               # Layer 1-2: contract (纯 2.7.0 schema), transport (subprocess+分页), projection (纯离线，免 --config!), cli
├── llm/                      # Layer 2: deepseek_client (单一 JSON 提取器 + 原子写 + 接通 --model/--base-url)
├── reporting/                # Layer 2: report_format, report_output (原子写), report_sections, report_generator (用 yaml.safe_load!)
├── observability/            # Layer 1: logging_setup (跨进程锁轮转+脱敏+stderr 兜底), native_feedback, feedback_owner
└── installer/                # Layer 3: 清单驱动技能同步器（含 feedback_owner/config/checklist/modules/templates + 孤儿检测）
```
- **核心重构**：修复 `deepseek_client.py:603` (`evaluation_basis`) vs `report_generator.py:596` (`recommendation_basis`) 共享契约；拆 2,240 行 `quick_scan_client.py` 并让离线子命令脱离 `--config` 依赖；消除 7 处 `try/except ImportError` 双路径黑客；用 `yaml.safe_load` 取代手写 YAML 解析器与 53 行业重复硬编码表。

### 2. 硬编码与日志硬化
- 删除 `config.yaml` 与 `modules/*.md` 全部个人路径 `C:/Users/郑曾波/...`；接通 `--model`/`--base-url`/`DEEPSEEK_*` env；消除 6x 复制粘贴非原子写与 bare filename 崩溃；移除 `report_generator.py` 静默证据截断与死变量 `categories`。
- 为 10 个业务文件与 `feedback_owner.py` 接入跨进程带锁轮转日志（修复 `native_feedback.py:248` 无锁 Windows rollover 竞态与路径重定向忽略）；`deepseek_client.py` 报错迁往 `stderr`；清理 7 处无日志 `from None` 与 7 处丢 `from exc`。

### 3. 量化指标与 CI/E2E
- **指标目标**：最大文件 `2,240 → ≤ 500 LOC`；个人路径 `>10 → 0`；无日志 `from None` `7 → 0`；业务 `logging` `1/11 → 11/11`。
- **CI/E2E**：扩展 `owner-contracts.yml` 为 `[ubuntu-latest, windows-latest]` 跑满全部 15+ 测试文件 + `ruff` + `mypy`；移除 `test_deepseek_boundary.py:38-91` 54 行 `runpy`/`socket` 劫持（改传 `--base-url`）；新增 `extract_framework → evaluate_company → report_generator → render-section → audit-section` 全链 E2E、洁净技能同步 E2E 与并发轮转 E2E。

---

## M12. `MeetingConverter`（MC，`master@7b83fe6f7`）

### 1. 目标分层架构与打包
```text
pyproject.toml                # 修复 build-backend = "setuptools.build_meta"; 移 pytest 至 [optional-dependencies] dev; 补 [project.scripts]
src/meeting_converter/
├── core/                     # Layer 0: config (强校验, 清死字段 translate_batch_size), error_attribution (合并 3 份重复异常链!),
│                             #          atomic_io (补 os.fsync + Win32 重试), exceptions
├── audio/                    # Layer 1: audio_utils (ffprobe 检 returncode + 配置 timeout!)
├── engines/                  # Layer 2: base (EngineEventSource Protocol), mimo, whisper, fallback, factory, provider_exchange
├── translation/              # Layer 2: translator (确定性 __CORR_N__ 占位符替代 hash()), text_merger
├── feedback/                 # Layer 2: schema, storage, state (拆 1,487L core/feedback.py，删全局 _RECORDERS!), local_diagnostics (线程安全)
├── pipeline/                 # Layer 3: pipeline, batch, company (唯一 companies.yaml 原子写 + 报错非零退出)
└── cli/                      # Layer 4: transcribe_cli (配置非法 fail-closed!), company_cli, feedback_owner_cli
```

### 2. 硬编码与日志硬化
- `audio_utils.py:30-45` `ffprobe` 强制检 `returncode` + `timeout`；`transcribe.py:173-188` 配置非法时 fail-closed 不绕过校验；外置 MiMo/Whisper/ffmpeg/Translator 参数到 `Config`；`translator.py:50` 去除非确定性 `hash()`；`core/output.py:131` 补 `os.fsync()`；`company_manager.py` 改原子写且错误路径返回非零退出码。
- `transcribe.py:127-131` 将 `basicConfig` 迁至 `sys.stderr`（含时间戳/级别/脱敏）+ 轮转文件日志，致命错误改 `logger.error`；`core/feedback.py` 告警强制走 `stderr`；为 `feedback_owner.py` 接入 `cli_diagnostics`；使 `local_diagnostics.record_failure` 在库模式生效且无全局 `_LOGGER` 竞态；补齐 13 处 `exc_info=True`。

### 3. 量化指标与 CI/E2E
- **指标目标**：最大文件 `1,487 → ≤ 500 LOC`；重复异常链提取器 `3 → 1`；全局可变 `_RECORDERS` → 0；`stdout` 日志污染 → 0；`errNoExcInfo` `13 → 0`。
- **CI/E2E**：更新 `test_ci_workflow_config.py:79-89` 与 `ci.yml` 允许并运行 **`[ubuntu-latest, windows-latest]` 双 OS 矩阵**（真正执行 Windows 长路径、打开目标阻塞与原子替换回归！）；新增不劫持 `load_config` 的真实 `transcribe.py` + `config.json` CLI 优先级 E2E、本地 `127.0.0.1:0` HTTP 200 断流 E2E、真实 `ffprobe` 失败 E2E 与 `company_manager`/`feedback_owner` 子进程 E2E。
