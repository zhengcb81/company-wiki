# 三仓原痛点修复总计划（隔离待批准，不实施）

> **R4状态覆盖（2026-09-07）**：本文正文是R3历史方案/测试细节库，已不再作为活动执行队列。唯一活动编排为[R4实施计划](simplified-execution-plan.md)，测试见[R4矩阵](simplified-test-matrix.md)，原WP归属见[迁移表](r4-transition.md)。仅按迁移表继承领域步骤、反例与原始成果要求；不执行下文旧G0–G5依赖或95门DAG。历史review只签当时字节，本次新增状态头使当前文件hash变化，不能宣称旧签收绑定修改后文件。旧gate-dag.json及validate_execution_plan.py原样保留为R3历史工具，不用于R4验收。文档更新不授权产品实施。

版本：R3，2026-09-07；保留R2门级依赖并新增逐步执行手册与G3隔离测试边界。R2历史review只绑定当时字节；R3及执行补充另见execution-independent-review.md。全部审计范围已记录于unit-ledger、GP、历史项目及分报告；动态未验证项不冒充已完成。此文只是未来施工方案，不是修改产品/生产运行授权，不并入现有主线或v5目录。

## 0. 先读边界，禁止跳步

1. 9/6用户追加批准跨仓planning文档同步和步骤细化；此前“只写新目录”是审计阶段边界。本轮仅允许这些文档变化。下文“改动/运行”全部是将来获得授权后的产品步骤，不自动resume worker、register任务、下载、LLM、迁移、prune或安装同步。详细步骤见[执行者必读](execution-handbook.md)和其中三份分面手册。
2. 实施分三种独立授权：DEV（批准代码/测试精确文件）；CANARY（批准精确数据/DB行/文件/网络与费用）；AUTOSTART（最终明确恢复后台/登录启动）。DEV或历史owner授权不自动包含后两者。
3. 旧计划/receipt不就地重写。保留accepted为历史状态，建立原目标的current资格；任何T2/T3/真实周期移出原卡必须保留未完成后继及阻断门，不能只写“部署以后做”。
4. 当前worker保持paused。自动prune风险、外发安全、队列持久化、取消/失败恢复未过前，即使SQL已经很快也不能启动生产worker。禁止把暂停标记当无任何进程的证明。
5. 不重启旧Strategy A提升复制，不恢复legacy研究writer，不擅自改变owner全roots public决定、不迁D盘。公司资料事实仍在wiki；投资研究状态不进入wiki；跨仓只读export/CLI传契约，禁止共用可变DB。
6. 如出现已有并发改动：立即记录HEAD/dirty hash，重新核对该工作包，不覆盖、不reset、不顺手格式化其他文件。与正在改section_extractor的任务冲突时在自己的开发分支/隔离副本实施，并明确未来合入顺序。

## 1. 每包强制执行卡：G0→G5

每一个WP都创建自己的task_plan/findings/progress及下列产物于**未来批准的新的实施run目录**；不能将本报告目录改造成生产状态库。状态只能pending→design_review→red_proved→implemented→isolated_green→integration_green→independent_accepted；真实结果另列production_pending/production_verified。

| 节点 | 操作者与产物 | 独立审查必查项 | 通过/失败行为 |
|---|---|---|---|
| G0 目标与范围 | 实施者写card：原痛点/原条款、允许文件、禁止路径、现状hash、依赖 | Reviewer-A独立核原目标未缩减；提案交付与实现目标区分 | 空字段、未知依赖、未获授权停止；不得补写虚构授权 |
| G1 RED与设计 | 实施者提交红例、独立期望值、接口/状态/迁移/回滚ADR、测试ID | Reviewer-B先审oracle和生产entrypoint；不得以helper替主链、不得自勾稽 | RED必须在基线真实失败且原因精确；只有缺测试文件不算产品RED |
| G2 最小实现 | 只改card allowlist；每步diff和验证；不改golden使错误通过 | Reviewer-A检查生产caller全部接线、权限不扩大、无额外双实现 | scope/hash漂移或安全负例失败即停，保留证据 |
| G3 测试/故障/性能 | 实施者提交isolated测试原始结果、mutation、预算、前后快照 | 独立Test-Agent在隔离环境重跑，自己构造至少一个对抗变体 | required skip/unknown/工具缺失不是通过；未执行的层级保持pending |
| G4 实际接线 | 获CANARY授权后operator执行，生成真实调用trace/attempt/产物/成本与回滚证据 | 独立Ops/Safety-Agent核OS/DB/文件事实，不信被测summary；核同一版本/输入 | 越scope/未授权egress/timeout/账实不符立即暂停，按预审恢复，不续跑 |
| G5 资格签收 | reviewer签的是精确实施receipt hash与全部required结果，而非文件存在 | Reviewer-C（非实现者、非原oracle作者）抽查原痛点与真实结果；旧拒绝与未关finding阻断 | 格式valid、配对valid、业务accepted、生产verified分字段；一个都不替代另一个 |

Reviewer identity记录实际agent/task ID、时间、审查输入hash、命令/结果、未读范围、findings closure。中断/额度限制/没有最终verdict不计PASS。不同名字字符串不是独立性证据；实施者不能代签。每个WP的G0/G1/G2/G3/G4/G5均是独立审查节点，绝非只在项目最后审一次。

## 2. 工作包依赖与优先级

下表依赖列仅是主题关系导航，不是运行前置。执行器只允许采用第5节的精确gate DAG，禁止将裸编号解释为整包G5。

