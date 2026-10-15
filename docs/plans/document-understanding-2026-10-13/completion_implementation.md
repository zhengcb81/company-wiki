## ROOT 当前状态与 DU4 并行分工 — 2026-10-15

当前已发布 master/origin 为 8206e78d；本地新引用归属/历史恢复工程尚未提交发布，不冒充当前远端 CI 已验。已完成集中工程验证：146 单元/契约 PASS（17.83s），正式生产 7 E2E PASS（85.63s），历史 None/v1/v2 恢复 6 E2E PASS（135.47s）；均 0 外部供应商调用，测试临时目录删除，配置/sentinel 保持。RF 新 context/2 与 claim context 引用的窄升级 145 PASS；安装副本仅定点同步一个契约脚本。全跨仓新版本联调及正常发布仍待 ROOT 收尾。

真实 HK 原件零付费重放 96/96，语言端口和逐 claim 语言聚合已修；原 source table 同时证实右列新年数据未被当前选择完整保留。旧付费失败收据不覆盖，工程测试不能代替摘要数字/经营质量通过。默认仍 0.8，三供应商正式质量、默认切换和母 G2/G4/G5 继续开放。预算未新增消耗：母 581487 tokens / 381768 µUSD 代理（含旧 unknown），累计上限 $20 / 200万 tokens。

新三份可立即开工的独立施工包见 [DU4 总计划](parallel/du4-2026-10-15/README.md) 与 [固定接口](parallel/du4-2026-10-15/INTERFACES.md)：TABLE 数字列/期间绑定、STATE 经营状态关系、FORM 原生表单/轮次信号。三个稀疏 worktree 已备好，源码/测试/作者 PWF 写入范围彼此不重叠；不复制原件或资料库。三包仅 A/RED、B/集中组件验证、C/交付三个大节点；没有小步骤人工签收。参考旧设计里宽泛的直接接线分工由本次卡的边界取代。ROOT 独占既有共享源码、真实接线/E2E/并线发布，作者可独立开始，不等待主线。

Next Step：ROOT 收尾新引用归属工程的跨仓联调/发布；外包三线独立实施其纯组件。接收后 ROOT 按同一共享引擎接线，做真实原件与其他公司 holdout、正式摘要及恢复的大节点验收。另记录 narrative CLI 全局配置误要求未使用 search/wiki 配置的责任范围问题，待主线单独修复，不把它描述成缺 LLM 凭证。

以下为历史冻结记录；若与本节状态不同，以本节为准。

## ROOT 当前接收与真实质量整改 — 2026-10-14

三 DU3 已实收，本地工程提交870b0a78。正常pre-push发现3个Worker重复解码失败及1个旧瞬时元数据预期失败（5153 PASS/24 SKIP），因此未推送；不跳hooks。Worker统一一次冻结快照已68 PASS，原count=1不变；几何测试补验共享/不可变/持久ID及model/Bundle不泄漏，36 PASS，非源码泄漏。

新真实MiMo请求输入13624 tokens（此前64804），但output8192中reasoning6547，最终JSON在c16截断；1次真实POST、21816 tokens、5002µUSD预算代理照账。没有原件修改、没有自动重发，独立测试目录已删除。母累计502598 tokens/353764µUSD（含旧FX保留），旧未知7项继续保留。原费用与FAIL收据不覆盖。

安踏周转天数实际已选中，旧测试把native表格分隔符误作漏读；品牌组合是真实通用语法准入遗漏，另有源已验真的枚举换行观察缺口。分开修复policy和单一测试oracle，不修改金标语义/12项分母。source25/25、fresh9/12只是旧冻结结果，不能提前写新分数。默认仍0.8，A/C和母G2/G4/G5开放。

接下来的统一实施顺序：①并行完成Worker/瞬时几何测试与通用portfolio/源表示观察修复，冻结后集中测试；②正式摘要使用已有generation_policy按narrative用途明确thinking设置，遵守真实配置，保留模型/endpoint/8192/temperature及旧代重放；③先原三零付费回归，再按同一母账进行三家供应商新旧真实摘要、各自独审关键业务/数字/引用/阶段及恢复；④质量达标才切默认，一次大节点验收、正常提交/推送和精确CI。若单次摘要仍不能满足覆盖，再设计复用现AUTO的有界分批，不凭提高cap或补截断JSON放行。

