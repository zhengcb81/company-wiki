# WP01–WP07 数据供应链实施手册（待授权，不执行）

> **R4状态覆盖（2026-09-07）**：本文正文是R3历史方案/测试细节库，已不再作为活动执行队列。唯一活动编排为[R4实施计划](simplified-execution-plan.md)，测试见[R4矩阵](simplified-test-matrix.md)，原WP归属见[迁移表](r4-transition.md)。仅按迁移表继承领域步骤、反例与原始成果要求；不执行下文旧G0–G5依赖或95门DAG。历史review只签当时字节，本次新增状态头使当前文件hash变化，不能宣称旧签收绑定修改后文件。旧gate-dag.json及validate_execution_plan.py原样保留为R3历史工具，不用于R4验收。文档更新不授权产品实施。

日期：2026-09-06。状态：**NOT_IMPLEMENTATION_AUTHORIZED**。这是[修复总计划 R2](remediation-plan.md)的展开，不改变其第5节门级DAG、第6节授权及恢复边界；发生冲突时停止并请计划维护者裁定，不能自行择宽松条款。本轮只写文档，没有修改下述文件、运行生产CLI/worker、联网、归档或回收。

原证据：[wiki审计](wiki-audit.md)、[filing审计](filing-audit.md)、[历史项目审计](historical-projects-audit.md)、[回收独立复核](retention-independent-review.md)。以下候选文件在本轮通过文件列表核实存在；文件名不是修改授权。行号故意不固化：未来G0必须重新核源码、HEAD、dirty hash和真实调用链，不能直接按历史行号替换。

## A. 通用执行协议：先知道何时必须停

### A1. 目录、权限及产物

未来每包在**独立批准的实施run目录**建立 `task_plan.md / findings.md / progress.md`。不得把本审计目录、历史receipt或生产目录当运行临时目录。每一步登记：`step_id、started_at、ended_at、operator、input_hashes、exact_argv、cwd、allowlisted_env_keys、exit_code、business_outcome、output_hashes、side_effects、review_ref、next_step`。不得保存凭据或真实私有正文到公开CI日志。

下文产物文件名是**未来待建立的合同**，目前不存在不代表任务失败；不能给它们填模拟hash或伪造通过。每包至少产出：

- `scope.json`：三仓精确提交、dirty输入hash、允许修改文件、禁止路径、数据/DB/网络/费用权限、到期时间、暂停与恢复责任人。
- `case-manifest.jsonl`：case ID、真实source ID/路径/原始SHA、来源与获取日期、公司/市场/期间、数据量、许可用途、required tier、独立oracle及预算。
- `command-cards.jsonl`：精确解释器/入口/argv/cwd/env键、读写路径、网络目的地、超时、最大资源、预期退出码与业务状态；独立审查后才可执行。
- `results.jsonl`：一例一层一版本一结果，`passed/failed/blocked/not_run`明确分开；保存原始输出、进程/文件/DB观察及hash，不能只写pytest总数。
- `review-G0.md`至`review-G5.md`：实际agent/task身份、输入hash、读过/未读材料、独立检查、问题及结论。每个小步骤完成并不等于对应G已通过。

DEV只准卡片列明的源码/测试变更。CANARY须分 `manual_worker_run / network_case_run / schedule_register_or_update / watchdog_enable`；仅修改文档不获得其中任何权限。AUTOSTART独立，**本手册所有终态默认paused**。复制真实库也需批准读源/目标/空间；禁止直接文件复制正在写入的SQLite假定一致，不碰生产-WAL/-SHM，不自动VACUUM、ANALYZE或改生产索引。

### A2. E2E的真实含义与不可替代关系

| 层 | 必须实际经过什么 | 可证明什么 / 不能证明什么 |
|---|---|---|
| T0/T1机制与故障诊断 | 合成小库、受控clock、mock/provider spy或fault facade | 只能证明算法/边界/故障机制；不能称真实数据E2E或真实服务可用 |
| E2E-R隔离真实数据 | 已批准的真实raw原字节及来源manifest、一致真实目录/库副本、真实产品CLI/真实子进程/真实parser、真实磁盘产物 | 能证明该candidate在批准隔离数据与环境上的完整链；不能推断生产已恢复、真实网络已通或自然周期达标 |
| E2E-N真实网络 | E2E-R基础上真实指定provider/LLM服务、独立网络/费用授权、真实响应/请求ID/账单或服务计数 | 能证明这一次真实外发/下载/消费；不能把录制重放、本地HTTP替身、设置环境flag当真服务证据 |
| E2E-P生产小cohort | R2所有动作门、精确授权和当前真实部署，1→3→7各自停审 | 只证明批准cohort与版本；不是全部752候选通过，更不是恢复自启动 |

