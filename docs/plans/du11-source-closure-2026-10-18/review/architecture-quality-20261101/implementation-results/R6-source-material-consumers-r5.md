# R5 来源材料消费者链只读调查

状态：**只读消费者链调查完成，未实施/运行功能验收**。CWP候选 `tmp/architecture-r2` HEAD=`2b0787dc1c5352cd8566fc71fc585afe735ec75c`，对应失败CI41373840648；兄弟RF HEAD=`957c6283d3381d23c39515afd3a09147d8201c7b`。不改production/tests/Git/PWF，不运行原件、模型、全量测试。目标是区分来源材料可用、来源自述、独立事件及数值/投资接受，避免通过加门禁或广泛bool绕过掩盖同根问题。

调查范围：OperatingFact的原始文档明确“无semantic truth claims，计划/预测/否定保留原文”；当前support_use已有support/context_only/unresolved轴，并不天然表示事件完成。本次已追踪prepared用途/价值到native材料、LLM呈现及RF实际绑定入口，以下区分生产者抹除、排序降格、下游用途和仍待执行验证的边界。

## 结论

**应保留有信息量的来源范围、定性意图、定义/口径和币种限定，不要求它们先成为已完成事件或数值结果。** CWP的任务是表达“该来源写了什么、原文限定和用途是什么”，不是证明原文陈述在外部世界为真。`eligible`、`independent_payload`、`material_payload` 当前直接服务于阅读/材料价值；把它们改成“世界真值/已完成事件证明”会破坏既有合同，而当前下游并没有这种自动推导。

静态追踪中未发现下述消费者因为 `OperatingFact.eligible=True` 自动生成实际收入数值、完成事件或投资accepted。真正风险在**生产者将不同层次的信息共用payload布尔含义后，过早抹掉/降格材料**；另一风险是人或未来消费代码误读`meaningful_fact`/`opened_and_checked`等名字。应修准备owner的定义与投影，不在每个消费者添加`or source_scope`或取消真实support/context边界。

本结论是所查路径的代码事实，不是RF所有模型、摘要改写或公司经济结论的全面正确性证明。/4改写式LLM仍可产生语义错误，代码明确保留semantic_status=not_evaluated；/5原文卡降低改写风险，但也不证明原文真实。

## 一、字段的实际含义

| 字段/对象 | 实际产生与消费 | 不代表什么 |
| --- | --- | --- |
| `OperatingFact.eligible` | `n6_candidate_operating_facts.py:1-27`声明来源文本的经营材料召回评估；可含计划、否定、结构描述。`project_reading_business_fact`再保留具体source-state labels；admission/排序消费 | 外部世界真值、issuer身份已确证、事件完成、数值可直接填模型 |
| `AssertionRole.independent_payload` | `assertion_roles.py:772-815,823-863`：本clause是否有独立的具体内容/参数；True/False/None是局部角色观察。`bound_payload`可由已绑定的来源关系/资源/数量补足 | independent不等于独立外部第三方确认，payload不等于已发生事件 |
| `AssertionRole.material_payload` | `assertion_roles.py:858-859`：`proof.independent is True`且非descriptive-only或有observed material_scope；被`SourceAssertionRoles.descriptive_only`和material value消费 | 字段本身不是event stage；静态客户集合可以material=True而function_or_event=False |
| `source_scope` | assertion/disclosure owner观察的局部业务范围/未来意图等来源说明；当前`_SOURCE_SCOPE_RELATIONS`显式包括business_scope、portfolio、ownership、operating_plan、definition/segment/outlook等 | 不是storage canonical_scope身份校验，也不是T3结构note frame，更不能变成issuer/consolidation或机制/生产里程碑 |
| `reading_material_value` | `narrative_business_disclosures.py:546-552`返回meaningful_fact/description，供有限卡片优先级和预算分配使用 | meaningful_fact是现有wire名字，不是经投资审查accepted的事实 |
| `SourcePassageCapability` | `narrative_source_passage.py:42-51`的use/reason/role/relevant/financial_only/assessment_complete是同一source quote的资料用途、能力与未完成状态 | support不是“该观点为真”；unresolved也不等于未下载或禁止原文预览 |
| `reading_support_use` | summary task继承exact citation-view的support/context_only/unresolved，current schema4有strict bounded reason | 不能用整个doc的company_filing角色将context句直接升为support |

