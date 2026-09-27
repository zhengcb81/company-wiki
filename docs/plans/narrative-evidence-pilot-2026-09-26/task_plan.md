# 叙述性证据选择与摘要：小范围试点及实施方案

> 独立实施计划；不替代仓库根目录或任何已有专项计划。Phase 17 的旧库退役已完成；Phase 18 的离线 G1 选择、定位和草稿验证已完成一轮。**2026-09-27 新顺序：RF 主线并线已完成，先实施 R4 数据湖抽象层，再继续本计划的 W5/G2a、Worker 与空间处置。**本计划自身不写 RF，不启动生产 Worker；已有隔离叙述工位与主树未提交文件保持原样，待抽象层合同接入时按当前文件快照整合。

## Goal

用 10 份不同类型的 PDF 与 2 份英文 TXT 验证业务叙述选择、证据定位和摘要边界，形成 company-wiki 与 filing-fetch、StockWiki、revenue-forecast、invest-quick-scan 兼容的可实施方案。

## Next Step

**2026-09-27 Phase 22 阻断结论：**暂停 R4 consumer/跨仓接线。下一步必须先按 TDD 增加“正式 `SourceEnsureResult.to_dict()` / CLI latest-as-of gap payload → v2 projection”红测，再让 consumer 恢复读取既有 schema 的 `acquisition`（若要改名，必须做 schema 升版和兼容迁移，不能单改 consumer/test）。随后为复杂度临时豁免建立 G0/G1e/G2 硬阻断并按生产启用顺序分解；现有 390/88 项绿灯不能覆盖这个 producer/consumer 反例。

**2026-09-27 最新优先级（优先于下方历史实施快照）：**先按[数据湖边界复核](data_lake_boundary_review_2026-09-27.md)与[R4 数据湖实施卡](../painpoint-outcome-audit-2026-09-05/r4-data-lake-priority-rollout-2026-09-27.md)实施来源身份、受控读取、跨进程交付和各仓责任；RF 远端 main 已并入 `3a69f9c5`。R4 基础 reader 的真实 B/C.local E2E 通过后，再把本计划 selected evidence package 接到 G2a；已有离线 G1e 代码在自己的隔离工作树保留，合同时整合。生产 Worker 与原文处置仍待各自大节点；试点 `source_id → raw path` 映射不能成为正式 G2 消费者合同。

**并线前执行快照（已由上方最新优先级覆盖）：**当时 RF `main`/`fcap` 同为 `ee0a82bfd`，后续工作仍在本地未提交，故 G0 与产品接线暂停。保留的事实是 RF Phase 7 计数不等于 CWP 来源接口已完成；I-05-C 的真实 producer/consumer/event 及 I-06-A/B 的 caller/跨进程 claim 尚需按新 reader 合同验证。E-T `discover`/`fetch-candidate` 与隔离 importer/preflight 有历史离线收据；CWP 主树与 transcript 分支的 `canonical_writer.py` provenance 调用点有 diff，整合时逐 hunk 联合回归。Worker、生产 SourceBundle/DAG/consumer 和原文处置不由 RF 并线自动放行；实施前按[跨项目协调](cross_project_coordination_2026-09-26.md)重锁当前状态。

### 历史实施快照（仅供追溯，状态以本节首段为准）

**当前实施收据（2026-09-27；优先于下方较早的 G1e-C 状态段）：**G1e-C importer 核心现在有可运行的 `company-wiki-transcript-import --wiki-root ...` stdin JSON CLI，并在隔离 worktree 注册 console entry。CLI 只接收 `/2` transcript result；重新加载 company-wiki 当前 runtime/right policy、重算精确候选授权并与请求、候选、预取 admission/hash 绑定后才创建 catalog/writer。固定从 wiki root `config/provider_use_policy.json` 读取 rights policy，缺失即拒绝；不提供可自选 policy 路径，也不写生产 policy。合成 fake E2E 覆盖合法原件→canonical raw/sidecar、stdout 不含正文/重复 base64、staging 清空，以及权利撤销后在 raw/staging/catalog 写入前拒绝。聚焦 CLI+import/material+rights suite **33 passed**；Ruff 与 diff check 通过，pytest 独立 run root 已验证/清理。此 slice 完成不等于跨仓接线：CLI 只能复核当前授权和结果，尚不能证明父进程在 discovery 和 exact body fetch 前按顺序做了 rights gate；preflight JSON 不是可信时序证明。filing-fetch 的 discover→候选选择→精确授权→`fetch-candidate`→stdin import 全链 E2E、schema/partial-success 和 G1e-D 仍待 revenue-forecast 同步窗口。`transcript_tool.py` / `transcript_api.py` 按既有契约始终返回未翻译英文原文，不加无作用的翻译 flag；legacy `scraper.py` 已有 `--no-translate`，并新增 `--disable-translation` 清晰别名。E-T 离线回归 **108 passed, 2 deselected**（需本机 LLM key 的偏好测试及可能调用 Google 的合成短句测试明确排除）。Koyfin/Seeking Alpha 不接入；没有证实增量价值时不增加 provider。

