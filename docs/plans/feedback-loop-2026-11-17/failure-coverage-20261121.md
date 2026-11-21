# F4 真实运行失败覆盖核查

12 个已上线模块逐仓核查，12 个都有日常失败覆盖缺口。总控另查统一启动器。24 条开放发现已使用既有本机 F4 端口登记，另一进程按原观察身份查回 24 条，登记动作只有 observe。清单中的每一条是可重放的审计发现。本轮没有把它们批量派给模型修理。[正式发生清单](issues/failure-coverage-20261121.jsonl) · [12 仓和总控复验入口](probes/README.md)

## 范围和方法

从 12 个已上线责任仓的普通用户入口取证。Dayu 的采购调用由 CWP 适配层负责。在每个仓区分公开 CLI、原生作业、定时器、HTTP/UI、第三方调用等适用入口。记录正在使用的版本、正常启动方式、失败后的业务返回、留存位置、能否进入分诊、能否安全复现。以新进程读取同一运行作为持久性证据。费用未知的原调用只读核对。

1. 对照原验收范围和 IQS 事故的原始证据。原日志缺字段时区分已知事实与推断。
2. 分仓独立审计，从实际入口注入可控失败，与成功或已覆盖的故障对照。记录没有用例的范围。
3. 总控复核跨仓的因果链、重复计数与错误分类。发布可复跑的发现、根因、下一步和实际验证边界。

## IQS 的原始事故

中微 28 题重评已经保存并交付 10 题。IQS_13、IQS_14 在 HTTP 发送前失败。StockQA 的原始工作记录能证明已准备、没有发送意图、没有对应预算尝试和响应。原释放回执显示两题回到 pending，前十个检查点哈希相同。异常转换只保存了外层 `QuickScanWorkPersistenceError`。无法再从这些旧材料确定底层异常，也不应据此重新调用模型。IQS 是发现方，原因最早能被记录的位置在 StockQA。并行 IQS/StockQA 线的改动应沿同一原任务复验。[IQS 原交接](../../../../invest-quick-scan/docs/implementation/handoff-for-new-agent.md) · [原未发送回执](../../../../invest-quick-scan/runs/amec-rescore-20261121/released-unsent-summary.json)

## 逐仓证据与责任

下表按 2026-11-21 实际审计的版本描述。一个反例即可推翻该仓全覆盖。各行选择的是不同故障类型，不能用它们计算生产漏报率。观察为零、观察被判正常和仅能查到账本是三种不同的结果。发布版、隔离版和安装版有差别时分别注明。

