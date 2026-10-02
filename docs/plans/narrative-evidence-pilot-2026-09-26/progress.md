# Progress：叙述性证据试点

## Session: 恢复实施与 S0a（2026-09-29）

- 用户恢复长目标。先将 CWP 39 个先前未提交源码/测试变更及 CI/pre-commit 已删除 mypy 文件引用修正保存为 `db3ff32`，然后主树返回干净 `master@c5ce72b`；复用独立 `data-lake-reader` worktree 作为唯一 CWP 代码写入目录，主树仅写本计划。原始下载资料未移动或删除。
- ET、FF、RF、StockWiki、IQS 各派只读 S0a 审计；形成 [observed 接口/只读样本表](s0a_observed_interfaces_2026-09-29.md)，不提前把未冻结 WIP 当正式 golden。随后 ET/FF/RF 各在独占仓库开始保全 WIP 与独立 RED；StockWiki/IQS 的施工卡待空闲 slot 派发。
- CWP SourceVersionReader 先改测试，聚焦运行 **3 failed/33 deselected**（预期 RED）：pending proposal、review store 故障、无 review 回执。pytest 路径治理器把 basetemp 重定位到 `cw-pytest-basetemp/20260929-174224-949ba742`；失败后按精确路径检查非 reparse/父路径 containment 并删除，复核不存在。测试 diff 当前只含两份 contract test；无产品实现修改。
- 第一次 P0 产品改动自动审批拒绝：认为全局移除 remediation/prompt-review 阻断过宽。只读检查生产 remediation 表为零、无生产提案创建者、保留实际 SHA/身份/根约束后据此重试，第二次仍被拒绝；不再尝试其它手法，已请求用户对此具体控制明确授权。独立 G-0 与各仓工作继续。
- 只读命令两次 PowerShell 语法问题：Bash 花括号路径列表不可用；`foreach` 表达式需先赋值再接 `ConvertTo-Json`。改用明确文件数组后成功算出七件样本完整 SHA；未改资料。

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

## Session: Phase E / E1 Automation DB v2 与原子 Store（2026-09-28）

- 严格按施工卡先写 RED：第一组迁移/Store/双连接竞争测试收集 20 项，得到 **18 failed / 2 passed**；失败分别指向仍为 schema v1、缺 runtime gate、缺原子 application API。Worker 增量红测得到 **4 failed / 13 passed**，证明旧实现仍组合 `list_jobs/transition_job/put_attempt/put_outbox_entry`、立即把 retry 置 READY 且 paused gate 不生效。多 effect/hash 补充红测再得到 **2 failed / 1 passed**。
- Automation schema 升为 v2：保留冻结 v1 DDL/validator；新库在一个 transaction 内依次应用 v1/v2；合法 v1 可经 backup hook 后升级；DDL/backup 失败不半升级；未来 v3、v1/v2 schema drift、缺 claim index 和缺 singleton gate row 均 fail closed。v2 新增 `attempts.runtime_generation`、`runtime_gate` 和 jobs/attempts/outbox 三组 claim index，初始状态固定 `paused, generation=1`。
- Store 新增原子 claim、heartbeat、finish、promote、reap、outbox claim/ack/retry 和 gate 操作。claim 在一个 `BEGIN IMMEDIATE` 内选择 due/依赖满足的 READY job、写 attempt 并到 RUNNING；finish 在同一事务更新原 attempt，按结果改变 job，并原子写 Effect+Outbox。旧 token、旧 generation、非最新 attempt、完成/过期 lease、暂停后的旧执行者都被具名错误拒绝。
- Outbox projector 合同现在要求 token/generation/lease 匹配、actual hash 与 intended hash 相同；一个 job 的所有 effect 全部 delivered 后才从 VERIFYING 到 SUCCEEDED。达到 retry budget 时 effect FAILED、outbox failed、job DEAD_LETTER 同事务提交。双 AutomationStore 的 job claim 和 outbox claim 竞争各自都只有一个胜者。
- Worker 已重写为薄 orchestration：只读 gate、调用 `claim_next_ready`、在事务外执行 handler、分类 retry/blocked/terminal 后调用 `finish_attempt`；不再吞 claim/finish 错误或重用 insert-only `put_attempt`。retry 保持 RETRY_WAIT 到 `not_before`，reaper 写完 `LEASE_EXPIRED` 后由 promote 单独升 READY。
- 新增/旧 automation 合并门最终共 **193 passed**。修改范围 Ruff、显式 C901 `<=10`、`git diff --check` 通过；pre-commit 的 Ruff、config doctor、host assumption guard 通过。全部 `C:\cwt\m3-e1-*` 根清理为 0。
- production `.source_catalog/worker_control.json` 仍为 paused，`worker_runtime.json` 不存在；未创建/迁移生产 Automation DB，未改 raw/catalog。RF 只读边界仍为 `fcap@ee0a82bf`、`origin/main@3a69f9c5`，保留其既有 planning/assurance dirty 和一次性目录，本项目零写入、零清理、零切换。
- 下一步 E2：先写 DAG materialization、dependency result、missing/corrupt/paused gate、pause/claim/finish 线性化 RED tests；只修改 `automation/scheduler.py`、`automation/runtime_control.py`、controller/planner 与关闭 legacy auto-prune 所需最小边界。E2 完成后统一执行 E-A，不提前写 Supervisor 或 narrative handler。

## Session: Phase E / E2 DAG 与运行闸门；E-A 集中审查（2026-09-28）

- 按冻结施工卡先写 E2 RED tests：DAG 重复物化、payload/job-key 冲突、依赖 result 缺失、terminal predecessor blocked、gate 缺失/损坏、pause/finish race、legacy interlock 和旧 Worker prune。首组为 **12 failed**；新增双向 interlock 审查为 **4 failed / 4 passed**；重复 enable 幂等为 **1 failed**。
- 新增 `automation/scheduler.py`、`automation/runtime_control.py` 和 connection-local `automation/dag_persistence.py`。Controller shadow 不再逐 job 写 DETECTED，而是一次事务写 root READY、downstream PLANNED 和全部 dependency；异常不会留下半个 DAG。
- `promote_ready_jobs` 只接受具有非空成功 `result_json` 的 SUCCEEDED predecessor；cancelled/dead-letter predecessor 会把仍在 PLANNED 的 downstream 标成 `BLOCKED_HUMAN / DEPENDENCY_TERMINAL`，诊断列出 parent job/status。
- runtime control 同时使用 SQLite generation 与 catalog operation lock。AUTO enable 设置 legacy `automation_enabled` 标记；legacy `resume/start/open_session` 读取同一标记并拒绝双开。pause 在锁内更新 AUTO gate、持久 legacy pause、清除标记，锁外停止旧进程；旧 attempt 随 generation 失效。除 fake seam 竞争测试外，真实 `WorkerController` ↔ `AutomationWorkerController` 临时根集成 **2 passed**。
- E-A 首轮 **227 passed** 后没有直接签收：人工审查发现 legacy resume 的单向互斥缺口，补测修复并再跑最终门，结果 **229 passed in 69.23s**。随后全部 automation 单测加 store boundary 回归 **195 passed in 19.14s**；其中两条旧 shadow 测试从过时的 DETECTED 假设更新为 root READY/downstream PLANNED，仍明确禁止 shadow 产生 SUCCEEDED/accepted 决策。DAG SQL 从大 Store 拆到 capability 文件，但 transaction 仍由 Store 管理；修改文件 Ruff 全绿，新 automation 模块 C901 `<=10`，`dag_persistence.py`、`scheduler.py`、`runtime_control.py` strict mypy 通过。
- 旧 `SourceCatalogWorker` 的 retained-evidence 周期任务从 `apply=True` 改为 `apply=False`，并以 cycle timestamp 显式构造 timezone-aware `now`；测试还暴露并修复了原本缺失的 `project_root` fallback 属性。Phase E 没有提供 destructive apply 入口。
- 所有测试位于精确 `C:/cwt/m3-e2-*`、`m3-gate-a*` 根并在 finally 后复核为 0。production legacy control 仍 paused，runtime/automation DB/operation lock 均不存在；未运行 Supervisor、narrative handler 或 production Worker。
- RF 阶段边界只读核对仍为本地 `fcap@ee0a82bf`，保留其既有 planning/assurance/temp dirty 内容；本项目没有修改、清理或切换 RF。下一步为 E3 Supervisor/worker-process 的真 `spawn` 多文档并发。

## Session: Phase E / E3 真正的多进程执行与恢复（2026-09-28）

- TDD 首轮因缺少 `automation.supervisor` 按预期在 collection 阶段失败；随后依次实现 spawn-safe runtime factory、P1/P2/P4 固定拓扑、compute/model job 路由、child-local model client、attempt heartbeat、Supervisor promote/reap/restart loop 和 bounded tail logs。旧 Worker 默认行为保持兼容，17 项原测试持续通过。
- P2 真实 Windows `spawn` 测试让 `source.normalize` 与 `source.analyze` 两个不同 source 的 0.7 秒 handler 执行区间重叠，同时依赖该 normalize 的同 source downstream 只在前置成功并持久化结果后启动。runtime 记录证明 model slot 恰为 1，compute slot 未构造 model client。
- claim 后、handler 中、finish 前三个强杀窗口都留下未完成 attempt；租约过期后 Store 写 `LEASE_EXPIRED`，重启 Supervisor 以第二个 attempt 完成同一 job，没有把 in-memory queue 当恢复依据。active heartbeat 经过原 lease deadline 仍阻止 reaper，child 停止后相同 attempt 可按期限回收。
- 新增父进程强杀真实测试。要求 child 已进入无限等待 handler 后再 terminate Supervisor parent；首轮按预期失败并留下活 child，测试 `finally` 精确清理。加入无状态 parent watchdog 后 child 自退出。合并复跑又发现 watchdog 与主循环同时等待同一个 multiprocessing Event 时，硬杀可能把 semaphore 留在锁定状态并卡住 parent `stop_event.set()`；改为 watchdog 只用本地 sleep + parent handle 检查后，死锁消失。
- 日志 writer 先有 64/512-byte 硬上限；补充 restart 红测发现构造器会清空前次 crash tail，改为保留并裁剪既有 tail。Supervisor normal stop 有界 signal/join/terminate/kill，abrupt parent 由 child watchdog 收口；restart 次数按 slot 有硬上限。
- 最终聚焦 E3 为 **29 passed in 13.79s**；扩大到全部 automation unit、Store 双连接 race、真实 multiprocess 和 store boundary 为 **209 passed in 32.07s**。Ruff 与三个新边界模块 strict mypy 全绿，diff check 无空白错误。
- 全部 `C:/cwt/m3-e3-*` RED/debug/green/regression 根逐一验证父目录和名称后删除，remaining=0。production Worker/control/catalog/raw 未写，真实 LLM 未调用，RF 未改。下一步 E4 先写 handler/context/dependency-result RED tests，再接 Phase C/D 既有组件。

## Session: Phase E / E4 实施前详细设计冻结（2026-09-28）

