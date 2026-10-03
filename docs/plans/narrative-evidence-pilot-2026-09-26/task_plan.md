# 公司来源平台：激进简化与叙述批次实施总计划

> 2026-10-03 用户采纳八束激进方案并要求继续实施。本页是唯一当前施工顺序；旧Phase 1–64、W/G卡和审查要求只供技术追溯，不再产生任务或签收门。历史版本：https://github.com/zhengcb81/company-wiki/blob/bff81afe7cbb11c895764a94c2eabd121539e248/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md。原文不丢；旧无限Worker保持paused，新的显式有限批次按本计划上线。

## Goal

完成八束整套简化：一个下载请求入口、一套pathless来源接口、一套AUTO任务系统，按需选择业务叙述、摘要和检索；停止全量永久转换与重复正文；完成真实模型、持久预算、可恢复多文档处理及消费者接线，然后分批删除无调用者的旧派生。原件、来源/版本事实不丢。RF/FF/ET/StockWiki/IQS各仓独占写入，不修改其他owner未提交工作。

执行已恢复。最新 `get_goal` 实读为 **active**（2026-10-03）；此前工具无resume接口的限制已由应用实际恢复解决，不再把旧paused快照当当前状态。目标未完成，不标complete。

## 当前基线

- CWP mainline: commits `d2250b7` (run/generation ownership) and `54db2a2` (SQLite migration fixture close) are pushed. The 54db2a2 remote CI status could not be read in this session. On 2026-10-03 the old Worker public execution surface was retired: bulk `normalize/summarize/run`, worker launch/start/resume/pause and startup installation commands plus PS/VBS/menu/pilot launchers are gone. `worker-status`, identity-checked `worker-stop`, startup status/removal, scan/query/export and explicit `ensure`/`close-gap` remain. A read-only production check found desired state paused, runtime stopped, no matching worker/supervisor process and no installed startup task; no catalog/raw/config data was changed.
- RF `rf-impl` 当前 `main/origin/main@6fb2def7`，N3a narrative consumer 已并入；最近两提交修复 POSIX pipe deadline/reader descendants。4个旧 execution evidence 文件有本地行尾差异，保留不动；`Projects\revenue-forecast@fcap/5319ee26` 仍为另一工作树。FF-S3 已提交并推送至 `origin/codex/ff-s3-single-request-limits@8f17cbd`；CWP bounded JSON桥接、CNINFO provider隔离实现及跨进程E2E已完成，但StockInfo分支尚未合入当前配置所指的工作树（配置仍为1.1.0且能力默认关闭），因此生产限额仍fail closed；v1/latest_as_of额度语义仍待汇合。ET-S3 已并入 earnings-transcripts main，合并提交 `93fe52c`；同步阻塞 HTTP 与翻译预算仍不构成硬总时限承诺。SPACE-S5 只读审计已交付，机器/文字报告及 15 项工具测试通过；清理仍归主线。StockWiki/IQS/RF dirty 工作树继续保持 owner 隔离。
- 最新完整空间32,821,613,206B/32.82GB，公司原件25.20GB，current DB3.06GB、旧derived/index约2.87GB。已释放13.06GB不再重复计收益；原件不进入清理候选。
- 真实代码CI约56–62秒，单Python/全Unit/精选回归；不恢复全Contract/coverage日常门。

## 实施顺序与完成条件

