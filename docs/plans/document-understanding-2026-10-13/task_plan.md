## ROOT 当前状态 — 2026-10-15 真实摘要与发布收尾

**已发布：** CWP `0b61bcd1` 正常pre-push **5642PASS/24SKIP（518.41秒）**，精确CI **38788268113 SUCCESS**；RF `caf74c5f` 精确CI **38784099830 SUCCESS**。首次push的6项失败、所属职责修复与全部旧失败收据保留，未绕过hooks。工程发布见 [发布收据](common-root-quality-evidence/attribution-publication.json)。前述146单元/契约、7正式E2E、6历史恢复、110+20独审及74配置范围节点仍有效，数字有重叠不合计。

**真实质量仍未过：** 中微2026半年报按实际MiMo `mimo-v2.6-flash` 配置运行，新0.9一次POST完成、96/96原文回放、same/cross-run 0额外POST。独审20条为 **8PASS/6WARN/6FAIL**，20/20引用展开与canonical保持，排除decoder错配；6条正文使用了selected输入中有、但本claim实际未引用的数字/产品/阶段。不能把原文定位绿写成事实语义绿，也不应把这些全部说成外部捏造。若干新业务被摘要遗漏；WARN不全部等于数字错误或必须逐动词拆句。见 [真实材料、费用和独审](common-root-quality-evidence/cn-h1-citation-unit3-live-acceptance.json) 和 [共因整改细则](review/summary_grounding_implementation.md)。原付费输入/终文/bundle不改、不盲目重发。

**对照的测试适配故障：** 旧0.8尚未POST，observer将旧原文顺序组误当新selection顺序组。纯反例RED 1FAIL/16PASS；仅测试observer沿唯一quote oracle评估每个真实旧组，原新context/native order规则和旧HTTP字节不改，30PASS/3.62秒，临时测试目录恢复。整组FAIL与旧前置失败保留，不据此宣称产品旧解析缺陷或baseline通过。

**长招股书性能根因：** 一次60秒真实profile证实：675页文字4.292秒已读完，230页只是表格候选计划，133次已完成native找表耗时50.163秒；后段已有文字被逐页昂贵table emit拖住。layout15秒不限制find_tables。独立只读架构调查16文件保持，分 B0文字可用/有界native、B1单次prepare/finalize按需增强、B2同AUTO完成单元恢复/容量、C原样本+另一长文档真实验收；这些实现尚未完成。见 [详细接口与TDD](review/hk_ipo_parser_performance_implementation.md)。不增加全MD/PDF副本、第二队列或每页重复传整份原件。

**并行边界：** 用户确认三条DU4均IN_PROGRESS：[调度与工作目录](parallel/du4-2026-10-15/README.md)。ROOT不改作者新组件/测试/独立PWF；只在既有parser/共享引擎、模型、恢复与主计划施工，最终由ROOT接线。

**预算：** 本次实际18103tokens/3345µUSD预算代理；母累计 **599590tokens/385113µUSD代理**，旧unknown7保留，上限200万tokens/$20。原件、生产配置、sentinel保持，真实独立临时湖删除。金额不是供应商账单。

**未完成范围：** 默认仍0.8；正式摘要语义共因、DU4接线、HKIPO分阶段恢复、三配置供应商新旧质量、并发2/4、默认切换、母G2/G4/G5及原三/新三研究审计循环均继续开放。

**Next Step：** 将真实错引/跨产品/期间/单位/QA反例固化为ROOT零付费回归并在同一模型/共享结构边界整改；随后实施不与DU4重叠的HKIPO B0/B1/B2。仅原A/B/C和母G节点集中验收，不新增小节点签收。

---

## 上一工程节点记录 — 2026-10-15（历史，发布状态以顶部为准）

引用归属/恢复共因节点e1b3e234已正常提交；首次正常push由6项兼容问题拒绝（5610PASS/24SKIP），已按真实职责修复并88集中PASS，准备连同用途范围配置节点正常补交/重推。新显式0.9使用单一citation-unit/3，完整原文只发一份；原生QA的回答支撑与提问上下文分别传递，程序恢复canonical ID，不让模型回填来源。context/2和可选claim context字段由既有RF消费者接收，旧None/v1/v2请求字节与已存Ref保持。PDF重放传真实源语言；语言观察逐claim比较自己的事实支撑，避免其他中文段落掩盖英文被翻译。

