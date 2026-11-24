# 全 12 模块深度代码审计报告：架构解耦、私有调用与日志可复现性（2026-11-24）

> **审计性质**：严格只读代码审计（**零生产代码修改、零配置修改、零外部请求/付费调用**）。
> **覆盖范围**：本机全部 12 个自有生产模块（**1,654 个生产 Python 文件 / 466,417 LOC** + `investment-dashboard/apps/web` TypeScript/React 前端），先做全量 AST 静态扫描，再由四路独立审计员逐仓核对真实源码、过滤误报并定位精确 `file:line`。
> **关联已有 PWF 计划**：
> - 架构与模块边界补充：[module-boundaries-2026-11-11/task_plan.md](../task_plan.md)
> - 日志与错误可复现性补充：[feedback-loop-2026-11-17/task_plan.md](../../feedback-loop-2026-11-17/task_plan.md)
> - 总控状态入口：[du11-source-closure-2026-10-18/CURRENT_STATUS.md](../../du11-source-closure-2026-10-18/CURRENT_STATUS.md)

---

## 一、全局总览与核心结论

### 1. 两个核心关切的总体诊断

1. **架构独立性、松耦合与跨模块私有调用（维度一）**：
   - **跨仓生产链基本已走公开 CLI/HTTP 协议（M1–M3 成果有效）**，但仍残留少量跨仓越界：`revenue-forecast/scripts/processed_artifact_canary.py`（及 4 个 RF 工具）直接打开 `company-wiki` SQLite 查私有 `artifacts` 表；`MeetingConverter/company.py` 硬编码读取 `~/company-wiki/graph.yaml`；`filing-fetch/tools/offline_contract_matrix/*` 与 `invest-quick-scan/scripts/iqs_scan/acceptance/stockwiki_g2b_acceptance.py` 直接导入邻仓内部模块甚至邻仓 `tests/*` 私有夹具。
   - **仓内模块封装与独立性严重失守**：在过去按文件拆分巨石模块时，没有建立清晰的分层子包与公开内部契约，导致跨文件/跨子模块直接导入 `_private` 符号、访问外部对象 `other._private`、跨对象写私有状态以及运行时循环依赖（靠函数内延迟导入掩盖）普遍存在。最严重的是 **`StockQAbyLLM` 24 文件循环依赖环（184 处延迟导入）**、**`company-wiki` 9 处运行时循环依赖（含 `source_contract <-> source_catalog` 反向越层环及 12 文件 `source_catalog` 环）**、**`StockWiki` 38 处跨域私有导入 + 52 处外部私有调用 + 约 20 处绕过 Store 直连 SQLite**、**`revenue-forecast` 7 文件 `report_catalog*` 环 + 40+ 私有导入**、**`investment-dashboard` `ops/*` 对 `DashboardService` 的 41 处私有调用**。
   - **为何现有边界测试没有拦截**：CWP 的 `tests/support/layer_boundary_scan.py` 存在 **6 处结构性盲区**（同层豁免导致 264 文件 `source_catalog` 内部零检查、`<shared>` 根模块无方向规则、`tools/feedback_loop/` 未纳入、`_LEGACY_EDGES` 永久豁免 6 条越层边、无循环依赖 SCC 检测、无类型注解参数绕过检查）；且其余 11 仓均缺乏统一的静态 AST 私有调用/循环依赖门禁。

2. **日志完备性与错误可复现性（维度二 — 解释“为何此前多次出错无记录”）**：
   - **系统性日志真空（9/12 仓零日志配置）**：`company-wiki`、`filing-fetch`、`revenue-forecast`、`revenue-forecast-audit`、`StockWiki`、`invest-quick-scan`、`industry-research`、`investment-dashboard`（HTTP/service/feedback 层）均未配置 Python 标准 `logging` 处理器/文件落盘；其余 3 仓中 **`StockInfoDLSimple/src/logger.py` 存在导入期空句柄短路 Bug，导致 `config["logging"]` 配置的文件日志 100% 死代码（从未写入任何日志文件）**，**`MeetingConverter/engines/mimo.py:137` 存在线上 P0 Bug（未定义 `logger`，首次重试即抛 `NameError` 覆盖真实错误并中止重试）**，`earnings-transcripts` 日志无轮转且 `propagate=False` 与 root logger 割裂。
   - **脱敏/不崩溃设计矫枉过正，导致根因与堆栈被销毁**：大量模块为避免向对外 wire/UI 泄露内部路径或凭据，直接把异常吞掉或用 `raise ... from None` / 粗粒度错误码替代，却**未先写入本地脱敏结构化日志**（CWP 95 处 `from None`；ET `transcript_api.py` 3 处全捕获为 `unexpected_provider_failure` 且 `retrieval_runtime.py` 崩溃后立即删除 `worker_stderr.log`；StockQA 10 处丢 `from e` + 61 处 `logger.error` 无 `exc_info=True`；RF `filing_fetch_client.py:373` 报错不读 `stderr`；Dashboard 前端 `api.ts` 丢弃后端返回的 `correlation_id`）。
   - **子进程 `stderr=DEVNULL` 黑洞**：CWP 7 处（`tools/feedback_loop/` 6 处 + `isolated_ocr.py` 1 处）、FF 定时任务 `ff_scheduled_windows.py:153`（stdout/stderr 双 `DEVNULL`）、StockQA `quick_scan_owner_research.py:462`、Audit `run_pool_progress_e2e.py:218` 直接丢弃子进程错误流。
   - **反馈旁路（F4 Sidecar）自身写失败静默吞异常**：CWP/FF/StockWiki/Audit/IR/Dashboard/MC 的旁路记录器在落盘失败时均 `except Exception: pass/return` 且无 stderr 兜底告警，一旦磁盘/权限/序列化异常，业务侧与观察侧同时归零。

