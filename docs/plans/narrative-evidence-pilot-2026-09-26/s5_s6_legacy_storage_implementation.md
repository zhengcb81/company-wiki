# S5/S6：旧派生退出与来源库降容实施细则

> MAIN负责执行，不是新的外包卡。复用总计划S5/S6存储节点，不增加逐文件或逐helper审查。N4-T1/T2保持各自写集，本文件不授权修改它们的施工目录。原件、来源版本和撤回事实保留。

## 2026-10-06交付验收恢复点

**最终当前状态（覆盖下方执行中/未删的历史记录）：**生产存储节点已完成并验证成功。derived7104文件/2826010634 B清零，8191旧handle retired、1490530旧span清零；DB整批3055841280→222408704 B，净减少5659443210 B（5.66GB/5.27GiB）。来源17表/四份公开原文SHA及固定年报/电话会TXT均不变，FK/完整性通过；原件0删除。恢复点、大清单/报告和脚本共186486185 B已清除，tmp/s5-storage-20261006恢复absent；这个临时清理量不另加进净释放。正式小收据[harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json](harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)。所有执行进程已terminal，不再等待旧handle/复跑inventory、retire、prune、VACUUM或长测试；下一仅做S6现行docs/hook核销并回N4C，总目标尚未完成。

P5-FF与P5-STORAGE均已验收并发布，精确CI已再核success。CWP旧生成器b148123已退出生产安装包；RF已验收并推main ca67eab7（默认链代码b110502f）；精确CI37391526925一次全绿、job32秒。本地正式revenue-forecast已切main同步，旧rf-impl WIP原样保留在独立分支；三处已安装来源入口SHA与主线一致。生产derived/span/VACUUM仍未执行，空间收益须实际处置后测量。下一步复用[P5-RF整合细则](harness_lanes/results/p5_rf_main_integration_plan_2026-10-06.md)，不重跑工具已签收的长验收。

## 2026-10-06生产盘点后必须收口的共享路径问题

**终态收尾补充：**主节点已succeeded，1490530条旧span删除，VACUUM完成，同四份原文/17表事实均保持。剩32文件41090 B已逐个实读frontmatter：21份structured_text旧normalized、11份旧LLM summary，全部为`.PDF.source`等侧车元数据产生的无registered handle缓存，非原始PDF或新final。MAIN仅对此精确列表按当前SHA/size、SHA目录与header身份、角色/版本、无artifact引用及非locations原件复核后unlink；空目录只rmdir，不递归扫未知对象。随后把整体基线修正为退休前DB3055841280→222408704 B（压缩前3059736576是退休元数据临时增长后的值，不能多报整批净释放），保存小聚合/PWF再清除17表恢复点、大manifest/阶段收据与一次性脚本。原件/新final/源码不再修改，不增加小节点测试或签收。

**当前实际运行：**代码96f44a1已推master，精确CI37394193179 attempt1全绿。生产readonly预览结束：6714候选、7072唯一文件/2825969544 B、8191相关旧handle（1477共享alias）、excluded0。实际节点`tmp/s5-storage-20261006/execute_storage_node.py`正在运行；会话15696、当次PID39672只作定位线索，恢复时必须确认真实进程或工具handle仍live，不能仅看文件。四份生产原文公开CLI `--purpose preview` SHA/size已通过，17表source-only checkpoint161251328 B与preview事实完全一致；没有整库备份/恢复演练。当前stage为retire，未见终态收据时不能报告释放量。

**中断接手规则：**先读同目录`production.before.json`、`production.retire.json`、各`production.prune.*.json`、`production.vacuum.json`与`production.aggregate.json`，再核当前DB/文件。进程live就等待原进程，不另启动；只有terminal/missing且未成功才接续。保留原before/checkpoint/manifest和已成功阶段收据，不盲重跑或覆盖整个一次性脚本；用正式`tools/legacy_storage_retirement.py`仅重试未完成操作，retire复用`manifest.revised.json`，输出新命名的恢复收据。prune仅用原manifest的8个精确parser/version，保留引用集合本次实际为空（production新final0、其他表无span/locator字段或evidence外键）；若后来新增final则重新取当前keep refs。VACUUM成功后对比原before的17表digest、同四份preview stdout SHA/size、配置SHA和实际文件/DB字节，再写聚合并清除一次性材料。失败保留小恢复点，不恢复全文缓存、不备份/还原整库，不重新做49项/历史53项长测。

