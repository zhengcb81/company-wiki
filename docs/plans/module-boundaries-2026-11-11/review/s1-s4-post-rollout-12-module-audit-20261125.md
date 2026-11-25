# S1–S4 实施后全 12 模块逐仓深度复审报告：计划完成度、架构边界、新代码缺陷与部署漂移（2026-11-25）

> **审计性质**：严格只读全量复审（零生产代码修改、零配置修改、零外仓写入、零外部/付费请求、零密钥输出）。
> **审计基准**：对照 [2026-11-24 全 12 模块深度代码审计报告与 S1–S4 原计划](full-12-module-architecture-logging-audit-20261124.md)，逐项核查 [S1 台账](../../feedback-loop-2026-11-17/s1-p0-blackhole-plan.md)、[S2 计划与收尾台账](../../feedback-loop-2026-11-17/s2-closeout-20261125.md)、[S3/S4 分仓台账](../s3-s4-owner-rollout-20261125.md)、12 个仓库最新正式发布引用（`master`/`main`/`origin/main`/`origin/master`/`v2-clean-rewrite`）、本机工作区检出、F4 宿主 `settings.json` 实际运行路径及四套全局技能目录（`.agents`、`.codex`、`.claude`、`.gemini/config`）。

---

## 一、核心结论总览：S1–S4 真实完成度评估

### 1. 阶段级完成度判定

| 阶段 | 原计划核心要求（2026-11-24 基准） | 实际交付状态 | 真实完成度评估与核心差距 |
|---|---|---|---|
| **S1（P0 黑洞止血）** | 8 仓 P0 线上崩溃（MC `NameError`、SID 死文件日志与分页吞错）及子进程 `stderr=DEVNULL` / 异常吞没止血 | **部分完成（约 70%，含 4 项回退/新缺陷）** | MC `NameError`、SID `main.py` 日志短路与 `browser.py:645`、RF `rf_job_facade` `from exc` 已修；**但**：(1) **RF S2（`1b471df4`）删回了 S1 在 `filing_fetch_client.py` 新增的 `_logger` 与 `_redacted_stderr_excerpt`**；(2) **StockQA S1（`1449d715`）正则漏脱敏 `Authorization: Bearer <token>` 导致凭据明文落盘，且读取 `stderr` 头部 8KB 截断尾部堆栈**；(3) **ET（`0f3b690`/`d694486`）删除 `worker_stderr.log` 改为 `stderr=DEVNULL`，生产 `--report-usage` 下标准日志全关**；(4) **SID 被 CWP 调用的真实生产入口 `company_wiki_adapter_cli.py` 仍零文件日志，且 `setup_logger` 存在句柄泄漏**。 |
| **S2（全 12 仓统一双层日志）** | **第一层**：12 仓全部 CLI/HTTP/Worker/Scheduler 默认启用本地 `RotatingFileHandler` 脱敏结构化日志；**第二层**：统一最小可复现错误信封（含 git SHA、`input_ref`、`exc_chain`）；`from None` 前必落日志；F4 旁路写失败必打 `stderr` 告警 | **仅完成局部切片（约 30%，被缩窄为每仓 1 个 F4 试点节点）** | **0 / 12 仓实现第一层“全入口统一本地轮转日志”**：7 仓生产代码仍 **0 个 `RotatingFileHandler`/`FileHandler`**（CWP `src/`、FF `0/67`、RF `0/153`、Audit `0/46`、StockWiki `0/268`、IQS `0/318`、Dashboard `0/66`、IR `0/10`），MC 打 `stdout`，StockQA/ET 用无轮转 `FileHandler` 且主 CLI 未接入。F4 旁路写失败在 **FF、RF、StockWiki、ET、IR、Dashboard（甚至向前端返回查不到记录的幽灵 `correlation_id`）** 中仍静默吞错无 `stderr` 告警；Audit 在 SQLite 写失败走 `exported_without_journal` 时漏存 `failure` 正文导致 F4 `reconcile` 永久返回 `unknown`。 |
| **S3（跨模块私有调用清零与破环）** | 跨仓 SQLite/内部导入清零；破除 StockQA 24 文件巨环、CWP 9 环与 264 文件扁平 `source_catalog`、StockWiki ~20 处 Store 绕过、RF 7 文件 `report_catalog` 环、Dashboard 41 处 `ops/*` 私有调用与适配器私有导入、FF 3 环与巨石、IQS 包化去 142 垫片、IR 拆分 `quick_scan_client.py` | **部分完成（约 40%，跨仓显著改善，仓内核心巨环与巨石未动，引入 3 项功能回归）** | **已完成亮点**：MC 移除外仓 `graph.yaml`、Dashboard 清零 `ops/*` 41 处 `DashboardService._*`、Audit 破除 2 文件环、SID/IR 清零跨文件私有访问、CWP 迁入 `runtime_config` 与纯值契约、RF 退役旧 canary SQLite 直读、IQS `stockwiki_g2b_acceptance.py` 改走公开 CLI。**未完成主项**：StockQA 仍为 **58 文件巨环（30 文件 `quick_scan` 环、597 处延迟导入、7,081 LOC `quick_scan_work_store.py`）**；CWP 仍有 **15 个运行时环、267 文件扁平 `source_catalog`、6 条 `_LEGACY_EDGES`、58 私有导入/62 私有属性/24 `sqlite3.connect`**；StockWiki ~19 处 Store 绕过与 3 环未动；RF 5+2+2 三环与 60 私有导入未清；FF `seed_batch.py:32` 与 IQS `legacy_oracle.py:3,7` 仍跨仓导入，IQS 0 `pyproject.toml` 且垫片增至 144 个；IR `quick_scan_client.py` 仍 2,820 LOC。**新引入 S3 回归**：StockQA `_quick_scan_owner_refresh_port.py:398` 漏改 `_environment` 致显式 `process_env` 失效；MC `transcribe.py` `config.json` `transcription_engine` 100% 死配置且 CLI 参数优先级倒置；StockWiki `SecurityIdNormalizationStore.complete()` 跨库非原子提交顺序风险。 |
| **S4（全 12 仓统一静态 CI 护栏）** | 修复 CWP `layer_boundary_scan.py` 6 大盲区；全 12 仓落地 A1–A4（架构）与 L1–L4（日志活性自检）静态门禁并接入远端 CI | **基本未完成（< 15%，M4-C 计划改口放弃统一门禁）** | **CWP `layer_boundary_scan.py` 与 `test_layer_public_boundaries.py` 零改动，6 大盲区原封未动**；全 12 仓均未落地 L1–L4 静态门禁与 1 秒轮转日志活性自检；**RF 新增的 10 个 S1–S4 测试文件全部漏加进 `tools/pre_push_gate.py:CI_TESTS`（GitHub CI 实际执行数为 0！）**；FF 新增边界测试硬编码 4 文件名漏掉同目录 `seed_batch.py`；**5 个仓库（StockWiki、Audit、ET、SID、IQS、Dashboard、IR 共 7 仓）在目标发布分支上无 GitHub Actions CI 工作流**。 |
| **现场部署与技能同步** | F4 宿主运行目录、主工作区与全局安装技能同已验收正式版本一致 | **严重漂移（5 个 F4 运行目录 + 全部 4 套全局技能未对齐）** | F4 `settings.json` 中 **FF（缺 `c110943` `ff_t3_receipt.py`）、IR（停在 S2 `a055204` 缺 S3）、IQS（停在 11-23 `aa847ac` 缺 S2/S3）、RF（`report` 跑 `597c6bc2` 旧树而 `reconcile` 跑 `b9e59db4` 分裂）、StockQA（停在 `a3c2c72` 缺 `origin/master` 后续 8 提交）**；`.agents`/`.codex`/`.claude`/`.gemini/config` 四套全局技能中 **FF（停在 S1 前 `1defca5`）、RF（46 文件漂移+26 文件缺失，仍含直查 SQLite 的旧 canary）、Audit（缺 `financial_measure_core.py`，`.codex` 整包缺失）、IR（缺 S3 新增 `report_format.py`/`report_output.py`）** 均未同步！ |

