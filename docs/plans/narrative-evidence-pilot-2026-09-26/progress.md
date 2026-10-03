# Progress：激进简化实施

> 历史Phase 1–64及详细运行记录：https://github.com/zhengcb81/company-wiki/blob/bff81afe7cbb11c895764a94c2eabd121539e248/docs/plans/narrative-evidence-pilot-2026-09-26/progress.md。当前只记录本计划的真实完成项与下一步，不重复旧验收。

## 2026-10-03 — 采纳方案、恢复实施

- 用户明确要求以八束激进方案改整个PWF并继续执行。已将task_plan改为S0–S6当前顺序、具体接口/owner/大节点与原件保护；README统一入口，旧卡的执行要求由当前页覆盖，不复制大体积历史。
- CWP当前bff81af已核clean。正常用户只读外仓：RF main6fb2def7/4 tracked dirty，fcap5319ee26保留；FF c47c397 clean，ET4924d57 clean；StockWiki d4779e6/2 tracked dirty，IQSbfaf04c clean。未覆盖其他owner。
- 并行分工：R1先精确退役清单，N4A先scope接口负例；root拥有PWF/hooks与汇合。写入必须独占文件，shared Store与registry/planner分开。
- goal实读paused；工具只有get/create/update(complete/paused/blocked)，无resume/修改objective；继续已授权本轮工作，不错误mark旧goal complete。
- 初始决定：先保存计划，然后S0 TDD/退休，N4A在独占范围并行（已完成，见下文）。旧Worker仍paused，未调用provider或删除原件。

## 当前步骤

S0/N4A及S2模型预算基础、CLI阶段与CI修复已正常发布，当前CI绿；跨run节点已绿、owner/父kill/ACK整体待收口；S3英文召回已绿、其他来源默认/caps待做，S4–S6 pending。外部FF/ET/只读空间包running；不新增每文件review/coverage门。

## S0 / N4A TDD进行中

- root先取得4项确定性RED：commit重复pytest、config always_run、activation CLI无reviewer失败、restore无reviewer失败；实现自动actor记录与静态commit后，36相关测试GREEN/6.62秒，Ruff/mypy3模块通过，测试根finally删除。
- R1 agent先取得11项退休行为RED；整套退出后节点包157通过/3静态失败，真实叙述3个E2E与23个内容质量测试均绿。收敛import层级误判与B10现行metadata handoff，未弱化原件/引用断言。
- N4A agent取得19项scope初测，12项缺scope接口RED；正实施SQL先LIMIT过滤与prepared effect scope，通用状态/Store schema不改。
- root整套删除旧deletion_manifest及仅服务它的Unit/过期ignore；合法ignored凭证的旧rotation门已先RED再改，真实tracked/history泄露检测仍保留。可选prompt签名writer只服务fixture但有多个consumer测试构造，合入S3诊断协议收口，不在本批留下新签收替代物。

## Errors Encountered

- sandbox只读Git提示用户ignore/cache权限；正常用户元数据盘点正常，不修改ACL或reset。工具agent线程上限沿用现有agent，不继续创建新线程。
- 两个猜测测试文件名不存在，改用CodeGraph给出的实际activation/restore文件；rg混合显式文件和目录导致过宽输出，后续只列命中文件/精确片段。pytest插件隔离下asyncio_mode警告不影响结果；测试根已清。施工中另agent文件EOF提示交该owner收尾，不跨线修改。

## S0 / N4A集中验收完成

- root一次集成全Unit及受影响activation/restore/transcript/automation/B10合同：1161 passed /178.40s（Windows）；隔离根finally删除。该大节点不进入每次commit，提交只静态检查，CI继续现有快速组。
- R1首次157绿/3红，根因修复责任包22全绿；11退休RED与4数组元数据RED均转绿。净删约4027行；gold内容质量和三份真实叙述E2E保留绿。
- N4A相关120绿/1新增spawn夹具身份错误，修夹具后该项绿，root集成21scope全部绿。覆盖批外parent只读、空scope零事务、101早prepared及库外ACK不被本批处理。没有schema升级。
- secret ignored-local规则1 RED→9相关GREEN/17.55s；真实tracked/history泄露检测仍在。复杂度冻结及其镜像断言退出，tools/complexity_report.py只报告；不新增数值门。
- root extra mypy发现现有Spec float→Worker int秒注解不一致，统一真实支持的float秒，不截断lease。生产raw/config/control/DB未写，测试不联网、不读实际key。
- goal重新创建尝试被工具拒绝：cannot create a new goal because this thread has an unfinished goal。旧目标尚未完成，不能mark complete绕过；应用卡仍需用户侧resume，执行持续推进。
- 当前准备正常提交推送S0/N4A和PWF；S2新adapter文件若已创建不混入本次阶段提交。

