# F4 分仓上线与组合验收

2026-11-20。本机 F4 工程上线和组合验收按各仓支持范围收口。12 个责任模块已接入总控。独立 agent 分别验证本仓端口，总控负责公开接口组合、实际接线、发布和跨仓独审。现场原作业或正式结果尚缺的见末节，按对应业务计划跟进。

2026-11-21 逐仓从日常入口注入故障后，12 个责任仓均有漏报或误判。以下保留已通过的接线场景。常态运行覆盖的现状与下一步以 [失败覆盖审计](failure-coverage-20261121.md) 为准。

## 当前工作

| 责任仓 | 本轮范围 | 进度 |
|---|---|---|
| earnings-transcripts | 原始请求与用量收据的只读恢复，验证并回告可核对的旧结果 | `main@61fe94e` 已发布并接本机，744 项及组合通过，独审 7 项通过 |
| StockInfoDLSimple | 原有供应商候选证据到公告投影，复验证券与材料绑定 | `v2-clean-rewrite@ae94406` 已发布并接本机，147 项、SID→CWP 17 项及总控独立组合通过 |
| industry-research | 依据原权威结果修复报告覆盖状态，保留原报告 | `main@2aa2eff` 已发布并接本机。独审问题修复后 70 项，ROOT 8 项及 7 子例、组合各通过 |
| StockWiki | 从本仓已发布评估恢复原 run/scan 投影 | `a3cd01c` 已并本地主线。接线后主线到 `e4d7e85`，F4 文件一致。本仓无远端，179 项定向、392 项日常和宿主复验通过 |
| invest-quick-scan | 从本仓已保存答案恢复覆盖率和检查回执 | 原发布线 `codex/iqs-manifest-delivery-01@4a895d3` 已推送并接本机。283 项、真实记录、总控复验通过 |
| StockQAbyLLM | 从原付费作业和本仓结果回告接续 | 原发布线 `codex/qa-content-filter-resolution-01@79b0800` 已推送并接本机。原尝试、原账本及强退恢复通过 |
| investment-dashboard | 从正式公开结果、原发生与 UI 投影接续 | `main@fb5c11a` 已推送并接本机固定公开读端口。真实读取、隔离正式结果的复验和回告通过 |
| company-wiki | 统一接收、作业唤醒、原生消费者验证 | 本机统一入口及现有分诊接线有效。独审定位并修复旧 Windows 包路径，按当前安装启动 |
| filing-fetch | 原生作业接续、用量保真、原回告读回 | `main@301ec0b` 已推送并接本机。实际已有第 2 次尝试的作业查证通过，`exact`、`latest_as_of` 均通过强退复验 |
| revenue-forecast | 按原 attempt 核对来源步骤及费用，读取原回告 | 本机公开脚本 `70165f99`，测试与计划已推 `main@f06534bc`，运行脚本一致。原作业恢复和回告通过独立复验 |
| revenue-forecast-audit | 按原 capture 核对状态，发布原生工具失败和拒绝，复验原发现 | 本地 `main@87849d8`，同步现有两份技能。真实 FF 拒绝、同一观察去重和未知作业恢复通过独审，805 项基线和最终 39 项定向通过 |
| MeetingConverter | 已配置本机宿主，复验已发布的旧译文清单动作 | 运行代码 `8b8e574`，复核计划发布到 `master@e7b6c02`，正式设置的五条路由、强退接续与零重复转录确认通过 |

Dayu 的运行观察继续通过 CWP 的外部 provider 适配器。

## 实施顺序

1. 各独立 agent 核对活动工区，从当前发布基线用本仓独立短工作树施工。受支持场景先留红绿证据，以原生输出、原件指纹、版本和实际可恢复的业务状态为依据。能复用现有恢复或结果接口时沿用。依现有分诊协议审视真实拒绝保护的事实。证据缺失、任务尚在运行和未知费用保留各自状态。
2. 复用总控 `feedback-action/1` 和已配置的 `owner-json`。交固定命令与运行目录、生产旁路位置、可读原生状态、可安全修理的范围、完整持久回执及其只读查询。业务完成后从已有 sidecar 唤醒总控。统一启动入口为模块提供自己独占的旁路文件，原 CLI 的返回码及输出由原 CLI 负责。进程中断后恢复已有动作及待处理观察，不重新启动业务。
3. 总控用真实 owner 命令和隔离数据验证同一观察自动经过分诊、修复、原消费者复验和回告。生产测试用计数夹具或已保存原数据核对恢复零新增业务调用、尝试和费用。强退或缺回执用原 ID 查证。合并前集中独审，确认保护边界、旧状态和实际可读取的适用范围。
4. 各仓通过后按已有发布线推进并核对版本。逐仓更新实际宿主配置，在部署路径只读核对原生端口。保留现有作业及收据。用一次统一入口的组合检查验证独立模块并行、重复和重启。总控据实际可部署范围写入本表和父计划。

各仓同一场景完成即发布，交接字段与既有分工一致。未有安全自动修复范围的事件保留问题并转本仓修复流程。 [控制协议](interfaces.md) · [现有宿主](host-integration.md)

