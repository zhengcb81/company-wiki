# 默认PDF几何需求规划：只读设计调查

状态：DESIGN_ONLY；2026-10-16；ROOT决策后实施。此报告不修改源码、配置或原件，不调用供应商，不新增外包卡。

## 已确认的结构事实

- `profiles/registry.py::_sections/resolve_reading_profile`保留配置的完整`section_rules`（层次/角色/优先级/aliases）；`section_priorities`是兼容flatten视图，不能替代完整规则。
- `pipeline.py::understand_units`目前先接收解析完成的units，再route→resolve profile→structure→bind_reading_plan。源parser的table发现/fine请求已经发生，后置profile无法追回前部误花的预算。
- `structure/sections.py::build_sections`已有TOC/furniture排除、层次栈、source边界、有限延续、角色/来源basis/confidence；不能在parser另抄一份业务正则和章节栈。
- `structure/table_purpose.py::qualify_table`已有真实表成员的经营/会计区分，明确允许财务附注里的经营表。该服务只能在已读真实表后确定用途，不能伪装成native发现前已经有表格。
- 默认真实反例仍见`probe-auto.json`：金禾136页请求、62页projected、74deferred，223/224无fine。显式请求成功不等于默认策略已完成。

## 1. 精确复用点与当前缺口

| 层/已有符号 | 复用职责 | 当前不能声称已有的能力 |
|---|---|---|
| `profiles/registry.py::resolve_reading_profile/_sections` | 对实际有界original probes复用原route，选择唯一family/lifecycle overlay，产出完整section_rules/profile_version/policy_components/context_requirements | parser目前没有接收title/kind/profile；不是给parser一个profile_id就完成有证据路由 |
| `strategy_binding.py::_match_rule/_PolicyPreparation` | 唯一heading_path、ASCII边界、Part/Item身份、冲突、明确父rule继承的匹配语义；优先级1较高、3较低 | 是私有函数；应由其owner提取窄的纯公共facade供两处调用，不让parser直接依赖私有函数或复制匹配算法 |
| `strategy_binding.py::bind_reading_plan` | 原body最终归属/child scope/真实section规则、同role不同Part不混用 | 当前对完整structure运行，不能为每页反复重跑全前缀；不能把route本身当section_rules来源 |
| `structure/layout.py::order_units/_toc_units/is_heading/heading_depth` | 原读取序、真实TOC leader、furniture、编号/DOM/明确heading证据 | `_toc_units`与`profiles/signals.py::_is_toc_unit`有不同用途/边界；后者认目录标题和双语目录，前者认单位级leader。不能只挑宽松者把整页正文删除；全局重复页眉也不可能只凭当前页最终确定 |
| `structure/sections.py::build_sections` | 原heading stack、source边界、parent、有限continuation、section basis/confidence、unknown | 它在完整ordered units上构建；不应在parser重新实现同类章节状态机。`_role_for_heading`是泛化fallback且顺序敏感，不能覆盖更具体的policy path证据 |
| `profiles/registry.py::configured_table_signal` | 单catalog经营词仅作候选线索；后续可改成返回命中facet/evidence ID供规划 | bool丢失scope/依据，现跨全部facets任意词OR；不是“当前页确有表/当前经营事实”的证明 |
| `narrative_evidence.py::_table_scan_signal` | legacy选择行为保留可重放；v0.9退出它与configured的双OR裁决 | QA、风险/计划和行业词命中都不证明需要native table，不能继续主导新默认fine |
| `structure/table_purpose.py::operating_header/qualify_table` | 已实际读表成员之后唯一经营用途确认，保留财务章节中经营指标，纯金额表/会计表区分 | `qualify_table`不能接一页全部文字冒充header/rows；pre-discovery最多使用明确标为provisional的字段线索，不能给未发现的表eligible |
| `automation/narrative_select.py::_parse_pdf/_select_pdf` | source_metadata真实title/kind/language在此可用，现子进程监督仍负责C调用硬中止 | `_select_pdf`现有“无spans+有deferred页→full_table_scan第二parse”会重建collector/deadline。新规划必须显式处理这条补全路径，不能静默重置资源后声称单parse |
| `narrative_pdf_layout.py::PdfLayoutCollector` | 同一TextPage的DICT/WORDS、实际capture/project/release与64/15s/结构额度 | 不应成为业务策略owner；执行顺序/未做原因要忠实，不从空的已释放pages反推missing |