## S0/N4A发布与S2模型接口

- ff5396c3a8766f557c016c30cbbf33571d67b288已正常commit/push；Ruff/mypy/host静态hook通过，pre-push精选通过，无跳过hook。CI37131769647成功，Fast checks job53秒。
- 15项usage字段先RED后GREEN：可选成对token、0有效、bool/负值/部分字段拒绝；4位置参数replay兼容，坏JSON仍可带真实usage。
- 完整schema/同语言wire示例先4 RED，prompt升级1.1.0；41项summarize/model字段包GREEN/1.62s。模型端清楚业务叙述、来源引用、角色/情态和质量诊断；不新增第二轮LLM。
- gh不在PATH/常见安装位置；改用GitHub公开API取得真实CI收据。发布前scope测试多一个EOF空行被diff-check拦住，修空白后正常提交，未绕过检查。测试独立根已finally清除。

## S2/N4节点A：持久预算与生产factory

- AUTO v3只新增run/run_jobs/reservations三表，v1/v2事实与只读classification竞态保留；当前reopen只读，旧v2明确迁移且仅一次小库backup。预算不创建第二CSV/数据库。
- 55项预算/迁移相关契约累计GREEN，含真实双spawn抢最后额度仅一份成功、kill/expired lease后预留保留、异常聚合整数上界仍记账并block。ctor不初始化/迁移生产库。
- HTTP33项真实loopbackGREEN/2.13s，无redirect/retry/fallback；truncate带已知usage、确定零HTTP的credentials具名区分，不保存响应正文或key。
- caller先7 RED，再7绿/1新storage-failure RED，修后8全绿/0.98s；settle-before-decode，未知保占额，确定未调用才0，DB结算失败保预留metrics。handler新增4 RED，45包全绿/1.43s，坏JSON/坏claim不丢已付费metrics，skip0调用。
- 请求16 RED→16绿；round-trip补1 RED修正规范金额后17绿/0.69s。1–100精确refs、折叠重复、路径在composition、integer microUSD，profile/时限/模型/费率/版本共同bind hash，secret值不进入options。
- 正式factory15项已各自GREEN含真实spawn+真实Reader零外网/原件不变；真实Reader的dict返回不协变，用只读Mapping Protocol收敛，无cast/第二Reader。6模块mypy与现行Ruff scope全绿。
- root大节点集中1241项：1238绿/3旧预期红，旧expected error tuple/v2 version+table set；同步真实v3后117责任包GREEN/13.35s。不重跑全部既有1238绿、不放宽注入/版本/lease断言。所有独立根finally清除，生产DB/config/control/raw未写。
- 尚未完成：正式batch coordinator/CLI、terminal降容、完整本地HTTP CLIE2E、真实四样本live与S3–S6。新markets/agreements业务句零召回已记S3质量缺口；不能将factory synthetic成功当真实叙述召回验收。

## S2阶段发布、正式CLI/降容与并行卡