真实源数据不允许替换成手写 `pages` 数组、fixture forecast、改名复用同一公司、合成catalog填充后称真实49GB。合成规模可以验证复杂度，但生产规模论断另需同拓扑真实一致副本。缺少实际样本/许可/副本空间/凭据/子进程跟踪权限时，记录具体blocked和补齐方式，不降低tier。故障注入可作用于真实链的隔离副本，但报告必须标明注入点和人工改造字段；它不是自然发生故障的证据。

**oracle独立性**：Reviewer-B在读实现前由原合同/真实原文形成期望；G3 Test-Agent不能调用被测选择器、hash验证器、统计器或SQL自身来生成期望。至少用另一种表达：人工原文逐项标注、直接按冻结名单核PK/文件hash、独立Decimal/集合计算、OS进程与服务端事实。实现者导出的summary仅是被检对象。

### A3. 每包的六个独立门

1. G0：Reviewer-A核原痛点、完整范围、依赖和精确权限；未知依赖/并发冲突停止。
2. G1：Reviewer-B核每个RED的独立oracle、真实入口、数据资格、迁移/回滚和操作卡；无真实失败或仅缺测试不得称RED成立。
3. G2：Reviewer-A核最小diff、全生产caller、未扩大范围、原正向保护仍在；新增入口必须纳入同一门。
4. G3：独立Test-Agent重跑隔离机制/真实数据case并增加至少一对抗变体；适用R2前置门。每个required case必须有实际结果，无skip转绿。
5. G4：独立Ops/Safety-Agent按 `integration_scope` 审真实CLI或获授权canary的OS/DB/egress事实；所有动作取R2 §5.3门的并集。没有生产权限可以完成isolated_cli能力，但必须保留production_pending。
6. G5：Reviewer-C非实施者、非原oracle作者，复查原目标和证据hash、未关问题、层级；只签精确能力。原目标关闭仍由WP14处理。

**每包10步固定停止点**：01后等G0；03后等G1；06后等G2；08后等G3；09后等G4；10等G5。一个门拒绝，后续步骤都不运行。各门必须审此前所有步骤，而非只审最后一项。超时/未知开销/意外写入先停止，保全已发生事实，不能删日志后重跑到绿。任何新生产故障先记finding进入新卡，不顺手扩修。

## B. WP01：逐对象可信归档、保留期和回收

候选根 `W = C:/Users/郑曾波/Projects/company-wiki/`；源码前缀 `SC = W/src/company_wiki/source_catalog/`。已核实：`SC/archive_retired_evidence.py`、`SC/prune_retired_evidence.py`、`SC/worker.py`；测试 `W/tests/contract/test_source_catalog_archive_retired.py`、`test_source_catalog_prune_retired.py`。不修改旧归档、不删除现有span，不缩短生产90天以求快速验证。

准入：G0需WP00.G1；G3需WP00.G3。真实归档/恢复/prune动作需S01；真实生产删除另需精确PK批准与恢复演练。生产worker另取S01/S02/S04/S05/S06及manual_worker_run，不因本包完成而启动。

