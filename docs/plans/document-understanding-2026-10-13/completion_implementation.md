# 共享引擎＋文档阅读策略：统一收尾施工细则

Owner: ROOT。状态由同目录 `task_plan.md` 唯一管理。此文合并原 `implementation.md`、`review/root_implementation.md` 剩余 B8/B10–11/C12–15；两份旧文件保留设计依据，旧阶段状态不再调度。DU/DU2 接收账保持已完成，不重开已交付卡。

## 1. 完成范围与已有事实

目标：正式资料处理链使用同一个结构、策略、选择和摘要引擎。不同市场、文档用途与业务重点通过配置组合，格式适配器只负责提取真实内容与坐标。CWP只产生来源型摘要和证据，研究预测由RF/StockWiki负责。

已完成：唯一运行 `profiles/reading_catalog.json`（24文档规格、14业务策略）、真实父子章节范围、实际采用策略指纹、布局工作预算、已有字体/粗geometry透传、最终原文上下文实物化。源码deb7eb7d已并master并推送，CI38476678472 success；PWF收尾9e4faf2a已推送。1135联合PASS、四PDF658span原文回放、真实10-Q六项通过。详情见 `du2-reception/acceptance.md`。

生产接线已于d3c57b31/fc2a4513发布并通过精确CI：公开显式0.9、ReadingPlan进入正式span选择/模型请求、final generation CAS及same-run/outbox/v5恢复工程验收完成。剩余：真实依赖组件接入后的跨run缓存；同预算真实摘要质量及母G2/G4/G5；细geometry生产前端。微软关键业务旧baseline4/8与初新1/8 FAIL保留；实际form/意义修复后当前7/8，仍须关闭章节/预算共因才切默认。

**接收后再核对的准确结论：** DU `summary_input.evidence_packages[*].members`重复物化共享正文；现有生产 `NarrativeModelRequest`已经使用唯一evidence行和group别名引用，最终HTTP不因group重复全文。修新链时复用这一正确传输机制，不能据DU重复视图重写另一套HTTP协议。

## 2. 责任层与唯一入口

| 层 | 承担的任务 | 既有入口/输出 |
|---|---|---|
| 来源/存储 | 原件字节、身份/期间/as-of、SourceRef、路径与读取 | SourceReader；下游只用来源引用 |
| 格式前端 | PDF/native/OCR、HTML、TXT/JSON、PPTX等读取，真实locator与覆盖 | 现有parser、NarrativeNormalization；不判断投资意义 |
| 阅读引擎 | 路由、章节、实际范围策略、布局与必要依赖 | `understand_units`，ReadingPlan/依赖图 |
| 内容选择 | 候选准入、业务价值/多样性/新信息、完整闭包和真实成本 | 既有 `select_narrative_evidence → finalize_selection → select_budget_items` |
| 摘要请求/模型 | 实际选中的唯一原文表、策略指令、原语言、别名与usage | `NarrativeModelRequest.from_selection`；BudgetedNarrativeCaller |
| 调度/缓存 | generation、lease、outbox、可恢复并发、有效复用 | 既有AUTO Store / narrative_batch / NarrativeRef |
| 消费者 | 验证版本化来源出口、消费业务摘要；独立研究模型 | FF/RF/StockWiki，不跨仓直接读目录 |

保留单个运行catalog；compiler只维护编译，不成为运行第二来源。文档类型策略不下载资料、不提升预算、不另建任务库。正文中的指令仍按数据处理，不新增逐材料许可、人工签收或canary链。

## 3. A：选择与唯一材料，先TDD再实施

### A1 先固定反例

在现有预算/DU root测试包增加少量行为测试：

