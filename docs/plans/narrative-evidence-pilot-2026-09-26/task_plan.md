# 公司来源平台：激进简化与叙述批次实施总计划

> 2026-10-03 用户采纳八束激进方案并要求继续实施。本页是唯一当前施工顺序；旧Phase 1–64、W/G卡和审查要求只供技术追溯，不再产生任务或签收门。历史版本：https://github.com/zhengcb81/company-wiki/blob/bff81afe7cbb11c895764a94c2eabd121539e248/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md。原文不丢；旧无限Worker保持paused，新的显式有限批次按本计划上线。

## Goal

完成八束整套简化：一个下载请求入口、一套pathless来源接口、一套AUTO任务系统，按需选择业务叙述、摘要和检索；停止全量永久转换与重复正文；完成真实模型、持久预算、可恢复多文档处理及消费者接线，然后分批删除无调用者的旧派生。原件、来源/版本事实不丢。RF/FF/ET/StockWiki/IQS各仓独占写入，不修改其他owner未提交工作。

执行已恢复。最新 `get_goal` 实读为 **active**（2026-10-03）；此前工具无resume接口的限制已由应用实际恢复解决，不再把旧paused快照当当前状态。目标未完成，不标complete。

## 当前基线

- CWP mainline: commits `d2250b7` (run/generation ownership) and `54db2a2` (SQLite migration fixture close) are pushed. The 54db2a2 remote CI status could not be read in this session. On 2026-10-03 the old Worker public execution surface was retired: bulk `normalize/summarize/run`, worker launch/start/resume/pause and startup installation commands plus PS/VBS/menu/pilot launchers are gone. `worker-status`, identity-checked `worker-stop`, startup status/removal, scan/query/export and explicit `ensure`/`close-gap` remain. A read-only production check found desired state paused, runtime stopped, no matching worker/supervisor process and no installed startup task; no catalog/raw/config data was changed.
- RF `rf-impl` 当前 `main/origin/main@6fb2def7`，N3a narrative consumer 已并入；最近两提交修复 POSIX pipe deadline/reader descendants。4个旧 execution evidence 文件有本地行尾差异，保留不动；`Projects\revenue-forecast@fcap/5319ee26` 仍为另一工作树。2026-10-04 FF-S3 已快进推入远端 `main@1d0c73c`，本地 fcap 工作树同步至同一提交；未跟踪 `config/FMP_API_KEY.txt` 保持原样。Actions #52/#53/#54实际均失败在FC-1204-c mypy步骤；Python 3.12/mypy 1.19 Linux目标复现出 `transcript_tool_transport.py:100` 对平台特有 `subprocess.CREATE_NO_WINDOW` 的类型错误。TDD添加缺失常量用例并改用安全 `getattr`，Linux目标mypy现绿；完整CI精选集 **361 passed / 5 skipped / 78 subtests**，Actions #55 `37182527153` 已 completed/success。另独立修复了安装清单测试对真实工作树key缺失的假设；该本地测试脆弱点不是上述Actions根因。StockInfo bounded provider分支现为 `8ed5fdd`，并补上 adapter CLI stdout JSON 修复；CWP配置已指向隔离 provider 工作树并声明版本1.2.0/budget能力。以 BYD FY2024真实CNINFO年报完成 FF→CWP→StockInfo正式入口E2E：下载10,092,140 B，SourceRef、原始PDF和hash/字节数一致；latest_as_of只读复用和 legacy v1复用都没有新增文件。ET-S3 已并入 earnings-transcripts main，合并提交 `93fe52c`；同步阻塞 HTTP 与翻译预算仍不构成硬总时限承诺。SPACE-S5只读审计已交付，机器/文字报告及15项工具测试通过；清理仍归主线。StockWiki/IQS/RF dirty工作树继续保持owner隔离。
- 最新完整空间32,821,613,206B/32.82GB，公司原件25.20GB，current DB3.06GB、旧derived/index约2.87GB。已释放13.06GB不再重复计收益；原件不进入清理候选。
- 真实代码CI约56–62秒，单Python/全Unit/精选回归；不恢复全Contract/coverage日常门。

## 实施顺序与完成条件