配置依据：MiMo/DeepSeek/MiniMax-M3官方均支持thinking disabled，当前缺少narrative用途配置导致供应商默认推理。工程根因修复将把用途选择集中放在已有配置端口，HTTP只执行并绑定配置，不写供应商临时特判、不增加许可。一般研究推理不变。具体外部依据和下一批真实结果随后进入收据，不能用配置意图代替质量证明。

以下保留此前冻结节点记录；当前状态以本节及阶段表为准。

## ROOT 冻结发布节点 — 2026-10-14

三 DU3 已全部实收，DEPENDENCIES 补交 282aee36/ef59a574 已纳入暂存、138 PASS，作者树只读不变。SOURCE STOP 已覆盖所有 ROOT 子线；正常发布工程节点，正式默认仍0.8，真实质量尚未达标。

源码因果版本：pipeline1.7、business-policy/5、table-purpose/3、source-script-match/1；唯一经营指标facet1.4同步源record与编译runtime，没有第二registry。简繁只作用于匹配，原文/ID/locator不改；混合表只保留实际经营行与必要上下文。264相关PASS＋新55/20Kcase共56PASS。实测同20K用例38.668→15.95s；2000 facts结果SHA逐项不变，宽正则seed快路是主因，固定配置词4096条/256字符有界缓存为次因，原文不缓存。

正式模型由已冻 scalar reading_model_projection=reading-model-input/1选择一个语义视图；仅missing表示legacy，present-null/未知不能误降级。旧0.8及旧unfinished原指令/输入保持，new generation因果不同，same/cross0POST；真实暂停竞态统一作为paused正常控制处理。相关111PASS、最后恢复16PASS、静态检查通过。保存真实MiMo输入重构136913→52618字节（策略111932→27543），96证据/64组引用和公开全context原样；尚未测新真实tokens或摘要质量，不能按字节降幅宣布质量提高。

ROOT因果＋生产选择42PASS；夹具真实HTML必须显式mime_type，不能用PDF默认或伪造frontend使partial假绿。CLI Python/native fd1诊断归stderr，JSON-only stdout18PASS。新正式离线CWP→FF→RF CLI联调PASS：0.8成为LATEST后精确历史0.9 Ref，完整body/context/spans/summary/sourceRef保持，same/cross0新增POST、两负例0预留，临时目录恢复，0真实供应商调用。

真实源码冻结回放原三25/25；新三9/12（SMIC4/5、ANTA1/3、Apple4/4）。精确漏项是分红计划、品牌组合、周转天数；安踏已保留Amer Sports最大股东与独立上市身份，不得把参股关系和周转天数的支持结果说反。分红属于用户业务阅读范围争议，旧12分母保持。仅Apple原文字面引号按独立验证修订，旧金标与5/12失败保留。第一份真实MiMo摘要仍7完整1部分2漏及4引用不足；母账480782tokens，新增11535µUSD只是预算代理。默认切换与三家真实供应商质量、母G2/G4/G5仍开放。

紧凑证据：[冻结节点与未完成范围](common-root-quality-evidence/finalization.json)、[23份实际测试/独审/回放收据](common-root-quality-evidence/final-receipts.zip)，另[前节点31份证据](common-root-quality-evidence/acceptance.json)保存原失败和第一次真实费用。RF aed581ac精确CI38609253663 success；CWP本节点正常commit/push后核精确CI，不跳hooks、不改他人WIP。

## 当前节点 — 2026-10-14 真实摘要之后

三 DU3 已交付。QUALITY dcde9aae 与 GEOMETRY a8cc604d 的全部改动已收到；DEPENDENCIES ef59a574 的补交 282aee36/ef59a574 已实收暂存，ROOT 138 PASS。它们修复同一依赖文件被重复扣字节预算的问题；完整 cache 仍由正式 AUTO 链验收。ROOT 未修改三个作者工作树。

本节点源码：business-policy/4 具名分部归属 161 PASS；唯一 operating-table-purpose/2 按实际经营行筛选、保留建设期/混合表经营行 286 PASS；其版本已进入决策依赖，因果测试 41 PASS；冻结代默认升级恢复 9 PASS（真实 selector 0.8→0.9 与 PDF parser 0.1.0→0.1.1）。旧升级测试实际未运行 bootstrap 的问题已纠正，不把基线失败直接当可删的断言。全部零真实 POST，独立临时目录与配置/原件约束保持。

