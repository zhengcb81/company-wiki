# 原目标逐项核查与主线验收

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> 2026-10-07：16项在下述明确范围内已有实现及验收证据。原A12/A13两处日期语义缺口已获授权、TDD修复、实际主线六CLI验收；CWP ee0d1e7已推送，精确CI37575052423全部步骤绿70秒，必要施工无剩余。不是全历史资料和自动投资研究均已生产运行的声明，不新增人工签收或日常长测试。

## 当前权威状态

RF main/远端 e241389，精确CI全部步骤绿30秒；StockWiki本地master9f552a6、无远端。RF三日志与CWP用户source_acquisition修改保留，StockWiki clean。既有运行代码aa52cbd/7aa88ae及FF758e8f4/ET2b9fb84证据仍有效。

[本次实际主线验收](harness_lanes/results/final_asof_implementation_2026-10-07.json)及两个独立交接收据取代“未落地”的当前状态；[此前只读核查](harness_lanes/results/final_scope_acceptance_2026-10-07.json)与历史RED收据只作历史保留。九原件、生产DB及六保护文件不变，全部本次临时根恢复absent。

## 核查方法

已读最初[设计思想](../../../设计思想.md)、当前AGENTS职责边界、架构、N4/S5/S6/S7细则及实际测试/运行入口。设计初稿中的研究时间线和投资综合判断现归StockWiki；CWP只供应来源资料。旧卡、旧“待交付”和旧预算不能恢复成当前任务。

证据必须匹配责任范围：检查真实CLI/Worker/存储/consumer代码，以及测试实际断言和已发布收据，不能仅数绿灯。既有源码祖先和代码SHA可复用；没有实现变化或新的风险，不重跑已绿九样本、付费模型、kill/ACK长套件。未来公开的反例在当前六CLI中由producer首先拒绝；不能拿此结果冒称已独立验证两个消费者的所有日期分支。

## 逐项结论

