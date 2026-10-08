# S7 后续质量整改实施单（2026-10-07）

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

## 恢复点与边界

当前MAIN代码c1295b1/CI37552600440全绿75秒，selector0.4.1、parser0.1.1；真实九文档27/33、761定位0失败。N6历史基线e8c645e/selector0.4.0/parser0.1.0为21/33，经营节点9bf25a5提高到27/33；原86点/33分母不变。RF main6e6b817a，daily/weekly/manifest三owner日志与CWP用户source_acquisition.yaml只读保护。上轮是实质进展，不是等待。

本单只推进资料质量，不写投资研究状态，不跨写RF/StockWiki/IQS/ET/Dayu，不调用供应商或下载。96/160与空间限额不扩大；原件不可变。已有N6三卡不重派。逐helper没有人工签收或全表长测试。

## 实施顺序

1. **先定位9个业务差距。** 读取原samples/golden，限定同一原件的声明已读表页，捕获既有finalize_selection输入，再按parsed→candidate→deduplicated→selected核相同quote/locator。结果明确诊断口径，不能当生产/default/full-table覆盖。保存≤2MiB小报告，包含源/原件SHA、阶段、被省原因、组成本/理由和少量必要片段；不存整份转换正文。先后核原件及配置/owner指纹，自己的tmp脚本删除恢复absent。
2. **修选择责任层。** 根据实证区分识别、句子补全、分组、语义分类和预算淘汰。先写跨公司一般表达的RED（行业规模预测、已应用/批量销售、并购方案/收购完成、募投用途与新增产能），再修改责任函数；纯损益数字、融资总额、法律套话、无动作描述保持负例。情态只保留原文，不把预测/计划改成已实现。预算稀有业务类别不能因已有generic event而失去语义，原始span与定位不重造。新算法实际发布时统一selector版本；不复用旧批次。
3. **再修IR解析单元。** 现S08一个219字orphan cell包含4/5编号问答和接待套话。先测试数字编号、问题/答案role与QA关联、跨cell继续、字符范围和原cell hash；拆分应绑定原cell真实范围并可回放。保留0.1.0旧final读取，不静默改变旧parser行为；确需新parser/version时先列完整生产reader/Worker/回放版本传播接口，再集中实现与兼容测试。不能删整条占比事实或关闭噪声测量。
4. **一个集中发布节点。** 短责任测试与Ruff/mypy；真实受影响的年报、募投/可转债、IR从正式SourceVersionReader/Worker/outbox→final→search/exact/RF→恢复（独立短tmp，确定性loopback profile、0供应商费用）。真实定位回放/身份/原语言/原件保护仍须满足，旧final与AUTO新旧generation按影响验证。修完一组后再跑全九样本一次核必需业务旧full无退步和新缺口，optional取舍逐项按资料价值解释，不能隐藏，不每次小修改跑六分钟全表。正常commit/push，核精确代码CI；最后小收据和三份总PWF推送。

## 当前9个目标点

| 目标 | 需保留的资料语义 |
|---|---|
| S01 G01 | 全球先进产线已应用与海外批量销售 |
| S01 G03 | 拟议收购与干法向湿法业务扩展，不删计划词 |
| S01 G05 | 行业装备规模与增速的来源预测 |
| S02 G02 | 行业规模增长预测 |
| S02 G03 | 国内外先进客户采用和批量订单 |
| S04 G03 | 募投引导句须与同页紧邻具体项目组合，不单独摘要 |
| S06 G02/G03 | 募投具体生产线用途、达产条件及新增产品产能 |
| S06 G04 | 历史进口替代趋势及原期间，不改成最新事实 |

原required另有纯金额G-S06-01、正文外provider G-S09-01、纯guidance G-S09-03未命中，保留原分母并按业务边界解释；G-S09-04伴随原句入选不算额外业务增益。三噪声G-S01-11、G-S08-05/06继续测量。

## 完成记录接口

使用`s7-followup-quality-node/1`小JSON，记录base/实现SHA、8+实际源模块SHA、selector/parser版本、每点各阶段和解释、RED/GREEN命令/结果、完整benchmark路径与对照、实际E2E是否fixture/资料类型、old-final/generation验证、0供应商/下载/费用、保护指纹和tmp恢复、提交/推送/精确CI。未完成点仍列remaining，不借范围说明删业务点。总task_plan引用本单，progress按实证追加，findings记录责任归因。