**实现恢复点：**共享路径闭合、事务内当前引用集合复核、sections所有权及物理字节去重已实现。新增16项责任测试连同既有恢复/边界/规模共49 passed/87.25s，Ruff与diff检查GREEN，测试根均恢复absent；收据为[harness_lanes/results/s5_shared_path_acceptance_2026-10-06.json](harness_lanes/results/s5_shared_path_acceptance_2026-10-06.json)。生产尚未处置，下一动作是正常发布/精确CI及旧manifest范围补充预览，再进入第5项实际降容。不是重新签收P5-STORAGE或新增小节点。

RF默认链已经main发布/精确CI绿，本地与安装生产依赖同步。一次inventory已成功结束，真实aggregate见[harness_lanes/results/s5_production_preflight_2026-10-06.json](harness_lanes/results/s5_production_preflight_2026-10-06.json)。操作manifest为tmp/s5-storage-20261006/manifest.json（5588419B，恢复输入，不提交Git）；不重复多分钟的全legacy表摘要盘点，只对修正相关范围核验。

当前6479个候选artifact指向6479个主文件；1712个excluded中1477个直接parser标签行与候选共享同路径/同document_id（0跨document冲突），其中814哈希相同、663旧哈希已失配；另235个summary行generator/version为空。这不是未知原件，而是需要验证/退休的旧派生元数据。按现工具直接apply会留下1477条completed/partial等别名指向已删除文件；生产不能据旧53项fixture签收跳过这项具体缺口。

MAIN下一集中实现/验收：

1. TDD使用小型真实schema/原文夹具：已识别旧候选与直接parser历史别名共享一个文件，退休时全部相关旧handle在同一事务不可消费后才unlink；同路径的失配旧hash仍保留诊断事实，不假造校验通过。任一共享行属于未知现代generator/非legacy角色/跨document冲突时，整个物理对象拒绝删除，不能只排除该行后删文件。测试恢复/幂等及范围外原件/新final不变。
2. 根据历史parser/writer代码和已核生产标签，明确识别旧direct parser生成normalized的名称与版本，补上235条空标签summary的可证明路径/role规则。保持新NarrativeRef对象/其他角色/未知对象受保护；不要把所有unknown_generator放开，不新增人工签收或权限flag。
3. 候选/实际释放字节按规范化物理路径去重。sections的managed成员可能与其他条目重合，禁止重复累计/重复unlink导致误报。已知candidate_bytes2826149019大于实际derived2826010634，显示不能把行级字节总和当物理释放量。
4. 在已有catalog锁与事务内复核整个路径的当前行集合及身份；元数据退休必须涵盖受影响旧别名，恢复重试用原manifest/当前DB事实。先修工具/责任测试再正常发布及精确CI；这一组是存储大节点的一部分，不逐helper审批。
5. 复用已完成RF真实年报/原件transport与工具真实样本签收，新增相关共享路径/空标签/unique-byte责任包集中验证。随后以修正工具对现manifest做一次范围预览，保存17张来源事实/新final的小摘要恢复点，再执行retire-derived→明确8类legacy span scope prune→VACUUM；实际引用保留集合和未知表保持，不完整备份或演练恢复3GB库。
6. 原件、来源版本/位置/公开日/撤回事实与当前新final保持；0模型/外部下载。实际物理释放和DB shrink分别写小收据，测试材料finally恢复，生产manifest在成功收尾后删除。不能把当前只读盘点说成生产清理完成。

## 依据与边界