| ID／原要求 | 结论 | 实际实现、测试与权威证据 | 证明边界／剩余 |
|---|---|---|---|
| A01 原设计、分层、各层负责本级任务 | 已证实当前约定 | 最初设计、AGENTS、`docs/ARCHITECTURE.md`；SourceVersionReader／SourceExport v2存储边界；`test_source_export_v2.py`实际迁根、任意root label、孤儿span／同size坏字节反例；G-C消费者只产自有来源DTO | 不把初稿投资研究writer重新放回CWP；不承诺各仓所有其他模块都已重构 |
| A02 停止永久全文PDF→MD→全部切片 | 已证实 | 有限 `narrative_batch` 正式入口；旧无限worker/writer退役；S5生产7104文件、8191 handle、1490530旧span处置；终态compaction真实接入 `_final_documents` | 原件保留，临时解析不等于永久全文存储；不重新启动全库daemon |
| A03 九类典型文档的小范围试点 | 已证实有界样本 | S7正式九原件86点、固定33 required：年报/半年报/季报/招股/增发/可转债/两类IR/英文TXT；29/33，761 locator全部回放，角色混淆0 | 这是定向标注范围，不是全文、全公司或全部历史资料的召回率 |
| A04 业务／第二曲线／海外／行业／募投优先，财务和程序内容跳过 | 已证实有界策略 | S7通用正反例及年报/招股/TXT正式Worker→outbox→RF/search/exact；N6固定96/160预算、原子事件组与经营类别；IR句级QA；policy skip零模型 | 混合IR保留事实，不按文档类型整份删；部分解析不伪报无业务；未承诺提取所有可选信息 |
| A05 miss和取舍透明，原标准不缩水 | 已证实 | S7保留86点/33分母；四required miss及同原件S06 page7 canonical完整产能另测；原golden未改，optional三项取舍逐项记载 | 纯融资金额、正文外provider摘要、纯guidance不塞入业务摘要凑分；重复6/761、optional2/17仍公开 |
| A06 原语言、遵守配置、多模型实测、坏claim恢复 | 已证实有界能力 | run05/06/08/10实际MiMo/DeepSeek；`Config.load/model_options_from_config`；R6来源/语言/引用验证与有效claim保留，真实TXT→配置CLI→RF读取 | 不翻译；旧timeout/截断/unknown不消账。电话会六类主题精选6/6、摘要5/6，GPU效率未单列；本地HTTP不冒充供应商模型质量 |
| A07 原文预览、精选检索/exact、旧版本读取 | 已证实 | SourceRef打开实读SHA；公开transport/read/search/exact；S7新真实链＋冻结旧final9＋实际selector升级1。SourceExport CLI禁止扫描/网络并核原件与数据库不变 | 只检索精选资料；旧pin按旧parser回放，不重选旧final，不持久化第二份全文 |
| A08 多文档并发、计算/模型隔离、有界运行 | 已证实配置范围 | 当前Supervisor `P1=mixed1/P2=compute1+model1/P4=compute3+model1`；每子进程自有client。`test_p2_processes_two_sources_concurrently_and_preserves_same_source_dependency`实际断言不同源起止时间重叠、同源后续不早于前置结束；正式N4批次多文档 | P4不是四模型并发；没有承诺所有任务都提速或多供应商同时调用的实测收益。遵守配置，不开无限进程 |
| A09 kill/失联/ACK丢失可恢复、幂等、跨批隔离 | 已证实故障范围 | 正式batch recovery实际杀协调器、阻断首次HTTP返回，再按原run恢复；cross-run原件/外国任务不变；outbox租约过期旧token失效；prepared/ACK后进程退出重协调；`test_reservation_reconciliation_tolerates_lost_commit_acknowledgement`先真commit再抛超时，重试不重复计费 | 外部响应丢失时费用未知仍保留预留，不承诺供应商exactly-once退款；不能把普通resume当kill证据。已读n4c_prompt_node的14个不同正式用例收据 |
| A10 时间/token/费用/空间总上限、终态降容 | 已证实明确边界 | 一套AUTO budget事务；未知usage/超限实际usage持久；BatchStorageBudget统计DB/WAL/objects/work并排除原件；final2MiB、增量1GiB、scratch2GiB；deadline7aa88ae的57责任／五CLI；terminal integration核final读前后相等、三attempt正文压缩、第二次no-op、费用/job/effect/outbox不变 | deadline协作式，已开始同步I/O及收尾不能瞬间打断。active/retry/prepared/未ACK不能提前压缩；费用是配置代理而非供应商账单 |
| A11 FF调用ET、公司目录统一保存TXT、不翻译并进入处理 | 已证实离线契约及本地复用 | FF→ET→CWP真实三仓CLI/supervisor/worker/serializer/import/query/open，只在provider HTTP seam确定性替换；P5-FF发布758e8f4；ET2b9fb84的92项、10goldens，43真实旧TXT只读audit；TXT直接解析无PDF转换 | 不冒称免费网络已下载；FMP真实402是套餐边界。43旧TXT标legacy_unverified，不伪造历史下载收据；新下载才写SHA/期次sidecar |
| A12 RF/StockWiki/其他消费者通过抽象接口消费 | 已证实约定消费范围 | RF默认pathless v2与真实原件读；StockWiki公开narrative CLI自有DTO；G-C迁根/hash/身份/期间/skip证据；当前六CLI普通早下载可读且spans逐条相等 | 原两例真实RED现由RF e241389/StockWiki9f552a6修复，实际六CLI6pass；IQS有独立项目不改；不宣称RF全部预测计算或StockWiki自动研究同步已完成 |
| A13 去掉多余人工权限、门禁、审计签收 | 已证实约定精简范围 | 46项清单/G1实现及诊断故障测试；private/public人工许可、prompt/review/待修复提案、release人工签收、签名/TTL、shadow/WU退出；reader稀疏collector/URL/capture诊断不阻断 | CWP/FF/ET相关清理完成；两消费者重复下载日限制已取消，公开日/格式反例保留。SHA/身份/期次/公开日期/原件路径保护/预算/事务属各层自动正确性，保留 |
| A14 降空间、原件不丢、不过度备份演练 | 已证实处置范围 | S5/S6生产净释放5659443210B、raw删除0；DB3055841280→222408704B；当前只读17表count/digest＋九raw SHA/size/mtime对已发布基线一致。N6 footprint单根逻辑24365900191B，raw约96.3% | 不恢复完整46GB备份演练；云占位1007跳过、物理allocated未知；raw exact-SHA去重可选，不计未实读/未删除的节省 |
| A15 E2E独立测试根、结束恢复原样 | 已证实已执行节点 | N4/R6/S7/deadline/日期反例各自finally与保护fixture；本次已读terminal/fault样例；各正式收据记录根absent、原件/生产/用户/owner不变 | 只清自身新路径，不清未知owner目录。本轮授权隔离修复的两个worktree/三个测试根已恢复absent，原件和生产指纹不变 |
| A16 TDD、各层单元/集成/E2E、大节点验收、快CI和及时并线 | 已证实已发布节点 | S7真实8功能RED→200责任项＋11真实/兼容/升级绿；deadline5功能RED→57责任＋五CLI；N6三包实际祖先与精确CI；当前hooks/workflow实读 | commit静态、不跑pytest；CI单Ubuntu3.12全Unit＋短合同、5分钟上限，近期精确代码CI53–83秒；长九样本/真实模型不进日常CI。原A12/A13实际RED已TDD修复与当前两仓正式CLI验收 |

