# Progress：叙述性证据试点

## Session: 2026-09-26

### Phase 1：样本与基线

- **Status:** complete
- 已阅读 planning-with-files 技能并检查现有根计划、专项计划及 Git 状态。
- `PLAN_ID`、`PWF_PLAN_ROOT` 未设置，仓库当前没有 `.planning/`；为避免改变默认计划入口，在 `docs/plans/` 新建独立三文件计划。
- 基线 Git 状态：`CLAUDE.md`、`README.md`、`src/company_wiki/source_catalog/artifact_dag.py` 已有修改，均非本试点所作。
- 已登记 10 份 PDF、2 份 TXT；PDF 页数、字节数与 SHA-256 通过 PyMuPDF 和 hashlib 只读计算。只读 SQLite URI：`mode=ro&immutable=1`。
- 再融资两份样本为大写 `.PDF`；在现有 catalog 中均被归为 `other`。

### Phase 2：小范围只读试点

- **Status:** complete
- 逐页抽读 10 PDF、2 TXT；使用 PyMuPDF 页内偏移及 TXT 行号编制 11 张来源摘要正例和 2 张跳过负例，详见 findings.md。
- 对 P03 第 3 页和 P08 第 2 页渲染并视觉核对；截图仅存 Codex 可视化临时目录，未写回项目。
- 对 P04 只读查询现有章节索引：业务与技术一个片段覆盖 83 页、302,779 字符；P05/P06 当前归类 `other`。
- 只读查看 revenue-forecast 独立活动计划的当前状态，不修改或切换其绑定。

### Phase 3：实施方案与跨项目契约

- **Status:** complete
- 新增 `implementation_plan.md`：W0–W7 工作包、文档类型策略、来源/摘要契约、filing-fetch→earnings-transcripts 路由、Worker 状态机、隔离验收与迁移回滚。
- 只读核对 company-wiki 的 Worker stage 白名单、SourceBundle artifact role 白名单、来源导出 v1 结构及 acquisition 市场路由，标明新增 role 不会自动进入消费合同。

### Phase 4：复核与交付

- **Status:** complete
- 重新读取登记表逐文件校验：12/12 样本存在且 SHA-256 前缀吻合；另对 7 处 PDF 锚点与 2 处 TXT 版式锚点重查，9/9 命中。
- 四份新 Markdown 文件 UTF-8 可读，代码围栏配对。现有 `CLAUDE.md`、`README.md`、`artifact_dag.py` 的修改统计与本轮开始时相同；只新增本目录四份文档，未触碰其他计划或生产文件。
- 未验证在线抓取、全语料质量、实际节省的时间/空间；这些已列入实施门禁，未作为本轮成果声称。

## Test Results

| 检查 | 预期 | 观察 | 状态 |
|---|---|---|---|
| 样本基线 | 每类有可定位原文 | 10 PDF + 2 TXT；再融资文件可读 | pass |
| 正负例试点 | 来源摘要可锚到原文且保留限制 | 11 正例、2 跳过负例；页和行可回查 | pass (sample only) |
| 自动质量指标 | 在本轮有全样本标注 | 未进行全篇穷尽标注，召回/精确率未证实 | not tested |
| 样本哈希 | 12 个登记文件与源字节一致 | 12/12 前缀匹配 | pass |
| 证据锚点 | 指定 PDF 页或 TXT 行可回查 | 9/9 复查命中 | pass |
| 计划隔离 | 不改任何已有专项计划/产品文件 | Git 仅新增本目录 4 文件；原有 3 文件修改统计未变 | pass |

## Error Log

| 错误 | 次数 | 处置 |
|---|---:|---|
| GBK 控制台输出特殊字符失败 | 1 | 后续脚本 JSON ASCII 转义输出 |
| 小写扩展名过滤漏掉 `.PDF` | 1 | 只读 catalog 查标题后定位文件 |
| 一次补丁 hunk 匹配失败 | 1 | 缩小目标文件与匹配范围，重新应用成功 |
| 无界跨仓文件枚举遇隔离目录访问拒绝 | 1 | 改读已知计划文件，停止遍历隔离产物 |

## Next Step

本轮交付完成；未来从 `implementation_plan.md` W0 开始，先测契约和基线。

## Session: 2026-09-26（方案细化）

### Phase 5：实施细化与审查设计

- **Status:** complete
- 用户要求进一步细化，并加入审查与测试，让较弱模型也能按步骤实施。
- 已复核本目录四份计划文件及产品现有测试入口；本次仍只修改独立计划目录。
- 新增 `execution_cards.md`：固定 D1–D6 设计选择及停机点，将 W0–W7 写成依赖、步骤、预期结果、负向验证、回退与独立审查卡。
- 新增 `test_acceptance_plan.md`：12 份真实原文的 13 张探索卡、九层至少 36 件盲测留出集、对抗夹具、测试矩阵、指标定义与 W0 冻结门槛。样本总体质量与空间收益仍未测，明确标记 `UNDECIDED`。
- 新增 `review_protocol.md`：每卡 receipt、双层审查、P0–P3 严重性、`accepted_scoped/changes_required/blocked_decision` 裁决、发布与回退门禁。
- 修正 `implementation_plan.md`：默认使用关联旧 v1 的附属只读包，W0 核对真实导出身份/消费者；指出 `processing_demand.py` 纯内存，Worker 持久断点必须另外实现和测试。
- 只读验证 7 份规划文件 UTF-8 可读、相对链接均有效、代码围栏配对；Git 中原有 `CLAUDE.md`、`README.md`、`artifact_dag.py` 修改统计仍为 8/6/4 行，未触碰；只增改本计划目录。一次 `rg` 使用 Bash 式花括号在 PowerShell 中解析失败，改为显式文件列表后成功；不影响文件。
- 未运行产品测试或 Worker，因为本轮只有计划文档变更；未来测试命令及隔离前提已写入测试计划。

## Next Step（未来实施）

先执行 W0：确认真实导出/消费合同、耐重启状态真相源、留出集及基线门槛；通过独立审查后按 W1–W7 逐卡推进。此计划的完成不解除 Worker 暂停，也不允许直接清理生产数据库。

## Session: Worker 并发与丢任务恢复补充

### Phase 6

- **Status:** complete
- 只读核查：`service.py` 对长 normalize/summarize 调用持 `CatalogOperationLock`；`store.py` 为 WAL/`BEGIN IMMEDIATE` 的单写模型；`processing_demand.py` 纯内存；`producer_attempts` 为尝试审计而非任务真相源；`scripts/llm_client.py` 有可变限流/计数状态。现行 Worker 不适合直接多开。
- 新增 `worker_parallel_recovery.md`：R0–R4 分阶段演进，先单执行者完成 durable work key/lease epoch/暂停代际/幂等提交/恢复对账，再让不同文档的解析与模型计算受控并行；复杂高价值文档才按需启用多 agent 核验。
- 将消息/ACK/心跳丢失、旧执行者返回、文件与 DB 双写崩溃、模型超时、SQLite busy/磁盘满、source retired、暂停临界点写成可执行故障矩阵；不承诺远程调用恰好一次，只要求逻辑结果唯一且可恢复。
- 更新总方案 W6、执行卡 D4/W6、测试矩阵与审查清单；保留用户暂停与其他项目计划不变。没有启动 Worker，也没有改产品代码。
- 8 份 Markdown 的 UTF-8、相对链接与代码围栏通过只读检查；Git 中既有 3 个脏文件的差异统计保持 8/6/4 行，只改本独立计划目录。吞吐收益尚未测，明确要求 1/2/4 在途任务对照实验。

## Session: 可实施多文档并发方案

### Phase 7

- **Status:** complete
- 用户指出概念方案不足以实际实施。只读检查现行 Worker v5 冻结计划、R4 C05/C07/D01–D04、`automation` 表/Store/Worker、source-catalog 长操作锁、catalog artifact 唯一约束、Windows 控制与解析进程。
- 关键纠正：R4 C05 已指定唯一现有持久 job/attempt 入口；`automation` 有 jobs/attempts/effects/outbox，但 CLI `status` 实测 `mode=off,status=not_configured,writes_performed=0`。当前 claim 是多事务，完成 attempt 的冲突被忽略，outbox 与 job 完成分开写。此前建议在 catalog 新建任务表不符合 R4；已在本计划所有执行入口改为复用/修复 AUTO。
- 新增 `worker_parallel_execution_plan.md`：N0–N6 交接、source 任务 DAG 与 job key、AutomationStore 原子 API、两个 SQLite/文件的 prepared→verified→visible saga、暂停线性化、Windows 子进程、F01–F16、P1/P2/P2M/P4 吞吐对照和运营回退。旧 `worker_parallel_recovery.md` 改为背景说明并指向新手册。
- 新增本目录 `README.md` 明确权威阅读顺序和 v5/R4 生产门禁；更新 implementation/execution/test/review 文档的 Worker 段。
- 只读运行现有 automation 三组单测：默认 pytest 临时根权限错误导致 9 passed/61 setup errors；指定经过边界验证的隔离 `--basetemp` 后 **70 passed**。这是旧单线程单元基线，不证明并发已可用。
- 未测真实吞吐、远程模型费用或 72 小时运行；均作为 N5/N6 未来门禁，不能写作已验证成果。未改生产代码/数据/其他计划，Worker 保持暂停。
- 最终机械核验：本目录 10 份 Markdown 的相对链接和代码围栏有效；主手册含完整 F01–F16、P1/P2/P2M/P4、N0–N6；全文检索未发现仍要求在 catalog 新建任务队列的执行指令。既有 `CLAUDE.md`/`README.md`/`artifact_dag.py` 修改统计仍为 8/6/4 行，保持原样。

## Session: 第二轮设计审查

### Phase 8

- **Status:** complete
- 发现并修正关键路径矛盾：并发手册曾把旧 `source.normalize` 放在新 DAG 前面；现有 `normalize_catalog` 会写整份 normalized 并重建所有旧 spans。新 DAG 改为从 immutable raw 做轻量 outline，仅可选只读复用已有效的旧 artifact；W2/W3 与测试矩阵同步增加 P04/P09 零全量增量断言。
- 发现并修正跨库竞态：AUTO job `succeeded` 先于 catalog `visible`，若只凭依赖状态会放行下游。下游保持 `PLANNED`，visible/源身份/覆盖账本核验后才升 `READY`；reconciler 补漏升，运行前/提交前再校验。来源退休按现有 JobStatus 合法迁移处理，不直接把 RUNNING 改 CANCELLED。
- 增加 Windows 路径身份、junction/symlink/reparse 检查、同卷暂存与跨卷复制重验的设计，故障矩阵扩为 F01–F20；更新主入口、实施卡、测试与审查。
- 本轮仅修订独立计划文档；未运行新 Worker、未修改产品代码或生产数据。F17–F20 与真实吞吐/空间收益仍待未来实施验证，不能写作已通过。
- 机械复核：本目录 10 份 Markdown 的相对链接/围栏均通过；主手册故障行 F01–F20 连续、无重复，DAG 无 `→ source.normalize`；进入本轮前已有三个脏文件的 diff 统计仍为 8/6/4 行，未碰其内容。

## Session: 第三轮反例审查与小样本验证

### Phase 9

- **Status:** complete
- 只读 PyMuPDF 1.26.7 小试：P08 IR 第 2 页的表格 bbox 占约 71.9% 页面，按现行快照函数的 bbox 排除规则，30 个正文块中 29 个被排除，多个问答进入 1×2 表格单元；P04 第 114 页产品/应用表也包含有用业务描述。P03 同页财务表只占约 1.4%，正文不能整页过滤。五个 PDF 页的 `sort=False/True` 字符长度均不同。由此收紧 W2 双视图、锚点覆盖、多原子锚与 W0 locator 裁决。
- 对生产 SQLite 使用 `mode=ro&immutable=1`、`PRAGMA query_only=ON`，固定 seed 20260926 在 rowid 空间抽取 1000 条旧 span：820 条 table cell、496 条 raw_text 空；平均 `span_json` 812.6 B，raw_text 16.9 B。DB 46.266 GiB，freelist 9 页。当前 Python SQLite 没有 dbstat，不能据样本报全库精确分解或空间节省率。
- 纯内存 SQLite FTS5 反例：`unicode61` 无法命中样本中的“硫化锂”“中试线”；trigram 可命中这两个三字词，但 `MATCH` 无法命中两字“出海”。现有 source_catalog 查询无显式全文 FTS；W5 增加中文短词、英文、时间过滤、按需回源与索引空间/p95 合同。
- C 盘当时空闲约 77.56 GiB，主库约 46.27 GiB；两份等大副本约 92.53 GiB，W7 增加独立存储/最坏空间硬门槛。另补 skip 文档不可读时不得假成功、原文 prompt injection 不可执行、一般公告/新闻/研报后续扩展边界。
- 最后对统计门槛再收紧：原计划每类 4 件、共 36 件只能作为盲测最低集成样本。W0 要预注册每类目标误差、文档聚类置信区间与正式样本量；证据不足为 `insufficient_evidence`，不得把小样本零失败说成可靠召回率。
- 只修改本独立计划目录；未运行产品解析写入/Worker/LLM/联网抓取，未修改生产数据、源码或其他项目计划。当前小试证明存在反例，**不证明**新选择器的质量、吞吐、索引时延或总体空间收益。

## Session: 46 GiB 降容升级方案

### Phase 10

- **Status:** complete
- 只读核对：主库 46.266 GiB、WAL 0 B；目前 sqlite3 CLI/Python 均无 `dbstat`。全库 `COUNT/SUM(locator/raw_text)` 两次扫描耗时较长，主动中止，未改 DB。现有 gzip 归档功能不等于自动 prune 已安全，仍受 Worker v5/R4 H01 门禁约束。
- 以固定 seed 的同一 1000 条 span JSON 做仅内存 zlib 小试：812,588 B 原 JSON，逐行压缩 469,528 B，合并压缩 175,172 B（21.6%）。这只表明冷归档有潜力，未含索引/其他表/查询服务，不能外推“46 GiB→10 GiB”。
- 新建 [space_reduction_upgrade.md](space_reduction_upgrade.md)：S0 精确空间账本→S1 新数据止增→S2 可信冷归档→S3 独立卷紧凑库影子重建→S4 双读切换→S5 保留/回收，逐步验证质量、查询、引用、备份与净总磁盘字节。P01/P03/P04/P08/P09/T01 定为隔离小试范围；80% 派生字节下降仅为预注册挑战目标，非已达成数值。
- 本轮只编辑独立计划目录；未执行 prune、VACUUM、归档、生产 Worker 或项目代码写入。

## Session: 重复字段与空单元降容复核

### Phase 11