### 2. 全 12 模块定量审计矩阵（AST 原始计数 + 源码人工核验结论）

| 模块 | 生产文件 / LOC | 跨模块私有导入（核验） | 外部私有属性/反射（核验） | 运行时循环依赖 (SCC) | 标准 `logging` 配置 | 核心 P0/P1 风险摘要 |
|---|---:|---|---|---|---|---|
| **company-wiki** | 519 / 158,547 | 58 原始（含 `automation`/`source_catalog`/`DU`/`DN` 多处实违） | 68 原始（`coordinator._*`、`prepared._*`、`builder._budget`、`getattr(_*)` 等） | **9 个运行时环**（含跨包 `source_contract<->source_catalog` 及 12 文件 `source_catalog` 环） | **0 配置**（233/243 含 `except` 文件无 `logging`） | **P0**：7 处 `stderr=DEVNULL`、全仓零日志处理器、95 处 `from None` 前无日志、`isolated_ocr`/`narrative_projection`/`feedback_loop` 静默吞错、跨包反向环、`scheduled_summary` `sys.path` 侵入 `scripts/` |
| **filing-fetch** | 63 / 20,985 | 3 生产 + 9 工具 | 0 生产实违（`Popen._handle` 属 Win32 互操作） | **3 生产环** + 1 工具 9 文件环 | **0/63 文件** | **P0**：`ff_scheduled_windows.py:153` 双 `DEVNULL`、全仓零日志；**P1**：`tools/offline_contract_matrix` 直连 CWP SQLite 及导入 ET `tests.*`、`fetch_filing.py` 2,112 LOC 巨石 |
| **revenue-forecast** | 146 / 47,973 | 40+（`report_catalog*`）+ 10+ 其他生产模块 | 24（`catalog._*` 20 处、`runner._pending_attempt_no`、`store._*`） | **1 个 7 文件生产环**（`report_catalog*`） | **0 配置**（1 处未用 import） | **P0**：`filing_fetch_client.py:373` 丢 `stderr`、`rf_job_facade.py:940` 丢 `from exc`；**P1**：`processed_artifact_canary.py` 直查 CWP SQLite、`contracts/document.py` 把引擎 Bug 伪装为校验错 |
| **revenue-forecast-audit** | 45 / 19,383 | 0 生产 | 1（`measure._time_str`） | **1 个 2 文件环**（`financial_measure_*`） | **0/45 文件** | **P1**：`feedback_owner.py:394` 仅输出异常类名、`audit_delivery.py` 静默吞 SQLite/IO 失败、`pool_progress`/`audit_run` `from None`、`run_pool_progress_e2e.py:218` `DEVNULL`；**P2**：16 处 `sys.path` |
| **StockWiki** | 278 / 79,494 | **38 跨域实违**（另 180 为包内 `_` 模块） | **52 实违**（`service._recheck`/`_publish`/`store._connect`/`store._prepare`） | **4 个运行时环** | **0 配置**（仅 1 文件 import） | **P0**：`documents.py`/`llm_usage_ledger.py` 宽泛吞错致解析/计费静默失效、全仓零日志；**P1**：约 20 处绕过 Store 直连 SQLite + 原始 `UPDATE`、`ui.py` 吞堆栈、`dashboard_onboarding.py:548` 死分支 Bug |
| **earnings-transcripts** | 30 / 11,890 | **9 实违**（`transcript_preflight._*`、`_BudgetSession`、`_OpenAITranslator`） | 2 工具 monkey-patch + 6 同文件跨类 `recorder._note_failure` | **0** | 局部有配置（无轮转、`propagate=False` 割裂；核心 CLI/worker 零日志） | **P0**：`transcript_api.py:804,1142,1404` 全捕获为 `unexpected_provider_failure` 零日志；**P1**：`retrieval_runtime.py` 崩溃后立即删 `worker_stderr.log`、5 处日志无 `exc_info`、`manifest` 写失败仍退出 0 |
| **StockInfoDLSimple** | 29 / 7,905 | **2 实违**（已有公开名仍导 `_matches_*`） | **0** | **0** | **配置死代码（P0）** | **P0**：`src/logger.py:15,39` 导入期初始化+空句柄判断短路，导致 `config["logging"]` 永久失效、零日志文件写出；**P1**：`browser.py:645` 吞错静默截断为 1 页、20 处 `log.error` 无 `exc_info`、3 处丢 `from e` |
| **invest-quick-scan** | 315 / 39,079 | **9 跨仓私有测试导入**（StockWiki `tests.*`） | 2 同类/同文件低危 | **0** | **0/315 文件** | **P1**：全仓零 `logging`、62 处宽泛静默 `except Exception`（`dashboard_service`/`dashboard_jobs`/`dashboard_batches` 零堆栈）、142 个顶层 `scripts/*.py` `sys.modules` 垫片、跨仓导入 StockWiki 内部模块与测试 |
| **investment-dashboard** | 65 / 11,728 (+前端 TS) | 9 跨兄弟文件实违（`forecast_common._*`、`ff_job._cli_result`、`tests._owner_stub`） | **43 实违**（`ops/*` 41 处调 `DashboardService._*`、`adapter._deployment_args`、`_fallback._read`） | 仅 `TYPE_CHECKING` 环（0 运行时环） | HTTP/Service/Feedback 均 **0 `logging`** | **P1**：`ops/*` 41 处破坏 `DashboardService` 封装、`http.py`/`request_feedback.py` 零日志且旁路写错静默吞、`adapters/common.py:fail()` 丢 cause、`_find_job` 静默吞异常；**P2**：前端 `api.ts` 丢 `correlation_id`、`OriginalPreview.tsx` 绕过超时封装 |
| **StockQAbyLLM** | 132 / 59,910 | 8 原始（含 3 跨文件实违） | **13 跨类实违**（`_environment` 5 处混用方法/字典、`work_lifecycle._*`、`service._record`） | **1 个 24 文件巨环（P0，184 处延迟导入）** | 有 `logger.py`，但 59/124 `src/` 文件无日志 | **P0**：24 文件循环依赖 + 7,530 LOC `quick_scan_work_store.py` 巨石；**P1**：10 处丢 `from e`、61 处无 `exc_info`、`llm_provider` 仅打类名并重试代码 Bug、`quick_scan_owner_research.py:462` `stderr=DEVNULL`、`_environment` 类型陷阱 |
| **industry-research** | 8 / 5,186 | **2 实违**（`report_generator._md_cell/_md_inline`） | **5 实违**（`client._consumer_path`） | **0** | **0/8 文件** | **P1**：`quick_scan_client.py` 2,817 LOC（占全仓 54%）、`feedback_owner.py:281` 吞 6 类异常为静态串、`native_feedback.py:176` 静默吞写错、`deepseek_client.py` 错误打 stdout |
| **MeetingConverter** | 24 / 4,337 | **0** | **0** | **0** | 有配置但有 **P0 致命 Bug** | **P0 线上 Bug**：`engines/mimo.py:137` 调用未定义的 `logger.warning` 致首次重试抛 `NameError`；**P1**：硬编码 `~/company-wiki/graph.yaml`、配置双源且 `mimo_base_url` 默认值冲突、`transcribe.py` 错误按 `INFO` 打 stdout、`core/feedback.py:1086` 吞 `BaseException` |