- 按用户要求先完善计划和实施细则，本轮没有写 E4 产品代码。新增 [E4 Narrative handlers 详细实施规格](phase_e_e4_narrative_handler_implementation_spec_2026-09-28.md)，把 E4 拆成 strict contracts、execution snapshot/context、registry/DAG、reader/PDF bytes、select、summarize、verify/effect、隔离集成八个 TDD slice。
- 冻结 source revision event exact schema 和 canonical input hash；Store 必须在一个只读 snapshot 内验证 gate/generation/token/latest attempt/event/direct dependencies，再由 context factory 构造不可变 `JobExecutionContext`。HandlerExecutor 一次性迁移，不保留 dict 双接口。
- 空间合同进一步收紧：select result 不重复保存 `summary_input` 正文；模型输入从 selected EvidenceSpans 临时构造。Transcript 只保存已选 evidence 对应的 original byte bindings，不保存整份派生文本或全部行图；model 原始响应也只留 hash。
- transcript 权限分三次独立复核：select 要 `derive_text + select_evidence`，summarize 单独要 `generate_summary`，verify 在 effect 前重验所有实际使用过的 action 和当前 policy hash。任何下载阶段许可都不能转移。
- 外发前继续复用现有 prompt-injection review receipt：它是来源内容完整性门，不恢复 public/private 分类。Select 记录与 source/policy 绑定的 review snapshot；summarize 在网络前、verify 在 effect 前重验，缺失或漂移均具名阻断。
- PDF handler 不接 Path：新增 bytes parse/replay facade并与现有 path facade 共用一个内部 parser；verified reader 新增明确的 `narrative_derivation` purpose，继续重验 remediation/read policy/root/source/hash。
- 明确三类 result cap：select 1 MiB、summary 64 KiB、bundle 1.25 MiB、skip bundle 16 KiB；递归拒绝物理路径但允许 page/line/byte locator。verify 只产生一个逻辑 effect，E5 前不写 catalog/object。
- E4 隔离测试统一使用 `C:\cwt\m3-e4-<nonce>`，finally 做 exact-root 校验和清理；E4 结束只跑一次合并门，避免每个 helper 重复大回归。production Worker 保持 paused。
- RF 阶段边界只读复核：仍为 `fcap@ee0a82bfd1ee`、`origin/main@3a69f9c5b651`；既存 planning/assurance/temp dirty 内容未修改、未清理、未切分支。下一步先单独提交计划，再从 E4.1 RED contract tests 开始。

## Session: Phase E / E4.1 strict narrative job contracts（2026-09-28）

- 计划 commit `60c896a` 后才开始产品实现。新增 12 项合同测试；首个 RED 因 `automation.narrative_contracts` 不存在在 collection 失败，首轮实现为 **3 passed / 9 failed**，定位到 selection 计数以无序集合位置传参的真实缺陷。
- 改为字段名显式构造后聚焦测试 **12 passed in 0.64s**；最终加 automation models 回归为 **41 passed in 0.74s**。合同现在严格验证 source revision event、source/ref/policy pin、selected evidence、summary draft、bundle、transcript lineage/action/bindings、依赖间 identity 和四类 byte cap。
- 递归 path-leak gate 拒绝路径 key、drive/UNC/file URI，同时允许 page/line/byte locator 与 HTTPS source URL。Select 结果拒绝 `summary_input`，transcript bindings 必须与 selected evidence ID 精确相等。
- skip 只有 complete coverage + 零 evidence 才成立；summary_not_needed 必须零 model/draft；completed summary 必须同语种、`translate=false` 且 citation/role 通过现有 validator。合同层不调用 Worker、reader、provider/model 或 catalog。
- Ruff、C901 `<=10`、strict mypy 全绿；三次 `C:\cwt\m3-e4-contract-*` 根均精确清理。下一步 E4.2 先写一致性 execution snapshot/context RED tests。

## Session: Phase E / E4.2 consistent execution snapshot（2026-09-28）

- 按计划先写 context/snapshot RED tests；模块缺失时 collection 失败，首轮实现 **11 passed / 2 failed**。失败揭示两个夹具错误：duplicate dependency 已在 snapshot 构造边界被拒绝，以及 malformed payload 夹具同时漂移了 job/event hash。拆分单一风险后聚焦 **13 passed**。
- 新增 `execution_snapshot.py` 与 `execution_context.py`：一个 Store read transaction 绑定 gate generation、完整 claimed job/attempt、event identity 和全部直接 dependency 的最新成功 `HandlerResult`；context 冻结 JSON，按 job type 精确约束 dependency set，并暴露 heartbeat checkpoint。
- Worker/HandlerExecutor 已一次性改为 typed `JobExecutionContext`。Supervisor/multiprocess 首轮 **28 passed / 1 failed**，定位到旧测试 helper 在同一 source revision 为下游新建第二个 event，违反既有 event natural key；helper 改为复用父 event 后 **29 passed**，没有放宽生产唯一性。
- 增加数据库可落库但领域非法的 runtime gate 时间戳用例，验证模型异常统一映射为 `ExecutionSnapshotError`；非法 desired state 本身已经由 SQLite CHECK 在写入边界拒绝。
- 最终节点门覆盖全部 automation unit、双连接 race、真实 multiprocess、CLI、Store boundary 与 E4.1 contracts，共 **244 passed in 42.93s**。strict mypy（4 个边界模块）、Ruff、C901 `<=10`、config doctor、diff check 全绿；独立测试根均清理。
- 此步未接 reader、provider、model 或 catalog，未写 production raw/catalog/runtime。下一步 E4.3 先用 RED tests 将 source revision 唯一映射为 select→summarize、select+summarize→verify 三阶段 DAG，并移除旧 normalize/analyze 映射。

## Session: Phase E / E4.3 registry 与三阶段 DAG（2026-09-28）

- 先改 exact contract tests，RED 为 **9 failed / 14 passed**；全部失败精确落在旧 source specs、旧两阶段 mapping 和缺 network admission，没有无关回归。
- 默认 registry 已删除 `source.normalize/source.analyze`，新增冻结的 select/summarize/verify specs；summarize 同时声明 `llm=True/network=True`，三项 `allowed_paths=()`，error 集合、attempt budget 与 result schema 均按 E4 卡固定。
- source revision DAG 固定为三个 job 与三条 edge；重复 materialize 首次 3/3、再次 0 new + 3/3 existing。controller shadow 验证只有 select 可领取，verify 直接依赖 select 与 summarize。
- Worker 通用单测使用现有非叙述 `timer.execute_step`；multiprocess 拓扑/强杀测试使用 test factory 私有的 `test.compute/test.model` specs。未把假 handler 混入产品 registry，也未提前启用 narrative runtime。
- 聚焦 planner、scheduler、controller、Worker、Supervisor 与真实 multiprocess **70 passed in 25.36s**；registry/planner/CLI strict mypy、Ruff、C901 全绿。下一步 E4.4 先扩展 verified reader 的 `narrative_derivation` purpose，再实现 PDF bytes parse/replay facade。

## Session: Phase E / E4.4 verified reader 与 PDF bytes facade（2026-09-28）

- RED 分成两个独立风险：PDF bytes API 缺失在 collection 失败；reader 新 purpose 为 **2 failed / 23 passed**，准确命中 purpose whitelist 与 remediation gate。
- `SourceVersionReader` 新增 `narrative_derivation` purpose，不接受路径输入，也不返回路径；每次 open/verify 重验 active source、root admission、runtime/read policy、remediation 与 bytes SHA，并在两种结果上返回绑定 source SHA/evidence SHA/review policy 的 review snapshot。
- path 与 bytes PDF facade 共用唯一 `_parse_pdf_document`；bytes 在打开 PyMuPDF stream 前核对 SHA，replay 复用现有 parser-version/table-page/roundtrip-key 规则。monkeypatch 所有 Python temp/write API 的测试仍绿，证明应用层不落临时 PDF。
- PDF/narrative **37 passed**，reader contract **25 passed**，reader/export 直接消费者与真实 bytes E2E **41 passed**；strict mypy、Ruff、PDF C901 `<=10`、complexity ratchet 全绿。`source_reader.py` 已加入 CI/pre-commit strict mypy 并用 targeted hook 实测。
- 没有打开 production raw、没有新增 normalized artifact 或 catalog 写入。下一步 E4.5 先为 PDF/TXT select handler 写 success/skip/incomplete/parser/policy/checkpoint/result-cap RED tests。

## Session: Phase E / E4.5 selective narrative handler（2026-09-28）

- 按冻结规格先建 handler tests；模块缺失在 collection 失败，首轮实现后 15 项通过。再补 selected-only transcript binding、policy revoke 与损坏 PDF；后者先以未捕获 PyMuPDF `FileDataError` 红灯（1 failed / 16 passed），窄映射后 **17 passed**。
- 新 `NarrativeSelectHandler` 仅从 `JobExecutionContext` 与 verified bytes 工作。PDF 在内存选择；transcript 原件经 deterministic material 后只保留被选 evidence 对应的原始 byte ranges。没有路径参数、全文副本、`summary_input`、DB/catalog 写入或 effect。
- 年报、招股书、IR、TXT/HTML 电话会、完整低价值 skip、parser incomplete、缺逐动作授权、policy revoke、source/read-policy/metadata drift、cap/path leak 全部有显式测试。handler 重新计算 opened bytes SHA；损坏但 hash 正确的 PDF 进入 `PARSER_INCOMPLETE/BLOCKED_HUMAN`。
- strict mypy 纳入 8 个 E4 automation boundary 模块后发现 summary contract 的三个 Literal 参数未收窄。新增运行时值域负例先得到 2 failed / 1 passed，再同时加入显式集合校验和类型收窄，避免非法 `investment_conclusion`、`guaranteed` 或 `accepted` 值进入合同。
- 最终直接依赖组合门 **97 passed in 1.64s**；mypy hook 检查 46 个模块通过，Ruff 与 C901 全绿。所有 `C:\cwt\m3-e4-select-*` / `m3-e4-contract-*` 本轮测试根均由 `finally` 清理。下一步 E4.6 先写 replay/skip/language/prompt-review/model-error/transcript-summary-policy RED tests。

## Session: Phase E / E4.6 selected-only summarize handler（2026-09-28）

- 先写 18 项 handler RED tests，因模型边界模块不存在在 collection 失败。首轮实现后 2 failed / 16 passed；失败均为测试夹具误用了正式 locator/binding schema，修正夹具后 18 passed，没有放宽生产合同。
- 新 `narrative_model.py` 冻结无 SDK 的窄 port：canonical instruction/data request、128 KiB transport cap、严格 UTF-8 JSON、duplicate-key rejection、prompt version 和响应 SHA。`narrative_summarize.py` 只消费 select dependency，不读路径/全文、不写 DB/catalog/effect。
- replay 同输入 byte-identical；skip 不调用 model/review/provider。zh/en/mixed 保持语言且 `translate=false`。缺模型、缺/漂移审核票据、429/timeout、非法响应、错误 citation/role/locator 状态与 transcript `generate_summary` 权限分别映射到冻结错误码。
- 扩展攻击面加入 duplicate JSON、超 transport cap、model path leak、provider hash drift 与 revoke，handler suite 为 **23 passed**。直接依赖组合门 **118 passed in 2.08s**；strict mypy、Ruff、C901 全绿，新增模块已进入 CI/pre-commit 范围。
- 模型原始 response bytes 仅在单次执行内存存在，持久结果只含 response SHA 和最小模型身份。每个 transient handler attempt 只调用一次模型，重试总量由 registry `default_max_attempts=3` 与 durable Worker 控制。下一步 E4.7 先写全 locator replay、依赖漂移、post-model revoke/review drift、canonical bundle/effect idempotency RED tests。

## Session: Phase E / E4.7 locator replay 与 effect intent（2026-09-28）

