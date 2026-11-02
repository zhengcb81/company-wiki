# R6/R5 来源合同复核：材料可用不等于世界事实核实

结论：**CONTRACT_MISMATCH_CONFIRMED_REDESIGN_REQUIRED**。R4 将“source scope 没有事件型证明”普遍投影成 `OperatingFact.eligible=False`、`description`，改变了原有来源阅读合同。完整 CI 的 70 个失败不只是新案例没加够；继续围着失败句补词会保留这个错层。需要先统一同层语义，再实现和验收。

本轮只读核查候选 `2b0787dc1c5352cd8566fc71fc585afe735ec75c`、CI `41373840648` 的原记录/29 个失败函数组、原测试及消费链；没有运行测试、原件或模型，没有改源码/旧 oracle/Git/PWF。上一轮 `R6-independent-ci-r4` 的 32 个限定场景记录保持原样，不能当成全域通过；其中新设的“scope-only 一律 no fact/description”“未知成员列表一律无材料信息”预期不能反压原产品合同。它们所用的 fact 概念解释过窄，需要本轮明确纠正。

## 一、回答三个字段的实际职责

`n6_candidate_operating_facts.py` 开头明确写 **no semantic truth claims**，预测、计划和否定须保留来源措辞。`narrative_business_disclosures.py` 则明确说明只标注未改来源的用途，不判断其 truth、issuer attribution 或 completion。因此：

| 字段/对象 | 应负责的来源任务 | 不承担的任务 |
|---|---|---|
| `OperatingFact.eligible` | 当前来源文字是否包含可召回/选材的经营信息；保留既有 reading-only 用途标签 | 验证现实世界真伪、实际发生、发行人归属、并表、预测成立 |
| `SourceAssertionRoles.independent_payload` | 当前闭合来源范围内，是否有独立于套话/上下文借词的资料内容；True=具备，False=明确泛泛/无独立内容，None=未定 | True 不代表 positive 事件、已完成、正面经营判断；None 也不是 False |
| `source_scope` | 来源披露的范围/目录/用途/关系类型；可以与具体信息、计划、定义并存 | 不是统一降级开关，不蕴含 `eligible=False`，也不蕴含材料只能为 description |
| `reading_material_value` | 在可读材料中区分具体、自足的信息与宽泛背景，供有限预算排序 | 不判事实真伪，也不能仅因 scope 非事件型便降低所有目录/口径的优先级 |
| `source_support_use` / relevance | 这份精确引用是否可作资料支持、未决原话或仅上下文；不允许独立句/受益者捐证明 | `support` 不是事实核实或完成认证；`unresolved` 也不必一律不相关 |
| 原 relation bindings / modality / polarity / attribution | 保留来源中具体主体、动作/状态、对象、否定、条件、计划和限定的绑定 | 也不验证世界真伪；只能禁止把来源的计划改成实际、第三方改成发行人等投影幻觉 |
| 原 metric/单位/期间 owner | 判断来源是否披露数值或定义、数值归属和量纲；定义不能生成观测值 | 不由 scope/material/eligible 推出增长数值、当前数量、会计口径一致或收入预测 |
| `financial_exempt` | 在普通财务过滤中保留确有经营用途的来源范围 | 不是财务信息可信认证、全篇豁免或上游研究结论 |
| `assessment_complete` | 本轮来源能力/工作是否实际完成；缺资源/预算/过长保 partial/deferred | 不是公司信息完整、结论可信或“无业务变化” |

所有这些仍属于 AGENTS 定义的上游来源职责。StockWiki/RF 负责研究采用和分析判断；本次不应为了“更严格”在上游新增现实事实核实门槛。

## 二、原 positive/negative 已明确要求什么

