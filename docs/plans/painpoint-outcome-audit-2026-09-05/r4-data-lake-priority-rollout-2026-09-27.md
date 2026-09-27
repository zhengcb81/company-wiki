# R4 位置透明数据湖优先实施卡（2026-09-27）

> **本页是 [R4 唯一活动编排](simplified-execution-plan.md) 的实施细化，不另建计划或审批门。** 下述旧的“RF 不必并线／company-wiki 产品代码暂停”属于并线前快照；用户现指定先并 RF、再实施抽象层。RF 远端 `main=3a69f9c5b6516ebc949d1c95bd50965f9112b7ad` 已核对，当前在独立 CWP 工作树实施以保护主树未提交改动。现有 A v0.4.2 的 A.DR/A.VR 为 `accepted_with_findings`、历史 A.AR 为 `rejected`；后续 A08 处置已解决其中多项，但旧裁决原文不改。只对当前合同与真实样本做一次增量独立审查，然后在隔离工作树实施 B；B/C 的正式路由按各自大节点 E2E 和 AR 签收。**C.local 先验基础来源 reader，不等待叙述 W5/G2a；G2a 后续复用已通过的 reader 收据，再验 selected evidence package。**

### 2026-09-27 单用户简化裁决（覆盖本页较早的“权限”措辞）

本项目是个人资料湖。用户已明确裁定**取消 `private/public` 区分，全部已配置来源允许外发给 LLM**。本地 query、预览、SourceExport 和正式财报复用采用同一读取规则；`privacy_class`、`reusable_for_filing`、根类型和物理路径不授予或剥夺读取资格。正式复用仍要求具体来源的报告期、来源 URL、采集记录、身份声明无冲突和完整字节 SHA；不同 SHA 不替代，已撤回或损坏的版本拒绝。`read_only`/写目标仅约束采集写入位置，文件大小、类型和状态过滤只用于解析能力与资源控制。先用 TDD 消除新 v2 reader 的根标签门控，再迁移 filing-fetch 旧 resolve 分支，最后删兼容字段；不为了删配置而改变旧消费者结果。

本页下方历史步骤若仍写“权限”“批准 root”“private/public oracle”，实施时统一按上段解释：只检查操作系统可访问性、已配置根范围、显式联网/删除动作和来源事实；**不再创建根级隐私等级或外发审批门**。历史 A/VR/AR 收据作为已有证据复用，不因新字段再单开一套签收；只有合同变化或大节点真实 E2E 暴露的新风险才补一次增量复核。

当前隔离 CWP 实现已让同 SHA 的任一已配置副本回退读取，RootPolicy 3.x 不再强制根标签，隔离配置删除四根的 `privacy_class`。用户明确授权后，`llm_summarizer.py` 的标签外发否决也已移除；GP003 八项测试通过，其中规范化工件被篡改和旧根遮蔽新根两项曾先红后绿。摘要路径仍用来源 SHA、规范化工件实际 SHA 和现有审查收据绑定当前字节，这属于内容与来源校验，不重新引入目录权限。旧 schema 字段暂留兼容，随消费者迁移清理。

简化的后续 TDD 顺序：① CWP 真实多根读链确认根标签、优先级、目录移动不改变 source/version/业务元数据，冲突侧车仅按来源事实拒绝；② filing-fetch 的 v2 本地复用只做 `query_local` 与来源候选资格判断，返回 pathless ref，不先 `open_version` 读整份 PDF，也不二次解释 `canonical_path` 与根白名单，旧入口保持兼容；③ RF 等最终需原文的消费者凭该 ref 调 CWP 当前 `open_version` 一次取得已验字节，StockWiki 消费路径无关导出，关闭各自的路径分支；④ 旧 RootPolicy 1/2/3 wire hash 兼容期不变，新完整读取指纹只作审计或明确要求的单次快照一致性，不跨仓硬 pin；消费者全切换后删除重复根资格、路径校验和多余配置字段。跨仓测试分别验证零下载、无双重全文读取、同 SHA 回退、移动/优先级改变后仍可用、当前实际策略与真实文档不改动。每个大节点审一次，不给每个小字段另建签收门。

**C.local 当前实测差距（按时间保留）**：首轮隔离三仓真实 E2E 中，FF v2 候选经 legacy `resolve` 先核整份 PDF，RF 又打开一次，因此曾有两次全量来源 IO。随后 CWP 增加仅查 DB 的候选投影，FF 的显式 `--source-ref-v2` 入口改走 `source_query_cli`；更新后的三仓真实 E2E 和 FF↔CWP 真实集成均已绿，候选阶段不再做来源字节验真，RF 最终 `open_version` 才逐字节核 SHA。同尺寸篡改反例表明候选仍可列出、最终打开会拒绝，证明没有以省读取为由省掉终验。**这是隔离 opt-in 路径的结果，旧 FF 默认入口尚保持 legacy 行为，正式生产路由与 StockWiki 全链未切换；也尚未用 OS 级计数器签出“恰好一次文件打开”。**下一大节点应测候选零来源字节读、最终一次完整验真、旧兼容与 StockWiki 接线，再决定默认路由切换。CWP/FF 两处 `retrieved_at` 分别是共享版本记录与一次采集位置观察，不是稳定版本身份；RF 只对 source ID、SHA、长度及可靠的发行人/期间/title/URL 做硬一致性，将两个采集观察和取值出处都留 trace，不用它们错拒同一版本。

**C.local 审查时间一致性（隔离 opt-in 已修）**：原来 `capture_ready`/`prompt_injection_status` 只在候选 DB 查询时计算；query→open 间撤回审查，RF 可沿用旧 `not_detected`。撤回反例先红，现由 CWP 在原文字节验真后读取当时可见的 review，随同一次 `source_reader_cli` 成功收据返回状态及 source/evidence/rule hash；RF 严格校验最终收据，只接受与已验 source SHA 绑定的 `not_detected`。真实三仓 E2E 在 FF 选出候选后撤回 review，最终 RF 已拒绝；没有为此增加第二次全文读取。收据表示读取时的审查观测，后续撤回由后续请求重新查询；**它不是跨整个消费者生命周期的数据库锁**。正式默认路由、StockWiki 实接与 OS 级 I/O 计数仍归 C.local 大节点验收，不额外建签收门。

**跨仓隔离回归收据**：FF `python -m pytest -q tests` 为 **379 passed、13 skipped、78 subtests**（有 1 条既有测试线程解码 warning），Ruff/Mypy/diff-check 绿；RF v2 相关 13 个测试文件 **81 passed**，Ruff/Mypy/diff-check 绿；CWP reader/query/真实字节相关 **33 passed**，Ruff/diff-check 绿。三仓 E2E 通过正常来源、旧 root 标签 false、同尺寸篡改拒绝和测试夹具恢复。仅限三个隔离工作树的显式 v2 opt-in，尚未提交/合并。`latest_as_of` 与授权下载仍走 FF 旧 ensure/resolve，可能重复全文 I/O；须把这两个请求型态纳入 C.local 成本与兼容测试。`detected_and_ignored` 的 v2 候选继续保守 hold：自动审批曾拒绝仅凭无可复验签名的 disposition 字段放行，当前不将其算成功复用。RF 缺 title 仍 fail closed，待来源字段独立核实后再决定是否放宽。

### 全仓结构审查后的进一步简化（2026-09-27 增量）

本轮用 CodeGraph 盘点了仓库内 **559 个 Python 文件**，其中 `source_catalog` 83 个；随后逐条核对主要运行入口、文件读写和现有测试。它是全仓结构审查与热点代码核查，**不是逐行签收全部文件**。下表列的是可验证的重复责任；执行前还要用真实样本与运行观测确认收益，不凭文件数量推断可删空间。