---

## 二、逐模块核验清单（精确落点与根因）

### 1. `company-wiki`（CWP）
- **维度一（架构/封装/私有调用）**：
  - **[P0] 跨包反向循环依赖**：`src/company_wiki/source_contract/announcement_collector.py:23,31` 延迟导入 `company_wiki.source_catalog.announcement_collector`，形成 3 文件运行时环；另有 3 条越层边被永久豁免在 `tests/contract/test_layer_public_boundaries.py:341-356` 的 `_LEGACY_EDGES` 中。
  - **[P0] 越界 `sys.path` 侵入**：`src/company_wiki/automation/scheduled_summary.py:33-36` 运行期修改 `sys.path` 导入仓根 `scripts/config.py`。
  - **[P0] `source_catalog` 264 文件（88.9K LOC）巨型扁平包 + 12 文件核心运行时循环依赖**：`acquisition`/`canonical_writer`/`resolver`/`scanner`/`source_reader`/`financial_statements/service` 等 12 个文件靠 25+ 处函数内延迟导入成环；另有 8 文件 `narrative_*` 运行时环与 3 文件 `tools/feedback_loop/` 环（全仓 9 个 SCC 全部是真实运行时环）。
  - **[P1] 跨文件私有调用与反射**：`automation/narrative_run_store.py:21-24` 与 `store.py:1466,1482` 互调私有事务函数并调 `migrations._open_*`；`narrative_model_extractive.py`/`narrative_model_scoped.py` 调用 `legacy._*`；`source_catalog/acquisition_service.py:133,255,264` 调 `coordinator._select_for_ensure/_stage_for_ensure`；`local_reconcile.py:650,654` 反射 `getattr(identity, "_discovery_only" / "_identity_cache_dir")`；`document_understanding/operating_states/relations.py:1264,1338,1342` 直接修改 `prepared._*`；`structure/relations.py` 13 次访问 `builder._budget`；11 个 `source_catalog` 模块绕过 `SourceCatalog` 直接操作 `catalog.store.*`；25 处分散 `sqlite3.connect`。
  - **[P1] `tests/support/layer_boundary_scan.py` 六大盲区**：(1) `_foreign()`（`:159-161`）豁免同包内所有跨文件私有访问；(2) `<shared>` 根模块（39 文件）无方向约束；(3) `tools/feedback_loop/` 未纳入 `SOURCE_ROOT`；(4) `_LEGACY_EDGES` 永久放行 6 条越层边；(5) 无 SCC 循环依赖检测；(6) 无类型注解参数（如 `def f(catalog): catalog._store`）无法拦截。
