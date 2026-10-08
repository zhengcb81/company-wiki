# R2：生产来源事实与旧电话会登记实施细则

**Status: complete。** R2源码6ae7ddc已正常推master、精确CI37705927320全部步骤success，真实生产九来源正式应用已完成。R3真实final和R5最终收口另有责任；总目标active，不能把本卡完成当整体完成。

## 正式生产与R3交接（覆盖下方发布前记录）

[生产应用收据](harness_lanes/results/r2_production_source_application_2026-10-08.json)：S01–S04正式restore，八条原退休审计保持；S01–S09经公开API写九条事实，S05/S06融资分类正确、S07/S08/S09公开日unknown保持。TXT从ET原字节复制66,324B到Microsoft/raw/transcripts、sidecar589B，legacy_unverified/null HTTP receipt明确，不翻译、不重抓。documents23530→23531、sources43112→43114、locations46606→46608、assertions22→31、restore audit1→5，retire audit19000不变；重复新增断言0。不相关documents、根水位、九原件及原侧录/config SHA保持。DB主文件222,408,704B不增长，本次WAL1,240,152B是合法事务增量；不当作全文副本或宣称已释放。

R3[完整DTO请求](harness_lanes/results/r3_production_batch_request_2026-10-08.json)已校验，生产SourceRef而非fixture：S09实际经营内容加active真制度。使用已配置DeepSeek Flash/8192/温度1，49段精选证据、HTTP正文10,873B；[零POST预检](harness_lanes/results/r3_production_request_preflight_2026-10-08.json)最坏预留19,193tokens/14,591microUSD，费用仍在原累计$0.12内，token余9965不足。已请求仅提高累计token到220000，费用不变；答复前零POST，全部旧190035/100502/unknown7/FX2764保留。

唯一下一动作：收到必要预算增量后执行R3正式配置入口和两个来源唯一batch；单batch恰限19,193tokens/$0.014591，任一实际请求收费后无法再预留同一完整请求，不盲目重试。生产AUTO用既有实现及文档的`.source_catalog/automation.sqlite3`（目前未建立），work-dir`.source_catalog/r3`；历史tmp pilot账本保留，不创建第二任务框架、不冒称已运行。正式成功后当前RF/SW CLI消费、未知公开日诚实资格、locator回放、同run新增POST0及空间收据一次大节点验收。

## 实施与隔离验收记录（发布前历史；完成状态见页首）

来源事实公开API/薄CLI、显式unknown读取及有限重新登记已实现。当前101责任项15.08秒全绿、九份真实原件隔离E2E一项4.75秒全绿，均零skip/-W error。实际复制37,943,036B原件，恢复4个document、保留8条退休审计、仅9条事实断言，重复登记/事实处理零新增断言；不相关来源/根扫描水位保持，finally恢复测试lake absent，原件及生产配置/DB的size/mtime不变。入口不发模型、不翻译、不构造HTTP receipt。源码尚待正常commit/push和精确CI，生产尚未应用；详见[结构化验收](harness_lanes/results/r2_source_facts_api_acceptance_2026-10-08.json)。

当前正式测试包为tests/unit/test_source_facts.py、既有scoped/scanner/financing/steady/assertion/upsert/B05责任包，及tests/e2e/test_r2_source_facts_real_bytes.py。真实E2E仅在显式CWP_R2_SOURCE_ROOT（CWP根）和CWP_R2_TRANSCRIPT_ROOT（ET transcripts根）下执行，pytest加`-o junit_family=legacy -W error`、独立短basetemp；缺显式根只表示未执行，不算验收通过。复制实际原件，旧行投影/状态以现场观察构造隔离夹具，因此不冒称生产已修或供应商在线质量已通过。测试前后核九原件SHA，生产配置/DB stat，最后删自己的lake。不得使用生产目录作basetemp。

事实和扫描共享唯一document kind→source family映射。单请求128KiB，累计字段证据64KiB、普通事实文本2048字符；只有重新观察时间变化不追加历史。相同旧capture重登采用已核事实，真正新矛盾仍走B05拒绝，不覆盖原始采集声明。避免重复空间和假冲突，不增加人工门。

错误也已记入收据：初次夹具缺SHA/reader关闭、一次不存在的测试路径、JUnit xunit2警告、退休后错误query_ref均不当产品RED；真正RED为入口缺失和重登假冲突。额外本地`--strict`暴露未改reader的旧Any返回，不属于配置CI；按当前配置的mypy通过，不改无关reader或增加检查门。

本轮21个实际存在的owned临时条目先存逐项清单再原生删除，全部恢复absent；实测68,812,548B/1,393文件。只删测试材料，不删原件；五个历史g2根仍保留待R5确认。见[清理收据](harness_lanes/results/r2_owned_temp_cleanup_2026-10-08.json)。PowerShell OrderedDictionary汇总显示null，依据已保留逐项数值重算，未虚报空间。

## 当前事实

