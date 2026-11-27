# 全 12 模块深度审查发现报告（2026-11-27 实时源码基线）

> **审查性质**：严格只读全量审查（**零生产代码修改、零配置修改、零外仓写入、零付费/网络请求**）。
> **审查基线**：2026-11-27 对全部 12 个自有模块（**2,039 个生产 Python 文件 / 524,419 LOC** + `investment-dashboard/apps/web` TypeScript/React 前端 + 约 **20,000+ 条测试函数**）的**最新实际发布检出**执行：（1）全量 AST/正则/Git/CI 自动化定量扫描；（2）四路并行架构师级逐文件深度源码审查；（3）直接核验全部 `.github/workflows/*.yml` 与 `scripts/checks.py` / `tools/pre_push_gate.py`。
> 本文记录 2026-11-27 的审查基线；当前派工与验收见 [task_plan.md](task_plan.md) 和 [progress.md](progress.md)。

---

## 一、全 12 模块实时定量与状态总表（2026-11-27）

| # | 模块 | 实审发布检出与 SHA | 主工作区漂移 / Worktree 数 | 生产文件 / LOC | 运行时环 SCC / 延迟导入 | 跨文件私有导入 / 外部私有属性 / SQLite 直连 | 标准 `logging` / 轮转模块 / 无日志 `from None` / 静默吞错 | 测试文件 / E2E 文件 / CI 现状 |
|---|---|---|---|---:|---|---|---|---|
| 1 | **company-wiki (CWP)** | `master@67bd4ff4d` | 对齐 / **15 wt** | 812 / 237,650 | **18 环 (5 顶层)** / **1,706** | 78 / 130 / **54** | 27/812 / 1 (`diagnostic_logging.py`) / **83** / **80** | 1,253 / 254 / `ci.yml` **仅 Ubuntu + 硬编码子集**；`source-system.yml` 不因 `src/**` 触发 |
| 2 | **filing-fetch (FF)** | `main@4dd4e13ec` | 对齐 / **29 wt** | 78 / 23,694 | 0 / 100 | 13 / 4 / 0 | 1/78 / 1 (`ff_runtime_log.py`) / 8 / 6 | 109 / 15 / `quality.yml` **仅 Ubuntu + 硬编码 55 文件**，跳过 Windows 定时与隔离 E2E |
| 3 | **earnings-transcripts (ET)** | `main@672ed1012` | 对齐 / 3 wt | 34 / 12,440 | 0 / 10 | 0 / 11 / 2 | 8/34 / 1 (`runtime_logging.py`) / 0 / 8 | 36 / 2 / `ci.yml` **仅跑 4 文件+7 用例（Ubuntu）**，跳过全部 S1/S2/F4/batch/reader 测试 |
| 4 | **StockInfoDLSimple (SID)** | `v2-clean-rewrite@5c6560502` | 对齐 / 2 wt | 30 / 8,324 | 0 / 30 | 0 / 0 / 2 | 1/30 / 1 (`src/logger.py`) / 1 / 11 | 45 / 8 / `ci.yml` **仅跑 7 文件+2 用例（Ubuntu）**，跳过 `cninfo_api`/`downloader`/`adapter` |
| 5 | **revenue-forecast (RF)** | `.worktrees/f4rd@782cfd9a` (`origin/main`) | **严重分叉**：主仓停在 `d62fca9a` / **26 wt** | 161 / 49,589 | **1 环** / **148** | 22 / 19 / 2 | 2/161 / 1 (`rf_local_diagnostics.py`) / 1 / 3 | 259 / 25 / `quality.yml` 含 `windows-lifecycle`(4 文件)，但主套件仍为**硬编码 75 项 `CI_TESTS`** |
| 6 | **revenue-forecast-audit (Audit)** | `main@9e9e98096`（无远端） | 对齐 / 3 wt | 49 / 19,710 | **1 环 (6 文件工具)** / 2 | 0 / 0 / 2 | 1/49 / 1 (`audit_diagnostics.py`) / 3 / 0 | 51 / 1 / **零 CI 工作流、无远端、无 `pyproject.toml`** |
| 7 | **StockWiki** | `master@0fbaf7ce3`（无远端） | 对齐 / **31 wt** | 281 / 79,985 | **3 环** / **244** | **290** / **34** / **66** | 6/281 / 1 (`runtime_feedback.py`) / **82** / 10 | 188 / 11 / 无远端；`ci.yml` **仅 Ubuntu + `SHORT_TESTS` 子集** |
| 8 | **invest-quick-scan (IQS)** | `.planning/wi26@3094c5f7` (`origin/master`) | **漂移**：主仓停在特性分支 `50fe2b1` / **18 wt** | 321 / 39,816 | 0 / **280** | 6 / 2 / 15 + **145 `sys.modules` 垫片** | 1/321 / 1 (`runtime_log.py`) / **52** / 3 | 156 / 11 / `quality.yml` **仅 Ubuntu + 7 文件+1 用例**（跳过 148+ 测试文件） |
| 9 | **investment-dashboard (Dashboard)** | `release-de59feed@de59feed` | **4 路分叉**：`main@fd4d62d` / `origin@41ddcf6` / `release@de59fee` / PWF `fcd464e` / **34 wt** | 96 / 18,528 (+前端 TS) | **1 环 (adapters)** / 49 | 35 / 9 / 5 | 3/96 / 1 (`request_feedback.py`) / 1 / 5 | 401 / 167 / `feedback-contracts.yml` 含 Win+Ubuntu 但**仅跑 3 后端+3 前端文件**，不跑 `typecheck`/`build`/Playwright；`testpaths` 排除 `adapters/` |
| 10 | **StockQAbyLLM (StockQA)** | `.worktrees/f4-runtime@86f633d8` (`origin/master`) | **漂移**：主仓停在 `a3c2c72` / 4 wt | 129 / 59,133 | **1 巨环 (23 文件)** / **384** | 8 (`api_*` 伪公开) / **46** / 11 | 5/129 / 自建 `_DailyFileHandler` / 19 / 5 | 214 / 43 / `ci.yml` **仅 Ubuntu Py3.10 + `DAILY_TEST_TARGETS`**（跳过 ~3,500 用例及全部子进程 E2E） |
| 11 | **industry-research (IR)** | `.worktrees/f4-runtime@77f3c7dd5` (`origin/main`) | **漂移**：主仓停在 S2 `a055204` / 5 wt | 11 / 5,476 | 0 / 0 | 0 / 0 / 3 | 1/11 / 1 (`native_feedback.py`) / 7 / 0 | 15 / 1 / `owner-contracts.yml` **仅 Ubuntu + 7/15 文件**（私有仓远端未验） |
| 12 | **MeetingConverter (MC)** | `master@7b83fe6f7` | 对齐 / 2 wt | 26 / 4,774 | 0 / 6 | 0 / 0 / 2 | 8/26 / 1 (`local_diagnostics.py`) / 0 / 0 | 26 / 2 / `ci.yml` 全跑 `tests/` 但**测试强制限制单 Ubuntu 作业（零 Windows CI）** |

---

## 二、跨全生态五大系统性根因