- SPACE-S5报告：`C:/Users/郑曾波/Projects/company-wiki-storage-audit-20261003/results/storage_audit.{md,json}`。报告的138,648,023 B缓存、2,826,010,634 B derived、3,055,800,320 B DB是当时实测，下一批只核变化的集合。
- 2026-10-04重新读RF `origin/main@8a153f3`实际scripts：`source_preparation.prepare_source`默认`source_reader_v2=False`；旧分支选取并实读SourceBundle artifact。v2实现存在不等于生产默认已切换。
- CWP SourceBundle允许坏artifact与可用原件独立，不能声称normalized一丢就让整个原件不可用。`extract-sections` CLI/服务API已退出。此前“公开normalize/summarize及后台启动都已退出”的记录不准确：CLI启动入口已撤下，但`SourceCatalog.normalize/summarize/summarize_with_llm`按需方法仍存在；旧 Worker 类也曾保留。2026-10-05已移除无生产调用者的旧 Worker 类和仅供其调度的阶段策略，但未删按需API、normalizer、摘要模块或历史数据。
- 新叙述选择从verified raw现场建立精选EvidenceSpan，不依赖数据库全量旧span。EvidenceSpan仍是来源层canonical对象；改变的是永久存储范围，不是取消来源定位、原文校验或引用回放。
- IQS当前独立项目不触碰；Dayu零代码修改。RF owner两项assurance记录不加入本线提交；`config/source_acquisition.yaml`保持用户原样。

## 顺序与输出

### A：先删除无活动依赖缓存

七类限定集合：`.source_catalog/index`、`drills`、`parser_tmp`、`qa`、`wheel-test`、`worker_runs.jsonl`、满足精确旧attempt命名的stdout/stderr日志。不扩张为所有log/tmp/sqlite目录；staging可能含未完成原件，继续保留。

先复核进程和paused控制、路径/reparse及实测文件数；正式source-reader CLI实读已有四份原件。清理前后比较公司原件目录文件名/size/mtime清单摘要、完整生产DB SHA、配置SHA、保留的derived/staging/security_master/artifacts与旧unknown费用run清单。实际删除后再做同四份原件CLI读取。产出一份JSON和简短说明；不完整备份或恢复全库。

无代码变更不跑全仓长测；真实CLI与保护快照就是本批端到端验收。一次性清理脚本执行完删除，收据提交。

### B：关闭旧生产与消费路径，避免再长回去

1. RF在独立worktree基于当前main实施；先读现有PWF及生产调用者，保留owner工作。本地TDD先验证：正式source preparation只消费SourceRef v2，只有原件而没有derived时也能成功；证据SHA/公司/期次/as-of错误仍拒绝；结果没有物理路径及旧artifact正文读取。继承现有v2 record/reuse receipt合同，不新建来源类型或任务库。
2. 实际调用者显式使用现有catalog配置接线：缺配置给可诊断的配置错误，不能通过猜目录或偷偷落回legacy掩盖。更新调用者与CLI默认一起交付；仅改默认bool却让生产入口缺配置失败，不算完成。
3. 清查FF与其他有证据的旧SourceBundle消费者：已用v2的不用重改；实际仍读旧正文的迁现有source-reader/narrative接口。历史JSON、测试夹具和.planning副本不能算活动调用者。现有wire不随清理任意改版本。
4. `extract-sections`公开CLI与服务API已退休。旧自动`SourceCatalogWorker`及其阶段策略也已删除：实查src/scripts没有生产导入/调用者，CLI无启动命令，现场没有匹配进程或Windows任务。保留worker-status/worker-stop用于残留进程清理。公开normalize/summarize/summarize_with_llm writer已退，低层历史fixture模块尚未整体退出。依赖需区分：RF默认SourceBundle仍读取normalized等旧artifact角色；CWP EvidenceQueryService仍从SQLite读取旧EvidenceSpan正文/locator；已发布质量v2优先读有界精选final，无final时才兼容未退休旧normalized metadata/span，retired或未处理为metadata_only。均不打开旧normalized正文文件。CWP直接读取normalized正文的代码点为`llm_summarizer.py`、`section_extractor.py`、`summarizer.py`；公开`extract-sections`入口已退休，但低层函数/其他调用者仍要核实。保留DB spans不要求永久保留Markdown正文；只有RF和CWP实际正文消费者迁移/退休后，才能删物理文件。删除前还须把artifact记录改成不可复用的退休状态并明确quality语义，不能保留指向不存在文件的“completed”句柄。数据库EvidenceSpan缩减另按D/S6执行。
5. `fingerprint-backfill`单独对待：当前从raw现场抽取后只保存小型文本指纹，可用于等价来源复用，不依赖永久normalized。若保留，继续有界按需，不将其作为重建全部派生的理由。`export`是显式可再生索引，不作为常驻第二库；本次删index不会取消用户按需export。

