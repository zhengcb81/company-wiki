# S1–S5 整改验收与发布

验收以旧独审发现的真实反例为基线。各仓通过公开入口和独占数据根验证原运行号、原失败、原产物和外部效果，保持代码归属和独立运行。每项故障修复由另一 agent 复验。

| 模块 | 本轮确认 | 提交与 CI |
|---|---|---|
| CWP／F4 宿主 | 作业开始、终态及诊断独立持久化。6 条 CWP 独审、14 条原现场回归、三条宿主进程环境和旧 sidecar 公开命令通过 | `4154161da` 已到远端与本地 `master`。Linux Unit 的旧 trace 绑定已修，33 项 Linux 与 45 项 Windows 通过。[远端 CI 通过](https://github.com/zhengcb81/company-wiki/actions/runs/45737866794) |
| filing-fetch | 原业务终态和补投分离，公开查回保持只读。独审 17 项，双出箱真实宿主五条原观察、一次业务、零重复 | `4bd76b39` 已推送 `main`，[远端 CI 通过](https://github.com/zhengcb81/filing-fetch/actions/runs/45736272026) |
| revenue-forecast | 迟到旧进程无法覆盖新结果，原运行与尝试绑定、归档只读。原单文件故障的两条反馈在 Windows 与 Linux 均完整保留，重复恢复无新增。原档、错号和失效文件的对照均独审通过 | `ac5e94a6` 已推送 `main`，提交钩子和 12 项本地推送测试通过。[Linux 与 Windows 远端 CI 均通过](https://github.com/zhengcb81/revenue-forecast/actions/runs/45740422855) · [最后一轮独审](reviews/rf-linux-independent-20261126.md) |
| earnings-transcripts | 启动失败确认零请求，已派发后中断保持原事实，原 owner 公开查询可恢复 | `672ed101` 已推送 `main`，[远端 CI 通过](https://github.com/zhengcb81/earnings-transcripts/actions/runs/45733257511) |
| StockInfoDLSimple | 翻页失败与末页分开，按原运行读取部分进度，正式端口独立 61 项通过 | `5c656050` 已推送 `v2-clean-rewrite`，[远端 CI 通过](https://github.com/zhengcb81/StockInfoDownloader/actions/runs/45731060432) |
| MeetingConverter | 503 保留响应和序号并关闭，200 正文中断零重发，原运行可在强停后查回 | `7b83fe6f` 已推送 `master`，[远端 CI 通过](https://github.com/zhengcb81/MeetingConverter/actions/runs/45734682480) |
| StockWiki | 身份只读接口、含 `#` 和 `%` 的路径及源资料运行链。独审 25 项通过 | `2ed18c51` 已提交本地 `master`。该仓未配置远端 |
| invest-quick-scan | HTTP POST 中断后用同作业和同尝试冷读，重提附着现有作业。独审 42 项通过 | `34d32a5e` 已推送 `master`，[远端 CI 通过](https://github.com/zhengcb81/invest-quick-scan/actions/runs/45734309620) |
| investment-dashboard | 实际 Chromium 200／206 中断同号冷读。作业归属不明时保护动作，明确 owner 保持可用 | `38542cf2` 已推送 `main`。75 个后端和 38 个前端用例、离线真实浏览器及独审通过。当前会话未登录该私有仓，远端 CI 未核实 |
| StockQAbyLLM | 两题各留原超时链和请求引用。已付结果沿原外层身份，合法旧原生读法保留。最终独审 5 项通过 | `86f633d8` 已推送 `master`。127 个源码的 mypy、全部提交钩子与 [远端 CI](https://github.com/zhengcb81/StockQAbyLLM/actions/runs/45737586830) 通过 |
| industry-research | 合成凭据完整脱敏，越界出口退回本仓，按原号补投。组合完成观察到回告全过程 | `38345b66` 已推送 `main`。真实组合、离线回归和独审通过。公开查询返回 404，远端 CI 未核实 |
| revenue-forecast-audit | 原角色包装器强停及原阶段证据。无输出时也能按原号查到已知开始时间 | `9e9e9809` 已提交本地 `main`。该仓未配置远端 |

三仓组合按实际发布源码复验。两套收件箱都不可用后，F4 按原编号查回和补投。IR 的观察、分诊、修复、复验和回告五步完整落盘。ET 启动故障的原始请求和响应字节均为零。过程使用合成输入、真实本地进程和独占数据根。[组合记录与机器收据](reviews/f4-combination/review.md)

本次验收覆盖本轮确认的缺陷、公开边界及上述实际测试。已在生产定时任务留下的旧记录仅使用现存证据。Windows SYSTEM 定时触发、实账户的网络与计费、全局技能副本另以实际部署范围验证。
