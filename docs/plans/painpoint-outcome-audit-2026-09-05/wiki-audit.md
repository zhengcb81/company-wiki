# company-wiki 原始痛点独立审计

状态：审计子任务已完成（只读代码/已有证据审查，未重新执行生产验收）；2026-09-05 开始，2026-09-06 续审。只读检查代码、测试、已有生产证据，不运行 worker、不打开生产数据库、不修改原文件。下述 UNVERIFIED 不表示失败；PARTIAL/CONTRADICTED 均保留已真实实现部分。

## 初始事实与限制

- `reader.py` 已提供 `mode=ro` 和 `query_only=ON`；其类注释明确承认 WAL 模式缺失 sidecar 时 SQLite 仍可能创建空 `-wal/-shm`，因此“零数据库写”不能直接扩大成“任何环境零文件写”。需要检查现有测试覆盖及生产只读接线。
- `processing_demand.py` 明确是纯内存队列，单此模块不证明真实需求持久化和 worker 消费；后续检查实际调用及新生产接线，不能据此直接判定系统未实现。
- 初次 CodeGraph 未指定项目时对 CatalogReader/ProcessingDemand/submit 搜索均无结果，需确认项目索引；不是证明符号不存在。

## 待核验

- ZR201–206、ZR301–307、ZR501–510、ZR1002–1008 的生产路径、测试、真产物与验收差异。
- P02/P05/P06/P07/worker 与 GP010 超 cohort 事件。

## 已验证接线差距（阶段记录）

- ZR-304：`producer_journal.py` 定义 `PRODUCER_ATTEMPTS_DDL/record_attempt/calls_this_request`，但 src/scripts 字面引用扫描仅命中定义文件；`store.py` 仍用 artifact INSERT trigger 写 `producer_events`。这不能记录失败、超时、重试且未产 artifact 的真实调用。需进一步检查跨仓消费；不得把 event=0 声称 API call=0。
- ZR-507/508：`processing_demand.py` 的 DemandQueue 只有纯内存状态；src/scripts 的唯一外部接线为纯 scheduler 模块。`test_zr1006_broker_cohort.py` 明示 C2–C5 纯内存/临时库、C1生产仅快照。当前证据不支持真实持久化 submit→worker→completion→跨进程 dedupe 已完成。
- GP-010 现文档明确 normalized7/7、summary6/7、sections5/7；summary 1份安全拒绝不是应绕过的失败，sections 2份仍是产品缺口。
- CodeGraph 索引 status 显示543文件、10534节点，能找到 CatalogStore 但找不到磁盘上的 CatalogReader/ProcessingDemand；此次 explore 返回旧 service 路径，不能将其符号缺失当成实际无代码。接线以已定位文件及 import/字符串检索复核。
- 错误日志：初始猜测 processing.py/bundle.py/artifact_contract.py/llm_summary.py/page_fidelity.py/table_fidelity.py 不存在；已转为文件列表定位实际模块，不重复猜测。

## 1. 审计基线与并发变化

2026-09-06 08:05 BST：company-wiki HEAD 为 `853dca2d30bc2b85dc95e3117a6afc3b448daec7`，与上一轮相同。工作树并非干净：原有旧计划删除、成本日志等保持原样；新增并发修改 `src/company_wiki/source_catalog/section_extractor.py`（把 document_kind 分派提成 `_extract_sections_for_kind`）和 `tests/contract/test_fc906a_producer_binding_metadata.py`（为 annual 夹具加 sidecar）。只读 diff 显示这两项不实现需求持久化/TTL/SQL 性能修复，也未改变7份生产产物计数的已记录证据。未覆盖或修改它们。

本审计引用的 ZR implementer receipt 属历史执行记录，不把 receipt 自述等同独立当前验证。凡称“测试有覆盖”，指本次阅读测试代码看到对应断言；没有声称本次重新运行全部测试。生产计数取已存在的9/5独立复核记录，未读取49GB生产数据库。

## 2. 关键发现：原痛点没有随 completed/accepted 全部消失

### W-01 — 队列 SQL 回归及永久重启放大机制仍在代码中（P0；CONTRADICTED）