集中验证RF来源准备v2责任集、FF→CWP pathless真实CLI离线链和CWP正式有限Worker端到端。只运行受影响包；不得调用付费模型、下载真实资料或写穿生产配置来测试入口迁移。提交/推送后核实际主线，不用未提交候选当切换完成。

### C：derived与artifact记录同批退役

- B的活动调用者迁移/退休后，确认新读取仅依赖原件/SourceRef及新final包。不要要求23,530个文档全部重新生成摘要，未请求的保持metadata_only。
- 按固定旧generator/role/path范围找旧artifact，区分active/prepared新final包；新`.source_catalog/artifacts`不是旧`.source_catalog/derived`，不得一起删。
- 在事务内退休旧artifact可消费状态/清理对应派生记录，保留必要的generator/hash退役摘要；不能留下可复用handle指向已删文件，也不能假造成功handle。删旧derived后重跑相同四份raw read与新final/consumer读取。
- 所有原件及sources/documents/locations/roots、source_metadata_assertions、revision/amendment/supersession、撤回/恢复audit不变。来源变化真实发生时具名失败，不能为删缓存改原件hash。
- 实际释放量按删前/删后bytes写收据；2.826GB是候选历史值，不是预先宣称收益。失败保留阶段事实和定位，不自动还原2.8GB缓存，更不重启旧全量Worker。

### D：全量旧span降为按需精选span，再收缩DB

先核`EvidenceQueryService`/CLI evidence-list、extraction-quality、scanner存在性判断和统计调用者。对每个入口给明确去向：原件按locator读取、现有narrative bundle的精选span、metadata_only/尚未解析的质量状态，或明确退休旧全量列举功能。不能把“未处理”伪造parsed，也不能以空结果掩盖旧引用无法回放。

TDD至少框住：精确source+locator能验原件并回放；原件hash不符/locator不存在具名失败；未请求原件不永久全文建span；既有新summary引用可回放；source版本与撤回不变。外仓旧span_id若有实际消费者，先迁至已有SourceRef+locator或保留它确实引用的小集合，不能靠全量冷库躲过降容目标。

审计已确认1,490,530条旧span全部属于active文档；只prune retired无收益。待调用者切换后删除不可再消费的旧全量span与相关派生状态，保留小型canonical选材/final来源事实。schema仍可保留空表以兼容必要查询；不为“表数量更少”破坏合法read API。

删除和VACUUM分别记录：逻辑freelist增加不算真实释放。对来源事实做一个小型恢复点，禁止完整3GB/46GB备份演练。运行时核临时空间足够、无活动writer、事务与外键一致；提交后收缩再校验来源事实计数/hash、四份原件实读与新final回放。未知失败不删除恢复材料；成功后收尾小恢复点。

## 一个存储大节点的验收接口

### B剩余生成器分层节点（2026-10-06，先计划后实施）

前置事实：P5-FF已main758e8f4/精确CI GREEN；STORAGE已验收e570daf，生产处置未执行。RF专用树8a153f33、有17份tracked WIP及两份新增测试、无HANDOFF，MAIN不碰。CodeGraph首查后以当前tracked AST补足imports：正式代码通过service指纹补算及__init__两个历史类型加载旧生成器；正文reader生产caller只有旧生成器自身。零caller不能单独证明无依赖。