| 步骤 | 当前状态 | 实现范围与输出 | 验收合入位置 |
|---|---|---|---|
| S0 简化收口 | complete（ff5396c，CI绿） | PWF只留当前入口；删除R1旁路签收/shadow/gold；commit移除pytest、config doctor按相关文件触发 | 一次相关Unit/混合行为回归与正常发布；不逐文件签收 |
| S1 N4A | complete（ff5396c，CI绿） | scope贯通Store/Worker/Supervisor/outbox/prepared，None兼容、空scope零修改、范围SQL先于LIMIT | N4节点A，确定性RED先行 |
| S2 N4B | in_progress (budget/factory/batch/recovery and public legacy Worker retirement implemented; capacity and real-sample acceptance remain in the later N4C node) | real factory/HTTP adapter/full prompt; persistent token/cost reservation in AUTO; finite batch CLI; unique final artifact and small recovery receipt; public legacy whole-catalog Worker and startup routes removed | node A accounting/concurrency green; node B formal CLI/HTTP/kill/ACK and focused regression green; CWP producer limits are now connected and have real-data E2E evidence; proceed to N4C after G1/S3 closeout |
| G1 残余门禁/签收精简（当前第一优先） | in_progress（AUTO Approval API已退役、历史表保留；resolver复核存储失败已降为诊断；prompt复核签名/信任根/TTL工具已删；历史active映射不再要求手填reviewer） | 对照46项基线核实“仍在代码里”与“真能阻断”；优先完成 CWP 本仓清理及跨仓只读审计，不改其他owner的dirty工作树 | 110项来源/复核相关回归、22项激活/恢复回归、Ruff通过；快速门精选测试名已修正并通过。整体审计仍未完成；大节点收口后再进入 S3 |
| S3 SourceRef/SourceExport 虚拟化与来源默认收敛（G1之后第二优先） | in_progress（FF-S3已进main；ET-S3已合并；CNINFO bounded provider已启用并通过真实资料FF→CWP→provider E2E；RF/StockWiki已有pathless消费证据；ET真实工具导入仍待一次验收） | 上层只使用 SourceRef/SourceExport v2，不依赖 CWP/StockInfo/Dayu/Dropbox物理目录；收口FF v1 exact reuse、v2 latest_as_of只读复用、来源缺元数据partial、published-asof、安装示例及ET原语言导入 | BYD年报真实采集闭环已通过；电话会 live import验收使用[ET-LIVE独立卡](harness_lanes/et_transcript_live_import_acceptance.md)。明确 IQS 快扫不自动消费/下载 CWP 文档，其 PWF 将 company-wiki 定义为可选只读深研链接，不为追求“全仓统一”强行改边界 |
| S4 N4C real samples and storage plan | pending（G-C 证明了 RF 年报/TXT 来源消费，不等于 Worker 多文档批次；排在优先门禁精简之后） | four real document types / consumer reads / language and citation coverage / total incremental bytes; retain only status/stop/uninstall compatibility for old worker process cleanup | node C; bounded real batch, then measured 1/2/4 parallelism；至少覆盖年报、招股/再融资、IR和电话会/季度类中的四种，记录摘要证据定位和新增空间 |
| S5 B2逐caller清理 | pending（SPACE-S5只读审计已交付） | 审计确认约138.6 MB无代码调用者集合可列入首批候选；2.826 GB `derived/` 仍有 reader 与 8,191 条 artifact 路径引用，必须先迁移；报告不是删除清单 | 主线复核当前调用者/生产文件状态后分集合处理；每批验证原件与来源事实保留并测实际释放量 |
| S6 DB事实收缩与收尾 | pending | 表级盘点，删除不可再消费派生/废索引并收缩，来源版本/撤回事实保留；旁路兼容、docs/hook残留清完 | 同一存储节点；commit/push、PWF收尾 |
| 可选 exact-SHA原件对象去重 | 不阻S0–S6完成 | 先用已有SHA/size找候选、逐候选验字节，保留所有source/location版本事实 | 有真实收益才实施；不报未测节省量 |

## S0精确施工范围

- 删除scripts/gate_runner.py、reviewer_gate.py、gate_state.py、gold_review_gate.py；删除automation/handlers/gold_review.py、human_inbox.py与source_catalog/source_lifecycle.py、readiness_graph.py及仅服务它们的测试。
- registry/planner/doctor同步去gold/analysis占位映射，保留timer与通用历史BLOCKED_HUMAN状态；不DROP历史表、不改Store lease/fence/预算。
- 混合测试迁移环境隔离到已有clean_env_gate helper，保留原件不入candidate、生产原件不变和故障真实失败断言；不能整文件删test_writer_freeze/hermetic/acceptance。
- read_chain删已退出shadow模块的handoff，writer_policy删不存在脚本的旧allowlist。AGENTS/architecture静态引用随实际功能退出；已停用研究writer可分批删空壳，来源职责仍保留。
- activation/rollback/restore reviewer已改可选运行记录。prompt签名/TTL旧写工具已在G1退役并保留旧诊断读取；旧一次性archive审批工具仍列在S6，待确认调用后收尾。签名格式若有真实消费者先薄兼容，不能伪造host_signed。
- commit保相关Ruff、有限mypy/路径静态检查，无pytest；config doctor仅config/配置加载代码改变时触发。push精选一次、CI全Unit与同精选一次。coverage/complexity数字改诊断，不为数字拆helper。