- 节点A 9ccd29f47d7bcfac895b6ceba71db9d1aae8c524正常commit/push，静态hooks/pre-push绿；CI37135709529成功。没有stage尚在实施的CLI E2E。
- 正式CLI先6模块缺失RED→6 GREEN；OS mutex两RED→8责任包GREEN/1.99s，共用基础设施函数，进程死亡自动释放，无PID签收文件。Factory尊重请求max_final_bytes，不只写DTO。
- 新terminal/lease 24责任节点、真实62组合GREEN/36.67s，Store兼容49 GREEN，故障SQLite第二条UPDATE abort整组rollback后恢复4 GREEN/5.27s；预算/outbox不改，exact visibility/hash+三job终态后才去attempt正文，repeat只读no-op。
- 正式多文档CLI独立subprocess：P2三原件（中/英+制度skip）2真实loopback POST/184tokens/222µUSD/3可读final；同run重跑0新增POST、同refs；之后原文SHA变化具名失败且账仍222µUSD。另0费用/原文失配/4KiB空间cap三故障均0POST/no artifact，生产原件/外批READY不动。所有fixture根finally恢复原样。
- root正式集中节点 **67 passed/55.05s**，含CLI、factory、terminal、自动mutex/进程kill及既有catalog lock/runtime兼容；短根C:\cwt\n4b-node-73bd798d已finally清除。尚未验正式batch父kill/ACK窗口/跨run，不能记N4B全完成。
- CLI首次TypeError源于浅dict保tuple冻结结果，改用HandlerResult.to_dict深投影；同run时间变化put_event幂等冲突，改复用同ID且input/payload/policy/subject完全一致的stored event时间，不放松Store通用幂等。合法失败回执从原ledger读费用，不误报0。
- S3 selector 11正例RED/11负例绿→新23+既有114 GREEN，版本/架构/请求/factory70 GREEN，Ruff/mypy绿。版本0.2.0仅补明确英文业务对象/完成动词，安全港/套话/财务表继续跳过，原文和locator精确回放；parser0.1不改。
- 用户要求可交其他harness的目录独立大包。最新外仓只读核：FF c47c397真实主线、ET4924d57、RF6fb2def7四dirty/原fcap5319ee26；StockWiki推进aa98848四dirty，IQS44b805f活跃；保留owner。新增parallel_execution_plan与FF-S3/ET-S3/SPACE-S5三独立卡，ready未派、输入/输出/范围/集中测试/主线汇合写明。
- 当前get_goal实读active，应用目标已恢复；不再报告paused。未外发live key、未paid FMP/LLM、未生产DB/control/raw修改。
- root只读大节点复核发现cross-run effect/work_key与idle旧daemon所有权缺口，写入N4卡/root nextstep；外线不抢Store/worker/producer。S5审计只读报告不带删除权；三线可现在启动，FF producer caps由root补齐后联调。
- 发布前静态检查补齐两处类型表达：OS mutex用sys.platform分支供Windows/Linux类型存根正确收窄；失败预算明确允许ledger不可读时的null。6模块mypy、Ruff、diff-check均绿，未放宽运行时校验。准备把已绿阶段与三张施工卡一起正常commit/push；N4B未完成项仍由root实施。
- cf662cc2e71e9a04e96f2cc767b2cfd29e502037已正常commit/push到master，28个文件；Ruff/mypy/host hooks和pre-push精选绿，工作树clean，专用临时根finally清除。CI37139201102首次查询in_progress，未冒报成功。三卡仍ready未派；本轮不启动live批次。

## 三外线启动与CI两项确定性修复

- 用户确认FF-S3、ET-S3、SPACE-S5已全部派出；三线登记running，root只处理CWP主线与联调，不改三独占工作目录。空间卡在CWP存放，执行和输出在独立workspace，生产全只读。
- CI37139201102最终Unit两红：mutex子进程无显式src，CI没装editable，父pytest的sys.path不会继承；使用-S/cwd tmp/去PYTHONPATH先确定RED，再显式仓内src bootstrap，真实kill/重取锁断言保留。无需改锁算法或skip Linux。
- 旧worker expiry夹具直接构造Attempt默认generation0，与enabled gate不符，实际RUNTIME_GENERATION_CHANGED合理。先复现RED，改真实claim绑定当前generation，增加未过期reap=0，保留精确LEASE_EXPIRED断言；Store新分类不放松。
- 一次相关mutex/worker/runtime/terminal/catalog lock责任包54 passed/15.16s，Ruff/diff绿；agent额外worker/terminal真实集成41 passed/23.23s。短独立目录finally清除，原件/生产DB/config不动。接下来正常发布修复并继续跨run节点，不扩CI矩阵或恢复慢测试。
- a104d259923e5bf6121ac9c09d8ef6a902642de9正常commit/push，CI37139842105 success。两项远端失败已闭合；不绕过hooks或新增慢矩阵。

## S2跨run身份节点及下一owner实施

- 公开verify handler先1 RED（两job同effect ID）；正式3run CLI先RED：A完成，B partial，C OUTBOX_FAILED。修effect action hash为verify job+bundle SHA，projector work-key/2加入publication effect key；bundle本体/intended SHA/Store冲突语义保持，正文对象仍按SHA只存一份。
- 真CLI新节点GREEN/18.76s：三run各92tokens/111µUSD，三个independent versions/effects/workkeys、A/B同正文对象、C异正文，物理对象2份；B重复0新增HTTP，三旧exact pins全实读，outsideREADY无attempt、原件/sidecar/config不变，unique root恢复。
- root责任包32 passed/20.23s，升级前prepared新增夹具先因旧helper目录前缀、outbox返回dict误用失败，修fixture后该项1 passed/2.11s；旧effect继续work-key/1准备/ACK/可见，版本ID和bytes不变。Ruff/mypy2模块绿。已充分验证，不重复全部历史大包。
- 只读owner审计纠正假设：没有AUTO独立生产daemon；正式factory已拒None/空/非run scope。真正入口为catalog worker、once、start/resume、startup PS/VBS及全量normalize/run；旧周期会全局normalize/旧LLM summary且长持catalog lock。生产control为paused、runtime不存在；sandbox无法查人类计划任务，未知不报禁用。
- 下一步现有run行最小generation绑定+原库正确迁移，未知ENABLED不接管、父kill自身可恢复；退役上述旧执行入口，generic库None兼容保留、FF下载不占长owner锁。统一在节点B验owner/正式父kill/ACK及全生命周期deadline，不加手工审批/新control面。