| 原合同域和证据 | 必须保留的材料能力 | 必须避免的升级/借词 |
|---|---|---|
| `test_source_measurement_scope_and_enumeration::test_closed_named_service_scope_has_material_payload_without_a_type_dictionary` | `Our services cover miralon, tressiq and zovren.` 闭合、带关系的命名范围即便不在产品字典，也是独立材料；True/material/support | 抽象 value/success、未闭合列表、模板/问句不能借成员名放行 |
| `test_source_observed_business_scope` | 已销售目录、实际客户组成等可为 meaningful material，无须增长/数量变化/制造事件 | “目标客户”“未来主要客户”、泛产品服务、财务项目与填表例子不等于已披露的现有范围 |
| `test_reading_named_portfolio_drivers` / `test_reading_portfolio_disclosure` | 明确品牌名组合、股东关系、来源描述的第三方范围可以 eligible；无需反复“本公司” | 不变成发行人生产、控制/并表；裸名字、假设、术语例句、否定的“现有组合”不能冒成实际组合 |
| `test_qualitative_operating_intent` | 降低买量依赖、更新产品、稳住留存等具体行动可 eligible/operating_plan，哪怕时间未定、带不确定性、没有数值 | 不生成 milestone/current/completed；员工培训、费用记录、泛“越来越好”、跨句借产品、问句不得变计划 |
| `test_turn_plan_qualification` | 同 turn 的计划及“尚未确定/可能改变”必须一起进入原文卡和模型请求，角色 unknown 不妨碍资料使用 | 不能删限定、借另一说话人限定、或把输出 modality 标 actual |
| `test_reading_reporting_basis` | 本公司指标定义、口径变更、机械重述、单一分部/未来投资限制都可 eligible；定义/范围本身有价值 | 定义里的 growth 不等观测增长，未量化定义不等 RPO 余额；教材、审计程序与一般会计政策不冒充经营披露 |
| `test_operating_argument_axes` | 明确“manufacture KZ-4”等未知对象保持 unresolved/relevant 和原话；不用先认识产品后缀 | engine binding 可仍 False；不改成已知产品、正面发行人事件；财务/抽象/疑问/未闭合参数不能按陌生对象放行 |
| `test_reading_material_value` | 可读泛益处和具体信息分优先级；有限 12 spans 要保范围/地理口径/合同转化/机制等独特内容 | description 不抢占 scarce material；eligible 与 value 明确独立，不能当成同一 bool |
| 原 R3 独立五反例 | “supports remarkable ambitions / promising possibilities / unfamiliar technical endeavours”“aim to pursue luminous horizons”“plans to support remarkable ambitions”没有正向资料内容时仍 None/unresolved、不凭句法获得经营相关或强 proof | 不能恢复 default-specific；也不能把这个 weak-function/goal 反例扩大成“所有未知命名目录、定性计划都无材料信息” |

这里的“原合同”来自候选中并未被 R4 修改的既有测试，不是本轮为了让旧 CI 绿而新改 oracle。指标定义和定性计划的 source eligibility 与事件资格明显不同，足以否定“eligible = 世界经营事实已核实”的解释。

## 三、消费链说明为何不是单个字段小改

当前 `narrative_reading.py` 让同一 session 一次准备 `fact + source_roles + passage`，然后分别计算 use、relevance、value。`narrative_reading_admission._admitted` 接受相关的 support/unresolved，而非只检查 fact bool；所以制造未知对象能保资料而无绑定事件，正是原设计。

`narrative_budget.py` 直接消费 `reading_support_use` 和 `value_band` 排序，不读取原文重新猜。scope 一律降为 description，即便最终未被 admission 完全丢掉，也会输掉有限 slots。`source_cards.py` 又只允许 `support` 卡进入正式生成，把 unresolved 显式排除，因此 source use 错误还会继续变成“有原文，但模型没收到”。这是 70 中 turn plan、有限 12 spans、口径/组合资料一起失败的共同通道。

`narrative_model_extractive.py` 要求完整原文支持范围保留，未知角色和 actual/planned 混合不能改写；旧 turn-plan 测试对最终 draft 的 modality 也有断言。恢复资料 eligibility 不应改变这些数值/主体/限定的独立规则。反之，在来源准入时提前把完整计划或定义清空，并不是这些规则的合理替代。

## 四、对 70 个失败的界定

公开 CI 记录可复核为 **29 个函数组、70 个 case、13 个测试文件**。Unit 步骤约 283 秒，正常结束为断言/错误失败；不据此推断超时或平台是主因。分组和 case 前缀保存在同名 JSON。