- **Status:** complete
- 对只读 immutable SQLite 再抽 1200 条 span（seed 20260927）：`span_json` 均值 815.5 B；7 个通用字段与关系列重复，估算 418,218 B；结构值又复制正文约 18,324 B。可复核分项之和为 436,542 B、约占样本 JSON 44.6%，不是全库可节省比例。
- 部分 table cell 还将正文重复放在 `raw_text` 与结构化值中；空 cell 也有 JSON 元数据壳。计划新增字段单次存储、正文单份保存、空 cell 不建 span、读取适配层及精确全量 S0 账本。
- 反向检查确认不能按文档类型粗暴丢表格：招股书产品/应用表与 IR 问答可能含高价值描述；仅过滤空格和经确认可由 API 供给的标准财务数据，仍需验证召回。
- 更新 `space_reduction_upgrade.md` 和本计划阶段记录；只增改独立计划文档，未改源码、生产库、Worker 或其他计划。
- 数字复核时发现旧记录的 460,942 B / 47.1% 比已列分项多 24,400 B；无可复核依据，已在 findings 和降容方案中撤回，后续需由固定脚本复算。

## Session: 46 GiB 旧 catalog 全量重建审查

### Phase 12

- **Status:** complete
- 只读核对 `config/source_catalog.yaml` 经正式配置加载后的 4 个输入 root 均存在，catalog_dir 指向 `.source_catalog`；另有独立 `source_manifests/`。项目文档确认 raw 输入为只读，normalized/summary、SQLite 和索引写到 `.source_catalog/`。
- 核对 `.source_catalog/` 同时包含 DB、Worker desired state/control/runtime、状态/运行日志、acquisition 与 cleanup 审计、security master、staging、derived 和 export/index。全删会损失运维/历史信息并可能破坏 Worker paused 状态；旧扫描约定对消失路径保留 `missing` 状态，空库不能复原已消失的来源历史。
- 评估结论：用**新格式在隔离 catalog_dir 从只读 raw 重建，再双读/消费核对后替换旧派生库**可能更清晰；先删再旧流程重跑会重建全量 normalized/spans，不能治本。新方案、R0–R5门禁、回滚和容量风险写入 `space_reduction_upgrade.md`。
- 重新确认 C 盘此前余量约 77.56 GiB；保留旧 DB 影子重建时给新库/临时/WAL/索引约 31.3 GiB，峰值未测。未运行 scan/Worker，未删除或复制数据库，未改配置、源码、raw 或其他项目计划。

## Session: 提前退役旧主库的快路径验证

### Phase 13

- **Status:** complete
- 生产库只读元数据：49,677,344,768 B、WAL 0、17 张非 evidence_spans 表共 189,580 行；sources 43,112、documents 23,530、locations 46,606、artifacts 8,191。active 文档 13,839、retired 9,501。通过 `idx_documents_status_kind` + `idx_spans_document` 精确计数 active 旧 span 为 1,490,530（约 8.75 秒）。
- 系统临时目录两次原 DDL/数据/索引复制试验：目录表独立库 225,280,000 B（214.84 MiB）；目录+全部 active span 库 3,059,200,000 B（2.849 GiB，1,680,110 行，耗时约 143 秒）。均 `foreign_key_check` 无错误、`quick_check=ok`，临时目录自动清理；只证明大小和关系完整性，未通过实际服务/下游差分。
- 发现 `source_manifests/archive/2026-08-07/retired-evidence.jsonl.gz` 为 5,207,478,767 B、首条可解析为旧 span；ADR-009 记载 25,708,956 条退休证据归档，H01 独立复核指出校验与不可覆盖发布缺口，因此不能把它当唯一可恢复备份。`derived` 约 2.83 GB、`index` 约 45 MB，另行管理。
- zstd level 3 对 6 处各 8 MiB 旧 DB 的只读试压比例 12.2%–32.1%；完整快照大小未知。当前 C 盘空闲约 85,079,416,832 B（79.24 GiB）。StockWiki 当前 company-wiki provider disabled；revenue-forecast 使用 filing-fetch/source 目录链，真实合同仍列 F3 核对。
- 新增 `early_catalog_retirement.md`：推荐在完整可恢复压缩备份前提下，以 2.849 GiB 活跃子集替换主文件，先保住 active 旧查询；retired 查询必须明确归档不可用或冷读，不能伪报 not found。F0–F3 可独立准备，F4/F5 分别审生产切换和按确切路径清理；预计本机净节省依完整压缩文件实际大小计算。
- 同步总方案、执行卡、测试和审查门禁，未改生产 DB/源文件/Worker/配置/代码或其他活动计划。此次用户请求仍是方案讨论，没有执行旧文件删除。
- 最终 Git 状态另出现 `src/company_wiki/source_catalog/dayu_cli_adapter.py` 的未提交修改（121+/7−），本轮没有编辑该文件，也未据此改写计划外代码；此前已有 `CLAUDE.md`、根 `README.md`、`artifact_dag.py` 脏改动保持原有统计。此项属于并行工作区状态，实施 F 卡前要重新识别所有现存改动。

## Session: 新仓库与逐文档清理方案

### Phase 14

- **Status:** complete
- 只读 `PRAGMA` 确认生产 SQLite `auto_vacuum=0`、`journal_mode=delete`、freelist 9 页。逐来源删除其中的 span 行不会逐来源缩小 46.266 GiB 主文件；主文件仍需受控影子库切换与整文件退役。
- 明确可逐件核验和清理的是旧 derived（总计约 2.83 GB）及成功迁移后旧位置的 raw 重复副本；唯一 raw、source manifest、仍被消费者引用的产物不可删。5.21 GB 退休 gzip 为整包，另行审查。
- 在 `early_catalog_retirement.md` 增加可选新 Git 代码仓与优先的同项目隔离 v2 数据根，并规定逐件 raw 迁移的 hash、可读性、映射、消费者切换、回滚和精确路径清理门禁。新 Git 仓本身不会减少储存，迁移期复制原文会增加峰值占用。
- 本轮仅更新独立规划文档；未创建新仓、写生产数据、迁移或删除任何文件，Worker 保持暂停。

## Session: 不重要来源也回收旧原文

### Phase 15

- **Status:** complete
- 只读核查 `SourceManifest v1`：原路径、SHA、大小绑定，`verify_file()` 要求文件仍存在；`immutable_status` 只有 verified/quarantined，不能描述按政策处置。现有业务 `skipped_*` 只是不生成切片，不能直接触发 raw 删除。
- catalog 只读 `locations` 分组显示 `company_raw` 的 original_primary active 7,524 件、observed_size 6,511,169,498 B；retired 9,046 件、18,641,858,464 B。这些是历史观察大小，不是当前物理占用或可删除量；`retired` 不等于低价值。Dropbox/dayu 是外部只读输入，不能纳入本项目删除动作。
- 新建 `raw_disposition_plan.md`：把内容选择与原文处置分开，允许对经完整覆盖和独立复审的唯一低价值来源逐件删除原文，或先清理同 SHA 重复副本；保留轻量历史身份、版本化处置状态和精确路径删除 receipt。加入来源/旧 span/下游引用、错误缺失、崩溃重放和真实同卷字节门禁。
- 同步入口、总实施、空间、旧库退役、执行卡、测试、审查和并发 Worker 手册。D0–D3 可只读准备，D4 与 F0–F5 的共享 SQLite 整文件退役分别审查；Worker 只提出候选，不并发删文件。本轮没有改生产代码/数据、启动 Worker、创建新仓或实际删除文件。

## Session: 分步骤空间增减账

### Phase 16

- **Status:** complete
- 只读 stat 统计：`.source_catalog/` 52,700,659,299 B（49.081 GiB），`source_manifests/` 5,207,479,410 B（4.850 GiB），`companies/` 25,173,861,091 B（23.445 GiB，33,129 文件）；三处合计 83,081,999,800 B（77.376 GiB）。公司 `raw/` 中 PDF 15,129 件、25,073,770,125 B（23.352 GiB），其可删除比例未知。
- 当前未变化的 49,677,344,768 B 旧 DB 只读 `zstd -3 --stdout` 流计数为 6,198,704,362 B（5.773 GiB，约 96 秒）；输出流只被计字节，**没有**保存备份或做恢复试验。之前 2.849 GiB 活跃临时库实测可用于预算，非生产交付。
- 若正式快照相同且留 C 盘，F1 +2.849 GiB、F2 +5.773 GiB、完整恢复临时再 +46.266 GiB（峰值较现状 +54.888 GiB），F5 删除原主库 −46.266 GiB，累计净释放 37.644 GiB。当前 C 空闲 79.217 GiB，理论峰值剩余 24.329 GiB，未含 WAL/其它进程和安全缓冲。
- 新产物/检索索引大小未知；旧 derived 最多 2.632 GiB 可审查回收，唯一低价值 raw 需 D0 逐件测。两份已知负例仅 262,925 B，不能外推。现有 4.850 GiB 退休归档与完整备份暂保留。空间账写在 `stepwise_space_budget.md`，只更新独立规划文档，未执行生产迁移、清理或 Worker。

## Session: 用户取消完整恢复演练并授权实施

### Phase 17（进行中）

- 用户明确要求不进行完整落盘恢复备份演练，其他步骤可实施。已把 F2 改为正式快照 SHA、`zstd -t`、完整解压流 SHA/长度与原库相同，并明列未来实际落盘恢复未演练的剩余风险；同盘峰值预算由 54.888 GiB 降为 8.622 GiB。新建 `implementation_run_2026-09-26.md` 作为本轮 I0–I6 执行卡。
- 产品代码新增 `EvidenceQueryArchivedError`，active-only catalog 中非 active 来源缺失旧 span 时明确返回 `legacy_evidence_archived`，旧完整库行为保持；CLI error taxonomy 版本 1.1 标该错误不可重试。相关证据/错误合同测试 27 passed。
- 新增 `scripts/retire_source_catalog_db.py`：只读原库、复制全部非 span 数据/active 旧 span/索引/触发器，逐表摘要、FK/quick_check，生成 zstd 快照并流式重验；不做切换/删除。临时库测试补触发器、Worker pause、零 WAL 可接受/非零 WAL 拒绝，3 passed；合并相关测试 29 passed。
- 生产预检仍为 `worker_control.paused`、主库 49,677,344,768 B、`operation.lock` 不存在、C 空闲约 85,025,054,720 B；现有 `-wal` 文件为 0 B、`-shm` 32,768 B（最近读连接留下），工具允许零 WAL 且每阶段重验，非零 WAL 阻断。`Get-CimInstance Win32_Process` 被访问拒绝，因此不能凭进程清单证明无其他 writer；用操作锁、源 hash/stat/WAL 前后重验补强。
- 尚未运行生产影子库/正式备份、切换或删除；下一步 F0/F1/F2 准备阶段，Worker 仍暂停。
- **随后执行更新（2026-09-26 17:08–17:55 UTC）**：生产 `run_id=20260926T170825Z-4a9c67e1` 的准备进程已启动，持有 `operation.lock`；F0 的完整源库 SHA 与只读 `quick_check` 通过，约 17:40 UTC 进入 F1。候选 `catalog.active.sqlite3.partial` 已到 3,055,796,224 B，正在逐表摘要/质量校验；尚无 `prepared.json`，F2 未开始，原主库仍为 49,677,344,768 B、旧 mtime 不变、WAL 0 B，Worker 仍 paused。**不得另启第二份准备进程。**
- 补充 `audit_catalog_retirement.py`（active 原文/页查询差分、retired 显式归档、同 SHA+locator 活跃碰撞识别）、`audit_catalog_consumers.py`（只读 metadata query/SourceResolver 配对差分、StockWiki provider disabled 检查）及 `cutover_source_catalog_db.py`（意图收据、精确旧库/侧文件 rename、切回、两次烟测、精确删除/中断续清理）。工具只在各阶段对应收据存在且 hash 相同时前进，未对生产执行切换/删除。
- Windows 临时夹具第一次 cutover 因测试建库连接未显式关闭遭 WinError 32；修复夹具后切换/切回通过。随后补充烟测间隔、精确旧文件删除和重命名中断后反向恢复测试，6 passed；先前查询/错误/迁移合并测试 31 passed。该失败证明生产若仍有占用句柄会拒绝切换，不能把重命名错误当成功。
- 只读按 `documents.primary_source_id` 分组核查，当前同时挂 active 与 non-active 文档的 source ID 数为 **0**；这是来源级查询截断风险的初筛，不代表所有 `evidence_spans.source_id` 完全无交叉。F3 仍要核实际 span locator 碰撞与来源查询行为。
- 增补消费依赖快照 SHA、精确侧文件白名单、Worker 二次检查和切换中断夹具后，合并测试重新运行 **33 passed**；`git diff --check` 无空白错误（仅已有文件行尾规范警告）。F1 此时仍运行，没有把夹具通过误记为生产验收。
- 约 18:20 UTC 只读 Win32 进程计数显示准备进程从 F0 起累计约 235 GB read transfer、约 14.98 GB write transfer；这些是进程 I/O 计数（含缓存/重复读），不是新增磁盘占用或 F1 单阶段数据量。可见旧 SQLite 的完整校验具有明显读放大；后续 W7 性能合同需按实际 read bytes/墙钟记录。
- 约 18:22 UTC 准备进程打印 `F2 compress and verify full decompression stream`，表示 F1 的逐表行数/字段摘要、活跃 span、外键与影子库 `quick_check` 已通过；候选实际文件暂为 3,055,796,224 B（尚为 `.partial`），旧库未切换。F2 压缩、`zstd -t`、完整流 SHA 与最终 `prepared.json` 尚在执行中，不能提前判为完成。
- 18:30:01 UTC 正式 `prepared.json` 发布：旧库 49,677,344,768 B / SHA `69f498a2…`，active-only 候选 3,055,796,224 B / SHA `63c359aa…`，完整 zstd 6,198,704,362 B / SHA `1bc09746…`；完整解压流 49,677,344,768 B / SHA `69f498a2…` 与源相同，`zstd -t=ok`、FK/quick_check=ok，active span 1,490,530 行摘要一致。备份无完整落盘恢复演练（用户排除），生产 DB 未切换、旧 DB 未删除。
- F3 真实证据差分 `evidence_audit.json` 已发布 `passed`：31 个 active 样本查询一致、25 个 retired 与 5 个其他非活跃样本均按预期归档失败关闭；源 ID 混用 0、样本 locator 碰撞 0。此收据明确 `consumer_contracts_checked=false`，不能单独允许 F4；消费端审计正在运行。
- 用户询问与 revenue-forecast 三项目在飞计划是否冲突。只读检查其 Round 117 与 I-11-B/I-05-C/I-06-A：当前 I-11-B 主体不碰本轮 SQLite，I-05-C 未来将改 CW DAG/service/processing_demand，I-06-A 可能落 store 持久需求；未来 W0/W6 必须复用正式合同。本轮新增 `cross_project_coordination_2026-09-26.md`，F4/F5 固定 14 个 CW 源码+生产配置及三项消费入口 SHA，变化则停。
- F3 消费者审计第一次因审计脚本误把 `fiscal_year` 当作文档主表列而失败；核真实 schema 后改从已核验的 `source_metadata_assertions` 抽样，确认临时 hardlink 清理，再重跑通过。`consumer_audit.json` 记录 6 组 metadata query、12 组无下载 resolve 均与旧库相同（reused_equivalent 2、missing 4、ambiguous 6）；StockWiki 的 company-wiki provider 仍 disabled。该审计未跑真实下游业务流程，收据如实标 `downstream_live_business_run_performed=false`。
- 预切换夹具改用仓库内 `--basetemp=.pytest_retirement` 避开受限系统 TEMP，相关 33 项通过；`git diff --check` 无空白错误。核了运行目录、三个精确文件、Worker paused、WAL 空、operation.lock 不存在。18:47:45 UTC F4 `cutover.json` 成功：3,055,796,224 B 的 active-only 候选成为生产 `catalog.sqlite3`，49,677,344,768 B 原库改名 `catalog.sqlite3.retiring.<run_id>` 并保留回滚，压缩备份仍在；尚未释放旧库空间。
- 18:52:17 UTC 第一轮 `smoke_1.json` 通过：生产/旧库/备份 SHA 与准备收据相同，active span 1,490,530，FK/quick_check=ok，真实 active EvidenceSpan 查询返回预期文档。随后生产只读 CLI `status` 返回 documents 23,530、sources 43,112、evidence_spans 1,490,530；`query` 和 `resolve --entity 微软 --document-kind annual_report --fiscal-year 2025` 正常返回（该 resolve 为 `missing`，原因是已有 Microsoft 10-K FY2025 capture_incomplete，与 F3 旧/候选差分一致）。F5 前仍需间隔至少 10 分钟的第二轮烟测及再次合同 SHA 核对。
- 19:03:16 UTC 第二轮 `smoke_2.json` 通过，距首轮 **658.450 秒**，三文件 SHA、FK/quick_check、active span 数和样本证据一致；18 个本仓/跨仓合同文件 SHA 未变化。附加的生产退休证据取样 SQL 因旧库扫描慢而主动停止；正式 F3 已对 25 个 retired 样本验证 `legacy_evidence_archived`，没有将附加尝试计为通过。
- 19:06:54 UTC `retired.json` 发布：精确旧文件 49,677,344,768 B 和记录的零 WAL/SHM 已删除；3,055,796,224 B 新主库及 6,198,704,362 B 完整备份仍在，Worker paused、无 operation.lock。清理前同卷空闲 75,756,457,984 B，清理后 125,431,902,208 B；准备前 85,026,582,528 B，故整轮实际净增 **40,405,319,680 B = 37.630 GiB**。理论文件净减少 40,422,844,182 B = 37.647 GiB；差额不能据此归因。用户排除的完整落盘恢复未做，真实下游业务流程未跑。

