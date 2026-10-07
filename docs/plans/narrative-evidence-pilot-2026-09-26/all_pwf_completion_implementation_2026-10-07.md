# 全部PWF内容：实际落地与最后收口（2026-10-07）

## 用户目标与当前基线

用户要求完成全部PWF计划内容并逐步实施。代码2cad90d/CI37582474369是前一发布，审计计划8ffd3f0已推；RF e241389、StockWiki9f552a6、StockQA最新6a9ff138。先前16项有界验收继续有效。目标服务最新实读active，继续下列次序。MAIN独占总计划/共享接口/生产/合入，各大节点一次，不增签收或小节点门。

**当前并行：**[三个新施工包](harness_lanes/g2_parallel_packages_2026-10-07.md)已由用户分派，待交接：SW日常检查、StockQA工程入口/四workflow、RF可选工具/清单。各仓独占目录、自己的PWF/测试/交接，未代用户启动。MAIN13/01b/12不等待外线；MAIN收交接统一合入，纳入既有G2B，不添加小节点签收。单卡已补RF历史caller兼容与StockQA额外workflow/真实import隔离，不缩R2–R5范围。

**2026-10-07优先级更新：**先[G2全面补漏](gate_simplification_reaudit_2026-10-07.md)，再R2/R3/R4/R5。现场steady小配置迁移已完成；默认读取/有效pin/AUTO错误/摘要质量/版本恢复核心93ac5a5已推，精确CI37590638806全部步骤绿90秒。Store轻初始化b202d07已推/精确CI绿；scoped pin仍P0，SW/StockQA日常全测/联网hook/隐藏阈值、CWP/FF latest统一请求升P0-B，RF可选发布/会话强制清单、CWP公开旧CLI/写Store库存与冻结gate家族有具体同步写集。G2只重排，不缩原目标，仍仅两个大节点。R2 metadata/正式生产登记和R3 paid没有执行。

计划文件以[逐份目录及SHA](harness_lanes/results/all_pwf_inventory_2026-10-07.json)登记。旧执行卡W0–W7、F/D卡、各并行卡与其后继方案按下表对账；不能重复跑旧命令恢复已删除全文，不能将旧审批流程或唯一raw删除重新启用。当前用户原件不丢、Dayu零代码修改、IQS独立项目不动优先。

## 计划家族与完成条件对账

| 计划家族 | 现状与真正待办 | 实施处理 |
|---|---|---|
| G1/46项/八束激进门禁精简 | 原约定入口已验收；G2八仓复核确认14组及scoped pin遗留，历史全面完成不成立 | P0核心/Store轻初始化与P0-B日常工程门/latest统一请求，P1实际公开遗留家族/工具清理；两大节点，保留自动正确性 |
| 原设计、W0/W2–W6、E4/M3、并发恢复/检索导出/跨仓G-C | 当前SourceRef/SourceExport、AUTO/outbox、精选/原语言摘要、配置模型及恢复有已发布节点证据 | 保留验收，不重写第二套队列/reader/投资研究状态。生产使用另按R2/R3 |
| W1来源分类与无翻译ET统一管理 | ET/FF正式接口已交付；**生产S05/S06仍other、S01–S04仍retired且缺公开日、S09未登记**，试点fixture不能代替生产元数据 | R1修正式扫描器融资分类；R2核实来源/公开日/期间和retired原因，经现有入口登记/更新；不猜日期或直接UPDATE恢复retired |
| S7/DOCSET质量 | 29/33必需、761定位回放；纯融资金额、纯财务guidance、正文外provider摘要及同源另页canonical产能已解释，golden不变 | 当前4个miss不盲目“修满分”；保留29/33和定位级覆盖，新增生产实际业务质量检验。发现新增业务漏项才TDD修责任层 |
| N4真实模型/生产composition | 四类真实模型在隔离根验收、正式链可用；生产final0 | R3真实来源正式有限批次，成功final持久可读、同run恢复不增对象；预算获明确增量后才新POST。不用Replay冒充生产摘要 |
| F0–F5、S5/S6、D旧删除提案 | 已净释放5659443210B，原件删除0；历史唯一低价值raw删除已取消 | 不重做整库迁移/备份恢复、不删唯一raw，原文去重依据N5实证，不把7.8GB登记上界当可回收物理量 |
| N5 RAW-DUP与R5可选对象化 | 只读工具完成；已读3组约158MB跨根，CWP内部收益未证明，外根只读 | R4一次只读CWP内部候选核实、给真实收益/是否值得的决策；收益不足不强行迁移对象库，不动Dayu/Dropbox |
| FF/ET联调、各外包、主线合并 | 已正式交付并线及对应CI，日期缺口已修复 | 复用已交付SHA，不重新派发；生产跨仓再用当前已提交consumer，不接入IQS活动队列 |
| 完整预测/投资研究 | 当前PWF要求只读来源reader/adapter，未授权CWP产生正式研究；“自动完整研究”不是此来源平台writer目标 | R3将真实生产NarrativeRef读入RF/StockWiki既有公开consumer，不新增CWP研究状态；不把consumer读成功称全预测算法运行 |
| R7快CI与TDD | 正常静态commit/短push/单Ubuntu快速CI已实现 | 本次新增行为先RED→责任包；生产联调/空间恢复集中节点，不每天跑全部PDF或全部跨仓套件 |
| R8PWF收敛 | task_plan短入口完成；findings/progress仍近千行，历史卡最新状态散落 | R5压缩当前三入口/README与历史卡导航，历史原文在固定Git9a18e6d；不复制大归档，不掩盖errors与真实remaining |

