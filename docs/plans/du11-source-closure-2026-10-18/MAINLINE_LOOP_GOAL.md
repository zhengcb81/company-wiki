# 当前主线循环目标
## 2026-10-25 当前增量：来源复评与CI跟进

最新独立来源/实际输入评分12PASS/2PARTIAL/0MISSING，绑定06c及attempt05，见[报告](review/annual14-local-flow-regrade-20261025/report.md)。A01/A05已补齐，A02/A13精确财务仍由完整来源/金融层及RF实际采用承担。06c精确CI40190090649六项失败已原样复现；共因修复后218项通过/16.45秒、生成链check/Ruff通过，最终独审已PASS，待正常提交推送及新精确CI，旧CI不能记绿。下一步唯一动作是完成这一发布节点，再用其他市场/文种真实样本验证及运行配置内正式摘要/cache/RF。三外包工区不写；模型响应NOT_REVIEWED、RF OPEN。

**执行状态：用户2026-10-23“继续”已恢复，原生目标active。以CURRENT_STATUS为唯一入口，目标正文/累计预算保留，整体未完成。**

## 原生目标正文

以 company-wiki/docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md/json 和 MAINLINE_LOOP_GOAL.md 为唯一主线入口，持续完成新版 revenue-forecast-audit 八步循环。先接收药明康德 final3 四路复审共因PWF，按W08–W12先写根因测试再修来源选材/上下文、研究证据/经营桥、逐文档投影和实际外部来源缺口；原公司新attempt复验后，依次药明合联、Snowflake做新公司泛化。每轮真实执行RF、四路独立审查、共因方案与实施、再验收、代码/模块化/泛化及买方收入研究质量改善、基于新问题提升检测并验证正反例和实际采用。承接旧PWF/NVDA及阿里巴巴、小米集团、药明生物、药明康德、药明合联、微软、Snowflake、MongoDB清单的未完责任；固定清单和责任包闭环后，同一有效版本连续三家不同公司无主要问题才完成。重大外部阻塞不算通过。保留原文与封存历史，遵守配置及最新累计10M tokens/$20（含unknown，公司软目标）；不修改Dayu/IQS他人施工，不加人工许可/小节点门禁，不以特判或删断言换绿。独立大节点审查、隔离测试恢复，及时提交推送并更新PWF。

## 2026-10-25 当前并行安排

主目标继续active；唯一当前行动见CURRENT_STATUS及task_plan。ST-A13/01/03/09来源工程已发布；独立来源/实际模型输入最新12PASS/2PARTIAL/0MISSING，旧10/4和8/6报告单独保留。纯文档push效率根修1171aa6f已推送且精确CI成功。A01/A05列表/页码组件206项已发布；后续局部流、lane正证、上下文与预算共因已完成，集中339P/6既有skip、补58P（重叠），最终独审PASS。真实attempt05的DM/TIDES各自实际task已含Chemistry父级/报告期，旧10PASS/A13保持，112span/9060字符/62task/13.45M of16M；整体partial不改，正式响应和当前RF仍OPEN。本节点06c1a583已推送，精确CI40190090649进行中，独立来源重评已启动；再正式摘要/cache/RF/W12。下方早先节点不能覆盖CURRENT_STATUS。

新的[W16/W17/W18三卡](harness_lanes/20261025/README.md)由用户确认全部发出，等待作者交接；不是READY_NOT_DISPATCHED，不臆测作者实现已完成。ROOT负责CWP生产路径及最终真实摘要/cache/公司四审；W16负责RF历史基数口径、W17负责Audit覆盖观察、W18只负责新源侧gold/冻结测试，不并发修改ROOT生产源码。所有分包交付后仍须ROOT集成和实际公司内容验收，完成条件和预算不变。

## 历史起点与循环步骤（2026-10-25早先快照，不覆盖CURRENT_STATUS）

