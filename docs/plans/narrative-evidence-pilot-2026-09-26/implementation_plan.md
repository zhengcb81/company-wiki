> 2026-10-03 当前施工由 [task_plan.md](task_plan.md) 的S0–S6统一定义。本文保留历史技术背景，旧审批/签收、原件处置和逐小步审查要求不再执行；原件全部保留。

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

# 叙述性证据流水线：拟议实施方案

> **状态：共享选择性证据流水线 W0–W7 仍在规划；独立的 F0–F5 旧库退役已完成；G1 只完成了离线候选选择、定位和摘要草稿验证。** 以 [task_plan.md](task_plan.md)、[findings.md](findings.md) 和 [G1 来源支持审查](g1_summary_source_support_audit_v1.md) 的 10 PDF + 2 TXT 试点为依据。离线代码和 JSON 收据不代表共享接入、生产落库或独立审稿通过；本文规定后续工作包和验收口径，不改变其他活动计划的优先级或 Worker 暂停状态。

**执行细则**：[G0–G4 大节点审查节奏](milestone_review_cadence.md)、[实现工作包](execution_cards.md)、[测试断言矩阵](test_acceptance_plan.md)、[关键路径端到端测试与恢复](end_to_end_test_plan.md)、[审查规程](review_protocol.md)、[多文档并发 Worker 实施手册](worker_parallel_execution_plan.md)。本文件提供架构方向；遇到描述不够具体之处，以 G0 契约裁决和相应大节点门禁为准，不能由实施者自行补猜。

**存储边界补充（2026-09-27）：**[数据湖边界复核](data_lake_boundary_review_2026-09-27.md)是本专项对现有 R4 A/B/C 唯一虚拟数据湖合同的应用。来源可位于 company-wiki、dayu、Dropbox 等已批准 root；W1 的目录映射属于 adapter/受控写入层，W2–W5 及下游消费者只按来源版本、能力和 locator 工作。现有 pilot 的调用方 raw-path 映射不得晋升为正式 G2 API。用户澄清 RF 后续工作是本地未提交改动；本计划以冻结候选快照/支线提交而非并线为技术前置，**但不解除当前 company-wiki 产品代码暂停**。

## 1. 本轮试点推导出的产品目标

company-wiki 默认保存不可变原文，并把有业务意义的叙述变成可回查的来源证据与来源摘要。用户关心产品、行业、客户、产能、海外、合作、募投、管理层解释及风险；标准财务报表数值由下游清洗数据接口负责，但与业务驱动直接相关的运营数值仍可入选。所有摘要明确是**来源说法**，不产生投资结论。经[原文处置 D0–D5](raw_disposition_plan.md)独立判定确实不重要且无引用的旧来源，可逐件清理原文并保留来源处置记录；这项策略需要显式版本化合同，不由 `skipped_*` 自动触发。

本轮样本显示，文件类型仅提供初始优先级，决定保留与否须读正文：P03 的运营进展与报表数字在同页；P07/P08 的具体问答与套话混合；P09/P10 是适宜跳过的制度/通知。P04 的旧章节选择覆盖 83 页、约 30.3 万字符，说明章级定位之后仍需段落/问答/项目级选择。

### 目标数据流

```text
source manifest + immutable raw
  → 轻量识别（文件类型、版本、语言、版式、页/行目录）
  → 按文档类型提取候选结构（章节、段落、问答、项目）
  → 业务证据选择 + 覆盖/跳过账本
  → 来源摘要 + 逐项校验
  → 版本化 SourceBundle/只读 export
  ├─ StockWiki / revenue-forecast: narrative evidence only after owner contract freeze
  └─ invest-quick-scan: optional company/entity identity snapshot only; no narrative package or raw documents
```

入口先由 company-wiki catalog 按身份/版本查询，再由受控 open 取得经验证的同版本原文字节；具体 root/path 只在 adapter 和诊断中出现。上图的 `immutable raw` 是逻辑来源版本，不暗示唯一目录。缺原文时由显式 request_work 决定是否授权下载/加工，纯查询不调用 provider 或暂停 Worker。