## Session: 用户要求减少重复审查和测试

### Phase 18（计划节奏修订）

- 用户指出逐小节点复核过多且拖慢进度。审查确认旧方案中 W/N/D 每卡独立签收、每次保存全套 hash、F 路径反复哈希 46 GB、Worker F01–F20 各 10 次和额外 72 小时 soak 属于重复成本。本轮 F5 已在执行中，未中途改动其删除门禁。
- 新建 `milestone_review_cadence.md`，将后续审查合并为 G0 合同、G1 W1–W4 集成小试、G2 检索消费、G3 Worker 受控发布、G4 物理迁移/删除批次。普通代码修改只跑相关测试与轻量自检；大库完整校验只在准备/不可逆切换执行，重复观察烟测可用轻量状态/读取；原文真正删除前仍逐文件只做一次完整 SHA。输入改变只重开受影响节点。
- 同步 `execution_cards.md`、`review_protocol.md`、`test_acceptance_plan.md`、`worker_parallel_execution_plan.md`、`raw_disposition_plan.md` 与入口 README。Worker 保留 20 个故障模式各一次确定性注入，对竞态点做 3 次真进程复验及一次至少 100 job 的有界混合负载；不再加本专题 72 小时隔离 soak，外部 v5/R4 的正式门禁仍服从或复用其收据。物理删除人审按批次，逐文件技术身份核查不省。

## Session: G1 隔离试点继续实施（2026-09-26）

- 将锚点检查从“整页/整角色文字含词”收紧为“最小连续选中 span 窗口含词”；报告新增 `matched_evidence_ids` 与 `match_scope`。若选中页面包含该词但无精确证据窗口，摘要验证器失败关闭，不把上下文页当引用。
- 全量最终复跑 v7（10 PDF + 2 TXT）：13/13 个目标锚点均映射到精确 span，837/837 个选中定位回读成功，0 锚点失败、0 blocked；6 PDF 为 `partial`（部分表格页延迟扫描/覆盖预算），2 份 IR 为 `needs_review`（表格 locator 不稳定），2 个负例跳过，2 个电话会 TXT 入选。52,196,853 B 原文产生 347,809 B 选择证据 JSON（0.666%）；这是模型输入候选量指标，不能当作持久 DB 增量、最终摘要大小或总体召回率。
- 新增 13 条人工来源摘要草稿（含 P06 两条分别表达项目认证与建设理由，并把 P08 投资者“低于 5%”问题与管理层“超过 25%”回答拆开）。13/13 通过已选 evidence ID、来源哈希、语言及发言角色的机械校验；T01/T02 摘要使用英文原语言；P08 答复关系还通过同一 `qa_group_id` 校验。每条均为 `needs_review`。语义蕴含、限定词及独立审读还未验收；未调用 LLM/API、未连接 catalog/export、未新增生产 DB/Worker 写入。
- 代码与产物：`narrative_evidence.py` 增加精确 span 锚点映射所需的试点计算；`scripts/narrative_evidence_pilot.py` 输出 v7 全样本收据；`scripts/narrative_summary_review_pilot.py` 和 13 条 claim spec 生成带引用定位的离线草稿验证报告 v4；两个相关单测文件覆盖精确/拆分锚点、页级匹配拒绝、发言角色错误、同组问题—答复引用关系、源语言门及 needs_review 状态。
- 验证：`ruff check` 通过；`tests/unit/test_narrative_evidence.py` + `tests/unit/test_narrative_summary_review_pilot.py` 共 32 passed；全量只读样本脚本 exit 0；摘要验证器报告 `citation_and_role_checks_passed`（10 个来源、13 条 claim）。分类实测将 P05/P06 分别识别为可转债/定增募集说明书，P09/P10 分别跳过为 IR 制度/会议通知。一次锚点拆分测试初次失败，定位为算法对较长片段提前截断；移除错误上限后重跑通过。P08 首版把问答合成一条虽机械通过但来源角色不完整，已拆分并以 v7 重跑修正；T01/T02 首版摘要为中文，已改为英文并加入语言门。
- 跨项目保护：只读刷新 revenue-forecast 至 Round 120。其 `task_plan.md` 顶部仍是 Round 98；Round 120 progress/§150 register 未给 I-05-C/I-06-A 可复用的最终字段及 owner 决定。I-05-C 卡片状态仍写 planned，登记记录又载明 `accepted_scoped` 与两项外部授权欠账；I-06-A 的 D-W06 持久 owner/schema/API 冻结仍是阻断。未修改 revenue-forecast、StockWiki、invest-quick-scan 或 company-wiki 共享 DAG/service/store/producer/Worker；Worker 仍暂停。
- **当前阶段判断：G1 的选择、精确定位及引用/角色机械验证子阶段通过；G1 整体未完成。** 尚缺摘要语义限定词复核、分类/来源接入路径、逐件持久字节测量及留出集；G0 维持等待权威跨项目合同，G2–G4 未开始。

## Session: G1 量化目标补选与阶段收口（2026-09-27）

- 逐条核对 13 条摘要草稿和对应原件。发现半年报 P02 p.21 将“超过60%的设备市场”拆在相邻 locator；旧候选 JSON 只含第一片，故将精确目标加入锚点后，首轮失败 1 锚点并保留该失败收据，没有按不完整引用放行摘要。
- 在隔离选择器中新增“量化市场覆盖目标”成组规则，按最小连续片段保留两段原 locator，并在原硬预算内优先于普通事件；增加回归测试，竞争预算仅 2 span 时仍完整保留两个目标片段、数字锚点可精确映射。没有增加任意文档的预算。
- 主样本 v16 exit 0：12 件、原文 52,196,853 B、1,289 spans、1,289/1,289 roundtrip、18/18 锚点、0 roundtrip/anchor failure、0 blocked、0 超上限；状态为 2 selected、6 partial、2 skipped、2 needs_review。选择证据 JSON 为 542,820 B（1.0399%）。
- 固定回归集 v11 exit 0：4 件、14,939,109 B、401/401 roundtrip、5/5 锚点、0 failure/超上限；选择证据 JSON 为 202,661 B（1.3566%）。它是 regression set，不称为盲留出集。
- 摘要校验 v8 为 10 sources、13 claims，`citation_and_role_checks_passed`；新增 [g1_summary_source_support_audit_v1.md](g1_summary_source_support_audit_v1.md) 记录原文是否支持、计划/时点/角色边界和 locator 风险。实施者来源核对不是独立审稿，机器字段仍明确 `semantic_review=not_performed`，13 条均 `needs_review`。
- 验证：相关两个测试文件 **44 passed**；`ruff check` 通过；v16/v11/v8 JSON 解析通过。每个样本测得的临时 fsync JSON 字节等于序列化字节，且 selection 未超过硬上限。该测量不包含 catalog/DB/索引/生产封装，不是持久空间差量。
- 跨项目只读重核到 revenue-forecast progress Round 120、register §161、owner decisions §38 和当前 attempt：I-05-C 盘上 `accepted_scoped` 但仍有真实 producer、`consumer_analysis` owner/入口及 InvocationTracker schema 开放项；I-06-A 最新 `accepted_scoped` 只覆盖 store-side lifecycle，caller/CLI、跨进程、I-06-B consumption face 等仍在 carried-open，生产晋升需 owner commit。已更正[协调记录](cross_project_coordination_2026-09-26.md)，不再沿用“整个 D-W06 owner/schema 都未决定”的旧说法。
- 本轮未修改 revenue-forecast、StockWiki、invest-quick-scan 或 company-wiki 共享 DAG/store/service/producer/processing_demand/Worker；未调用 LLM/API、未连接 catalog writer、未删任何 raw/derived 文件。复读 `.source_catalog/worker_control.json`，desired state 仍为 `paused`。
- **阶段结论：**G1 的离线选择/定位、引用角色校验、实施者来源支持审查和候选 JSON 字节量测完成；独立审稿、来源扫描器/目录接入、真实持久差量均未完成，仍属于 G1 集成部分，须先通过 G0。G2–G4 继续待门禁。旧主库退役 F0–F5 的 37.630 GiB 实测释放收据不变。

## Session: D0 当前文件元数据盘点（2026-09-27）

- 以 immutable read-only SQLite 和逐路径 `stat` 检查 29,409 条登记原文位置；全量元数据遍历耗时约 94 秒。除 catalog 原已标 `missing` 的 3 条外，路径均存在且实际大小与登记一致；未读正文、未算新 SHA，未写生产库。
- 自有目录实测：`companies/` 33,131 文件 / 25,189,914,642 B；`source_manifests/` 2 文件 / 5,207,479,410 B；`derived/` 7,104 文件 / 2,826,010,634 B；`index/` 8 文件 / 45,052,670 B。登记 artifact 8,191 行归并为 6,714 唯一路径、2,794,944,096 B；620 条唯一路径存在历史 byte_size 冲突。
- `.source_catalog/` 全目录 8,214 个文件 / 12,277,797,132 B；`retirement/` 占 6,198,717,464 B，active-only 主库 3,055,796,224 B。三个本地数据目录合计 42,675,191,184 B（39.744 GiB），较 F5 前逻辑长度少 37.632 GiB；以 F5 同卷实际净增 37.630 GiB 为物理空间结论。
- 最近 5 个 company 文件（16,120,320 B）是紫金矿业 2023 年报 PDF+sidecar 和 Microsoft 两个 8-K HTML+sidecar，与 revenue-forecast 正在使用的资料吻合。逐路径查询确认 5 个都未登记到 catalog locations；保持 `hold`，不启动 scan/normalize，也不进入删除/迁移候选。
- 本地 source SHA 只显示 52 组双路径别名，理论重复差额为 98,845,393 B；仍是候选上限，不是可删量。D0 收据与边界见 [D0 inventory receipt](d0_inventory_receipt_2026-09-27.md)。
- 本地引用映射补充：1,490,530 条当前 evidence span 对应 1,636 个 source ID；1 个 ID 无登记原文 location，329 个 ID 有跨 root location，未发现 span 只挂在 retired location 上。8,191 条 artifact 记录均有 source/document ID；643 B SourceManifest 可关联到已登记原文。5.207 GB retired-span gzip 只核路径和长度，未打开内容。
- D0 本地文件及引用盘点完成；跨仓 consumer 的处置响应必须由 G0/D1 owner 合同规定，不用本地盘点推断可删除。未改 revenue-forecast、StockWiki、invest-quick-scan 或共享 catalog/Worker；Worker desired state 仍 paused。G0 依然关闭。

## Session: G1–G4 端到端测试隔离计划补充（2026-09-27）

- 按用户要求，将 E2E 放在现有 G1 来源到证据包、G2 检索/消费者、G3 Worker 真子进程与恢复、G4 scratch 原文处置等大节点；日常小修改仍只运行受影响测试。
- 新增 `end_to_end_test_plan.md`：规定 fixture 只读、每次唯一 `.runtime/<run-id>`、样本先复制并核 SHA、所有 DB/WAL/cache/log/lock/download/output 限定于 run root、`finally` 与崩溃后的 cleanup/resume、前后测试树清单一致性和失败关闭。真实 transcript canary 需来源许可/授权和副作用隔离证明；当前默认 fake provider。
- 更新 `README.md`、`implementation_plan.md`、`execution_cards.md`、`milestone_review_cadence.md`、`test_acceptance_plan.md` 和 `task_plan.md` 将目录恢复纳入 G1–G4 收据。测试目录中原本不存在的下载文件及其派生产物必须删除；不能证明清理或发现外部写入则门禁失败。未运行 E2E、未下载、未改代码、未改生产或其他项目数据；G0 仍关闭、Worker 仍 paused。

## Session: G1 隔离 CLI 与真实样本 smoke E2E（2026-09-27）

