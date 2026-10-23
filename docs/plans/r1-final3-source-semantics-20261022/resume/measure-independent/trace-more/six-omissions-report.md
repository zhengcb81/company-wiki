# 六项遗漏：实际链路只读诊断

结论：六项已追到实际载体、资格、预算闭包和上下文。当前不是全内容PASS。预算原因来自各目标真实key的诊断，不以总计budget_full代签。

两次public reader重放分别读取同一1,608,226字节原件，共3,216,452字节，0副本。第二次仅补首轮未捕获的非目标项目标题anchor。两次选中证据canonicalSHA均为 `853df4608ea21aa5821458d755f2d130acbd57a316c3280546cc575a9a4e7127`，context均为 `c5ab4bd4d1ede34a94144503acaacfd3246df06e9b49f06df05d89c57404561c`，与candidate-shared-owner-full完全一致。每次配置/DB前后SHA均未变。

实际249页/5647原units，96 spans/8156chars，work7,304,116/16M未耗尽。candidate counter1509不等于实际预算项：planner收到484项，其中最终51个meaningful anchors加45个context占满96。没有description anchor入选。

| 项目 | 原始→载体 | 意义/实际预算链 |
|---|---|---|
| 42万/310 | p13/24、25→p13/23 chars1211–1300；原文两个分母都在同native carrier | eligible true、score3、meaningful、core_business、priority2；闭包5，末新增2span/94chars，含Chemistry父级。未pop，逐key budget_full。 |
| 小分子4000kL | p12/28与p14/10；后者→p14/8 chars302–395 | p12属于m123，唯一anchor是p12/22泛标题；标题eligiblefalse且is_heading被拒，正文无candidate/offer，p12/28事实cache未产生。p14 carrier eligiblefalse/score0，仅operating_metrics角色放行成description；闭包3、末新增1/93，逐key budget_full。 |
| 安评4.6% | p14/19自身原unit | eligiblefalse/score0/purposeunknown，角色放行description；Testing父级已在闭包，闭包5末新增1/35；未pop，逐key budget_full。不是用Testing4.7%替代。 |
| guidance及条件 | p14/32→chars1168–1257；条件p14/34独立risk卡 | 两卡均eligibletrue/score3/meaningful/core_business/priority2；各闭包3、末新增各1span(89/155chars)，逐key budget_full。两闭包互不包含对方。guidance缓存relation是issuer actual/current business_scope，未表示forecast；条件antecedent窗口虽看到guidance，required边未生成。均未sent，不指控错summary。 |
| Sep及多肽100000L | p12/29、30属于m124 | 共享analysis:p29+p30 eligibletrue/quantified_operating_status/score3；仅p29为anchor，p30是context_only无独立offer。闭包还强带p12/31、32两个一般未来段，共4span/174chars全新增；priority1但未pop，逐key budget_full。L与小分子kL不能混。 |
| Biology引流20% | p14/27→p14/26 chars919–997 | eligibletrue/operating_description_unknown/score3/meaningful/core_business/priority2；闭包5末新增1/78，包含Biology自父级；未pop，逐key budget_full。不是Biology30%收入指标。 |

所有目标完整闭包的重复标记为false。不能归因于semantic去重。core_business最终41 visits；真实policy先value、新颖度、平均visits，再priority、重复、score、边际span、来源序。这里目标均未实际pop，因96满时直接给remaining登记逐key budget_full；trace中actual_rank=null必须保持，不能伪造“第几名”或把末态访问数称为当时出价。

## 共用根因与中性RED设计

1. **项目首anchor遮蔽正文**：`_prose_reading_packages:372–395`保留project首anchor，`_candidates:699–751`仅审这些anchor，`_admitted:80–81`拒绝非事实heading后，m123整包正文失去候选入口。中性RED：泛项目标题下两段独立且完整的设备交付/产能事实，不得因标题无事实丢掉正文；另一段一般未来计划不应无来源依赖地提高完整成本。保持原ID与成本。
2. **经营measure资格缺口**：本地总体积“已提升至超…kL”和自名业务收入“同比增长…%”没有meaningful关系，降为description。中性RED可换行业/数字（如设备总体积8200kL、支持服务收入+6.3%），配ID/日期/货币/公司总数/错主体/假设/未知负控；保留单位与同比基数，不能让未来数量变当前。
3. **粗主题竞争与包成本**：R/Biology/指引/条件/多肽都折为core_business score3，未提供各自数量/客户引流/产能/预测维度，且项目包有额外通用context成本。这是本次实际排序条件；在没有有限覆盖合同前，不能宣称每个漏项都必须塞进96。中性RED应验证独立来源scope/关系类型在metadata和闭包中的区分，再测试等成本泛描述竞争；不加企业、数字、oracle保留席位。
4. **预测与限定未闭合**：范围指引与紧随其后的限定分卡，实际缺依赖，预测card中缓存actual/current关系。中性RED：其他公司的下一年收入范围、持续业务增长与局部明确前提/非承诺段，验证forecast/conditional归属及tight-cap闭包；邻近无关风险不得附会。原文与单位不改。

详细target原UID、material UID、cached fact/relations、profile、完整包、闭包成员及实际key diagnostics均保存在trace-more-v2.json；无withheld target。p12/28未被实际审过，报告不会用单独文本猜测其fact替代真实链。

未修改production、ROOT tests、W09/W11、原件或Git；无模型/下载；脚本仅观察返回值与planner真实locals。观察脚本与源码SHA、前后完整性、实际退出在JSON/stdout。中性RED仅建议，未声称已经执行。