对保留原文的来源，目标是让原文可全文检索和预览，同时**默认不把所有段落作为永久 EvidenceSpan 写入 SQLite**。只读检查确认 `EvidenceQueryService` 提供精确 `source_id+locator` 查询和按来源/文档列 spans，`SectionQueryService` 只列 sections；legacy `scripts/search.py` 搜索 Wiki 页面，不是新选择包。隔离试点现在能从 `summary_scope=selected_evidence_only` 包建 query-local 内存索引；新增 pilot-only resolver 已在 12 件隔离样本上按 source SHA 重跑当前 parser/selector，并逐组校验 ID/locator/text hash。bundle v0.2.0 已内置 replay_contract（parser/selector 版本、文档类型/语言、解析选项和选择预算）；resolver 只依赖调用方显式的 source ID→raw path 映射，不把原件路径写入包，也不依赖外部样本 manifest 提供解析参数。它仍是 pilot-only replay helper，不是生产索引/API；来源授权/撤回、历史时点过滤、持久查询和三仓 consumer contract 尚未冻结。W5 仍要冻结 package-backed resolve 的正式 schema/版本、**由 company-wiki 按来源版本受控回源而非消费者路径映射**、处置/历史时点过滤及三仓消费合同；比较轻量页级索引、中文分词/trigram 与按需回源的空间、两字查询和 p95。旧 `EvidenceQueryService.lookup` 不能单独回读未存入 `evidence_spans` 的 span。未通过 W5 查询合同前，不能宣称新 route 与旧检索等价，也不能停旧检索路径。对未入选段落只记紧凑的章节覆盖统计和跳过原因；已存在的规范化/章节产物先保持可读，另行制定安全迁移，不在上线新流程时直接删库。

## 2. 源数据和处理契约

### 2.1 统一类型与来源

| 类型 | 候选单元 | 默认处理 | 关键限制 |
|---|---|---|---|
| 年报、半年报 | MD&A、业务、行业、研发、客户、地域、风险 | 先章节后段落；同主题与前期做版本对照 | 财务表只保留与业务机制相关的说明 |
| 季报 | 财务数据旁的经营说明、重大事项、项目进度 | 全篇廉价扫读后局部入选 | P03 证明不能整页过滤 |
| 招股书 | 业务与技术、竞争、客户、产能、风险、募投 | 建立披露时点的业务基线；章内再切 | P04 整章 83 页过宽 |
| 增发、可转债 | 募投项目、必要性、产能、技术、认证、资金用途、风险 | 按项目组成“目的—能力—计划—约束”证据组 | 注册稿/预案、承诺与实际进度分开 |
| 投资者关系 | 完整问答和追问 | 读全篇、按回答的信息量选取 | 纠正错误前提、跨页问答，问题非公司事实 |
| 英文电话会议 TXT | 发言轮次、准备发言、分析师问答 | 分离网站编辑材料与逐字稿；英文原文、英文来源摘要 | 不翻译；保留转写不确定与供应商身份 |
| 制度、会议通知 | 来源元数据 | 终态跳过业务切片 | P09/P10 可作回归负例 |
| 一般公告、新闻、券商研报（后续扩展） | 具体业务事件、来源陈述及其限定；研报的分析师观点单列 | 先登记来源与文档角色，完成本轮九层门槛后按类型增补留出集，再决定是否选证据 | 不能按“公告/新闻/研报”标题一概切或跳；券商判断不能冒充公司披露 |

新增明确的 `document_kind` 值建议：`equity_offering_prospectus`、`convertible_bond_prospectus`、`investor_call_transcript`。最终命名应先经 company-wiki/filing-fetch/revenue-forecast 三方版本契约核定。对已有 `other` 的 P05/P06 做**重分类迁移**，保留原 `source_id`、原文哈希与旧分类审计记录，不能重新下载制造第二来源。

### 2.2 最小证据单元

候选 `SelectedEvidence` 字段（字段名待契约审查）：`source_id`、`document_id`、`source_sha256`、`document_kind`、`language`、`parser_name/version`、`locator` 或 `anchor_refs[]`、`raw_text_sha256`、`content_role`（management/analyst/editorial/regulator）、`speaker_raw`、`qa_group_id`、`topic`、`entity/product/region`、`event_time`、`published_at`、`modality`（已发生/计划/预测/问题/否定）、`quality_flags`、`selection_reason`。跨页问答、同一表格单元中的多个问答及“项目理由—远页风险”必须作为**一个选中单元引用多个原子锚**，每个锚保留自身页/角色/hash；问题锚不得支持管理层事实。W0 要裁决 v1 span ID 列表是否足够，还是必须定义 locator v2；未裁决前不能承诺新包 schema 已定。