特别注意：`SourceAssertionRoles.independent_payload`过滤rule_purpose后，存在`self.clauses`非空但values为空而`all(empty)==True`的False分支（813-814）。因此不能把所有False都叫“已证实泛泛套话”；有些只是没有进入经营payload判定的rule类条款。是否需要改此实现应由owner结合旧合同判定，本审查不把该静态边界单独算成新功能缺陷。

## 二、实际caller链与下游边界

以下CWP路径均相对候选工区；RF路径相对兄弟RF根。26个源码SHA记录在同名JSON。

| 节点 | 代码位置/明确调用 | 实际责任与发现 |
| --- | --- | --- |
| 单次source准备 | `narrative_operating_relations.py:771-821` `SourceOperatingSession.fact -> prepare_reading_business_assessment`，缓存fact/financial/assertions/passage | 每个实际owner一次准备；后续getter没有另起分类器 |
| 统一准备入口 | `narrative_business_policy.py:1129-1210` | 同时得到source角色、statement scope、事实标签、财务轴和passage；这里是最小一致性修复点 |
| 引用级用途 | `narrative_reading.py:580-625` `scope_use` | 按closed support成员准备owner，调用source_support_use、source_narrative_relevance、reading_material_value，缓存五元结果；context不能捐谓词 |
| 阅读准入 | `narrative_reading.py:719-727 -> narrative_reading_admission._admitted` | 当前生产传入缓存support_use/offer_relevant/assessment_complete；既不只看eligible也不应另行扫文本。False仍影响bare glyph、heading等边界 |
| 稀缺选择 | `narrative_reading.py:731-758`、`narrative_budget.py:773-791` | meaningful_fact/description、support/unresolved改变value bucket和优先顺序；即便quote仍support，降为description也可导致有限名额下漏选 |
| 原生材料闭包 | `narrative_native_materials.py:24-25,359-385` | 实际调用默认classify=None；`diagnostic_fact.eligible`只在旧private诊断callback路径，不能说生产native compiler因为它再次过滤。结构/原始成员先于意义 |
| summary任务 | `summary_tasks.py:124-170` | 原样继承source group/view/role/use；support/context必须partition，非另推主体或数值 |
| source card可用 | `source_cards.py:66-106` | 已解析/表格可定位才available；source_card_generation_reason只在use=support（或历史未带该字段）时生成。context_only/unresolved原文仍可读，但不能伪装独立摘要支持 |
| 卡片分配 | `source_card_allocation.py:18-49` | 只消费已准备priority/value/score及位置，不能替上游重新判断哪段是事实 |
| /5原文卡 | `narrative_model_extractive.py:92-159` | 完整source quote成为卡，不把模型新prose写成事实；modality=uncertain、needs_review=True，模型仅advisory ranking，不能删除已准入卡 |
| /5模型呈现 | `narrative_rank_material.py:13-48`、extractive instruction | 只给已admitted任务原文片段、support/context indices和reading hints；模型不生成数字、正文、估值或结论 |
| /4摘要呈现 | `narrative_model_scoped.py:33-101,404-413,426-470` | 展示admitted任务；prompt要求保留主体、否定、modality、币种单位口径，明确reading hints不是真值。某旧prompt说不要用metric definitions凑数，但不等于程序删除所有有用定义 |
| /4解码 | `narrative_model_scoped.py:327-379` | 从合法local basis构建claim，modality来自模型；校验引用/形状和诊断。没有将eligible自动变actual；也没有外部真值验证，应诚实保留not_evaluated |
| RF实际采用 | RF `source_narrative_context.py:154-239` | read context一次，caller明确绑定已存在且used的parameter和真实formula_refs；没有从summary存在推参数值 |
| RF claim | RF `source_narrative_context.py:109-135` | 仅rationale_support，保留原文excerpt/来源SHA/locator；opened_and_checked说明读取核对来源，不是经济接受 |
| RF summary-use | RF `narrative_summary_usage.py:145-241` | caller选择summary_claim_id和research_reason；原support/context/父来源、modality、needs_review和formula关联随真实claim保存，不计算新金额 |
| RF持久证明 | RF `narrative_summary_provenance.py:61-98,184-218` | excerpt_scope=source_anchor_only，semantic_status/subfact_coverage_status必须None或not_evaluated；不是accepted投资结论 |

RF `narrative_citation_context.py:366-416`仍拒绝把source发布为context_only/unresolved的view当作rationale support；coverage本身仅诊断（1-12、264-283）。该拒绝保留正确责任，不能为了恢复旧召回就放宽RF，让任意raw span穿越support/context分区。

