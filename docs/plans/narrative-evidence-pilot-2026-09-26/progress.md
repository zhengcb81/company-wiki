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

## 2026-10-03 — CWP producer budget 回执二次校验

- RED：新增 under-reporting bounded adapter，discovery先计20 B、下载产物21 B、总cap 30 B；旧逻辑未拒绝。原因是它把 receipt 与总cap比较，没有验证本次 fetch 实际记账，也没有扣除 discovery 消耗。
- GREEN：fetch 前记录累计响应字节，fetch 后要求 `receipt.byte_size` 不大于本次新增计费字节及 discovery 后剩余额度；新增 CN `JsonCommandAdapter` 子进程 marker 测试证明不支持 bounded 的 adapter 会在外发前 fail closed。5个相关测试文件最终 **35 passed / 1 existing pytest config warning**；Ruff与`git diff --check`通过。所有本轮 `.t-*` basetemp 均确认移除。此修正只挡住漏记账回执；生产 CNINFO/Dayu bounded transports 仍未实现，不能宣称真实 provider cap 已生效。
- StockInfoDLSimple 状态复核：`v2-clean-rewrite@1693045` 原 checkout 有24个tracked修改及其他未跟踪文件；其现有 `CninfoAnnouncementClient.fetch_pdf` 仍先完整 `response.read()` 再写。没有修改原 checkout；后续需先建立精准隔离快照并将 discovery 与 PDF 下载统一到一个逐块消耗的 budget。Dayu 保持未改。

## 2026-10-03 — 跨仓阶段重新核对

- 开始下一阶段前先检查 RF：当前本地 checkout 是 `fcap@5319ee263c4af41ac255938c25bebd32cce56f66`，`origin/main` 是 `6fb2def709d13bda9cfada7ecf62bfc0e3744ae2`；checkout 保留大量 `.planning/2026-09-19-three-project-history-audit/execution_runs/**` tracked 删除。本轮只读并保留 owner 工作，没有恢复、合并或修改 RF；Git dubious-ownership 用命令级 `safe.directory` 读取，没有改全局配置。
- RF 当前 PWF 根为 `.planning/2026-09-19-three-project-history-audit/`。CodeGraph 对 pathless receipt 的模糊查询没有给出规范合同，下一步从 RF main 的正式合同文件直接核实并复用，再决定 company-wiki 的接口与回归范围。
- 已直接检查 RF `scripts/contracts/evidence.py` 与 `scripts/contracts/document.py`：消费者模型将 source identity、HTTPS URL、日期、snapshot SHA 和 host/capture receipt 纳入验证；这证明的是 forecast evidence data contract。它没有声明数据湖路径，也未找到独立 pathless reader 的证据；继续定位真实 reader adapter 前不新造第二份合同。
- 随后发现本地 `fcap` 是旧 checkout，改从 `revenue-forecast origin/main@6fb2def7` 与 CWP G-C 收尾记录复核：main 已发布 `scripts/narrative_source_preparation.py` + `company_wiki_narrative_reader`，以 pathless `narrative-read-request/1` 读取 CWP source-only context；年报与英文 TXT 的 RF/CWP CLI 真实跨仓端到端已记录通过。CWP `SourceVersionReader` 已被 narrative/SourceExport v2 正式调用。前一条“未找到pathless reader”只适用于旧 `fcap` checkout，已由 findings 明确更正；RF 文件保持只读。
- 计划状态：G-C 消费接口能力已有交付，不重复实现或改 RF；N4C 的真实多文档 Worker 批处理、1/2/4并行实测、四类叙述召回/引用覆盖及空间增量仍未被该消费者 E2E 替代，S4 继续 pending。S3 仍由 CWP 的真实 provider download limits 和 FF 汇合阻塞。
- FF-S3 当前源码将 `acquisition_limits` 接入共享deadline，并含 CWP `--max-download-*` 参数适配；但 CWP 的 `JsonCommandAdapter` 仍无 `discover_bounded/fetch_bounded`，外部 provider是否逐块计费仍未闭合。接下来逐个核 FF 实际命令路径及CWP预算分流，避免把 schema/argparse通过当成实际下载限额。
- 已核 FF-S3 实际 argv：`_command_arguments()` 将三项上限附至 ensure/close-gap；v2 pathless ensure与legacy close-gap都调用它，`_shared_deadline()` 贯穿全请求。预算确实传到CWP CLI；差口是CWP生产provider transport，不是FF漏传。
- CWP bounded JSON桥接先写了RED合同：发现与fetch用同一budget，子进程收到剩余bytes/time/cost并必须返回usage；另覆盖usage缺失/超额。第一次pytest未进用例，失败在全局可选`langsmith`插件导入`pydantic_core` DLL被拒；不是项目测试红。测试根已在finally清除；接着仅本次命令禁用外部plugin autoload，继续得到真实行为RED，不改pytest配置。
- 隔离插件autoload后行为RED为3项，根因正是 bounded CLI methods不存在。实现 `JsonCommandAdapter.discover_bounded/fetch_bounded`：请求携带schema `1.0`剩余字节/秒/成本，subprocess timeout受同一剩余时限约束；输出须精确返回 `acquisition_usage/1.0`，再计入原budget，fetch收据字节不得超过该fetch本次收费。既有无预算`discover/fetch`形状未动。三条进程合同 **3 passed**；初次plugin failure与RED/Green basetemp均由finally清理，pytest cache plugin关闭以绕开ACL warning。CNINFO实际HTTP仍未启用bounded。
- 补充真实子进程sleep合同验证剩余deadline会杀掉慢provider；bounded adapter责任组最终 **4 passed / 1现有 unknown `asyncio_mode`配置warning / 4.25秒**。关闭全局plugin autoload是仅本次测试命令的环境选择，没有修改CI/pytest配置。
- company-wiki 仍有 producer-budget 未提交 WIP；上一节点35项相关测试通过，但生产 provider 响应流尚未接入硬限额。无外仓写入、无原件/生产库操作。