### 现catalog不是可直接执行的几何规范

`section_rules`已有role、aliases、heading_path、priority、questions；`deprioritize`是`content/unless`自然语言说明。**不把这些中文句子临时regex化执行。** 还缺“读正文优先级”和“是否需要表发现/细格”之间的明确能力投影。例：`administrative_document`行政章节priority=1；如果机械把priority1变fine，会优先扫描签字声明。HK/SEC financial_notes中可有经营合同、RPO或销量表，不能把financial_notes变硬拒绝。

建议在**同一reading_catalog**追加少量类型化`geometry_intent`（按section/rule可覆盖），经原registry解析/版本摘要，禁止新YAML/新关键词注册表：

```text
geometry_intent = {
  discover: on_tabular_evidence | context_only | none | unknown,
  fine: on_candidate | explicit_only | unknown,
  demand_class: operating | project | mixed | context | administrative | unknown
}
```

它只是资源请求资格：`none`不删除正文，`operating`不等于已证实经营事实。保守默认unknown；与旧profile wire兼容的投影保持不变。typed字段默认与内容改动必须进入profile/component digest，不能只改解释文档。完整schema版本是否升/2由ROOT依现验证器决定，不能无检查悄悄插字段。

### catalog实际样本覆盖缺口

可转债family的fundraising rule同时声明aliases“募集资金运用”，但`heading_path`首层只有“募集资金投资项目/本次募集资金投资项目/本次发行募集资金投资项目简介”。真实金禾根标题是“第八章 本次募集资金运用”，并不满足该根路径；同页后续“募集资金投资项目的备案及环保批复情况”可命中别的规则，不能倒推根标题已绑定。不能靠fallback flatten把失败路径洗绿；应把实见章节变体在原family配置补正，保留风险章节同词、否定标题、不同Part同名的反例。名创`業務回顧及展望`已有准确path。

## 2. 真实原生导航调查：有限需求可以在深页到达前规划

新收据`native-navigation.json`：只调用当前PyMuPDF原件的`get_toc(simple=True)`与`get_page_labels()`，**0 TextPage、0完整parse、0复制、原件SHA/mtime不变**。

- 金禾283页：**481条native outline**。原生目的地有“第八章 本次募集资金运用”→物理223，“二、本次募集资金投资项目的可行性与必要性”→224；p91“发行人主要产品的基本情况”、p93“销售情况”、p94“前5名客户销售情况”等真实细层级。
- 名创246页：**21条native outline**。“業務回顧及展望”→物理11，下一同级“管理層討論與分析”→26，故p12在真实业务章节范围；不能据此断言p11–25每页均有经营表。
- 两份均没有page label rules。目的地来自PDF书签的物理地址，不从TOC印刷数字猜+1/-1偏移。目录文本本身不是body证据。
- 书签可能无效、重复、乱序、外链或与正文冲突。native outline只作导航计划，不能当业务事实、完整coverage或强行改变路由。保留来源SHA、outline index/level/destination及后续正文确认依据。
- `get_toc`一次原生调用会先返回其列表：结果后截断不是原生调用分配/墙钟硬限。原件字节/现子进程时间监督仍有效；对巨大outline只能记录navigation_resource_limit，不能宣称Python循环前预扣可抢占C层。

## 3. 推荐薄接口：一个策略owner，一个source执行port

建议新增纯`document_understanding/geometry_intent.py`作为ROOT装配facade，**不读文件、不导入source_catalog、不调模型、不保管TextPage**。内部调用原registry和structure/strategy服务。parser只提供实测PageMaterial和执行所选操作，不含业务词。

```text
GeometryIntentContext {
  source_id, source_sha256, scope_id,
  resolved_route?, resolved_profile?, actual_probe_refs,
  limits, version
}

NavigationHint {
  navigation_ref: {source_id, source_sha256, outline_index},
  level, title, physical_destination, status
}

PageMaterialView {
  source_ref, physical_page,
  borrowed blocks/text + original block/range refs,
  observed bbox/font/heading metadata,
  prior confirmed section refs, native_navigation_refs
}

PageIntent {
  page, scope_id, section_role, matched_section_rule_digest?,
  basis_refs, role_confidence, profile_version,
  tabular_evidence: observed_candidate | absent | unknown,
  discover_requested, fine_requested, priority,
  context_for, reason_code, provisional
}

GeometryRequestPlan {
  version, source_ref, profile_components,
  navigation_digest, scope_digest, planned_pages,
  request_digest, plan_complete, deferred_reason_counts
}
```