| 步骤 | 当前状态 | 实现范围与输出 | 验收合入位置 |
|---|---|---|---|
| S0 简化收口 | complete（ff5396c，CI绿） | PWF只留当前入口；删除R1旁路签收/shadow/gold；commit移除pytest、config doctor按相关文件触发 | 一次相关Unit/混合行为回归与正常发布；不逐文件签收 |
| S1 N4A | complete（ff5396c，CI绿） | scope贯通Store/Worker/Supervisor/outbox/prepared，None兼容、空scope零修改、范围SQL先于LIMIT | N4节点A，确定性RED先行 |
| S2 N4B | in_progress (budget/factory/batch/recovery and public legacy Worker retirement implemented; capacity and real-sample acceptance remain in the later N4C node) | real factory/HTTP adapter/full prompt; persistent token/cost reservation in AUTO; finite batch CLI; unique final artifact and small recovery receipt; public legacy whole-catalog Worker and startup routes removed | node A accounting/concurrency green; node B formal CLI/HTTP/kill/ACK and focused regression green; CWP producer-limit design must first close verified provider transport gaps, then N4C |
| S3 来源与采集默认收敛 | in_progress（英文召回子项绿；FF-S3 branch delivered，ET-S3 merged；RF G-C pathless consumer 已由 main + 跨仓E2E确认；CWP bounded bridge/provider已实现并E2E验证，provider尚未进入配置工作树、生产能力仍关闭） | R2/R6：一请求、薄v1适配、相关字段fingerprint、缺元数据partial、published-asof；FF执行limits/ET旧入口一致；安装技能示例同步 | 将已测试StockInfo provider能力并入其集成工作树；更新CWP provider版本/能力声明并以正式FF请求跑跨仓E2E；定清 v1 / latest_as_of 预算语义后再合FF |
| S4 N4C real samples and storage plan | pending（G-C 证明了 RF 年报/TXT 来源消费，不等于 Worker 多文档批次） | four real document types / consumer reads / language and citation coverage / total incremental bytes; retain only status/stop/uninstall compatibility for old worker process cleanup | node C; bounded real batch, then measured 1/2/4 parallelism；至少覆盖年报、招股/再融资、IR和电话会/季度类中的四种，记录摘要证据定位和新增空间 |
| S5 B2逐caller清理 | pending（SPACE-S5只读审计已交付） | 审计确认约138.6 MB无代码调用者集合可列入首批候选；2.826 GB `derived/` 仍有 reader 与 8,191 条 artifact 路径引用，必须先迁移；报告不是删除清单 | 主线复核当前调用者/生产文件状态后分集合处理；每批验证原件与来源事实保留并测实际释放量 |
| S6 DB事实收缩与收尾 | pending | 表级盘点，删除不可再消费派生/废索引并收缩，来源版本/撤回事实保留；旁路兼容、docs/hook残留清完 | 同一存储节点；commit/push、PWF收尾 |
| 可选 exact-SHA原件对象去重 | 不阻S0–S6完成 | 先用已有SHA/size找候选、逐候选验字节，保留所有source/location版本事实 | 有真实收益才实施；不报未测节省量 |

## S0精确施工范围

- 删除scripts/gate_runner.py、reviewer_gate.py、gate_state.py、gold_review_gate.py；删除automation/handlers/gold_review.py、human_inbox.py与source_catalog/source_lifecycle.py、readiness_graph.py及仅服务它们的测试。
- registry/planner/doctor同步去gold/analysis占位映射，保留timer与通用历史BLOCKED_HUMAN状态；不DROP历史表、不改Store lease/fence/预算。
- 混合测试迁移环境隔离到已有clean_env_gate helper，保留原件不入candidate、生产原件不变和故障真实失败断言；不能整文件删test_writer_freeze/hermetic/acceptance。
- read_chain删已退出shadow模块的handoff，writer_policy删不存在脚本的旧allowlist。AGENTS/architecture静态引用随实际功能退出；已停用研究writer可分批删空壳，来源职责仍保留。
- activation/rollback/restore reviewer已改可选运行记录。prompt签名/TTL旧写工具在S3诊断协议一起退役；旧一次性archive审批工具在S6收尾，已有引用先迁移。签名格式若有真实消费者先薄兼容，不能伪造host_signed。
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