| WP | 目标 | 主题关系（非运行前置） | 主责任仓 | 原问题/条款 |
|---|---|---|---|---|
| 00 | 完成资格与证据真源 | 无；先获DEV | revenue assurance | P01，CA001–109/301/305/306 |
| 01 | 归档与自动回收安全 | 00设计门 | wiki | H01，旧空间Phase2，P11 |
| 02 | 单请求policy/只读/eligible | 00 | wiki+filing | P02/P03，ZR201–205/401–405/409 |
| 03 | 期间修订、授权补缺和失败事实 | 02 | wiki+filing | P04，ZR406–408/805 |
| 04 | 持久需求、attempt与artifact消费 | 02 | wiki+revenue | P05，ZR304–307/507–508/706 |
| 05 | 外发安全与cohort机器边界 | 02、04 | wiki | P06/P07，ZR301–303、GP003/010 |
| 06 | worker性能、取消、checkpoint与circuit | 01、02、04、05设计门 | wiki | 8/12原故障、v5、ZR206 |
| 07 | broker/网页真实解析与事实链 | 04、05、06隔离门 | wiki | P07，ZR501–510 |
| 08 | 资产事实、单位、权属和外部收入 | 02、07数据合同 | wiki+revenue | P09，ZR601–611/707/711 |
| 09 | 真generator、纯验证与事务发布 | 00、02 | revenue | P08，ZR701–705/710 |
| 10 | 真实历史回测和confidence消费 | 08、09 | revenue | P08/P09，ZR708/712/713 |
| 11 | 三仓CI、测试分层和质量递减 | 00；后续包逐个接入 | 三仓 | P10/P11，CA201/ZR101–105/801/901/906/907 |
| 12 | 真T2/T3/月度报告、告警与soak | 00、03、04、11 | revenue运维 | P10，CA202–206/ZR902–905 |
| 13 | 四root/三公司完整旅程与小cohort | 01–12全部所需隔离门 | 三仓 | ZR802–806/1001–1008、CA301/302 |
| 14 | 自然观察、legacy退出与最终关闭 | 12、13、单独运行授权 | 三仓 | CA303–306、ZR1009/1101–1105、GP008/009 |

允许独立DEV包在明确无文件交叉时并行，但所有生产写仍单operator、单writer。允许schema设计并行，不允许在WP08真实数据未完成前把合成矿业算真实pass。WP11是持续门，不是最后补CI。

## WP00 — 完成资格与证据真源（P0）

候选改动面：`assurance/unified_completion/uc/{receipt,revision,closure,scenarios,commands,strict_state,legacy_disposition}.py`、对应tests、真实CI消费者。路径须G0重新确认；本轮不改。

1. 从本次117项+GP10+legacy81项建立requirements表，保留原条款hash；每项列required tier、实际owner、entrypoint、数据样本、成功/失败指标、自然时间/授权要求。修复legacy波次`ZR-1002/1003`展开丢1003；未知ID不可静默丢弃。
2. 接受原始rejected收据的合法保存；另建business eligibility必须latest verdict accepted、所有blocking findings实际关闭或有效未完成后继阻断。不能把machine_valid当accepted，不允许self或只换reviewer字符串。
3. receipt固定三仓完整40hex+存在性+精确current组合；dirty输入文件hash、config/runtime/export/schema、命令argv/env键、样本、tier、result path/hash、授权与时间绑定。历史格式放只读迁移层，不能反过来豁免新证据。
4. scenario按sid×required tier×candidate建立多结果单元，不能一条status代表T1/T2；禁止已passed无条件skip。以JUnit/结构化结果核collected/skip/fail/业务结果；stdout可留hash，秘密env值不保存。
5. RED IDs E01拒绝review→资格拒绝；E02缺T2；E03换HEAD/dirty；E04删filing receipt；E05过期/未来；E06旧rev accepted+新rev rejected；E07未关闭P1仅有successor；E08all/partial skipped；E09命令缩短；E10同hash不同内容/同内容不同run；E11工具崩溃；E12required set为空。每个mutation必须在真正closure消费入口使release不可用，不只是schema函数返回异常。
6. 对GP004/FC903，不改旧签署字节。寻找原hash对象，无法恢复则历史审查资格unknown；在隔离checkout重新独立验证后创建新revision与supersedes链。原旧记录与撤销理由保留。
7. G5：Independent evidence reviewer重算全部hash、抽查跨仓原条款、确认没有把真实部署移出后仍closed。未达到真实tier可标implemented_verified，不可product_closed。

## WP01 — 阻断不安全回收、可信归档（P0，恢复worker前置）

候选文件：wiki `prune_retired_evidence.py`、`archive_retired_evidence.py`、`worker.py`及对应contract tests；与v5保留期/写合同协同，不另造宽松清理器。

1. G1冻结“空旧目录+新retired无归档”红例，使用小临时库；不得执行生产prune。加入R02缺gzip、R03截断、R04同count改内容、R05退役后新增span、R06恢复active、R07archive路径逃逸、R08同日二次导出中断。
2. 归档生成唯一operation/content-addressed文件；先私有staging→内容/逐文档coverage/locator验证→fsync/原子publish；同日不覆盖。manifest列source/document/span范围、parser/version、hash、retired_at、归档完成时间、可恢复定位和签认。
3. 回收只接受完成且验证的manifest，逐文档保留期和当前source/retirement代际相符；明确下游引用保留策略。候选为精确PK集合，不是`WHERE retired`开放条件；复核前后集合hash与最大触达行数，变化则拒绝。
4. 自动worker回收默认不得因日期单独触发。如何保留/禁用自动入口由G1安全ADR决定；若保留，必须每run有独立授权/精确write contract。大DELETE分批有intent/finalize，失败保留已完成批及可恢复状态。
5. G3独立Data-Recovery-Agent从归档恢复所有小fixture内容与locator，而非只数行；注入每批commit后kill、manifest破坏、目录ACL、磁盘满（仅fault facade）检查零未授权删除。
6. G4生产默认0删除。实际回收另开操作卡，需真实恢复副本、空间门/停机窗/授权、独立review及恢复演练；禁填满C盘、禁把现有恢复点算可删除空间、禁运行VACUUM作顺手优化。