- verify RED suite 先因模块缺失在 collection 失败。首轮实现连同 select source-guard regression 为 2 failed / 26 passed；两项分别是测试直接 canonicalize frozen MappingProxy、低价值 fixture 未执行 select 的 deferred-table completion。修正测试建模后为 28 passed，补 missing current review 后最终 **29 passed**。
- 新共享 `narrative_source_guard.py` 将 source ref、实际 bytes SHA、read-policy、metadata 和 review snapshot 绑定从 select 中抽出，verify 复用同一端口；handler 仍看不到物理路径或 root。
- verify 对 PDF 全量 bytes locator replay；对 transcript 重建 material 并核 original lineage、span line range、每个 byte range 与 speaker-block roundtrip。post-model prompt review 缺失/漂移和 provider revoke/hash drift 均发生在 effect 前，失败结果零 effect。
- 成功 bundle 保留 selected evidence、validated summary、最小 lineage/versions/current action evidence；普通与 skip cap 均通过。每次成功只返回一个 deterministic `PENDING` effect，logical URN target 无 slash/backslash，after hash 等于 canonical bundle hash，无 ArtifactRef、无 catalog/object 写入。
- 直接依赖组合门覆盖三 handler、strict contracts、PDF parser/replay、provider/material 和 verified reader，共 **157 passed in 7.37s**；strict mypy hook、Ruff、C901 全绿。下一步 E4.8 在隔离 catalog/Automation DB 中注册真实 handler factory，验证 DAG dependency snapshot、outbox pending、幂等与故障路径。

## Session: Phase E / E4.8 隔离端到端与合并门（2026-09-28）

- 按先 RED 后 GREEN 建立 E4.8 隔离链。缺失 `narrative_runtime` 时 collection 失败；实现 runtime composition 后暴露两类测试夹具问题：transcript 文档类型误写为 `earnings_call_transcript`（正式类型为 `investor_call_transcript`），以及文件未按 company_raw 的 `companies/.../raw/` 结构放置。修正为正式 sidecar/目录合同后，运行时集成 **4 passed**。
- `narrative_runtime.py` 显式注入 reader、model、prompt review 与 provider policy；Catalog review 只投影成 strict `PromptReviewValue`。runtime factory 只把三 handler 注册到传入 executor，未在 CLI/production 接线。
- 综合 E4 节点门共 **420 passed in 70.65s**：narrative handlers/contracts、automation unit、Store/runtime races、multiprocess、provider/source reader/transcript contracts。Ruff、C901、strict mypy 通过；config doctor healthy；host assumption guard 新违规为 0；diff check 通过。
- 四种主路径的 E2E 使用隔离 catalog/Automation DB：年报摘要、低价值 IR skip、原始 TXT transcript、model 429/timeout、reader refusal、生成后 provider revoke、重复 materialize 幂等、pending outbox 只留 intent。检查 raw 字节 hash 未变，catalog artifact 数不变；E4 不 apply effect。
- 所有临时基于 `C:\\cwt\\m3-e4-*` 的测试根均已清理（计数 0）。Production Worker 进程未运行，production executor 未注册 narrative runtime；config/raw/catalog 未纳入本次变更。
- 同步记录本轮跨仓审计：company-wiki 当前本地 `master@b33ce932` 已包含 `fcap/r4b03/r4b06/codex-data-lake-reader/codex-transcript-companion` 支线祖先；与当前 `origin/master@f39bd5a` 相比本地 ahead 32、远端独有 0，未推送。StockWiki `master` 与 `codex/source-export-v2-reader` 都为 `f5b8526`、工作树干净，但仓库未配置 remote。RF 仍为 `fcap@ee0a82bf`，工作区存在 11 个 tracked 修改及 355 个 untracked 文件；只做分组核查，未清理或修改。RF untracked 里包含 `.planning/.../execution_runs/` 收据，后续必须先检查 PWF 引用关系再分类处置，不能一律删除。
- 下一步遵循优先级：先把 RF 支线未提交内容逐项映射到 PWF/提交记录并完成并线方案与测试门；本轮不对 RF 作写操作。StockWiki 因本地分支已同提交、工作树干净，不需要额外文件清理。

## Session: Cross-project pathless reader baseline and E2E audit (2026-09-28)

- 复核当前 refs/worktrees 后更正前次状态：company-wiki 主工作树 clean、`master@43c5f4a` 比缓存 `origin/master@f39bd5a` ahead 33，列出的功能支线均为 master 祖先；StockWiki 主工作树不是 clean，reader-v2 linked worktree clean，而当前未提交 `QuickScanStore`/测试由 invest-quick-scan P00/W01 计划明确引用，应保留；RF root 和 reader 专项 worktree 均有未提交工作。
- 按 RF 当前 `codex/revenue-source-reader` WIP 对照 company-wiki `SourceVersionReader` 和 RF 生产 adapter。旧 RF adapter 仍消费 `canonical_path` 并直接导入 company-wiki `artifact_dag`；pathless reader adapter 正在把 source identity/bytes/review 转换为现有 RevenueSourceRecord，不向记录写入物理路径。
- 在 `C:\\cwt\\rf-source-reader-e2e-20260928` 运行 `tests/test_source_preparation_v2_cross_repo.py` 与 `tests/test_source_ref_v2_three_repo_e2e.py`：前者 **1 passed**；后者 **1 failed**，filing-fetch 真实 CLI 不认识 `--source-ref-v2`。失败定位在 FF producer/CLI 合同缺口，未触达 CWP reader；不要在 CWP 侧重复造 reader 或恢复路径耦合 fallback。
- 另跑 RF reader WIP 五个隔离单测/合同/两仓测试文件（reader transport、record projection、source preparation、candidate binding、RF↔CWP），结果 **37 passed in 2.07s**。结合三仓 E2E 的失败，当前唯一已复现的端到端缺口位于 filing-fetch producer，不是 RF→CWP pathless open。
- 阅读 filing-fetch 当前实现：`resolve_filing` 从 company-wiki resolve/ensure 取得结果，`_handle_from_resolution` 深验带 path 的 capture-ready handle，CLI 只输出现有 response wrapper。后续 FF v2 方案必须做显式版本化字段投影、保持 v1 默认兼容、清除嵌套路径字段，同时保留 verified identity/capture/download evidence；测试先写 v1 compatibility 与 v2 no-path/identity negatives，再做三仓真实 CLI E2E。此次未写 FF/RF/StockWiki 文件。
- 测试前已审查夹具：所有 catalog、config、PDF 与损坏/恢复动作均位于 pytest `tmp_path`；下载未授权；`PYTHONDONTWRITEBYTECODE=1` 且禁用 pytest cache。finally 删除该专用 basetemp，复核不存在；测试前后 RF reader WIP、CWP、StockWiki 状态未被本次测试改动。
- 待办门：复核 filing-fetch 的正式 SourceRef candidate producer 合同与实现安排；在其支持 candidate 后重跑三仓 E2E，必须覆盖真实 FF 输出、CWP 当前 read-policy/review/bytes 校验、RF RevenueSourceRecord 校验、无下载/无物理路径泄漏、raw/catalog/file hash 无变化。reader WIP 的 PWF 收据、StockWiki QuickScanStore 与 invest-quick-scan W01 身份 contract 需分别纳入跨项目同步记录。旧预审 detached worktree 的文件缺失/未跟踪 reviewer receipts 暂不清理，待完成来源及活动性分类。

## Session: SourceRef v2 producer integration check (2026-09-28)

- 找到现成 filing-fetch `codex/ff-source-reader-v2-20260927@90771d8` 工作树。该工作树已有 v2 candidate producer、CLI flag 与专门测试；生产 diff 范围较大，包含删除旧 transport 模块/测试，需先做调用者与 v1 兼容审查，暂不合入。
- FF v2 定向测试首次 `20 passed, 2 skipped`，跳过原因是未提供 CWP 源路径；设置 `CWP_V2_CODE_ROOT` 与 `FILING_FETCH_V2_WIKI_SRC` 指向当前 company-wiki 后重跑 **22 passed in 7.72s**，零跳过。独立 pytest basetemp 清理并验证完成。
- RF 三仓隔离 E2E 以真实 FF/CWP/RF 代码重跑，失败点从 FF CLI 参数进入 RF adapter 后移至时间边界：`source capture is outside published <= captured <= as_of`。测试请求 as-of 固定在 `2026-09-27`，实际运行日期为 `2026-09-28`；待核 fixture manifest 与 candidate 的实际日期字段，不能先将它归因为实现或测试，也不得放松生产时序约束。
- 三仓 pytest basetemp `codex-three-repo-source-v2-20260928` 在 finally 中删除且已确认不存在；本次没有改 RF、FF 或 CWP 产品代码，只追加本计划的状态、发现和进度记录。
- 日期诊断：`pytest --showlocals` 确认 `source_manifest.retrieved_at=null`，有效 capture 时间来自 FF candidate 的 `2026-09-28T18:55:58Z`，晚于测试固定的 `as_of_date=2026-09-27`。TEMP 副本只把 as-of 改为 `date.today()`、仍导入实际 RF scripts/FF/CWP 后，三仓 E2E **1 passed in 14.09s**；正式 RF 测试和产品文件均未改，正式测试仍需在对应工作树更新日期 fixture 后复验。
- FF legacy/v2 combined regression **138 passed, 1 skipped, 39 subtests passed in 21.18s**; skip 是既有 production security-master smoke test 因本机 snapshot 缺失。旧 `source_reader_transport` 没有剩余仓内引用；v1 默认仍走 legacy `validate_handle` 与 root-policy hash gate。FF v2 整体 diff 尚待完整 code review，不能只凭定向测试并线。

## Session: Reader WIP plan provenance and RF worktree inventory (2026-09-28)

- 搜索 RF/FF reader worktree 内的 PWF 文件及 RF `.planning` 后，确认这两个 linked worktree 根部的 PWF 是旧通用计划，没有 reader 专项实施收据；RF 的 B10 只记录旧 metadata reader 的限度。reader WIP 的用途、合同、测试和下一步在 company-wiki 的 narrative-evidence 与 R4 rollout 计划中有明确记录，见 `findings.md` 本轮补记及两个计划文件。
- 用 `SourceVersionReader` 的 CodeGraph 符号信息确认 CWP 已有 `query_local`、`describe_version`、`open_version` 等入口；职责是按逻辑版本查找并在使用前校验精确原文字节/当前读取策略，再交给薄消费者。RF WIP 将它投影为 RF 自有 `RevenueSourceRecord`；FF WIP 提供兼容 v1 的显式 v2 候选 CLI，不再要求消费者持有物理 root/path。
- 纠正受限沙箱的 RF Git 误报：沙箱外只读 `git status --porcelain=v1 --untracked-files=all` 实际为 **415 行（11 修改、404 未跟踪、0 删除）**；沙箱内 6,123 行/3,778 删除不得作为恢复或清理依据。个别长路径/权限警告待精确核对。此前 `.tmp-zr408-unit*` 的 681 文件/19.55 MB 每组及 58.65 MB 合计也仅来自受限扫描，撤销可清理量判断；未删除文件。
- 本次没有写入 RF、FF 或 StockWiki 产品/工作树文件，没有删除 RF 测试或证据。后续先按 PWF 卡片和 manifest 对 `.planning/execution_runs` 的删除/新增逐组分类；reader 集成则先审 FF 大 diff、更新 RF 的过期固定日期 fixture，再在原 RF 测试文件上重跑真实 FF→CWP→RF E2E。

## Session: Cross-repository mainline and delivery plan (2026-09-28)

