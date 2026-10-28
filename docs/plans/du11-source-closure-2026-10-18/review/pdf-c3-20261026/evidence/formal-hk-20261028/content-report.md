# HK C3 独立内容审查

**FAIL：3 个 critical 目标实际摘要通过 2 个。** 来源已选中、实际请求已发送 3/3，不能替代摘要内容验收。生命周期恢复与公开读取收据通过，但内容节点不能关闭。

审查人 `/root/c3_semantic_final_20261028` 非摘要作者。只读检查实际请求、原语言 final、公开 bundle、冻结 gold 与运行收据；没有外部模型、网络、PDF/Docling重跑。来源 SHA `4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36`；bundle 解压 SHA `ba856a0881d078ae55dee65b6583f19f8a45c7abe4da6c6d626b840effe9a0ae`；实际 final SHA `2bbbaf0ce5e1dbac4714a10d8ca0466ac37827c4928814902f49dad94133d074`。

## 三个 critical 目标

| 目标 | 实际 claim 与引用 | 结论 |
| --- | --- | --- |
| 行业云收入、同比与原因 | t37 已发送 p2–p5（s33–s36），原文在 p13 段9–12；final 没有 t37。t27-1 仅写行业云人民币1,340.4百万元（187.1百万美元），引用 p9 的总收入段。 | **FAIL**：缺同期1,245.4百万元、+7.6%、IT需求与复制行业方案两项原因。17.8%属于全公司，不替代行业云同比；未出现23.0%拼错。 |
| 研发期间与人员时点 | t34-1：『報告期內研發費用為人民幣420.5百萬元（58.7百萬美元）；截至二零二五年六月三十日，研發人員達1,094人。』支持 t34/p3=s28，`loc:v1/page:11/paragraph:21/chars:404-469`。 | **PASS**：期间、时点、币种、单位及人数均保留。t33另述2024年底武汉中心含实习/外包超过620人，主体和时点明确，没有替代1,094。 |
| H2 AI计划不得当作已实现 | t35-1 保留『展望下半年』『將』『旨在』，modality=`planned`；支持 t35/p3=s30，`loc:v1/page:11/paragraph:24/chars:475-571`。 | **PASS**：维持战略、持续研发、提升AI能力仍是未来计划。 |

行业云问题是实质目标遗漏，不是要求每句重复同义基数。即使允许省略同比基数，整个行业云7.6%增长与两项明确原因仍全部消失。该四片段在实际发送任务中完整存在，故根因位于输出取舍/覆盖验收，而非本次已修的来源选择、拼接或模态识别。

## 完整24条输出的其他问题

- **CONTENT-01 / P2：关键业务内容漏选。** 60个任务对应目标24条；实际24条均来自t1–t35，没有t37或更晚任务。低信息背景先占用配额，现有输出契约没有确保已发送的重要业务更新进入最终摘要。模型的内部取舍不可从收据推断，但漏出发生在已送达之后可以确定。
- **CONTENT-02 / P2：金融数字缺必要列口径。** t3/t4从三列模糊表格选择首列数值，未指明期间、币种、单位；t9/t10/t20照列三个数字，亦未把列与期间/货币单位对应。`uncertain`和`needs_review`如实保留不确定性，却不能令这些数字成为可独立理解的金融事实。本审查不在缺表头时猜测具体哪一年或换算错了。
- **CONTENT-03 / P2：因果句缺被解释主体。** t2-1只有『有關增加主要由於經營虧損增加及利息費用增加。』，其事实引用p14段13亦只有同一句，context只有『管理層討論與分析』。没有指出何者增加；前一条t1经营亏损更容易造成错误承接。任务输入本身已缺前指，因此须检查来源任务闭合及输出指代，不能仅认有引用就合格。
- **信息分配观察：** t8把财务指标标题改成定义，t26重复『高質量、可持續發展／技術立業』原则；多条股权计划规则及非GAAP定义占据24条目标。这些有原文支持，不冒称幻觉，但不应掩盖已发送行业云关键更新的缺失。t26文字是持续原则，模型标`planned`也不够精确。

逐条核对全部24条 actual final→本任务 factual basis_parts→bundle evidence_id，**引用映射全部通过**；没有借context-only或其他任务支持。112个span均绑定同一来源。该机械通过不能证明每条改写的完整性，以上缺口仍成立。

## 已验生命周期及消费者的实际范围