| 模块及受测版本 | 普通入口实测 | 漏记的位置和修复责任 |
|---|---|---|
| IQS `296ab842`，另核活动线 `cd1caec` 相同路径 | 7 种失败或中断没有一例形成可分诊的业务偏差。缺/坏 answers、上游未启动、后台异常和强停、API 500 均可复现。三题全部失败却只报覆盖完整。既有原生 F4 修复/回告 5 项通过。 | `scripts/iqs_scan/tools/scan_result_check.py:175` 查覆盖声明。`workbench/dashboard_jobs.py:132`、`workbench/dashboard_service.py:834` 把异步和 HTTP 错误转译。用 run/job/question/attempt 引用 StockQA 详情，分别保存执行和覆盖结果。 |
| StockQA `2f649c8`，原 F4 `79b0800` | 实际 CLI 的坏题包数、缺 batch 文件、缺主体约束均失败，明确配置反馈输出仍为 0 条。缺文件有本地 traceback。旧付款/强退等 7 个对照通过。 | `src/core/qa_engine.py:552`、`:822` 丢原异常层次。`tests/unit/test_quick_scan_feedback_observation.py:639` 明确断言一种拒绝不产观察。保留结算真值，增加调用失败及可解析的诊断引用。在途修复按最终部署版本复验。 |
| filing-fetch `006725a0`，定时代码 `ec2374a6` | 8 个故障输入中 6 个零观察。坏短请求 5 条均 expected。另一个作业原账为 failed/config_error、执行 1 次，F4 3 条均 expected。真实首次定时补跑有 partial 原生记录。 | `scripts/fetch_filing.py:1904` 先做入参/时间校验，`scripts/ff_short_feedback.py:211`、`scripts/ff_job_feedback.py:65` 在核对结果表达及用量。计划任务直接启动 tick，`scripts/ff_scheduled_windows.py:140` 重定向双流。由 FF 对每个 slot 和作业失败持久投递，按原 attempt 核账。 |
| revenue-forecast 固定宿主 `70165f99`，本地 `698eabd1` | 已安装预测 CLI、来源准备、报告目录、作业提交 4 次错误均为 0 条。来源字节损坏后作业可冷读为 failed，计算和发布未执行，F4 把 failed 标为 expected、费用单列 unknown。 | `rf_job_cli.py:129`、`rf_job_feedback.py:23`。三份已安装技能的普通预测脚本与固定 F4 宿主的文件指纹不同。由 RF 在来源、算、发布的所属作业区保存业务终态。同时测技能与原生入口。[复跑](probes/rf.py) |
| revenue-forecast-audit `df7b0e13`，安装版三个关键文件一致 | 10 个场景。4 个准备/完整性失败零观察。普通 capture 的 exit 7 可分诊。两种委托捕获没有收到下游回执时只有 expected。强杀可只读查回 unconfirmed。64 字节取证设置下，同样的超长 stderr 让 exit 0 和 exit 7 都被读成 failed。 | `audit_run.py:523`、`:813`、`:998` 和 `audit_feedback.py:59`。按已经收到的同次下游终态去重。分别存退出、详情完整度及费用。保留完整脱敏原因引用，费用未知只查原作业。[复跑](probes/audit.py) |
| StockWiki `7ab87780` | 身份参数、文件缺失、历史分页、登记、发布、工作决定共 6 个 exit 2 全部零观察。身份源离线 exit 0，产 2 条 expected 且丢失 owner_offline。合法历史缺失对照正常。 | 身份/评估的 CLI 只在成功返回后投影，`tests/test_research_feedback.py:745` 明确断言拒绝时无观察。由本仓在命令终态同时保存原生 reason 与投影质量。[复跑](probes/stockwiki.py) |
| Dashboard `46e29cd4` | 隔离实际 HTTP 服务收到 3 个 503、1 个 400、1 个 404。五个响应均有 correlation ID，访问日志有状态码。重启读取 0 条 F4，无法根据任何一个 ID 找回 FF 子进程诊断。 | `backend/dashboard/transport/http.py:397` 转译请求，F4 只接了快扫投影。每个 HTTP 请求用同一 ID 引用后端调用。记录真实错误、预期输入拒绝、主动取消的区别。前端只补服务端看不到的失败。[复跑](probes/dashboard.py) |
| earnings-transcripts `61fe94e2` | 8 案中 4 案零观察，含坏 TXT 已在原生审计报告记 corrupt。离线 worker 失败/HTTP 402 有观察，命名检查均 expected，费用 unknown。漏用量的正控能报偏差。 | 参数处理早于日志，普通采集和 TXT 审计独立。`retrieval_runtime.py:130` 及 `transcript_feedback.py:293` 丢子进程诊断或只校验错误名称。分别发动作、来源可用性与费用事实。[复跑](probes/et.py) |
| StockInfoDLSimple `ae944067` | 9 案中 7 个故障均不能分诊。模拟下载 PermissionError 时主程序先报失败再报全部完成，退出 0。失败 logger 第一次写盘注入 PermissionError，恢复后第二次 flush 无文件且队列已空。正常候选和身份丢失两个对照正确。 | `src/downloader.py:61` 写前清空内存。`main.py:218` 丢弃任务结果。适配器把入参/暂存/超时合成 upstream_unavailable。成功提交才确认队列。业务与重试原因按原步骤保留。[复跑](probes/sid.py) |
| MeetingConverter `e7b6c021`，部署代码 `8b8e574f` 相关路径一致 | 10 案。4 个启动失败零观察。翻译器未启动、主引擎故障后回退都发布成功且无偏差。一次转录失败只留 RuntimeError，底层 TimeoutError 只出现在控制台。强停保留原尝试和未知费用。 | `transcribe.py:83`、`core/pipeline.py:129`、`core/feedback.py:597`。入口覆盖初始化，每个请求阶段分别保存意图和实际用的引擎，保留脱敏原因链。成功回退记录为降级。[复跑](probes/mc.py) |
| industry-research `2aa2eff1`，另测实际安装技能 | 11 案。10 个新故障中 9 案零观察。上游 exit 43、collect 工件写明 unavailable，但 F4 两条均为 expected。缺三份必需材料时本仓退出 1，安装的旧版却退出 0，写出 sources_count 为 0 的正式报告。已有报告覆盖正控可以分诊，原修复/恢复测试 8 项通过。 | `tools/quick_scan_client.py:2505`、`tools/report_generator.py:68`、`tools/deepseek_client.py:81`。收集、渲染、模型调用和实际安装的普通入口分别核验，owner 决定何时报告可发布，并同时留下缺项和处理结果。[复跑](probes/ir.py) |
| company-wiki `197a1718b`，定时入口固定 `1e2a3b0e3` | 损坏原件精确读取 exit 2，定时读取 exit 0 但单项 uncertain/source_owner_refused，新进程查回同一结果。摘要、坏配置、Dayu 适配层和 Worker 均找到零观察路径。Worker 账本可读 dead_letter/HANDLER_EXCEPTION/1 attempt。旧 Phase C 显式重投只有 v1 普通失败产生对应偏差。 | `src/company_wiki/source_catalog/source_reader_cli.py:126`、`src/company_wiki/automation/narrative_batch_cli.py:103`。本次已修复正式 Phase C 投影。公开读取、普通批处理、worker、定时逐项投递仍需本仓接入。[复跑](probes/cwp.py) |

前三仓的可复跑入口为 [IQS](probes/iqs.py)、[StockQA](probes/stockqa.py)、[filing-fetch](probes/filing_fetch.py)。这些探针都使用本地夹具。可按 [复跑说明](probes/README.md) 选取对应代码版本。测试用子进程、HTTP 环回和临时文件均由探针自己拥有。