- **维度二（日志/可复现性）**：
  - **[P0] 零日志配置**：全仓 `basicConfig`/`FileHandler`/`RotatingFileHandler` = 0，233/243 含 `except` 文件无 `logging`；`runtime_feedback.py` 仅接入 15/27 个 CLI 且在 `:167-187` 静默吞掉自身写入失败。
  - **[P0] 7 处生产 `stderr=DEVNULL`**：`tools/feedback_loop/local_host.py:187,343,533,549`、`intake.py:330`、`hook.py:45`、`document_normalization/isolated_ocr.py:371`（叠加 `:222` 丢异常为 `"OCR_INFERENCE_FAILED"`）。
  - **[P0] 高危静默吞异常**：`tools/feedback_loop/intake.py:373`、`local_host.py:107,189,259,316,371,439`、`automation/narrative_projection.py:261-265`（批量激活异常静默 `continue`）。
  - **[P1] 95 处 `raise ... from None` 未先落盘脱敏日志**；`normalizer.py:1382,823,850`、`controller.py:70,104`、`public_canonical_browser.py:1058`、`catalog_repair.py:86,99`、`scheduled_summary.py:107` 静默降级或丢错；`error_taxonomy.structured_error` 与 `runtime_feedback.py` 缺少 `code_version` 和逻辑 `input_ref`。

### 2. `filing-fetch`（FF）
- **维度一**：`tools/offline_contract_matrix/{cwp_readback_probe,seed_batch,source_proofs,et_transcript_proxy}.py` 直接导入 CWP 内部模块、直查 CWP SQLite `documents/sources` 表并导入 ET `tests.*` 夹具（P1）；生产 `scripts/` 有 **3 个运行时循环依赖**（`fetch_filing <-> transcript_companion`、`ff_job_feedback <-> ff_job_runner <-> ff_job_store`、`filing_contracts` 4 文件环）+ 3 处生产跨文件私有导入（`filing_contracts._required_text/_validate_companion_request/_validate_date`）+ `fetch_filing.py` 2,112 LOC + 10 处 `sys.path.insert` + 0 个静态 AST 边界测试。
- **维度二**：**P0** `scripts/ff_scheduled_windows.py:153-160` 启动定时任务时将 `stdout`/`stderr` 全丢 `DEVNULL`；**P0** 全仓 **0/63 文件**使用 `logging`；**P1** `transcript_companion.py:143,165`、`fetch_filing.py:1814,1931`、`ff_runtime_feedback.py`（6 处）、`ff_job_store.py:81,358`、`ff_process_transport.py:112-123`（`from None` 丢 `winerror`）吞异常或丢上下文。

### 3. `earnings-transcripts`（ET）
- **维度一**：无跨仓导入、无循环依赖（良好）；存在 **9 处跨文件私有导入**（`transcript_preflight._*` 5 处、`retrieval_budget._BudgetSession` 3 处、`translator._OpenAITranslator` 1 处）、`tools/replay_feedback_case.py:245-265` 对私有函数 monkey-patch、5 处 `sys.path.insert`、3 个 1,400–2,200 LOC 巨石文件、缺静态 AST 边界测试。
- **维度二**：**P0** `transcript_api.py:804,1142,1404` 将所有未预期异常静默转为 `unexpected_provider_failure` 且无日志无堆栈；**P1** `retrieval_runtime.py:84-99,257-284` 从 `worker_stderr.log` 只抽单个类名后立刻删除工作目录导致堆栈永久消失；`config.py`/`scraper.py` 无轮转且 `propagate=False` 割裂日志；`scraper.py:1775,1792`（写 manifest 失败仍 exit 0）与 `translator.py:31,66,175` 静默吞错；5 处日志缺 `exc_info=True`。

### 4. `StockInfoDLSimple`（SID）
- **维度一**：无跨仓、无循环、无外部私有属性访问（结构较干净）；仅 `src/company_wiki_adapter.py:20` 导入已有公开版的 `_matches_excluded/_matches_keywords`（P2）、`main.py:30` `sys.path.insert` 及缺静态 AST 边界测试。
- **维度二**：**P0** `src/logger.py:15-16,39` 在导入期无参执行 `setup_logger()` 且受 `if logger.handlers: return logger` 短路，导致 `main.py:460` 与 `src/config.py:48-52` 的文件日志配置**完全失效（从未写出日志文件）**；**P1** `src/browser.py:645` 吞错返回 `total_pages=1` 静默截断分页、同文件 17 处宽泛吞错、`feedback_owner.py:459` 吞 6 类异常为固定字面量、20 处 `log.error/warning` 缺 `exc_info=True`（含 `main.py:273`、`downloader.py:89,288,420`）；3 处丢 `from e`。

