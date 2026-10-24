# 跨市场/文种阅读策略独立审查

审查人：`/root/w08_reporting_rule_review`。结论：**现有共享引擎＋单一策略注册表方向成立；已证实三处局部配置/金标问题，应先修并测实际效果。其余是明确的行为验收缺口，不能写成生产已经失败或已经覆盖。** 本审查仅写本目录，未改产品、母PWF、其他施工区，未下载、未调用模型。

## 证据与接线

已读本子计划的 findings、sample_matrix、task_scope、targeted-reading 及后补 business-reading-supplement；读 installed `reading_catalog.json`、`registry.py`、`strategy_binding.py`、`narrative_model_scoped.py` 和 legacy `_reading_model_context`。独立重新读取 TAL 20-F HTML 与微软电话会 TXT 两份原件并验证 SHA；其余市场引用 ROOT 冻结的有界真实页段，不能称本审查重新通读13份原件。两份原件前后SHA不变。

接线确实存在：registry 按实际 family/form 选择 section_rules、reading_questions、context_requirements、negative_hints，并计算内容摘要；strategy binding 将这些内容绑定到实际单元；`build_scoped_request` 在真正请求中携带 `reading_strategy`。因此不能把问题解释成“需要再写24个skill”或“目前没有路由器”。profile负责识别/章节/关注点，正文归属、表头脚注、问答边界、说话人、事实/预测与时间作用域由共享引擎负责。

`policy_probes.py` 实际调用当前生产 `_match_rule`，结果在 `probes.json`。这是策略匹配探针，不是完整selector、模型请求或摘要的端到端验收。首次探针因review脚本错误地用固定祖先下标定位项目而失败，改为寻找已有pyproject祖先后成功；没有修改任何产品文件。

## 已证实的问题

### MP-01：20-F 的真实风险章节层级未声明

TAL原件确有 `Item 3. Key Information` → `D. Risk Factors`；当前 `sec_20f` 风险规则只声明单层 `Item 3D. Risk Factors`、`Item 3D Risk Factors`、`Item 3. Risk Factors`。生产匹配探针对真实两层路径返回无规则，而同源 `Item 4. Information on the Company` → `B. Business Overview` 返回 business/priority1。20-F的Item7没有被误配为MD&A，10-K的Item7正常匹配 management_discussion，须保留这两个反控。

最小修复归profile：保留现有单层写法，增加真实两层风险路径；不要把“Item3”全局重写为risk，不按公司名分支。配置还将 `C. Industry Overview` 作为行业别名，但TAL同级真实标题是 `C. Organizational Structure`，应防止把组织架构误认行业；行业、竞争与监管可以在B.Business Overview内部，不要求所有20-F有独立C行业章节。`Item17`财表变体当前也不匹配，但本轮TAL观察不能证明该变体的真实业务召回问题；将其作为缺样/后续覆盖项，不能据此先扩大解析所有财务附注。

### MP-02：旧电话会金标错误地把条件口径扩大为全部增速CC

`case-earnings-call-roles-01.json` 的u3备注和f2.must_preserve称“后续所有增长率/全部增长率”适用constant currency。原TXT130说：默认同比，另在可得时提供constant-currency增速；132说：**当两者相同**只报一个增长率。后者不等于所有增速均为CC，更不等于删掉reported与CC的区别。原件128–134的真实说话人是Jonathan Neilson；旧case把132归为“投资者关系（开场声明）”合理，错误在口径解释。

最小修复首先归评测/源上下文：按原130和132共同冻结条件；不把现有错误must_preserve沿用为回归真理。共享引擎应传递限定的适用范围，profile只要求保留原始同比、reported/CC、当可得/当相同时等约定。最小行为反控：提供reported与CC不同的本地事实时必须保留两种数；相同时允许一数且带真实约定；不得把CC换称GAAP。该审查未测生产是否已发生这一数字幻觉，只证实旧金标语义错误。

### MP-03：港股中报期后标题的中英策略不对称

ROOT冻结的真实名创p19英文标题是 `RECENT DEVELOPMENTS AFTER THE REPORTING PERIOD`，中文为`報告期後的近期發展`。当前匹配探针中文得到outlook/priority1、英文无规则。应为同一scope补实际英文别名并测试两种语言各自独立出现的情况。整段可能从Business Review父级继承有效角色，因此此结果**不证明**整段未被选到。