原痛点是8/12起无产出且慢，不是“写好了改进计划”。`docs/worker-investigation-2026-08-20.md` §1/§6 保存的历史性能链：提交 `0ee0d09...` 加相关 EXISTS；生产约23530文档×25046 active locations，缺统计/匹配索引时选 status 单列索引；worker 96.8%单核、90.9MiB、物理磁盘<3%，902秒无 parser 启动；等价非相关查询0.231秒。末成功周期 normalize queue 约610秒/总696秒，parser仅约1秒。该报告已有现场采样，而本轮未重跑以免负载/写 sidecar。

当前 `normalizer.py:1572–1591` 仍相关 EXISTS + `store.fetchall(sql, params)`，进度/should_stop 检查在SQL返回后才进入文档循环。`store.py:241–249` 仍列单列document/status与root/role/status索引，没有证明原目标查询计划已修好。`worker.py:540–543` 先只改内存扫描状态，`:848`附近才周期末 `_write_state()`；supervisor `scripts/source_catalog_worker.ps1` 仍 `RestartResetSeconds=900`、`WorkerHangTimeoutSeconds=900`，退出处理以 uptime 达阈值清失败次数，而不要求成功进度。这保留了“扫描→SQL无heartbeat→watchdog杀死→失败数被清→低延迟重启→再扫描”机制。注意：无法由静态代码断言当前查询一定仍耗902秒，但没有当前修复/等价生产规模验收依据，不能宣称痛点解决。

v5 `task_plan.md` 明确只完成 V5-0 导入/V5-R退役；V5-1版本合同、V5-2冻结和三路审查、V5-3交接仍pending，且本阶段不实施worker修复。应将“调查完成”“隔离完成”“计划导入完成”与“worker恢复完成”拆开。

### W-02 — 停机隔离仍有正证据，不能借本审计恢复（RESOLVED_CURRENT/有限范围）

08:08 BST 只读观察 `.source_catalog/worker_control.json` 为 desired_state=paused；HKCU Run 的已知 `CompanyWikiSourceCatalog` 值不存在；launcher log尾仍2026-08-20 `persistent_pause`，runs尾仍8/12，未出现新产出周期。Win32_Process CIM查询遭拒绝访问，所以当前所有匹配进程是否为零是 UNVERIFIED，不能写“已经独立确认无进程”。此次没有枚举所有启动任务/服务，也不扩大成所有未知入口均关闭。

### W-03 — Producer journal 和唯一 artifact read model 停留在模块/夹具层（P1；CONTRADICTED）

`producer_journal.py` 有 append-only attempts DDL、record_attempt、request_id过滤，确是有价值的新能力；但对 src/scripts 字面导入/引用检查只命中定义文件，`store.py` 没采用其DDL，normalizer/llm_summarizer没调用record_attempt。`resolver.py:513–522` 仍用 `producer_events.count_producer_events` 填 parser_calls/llm_calls；后者数 artifact INSERT trigger 的全历史成功产物，不是当前请求全部真实调用。失败/超时/安全拒绝且无artifact的调用不可由该数恢复，复用时历史计数也不会自然归零。

`artifact_read_model.py` 已实现 bindings/metadata/columns归一，但无生产调用；`service.py:441–463` 直接从 artifacts列取数据后调用build_source_bundle，无bindings join/read_artifacts。ZR305的 `test_apply_then_real_source_bundle_consumes_binding` 调用测试辅助 `_artifacts_for_bundle(cat)`，在夹具中补齐字段后直接调用纯builder；这不是 SourceCatalog生产入口消费 migration binding 的证明。ZR304收据明确“既有产品零改动”，恰好揭示模块新增与生产接线目标间的缺口。

已解决部分：`artifact_handle.py:100–104` 已拒绝空sourceSHA并比较源SHA；normalizer/LLM producer写schema/sourceSHA；service bundle支持源hash漂移拒绝及role独立拒绝。不能为修补接线而降低这些门。

### W-04 — 实际需求只在单进程内存中“submit”，CLI退出即丢，worker未消费（P1；CONTRADICTED）

