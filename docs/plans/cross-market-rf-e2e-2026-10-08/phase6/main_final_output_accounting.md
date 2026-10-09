# MAIN：重试的最终输出槽与供应商账分开

状态：实施中，属于 Phase6 Worker 可恢复性；先集中责任测试，再由跨 run 包的真实 POST-kill / ACK-outbox 用例验收。

## 实际根因

本机单源最终文件上限默认 2 MiB，旧实现却对每次 model attempt 都预留 2 MiB，再求和。Worker 在 POST 后失联，费用必须保持 unknown，但该未知 attempt 的输出预留永久挤满整个单源上限。实际故障恢复只有 3382 tokens / 3782 microUSD / unknown1，低于 200000 tokens / USD2，仍返回 budget_exhausted，没有最终 artifact。不能用扩大上限或允许测试接受 budget_exhausted 冒充恢复成功。

## 责任与实施

1. 保留现 AUTO 数据、旧 attempt、费用与 output receipts，不建新表/数据库，不清未知费用。
2. token / cost 是调用消耗，按所有 attempt 累加；最终文件是 summarize job 对应的一个派生结果槽，重试同 job 复用此槽。
3. 输出预算对每 job 的未结算 bound / 已结算 bytes 取最大值再合计。新 attempt 入场只增加该 job 的槽差额。未知旧 output 不猜成 0；已损坏或超额的实际 receipt 仍拒绝。
4. 不同 job 并发必须各自占槽。真实 scratch / SQLite / content-addressed objects 的物理增量继续由既有 BatchStorageBudget 计量，不能把账本槽误称实测文件大小。
5. 只改 narrative_run_store.py 及 unit 责任测试；共享 batch 包由另 owner 改造，MAIN 合并后集中联调。

## TDD 与大节点

- 同 job 失联后用同一个槽再尝试，足够的 token/cost 下可入场；unknown旧费用保留，旧 output receipt 不改。
- 两个不同 job 输出槽超过 run cap 仍拒绝；同 job 重试较大 bound 也受差额限额约束。
- known usage / unknown usage / finished-but-unsettled output 均遵守独立计量；新尝试不能规避 token/cost 总额。
- final bytes 超过原 attempt bound、receipt 冲突、活跃 lease 和原 run 身份等既有责任测试保持。
- 集成后实际 supervisor POST-kill → 原 run 恢复 → completed / public read，另 run 默认复用 0 POST；费用未知保留。ACK 已写入结果的故障则必须 outbox 恢复，不允许再发 POST。
- 测试 TEMP 独占且恢复初始状态，外部收费调用 0、原件修改 0。

责任节点：6新用例真实4RED/2PASS（2.77秒）→含既有run/lease/unknown/modelcaller共50PASS（8.00秒）；ruff PASS，mypy按本项目ignore_missing_imports两模块PASS。真实POST-kill回主线后仍待重跑，不冒充完成。
