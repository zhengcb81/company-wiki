# S1 立项计划：全生态 P0 日志黑洞止血（2026-11-24）

> **立项状态**：`PUBLISHED`（2026-11-24 全部 8 仓 S1-01..S1-08 已完成 RED→GREEN 根修、定向回归与静态检查，合计 **462 passed / 0 failed**，并已逐仓提交与推送到各自发布主线）
> **父计划**：[feedback-loop-2026-11-17/task_plan.md](task_plan.md) · [full-12-module-architecture-logging-audit-20261124.md](../module-boundaries-2026-11-11/review/full-12-module-architecture-logging-audit-20261124.md)
> **实施纪律**：
> 1. 每项修复均采用 **RED → GREEN TDD**：先写精准复现日志黑洞/吞错的测试并确认红灯，再做最小根修，回归受影响测试集确认绿灯。
> 2. 严格保持对外机器 JSON `stdout` 协议、退出码及脱敏边界不退化；绝不触碰各仓已有在途/未提交改动（如 RF `assurance/runs/*`、MC `.coverage`、ET handoff、CWP `read_budget.py`）。
> 3. 每完成一个批次（Batch 1 / Batch 2）即时回写本表状态、测试结果、改动路径及遇到的问题。

---

## 一、8 仓 S1 工作包与实时进度台账

| ID | 责任仓 | 基线分支 / SHA | P0 目标缺陷与精确落点 | 状态 | 改动文件 | RED→GREEN 验证结果 |
|---|---|---|---|---|---|---|
| **S1-01** | `MeetingConverter` | `master@e0ab125` | 1) `engines/mimo.py:137` 调用未定义 `logger.warning` 致首次重试抛 `NameError` 覆盖真实 API 错；2) `core/feedback.py:1086` 捕获 `BaseException` 吞掉中断信号且无 stderr/日志告警 | `done` | `engines/mimo.py`, `core/feedback.py`, `tests/test_s1_logging_resilience.py` | RED 精确复现 `NameError` → GREEN：**64 passed / 0 failed**（`test_s1_logging_resilience` + `test_mimo_engine` + `test_output_feedback`） |
| **S1-02** | `StockInfoDLSimple` | `v2-clean-rewrite@9e35347` | 1) `src/logger.py:15,39` 导入期空句柄短路导致 `config["logging"]` 永久失效（零日志文件写出）；`main.py:460` 早于 `load_config()` 初始化；2) `src/browser.py:645` 宽泛吞错静默返 `total_pages=1` 截断分页 | `done` | `src/logger.py`, `main.py`, `src/browser.py`, `tests/unit/test_s1_logging_and_browser_errors.py` | RED 复现零日志文件与未抛 `BrowserError` → GREEN：**50 passed / 0 failed**（`test_s1_*` + `test_browser_tab_selection` + `test_failed_logger` + `test_downloader`） |
| **S1-03** | `filing-fetch` | `main@1defca5` | `scripts/ff_scheduled_windows.py:153-160` 定时 tick 子进程将 `stdout`/`stderr` 双重路由至 `DEVNULL`，导致启动/导入/未捕获异常全部无痕消失 | `done` | `scripts/ff_scheduled_windows.py`, `tests/test_s1_windows_tick_logging.py` | RED 复现失败 tick 零 stderr 落盘 → GREEN：**17 passed / 0 failed**（`test_s1_windows_tick_logging` + `test_scheduled_refresh` + `test_scheduled_refresh_public_e2e`，成功运行零目录残留） |
| **S1-04** | `earnings-transcripts` | `main@6ee1844` | 1) `transcript_api.py:804,1142,1404` 将所有未预期异常静默吞为裸 `unexpected_provider_failure`（零日志/堆栈）；2) `retrieval_runtime.py:84-99,257-284` 崩溃后只抽类名并立刻删除 `worker_stderr.log` | `done` | `transcript_api.py`, `retrieval_runtime.py`, `tests/test_s1_provider_error_logging.py` | RED 复现 3/3 漏记 → GREEN：**70 passed / 0 failed**（`test_s1_*` + `test_transcript_api` + `test_retrieval_runtime` + `test_runtime_contract_isolation`，保 `temp_root` 零残留） |
| **S1-05** | `company-wiki` | `master@90b15051b` | 1) 清除 7 处生产 `stderr=DEVNULL`（`tools/feedback_loop/local_host.py:187,343,533,549`、`intake.py:330`、`hook.py:45`、`isolated_ocr.py:371`）；2) 修 `isolated_ocr.py:222` 裸错误、`narrative_projection.py:261` 批量激活静默 `continue`、`runtime_feedback.py`/`intake.py:373` 写失败静默吞错 | `done` | `src/company_wiki/document_normalization/isolated_ocr.py`, `src/company_wiki/automation/narrative_projection.py`, `src/company_wiki/runtime_feedback.py`, `tools/feedback_loop/{hook,intake,local_host}.py`, `tests/unit/test_s1_p0_logging_blackholes.py` | RED 5/5 复现 → GREEN：**25 passed**（`test_s1_p0_logging_blackholes` 5 + `test_feedback_f4_intake` 20）+ **86 passed**（`test_layer_public_boundaries`）+ Ruff 全通过 |
| **S1-06** | `revenue-forecast` | `main@698eabd1` | 1) `scripts/filing_fetch_client.py:357-377` 非零退出/非法 JSON 报错未读取 `completed.stderr` 且 `:376` 丢 `from exc`；2) `scripts/rf_job_facade.py:940-944` 丢 `from exc` 且不记诊断详情 | `done` | `scripts/filing_fetch_client.py`, `scripts/rf_job_facade.py`, `tests/test_s1_p0_error_observability.py` | RED 复现空 stderr 与丢 `__cause__` → GREEN：**9 passed / 0 failed**（`test_s1_p0_error_observability` + `test_rf_job_boundary_regression`） |
| **S1-07** | `StockWiki` | `master@153e87e` | 1) `documents.py:93,154,193,242,390` 解析崩溃静默返 `None`；2) `llm_usage_ledger.py:60,129,147` 计费写入/定价读取失败静默返 `None`/`{}`；3) `ui.py:163,243,246` 空 `log_message` 且吞 500 堆栈；4) `dashboard_onboarding.py:548` 死三元表达式 Bug | `done` | `stockwiki/documents.py`, `stockwiki/llm_usage_ledger.py`, `stockwiki/ui.py`, `stockwiki/dashboard_onboarding.py`, `tests/test_s1_p0_logging_observability.py` | RED 2/2 复现静默吞错 → GREEN：**72 passed / 0 failed**（`test_s1_p0_logging_observability` + `test_ui` + `test_dashboard_onboarding`） |
| **S1-08** | `StockQAbyLLM` | `codex/qa-content-filter-resolution-01@e64c3e5` | 1) `quick_scan_owner_research.py:462` `stderr=DEVNULL` 及 `quick_scan_owner_budget_permissions.py:79`/`quick_scan_work_decision_authority.py:152` 丢弃 `stderr`；2) `llm_provider.py:990-1047` 与 `async_llm_provider.py:366-429` 宽泛重试代码 Bug 且只记 `type(e).__name__` 无 `exc_info=True` | `done` | `src/utils/quick_scan_owner_research.py`, `src/utils/quick_scan_owner_budget_permissions.py`, `src/utils/quick_scan_work_decision_authority.py`, `src/providers/llm_provider.py`, `src/providers/async_llm_provider.py`, `tests/unit/test_s1_p0_provider_and_subprocess_logging.py` | RED 复现 `DEVNULL` 与编程错重试 → GREEN：**69 passed / 0 failed**（`test_s1_p0_provider_and_subprocess_logging` + `test_llm_provider`） |