**2026-09-27 当前下一步：**[G1e provider 逐动作权限合同](transcript_provider_rights_contract_v1.md)及[跨仓集成合同草案](filing_fetch_transcript_integration_v1.md)已成文；company-wiki 隔离分支具备请求前闸门、下载后 policy/response 二次校验、紧凑 lineage schema v2 和 fake-provider→canonical writer→英文 TXT/locator replay E2E（34 passed）。**G1e-B 已在 earnings-transcripts 实现并通过全量离线回归**：默认结果 schema `/1` 保持原样；`--include-source-payload` opt-in 返回 schema `/2` 的受限 base64 provider 原件、MIME、安全 effective URL，成功结果不重复携带正文；全量 **100 passed, 1 deselected**（一个既有 LLM-key 测试因本机无凭证跳过），Ruff 与 `git diff --check` 通过。设计复核发现并修复了 fetch 前候选授权时序：E-T 新增 `--operation discover`（只返回候选）和 `--operation fetch-candidate`（只取调用者授权绑定的精确 URL），旧单步接口禁止用于集成；全量离线回归 **106 passed, 1 deselected**。下一步是 **G1e-C：company-wiki stdin importer**，实际证明 caller 在 discovery 前校验 `discover` 权限、在 candidate-fetch 子进程前校验 exact DownloadAuthorization/retain/derive 权限，再验证 `/2` JSON、base64/原件 SHA、MIME/URL/期次和 rights pin，调用 canonical writer 与 compact lineage。随后才是 filing-fetch schema 1.3/独立授权/partial-success 接线及跨仓 E2E；这一段仍须等待 revenue-forecast 同步窗口，当前不修改 filing-fetch、RF 或共享 role DAG。filing-fetch 文档 schema 1.1 与代码 1.2 的漂移将在其获准实施时一并修复。Motley Fool 权利 hard deny、FMP 单次 canary 402/保留权未确认，所有阶段仅 fake provider，不访问真实正文端点。工具/平台比较见[对照卡](earnings_transcripts_vs_platforms_2026-09-27.md)，结论仍是先不买；Revenue-forecast I-17-A 自然观察在飞，Worker 继续 paused。

**2026-09-27 G1e-C 增量状态（以本段为准）：**隔离 worktree 已完成 company-wiki importer 核心库函数，不是 stdin CLI 或端到端 caller。它要求预取 admission 绑定 request/candidate/auth hash；限制并校验 `/2` JSON、重复键、ticker/venue、FY/Q/as-of、候选 URL/ID、原始 base64/SHA/MIME/时间；复查下载后 rights policy；规范化写入前失败不产生 raw/staging；成功写入单份原件、rights/auth hashes 与校验动作进 namespaced provenance extension，并只在内存产出未翻译文本及 locator。核心+canonical writer/acquisition/sidecar 合同测试 **56 passed**，Ruff 与 diff check 通过。**G1e-C 仍未完成**：stdin 包装、discovery 权限前闸门及调用者在 E-T 子进程前的真实排序尚未接；G1e-D/E 继续等 revenue-forecast 同步窗口。E-T 输出的 exchange 是调用参数的回显，故正式调用必须先有精确交易所映射；`auto`/未知 venue 在 importer 端拒绝。没有新增 provider，Motley Fool/FMP 仍不放行。

Phase 17 的 F0–F5 已完成。G1 离线主样本和回归集已经复跑：12 件样本 1,289/1,289 locator 回读成功、18/18 锚点命中、13 条人工草稿通过引用/角色校验并完成实施者逐条核源；所有草稿仍是 `needs_review`，两份 IR 仍有不稳定表格定位。JSON 输入字节已实测，**不是数据库增量**。两个试点 CLI 有隔离 `--run-root`；P06 定增说明书与 T02 英文电话会完成中英检索；新增 pilot-only resolver 在 12 件样本上从隔离 raw 重新解析/选择，逐组核对 source SHA、evidence ID、locator 和文本 hash。bundle v0.2.0 的最新合并回归为 12 个检索/回源单测 + P06/T02 双样本 E2E + 12 件样本 selected-anchor/raw-replay E2E，共 **14 passed in 130.77s**；历史全绿收据为 122.56s；`ruff check` 通过。pytest 实际 basetemp 已删除并复核不存在，`tests/e2e/.runtime/` 运行前后均不存在，run tree 已恢复基线。此结果不连接生产 catalog/query API 或消费者，也不等于 G1/G2 共享集成放行；不证明未选内容召回率或生产性能。Revenue-forecast 当前已推进到 progress Round 120、register §162、owner decisions §39：I-16-B 部署执行已 `accepted_scoped` 落定；register 将 I-17-A 列为在飞，但其基础执行卡仍标 `planned`；I-17-B 后继待做。I-05-C 的真实 producer/consumer 入口/InvocationTracker 事件 schema 开放项及 I-06-A 的 RF caller/CLI、跨进程 claim、I-06-B consumption 面等 carried-open 仍阻止 G0。不得改共享接口、store、producer、service、DAG 或 Worker；具体证据与时间点见[跨项目协调](cross_project_coordination_2026-09-26.md)。

## Current Phase

Phase 18：隔离 G1 离线选择/摘要、两文档检索 smoke、12 件样本已选锚点和 package→raw 回放回归已完成；G0 跨项目消费合同未冻结；G1e 的 E-T 与 CWP 上游隔离接口已实现，filing-fetch companion 及跨仓 E2E 在推进；G2 consumer、G3 Worker、G4 原文处置均待各自门禁。

外部来源采购补充：FMP Basic key 实测 profile/有效 SEC 检索 200，press releases/transcript dates 402；SEC 原生 API 无 key。以 246 个本地公司目录作保守分母，Basic 补充 SEC 检索约 2,076 calls/30 日，纯 SEC/IR 路径为 0 FMP calls；Koyfin 无用户 API，Seeking Alpha 个人订阅不授权自动抓取；Motley Fool 官方条款也禁止自动访问/采集，现有适配器不得接通生产。详细价格、假设、权利分级和 30 日试点见 [外部数据源与成本卡](provider_cost_and_capability_2026-09-27.md)。采购结论为先不买，且不改变 G0/G1e 门禁。

## Phases

### Phase 1：样本与基线
- [x] 覆盖年报、半年报、季报、招股书、两类再融资、投资者关系、英文电话会议及低价值格式文档。
- [x] 对每份样本记录文件身份、尺寸、页数或行数、来源及已有规范化状态。
- **Status:** complete

### Phase 2：小范围只读试点
- [x] 抽取每类文档的业务片段与低价值片段，保留页码、段落、行号或字符区间。
- [x] 检查现有解析、章节、摘要的命中、误收、漏收和来源质量。
- [x] 记录候选选择/摘要策略和不可自动判断的情况。
- **Status:** complete

