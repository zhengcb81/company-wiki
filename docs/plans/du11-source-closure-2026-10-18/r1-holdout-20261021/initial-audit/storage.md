# 药明康德 initial — 独立 storage 审查

结论：FAIL，initial 执行仍为 partial。检查：PASS 9, FAIL 4, BLOCKED 3, NOT_RUN 1, N/A 1。executor_completion=partial；不是执行成功或预测质量认证。

封存manifest SHA：`ee08753799d7d2a849dd3fd9c811e7c0e83d20d7538f978218245fdf98dca458`。639个封存工件实读SHA均一致。正式预测SHA：`21ac4e6c9a409b90a1b43fc03d13dd0b9341ba04e0bdedfd9486f72abcf31c96`，Markdown `a4d72d4121a7211d6fe398b8955a4e6743bc249dfe935ffdd9e42021c8d10fab`，snapshot `e76203552a4f1c5c5f45a223976170cccb40a39ce28c14c3ba224332babe487e`。

盲审于 2026-10-21T21:41:19.954718+00:00 冻结21项来源目标，canonical SHA `b1156f7d6ec06b1650aca01860f2a3d80e43e87b1f0678d24c7b0ad07442bd46`；此前没有读取summary/selection/forecast或其他reviewer初稿。候选已存在，因此不宣称冻结早于候选生成。四原件通过CWP query_ref/open_version打开且SHA匹配；原件未复制、未写入。

实际来源阅读：

- 97fb5026d6a2：共249页，完整实读PDF页 11,12,13,14,15,16,29,30,31,32,119,120；视觉复核 [13, 14]。
- 27e3508560a6：共21页，完整实读PDF页 1,2,3,4,5,6,7,8；视觉复核 [4]。
- 6d7f4c4abcf1：共201页，完整实读PDF页 11,12,13,14,15；视觉复核 []。
- c49d3d6fc2e4：共770页，完整实读PDF页 1,2,3,12,13,14,15,16,17,18,74,248,249,250,654,655,656,657,658,659,660；视觉复核 []。

年报业务/分部/风险/收入确认，Q1业务，H1业务及IPO业务/募投均实际阅读。共1241页只是机械提取，完整实读46页及另列部分摘录，未读余下UNKNOWN。另读封存请求/usage/document matrix、公开bundle/receipt、RF单一消费参数与公式引用；SQLite仅mode=ro。