真实开发回归原文选择 CN 10/10、HK 7/7、US 8/8；换公司开发泛化 SMIC 3/5、ANTA 0/3、Apple 2/4，共 5/12。它们不是未见 holdout；不修改 gold 或隐藏范围边界来提高分数。HK 实际路由是 hkex/annual，不能凭市场 metadata 猜错路由；简繁 matching、品牌/股东关系及混合经营指标仍需根因整改。两次只读 observer 的后置测试工具故障保留，不能签为真实 window 观测通过。

第一次实际配置 MiMo 摘要已生成、公开回开 verified、96 spans，67004 tokens（输入64804/输出2200），预算代理费用11535µUSD，非发票。母累计480782 tokens/已知345998µUSD＋FX hold2764；剩余1519218 tokens/$19.651238，旧 unknown 仍照账，不重记 reasoning。真实摘要独审为7完整/1部分/2遗漏（关键4/7完整），4 claims 引文范围不足，混合 actual/planned 需修。原文10/10不能替代摘要忠实度。

实际请求暴露 reading_strategy 115003 字节，包含 matcher/UUID/未读诊断等程序信息；模型端应使用一个语义投影，公开完整上下文和来源身份保留。旧/新 prompt/generation 必须因果区分。随后同 run 恢复完成且0新增POST，但第三方 PDF 提示污染 JSON stdout，整体 runner FAIL；修 CLI 操作边界，不能在 harness 剥掉提示或把失败当模型失败。

RF main/origin main 已到 aed581ac（源512e85bb精确CI38563752875 success）；正常push416 PASS＋36子测试。reading_context 消费完整，定点同步两物理安装副本完成；旧 assurance/output WIP 保留。CWP 8f1c607b 与 d240871d 待本节点正常提交/推送，默认仍0.8。

## Next Step

ROOT 先收尾当前引用归属/恢复节点的跨仓联调与发布；三个 DU4 作者按各自独立卡开工。接收后执行 [DU4 总计划](parallel/du4-2026-10-15/README.md) 的生产接线及真实 holdout，不改默认或跳过质量验收。

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

## 7. 真实摘要暴露共因的下一施工窗口（2026-10-14）

这是 A/B/C 原节点的后续实施，不增加审批或小节点验收。DU3 QUALITY、DEPENDENCIES、GEOMETRY 已收，不再等待作者施工。先正常发布 `d9a13511` 工程节点，再开放下列不重叠写入窗口；未完成真实质量，正式默认保持 0.8。

### 7.1 并行边界与接口

| 责任人 | 独占写入范围 | 输入与交付 | 不重叠约束 |
|---|---|---|---|
| 输出预算线 | automation `store.py`、`narrative_run_store.py`，独立 `test_narrative_output_failure_finalization.py` | 已有有效 lease、实际 HandlerResult、同 connection；交付终态失败输出结清及 RED/GREEN 收据 | 不写 summarize/caller/batch/select/schema/config；不改收费或新建 Store |
| 可用片段线 | automation `narrative_select.py` 与必要 source-owned parsed-material 准则、排他 `test_narrative_partial_source_admission.py` | 已开原件＋已解析 units＋最终 package；交付统一格式无关准入与真实 handler/DAG 测试 | 不写预算/排序/模型/身份库/消费者；如需其他源文件先向 ROOT 报精确范围 |
| 类型根因线 | 先只读 route/QA/native parser 和已存材料 | 交付实际触发 unit、原文 SHA、候选/closure 原因、泛化反例与小范围 profiling 设计 | 此阶段不写代码；不得在集中测试时并行昂贵解析；不按文件名/manifest 标签强判 |
| ROOT 模型边界 | narrative_model/summarize/generation/batch/factory/verify/register 接线及排他模型测试；统一 PWF/Git | 同 pinned SelectResult＋frozen renderer；有限 None/v1/v2 派发与程序身份组装 | 不重写前三线文件；共享接口先在本节固定，完成工程节点后集中验证与推送 |

各线都只改 ROOT canonical checkout 的获分配文件；DU3 作者树、Dayu、IQS、其他 WIP 不动。没有其他 harness 要等待的交付。源代码和测试在正常 Git hooks 执行期间保持冻结；这属于写入协调，不是材料许可。