wiki `processing_demand.py` 明示pure-memory；仅 `scheduler.py` 消费该队列。真实 `worker.py` 导入的是 `scheduler_policy.SourceOnlySchedulerPolicy`，并非DemandScheduler，没有持久化demand claim/complete路径。revenue `scripts/source_preparation.py:27–52` 另有一份进程级DemandQueue，`_submit_preparation_demand` 把source key、kind=source_preparation、now=0.0入内存，`:194`附近提交后return，CLI结束后状态消失；下游被safety阻断时甚至在该提交之前raise。其注释承认persistence是later phase。

ZR507的lease/dedupe/backoff、ZR508的aging/budget单元机制确实存在；但不支持跨进程持久化、重启恢复、调用者查询完成、pause后诚实pending、重复请求不重做解析/LLM。ZR1006 C2–C5显式是pure-memory + tmp DB，不能补这个实际缺口。

### W-05 — LLM出口未接入TTL/policy判定，注释与执行相反（P0；CONTRADICTED）

`llm_summarizer.py:11–15` 声称TTL/reviewed_at与policy_hash由readiness graph逐文档保证。实际 `summarize_catalog_with_llm:366–429` SQL只校验receipt schema/status/sourceSHA和root privacy，随后`:430–459`读normalized文件并 `client.generate`，没有调用evaluate_review/evaluate_readiness。全src引用扫描亦只见readiness_graph自身，且该模块头明确shadow-only/no production wiring。一个sourceSHA仍相同但review TTL过期或policy已换的receipt仍满足这条LLM选择SQL；这是有代码证据的出口缺口，不只是“未找到测试”。

现有正向保护：receipt缺失/源SHA不符被SQL排除，private root排除，`_FORBIDDEN_OUTPUT`确实导致7份中一份summary拒绝（应保持fail-closed）。9/3 owner已批准生产roots全部public，这是一项后续边界决定，不能凭旧private_user痛点要求本次擅改回去；但未来新增root/未知privacy默认允许的兼容行为需要显式版本与授权验收。

额外输入绑定风险：该SQL取normalized_sha/source_sha但在generate前不验证当前normalized文件hash与artifact sourceSHA/status；人工改写/旧版normalized被替换是否会外发，缺真实入口负例。应在出口临调用前校验同一不可变输入快照，不能只核原始文件的receipt。

### W-06 — 生命周期“ready”的部分语义弱于用户目标（P1；PARTIAL）

`source_lifecycle.py`：freshness只检查published_date非空，artifact只要求任意completed row，semantic只要求任意parse_ok span，identity查询verified assertion未限制active可见性。`readiness_graph`只加强safety缓存，其余沿用。这不是严格证明provider latest、可消费bundle、目标roles齐全、多实体fact正确。模块叫unified readiness不应掩盖定义差异；应作为局部原型而非真实消费放行真源，直到强契约与生产路由完成。

### W-07 — retry分类把确定性ProgrammingError当超时（P1；CONTRADICTED）

`error_taxonomy.py:58–63,79–85` 将序列化/真实 `ProgrammingError` 无条件映射db_timeout/retryable=True。sqlite3的绑定参数数错误、使用已关闭连接是编程错误，不是需要bounded retry的锁；这违反该文件自述non-lock-never-retryable。真实锁/timeout结构化输出已接CLI，方向正确；需单独添加这些确定性负例，不能为避免异常一概重试。

### W-08 — Broker端有真实局部推进，但不能把7PDF+2HTML全链验收改成“长江形状文本”测试（P1；PARTIAL/CONTRADICTED）

normalizer `_frontmatter:1424–1530` 已接首页身份、entity检测、regex sections/facts和chunk attribution；page-aware adapter保留页/表格cell坐标；9/4broker sections能力也已进入真实入口。这些不是纸面零实现。

但 ZR504/505测试主要构造已解析pages/table数组来断言adapter fidelity，无法测真实PDF抽取表格准确率；ZR510把原“7PDF+2HTML真canary、日期/页码/表格/事实/归属”缩成CHANGJIANG_TEXT合成段落的9测试。`html_capture.py`在src仅定义，未见normalizer/consumer入口调用。`extract_facts`仅metric/value/unit没有source/locator/entity/period，frontmatter只放chunk_count不存chunk边界；不能称完整FactAssertion/tag/跨页table artifact消费完成。未知/无匹配返回空是诚实行为，但空输出不能替代目标语义成果。

