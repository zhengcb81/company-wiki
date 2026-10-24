# W08 共享预算下一根因设计（只读）

## 结论与责任边界

**下一步应先修来源层给预算的“材料价值与覆盖意图”，复用已有 reading_plan/3，而非再造 planner、整体抬业务权重、扩大额度或继续删除几类模板。** 现有机制把“可保留/可解释”与“应占稀缺正式材料”混成了一个 eligible 布尔值，又把业务范围、集团订单、客户地域等不同问题压入 core_business。预算层不应通过读取 raw payload、公司名、页码或金标文本重新解释这些问题。

这是有证据支持的下一轮假设，**尚未证明修改后14目标改善**。本任务只读源码/冻结记录，未执行产品、作者脚本、测试、湖读取、模型、下载；仅写本目录 analysis.md/json。未改生产、原gold、母PWF或W13–W15。

## 1. 当前证据（事实，不由聚合数倒推单目标）

证据均相对本目录上级：`README.md`、`content-review/report.md/json`、`trace.json`、`selection.json`。选材SHA与独审报告绑定，7 pass / 5 partial / 2 missing；不构成正式摘要、cache或RF通过。

| 原始目标 | 真实source→budget字段 | 具体延期证据 | 能得出的结论 |
|---|---|---|---|
| A01完整四业务范围 | p11/par13，127字符；admitted=true；purpose=unknown；reason=operating_description_unknown；priority1、meaningful_fact、topics=[core_business] | budget_full，used96/requested2/closure3 | 有原文、有admission、有预算延期；scope未被表达为独立覆盖问题，并非未解析 |
| A03客户地区收入+A04集团订单 | p11/par22，215字符；purpose=operating_metric；reasons含business_revenue_measure/current_state；priority2、meaningful_fact、topics=[core_business,business_revenue_measure] | budget_full，96/2/3 | 同段同时承载客户地域与集团订单，budget没有看到这两种独立用途 |
| A01 Chemistry完整服务范围 | p119/par4，168字符；purpose=unknown；operating_description_unknown、core_business、priority2、meaningful_fact | budget_full，96/1/3 | 通用静态产品/业务范围识别或投影丢失具体用途，不应因未完成态而一律降为未知描述 |
| A04 RPO本期余额/2026确认计划 | p184/par14，109字符；purpose=unknown；operating_state_unknown、core_business、priority2、meaningful_fact | budget_full，96/2/3 | 实际合同stock和时间转换与普通core_business混同；目前字符串模式只收未来/next等，绝对年份等表达可能未覆盖，需中性TDD证明 |
| A03客户母公司所在地定义 | p16包含汇总+注1；admission fact.eligible=false、purpose=unknown | 当前不是单纯预算失利 | 仅修排序不能补此定义；需要source-owned measure口径/附注依赖，或SourceRef按需读取 |

本轮全package是1526 candidates，trace.candidate_count=470只属最后callback；39 target budget rows不是完整offer序列。不能据此说全量其他候选被丢、也不能复原第几次选择导致哪个visit。目标具体行可以证明上述budget_full，不能证明所有比较项的当时rank。

96已选 = 55 meaningful_fact + 41 context-only（由真实selection_reasons=['reading_context']计数）；41上下文不是可直接删掉的垃圾。topics计数为core_business22、capacity_projects11、operating_metric_change10、currency_risk10、business_revenue_measure7、business_revenue_recognition7、new_business6等（一个span可多topic，不能相加当55）。A01被22个core_business访问共享竞争，A03/A04又被七个revenue值共享竞争；它们没有自己的客户地域/合同存量覆盖语义。

## 2. 共享根因与源码证据

### R1：admission eligibility错误充当预算material value

`narrative_reading.py`的 `_candidates` 在source session已评估fact后，直接 `meaningful = fact.eligible or package.kind == operating_table`，用它生成meaningful_fact。eligible本来回答材料可否保留、是否有源语义；它不能保证已披露当前业务数据、结构范围或具体约束的强度。当前选中的公司宗旨/提升客户效率、子公司控制制度、终止经营定义片段、反复一般确认机制因此和具体scope/订单同处第一价值层。它们仍可留检索/背景，不需要一律丢弃或禁止读取。

### R2：source projection把可解释关系压成宽topic或unknown

