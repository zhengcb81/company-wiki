# CN-688012 中微公司：独立全量审查（v2）

## 结论：PARTIAL

原文历史数据、并购口径、真实下载复用链路及正式数值工作流通过。前瞻引用与最新重要公告的覆盖仍有三组 P2 问题；生产 CWP Worker 未运行，不能签完整端到端 PASS。本审查未替执行者改 input 或签收。

## 已通过的核验

- 344 个交付文件的字节与 SHA，73 对 start/finish；16 次失败尝试保留。嵌套进程记录 84 启动、84 退出、39 spawn。
- RF→FF→CWP→SID 的真实 H1 首次下载及随后0新下载。独立再次走 RF→FF→CWP 两份 reuse_only，SourceRef v2 原件实开；annual 9,165,875B、H1 3,149,962B。两份官方网原PDF独立HTTP200实际全流SHA与本地相同。
- 年报259页、半年报210页独立提取。77/77摘录匹配；全部42参数、3历史总额、3目标、9维、6沟通类、4驱动逐条记录在 facts_full.json。6张重要表格实际渲染并视觉读表头/列/单位。
- FY2023/24/25营收6263.51358137/9065.16509769/12384.63826811百万元；equipment10527.0百万元是舍入披露。1240为售出腔数，单位收入8.489516仅混合proxy。
- CMP控制日2026-05-31，控制后至6月30日收入1.29190208百万元，64.69%持股不乘合并收入。卖方2026/27/28全年280/430/580百万元承诺不等于AMEC部分年指导；2026范围不匹配已保留。
- 独立实时读取SSE195条互动，精确公司身份过滤8条；29条预征集精确1条。8条全部原中文读完，独立响应557100B同SHA。800海外累计腔未当年度销量，厂房面积未机械换收入。
- 所有27个分部年度场景、9个公司年度场景、增长/CAGR/增量、4敏感性、4驱动分配通过。strong原input校验、Markdown精确渲染、snapshotv2、独立TEMP新CLI全JSON/MD精确相同；修复后registry audit RC0。
- 配置及SKILL的4份基线SHA未变；原件未改。审查无LLM调用/无费用，Dayu未改。

## 一次性交给原执行者修复的完整问题

### CN-01 / P2：semantic_rationale_and_residual_perimeter

九个非设备残差路径和 aftem_support 驱动仅绑定年报 p174 备件/劳务确认政策。政策证明何时确认，不能证明安装基数、需求或重复服务增长。1857.63826811m 是非设备残差，未拆出的其他业务也可能在内，不能把其全部增量归因为备件服务。

精准 claim IDs：`claim_aftermarket_revenue_low_2026`, `claim_aftermarket_revenue_low_2027`, `claim_aftermarket_revenue_low_2028`, `claim_aftermarket_revenue_base_2026`, `claim_aftermarket_revenue_base_2027`, `claim_aftermarket_revenue_base_2028`, `claim_aftermarket_revenue_high_2026`, `claim_aftermarket_revenue_high_2027`, `claim_aftermarket_revenue_high_2028`, `claim_driver_afterm_support`。

精准 parameter IDs：`aftermarket_revenue_low_2026`, `aftermarket_revenue_low_2027`, `aftermarket_revenue_low_2028`, `aftermarket_revenue_base_2026`, `aftermarket_revenue_base_2027`, `aftermarket_revenue_base_2028`, `aftermarket_revenue_high_2026`, `aftermarket_revenue_high_2027`, `aftermarket_revenue_high_2028`。

覆盖接口：`research_coverage:demand`。

复现：将以上 claims.excerpt 与独立年报 p174 完整上下文比较；对照 annual p48/p53/p65、H1 p19/p23，不把混合残差当公开纯服务分部。

改法：在新 forecast_version 中引用实际售后业务/已售设备背景，明确只是方向性支持；保留未测装机量/attach rate/服务进度的 data_gap。将驱动及叙述限定为未拆开的非设备残差，或为纯售后归因提供分部范围证据。路径可以保留透明假设，但不能把会计政策充当增长证据。

### CN-02 / P2：claim_scope_and_counterevidence_binding

客户集中度实际正确但没有对应 checked claim；WFE claim 只摘2026而节点扩展到2027/28和中国放缓；四个 contrary 节点共享 H1 p33 却同时声称客户 capex/延期；films_packaging 的摘录只涵盖薄膜，未涵盖标题中的先进封装。

精准 claim IDs：`claim_outside_wfe_reference`, `claim_driver_films_packaging`, `claim_contrary_core_etch_acceptance`, `claim_contrary_films_packaging`, `claim_contrary_afterm_support`, `claim_contrary_cmp_ramp`。