### 7.2 失败输出槽位结清：复用原 Store 事务

已证实失败摘要仍保留 2,097,152 bytes **额度**，不是实际新增文件或重复费用。唯一修复入口是 `AutomationStore.finish_attempt` 的现 active-lease 同事务；由 `NarrativeRunStore` 抽出已有 output settlement 的 connection 内核心并负责账务规则。只有 `source.narrative_summarize` 明确返回非 success、无 accepted artifact/effect 的**该 attempt**结清 `(output_bytes=0, output_sha256=null)`。成功/未决/丢失结果/旧 lease 不归零；reserved/unknown/known 的 tokens、cost、response SHA、错误与保守收费保持。

先 RED：known terminal / retryable 失败额度归零；unknown 费用不退；其他 attempt/job 和 success 保留；旧 lease/paused/expired 被原 fence 拒绝；正输出冲突不覆盖；注入 SQL 后异常证明 attempt/status/output 同时回滚；已提交但丢 ACK 不重复结清。不得在当前事务内开启另一个 Store 连接。历史回填不在首个补丁内，旧真实收据不改。

集中跑新增生命周期矩阵和受影响 store/run ownership/caller 测试，再在既有隔离失败摘要 CLI 收尾中断言额度已归零。0 真实模型；临时 DB、文件、sentinel 恢复。详细只读依据保存在 ROOT owned `post-model-ledger-readonly/implementation-brief.md`，接收节点归档到本 PWF。

### 7.3 来源可用性：有界片段、真实覆盖、前置材料证明

当前 PDF 的任何 errors/opaque 整份拒绝而 normalized carrier 跳过，是真实生产不一致；不能只删除条件或改标签。统一接受**可靠媒体里闭合、可回开且非空的片段**，保留真实 partial/unread/deferred 与 selected-excerpts 范围；只有完整空业务材料才可 `skipped_no_narrative`。全 opaque、空 incomplete、blocked、fatal media、真实原件或所选引用不符仍在模型前失败。模型返回坏引用已发生一次调用，必须照计 usage，不能伪报 0POST。

复用本轮已解析 units 和原有 replay 匹配，不重新 parse、逐 span 打开 PDF、复制全篇 MD 或再造 ranker。必要上下文不可靠由原 context graph withheld whole package；不在末端删引用伪闭合。选中片段内的材料验真与最终 verify 的原件再回开职责不同，身份/字节只在所属层执行，不要求模型复制 SHA。

先 RED：真实两页 PDF 一页可读/一页 opaque 贯穿 select→summary→verify；局部 text/table 异常与独立可读 prose；等价 HTML fragment；fatal/全 opaque/空 incomplete；跨源或篡改 locator/native-range；必需上下文缺失；partial 不能伪标 complete；完整纯财务 skip。至少一个真实注册 DAG 正例和两个前置负例观测模型次数。None/v1 固定输入的旧请求字节不变；源准入变化使用现 source 因果依赖进入新 generation，不重签历史 Ref。

### 7.4 模型只生成 claims：一个有限边界派发

模型不再回填程序已有的 source/subject ID、64位 SHA、language。下一内部 `reading-model-input/2` 返回 `{"draft":{"claims":[...]}}`，保留 claim_id、text、eN/gN、claim_type、modality。程序从**同一 pinned SelectResult**组装原 canonical header；official JSON 使用 subject SHA，各 immutable parent 的 role/group 保持独立。额外未消费 header 矛盾只作有限诊断，不覆盖 pinned 值，不作为许可阻断。

一个内部版本派发同时选择 renderer、schema、decoder、实际 prompt；generation、per-job prompt freeze、budget reservation、verify、reuse 消费相同决定。None 与 `/1` 的 instruction/data/input SHA/完整 HTTP body 原字节保留，显式 null/未知版本不暗降级；不得直接修改旧全局模板后重签旧 run。新模板/schema/decoder 的实际因果改变进入现 generation，不只改字符串标签。公众 DTO、任务库、算法选择 flag 和人工审查链不增加。

先冻旧 bytes 再 RED：仅 claims raw/official JSON；多回错 header不覆源身份；真实错误引用/角色/group 与 metadata 分开；新 prompt 真正进入 request/reservation/verify/reuse；旧 frozen unfinished run/default 变化仍使用原 renderer且0额外POST；strict JSON多括号/重复键/非法数拒绝并保留既有 final诊断和真实 usage。不得补 JSON 或自动换供应商重发。