薄方法可为`plan_navigation(context, hints, work_budget)`、`observe_page(context, material, section_state, work_budget)`、`admit_request(plan, page_intent, execution_balance)`；是纯函数/调用内session，不是新workflow或任务库。`basis_refs`在尚未emit canonical unit前必须引用真实source+physical page+block/range或outline index，**不能捏造最终unit_id/locator**；canonical单位由现source emitter一次生成，后续才绑定精确unit refs。

预算边界明确：现source collector的1M几何work/15s与后置理解链2M WorkBudget目前不是同一实例。preflight必须通过source owner提供的窄charge协议消耗其现有余额（以及原全attempt监督），不能每页新建WorkBudget或用后置2M通过冒充来源成本有界。后置仍向其原同一2M实例收费；本设计不承诺已统一为一个物理账户。

### profile如何到达parser：不能假装现签名已有

现公开`parse_pdf/parse_pdf_bytes/_parse_pdf_document`不接title/kind/profile，而这些信息在`narrative_select::_parse_pdf(payload, data)`可用。ROOT有两个合理选择，建议选A：

- **A（推荐）**：给现PDF来源port增加一个可选不可变`reading_intent_context`，由现统一来源准备从metadata和**实际原文有界cover/heading probes**调用原route/profile构建；无context时source按同模块保守generic处理。旧调用不变；只对已选0.9生效，不把旧0.8重放变成新规划。不是新增回调，也不把模型/配置IO塞parser。
- B：source以当前读取材料在同一纯facade中做有界route/profile准备，再交给后置pipeline复用决策；依赖方向允许，但必须借用真实source范围，不能把书签/文件名当body信号。当前缺title/kind导致family未知时应如实generic。

两种都需要解决“cover探测”生命周期：若已有caller预读，则必须传递其同页材料并由原parser消费，不能再建TextPage；若尚未预读，则首个/当前页借用本次DICT产生真实probe。不能为了有context提前另parse一次全文。所有supplement/child scope依原route边界；不能把父文profile灌入陌生附件。

### 结构复用的落地方式

不得从parser直接调用私有`_role_for_heading/_match_rule`后另起状态机。由structure/strategy owner提取：

1. 原section stack中的heading advance/边界逻辑为调用内`SectionCursor`，原`build_sections`和流式preflight共用该实现；仍保留TOC/furniture/parent/source-gap/Part/Item/compound heading既有测试。
2. 原`_match_rule`+prepared material封装成`SectionPolicySession`，后置`bind_reading_plan`也使用同一服务。每profile预编译一次，按已观察的heading ancestry匹配；无法匹配就unknown，不重试flatten。
3. preflight只做“这个页面需不需要昂贵结构”的规划，不调用完整`understand_units`、project/QA/binder，也不每页重建全前缀structure。只保留有限祖先refs/短标题及当前两页材料；正文继续原units输出，不复制另存。
4. 流式时重复页眉与显示heading可能尚未最终确认，明确provisional。后置全局structure可修正判断，已花的成本不能假称撤销；final fact role仍属于最终structure/binding，不以PageIntent代替。

这是复用服务的小型抽取，有明确旧行为等价测试；不能一边保留旧stack、一边只给新stack起共享名字。

## 4. 默认调度：先有依据分配有限请求，再用当前真实材料确认

```text
现source intent/metadata + 同轮实际有界probes
        → 原route / resolved full profile
PDF native outline（导航，无TextPage）
        → 同策略matcher绑定候选章节 / 有限需求计划
物理顺序逐页：同一个TextPage → DICT/blocks
        → 共享SectionCursor + policy page intent
        → 当前cheap tabular evidence确认
        → 一个请求准入器同时决定find_tables与fine
        → 原find_tables/DU7/projector → 立即释放native材料
        → 后置原pipeline/binder/selector/摘要（身份覆盖同一计划）
```

### 有原生outline的推荐默认