| 步骤 | 输入及具体动作（将来获准后） | 必交产物 / 检查点 / 失败即停条件 |
|---|---|---|
| 01 范围与数据 | 读H01和上述生产调用；列旧归档、retired/active/new span引用关系；只批准隔离复制目标，冻结磁盘预算。 | scope、candidate调用图、真实源样本清单；G0独立恢复agent核“原文不删、精确locator可恢复”；无一致副本策略即停。 |
| 02 固定反例 | 在小临时库重现空旧目录+新retired未归档可进入删除；补缺gzip、截断、同count异内容、新span、重激活、路径逃逸、同日覆盖中断。 | H/R case逐项基线PK/hash，RED失败原因；仅目录日期改变产生通过必须被判错误。不得对真实生产apply。 |
| 03 冻结合同 | 明确一致读snapshot/高水位、逐span和逐文档coverage、retired_at与代际、下游引用、保留期边界；唯一归档名、staging/发布/恢复协议。 | ADR、manifest schema、精确回收集合算法的独立集合oracle、rollback；G1核H11–H16：前1秒/恰到/后1秒、未来目录、导出并发、新退役/重激活。 |
| 04 归档最小实现 | 只改已批准archive模块及对应测试：稳定视图→流式导出→逐对象内容hash→staging校验→原子发布；已有同日文件不覆盖。 | 最小diff、manifest原始字节和逐对象coverage；跨批COUNT相等但PK不同必须失败，未完成归档不得可见为可回收。 |
| 05 回收最小实现 | 仅接受完整验证manifest、逐对象保留期/代际/引用资格；精确PK/CAS集合、max rows、intent/逐批finalize；worker自动入口按预审ADR限制。 | 删除计划含精确集合hash；空目录/不匹配/新增对象0越界删除；不得把条件改成“所有retired”。 |
| 06 恢复路径接线 | 为批准隔离库实现/验证恢复协议；保留原PK、内容、locator、parser/hash及引用，冲突不覆盖；核worker所有自动回收路径。 | restore diff、与源快照逐对象比对；G2独立agent抽查生产caller及无旁路，禁止只恢复行数。 |
| 07 故障测试 | 在隔离目标逐批commit后kill、归档publish前后kill、ACL失败、文件占用、manifest破坏；磁盘满用fault facade，绝不填满宿主盘。 | 每故障点实际已提交集合、恢复集合、残留文件和退出码；能恢复已授权本地对象且未删外集合。kill非目标PID即事故停止。 |
| 08 真实数据恢复E2E-R | 用获准真实retired文档/原locator一致副本，经真实归档入口→校验→隔离回收→真实恢复入口；混入真实active/未归档样本作禁删对照。 | 独立恢复agent重算全部所选span/locator，不只抽一行；G3签该副本层级。缺真实retired样本或原locator清单则blocked，不能用全合成补资格。 |
| 09 G4操作演练 | 默认isolated_cli且生产删除0；如另获生产回收授权，先核真实恢复副本、空间、停机窗、精确PK和授权有效期，每批后停核。 | Ops独立读OS/DB实际变化，与intent对账；任意source/生命周期漂移撤销该批资格。无授权保留production_pending。 |
| 10 G5封存 | 独立Reviewer-C检查RED→恢复E2E→生产入口限制，所有阻断项闭合；原归档和历史日志保持。 | 签收receipt+剩余生产门；自动恢复worker仍禁止；不能把“无事故记录”写成“风险不存在”。 |

本包性能不是删得越快越好：事前冻结批量大小、事务最长时间、WAL/磁盘上限和取消门；逐批记录总量/已删/未删及时间。未达到完整性与恢复要求时，任何性能数字不得放行。

## C. WP02：一个请求上下文与请求级可用副本

候选已核实：`SC/config.py / runtime_policy.py / policy_2x.py / policy_3x.py / cli.py / resolver.py / service.py / acquisition.py / close_gap.py / reader.py / error_taxonomy.py`；filing `C:/Users/郑曾波/Projects/filing-fetch/scripts/filing_contracts.py`、`fetch_filing.py`；现有测试 `test_runtime_policy.py / test_root_policy_2x.py / test_zr405_policy_export_cli.py / test_source_catalog_resolver.py / test_resolve_bundle_cli.py`（wiki tests/contract）。测试不是只准这几项，G0必须由实际调用链补充精确allowlist。

准入：G0需WP00.G1；G3需WP00.G3。真实跨root复用需S02；本包只读操作绝不因取状态自动pause/resume worker。

| 步骤 | 输入及具体动作 | 产物 / 检查点 / 停止 |
|---|---|---|
| 01 入口盘点 | 从真实resolve、exact ensure、latest ensure、close-gap finalize、filing handle消费列入口与所有policy读取/SourceResolver构造。 | caller清单与当前HEAD/hash；G0核四root来源资格和私有/公开后续owner决定，不能擅改public配置。 |
| 02 固定RED | 构造同SHA两真实副本映射：高priority禁用、低priority允许；逐路比较选择与policy/epoch；合成补C01–C10及ProgrammingError负例。 | 独立期望selected_location，而非调用global canonical求期望；missing policy不得静默回退。 |
| 03 合同审查 | 冻结不可变context字段、schema迁移/N-1明确协商、metadata是否网络/写journal、WAL/SHM允许边界；未知默认fail-closed。 | ADR、context schema、只读OS观察方案、四rootcase manifest；G1无owner决策时不得实施隐式兼容。 |
| 04 上下文接线 | 入口一次加载/构造，透传ensure/discover后再解析/close-gap/bundle/envelope；删除事后另读policy贴标签行为。 | 每段trace同一hash/epoch；mutation去掉任一注入必须红；不新增全局可变context。 |
| 05 选择与错误修正 | 从全部副本逐项policy→health→priority→稳定tie-break；global canonical仍展示用途；ProgrammingError与锁/超时分离。 | selected与global字段语义及拒绝原因；filing containment/sourceSHA强门不得删除。 |
| 06 只读接线审查 | reader缺DB不mkdir、不DDL；WAL真实状态分组；逐路检查间接writer/journal开库。 | G2独立caller审查、OS/SQLite authorizer/前后digest三层计划；不能用immutable=1读live WAL规避证据。 |
| 07 隔离机制测试 | C01–C10、反转root顺序、policy中途轮换、同size改bytes、reparse逃逸、schema未知、SQL参数错误；权限不足case blocked。 | OS写观察原始结果；确定性错误不得重试；缺sidecar仅允许G1冻结的明确协议行为。 |
| 08 四root E2E-R | 使用四个实际不同root合法真实文件/目录一致副本，从真实下游请求入口经filing子进程到wiki再返回handle；exact重复两次。 | 独立Test-Agent核真实路径未搬到companies、原文hash不变、provider/parser/LLM为0、全段context一致；G3。第四root空则明确blocked。 |
| 09 G4复用验证 | 先批准隔离真实CLI接线；对真实生产root只读需S02/操作卡与精确范围，不允许触发ensure隐式写。 | Ops从OS与独立网络观察证实0未授权写/外发；有写即停并留实际事实，不能仅信包络0。 |
| 10 G5资格 | Reviewer-C抽一种禁用canonical有允许替代副本、一种policy换代、一种只读异常，从原请求重走证据链。 | 已验层级和生产_pending分开；按原P02/P03而非“3.0loader文件存在”签收。 |