## 最小正确性与接口责任

1. 存储层：原件immutable、实际open验bytes SHA、路径包含与写入归属。上层只用SourceRef，不重复判断company-wiki/dayu/Dropbox目录。
2. 来源层：公司/证券/期次/公开时间、版本与撤回事实；缺非核心采集字段可partial，不伪报verified。默认公开日期cutoff，retrieved-at严格快照仅显式模式。
3. 解析/摘要层：selected evidence/locator可回放、parser/prompt/version、同原语言；source-only，无正式投资判断。保留final短引用，locator-only另演进现有bundle，不破现有consumer。
4. 调度层：Store事务、lease/generation、幂等attempt/effect/outbox；解析/HTTP锁外，提交验来源版本。后台pause不阻一次明确主动下载。
5. 资源层：一次操作真实执行文件/字节/时间/token/费用上限；未知usage保留reservation。限额不是人工授权文件，不写第二CSV或任务库。

## 原件与降容规则

- 未解析资料metadata_only；高价值请求优先。格式化/重复模板skip只留source、原因、coverage；财务表格不全量建span。
- 一份raw、一份最终摘要+精选引用、一份小型来源/usage记录。active/retry/prepared/未ACK保留恢复材料；DAG终态且final visible后去重复正文。
- 全文转换临时；典型final20–100KB是待测目标，2MiB仅紧急cap；新持久增量1GiB、批次scratch峰值2GiB沿N4实施，不因超限删原件。
- 不自动全DB/旧span/derived压缩备份。不可再生metadata迁移仅一个小库恢复点，成功后收尾；不完整恢复46GB备份演练。
- B2无引用的集合可提前退出；DB3.06GB不是可删量。SQLite逻辑删除与真实文件释放分别记录。

## 并行所有权

R1/N4A临时分工已完成。外部harness分工见[并行实施总计划](parallel_execution_plan_2026-10-03.md)：MAIN独占company-wiki；FF-S3曾独占filing-fetch-s3-limits worktree，已快进推入FF main；ET-S3曾独占earnings-transcripts-s3-runtime worktree，已合并并推送；SPACE-S5只写独立company-wiki-storage-audit-20261003目录、所有生产仓只读，报告完成后由主线负责清理。StockWiki/IQS/RF dirty工作树继续由各自owner管理。

StockWiki/IQS已有活跃owner与新未提交工作，本轮不再派线；RF源工作树保留。FF/ET不写CWP总PWF或彼此仓库，各自局部PWF/测试/小报告，交commit；root一次合入联调，不逐helper审批。结构上共用Store/来源默认/批次/空间清理仍归MAIN，不强拆同目录。

## 验收与发布

TDD框住公开行为，不把旧签收规则写进新测试。仅S0相关收口、N4 A/B/C、存储迁移几个大节点；helper/每文档/每删除文件没有人工审查。修复具体红灯后重跑相关包，不为了可选复杂度/覆盖率/固定场景数量全仓长测。

正式端到端测试使用独立短根、同OS账号创建/执行/finally清理；本地HTTP/模型请求也必须显式测试预算。真实资料副本原来不存在则退出删除。生产配置/control/原件fingerprint前后不变；不把失败夹具留在生产或仓库。正常commit/push，代码CI绿后记录；纯Markdown不要求新CI。

## 当前文档导航

- [已采纳的八束方案](radical_simplification_proposal_2026-10-03.md)
- [N4接口/TDD/正式batch详细卡](n4_production_batch_implementation.md)
- [ET-LIVE电话会原文导入与虚拟化独立验收卡](harness_lanes/et_transcript_live_import_acceptance.md)
- [46项原审计基线及2026-10-04覆盖更新](gate_permission_inventory_2026-10-03.md)，基线日期不变；当前状态以新增覆盖节为准
- [最新空间收据](harness_lanes/results/gd_storage_final_cleanup_2026-10-03.md)
- [findings](findings.md)、[progress](progress.md)
- 旧implementation/execution/worker/review/space卡保技术背景，其流程/顺序由本页覆盖。已交付harness不再派发同一工作。

