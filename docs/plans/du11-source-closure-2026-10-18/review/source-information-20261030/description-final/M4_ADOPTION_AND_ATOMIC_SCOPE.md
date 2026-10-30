# M4 后续：单条摘要限定与真实 RF 采用

唯一总入口仍为本计划 CURRENT_STATUS.md/json。本文件补充 SUMMARY_QUALITY_IMPLEMENTATION.md，不建立第二目标或执行队列。M3b工程已发布 ee27c962；真实 `/6` v1、消费者零付费重放和自然语言独审分别保留，不能互相代签。

2026-10-30 本轮明确冻结的新recipe为 `/7`、prompt `reading-source-scoped/4.3.0`、request `/8`、decoder `/7`、assessor `source-summary-assessment/1.1.0`；仍复用bundle2.1/3.1、producer1.1、wrapper2，不因语义行为新增无关字段版本。1.1新增assertion_frames依赖（共8），新有限规则为possible_current_action_as_future、possible_project_capacity_basis_loss，归属扩展仍possible_attribution_loss。旧 `/6`、prompt4.2、assessor1.0/7依赖/旧规则保持严格配对；生产默认仍 `/4`。这是工程实施的明确接口，不代表已通过真实新摘要或RF预测采用。

## 已经明确的根因

1. 原始来源可用不代表摘要完整。M2共享准入已恢复客户链、已售清单、已开发数量；新摘要显式覆盖8任务，实际20条。子事实和语义仍须看独审，任务8/8不是全文召回。
2. 段落有完整限定不等于每条拆分摘要仍有完整限定。来源报道前提、联系对象、否定程度、条件和项目阶段可能跨并列分句；模型拆句时会丢作用域。另当前进行的经营活动不能仅因语气积极而标为未来计划，项目包含产能不能当成已投产或已出货。以真实逐条独审判定确定错误和风险，不能把所有潜在风险夸大成编造。
3. 实际摘要使用与原文引用是两件事。RF现有 `consume_narrative_input` 只绑定原文span→RF evidence claim→used parameter/formula；M3只是保留assessment，没有选择摘要claim。没有真实本公司native输入，不能改名fixture、其他公司模型或添加无经济作用参数来签实际采用。
4. 工具mock原先只模拟返回成功，漏掉真实RF candidate下载次数的int合同；真实v1因此整体FAIL。已补真实RF纯validator的正确0/六种错误形状，以及mock边界精确类型。费用、失败、清理记录不可改写，修后同一bundle正文在新临时湖通过公开store/reader零付费重放。

## 节点一：原子命题的限定与状态

先固定中英及繁体中性正反例，再改共享owner，不加公司名、产品名或本样本句子的特殊分支：

- 当前进行、已完成、未来意向、条件未来、否定分别作为测试轴；“积极开发”“持续完善”没有未来词时不自动变为planned；“计划完成率”“已将”不制造未来动作。
- 报道/据第三方信息的作用域覆盖受其支配的并列命题，但不向后续独立回答、其他主体或另一段捐限定。单条摘要独立被选用时，应保留本命题的归属及必要交易/合作对象；不得只靠上一条补足。
- 建设已启动、项目设计/拟建能力、已投产能力、实际产量/销量分开。合法描述“项目包含产能”不等于伪造投产，但数值采用必须保留阶段与条件，不能当已有出货。
- 继续检查否定的程度、已售集合与已研发集合、主体/子公司/客户角色。不得为了单一模态把关键上下文删掉，也不得为了独立成句新增原文没有的合作或收入。

责任：来源命题及上下文作用域由CWP共享解析/任务编译层描述；模型提示和有界输出解码由现有scoped引擎负责；RF只消费版本化事实及其限定，不再解析PDF或用另一套来源准入算法。

source frames是保守的派生提示，字段须明确是规范化matching视图，不是原文quote/字符locator；原文span与引用闭包保持权威。未知语法保留原输入、提示留空，不能因为没有frame而丢弃重要业务任务或新增准入门。送模型时绑定既有source_key与段内序号，只发必要标记，不复制每个分句全文。程序限定诊断保持possible；不得把它升级为研究结论或人审许可。

