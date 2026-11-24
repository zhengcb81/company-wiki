# S2 统一日志与故障复原计划

**当前状态：暂停。** 2026-11-24 已有设计稿和外部调度编号 `25bb30f8-3497-44e7-a8c4-a628480fba0b`。本仓仅记录暂停及设计，未把外部任务回执或工作区是否干净作为验收。最新 S1 实际发布线见[分仓发布台账](s1-p0-blackhole-plan.md)。

## 暂停前的范围

覆盖 company-wiki、filing-fetch、revenue-forecast、revenue-forecast-audit、StockWiki、earnings-transcripts、StockInfoDLSimple、invest-quick-scan、investment-dashboard、StockQAbyLLM、industry-research 和 MeetingConverter。每仓在自身入口和日志写入层实现，沿用本仓已有轮转和故障数据。共享的是字段语义、脱敏反例和公开 F4 观察接口。

- 本地日志关联运行、尝试、操作、源码版本与逻辑输入。非预期故障记录可复核的异常类型、因果链和源位置。明确的输入拒绝用离线用例验证简明 CLI/HTTP 契约及本地冷查。
- 日志写入前处理凭据、请求原文和第三方错误流。后台进程遵守现有静默启动和可恢复业务状态。日志写失败作为诊断，业务原结果保留。
- F4 只交换必要状态、发生标识和证据引用。Dashboard 后续用现有相关号连到所属模块。本地日志与 F4 不需要两份诊断正文。
- 用真实入口的故障、合法反例和新进程冷查验收。已有边界测试继续使用。是否加 CI 行为用例按实际漏记和回归决定，不按 `from None`、`exc_info` 或 `DEVNULL` 的语法用法统一拒绝。

## 与其他工作线的关系

当前 S1 补修限 CWP、ET 和 SID。M4/S3 仍是单独的架构审计计划，S4 暂无实施。详细问题出处见[12 仓审计](../module-boundaries-2026-11-11/review/full-12-module-architecture-logging-audit-20261124.md)，执行入口为[总控 PWF](task_plan.md)。