- W03/W07共享引擎接线、真实摘要链、激活恢复、缓存与RF只读消费工程验收已完成；它们不代签当前内容质量。
- 药明康德 final3 四路复审已形成W08–W12共因计划。W08最新来源复核为8通过、6部分、0缺失；明确未完成项是Chemistry父级范围、表格表头及持续/终止口径、客户母公司所在地定义、多肽日期与容量局部关联、时段金额与业务归属。报告见review/r1-w08-material-value-20261024/content-review/report.md，依赖根因见review/r1-w08-material-value-20261024/next-dependency-plan.md。
- Microsoft FY2025 10-K v4零费用预检的112个入选片段支持8/8冻结必需业务事实；正式付费运行仍是旧v5排名路径，43条claim全部uncertain/needs_review，RF未消费。不能把候选省略数、未分配单元或缺bbox单独推成业务事实漏读。
- 当前先完成冻结样本的离线根因拆分：源扫描、候选选材、版面几何、source projection/task依赖、摘要语义、RF实际消费分别验。只在真实目标证据显示额外批次会补足必需事实时设计可恢复批次；不要仅抬上限或把全部候选送模型。
- selector 0.9 v4默认、付费响应持久化/零POST恢复已推送；修复提交3dc04a8的精确CI 40148571611全绿。当前工作树本地只有覆盖维度命名属性及测试/PWF差异待发布；原formal-v4收据保持不变。
- IR-REPORT-GENERATION、QA-RAG-SAFE-REBUILD、MC-OUTPUT-INTEGRITY三张独立卡均已按交接、版本绑定独审、测试和清理收据ROOT接收；作者仓和分支保持独立，未替其跨仓合并。
- 预算授权以2026-10-23用户明确批准并落入config/resource_budget.yaml的累计10,000,000 tokens / $20为准，旧目标描述里的2M文字已过期；未知费用和历史使用均保留。当前母账1,783,378 tokens / $0.724836，离线工作不新增费用。

1. 读取实际配置与累计预算，冻结公司/信息时点/版本及隔离目录。
2. 独立executor完整运行实际RF，保存可复查输入、调用、输出与失败。
3. 四个独立agent分别审来源处理、FF复用采集、RF流程数字、买方收入模型。
4. 独立专家查共用根因，区分代码、配置、研究、数据、provider和可观察性，形成PWF。
5. 按责任层TDD实施；充分验证后提交、并线、推送和定点安装。
6. 新attempt复验原公司；通用行为改变再验证未用于修复的新公司和受影响市场。
7. 全面改善本轮共享调用链的硬编码、模块化、泛化和收入研究方法，独立大节点复核。
8. 从新问题和误报改善通用检测，验证正反例、合并/退役低价值重复检查，在新有效attempt真实采用。

只读/外部限制/unknown如实记录；工程绿、引用字节真和算术对不代签业务语义或预测幅度。合法条件预测不因缺未来实测值自动违规，也不能被宣称已经经验校准。

## 完成与预算边界

2026-10-23用户明确授权预算制度升级为累计10M tokens/USD20、公司软目标；旧2M文字是历史授权，不能继续用作当前硬门。唯一运行配置为config/resource_budget.yaml，历史费用和unknown holds全部保留。当前母级账为1,783,378 tokens/$0.724836，剩8,216,622 tokens/$19.275164；此数含原有unknown holds，非供应商发票。本机实际回读曾显示更新目标后保留原应用目标使用计数，不据文档一般说明假设清零。预算授权与最新使用数分别有对应PWF与母账收据。

外部预算耗尽或资料不可获得不能算完成，继续能免费完成的诊断/实现并保留恢复入口。未完责任不能靠换公司、换版本、清空费用或声明旧目标完成逃避。抽样通过只覆盖实际版本与范围。

## 2026-10-24 当前追加节点（优先于历史状态）