## 状态

阶段1/2经营节点9bf25a5已发布；阶段3 IR parser0.1.1节点c1295b1已发布、精确CI37552600440全绿75秒。剩余仅S01应用事实预算与S04具体项目上下文，按总计划Next Step处理。S04实际PDF项目表被抽取到法律段落之后，不能按文本索引的“紧邻”草率拼接，须以同页视觉位置/表结构联系再设计；不以笼统提高关键词权重或扩配额代替实证。

### 分层诊断后的具体设计

- 应用/批量销售、并购、明确募投生产线、达产后的物理新增量和量化行业前景使用具体reason并参与现有类别公平预算；保留既有generic reason及原情态。base-eligible不应丢弃新具体reason，已有span ID/locator不变；算法发布升selector0.4.1。
- S01行业预测需识别“行业/全球/市场+销售额/规模+将达/提高至+数字”的一般表达，不将公司纯营收guidance或资金总额变行业事实。
- S06进口趋势p11/p12属于一条未完句，两个相邻fact窗口只有在源/parser/role/language/discourse相同且前段没有句末标点时才合组；完整相邻两句不合、8单位/1600字符继续有界。
- S06新增产能G03已存在同原件另一个canonical locator，原page43标准仍计miss；不为命中率回退去重。单独记录原句实际存在及可回放映射，与正式benchmark分开。
- S04募投引导句只有与同页紧邻具体项目内容成组才可选，不能提升孤立引导句；仍需真实表/text字段探针决定具体拼接接口。

### 2026-10-07 本次集中实现与测试

1. 初次语义7个真实RED/4通过（夹具metadata修正后），修补已应用/批量销售、并购、具体募投、物理产能和量化行业预测reason；generic eligibility不丢具体reason。随后280责任项绿。
2. 未完句窗口先8个签名RED；加兼容参数后明确1产品RED/18通过，实施仅源/parser/role/language/discourse一致、前句未结束的相邻窗口有界合组。英文句号也是终止。完整相邻两句不合；8单位/1600字不扩。66相关责任项绿。
3. 量化进口趋势识别及量化事实不被泛行业背景挤掉两个RED，新增quantified_industry_change及quantified_industry类别，保留历史期间和原情态。290全相关责任项3.23秒、Ruff全CI范围/4模块mypy绿；旧断言/原golden不改。最后发布前继续8模块mypy与集中E2E/全九文档。
4. 新增独立opt-in `tests/integration/test_s7_operating_business_cli_e2e.py`，真实S01年报、S02半年报、S06可转债通过正式配置Worker/outbox→CWP/RF→search/exact→同run恢复；实际7个业务quote断言，原件字节真实，身份元数据仍隔离Acme夹具。既有S01/S07/S09四个业务点、冻结0.3.2 finals9和实际AUTO升级1继续保留。两组本地loopback6 POST，零供应商/下载，不声称模型事实质量。运行完成后记录实际结果，不计skip为通过。

### 真实默认解析暴露的问题与修正

首轮新S7真实E2E1失败、旧节点/兼容/升级11通过，总149.92秒：G-S01-03在默认表扫描仍miss。只读默认年报23.338秒诊断发现，3个被当成具体corporate_development的组其实是未来并购策略/整合风险，真正购买控股权被预算挤掉。增加三条泛策略/风险负例（2真实RED/1原已通过），计划交易只有动作及公司/企业/股权/资产对象时获得具体reason；generic策略仍保留旧project reason。49相关项0.77秒绿，最终293责任项3.60秒、全范围Ruff/8模块mypy绿。

第二轮只复验新节点83.28秒：具体购买计划断言已通过，失败在测试误用“收购”作词面查询；原quote写“购买”。现检索是原文关键词接口，不是同义改写接口，所以将夹具改为原字“购买”，加每个query确实存在所选原句的前置断言和失败sample/query上下文；全部7个quote、SHA/身份/定位/恢复断言保持。原33点/golden与产品检索实现未改。当前复验和最终全九报告以完成后的收据为准，不把这两个失败隐去。