## 2026-10-04 — CWP / StockInfo bounded provider 节点

- CWP producer-budget 代码与新增测试已覆盖共享 AcquisitionBudget、明确provider capability、bounded JSON子进程、严格usage与部分失败计费、receipt二次校验，以及缺能力时外发前fail closed。复核发现deadline已过时仍须记录provider已报告usage，新增两项先RED后GREEN；最终六文件责任回归 **41 passed in 14.83s**，Ruff与`git diff --check`通过。pytest hook曾重定位并漏删987,840 B fixture，本轮按精确路径清除；短路径 `.t-bud` 通过finally删除。
- StockInfo CNINFO bounded transport在隔离分支 `codex/cninfo-bounded-budget@947e839`（基于 `1693045`）完成并提交，仅13个相关文件；original dirty checkout未改。focused测试此前61 passed、限定改动文件Ruff clean。今天额外51项运行到100%但退出阶段挂住并被中断，不算完整测试结果。随后GitHub API核实远端隔离分支精确为947e839，`v2-clean-rewrite`仍是父提交1693045；provider仓未发现Actions workflow。
- CWP→StockInfo CLI/client跨进程模拟HTTP E2E通过：1个候选，PDF 399 B，discovery+PDF用量713 B且精确对账；测试没有外网请求、生产目录变更，临时root已删除。
- 配置保持不变且正确fail closed：`config/source_acquisition.yaml`仍指向旧 `v2-clean-rewrite` provider 1.1.0，没有 `supports_acquisition_budget`，默认能力false。故本阶段完成provider和CWP桥接实现，不等于生产下载限额已经启用。下一步先将StockInfo分支纳入owner集成工作树，再显式配置1.2.0和budget capability，完成FF正式入口端到端及v1/latest_as_of复用语义验证，然后合入FF-S3。Dayu无改动。
- CWP budget桥接与额度计量修复已commit `288b028` 并推送；远端CI `37162544905` 已对该SHA成功。这个阶段完成的是安全fail-closed桥接，不是生产provider已经启用。
- StockInfo分支拓扑：远端bounded分支947e839是`v2-clean-rewrite@1693045`的直接子提交；默认`main@6df45a1`与v2-clean-rewrite无共同祖先。CWP原配置使用v2工作树，后续按v2集成线处理；本轮依用户授权仅清理无调用者辅助脚本和空文件，功能WIP保留，不把commit强行迁到不相关的默认main。
- 按用户要求检查 StockInfo 原 `v2-clean-rewrite` 未提交改动。`config/source_acquisition.yaml` 仍指向该目录，当前工作树中的 `stockinfo-cninfo` 1.1.0 CLI 仍是本项目配置的适配器入口；整体 restore 会让当前配置失去该入口，所以保留 adapter/client/CLI、预算分支前的源码、测试与夹具，以及 downloader/browser 的功能改动。README/config 变更与现存批量 CLI 能力吻合，`a_share_companies.txt`、`companies.txt` 保留。删除未被代码/文档引用且会绕过 pathless 抽象的 `lookup_a_shares.py`、可能按同名直接删 PDF 且已被 `save_subdir` 取代的 `reorganize_downloads.py`，以及确认的0字节 `nul`；另将11个仅有未使用import/格式调整的tracked文件恢复至当前HEAD，index未动。没有改动或移动任何原始下载资料。
- 当前脏工作树相关回归 **88 passed / 19.96s**（downloader、CNINFO API/fixture contract、adapter/CLI）。首次 pytest 自动加载全局 `langsmith` 插件时在 `pydantic_core` DLL import 失败；仅本次测试关闭 plugin autoload 后测试正常，未修改项目 pytest 配置。StockInfo 其余功能改动仍未提交；隔离分支 `947e839` 与原目录WIP保持分开，CWP仍配置1.1.0且budget capability关闭，后续集成工作仍待办。

