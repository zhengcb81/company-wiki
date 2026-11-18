# F4 强制终止及真实宿主验收 · 2026-11-18

后续 RF/Audit 的真实宿主、中断恢复和回告见 [F4 RF/Audit 验收](f4-rf-audit-acceptance.md)。

## 1. FF 真进程被杀后的恢复

实际 RC 跑 FF 与 CWP 的公开 CLI。HTTP 提供方仅本机环回，供方模拟收费、实际记录请求次数。取件、原文验真和入库均已由真实 CWP 执行；在该结果送回 FF 前强制终止 FF 进程。仅保留 FF 开始行。两个恢复进程并发、再重投一次，都使用原生 `get_status` 和同一作业的只读 `act reconcile`。

| 请求 | 原作业 | 强杀后恢复 | 新增 |
|---|---|---|---|
| `exact` | `ffjob-be3c9ef3b114` | `succeeded`，原文 SHA 同一，原生尝试 1，run_started 1，reconciled 1 | 作业 0、HTTP 0、下载 0、模拟费用 $0 |
| `latest_as_of` | `ffjob-29589aa13abc` | `succeeded`，原文 SHA 同一，原生尝试 1，run_started 1，reconciled 1 | 作业 0、HTTP 0、下载 0、模拟费用 $0 |

两次原文 SHA 都为 `00d23755dabb6e6b2861f221da9695414db0bf1ee762aea4e2eea023c468bd9d`。每个原作业发生两个元数据 HTTP 请求、一个正文 HTTP 请求和一次入库。供方模拟原读费用为 $0.0009，FF 被杀前未写回终态，原账均保留 `unknown/null`；只读核对的零新增费用不会填回旧账。本地 `latest_as_of` 只证明已入索引的候选，不证明供应商侧最新。临时测试目录由测试夹具清理。

## 2. 真宿主分诊、修复、复验和回告

以现有半年报原件挂载隔离 CWP 目录，在 FF 原版 `a17fc632aebf8b50d9d071e4816cb672f6f5637e` 启动并强杀一笔 `latest_as_of` 作业。用原 FF 公共命令复现对账被正常采集限额拒绝；初始费用错误地显示为 `not_applicable`。分诊只使用该公开错误的脱敏字段，未发送原件或凭据。

真实 Codex 已创建 session `01a1f054-2130-7060-bc8e-e84f5c1c3f5e` 后强制终止总控。重启找回同一个 session 的结果。真实 FF owner 命令在隔离副本核对原代码、采用已独审的 Git 修复版 `a9f9d6d1f3af139c08898a296dba14574dbf044d` 并运行定向回归。CWP 发现端校验确实执行该版本，依据原观察再次查同一 FF 作业 `ffjob-4c54cbb8a9c0`，关联未改的原文及 SHA `d0dba19ede6e35ae3e127a1da91a42f04262e90d14efeb847bdfbff9b6354a5f`。业务结果找回，费用保留未知。

FF 用本仓 `get-report` 读回责任仓完整回告，包含原发现方、版本及复验引用。`observe/triage/repair/replay/report` 各 1 条终态。重复重启回执一致、下载及 FF 作业增加 0，Codex 没有新增会话。最终受控试验只用了一个分诊回合，输入 21,022（缓存 13,056）、输出 324 tokens；无业务模型调用。这是自动执行已独审修复的验收，不代表所有 owner 都已能自主生成、验证和发布任意新修复。[机器收据](f4-host-receipt.json)

最初诊断试跑中 Windows 沙箱在临时目录无法启动读文件工具（267）；Codex 正确返回 `needs_evidence`，没有执行修复。该尝试消耗输入 200,865（缓存 188,416）、输出 1,177 tokens，不算在成功作业的复用计数里。后续将已由 FF CLI 验证的脱敏证据直接附给只读分诊，确定性步骤由 owner 命令执行。两个宿主试跑均未请求供应商和业务模型，Codex 真实账单金额未从 token 估算。成功试验临时目录自动删除；早期试跑的进程锁解除后，其专用临时目录也已清空删除。

## 3. 重跑方法和检查范围

- 装配/强杀：设置 `FEEDBACK_FF_CODE_ROOT` 为兼容 FF 工区，用 `python -B -m pytest -q -s tests/integration/test_feedback_f4_owner_recovery.py`。只有被显式指定时才用相邻仓。保留两类请求、并发对账、一次入库、原文指纹和直接 HTTP 计数断言。
- 真宿主：[指定版本的试验脚本](../../../tests/integration/f4_real_host_probe.py)。在 `PYTHONPATH` 含总控仓根的正常宿主，从仓根运行 `python -B -X utf8 tests/integration/f4_real_host_probe.py --help` 查看参数。用上述 FF 两个版本、已归档的 `t4-phase-c-20261114/preparation.json` 内 `r4-cn-h1-real`、截至日 `2026-11-17`，以及本机已配置 Codex 路径。每次试验单独指定不存在的 `--output`，只在需要新验收时明确运行；正常重启按原 `recover` 继续。
- ROOT 反馈、CLI、Phase C 加跨层合同 114 项通过；历史本机环回 3 项在正常宿主通过；实际 FF/CWP 双强杀 2 项通过。FF 本仓 188 项及 8 子例通过，已推送 `main`。受限沙箱中的三个旧回归在第一个 POST 前失败，同一版本的正常宿主测试全绿，保留原断言。
- 独审覆盖旧费用两种错误形态、合法未启动零证据、原生 attempt 错配、结果及费用分离、实际回告和受控真实链。总控代码核对工作树 SHA-256 前缀：`local_host.py` `c1907cba`、`coordinator.py` `c13ce2d2`、`observations.py` `ad53b0ad`。实际 FF 为上述提交。

本轮验证指定 FF/CWP 组合与通用宿主。其他 owner 的生产接线、不同供应商费用的额外核对以及公司池正式运维继续沿[分工](dispatch.md)与各自 PWF，不能将本轮的隔离验证记作已全量上线。
