# M3 接线细则（工程已实施，真实节点继续）

当前M3b工程实现见 fidelity-production-wiring/README.md；下文为设计合同，真实保真、恢复和RF实际采用仍须分别验收。生产默认尚未切换。

## 必须固定的行为

1. 新明确projection `reading-model-input/6`、prompt `reading-source-scoped/4.2.0`、request `narrative-model-request/7`；旧/4、extractive/5身份与wire不改标签。新行为先显式opt-in，完成消费者和恢复验收再切生产选择，禁止按selector/source_owned布尔开关偷偷替代旧协议。
2. 共用scoped request/compiler/decoder，用明确protocol recipe参数；不复制第二套完整模型引擎。新protocol的source-plan marker固定40，与decoder/assessment一致；保留legacy实际HTTP marker20、旧decoder40的历史语义。新提示覆盖所有直接支持任务，保留归属/程度/条件、已售和已开发两种集合，按单modality分句。新每任务cap应允许同一来源的否定/接触/未来意向分别表述，仍不超过现有40总条数、280字/条、配置输出token限额。
3. 新protocol不启用only_tasks/自动paid continuation；HTTP material发送集与重算的source-admitted集一致。实际发送过而未输出的任务必须报missing，不能冒充budget_deferred；若将来发送集真的裁剪，必须从冻结请求保留实际requested集合，不得由输出倒推。额度不足仍由既有AUTO budget拒绝，不增加许可/人审。
4. 公共SummaryResult DTO保持原2.0/3.0。新内部execution wrapper承载canonical summary与program-owned assessment，旧extractive execution/1保留。新prompt不得通过删wrapper降级为无评估的旧summary。parse_summary_job_result在有selected时按同一pure owner重算，并比较冻结source plan/admission、requested、最终claims和有限诊断。
5. 新raw bundle2.1/projected3.1带summary_assessment；旧2.0/3.0没有新增字段，精确回放保持。所有生成与验证路径共用一个protocol→bundle schema/producer resolver，包括narrative_generation的raw/projected、narrative_verify._bundle和_effect。新producer应为1.1.0，effect key使用实际bundle producer，不能继续全局1.0.0。
6. strict DTO只接受对应版本字段；新bundle中summary prompt、bundle schema、producer、assessment版本必须一致，不允许旧schema藏新prompt。assessment重算应绑定真正的证据/reading_context、source admission和final retained claims；有限历史validator算法按明确版本解释，录制的implementation recipe不被冒称为当前软件。validator包含normalizer、任务/准入、scoped view、claim role及canonical encoding的直接依赖。不要把SHA观察再变成人工许可。
7. quality projection之后才保留程序风险标记，不能让旧project_summary_claim_quality抹掉。详细diagnostics最多64项、总字节64KiB，另保留diagnostic_count/limited及全部风险claim IDs；被限幅不能显示成无风险。semantic_status和subfact_coverage_status都保持not_evaluated，possible诊断不能宣称通用NLI或完整保真。歧义claim/task映射显式ambiguous、不任择最后一项，也不只信claim_id前缀。

## 责任路径与顺序

- CWP pure recipe/assessment → scoped builder/decoder及runtime有限分发 →内部summary wrapper → strict bundle DTO/verify/generation/effect共用resolver → artifact projection/read/transport。上层只读逻辑引用，不读取物理目录或选择PDF后端。
- RF `company_wiki_narrative_contracts` 与对应context/consumer只扩展明确的新bundle版本并保留摘要质量观察；不能重新实现PDF、source admission或新造另一套语义审查。先锁定context wire能否兼容携带诊断；若必须新版本，明确枚举版本、字段集和旧fixture，不隐式接受任意多字段。升级后用现有定点安装器同步受影响运行时文件，配置和output保留。
- CWP生产默认选择在上述链路全部通过后最后变更。FF已存在的SourceRef复用能力和新SourceRef输入产品能力分开记录；M1真实registered IR成功不代表FF新增请求模式已完成。已存在原件不为证明调用FF而重复下载。

## 关键节点验收（不再细分人审）

**工程节点：** 协议身份/旧wire回放、新prompt与单modality/每任务限额、完整plan/真实requested/final retained、归属/否定程度/条件的中英局部正负对照、同scope多intent歧义、diagnostics限幅、raw/projected schema和producer/effect一致、篡改/删assessment拒错、RF保留质量观察。只跑受影响域及必要类型/lint；大节点独审稳定实际版本，修完再发布，不反复超时全量。

**真实节点：** 同一IR的8个已冻结输入检查点，当前配置一个有界新摘要，独审逐项比较原文/输出/结构化modality/归属，不把8任务有输出当8事实全保真。生产原件/config/哨兵不变；持久paid response后中断、activation、同run重启和跨run复用均0额外POST。资料置独立owned测试湖，结束精确清理恢复；不手写accepted数据库，不修改历史paid产物标签。

**采用节点：** RF通过正式来源/叙述接口读取本节点产物，参数/证据/公式实际依赖记录明确、保持币种单位期间及partial/needs_review局限；只拿到metadata不算采用。与完整公司循环/新holdout的审查分开记结果。全部验收后才宣称M3/M4完成。
