# StockQAbyLLM S1–S5 独立复审

2026-11-25。F4 检出为 `C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime`，完整 SHA 为 `a4a81e5a818887835095f109e204f6d8a984fd17`，与本地 `origin/master` 引用一致。F4 检出为 detached HEAD，复审前后均干净；StockQA 主工区的三份在途计划保持原状。F4 是 sparse checkout，测试从同 SHA 的 Git 对象导出到独占临时根，运行在 Windows Python 3.13.9。使用合成输入和运输替身，外网连接、新供应商请求、真实费用和生产写入均为零。远端 CI 与正式 C06 现场验收沿用已有台账。 [S5 发布台账](../../../s5-verification-20261125.md)

| 项目 | 判定 | 本轮证据 |
|---|---|---|
| S1 | 已验，限 S1-08 及已付恢复切片 | 同步 provider 的编程错只调用一次，保留原 `KeyError` 与 traceback。异步公开单请求对本地注入的 `TypeError` 同样快速退出并留下 traceback。三个 StockWiki 子进程边界的退出 23、长 stderr 尾段、Bearer/Basic、折行及查询凭据脱敏、显式进程环境定向回归均通过。已付恢复从原 SQLite 读取，无新请求和账本变化。异步批入口的可追溯性见下方。 |
| S2 | 部分 | 双进程共享日志轮转、F4 结构化错误、公开 owner 跨目录冷读与重复查询通过。预算预检业务运行号与 F4 运行号断开，诊断写入皆失败后普通日志无该拒绝。异步批次有本地错误文本，缺少同身份的原生观测。全阶段成功、拒绝、进程启动、强停和恢复的统一运行记录仍未证。 |
| S3 | 部分 | 正常输出和已付恢复输出均交给 `QuickScanResultProofPort`，已替换历史的三个 lifecycle 私有字段读取。任务仍依赖具体的工作账本，装配层透传 prepared session 的 `service.store`。账本与 journal 的运行依赖、运输层原始连接及已配置的跨仓导入路径仍在。 |
| S4 | 部分 | 按真实 `DAILY_TEST_TARGETS` 和 `BASE_PYTEST_ARGS` 在 Windows 实收 426 项。已收 S1、轮转、冷读、已付恢复、并发测试及 AST 边界检查。当前预检关联、双写失败后普通本地日志和独立异步 provider 组未进日常。C06 为需要独占外部夹具的验收。 |
| S5 | 部分 | 已推送且 F4 已采用 `a4a81e5`，同版远端 CI 通过的证据见发布台账。复验了脱敏、stderr 尾段、环境注入、轮转、原账本恢复和切换目录冷读。S5-05 对所有相关入口的双层日志、S5-08 仓内账本依赖仍有缺口。 |

## 实测