1. 仅改真实父/子ReadingPlan priority，**生产**选择变化只发生在匹配范围；改无关策略不影响该文档。
2. 不同公司、不同项目周期（如2–7个月、12–18个月）照常按意义入选；4–9个月或某个题材没有特殊保留资格。
3. 经营表格与描述段落共同竞争；纯财务/重复同主题不得挤掉独立重要业务。定性事实无需编数字。
4. 两个项目共享表头/脚注：各自闭包完整，唯一unit/span和字符只扣一次。相同字串、不同locator/主体/期间不可仅按text合并。
5. 必需依赖超预算整包deferred；`all candidates fit`捷径也计算依赖，不能按锚点数放行。
6. 否定、期间、单位、问答角色与项目阶段保持；context-only不当价值锚点，不把问题当管理层事实。纯财务季报/行政材料经完整可读核实允许0派生/0模型；财务附注中的真实业务变化仍入选，opaque/未读不可假装no_value。
7. 最终实际 `NarrativeModelRequest.data_json` 中共享正文一次、策略一次、每包引用可回原文；仅检查DU中间JSON不足。

### A2 实施边界

- 新只读选择上下文携带unit→实际范围ReadingPlan、facet提示、既有唯一依赖图、原文成本表；传到现有预算planner，扩展明确的新selector policy。旧版本0.6.0/0.7.0/0.7.1/0.8.0只保留必要历史回放。
- 同时检查候选准入与排序，替换固定集成中心/4–9个月regex、题材boost/预留预算及具体样本词句的活跃新路径；不能只重排已被过滤过的候选或提高cap。
- 业务价值用实际policy priority、业务问题/facet提示、具体变化/风险/机制、主题覆盖、新信息和边际闭合成本表达。facet不是事实证据；最末仍按**实际送出原文**形成模型提示。
- 只有一个价值选择器。orchestration提供结构包；summary assembly验证并物化已选闭包，不能各加另一套排名。
- 多包共享context使用唯一材料表及组ID引用，复用现有eN/gN传输；共享依赖不把所有包并成一个巨包。最终字符/字节与provider tokens/usage分别计量。
- 原文、旧ID/locator、历史parser回放保留。临时兼容视图不得与唯一表一起进入模型或持久化成两份全文。

受影响范围：source_catalog的narrative_evidence/candidates/group_candidates/budget/finalize，document_understanding的selection_bridge/orchestration/summary_input。直接回归：`test_n6_budget_selection`、`test_narrative_selection_architecture`、`test_n6_dedup_context_safety`、`test_s7_operating_fact_semantics`、`test_s7_adoption_project_context`、DU root tests，integration的n6 candidate/budget packages及历史persisted compatibility。不为每helper新增一份审查。

## 4. B：正式生产接线与缓存，先TDD再实施

### B1 精确接线

1. `NarrativeSelectHandler._select_normalized/_select_pdf/_select_transcript`继续用已解析原文；共同 `_run_selector`接一次 `understand_units` 和A选择上下文，PDF不重新转整篇MD、HTML不另建parser。
2. 一个automation adapter将最终唯一原文unit经原 `NarrativeUnit.to_evidence_span`映射成canonical span，保留原coordinates/parser/raw，不能以摘要文字造证据。类型化SelectResult通过兼容字段携带**紧凑**reading summary：实际策略/依赖版本、focus/问题/负提示/风险约束、组→已选EvidenceSpan引用、unread/deferred。policy不逐span复制，不持久保存完整observation/DOM/all-units。严格wire解码和旧生产者兼容一起更新，不能任意塞JSON绕过类型检查。
3. `NarrativeModelRequest.from_selection`消费这些实际策略，仍用现有canonical aliases/response schema。`NarrativeSummarizeHandler`仍只经唯一 `model_caller.generate`；字节/费用/超时由原负责层执行。
4. `register_narrative_handlers`提供可注入正式依赖；测试使用真实handler/runtime路径及loopback模型端口，不新立canary流程或另一个摘要服务。
5. official_json、TXT/JSON电话会及普通normalize材料在同一类型接口下接入；记录/发言的原始父来源、role及group范围保留，不能跨父来源合包。PDF缺geometry可以partial，不能因此丢全部可读业务。