生产目标最新已有记录是normalized7/7、summary6/7、sections5/7（9/5 `planning-sync.../final-independent-review.md:36`，及GP010状态页）。2份列表式研报没有sections；1份LLM summary被安全门拒绝3次。应允许安全拒绝成为终态但保留功能缺口与后续“source-only摘要策略”的独立验收，禁止为绿灯放行评级/目标价。

### W-09 — Cohort约束未在执行入口强制，已发生752候选/214写入（P0；CONTRADICTED）

revenue `assurance/runs/2026-09-02_remaining-gap-closure/progress.md:152` 明确记录调用 `catalog.extract_sections(document_kind="broker_research")` 导致eligible752/completed214/skipped538，超GP010批准7份；owner随后决定保留全部。事后保留授权解决当前产物处置，不修复执行前越界控制。

`section_extractor.py:250–314` 仅有可选document_id/document_kind/limit，document_kind选择所有该类，无cohort manifest/hash/count强制门；service仅operation lock包装。该入口允许精确单份，因此操作失误并非API不能精确选取，但也说明批准范围未被机器校验。应在mutating入口要求明确allowlist与dry-run exact set，防“一个kind”被误当“批准7份”。本审计不删除214产物。

## 3. 逐项核验表（覆盖分配给本子任务的30项）

表中“未有当前真验收”不等于代码失败；第三列列的是局部实现/测试，第四列是仍缺的用户结果。