## WP02 — 同一运行上下文、真正只读、请求级eligible（P0）

详细素材：filing-audit FF-WP1/2。候选wiki config/policy/cli/resolver/service/acquisition/close_gap/reader，filing contracts/入口。

1. 一次构造不可变RequestRuntimeContext（policy schema/hash、epoch/cohort、reader模式、allowed root IDs、request/as_of、授权及deadline）。所有resolve、ensure、discover后再解析、close-gap finalization、bundle/envelope使用同一实例/可核serialization。
2. 明确“metadata discover”是否允许网络/写journal；原strict noauthorization=discover/fetch0与兼容flag授权冲突需owner选择、形成ADR。选择未定时fail-closed，不能事后贴policy hash称合规。
3. 全局canonical保留去重展示；请求selected_location独立从全部副本经per-root policy→health→priority→稳定tie-break。显式false覆盖kind默认；未知root/privacy按版本合同拒绝；不取消filing containment。
4. RED C01高priority禁用低priority允许；C02reverse order；C03kind允许root禁止；C04snapshot轮换中途；C05缺context降级；C06close-gap丢export；C07symlink/reparse；C08源变更同大小；C09缺DB/WAL/SHM只读状态；C10SQL编程错误不能retry。
5. 只读测试用OS权限+DB authorizer+前后文件digest三层；SQLite WAL/SHM协议写要先定义允许边界或建立一致只读快照，不用immutable=1读live WAL假装安全。不能把mkdir/DDL放回reader。
6. G3/G5独立caller agent核所有生产构造；独立三进程测试核hash从入口到结果不漂移；无下载模式不暂停/恢复worker，不写生产journals。

## WP03 — 期间修订、精确授权补缺、单飞与失败账本（P0/P1）

详细素材：filing-audit FF-WP3/4。候选gap_plan/acquisition/authorization/close_gap、filing fetch_filing。

1. 把本报告4个freshness与10→14秒deadline反例直接列为RED。市场period key包含report kind/fiscal period/end与revision identity；日期/官方revision relation决定新旧，ID词序不决定新旧。无法排序报ambiguous。
2. canonical候选hash绑定entity/provider/period/URL/修订日期/已知size等，锁内重发现检查是否同一授权候选。未知size不能按0躲预算；streaming硬上限、实际bytes提交前再核，超限不commit。
3. 多gap返回逐项结果与remaining；只有全部授权必需项真正闭合才能completed。若暂只支持一项，明确partial/unsupported；禁止处理actionable[0]后泛化成功。
4. 将候选幂等键与授权TTL/预算字段分开；两合法不同authorization同候选不能双fetch，同请求重复commit幂等。结果未知的post-send timeout不可无条件再发；provider idempotency/result lookup不支持则人工处置。
5. 外部deadline传到lock/provider/内部重试，失败后重新计算remaining，jitter后clamp。T01底层耗9/剩1禁止sleep5；T02抖动不得破cap；T03退出清理子孙；T04fetch成功commit失败、T05commit成功handle失败、T06响应损坏均保留实际attempt/fetch/bytes/commit，不以unknown写0。
6. G3独立OS/provider spy ledger对账；G4三市场实测需独立网络、费用、目标wiki授权，不得在生产目录下载；首次下载、第二次零下载、新修订、半失败、并发各记录。

## WP04 — 唯一持久需求、实际attempt、统一artifact读链（P0/P1）

详细素材：wiki WP-W2/3、revenue WP-R6。必须收敛两套内存队列，不能新增第三个孤立队列。

1. G1设计持久demand key含source SHA、role、input bundle、producer/schema/prompt/model/policy等；状态pending/claimed/heartbeat/completed/retryable/terminal/unknown/paused，带lease fencing和request ID。
2. revenue通过wiki受控CLI/API提交，不跨仓写DB。缺artifact/安全pending/失败请求要持久记录原因和必要任务，成功且无缺角色不制造空任务；真实时钟不能固定now=0。
3. worker必须真实claim→执行→完成→caller再读；每次attempt在调用前记start，之后finish/outcome unknown。artifact INSERT是产物事件不是调用次数；失败没有产物仍必须计尝试/成本reservation。
4. service/reader/resolver统一artifact_read_model；binding precedence、active/shadow、当前source和payload hash全部检查。用实际migration apply→真实bundle读取的测试，禁止fixture预合并字段欺骗测试。
5. RED D01提交者退出；D02worker崩溃重启；D03过期lease旧worker写；D04重复100次同key；D05改一个role版本只最小DAG；D06S1→S2旧artifact不得抑制；D07失败没产物但attempt非0；D08paused不领取且caller可见；D09多location LIMIT前dedupe。
6. G3独立进程A/B/C与独立ledger作oracle；G4首先NETWORK_DENY/LLM_OFF，仅明确cohort。二次exact复用必须真正0下载/0parser/0LLM，而不只是planned DAG为空。

## WP05 — 实际外发安全、readiness与cohort边界（P0）

候选llm_summarizer/readiness_graph/source_lifecycle/section_extractor/service与测试。详细素材wiki WP-W4/5。