### Phase 3：实施方案与跨项目契约
- [x] 明确阶段化流水线、数据契约、Worker 调度和存储方案。
- [x] 明确 filing-fetch 接入英文 TXT 电话会议以及跨仓边界。
- [x] 给出验收指标、试点门槛、实施顺序、回滚与依赖。
- **Status:** complete

### Phase 4：复核与交付
- [x] 复核样本证据和方案的可执行性，标注未验证事项。
- [x] 核对 Git 状态，确认只新增本目录文件。
- **Status:** complete

### Phase 5：实施细化与审查设计（用户 2026-09-26 追加）
- [x] 将 W0–W7 展开为带输入、输出、允许修改范围、先后依赖、停机条件的实施卡。
- [x] 为 12 份真实样本、对抗样本、跨仓消费和空间迁移建立可复现测试矩阵。
- [x] 明确独立审查、证据收集、问题修复与放行规则；消除会让实施者自由猜测的设计歧义。
- [x] 校验新增规划文档及 Git 状态，保持既有计划和产品文件不变。
- **Status:** complete

### Phase 6：Worker 并发与丢任务恢复设计（用户追加）
- [x] 核对现行 Worker、catalog 操作锁、SQLite 事务、内存需求队列、调用审计和 LLMClient 状态。
- [x] 补充先可靠再并发的架构、租约代际、幂等提交、故障对账、暂停和多 agent 使用边界。
- [x] 将 W6 的实施卡、测试矩阵和独立审查同步到新设计。
- [x] 验证规划文件链接、代码围栏与 Git 隔离。
- **Status:** complete

### Phase 7：可实际实施的多文档并发方案（用户追加）
- [x] 查 Worker v5/R4 C/D 现行归属与 `automation` 持久 job/attempt/effect/outbox 真实实现。
- [x] 将早期“新增 catalog 任务表”的错误方向改为复用 R4 C05 唯一入口；写明现行 AUTO 的原子性缺口。
- [x] 给出进程拓扑、job DAG/key、claim/finish 事务、两库/文件 saga、暂停线性化、故障注入、基准和灰度/回退卡。
- [x] 用隔离 basetemp 运行现有 automation 单测并记录真实基线；同步计划入口、执行卡和测试/审查。
- [x] 全面核验链接、矛盾表述、Git 隔离及最终状态。
- **Status:** complete

## Phase 8：第二轮设计审查（2026-09-26）

- [x] 复查新 DAG 与旧 `normalize_catalog` 的调用和空间目标，移除会隐式生成全量 normalized/spans 的前置。
- [x] 按现有 `JobStatus` 状态机审查两库 saga；明确上游 visible 后才升下游 READY，来源退休时按合法状态封存运行 attempt。
- [x] 补 Windows reparse/跨卷文件暂存边界及 F17–F20 故障注入，更新验收与审查入口。
- [x] 核对本独立计划内的引用、链接、围栏和 Git 修改范围；不启动 Worker，不改产品代码。
- **Status:** complete

## Phase 9：反例审查与小样本验证（用户追加）

- [x] 在已有 PDF 中只读测量正文/表格双视图、业务表、IR 问答和文本锚稳定性；用内存 SQLite 检验中文全文检索的短词反例。
- [x] 以只读 SQLite 随机抽取 1000 条旧 span、读取库页面与磁盘余量，明确样本局限；退休来源语义仍列为 W0 未验证项。
- [x] 将发现转化为 W0/W2/W3/W5/W7 的门禁和测试；保持跨仓与 Worker 状态不变。
- [x] 复核独立计划目录、链接与 Git 修改范围。
- **Status:** complete

## Phase 10：46 GiB 降容升级设计（用户追加）

- [x] 核查主库文件、freelist、样本 JSON 压缩、现有归档/自动 prune 门禁及本机空间容量。
- [x] 将“新来源止增”与“旧库文件实质缩小”分开，写出 S0–S5 迁移和回滚门槛。
- [x] 明确当前不能给出确定节省 GB 数或用 1000 行样本外推全库；提出隔离小批量测法与净总字节验收。
- [x] 核对只改独立计划目录，Worker 与生产库未动。
- **Status:** complete

## Phase 11：重复字段与空单元降容复核（用户追加）

- [x] 用第二个固定随机样本检查 `span_json` 是否重复序列化已有关系列，并把重复比例严格限定为样本观察值。
- [x] 将字段单次存储、正文单份保存、空表格单元不建 span、兼容读取适配器和全量精确 S0 账本纳入降容设计。
- [x] 复核有业务价值的表格/IR 内容必须保留，防止为了节省空间误删证据。
- [x] 核对规划文档和 Git 范围；不改代码、数据库、Worker 或其他项目计划。
- **Status:** complete

## Phase 12：旧库清空与干净重建可行性审查（用户追加）

- [x] 只读核对 catalog 输出目录、原始输入 root、独立 source_manifests 目录，以及混存在 `.source_catalog/` 的控制/审计文件。
- [x] 比较“直接删除后旧流程重跑”与“新 schema 影子重建后替换”，明确来源历史、消费者引用、Worker paused 状态和容量风险。
- [x] 为来源哈希核验、新格式门禁、影子重建、双读、切换、延后清理写出逐步审查条件。
- [x] 保持 planning-only；不删除文件、不运行扫描/Worker、不改配置或其他项目计划。
- **Status:** complete

## Phase 13：旧主库提前退役实测与快路径（用户追加）