---

## 二、验收标准（每个工作包必过）

1. **红灯复现（RED）**：新增或补充定向单元测试，在修改源码前能稳定复现原日志黑洞（如 `NameError`、零日志文件、空 stderr、`__cause__ is None`、静默返 `total_pages=1` 等）。
2. **最小根修（GREEN）**：保留既有公共 wire 协议与脱敏约束，修复后新增回归测试与该仓受影响既有测试全部通过。
3. **无副损伤**：各仓已有未提交文件保持原样；未向任何仓库引入生产密钥泄露、stdout 污染或非授权跨仓写盘。

---

## 三、实施日志与遇到的问题（Errors Encountered）

| 时间 (UTC) | 工作包 | 观察 / 错误 | 处理与结论 |
|---|---|---|---|
| 2026-11-24 20:19 | 立项 | 核验 8 仓当前分支/HEAD 与在途脏文件（MC `.coverage`、ET handoff、RF 4 项 assurance/PWF、CWP `citation-release`/`read_budget.py`） | 全部与 S1 目标源码零重叠，施工期间严格保留原样。 |
| 2026-11-24 20:25 | Batch 1 (S1-01..04) | 完成 MC / SID / FF / ET 四仓 RED→GREEN 根修；确认 FF 成功运行零目录残留契约与 ET `temp_root` 零残留、无 provider 导入隔离契约全部保持 | 四仓受影响回归合计 **201 passed / 0 failed**（MC 64、SID 50、FF 17、ET 70）；已转入 Batch 2（S1-05..08）。 |
| 2026-11-24 20:34 | Batch 2 (S1-05..08) & Ruff 清理 | 完成 CWP / RF / StockWiki / StockQA 四仓 RED→GREEN 根修；Ruff 检出 `_logger` 定义位于局部 import 之上触发 E402 | 已统一将新增 `_logger`/脱敏 helper 移至各文件顶层 import 之后；CWP 全量 Ruff 与 8 仓 E402/F821 检查全部通过，8 仓 `git diff --check` 均为 0；Batch 2 定向回归 + CWP 边界契约合计 **261 passed / 0 failed**（CWP 25+86、RF 9、StockWiki 72、StockQA 69），8 仓 S1 最终复扫全绿。 |
| 2026-11-24 21:00 | 全 8 仓提交与推送 | 严格按显式路径提交，保留各仓原有在途未提交改动；RF 本地 `main` 与远端 `origin/main` 分叉，采用独立临时 worktree 从 `origin/main` cherry-pick 验证后快进推送；StockWiki 按仓无远端仅提交本地 `master`；StockQA 沿现行发布线 `codex/qa-content-filter-resolution-01` 提交推送 | 已发布 SHA：`MeetingConverter` `master@8c97cc5`、`StockInfoDLSimple` `v2-clean-rewrite@24ce0be`、`filing-fetch` `main@f43a875`、`earnings-transcripts` `main@cda3afb`、`revenue-forecast` `origin/main@db4f8c7a`（本地 `main@d62fca9a`）、`StockWiki` 本地 `master@9904b43`（无 remote）、`StockQAbyLLM` `codex/qa-content-filter-resolution-01@1449d71`、`company-wiki` 随本提交发布至 `origin/master`。 |