写集仅CWP source_catalog、相关tests/support和测试、MAIN PWF/收据；保持SourceRef/NarrativeRef、指纹算法及历史artifact字段/hash。其他仓库、生产raw/derived/span零写入，不加许可flag。

1. TDD：安装包不存在全文normalize/summary/sections writer及其正文reader，普通catalog导入不加载旧生成器/测试模块。指纹实跑只存小型状态、不建artifact/span/derived且重复幂等。原文篡改、解析期间换字节、manifest与候选来源不符均具名失败，后续健康文件照常完成。
2. normalizer保留临时格式解析、子进程期限/清理、raw-text指纹算法及retry状态；移出normalize_catalog、frontmatter和全量写入。旧造数器/summary/sections/正文reader仅放tests/support以保留历史读/清理夹具，不复制原文解析器；setuptools仅打包src，src/scripts/tools不导入测试模块。此节点不冒称已删除所有历史专属测试。
3. 删除未被实际产品使用的LLMSummaryError/SectionSlice public导出；历史generator registry/version作为旧artifact识别数据保留。读链计数删除退休writer，旧生产者源码断言改为安装包无writer与历史metadata绑定，不虚构路径维持门禁。
4. 指纹复用manifest实字节验证，解析前/后检查原件，manifest source_id/SHA必须与调度row相等。不加人工review/ACL/新库。历史fixture故障注入指向真实所属层，不能为GREEN恢复runtime writer。
5. 大节点集中测公开退休、原文parser/指纹、受影响历史读/质量/清理及有限Worker E2E。真实年报PDF+电话会TXT仅复制到独立短根：原SHA不变，artifact/span/derived零新增，parser临时结果清理，finally恢复absent；零外部下载/模型请求，不逐helper签收。
6. GREEN后正常commit/push、核精确CI、更新caller收据/PWF。生产2.826GB派生及旧span/VACUUM仍待RF默认v2验收，代码边界完成不等于已释放生产空间。

交付字段：代码HEAD/远端HEAD、实际退出/迁移入口、集中测试命令与结果、集合前后files/bytes、DB前后bytes/page_count/freelist、保留事实摘要、真实原件CLI读数、新summary引用回放、network/model调用数、残留问题及下一动作。

不增加release授权文件、人工签名、逐文件签收或固定场景数量。A可在N4外线施工期间先做；B–D由MAIN协调共享接口，N4C成果可用后再做集中存储迁移验收。本卡尚未宣称B–D已实现。

## B 本仓旧写入 API 退出（2026-10-05，MAIN当前执行）

CodeGraph首查未收录部分旧模块/函数，不能以其“无调用者”证明不存在；补充当前Git tracked src/scripts/root Python AST核查，334个文件只有service内部调用旧batch writers，另有artifacts/gates旧演练调用。运行入口已不注册normalize/summarize/extract-sections；正式有限叙述Worker从verified raw选材，不依赖这些方法。本轮仅退出CWP public writer，不改RF/P5外包写集和生产资料。

1. 先写公开行为TDD：SourceCatalog不存在normalize/summarize/summarize_with_llm/extract_sections；实例化或拒绝旧CLI不创建catalog/derived、不调用网络。scan/source reader/指纹按需backfill及新有限Worker仍可使用。
2. 删除service的三个legacy writer forwarders及对应imports；public类只保留来源/原件索引与读接口，实际叙述任务由现有automation管。不能替换成另一套同名writer，也不新增环境/许可flag控制旧入口。
3. 历史fixture测试仍需构造旧artifact以验证读兼容、SHA、撤回及未来清理。不让这些测试要求恢复正式旧writer：仅在tests/support增加明确的legacy造数helper，接受已有fixture catalog，调用尚未退休的底层legacy parser/fixture generation，保持测试目录隔离。把调用public旧方法的夹具准备改为这些helper；保留读行为断言。该helper不得被src/scripts/tools导入，不是新运行接口。旧writer内部实现与专属测试在所有读消费者迁移后下一集中节点继续删除，不冒称本轮已完成全部legacy正文模块退役。
4. 旧slow-canary演练是历史artifact，未作为生产入口。公开入口退役后不得将它用于新项目运行；从当前运行指引剔除，不以它恢复旧normalize。原始公司文件、历史来源事实、DB spans/artifact句柄均不变。
5. 集中验证：公开退役合同、受影响的历史读/清理/指纹/质量fixture tests，以及正式有限Worker独立CLI E2E；无付费模型/真实下载。只跑相关包，暂不删除2.826GB derived或3.06GB DB。完成后提交/推送、核CI并更新PWF。RF默认消费切换仍归P5-RF，物理删除仍待B其余消费者和C记录状态语义完成。

