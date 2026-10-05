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

## 2026-10-04 — 外包工作树状态与ET样本占用复核

- 只读检查G1-LEGACY：分支实现提交 `1cf8183` 基于 `1cfec10`；交接文件仍未跟踪，尚非完整commit/push交付。交接报告称责任包142 passed、Ruff通过；共享合同包另有1条旧断言仍期待环境变量能放行旧入口（其余25项通过）。主线合入时需按已批准的新静态策略改该合同断言，并在合并代码上集中跑受影响责任包；没有提前改外包写集。
- 只读检查ET-DEADLINE：worktree仍基于 `93fe52c`，`scraper.py`、`transcript_tool.py`、`test_batch_runtime.py`已修改，worker/supervisor及专属测试/PWF为未跟踪；这是活动中的未交付实现，不能当完成包或清理。
- 实测正式ET main、旧runtime、新deadline三处各130个transcript文件，每处15,953,731 B，按相对路径SHA-256全部相同；两个worktree额外重复31,907,462 B。旧runtime提交 `53e1e60` 已在main历史内且Git工作树干净，暂不删除其本机配置/缓存；这项重复量只占约30.4 MiB，不能解释CWP的数十GB占用。
- RF `fcap@5319ee26` 只读检查遇到当前sandbox账号对 `.planning/.../execution_runs` 的访问拒绝；Git输出大量表观删除项并伴随2个assurance文件变化，无法区分真实删除与不可访问路径。本轮未恢复、删除或合并RF内容；原先“两项dirty”的快照在当前账号下无法重新确认，后续需在有权读取这些目录的owner上下文核实后再做RF合支判断。
- CWP生产代码、raw原件、目录数据库和本机provider配置均未改；本轮只补充PWF实测记录。

## 2026-10-04 — RF fcap 权限表象复核

- 随后获准以只读提升权限复查RF：`fcap@5319ee26` 的tracked status为0个删除、2个修改（仅 `assurance/runs/weekly_alert.jsonl` 与 `weekly_manifest.json`）；此前`.planning/.../execution_runs`的大量表观删除来自普通sandbox账号的目录访问拒绝。样本路径现可读取。本轮仍未修改RF任何文件，恢复原先“两项tracked dirty”的判断。

## 2026-10-04 — G1门禁收口并转入S3电话会真实导入

- RF先行只读复核：`revenue-forecast@fcap/5319ee26`经提升权限核实仍只有2项tracked变更（`assurance/runs/weekly_alert.jsonl`、`weekly_manifest.json`）；普通sandbox访问拒绝曾把执行记录显示成大量假删除。RF/StockWiki/IQS owner树均未改。
- FF隔离工作树先以两条RED合同证明：pathless SourceRef v2缺`https_url`、provider/collector/retrieval描述或`capture_ready=false/缺失`时仍会被外层拒绝；实现后保留hash、SourceRef ID、公司/证券、期次、公开日/as-of校验，仅将采集完整度字段降为诊断。旧pathful v1 `validate_handle`未动。
- FF责任集最终 **177 passed, 1 skipped, 39 subtests**；唯一skip为本机没有生产security-master快照。Ruff、diff check通过；正常push gate的ruff、compileall、import、contract mypy、host/config/plan/BOM检查全GREEN。提交`e1eda60`从当前`fcap`快进并推送到远端`main`；push返回`1d0c73c..e1eda60`。
- CWP→ET→CWP确定性端到端先暴露临时根叠加长规范文件名导致Win32 MAX_PATH超限，准确栈在`canonical_writer._atomic_copy`打开`.importing`临时文件时`FileNotFoundError`。只缩短E2E临时根名字，保留导入/原文SHA/selector/去重/字节漂移断言；`test_transcript_provider_full_chain.py`加`test_transcript_import_cli_e2e.py` **12 passed**，临时测试根自动删除。CWP产品写入逻辑没有改。
- 通过CodeGraph重新分类G1清单：`CloseGapBinding`、`archive_retired_evidence`、`prune_retired_evidence`以及旧`llm_summarizer.summarize_catalog_with_llm`未发现生产caller；因此不存在当前公开流程要求用户手工准备binding文件。canonical `NarrativeSummarizeHandler`按SourceRef ID/SHA、语言与evidence span校验，不走旧禁词regex。旧未调用能力进入S5/S6 caller清理，不挡G1；source SHA/身份/期间/公开日/可回放引用和不生成投资结论的职责边界继续保留。
- G1大节点完成；S3进入真实ET工具→临时CWP导入→SourceRef/SourceExport pathless回读。ET-LIVE卡明确最多一次取数、不翻译、保留原始语言；ET-DEADLINE仍在独立worktree施工。当前CWP端到端用fake provider、FF companion用确定性工具测试，均不能冒称真实ET live。