[只读现场收据](harness_lanes/results/r2_current_source_observation_2026-10-08.json)实核九份原件SHA，SQLite total_changes=0。S01–S04只有缺URL治理及其reconcile退休原因，无真实撤回记录；S05/S06仍other，S07/S08弱名称身份，S09未登记。G3官方字段证据继续用已验收metadata_proposals/evidence_index，不从文件名猜公开日。S07公开日unknown；S08旧2023-12-31未获证实，不能当真实公开日；S09会议日与URL路径日不是公开日。

现有identity-enrichment preview实际上写candidate（CLI旧help不准确），verify追加verified；它们不能原子同步documents的分类/公开日投影。不能在临时脚本直接UPDATE生产、覆盖原sidecar或用fixture身份掩盖缺口。

## 一次来源事实事务

在现有assertion_service增加record_source_facts，由SourceCatalog同名方法提供公开入口。入参SourceRef、明确facts及字段证据；不引入第二状态库、许可、签字、TTL、计划hash或重造reader。事实verified仍只指来源质量，不是投资判断。

1. 在既有CatalogOperationLock内通过SourceVersionReader核实际字节SHA/大小/当前可读状态；失败零写。恢复退休是独立的既有documents restore入口，不默认恢复任何retired。
2. 仅接纳现有来源语义字段；缺key=不改，显式null=修正为unknown。保留未改字段，包含期间/URL/语言；证据需给已改字段的locator和观察值，null也说明unknown原因。字段证据是来源数据，不是人工签收。
3. 与最近可见同SHA verified事实合并，追加一条不可变assertion并supersedes之前记录；同时只更新该documents行的查询投影（kind/source_type/date），单事务失败全部回退。同一facts+证据重复零新assertion/零投影写，不用新run许可。
4. steady事实读取识别本接口的显式unknown，不能从旧capture补回已否定日期；SourceRef/原件/原sidecar/历史assertion不改。正式describe、候选、查询和as-of使用同一有效投影；现有坏字节/真实冲突仍拒绝。
5. 增加薄CLI source-facts --request：有界JSON、SourceRef身份而非原文路径，转发现有服务。正常实际字节验真与事务，不增加人工review文件。

## 先测后实施，只设一个R2大节点

新责任测试先RED：真实SQLite/原件夹具，正式服务及literal CLI；检查身份/分类/公开日有效、unknown不回填、重复零写、字段证据不符/未知字段/坏SHA/文件改变零写、不可读状态拒绝、事务异常原子回退、历史记录不覆盖、不相关来源/原件/配置不变。CLI不接受fixture原始路径；只用SourceRef。旧preview帮助与死代码同时清掉，不改旧命令实际兼容。

同节点复用既有assertion、steady/read-policy、B05/reader、scoped registration责任包，增加当前R2真实原件的隔离端到端验证：S05/S06分类、S07身份/未知日期、S08错误日期修成unknown且不获as-of资格、S01–S04有证据恢复而保留退休审计、旧TXT原语言有限登记并同SHA复用。测试根起初absent、finally和节点后恢复，不复制整个生产库，不完整恢复备份，不跑付费模型/全根/全Unit。所有测试资料只在owned短根，收据不保存正文。

## 正式生产应用次序

先发布新增入口、核正常短检查和精确源码CI，再用相同入口和实核SHA应用：

- S01–S04：再核无其他撤回原因，既有restore恢复；原审计保留。按G3官方公告日期与688012补字段，期间来自封面，不以招股书年份冒充财务期间。
- S05/S06：官方证券300775/688059、融资kind/source_type、官方公告2022-11-30/2022-06-22；原始ID/SHA不变。
- S07：002643，published_date保持unknown，原语言zh；业务活动日不替代公开日。
- S08：002867，旧未核实公开日显式unknown，来源证据保留活动窗口；不捏造任何豁免或新日期。
- S09：旧TXT66,324B/SHA4ac3…852a先核ET header与正文，复制原字节到CWP Microsoft/raw/transcripts；旧ET文件不写。metadata明确legacy provenance、provider receipt未核；通过现有SourceCatalog.register_sources单根指定组登记，不构造DownloadReceipt或伪造HTTP成功。源URL只作第三方声明，published_dateunknown，期次MSFT/Q4/2026，不翻译、不抓取历史。
- 真中微管理制度原件用于零模型skip，不能用含业务黄金结构的S08凑skip。

生产前后保存小事实计数与所选行/版本/manifest/断言差异、未选根扫描水位及原件SHA；合法生产登记后DB变化是预期，不能要求DB整字节保持。按实际新增TXT/sidecar/DB/WAL记空间，停止后清staging和owned测试根。Dayu/IQS/邻仓owner零写。

## R3请求与预算交接

准备一个有价值IR/TXT来源和一个真制度skip的唯一显式batch，使用生产AUTO Store及P4计算3/模型1，不起无限worker、不新建任务库。调用按Config和profile，不改mimo-v2.6-flash/deepseek-flash/8192/温度1/价格。

现累计190035tokens，限200000；现余9965，不足18755完整请求预留。费用100502microUSD、未知7/FX2764照计，余16734。在来源/完整请求/预留可审查后提出必要预算增量；新目标不等于提高预算。R3须真实供应商final+原文定位、当前RF/SW正式消费、同run0新模型/不重复计费和真实空间收据；R2零模型绿不能冒称R3完成。
