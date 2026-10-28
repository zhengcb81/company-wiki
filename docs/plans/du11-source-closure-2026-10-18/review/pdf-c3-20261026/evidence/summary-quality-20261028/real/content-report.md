# HK质量复验：独立内容审查

**PARTIAL：没有新final可审；来源支持准入FAIL，内容验收未通过。** 新run `phaseC-090-d7c91950f2dc` 在预留前以`PHASE_C_GOLD_SUPPORT_MISSING`结束，0 POST、0 reservation、0 tokens/费用。不是模型再次遗漏，也不能称新摘要通过2/3。

实际准备的57任务中，研发t32及H2计划t33来源支持齐全；行业云关键事实失去共同的事实支持作用域，故来源gold与准备请求gold均为2/3。observer中的`sent_tasks`是编译范围标签，本run并未实际HTTP发送。

## 行业云闭合断裂

- **t4/p2=s33**，background、management_discussion、meaningful_fact：收入头含人民币1,340.4百万元及同期数字，末尾停在`人民幣1,245.4`，缺该基数的单位与同比。
- **t35/p2=s34**，native_continuity、description：以`百萬元增加7.6%。該同比增加主要是由於不斷增長的IT需求及我們向垂直行業客戶複製行業解決方案\n的能力。`起止，缺行业云收入主体与基数数字。
- 两任务context都只是“管理層討論與分析”，没有把另一任务纳入事实support。t19只在总收入段保留行业云1,340.4当前值，不能替代行业云同比及原因闭合。task-local basis不允许模型跨任务借证补出该闭合。

**QC-IR-01 / P2：source grouping/native continuity/citation-support closure失败。** 文字仍在准备材料中，不能描述成原件没内容；但完整收入＋基数＋7.6%＋两项原因不再属于同一可引用支持视图。现有预留前防线正确拒绝了这次请求。仅凭留下的请求无法断言更下层的具体代码分支，须由ROOT来源层定位；审查人没有额外重跑或改源码。

## 另两关键目标与整体审查边界

t32/p3=s27完整保留“報告期內”420.5百万元（58.7百万美元）及2025-06-30研发人员1,094人的时点；t31另述2024年底武汉中心含实习/外包超过620人，输入里没有替代。t33/p3=s29保留“展望下半年／將／旨在”和AI计划。**这些只是准备输入通过；无响应，无法验新摘要是否正确保留。**

准备材料还有可核对的风险：t2/t3/t9/t11/t12页脚被列作事实support；t5是“非公”、t7是“非公認”，而对应毛利/毛利率正文拆在别的任务；t10“主要由於…”仍无被解释结果；非GAAP定义、原则套话、股权及会计政策仍占任务，有的标meaningful_fact。这些是输入观察，不能冒称模型已输出它们。新final的货币/单位、主体期间、引用support/context、业务更新遗漏及套话程度均尚未评定。

## 本run生命周期与绑定

- overall=`PRE_RESERVATION_BLOCKED`，batch failed、document dead_letter；native usage为空，母账仍1,800,368 tokens / 727,945 micro-USD。没有新增unknown或收费调用。
- 激活恢复、同run重启、跨run缓存及FF/RF公开消费者**本run未执行**。不借旧run的PASS，也不把RF读取当预测采用。
- producer收据：protected/sentinel不变、临时湖已删除。审查人没有启动额外生产脚本、模型、PDF/Docling或下载；源码/PWF/原件/config及工程独审报告均未修改。

来源SHA：`4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36`。

准备HTTP输入体SHA（67,716字节）：`1bd23886b5e395ca39de93d8c9ea270ca6f7ea5dec6dba6fb4d6ff73fa18d108`，与pre-reservation事件相同。选材输入身份SHA为`eea2d381981baa554129d54e7ef48dd28740057a744fbda3e3c276b1d0367bc2`。**artifact/final SHA均为null，因为没有生成。** 实际launch、generation、材料、gold和各收据SHA详见同目录`report.json`。
