# S2 分仓接续验收

先沿公开业务入口复现一个真实缺口。失败后用新进程按原发生查回。检查正常对照、脱敏、原终态和费用语义，并在最终候选独审。状态以表中实际提交、远端或本地主线为准。

| 模块 | 本轮范围 | 状态 |
|---|---|---|
| CWP | AUTO 已确认的摘要待激活。把首次激活失败关联原 effect 和尝试。正常锁等待作为预期观察，存储故障保留因果链。 | `master@6843655cd` 已推送。定向 124 通过、1 跳过。三条独立复验、推送快测 23 项及远端 CI 通过。[远端 CI](https://github.com/zhengcb81/company-wiki/actions/runs/45512714220) |
| FF | Windows 定时子进程已退出。宿主从错误流只投影已观察的退出事实、可识别的类型和 F4 引用。 | `main@1adea742` 已推送。11 项定向、ROOT 三条独立复验、推送检查与远端 CI 通过。[本仓记录](../../../../filing-fetch/docs/plans/feedback-loop-2026-11-17/S2-FF-windows-logging.md) · [远端 CI](https://github.com/zhengcb81/filing-fetch/actions/runs/45512537138) |
| SID | 普通运行的旋转文件日志不能启动。日志降级可从 F4 查回，原下载动作及业务状态保持。 | `v2-clean-rewrite@ab50c8f5` 已推送。77 项定向、21 项独立复验通过。[本仓记录](../../../../StockInfoDLSimple/v2-clean-rewrite/docs/plans/feedback-loop-2026-11-17/f4-runtime.md) |
| RF | 上游采集子进程非零或返回不可解析输出。原 RF 机器收据与 F4 诊断各走已有接口。 | `main@1b471df4` 已推送。90 项定向、两条独立真实入口、12 项推送快测及远端 CI 通过。由正式基线隔离快进，原主工区及宿主检出保留。[远端 CI](https://github.com/zhengcb81/revenue-forecast/actions/runs/45512784316) |
| IR、MC | 独立施工，分别处理 DeepSeek、MiMo。 | 用户已转交，按交付再验收。 |
| ET、Audit | 见[首站和分仓验收](s2-pilot-20261124.md)。 | 本轮已验收。 |
| StockWiki | 模型成功但本仓用量账本不可写。保留原业务结果，冷读只诊断子步骤，费用按原事实保持未知。 | 本地 `master@665f6a85`，39 项定向、两条独审通过。无 Git 远端。[本仓记录](../../../../StockWiki/.planning/modularity-closeout-20261111/F4-SW.md) |
| StockQA | 已付原响应的单题解码失败可查回原成员，局部诊断和外层终态分别记录。 | `codex/qa-content-filter-resolution-01@95fdab89` 已推送。三条最终独审和原提交钩子通过。该维护分支不触发现有远端 CI。两次冷读未重发、未改变原付费账本。[本仓记录](../../../../StockQAbyLLM/.planning/modularity-closeout-20261111/S2-STOCKQA-recovery.md) |
| IQS | provider HTTP 非 JSON、超时、连接错误的安全诊断。同一尝试、同一原因归并，异类分别记录。 | `master@fb3fcbe7` 已推送。36 项定向、7 项独审通过。由远端合并基线 `05f95a2` 隔离快进。该提交无远端 CI。D00 的原 HTTP、作业、F4 检出与本地主工区保留。 |
| Dashboard | M0 共享前端保留相关号，现有 owner 提供只读 F4 冷查。 | `main@a3523e8` 独审已推，原 M0/M3/M6 在途文件保留。 [最后三区验收](s2-closeout-20261125.md) |

11 月 25 日核对 IR 和 MC 工作区均有本卡源码变更，等最终正式交付。本轮 RF 和 IQS 从实际远端基线隔离发布，安装版本与原本地工作区分开记录。总控任务见 [S2 执行顺序](s2-unified-logging-plan.md)。
