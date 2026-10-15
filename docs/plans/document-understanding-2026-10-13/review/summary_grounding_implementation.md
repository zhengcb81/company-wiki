# 正式摘要：逐命题支撑与真实质量整改

ROOT，2026-10-15，属于原Phase C质量节点；不增加人工审批、小节点签收或每次commit全套验收。DU4三作者目录不写入。

## A 当前实证与责任

CWP 0b61bcd1正常push，5642PASS/24SKIP，精确CI38788268113 SUCCESS；RF caf74c5f精确CI38784099830 SUCCESS。

真实cn-h1中微2026半年报，用实际mimo-v2.6-flash/thinking disabled/8192/temp1：0.9一次POST完成、96原文定位通过、same/cross-run零新增POST；18103 tokens/3345µUSD预算代理。母账599590tokens/385113µUSD，旧unknown7保留，累计上限200万tokens/$20。原件/生产配置/sentinel保持，独立临时湖已删除。输入、原始终文、canonical bundle和native账本已保留，不重发来掩盖失败。

独审已发现：合法unit引用与原文SHA/locator通过仍不能证明claim的每个产品、阶段和数字由该claim自己的support支撑。部分事实存在于完整selected输入，却不在该claim所引unit。这类事实不能说成来自外部捏造，也不能质量签通过。独审已完成20条：8PASS/6WARN/6FAIL，20/20 decoder展开与canonical引用完全一致。报告与实际输入/终文/引用已冻结于cn-h1-citation-unit3-live-receipts.zip；原付费response不可改写。

旧0.8对照尚未真实调用：测试observer把旧模型按原文位置排序的group伪装为要求selection顺序的新阅读context，closed_group_support拒绝 order。失败在测试适配层，无POST/预留；不是产品解析报错。先写零API反例，沿唯一quote oracle分别评估实际旧组，不修改旧HTTP字节、不放松新context/native闭合校验；测试夹具应明确实际schema。保留整组FAIL及旧失败收据。

## B 共因整改施工顺序

1. 冻结真实input/response/bundle和逐claim独审证据；区分材料召回、协议合法、来源重放、事实语义支撑、业务覆盖五种结果。前四项工程绿不可替代最后两项质量。
2. 将独审实际错引固化为零供应商回归：原response经正式decoder复现同一canonical引用，按每条命题自己的support核对gold锚点。用缩小/错换unit、只在另一个claim有数字、问题带数/回答未确认、跨产品/阶段/期间/单位反例，避免只针对中微产品特判。context只能解释不能授权事实。
3. 先比较真实请求表示、unit语义粒度与模型读/引用负担，复用共享结构/DU4经营状态与表格事实；禁止只换prompt、给缺引用自动补邻居、把全文全引、用字面数字匹配假装通用语义判断，或新增第二解析/选择器。候选改法必须由旧失败回放和跨产品/行业反例框住。
4. 最终实现需把提取/摘要/支撑责任分清：量化/经营状态绑定由原生观察及共享引擎提供，LLM只改写有支撑的命题。自由叙述的语义不确定性不能靠SHA洗成事实；使用既有大节点独立审查，明确抽样/未覆盖边界。不能未经证据就声称所有自然语言事实可由简单规则证明。
5. 修后先保存材料做零付费复现/集中契约与正式CLI集成，避免每改一个小点重发API。只在完整候选冻结后，依配置跑MiMo/DeepSeek/MiniMax真实摘要，保留旧结果/费用和原分母；原三与新三真实公司端到端仍由母计划负责。

## C 集中验收

必须同时记录实际业务覆盖、每条claim产品/阶段/数字/期间/单位/否定与support、QA归属、原语言、原文重放、same/cross-run零重付费、真实时间/容量/预算以及测试目录恢复。模型有一次绿不等于系统可靠；不提高限额或删除困难样本换绿。旧0.8基线修测试observer后再做实际对比，失败的new样本不盲目跑更多付费。默认仍0.8，三条DU4完成后由ROOT统一接线，不要求作者改此层。

状态：A真实工程通过但语义质量FAIL；observer纯反例RED 1FAIL/16PASS→修测试适配后30PASS/3.62秒，原oracle和产品未改、0API。独审已实收，B/C正式共因整改未完成。下一步将真实逐claim错引和泛化反例固化为ROOT回归。


## 下一施工节点的明确边界

- ROOT源码：`automation/narrative_model.py`、`narrative_model_citations.py`、`narrative_contracts.py`与既有共享策略/摘要投影；先调查影响，再决定实际最小的责任重构。测试oracle继续`tools/document_understanding_benchmark/closed_group_support.py`，不能另写文本匹配器。不得修改三作者新包/测试，不能把纯组件单测当成生产接线完成。
- 新测试责任：`tests/unit/test_narrative_claim_grounding.py`和`tests/integration/test_narrative_claim_grounding_e2e.py`（拟议、未实施）；真实材料由本节点受hash保护的zip中取精选反例到独立fixture，不拷原PDF或完整湖。旧付费失败保留原样，改后的候选要另编号。
- RED应覆盖实际20条解码得到的六处错引用；缩小/错换unit、邻接/标题不能借数、产品指代、同量纲不同时期、planned/actual、QA问题不是事实。必须包含非本公司/英文/相反阶段的合成例，避免写产品白名单。自然语言蕴含不能伪装为简单标点/数字通过即证实；自动可证范围与需大节点独审的范围分别记录。
- 测试读取真实模型输出经正式decoder；检查真实canonical support/context，不能只验证测试自造DTO。离线集成走正式worker→verify→public read→RF消费，并检验cached失败的诊断/费用，0真实供应商调用。
- 完成证据包须输出：原输入/输出及每个引用的SHA、逐命题支持矩阵、失败/提醒/覆盖未知、实际费用、选择代际/缓存命中与0新增POST、原件/配置/测试目录前后状态；审查一次集中进行。

