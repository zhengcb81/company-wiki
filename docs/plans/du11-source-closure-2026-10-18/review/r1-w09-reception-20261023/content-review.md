# W09 独立内容审查（2026-10-23）

## 结论

**两项实质内容问题需由ROOT修复。** 收入金额、单位换算、主/压力公式和原文切片均未发现计算错误，但“引用角色修好了”没有完整传到模型说明。另有两项说明精度问题。可在ROOT整合版本共因修复，不需要外包作者重跑整套或重复收费。

审查绑定作者HEAD `eb7c2deec3650889a10220fdfe8fccb168b28c72`。这是W09包的有限内容审查，不代替W08新摘要采用、资料覆盖核查或W12四路公司审查。数值部分另由未参与作者实现的只读子agent独立重算。

## 实核范围

- 49/49当前claim逐行比对真实source/locator/target/role、连续页文本、raw/strip/page SHA，全部匹配；22/22当前excerpt模板独立重切匹配。没有重新打开PDF或把页文本hash冒充本轮PDF实读。
- 完整看了49项八组业务含义。Biology自身段、三条H2 rebase、non-TIDES R/D&M机制、TIDES客户/分子句、18条跨业务价格条件和两条历史弱化的核心引用/角色正确。18条本来正确的conversion反控未被误改。RPO另外核对为管理层预计而非未来实绩。
- 主228参数/128公式、压力253参数/148公式，54个分区年度值、25行经营桥、7项敏感性由独立Decimal/受限算术AST复算，最大差仅2.46e−11 CNY million。未执行作者引擎或测试，不能把这些独立算术探针写成作者native重跑。
- 六分区互斥，TIDES只计一次；万元÷100、亿元×100、元÷1e6到CNY million正确。RPO58004.7875存量/42207.0646预计值均无收入DAG消费，未与H1/新单加总或当全年floor。
- 共同压力按3000/6000两个互斥池只施一次，年度−4500/+3600/0，三年累计损失900；FY28恢复原单年路径不等于追回900取消损失。

## C01：历史弱化没有传到driver正文（P2）

`claim_driver_other/discontinued`已正确降为history_base，原文只有其他业务历史下降行和终止经营零收入/分类依据。然而main/stress的两条driver仍声明：

> Actual latest half-year anchor and disclosed project/ramp mechanisms support conditional continuation...

其evidence节点仍叫issuer_current_operating_update、one_step，conclusion称latestH1给actual workload/conversion direction，因果链仍是客户项目→可交付量→净价→确认。两份native输出的headwinds也原样发布这套话；其他位置的“没有未来机制”限制没有撤回该错误断言。

同类复制残留出现在12项calibration统一套用TIDES72.6/44.3%和Bachem限制，至少Testing/Biology六项并非自身基数说明。

**根因与最小修法：** 主claim已变，driver、calibration等平行说明仍各自保存旧模板。由authoring责任层按实际证据处置和scope生成同一套说明：历史-only要写条件runoff/零贡献，不写已披露ramp；有真实机制的业务保留机制。保留所有收入、负贡献和合法推测，不加公司词典、关键词判别或新门禁。用中性“历史下降/零范围”及“真实经营机制”对照检查最终input和render。

## C02：Low/High错用了Base的35.3%（P2）

三项`non_tides_{low,base,high}_2026_activity.rationale`全部说“this index requires H2 D&M growth of about +35.3%”，但指数分别1.1/1.3/1.5。在同一“残余H2重复可比H2”条件下独立重算：

| 情景 | H2 non-TIDES收入，CNYm | 隐含D&M H2收入，CNYm | 隐含D&M同比 |
|---|---:|---:|---:|
| Low | 14,309.42141054 | 11,723.96835035 | 4.3038% |
| Base | 17,793.62636872 | 15,208.17330853 | 35.3015% |
| High | 21,153.26211666 | 18,567.80905647 | 65.1910% |

计算保持残余H2=2585.45306019、可比D&M H2=11240.20845397。这是条件分解，不是观测预测区间。当前说明高估Low、低估High最大驱动的要求。

**根因与最小修法：** Base cross-check丢了scenario标签后复制到全部参数。按已有组件桥生成各情景说明，或明确35.3%只是Base对照；要以该情景完整H2确认收入（含自身price/FX）解释，不是activity单因子。不要反过来调预测数迎合错误文案。中性多情景反例必须保证不同情景不能继承第一个情景的数字。

## C03：舍入传播说明夸大且表引用不存在（P3）

`component-bridge`的residual_h1_yoy行写舍入放大为“several percentage points”，并称敏感性表显示舍入基数变化。现有表实际是native敏感性和残余±10%条件，不是舍入表。若按显示数常规四舍五入，四个显示输入上下界的16角点约给5.31867%–5.91918%，全宽约0.6005个百分点，不能叫several；这也不是经验置信区间。

删掉夸大的量级和不存在表指针即可；若保留区间，注明只传播显示舍入、写清假设。约5.6%和正式预测无需变更。

## C04：尾项修复说明和数值保真论证不精确（P3）

helper的自检循环现在确已位于Testing模板加入后；本审查22/22独立重切无误。memo§3也确已定义“逐位相同”仅为scenario segment_subtotal。可是§2.1原句仍未限定，review-fixes却说该处已经改好；完整阅读不至于误解，但收尾声明不完全对应当前文本。

另memo§6把置信分不变当作“没有偷改数字”的证据之一：结构置信分恒定不验证收入值相等。应引用真正的subtotal/diff核对。两项直接改说明，无需因此整链或收费重跑。

## 正确保留的内容与未知

Base经营桥的5.6192%残余同比、35.3015%H2 D&M隐含要求、2.04983倍FY28 D&M要求、65.8196%集团净增量份额与61.5711%正向driver分母份额均能复算，两个分母没有混淆。

U01子业务拆分、U02净价/mix、U03利用率/吞吐、U04取消/期初队列兑现、U05客户配置、U06经验校准、U07其他/终止机制、U08同行转移率都是真实外限，金额暴露与当前输出一致。12校准均unverified，observed_range均null，无历史预测记录和经验概率区间；允许保留明确条件预测，不能为消除unknown编造未来实绩。

三方法卡总体是跨业务的范围、角色、经营桥和修复方法，未引入production公司名特判或新schema。应补的是**当前证据处置→scope/scenario→所有派生说明**的一致性，而不是另一轮权限审批。

## ROOT最小收尾

保留旧包/FAIL，建新ROOT整合版本；先以中性反例框住C01/C02，修authoring共同投影，再对新main/stress离线native输出、快照及说明做集中复验。数字若无独立研究变化应保持不变；句子/舍入修正不用收费调用。缺失49项测试日志由ROOT一次隔离执行补齐。随后W08 summary采用和W12四审仍按主PWF推进。

精确21文件SHA、49逐项结果、22模板结果、数值子审与问题指针在content-review.json。全程0作者工区写入、0作者脚本/测试、0网络/模型/密钥/PDF原件读取、0Git索引/配置改动；只写本MD/JSON，无测试临时目录。
