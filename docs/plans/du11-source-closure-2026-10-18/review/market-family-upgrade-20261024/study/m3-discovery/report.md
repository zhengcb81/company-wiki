# M3：经营指标定义、历史口径与指引依赖 — 只读调查

## 结论与适用边界

**存在真实漏材，也存在观察格式不足；两者不能用同一个 0 分解释。** MSFT 的定义、指标范围变化和机械重列指引在原 HTML 中可读，当前没有进入选材。HK 的一经营分部、下半年展望、重大投资否定、便捷汇率/编制基础也未完整出现；部分经营因果只留下半句。它们不是新下载或 LLM 问题。

本调查以 `m2-final-real-selection` 的已冻结观测为准，未重跑选择器。只在内存调用原 HTML parser 和现有纯 meaning port 定位原因。MSFT/HK 原件 SHA 与 M1 接受的绑定一致；所查 17 个 source/selection/normalization/model owner 的当前字节**全部等于该轮 producer 绑定**。详见 `observations.json`，不是用后来不同代码倒签旧输出。

M1 development gold 保持不变。没有新 oracle，没有改 evaluator，没有凭全局字符串在场代签 task-local 支持，也没有进行摘要/RF 验收。本文页码是 PDF 物理页码；HTML 使用现有 paragraph 与 DOM locator。

## 一、真实材料具体漏在哪里

### MSFT EX99.1：7/21 个源 unit 被选，无 selection withheld

原件 SHA：`47a0a4a1d6a335fffab571789aba597eca0637d2650f0f62371afa10e205b987`。文件路径见 `observations.json`，不复制原件。

