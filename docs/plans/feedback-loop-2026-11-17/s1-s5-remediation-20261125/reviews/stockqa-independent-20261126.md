# StockQA 整改候选独立复审

2026-11-26。基线 `a4a81e5a818887835095f109e204f6d8a984fd17`。受验补丁 SHA-256 为 `83d455d63d0d40dd9171257f9c5fc1099d7e9cfe4dc59dbe99769cf71295a2a8`。执行根为隔离候选 `.planning/r25/qa`。所有外部运输为合成替身。生产和候选源码保持原样。

**判定 HOLD。** 28 项原修定向回归通过，包含本机公开 CLI 的预检拒绝、正常及发送意图后强停、新进程只读查回、批中抛出的每题编程故障、现有账本边界和已付原记录恢复。另有两条原身份与原因保真缺口。

## P1 · 异步批的运输异常被投影为普通拒绝

在 `tests/unit/test_async_llm_provider.py::_provider` 创建的合成 provider 上设 `max_retries=1`。以一个异步运输替身实现 `send_search_request_async`。每次先抛合成 `TimeoutError`，再以现有 `LLMTransportAttemptError("TimeoutError", receipt)` 包装。每题有不同的合成 `receipt.request_id`。调用实际公开 `batch_search_async` 两题，随后在独立新进程调用 `src.utils.quick_scan_feedback_owner runtime-history`，使用原批 run/attempt。

- 两题各执行一次合成运输，返回的两个业务条目均为 `error`。
- 冷读有两条原题身份记录，均为 `WorkClaimRefused / async_provider_returned_error`。两个 `chain` 都是空，原请求引用缺失。
- `src/providers/async_llm_provider.py` 的 `_call_llm_api_async` 已把运输异常和 receipt 转为 `ParsedLLMAnswer` 及通用元数据。外层失败投影只看到业务状态。实际 cause 和它与运输事实的关系在跨边界时丢失。

复验须保留原两条的题号、调用域、`LLMTransportAttemptError` 与其 `TimeoutError` 因果、对应的安全请求引用。保持原业务返回形状、计费未知和两次实际调用数。通过已转换的业务状态构造泛化拒绝仍无法复现运输异常。

## P1 · 原生已付查询接受别的父运行身份

沿 `tests/unit/test_quick_scan_feedback_owner.py::test_reconcile_knows_the_exact_native_paid_cost_without_changing_it` 构造隔离本地原生账本。用合成 USD 0.25 的收据，确认该尝试收到响应并因缺少答案进入已结算失败。通过正式 `quick_scan_refresh_inspect_cli` 写出一份该 ledger 的 `settled-disposition`，明确外层 run/attempt 为 `qa-original-observation` 和 `qa-original-wrapper`。inspect 的 `API_requests=0`。

后续三次均执行实际 `quick_scan_feedback_owner reconcile`，通过同一既有 observation-dir 和绑定状态读取原账本，不显式传业务 ledger。每次重算该测试 action 的协议摘要。

| 请求中的原观察 | 结果 |
|---|---|
| 未改 | `done / failed / known` |
| 仅改父 `run_id` | `done / failed / known` |
| 仅改父 `attempt_id` | `done / failed / known` |

原账本字节逐次保持一致。普通执行失败的 `read_execution` 已核对身份。结算分支在 `quick_scan_feedback_owner.py` 用 `SettlementRef` 只读 native evidence 和 native attempt。现有 `ledger_bindings` 没保留外层观察身份，lookup 将另一次运行的标签附着于相同付费事实。应将当前整条已发布观察与原生引用一并查回，兼容显式历史 owner 账本的无外层身份读取。

## 可复跑范围

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHON_DOTENV_DISABLED='1'
C:/Miniconda/python.exe -B -m pytest -c pyproject.toml --rootdir . --confcutdir . -p no:cacheprovider --basetemp ../ivq -q --tb=short tests/unit/test_execution_feedback_intake.py tests/unit/test_async_llm_provider.py tests/unit/test_quick_scan_native_lifecycle_boundary.py tests/unit/test_paid_runner_independence.py tests/unit/test_paid_result_preservation.py -k 'public_spend_preflight or public_dispatch_can_be or batch_failure_is_readable or async_repair or quick_scan_native_lifecycle_boundary or paid_runner or received_recovery or paid_partial_publication or real_paid_partial_output'
```

Windows 本机结果 28 通过，51 未选中。两条新增反例使用退出后清理的独占工作根。首次异步反例在隔离候选入口加载日志模块，向该候选已有测试日志追加了合成记录；后续直接探针先切换到独占工作根再导入。真实使用量、供应商费用均为零。