## 统一运行与接续

普通应用原生观察目录由宿主设置中的每仓 `native_observation_dirs` 指定。Windows 唤醒使用原宿主的 Python，当前用户登录和每十分钟触发同一个任务，机器恢复后补跑。相同配置安装两次仍是一项任务。设置文件旁的 `last-native-recovery.json` 只保存最近一轮结果。隔离验收已用真实 Windows Task Scheduler、模拟发布中断遗留的完整正文和空动作库查回一条已完成观察，临时任务已清理。交付期可用 `-Owners` 选已验模块，后续在同一任务上更新订阅。多仓联调有单独的真实强停用例。

```powershell
.\tools\feedback_loop\install_recovery_task.ps1 -SettingsPath .planning\shared-reading-production\feedback-host\settings.json -PythonPath C:\Miniconda\python.exe
```

11 月 23 日已为 `company-wiki`、`industry-research`、`revenue-forecast`、`revenue-forecast-audit` 与 `investment-dashboard` 启用同一个实际任务。重复安装返回 `already_installed`，手工唤醒系统退出 0 并得到新回执，当时无待处理观察。按 owner 指定范围时，恢复从该范围查原队列及收件箱，背景动作完成后的接续继续使用相同范围。各 owner 明确转交的观察仍按已有接口路由。StockWiki 默认收件目录已有历史失败，当前在本仓核对来源后再接入自动分诊。

在总控仓用实际宿主的解释器运行下面的入口。`SETTINGS` 和 `HOSTS` 来自原有本机 `feedback-host` 目录。给一个 owner 配置固定工作目录和专用 `observation_dir`。下面命令中 `ORIGINAL_COMMAND` 是本次已确定的本仓公开命令及原参数。

```text
python -B -m tools.feedback_loop.intake --settings SETTINGS --hosts HOSTS run --owner OWNER -- ORIGINAL_COMMAND
python -B -m tools.feedback_loop.intake --settings SETTINGS --hosts HOSTS drain
```

首次启动或宿主重启在原配置和原动作库执行 `drain`，然后按正常方式调用业务。每次原命令保留自己的返回码和标准流。反馈先存独占观察文件并异步接续。`intake_hosts` 指向已配置的 owner map，后续动作有可信终态时自动唤醒相同收件箱，因此最初的有限等待结束后仍能完成复验和回告。值班人员可单独指定 `--owner` 诊断某仓。恢复只查已登记的观察和原动作。尚无法验证的终态留在原观察，业务重新发起由原调用者明确控制。

父 CLI 和继承输出变量的 provider 可以共用同一受控观察目录。例如 filing-fetch 调用电话会工具时，两方的原生观察可在同一独占旁路。宿主按每行的发现方和责任方路由，共用收件箱只扫描一次。各仓按自己的原生引用、发生和尝试取证，修复与回告仍在本仓保存。进程强停遗留的 `.pending` 保留给恢复，因为同一业务可能还有迟到的记录。

总控快捷复验运行 `tests/integration/test_feedback_f4_intake.py`。`tests/integration/test_feedback_f4_owner_runtime.py` 可给各仓指定含本仓测试夹具的正式版本，环境变量为 `FEEDBACK_<仓标识>_RUNTIME_ROOT`，仓标识为 `ET`、`SID`、`IR`、`SW`、`IQS`、`QA`、`DASH`。用各仓真实产出或已保存观察、真实 owner 命令和独占总控动作库，核对回告、重复接续及原始材料完整性。

## 第一批宿主验收

ET、SID 已快进到原发布分支，本机使用这两个正式检出。总控及已配置端口的定向回归执行 47 项，46 项通过，1 项需要已发布 RF 代码而未参与此批。使用 SID 已发布公开入口跑通实际 `intake run`、返回和自动唤醒。接线前后已有动作库仍为 12 条 `done`，字节 SHA 完全一致。验证使用隔离数据和既有留存，没有新增业务供应商请求或模型调用。ET 的该历史补发结果由本仓公开查询读回，FF 对真实历史记录的采用要单独取证。

## 第二批宿主验收

StockWiki 从已发布评估公开读取补发三组原 run/scan 引用。修复及回告先落盘后丢回复，原动作各只登记一次。本机使用本地 `master`。行业研究的自动纠正确认同一查询主体、字段、日期、快照与筛选范围，原 Markdown 字节保留。异源、围栏伪元数据和未证来源保留问题，真实旧格式在有同源上下文时仍可复验。本机端口代码使用 `industry-research` 正式检出，数据根沿本机已配置的行业研究工作区。

RF、FF、Audit 正式版本在隔离环境再次跑通原有来源失败和审查作业恢复。两个原元数据请求来自环回夹具，恢复期间请求、下载、付费均为零。原 RF 只剩 `reconcile`，旧费用继续未知，Audit 正确查回原未确认 capture，新的同案核验与回告各一次。此轮使用离线分诊，真实 Codex 会话见[原验收](f4-rf-audit-acceptance.md)。