## 总控和 CWP 已修复的范围

1. 旧的统一启动器在原程序提前退出、可执行文件不存在、或仅下游留下观察时会丢掉本次运行。隔离测试旧版的 exit 17、exit 127 和真实原件读取 exit 2，冷读宿主三个场景均为 0。现在启动器先保存原运行和尝试，异常退出在本仓收件箱保存独立进程回执。原生命令的二进制标准流、退出码保持。仅当本仓原生回执明确绑定本次进程并解释同一退出码时才合并这一事实。同一 run 下另一步失败不能代替它。重读不会重启原件下载或模型调用。监督进程先死则返回可查的 unconfirmed。仍存活的长任务也可能暂时没有终态，此时不能声称已经失败。[总控探针](probes/intake.py) · [总控回归](../../../tests/integration/test_feedback_f4_intake.py)
2. CWP 正式摘要回执 v1 的成员叫 documents，v2 的叫 items。投影现在按两个公开合同及原 run 读取失败、预算耗尽、空间耗尽，保留原原因、费用可知性和尝试。坏版本、另一 run、正常成功和没有实际运行的阶段均有反例。旧固定生产目录代表修复前状态。投影修复验证在当前主线，普通调用的自动投递和未知费用下的独立业务分诊仍待实施。[生产投影](../../../tools/document_understanding_benchmark/phase_c_feedback.py)

## 为什么原测试通过

原验收的起点是“已经出现一条受支持的观察”，测去重、查原作业、修复、复验和回告。普通用户从 UI 点击、原生 CLI 启动、系统唤醒定时器、技能安装目录执行时，可能在建观察前就退出，或根本不走统一启动器。格式、计费、覆盖率检查各自可以正确，同时业务失败。CI 的缺口是没有从这些普通入口建立失败清单，并用退出后的第二个进程去核对实际能否分诊。

## 分仓整改顺序与验收

| 顺序 | 谁做什么 | 验收证据 |
|---|---|---|
| 1 原因与记录防丢 | StockQA 与 IQS 在现有重评工作线上保留同一 question/job/attempt 的发送前阶段、脱敏异常链及所属模块代码位置。SID 把失败队列的确认放到成功持久化之后，覆盖并发、失败后再次写入。Audit 把日志传输完整度和业务终态拆开。 | 造两个外层异常同名、底层原因不同的故障。从新进程分辨两者。失败写入/强停后第二次补投只有一个发生，原收费调用计数不变。旧 IQS 两题根因仍记未知。 |
| 2 对齐业务真值 | FF、RF、CWP、ET、MC、IR、StockWiki、IQS 分别从既有原生结算/作业/逐项结果投递业务终态。同时保留来源是否可用、是否降级、是否实际发送、用量是否已知。IR 和 RF 将日常技能安装入口纳入同一组验证。 | 正常退出但部分失败、预期空结果、合法拒绝、可用降级、收费未知、格式正确但业务失败均可冷读区分。已支付或不确定的请求只从原尝试核对。空报告、公文占位、已跳过的工作不能记作成功完成。 |
| 3 全普通入口接入 | 每个 owner 在调用边界最早分配身份，默认写自己的原生日志/事务内待投递项。Dashboard/IQS 在每个 HTTP 请求和后台作业各自记录，FF 由定时 slot 对账。总控消费公开回执和确认投递。业务结果与诊断写失败分别报告。 | 关闭调用者的可选反馈环境变量，普通入口仍能在新进程读回发生。注入冷启动、子进程失败和临时日志介质不可用。恢复后能核对受影响区间和补投，成功同级任务保留。 |
| 4 验收与运营 | 总控与各仓用同一批独立样本测试公开边界。在现有日常检查增加对账，分别显示已登记失败、可分诊、缺原因、仅可查账、待补投。发布时对真实安装入口做一次抽查。 | 以 owner 原生失败清单、入口交通或启动登记作分母，逐项逐 attempt 对照 F4。允许多个观察指向一个问题。不能用反馈库自己的行数当分母。新造的运行错误从发现端到责任仓再到发现端复验，通过后才更新全覆盖结论。 |

每个 owner 保留一次本地最小复现所需的公共操作名、代码/配置版本、原运行/尝试、输入引用、阶段、稳定原因码、经过脱敏的异常层次和代码位置，以及副作用是否已经开始。调度层只接收引用和可比较的结果。预期拒绝可留观察并由 owner 审视门禁。不需要为每条记录发起修复。未知费用不妨碍记录和调查已知业务错误，只约束会重复产生副作用的动作。

## 证据边界

本轮没有重新发出中微原任务、使用真实付费模型、重启在线服务或改动另一个 harness 的业务仓。没有逐一触发每个业务分支、每个浏览器事件或每家供应商线上故障。相应结论以逐仓证据为限。没有可写介质且外层也未登记启动时，事后无法从零字节还原异常。运行前的启动登记与跨进程只读对账可以暴露这段缺口。跨进程强杀、正常退出但业务失败、安装版本分歧分别验收，不能互相代替。