|检查|状态|观察|
|---|---|---|
|S01|PASS|限已打开版本：四原件query_ref/open_version SHA及bytes均匹配，主体药明康德603259、FY2025/Q1-2026与原件一致；FY2025H1/2018IPO仅preview，publication/asof资格保持unknown且未进预测。模型主来源为2025年报，最新信息覆盖缺口另列S07。|
|S02|PASS|原件与正式摘要通过pathless SourceRef/NarrativeRef读取，消费者请求只有ID/hash与配置，物理根映射留在catalog；未见消费者按CWP/Dayu/Dropbox分支拼raw路径。|
|S03|PASS|本轮观察：四refs为四个内容SHA，CWP原件只复用，未生成新raw副本；唯一visible摘要对象按内容hash存储；cache返回同artifact和同generation。未对目录复制/损坏注入做扩展验证，不宣称全局去重正确。|
|S04|PASS|本轮0 acquisition downloads，隔离companies无新raw；8项scope配置SHA现值一致，生产配置未写穿证据与独立实测吻合。没有新增下载可审registration，原文未翻译且四原件仍可打开。|
|S05|PASS|适用格式仅文本PDF：正式年报249页、5752 source units、96 native EvidenceSpans有非空原语言文本，原件/locator回放通过。审查另用PyMuPDF读四PDF，不将审查解析冒称执行结果。HTML/IR未形成native parse链归S07；TXT/JSON/PPTX/扫描PDF/OCR未涉及，不宣称全格式通过。|
|S06|FAIL|真实执行是旧selector0.8；所读年报重要小分子管线、TIDES订单/客户、指引与风险遗漏，混入无业务价值财务碎片。体积尚小不能抵消业务内容损失。|
|S07|BLOCKED|2018IPO业务实质页已读（executor p248-263、reviewer另读募投与风险），但最新IR/JPM/演示、2026融资/股权材料未完整qualified/consumed；电话会companion被挡，无实质Q&A。不是按缺文件判N/A。|
|S08|FAIL|摘要中文原语言、source_id/locator/parser/model/prompt版本齐，9claims逐条回原件；c4实际FAIL，c1/c6 WARN，其余6PASS。9条全有自身support定位不等于每条语义正确。|
|S09|PASS|限实际窄链：p11/6 CRDMO span经公开bundle被consume_narrative_input附入RF claim narrative_crdmo_chem_2026，绑定chem_base_2026_conditional_rate=0.2并到化学base recognized_revenue公式。它只支持机制方向，数值仍是未校准analyst assumption；不能称9条DS summary都被使用。|
|S10|BLOCKED|实测唯一bundle169547bytes（原件1608226，10.54%），摘要JSON4698、selected原文UTF8 16906；隔离根31文件3615192bytes，无无限常驻全库转换。新run精确cache复用已证，三类失效和独立peak/delta未执行/观察，故完整S10不能PASS。|
|S11|NOT_RUN|单文档正常子进程/预算与outbox可观察，未知MiMo预留没有置零；受控paid-response-before-activation恢复未跑。并发竞争不在当前单文档路径观察范围，不能从一个delivered outbox推出故障恢复/并发PASS。|
|S12|PASS|上游正式产物仅来源/解析/资料摘要与只读引用；预测、假设、公式在RF audit run外部目录。未见向StockWiki写入、投资评级或private/public/逐材料许可复活；preview publication unknown属于来源asof责任，不是人工签收门。|
|S13|FAIL|已读原件高价值正文确有可提取文字；小分子项目与风险等未保留。selection部分coverage标记有披露，但没有逐遗漏业务影响/未读context追踪；本次并非opaque造成的可接受未知。未读全原件余下页面仍UNKNOWN。|
|S14|FAIL|c4跨测试/生物学分部拼接，两个support无分部heading；RF receipt citation_trace ungrouped、group_count0、reading present=false，与原件上下文不一致。真实年报期间未混成另一公司；错误是业务主体分母和阶段/context。|
|S15|BLOCKED|本轮电话会原语言TXT/JSON与Q&A没有形成；发现的是通知与blocked companion请求。无法核actor/stream/precollect/closing及question+answer保留，未执行不能判N/A或PASS。|
|S16|N/A|四个实际原件均PDF、正式subject为raw annual SourceRef，没有official JSON母页/projection路径。最新JSON/电话会未形成的任务缺口已在S07/S15列出；本轮不证明JSON投影机制正确。|
|S17|PASS|限精确generation/parent实证：DS与cache reconstruction均为ea5fe54..、设置hash及generation匹配，cache pin指向原narrative-bed3..与f0f9..对象；当前公开精确读取重验父SourceRef/96locators且SHA一致。不是跨配置失效测试（归S10），也不把MiMo b1bd..冒充DS。|
|S18|PASS|工程复用与业务recall分开：cache零新tokens/预留属工程观察；native coverage_complete=false、RF needs_review，独立来源目标揭示遗漏，均未将cache当业务召回或恢复证据。全1241页仅机械提取，实际来源阅读46完整页加部分摘录，余下UNKNOWN。|

## STORAGE-001 P1 — Initial明确执行selector 0.8.0，未执行共享阅读引擎0.9路径。

封存DS请求显式selector_version=0.8.0；正式bundle/2.0为parser0.1.1、selector0.8.0、prompt1.7.0、deepseek-flash，无reading_context。Initial pin中0.9才分派select_reading_evidence，故此结果不能验收共享阅读引擎。0.8为当时默认，但这不使共享路径变成已执行。