期后已完成战略融资属于报告期后的actual，下一段H2经营展望属于planned/forecast；不能因为都进入outlook章节而把二者统一为未来计划，或把融资归入上半年经营事实。这部分时间/语态关系由共享作用域承担，profile补别名无法单独保证正确。

## 必须用行为验收的集中改进

| 最小包 | profile责任 | 共享引擎责任 | 用现DU-BENCH/生产请求检验的正反例 |
|---|---|---|---|
| T01 20-F/10-K章节 | 修MP-01；按真实form保留Item4/5与Item1/7不同路径 | DOM标题/目录/交叉引用不混；无真实正文不宣布已读 | TAL业务正文与Item5真实经营驱动被选且进入请求；TOC、尾部“see Item4”不冒充业务正文；Item7股东章节不变MD&A；10-K对照仍通过 |
| T02 港股双语/期后 | 修MP-03；保留周期/经营指标口径问题 | 双栏顺序、表头/脚注依赖、同一事实双语对应、事件时点 | 同一GMV人民币16.7billion/167亿元不是两次增量或两份收入；门店mode×region×date随数值；融资actual且postperiod、H2计划planned；英文/中文单独抽取均能保留限定；语言版本数值不同时不能静默去重 |
| T03 IPO行业/募投 | 沿现prospectus/offering策略保留发行时点、第三方、项目条件 | 原作者归属、historical forecast、项目/期间/行脚注 | 名创p193顾问预测不变公司实绩，GMV不变收入；p400–401募资基准、36–48月、门店模式、地域、疫情假设随对应行；中微IPO/金禾/恒锋的原有产能、募投新增、预测收入和现时实际收入保持分开 |
| T04 IR完整Q+A | 沿现investor_qa_record策略，不按“无重大信息/无附件”跳过 | 跨页问答/追问、否认与问题假设、主体关系 | 万润p5Q13的“10以上收益”本身无明确单位，不能补写10%或公司目标；回答仅支撑已销售产品、300余化合物、拟建751吨/年；p6意向书与实际销售并列；硫化锂6月底是计划中试，不能改量产；父公司联系不等于上市公司签单 |
| T05 电话会角色/限定 | 沿现earnings_call_transcript，避免另建ET解析器 | 参与人映射、continuation turn、编辑/Operator边界、限定范围 | 236提问与238–248多段回答/CFO补充完整绑定；无speaker前缀续段不能改成编辑；前部takeaways与334之后LLM/持仓免责声明不能成为管理层发言；MP-02修正后的CC正反例实际出现在请求和摘要 |
| T06 A股年报/中报产品阶段 | 沿现annual/interim，强调产品/阶段和H1/期后/H2 | 相同产品不同代次绑定、目标与完成状态、跨段条件 | 中微年报/中报的已验证、重复订单、将送样、下半年及五年目标按产品分别保留；研发投入非销售；收购已完成与未来覆盖目标不合并；不得用扩大片段/预算上限换召回 |

以上每包都应先冻结业务命题与排除命题，再对当前同版本跑：真实route与policy组件→候选/admission→依赖上下文→实际scoped请求support/context parts→摘要与证据→第二次缓存恢复。只在大节点审查；不新增逐段人工签收、财务数字全量切片、独立路由器或新的任务库。缺上下文应据实标unknown/partial或保留带限制资料，不能扩大为人工许可流程。

## 覆盖边界与交付建议

catalog的evidence_status/design与case_ids是声明，不是本次生产效果收据。旧20-F case明确not_evaluated业务正文，旧电话会case也明确未验全部问答。ROOT补读的业务窗口解决了最初调查缺口，但仍需冻结新命题并跑实际请求，不能把补读当召回通过。

优先做MP-02金标校正、MP-01/03局部策略修复及T01/T05行为回归，再合并T02–T04/T06的既有共享能力证据；实际失败才改对应源/结构层。S-1/F-1/424B4仍无真实绑定，US真正H1/6-K附件、港股真实电话会/IR和金融/地产结构仍缺样，应如实标缺口，不拿synthetic或单季10-Q冒充。已用于调规则的这些样本都只能算regression；最后另选公司/布局作为未调规则holdout。

本审查没有运行完整selector、收费摘要、四路RF审查或内容缓存端到端，因此不签发“跨市场文种策略生产全面通过”。当前可签发的只有：接线源码检查、8个策略matcher观察、两份原件SHA核验以及具体修复/行为测试建议。