先调查当前 `_local_risk_diagnostics`、任务编译及claim-role owner如何表达上述作用域；有限规则只能报告possible，不得改称通用NLI。需要新增提示/物料表达时，采用明确recipe与协议注册，保留 `/4`、`/5`、已录制 `/6` 原始wire及读取能力；不要在多个消费者继续复制单一prompt常量，也不要给历史paid回复重打标签。旧assessment算法的解释不可静默改变，新增诊断必须有明确版本/回放边界。

用已捕获回复先做离线负对照定位。只有请求/语义行为确有改进才进行一个配置内有界新生成；不能为验收工具错误、读取错误或文件清理问题重付模型费用。关键节点独审一次，修完同范围复审，不扩展小节点签收。

## 节点二：RF 窄摘要采用链（TDD）

参考本目录下真实节点归档的 rf-actual-adoption-design.md。实施归RF仓现有消费owner及一个必要的纯lineage helper，不新建数据库、研究引擎或权限流程。

拟采用现有consumption receipt可选 `summary_use`（明确 `revenue-summary-use/1`），旧span binding和旧receipt保持兼容。精确字段在RED测试中先冻结：实际NarrativeRef/artifact SHA、被选择的summary claim ID/canonical hash、原文support/context引用、modality/claim_type/quality、真实研究处理理由、RF evidence claim ID、parameter ID和native formula refs。不要让caller自行提供并冒充已读的摘要文本或hash。

程序从同一次正式读取得claim和source-owned引用闭包；所选摘要必须属于该artifact、支持须能在对应原文引用中核对，context不能当主支持。RF evidence excerpt仍写原文，摘要改写只放lineage/研究rationale；不把它标为原文quote。partial/needs_review/semantic not_evaluated在receipt中保留，不新增人审许可。

RED反例至少覆盖：不存在/重复/错artifact摘要ID；摘要hash错配；支持与上下文互换；错parent；仅read被标used；没有真实used parameter或formula；质量洗白；摘要改写冒充原文excerpt；caller输入不变和旧binding兼容。不要机械堆测试数量，同一公共行为用参数化正负对照。

## 节点三：真实公司采用与验收

1. 优先查找并核对本公司的真实研究输入；没有则按RF正式技能研究，历史数字从对应金融数据层/已核原件获取，不从这张IR表编出完整财务模型。收入驱动、销量、价格、利用率和情景假设必须分别给来源或明确研究假设及依据。
2. 研究者真实选择适用摘要，核回原文，说明它是数值事实、方向支持、约束/反证还是暂不量化的信息。研发化合物数不是收入，设计能力不是销量，集团联系意向不是上市公司订单。不能把20条都机械塞入参数。
3. 经正式consume owner形成原文claim和摘要采用lineage，目标必须是本公司实际模型中有经济含义的used parameter。只有原文采用/只读context的结果保持其准确名称。
4. 用既有 `lint_input.py`、`fix_hashes.py --check`、`revenue_forecast.py --validate-only`，再原native forecast、support diagnostics、snapshot与必要sensitivity。publication registry指向自有测试/研究运行目录；不用第二计算器。验证币种、单位、期间、收入确认、情景和证据，保留不确定性。
5. 大节点独审来源/限定、真正研究采用及公式影响。结构依赖非空不能独自证明参数幅度合理；不为了制造变化而随意调整百分比。完整公司八步/跨市场holdout另列，不把本局部开发样本冒签它们。

## 存储、复现与发布

原件只读且不复制，测试湖由context manager清理。保留紧凑实际输入/最终回复/正式bundle压缩件、命令/usage/质量/独审和清理收据；不用整个AUTO DB、原PDF或SDK副本。母账及未知费用保留，沿用真实Config，不增加额度或许可。

代码节点相关unit/integration/type/lint通过并独审后正常commit/push，观察精确CI；真实节点单独归档并更新CURRENT_STATUS。真实内容/采用尚未通过前，生产默认保持历史协议；没有新人工签收链。