## 2026-10-04 — FF/CWP/StockInfo 真实采集闭环并合入 FF main

- StockInfo provider隔离分支 `codex/cninfo-bounded-budget` 从 `947e839` 补上 JSON stdout 修复，提交并推送 `8ed5fdd`；聚焦 provider suite **62 passed / 0.87s**。原 `v2-clean-rewrite` owner工作树没有整体恢复或覆盖。
- CWP配置改为 StockInfo隔离 provider路径、版本1.2.0、`supports_acquisition_budget: true`；本地配置加载与 registry smoke通过。CWP限额与适配器责任集 **32 passed / 18.08s**。
- 真实CNINFO年报E2E经 FF-S3 v2入口下载BYD FY2024 PDF **10,092,140 B**，SourceRef SHA `e9c2d7fdd088e151ccb6c8ad3d95587b2b014b10f2c9731508d23ce07fde4de3` 与PDF实际内容一致。`latest_as_of + reuse_only` metadata lookup、legacy v1 exact reuse均无重复下载/原件改动；v1缺件且无budget在外发前失败。生产配置和CN身份快照指纹未变，隔离root已清理。
- E2E发现provider logger污染JSON stdout，先写回归再修复；修后测试通过。FF发现latest_as_of reuse-only仍访问provider metadata，追加request ceilings合同，FF重点回归 **23 passed / 11.72s**；本地pre-push检查全绿。
- FF-S3提交 `5b9a8c1` 已从 `origin/main@c47c397` 快进推入远端main；`Projects\\filing-fetch` 本地owner工作树也同步到 `5b9a8c1`。保留未跟踪 `config/FMP_API_KEY.txt`，未读取或暂存。FF合入后的GitHub Actions状态待查。
- 当前S3余项是确认FF发布CI、检查安装示例和采集默认/缺元数据语义；随后按总计划转N4C，做四类真实资料有限批次、摘要引用覆盖和空间增量测量。Dayu不改，不能实施bounded的Dayu请求仍外发前拒绝。

## 2026-10-04 — 修复 FF Actions 安装清单测试的工作树依赖

- FF `5b9a8c1` Actions #52/#53失败；GitHub匿名页面可见run状态和step注释，但隐藏详细job logs。按项目同一CI pytest命令本地复现为 **359 passed / 5 skipped / 78 subtests，1 failed**：`test_manifest_excludes_a_fake_fmp_api_key_file` 假定真实owner工作树不存在 `config/FMP_API_KEY.txt`，而 fcap 有用户未跟踪key，于前置断言失败。测试失败发生在读写key之前，没有读取key内容。
- 修正测试只在 `tmp_path/canonical/config/FMP_API_KEY.txt` 写入假值，并构造三个必需公开manifest模板文件；不读写真实checkout、不清理用户key。聚焦安装面 **7 passed / 4.42s**。
- 同一完整GitHub CI精选pytest命令 **360 passed / 5 skipped / 78 subtests / 52.86s**。提交 `2936ad1` 已正常快进推至FF main；本地pre-push gate全绿，远端Actions run `37167803001` 当时仍in progress。`Projects\\filing-fetch` 本地owner工作树同步至该提交，未跟踪key仍保留。
- 更正：上述是本机安装清单测试的独立环境脆弱点；不能据此断言GitHub Actions根因。Actions #52/#53/#54实际失败于mypy step，真实根因及修复见下节。