R1/N4A临时分工已完成。外部harness分工见[并行实施总计划](parallel_execution_plan_2026-10-03.md)：MAIN独占company-wiki；FF-S3独占filing-fetch-s3-limits worktree；ET-S3独占earnings-transcripts-s3-runtime worktree；SPACE-S5只写独立company-wiki-storage-audit-20261003目录、所有生产仓只读。ET-S3已合并并推送；FF-S3已推送支线、等 CWP producer/预算语义联调后再合 FF main；SPACE-S5报告完成、主线负责按报告实施清理。StockWiki/IQS/RF dirty 工作树继续由各自 owner 管理。

StockWiki/IQS已有活跃owner与新未提交工作，本轮不再派线；RF源工作树保留。FF/ET不写CWP总PWF或彼此仓库，各自局部PWF/测试/小报告，交commit；root一次合入联调，不逐helper审批。结构上共用Store/来源默认/批次/空间清理仍归MAIN，不强拆同目录。

## 验收与发布

TDD框住公开行为，不把旧签收规则写进新测试。仅S0相关收口、N4 A/B/C、存储迁移几个大节点；helper/每文档/每删除文件没有人工审查。修复具体红灯后重跑相关包，不为了可选复杂度/覆盖率/固定场景数量全仓长测。

正式端到端测试使用独立短根、同OS账号创建/执行/finally清理；本地HTTP/模型请求也必须显式测试预算。真实资料副本原来不存在则退出删除。生产配置/control/原件fingerprint前后不变；不把失败夹具留在生产或仓库。正常commit/push，代码CI绿后记录；纯Markdown不要求新CI。

## 当前文档导航

- [已采纳的八束方案](radical_simplification_proposal_2026-10-03.md)
- [N4接口/TDD/正式batch详细卡](n4_production_batch_implementation.md)
- [46项原审计基线](gate_permission_inventory_2026-10-03.md)，历史规则不是新许可
- [最新空间收据](harness_lanes/results/gd_storage_final_cleanup_2026-10-03.md)
- [findings](findings.md)、[progress](progress.md)
- 旧implementation/execution/worker/review/space卡保技术背景，其流程/顺序由本页覆盖。已交付harness不再派发同一工作。

## Next Step

旧 Worker 的公开执行与启动链已退役，生产无残留进程/登录任务。CWP producer-budget WIP 包含额度模型、CLI参数、失败关闭检查、回执二次校验及bounded JSON进程桥接；发现并修复deadline之后未记录provider已实际消耗usage的缺陷，TDD两项RED/GREEN，最终六文件集中回归 **41 passed / 14.83s**。跨仓模拟HTTP E2E发现1个候选、PDF 399 B、发现+下载计费713 B且精确吻合。StockInfo隔离分支 `codex/cninfo-bounded-budget@947e839`（父提交 `1693045`）已实现流式CNINFO discovery/PDF限额；当前CWP配置仍指向原 `v2-clean-rewrite` 并配置 provider 1.1.0、未声明能力，因此按默认false保持fail closed。StockInfo分支focused test先前61 passed；本轮补跑51项到达100%但pytest未输出终结摘要，进程挂在退出阶段后被中断，不计作完整新绿。FF-S3 `_command_arguments()` 已把同一请求的bytes/seconds/cost传入ensure/close-gap，`_shared_deadline()`统一全请求时限；Dayu保持不改且不支持硬限额。StockInfo分支尚需进入owner集成工作树、CWP配置显式切至1.2.0并经过正式FF跨仓E2E，之后才可合FF-S3。

### S3 bounded provider transport：固定桥接合同