1. LLM generate前必须统一校验本次source SHA、normalized artifact ID/hash/current status、review TTL/now/current policy/identity/root授权；SQL只能预筛。所有fallback独立授权，不能继承主provider隐式许可。
2. readiness字段按用户语义：freshness需请求模式/供应方证据，artifact需verified required roles，semantic需具体consumer合同；不能以published_date非空/任意span/任意completed足够。
3. mutating入口绑定不可变cohort manifest/精确document IDs+source SHA/expected count/allowed columns/paths/费用；dry-run确定集合，commit前CAS验证。kind-only、空名单、集合变化或超一项必须零写拒绝。
4. RED S01过期review；S02换policy；S03换normalized bytes不换source；S04contradicted identity；S05未知root；S06private；S07fallback未授权；S08cohort7→752；S09增删一个ID；S10超过token/字节/cost cap；S11恶意文档指令与禁止投资输出。所有拒绝由独立spy验证真实调用0，而非结果自己报告。
5. 安全拒绝不是待强行做绿的缺陷。对GP010第7份可规划更窄source-only摘要或保持终态，但不得调松评级/目标价禁令；已越cohort的214历史产物按owner保留，禁止本包清理。
6. G1/G4/G5独立Safety-Agent必须逐个边界审核，独立数据operator只执行manifest绑定操作。没有成本上限/目的地/隐私批准不能LLM_ON。

## WP06 — Worker性能与恢复协议（P0/P1）

历史902秒/0.231秒来自旧现场，不是这轮baseline；禁止承诺未经实测倍数。详细素材wiki WP-W1、filing F-F07，v5导入的acceptance_thresholds仅作为待正式冻结输入。

1. 先完成v5版本合同/冻结映射，或在本实施线正式引用其冻结版本；不能只改文件名成v5。Independent performance/design/safety三路核同一哈希后才施工。
2. 测量分段：enumeration、metadata、queue SQL prepare/consume、hash、parser启动/运行、DB commit、LLM wait/egress、export、checkpoint、重启/backoff；同时wall/CPU/peak RSS/I/O bytes、样本大小/页数、队列年龄、失败次数。进程启动与全PDF SHA必须独立展示，不用SQL LIMIT1替全请求。
3. SQL先构造25k docs/50k locations及5k/10k/20k/40k等比分布，force/retry/terminal/主source漂移/重复location；独立oracle比较有序IDs100%一致。旧坏查询仅scratch限2秒，不能再在生产跑902秒。
4. 待G1正式冻结的继承最低门：warm n≥30且P95<2s；cold-ish n≥10且max<10s；翻倍VM proxy≤2.8、wall median≤3；无correlated status-per-document坏plan。测量mode明确approx callback proxy或真正stmtstatus，禁止混称精确指令。迁移索引只在显式升级，不在普通open做DDL。
5. SQL取消handler与控制轮询分开；查询开始后另一真实进程pause，P95≤5s/max≤10s，handler下次query前清除。parser每route大小/损坏/加密/超时/子孙清理按冻结v5格式矩阵，不足样本的route禁用而非跳过绿。
6. scan完成就checkpoint；heartbeat不能当成功；完整cycle success才reset failure budget。连续同signature3次/30min任意5次等circuit规则必须持久，不因900秒uptime清零；重启/登录不清circuit。reset需要单独授权且结果仍paused。
7. scanner用同拓扑baseline/candidate交替n≥10，candidateP95≤120s及≥2倍目标仅在G1锁定同协议后验收；不靠少扫目录获利。hash优化不得取消完整性校验；同metadata重审周期要有明确30天最大间隔和高风险即时hash策略。
8. G4先LLM_OFF、自动删除0、精确写合同小cohort；CPU>80%且无真实进度连续5min停。不得并行化非线程安全LLMClient来提速；先解决无效重复、SQL复杂度和取消。最终profile附所有原始样本/异常值，独立agent计算分位数，不删慢样本。

## WP07 — Broker/HTML真实语义成果（P1）

1. 固定7PDF+2HTML候选hash与独立标注，另加列表式、跨页表、多栏、多实体和非紫金样本。真实源不可得则该tier blocked，不用CHANGJIANG_TEXT替代。
2. 真parser输入开始验证物理页、读序、表格cell/行列、单位/币种/期间、章节、标签、事实与source locator；人工已解析pages数组只计adapter T1。
3. 列表式报告采用清晰策略或unsupported终态；不编标题骗section计数、不反复占队列首。HTML identity接入实际导入→normalizer→consumer，不只测纯parser。
4. B01换页；B02表跨页；B03千/百万混用；B04多实体错归；B05同名不同期间；B06HTML wrong strategy；B07真实缺字段→gap；B08恶意文字；B09无section；B10源/locator改变后缓存失效。
5. 按1→3→7真实持久DemandQueue执行，每一步G4有独立review，不只最终看总数。要求exact cohort/旧原始字节不变/调用和费用账实一致；结果不是7/7时逐份解释，安全拒绝不绕过。

## WP08 — 上游资产事实与可计算矿业收入（P0/P1）

详细素材upstream-asset-audit、revenue WP-R2/3；原601–604 owner仍wiki，不能把收入单测替来源事实。