性能单列identify进程、resolve进程、SQL、文件SHA、policy加载，不以零解析等于零I/O；在WP06同协议下测完整大文件时延，暂不承诺速度倍数。

## D. WP03：期间/修订、授权、多缺口与真实失败账本

候选已核实：`SC/gap_plan.py / acquisition.py / authorization.py / close_gap.py / cli.py`；filing `scripts/fetch_filing.py / filing_contracts.py`；wiki现有 `test_source_catalog_gap_plan.py / test_source_catalog_download_authorization.py / test_source_catalog_acquisition.py`。只读inspect官方元数据/已存provider证据，不执行provider来“看看能不能用”。

准入：G0需WP02.G1；G3需WP02.G3。真实provider发现也属于network_case_run，不由DEV、文件名或allow_download默认值推导；G4取S02、WP03.G3及R2公共canary门。

| 步骤 | 输入及具体动作 | 产物 / 检查点 / 停止 |
|---|---|---|
| 01 原目标和市场样本 | 列CN/HK/US真实初始版/修订版官方元数据、FY/Q1/Q2/H1/非自然年，缺哪一市场哪种版本明确记录。 | scope和市场映射来源；G0独立agent核发行人、期间、版本不是按文件名猜。 |
| 02 RED锁定 | 保留F-F03四探针、10秒deadline→14秒、不同TTL同候选并发、多gap首项伪completed及失败漏stats。 | FF/T01–T08基线输出与独立时序/计数oracle；不改accession为递增词序救测试。 |
| 03 设计冻结 | period key/revision关系、ambiguous、canonical候选hash、stream字节硬上限、授权与幂等键分离、所有stage/unknown、deadline与恢复协议。 | ADR、授权卡、provider结果查回可用性、retry decision表；G1核已发请求unknown不可盲目再发。 |
| 04 新鲜度/授权实现 | 词序不决定时序；锁内重发现校候选；URL/期间/日期/size变化重授权或拒绝；未知size按实际stream cap。 | 最小diff、变更字段mutation；candidate hash完整绑定，禁止缺size当0许可。 |
| 05 多gap/单飞实现 | 每gap精确事务、剩余列表、partial/failed/unknown；只有全部必需授权项闭合completed；同候选不同合法授权共享幂等。 | 独立candidate ledger；并发同候选至多一有效fetch/commit，其他请求取得可验证同结果。 |
| 06 期限/账本接线 | 内外层锁/provider/retry共享deadline；异常后重算remaining、jitter后clamp；统一success/gap/fatal stats，已发生fetch不因handle失败清0。 | G2 reviewer逐异常路径检查；downloads/fetch_calls/bytes/commits分字段，unknown有原因。 |
| 07 故障与恢复 | 隔离链注入fetch成功commit失败、commit成功re-resolve失败、handle拒绝、坏JSON、响应后kill、不同授权并发、取消子孙。 | 独立OS/adapter日志和磁盘oracle对账；fault facade只算诊断，不能称真实provider失败E2E。 |
| 08 离线真实数据链 | 在真实raw/官方元数据获准副本上，用实际产品CLI验证existing/修订gap/ambiguous/剩余项；NETWORK_DENY时不要求真的补齐。 | G3核真实复用0外发和真实metadata识别；需要fetch的case应blocked/pending而非mock补齐后pass。 |
| 09 三市场E2E-N | 分别授权首次缺失下载→commit→resolve→filing handle、同请求第二次0下载、真实修订补缺；实际provider/子进程，不接替身。 | 服务请求ID、bytes/原文SHA、生产CLI阶段事实、独立网络计数；每市场独立G4，缺修订样本/授权则该case blocked。并发与断网故障另开精确卡，不重复真实收费直到绿。 |
| 10 G5结论 | 独立Reviewer-C任选一次失败和成功追踪官方metadata→candidate授权→真实fetch→落盘→handle；重算remaining。 | 不把已有两个市场/旧triplet替第三市场；缺T3保留production_pending，后续WP12不能把缺项算weekly成功。 |