| 优先级／证据 | 简化动作与唯一责任层 | 先写的失败测试／退出旧链条件 |
|---|---|---|
| **S1 来源读取与旧权限**：`resolver.py` 旧默认复用仍按 `reusable_for_filing/reusable_root_kinds` 分流；`policy.py`、`policy_2x.py`、`policy_3x.py`、新读取指纹并存。 | 新读链只由 CWP `query_local → open_version` 裁决当前副本、来源资格和字节 SHA；FF 返回 DB-only 候选，不读 PDF；RF 最终一次 open；旧 wire 兼容结束后删除根级复用/隐私字段和重复 pin。`config_doctor.py` 已 TDD 改为通用根校验。隔离 FF v2 opt-in 已改为 DB-only，最终审查收据绑定也已在隔离读链实现；旧默认 resolve 和生产切换仍待完成。 | 目录搬迁/优先级调换、同 SHA 回退、旧 ref、不同 SHA 拒绝、FF 零下载/零全文读取、RF 最终一次完整验真；query→open 撤回 review 的真实三仓负例已通过；全链来源 IO 用计数器确认。FF/RF/StockWiki 新入口均不需 raw path，旧入口保留到消费回归通过。 |
| **S2 工件读取完整性与重复加工**：`llm_summarizer.py`、`summarizer.py`、`section_extractor.py` 曾分别从数据库 `normalized_path` 读文本；原文 SHA 无法替代规范化工件 SHA。当前 4,969 条 completed/partial normalized 行只对应 3,500 个文档，**1,469 个文档各有两条可读工件**。 | 唯一 CWP artifact reader：新行核 DB source ID/SHA、生成器版本、工件实际 SHA 与状态；旧行（4,984 条中 4,797 条 DB `source_sha256` 缺失）只有实际工件 SHA 匹配且 frontmatter 中 source ID/SHA、parser name/version 与 DB/当前来源一致才只读复用，不能全库重做 PDF 或盲回填。三个消费者先按同一文档/版本**确定性只选一个**（modern 优先、否则 legacy）；选中损坏留下失败，不在同批次再发旧副本造成重复付费。旧兼容分支随旧工件自然退役。 | 改文件/DB lineage/frontmatter 或错 parser 时三消费者拒绝；已验历史/新工件可用。双工件夹具断言一次摘要/章节及 LLM `generate` 恰好一次；少量真实旧工件只读核兼容范围并统计拒绝原因，不把旧工件自动升级新 schema。 |
| **S3 全文与章节重复存储**：`normalizer.py` 先整篇 PDF→`normalized.md`，`section_extractor.py` 再写多份章节 `.md`/`index.json`，两种摘要再各写 `summary.md`；`narrative_evidence.py` 的精选能力当前主要由试点/检索入口调用。 | 先按文档身份/类型、页标题和轻量文本做 **triage**，只有叙述候选才做页/段定位与精选；财务表和一般性格式文件留来源 manifest 并记可解释 skip。招股书、再融资、IR、电话会按各自版式选择，TXT 电话会直接定位。生产只保留 raw + 必要的已验定位/精选摘要；全文 MD 作为可重建暂存，先验证下游无引用再退役，不在扫描阶段无条件复制。 | 先对年报/半年报/季报/招股书/定增或可转债/IR/TXT 电话会各取真实样本，测有价值内容召回、页码/发言人 locator、误跳过率、每份新增字节、旧新耗时；全量删 MD 前先证实 StockWiki/RF/检索可从 raw 复现。 |
| **S4 Worker 双体系**：`source_catalog/worker.py` 周期性串行调用 scan→normalize→sections→LLM→export，配置有多套批量/重试/轮询参数；`automation/worker.py` 已有 claim、lease、retry、outbox，却尚未承接这条生产链。`scripts/scheduler.py` 另有 legacy daemon。 | 保留一个用户可暂停的 supervisor；将每个来源版本的 parse/selected-evidence/summary/export 变为持久 job，采用 `(source_id,SHA,stage,generator_version)` 幂等键和租约恢复。多个独立进程并发不同文档，单文档同一阶段独占；每进程自有 LLMClient，分别限制解析进程数、LLM 并发/费用和临时空间。旧周期 Worker 只负责发现与投递，可靠队列真实 E2E 通过后退休；不要直接给含全局状态的 LLMClient 加线程。 | 两文档确实重叠运行；同文档不重复提交；杀进程/租约过期/重复消息/断电后重启均恢复且无丢失、无重复外发；暂停即停止领新任务，在途完成或可恢复；隔离测试目录前后相同。验证旧队列与新队列不会同时处理同版本。 |
| **S5 上下游职责**：legacy `scripts/scheduler.py` 默认步骤仍包含 `assess/distill/judgment/consolidate`，`legacy_research_ingest.py` 仍在树中；AGENTS 已规定 StockWiki 独占投资语义。 | 把 source-only CLI/Worker 设为唯一可启动生产入口；legacy 研究 writer 只作历史读取/迁移，核调用点后从默认调度、自动启动和文档推荐中移出。`automation/registry.py` 中 `analysis.*`/`gold.*` job 逐项确认是否仅是来源质量；投资语义迁至 StockWiki，不能仅凭名称删除。 | 静态入口表 + 控制台命令 E2E 证明 CWP 不写研究结论，旧兼容读取仍可用；任何真正使用中的迁移消费者先有替代入口再移除。 |
| **S6 空间处置重复流程**：`duplicate_cleanup.py`、`focus_cleanup.py`、`archive_retired_evidence.py`、`prune_retired_evidence.py` 各自维护计划/收据/删除路径。 | 最终收敛到一个按 source/version 生成的处置 ledger：引用闭环→预估可回收字节→删除/保留决策→逐文件 SHA 与状态核对→执行→可追溯结果。优先退役可重建全文与精确重复文件，不删唯一 raw 或证据引用仍在用的文件；跳过加工的低价值来源也按同一 ledger 判定。 | 在独立测试目录真实创建多副本、缺副本、旧引用和 skip 案例，核只删目标文件且剩余引用仍可解析；旧 46.266 GiB DB 已按 F0–F5 退役，后续只针对当前 39.744 GiB 基线逐项分类与核实实际回收，不做完整备份恢复演练。 |
| **S7 LLM 前置复核空转**：现行 23,530 个 document 中只有 **22 个**有 `prompt_injection_review` 收据；3,500 个有 completed/partial normalized 的文档中也只有 **22 个**有该收据。旧 `llm_summarizer` 要求先有收据才选择文档，而仓内曾产出 2,734 件 LLM summary，说明旧摘要与当前新入队资格不能混当覆盖率。 | 新选择性 DAG 对**即将发送的同一批已验字节**自动运行确定性 prompt-injection 扫描，为 `not_detected` 自动写 source SHA、输入字节 hash 与规则版本收据并继续；只有扫描命中、不可读或字节/规则漂移时进入 `needs_review`，不把 23,530 件文档逐件人工签收作为常规前置。旧收据只用于历史兼容；不删除 prompt-injection 内容隔离与源/工件 SHA 校验。扫描输入和实际 LLM 输入必须由同一已验缓冲区产生，不能让无关的 hash 字符串当 review evidence。 | TDD：干净真实招股/IR 文档自动取得收据并完成一次摘要；注入夹具不外发；扫描后文件篡改、重复消息、规则版本变化均拒绝或重扫；同次运行计实际扫描/LLM 次数、成功覆盖与误拦率。G1 小试验证价值与误拦，G2/Worker 大节点真实 E2E 后才切生产路由。 |
| **S8 CI 重复与假绿**：`.github/workflows/ci.yml` 在 3 个 Python 版本先跑 unit、contract，又跑全 `tests/ --cov ... || true`，随后重跑属于 contract 的 6 组 canary；CLI smoke 的 `collect_news.py --help || true` 也可吞失败。 | 每个版本保留一次会传播失败的分层测试，覆盖率只在选定版本从同一次测试生成并核门槛；canary 若已有同 ID 合同覆盖则取消重复启动，真正独立的变异用例保留。静态计划检查只跑一次；不要靠旧 coverage.json 或测试文件名 ratchet 假装行为通过。 | 先列 pytest collect ID/skip 集合与现有 gate，修改 workflow 后用故意失败的临时测试证明该 job 失败，并核 coverage.json 为本次产物；六组来源 SHA/授权/拒绝反例仍实际执行。量 CI wall 时间再确认收益。 |
| **S9 StockWiki 隐式旧来源回退**：`stockwiki/services/pipeline_source_provider.py` 的 disabled/not_configured 返回空 provider，`cmd_enqueue_news_jobs` 转排 `news-fetch-tavily`；weekly planner 也只在 provider 有效时移除旧任务。当前 `config/source_provider.yaml` 的 company-wiki 明确 disabled，这是现行 legacy 模式。 | **等 C.local v2 正式接入并显式启用后**，用一个用户可见的来源模式选择 `company-wiki` 或 `legacy_news`；前者失效则停排并报错，后者才允许 Tavily。来源决定只在 StockWiki 配置/调度层，不由 CWP 根目录或物理路径推断。当前 disabled 行为先保留。 | 两种模式的实际 CLI/weekly E2E：启用后 provider 失效或配置漂移时 0 Tavily/0 双采集；显式 legacy 仍可抓取。对比任务队列和费用调用，不为临时 provider 故障自动切换市场源。 |
| **S10 依赖与 CI 安装面**：`pyproject.toml` 已把 PDF、download、catalog 列为 extras，`requirements.txt` 却将 PyMuPDF、Playwright、docling/Office 解析器全列入，CI 每个测试矩阵及 CLI smoke 均安装全套。 | 先量安装时间与失败率，再把 core reader/query/export 与 parser/download 测试分车道；core 只装 core，格式解析车道装对应 extras。可选包缺失给明确 unsupported，不在 import 时崩溃。不要在无收益证据时为了拆包新增维护负担。 | core-only 环境跑真实 query/open/export 与 CLI smoke；带 extras 环境跑 PDF/HTML/Office/下载相邻合同及真实样本。比较三版本 CI wall、包体与错误率，收益不足则不实施。 |