1. G1由独立Source-Contract-Agent与Accounting-Agent共同冻结asset ID/type/时效alias、source_id+locator/parser、事实原值/单位/标准化值、resource/reserve标准/measurement date、100%/equity/consolidation basis、country/region。未知与假设分开，不存投资评级。
2. 从真实表格产生带冲突的双assertion与review状态，保留旧值不覆盖；资产alias循环/碰撞/变更时效拒绝。下游消费只读export和已获合法选择的事实，不能自动选择未review参数。
3. 量价计算显式ore/contained/payable、kt/t/kg、%/ratio/g/t、wet/dry、计价量、FX方向；TC/RC声明rate或amount及各自denominator；payability只应用一次，0产量/0股权与缺值区分，NaN/inf拒绝。
4. 权属遍历整个期间变更点，A→B→A不能首尾判定；任何期内change默认block，显式pro-rata另声明模型假设。operational100%、equity attribution、集团合并external三视图不能相混。
5. 内供从毛额+唯一flow ID/双边/合并范围做消重；不得要求调用者预先给正确external再自勾稽。外部披露reference独立source/period/basis/currency绑定；差额保留unallocated，禁止plug清零。
6. M01 kt×%到t；M02 g/t到kg；M03TC精矿吨/RC金属吨；M04重复payability；M05A→B→A；M06associate不并收入；M07内部双计；M08一side缺失；M09resource冒充reserve；M10跨公司review事实；M11同值不同单位；M12无source。双独立Decimal手算至少一个矿、分部、公司，生产输出匹配误差门须事前冻结。
7. 3.8 operating_units必须实际驱动图：改单个unit改变相关收入且其他矿不变。旧3.7兼容数值不漂移是另一项测试，不能用“不变”证明新units被消费。

## WP09 — Generator、纯验证与事务发布（P0/P1）

详细素材revenue WP-R4/5。候选generate_input_template/schema_fields/contracts/document/revenue_forecast/revenue_core/publication_registry及CLI测试。

1. 生成模板必须来自版本合同，minimal/mining两型；monetary字段currency/scale和driver dimension正确，默认日期不含未来完整年度事实。填值fixture只能填值/source/许可假设，不可改结构救模板。
2. 固定测试真实build_template→fill→lint→hash/capture→validate→draft→render；不能替换forecast_document。保留lint clean但engine fail负例；所有文档可执行示例走同一链。
3. pure prepare默认draft或明确无I/O API；validate-only/probe不得registry/key/artifact写。用实际配置的registry路径和OS写哨兵验证，不检查一个没传入的tmp_path。
4. 发布定义operation_id及prepared/committed/aborted、输出json/md/签署hash、append-only intent/finalize、恢复状态；所有交付物stage验证后才commit可见。相同operation重试一次commit，不等于同input永远只允许一次新发布。
5. P01compute后；P02validate后；P03render；P04sign；P05fsync；P06rename-json；P07rename-md；P08registry-commit；P09response：每处异常和进程kill，独立检查磁盘状态、恢复与恰一次。磁盘满用fault facade；Windows文件占用/只读目录/并发同operation必须覆盖。
6. 修registry audit四元组key对input字符串错误，加入真已登记正例；多进程append需原子协调，不能两个prev头分叉。失败保留真实journal不删除历史注册伪装零副作用。
7. G5独立Release-Agent通过真实CLI与磁盘oracle确认事务，helper atomic-write绿仅是G3中一项。

## WP10 — 真实历史、滚动回测与confidence（P0/P1）

1. 独立定义forecast_origin与evaluation_as_of：当时预测输入必须当时可知，后来actual可用于评估但不可反灌预测。snapshot/actual/评价相互hash及company/period/source绑定，不能只验自签JSON。
2. observation按真实身份去重；同snapshot换as_of、拆分同actual、跨公司record不得增加独立窗口。缺两真实origin就保留cap，不伪造旧快照。
3. mine-volume要预测与actual同mine/product/unit配对，才算误差；只有actual分解/wape=None记未覆盖，不能解除cap。
4. ConfidencePolicy真正注入analysis.confidence并在输出验证重算；one-observation cap是数值约束，不仅disclosure；policy版本和全部输入进入receipt。保留现主validator真实hash校验，不为重构删除已有门。
5. K01同snapshot改日期；K02伪非空hash；K03改WAPE重hash；K04future source；K05跨公司；K06重复拆分；K07单观测零误差；K08缺mine预测；K09policy换权重但输出不变。独立oracle重算底层误差和置信限制，不能调用被测评分自身。

## WP11 — 真正阻断的三仓CI与质量门（P1）

1. 任一仓candidate生成精确三仓组合，其他两仓pin不得漂移；构建candidate时N-1与current分开。实际fanout需Git托管权限单独批准；不能只搜索workflow_run字样验收。
2. 所有纯/临时fixture T0/T1 required且不可continue-on-error；current真实roots T2在授权隔离自托管环境，网络T3独立权限。不能在公共runner上传私有root正文/密钥。
3. 对本报告一一把测试替身改为真实入口与独立oracle，保留有用合成测试但纠正tier和名称。required collected/skip delta基线、JUnit与业务outcome入WP00；工具异常非0必须阻断，不能只数stdout errors。
4. AST扫描三仓全部指定core（含子目录），禁止固定公司词小名单证明无硬编码；source-only职责、dead dual paths和legacy调用图独立审。复杂度/类型/coverage按批准基线逐波下降，新改关键函数CC≤10或事前ADR，不能失败后抬门。
5. Q01required Windows失败应阻断；Q02删T2；Q03skip provider；Q04工具不存在；Q05陈旧sibling；Q06新子目录hardcode；Q07单行docstring之后坏代码；Q08old gate重新接入；Q09scope缩减仅改测试。这些都要观察实际CI结论，而不是只测scanner函数。

## WP12 — 调度、真实报告与独立停跑告警（P1）