检查RF scripts未见直接读取CWP的material_payload/independent_payload/reading_value_band/reading_fact_purpose或`fact.eligible`；其入口为版本化wire，不跨层import CWP分类实现。本次不扩大到所有RF公式/其他provider或UI，不能据此保证未来所有消费者都不会误读名字。

## 三、R4为什么同时伤到旧有效scope、intent和basis

这是生产者层次收窄，不是已证明所有70失败全属一个原因。两spy TypeError由ROOT迁移；其余由source作者/独审逐个旧合同验证，下面只给共用可追踪路径。

### 1. 把source描述从“独立材料内容”排除成非fact_candidate

`narrative_business_policy.py:815-820,919-927`把business_scope、portfolio/ownership、qualitative operating_plan、metric-definition/change/scope、outlook/segment/future-investment放进_SOURCE_SCOPE_RELATIONS。它们不再进入payload_reasons；business_scope又进入_UNKNOWN_RELATION_REASONS，所以也不进scope_reasons。

`narrative_source_passage.py:136-156`对source_scope描述且没有typed_business/independent_payload=True的clause设置fact_candidate=False；235-239再按fact_candidate过滤members，262-269用空白抹掉classification text并清fact_roles。`prepare_reading_business_assessment`1163/1175-1180使用这个masked text/fact_roles做detector、purpose和后续投影，因此原有useful disclosure reasons可在调用真正的disclosure observer前就消失。

正确排除问句、模板、套话、未闭合片段是必要的，但“不是事件”不能成为抹除business scope/经营计划/指标定义的理由。

### 2. 有些并未完全拒读，却被降为description

`prepare_source_passage`420-422允许source_declared_scope成为support，所以有些quote仍能进入阅读；不能把所有直接`eligible=False`测试失败说成全文都不见。

但`reading_material_value(fact, source_roles=...)`一旦有roles，就**完全不看fact.reasons**，只看independent_payload=True且非descriptive_only。原source_scope从payload排除后，即使passage仍support，也可能降为description，进而在真实有限预算/卡片字节排序中被其他项挤走。原`test_real_source_selection_retains_distinct_business_information_in_twelve_spans`的CI失败与这种价值轴回退一致；本次没有重跑，不能冒称已唯一定位该case的全部中间结果。

### 3. “观察到的集合/说明”不等于“已完成事件”

`assertion_roles.py:576-600`已经计算closed member_identity/observed_scope/material_scope，但_DescriptionProof返回值仍是较窄的_argument_payload结果；当它为None时，858行material_payload又要求independent=True，已明确命名/闭合的来源集合也会失去材料意义。

旧`test_source_observed_business_scope.py`明确要求静态客户scope有material payload且function_or_event=False；`test_source_measurement_scope_and_enumeration.py`要求陌生闭合service members有有用材料，并反控抽象词、开放尾项、模板/问句。它们本来就没有宣称上市公司一定生产这些东西或句子已被外部证明为真。

### 4. 旧intent/definition/currency合同没有要求伪造里程碑或数字

- `test_qualitative_operating_intent.py:12-39`11例要求operating_plan/purpose operating，明确不要applied_operating_milestone；员工培训/抽象愿景/问句等负控保留。R4不能以缺数字或未知完成阶段否决这些具体计划。
- `test_reading_reporting_basis.py:36-53,57-95`要求source-defined metric basis、definition change和mechanical outlook recast可用，同时明确禁止operating_quantity/metric_change/revenue measure或guidance的错误升级。这是“如何读数”的信息，不是已报告增长。
- `test_reading_material_value.py`把具体业务scope、客户收入地域口径、合同转换分开；generic quality/成功愿景仍description。恢复scope材料不是把所有business_role都当机制。
- currency要区分：通用外币折算/套保会计政策不是本项目稀缺业务卡；“收入主要美元结算、人民币升值影响本公司收入”是具体业务暴露；“按固定汇率增长”是该测量的比较限定，不是新金额。`test_reading_reporting_rule_boundaries.py:17-75`已经同时锁住这些正反边界。70失败里currency对应unknown_error，没有完整本次逐clause运行，**具体首错仍OPEN**，不能只见有account词就定为会计套话。

## 四、建议最小改单个准备owner合同，不另建框架

建议R5以**现有`prepare_reading_business_assessment`为唯一资料用途准备owner**收口，而不是新增第二套classifier/permission/schema。实现由当前source作者统一负责；本审查不动代码。

