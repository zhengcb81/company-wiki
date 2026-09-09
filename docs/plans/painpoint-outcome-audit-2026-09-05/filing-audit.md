# filing-fetch 与跨仓多根/下载真实性审计

日期：2026-09-05 开始，2026-09-06 08:04 BST 恢复核对。状态：completed_static_and_pure_probe_audit；并非产品验收完成。只读代码与证据；仅本文件是本审计写入物。父任务维护 task_plan/findings/progress；本报告不修改既有计划或源代码。

## 方法与范围

按原始 P02/P03/P04/P10 及 ZR-201–206、ZR-401–409、ZR-805 逐项检验。先 CodeGraph 获取生产结构，再读取具体实现、测试与收据；不运行生产 resolver/ensure/close-gap/worker、不联网、不写数据库。已有 accepted 不视作真实用户结果。

## 已确认的初步事实

- filing `scripts/filing_contracts.py:449–484` 已对携带的 policy export 重算文档 hash，并仅选 `reusable_for_filing=true` 的 root；`:485–486` 仍保留无 policy 时 companies 兼容回退。这说明旧 companies-only 问题局部已修，不证明当前上游每条路径都发送且执行同一 policy。
- `validate_handle:509–514` 校验原文件大小并一次性 `read_bytes()` 重算 SHA；因此大 PDF 每次调用至少做一次全文件读取，内存峰值随文件大小线性增长，重复零解析不等于零 I/O。尚未量化现场 p95。
- `src/company_wiki/source_catalog/acquisition.py:resolve_or_stage` 目前调用 `SourceResolver(self.catalog)`，构造器还触发 `self.catalog.store`。必须继续追踪 SourceResolver 的默认行为及 CLI 接线，不能仅凭未传参数认定旁路仍然存在。
- 原始 ZR-407 明文验收为“无授权 discover/fetch=0”；filing `latest_as_of` 路径不论 allow_download 都走 ensure，因此需区分元数据发现授权与下载授权的真实合同，不能直接将现有 metadata-only 行为解释为符合原文。

## 限制与错误

- CodeGraph explore 合并结果被截断；没有声称已完整读取被截断内容，后续按具体区段补读。
- 未改动任何旧计划、代码、配置、收据；不把历史 live 下载成功当今天 current-triplet 成功。
- 查阅 `scanner_facade.py` 时发现该文件不存在；实际 facade 位于 `scanner.py:1375 scan_root_strategy`。已定位，不重复错误路径。
- 收尾 targeted git status 成功列出本文件为新文件，但读取用户 `.config/git/ignore` 权限不足产生warning；未改Git配置或尝试越权。本文件165行（后续本条追加后166行），未将warning解释成产品问题。

## 1. 基线、判定与总体结论

恢复后的 HEAD：company-wiki `853dca2d30bc2b85dc95e3117a6afc3b448daec7`；filing-fetch `89c8bdb2cfba4d88720d005d0558f422957e8ade`；revenue-forecast `2ff20d9b410d3498181f7258a23ed9625caab826`。前两个与 9/5 一致；revenue 相对先前 `2cbd585e` 仅修改 daily scheduler 与对应测试，不覆盖本报告的 filing/resolver/gap 实现。其他线程可能持续修改，结论锚定本次读取字节与上述观测点，不代表以后 HEAD。

原始问题并未全部解决。已经有实际资产：只读 Reader、policy export 的 hash/containment 校验、修订版 actionable 分支、按事务单飞锁、错误分类和指数退避。但端到端仍有关键反证：生产 resolver 与 ensure/close-gap 执行不同 reader policy；全局 canonical 未与请求 eligible 分离；freshness 仍按 accession 词序而非修订时间；多项 gap 只处理首项；期限重试可能越界；失败之后下载事实可丢失。部分“完成”的工作单元只新增测试、缩窄验收面，或把真实 T3 留作未执行 opt-in。

判定细分：CONTRADICTED = 当前实现或纯探针反证原验收；PARTIAL = 有可保留实现但接线/用户结果不完整；HISTORICAL_ONLY = 历史实跑不足以证明当前；SUPERSEDED = 后续明确决策改变要求，不以旧标准误判。

## 2. 逐项完成真实性账本