`SourceSummary` 只引用一个或多个已验证的 `SelectedEvidence` ID；必须逐条可回到原文，并标明 `summary_scope=selected_evidence` 与覆盖状态，不能暗示已穷尽整份文件。摘要不包含目标价、评级、估值、仓位、投资命题 accepted/rejected。`CoverageLedger` 仅存来源范围、页/段/问答计数、已入选范围、跳过原因、版本、解析失败/不透明表格范围与 `complete|partial|blocked` 状态，不复制全文。只有完整扫描且负例规则经复核时才能标整件 `skipped_*`；有不可读的业务候选页则保留 `partial/needs_review`，不能伪装为“无业务动态”。

定位规则：PDF 优先复用经原文回读验证的现有 `loc:v1` 原子 span；试点的 PyMuPDF `sort=True` 页内偏移与旧规范化游标**不是同一坐标系**，不得直接转换。若一个旧表格单元含多组问答，row/column 定位不足以支持单问答引用，W0 须定义新的片段锚（页 + 表/块 + 精确引文 hash/上下文 + parser 版本，必要时 bbox/locator v2）及回读方法，或以明确的 `needs_review` 停止细粒度导出。跨页组用多个可回读原子锚引用，不伪造单个跨页 range。TXT 增加稳定的行/字节偏移适配，绑定**原文件 SHA**；必须确定是 header、网站编辑、准备发言、问答还是尾注。选取了答案时必须能回查对应问题。解析版本变动后重验所有 locator。

### 2.3 时间和来源身份

分别保存财年季度、电话会议日期、文档发布日期、原文抓取 UTC 时间和进入 catalog 时间。`as_of_date` 可消费性按**文档公开时间**判定。招股和再融资文件标明草案/注册稿/正式稿，项目预期不自动晋级为进展事实。网站摘要与电话会逐字稿属于同一供应商材料的不同角色，不能当独立交叉验证。

## 3. 工作包与目标文件（实施时逐包审查）

| 工作包 | 建议落点 | 具体改动 | 完成条件 |
|---|---|---|---|
| W0 基线与契约冻结 | 本计划样本；`source_contract/`、三仓消费契约 | 固化 13 张试点卡；逐项定义类型、locator、版本、时间、摘要角色；记录旧库/旧导出基线 | 消费方可读旧版本；负例和历史时点规则经审查 |
| W1 分类与来源 | 来源 adapter、`scanner.py`、`canonical_writer.py`、`acquisition.py` | 识别大写 `.PDF`、增发/可转债及电话会议；sidecar 与来源事实按字段 provenance 合并；目录映射只在 adapter/受控写入；市场+文档类型路由 | P05/P06 不再 `other`；P09/P10 仍可登记但跳过业务处理；同 SHA 跨 root/优先级置换不改业务元数据 |
| W2 轻量解析 | 专用 PDF/TXT 结构适配器；只复用已证明无写入且不丢块的纯函数 | 从 raw 读页/行目录与章节候选；PDF 保留页文本/块和表格双视图并做锚点覆盖检查，不调用全量 `normalize_catalog`；TXT 支持两种 Motley Fool 版式 | P08 大表格单元的多个问答可拆且不丢正文；P04 产品表保留；P03 同页信息可分；P07 跨页组完整；P04/P09 无新全量 normalized/spans |
| W3 证据选择 | 独立选择器，复用 `section_extractor.py` 无写入规则；`artifact_dag.py` | 区分财务报表与产品/客户/产能/募投业务表，按段落/问答/项目选证据；正文未入选不持久写全量 spans；覆盖账本记录布局不确定与 skip 复核；相邻 PDF 片段合成一个选择预算组 | 11 正例都可定位；2 负例无业务切片；漏选高价值表和误收提问均阻断。像 P02 “超 / 过60%”的量化目标须保留全部必要 locator，任一片缺失即锚点失败；skip 误漏率在留出集单列 |
| W4 来源摘要 | `summarizer.py`、`llm_summarizer.py` | 先压缩候选再摘要；逐条引用 selected evidence；保留限定、风险、否定、时点和计划阶段；英文 TXT 同语言摘要 | 摘要无无来源断言；C02 保留“未来五至十年、超过60%的设备市场”为公司前瞻目标并引用两段；P08 问题错误前提得到纠正；T02 “尚早判断”不改成既成事实 |
| W5 检索与只读消费 | `source_bundle.py`、`artifact_handle.py`、`source_contract/source_export.py`、R4 B07 受控读取合同、轻量检索适配及消费者夹具 | 显式登记来源工件 role/版本；按 source/version/locator 回源而非要求调用方路径；比较页级索引、中文短词/英文/精确短语和源过滤；版本化导出与撤回 | 旧消费者安全降级；正式 RF/StockWiki reader 零 root/path 业务分支并可处理撤回；新来源全文查询在冻结质量/空间/p95 门槛内，否则不切换 |
| W6 Worker 执行 | R4 C05 的现有 `automation/jobs/attempts` 入口、source-catalog Worker/提交接口 | 同文档依赖串行、不同文档锁外受控并发；先修原子领取/断点/幂等，再逐级扩容 | 崩溃或丢 ACK 可恢复；同 job key 至多一个 accepted 产物；用户暂停不被自动恢复 |
| W7 存量/空间迁移 | 独立的数据修复计划，与现有空间整改计划衔接 | 先影子产物/比较，再小批切换；校验下游快照、引用及备份；最后才考虑旧全量 spans 归档/压缩/数据库收缩 | 查询与来源链一致、可回滚、真实 DB 字节数与长时间运行指标实测 |