### 1. 本轮新查出的线上 P0 级实时缺陷（尚潜伏在 2026-11-27 最新正式版本中）
1. **Audit 实时 `NameError` 崩溃**：`skills/revenue-forecast-audit/scripts/feedback_owner.py:187` 在 `audit-capture` 重放时调用已删除函数 `_capture_events(...)`（第 15 行已改名 `select_capture_events`），且不被 `:354` `except` 捕获，零回归测试。
2. **ET 实时 `NameError` 崩溃**：`reader.py:21` 定义 `__TEMPLATE_FILE`（双下划线），`:36` 读取 `_TEMPLATE_FILE`（单下划线），每次访问 HTTP `/` 直接崩；因 CI 零 `ruff` 且跳过 `test_reader.py` 而带病上线。
3. **IR 实时静默数据丢失 + 死参数 + 相对路径崩溃**：`tools/deepseek_client.py:603` 要求模型输出 `"evaluation_basis"`，而 `tools/report_generator.py:596` 读取 `"recommendation_basis"`，**100% 公司推荐依据被静默丢弃**；`deepseek_client.py:660` 解析的 `--model` 被完全忽略；6 处复制粘贴的 `os.makedirs(os.path.dirname(output_file))` 在传入无目录相对路径 `--output out.json` 时抛 `FileNotFoundError`。
4. **StockWiki 未转义 SQLite URI 缺陷仍在产**：`stockwiki/dashboard_onboarding.py:145` 与 `stockwiki/quick_scan_identity.py:151` 仍用 `f"file:{path.as_posix()}?mode=ro"`（含 `#`/`%`/`?` 路径静默错库）；`dashboard_onboarding.py:502` 存在恒等死三元分支；`quick_scan_store.py:404-415` 有 3 段完全相同的连续 `if`；`security_id_normalization_store.py:259-291` 仍先提交 `identity_receipts.sqlite` 再提交 `scan.sqlite`。
5. **IQS 80ms 锁重试静默丢失败态**：`scripts/iqs_scan/workbench/dashboard_jobs.py:156-168` 仅重试 `8 × 10ms = 80ms` 后静默 `break`，把失败作业永久困在 `'preparing'` 状态。
6. **CWP `DayuCliDownloadAdapter` 管道死锁 + 环境/孙进程泄漏 + 死限额**：`src/company_wiki/source_catalog/dayu_cli_adapter.py:220-260` 绕过 `bounded_process`，拷贝全量 `os.environ`（泄漏 `RESEARCH_FEEDBACK_*` 与无关密钥），用原始 `Popen(PIPE, PIPE)` 在 `poll()` 死循环中不读管道（输出 >64KiB 死锁），无 Job Object 泄漏孙进程；`source_query_cli.py:22,47` 和 `official_source_cli.py:21,39` 的 `_MAX_REQUEST_BYTES` 是未执行的死常量。
7. **FF 定时任务无超时 + 生产 CLI 执行 `tests/` 文件**：`scripts/ff_scheduled_windows.py:208-212` `subprocess.run` 缺 `timeout=`（卡死即永不退出）；`scripts/ff_t3_receipt.py:350-379` 通过 `exec_module` 直接执行 `tests/test_e2e_download.py`。
8. **SID 截断 PDF 放行 + 非原子删原件**：`src/cninfo_api.py:422-424` 在 `budget is None` 时 `response.read()` 无 `Content-Length` 校验，放行截断 PDF；`:487-489` 在 `replace()` 前先 `unlink()` 目标文件制造丢失窗口。
9. **RF 引擎代码 Bug 被吞成用户输入校验错**：`scripts/contracts/document.py:1210-1213,1258-1261,1316-1325` 宽泛 `except Exception` 零日志将 `TypeError`/`KeyError`/`AttributeError` 伪装为数据校验错误。
10. **MC 未检 `ffprobe` 退出码与超时 + 配置回退绕过校验**：`audio_utils.py:30-45` 运行 `ffprobe` 不检 `returncode` 且无 `timeout`；`transcribe.py:173-188` 回退构造 `settings` 时跳过 `validate_transcription()`。
11. **Dashboard 4 路版本分叉 + 幽灵 `correlation_id` + 静默缺失前端构建**：`main`/`origin/main`/`release-de59feed`/PWF 指向 4 个不同 SHA 且含两套不同哈希前端 bundle；`http.py:469-483` 缺失 `apps/web/dist` 时静默返回 404；`main.py:67` 在 `--data-dir` 为文件时静默写回真实用户 `Path.home()/.investment-dashboard`；`http.py:317` 写失败前就发 `X-Dashboard-Correlation-ID` 头，前端 `OriginalPreview.tsx:37-41` 和 `<Load>` (`components.tsx:26`) 从不展示 `correlationId`。

### 2. “小技巧伪解耦”典型模式清单（违背架构层面真正解耦）
本次审查在多个仓库发现“为了通过静态规则或绕开循环依赖而采用的局部技巧”，并未在架构层真正解决所有权与依赖方向：
- **技巧 1 — 私有函数直接改名公开（StockQA）**：`quick_scan_work_store.py:6901-7085` 将 17 个底层 SQL/事务私有函数直接别名挂到公共面（`api_work_store_* = _*`、`validate_schema = _validate_schema`），甚至把 `MODULE_API_PROTOCOL` 块复制了两遍；`test_quick_scan_module_boundaries.py:23-45,233` 永久豁免 21 个模块直连 SQL 与全局 `sqlite3.connect`。
- **技巧 2 — `lambda` 闭包隐藏 `.__self__`（Dashboard）**：`application/service.py:132-204` 用 **37 个单行 `lambda`** 包装 `self.<method>` 塞进 `OperationBindings`，仅抹掉了 bound method 的 `.__self__`，`fn.__closure__` 仍绑定同一个 629 行巨石 `DashboardService`。
- **技巧 3 — 继承写类 + `__getattribute__` 黑名单封写（StockQA）**：`ReadOnlyWorkView(QuickScanWorkStore)` (`quick_scan_refresh_inspect.py:234-244`) 继承 7,085 行写入类，再靠 `__getattribute__` 黑名单 + SQL 前缀字符串过滤假装只读，而非组合独立只读引擎。
- **技巧 4 — 子类化 Store 只为覆写私有 `_connect()`（StockWiki）**：`security_id_normalization_store.py:79-95` 与 `public_company_assessments.py:233-257` 定义 `_ReadStore`/`_ReadReceipts`/`_ReadOnlyObservationStore` 覆写私有 `_connect()` 在 Store 外部执行原生 SQL。
- **技巧 5 — `WeakKeyDictionary` 隐身句柄 + 9 个全局 `ContextVar`（StockQA）**：`_quick_scan_owner_refresh_port.py` 与 `quick_scan_company_runtime.py` 用全局 `WeakKeyDictionary` 藏匿真实依赖，内部仍直接操作 `owner.service.store`；`quick_scan_work_transport.py:521-562` 用 9 个模块级 `ContextVar` 暗度陈仓传权限。
- **技巧 6 — 函数体延迟导入 + 回调反转遮掩循环依赖（全生态 2,960+ 处）**：CWP 1,706 处（18 个运行时 SCC，且 `layer_boundary_scan.py:204` 的 `runtime_import_cycles()` 只测合成 `tmp_path` 从不测生产源码！）、StockQA 384 处（23 文件巨环）、IQS 280 处、StockWiki 244 处（`test_f05` 直接把 3 向循环 `refresh<->query<->delivery` 写进允许预算）、RF 148 处（`revenue_core.py` 靠回调+底部 `E402` 重导出且测试把该技巧固化）。
- **技巧 7 — `sys.modules[__name__]` 双身份垫片 + `sys.path.insert` 满天飞**：IQS **145 个**顶层 `scripts/*.py` 垫片且无 `pyproject.toml`；全生态约 **160+ 处** `sys.path.insert`（CWP 50、Dashboard 32、RF 18、Audit 16、FF 14、StockWiki 10、IQS 6、ET 5、StockQA 3、SID 1）；7/12 仓（FF、ET、SID、RF、Audit、IQS、IR）仍不是可安装的 PEP 621 标准 Python 包。
- **技巧 8 — 公开 `main()` 塞满 `_private` 测试注入参数（ET）与生产代码内嵌测试替身（RF）**：ET `scraper.py:1838`、`transcript_tool.py:193` 在公开 `main()` 上挂 5–9 个 `_retrieval_*` 私有测试参数；RF `rf_job_facade.py:114,623` 在生产文件内嵌 `SimulatedProcessDeath` 与 `FakeStageRunner`。
- **技巧 9 — 永久白名单豁免架构越界**：CWP `_COMPATIBILITY_PORTS` 从 6 条涨到 **8 条**（`test_layer_public_boundaries.py:426-443`）；StockQA `STORE_SQL_ADAPTERS` 豁免 **21 文件**；IQS `test_dashboard_module_boundaries.py` 仅扫描 6 个文件放行 `legacy_oracle.py` 跨仓导 `stockwiki`。