IQS 对原快扫纠正的是完整性判断，保留已答 24 题，报告 38 题中有 14 题未覆盖。原检查退出码为 1，反馈仍自动回告。StockQA 从本仓的原尝试绑定找回原冻结账本，补发已结算终态。ROOT 复验通过，修复和回告重复处理各只发生一次。原材料和账本逐字节保留。两仓历史费用按原证据保留，新增请求、尝试和费用均为零。

本机 IQS 和 RF 的代码路径采用各自仓内 `.worktrees/f4-runtime` 中精确发布版。对应业务数据继续从各自工作根读取。IQS 当前原工区正在修改 `task_plan.md` 与其他代码，因此从隔离检出提供发布文件；RF 也从隔离检出运行。StockQA 在自己的既有发布线可快进，使用正式检出。

## 最终接线和验收范围

- 总控最终 51 项原生和组合用例通过。覆盖业务结束后的自动接续、多个 owner 共用观察目录、实际子进程强退、幂等修复和回告。独立复核核对原请求、版本、费用未知和只读边界。CWP 的 Windows 安装动态解析、缺可执行文件终态及原生标准流在 24 项定向复验中通过。旧包路径已换为固定命令名，宿主按可信 PATH 或 Windows 注册安装取当前版本。现场 `--version` 和 `exec --help` 通过，当前 CLI 为 `0.169.1`。
- FF 新路由直接调用本仓公开 `reconcile`，其原作业作用域、期次、限额及结算分别由 FF 自己核对。终止两种采集进程后均恢复同一原件与一次原尝试；恢复期间外部请求、下载和新增费用为零。ET 补发的内嵌 `usage_receipt` 在隔离环境通过 FF 现有用量解析；错误的请求 ID 仍报未知。 [FF 本仓验收](../../../../filing-fetch/docs/plans/f2-ff-short/f4-native-reconcile.md)
- Audit 启用多运行原 capture 读取。通过扩展版 `f4_rf_audit_host_probe.py --audit-runtime` 和当前 FF/RF 测试真实进程、原尝试及动态复验条件。现场真实 Audit 原捕获状态为 `succeeded`，历史费用未知，原事件文件一致。本机尚没有与当前正式自动复验规则配对的 RF 原作业。已有验证适用隔离冻结原作业，生产缺对应输入时继续待证。 [Audit 本仓验收](../../../../revenue-forecast-audit/docs/plans/company-pool-cycle-2026-10-09/F4-AUDIT.md)
- Dashboard 的 F4 读面使用正式 IQS `127.0.0.1:8766` 和独立 Dashboard `127.0.0.1:48766`。两段公开读均为 HTTP 200。实际短命令从同一 StockWiki 数据根读到同一实体与挂牌，隔离宿主接到六条真实观察。宁德时代、微软和腾讯在本次验证的同一业务根尚无正式快扫评估；缺失按现有结果返回。已有正式结果的复验、强停和回告在隔离 HTTP 端到端完成。后续同一业务根的正式登记归 M6。此上线入口是单次取证命令，常驻站普通点击逐请求触发由 Dashboard 自己维护。 [Dashboard 本仓验收与启动配置](https://github.com/zhengcb81/investment-dashboard/blob/fb5c11aff0ef3189bda241b4ea3c4a7b1c328ef5/.planning/unified-dashboard-2026-10-26/modules/m6-quickscan/feedback-runtime-2026-11-20.md)
- 本机配置为原 `feedback-host/settings.json` 和 `hosts.json`。原动作库依旧为 12 条已完成观察，发布前后字节 SHA 一致。IQS 隔离检出保留其启动用的代码、schema 和题库，Dashboard 隔离检出保留 backend、contracts 和 scripts。两个固定读监听均使用原 IQS 的 `--no-refresh` 配置和独立 Dashboard 状态目录。启动参数在 Dashboard 交接中，`investment-dashboard/read-listeners.json` 记本机启动回执。宿主重启先恢复原本机服务，再执行本页 `drain` 接回原观察和原动作。

M6 后续已在原位置登记中微的 `cas_6cab1b94d8f45d42c750`。据 StockWiki `e8da004` 和 Dashboard M6 本仓记录，36 题中有 8 题得分、28 题证据不足，总分为空。StockWiki CLI、IQS HTTP 和 Dashboard 已公开读回同一结果。这份结果的历史反馈复验仍按原发生和正式结果身份取证。 [M6 进度](../../../../investment-dashboard/.planning/unified-dashboard-2026-10-26/modules/m6-quickscan/progress.md)

W12 追加真实 RF 和 Audit 配对证据。两仓的公开 reconcile 查回一次正式 RF 作业和对应的原 Audit capture，确认源、算、发布各一次，原文件字节一致，原捕获的外层费用保持未知。真实拒绝另行核对，先记录原发生，再审视截止日检查。其独立审查已写入 Audit LOG，隔离宿主仍未返回分诊终态，保留原会话待证。 [真实 W12 收据](../du11-source-closure-2026-10-18/review/w12-wuxi-resume-20261120/README.md)