## 2026-10-04 B步骤当前进度

公开extract-sections CLI与SourceCatalog.extract_sections方法已在71f867a退休；入口TDD 3项RED后，入口/纯章节解析/历史artifact binding集中48项GREEN。保留低级章节解析用于历史隔离夹具，不将其算当前公开生产入口。旧normalize/summarize库兼容方法、RF旧默认及旧derived/artifact/span主体仍待迁移，B–D没有整体完成；原件/生产库未变。

## 2026-10-05：旧整库Worker退役与S5依赖边界

生产源码/脚本没有`SourceCatalogWorker`导入者；其原始CLI启动入口已早先退出，现场另查无对应进程与计划任务。删除`source_catalog/worker.py`、仅供该循环使用的`scheduler_policy.py`及专属调度/Worker可靠性测试；保留控制面status/stop/uninstall。为了保住仍工作的读取和迁移夹具，不删除`SourceCatalog.normalize/summarize/summarize_with_llm`、低层normalizer、摘要实现、EvidenceSpan、normalized artifacts或RF消费接口。RF默认`source_reader_v2=False`，仍读旧SourceBundle normalized角色。CWP evidence-query直接查DB span；extraction-quality查DB artifact状态/metadata与span，均不打开Markdown正文。正文读取代码仍见于CWP `llm_summarizer.py`、`section_extractor.py`、`summarizer.py`，其生产调用者需逐项核清。后续切分为两个大节点：先迁移/退休全部normalized正文消费者，更新artifact句柄与quality语义并删除物理Markdown；DB EvidenceSpan保留，待S6单独核消费者和压缩收益。此前“查询/质量直接依赖normalized文件”的表述过宽，本段按源码实际读路径更正。

旧Worker退役集中责任包：`test_source_catalog_legacy_cli_retirement.py`、background/control/architecture、tier1、fingerprint、现有summary/pipeline/section tests，**127 passed / 64.28s**。第一次受限sandbox执行125 passed、两失败（spawned parser与python-docx原生扩展被系统限制）；同一正常用户上下文单测复核两项通过，完整同集重跑127项通过。测试专用目录已清理。调试脚本最初从stdin运行不适用于Windows multiprocessing，改用带`__main__`的短文件后诊断并删除。一次跨用户权限清理测试目录被拒，原创建者清理后在同一正常用户作业中创建/清理专用根。


## 2026-10-05 工具节点已完成后的顺序

P5-STORAGE四操作工具已通过53个不同case分步验收并合入master@e570daf；真实年报+MSFT TXT原文/叙述完整回放和fixture恢复均GREEN。只读预览、当前对象绑定、未unlink恢复、范围SQL切片、实际空间/VACUUM和失败观测已落实；没有执行生产删除。工具位于tools/legacy_storage_retirement.py，操作说明在tools/legacy_storage/README.md；最新节点收据在总PWF/harness_lanes/results/p5_storage_integration_acceptance_2026-10-05.json。旧handoff样本只作历史追溯。

MAIN接下来核实际旧底层generator/EvidenceQuery/ExtractionQuality caller，落实metadata_only与精选叙述reader行为，然后验收RF默认SourceRef迁移。在消费者/质量语义已迁且原文/新final读取可用后，才用该工具处理生产的known legacy范围，报告生产前后实际空间。仍不做全备份恢复演练、不新增人工签收、不重跑每文件小门。