- 使用 RF/FF/ET、StockWiki/IQS 和 CWP 各自 PWF、Git refs/工作树现状及真实局部测试交叉审计；RF 状态计数改用沙箱外只读结果 415（11 M/404 ??/0 D）。确认 RF fcap 和 CWP 旧命名支线均已进入相应主线，而 RF reader、FF SourceRef v2/companion、ET 工具和 StockWiki v2 reader 尚未并主线或尚未实现。StockWiki W01 现行测试 8 passed/10 failed；ET 聚焦 31 passed，FF companion 6 passed；这些局部结果没有被记为跨仓端到端验收。
- 新建 `cross_repo_mainline_and_delivery_plan_2026-09-28.md`，固定 S0/G-0 基线与 R4 多根 reader、ET/FF/RF G-A、StockWiki 基础 G-B 与独立 IQS G2b、CWP 旧链/N1–N3/G-C、派生 G-D 的依赖图、逐步执行卡、单仓提交/并线方式及大节点 TDD/E2E/清理/回退门。同步 `task_plan.md` Phase 24、README、清洁架构总图和 R4 卡的过期状态指针；本次仅修改 company-wiki 规划文件。
- 未修改任何 RF、FF、ET、StockWiki、IQS 源码或 PWF；未合并/推送分支，未读取 API key 内容，未下载或删除原文，未运行生产 Worker/派生清理。现有旧库退役收据原样保留，不把已释放的 37.630 GiB 重计入后续收益。下一轮从 S0 live refs/样本 oracle 与 G-0 的未签项开始，再按已固定 DAG 施工，不临时另定顺序。
- 对新总计划做独立只读审查后补齐：SourceExport v2 producer、StockWiki S5b sync/weekly 实作与发布回路，G-0 scoped A/B 结论，ET `/2` 抽取字节与 CWP material hash 的区分，G1e 取前授权时序、正常文档自动 review、旧 normalized 实际字节核验，以及 G-A latest/gap/close-gap 真链矩阵。同步旧 raw 处置/空间账页首标记本轮 `Rdup=Rskip=0`。`git diff --check` 已通过；尚未运行任何新产品测试，规划文档仍待最终提交。

## Session: S0/G-0 plan correction and CWP baseline (2026-09-28)

- 复查代码与合同测试后发现 CWP 主线已有 `source_export_v2.py`、`source_export_v2_cli.py` 及对应 producer/CLI contract suites。修正总计划和 Phase 24：不重新造 producer；先跑现有测试并补真实样本输出证据，StockWiki reader/CLI 仍是待实现项。
- 复核 RF 当前 HEAD 与根工作树计划，发现 RF 根 PWF §42/dirty implementation 允许 evidence path 缺 hash 时 pending，与用户已经确认的“有 path 必须有有效 hash”冲突。更新总计划为拒绝导入该放宽规则；本仓没有对 RF 做写入。
- 核实本仓当前 HEAD `25aa51b`，相较已知 `origin/master@f39bd5a` ahead 34；工作树仅有总计划修改。下一动作是运行 CWP SourceExport v2、reader、operation 合同测试及真实字节 E2E；具体通过/skip/fail 和测试根恢复状态待补。
- CWP 基线测试在 `C:\cwt\g0-20260928-source-reader` 运行：`test_source_operation_v2.py`、SourceVersionReader unit/CLI、SourceExport v2 producer/CLI contract、`test_source_version_reader_real_bytes.py` 共 **77 passed, 0 skipped in 22.78s**。sandbox 阻止的第一次尝试未执行产品逻辑；按用户此前授权在完整文件系统重跑后通过。finally 后确认唯一测试根不存在。
- 真实字节门覆盖 STAR annual report 的双根同 SHA 查询、完整验 hash、首选位置移动后的 fallback、同尺寸篡改后的 fallback；P06 定增说明书 sidecar 缺完整正式期次/来源，exact query 不复用，preview 仍验原始 SHA，正式 reuse 被拒。测试本身对原始文件 SHA/size/mtime/attributes、测试树快照作前后断言。本轮没改产品源码、没下载或编辑原文。
- G-0 剩余实质缺口：四隔离根、company/dayu/Dropbox 原生布局与 adapter、真实 SourceExport v2 span/locator 回放、旧引用回放、429 页招股说明书资源约束以及独立 B.AR。不能用这 77 项基线代签 G-0；下一步调查能否用现存原件做上述同一大门验收，并将缺失 oracle 逐项列为 hold。

## Session: E5 schema/outbox implementation audit (2026-09-29)

- 继续 E5 前使用 CodeGraph 对照当前源码：`NarrativeVerifyHandler` 已把严格 bundle 放入 attempt result 并产生一个 effect；`AutomationStore.finish_attempt` 原子写 attempt/effect/outbox，claim/ack/retry 已存在，但 `claim_next_outbox` 的调用者只有测试，没有生产分发器，outbox JSON 只含 effect 身份，不含 bundle 正文。因此单独实现 catalog projector 会是无法交付的孤立组件。
- 发现 E5 两份规格互相冲突：Phase E 写 `visible/withdrawn`，worker 并发计划写 `prepared/visible/retired/quarantined`，后者还把物理 `path` 放进 catalog 表。已把 Phase E §3.4 定为唯一 DDL：含 `effect_id` 与逻辑 `object_key`、状态 `prepared/visible/retired/quarantined`；path 只留在 object storage adapter。`artifact_dag.py` 与 legacy generic `artifacts` 不参与新 bundle 发布，避免复用错误职责。
- E5 实施顺序已修正为：attempt result → effect-type 限定的 outbox lease/dispatch → content-addressed object → 短 catalog `prepared` → AUTO ACK → 短 catalog activate；ACK/activate 间退出由按 `effect_id` 对账恢复。projector/reader 只见逻辑键或已校验 bytes，存储 adapter 唯一知物理布局。所有来源/hash/策略和 runtime generation 校验为自动事实，不加人工批准/receipt。
- 再按 L0/L3/L4 依赖方向复核后，projector 与 typed reader 放在 automation 层；`source_catalog/narrative_artifact_store.py` 仅做 bytes/object/SQL port，不认识 Effect/NarrativeBundle，也不 import automation。增加 layering contract test，防止底层 storage 反向依赖 job 合同。
- 本次只改了计划文件，未改产品代码、未运行产品测试，也未接触其他项目或原始财报。下一步先在 CWP 专用代码 worktree 写 E5 单元/恢复测试并确认 RED，再实现 API、object adapter、projector、pathless reader 与 outbox 分发器；Worker 继续 paused。

## Session: 人工权限门简化与回归（2026-09-28）

- 根据用户已经给出的个人项目及外部 LLM 外发授权，移除逐文档人工批准、review 回执门槛、transcript rights-policy 文件/哈希、双阶段预授权与取后政策复核；CLI 收敛为 schema `/2` 的一次精确请求结果导入。无回执不再阻断叙述摘要；Worker 技术失败走自动重试或终态失败。
- 保留可自动判定的数据正确性与运行预算：公司/证券和期次匹配、URL/状态/MIME、原文 SHA 与字节长度、最大 payload、去重、原文不可变、summary schema/引用/locator 回放。它们不要求人工队列，也不将内容标成 private/public。
- 删除未被当前 importer 使用的 provider-rights/admission/preflight 服务链与专属测试；narrative event/select/summary/bundle 合同升到 `/2.0` 并删除 provider-policy 字段，测试确认新版本不需要 policy receipt。通用 `DownloadAuthorization` 仍被 `close_gap` 使用，本轮保留待后续单独评估。
- 两轮回归分别 **127 passed** 和 **95 passed**（共 198 个不同用例，24 个 automation planner 用例重复覆盖）；覆盖 transcript importer/reader/narrative 全链、LLM egress、Worker、focus admission、reader 原文篡改检测、planner/registry 与 observability。全部改动 Python 文件 Ruff clean，`git diff --check` clean。
- 两组测试使用 workspace `.test-tmp` 隔离 basetemp；测试输入只为临时 fixture，未下载或删除生产原文；测试完成后 `.test-tmp` 已删除。Worker 仍按总计划保持 paused，跨仓与生产 Worker 启用须通过相应真实数据大节点 E2E。

## Session: 多余门禁统一清理与并行施工规划（2026-09-29）

- 用户要求先全面清查多余权限、人工签收和复杂合同，形成具体清理方案；完成后由本任务统一协调，按仓库目录独占拆成可交给不同 agent harness 的独立计划。本轮仅做只读审计与规划文档，不改产品代码。
- 已启动 company-wiki、FF/ET/RF、StockWiki/IQS 三个只读审计；当前发现旧历史实施卡与 2026-09-28 自动验收规则存在冲突，且 `close_gap` 的运行策略哈希与自动授权、automation 人工审批模型仍在现行代码中。待核调用图和实际阻断范围后裁定，不按关键词批量删除。
- 三项只读审计均已完成。新建 `gate_and_contract_simplification_2026-09-29.md`，按 P0 真阻断、P1 影子/人工状态、P2 配置/历史文档列代码位置、替换规则与测试；明确保留原文/来源/预算、RF 有路径必有哈希和实际 provider 限制。第一部分为已完成的实施方案，尚未修改六仓产品代码。
- 在清理裁定之后新建 `parallel_harness_orchestration_2026-09-29.md` 和六份仓库独占施工卡。主 agent 唯一写总计划/跨仓测试根；各仓 owner 独自保存 WIP、提交/合并本仓分支并停写；总指挥登记真实 producer golden、协调接口和 G-0/G-A/G-B/G2b/G-C/G-D。S0a 只读 observed 先于派发，S0b 正式 golden 由对应 producer owner 生成；每仓测试包、交接格式和自动验收标准写在各卡。
- 三条只读 QA 发现并修订了重要歧义：CWP `capture_ready` 查询保持 metadata-only，实际 SHA 在 open/verify；review store/pending proposal 不再阻断；LLM 模型网络与采集网络分别限额；ET `/2` 必须 FY+Q 且不含原始 payload 长度，默认 Motley 禁用、fake FMP 成功链；FF/RF v2 测试来自特定 WIP worktree；RF scenario/三仓 closure 两个 CLI 坏证据须非零；IQS 是 schema/校验器而 StockWiki 是身份真实 producer；selected consumer 分配 RF/StockWiki 各仓；G-D 按清理批次实际消费者引用选择前置测试，不加全局身份门。
- 产品代码、其它五仓和生产原文/派生均未由本轮规划改写；未派发 harness 或启动 Worker。规划链接与格式检查结果见本会话最终核对，旧实施目标继续暂停。
- 最终静态核对：19 份本轮涉及的 Markdown（现有入口/状态/测试页 + 新总方案/六卡）相对链接缺失 **0**、行尾空白 **0**；规划目录 `git diff --check` 退出码 **0**。本轮为文档规划，没有运行产品测试；此前未提交的产品/测试 WIP 仍在原工作树，未被本轮重置或合并。

## Session: 恢复实施，CWP P0 与六仓并行交接（2026-09-29）