- 用完整path/parent和typed geometry intent映射native section spans，按语义请求类/具体rule、已配置priority、source顺序做确定性有限轮转。先给不同高价值section最小机会，再分剩余，避免一个长business章吃完后面的募投章节；不能仅对全页候选排序前64。
- 规划的是**最多64个物理页操作名额**，同页不同候选合并，一页discover与fine共享名额；邻页/重试/失败读取都计入原资源，不另开账户。候选metadata可多于64，但遍历/排序必须在原work余额内预扣，bounded diagnostics不藏超限候选。
- 章节跨度不等于整章fine；先定位章节真实开始/子heading目的地及有据延续；当前页用DICT的行列/对齐与已观察字段只作候选确认，不需WORDS或find_tables才知道是否可能tabular。p223/224两个独立导航目的地、p93/94销量/客户、名创业务章节中p12的邻接材料均可获得机会，不写公司或页码常量。
- 选择名额前后对正文/书签不一致保留unknown；不要把错误书签变成拒绝显式历史页请求的权限门。已分配但无表的页标`candidate_no_table`，不能写抽取失败或无业务。
- 显式`table_pages`最高确定性，既有full/empty语义维持；explicit仍受原资源上限，不能抬64/15秒。
- 时间仍是实际执行耗时：仅把名额分给后章不足以保证时间留到后章。如果较早请求C调用很慢，后章可能deadline deferred；硬抢占仍由现worker负责。若默认目标要求“优先业务章必须先读”，就必须允许有界需求顺序读取，见下一节，不把逻辑优先级冒充执行顺序。

### 无有效outline / 混合 / 扫描件的推荐默认

- 当前两页共享cursor给明确TOC/释义/签字/纯会计且无经营字段证据的页面保留正文，跳过昂贵discover/fine；数值多不是纯财务判据。
- 风险、计划、行业机制可保留文本摘要和真实条件，但不能因事件词本身触发表查找。unknown混合页可请求小额探索；探索与高价值请求使用同一总上限，具体分配是执行策略版本的一部分，不是第二预算。
- 存在财务/行政外层role但内含明确经营列/本级经营heading时，经营例外可请求；p94产品销量、RPO/订单、客户留存、门店、项目建设进度不能被整章排除。最终还须原qualify_table逐表确认。
- 空页/扫描页标native_text_unavailable，不能因not blocks给所有空页排队find_tables；现OCR/needs_source路径仍负责，不在本改造引入新OCR解析器。
- 不能知道未来章节位置时，不声称全球最优或完整。报告`navigation_missing/role_unknown/request_deferred`；有限在线探索有失败概率，默认真实holdout必须验证这种能力限制。

## 5. 信息不足与单TextPage约束：明确可做与不可做

同时要求下面五件事，在无导航的任意文档上不可能保证：①固定64/15秒；②严格物理顺序；③每页native材料只读一次；④最多两页native缓存；⑤未来任意深页全局最优且必完整。

**此次推荐最小保证**：保留一次TextPage/page、最多两页native缓存和现预算；用原生导航/实际章节意图减少已证实噪音，预留不同业务section名额；未达到仍诚实deferred。金禾/名创有导航的默认真实回放可以检验收益，不能把它写成所有PDF保证。

如果ROOT要求更强“先处理最重要后章，再扫全文”，应另行明确选择一种取舍，不能偷偷做：

- 原导航指向的优先页先在**同一parser与同一预算**读取；其canonical文本产物作为原units暂存，后续物理序输出借用它，不再建TextPage，native fine即时project后释放。最多64个选页的**既有最终单位**可留存，不留TextPage/全页snapshot；不过当前emitter全局ordinal/QA状态依赖物理顺序，必须先用测试证明unit ID/locator/顺序未改变，否则不能采用。它是同parser调度重构，不是当前已经支持。
- 若保持旧emitter严格顺序，也可明确允许有界目标页补读并记录重复TextPage次数、原总deadline/work不重置；这会放宽“一次native读取”的要求，不能继续宣称满足。本报告不推荐在未确认用户约束前这样做。

只让low-priority前缀等待、不保留其native页、扫描结束再想取fine，必然要补读或全页缓存；不存在无成本第三种方案。

## 6. coverage、恢复与旧full-scan回退

在现`coverage.capture`加compact planning summary或其digest，不建新store。至少区分：`navigation_observed_count/limited`、`planned/discover_attempted/discovered/fine_requested/captured/projected`、`not_requested_by_intent`、`deferred_resource`、`role_unknown`、`outline_conflict`。列表有界，完整数量/hash来自实际集合；canonical_text_read与fine coverage分开，未请求fine不称未读原文，也不称业务无价值。