---

## 二、全 12 模块定量复测对比表（2026-11-25 最新正式发布引用）

| 模块 | 审计发布引用 | 本地主工区 HEAD | F4 宿主实际运行版本 | 运行时环 (SCC) | 跨文件私有导入 / 外部私有属性 | 标准 `logging` 文件数 / 轮转 Handler | S1–S4 完成度评级 |
|---|---|---|---|---:|---|---|---|
| **1. `company-wiki`** | `master@d021c7976` | `master@d021c7976`（对齐） | `master@d021c7976`（对齐） | **15**（`src`+`tools` 11） | `58` / `62`（`src`+`tools`） | `25/795` / 仅 F4 唤醒子进程 1 处（`src/` 为 **0**） | **部分完成（约 40%）** |
| **2. `filing-fetch`** | `origin/main@c110943` | `main@711db1c`（滞后 1 提交） | **漂移**：`main@711db1c`；全局技能停在 S1 前 `1defca5` | **2 生产 + 1 工具(9文件)** | `0 生产 + 10 工具` / `3 工具`（另 `seed_batch.py` 跨仓导 CWP） | `0/67` / **0** | **部分完成（约 45%）** |
| **3. `earnings-transcripts`** | `main@2fc8f92` | `main@2fc8f92`（对齐） | `main@2fc8f92`（对齐） | **0** | `1`（`_OpenAITranslator`）/ `13`（含 monkey-patch） | `7/31` / **0 轮转**（2 处无界 `FileHandler`） | **部分完成（约 45%）** |
| **4. `StockInfoDLSimple`** | `v2-clean-rewrite@1d02afd` | `v2-clean-rewrite@1d02afd`（对齐） | `1d02afd`（对齐） | **0** | **0** / **0** | `2/29` / `1`（仅 `main.py`；CWP 适配 CLI 为 **0**） | **部分完成（约 55%）** |
| **5. `revenue-forecast`** | `origin/main@b9e59db4` | `main@d62fca9a`（分叉滞后 37 提交） | **脑裂**：`cwd`/`report` 跑 `597c6bc2`，`reconcile` 跑 `b9e59db4`；全局技能严重过期 | **3**（5文件+2文件+2文件） | `61` / `24`（`catalog._*` 21 处） | `2/153` / **0** | **部分完成（约 35%，含 CI 漏跑与 S1 回退）** |
| **6. `revenue-forecast-audit`** | `main@8267a8a` | `main@8267a8a`（对齐） | `main@8267a8a`（对齐）；**全局技能过期且 `.codex` 缺失** | **0** | **0** / **0** | `0/46` / **0** | **部分完成（约 50%，含 S2 reconcile 缺陷）** |
| **7. `StockWiki`** | `master@dd5b033`（无远端） | `master@dd5b033`（对齐） | `master@dd5b033`（对齐） | **3** | `~35+ 跨域` / `37`（另 ~19 处绕过 Store 直连 SQLite） | `5/268` / **0** | **部分完成（约 30%）** |
| **8. `invest-quick-scan`** | `master@3a07832` | `codex/cross-id...@50fe2b1`（S2/S3 前） | **漂移**：`.worktrees/f4-runtime@aa847ac`（S2/S3 前） | **0** | `1` / `2`（另 `legacy_oracle.py` 跨仓导 StockWiki；144 垫片） | `0/318` / **0** | **部分完成（约 30%）** |
| **9. `investment-dashboard`** | `origin/main@e563354` | `main@ead3425`（滞后 4 提交） | `.worktrees/f4dv@e563354`（对齐），但主仓与 `f4-runtime` 滞后 | **0** | `33`（`adapters/*` 内部）/ `2`（`adapter._deployment_args`, `_fallback._read`） | `2/66` / **0** | **部分完成（约 55%）** |
| **10. `StockQAbyLLM`** | `origin/master@a89636f` | `codex/qa-content...@a3c2c72`（滞后 8 提交） | **漂移**：跑主仓 `a3c2c72`（缺 8 个 S3/S4 提交） | **1 巨环（58文件；`quick_scan` 30文件）** | `0` / `60`（含 `_environment` 漏改 Bug） | `5/133` / **0 轮转**（1 处无界 `FileHandler`，11/14 CLI 未接） | **部分完成（约 35%，含凭据漏脱敏与 S3 回归）** |
| **11. `industry-research`** | `origin/main@1c98102` | `codex/s2-ir...@a055204`（缺 S3） | **严重漂移**：主仓与全部 4 套安装技能均停在 `a055204`（缺 S3 新文件） | **0** | **0** / **0**（在 `origin/main` 上） | `0/10` / **0** | **部分完成（约 45%，S3 未部署上线）** |
| **12. `MeetingConverter`** | `master@9a96ecf` | `master@9a96ecf`（对齐） | `master@9a96ecf`（对齐） | **0** | **0** / **0** | `7/17` / **0 轮转**（`basicConfig` 打 `stdout`） | **大部分完成（约 65%，含新 CLI/配置优先级 Bug）** |

---

## 三、逐模块深度审计详情（完成度、新代码缺陷、架构与代码质量问题）

### 模块 1：`company-wiki`（CWP，`master@d021c7976`）