| 单元 | 原始目标/痛点 | 判定 | 当前证据与局限 |
|---|---|---|---|
| ZR-201 | P02，无写 Reader 工厂 | PARTIAL | `reader.py:157–181` 不存在 DB 先拒绝，URI mode=ro/query_only；没有 mkdir/DDL/commit。原 implementer 明确 WAL 协议可能创建空 side 文件，验收已从绝对“零文件写”收窄为 DB/WAL 字节及 SHM协议例外。本次未做真实库只读连接，不能覆盖 OS/WAL 全状态。 |
| ZR-202 | P02，typed reader 和 schema 门 | PARTIAL | reader 有 typed查询和 schema 检查；通用 `fetchone/fetchall(sql)` 仍暴露，SQLite query_only 拒绝写 SQL。静态存在 ≠ 所有生产调用 schema 门完整；生产接线问题由 ZR-203 判。 |
| ZR-203 | P02，所有只读生产入口无 writer initializer | CONTRADICTED（完整用户语义） | `cli.py:753` exact no-download ensure 已只读；`:760–762` latest no-download ensure 却显式初始化 store，且走 journal。filing latest 未授权下载也调用 ensure，因此“只查询最新资料”仍非全程只读。原收据还移交 duplicate-preview store 遗留，本次不以未复查该遗留作新反证。 |
| ZR-204 | P02，锁/超时错误分类 | PARTIAL | filing `_classify_wiki_error` 消费 canonical catalog_locked/busy/db_timeout，未知形态 fatal；旧 raw OperationalError 类名兼容仍不识别，只有当前 wiki canonical 路径受支持。锁分类已改进；不得把完整 retry/outcome 算此项独立完成。 |
| ZR-205 | P02/P10，deadline+阶段事实 | CONTRADICTED | 纯 clock 探针：10秒期限，子调用耗9秒后 busy，仍 sleep5秒，总14秒。使用子调用前 remaining；结构化 gap main 输出不含 calls/downloads；close-gap失败及handle验证失败的计数仍可丢失。见 F-F05/F-F06。 |
| ZR-206 | P02，49GB/live-writer SLO | HISTORICAL_ONLY / PARTIAL | 历史收据真实49.62GB T2在 worker暂停窗口执行；live writer为合成T1，不能拼成“真实49GB live writer全链”。历史 status/health p95约6.3秒、query约1.2ms是typed方法，不含三进程、完整SHA读取、provider、重试。当前未重测。 |
| ZR-401 | P03，严格RootPolicy3.0/no隐式权限 | CONTRADICTED（接线）；部分SUPERSEDED | 3.0 loader存在但 `config.py:64–65` 生产只接受1.0，`:144` privacy默认为public，CLI policy export用2x，非3x。生产Dropbox private要求已被9/3 owner的全roots public决策取代，不能当安全违例；但是严格loader、必填权限、单一snapshot接线目标未因此自动实现。 |
| ZR-402 | P03，adapter通用路由 | PARTIAL | registry/dispatch按adapter_id失败封闭可保留；`adapter_dispatch._to_scanner_candidate` 仍调用 scanner._infer_company按路径推断实体。receipt称移交ZR403，而ZR403纯测试无产品修改。v2 facade只在flag开启才执行；未知/缺runtime snapshot fallback v1，非通用loader全链闭环。 |
| ZR-403 | P03，global canonical与eligible location分离 | CONTRADICTED | `service.py:621–665` 先按健康active/priority选全局canonical；`resolver.py:912–939` 只筛is_canonical，再验root kind。高优先级禁用root的canonical可遮蔽低优先级可用副本；per-root reusable=false未参与resolver。原7测试多为全root获准/健康排序，并不证明目标顺序policy→health→priority。 |
| ZR-404 | P03，一致policy/epoch/cohort与解释 | CONTRADICTED | CLI resolve传runtime_policy；acquisition及close-gap finalize未传，默认v1/bridge。ensure事后读runtime policy贴envelope，实际选择与标签可能不同；close-gap finalize连policy_snapshot与policy_export都未带。新增4字段/格式校验不证明选择一致。 |
| ZR-405 | P03，filing任意获准root | PARTIAL | `filing_contracts.py:449–497` policy自校验和真实path containment可保留；外部root纯handle测试存在。上游close-gap缺policy_export会落N-1 companies回退；resolver若先选禁用canonical，filing安全拒绝而非尝试可用副本。当前真实three-repo journey未得到证明。 |
| ZR-406 | P04，正交freshness与修订 | CONTRADICTED | 当前纯函数4个探针反证，见F-F03；year-only分桶忽略季度/半年期间键，accession词序仍代替时序；39测试收据甚至记录把fixture accession改成递增词序以通过。 |
| ZR-407 | P04，授权bound缺口补齐 | PARTIAL / CONTRADICTED（完整范围） | `newer_revision` 已被纳入actionable是真修复；但close-gap仅actionable[0]、hash不绑定完整候选；exact allow_download路径authorization=None仍可fetch。后者可能是旧CLI显式flag授权语义，却与原ZR-407无authorization discover/fetch=0及scope/hash/TTL要求不一致，必须作契约决策而非自称已满足。 |
| ZR-408 | P04，staging/commit/单飞/恢复 | PARTIAL | 同一binding事务hash锁与进程级测试是有效资产；不同合法authorization绑定同一候选→不同锁，未证明单候选跨binding至多一次。commit失败结果fetch_events=0可与实际fetch冲突；多gap只提交一项后仍可completed。未运行故障提交，不宣称已发生生产重复下载。 |
| ZR-409 | P03/P10，第四根与真实三仓旅程 | PARTIAL | 卡片实际C2只调用wiki resolve；将三仓用户旅程缩成三root resolver样本，T3移交后续且3.0loader再延期。future_lake为空占位+合成测试不等于真实第四root从revenue入口消费。filing已纠偏E2E设计明确synthetic companies-root reuse-only。 |
| ZR-805 | P10，真实CN/HK/US首次+复用 | HISTORICAL_ONLY / CONTRADICTED（完成证据） | 11receipt新增3个授权/静态测试，明确真实T3“需用户网络授权=blocked/opt-in”，side_effect downloads=0/real_catalog_access=0。旧filing v1.3三市场下载成功是旧版本历史，不是当前triplet T3结果。此处不是网络故障认定，是完成主张范围不足。 |

