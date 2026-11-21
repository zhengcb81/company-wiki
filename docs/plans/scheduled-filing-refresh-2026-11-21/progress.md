# 进展

## 2026-11-21

- 建立独立 PWF。主线循环目标仍为暂停。
- 查实旧 worker 的本机状态和公开入口退役。独立 agent 核对了当前共享批次、原文只读接口和 F4 恢复证据。确认 FF 与 ET 的确切协议以及 PC 触发与作业恢复的边界。
- 只读核对各仓主线与在途路径。确认 FF 的提交锁及死写者恢复在现用代码中。Dashboard 的现有改动集中在计划和交接；新卡使用独立开发和复验范围。
- 隔离基线测试完成后清理临时根。FF 跨进程 3 过。CWP MiMo 回环恢复 1 过，现有混合 PDF/TXT 语言测试 1 失败。单用例重跑再次失败，白名单诊断定位到一份原件 `PARSER_INCOMPLETE`，其余三份输出完成。该用例进入 CWP 卡的首项 TDD。网络采集和真正模型请求为 0。
- P0 交付 [总计划](task_plan.md)、[公开接口与验收夹具](interfaces.md)、[CWP 施工卡](harness_lanes/cwp-incremental-reading.md) 和 [Dashboard 施工卡](harness_lanes/dashboard-refresh-controls.md)。自动更新的产品实现、正式验证与启用仍在 P1–P3。
- 验证 Windows 可按独立 PLAN_ID 解析该计划。七份文档的本地引用及 JSON 夹具示例已核对。

### P1 · FF 接收

- 两张外包卡由用户发出。FF 从 `fcacf2e` 的短路径隔离工作区实施，`1ab0a94` 已快进并推送到 filing-fetch `main`。状态、配置和历史通过统一 CLI 读取。新增日周槽位、动态/定版名单、增量时间水位、独立精确期电话会、原 job 持久续做和有限阅读接线。[FF 部署说明](../../../../filing-fetch/docs/scheduled-refresh.md)
- 独审复现了旧付费批次被混入新批次、换范围仍可能执行旧待办、IQS 原生 JSON 外层、局部覆盖被错误推进、原生启动和 Windows 共享写入边界。已按作用范围、原请求与原批次修复。窗口中的同槽启动只接纳一次，关闭和接纳共用状态锁。跨范围只读查原批次，已证明未启动的瞬时失败才可使用已有作业的安全 retry。
- 共享 FF 持久写入使用 Windows 长路径和短临时文件。确认遇到有界共享冲突时只重发同一已同步字节的原子替换。独审发现的未签名 PowerShell 启动依赖已改为直接 Python 入口，实际运行了隐藏 launcher 的隔离退出验证。卸载收据仅在确认并实际删除原任务后写入。
- 最终 FF 聚焦回归 **101 passed，8 subtests passed**。包含三市场 pin 的公开 CLI 组合、重复触发、实际 `pythonw.exe` 隔离启动、文件共享冲突、停用竞争、换名单、相同来源恢复和电话会未知费用的只读对账。较宽回归 **132 passed，10 条真实环境 opt-in 跳过，8 subtests passed**。Ruff、mypy、提交钩子及推送 smoke 11 项通过。各隔离目录已恢复，真实新下载与真实付费调用均为 0。
- 阶段仍为 P1。CWP 和 Dashboard 正式交付后，验第 5 节的实际 owner 组合，并从原 SourceRef 查回内容、核对冻结名单和重复用量。正式数据目录、Dashboard 监听进程与 Windows Task Scheduler 未安装或切换本功能。