**审查与落地状态，不把方案当成果**：CodeGraph 索引 559 个 Python 文件用于结构覆盖；对上表涉及的主入口、调用链、配置和存储副作用做了热点核查，并以生产 catalog 只读统计及隔离真实资料实验交叉验证。没有逐行审阅全部 559 件，也没有穷举动态导入、所有定时启动方式及全部下游调用者。后续不设“全文件逐行审完”空泛门槛，而在旧入口删除/生产切换前对该入口做一次真实调用者枚举和对应 E2E。

| 项 | 当前状态 | 下一个可判定动作 |
|---|---|---|
| S1 | CWP/FF/RF 隔离 v2 opt-in 的最终 review 收据、撤回反例和局部真实链已绿；StockWiki 正式入口、旧默认及 `latest_as_of`/授权下载迁移未完成。 | 用同一真实语料测普通本地、`latest_as_of`、授权下载的全链 I/O 和旧兼容，再接 StockWiki、切默认入口。 |
| S2 | 隔离唯一工件 reader、双工件一次选择及旧版兼容已定向绿；生产目录只读抽样 11 件有 3 件按规则拒绝。 | 以被拒原因形成统计与修复/跳过规则，合并真实摘要/章节/LLM 消费回归后切读入口；不批量重解析旧 PDF。 |
| S3 | 已有精选试点代码与空间账，生产默认链尚会生成整篇 MD/大量 span。 | 七类文档真实小样本测召回、误跳过与新增字节；新 DAG 首先锁旧式 span/MD 零增量，再谈 derived 退役。 |
| S4 | 持久 job 基础能力与串行来源 Worker 并存，尚未接成一条生产链。 | 隔离双文档并发、重复消息、kill/restart、pause/resume E2E；选单一写 owner 后再退役旧 loop。 |
| S5 | legacy 研究 writer 与 source-only 边界仍并存。 | 枚举真实启动与动态调用点，逐一将默认入口指向 source-only；StockWiki 接住投资语义后停旧 writer。 |
| S6 | 旧 46.266 GiB 库已有退役收据；剩余 39.744 GiB 尚未逐文件核可回收关系。 | 建唯一 ledger dry-run，按 SHA、引用和重建性计算各类可删上限；隔离真实删除/恢复原样后逐项处置。 |
| S7 | 仅 22 个来源有当前 review 收据，自动清洁扫描尚未进入正式摘要 DAG。 | 同一已验缓冲区扫描并外发的红绿测试，先在真实招股/IR/TXT 小样本核覆盖与误拦，再并入 Worker。 |
| S8 | CI 重复与 `|| true` 经 workflow 原文核实，尚未改 workflow。 | 在不增加新审批门的前提下合并重复运行、让失败传播，用故意失败夹具和当次 coverage.json 验证。 |
| S9 | StockWiki 当前明确 disabled，旧 Tavily 回退是现行模式，尚不能删除。 | C.local v2 激活后用显式来源模式替换隐式回退，再验 CLI/weekly 队列与费用。 |
| S10 | extras 与 requirements/CI 安装不一致，收益未测。 | 先量 CI 安装时长与 core-only 能力；收益足够再拆测试车道。 |

**空间基线更正**：旧 49,677,344,768 B（46.266 GiB）主库已在 2026-09-26 的 F0–F5 中退役，同卷可用空间净增 37.630 GiB；不是接下来仍需处理的 46 GiB 文件。[D0 当前盘点](../narrative-evidence-pilot-2026-09-26/d0_inventory_receipt_2026-09-27.md)给出本仓三个自有目录合计 **39.744 GiB**：`companies/` 23.460 GiB、`.source_catalog/` 11.435 GiB、`source_manifests/` 4.850 GiB。后两者含 active 库 2.846 GiB、旧库完整压缩备份 5.773 GiB、`derived/` 2.632 GiB、退休证据归档 4.850 GiB；旧索引 0.042 GiB。D0 的同 SHA 本地重复候选理论差额仅 **98,845,393 B**，不是可删证明。当前主库只读 stat 为 3,055,800,320 B（比 D0 多一页）；本轮未重新走访其余目录。下一步空间收益应写成 `39.744 GiB + 新产物 P − 经核验派生 D − 经核验重复 Rdup − 经核验低价值原文 Rskip`，备份、归档、索引只有各自引用与保留条件通过后才另计，不能再宣称“尚有 46 GiB 待删”。详见[逐步空间账](../narrative-evidence-pilot-2026-09-26/stepwise_space_budget.md)。

**46 GiB 的成因与防复发优先级**：旧库的膨胀主要是逐表格单元持久化的大量 `evidence_spans`、重复字段的 `span_json` 与索引；它不是仅靠删除 `normalized.md` 就能解决。此前只读样本约有 2720 万 span，1000 条抽样中 820 条是 table cell、496 条 `raw_text` 为空，`span_json` 平均 812.6 B；全库各表/索引的精确占比尚未测出，不把样本外推成释放比例。当前 active-only 库仍有 **1,490,530** 条 span。S3 的首个生产约束是新 DAG 对入选、跳过文档均 **零新增旧式全量 `evidence_spans` 和 `normalized.md`**，只保存可回读的精选证据与紧凑覆盖账本；随后才依据引用核验逐件退役旧 derived。空间验收分别报“新增每份文档字节”和“同卷实际释放字节”，不能混算。

**最终应收敛成的最小运行结构**：① 一个 source/version 目录和可验证 reader，root、目录和同 SHA 副本仅是存储细节；② 一个规范化工件读取器，所有摘要/切片先核工件字节；③ 一个按文档类型做轻量全篇覆盖、只对有价值叙述深解析的 DAG；④ 一个持久 job 队列与可暂停 supervisor，用独立进程同时处理多份文档；⑤ 一个来源处置 ledger，唯一处理保留、跳过、去重和精确删除。每块只保留一个生产 owner、一个版本合同和必要的兼容入口。新旧链并存期间明确谁可写、何时退役，不能为每个消费者复制一套 root/隐私/路径策略，也不新增逐小步签收委员会。用本层单测、相邻合同测试和 B/C/G/Worker/空间五类大节点真实 E2E 验证。

