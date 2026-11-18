# F4 RF 与 Audit 宿主验收 · 2026-11-18

## 原问题和修复

RF 以复用已有财报的结果推断整个来源步骤无外部调用。FF 的 `latest_as_of + reuse_only` 仍会在限额内发现元数据。旧 RF 在该调用后中断时允许重跑 source，成功复用时也可能把未知费用报告成零。两条 RED 分别重现了错误的 `resume` 和错误的 `known`。

RF 源码修复为 `24e8f978f54194a2d10905a61f13a1563d1ce8e4`。调用前区分纯本地与可能访问供应商，调用后另读原生用量证据。旧记录缺充分证据保留未知。已证明的本地读取仍可安全续跑，成功准备的来源仍交给后续计算。RF 公开回告可独立读回。Audit 原生 finding 绑定 run、审查轮次、角色、编号及报告 SHA。复验在 Audit 本仓 capture 内运行指定的只读检查。ROOT 只通过配置好的 owner 命令核对原作业。

## 实际宿主与恢复

基线 RF 为 `51b26dcf0b168964b34366eff66fe6f1aca1aaea`。使用两个隔离 RF 作业各发一次环回元数据请求，来源子进程退出后、冻结来源结果前强制终止 RF。另在 Audit capture 已记录开始后强制终止。审查将旧 RF 的公开 `allowed_actions` 偏差登记为原生 finding。

真实 Codex 启动分诊会话后强制终止总控。重启取回同一个会话 `01a1f081-a33a-7681-86d6-de34ac621478`，由宿主自动调度隔离 RF owner 采用已独审的修复版本。Audit 校验版本并调用 RF `get-status` 复验旧作业 `rfjob-20261118-66de181b65e4/source-1`。它始终是同一作业、一次尝试。修复前为 `resume, reconcile`，修复后仅有 `reconcile`。随后 RF `get-report` 读回 Audit 的版本化复验收据。修复、复验和回告各执行一次。

另一笔 RF 作业的自动对账找回原 `source-1`。Audit 找回原 capture，原状态为 `unconfirmed`。原账未知继续未知。恢复阶段新增供应商请求、原件下载、业务模型调用和 Codex 分诊均为 0。首轮真实分诊用量为 20,811 输入 tokens（缓存 13,056）及 96 输出 tokens，金额由宿主账单记载。提示内只有合成工程信息。两轮临时目录均清理。[真实宿主收据](f4-rf-audit-receipt.json) · [正式请求契约收据](f4-rf-audit-contract-receipt.json)

真实宿主使用受控环回元数据夹具。独审发现首轮夹具遗漏 FF 的正式请求限额，随后用实际 FF `d5fa32c` 请求校验器及字节、时间、费用限额完整复跑离线链。两份收据分别证明真实分诊中断恢复及符合接口的原作业恢复。该范围覆盖选定问题与已审修复版本。完整公司流程和其他待配置的 owner 生产接入按各自 PWF。

## 重跑和部署

在正常宿主的总控仓根目录将其加入 `PYTHONPATH`，运行 `python -B -X utf8 tests/integration/f4_rf_audit_host_probe.py --help`。传入三个隔离或已验证的 RF、FF、Audit 仓路径及匹配的 RF 修复前后 Git 版本。默认分诊使用离线夹具；显式 `--codex` 才另开一笔真实分诊。排查真实任务中断时，继续用原 `recover`、原 SQLite 和原 sidecar。

RF 定向作业测试、Audit 本仓测试和 CWP 宿主/FF 强杀测试见[进度](progress.md)。独立审查核对 RF 作用域、旧记录、回执与作业身份、Audit 原报告 SHA、真实会话及环回计数。发现的缺项已在最终代码及契约复跑补齐。Audit 实测源码与 `9a38021c15249766b7604f6403d7b7b2df4704ea` 一致，SHA-256 前缀为 `feedback_owner.py a1e738fb749a1ac3`、`audit_run.py 70e412130b372742`。ROOT 为 `local_host.py 86d7bfd064283766`、`coordinator.py e5e30e916de2e068`。实际命令接线见[实施细则](host-integration.md)。