`narrative_business_policy.py::project_reading_business_fact`把多种source关系聚成core_business，再附operating_state_unknown/description_unknown；`_segment_reporting_relation`有较严分部语法，普通“公司业务可以分为”可未形成reporting_scope；source_purpose的contract stock值语法要求stock后紧邻数字谓词，带币种/换行或非连续“履约义务对应的收入”形态会漏；`_CONTRACT_CONVERSION`+`_FORWARD_PERIOD`要求特定未来词，对显式会计年度窗口未知。此处均是待以中性正反例验证的具体解释；当前trace仅直接证明最终字段粗化，未记录每个内部正则分支。

### R3：字段丢失是真实，但不能简单把purpose/reasons原样当rank

`_candidates` metadata保留fact_purpose/fact_reasons；`narrative_finalize.py::_budget_item`只传priority/topics/required/context/value_band等，未传两字段。即便直接传purpose，A01/RPO仍是unknown，不能根治。预算也不该维护reason-name优先名单。最小做法是在source层一次把真实关系转成已有value_band和有判据的topics，再走既有接口。原purpose/reasons留解释收据即可，无需把预算变成第二语义解析器。

### R4：现有budget的硬限额/边际closure本身未见本轮错误证据

`narrative_budget.py::_reading_plan`已计算原ID闭包、共享依赖一次成本、cost动态递减、topic平均visit、value层、scope priority、软重复及有界work。3-member目标最终只需1或2增量，恰与已有共享上下文相符。当前证据不能称为共享parent重复收费bug，不能以除去header或把兄弟union为atomic来挤出位置。

### R5：保守软重复不等于模板语义去重

`narrative_semantic_coverage.py`要求protected_sentences和stage_signals完全相等再85%双向token重叠；包含subject的普通公司宗旨句也被保护，轻微改写模板不会被惩罚。该保守性保护数字/主体/否定，不能放松成数字bag或“都谈产能”就合并。先把泛描述分层；仅在同层再用既有软重复，避免新造LLM相似度判断。

## 3. 最小统一改法（推荐实现，不是已实现）

1. **source owner一次确定材料价值，不增加第三套planner。** 在现有source-session assessment/project阶段增加明确的可选 `value_band` 观察值，仍只有已有meaningful_fact/description二值；默认None供明确旧selector兼容。生产事实必须由该owner设定。`eligible`保持原admission语义； `_candidates`消费source观察值，而非简单用eligible冒充meaningful。上层不再重复正则判断。不要将unknown目的、没有数字、没有完成态直接判低：完整静态业务范围/计费机制同样可为meaningful。
2. **利用现有fact.topics/reading_topics，不再引入第二coverage字段。** 在同一source关系owner给出有限、公司无关的关系类型：business_scope（公司/父业务组成和服务边界）、customer_geography（客户地域与归属口径）、contract_stock、contract_conversion（存量向具体期间收入兑现），已有operating_quantity/causal/billing等继续使用。只有关系predicate+object及来源主体/口径足够时加；不是匹配“美国/订单/收入”就加。source中一个真实单元可同时携带stock+geography，但不凭金额多少加topic。不展开每个国家/每个产品为新topic，不允许标签泛滥人为获得novelty。
3. **分类以关系，不以章节黑名单。** 一般发展愿景/例行治理控制、未具体关联当前经营状态的会计定义作为description；实际受限投产、已经发生的客户交付、具体售卖/订阅机制、收入地域定义保持meaningful。具体风险仍保留条件/非已实现属性；真正客户经营约束不能被“治理”或“风险”章节误删。
4. **预算保持纯元数据消费。** `_budget_item`继续透传既有字段，当前平均topic访问和真实边际闭包不改；先以source改法证明收益。如果完整真实重放仍无改善，再收集有界接受offer证据（每次锚点ID/新topic/旧visit/全closure与delta/rank前缀/选择原因），设计最小排序更改。禁止现在就换rank次序或加神奇权重。诊断采样要有完整/截断标记，不靠39 targets假装全过程。
5. **口径/父子/日期仍属结构依赖，不是多topic能替代。** 地区注释只绑定对应地区measure；Chemistry父范围只进其子业务局部task；产能日期只与有来源证明的同项目容量join。保留8单元/4block/2048 envelope，缺证据继续partial/deferred。精确数额需要时SourceRef/API按需取；实际未读不能盖PASS。
6. **版本及缓存。** 把新source值判据留现有decision_inventory业务依赖集合，变动必须使decision缓存失效；不加许可文件。旧legacy/semantic/reading replay policy版本显式保留旧结果，当前production阅读version按已有机制变更。无需新task库、费用账或中间全文副本。

