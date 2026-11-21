# 日常失败接入 F4 的模块分工

24 条发现使用原发生清单中的 owner 和 step 对账。每个责任仓的 F4 子计划保存本仓的原因、实施细节、先复现的普通入口和验收条件。下表记录分工与入口。用户已将三张外包卡分别发给独立 harness。剩余九个模块及跨仓组合由 ROOT 实施。各仓保留自己的运行状态及发布线。[原审计](failure-coverage-20261121.md) · [原观察](issues/failure-coverage-20261121.jsonl) · [中微原故障补证](issues/iqs-presend-20261121.md)

| 负责方式 | 模块和本仓施工入口 | 该仓原发现 |
|---|---|---|
| 独立 harness | [earnings-transcripts](../../../../earnings-transcripts/earnings-transcripts/docs/plans/feedback-loop-2026-11-17/F4-ET-FAILURES.md) | txt-and-cli、retrieval-worker |
| 独立 harness | [StockInfoDLSimple](../../../../StockInfoDLSimple/v2-clean-rewrite/docs/plans/feedback-loop-2026-11-17/F4-SID-FAILURES.md) | failure-log-flush、ordinary-download |
| 独立 harness | [MeetingConverter](../../../../MeetingConverter/docs/plans/f2-mc-output/F4-MC-FAILURES.md) | initialization、fallback |
| ROOT | [StockQA](../../../../StockQAbyLLM/.planning/modularity-closeout-20261111/F4-STOCKQA.md) | pre-send、ordinary-cli，另有诊断构造失败的候选回归 |
| ROOT | [IQS](../../../../invest-quick-scan/docs/implementation/parallel-lanes/packages/2026-11-11-modularity-closeout/feedback-20261117.md) | answer-execution、background-job，另有 8 个旁路写失败与子进程收尾红测 |
| ROOT | [company-wiki 与调度](company-wiki.md) | ordinary-sources、generation-accounting、inbox-outage |
| ROOT | [filing-fetch](../../../../filing-fetch/docs/plans/feedback-loop-2026-11-17/FB-FF.md) | public-start、failed-job |
| ROOT | [revenue-forecast](../../../../revenue-forecast/docs/plans/mb11-rf-2026-11-11/feedback-20261117.md) | ordinary-skill、source-stage |
| ROOT | [revenue-forecast-audit](../../../../revenue-forecast-audit/docs/plans/company-pool-cycle-2026-10-09/F4-AUDIT.md) | capture-delegation、diagnostic-retention |
| ROOT | [StockWiki](../../../../StockWiki/.planning/modularity-closeout-20261111/F4-SW.md) | ordinary-refusals、identity-availability，另核对权限刷新和主体登记的意外错误 |
| ROOT | [Dashboard](../../../../investment-dashboard/.planning/unified-dashboard-2026-10-26/modules/m6-quickscan/feedback-runtime-2026-11-20.md) | http-request |
| ROOT | [industry-research](../../../../industry-research/.planning/modularity-closeout-20261111/feedback-20261117.md) | installed-publisher、collection |

三个外部模块正在各自 harness 施工。卡的发布版本分别为 ET `0bfa07b9`、SID `95533795`、MC `101124f5`。其代码改造由各自 harness 实施，ROOT 按收到的正式交付逐仓验收。StockWiki 有并行项目，RF 常用目录含独立历史进度；实施使用与基线相容的原发布线，提交只包含本模块变更。

### ROOT 的组合验收

1. 先完成每个 owner 的最小实际错误与合法对照，再验证无显式侧带路径的普通 CLI、服务、定时器或实际技能。用第一个进程保留的原生 run/attempt、执行次数和工作项作分母，从第二个进程逐项查询。各仓完整记录归本仓，跨仓只共享公开观察与诊断引用。
2. 总控兼容原监督启动目录及各仓独立运行的 outbox。故障断点覆盖首写、原子提交、投递确认及进程强停。中断后对同一业务尝试只读核对，不能因补日志重启付费请求。费用未知、正常空结果、预期拒绝、可用降级、实际业务失败分别核对。
3. 用 IQS 和 StockQA 做发现方至责任方再回告的联合复验。历史两题的缺失原因永久保留未知，新的合成故障必须能区分两个不同底层原因。独审按最后一次实际发布版本复验；每仓记录查询、修复、部署和验收的各自状态，再更新总表。