当前 HTTP 已发 `response_format=json_object`，不能把“再次加同一参数”当修复。MiMo与DeepSeek官方文档支持 JSON mode；MiniMax-M3 的实际响应已反证该字段能保证 JSON，不用其他供应商文档宣称其能力。若需调整参数，只经现配置用途端口绑定真实选项，保留旧 wire/hash。

实际语言观察必须区分英文/西班牙语等同为拉丁脚本的正文；旧脚本计数器不满足。先用有界离线通用检测器做技术文本/品牌型号/短数字/英文改写/中文夹英文/mixed引用/第三语言反例，评估包体积、冷启动和不确定结果。只比较 claim prose 与实际 cited prose；短名/数字和未知结果明示诊断，不能默认英语或变成全面阻断。明确语言不匹配作为摘要质量问题处理，不翻译回去、发第二个 LLM 或用公司/西语关键词黑名单。是否采用依赖以真实试验决定，尚未实施。

候选试验已完成：py3langid0.4.0官方wheel校SHA，三独立进程108样本，24泛化四语经营段落和20实际西语claims标签正确；13个短Item标题与中文夹品牌的wuu标签证明不能每span语言身份硬核。安装4,723,249B，冷import/初始化0.928–1.070s，热调用中位0.249–0.302ms；模型原件0重解析、0LLM，临时9.3MB与失败收据保持/恢复。采用为有限离线观察器，固定依赖0.4.0、已有NumPy不重装；ROOT负责声明与安装/调用/因果指纹，观察器线仅独占新module/test。按实质claims与实际所引prose的标签和aggregate共识观察强整份第三语；短/混合/近缘汉语/不确定结果不作材料许可。normalized posterior不当准确率，原语言和事实质量仍需真实大节点独审。依赖首次进入正式环境为施工安装，不伪称测试Temp未增内容。

### 7.5 类型覆盖与真实质量收尾

已有20份 purposive样本：19份正式选择、HKIPO一次80s未完成；旧 timeout与原件保持。先确定 DEI 10-Q 为什么丢到 earnings_call、IR否定/原因到底在 admission/closure/rank 哪一层丢失；真实文件声明错不等于路由错。源 origin 与 speaker/attributed actor 的 role 含义先澄清，不能用unknown替换把gold凑绿。长招股先 profile 已定位工作，按共享parser责任修复，不抬上限重跑碰运气。

集中工程通过后沿同一账本再跑三家配置模型、各自独审关键业务/数字/角色/阶段/语言/自身引用和恢复；原三25/25、新三原分母11/12及普通分红边界继续展示。源可运行、quote召回、正式摘要、RF/买方模型分开报告。质量通过才切默认，并完成原计划并发2/4、缺真实类型、原三/新三及母研究循环；这些尚未完成，不以组件PASS关闭目标。

### 7.6 本窗口已证实的接线补漏与统一验收

