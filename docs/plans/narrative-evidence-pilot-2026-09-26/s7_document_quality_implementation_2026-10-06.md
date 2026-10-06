# S7：真实文档选择质量改进细则

## 当前依据与责任

N5-DOCSET工具已完成MAIN实读接收；产品质量仍待改进。旧报告保持在`benchmarks/narrative_document_types/report.json`，新报告为`report-main-2026-10-06.json`：运行代码CWP c8bf461c、parser0.1.0、selector0.3.2，实际工具SHA另记在报告中。9份原件、86点全部核定位；required12/33、optional4/17、744定位全部回放、48重复span。**这些是定向标注范围的结果，不是全文覆盖率或LLM摘要质量。**

MAIN独占运行时代码、共享合同、合入与总PWF；已交DOCSET/RAW-DUP/ET不重派。RF main6e6b817a只读且每大节点先核状态；其两weekly owner文件、CWP用户source_acquisition修改不动，Dayu/IQS/StockWiki/ET零写。不新增权限/签收/第二任务库，不改变剩余模型预算或Config，不发付费请求。先完成DOCSET并线/精确CI，再按以下顺序施工。

## 已完成的实证归因

完整基准全PDF表扫描，耗时378.983秒、runner scratch峰值76302 B、精选文本合计72042 B；它不是生产默认自动表扫描。正式SourceVersionReader三份PDF E2E为默认策略，271定位回放、三个包都partial（deferred tables），无全表回退。不以full benchmark速度代表Worker速度，也不加入日常CI。

为区分候选与截断，在同一原件上作了一次限定表页的诊断：全PDF文本、只对golden已读页扫描表格，捕获既有finalize_selection输入，不改规则。记录见`harness_lanes/results/n5_docset_gap_probe_2026-10-06.json`。**诊断候选数不同于全表基准，不能混用计数。**21个required漏项中20个在parsed阶段可完整匹配；只有电话会provider highlight不在parser正文范围。5个在诊断candidate阶段完整、最终仍漏，1个candidate只有partial，其余主要缺候选/完整上下文。不能把所有漏项归因于预算太小或PDF识别差。

| 优先问题 | 真实复现点（PDF页序号从1起） | 已知结果/实施目的 |
|---|---|---|
| 中文正文及跨块上下文 | S01 G01页32、G03页40；S02 G02/G03页18、G04页31；S03 G03页3 | parsed完整，candidate不完整/缺失；保留刻蚀应用、并购业务扩展、行业景气、已投用产能和薄膜第二曲线，不靠单个词命中 |
| 固定预算下的排序 | S01 G02页40、G05页75；S05 G03页101；S06 G02/G03页43 | 诊断candidate完整但selected漏；先去重、按具体经营事件/业务章节分配，不直接扩96/160限额 |
| 募投项目上下文 | S04 G03页34、G04页49；S06 G02/G03页43、G04页87 | 资金引导句、项目名称、建成产能常分块；完整项目逻辑有价值，不能把通用融资数额当业务结论 |
| IR表格问答 | S07 G01页1；S08 G01页3 | parsed完整，但candidate漏；S07原文是境内收入约8.19亿元/占比约22%的结构变化，不是海外22%；产品组合也是业务事实；S08虽为程序性标签仍有一条事实，不得全类型skip |
| 英文需求描述 | S09 G05行200/字节32538–32593 | parsed完整，candidate漏；“需求持续超过可用产能”应保留；已有数据中心G02从旧miss变full不重做 |
| scope/产品边界 | S09 G01行30在正文marker前；G03/G04为收入guidance；S06 G01仅融资总额 | provider摘要不得冒充管理层原话；纯金额/guidance的漏项不自动当缺陷。旧golden/分母保留，在解释表明确处理理由，不改成易过的答案 |

年报1/5、半年报1/4、季报3/4、招股1/3、增发2/3、可转债0/4、有价值IR3/4、程序性IR0/1、电话会1/5；S05重复24/160、S06重复14/160。年报2个噪声只在3个可判定span内发现；全样本noise2/25，136个in-scope span未判定，不能声称其余都干净。角色/情态0只测question/statement错配，不证明计划/预测/否定已语义核验。

## 一、先用测试框住候选与完整事件

1. 打开既有`narrative_candidates.py`、`narrative_context.py`、`narrative_group_candidates.py`、`narrative_neighbors.py`与`narrative_evidence.py`；结构查询先CodeGraph。复用`NarrativeUnit`、现有page/paragraph/table/row/column/char locator与selection_group_id，不复制parser或保存全文。
2. 在现有Unit责任包先写RED：中文“已应用于/进入客户验证/已投用/产能提升”、具体产品+增速+第二曲线跨块句、行业产销景气、募集项目名称+用途+投产计划、IR海外/产品组合问答、英文capacity constraint。原件短引文仅作为source-oriented夹具，另加不同公司/行业措辞的合成正例，不能仅把9份公司的名词加入正则。
3. 同时写反例：纯损益表/合计金额、目录、承诺声明、无业务对象的“持续推进”、孤立“是的”、融资总额、重复风险声明。问句不得变公司陈述；“尚未通过验证”“预计投产”保留否定/计划原文，不改写已实现。纯财务数值可跳过；携带具体产品/客户/产能对象的定量描述不可被财务过滤整体吞掉。
4. 改现有候选/章节与邻接规则：用同一业务章节内的标题与相邻正文共同判定；只补最小必要邻接窗口，不能跨页/跨章节任意拼句。保留每个原始unit的locator，不把合并文字伪造为单个可回放span；一个事件的必要片段作为组参与预算。table问答继承正确speaker角色。
5. 针对上表逐点说明parsed→candidate→selected的期望，具体业务事实优先；scope外provider highlight与通用数额保留解释，不为12/33强行扩大parser范围。不更改旧golden或其required分母，不让评估器生成标准答案。