实际验收：ROOT 146单元/契约、7正式生产E2E、6历史恢复E2E通过；独立审查另跑110单元及20纯反例，无阻断发现。各测试集可能重叠，不相加冒充唯一覆盖数。真实旧5a源码生成activation_pending，由新代码正常恢复，额外模型POST=0，费用/attempt保持；输出结算三字段正常变成真实已发布字节/SHA。新的FF→CWP→RF完整离线CLI PASS；另有原生QA→正式选择/模型/验证/发布→公共compact /3→RF真实CLI PASS，管理层支撑/投资者问题上下文和完整正文逐字段保持。静态Ruff/mypy通过。

新测试全部为隔离loopback，0供应商、母账不变；配置/原件/sentinel保持，临时目录清理。真实HK source-only重放96/96另有收据；旧付费HK的typed snapshot缺失仍NOT_RETAINED，不用新重放冒充旧任务恢复。初始配置快照选错、探针夹具/版本/summary路径错误、13E2E合并超时、mypy及sandbox失败均保留，在所属测试工具修复，未放宽产品断言。详见[验收收据](common-root-quality-evidence/source-attribution-recovery-acceptance.json)和[123份紧凑证据](common-root-quality-evidence/source-attribution-recovery-receipts.zip)。

RF消费者代码caf74c5f已正常推送，416+36subtests通过，精确CI38784099830 SUCCESS；两份物理安装副本只定点同步一个脚本。DU4卡/PWF4f065af2已推远端，用户确认三个作者包均已开工，目录独立IN_PROGRESS；ROOT不写它们的新组件/测试/PWF。[DU4总调度](parallel/du4-2026-10-15/README.md)与[固定接口](parallel/du4-2026-10-15/INTERFACES.md)有效，只有A/B/C大节点。

用途范围配置共因也已TDD完成：统一loader/builder先选择真实profile，llm范围不消费无关search/wiki/schedule/downloader或未选fallback；实际key/参数仍严格，不靠pytest宽松。25新反例与旧配置/模型/purpose共74PASS，真实CLI缺搜索配置/旧路径且无测试宽松变量的摘要+0POST恢复E2E PASS，官方JSON问答另PASS。独审最初找到两处残耦合，修复后5个原fallback形状和4个profile控制均通过。见[范围/兼容收尾](common-root-quality-evidence/scoped-config-recovery-acceptance.json)及[紧凑证据](common-root-quality-evidence/scoped-config-recovery-receipts.zip)。

**仍未完成：** DU4表格期间/选择、经营状态、真实FORM/turn信号及ROOT接线；HKIPO有界性能；三配置供应商正式摘要新旧质量、并发2/4、默认切换、母G2/G4/G5和原三/新三公司研究审计循环。默认仍0.8；工程通过不等于正式摘要或买方研究通过。累计581487 tokens /381768µUSD代理（旧unknown7保留），上限$20/200万tokens，本节点新增供应商消耗0。

Next Step：正常发布本次CWP/RF工程节点并核精确CI；随后处理不与DU4重叠的HKIPO有界性能/真实验收准备。接收DU4后统一接线并重新跑真实摘要质量，保留失败和原分母。

以下为历史冻结记录；若与本节状态不同，以本节为准。

## ROOT 当前接收与真实质量整改 — 2026-10-14

19:47实际更新：原三portfolio6回放25/25，新三11/12（SMIC4/5、ANTA3/3、Apple4/4），各自一次parse/select，原件/金标不改。普通分红提案属于资本分配而非强制业务召回，原12项分母/FAIL继续展示，不能静默改gold。新配置完整离线CWP→FF→RF CLI PASS。用途配置82PASS。

MiMo按已配置disabled第二次真实试验：input13626/output2103/reasoning0，transport完成但SUMMARY_INVALID，1POST已记15729tokens/2973µUSD；累计518327tokens/356737µUSD含FX。原件/sentinel保持、Temp移除，未执行旧0.8的后续支付，也不盲重发。尚不能猜具体违反规则：当前_summary_failure丢失了完整返回的有界诊断与下游失败原因。**优先补齐统一post-model失败诊断**：复用FailedFinalDiagnostic与现attempt/usage/handler result，给所有付费后decode/citation/contract失败保留具体规则、原metrics及最多16KiB UTF8终文前缀/hash，不接受失败摘要、不改guard、不建第二产物库；invalid/oversize/path异常各自负控，零付费先验证，随后才重新真实运行。失败回复与transport截断统一在所属摘要边界可查，不以不断重发找原因。

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

