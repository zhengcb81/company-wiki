# 主线语义与收口设计复核（2026-11-02）

本报告只读核对当前源码、当前PWF和既有失败证据；没有修改产品、调用供应商、下载或重新运行公司测试。报告由ROOT独立分工的mainline_rethink agent形成。源码行号为本次读取位置，后续以所属函数为准。

## 结论

工程底座已有明显进展，但当前瓶颈是来源作用域与改写忠实度。引用字节真、材料召回和工程测试绿，不能合并推定父链正确或改写保留了限定。应在已有来源卡和任务作用域上收敛责任；不重建数据库、队列、共享SDK或微服务，也不试图用不断增加的句式正则证明任意自然语言蕴含。

## 已确认事实与待验证设计

|证据|已确认|不能推出|
|---|---|---|
|`src/company_wiki/document_understanding/structure/sections.py:467–486`，特别是476|识别新note时直接复制当前stack；既有H1独审证据有三个selected view继承旧局部标题|不能按本公司备注号或删除所有父标题修复；其他真正嵌套需保留|
|`src/company_wiki/automation/narrative_summary_assessment.py:186–200`|scope匹配使用support/context，但正文诊断逐个support span运行；未在这里联合处理context限定关系|不能仅把所有context文本拼起来就认定它们限定同一主张|
|`src/company_wiki/document_understanding/assertion_frames.py:79–146`|每个sentence重新初始化局部project/reporting状态；project_condition只附着于project_capacity_specification|现有有限句内框架不等于一般跨span条件绑定|
|`../architecture-quality-20261101/implementation-results/gate-rejection-followup-20261102/cwp-contract-followup.json`|有源合成反例“计划…建成后”＋“仍须验收后”被改写为actual，legacy/v7实际decoder无诊断|这是当前代码的真实能力缺口，尚非已证实的真实付费公司事故|
|`narrative_summary_assessment.py:216–217`|输出明确区分semantic_status=not_evaluated和no_known_violation|无已知诊断不能冒称所有语义已验证|

根因设计假设是：结构依赖与限定作用域应在一个来源owner中产生，再由选择、模型输入和解码复用。具体需要哪些字段、如何跨段绑定，仍须TDD与真实来源验证；本报告不把新DTO或任意句间传播当成已经确定的实现。

## 必须复用的现有机制

- `document_understanding/summary_tasks.py:27–45`已有SourceSummaryTask及member_ids/support_ids/context_ids。它是引用式任务，不应另建一份原文或经营事实库。
- `document_understanding/source_cards.py:24–33,96–107`已有SourceCard，完整支持材料与context引用分开；原文和locator继续权威。
- `automation/narrative_model_extractive.py:1–5,126–138`已有原话优先协议，模型仅排序，不能替换来源文字、数值或引用。它将不能证明的模态标成uncertain，不能把这种标记解释成来源无用。
- `source_catalog/official_source_flow.py:926–945`仅在新的、明确选择shared engine且没有显式projection的membership-free模板上选择quote-primary。完整旧请求、旧run恢复和显式projection保持原意；不能声称所有旧路径已经自动切换。
- `automation/narrative_model_runtime.py:48–71`已有统一request/decode协议分派，legacy/scoped/extractive实现不应再各自复制新限定规则。
- `narrative_summary_assessment.py:47–66`已有实现身份依赖，付费response和恢复另有现有owner。改变限定绑定应纳入既有recipe/cache身份，已存response可本地重解码，不能用重复POST掩盖问题。
- 边界分工审查已确认RF/Stock接受正常uncertain/needs_review来源并传播质量；不存在需要另开卡修复的“一律拒绝unknown”问题。详见本目录boundaries.md。

## 有界整改方案

1. **结构owner负责父链与依赖。** 新peer scope关闭旧局部层级，保真正共享章/节及合法嵌套。无法证明几何或边界时保原文与不确定性，不能普遍要求bbox才准读。
2. **来源限定owner在完整task范围工作。** 保主体、时间、条件、否定、计划/实际和归属，关系必须指向原span；支持跨段但不得仅凭邻近或共享关键词借用另一主体的条件。优先扩展已有结构/断言机制，先冻结测试再决定最小表示。
3. **选择/排名只分配材料。** 优先级与配置预算决定供给范围，不因材料是计划、定性、业务目录或无增长数字而全部禁入，也不重做事实核实。
4. **派生摘要不得取代来源。** 原话卡及其限定引用为权威；显著剥条件/升级actual的改写按已有partial/diagnostic机制处理，原文继续可读。有限观察不能证明的情形保持unknown，不建人工review许可。
5. **研究判断归RF。** CWP保障来源忠实而非投资命题成立；RF承担经营解释、单位期间、假设和情景，不能让来源层替它证明经济结论。

来源卡是根本性隔离手段，不是取消用户需要的摘要。可读摘要可以继续生成，但其引用、限定与模型推断必须分清；不能把“改写看起来流畅”放在资料真实性之上。

## 关键路径及完成标准

1. 冻结T4与SEM-QUAL-01同组去公司化正反例：同级note、真正上级、嵌套note、跨段条件、条件已满足、独立主体、中英文、否定。当前失败须保持可复现。
2. 在结构/限定owner实现；legacy与current薄复用。单元验证边界，集成必须走normalize/select→实际model-input→decode，而不只测正则。正确actual不得误降级，未知材料与可选诊断不得整篇阻断。
3. 一次来源大节点独审；单H1保持既有90s/16M/112配置复验，旧标题污染消失且原12重点和真实限定保留。计数是原运行条件/观察，不能又变成任意内容许可。
4. 汇合RF/AUDIT修改后按当前真实配置完成新摘要→prepared中断→同/跨run零重复POST→同artifact实际RF参数/公式/报告/snapshot；一次真实链大节点独审。历史有界通过不能代本次新版真实验收。
5. 回原公司及固定公司循环。主要错误继续修；不影响当前正确性的P3/可选优化进维护队列，不每个都重开主里程碑。不能以小样本全绿宣称自然语言全部情形正确。

长期未完成的原因不是没有组件，而是交付单位偏向包/文件，关键链终点没有同时闭合；旧有界验收与新runtime、来源召回与改写/研究质量曾被混读。下一验收单位应是“同一新来源材料可靠进入实际RF报告，并且恢复不重复付费”。

## 有意义的并行边界

- ROOT/CWP：T4来源父链与限定、已确认入口/入库预算遗漏，拥有来源集成关键路径。
- RF：既有R4公式kind/input互斥、同口径期间补集、证据采用与本仓测试；只消费公开DTO，不自行重做PDF树或修改CWP。
- AUDIT：风险检查与正反例、attempt绑定、native/observer/质量分离；先用固定公开fixture，最终接ROOT真实run。独审是交付检查，不是每次正常运行许可。
- FF/ET只有确认的采集至最终入库预算不一致需处理；Stock/存储没有新阻塞就不为了凑并行数量开任务。

各仓PWF负责本仓实现/测试，ROOT只持有接口、依赖、交付commit和两大组合验收。局部工作可并行，但新摘要与实际RF采用之间的因果依赖不能消除。

## 额外上帽观察

只读确认`official_source_flow.py:241–251,778–779`仍含128MiB/300s静态上帽，限制显式资源参数；这是读取/导入前第二约束，不是已经产生结果被后置拒绝，具体复现及处置归rectification.md。

`summary_tasks.py:151–154`仍限制citation_views最多2；目前仅角色/协议兼容候选，尚未证明它超出了真实双角色不变量。不能仅见数字就删除或宣布已修。