| 注册项 | 判定 | 已有证据/真实解决层 | 原验收缺口与对应发现 |
|---|---|---|---|
| ZR-201 | PARTIAL | reader.py mode=ro/query_only、不存在路径不mkdir；test_catalog_reader覆盖缺失/OS只读 | WAL缺sidecar仍可创建文件；零数据写≠零文件写。真实live-WAL只读/sidecar缺失/目录ACL matrix需分别验收 |
| ZR-202 | PARTIAL | typed document/source/artifact/query/status/health方法存在 | status/health全量COUNT约秒级历史证据；未验证当前triplet全部schema/pressure；不得说全查询低延迟 |
| ZR-203 | PARTIAL | SourceCatalog lazy writer，status/query/resolve/bundle用reader；test_zr203读路由/CLI门 | AST gate只查直接CatalogStore调用，不能证明所有间接写无副作用；artifact unique read view仍未接，W03 |
| ZR-204 | CONTRADICTED | cli/identity_cli使用structured_error，锁分类机制存在 | 全ProgrammingError可重试违反非锁不重试，W07 |
| ZR-205 | PARTIAL（跨仓详审） | ZR307卡及实现收据承认filing已有deadline/attempt/stage | revenue source_preparation仍generic RuntimeError并失trace；错误taxonomy误重试影响；由filing子审计补精确retry断言 |
| ZR-206 | HISTORICAL_ONLY/PARTIAL | t2/evidence/zr206_t2_probe.json 8/17真49.62GB/27178657spans；status p95=5755ms health=6148ms，unit livewriter/temp机制 | 当前未重测；reader查询SLO不是worker normalize queue SLO，W01不能被此通过覆盖 |
| ZR-301 | PARTIAL | 八stage ConsumerRequirements/evaluator及9测试；明确shadow | stage satisfied标准过弱、无真实consumer强合同，W06 |
| ZR-302 | PARTIAL | scan_text/RULESET_HASH/evaluate_review缓存、TTL/source/policy负例；生产7 receipts历史 | helper安全门未真正守所有LLM入口；W05 |
| ZR-303 | CONTRADICTED | graph合成35-test suite中的9graph测试 | 仍shadow且LLM注释误称已接；并未形成一个生产machine decision graph，W05/W06 |
| ZR-304 | CONTRADICTED | attempt/read_model函数、mandatory sourceSHA验证存在，9夹具测试 | producer无attempt接线、service不读unique view、resolver数成功artifact全历史，W03 |
| ZR-305 | CONTRADICTED | 五桶dry-run/apply幂等、保留legacy rows；5测试 | 测试手工merge字段直接builder，并非production service消费bindings；W03 |
| ZR-306 | PARTIAL | artifact_dag角色闭包、6property tests | 真producer选择仍按artifact存在跳过，prompt/model/config变化并未真实触发工作队列最小重算；W04；手工oracle算法形似实现需不同表达复核 |
| ZR-307 | PARTIAL | 原卡目标/receipt实现filing resolution_trace透传（非debug） | safety graph仍future接线；revenue prepare_source在非0处RuntimeError，只保留stderr尾800字符，无法算全程8stage证据。filing子审计单独核 |
| ZR-501 | PARTIAL | sidecar元数据不按filename编事实、非filing拒绝、page_count进入normalizer | 七真研报publisher/author/date/security/page独立golden核对缺口，不能从sidecar夹具推全覆盖 |
| ZR-502 | PARTIAL | sidecar不成primary；homepage identity写frontmatter与质量flag | contradiction flag是否拦截真实consumer/LLM无闭环证据，W05/W08 |
| ZR-503 | PARTIAL | entity检测与multi_entity_attribution_needed接frontmatter | 文档多实体flag≠各fact实体精确归属，W08 |
| ZR-504 | PARTIAL | adapter物理页与paragraph/offset顺序，normalizer render接线 | 测试已构造pages数据；真PDF parser页序、双栏读序golden尚未由这些测试证实 |
| ZR-505 | PARTIAL | typed cell矩阵及locator/render负例 | adapter单测不测真实PDF表格识别/跨页/单位精度；不能宣称真实broker table artifact闭环 |
| ZR-506 | PARTIAL | regex detect_sections/chunk_spans/extract_facts、frontmatter真实接线 | 没完整tag/FactAssertion/source locator/period合同，列表研报5/7问题仍在，W08 |
| ZR-507 | CONTRADICTED | 纯内存enqueue/lease/retry/dedupe14 tests | 不持久化、不worker消费、不跨CLI幂等，W04 |
| ZR-508 | CONTRADICTED（生产目标） | pure DemandScheduler aging/deadline/cost预算11tests | 实际worker用另一scheduler_policy，不能证明真实fairness/budget运行，W04 |
| ZR-509 | PARTIAL | parse/validate_html_capture纯函数12tests，wrong-strategy合成HTML拒绝 | 无生产引用/两份真实HTML抓取消费链，W08 |
| ZR-510 | CONTRADICTED（原范围） | 长江形状合成文本多实体attribution + normalizer接线9tests | 原7PDF+2HTML全chain验收被缩成shape test，W08 |
| ZR-1002 | PARTIAL | Reader在service已实际接；test_zr1002 temp activation/rollback/SLO | 测试明确hermetic，无当前生产release/rollout/caller完整证明；不得由临时activate表断言零写生产恢复 |
| ZR-1003 | CONTRADICTED（观察周期） | temp assertion activation/rollback，safety receipt与flag测试 | “two dynamic cycles”实际两次同一catalog shadow读相等，非两个自然周期；graph仍未守生产出口 |
| ZR-1004 | PARTIAL（跨仓详审） | receipt：7 tests真实roots只读resolve+浅fingerprint+重复request；产品零改动 | 原逐root T2/UJ cohort rollout/同request rollback不等于重跑read结果一致；由多root子审计验证 |
| ZR-1005 | PARTIAL | test宣称C1生产dry-run>10min；C2–C4 tmp shadow binding apply幂等 | 生产small-cohort apply并服务消费无此测试证明，W03；不得为本审计重跑全库 |
| ZR-1006 | CONTRADICTED（实际worker） | C1生产7份normalized快照；C2–C5内存cohort1→3→7机制 | 生产GP010是人工调用且超cohort，未提交持久demand/真实公平调度/自然resume；W04/W09 |
| ZR-1007 | PARTIAL（revenue详审） | receipt12 tests mine shadow vs legacy公式、reconcile/backtest、零run_forecast | 无生产mine事实消费/真实cutover结果；此项具体模型由revenue子审计负责 |
| ZR-1008 | PARTIAL（revenue详审） | receipt10 tests draft/formal/replay/rollback/3cycle，1.22s执行 | 1.22秒的3cycle不可替代自然观察期；source前端demand/安全/worker仍W03–05缺口 |