# 共享引擎＋多份文档阅读策略 — ROOT统一执行PWF

PLAN_ID: document-understanding-2026-10-13
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/company-wiki/docs/plans
Owner: ROOT
Current Phase: A/B/C — DU3已实收；真实泛化与正式摘要共同根因整改中

## Goal

完成一个共享文档阅读引擎与多份市场/文档/业务策略，并接入正式资料处理、原语言摘要和缓存。与母PWF共用G2/G4/G5真实验证；不另建引擎、任务库、全篇MD副本、权限或人工签收链。原件保留，IO/身份/预算各由负责层执行。

此表是唯一当前执行状态；详细施工见 [completion_implementation.md](completion_implementation.md)。旧DU/DU2接收已关闭，旧卡和阶段文字只供历史/设计参考，不再等待交付或重发同卡。改前先读本表、findings、progress及所做节点细则。

## 已完成基础

- [complete] 20原件调查、设计与DU/1接口、原三包和独立接收整改。三仓本轮架构质量改造已发布。
- [complete] DU2三最新作者＋ROOT整合：一个运行catalog含24文档规格/14业务策略；层级/实际范围、原文闭包、字体/粗几何和有界布局实际消费。
- [complete] 联合1135 PASS，四PDF658原文span验真，真实10-Q六项PASS，独审共同根因关闭；原件/配置/测试环境保持。
- [complete] 源码deb7eb7d并master并推送，CI38476678472 success；正常pre-push4175 PASS/17 SKIP。收尾9e4faf2a已推送，ROOT整合树/临时材料已归档回收，作者bindings保持。

## 剩余阶段（仅三大节点）

### Phase A: 生产选择与唯一材料

**Status:** in_progress

统一ReadingPlan进入既有candidate/finalize/budget流程，业务价值/主题多样性/新信息和完整闭合边际成本共同决定选择。根治旧活跃题材/固定4–9个月优待，不能仅改排序或提高cap。共享上下文唯一材料＋组引用，复用生产eN/gN形式。先写行为RED，集中实现并跑A受影响测试。

责任范围：source_catalog的候选/预算/最终选择；document_understanding的选择桥/摘要组装。旧版本仅供必要回放，新默认在C达标后切换。

### Phase B: 正式摘要、generation与缓存恢复

**Status:** in_progress（引用归属/语言/阶段恢复共因工程已验收；真实供应商质量与默认切换仍待完成）

同一次parser→DU→正式SelectResult→ModelRequest→NarrativeRef，只有最终实际采用提示进入模型。selection-decision指纹与final-sent-policy指纹分开；未选但参与决策的策略变化也失效，无关策略不全库重建。

采用base归属→正式select一次→final generation CAS→模型任务顺序，复用原AUTO/Store/outbox与计费。production factory/loopback、相关/无关变更0POST、取消/丢ACK/重启、旧ref回放和消费者在一次集中工程E2E节点验收，独立复核后正常发布。不新建canary或人工许可。

### Phase C: 真实质量、泛化、默认切换和清理

**Status:** in_progress（实际供应商摘要已执行，质量尚未通过）

同原件同范围同预算旧/新比较，精确使用配置的MiMo/DeepSeek/MiniMax和原累计账$20/200万token；与母G2真实摘要、G4原三公司、G5新A/H/US三公司共用一个验证窗口。包含文档类型覆盖、关键业务gold、原文回开、数字/角色/阶段、空间/时间/并发观察。

细分栏/细表不足及缺样诚实记录；关键经营信息漏读不能用partial标签放行。达标后一次切正式默认、清理被替代运行逻辑和自有scratch，保留历史ref回放、原件及必要usage，正常并线/推送/精确CI与技能定点同步。

## 当前节点 — 2026-10-14 真实摘要之后

三 DU3 已交付。QUALITY dcde9aae 与 GEOMETRY a8cc604d 的全部改动已收到；DEPENDENCIES ef59a574 的补交 282aee36/ef59a574 已实收暂存，ROOT 138 PASS。它们修复同一依赖文件被重复扣字节预算的问题；完整 cache 仍由正式 AUTO 链验收。ROOT 未修改三个作者工作树。

