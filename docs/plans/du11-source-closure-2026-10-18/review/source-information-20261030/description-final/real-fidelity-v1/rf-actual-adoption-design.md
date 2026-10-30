# RF真实摘要采用：只读设计检查

日期2026-10-30；RF发布基线按ROOT提供为`4bbf4528`。本检查未写RF产品、未跑预测/完整公司loop、未启动下载/模型、未生成经营假设或研究结论。

## 结论与明确缺口

现有正式API能证明 **真实原文span → RF evidence claim → 真实used parameter → native segment formula** 的结构采用；不能单凭`status=consumed`证明 **某条模型摘要claim被研究过程采用**。当前缺少summary claim的选择、hash、研究处理决定及其到RF claim/parameter的显式lineage。M3只把`summary_assessment`保留到context/receipt，并没有新增这条采用链。

本次在RF `output/` 与 `artifacts/` 的JSON/Markdown按`002643 / 万润股份 / Wanrun`检索未发现本公司正式input/forecast；现有cross-market output是中微、腾讯、微软等公司的真实工件，不能改名当万润输入。本结论是对这些明确目录的查找，不声称检查过整个用户磁盘。也不能把test fixture、`generate_input_template`产物或人为增加无经济意义的参数当本公司实际forecast验收。

因此当前可推进真实RF读取、原文研究引用和来源质量保留；**若没有已真实研究的万润native输入，实际forecast采用暂有真实模型输入缺口**。新增summary-use lineage属于RF研究/消费责任，不应由CWP生成参数、收入或accepted投资判断来填空。

## 本次真实/6材料的现状

已只读解压ROOT `real-fidelity-v1/phaseC-090-ac0779f182e9.bundle.json.gz`，没有解析PDF或调用模型。原件SHA为`221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7`；bundle为`narrative-bundle/2.1`，artifact SHA为`c996577bbe4930bc12bd86deac68d3ed813dd2a372feee3989cc5aba9ac1d27b`。20条原语言summary claims，8个requested/admitted task均有输出；但selection仍`partial`、coverage_complete=false、229候选仅15选中、214遗漏、49财务项被drop，bundle与draft均`needs_review`。程序diagnostic_count=0且semantic/subfact status仍`not_evaluated`，不是摘要语义全通过。

已有CWP真实public read命令收据exit0，原样返回170428B artifact，locator_count15、read_at真实2026-10-30、selection partial、quality needs_review、replay verified；未知FY/pub/url均保持None，availability依据current_verified_open，仅支持相应当前cutoff，不可拿文件名20260515反推历史公开日。该收据是CWP public read，不能冒称RF预测采用。

可供研究核对的真实summary范围包括：2025内销收入/占比的历史说明、OLED客户链、有关报道的归属限定、上市程序及后续条件、分子筛历史价格方向、VC业务否定、已售半导体材料/开发化合物、C05项目产能与建成条件。它们的模型用途不同：研发化合物数量不是未来收入、设计产能不是已出货量、历史价格方向不是未来涨价区间、计划/条件不是已投产。此检查不据此填销量/ASP/利用率、CAGR或恢复日期。

## 当前真正存在的入口

1. `scripts/narrative_source_preparation.py --operation reference/read`，以及 `company_wiki_narrative_reader.find_narrative_reference/read_narrative_context`：按真实SourceRef/NarrativeRef读取、验证原件/locator/assessment，返回source context。只调用这些是read，不是use。
2. `source_preparation.prepare_registered_source_result(candidate, *, as_of_date, company_wiki_catalog_config, source_reader_receipt_version="2.2", ...)`：为该无FY/无URL原件建立真实SourceCapture；不需要FF重辨公司/期次。ROOT已有来源准备PASS路径。
3. **准确函数名** `source_narrative_context.consume_narrative_input(data, *, request, bindings, source_id, catalog_config, timeout_seconds=30, verified_by="RF narrative reader") -> (updated_input, consumption_receipt)`。该文件没有独立CLI；不能把不存在的`consume_narrative_context`函数名当可执行入口。

`consume_narrative_input`的binding精确字段为`span_id, claim_id, parameter_id, support_type`，可选`citation_group_id/citation_view`。`support_type`目前仅`rationale_support`；加未支持的`summary_claim_id`会被字段门拒绝。它再次从public reader取得真实context，核对capture exact parent、asof一致、parameter确实在`collect_parameter_roles(...)["used"]`里、`parameter_formula_refs`非空、support/context分区与locator，再：

- `_claim`把`span.raw_text`写为RF evidence excerpt，并写原件SHA/capture receipt SHA；**没有读取或选择summary draft claim的text/id**；
- 给parameter增加native claim_ids/source_ids；receipt记span/locator/parser/source SHA、RF claim ID、parameter ID、formula_refs与citation_trace；
- 有这些原文dependencies才设`consumed`；assessment只被deepcopy保留。故该consumed当前语义是原文span采用。

这些限制合理：模型摘要是有来源的改写，不是原文quote。不能为了summary采用把summary.text塞进`excerpt`并标`opened_and_checked`，也不能把t2的归属/uncertain、t4/t8条件降为actual。

## 最小真实可执行顺序

### A. 现在就可做，结论只到真实阅读/原文采用