最终新S7节点1通过/97.74秒，正式三文档7点、RF真实读取、search/exact和同run恢复全通过。全九唯一最终运行436.885秒：27/33（原21/33），optional3/17（原5/17）、764定位/0失败、重复4（原3）、精选66215B（原66195B）、scratch60374B。必需旧full无回退；两optional回退是静态海外销售主体职责和项目营收/利润预测，均不作为业务动态优先选择的硬门，仍保存原标注与结果，不声称全部旧full无回退。没有改产品测试/原golden或掩盖回退；一个对所有positive一刀切的收据断言首次检出这两点，MAIN按用户的资料目标和放松无用门禁要求作此具体判断，不能泛化放宽重要业务或SHA定位。新报告/收据并存、原件仍在，可按需读原文。

## IR parser 0.1.1 施工接口（已完成；独立于0.4.1节点发布）

真实S08三页只读核查：page3/table0/row0/column1的219字符cell从“答：黄金产品”开始，随后出现“4：…？/答：…”和“5：…？/答：…”，末尾混有参阅记录及法律套话。旧parser0.1.0把整个cell变为一条orphan_answer；cell SHA `c9e79342dc3ddca67c9cf0c0b397fa46c5012a9f520af5ffa31f1482cddcb048`，完整offset0—219。旧parser行为必须可重放，不能直接改常量所标版本却不分派逻辑。

### 写集与版本传播

- 解析只改CWP `narrative_evidence.py`的QA helper/emit入口及必要的独立QA模块；不改RF/ET或来源合同。parser新默认0.1.1，明确0.1.0仍走原有QA marker/整答案逻辑。0.4.1本次发布后再做下一节点，不能与正在跑的基准混用源码。
- `_pdf_qa_parts`收到state.parser_version；`_emit_pdf_row`传入此pin。QA页/shadow识别及`_table_scan_signal`涉及数字标记时同样接收解析pin，老0.1.0扫描规则不被静默改变。`_parse_pdf_document`的state pin进入这些入口。
- `parse_pdf`/`parse_pdf_bytes`显式parser_version继续支持旧pin；`verify_pdf_evidence_spans(_bytes)`从旧span读pin经PdfReplayPlan重解析，不用当前默认覆盖。SourceVersionReader仍负责原字节SHA；不加权限文件。
- `automation.narrative_select`与VersionPins从统一常量取新默认，新parser进入既有AUTO generation/工作键；旧artifact由NarrativeTransportReader原样读取、旧selector/旧parser回放。不要另建任务库或改变外部v2接口。

### 新QA片段规则

1. 旧“问：/问题：/1、问：”保持；新数字“4：/5：”只能在行开头且具有可判别问题/答标记联系时认定，年、时间、比率、编号项目行不能被当成提问。数字问题跨cell没有答时若是明确问句，保留question_unanswered供现linker配对；不能凭同数字跨公司/页任意挂接。
2. 答案按原cell中可回放句子拆分；每个fragment的start/end是原cell绝对字符范围，必须`cell[start:end]`等于fragment text（以统一trim策略处理空白），保留整个cell SHA、片段SHA、QA group/number/state/role。不在片段内改写原文、删“预计/尚未/计划”等词，不把外来正文作为指令。
3. 含业务事实的一句继续被选；“参阅前次活动记录”及披露制度句各为独立片段，自身没有业务事实就不入选。问题关联只挂到实际被选答案，不把同问答所有剩余套话再带回组。跨页question/answer continuations沿现linker关联，不能新造第二关联库。
4. 同一cell中的新片段仍用现page/table/row/column locator及完整range/hash重放；不要把统一page/row当作跨片段同一证据。验证篡改range、cell SHA、role、parser pin时定位验证失败；这属于字节真实性测试，不是人工审查门。

### 一次集中验收，不加小节点门

- 先RED：numeric4/5与旧markers、完整和断行问题、答案中两句事实/尾部套话、无答/跨cell continuation、日期/比率/编号项目负例、相同原文不同QA/角色隔离；原cell精确范围正反例。
- 单元/集成：新0.1.1实际cell split→selector保留占比、排除套话；旧0.1.0同cell输出保持完整219字符orphan；旧published/frozen final ID/字节/hash及旧pin回放不变；AUTO升级使用不同generation且resume不重复模型调用。
- 大节点真实E2E：原S07+S08两类IR经过正式Worker/outbox、原语言final、RF正式读取、search/exact及resume；模拟模型零供应商费用；S08产品结构事实仍full，套话不靠删整cell避测。S01/S02/S06和TXT已通过业务节点的合同不因parser升级失效，按明确影响选短复验。
- 最后全九报告一次，原golden/33分母不改；记录新旧parser的定位数、role confusion、两条S08噪声与所有原full回退。原件/配置/RF owner SHA不变，独立测试根恢复absent。正常commit/push核精确CI，日常CI不加入全九/真实长E2E。