## 二、固定预算去重与选材，认真处理混合IR

1. 读`narrative_finalize.py`、`narrative_budget.py`与`narrative_routing.py`的既有选择逻辑。先RED证明重复正文/同一事件在多个章节不应挤占多个配额，同时角色不同、期间不同或不同项目的相似句不能误合并；多span完整事件不能选一半。
2. 去重限定同源、同角色、同一事件上下文的规范化正文；canonical片段仍有真实来源定位，保留必要的alias/原定位关联，不篡改SourceRecord、原件或既有来源版本。不能只按小写文本全局去重，更不能跨公司删原件。
3. 将具体业务事件、行业变化、募投项目、经营问答的组作为预算对象；在原96/160额度内避免一个高频章节吃满。空间约束与全部引用回放继续有效，不能把数量限制换成无限正文/永久Markdown。
4. 保留季度报缺信号为质量诊断。IR依内容分为有事实、混合少量事实、完全流程套话：混合文档只保留事实段；只有解析范围足够、确无事实的文档才skip/零模型。S08应保留产品组合那一条，不能为了消掉needs_review直接把IR全类型设为空即可skip。needs_review仍可读，不新增人工签收。
5. 接口字段、来源reader/RF合同不变；选择行为变更时更新selector version及相关固定版本测试，旧artifact仍按旧parser/version可回放。若确须公开合同变化，MAIN先列消费者影响与迁移细则，不能让外仓猜字段。

## 三、一次质量节点验收与发布

所有上述helper修复汇总到一个质量节点，不逐条人工审查或每修一点重跑全表。

- Unit：新语义正反例、分组完整、角色/否定、去重/固定预算、scope不足不skip，及现有责任包；先见RED再实现，不改断言适应错误产品。
- Integration：同一不可变golden和9样本，以新selector再跑一次零LLM基准，另存≤2MiB新报告；记录实际HEAD/工具SHA、原来的12/33及逐点改进/剩余原因。新增独立业务表达不反向改旧分母。精确定位0失败，已命中业务点不能回退；scope外/不符合业务目标的点明确列理由，不伪装全覆盖。
- E2E：独立短tmp，正式SourceVersionReader→现有AUTO Select/Worker/outbox→确定性模型响应→正式search/exact→RF已提交consumer。真实年报/IR/英文TXT字节，身份/日期使用明确fixture侧录；覆盖固定预算、混合文档零噪声、坏claim容错/同语言、全部locator回放与终态清理。不称为真实provider摘要质量，0付费/下载；已绿并发kill/ACK长包不重跑。
- 测试根起初不存在，finally关闭SQLite/子进程并恢复absent。大节点前后核原件SHA/size/mtime、生产库/配置、用户config及RF当前三owner日志（daily_alert、weekly_alert、weekly_manifest；执行前再实读status）；不把新副本/DB留下，不做46GB恢复备份演练。
- 日常commit静态检查、pre-push短集合、既有单Python快速CI保持；新完整9样本长测不放到CI。MAIN正常提交/推送，核精确代码SHA的CI；最终小收据与PWF更新，不能拿别的提交的绿灯替代。

## 可执行复现与交接

按`benchmarks/narrative_document_types/README.md`建立被忽略的local.json。当前基准命令（输出与scratch均先不存在）：

```powershell
python benchmarks/narrative_document_types/run_benchmark.py --output tmp/docset-next-report.json --temp-root tmp/docset-next-scratch
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -p no:cacheprovider --basetemp tmp/docset-next-tests benchmarks/narrative_document_types/tests
```

限定页诊断复现算法：以samples中的原件SHA/source_id调用现有`parse_pdf(..., table_pages=golden.read_scope.pages_read)`，TXT用`parse_transcript_text`；在独立Python进程中暂时包装`narrative_evidence.finalize_selection`捕获第三参数candidates，并在finally恢复函数。parsed.units与candidate.unit各调用`to_evidence_span(topics=(), selection_reasons=())`，分别与最终package.evidence_spans交给现有`evaluator.match_positive`，只报告原基准漏项。它是诊断，不能把限定表页的候选计数/排名当全表或生产指标；正式验收继续用runner及默认处理入口。读取与输出仍遵守上述独立根和原件指纹要求。

交接须附代码SHA/selector版本、新旧报告、具体golden ID/locator/阶段结果/处理理由、责任测试命令与结果、E2E是否fixture、根恢复/原件与owner指纹、0模型费用。若未修复项仍影响具体经营事实，将其列为remaining，不把工具通过或全定位合法当产品语义完成。此卡当前**in_progress**：候选/预算步骤已按N6独立写集分派，MAIN负责共享接线和最后一次节点验收三，不在本树重复做外线实现。

MAIN先行材料：[0.3.2冻结final兼容](n6_main_compatibility_implementation.md)、[33点统一业务解释](n6_main_business_expectations_2026-10-06.md)。9项兼容测试已绿；最终新代码仍要重跑该责任包。原required33、旧报告及golden不改，scope/纯财务边界不靠减分母让报告变绿。

另有[正式业务E2E框架](n6_main_business_e2e_implementation.md)已合成三文档27.65秒绿/13bba07精确CI74秒绿、[执行升级隔离](n6_main_upgrade_execution_implementation.md)纯流程PDF16.33秒绿。后者真实AUTO运行当前与模拟下一版本，证明新旧job/artifact独立、旧ref可读、同run恢复幂等，不证明外线未交付的业务规则。最终只在大节点重跑这些MAIN责任包，不扩日常CI。