## 2026-10-04 — 修复 FF Actions 的 Linux mypy 失败

- Actions公开 Jobs API确认 #52/#53/#54都失败于第7步 `Strict type check on public contracts (FC-1204-c)`，pytest步骤被跳过。Python 3.12.12/mypy 1.19.0 Linux目标复现：`scripts/transcript_tool_transport.py:100` 无保护引用平台专有 `subprocess.CREATE_NO_WINDOW`；Windows默认目标本地类型检查通过，掩盖了Linux平台存根问题。
- RED新增缺少该常量时的creationflags合同；改用 `int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0` 后GREEN。新增回归1 passed，Python 3.12/mypy 1.19.0 `--platform linux` + CI CWP `PYTHONPATH` 返回 no issues。
- 完整FF CI精选pytest命令 **361 passed / 5 skipped / 78 subtests / 48.97s**；正常pre-push gate全绿。提交 `1d0c73c` 已从 `2936ad1` 快进推入main；fcap工作树同步且保留未跟踪API key。Actions #55 `37182527153` 已 completed/success；根因修复经真实远端workflow验证。
- `2936ad1` 的假key测试改造仍保留：它解决了本机key工作树上的真实测试前置条件脆弱点，但不是GitHub Actions失败根因。

## 2026-10-04 — FF-S3 技能安装同步

- 检查发现 FF 主仓推荐 schema 2.0 技能说明与两个实际安装副本不一致，`.agents` 和 `.codex` 各有10项manifest漂移。
- 运行 FF allowlist installer 后，两个目录各报告 **MATCH 11 files**；再次 `--check` 均匹配。旧测试夹具/cache只从这两个 skill 目录按manifest清理；`filing-fetch/config/FMP_API_KEY.txt` 仍为未跟踪原样，未读取。
- 一次锚定尾行的PWF补丁因上下文不匹配而未应用、未修改文件；改为UTF-8追加。本次工作树状态另行核实。
- 下一步核对 CWP `latest_as_of` 遇到缺失 `published_date` 的处理：这是核心时序字段，不能被当作可忽略缺省值或据此声称latest已命中；然后决定S3是否收口并转N4C。
## 2026-10-04 — latest_as_of 缺失发布时间语义

- 代码复核确认：无 `published_date` 的候选会被 latest-as-of 排除；仅有这类匹配来源时返回 `AMBIGUOUS / matching_sources_have_unknown_published_date`，不会伪造“最新”结果。source classification也不会仅凭年份捏造完整发布日期。
- 现有latest合同测了排序和cutoff，没有单测该缺失日期路径；下一步先加一个短合同回归，运行该测试确认当前实现，再按来源默认/FF响应语义完成S3大节点校验。
## 2026-10-04 — latest_as_of 缺失日期合同测试

- 新增缺失 `published_date` 回归，确认 resolver 不会用无日期的匹配文件满足latest-as-of；只报 AMBIGUOUS + `published_date_unknown` trace，四项latest模式测试 **4 passed / 0.75s**，无生产实现变化。
- 测试环境的外部pytest plugin DLL加载失败、默认Temp目录ACL枚举失败均发生在测试执行前；改用唯一短路径 `.tla-1004` 并禁用外部插件/cache后执行成功。pytest hook另生成的唯一Temp测试树已按精确路径清除；本轮短根不存在，测试文件使用临时目录且已自动清理。
- pytest.ini 的 `asyncio_mode` warning因单次禁用插件而出现，未改配置。下一步核对 S3 剩余指纹/缺省合同，完成后刷新阶段状态并转 N4C。
## 2026-10-04 — R2/R6 合同复核