源码`f2b8f2bf`已正常推送，真实合线`e09e44e1`保留`ef49ae3e`作者祖先；完整单测8056P/24既有skip/221.02s，契约smoke146P/30.52s。精确[CI40050949303](https://github.com/zhengcb81/company-wiki/actions/runs/40050949303) completed/success。原4失败、同13+原4独审17P及两处共因修复收据均保留，未改旧断言/绕hook。本轮W08诊断合同新增171项相关测试、13项端到端测试全绿，独审未发现blocker；后续回归根修已由提交`87a14a86`正常推送且精确[CI40060222913](https://github.com/zhengcb81/company-wiki/actions/runs/40060222913)成功。

逐目标offer/defer诊断合同已发布。当前按真实annual14断链继续修源层级、事件时间/指引前提闭包、低信息财务孤片与定额选材/分批；在大节点集中测试/独审，再用同一实际输出核内容。随后正式新摘要、cache恢复、W09/W10实际采用矩阵和W12四审；原公司复验后药明合联→Snowflake。

真实14内容仍3P9partial2missing，整体目标active，未标complete。

## 2026-10-24 08:00 UTC 最新发布状态

W08 DTO/cache根修`baa77ab6`与清洁Phase C测试修复`aade6b93`已正常推送；精确CI [40076059766](https://github.com/zhengcb81/company-wiki/actions/runs/40076059766) 对应 HEAD `aade6b933a065fae71a14b8baf2a3b16fcbb9bb9`，completed/success。全量pre-push 8126 passed/24既有skipped，146项契约smoke、170项聚焦/集成E2E、Ruff及全源mypy均通过。测试根因和Windows沙箱loopback限制见CURRENT_STATUS；没有调用真实模型或付费API。

用户确认W11-CWP-SOURCES A/B/C均已完成并推送，施工卡关闭。真实来源内容验收仍按独立业务证据状态处理。整体目标继续ACTIVE：先处理annual14的5项partial和2项missing，再进入正式摘要/cache恢复、实际采用矩阵与W12四审。全量pre-push约6分30秒的成本已记录，后续按计划评估测试分层，不跳过现有门禁或把未运行测试记作通过。

## 2026-10-24 当前追加：报告规则/断言修复及完整14目标链

本轮共用source-purpose工程320项独审PASS，自然2302P/11skip，Ruff/mypy373通过；cache新规则字节依赖另58P。真实年报1526候选、96/7689字符、8845814/16M、55任务，独立内容仍7P/5partial/2missing，无净改善。上一V5不再是唯一最新内容记录，最新链接见CURRENT_STATUS。基于已冻结完整14项目标链，先TDD修共享语义包排序与边际闭包竞争，保留96/48000/16M与8/4/2048；随后修业务父子和容量日期的局部依赖，合并共因后再做一次真实新选材及同14项复核。内容闭合后再正式摘要/cache、W09/W10真实采用矩阵、W12四审与新公司泛化。 此次没有模型/下载/新许可或额度提高；原件、旧历史和预算账保留。

当前下一动作按独立budget根因设计收敛：先按budget-next/analysis.md写中性RED：来源admission不等于稀缺材料value，业务scope、客户地域、合同stock与确认转换用途不能压成core_business；在source owner内细化现有value_band/topics并复用reading_plan/3，不先改planner权重或提高限额。接着修地域口径、父子业务与容量日期局部依赖；共因完成后一次真实14项复核，再正式摘要/cache、W09/W10实际采用矩阵和W12四审。 产品已commit1e5e6c1a，正常推送/精确CI另实查，不将未运行算通过。

## 2026-10-24 09:31 UTC 本节点发布收尾

报告规则/事件断言及cache依赖根修源码1e5e6c1a已随PWF推送f73afb89，正常全量pre-push8160P/24既有skip（409.50s）、146smoke（32.46s），精确CI40081962182 completed/success（09:26:32–09:31:07）。最终独审320P，真实内容等价补审仍7/5/2，不代签整体完成。下一步以CURRENT_STATUS及budget-next设计为准，先中性TDD修source价值/覆盖，再依当前完整循环推进；原件/封存/预算账/外包独占范围保留。

## 2026-10-24 source材料价值最新节点

当前真实annual14独审为8pass/6partial/0missing，A04订单/RPO/确认排程通过，A03地区收入部分，旧7pass保留，A02旧增长子事实支持回退如实记录。source value/coverage和对象断言共因已实施；指数回溯改线性token扫描，最后一般义务与客户合同类型已收敛。最终独审/发布按CURRENT_STATUS及review/r1-w08-material-value-20261024收据；正式摘要/cache、RF实际采用与W12仍OPEN。上一节点7/5/2与先写value RED均为历史，不覆盖本段。完整目标/10M+$20历史账不重置。