**配置面也要减法**：当前 `config/source_catalog.yaml` 的 `reusable_root_kinds`、逐根 `reusable_for_filing` 与 `privacy_class` 是旧资格/外发策略；隔离配置已先删隐私标签。待 FF/RF/StockWiki 新合同回归通过后，生产配置只让 root 声明存储事实（ID、kind/adapter、位置、优先级、写入目标/只读、解析资源上限），来源能否复用由来源版本事实决定。旧 Worker 的逐阶段 batch/retry/poll 参数与新队列租约设置不可两套同时成为运营旋钮；切换后控制面只暴露暂停状态、解析并发数、LLM 并发/费用、临时空间上限及一套有类型的重试策略，特殊阶段覆盖须有实测理由。先列配置键真实读取者和旧值映射，再删旧键；未知键仍明确报错，不默默忽略。

**同名 hash 不混删**：本轮要去掉的是把 root 位置/标签快照当成跨仓读取资格的硬 pin。`prompt_injection` 审查使用的规则集 hash、显式下载/删除 action receipt，以及 source/工件内容 SHA 各有独立用途，不能凭名称含 `policy_hash` 就一并删除。实施者先按生产调用链列字段 owner 与验证对象，再逐处裁掉重复的 root 判定。

**近期落地顺序**：先完成 S1 的 CWP/FF/RF/StockWiki 新合同与真实资料 C.local，再做 S2 的统一工件读取；S3 的 triage/保留规则和 S4 持久并发 Worker 可在隔离目录 TDD，S7 与精选摘要入口同批实现，只有 C.local 与叙述 G2a 的真实 E2E 通过才迁移生产任务。S5/S6 随相应消费者与空间节点收尾。S8 可在不影响产品路径时独立简化；S9 必须等 StockWiki v2 激活，S10 先量收益再决定。每项只在上述大节点独立审查一次，局部实现仅跑本层和相邻合同测试。**待测量项**：当前 39.744 GiB 中各文件的真实引用/可重建关系与可回收量、旧 Wiki/StockWiki 消费范围、现存自动启动路径、两 Worker 同时运行风险、不同类型文档的精选召回与峰值内存；未量到前不承诺固定节省比例。

### 分层责任与最少测试组合

| 层／owner | 本层单元测试 | 相邻合同集成测试 | 大节点真实 E2E |
|---|---|---|---|
| Catalog／CWP | source/version、字段 provenance、权限/时点/撤回、冲突不随 root priority 变化 | 临时 SQLite + 原生 sidecar，沿用 L02、L08–L11 | B.AR 审真实多根 metadata 与 old-ID 重放 |
| Storage/open／CWP | 同 SHA fallback、完整 hash、路径越界/TOCTOU、拒绝码和资源上限 | 四隔离根撤副本、移动、篡改、ACL、取消，沿用 L03–L07/L12 | B.VR/B.AR 用 P06 四副本及 company/dayu/Dropbox 原生样本验 `query_local→open_version`，前后目录恢复 |
| Producer/export／CWP | parent source/version、locator、quality、撤回、v2 路径无关 ID | 临时 raw→上游工件→只读 export；v1 `cw1_*` 回放 | C.local 验基础来源导出；W5 后 G2a 只加 selected package |
| filing-fetch／自身仓 | 本地来源候选、显式下载授权、零全文读取 | 其真实 CLI 对隔离 CWP query，不读上游 raw path | C.local 星环真年报二次零下载复用 |
| RF／自身仓 | `needed_roles`、已审资格、拒绝原因 | `source_preparation` 正例与 `not_reviewed` 负例，不导入 CWP DAG | C.local 微软真实来源形成 RevenueSourceRecord，负例仍拒绝 |
| StockWiki／自身仓 | v2 strict reader、路径无关 ID、v1 兼容 | 新入口无 `--source-root`；历史 `cw1_*` 回放 | C.local v2 dry-run，同字节移位前后身份与结果不变 |

变动只运行所属层单测与相邻集成；跨层合同变更再运行受影响消费者集成；B.AR、C.local.AR、G2a、Worker 恢复和空间回收各在自己的大节点跑完整真实 E2E。保留现有 L/P/O/M 测试 ID，不为每个小步建新审批表。

**实施顺序采用 TDD。** 对每个尚未满足的层级合同，先写一个可观察的失败测试（red），保存失败命令和原因；再做最小产品改动使其通过（green），最后在测试保护下整理实现（refactor）。测试应从调用者可见的输入、输出和副作用断言责任边界，避免只复述内部实现。修 bug 时先补能复现该 bug 的测试；已有绿测试不重写成红测试。每个小步仅跑所属层单元测试和直接相邻的合同测试；只有上述大节点才集中跑真实资料 E2E 和独立审查。首个切片是路径无关 `SourceRef → open_version`：测试不得给读取方原始路径，须覆盖同 SHA 副本故障回退、不同 SHA 不替代、坏字节拒绝、权限与零隐式网络/写入；现有 `read_verified_bytes(handle)` 可作为内部字节校验原语，但不能成为跨仓输入合同。

## 1. 结果合同与分层边界

使用者按实体/证券、文档类型、报告期间、公开时点、所需能力查询；业务返回值只能引用 `document_id + source_id/版本哈希 + locator + artifact/schema 版本`。路径、root、location、I/O 优先级只能用于内部读取与诊断。**同 SHA 的同一版本可有多个位置；不同 SHA 必须保留独立版本，修订关系须有来源证据。** 根目录不是文件类型、可信度、公开许可或外发权限的代理。

**当前 ID 迁移缺口：**现行 scanner 对有原文的记录以 `_document_id_for_source(source_id)` 生成 `document_id`，因此它实际是版本相关 ID，尚非上表目标的逻辑文档 ID。首个 TDD 切片沿用旧 `document_id + source_id + SHA` 做精确版本读取，不宣称已经完成逻辑文档/修订关系抽象。B04 须先用真实更正公告确认同一逻辑文档的合并依据，再定义独立 `logical_document_id` 与旧版本 ID 映射；不同 SHA、缺权威修订证据时不能按文件名合并。旧精确版本引用须继续可读或明确报告该版本已无可用副本。

| 层和唯一 owner | 实施边界 | 不能向上泄漏的决定 |
|---|---|---|
| company-wiki catalog | 现有 `sources/documents/locations`、实体/报告身份、版本、字段级 provenance 与冲突、extraction quality、撤回/时点 | 不用扫描先后/root priority 选业务事实；不以同 SHA 副本洗白许可 |
| company-wiki storage/open | 注册 root 的 adapter 解析布局与 sidecar；仅从**同版本**健康副本取得实际验证的字节；失败报告不可用/权限/需水合/哈希漂移 | 不把 `canonical_path` 当权威身份；不因缺首选副本自动下载或换版 |
| company-wiki producer/export | normalized、选定 EvidenceSpan、来源摘要等上游工件；版本化、只读导出及旧引用重放 | 不生产 RF 的 `consumer_analysis`、投资结论或 StockWiki 状态 |
| filing-fetch 与来源 provider | 精确请求、候选发现、经授权的获取；新 raw 交 canonical writer 的受控收件区 | 不自行建第二个 catalog/权限中心；固定写入地是所有权，不影响旧资料从任一批准 root 读取 |
| RF、StockWiki、quick-scan | RF/StockWiki 通过来源与证据合同消费；quick-scan 仅可选身份映射 | 不依 root/path 分支，不导入上游 DAG，不跨仓写 CWP DB |

合同至少含 `query_local`（只查已索引集合、零网络/写/Worker 控制）、`open_version`（锁定指定 source hash、实际交付字节完整核验）、`request_work`（显式缺失来源/产物请求、独立预算与持久任务）。`latest` 只表示湖内截至时点最新版；联网 refresh 是另一个动作。读取能力、来源/身份质量、处理状态、按来源和动作的权限分别表达。错误至少区分 `not_found/not_indexed/unavailable/blocked/ambiguous`，协议版本不兼容另有明确错误；不得静默回退到 company 根或另一个修订。

### 必须在 A.DR 冻结的跨进程 open 细则