## 2026-10-04 — ET-LIVE单次实测与ET-DEADLINE集中验收快照

- RF先行只读复核：fcap@5319ee26，tracked仅assurance/runs/weekly_alert.jsonl与weekly_manifest.json两项修改；FF为fcap@e1eda60（未跟踪API key留存未读）；ET正式main为93fe52c（两个用户未跟踪文件保留）。没有更改这些owner目录。
- CWP transcript importer确定性测试 7 passed / 11.30s；FF companion/transport 17 passed / 7.65s；pytest缓存关闭、bytecode关闭，两个独立TEMP basetemp均删除。
- 按已授权仅调用ET/FMP一次：MSFT US FY2026 Q3、英文原语言请求、10秒与1,000,000字节上限。ET返回unavailable/provider_entitlement_required；读取实现确认这是FMP HTTP 402映射，一次GET、redirect关闭、没有重试。工具wire没有回传http_status字段，因此报告按映射记录402。无正文，CWP导入与SourceRef回读为NOT RUN；不购买或重复调用。
- 临时CWP根用系统TEMP下随机et-*新目录，唯一配置只指向该根；cleanup PASS、根确认消失，生产source_catalog.yaml和source_acquisition.yaml散列未变。独占验收报告：C:\Users\郑曾波\Projects\company-wiki-et-live-20261004\report.md；报告不含正文/密钥。
- 只读ET-DEADLINE集中责任包按卡执行，91 passed / 1 failed / 51.46s，测试scratch恢复。唯一失败test_tool_worker_failure_never_leaks_key_or_body把build_failure="RuntimeError:boom"当成worker退出；异常发生在transcript_api.fetch_transcript捕获范围内，正确回传provider_error/unexpected_provider_failure，并非supervisor收到worker退出。真正的异常退出已有runtime单测（SystemExit:7）证明映射为worker_failure；e2e夹具应改为真正worker退出后复跑。独立worktree仍未提交，主线未改其写集。
- CWP唯一本机未提交项仍为config/source_acquisition.yaml，未暂存。CWP本轮只更新总计划/进度/发现/验收卡并修正ET-LIVE报告状态，不改生产代码/配置。
- 随后用一次独立TEMP、假provider正式CLI检查真正worker异常退出映射：初次临时脚本漏设stdin，得到invalid_json后立即修正脚本；修正版以SystemExit:7让子进程真实退出，CLI返回provider_error/retrieval_worker_failure，无key/body泄漏且worker临时目录为空，父TEMP根清理完成。无项目代码改动。
- provider配置审查确认现有${PROJECT_ROOT}/${PYTHON_EXECUTABLE}变量已处理CWP与Python解释器定位；唯一脏差异是用户本地把CNINFO adapter指向隔离集成worktree并标记budget能力。保持该设置不动；CNINFO进入稳定StockInfo checkout后只校正adapter路径，不新增根路径解析层。

## 2026-10-04 — N4C真实样本来源预检（只读）

- N4C仍按总计划等待S3收口；本次只用read-only catalog/API预选真样本，没有启动Worker/模型、写数据库或复制原文。
- 金山云2025年报、2025中报和2026年3月季报构成同公司可见财报组；前两份已有parsed/normalized/summary工件，季报尚无spans/派生物，正式批次必须区分复用与新处理增量。
- 三七互娱2026-05-11 IR记录经SourceRef narrative_derivation读出、验证133,294 B SHA，实际包含游戏储备、重点品类和海外上线等信息，也重复出现一般性模板话术；但当前v2 `describe_version` 返回`metadata_not_visible`，未满足pathless export入场条件。
- catalog内229份招股书全为retired；其中盛美上海招股书7,073,891 B的记录和原件位置状态均retired，不通过物理路径绕过。7条active电话会记录为旧PDF/JSON而非ET TXT；ET-LIVE仍因HTTP 402未导入。
- N4C细卡已新增逐项入场要求：先通过既有source admission得到active、v2 metadata可见且字节SHA匹配的IR/招股书/ET TXT；若未就绪，阶段如实保持pending。下一步仍是验收ET-DEADLINE交付并完成S3确定性联调。

## 2026-10-04 — RF接口复核与IR来源门诊断