预期：本轮须识别真实引擎/策略/版本，若验收共享引擎，实际请求及产物应来自其路径。

原因推测：执行准备/配置路由选择了legacy selector；实际运行版本证据确定，为什么holdout选择旧策略应由专家继续定位。

建议：在新attempt显式接通当前批准的共享策略/模型投影，保留本轮历史；用同一冻结来源目标验证业务保留和主体限定，不能只改变版本断言。

证据：

- [input-0001-ed7969417204.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/executor/commands/8a277d8c72da40279ffdf8ecb26b820c/input-0001-ed7969417204.json) — /selector_version
- [current-read-and-disk-observation.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/current-read-and-disk-observation.json) — versions, reading_present
- [initial-policy-and-runtime-observation.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/initial-policy-and-runtime-observation.json) — files/0/excerpts line2494-2497; runs

## STORAGE-002 P1 — 年报选择漏掉高价值业务事实，却保留失去表头的财务/行政片段。

原件p14的小分子D&M 199.2亿元/3452分子/83商业化/91 III期、TIDES订单20.2%及客户/分子增长、513-530亿元指引均未进入96 spans；p31-32需求/监管/国际政策/汇率等主要风险也未保留。selected反而含p128整块税率、p87资产负债行及p235缺表头的终止经营数值。原件有可提取文字，非opaque；coverage_complete=false已诚实披露，但不能替代遗漏影响。

预期：S06/S13要求按业务价值保留正文与限制，财务表不能替代业务叙述；原件→选择需对照独立来源目标。

原因推测：selector0.8的候选/财务拒绝/组保留规则及预算优先级可能使业务事实和完整风险丢失；本报告确定症状，不声称已定位具体函数根因。

建议：用冻结ST-02至ST-11逐项回归：将业务/指引/风险条件与主体成组保留，减少无业务价值表片段；新共享路径仍须在真实同源样本复验。

证据：