- 对照激进方案细则厘清两个语义：缺非核心采集描述/局部摘要覆盖可标partial；缺 `published_date` 时不能满足latest-as-of，现为AMBIGUOUS并已加合同测试。finalizer的partial依赖coverage/预算遗漏，真实来源时序仍由resolver负责。
- `VerifiedVersionReceipt` 已有pathless source ID/SHA/size/read-at及policy pin字段；尚需确认policy fingerprint输入是否只含本次读取实际依赖配置，并查其测试。
- 审计过程中曾在company-wiki cwd读取FF相对测试路径导致FileNotFound，改到filing-fetch checkout后继续；无文件变动。
## 2026-10-04 — read-policy fingerprint 调查

- CWP `source_read_policy_sha256()` 当前直接对整个 `CatalogConfig` 的 `asdict` 和runtime snapshot SHA取哈希；现有合同证明admission配置/activation变化会变，但未证明无关配置变化不会变。它可能超出R2的最小依赖绑定目标。
- 下一步查CatalogConfig真实字段和现有fixture，再判断是否要窄化hash输入以及增加“相关配置变更拒绝、无关配置变更仍可用”合同测试。
## 2026-10-04 — read-policy 范围更正

- `CatalogConfig`只有project/catalog位置、RootSpec列表、可复用root kind四项；RootSpec本身承载来源路径、准入/版本/路由/边界等source读策略。现有合同测试覆盖多项相关变更。故当前hash全量取CatalogConfig并未证明夹带日志、批大小等运行设置，不擅自重构。
- 下一步只核 runtime snapshot hash 是否包含纯时间字段等无关变化；如果没有具体不必要输入，保留现实现并在S3计划说明其范围，而不是为“最小”泛化出新合同。
- 两个CodeGraph测试节点按名未找到，直接读取对应测试文件补足证据。
## 2026-10-04 — 定位 runtime timestamp fingerprint 候选

- 确认runtime snapshot自身SHA包含 `updated_at`；reader pin又直接包住该SHA，因此一个纯更新时间会使verified-open pin变化。它很可能不是读取实际依赖项。
- 将按TDD核Resolver消费字段；准备只对read-policy pin排除更新时间，保留runtime snapshot原schema/hash以及真正影响准入的flags/epoch/cohorts/policy hash。
## 2026-10-04 — reader pin 依赖集合确定

- CodeGraph解析 `resolver_visibility` 后确定 SourceResolver消费范围仅为reader模式、epoch、active cohorts和legacy bridge；SourceReader还复核当前RootPolicy `policy_hash`。其余snapshot flags及`updated_at`不参与这次读取。
- 当前read pin全量包住snapshot SHA，确认会让无关扫描flag或纯更新时间触发pin drift。下一步按TDD先补相关/无关字段两组测试，再把read-specific fingerprint收敛到实际消费字段；不改runtime snapshot存储哈希或root config admission pin。
## TDD 运行记录：read-policy 反例 fixture 初次被schema拦截

- 新 RED 用例第一次未触及fingerprint断言：fixture将 `v2_scan_shadow=false` 与 `v2_persist_assertions=true` 组合，runtime snapshot校验拒绝该不合法依赖（persist assertions requires scan shadow）。没有项目行为失败或配置写入。修正为有效成对变化后重跑。
- 第二次fixture调整仍未执行目标断言：把 `v2_persist_assertions` 关闭但保留 `v2_resolve_shadow=true`，又违反snapshot前置关系（resolve shadow requires persist assertions）。停止猜flag组合，先读取validator约束，改用独立无关flag变化。
- Validator代码复核找到前述flag依赖链：`persist_assertions→scan_shadow`、`resolve_shadow→persist_assertions`、`resolve_active→resolve_shadow`、`bundle_active→resolve_active`。第三次RED尝试将采用全关闭有效基线；测试有效启用reader时只打开完整依赖链，不再用无效组合探路。
- 用合法全关闭基线重跑后，目标测试按预期RED：只改 `updated_at` 并启用无关 `v2_scan_shadow`，完整runtime snapshot SHA改变，当前read pin也错误地从 `2b111c…59fc` 变为 `0d2f7f…2dba5`。测试触及目标断言；没有生产库或config写入，basetemp已清理。
## 2026-10-04 — reader-specific policy pin实现与验证