公开有限批次请求新增可选 `selector_version: "0.9.0"`，由同一个request/execution binding保存；省略时沿正式默认，旧请求编码/身份保持。生产验收和真实批次直接用该字段，不通过sitecustomize修改默认或全局常量。该字段是算法版本选择，不是放行许可。

### B2 generation必须区分两种依赖

- **selection依赖指纹**：本次路由、候选准入/排名实际查验的matcher与策略内容、相关父/子范围、结构/选择版本。包括可能改变赢家的败选候选；同family/form中新增加/修改的匹配信号亦纳入。不能仅hash旧版最终入选内容。
- **model输入指纹**：最终实际发送的policy/facet/约束/原文引用及prompt版本。现 `reading_policy_version`适合这一层，不直接代替selection cache身份。
- source/normalization、结构/选择/summary/layout feature、原语言、prompt实际内容/version、schema及output plan参数都沿实际执行绑定；实际model_id/endpoint/output tokens/thinking/reasoning/temperature/output_token_field沿现 `generation_manifest`配置及HTTP omission规则绑定。api_key/env名、pricing与runtime timeout不作为生成内容身份；P1/P2/P4是worker profile，不能冒充文档阅读profile。正式factory复核构造后的effective spec与冻结代一致。
- final selection同时保存完整select结果SHA（Store审计）和`material_sha256`（SelectResult/Bundle共同实际材料：subject、source_metadata、selection、evidence、reading_context、电话会lineage/byte bindings）。Bundle省略parser name及select时的review诊断，不能伪造重建whole select hash；公开读缓存重算物料SHA，仍核final metadata和原始证据。partial dependency可有诊断用SHA，但不是cache-ready。
- 原件实读由正式select/public read负责。当前0.9 cache命中在同一operation以非持久`verified_reuse_keys`复用已完成字节证明，不再二次实读；该字段不进binding，恢复/另一operation必须重新public read一次。自己已完成raw历史同样走public read，篡改原件不能返回完成。unknown-language探测或独立消费者回开分别计量，不伪称整个跨进程系统只读一次。
- 原 `narrative_batch._run_owned/_run_prepared`、freeze/thaw和reuse pin只扩展本源因果字段。不得whole-catalog hash导致无关改动全库失效；也不能为复用先parse/select一次、进入worker再parse/select一次。
- 明确采用**base归属→正式select一次→final generation CAS冻结→释放summarize/verify**的两阶段顺序。base归属不等于模型可运行的generation；未冻结前model不得运行。miss时只在原AUTO compute/select阶段解析/选择一次，后续消费同一个类型化select结果。不得在coordinator另跑DU副本后worker重跑。
- cache precheck只比较已有候选的紧凑decision trace与当前相关组件/候选集合，不跑selector。trace须含曾参与匹配的候选集合membership及matcher/full-content digest，覆盖新增或移入适用范围；只存最终winner不够。与base一致并通过现有read_reuse_pin原文/定位校验才复用0POST。没有新trace的历史产物仍能回放，但不能冒充新策略缓存命中。
- 每项内容身份用完整digest；展示用短profile_version不作唯一缓存凭证。旧run恢复使用已冻结策略结果与effective spec，不能因当前registry漂移重签旧job。generation冻结与任务释放由既有Store/CAS和outbox负责，不新建持久缓存库。实现前确认现有job ID、binding和取消语义，在B反例框住交界，不借此恢复签收许可。

### B3 集中工程与离线端到端节点

使用现有 `tests/integration/test_narrative_production_factory_e2e.py`（production factory/子进程/loopback）、`test_narrative_generation_reuse.py`（PDF/HTML/TXT与mixed miss）、`test_n6_batch_upgrade_identity.py`、`test_narrative_generation_outbox.py`、`test_narrative_batch_recovery_e2e.py`、`tests/support/narrative_model_fixture.py`与现九型pipeline工具，增加决定性反例：