- [blind-source-targets.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/blind-source-targets.json) — targets ST-02..ST-11
- [blind-original-1-pages.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/blind-original-1-pages.json) — pages PDF13-16,31-32
- [public-bundle.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/public-bundle.json) — evidence_spans loc:v1/page:14/*,31/*,32/*,128/*,235/*
- [summary-semantic-review.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/summary-semantic-review.json) — manual_same_target_observations ST-02..ST-11

## STORAGE-003 P1 — 正式摘要c4丢掉分部主体，把两个不同分母的“超30%”拼成一条无分部限定的结论。

c4两个support分别是原件p14测试业务和生物学业务的新分子占比；两个span均不包含(2)/(3)分部标题。c4未说明任何分部，合并了测试领先领域与生物学新客户增长，不能据此得出公司整体新分子收入占比超30%。c4 needs_review=false，实际语义FAIL。RF没有引用c4，故不编造其已经改变预测金额。

预期：每条claim须由自身support蕴含；同一主体的业务口径、阶段、期间及限定context应成组保留，不能跨组拼接。

原因推测：上游选择/摘要接口缺分部heading/context binding，加上模型合并语句；citation_trace ungrouped与缺reading_context是机制线索。

建议：保留测试/生物学各自标题及context，要求claim显式业务分母、自己support/context；再进行原件逐claim独立审查。

证据：

- [blind-original-1-pages.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/blind-original-1-pages.json) — PDF p14 (2) and (3)
- [blind-doc1-p14.png](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/blind-doc1-p14.png) — visual full page
- [public-bundle.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/public-bundle.json) — summary/draft/claims/c4; evidence_spans 521560f.. and 304e77cc..
- [summary-semantic-review.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/summary-semantic-review.json) — items claim_id=c4

## STORAGE-004 P2 — 摘要对已选择的计划/口径限定保留不足，不能把引用打开成功视为语义完整。

c1标actual却把现况CRDMO与自身support中的“将/2026”建设计划混合；c6的47.64%缺2025公司总口径，不能与持续经营48.91%或分部毛利率混用。selected p14/34的展望条件没有在9条摘要中保留，ST-07只能判遗漏。c1/c6语义WARN，不虚构数值已错。

预期：summary→own support必须区分现况/计划，并保留金额和比率的主体及期间。

原因推测：摘要生成压缩了阶段/口径，生产claim合同没有强制把相关context作为独立引用维度。

建议：新摘要将实际与计划分开，明确2025集团总口径；对指引与前提成组保留。

证据：

- [public-bundle.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/public-bundle.json) — summary/draft/claims c1,c6; selected p14/34
- [summary-semantic-review.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/summary-semantic-review.json) — items c1,c6 and ST-07

## STORAGE-005 P1 — 截至2026-10-21的重要最新资料与Q&A未形成可消费的合格来源链。

document_matrix承认2026H1被local_metadata_gap/publication_date_unknown和FF invalid_producer_schema阻塞；IR/presentation/JPM、2026融资线索已发现而未完整CWP合格。电话会仅通知/companion请求，未建立ET实质Q&A。2026Q1已合格且可打开，但未normalize/summary并未进入模型。2018IPO业务预览已读，不能替代当前融资/最新经营资料。

预期：S07要求认真读取有实质价值IR/电话会/募投；不能按本地缺文件判N/A。S15需实际问答才能核actor/stream及Q&A完整性。

原因推测：CWP元数据与FF producer边界错误和执行研究覆盖不足分别存在；没有证据支持把这些都归为外部来源不可获得。具体共同根因由fetch/编程专家定位。

建议：修复既有来源资格/接口边界，在新attempt完成已发现最新资料与原语言Q&A读取；保留明确失败状态，不用通知替代电话会，不用2018IPO替代2026经营事实。

证据：

- [document_matrix.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution/document_matrix.json) — documents semi_annual_report, quarterly_report, investor_*, strategy_communication, convertible_bond_prospectus
- [source_ledger.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution/source_ledger.json) — sources/1 normalization_result, summary_result, forecast_use
- [discovery.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution/discovery.json) — records/1,3,4
- [remaining_items.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution/remaining_items.json) — remaining/0..3

## STORAGE-006 P2 — 同代缓存复用有实证，原文/配置/generator变化失效与scratch峰值没有本轮实测。

cache new-run确实复用同artifact、零新reservations；未见原文/配置/generator版本变更的失效执行。当前磁盘测得31文件3615192 bytes，唯一bundle169547 bytes；这只是终点快照，不是峰值或baseline delta。native声称DS persistent_added554987/scratch_peak169547，cache added138/scratch0；本审查不将声明当峰值实测。

预期：S10要求实际重复run与缓存失效覆盖原文/配置/generator版本，并将实际空间与声明分开；不能凭结构或声明判通过。

原因推测：本轮执行未安排有界失效/峰值观察，属于验收证据缺口，尚无缓存错误实证。

建议：新owned fixture/run记录三类失效及当前parent拒绝，增加有界空间前后/峰值观察；不付费补做后回填initial PASS。

证据：

- [current-read-and-disk-observation.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/current-read-and-disk-observation.json) — isolated_disk_measurement
- [storage-probe.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/storage-probe.json) — derived_measured
- [stdout.txt](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/executor/commands/8a277d8c72da40279ffdf8ecb26b820c/stdout.txt) — storage
- [stdout.txt](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/executor/commands/6ffdb542e7dd46668de0471ccd70244e/stdout.txt) — storage, documents generation_status
- [remaining_items.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution/remaining_items.json) — remaining/6

## STORAGE-007 P1 — 付费响应后激活前中断恢复与并发lease竞争未在initial执行。

仅一个文档的正常worker路径，AUTO中5次attempt、一个delivered outbox；MiMo失败unknown费用预留保留、DS成功、cache零新预留均可复核。usage明确failure_after_paid_before_activation_test=not_run。既无该故障注入/恢复，也无并发worker竞争证据。不能对这些路径签PASS。

预期：S11对涉及的lease/outbox/费用恢复给实际过程证据；cache命中不证明故障恢复。

原因推测：验收场景未执行；本报告没有据此断言lease或恢复实现必然错误。

建议：在新attempt执行已授权受控中断恢复大节点，保存付费响应、激活、lease/generation/outbox、去重费用的前后状态；并发若仍不涉及应明确N/A范围。

证据：

- [usage.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution/usage.json) — cache_check/failure_after_paid_before_activation_test
- [initial-policy-and-runtime-observation.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/initial-policy-and-runtime-observation.json) — attempts,outbox_status_counts,reservations
- [remaining_items.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution/remaining_items.json) — remaining/6

## 摘要逐claim与遗漏

9条claim全部核其自身support并回原件：c4 FAIL（分部主体/30%分母丢失），c1/c6 WARN，6条PASS；不存在总分。11个年报目标逐项比较，另外10个Q1/H1/IPO目标保持独立来源范围，不能计为年报selector漏选。工具导入map、prepare output、attach-review和compare已按公开CLI形成；工具的selected-only机械包不证明全文recall，原件语义结论见[summary-semantic-review.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/roles/storage/summary-semantic-review.json)。

## 空间、费用与影响

唯一正式bundle 169547 bytes；原件1608226 bytes，比例10.54%。selected原文UTF8 16906 bytes，summary JSON4698 bytes。隔离根31文件3615192 bytes，其中security master2294033、catalog307200、AUTO684032等；不是原始资料全库盘点。native声明DS净增554987/scratch峰169547，cache净增138/scratch0，与终点实测分列。空间未见失控，遗漏与context仍失败。

DS已知6855 tokens，费用估计2992 microUSD；MiMo401有未知usage预留6728 microUSD，合计proxy/hold9720 microUSD，实际现金发票null；cache无新预留。未知没有改为0。

被selector遗漏的小分子D&M 2025收入199.2亿元，约为化学业务364.658469亿元的54.6%；TIDES 113.7亿元约31.2%。它们在同一化学分部内，不另加收入。 选择丢失下行风险和订单/管线限定，可使方向论据过于乐观；最新Q1与H1未整合还可能错失增速变化。实际未来金额偏差与净方向unknown。 RF只绑定CRDMO机制span，未引用错误c4；executor还直接读原件关键表/政策，不能把摘要漏项自动当成预测数字已错。20%是明确分析师条件假设。

## 推断、未知及复测

- 未读原件完整范围不作全面召回结论。
- 最新H1/IR/融资/实质Q&A材料资格与内容缺口。
- 三类cache invalidation及受控付费后恢复未测试。
- 终点磁盘不证明峰值/净增量。
- MiMo失败实际现金费用null，保留预算hold。
- current public reader用于打开固定initial字节，不把正在接收的后修源码当initial执行结果。

- 新attempt实际使用共享引擎批准策略/投影并保留真实engine/version/context evidence。
- 同一冻结年报目标，逐项原件→selected→summary→自身support回归，尤其ST-05/06/07/09/10和c4分部主体。
- 最新已发现材料与Q&A经现有CWP/FF公开边界完成；Q1实际进入经营证据链。
- 有界cache原文/配置/generator变化失效、当前parent拒绝及空间delta/peak。
- 已授权付费响应后激活前中断大节点；验证lease/outbox、raw response保持与预算不重复。

Initial生产代码没有被本reviewer修改；没有POST、下载、付费补做或execution写入。当前读取只证明固定initial bundle可打开；后修代码不能算首轮PASS。S16的JSON路径未涉及，其余BLOCKED/NOT_RUN均有具名finding。