1. **先固定含义**：OperatingFact在0.9 reading入口保留历史“资料有用性/召回标签”含义；eligible不升级为真值。independent_payload表示独立、具体的来源内容，不要求事件完成；material_payload表示有材料价值，function_or_event仍区分描述/事件语法。source_scope本身不能直接变成operating_mechanism、issuer、measurement或consolidation。
2. **保留source描述观察，不让event视图变总闸**：SourceStatementScope可以保留单独的事件投影视图，问句/模板等依旧不能捐谓词；但不得把fact_candidate=False的source_scope一并从所有reading labels/value/purpose中抹除。复用同一准备cache已有的_ReadingRelationObservation/原始source clauses，而不是重新跑两次词法/语法或按公司补白名单。
3. **从实际source-local proof给回材料意义**：闭合、具名业务成员/客户链、明确经营意图、公司自己的metric basis等由各自已有observer输出原有精确reason；不靠`source_role=company_filing`或“可读任意句子”取代具体关系。对closed membership，member identity/material_scope是资料内容的证明，不能要求未知名词先进入产品字典；计划仍携带不确定与未来语气。
4. **单个准备结果负责use/relevant/value一致性**：现ReadingBusinessAssessment已含fact/financial/source_roles/passage，应保证这些投影来自同一次原始clause评估且不矛盾。优先修原producer的material/payload语义，让现reading_material_value自然返回正确band；若确需显式value投影，只挂在这个已有prepared结果上并让scope_use消费一次，别让admission、material value、passage、compiler各自做bool补丁或另分类。保留当前枚举wire名字以免无意义跨仓升级。
5. **事件/数字仍归现有专门owner**：source_relations的原始refs、polarity/stage/attribution/modality与binding决定“来源声称何种状态”，不是OperatingFact.eligible。定义/计划/范围可被摘要，但不能因此新增operating_milestone、operating_quantity、收入conversion、actor归属；原文比较basis/币种单位必须留在完整scope/context中。source claim本身也不是world-truth。
6. **消费者保持薄**：材料准入/预算只消费prepared use/value/completeness，native compiler保留whole original support/context，LLM只按已配置协议呈现，RF只保存explicit rationale绑定。不要给RF或LLM补“trusted scope=true”、不新增人工签收，不把未知语言/工作预算失败伪装为完成；也不因一个scope未知整文拒读/禁止原文复用。
7. **保留0.8边界**：legacy detect_business_fact/replay不隐式opt-in新scope识别，不能为了修0.9而扩老机制。当前70中legacy相关失败仍要按原合同修，不能统一改expected适应新布尔含义。

这些调整的共同重点是修“已完成事件证明”和“有用原文信息”的错误等同，既不把所有描述丢弃，也不靠source_scope或role泛化成机制。

## 五、后续最小验收建议（本次没有运行）

- 复用既有70失败合同，由source作者先跑同根少量正反子集，再一次合并域；不要改掉旧“无milestone/无metric-change/function_or_event=False”反控来凑绿。
- 给单一ReadingBusinessAssessment做表驱动matrix：closed roster、prospective target roster、具体qualitative plan、generic aspiration、company metric definition、会计教科书定义、美元业务暴露、通用汇兑政策、已观察增长及完整比较basis。每项同时看fact labels/use/relevant/value/financial/completeness，避免只看eligible。
- 一份小型真实pipeline/compile检查：scope/plan/basis确实成为selected source card并进入material原文，精确保留主体/口径/币种；/5仍uncertain+needs_review，/4的model modality不由程序假设actual。缺proof/grammar/预算时状态诚实，原文仍可预览。
- 一个RF离线绑定检查足够：对含plan/definition的摘要显式summary_use，进入既有parameter rationale但parameter的value/unit/currency/period与formula输入不变，semantic_status仍not_evaluated；context-only不能借该入口伪造support。无必要不改RF实现或扩大跨仓测试。
- recipe依赖按真实owner代码自动失效，旧artifact/费用/失败历史不重签；不用提升额度重复整批，更不启动新公司循环证明这个接口修复。

## 边界、快照与STOP

同名JSON记录26个实际读取源码的SHA与close时绑定；这是逐文件只读快照，不是所有跨仓源码都在整个调查过程中冻结的声明。CodeGraph提供入口，但默认主索引没有候选callers，RF索引也未找到summary_use_entry；本轮不初始化或写索引，具体证据来自指定工区实际文件。

没有运行pytest、source selector、原件parser、收费或非收费模型；没有访问密钥/生产配置/DB，没有改src/tests/Git/index或主PWF。仅持久化本报告与JSON。T3-tests继续STOP，下一步由source作者/ROOT在当前同一大节点完成R5统一设计和修复、独审与CI；本作者 **STOP**。