- 为 `scripts/narrative_evidence_pilot.py` 和 `scripts/narrative_summary_review_pilot.py` 增加 `--run-root`：隔离模式要求 manifest/样本/metrics/claims/output 均在同一 run root；evidence JSON 的 fsynced 临时文件也写入 run root 的 `state/measure_tmp`。默认旧计划运行仍保持原目录约束。越界输入/输出失败关闭。
- 新增 `tests/e2e/test_narrative_g1_pipeline.py`，以真实 P06 定增说明书与 T02 英文电话会议**副本**端到端运行两个 CLI。校验两件文档、所有定位回读/锚点、summary-input 序列化长度、3 条引用/角色摘要仍为 `needs_review`、英文原文无翻译副本、测量临时目录为空，以及越界写出被拒绝。
- 验证：`ruff check` 通过；目标单元测试 + 新 E2E **45 passed in 5.32s**。E2E 在唯一 pytest temp tree 中完成，测试函数比较运行前后 tree manifest 并在 `finally` 删除 run root；pytest basetemp 插件回报运行目录已清除，随后 `Test-Path` 复核唯一指定/实际 basetemp 均不存在。未写生产公司目录、catalog、计划产物或 revenue-forecast；没有网络、LLM、provider、Worker 或 export。
- 环境错误与处置：首次默认 pytest basetemp 在 `pytest-of-<user>` 遇到 WinError 5，导致 43 passed/1 fixture setup error。显式指定一次性 basetemp 后治理器将其迁到短路径 `cw-pytest-basetemp`，完整 45 项通过且临时目录清理成功；已录入 `task_plan.md` 错误表，后续使用唯一显式 basetemp。
- 范围声明：这是 G1 隔离本地 smoke，不替代 G0 后的 12 件/13 卡集成门禁，也不验证 filing-fetch 实际 transcript 获取、持久 catalog 增量或下游 consumer。G0 未通过，Worker 继续 paused。

## Session: Transcript acquisition E2E 边界细化（2026-09-27）

- 复核确认计划已有 D5/W1 transcript 接入卡和 C12 fake provider 合同测试；但当前已通过的 P06/T02 smoke 只处理本地 TXT，不覆盖 filing-fetch 到 earnings-transcripts 获取、company-wiki 暂存落盘、摘要 package 的整条链路。
- 在 `end_to_end_test_plan.md` 中新增 G1 transcript acquisition-to-summary E2E 的明确入口、三条路径（授权未命中、已有来源复用、transcript 失败但 filing 成功）、断言及其与 C12 contract test 的职责区分；在 `test_acceptance_plan.md` 与 `task_plan.md` 增加待办 G1e 和测试入口 `tests/e2e/test_filing_fetch_transcript_pipeline.py`。
- 该 E2E 必须等 G0 的 filing-fetch consumer/adapter 合同冻结后才实施；全部用 fake provider 和唯一 run root，不启动共享配置 earnings-transcripts CLI、不联网。可选 live canary 不是门禁条件，需另行许可并证明配置/cache/log/lock/output 均隔离。
- 当前仅修改计划文档，尚未实现 adapter 或测试；既有 45 项 smoke 通过不代表 acquisition E2E 已覆盖。未改 production catalog、真实原文、Worker 或其他项目。

## Session: selected-evidence 检索隔离 prototype（2026-09-27）

- Revenue-forecast 前置重核：当前可见 `progress.md` Round 120、`REMEDIATION_REGISTER.md` §161、`OWNER_DECISIONS.md` §39。I-05-C 虽盘上 `accepted_scoped`，真实 producer 尚未实现，`consumer_analysis` owner/入口与 InvocationTracker 事件 schema 仍开放；I-06-A 最新 `accepted_scoped` 的 reviewer scope 只含 store-side lifecycle，review lines 183/203 明列 I-06-B consumption/CLI、RF wiring 和 cross-process concurrency 为 carried-open。G0 仍关闭；只读查看，未修改 revenue-forecast。
- CodeGraph 与源码复核：canonical `EvidenceQueryService` 只有精确 `lookup(source_id, locator)` 与按 source/document `list_spans`；`SectionQueryService` 只列 sections；legacy `scripts/search.py` 搜索 Wiki 页面，不会搜索新 selected package。若新 spans 不落 `evidence_spans`，后续需单独冻结 package-backed locator resolve，现有 lookup 不能替代。
- 新增 `src/company_wiki/source_catalog/narrative_retrieval.py`：版本化 selected-evidence bundle 的 query-local 内存 BM25，中文 CJK bigram + 英文/数字 token，结果含 source/hash、package status/coverage、evidence IDs/locators；不建持久索引、不读写 catalog、不处理 full-document 或 summary claims。`needs_review` 命中保留状态，`blocked` 与 `skipped_no_narrative` 不索引。
- `narrative_evidence_pilot.py` 增加仅隔离模式可用的 `--package-output`，强制落在 `--run-root/outputs/`；扩展 P06 定增说明书 + T02 英文电话会 E2E：从实际 selected package 查询中文业务词和英文原句，核对源 hash 与证据 ID/locator 集合，断言 package 字节小于两份 raw 合计并拒绝越界输出。测试不连接生产 catalog 或写任何持久文件。
- 验证：该次运行结果现已由 12 件样本检索回归补充（详见下一 session）；本记录原先的 **8 passed in 5.96s** 是当时两份样本 smoke + 7 个检索单测的历史收据，保留以避免改写历史。
- 计划同步到 `task_plan.md`、`implementation_plan.md`、`test_acceptance_plan.md`、`end_to_end_test_plan.md`、`findings.md`、`cross_project_coordination_2026-09-26.md` 与 `README.md`。G2a 仅登记为隔离检索预研，不宣称 G2 通过；transcript acquisition E2E 仍等待 G0 adapter/consumer 合同。
- 命令/操作错误记录：一次 PowerShell `rg` 使用了不兼容的 brace 路径展开，另一次 RF 手工收据读取漏写 `.planning/...` 前缀；两次均为只读命令且未改状态，改用 PowerShell 数组路径和正确 attempt 路径后取到结果。第一次脚本补丁因上下文不匹配未应用；拆分补丁后成功，未覆盖其他改动。

## Session: 12 件样本 selected-evidence 检索 E2E（2026-09-27）

- 在唯一 pytest basetemp 中复制 12 件 G1 pilot manifest 样本（10 PDF、2 TXT），运行隔离选择/package 流程后，对 metrics 中每个已选 span anchor 通过 package 检索；逐项断言 source ID、evidence ID、locator 与 bundle 一致。还断言 12 件的 locator/anchor failures 均为 0、package 小于样本 raw 总字节、source SHA 与复制件一致、`state/measure_tmp` 为空。
- 同轮验证 retrieval 单测 7 项、原 P06/T02 检索 E2E 1 项和本 12 件回归 E2E 1 项：**9 passed in 72.32s**；`ruff check` 通过。
- 清理检查：pytest governance 将长路径 basetemp 迁到唯一 `%TEMP%\\cw-pytest-basetemp\\20260927-023838-e1bf5d44` 并报告已删除；逐路径确认该 basetemp 不存在，`tests/e2e/.runtime/` 在测试前不存在且测试后仍不存在，测试函数的 run tree 也通过 finally 恢复。没有保留样本副本、package、metrics 或临时数据库。
- 该测试验证的是当前 pilot manifest 已选锚点的内部可检索性与身份/定位链，不测未选内容召回率、语义质量、p95、package-backed 原文二次读取、生产 API/catalog、真实 transcript acquisition 或跨项目消费；G2 仍未通过，G0 仍关闭，Worker 仍 paused。

## Session: pilot package→raw resolver 原件回放（2026-09-27）

- Revenue-forecast 前置重核（只读）：progress Round 120、register §161、owner decisions §39。定位到实际 `execution_runs/I-05-C/a20260919-01` 与 `execution_runs/I-06-A/a20260922-02`。I-05-C `accepted_scoped` 仍有限定范围，review 记录真实 producer 仍为 mock、`consumer_analysis` 入口/owner 和 InvocationTracker 生产事件 schema 未闭合；I-06-A `accepted_scoped` 仍只覆盖审查范围，handoff 的 open items 保留 I-06-B consumption/CLI、RF caller wiring、跨进程 claim、外部 probe 和 owner-side production commit。G0 继续关闭；没有写 revenue-forecast 或其他仓库。
- 在既有隔离 `narrative_retrieval.py` 增加 pilot-only `NarrativeEvidenceResolver`，使用调用方显式 source ID→raw path 与冻结 pilot manifest 元数据；先校验 raw SHA/source ID，再按同 parser/selector 回放并核对完整 selected-group 集合、evidence ID、locator、raw text hash、parser/version。每次 resolve 重哈希原件；bundle 不提供或控制原件路径；进程内只缓存 selected groups。它不写 catalog/SQLite/FTS/cache，不宣称正式 G2 API。新增失败关闭条件：错误原件 hash、伪造 locator、bundle 文本篡改、选择状态/解析版本不符均拒绝。
- 扩展 12 件真实样本隔离 E2E：复制 10 PDF + 2 TXT 到唯一 run tree，对每个可搜索来源的全部 selected groups 逐组从隔离 raw 重解析，并核对完整 ID/locator/text；检索锚点命中再经 resolver 回源。保留 P06/T02 两样本端到端路径。测试不从生产目录解析写回；所有样本/包/metrics/中间物均在 pytest temp 内。
- 最终验证：`pytest -p no:cacheprovider --basetemp <unique> tests/e2e/test_narrative_g1_pipeline.py tests/unit/test_narrative_retrieval.py` **13 passed in 127.82s**；其中 11 个检索/回源单测、2 个 E2E。`ruff check` 通过。前一轮完整 E2E 通过后加了 package-text SHA 与 replay 后 raw SHA 守卫，故又在最终代码上重跑整组关键 E2E。
- 清理复核：pytest basetemp 被治理到 `%TEMP%\\cw-pytest-basetemp\\20260927-030238-207f9002`，cleanup 事件显示 removed=true，随后 `Test-Path` 复核不存在；`tests/e2e/.runtime/` 运行前不存在，运行后也不存在。E2E finally 比较 run tree 与基线一致，未留下 12 件副本、package、metrics 或测量 JSON。
- 当前限制：resolver 依赖 pilot manifest 的 language/title/table options；bundle 没有冻结正式 parser/selector 版本、处置状态、授权路径和历史时点查询。旧 `EvidenceQueryService.lookup` 仍只查旧 spans，不能由这个预研替代。G2、三仓 consumer、真实 transcript acquisition、G1 独立摘要审查仍未通过，Worker 保持 paused。
- 命令/测试错误留痕：①第一次跨 repo `rg --files` 搜索范围过宽，触及 RF execution_runs 中受 ACL 保护的 scratch 并返回 access denied；只读，改为精确 attempt 路径。②首次 RF attempt 路径误用了 `attempts/`，RF 实际归档目录是 `execution_runs/`；之后已按实际 attempt id 定向读取。③I-05-C 首次把 attempt 子目录误设为 a20260921-01，实际当前 carrier 位于 a20260919-01；纠正后复核成功。④resolver 首轮合成 TXT 没触发业务候选；改用已有 positive fixture 结构。随后发现 `_sha256_file` helper 漏定义，补齐后单测通过。中间失败运行的 run root/basetemp 均由 finally/外层清理并删除；最后完整目标测试在最终代码通过。

## Session: G1–G4 端到端测试方案安全性复核（2026-09-27）

- 用户要求关键步骤具备真正端到端测试，所有测试文件/下载/状态都放在独立测试目录，结束后恢复目录原样。本轮只改专项计划文档，未运行 Worker、provider、网络、生产目录或跨仓消费者。
- 复核发现测试计划已有隔离与恢复原则，但大节点矩阵的表格少了明确的放行列，且遗留运行清理依赖清单语义过宽；已修订为四列矩阵，并把 cleanup 限制为“运行根开始时不存在、唯一 run-id 独占、manifest 与 canonical path 验证通过”的精确目录。
- 增补正常失败清理与强杀/断电后续恢复协议：PID 加进程启动时间校验；遗留进程、manifest 损坏、reparse point 或越界写入时拒绝自动删除；任何根外写入都失败并留待人工排查。原先不存在的真实下载/模拟下载、摘要及数据库派生物必须随 run root 删除，结束检查 run root 和下载路径不存在、fixture/runtime 基线恢复。
- G1 transcript E2E 明确要经过 filing-fetch 的生产编排调用边界，以 fake earnings-transcripts tool/provider 替代外部副作用；G2 要用消费者真实 reader 并收各 owner 收据；G3 使用真子进程；G4 仅在 scratch 副本上删除。矩阵明确合同测试不能冒充跨仓 E2E。
- 更新 task_plan 与 findings，沿用既有 E2E 计划入口；未新增每张 W/N/D 卡的签收步骤。未执行项目测试，因此本会话只有文档结构/内容复核，不声称测试代码验证通过。
- 创建窗口的进一步审查已把运行清单改为运行根同级控制文件：先用唯一 run-id 创建 pending、flush/fsync 并原子改名为正式 manifest，再创建运行根；中断遗留 pending 且 root 不存在时只清理该精确 pending。文件树恢复仍以 fixture/runtime 前后快照为最终门槛。
- 首轮静态校验脚本有一个自定义中文短语与正文措辞不一致，未发现文档结构问题；改为检查实际合同词组后重新运行。
- 为确保连“创建 runtime 容器后、pending 清单前”中断也不留下未知目录，规定 runtime 父容器由测试基础设施预先初始化并作为基线；若未初始化则阻止运行或使用已存在的显式 basetemp 父目录。单次 E2E 只创建/删除同 ID manifest 与 run root，运行容器本身前后保持不变。- 一次跨计划文档更新脚本在 progress 段落锚点上未匹配并安全停止；此前已成功更新的 test_acceptance/findings 未回滚或覆盖。改用文件末尾追加记录后继续。

## Session: bundle v0.2 目标回归与测试目录清理确认（2026-09-27）

- 在显式唯一 --basetemp 下运行 12 个 retrieval/resolver 单测和 P06/T02 来源到摘要 E2E；结果 **13 passed, 1 deselected in 5.73s**。被排除项是 12 样本 selected-anchor/raw-replay E2E；本轮未因新加的未知 selector contract 单测而重跑该耗时用例。`ruff check` 对本轮相关 5 个代码/测试文件通过。
- pytest 治理器将请求 basetemp 迁至唯一短路径并输出 cleanup removed=true；分别复核请求路径、实际路径和 tests/e2e/.runtime 均不存在，测试目录回到本次运行前状态。
- 结果限定：bundle v0.2.0 的 12 样本 E2E 在此前的一次回归中通过，但同轮有另一项 P06/T02 旧 schema 常量断言失败；修复断言后 P06/T02 单项通过。当前没有一次把 12 样本 E2E、P06/T02 E2E 与 12 单测合并运行且全绿的最终总套件收据。
- v0.2.0 selected-evidence bundle 现在内含 replay_contract（parser/selector 名称和版本、格式/语言/document kind、parser options、选择上限）；raw path 仍由调用方显式映射。已更新 README、implementation/test/overall plan、findings 和跨项目状态，不再把 resolver 描述为依赖 manifest 提供解析参数。历史 progress 项保留为当时记录。
- 计划修改仅限 docs/plans/narrative-evidence-pilot-2026-09-26；没有改其他仓库计划、共享接口、catalog、真实公司目录或 Worker 状态。Worker 仍 paused，G0 仍关闭。- 两次把含 Markdown 反引号的补丁嵌入 JS 模板时触发工具脚本语法错误，失败发生在 apply_patch 调用前且未写入文件；随后改用精确章节边界/锚点的文件更新方式完成，最终检查通过。
## Session: 最终合并回归及端到端测试目录恢复复核（2026-09-27）