- 来源可用性依赖必须按实际已解析units的parser责任冻结；电话会TXT/JSON与filing PDF使用同一既有matcher，HTML同时可能是transcript或normalized filing。`source-matcher-used`进入原决策trace，不能仅看MIME。后续84项纯材料/因果测试通过，3个需解析旧fixture只在该窄节点明确排除，正式集中节点照常运行；旧0.9缺该因果证明只失效重读一次，不改历史Ref。
- 每个model job的实际prompt由其generation负责；不得由请求容器/schema决定是否传给费用账。真实raw `/2`新代因缺map而误回run的1.7.0，调用前出现MODEL_RUN_BINDING_CONFLICT、0POST；新RED1FAIL/5PASS证实，按实际per-job差异冻结并在raw resume校验，旧None/v1 absent-map保持。87相关PASS；不放松ledger或重签旧run。
- 供应商模拟器只根据真实request schema派发：schema3返回claims-only，None/v1保留完整header。共用raw/official helper由ROOT维护，历史恢复test不各自再造协议。两个真实格式反例RED后6PASS。正式production E2E默认新代应明确断言`reading-model-input/2`、实际prompt/descriptor和source-owned canonical identity；None/v1另有冻结bytes及真正显式generation接口验收，不能仅改常量假造旧代。
- v2实际语言观察只作用于canonical claims的本条引用正文。明确different通过现post-model失败诊断保原metrics/终文SHA；uncertain/unavailable只投影现needs_review和有限静态日志，继续可消费，不是人工许可。新绑定RED5FAIL/3PASS后88相关PASS；observer组件67项含真实20西语样本。实际validator两模块、py3langid代码/权重与NumPy distribution因果绑定进同generation；缺模型资源/恢复必须改变identity，不能只信0.4.0标签。
- 工程集中测试和真实CLI期间冻结所有实际因果source，不只最初7个automation文件。一次旧恢复节点2PASS/2FAIL的paid-tail尚未通过，保存NO_CERT；更改实际causal source时不可把测试结果当稳定实现验收。ROOT明确宣布所有source STOP后只跑同一集中节点、真实跨仓loopback及必要counterexample，不新增每helper门禁。
- ROOT test runner使用workspace直属唯一短Temp、子进程TEMP/TMP和短`p` basetemp，finally恢复目录与sentinel/config。沙箱默认Temp拒写、深scratch导致WinError206分别保留，属于harness环境问题；短Temp后87PASS，不改生产代码或测试断言。正式验收还要原件SHA/mtime/大小不变，失效不表示可以丢原件。

以下真实类型诊断取代先前只读设计里的未证实假说：VRSK10-Q的9字符FORM行未进入有限probe，Revenues表格冒号被误识别speaker turn；万润IR的否定及母公司联系/希望合作已在完整m41身体，实际经营predicate得0而被过滤，并非QA closure或budget漏失。两原文/实际units/0LLM探针留证于ROOT type-matrix-root/root-cause-followup，后续按共享FORM证据与经营状态语法TDD，不加公司/产品/英文Revenue黑名单。HKIPO仍需有界phase/page profiling，不能把80秒失败说成已定位具体瓶颈。


### 7.7 下一实施窗口的文件归属与RED包（尚未实施）

真实三家摘要及独立审查先完成，ROOT保持同一源版本；随后才开放以下互不重叠的代码窗口。详细设计已定点保存于[FORM/发言人路由实施细则](review/source_form_route_implementation.md)及[经营状态准入实施细则](review/operating_state_admission_implementation.md)，只读18项/32项观察不能当作已运行TDD。

- FORM线负责一次HTML DOM读取时捕获真实可见FORM/DEI载体，走小型内部source-owned record→现有adapter→唯一router；探测仍200units/64000chars，载体先占既有限额。原因引用实际native ID/DOM；declared metadata不冒充observed；parent/child独立。转发kind/role/parent/turn后，真实发言成立才认call，财务表格冒号不是发言人。源码及A/B/C新RED包路径详见实施细则第6节。
- IR线只改现有shared business predicate及专属新tests/unit/test_reading_operating_states.py：真实经营否定、未商业化、暂停/未获认证、已接洽与仅希望合作分别保留；定义/行政/纯财务总计/泛泛愿望不得借OBJECT×ACTIVITY或legacy OR变成经营事实。32正反例＋12独立反例先RED，再走完整QA/source-role/actor/stage和不抬cap的生产选择集成。已完整m41的QA/closure/budget不重写。
- ROOT独占narrative_document的transient剔除、normalization/reading/pipeline胶水、版本和因果inventory、共享fixtures和生产E2E；不得两线同时改这些文件。旧0.8/None/v1 wire、Ref及原件保持。只做大节点集中审查、真实原件回放和正常发布，不增加小节点许可。
- HKIPO先有界phase/page profiling确认真正耗时，不能把80秒超时猜成几何问题或无条件提限。缺真实材料的类型明确NOT_EVALUATED；原回归样本不再称holdout。


### 7.8 三家真实失败后的共因施工（最高当前优先级）