## Next Step

**当前优先顺序（2026-10-04更新）**：①G1门禁/签收精简：完成CWP确认无真实身份校验价值的人工字段清理，并逐项更新46项审计；②S3 SourceRef/SourceExport虚拟化：收口安装示例、来源默认/缺元数据语义，验证FF/ET到CWP的原语言原文导入及pathless读取；③S4 N4C多文档批次与真实样本空间测量；之后再做S5/S6派生与DB清理。G1/S3只在大节点做集中测试，不恢复逐文件签收；外仓有owner改动时保持只读。

**可并行包**：[ET-LIVE电话会原文导入验收](harness_lanes/et_transcript_live_import_acceptance.md)可现在交给独立harness。它只做一次受限真实验收并只写唯一结果文件，不改生产代码/配置；若发现代码缺口，交给主线在G1完成后修。FF-S3、ET-S3、StockWiki W01/W04和SPACE-S5均已交付，不重复派发；目前没有适合外部harness直接改CWP核心或RF/StockWiki/IQS代码的无冲突包，因为核心接口归主线，外仓owner工作树仍有未提交改动。

旧 Worker 的公开执行与启动链已退役，生产无残留进程/登录任务。CWP producer-budget 集中回归 **41 passed / 14.83s**，模拟HTTP跨仓E2E发现1个候选、PDF 399 B、发现+下载计费713 B且精确吻合。StockInfo隔离分支 `codex/cninfo-bounded-budget@8ed5fdd` 已实现流式CNINFO discovery/PDF限额和JSON-only stdout；原 `v2-clean-rewrite` owner工作树保持隔离。CWP已切换到该集成工作树、配置provider 1.2.0并显式声明budget capability。2026-10-04以 BYD FY2024真实CNINFO年报跑通 FF-S3→CWP→StockInfo正式入口：实际下载10,092,140 B；PDF、SourceRef SHA-256与字节数一致。`latest_as_of + reuse_only` 带5MB/90s/$0限额只查询元数据，0缺件且无文件/hash变化；legacy v1 exact reuse也未增加下载。legacy v1缺件且无额度参数时返回码2并未写公司文件。所有独立测试root已清理，生产配置/identity snapshot指纹前后未变。Dayu保持不改，遇到无法真实施加硬上限的请求仍外发前拒绝。FF-S3 `1d0c73c` 已快进推入main；Actions #52/#53/#54实际失败在Linux FC-1204-c mypy。Python 3.12/mypy 1.19 指定Linux目标复现并修复 `CREATE_NO_WINDOW` 存根问题；TDD回归转绿，FF完整精选CI **361 passed / 5 skipped / 78 subtests**，GitHub Actions #55 completed/success。另将安装清单假key测试隔离到pytest临时树，解决其在本地 fcap key 工作树上的独立失败。fcap同步到1d0c73c，未跟踪API key仍未读未动。

### S3 bounded provider transport：固定桥接合同