1. **验证时点**：消费者拿到可使用的正文之前，完整 SHA 与指定版本必须成立。流式交付若在末尾才验 SHA，消费者此前只能暂存、不得解析/引用/提交；如不能强制此约束，就先在受控私有临时区完整物化和验证，再交付只读句柄。`resolve` 返回 handle 不等于已验交付字节。
2. **大文件与资源**：不得把 PDF/TXT 整篇塞进 JSON 或无界内存。合同冻结最大输入字节、分块大小、并发临时峰值、空间不足与取消行为；用真实 429 页招股书和 8.16 MB 10-K 量测。纯 `query_local` 不造缓存；若 open 需要物化，显式记为准备动作，收据包含 run owner、私有目录/ACL、TTL、引用次数或租约、到期/取消清理与进程崩溃恢复，不把写入藏在“只读”名称下。
3. **竞态与版本**：选取、打开、读完、验证跨越文件被替换/重指时，只能返回该 SHA 的完整字节或失败；不得靠 mtime、文件名或 catalog 宣称代替核验。路径、受控临时句柄可用于传输/诊断，不能进入稳定证据 ID、业务元数据或导出身份。N-1 客户端兼容由一个边界 adapter 明示转换；未知 schema/policy 拒绝。
4. **动作边界**：已配置来源不按 `private/public` 限制本地读取、加工或 LLM 外发。采集联网、生产 Worker 启动和原文删除仍按各动作既有授权与大节点验收执行；这些流程不得由一次普通预览隐式触发。相同 SHA 的不同采集记录仍各保留 provenance，不因位置合并而丢失来源事实。

## 2. 按依赖实施，不重复造门

| 顺序和对应 R4 步骤 | 具体交付与改动归属 | 大节点审查与停点 |
|---|---|---|
| **0. 跨仓基线钉住（RF 已并线）** | 以 RF 远端 `main=3a69f9c5` 为已合并代码基线，另记录 RF 原工作树剩余 dirty 运行记录但不捎带进入合同；记录 CWP/filing-fetch/StockWiki 当前 HEAD+dirty。对比 `company_wiki_source.py`、`source_preparation.py`、跨仓 E2E 与 CWP 当前修改，列 `canonical_path` 直接读取、root 特例、DAG 导入、SourceExport v1 路径字段。CWP 实施在隔离工作树，主树其他工位未提交改动只读保护。 | 若 RF 基线或消费者合同继续移动，仅增量复审受影响入口；不重做全套历史 A，也不把 CWP 主树 dirty 当作验收绿。 |
| **1. A01–A08 / 叙述 G0：合同和真实基线** | 沿用已裁决 A v0.4.2，补本页 open 语义、字段权属、旧引用/版本迁移、Source Provider v1→新合同路线；Data Reviewer 冻结下表真实样本的完整 SHA、原生 sidecar、独立 kind/期间/locator 与来源身份 oracle。基线只读，不重扫已退役的旧库。G0 复用 **A.DR** 一次合同审查；A.VR/AR 对基线与负例签各自既有结果。 | 修订关系或来源身份不明只 hold 对应正例，不用不同年度/故障夹具冒充。A.AR 只表示可实施 B，不表示读取器完成。 |
| **2. B01–B07：湖内读取与元数据** | 在现有 catalog/resolver/scanner/normalizer/policy 上做最小变更：root adapter 只解释布局；同 SHA 候选逐一验实际可读与能力，priority 最后仅排 I/O；metadata 按字段 provenance 合并并保留冲突；统一内部解析与跨进程受控 open；旧 source/version/locator 继续解引用。先证明当前实现失败的反例，已存在的 fallback 保留。 | B.DR 对 schema/协议/空间/回滚审一次；B.VR 在隔离真字节测试 L01–L12。若权限洗白、元数据随 priority 变化、交付未验字节、旧引用失效，B 路由不得切。 |
| **3. B08–B10：通用 reader 真实验收** | B 结果包分三栏：①同一真实 PDF 在四个隔离已配置 root 的位置等价与故障；②company/dayu/Dropbox 各自**原生**文件和 sidecar 的真实 adapter→query→verified open→locator；③第五个支持格式 root 只改注册、不改 reader。D0 在 `future_lake` 记录 1 件 545 B 原文，但尚未证明它是有代表性的原生文档/sidecar 样本，原生第四根覆盖暂记 pending；不能用改名副本凑数。此时的“consumer”仅最小通用协议客户端。 | **B.AR** 由非 oracle 作者独立核完整 SHA、业务投影、当前配置与前后副作用；未覆盖根只能签有限范围，不能宣称四原生根通过。通过后才给真实跨仓 consumer 接线。 |
| **4. C01–C04/C08：薄消费者与基础来源 export** | filing-fetch 改走一次本地 query/reuse 和受控 open；RF 改用版本/所需能力，退出 root/path 分支与 CWP `ROLE_DEPENDENCIES`，其研究缓存仍归 RF；CWP 输出新版本的路径无关**基础来源**引用和可回读证据。StockWiki owner 给新版 strict reader 与导入范围/撤回语义；旧 v1 通过稳定受控导出视图兼容，不能把原物理路径写进新身份。quick-scan 仅测可选身份关联。叙述 W5 selected package 不作 C.local 前置。 | C.local.VR/AR 独立签**基础来源 reader** 结果包；filing-fetch/RF/StockWiki 各走自己的实际入口。叙述 G2a 在 W5 完成后复用这些 reader 收据/同一测试设施，加测 selected package，不重跑无关 B 全套。任何 consumer 仍需原始 root/path/DAG，或本地查询触发下载/写/Worker 控制，只撤该 consumer 的新路由，B 不因此倒退。 |
| **5. C05–C10、G3/G4/D** | 持久 request/worker、并发加工、provider 正文获取、来源处置/空间回收分别沿用其现有权限、D.SAFE、v5 与大节点 E2E；可与隔离研究并行设计，正式上线取 B/C 对应 AR。 | C.local 通过不自动解除 Worker 暂停，也不授权生产下载、全量 StockWiki 同步或删除；每项只按其既有大节点推进。 |

**StockWiki 的实在泄漏**：当前 SourceExport v1 manifest 必填相对 `original_path`，它参与 `export_id` 哈希，v1 sync 又按 `source_root/original_path` 打开原文。`company_wiki_v1_adapter.py` 还把含路径的 manifest record hash 写进候选 `evidence_id`，从路径 basename 派生 `source_title` 并保存 `provider_original_path`；legacy sync 保存 `_resolved_original_path`。因此仅替换 CWP resolver 或只测新 export ID 都不足以证明跨仓位置透明。新合同须以 source/version/locator 决定 export、evidence、候选身份，标题取可信文档元数据；读取用受控 open。旧 v1 在兼容期保留稳定视图与旧 export/evidence ID 的显式对照和回放，不原地改历史 manifest；`provider_original_path/_resolved_original_path` 只留在隔离兼容记录，不进入新业务合同。待新增的**路径无关 SourceExport v2 reader/CLI** 的导入范围、同源重新导出、撤回和 supersession 需 CWP/StockWiki owner 于 A.DR 冻结。当前 StockWiki 生产 provider 仍 disabled；已有的配置 schema v2 只支持 sample/delta，现有 `--bundle` CLI 仍读 SourceExport v1，**full sync 不列入 C.local 放行**。

### 跨仓一律升级为来源接口，业务代码不得碰上游原文路径

这条约束覆盖 **StockWiki、revenue-forecast、filing-fetch、invest-quick-scan 和未来消费者**，不只约束 CWP 内部。CWP 对外保留一套有版本的本地 API/CLI（不要求先建常驻服务）和薄客户端：`query_local(request) → SourceRef[]`、`open_version(SourceRef, purpose) → VerifiedContent/receipt`、`resolve_evidence(EvidenceRef) → text + locator + quality`、`request_work(...) → JobRef`。这些是**目标操作/类型名，须在 A.DR 按当前真实 CLI 冻结，不是已存在的命令参数**。`SourceRef` 只含逻辑身份、版本、能力、质量、时点、策略结果及**带字段级 provenance 的展示/路由元数据**（发行人、证券、可信标题、文档类型、报告期间/发布日期）；缺标题返回 unknown 或已冻结的非路径后备值，不从 basename 猜。`EvidenceRef` 含 source/version、locator、parser/artifact 版本；跨仓业务代码只用这些对象。文件形态/目录只在 CWP adapter、storage/read broker 和 canonical writer 内部出现。最少一个跨仓 CLI 边界完成一次本地查询；大正文的传输形态按 A.DR/B07 的已验证字节、内存/临时预算冻结。若协议内部使用临时物化，路径及打开/清理由 CWP 传输客户端封装，StockWiki/RF/filing-fetch 业务与 source-provider 层只拿 `VerifiedContent`，不得接收绝对源路径或自行打开临时文件。