[独立逐条报告](cn_h1_live_summary_independent_review.md)。机器逐条证据、原始终文、引用和现有oracle测试适配均在[冻结材料](../common-root-quality-evidence/cn-h1-citation-unit3-live-receipts.zip)内按原仓库相对路径存放。仅做纯测试时解压到独立检出，再运行 `python -B -X utf8 -m pytest .planning/shared-reading-production/live/owned-runner/test_phase_c_observer.py tests/unit/document_understanding_selection/test_closed_group_support.py tests/unit/document_understanding_selection/test_attributed_context_quote_oracle.py -q -p no:cacheprovider --basetemp=.cw-obs-replay`，无需API凭证；测试后清理自己创建的空basetemp，不碰预先存在内容。真实runner不属于这条纯测试命令，不可在回放时误调用供应商。


## B1 正在实施：统一quote oracle增加逐claim观察

2026-10-15续跑：先将真实终文经正式decoder的引用和审查锚点固化为纯测试。新增 `score_claim_facts` 作为现有quote oracle的组合观察入口，仅按调用方明确提供的claim→gold命题映射评价自己的support；context与其他claim/全文selected不能借用。它不自动判定自由文本的语义，不进入生产许可/采集门禁，也不替代大节点独审。多unit命题的每个已知锚点可分别来自实际所引单元，必须同source/role/page范围；不凭字面数字宣布完整语义正确。旧score_facts的单一闭合group规则保持。

测试应证明：旧summary即使20/20引用展开与96原文SHA通过，六个已知错引仍观察为未支撑；人工审查指定的真正支撑在selected中确实存在；只换测试候选引用后可分开观测，原付费response/SHA绝不改。未知/重复claim或证据引用、只在context的问题数字、跨产品/期间/角色的反例须明确失败。生产协议设计另由独立只读架构调查提供，当前尚未冻结新协议，不先修改旧请求字节。


### B1 实测收尾

- 已冻结123069字节真实精选fixture，SHA `13fcc0a584f0f5021c51282f119bfc7c7391b959914d57337b55f1eeb9e74c29`；从public bundle重建typed selection后，正式request instruction/data与原真实输入逐字相同；原付费response通过正式decoder仍还原原20条。
- 新 `score_claim_facts` 只组合原有quote/range/role matcher，既有score_facts行为不改。原六条错引明确false，而其所需真实支撑在完整selected中true；跨claim/context/角色/期间/货币/否定及真正被引用的跨unit锚点都有反例。
- RED为新观察入口缺失；首次26PASS/1FAIL是测试把投资者问题当成business-fact oracle可接受角色的错误预期。保留原matcher的角色范围，改为公司事实断言，并新增同company_filing角色context借数反例；最终28PASS/2.52秒。测试只观察已审查锚点，不认证一般语义。原件/生产配置/sentinel保持、Temp删除、0API，原失败输出和收据均保留。
- 下一步采用独立架构报告的source-scoped一次请求设计；先在共享引擎做来源任务view，不选新provider，不用gold反推生产规则，不在renderer重新按公司/产品排名。详见[接口施工细则](source_scoped_summary_implementation.md)。


## 来源任务＋纯编译节点实收（生产v4仍未接线）

最终47组件PASS/4.30s，原None/v1/v2/v3/QA集中160PASS/8.08s是compact前快照；独立44PASS/2.88s同为compact前，最终defaults只读核对无阻断。无损回还测试覆盖实际角色/flags/kind/section/topics/all-parts与QA例外；实际source view30590B对旧同范围30758B，保留47813B退化初版和相应RED。完整v4 HTTP/token/真实语义尚未测。见[节点实证](../common-root-quality-evidence/source-scoped-foundation-acceptance.json)。

审查找到的两项新增helper边界已TDD修复：可变kind/section标签影响不可变plan hash，改为有限str字段；JSON对象role先去重会TypeError，改为按已有规则非str→unknown再去重。不重新做来源身份/SHA或引入许可。原始quote oracle的matcher/业务角色边界保持；显式负控证明错误文本搭配合法锚点仍不能称一般蕴含成立。合成夹具改metadata未重建EvidenceSpan造成的hash错误已在夹具修复；mypy局部list标注、测试角色预期、所有RED与初版结果均保留。

下一步必须注册显式v4正式renderer/decoder、因果依赖和现有worker/caller，不留作永久闲置模块；旧v3真实终文和None/v1/v2/v3 wire保持。source task的每个原文body只一次，共享refs是图；context不作事实，完整native scope闭包不表示所有命题真实。继续补共享引擎有证据的指代/对象和覆盖分配，再做离线正式E2E/恢复与真实配置供应商独审，原六错引与PD5/Matrix遗漏未关闭。