## R1 正式融资文档分类（零费用，先TDD）

**Status:** complete

代码66ce046已推master，精确CI37578307854全部job/step绿79秒；责任45pass与真实两PDF公共CLI2pass，六新测试根已恢复absent。

实际scanner._classification只认识普通prospectus，未识别equity_offering_prospectus/convertible_bond_prospectus。生产S05/S06为other。先用独立当前schema目录/原件夹具建立反例：显式sidecar融资类型、精确“股票募集说明书/可转换公司债券募集说明书”标题（大小写.PDF）、一般债券募集文件、broker点评及最高优先级sidecar；含“发行股票董事会公告”等不能误当招股。保持SourceType.PROSPECTUS现有族（实际枚举PROSPECTUS）、source/document ID按原SHA不变，不为了分类重下载。新增行为先真实RED，再最小scanner实现，集中责任测试及扫描二次幂等。生产元数据迁移属于R2，不能拿Unit绿说生产已改。

## R2 生产来源准备与请求编制（零模型）

**Status:** in_progress

本阶段有限登记/单次权威SHA/AUTO范围SQL与终态零子进程/steady源码已发布2cad90d，202责任项与精确CI绿。现场steady迁移归G2-00首先实施；其他生产metadata和正式请求在G2两个节点后继续，不重复已绿代码验收。

已修复历史缺陷：CanonicalSourceWriter曾每次新增全扫company_raw，扫描器曾没有按文件入口。2cad90d已TDD实现单根显式relative_paths有限登记：保留相同group完整成员，未选组及根完整扫描水位不改，不做missing sweep；拒绝空集/越界/未命中。常规全扫描保留，canonical import仅登记刚写入组；202责任与精确CI已绿，不重造scanner或重跑该节点。当前R2生产metadata更新直接使用此正式入口，不patch扫描器、不全库23GB重扫。