- **StockWiki**：source-provider 的新版本只接版本化 manifest/证据引用与 CWP verified reader；原文预览向 CWP 要受控流或已解析证据。其业务 service/sync 不拼 `source_root/original_path`、不直接 `open()` CWP/dayu/Dropbox raw、不把相对路径算进新 export/evidence/candidate ID 或标题。旧 v1 只留一个有期限的兼容 adapter/稳定导出视图，逐来源记录迁移和旧 ID 对照；该 adapter 不是新业务入口。正式关闭 v1 前回放历史 `cw1_*` 引用，并验同字节移位后新 export ID、evidence ID、标题、候选内容及状态全不变。
- **RF**：来源准备入口只请求 `SourceRef`/所需角色并消费 verified content 或来源证据；不打开 `canonical_path`、不读取 CWP `ROLE_DEPENDENCIES` 或直接查询 CWP store。预测模型、情景、consumer cache 和其自有文件仍归 RF。
- **filing-fetch**：先调用 query/reuse；只有显式缺失请求才经 CWP action authorization 调来源 provider。provider 返回候选/原始响应给 CWP admission，不让 filing-fetch 自行选择某个 root 并复制/打开已有 raw。输出保持上层 source/version/状态，历史路径字段仅作限期诊断兼容。
- **invest-quick-scan**：仅消费可选版本化 identity mapping；不得为了映射扫描 company-wiki 公司目录或读取叙述原文。dayu/earnings-transcripts 等供应工具只交候选或获准原始响应，原件存储由 CWP writer 负责。

为防回归，C.local.VR 在每个消费者 repo 的**生产入口调用链**做一次静态边界检查（禁止新增上游 raw 路径拼接、`canonical_path`/`original_path` 业务读取、直接导入 CWP store/resolver/DAG），再以真实 CLI E2E 证明无路径参数：同一 `SourceRef` 在首选副本撤走/目录改名/新增第五根后仍可消费。检查只管**上游来源文件**，不误禁 StockWiki/RF 自己的数据库、模型工件和测试临时目录。静态检查不是逐文件审查门；与 C.local 的真实结果包一起签一次。

### 实施者的文件落点与改动次序（候选，不是扩大写权限）

实施前以 RF 已并主线 SHA 和 CWP 隔离工作树 SHA 重新定位符号/调用者，按下表记录最终 file allowlist 和 owner；若现状已修则只保留回归，不重做。一个仓的 owner 只改其自身文件，跨仓合同通过版本化 fixture/CLI 对齐，不直接写对方数据库或配置。filing-fetch、RF、StockWiki 的消费改动各在自身仓隔离分支进行，按 C.local 大节点联合验收后分别合并。

| 顺序 | 首先核查的现有文件 | 目标 diff 与必测结果 |
|---|---|---|
| CWP B | `src/company_wiki/source_catalog/{scanner,resolver,normalizer,policy,config}.py`、`source_contract/{source_manifest,source_export}.py`、`artifact_handle.py`；实际符号以当前代码图为准 | 去 root-kind 元数据真伪分支、单一路径选择、未验交付；新增版本化只读协议/字段 provenance/明确失败。保留原有同 SHA fallback、旧 source 引用和 canonical writer 单写入 owner。B 包只验通用读取。 |
| filing-fetch C.local | `scripts/{fetch_filing,filing_contracts}.py` 与 `tests/e2e_support/isolated_wiki.py`、`tests/test_e2e_download.py` | exact 本地复用使用 CWP DB-only query；FF 不开原文。`latest_as_of` 必须继续走 CWP provider ensure 才能保持截至日期的最新性；显式下载继续走 `ensure/close-gap`，须有具体验证授权。当前 FF 虽将两类 legacy 结果转换为 pathless handle，但 subprocess 响应先带 `canonical_path/source_bundle` 进入 FF，**进程边界仍泄漏存储细节**。下一切片须由 CWP 在 CLI 边界直接投影版本化 pathless ensure/close-gap 结果，然后 FF 只消费 `SourceRef + metadata + operation receipt`；旧 CLI 保留 v1 兼容。 |
| RF C.local | `scripts/{company_wiki_source,source_preparation}.py`、`e2e/run_cross_repo_chain_e2e.py` | 退出 CWP path 与内部 DAG import，只请求 SourceRef/所需能力；一份合法已审原文正向产出 RevenueSourceRecord，`not_reviewed` 拒绝另测。runner 的 `CODE_PINS` 在改动后正式重绑定，离线显式 `--live never`；持久 claim/Worker 留 C05/G3。 |
| StockWiki C.local | `stockwiki/{company_wiki_contract_v1_records,company_wiki_contract_v1,company_wiki_v1_adapter,company_wiki_v1_sync,source_provider_sync}.py`、`stockwiki/services/source_provider.py`、`config/source_provider.yaml` | v1 文件与历史 ID 保持兼容；**另增**路径无关 SourceExport v2 contract/reader/CLI，不复用现有带 `--source-root` 的 v1 sync 宣称成功。新候选 ID、title、内容/状态从来源字段与 locator 得出；同字节移位前后不变；历史 `cw1_*` 回放及迁移表通过。全量生产 sync 仍待范围/失效合同。 |
| invest-quick-scan / provider | quick-scan 的实际 identity adapter、dayu 与 earnings-transcripts 的候选/响应入口由各自 owner 在 A.DR 重新定位 | quick-scan 只用可选身份映射、不扫 raw；provider 不决定存储 root 或研究语义，获准正文交 CWP canonical admission。未找到实际入口时记 hold，不发明跨仓路径 API。 |

## 3. 冻结真实语料：候选是 catalog 记录，不是已通过测试

### 2026-09-27 隔离实现快照与 TDD 冻结接口（尚未合并/签 B.AR）

- CWP 隔离分支 codex/data-lake-reader 已提供 SourceRef schema 2.0（document_id、source_id、content_sha256、byte_size、mime_type；不含 root/path）、query_local、按精确版本的 open_version。query 只读 catalog、不得扫描/下载；open 每次重查当前根策略、source 状态、待修正提案、原文 SHA 与正式复用的 HTTPS/capture/报告期资格，同 SHA 副本失败可回退，不同 SHA 不替换。查询采用 1000 条分页、至多 20,000 候选；超预算明确 unavailable，不能返回伪 not_found。当前 document_id 仍是版本相关 ID，逻辑文档修订映射未完成。
- 跨进程临时协议：company-wiki-source-query 从 stdin 接 SourceRequest JSON，stdout 返回路径无关结果；company-wiki-source-read 接 config+精确三元组，成功 stdout 原始二进制且 stderr 单行 receipt（含 policy_sha256），失败 stdout 为空且 stderr 单行错误。新 SourceExportBundleV2 schema 2.0.0 从 catalog 引用与 EvidenceSpan 构建，显式 title、期间、URL、collector 等字段，严格 JSON 加载查 hash/count/排序/孤儿/路径字段/重复 key；company-wiki-source-export-v2 只收精确引用和 span，输出路径无关 bundle。旧 SourceExport v1 保留兼容，不能把它的 original_path 当 v2 来源身份。
- 2026-09-27 收据版本边界：二进制最终读取回执升级为 **2.1**，新增原文字节验 SHA 后观察到的 `prompt_injection_review` 快照；`SourceRef` 和 query candidate 仍为 **2.0**，不随读取回执字段变化。FF transport 与 RF final record builder 均严格要求 2.1，并有旧 2.0 成功回执拒绝测试。RF 仅接受与当前 source SHA 绑定的 `not_detected`；该快照表示本次读取时点，不是长期数据库锁。
- 测试采取逐项 red→green；目前真实星环年报与 P06 隔离读链 2 passed，v1/v2 相邻合同一次合并回归 229 passed、1 skipped，新增 v2 发布 CLI 3 passed；该覆盖尚缺真实四根原生拓扑、修订关系、第五根格式、P04 资源峰值、独立 B.AR。SQLite WAL 的只读连接会刷新 -shm 修改时间，E2E 须核主库/WAL 原字节及 -shm 字节/大小，并在独立临时树结束时恢复；不得把 mtime 变化写成数据写入。
- filing-fetch 独立分支 codex/ff-source-reader-v2-20260927 已把 verified binary read 设为显式 --verify-source-version 过渡开关：目标回归 278 passed、3 skipped，隔离 CLI E2E 1 passed；仍用旧 resolve 提供 metadata/envelope，尚未完全移除 canonical_path。StockWiki 独立分支先完成 v2 loader+transport 单测 24 passed，原主树的 cw1/provider 文件仍未跟踪，尚不能安全接到 full sync。RF 新 sparse worktree 已就位，消费者 TDD 尚在进行。C.local 不得用这些局部绿灯直接签收。
- 上述回执版本变化后再次运行关键门：CWP source reader/CLI 契约 **32 passed**；RF reader transport、record builder、source preparation 与 FF→CWP→RF 真实 E2E **36 passed, 1 skipped**；CWP/RF Ruff、RF 三个适用源码文件 Mypy、两仓 `git diff --check` 均通过。测试临时目录定向到隔离可写区；结果仍只证明隔离 v2 opt-in，不表示默认生产路由或 StockWiki 已切换。

