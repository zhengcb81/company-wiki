> 2026-10-03 当前施工由 [task_plan.md](task_plan.md) 的S0–S6统一定义。本文保留历史技术背景，旧审批/签收、原件处置和逐小步审查要求不再执行；原件全部保留。

# 执行卡：叙述性证据流水线 W0–W7

> **后续 W/D 实施卡；本轮 F0–F5 已获授权并单独执行。** 总体目标、样本和已验证事实分别见 [implementation_plan.md](implementation_plan.md)、[findings.md](findings.md)。执行时新建独立实施记录，不修改当前或其他项目的活动计划指针。W/N/D 卡按依赖关系实施，**集中在 [G0–G4 大节点](milestone_review_cadence.md)审查；本文件和旧审查/测试文档中“逐卡签收/逐步全验”的频率均以该修订为准**。具体断言见 [review_protocol.md](review_protocol.md)、[test_acceptance_plan.md](test_acceptance_plan.md)；G1–G4 的真实端到端路径、run-id 测试目录与清理后基线恢复见 [end_to_end_test_plan.md](end_to_end_test_plan.md)。

## 0. 对实施模型的统一指令

1. 按依赖领取一组相邻卡，先记录 Git HEAD、工作区既有改动、相关测试基线和允许修改的文件；发现其他人改动时保留原样。禁止顺手重构、跨仓写文件、改生产配置或处理全量历史库。
2. 所有开发和测试使用临时 catalog、临时 raw 根目录、假下载器和固定时间；不得在真实 `companies/`、生产 SQLite、`config/source_catalog.yaml` 上运行测试写入。生产 Worker 保持用户暂停状态。
3. 只实现本卡列出的输出；未确定的接口使用 `blocked_decision` 结束本卡，不猜字段、来源时间、发言人、证据位置、下载权限或业务结论。不可用空断言、全 mock 或降低门槛把失败变绿。
4. 每张卡完成时由实施者做相关 diff 与目标测试自检；G0–G4 大节点才提交一次变更清单、关键命令/退出码、质量/空间结果、失败清单和回滚方法。返工只复测受影响的模块及其直接消费者，不逐卡独立签收。
5. 任意阶段保持原文不可变；`source_id`/原文 SHA/发布时点不重写。company-wiki 只输出来源证据和来源摘要，不产投资判断。内容选择依据正文，文件名仅辅助分类。

## 1. 固定设计选择和待裁决点

| 编号 | 执行选择 | 边界/停机点 |
|---|---|---|
| D1 | **消费者包 schema 暂不预选。** 对照现有 `SourceExportBundle/v1`、StockWiki 严格 `Source Provider v1` 和 revenue-forecast 获批合同，确定叙述证据是否可作为兼容的只读扩展或需要新版本；invest-quick-scan 仅涉及可选身份映射，不消费叙述包。 | G0 由相关 owner 批准稳定身份/哈希关联、selected evidence、source summary、coverage、`partial`/`needs_review`、撤回及时点语义。pilot bundle v0.2.0 不得宣称兼容 StockWiki v1；合同未冻结就停止 W5，不自造字段或消费路径。 |
| D2 | 选中证据以单个段落、完整问答、募投项目说明及其相邻风险为最小组合；组合可含多个原子锚。标准财务报表默认不入摘要，产品/客户/产能/募投业务表须审读；同页运营描述保留。 | 不以整个页面/章节/表格或关键词作最终选择。旧表格单元含多个问答时不能用单个 row/column locator 假装细粒度；无可靠定位即 `needs_review`。 |
| D3 | 摘要逐项绑定 evidence ID，继承语言、说话人角色、披露日期、阶段、否定与限定词。TXT 保持英文。 | 任何无引用事实、把投资者提问/网站编辑说法写成管理层事实、把计划写成完成，均拒收。 |
| D4 | 复用并修复现有 `automation/jobs/attempts/effects/outbox`，使它成为唯一持久 job 状态；catalog 只保存来源与版本化叙述产物。`processing_demand.py` 仅可作内存视图；`producer_attempts` 仅作调用审计。 | 按 R4 C05/C07 核查事务与锁，冻结 job key、attempt fencing、暂停、跨库 saga 和恢复协议；不得在 catalog 另建第三套队列。详见 [并发实施手册](worker_parallel_execution_plan.md)。 |
| D5 | 财报下载通过版本化 companion result 调用一个匹配 period 的 earnings transcript；存量优先复用；transcript 与 filing 分开报告。dayu 的 US filing 路由继续独立。 | 目前没有可调用的 MCP tool，只有 `scraper.py` CLI；当前 CLI 输出、配置、logs、lock、cache、副翻译文件不能天然隔离，period 也只是最近 N 季。在线路由前须有可注入、精确期次、无翻译、无全局副作用的正式 adapter/API，并返回可验证 HTTPS 来源；FMP 的占位 URL 禁止接受。此上游 contract 可独立于 RF 下游 G0 冻结。 |
| D6 | 所有旧 `retired`、撤回与更新继续由现有来源语义决定。新包仅消费有效快照并显式发布撤回/替代。 | 旧 catalog 的 `retired` 语义未核实前不可把旧 artifact 自动重新激活。 |