- 六仓 S0a 只读现场与原件 SHA 记录在 [S0a/S0b 表](s0a_observed_interfaces_2026-09-29.md)。company-wiki 既有 39 文件 WIP 已保存在专用代码分支 `db3ff32`；主树只写 PWF，代码 worktree 独立。
- CWP SourceVersionReader 的 pending-remediation、prompt-review 与 review-store 故障阻断曾有 3 项聚焦 RED；自动审批两次拒绝跨全局安全门的修改后，用户**具体授权**三者降为诊断。改动 `resolver.py/source_reader.py`，保留原文 open/verify 的实际 SHA、身份、期间、root 和配置 epoch。旧 FC701 静态检查误将顶层 `SourceEnsureResult.acquisition` 当作已删的 legacy `metadata_json.acquisition`；只收窄该断言，保留新调用者反例。聚焦批 84 passed，FC701 7 passed，四根原生位置真实 E2E 3 passed，narrative runtime E2E 4 passed。
- 专用 worktree 缺生产 `.source_catalog` 使 commit hook 的旧 config doctor 误失败；TDD 新增 `--structure-only`，仍验真实 YAML/root 结构，生产默认模式仍检实际 catalog。新测试 RED 后 **14 passed**；主树生产 config doctor healthy。`ruff --no-cache`、`git diff --check`、commit hooks 的 Ruff/mypy/config doctor/host guard 全通过。CWP 提交 `d5162e5`，没有跳过 hook。短根 `C:\cwt\config-green-20260929` 与本轮其它精确 pytest 根均已删除并证实不存在；原件未修改。
- ET 唯一 owner 合入本地 main `4924d57`，保留原 WIP 基线，FMP `/2` fake HTTP→serializer/CLI 与 Motley test-only golden 已交；offline 118 passed/2 deselected，merge 后 41 passed，10 个 golden matched。FMP real 200 权益未知。FF owner 两个 WIP 顺序保全，303 passed/4 skipped、FF→CWP 隔离 E2E 15 passed，正式 ET adapter 待黄金样例。RF 独立 worktree `main@8b11b0ce` 已严格补 197 个 scenario hash，closure 0/197 pending，review status 为诊断，待 CWP/FF 正式 golden。
- 用户另开 StockWiki W01 harness，StockWiki 目录由其独占写入；本任务只读观察，避免冲突。当前尚未冻结 CWP SourceRef/SourceExport 的真实 CLI golden，G-0 与后续跨仓门不能据局部测试宣布完成。Worker 仍 paused；没有下载、删除原文或清理生产派生。
- CWP 随后以真实 `source_export_v2_cli` 和自包含文本夹具在专用代码工作树的 `tests/golden/source_v2/` 生成 SourceRef/SourceExport v2 golden；新增测试先因文件不存在 RED，生成后完整 CLI 文件 **5 passed**。四个 JSON 逐字节 SHA 与 commit `c508e8e` 绑定，`.gitattributes` 在 `3dd41e1` 固定 LF，避免 Windows autocrlf 破坏消费者样例。FF/RF owner 已收到路径、SHA、版本；两方独立 RED 已开始。
- 真 P06 四隔离根测试增旧 `SourceRef` 跨根迁移、优选副本同尺寸改字节后的 SHA fallback、四份均改字节后的 `no_verified_location` 拒绝。真 P04 429 页、11,211,796 字节招股书进入流式 verify，无返回全文 data、tracemalloc 峰值小于 8 MiB；P04 内容 SHA 按原 host-neutral guard 登记。G-0 指定 6 文件测试包 **80 passed / 0 skipped in 27.40s**，`ruff`、全部提交 hook 通过，提交 `58e2f21`。每轮隔离 `C:\cwt` 精确测试根均已删除并复核不存在；生产原件 SHA 未变。
- ET 深审发现 FMP 不能仅改 importer：query URL 被旧 policy 和 tool contract 双拒；候选授权的精确 document ID 含响应后才有的 call date；候选 `filing_date` 会被 scanner 写成 `published_date`；JSON 原件和文本换行规范化不符合旧 HTML/plain 相等哈希。真实 FMP canonical admission 维持 hold；FF 先做严格离线 consumer。CWP PDF 原件仅可出 v2 manifest，PDF 页段 locator 留 E5/G-C，已更正 G-0 计划，不以假 PDF span 凑验收。
- RF 本地 `main@8b11b0ce` 已完成 197 个 registry evidence 真 SHA 与两个 CLI 退出码，真实 closure 197/197 exit 0；人工 review 诊断化按用户授权完成。RF reader 旧 WIP 保存在 `3b00b938`，因仍挡 `not_reviewed` 不直接合入；已基于 CWP golden 写 2 项 RED。release-readiness 删除人工授权门的产品补丁遭自动审批拒绝，RF 只保留 4 项 RED 并等用户对此具体项授权，其他独立工作继续。

## Session: StockWiki 独立 reader 派发与 producer golden 校正（2026-09-29）

- StockWiki W01 由独立只读验收确认 `master@5bb68f6`、18/18 SQLite 测试、定向 Ruff 绿；W02/W03 缺 IQS 正式 CLI/真实 identity snapshot，基础来源 reader 不依赖这些输入。用户需要新的其它项目并行线，已写 [独立 reader 施工卡](harness_lanes/stockwiki_source_reader.md)：唯一 StockWiki 写入者、opt-in SourceExport v2/verified-open、先 RED、文本真实 locator 与 P06 PDF manifest E2E、隔离测试根恢复、G-B 总指挥跨仓验收；不分配 IQS、selected/full sync 或其它仓写权限。
- CWP producer `verified_open_bad_sha.json` 的 Windows 工作树曾是 CRLF 86 字节、README 声称其 SHA，但 Git 文本归一化后的提交 blob 是 LF 85 字节。已将 CLI 合同测试改为只归一化错误行换行并将 README 钉到 LF SHA `daed1b192dab90daf50bc2c9a3dc92695009944f51457177374cc77e0d53a0b5`；真实 producer CLI 测试 **6 passed**，Ruff/config doctor/host hook 绿，提交 `codex/narrative-gates-integration@7760b09`。成功 receipt/SourceRef 原有 SHA 不变。StockWiki 新 harness 必须读取该 HEAD 的 README，RF/FF consumer 复制的负例 fixture 要对齐新 LF pin。
- FF owner 已交本地干净 HEAD `5532ce0`，全套 **433 passed, 13 skipped, 78 subtests**，隔离 FF CLI→CWP E2E **15 passed**；FMP canonical admission 和 CWP RequestPlan 尚 hold。RF release-readiness 自动门按用户具体授权完成 `88b3bda3`，定向 13 passed；RF reader 继续独立推进。总指挥尚未把各仓局部绿灯当 G-A/G-B 正式验收。

## Session: StockWiki 下一条独立线与 E5 恢复验证（2026-09-29）

- 用户指出 `stockwiki_source_reader.md` 是刚完成的 SourceExport v2 任务对应施工卡。确认重复推荐属实，已从“新任务”候选中撤下；用户报告该 reader 已完成，G-B 总指挥验收仍等原 owner 的 commit/测试交接，未把用户报告替代为本任务自己的测试收据。
- 检查 StockWiki 当前 `AGENTS.md` 与 `scripts/check_all.sh`：全量 `pytest -q` 先单独运行一次，随后 `coverage run -m pytest -q` 又跑第二次；总 coverage 73%、`stockwiki/ui.py` 40%、Ruff、`validate-framework` 及真实 workspace/data-contract 测试仍有价值。新增[StockWiki 工程测试门简化施工卡](harness_lanes/stockwiki_engineering_gate_simplification.md)，范围仅 StockWiki AGENTS、全量验证脚本和至多一个脚本行为测试；明确保留质量阈值及 `review_workflow.py` accepted/rejected 研究状态。已在[并行总表](parallel_harness_orchestration_2026-09-29.md)引用。此卡只在 reader owner 停写/交接后派发，以满足每仓单一写入者。
- 本轮没有修改 StockWiki 产品仓、RF/IQS/FF/ET；没有启动新的 harness。计划文档 `git diff --check` 通过，Git 提示主计划现有 LF 会在 Windows 下转为 CRLF。
- CWP E5 专用 worktree 的受影响回归包含 automation store/atomicity/worker、outbox 重领和 fencing、artifact store、layering contract 与真实 narrative runtime E2E：**84 passed in 10.08s**。此批用例检查正常 ACK 后仍能重建原始 effect result，及 ACK→activate 中断后的 prepared-artifact reconcile；Worker 仍 paused，测试不接触 production raw/catalog。E5 仍未完成，继续实现/验收前不启动生产 Worker。

## Session: E5 outbox projection 与 pause fencing（2026-09-29）

- 在 CWP E5 专用 worktree 把 `narrative_artifact_versions` 作为 additive 表实现，object adapter 以 content SHA 写不可覆盖的 JSON bundle；`prepare` 先验来源仍为当前 active primary、在 catalog lock 外落对象，再短事务登记 `prepared`。同 work key/hash 重试复用既有对象；不一致内容冲突。automation 层 dispatcher 只接 `narrative_bundle.publish`，按 effect id 精确恢复成功 attempt result、重算 bundle hash、ACK 后激活；reader 只返回 visible、当前 source SHA 匹配且 bytes/schema 均重验的 bundle，不泄漏物理 object path。
- 原 E5 E2E 首先暴露 ACK 完成后 `result_for_effect()` 与当前已转为 VERIFIED 的 effect 比较会误拒；增加回归并修复为比对不可变 effect 身份，同时核对当前 VERIFIED 状态/hash。
- 对照冻结 E5 规格又发现 ACK 与 catalog activate 之间缺少 pause 的线性化边界。先加入真实隔离 PDF/TXT runtime E2E 作为 RED：暂停成功后 event order 为 `paused → visible`，证明原实现会在 pause 返回后继续使 bundle 可见。实现层在 activate/reconcile 共用 `CatalogOperationLock`，先重验 enabled gate/generation 和 AUTO effect verified/hash；pause 获胜时 artifact 留在 prepared、paused reconciliation 不激活，恢复 enabled 后才激活。RED 已转绿，E2E 也继续验证正常 dispatch、ACK 后模拟崩溃恢复与 pathless read。
- 最终受影响批包括 automation store/atomic/worker、store race、narrative runtime E2E、outbox/artifact store 和 layering contract：**84 passed in 7.34s**；触及 Python 文件 Ruff 全绿，`git diff --check` 通过。一次中间 RED 因测试把 domain `Event` 名与 threading event 冲突，改用 `ThreadEvent` 后得到目标竞态 RED；无产品变更基线未被覆盖。
- 代码仍在专用 worktree 未提交；未接入生产 runtime composition、未运行完整 E6/E7 故障/吞吐矩阵、未启用 Worker。按 spec 将实际模块/测试名同步到 E5 施工卡，下一步继续验证运行时 dispatcher 接线及 E6/E7 真实数据/恢复矩阵；旧 raw/catalog 未触碰。
## 2026-09-29 — E6 continuation: live worktree and cross-project boundary recheck

- Re-read live state before resuming the next implementation phase. CWP planning root is `master@b9f38d9` with active planning edits; the dedicated code worktree is `codex/narrative-gates-integration@5bcb337` and still contains the E5 automation/catalog changes plus the new E6 spawn-safe runtime fixture. No production raw/catalog state was changed.
- Fresh read-only RF check: `fcap@ee0a82bf` remains the live head and has substantial uncommitted planning, code, test, and generated execution-run state. No RF files were changed. The current E6 work exercises only the CWP Worker and isolated CWP catalog; RF selected-package consumption remains a later cross-project gate and is not being inferred from this local E2E.
- E5's most recent affected regression receipt remains **84 passed** after pause/activation fencing; E5 is still uncommitted and not connected to production composition. Production Worker remains paused.
- Next action: finish the isolated P01/P04/P07/T01 plus low-value skip E6 runtime test, exercising actual P1 and P2 supervisor processes; record raw hashes, locator replay, outbox/pathless read, idempotent rerun, concurrency/order and ≤3% object/raw byte ratio. Keep all writes under a fresh `C:\cwt\m3-e2e-<nonce>` test root and remove only that exact root afterward.

## 2026-09-29 — E6 input freeze and test-shape correction

- Corrected the E6 specification to make the executable cohort explicit: four frozen real sources plus one synthetic `ir_policy` control, run in separate P1 and P2 catalog/AUTO roots. The real-source storage ratio is measured independently from the skip bundle.
- Rehashed each live sample before the test: P01 `d64c4108…` / 9,165,875 B; P04 `19cdb41e…` / 11,211,796 B; P07 `221467c1…` / 153,851 B; T01 `4ac3b4f0…` / 66,324 B. `C:\cwt` exists and has no current `m3-e2e-*` root.
- Confirmed existing route test/implementation contract for the exact low-value IR policy title; it requires complete PDF coverage to skip and has no selected spans. E6 will additionally assert skip produces no model call.
- No production data was read through the production catalog or written. Next: implement the opt-in E6 real-sample supervisor test and change the lifecycle trace from `attempt_finished` to `before_finish`.