性能报告分别列provider发现次数、进程数、锁等待、网络/写入/重解析/hash；优化必须保留锁内重校/完整性与独立负例。不允许以少校验或少gap形成更快的虚假收益。

## E. WP04：跨进程持久需求与实际artifact消费

已核实候选：`SC/processing_demand.py / scheduler.py / scheduler_policy.py / worker.py / producer_journal.py / artifact_read_model.py / artifact_handle.py / resolver.py / service.py / reader.py`；revenue `C:/Users/郑曾波/Projects/revenue-forecast/scripts/source_preparation.py`；wiki `test_zr507_processing_demand.py / test_zr508_scheduler.py / test_fc902_bundle_in_resolver.py / test_source_catalog_artifact_handle.py`。新增持久存储/migration文件位置未冻结，G1前不得猜名创建第三套队列。

准入：G0需WP02.G1；G3需WP02.G3。G3前不能启动真实worker验证；G4 demand/worker/pipeline取S01/S02/S04/S05/S06+manual_worker_run，外发另加network_case_run。

| 步骤 | 输入及具体动作 | 产物 / 检查点 / 停止 |
|---|---|---|
| 01 三进程链盘点 | 定位revenue submit、wiki受控接口、worker真实scheduler、reader返回；列两内存队列及artifact INSERT计数旧路径。 | scope、旧路径退役/adapter映射；G0核跨仓只读边界，禁止revenue直写wiki DB。 |
| 02 RED与oracle | A提交后退出、B重启需求丢失、失败无产物但调用非0、migration后真service不消费binding、payload变更双hash仍相等。 | D01–D10用独立进程/集合期望；人工fixture预merge binding不能称RED或E2E。 |
| 03 冻结持久合同 | demand key、状态/lease/fencing/heartbeat/terminal重试权限、源/角色版本、quota、attempt start/finish/unknown、唯一artifact read precedence。 | ADR、迁移/回滚方案、paused可见性、真实时钟协议；G1审跨进程崩溃和双worker旧lease写拒绝。 |
| 04 最小持久入口 | 只在wiki受控DB实现提交/查询/claim；两旧内存队列收敛到adapter；被safety阻断也保留合理pending及原因。 | 真实demand ID与请求关联；CLI退出再查仍存在，成功无缺角色不产生空任务。 |
| 05 worker/attempt接线 | 真实worker领取/开始/完成/失败；每外部尝试开始前记reservation/attempt，结束记结果，crash unknown；不再以artifact触发器当调用数。 | 进程B实际trace；重复同key与过期lease最小重算；费用事实不能回滚擦除。 |
| 06 artifact统一消费 | migration apply后由真实reader/service/resolver读同一view；核active/shadow/版本/current source/hash；消费者canonical重算bundle内容hash。 | G2独立caller清单+mutation；源SHA空拒绝与既有有效role保护保留。 |
| 07 机制故障矩阵 | A/B/C独立机制进程调用真实持久队列API，B不是worker loop，不执行parser/LLM/生产调度；100重复、lease过期双claim、kill、pause、时钟边界、S1→S2、单角色版本改动、失败没artifact、LIMIT前dedupe。 | Test-Agent独立ledger：任务/attempt/费用/产物各计数与状态；此为隔离机制测试，不冒充完整真实加工E2E，完整worker链留步骤09。 |
| 08 真实数据E2E-R无worker预放行 | 获准真实raw副本先经真实submit/query CLI，验证持久pending、blocked理由、bundle真实消费和重复只读；worker执行case等待全安全门。 | G3记录已跑部分和worker case阻断条件；不得为本包早过G3绕S05/S06真worker门。隔离机制可验证能力，真实处理层保持pending。 |
| 09 G4真实处理链 | 满足全部安全门后，以真实cohort A submit退出→B worker实际parser→C后续CLI读产物；二次精确复用，升级一个role后最小失效。 | Ops独立观察文件/DB/进程；二次真实0download/parser/LLM。LLM未授权时对应role pending，不用spy输出冒充真实摘要。 |
| 10 G5签收 | Reviewer-C随机选一失败attempt、一过期lease、一binding迁移与一次二次复用，从原文SHA追到consumer。 | 能力、处理层、生产层分字段；未走实际worker的需求持久化不等于全P05闭环。 |

本包恢复目标：保留已提交task/attempt、精确状态及去重；provider未知成本不可逆只可记录与处置。吞吐/公平性测每任务真实排队年龄、claim等待、饥饿和预算拒绝，不拿内存scheduler每秒操作数替生产指标。