## 本节点实际发布

代码9bf25a5f4d7339d24ed75661a22036f1e7068eb9已推master，精确CI37550268890 attempt1全部step/job成功、job112563794701/71秒。正常commit/pre-push绿，14个本次tmp路径恢复absent，原件/用户配置/RF owner与运行源码指纹保持。收据s7_operating_main_acceptance_2026-10-07.json状态published_exact_ci_passed。上文等待/准备状态已被本节完成事实覆盖；下节点IR0.1.1仍未实施，S7总目标继续in_progress。

## 2026-10-07 IR0.1.1实际实施（覆盖前述尚未开始）

当前新默认parser0.1.1/selector仍0.4.1；明确0.1.0走全部原QA解析/ID/关联/回放逻辑。新模块负责marker与精确trim范围，_make_unit新pin QA身份加范围/role，现linker按source/parser/language及相邻页配对、仅同cell顺序多句继承；新pin回放核fragment SHA、QA group/number/state。既有Reader/VersionPins传播复用统一常量，不改公开v2合同或RF文件。

当前责任26新用例+91原相关项117通过/1.68秒，5源mypy与相关Ruff绿。真实S07/S08/S09正式链及冻结旧final9、实际AUTO selector/parser两种升级共12通过/52.16秒。新IR E2E明确检查原G-S08-01占比full与G-S08-05/06套话clean，TXT原G-S09-05仍full，未翻译。新旧批次工作键、job IDs、artifact refs隔离；旧ref字节不变，resume零额外调用。隔离Acme身份与本地HTTP确定性响应，不能冒充真实供应商质量。全九/Unit集中运行后填最终收据；无需外仓修改或人签。


## 2026-10-07 IR集中本地验收收口

最终九文档400.944秒：required27/33不变、761定位零失败、角色/情态混淆0、精选66215→62953B（少3262B），负例命中点3→1、噪声span3→2、重复4不变；S08两套话clean、占比事实仍full。optional3/17→2/17：G-S07-07是投资者提问，内容包括研发占比及PI/PEEK等新品验证/性能担忧，并非只是财务数字；原管理层答复实读为泛研发布局/长期开发/财务同比增长。旧整答案混合得到current_business_progress并挂问题，新句级解析没有具体进展入选，因此问题退出精选。记录这个问答上下文取舍，不把投资者担忧冒作公司已确认事实，不泛化允许丢实际业务动态；原件保留，原golden不改。三条先前optional取舍仍可查。

全Unit一次1688通过/10失败/140.93秒，均为英文测试把默认写死0.1.0；补显式旧TXT pin与新默认的文本/角色/定位同等并回放旧pin，不削业务断言。相关143复验1.35秒绿，新QA含29项；全CI范围Ruff及45源mypy绿。真实节点/冻结9/两种实际升级12项52.16秒绿，不重复长套件。全九报告和IR小收据保存，9原件/两配置/RF三owner/10运行源码SHA不变；10个自身tmp根、包装文件/脚本/缓存全部恢复absent（全Unit临时逻辑58,364,951B已删除）。日常CI没有加入全九或真实长E2E。

正常发布准备，精确CI未完成前不冒称published。后续仍须处理应用句与募投表联系；S7不complete。receipt生成脚本首次补丁上下文不匹配、没有修改，随后修正；UTF-8显式配置继续执行。


## 2026-10-07 IR0.1.1发布完成（覆盖此前准备/等待状态）

实际代码c1295b12b652006ec4713e1155170ac66cad7406已推master；正常commit/pre-push绿，精确CI37552600440 attempt1全部step/job成功，job112571348105/75秒。CI全Unit和短合同全绿，先前版本写死的10失败已在推前责任包解决。11个自身tmp路径/脚本/缓存恢复absent，原件/用户配置/RF三owner及10运行源码SHA保持，另记published Git blob SHA以处理换行差异。正式收据状态published_exact_ci_passed。没有日常长测新增或供应商调用。

下一唯一施工动作已写总task_plan：RF状态核查后处理S01应用事实预算，再处理S04募投intro/项目表真实联系。S08两套话已解决；S7仍in_progress，不能拿九样本定位绿冒充所有业务覆盖完成。旧N6/旧IR等待文字不恢复为门禁。
