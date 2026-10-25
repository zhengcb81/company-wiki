# v4 运行器静态预审

**结论：当前版本不能放行真实运行；等待列出的实现缺口修复及绑定版本的定向测试后复审。** 本文仅审查流程与静态代码，不执行 `run_operation.py`、模型/API、下载、真实源解析或测试脚本。

## 审查范围与版本

- HEAD：`483cb2a56299cb28ca07bbd349674860baf04430`
- 运行器：`review/production-v4-formal-20261025/run_operation.py`，SHA-256 `99a78e354db38d52dedd205347db8c5ac96df20615dddb3ed540d5e994fa9f2`
- README SHA-256：`0736439592fab2533bc91cb1328d2cb426b8957ac28371eaa93e7c71e3148769`
- 复用实现：`tools/document_understanding_benchmark/phase_c_runner.py`，SHA-256 `3c744e6265d7790819d581e8204726258bdcb1b7813da59b1f04c3d42f6f8e99`
- 源码工作树在此审查时没有未提交差异；运行器本身是新建未跟踪文件。

## 通过的静态设计点

- 延用现有 `phase_c_runner.run_pair`、production worker、SourceRef、Store、usage ledger，没有新建 HTTP 客户端或第二套预算账本。
- 依据样本元数据选择 provider，再从 `Config.load()` 实际读取模型选项并做精确相等比较；用的是本地配置，不存在代码中的 provider override。
- 请求级上限为 100,000 tokens / $0.10，正式运行前用当前 usage ledger 与统一政策检查累计预算；新版本还计算账本前后差额，并把包含 unknown hold 的总数检查到单次与累计限制内。
- 预检将 `forbid_post` 注入 observer，并要求零 POST、唯一拒绝码 `PHASE_C_CACHE_WOULD_GENERATE`、完整必需 gold、预算账本不变、临时库删除。它是本节点的无付费烟雾预检，不是人工授权/签收门。
- 正式模式不依赖独立预检 receipt；这是符合用户“简化门禁”的选择。正式 `run_pair` 仍需就本次实际 source、gold、provider 和预算做新鲜的预留前检查。
- 运行器记录源、gold、配置及关键执行文件指纹；operation 输入在结束时复核未变。正式模式还要求 worker PASS、临时库删除及母账增量不超限。
- 最新 wrapper 另外记录当前 Git HEAD、`src/company_wiki` Python 文件树 SHA、读取到的 PWF 状态文件指纹及所用累计 caps。PWF 指纹是本次观察的来源记录，不作为付费前的人工作业许可或全文件稳定门；实际生效预算仍以政策配置严格比对。
- `registered_readonly` 路径复用已存在原件并校验源字节，不要求 raw 副本；恢复分支复用已持久化的成功响应，不该重新 POST。完整的恢复、FF、RF 仍必须由 ROOT 通过实际定向端到端运行验收。

## 尚未关闭的发现

### R1 — 清理会被账本快照异常短路（阻断真实运行）

`phase_c_runner.run_pair` 的 `finally` 当前先调用可抛错的 `append_native(...)`，之后才执行 `shutil.rmtree(root)`。SQLite 读取、usage ledger 写入或相关收据 I/O 一旦异常，finally 的后半段不会执行，owned 临时数据湖可能残留。`append_native` 虽然把 failure-review snapshot 错误局部捕获，但 native charge 持久化仍可能抛错。应使用嵌套 `try/finally` 保证临时根目录清理必运行；账本快照失败必须被报告为明确 FAIL/账本不确定，不能吞掉、继续 PASS，也不能让清理失效。需用临时目录故障注入测试证明“账本写入失败仍清理 + 运行失败 + 失败原因留存”。

### R2 — PWF 与实际使用预算的可追溯记录（已处理）

最新 wrapper 已记录 `pwf_status_fingerprint_observed` 与 `pwf_cumulative_caps_used`，并保留 PWF caps 与 `config/resource_budget.yaml` 的精确比较。PWF 是进度观察，不是运行时授权配置；不要求整个 PWF 文件在正式摘要期间冻结，也不应因正常进度更新使成功运行失败。该记录应清楚表达它是读取时的观察值。

## 复审条件

1. ROOT 完成 R1 后冻结 `phase_c_runner.py`、运行器和对应测试 SHA。
2. 对 R1 做真实故障注入：在 `append_native` 写母账失败时验证 owned temp root 仍被删除、最终状态不可能 PASS、费用/unknown 状态不被隐藏。
3. 对 R2 做运行期输入变更 RED：改写被测 PWF 快照后运行器必须失败；冻结输入 GREEN 后必须通过。
4. 通过 ROOT 指定的窄范围单测/CI 后，再对零 POST 预检做真实本地端到端验收；只有 ROOT 后续明确执行正式模式时才产生一次受预算约束的模型请求。检查账本前后差、unknown hold、source/gold SHA、恢复不重 POST、临时库回收。

没有要求 formal 必须读取前一运行的预检收据；以独立预检结果充当许可会重新引入用户已要求清理的签收门。真实付费前只要求同一次正式运行自身完成完整的最新 source/gold/config/预算检查与版本记录。README 与本静态报告不等价于实际端到端验收。
