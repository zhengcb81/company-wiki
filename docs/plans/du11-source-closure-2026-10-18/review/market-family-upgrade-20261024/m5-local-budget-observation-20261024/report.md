# M5 本地预算观察链根因修复

日期：2026-10-24

## 范围和结论

修复 CWP 本地准备被限额阻断时，owner 计量无法穿过 ensure、FF 和 RF 的共同传递断点；同时修复本轮回归暴露的历史期次二次发现丢失scope的问题。CWP源码提交为 `0f64289e`。FF 改动 `324ced2` 和测试时限根修 `e0d9642` 已推送；精确 FF CI [40115441655](https://github.com/zhengcb81/filing-fetch/actions/runs/40115441655) 成功。

**验收结论：** 三模块合同/历史scope/跨仓离线端到端组合46项通过；Ruff、CWP三个修改源文件的mypy、host-assumption guard与diff-check通过。FF完整pre-push为933 passed、7 skipped、78 subtests，耗时127.92秒。CWP源码已常规提交；本PWF收据提交、CWP正常推送及精确CI仍待完成。

## 根因和修复

1. `AcquisitionCoordinator.ensure` 的本地准备分支只投影status/reason/causes，丢失 `LocalReadBudget.observation()`。现在仅允许一个owner observation，并将其纳入已有 `local_preparation`。CWP operation contract严格校验schema、usage scope、精确key set、令牌、limits、counters、elapsed与bound；不允许路径字段或重复owner观察。还补了unhashable bound反例，避免畸形JSON穿透成裸 `TypeError`。
2. FF虽已有`filing-local-preparation-observation/1`，没有从CWP子操作构造其既有观察。现将owner预算映射到此既有结果格式，不引入新账本/许可门；`provider_started`保持false，provider预算字段不伪造。
3. canonical local group二次发现未复用请求的`HistoricalCaptureScopes`，也未向`qualified_source_scope`传递已登记的metadata。可信历史commit的S-1因此变成未知period并可能被打开。现在二次发现复用同一journal并读取登记metadata，原历史排除规则保留。
4. FF第一次push门禁6项失败是测试时窗本身的竞态：一例用3秒覆盖身份识别和后续ensure，而Windows probe用1秒包含自身Python启动。仅扩大这三个合成请求的测试budget（10秒）和probe启动/清理窗口；生产deadline、cleanup、子进程归属与“不杀无关进程”断言未改变。8个相关用例8/8通过，随后完整pre-push通过。

## 端到端验证

CWP端到端使用独立临时lake、构造的有限issuer目录、socket拒绝器和marker provider。RF请求产生source-group discovery超限，并实际穿过RF source preparation→FF→CWP ensure。

- RF观察包含已有 `filing-local-preparation-observation/1` 与唯一 `local_read_budget/1`，包括 `phase=source_group_discovery`、`triggered_bound=max_discovery_groups` 和消费值`limit+1`。
- `provider_started=false`、下载数0、marker provider从未启动、网络拒绝器未触发、`local_io_usage`不被混作网络账本，返回error不含lake物理路径。
- 最终CWP命令：`pytest -q tests/contract/test_source_operation_v2.py tests/contract/test_canonical_acquisition_scope.py tests/integration/test_local_budget_observation_rf_e2e.py`，46 passed（26.44秒）。历史scope文件22项通过；包含新增shape边界及畸形bound测试。
- CWP `mypy acquisition.py local_reconcile.py operation_contract.py`成功；修改文件Ruff通过；host guard为68既有baseline violations、0新增；pre-commit最终通过。
- FF：被阻塞的8例单独复跑8/8；完整pre-push 933 passed、7 skipped、78 subtests（127.92秒）；精确远端CI为success。

## 限制与剩余项

没有provider请求、原件下载、模型调用或Dayu修改。真实Snowflake 2020 S-1原件当前不在`companies/`，也未重跑旧请求。因此此修复证明**观测路径**可用，不证明已查明历史事故触发的是哪一项local bound；原始触发bound保持OPEN。以后从可得的原请求/原件离线复放时，可沿同一owner observation直接读出阶段和限制，而不需要再造诊断机制。PWF后续主线继续正式摘要与缓存恢复验收、RF实际采用及四审。