### 5. `revenue-forecast`（RF）
- **维度一**：**P1** 7 文件 `report_catalog*` 运行时循环依赖（25 条内部边）+ 40+ 跨文件私有导入 + 20 处 `catalog._*` 私有调用；**P1** 生产脚本 `scripts/processed_artifact_canary.py:59-70`（及 4 个 `tools/` 脚本）直连 CWP SQLite 查私有 `artifacts` 表；`tools/ex05_chain_replay.py` 导入 CWP/FF 内部模块并硬编码个人路径；`rf_job_facade.py:887,1260,1288` 写 `runner._pending_attempt_no` 及调 `store._*`；19 处 `sys.path.insert`。
- **维度二**：**P0** `scripts/filing_fetch_client.py:373` 报错完全未读取 `completed.stderr` 且 `:376` 丢 `from exc`；`rf_job_facade.py:940-944` 丢 `from exc` 且不落明细；**P1** 全仓零日志配置（80/146 文件无 `logging`）、`scripts/contracts/document.py:1197,1245,1310` 把引擎代码 Bug 吞成用户输入校验错、`revenue_core.py:239` 仅截断 `stderr[:200]`、`tools/release_readiness.py:80` `DEVNULL`。

### 6. `revenue-forecast-audit`（Audit）
- **维度一**：生产侧 0 跨仓、0 私有导入（较干净）；**P2** `financial_measure_audit.py:545 <-> financial_measure_evidence.py:56,684` 成环且调私有 `measure._time_str()`；16 处 `sys.path` 注入（含 `audit_run.py:809` 运行期注入）与 8 个超 800 LOC 脚本。
- **维度二**：**P1** 0/45 文件使用 `logging`；`feedback_owner.py:393-395` 吞掉错误详情只印类名；`audit_delivery.py:116-156` 静默吞 SQLite/IO 失败；`audit_run.py:776` 静默吞 `OSError`；`pool_progress.py:1126` 与 `audit_run.py:756` 使用 `from None` 擦除堆栈；`tools/run_pool_progress_e2e.py:218` `stderr=DEVNULL`。

### 7. `StockWiki`
- **维度一**：**P1** 严重绕过 Store 封装：约 20 处特征模块绕过 `QuickScanStore`/`IdentityReceiptStore` 直接 `sqlite3.connect(store.database_path)` 或调 `store._connect()`/`_read_connect()`，其中 `admin_security_id_normalization.py:73-310` 直接对核心表执行原始 `UPDATE` 并调 `store._prepare()/_save_prepared()`；`public_company_assessments.py`（2,566 LOC）混用 7 处 `_read_connect()` 与 7 处原生 `sqlite3.connect`；**P1** 38 处跨域私有导入 + 52 处外部私有属性/方法调用（含 `quick_scan_work_delegation.py` 12 处调用 `service._recheck`/`grants._publish`、`dashboard_company_assessment_operator_cli.py:32` 导入 `_canonical_json`）；**P2** 4 个运行时循环依赖、7 个根 CLI `sys.path` 注入、`runtime_feedback.py:112-114` 访问 `argparse` 内部私有字段。
- **维度二**：**P0** 全仓零日志配置（157/278 文件含 `except` 无 `logging`）；**P0** `documents.py:93,154,193,242,390` 解析崩溃静默返 `None`、`llm_usage_ledger.py:60,129,147` 计费落盘失败静默返 `None`/`{}`、`public_company_assessments.py:1136,1287,1566` DB 锁/损坏静默返 `None`、`runtime_feedback.py:58,134,288` 静默吞错；**P1** `ui.py:163,243,246` `log_message` 空实现且吞堆栈、`market_registry.py`/`public_research_view.py` 3 处丢 `from exc`；另发现逻辑 Bug `dashboard_onboarding.py:548-550` 死三元表达式。

### 8. `invest-quick-scan`（IQS）
- **维度一**：**P1** `scripts/iqs_scan/acceptance/stockwiki_g2b_acceptance.py:30-36,126-135` 注入 StockWiki `tests` 路径并导入 9 个 StockWiki 私有测试辅助函数及 8 个内部 Store 模块；`iqs_temporal_vendor/legacy_oracle.py:3,7` 直接导入 `stockwiki.quick_scan_freshness`；**P1** 142 个顶层 `scripts/*.py` 通过 `sys.modules[__name__] = ...` 制造双模块身份 + 11 处 `sys.path.insert`；**P2** 15 处分散 `sqlite3.connect` 及 11 个超 800 LOC 巨石文件。
- **维度二**：**P1** 全仓 **0/315 文件**导入 `logging`；**P1** 62 处宽泛静默 `except Exception`（`dashboard_service.py:856` HTTP 分发未捕获异常仅返 `"本地组件处理失败"` 零服务端日志、`dashboard_jobs.py:128-166` 丢异常类型/堆栈且锁超时 80ms 直接丢弃错误态、`dashboard_batches.py:761`、`dashboard_execution.py:986`、`workbench_snapshot.py:368`）；**P2** 5 处丢 `from exc`。