精准 parameter IDs：`equipment_units_low_2026`, `equipment_units_low_2027`, `equipment_units_low_2028`, `equipment_units_base_2026`, `equipment_units_base_2027`, `equipment_units_base_2028`, `equipment_units_high_2026`, `equipment_units_high_2027`, `equipment_units_high_2028`。

覆盖接口：`research_coverage:customers`, `research_coverage:industry_market`, `research_coverage:policy`, `research_coverage:technology`。

复现：原文 annual p219=39.99%/22.15%；SEMI 2026-07-14原文 WFE 下一段=21.8%/14.1%、区域段=China moderate；H1 p32=供应/政策等风险，p33=并购/R&D；H1 p16/17另有TSV/封装上下文。77条摘录存在不等于77条结论全部获支持。

改法：为集中度增加真实 checked 的 target-bound claims；SEMI 扩展/拆分完整年份及中国区域 claims，将区域放缓作为 equipment contrary node。按每个驱动实际适用范围拆出风险或收窄原结论；为封装补真实上下文或收窄名称。禁止仅把新引用塞到 source 列表而不绑定目标。

### CN-03 / P2：communication_coverage_overstatement

material_announcements_since_last_filing 标为 checked，但19项只读元数据；关于私募基金进展及募投项目延期的原文尚未打开。H1及9月问答不能代替这些公告。

精准 parameter IDs：`equipment_units_low_2026`, `equipment_units_low_2027`, `equipment_units_low_2028`, `equipment_units_base_2026`, `equipment_units_base_2027`, `equipment_units_base_2028`, `equipment_units_high_2026`, `equipment_units_high_2027`, `equipment_units_high_2028`。

覆盖接口：`management_communication_coverage:material_announcements_since_last_filing`。

复现：recent_announcements_receipt 明确 metadata only；原 input 的该类别结论承认 bodies 未开但 status=checked。

改法：为19条标题分别记录重要/不重要的理由，读取涉及业务或产能时间的公司官方全文（先1225582793、1225482911；1225482916区分公司公告和核查意见）。确认目标/产能是否影响年度路径后更新目标与假设；取不到则有真实失败记录并标 not_available/明确gap，不能保持全覆盖 checked。

### CN-04 / P3：source_url_timestamp_diagnostic

H1公开日已纠正为中国日期2026-08-20，source_url 的 detail 查询仍带 UTC误转的2026-08-19 16:00；provider id 与官方PDF SHA完全一致，不构成金额/身份错误。

复现：对照 independent official_pdf_current_sha_checks 与来源URL查询日期。

改法：可通过正常 source-facts 校正为实核的官方PDFURL或中国日期detailURL，保留旧收据；无需重下原件。

## 如实保留的范围缺口

本次只在TEMP确定性解析PDF，生产CWP的叙述选择/摘要Worker未跑，parser/LLM计数null仍未知；不能用raw成功替代完整初级处理成功。最新IR-DOCX/完整presentation、正式中文电话会TXT原文未取得；SSE网络问答是独立补充路线，不能冒称FF→ET中文链路成功。未来年度实绩尚未知，回测evaluate不适用。

当前65.5923 medium是runtime结构评分，历史准确率观察0；引用文字错配会使表面覆盖率高估，不能将这个分数解释为预测经济准确率。所有未来路径均是条件性分析师假设，非概率区间或公司指导。

## 修复与复查接口

原执行者按CN-01/02/03一次处理，创建新forecast_version，保留v1/v2冻结文件与旧失败记录。CN-04为来源诊断建议，原件已经相同SHA，勿重下。独立复查只检查改变的source/claim/parameter/coverage/target依赖及新版正式engine/render/snapshot/registry；不重复读取无变化全文、不重复已绿真实下载。CWP未跑/官方原文缺口仍按真实情况记录。

## 交付索引

- review.json：规定格式，包括每个技能步骤、全量事实、独立计算、精确问题范围。
- facts_full.json：161条实体/事实/参数/claim逐条记录（实际数量以review.json为准）；摘录匹配与语义支持分开。
- all_claim_original_match.json：77条原文匹配；它不是语义全PASS签收。
- independent_calculations.json / formal_independent_checks.json / independent_fresh_cli_reproduction.json：独立复算和正式重现。
- commands/index.jsonl：审查实际命令开始/结束/退出/输出SHA；失败尝试保留。
- official_pdf_current_sha_checks.json / visual_table_render_receipt.json / live_official_ir_check.json / configuration_unchanged.json：实际官方原件、视觉表格、实时问答与配置核验。

审查ownedTEMP保留供主线收尾与复查；不会删除生产原件或覆盖执行产物。
