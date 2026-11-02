# R6 R5 — 来源材料合同与70例回归根因矩阵

状态：**IMPLEMENTATION_FROZEN_FOR_ROOT_REVIEW**（2026-11-02）。设计基线`2b0787dc`，CI`41373840648`。下方设计与原70例RED留存；实现、最后定点恢复和未完成验收见文末。R4及其独审历史保留，不回写成通过；本报告不是完整CI/H1通过收据。

## 已复现的事实

CI实际29失败组、70例、13个失败文件。用这13个完整文件加7个已有正反控制文件，共20文件在正常宿主复现：**70F/978P/0E，20.97秒（1048项）**，与CI70完全一致，不是Linux差异或测试超时。首次我禁用插件但漏显式pytest_timeout，collection 1E，未执行测试；已独立保留命令错误，再正确启用插件复现，不能把该E当产品缺陷。

ROOT另负责2个预算spy，只迁移kwargs并断言同账户；它们是协议调用的测试仪器适配，旧语义断言不改。本线剩余68例均须产品根修。原70旧期待均保留。

## 根本误释

`n6_candidate_operating_facts.py`首段写明“no semantic truth claims”，计划、预测和否定保留source wording。`OperatingFact.eligible`是来源材料准入/召回，不是世界事实核实。`independent_payload`是来源断言提供自足具体信息，包含闭合具名经营范围、当前/否定范围、定性计划、指标口径；不以增长、事件或产品后缀为必要条件。

R4错误地把source_scope等同“不能eligible/只能description”，又把unknown member没有行业类型当资料不自足，删除了真实材料。其新测试把错误定义压到实现上，不能反过来替换旧资料合同。另一方面，泛operating_mechanism仅因为roles.operating而产生仍然错误：generic weak function/goal未知目标不能凭POS/default-specific升业务相关。

## 70例归类及共因

| 类 | 例数 | 原合同 / 必要修复 |
|---|---:|---|
| A observed / named / material scope | 30 | 闭合具名品牌/股东/客户/服务成员与实际销售/开发范围是资料信息，可meaningful_fact；恢复原scope/material观察，不要求行业词典或event，不将scope类型全局降格 |
| B bounded intent / reporting basis | 26 | 原局部plan→action→business object、定义/口径/机械重述均有自足资料；保限定、计划不确定性和同turn约束，不把定义label的growth变成actual change |
| C typed operation / unknown argument | 8 | 原engine已识别制造谓词与闭合argument，unknown entity type不等无业务。unresolved+relevant保原话；qualified binding仍False、不得推issuer事件 |
| D background / nonbusiness / rounding | 4 | 已知generic benefit可eligible但description；纯财务因果不得从“因为…”子句重生业务；rounding原展示背景不能抹掉同scope另一自足业务 |
| E spy instrumentation | 2 | ROOT迁移work_budget透传并验证同对象；不改产品语义/不删断言 |

完整29组对应表：