## 3. 关键发现的证据链和推理

### F-F01 — 同一请求的 policy 会在 resolve/ensure/close-gap 之间退回旧行为（高）

1. `resolver.py:721–748` 明确：runtime_policy缺省时 reader=v1、current_epoch=None、active_cohorts=()、legacy_bridge_allowed=True。
2. `cli.py:1175` resolve显式传policy；`acquisition.py:resolve_or_stage`初始解析与discover后解析均只构造SourceResolver(self.catalog)；`cli.py:753`只读ensure也无参数；`close_gap.py:460`finalize无参数。
3. `cli.py:805–818`在ensure执行后另读runtime policy贴policy_export/envelope；这不是原请求执行上下文。并发CAS可能进一步造成时点不同，但无需并发也已存在reader模式差异。
4. `close_gap.py:477–494`finalize不传policy_snapshot，resolution.to_dict无policy_export。filing `_handle_from_resolution:889–903`因此走N-1兼容，envelope的null policy也不强制拒绝。

结论：原P03“旧选择披新策略回执”不是只存在于旧报告，而是当前代码可达。修复要求：不可变RequestRuntimeContext只加载一次，注入所有再解析、gap revalidation、bundle和finalize；N-1必须由显式peer版本协商，而非字段缺失自动降级。

### F-F02 — 多根选择仍是 global canonical 先行，per-root拒绝不能挑选健康替代副本（高）

`service._annotate_locations`无请求policy参数，按priority定is_canonical；resolver先限定is_canonical后仅验证root.kind。其root IDs集合忽略 `RootSpec.reusable_for_filing`；反观`policy_2x._effective_reusable_2x`明确优先per-root字段。两层合同不一致：wiki可能给出禁用root，filing按export拒绝，或可用副本被global canonical遮蔽而出现missing。不能通过取消filing containment修复，必须在上游请求级selection改正。保留全局canonical作去重展示，但它不能控制本次可用location。

### F-F03 — freshness 仍错误使用 accession 词序；候选集合与hash不够精确（高，纯函数复现）