### 9. `investment-dashboard`（Dashboard，含前端 `apps/web`）
- **维度一**：（已过滤误报：`factory.py:11` 是同包相对导入 `.filing_fetch`，`ops/__init__ <-> service` 仅为 `TYPE_CHECKING` 环）**P1** 全部 9 个 `application/ops/*.py` 共对 `DashboardService` 发起 **41 处私有方法调用**（`_port`/`_read`/`_company`/`_find_job` 等）；**P2** `forecast.py`/`forecast_scope.py` 导入 7 个 `forecast_common._*` 并调 `adapter._deployment_args()`、`ff_scheduled_refresh.py:26` 导入 `ff_job._cli_result`、`identity.py:155` 调 `_fallback._read()`、`scripts/f2_dash_feedback_sample.py:28-35` 导入 `tests` 私有 `_owner_stub`；前端 `apps/web/src/features/documents/OriginalPreview.tsx:45` 绕过 `shared/api.ts` 超时封装。
- **维度二**：**P1** `transport/http.py`、`application/service.py`、`request_feedback.py` 全部零 `logging`，且 `request_feedback.py:305-309` 静默吞所有诊断写盘异常；**P1** `adapters/common.py:23-24` `fail()` 未接收 `cause` 导致全部适配器丢异常链；**P1** `service.py:366-378,439-448` 静默吞 `OwnerPortError`；**P2** `cwp_stream.py`/`iqs/quickscan.py` 告警缺上下文与堆栈；前端 `apps/web/src/shared/api.ts:56-63` 丢弃后端 `correlation_id` 导致 UI 报错无法与后端日志关联。

### 10. `StockQAbyLLM`（StockQA）
- **维度一**：**P0** `src/utils/quick_scan_*.py` 存在 **24 文件巨型运行时循环依赖环**（184 处延迟导入 + 48 条顶层边），围绕 7,530 LOC 巨石文件 `quick_scan_work_store.py`；**P1** 13 处真跨类私有访问，其中 `_environment` 在 2 处被当方法调用（`client._environment()`）、在 2 处被当字典属性读取（`self.owner._environment`）构成潜伏 `TypeError` 陷阱；`llm_runner.py:3055,3172,3176` 读取 `work_lifecycle._lease_seconds/_store/_owner_refresh`；`quick_scan_refresh_execution.py:385,466` 调 `service._record`；**P2** 18 个超 800 LOC 文件、11 处分散 SQLite、4 处 `sys.path.insert`。
- **维度二**：**P1** 10 处 `raise` 丢失 `from e`（`config_manager`/`json_config_manager`/`search_service`/`output_validator`/`security`）；**P1** `quick_scan_owner_research.py:462` `stderr=DEVNULL`，另 2 处捕获后直接丢弃 `stderr`；**P1** `llm_provider.py:990-1047` 与 `async_llm_provider.py:366-429` 宽泛捕获 `Exception` 重试代码 Bug 且仅记录 `type(e).__name__`；全仓 **61 处 `logger.error/warning` 缺 `exc_info=True`**；`llm_runner.py:1558,1671,1707`、`llm_integration.py:867-1037`、`qa_engine.py:139,938` 静默吞异常（`:1671` 把坏 checkpoint 误判为未持久化）；59/124 `src/` 文件零日志。

### 11. `industry-research`（IR）
- **维度一**：跨仓隔离干净（0 跨仓/0 环/0 `sys.path`）；**P1** `tools/quick_scan_client.py` 2,817 LOC 占全仓 54%；**P2** 导入 `report_generator._md_cell/_md_inline` 及 5 处调用 `client._consumer_path(...)`。
- **维度二**：**P1** 0/8 文件使用 `logging`；`tools/feedback_owner.py:281-283` 将 6 类异常擦除为固定文案；`tools/native_feedback.py:174-177` 静默吞自身落盘失败；`tools/deepseek_client.py:647-693` 将错误打印到 `stdout`。

### 12. `MeetingConverter`（MC）
- **维度一**：全生态封装最干净（0 私有导入/0 私有属性/0 环/0 `sys.path`）；**P1** `company.py:14,130-152` 硬编码跨仓读取 `~/company-wiki/graph.yaml`；**P1** `config.py` 与 `translator.load_config` 双配置源且默认 `mimo_base_url` 冲突；**P2** `core/pipeline.py:343` 依赖具体类 `isinstance(engine, FallbackEngine)`，`core/feedback.py` 1,478 LOC 占全仓 34%。
- **维度二**：**P0 线上 Bug** `engines/mimo.py:137` 调用未导入/未定义的 `logger.warning(...)`，任何首次瞬时 API 错误都会触发 `NameError` 直接打断重试并掩盖原错误；**P1** `transcribe.py` 将致命错误按 `INFO` 打到 `stdout`、`engines/fallback.py:60`/`core/pipeline.py:227`/`translator.py:85-92` 缺 `exc_info`、`core/batch.py:128` 割裂 `traceback.print_exc` 与日志、`core/feedback.py:1086` 捕获 `BaseException` 吞掉中断信号；**P2** `audio_utils.py:151` 不检查 `ffmpeg` 退出码/错误流。

---

## 三、系统性解决方案与分阶段实施路线（PLAN_ONLY，待用户确认后按 owner 仓实施）

