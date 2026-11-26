# S1–S5 独立复审发现

**结论：S1–S5 的完整验收尚未通过。** 12 个模块分别由独立 agent 检查，核对实际运行版本、公开入口、仓内依赖、CI 收集范围和原故障的可复现性。本轮确认已发布的定向修复中有通过项。S2、S3、S4、S5 的完整范围在 12 仓均为部分完成。S1 的八个原任务中，3 个在原卡范围内通过，5 个仍有缺口。其余 4 个模块没有单独的 S1 原卡。

## 分模块判定

| 模块与独审报告 | S1 | S2 日志 | S3 边界 | S4 测试 | S5 收口 | 首要未完成项 |
|---|---|---|---|---|---|---|
| [company-wiki](modules/company-wiki.md) | 部分 | 部分 | 部分 | 部分 | 部分 | AUTO 领取前崩溃丢原尝试，日志泄露合成凭据，资料注册直接依赖存储 SQL |
| [filing-fetch](modules/filing-fetch.md) | 原卡通过 | 部分 | 部分 | 部分 | 部分 | 次级日志失败使已得业务终态丢失，三表入口强停未保存原请求 |
| [revenue-forecast](modules/revenue-forecast.md) | 部分 | 部分 | 部分 | 部分 | 部分 | 旧子进程可覆盖恢复产物，历史尝试无法用原身份查回 |
| [earnings-transcripts](modules/earnings-transcripts.md) | 部分 | 部分 | 部分 | 部分 | 部分 | 子进程启动被拒时丢脱敏、退出协议和已知未发起请求的终态 |
| [StockInfoDLSimple](modules/stockinfo-dl-simple.md) | 部分 | 部分 | 部分 | 部分 | 部分 | 翻页故障被当成合法末页，部分下载被报告为全部完成 |
| [MeetingConverter](modules/meeting-converter.md) | 原卡通过 | 部分 | 部分 | 部分 | 部分 | 已收到 HTTP 200 的请求因正文截断被重复提交 |
| [StockWiki](modules/stockwiki.md) | 部分 | 部分 | 部分 | 部分 | 部分 | 身份桥绕过存储层并破坏只读语义，公开资料入口缺留痕 |
| [invest-quick-scan](modules/invest-quick-scan.md) | 无原卡 | 部分 | 部分 | 部分 | 部分 | 原异常已落盘，但重启后按原作业无法查回 |
| [investment-dashboard](modules/investment-dashboard.md) | 无原卡 | 部分 | 部分 | 部分 | 部分 | 流开始后失败，前端收到的响应没有可查询的相关号 |
| [StockQAbyLLM](modules/stockqa.md) | 原卡通过 | 部分 | 部分 | 部分 | 部分 | 公开拒绝与 F4 分配不同运行号，任务仍依赖具体账本 |
| [industry-research](modules/industry-research.md) | 无原卡 | 部分 | 部分 | 部分 | 部分 | 内容偏差投递失败无降级告警，纯文件处理仍依赖快筛运行环境 |
| [revenue-forecast-audit](modules/revenue-forecast-audit.md) | 无原卡 | 部分 | 部分 | 部分 | 部分 | 观察已投递时公开冷读仍可能找不到原诊断，角色捕获强停丢输出 |

## 已实证的跨模块问题

