# W08 年报14目标：shared-owner完整context有限复审

**结论：PARTIAL，并有一处已观察到的错误context关系。不得据此写全内容PASS。** 本报告绑定指定实际selection，未签后续代码执行或摘要。

选材文件：`b0178aecc041aac84cad508f4a7b5bbbd14984735ba348023f6ad62a7c553b7c`；96 spans、8,156 chars、1,509 candidates、249页。selected_evidence canonical SHA-256：`853df4608ea21aa5821458d755f2d130acbd57a316c3280546cc575a9a4e7127`；reading_context canonical SHA-256：`c5ab4bd4d1ede34a94144503acaacfd3246df06e9b49f06df05d89c57404561c`。

已核14个原盲年报目标，复用上一报告全部原文证据；本轮未重开原件、未下载或调用模型。D&M管线与TIDES三分母可支持；Testing/Biology两30%自身归属正确。重要遗漏仍存在，且相较中间版，多肽容量、Biology集团引流20%、整个2026指引继续掉出。

| 目标 | 实际有限结论 | 具体缺口 |
|---|---|---|
| ST-A01 | partial | Chemistry全分子/制剂范围p119缺失；D&M/TIDES各自view只有MD&A/主要经营情况，未带已选的p13 Chemistry父级，故Chemistry内的父子关系未闭合。 |
| ST-A02 | partial_with_unknown_table_columns | p183精确元表未选；p16两数表行view仅一般标题，无自身营业收入/成本/毛利率/同比列头及万元。21.40等裸数不能自行推定列义。p235也无表头单位，不能借它签精确终止收入。 |
| ST-A03 | partial | 客户母公司所在地及对比期调整脚注p16未选；view无该限定。 |
| ST-A04 | partial | RPO定义、5,800,478.75万元及4,220,706.46万元预计2026确认全部未选；view不能支持转化排程。 |
| ST-A05 | partial_parent_relation_missing | D&M/TIDES各自view不包含Chemistry父级；已选Chemistry独立view context为空，不能跨view借父级。残差纯R未被支持。 |
| ST-A06 | covered_local_fact | Chemistry祖父级未在view中，归入A01/A05；本目标的本地D&M流量/存量/阶段事实可支持。未审新summary。 |
| ST-A07 | missing | 超过42万新化合物及R到D310均未选。数字310在其他金额子串中的出现不计支持。 |
| ST-A08 | covered_local_fact | Chemistry祖父级归入A01/A05；本目标自身TIDES业务及三个分母可支持。未审新summary。 |
| ST-A09 | missing | 小分子API超4,000kL、多肽超100,000L、2025年9月提前完成泰兴建设全部未选；完整context中也无补入。 |
| ST-A10 | partial | 药物安全性评价收入+4.6%未选，不能用Testing整体4.7%替代。 |
| ST-A11 | partial | 为集团带来超20%新客户未选；新分子领域客户快速增长不是该比例。 |
| ST-A12 | missing | 整体513–530亿元、持续经营18%–22%和p14前提/不确定性全部未选；不能描述为仅漏前提，也不构成已选事实的模态错误。 |
| ST-A13 | missing | 时段12,125,518,838.35元、时点31,295,304,900.48元、业务政策及预收负债规则全未选。p184脚注view含p160余额行，为实际错误context关系。 |
| ST-A14 | partial | 48.11%客户集中度、美元为主结算/人民币升值折算收入影响、竞争风险未选；套保文本不能替代结算币种与收入敏感性命题。 |

完整context确认的问题：

- p184/paragraph4重述脚注的view携带p160/paragraph19“5.期末余额…”裸数行，跨23页无关；属于错误context关系，不能作收入父级或表头。精确group为`urn:company-wiki:reading-group:sha256:3669a74d3ecd085f6594eb15515edbf05c4371871f14ef8c0726f0a2648b10db`。
- p16/paragraph2、3的持续/终止经营裸数行只有一般“分行业、分产品、分地区…”标题；没有自身列头、万元或年度。这是unknown/partial列义，不据此指控某个数字本身为假。
- D&M/TIDES p14/paragraph3、12、14各自view只有MD&A和主要经营情况标题；缺p13/paragraph21 Chemistry父级。carrier本地自名数量仍有效，Chemistry父子关系未闭合。

优先trace事实和定位：

- **TRACE-R-42W-310**：2025超过42万新化合物、R到D转化310分子。定位："urn:company-wiki:source:sha256:7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2#pdf_pages=13"。找到该原单元/新carrier，记录fact purpose/eligible/score/value_band及实际planner项；不要把合成化合物量和转化分子量合并成同一分母。
- **TRACE-CAPACITY-4000KL**：2025末小分子原料药反应釜总体积超4,000kL（p12和p14均有）。定位："urn:company-wiki:source:sha256:7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2#pdf_pages=12,14"。从已核原文页定位小分子capacity原单元；本报告没有可靠的现行paragraph定位，勿猜。核单位kL和小分子subject是否在meaning/purpose后保留，及被拆为description或真实SELECTION_BUDGET的具体证据。
- **TRACE-SAFETY-4P6**：药物安全性评价业务收入同比增长4.6%。定位："loc:v1/page:14/paragraph:19"。跟随该自名业务收入同比事实至source fact/measure/purpose与planner；查为何Testing40.4/+4.7及自身30%可保留而该小段仍掉出。
- **TRACE-GUIDANCE-CONDITION**：预计2026总收入513–530亿元/持续18%–22%，附在手订单及行业/贸易/监管前提。定位：["loc:v1/page:14/paragraph:32/chars:1168-1257", "loc:v1/page:14/paragraph:34"]。分别记录指引与其同局部前提的合法forecast/conditional识别和实际defer原因；完整缺失是选材遗漏，不能拿保留一般2026计划替代。
- **TRACE-PEPTIDE-100000L**：2025-09泰兴提前完成建设，多肽反应釜超100,000L。定位：["loc:v1/page:12/paragraph:29", "loc:v1/page:12/paragraph:30"]。比较中间版已选与当前未选的同源同定位事实，判明共享owner变化怎样影响purpose/score/rank；保持L与小分子kL区分。
- **TRACE-BIOLOGY-CUSTOMER20**：Biology持续为集团带来超过20%新客户。定位："loc:v1/page:14/paragraph:26/chars:919-997"。记录客户引流比例的分母和主体识别为何从中间版selected变为本版遗漏；不能借Biology30%新分子收入份额代替。

RPO排程（p184）与收入确认（p119/120/183/184）也仍缺。API能取得这些原文不等于selection已覆盖；不要求全部金额进入96，但下游若需要，必须有真实回读及来源定位。

判因边界：aggregate budget_full=264、deferred记录有限，均无逐目标链。WorkBudget 7,304,116/16,000,000未耗尽，selection96位满。这里只判实际保留、缺失、错误context或unknown，不为遗漏代填预算原因，也不建议放宽预算。源码trace应逐原单元→carrier→fact/measure/purpose/eligible/score→实际planner item，再检查citation view。

JSON逐目标保存精确span、locator、group/citation context、主体/分母/单位/模态判据和收入信息风险；保留旧B及中间版回退，未新增或改写验收目标。ROOT单行types注解可能改变代码hash，本报告绑定内容hash，不能替代新代码实际执行证明。

JSON SHA-256：`403b75cfd240d0ebeeb1ca83e17640cc10424a8f23679c8c16d0e1c06a065d46`。