- 实施下一步前先只读检查RF：`origin/main`=`rf-impl main@6fb2def7`；`fcap@5319ee26`只有weekly alert/manifest两项dirty。RF main工作树还有owner未提交的规划/证据改动，全部保持不动。RF没有CodeGraph索引；没有为本次任务向RF写入索引。
- 确认复用RF已发布接口而非重造：财报消费用`SourceRef/2.0` exact ref、CWP pathless `filing_reuse` CLI、RF bytes SHA/size + identity/period/publication/as-of校验；审查状态仅诊断。RF叙述reader `narrative-read-request/1`面向已有叙述工件，走有限只读子进程传输，不替代CWP的raw/source处理。
- 只读SQL查明三七互娱2026-05-11 IR没有任何`source_metadata_assertions`，现有`metadata_json`只有scanner/acquisition字段。当前v2不可见的直接原因是缺normalized assertion，而非活跃状态或字节验证失败。通用upsert新建的是shadow assertion，激活流程单独依赖epoch/cohort/policy snapshot；已将其列为G1剩余复杂度审查项和N4C入场路线设计点，不绕开或直接写数据库。
- ET-DEADLINE worktree仍为`codex/et-s3-deadline@93fe52c`且代码/测试未提交；当前PWF未更新、无handoff文件。最新观测到代码文件修改时间为本地10:59，不能据此断言harness终止。保持外线写集不动，S3仍pending。
- 本轮只有证据收集与PWF更新；无代码测试需要重跑。待提交前执行`verify_plan_claims.py`和`git diff --check`，只提交本次计划文档，保留`config/source_acquisition.yaml`用户本地变更。

## 2026-10-04 — Sparse SourceExport implementation

- CWP `SourceVersionReader.describe_version` now permits a pathless sparse manifest when v2 capture metadata is absent; absent display/provenance/period fields remain null. `filing_reuse` still rejects the same incomplete financial source.
- TDD: focused reader/export tests RED for the intended block, then **34 passed / 10.00s** after the narrow change. Synthetic CLI E2E verifies source ID/SHA/size, grounded span, no raw-body leak, and unchanged scratch tree.
- Pytest scratch cleanup was verified: the first long basetemp was relocated and its exact run directory manually removed; the successful rerun used short unique `tmp/pt1004b`, `relocated=false`, and that directory was removed after the test.
- Remaining sample gate: the IR can now be represented as a sparse manifest but batch creation still requires language metadata. Next implement deterministic language resolution from the exact opened SourceRef bytes, bind it into the event hash, then prove through isolated Worker/consumer E2E before N4C real batch.

## 2026-10-04 — Sparse SourceExport published; ET deadline still open

- Commit `48d3a9d` pushed to `origin/master`. Pre-commit Ruff, contract mypy and host assumption guard passed; pre-push fast contract smoke passed. Local/remote HEAD match. Preserve the one user-owned dirty config file, `config/source_acquisition.yaml`.
- Read-only status check of `earnings-transcripts-s3-deadline` confirms the actual deadline worktree is still uncommitted at `93fe52c`; `s3-et-runtime-handoff.md` inside it describes the earlier runtime package, not this deadline work. Do not merge or clean the active worktree before its dedicated handoff and focused acceptance.
- The two ET work directories serve separate stages: completed runtime integration (already in main history) and later deadline hardening (still WIP). Remote Actions was not checked because `gh` is unavailable; pre-push GREEN is not a claim that remote CI completed.
- Next: accept the deadline-specific commit/handoff, run its consolidated tests plus golden check, then close S3. The N4C language-resolution issue remains planned and is not yet implemented.

## 2026-10-04 — G1-LEGACY验收与稀疏language桥收口