本节点源码：business-policy/4 具名分部归属 161 PASS；唯一 operating-table-purpose/2 按实际经营行筛选、保留建设期/混合表经营行 286 PASS；其版本已进入决策依赖，因果测试 41 PASS；冻结代默认升级恢复 9 PASS（真实 selector 0.8→0.9 与 PDF parser 0.1.0→0.1.1）。旧升级测试实际未运行 bootstrap 的问题已纠正，不把基线失败直接当可删的断言。全部零真实 POST，独立临时目录与配置/原件约束保持。

真实开发回归原文选择 CN 10/10、HK 7/7、US 8/8；换公司开发泛化 SMIC 3/5、ANTA 0/3、Apple 2/4，共 5/12。它们不是未见 holdout；不修改 gold 或隐藏范围边界来提高分数。HK 实际路由是 hkex/annual，不能凭市场 metadata 猜错路由；简繁 matching、品牌/股东关系及混合经营指标仍需根因整改。两次只读 observer 的后置测试工具故障保留，不能签为真实 window 观测通过。

第一次实际配置 MiMo 摘要已生成、公开回开 verified、96 spans，67004 tokens（输入64804/输出2200），预算代理费用11535µUSD，非发票。母累计480782 tokens/已知345998µUSD＋FX hold2764；剩余1519218 tokens/$19.651238，旧 unknown 仍照账，不重记 reasoning。真实摘要独审为7完整/1部分/2遗漏（关键4/7完整），4 claims 引文范围不足，混合 actual/planned 需修。原文10/10不能替代摘要忠实度。

实际请求暴露 reading_strategy 115003 字节，包含 matcher/UUID/未读诊断等程序信息；模型端应使用一个语义投影，公开完整上下文和来源身份保留。旧/新 prompt/generation 必须因果区分。随后同 run 恢复完成且0新增POST，但第三方 PDF 提示污染 JSON stdout，整体 runner FAIL；修 CLI 操作边界，不能在 harness 剥掉提示或把失败当模型失败。

RF main/origin main 已到 aed581ac（源512e85bb精确CI38563752875 success）；正常push416 PASS＋36子测试。reading_context 消费完整，定点同步两物理安装副本完成；旧 assurance/output WIP 保留。CWP 8f1c607b 与 d240871d 待本节点正常提交/推送，默认仍0.8。

## Next Step

ROOT 先收尾当前引用归属/恢复节点的跨仓联调与发布；三个 DU4 作者按各自独立卡开工。接收后执行 [DU4 总计划](parallel/du4-2026-10-15/README.md) 的生产接线及真实 holdout，不改默认或跳过质量验收。

## DU3 并行交付（已收到，不重发）

[DU3三卡总览与工作目录](parallel/du3-2026-10-14/README.md)。QUALITY仅拥有tools/document_understanding_benchmark；DEPENDENCIES仅拥有新decision_dependencies子包；GEOMETRY仅拥有新layout_snapshots子包，各自另有排他tests/ledger、独立稀疏worktree。ROOT保留source_catalog候选/预算/finalize、DU选择/summary与automation正式接线，三线不写这些共享目录、不重开旧DU/DU2卡。

三卡已由用户分发，接口冻结DU3/1，ROOT不写作者工作目录。2026-10-14最新盘点三树干净：GEOMETRY接收为7e023a15/c6224a1a/ef69957a（ROOT89PASS/13SKIP）；QUALITY接收为016e3b4a/9f1a27bd/a8686990/804dfbb7（ROOT217PASS/7SKIP）；DEPENDENCIES接收完整六commit为c79e0c13/e5ad62af/f86aea25/7fd2f117/8a4e4cc4/d6e91356，含两轮独审根因修复。ROOT完整trace/current重建、实际0POST缓存与恢复仍须验证；这些组件PASS不代替生产PASS。A/B/C只作三个大节点，真实模型与跨仓共用母窗口。

## 完成标准与注意事项

- A/B/C全部有真实证据，正式默认启用且发布后才关闭共享阅读升级。母研究循环按原计划继续，不将模块PASS当经济研究PASS。
- 旧微软关键业务baseline4/8 FAIL保持；真实/合成/不可评分别报告，不降gold或删失败收据。
- 生产HTTP原已unique evidence rows；重复正文在DU中间package视图。接线复用既有传输，不能误修正确的HTTP机制。
- 原件与生产配置不写穿；测试独立tmp/sentinel/owned清单，成功/失败都恢复。Dayu/IQS和他人WIP不动。
- ROOT统一共有接口/状态/Git。旧DU/DU2作者卡已完成，不自动重派；DU3按上节最新状态接收，未来分包需排他目录与冻结接口。
- 既有静态/快速hooks正常执行；只在A/B/C大节点做集中复核，不新增小节点门禁。