### 3. 日志体系“有轮转模块 ≠ 有完整可追溯日志”
S5 之后 11/12 仓新建了 1 个局部轮转文件日志模块，但距“任何入口出错皆有足够信息追溯并修复”仍有 **5 大结构性缺口**：
1. **大量生产入口仍零轮转日志**：CWP 3 个 console script 吞异常只记 `"exit:1"`；FF `JobStore.append_log` 无轮转无脱敏无锁；ET 4/6 入口脱节且 `scraper.py:249` `propagate=False` 隔绝子模块日志；SID `feedback_owner.py` 零日志且 `main.py` 启动期在挂文件日志前；RF 16+/20 CLI 零日志；Audit 11+/14 CLI 零日志；StockWiki `cli`/`ui`/`query_v2`/`feedback_owner` 零日志；StockQA 11/15 CLI 零日志且 raw `getLogger(__name__)` 撞上 `propagate=False` 进黑洞；IR 0/10 业务文件用 `logging` 且 `feedback_owner` 抹除全部错误；MC `feedback_owner` 零日志且运行日志直打 `stdout`。
2. **日志/旁路写失败静默吞错（零 `stderr` 兜底）**：CWP `runtime_feedback.py:120,341` & `runtime_trace.py:85` 显式传 `warn_on_stderr=False`；FF `ff_runtime_log.py:134` & `ff_short_feedback.py:128`；ET `runtime_logging.py:48` `warn_on_failure=False`；RF `rf_local_diagnostics.py:77,95` 锁竞争/IO 错静默丢弃；MC 旁路告警走 `basicConfig(stream=sys.stdout)` 污染 `stdout`。
3. **日志/异常信息自毁**：StockQA `logger.py:407` 2000 字符**头部截断**直接砍掉堆栈尾部异常类；CWP `triage_diagnostic.py:23-43` 与 ET `retrieval_diagnostics.py:137` 仍丢弃非白名单自定义异常类；IQS `runtime_feedback.py:142` 剥除全部异常消息；全生态 **256 处 `raise ... from None` 未先落盘日志**（CWP 83、StockWiki 82、IQS 52、StockQA 19、FF 8、IR 7、Audit 3、SID 1、RF 1）与 **146 处 `logger.error/warning` 缺 `exc_info=True`**。
4. **Windows 并发轮转竞态**：Dashboard `request_feedback.py:345` 与 IR `native_feedback.py:248` 每次事件开关 `RotatingFileHandler` 且无跨进程文件锁、无 Windows `PermissionError` rollover 保护；Audit `audit_diagnostics.py:11-16` 吞掉 rollover 失败致单文件无限增长。
5. **`stdout` 污染与前端断链**：StockQA `logger.py:588`、MC `transcribe.py:127`、IR `deepseek_client.py` 仍向 `stdout` 打日志/报错；Dashboard 前端 `OriginalPreview.tsx:37`、`<Load>`、`api.ts:80,106` 丢弃后端 `correlation_id`。

### 4. CI 假绿与 Windows 平台测试盲区（12/12 仓均有实质缺口）
- **硬编码樱桃采摘测试清单（9/12 仓）**：CWP `CI_CONTRACT_CASES` 跳过整个 `tests/e2e/` 和 2,313 行 `test_narrative_runtime_e2e.py`（仅 ruff 扫描！）；FF `CI_TESTS` 跳过 `test_e2e_isolated_wiki.py` 和 41 例离线矩阵；ET `ci.yml` 仅跑 4 文件+7 用例，**跳过全部 S1/S2/F4/batch/reader 测试**；SID `ci.yml` 仅跑 7 文件+2 用例，跳过 `cninfo_api`/`downloader`/`adapter`；RF 仍为 75 项硬编码 `CI_TESTS`；StockWiki `SHORT_TESTS` 跳过跨库提交与大部分反馈回归；IQS `quality.yml` 仅跑 7/156 文件；Dashboard `feedback-contracts.yml` 仅跑 3 后端+3 前端文件且 `pyproject.toml:27` `testpaths` 排除 `tests/adapters/` 和 `tests/test_http_failure_feedback.py`；StockQA `DAILY_TEST_TARGETS` 跳过 ~3,500/3,707 用例（含 Bearer 脱敏与全部 25 个子进程崩溃测试！）；IR 仅跑 7/15 文件；Audit **零 CI 工作流且无远端**。
- **Windows CI 极度缺位（10/12 仓零 Windows CI）**：仅 RF（4 文件）与 Dashboard（2 文件 `-k`）有 `windows-latest` 作业；CWP、FF、ET、SID、StockWiki、IQS、StockQA、IR、MC、Audit **全部无 Windows CI**（MC `test_ci_workflow_config.py:79-89` 甚至在测试里禁止加 OS 矩阵！），导致大量 `@skipif(os.name != "nt")` 的 Windows 锁/长路径/弹窗/`os.link`/原子替换回归从未在 CI 执行。
- **E2E 过度内存 Mock 与缺失关键故障场景**：多仓 E2E 通过 `monkeypatch` 替换 `urlopen`/`session.post`/`load_config`/`FakeStageRunner` 跳过真实 TCP 帧、真实配置解析和真实子进程生命周期；缺少统一的“启动失败 → 强杀恢复幂等 → 截断响应 → 双写失败降级 → 洁净安装态”七维 E2E 覆盖。

---

## 三、逐模块深度审查详录（1–12 模块，精确 `file:line`）

### 模块 1：`company-wiki`（CWP，`master@67bd4ff4d`）
1. **解耦与封装**：
   - **[P0]** `tests/support/layer_boundary_scan.py:204-213` 的 `runtime_import_cycles()` 仅在 `tests/contract/test_layer_public_boundaries.py:379-395` 测 `tmp_path`，从未对 `src/company_wiki` 执行（实测 **18 个运行时 SCC，含 5 个顶层环**，如 9 文件 `source_catalog` 核心环、9 文件 `narrative_*` 环、8 文件 `du.profiles` 环、7 文件 `du.structure` 环、5 文件 `du.operating_states` 环）。
   - **[P0]** `src/company_wiki/source_catalog/dayu_cli_adapter.py:220-260` 绕过 `bounded_process`：拷贝全量 `os.environ`（泄漏 `RESEARCH_FEEDBACK_*` 与密钥；同见 `adapter_process.py:385`），原始 `Popen(PIPE, PIPE)` + `while poll() is None` 不排空管道（>64KiB 死锁），无 Job Object（泄漏孙进程）。
   - **[P1]** `tests/contract/test_layer_public_boundaries.py:426-443` 保留 **8 条永久逆层豁免 `_COMPATIBILITY_PORTS`**；`source_catalog/` 仍为 **267 文件扁平巨包**（仅 13 个 `PUBLIC_PORTS`），存在 2,812 行 `narrative_evidence.py`、2,573 行 `resolver.py`、2,332 行 `narrative_contracts.py`、2,240 行 `automation/narrative_batch.py` 等巨石与 **1,706 处延迟导入**。
   - **[P1]** `source_catalog/store.py:624-631` (`read_pipeline_status`) 绕过 `ReadOnlyCatalogReader` 直连 `sqlite3.connect` 且缺 `configure_tolerant_sqlite_text_decoding`；`tools/run_source_system_tests.py:23-24`、`tools/pre_push_gate.py:47-49` 直接导入私有 `_bounded_process`；`source_catalog/cli.py:544-550` 改写 `subparsers._choices_actions`；`automation/store.py:1303,1321` 嵌入 `if job.job_type == "source.narrative_*"` 反向业务耦合；`scripts/` 仍混存 100+ 历史遗留脚本（如 1,330 行 `scripts/llm_client.py` 与硬编码个人路径 `scripts/run_downloader.py:205`）。