1. 在ROOT受控独立湖中，由已有CWP owner合法保持/恢复exact原件和已保存native artifact；如果上轮临时湖已删除，不用手写accepted行或只读gzip伪造一次新的public read。复用paid响应，保持历史账与unknown holds，不发新摘要POST。
2. 使用真实registered candidate取得RF SourceCapture，再以/6实际read-request和精确artifact引用跑RF public narrative reader；保留真实context、receipt、命令exit、runtime/安装版本、source/artifact/claims hashes。所有partial/needs_review、coverage和assessment限制原样保留。
3. 研究者阅读summary实际claims，并回到其已验证support/context原文核对归属、否定、时间、单位与条件。记录研究处理：可以是使用某一事实作为方向/边界、保留原假设并说明证据作用、反证/排除某业务、或明确数值支持不足。一个有用的未量化观察可以是实际研究使用，但不能据此声称已经进入native formula。
4. **只有已有真实本公司模型输入/在本任务独立研究中已形成合法本公司输入时**，挑选与其真实used parameter相符的原文span，调用`consume_narrative_input`。选用真实参数ID，不添加无关/零作用参数；不要为测试链路而创造公司销量、价格或增长率。阶段产物可准确称“真实原文rationale引用采用”，不称summary claim直接采用。

现API支持原文qualitative rationale；若要引用历史精确金额，采用既有native `exact_value`和原文locator/数值抽取字段，不能让当前rationale-only helper替代数值核实。完整native source/claim合同还支持`policy_support`；这不是本次helper可静默扩大的能力。

### B. 补齐summary使用lineage后，才验真实summary→参数/公式采用

建议在RF已有消费owner内增加一个**窄、可选、版本化summary-use扩展**，不改forecast计算模型、不扩CWP职责、不加第二研究数据库/许可链：

- caller显式选择实际summary claim ID；owner从已验证context取claim、计算canonical claim hash，绑定NarrativeRef/artifact SHA、summary claims SHA、support/context IDs、claim_type/modality/needs_review以及完整assessment的观察状态。
- 记录真实研究处理及理由，指向已有RF evidence claim IDs、parameter IDs、native formula_refs。RF evidence claim继续引用连续原文excerpt，摘要改写只在summary-use lineage/研究rationale里；不把它伪装成另一份原始来源。
- 输入binding可以新增有版本辨识的可选summary选择字段或提供同一owner的summary-specific helper；旧span binding保持兼容。不要现在往旧binding硬塞未知字段，也不要临时写另一套参数计算器。
- 输出放在现有consumption receipt的可选`summary_use`对象（例如`revenue-summary-use/1`），可以伴随原input/更新input/forecast的canonical hash保存为小sidecar。不要为了这个局部链路先改context/forecast主schema或建立accepted/rejected投资状态。exact字段/状态须先TDD定稿再改产品，本报告只是设计。
- `not_used`/`read_only`不能变成used；真实参数rationale采用须有目标native claim/parameter和formula_refs；仅反证/业务排除但未进入现有DAG的研究观察单列，不谎报formula采用。摘要needs_review可保留并触发研究说明/原文复核，不新增逐条人工放行。

这条lineage只证明有审计依据的研究输入/决定链，不能机械证明人的思考因果。实际研究的理由、原文核对与模型一致性仍需原有大节点独审。保留参数值不变也可能是合法研究决定，但仅给既有参数事后挂一个无作用source ID不是充分采用证据。

### C. 真实native input具备后，用原正式引擎验收

保存新的万润输入版本（来源时间/当前研究时间真实、既有历史不改写），按既有研究authoring procedure只跑相关步骤：

```text
python -X utf8 -B scripts/lint_input.py <new-real-wanrun-input.json>
python -X utf8 -B scripts/fix_hashes.py <new-real-wanrun-input.json> --check
python -X utf8 -B scripts/revenue_forecast.py <new-real-wanrun-input.json> --validate-only --verbose
python -X utf8 -B scripts/revenue_forecast.py <new-real-wanrun-input.json> --output <new-forecast.json> --markdown <new-forecast.md>
python -X utf8 -B scripts/research_support_diagnostics.py --input <new-real-wanrun-input.json> --output <new-support.json>
python -X utf8 -B scripts/revenue_backtest.py create <new-real-wanrun-input.json> --version <same-new-version> --output <new-snapshot.json>
```

命令在真实RF runtime/cwd中执行；本检查没有执行。formal compute/snapshot前由所属任务将`REVENUE_PUBLICATION_REGISTRY`指向自有尝试目录，事后恢复；validate-only是draft/零registry写，不等于正式publication。保留input/forecast/snapshot canonical anchors、summary-use receipt、actual commands/exit、质量限制和TRUST_BOUNDARY。输出必须仍有原partial/needs_review信息，不许把8task齐全当全原件覆盖。

dependency visitor只描述既有模型实际driver/derived ancestry，不计算第二套收入。需要经济影响验证时用原native sensitivity/情景结果，并说明真正影响的segment/scenario/input和recognized periods；无需为“看起来有差异”改一个任意百分比。结构依赖非空不独自证明参数幅度有证据，收入预测本身的完整历史、口径/识别/区间支持继续由RF研究owner负责。

## 后续最小验收反例与当前状态

工程TDD可用合成数据验证summary ID/hash错配、支持/上下文互换、错parent/旧artifact、无used参数/无formula、needs_review洗白、仅read变used等拒绝；**这些不能计作真实公司采用验收**。真实节点须使用本次20条实际claims中的明确选择、真实原文locator、真实本公司native输入、原引擎产物及独审；不要求把20条都机械塞入预测。

当前状态：RF来源准备/公开source context可分别验；原文binding API存在；summary-specific采用lineage缺失；本检查范围内未找到真实万润native input/forecast；实际summary→研究→参数/公式→正式forecast尚未完成。合理下一步是先补这条窄lineage并识别/复用真实本公司研究输入；若没有真实输入，保留具体缺口，不启动完整公司loop或为验收造数。