完整读取`gap_plan.py`确认只有标准库导入，无数据库/文件/网络副作用后，以`python -B -c`按绝对文件import执行。样本均为Synthetic company、FY2025、as_of=2026-09-05，未调用任何provider。结果：

| 探针 | 输入 | 实际输出 | 违反目标 |
|---|---|---|---|
| newer_date_lower_id | local=z-old/2026-03-01；remote含z-old及a-new/2026-04-01 | newer_revision=[]；not_published=true | 较新修订被旧ID字典序压过 |
| older_only_remote | local=a-new/2026-04-01；remote只有z-old/2026-03-01 | newer_revision=[z-old] | 旧远端被当成新修订，可能倒退或多下载 |
| missing_same_period_two_revisions | 无local；remote含同期间z-old、a-new | missing=[z-old,a-new] | 不按最新修订合并，首项可是旧版 |
| url_and_date_changed_same_gap_hash | 相同year/id的source_url及filing_date改变 | same_hash=true | 授权plan hash不能证明精确候选元数据未变 |

根因：`:167–170`max键=(accession,amended)，`:180–184`无本地时extend全部候选；`:214–247`hash只串接request/asof/year/accession及provider error，不含canonical序列化、source URL、期间、候选大小或修订日期。字节hash不负责猜远端未下载内容，但至少应冻结发现候选的身份/期间/URL/修订元数据，并在fetch提交验证。

另外`acquisition._gap_plan_result:470–479`对所有无year latest请求使用as_of_year-1，即使quarterly/semi也如此；`gap_plan`按fiscal_year一桶，未采用period_end/fiscal_period。原计划要求非自然年和期间语义，不应把FY2025多个季度折成修订关系。

### F-F04 — CloseGap只关闭首个actionable，且授权强度/计数不全面（高）

`close_gap.py:263`只取actionable[0]，`:292–315`只调用一次_fetch_and_commit，finalize只要求任何可复用文档而不要求重算后所有授权缺口关闭。因此多项gap可留剩余而status=completed。当前包络download_events仅0/1也反映单项实现，不能在不升级合同情况下假装支持完整多缺口事务。

`acquisition.py:425–444`仅authorization非None时校验；exact+allow_download由CLI ensure直接驱动，source request的authorization并未在普通ensure注入。`authorization.py:123`remote_size未知视0，只对事前元数据校验cap；coordinator fetch后_validate_receipt无max_bytes重新核验。因此“有显式flag”不等于“有精确候选+TTL+字节预算授权”。这是契约与资源边界缺口，非断言已越权下载。

同一binding的单飞用`_txn_id(binding)`，hash含expires_at/max_items/max_bytes等授权字段。不同授权针对同候选会产生不同lock；现有跨进程测试共享同binding，没有击杀此变体。应将授权核验与候选幂等键分离，仍分别保存每个请求的合法授权与结果。

### F-F05 — deadline-aware retry 的实现会睡过deadline（中，纯探针复现）

`fetch_filing.py:304`在subprocess前计算remaining，`:325–337`遇busy后复用该旧值而非重新读clock。安全probe只patch时钟、底层call和sleep：deadline=10，底层call将clock推到9后抛busy，sleep记录5，最终clock=14再抛upstream_error。没有实际等待或子进程。输出为`{"deadline":10,"elapsed":14.0,"sleeps":[5.0],"code":"upstream_error"}`。

另cap作用在backoff基值，乘+20%jitter后60秒可变72秒；若要求硬cap60，需在jitter之后再clamp。close_gap内部重试sleep1/2也没有统一deadline参数；外层杀子进程不是完整资源取消协议。

### F-F06 — 下游失败仍可能把已下载写成0，gap输出丢计数（高）

1. `close_gap._fetch_and_commit`在adapter已fetch后，canonical writer异常返回其局部_fail，硬编码fetch_events=0；未保留fetch成功阶段。
2. finalize re-resolve失败虽保留fetch_events=1，但filing `_close_gap_and_return_handle:1009–1013`只抛gap_not_closed，未复制closed计数/阶段/已有resolution。
3. filing stats.downloads只在handle最终验证通过后`_record_download_events`更新；若真实下载已提交但handle hash/policy验证失败，main可输出downloads=0。未知应是unknown/ledger-backed实际值，不能用缺省0作“零下载”证明。
4. main对structured gap直接output=handle，不加入calls/downloads/schema；一般Exception fatal分支也不带stats。ZR205“最终成功/失败均有对账”未覆盖完整分支。