1. **S1–S4 计划要求核查**：
   - **已完成**：`scheduled_summary.py:27` 改为从包内 `company_wiki.runtime_config` 加载配置（消除运行期侵入 `scripts/config.py`）；抽取 `acquisition_contracts.py`、`incremental_command.py`、`narrative_run_binding.py`、`source_request.py` 纯值模块；`acquisition_service.py:123` 引入 `AcquisitionStages` 协议消除 `coordinator._select_for_ensure/_stage_for_ensure`；`local_reconcile.py` 移除 `getattr(identity, "_*")` 反射并改用 `CatalogReader` 公开方法；`isolated_ocr.py` 与 `local_host.py` 4 处同步调用改用临时文件/`PIPE` 捕获脱敏 stderr。
   - **未完成**：
     - **S2 第一层日志缺失**：`src/company_wiki/` 下 **0 个 `RotatingFileHandler`/`FileHandler`**（全仓仅 `tools/feedback_loop/diagnostics.py:48` 在 `CWP_F4_ERROR_LOG` 下启用）；`11/11` 个 `pyproject.toml` 公开脚本入口无标准文件日志；`17/30` 个 `__main__` CLI 甚至未挂 `@runtime_feedback.entry`；**104 处 `raise ... from None` 中仍有 98 处无前置日志**（含新改过的 `isolated_ocr.py:109,170`）；`runtime_feedback.py:203-227` 旁路写失败无 `sys.stderr` 兜底；`error_taxonomy.py:103-120` 仍缺 `code_version`（含 git SHA）与 `input_ref`。
     - **S3 仓内解耦未收口**：`source_catalog/` 未按域拆分子包（反从 264 增至 **267 个扁平文件**）；全仓仍有 **15 个运行时循环依赖 SCC**（含 `_LEGACY_EDGES` 6 条永久豁免边对应的 `source_contract <-> source_catalog` 反向越层环、两个 9 文件 `source_catalog` 核心环、4 文件 `automation/narrative_model_*` 环、`narrative_run_store <-> store` 环、`tools/feedback_loop/{host,intake,local_host}` 环）；`src/`+`tools/` 仍残留 **58 处跨文件私有导入**（如 `narrative_model*.py` 仍导 `narrative_contracts._claim_from_dict/_draft_from_dict` 与 `models._to_plain`、`narrative_run_store.py:26` 导 `store._read_runtime_gate_in_transaction`、`store.py:29` 导 `migrations._open_readonly_connection`）、**62 处外部私有属性访问**（`operating_states/relations.py` 写 `prepared._*`、`structure/relations.py` 13 处读 `builder._budget`、`canonical_writer.py`/`assertion_service.py` 6 处直访 `catalog.store.*`）及 **24 处分散 `sqlite3.connect`**。
     - **S4 扫描器与静态门禁零推进**：`tests/support/layer_boundary_scan.py` 与 `tests/contract/test_layer_public_boundaries.py` 在 S1–S4 期间**零修改**，6 大盲区（同包 `_foreign()` 豁免、`<shared>` 无向规则、`tools/feedback_loop/` 未纳入、6 条 `_LEGACY_EDGES`、无 Tarjan SCC 检测、未标注参数如 `:307 def unrelated(catalog): catalog._local_cache` 放行）全部原样保留。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P1 Bug] `tools/feedback_loop/triage_diagnostic.py:18-21,37-49`（`fc2e0f31c`）白名单丢弃全部非内置异常**：`_EXCEPTION_TYPES` 仅收集 `vars(builtins)` 中的 `BaseException` 子类，导致 `.diagnostic.json` 中所有标准库子模块与业务自定义异常（如 `sqlite3.OperationalError`、`json.JSONDecodeError`、`yaml.YAMLError`、`CatalogConfigError`、`SubprocessError`）在 `:42 if exception_type is None: continue` 被**静默丢弃**，传入 Codex 分诊的 `exceptions` 变为空数组 `[]`！
   - **[P1 可观测性假象] 新增强制 `_logger.error/warning` 无 Handler 落盘（`isolated_ocr.py:228,494`、`runtime_feedback.py:204,222`、`worker_feedback.py:28,39`）**：子进程与父进程均未配置 `FileHandler`，`isolated_ocr` 父进程仅在 `_stop_worker()` 读取 stderr 尾段并调 `_logger.error`，无人值守或父进程重定向 stderr 时 OCR 崩溃堆栈依然丢失。
   - **[P2 后台唤醒导入期黑洞与隐式命名空间双加载]（`tools/feedback_loop/diagnostics.py:11,40-63`、`hook.py:46`、`intake.py:334`、`local_host.py:223`）**：3 处后台唤醒仍保留 `stderr=subprocess.DEVNULL`，依赖子进程进入 `__main__` 后执行 `run_background` 挂载 `CWP_F4_ERROR_LOG`；一旦顶层导入失败、解释器启动失败或 `argparse` 触发 `SystemExit(2)`（`diagnostics.py:58` 仅捕 `Exception`，不捕 `SystemExit`），错误直接落入 `DEVNULL`。且 `diagnostics.py:11` 写成 `from src.company_wiki.diagnostic_redaction import ...`，依赖隐式命名空间包 `src.`，造成 `sys.modules` 双模块实例。
   - **[P2 并发竞态] `tools/feedback_loop/local_host.py:43-49` 手工日志轮转无锁**：`_persist_host_stderr` 直接执行 `log_path.stat().st_size >= 2MB` 后 `log_path.replace(...)` 再 `open("a")`，多 worker 并发写失败时存在覆盖竞态与 Windows `PermissionError`。

---

### 模块 2：`filing-fetch`（FF，`origin/main@c110943`）

1. **S1–S4 计划要求核查**：
   - **已完成**：`ff_errors.py` 与 `ff_pathless_payload.py` 拆出并破除 `filing_contracts` 4 文件环，生产 `scripts/` 跨文件私有导入清零；离线矩阵 4 个文件（`cwp_readback_probe.py`、`source_proofs.py`、`et_transcript_proxy.py` 等）迁至 CWP 公开 CLI 与 FF 自有替身。
   - **未完成**：
     - **S2 标准日志与旁路兜底缺失**：`0/67` 个生产/工具文件导入 `logging`；`ff_runtime_feedback.py:190-218` 旁路写失败仍 `except Exception: return False`（零 `stderr` 告警）；`9` 处 `raise ... from None`（含 `ff_process_transport.py:145,153` 丢弃 `winerror`）无前置日志；`transcript_companion.py:144,166`、`fetch_filing.py:1814,1931`、`ff_job_store.py:81,358` 宽泛吞错未动。
     - **S3 残留跨仓导入、循环依赖与巨石**：`tools/offline_contract_matrix/seed_batch.py:32`（`from company_wiki.source_catalog import cli`）与 `cli_main.py:107-110`（内联脚本 `import company_wiki.source_catalog.cli`）**仍在直接导入 CWP 模块**；生产代码仍存 **2 个运行时环**（`fetch_filing <-> transcript_companion`、`ff_job_feedback <-> ff_job_runner <-> ff_job_store`）与 9 文件矩阵工具环；`scripts/fetch_filing.py` 仍为 **2,112 LOC**；无 `pyproject.toml`（9 处 `sys.path.insert`）。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P1 过度脱敏抹除根因] `scripts/ff_scheduled_windows.py:152-170`（`1adea74`）**：`_BUILTIN_EXCEPTIONS` 仅保留 `builtins` 异常名，导致子进程抛出的 `FilingFetchError`、`FFJobError`、`RefreshStateError`、`sqlite3.OperationalError`、`JSONDecodeError` 全部被抹除为裸 `{"exit_code": 1, "stderr_form": "python_traceback"}`（无异常类名、无文件行号、无 stderr 尾段）；且多行异常消息会使 `rsplit(b"\n", 1)[-1].partition(b":")[0]` 切错行！
   - **[P2 S4 门禁漏检] `tests/test_s3_matrix_owner_boundary.py:20`（`6afecde`）**：仅硬编码扫描 4 个文件名而非 `MATRIX.glob("*.py")`，导致同目录 `seed_batch.py:32` 的跨仓 `company_wiki` 导入直接漏过 CI。
   - **[P2 诊断黑洞] `scripts/ff_t3_receipt.py:361-365,406-408`（`c110943`）**：执行原生 T3 套件时用 `redirect_stdout(devnull), redirect_stderr(devnull)` 吞掉子组件警告，且 `get --latest` 遇 `OSError`/`TimeoutError` 时输出 `"run_id": null` 无错误原因。
   - **[P0 现场三方漂移]**：`origin/main` 在 `c110943`，本机主仓与 F4 `settings.json` 运行路径停在 `main@711db1c`（**缺少 `scripts/ff_t3_receipt.py`**，RF 周测调用本机路径将直接报文件不存在），而 `.agents`/`.claude`/`.gemini/config`/`.codex` **全部 4 套全局安装技能仍停留在 S1 之前的 `1defca5`（23/35 个 `.py` 文件过期，定时任务仍是双 `DEVNULL`）**！

