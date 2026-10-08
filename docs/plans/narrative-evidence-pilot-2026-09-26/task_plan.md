# 公司来源平台：唯一当前施工入口

**2026-10-08｜目标 active，全部PWF尚未完成。** G2–G5已验收并线发布；R2真实生产来源修正/TXT登记完成。R3尚未POST、production final仍0，必要token增量待答。R5文档与临时归属部分提前实施，最终验收须等R3。

## Goal与边界

完成全部PWF及引用实施细则的约定内容，不用试点或缩小范围代替完成。原件/来源版本/历史usage不丢；CWP供应来源、精选业务描述、原语言摘要和可回放证据，投资研究语义属于StockWiki。上层只使用SourceRef/SourceExport v2/NarrativeRef，存储目录由来源层处理。一套AUTO/lease/generation/outbox，解析与模型分别有界，不启旧全量永久PDF→MD/无限worker。

MAIN负责共享接口/生产/总PWF/并线；Dayu零代码修改、IQS独立项目不写。其他仓owner WIP保持；CN只用StockInfoDLSimple的v2-clean-rewrite，不维护旧StockInfoDownloader main。删除的人工review/许可/签收/canary开关不恢复；保留真实字节SHA、身份/期间/公开日/版本、写入归属与资源限制。测试只在大节点，测试根恢复，无每helper或每commit长pytest。

## 实际进度与证据

| 阶段 | 当前状态 | 权威证据与范围 |
|---|---|---|
| S0–S2/N4 A/B并发恢复 | complete | [完成证据](main_completion_evidence_2026-10-06.md)、[N4细则](n4_production_batch_implementation.md)：scope/隔离进程/预算/kill/ACK/outbox；不重造队列 |
| S3来源虚拟化 | complete（来源接口范围） | SourceRef/Export v2、FF→ET→CWP、迁根及当前RF/SW正式读取；不等同完整预测算法 |
| S4/N4C/R6局部摘要质量 | complete（明确试点范围） | [run10真实业务复核](harness_lanes/results/n4c_live_business_review_2026-10-06.json)、[R6节点](harness_lanes/results/r6_partial_summary_node_2026-10-06.json)；隔离真实模型不能代替R3生产final |
| S5/S6旧派生/数据库 | complete | [生产收据](harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)：净释放5659443210B，原件0删除，DB3055841280→222408704B |
| S7九文档质量 | complete（已约定有界范围） | [后续质量单](s7_followup_quality_implementation_2026-10-07.md)：29/33 required、761定位回放，四miss/optional取舍/重复6真实保留，不改golden |
| G1/G2门禁补漏 | complete | [G2最终验收](g2_consolidated_node_2026-10-08.md)：14组/A-B，50e42f2/精确CI37702678973绿；RF/FF实际定点安装完成 |
| G2–G5与早期所有已发包 | 已交付/验收，不重派 | [G5正式验收](g5_main_acceptance_2026-10-07.md)、[G4](g4_main_acceptance_2026-10-07.md)、[G3](g3_main_acceptance_2026-10-07.md)，旧W/F/D/P/N卡通过导航保留 |
| R0完整计划对账/R1融资分类 | complete | [全PWF实施单](all_pwf_completion_implementation_2026-10-07.md)、66ce0467/真实两PDF分类与精确CI |
| R2真实生产来源/请求准备 | complete | [R2细则](r2_source_preparation_implementation_2026-10-08.md)：6ae7ddc正常推master/精确CI37705927320全绿、101责任+九原件E2E绿；4restore/9facts/TXT66324B+589B，重复0新增 |
| R3正式生产与当前跨仓消费 | in_progress：R3A complete；live待token答复 | [R3A细则](r3_current_material_read_implementation_2026-10-08.md)：producer4c5590a/RF main c672a5e/SW master42fba06，四真实原件公共CLI节点1通过/0skip、RF及CWP f0ad6b9已推/精确CI绿，定点安装完成；[完整请求](harness_lanes/results/r3_production_batch_request_2026-10-08.json)、[实测预检](harness_lanes/results/r3_production_request_preflight_2026-10-08.json)仍需真实final/skip/语义/恢复/空间 |
| R4可选原件对象化 | complete：依据收益不迁移 | [G3事实验收](../../implementation/g3-source-facts/MAIN_ACCEPTANCE.md)：注册重复上界94.3MiB、实读额外34.5MiB，allocation/releasable未知，未删原件；见全PWF实施单 |
| R5文档/历史临时/最终发布 | in_progress，最终未验收 | [R5卡](r5_cleanup_and_navigation_implementation_2026-10-08.md)：8个owned临时根清119913476B/1123文件，26保护SHA及生产DB stat不变；历史pilot账本保留 |

## 已授权预算与唯一下一动作

当前累计上限仍 **200000 tokens/$0.12**；已占190035tokens/100502microUSD、历史unknown7/unsettled0、FX guard2764不清账。余9965tokens/16734microUSD，费用为代理估算，不是账单。已问仅将token提高220000，**尚无答复**，不能据请求文件或新目标认为已批准。

现配置DeepSeek Flash/8192/温度1的生产TXT实际49精选段，body10873B，完整预留19193tokens/14591microUSD。单batch额度恰为该预留，只允许一次真实请求；真制度零模型。配置经Config.load，不改端点/输出/温度/thinking/价格绕限。MiMo既有mimo-v2.6-flash保持，DeepSeek key使用环境变量，密钥不保存。

## Next Step

[R3A](r3_current_material_read_implementation_2026-10-08.md)已发布/精确CI完成，不重做已绿RF/SW/三仓/安装节点。既有token增额答复到达后，在CWP根执行[全PWF实施单R3](all_pwf_completion_implementation_2026-10-07.md#r3-真实生产有限批次及跨仓验收)的已备唯一请求，不POST绕额度、不假结算旧unknown。生产公共阅读显式`as_of_date: null`；历史unknown仍拒绝。R3一次大节点验证正式final、真制度skip、原语言/来源支持/locator、ref/search/exact、当前已提交RF/SW、同run新增POST0与对象/DB/WAL/scratch；完成后R5完整要求审计和发布才可完成目标。

## 当前导航与历史

[实施单](all_pwf_completion_implementation_2026-10-07.md)定义命令与完成条件；[findings](findings.md)保存当前事实/风险；[progress](progress.md)保存已做/错误/下一责任；[本目录README](README.md)导航历史卡。历史全文固定Git链接：[6dd5601完整主计划](https://github.com/zhengcb81/company-wiki/blob/6dd56011a7d49e2b8c147f2163b0708074f9edd7/docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md)。旧paused/待签收/待并线/旧额度仅历史，不产生当前任务。