遵循 `AGENTS.md` 与 `architecture.md` 原则：**不拆微服务、不引入运行时反射沙箱、不设任意字节数日志许可门、坚持单仓单 owner 实施 + RED→GREEN TDD + 静态 CI 护栏**。整体分四条工作线（S1 → S2 → S3 → S4）：

### Workstream S1 — P0 线上 Bug 与零可见性黑洞止血（最高优先级）
1. **MeetingConverter**：在 `engines/mimo.py` 补 `import logging; logger = logging.getLogger(__name__)` 并加 `exc_info=True` 及重试单测；将 `core/feedback.py:1086` 收窄为 `except Exception`。
2. **StockInfoDLSimple**：移除 `src/logger.py` 导入期副作用或支持重新配置，在 `main.py` `load_config()` 之后按 `config["logging"]` 启用 `RotatingFileHandler` + ISO 时间戳；修复 `src/browser.py:645` 吞错返 `total_pages=1`。
3. **filing-fetch**：移除 `ff_scheduled_windows.py:153-160` 双 `DEVNULL`，改为落盘轮转 tick 日志并在非零退出时保留脱敏 stderr 尾段。
4. **company-wiki**：清除全部 7 处生产 `stderr=DEVNULL`（`tools/feedback_loop/local_host.py` 4 处、`intake.py`、`hook.py`、`isolated_ocr.py`），捕获有界脱敏 stderr；修复 `isolated_ocr.py:222` 与 `narrative_projection.py:261` 静默丢错。
5. **earnings-transcripts**：修复 `transcript_api.py:804,1142,1404` 静默吞异常为 `unexpected_provider_failure`；在 `retrieval_runtime.py` 删除临时工作目录前将失败 `worker_stderr.log` 持久化到轮转诊断日志。
6. **revenue-forecast**：修复 `filing_fetch_client.py:373` 未读 `stderr` 与 `:376`/`rf_job_facade.py:940` 丢 `from exc`。
7. **StockWiki**：修复 `documents.py` 与 `llm_usage_ledger.py` 静默返 `None`/`{}`、`ui.py` 空 `log_message` 及 `dashboard_onboarding.py:548` 死分支 Bug。
8. **StockQAbyLLM**：清除 `quick_scan_owner_research.py:462` `stderr=DEVNULL` 及另 2 处丢弃 `stderr`；修复 `llm_provider.py`/`async_llm_provider.py` 重试代码 Bug 且只记类名的问题。

### Workstream S2 — 全 12 仓统一双层可观测性与可复现日志规范（F5 基础设施）
- **第一层（本地轮转结构化日志，所有入口默认开启，绝不破坏对外 stdout 协议）**：
  - 每仓建立轻量化标准日志引导模块（仅依赖标准库 `logging.handlers.RotatingFileHandler` + JSONL/结构化脱敏格式器，屏蔽 API Key/Token/Authorization），在所有 CLI、HTTP、Worker、Scheduler 入口初始化，输出至 `<state_root>/logs/<module>.log`（错误同步写 `stderr` 或独立错误通道，绝不污染机器 JSON `stdout`）。
- **第二层（最小可复现错误信封，统一字段）**：
  - 每条 `ERROR` / 非预期 `WARNING` 必须携带：`timestamp_utc`、`level`、`repo`、`code_version`（包版本 + git short SHA）、`run_id`、`attempt_id`、`step_id` / `correlation_id`、`operation`、`input_ref`（逻辑标识/哈希，不含凭据）、`exc_type`、`exc_chain`、`traceback`（脱敏）。
- **核心编码红线（“先写全量脱敏日志，再投影安全对外错误”）**：
  1. 任何 `raise ... from None` 或对外安全错误封装（`invalid_request`、`export_unavailable`、`本地组件处理失败` 等）之前，**必须先**调用 `logger.exception(...)` 落盘完整脱敏堆栈；
  2. 禁止在业务/IO/DB/子进程路径静默 `except Exception: pass/return None`；区分预期控制流（窄异常）与非预期故障（记 `exc_info=True`）；
  3. 所有 F4 反馈旁路写盘失败时必须向 `sys.stderr` + 标准日志输出一行降级告警，禁止静默吞错；
  4. `investment-dashboard` 前端 `shared/api.ts` 保留并展示 `correlationId`，打通“UI 报错 → HTTP 日志 → F4 观察 → 责任仓日志”全链路定位。

### Workstream S3 — 跨模块私有调用清零与运行时循环依赖解耦（M4 架构收口）
- **跨仓边界清零**：
  - `revenue-forecast/scripts/processed_artifact_canary.py` 及 4 工具改走 CWP 公开只读 CLI，停止直查 CWP SQLite；
  - `filing-fetch/tools/offline_contract_matrix` 与 `invest-quick-scan/.../stockwiki_g2b_acceptance.py` 停止导入邻仓内部模块及邻仓 `tests/*`，改用公开 CLI 契约/独立夹具；
  - `MeetingConverter/company.py` 移除 `~/company-wiki/graph.yaml` 硬编码，统一单配置源（`config.py`）。