1. 统一daily/weekly/monthly/report schema与consumer；旧两个weekly runner须明确一个canonical、另一仅兼容adapter，禁止不同skip判定。真实runner必须走atomic publish，业务SLI每项独立来源，不复制ledger.ok。
2. Daily执行三/四root unique样本的实际resolve/bundle/复用/Reader-live-WAL/fault/完整pipeline时延；根为动态policy列表，不硬编码三个路径。只读零写证据用manifest/分层hash与OS事件，文件数不是指纹。
3. Weekly每市场required case独立结果，metadata/首次/二次/修订/单飞对账；blocked/partialskip非0且不fresh。Monthly轮换真实broker/异构矿企/非矿企，缺样本blocked。
4. 任务检查区分registered/missing/disabled/permission_denied；部署核actual Action、解释器、参数、cwd、SID、凭据读取权限、电源/wake/StartWhenAvailable、并发实例、退出码和触发event。不得从新manifest推断自然触发。
5. 独立watchdog不依赖被监测任务本身运行：无新run、迟到、半报告、主机休眠都须报告可观测状态；告警sink/ack/retry可验证。不得只向本地JSONL写一行就称用户已收到告警。
6. 生产soak只有一个计算入口，测试调用它并另有独立oracle；run ID、不同自然日/周、时区/DST、失败链、未来/重放、重复样本、最新fresh、late catch-up全部规定。连续7daily、≥7天间隔2weekly、35天内monthly、真实drill ack不允许测试时钟代替。
7. O01任务不触发；O02SYSTEM权限差；O03future；O04copy old green；O05report okfalse；O06缺一个SLI；O07hash坏；O08same-time7run；O09链中失败；O10半report进程终止；O11alert sink失败；O12report HEAD/config变更。独立Ops-Agent看平台事件及ledger一致性，非仅程序ok。

## WP13 — 当前三仓真实旅程与生产小cohort（P1，单独CANARY授权）

1. G0/G1冻结四root和三真实公司选择：紫金、结构显著不同的矿企、非矿企；实际身份与输入不同，不改名字复用同一合成document。没有资料的root不能用companies副本充数；缺数据是具体blocked并保留已成功阶段。
2. 建逐事实manifest：raw/sourceSHA→parser/locator→review→artifact→demand/attempt→parameter→model node→output→独立reference；每条输入确实来自该source，不在测试后半程改成手工forecast_document。
3. 三个干净checkout由独立reviewer重建，登记环境/fixture与dirty禁止；历史未跟踪输入不能直接整目录复制实施者树，必须按manifest审核导入，不能污染clean声明。
4. 真实1→3→7小cohort逐步停下审查，source/配置零未经授权变化、费用不超、每次write contract精确PK/文件、失败恢复RPO0。无网络阶段先通过；任何LLM/provider阶段另授权manifest。
5. E2E状态existing/partial/missing/stale/amended/safety_pending；第二次0download/parser/LLM；source/policy/parser/prompt变化只失效必要节点；错误保留前阶段receipt。每条三公司完整旅程G4/G5分别独立签收。

## WP14 — 自然运行、legacy退出与最终资格（P1）

1. 启动观察前所有安全/恢复/性能/真实cohort门都通过，另有用户运行批准；只允许批准profile。仍缺完整v5版本/冻结/trust anchor则AUTOSTART不可实施，计划不能替代该前置。
2. 两小时≥5完整cycle是worker观察，7/2/1/1是动态审核；两类不得互相抵扣。SQL/CPU无进度超门、额外写/egress、未知费用、脏release立即pause并停止计数，保留历史失败。
3. R9需两个真实完成且各≥24h/zero legacy hit窗口、当前required矩阵、N-1授权；不按预计日历放行。保留未完成窗口为未完成，不把synthetic两次read算两周期。
4. 分批明确旧符号/caller/flags/文件allowlist、entry/exit/rollback。每批独立agent审查影响图→小范围删→全required矩阵→真实cohort回滚再激活；不得删测试/改skip解红，不一次大爆炸。历史旧授权需重新核scope/有效性和当前版本。
5. 六成功问题由实际证据计算：每个子项通过方可目标closed；不能只检查accepted/文件存在/40字符。任何unknown、缺自然时间、未实施真实动作仍阻断相应资格。
6. 最后仅在用户明确批准后切换入口/发布/安装；worker当前session启动与登录自启动是独立动作。退出审核后默认回paused；AUTOSTART按v5独立双授权/保护快照/真实登录验证流程，不在本计划简化成写HKCU Run。

## 3. 实施前必须解决的选择，不允许弱模型自行猜

| 决策 | 决策者与时点 | 未决时行为 |
|---|---|---|
| 是否允许metadata-only请求联网/写journal | owner+安全reviewer，WP02 G1 | 按无外发/无写保守路径，显式blocked |
| RootPolicy1/2/3迁移与N-1边界 | 三仓contract reviewer，WP02 G1 | 不自动缺字段降级；不改生产config |
| v5版本合同、正式manifest与统计预算 | 原v5 owner+独立性能/安全reviewer，WP06 G1 | 仅隔离设计/测试，不真实运行 |
| 自动prune保留方式、引用/恢复策略 | owner+数据恢复reviewer，WP01 G1 | 0生产删除，worker恢复门不通过 |
| 真实网络/LLM provider、数据scope、成本/字符/token/日月cap | owner，每次CANARY前 | LLM_OFF+NETWORK_DENY |
| 三真实公司/四root样本、事实golden与误差阈值 | source/accounting reviewer，WP08/13 G1 | 不能用synthetic替真；不解除结果缺口 |
| 发布操作exactly-once与多版本语义 | publication reviewer，WP09 G1 | draft only，不动registry |
| 自然日时区/DST/迟到补跑、动态报告freshness | owner+Ops reviewer，WP12 G1 | 不计窗口、不放release |