- 最终代码上合并运行 `tests/unit/test_narrative_retrieval.py` 与 `tests/e2e/test_narrative_g1_pipeline.py`：12 个检索/回源单测、P06/T02 双样本链路 E2E、12 件样本 selected-anchor/raw-replay E2E，共 **14 passed in 122.56s**；相关 `ruff check` 通过。此次补齐了上一轮遗漏的“更新后代码全套合并、全绿”收据。
- 测试使用唯一 basetemp 与 run ID。pytest 治理器实际 basetemp `C:\Users\郑曾波\AppData\Local\Temp\cw-pytest-basetemp\20260927-034720-1fddadeb` 在 runner 收尾报告 removed=true，之后 `Test-Path` 复核不存在；`tests/e2e/.runtime/` 运行前和运行后均不存在。所有样本副本、package、metrics、临时状态和 run tree 均未保留，测试目录恢复到运行前基线。
- 本轮只更新本计划目录中的当前状态摘要与进度收据；未写生产 catalog/company 目录、Worker 状态、真实 provider/网络或 revenue-forecast、StockWiki、invest-quick-scan。G0 仍关闭，G2a 仍是隔离预研，不表示生产 API/consumer、未选内容召回率或 p95 已验证。

## Session: G1–G4 E2E 纳入总计划并校正消费者测试边界（2026-09-27）

- 按用户要求，复核并同步关键节点 E2E 到总计划。既有 [端到端测试计划](end_to_end_test_plan.md) 覆盖 G1 来源到证据包（含 acquisition）、G2a StockWiki/RF 实际 reader、G2b quick-scan optional identity、G3 多文档真子进程 Worker、G4 scratch 原文处置；测试用样本副本、模拟/真实下载、DB/WAL、日志和产物均被限定在唯一 run-id 根，清理后对照运行前文件树基线。
- 明确真实 transcript acquisition 默认使用 fake provider 经过 filing-fetch 编排边界；真实下载只可在边界隔离已证明且单次授权的 canary 中进行，新增 TXT/sidecar/摘要副本测试结束后必须不存在。Worker E2E 需确认子进程退出、句柄关闭和状态对账；G4 只删除 scratch 副本。E2E 集中在 G1–G4 大节点，不逐 W/N/D 小卡重复全量执行。
- 同步纠正旧消费者假设：StockWiki strict Source Provider v1 不兼容 pilot bundle v0.2.0，revenue-forecast 当前接口仍待 G0 owner 合同，invest-quick-scan 不是叙述包消费者。尚未冻结 `NarrativeEvidencePackage/v1` 默认版本；相关文档已将 G2 拆分并列出真实 reader/identity E2E 的待办及 hold 条件。
- 记录最新离线回归收据：12 个检索/回源单测 + P06/T02 双样本 E2E + 12 件样本 E2E 为 **14 passed in 130.77s**。指定 basetemp 与 pytest 实际 basetemp 均清理并复核不存在，`.runtime` 测试容器未出现，`tests/e2e` 文件 SHA 集合不变。该回归不测试 transcript acquisition、跨仓 reader、Worker 或 scratch 删除流程。
- 本轮只改本计划目录中的文档，没有执行下载、Worker、删除、生产目录写入，也未改 revenue-forecast、StockWiki 或 invest-quick-scan。文档链接与旧接口表述完成静态复查；G0 保持关闭。
- Revenue-forecast 并发前置重核：I-16-B 卡仍为 `planned`，未见该卡部署执行收据。其目录 `a20260926-02/impact_scope.json` 实际记录的是 I-16-A，不能当作 I-16-B 的执行凭证。I-16-B `snapshot_manifest.json` 在 01:55:35Z 创建时 `all_match=true`；本轮只读重算发现其覆盖的本专题 91 个计划文件中 11 个 SHA 已变，这是计划目录版本差异，不是生产改动。已把“RF 实施前刷新/复核快照”的条件写入跨项目协调文件；本轮未写 RF 仓库。

## Session: filing-fetch × earnings-transcripts acquisition 接口核实（2026-09-27）

- 按持续目标先重查 revenue-forecast：Round 120 / register §161 / owner decisions §39；I-16-A 在飞状态为“读卡”，I-16-B 卡仍 `planned`，未见 I-16-B 部署收据。其 01:55Z 快照在创建时一致，但对本专题 91 个纳入文件重核有 11 个 SHA 不同；本轮只写 company-wiki 专项计划，没有写 RF。I-16-B 实施前仍需按最终计划版本重新冻结快照。
- 应用 filing-fetch 技能并只读核验对应项目源码：没有暴露 earnings-transcripts MCP tool；`earnings-transcripts` 实际接口是 `scraper.py` CLI，缺 `--config`，仅 `--output` 不会隔离 logs/lock/cache，默认翻译，`--quarters` 为最近 N 季而非 exact-period。其 writer 会添加 header，FMP 返回的 URL 当前为占位文本 `FMP API`。
- `filing-fetch` 实际 `resolve_filing()` 只做 verified identity + company-wiki resolve/ensure 并返回 filing handle；schema 1.2 严格拒绝未知字段，无 related-transcript 复合结果。repo/安装技能文档写 schema 1.1、v1.4.0，与当前 Python 常量 1.2/1.2.0 不一致；外仓 `git status` 因 safe-directory ownership protection 无法只读完成，未修改其设置或文件。
- 据此将 companion flow 调整为：新版 request 对财报获取默认启用一个有界、精确 period/as-of 的 related transcript；旧 schema 不变；filing 与 transcript 独立子结果。先冻结上游 provider/response contract 和 no-translation、可隔离 adapter；此 G1e gate 不依赖 RF 下游 G0，G2 仍依赖。更新了 implementation/execution/test/E2E/task/findings/cross-project 文档，具体证据和限制见 [findings](findings.md)。没有新增真实下载、外部项目写入或运行测试。
- 操作记录：第一次只读状态命令把 bash brace expansion 写进 PowerShell 导致 parser error，命令解析阶段未执行；改为显式文件参数后读取成功，无文件副作用。

## Session: 外部数据源成本、调用量与人工平台比较（2026-09-27）

- 保持 revenue-forecast I-16-A/I-16-B 协调门禁：本轮未改该仓或其活动计划，G0 仍关闭；Worker 仍暂停。本轮编辑范围仅 company-wiki 本专项计划目录。
- 查 SEC/FMP/Koyfin/Seeking Alpha 官方页面，形成 [外部来源成本卡](provider_cost_and_capability_2026-09-27.md)。本地目录实数 246 家，明确不是 FMP/美股已核实分母；按 20 家每日、其余每周五轮、20% 请求余量，免费 FMP SEC 补充预算 2,076 calls/30 日，首月 profile bootstrap 2,372；纯 SEC/IR 为 0 FMP calls。付费方案均有精确 endpoint 权益和存储许可待验证，当前建议 $0。
- FMP 用用户已有 key 做只读小样本：先在沙箱内四请求均遇 URLError，不能判定权限；提权后的首次 Python 命令解析失败，未发请求。修正后 MSFT profile 200、SEC 因缺必填日期 400、新闻稿 402、电话会期次 402；补齐 SEC 必填参数后 200。只打印 endpoint/status/响应长度，未保存正文或密钥，仓库未产生探针文件。
- 复核 earnings-transcripts 工作树，已有未提交 transcript_api.py、transcript_tool.py；旧审计中“当前只有 scraper.py CLI”的陈述因此仅代表当时快照。filing-fetch 尚未连通 companion flow，本轮未运行其跨仓 E2E。
- 对新增计划文件执行公式复算、链接/表格/改动范围静态检查。此处是计划和只读 API canary，没有运行产品测试或生产采集。

## Session: G1e 来源权利校正与隔离导入合同试验（2026-09-27）

- 再核 revenue-forecast 当前 I-16-A 隔离/部署绑定仍在进行、I-16-B 待后续；没有修改 RF、filing-fetch 或 earnings-transcripts 工作树，也没有触碰生产 catalog、公司原文或 Worker。为隔离 CWP 试验创建并使用托管 worktree `C:\\Users\\郑曾波\\.codex\\worktrees\\transcript-companion\\company-wiki`，分支 `codex/transcript-companion`；主工作树仅更新本独立计划文档。
- 隔离分支新增 TXT transcript 路由、Windows 短文件名、结果身份/期间/as-of/hash/URL 校验和默认拒绝的 `TranscriptUseGrant` 导入闸门；没有生产 grant，亦未接通 filing-fetch。测试中的 synthetic grant 仅用于离线合同测试，不构成 Motley Fool 的实际许可。由于未保留 provider 原始 HTML，且尚缺正式权利表，此分支仍是 spike，不合并/不宣称 G1e 完成。
- 独立 temp catalog/writer 合同测试 18 passed；`ruff check --no-cache` 全绿、`git diff --check` 无错误。首轮测试误用不存在的测试文件名，0 tests、无产品副作用；改用实际 `test_source_catalog_canonical_writer.py` 后通过。pytest 治理器报告有效 basetemp cleanup removed=false，进程退出后按已验证的精确绝对路径单独清理，最终 `remaining=False`；没有通配清理或触碰生产树。
- 官方来源复核发现 Motley Fool 禁止自动采集、Seeking Alpha 个人条款限制抓取；SEC 8-K 有电话会议全文附件实例，NVIDIA IR PDF 有 FactSet 版权。已更新本计划入口、来源成本卡和 G1e E2E 门槛；采购仍为先不买。下一动作是冻结 provider 逐动作权利表并探索 issuer-authored SEC 附件的有界覆盖，完成原件/派生双层来源合同后再考虑接正式编排。


- 补充并冻结规划层面的 [`transcript_provider_rights_contract_v1.md`](transcript_provider_rights_contract_v1.md)：7 个分离动作、政策字段/来源、网络前与持久化前双检查、原件与英文 TXT 的 parent/hash、撤销处理、G1e 集中 E2E 和 hold 条件。合同没有授予任何待核来源正文许可。
- 另查 3 个 2026 年 SEC EX-99 电话会全文 HTML 实例，并找到 SEC 内 FactSet 版权附件反例；已在 findings 留链接。该小样本没有下载正文或测 20 家公司覆盖。隔离权利闸门补 3 个缺动作/过期/错 provider 负例，目标测试 **14 passed**、`ruff check` 全绿，唯一 pytest basetemp 自清理 removed=true。

- 最终合并运行 `test_transcript_companion_import.py` + `test_source_catalog_canonical_writer.py`：**21 passed in 3.13s**。pytest 有效 basetemp `20260927-065548-ea9d15b7` 在 runner 内因短暂句柄未自动删除；进程退出后按精确路径与非 reparse 检查清除，`remaining=False`。这仍只是隔离合同试验，不是 G1e 正式编排/来源许可/原件双层保存验收。


## Session: G1e 复用精确授权并实现隔离请求前闸门（2026-09-27）

- 阶段开始再查 revenue-forecast register §161：I-16-A 仍在飞、I-16-B 待做；未改其文件。CWP 主工作树未改产品代码，Worker 仍暂停；仅在托管 `codex/transcript-companion` 工作树新增 `provider_use_policy.py` 和 `test_provider_use_policy.py`。
- 已读现有 `authorization.py`、`runtime_policy.py`、`SourceManifest` 和 artifact schema；据此在计划合同补“复用现有 DownloadAuthorization，不替代”的精确规则。
- 隔离实现：严格 schema/hash 的只读 provider 权限规则，动作与 URL/日期/保留/导出范围检查，Motley Fool/Seeking Alpha provider 或站点 host 硬拒；请求前 `authorize_transcript_fetch` 组合 `SourceRequest`、`DownloadCandidate`、现有 `validate_download_authorization`、RuntimePolicy hash 和 provider 权限。候选必须包含与请求一致的 market/security_id、确切 FY/Q、已知 remote size；否则拒绝。无网络、无生产政策加载或正式编排。
- 13 项定向合同测试通过，`ruff check --no-cache` 全绿；唯一 pytest basetemp `20260927-070504-92fa9727` 清理报告 removed=true。此结果不覆盖原件/派生存储、下载后再检查、filing-fetch×earnings-transcripts E2E 或真实来源许可，G1e 保持 hold。


- 继续硬化隔离 `provider_use_policy.py`：站点 host 与 provider 双拒绝、禁止编码路径越界、政策文件 1 MiB/规则 1000 条上限、严格 JSON/hash/日期/范围；增加 `authorize_transcript_fetch` 复用既有 DownloadAuthorization 的请求前决策。合并 3 组合同测试 **34 passed in 3.48s**，相关 `ruff check --no-cache` 全绿。pytest 有效 basetemp `20260927-070750-7671eb33` runner 内因句柄 removed=false，进程退出后按精确路径/非 reparse 验证后删除，`remaining=False`。无网络、无生产目录写入，G1e 仍未放行。
- 代码调查发现 generic HTML normalizer 为整篇单 locator，不能满足 transcript speaker/QA 原件定位；已写入 findings，下一阶段做专用原件→TXT/locator 合同。未修改 revenue-forecast 或其他仓库。

## Session: 原件字节回放与 earnings-transcripts/平台能力比较（2026-09-27）

- 隔离 `codex/transcript-companion` 工作树的旧 TXT-as-raw spike 已撤去。新增纯 `transcript_material.py`：对 synthetic UTF-8 HTML/TXT 生成未经翻译的行、原件字节 locator、原件/文本 SHA、转换版本和持久化 lineage 回放；真实临时 SourceCatalog/CanonicalSourceWriter 合同测试证明 HTML 原件的 source ID 与 SHA，派生 TXT 只在内存中。当前还没有派生 artifact 持久化、下载后权利复核、正式 provider 或 filing-fetch 编排。
- 合并运行 `test_provider_use_policy.py`、`test_transcript_material.py`、`test_transcript_original_import.py` 和既有 canonical writer 测试：初次因回放重算放错函数产生 4 个递归失败；修正后 **27 passed in 2.53s**，`ruff check --no-cache` 与 `git diff --check` 全绿。两次 pytest 有效 basetemp 分别为 `20260927-071735-e3afe4fc` 与 `20260927-071827-32248168`，runner 内清理均报告 removed=false；进程退出后逐个核实位于专用 temp 根且非 reparse，再按精确路径清理，最终两者 `remaining=False`。无生产公司文件、catalog、Worker 或外部正文写入。
- 用户要求将 Koyfin/Seeking Alpha 与现有 earnings-transcripts 实际能力并排比较。只读 ET 工作树、两接口源码和本地文件数/大小；43 份英文全部标为 Motley Fool，6 家公司，本地三格式和 summary 合计 15,953,731 B。写入[对照卡](earnings_transcripts_vs_platforms_2026-09-27.md)，明确已提交 CLI 与未提交精确季度接口不同、原件缺口和商业平台人工阅读/自动权限边界。没有登录/抓取 Koyfin、Seeking Alpha 或 Motley Fool，未修改 ET 工作树；仍待 20 家 30 日覆盖/增量试点，结论为先不订阅。
- 本轮只更新 company-wiki 独立计划目录与托管隔离分支；没有改 revenue-forecast、filing-fetch、earnings-transcripts、StockWiki 或 invest-quick-scan。G0、G1e 正式放行、G2/G3/G4 均保持原门禁，Worker 继续暂停。