---

### 模块 3：`earnings-transcripts`（ET，`main@2fc8f92`）

1. **S1–S4 计划要求核查**：
   - **已完成**：`transcript_api.py` 4 处 provider 入口捕获异常时记录结构化 `exception_trace`（类型+因果+帧）并传入 `worker_error.json` -> F4 旁路；公开 `BudgetSession` 与 `transcript_preflight` 5 个校验函数（清零 8/9 处私有导入）。
   - **未完成**：
     - **S1/S2 日志与吞错问题未根治**：未将崩溃 worker 日志持久化到轮转日志，反而将 `retrieval_runtime.py:218` 改为 `stderr=subprocess.DEVNULL`；`config.py:33` 与 `scraper.py:252` 仍是无轮转 `FileHandler` 且 `propagate=False`；`scraper.py:1790-1791` **写 manifest 失败仍未置 `exit_code = EXIT_FAILURE`（继续退出 0！）**；`transcript_feedback.py:1439` **仍在捕获 `except BaseException:`** 且全文件 9 处旁路写失败零 `stderr` 告警。
     - **S3/S4 余项**：`common.py:26` 仍导 `_OpenAITranslator`，`replay_feedback_case.py:245-265` 仍 monkey-patch 私有函数，5 处 `sys.path.insert` 与 3 个 1,400–2,194 LOC 巨石未拆；**仓库无 `.github/workflows`（零远端 CI）**、零静态 AST 门禁。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P1 新增导入期/原生崩溃黑洞与生产静默] `retrieval_runtime.py:218-221` + `transcript_tool.py:144`**：worker 子进程 `stderr=subprocess.DEVNULL`，若在进入 `retrieval_worker.main()` 前发生 `ImportError`、C 扩展崩溃或磁盘满导致 `worker_error.json` 写失败（`retrieval_worker.py:134: except OSError: pass`），诊断信息 100% 归零；且 FF 生产调用必传 `--report-usage`，使 `transcript_tool.py:144` 中 `log_worker_diagnostics=not args.report_usage` 恒为 `False`，父子进程标准日志全部关闭！此外 `retrieval_worker.py:141` `failing()` 传 `trace=None`，预检失败不写任何原因。
   - **[P2 帧文件名正则误删堆栈] `retrieval_diagnostics.py:28,80-82`**：`_FILE = re.compile(r"[A-Za-z_][A-Za-z_0-9.]{0,127}")` 不允许连字符 `-` 和 `<frozen ...>`，导致含 `-` 的模块或 `importlib` 引导期堆栈帧被静默丢弃。

---

### 模块 4：`StockInfoDLSimple`（SID，`v2-clean-rewrite@1d02afd`）

1. **S1–S4 计划要求核查**：
   - **已完成**：`src/logger.py` 移除空 handlers 短路并改用 `RotatingFileHandler`；`src/browser.py:645` 区分 `PlaywrightTimeoutError` 与其他异常抛 `BrowserError(...) from exc`；抽取 `src/disclosure_matching.py` 清零全仓跨文件私有导入与外部私有属性（0 SCC、0 私有导入、0 私有属性）。
   - **未完成**：
     - **S1/S2 最大生产盲区**：**CWP 实际调用的生产入口 `src/company_wiki_adapter_cli.py` 从未调用 `setup_logger(log_file=...)`**，导致线上 A 股采集 100% 仍无轮转文件日志落盘！`src/logger.py` 无凭据脱敏、无结构化信封字段；`src/browser.py` 仍有 15+ 处宽泛静默 `except Exception`；`src/feedback_owner.py:459` 仍吞 6 类异常为固定串；21 处 `log.error/warning` 缺 `exc_info=True`；`feedback_publish.py:785` 旁路写失败仅记 `log.debug` 无 `stderr` 兜底。
     - **S4 缺失**：`v2-clean-rewrite` 分支**无 `.github/workflows`（零远端 CI）**，无静态 AST 门禁与 CLI 级日志活性测试。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P2 文件句柄泄漏与 `console=False` 失效] `src/logger.py:11-58`（`24ce0be`）**：`:58` 在导入期仍无参执行 `log = setup_logger()` 挂载默认 `StreamHandler`；后续调用 `setup_logger(console=False, log_file=...)` 不会移除已有 `StreamHandler`；若多次切换 `log_file`（如测试或多任务），旧 `RotatingFileHandler` 从未 `close()` 或移除，在 Windows 上造成文件锁残留（`WinError 32`）与重复写日志。

---

### 模块 5：`revenue-forecast`（RF，`origin/main@b9e59db4`）