**46 GiB 旧主库的提前退役是独立快路径**：已在临时环境实测“全部目录元数据 + active 旧切片”仅 2.849 GiB。按[提前退役 F0–F5 审查卡](early_catalog_retirement.md)可先验证完整压缩旧库备份、活跃查询差分、retired 查询失败关闭与文件级切换；它不要求等 W3–W6 全部完成。W7 继续负责新流水线后的历史冷热分层、旧引用和净总占用治理；快路径不解除 Worker 暂停或许可继续用旧全量 normalize。

**整件跳过与原文删除是两种裁决**：W3 只决定是否选业务证据；唯一原文的 `irrelevant_reclaimable`、重复副本、保留/阻断由[原文处置 D0–D5](raw_disposition_plan.md)另行审查。W0 冻结可用性状态和消费方合同，W5 验证 `raw_disposed_intentional` 的查询/预览/export 行为，W7 才接入逐路径回收；若新读路径或旧活跃 span 仍会伪称可回源，D4 不放行。Worker 可并发提出候选，物理删除仅由独立单执行者按 source SHA 串行实施。

`artifact_dag.py` 当前存在进入本轮前的他人未提交修改；W3 动工前需核对并保留其状态，不能以本计划覆盖。现有 `SourceBundle` 对 artifact role/生成器有显式白名单，`source_export` v1 仅含 manifest + EvidenceSpan。**只在表里增加一行新 role 不会自动让下游可消费**，W5 必须同时处理白名单、版本协商和导出结构。不可把本规划文档视为这些接口已经变更。

## 4. 电话会议专门接入：filing-fetch → earnings-transcripts