- [x] 只读精确统计全部非 span 表、源/文档/位置/产物与 active 旧 span；核对 ADR-009 退休归档、H01 风险和 StockWiki 当前 provider 状态。
- [x] 在系统临时目录测得目录元数据 214.84 MiB、目录+全部 active span 2.849 GiB；两者外键无错误且 `quick_check=ok`，临时库已清理。
- [x] 只读测 zstd 六处样本压缩比与当前磁盘余量，明确完整压缩备份大小和恢复性仍待实际 F2 验证。
- [x] 写出 F0–F5 提前退役卡；同步实施方案、空间方案、执行卡、测试、审查、发现和入口；明确 active 查询保留、retired 查询失败关闭、完整备份、回滚和精确文件删除门槛。
- [x] 核对计划文档链接、围栏及 Git 范围；未改生产 DB、Worker、代码或其他活动计划。
- **Status:** complete

## Phase 14：新仓库与逐文档删除方案核查（用户追加）

- [x] 只读确认旧 SQLite `auto_vacuum=0`、`journal_mode=delete`，区分逐行删除与文件级实际释放空间。
- [x] 区分可逐件迁移清理的 raw 重复副本/derived 与不能逐件物理缩小的共享 SQLite、整包 gzip 归档。
- [x] 将新数据根、可选新代码仓、逐来源验证和 F0–F5 整库替换的先后关系写入退役卡。
- [x] 保持 planning-only；未创建新仓、迁移/删除任何原文或派生文件、改写旧库或启动 Worker。
- **Status:** complete

## Phase 15：不重要旧来源的原文删除设计（用户追加）

- [x] 只读核查 SourceManifest v1 的原路径/哈希校验、目录 source/location 状态与各输入 root 的边界；确认 `skipped_*` 不等于原文可删。
- [x] 将重复副本、唯一低价值来源、保留/阻断和外部只读输入分开；设计版本化处置状态、逐路径删除 intent/receipt 与崩溃恢复。
- [x] 写出 D0–D5 实施卡、误删反例、盲测/复审、旧 span 与下游引用门禁、实际同卷字节验收，并同步现有独立计划的入口、测试、审查和 Worker 手册。
- [x] 保持 planning-only；未删原文、未创建新仓、未改生产数据/代码/其他活动计划，Worker 仍暂停。
- **Status:** complete

## Phase 16：逐步骤空间增减实测与预算（用户追加）

- [x] 只读统计 `.source_catalog/`、`source_manifests/`、`companies/` 的当前文件逻辑长度、类型分布和 C 盘余量；区别总占用与可回收量。
- [x] 对未变化的完整旧 SQLite 运行不落盘 `zstd -3` 流计数，得到 5.773 GiB；以实测 2.849 GiB 活跃库计算 F1/F2/F5 净额和 F2 恢复试验峰值。
- [x] 将新包/索引、旧 derived、重复 raw、唯一低价值 raw 与归档/备份分别列为已知或待 D0/W 试点测定的变量；不能用负例小样本外推。
- [x] 写入独立逐步空间账，并同步快路径、空间方案和入口；未创建备份/影子库、新仓库或删除文件，Worker 保持暂停。
- **Status:** complete

## Phase 17：按用户授权实施旧库提前退役（完成）

- [x] 更新 F0–F5 计划：明确取消完整落盘恢复；改为源库/压缩包 SHA、`zstd -t`、全量解压流 SHA/长度相同，旧文件切回与 active/retired 查询差分仍为硬门槛。
- [x] 新增 `implementation_run_2026-09-26.md`，明确 I0–I6 输入、输出、拒绝条件、收据、风险和无落盘恢复约束；不混入 W/D 卡。
- [x] 实施只读查询的 `legacy_evidence_archived` 失败关闭与临时库合同测试；实施影子库/压缩流准备工具，临时目录测试含触发器、零 WAL/nonzero WAL 和 Worker pause。
- [x] 实施只读证据差分审计和带中断意图收据的精确文件切换/切回工具；临时 SQLite 验证审计门禁、Windows 零 WAL/SHM 移动与旧库回滚。
- [x] 完成 F0 生产只读冻结、F1 活跃影子库、F2 正式备份流式验证与 `prepared.json` 收据；完整落盘恢复演练按用户要求取消。
- [x] F3 active/retired 证据差分、catalog query/resolve 差分及当前三方入口调查通过；真实下游业务运行未执行，收据明确其边界。
- [x] F4 精确文件级切换，658 秒间隔的两次生产烟测通过；真实生产切回未做，临时 SQLite 故障夹具已验证切回工具。F5 按精确旧库文件 SHA/路径删除，准备前至清理后同卷可用空间净增 37.630 GiB。Worker 保持 paused。
- **Status:** complete

## Phase 18：按大节点推进新流水线与原文处置（进行中）