- **仓内零私有调用与破环（按严重度排期）**：
  1. **StockQAbyLLM（P0）**：将 24 文件 `quick_scan_*.py` 环与 7,530 LOC `quick_scan_work_store.py` 拆为三层单向 DAG（`quick_scan_store_types` 底层类型/协议/异常 ← 独立 journal 仓储 ← `QuickScanWorkStore` 门面），清零 184 处延迟导入；统一公开 `subprocess_env()` 协议消除 `_environment` 方法/字典混用陷阱；在 `WorkItemLifecycle` 公开只读属性。
  2. **company-wiki（P0/P1）**：清退 `_LEGACY_EDGES` 6 条豁免边（重点破除 `source_contract <-> source_catalog` 环）；把 `scripts/config.py` 配置加载迁入 `src/` 消除 `scheduled_summary.py` `sys.path` 侵入；将 264 文件 `source_catalog` 按域拆分为带 `__all__` 门面的显式子包（`storage`/`identity`/`acquisition`/`browsing`/`narrative`/`financial_statements`），抽取纯值叶子模块破除 12 文件与 8 文件运行时环；统一通过 `CatalogStore.open_readonly()` 收口 25 处 SQLite 直连；将跨文件共享私有函数（`automation/db_tx.py`、`AcquisitionCoordinator` 公开方法等）显式公开化。
  3. **StockWiki（P1）**：在 `QuickScanStore`/`IdentityReceiptStore` 公开 `read_connection()`/`write_transaction()` 与领域写方法，清零 ~20 处 Store 绕过与原始 `UPDATE`；公开 `publish()`/`recheck()`/`canonical_json()` 消除 38 处跨域私有导入与 52 处私有调用；破除 4 个运行时环。
  4. **revenue-forecast（P1）**：抽取 `report_catalog_common.py` 并在 `ReportCatalog` 公开只读/校验接口，破除 7 文件 `report_catalog*` 环及 40+ 私有导入；将 `attempt_no` 显式传入 `runner.run()` 消除 `runner._pending_attempt_no` 写入。
  5. **investment-dashboard（P1）**：定义公开 `ServiceContext` 协议供 `application/ops/*` 消费，一次性消除 41 处 `DashboardService._*` 私有调用与 `TYPE_CHECKING` 环；公开 `forecast_common`/`ff_job`/`identity` 共享契约；前端 `OriginalPreview.tsx` 接入 `shared/api.ts`。
  6. **filing-fetch / invest-quick-scan / ET / SID / Audit / IR（P1–P2）**：
     - FF：抽 `ff_errors.py` 与 `ff_identity_client.py` 破除 3 个生产环，公开 `filing_contracts` 校验器，拆分 2,112 LOC `fetch_filing.py` 并包化去 `sys.path`；
     - IQS：以 `pyproject.toml` 正式包化 `iqs_scan`，逐步清退 142 个 `scripts/*.py` `sys.modules` 垫片；
     - ET/SID/Audit/IR：公开跨文件 `_private` 符号（`BudgetSession`/`validate_request`/`matches_excluded`/`format_time_str`/`md_cell`/`resolve_consumer_path`），将 ET `replay_feedback_case.py` monkey-patch 改为依赖注入，拆分 IR 2,817 LOC `quick_scan_client.py`。

### Workstream S4 — 全 12 仓统一静态 CI 护栏（防回潮）
1. **升级 CWP `tests/support/layer_boundary_scan.py`**：补齐全部 6 个盲区（子包级隔离、`<shared>` 规则、`tools/feedback_loop/` 纳入、清零 `_LEGACY_EDGES`、Tarjan SCC 运行时循环检测、未标注参数私有属性告警）。
2. **向全部 12 仓下发统一的零依赖 AST 架构与日志卫生检查门禁**（先锁存量 baseline 棘轮防新增，随 S1–S3 逐仓清零）：
   - **A1（零跨文件私有导入）**：禁止跨模块/跨文件 `from mod import _name` 或导入私有模块（仅白名单显式薄门面）；
   - **A2（零外部私有属性/反射访问）**：禁止非 `self`/`cls`/`super()` 的 `obj._attr` 与 `getattr/setattr(obj, "_...")`（仅允许显式标注 `# boundary: stdlib-interop`）；
   - **A3（零运行时循环依赖）**：全仓顶层+延迟导入 Tarjan SCC 必须为空；
   - **A4（零跨仓内部导入/越界 `sys.path`/外仓 SQLite）**；
   - **L1（零宽泛静默吞异常）**：禁止 `except Exception/BaseException/OSError` 无日志/无重抛/无结构化记录；
   - **L2（零异常链丢失）**：禁止 `except` 内 `raise NewErr(...)` 缺 `from exc`；使用 `from None` 前必须有脱敏日志记录；
   - **L3（零无堆栈报错与业务子进程 `stderr=DEVNULL`）**：`except` 内 `logger.error` 必须带 `exc_info=True` 或用 `logger.exception`；
   - **L4（每仓 1 秒日志活性自检测试）**：CI 用坏输入调用真实主入口，断言轮转日志文件确实写入含 `exc_type` + `traceback` + `run_id` 的可复现记录（彻底杜绝 SID 死日志与 MC `NameError` 类回潮）。