### C.local 下一切片：ensure/close-gap pathless operation contract（opt-in 首轮已实现，C.local 未签收）

**2026-09-27 首轮落地状态：**隔离 CWP/FF 工作树已有 `--source-ref-v2` opt-in。CWP 是 operation 结果的唯一序列化方：`ensure`/`close-gap` 输出独立 `operation_schema_version=1.0`、SourceRef 2.0、pathless 候选、outcome/download count、为 close-gap 授权绑定所需的 `policy_hash` 与 pathless gap；旧 CLI 未带 flag 时输出保持原格式。FF exact 无下载继续走 DB-only query；`latest_as_of` 与显式下载走 CWP pathless ensure，授权 gap 才调用 pathless close-gap。FF 校验 schema、operation、状态、policy/gap/request/hash、候选和 SourceRef 一致性，拒绝物理路径或版本漂移。默认入口未切换，改动仍未提交/合并。

**首轮大节点测试记录：**CWP reader/operation/CLI/close-gap 相关合同与真实字节测试 **52 passed**，Ruff 与 `git diff --check` 通过；FF `tests/` **385 passed、14 skipped、78 subtests**，独立 FF→CWP 本地 CLI E2E **1 passed**，FF Ruff、Mypy 与 `git diff --check` 通过，`fetch_filing.py` 复杂度最高 31（冻结上限 34）。全量测试有 1 条 `test_spy_log` 子进程 UTF-8 解码 warning。FF 对 latest/gap/授权 close-gap 的新增 operation 消费合同使用 pathless fixtures/mock；CWP 真 CLI E2E 目前覆盖本地 exact ensure。它们还没有证明真实 provider refresh、真实 CLI close-gap 下载和重复请求幂等性。

**测试区恢复例外：**测试创建的若干唯一 pytest basetemp 目录 ACL 仅允许 SYSTEM/Administrators，普通递归清理和 `icacls /reset` 均返回 Access denied；这些目录不含生产原文，测试运行已结束，但不能记为测试树已恢复。`mypy` cache 与一个空父目录已清理。完整 C.local 大节点签收前需在可访问的专用测试根重跑所需 E2E 并清理，或先由本机管理员恢复这些测试目录的继承 ACL 后删除。不得为此改项目权限或删其他路径。

1. **合同测试（首轮 RED→GREEN 已完成）**：CWP projector 测成功、gap、close-gap 的 pathless 字段；实际 CLI exact ensure 测新输出无路径且 legacy 输出兼容；FF 测 schema/ref/hash/路径篡改拒绝、latest/gap/显式下载/授权 close-gap 路由。继续补真实 latest/close-gap E2E 与幂等性，不把 mock 结果算作下载验收。
2. **CWP 唯一序列化 owner（首轮已实现）**：在 CLI 内从 ensure/close-gap 结果解析精确 source identity，再用 catalog reader `query_ref + describe_candidate` 读取 metadata；FF 不再清洗 legacy `canonical_path/source_bundle` JSON。保留 operation 1.0、SourceRef 2.0、最终 read receipt 2.1 的独立版本语义。latest provider freshness 与 exact DB-only query 属不同副作用路径，不能互换。
3. **FF 消费与授权路线（首轮已实现，仍只 opt-in）**：exact/local query 继续 DB-only、零 provider；`latest_as_of` 调用 pathless provider ensure，保持截至日期语义且未授权不下载；有效 authorization 才能按限额/expiry/accessions 走 pathless ensure/close-gap。FF 不接收或打开 CWP 路径；CWP close-gap 仍负责最终授权、hash 和落盘裁定。
4. **同一个 C.local 大结果包的隔离真实 E2E（未完成）**：覆盖 latest 已有版本、真实 provider fixture 返回结构化 gap、截止日后版本排除、无授权下载 0、一次授权下载后 CWP canonical root 恰一份且 FF stdout/stderr 无 root/path、同请求重试下载 0、最终 RF/CWP open 对同尺寸篡改拒绝。provider 使用隔离测试目录内 fixture/local stub，不调用付费 API。记录 catalog/原文/sidecar/journal 指纹，测试树必须恢复；本轮 ACL 锁定使 restoration 未验收，不能签这一步。
5. **大节点验收（未签收）**：完成真实 CWP ensure/close-gap operation CLI、FF/RF 消费合同、三仓一次性 E2E 结果包、OS 级来源 I/O 计数、测试目录恢复与独立审查后，才能讨论默认路由。失败只回滚 opt-in route，不改 v1 调用者、不写生产 catalog、不改 RF 主工作树。

以下 SHA/字节数原始候选来自生产 catalog 的只读记录和逐路径 stat。星环与 P06 的一处原件和原生侧车已在隔离测试中现场重算完整 SHA 并比对前后状态；其余位置/样本尚未完成相同核验，更未由独立人确认全部公司、期间、kind、locator。A05 继续在专用运行根补齐，不把现有叙述 manifest 的 SHA 前缀当字节证明。固定清单只存 metadata/预期，不把大型原文提交 Git。

| 样本与用途 | catalog SHA-256 / 大小 | 当前原生位置与已知局限 |
|---|---|---|
| P06 三角防务定增募集说明书，位置等价主样本 | `cd803fe9528f4646f8f29b518a450ae4bd5b5968c482eb49789f9786b523595b` / 5,595,592 B | company_raw `三角防务/raw/research/…注册稿.PDF` 与 Dropbox `军工/三角防务/…注册稿.PDF` active；四份隔离复制约 22.4 MB，不算四来源。 |
| 星环科技 2025 年报，缺 company 根反例 | `0d40d94aef8d2fa08c4c75760198be426a0b579be3d7200ec9450a7e04522b4f` / 1,794,755 B | dayu_portfolio `688031/filings/fil_cn_cd044bc0b6d88ca025885f43ed445e0b4c209822/…pdf` 与 Dropbox 原生 active；filing-fetch 本地复用候选。 |
| Microsoft FY2025 10-K，跨格式/跨根 | `99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe` / 8,158,067 B | company_raw `微软/raw/financial_reports/annual/微软_10-K_2025.htm` 与 dayu_portfolio `MSFT/filings/fil_0000950170-25-100235/msft-20250630.htm` active；RF reader 候选。 |
| 拓尔思 IPO 招股书，命名/分类反例 | `b99640fa6475292b63e9fa6d6c0ee22b08d61ff1816d2550782bbe9424d30164` / 4,981,074 B | company_raw `raw/prospectus/…招股说明书.pdf` 与 `raw/research/300229_IPO.PDF`、Dropbox `…/300229_IPO.PDF` 均 active；catalog 当前 kind=`other`，独立 oracle 应核为招股书；不能先删重复位置。 |
| P09 低价值制度文件，选择性加工负例 | `76e146985388c926f2683e24af47e6a1ab0ce8a156864fb16e7df9a2cc99b678` / 167,252 B | company_raw active；预期不产业务叙述切片，仍保留来源记录与必要预览。 |
| 三角防务 2023 年报原版/更正版，真实修订**候选** | `96b3befe9643b591db8a76ffc0e9ebff738e0ed2d2cd9b28ae7d9e40b3e68626` / 4,735,232 B；`cc338ad22b8abac357d4a77e880af1078829901ad23830ac2ebc9d8d9be7c6b2` / 4,786,302 B | 两份 company_raw retired，sidecar 缺权威 URL/日期；核官方更正关系前 L07 正向修订仍 blocked。 |

