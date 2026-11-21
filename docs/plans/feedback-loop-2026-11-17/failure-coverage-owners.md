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

### 日常入口验收到哪一步

| 责任仓 | 11 月 21 日实测和后续 |
|---|---|
| 行业研究 | 主线及远端代码 `f1c4ff2`。独审分别拿掉三份必要资料，三次均退出 1，未产生空报告。采集、导出及能力查询均保留子进程 43，超过 120 KB 的脱敏诊断可读到末行。三个已安装入口六个工具逐字节一致，更新后已从实际技能入口再跑原案例。 |
| Revenue Forecast | 远端 main `f90d28ad`，独审代码与宿主 `f7c7c45f`。三个技能入口均已实测。RF 的公开任务只发生一次来源尝试，后两阶段未执行，费用保持未知。三种不同长度的 Windows 根均由新进程两次查回同一原始拒绝。 |
| Revenue Forecast Audit | 本地主线 `1cf4a87a`，两处安装入口已同步。本仓未配置远端。真实子进程的退出码、原始费用状态、四种带 BOM 的长错误流以及中断产生的半行均已复验。 |
| StockQA | 已验代码 `e96b2fa5`，正式分支的本仓验收记录 `337ebcd`。通过已发布代码对既有真实生产账本只读查回 33 个工作项，零请求、零预留，账本字节相同。日常主目录另有并行源码改动，两者的运行位置已分别记账。 |
| IQS | 普通入口及长日志修复 `a0051c55` 已并入远端主线和专用运行目录。七个原场景及独审的长日志末行、密码遮蔽已通过。本仓在补齐 `--runs-root` 对旧位置诊断的冷读。 |
| StockWiki | 本地主线 `6e3974ac`，独审代码 `d819ffa`。八个原场景及追加的 370 字符目录通过，同一拒绝两次冷读一致。同类异常的两个具体原因在本地可读，跨仓只送引用。该仓没有 Git 远端。 |
| Dashboard | 已独审代码 `0aa04c40`、主线验收 `97b0bbc9`。五个 HTTP 失败可按关联号冷读。两个真实 HTTP 路由各启动一次离线子进程，长错误流仍保留真实退出码 43、原因和脱敏后的末行；同时复验了超时和响应超限。 |
| company-wiki 与调度 | 源文件、单篇处理、worker、摘要执行与费用已有普通入口留证。独审追加了损坏的可选异常属性、不同 attempt 共用一个文件、marker 错绑、长路径和写完 JSONL 即强停等反例。总控按真实输入复验，另验无人值守的普通入口投递。 |
| filing-fetch | 原发布线已登记两类漏报。本仓修复普通 CLI、单件失败的作业及定时 slot，复验需同时核对业务错误和独立费用状态。 |

组合验收的最后一步使用 IQS 与 StockQA 的公开进程确认同一 run/attempt 的调用关系。先保留正在使用的既有 bundle 和原工作账本，再用隔离输入制造可定位的不同失败。历史中微两题在发送前遗失的具体异常继续标为未知。

### ROOT 的组合验收

1. 先完成每个 owner 的最小实际错误与合法对照，再验证无显式侧带路径的普通 CLI、服务、定时器或实际技能。用第一个进程保留的原生 run/attempt、执行次数和工作项作分母，从第二个进程逐项查询。各仓完整记录归本仓，跨仓只共享公开观察与诊断引用。
2. 总控兼容原监督启动目录及各仓独立运行的 outbox。故障断点覆盖首写、原子提交、投递确认及进程强停。中断后对同一业务尝试只读核对，不能因补日志重启付费请求。费用未知、正常空结果、预期拒绝、可用降级、实际业务失败分别核对。
3. 用 IQS 和 StockQA 做发现方至责任方再回告的联合复验。历史两题的缺失原因永久保留未知，新的合成故障必须能区分两个不同底层原因。独审按最后一次实际发布版本复验；每仓记录查询、修复、部署和验收的各自状态，再更新总表。