## 4. 交接前自检

- 每WP每G节点都有真实review结果/输入hash，不把“计划安排审查”当“审查已过”。
- 所有RED/Fault IDs有对应测试路径与实际结果，required tier采集数可计算；没有整file映射虚报场景。
- 所有生产行为都有明确operator/授权/精确scope/终态/回滚证据；没有隐式LLM/下载/自启动。
- 每条原痛点有修复前失败、修复后局部绿、真实入口绿、独立效果证据；缺哪个就显示哪个。
- 实施进度以WP门管理，不再用新增了多少测试或文档长度衡量。未知生产问题不随意修改，先记录进入下一独立卡。

当前全部WP状态：**NOT_IMPLEMENTATION_AUTHORIZED**。本计划交付不改变暂停状态，不执行任何以上修复。

## 5. R2强制门级依赖与运行分段（优先于主题依赖表）

本节是P1-PLAN-01/02的修订。以下是未来状态合同，不表示本轮执行过这些门。

### 5.1 能力签收与业务关闭分离

- WP00.G3验证证据能力：隔离fixture通过真实CLI/closure消费路径，拒绝缺失真实tier，**不要求先有真实目标成功**。WP00.G4只接隔离真实CLI，独立Ops审核无生产副作用；WP00.G5签收此能力。原117项最终资格另由WP14.G5计算，绝不成为WP00或其他DEV的前置。
- WP11.G3签收bootstrap CI能力，使用代表性变更证明required gate有效；之后每包增加独立版本化适用矩阵。最终全矩阵覆盖在WP14，不反向阻塞bootstrap。
- 所有WP内部边固定G0→G1→G2→G3→G4→G5。G4按G1独立签署的integration_scope分为isolated_cli或authorized_canary；纯格式/验证器默认isolated_cli，零生产DB/外发。确无接线可测才允许Reviewer-C签N/A理由；N/A不产生production_verified。下表额外边叠加内部边，不替代授权。
- 安全签收`Sxx`指WPxx.G3原始结果经独立Ops/Safety-Agent复核并签hash，内容包括禁止写/外发、恢复和运行范围；不是开发者自报green。

### 5.2 DEV gate DAG：精确额外边

箭头左为准入门，右为**全部必须通过**的门。WP00.G0另需精确DEV批准。任一WP.G2必须有本包文件allowlist的DEV授权。

| 准入门 | 额外前置门 |
|---|---|
| WP01.G0、WP02.G0、WP09.G0、WP11.G0 | WP00.G1 |
| WP01.G3、WP02.G3、WP09.G3、WP11.G3 | WP00.G3 |
| WP03.G0、WP04.G0 | WP02.G1 |
| WP03.G3、WP04.G3 | WP02.G3 |
| WP05.G0 | WP02.G1、WP04.G1 |
| WP05.G3 | WP02.G3、WP04.G3 |
| WP06.G0 | WP01.G1、WP02.G1、WP04.G1、WP05.G1 |
| WP06.G3 | WP01.G3、WP02.G3、WP04.G3、WP05.G3 |
| WP07.G0 | WP04.G1、WP05.G1、WP06.G1 |
| WP07.G3 | WP04.G3、WP05.G3、WP06.G3 |
| WP08.G0 | WP02.G1、WP07.G1（上游数据合同冻结） |
| WP08.G3 | WP02.G3、WP07.G3 |
| WP10.G0 | WP08.G1、WP09.G1 |
| WP10.G3 | WP08.G3、WP09.G3 |
| WP12.G0 | WP00.G1、WP03.G1、WP04.G1、WP11.G1 |
| WP12.G3（12a隔离能力） | WP00.G3、WP03.G3、WP04.G3、WP11.G3 |
| WP13.G0 | WP01.G1至WP12.G1逐一通过 |
| WP13.G3 | WP01.G3至WP12.G3逐一通过；这里只需12a，不需要12b/c |
| WP14.G0 | WP13.G1、WP12.G1 |
| WP14.G3 | WP13.G3、WP12.G3 |
| WP14.G4 | WP13.G5、WP12.G5、S01、S02、S04、S05、S06，及当前运行/legacy操作独立授权 |

其余包到G4按下一节作用域门执行。G5签的是本包明确层级能力；若真实tier未完成必须保留production_pending，不得整目标closed。

### 5.3 任何真实动作的附加准入门

R3隔离测试边界：下表约束G4真实canary/生产/后台动作。G3允许在明确批准的隔离测试环境启动被测真实CLI/受控子进程，不以“真代码”误要求本包先过自身G3。WP06.G3真实worker测试必须先有WP01/02/04/05.G3、本包G1独立安全命令卡、数据读取/副本/受控进程精确许可；所有DB/config/output绝对路径封闭在隔离根，OS层禁止生产写/网络、LLM_OFF、自动prune=0、无调度/自启动/生产控制文件访问、进程超时与清理可独立执行。不能证明隔离则不运行并记blocked，禁止默认生产配置回退。此层不需要尚待测试形成的S06；通过后才由独立Ops生成S06，G4仍须全部安全门及单独授权。WP04.G3仅测试真实队列API的机制进程，不启动worker loop/parser/LLM；完整worker链留后续。该边界不是现时授权，也不把隔离成功算生产verified。

所有authorized_canary类型G4均需：本包G3、WP00.G3、WP11.G3、对应版本适用CI矩阵通过、G1冻结操作卡、精确且未失效授权、独立Ops批准。按动作取下列前置的并集；动作不能分类则拒绝，不默认放行。

