# N6-CANDIDATE 主线集中验收与两质量线组合

2026-10-07。接收 codex/n6-candidates@f31cc0d（实现9a4b815、交接ce61cdd），保留外线提交，MAIN负责修正与共享接线。当前master3f0bc2a、预算selector0.3.3已发布；RF main6e6b817a三owner日志、用户source_acquisition.yaml SHA3609e707只读保护，不跨写外线/外仓，不改生产配置/原件。

## 顺序与完成标准

1. 实际merge合法写集；审查跨块补全的source/role/language/page/问答与发言人边界、8单位上限和可注入OperatingFactDetector。补明确反例先RED，MAIN修正，不删除旧断言。
2. 为新quantified_operating_status提供预算语义映射（产品结构/产能经营状态，固定96/160），共享selector升0.4.0；候选Rules安全默认生效，不另造parser/状态库/接口。先集中短责任包与Ruff/mypy，不重复外线长测试。
3. 两线齐备后运行既有九样本正式全表benchmark一次，另存新小报告，原samples/golden/86点/required33不改。保留0.3.2基准12/33，逐点报告提升、回退及scope解释。定位必须全部可回放；若仍漏真实经营事实，先诊断具体阶段，责任修正/针对性复测，不每个helper重跑全表。
4. 独立短tmp一次正式真实年报/IR/英文电话会Worker→outbox→CWP search/exact→RF已提交consumer→恢复E2E，0供应商/下载/费用。同时冻结旧final兼容与实际AUTO升级隔离在新代码通过。使用配置好的确定性test profile，不动生产LLM配置；不能把这当真实供应商摘要质量。
5. 核原件/用户配置/生产库/owner保护与tmp恢复；正常提交推送，核精确代码SHA CI，最后三份总PWF与小收据发布。日常CI不加九样本/真实长E2E，不增加人工签收。

## 状态

交接已读取，开始实际合入/责任审查。空间cf24f34、预算3cd4960的CI已绿，不重验已完成线；本节点只核组合影响。外线“精确CI37528050044”是历史DOCSET运行，不能用于本次代码验收；最终记录新实际SHA。

## MAIN实测与修正（当前收口中）

17个MAIN责任用例逐批见RED后修正；最终269责任项2.81秒、CI范围Ruff与8源模块mypy通过。除初始9边界与经营类别映射，还补忙页第二category竞争、产品客户端量产验证分类、逐句补全不继承全页理由/跨句组、一般工程开工与未来建成/投产timeline、existing候选完整fact reason传播。原件/parser0.1.0/定位/96和160限额不变。首两次真实E2E均在EPI业务断言失败（54.16秒和53秒），明确修实现、不减断言。

初次九样本报告n6_combined_quality_initial_2026-10-07.json：18/33、764定位零失败、重复3、精选67047B、403.731秒。发现年报旧G04回退与S08两条新噪声，集中归因并修选择责任层后进行最终正式复验；原报告保留。S08一个219字orphan cell包含数字编号4/5的问答和套话，后续QA解析整改不能假称本卡已修，仍计入噪声。

真实Worker/RF/search/exact/恢复四业务断言现已通过；最终11项组合结果、九样本逐点对照、保护与恢复、提交SHA和精确CI另附小收据。本卡实现验收通过与S7语义整改全部完成分开：若仍缺具体经营事实，列后续责任步骤，不冒称已达到完整质量目标。没有真实供应商/下载/费用，生产final仍不在此次测试生成。

## 最终本地验收结果

- 真实九样本全表372.044秒：required21/33（旧12/33），optional5/17（旧4/17）；旧required与optional所有full点零回退。原86点、33分母、scope与golden字节不改。
- 764定位全部回放/0失败，重复3（旧48），精选66195B（旧72042B），runner scratch峰值61277B。只是标注范围选材结果，不是全文/摘要语义覆盖率。
- 明确业务/项目上下文命中20/29（解释子集，不改正式分母）；remaining9：G-S01-01/03/05、G-S02-02/03、G-S04-03、G-S06-02/03/04。原required剩余12另含G-S06-01、G-S09-01/03三个纯财务/provider边界点。G-S09-04收入guidance随原始句子入选，不能把它称额外业务覆盖。
- 负例3条噪声：G-S01-11重复段、G-S08-05接待套话和G-S08-06参阅既有记录；judged noise3/40，194个in-scope未判定，不能说剩余正文都干净。IR两条已归因旧orphan cell，后续parser责任整改保留原事实与定位。
- 269短责任项2.81秒、Ruff、8模块mypy绿；真实正式三文档+旧final9+AUTO升级1共11项66.48秒绿。EPI与原年报项目G04最终full，初次退步已纠正。
- 两次benchmark的scratch与本次8个测试/包装根均恢复absent；小报告与逐点对照收据保存，原件0删除/修改、外仓/owner/生产配置零写、0供应商/下载/费用。正常并线提交推送与精确CI随后写入同一收据。

[最终全表报告](harness_lanes/results/n6_combined_quality_final_2026-10-07.json)、[MAIN逐点对照/保护/发布收据](harness_lanes/results/n6_candidate_main_acceptance_2026-10-07.json)。实现集中验收本地passed；S7仍in_progress，不能以三张外包卡结束冒充整体资料质量全部完成。