1. **调用目标是伴随申报文件的电话会议原件。** filing-fetch 新版严格请求使用可选 `companion_transcript` 对象，须显式给出 FY/Q；年报不推断为 Q4，财报日期不推断电话会期次。旧请求未给该对象时沿用原 filing 行为；申报文件成功与 transcript 子结果独立返回。
2. 先确认唯一有效公司/证券身份，再用 `investor_call_transcript` 与精确 FY/Q 查询 company-wiki resolver；已有 capture-ready 原件直接 `reused`，不调用 provider。未命中时需 transcript 专属请求授权与独立进程开关，原有 filing `--allow-download` 不级联授权。
3. `earnings-transcripts` 的新 `transcript_tool.py` 是 stdin/stdout JSON 子进程工具，已提供 `discover`（仅候选元数据）、`fetch-candidate`（绑定单个已授权候选的正文）和 opt-in `/2` 原件响应；它不是 MCP server。filing-fetch 必须在 discovery 前做 provider `discover_metadata` 权利预检，在正文请求前让 company-wiki 对选定候选核验 `automated_fetch`、`retain_original`、`derive_text` 与精确 `DownloadAuthorization`。候选缺失/歧义、未知交易所、FY/Q 或 as-of 不匹配均失败关闭。旧 `scraper.py` 的最近 N 季批处理及其翻译/日志/cache 行为不进入这条调用链。
4. `/2` 响应只在显式 opt-in 时带有界 base64 provider 原始 HTML/JSON/TXT、MIME、实际 HTTPS URL、原件 SHA、提取版本和日期语义。父进程限制子进程 stdout/时间，company-wiki stdin importer 重新加载当前 runtime 与 rights policy、复算请求/候选/授权、URL、MIME、大小、SHA 和期次后，调用 canonical writer。**长期原件是一份 provider 原始字节**，当前 writer 对 `investor_call_transcript` 的目录映射为 `companies/{entity}/raw/investor_relations/transcripts/`；未翻译英文 TXT/行 locator 是从原件确定性重算的派生内容，不作为另一份 canonical raw 保存。存量 43 份 TXT 的迁入须另做身份、hash、权利及原件性质核验，不得直接批量覆盖。
5. 旧 transcript writer 生成的 header、双语 JSON 或交错 TXT 不能冒充 provider 原件；FMP 402、来源/保留权不明，Motley Fool 与 Seeking Alpha 自动抓取被现行 policy 拒绝。当前只用隔离 fake provider 验证代码路径，不做真实正文网络调用。测试运行根必须独立，正常、拒绝和超时后恢复到运行前基线，不残留 raw、base64 响应、catalog、锁或 Worker 状态变更。
6. 解析器保留原件可回源性，摘要选择时把网站前言、词汇表和尾注标为 `editorial`，不作为管理层观点；说话人冒号版和独立行版分别测试。遇到错标，不猜真实说话人，记录 `speaker_uncertain`。摘要仍是带 source/locator/质量标记的资料型草稿，不写投资结论。
7. 本节只定义上游 acquisition 边界；完整 request/response、分项状态和 G1e-C/D/E 验收以[跨仓集成合同](filing_fetch_transcript_integration_v1.md)为准。E-T/filing-fetch 的独立 adapter 调查与合同可与 RF G0 并行；**任何 company-wiki worktree 的 importer、canonical writer、测试或正式接线改动仍暂停**，其恢复前需锁定 RF 本地候选合同与冲突面，但不要求 RF Git merge。正式 transcript artifact role、SourceBundle、消费者接口与 Worker 仍须等 G0 冻结，且隔离 fake-provider E2E 不构成生产 provider 授权。

## 5. Worker 的具体执行模型

本节的串行状态链是**单份文档的依赖顺序**，不同文档可并行计算。先按 R4 C05 修复并接入已有 `automation` 持久 job/attempt，不另建任务队列；再按 C07 把整批 normalize/LLM 调用的长锁拆成锁外计算和短提交。具体事务、跨库对账、Windows 进程和试验见 [实施手册](worker_parallel_execution_plan.md)。现阶段不能直接多开现有 Worker 或共享 `LLMClient`。

一份文档一个依赖链：`discovered → classified → outlined → selected | skipped → summarized | summary_not_needed → exported`。每步绑定来源/上游/策略版本和结果哈希；同一 `automation.Job.job_key` 重试至多接受一个逻辑产物。`processing_demand.py` 是纯内存队列，`producer_attempts` 只是调用审计；已存在的 `automation` 表目前也未接生产 Worker，其 claim/finish/outbox 还需原子性修复。W0 对齐 R4 C05/C07 的实现状态，W6 按 [实施手册](worker_parallel_execution_plan.md) 的 N0–N6 实现，并在 G3 一次集中验证。质量不佳可为 `needs_review`；可恢复错误有上限重试，确定性无价值文档终态跳过。