2. **代码质量与硬编码**：
   - **[P0]** `source_query_cli.py:22,47` 与 `official_source_cli.py:21,39` 的 `_MAX_REQUEST_BYTES` 未生效（无界 `stdin.read()`），另有 6 个 CLI 同为无界读取。
   - **[P1]** `config/source_acquisition.yaml:12,22,25,41,44` 硬编码 Windows `.venv/Scripts/python.exe` 与邻仓路径；`acquisition_config.py:75,80-92` 硬编码三市场；`pyproject.toml:110` `mypy` 设 `follow_imports = "skip"`；`narrative_business_meaning.py:19-117,255-267` 内嵌双语领域词表正则；`adapter_process.py:430` 按字符串比对异常类名；10+ CLI 复制粘贴 `_JsonArgumentParser`/`_write_json_line` 模板代码；`runtime_config.py:464` 硬编码 `"~/company-wiki"`。
3. **日志体系与历史错误固化**：
   - **[P0]** `runtime_feedback.py:120,341` 与 `runtime_trace.py:85` 显式传 `warn_on_stderr=False`，`diagnostic_logging.py:35-40` `doRollover` `except OSError: pass`，日志写盘失败静默归零。
   - **[P1]** 3 个 console script（`source_contract/cli.py:143`、`identity_cli.py:71`、`transcript_import_cli.py:238`）捕获异常返回 exit 1/2 但不调 `record(..., error=exc)`，丢弃堆栈；`scheduled_reading.py:10` 缺 `@runtime_feedback.entry`；`triage_diagnostic.py:23-43` 将非白名单自定义异常全部压扁为 `"OwnerException"`；83 处 `from None` 无前置日志（含 `_bounded_process.py:112`、`source_stream_cli.py:188`、`automation/store.py:998`）；`dayu_cli_adapter.py:263,273` 嵌入未脱敏 `cli_stderr[-3000:]`。
   - **历史缺陷 CI 锁定缺口**：Windows `conhost.exe`、`os.link` WinError 5、`triage_diagnostic` 非内建异常、`test_narrative_runtime_e2e.py` AUTO 崩溃恢复、日志写失败告警 均未在 `ci.yml` 中真正执行。
4. **E2E 测试与 CI**：
   - **[P0]** `.github/workflows/ci.yml:33,67,82` 仅 `ubuntu-latest`，跳过全部 `tests/e2e/`（仅 ruff 扫描）、跳过 `tests/integration/test_narrative_runtime_e2e.py`（2,313 行仅 ruff 扫描）、跳过 ~250/285 契约文件；`source-system.yml:5-15` 不因 `src/**` 变更触发。

### 模块 2：`filing-fetch`（FF，`main@4dd4e13ec`）
1. **解耦与封装**：
   - **[P0]** `pyproject.toml:1-22` 缺 `[build-system]`/`[project]`/`[project.scripts]`/`requires-python >=3.11`（14 处 `sys.path.insert`）；`scripts/ff_t3_receipt.py:350-379` 通过 `exec_module` 直接执行 `tests/test_e2e_download.py`。
   - **[P1]** `scripts/fetch_filing.py` 2,095 行巨石（`resolve_filing` 257 行、`main` 240 行）；100 处延迟导入；`ff_short_feedback.py:139-140` 运行期修改全局 `os.environ.pop`；`ff_provider_cause.py:91-178` 手工复制 CWP 错误码字典；`ff_company_wiki_connection.py:89-93` 注入邻仓 `PYTHONPATH`；`tests/test_e2e_isolated_wiki.py:32,46` 直导 CWP 私有 `CatalogOperationLock`，`isolated_wiki.py:247` 复制生产 YAML。
2. **代码质量与硬编码**：
   - **[P1]** `scripts/ff_scheduled_windows.py:208-212` `subprocess.run` **缺 `timeout=`**；`ff_scheduled_refresh.py:84`/`ff_job.py:60`/`ff_configuration.py:30` 无界读取 stdin/文件；`fetch_statements.py:122`/`ff_job_runner.py:195`/`fetch_filing.py:2067` 输出未脱敏 `str(exc)`；`fetch_filing.py:1415,1875` 保留 3 个死 `pause_worker` 参数；`quality.yml:26` `mypy` 仅查 2 个文件；`isolated_wiki.py:223` 清理吞 `PermissionError`。
3. **日志体系与历史错误固化**：
   - **[P0]** `scripts/ff_job_store.py:348-355` 作业日志无轮转、无脱敏、无锁；`ff_runtime_log.py:90-96,134-142`、`ff_runtime_feedback.py:46,150`、`ff_short_feedback.py:128` 写失败静默吞错零 stderr 告警。
   - **[P1]** `ff_process_transport.py:145,153` `from None` 前无日志（丢 `winerror`）；`fetch_filing.py:432,1814` 与 `transcript_companion.py:143,165` 缺结构化堆栈日志。
   - **历史缺陷 CI 锁定缺口**：双 `DEVNULL` 修复测试 `test_s1_windows_tick_logging.py:48,122,138` 因 `@skipif(nt)` 在 Ubuntu-only CI 全部跳过；T3 限额未入离线 CI。
4. **E2E 测试与 CI**：
   - **[P0]** `quality.yml:9,53` 仅 Ubuntu 且硬编码 55 文件 `CI_TESTS`，排除 `test_e2e_isolated_wiki.py`、`test_du11_transcript_reuse_e2e.py`、41 例离线矩阵和 `host_assumption_guard.py`；且 `test_e2e_isolated_wiki.py` 与 `test_e2e_download.py` **100% 仅测旧 schema 1.1，零 schema 2.0 覆盖**！

### 模块 3：`earnings-transcripts`（ET，`main@672ed1012`）
1. **解耦与封装**：
   - **[P0]** 无 `pyproject.toml`（5 处 `sys.path.insert`）；`tools/run_request_budget_e2e.py:25-26,105-118` 生产工具导入 `tests.*` 并 monkey-patch 标准流；**实时线上 `NameError`**：`reader.py:21` `__TEMPLATE_FILE` vs `:36` `_TEMPLATE_FILE`。
   - **[P1]** 3 个巨石：`transcript_feedback.py`（2,118L，含全局 `_ACTIVE_RECORDER:1613`）、`scraper.py`（1,949L）、`transcript_api.py`（1,425L）；公开 `main()`（`scraper.py:1838`、`transcript_tool.py:193`）暴露 5–9 个 `_private` 测试注入参数；`retrieval_worker.py:57-72` 允许从请求 JSON 任意 `importlib.import_module`；`retrieval_runtime.py:317-323,386-409` 无 `CREATE_NO_WINDOW` 且无 Job Object 泄漏孙进程；`scraper.py:749-757` 无 `fsync` 且存在 `exists()` TOCTOU；`translate.py:72` 裸锁依赖 `atexit`。
2. **代码质量与硬编码**：
   - **[P1]** `config.yaml:49-51` 过时 FMP `/api/v3/` 与 `transcript_api.py:326` 硬编码 `/stable/` 矛盾；`config.yaml:107,140-152` 硬编码微软产品词（`Copilot`/`Azure`/`GitHub`/`LinkedIn`）；`translator.py:99-128,148,192` 硬编码 URL/模型、静默回退 Google、用 MD5 做缓存键；`config.py:17` 无配置校验；仓库零 `ruff`/`mypy`。