| 类 | 测试组 | 例数 |
|---|---|---:|
| A | `tests/unit/document_understanding_root/test_operating_relation_production.py::test_independent_description_survives_empty_relation_result` | 1 |
| A | `tests/unit/document_understanding_root/test_operating_relation_production.py::test_non_event_description_needs_no_offset_names_or_context_view` | 1 |
| B | `tests/unit/document_understanding_root/test_qualitative_operating_intent.py::test_specific_qualitative_operating_intent_is_useful_source_material` | 11 |
| B | `tests/unit/document_understanding_root/test_turn_plan_qualification.py::test_chinese_plan_retains_uncertainty_without_promoting_unknown_speaker` | 2 |
| B | `tests/unit/document_understanding_root/test_turn_plan_qualification.py::test_same_turn_plan_limitation_is_model_material_and_card_support` | 2 |
| D | `tests/unit/document_understanding_selection/test_reading_material_value.py::test_readable_generic_benefits_are_background_not_scarce_fact_material` | 2 |
| A | `tests/unit/document_understanding_selection/test_reading_material_value.py::test_real_source_selection_retains_distinct_business_information_in_twelve_spans` | 1 |
| A | `tests/unit/document_understanding_selection/test_reading_named_portfolio_drivers.py::test_actual_named_shareholder_relationship_is_source_scope_not_consolidation` | 1 |
| A | `tests/unit/document_understanding_selection/test_reading_named_portfolio_drivers.py::test_issuer_owned_named_portfolio_is_concrete_business_structure` | 4 |
| A | `tests/unit/document_understanding_selection/test_reading_named_portfolio_drivers.py::test_legacy_detector_remains_unextended_for_named_relationships` | 1 |
| A | `tests/unit/document_understanding_selection/test_reading_portfolio_disclosure.py::test_observed_concrete_portfolio_does_not_need_repeated_issuer_pronoun` | 9 |
| A | `tests/unit/document_understanding_selection/test_reading_portfolio_disclosure.py::test_source_disclosed_foreign_actor_is_preserved_without_issuer_or_consolidation_inference` | 1 |
| B | `tests/unit/document_understanding_selection/test_reading_reporting_basis.py::test_company_metric_definitions_are_readable_without_becoming_actual_metrics` | 2 |
| B | `tests/unit/document_understanding_selection/test_reading_reporting_basis.py::test_growth_in_a_metric_definition_label_is_not_an_observed_change` | 2 |
| B | `tests/unit/document_understanding_selection/test_reading_reporting_basis.py::test_mechanical_outlook_recast_is_retained_without_inventing_growth` | 1 |
| B | `tests/unit/document_understanding_selection/test_reading_reporting_basis.py::test_metric_formula_with_coordinated_metric_noun_is_not_a_new_observed_fact` | 2 |
| B | `tests/unit/document_understanding_selection/test_reading_reporting_basis.py::test_multi_metric_definition_is_not_misclassified_as_reported_growth` | 1 |
| B | `tests/unit/document_understanding_selection/test_reading_reporting_basis.py::test_reporting_scope_and_future_investment_limits_are_preserved` | 1 |
| B | `tests/unit/document_understanding_selection/test_reading_reporting_basis.py::test_updated_reporting_definition_survives_a_long_flat_native_paragraph` | 1 |
| B | `tests/unit/document_understanding_selection/test_reading_reporting_rule_boundaries.py::test_actual_customer_business_and_currency_exposure_are_preserved` | 1 |
| E | `tests/unit/document_understanding_selection/test_source_support_use.py::test_direct_admission_projects_use_and_relevance_from_one_preparation` | 1 |
| E | `tests/unit/document_understanding_selection/test_source_support_use.py::test_source_session_shares_one_role_assessment_without_repeated_scans` | 1 |
| C | `tests/unit/du11_production/test_operating_argument_axes.py::test_explicit_manufacturing_argument_does_not_need_a_known_product_suffix` | 8 |
| A | `tests/unit/du11_production/test_source_description_relations.py::test_closed_source_enumeration_and_impact_are_language_independent` | 2 |
| A | `tests/unit/du11_production/test_source_description_relations.py::test_compatibility_event_policy_does_not_implicitly_opt_in_source_rosters` | 2 |
| A | `tests/unit/du11_production/test_source_measurement_scope_and_enumeration.py::test_closed_named_service_scope_has_material_payload_without_a_type_dictionary` | 5 |
| D | `tests/unit/du11_production/test_source_measurement_scope_and_enumeration.py::test_nonbusiness_results_and_nonassertions_do_not_gain_fact_support` | 1 |
| D | `tests/unit/du11_production/test_source_measurement_scope_and_enumeration.py::test_real_business_proof_is_not_erased_by_rounding_vocabulary` | 1 |
| A | `tests/unit/du11_production/test_source_observed_business_scope.py::test_closed_observed_scope_is_material_without_requiring_growth` | 2 |

## 统一观察结果字段及责任（复用现有对象，不造第二分类器）

| 维度 | 既有字段/owner | 正确含义及消费者 |
|---|---|---|
| 来源材料候选 | OperatingFact.eligible | 来源可用性/资料召回；可包含background，不是已核实结论 |
| 来源关系种类 | SourceAssertionRoles.source_scope / 原reading relation kinds | 范围/计划/口径/功能等类型，不自动决定强弱或排除 |
| 信息自足性 | independent_payload（True/False/None） | True=有自足资料；False=已完整观察为泛目标/背景；None=未分类/不闭合/参数未知。不是world truth |
| 摘要材料价值 | material_payload / material_scope / descriptive_only → reading_material_value | 自足具名范围、口径、具体计划可meaningful_fact；several editions、泛benefit可description，不与eligible绑死 |
| 业务可读相关性 | typed scoped relation、bound_operating、原数字角色 | 已识别制造predicate+未知argument可unresolved+relevant；纯weak generic target None不相关。不能用roles.operating单一bool代替 |
| 引用使用 | SourcePassageCapability.use/relevant | support、自足资料可引用；unresolved仍可能相关可读；context不是槽位材料。cards只生成support，这直接影响计划和口径能否进入正式摘要 |
| 世界事件/主体/数值资格 | 原engine.relation_bindings、actor/modality/period、原metric owner | 唯一可生成issuer/event/number投影的owner。eligible、source_scope、词表、POS不捐这些绑定 |
| 能力完成度 | assessment_complete / WorkBudget / source_processing_complete | 缺资源、超长、超限走原deferred/unassessed；不是语义None/False，更不是人工许可 |