## F. WP05：外发临界门、真实readiness与cohort

已核实候选：`SC/llm_summarizer.py / readiness_graph.py / source_lifecycle.py / section_extractor.py / service.py / artifact_handle.py`，以及实际调用入口所在`cli.py / worker.py`。已核实测试 `test_source_catalog_section_extractor.py`；其他安全测试由G0调用图选入allowlist，不能靠路径名称猜已覆盖。

准入：G0需WP02.G1、WP04.G1；G3需WP02.G3、WP04.G3。G4 LLM需S02/S04/S05、network_case_run及精确source manifest；经worker执行再加S01/S06和manual_worker_run。

| 步骤 | 输入及具体动作 | 产物 / 检查点 / 停止 |
|---|---|---|
| 01 出口与cohort盘点 | 找全部generate/fallback与mutating入口；记录GP010批准7、历史214 owner保留、全roots public后续决定。 | scope、出口图、真实数据许可；G0 Safety-Agent核不删214、不放松投资输出禁令。 |
| 02 RED固化 | 过期review/current policy换、normalized bytes换而source不变、identity矛盾、unknown/private root、fallback无权；7→752或增一个ID。 | S01–S11逐项预期0外发/0越界写；独立网络/文件observer证明拒绝，不靠返回“0”。 |
| 03 冻结出口合同 | 本次source+normalized hash、review TTL/now/policy/root/identity、required roles、consumer语义；cohort精确ID+SHA+count+列/路径/CAS及费用。 | ADR和最小公开源授权卡；G1独立Safety-Agent逐字段核谁可批准，缺成本/目的地就LLM_OFF。 |
| 04 安全门接线 | 临实际generate前验证同一输入快照，SQL只预筛；fallback独立grant；TOCTOU重新校验策略不重复读后放松。 | mutation绕开任何出口应测试红；旧sourceSHA/隐私/禁止输出强门保留。 |
| 05 readiness/cohort实现 | freshness按请求/provider证据；artifact verified required roles；semantic按consumer；mutating接口缺manifest/集合变化fail-closed。 | dry-run候选精确名单，与commit前CAS一致；不把published_date非空或任意span当ready。 |
| 06 G2接线复审 | 独立Agent核全部入口、fallback、别名路径和worker调用；审section_extractor并发变动合入顺序。 | diff/caller/hash审查；不能同时覆盖他人工作或产生第二套安全判定。 |
| 07 负例与越界故障 | 临界TTL±1秒、policy换代、原文恶意指令、源同size替换、cohort添加/删除/空、超预算、并发变更，在隔离目标执行。 | G3前独立Test-Agent统计真实observer：所有拒绝无调用/无越界写；安全拒绝不能改golden当失败。 |
| 08 E2E-R安全拒绝 | 对获准真实公开文档及必要隐私/恶意样本副本经真实CLI到实际出口门，在OS网络阻断下验证无权/过期/错误cohort真正不发送。 | G3签“真实数据拒绝链”；不能声称真实LLM成功或provider正确。缺许可的私有样本用机制负例，但其真实tier明确未验。 |
| 09 E2E-N最小授权 | 一份真实公开source-only样本、精确字符/token/cost/目的地grant、真实provider，核实际发送hash/响应/request ID；再跑同样输入复用0调用。 | Ops独立核服务计数/账单和本地attempt一致；禁止为7/7绕过安全拒绝。经worker需额外安全门。 |
| 10 G5签收 | Reviewer-C独立选policy漂移、normalized漂移、fallback和cohort新增ID核结果；功能不足可保留unsupported/terminal。 | 真实外发和禁止外发证据均齐才签该scope；全局production_verified不得由单样本推出。 |

性能门：完整安全校验的新增wall/I/O成本独立记录，优化缓存必须绑定相同bytes/policy/TTL，绝不以省略临出口验证提速。发现意外外发立即停，保留请求事实并按批准事件流程处置；不存在“撤回已经发送字节”的回滚承诺。

## G. WP06：worker真实瓶颈、取消、checkpoint和失败熔断

已核实候选：`SC/normalizer.py / worker.py / reader.py / scheduler_policy.py`；`W/scripts/source_catalog_worker.ps1 / source_catalog_worker_at_logon.ps1 / source_catalog_worker_at_logon.vbs`；filing `scripts/filing_contracts.py / fetch_filing.py`用于完整链测量。自启动文件只允许读结构，未经AUTOSTART不得修改注册/启用。实际scanner/store及parser route文件需G0按真实caller补allowlist，不猜测路径。

准入：G0需WP01/02/04/05.G1；G3需它们各G3。v5正式版本/冻结manifest和三路独立review仍需完成，历史导入不是已冻结授权。G4 worker取S01/S02/S04/S05/S06、公共CI门和manual_worker_run。