调度先响应 filing-fetch 或消费者的按需请求，再消费新到原文；低价值旧档的批量回填最后执行。按文档类型设置独立成本上限和输入量；页目录/结构识别后只给模型相关候选，保留按需回源的能力。每个任务记录墙钟时间、输入/输出 token、外部调用、候选数、入选数、拒选原因、重试次数、输出字节数及错误码。catalog 提交仍由一个 writer 串行；未来计算并发仅可采用独立进程/独立 LLMClient，且以 [并发实施手册](worker_parallel_execution_plan.md) 的共享预算、限流、恢复与暂停门禁为前置。

当前 Worker 用户已停止；本方案的创建和试点均不解除暂停。未来 W6 只能在现有 Worker 恢复计划允许的隔离测试/门禁内实施，先以临时 catalog 试跑，再有明确的上线批准。filing-fetch 如果遇到原本已由用户暂停的 Worker，不得替其恢复。

## 6. 下游协作边界

| 消费方 | 从 company-wiki 读取 | 其自身负责 | 接口门禁 |
|---|---|---|---|
| StockWiki | 原文来源、选定证据、来源摘要、质量、公开时间、版本与撤回 | 投资命题、结论接受/否决、公司研究状态 | 导出版本协商；来源撤回/纠错可传播，不跨仓写数据库 |
| revenue-forecast | 与驱动相关的运营描述、订单/客户/产能/指引条件及其定位 | 驱动树、情景、收入公式、预测误差 | 当前活动计划内对齐 source type 与 `page_or_section`/locator；不在本计划并行造第二预测接口 |
| invest-quick-scan | 可选 company-wiki entity/security identity mapping only | 快速筛查与展示 | 不读取或保存叙述证据包、摘要、原文；没有身份映射时仍可运行 |
| 外部标准财务数据 API | 上游只记数据来源引用或下游关联键 | 清洗的财务数字、单位/口径/版本比对 | 业务运营指标若来源于文本仍可留证据，不重复维护一套财务报表 ETL |

revenue-forecast 的独立活动计划为 `C:/Users/郑曾波/Projects/revenue-forecast/.planning/2026-09-19-three-project-history-audit/`，截至本轮只读查看仍有跨目录卡片与依赖门禁在执行；这里只定义待对齐的接口，不改其卡片、裁决或任务状态。StockWiki 和 revenue-forecast 是叙述证据候选消费者，须在 G0 冻结真实 reader/adapter 合同；当前 pilot bundle 与 StockWiki 严格 Source Provider v1 不兼容，不能直接宣称可读。invest-quick-scan 只涉及可选身份映射，不是证据包消费者。

上游只暴露版本化来源/证据合同，不把 CWP 内部 `ROLE_DEPENDENCIES` 作为 RF 运行时依赖；CWP 当前 DAG 含 `consumer_analysis` 属待迁移兼容项，具体调用者和失效链在 G0/R4 C01 核查后再版本化退出。新 provider 或新 root 不应触发 RF 直接修改 CWP store/resolver；确实缺通用原语时，由 CWP owner 以一份反例、合同及受影响调用者在大节点审查后实现，不因“少改文件”而禁止必要的上游修复。

## 7. 验收、上线和回滚

### 可复现试点门槛

- 13 张来源摘要/跳过卡（11 正例、2 负例）逐张可通过原文 SHA、PDF 页/文本锚或 TXT 行号重现；摘要每一事实均有来源，不得把问题前提、网站编辑材料、计划或风险改写为已实现事实。
- P03 页内混排、P07 跨页问答、P08 错误前提、P05/P06 再融资分类、T01/T02 双版式以及 Figma 说话人异常形成固定回归集合。失败则不扩样。
- 在上述样本之外建立**分层留出集**，每类至少覆盖不同公司和新旧时间版本；人工标注完整候选片段与应该跳过的材料，先公布分母，再计算证据召回、误收和原文定位成功率。当前 11 张正例只是下限样本，不能报总体准确率。

### 运行和空间门槛