## S2 run owner 与父进程崩溃恢复闭环

- AUTO schema v4给现有run增加nullable `last_runtime_generation`；v1/v2/v3历史迁移保持旧业务事实不变，旧启用generation无owner时明确拒绝接管。通用Store启停保持兼容；run专属`activate_run`在同一写事务检查CAS、generation和归属后绑定并fence。
- 正式batch CLI在启用gate时，先校验并恢复原run归属，再写入AUTO事件/任务；paused gate下先幂等准备原run，随后原子启用。finally只暂停自己持有的generation，unknown/别run冲突不会改变DB。
- 父进程在真实本地HTTP POST等待期间被kill：观察到真实worker退出、OS文件锁可重取、旧attempt以`RUNTIME_GENERATION_CHANGED`结束；同run CLI重启完成/预算封顶。旧请求reservation由`reserved`转为`unknown`，保留原token/费用上限、不记response hash、不退款；外批READY、原文/config保持原样。
- ACK丢失单元故障注入覆盖SQLite事务已commit但调用方收到超时：同run重试读到unknown，不重复费用结算。另覆盖active attempt不提前结算、已结束attempt幂等结算。
- 首轮53项owner/migration/recovery责任包全绿。扩展165项关联包164 passed、1 skipped；唯一失败的旧Store schema v3断言已改为v4并单测通过。最终batch/owner/正式父kill恢复22 passed/13.11s，Ruff与三模块mypy全绿。正常提交hook的host guard抓到新E2E硬编码POSIX `/proc`；改成POSIX `ps`进程表并实测Windows分支，guard新违规0、E2E 1 passed。CI将验证POSIX分支。禁用pytest plugin autoload时出现`asyncio_mode`未识别警告；该组无async依赖，CI正常加载插件，不更改pytest配置。
- 接下来完成旧source_catalog Worker/CLI启动入口退役，再汇总S2全生命周期/容量证据；之后与三条外线和root的S3 producer caps在大节点汇合。外线FF/ET/空间目录未被本组修改。
- CI37143351537唯一失败为v3只读分类测试。根因是冻结数据库夹具使用`with sqlite3.connect(...)`，该上下文管理器只提交/回滚、不关闭连接；我实测fixture返回后切换WAL模式会被旧连接以`database is locked`拒绝。改为明确commit并close；保留原WAL读路径的重复只读断言。修后53项owner/migration/recovery责任包全绿，远端修复CI待推送。

## 2026-10-03 — 旧 Worker 公共运行链退役

- TDD：新增 CLI 退役测试，覆盖 `normalize`、`summarize`、`run`、`worker`、start/resume/pause 和 install-startup 不再注册；确认 `scan/status/query/export/worker-status/worker-stop/uninstall-startup` 保留。重写 paused-guard 合同：显式 `ensure --allow-download` 与 `close-gap` 不再读取旧 Worker pause 状态，FF 外线兼容参数暂时保留为 no-op。
- 只读生产检查发现 Worker paused/stopped、进程清单为空、登录 startup 未安装。删除旧 CLI 执行分支、启动安装实现、控制菜单和 PS/VBS launcher、BG7 pilot；保留能发现/停止旧进程和卸载历史任务的诊断路径。未写生产配置、控制状态、SQLite、派生目录或原件。
- 删除旧 Windows launcher/bootstrap 专属测试及过期启动断言；保留 WorkerController 的旧 PID identity stop/process-inventory 测试与当前 finite batch 恢复 E2E。
- 相关集中测试首次 153 passed / 2 stale assertion failures（64.73s）；修正后两个失败用例 2 passed。CLI/ensure/close-gap/parser 责任包 18 passed；最终 74 项控制器/进程识别/恢复 E2E 通过。Ruff、有限 mypy 与 `git diff --check` 均通过。
- 下一步：正常提交并推送该退役节点；之后 root 独占实现 CWP ensure/close-gap 三个 producer cap，参数与 FF-S3 同步，然后进入 N4C。