- 唯一先实现的生产 transport 是 CNINFO。StockInfo 原工作区在实施前有24个tracked修改和未跟踪CNINFO adapter/client/test；已基于 `1693045` 建立隔离分支 `codex/cninfo-bounded-budget`，commit `947e839`（13个精确相关文件），实现provider-local预算和CNINFO discovery/PDF流式读取。依用户2026-10-04授权，对原工作区只移除两个无调用者且与CWP路径抽象冲突的辅助脚本、一个0字节误生成文件，并将11个仅有import/格式调整的tracked文件恢复至HEAD（index未动）；其余adapter、源码、测试、夹具、公司名单与功能改动保留。原工作区代码未整体恢复。GitHub API核对远端ref等于 `947e839`，owner集成分支 `v2-clean-rewrite` 仍等于父提交 `1693045`；它与默认main没有共同祖先，只有配置明确使用的v2路线可作为本项集成目标。provider仓未发现Actions workflow。Dayu 是纯外部项目，代码不改；HK/US 遇到硬下载 cap 继续外发前拒绝。
- CWP `JsonCommandAdapter` 增加 `discover_bounded` / `fetch_bounded`。子进程 JSON 请求附加 `acquisition_budget`：恰含 `schema_version="1.0"`、`max_response_bytes`（本阶段剩余额度）、`timeout_seconds`（单调 deadline 剩余秒）、`max_cost_usd`（十进制字符串）。CWP subprocess timeout 取配置 timeout 与同一剩余秒数的较小值。
- 支持 bounded 的 provider 对每个 discovery JSON / PDF HTTP响应按块读取；检查本阶段 deadline，并在接纳每块前拒绝超过 `max_response_bytes` 的响应。成功 JSON 必须包含 `acquisition_usage`，恰含 `schema_version="1.0"`、`response_bytes`、`cost_usd`；CWP 校验形状后把两项记入共享 `AcquisitionBudget`。漏报、额外字段、非法数、超预算、进程超时一律失败；fetch回执大小还须由 CWP 独立复核。
- 一个 `AcquisitionBudget` 对象贯穿 ensure/close-gap 锁外及锁内 metadata discovery、CNINFO分页、fetch与staging，不因子进程/分页重置；未知失败不重试已部分消费的预算。CNINFO当前收费为零，由provider明确报告 `"0"`，不将“没有成本数据”伪报为零。provider CLI 无预算的 legacy调用保持既有合同。
- TDD 大节点：CWP 命令适配器进程测试证明预算被传递、真实elapsed timeout、usage缺失/少报/超额失败；StockInfo 测试用分块假响应覆盖 discovery 与 PDF cap边界、deadline、cleanup `.part`；正式短根跨进程 E2E 从 CWP budgeted `ensure` 到 StockInfo JSON CLI，确认发现+下载共享总字节、精确SHA/回执、第二次失败时不留part/staging且没有第三方/生产文件变化。Dayu负例确认子进程 marker不存在。集中责任包通过后才启用CN bounded能力并与FF-S3运行正式E2E/汇合。

CNINFO bounded provider已进入隔离 owner集成工作树；CWP配置 `config/source_acquisition.yaml` 使用provider 1.2.0并启用 `supports_acquisition_budget`。正式真实数据E2E验证了FF→CWP→StockInfo的实际PDF下载、SHA/size闭环、latest_as_of只读复用、legacy v1复用及无预算v1缺件fail-closed。StockInfo focused suite 62项通过；CWP限额/来源适配器责任集32项通过。FF-S3的latest_as_of只读元数据预算语义与legacy exact复用/缺件合同测试共23项通过，提交 `1d0c73c` 已快进推到远端main。Actions #52/#53/#54都失败在FC-1204-c的Linux mypy；根因是传输模块无保护地引用Windows专属常量，Python 3.12/mypy 1.19 Linux目标回归与修复已验证通过。新的完整精选集361 passed / 5 skipped / 78 subtests，Actions #55 `37182527153` 已 completed/success。之前 `2936ad1` 的安装清单假key隔离只修正本地有key工作树的独立测试脆弱点，不能算远端CI根因修复。Dayu未改，硬限额仍只支持具备真实bounded transport的CNINFO。CWP producer-budget此前已推送为 `288b028`，CI `37162544905` success。当前先完成G1本仓门禁精简与审计更新；随后收口S3余下安装示例与来源默认/缺元数据语义检查，再进入S4真实样本多文档批次与空间测量；不重复跑全仓慢测试。

## S2 当前交接与下一集中节点

- N4A scope、N4B 真实模型计量、持久预算、production factory、有限 CLI、终态降容、跨 run 工件绑定、run/generation 自动 owner、父进程 kill 恢复与提交 ACK 丢失幂等已实现；相关提交 `ff5396c`、`9ccd29f`、`9041543`、`d2250b7`、`54db2a2` 均已推送。
- 2026-10-03 只读现场检查：旧 worker `desired_state=paused`、`runtime_state=stopped`；匹配 worker/supervisor 均为 0，Windows startup task 未安装。随后删除旧全库 CLI、启动/恢复/暂停与安装任务入口、Windows 启动器/控制菜单及旧启动专属测试；保留 `worker-status`、身份核验 `worker-stop` 与启动任务检查/卸载。旧 raw、SQLite、worker state 和日志均未触碰。
- 155 项相关回归此前 153 项通过；两项失败都是过期断言（deletion manifest 已退役、旧 `resume` 方法已删除），更正后对应 2 项单测复跑通过。CLI/显式下载退役合同另有 18 项通过。
- 仍不把 S2 标记完成：N4C 的真实模型小批、消费者实读、引用/语言 coverage 与全量新增空间峰值仍未验收；先完成 CWP producer limits，再进入 N4C。