| 动作 | 强制额外门 |
|---|---|
| 归档/恢复/prune | S01；生产删除另有精确PK批准与恢复演练；不随worker授权附送 |
| 跨root resolver/复用 | S02 |
| provider发现/下载/修订补缺 | S02、WP03.G3；network_case_run授权 |
| demand/worker/pipeline | S01、S02、S04、S05、S06；manual_worker_run授权 |
| LLM/cohort外发 | S02、S04、S05；network_case_run与精确source manifest |
| broker/HTML处理 | S01、S02、S04、S05、S06、WP07.G3 |
| 矿业/非矿业模型及发布 | WP08.G3（矿业case）、WP09.G3；回测/confidence另需WP10.G3 |
| schedule/watchdog持续部署 | WP12.G3；独立schedule_register_or_update/watchdog_enable授权；配置为disabled直到12b准入 |
| legacy删除/再激活 | WP14.G3、WP13.G5、WP12.G5；精确删除/恢复卡和当前运行授权 |

WP13的1→3→7各步分别独立G4审核；只可使用12a报告能力。其完成的真实case定义/hash签收为WP13.G5。

WP12分三段：12a=G0–G3隔离调度/报告/告警能力；12b=G4真实持续case，前置WP13.G5及上表动作门（不要求先有12c）；12c=G5自然时间资格，前置12b真实run证据和7/2/1/1。任何未通过WP13真实case的样本不计soak。12c不足只observing，不阻止其他无副作用DEV，但阻断WP14.G4。测试时钟只测试算法，不产生自然资格。

G1必须产出机器可读gate-dag.json及独立拓扑审查：枚举所有门/边/作用域，未知或空gate拒绝；测试加`WP00.G3依赖WP13.G5`能检测环；WP05未过请求LLM拒绝、WP06未过启动worker拒绝、仅synthetic monthly不计数、仅registered task不计run。审查产物包括拓扑序与每个G4授权/安全祖先列表。本文作为计划已人工核对无上述互等；未来机器DAG验证仍是实施前必需门，不能声称本轮运行过该测试。

## 6. R2独立审查补充操作卡和RED矩阵

### 授权卡（P2-PLAN-03）

CANARY必须逐operation subtype列`manual_worker_run`、`network_case_run`、`schedule_register_or_update`、`watchdog_enable`，禁止彼此推导。字段：owner批准证据、operator、精确task name/SID/action/interpreter/cwd/profile、文件/PK/source allowlist、起止时间/时区、最大run数、字符/token/byte上限、日/月费用预算、撤销方式、原任务注册快照与恢复命令审查。调度注册不授权无限未来外发；额度或授权到期自动fail-closed。AUTOSTART仍单独审批，手动启动不能变登录启动。告警演练也在sink/次数/费用授权范围内。

### 归档快照及恢复边界（P2-PLAN-04/06）

WP01.G1冻结一致读snapshot或等价可证明高水位/版本合同：精确PK清单与导出字节来自同一稳定视图，跨批COUNT相等不算集合相等。归档到prune之间出现重激活/新span需重新核资格，最多处理已验证原集合；锁不能代替生命周期检查。注入可信clock：H11保留期前1秒/恰到/后1秒；H12未来目录；H13retired_at晚于归档；H14同日空archive后新退役；H15导出期间并发变更；H16归档后重激活。每例检查精确PK/locator和零越界删除。

WP13所称RPO0限定可恢复本地对象，G1逐操作冻结：raw字节不得修改；EvidenceSpan须恢复精确PK/locator/parser/hash及引用；publication保留append-only intent/失败记录，不回滚擦除历史；provider已发生调用和费用不可撤销，保留事实/unknown及补偿或人工处置，禁止承诺物理撤回。回滚不包含启动暂停worker，再激活需当前独立授权。

### 发现→RED→独立证据补充（P2-PLAN-05）

| 发现 | 工作包 / RED ID | 独立G3/G4输出oracle |
|---|---|---|
| F-F06 structured gap漏计数 | WP03 T07 | 真CLI JSON含统一stats schema；spy对账calls/downloads/阶段，unknown不默认0 |
| F-F06 unexpected fatal漏stats | WP03 T08 | 在成功外部调用之后注入fatal，保留已知成本/阶段与unknown原因 |
| F-F08 bundle双字段相等但未重算 | WP04 D10 | 两处hash相同且改payload，真生产消费者canonical recompute拒绝 |
| A04 legacy ledger不可读 | WP12 O13 | 必需输入unavailable导致not_ok/not_fresh，明确原因 |
| A04 scan JSON损坏 | WP12 O14 | 解析失败不是0 errors；release消费者阻断 |
| A03 dry-run写evidence | WP00 E13 | 真CLI在OS写哨兵下0写，包括目录创建；不是只检查返回码 |
| A03 测试名自动扩大网络授权 | WP11 Q10 | 改测试文件名不能改变有效network grant；真实env/egress spy一致 |
| A06 scanners-only虚填ok | WP11 Q11 | 未执行维度not_run，required维度缺失时release不可用 |

完整审计导航为unit-ledger的117项→分报告finding→各WP原问题/条款与本表。未来WP00.G1必须扩展为一行一原条款/发现的机器映射（不得仅复制117个accepted）：requirement/finding ID、WP、本文RED/fault ID、独立oracle、G3结果hash、所需G4 tier/hash或pending理由、最终资格消费者。缺映射阻断设计签收；未实施的结果字段保持pending，不填模拟hash。所有本节新增RED均纳入对应WP的G1/G3及独立review，不是可选建议。