|来源位置|原件的完整职责与限定|本轮实际输出|定位结论|
|---|---|---|---|
|p3、p6|FY27 从旧三段转换为两段；Azure/GitHub/developer/Security Copilot/Healthcare and Life Sciences 的迁移范围|已选。p6 同时包括 Healthcare and Life Sciences 移到 Industry solutions|不能说“分部信息全缺”；FY27 与将来语气保留。|
|p10 / `cwp-html-dom/1\|n=0.1.41`，1374 chars|Metric Changes：Azure 剔除项、M365 纳入项、seat growth 纳入 paid GitHub seats、广告口径改变；只列重大变化，完整定义另指 slide 13|未选。源 meaning port `eligible=False/purpose=unknown/financial_only=True`；真实 admission 抽样直接记录其 financial_only|不是 span cap：全源仅7个 admitted，全部 selected。|
|p12 / `...n=0.1.49`，2586 chars|FY27 Investor Metric Definitions；bookings = revenue growth + unearned revenue 变化 + contracted-not-billed 变化；商业 RPO 包含未来开票和确认；seat 是期末付费 M365/GitHub 用户|未选。纯 port 将整 unit 判 accounting_policy；真实非经营拒绝抽样与此相符|“定义”不是已实现的订单/收入；但不是可以丢弃的普通财务总额。|
|p17，1537 chars|As Reported / As Restated FY26 指标，并明确 `GAAP % / CC %`；LinkedIn 拆分去向|已选，整个 unit 在场|已有重述比较和 GAAP/CC 表头不能再记 missing。它不替代 p10/p12 的完整定义。|
|p19 / `...n=0.1.77`，1847 chars|FY27 Q1；相对 July 29, 2026 的 **mechanical adjustments only**；旧 total $89.85–$90.95 billion 与 Adjusted/Total Company/**No change to outlook** 联合|未选。纯 port 无经营意义并判 financial_only；该 unit 的独立 admission reason 未在有限 trace 样本中保存|不能把报告重列说成新的总收入上调；若不输出精确区间，可按需 SourceRef/API，但“机械调整而非经济变化”的语义仍有价值。|
|p20 / `...n=0.1.81`，2208 chars|旧 Azure-and-other 约45% CC 与新 Azure 44%–45% CC；FX 下拉不足1 point；旧新业务范围不同；M365 17%/18% 与 prior-year in-period recognition 限定|未选。当前纯 port 也 financial_only|把两个范围直接比成业务减速是错误推论。必须同时带新定义、期次、旧新标签、CC/FX方向。|
|p14–16|历史财务全表、重列前后精确金额|未选|属于 correctness_if_emitted，不要求为分数切全表；如实际采用，必须读对应原表/合适 API 并记录口径。|

本轮七个 reading group 均只有各自一个 support，没有跨组 context。MSFT trace 不截断这七个 selected 映射，因此上述“p6在场、p10/12/19/20不在场”可以准确判断；不能把 p6 的存在当作未选 outlook 的 task 内完整支持。

### HK 中报：96 selected / 55 groups，已达到 span cap

原件 SHA：`4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36`。

|物理页|定向实读内容|本轮选材与缺口|
|---|---|---|
|9、13|AI 客户与行业云扩张推升收入，**部分被主动缩减 CDN 抵销**；公有云增长来自 AI 服务，行业云增长来自 IT 需求和复制行业方案|p13/4 只留到“並部分被我們主動縮減向”，CDN 对象和抵销收尾未选；p13/9 只留行业云金额到旧值前半句，7.6%及后面的驱动缺失。p9 的相近复述不能拿来代签 p13 的本地闭包；完整 CDN 限定全局也未出现。|
|13|毛利额增加，但毛利率 16.7%→15.2%；AI 服务器及客户前期投入导致率下降|只选 p13/34 的“少主要是由於…”尾句，比例与“毛利率下降”主语未同片出现；不是“完整原因都丢了”，也不是完整因果通过。|
|11|“展望下半年”持续研发/AI、小米金山生态云需求|本轮未选完整该段。半年报父期间是2025H1，不能把“下半年”解释为新的年份或已实现。|
|15|截至2025-06-30 无重大投资；重大投资含占总资产5%或以上定义；无未来重大投资及资本资产计划|完整两项否定未选。不得从此推出“没有普通服务器购置/没有AI投入”。|
|50|主要经营决策者按合并业绩看集团，**一经营分部**；无另列地域分部|未选。公有云/行业云服务收入分类在 p9被选，不等于两个可报告经营分部。|
|5、12、45、67|2025H1/2024H1；除股数/每股外千元；美元只是便捷换算，7.1636且不保证实际可兑；主报表US GAAP，另有IFRS对账|未见完整 basis/context。被选非GAAP调整短语含“US GAAP”不等于编制基础；银行外币风险也不等于便捷换算定义。若输出数字，需绑定这些真实限定。|
|66|6月1日签一年不可取消 IDC 协议，6月30日剩余采购承诺；全节单位说明与正文“元”需联合|未选。采购责任不是销售 backlog，也不是已经履约收入；不得只抓金额或把日期落到错误父期间。|

HK 现 trace 有 `budget_full` 252 项，**这是选材 span 资源，不是费用/审批**。307 admitted 中只有96 selected；没有逐目标完整 trace，不能把每个 HK 漏项都武断归为同一 admission 原因。中性纯 port 已能独立复现“一经营分部”和“无未来重大投资计划”不被识别，其余需在同一集中回放中观察完整 candidate→closure→selection 链。

## 二、0 分的测量问题要分开修

现 `observer._source_evidence` 只映射相同 locator 和完整 raw_text，返回原 parser unit 的 `scope_id=metadata.selection_group_id`，不是本轮 canonical span 的选择关系。四份观测 scope_id 全 None；无 context_evidence，未封存完整 canonical spans。

- `checkers._support_set_status` 要求**一个 row**包含一项 exact_quote。多原 fragment 即便构成同一完整源 quote，也不会自动合并；这是保守测量边界，不能随便改成整篇拼接。
- `require_same_scope=True` 没 scope 会返回 NOT_EVALUATED。吉比特条件性问题两锚都在 paragraph1；04:37 speaker 在p13、完整更新意向/未落地/可能变化在p16，仍因 scope 未观测而 NOT_EVALUATED。**这些不能作为 M2 产品退步的证据**。另有09:24/09:41/09:42等真实未选材料仍必须保留为缺口。
- 珀莱雅 p3/23 同一选材行里有 -84.16、回款减少和推广费增加；其 M1 长锚还要求“项目名称/变动比例/主要原因”和报告期标题。不能声称原因不存在，也不能仅凭原因在场就认定百分比表头已发送。
- HK 长金标跨物理行，本轮选材又确有只留半句；不能把全部失败归咎 observer。每项应记录“单行完整/原片部分/全局缺失/局部scope不可判”，不是另算一个更好看的召回率。
- HK selected trace 只抽样16/96，55组 citation ID 不能完整反连原 fragment。既有 gzip 不足以复原全部 model tasks；不能补造 scope_id 来过金标。

**最小测量改进：** 下次同一生产回放在现 research receipt 中保留 canonical `EvidenceSpan.to_dict()`、完整 reading_context 和实际 compiler task binding；使用 source/order/locator/parser/原 span metadata 证明已有 scope，再由现 DU-BENCH observer/evaluator 接口表达。复合 quote只能在明确同 source、正确次序、允许的同 task/support closure中匹配；共享上下文可单独表达到既有 context_evidence，禁止把整篇 selected_text 当证明，禁止凭公司标题填 period。旧产物不重签。

## 三、共用根因和现有所有者

|已确认机制|现有 owner / 接口|最小改造责任|
|---|---|---|
|`_reading_clauses` 对超过1200 chars 的完整 clause直接舍弃；此 HTML 多页 slide 以一个白色1pt `<p><font>`文本公开，p10/p12/p19/p20没有真实 `<table>`/`<br>`结构|`narrative_business_policy._reading_clauses`；1200来自 `n6_candidate_completion.BUSINESS_CHARACTER_WINDOW`；HTML parser 保留 DOM owner 原文/locator|不能只提高1200或按固定字数切。语义 owner 在已读原 unit 中做有界、计费的源声明/定义标签观察，保留原 range/全 unit。无真实行列就不伪造表格。无需为这两份材料改原 parser字节/旧版本。|
|有价值的定义同时含 revenue allocated/RPO，被解释成普通会计政策；纯指标名、范围变化、无数字的 unchanged guidance缺少独立意义通道|`narrative_source_purpose.source_purpose`/`_clause_purpose`；`narrative_business_policy._purpose_fact`；纯 `narrative_business_disclosures.disclosure_relations`|由**一个**纯 source-disclosure owner观察定义/定义变更/报告口径与机械重列关系，purpose和fact投影复用它；禁止两处复制识别词。定义是可读业务基础，不是已实现数量/里程碑。普通审计/会计余额继续不是业务卡片。|
|未来值识别绑定 future cue+revenue+amount；same-period old/new标签、无新金额的 no-change 没有语义关系|`narrative_revenue_guidance.revenue_guidance`/`revenue_guidance_premise`；`narrative_predicate_state.observe_metric_predicate`|沿现 predicate/time owner扩展无变化/重列表述；不要另造 forecast detector。旧新金额仅按原词保留，不在CWP算经济增速。|
|产品先行词闭包不是指标定义/旧新指引闭包；现 local qualification只认产品限制/计划或显式 guidance premise，跨一段的语义补路还要求PDF page int|`SourceOperatingSession.local_qualification_dependencies`、`reference`；`OperatingRelationSession.reference_closure`；`narrative_antecedent`|复用 source session一次索引/原 ref验证/同账户、现有祖先与原生顺序。指标名/期间/报告版本的明确关系由 source-disclosure owner提供；不能把“these products”词典直接套到指标，不让HTML page=None被硬变成PDF页。|
|上下文预算/发送已有统一通道，不缺第二个规划器|`narrative_reading._candidates` → `required_context_unit_ids`/`citation_support_views`；`selection_bridge.build_context_graph/dependency_closure`；`narrative_budget`；`build_summary_task_plan`/`source_cards`|所有必要口径/否定/期间随原 graph 到真正task；事实必需的否定应在 support，不是只有 context。上下文不晋升为经营事实、不借兄弟卡材料、预算照计，未知/多义或超包仅该卡明确defer。|

这些不是权限门禁。无需新增许可、身份验证、canary、router、持久任务库或公司/产品词典，也不提高现16M work、96 spans/48K chars、8 originals/4原block/2048 chars依赖包上限。一个整HTML unit已经超过2048时，不能谎称把它和其他大unit组合后仍在有界依赖内；若精确充分源范围尚无可回放表示，就保留/按需源读取并诚实标未闭合，而不是裁掉条件求绿。

## 四、层次与最小中性 RED

1. **存储/规范化层**：同一原件SHA、DOM/页段/表格与原始speaker；不判断指标经济含义，不给FX、FY、单位换算，不将影像或白字 text 伪造成行列。
2. **共享 source meaning层**：在有限已读范围识别“该公司/该份报告定义的指标”“范围从A移到B”“只机械重列/无变化”；显式区分 definition/version/change/actual/outlook/unknown，保持原 refs和否定。
3. **source session与现结构闭包**：连接 metric→definition version→period、parent→child、old→adjusted以及必要条件。只连接源文本证明的唯一关系；两个同名版本、不同公司、不同期次、竞争前提都不能按最近邻选一个。
4. **策略配置**：presentation/sec_exhibit、HK interim等已有 family可提高上述关系的阅读优先级；配置不是事实识别器，不按文件名把全章当业务。
5. **selection/budget/model-view**：只消费类型化关系与现图；按完整包收费，保持原文，实际 task-visible检查。RF 才负责取API数字、口径对齐及建模，采用记录必须说明实际读了哪个源。

`test_neutral_red.py` 是现纯 port 的最小可运行探针：六项无公司名的经营基础（bookings/RPO定义、指标范围改变、机械不变指引、一经营分部、未来重大投资否定）**6 RED**；通用教科书定义、纯现金余额、审计断言与既有前瞻收入 **4 PASS**。收据 `neutral-red.xml`。这不是新gold/oracle，也未代签 pipeline/期间依赖。

实施时在现 unit/integration测试再补以下一组边界，不新增每小步审查：

- 相同中性指标跨两版本：新定义不得套旧已报数；旧指引日期不变，Adjusted/No change不能当上调，CC与FX point不能变成reported增长。
- 同父两个业务：A增长驱动不得捐给B；一经营分部与两个服务收入分类同时存在，不能混为两段；FY/Q/H1父期与子段“下半年/期末”共同可见。
- 分开的匿名speaker/来源/文档、两个竞争年份或指标，关系保持未知；无来源的同名定义/审计RPO金额不可豁免。
- 真实父标题、单位、否定/限定被拿掉或包超限时，现单卡defer诊断；不扩大上下文、不降金标、不加人工审批。

## 五、一次集中真实验收，不走小节点签收

在 M3/M4 共用实现和纯反例完成后做**一次**集中节点：

1. 冻结最终producer/策略/observer/compiler、M1 gold与两原件SHA；同一现 work/token/storage账户，不复制raw。先集中相关unit/integration，再用MSFT、HK和现annual14作为development回归，不称fresh holdout。
2. 同一次真实source replay输出 canonical spans、完整 candidate/withheld摘要、reading groups、实际 compiled tasks/source cards与各方SHA。MSFT不得只增加名字/列表；需逐项核bookings三组成、commercial RPO未来开票确认、paid期末seat、Azure完整剔除、新旧FY27Q1/机械/CC/FX。p17现有重述/CC支持不回退。
3. HK核AI/CDN正负两面、兄弟服务归因、2025H1→下半年、一经营分部、重大投资阈值与未来否定、IDC合同日/到期/剩余及单位；精确三表数据可不全切。输出任何金额/率时，必须在实际同task或被明确采用的SourceRef/API记录里证明对应basis，不从相邻数字猜。
4. 用现 evaluator 如实呈现分数，同时独立agent逐原件→span→task检查上述语义；scope未测/超包/原件歧义按原状态留存。不能仅因为分数为0宣称内容为0，也不能因为词在全局出现宣布task通过。
5. 大节点发现的问题全修后再统一验证；正常发布/缓存来源组件纳入现registry。随后才沿母计划跑配置中的正式摘要、收费恢复、缓存与RF采用；本研究不代签这些。最后另取未用于调规则的公司/版式holdout，保持“开发回归”和“新样本泛化”两种证据分开。

## 文件与限制

- `observations.json`：真实输入、源码owner与producer SHA、精确unit/DOM定位、有限纯port观察、scope测量缺口。
- `test_neutral_red.py` / `neutral-red.xml`：6 RED + 4 PASS，故意留在研究目录，不能混入全绿声明。
- `report.json`：可机读交接与后续验收接口。
- `findings.md`：本调查工作记录。

HK这里只做定向文字读取，不声称表格视觉/几何验收；MSFT 1pt文本不具有可靠表格列语义。未下载、未调用外部模型、未复制原件，未改产品、共享PWF、旧gold、Git索引或提交。两个样本的费用/下载资格不在本次范围。