1. **模型表示层**：新版本采用flat claims及唯一citation_unit_ids（旧/2保持），从当前pinned selection的完整groups和真实standalone spans编译有限、确定的引用单元；原文仍唯一存储、单元引用共享原文。禁止eN/gN双重声明、猜测相邻组、递归扩成整章；未知/外来/重复引用、路径、角色和真实缺证据继续由所属层处理。单元闭合是定位依据而非语义蕴含。先写跨样本错配/重叠/未知/空引用、raw+official、旧None/v1/2字节和新版本缓存的RED；实现文件分工以ROOT发给model线的明确窗口为准。schema默认、语言观察、manifest/factory/batch/verify统一由ROOT接，不在每个消费者再写版本分支。
2. **PDF重放端口**：source_catalog/narrative_evidence.py的path/bytes verifier显式language keyword（旧zh默认兼容），automation/narrative_replay.py/Protocol传canonical selected source language；不要删除native_range language一致性校验。专属tests/unit/test_narrative_pdf_language_replay.py先RED验证en/mixed、旧zh、错误language/原文/source/parser反例。已6FAIL/12PASS→18PASS、两源仅6行additive。真实HK旧typed selection/最终generation未留存，不能宣称恢复原paid job；用真实原件新建typed selection，逐项比较旧实际HTTP的eN正文/role/flags及gN成员，然后正常独立verify。最多一次有界初始parse及正常verify的一次parse；不再付费定位、不补造历史。表格诊断只能观察已有extract返回的slots/boxes，不增加find_tables/get_text/parse；保实际failed IDs/有限cause诊断。
3. **ROOT留证/整合**：failed-summary和failed-verify两类均在测试DB清理前保存原生select/summary/actualgeneration；先落费用再做留证，留证异常不得阻止finally清理。真实旧HK缺失明确保留，不补造历史。ROOT负责唯一generation选择、历史版本回放、公共fixtures和真实factory→Store→模型→verify→FF/RF集中E2E；不与两条源码线重叠。
4. **质量复验**：CN逐产品身份/阶段，HK表格列期间与双语逐引用，US分部层级/口径与原语言。25/25只是现quote oracle；HK7504精确目标与允许over7500的OR语义必须分开展示，不静默改gold。MiniMax公开兼容文档未声明response_format保证；不能把发了json_object当供应商必然强约束，也不临时换模型/端点/参数。优先简化协议并实测；仍不合格则明确provider能力边界，按配置设计有限替代，绝不修补坏JSON入库。
5. **逐条语言归属**：实际HK9条英文引用生成中文，其中7条独立strong different，旧整批结果被其他中文lane稀释为uncertain。复用既有一次分析及局部分类缓存，让strong local mismatch保留；短句本身不足仍abstain，不借另一条的来源替它判断。专属13例先6FAIL/7PASS，再与原73例集中86PASS；仅3条明确要求整批弃权的旧合同按逐条责任更新，其他70不放松，Ruff/mypy绿。真实保存HK原回复的纯观察从uncertain变different，短c2/c20仍uncertain；它们不是历史canonical恢复。下一集中节点验证真实summary/frozen validator/None-v1旧路径，表格期间错误尚未修复。

本节点只集中审查和测试，不新增逐材料授权、人工签收、canary或新的状态库。费用母账继续581487tokens/381768µUSD；后续新调用照累加，不重置。

### 7.9 集中联调暴露的事实支撑/上下文及恢复职责（当前优先）

[实施细则](review/citation_attribution_implementation.md)冻结context/2 citation_views、可选claim context引用、单一unit模型输出及跨仓消费责任。先RED再实施，保旧None/v1/v2字节；不把问答一律改uncertain或跳选另一个片段来凑绿。ROOT367例366PASS/1FAIL与真实旧manifest软件不可用proof保留。

真实HK已完成一次initial和一次正常独立verify：96/96、0模型、原材料逐项相同，来源语言mixed被正确传递；初次诊断Rect序列化故障后复用已保存typed selection，没有第二次initial parse。后续真实表格小包证实2024右列在原件里，旧选择只带merged-cell旧列及标题，是共享表格绑定/选择的未完成问题。具体原件与恢复限度按上述细则保留。

## §7.10 DU4 并行实施：固定接口与不重叠目录

2026-10-15 新增三个纯组件施工包，详见 [总调度与接收顺序](parallel/du4-2026-10-15/README.md)。TABLE/STATE/FORM 各自独占新源码包、单元测试包、作者 PWF；ROOT 接线既有 normalizer/router/selector/context，并做原件及正式摘要的大节点测试。组件全部可以立即开始，接口不依赖彼此或 ROOT 未提交的新 context/2。作者提交本分支后 STOP，不自行并 master/同步技能/写生产数据。