现有消费链已由独审核对：reading614/617分别读passage.relevant与material value，budget785/790不重读原文；cards对unresolved不生成；RF仅rationale_support并保留uncertain/needs_review，不会把source eligible升级为world truth。因而应修源资料过度降格，不在cards/RF新增补偿门禁。

## 必要实施变化（同一owner组合）

1. 明确OperatingFact/新内部字段docstring，名称和解释都用source material/information，不再用scope-only不得factEligible的世界事实假设。保public class/API，不再造双分类器或兼容许可。
2. 原source assertion owner恢复闭合具名成员关系的independent/material_scope：明确offering/customer主体、局部声明谓词、闭合成员名、可定位原文是证据；不问成员属于哪个行业或known suffix。抽象/未闭合/模板/问句和跨句借主体仍负控。
3. 原reading relation owner产出统一material观察：局部定性intent、reporting basis、具名portfolio/ownership本身是自足来源资料，不能因kind=superscope而屏蔽。种类与材料强度分轴；财务豁免不作证明集合。现有canonical clause memo和同WorkBudget继续共用。
4. `prepare_source_statement_scope`只对真正non-assertion/无效附件/财务专属作用域作必要屏蔽；source_scope不是fact_candidate=False。goal/direct/background binding仍由同prepared matrix/complement owner完成，原五weak未知反例保留。不回default-specific。
5. known generic background的eligible/description单独保留；不借此把generic mechanism作为material强证。未知None弱function/goal仍unknown。原制造argument role的bound_operating/unknown_argument恢复可读相关性，但不提升qualified relation binding。
6. compat detect与production Session消费同一prepared源资料观察，不分别对scope先删、后重读产生两套语义。若保legacy0.8事件入口，明确只其历史policy不opt-in来源roster；0.9资料入口必须与生产解释一致。
7. 财务因果回归根在whole statement与子句的相关性作用域：完整财务句已判无业务时，孤立“因为财务表现良好”不能被POS作为business matrix重生。用同prepared scope purpose表达，不给该中文句加词补丁；rounding只治理展示背景，独立material relation不丢。
8. ROOT指定的R4自增错误oracle显式erratum：scope-only改测来源信息强度/原文限定、无新增milestone/issuer/actual number；未知双成员的资料自足性按声明合同，不拿听起来像营销的词当行业黑名单。旧70断言不改。仍守原五unknown弱function/goal和预算/资源边界。

## TDD与验收顺序

先用本地70已有RED作为真实合同框架，补少量跨类型组合反控（资料eligible不升级state/数字，未知制造仍None/relevant，scope material与weak目标区分）。分owner实现后只跑新变化或失败小组；最后只对20file整体再跑一次。通过后交ROOT独审与完整现有CI。原16M/112/模型资源/预算配置不改，无收费、原件或生产库操作，不复制大量文档。

本设计没有宣称70已修复，也没有宣称整个PWF完成。原R4三组绿只证明其当时局部定义，不能替代本次原合同和跨域复现。


## R5 实现冻结与真实验收记录（2026-11-02）

源码只在`tmp/architecture-r2`修改，主工区src、原文、生产数据库、模型资源、Git/index未动。冻版清单为同目录`R6-r5-freeze-manifest.json`，包含9个本轮源码与3个自增测试文件；清单SHA为`d45fc6875e411b2e2911e78e838b84a47af98fdf27c35c50438e5bc03b863650`。ROOT的两项budget spy由ROOT拥有，未在本线改写。T3测试仍排除。

实现沿既有prepared owner组合：