- G1-LEGACY复核：隔离分支`codex/g1-legacy-entry-retirement@c3209ee`干净并跟踪origin；实际实现提交`1cf8183`已作为`6394271`第二父提交合入主线。主线结果报告与外包`docs/implementation/g1-legacy-entry-retirement-handoff.md` SHA-256相同；分支额外的局部PWF/交接提交没有待合入生产代码。
- 在干净G1 worktree重跑责任包 **142 passed / 58.05s**；Ruff与`git diff --check 1cfec10..HEAD`通过。主线接手合同、clean-env与config-doctor测试 **44 passed / 10.40s**。一次直接在当前主工作树运行G1写集检测时会把本机`config/source_acquisition.yaml`及当前未提交的narrative改动列为超出G1写集；该检查属于预期的dirty-worktree保护，故改在干净外包worktree复跑并全绿。初次无显式临时根的pytest还受到当前sandbox对系统TEMP ACL的限制；成功验收使用隔离basetemp，测试目录在结束后清理。
- N4 sparse language bridge聚焦包 **23 passed / 41.06s**，覆盖中文/英文/混合电话会TXT、年报PDF、有/无语言元数据、低价值IR skip、Worker真实CLI+本地模型、重复执行不增模型请求及raw夹具不变。Ruff与mypy聚焦检查通过。未运行生产N4C批次，未改catalog/raw/本机来源配置。
- 计划同步：S4仍pending，但“缺少从verified SourceRef字节推导language”的阻塞已关闭。剩余N4C工作是S3/ET-DEADLINE收口、为真实多类型样本取得符合现行admission/import合同的SourceRef，再测consumer引用/语言覆盖、1/2/4并发吞吐和总空间增量。当前IR normalized assertion、retired招股书及ET 402分别仍是样本资格/可用性缺口；不绕过合同。

## 2026-10-04 — ET-DEADLINE 只读交付验收

- 接收并核对 `docs/plans/repository-state-audit-2026-10-04/results/earnings_transcripts.md`。ET main=`93fe52c`；ET-DEADLINE=`0017f24`，对照本地refs，deadline branch-only为1个提交且远端分支SHA一致；main无tracked修改，两个owner未跟踪资料及两个linked worktree均保留。
- ET-DEADLINE handoff记录92项责任测试、全量172 passed、10 goldens、ruff与diff检查通过；这是交付报告中的既有结果。本次只读盘点未运行测试，且没有独立CI链接。旧progress里的“待commit/push”已经过期。
- ET只读审计包验收通过；ET实现提交暂不并main。下一节点是隔离fake-provider的FF→ET正式CLI/supervisor→CWP importer/SourceExport联调，特别检查FMP 26字段JSON与CWP当前Motley 24字段exact-key差异；不改变ET wire、不请求付费API。
- 本轮没有修改ET、FF或RF；CWP既有未提交配置 `config/source_acquisition.yaml` 保持原样。

## 2026-10-04 — 并线前 FF→ET→CWP 联调门细化

- 按用户要求，在总计划中把该联调列为ET-DEADLINE合入前的明确必过节点，不再只作为一句后续建议。
- 细则固定使用FF正式调用入口、ET正式CLI/supervisor/worker和CWP importer/SourceExport真实路径，provider侧使用fake HTTP；包含FMP golden与已知26字段/24字段形状差异、原语言及hash/size/身份/期次、共享限额/截止时间、重复导入、失败回收和空scratch恢复的验收标准。
- 这是计划细化，尚未运行联调；测试前必须使用隔离短TEMP根，零付费API/LLM调用，生产raw/catalog/config不变。全部通过后才快进合入ET提交。

## 2026-10-04 — FF→ET→CWP 离线契约联调与缺陷修复

- 用真实 FF companion/`EarningsTranscriptsTransport`、ET deadline 分支 `0017f24` 正式 `transcript_tool.py`→supervisor→worker→FMP parser/serializer、CWP真实query/import/source-reader CLI跑通离线链路。只有HTTP由ET既有私有worker launcher换成fake session；没有付费API、LLM或生产目录写入。工具 `tests/e2e/run_ff_et_cwp_offline_acceptance.py` 使用短TEMP scratch并在退出时验证它确已删除。
- 成功链保留原始FMP JSON字节，SHA-256/size/MIME一致；SourceRef无物理路径；unknown publication不伪造日期且不参加历史as-of；第二次调用复用同一SourceRef、provider调用数为0、raw只1份。key未进FF结果/日志，成功后ET worker临时目录为空。
- 联调最初因ET `request_schema`失败，追溯到FF将公司身份的`NASDAQ`直接传给只接受`nasdaq`/`nyse`的ET公共CLI。FF adapter现有小写规范化和回归测试；此处只改exchange传输字段，不重写身份合同。
- 有限慢provider场景复现另一个真实问题：FF外层subprocess timeout与ET worker deadline同为2秒，FF先杀ET父进程，导致`et-retrieval-*`目录在worker结束后仍残留。FF现按ET下游60秒上限裁剪，先为清理保留3秒并延长外层等待；FF总余时不足3秒时不启动ET子进程。用5秒fake响应/2秒采集预算复测后映射`provider_deadline`，没有raw入库且worker scratch清空。
- ET独立 `tests/test_retrieval_cli_e2e.py` **6 passed / 19.13s**；FF `tests/test_transcript_companion_transport.py` **5 passed / 9.77s**，改动文件Ruff通过；CWP FMP importer责任包 **5 passed / 9.45s**。最终FF→ET→CWP离线脚本成功；pytest basetemp与E2E scratch逐路径验证删除。CWP测试禁用第三方pytest插件时有一条`asyncio_mode`未知配置warning，无测试失败。
- 旧ET golden README和早期findings中的“CWP只接受Motley 24字段、FMP 26字段尚不能导入”是已过期快照。当前CWP源码与`test_fmp_unknown_publication_cli_stores_original_but_excludes_historical_cutoff`确认FMP provider contract已存在；不增加CWP adapter。ET deadline分支的golden说明已按现状更新。
- 发布状态：FF两文件已测但尚未提交；ET deadline候选原`0017f24`新增一个producer README修正尚未提交。提交前确认各自远端头未前进，不带入FF API key、ET未跟踪文件、CWP用户配置和其他审计结果；随后FF修复推送、ET分支快进并入main后推送。