## 2026-10-03 — 复核 ET-S3 / RF / producer egress 边界

- ET-S3 handoff 已独立复核：交付分支 `codex/et-s3-bounded-runtime@53e1e60` 干净；ET 离线责任组 87 passed、`/2` goldens 10 matched、Ruff clean。全量套件 150 passed / 1 failed；唯一失败为未改动的翻译器工厂测试，本隔离运行没有 LLM 后端。真实 API/key 未读取。
- ET-S3 不是最终闭环：总时长限额在同步 HTTP 阻塞/1 秒最小 timeout 下没有硬 deadline 保证；显式翻译在预算路径外；handoff 的局部 task_plan/progress 未更新实际 push 状态。该问题不改变 `/2` 交接字段，也不阻止先做 CWP 内部实现，但跨仓声称“端到端硬时限”前必须修正。
- RF owner 状态刷新：`rf-impl main/origin/main@6fb2def7` 已包含 N3a consumer 和 pipe/后代回收 deadline 修复；4个 execution_evidence 文件 dirty，严格保留。版本化 pathless read receipt 合同复用，不碰 RF 文件。
- FF-S3 已在独立 `filing-fetch-s3-limits` worktree 实际改动/加测试，仍未提交；CWP只按卡片冻结参数接口实现，不访问该 worktree写入、不把 pending 标绿。
- 发现 CWP producer 限额必须覆盖实际 transport：CNINFO `response.read()`、Dayu `_http_download()->bytes` 都没有 caller byte/cancel 控制；CWP Dayu `discover()` 通过 bulk download 进程取候选而非 metadata-only。仅 argparse/`DownloadReceipt` 后验检查会造成“看似限额、实际未限额”，不能采用。
- close-gap 当前有锁外最新期重探、锁内再探、exact stage三段；Dayu discover存在体下载副作用时可能重复下载。后续先做 capability contract 与RED测试，解决 metadata-only/一次预算贯通/失败零外发；在 provider transport可真实消费预算之前，不声称 byte ceiling 已实现。
- 复核临时目录 `.tmp-et-full-review-20261003` 已删除，外部 ET worktree未改变；本条只更新 CWP PWF，未改生产代码/数据库/原件。
- Owner boundary correction: Dayu provider code changes are cancelled. Restored the pre-existing tracked `dayu/fins/downloaders/sec_downloader.py` diff to `HEAD` as explicitly directed; its worktree now has only the pre-existing untracked `docs/architecture_report.html`. Did not create a Dayu worktree. CWP will not claim hard download limits for Dayu unless its existing CLI/API can enforce them; unsupported hard-cap requests fail before egress.
- StockInfo provider changes remain authorized but are not started. Its original worktree has a broad uncommitted adapter integration, so the next step is to establish a safe isolated snapshot containing that exact adapter implementation before touching provider code. If that cannot be done without absorbing unrelated owner work, CWP will fail closed for CNINFO under strict caps and report the missing capability.

## 2026-10-03 — FF-S3 / SPACE-S5 外包包验收

- FF-S3 仓内交付审查完成：branch `codex/ff-s3-single-request-limits` commit `8f17cbd` 已正常推送，push gate 的快速静态/配置检查全绿；责任回归358 passed/4 skipped/78 subtests，独立 CWP SourceRef CLI E2E 1 passed。新增 CI 仅跑一次精选回归，取消重复全仓/coverage与持久 `.runs` E2E。FF main 合并仍等 CWP 实际 provider budget 能力及 v1/latest_as_of 语义；远端 Actions 状态当前不可查询，记 unknown。
- SPACE-S5 交付审查完成：报告 `company-wiki-storage-audit-20261003/results/storage_audit.{json,md}`，schema `storage-audit/1`；15项工具测试通过，production mutation 为0。报告供主线拆分 S5/S6，不是自动删除清单；优先候选138,648,023 B，derived 2.826 GB先迁移，DB无free pages。
- ET-S3 状态更正：已合并并推送到 earnings-transcripts main，merge commit `93fe52c`；旧计划中仍写“running/未合main”的状态已纠正。其同步网络调用和显式翻译是否受总时限约束仍开放，不能把ET报告成硬端到端deadline。
- 测试临时目录异常如 findings 所述：3个文件、402,088 B 因ACL残留于`%TEMP%`，未调整权限，清理失败事实已记录；该测试目录未达到恢复原样。
