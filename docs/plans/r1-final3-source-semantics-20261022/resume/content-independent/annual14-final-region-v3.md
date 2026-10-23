# W08 最终region-v3：年报14目标有限内容复审

**结论：PARTIAL；不能改写为whole-content PASS。** 指定p160→p184错误祖先已修复，其他缺口仍保留。仅核最终snapshot，复用旧同原件证据；本轮无原件读取、解析、模型、下载或源码修改。

快照SHA：`d7e5201d8330b700b87dc13140910f508b70dac20aa798e6c7a5c31b6cf4ad23`。249页、96 spans、8,137 chars、1,527 candidates；最终14模块指纹取自该snapshot并保存在JSON。

p184/paragraph4的最终group[18]仅带p83/paragraph2“财务报告”和p183/paragraph7自身分解标题；p160余额行已不在选材，错误祖先消失。

p16/paragraph2、3及新增paragraph16仍是background，只带一般分行业标题，列头/单位/期间未闭合。三行quality_flags仍为空，无定向table ambiguity约束，继续unknown/partial；不声称数字本身为假。D&M/TIDES三条自身view仍缺Chemistry父级。

| 不变目标 | 最终有限结论 | 实际内容 |
|---|---|---|
| ST-A01 | partial | 四分部可读；Chemistry分子范围与子业务父级缺 |
| ST-A02 | partial/unknown | 合计可读；p16列头/单位/期间缺，精确元表未选 |
| ST-A03 | partial | 地区收入在；客户母公司所在地脚注缺 |
| ST-A04 | partial | 580亿元订单在；RPO定义及2026转化排程缺 |
| ST-A05 | partial | 三项收入在；跨页Chemistry父级未进自身view |
| ST-A06 | 本地事实支持 | D&M新增/存量/阶段完整；不直接换算收入 |
| ST-A07 | missing | 42万化合物、R到D310缺 |
| ST-A08 | 本地事实支持 | TIDES订单20.2%、客户25%、分子45%分母明确 |
| ST-A09 | missing | 4000kL、100000L及泰兴完工时点缺 |
| ST-A10 | partial | Testing收入/自身30%/毛利原因在；安评4.6%缺 |
| ST-A11 | partial | Biology收入/自身30%在；集团新客户20%缺 |
| ST-A12 | missing | 整条513–530亿元/18%–22%及前提缺 |
| ST-A13 | missing | 时段/时点确认和预收负债规则缺；p184错祖先已消失 |
| ST-A14 | partial | 一般风险在；集中度/结算FX/竞争缺 |

六项优先遗漏仍全缺：R42万/310、小分子4000kL、安评4.6%、量化指引及前提、多肽完工/100000L、Biology集团客户20%。选材中的“2025年9月”属于Frost行业报告日期，不能计泰兴完工。两条30%各自Testing/Biology父级仍正确。

WorkBudget 7,298,096/16,000,000未耗尽，selection96位满，aggregate budget_full=250。没有最终逐目标丢弃/排名链，不能给每个遗漏代填预算原因；旧actual trace只作历史，不倒签最终字节或排名。API可补原文不等于selection已覆盖，不要求全部财务行进96，但须保留partial/unknown及具体收入信息风险。

JSON含最终support/group/view指针；原文页hash和旧细判据仅引用，旧报告保留。

JSON 9,330B（≤12KiB），SHA：`f5be22df566777b44e7a9e399639789a7ee1c9154b0bea2fcda3da90fbf33cf4`。