- [x] 回应用户的效率要求：以 [G0–G4 大节点审查节奏](milestone_review_cadence.md)替代 W/N/D 每张卡的独立签收和重复全量校验；保留删除、并发和跨项目合同的关键失败关闭。
- [x] 为 G1–G4 补充关键路径端到端测试、独立运行目录、run-id 清理/中断恢复和测试树基线一致性门槛；详细规则见[关键节点端到端测试计划](end_to_end_test_plan.md)。G1 离线 smoke 已执行；transcript acquisition、正式消费者、Worker 并发和 scratch 处置 E2E 仍按 G0/G1–G4 门禁待做。
- [x] 二次审查 E2E 计划：为 G1–G4 写明完整链路和放行条件；run-id 运行根开始时必须不存在；正常/中断清理只允许删除经校验的精确运行根；新下载与派生产物结束后必须不存在；G2 调用消费者真实 reader、G3 使用真子进程、G4 只删 scratch 副本。未增加逐卡签收。
- [x] G2 只读合同调查：StockWiki strict Source Provider v1 与 pilot bundle v0.2.0 不兼容，且 provider 当前 disabled；invest-quick-scan 仅有 optional identity mapping，不消费叙述包。已将 G2 E2E 拆为 G2a 叙述证据真实 reader 与 G2b 身份互操作。
- [x] G1e acquisition 接口审计：当前没有 earnings-transcripts MCP tool，只有带固定配置/日志/锁/cache 副作用、默认翻译且不能请求精确期次的 Python CLI；filing-fetch 代码只解析/确保一份 filing，schema 1.2 拒绝未知 companion 字段；安装技能 schema 1.1 与代码 1.2 不一致。已拆出独立 transcript acquisition contract gate；该上游 gate 不依赖 RF 下游 consumer G0。
- [x] 2026-09-27 后续只读状态校正：earnings-transcripts 工作树已新增未提交的无文件副作用 transcript_api.py 与 stdin JSON transcript_tool.py；上一条“只有旧 CLI”只描述原审计时点。filing-fetch companion 编排和 G1e 跨仓 E2E 尚未完成，不因此放行。
- [x] G1e 隔离 transcript material lineage：schema v2 只保留 parent source ID/hash、原件 MIME/大小、derived TXT hash/大小、extractor 版本及行数；逐行 byte locator 只在内存中使用，由 loader 按可信 receipt MIME 从 raw 确定性重算，且校验 persisted TXT bytes。27 项 provider/material/original-import/canonical-writer 测试通过，ruff 与 `git diff --check` 通过；两个由本轮创建的 basetemp 均逐一路径核验并删除。此为 helper 合同，不是 artifact 持久化/生产集成。
- [x] G1e 下载后权限与响应复核 helper：重新验证请求授权和当前 rights-policy hash，核对候选/receipt identity、成功 HTTP 状态、最终 URL 的 fetch/retain/derive 许可、MIME allowlist、字节上限、staging containment、regular-file 属性、实际长度与 SHA；拒绝只返回原因，不把正文交给 canonical writer。合并定向回归 **33 passed in 5.56s**，Ruff 与 `git diff --check` 通过。测试过程中 3 次断言/fixture 调整均已修正并记录；4 组由本轮创建的 requested/effective basetemp 精确核验后清理。此 helper 还不是真实 acquisition E2E；当前通用 `DownloadReceipt` 无 effective redirect URL 字段，不能宣称该 URL 已写入持久 provenance。
- [x] G1e-CWP 假 provider→canonical import E2E：隔离 run root 内跑 prefetch zero-call 拒绝、unapproved redirect 拒绝并清除 staging、合法 HTML 原件 import、未翻译 TXT/紧凑 lineage 持久化和定位重算、SourceResolver 复用；finally 逐项确认临时树 baseline restored。最终组合 suite **34 passed in 4.31s**；Ruff 与 `git diff --check` 通过，pytest 的两个精确 basetemp 已安全清理。此 E2E 只过 company-wiki fake seam，不等于 filing-fetch/真实 earnings-transcripts 已接通。
- [x] 2026-09-27 跨项目现状审查：filing-fetch skill 文档 schema 1.1 与代码 request schema 1.2 漂移；earnings-transcripts JSON subprocess 不是 MCP，且成功结果无 raw provider payload bytes/effective URL；原输出不足以生成 immutable canonical raw。详细目标合同、partial success、Worker lock、payload、rights gate 与四阶段 E2E 见[跨仓集成合同草案](filing_fetch_transcript_integration_v1.md)。
- [ ] G0 在 revenue-forecast I-05-C/I-06-A 与 Worker v5/R4 的最新正式合同上冻结本专题 source package、consumer mapping 和唯一 job owner。**当前保持关闭**：I-05-C 虽有盘上 `accepted_scoped`，其复审仍明确保留真实 producer 尚未实施、RF `consumer_analysis` 入口待 owner、InvocationTracker 持久事件 schema 待 reviewer 的开放项；I-06-A 的较新 `accepted_scoped` 仅验收 store-side lifecycle，RF caller/CLI、跨进程 claim、I-06-B consumption face 等仍是 carried-open，生产晋升还需 owner commit。RF §162 已确认 I-16-B 落定、I-17-A 自然观察启动；这没有关闭上述 G0 缺口。任何新增 artifact role 还须纳入 SourceBundle/read-model/role DAG 全链评估，G0 前不升级共享 bundle/schema。具体证据见[跨项目协调](cross_project_coordination_2026-09-26.md)。
- [ ] G0 同时引用 R4 A02–A04 的**目标位置透明合同**，并列出 B07 待实现/待验条件：`document_id + source/version hash + locator` 为消费身份，root/path 不决定业务字段或权限；核定跨进程受控 open、字段级 provenance、来源工件与 RF `consumer_analysis` 的归属。G0 是设计冻结，不要求尚未实施的 B07 先通过；只做一次架构裁决，不另设数据湖实施 DAG。当前证据和反例见[边界复核](data_lake_boundary_review_2026-09-27.md)。
- [x] G1a 完成 12 件隔离样本选择/分类、1,289 个选中证据 locator 回读与 18 个目标锚点精确映射；两份 IR 表格维持 `needs_review`，两份无业务动态的格式化文档标记跳过。6 件 PDF 为 `partial`，不当作完整覆盖。
- [x] G1b 建立 13 条人工来源摘要草稿；13/13 通过 evidence ID、source SHA、语言、角色和问答关系机械校验；另完成实施者逐条 source-support 审查，记录在 [G1 摘要来源支持审查](g1_summary_source_support_audit_v1.md)。所有草稿仍为 `needs_review`，这不是独立签字或生产验收；T01/T02 保持英文。
- [x] G1c-a 离线量测候选 evidence JSON：主样本 542,820 B / 52,196,853 B 原文（1.0399%）；四件回归集 202,661 B / 14,939,109 B（1.3566%）。逐件序列化字节与 fsynced 临时文件长度相同、均在选择上限内；这是输入包大小，不是 DB/索引实际增量或摘要成品大小。主样本和回归集各自定位/锚点零失败。
- [x] G1d 隔离 CLI smoke E2E：P06 定增说明书 + T02 英文电话会议先复制到唯一临时 run root，再运行选择/定位/摘要草稿验证；2/2 文档锚点与 locator 通过、3 条草稿为 `needs_review`、越界输出被拒。45 项相关单元/端到端测试通过；运行目录前后快照相同，下载/副本/JSON/temp 文件已清理。**不等于 G1 全量门禁**，无 catalog、export、真实 provider、Worker 或 LLM 写入。
- [ ] G1e filing-fetch × earnings-transcripts acquisition-to-summary E2E：新增 `tests/e2e/test_filing_fetch_transcript_pipeline.py`，经过新版复合 orchestration 与正式 adapter seam，使用 fake provider 覆盖授权下载、resolver 命中复用、未授权零调用、transcript 失败但 filing 成功；验证精确 period/as-of、正文不翻译、原始 payload/file 与派生 TXT 的 hash/parent 关系、HTTPS sidecar、locator 回读及测试树恢复。**前置增加逐 provider/动作权利表；Motley Fool 自动路径拒绝、Seeking Alpha 个人订阅拒绝、FMP 402 不重试，三类都不得留下正文。** 还须冻结 transcript acquisition 独立合同并解决 skill/code schema 漂移；不依赖 RF 下游 G0。当前 P06/T02 smoke 与隔离 writer 合同测试均不覆盖 filing-fetch 的真实 acquisition 编排。
- [x] G2a 检索隔离预研：`NarrativeEvidenceSearch` 对 selected-only package 建 query-local 内存 BM25；新增 pilot-only `NarrativeEvidenceResolver`，bundle v0.2.0 将 replay_contract（parser/selector 版本、文档类型/语言、解析选项、选择预算）内置；resolver 只由调用方提供 source→raw path 映射。回放校验 raw SHA、source ID、完整 selected-group 集合、ID/locator/text hash，且不写索引/cache。最新合并回归包括 12 个单测与 P06/T02、12 件样本两个 E2E，共 **14 passed in 122.56s**；`ruff check` 通过，pytest basetemp 清理并复核不存在，`tests/e2e/.runtime/` 保持运行前基线（不存在）。**不是 G2 放行**：尚无冻结的生产 package/source schema、处置/时点授权、持久 catalog/query API、盲留出集召回率/p95 或三方消费者合同。
- [ ] G1c-b 共享来源扫描/目录/export 接入、生产保存差量与独立审查；只有 G0 冻结后才能做。不得由离线 JSON 字节估算永久存储量。
- [ ] G1c-b 接入前按 R4 B01–B10 当前实现核对扫描器的 root-kind 元数据分支、normalizer 路径选择和同 SHA 副本读取；先验证优先级换位/云占位/路径移动，再接共享 catalog。已修的 resolver fallback 与统一 reusable policy 不重复开发。
- [ ] G2a E2E：G0 合同冻结后，从隔离 export 经过 StockWiki 与 revenue-forecast 各自真实 reader/adapter 到只读结果；owner 未提供可运行真实 reader 时保持 hold，不以本仓 harness 替代。
- [ ] G2a 的正式 reader 不接收试点 `source_id → raw path` 映射；接线前须有 R4 B 阶段受控 open 的独立验收（含 B07–B10）与 C01–C04 消费者适配。复用 R4 L01–L12、P01–P03，再补一轮叙述证据 ID/locator/撤回跨根不变及真实 RF/StockWiki reader E2E；不为每个目录新增消费者分支。
- [ ] G2b E2E：只验证 invest-quick-scan optional identity snapshot 的 mapped/unknown/ambiguous/null 路径，不读叙述包、原文或摘要。
- [ ] G3 E2E：以隔离持久 job store 和 fake provider 运行真 Worker 子进程，覆盖多文档并发、重试/ACK 丢失、暂停/恢复和进程退出清理。
- [ ] G4 E2E：在 scratch company tree 中跑逐路径处置、删除与中断恢复；仅删本轮创建的 scratch 副本，不接触生产原文。
- [x] D0 完成本地原文、sidecar、derived、index、artifact 与旧 span 的只读盘点及 source ID 关联；1,490,530 条 span 涉及 1,636 个 source ID，其中 1 个缺原文 location、329 个 source ID 跨 root 有位置。复用路径的历史大小冲突见 [D0 收据](d0_inventory_receipt_2026-09-27.md)。跨仓消费合同另由 G0/D1 门禁决定。
- [ ] D1 冻结 `SourceDisposition/v1`、正式 raw 保留/处置规范及查询/预览/export 行为；需处理 SourceManifest v1、旧 span 和三方消费者合同。G0 未通过前不改共享接口或 project-wide policy。
- [ ] D2 运行覆盖完整性的负例与独立复核，重点验证格式通知中的业务附件、业务表/IR 问答、OCR/附件缺口和跨公司用途；只有预注册误删门槛满足才放行。
- [ ] D3 在 D1/D2 通过后生成并冻结逐路径候选清单；D0 的 98,845,393 B SHA 别名差额仍只是基于 catalog hash 的理论候选上限，冻结前需引用/保留审查，D4 执行时对每个精确路径重新完整 SHA。
- **Status:** in progress