- SourceRef→真实normalize/parser→DU→正式select→真实ModelRequest→loopback→NarrativeRef→RF来源消费。覆盖PDFnative/有限OCR、HTML、TXT/JSON电话会、PPTX、官方记录、纯财务/行政低价值材料。
- 再次运行同源同配置0POST；相关已用策略变化、**旧版未选但实际匹配的候选**优先级变化应失效；未查验无关策略正文变化0POST。
- 原文修订/实际模型spec/原语言/prompt变化只失效正确对象；metadata不把H1/YTD当Q2，不换币种/量级。
- 不合作OCR/429/超时/unknown usage/取消、丢ACK和重启沿AUTO恢复，不能重复付费、重复提交或漏记未知费用；解析及模型并发分别有界。
- 在select完成/final CAS前后、模型已付费/outbox尚不可见分别注入终止。恢复不得重新选择漂移策略、重复费用或另run偷用未完成产物；正式factory必须使用真实batch frozen binding，不能monkeypatch假selector给出绿。
- 最终alias/group与原文回放、正文出现次数、输入字节/字符、实际usage全部检查；策略相关域与生效范围有证据。
- 原 `test_narrative_model_request`和`test_narrative_generation`单元测试覆盖请求hash、两种指纹、effective spec及100-source freeze/thaw体积；miss解析/选择计数各一次，locator独立回放校验不算第二selector。
- 每次独立TemporaryDirectory，现有生产配置SHA/mtime、原件SHA/mtime/size和预存sentinel不变，测试新增下载/DB/PNG均在finally恢复。缺配置明确PARTIAL/NOT_RUN，不人工门禁。

A/B实现期间先集中受影响测试，修失效后只重跑受影响范围。B完成做一次联合节点与独立共同根因复核，正常commit/main/push及精确CI；不把大套件加到每次commit。

## 5. C：真实质量、默认切换与母计划共同验收

1. 使用现有20原件开发清单与真实gold，旧/新同原件、读取范围、预算对照。当前已看过的样本只能称回归；新A/H/US公司组成独立泛化样本，不用改文件名当holdout。
2. 类型覆盖逐项列真实/合成/缺样：年/半/季、A/H/US招股、增发/可转债、IR、电话会、10-K/Q/20-F、8-K/6-K附件、S-1/F-1、修订稿、presentation、低业务/行政。新类型优先扩数据，不克隆pipeline；缺真实样本不据schema PASS认证语义。
3. 复用现有有限版面/OCR预算：已有字/行/DOM/表区域先行；仅对重要且关联不明的业务表格/多栏页补读真实word/cell/ROI，推断不改locator。细几何缺失单列，关键经营信息漏读仍需解决，不能靠partial标签签业务通过。
4. 精确核本机配置，按实际MiMo/DeepSeek/MiniMax能力/limits执行原语言摘要，不根据供应商名猜模型；沿原任务累计账$20/200万token及unknown/FX hold，不建新预算，不按每材料重新许可。密钥不进入提示、报告或Git。
5. 共享一次母G2/G4/G5窗口：G2真实摘要使用与回原文；G4原三家公司独立四审；G5换新A/H/US三家公司。RF流程/事实与数字/买方模型质量分别由相应审查者负责，CWP不写投资结论。微软旧4/8必须实际改善，原失败证据保留。
6. 冻结可用样本分母与gold后再比较：关键业务全部保留且无主体/期间/阶段/单位错误；原一般召回/precision/context目标需沿原A冻结依据，不临场降低。有资料不可读或预算限制要分开计，不包装成PASS。
7. 同时测首次/复用时间、parse/昂贵表格/OCR、独立RSS观察、raw/derived/scratch/db增量及并发2/4文档。未经测量不声称p95或节省百分比；不靠删业务信息满足体积。
8. 达标后一次切正式默认版本，清理替代运行入口/重复关键词逻辑/旧prompts；只保留历史NarrativeRef回放所需版本。派生只存精选span/摘要、紧凑结构和必要usage；不保存整篇MD/DOM/全阶段快照，不复制原件。
9. 正常合主线、推送和必要技能定点同步，核精确CI/真实入口；只清本次owned scratch。母PWF同一G2/G4/G5状态更新一次，随后沿既有revenue-forecast-audit公司循环，不创建竞争队列。

