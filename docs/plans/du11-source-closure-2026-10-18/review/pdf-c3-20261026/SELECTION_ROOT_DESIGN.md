# C3 后续选材共因诊断与 TDD 设计

状态：**READ_ONLY_DESIGN_READY；未实施**。先由 ROOT 发布已通过验收的 runtime/cache/gate 基础节点，再串行进入本设计。不能在基础节点发布前并发修改 generation、selector 或其依赖。本文不是新许可链，也不增加小节点签收。

## 结论

此次 HK 缺口主要在**读到之后的语义识别与主题投影**，不是 PDF 读取失败或 work budget 不够。先保留 `reading_plan/3` 的事实优先、防套话和完整上下文约束，保持真实批次 112 spans、48,000 字符及原 work/time/cost 上限；在共同语义 owner 补充经营资源和具体公司计划的证据识别。不要改 heap 排序来掩盖识别缺口。

三个须区分的概念：`admitted=True` 只是可以读，不是优先摘要；`meaningful_fact` 是有信息量的来源陈述，不是“已经实现”；`operating_plan` 可以有摘要价值，但必须保留将来、条件、主体和时点，不能当成实际资源或已完成进展。

## 现场证据与因果链

1. `native-selection-observation.json.gz`：native-only 4.308 秒，来源共 2,330 units，work 3,636,909 / 16,000,000，输出 112 spans；文件仅保留 p11/p13 的 67 个原始 unit 和 22 条 admission 明细，不能将 67 误当全文总数。
2. p11 研发段的完整 native_continuity 已包含“420.5百萬元（58.7百萬美元）”和“1,094人”；完整展望段包含“下半年”“投資技術研發”“提升AI能力”。二者均 admitted=True、priority=1，required context 均 2 个。fact 均 eligible=False、topics/reasons 空、purpose=unknown。另一段 620 人的研发中心资源也相同。
3. 在 `narrative_reading._candidates`，空事实可作为业务/展望段描述进入；随后得到 `value_band=description`，仅补章节 topic `business` 或 `outlook`，不会凭标题制造经营事实。
4. `narrative_budget._reading_plan` 的 v3 rank 是 value → novelty → mean visits → priority → repetition/score/cost/source order。事实始终先于描述是现有测试明确要求。112 slots 用满后，这些段落出现 budget_full；不是 work_budget_exhausted。
5. `hk-v2-source-check/diagnosis.json.gz`：增强成功、3 pages/约117秒转换，总观察125.181秒，仍为2,330 units/112 spans；work 3,778,313 / 16,000,000、exhausted=False。重跑增强不会解决已完整读到的 p11 语义缺口。
6. 本次零 IO/模型的纯语义观察覆盖 25 个中性句。简体/繁体/英文 5 类人员数量表达、2 类研发投入表达全部被归为 description；繁体和英文研发计划也如此。另用真实 `_candidates` + native fixture 对 3 类人员、2 类计划复现，均 complete=True、withheld=0、admitted description。见 `selection-design-probes.json`。
7. 小型纯 planner 反例：3 个 slots 内，description 展望不能挤入；即使改成 meaningful，但只有已拥挤的泛 `operating_quantity` topic，仍会落选；赋予来源证明的独立 resource 或 plan topic 后，**同一 v3 planner 和同一 cap** 能选入。这证明需要补正确语义主题，而不是只改 eligible 布尔值。

## 共同根因

### A. 经营资源没有进入受约束的 metric 模型

`narrative_business_policy._OPERATING_MEASURE` 覆盖客户、项目、订单、产能等，没有研发人员、研发团队、工程师或研发投入。既有 `_SOURCE_QUANTITY_UNIT` 已认识“人”，但没有相应 metric subject，所以句子根本到不了 quantity/state 关系识别。

不可简单把 employee/研发加入任意 keyword OR；“员工福利负债”“研发培训手册1094条”“研发费用计入损益”会借数字变成伪经营事实。人员数量和投入金额的对象、单位和目的不同，也不能共用“任何数字都算”的规则。

### B. qualitative plan 的关系语法窄且并列作用域不完整