### F-F07 — 性能闭环只测了局部接口，没有测用户请求总时延（中）

- filing每次至少identify+resolve两个独立Python进程；allow_download默认还涉及worker status/pause/resume，latest授权后可分别在ensure和close-gap两段重复pause scope；这些是可见阶段，不应混进一个“resolver快”结论。
- validate_handle用read_bytes再SHA，峰值至少一份文件内容；可改分块hash降低内存，但不能未经身份/mtime/inode稳定性设计便缓存跳过真实性校验。
- close-gap会pre-lock metadata discovery、in-lock再discovery、exact staging时再次discovery。每次都可能启动provider子进程；重复发现是否可复用必须有快照TTL及锁内重校合同，而非简单删检查。
- 历史49GBT2 typed方法p95不包含上述成本；本次未作生产profile。后续报告需要分阶段wall/CPU/I/O bytes/peak RSS/subprocess/lock等待/provider/parse/LLM/commit，用p50/p95/p99和重复调用对照，而非给未实测提速百分比。

### F-F08 — 完成保证证据不能替代真实结果（高）

- ZR406收据主动记录将accession fixture改为顺序递增，使词序假设不暴露；新增39测试不能推翻本次反例。
- ZR409卡片把跨仓旅程缩成wiki CLI三样本，且3.0loader延期到阶段I/CA303；这是范围债务，不是全目标绿。
- ZR805收据明说真实T3未执行，不能用旧三市场或静态检查`skipUnless`证明current T3。
- FC903 `12_reviewer_receipt.json`绑定implementer rawSHA=`010d0b9e9f4547ef2a71d9e7b47a90eb768744c8dca4825fe6b32ea157bdb3df`；本次Get-FileHash实际=`010699cab407eb20aafd7f985ed494e262d84f2fd0c3c479e83c2c1ed96f089d`。保持原收据，不重新签名；应找原签署字节/重新独立验证，不能用新hash机械替换证明reviewer曾审过。
- `validate_resolution_envelope:317–335`所谓bundle hash校验只检查外层与bundle内字符串相等，不重算bundle内容。按薄客户端边界它可不重做artifact validity，但本身不能证明内容hash已验证；要确保真正消费者或生产端做canonical recompute，需独立篡改负例闭环。

## 4. 建议纳入父任务详细修复计划的工作包（未实施）

所有修复等待父任务完成全部审计后编排；本节是审计建议输入，不是修改授权。每包关键节点安排不同于实现者的独立agent，审查失败则停止，不自动放宽测试/改golden。

### FF-WP1：请求上下文与读语义（P0，先于其他包）

1. 冻结当前最小红例：v2 active+legacy off样本，比较resolve、exact ensure无下载、latest无下载、close-gap re-resolve的可见集合及policy/epoch。所有夹具在隔离目录，writer/network探针默认拒绝。
2. 独立agent先审合同：元数据discover是否允许网络、写journal是否属于只读；列出版本协商与N-1允许面，禁止字段缺失隐式降级。
3. 引入一次加载的不可变context，在wiki入口构造并传给resolver/coordinator/transaction/bundle/envelope；文件级范围仅相关模块及测试。strict loader切换另做迁移预览/doctor，不能直接升级生产config。
4. 检查点：所有production SourceResolver构造可证明context绑定；采集/重解析全链不得事后读另一个snapshot贴标签；mutation去掉任一注入必须红。
5. 独立agent审diff+调用图+运行轨迹；隔离OS只读DB、缺DB、WAL已有/缺失和long writer分开验收，记录SHM协议写例外。最后才申请只读真实root验证，不启动worker。

### FF-WP2：请求级eligible选择（P0，依赖WP1）

1. 夹具同SHA两副本：高priority被policy拒绝、低priority健康允许；反转root顺序；每root explicit true/false/omitted；kind允许但root禁止；symlink逃逸和大小hash漂移。
2. 只从全部healthy原始location做policy→health→priority→稳定tie-break选择，返回global_canonical与selected_location两个不同字段，不改物理canonical文件。
3. 独立agent核验无allowlist扩大、拒绝原因准确、filing仍失败封闭；没有Windows symlink权限则明确blocked并安排有权限环境，不把skip记绿。
4. 所有四root均从revenue→filing→wiki真实子进程路径验证；无复制到companies、零provider/fetch/LLM，前后原文件hash集合一致。