1. **S1–S4 计划要求核查**：
   - **已完成**：`rf_job_facade.py:968-984` 补齐日志与 `from exc`，并显式传递 `attempt_no`（消除 `runner._pending_attempt_no`）；退役 `processed_artifact_canary.py` 直查 CWP SQLite 及日/周/月测外仓私表读取（仅剩 `tools/slo_probe.py:25-26` 仍硬编码 `.source_catalog/catalog.sqlite3`）。
   - **未完成**：
     - **S2 第一层日志与吞错未修**：`0/153` 个生产文件配置 `RotatingFileHandler`/`FileHandler`（仅 2 文件 `import logging`）；`16/20` 个 `scripts/*.py` CLI 未接入 `@observed_entry`；`scripts/contracts/document.py:1210,1258,1323` 仍把引擎代码 Bug 吞成校验错；`rf_feedback_outbox.py:98` 与 `rf_cli_feedback.py:115,137` 旁路写失败零 `stderr` 兜底。
     - **S3 `report_catalog` 环与私有耦合未解**：仅拆出 37 行 `report_catalog_common.py`，原 7 文件环分裂为 **5 文件环 + 2 文件环 + `rf_job_facade <-> rf_job_feedback` 环（共 3 个运行时 SCC、134 处延迟导入）**，仍存 **61 处跨文件 `_private` 导入**与 **24 处外部私有属性访问**（`catalog._*` 21 处、`self.store._creation_lock/_require_job_id`）。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P0 CI 门禁失明] `tools/pre_push_gate.py:76-128` + `.github/workflows/quality.yml:39`**：GitHub Actions CI 仅运行 `CI_TESTS` 硬编码元组中的测试文件，**本轮 S1–S4 新增/修改的全部 10 个测试文件（`test_s1_p0_error_observability.py`、`test_module_boundary_closure.py`、`test_daily_t2_public_sources.py`、`test_weekly_t3_owner_receipt.py`、`test_rf_job_feedback_roots.py` 等）0 个加入 `CI_TESTS`**，所谓“远端同版 CI 通过”完全没有执行任何 S1–S4 新增测试！
   - **[P1 S2 回退 S1 修复] `scripts/filing_fetch_client.py:34-37,376-393`（`1b471df4`）**：删除了 S1（`db4f8c7a`）添加的 `_logger` 与 `_redacted_stderr_excerpt`，子进程除 `^(ImportError|ModuleNotFoundError):` 外的一切崩溃 stderr 再次 100% 丢失且无本地日志。
   - **[P2 单根与去重不一致漏报 `native_owner_unverified`] `scripts/rf_job_feedback.py:83-85,104-106`（`b9e59db4`）**：`:105` 写为 `"native_owner_unverified" if len(roots) > 1 else None`，导致单资料根（或软链接去重后为 1 个根）下作业状态损坏时丢弃错误码，静默退化为普通 `unknown`；且 `:85` 用去重前 `len(owner_roots)` 而 `:105` 用去重后 `len(roots)`。
   - **[P2 脆弱英文前缀匹配] `tools/cwp_catalog_status.py:24-31`（`7409098d`）**：靠 `message.startswith("catalog does not exist...")` 匹配 CWP 人类可读文本而非结构化错误码。
   - **[P0 现场脑裂与全局技能过期]**：主工区停在 `main@d62fca9a`（缺 S2–S4），F4 `settings.json:878-921` 中 `cwd` 与 `report` 跑 `.worktrees/f4-runtime@597c6bc2`（S1 前旧版），而 `reconcile` 跑 `.worktrees/f4rd@b9e59db4`；4 套全局安装技能有 **46 文件漂移 + 26 文件缺失**，且**仍包含直连 CWP SQLite 的旧版 `processed_artifact_canary.py`**！

---

### 模块 6：`revenue-forecast-audit`（Audit，`main@8267a8a`）

1. **S1–S4 计划要求核查**：
   - **已完成**：抽取 `financial_measure_core.py`（574 LOC）破除 `financial_measure_audit <-> financial_measure_evidence` 循环依赖并消除 `measure._time_str()`（0 SCC、0 私有导入、0 外部私有属性）；`audit_delivery.py` 增加投递失败 `stderr` 告警。
   - **未完成**：`0/46` 个文件使用 `logging`；`feedback_owner.py:393-395` 仍只输出异常类名；`audit_run.py:776` 静默吞 `OSError`、7 处无日志 `from None`、`run_pool_progress_e2e.py:218` `stderr=DEVNULL`、16 处 `sys.path` 注入（含 `audit_run.py:809` 运行期注入）均未动；无 `.github/workflows`（无远端）、无静态 AST 门禁。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P1 Bug] `audit_delivery.py:130-144`（`206c93bf`）`exported_without_journal` 漏存 `failure` 导致 F4 `reconcile` 永久 `unknown`**：当 SQLite `_journal()` 抛错时，代码调用 `_export(token, batch)` 将含 `evidence_ref="audit-cli/1/<id>"` 的观察投递给 F4，但**从未将 `failure` 详情写入任何回退文件**；随后 F4 回调 `feedback_owner.py reconcile` 时，`failure_receipt(id)`（`:166-172`）只查 SQLite `failures` 表得 `None`，永久返回 `{"state": "unknown"}`！且双写均失败时 `:143` 用后错覆盖前错 `journal_error`。
   - **[P1 全局技能未同步]**：`.agents`/`.claude`/`.gemini/config` 下的 `revenue-forecast-audit` 技能仍停留在 S2/S3 前版本（**缺少 `financial_measure_core.py`**），且 `.codex/skills/revenue-forecast-audit` 整目录缺失。

---

### 模块 7：`StockWiki`（`master@dd5b033`，本地无远端）

1. **S1–S4 计划要求核查**：
   - **已完成**：修复 `dashboard_onboarding.py:548` 死三元分支；`WorkDelegationPorts` + `publish_record()` 消除 `quick_scan_work_delegation` 12 处私有调用并破除 1 个环（4 环降至 3 环）；`dd5b033` 隔离 `observations/native` 收件目录。
   - **未完成**：
     - **S1/S2 未闭环**：`0/268` 文件配置日志 Handler；`documents.py:391`（`parse_html`）与 `llm_usage_ledger.py:155,163`（`summarise`）仍静默吞错；`ui.py:251` `log_message` 仍为空 `return` 且未捕获服务端异常仍返 HTTP `400` 并回显裸 `str(exc)`；`public_company_assessments.py:1136,1287,1566` 仍把 `sqlite3.Error`（含锁冲突/损坏）静默吞为 `None`；`runtime_feedback.py:271,300,308` 旁路写失败无 `stderr` 告警；79 处 `from None` 无前置日志。
     - **S3 Store 绕过与私有耦合大部分未动**：**~19 个模块仍绕过 Store 调 `store._connect()`/`_read_connect()` 或原生 `sqlite3.connect`（全仓 67 处）**，连新抽出的 `security_id_normalization_store.py:80-107` 仍继承 `QuickScanStore` 调 `self._save_prepared`/`self._prepare` 并写裸 `UPDATE`；仍存 **3 个运行时 SCC**、**37 处外部 `obj._*` 调用**、**35+ 处跨域 `_private` 导入**及 7 个根 CLI `sys.path` 注入。
     - **S4**：新增 S1–S4 测试未加入 `scripts/checks.py:SHORT_TESTS`；无全仓 A2/A3/L1–L4 静态门禁。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P1 跨库非原子提交与锁嵌套风险] `stockwiki/security_id_normalization_store.py:283-310`（`6a3e67d5`）**：`complete()` 在持有 `scan.sqlite` `BEGIN IMMEDIATE` 写事务及全库 `_business_guard(lock=True)` 期间，先在 `:292`（锁外 TOCTOU）和 `:297,:308` 打开多个独立只读连接，更在 **`confirm_public_resolution(operation)`（`:308`）与 `con.commit()`（`:310`）之前就向另一数据库 `identity_receipts.sqlite` 提交了 `record_reanchored_receipt` 与 `supersede_if_active`（`:300-303`）**！若 `:308` 或 `:310` 失败，`scan.sqlite` 回滚至 `entity_saved`，但旧 receipt 在 `identity_receipts.sqlite` 已永久变为 superseded，重跑将在 `identity_receipts.py:285` 因旧 receipt 非 active 而卡死！
   - **[P2 重复发布冲突误报與拼写缺陷]**：`stockwiki/runtime_feedback.py:332-334`（`dd5b0338`）在 `observations/native` 与旧 `observations` 存在字节完全相同的未发布 `.cause.json` 时，`read_failure(ref, republish=True)` 误抛 `ValueError("runtime_ref_conflict")`；`quick_scan_work_delegation.py:242`（`b18e88c4`）错误码漏下划线写成 `"work_delegationnative_paths_required"`；`llm_usage_ledger.py:137`（`665f6a85`）删掉了 S1 刚加的 `exc_info=True`。