`narrative_business_disclosures._qualitative_operating_intent` 需要局部 plan→action→object，动作/对象词表偏产品、渠道与服务。投资研发、配置研发资源、提升特定技术能力未覆盖；又先按逗号拆段，后续“持续投入…并提升…”可能失去前面的公司主体、未来时段或 plan marker。

修复应补**可证明的并列谓词与作用域**，不能把“将/未来 + AI”变成条件。既有 `narrative_predicate_state` 是 modality/time owner，不能再抄一套 will/if/预计/尚未词表。

### C. 语义分类与覆盖标签缺少中间层

当前 topic 常来自 reason 名，章节标签只给描述。故“已识别到资源”若仅补成通用 operating_quantity，仍可能与客户/项目细节共享拥挤主题。阅读策略里的问题/summary_focus 是提示，不是句子证明，不能直接拿作已回答的 coverage。

本次先用现有 `reading_topics` 承载**有限、来源证明的语义主题**，不要增加第二 planner、第二候选库或章节配额。事实识别之后再投影资源/计划主题；标题只供上下文，不能升级 value。若语义修好后同 cap 仍有真实重要缺口，再单独论证 planner v4，保留 v1/v2/v3 replay；当前证据还不支持先改 rank。

## 责任层与实现接口

建议新增纯模块 `src/company_wiki/source_catalog/narrative_operating_resources.py`，集中经营资源观测；避免继续膨胀全局词表。它属于同一来源语义层，不做 PDF、provider、LLM、下载、金融 API 或研究结论。

内部接口草案（不是跨仓新合同）：

```text
observe_resources(bounded_matching_clause) -> tuple[ResourceObservation, ...]
ResourceObservation:
  family: workforce | research_allocation
  measure: persons | monetary_allocation
  metric_span, quantity_span, unit_span: matching-view offsets
  predicate: existing PredicateObservation
  explicit_actor_span?: matching-view offset
  purpose_link_span?: matching-view offset
```

- 量值不换算、不造 period/actor，不生成新的原文 locator。offset 只在现有匹配文本里供分类；实际证据继续沿用 SourceOperatingSession、native range、required refs 的原文链。
- 复用 `matching_reading_text`、`predicate_scope/observe_metric_predicate`。简繁转换只用于匹配，原文、数字逗号、括号双币种、原语言不变。扫描次数/长度有界，新增扫描计入既有 `READING_BUSINESS_SCAN_PASSES`；work 不足不重启文本 fallback。
- `narrative_business_policy` 负责把观测映射为 OperatingFact/value/topic；`narrative_operating_relations.SourceOperatingSession` 继续独占按来源闭合与 work 预算；planner 不看 raw_text。
- 生产 0.9 投影接线到 `assess_reading_business_fact/project_reading_business_fact` 的现有 owner。先检查兼容调用链，**不能未经测试直接扩展被旧 0.8 路径调用的 detect_reading_business_fact**。已有 `named_recognition_scope` 只加于 0.9 投影的做法可作结构参考。
- 计划关系也由同一来源语义层输出；可在既有 disclosure 模块增加生产专用 observer，但旧 `_qualitative_operating_intent` / legacy DTO replay 行为须被冻结。不要让 summary、RF、profile UI 再重复识别句子。
- 新模块必须列入 `document_understanding/decision_inventory.py` 的 business implementation hash 清单。发布时推进 reading business policy 版本（当前 `/19`），同时验证相同输入的新 selection digest、旧 completed artifact 的历史只读。此次不改 `reading_plan/3` 常量。

## 明确识别边界