## 2. W0 契约冻结与基线（所有卡的前置）

- **输入**：`findings.md` 中 P01–P10/T01–T02、C01–C11/N01–N02；当前 `SourceExportBundle/v1`、artifact DAG/handle、SourceCatalog、filing-fetch 实际 `scripts/filing_contracts.py`/`fetch_filing.py` 与安装技能文档、三方消费者实际读取代码及 revenue-forecast 现行活动计划。已观察到 filing-fetch 技能写 schema 1.1 / v1.4.0，而本地代码常量是 request schema 1.2 / `SKILL_VERSION=1.2.0`；W0 必须先确定活动接口来源，不可混用。
- **允许修改**：仅新建本专题的 schema 草案、夹具/测试计划和实施记录。不得修改其他项目文件、既有计划、生产配置/数据。
- **顺序**：① 冻结 12 源完整 SHA、出版/抓取时点、13 张标签和证据分母；② 查 `retired`/版本链与现有导出身份；③ 由相关 owner 对照 `SourceExportBundle/v1`、StockWiki `Source Provider v1` 与 revenue-forecast 当前合同，决定复用还是另定叙述包 schema/版本，冻结稳定 ID/哈希、**多原子锚与旧 locator v1 的兼容或 v2 需要性**、coverage/skip/withdrawal/时点语义及未知版本拒绝；④ 明确 `document_kind` 枚举和兼容旧分类；⑤ 分开记录 StockWiki/RF 叙述包 reader 与 quick-scan 可选身份映射，禁止假定两个证据消费者和身份映射客户端读同一包；⑥ 固定留出集阈值、性能/空间门槛、按文档聚类的正式样本量和置信区间、跳过文档的漏收审计与人工标注者签名。每类 4 件仅是集成盲测最低数，不是准确率证明。
- **输出**：版本化契约、样本/留出集 manifest、旧流程基线（按文件时间/token/数据库增量/locator 成功率）、兼容性表、已签门槛。`as_of_date` 使用可核验的公开时间，未知时标 `unknown` 并拒绝历史时点消费。
- **审查**：来源/导出契约审查 + 至少一位实际下游接口所有者的只读兼容性确认。没有真实消费者核对或数值门槛未冻结，W5/生产放行不得开始；W1/W2 可在临时夹具中研究。

## 3. W1 分类、来源与无翻译接入