1. **启动失败在第一条作业记录之前。** CWP 的 AUTO worker 在领取前真实崩溃。用合成 Bearer 的测试证实，父子尾日志可保留原样凭据，冷查却没有原尝试。整改应把脱敏放在写入点，并在父进程启动前固定可冷查的原身份。[CWP 复验](modules/company-wiki.md)
2. **进程结束与输出所有权需要分别证明。** RF 真实强停父进程后，仍活着的旧计算进程能覆盖新尝试已成功的结果文件。同一旧尝试在新尝试结束后也失去 F4 冷读。测试应证明产物按尝试隔离、只有已确认的结果能发布、以后仍可查询每次尝试和计费事实。[RF 复验](modules/revenue-forecast.md)
3. **业务提交与诊断持久化在关键路径上相互影响。** FF 已拿到结果后，次级日志写不进去导致原结果和费用进入未知。另一反例中详情无法落地，观察却被标为已送达，移除故障后仍不能查原详情。先保留业务事实，独立记录诊断或投递状态，再用同一身份对账。[FF 复验](modules/filing-fetch.md)
4. **正常、失败和中断需要共同的运行起点。** 总控对无侧车的成功进程会清掉 marker，CWP 的正常公共读取和 FF 的三表正常或失联也缺对应轨迹。F4 保留偏差分诊职责。本地 owner 用已有台账或有界日志轻量记下开始、关键步骤、原输入引用、实际版本和终态，单独保留外部效果的已知或未知状态。
5. **冷读必须从用户实际拿到的原身份出发。** StockQA 公开拒绝返回的运行号与 F4 不同。IQS 已持久保存准备失败，但按原作业公开 GET 只返回后来生成的通用诊断。Dashboard 已承诺 HTTP 状态和响应头之后再出错，前端拿不到后来才生成的相关号。按原运行进入冷读应能列出原尝试及其完整原因，并保留后续阶段的状态变化。流式响应先绑定可查相关号，随后以这同一身份保持终态。[StockQA](modules/stockqa.md) · [IQS](modules/invest-quick-scan.md) · [Dashboard](modules/investment-dashboard.md)
6. **故障被当成了正常结束。** StockInfoDLSimple 两页夹具的正常对照保存两份文件。第二页点击异常时只保存一份，CLI 和原生冷读均仍报告全部完成。分页端口应返回能区分合法末页与故障的结果，并保留已收集项和原异常。[SID 复验](modules/stockinfo-dl-simple.md)
7. **收到外部响应与成功读取正文是两个不同事实。** MeetingConverter 正常完整响应提交一次，已收到 HTTP 200 后正文截断时，同一载荷在隔离测试中提交三次。费用实际是否扣除仍未知。ET 的另一端是已知子进程创建失败，却只保存 started，随后原用量查为未知。应在进程或者网络的真实边界保留可证状态，并按该状态判断重试或冷查。[MC 复验](modules/meeting-converter.md) · [ET 复验](modules/earnings-transcripts.md)
8. **只读协议的行为要由实际存储边界保证。** CWP 的 AUTO plan 在缺库时创建 SQLite。StockWiki 在合法路径含 `#` 时打开错误位置并创建空库。装配层应使用所属存储的只读公共接口，路径转换和打开方式由同一 owner 管理。[CWP 复验](modules/company-wiki.md) · [StockWiki 复验](modules/stockwiki.md)
9. **投递成功和诊断可读都需实测。** IR 的内容偏差在观察目录不可用时静默丢失。Audit 的索引损坏且有两套自定义可写目录时，观察与诊断可落在不同地址，公开冷读找不到已知失败。验收需从调用者收到的身份或公开引用查回源因。[IR 复验](modules/industry-research.md) · [Audit 复验](modules/revenue-forecast-audit.md)

## 总控主进程留痕实测

使用 `c918a402e` 工作区现行 F4 编排源码、本地原生 Python 子进程与独占 SQLite，三种场景各执行一次。按审查用例中的替身仅关闭自动唤醒，以新进程调用正式 `drain`。

| 场景 | 原业务退出 | 写入的进程回执 | 新进程排空与数据库回读 | 在调用时的宿主告警 |
|---|---:|---:|---:|---:|
| 成功退出、owner 无侧车 | 0 | 0 | 0 个观察，ready 随后清理 | 0 |
| 失败退出、仅主输出根不可用 | 19 | 1 | 1 个原观察 | 0 |
| 失败退出、两个输出根都不可用 | 19 | 0 | 0 个原观察，排空时仅有 2 条 inbox 不可读 | 0 |

**F4-01 (P1)**。两个投递目录的创建错误都在 [intake.py](../../../../../tools/feedback_loop/intake.py) 的 `run_observed` 内被继续处理。无可用 marker 时，后续的失败收据、唤醒与降级记录整段跳过。业务继续运行一次，但调用方原退出与 F4 中的运行身份失去关联。已有单根故障对照能冷查，缺的是双根故障时独立于投递协议的宿主告警及原执行事实。使用相同原身份落现有宿主日志或 stderr，仍允许业务正常结束。应验收双根故障时的同 run/attempt 与退出、无法保存的明确状态、零回放副作用。

**F4-02 (P1 验收缺口)**。成功命令若没有 owner 事件，宿主只创建临时 marker，`drain` 允许清空标记且无成功历史。不能用 F4 流水反推有多少正常操作或在哪一阶段中断。保留 F4 的偏差分诊职责，每个 owner 的已有账本或有界日志负责保存开始、关键步骤、终态及其同一身份。用无失败正常跑、第一阶段强停和冷进程对照三个场景验收。脚本 [host_lifecycle.py](evidence/host_lifecycle.py) 可从仓库根运行，设置 `PYTHONPATH` 为该仓库根。

## 部署和 CI 核对