---

### 模块 8：`invest-quick-scan`（IQS，`master@3a07832`）

1. **S1–S4 计划要求核查**：
   - **已完成**：`stockwiki_g2b_acceptance.py` 移除 StockWiki `tests/*` 路径注入及 17 处邻仓私有/内部导入，改走公开 CLI 与 SHA 黄金校验；`provider_transport.py` 增加 HTTP 传输失败 F4 诊断。
   - **未完成**：
     - **S2**：**`0/318` 个生产文件导入 `logging`**；仍有 **69 处 `except Exception`（46 处既不重抛也不记 F4 观察，如 `dashboard_batches.py:761`、`dashboard_jobs.py:154` 80ms 锁忙即丢弃错误态）** 和 **52 处无日志 `from None`**；诊断信封缺 `timestamp_utc`、git SHA、`input_ref`。
     - **S3**：`scripts/iqs_scan/workbench/iqs_temporal_vendor/legacy_oracle.py:3,7` **仍直接导入 `stockwiki.quick_scan_freshness`**；**未创建 `pyproject.toml`**，顶层 `scripts/*.py` 的 `sys.modules[__name__]` 双身份垫片反而从 142 增至 **144 个**，7 处生产 `sys.path` 修改保留。
     - **S4**：无 `.github/workflows`（零远端 CI），无全仓 A1–A4 / L1–L4 门禁。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P1 未捕获异常崩溃] `scripts/iqs_scan/providers/provider_transport.py:27-53`（`fb3fcbe7`）**：`urllib.request.Request(url, ...)` 在 `try:` 块之外，且 `response.read()` 抛出的 `http.client.IncompleteRead`（继承自 `HTTPException`，**不属于** `OSError`/`URLError`/`ValueError`）未被捕获，直接穿透崩溃，违背该函数“所有传输结果均返回 `(status, payload)`”的契约。
   - **[P2 同阶段去重吞掉后续不同题目故障] `provider_transport.py:16-21` + `runtime_feedback.py:192-198`**：按 `[OWNER, run, attempt, stage, "operation-outcome"]` 哈希落盘且文件已存在即直接返回；单次公司扫描所有题目共用 `(run_id, attempt_id)`，第 1 题触发 `provider.http/transport_error` 后，后续题目发生不同根因的传输/解码错误全部被静默丢弃。
   - **[P2 参数静默失效] `stockwiki_g2b_acceptance.py:62-69,214-222`（`3a07832`）**：仅传 `--stockwiki-root` 时活体验真被静默跳过却仍在输出 JSON 写入 `stockwiki_root`；子进程崩溃空 stdout 时 `json.loads` 错误吞掉 `result.stderr`。
   - **[P0 现场检出滞后]**：F4 `settings.json:743` 运行 `.worktrees/f4-runtime@aa847ac`（2026-11-23），主工区在 `50fe2b1`，**均未包含 S2（`fb3fcbe`）与 S3（`3a07832`）代码**！

---

### 模块 9：`investment-dashboard`（Dashboard，`origin/main@e563354`）

1. **S1–S4 计划要求核查**：
   - **已完成**：`04064e1` + `71b2659` 将 `backend/dashboard/application/ops/*` 的 41 处 `DashboardService._*` 私有调用收口为显式窄端口（清零 `ops/*` 私有调用与 `TYPE_CHECKING` 环）；`a3523e8` + `e563354` 打通前端 `shared/api.ts` 与 `OriginalPreview.tsx` 的超时、取消、`correlationId` 展示及后端 `feedback_owner.py get-diagnostic` 只读冷查。
   - **未完成**：
     - **S2**：`transport/http.py`、`application/service.py`、`request_feedback.py`、`scripts/feedback_owner.py` **零 `logging`、零轮转日志**；`backend/dashboard/adapters/common.py:23-24` `fail()` **仍不接收 `cause` 参数**（全适配器抛 `OwnerPortError` 丢失 `__cause__`）；`service.py:458-476`（`_find_job`）与 `:534-545` 仍静默吞掉 `OwnerPortError`（上游挂掉被伪装成不存在或空列表）；**`request_feedback.py:325-329` 旁路写失败仍静默 `pass` 无 `stderr` 告警**。
     - **S3 适配器层私有访问原封未动**：`adapters/forecast.py:22` 与 `forecast_scope.py:49,71,118,186` 仍导 7 个 `forecast_common._*` 且 `:125` 调 `adapter._deployment_args()`；`ff_scheduled_refresh.py:26` 仍导 `ff_job._cli_result`；`identity.py:155` 仍调 `self._fallback._read()`；`scripts/f2_dash_feedback_sample.py:29,35` 仍注入 `sys.path` 导 `tests` 私有 `_owner_stub`（全后端仍有 33 处同层跨文件私有导入）。
     - **S4**：**无 `.github/workflows`（零远端 CI）**；现有边界测试豁免 `adapters/*` 同层跨文件私有导入且未扫描 `scripts/`；无 L1–L4 门禁。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P1 幽灵 `correlation_id` 陷阱] `backend/dashboard/request_feedback.py:267-330`（`a3523e8`）**：当侧车目录因权限/只读/满盘写失败时，`:325-329` 静默吞错（`state.recorded=False`），但 `:330` **照常向 HTTP 响应头/体返回该未落盘的 `correlation_id`**，前端向用户展示 `相关号 <id>`，运维执行 `get-diagnostic <id>` 却静默得到 `{"diagnostic": null}` 且全链路无一行 `stderr`/日志！
   - **[P2 前端预览错误信息丢失与超时竞态] `OriginalPreview.tsx:34-38` + `shared/api.ts:37-43,75`（`e563354`）**：无 `correlationId` 的 4xx/413 错误在 `OriginalPreview` 中丢失 `error.code` 与 `error.owner`，且 Dashboard 自身拒绝也被硬编码显示为 `"owner 原件不可用"`；`api.ts` 先挂 `setTimeout` 再检查 `callerSignal?.aborted`，事件循环阻塞时可能把调用方取消误报为 `ApiTimeoutError`。
   - **[P2 过度闭包包装与主工区滞后]**：`service.py:34-38,125-198` 用 ~35 个无签名 `invoke(*args, **kwargs)` 闭包隐藏 `__self__`，抹除函数名与签名；本地主工区 `C:\Users\郑曾波\projects\investment-dashboard` 仍停在 `main@ead3425`（落后 `origin/main` 与 `.worktrees/f4dv` 4 个 S2/S3 提交）。