- 先有目标行为RED：timestamps/scan flag使read pin变化。将`resolver_visibility_projection`放在runtime policy层，SourceResolver仍通过兼容`resolver_visibility()`返回相同tuple；`source_read_policy_sha256()`改为绑定CatalogConfig + snapshot schema/policy hash/有效resolver visibility，不再绑定不相关flag与`updated_at`。运行时snapshot完整SHA仍由load_runtime_policy校验。
- read policy + version reader + activation snapshot + latest-as-of合同 **58 passed / 5.10s**；通用SourceResolver合同 **13 passed / 1.68s**；Ruff、`git diff --check`及PWF claim检查均通过。测试仅因本机全局plugin/Temp ACL使用仓内唯一短basetemp与禁用外部pytest plugins/cache；短根已清理。唯一warning是该环境禁用pytest插件后`asyncio_mode`未知，不影响所选同步合同。
## 2026-10-04 — FF/ET companion wiring review

- FF schema 2.0 documents exact fiscal year+quarter, separate transcript caps, unchanged source language, no inferred Q4, and independent failure behavior. The two active local skill installs now carry that same canonical v2 protocol. FF tests invoke a subprocess fixture for the tool/SourcePayload contract.
- Before declaring the FF+ET edge fully exercised, check current earnings-transcripts main/working-tree and configured entry-tool availability; no live transcript acquisition is claimed yet.

## 2026-10-04 — AUTO approval API cleanup (CWP G1 first tranche)

