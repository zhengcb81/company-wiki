# W07 controller 独立审查：工程范围通过

- **结论：PASS_ENGINEERING_CONTROLLER_ONLY**。产品最初 `8b00fd7f` 的一个真实工具缺口已由作者修复；最终绑定 **`5a1548e228bfdf231ca624767661ed138c962136`**。
- 非作者审查：本审查者没有编写或修改 W07 产品与作者测试。作者最终文档 HEAD `8a9b57b1`，工区干净；四个工具、两个测试的物理 SHA 与 Git LF blob 分别绑定，测试前后六文件字节一致。没有改生产 src、配置、CI、原生预算/数据库实现或安装副本。
- **9 个新的独立场景均已通过，0 未解决问题、0 skip**。明确是同一最终源码上的 **7 个负向/预算通过 + 2 个正向定向收口**，不是声称有一次 9 例全绿调用；每例对应 XML、命令、源码及证据 SHA 见同名 JSON。

## 独立覆盖

| 场景 | 实际检查 | 结果 |
|---|---|---|
| 已知 usage 完整链 | 精确纯 preview →实际 configured CLI/loopback POST → durable paid pin →原生 RETRYABLE 和暂停 →新进程、attempt、lease、更高 fence 的实际 `_recover`/`replay_response` →activation_pending →同 run 完成 →新 run/workdir 同 artifact cache →再次重入 | 通过，始终 1 POST，0 新预留/费用/token；公读验真 |
| UNKNOWN usage 完整链 | 同上，直接读 native budget，未知费用/token 预留在拒绝旧 finish、恢复与 cache 后保持 | 通过，始终 1 POST，UNKNOWN=1 |
| 缺/坏 paid-response 对象、请求变化、current parent 无效 | 每类连续两次失败重入；原生账和唯一 paid operation 不变；无 `post_refused` 事件，排除只靠 HTTP guard 遮住二次发送 | 4 例通过 |
| preview 后输出上限或 model 改变 | 实际 configured body 不同，在 native reservation 和 HTTP POST 前明确拒绝 | 2 例通过，0 POST/预留 |
| 精确预算差一个单位 | 真实 UTF-8 body 的 `len(body)+128+400`，保留配置输出 400；不足预演不建 AUTO/run/locator/预留，正式入口也不 POST/预留 | 通过 |

正向预演的实际 body 保守上界 **8,590**；随后正式 run 就使用该精确上限。纯 preview 前后完整 catalog 文件 SHA 树一致、AUTO 不存在，未伪造原生执行收据。首次正式 HTTP body 与 preview 完全相同，wire 是 `narrative-model-request/6` 的真实 source cards/ranking。loopback 模型仅根据收到的任务 key 排名，无 reviewer gold 或特定公司答案。

已知 usage 的原生模拟账为 92 tokens /111 micro-USD；UNKNOWN 保留 8,590 tokens /8,990 micro-USD 的保守预留。这些是隔离夹具的原生记账，真实供应商调用和费用均为 0。恢复和跨 run cache 不追加该账。RF 始终明确 `not_consumed`，不以 artifact 可读代签实际参数使用。

## 发现与根因修复

**W07-INDEP-01（已解决）：** Observer 抛出 `HOLDOUT_AFTER_PAID` 并标 RETRYABLE，但该错误码不在原生 registry 的可重试集合中。原生分类器实际正确地保存为 TERMINAL_FAILURE；工具却称普通 RETRYABLE 已提交。初轮有效 RED 为 7P/2F/129.01s，两个失败均直接读取真实 native Attempt，非准备夹具失败。

作者在 `5a1548e2` 仅修改工具：使用已有合法 `IO_TRANSIENT`，进程内 marker 绑定实际 attempt/job/lease/fence，finish 后实读原生 RETRYABLE 才暂停；controller 再实读一次验证。没有修改生产 registry、权限、SQL 或预算逻辑。最终正向还直接读取新 lease/fence，并在拒绝旧 finish 后实读 native budget。

**审查测试自身的一次纠正：** 产品修复后，七例负向/预算继续通过；正向已完成 RETRYABLE、新进程/租约和 replay，但旧 finish 先被批次既有 PAUSED gate 的 `RuntimeGateClosedError` 正确拒绝。测试只接受 lease/fence 异常，假设过窄。接受这一明确原生拒绝后，仅复跑受影响的两个正向，**2P/0F/0S/53.79s**；产品没有为适应测试再改动。原 trace 和测试快照保留，未改旧 RED。

## 命令、字节与清理

- 使用作者冻结源码树与真实 configured 子进程，独审自有 `pytest.ini`/conftest，显式 PYTHONPATH；共享 source/server builder 只用于准备，九个场景与断言均为本审查新写，不把作者的 9P/10P 计入独立数量。
- 独立 Ruff 检查产品四工具、作者两测试及本审查两文件通过；mypy 四工具通过。仅允许 loopback，禁用 dotenv、删除进程内真实 provider key 并设置 synthetic key；不记录认证 headers/env 值。
- `source-before-final.json` / `source-after-final.json` 保存六文件物理和 LF SHA；同名主 JSON 列出全部指纹与逐证据 SHA。CodeGraph 在作者只读工区未初始化，本审查不建索引，以冻结 diff 和具体文件审查。sandbox Git 无法遍历该工区，正常本机只读 Git 成功，没有改作者索引。
- 独占短 TEMP `.planning/w7rv`、显式 mypy 缓存 `.planning/w7type` 均恢复不存在；两轮 cleanup 收据保留。每个 synthetic source fixture 先核原件字节后恢复初始 sentinel；current-parent 负例只暂改自有合成原件并恢复。未删除作者 TEMP 或生产原文。作者自有临时目录另由作者清理，最终工区 clean。

## 下一步与边界

ROOT 可以整合该冻结工具并按实时预算运行真实 holdout 的纯 preview 和配置内 paid 验收。本次只通过**离线工程链**：不代签真实模型内容、真实供应商计费、RF `consume_narrative_input` 与实际使用参数/公式、主线发布或安装验收。完整 source/native events/account/public-read 小证据与可重跑独立测试在同名目录；实际测试 fixture 已按要求清理。没有新增小节点人工许可、第二任务库或收费账。