| 来源陈述 | 结果与条件 |
|---|---|
| “期末研发人员达1,094人 / R&D staff totaled 1,094 people” | 实际资源 stock；metric→数量→人数单位在同一有界断言，复用实际/过去时态判断。topic operating_resources；不会推出生产能力、收入或生产率。 |
| “研发中心总人数620人，包括实习生和外包” | 保存整体原句及 included/excluded 口径、截至日期；不能自动变成员工正式编制，也不能拿历史620与当前1094直接算增长。 |
| “本期投入420.5百万元用于研发平台 / invested $80m in R&D” | 明确投入动作和研发用途/资源对象，允许 research allocation；金额、币种、期间、资本化与费用化口径原样，不换算货币，不把支出视为研发产出。 |
| “研发费用420.5百万元”独立会计行或三表摘录 | 本次不因金额单独升级；结构化财务获取属于既有金融 API。若与实际人员量同一原文段，因人员证据选择该完整段，费用信息自然同行保留，不对其建立第二套财务 extraction。 |
| “研发费用按会计政策计入损益 / capitalized under accounting policy” | 纯会计 policy，仍非经营；新的 resource recognizer 不能越过 source_purpose。 |
| “下半年我们将持续投入技术研发，并提升AI能力” | issuer/实际发言主体 + future/plan scope + 具体资源配置动作 + 技术对象。是 operating_plan，有摘要价值，不是实际资源增加/能力已实现。缺少金额不补零。 |
| “we will improve efficiency / 为社会创造价值 / 高质量发展” | 无具体资源配置或业务动作对象，保留 description；outlook 标题、AI 一词均不能独自提权。 |
| “如果人员达到…，我们将考虑…” | 不给 actual stock/allocation；若有明确公司条件计划，可保留计划及条件的完整闭包。单纯假设数量没有公司计划则不造事实。 |
| “尚未达到… / 未确定计划 / may change” | 不是实际完成；只按原有 restriction/qualification 规则保留来源限定。不能只留下数字或积极计划句。 |
| “请问是否… / Will you…?” | analyst/question role 仍 context-only，问句不能当公司计划。回答若未给承诺，不从问题补出承诺。 |
| “合作方/供应商研发人员…” | 若有明确事实可保留第三方来源陈述，但不能归成 issuer 资源；topic 不负责认定主体，原文/attribution 必须一起留下。 |
| “员工福利负债420.5m / employee option grants / 培训手册1094条” | 财务对象或编号，不是人员数量；不允许 head noun/跨谓词借用数字。 |

计划的并列继承只在**同一已闭合 native owner、同一主语、同一条件作用域**内成立；遇到新主语、but/while/whereas/而/但、会计谓词或新的时态即停止。不得跨公司、来源、章节或不连续页拼接。句子内计数的千位逗号不作为断言分隔。

建议投影（名称实施时统一一次，不可各消费者私自解释）：

- 实际人员量：reason `operating_resource_stock`，topic `operating_resources`；不是普通 financial-exempt 一刀切。
- 有用途的实际投入：reason `operating_resource_allocation`，topic `research_investment`。
- 明确未来资源/能力计划：reason/topic `operating_plan`；可附来源证明的 resource topic，但不附 actual resource reason。
- 每条新增观测最多 2 个语义主题；不以公司、年份、页码、具体研发中心、AI 品牌建 topic，也不把各 reading question 全复制进去制造 novelty。

## TDD 施工顺序（一个工程审查节点 + 一个内容节点）

### 1. 冻结不变量与 RED

新建 `tests/unit/document_understanding_selection/test_reading_operating_resources.py`，优先通过 SourceOperatingSession / `_candidates` 验证**生产投影**，不是只对字符串 helper 断言。

1. 简体/繁体/英文人员 stock；人数单位（人/名/people/employees/engineers）、numbered/totaled/employed、千位逗号；当前、历史明确日期都保留，不把年份当数量。
2. 金额与人数同段、括号第二币种、资本性/费用性投入明确限定；保留整段及原始 chars/SHA。裸会计费用、福利负债、费用定义为负例。
3. 未来研发投入与特定能力计划：带明确主体/时点、无数字仍有效。并列延续可识别；更换主语、假设、未决计划、未答问句、通用价值观应有不同结果。
4. CN annual/interim/IR、HK interim/prospectus、US 10-K/10-Q/transcript 的适配参数（language/source_role/section_role）；**市场标签改动不应改变同一句的语义**。报告形式只负责结构及阅读范围，不能切出独立事实分类器。
5. 永久 rank 回归：拥挤客户/订单事实 + 后置 resource/plan 闭包；原 cap 下两者被选，纯描述仍不能抢占事实。反转输入和改页码/公司名/数值保持语义结果，最终输出仍按真实 source order。
6. 拆为2–4行的 source fixture、显式同段续行、共享标题/期间/条件；真实原文 refs 和 required closure 全保留，不因 cap 拆半段。不同 source/actor/无证连续文本不得合并。