- 唯一先实现的生产 transport 是 CNINFO。StockInfo 原工作区在实施前有24个tracked修改和未跟踪CNINFO adapter/client/test；不得直接编辑。已基于 `1693045` 建立隔离分支 `codex/cninfo-bounded-budget`，commit `947e839`（13个精确相关文件），实现provider-local预算和CNINFO discovery/PDF流式读取；原工作区保持不变。该分支已推送（最新会话网络不可达，未能再次远端核验）；仓库未发现Actions workflow。Dayu 是纯外部项目，代码不改；HK/US 遇到硬下载 cap 继续外发前拒绝。
- CWP `JsonCommandAdapter` 增加 `discover_bounded` / `fetch_bounded`。子进程 JSON 请求附加 `acquisition_budget`：恰含 `schema_version="1.0"`、`max_response_bytes`（本阶段剩余额度）、`timeout_seconds`（单调 deadline 剩余秒）、`max_cost_usd`（十进制字符串）。CWP subprocess timeout 取配置 timeout 与同一剩余秒数的较小值。
- 支持 bounded 的 provider 对每个 discovery JSON / PDF HTTP响应按块读取；检查本阶段 deadline，并在接纳每块前拒绝超过 `max_response_bytes` 的响应。成功 JSON 必须包含 `acquisition_usage`，恰含 `schema_version="1.0"`、`response_bytes`、`cost_usd`；CWP 校验形状后把两项记入共享 `AcquisitionBudget`。漏报、额外字段、非法数、超预算、进程超时一律失败；fetch回执大小还须由 CWP 独立复核。
- 一个 `AcquisitionBudget` 对象贯穿 ensure/close-gap 锁外及锁内 metadata discovery、CNINFO分页、fetch与staging，不因子进程/分页重置；未知失败不重试已部分消费的预算。CNINFO当前收费为零，由provider明确报告 `"0"`，不将“没有成本数据”伪报为零。provider CLI 无预算的 legacy调用保持既有合同。
- TDD 大节点：CWP 命令适配器进程测试证明预算被传递、真实elapsed timeout、usage缺失/少报/超额失败；StockInfo 测试用分块假响应覆盖 discovery 与 PDF cap边界、deadline、cleanup `.part`；正式短根跨进程 E2E 从 CWP budgeted `ensure` 到 StockInfo JSON CLI，确认发现+下载共享总字节、精确SHA/回执、第二次失败时不留part/staging且没有第三方/生产文件变化。Dayu负例确认子进程 marker不存在。集中责任包通过后才启用CN bounded能力并与FF-S3运行正式E2E/汇合。

CNINFO provider transport已完成代码与模拟HTTP跨仓E2E，但尚未集成进当前CWP配置工作树。不能仅因配置切换就开放能力：先将StockInfo隔离分支纳入provider owner集成线，再把CWP配置版本改为1.2.0并显式声明supports_acquisition_budget，执行FF正式入口E2E；预算、latest_as_of复用和legacy v1请求语义也要一并验证。Dayu不支持的硬限额请求继续在外发前拒绝。CWP producer-budget改动仍为未提交WIP，最终集中测试41项通过；PWF整理后作为一个完整阶段提交。

## S2 当前交接与下一集中节点

- N4A scope、N4B 真实模型计量、持久预算、production factory、有限 CLI、终态降容、跨 run 工件绑定、run/generation 自动 owner、父进程 kill 恢复与提交 ACK 丢失幂等已实现；相关提交 `ff5396c`、`9ccd29f`、`9041543`、`d2250b7`、`54db2a2` 均已推送。
- 2026-10-03 只读现场检查：旧 worker `desired_state=paused`、`runtime_state=stopped`；匹配 worker/supervisor 均为 0，Windows startup task 未安装。随后删除旧全库 CLI、启动/恢复/暂停与安装任务入口、Windows 启动器/控制菜单及旧启动专属测试；保留 `worker-status`、身份核验 `worker-stop` 与启动任务检查/卸载。旧 raw、SQLite、worker state 和日志均未触碰。
- 155 项相关回归此前 153 项通过；两项失败都是过期断言（deletion manifest 已退役、旧 `resume` 方法已删除），更正后对应 2 项单测复跑通过。CLI/显式下载退役合同另有 18 项通过。
- 仍不把 S2 标记完成：N4C 的真实模型小批、消费者实读、引用/语言 coverage 与全量新增空间峰值仍未验收；先完成 CWP producer limits，再进入 N4C。