- **依赖**：W0 分类及来源身份契约。
- **建议落点**：company-wiki `scanner.py`、`canonical_writer.py`、`acquisition.py`，filing-fetch 的版本化 companion orchestration，earnings-transcripts 的正式 provider adapter；仅需改动时才扩展 schema。每个跨仓改动单独审查，不能在本卡代改他仓。当前 CLI 不是可直接复用的 adapter：无 `--config`、只支持最近 N 季，且会初始化配置目录/log/lock/cache；owner 必须先冻结可隔离、可注入测试的 exact-period 无翻译接口。不得让 Worker 每处理一件文档就盲目启动全局 scraper，也不得用 `--force`。
- **顺序**：① 以 sidecar 优先识别 `prospectus`、`equity_offering_prospectus`、`convertible_bond_prospectus`、`investor_call_transcript`，大小写扩展名等价；② 为 P05/P06 提供不换 `source_id`/raw SHA 的分类迁移；③ route=(market, kind, provider capability)，先 resolver 复用后显式许可下载；④ 与 filing-fetch owner 冻结新 request/response schema：有效 financial filing 请求可以取得 companion transcript，最多一个精确 period；旧 schema 行为不变，transcript result 独立；⑤ transcript provider 请求绑定 canonical company/security 与 fiscal period，响应包含原始未翻译正文/字节、准确 HTTPS 来源、provider ID、日期和 provider payload SHA，不直接写 catalog；⑥ canonical writer 只将该合同规定的正文字节暂存并写到 company-wiki，sidecar 保存 provider 来源与抓取时间，canonical file SHA 独立核验；不写双语 JSON/夹排稿、不翻译；⑦ filing 与 transcript 错误分立；无 provider、not-found、ambiguous、timeout 不改 filing 子结果；⑧ 满足这些合同后再开放联网 provider。
- **必须验证**：P05/P06 从 `other` 变目标类型但不新增来源；P09/P10 可登记并保持负例；T01/T02 字节不变、不翻译、同请求二次运行不覆盖；US 年报继续走原 filing provider；无下载许可时零网络调用；伪造 URL/FMP 占位来源拒收。独立 transcript contract test 验证 resolver 命中时 provider 调用为 0、无授权时零网络/写入、证券/ticker/精确 period/as-of 映射、隔离 staging、正文不变且不翻译、payload SHA 与 canonical file SHA 规则、HTTPS sidecar provenance、幂等，以及 transcript not-found/unsupported/ambiguous/timeout 不影响 filing 子结果。离线 E2E 通过正式 public adapter 边界注入 fake provider，不直接调用 parser 冒充编排 E2E，也不调用真实 CLI 网络路径；`--dry-run` 不能代替离线测试（仍可能探测来源页）。多文档 Worker 可并发解析已落盘 TXT；provider 抓取并发须受专用限流/锁保护。
- **停机/回退**：来源身份、已发布时点、许可或路径归属不明就只保留原始 catalog 状态；回退仅关闭新路由/分类投影，不删除原文。不得为修复分类重新下载。

## 4. W2 轻量结构解析

- **依赖**：W1 临时源记录；W0 locator 契约。
- **建议落点**：专用 PDF/TXT 轻量结构适配器，可复用 `normalizer.py` 中无写入的纯解析函数。旧 normalized artifact 保持可读且只可在 SHA/版本有效时作为可选缓存；新 DAG 不调用会写整份 `normalized.md`、重建全量 `evidence_spans` 的 `normalize_catalog`。新结构单独版本化。
- **顺序**：① PDF 页目录、正文块与表格双视图、OCR/文本质量预检；不可沿用“块与表格 bbox 相交即丢弃正文”的旧规则，须在双视图之间做文本锚点覆盖/重叠消解；② 对超大表格单元做内容级问答拆分，对产品/客户/募投表保留列语义；③ 建章节/问答/项目候选，跨页用多个原子锚关联；④ TXT 对原始字节建立行偏移表，区分网站编辑、准备发言、问答、尾注及未知角色；⑤ 为每个候选记录源 SHA、解析器版本、精度和可回查的原文片段哈希。
- **必须验证**：P03 第 3 页两种内容可分；P04 第 114 页产品/应用表关键描述不丢，83 页旧章节进一步划分；P07 跨页问题与回答成组；P08 第 2 页即使 29/30 正文块与大表相交，也能拆出多个问答且保留纠错；T01 行 124 起为逐字稿、334 起为尾注；T02 行 20/178/598 边界；说话人错标为 `speaker_uncertain`。同页字符偏移与旧 normalized 坐标不得混用。抽不到文字的 P05 封面不能伪造文本。P04/P09 新路径运行后旧全量 normalized/spans 增量为零，selected locator 仍能回读 raw。
- **停机/回退**：定位无法回读原文或 parser 质量低于 W0 门槛，则该范围 `needs_review`；保留来源索引，不生成细粒度证据。解析失败不能触发重下载。

## 5. W3 选择、覆盖账本与按需回源

