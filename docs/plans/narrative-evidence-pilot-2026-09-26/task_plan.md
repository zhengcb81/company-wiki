# 公司来源平台：门禁先行、虚拟化收口与叙述批次总计划

> 2026-10-03 用户采纳八束激进方案并要求继续实施。本页是唯一当前施工顺序；旧Phase 1–64、W/G卡和审查要求只供技术追溯，不再产生任务或签收门。历史版本：https://github.com/zhengcb81/company-wiki/blob/bff81afe7cbb11c895764a94c2eabd121539e248/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md。原文不丢；旧无限Worker保持paused，新的显式有限批次按本计划上线。

## Goal

完成八束整套简化：一个下载请求入口、一套pathless来源接口、一套AUTO任务系统，按需选择业务叙述、摘要和检索；停止全量永久转换与重复正文；完成真实模型、持久预算、可恢复多文档处理及消费者接线，然后分批删除无调用者的旧派生。原件、来源/版本事实不丢。RF/FF/ET/StockWiki/IQS各仓独占写入，不修改其他owner未提交工作。

**当前恢复点（2026-10-05）：**目标active；用户确认[P5三卡](harness_lanes/p5_parallel_packages_2026-10-05.md)已开工，RF/FF/新存储工具独占写集保留。MAIN模型thinking/null截断计量修复92 Unit、正式CLI 2 E2E GREEN；用户已明确永久授权指定公开来源向MiniMax做原语言摘要。真实run02终态budget_exhausted，IR/TXT收到HTTP客户端拒绝（当前收据未保留数字status），年报/招股在保守token预留前拒绝，synthetic skip PDF为PARSER_INCOMPLETE；无新final，RF真实消费未验收。总charged含旧unknown为33,660 tokens/$0.016580（保守预留，不是供应商账单）；下次剩余26,340/$0.083420，先查拒绝和计量/入场原因，不盲目扩大cap或重复付费。原件/生产/用户配置/RF owner不变，测试根恢复absent，收据[n4c run02](harness_lanes/results/n4c_live_2026-10-05_run02.json)。RF固定已提交main8a153f3只读复用，不切owner树。

