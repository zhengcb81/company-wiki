# 进展

## 2026-11-21

- 建立独立 PWF。主线循环目标仍为暂停。
- 查实旧 worker 的本机状态和公开入口退役。独立 agent 核对了当前共享批次、原文只读接口和 F4 恢复证据。确认 FF 与 ET 的确切协议以及 PC 触发与作业恢复的边界。
- 只读核对各仓主线与在途路径。确认 FF 的提交锁及死写者恢复在现用代码中。Dashboard 的现有改动集中在计划和交接；新卡使用独立开发和复验范围。
- 隔离基线测试完成后清理临时根。FF 跨进程 3 过。CWP MiMo 回环恢复 1 过，现有混合 PDF/TXT 语言测试 1 失败。单用例重跑再次失败，白名单诊断定位到一份原件 `PARSER_INCOMPLETE`，其余三份输出完成。该用例进入 CWP 卡的首项 TDD。网络采集和真正模型请求为 0。
- P0 交付 [总计划](task_plan.md)、[公开接口与验收夹具](interfaces.md)、[CWP 施工卡](harness_lanes/cwp-incremental-reading.md) 和 [Dashboard 施工卡](harness_lanes/dashboard-refresh-controls.md)。自动更新的产品实现、正式验证与启用仍在 P1–P3。
- 验证 Windows 可按独立 PLAN_ID 解析该计划。七份文档的本地引用及 JSON 夹具示例已核对。
