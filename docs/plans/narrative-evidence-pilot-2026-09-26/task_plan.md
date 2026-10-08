# 公司来源平台：唯一当前施工入口

**2026-10-08｜全部约定实施及最终实质验收完成；R5仅余文档提交推送。** R3正式生产、语义、跨仓消费、恢复、空间、清理均通过；[完整要求对账](r5_full_closeout_2026-10-08.md)覆盖全部计划家族。模型累计上限220000 tokens/$10，旧费用与unknown保留；无需再批准。完成最终发布后才将目标设complete。

## Goal与边界

完成全部PWF及引用实施细则的约定内容，不用试点或缩小范围代替完成。原件/来源版本/历史usage不丢。CWP供应来源、精选业务描述、原语言摘要和可回放证据；投资研究语义属于StockWiki。上层使用SourceRef/SourceExport v2/NarrativeRef，目录归存储层。一套AUTO/lease/generation/outbox；解析与模型各自有界，不启永久全文PDF→MD或无限worker。

MAIN负责共享接口/生产/总PWF/并线。Dayu零代码修改，IQS独立项目不写；其他owner WIP不回退、不混入提交。CN维护StockInfoDLSimple的v2-clean-rewrite，不维护旧StockInfoDownloader main。人工review/许可/签收/canary不恢复；保留真实SHA、来源身份/期间、历史公开时点、版本、写入归属与资源正确性。只在大节点测试，测试副本恢复，不加每helper审查或每commit长pytest。

## 全部阶段

| 阶段 | 状态 | 权威证据与范围 |
|---|---|---|
| S0–S2/N4并发恢复 | complete | [完成证据](main_completion_evidence_2026-10-06.md)、[N4细则](n4_production_batch_implementation.md)：同AUTO、隔离子进程、lease/generation/outbox、预算、kill/ACK恢复 |
| S3来源虚拟化 | complete | SourceRef/Export v2、FF→ET→CWP、迁根/真实读取。目录不进入消费DTO；不等同完整预测算法 |
| S4/N4C/R6摘要能力 | complete | 四类真实模型、[run10](harness_lanes/results/n4c_live_business_review_2026-10-06.json)、[R6](harness_lanes/results/r6_partial_summary_node_2026-10-06.json)；现另有R3正式生产证据 |
| S5/S6旧派生/数据库 | complete | [生产收据](harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)：净释放5659443210B、原件0删除、DB3055841280→222408704B |
| S7九类质量 | complete（约定有界范围） | [质量节点](harness_lanes/results/s7_adoption_fundraising_main_acceptance_2026-10-07.json)：29/33 required、761回放、四miss/optional/重复6保留；不改golden |
| G1/G2门禁补漏 | complete | [G2最终验收](g2_consolidated_node_2026-10-08.md)：十四组/A-B、真实安装/重复0写、签收/canary及旧入口退休 |
| G2–G5/早期外包 | complete | [G5](g5_main_acceptance_2026-10-07.md)、[G4](g4_main_acceptance_2026-10-07.md)、[G3](g3_main_acceptance_2026-10-07.md)；约定交付已验收并线，不重派 |
| R0/R1完整核查/融资分类 | complete | [完整实施单](all_pwf_completion_implementation_2026-10-07.md)、原设计/16要求和102项历史目录继任对账 |
| R2正式来源事实/TXT | complete | [细则](r2_source_preparation_implementation_2026-10-08.md)：四restore、九facts、TXT66324B+589B，重复0新增，精确源码CI绿 |
| R3正式生产与当前消费 | complete | [正式验收](r3_production_acceptance_2026-10-08.md)：2 visible、1模型POST、20claims/49证据、三仓公共CLI、制度0模型、同run新增0、空间588030B、原件保护 |
| R4可选原件对象化 | complete：证据决定不迁移 | [G3事实](../../implementation/g3-source-facts/MAIN_ACCEPTANCE.md)：实读extra34.5MiB、allocation未知；不为小收益迁引用或删原件 |
| R5导航/清理/完整发布 | in_progress：实质审计complete，最后文档发布 | [最终对账](r5_full_closeout_2026-10-08.md)、[R5细则](r5_cleanup_and_navigation_implementation_2026-10-08.md)；全部家族已核，最后commit/push待完成 |

## 最新生产事实与预算

既有Config.load DeepSeek Flash/8192/温度1/default thinking/timeout60保持，MiMo mimo-v2.6-flash既有配置保持。本次英文电话会9499tokens/估算10235microUSD，真制度0模型；总199534tokens/110737microUSD，历史unknown7/unsettled0、FX2764照计。当前余20466tokens/$9.886499（代理估算，不是供应商账单）。[授权](harness_lanes/results/r3_budget_approval_2026-10-08.json)、[实账](harness_lanes/results/r3_production_live_batch_2026-10-08.json)。不因额度扩大而换配置、清账或启动全库处理。

当前普通资料使用显式as_of_date:null，未知公开日/采集时间/登记语言保持未知；派生检测语言单列。历史ISO仍检查公开日，不让current读取自动变成预测资格。所有来源/工件SHA和49定位验证。正式AUTO=.source_catalog/automation.sqlite3，work=.source_catalog/r3；成功final为正式资料，保留。一份106792B英文业务工件+1457B制度skip，整个库逻辑新增588030B，scratch峰106792B，终态work/log仅212B。重复同request/run没有新模型/attempt/费用或对象。

CWP源码6cd9b6d/CI37736338454，RF源码343e2de及依赖pin7cf337e/CI37737193724，SW源码1ebe012，独立交接后6d1dddb consumer源码相同，无remote。正常提交/push门均绿；不重复已完成端到端或付费生成。

## Next Step

正常提交/push这次R3/R5 PWF与薄收据，确认CWP实际远端HEAD与本地一致、工作树只含可解释资料；更新最终发布状态并将原目标complete。全部必要新增实施项为空。不启动新外包/无限worker/原件删除/订阅采购。未来新增工作须有新具体需求。

## 导航

[实施单](all_pwf_completion_implementation_2026-10-07.md)、[最终对账](r5_full_closeout_2026-10-08.md)、[findings](findings.md)、[progress](progress.md)、[README](README.md)。旧120卡顶部指向本入口；旧paused/待签收/旧预算仅历史。原完整日志固定在已推[6dd5601](https://github.com/zhengcb81/company-wiki/tree/6dd56011a7d49e2b8c147f2163b0708074f9edd7/docs/plans/narrative-evidence-pilot-2026-09-26)，不复制大归档。