## 4. TDD包（先RED，再最小实现；正反例不来自gold的数字/公司/page）

| 层次/测试 | 中性正例与期望 | 负例/不应得到的结果 |
|---|---|---|
| source价值与scope | 未知A股仪器商“本公司业务分为检测仪器、试剂及维护服务”；未知美股软件商“Our company operates through two businesses: workflow subscriptions and device support.”均为完整业务范围，meaningful+business_scope | “公司追求高品质/We aim to deliver superior service”可作description但不得scope；“收入包括利息和税款”不是经营业务scope；他人分部不可借给issuer |
| 客户地域 | 港股繁体“收入按客戶母公司所在地分區”；英文“revenue by the location of the customer headquarters”与其真实region measure/note构成customer_geography，主体/期间/单位保留 | 工厂所在地、直播覆盖国家数、银行现金所在地不能当customer revenue geography；无数值的口径定义仍有用，不以有数字才通过 |
| stock与转换 | 非药业A股“期末未交付订单余额为X元，其中Y元将在下一会计年度交付”；美股“RPO was $X, of which Y% is expected to be recognized in FY2028”保留不同stock/conversion用途，具体FY绝对年份不特判 | “审计师评估RPO”“合同须确认收入”的定义不冒充当期stock；计划争取订单不当已签余额；第三方stock保留归属，不改成issuer |
| 稀缺竞争整合 | 12span cap的混合中英fixture，数十条可admit的改写宗旨/治理模板+scope+region+stock+conversion+真实经营约束；scope/region/stock在完整closure可容纳时进入，重复模板不得抢完；topic数受固定关系类型限制 | 不提高cap、不要求所有数字全选；模板伪造USA/order/revenue等词不得获得新novelty；有价值具体风险不为抢新topic被删 |
| 共享parent真实cost | H为父上下文，A+H、B+H两anchor；先选A后B只付B新增ID；字符也只付新增；原文refs一致 | 不得借shared H把兄弟C一并选入；A缺required或成环不假装更便宜；缺source主体不能只靠parent heading恢复虚构值 |
| semantic重复边界 | 同一模板标点/换行变体可沿既有保守签名处理；泛描述不与具体稀缺fact同价值 | 不合并相同数字但不同业务/币种/年份；不混订单增长与收入增长；不以主语词近似合并限制条件不同的事实 |
| 回放/费用/有限work | 同输入乱序稳定；旧显式policy结果不变；低work上限产生明确partial/诊断，不输出半闭包；48000/96/16M及envelope不变 | source新字段坏值/无界topic拒绝；费用unknown不清零；不调用下载/LLM、不产生原文副本 |

先跑source owner和budget public API中性集成测试，证明baseline具体RED。实现source价值/覆盖改法后，跑既有自然包和cache依赖；只在大节点独审。最后做一次本原件当前代码完整离线选材+同14目标独审，并加另一市场/语言未知公司小样本；既有7pass不得回退。若只改scope进入、地区口径/确认计划仍缺，应诚实保持partial，转来源依赖或按需提取，不写“14通过”。

## 5. 已知未知与风险

- 没有全量offer-time rank/visit快照，不能证明泛治理具体第几轮挤掉A01；真实选择输出仅证明共存和具体目标延期。
- 没有运行source纯函数去证明每条正则推测；A01的unknown可来自识别或source-state投影，必须用分层RED定位，不一口气改两套语法。
- business_scope/stock/geography不同topic应改善当前饥饿，但因96 cap竞争、口径依赖、父子日期缺失，不保证完整14净改善；正式摘要和RF采用仍需后续。
- table-qualified无条件meaningful目前是现有代码，尚无本轮具体错误table归因证据；只增加同类中性反控，不先推大table重写。
- 同句当前事实+通用愿景应以真实关系保留meaningful，不能整段降级丢事实；同样同段一句真fact不能赋予所有其他行独立meaningful/novelty。
- 新固定关系类型不应膨胀成每行业、每公司、每metric一套taxonomy。它只是回答当前阅读策略的问题，不生成下游投资结论。

## 6. 交给ROOT的单一下一行动

**先为source owner写中性“admission不等于material value、scope/stock/geography用途不丢”RED，并通过已有budget public API做12span稀缺竞争整合；确认实际RED后再实现上面第3节。** 保留当前planner；以一次新的真实14项对比决定是否还需动rank，不继续仅删模板。