- 在隔离 catalog 上，先测现行流程与新流程的每文档时间、模型调用、token、SQLite 增量、衍生文件字节、查询延迟；相同输入/机器/版本重复测。单列 paragraph/table-cell/空 cell 行数、JSON 与索引字节、page_count/freelist/WAL/备份，并保持原文检索能力。优先检查 429 页招股书、15 页季报和 6 页问答，避免平均值掩盖复杂案例。
- 实现后要求新流程相对基线**确实降低**长文档永久 span 写入量与摘要输入量，同时保持留出集关键证据可回查；效果阈值由实测基线与业务容忍度定稿，不以本轮 12 份抽样捏造百分比。
- 生产空间优化分为提前退役旧主库与阻止新来源膨胀两条独立发布线。前者按 F0–F5 保留 active 旧切片及完整可恢复压缩快照，之后才针对确切原 DB 文件作单独清理；后者按 W0–W6 验证选择性入库。两线都要求原文/来源、哈希、外键、下游引用、回滚和停机窗口核验；不得在试点时直接 VACUUM、批量 DELETE 或清空目录。

### 发布顺序与回退

共享系统的优先依赖是 **RF 未提交候选的接口快照与 CWP 当前 dirty 冲突核对 → [R4 A 合同](../painpoint-outcome-audit-2026-09-05/r4-data-lake-priority-rollout-2026-09-27.md)（本专题 G0 复用其审查）→ R4 B 位置透明读取真实验收 → R4 C.local 基础来源跨仓消费**；RF 不需要先合并 main。**W5 正式 selected package 完成后才做本专题 G2a**，复用 C.local 的 reader 收据并新增叙述消费 E2E，不将 G2a 作为 C.local 前置。既有 W1–W4 隔离研究结果可保留；当前所有 company-wiki worktree 的产品代码、试点脚本和测试继续暂停。恢复后 W1–W4 的后续隔离实现仍须遵守 R4 合同，共享 catalog/export 发布和 W5/G2a 正式接线按上述依赖。W6 Worker 后置于稳定 source/version/job 合同与其既有暂停/恢复门；W7 及原文处置各走不可逆操作门。专题内部生产工序仍按 `W0 → W1/W2 → W3 → W4 → W5 → W6 → W7`，W1/W2 可在临时 catalog 分类型并行验证，但该序列不授予跳过 R4 B/C.local 的权利。每阶段先影子产物，再单公司小批、再按类型扩大；旧消费者在版本协商完成前继续读取旧结构。任何未通过的阶段只撤回该阶段的新版本 artifact/路由，原文和旧版本不改。

## 8. 待实施前核定的五项问题

1. **消费者包 schema 尚未冻结。** 先对照现有 `SourceExportBundle/v1`、StockWiki 严格 `Source Provider v1` 和 revenue-forecast 当前获批合同；pilot `narrative-evidence-selection-bundle/0.2.0` 不是 StockWiki Source Provider v1 的直接输入。G0 由相关 owner 确定是否可复用现有合同或需单独版本化的叙述包，并明确 coverage、`partial`、`needs_review`、撤回与历史时点语义。未获批前不得把 `NarrativeEvidencePackage/v1` 写成默认接口；invest-quick-scan 只需另测可选身份映射。
2. 现有全量 span 对检索的依赖范围，以及按需回源查询的 p95 延迟预算；对业务表/IR 大表格单元的细粒度定位是否需要 locator v2。不能先删存量再验证。
3. 再融资文件的最终分类命名和项目级 ID 规范；修订稿、注册稿之间如何建立替代/延续关系。
4. 英文电话会议不同供应商/版式的原文可用性、披露时间及发布许可；本轮只验证已有 Motley Fool TXT 样本。
5. 留出集的人工标注范围和关键证据漏收容忍度，由实际消费任务验证后确定，不能从 12 份探索样本外推。

## 9. 外部数据源与费用边界（2026-09-27 补充）

详见 [外部数据源、月调用预算与采购闸门](provider_cost_and_capability_2026-09-27.md)。来源发现优先使用 SEC EDGAR、交易所/公司 IR 和现有市场工具；FMP Basic 只作有界的身份/SEC 补充。现有 key 的 profile 和有效 SEC 检索实测 HTTP 200，新闻稿与电话会议期次为 402。Koyfin 没有用户 API，Seeking Alpha 个人 Premium 不能用于自动采集。按本地 246 个公司目录的保守上界，免费 FMP SEC 补充路径为 2,076 calls/30 日；纯公开源为 0 FMP calls。若精确权益、来源增量和存储/export 条款尚未验证，先不购买任何套餐。20 家美国证券的 30 日试点与 G1e 可独立于 RF G0 推进，不改变 G2 消费合同或 Worker 放行顺序。