## 2026-10-04 — ET deadline并线及合入后验收

- 上一条是提交前快照，现已完成：FF adapter/test commit `eb0af13`推至`filing-fetch/main`；ET deadline commit `0017f24`及golden README更正`63c4090`经纯快进进入`earnings-transcripts/main`，远端也已推至`63c4090`。候选branch同步到同一tip。
- 合入后在ET `main`重新运行FF→ET→CWP完整离线脚本成功；ET CLI E2E **6 passed / 22.54s**且**10 goldens matched**；FF companion **5 passed / 10.55s**；CWP FMP importer **5 passed / 14.98s**。Ruff之前在FF两个变更文件上通过；实际测试basetemp逐项清除。CWP pytest禁用第三方插件运行，有一条仓库`asyncio_mode`配置warning，没有失败。
- ET main工作树仍只有两个原有未跟踪个人文件 `.workbuddy-ai/`、`eval_results.json`；deadline worktree无跟踪改动。FF的未跟踪API key文件保持未读、未暂存、未推送。CWP本机provider配置仍未改。
- S3跨仓合同与deadline接线已完成；真实FMP取数权益仍未知/HTTP 402，不阻塞offline合同。下一步转S4/N4C：先逐类型只读确认active、metadata可见、原文字节SHA一致的真实样本；再跑有限Worker批次并测consumer实读、证据定位/语言与总空间。样本不合格就通过正式producer/activation流程解决，不手改catalog。

## 2026-10-04 — 新增外部harness施工包

- 已创建并接入总计划、并行计划的三个可独立派发卡：N4-T1模型传输错误诊断、N4-T2中文财报/IR叙述选材覆盖、MeetingConverter CI快速门。当前仅为READY TO DISPATCH，尚未收到这三张卡的施工交付。
- N4-T1和N4-T2限定在CWP不同代码目录和不同测试文件，需从同一已提交基线各自创建隔离worktree；不得共用checkout、修改共享PWF/配置/生产数据或执行付费请求。交付后由MAIN联合做跨层测试与新的有限真实批次。
- MeetingConverter卡限定其独立仓库CI配置；先核查远端最新workflow是否已有真实job和测试。如已修复只交证据，不为制造改动而改工作流。StockQAbyLLM与MeetingConverter早期只读盘点卡仍按原收据保持验收状态，IQS不派新任务。
- N4C run账本复核结果及不确定性已写入findings/task_plan：季报与IR来源可验证且解析覆盖完成但零span；MiniMax旧失败无状态码/响应摘要，确切原因未知；错误分类丢失HTTP状态是源码已确认的独立缺口。旧unknown reservation保留，不复用run ID。
- 无代码、source catalog、raw文件或生产数据库修改；本机用户文件 `config/source_acquisition.yaml` 原样保留。计划文档后续执行diff check/plan-claims检查并仅提交本轮明确的PWF及三张卡。

## 2026-10-04 — MAIN长文模型输入收缩完成（N4C仍未GREEN）