3. **日志体系与历史错误固化**：
   - **[P0]** `scraper.py:249` `log.propagate = False` 导致 `retrieval_runtime`/`transcript_api`/`translator` 永远不写入 `logs/scraper.log`；`translate.py:68` 未传 `log_file` 零文件日志；`reader.py:114` 空 `log_message`；`runtime_logging.py:48-65` `warn_on_failure=False` 写盘失败零 stderr 告警；`translator.py:236` 与 `translate.py:51` 记录未脱敏异常且缺 `exc_info=True`。
   - **[P1]** `retrieval_diagnostics.py:137-140` `WorkerStderr._drain` 仍用 `_BUILTIN_ERRORS.get` 丢弃自定义/库异常类；`:104-105` 丢弃被抑制的 `__context__`。
   - **历史缺陷 CI 锁定缺口**：启动失败零请求、崩溃 stderr 保留、`-`/`<frozen>` 帧正则、并发半份快照、manifest 失败退出码、Windows 弹窗/孙进程、`reader.py` 崩溃 **全部未在 `ci.yml` 执行**！
4. **E2E 测试与 CI**：
   - **[P0]** `.github/workflows/ci.yml:10,27-36` 仅 Ubuntu Py3.10、无 ruff/mypy、仅跑 **4 文件 + 7 单测**，跳过 `test_s1_*`/`test_s2_*`/`test_f4_ordinary_failures.py`(1,468L)/`test_batch_runtime.py`(1,266L)/`test_runtime_contract_isolation.py`/`test_reader.py`；且现有 batch E2E 靠 `_retrieval_launcher` 内存伪造响应，未走真实本地 HTTP/TCP。

### 模块 4：`StockInfoDLSimple`（SID，`v2-clean-rewrite@5c6560502`）
1. **解耦与封装**：
   - **[P1]** 无 `pyproject.toml`（`main.py:31` `sys.path.insert`，`runtime_steps.py:49` 硬读 `main.py`）；`company_wiki_adapter.py:296-303` 与 `adapter_cli.py:131` 残留旧 `StockDownloader` 耦合与死 SPA 辅助函数；`orgid.py` (`requests`+Playwright) 与 `cninfo_api.py` (`urllib`) 两套 HTTP 栈并存；`feedback_publish.py`（964L）、`cninfo_api.py`（921L）、`downloader.py`（805L）、`adapter_cli.py:_main`（327L）过载；3 处差异语义的异常链提取器；`tests/e2e/official_e2e_test.py:69` 残留无效 V1 导入 `src.data.mapping`。
2. **代码质量与硬编码**：
   - **[P0]** `src/cninfo_api.py:422-424` 无预算 `fetch_pdf` 缺 `Content-Length` 截断校验；`:487-489` 先 `unlink` 再 `replace` 非原子；`feedback_files.py:40` 缺 Windows `WinError 5/32` 重试，`storage.py:38`/`progress.py:53` 非原子无锁写。
   - **[P1]** 6 文件分散硬编码 CNINFO URL/域名；`adapter_cli.py:103` 硬编码 `max_pages=5` 忽略配置；`cninfo_report_metadata.py:20-47` `20\d{2}` 漏 1990s 年报且非 Q1 默认 Q3；`config.py:18-45` 缺显式 `--config` 时静默回退默认且 5 个配置键为死配置。
3. **日志体系与历史错误固化**：
   - **[P0]** `src/feedback_owner.py:437-462` 零轮转日志且吞 6 类异常为静态 `"sid_feedback_action_rejected"`；`main.py:479-497` 挂文件日志晚于 `parse_args`/`load_config`（启动期崩溃无文件日志）；`feedback_publish.py:915` CLI 零文件日志；27 处 `log.error/warning` 缺 `exc_info=True`；11+ 处静默 `except Exception`（`browser.py` 8 处、`orgid.py`、`cninfo_api.py`、`feedback_owner.py`）。
   - **历史缺陷 CI 锁定缺口**：`.github/workflows/ci.yml:11,26-36` 跳过 `test_cninfo_api.py`（`secCode`/UTC+8/429）、`test_downloader.py`（部分下载报完成）、`test_company_wiki_adapter.py`、9/10 `test_provider_error_contract.py`、15/16 `test_f4_start_input.py` 及全部 Windows 路径/锁测试。
4. **E2E 测试与 CI**：
   - **[P0]** 仅 Ubuntu + 硬编码 7 文件+2 用例；adapter CLI 测试多为进程内 `monkeypatch`；`official_e2e_test.py` 依赖外网且含坏 V1 导入。

### 模块 5：`revenue-forecast`（RF，`origin/main@782cfd9a`，主仓 `d62fca9a` 分叉）
1. **解耦与封装**：
   - **[P0]** `scripts/rf_job_facade.py`（1,512L）将 `Deployment`/`JobStore`/`SubprocessStageRunner`/`JobFacade` 全合一，更把测试替身 `SimulatedProcessDeath:114` 与 `FakeStageRunner:623-679` 嵌在生产源码！
   - **[P0]** `report_catalog*` 仍存在跨文件私有访问（`catalog._read_json`/`_index`/`_read_artifact`/`_validate_*`/`_entries`/`_source_refs`、`store._creation_lock`/`_require_job_id`、22 私有导入、19 私有属性）与延迟导入环；`rf_job_facade.py:57 <-> rf_job_feedback.py:148` 运行时环；`revenue_core.py` 依赖底部 `E402` 重导出与回调技巧（被 `test_module_boundary_closure.py:89` 固化）；无 `pyproject.toml`（18 处 `sys.path.insert`）；`revenue_report.py` 2,137L（`_validate_forecast_output` **995 行**！）、`targets.py:118` 681 行。
2. **代码质量与硬编码**：
   - **[P0]** `tools/pre_push_gate.py:78-153` 仍为硬编码 75 项 `CI_TESTS` 元组，`mypy` 仅扫 5 文件（`:186-188`）。
   - **[P1]** `tools/slo_probe.py:25-38,110` 硬编码 `"紫金矿业"` 2025 且 `:110` 伪造 `bundle = exact[:]`；`cwp_catalog_status.py:51-54` 脆弱英文前缀匹配；`report_catalog.py:953-1109` 与 `research_publication.py:433` 硬编码一次性 W09 / Q3-2026 历史路径；4 份重复 `assert_pathless`、6 份重复严格 JSON 解码、3 份重复原子写；`release_readiness.py:87` `stderr=DEVNULL`；本地主仓 `main@d62fca9a` 与 `origin/main@782cfd9a` 严重分叉且堆积 26 个 worktree。
3. **日志体系与历史错误固化**：
   - **[P0]** `scripts/contracts/document.py:1210,1258,1316-1325` 宽泛 `except Exception` 零日志将引擎代码 Bug 吞成用户输入校验错。
   - **[P0]** 仅 4/20+ CLI 挂 `@observed_entry`（16+ CLI 零轮转日志）；`rf_local_diagnostics.py:72-96` 锁忙（`:77`）或 IO 错（`:95`）静默丢日志且无 stderr 告警、无脱敏、缺 `attempt_id`/`code_version`/`input_ref`；`rf_feedback_outbox.py:109-124` 双写失败无 stderr 兜底；`company_wiki_source_reader_v2.py:201` `from None` 无前置日志；`filing_fetch_client.py:277-298` 三表分支丢 stderr；`compare_cli`/`rf_job_cli`/`rf_job_feedback` 吞异常无本地堆栈。
   - **历史缺陷 CI 锁定缺口**：`origin/main` 的 `windows-lifecycle` 已覆盖 4 个生命周期文件，但 `test_zr902_daily_schedule.py`（SYSTEM 任务）仅跑 Linux，`CI_TESTS` 硬编码风险与 `contracts/document.py` 吞引擎错均未锁定。
4. **E2E 测试与 CI**：
   - **[P1]** `FakeStageRunner` 使大量作业测试绕过真实子进程；缺真实双失败（SQLite + 日志不可写）及 `contracts/document.py` 内部异常穿透 E2E；`conftest.py` 需默认全局隔离 `LOCALAPPDATA`/`RESEARCH_FEEDBACK_*`。