## 2026-09-30 — StockWiki lanes integration plan ready for handoff

- Rechecked StockWiki refs/worktrees read-only. Local `master@8590b0e` does not contain the completed reader `codex/source-export-v2-reader@0b40683` or identity snapshot/mapping `codex/identity-snapshot-w02-w03@ae11135`; both source worktrees are clean and their changed-file lists do not overlap. StockWiki root contains untracked `.claude/`, which the new card explicitly preserves.
- Read the IQS G2b handoff and StockWiki serializer/store code. W02/W03 produces a real snapshot with scope-attestation IDs and source bindings, but the owner identity-receipt and market-registry records required by IQS are not available from the current persistent model/public snapshot. G2b must remain pending; do not synthesize trust records.
- Created [StockWiki mainline integration card](harness_lanes/stockwiki_mainline_integration.md): one StockWiki-only integration worktree, normal merges of the two completed branches, focused reader/identity/QuickScanStore regression, one `bash scripts/check_all.sh` major gate, preserve source worktrees and unrelated files. Updated lane status pointers, orchestration table and this plan's next step so completed implementation cards are not dispatched again.
- This session changed only company-wiki planning documents. No StockWiki product code, CWP E5/E6 code, IQS files, raw documents, or production derived data were changed; no product tests were run.

## 2026-09-30 — E5/E6 commits and StockWiki mainline integration receipt

- E5 was committed in the dedicated CWP code worktree as `05756d3` (`feat: publish narrative artifacts with recoverable outbox`). The affected E5 regression remains **84 passed, 1 skipped**; production Worker/runtime composition remains paused/not enabled.
- E6 first measured **731,345 / 20,597,846 bytes = 3.55%** with the prior selector defaults (160 standard spans / 320 prospectus spans). The real P01/P04 sample showed that reducing limits to **96 standard spans** and **160 prospectus/offering spans** preserves the tested narrative topics while meeting the planned 3% profile budget. P01 still covers new business, R&D/products, capacity, orders/customers, core business and industry dynamics; P04 still covers new business, R&D/products, capacity, orders/customers, core business and overseas expansion.
- E6 now runs opt-in against frozen P01 annual report, P04 prospectus, P07 investor-relations PDF, T01 transcript TXT and the low-value skip control, with P1/P2 isolated catalogs/AUTO DBs. Real sample E2E **1 passed in 165.34s** after the portable-path correction; it proves different-source overlap in P2, no overlap in P1, locator replay, no duplicate logical artifacts on rerun, exact byte/hash preservation, ≤3% object/raw ratio for both profiles, zero model call for skip, production fingerprint unchanged, and the configured test root restored. Selector/host-guard affected tests were **49 passed**; Ruff and host-assumption guard passed. Initial commit hook caught host paths and unregistered real-byte digests; paths were made repository/env-relative and three content-only hashes registered with rationales, then all hooks passed.
- E6 was committed as `c839baf` (`test: validate narrative selection and worker concurrency`), following the existing E5 commit in the dedicated worktree. No production raw, catalog, config or Worker state changed; the worker remains paused. E7 crash/lost-response/restart/throughput matrix and E-B remain the next CWP milestones.
- User reported StockWiki's independent mainline-integration task complete. Read-only verification confirmed local `master@c8cfb2e7`, a normal merge containing reader `0b40683` and identity W02/W03 `ae11135`; the focused suite has 99 passed/0 skipped and the single `bash scripts/check_all.sh` gate records 598 passed/exit 0, Ruff clean, coverage ≥73%, `ui.py` 75%, and validate-framework 0 errors. Source branches/worktrees are present and clean; `.claude/` is the only root untracked item and remains untouched. The [integration card](harness_lanes/stockwiki_mainline_integration.md), [orchestration table](parallel_harness_orchestration_2026-09-29.md), and task plan now mark this lane complete.
- Basic StockWiki G-B later passed in the total coordinator's real CWP producer→verified-open→StockWiki reader E2E; see the follow-up receipt below. G2b remains pending because the actual owner identity receipt / market-registry projection is not yet available.

## 2026-09-30 — G-B E2E receipt and independent StockWiki W04

- Ran StockWiki `tests/e2e/test_cwp_source_export_v2.py` with the real CWP checkout and isolated test catalogs: **3 passed in 11.37s**. Covered synthetic Unicode locator replay, exact manifest/version refusal, real P06 prospectus PDF+sidecar manifest/SHA, and same-SHA multi-root identity stability.
- Ran CWP `tests/e2e/test_source_version_reader_real_bytes.py::test_real_p06_four_root_export_is_independent_of_root_names_and_priority`: **1 passed in 1.47s**. Four isolated copies of real P06 preserved logical identity across roots/priorities; same-size corruption fell back to a verified copy; all corrupted copies returned named unavailable. The test checked original bytes and cleanup of its temporary roots.
- This closes **basic SourceExport G-B only**. Selected narrative G-C and IQS G2b remain separate; the latter still needs an owner receipt and a source-backed ISO MIC registry projection in StockWiki's public request.
- Read-only owner-state check: StockWiki `master@c8cfb2e7` has no tracked changes; IQS has active Q03 documentation edits, RF has extensive active local work, FF has multiple active worktrees, and ET's exact-period/provider-gate task is already implemented. Do not open second writers in those repositories.
- Created [StockWiki W04 owner-context producer card](harness_lanes/stockwiki_g2b_owner_context.md) as a larger independent product task. It writes only StockWiki, uses a separate worktree from this CWP E7 line, and includes owner receipt persistence/read API, versioned official ISO 10383 CSV projection, exact Entity request export, real-source canary, IQS public CLI positive/negative E2E, one full StockWiki quality gate, production DB immutability and test-root restoration.
- Updated orchestration/current status links so W02/W03 and SourceExport reader cards are not redispatched. The W04 work is planned only; no StockWiki product files or production databases were changed in this session.

## 2026-09-30 — W04 delivery acceptance

- Read-only verified StockWiki `master@72531b598dcd80325e55e1e70527b7afb89b163f`, merge of W04 `8bee364` and reader size split `6f0c2c4`; `.claude/` stayed untouched. IQS main is clean at `65e96ba`.
- Ran StockWiki W04 package: **64 passed**. Ran `bash scripts/check_all.sh` at merged HEAD once with `PYTEST_ADDOPTS` pointed to a forward-slash AppData temp path: **651 passed, 15 skipped**, Ruff clean, coverage gates pass, validate-framework 0 errors (11 existing warnings). The first full-suite invocation had only a malformed basetemp path due backslash parsing; it produced fixture setup errors and was rerun correctly.
- Ran the actual cross-repo E2E from StockWiki public exporter to current IQS public CLI: positive request exit 0/status valid, all 17 single-field negatives exit 2. The E2E checks production `data/` snapshot equality; our temporary acceptance/full-suite roots, coverage artifact and Ruff cache are removed. Full test git status remains `master` plus the pre-existing `.claude/` only.
- W04 implementation is merged and the current G2b happy/negative path passed. Full card signoff remains pending the explicitly promised wire golden SHA assertion/reviewable golden, parser OPRT/SGMT parent relation negatives, and stable expected error codes per mutation. Details are in [the lane card](harness_lanes/stockwiki_g2b_owner_context.md). CWP E7 test work remains in its separate worktree; RF and other repositories were not modified.

## 2026-09-30 — E7 recovery matrix and real-sample P1/P2 profile

- In the dedicated `codex/narrative-gates-integration@c839baf` worktree, R01 same-job claim race and R04 expired-attempt fencing each passed three repetitions; R09 lost model response/retry/no duplicate visible bundle and R11 34-document/102-job restart recovery also passed. Combined focused run: **8 passed in 37.37s**.
- The isolated synthetic bounded profile test passed once: six interleaved 45-job trials (two each at P1/P2/P4). Median wall time was 15.31s / 10.91s / 6.65s; it supports process overlap under a short deterministic handler but has no real catalog lock contention and does not establish real-document performance.
- Re-ran the opt-in E6 real cohort with explicit project/company/transcript roots because the worktree is not laid out beside `earnings-transcripts`. The instrumented test passed **1/1 in 94.23s**. P1 vs P2 wall time: 45.07s vs 48.13s; throughput 319.5 vs 299.2 narrative docs/hour; p95 queue wait 37.66s vs 39.79s; p95 handler 19.78s vs 22.18s; process-tree peak RSS 360.9 vs 440.7 MiB. Each profile emitted 419,428 B selected objects from 20,597,846 B input (2.04%), used a 1,011,712 B automation DB with zero WAL, zero retry and zero SQLite busy errors. Busy-wait p95/catalog-lock wait were explicitly unmeasured.
- This single replay-model pair does not generalize to a live LLM or the full corpus, but it fails the pre-set 25% P2 improvement criterion and shows higher P2 memory. Keep Worker paused/default-off and use P1 as the conservative isolated baseline; do not infer P2/P4 benefit from the synthetic benchmark. Both temporary E6 bases were removed and checked absent; the test asserted raw hashes, production fingerprint and test-root contents unchanged.

## 2026-09-30 — W04 final parser and cross-repo acceptance

- In isolated StockWiki worktree based on `72531b5`, wrote the MIC relationship RED tests first: blank Operating MIC, missing parent, non-self-referencing OPRT, and a cycle all passed the old parser. Implemented deterministic parent resolution and added accepted nested SGMT-chain and cross-market-parent cases.
- Official ISO CSV canary SHA `79de0f7704e260bd49b0d2439f3084891cabc93481da8bdbaa716e15a27211ed` parsed all 2,883 rows across 149 jurisdictions, including 8 nested SGMT links and 2 cross-market links. This rules out the overly strict alternative of requiring every SGMT to point directly to OPRT or to share its country.
- Follow-up commit `afa9692` was merged into StockWiki `master` as `b4f3846bb3e331f5661edee974a7d0b76dbf9664`. Focused parser/identity/G2b/SourceExport tests passed **57/57**; merged `check_all.sh` passed **686 tests**, Ruff clean, coverage floors passed, and validate-framework reported zero errors with 11 existing content warnings.
- IQS owner receipt now pins the canonical request golden SHA. The 17 public CLI one-field negatives remain rejected with the stable shared code `semantic_validation_failed`; separate per-mutation code names are optional diagnostic detail, not a W04 blocker. No IQS code was edited.
- Removed the exact temporary CSV and pytest/coverage/Ruff roots after verifying paths and the CSV digest; all are absent. StockWiki production `data/`, CWP raw files, and pre-existing `.claude/` were not modified. Per the user, this W04 acceptance is the end of the current work; the broader implementation plan is paused.

## 2026-10-01 — E-B centralized test acceptance and repository branch audit