request identity包括source SHA、planner版本、实际采用的profile组件/rule digest、导航/章节范围、explicit模式、额度。actual coverage单独描述执行，绝不能把plan存在当capture完成。旧/1历史可查看，不满足新计划identity；恢复沿原artifact/lease/outbox，不重跑模型；费用/token不重置。

`_select_pdf`旧空span→full_table_scan隐式二次parse必须在本大节点解决：新0.9收到unknown/预算不足时返回partial/needs_source及缺口；若确需补充，转为原同attempt的有界补充计划并复用材料/累计预算。旧0.8行为重放兼容单列，不能改其历史产物后声称没变。后置发现无摘要不是“授权再无限扫一遍”的充分理由。

## 7. TDD与验收：仅原A/B/C大节点

### A：共享策略契约与旧语义（先写RED）

1. 完整path覆盖、同名不同Part、risk标题含募投、bare Item冲突、子附件scope、超深/循环边界、零budget提前退出；证明新facade与原binding对已确认heading一致。
2. administrative priority1不变成fine优先；profile unknown不变成hard reject；改实际采用geometry rule会改变计划digest，无关family变动不应误失效。
3. 真实短材料目录`主要产品/募集资金使用`、释义同词、否定募投/投产风险：canonical保留，finder/WORDS次数=0。不是只断言新布尔字段。
4. 经营列/销量/客户/门店/RPO在financial/admin混合范围仍可请求；独立会计金额不借旁边heading经营认证；最终qualify_table不替换。
5. TOC印刷页码≠物理页无映射时unknown；原生目的地越界/外链/正文冲突，不猜offset/不造body refs；正文与导航缺失分别列覆盖。

### B：source执行/资源与真实默认（集中一次）

1. 80页合成PDF含前部TOC/风险/会计、后部经营/项目，测试真正默认`table_pages=None`，不得由测试传深页表冒充默认。不同章节公平分配；显式/full/empty兼容；0页/0work/0fine/原deadline/取消/原生失败均诚实。
2. 直接统计frontend TextPage、DICT、WORDS、find_tables、最大live native材料与累计工作。每页一次frontend TextPage、max2；C库内部是否额外分配不作未测承诺。超过余额前不排序/全遍历；低优先页不执行finder。
3. 真实金禾与名创原件只读：默认规划→真实discover→DU7→binder；记录136→实际请求变化、223/224和名创经营表覆盖、产品销量阳性、未执行理由、全parse耗时及2M共享成本。绑定unknown仍partial。至少一个无outline holdout；若样本缺失写NOT_RUN，不仅凭两份有书签材料签通用PASS。
4. 原canonical文本/ID/locator/字序、旧native/layout/binder测试原样通过；新intent页筛选不允许改变最终值/期间/单位。若采用优先页预读方案，增加重排序/QA跨页/哈希重放的实行为测试。

### C：正式生产恢复闭包

现正式worker→公共read→RF/AUDIT；新request/actual coverage进入原依赖库存、首次按真实配置摘要、恢复0额外模型调用、费用延续、缺口不能洗complete。专用隔离测试根预先记录sentinel/初始目录清单，测试下载/派生清理后逐项复原；生产原件/manifest/config SHA不变。集中后正常commit/push/PWF，不增加逐页审批或人工签收。

## 8. 实施顺序与边界（ROOT决策后）

1. 冻结当前显式port/默认反例，先补A行为RED；**不动当前另一线26项真实测试**。
2. structure/strategy owner抽共享cursor/matcher facade +同catalog typed geometry规则及真实章节变体；旧binder/数字引擎不动。
3. ROOT统一来源准备给原PDFport传不可变context；source owner在当前同TextPage接规划/准入，同时控制finder与fine，保留现projection与release。
4. ROOT移除新默认隐式full-scan重置，接capture/request causal identity；跑B+C集中大节点。

建议独占文件边界：shared `geometry_intent.py`、`strategy_binding.py`、`structure/sections.py`/`layout.py`所需最小复用facade、`profiles/registry.py/reading_catalog.json`；source `narrative_evidence.py/narrative_pdf_layout.py`；ROOT `automation/narrative_select.py`、decision_inventory和现worker cache因果接线。具体只能在ROOT解冻/分配后修改；本报告**没有写这些源码**。本次scratch仅本报告与native-navigation小收据，0供应商/0配置写/0Git写。