### 模块 6：`revenue-forecast-audit`（Audit，`main@9e9e98096`，无远端）
1. **解耦与封装**：
   - **[P0] 实时 `NameError`**：`skills/revenue-forecast-audit/scripts/feedback_owner.py:187` 调用已删函数 `_capture_events(...)`（应为 `select_capture_events`）。
   - **[P1]** 无 `pyproject.toml`（16 处 `sys.path.insert` + 测试遍地 `spec_from_file_location`，逼迫 `financial_measure_evidence.py:542` 写 `hasattr` 鸭子类型）；`tools/adoption_replay_support/` 存在 6 文件顶层环；5 个 >1,000 行巨石（`audit_run.py` 1,361L、`pool_progress.py` 1,339L、`coverage_observations.py` 1,136L、`financial_measure_evidence.py` 1,112L、`summary_review_packet.py` 1,059L）。
2. **代码质量与硬编码**：
   - **[P1]** `tools/sync_skill.py:12-13,66-94` 仅硬编码 `.claude`/`.agents`（遗漏 `.gemini/config`/`.codex`）且从不检测目标目录残留孤儿脚本；4 处原子写（`audit_run:77`、`audit_delivery:74`、`pool_progress:1109`、`sync_skill:62`）全缺 Windows `os.replace` 重试；`20\d{2}` 正则漏 1990s、`USD/HKD/CNY` 漏欧日元、`coverage_observations.py:58` 硬编码 W08 专用 schema 名；`require`/`SCALES` 等工具在 8+ 脚本复制粘贴。
3. **日志体系与历史错误固化**：
   - **[P0]** 11+/14 CLI（`audit_contracts.cli_main` 所辖 7 个 CLI、`financial_measure_*`、`numeric_audit`、`rf_workflow_index`、`sync_skill`）**零轮转日志**；`audit_run.py:1317` 仅捕 4 类异常导致 `RuntimeError`/`sqlite3.Error`/`AttributeError` 漏记 `runtime.log`；`feedback_owner.py:354` 把 `{"error": ...}` 打到 `stdout` 且剥除消息；`audit_diagnostics.py:11-16` 吞 rollover 错且自身不脱敏；`run_pool_progress_e2e.py:218` 双 `DEVNULL`。
   - **历史缺陷 CI 锁定缺口**：本地虽有 830 个单测，但**零 CI 工作流、无远端、无预推钩子**，且零测试覆盖 `feedback_owner.py replay` `audit-capture`（放行了实时 P0 `NameError`！）。
4. **E2E 测试与 CI**：
   - **[P0]** 全仓无自动化 CI；`run_pool_progress_e2e.py` 脱离 `unittest discover` 且用双 `DEVNULL`；缺少串联 `init → execution_request → audit_run capture → document_status_join → review_protocol → financial_measure_evidence → feedback_owner reconcile/replay` 的全链子进程 E2E。

### 模块 7：`StockWiki`（`master@0fbaf7ce3`，无远端）
1. **解耦与封装**：
   - **[P0]** 严重绕过 Store 封装（全仓 **66 处 `sqlite3.connect`**、**290 处私有导入**、**34 处外部私有属性**）：`quick_scan_query.py:110` 以读写模式直连 SQLite；`quick_scan_identity.py:151` 裸写 3 表 JOIN；`security_id_normalization_store.py:79-95` 与 `public_company_assessments.py:233-257` 子类化 Store 只为覆写私有 `_connect()` 执行外部 SQL；`quick_scan_store.py:402` `_save_prepared()` 违反“调用方持事务”文档自行 `commit()`。
   - **[P1]** 3 个运行时 SCC（`identity_*`/`quick_scan_analysis`、`dashboard_research_binding_*`、`news`/`news_fetch`）；`tests/test_f05_module_api_boundaries.py:115-138` 允许 3 向循环且仅扫描 `quick_scan_*.py`（盲区含 2,565 行 `public_company_assessments.py`、`ui.py`、`dashboard_onboarding.py`）；`ui.py:47` 跨模块导 4 个私有函数；根 CLI 存在 10 处 `sys.path.insert`。
2. **代码质量与硬编码**：
   - **[P0]** 未转义 SQLite URI 缺陷仍在产：`dashboard_onboarding.py:145`、`quick_scan_identity.py:151`（`#`/`%`/`?` 静默错库）；`security_id_normalization_store.py:71`、`quick_scan_observations.py:212` 缺 `.resolve()`。
   - **[P1]** `stockwiki/paths.py:11` 硬编码个人路径 `C:\Users\郑曾波\Projects`；`dashboard_onboarding.py:502` 死三元分支；`quick_scan_store.py:404-415` 连续 3 块重复 `if`；`ui.py:55,255` 硬编码端口 `8765` 与无界 POST 读取（OOM 风险）；`check_c06_interop.py:15` 硬编码旧 IQS SHA；`scripts/checks.py:48-76` 硬编码 `SHORT_TESTS`；堆积 31 个 worktree。
3. **日志体系与历史错误固化**：
   - **[P0]** `cli.py`/`ui.py`/`quick_scan_dashboard_cli.py`/`quick_scan_query_v2_cli.py`/`feedback_owner.py` 全缺轮转日志；`ui.py:168,249,251` 静音访问日志且未捕获异常返 HTTP 400 泄漏裸 `str(exc)`；**82 处 `from None` 无前置日志**（仅 `public_company_assessments.py` 就占 **26 处** + 6 处静默吞错）；`documents.py:391` 静默返 `None`；`llm_usage_ledger.py:137,155` 缺 `exc_info` 且静默跳坏行；`runtime_feedback.py` `unavailable_detail()` 漏接 2 个 CLI；`feedback_owner.py:29-33` 缺 `CREATE_NO_WINDOW`。
   - **历史缺陷 CI 锁定缺口**：跨库非原子提交（仍在产！）、`#`/`%` SQLite 路径（仍在产！）、Windows 轮转日志并发丢行、Git 弹窗、复本重投归档破坏、死三元分支 **全部未在有效 CI 中执行**（无远端 + `ci.yml` 仅 Ubuntu `SHORT_TESTS`）。
4. **E2E 测试与 CI**：
   - **[P0]** 无远端仓库；`ci.yml:16,33` 仅 Ubuntu + `SHORT_TESTS`，跳过 7/10 `test_runtime_feedback.py`、几乎全部 `b34_id_normalization/` 与全部 `tests/e2e/*`。

### 模块 8：`invest-quick-scan`（IQS，`origin/master@3094c5f7`，主仓停在 `50fe2b1`）
1. **解耦与封装**：
   - **[P0]** 无 `pyproject.toml`；**145 个顶层 `scripts/*.py` `sys.modules[__name__]` 双身份垫片** + 6 处 `sys.path.insert`；`iqs_temporal_vendor/legacy_oracle.py:2-8` **仍在直接跨仓导入 `stockwiki.quick_scan_freshness`**（因 `test_dashboard_module_boundaries.py:202` 仅扫 6 文件而漏检）；`tests/test_company_scan_native_e2e.py:48-72` 注入 StockQA 路径并导入其内部模块与私有 `tests.*` 夹具。
   - **[P1]** 5 个 >950 行 workbench 巨石（`dashboard_execution.py` 1,382L、`dashboard_prepare.py` 1,241L、`dashboard_job_facade.py` 1,206L、`dashboard_service.py` 1,199L、`dashboard_batches.py` 975L）；280 处延迟导入；`dashboard_service.py:819-821` 用浅拷贝 `copy.copy(self)` 共享可变子服务。