- **原已付作业。** 运行 `tests/unit/test_paid_runner_independence.py::test_paid_runner_uses_original_receipt_metadata_without_today_model_or_budget`。夹具通过真实 `QuickScanWorkStore` 写入一次合成已收费收据及原答案后冷开同一个 SQLite。原请求、响应、模型、完成时点和搜索收据保持，原题数 2、恢复 1、剩余 1，`API_requests=0`、`dispatch_started=false`，账本字节完全相同。测试阻断现行模型配置、成本解析及 HTTP，使用原账本和公开结果证明适配器，并在 runner 的恢复方法上替换 owner 登记和共享引擎。这组恢复、S1 文件、两写者轮转和旧目录冷读共 **14 项通过**。 [已付回归](https://github.com/zhengcb81/StockQAbyLLM/blob/a4a81e5a818887835095f109e204f6d8a984fd17/tests/unit/test_paid_runner_independence.py#L44)
- **主入口 C06 证据。** 已验台账记录 `96a3ead` 在同一冻结 StockWiki/IQS 夹具上执行真实 `main_with_llm.main`，一次合成 POST 后工作项到 `result_ready`。移除合成供应商及预算配置后用原键恢复，同一运输计数仍为 1，恢复产物报 `API_requests=0`，无 lifecycle 私有字段读取。独立复审核对了同 SHA 测试的限位和断言，并采用上面的短恢复回归。十几分钟的组合 C06 本轮仅核证，进程强停未另做注入。 [C06 测试断言](https://github.com/zhengcb81/StockQAbyLLM/blob/a4a81e5a818887835095f109e204f6d8a984fd17/tests/integration/test_controlled_pack_main_public.py#L184) · [S5 现场与用时](https://github.com/zhengcb81/StockQAbyLLM/blob/a4a81e5a818887835095f109e204f6d8a984fd17/.planning/modularity-closeout-20261111/S5-STOCKQA-lifecycle-output.md)

## 已复现的可追溯性缺口

### P1 预算预检运行号断开，诊断双写失败后没有普通日志

在同 SHA 临时检出中启动以下公开命令。令 `RESEARCH_FEEDBACK_DIR`、`RESEARCH_FEEDBACK_OUT` 指向该临时根内的可写位置，清除继承的 `RESEARCH_FEEDBACK_RUN_ID` 和 `RESEARCH_FEEDBACK_ATTEMPT_ID`。用隔离审计 hook 禁止 DNS 和 socket 连接。

```powershell
python -B main_with_llm.py --company Synthetic --require-search --entity-id 00000000-0000-4000-8000-000000000001 --config missing.json --output result.json
```

- 正常诊断介质下 exit 2，stdout 只有一个 `stockqa.spend_preflight/1.0.0` JSON，原因 `spend_authorization_missing`。输出的 `run_id` 是 `run-20261125T222801Z-148581`，F4 的是 `cli-run-9b549457123a4775ae863db0073ef51d`。业务 JSON 没有 observation 引用或 attempt 供关联。传入原 F4 观察行，在不同 cwd 以 `python -B -m src.utils.quick_scan_feedback_owner --state <临时状态> --observation-dir <原收件目录> triage` 读得同一拒绝，`reconcile` 连续两次得到 `known / failed / not_applicable` 和同一 `evidence_ref`。原业务 `run_id` 无法用于这次查回。
- 双写失败复现将 `RESEARCH_FEEDBACK_DIR` 指到普通文件，`RESEARCH_FEEDBACK_OUT` 指到该文件的子路径，并以普通文件堵住隔离代码根的 `logs/.feedback`。同一公开入口仍 exit 2，stdout 单 JSON 保留原拒绝，stderr 提示 fallback 和 `execution failure tracking incomplete`。普通日志快照未改变，新运行无原生诊断和 sidecar，未生成工作账本或结果。冷读入口自身在处理错误时只发固定 stderr 并 exit 2。
- 根因在于预检先用上下文随机身份发观察，再单独生成对外 `run_id`。该分支向 `record_execution_failure` 传 `None` 作为 logger，并构造一个未抛出的 `ValueError()`，所以结构化诊断只记类别、参数形状和拒绝原因，栈为空，常规日志未承接该分支。诊断 I/O 异常独立处理，保留了业务结果。 [预检发观察与生成运行号](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/runners/llm_runner.py:2288) · [日志与观察写入](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/logger.py:171) · [F4 身份选择](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/execution_feedback.py:134) · [冷读失败分支](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/quick_scan_feedback_owner.py:351)
- 验收用相同公开命令配对无宿主 ID 与有宿主 ID 两种运行，断言 stdout 保持机器格式、公开运行号可映射到原观察、重复冷读只得原拒绝。再分别注入本地日志、原生收件和 F4 投影故障，核对仍可写的介质持有同一身份和拒绝码，原 exit 2、零请求和零原账本写入保持。

### P2 异步批入口只留下未关联的本地错误

在隔离根以现有异步 provider 测试配置初始化 `AsyncLLMProvider`，仅用 `AsyncMock(side_effect=TypeError("synthetic-async-code-fault"))` 替换 `client.send_search_request_async`。公开 `search_async` 只调替身一次并原样抛出，`batch_search_async` 对单个问题只调一次并返回 `[[]]`。本地轮转日志可见原 `TypeError` 行与调用堆栈，两次均无 native ready 文件或 F4 sidecar。公开异步类在本仓被导出，当前 StockQA 生产主 CLI 未发现实际采用它的路径。根因是 provider 编程错分支只写普通 logger，批量入口聚合异常为原协议的空结果，缺少对调用上下文的结构化投影。后续验收沿用单次尝试和批量返回格式，给聚合失败保留可查询的原问题/调用身份，并验证失败诊断不引发新增请求。 [异步失败与批量聚合](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/providers/async_llm_provider.py:420) · [公开导出](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/providers/__init__.py:8)

另运行 `test_async_llm_provider.py` 与 `test_quick_scan_module_boundaries.py`，共 **16 项通过**，包含异步格式修复的原始运输证明、未确定结算和持久化错误。当前 AST 检查通过时，下面列出的装配依赖仍可发生。

## 入口阶段和账本责任的剩余核查

- **CLI、provider 和子进程启动。** `observed_command` 在 wrapper 建调用上下文，对参数失败、抛错和非零返回发观察，零返回直接结束。主 CLI 轮转 logger 写普通文本，时间、模块名和代码行可见，格式器没有运行号字段。失败 F4 原生收据另有版本、`recorded_at`、参数引用和异常节点。已声明的 StockWiki 能力子进程使用显式 OS 环境及文件流，非零退出的 stderr 尾段和退出码在常规日志中，启动异常或超时沿异常链返回。启动成功、发送意图、响应已收、保存和成功恢复没有由该 wrapper 串成同一 ID 的观察。业务账本另有 attempt、send intent 与收据，部分正常/偏差从 `refresh_inspect` 按账本投影。后续应以原 attempt 串起一次合成成功及一次发送后强停的启动、外部副作用、保存、冷读与重投，保留原费用和观察身份。 [CLI wrapper](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/logger.py:264) · [轮转日志格式](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/logger.py:487) · [子进程配置与终态](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/quick_scan_owner_research.py:431) · [已结算观察投影](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/quick_scan_feedback_observation.py:683)
- **结果端口收口，主运行器仍握具体账本。** 主 runner 在适配成公开 owner port 之前读取 `prepared_session.service.store`，已付恢复 helper 用原 `store` 构造 lifecycle，再生成结果端口。结果端口是公共协议，适配器仍通过 `isinstance(QuickScanWorkStore)` 约束具体实现。实际外部检索证据和附加资料投影校验原 attempt、收据和 scope 后，用已声明的 `work_store.connect()` 执行原生查询。只提供已声明 owner/proof 方法的独立实现无法替换该装配，仍需携带原具体 store 及连接能力。这是同仓真实运行依赖，尚未看到跨仓读取工作库私表的证据。 [主 runner 取账本](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/runners/llm_runner.py:2527) · [已付结果装配](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/runners/llm_runner.py:3423) · [具体适配器](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/quick_scan_result_proof.py:24) · [外部资料投影](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/quick_scan_work_transport.py:673)
- **仓内运行环与跨仓装配。** 七千余行的工作账本仍代理 pack journal、预算、checkpoint、证据和发布。实走的 pack 准备由账本延迟调用 journal 的 `prepare`，后者再导入账本类型和冲突类并使用账本事务。这条边在真实 pack 准备时执行。跨仓能力探针走 StockWiki 公共 CLI，IQS 配置化装配另保留 `sys.path.insert`，且对 `iqs_root/scripts/shared_company_engine` 有结构依赖，companion 走已声明 `.api`。下一轮以只持公开证据操作的生命周期复验正常输出与原已付恢复，并把事务和连接归还到账本 owner。进程级验收覆盖现行及兼容启动，同时校验原收据、账本字节、尝试号与零新增付费。 [账本 pack 入口](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/quick_scan_work_store.py:6352) · [journal 返回账本的运行依赖](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/quick_scan_question_pack_journal.py:322) · [共享引擎装配](C:/Users/郑曾波/Projects/StockQAbyLLM/.worktrees/f4-runtime/src/utils/quick_scan_shared_company.py:125)
- **门禁具体遗漏。** GitHub 的 default job 在 Ubuntu Python 3.10 调用 `python -B scripts/checks.py`。现有 AST 检查能捕捉 `src/` 私有命名导入、已声明范围里的状态成员和非法 raw connection 调用。owner refresh 检查的变量名集合未含 `prepared_session`，所以 `prepared_session.service.store` 在实际 runner 和检查中共存。运输模块是 raw connection 允许项。默认 pytest 面板实际收集了 426 项，异步专门文件和 C06 主入口未选入。支持现有完整大节点，可在日常加两条短的行为约束，覆盖预检关联及有异常时公开批次依然可从新进程查回，另以真实对照固定已证的 owner 装配绕行。 [GitHub 日常工作流](https://github.com/zhengcb81/StockQAbyLLM/blob/a4a81e5a818887835095f109e204f6d8a984fd17/.github/workflows/ci.yml#L36) · [测试选择](https://github.com/zhengcb81/StockQAbyLLM/blob/a4a81e5a818887835095f109e204f6d8a984fd17/scripts/checks.py#L100) · [边界规则](https://github.com/zhengcb81/StockQAbyLLM/blob/a4a81e5a818887835095f109e204f6d8a984fd17/tests/unit/test_quick_scan_module_boundaries.py#L157)
