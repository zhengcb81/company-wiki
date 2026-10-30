# M7 C3 来源候选冻结与冻结后复核

**两份 exact SourceRef 的当前候选、selection 与 /5 请求已冻结；重要业务召回存在 OPEN，当前不适合进入付费 rank。** 本轮 not_paid / not_RF_company_loop，未改 runtime、原件、生产配置或 source manifest。

采用当前代码 `599f6cf6a5a686c0ec5ce38be1f985515d7b7b46`，显式 selector `0.9.0` / `reading-model-input/5`。华利正式材料在 `r2/`，Berkshire 在 `r3/`；selection、normalized 与 request 均保存 gzip 和 SHA。目录内 README.json 等价主收据为 review.json；完整 gold 机械可见性见 gold-visibility.json。

## 实际结果

| 来源 | 原单位 | 候选 | selected spans | request tasks | admission | 状态 |
|---|---:|---:|---:|---:|---:|---|
| c3-cn-huali-ir-202305 | 80 | 17 | 4 | 2 | 2/37 | partial |
| c3-us-berkshire-letter-2008 | 269 | 66 | 7 | 2 | 3/199 | partial |

20/20 冻结检查点所需原文支持集合都存在于当前 normalized snapshot；完整进入 selected 或 model factual support 的集合为各源 0/10。这是严格 all-support 可见性结果，包含身份、行业/财务context，不等于20项语义均错误或每项都必须独立生成。没有模型回复，因此 prose semantics 未评。

P2 M7-01：两种语言的重要业务材料在 source admission/continuity 阶段被遗漏。华利急单不加价、部分新客户补位、印尼两期5000–6000万双/年及阶段条件未入；Berkshire风电33→794MW、GEICO份额等未入。拒绝记录主要为 no_independent_business_support / financial_only；这里只定位共用责任边界，不凭计数宣称已经证明根因。

P2 M7-02：Berkshire t1 只带 “we/our” 新险种正文，context为 `(2)` 和 `Insurance`，缺 GEICO 主体前提；原字节quote本身不能弥补归属。华利t1以“活性。”断句开头，前面的规划弹性前提未全带入。不能以强行改quote解决。

## 20 检查点逐条

| 检查点 | 冻结后观察 | 说明 |
|---|---|---|
| HUALI-01 | CONTEXT_INCOMPLETE | 公司名/记录编号在context；活动日及证券代码未完整进入。身份context单列。 |
| HUALI-02 | MISSING_BUSINESS | 去库存对订单影响、品牌差异及部分品牌Q2预期均未进入。 |
| HUALI-03 | MISSING_BUSINESS | 部分客户降、部分增及新客户订单预计部分弥补缺口未进入。 |
| HUALI-04 | MISSING_BUSINESS | 部分急单2–3周、急单不加价及规模效率未进入。 |
| HUALI-05 | MISSING_BUSINESS | 客户/产品组合、精益制造与工厂效率等经营解释未进入。 |
| HUALI-06 | PARTIAL | 保留积极扩产、土地手续后施工验收1–2年；前面的订单/规划弹性前提未全带入，支持开头仅“活性”。 |
| HUALI-07 | MISSING_BUSINESS | 印尼两期5000–6000万双/年、一期预计2023投产及订单/施工/审批条件未进入。 |
| HUALI-08 | PARTIAL_FINANCIAL_CONTEXT | 保留2022收益8200万元、2023Q1损失约3500万元；各实体本位币前提缺。不可把此项当业务营收数字。 |
| HUALI-09 | MISSING_SCOPE_CONTEXT | Converse/Vans各自收入占比与鞋类范围关系未进入；属范围/分母误归属反控。 |
| HUALI-10 | MISSING_BUSINESS | 工厂服务品牌/团队及新客户先借独立场地后足量设专厂的条件阶段未进入。 |
| BRK-01 | CONTEXT_INCOMPLETE | 公司/2008/签署者及签署日期未完整带入。旧HK/broker标签仍只是来源观察，未替其造metadata。 |
| BRK-02 | MISSING_BUSINESS | 经济敏感业务受损与保险/公用事业表现分化未进入。 |
| BRK-03 | MISSING_OPERATING_FINANCIAL_CONTEXT | 保险承保连续盈利、float与负成本未进入；须保留行业业务口径，不能把财务数强当营收。 |
| BRK-04 | MISSING_BUSINESS | MidAmerican持股及公用事业/管道业务范围未进入。 |
| BRK-05 | MISSING_BUSINESS | PacifiCorp风电33→794MW及2008投资口径未进入。 |
| BRK-06 | MISSING_CAPITAL_ALLOCATION_CONTEXT | 未分红/收益再投公用事业系统未进入；作为原文来源context，非CWP投资结论。 |
| BRK-07 | MISSING_INDUSTRY_CONTEXT | 保险行业8.5% vs Fortune50014%及25年截至2007比较未进入。 |
| BRK-08 | MISSING_BUSINESS | GEICO份额7.2→7.7%及第三名未进入，同时是下一条的主体前提。 |
| BRK-09 | PARTIAL_ATTRIBUTION_RISK | 23.4%、6%→7%+及新险种正文保留；只给Insurance/(2)context，缺GEICO antecedent，we/our不可按Berkshire总体现有业务解读。 |
| BRK-10 | MISSING_OUTLOOK_CONTEXT | 2009经济展望及“不预测股市方向”的否定限定未进入。 |

## 来源/预算/回放边界

来源原Ref/SHA/字节数由现 owner exact-mode校验。两源 FY/date/URL 缺省保留；Berkshire原 HK/Unresolved/broker_research 冲突原样记录，英语由正式源准备owner识别，不在FF/RF改市场。缺官方下载收据未挡住本步内容读取。

POST、网络尝试、下载、SDK、raw复制、新native generation均0；r2/r3受保护原件/config/生产DB/母账指纹前后相同，所有 owned Temp 自动清理。该指纹收据同时记录 ledger 文件存在/缺省状态，未把历史值冒称实时预算。

反泄漏限制：检查旧 freeze_gold.py 的reader示例时，其内嵌目标已进入上下文，已及时告知ROOT；未改算法，正式 gold JSON 在候选冻结后才打开。本次只称冻结来源回归，不称 blind。

作者观察脚本首次不能序列化tuple-key，第二次Berkshire重复native_source_view展开至9,504,760B超过作者8MiB cap，导致包装成PARSER_INCOMPLETE。最终r3只对snapshot去重，正式parser/selector未改且成功；不是产品解析错误。共5次PDF owner read（含这些重试）已保留，不再全PDF重读。

从保存snapshot的0PDF replay：Berkshire selected spans精确一致；华利fresh-work-account replay不同，故只作为局部源probe，不冒充原预算/原selection回放。实际r2 selection/request保持权威。replay_normalized.py公开该限制；后续根修可使用snapshot但须保留原selection对照。

ROOT下一步应定向修共享 source admission/continuity/主体前提，保留gold并用中性正负对照；不按公司补词、不提高额度、不用付费rank掩盖源缺口。完整RF公司循环未启动。