1. 只读核实际来源、位置/版本、acquisition sidecar与原件；S01–S04retired原因按正式journal/scan记录追溯，不能因文件在就复活撤回版本。S05/S06以明确来源类型迁移，不改raw或source SHA；S08表中活动日期与published_date2023-12-31冲突须记录，不能直接抄文件名为公开日。
2. 原文日期/证券/期间以官方公告元数据、可复核来源记录为依据，经现有SourceCatalog写入口更新或登记。缺公开日保持unknown，禁止临时fixture进生产。只修首批实际请求来源；不先全库metadata/全文回填。
3. ET旧TXT通过现有接口复用/导入公司目录；旧侧录缺失保持legacy_unverified，既有工具校验正文SHA与ticker/期次，新生产manifest不得伪造历史provider receipt。不改ET原件、不翻译、不启动scraper遍历历史。
4. 首批优先一个元数据可核的有价值IR/TXT，及一个纯流程零模型skip；复用真正原件SHA，统一既有AUTO Store、P4计算3/模型1。不新建生产第二任务库。每个run有唯一work-dir、明确source refs、时间/token/费用/空间上限及可复用的请求。保存小元数据/预算预检，不保存全文转换。
5. 根据正式Config（MiMo v2.6-flash/DeepSeek flash/8192温度1.0）计算实际完整请求最坏预留，旧190035token/100502microUSD/未知7/FX2764照计。现余9965token/16734microUSD不足已测完整请求18755，**新目标不是预算增量授权**。准备可审查的具体资料/目的地/请求与增量，再询问必要额度；期间完成零费用步骤。

## R3 真实生产有限批次及跨仓验收

**Status:** pending

先隔离E2E验证R1/R2新增公共行为，测试根最初absent、finally恢复；真实下载/副本/SQLite/子进程测试结束不得留下。生产保留成功final属于正式运行，不是测试残留。

真实调用前核RF最新HEAD/status，不碰owner日志/其他研究目录。请求由现有配置加载，保留未知usage预留，显式batch，失败局部保留状态与可恢复事实。外发仅明确批准原件和配置供应商；不通过改max_tokens、thinking、超时或价格绕预算。真实来源至少一份有价值业务final和一份纯流程skip（后一份0模型）；逐条核原语言/角色/来源支持和locator，短摘要不重复全文，记录final大小、AUTO/对象/数据库/WAL总增量、scratch峰值。

正式reference/read/search/exact及RF/StockWiki当前主线CLI消费；检索结果精确回放。相同run再执行：原final/ref不变，model请求0、费用不重复，终态临时正文收敛。未来公开/版本改变等既有反例复用责任包，不在生产造坏数据。此节点后production final不为0，不能用隔离数据库统计代替；不声称已处理全库或自动投资研究。

## R4 原件空间与可选去重决策

**Status:** pending

复用N5工具只读元数据候选，精确限定company_raw内部distinct physical copies，有限读取预算、拒绝云占位hydrate，原件不修改。所有source/version/location引用保留；输出实际实读duplicate上界与allocation未知。只有可量化收益与现行reader调用者迁移充分时才写下一步对象化施工细则；若只存在跨根副本/收益小，本计划以“不做无收益迁移”的证据决策完成本可选项，不假称已释放。用户最新“全部计划”不等于删除唯一原件或写外部Dayu。

## R5 最终PWF/主线发布收口

**Status:** pending

MAIN压缩当前findings/progress，保留当前目标、未完成、真实错误、保护文件、预算、验收、单一Next Step；历史正文使用Git9a18e6d固定链接。更新主计划各状态/README/完成证据顶部及所有相关交付卡的当前状态链接，避免弱模型恢复旧队列。

代码正常commit/push，精确对应代码CI全部执行步骤终态绿。纯收据/文档不重复代码CI。新根清理前核精确路径/所有权/无reparse、原件及用户文件指纹；生产库预期元数据/新增final写入需逐表小范围变化账，不能要求合法新增后整个DB SHA仍等于旧库。若仅生产状态使用无源码变化，不触发多余CI。所有真实必要条目及预算/外部依赖未闭合时目标仍未完成；目标服务当前active，不能靠更改Status或排除待办完成。

## 错误记录

首次resolver使用-CheckAmbiguity仅做探针不返回目录，已不带该flag显式PLAN_ID解析到本目录。两次Python中文stdout乱码是编码设置，文件UTF8未损；后续PYTHONIOENCODING=utf-8。三次猜测implementation_spec.md/n5_raw_duplicate_advisor.md/NARRATIVE_RUNTIME.md不存在，已按实际文件名及docs/source-catalog.md查阅，不新建替代契约或忽略缺文件。