- RF先行只读核查正常账号状态：fcap5319ee26仍仅两项owner运行记录dirty，origin/main8a153f3；没有修改RF/IQS或外包卡的写集。本线新代码只有automation/narrative_model.py和tests/unit/test_narrative_model_request.py。
- 先补施工细则，再TDD：新请求测试初跑5 failed / 0.92s，准确暴露完整span请求超限、无coverage和coverage不入hash；没有修改原摘要/引用断言。最终精简模型投影保留全部selected原文/ID/角色/有意义质量标记，定位仍由canonical证据负责，schema/example继续完整教给模型，prompt1.2.0。
- 最终单元/handler聚焦35 passed / 1.05s；预算caller+正式CLI/Worker本地HTTP端到端14 passed / 40.16s；合计49项通过。命令为pytest -p no:cacheprovider --basetemp tmp/ptcmp加上述四个测试文件，两次最终责任集均未relocate。Ruff和diff check通过。pytest禁用第三方插件后仅有既有asyncio_mode配置warning。
- 精确自建tmp/ptcmp在同账号下确认位于workspace后删除，测试scratch已恢复；旧失败run保留用于诊断和未知费用记账。真实select结果只读请求大小复测招股书252,185→47,202 B、年报7,797→4,285 B，全部ID/原文匹配且旧ledger文件SHA不变，没有外部调用。
- S4改为in_progress，纠正旧“批次尚未开始”文字；真实summary/consumer与并发/空间验收仍未通过。下一主线动作整合N4-T1/T2，先核算剩余总预算，再另建run；原unknown费用和原件不丢。用户source_acquisition.yaml不纳入提交。

## 2026-10-04 — 发布收据与串行复用施工目录