**最近发布验收：**修复提交`b09e845a845e172a3659acef6ad6d172f7565d2f`已推送`origin/master`，快速pre-push契约门GREEN；[精确SHA的CI](https://github.com/zhengcb81/company-wiki/actions/runs/37354477263) completed/success（job约77秒，含完整Unit）。清除两个旧卡永久Git工作树门；保留所有产品/原件保护测试。收尾文档`f775406`已发布；当时paused状态已由本次用户恢复撤销。

## 2026-10-05 四仓状态与当前主线

本节为当前执行状态，优先于下方较早的baseline、并行线状态和 Next Step 历史文本。

- **Revenue Forecast**：fcap 的 DWA-04R 有价值证据载体/账本以 merge commit `8a153f3387ae75fb172e70f8ab63ffd38100779a` 推到 `origin/main`；保留主线 UC/hash-pending 语义，UC 聚焦测试 29 passed。稀疏 worktree 的 `tools/pre_push_gate.py` 不存在，故只记录对应钩子跳过，不宣称该门通过。
- **StockInfoDLSimple**：`codex/cninfo-bounded-budget` 已快进并推送目标支线 `v2-clean-rewrite@8ed5fdd`；provider 单测 171 passed，CWP provider contract/E2E 20 passed。owner checkout 剩余 WIP 保留，CWP 用户配置未动。
- **filing-fetch**：SourceRef v2/companion 功能已在主线；旧 schema 原型不并入。PWF 收尾提交 `d4d2fac` 已推送 `fcap:main`，plan claims 与 push 选择门通过。
- **Dayu**：用户本轮要求的唯一现有 `opt/cn_score@76037b2` 提交已快进到本地 main，相关 focused tests 87 passed；远端 push 被 HTTP 403 拒绝，停止重试。该项是已有提交的本地集成，不代表远端已更新。
- **外部审计卡**：StockQAbyLLM 与 MeetingConverter 报告已收到并验收，唯一运行数据保留。invest-quick-scan 另有独立项目正在进行；本线不检查、不修改、不重复派发该仓任务。
- RF worktree audit 外线分支 `codex/rf-state-audit@447d1c7` 已有一份受 ACL/长路径限制的补充报告；它与主线已有同名完整报告冲突，不能直接覆盖或并入。补充报告没有可安全删除候选；本机 `config/source_acquisition.yaml` 用户改动和本计划审计结果目录继续排除在本线写集之外。

**恢复后的MAIN下一步：**阶段parse/select/replay控制实验已完成，不重复跑三档E6。以有限P4为候选完成一个独立N4C真实模型多文档批次，记录Worker各阶段耗时，并复用RF已提交的N3a公开读取验证summary/locator、语言/引用coverage、预算与空间峰值。旧未知费用不清零，新run绑定selector `0.3.0`；执行范围、剩余额度与清理边界见本次收尾收据。用户明确恢复前不启动；RF默认SourceBundle迁移前保留旧derived与reader。表格发现的几何预筛选只是候选优化，尚未证明不漏无框表格/Q&A，不据此删覆盖或阻塞下一大节点。

**N4-T2 selector实现状态：**基础实现`ea9dd26`基于`4807c01`并已发布；选择性吸收外包差异的实现提交`0657579d`已发布，Actions #37273071081对精确SHA成功。外包交付`2b5bec9`基于N4-T1提交`4a53080`，82项测试、Ruff与diff check全绿，工作树干净，但无正式外包验收文档。逐路径对比后未整支并入：主线多数行为已存在；保留外包对景气/生产运营/境外业务用词及新设业务单元事件的高价值补充，拒绝去掉具体动作条件、以及按“无词汇命中”自动跳过季度/业务文档。主线新增合成PDF覆盖四类业务信号、titleless季度/IR路由、套话/目录排除和每个span的字节定位回放；信号全无的真实季度仍`needs_review`。改良选择器后的E6真实Worker P1/P2/P4复测为1 passed/246.39s，详细吞吐、队列等待和内存数据见[MAIN selector实现与验收](harness_lanes/results/n4t2_selector_acceptance_2026-10-05.md)。N4-T2外包差异已收口，接下来推进N4C，不再等待或合并重复分支。

**S5旧写者与RF依赖核验（2026-10-05）：**CWP `SourceCatalog` 仍公开 `normalize/summarize/summarize_with_llm` 包装方法，底层旧normalizer、extractive/LLM summarizer与section extractor仍在；针对 `src/` 和 `scripts/` 的精确引用检索没有发现业务入口直接调用这些包装方法，旧合同测试仍大量调用。`llm_summarizer.py`、`summarizer.py`、`section_extractor.py` 仍经 `read_verified_normalized_text` 读取物理normalized正文。RF缓存 `origin/main@8a153f3` 的 `source_reader_v2` 默认值仍是 `false`，旧SourceBundle仍承担默认读取。故先在N4C验证新叙述产物，再由RF owner切换并验默认消费；之前保留旧reader、artifact句柄和文件，不能把“CWP没有自动Worker”当成“RF已不读旧产物”。RF本地 `main@6fb2def`、`fcap@5319ee2` 与 `origin/main@8a153f3` 不同；正常账号只读盘点只有`assurance/runs/weekly_alert.jsonl`和`weekly_manifest.json`两项owner修改，本线不清理/修改。已以`ls-remote`核live main，未做fetch；沙箱ACL导致的旧删除计数已纠正。

**S5空间实测（2026-10-05，真实用户工作目录，只读）：**`.source_catalog/derived` 为7,104个文件/2,826,010,634 B：3,528个 `normalized.md` 共2,748,621,075 B（约97.3%），596个 `sections` 文件共67,624,394 B，2,980个 `summary.md` 共9,765,165 B。normalized是降容的首要目标；成功迁移前不得删。只读SQLite结果为page_count 746,055、freelist 0、EvidenceSpan 1,490,530；artifact行有normalized completed 4,842/partial 127/unsupported 15、sections completed 238、summary completed 2,969。该扫描不触碰companies原件、不写数据库；文件逻辑长度不是已释放磁盘空间，未来删除后仍需实测free-space。

## 当前基线（2026-10-04正常用户上下文复核）

| 项目 | 已发布/已验收事实 | 本机状态与本轮边界 |
|---|---|---|
| CWP | `master@9d97814`与`origin/master`基线一致；G1-LEGACY、SourceExport等已发布 | 本轮PWF/E2E文件为本线改动；本机 `config/source_acquisition.yaml` 与repository-audit结果文件保持用户/审计线原样，不纳入本线 |
| RF | `revenue-forecast fcap@5319ee26`；N3a pathless消费者已有 | 提升权限复核确认仅2项tracked变更（weekly alert/manifest）；owner文件保持不动。`rf-impl` 当前工作树也不作为本线写集 |
| FF | `eb0af13`已推送`origin/main`；SourceRef v2和FF→ET companion接线已测 | 本地`fcap`与远端main相同；未跟踪`config/FMP_API_KEY.txt`保持未读、未暂存、未推送 |
| ET | ET-S3、bounded-runtime和deadline hardening均已在`main@63c4090`，远端同步 | ET deadline候选已按快进合入；`.workbuddy-ai/`和`eval_results.json`仍是未跟踪并原样保留 |
| N4 | scope、持久预算、factory、有限batch、kill/ACK恢复与终态降容节点A/B已有集中GREEN | N4C真实多类型批次、1/2/4并行与总空间实测仍待做，不重复开发A/B |
| 空间 | 最新完整盘点32,821,613,206 B是首批清理前历史值；原件25.20GB、DB3.06GB；此前释放13.06GB，本轮另删除138.65MB | 本轮923缓存文件已删除；derived约2.826GB仍须迁caller，DB旧全量span未删；不把算术减法当重新完整实测，原件不进清理候选 |
| CI | 单Python快速代码CI约56–62秒；commit无pytest，push/CI同一精选集合 | 不恢复全Contract/coverage日常门；纯Markdown不要求新CI |

StockWiki/IQS已有owner工作及消费者交付，本轮只读，不重复分派。Dayu为纯外部项目，零代码修改。已验收细节留在findings/progress和既有报告，未提交内容不自动视为已合入。

## 实施顺序与完成条件

| 步骤 | 当前状态 | 实现范围与输出 | 验收合入位置 |
|---|---|---|---|
| S0 简化收口 | complete（ff5396c，CI绿） | PWF只留当前入口；删除R1旁路签收/shadow/gold；commit移除pytest、config doctor按相关文件触发 | 一次相关Unit/混合行为回归与正常发布；不逐文件签收 |
| S1 N4A | complete（ff5396c，CI绿） | scope贯通Store/Worker/Supervisor/outbox/prepared，None兼容、空scope零修改、范围SQL先于LIMIT | N4节点A，确定性RED先行 |
| S2 N4B | complete（节点A/B集中验收已绿；整体N4仍待独立S4/N4C） | real factory/HTTP adapter/full prompt; persistent token/cost reservation in AUTO; finite batch CLI; unique final artifact and small recovery receipt; public legacy whole-catalog Worker and startup routes removed | node A accounting/concurrency green; node B formal CLI/HTTP/kill/ACK and focused regression green; CWP producer limits are now connected and have real-data E2E evidence; proceed to N4C after G1/S3 closeout |
| G1 残余门禁/签收精简（第一优先） | complete（CWP来源链与G1-LEGACY已合入；FF SourceRef v2于`e1eda60`推送） | 46项清单已分为已退出、必要自动校验、能力边界及外仓owner事项；未找到生产调用者的旧摘要/binding/archive工具不再作为当前门，留待S5/S6 caller清理 | CWP来源/as-of 64项、resolver/planner/canonical 100项与G1-LEGACY 170 passed / 1 deselected既有收据；FF集中回归177 passed / 1 skipped / 39 subtests，Ruff及push gate GREEN；电话会provider→CWP导入端到端12 passed。保留SHA、来源身份/期间/公开日、可回放引用和资源限制 |
| S3 SourceRef/SourceExport 虚拟化与来源默认收敛（第二优先） | **complete**（FF `eb0af13`、ET `63c4090`已推送；CWP SourceExport已发布；合入后FF→ET→CWP链及各仓责任集均GREEN。live FMP仍受HTTP 402权益限制，不影响接口合同完成） | 上层只用SourceRef/SourceExport v2；复用FF exact/latest_as_of和pathless reader，不依赖物理目录；电话会走正式ET CLI并由CWP持有原件；provider定位仍在adapter层 | ET deadline分支已快进到main；其`/1`、`/2`、discovery/candidate wire与goldens未改，CWP importer现有provider-aware FMP JSON合同经真实三仓离线链验证。跨仓脚本验证FF uppercase exchange转ET小写、精确FY/Q、FMP原JSON与canonical text各自SHA/size、unknown publication、pathless SourceRef、重复读取不触provider，以及超时后worker结果清理。合并后ET `tests/test_retrieval_cli_e2e.py` 6 passed、10 goldens matched；FF companion 5 passed且Ruff clean；CWP FMP importer 5 passed。FF只在owner目录用`eb0af13`修正交易所slug与3秒清理窗口；ET只更新过期golden说明并合入`63c4090`。旧“Motley 24字段唯一可导入”记录已由当前源码/测试更正。真实FMP HTTP 402不作为代码合同门；正费用额度没有实际账单计量，本计划只声称FF zero-cost拒绝与单次provider请求，不声称美元账单cap已实测。 |
| S4 N4C real samples and storage plan | **in_progress; 已恢复，MAIN独占**（CWP transport真实四类型4 passed；RF N3a真实年报+电话会15 passed；E6 P1/P2/P4通过：当前93.006/89.453/62.527s，RSS分别373,583,872/459,042,816/686,489,600 B；旧P4 29.091s/630,353,920 B。已完成新旧parse/select/replay对照及`0.3.0`版本修复，不放开并发。RF/CWP跨仓实Worker消费、真实provider usage、第二IR/季度叙述覆盖及总增量空间仍待完成） | four real document types / actual bounded batch and consumer reads / language and citation coverage / total incremental bytes; retain only status/stop/uninstall compatibility for old worker process cleanup | 运行一个有限批次及RF N3a读取，一次大节点记录阶段耗时、总字节、预算、重试/锁、引用/语言与目录恢复；不重复已绿A/B与三档E6。P5三外线同时编码，不作为N4C屏障 |
| S5 B2逐caller清理 | in_progress（首批缓存、extract-sections、旧自动 Worker/阶段策略与旧WorkerSession启动/心跳API已退出；normalized/summarize按需接口等RF与CWP读者迁移后再退） | [S5/S6实施细则](s5_s6_legacy_storage_implementation.md)；不再有旧Worker创建入口，worker-status/stop保留并检查既存旧runtime snapshot；旧 normalized/summary 数据和 API 未删。RF远端 main 已有SourceRef v2 opt-in，但默认旧SourceBundle artifact bundle仍消费 normalized。历史 derived 2.826 GB / 8,191路径引用仍保留，等待caller迁移 | 旧Worker主循环集中127 passed；本轮status/stop、CLI保留与AUTO暂停互锁集中55 passed，commit `a9b1a06` 已推送，CI run `37246820601` success；每个存储大节点复核来源事实/消费者与前后空间；不逐文件签收 |
| S6 DB事实收缩与收尾 | pending | 表级盘点，删除不可再消费派生/废索引并收缩，来源版本/撤回事实保留；旁路兼容、docs/hook残留清完 | 同一存储节点；commit/push、PWF收尾 |
| 可选 exact-SHA原件对象去重 | 不阻S0–S6完成 | 先用已有SHA/size找候选、逐候选验字节，保留所有source/location版本事实 | 有真实收益才实施；不报未测节省量 |

## S0已完成技术记录

- 删除scripts/gate_runner.py、reviewer_gate.py、gate_state.py、gold_review_gate.py；删除automation/handlers/gold_review.py、human_inbox.py与source_catalog/source_lifecycle.py、readiness_graph.py及仅服务它们的测试。
- registry/planner/doctor同步去gold/analysis占位映射，保留timer与通用历史BLOCKED_HUMAN状态；不DROP历史表、不改Store lease/fence/预算。
- 混合测试迁移环境隔离到已有clean_env_gate helper，保留原件不入candidate、生产原件不变和故障真实失败断言；不能整文件删test_writer_freeze/hermetic/acceptance。
- read_chain删已退出shadow模块的handoff，writer_policy删不存在脚本的旧allowlist。AGENTS/architecture静态引用随实际功能退出；已停用研究writer可分批删空壳，来源职责仍保留。
- activation/rollback/restore reviewer已改可选运行记录。prompt签名/TTL旧写工具已在G1退役并保留旧诊断读取；六个完成的一次性archive工具已核caller，改由G1-LEGACY优先退出，不再等S6。签名格式若有真实消费者先薄兼容，不能伪造host_signed。
- commit保相关Ruff、有限mypy/路径静态检查，无pytest；config doctor仅config/配置加载代码改变时触发。push精选一次、CI全Unit与同精选一次。coverage/complexity数字改诊断，不为数字拆helper。

## 最小正确性与接口责任

1. 存储层：原件immutable、实际open验bytes SHA、路径包含与写入归属。上层只用SourceRef，不重复判断company-wiki/dayu/Dropbox目录。
2. 来源层：公司/证券/期次/公开时间、版本与撤回事实；缺非核心采集字段可partial，不伪报verified。默认公开日期cutoff；当前不为未有需求的retrieved-at严格快照新增模式或配置。
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

[并行总计划](parallel_execution_plan_2026-10-03.md)统一列分工与合入；MAIN保持G1→S3→N4C→S5/S6顺序。当前可给外部harness的独立包：

| 包 | 独占实际工作目录 | 写入责任 | 合入位置 |
|---|---|---|---|
| [G1-LEGACY](harness_lanes/g1_legacy_entry_and_retirement.md) | `Projects/company-wiki-g1-legacy` | 明确脚本/专属测试；不改src、共享Contract、配置和总PWF | 第一优先G1 |
| [ET-DEADLINE](harness_lanes/et_retrieval_deadline_closeout.md) | `Projects/earnings-transcripts-s3-deadline` | ET正式两个入口硬采集deadline及子进程测试；已验收并合入 | 已在`main@63c4090`，不再派发 |
| [ET-LIVE](harness_lanes/et_transcript_live_import_acceptance.md)（已完成一次性尝试） | `Projects/company-wiki-et-live-20261004` | 单次真实工具调用与临时根报告；生产仓只读 | 报告已交；FMP HTTP 402 entitlement，live import 为 NOT RUN |

G1-LEGACY已合入；ET-DEADLINE交付和只读盘点已接收：`0017f24`为远端支线唯一独有提交，worktree干净。旧责任包91/1失败是此前快照，交付人报告已修正夹具并记录92责任项、全量172 passed、10 goldens；只读审计没有重跑，缺独立CI链接。ET-LIVE一次性报告为HTTP 402且未重试。MAIN独占CWP共享接口、总PWF与最终跨仓合入；先跑隔离fake-provider跨仓CLI→importer→SourceRef联调，绿后再并线。

FF-S3、ET-S3、SPACE-S5、StockWiki W01/W04、SourceExport与既有消费者线均已交付，不再重派。RF/StockWiki/IQS active owner树不另开代码线；Dayu不改。需要共享接口变更，外线交root协调，不擅自升级wire或扩张写集。

## 验收与发布

TDD框住公开行为，不把旧签收规则写进新测试。仅S0相关收口、N4 A/B/C、存储迁移几个大节点；helper/每文档/每删除文件没有人工审查。修复具体红灯后重跑相关包，不为了可选复杂度/覆盖率/固定场景数量全仓长测。

正式端到端测试使用独立短根、同OS账号创建/执行/finally清理；本地HTTP/模型请求也必须显式测试预算。真实资料副本原来不存在则退出删除。生产配置/control/原件fingerprint前后不变；不把失败夹具留在生产或仓库。正常commit/push，代码CI绿后记录；纯Markdown不要求新CI。

## 当前文档导航

- [已采纳的八束方案](radical_simplification_proposal_2026-10-03.md)
- [G1收口施工细则](gate_simplification_closeout_2026-10-04.md)
- [G1-LEGACY独立代码包](harness_lanes/g1_legacy_entry_and_retirement.md)、[ET-DEADLINE独立代码包](harness_lanes/et_retrieval_deadline_closeout.md)
- [N4接口/TDD/正式batch详细卡](n4_production_batch_implementation.md)
- [ET-LIVE电话会原文导入与虚拟化独立验收卡](harness_lanes/et_transcript_live_import_acceptance.md)
- [46项原审计基线及2026-10-04覆盖更新](gate_permission_inventory_2026-10-03.md)，基线日期不变；当前状态以新增覆盖节为准
- [最新空间收据](harness_lanes/results/gd_storage_final_cleanup_2026-10-03.md)
- [S5/S6旧派生退出与来源库降容实施细则](s5_s6_legacy_storage_implementation.md)
- [findings](findings.md)、[progress](progress.md)
- 旧implementation/execution/worker/review/space卡保技术背景，其流程/顺序由本页覆盖。已交付harness不再派发同一工作。

## Next Step

**MAIN下一动作：**按用户要求实测MiMo/DeepSeek，使用配置入口新增的`--llm-provider`，保持8192/温度/各家地址和Key来源。配置与安全响应诊断集中责任集139 passed（135 Unit +4正式CLI/Worker/HTTP E2E）；默认MiniMax不变，MiMo按已配置fallback选取，DeepSeek复用同一Config已有defaults，不临时改thinking。用户纠正后已统一MiMo `mimo-v2.6-flash`、DeepSeek `deepseek-flash`；二者正式配置 `/models` 均HTTP200、配置模型在清单中。DeepSeek旧401是项目dotenv覆盖有效环境密钥，已TDD修复；无须用户更换密钥，真实摘要POST仍待做。旧试点run04失败且未知用量最坏记账24,863tokens/17,304microUSD，累计58,523/33,884，另保留2,764汇率余量；剩余1,477tokens不足一次配置调用。已询问累计token上限提高到160k、美元仍限$0.10；答复前不突破旧cap。获同意后先MiMo处理P07中文IR、T01英文电话会+零模型policy；DeepSeek同样样本对照。每家独立run/账本，累计包含旧未知账；Mimo Token Plan记Credit与保守PAYG等价费用代理，不能写成现金账单。真实入口→Worker→final→CWP公开read→RF N3a读取，核完整引用/原语言/用量/峰值/重复运行零额外调用并恢复测试根；集中节点验收，不增加小节点人工审查。RF已提交消费模块完整六文件依赖在首次模型POST前校验；本次导出/CLI help实测退出0，零模型，临时根恢复。P5正式交付尚未到，RF live main仍8a153f33、owner两份assurance保持不动。采样修复0ae191a已推送且精确SHA CI37365773471成功。整体N4C、S5/S6未完成。

## 2026-10-04：新增三张可独立派发的施工卡

三张卡均已交付：N4-T1已集成MAIN；MeetingConverter已验收、合入并发布master且主线CI绿；N4-T2已完成差异对账、选择性吸收及验收。本段原写集和接口仅供交付追溯，不重派已完成卡。StockQAbyLLM 与 MeetingConverter 先前的只读盘点交付仍按已有收据验收；invest-quick-scan 仍由其独立任务负责，本计划不检查、不修改、不重复派发。

| 卡 | 仓库 / 隔离工作树 | 精确责任 | 与其他卡的隔离方式 |
|---|---|---|---|
| [N4-T1 模型传输错误诊断](harness_lanes/n4_model_transport_diagnostics.md) | company-wiki 新建独立 worktree | automation 的HTTP模型适配、错误分类、预算账本诊断及对应测试；不修改选择器/调度/配置/生产来源 | 与N4-T2代码目录及测试文件完全不重叠；两者只共享只读的当前主线基线 |
| [N4-T2 中文叙述选材覆盖](harness_lanes/n4_selective_narrative_coverage.md) | company-wiki专用worktree；串行可复用T1目录 | source_catalog选材/路由/收尾与selector测试；增强中文季报、IR中的行业、业务进展、新业务、出海证据选取 | 不修改automation模型传输、Worker/AUTO、共享wire、配置或PWF；只提交本线分支，不合main |
| [MeetingConverter CI 快速门](harness_lanes/meetingconverter_ci_fast_gate.md) | MeetingConverter 新建独立 worktree | 只调查和修复CI零任务/无实际测试问题，限定CI工作流、专用配置测试和本线HANDOFF | 在独立仓库施工，不读写company-wiki业务代码、StockQAbyLLM、IQS或任何转录资料 |

N4-T1与N4-T2文件写集互斥。并行施工时从同一已提交主线基线创建两个worktree；串行施工时可复用一个专用worktree，T1测试结束且commit后再做T2，T2以T1交付HEAD为base，分别报告每张卡的commit范围。无需每张卡再等人工许可；同目录不能同时施工，也不使用MAIN当前checkout。两卡交付后由MAIN按先后顺序整合并运行跨模块测试及Worker端到端验收。MeetingConverter卡与CWP N4C完全异步，可以独立完成，不进入N4C关键路径。卡片中的路径、测试、边界、handoff字段和禁止操作是交付接口；外部harness只需拿对应卡，无需本总计划全文。

### N4C复盘：已证实的问题与尚未证实的原因

- 2026-10-04隔离运行n4c-20261004-wave1已停止且不重跑：四个SourceRef的原件SHA/身份可验证；年报选择出3条span，招股书选择出160条span但summary触发预算拒绝；中文季报和IR均零候选/零span并报PARSER_INCOMPLETE。失败账本没有HTTP状态/响应摘要，因此不能反推MiniMax那次请求究竟因HTTP错误还是2xx响应格式失败。
- 此前可观测性缺口已由N4-T1修复：HTTP状态按4xx/5xx归类且安全数字状态保存在attempt中，未知用量保守计费不变。MAIN已有持久账本E2E证据；不能宣称这已证明旧请求根因，也不能降低未知用量按预留上限计费的规则。
- 季报和IR的正式来源读取、PDF抽取、表格覆盖均成功；选择器仍未选到业务叙述。N4-T2优先以离线合成中文案例证明选材与跳过逻辑；不得把解析未覆盖当成“无叙述可跳过”，也不能以财报数字span代替主营进展证据。
- 旧运行约0.005258美元的未知预留继续保留在旧run账本；不得复用该run id或把未知费用清零。新真实模型检查由MAIN在两张N4卡集成且离线验收后另建run，并受剩余批次预算约束。

### 新施工卡导航

- [N4-T1 模型传输诊断卡](harness_lanes/n4_model_transport_diagnostics.md)
- [N4-T2 叙述选材卡](harness_lanes/n4_selective_narrative_coverage.md)
- [MeetingConverter CI快门卡](harness_lanes/meetingconverter_ci_fast_gate.md)
- [并行总计划与隔离合同](parallel_execution_plan_2026-10-03.md)

### 已完成：ET-DEADLINE 并线前 FF→ET→CWP 离线契约联调

**目的：**验证已交付deadline分支通过真实命令行/子进程，被FF实际调用并由CWP importer接收，最后通过CWP exact query与SourceVersionReader verified-open读回。测试覆盖ET分支 `0017f24`，不以独立ET单测或历史Motley E2E代替此链路。

- **测试布置：**从CWP根运行 `python -B tests/e2e/run_ff_et_cwp_offline_acceptance.py --ff-root <filing-fetch> --et-root <earnings-transcripts-s3-deadline>`。脚本创建唯一TEMP scratch；FF使用真实`resolve_companion_transcript`与`EarningsTranscriptsTransport`，执行候选分支正式ET CLI；ET `transcript_tool.main`→supervisor→worker→FMP parser/serializer照常运行，只有HTTP session由私有launcher注入有限假响应；CWP真实`source_query_cli`、`transcript_import_cli`、`source_reader_cli`与catalog运行。脚本不是CI长测，不mock ET抓取、FF调用或CWP导入。
- **成功/幂等断言：**精确MSFT/FY2026/Q3请求；provider golden字节原样存储、SHA/size/MIME一致，原语言且不翻译；SourceRef只有公开pathless字段，unknown publication不伪造日期且不进入历史as-of；第二次同请求返回同一SourceRef、provider调用为0、raw仅1份。key不进入输出/日志，HTTP调用计数为1，ET worker结果目录为空，scratch退出后确已删除。
- **当前FMP合同事实：**ET `/2` FMP golden为26字段JSON；当前CWP有独立FMP provider合同并已能精确存储原JSON字节，unknown-publication过滤由`tests/contract/test_transcript_import_cli_e2e.py::test_fmp_unknown_publication_cli_stores_original_but_excludes_historical_cutoff`覆盖。此前“CWP只接Motley 24字段”的只读发现和ET golden README均已过期；本轮不增加CWP adapter，不改ET wire，不伪造publication date。ET-LIVE HTTP 402只说明真实provider权益未确认，fake契约测试照常运行。
- **费用语义：**FF目前只将`max_cost_usd=0`作为禁止provider调用的条件；ET wire不返回实际美元计费。本次验证exactly-one provider request与请求内的正费用门槛，不声称positive dollar cap已按实际账单计量。若FMP未来按请求额外收费，需先确认计价规则，再由owner把“请求次数/价格”映射到预算；不能把subscription entitlement猜成0成本。
- **截止时间/恢复断言：**集成脚本另用5秒有限fake响应和2秒provider cap，检查FF的外层等待是否覆盖ET worker deadline及清理宽限；超时不得导入raw，worker和ET结果scratch必须为空，随后整个测试scratch消失。首次运行复现了旧FF行为：FF与ET同为2秒外层timeout，7秒后ET `et-retrieval-*`仍遗留；FF已改为ET最大60秒合同、先预留3秒清理时间，外层子进程等待最多“ET worker deadline+3秒”，总FF余时不足3秒时不启动下载。
- **已执行验收：**三仓离线脚本先在候选`0017f24`、再在合入后的ET main上均成功；包括提供商slow response deadline和目录清理。FF `tests/test_transcript_companion_transport.py` **5 passed**、Ruff clean；ET `tests/test_retrieval_cli_e2e.py` **6 passed**、10 goldens matched；CWP FMP importer **5 passed**。pytest basetemp和三仓脚本scratch逐一确认删除。没有付费网络或LLM请求。
- **并线收据：**FF adapter修复`eb0af13`已推送FF `main`；ET文档说明修正`63c4090`随deadline实现快进合入并推送ET `main`。ET main/candidate同指`63c4090`；ET原先未跟踪的`.workbuddy-ai/`、`eval_results.json`保持原样。CWP源catalog配置未改。
- **关口结论：**成功原文hash/size、FMP与canonical text哈希分离、身份和FY/Q、unknown-publication、幂等、pathless reader、timeout/worker cleanup及测试scratch恢复均通过。无需再改CWP importer；不等付费FMP账户证明fake provider合同，也不声称positive dollar limit被实际计价。

该门通过后，按顺序进入N4C真实样本/并发/空间测量，再做S5/S6；不额外增加逐helper或逐文档人工审查。

**外线状态：**G1-LEGACY和ET-DEADLINE已合入；FF companion deadline/exchange修正和ET consumer-contract说明均已推送。ET-LIVE因HTTP 402没有可导入付费正文，因此N4C如需ET样本应先检查现有本地TXT来源是否已合法进入CWP；不把live provider entitlement当作代码验收。所有跨仓验收使用fake-provider；MAIN保留共享合同协调权，不重派ET工作、不加逐helper/逐文档审查。

以下保留已验收producer桥接技术细节，**不是新的下一步**：

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
- 当前按节点分清状态：S2/N4B节点A/B已验收；整体N4仍未完成，因为独立S4/N4C的真实模型多文档、消费者实读、引用/语言coverage与总新增空间峰值未验收。producer limits已完成，本轮先G1→S3，再N4C；不把N4C待验收写回S2重新开工。

## 2026-10-05 — RF叙述消费者与S5物理依赖复核

- **RF状态先查**：本次正常用户会话最近一次 live 检查记录 `origin/main@8a153f3387ae75fb172e70f8ab63ffd38100779a`；本 sandbox 不能连 GitHub（HTTPS/443受限），只读本地确认 `fcap@5319ee263c4af41ac255938c25bebd32cce56f66`，其本地 `origin/main` ref 仍为 `8a153f3`。不得把缓存 ref说成本轮新鲜live远端检查；跨仓实施前须先重查 owner/PWF/远端。
- **RF已有叙述合同**：`docs/implementation/reviews/narrative-consumer/N3a-RF-2026-10-03.md` 定义 RF `narrative_source_preparation.py` 通过 bounded subprocess 使用 CWP `company-wiki-narrative-read`；`NarrativeRef` 是 metadata-only，read 输出来源叙述、选中EvidenceSpan/locator、摘要草案及可核验receipt。报告包含89项E2E责任集（含年报PDF与电话会TXT本地原文样本），没有声明把结果写入收入预测。该报告明确标注“未接入收入计算”。
- **两条路径不得混称**：RF N3a叙述消费者与 RF filing `source_reader_v2` opt-in 是不同接口。后者在 `source_preparation.py` 默认仍为 `false`，当前默认 `SourceBundle` 继续读取旧 normalized/summary/sections角色；N3a能够读叙述包不能证明默认财报准备和收入计算已经接线。复用已有N3a，不再新建CWP/RF wire合同。
- **CWP文件/DB依赖更正**：当前 `EvidenceQueryService` 从SQLite读 `evidence_spans.raw_text/span_json` 与source/document/location事实，不读normalized Markdown文件。`ExtractionQualityService` 从SQLite读normalized artifact状态/metadata及EvidenceSpan，不打开artifact正文。CWP当前直接调用 `read_verified_normalized_text` 的源码位置是 `llm_summarizer.py`、`section_extractor.py`、`summarizer.py`；section-extractor的公开CLI/Service入口已退休，但不能据此把低层函数/所有调用者都算已清除。故保留EvidenceSpan行不必然阻止物理Markdown释放；但必须先迁移RF的旧SourceBundle读者和CWP仍在用的摘要/章节读者，并处理artifact记录指向已删除文件与quality status的含义。物理文件与数据库span分阶段处置，不能捆成一次删除。
- **RF worktree audit交付状态**：`codex/rf-state-audit`两条仅文档提交新增了受限报告；它因6处ACL拒绝而停止全量未跟踪分类，0 bytes列为“已确认可安全释放”。主线同路径已经存在更详细的audit报告，且明确不可读子树是覆盖/删除结论的边界。保留补充报告的限制结论，不覆盖主线报告、不从该分支执行任何RF操作。
- **CWP真实原件transport E2E（仅子节点）**：2026-10-05在当前代码执行`test_narrative_transport_real_samples.py`，4项通过/31.70秒；覆盖年报、招股书、IR活动记录、电话会TXT的原件SHA、实际公开CLI返回、完整locator replay。Capture metadata来自隔离fixture；这不代表生产catalog准入、N4 selector/Worker摘要、RF bounded consumer接线或N4C批次已验收。basetemp按项目path guard自动重定位，报告退出已清理；详情在progress/findings。
- **后续大节点（收尾后更新）**：N4-T2已收齐，改良选择器E6 P1/P2/P4已复测。用户恢复后按Next Step执行一个有限真实provider批次，复用已提交RF N3a read/reference合同，对实际Worker产物记select/skip、语言、完整locator replay、usage、总字节及consumer read；不重复Replay三档或空fixture合同。后续将叙述接入预测计算/切换SourceBundle默认，由RF owner按届时PWF负责；之前不改RF。S5物理正文、artifact句柄与S6数据库span仍分阶段迁移。