- **依赖**：W2、W0 证据契约。
- **建议落点**：独立选择器可复用 `section_extractor.py` 中无写入的候选规则，直接消费新 outline；`artifact_dag.py`（注意该文件有进入本轮前的未提交修改）、artifact role/producer registry、检索定位适配。先做新产物影子运行，不改变现有全文检索。
- **顺序**：① 文档类型候选策略；② 表格先按列义/内容区分标准财务报表与业务描述表，前者排除、后者进入候选；通知/制度/编辑/尾注排除须有可复核理由；③ 对剩余候选按主题和业务增量选段/问答/项目并配对约束/风险；④ 写 coverage ledger（范围总数、选择/跳过/失败计数、布局不确定和原因，不复制全文）；⑤ 只对选中单元物化永久 span，其余通过原文/临时解析按需定位；⑥ 对 skip 文件按 W0 冻结的比例/风险分层抽样回读，发现漏选则撤销 skip 并以新策略版本重跑。
- **必须验证**：C01–C11 均有可回查单元，N01/N02 在**全篇可读**时零业务切片；若任一业务候选页不可读、表格不透明或 OCR 失败，整件不得标 `skipped_*`，coverage 必须为 partial/blocked 并上报缺口；P03 运营段入选且财务表不入；P05/P06 募投与风险同组；P08 的错误提问只作问题角色；同 SHA+策略版本重复运行零新增。未知 locator/role/schema 被 handle/DAG 拒绝。
- **停机/回退**：任何关键证据漏收或误收负例，停止扩大样本；影子产物可标 invalid/retired，不动旧 spans。旧全量路径的停用须另验全文查询回源能力；这不意味着新 DAG 可以调用旧全量 normalize，也不授权删除旧库。

## 6. W4 来源摘要与验证器

- **依赖**：W3 通过 13 张卡；W0 时间/语言/角色契约。
- **建议落点**：`summarizer.py`、`llm_summarizer.py`、独立逐项校验器和新版本摘要 schema。
- **顺序**：① 摘要输入仅 selected evidence + 必要上下文，原文始终标为不可信数据，文档内“忽略规则/执行命令/泄露信息”等指令不得进入系统指令位；② 每句声明引用一个或多个 evidence ID；③ 验证语言、角色、数字/单位、否定、时间、计划/实际与风险配对；④ 不确定或冲突写 `needs_review`，不得强行概括；⑤ 记录模型、提示词哈希、源版本和成本。
- **必须验证**：C01 三种成熟度、C03 “部分”、C04 历史时点、C05/C06 募投预测、C07 未证实兑现、C09 提问数字被回答纠正、C11 `too early to speculate`；T01/T02 英文原文和摘要不翻译。植入无来源句、反转否定词、错误说话人和原文中的操作指令时验证器必须拒绝；模型不得访问网络/文件系统工具来执行原文指令。
- **停机/回退**：不合格摘要不导出；选中证据仍可被只读消费。模型输出失败不能自动换成无引用的自由摘要。

## 7. W5 只读导出与跨仓消费

- **依赖**：W0 契约签定、W3/W4 通过；实际消费者的适配需其所属项目独立实施与审查。
- **建议落点**：`source_bundle.py`、`artifact_handle.py`、`source_contract/source_export.py` 旁的新 v1 附属包生成器；各消费者只在其本仓的既有计划允许时接入。
- **顺序**：① 注册新 role、依赖、producer 版本与验签；② 在临时库比较轻量页级全文索引、trigram/中文分词与按需原文检索，明确两字词、英文词、短语、OCR 缺页、源/时间过滤的回源行为；索引只指向 source+页/行，不生成全量永久 EvidenceSpan；③ 根据同一 catalog 快照导出旧 v1 包及新附属包，绑定导出 ID/哈希；④ 定义 full/delta 顺序、撤回/更正/tombstone 与重放幂等；⑤ 消费者显式协商支持版本，未知版本 fail closed；⑥ 只读跨仓合同测试，不写 StockWiki 数据库。
- **必须验证**：查询“硫化锂”“中试线”“出海”在 P07/相关受控夹具可找到对应原文，短词回退的 p95/空间在 W0 门槛内；返回片段可回读 raw；旧消费者仍能读原 v1；新消费者不能在源 retired、hash 不符、artifact invalid 或 `as_of_date` 早于公开日时消费；撤回能把旧引用失效，重放不制造重复结论；研究结论/预测字段不能写进上游包。
- **停机/回退**：消费者任一必需字段不兼容时只发布旧包，新包保持影子；不得通过复制投资状态到上游来兼容。

## 8. W6 Worker 持久断点及受控并发

