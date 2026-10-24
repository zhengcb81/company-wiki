# W08 年报14项独立真实内容审查

结论：**3 pass / 9 partial / 2 missing / 0 unknown**。仅评价绑定执行的实际选材 citation/model 可读链；不签全公司 RF 四审、最终产品、模型摘要或后续修复版本。

- executionSHA：`69a13ee56af0bac68a2aca65d9c355a44cfcd5f84a4c32c8f8cc371a1f05763d`
- selectionSHA：`17c1f79ac72208fc74975c4488aaf14cd14e17b66999b219ae9045d01cec5fb9`
- goldSHA：`dae0f0b81edc2df430ce4707c4ad9ea15126ab2998aaa6c0f4f7dff66022b9c8`
- SourceRef：`urn:company-wiki:source:sha256:7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`，1,608,226 bytes。
- selector0.9.0；249页/5647units；1512 candidates；96 spans /8518chars；work8630449/16000000未耗尽。
- 实际离线 model view：96 fragments /55 tasks；相关编译代码与 execution 源哈希一致。未调用 LLM，未审新摘要。
- 两条30%检查通过；`coverage_complete=false`、`whole_content_pass=false`保持不变。

## 逐项结果

| 目标 | 实际可读链状态 | 事实与缺口 | 实际task |
|---|---|---|---|
| ST-A01 | partial | 持续经营四业务分类中的Others与p119 Chemistry完整范围未入选；D&M/TIDES的局部task不能读取Chemistry父级，选中的业务名称不构成完整业务树。 | t22, t25, t12, t32, t33, t13, t14, t16 |
| ST-A02 | partial | 保留434.2亿元持续收入、454.6亿元合计和21.4%/15.8%及重述说明；精确元值未由安全数表链覆盖。p16裸行与p235裸数的选中字面值缺自己的列头/单位，不能充作已采用精确收入。 | t24, t10, t11, t37, t19, t55 |
| ST-A03 | partial | 各客户地区金额与同比已保留，p16客户母公司所在地及对比期调整脚注不在任何可读task。 | t24 |
| ST-A04 | partial | 年末持续经营在手订单580.0亿元/+28.8%已保留；p184 RPO定义、精确万元及预计2026确认排程均未选。 | t24 |
| ST-A05 | partial | 364.7/199.2/113.7亿元及对应增速已选，但t32/t33上下文只有章节，缺t12 Chemistry父级。全局可见t12不能充作另一task的合法basis或局部限定。 | t12, t32, t33 |
| ST-A06 | pass | 同一实际support自述小分子D&M、新增839、期末3452及83/91/377/2901、后期+22；无需借别的task解释该局部指标。 | t32 |
| ST-A07 | missing | 超过42万个新化合物与R到D 310分子均不在96个selected bodies或model fragments中。 | 无 |
| ST-A08 | pass | TIDES自述年末订单+20.2%，TIDES D&M自述客户+25%/服务分子+45%，各自对象在实际support内，可分别读取。 | t33, t13 |
| ST-A09 | partial | 小分子API超4000kL已保留；超100000L也保留。2025年9月提前完成泰兴建设的日期/事件被两段之间的切分去掉，citation上下文和model均无法取回。两处100000L是同一产能事实。 | t28, t29, t34 |
| ST-A10 | pass | Testing40.4亿元/+4.7%、安评+4.6%、新分子收入超30%和毛利率下降6.32个百分点/价格随订单转化均实际可读；30%视图含自身Testing父级，无Biology。 | t14, t15, t35, t39 |
| ST-A11 | partial | Biology26.8亿元/+5.2%及本业务新分子收入超30%实际可读；集团新客户超20%的p14原文未选，不能用新分子30%替代。 | t16, t17 |
| ST-A12 | partial | 预计2026整体513–530亿元、持续经营增长18%–22%已选，预计模态仍在；在手订单基础、行业/贸易/监管稳定前提、非承诺与不确定性均未选。 | t36 |
| ST-A13 | missing | p183标题和p184终止经营重述脚注不是确认政策支持；时段/时点金额、业务政策、预收先负债后履约转收入均未进入实际support。 | 无 |
| ST-A14 | partial | 客户研发/外包、监管及产能延误风险已可读；48.11%客户集中度、美元为主结算/人民币升值风险和竞争风险未选。 | t48, t49, t50, t51 |

各项完整 support IDs、context IDs、原句、source locators、单位/期间/分母/模态/存量流量/不重复计量限定在同目录 `review.json`。

## 四类实际断点

1. **Chemistry层级**：原p13 `(1)化学业务`跨页包含p14小分子D&M/TIDES。当前Chemistry在t12，D&M在t32、TIDES在t33；t32/t33上下文只有章节标题，均无Chemistry父级。父项虽全局可见，不能充作另一task局部basis。A01/A05部分覆盖，防止Chemistry+D&M+TIDES重复相加或差额命名纯R。
2. **容量日期**：原p12/p14为2025年9月提前完成泰兴建设，并披露多肽>100000L；当前>4000kL在t28、多肽容量在t29/t34。9月/提前完成事件未selected，因此citation/model均无日期。两处多肽容量是重复事实。
3. **新客户20%**：原p14明确Biology为集团带来超20%新客户。当前t16保留Biology收入、t17保留本业务新分子收入超30%；20%句完全未选。A11由旧中间审supported退为partial，不能换分母。
4. **指引前提**：原p14在2026指引后紧接订单基础、行业/贸易/监管稳定、非承诺与不确定性段。t36只保留数值和“预计”，上下文没有前提；缺失发生在selection，不能视为无条件实际路径。

## 覆盖方式和需修共因

- **selected实际覆盖**：只计实际task support及该task的context。另一个task中有文字不等于该事实能合法引用。
- **fallback原文已实读**：所有14项源侧事实在完整确切版本页均可核验。A02/A13精确财务数可用财务API或精确SourceRef fallback；A04 RPO排程同样可精确取原文。本审未调用财务API，也未声称摘要采用这些原文。无需把全部财务报表强行切片进96摘要位。
- **叙述价值缺口**：A07研发引流、A11集团新客户、A14集中度/美元/竞争与条件约束；应保留高信息价值的经营事实及源限定。
- **共用可见问题**：父级、定义、事件时间和指引前提未随核心事实进入局部可读链；需要源上下文依赖闭合和逐目标遗漏可观察性。
- aggregate257 budget_full、315有限deferred只说明选材位满；没有逐offer/defer来源链，不把任何具体遗漏归因为96预算。当前work预算未耗尽、字符远低于48000；不据此提高预算或改oracle。

## 独立取证与保护

额外只通过既有SourceRef/SourceVersionReader读原件一次，核SHA，离线提取缺少正文的p11/12/13/17/31/32/119/120八页，共10,888字符。页正文哈希全部与旧审记录吻合，保存一份 `audit-original-eight-pages.json`。已有p7/14/15/16/183/184完整页复用。此次额外读取与原单次parse/select分别记账，未调用parse_pdf_bytes、未遍历其余241页、未复制PDF、无网络/LLM。

输入、原gold、旧PARTIAL、catalog配置及数据库前后哈希一致；reader/fitz已关闭；未写source/tests/Git/PWF。只新增本目录四个审查产物。

这份收据仅说明当前实际选材有用但未覆盖完整14标准；后续代码或英语修复不得沿用本收据冒签新执行。
