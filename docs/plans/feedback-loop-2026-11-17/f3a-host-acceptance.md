# F3a 真实宿主与原生 FF 作业恢复

2026-11-17。使用本机已登录的 Codex CLI `0.169.0-alpha.11.1`、FF `a17fc632aebf8b50d9d071e4816cb672f6f5637e` 和药明康德 2026 半年报。CWP 通过既有目录挂载原件，在独占测试库登记来源和证券快照。仅请求 `reuse_only`。

| 注入与检查 | 原生结果 |
|---|---|
| 丢弃 FF submit 回复后按原键查询 | `idempotent_replay=true`，作业 `ffjob-febb9d08abaa`，查询总数为 1 |
| 真实 Codex 分诊启动后终止首个总控进程 | 终止时 FF 仍为 `running`，原生尝试次数为 1。故障仅施加到总控进程 |
| 从原观察及磁盘作业恢复 | 稳定总控 action `99ad4d77…` 取回同一个 Codex 会话 `01a1eb74-48a1-7c20-94ef-c0c456f8509e` 的终态，分诊判为预期故障注入 |
| FF 最终完成 | 原生 `run_started=1`、`attempts=1`、`execution_count=1`。恢复只发三次 `get_status`，无第二次 run，实际下载为 0，费用状态 `not_applicable` |
| 原件与清理 | 从 FF 返回的 SourceRef 核对 SHA `d0dba19ede6e35ae3e127a1da91a42f04262e90d14efeb847bdfbff9b6354a5f`。1,216,470 字节和修改时间一致，原件复制为零，独占测试目录已清除 |

本机证据位于 `.planning/shared-reading-production/f3-feedback-20261117`。`host-live.json` SHA-256 `97aa3f04e606c43e642364d5168ead46b583276ef7f4e3505d886ce6922dfa1e`。`host-live-driver.py` 记录实际故障注入和公开调用。Codex 记录输入 24,546、其中缓存 13,056，输出 27 tokens。资料摘要费用使用独立业务账本。

独审核对实际执行脚本、原件 SHA 及作业收据，通过 F3a。定向组合 24 项通过。回调会在运维显式配置的有限窗口内跟随异步结果。离线探针还核对了宿主终态写回前中断、唤醒消息丢失、冲突请求、未知费用和写工作区隔离。这次现场演练中 FF worker 持续运行，失去 worker 或付费用量未知的证据来自独立回归。真实修理可使用宿主同一调度端口和明确配置的责任工作区。现场 Codex 调用为只读分诊。