## 4. 后续修复工作包建议（仅供主审计汇总；不实施）

这些步骤是审计派生建议，不是运行授权。每包进入实施前均须由独立agent核对原痛点→代码入口→负例→期望输出；实现者不得自审，也不得凭原accepted收据免审。

### WP-W1：恢复normalize队列有界执行及worker进度合同

1. 冻结精确SQL/排序/force/retry语义与生产规模分布，不复制生产秘密；构造至少25k文档/25k多location、9506无primary、重复位置、source mismatch、冷/热cache、无统计/有统计夹具。
2. 独立性能agent先对等价非相关候选/复合索引方案设计审查：候选集、前N顺序、重复、缺root、force、due retry都必须等价；禁止先改大库ANALYZE/索引当作隐式修复。
3. 在隔离库实施SQL与索引迁移策略；EXPLAIN禁止按每文档反复status全扫；分别测select/parse/write/export。定量门从v5 acceptance_thresholds正式冻结，不用本次历史0.231秒随意作为通用绝对门。
4. 队列查询有独立deadline/cancel/heartbeat，heartbeat表示活跃不能代替成功进度；scan完成即原子checkpoint，crash重启不应重复整扫；失败backoff只能由有效成功进度reset，不以uptime重置。
5. 故障测试：SQL挂起、parser挂起、LLM挂起、checkpoint前后kill、磁盘满、暂停中途、stale PID复用、连续3次失败；每步独立agent审查真实调用/进度时钟/停止延迟。
6. 取得新授权后才最小生产cohort，先无LLM/无删除，展示CPU/磁盘/队列等待p50/p95/stop时间/产物增量；独立验收同一冻结版本，明确回滚。未经用户恢复授权保持paused且不增自启动。

### WP-W2：建立唯一持久化需求与实际attempt真源

1. 先冻结source+role+inputSHA+producer/schema/prompt/model/config组成的任务key、状态机、pause/defer/terminal语义、返回demand_id和查询API；将现有两套内存队列列为legacy adapters，而非再建第三套。
2. 独立数据一致性agent审查attempt start/finish双事件、crash未知结局、request_id关联、quota计数、provider retry每attempt记账；统计区分attempted/succeeded/artifact_created与历史/当前，不用INSERT trigger代理调用数。
3. 实施只写自身受控catalog的持久队列与原子claim/fencing/lease；跨repo通过API/CLI提交，不跨仓直接写DB；worker真实claim执行，paused时持久pending且向caller回原因。
4. 用独立进程A submit、B worker、C查询测试；A退出/B crash/restart/重复100request同key/expired lease双worker/terminal重试权限均有oracle；重复已完成且输入不变应零新parser/LLM，变化只最小DAG子树。
5. 独立测试agent不得调用测试可见内存queue当E2E；必须真实CLI、状态文件/事件哈希与副作用探针共同证明。

### WP-W3：统一artifact读取并接真实消费

1. 冻结columns/metadata/binding precedence与active/shadow冲突策略，源SHA/fileSHA/schema/generator/allowed-root都fail-closed；明确sourceSHA非空修复不得回退。
2. SourceCatalog.query_source_bundle/reader.bundle/CLI resolver都接同一view；在真实service入口构造legacy列缺字段、有效active binding、shadow binding、binding冲突、文件丢失/改hash/未知role负例。
3. 新测试禁止在测试辅助器预合并成“已经正确”的artifact；必须先调用migration apply，再通过真实resolve CLI取bundle，检查只允许的角色变可复用；two dry runs幂等/rollback恢复旧视图，历史artifact字节不动。
4. 独立reviewer对source→binding→artifact→bundle→consumer receipt逐字段抽查，确认当前request producer counts与WP-W2一致，再批准有限cohort迁移。

### WP-W4：安全与readiness真正位于外发边界

