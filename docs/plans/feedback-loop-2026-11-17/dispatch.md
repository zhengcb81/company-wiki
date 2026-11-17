# 施工分工与模块入口

总控 PWF 为[实施路线](task_plan.md)。下面的工作目录从同一个 `Projects/` 起算。每个 harness 只写自己一行的仓库，启动时从本仓施工卡和当前 HEAD 接续。交接时给 owner、分支、实际提交、测试命令及结果、独审及修复覆盖的版本、临时数据清理、脱敏观察和消费侧待验范围。ROOT 在公开接口做组合。直接交给三个 harness 的卡已各自发布。

| 可立即分发 | 工作目录 | 独立施工卡 | 首次发布的计划版本 |
|---|---|---|---|
| FB-ET | `earnings-transcripts/earnings-transcripts` | [电话会原语言采集](../../../../earnings-transcripts/earnings-transcripts/docs/plans/feedback-loop-2026-11-17/FB-ET.md) | `main@6883623` |
| FB-SID | `StockInfoDLSimple/v2-clean-rewrite` | [公告候选与暂存](../../../../StockInfoDLSimple/v2-clean-rewrite/docs/plans/feedback-loop-2026-11-17/FB-SID.md) | `v2-clean-rewrite@16499a0` |
| FB-IR | `industry-research` | [研究输入和报告输出](../../../../industry-research/.planning/modularity-closeout-20261111/feedback-20261117.md) | `main@9b347fd` |

| 责任仓标识 | 接续责任 | 本仓 PWF |
|---|---|---|
| `company-wiki` | ROOT，证据完整性、P1 选材与恢复，另负责编排组合 | [CWP 试点](company-wiki.md) |
| `filing-fetch` | ROOT 与 FF owner，原生持久 job、未知用量与只读对账 | [FB-FF](../../../../filing-fetch/docs/plans/feedback-loop-2026-11-17/FB-FF.md) |
| `revenue-forecast` | ROOT 与 RF owner，消费与原版本复验 | [RF 计划](../../../../revenue-forecast/docs/plans/mb11-rf-2026-11-11/feedback-20261117.md) |
| `revenue-forecast-audit` | ROOT，原四审发现定位、宿主及公司池边界 | [Audit 计划](../../../../revenue-forecast-audit/docs/plans/company-pool-cycle-2026-10-09/feedback-20261117.md) |
| `earnings-transcripts`, `stockinfo-dl-simple`, `industry-research` | 三张可发卡各有唯一作者 | 见上表 |
| `stockwiki` | 现有研究线，研究主体和来源关联 | [StockWiki 计划](../../../../StockWiki/.planning/modularity-closeout-20261111/feedback-20261117.md) |
| `invest-quick-scan` | 现有 IQS 线，尺度与筛选投影 | [IQS 计划](../../../../invest-quick-scan/docs/implementation/parallel-lanes/packages/2026-11-11-modularity-closeout/feedback-20261117.md) |
| `investment-dashboard` | 现有 Dashboard 线，公开 DTO 到 UI 的实际显示 | [Dashboard 计划](../../../../investment-dashboard/.planning/unified-dashboard-2026-10-26/feedback-20261117.md) |
| `stockqa` | 原 QA 活动项目接续，原分支有源码施工，主线文档已可用 | [StockQA 主线计划](https://github.com/zhengcb81/StockQAbyLLM/blob/21d3c99d07888003cd69e26fb4c5e6603f7c15e8/.planning/modularity-closeout-20261111/feedback-20261117.md) |
| `meeting-converter` | 已有本仓入口，留待转录节点 | [MeetingConverter 计划](../../../../MeetingConverter/docs/plans/feedback-20261117.md) |

Dayu 是纯外部 provider，其边界的运行指针由 CWP 适配器负责。公司池启停、真实计费与预算在各自唯一 owner 执行。文件链接用于同一 Projects 下的工作区交接；独立机器从同名仓的对应计划入口启动。
