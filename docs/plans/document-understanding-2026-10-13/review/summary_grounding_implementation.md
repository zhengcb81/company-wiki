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