RED 以目标断言失败为证，若只是 import/setup 错误需先修夹具；不得把现状 description 写成期望来“通过”。保留现有所有 assert。

### 2. 实现共同 owner，GREEN

按上面的 resource observer + production projection 接线；先不动 planner。以中性反例测试驱动，不向原文词表塞“420.5、1094、金山云、p11、半年报专用”特判。

重点防回归的既有短测：

- `test_reading_material_value.py`：通用收益/理念仍 description；会计、产品用途、真实机制区分。
- `test_reading_semantic_value.py`：生产 native carrier 和金融数字借用负例。
- `test_reading_predicate_state_owner.py`、`test_reading_measure_scope.py`、`test_reading_predicate_generalization.py`：actual/plan/condition 共享所有权。新增 actual resource reason 必须进入这些测试的实际理由集合，不能因旧集合不知道新 reason 而漏测。
- `test_reading_order_metric_language_parity.py`：语言、数值变化、未来量与实际量不混淆。
- `test_reading_value_coverage.py`、`test_reading_balanced_coverage.py`：事实永远优于纯描述、稀疏主题公平、原文唯一计费、完整闭包、missing context、work stop 和旧 policy replay 不变。已有20k性能案例只在本节点跑一遍，不改每commit门禁。
- decision inventory 相关短测：新增模块字节变更改变 digest，两个输入无关的 company/page perturbation 不改变语义。

按组运行有界短测，失败只重跑相关组。若超时先读已落日志和存活子进程，不重启整批。工程独审只在上述完整 GREEN 后进行一次；独审发现问题修完后复验相关反例即可，不增每小步签收。

### 3. 既有真实 HK 内容节点

复用当前已登记原件和冻结 oracle；先 native-only 一次选材观察，**不再为这两个已完整原文段重跑 Docling**。确认下列内容进入现有模型材料闭包：

- 原研发段同存 420.5百萬元、括号58.7百萬美元、1,094人及各自日期/单位；不得算成两个投入金额合计。
- 下半年计划仍为将来，研发投入和AI能力目标与公司主体相连；不能声称已经实现或添造预算。
- 如果620人的历史段进入，保留2024年底、实习/外包口径；不要求强塞所有 resource 段，也不强求一段占一个 slot。
- 源 SHA/原件/生产配置不变、max112、max_chars48000、work≤现有上限、0模型/0下载/0新原件；required context 不丢，不新增不可解释的高价值召回退化。

检查点必须看实际最终 spans/summary input，不只看 fact.eligible=True。如果仍没进入，先用 selection trace 精确定位 topic、closure cost 或预算竞争，不直接扩大 cap。这个节点通过后，再由 ROOT 按主 PWF 跑一次正式摘要及缓存恢复；本只读设计不抢跑该任务，也不触新 holdout。

## 明确保留的 rank / 架构约束

- 不改 `test_fact_value_always_precedes_even_novel_high_priority_description` 的期望。
- 不按标题/页码/公司/市场提权，不为每个章节预留 slot；没有原文支持的阅读问题仍 unknown，不能视为已覆盖。
- meaningful 不等于 actual；计划/限制有意义，但必须保留 modality 与条件。未知不自动变完成。
- provider/PDF SDK/结构化三表 API 不进入语义 observer，RF/summary 不覆写原文分类。
- 本轮不迁移数据库、不新增审查许可、不修改预算制度或重做大批 PDF。上个节点的历史恢复/当前执行区分保持原验收结论。

## 交接与可执行性

唯一当前动作：ROOT 先完成基础节点提交推送。之后由 ROOT 按本设计开一个来源语义 owner 实施任务，审查者独立于作者；不要把 resource helper 与计划投影分给会同时写同一 business policy 的两个 harness。

本次只读诊断产物：本文件、`selection-root-design.json`、`selection-design-probes.json`。未修改产品/测试、未执行 parser/Docling/LLM、未下载、未复制原件、未触新 holdout。这些探针是基线观察，不宣称修复已通过。