| 步骤 | 输入及具体动作 | 产物 / 检查点 / 停止 |
|---|---|---|
| 01 v5与基线锁定 | 对原8/12链、v5版本合同/待冻结门逐条映射；盘点相同真实root拓扑/DB副本/机器、可用空间与进程观察权限。 | scope和baseline/candidate精确版本；G0拒绝“902秒一定仍存在”或“SQL已快即可恢复”。 |
| 02 采样与RED设计 | 分enumerate、metadata、SQL prepare/consume、hash、parser启动/执行、commit、LLM等待、export、checkpoint、restart/backoff。 | case清单与wall/CPU/peakRSS/I/O/队列年龄/重试字段；历史902/0.231只作线索，不当本次数值。 |
| 03 冻结oracle与预算 | SQL输出有序ID独立集合oracle；25k/50k与5k/10k/20k/40k合成复杂度；真实规模副本协议、冷/热定义、分位数算法、取消和资源门。 | G1性能/设计/安全三路独立签同hash；锁定最低门见下，不能结果差后提高阈值。 |
| 04 SQL最小修正 | 在隔离库比较等价候选/显式索引迁移，覆盖force/retry/terminal/源漂移/重复location；禁止普通open隐式DDL。 | EXPLAIN+相同有序ID100%一致；旧坏查询scratch硬限2秒，禁止生产再耗902秒。 |
| 05 取消与checkpoint | 查询取消、控制轮询分离；scan完成原子checkpoint；parser大小/路由/子孙超时与下一query handler清理。 | 真实进程pause时序、kill点恢复；只更新heartbeat不算完成进度，取消残留handler不得误杀下次。 |
| 06 持久失败协议 | 成功完整cycle才reset，uptime不清预算；同signature3次/30min5次持久circuit，重启/登录不清，授权reset仍paused。 | G2独立agent核PS supervisor与Python共同状态，不存在两个互相清零计数。 |
| 07 机制/故障/规模 | scratch复杂度、SQL hang、parser hang、checkpoint前后kill、stale PID、权限/文件占用、cancel、重启；fault facade磁盘满。 | 每case实际进程树/状态/输出；独立Test-Agent计算分位数不删慢样本，缺格式route样本保持禁用或blocked。 |
| 08 E2E-R profile | 获准一致真实目录/DB副本与真实PDF/HTML，真实产品CLI/单worker受控测试进程从scan到产物；已具备的无外发链二次复用。 | G3前置是WP01/02/04/05.G3、本包G1独立安全命令卡及隔离数据/进程许可，不是S06自身。严格执行总计划R3第5.3节隔离协议，无法OS层阻止生产访问则blocked；LLM_OFF/自动prune0/无任务或自启动。测试成功后才签S06供G4使用，真实拓扑不可少扫取巧，缺49GB副本只报告有限规模。 |
| 09 G4小cohort | 全安全门通过后先1份、LLM_OFF、精确写合同、自动prune0，正常/pause/异常退出各停审；每升级scope新卡。 | Ops独立核CPU/产物增量/停止时间/无越界写，CPU>80%且无真实进度连续5min停。无manual_worker_run绝不运行。 |
| 10 G5性能签收 | Reviewer-C核同协议baseline/candidate原始采样、完整慢样本、oracle等价、恢复和circuit，不以局部SQL代整链。 | 实测绝对时间/分段占比/剩余瓶颈；worker退出回paused，自启动仍pending。 |

G1应正式冻结的继承最低门：SQL warm n≥30且P95<2s；cold-ish n≥10且max<10s；翻倍VM proxy≤2.8、wall median≤3；pause P95≤5s/max≤10s；scanner同拓扑交替n≥10，candidate P95≤120s且≥2倍目标须同协议。VM回调proxy不得称精确指令。大文件SHA峰值优化可采用分块但不能取消完整性核验；同metadata重审≤30天及高风险即时hash在ADR中锁定。LLMClient非线程安全，不以加线程绕开结构瓶颈。

## H. WP07：真实PDF/HTML解析、定位和1→3→7旅程

已核实候选：`SC/normalizer.py / html_capture.py / section_extractor.py / service.py`，现有测试 `W/tests/contract/test_pdf_page_aware_parser.py / test_source_catalog_pdf_page_aware.py / test_source_catalog_section_extractor.py / test_zr509_html_capture.py`。实际parser实现、table/fact输出schema和导入入口需G0重新沿真实调用核查，不能只改adapter测试。

准入：G0需WP04/05/06.G1；G3需它们各G3。G4 broker/HTML处理需S01/S02/S04/S05/S06、WP07.G3与相应运行授权；网络抓取/LLM另有精确授权。WP07.G1数据合同为WP08.G0前置，但WP08模型case不得倒过来当本包来源解析oracle。