- 共用`source_nominal_members`识别闭合成员声明，roles与disclosure标签复用；未知成员名无需产品后缀/行业字典。成员分隔包括中英文一般并列，不新增公司/行业名单。
- 原reading relation owner对自足来源计划、口径、范围产出一致information payload；类型不再一律降格。`operating_mechanism`仍要求正向prepared payload，不凭roles.operating/POS制造业务相关性。五个weak function/goal None反例保持未知且不相关。
- `.eligible`恢复来源召回；generic benefit可背景候选，但不能占自足材料资格。scope material不再等同world truth。旧事件、数字、主体绑定未放宽；资料范围可meaningful仍无新增milestone/current-state/actual-number。
- whole financial statement已无业务proof时，将其子句keys放同prepared scope，不许孤立“because/因为”经POS重生业务；独立业务causal/measurement仍保留。
- 生产resource purpose回调复用同prepared clause、同WorkBudget和局部memo；窄子句确需重准备时显式按原19n预扣并传入原账户。无新用户门、无总预算上调；原scope target8n+1与grammar32n+1边界不变。
- 最后资源测试揭示text compat被生产资源扩展。用同一`ReadingBusinessAssessment`显式区分`text_fact`（prepared来源文本兼容投影）与`fact`（生产resource/relation投影）。`detect_reading_business_fact`取text_fact；production保持fact。不按资源reason删结果、不建第二分类器；0.8 opt-out仍不扩展roster。

| 顺序 | 真实结果 | 范围 / 留证 |
|---|---|---|
| 首次命令 | collection 1E，未执行 | 漏启pytest_timeout；`tmp/r6-r5-contract-red.*`，非产品失败 |
| 原合同完整20file RED | 70F / 978P，20.97s | `tmp/r6-r5-contract-observed.*`，与原CI70一致 |
| 共同实现后原失败组 | 5F / 105P，14.29s | `tmp/r6-r5-groups-first.*` |
| 原5项恢复与weak/finance反控 | 27P，6.70s | `tmp/r6-r5-five-recovery.*` |
| 唯一完整20file复验 | 1044P / 4F，31.23s | `tmp/r6-r5-contract-final.*`；原70旧期待全绿。4F在控制文件：同账户1、R4错位oracle2、财务cause1 |
| 四项修复定点复验 | 17P，5.19s | `tmp/r6-r5-four-recovery.*`；无再跑1048 |
| resource + prepared-context收尾 | 98P / 1F，8.18s | `tmp/r6-r5-resource-final.*`；遗留text compat意外带入production resource，保失败历史 |
| compat同根修复及必要正负控 | 16P，5.54s | `tmp/r6-r5-compat-final.*`；旧legacy资源不扩展、production实际资源、roster opt-out、五weak目标 |
| 静态检查 | Ruff通过；mypy9源通过 | 最后text_fact修改后单独再查policy Ruff/mypy通过 |

上述结果不能合成为“最后1048全绿”：最后改动后未重跑1048/整仓/完整CI。ROOT后续应独审冻结代码、正常commit现有检查、现有完整CI，最终H1仍须原16M/112限额验收。未跑真实公司/原件/模型/收费流程。

### R4 自增oracle显式纠正

旧70期待未修改。仅本线自增`test_source_argument_semantics.py`、`test_source_preparation_axes.py`、`test_source_semantic_axes.py`纠正：

1. source_scope一律`not fact.eligible`/description的期待过强；改验来源可用性、自足强度、原句保留，以及无新增event/actual-number。真正只有description的范围仍可description，不全局升material。
2. bounded定性plan / reporting definition不是actual事件但本身为自足来源资料；不再要求数字或已达成。保modality、same-turn限定、issuer不推断。
3. 明确closed catalogue两个陌生成员不因无行业类型而变None；保留成员/原文并允许material。列表语义不证明成员真实或公司已投产，不为听似营销的名称造黑名单。单个weak function/goal未知NP五反例仍None/unresolved/no relevance。
4. 已观察generic benefit可背景eligible但无业务支持/相关性、不占meaningful材料。原自增“eligible即世界事实”的两个控制改验不support、不relevant、无event/actual-number；财务整句仍不能凭此重生。

### 身份、效率与剩余边界

实际`business_algorithm_hashes`在PDF和非PDF入口均包含全部9个变更源码（非PDF96模块、PDF123模块），证据`tmp/r6-r5-recipe-presence.json`。仅算法模块/grammar固定资源身份改变缓存；未手动扩为全仓hash，未改wire schema或预算配置。

同clause roles/typed relations/purpose结果复用，false观察也memo；resource narrower scope需要真实预扣。17P包含真实生产入口同WorkBudget反控，98P包含resource模态/否定/财务控制。以上只证明有界工程行为，不能声称真实H1预算或性能已验收。完整语义覆盖与真实摘要/RF采用仍归ROOT后续大节点。现在本线源码冻结并STOP，不追加设计/新范围。