## MAIN当前质量节点实施细则（2026-10-05）

1. `extraction-quality`保持只读诊断，发布明确的v2输出（新的状态不能冒用v1合同）。当前visible叙述包优先；通过既有read-only artifact facade与NarrativeBundle严格合同实读有界final、校验对象SHA和来源绑定，只输出计数/locator，不输出正文、路径或摘要。诊断注明它没有验证当前原件字节；消费者实读仍由正式narrative transport负责SHA与完整回放。不得让质量查询下载、转换全文或调用模型。
2. 已有旧normalized未退休且无visible final时，保留旧metadata/span一致性检查作为迁移兼容；旧artifact retired后不再读取全量旧span。不要求重建。原件未请求/旧提取退休为metadata_only；有效skip final为skipped_no_narrative；partial/needs_review是技术诊断，非人工签收门；source撤回/无active location仍不可用。final损坏或身份冲突明确报错，不静默退回旧数据。
3. TDD先覆盖原件only、retired+旧span、selected/skip/partial final优先与无旧span依赖、prepared不提前可见、损坏final拒绝、body-free/只读/locator限额。复用已有真实三任务DAG夹具；关键CLI E2E增加固定SHA的微软原TXT副本，查询质量后正式transport回放，退出恢复测试目录。零网络与外部模型。
4. 集中相关quality/artifact/transport回归；只新增低成本公开行为到适合的责任包，真实解析E2E仍在integration。不添加日常长CI、逐文件审查或人工授权文件。完成commit/push并观察精确代码SHA CI。
5. 本节点不等于EvidenceQuery已迁，也不允许生产prune。下一个节点把evidence lookup/list接原件回放/精选包或明确metadata_only；再接RF外线默认v2交付，最后实际旧derived/span处置。

**本节点已完成：**dd35d2f已在master/远端，55个不同case分步GREEN，真实TXT质量CLI/正式transport原件SHA与全部引用回放、目录恢复通过。精确CI37378430383 attempt1 success。[实际收据](harness_lanes/results/s5_quality_migration_acceptance_2026-10-05.json)。quality不再依赖退休旧span；EvidenceQuery/sections-list/scanner/stats以及RF默认仍需下一节点核清，生产不能提前prune。

### 下一查询节点的具体边界

- 已查当前328份生产Python直接imports和RF/FF/StockWiki运行literal references；旧EvidenceQuery唯一明确公开运行入口是CWP evidence/evidence-list。补核实际v1 caller后，没有活动消费者可明确退休旧全量CLI，既有原件SourceRef读取与NarrativeRef精选读取负责资料访问；不重新造query库/任务表/存储配置。
- 新读取必须绑定现有artifact版本及source SHA，不以裸loc:v1坐标猜新parser的段落。原始正文读取用现有SourceVersionReader、精选引用用正式transport完整回放；quality v2只用于body-free状态/locator展示，不等于raw验证。
- TDD集中覆盖退休入口拒绝不建目录/不写库、正常SourceRef原文读、NarrativeRef精选body/locator实读、未请求metadata_only、损坏原件/版本变化具名失败、跳过不造span。对尚有真实v1消费者的路径先迁或仅保留其确实引用的小集合。历史夹具仍可构造旧span，但不得被生产导入。
- 同节点核sections-list、scanner存在性判断、stats旧artifact/span依赖，分别判定纯诊断可留还是正文入口需退；不能为了删表破坏合法来源检索，也不能因空span自动重建全量。仅在这些责任及RF默认迁移交付已通过后，执行生产C/D。

### 精选查询节点实现细则（MAIN写集，2026-10-05）