- 模型请求投影收缩提交df529a9已推origin/master，pre-commit Ruff/mypy/host检查和pre-push快速门通过；GitHub CI [37239069991](https://github.com/zhengcb81/company-wiki/actions/runs/37239069991) 已completed/success，head_sha匹配df529a9。
- 用户询问同目录先后执行N4-T1/T2，已将两张卡、总计划与并行计划改为：并行各用一个worktree；串行可复用同一专用worktree，T1测试完且commit后T2接续，分别记录base/head。T2允许以T1交付HEAD为base，不reset已交付代码；MAIN活动checkout仍由主线独占。没有新增人工签收或测试节点。
- 此后续改动只有文档，diff check通过；不再重复业务测试。并行计划头部同步G1/S3已完成的事实，旧同日记录标为历史过程，防止重新派发ET-DEADLINE。用户配置保留。

## 2026-10-04 — S5首批旧缓存实际清理完成

- RF先行正常账号只读复核仍为fcap5319ee26、origin/main8a153f3、两项owner记录dirty。本轮只读其主线scripts确认默认仍走legacy SourceBundle；不能按v2实现存在便删全部derived。IQS/Dayu与外线代码写集未动。
- 新增S5/S6实施细则：RF生产入口迁pathless、CWP旧section/全量writer退休、derived和artifact状态同批退出、旧全量span消费者逐项迁移后DB收缩。原件/来源版本/撤回事实保留，不等全量文档重新摘要，不复制巨大恢复备份，不加小节点人工门。
- 首次只读dry-run逐集合数值正确但PowerShell对ordered hashtable的Measure-Object汇总得0，尚未删除即发现；改collection为PSCustomObject，第二次得到138,648,023 B/923文件，与交付审计一致。受限账号只读CIM访问拒绝后用正常账号核活进程；没有重复启动清理进程。
- 一个有界PowerShell进程2026-10-04 22:21:38–22:26:27 UTC完成七集合删除；进程终态exit0/status=success。公司原件清单、完整catalog DB SHA、配置、保留derived/staging/security_master/artifacts、旧失败run及控制状态前后相同。一次性全量保护检查耗时约5分钟，不放进commit/CI。
- 清理前后正式source_reader_cli各4次读取真实年报/招股书/IR/季报，共8次、每轮12,343,802 B，完整bytes SHA、来源身份、size及policy一致。没有下载/模型/原件副本；生产DB mutation0、原件删除0。所有923目标文件消失，按文件逻辑大小释放138.65MB；不声称磁盘free-space净变化或完整总量新实测。
- 一次性两个脚本及重复临时读取JSON逐绝对路径验证并删除，只保留合并机器收据和短说明。用户配置不stage。S5仍in_progress；derived主体、旧全量span及N4C两卡集成/真实摘要/并发与消费者仍待完成。仅文档/收据提交，无新业务代码，不全仓重测。
- 发布：`3f7dd2b`已推origin/master，pre-commit无相关代码文件正确跳过，pre-push快速门GREEN；git status仅剩既有用户配置。顶层当前状态同步本轮完成项，避免弱模型按较早文字重复收缩模型请求或再次清理923文件。

## 2026-10-04 — 旧normalized section公开生产入口退休

- 先重新fetch RF主线8a153f3，确认owner两项记录未变；其旧来源准备默认、SKILL文档及CLI夹具仍相互绑定，后续迁移一起处理，不仅改开关。CWP独占改动先处理extract-sections；本轮没有修改RF代码。
- TDD新增CLI未注册、公开SourceCatalog不再提供section writer、真实子进程在配置打开前拒绝旧命令且raw不变。首轮一个根为空的fixture不满足CatalogConfig要求，修成合法RootSpec后再次得到**3 failed/15 passed（1.89s）**，三个失败都对应待退休的实际入口行为。
- 删除extract-sections CLI注册/分派与SourceCatalog.extract_sections方法，修正CLI用途说明。旧纯解析和artifact完整性回归通过显式低级函数创建隔离legacy夹具，原断言保持；不再为这些fixture保留公开生产入口。
- 集中入口退休、章节解析与producer binding测试 **48 passed/24.30s**；改动Python Ruff与diff check GREEN。pytest禁用第三方插件仅有既有asyncio_mode warning；测试根短路径未relocate。正式新Worker回归与N4-T1集成一起执行。
- 旧normalize/summarize库方法、兼容旧Worker类和RF artifact读取仍待后续；没有删除2.826GB derived或生产DB span。当前用户报告N4-T1完成，已定位提交4a53080（base349d331），远端分支一致，六个文件符合独占写集；没有改该worktree，先将本轮入口改动commit，再查收集成T1。

## 2026-10-04 — N4-T1与MeetingConverter外包验收/并线

最终发布收据：company-wiki master/origin/master代码交接为66808ee，包含71f867a及5de9154；pre-push精选契约GREEN，远端run37241977614实际job72秒，Unit30秒/精选契约2秒，均success。MeetingConverter master/origin/master为8a33a7f，主线run37241709261实际job22秒且success。测试根ptn4t1/ptn4sql已按绝对包含路径删除；CWP唯一保留用户config/source_acquisition.yaml未提交。后续仅补本条文档状态，不增加小节点测试。

- N4-T1外线4a53080只含六个允许文件；MAIN cherry-pick为5de9154，没有覆盖其旧基线之后的PWF/紧凑请求/S5内容。外线工作树保持原样，T2可从4a53080接续，只交自己的新增提交。跨层114 passed/48.56s；MAIN新增实际HTTP400→正式CLI→SQLite attempt/unknown reservation端到端1 passed/6.59s，敏感正文/密钥不入输出或库。详见harness_lanes/results/n4t1_model_transport_acceptance_2026-10-04.md。
- MeetingConverter仅三个允许文件，交付8a33a7f；分支push/PR实际非空job绿18/19秒。MAIN正常用户上下文fetch核ref、merge --ff-only并push master；.coverage/config.json完整SHA/size/mtime和output清单前后相同，原dirty .coverage保留。PR1自动merged=true；新master run37241709261实际job绿22秒、Run tests2秒。外线全量204测试，本次未删业务回归；MAIN未在主checkout跑pytest。详见harness_lanes/results/meetingconverter_ci_acceptance_2026-10-04.md。
- MeetingConverter既存mimo.py:137未定义logger仍未修，卡片禁止应用代码改动，不把CI绿误报业务缺陷已消失。当前没有恢复全仓lint要求。
- N4C仍未完成；T2仍待交付。真实新run继续计入旧10,325token/$0.005258未知reservation，不扩总60,000token/$0.10预算；ET live仍402。用户配置、RF owner、IQS与Dayu均未改。

## 2026-10-05 — MAIN S5旧整库Worker退役与测试

- CWP现状核对修正计划此前的误记：旧Worker执行类曾残留，但没有任何src/scripts生产调用者；CLI的启动入口已移除，Win32无运行进程或任务。因此本次删除自动整库Worker及其专用scheduler_policy/测试，保留worker-status/worker-stop/uninstall用于遗留进程清理。
- 没有删除SourceCatalog的normalize/summarize按需接口或历史产物：RF远端main仍为`8a153f3`且`source_reader_v2=False`，实际默认分支消费SourceBundle normalized artifact；CWP evidence-query、extraction-quality及若干解析/PDF合同测试也仍依赖该读取面。等RF与CWP locator读取迁移完成再做API与derived退役。
- 保留旧摘要兼容测试并从混合worker大测试中提取到`test_source_catalog_legacy_summary.py`；移除的是死掉的后台Worker循环、stage policy专用测试，以及两个纯worker进程生命周期测试。新退休合同同时证明旧Worker/scheduler模块不可导入，而按需source catalog方法仍可用。
- RED：新退休合同先因`SourceCatalog.normalize`仍存在而失败；基于生产调用及下游依赖调查，把目标改为只退休无人调用的自动Worker，并加注释约束normalize API在读者迁移前保留。GREEN集中集：**127 passed / 64.28s**（退休入口、worker control/status、摘要、SourceCatalog pipeline/section、fingerprint）。
- 初次sandbox运行125 passed/2失败：HTML parser的Windows spawn受受限`<stdin>`/本机权限影响，python-docx etree DLL access denied；按项目正常用户上下文单独复核2 passed，并重跑同一127项完整集全绿。pytest专用目录最终恢复/删除。stdin诊断脚本和一次跨执行账户清理失败均记录为测试工具问题，已按真实脚本入口和原目录owner纠正。
- 代码和测试限定CWP，未改`config/source_acquisition.yaml`；RF的fcap两份weekly assurance用户记录保持原样。N4-T2/N4C和真实模型运行仍未完成。

## 2026-10-05 — S5退役提交发布与CI验收

- `ff0eec01137eac23e5142ce7863e20efd27fdfd4` 已推送 `origin/master`；pre-push快速契约门通过。GitHub Actions [37244400156](https://github.com/zhengcb81/company-wiki/actions/runs/37244400156) 对应head SHA完全匹配，最终 `completed/success`（Fast checks Python 3.12）。Ruff、严格类型检查、compileall/config doctor、unit、focused contract、CLI smoke 与 secret scan 均成功。
- N4-T1的独立收据此前已确认 ACCEPTED/INTEGRATED/PUBLISHED（114项跨层回归加真实loopback HTTP 400持久账本E2E；主线CI run 37241977614 success），此次没有新变更或需补验内容。N4-T2仍待交付。
- 发布后 `master` 与 `origin/master` 同步；仅保留原用户改动 `config/source_acquisition.yaml` 未提交，没有暂存或覆盖它。

## 2026-10-05 — MeetingConverter外包卡远端复核

- 按用户要求重新核对原始handoff、远端Git refs、PR和Actions。PR #1已closed/merged，merge SHA为`8a33a7f96292af8e6574d98b959703c6d11919eb`；远端`master`与`ci/fast-gate`、本地`master`/`origin/master`均为该SHA。主线push run `37241709261`、PR run `37241093118`、分支push run `37241089223`均success。
- 发现外仓`HANDOFF.md`的SHA/“PR未合并”段落仍是并线前版本；CWP验收收据和GitHub live状态一致且权威，本轮已在验收收据补充该过期字段说明。外仓文件未修改；MeetingConverter本地仅保留既有tracked `.coverage` dirty状态。

## 2026-10-05 — S5移除无人调用的Worker session launcher

- 源码调用调查确认`WorkerSession`、`WorkerController.open_session()`和`read_desired_state()`无剩余src/scripts生产调用者。移除该旧启动/心跳API与专用循环测试；`worker-status`、`worker-stop`、pause/interlock仍保留，并继续读取和清理升级前写下的runtime snapshot。
- TDD先以新增契约证明旧API确实退出；最终聚焦`test_source_catalog_control.py`、CLI retirement与automation race共 **55 passed / 17.48s**。Ruff四个改动Python文件及`git diff --check`通过。普通插件自动加载先因环境的`langsmith/pydantic_core` DLL权限在collection前失败；禁用无关插件后同一测试集完整通过（仅pytest.ini中缺asyncio plugin的既有`asyncio_mode` warning）。短路径`tmp/ptworker-s5-sandbox2`已在验证归属后删除。
- RF只读对账：remote `origin/main@8a153f3387ae75fb172e70f8ab63ffd38100779a`；`fcap`领先0、落后15提交，其3,833个execution_runs删除及两条weekly assurance dirty记录都属于owner WIP，未触碰。远端SourceRef v2仍为opt-in（默认`false`）。用RF/CWP两端都与对应主线匹配的代码跑三仓SourceRef原件复用/篡改拒绝E2E：**1 passed / 8.51s**，未下载或请求外部服务；隔离测试目录已移除。该测试不证明RF默认叙述/derived消费者迁完。
- 本次S5改动提交`a9b1a06f520c7d2565e2a5d93b90e26e9cdd28f2`并推送`origin/master`；pre-push fast contract smoke GREEN。GitHub Actions [37246820601](https://github.com/zhengcb81/company-wiki/actions/runs/37246820601) 对应SHA匹配，所有步骤通过，最终`completed/success`（Fast checks Python 3.12）。推送后仅保留既有用户配置`config/source_acquisition.yaml`未提交。
