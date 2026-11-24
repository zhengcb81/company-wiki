# S2 分仓接续验收

先沿公开业务入口复现一个真实缺口。失败后用新进程按原发生查回。检查正常对照、脱敏、原终态和费用语义，并在最终候选独审。状态以表中实际提交、远端或本地主线为准。

| 模块 | 本轮范围 | 状态 |
|---|---|---|
| CWP | AUTO 已确认的摘要待激活。把首次激活失败关联原 effect 和尝试。正常锁等待作为预期观察，存储故障保留因果链。 | `master@6843655cd` 已推送。定向 124 通过、1 跳过。三条独立复验通过，推送快测 23 通过。[远端 CI](https://github.com/zhengcb81/company-wiki/actions/runs/45512714220) |
| FF | Windows 定时子进程已退出。宿主从错误流只投影已观察的退出事实、可识别的类型和 F4 引用。 | `main@1adea742` 已推送。11 项定向、ROOT 三条独立复验、推送检查与远端 CI 通过。[本仓记录](../../../../filing-fetch/docs/plans/feedback-loop-2026-11-17/S2-FF-windows-logging.md) · [远端 CI](https://github.com/zhengcb81/filing-fetch/actions/runs/45512537138) |
| SID | 普通运行的旋转文件日志不能启动。日志降级可从 F4 查回，原下载动作及业务状态保持。 | `v2-clean-rewrite@ab50c8f5` 已推送。77 项定向、21 项独立复验通过。[本仓记录](../../../../StockInfoDLSimple/v2-clean-rewrite/docs/plans/feedback-loop-2026-11-17/f4-runtime.md) |
| RF | 上游采集子进程非零或返回不可解析输出。原 RF 机器收据与 F4 诊断各走已有接口。 | `main@1b471df4` 已推送。90 项定向、两条独立真实入口、12 项推送快测及远端 CI 通过。由正式基线隔离快进，原主工区及宿主检出保留。[远端 CI](https://github.com/zhengcb81/revenue-forecast/actions/runs/45512784316) |
| IR、MC | 独立施工，分别处理 DeepSeek、MiMo。 | 用户已转交，按交付再验收。 |
| ET、Audit | 见[首站和分仓验收](s2-pilot-20261124.md)。 | 本轮已验收。 |
| StockWiki | 本仓模型用量账本不可写。 | 确认与当前 Dashboard/IQS 写入分离后，已分仓实施。 |
| StockQA | 已付原响应的单题解码失败只能看到部分恢复。 | 已在正式 owner 分支隔离源改动和旧根计划，准备真实冷恢复复验。 |
| IQS | HTTP/后台异常与旧版 F4。 | 活动的 cross-ID 返回支线同时改 19 个生产文件，涉及 F4、作业、HTTP 和恢复。沿原分支接续，等待实际边界分离。 |
| Dashboard | 前端丢失后端相关号，候选写域在共享 M0。 | 当前挨个交接 D00 模块且 M0 PWF 有在途变更。只核对候选，不另开重复 M0 写入。 |

总控任务见 [S2 执行顺序](s2-unified-logging-plan.md)。在途目录及根计划保持原状。
