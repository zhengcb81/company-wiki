# S5/S6：旧派生退出与来源库降容实施细则

> MAIN负责执行，不是新的外包卡。复用总计划S5/S6存储节点，不增加逐文件或逐helper审查。N4-T1/T2保持各自写集，本文件不授权修改它们的施工目录。原件、来源版本和撤回事实保留。

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
4. `extract-sections`公开CLI与服务API已退休。旧自动`SourceCatalogWorker`及其阶段策略也已删除：实查src/scripts没有生产导入/调用者，CLI无启动命令，现场没有匹配进程或Windows任务。保留worker-status/worker-stop用于残留进程清理。按需normalized writer和摘要模块尚未整体退役。依赖需区分：RF默认SourceBundle仍读取normalized等旧artifact角色；CWP `EvidenceQueryService` 从SQLite读取EvidenceSpan正文/locator，`ExtractionQualityService` 从SQLite读取normalized artifact状态/metadata及span，两者不打开normalized正文文件。CWP直接读取normalized正文的代码点为`llm_summarizer.py`、`section_extractor.py`、`summarizer.py`；公开`extract-sections`入口已退休，但低层函数/其他调用者仍要核实。保留DB spans不要求永久保留Markdown正文；只有RF和CWP实际正文消费者迁移/退休后，才能删物理文件。删除前还须把artifact记录改成不可复用的退休状态并明确quality语义，不能保留指向不存在文件的“completed”句柄。数据库EvidenceSpan缩减另按D/S6执行。
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

交付字段：代码HEAD/远端HEAD、实际退出/迁移入口、集中测试命令与结果、集合前后files/bytes、DB前后bytes/page_count/freelist、保留事实摘要、真实原件CLI读数、新summary引用回放、network/model调用数、残留问题及下一动作。

不增加release授权文件、人工签名、逐文件签收或固定场景数量。A可在N4外线施工期间先做；B–D由MAIN协调共享接口，N4C成果可用后再做集中存储迁移验收。本卡尚未宣称B–D已实现。

## 2026-10-04 B步骤当前进度

公开extract-sections CLI与SourceCatalog.extract_sections方法已在71f867a退休；入口TDD 3项RED后，入口/纯章节解析/历史artifact binding集中48项GREEN。保留低级章节解析用于历史隔离夹具，不将其算当前公开生产入口。旧normalize/summarize库兼容方法、RF旧默认及旧derived/artifact/span主体仍待迁移，B–D没有整体完成；原件/生产库未变。

## 2026-10-05：旧整库Worker退役与S5依赖边界

生产源码/脚本没有`SourceCatalogWorker`导入者；其原始CLI启动入口已早先退出，现场另查无对应进程与计划任务。删除`source_catalog/worker.py`、仅供该循环使用的`scheduler_policy.py`及专属调度/Worker可靠性测试；保留控制面status/stop/uninstall。为了保住仍工作的读取和迁移夹具，不删除`SourceCatalog.normalize/summarize/summarize_with_llm`、低层normalizer、摘要实现、EvidenceSpan、normalized artifacts或RF消费接口。RF默认`source_reader_v2=False`，仍读旧SourceBundle normalized角色。CWP evidence-query直接查DB span；extraction-quality查DB artifact状态/metadata与span，均不打开Markdown正文。正文读取代码仍见于CWP `llm_summarizer.py`、`section_extractor.py`、`summarizer.py`，其生产调用者需逐项核清。后续切分为两个大节点：先迁移/退休全部normalized正文消费者，更新artifact句柄与quality语义并删除物理Markdown；DB EvidenceSpan保留，待S6单独核消费者和压缩收益。此前“查询/质量直接依赖normalized文件”的表述过宽，本段按源码实际读路径更正。

旧Worker退役集中责任包：`test_source_catalog_legacy_cli_retirement.py`、background/control/architecture、tier1、fingerprint、现有summary/pipeline/section tests，**127 passed / 64.28s**。第一次受限sandbox执行125 passed、两失败（spawned parser与python-docx原生扩展被系统限制）；同一正常用户上下文单测复核两项通过，完整同集重跑127项通过。测试专用目录已清理。调试脚本最初从stdin运行不适用于Windows multiprocessing，改用带`__main__`的短文件后诊断并删除。一次跨用户权限清理测试目录被拒，原创建者清理后在同一正常用户作业中创建/清理专用根。
