# 公司来源平台：激进简化与叙述批次实施总计划

> 2026-10-03 用户采纳八束激进方案并要求继续实施。本页是唯一当前施工顺序；旧Phase 1–64、W/G卡和审查要求只供技术追溯，不再产生任务或签收门。历史版本：https://github.com/zhengcb81/company-wiki/blob/bff81afe7cbb11c895764a94c2eabd121539e248/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md。原文不丢；旧无限Worker保持paused，新的显式有限批次按本计划上线。

## Goal

完成八束整套简化：一个下载请求入口、一套pathless来源接口、一套AUTO任务系统，按需选择业务叙述、摘要和检索；停止全量永久转换与重复正文；完成真实模型、持久预算、可恢复多文档处理及消费者接线，然后分批删除无调用者的旧派生。原件、来源/版本事实不丢。RF/FF/ET/StockWiki/IQS各仓独占写入，不修改其他owner未提交工作。

执行已恢复。最新 `get_goal` 实读为 **active**（2026-10-03）；此前工具无resume接口的限制已由应用实际恢复解决，不再把旧paused快照当当前状态。目标未完成，不标complete。

## 当前基线

- CWP master/origin/master 9ccd29f，S0/N4A和模型/持久预算基础已发布，CI37135709529成功；S2正式CLI/降容首组67绿但恢复收口仍待完成。G-A/N3a/G-C、B1/B3/B4均完成，不重新验收整个历史。
- RF rf-impl main 6fb2def7/4项tracked dirty；原fcap 5319ee26保留。FF真正origin/main/交付线c47c397，常用根仍fcap d35b6f5；ET main4924d57 tracked干净。StockWiki master已推进aa98848/4项quick-scan dirty；IQS master44b805f在继续实施。外仓各自owner，不reset或重复派线。
- 最新完整空间32,821,613,206B/32.82GB，公司原件25.20GB，current DB3.06GB、旧derived/index约2.87GB。已释放13.06GB不再重复计收益；原件不进入清理候选。
- 真实代码CI约56–62秒，单Python/全Unit/精选回归；不恢复全Contract/coverage日常门。

## 实施顺序与完成条件

| 步骤 | 当前状态 | 实现范围与输出 | 验收合入位置 |
|---|---|---|---|
| S0 简化收口 | complete（ff5396c，CI绿） | PWF只留当前入口；删除R1旁路签收/shadow/gold；commit移除pytest、config doctor按相关文件触发 | 一次相关Unit/混合行为回归与正常发布；不逐文件签收 |
| S1 N4A | complete（ff5396c，CI绿） | scope贯通Store/Worker/Supervisor/outbox/prepared，None兼容、空scope零修改、范围SQL先于LIMIT | N4节点A，确定性RED先行 |
| S2 N4B | in_progress（正式CLI/终态降容首组67绿；跨run/owner/kill/ACK待收口） | 真实factory/薄HTTP model adapter/完整prompt；同Store持久token/费用预留；有限batch CLI；唯一final正文、终态恢复小记录 | 节点A记账/并发、节点B正式CLI本地HTTP/kill/ACK/空间 |
| S3 来源与采集默认收敛 | in_progress（英文召回子项绿；FF/ET ready未派，CWP默认/caps pending） | R2/R6：一请求、薄v1适配、相关字段fingerprint、缺元数据partial、published-asof；FF执行limits/ET旧入口一致；安装技能示例同步 | root CWP与FF-S3/ET-S3在一个接口大节点汇合 |
| S4 N4C与旧Worker退出 | pending | 四类真实文档小批/consumer读取/语言引用coverage与总容量；迁移control实际调用者，唯一AUTO执行器、短提交锁 | 节点C；先有限批次，再按实测1/2/4调整并发 |
| S5 B2逐caller清理 | pending | 每集合无引用即可删约2.87GB旧derived/index；停用功能直接退役，未要求全库先生成摘要 | 存储迁移节点真实回读/原件保留/实际bytes，逐集合幂等 |
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

R1/N4A临时分工已完成。新的外部harness分工见[并行实施总计划](parallel_execution_plan_2026-10-03.md)：MAIN独占company-wiki；FF-S3独占filing-fetch-s3-limits worktree；ET-S3独占earnings-transcripts-s3-runtime worktree；SPACE-S5只写独立company-wiki-storage-audit-20261003目录、所有生产仓只读。三卡均可现在开工，ready不代表已派出。root保持总指挥、CWP producer/全局安装/跨仓大节点集成；接到用户派出消息后登记running，不重复施工对应包。

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

发布已绿的S2 CLI/终态降容及S3英文召回阶段、交付三条独立卡；随后root补S2跨run工件身份/自动owner/kill与ACK恢复，CWP S3实际采集limits与来源默认。FF/ET/空间卡可现在由用户分派，等待只发生在最终接口汇合；未交付模块不写complete。不启动旧无限Worker，不删除原件。

## S2当前交接与下一集中节点

节点A已实现真实HTTP、完整prompt1.1、成对usage、AUTO v3同库持久预算、BudgetedNarrativeCaller与production factory并发布9ccd29f。正式 `company-wiki-narrative-batch` / `python -m company_wiki.automation.narrative_batch_cli` 和terminal receipt已实现首组67绿：同run零重复HTTP、原文错误保持真实费用、0费用/小空间cap零外发、exact工件可回读、完成DAG去正文。自动OS mutex复用到基础设施层，gate CAS/scoped obsolete generation reaper保未知reservation；不写第二queue或人工许可。parse/HTTP在Catalog短锁外。

S2剩余两项已实读风险：不同run同源的effect/work_key尚缺job/版本作用域，会发生同内容effect跨job冲突或异内容work_key冲突；generation只fence旧attempt，不能阻空闲scope=None daemon重新claim。root在真实production小批前先修跨run身份并收敛统一启动owner，不能靠previousrun+ENABLED猜可接管；对应两run/旧pin/父kill/ACK恢复集中在节点B。每run独立work-dir、同run复用baseline，不能覆盖已存baseline。

English entered new markets/pilot agreements已TDD修为selector0.2.0，114+70责任包绿；safe-harbor/会议/纯金融负例仍跳过，parser未改。S3其他默认/caps及S4–S6仍未完成；不借阶段提交标全部完成。outbox原来只保存小Effect metadata，主要去attempt.result重复正文，不能虚报outbox GB收益。
