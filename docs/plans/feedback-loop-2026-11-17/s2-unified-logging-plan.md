# S2 统一日志与故障复原计划

**当前状态：收尾中。** CWP、ET、FF、SID、RF、IQS、StockQA 和 Dashboard 受验节点已推送。Audit 和 StockWiki 已验收并提交本地主线。IR、MC 等正式交付。历史核查见[首站台账](s2-pilot-20261124.md)，发布证据见[分仓接续](s2-owner-continuation-20261124.md)与[最后三区验收](s2-closeout-20261125.md)，S1 发布线见[分仓发布台账](s1-p0-blackhole-plan.md)。

## 共同接口与验收方式

覆盖 company-wiki、filing-fetch、revenue-forecast、revenue-forecast-audit、StockWiki、earnings-transcripts、StockInfoDLSimple、invest-quick-scan、investment-dashboard、StockQAbyLLM、industry-research 和 MeetingConverter。每仓在自身入口和日志写入层实现，沿用本仓已有轮转和故障数据。共享的是字段语义、脱敏反例和公开 F4 观察接口。

- 本地日志复用运行、尝试、操作和可安全引用的逻辑输入。保留已知的版本信息。包版本和精确发布提交分别记录，旧日志缺项仍可冷读。非预期故障记录可复核的异常类型、因果链和源位置。明确的输入拒绝用离线用例验证简明 CLI/HTTP 契约及本地冷查。
- 日志写入前处理凭据、请求原文和第三方错误流。后台进程遵守现有静默启动和可恢复业务状态。日志写失败作为诊断，业务原结果保留。
- F4 沿用既有观察标识、状态和 owner 证据引用。同一发生记录跨部署重投时，已有公共标识及用于幂等的 payload 保持兼容。诊断正文由 owner 写一处，Dashboard 后续沿相关号定位。
- 用真实入口的故障、合法反例和新进程冷查验收。已有边界测试继续使用。是否加 CI 行为用例按实际漏记和回归决定，不按 `from None`、`exc_info` 或 `DEVNULL` 的语法用法统一拒绝。

## 施工顺序

| 顺序 | 负责人 | 验收 |
|---|---|---|
| 历史日志只读核查 | ROOT 并发只读复核 CWP、ET | 只登记文件、风险类别和范围。缺席、归属不明及无法判定的部分显式列出。 |
| CWP 首站 | ROOT | 用真实公开原文读取命令复现配置故障，检查无原文落盘，同一 F4 实例冷读两次仍只有一个观察动作。任何诊断变化均保持正常读取和原错误契约。 |
| ET、Audit | 各仓独立 agent，ROOT 统筹 | 已独审。ET 记录引导依赖及清理失败，机器收据保持兼容。Audit 记录反馈投递全失，能冷读原角色故障。发布细节见[复验台账](s2-pilot-20261124.md)。 |
| [IR](owner-cards/S2-IR-DEEPSEEK-DIAGNOSTICS.md)、[MC](owner-cards/S2-MC-MIMO-DIAGNOSTICS.md) | 外部 harness | 已分发。每仓一种真实故障、合法反例、脱敏落盘、F4 冷读及最终版本独审。 |
| CWP、FF、SID、RF | ROOT 与三个分仓 agent | 原摘要激活、定时子进程失败、文件日志启动、采集子进程机器收据四个节点独审并推送。 |
| StockWiki、StockQA、IQS | 分仓 agent | 本仓账本、已付恢复和 provider 错误三个节点已独审。StockWiki 本地提交，StockQA 和 IQS 已推送。 |
| Dashboard | M0 隔离实施，ROOT 串接 | 独审并推送。共享请求与错误视图保留关联号，原 owner CLI 只读冷查。 |

试点记录与历史抽核见[复验台账](s2-pilot-20261124.md)。M4/S3 和 S4 分开管理。问题出处见[12 仓审计](../module-boundaries-2026-11-11/review/full-12-module-architecture-logging-audit-20261124.md)，执行入口为[总控 PWF](task_plan.md)。