---

### 模块 10：`StockQAbyLLM`（StockQA，`origin/master@a89636f`）

1. **S1–S4 计划要求核查**：
   - **已完成**：`llm_provider.py` / `async_llm_provider.py` 对 `TypeError`/`KeyError` 等编程错快速失败并加 `exc_info=True`；`execution_feedback.py` 补齐旁路失败 `stderr` 告警；`tests/unit/test_quick_scan_module_boundaries.py` 落盘 A1 门禁（`src/` 跨文件 `_private` 导入清零）；`cff6b3d3`/`a89636f` 去除异常链 16 层截断与重复 `_authorize`。
   - **未完成**：
     - **S2**：`src/utils/logger.py:378` 仍是无轮转 `FileHandler`，且 **`11/14` 个 `__main__` CLI 零日志 Handler**；仍有 **12 处 `raise` 丢 `from e`**、**59 处 `logger.error/warning` 缺 `exc_info=True`**、`llm_runner.py:1680-1683` 仍把损坏 checkpoint 吞成 `None`。
     - **S3 头号 P0 目标基本未动**：仅拆出 508 行 `quick_scan_work_values.py`，`src/utils/quick_scan_work_store.py` 仍高达 **7,081 LOC**，`src/utils/*quick_scan*.py` 仍构成 **30 文件运行时巨环（474 处延迟导入；全 `src/` 为 58 文件巨环、597 处延迟导入）**；`llm_runner.py:3066,3183,3187` 仍直读 `work_lifecycle._lease_seconds/_store/_owner_refresh`（全仓仍有 **60 处外部私有属性/反射访问**）。
     - **S4**：缺 A2/A3/L1–L4 门禁，且 S1 新增测试 `test_s1_p0_provider_and_subprocess_logging.py` 漏加入 `scripts/checks.py:DAILY_TEST_TARGETS`。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P0 安全/凭据泄露 Bug] `quick_scan_owner_research.py:42`、`quick_scan_owner_budget_permissions.py:23`、`quick_scan_work_decision_authority.py:32`（S1 `1449d715`）**：`_STDERR_REDACT_RE` 使用 `(authorization)(\s*[:=]\s*)([^\s,;\"']+)`，遇到 `Authorization: Bearer <secret_token>` 时仅将 `"Bearer"` 替换为 `[REDACTED]`，**把真正的 `<secret_token>` 明文留在日志中**！且 `quick_scan_owner_research.py:477-479` 用 `err_stream.seek(0); err_stream.read(8192)` 截取 **头部** 8KB 而非尾部，长日志下直接截断底部的 Python Traceback！
   - **[P1 S3 新引入环境泄漏回归] `src/utils/_quick_scan_owner_refresh_port.py:398` vs `quick_scan_owner_refresh.py:148`（`a3c2c720`）**：`OwnerRefreshClient` 将 `self._environment` 改名为 `self._process_env`，但 `_quick_scan_owner_refresh_port.py:398` 仍在执行 `getattr(client, "_environment", None)` 并回退到 `os.environ`！导致传入 `OwnerRefreshClient(config, process_env=...)` 的隔离环境变量在 `subject_dispatch_setup()` 中 **100% 静默失效并泄漏宿主 `os.environ`**（若测试替身定义 `_environment()` 方法更直接抛 `TypeError: 'method' object is not iterable`）！
   - **[P0 现场检出严重滞后]**：F4 `settings.json:922` 指向 `C:\Users\郑曾波\Projects\StockQAbyLLM`，当前停在 `codex/qa-content-filter-resolution-01@a3c2c72`，**缺失 `origin/master` 后续全部 8 个 S2/S3/S4 提交**！

---

### 模块 11：`industry-research`（IR，`origin/main@1c98102`）

1. **S1–S4 计划要求核查**：
   - **已完成（仅在 git `origin/main`）**：`b3893f0` + `1c98102` 抽离 `report_format.py` 与 `report_output.py`（修复复用作文件描述符误关问题），公开 `QuickScanClient.resolve_consumer_path`（清零跨文件私有导入与私有属性）；`86d930f` 去除 DeepSeek 原始返回体输出。
   - **未完成**：`0/10` 个生产文件导入 `logging`；`deepseek_client.py:117,125,134,659-703` 仍用 `print` 把错误打到 `stdout`；`feedback_owner.py:281-283` 仍吞 6 类异常为固定串；**`native_feedback.py:178-181` 旁路写失败仍静默 `return` 无 `stderr` 告警**；**`tools/quick_scan_client.py` 仍为 2,820 LOC（未拆分）**；**无 `.github/workflows`（零远端 CI）**。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P0 S3 完全未部署上线]**：本机仓库 `C:\Users\郑曾波\projects\industry-research`（F4 `settings.json:612` 直接运行此目录！）仍检出在 S2 分支 `codex/s2-ir-deepseek-diagnostics-20261124@a055204`，且 `.agents`/`.claude`/`.gemini/config`/`.codex` **全部 4 套安装技能也停留在 `a055204`（缺少 `report_format.py` 和 `report_output.py`，且 `install_reporting_tools.py` 从不同步 `SKILL.md` 与 `modules/*.md`）**！
   - **[P1 异常误判导致额外付费重试与无意义等待] `tools/deepseek_client.py:107-113,131-140`（`86d930f`）**：`response.json()` 抛出的 `requests.exceptions.JSONDecodeError` 是 `RequestException` 的子类，被 `:131 except requests.exceptions.RequestException` 误判为 `"transport_error"` 并**额外重试 2 次付费大模型请求**；而 HTTP 429 在最后一次尝试（`attempt == max_retries - 1`）失败后仍白白 `time.sleep(15)` 再抛错；`main()` 对裸 `Exception` 传 `messages=False` 导致本地 JSON 提取失败全部只剩 `"reason": "Exception"`。

---

### 模块 12：`MeetingConverter`（MC，`master@9a96ecf`）