1. 把安全输入明确为本次实际外发bytes（normalized artifact SHA与原source SHA双绑定）、当前policy hash、now/TTL、root授权与document identity状态；独立安全agent审设计，避免误把“公开来源”当无限内容授权。
2. 临client.generate之前统一evaluate_review/hit门，校验artifact status/current sourceSHA/fileSHA；SQL预筛只能优化，不能代替最终门。
3. 用spy LLM factory（绝不联网）测试missing/expired/boundaryTTL/changed policy/source drift/normalized drift/contradiction/private/unknown-root；每个拒绝都是factory或generate=0的独立断言，request同时保留已成功resolution阶段。
4. 将freshness改为请求模式/provider证据判断，artifact改verified bundle required roles，semantic按具体consumer合同，不用任意completed row/任意span充当ready。所有blocker带next_action但不自动越权下载/外发。
5. 安全拒绝的summary保留终态并记attempt；只在新授权cohort内评估更严格source-only摘要策略，不调松_FORBIDDEN_OUTPUT绕过评级/目标价。

### WP-W5：Broker真实语义与cohort防越界

1. 冻结7PDF+2HTML不可变SHA名单，独立标注publisher/date/物理页/标题/表格cell/单位/实体/period/locator黄金集；另选非紫金、多栏/跨页表/列表式报告/无实体网页反例，避免姓名硬编码。
2. 在mutating API入口强制cohort manifest+expected count+policy hash；dry-run输出精确document IDs，执行前CAS核同一集合；kind-only/空名单/名单新增/越界ID必须零写拒绝。独立agent先审此门，再允许真实加工。
3. 页/表格验收从真实PDF parser输入开始，不从人工已解析pages数组开始；结果写source-oriented table/fact contracts并有locator、实体、period、unit、置信与unknown原因；研究判断不入wiki。
4. 列表式2份报告设计独立策略或明确unsupported终态，不让反复无section占队列首；保证一般标题与列表内容不伪造section。HTML identity接真实导入入口，wrong strategy fail-closed。
5. 1→3→7通过WP-W2真正需求消费，每阶段验收exact scope、旧hash不变、失败隔离、实际调用/成本；独立agent逐阶段审查，不能仅最后看artifact总数。
6. 752/214历史事件仅保留owner决定与原产物，不在本包擅自删除；补根因、越界门负例与回滚精确名单，事后保留不视作防越界完成。

### WP-W6：完成保证与测试诚实性

1. 所有上述ZR保留原accepted为历史，当前痛点结果单独判定；禁止擦写旧receipt以抹去“产品零改动”事实。
2. 将test_zr1003“两次同读”、1006“内存cohort”、510“长江形状”、1008“1.22s三周期”等明确归T1机制；自然T2/T3窗口须真实调度时钟/宿主/版本/触发事件，不靠重放循环补天数。
3. 独立agent审每个关键节点的实现与负例、生产路由、真实副作用证据；证据含命令/环境/精确triplet+dirty hash/输入hash/期望业务结果/实际结果，reviewer不得只复用实现者oracle。
4. 最终主审计必须把本表30项与其他两仓合并去重；ZR205/307/1004/1007/1008跨仓行的本报告只负责wiki影响，完整闭环由相应子审计补齐，不重复计算通过。

## 5. 本轮未做与错误记录

- 未打开生产SQLite、未重跑49GB探针、未启动worker/生成summary/处理PDF/联网、未修改旧文档或源代码；仅在新审计目录增改本文件。
- CIM进程查询拒绝访问；未以空输出冒充零进程。Git全局ignore与.pytest_cache权限警告不影响显式目标代码读取，但不声明全仓可读取/干净。
- 猜测历史报告路径不存在后通过rg文件列表定位到 `docs/worker-investigation-2026-08-20.md`；猜测read_errors.py不存在后定位error_taxonomy.py。一次PowerShell传给rg的字面`*.md`路径不展开，改为目录+`-g '*.md'`。
- 合并CodeGraph/大量收据输出曾截断，已对用于结论的具体文件/行单独复读；不声称逐字读完所有未引用附录。