## Session: 紧凑 transcript lineage 与确定性 locator 回放（2026-09-27）

- 开始前复核 revenue-forecast 最新状态：register §162 / Round 120，I-17-A 在飞而基础卡模板为 `planned`，I-17-B 待后续；I-16-B 已 `accepted_scoped`；Worker 仍 paused。未修改 RF。再次确认新 transcript artifact role 需穿过 `ROLE_DEPENDENCIES`、`SourceBundle`、read model、producer registry 和 CLI allowlist，G0 前不触碰这条共享合同。
- 在托管隔离分支将 `transcript_material` 从 schema v1 改为 v2：lineage 持久字典去掉逐行 locator 列表，仅存 parent source ID/SHA、可信 MIME、原件/派生字节数与 SHA、extractor 版本及行数。load API 必须显式传入 trusted `expected_mime_type`，从 canonical original 重算材料，再核对 lineage 和现存派生 TXT 的 exact bytes；成功时只返回内存 locator。
- 更新 HTML/TXT 与 synthetic canonical import 合同测试：覆盖 locator 不落盘、line count 篡改、调用 MIME 与 trusted receipt 不一致、TXT 同一性及原件 SHA/locator 回放。定向 suite **27 passed in 4.79s**；Ruff 与 `git diff --check` 通过。pytest requested basetemp 被运行器依路径预算改到另一专用临时目录；实际和 requested 两个精确目录均验证位于 temp 根下、没有 reparse point 后逐个删除，最终不存在。
- 这是隔离 helper 级的存储压缩，不代表大库节省数或 production catalog 接入。下一步按 Next Step 实现 fake-provider post-fetch identity/rights recheck 和 acquisition E2E；没有真实提供商正文请求，也没有启动 Worker 或写入公司原文目录。

## Session: transcript 下载后权限与字节复核（2026-09-27）

- 对照 `DownloadAuthorization`、`DownloadReceipt`、`AcquisitionCoordinator._validate_receipt` 与 provider rights policy 后发现：现有预取准入只覆盖候选元数据及 `automated_fetch`，不能证明 HTTP 之后的 effective URL、保留/派生权限、实际文件字节/hash仍受授权约束。
- 在隔离 `provider_use_policy.py` 增加 `validate_transcript_fetch_result`：要求 post-fetch freshly loaded rights policy hash 与预取 pin 一致；复验原 exact request authorization；比对 response receipt 的 candidate/provider/document/url；要求 2xx、可解析 TXT/HTML MIME、字节不超过授权上限、retrieved timestamp 不晚于复核时间、resolved file 留在专属 staging root、为 regular file、文件实际长度和 SHA 与 receipt 一致；然后在 final URL 上分别确认 fetch/retain/derive 三种 action 都被许可。仅为验证返回结构化判定，不 canonicalize 文件。拒绝原因可供调用方安全清理。
- 假响应测试覆盖 policy 更新/redirect 到外域或被禁站点、staging 外路径、ID/MIME/大小/SHA 篡改与合规成功响应。初轮测试夹具传入多余 `rights_policy` 字段，下一轮修正时又过早移除 policy；随后 SHA 篡改 fixture 长度变化先命中 size gate。对应三处均根据实际异常修正，不修改生产接口。
- 最终与 lineage/raw-import/canonical writer 合并定向测试 **33 passed in 5.56s**；Ruff 通过，`git diff --check` 空。3 次失败运行和 1 次最终运行共 8 个精确 requested/effective pytest 目录，均先验证限定在专用 TEMP 根与无 reparse point，再分别删除并核实不存在。
- 重要边界：`DownloadReceipt` 没有 effective redirect URL 字段。validator 目前能够检查 final URL 当下的权限，但不会自动把它加进 canonical sidecar。后续 fake E2E 用无 redirect fixture；production promotion 前要记录 effective URL provenance，或拒绝 redirect。Revenue-forecast 仍为 §162 / Round120，I-17-A 在飞，Worker paused；本轮没有改 RF、真实 provider、生产 catalog 或 Worker。

## Session: fake-provider transcript E2E 与跨仓契约复核（2026-09-27）

- 新增 company-wiki 隔离 E2E：未授权时 provider 调用 0；请求前授权后，假 redirect 到未许可域在 canonical import 前拒绝并清理 staging；合法 HTML 通过 post-fetch 检查、经 `CanonicalSourceWriter` 保存单份原件、生成未翻译 TXT 和紧凑 lineage、重算 locator，并由 `SourceResolver` 命中 reuse。所有文件位于唯一 test run root，finally 确认删除后恢复初始不存在状态。
- E2E 初跑依次暴露测试 staging dir 未创建、URI 格式 source ID 含 Windows 禁用冒号、pytest 深根叠加 company-tree 产生 sidecar 长路径三个 fixture 问题；修正为 provider 创建 staging、用 raw SHA 命名派生文件、缩短测试根/公司目录后通过。错误 run 的 2 个 basetemp 也逐一检查并清理。一次补丁上下文匹配失败后读取实际 imports 重做，没有造成文件变更。
- 最终 combined focused suite **34 passed in 4.31s**；ruff 和 `git diff --check` 全绿；最终 requested/effective pytest temp 均经精确路径/reparse 检查清理。未运行真实 ET/FMP/MF 网络，也未访问生产 raw/catalog/worker。
- 跨仓复核发现 E-T 当前 JSON subprocess 结果只返回 payload hash 和 clean text，不含原始 HTML/JSON payload bytes，也不含 effective URL；而 filing-fetch code request schema 1.2 与 SKILL.md 1.1 漂移、无 companion response contract。已新增[跨仓集成合同草案](filing_fetch_transcript_integration_v1.md)，将后续分为 E-T response v2、CWP stdin importer、filing-fetch companion schema/partial-success、跨仓 E2E；没有改 E-T、filing-fetch 或 revenue-forecast。
- revenue-forecast 最新只读状态仍为 Round 120 / register §162，I-17-A 在飞、Worker paused、G0 open。没有修改其文件、工作树、监控或同步计划；Motley Fool/FMP 的真实 provider gate 继续关闭。

## Session: Koyfin / Seeking Alpha 免费层是否纳入来源链（2026-09-27）

