# 来源信息含量：小型共享 owner 设计（等待 ROOT 选择实施 slice）

状态：DESIGN_FROZEN_AWAITING_ROOT_ACCEPTANCE。只写本目录；无产品/测试/配置/PWF/Git修改，无原件/PDF/SDK/LLM/网络调用。承接 canonical SOURCE_INFORMATION_ROOT_PLAN，不混 CNIR QA closure、US工作上限、重复归并或SDK部署。

## 证据和共同契约缺口

完整内容预审位于 formal-content-preaudit/report 与 review-matrix。真实t11/t14的value_band已经是description，但仍被source_business_relation作为support并创建独立task。因此“description降权”已经存在，继续改planner权重不能关闭这条来源旁路；有价值的无数字主营描述也同样可能是description，不能整类禁止。

纯text-owner诊断见observations.json：26个中英期望＋3个保存scope文本共29条，**不是pytest RED或native回放**。实际t11/t14复现eligible=True、financial_exempt=True、operating_mechanism→support；t29更关键：prepared roles.operating=False，却因operating_current_state得到eligible/financial_exempt=True、meaningful_fact和support。其原文包含“管理层评估是否有足够财务资源持续经营”的附注语境，不是经营产能事实。source-owned financial predicate已有现金等价物，但`reading_financial_only`首先看到豁免即返回False，补现金/授信词无效。

代码责任链已核：

- assertion_roles._description_payload目前主要检查有字母/汉字及financial noun修饰；“完整功能语法”没有保留独立信息payload的证明。
- project_reading_business_fact按relation的stage/modality/attribution转换reason；末尾把“非unknown reason存在”变成financial_exempt。typed operating object缺失的current-state也可走这条路径。
- source_support_use与source_narrative_relevance都把eligible＋reason减unresolved直接当充分信息依据；后者又控制early offer。
- reading_material_value仅看reason集合，不能区分同属operating_mechanism的真实技术功能与泛目标，也不能识别被错升级的financial current state。
- 单一planner已消费support_use/value_band，保持support-first及成本/closure。它不读payload，这个职责不变。

## 同一个准备结果，三件事不要混为一谈

1. **完整性**：源上有真实主体/谓语/实际局部宾语或条件，refs定位合法不等于完成。保持既有typed head/NP binder和原语言/模态。
2. **对象类型**：经营对象/物理资源，还是财务存量/可用授信、会计规则背景。按实际governing NP和predicate-role，不按所在章节。credit facility不是manufacturing facility；贷款固定利息/抵押约束、资金限制导致具体产线延期可以提供独立信息。
3. **独立信息payload**：该局部关系是否给出具体业务范围、功能、机制、真实状态/动作/计划或限制。一个明确技术功能足够；不要求数字、新动作、新产品、多个特征或固定长度。产品/服务＋抽象好处、旨在满足需求/提升参与度，不因语法完整就独占摘要。

不新增文档分类体系。仅在现有prepared proof附加最小的**局部operating-object绑定＋independent_payload三态(True/False/None)**及实际witness范围；现有完整性/模态/actor字段照旧。False必须是已完整识别的泛目标或财务/规则背景，不能是“没识别到具体性”。None为未解析/不确定，不能伪称已证明套话。原文/index始终可读。

## 建议 ROOT 先选 A，再接 B；不要一次重写全语义层

### A：先关闭无typed对象的current-state财务豁免旁路

这是当前证据最小、最清楚的slice。复用operating_states._Event.bound_operating_object以及已准备predicate/object refs；不要从`operating_current_state`字符串反推“经营”。现有unit级complete_assertion布尔不足以处理混合句，若需透传，沿现有session缓存按predicate/局部clause保留绑定sidecar，借现有original-ref mapping投影，不加公开schema/新扫描。

最小owner：operating_states/relations.py（已有绑定sidecar，如现cache不足才补）、narrative_operating_relations.py（同owner准备/映射/缓存）、narrative_business_policy.py（当前state进入经营content及豁免须消费实际局部绑定），以及owned test。没有typed经营对象的金融/评估背景不得仅凭current reason获得豁免；现有_SOURCE_ACCOUNTING负责金融识别，不加新词。经营因果、贷款条款、负面/计划、经营资源/数量的已观测具体证据仍从各自现owner产生，不能因不含product head整类丢弃。

关键：不能用整scope“某句有operating=True”给另一金融句捐对象，也不能把某句金融背景抹掉整个scope真实业务。旧legacy0.8走既有路径；新执行缺typed proof不能默认True。A本身不宣称已修t11/t14。

### B：把现有功能/用途匹配的payload准备下来，供三个消费者共用

在assertion_roles原head/predicate/argument匹配中保留局部payload witness，不另扫整段判“套话”。已有主语、产品/服务compound、功能/客户/渠道、计划动作、限制和条件matcher提供具体payload；**具体功能与泛受益目标必须在同一关系owner区分**。沿已有generic component/vision/goal语法收敛到一处局部用途判断，不能给t11、数字化转型或参与度写整句黑名单，不能靠公司名/数字/形容词数量证明具体性。未知技术词不自动generic；不能为了减少tasks排除所有无数字描述。若现grammar不能区分，保None/未解析而不是伪造具体性或套话结论。