1. 正式narrative-read CLI增加精选 `evidence-list` / `evidence-lookup` / `evidence-search` operation；沿用现有NarrativeReadRequest输入及完整transport核验。旧reference/read的字节/receipt wire保持原样。list/lookup/search输出一个pathless来源view及其SHA/size小收据，不输出旧绝对路径或读取旧artifact/span。
2. view始终固定NarrativeRef.artifact版本；lookup以span_id或已绑定版本的locator精确匹配，零/多匹配具名拒绝，不把旧裸坐标猜成新段落。分页/检索limit上限500，非法输入在raw读取前拒绝。搜索只对已精选正文按现有BM25排序；不要检索模型摘要并当原文。已有分组summary_input纯函数供试点与正式view复用，转换仅在本次内存，不落磁盘。
3. 正式transport先验原件SHA、来源身份/期次/as-of并完整回放final所有locator；view标明selection/coverage/quality。policy skip返回明确空精选状态，不假造parsed；只有raw无final时沿用reference not-found与quality metadata_only，不自动下载/解析/LLM。损坏当前final/原件绝不落回legacy。
4. TDD先验证新公开operation、现有wire不变、精确版本/lookup/有界分页/中英搜索/skip，以及坏SHA/as-of和非法参数拒绝。独立端到端使用固定SHA微软原TXT及有业务叙述的合成PDF，中英/跨目录/无旧span场景；测试根退出恢复，原件SHA不变，0模型POST/网络。相关节点一次验收，不逐helper或逐文档加门。
5. 同步退出source-catalog旧evidence/evidence-list/sections-list运行命令及旧公共backend exports，保留显式历史backend fixture读兼容；旧CLI成功测试改测退出公开入口与正式view，不弱化当前原文/引用校验。scanner引用保护与status计量保留：它们没有生产调度/重建语义。更新运行文档和PWF后commit/push，精确代码CI绿。
6. RF/FF外线文件不动，生产derived/span暂不删除。新版view接通后仍待RF默认卡验收和旧generator/reader实际caller收口，最后生产处置。已有reference/read/SourceRef/SourceExport正式合同不升级，也不另加人工签收。

**本节点验收完成：**102个不同case分步GREEN，集中100 passed/2失败后仅6受影响cases GREEN23.41s，非重跑全包。两处修正是公开错误名与退役旧CLI断言；来源/旧backend事实校验未放宽。真实MSFT TXT search→lookup/全部引用回放/原始SHA、四类型持久文件集合/SHA不变及s5vred/green/final测试根恢复均通过。实际read/reference goldens保持原字节；0外部model POST，0生产删除。Ruff/diff-check GREEN；1b0feb4已发布/精确CI绿。[小收据](harness_lanes/results/s5_selected_retrieval_acceptance_2026-10-05.json)。

**发布已完成：**代码1b0feb44ff1695a8bae761eac538ce68236c04d6已推送master；正常commit/pre-push均GREEN，用户配置SHA保持。CI37381429717 attempt1 completed/success，所有步骤GREEN。质量/公开精选读取两个节点已关闭，整体S5仍待FF/RF外线、旧generator实际caller与生产处置，不复跑本节点102项。

## B剩余生成器边界验收（2026-10-06）

代码b148123d1ada7d0d222574b6b5852f976c2985e8已master发布，精确CI37388329668已completed/success，所有步骤GREEN。公开/指纹/读链65 passed，兼容160 passed/2 skipped，Worker+工具3 passed，stdout修复后解析/指纹31 passed；229个不同case分步GREEN，非单次全包。真实年报PDF+电话会TXT通过公开scan/backfill/重复backfill，原SHA及来源事实不变、0新artifact/span/derived、短根恢复absent。运行模块净退出2182行旧生成器，343份生产Python无test-support imports；历史generator registry/version是旧数据识别，造数器仅在tests/support，不是生产入口。小收据见harness_lanes/results/s5_generator_retirement_acceptance_2026-10-06.json。

未完成的边界：RF默认v2交付仍无HANDOFF，兼容SourceBundle还可能读旧artifact；生产处置须等该卡验收。FF758e8f4已并线/精确CI绿，STORAGE工具e570daf已验收；不能再写两卡待验收。下一步用已验收工具只读预览生产清单、核RF交付，然后做已规划retire-derived/prune/VACUUM大节点；不新增签收、完整备份或逐文件测试。