## Phase 19：外部来源成本与采购验证（可与 Phase 18 独立推进）

- [x] 核对 FMP、Koyfin、Seeking Alpha、SEC 的官方价格、数据接口与个人订阅使用边界；以现有 FMP key 对四类 endpoint 做只读 MSFT canary，并纠正 SEC 必填日期导致的 400。另对现有 earnings-transcripts 的已提交批量 CLI、未提交精确季度接口及本地 43 份英文文件做只读对照，见[工具与平台对照](earnings_transcripts_vs_platforms_2026-09-27.md)。
- [x] 用实数 246 个本地公司目录做保守 30 日预算，区分纯公开源、Basic、条件性付费新闻稿/日历/电话会方案；写明按日配额、30 日带宽、权益和原文许可的不确定项。
- [ ] 在 G1e 来源接口合同冻结后，取 20 家核实身份的美国证券做 30 日来源覆盖/时效/增量价值试点；以现有 earnings-transcripts 43 份只读库存、SEC/发行人原始披露、FMP 权益状态及用户人工可见的 Koyfin/Seeking Alpha 页面并排记录，但不从两平台复制正文。使用独立 run root，按关键 E2E 计划清理并保存脱敏汇总收据；指标与缺失值规则见[对照卡](earnings_transcripts_vs_platforms_2026-09-27.md)。试点不要求 RF G0 先完成。
- [ ] 只有在上述日志证明付费 endpoint 具有独有、相关、可合法存储的内容且当天权益/合同确认后，才向用户提出具体套餐采购建议；目前维持 $0。
- **Status:** in progress