最小owner：assertion_roles.py＋narrative_operating_relations.py的已有准备缓存；narrative_business_policy/source_purpose按同份局部proof投影；narrative_support_use只消费结果，不读正文再分类。reading_material_value增可选prepared参数或消费同一cached assessment，current reading传实际proof，显式legacy调用保旧解释。narrative_reading只透传exact-view准备结果及早期offer/value字段；planner/summary compiler/source_cards/RF/FF不改。

不要另造大ontology/第三分类器。若B需新抽象目标语法，仅在原作用关系owner扩展有限结构，必须先用“support客户订单处理”对“support抽象业务好处”等同谓语对照证明不误杀；不枚举公司的宣传句或追逐全部潜在目标词。后续每个新业务功能不应新增公司或产品allowlist。

## 当前接口如何消费（不新增wire）

- fact.eligible/reasons可以继续作为候选召回/诊断观察；不能在任何current摘要路径单独兑换content-proof。stage标签不承担对象类型或信息含量。
- source purpose、financial_exempt、support_use和relevance共用同一局部prepared结果。独立具体经营payload可豁免包含的金融词；财务存量背景不能因为有“为营运提供资金”就豁免。无需把泛目标谎称成非经营purpose。
- True→既有support；已证明纯泛目标/financial-context→context_only；有经营迹象但proof None→unresolved，原始可读独立于生成。保持已有numeric ambiguity更严格约束，不用新具体性抹去单位/列/期间未知。
- early offer仅为有独立业务payload或有正向经营依据的未决材料服务；已证明context不独占112选材。未知普通prose仍保raw/index，不能当“已读无叙述”终态。_admitted不应新增reason字符串白名单来接受另一种unresolved；消费同一source-use/relevance契约。
- value_band由这份证据派生：真实持久主营/单一技术功能可以是meaningful，泛目标/finance background为description；None不伪造meaningful。不是description blanket ban，也不是只有新事件才meaningful。
- mixed exact-view只从该view的support clause取witness，context/title/其他task不能捐对象或细节。有具体业务与泛目标混合时保具体内容及原文/限定，不整scope否决；独立泛目标view仍context_only。原始spans、物理closure/成本不缩小。

## 冻结中性期望、真实RED边界与必要测试

cases.json冻结13组中英对照（26条）：泛产品/服务目标、平台参与度目标、现金/授信背景；与无数字单一功能、主营服务、路由机制、真实计划、负面认证、固定息抵押贷款、融资导致产线延期、物理设施分别对照；另有裸NP/word-only-stage负控。观测29记录中10条与期望不同：G1/G2四条＋actual三条为不当support；P4-zh/P8-en/P9-zh三条是**已有纯召回缺口**，不得用改期望或把它们叫套话来凑绿，亦不强塞进A小slice。实际与中性可能文本重复，不把这些记录数当独立pytest failure数量。

实施前转为可执行TDD，先冻结有效RED；至少：

- A用实际t29保存文本/最小中性持续经营评估句与financial-resource/physical-resource、具体资金约束成对；t1真实条款、t22风险、t23否定计划、t32/35/36/38业务条款保正控。
- B用同谓语support/支持的泛好处和实际订单处理、医疗消毒、网络接入服务成对；无数字/无新动作描述、真实future/negative照旧support。
- generic＋具体函数、financial context＋产线限制，交换句序；每个独立view、未知scope、标题/其他task不能捐witness。未识别payload保unresolved/raw，不能假context/假终态。
- 保旧NP/主体归属/问答/指代/财务数字质量、R&D资源、计划/条件和legacy重放控制，按实际owner影响选短包，不重跑600s全域。
- 同source owner重复fact/purpose/value/use/relevance不增加准备次数或work；prepared regex n/2n/4n按既有增长阈检查，不提高scan常数/额度掩盖重复。per-clause复用必须真缓存，不能每消费者重新分类。
- 现有decision_inventory已覆盖相关owner；核实际修改字节使business算法身份失效，旧冻结publication仍可读，不借旧身份假命中。无新registry/权限链/schema。

ROOT选择slice后一次必要TDD/短包＋集中独审；实际复验只重用已有HK five-gold/full38 scopes和已曝光开发基线，精度看新source disposition和具体内容，不要求任务数/旧38support/0unknown恒定，不改gold分母。仅在原始native scope接线确需确认时做一次有目的原生复验，不重读来填报告。正式供应商摘要/SDK/cache/RF仍另验。

本设计不承诺解决全部C3重复/训练/通用规则，不触CNIR closure或US预算问题。真正的未解析、财务背景和无独立信息分开记录；不为信息含量创建人工门禁或许可。