2. **代码质量与硬编码**：
   - **[P0]** `dashboard_jobs.py:156-168` **80ms 魔数锁重试（`8 × 10ms`）后静默 `break`**，把失败作业永久困在 `'preparing'`！
   - **[P1]** `scripts/iqs_scan/tools/status_report.py:83-85` 硬编码个人路径 `C:/Users/郑曾波/Projects/iqs-...`；`dashboard_service.py:109` & `open_dashboard.py:138-141` 硬编码邻仓路径与冲突默认端口（`8765` vs 生产 `8766`）；`dashboard_prepare.py:31` 硬编码 `DEFAULT_PACKAGE`；`thin_scan.py:35-54,79` 硬编码日期 `"2026-10-18"` 与 50 处硬编码模型/28 处硬编码 URL；`provider_transport.py:48` 无界 `response.read()`；主仓停滞于特性分支且堆积 18 个 worktree。
3. **日志体系与历史错误固化**：
   - **[P1]** `runtime_log.py` 具备带锁轮转基础，但全仓仅 1/321 文件用 `logging`、78/79 `__main__` 缺日志接入；`runtime_feedback.py:142-168` 剥除全部异常消息导致 HTTP 500 难辨原因；`open_dashboard.py:51,168,194` 静音访问日志、缺 `CREATE_NO_WINDOW`、启动失败零堆栈；**52 处 `from None` 无前置日志**；`dashboard_http.py:146` 传 `error=None` 丢解析异常。
   - **历史缺陷 CI 锁定缺口**：80ms 锁丢失败态仍在产；`IncompleteRead` 与同阶段多题去重缺专项回归测试；`open_dashboard.py:168`/`run_tests.py:134` 仍缺 `CREATE_NO_WINDOW`；全部 Windows 场景无 CI。
4. **E2E 测试与 CI**：
   - **[P0]** `.github/workflows/quality.yml` 仅 Ubuntu 且只跑 **7 文件 + 1 单测**（跳过 148+/156 文件，含 `test_producer_pipeline_e2e.py`、`test_dashboard_http.py`、`test_thin_scan_search.py`）；`suites.json` 仅 1 个离线 E2E 且高度 mock，5 个 native E2E 需 4 个外部仓环境变量才运行。

### 模块 9：`investment-dashboard`（Dashboard，`release-de59feed@de59feed`，4 路分叉）
1. **解耦与封装**：
   - **[P1]** `backend/dashboard/application/service.py:132-204` 用 **37 个单行 `lambda` 闭包**包装 `self.<method>` 塞入 `OperationBindings`——仅隐藏 `.__self__` 的包装技巧，`DashboardService` 仍为 629 行中心巨石。
   - **[P1]** `adapters/identity.py:155` 直接调 `self._fallback._read(...)`；`adapters/research.py:72-75` 延迟构造 `StockWikiIdentityAdapter` 绕过 DI 且丢失 fallback 工作区；`adapters/iqs/{identity,quickscan,universe}.py` 跨文件导 `._shared._*`（全仓 35 私有导入、21 文件 adapters 环）；`adapters/iqs/quickscan.py` 1,082 行巨石；`scripts/f2_dash_feedback_sample.py:28-42` 导入 `tests` 私有 `_owner_stub`；`scripts/feedback_owner.py:158,219` 绕过存储层直连 SQLite；前端 `Documents.tsx:4,41` 跨 feature 直导 `../research/citation-binding`；`handoffs/` 目录残留 9 处跨仓内部导入脚本。
2. **代码质量与硬编码**：
   - **[P0]** **4 路版本分叉**（`main@fd4d62d` / `origin@41ddcf6` / `release-de59feed@de59fee` / PWF `fcd464e`，前端编译产物哈希不一致）+ 34 个 worktree；`transport/http.py:469-483` 缺失 `apps/web/dist` 时静默降级为全站 404；`main.py:52-55` 吞 `adapters.factory` `ImportError` 返空端口；`main.py:67` `--data-dir` 为文件时静默写回真实用户 `Path.home()/.investment-dashboard`！
   - **[P1]** 多文件硬编码超时/限额/端口及前端中文报错文案；`m7_screens.py:30` 脆弱 `parents[4]` 路径；`playwright` 未声明进 `pyproject.toml`；前端 `Overview.tsx:140` 漏传 `openDestination` 丢返回上下文、`ScreenBuilder.tsx:58` 误比对快照 ID。
3. **日志体系与历史错误固化**：
   - **[P0]** `request_feedback.py:345-368` (`_RuntimeLog`) 每请求开关 `RotatingFileHandler` ~5 次，仅靠进程内 `threading.Lock`，**无跨进程文件锁、无 Windows `PermissionError` rollover 保护**；`main.py`/uvicorn/`cwp_stream`/`quickscan` 无轮转文件日志。
   - **[P0]** **幽灵 `correlation_id` + 前端丢弃**：`http.py:317` 在旁路写前即输出 `X-Dashboard-Correlation-ID` 头、`main.py:89` 写失败仍印 `correlation_id`；前端 `OriginalPreview.tsx:37-41` (`previewFailure`)、`<Load>` (`components.tsx:26`)、`api.ts:80,106-108`、`capabilities.ts:46` 丢弃或不展示 `correlationId`！
   - **[P1]** `adapters/common.py:23-24` `fail()` 无 `cause` 参数全适配器丢异常链；`cwp_stream.py:115-136` 未调 `child_result()` 丢流式子进程退出码/stderr + 7 处静默吞错；`service.py:353,529,537` 吞 `OwnerPortError`；`http.py:346` `from None` 丢 ASGI 堆栈；`feedback_owner.py:283` 吞错返 exit 0 零日志。
4. **E2E 测试与 CI**：
   - **[P0]** `pyproject.toml:27` `testpaths = ["tests/unit", "tests/integration"]` 静默排除 `tests/test_http_failure_feedback.py`、全部 `tests/adapters/` 与全部 `tests/e2e/`；`feedback-contracts.yml` 仅跑 3 后端 + 3 前端文件（跳过 `typecheck`/`npm run build`/Playwright/全部单元测试）；10 个 `tests/e2e/m*/` 重复造服务启动器且仅跑 `synthetic` 模式；私有仓 CI 结果未获外部核验。

### 模块 10：`StockQAbyLLM`（StockQA，`origin/master@86f633d8`，主仓停在 `a3c2c72`）
1. **解耦与封装**：
   - **[P0]** **全生态头号巨石与巨环**：`src/utils/quick_scan_work_store.py` **7,085 行（104 个公开方法、27 版混合迁移）**、`llm_runner.py` **3,687 行**（`_run_single_company` **883 行**！）、**23 文件 `quick_scan_*` 运行时巨环** + **384 处延迟导入**。
   - **[P0]** **教科书级伪解耦技巧**：`quick_scan_work_store.py:6901-7085` 将 17 个底层 SQL/事务私有函数改名别名成公共 API（`api_work_store_* = _*`）并重复声明 `MODULE_API_PROTOCOL` 两遍（`llm_client.py:1926-1955` 同病）；`test_quick_scan_module_boundaries.py:23-45,233` 豁免 **21 个模块**直连 SQL 与全局 `sqlite3.connect`；`ReadOnlyWorkView(QuickScanWorkStore)` 继承写类靠 `__getattribute__` 黑名单封写；`WeakKeyDictionary` 隐身句柄 + 9 个全局 `ContextVar` + `copy.copy(self)` 改私有字段；`main_with_llm.py:17` & `quick_scan_shared_company.py:136` 注入 `sys.path`。
2. **代码质量与硬编码**：
   - **[P1]** 30 处硬编码模型/15 处硬编码 URL（`llm_client.py:115-212,1301-1433`、`quick_scan_search_policy.py:49-52`）；`max_output_tokens=8192` 在 5 处重复；6 处硬编码 CWD 相对状态文件名；硬编码超时/租约/截断帽；`async_llm_provider.py:79,102` 过时 `asyncio.get_event_loop()` 与裸 `raise Exception`；`qa_engine.py:1034` 非原子写最终结果；`config_manager.py:71-87` 丢 `from e`；`quick_scan_owner_research.py:91-92` 连续重复条件；`pyproject.toml:15` 占位符作者。
