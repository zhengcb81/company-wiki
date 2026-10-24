# 当前主线循环目标

**执行状态：用户2026-10-23“继续”已恢复，原生目标active。以CURRENT_STATUS为唯一入口，目标正文/累计预算保留，整体未完成。**

## 原生目标正文

以 company-wiki/docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md/json 和 MAINLINE_LOOP_GOAL.md 为唯一主线入口，持续完成新版 revenue-forecast-audit 八步循环。先接收药明康德 final3 四路复审共因PWF，按W08–W12先写根因测试再修来源选材/上下文、研究证据/经营桥、逐文档投影和实际外部来源缺口；原公司新attempt复验后，依次药明合联、Snowflake做新公司泛化。每轮真实执行RF、四路独立审查、共因方案与实施、再验收、代码/模块化/泛化及买方收入研究质量改善、基于新问题提升检测并验证正反例和实际采用。承接旧PWF/NVDA及阿里巴巴、小米集团、药明生物、药明康德、药明合联、微软、Snowflake、MongoDB清单的未完责任；固定清单和责任包闭环后，同一有效版本连续三家不同公司无主要问题才完成。重大外部阻塞不算通过。保留原文与封存历史，遵守配置及最新累计10M tokens/$20（含unknown，公司软目标）；不修改Dayu/IQS他人施工，不加人工许可/小节点门禁，不以特判或删断言换绿。独立大节点审查、隔离测试恢复，及时提交推送并更新PWF。

## 当前起点与下一步

- W03/W07 的共享引擎公开接线、一次真实摘要、激活前故障恢复、缓存及RF消费已有工程验收，不重复收费重做。
- 药明康德 final3 的四份报告均已完成，14个问题出现项归并到10个根因、W08–W12五张卡。旧报告、639件初始封存及501件final3封存均保留。
- 共因方案位于 `C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/remediation/r1-final3-review-20261022/`，诊断与交接位于同run的 `diagnosis/r1-final3-review-20261022/`。
- ROOT新attempt保留。W08共享原生观察/跨页/订单/逐target依赖已真实合线推送`f2b8f2bf`，独审17P、精确CI40050949303成功；诊断合同`87a14a86`及选择兼容修复`584c1101`均正常推送且精确CI成功。最新DTO/cache根修`baa77ab6`和clean Phase C端到端测试根修`aade6b93`已推送；pre-push完整单测8126P/24既有skip（389.84秒）、契约smoke146P、聚焦与集成170P、Ruff及mypy src 372文件全过；精确CI40076059766 completed/success。W11-CWP-SOURCES A/B/C已完成推送并关闭施工卡，真实业务IR材料仍有独立的内容验收缺口。W08年度14项目标仍7pass/5partial/2missing；下一步逐项定位有界选材/上下文缺口，之后再做正式摘要、cache恢复、RF实际采用矩阵及W12四审。具体状态以唯一CURRENT_STATUS为准。
- W08负责CWP来源语义/结构，W09负责RF研究输入与方法，W10负责audit逐文档结果投影；目录不重叠部分可并行，共享接口和技能卡由ROOT串行整合。W11有界恢复实际来源缺口；W12整合、原公司复验、泛化和质量/检测收尾。
- [2026-10-24三包](harness_lanes/20261024/README.md)已准备就绪：W13独占CWP测试调度/hook、W14独占RF离线E2E、W15独占Audit工程证据移位；尚未派发/实施。ROOT继续annual14/正式摘要/cache/真实矩阵/W12，不同时改委派文件。包内独立agent最终审查及问题修复是交付条件，不新增逐小步人工许可。

## 每轮的八步

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

2026-10-23用户明确授权预算制度升级为累计10M tokens/USD20、公司软目标；旧2M文字是历史授权，不能继续用作当前硬门。当前单一策略config/resource_budget.yaml，历史费用/unknown全保留。当前母级外部调用账仍为1,561,352 tokens/$0.631959，剩8,438,648 tokens/$19.368041；包含历史unknown hold，以实际原生账为准。本机实际回读显示更新目标后保留原应用目标的使用计数（77,576,348 tokens / 238,440秒）；不据文档中的一般说明假设已清零。**项目的模型费用、token累计账和历史责任均不重置**；目标修改前后回读保留在本计划review收据。

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