其中 2 个是 ROOT 已接手的 WorkBudget 参数 spy 签名迁移；其余不能统称“都因 scope 太严”：除了命名范围/计划/指标口径的 false negatives，还包含原 `test_nonbusiness_results_and_nonassertions_do_not_gain_fact_support` 的一个 negative 失败。当前公开记录只给该函数组 x1，未提供完整可定位栈；不能编造具体是哪条参数及其根因。既有 financial/template/问句反控必须一起保留，禁止一刀切放开或把 70 全改 expected。

上一轮集中独审恰好验证了新局部假设而未覆盖这份原始职责矩阵。这是审查模型的缺口，不只是少跑了几个案例；完整 CI 阻止了错误概念直接并入主线。历史限定收据保留，但全域仍 OPEN。

## 五、最小一体化实现建议

1. **先固定合同语义，不扩审批**。在同层已有 prepared assessment 文档/测试中明确以上定义；保留现有公共字段、版本化 export、预算、source SHA 和 partial wire，不建第二合同系统/人工签收。`OperatingFact` 名称虽易误读，可先保兼容、修 docstring，不急于跨仓改名。
2. **原关系 owner 返回一次绑定的来源信息**。已有 disclosure/composition/intent/metric-basis owner 应返回具体资料用途、限定和材料级别；unknown/abstract 继续三态，不让消费者按 reason 名字集合自行重判。explicit typed roster 的语义来自“某类来源范围 + 命名成员 + 闭合关系”，不来自认识这些成员；具体计划来自同 clause 的 action/target，不来自已有 completed proof。
3. **撤掉 scope 的统一事实否决**。`source_scope=True` 不能统一使 `fact_candidate=False`；可把这个内部字段明确为“来源资料投影是否可用”，真正的 event/current/numeric 资格仍由原 binding owner。哪些 scope 是具体信息、哪些是 description，归来源内容 owner，而非一律将 scope 列入非 payload 集合。
4. **一份准备、多种消费**。同一结果投影兼容 `eligible/reasons/purpose`、`independent_payload`、material band、use/relevance；compat 和生产入口必须一致并复用缓存。不让修复版 callback 支持了 scope，而后面的 bool/reason 分支再次抹掉它。
5. **保五弱目标与所有旧边界，不列营销/公司词表**。一般语法只证明陈述结构；weak-function/goal 无资料内容的不能靠“不是已知抽象词”变正证。但 explicit membership/plan/definition 等不同关系有自己的 source 信息判据，不能都套用通用 weak function 的 NP 语义 gate。closed roster 不能再仅靠“数量≥2”成为业务事件，也不能因名字未知永久降级；它证明的只是来源声明了这些成员。
6. **预算和能力失败仍一个 owner**。保持 R4 的实际字符预扣/memo、同一 WorkBudget 和缺资源/超界 partial，不把失败当无业务。不要通过提额度或重复扫描掩盖合同恢复。ROOT 的两个 spy 只迁移参数传递，不削弱预扣/缓存断言。

## 六、下一个大节点如何验收

不增加小节点门禁。一个集中节点同时看：旧 70 所属 positive/negative、原五未知弱目标、任意新命名成员的完整/不完整变形、源范围/计划/指标定义的不同用途，以及同一候选的完整 CI。测试原 oracle 保留，确有错误的新 R2/R3/R4 预期在独立 erratum 中逐项解释，不能默改旧来源合同。

至少包含一个整链案例：合成材料同时有命名范围、无时间表的计划＋本 turn 限定、指标定义＋独立真实数值、weak aspiration、一般财务段。检查来源 owner、有限选材、原文卡、模型请求和 extractive modality 的一致性：具体资料进来，套话/财务不抢位，定义不造值，计划不变实际，限定和第三方归属不丢。用新成员名/未知产品代号防止仅修原公司的文本。完成这一个大节点并获得精确候选 CI 绿后，再接原真实 H1/摘要/cache/RF C 任务。

本轮是只读设计审查，**不签实现/全 CI/真实资料验收**。报告完成 STOP，ROOT 和同层实现作者据此统一修复。