- Retired the unused public `Approval` / `ApprovalDecision` model exports and `AutomationStore` approval CRUD. Source-level caller review found no live production workflow using these APIs; `remediation.approval_id` is a separate historical remediation field and was left unchanged.
- Kept the SQLite `approvals` table and migration intact. Added a regression that writes a valid historical approval row linked to an event/job, reopens the store, and confirms the row survives; no production database was opened or modified.
- TDD focused suite: initial API assertions went RED as expected. The first preservation fixture was correctly rejected because it violated the table foreign key; the fixture was corrected to create valid parent rows. Final relevant suite: **148 passed / 10.63s**. Changed-file Ruff and `git diff --check` passed. pytest needed `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and a workspace-local short basetemp because a global `langsmith` plugin DLL and the default Temp ACL prevent test collection here; no pytest/CI configuration was changed. All `.tga*` scratch roots were removed.
- This is one CWP cleanup slice, not completion of the 46-item cross-repository gate audit. Next: close remaining S3 examples/metadata semantics, then prioritize G1 gate cleanup before N4C. External repositories remain read-only and owner-scoped.

## 2026-10-04 — Prompt-review storage failure is diagnostic on resolver export

- TDD added `test_pi10_review_storage_failure_is_diagnostic_not_export_blocker`. It failed before the fix: `build_resolution_envelope()` propagated `PromptInjectionReviewError` from optional prompt-review metadata and aborted an otherwise valid export.
- Resolver now catches the review-specific store error and SQLite failures, reports `not_reviewed`, and continues building the source envelope. SourceRef/hash identity and other source qualification checks are unchanged.
- Resolver envelope plus SourceVersionReader regression set passed **35 tests / 8.10s**; Ruff on the changed code/test passed. The one pytest warning is the known `asyncio_mode` warning caused by disabling the incompatible globally installed pytest plugin; no project config changed. The short scratch root was removed.
- At the time of this fix, the signed receipt writer and TTL evaluator were still present; they were subsequently retired in the next G1 slice below. This entry records the storage failure fix only.

## 2026-10-04 — Retire prompt-review signature and TTL machinery (CWP G1)

- The prompt review writer had no production callers. Removed its Ed25519/trust-root/signature and disposal authorization path; `detected_and_ignored` is now a scanner-bound diagnostic that requires no human authorizer. The 30-day review-cache TTL/evaluator, cache-state machinery, and stale read-chain candidate entries were removed.
- Kept `scan_text`, source/evidence hash binding, its optional metadata write, and the legacy receipt reader so existing source status can still be shown. SourceReader/resolver expose it as optional diagnostics; resolver database failure now returns `not_reviewed` and does not interrupt a valid export. Raw SHA, identity, period, root, and configuration checks were not changed.
- Updated the old shadow assertion test descriptions so they no longer claim an unreviewed source blocks consumption. Updated latest-as-of CLI fixtures to declare bounded discovery support, return usage, and pass explicit 5 MB / 90-second / $0 limits; this keeps the existing bounded-provider contract test valid.
- TDD retirement tests initially RED on the required authorizer and TTL API. Final focused suite: **110 passed / 59.78s**. Ruff passed on all changed Python files; `git diff --check` passed. A transient earlier run exposed the stale fake-provider fixture and was corrected without relaxing budget enforcement. Test scratch roots were removed. This is a CWP G1 tranche; the full gate inventory and cross-repository owner queues remain open.

## 2026-10-04 — Remove the last manual reviewer field from legacy activation mapping

- CodeGraph/caller review found `map_existing_activation` had no production caller and was the only activation path still requiring a typed reviewer label. Activation, rollback, restore, and their CLI already accepted an omitted reviewer and filled the actor from the current process user.
- TDD added a regression for omitted and blank labels; it first failed because the keyword was required. The mapping now uses the same `operation_actor()` fallback. It still requires an explicit reason and keeps transaction, assertion state, and policy-hash checks.
- Activation plus restore focused contracts: **22 passed / 2.58s**; Ruff passed. The pytest scratch directory was removed. This closes the reviewer-required part of G1 item #1, not the full gate audit.

## 2026-10-04 — Reprioritize PWF and prepare an isolated ET live-import lane

- Reordered the master plan explicitly: G1 gate/sign-off simplification first; S3 SourceRef/SourceExport virtualization second; N4C real multi-document batch after both. Clarified that IQS intentionally treats company-wiki as an optional read-only deep-research link, so it is not forced into document download/source consumption.
- Refreshed the cross-repository snapshot from read-only Git status: RF `rf-impl@6fb2def7`, RF fcap `5319ee26`, StockWiki `3a3d061`, IQS `6a8b8f3`, FF `1d0c73c`, ET `93fe52c`; owner worktrees remain dirty, so no external code-writing lane is safe to dispatch.
- Added the standalone ET-LIVE acceptance card. It permits at most one real transcript request, no translation, uses a brand-new temporary CWP root, checks SourceRef/SourceExport pathless reading and raw SHA/size, and writes only its unique result report. It can run alongside G1 because it does not change code/config; any fix waits until G1 closes.
- `verify_plan_claims.py --plan-dir .` and `git diff --check` passed after the PWF refresh.

## 2026-10-04 — Publish the G1 tranche and refresh N4 handoff order

- Commit `1cfec10` pushed to `origin/master`. Pre-commit Ruff, contract mypy, host-assumption guard, the fast contract push gate, and plan-claim verification passed. GitHub Actions run `37188829582` completed with `success`.
- The machine-specific `config/source_acquisition.yaml` provider path remains local and was excluded from the commit; it points to an isolated StockInfo integration worktree and needs a portable provider location before publication.
- Corrected the N4 detail card: N4A/N4B acceptance is complete; N4C remains pending and now explicitly follows G1 and S3. This prevents the detailed card's older sequence from overriding the master plan.

## 2026-10-04 — 本轮PWF重审与两个独立代码施工包

- 按用户要求固定MAIN顺序：G1门禁/签收精简→S3抽象层虚拟化收口→N4C真实多文档/并发/空间→S5/S6。本轮只改计划文档，不改生产代码、配置、原件或数据库。
- 正常用户Git复核CWP仅本机provider配置dirty；RF rf-impl242项与fcap2项分别记录，FF/ET已合提交复用，保留各owner未提交记录。`get_goal`仍active。
- 更新task_plan、46项清单当前安排、并行总计划与N4细卡；修正“未commit”、陈旧FF/ET HEAD、将N4C反写成N4B未完成、以及末尾旧下一步。已交付三施工卡增加醒目完成标记，不再重派。
- 新建 `gate_simplification_closeout_2026-10-04.md`、G1-LEGACY及ET-DEADLINE代码卡，冻结独占目录/写集/接口/TDD/集中测试/交接；ET-LIVE移到独占验收目录并澄清真实链范围。用户尚未登记启动，状态保持ready。
- root下一实施是filing_reuse非核心字段阻断TDD，其后清叙述capture cutoff；G1-LEGACY可以同时施工，ET-DEADLINE提前准备但合入排S3。MAIN独占共享来源核心、CLI/合同、配置发布和最终跨仓接线。
- 文档核验：`python tools/verify_plan_claims.py --plan-dir .` GREEN（11个plan）；`git diff --check` GREEN。本轮纯Markdown，不重复已绿业务测试，不增加小节点审查；本机provider配置继续排除于提交。
- 包级复核补足ET-LIVE的现行四字段import envelope、调用前SourceRequest/request_id及临时catalog配置，避免唯一一次取数后导入必然失败；ET-DEADLINE明确硬保证为worker采集终止，parent有界验证的返回开销不虚报为可抢占。
- 本轮发布提交以 `Clarify gate-first plan and isolated harness packages` 为Git标识；仅13份计划/卡片/进度Markdown，本机provider配置排除。总计划与卡片ready状态不代表外部harness已启动；用户可直接交出两个代码包，MAIN统一合入。


## 2026-10-04 — G1来源open与叙述日期第一组实现

- 先RED：缺URL/HTTP provenance/缺collector仍可verified raw、公开日在cutoff之前但capture在之后仍可叙述回读。初次叙述夹具误传SourceRefValue触发TypeError，改用真实reader.query_ref后得到目标source_after_as_of红灯。
- 生产实现移除这两项非核心资格门，保留真实SHA/身份/期间/公开cutoff；稀疏candidate不再丢已知字段，capture_ready仍False。坏字节反例验证门禁简化没有绕过raw hash。
- 来源reader/latest-as-of/叙述第一组56 passed / 29.81s；包含候选CLI与稀疏字段新行为的最终集中责任包64 passed / 57.25s。mypy暴露optional dict收窄问题，改为逐值校验后2个修改模块mypy GREEN、稀疏候选定点复跑1 passed；Ruff GREEN。
- G1整体仍in_progress：正式resolver/gap_plan/canonical_writer与FF重复资格门是下一动作。没有修改外包G1-LEGACY/ET-DEADLINE写集、其他owner树或生产原件/数据库。本机provider配置继续排除提交。
- 两外包包登记dispatched，ET worktree已创建；没有将目录存在当运行进程证明。旧runtime未清理，原正式ET main保留。


## 2026-10-04 — CWP resolver / planner / canonical 消歧收口

- TDD先红：`SourceResolver.resolve` 对有原文但缺URL/collector的期次资料返回MISSING；qualification envelope因此没有来源handle；`build_gap_plan`过滤capture_ready=false；canonical writer在provider身份有歧义时仅因capture_ready=false拒绝了匹配本次提交SHA的版本。
- 实现让身份、期次、公开日和候选字节校验决定复用。resolver不再因采集描述丢弃已验证候选；gap planner删除`_usable_handles` helper；canonical writer用receipt SHA、source_id与provider身份消歧。capture_ready与preview/gaps仍作为诚实诊断。
- 集中责任测试：`test_source_catalog_resolver.py`、`test_r4b06_qualification.py`、`test_zr406_gap_plan_orthogonality.py`、`test_source_catalog_gap_plan.py`、`test_source_catalog_canonical_writer.py`、`test_source_operation_v2.py`共100 passed / 9.03s。原件SHA/size、identity/period/publication/future cutoff保留；随后在发布门继续跑Ruff/mypy/hook。
- RF先行核查：main@6fb2def7；fcap@5319ee26，merge-base ee0a82bfd1eec935cf4e567eb42f0ef79efa0226。main侧后加SourceRef v2消费代码尚未进入fcap；支线没有在merge-base后改这些源消费者文件。本轮不改RF，未来合支线需保留main的pathless verified-open链路。
- FF核查：正式checkout fcap@1d0c73c2只有未跟踪API key，本轮未读未改；已有`codex/transcript-companion@29085f7`工作树改动`fetch_filing.py`/`filing_contracts.py`，与剩余SourceRef v2资格门重叠。先协调这条现存工作线，不并发改FF同文件。
- G1未完：CWP reader/as-of/resolver/gap planner/canonical writer门已收敛；FF v2 consumer和G1-LEGACY外包旧入口收口还在前面。未改RF/FF、外包目录、原始财报、catalog数据库或本机采集配置。