## Phase 20：数据湖抽象与跨仓责任复核（规划修订）

- [x] 只读核 company-wiki、filing-fetch、revenue-forecast 的来源身份、物理路径、受控读取与工件 DAG；将已修复的 resolver fallback/policy 与仍在的 scanner、normalizer、consumer 路径泄漏区分。
- [x] 沿用 R4 唯一数据湖编排，给 G0/G1c-b/G2 加入位置透明合同、职责边界、试点路径映射退出条件和集中 E2E；记录于[边界复核](data_lake_boundary_review_2026-09-27.md)。本轮只改规划，未运行产品测试或解除暂停。
- **Status:** historical planning snapshot; latest branch/dirty-state rule is Phase 21 below.

## Phase 21：位置透明优先线路与全消费者抽象（2026-09-27，仅规划）

- [x] 将 [R4 优先实施卡](../painpoint-outcome-audit-2026-09-05/r4-data-lake-priority-rollout-2026-09-27.md)设为唯一详细执行路线；本项为并线前规划快照，当前 RF `main=3a69f9c5` 已完成，后续按 A/G0 合同 → B 通用读取真实 E2E → C.local 的 filing-fetch、RF、StockWiki 基础来源 reader；W5 后 G2a 复用 reader 收据并验 selected package。现存隔离 W1–W4 成果保留。
- [x] 明确所有跨仓消费者业务层只接 `SourceRef`/`EvidenceRef`/版本化请求，不拼接或打开 company-wiki/dayu/Dropbox 原文路径；StockWiki v1 路径型 export 仅经限期兼容视图，v2 路径无关合同及历史引用迁移另审。
- [x] 将 B 与 C.local 两个大节点的真实字节 E2E、独立样本、权限/身份/版本反例和测试树恢复映射到现有 L/P/G 收据，不新增逐卡门。
- **Next Step（按最新优先级）：**以 RF `3a69f9c5` 和 CWP 隔离工作树为基线，完成 R4 A 受影响合同与真实原文 oracle 的一次增量审查；随后实施 B 统一读取并在 B.AR 真实多根 E2E 通过后，接 C.local 三仓消费者。叙述 G2a 复用该 reader 收据并增验 selected package；G3 Worker、G4 空间处置各按其大节点顺序实施，不抢跑生产动作。
- **Status:** planning complete; B/C/G2 product results pending.

## Decisions Made

| 决定 | 原因 |
|---|---|
| R4 是唯一虚拟数据湖 owner；本专题只消费其位置透明合同，不另建目录/reader 平台 | 统一 catalog 和部分副本回退已经存在，重复抽象会加重跨仓耦合；新 root 应由 adapter/storage 吸收，RF/StockWiki 不按路径分支 |
| 本计划固定在 `docs/plans/narrative-evidence-pilot-2026-09-26/` | 现有根计划和专项计划都有各自状态；避免改变其入口及活动指针 |
| 试点只读运行，对真实文档做人工标注与轻量统计 | 用户要求先验证方案，且不影响现有任务和生产队列 |
| 再融资样本使用存量 `.PDF` 原文和只读目录查询 | 初次仅搜小写 `.pdf` 漏掉了大写扩展名；其现有 catalog 分类均为 `other` |
| 实施方案另存 `implementation_plan.md` 并保持 planning-only | 完整写清未来代码落点与门禁，同时不改既有 Worker/revenue-forecast 计划 |
| 尚未冻结叙述包 schema/version | 先对照 SourceExportBundle v1、StockWiki Source Provider v1 和 RF 获批合同；pilot v0.2.0 不等于消费者 API；quick-scan 仅测试可选身份映射 |
| Worker 持久状态不依赖 `processing_demand.py` | 该模块纯内存；R4 C05 已指定唯一现有持久 job/attempt 入口。应修复/接入 `automation`，不在 catalog 再建任务队列 |
| 跳过切片与原文处置独立 | 唯一原文一旦删除便不能靠 SHA/URL 保证恢复；旧 SourceManifest v1 不能表示有意删除，须有版本化处置记录与消费合同 |
| 量化业务目标不能被相邻 PDF 片段截断 | 半年报把“超过60%的设备市场”拆成“超”与“过60%…”两个 locator；选择器将两个片段按预算成组保留，草稿引用两者，不能只凭首片摘要数字 |

## Errors Encountered