## 依据和历史

[已发布DU2验收](du2-reception/acceptance.md)、[发布收据](du2-reception/evidence/publication.json)、[旧DU验收](reception/acceptance.md)、[设计](design.md)、[接口](INTERFACES.md)、[旧细则](review/root_implementation.md)、[母跨市场PWF](../cross-market-rf-e2e-2026-10-08/task_plan.md)。原ROOT阶段表保留在Git 9e4faf2a；本表已合并其完成事实与全部剩余任务，历史不再作为当前指令。

## Phase A预算组件节点

纯planner104集中PASS/38独立probe PASS，mypy/ruff通过；原RED、环境失败、测试fixture纠正及独审中间失败留证：[小归档](phase-a-budget-evidence/receipts.zip)/[组件收据](phase-a-budget-evidence/acceptance.json)。只签纯planner，生产ReadingPlan/候选/最终模型输入仍待接线；旧默认与原件/配置保持，0付费。

## 当前 ROOT 实施记录 — 2026-10-14

- 0.9.0新路径实际运行共享understand_units→候选/闭包→既有reading_plan/1→canonical EvidenceSpan。旧题材/4–9月规则只留历史版本。明确anchor身份、被拒包deferred、结构工作停止已修；21边界反例通过（另20K效率反例正在修）。不同原件同locator+同文本保留各自source身份，结构按parent隔离、全局共同竞争预算。
- 正式SelectResult→ModelRequest→Bundle保留紧凑策略；真实48K共享上下文只发一次且双组独立。30新传输测试/246相关集中通过；后续ROOT加bounded deferred全count、选择诊断与可选decision依赖，需统一复验。
- AUTO schema6只增既有run_jobs的nullable final_generation_json；select成功与final CAS同lease事务。实际model有效配置核对、reservation前final-ready、动态runtime resolver已接。143 Store/migration/factory相关通过。
- 新HTML/PDF/TXT正式CLI+子进程E2E和付费后待activation恢复4PASS/65.91s；loopback0真实供应商调用，原件/config/临时目录恢复。same-run0POST，缺完整decision trace跨run不能冒充缓存命中。
- 独审发现20K候选扫描耗尽预算、deferred逾1MiB，及真实HK多行经营表漏读；分别改planner索引/工作计费/有限样本＋全量计数与通用多行header结构。旧失败收据保留，不提高限额或降低gold。真实供应商/质量泛化/default切换未完成。
- 三DU3工作树只读核对仍在195aba20基线，无新commit；ROOT未修改它们owned路径。当前ROOT可选dependency hook缺模块会明确诊断，允许摘要但不允许新缓存有效复用，不重写外包freezer。

## 2026-10-14 生产接线工程节点

实现d3c57b31和夹具修复fc2a4513已正常推master；正常pre-push4379PASS/17SKIP/381.75s，精确[CI38540579403](https://github.com/zhengcb81/company-wiki/actions/runs/38540579403) success。[发布收据](production-wiring-evidence/publication.json)。原3个旧schema夹具失败保留在[修复记录](production-wiring-evidence/push-repair.json)，未跳hooks。

[节点收据](production-wiring-evidence/acceptance.json) / [紧凑原始证据](production-wiring-evidence/receipts.zip)。正式public request显式0.9、唯一原文/策略摘要、same-run/outbox/真实v5升级、原件篡改拒绝已验。集中1149 PASS/17 SKIP/3旧factory失败后，只复跑受影响51（50PASS/1新test参数失配）及最后18PASS；全部已知工程失败关闭，原FAIL保留。新7E2E：集中6PASS，1计数观察点过时，改为统一真实byte owner后1PASS；旧11E2E全PASS。没有反复重跑千项套件或降低断言。

**A/B/C仍未全部完成：** 真实跨run缓存等待DU3依赖组件；同原件旧/新三市场native回放更快但不是摘要质量通过。实际微软8条required_business仅1/8在新选择中保留（旧4/8），三层共因已实证，不是拆句误报。新默认不能启用；下一批先通用RED再修，不在生产加公司词/样本特判。unknown语言准备仍有一次重复读，作为同责任层性能收尾，不新增审批。