- 按用户新增边界“无真实增量不强加 provider”，只查官网价格/功能/条款，没有登录、调用 private API 或抓取站点正文。
- Koyfin 官方当前 Free 是有限新闻/公司快照等，filings、新闻稿、transcripts 标在 Plus；因此免费层对叙述原件自动链无实证增量。不接 adapter。
- Seeking Alpha 官方称 earnings-call transcripts 免费并介绍覆盖/时效；但其条款明确允许个人非商业访问/下载且禁止自动 robot/retrieval/index/data-mine/scrape/harvest。故只保留可选人工发现链接，正文不写入 CWP，不接 SA provider。
- 更新 [平台对照卡](earnings_transcripts_vs_platforms_2026-09-27.md)、[跨仓集成合同](filing_fetch_transcript_integration_v1.md)、task_plan 与 findings：机器来源先找 issuer/SEC 的逐件可留存材料；SA 外链只辅助发现并追溯一手来源；无须购买，不新增订阅成本、connector 或 Worker 状态。
- 依据：[Koyfin Free/Plus 权益](https://www.koyfin.com/pricing/)、[Koyfin Terms](https://app.koyfin.com/terms-and-conditions)、[SA transcripts 信息](https://about.seekingalpha.com/transcripts)、[SA Terms](https://about.seekingalpha.com/terms)。

## Session: G1e-C company-wiki importer 核心（2026-09-27）

- 在托管隔离 company-wiki worktree 实现 `transcript_import.py` 库函数：消费 earnings-transcripts result `/2` 原始 JSON，不依赖 unbounded stdout；拒绝重复 JSON key、未知 schema/字段、错 request/provider/document/ticker/exchange/FY/Q/as-of/publication date/source/effective URL/MIME/HTTP/timestamp/hash/字节上限。要求 fetch 前 admission 已绑定本次 request、candidate 和 DownloadAuthorization receipt hash；另以下载后当前 rights policy 对齐 preflight pin 并复查动作。
- 原始 payload 先受限写入 private staging；post-fetch gate 与 UTF-8 原件 locator 解析都通过后才调用 canonical writer。只保存一份原始 HTML/TXT；派生英文材料和精确 byte locator 返回内存，不落第二份全文。rights policy hash、DownloadAuthorization hash、effective URL、原文 SHA、adapter/extractor 版本及允许动作写入 `.source.json` 下的 namespaced provenance extension（≤16 KiB）。旧 canonical writer 调用不传 extension 时行为不变。
- 同步补上 `DownloadAuthorization.request_id == SourceRequest.request_id` 检查；现存 helper 漏检时，不同请求在重用 provider/accession 授权的情况下可能通过其他范围校验。新增对应负例。
- E2E 使用 `fixtures.invalid` 假结果，在唯一 pytest basetemp 中覆盖坏 payload SHA、错 request/document/venue/period、外部 effective URL、重复键、拒绝 admission 和合法 canonical 原件+审计 sidecar；失败路径无 staging/raw，成功路径清空 staging，测试 finally 将 run tree 还原为不存在。
- company-wiki transcript helper、writer、acquisition、sidecar 聚焦组合 **56 passed in 5.46s**；CWP Ruff 与 diff check 通过。earnings-transcripts 完整确定性离线回归 **106 passed, 1 deselected, 2 warnings**；被排除项是需要本机未配置的 LLM 凭证、且会断言某个 LLM translator 被选择的既有测试。未排除运行时该一项失败并降级到 Google；产品代码测试通过。
- 本 session 没有对真实 transcript provider 正文端点发请求；没有接 stdin CLI、filing-fetch caller 或 production rights policy，不宣称 G1e-C 完成。Motley Fool/Seeking Alpha 自动来源 hard-deny、FMP 402 和保留/派生权未决；不增加 Koyfin/SA connector。RF 保持 Round 120 / register §162 的最后已知同步点、Worker paused；没有改 RF、filing-fetch 或共享 artifact role DAG。

## Session: G1e-C stdin importer CLI、翻译边界与提供方约束（2026-09-27）

- 复核 revenue-forecast 最新只读快照：Round 121 / Phase 7 complete，HEAD `ee0a82bf`（10:06）；I-17-B 的 UTF-16 负例门发现 N1/N2/N4/N5 未拒绝，属于 RF 新质量缺口。没有在 RF、filing-fetch 或共享 role DAG 上写入；Worker 仍 paused。当前 importer slice 与该缺口独立，后续父调用编排仍等 RF 同步窗口。
- 在已存在的托管隔离 company-wiki worktree 增加 `transcript_import_cli.py` 和 console entry。stdin envelope 有字节上限、UTF-8/重复 JSON key/严格字段验证；request/candidate 按真实 dataclass 全字段重建，单 accession DownloadAuthorization hash 重算；固定从传入 wiki root 的 `config/source_catalog.yaml`、catalog runtime snapshot、`config/provider_use_policy.json` 读取。rights policy 或 runtime snapshot 缺失/无效即拒绝，不创建可由 stdin 自选的授权路径。
- CLI 独立用当前 rights/runtime hash 重算 transcript preflight，并要求与 caller 所传 admission 完全一致；随后由既有 post-fetch import 再查 effective URL/MIME/字节/hash/权利，再交给 canonical writer。成功 stdout 仅有 source ID/hash、状态及行数；不输出正文、base64 或绝对路径。撤权负例证明 rejection 发生在 canonical raw、staging、数据库写入之前；成功 synthetic HTML 只落一份 immutable raw 和紧凑 sidecar，staging 清空，无第二份 TXT 落盘。此 CLI 不是 caller/network 次序的密码学证明；G1e-D 仍需父调用方在发起 discovery/body request 前完成 gate 并用真实 orchestration E2E 验证。
- 新增独立 subprocess E2E 后，transcript CLI + importer/material/provider-rights 组合 **33 passed in 4.61s**；Ruff 对相关代码全绿，`git diff --check` 全绿。第一次 E2E 发现成功路径读取了不存在的 `line_count` 属性并修正为 `len(material.lines)`；重跑成功。pytest harness 因 Windows 路径预算把 request basetemp 移到 TEMP 子目录，最终按精确路径/reparse 检查删除，测试 fixture wiki root 在各用例 finally 还原为不存在。
- 用户指出 company-wiki 不需要翻译。检查 E-T 发现 `scraper.py` 已有 `--no-translate`，双 provider 下载、增量跳过和 dry-run 都尊重它；新增同义名 `--disable-translation` 并把 parser 提成可直接测试的函数。测试证明两个旗标同义，skip 分支不会初始化 `TranslatorFactory` 或写文件。company-wiki 调用的 `transcript_tool.py` / `transcript_api.py` 已始终不读翻译配置、不加载翻译器、不输出双语；不加一个没有效果的 companion CLI 旗标。
- E-T 全套 **108 passed, 2 deselected**：排除缺本机 LLM 凭证的 translator-preference 测试，以及 `test_google_translate`（只对合成短句调用 GoogleTranslator、可能触发外部请求）。此前第一次全套运行曾包含后者；它未处理公司文档，但可能请求了外部翻译。之后离线验收显式排除两项。未读任何 API key，未下载或翻译公司资料。
- E-T Ruff 在本次测试文件/API 文件全绿；`scraper.py` 普通全文件 Ruff 仍有 3 个 diff 外旧问题（未用的 `LineClassifier`/`text_hash` imports 和多余 f-string）。用 `--ignore F401,F541` 复核当前文件其余规则全绿；未顺手改不相关代码。`git diff --check` 通过。
- 没有增加 provider：Koyfin 免费层无自动 transcript 增量、Seeking Alpha 条款不支持自动采集、Motley Fool 仍 hard-deny、FMP 402/内容保留权未解决；不买订阅、不新增 connector。

## Session: revenue-forecast Round 121 跨项目冲突复核（2026-09-27）

- 只读核对 revenue-forecast 活动 PWF 的 `task_plan.md`、`progress.md`、`implementation_plan.md`、最新 owner decisions、remediation register 与当前本地 git refs。确认 Round 121 的 15/15 和 Phase 7 complete 是有范围的卡级验收；RF 本地 task plan 仍有过期的“不完整”状态段，owner §42 又新增 `closure_ready` 修正与 company-wiki pre-push 两项门禁。`fcap`/本地 `origin/main` 指向 `ee0a82bf`，本地 `main` 仍落后；未 fetch，未修改 RF。
- 将这些事实及阻塞边界追加到 [跨项目协调](cross_project_coordination_2026-09-26.md)：I-05-C owner 授权已解决但不等于实现完成；G0 继续关闭；`canonical_writer.py` 需等 DEF-MSFT-CANONICAL-DUP 与本仓改动对齐；叙述模块复杂度门需先处置。此轮未改产品代码、Worker、catalog、原文、Provider 或其他项目状态。

## Session: 数据湖抽象与跨仓责任复核（2026-09-27）

- 应用户要求只读复核 company-wiki、filing-fetch、revenue-forecast 的目录与来源调用链，并与已有 R4 数据湖诊断/实施计划和本专项 G0–G2 对照。确认已有统一索引、policy 和 resolver 同 SHA 副本回退；发现生产 scanner/normalizer 及跨仓消费仍把 root/path 带进元数据或读取行为，CWP/RF 的 `consumer_analysis` DAG 角色双向耦合。未读取原始财报正文、运行下载/Worker 或修改任何仓库产品代码。
- 新增[数据湖边界复核](data_lake_boundary_review_2026-09-27.md)，并仅更新本专项 `task_plan.md`、`implementation_plan.md`、`cross_project_coordination_2026-09-26.md`、`findings.md`、`test_acceptance_plan.md` 和 `end_to_end_test_plan.md`。R4 仍是唯一通用实施计划；沿用其 L01–L12/P01–P03 与本专项 G0/G2 大节点，不新增逐文件门禁。company-wiki 代码继续等待 RF 并线后的统一处理，Worker paused。
- 本轮为 planning-only 静态审查；没有运行产品测试或宣称位置透明已经实现。后续先重核最终 RF/CWP 合同与当前 dirty 文件，再做隔离失败夹具和真实 reader E2E。
- 两位只读审阅者指出并已修正：resolver 虽有候选回退，旧 canonical 仍可能返回 claim-trusted handle，交付字节须另做硬验；G0 只冻结 R4 A 目标/B07 待验条件，G2 才等 R4 B 阶段验收；provider 只提供许可资料和执行获取，CWP 统一裁决具体来源/动作授权。初版链接检查脚本的正则写法失败，换简化检查后八份规划文件相对 Markdown 链接为 0 个失效、尾随空白为 0；未运行产品测试。

## Session: 数据湖优先实施与跨仓真实 E2E 规划（2026-09-27）

- 将 R4 A/B/C.local 设为 RF 并线后共享系统的优先路线，补真实跨根样本、跨进程 open、StockWiki 路径型 SourceExport v1 迁移、所有消费者的无上游原文路径接口与静态/真实入口双重验收。R4 仍是唯一主计划；G0 复用 A 合同审查，G2a 在 W5 后复用 C.local 基础 reader 收据并增验 selected package，不增加逐文件签字。
- B 计划以真实 P06 四隔离副本和星环/微软/拓尔思原生根布局验通用 reader；C.local 基础来源 reader 计划从 filing-fetch、RF、StockWiki 新版真实 CLI 端到端读取，并按本目录 run-id 恢复协议清理。catalog SHA 尚待隔离副本完整核验，真实修订/future_lake 原生样本缺口写 pending；没有把设计写成产品 PASS。
- 本轮只修改规划文档；未运行新产品 E2E、未恢复 Worker、未改变正在进行的 RF 计划或生产文件。当前叙述产品工作树已有未提交改动，待 RF 并线后统一核对，不能归因于本轮规划。

## Session: RF 未提交工作澄清与仓库状态复核（2026-09-27）

- 只读核对 GitHub：company-wiki 远端 `master=f39bd5a`、`fcap=8665c8c`，本地主树 `fcap=dbe4745` 比远端 master 多 4 个提交且有既存 dirty；RF 远端 `main=fcap=ee0a82bfd`，用户确认后续 RF 改动目前**本地未提交**。远端旧并线不代表这批新工作可作为稳定接口。
- R4 与本专项当前技术依赖改为固定 RF 候选快照/支线提交及接口合同，**不要求 Git merge**；旧进度中“等并线”仅属历史口径。company-wiki 任一 worktree 的产品代码与测试改动仍暂停，只有规划/只读核对继续。本轮未执行 fetch、pull、merge、push 或产品测试。

## Session: R4 reader 真实字节回归与 StockWiki 主线重核（2026-09-27）

- RF 最新本地 remote-tracking 事实：`origin/fcap=ee0a82bfd` 是 `origin/main=3a69f9c5` 的祖先，`git rev-list --left-right --count origin/main...origin/fcap` 为 `1 0`；远端主线已包含 fcap 全部已提交内容，main 另有一个后续提交。当前本地 `main=3ce9cc4` 落后 `origin/main` 813 个提交，主工作树在 `fcap=ee0a82b` 且另有未提交代码/执行记录。本轮 `git ls-remote` 因 GitHub 443 连接失败，以上是已缓存 tracking refs 的结论；未改 RF、未清理其 dirty tree、未做重复合并。不能把 RF 本地 dirty product diff 当作已合并内容。
- StockWiki 按用户指示恢复到本地 `master=f5b8526` 后，主线及 `StockWiki-v2-reader` 中的 v2 reader 原型文件均不存在；当前 StockWiki 主线没有 `company_wiki_contract_v2`。因此 R4 C.local StockWiki 新 reader/CLI 必须重新实施和验证，不能引用已清理原型的历史单测声称已接入。StockWiki 状态仅残留自动重新出现的 `.claude/` 本地工具设置，非产品源文件；没有再清理它。
- company-wiki `codex/data-lake-reader` worktree（HEAD `dbe4745`）运行 pathless source export/operation/read-policy/version-reader、normalized artifact 与既有 provenance/摘要合同，连同 P06（三角防务再融资 PDF）及星环科技年报真实字节 E2E：**133 passed**。关键真实样本经 SHA/sidecar 检查后只复制进测试 basetemp，测试断言源文件状态和固定测试树前后相同；测试过程没有改该 worktree 的 dirty 文件清单。
- 首次长路径 basetemp（requested path 100 chars）被 `conftest.py` 重定位到 `%TEMP%/cw-pytest-basetemp/20260927-185414-83e4572c`；测试 133 项通过但清理回执 `removed=false`。该唯一目录仍存在且当前命令返回 Access Denied；没有改 ACL 或删除其他 temp。故该次 E2E 的全局 cleanup gate **未通过**，需用户/环境 owner 清理这个 exact run-id 后才能把测试环境声明为完全恢复。
- 为避免复现，已把 Windows basetemp 短路径规则补进 [端到端测试恢复协议](end_to_end_test_plan.md) §2。相同 133 项随后以仓库 `tmp/r4-<8 hex>` 短路径（解析后 50 chars、`relocated=false`）再次运行：**133 passed in 110.00s**，该 run-id 目录确认不存在，测试 worktree 状态前后相同。此轮直接 reader 真实字节回归仅是 B 的一个实样本子门，不等于 B.AR 四根验收、C.local filing-fetch/RF/StockWiki consumer E2E、OS 文件打开次数计数或 full-scope 位置透明通过。
- CodeGraph 已在 company-wiki 主工作树可用，但 `data-lake-reader` linked worktree 没有 `.codegraph`；已依 AGENTS.md 向用户询问是否初始化。等待答复期间只做了已知文件定向阅读与测试，没有在该 worktree 修改代码。

## Session: CWP 本地集成分支回归收尾（2026-09-27）

- 在用户授权的非沙箱仓库操作下复核 `fcap`：reader、transcript-companion 与此前 selective narrative changes 均已通过本地提交并入；本地 HEAD 相对 `origin/master` 为 9 commits ahead，未 push。transcript writer 唯一冲突已按 immutable provenance 语义解决。
- 集成后的跨分支合同修复和测试夹具改动已完成；36 个受影响测试模块共 **390 passed**。全仓 3,108 项测试曾在约 40% 时中止，不能作为全仓通过。当前剩余工作树包含 9 个产品/测试路径和本计划 task_plan 改动；本轮还需完成 findings/progress 收据、diff/Ruff/常规 commit hooks，再安全 fast-forward 本地 `master` 并把主工作树切回 `master`。不推送远端。
- `.tmp-pytest-narrative-cap`、`.tmp-pytest-narrative-g1` 和先前一次长路径 basetemp 的访问权限问题仍是历史环境残留；本轮未改 ACL、未扩大删除范围。本轮确切 pytest 临时目录已核实并清理。
- 此次只完成分支集成回归，不代表 R4 reader 全面位置透明、filing-fetch/RF/StockWiki 消费者 E2E、G0/G1e、Worker 或旧 46G 退役计划完成。RF 工作树保持未触碰。
- 后续非沙箱只读复核发现 `cw-b06-wt` 只有 1,645 个 tracked deletions，无 untracked/ignored 数据；`r4b06-wip` 无独有提交（相对 master 落后 46 commits）。依照“本地未提交恢复到主线”的既有授权，将该临时 worktree `reset --hard master` 至 `2ecb6f8`，恢复约 69 MB tracked files，复核干净。
- `git fetch origin master` 在非沙箱执行成功并刷新 `.git/FETCH_HEAD`；`FETCH_HEAD` 无只读属性/锁，ACL 未拒当前 Windows 用户。故先前“无法写 FETCH_HEAD”由沙箱文件系统边界导致的判断有实际成功 fetch 验证；本次 fetch 仅更新本地远端跟踪状态，没有 push。
- 跨 worktree 边界复核：reader 与 transcript-companion 工作树干净，其提交均已在集成历史中；RF 工作树仅运行 `git status` 读取，看到的本地 dirty 内容未触碰。旧 `.tmp-pytest-*` 两目录仍有历史 ACL 访问警告，没有改 ACL 或动它们。

## Session: 集成测试失败第一性原理审计（2026-09-27）

- 启动 Phase 22，只读检查修复提交、CodeGraph 索引和 pytest 历史缓存；不修改产品代码。
- 历史缓存含 30 个 node ID，不能等同于计划中修复的 8 个直接失败。第一次直接展开缓存重跑因 22 个过期 node ID/Windows 路径编码而 pytest exit 4，未执行断言；本次错误已记录，独立 `%TEMP%/cw-failure-audit-20260927-a` 已清理。
- 下一步按当前可收集测试和 `251805c..2ecb6f8` 精确差异重建失败分类，再选择当前仍存在且能回答架构风险的最小回归。
- `git archive | tar` 的历史快照提取因中文路径被 Windows tar 错误解码而失败，未执行测试；finally 已删除精确 archive/root。改用临时 detached worktree 成功：修复前六个合同文件为 **6 failed, 53 passed**，pytest 重定位的 basetemp 收据为 `removed=true`，临时 worktree 已由 Git 删除。
- 对正式 producer/consumer 做独立复核发现当前缺陷：producer 仍输出 `acquisition`，consumer 与测试被同步改成 `acquisition_result`。正式 payload 最小复现返回 gap 状态却丢 `gap_plan` 和 `request_id`。因此 390 项绿灯不能作为 R4 继续依据；当前暂停在诊断阶段，不修改产品实现。
- Ruff C901 对八个新增模块报告 13 个高复杂函数；非增长 baseline 是临时 waiver，不是修复。下一步完成各失败类别影响结论和当前相关回归，然后向用户报告修复优先级；未恢复 Worker、未写 RF。
- 当前八个相关测试文件重跑 **88 passed in 44.01s**，独立 `%TEMP%/cw-audit-current-b` 测试根已核实并清理。该绿灯与正式 producer 反例并存，确认缺少 latest-as-of/gap 的 producer→CLI→projection E2E。
- Phase 22 完成：不把问题归结为单纯“测试错了”或“仓库整体坏了”。当前阻断是新 v2 抽象层的 DTO 断链；安全夹具/Windows harness 应调整测试；复杂度属于未解决的生产化风险。产品实现本轮未改，Worker/RF 未触碰。

## Session: Phase 23 清洁架构与 TDD 总图（2026-09-27）

- 用户明确最终安全底线：下载的财报、公告、招股/再融资、投资者关系和电话会议原件不得丢失；normalized、spans、摘要、索引、缓存、staging 等中间产物可删除重建；项目未投产，允许大规模重构内部代码和派生 schema。
- 新增 [清洁架构与 TDD 实施总图](clean_architecture_tdd_execution_plan_2026-09-27.md)，把 catalog/read/acquisition/derive/evidence/export/jobs 分成 L0–L7 单向依赖，并把现有 R4、叙述证据、transcript、Worker、跨仓和空间计划收束为 Phase A–G、M1–M4 四个大节点。
- 测试体系明确为 U/C/I/E/X/P：正式 producer/service/CLI 生成正例，手写 JSON 只做畸形负例；真实 CLI 使用独立 run root，前后哈希快照和 finally 清理；大节点才跑受影响全集，避免每个小步骤反复全验。
- 在写计划前做了一个未提交 TDD spike：正式 `SourceEnsureResult.to_dict()` gap 测试首先按预期失败（`gap_plan=None`）；一行恢复 `acquisition` 后 3 项通过；再加未知 schema、错误别名和 request ID 漂移三项红测后，重构原型达到 6 项通过。这些结果只用于验证施工方向。用户要求“先计划后实施”后，`source_operation.py` 与对应测试已全部 `git restore` 到 HEAD，工作树只保留规划文档改动。
- RF 阶段边界只读核对：远端 `origin/main=3a69f9c5b`；本地 `fcap=ee0a82bfd`，仍有其既有 planning/assurance 未提交改动与一次性运行目录。本项目没有写入、清理或切换 RF。
- 工具调查中曾错误假设 `gap_plan.py` 存在 `GapItem`，import 失败后直接读取正式 `GapPlan` 和 `DownloadCandidate` 定义修正；没有文件改动或测试副作用。追加 planning 日志的首个补丁也因锚点标题不匹配安全失败，随后按文件真实尾部重试。
- 下一步严格从总图 Phase B 开始：先提交 producer→contract 和 latest-as-of fake-provider CLI 的 RED tests，再实施 typed operation contract、纯 projection 与 reader facade；不能用一行字段修补代替重构。

## Session: Phase B / M1 来源读取与 acquisition operation 重构（2026-09-27）

- 先提交清洁架构与 TDD 总图，再开始产品实现。正式 producer 红测首先得到 4 failed / 2 passed，真实 latest-as-of fake-provider CLI 也复现 `gap_plan=None`；没有用一行字段补丁掩盖断裂。
- 新增 `operation_contract.py` 与 `operation_projection.py`，把 producer schema/request identity/状态校验和 pathless 投影分开；`source_operation.py` 只编排 parse → project。错误 `acquisition_result`、未知 schema、非法 policy hash、负下载计数、大小/MIME 漂移和路径字段均失败关闭。
- read-only ensure 改用真实 `AcquisitionResult` + `SourceEnsureResult.to_dict()`；`attempt=None` 明确表示没有 acquisition attempt，避免 CLI 手写第二套 envelope。
- fake provider E2E 覆盖最新期次与 provider unavailable。两者均只 discover 一次、fetch 为 0、staging 不存在、fixture raw 文件树与 SHA 不变。provider 的底层异常原因可能含路径/进程信息，因此跨进程 DTO 只公开 `provider_unavailable=true`，不公开 `provider_reason`。
- 跨 root/版本/导出验收：SourceVersionReader 24 passed；export/location/r4b07 33 passed。M1 合并门覆盖 operation、CLI、gap/acquisition、read chain、复杂度、reader、export、位置切换和版本合同，共 **115 passed in 38.25s**。
- 静态门：修改文件 Ruff 通过；三个新边界模块 strict mypy 通过；`source_operation.py` 从复杂度冻结表移除；`git diff --check` 通过。所有 pytest 使用 `%TEMP%/cw-m1-*` 独立根并清理，没有写生产 raw、catalog、Worker、RF 或其他仓库。
- 测试校正：SQLite 可在只读打开期间改变 `-shm` mtime，因此快照改为目录成员 + 文件大小/内容 SHA，不再把运行时 mtime 当持久数据变化；provider unavailable 红测最初要求公开异常字符串，经合同审查后改为明确禁止公开。

## Session: Phase C / M2 叙述证据分层重构，节点 1（2026-09-27）

- 按 TDD 先增加架构测试，再新增五个小模块：`narrative_document` 持有 `DocumentStructure`/unit/package，`narrative_routing` 持有文档类型、默认预算和空结果策略，`narrative_candidates` 负责单 unit typed assessment，`narrative_context` 负责招股/再融资章节边界，`narrative_budget` 负责原子组与跨页预算。
- `narrative_evidence` 保留兼容 facade；parse result 是 `DocumentStructure` 的同一类型，现有导入无需双轨对象转换。基础候选、章节上下文和预算已经改为调用新层；原件、catalog、Worker 和消费者未接线。
- 新架构红测分别以缺模块失败后转绿。当前合并回归为 **66 passed**（架构、selector、retrieval、复杂度）；五个新模块 strict mypy 和 Ruff 通过，新文件复杂度均不高于 10。
- `narrative_evidence.py` 的最大 custom complexity 从 363 降至 220；M2 尚未完成，仍须拆 PDF context enrichment、相邻/问答补充、locator replay，以及 12 件样本/空间 E2E，故不下调最终 gate、不宣称可投产。

## Session: Phase C / M2-derive 大节点完成（2026-09-28）

- 延续 TDD 拆分，新增 `narrative_group_candidates`、`narrative_neighbors`、`narrative_finalize`、`narrative_pdf_groups` 与 `narrative_replay`。候选组扩展、相邻上下文、去重/预算/封装、PDF 视觉连续组和版本绑定 locator 回放分别归属独立层；`narrative_evidence` 只保留解析兼容面与编排。
- 新增数值坐标排序合同。真实 P06 E2E 首次进入业务断言后发现：预算层曾按 locator 字符串排序，使 `page:161` 排在 `page:3` 前，重复披露保留了后出现位置，导致第 3 页锚点缺失。先加入红测复现 `page:10` 错排在 `page:2` 前，再为 `BudgetItem` 增加显式 `order_key`，locator 只负责回放；真实锚点恢复。
- Windows 默认 pytest 临时路径叠加中文用户名和长 PDF 文件名，首次 E2E 在复制测试夹具前触发路径长度错误；测试 `finally` 已清理。随后统一使用经 `Resolve-Path` 和 `C:\cwt\` containment 校验的短 run root，两个 E2E **2 passed in 102.93s**，结束后精确目录不存在。
- 12 件真实样本覆盖年报、半年报、季报、IPO 招股书、定增/可转债募集说明书、两类投资者关系文件、两份低价值格式文档和两份英文电话会 TXT：业务锚点失败 0，locator 回放 **1,289/1,289**，2 个低价值文档生成跳过收据，原件只读复制且测试树恢复。
- 空间实测：12 件原件合计 **52,196,853 bytes**；selected evidence bundle **549,768 bytes**，为原件的 **1.0533%**。两个跳过文档的 summary input 分别仅 326/331 bytes；没有默认持久化全量 spans。该比例是样本逻辑字节，不含未来数据库索引和文件系统 allocation rounding。
- `narrative_evidence.py` 的最大 custom complexity 已由 363 降至 **10**，从 `FROZEN_MAX` 删除；11 个叙述模块全部纳入 CI/pre-commit mypy。大节点门：相关单元/检索/复杂度 **72 passed**，CI 同款 25 模块 mypy、全范围 Ruff、config doctor、pre-commit config 与 diff check 全绿。
- 节点提交钩子首次显示 mypy `no files to check`，进一步检查发现既有多行 `files` 正则由 YAML folded scalar 插入空格，实际不会匹配。已加 `(?x)` extended mode，并以 `pre-commit run mypy-contract --files .../narrative_evidence.py` 实测钩子执行且通过；不把手工 mypy 绿灯误当成钩子已生效。
- Phase 边界只读复核 RF：本地 `fcap=ee0a82bfd`、`origin/main=3a69f9c5b`，既有 planning/assurance dirty 与一次性目录仍在；本项目未写入、清理或切换 RF。下一步只进入 Phase D provider/transcript adapter，不启动 Worker，不删除原件。

## Session: Phase D / M2-provider 实施细则冻结（2026-09-28）

- 先只读核查现有 `provider_use_policy`、transcript importer/material/CLI、三个合同测试和 E-T 工具边界，没有修改产品代码。确认已有局部 preflight、`/2` import 和内存 fake-provider 测试，但没有 provider 子进程 → CWP stdin importer → 正式 verified reader 的完整链；现有 `/2` E2E 由测试手写结果，另一 fake provider 测试直接操作 staging/writer。
- 新增 [Phase D / M2-provider 实施细则](phase_d_m2_provider_implementation_spec_2026-09-28.md)，冻结六层拆分、D0–D7 TDD 顺序、拒绝矩阵、短路径测试根、空间计量、集中验收和停止条件。company-wiki 不承担 filing + transcript partial-success 编排；跨仓 caller 仍放 Phase F。
- 本阶段目标明确为移除或降至实际 `<=10` 的四项复杂度 freeze：`provider_use_policy.py=38`、`transcript_import.py=41`、`transcript_import_cli.py=23`、`transcript_material.py=19`。不得只迁移巨函数或放宽 ratchet。
- E-T 只读状态为本地 `codex/transcript-companion-adapter`，工具/API/测试仍是未提交文件；`transcript_tool.py` 已是无翻译 JSON 子进程，旧 scraper 有 `--disable-translation`。Phase D 用冻结 JSON schema 的 fake subprocess，不把未提交外仓实现作为生产依赖；正式提交和 filing-fetch 互操作留 Phase F。
- RF 阶段边界只读复核：`fcap=ee0a82bfd1eec935cf4e567eb42f0ef79efa0226`、`origin/main=3a69f9c5b6516ebc949d1c95bd50965f9112b7ad`，原 planning/assurance dirty 与一次性目录仍在。本阶段零写入、零清理、零切换 RF。

## Session: Phase D / M2-provider 大节点完成（2026-09-28）

- D0 基线：现有 provider/transcript 四组测试 **36 passed in 6.36s**。架构 RED 测试按预期 3/3 失败，证明 8 个目标模块未出现、provider policy 仍反向导入 admission/acquisition，四个 38/41/23/19 freeze 仍存在；没有先放宽门禁。
- 依次拆出 `transcript_use_policy`、prefetch admission、postfetch validation、`/2` transport、canonical admission、deterministic text/lineage 和 typed preflight service；原 `transcript_import`、`transcript_material` 缩为兼容 facade，CLI 只保留 bounded transport/组合根。四个旧 freeze 已删除，新模块与 facade 的 custom/Ruff complexity 均 `<=10`。
- TDD 发现并修复一个真实 admission 缺陷：`/2` 的 `canonical_content_sha256/content_bytes` 原先只校验格式，未与 CWP 从 raw 独立重建的文本比较；新增错误 hash/size 负例先失败，随后 admission 在 staging 前重建 material 并比对，拒绝路径无 raw/staging。
- 新增独立 fake provider 子进程，成功链对 HTML/TXT 都执行 discovery → discovery preflight → exact candidate preflight → fetch-candidate `/2` → CWP stdin import → `SourceVersionReader` verified open → transcript selector → locator replay。初轮 RED 先抓到手写 request ID 漂移，再抓到 runtime policy hash 未绑定 catalog，最后抓到测试快照关闭 metadata bridge 导致 period 不可见；均修正 producer/夹具，没有放宽 reader identity/period/hash gate。
- 失败矩阵覆盖 discovery deny、candidate 缺 derive、timeout、坏 JSON、stdout 超限、effective URL redirect、fetch 后 policy 改变和 canonical bytes 漂移。拒绝链 raw=0、sidecar=0、catalog source=0、staging=0；timeout child 被 kill/wait 回收；reader 在 hash 漂移后 fail closed。
- 集中测试：核心合同/架构/复杂度/新 E2E **51 passed in 25.68s**；transcript selector 定向 **3 passed**；Phase C P06/T02 与 12 件真实样本 E2E **2 passed in 118.03s**；E-T 自有 producer 与翻译控制离线测试 **31 passed in 1.95s**。Ruff、12 模块 scoped mypy、config doctor、host-assumption guard 均通过。
- 空间收据：synthetic HTML 为 raw 343 B、sidecar 3131 B、catalog 249856 B、selected 3551 B；TXT 为 raw 266 B、sidecar 3125 B、catalog 249856 B、selected 3551 B。短样本被固定审计元数据主导，selected/raw 分别 10.35/13.35，不作为长文档比率；Phase C 真实 12 件的 1.0533% 仍是主要容量证据。永久逐行 locator 为 0，raw 各一份，第二次 resolve 时 fetch 仍为 1。
- 兼容核对发现真实跨仓阻断：E-T 当前 HTML `/2` 以 provider 提取正文计算 canonical hash/size，而 CWP 以 raw 的确定性全文 material 计算。E-T 自有 fixture 实测 `543 B / 97b5...f2ca`，CWP 为 `570 B / 3cb8...8eb0`，二者不等。Phase F 必须升级 producer contract 或明确传输可验证的派生正文；不得删除 CWP 的独立 hash 校验，也不得宣称 fake provider 已证明真实 E-T 可导入。
- 测试根收据：本轮列出的 13 个 RED/debug/full-chain 根、3 个 D7 根及 1 个 E-T 根均先校验精确名称与 `C:/cwt` 父目录后删除，remaining=0。CWP 未写生产 raw/catalog；RF 保持 `fcap@ee0a82bf` 原 dirty 状态，E-T 保持 `codex/transcript-companion-adapter@1a48f66e` 原 dirty 状态，均未被本项目修改。
- 下一步先编写并单独提交 Phase E / M3 Worker 详细施工卡，再实施；Worker 仍 paused，46 GiB 旧派生仍未删除。

## Session: Phase E / M3 Worker 实施前调查与施工卡冻结（2026-09-28）

- 严格遵守“先计划后实施”：本节只读调查并新增 [Phase E / M3 Worker 详细施工卡](phase_e_m3_worker_implementation_spec_2026-09-28.md)，没有修改 Worker 产品代码、生产 catalog/raw/control、RF 或其他仓库。
- 真实代码核查确认 Automation Worker 的 claim 由三次事务组成；attempt 完成错误地复用 insert-only `put_attempt` 且异常被吞；Effect 未插入即写 Outbox；job/effect/outbox 非原子；无 heartbeat、最新 attempt fencing 或 pause generation。现有 worker tests 只看 job 最终状态，因而会漏掉这些故障。
- 旧 `SourceCatalogWorker.run_cycle` 仍串行 scan→normalize→fingerprint→sections→LLM→export，并包含 `prune_retired_evidence(..., apply=True)`；新并发内核明确只建在 `automation/` 上，旧 Worker 保持 paused，并在 E0/E2 先改为 fail-closed/default-paused 和关闭自动 destructive prune。
- 现有 targeted baseline 在经校验并最终清理的 `C:\cwt\m3-plan-baseline-*` 中运行 150 项，结果 **145 passed / 5 failed**。五项均为 `test_source_catalog_worker::_review_all` 未随 mandatory `evidence_payload` 合同更新；生产 fail-closed 正确，E0 只修 helper，不放松生产 gate。同类 focus-admission helper 一并列入。
- 复杂度只读门发现 11 个既有 C901 超限，旧 `run_cycle=34`。施工卡冻结新函数 `<=10`、不扩张旧函数，并只在 E-A（事务/安全）与 E-B（完整 M3）做集中审查。
- 冻结架构：一个 AutomationStore 队列；Windows spawn 的 compute/model 进程；模型进程固定 1；heartbeat 线程只写 Store；每文档三个 job `select→summarize→verify`；publication 走 effect/outbox 单 writer，避免 ACK 丢失重跑模型。
- 空间取舍：select/summary 中间结果存有上限的 attempt JSON，不生成全量 normalized 或逐页文件；verify 只生成一份内容寻址 canonical JSON bundle；低价值文档只生成小型 skip/coverage bundle。最终使用窄的 immutable `narrative_artifact_versions`，不覆写 legacy `artifacts`，不增加第二全文索引。
- 当前 production control 仍为 `paused` 且 runtime 文件不存在。RF 阶段边界仍为 `fcap@ee0a82bfd`、`origin/main@3a69f9c5`，其既有 planning/assurance dirty 内容未触碰。
- 下一步：单独提交本次纯规划变更；之后从 E0 测试夹具/默认暂停红测开始。E-A 通过前不写 Supervisor/narrative handler，E-B 通过前不建议生产 enable。

## Session: Phase E / E0 可信基线（2026-09-28）

- 计划先以独立 commit `77b1229` 冻结后才改产品。E0 新增 missing/malformed/unknown legacy control 三个 fail-closed 用例，首轮按预期 **3 failed**；`WorkerController._read_control/read_desired_state` 改为缺失或非法时默认 `paused` 后，聚焦集合 **10 passed**。
- 旧 control tests 若确实要启动 Worker，现在必须显式写 `enabled` 或走 `resume`。测试 helper 只在首次构造时显式 opt in，不再依赖生产默认开启；这使 fresh install、控制文件损坏和测试启动意图分开。
- `test_source_catalog_worker` 和 `test_source_catalog_focus_admission` 的 review helper 现在传入与 `evidence_sha256` 对应的 `evidence_payload`。原先五个失败与 focus summary 调度用例均通过；mandatory payload 的生产拒绝逻辑没有更改。
- 扩展 E0 基线覆盖 automation store/worker/migration/controller、operation lock、parser liveness、legacy worker、pause guard、control/bootstrap 和 focus admission，共收集 223 项。首次运行 **222 passed / 1 failed**，唯一失败是 fresh control 后直接调用 `worker-start` 的真实临时 Worker 测试；按新合同在 fixture 显式 enable 后，该项单独重跑通过。未重复运行其余 222 项，因为改动只影响该 fixture 的启动前状态。
- 修改文件 Ruff 与 `git diff --check` 通过；全部 `C:\cwt\m3-e0-*` 测试根清理为 0。生产 `.source_catalog/worker_control.json` 仍为 paused，`worker_runtime.json` 不存在，没有启动生产 Worker。
- 下一步 E1：先增加 Automation DB v2 migration 和原子 claim/heartbeat/finish/reap/effect+outbox 的 RED tests；E-A 之前不实现 Supervisor。