| 步骤 | 输入及具体动作 | 产物 / 检查点 / 停止 |
|---|---|---|
| 01 真样本资格 | 冻结7份原PDF+2份原HTML，记录publisher/date/company/市场/期间/原SHA；另列列表式、多栏、跨页表、多实体、非紫金样本。 | case manifest与可读取/许可证明；G0核9份不同真实源，缺项写blocked，不用CHANGJIANG_TEXT顶替。 |
| 02 独立原文标注 | Source-Reviewer从原文物理页/网页截图/DOM定位独立标publisher/date/读序、表cell、单位/币种/period/entity、sections、关键facts；第二人核歧义。 | golden含原文locator、预期值/unknown、误差门、标注者身份；不能从candidate提取后复制回golden。 |
| 03 红例与合同 | 原7份5/7section缺口、HTML未接线、table/fact缺身份；补B01–B10，定义列表报告合法策略或unsupported终态。 | G1审physical vs printed page、跨页table、事实归属、缓存依赖及read-only export schema；不编造标题凑section。 |
| 04 parser真实接线 | 从raw真实字节走生产parser→normalizer→page/table输出，保持读序/单元格/locator；人工pages数组只保留T1测试。 | 候选最小diff及raw→中间→artifact trace；样本没被替换、错误保留原文。 |
| 05 HTML/section/fact接线 | 实际导入入口调用HTML身份/策略校验并连consumer；列表策略或终态；fact带source/locator/entity/period/unit，不存投资结论。 | 每source结果和gap/unknown；多实体不能只挂文档flag而每fact无归属。 |
| 06 真实consumer复核 | 从持久demand入口到真实artifact view/只读bundle，核source/parser/policy版本与章节/事实schema，WP08可读合同不偷加收入结论。 | G2独立caller审查；换source/locator后缓存必须失效，旧raw hash不变。 |
| 07 机制故障测试 | B01换页/B02跨页/B03单位/B04多实体/B05期间/B06HTML策略/B07缺字段/B08恶意/B09无section/B10cache drift；含进程中断/坏文件。 | 独立Test-Agent不使用被测adapter生成期望；安全拒绝为正确终态，不能改规则逼绿。 |
| 08 E2E-R全9源 | 获准隔离真实数据，真实CLI→持久需求→真实worker/parser→review/artifact→consumer；与两人原文golden逐份比对。 | G3结果每PDF/HTML分别列字段准确/缺失/unsupported，缺真实HTML导入则未过，不拼mock网络成功。LLM未授权部分明确pending。 |
| 09 G4 1→3→7逐级 | 精确cohort1执行并停下独立Ops审；通过才新卡3，再新卡7。2HTML以独立明确manifest纳入，不把7隐式扩大9。 | 每级G4独立签scope/hash、调用/成本/错误/恢复；实际结果非7/7逐份解释。旧214产物保留，不让kind选择752。 |
| 10 G5用户成果 | Reviewer-C独立抽跨页表、列表式和多实体报告及一HTML，从原文重新查locator、事实、来源、实际consumer。 | 真语义成果与unsupported/安全拒绝分开；生成7个文件不是7份真实准确可消费。缺项保留原痛点pending。 |

性能验收按页数/文件大小/route分桶列parser启动、运行、table/section/fact、queue与LLM时间，不能把列表报告0sections快速跳过当性能提升。一个坏文档不得持续占队列首；以真实其他样本完成和持久terminal/重试预算证据验fairness。

## I. 交给独立计划审查者的完成检查

- 每包10步、六个独立门是否都有输入/产物/停止点？哪一步仍需要设计决策，不可自动补猜？
- 是否每个“E2E”都声明真实来源、实际入口、进程/存储、oracle、是否真实网络以及scope，缺样本是否明确blocked？
- G0/G3/G4是否遵守R2精确依赖，不因这份手册换成整包G5互等？WP04早期不能要求WP06先完成整包，也不能绕安全门运行worker；只验证隔离能力并保留真实处理待办。
- 是否存在mock/clock/人工数组/重放结果冒充真实外发、真实49GB、真实broker或生产自然观察？发现一处即P1阻断计划签收。
- G4后是否保留production_pending和最终WP14资格，而不是每包局部绿自动关闭117项？
- 本文所有未来命令必须在执行前按实际CLI/parser参数和help副作用审查形成command card，**本文件没有提供未经核实的可直接执行产品命令**；弱模型遇未知flag必须读源码/入口，不试运行猜测。

本手册没有宣称这些步骤已经实施或通过；当前交付为待独立审查的执行细化文档。若未来权限/版本/样本变化，先更新卡片并重新独立签收相应门，不能靠旧计划通过继续运行。