再从既有 P01 年报、P04 429 页招股书、P07/P08 投资者关系、T01/T02 英文 TXT 及半年报/季报选样，补原生位置、完整 SHA、来源身份和人工 locator。TXT 尚未获正式 catalog 接纳时只用于隔离 G1；不能冒充 B 原生根覆盖。根覆盖与四副本等价为不同测试。`future_lake` 当前 545 B 文件若不足以证明原生适配，则明确 `pending/limited_scope`。D0 的 52 组本地同 SHA 双路径与约 98.8 MB 冗余仅是 stat 候选上限，不能当删除许可或真实节省。

## 4. 大节点真实字节 E2E：复用 R4 L/P 与叙述 G，不逐卡审

所有运行复用[独立测试目录与恢复协议](../narrative-evidence-pilot-2026-09-26/end_to_end_test_plan.md) §2：从只读 allowlist 复制少量样本到唯一 run-id，**复制后核完整 SHA**，临时 catalog/config/root/输出/缓存/锁均在运行根；不复制生产全库/活动 WAL 库，不完整恢复备份。冻结三仓/StockWiki HEAD+dirty、输入 hash、oracle、CLI argv、资源预算和预期状态。禁生产写/网络/Worker 控制；结束核原始文件 path/大小/mtime/SHA，测试树起止条目/字节/hash/属性一致，删且仅删本次 run-id 与其控制记录，检查进程/WAL/锁无遗留。测试生成的真实下载文件同样按 run-id 清除，回到运行前基线。

| 共用结果包 | 必须从真实入口走到结果 | 关键断言；缺口如何记 |
|---|---|---|
| **A.DR/G0**（设计与语料，不冒充 E2E） | 独立原文/sidecar oracle，冻结 query/open/export 协议、权限与样本清单；基线只读 trace | 完整 SHA、公司/期间/kind/公开时点/locator、修订证据、版本与资源阈值；不明字段写 unknown，样本不足对应 case hold。 |
| **B.VR/B.AR**（L01–L12 一次大包） | P06 真字节四隔离根：逐一索引→查询→verified open→locator，随后调 priority/扫描顺序、撤/搬首选、同 size 篡改、读中替换、全失效/ACL/需水合；另用星环、微软、拓尔思保留原生拓扑和 sidecar 做各根只读链；第五根只改注册 | 同 source/version/期间/kind/权限/locator 与 SHA；不同 SHA 不顶替；冲突留 provenance；零网络/隐式水合/生产写/Worker。P04 测有界 RSS/临时峰值/取消。真实云离线与真正修订无条件时单列 pending，不用注入替代。B.AR 仅签通用 reader，不要求真实 consumer。 |
| **C.local.AR 基础来源 reader**（P01–P03 与 L11/L12） | filing-fetch 现有 `fetch_filing.py` 本地 identify/resolve 入口读星环，再次查询 0 下载；RF `source_preparation.py` 真实入口读微软，使用其三仓 E2E runner 显式 `--live never`；StockWiki **待新增路径无关 SourceExport v2 strict reader/CLI**，无 `--source-root` 或 raw path 入参，以 SourceRef 调 CWP verified open 读 P06 基础 source/locator export，在隔离 StockWiki root 执行该**新入口的 dry-run** 验原文字节。现有 `source-provider-sync --bundle … --source-root … --dry-run` 只作为旧 SourceExport v1 兼容回归，不能证明新 reader。 | 每方 source/version/hash/locator/质量/撤回/as-of 与真实字节一致；旧引用可回放；同 SHA 换位置不改新 export/evidence/candidate ID、标题/kind/period、候选内容/状态或业务结果；0 网络/下载/LLM/Worker/生产写。filing-fetch 保持现有退出码/JSON 兼容；RF 现有 runner S2 的 `not_reviewed` 拒绝只算安全负例；**RF 放行必须另有一份合法已审真实来源由 `source_preparation` 正向产出 RevenueSourceRecord/verified bytes**，无正例则 RF 栏 hold。代码 pin 变更要正式重绑；StockWiki full sync 仍 blocked。**此包不等于叙述 G2a。** |
| **叙述 G2a**（W5 后） | 正式 selected evidence package → 上述已验 reader/StockWiki 与 RF 的叙述消费入口 → locator 回读和查询；同一测试 run 协议，若与 C.local 同期完成可合并执行 | 只加测包 schema、coverage/partial/needs_review、撤回/as-of、证据引用和检索；复用 C.local/B 不变的收据。W5 未完成只记 G2a pending，不倒扣 C.local 已验的基础读取。 |
| **G1 叙述小试** | 复用现有 12 件探索材料和 P09/P10 负例，真实 raw→选择→来源摘要→locator 回读；T01/T02 接纳后分别回放英文 TXT | 财务表不变成运营结论，招股/再融资/IR 高价值段落召回、角色/否定/时点/问题前提正确；量测未选内容的独立留出集，不以已选锚点通过证明总体召回。G1 不能代替 B 或 G2。 |

若某消费者暂时只有 strict v1，先测稳定兼容视图并把 v2 栏记 hold；不能宣称已实现跨仓路径透明。RF 生产跨进程 Worker E2E 还要等持久 request/claim 合同与 G3，不能用进程内队列冒充恢复成功。真实下载只属于后续 C provider/G1e 授权线路，不混入 C.local 的零网络结论。

## 5. 量测、停机、回退与完成定义

每个大包记录各样本 raw 字节、同 SHA location 数、catalog/artifact/index 增量、临时峰值、整文件读取次数/字节、冷/热延迟分布（预冻次数及 p50/p95 算法）、解析/LLM/provider 次数、网络与生产写观察、run tree 清理前后差。先量旧、新链同机同语料，再裁性能与空间阈值；不能承诺一律加速或据 46 GB 总量推算可删量。一个同字节原文保留可读取副本与权利证据；大幅省空间主要靠少存全量 span/衍生全文及获批后处置精确重复项，且分别验可回源和下游引用。

**B 停机**：元数据或权限随 root priority 改变、返回未验字节、旧引用失效、临时峰值越界、隔离清理失败。只回退 reader/schema 路由或 adapter，不改写原 raw/source 历史。**C.local 停机**：任一真实 consumer 仍要求用户给 root/path、导入 CWP DAG、隐式联网/写库/控制 Worker，或 StockWiki 新 `export_id` 随原始路径变化；只撤该 consumer 的新路由，B 可独立保留。已通过局部结果不得扩大到未测的根、真实云、全量同步、生产 Worker 或删除。

完成本优先线路需：A 合同与独立 oracle 可复核；B 通用 reader 的真实字节 AR 明确覆盖范围；**filing-fetch、RF、StockWiki 三个 C.local 基础来源实际新版 reader 均通过**（quick-scan 的可选身份映射另按其合同测）；四类业务字段不依 root，旧 source/locator 可回放；专用测试目录彻底恢复基线。某消费者 hold 时可发布已验 B 或其他消费者的**有限范围**成果，但整体跨仓抽象目标仍 `incomplete`，不得写完成或解除其旧路径。**叙述 G2a 是 W5 后的独立业务能力验收，不阻基础 C.local，也不能借 C.local 自动放行。**空间处置按 G4 另行批准。所有结论附原始测试结果与审查者，不从本计划推导 PASS。