## 证据导航

1. [S7最新质量／正式链／保护](harness_lanes/results/s7_adoption_fundraising_main_acceptance_2026-10-07.json)，[IR节点](harness_lanes/results/s7_ir_main_acceptance_2026-10-07.json)，[业务范围解释](n6_main_business_expectations_2026-10-06.md)。
2. [真实模型与完成边界](main_completion_evidence_2026-10-06.md)，[真实业务复核](harness_lanes/results/n4c_live_business_review_2026-10-06.json)，[R6细则](r6_partial_summary_implementation_2026-10-06.md)。
3. [N4生产批次／并发／恢复](n4_production_batch_implementation.md)，[14例正式CLI/fault节点](harness_lanes/results/n4c_prompt_node_2026-10-06.json)，[准备deadline发布](harness_lanes/results/final_batch_deadline_acceptance_2026-10-07.json)。
4. [跨仓消费G-C](harness_lanes/results/gc_consumer_closeout_2026-10-03.md)，[P5 FF](harness_lanes/results/p5_ff_main_acceptance_2026-10-05.json)，[P5 RF](harness_lanes/results/p5_rf_main_acceptance_2026-10-06.json)，[ET TXT](harness_lanes/results/n5_et_text_main_acceptance_2026-10-06.json)。
5. [G1细则和自动正确性](gate_simplification_closeout_2026-10-04.md)，[46项分类](gate_permission_inventory_2026-10-03.md)。
6. [生产空间处置](harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)，[当前只读来源事实](harness_lanes/results/final_current_source_facts_2026-10-07.json)，[单根footprint](harness_lanes/results/n6_footprint_main_scan_2026-10-06.json)。
7. [当前两消费者RED／隔离副本GREEN](harness_lanes/results/final_consumer_asof_audit_2026-10-07.json)。CWP证据代码a8f2513对应CI37558926678全步骤success/73秒，**仅证明本仓回归，不证明外仓已修复**。

## 2026-10-07 授权实施与主线验收

用户“授权隔离修复并线”已执行。RF `e241389adeda37bc9cbb53d7831063718552a936` 正常快进 main、推送 origin/main，精确 CI 37574397700/job112639930230 全部步骤成功，用时30秒。StockWiki `9f552a6741dd093dc760ad6965458989cd027251` 正常快进本地 master；本仓没有远端，不声称已推送或有远端CI。

两仓先各获得2个真实语义RED（晚下载和公开日等于cutoff），再最小修改日期判断，保留 UTC/公开日/身份/期间/SHA/locator反例；没有改原件、公开wire或golden。RF责任58pass/1skip、快速门107pass及正常push门107pass；StockWiki责任113pass/1skip。StockWiki集中大节点首跑934pass/15skip/1个Windows长路径环境失败，同一失败用例改独立短测试根后1pass：共935个不同用例绿，coverage总81%、UI75.56%，不是单次全套全绿。未重跑全部长测。

当前CWP→实际两仓主线正式CLI六例6pass/29.63秒，逐条证据一致，RF只导出现场已提交HEAD，删除临时提案覆盖入口。这是日期合同的本地Replay E2E，不冒称新增付费模型或真实供应商下载；两个消费者自己的未来/未知公开日等分支另由责任包证明。

本次两个独立worktree和三个测试根恢复absent，移除136471537 B临时代码/测试资料，不计为生产清理收益。九原件SHA/size/mtime、生产DB完整SHA及六个配置/owner文件指纹保持。RF三owner日志和CWP source_acquisition用户修改不暂存、不覆盖；StockWiki owner工作树clean，quick-scan/IQS未改。两套安装技能仅在校验旧主线字节后同步本次两文件，其他本地内容保留，不宣称整套安装完全一致。

完整[主线验收收据](harness_lanes/results/final_asof_implementation_2026-10-07.json)、[RF独立交接](harness_lanes/results/final_rf_asof_handoff_2026-10-07.json)、[StockWiki独立交接](harness_lanes/results/final_stockwiki_asof_handoff_2026-10-07.json)。历史RED/提案GREEN收据保留，不能替代本次实际主线结果。CWP本次测试/文档已正常提交推送：ee0d1e7，精确CI37575052423/job112641956369全部步骤绿70秒；六跨仓CLI为另行本地集中验收，不冒称日常CI执行外仓E2E。本轮必要施工全部完成。

无其他已证必要施工待办。可选raw去重、全历史资料生产处理或自动投资研究不混入本轮收口。