- 唯一POST、唯一已知usage：输入15,327、输出1,663，合计16,990 tokens；3,109 micro-USD为预算代理费用，非供应商账单。final-only捕获SHA与native收据及bundle相同。
- 激活前故障恢复：`activation_pending`恢复后attempts 1→1、POST 1→1、tokens16,990→16,990、micro-USD3,109→3,109，generation及response identity不变。
- 已完成同run重启与跨run缓存：均completed；同run预算不增；跨run预算0、native-usage空，events总POST仍为1。没有重复外发。
- 公开读取replay verified，exact/latest同artifact。RF-narrative公开读取返回同一bundle的同24条摘要，质量仍`needs_review`、selection仍partial。
- FF真实调用2次、下载0，复用2025H1原件；其自身仅`source_candidate`且`pending_verified_open`。RF-source随后有`verified_read`与同SHA原件读取收据。**RF-source的narrative为`not_consumed`、依赖0**；不能称已经进入RF预测或研究依赖。RF公开context读取成功与RF下游采用是不同证据范围。
- overall收据的protected/sentinel不变、temporary lake已删除均为true。审查人未创建测试湖或后台任务；只保留本目录小脚本与报告，不复制完整bundle。

RF的`not_consumed`是**本次只读准备阶段的预期收据，不是产品缺陷**：RF `source_preparation.py`读取context后调用`source_narrative_context.py:34`的`narrative_read_receipt`，该构造器直接初始化`not_consumed`及空dependencies；本次CLI没有传forecast/claim/parameter绑定。保留的`narrative-read-request/1`没有`required`标志，只有ref/as_of/expected_source。原consumer请求文件已随临时湖删除，因此不冒称逐字读取过该已删文件；runner的消费者writer直接保存传入read request。实际RF预测采用未在本次范围内请求或证明。

## 供共因定位的实际任务元数据

以下topics/section_role按实际请求默认值展开；JSON另含各context及support member完整关键元数据，没有复制原文bundle。

| Task | 页/事实引用 | kind / section_role | 展开topics | 事实member选择原因及质量 |
| --- | --- | --- | --- | --- |
| t2 | p14段13/s41 | background / management_discussion（显式） | core_business（默认） | reading_plan + operating_state_unknown；meaningful_fact |
| t3 | p42段5/s97 | paragraph_event / unknown（默认） | core_business（默认） | reading_plan + operating_description_unknown；meaningful_fact；table_structure_ambiguous |
| t4 | p42段9/s98 | paragraph_event / unknown（默认） | core_business（默认） | reading_plan + operating_state_unknown；meaningful_fact；table_structure_ambiguous |
| t8 | p7段2/s7 | background / unknown（默认） | core_business（默认） | reading_plan + operating_state_unknown；meaningful_fact |
| t9 | p8段5/s11 | background / unknown（默认） | core_business（默认） | reading_plan + operating_state_unknown；meaningful_fact；table_structure_ambiguous |
| t10 | p8段9/s12 | background / unknown（默认） | core_business（默认） | reading_plan + operating_state_unknown；meaningful_fact；table_structure_ambiguous |
| t20 | p41段28/s95 | background / unknown（默认） | core_business（默认） | reading_plan + operating_state_unknown；meaningful_fact；table_structure_ambiguous |
| t26 | p9段3/chars30–56/s16 | native_continuity（默认） / unknown（默认） | business（显式） | reading_plan；description |
| t37 | p13段9–12/s33–s36 | native_continuity（默认） / unknown（默认） | business_revenue_measure（显式） | 每个member均reading_plan + business_revenue_measure；meaningful_fact；无质量flag |

t26事实member为`pdf_native_range`；其余表内事实member均`pdf_text_block`。所有这些member的table_index/row_index均null；表格数字以模糊文本块进入，而不是已闭合表格行。它们的context-only标题均`pdf_text_block`、reading_context、description，未被final错误用作basis。共因线索是fallback把纯财务/标题块送作core_business meaningful_fact，而明确信息的t37虽已正确成组送达仍被最终输出遗漏；具体代码owner由ROOT下一根因节点确定，本审查不据收据猜测模型内部决策。

尚未通过：关键摘要内容3/3、金融数字列口径与因果主体闭合，以及partial选择之外的全文完整性。不得据CLI completed、overall PASS或source gold3/3关闭内容验收。