- CWP E-B ran in the dedicated `codex/narrative-gates-integration` worktree. The broad focused regression passed **404 tests, 2 skipped, 695 deselected** in 82.95 seconds with `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`. A default Windows code-page run hit a pytest capture/child-process encoding error during R11 teardown; R11 alone and the R07→R08→R11 sequence passed, and the UTF-8 parent/child environment made the broad regression pass.
- Added process-level R05 pause-vs-finish and R07 ACK-then-exit/recovery repetitions (3 each), plus R08 using a real `CatalogOperationLock` held during publication. AUTO ACK remained durable while the artifact stayed prepared/invisible; after lock release, reconciliation exposed exactly one visible version. These targeted cases passed.
- E-B test changes were committed as `cba745a` (`test: harden worker integration recovery coverage`); the commit changes only two integration test files and one unit test file. Pre-commit and commit hooks passed Ruff, config doctor and host guard; scoped mypy was skipped because the staged changes were tests only.
- Latest E6 four-document replay: P1 90.14 s / 159.8 narrative docs per hour / 401,235,968 B peak RSS; P2 84.776 s / 169.9 docs per hour / 495,566,848 B peak RSS. P2 improved wall time 5.95% and throughput about 6.3%, with about 23.5% higher peak RSS. Both emitted 419,428 B selected objects from 20,597,846 B raw input (2.04%); 1,441 B skip artifact; five visible records; four model calls; zero retries/busy errors; database about 1.0 MB; WAL 0. Catalog lock wait and SQLite busy-wait p95 remain unmeasured.
- E-B is **not integrated into CWP master**. `master@b0fd763` and the dedicated branch have 9 and 13 commits unique to each side, with a 77-file diff. Do not merge the branch wholesale; reconcile its commits and files against current master first.
- Read-only cross-repository ancestry snapshot: StockWiki W02/W03, SourceExport reader, W04 and G2b owner-context branch tips are ancestors of local `master@b4f3846`; ET transcript companion tip equals local `main@4924d57` (local main is six commits ahead of origin). CWP transcript-companion/fcap/r4b06 tips are ancestors of local `master@b0fd763`; CWP narrative-gates E-B is the divergent branch above, and CWP master is 44 commits ahead of `origin/master`. RF `fcap@ee0a82bf` is an ancestor of local `main@415d8eb3`, but `codex/revenue-source-reader` has one branch-only commit; complete-permission read-only status is 12 tracked changes and 404 untracked paths at the RF fcap root. The separate RF main and reader worktrees are clean. FF local `main@c9799b7` does not contain its fcap/source-reader/transcript-companion branch tips (39/41/45 branch-only commits respectively); those worktrees are clean, while FF root has one untracked path whose name/content was not inspected. IQS local `master@091999d` is clean with no unmerged local branch tips. These are local ref relationships; they do not assert that remotes are synchronized.
- Production Worker remains paused. No runtime worker JSON, automation DB or operation lock was present. Exact test roots created for this run were checked absent after cleanup; production raw documents were not modified.
- A read-only CWP audit found 87 untracked files under `.pytest-e7-*` roots, all generated DB/JSON/signal outputs from R01/R04 test reruns. Verified all four exact roots were inside the CWP repository with no reparse points, removed only those roots, then verified all four paths absent and zero untracked CWP files remaining. No source, plan, or raw document was included in cleanup.

## 2026-10-01 — RF audit interface and strict evidence-hash contract

- Confirmed the RF read-only audit card defines its sole report path, report schema, start/end immutability checks, RF no-write boundary, and stop condition for incomplete filesystem visibility. The report is not present yet; no audit completion is inferred.
- Reproduced that uncommitted RF `fcap` closure logic returns ready for a nonexistent evidence path paired with a malformed fixture hash. Its 11 passing tests omit this invariant. The mainline implementation rejects missing, malformed, and mismatched hashes and accepts a matching SHA; its focused 16-test suite passes. This confirms a contract regression in the dirty proposal despite its local test result.
- No RF files were changed. Integration must retain the selected invariant “evidence path requires valid matching hash”; add a direct regression before accepting any RF closure changes. The isolated temporary mainline fixture was removed.

## 2026-10-01 — RF closure hash 规则更新与验收

- 用户将先前“有 evidence path 必须有 hash”的规则放宽：路径解析到 RF 仓库内真实可读普通文件时，缺失或空白 `fixture_hash` 仅增加 `evidence_hash_pending` 诊断，不阻断 `closure_ready`。保留仓库边界、文件存在和可读性校验；若记录 hash，仍要求合法 SHA-256 并匹配当前文件字节；错误路径或错误/不匹配 hash 仍阻断。
- 在 RF main `415d8eb3` 上先补 RED：缺 hash+真实文件预期 ready、缺 hash+不存在路径仍 fail、closure summary 保留 pending 且 registry 不变。随后修改 `scenarios.py`，未照搬 fcap 代码中不检查无 hash 路径且会修改输入对象的问题；四文件提交为 RF main `3e03ce83`，工作树干净。
- 真实 `tmp_path` 字节夹具的 scenario、三仓 closure 与双 CLI 定向测试 **33 passed**；覆盖已有错误 hash、坏路径拒绝和缺 hash 正例。另对 RF main 真实 registry 做只读核验：197 项当前全 ready；内存中移除 AR-01 hash、保留实际路径后仍 ready、pending=1，registry SHA 不变。全目录测试被 `test_freeze_exclusive_and_cas` 派生的 CodeGraph `prepare_source` 子进程挂住，未据此记为全套通过；确认进程属于本轮后结束它，并删除本轮 pytest-7046/7047/7048 三个独立临时根，验证它们已不存在。
## 2026-10-01 — CWP E-B 与当前主线整合验收

- 在 `codex/narrative-mainline-integration` 上，以当前 CWP `master@11b6472` 为基线，将已验收 E-B 分支 `codex/narrative-gates-integration@cba745a` 做无快进合并。两处计划文档冲突采用较新的主线版本；未合并其他仓库文件。
- 合并后的 29 个变更测试文件回归 **349 passed、2 skipped**；SourceExport v2 CLI 专项 **6 passed**；真实字节及 transcript E2E **11 passed**。修复并覆盖 Windows stdout/stderr 将协议 LF 写成 CRLF 的问题。
- Ruff 对 56 个变更 Python 文件通过，暂存/未暂存 `git diff --check` 均通过，无 unmerged paths。所有本轮创建的 `C:\cwt` 和 pytest 临时目录均经存在性核查后确认已清理。
- 集成已提交为 `9e73eb4 Merge narrative evidence gates into mainline` 并 fast-forward 到 CWP `master`；当前 master 比 `origin/master` 超前 61 个提交，本轮没有 push。E-B 测试通过不代表 Worker 已启用；生产 Worker 继续 paused/default-off，G-C selected-package consumer 与 G-D 批处理/撤回验收仍待做。

## 2026-10-01 — 六仓 live refs 与 PWF 计划对照

- 本轮只读核对 CWP、revenue-forecast、filing-fetch、earnings-transcripts、StockWiki、invest-quick-scan 的 HEAD、分支/worktree 和各自最新可读计划/交接收据；只在 CWP 本计划目录记录结果。未读取 API key 或其他凭据，未修改/清理任何外仓。
- CWP：`master@00af53f`、`origin/master` 前 62；E-B merge `9e73eb4` 已进入主线，合并后相关回归 349 passed/2 skipped，56 个变更 Python 文件 Ruff 通过。与 Phase 32 首次快照相比，ahead 计数从 61 增至 62。当前可见 Git 输出仍提示 `.pytest_cache` 权限不可见；因此只报告可见状态，不宣称未忽略文件完全 clean。
- StockWiki：`master@b4f3846`，`.claude/` 是既有未跟踪本地路径。W02/W03、SourceExport reader、G2b owner-context、W04 MIC 分支共六个已知 branch tips 全部是 master 祖先（`master...branch` 计数分别为 15/0、11/0、6/0、21/0、8/0、6/0）；整仓门 686 passed。旧 worktree 没有独有提交；本轮保留，不为“整理”而删除。
- RF：正式仓 `rf-impl main@3e03ce83` 干净、ahead origin 4；`fcap@ee0a82bf` 已提交历史为该 main 的祖先。用户放宽后的缺失 `fixture_hash` pending 规则已在 main 提交，相关 unit/integration/CLI 回归 33 项通过；raw `SourceRef` 字节 SHA 仍严格验证。另一个 `revenue-forecast` fcap 工作树仍有大量 dirty/删除/运行目录状态；既有 RF 审计只确认至少 404 个可见未跟踪项和 7 个不可见子树，数字不能作为完整空间盘点或清理依据。其 PWF task_plan/progress/register 最后更新均为 2026-09-27，且 task_plan 的 R98 指针落后于 progress R123/register §165。CWP 不改 RF、不合并该脏树。
- FF：根当前 `fcap@d35b6f5` 与 `origin/main` 同步；本地名为 `main` 的 ref `c9799b7` 落后 39。SourceRef v2 与 transcript companion 位于两个干净 worktree（HEAD `5532ce0`、`29085f7`），但共享至少四个关键代码/测试文件，因此由同一 FF owner 先对齐 live main 再逐 hunk 汇合。凭据路径 `config/FMP_API_KEY.txt` 只记录状态、不读取内容。ET `/2` producer 的两个 golden 是 FF 集成输入。
- ET：`main@4924d57` 比 `origin/main` 超前 6；当前 PWF 记录 `/2` schema golden、Motley 三入口默认禁用、一个 request 内 `download_authorized` 控制网络意图，离线 118 passed/2 deselected。FMP 真实请求曾返回 402，不能声称已取得 transcript 权益。`eval_results.json` 与 `.workbuddy-ai/memory/` 仍未跟踪，但 ET PWF 早已标为旧评测与工具笔记；原样保留。FF→ET→CWP 的正式 companion 集成尚未通过 G-A。
- IQS：`master@e7fe99c`，工作树有 owner 对 `task_plan.md` 的未提交更新，本轮未覆盖。最新复验为 StockWiki→IQS focused package 113 passed；provisional G2b 正反 CLI 可用，但 full G2b 仍 partial，缺 verified/multi-listing/AnalysisSubject 与有效期/近名生产样例等；QA-04 有行为测试但交付 handoff partial，SW-IDENT 完整交付也未关闭。DWA-03/04/05/06 仍有 owner follow-up，无新的独立写入卡。
- 计划校准：更新 CWP 当前 refs、E-B/W04 完成状态及 RF/FF/ET/IQS hold，旧 Phase 32 保留为历史快照。实施主顺序不变；具体下一步是在 G-0/G-A 剩余真数据门通过后，以独立 pathless `NarrativeBundle /2.0` read/export reference 和 artifact SHA/source binding/as-of/locator golden 接入 RF、StockWiki 查询入口。不得把叙述包混进 raw `SourceExportBundleV2` 或贸然加通用 role DAG；跨仓真实消费通过 G-C 后再按精确批次 G-D 清理派生空间。Worker 仍 paused/default-off。
- 空间账：F0–F5 已实测同卷净释放 **37.630 GiB**；D0 记录的 39.744 GiB 是当前 catalog 数据目录逻辑长度，含 raw、归档、备份和派生。G-D 尚未实施；RF 审计的最多约 40.3 MB 条件候选不足以解释/解决历史 46 GB 体量问题，不能作为删除目标。
- 文档验证：9 个编辑文件的相对 Markdown 链接全部存在，`git diff --check` 通过。该轮只改 PWF，不重跑产品套件；引用的产品测试结果仍限定于各自已记录的变更范围。Git 提示部分 harness 文档将 LF 转为 CRLF 的 autocrlf 警告，未造成 diff-check 错误。
- 执行时一条 PowerShell 文本替换查询因反斜线转义写法失败；该次只读查询未改文件，随后改用字符串原样查找完成。无产品代码变更。

## 2026-10-01 — 跨线盘点收尾与发布暂停