已读实际 12 个 F4 工作目录。7 个有跟踪文件差异，运行源码命中为 CWP 的既有 `source_catalog/read_budget.py`，未更改。其余命中为规划、覆盖率或证据类型路径，按分仓报告记录。重新读取八个公开 GitHub Actions，均对应 S5 发布台账的源码提交且成功。CWP 的 `c918a402e` 是在通过 CI 的 `88f10bf96` 之上的文档提交。StockWiki 和 Audit 为本地正式线，Dashboard 和 IR 的私有远端 CI 保留为未在本会话独立验证。

对已配置的 Python argv 做静态定位。RF 的 report 和 reconcile 都落在当前 `f4rd` 的同一个 `rf_job_feedback.py`。其余明确含 Python 脚本或模块名的 owner 入口也能在自己的工作目录定位。CWP 的配置项走宿主动作而非此类直接 argv。动作配置只是连接证明，完整业务步骤检查见分仓结果。

重新运行原生 F4 八项定向回归，全部通过。所测为原退出不重跑、主根失败备份、确认归属、完整成套回告及保留未知原费用。源码只读，唯一环境警告是本次关闭自动加载插件后 pytest 不识别仓内未用的 asyncio_mode 配置。

| Owner | 实际 Git 引用 | CI 证据 |
|---|---|---|
| company-wiki | c918a402e | [源码 88f10bf96 通过](https://github.com/zhengcb81/company-wiki/actions/runs/45706597671) |
| filing-fetch | 7651f70d | [通过](https://github.com/zhengcb81/filing-fetch/actions/runs/45702059828) |
| revenue-forecast | 49a4013d | [通过](https://github.com/zhengcb81/revenue-forecast/actions/runs/45703892813) |
| earnings-transcripts | 7f4c1e7d | [通过](https://github.com/zhengcb81/earnings-transcripts/actions/runs/45698502294) |
| StockInfoDLSimple | 9b0c07c9 | [通过](https://github.com/zhengcb81/StockInfoDownloader/actions/runs/45699176729) |
| MeetingConverter | fa1f840d | [通过](https://github.com/zhengcb81/MeetingConverter/actions/runs/45692989173) |
| StockWiki | 65d39025 | 本地正式线 |
| invest-quick-scan | e0ad7576 | [通过](https://github.com/zhengcb81/invest-quick-scan/actions/runs/45706744119) |
| investment-dashboard | b57672fd | 私有 CI 未独立核对 |
| StockQAbyLLM | a4a81e5a | [通过](https://github.com/zhengcb81/StockQAbyLLM/actions/runs/45709450883) |
| industry-research | 42c23330 | 私有 CI 未独立核对 |
| revenue-forecast-audit | 560ae51c | 本地正式线 |

四个逻辑技能安装位置用原安装器只读查验。IR 的受管文件零差异，Audit 的 52 个受管文件四处均一致。RF 独审对四处各 141 份非配置文件核对了实际字节。FF 独审确认运行脚本一致，安装器仍报告两份 references 的换行字节差异。当前安装结论以这些实际检查的受管范围为准。

本轮使用真实入口、实际进程生命周期、隔离状态以及合成输入或本地替身。未请求外部数据或模型服务，未产生供应商费用。CWP 的脱敏反例只证明合成值在该路径会明文落盘。Windows SYSTEM 定时任务的实际触发和所有平台上的完整运行矩阵尚未复验。分仓报告有明确的定向验证范围。

## 设计与验收建议

1. **在公开入口建立一次原运行身份。** CLI、HTTP、定时器和父进程在解析、首个子任务或 HTTP 响应开始之前关联同一运行。owner 用已拥有的台账或小型有界日志记时间、实际代码版本、输入引用、尝试、关键步骤和终态。已知失败的完整脱敏因果在本仓可冷读，F4 继续接收简明偏差和可查引用。
2. **先保存业务事实和可证计费，再处理投递与告警。** 轮转日志、观察投递和业务提交各有自己的错误。对于已知没有启动的失败，保留这项事实。对于可能产生外部效果的失败，保持未知并沿原动作查询。已收到的结果和费用事实不得因次级日志失败变成未运行。测试包括一个介质失败和多个介质失败的情况。
3. **按尝试隔离进程与产物。** 恢复时先查活跃的旧子进程及原费用，后续尝试使用独立输出。只有所属层确认的尝试能发布，历史 run/attempt 在新结果发布后仍可冷读。每个真实命令分别测正常、启动失败、强停、延迟旧进程和恢复。
4. **用实际所有权验证解耦。** 在 CWP 来源读写、FF job 终态、RF 归档读取和 StockQA 工作账本等已证边界优先拆开职责。测试用仅实现公开协议的协作者，把私有存储、配置和发布流程留在所属层。CI 快速组加入已证故障所需的最小用例，Windows 上实际发生的进程、分页和文件语义用原平台验证。循环计数用于定位，行为回归决定是否收口。