| 错误 | 次数 | 处置 |
|---|---:|---|
| Windows GBK 控制台无法输出 PDF 中的部分 Unicode 字符 | 1 | 只读脚本输出改用 `json.dumps(ensure_ascii=True)`；不改变源文件 |
| 文件枚举只匹配小写 `.pdf`，漏掉再融资 `.PDF` | 1 | 从只读 catalog 标题查询定位，再按真实扩展名纳入样本 |
| 首次大补丁末尾任务计划匹配行缺少 `- [ ]` 前缀，整次补丁未应用 | 1 | 去除多余 hunk，仅对 findings.md 定向应用，现已成功 |
| 跨仓无界 `rg --files -uu` 遍历隔离运行目录时出现访问拒绝且输出膨胀 | 1 | 改为直接读取已知独立计划路径，不重复全仓搜索 |
| 用 Bash 花括号形式指定多个文件导致 PowerShell 参数解析错误 | 1 | 改为对已知目录限定 `rg -g '*.py'` 查询 |
| 生产 Python SQLite 未编译 `dbstat`，精确表/索引空间查询失败 | 1 | 不外推 1000 行样本；W7 改为先准备经审查的离线工具或副本方法 |
| 文档补丁引用句与实际内容不符，整次补丁未应用 | 2 | 先 `rg` 定位原句，再以更小的精确补丁重试 |
| 验收表把 P09 制度 PDF 误写为 TXT | 1 | 改为 P04/P09 PDF 加 T01 TXT 的三类选择性物化对照 |
| 全库 `COUNT/SUM(locator/raw_text)` 只读扫描长时间占用资源 | 2 | 主动中止，采用明确标为样本的 1000 行估计；精确分解归 S0 离线工具/副本 |
| pytest 默认 Windows basetemp 在本沙箱 `pytest-of-<user>` 创建时报 `WinError 5`（43 passed、1 fixture setup error） | 1 | 指定唯一 basetemp 重跑；路径长度治理器将其移至 `cw-pytest-basetemp`，45 项通过并确认运行目录已清除；后续测试显式给出唯一可写 basetemp |
| 切换夹具的 SQLite 建库连接未显式关闭，Windows 拒绝重命名 | 1 | 修正夹具以 `closing` 关闭连接，并保留生产切换对持续占用句柄的拒绝；夹具重新通过 |

## Scope Boundary

company-wiki 只负责来源、解析质量、证据定位、检索和来源摘要；投资判断与预测留在 StockWiki 和下游。本轮已获授权实施旧库提前退役，明确排除完整备份落盘恢复演练。W/D 各卡仍按各自质量与处置门禁推进。

## Phase 19：company-wiki 本地工作树审查与支线并线（进行中）

- [x] 只读确认远端 `master=f39bd5a`；本地 `master` 当时等于远端且为 `fcap` 祖先。识别并追溯 fcap 本地未提交改动：叙述证据试点、目录退役工具与对应计划/测试，不包含未知的一次性运行载荷。
- [x] 将已审查的 fcap 变更提交为 `7965962`；reader 支线提交 `a3deec2`、transcript 支线提交 `9bc3c31` 已分别通过其本地测试与 hooks，再以 merge commit `7f71708`、`251805c` 合入 fcap。`r4b03-wip`、`r4b06-wip` 原已是 fcap 祖先，无重复合并。
- [x] 解决 transcript 合并中 `canonical_writer.py` 的冲突：保留既有不可变 provenance 校验/重导入语义，同时允许首次 import 写 namespaced transcript provenance extension；43 项 writer/transcript 契约先行通过。
- [x] 修复并复验跨分支契约：reader metadata handoff、reason/stage 注册、source-operation DTO 命名、review receipt 的真实哈希/签名夹具、Windows subprocess 编码；normalized artifact reader 降复杂度后，36 个直接受影响模块共 **390 passed**，Ruff 通过。
- [x] 复杂度新文件阈值仍为 10；只对本轮已纳入且实测超限的模块记录不增长上限。摘要选择器 363、source operation 51、transcript importer 41、provider policy 38、transcript CLI 23、material 19、export CLI 15；这些模块仍须在 G0 生产放行前拆分/降复杂度。Worker/G0 当前关闭，本登记不代表已进入生产。
- [x] 全量 3,108 项测试曾运行到约 40% 后按效率要求停止，不能声称全库通过；当时记录的失败在 390 项受影响回归中转绿。Phase 22 的生产者/消费者复核随后证明 `source_operation` 的 `acquisition_result` 改名使真实 `SourceEnsureResult.acquisition` 断链，因此“全部修复”的旧结论已撤回，须先修该合同再继续 R4。
- [x] 清理本轮创建的 pytest 临时根 `pytest-6997/7002/7003/7004`（精确路径位于 `%TEMP%/pytest-of-郑曾波`，逐根确认无 reparse point 后移除）；E2E 样本/输出测试根由其自身前后快照断言恢复。
- [x] 将剩余回归修复与计划收据提交为 `2ecb6f8`；标准 pre-commit 的 Ruff、config doctor、host assumption guard 全部通过。
- [x] 非沙箱执行 `git fetch origin master` 成功，`FETCH_HEAD` 已刷新；远端 master 仍为 `f39bd5a`，本地 master 已从该提交 fast-forward 到集成提交。当前不 push。
- [x] 复核 `FETCH_HEAD`：文件存在且可写、无只读属性和锁文件，ACL 给当前用户完整权限；之前写入失败与沙箱文件系统拦截一致，不是仓库 ACL 配置错误。
- [x] 将旧 `cw-b06-wt` 工作树恢复到主线：`r4b06-wip` 原有提交已是祖先（无独有提交），工作树仅有 1,645 个 tracked deletions、无 untracked/ignored 文件；重置后 HEAD 为 `2ecb6f8` 且干净。
- [x] reader/transcript 功能 worktree 均干净，其已审阅提交包含于主线；RF 状态仅只读核对，保留其原有未提交工作，本轮未写入或清理 RF。主工作树已切至本地 master；本地变更未推送。

**Status:** 本地分支整合与状态恢复完成；R4 B/C、G0/G1e、Worker、G4 空间退役等产品阶段仍待执行。

## Phase 22：集成测试失败第一性原理审计（2026-09-27）

- [x] 从当前可收集测试、修复前后代码和生产合同三方重建失败，不把过期 `.pytest_cache/lastfailed` 当事实。
- [x] 逐项归类为生产代码缺陷、测试合同/夹具缺陷、Windows 测试环境缺陷或复杂度架构债，并判断影响半径。
- [x] 重跑修复前合同快照（6 failed/53 passed）与当前相关范围（88 passed），并用正式 producer payload 构造现存反例。
- [x] 把证据和结论写入 findings/progress；本阶段没有修改产品实现。R4 继续实施被 `acquisition` DTO 断链阻断。

**Status:** complete；结论为“局部真实合同缺陷 + 测试盲区 + 尚未解决的复杂度债”，先修合同再继续。
