# 施工分工与模块入口

总控 PWF 为[实施路线](task_plan.md)，并行安排见 [F2 路线图](f2-roadmap.md)。下面的工作目录从同一个 `Projects/` 起算。每个 harness 只写自己一行的仓库，启动时从本仓施工卡和当前 HEAD 接续。交接时给 owner、分支、实际提交、测试命令及结果、独审及修复覆盖的版本、临时数据清理、脱敏观察和消费侧待验范围。ROOT 在公开接口做组合。首批三张已验收并分别发布到本仓主线，详见[首批签收](f2-owner-acceptance.md)。

| 已签收 | 工作目录 | 原独立施工卡 | 首次发布的计划版本 |
|---|---|---|---|
| FB-ET | `earnings-transcripts/earnings-transcripts` | [电话会原语言采集](../../../../earnings-transcripts/earnings-transcripts/docs/plans/feedback-loop-2026-11-17/FB-ET.md) | `main@6883623` |
| FB-SID | `StockInfoDLSimple/v2-clean-rewrite` | [公告候选与暂存](../../../../StockInfoDLSimple/v2-clean-rewrite/docs/plans/feedback-loop-2026-11-17/FB-SID.md) | `v2-clean-rewrite@16499a0` |
| FB-IR | `industry-research` | [研究输入和报告输出](../../../../industry-research/.planning/modularity-closeout-20261111/feedback-20261117.md) | `main@9b347fd` |

## FF 和 MC 隔离施工交付

| 已验收 | 本仓发布日期与版本 | 正式交接与组合 |
|---|---|---|
| F2-FF-SHORT | 2026-11-19，FF `main@95769c0` | [作者交接](../../../../filing-fetch/docs/plans/f2-ff-short/handoff.md) · [ROOT 验收](f4-acceptance.md#6-f2-ff-短请求进入总控) |
| F2-MC-OUTPUT | 2026-11-19，MC `master@1d3fd6c` | [本仓进度](../../../../MeetingConverter/docs/plans/f2-mc-output/progress.md) · [ROOT 验收](f4-acceptance.md#7-f2-mc-转录发布反馈进入总控) |

## 现有 harness 接续卡

用户已将以下四张卡分别交给对应的现有 harness。各仓由原工作线统筹，可先核对公开入口和离线夹具。写范围重叠的部分在同一 harness 排队，正式交接后由 ROOT 逐张做组合验收。

| 接续卡 | 工作目录（相对 Projects） | 排队位置 |
|---|---|---|
| [F2-SW-FEEDBACK](owner-cards/F2-SW-FEEDBACK.md) | `StockWiki` | 身份桥、发布和来源关联与原研究线共用的改动接在对应项目后 |
| [F2-IQS-FEEDBACK](owner-cards/F2-IQS-FEEDBACK.md) | `invest-quick-scan` | MANIFEST-DELIVERY-01 先收口同入口的当前发布改动 |
| [F2-DASH-FEEDBACK](owner-cards/F2-DASH-FEEDBACK.md) | `investment-dashboard` | D00 在 M6 原线接续，M0 共享适配器由原 owner 维护 |
| [F2-STOCKQA-FEEDBACK](owner-cards/F2-STOCKQA-FEEDBACK.md) | `StockQAbyLLM` | 当前内容过滤恢复的检查器和同测试先完成 |

## Owner 入口

| 责任仓标识 | 接续责任 | 本仓 PWF |
|---|---|---|
| `company-wiki` | ROOT，证据完整性、P1 选材与恢复，另负责编排组合 | [CWP 试点](company-wiki.md) |
| `filing-fetch` | 原生持久 job、未知用量、只读对账及回告已在 F4 验收，短请求也已通过组合 | [FB-FF](../../../../filing-fetch/docs/plans/feedback-loop-2026-11-17/FB-FF.md) |
| `revenue-forecast` | 作业对账、版本化回告已在 F4 验收，业务采用按原计划 | [RF 计划](../../../../revenue-forecast/docs/plans/mb11-rf-2026-11-11/feedback-20261117.md) |
| `revenue-forecast-audit` | 原捕获查询和发现端复验已在 F4 验收，公司池按原入口 | [Audit 计划](../../../../revenue-forecast-audit/docs/plans/company-pool-cycle-2026-10-09/feedback-20261117.md) |
| `earnings-transcripts`, `stockinfo-dl-simple`, `industry-research` | 已接入专用观察；自动对账和回告交 F4 | [三卡验收](f2-owner-acceptance.md) |
| `stockwiki` | 现有研究线，研究主体和来源关联 | [StockWiki 计划](../../../../StockWiki/.planning/modularity-closeout-20261111/feedback-20261117.md) |
| `invest-quick-scan` | 现有 IQS 线，尺度与筛选投影 | [IQS 计划](../../../../invest-quick-scan/docs/implementation/parallel-lanes/packages/2026-11-11-modularity-closeout/feedback-20261117.md) |
| `investment-dashboard` | 现有 Dashboard 线，公开 DTO 到 UI 的实际显示 | [Dashboard 计划](../../../../investment-dashboard/.planning/unified-dashboard-2026-10-26/feedback-20261117.md) |
| `stockqa` | 原 QA 活动项目接续，原分支有源码施工，主线文档已可用 | [StockQA 主线计划](https://github.com/zhengcb81/StockQAbyLLM/blob/21d3c99d07888003cd69e26fb4c5e6603f7c15e8/.planning/modularity-closeout-20261111/feedback-20261117.md) |
| `meeting-converter` | 本机 F4 已接通。已证明的旧译文发布归属可自动修复清单、复验及持久回告，原作业与用量只读核对 | [MC 运行端口](../../../../MeetingConverter/docs/plans/f2-mc-output/runtime.md) |

Dayu 是纯外部 provider，其边界的运行指针由 CWP 适配器负责。公司池启停、真实计费与预算在各自唯一 owner 执行。文件链接用于同一 Projects 下的工作区交接；独立机器从同名仓的对应计划入口启动。