3. **日志体系与历史错误固化**：
   - **[P0]** 11/15 CLI 零轮转日志；`logger.py:588` 默认向 **`sys.stdout`** 打控制台日志（逼迫 6 个 JSON CLI 套 `redirect_stdout(sys.stderr)`）；`quick_scan_owner_research.py:28,475` 与 `work_decision_authority.py:28,165` 用原始 `logging.getLogger(__name__)`，撞上 `propagate=False`（`logger.py:561`）进黑洞；`logger.py:372,407` **2000 字符头部截断**直接砍断堆栈尾部异常类且漏脱敏 URL userinfo/`ghp_`/`AIza`。
   - **[P1]** `llm_runner.py:1686-1689` **仍静默吞坏 checkpoint 为 `None`**；`llm_client.py:1640,1876` 19 处 `from None` 无前置日志；3 个子进程调用点（`owner_refresh:200`/`refresh_consent:148`/`subject_owner:64`）丢弃已捕获 `stderr`；60 处 `logger.error/warning` 缺 `exc_info=True`；`llm_runner.py:2676` 漏传 `run_id`/`attempt_id`；`async_llm_provider.py:508` 吞异常返 `[]`。
   - **历史缺陷 CI 锁定缺口**：Bearer 脱敏测试（`test_q05_content_boundary.py`）、9/10 `test_execution_failure_diagnostics.py`、坏 checkpoint 吞错、3 处子进程 stderr 丢弃、全部 Windows `msvcrt`/junction 测试 **均未在默认 CI 执行**；`test_owner_refresh_charge_boundaries.py:81,162` 仍残留旧 `_environment={}` 假替身。
4. **E2E 测试与 CI**：
   - **[P0]** `ci.yml` 仅 Ubuntu Py3.10 跑 `DAILY_TEST_TARGETS`（跳过 ~3,500/3,707 用例，含全部 25 个 `test_external_context_cli_e2e.py` 子进程崩溃/强杀恢复测试与 `test_live_wal_refresh_readers.py`）；`test_quick_scan_cli.py:379` 进程内 `Mock()` 替换 `http_client_manager` 跳过真实 TCP/HTTP 帧。

### 模块 11：`industry-research`（IR，`origin/main@77f3c7dd5`，主仓停在 `a055204`）
1. **解耦与封装**：
   - **[P0]** 无 `pyproject.toml`/`requirements.txt`（7 文件重复 `try/except ImportError` 双路径黑客）；**实时静默丢数据 Bug**：`deepseek_client.py:603` 输出 `"evaluation_basis"` vs `report_generator.py:596` 读取 `"recommendation_basis"`！
   - **[P1]** `tools/quick_scan_client.py` 2,240 行（占全仓 41%），且纯离线子命令（`summarize`/`render-section`/`audit-section`）仍强依赖 `--config` + `owner_root`（`:2123,2166`）；`install_reporting_tools.py:8-19` 硬编码安装列表遗漏 `feedback_owner.py`/`config.yaml`/`checklist.md`/`modules/`/`templates/`；`report_generator.py:115-152` 手写脆弱 YAML 解析器并复制 53 个行业硬编码表（`:685-696`）。
2. **代码质量与硬编码**：
   - **[P0]** `config.yaml:8,18-26`、`modules/deepseek-api.md:37,108-109`、`modules/report-generation.md:10,327` 硬编码个人路径 `C:/Users/郑曾波/...`！
   - **[P1]** `deepseek_client.py:73-74,122-147` 硬编码 URL/模型/重试睡眠/截断帽且不读 `config.yaml` 或 env；`--model`（`:660`）为 100% 死参数；6 处复制粘贴非原子写且 `--output out.json` 无目录崩溃；`report_generator.py` 多处静默截断证据列表（违背 R7）+ 死变量 `categories:401`。
3. **日志体系与历史错误固化**：
   - **[P0]** 0/10 业务文件用 `logging`；`native_feedback.py:248-266` 每事件开关 `RotatingFileHandler` **无跨进程文件锁**（Windows 轮转竞态）且忽略重定向路径；`feedback_owner.py:313-315` 零日志抹除 6 类异常为静态串 + 4 处静默吞错；`deepseek_client.py` 20+ 处 `print` 把全部报错打到 `stdout`；7 处 `from None` 无前置日志、7 处丢 `from exc`。
   - **历史缺陷 CI 锁定缺口**：技能安装器同步一致性（`install_reporting_tools.py`）零自动化测试；`owner-contracts.yml` 仅跑 7/15 文件且仅 Ubuntu（私有仓未验）。
4. **E2E 测试与 CI**：
   - **[P1]** `test_deepseek_boundary.py:38-91` 因 `deepseek_client` 硬编码 URL 需 54 行 `runpy`+`socket` 劫持；缺少其余 5 个 DeepSeek 模式、`deepseek_client → report_generator` 端到端契约、强杀恢复、洁净技能安装及 Windows 轮转并发 E2E。

### 模块 12：`MeetingConverter`（MC，`master@7b83fe6f7`）
1. **解耦与封装**：
   - **[P1]** `core/feedback.py` 1,487 行（占全仓 31%）混合 5 项职责并持全局可变注册表 `_RECORDERS`/`_LAST_RECORDER`/`_PROCESS_RUN_ID`；3 份重复异常链提取器（`engines/fallback.py:20`、`core/feedback.py:286`、`engines/mimo.py:53`）；`pyproject.toml:3,12-18` 用已弃用后端 `setuptools.backends._legacy:_Backend`、把 `pytest` 放进运行期 `dependencies`、缺 `[project.scripts]`；顶层平铺脚本 + `company_manager.py` 非原子写且报错返回 exit 0；注：`isinstance(engine, FallbackEngine)` 已正当改为 `EngineEventSource` 协议。
2. **代码质量与硬编码**：
   - **[P0]** `audio_utils.py:30-45` `get_audio_duration` 调 `ffprobe` **未检 `returncode` 且无 `timeout`**（卡死永挂）；`transcribe.py:173-188` 配置非法时回退 `normalize_config(overrides)` 跳过 `validate_transcription()` 且静默丢弃翻译配置。
   - **[P1]** `Config.translate_batch_size` 为死字段；`engines/mimo.py:33,106,182`、`whisper.py:22`、`audio_utils.py:14,115`、`translator.py:23-35,91` 硬编码模型/重试/超时/参数；`translator.py:50` 用非确定性加盐 `abs(hash(right)) % 100000`；`company.py:17-40` 硬编码 6 家公司兜底；`core/output.py:131` 缺 `os.fsync()`；`core/local_diagnostics.py:110` 线程不安全地修改全局 `_LOGGER`。
3. **日志体系与历史错误固化**：
   - **[P0]** `transcribe.py:127-131` `basicConfig(stream=sys.stdout, format="%(message)s")` 将全部运行日志与 `core/feedback.py` 旁路故障告警全部打向 `stdout`（无时间戳/级别/脱敏/轮转），且 `:138,152,181,191,198,218` 把致命错误按 `logger.info` 打印；`feedback_owner.py:319-348` 零日志；`local_diagnostics.py:164` 库调用模式为 no-op；13 处 `logger.error/warning` 缺 `exc_info=True`。
   - **历史缺陷 CI 锁定缺口**：CLI `--engine` 省略保 `config.json` 与 CLI 覆盖优先级缺真实 CLI 回归、`ffprobe` 非零退出缺测试、全部 Windows 原子替换/长路径测试在 Ubuntu-only CI 跳过。
4. **E2E 测试与 CI**：
   - **[P0]** `ci.yml:11,26` 仅 Ubuntu Py3.13 且被 `test_ci_workflow_config.py:79-89` **测试强锁为单作业禁止 OS 矩阵**；`f4_child_runner.py:190,248` 劫持 `load_config` 与 `urllib.request.urlopen`，跳过真实 `config.json` 优先级与真实 TCP/HTTP 断流、真实 `ffprobe`/`ffmpeg` 集成。