- 复核各仓当前 HEAD/PWF，细项与恢复次序见[收尾报告](harness_lanes/results/cross_line_closeout_2026-10-01.md)。修正总编排中的 W04 待启、mapping DTO 不存在等旧描述；IQS 当前 HEAD 56ff421 的 V02/scoring 活动文件保留，不覆盖/提交。
- 补齐 G-A 的 FMP JSON admission、原件转义 locator、publication 未知与历史 as-of 的实施/测试细则。发布检查前本轮仅编辑文档；后续为解决新文件复杂度超限，作两处保行为 helper 拆分。生产配置/原件不改，未启动 Worker/空间清理。
- ET 正常推送 1aa9111..4924d57，origin/main 已接受。RF/CWP 发布均使用既有 hooks，不 force push 或 bypass。StockWiki/IQS 无 remote；FF 未汇合支线仍由 owner 整合。
- RF 第一次 push 因 sparse checkout 未物化 e2e 而 Ruff E902。尝试补齐全树遇三项旧测试路径 Filename too long，随后仅追加 e2e/.github。稀疏展开显示四项历史 .planning 文件 M；逐字节比较确认全部等于 HEAD blob，差异是 Git 换行 clean/index 语义，不含未提交业务工作。保留原字节，不 reset。自动审批曾拒绝四路径 restore，理由是当时尚无证据证明改动归属；转为只读完整字节比较及不丢弃文件的追加稀疏目录方案，未绕过拒绝。
- 当前计划仍按 G-0/G-A→NarrativeBundle transport→G-C→G-D；Worker paused/default-off。完成本轮远端发布及临时根收尾后，遵照用户要求暂停。

- RF 再次正常 push：Ruff、compileall、unique symbols、host guard、mypy 全绿；meta/binding 25 passed/2 failed，故未发布。根因已只读确认：compatibility/current.json 的 2026-08-12 informational current_triplet 仍被当作 frozen floor 的验收对象，FF 89c8bdb2cf/CWP 31c0afcb96 都是存在的历史 commit，但非冻结基线后代；不是当前主线回退。修复需要明确历史快照与 live HEAD 校验合同并写 RED，留待恢复，不在本轮停机收尾中仓促改验证器或更新历史 SHA。

- CWP 初次 push：Ruff/compileall/config doctor 通过，复杂度检查 RED（transcript_import 12；后续发现 transcript_tool_contract 13）。只抽取入口上下文校验和 byte cap helper，未变合同或放宽阈值。第二轮复杂度及原件导入/CLI/full-chain 测试 **13 passed**，Ruff 通过；第一次增量试验为 12 passed/1 failed，最终全绿。相关独立根 .pc8869/.pc8869b 在发布前精确清理；hook 的路径重定位根已由清理器删除。最终普通 push 仍须执行原有标准门。

- CWP 第二轮 standard push：lint/编译/config/复杂度/host 全绿；contract/meta 101 passed/1 failed。失败是旧 writer scanner 将六个 source audit/catalog lifecycle/叙述试点工具当成 legacy research writer。先 RED 六项分类断言，新增明确 source-workflow 分类（不是泛化放行），六个真实 CLI --help 无 legacy 环境即可使用，退役研究 writer 不被重新启用；writer freeze 完整包 **20 passed**，Ruff 通过。source 工具自身 SHA/path/事务检查不改。

- 发布最终收据：CWP **f39bd5a..d6d33b8 正常推送成功**，git ls-remote 实读 d6d33b8f6a73edc0f464718c8eb44f1669c95ae1；全部六个标准 pre-push 门 GREEN。ET origin/main 实读 4924d57044ae061d5fec3ccd4f1b7e74633f013a。GitHub Actions run 36936780795 在核对时 in_progress（不是已绿）。RF 未推送，保留既有失败证据。
- 所有本轮独立测试根 .push-rf-20261001/.pc8869/.pc8869b/.prwred/.prwgreen/.pp7f8c/.ppd6d3 均已验证不存在；Win32 pytest owner ACL 使不同执行上下文清理曾失败，改由创建它们的原上下文或同权限上下文清理成功，未修改生产权限。旧不可读 pytest 根不清理。该发布收据提交后正常推送文档，随后暂停；不继续 RF/G-A/G-C/G-D 实现。

- 最后远端核对：CWP master 已到 **7c800313ae41ca516b5ac4a8421f73614f845c56**，本地与远端一致，标准六门再次全绿，最后 .ppreceipt 根已清理。随后发现前一 run **36936780795 / d6d33b8** 的 Python 3.11/3.12/3.13 job 均在 **Unit tests** 步骤失败；check-run 注释只有 exit 1 和 runner/action 提示，未给具体失败用例，不能推断根因。最新 run **36937052936 / 7c80031** 当时 queued。远端 CI **未验收**；按用户收尾暂停要求不扩展产品改造，恢复后先获取失败日志、区分环境/测试/实现，再修 RF 已记录的 snapshot 发布门。此 CI 事实补充文档提交正常推送。

## 2026-10-02 — 远端 Unit tests 复现与修正

- 复核 RF：`rf-impl main@3e03ce83` 仍领先 origin 4；dirty fcap 四个可见状态文件字节与其 HEAD 相同，不提交/覆盖。
- 匿名 GitHub API 确认 run 36937292193 Python job 的前置 Ruff、mypy、compile/config 通过，Unit tests 失败；下载 job logs 返回 403 `Must have admin rights to Repository`。
- 本机按 CI 原命令 `pytest tests/unit -q --tb=short` 在 Python 3.13 重现 **1038 passed / 2 failed**。
- 数值矛盾 fixture 日期硬编码在 2026-06-24..27，超过实现的最近 90 天窗口。测试改为按 today 生成距今 1..4 天的相邻日期，保留现有功能契约；不改产品代码。
- stage semantic spot 的 `provider_site_automation_blocked` 已不在 reason registry；既有清洁架构计划 §4.1 已将它认定为过时测试期望。移除这条旧硬编码，保留真实的 `downloaded_bytes_exceed_authorized_cap -> acquisition+safety` 映射。
- 两个失败模块聚焦回归 **29 passed**；完整 unit 回归 **1040 passed in 70.57s**，Ruff 通过。
- 三个确切 basetemp `.ciunit1002/.cwfails-fixed/.cwall-unit1002` 均以同一受限上下文清理；清理脚本逐项核对目标是 workspace 直接子目录、无 reparse point，并恢复测试生成的只读权限；三个路径最终都不存在。生产 raw/配置/运行 Worker 未动。
- 下一步原计划为提交并正常推送、检查新的 GitHub Actions unit/contract/coverage；Phase 36 已补充远端失败与本机 Linux 复测的最新结论。

## Session: Linux CI 差异与停机收尾（2026-10-02）

- CWP `69652b5` 已推送，`git ls-remote` 确认 `origin/master` 与本地 HEAD 相同。GitHub run `36982949142` 的三个 Python job 都在 `Unit tests` 失败；markdown lint、CLI smoke、secret scan 成功。
- 公开 API 可读 job 摘要，但失败日志下载返回 403 `Must have admin rights to Repository`。未读取凭据。该限制使远端具体失败用例仍未知。
- 本地初次 WSL 结果无效：WSL 通过 Windows PATH 选中了 `zstd.exe`，造成 4 个需要 Linux zstd 的测试假失败。将 Ubuntu `zstd` 包解到临时 `/tmp` 后，聚焦包 **6 passed**、Linux/Python 3.12 全量 unit **1040 passed in 83.12s**。Windows/Python 3.13 全量 unit 亦 **1040 passed**。这些结果尚不能解释远端三矩阵同时失败，不能记远端 CI 为绿。
- 本轮 `/tmp/cw-zstd-native-20261002`、`cw-retire-linux-20261002`、`cw-unit-linux-20261002`、`cw-unit-linux-native-20261002` 均核对为直接子目录且非符号链接后删除；复查均不存在。RF `main@3e03ce83` 仍 ahead origin 4；四个 `.planning/execution_runs` 可见状态文件逐字节等于 HEAD，未触碰。
- 下一恢复动作：取得带具体失败用例的 Actions 日志或等效 runner 证据，再处理远端 CI；其后按计划继续。CWP 产品代码、原文、生产配置、Worker 和 RF 文件均未改。本轮仅更新 CWP PWF 并按用户要求暂停。

## Session: 补齐 push 前 Unit tests 门（2026-10-02）

- 用户要求修复先前提交后触发的远端 CI Unit tests 失败，并追查 pre-commit 为什么没有拦截。核对发现 commit hook 无 pytest；旧 pre-push 也没有完整 `tests/unit`，故既有 GREEN 只覆盖静态检查及定向 contract/meta。
- `tools/pre_push_gate.py` 现运行完整 `tests/unit`，失败即阻止 push；`.pre-commit-config.yaml` 注释同步说明 commit hooks 保持快速、完整 unit 在 pre-push、较广 contract/coverage 仍由 CI 执行。
- 更新后的 Windows 全门 GREEN：Ruff、compileall、config doctor、复杂度 ratchet、host assumption guard、unit tests、contract/meta tests。
- Fresh Python 3.11.15 + CI 同版依赖 + 原生 Linux 文件系统完整 unit：**1040 passed in 169.84s**；Windows/Python 3.13 与 Linux/Python 3.12 也均为 1040 passed。
- 仍未取得 GitHub run `36982949142`、`36984865650` 的具体失败日志（job-log API 403）。因此已修复“push 前本地门缺少 unit”的缺口，但远端失败根因仍未证实；待提交推送后检查新 Actions run，不把本地 GREEN 当成远端验收。

## Session: 新 Actions 仍红与失败用例诊断（2026-10-02）

- `f97b111` 正常推送至 `origin/master`；本地 pre-push 重新运行的七阶段全部 GREEN。GitHub Actions run `36989156366` 已触发，公开 job 状态显示 Python 3.11、3.13 的 Unit tests 失败，3.12 在初查时仍运行；Ruff、mypy、compileall/config doctor 成功。
- 失败 job 用时分别约 10 秒和 14 秒。公开 annotation 只报告 `Process completed with exit code 1`；GitHub 页面显示未登录，失败步骤日志无公开 log URL；REST logs 403。没有据此猜某个测试。
- 为获取受限的精确诊断，CI Unit tests 增加 JUnit XML；pytest 失败时发出最多 25 条只含 node ID/文件/行号的 error annotations，不输出完整异常正文。下一步先验证合成报告解析与边界，再推送并按新 Actions annotation 修复。
- 验证 annotation helper 的三个合成报告测试 **3 passed**。首次完整 pre-push 暴露另一项本机因素：默认 `%TEMP%\pytest-of-郑曾波` ACL 拒绝创建，导致 539 个 tmp fixture setup errors；无关测试函数本身。显式短 workspace basetemp 下受影响模块 **18 passed**、全量 unit **1043 passed in 90.80s**（仅不可写 `.pytest_cache` warning）。
- `tools/pre_push_gate.py` 已让 unit gate 在 workspace 用 `TemporaryDirectory(prefix='.pp-')` 建立短隔离根，传 `--basetemp`、禁用 optional cache provider，并为子进程设置 `PYTHONIOENCODING=utf-8`/`PYTHONUTF8=1`。需以重跑完整 pre-push 为收据后再提交。
- 全门第一轮修复后 unit 已通过，末尾 contract/meta 出现 36 个同源 `tmp_path` setup errors（73 passed）；因此把相同 temp/UTF-8/cache 设置推广到所有 pytest gate。完整 gate 再跑中，未推送当前 workflow 诊断改动。
- 第二轮完整 pre-push 七阶段全部 GREEN，unit 为 1043 passed；contract/meta GREEN，所有 `.pp-*` 测试根退出后均自动删除。Ruff、YAML parse、`git diff --check` 通过。
- Actions `36989156366` 最终 3.11/3.12/3.13 都在 Unit tests 失败，其它公开 jobs 成功；原始 log 仍不可匿名读取。失败 node ID annotations 尚在本地 workflow 修改中，待随下一提交推送。