### FF-WP3：期间/修订和授权候选（P0，依赖WP1/2）

1. 把本报告4探针固化红测试，扩展非自然年、同年Q1/Q2/H1/FY、日期缺失、amended发布日期、providerID任意字符串、future、同候选多版本。
2. 独立agent先审每market官方元数据映射合同；无法确定revision顺序应unknown/ambiguous，不用词序猜。仅改变词序的property应不改变freshness。
3. Canonical JSON候选快照hash纳入provider、实体、期间、版本、URL、已知size、发现时点/TTL等合同字段；明确哪些可变字段允许重新发现。修改URL/日期/期间的mutation必须使授权失效或要求重新绑定。
4. 多gap明确逐项事务结果partial/completed与remaining列表；若产品暂只支持一项，应显式unsupported/partial，不能completed。
5. 精确模式与latest统一授权政策；如保留flag-only兼容，必须单独限权且不得满足强授权验收。未知远端size要求streaming硬预算，下载后校验实际bytes，超过预算不commit。
6. 独立agent审负例及授权可撤销/TTL/预算，验证无授权network/fetch=0符合已定合同；真实provider测试需另外明示网络和字节授权。

### FF-WP4：单飞、阶段账本和截止时间（P1，依赖WP3）

1. 修复前固定clock探针和故障矩阵：fetch完成→commit抛错、commit成功→re-resolve失败、handle校验失败、响应JSON损坏/超时；每种均保留阶段事实而非缺省0。
2. retry异常后重算remaining；jitter后应用硬cap；内部coordinator/lock/provider共享deadline及取消token，不仅依赖外层超时杀进程。
3. 候选幂等键独立于authorization字段；不同TTL/cap的两个合法请求竞争同候选、同binding竞争、不同候选并行均测试，独立adapter append-only日志作fetch oracle，catalog/文件hash作commit oracle。
4. 统一stage envelope：planned/discovered/fetch_started/fetch_completed/validated/committed/resolved；downloads与fetch_calls/commits分开，未知为null+reason；gap和fatal路径也携带已知调用事实。
5. 独立agent审crash点恢复、staging残留和锁回收；不得为过绿删journal或重置真实状态。T1通过后另申请小cohort真实故障演练。

### FF-WP5：端到端性能与证据重建（P1，依赖WP1–4）

1. 先只用隔离同文档大小阶梯和clock/network spy量化进程启动、身份、SQL、路径、SHA、discovery、lock、writer；冷/热缓存及首/重复请求分开。
2. 实际优化候选：分块hash降峰值；同request复用已验证metadata与context；避免无下载时worker暂停；明确安全TTL下复用discovery；有证据后再考虑进程复用。每一优化保留完整性与外发negative tests。
3. 独立性能agent比较同HEAD相同样本/环境p50/p95/p99、RSS与I/O，报告绝对耗时，不用synthetic小query证明用户大PDF速度。
4. 审计FC903原签署字节，必要时重新独立执行并建立新receipt链；保留原记录及撤销/替代关系，禁止批量自签当历史review。
5. 真T3三市场与三仓四rootjourney分别设门，blocked/skip不计passed。任务注册/自然周期证据归父计划统一运维包，不能把本包T1当Daily/Weekly自然运行。

## 5. 本次实际执行清单与未执行边界

- 已执行：CodeGraph结构定位；原P01–P11目标和相关ZRregistry；filing根计划/状态/E2E设计；ZR201–206、401–409、805相关卡片/receipt针对性读取；具体生产实现静态追踪；FC903rawSHA计算；4个GapPlan纯函数反例和1个mock-clock deadline反例；HEAD差异核对。
- 未执行：pytest全量、真实库probe、任何ensure/close-gap/scan/worker命令、provider联网、下载、生产压力测试、安装镜像同步、Git提交、task/scheduler修改。因用户要求先审计，未以这些未执行项作通过结论。
- 写入物：仅本文件。未修复源代码；新发现应由父任务统一合并到新目录findings/覆盖账本和详细计划。
