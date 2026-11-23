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

三个外发任务均已独审并入正式发布线、推送及接入同一个 Windows F4 恢复任务。下表记录各仓最终版本和剩余范围。

### 日常入口验收到哪一步

| 责任仓 | 11 月 21–23 日实测和后续 |
|---|---|
| 行业研究 | 主线及远端代码 `f1c4ff2`。独审分别拿掉三份必要资料，三次均退出 1，未产生空报告。采集、导出及能力查询均保留子进程 43，超过 120 KB 的脱敏诊断可读到末行。三个已安装入口六个工具逐字节一致，更新后已从实际技能入口再跑原案例。 |
| Revenue Forecast | 远端 main `f90d28ad`，独审代码与宿主 `f7c7c45f`。三个技能入口均已实测。RF 的公开任务只发生一次来源尝试，后两阶段未执行，费用保持未知。三种不同长度的 Windows 根均由新进程两次查回同一原始拒绝。 |
| Revenue Forecast Audit | 本地主线 `1cf4a87a`，两处安装入口已同步。本仓未配置远端。真实子进程的退出码、原始费用状态、四种带 BOM 的长错误流以及中断产生的半行均已复验。 |
| StockQA | 已验代码 `e96b2fa5`，正式分支已推 `e95befd`。通过已发布代码对既有真实账本只读查回 33 个工作项，零请求、零预留。旧子进程测试丢失隔离根的问题已修，精确回收了 8 份测试观察。日常主目录仍有并行源码改动。 |
| IQS | 远端 master 及专用运行目录 `aa847acf`，独审代码 `86385f3`。回放七个原入口与五个对照。普通调用自动生成和显式提供的编号均可传给 StockQA，兼容旧日志冷读和 446 字符 Windows 收件根。 |
| StockWiki | 独审代码 `d819ffa`，本地主线记录 `153e87e`。八个原场景及追加的 370 字符目录通过，同一拒绝两次冷读一致。73 条旧记录已查，其中 61 条是两个找不到输入原路径的批次，只有两条能证实有人为调试，当前留证待核。该仓没有 Git 远端。 |
| Dashboard | 已独审代码 `0aa04c40`、主线验收 `97b0bbc9`。五个 HTTP 失败可按关联号冷读。两个真实 HTTP 路由各启动一次离线子进程，长错误流仍保留真实退出码 43、原因和脱敏后的末行；同时复验了超时和响应超限。 |
| company-wiki 与调度 | 源码 `e27c67a39`。独审使用真实宿主进程核对发生标识、错绑、中断、完整投递确认与未知费用。23 项推送快测通过。Windows 同一任务已订阅 10 个已验模块。[总控 CI](https://github.com/zhengcb81/company-wiki/actions/runs/45277769660) |
| filing-fetch | 已部署代码 `32cf33e6`，远端主线 `a882295` 的 CI 成功。独审用三市场确认原收件箱坏后可补投两个原失败，原有六次调用保持六次。新浪部分失败保留具体表、原因及原用量。四个实际入口合计 12 个故障可冷读，三个物理订阅目录已登记。 |
| earnings-transcripts | 远端 main `f2512176`。原卡 128 项和真实强停验收有效。本轮双目录查证 35 项通过。ROOT 用历史 sidecar 和新收件样例分别两次冷读，费用分别为未知和不适用。正式宿主已使用双目录，定向恢复退出 0。该仓目前没有远端 CI；批量采集内部逐公司、逐期次反馈仍列在本仓后续项。 |
| StockInfoDLSimple | 已推送源码 `8d098c29`。90 项集中、7 项独立制品、19 项 Node C、17 项 G4 路由与传输回归通过。实际独立制品默认写收件箱；两次冷读找回同一权限错误和未知费用，原始记录未变。多个进程写失败日志时均保留。仓库无远端 CI。 |
| MeetingConverter | 主线 `master@e0ab1252`，独审源码 `0e3c4a39`，本仓 345 项通过，[同版 CI 成功](https://github.com/zhengcb81/MeetingConverter/actions/runs/45277560721)。正式入口和备用收件箱写出两个完整包，实际总控首次确认 21 条，第二轮为零。两笔原作业的费用继续为未知，恢复零转录调用，原始文件字节一致。 |

11 月 23 日用现有登记 bundle 和原 SQLite 的隔离快照做 IQS 与 StockQA 组合验收。填写和省略关联号的两轮均读回 33 项，模型请求和费用预留为零。两个同为 409 的拒绝分别冷读出 `ValueError` 和 `JSONDecodeError`，两仓保留同一 run/attempt，原快照字节相同。历史中微两题在发送前遗失的具体异常仍为未知。[复跑脚本](probes/iqs_stockqa.py)

### ROOT 的组合验收

1. 先完成每个 owner 的最小实际错误与合法对照，再验证无显式侧带路径的普通 CLI、服务、定时器或实际技能。用第一个进程保留的原生 run/attempt、执行次数和工作项作分母，从第二个进程逐项查询。各仓完整记录归本仓，跨仓只共享公开观察与诊断引用。
2. 总控兼容原监督启动目录及各仓独立运行的 outbox。故障断点覆盖首写、原子提交、投递确认及进程强停。中断后对同一业务尝试只读核对，不能因补日志重启付费请求。费用未知、正常空结果、预期拒绝、可用降级、实际业务失败分别核对。
3. 用 IQS 和 StockQA 做发现方至责任方再回告的联合复验。历史两题的缺失原因永久保留未知，新的合成故障必须能区分两个不同底层原因。独审按最后一次实际发布版本复验；每仓记录查询、修复、部署和验收的各自状态，再更新总表。