1. **S1–S4 计划要求核查**：
   - **已完成**：修复 `engines/mimo.py` `NameError` 与 `core/feedback.py` `BaseException`；脱敏 MiMo 重试与 8 层异常链归因；`company.py` 移除外仓 `~/company-wiki/graph.yaml` 硬编码；统一 `config.py` 配置源与默认 `DEFAULT_MIMO_URL`；具备活跃 `.github/workflows/ci.yml`。
   - **未完成**：
     - **S2**：`0/24` 文件使用 `RotatingFileHandler`；`transcribe.py:116-120` 仍将 `basicConfig` 绑定到 `sys.stdout` 并用 `logger.info` 打印致命错误；`translator.py:89,92` 仍把原始 `urllib` 异常未脱敏拼入日志（无 `exc_info=True`）；`fallback.py:68`、`pipeline.py:227` 仍缺 `exc_info=True`；`batch.py:128-133` 仍割裂 `traceback.print_exc()`。
     - **S3/S4**：`core/pipeline.py:343` 仍耦合 `isinstance(engine, FallbackEngine)`；**`audio_utils.py:137-153` 仍未检查 `ffmpeg` 退出码（失败时把 0 字节临时文件送入转录引擎！）**；`core/feedback.py` 1,483 LOC 巨石未拆；无静态 AST 门禁与轮转日志活性测试。
2. **S1–S4 新写代码审计发现的问题**：
   - **[P1 功能回归 Bug：`config.json` 引擎配置死代码 & CLI 参数优先级倒置] `transcribe.py:85-88,152-187`（`9a96ecf`）**：
     1. `--engine` 的 `default=Config.transcription_engine` 为非空字符串 `"auto"`，导致 `:186 engine_choice = args.engine or settings.transcription_engine` 永远短路取 `args.engine`，用户在 `config.json` 中配置的 `"transcription_engine": "whisper"` 或 `"mimo"` **100% 失效**！
     2. `:152-160` 构造 `{**cli_defaults, **raw}`，使 `config.json` 中的值**反向覆盖用户在命令行显式传入的 `--model`、`--device`、`--compute-type` 参数**！
   - **[P1 校验绕过] `config.py:67-113` + `transcribe.py:160` / `translator.py:64` / `engines/factory.py:34`（`9a96ecf`）**：所有运行期入口均调用 `normalize_config()`（`Config.from_dict()`），**完全绕过了 `_validate()`**（例如 `"translate_max_retries": 0` 会使 `translate_paragraph` 隐式返回 `None` 导致批处理中途崩溃；且 `_validate` 中 `isinstance(True, int)` 未排除 `bool`）。
   - **[P2 连接泄漏与 HTTP 200 结构错重试] `engines/mimo.py:197-247`（`1bddabc`/`45f5a6d`）**：捕获 `urllib.error.HTTPError` 后未调用 `e.close()` 即进入 `time.sleep(wait)` 泄漏底层 socket；HTTP 200 缺 `choices` 抛 `KeyError` 会白白重试 3 次付费请求且 `from None` + `_source_location` 过滤后仅剩 `KeyError @ mimo.py:199`；`company_manager.py` 未同步支持 `position`/`sectors` 参数且 `company.py:131` 遇 YAML 空节点会抛 `AttributeError`。

---

## 四、后续整改分期建议（S5 收口清单，按优先级）

1. **S5-P0（立即止血：部署对齐、凭据脱敏、CI 假绿修复、新引入功能回归）**：
   - **同步现场检出与全局技能**：对齐 `FF`（本地快进 `c110943` + 同步 4 套技能）、`RF`（统一 F4 `settings.json` 至 `b9e59db4` + 同步 4 套技能移除旧 SQLite canary）、`IR`（切换本机至 `main@1c98102` + 运行安装器同步 `report_format.py`/`report_output.py` 与文档）、`Audit`（同步技能补齐 `financial_measure_core.py` 并补 `.codex` 副本）、`IQS`（更新 `f4-runtime` 至 `master@3a07832`）、`StockQA`（更新主仓至 `origin/master@a89636f`）、`Dashboard`（快进主仓至 `e563354`）。
   - **修补 S1–S4 新引入的高危 Bug**：
     1. `StockQAbyLLM`：修复 `_STDERR_REDACT_RE` 对 `Authorization: Bearer <token>` 的凭据明文泄露 + `err_stream` 改读尾部 + 修复 `_quick_scan_owner_refresh_port.py:398` `getattr(client, "_environment")` 漏改回归；
     2. `revenue-forecast`：将全部 10 个 S1–S4 测试文件补入 `tools/pre_push_gate.py:CI_TESTS`，并在 `filing_fetch_client.py` 恢复本地脱敏错误日志记录；
     3. `MeetingConverter`：修复 `transcribe.py` `--engine` 默认值短路与 CLI 参数被 `config.json` 覆盖的优先级倒置，在 `normalize_config()` 接入 `_validate()`，在 `audio_utils.py` 检查 `ffmpeg` 退出码，在 `mimo.py` 关闭 `HTTPError`；
     4. `company-wiki`：放宽 `triage_diagnostic.py` 异常类名提取（保留自定义与标准库子模块异常类名），修复 `local_host.py` 轮转竞争与唤醒子进程启动期错误捕获；
     5. `filing-fetch` / `revenue-forecast-audit` / `investment-dashboard` / `industry-research`：修复 `ff_scheduled_windows.py` 非内建异常被抹除、`audit_delivery.py` `exported_without_journal` 丢失 `failure` 致 `reconcile` 永久 `unknown`、`request_feedback.py` 写失败返回幽灵 `correlation_id`、`deepseek_client.py` `JSONDecodeError` 误重试付费接口。
2. **S5-P1（补齐原 S2 双层轮转日志与旁路 `stderr` 兜底）**：
   - 为仍为 0 `RotatingFileHandler` 的仓库（`CWP`、`FF`、`RF`、`Audit`、`StockWiki`、`IQS`、`Dashboard`、`IR`、`MC`）及 `SID` `company_wiki_adapter_cli.py`、`ET` `transcript_tool/worker`、`StockQA` 11 个 CLI 补齐真正的本地轮转脱敏日志与 F4 旁路写失败 `sys.stderr` 一行告警。
3. **S5-P2（完成原 S3 核心破环与 S4 静态门禁 + 缺席 CI 工作流）**：
   - 清掉剩余 2 处跨仓导入（FF `seed_batch.py:32`、IQS `legacy_oracle.py:3,7`）与 RF `slo_probe.py` 路径硬编码；
   - 分阶段推进 StockQA `quick_scan_work_store` 三层 DAG 破环、CWP `source_catalog` 子包化与 `_LEGACY_EDGES` 清零、StockWiki Store 封装收口、RF `report_catalog*` 破环、Dashboard `adapters/*` 私有导入公开化；
   - 修复 CWP `layer_boundary_scan.py` 6 大盲区，落地 A1–A4 / L1–L4 静态门禁与 1 秒轮转日志活性测试，并为 `ET`、`SID`、`IQS`、`Dashboard`、`IR` 补齐 GitHub Actions CI 工作流。