## 6. 完成判定与交接

### 2026-10-14 真原件暴露的格式粒度共因（优先于真实付费）

最终保存材料由统一独立oracle重新计分：US 8/8、HK 7/7、CN 2/10。US先前0/8是测试helper忽略HTML的`location_kind=document`，已用独立反例纠正，原失败收据不改。CN真实96 spans仅3339字符，69依赖/27锚点；p13现状/未来目标/收购与p18多个业务阶段已进入正确候选，仍因原生PDF半句碎片占槽落选。`_sentence_fragments`本身只按标点切，主要碎片来自PDF实际DICT块边界。提高score、去除必要依赖或按gold保留不能根治。

实施顺序与排他接口：

1. 来源层在既有一次DICT扫描内定义`native-pdf-page-view/1`：实际原序block文本及原换行构成一个可回开的格式视图，绑定每块SHA和视图字符范围。仅新0.9/确需native-range回开时构造；只在内存共享，不逐单位复制、写全篇MD或保存页正文。旧0.8原单位/Span身份不变。
2. 共享连续性引擎仍负责真实字体/列/标题/表/主体/期间作用域与闭包。来源层`native_range_unit(original_members)`只把该已验证身体映射到原生视图的严格substring，使用`native_pdf_range_parser/0.1.0`、`pdf_native_range`和显式坐标空间/原member IDs、SHA/ranges；最多8原单位/4原块/2048字符。没有共同原生range证明保留旧多span并诊断，不能在selector拼造新正文。
3. ROOT将有来源证明的carrier接入同一候选/planner：一个真正源range按一个span付槽成本，原字符/字节全照计，仍96/48000；同一身体不与旧碎片重复发送，标题/脚注共用唯一引用。原单位到carrier引用映射用于实际策略和context，不能重跑DU/另建排名器。原生范围不是模型摘要。必要否定/未来/阶段不得为了缩小闭包裁掉。
4. 回开只由来源层验证原件与范围。native range的底层仍旧0.1.1 parser，兼容普通span、QA/table和旧ref；坏来源/页/range/member/SHA、截掉限定语或改词必须拒绝。不要求消费者重新推断几何或物理目录。
5. 新carrier内容身份与producer feature进入现有selection-decision依赖，整体pipeline升级；旧缓存不能误用。RF仅消费版本化source-bound出口，不创建下载/几何/人工许可。四个owner排他：来源view/回开、候选语义、RF DTO、ROOT正式接线/PWF/发布。
6. 先小真实PDF与历史定位TDD、旧QA兼容和篡改反例；集中源/选择/公开缓存工程节点后，同一CN原件/同gold/同cap一次新回放。原CN2/10不删除；若仍有漏读继续查共享原因。达到重点保留再花真实模型预算，不能以unit压缩本身签质量完成。

以上属于A/B原步骤的根因修复，不增加审批、canary、小节点签收或第二parser/任务库；仍在三大节点验收。

只有A的生产选择/唯一材料、B的正式链/缓存/恢复、C的真实质量与泛化都通过，并真实切默认发布，才标“共享阅读升级完成”。模块绿、引用存在、路由正确或loopback绿各有范围，均不能代替真实摘要忠实度。

ROOT维护一个状态表、一个Next Step；三大节点汇总命令/退出码/耗时、版本、样本分母、实际调用/usage、原件/配置/目录恢复、失败及仍未测。沿原receipt格式复用小汇总，不增加审批JSON或每步手签。旧DU/DU2作者树与local bindings不动；FF/RF/StockWiki仅在消费接口确需更新时定点变更，Dayu/IQS及他人WIP不动。

可复跑步骤、真实配置绑定与预算账位置在节点开始记录；恢复时先读同目录task_plan/findings/progress，再读该节点收据。若测试失败，先判真实代码缺陷或oracle错误；只有独立反例证实oracle错误才能修断言，不能删失败测试/降低gold来完成。