- **依赖**：W1–W5 的生产契约及 W0 持久状态设计；独立 Worker 恢复计划允许的测试门禁。
- **建议落点**：R4 C05 的 `automation/store.py,worker.py`、C07 的 catalog writer、`scheduler_policy.py` 和独立计算进程；保留 `producer_attempts` 作为审计。`processing_demand.py` 当前纯内存，`service.py` 当前长批调用持 catalog 操作锁，不能直接多开现有 Worker。
- **顺序**：按 [多文档并发实施手册](worker_parallel_execution_plan.md) N0–N6：先修 AUTO claim/finish/outbox，单执行者完成跨库对账与暂停故障测试，再把不同文档的锁外计算逐步扩到 2、4 等在途上限；复杂文档多 agent 核验单独评估。
- **必须验证**：claim/心跳/ACK 丢失、旧 epoch 返回、进程强杀、文件 rename 后崩溃、DB commit 后崩溃、429/磁盘满/SQLite busy、retired、暂停临界点均可恢复或失败关闭；同 work key 至多一个 accepted artifact；P09/P10 终态 skip；429 页 PDF 不长期阻塞其他文档；SourceOnlyStage 白名单不被绕过。
- **停机/回退**：单执行者可靠性未过即不并发；并发无实测收益或质量/成本越线退回单执行者；生产 Worker 保持暂停，恢复仍需现有专项计划和用户授权。

## 9. W7 旧库与空间迁移（独立变更）

此卡处理新流水线后的**最终**冷热分层；释放现存 46 GiB 主文件有更早的独立[F0–F5 提前退役卡](early_catalog_retirement.md)。F 路径实测 active-only 库 2.849 GiB，要求旧库压缩包全量解压流 SHA/长度与原库完全一致、旧证据归档提示、下游差分和文件级清理审查；按用户要求**不做完整落盘恢复演练**。不依赖 W3–W6 交付，但不能让 Worker 再用旧全量 normalize 写回。

经新方法判定不重要的旧原文另按[原文处置 D0–D5](raw_disposition_plan.md)实施。W3 的 `skipped_*` 仅提出候选，不能直接触发删除；D4 必须有独立处置合同、完整负例覆盖、来源所有权与路径复核、下游引用审查和持久删除 receipt。共享 SQLite 的 46 GiB 仍由 F 卡整体退役。

- **依赖（仅 W7 最终迁移）**：W3–W6 的影子/小批实测，全文检索按需回源与 W5 消费合同通过；单独的迁移和恢复审批；迁移前先核独立卷/快照与主库+副本+WAL+重建临时空间的最坏字节预算。此前 C 盘空闲约 77.56 GiB，放不下两份约 46.27 GiB 的完整主库副本；F 快路径改用实测 2.849 GiB 活跃库和压缩快照，另按实际峰值预算。
- **允许修改**：未来单独迁移分支、一次性迁移工具、临时副本及审计记录；绝不把空间清理塞进选择器上线补丁。
- **顺序**：① 只读列出 SQLite 文件、表/索引大小、paragraph/table-cell/空 cell 行数、JSON 负载、引用量及下游活跃引用；当前 Python SQLite 无 `dbstat`，精确表/索引分解须选经审查的离线工具或副本方法，不能用 1000 条样本推算冒充；② 在副本上做完整流式备份 SHA/长度、行数/哈希/外键验证与文件级切回测试，不进行完整落盘恢复；③ 选择一小批旧 span 影子归档并逐查询差分；④ 定义保留期、tombstone 和回滚窗口；⑤ 以真实磁盘字节、p95 查询延迟、召回/定位结果比较；⑥ 审查通过后才安排生产迁移。
- **必须验证**：恢复副本可查询；同一来源旧/新导出可重放；撤回和纠错均有效；只读检索对照无关键证据损失；记录迁移前后 DB、WAL、备份、归档总字节而非只报主 DB 缩小。
- **停机/回退**：没有可恢复备份及最坏空间余量时 W7 不开工；任何引用丢失、外键/哈希不一致、回源延迟超门槛立即停止并从已验证备份恢复。不能直接清理约 46 GiB 生产库；空间收益若未经实测只能写“未知”。

## 10. 交付顺序

`W0 契约 → W1 来源 → W2 结构 → W3 选择 → W4 摘要 → W5 导出 → W6 Worker → W7 最终迁移` 是实现依赖，不是八次独立审查。G0 审 W0、G1 合审 W1–W4、G2 审 W5、G3 审 W6、G4 审 W7/删除批次。已获授权的旧主库提前退役另按本轮 `F0 → F5` 运行卡执行。`accepted_scoped` 只记录 G 节点范围，不自动表示生产上线、跨仓改动或解除 Worker 暂停。

逐来源原文回收按 `D0 盘点 → D1 处置合同 → D2 负例验证 → D3 候选审查 → D4 精确路径删除 → D5 对账恢复`。D0–D3 可与 F 卡只读准备并行；D4 依赖 W5 对处置状态和旧 span 的失败关闭验证，且不能与同一 source 的解析/导出并发。
