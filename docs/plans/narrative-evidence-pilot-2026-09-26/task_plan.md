# 叙述性证据选择与摘要：小范围试点及实施方案

> 独立实施计划；不替代仓库根目录或任何已有专项计划。Phase 17 的旧库退役已完成；Phase 18 的离线 G1 选择、定位和草稿验证已完成一轮。**2026-09-27 新顺序：RF 主线并线已完成，先实施 R4 数据湖抽象层，再继续本计划的 W5/G2a、Worker 与空间处置。**本计划自身不写 RF，不启动生产 Worker；已有隔离叙述工位与主树未提交文件保持原样，待抽象层合同接入时按当前文件快照整合。

## Goal

用 10 份不同类型的 PDF 与 2 份英文 TXT 验证业务叙述选择、证据定位和摘要边界，形成 company-wiki 与 filing-fetch、StockWiki、revenue-forecast、invest-quick-scan 兼容的可实施方案。

## Phase 34：发布收尾与暂停（2026-10-01）

- [x] 完成各线/PWF 复核并形成[收尾报告](harness_lanes/results/cross_line_closeout_2026-10-01.md)；不重复已完成 E-B/W04，不覆盖 IQS 新的 V02/scoring owner 工作。
- [x] 将 FMP JSON admission、原件 locator 和未知 publication/as-of 语义补为 G-A 明确待办。发布检查暴露 importer/contract 的 12/13 复杂度超限，按既有 RED 拆分入口/预算校验，保留行为；13 项合同/CLI/端到端回归通过，Ruff 通过。
- [x] 用户要求及时推送：ET main 已正常推送至 `4924d57`。CWP/RF 按普通快进与既有自动检查发布，结果记 progress.md；无 remote 的 StockWiki/IQS 不擅自建远端。
- [x] 记录 RF push 的环境问题：rf-impl 稀疏检出漏掉 tracked e2e，Ruff E902；补齐当前 HEAD 工作树后再跑原有检查，不 bypass。
- [x] 修复发布检查的 source-workflow/legacy writer 误分类：六项 RED→writer freeze 20 GREEN，保留退役研究 writer、来源工具自身 SHA/path/事务规则。
- [x] 本轮收尾后暂停实施；Worker 保持 paused，原件保留。RF 普通推送被 historical current_triplet ancestry 的 2 项测试阻断（其余 25 项通过）；不绕过，留待恢复时先 RED 区分 historical snapshot/live HEAD。CWP 本轮提交的发布结果以 origin/master 实读核对为准。

## Next Step

> **2026-10-01 当前审计基线（Phase 33，覆盖下方较早的 live-state 快照）：**CWP `master@00af53f`，比 `origin/master` 超前 62 个提交；E-B 已由 `9e73eb4` 并入，合并后相关回归 **349 passed、2 skipped**，56 个变更 Python 文件 Ruff 通过。StockWiki `master@b4f3846` 的 W01/W02/W03、SourceExport reader、W04 和 MIC 关系补强均已合并；已知源分支全部是 master 祖先，`check_all.sh` **686 passed**。RF 正式 `main@3e03ce83` 干净且比 `origin/main` 超前 4 个提交；`fcap@ee0a82bf` 的已提交历史是 main 祖先，但 fcap 工作树仍有大量未提交/不可见路径，审计报告的 404 是下界，不能清理或整树并线。FF 当前检出的 `fcap@d35b6f5` 与 `origin/main` 同步；本地 `main@c9799b7` 落后 39 个提交，SourceRef v2 与 transcript companion 两个独立 worktree 的改动路径有重叠，仍应由单一 FF owner 汇合。ET `main@4924d57` 比 `origin/main` 超前 6 个提交，工具 `/2` 已实现；FF→ET→CWP 的正式整合门仍待做。IQS `master@e7fe99c` 仅有 owner 正在编辑的 `task_plan.md`；provisional G2b 正反 CLI 已通过，但完整 G2b、QA-04 收尾和部分 W01–W03 交付仍 pending。下方早于 Phase 33 的“当前/下一步”状态段均是历史快照，不作为当前派发依据。各仓当前证据与计划漂移见 Phase 33、`progress.md` 和 `findings.md`。

> **2026-09-28 权限/审查简化（优先于下方所有历史段落）：**不设 private/public、逐文档/逐期/逐 job 授权、review receipt、独立 reviewer 或人工批次审批。用户已授权范围内，自动化测试和 source/hash/lineage/预算断言决定能否继续；原始文档全部保留，只清理可重建且无引用的派生文件。下方 2026-09-27 transcript permission 细节和历史 G 门槛只作事实记录，不是待实施指令。

**2026-09-28 跨仓总编排（覆盖本节以下较早的“唯一下一步”与 Current Phase 快照）：**先按[跨仓主线整合与交付总计划](cross_repo_mainline_and_delivery_plan_2026-09-28.md)固定 **S0/G-0 → S2/S3/S4/S4b/G-A → S5/G-B** 的来源抽象与真实消费者门；IQS C01→StockWiki W01/W02/W03/G2b 独立推进，CWP N0/N1 可并行，随后 N2/N3/G-C、派生 G-D。RF `fcap` 已并入远端 main，不再重复合并；真正待并的是 RF reader、FF 两个重叠 WIP、ET 接口和 StockWiki 的新 reader。**2026-09-30 状态更新：StockWiki reader/identity lanes 已并入本地 master，基础 G-B 真实 E2E 已通过，W04 是当前可派发的 StockWiki G2b producer 线；RF/FF/ET 仍按各自 owner 当前状态处理。**大节点验收前不切默认路由、不启动生产 Worker、不删除唯一原文。下方长篇 Phase 1–23 保留历史与阶段证据，不再自行定义施工顺序。

**2026-09-28 Phase 23 重构总图：**后续实施统一按[清洁架构与 TDD 实施总图](clean_architecture_tdd_execution_plan_2026-09-27.md)的 Phase A–G / M1–M4 执行。内部代码和派生 schema 允许破坏式重构；canonical raw 原件、来源 SHA/manifest 和版本事实不得丢失。Phase B/M1、Phase C/M2-derive、Phase D/M2-provider 与 Phase E/E0–E4 已完成。当前大节点是跨仓 pathless reader 合同验收：复用现有 RF `codex/revenue-source-reader` WIP、filing-fetch `codex/ff-source-reader-v2-20260927` WIP 与 company-wiki `SourceVersionReader`，不重复实现适配器；FF→CWP 定向集成 **22/22 通过**，FF 原有 `test_fetch_filing.py` 与新增 v2 定向组合回归 **138 passed, 1 skipped, 39 subtests passed**（唯一 skip 需要本机 production security-master snapshot）。旧 transport 在 FF 工作树内无残余代码引用；v1 默认路径仍调用 `validate_handle` 的 root-policy/路径校验，v2 是显式分支。FF 的新增 producer 仍有较大 diff，须完成全 diff 审查再考虑合入。原 RF 三仓 E2E 因固定 `as_of_date=2026-09-27` 早于实测 FF candidate capture (`2026-09-28T18:55:58Z`) 而失败；仅在 TEMP 测试副本把 as-of 改为测试日、其余三仓代码不变后，真实 FF→CWP→RF E2E **1 passed in 14.09s**。**历史下一步（已由上方跨仓总编排替代）：完成 FF v2 全 diff 与输出合同审查，确认默认 v1 golden/调用者兼容；再协调更新 RF WIP 中过期 E2E 日期夹具，并以原路径重跑三仓门。**不得为通过测试放宽 capture/published/as-of 校验。当时拟在三仓门绿后接 G2a/StockWiki；现以总编排的 S5 并行和 N3 前置为准；Worker 与空间处置继续按 Phase G 的节点顺序实施。

**2026-09-28 最新状态（覆盖下方历史快照）：**Phase E/E4.1–E4.8 已完成；全套 E4 节点门 **420 passed in 70.65s**，Ruff/C901/strict mypy、config doctor、host guard、diff check 均通过。production Worker 保持 paused，runtime composition 尚未接入生产；短路径测试根已清零。RF 已提交的 `fcap@ee0a82bf` 是缓存 `origin/main@3a69f9c5` 的祖先，本地 `main` 仍落后；**沙箱外**只读 Git 盘点 RF 根工作树为 **415 条状态（11 修改、404 未跟踪、0 删除）**，个别长路径/权限警告另见 findings.md；先前沙箱内报告的 6,123 条及 3,778 删除是访问隔离造成的误报，不得据此恢复或清理文件。另有 `codex/revenue-source-reader` 未提交 WIP（3 个修改、7 个未跟踪）。filing-fetch 已有未提交 SourceRef v2 producer WIP（提交 `90771d8` 之上另有修改）；以 CWP 当前源码路径运行其 v2 定向测试为 **22 passed**。RF 三仓原测试失败原因为 as-of 固定旧日期：候选 capture 实测为 `2026-09-28T18:55:58Z`，而 `as_of_date=2026-09-27`；只修改 TEMP 副本的日期输入后真实 FF→CWP→RF 路径 **1 passed in 14.09s**，原 RF 文件未修改。三仓接口路径已实证，但 FF v2 差异仍需 v1 兼容/旧 transport 删除影响审查，RF 正式工作树测试夹具仍待更新后复验，因此尚不能接入 G2a。company-wiki `master@43c5f4a` 包含已核支线提交、本地工作树干净但比缓存远端领先 33 个提交；StockWiki 有 invest-quick-scan 计划明确引用的活动 `QuickScanStore` 未提交改动，须保留。当前阶段先审清这些既有工作与合同边界，不把仓库局部 clean 误报为跨项目集成完成。

**Phase 22 阻断结论（保留证据）：**暂停 R4 consumer/跨仓接线。正式 `SourceEnsureResult.to_dict()` 输出 `acquisition`，当前 consumer/test 同步漂移到不存在的 `acquisition_result`；现有 390/88 项绿灯不能覆盖这个 producer/consumer 反例。

**2026-09-27 最新优先级（优先于下方历史实施快照）：**先按[数据湖边界复核](data_lake_boundary_review_2026-09-27.md)与[R4 数据湖实施卡](../painpoint-outcome-audit-2026-09-05/r4-data-lake-priority-rollout-2026-09-27.md)实施来源身份、受控读取、跨进程交付和各仓责任；RF 远端 main 已并入 `3a69f9c5`。R4 基础 reader 的真实 B/C.local E2E 通过后，再把本计划 selected evidence package 接到 G2a；已有离线 G1e 代码在自己的隔离工作树保留，合同时整合。生产 Worker 与原文处置仍待各自大节点；试点 `source_id → raw path` 映射不能成为正式 G2 消费者合同。

**并线前执行快照（已由上方最新优先级覆盖）：**当时 RF `main`/`fcap` 同为 `ee0a82bfd`，后续工作仍在本地未提交，故 G0 与产品接线暂停。保留的事实是 RF Phase 7 计数不等于 CWP 来源接口已完成；I-05-C 的真实 producer/consumer/event 及 I-06-A/B 的 caller/跨进程 claim 尚需按新 reader 合同验证。E-T `discover`/`fetch-candidate` 与隔离 importer/preflight 有历史离线收据；CWP 主树与 transcript 分支的 `canonical_writer.py` provenance 调用点有 diff，整合时逐 hunk 联合回归。Worker、生产 SourceBundle/DAG/consumer 和原文处置不由 RF 并线自动放行；实施前按[跨项目协调](cross_project_coordination_2026-09-26.md)重锁当前状态。

### 历史实施快照（仅供追溯，状态以本节首段为准）

**当前实施收据（2026-09-27；优先于下方较早的 G1e-C 状态段）：**G1e-C importer 核心现在有可运行的 `company-wiki-transcript-import --wiki-root ...` stdin JSON CLI，并在隔离 worktree 注册 console entry。CLI 只接收 `/2` transcript result；重新加载 company-wiki 当前 runtime/right policy、重算精确候选授权并与请求、候选、预取 admission/hash 绑定后才创建 catalog/writer。固定从 wiki root `config/provider_use_policy.json` 读取 rights policy，缺失即拒绝；不提供可自选 policy 路径，也不写生产 policy。合成 fake E2E 覆盖合法原件→canonical raw/sidecar、stdout 不含正文/重复 base64、staging 清空，以及权利撤销后在 raw/staging/catalog 写入前拒绝。聚焦 CLI+import/material+rights suite **33 passed**；Ruff 与 diff check 通过，pytest 独立 run root 已验证/清理。此 slice 完成不等于跨仓接线：CLI 只能复核当前授权和结果，尚不能证明父进程在 discovery 和 exact body fetch 前按顺序做了 rights gate；preflight JSON 不是可信时序证明。filing-fetch 的 discover→候选选择→精确授权→`fetch-candidate`→stdin import 全链 E2E、schema/partial-success 和 G1e-D 仍待 revenue-forecast 同步窗口。`transcript_tool.py` / `transcript_api.py` 按既有契约始终返回未翻译英文原文，不加无作用的翻译 flag；legacy `scraper.py` 已有 `--no-translate`，并新增 `--disable-translation` 清晰别名。E-T 离线回归 **108 passed, 2 deselected**（需本机 LLM key 的偏好测试及可能调用 Google 的合成短句测试明确排除）。Koyfin/Seeking Alpha 不接入；没有证实增量价值时不增加 provider。

**2026-09-27 当前下一步：**[G1e provider 逐动作权限合同](transcript_provider_rights_contract_v1.md)及[跨仓集成合同草案](filing_fetch_transcript_integration_v1.md)已成文；company-wiki 隔离分支具备请求前闸门、下载后 policy/response 二次校验、紧凑 lineage schema v2 和 fake-provider→canonical writer→英文 TXT/locator replay E2E（34 passed）。**G1e-B 已在 earnings-transcripts 实现并通过全量离线回归**：默认结果 schema `/1` 保持原样；`--include-source-payload` opt-in 返回 schema `/2` 的受限 base64 provider 原件、MIME、安全 effective URL，成功结果不重复携带正文；全量 **100 passed, 1 deselected**（一个既有 LLM-key 测试因本机无凭证跳过），Ruff 与 `git diff --check` 通过。设计复核发现并修复了 fetch 前候选授权时序：E-T 新增 `--operation discover`（只返回候选）和 `--operation fetch-candidate`（只取调用者授权绑定的精确 URL），旧单步接口禁止用于集成；全量离线回归 **106 passed, 1 deselected**。下一步是 **G1e-C：company-wiki stdin importer**，实际证明 caller 在 discovery 前校验 `discover` 权限、在 candidate-fetch 子进程前校验 exact DownloadAuthorization/retain/derive 权限，再验证 `/2` JSON、base64/原件 SHA、MIME/URL/期次和 rights pin，调用 canonical writer 与 compact lineage。随后才是 filing-fetch schema 1.3/独立授权/partial-success 接线及跨仓 E2E；这一段仍须等待 revenue-forecast 同步窗口，当前不修改 filing-fetch、RF 或共享 role DAG。filing-fetch 文档 schema 1.1 与代码 1.2 的漂移将在其获准实施时一并修复。Motley Fool 权利 hard deny、FMP 单次 canary 402/保留权未确认，所有阶段仅 fake provider，不访问真实正文端点。工具/平台比较见[对照卡](earnings_transcripts_vs_platforms_2026-09-27.md)，结论仍是先不买；Revenue-forecast I-17-A 自然观察在飞，Worker 继续 paused。

**2026-09-27 G1e-C 增量状态（以本段为准）：**隔离 worktree 已完成 company-wiki importer 核心库函数，不是 stdin CLI 或端到端 caller。它要求预取 admission 绑定 request/candidate/auth hash；限制并校验 `/2` JSON、重复键、ticker/venue、FY/Q/as-of、候选 URL/ID、原始 base64/SHA/MIME/时间；复查下载后 rights policy；规范化写入前失败不产生 raw/staging；成功写入单份原件、rights/auth hashes 与校验动作进 namespaced provenance extension，并只在内存产出未翻译文本及 locator。核心+canonical writer/acquisition/sidecar 合同测试 **56 passed**，Ruff 与 diff check 通过。**G1e-C 仍未完成**：stdin 包装、discovery 权限前闸门及调用者在 E-T 子进程前的真实排序尚未接；G1e-D/E 继续等 revenue-forecast 同步窗口。E-T 输出的 exchange 是调用参数的回显，故正式调用必须先有精确交易所映射；`auto`/未知 venue 在 importer 端拒绝。没有新增 provider，Motley Fool/FMP 仍不放行。

Phase 17 的 F0–F5 已完成。G1 离线主样本和回归集已经复跑：12 件样本 1,289/1,289 locator 回读成功、18/18 锚点命中、13 条人工草稿通过引用/角色校验并完成实施者逐条核源；所有草稿仍是 `needs_review`，两份 IR 仍有不稳定表格定位。JSON 输入字节已实测，**不是数据库增量**。两个试点 CLI 有隔离 `--run-root`；P06 定增说明书与 T02 英文电话会完成中英检索；新增 pilot-only resolver 在 12 件样本上从隔离 raw 重新解析/选择，逐组核对 source SHA、evidence ID、locator 和文本 hash。bundle v0.2.0 的最新合并回归为 12 个检索/回源单测 + P06/T02 双样本 E2E + 12 件样本 selected-anchor/raw-replay E2E，共 **14 passed in 130.77s**；历史全绿收据为 122.56s；`ruff check` 通过。pytest 实际 basetemp 已删除并复核不存在，`tests/e2e/.runtime/` 运行前后均不存在，run tree 已恢复基线。此结果不连接生产 catalog/query API 或消费者，也不等于 G1/G2 共享集成放行；不证明未选内容召回率或生产性能。Revenue-forecast 当前已推进到 progress Round 120、register §162、owner decisions §39：I-16-B 部署执行已 `accepted_scoped` 落定；register 将 I-17-A 列为在飞，但其基础执行卡仍标 `planned`；I-17-B 后继待做。I-05-C 的真实 producer/consumer 入口/InvocationTracker 事件 schema 开放项及 I-06-A 的 RF caller/CLI、跨进程 claim、I-06-B consumption 面等 carried-open 仍阻止 G0。不得改共享接口、store、producer、service、DAG 或 Worker；具体证据与时间点见[跨项目协调](cross_project_coordination_2026-09-26.md)。

## Current Phase

Phase 33：完成六仓现场与 PWF 只读对照，并将 CWP 当前计划状态校准到 live refs。实施顺序无需重排：先关闭 G-0 剩余真实 reader/locator 缺口及 G-A 正式 source/transcript 汇合，再做 G-C selected narrative 消费，之后按批次做 G-D 派生清理。CWP E-B 与 StockWiki W04 已完成；RF 已提交 fcap 历史已在正式 main 祖先链，但其 fcap 脏工作树未归属，不做合并或清理。FF 同名 main 落后远端 39 个提交，两个功能 WIP 有文件重叠，保持单一 owner 汇合。RF、FF、ET、IQS 的跨仓消费者/端到端门仍未全部通过。`NarrativeBundle /2.0` 目前是独立持久叙述工件，尚未成为通用 SourceExport 或 RF/StockWiki 消费入口；下一轮先冻结其 pathless 引用与真实读回 golden，不改 SourceExport v2 wire 或通用 role DAG。production Worker 继续 paused/default-off；真实 P2 仅约 6.3% 提速且峰值 RSS 高约 23.5%，锁等待 p95 未测。原始文档保留。

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

## Phase 23：清洁架构与 TDD 重构总图（2026-09-27）

- [x] 明确 canonical raw、来源 SHA/manifest 和版本事实为不可丢失层；normalized、spans、摘要、索引、缓存和 staging 为可重建层。
- [x] 将 catalog、read broker、acquisition、deterministic derivation、evidence、export/consumer、durable jobs 分成单向依赖的 L0–L7。
- [x] 为 operation/read、叙述证据/provider、Worker、跨仓消费与派生清理写出 Phase A–G 的输入、允许修改、停止条件和完成门。
- [x] 建立 U/C/I/E/X/P 分层测试体系和 M1–M4 四次集中验收；正式 producer 生成正例，手写 JSON 只做畸形负例。
- [x] 本轮曾用红测确认正式 `acquisition` producer 与 consumer 的断裂，并验证重构思路；按用户“先计划后实施”要求，所有未提交产品/测试试验已恢复到 HEAD。
- [x] 按总图 Phase B 完成 producer/CLI 红测、typed operation contract、projection 与薄 facade；read-only ensure 复用正式 producer serializer。
- [x] 完成 M1 大节点：正式 producer/consumer 合同、latest-as-of/provider-unavailable CLI E2E、跨 root 同 SHA 回退、错误 SHA 拒绝、复杂度与严格类型门，共 115 项测试通过。
- [x] 按总图 Phase C 完成 12 件样本、DocumentStructure/selector/coverage/locator/空间行为与叙述证据分层。
- [x] 完成 Phase D provider/transcript adapter、失败矩阵与 fake subprocess E2E；保留真实 E-T HTML material 语义阻断到 Phase F。
- [x] 完成 Phase E/E0 fail-closed baseline 与 E1 Automation DB v2、原子 Store、Worker/Outbox fencing。
- [x] 完成 E2 原子 DAG materialization、依赖结果门、双向 legacy/AUTO interlock 与 destructive prune dry-run 收口；E-A 集中审查最终 **229 passed**。
- [x] 按冻结施工卡完成 E3：Windows `spawn` 的 P1/P2/P4 有界进程拓扑、compute/model 硬隔离、per-attempt heartbeat、数据库租约恢复、父进程强杀自退出、bounded shutdown 与跨重启有界日志均已先红后绿；真实 P2 证明两份不同 source 同时执行，同 source downstream 不越过依赖。
- [x] E4.1 strict narrative contracts、E4.2 single-snapshot `JobExecutionContext`、E4.3 三阶段 DAG、E4.4 verified bytes reader/PDF facade、E4.5 select handler 已逐片先红后绿；select 对年报/招股书/IR/transcript 做证据最小化，完整低价值文档才可 skip，parser/policy/source drift 均零 effect 失败。
- [x] E4.6 summarize handler 完成：同语种、不翻译、selected-only prompt、模型错误分类和原始响应不持久化均有 RED→GREEN 合同；2026-09-28 简化后无 prompt-review 回执和 transcript action-policy gate。
- [x] E4.7 verify/effect 完成：全 locator/original-byte replay、canonical bundle 和单一逻辑 PENDING effect 均有 RED→GREEN 合同；去掉生成后人工 review/provider policy 复核；未 apply、未写 catalog。
- [x] E4.8 隔离三阶段集成完成；按冻结施工卡完成隔离端到端验证及一次 E4 合并门（420 passed），runtime 尚未在 production 注册。

**Status:** Phase E/E4.1–E4.8 complete；production Worker 仍 paused。下一步按总优先级审查 RF 支线并线与跨仓抽象边界。

## Phase 24：跨仓主线整合与剩余施工总编排（2026-09-28）

- [x] 对 CWP、RF、FF、ET、StockWiki、IQS 的当前 refs、未提交工作、PWF 收据和关键现行测试做只读交叉盘点；纠正 RF 沙箱误报（真实 11 M/404 ??/0 D）。
- [x] 写出[跨仓总施工图](cross_repo_mainline_and_delivery_plan_2026-09-28.md)：冻结层级责任、合并分支与冲突次序、G-0/G-A/G-B/G-C/G-D 大节点真数据 E2E、TDD/回退/测试根恢复、Worker E5–E7、旧链退出和派生空间账。
- [ ] S0/G-0：live refs、真实样本 oracle、CWP 多根 verified reader 的一次自动 E2E；旧 A.AR 只作历史事实，不借 M1 内部门跳步。已复核 CWP SourceExport v2 producer/CLI 在主线，当前要验现有合同并补真实输出证据，不重建 producer。
- [ ] S1–S4b/G-A：整理 ET WIP；FF SourceRef v2 最终净差异 → RF reader 正式夹具与三仓真测 → FF companion 真实 ET/CWP 编排，按各仓正常合主线。
- [x] S5/G-B 基础来源消费：StockWiki SourceExport v2 reader/CLI 已在本地 master；真实 CWP producer→verified-open→StockWiki reader E2E 通过。S5b full sync/weekly 留 G-D 发布门。IQS 契约包 2.2.0（Entity 2.1.0 + AnalysisSubject 1.0.0）、StockWiki W01 与 W02/W03 新合同已并入；G2b 仍需真实 owner receipt/market-registry 数据及自动测试。
- [ ] N0–N3/G-C：退出旧重复工件/全量写/研究 writer；E5 outbox dispatcher、attempt bundle 恢复、prepared→visible 可恢复投影与 pathless reader 已提交；E6 真实样本 P1/P2 已通过。下一步完成 E7 崩溃/恢复/吞吐矩阵和 E-B 集中验收，再做正式 selected G2a 消费。生产 Worker 在 G-C 自动测试通过前 paused。
- [ ] G-D：只对可重建派生做 scratch 与精确生产批次清理，量同卷净收益，原件/manifest 保持不变；受控发布与分仓脏树对账。
- [x] 权限简化：移除逐文档/逐期人工授权、prompt-review receipt 门、transcript rights-policy 与双阶段复核。删除 importer 调用链外且只互相调用的 rights/admission/preflight 旧模块及专属测试；transcript importer CLI 收敛到 `/2` 单次请求。narrative event/select/summary/bundle 合同升至 `/2.0` 并去掉 provider-policy 字段。保留身份、原文 hash、lineage、payload 上限和结构校验。自动化 `PolicyConfig` 默认允许 LLM；外部下载仍由具体采集任务触发并受 API 速率/费用/字节约束。
- [ ] 后续合同迁移：`privacy_class` 当前不控制外发，但仍进入 RootPolicy 3.0 导出 hash；在统一更新 CWP/RF/StockWiki consumer 后移除此 legacy 字段，不能在中途静默改变 3.0 hash。
- [x] 简化 transcript provider/import：旧 v1 rights receipt 规则只作历史；importer 直接消费一次精确工具结果，保留确定性身份/期次/状态码/MIME/长度/SHA 校验，不再逐期人工签收或创建 preflight receipt。
- [x] 减少人工门禁：审查规程改为自动测试放行；G0–G3 为集中真实 E2E，不再要求独立 reviewer、人工签收、逐文件授权或批次审批。未通过时仅暂停受影响能力。

**Status（2026-09-28 最新）:** S0/G-0 reader 基线曾通过 **125 项**；它不覆盖尚待完成的四根/原生目录位置、SourceExport locator 真消费及旧引用回放，G-0 仍未通过。权限简化代码已扩展到 narrative handlers 与 transcript importer/CLI，并删除不再使用的 transcript rights/admission/preflight 服务链：第一组回归 **127 passed**，第二组 **95 passed**（两组重叠 24 个 planner 用例，共 198 个不同用例）。narrative event/select/summary/bundle 合同为 `/2.0`，importer CLI 为 `/2`；改动 Python 文件 Ruff clean、`git diff --check` clean，隔离测试根已删除。当前不要求逐文档人工批准、人工 review receipt、private/public 外发分流或独立签收；保留身份/SHA/长度/locator/结构校验及运行预算。通用 `DownloadAuthorization` 仍由 `close_gap` 使用，本轮未改，恢复整体工作时单独评估。Worker 仍 paused，需 G-C 真实数据 E2E 通过后才进入其原计划发布阶段。RF 根 PWF §42 与用户确定的严格 fixture-hash 规则冲突，CWP 不导入其 dirty 放宽实现。跨仓并线、RF/StockWiki/IQS 脏树清理和生产派生清理尚未执行。

## Phase 25：统一清理多余门禁与按仓库独占的并行施工计划（2026-09-29）

- [x] 第一部分：逐仓调查运行时代码、测试与现行计划；把人工权限/签收、自动数据正确性校验、运行预算和历史文字分开，形成[统一清理方案](gate_and_contract_simplification_2026-09-29.md)及受影响测试清单。方案已完成，产品代码清理尚未执行。
- [x] 完成第一部分的清理实施方案后，建立[总指挥计划](parallel_harness_orchestration_2026-09-29.md)与六仓独立施工卡；每条线独占一个项目目录，按 S0a observed→S0b producer golden 冻结输入/输出、交接、独立测试包和跨仓大节点。IQS 管合同校验，StockWiki 管真实身份库；RF/StockWiki 的 selected consumer 各有本仓施工任务。
- [x] 只更新本计划目录的规划文件，复核链接、目录独占、依赖图和 `git diff --check`；本轮不修改项目实现、不启动 Worker、不清理原文或派生数据。只读 QA 指出的接口版本、真实审查阻断、closure 退出码和 G-D 分批依赖已写回施工卡。

**Status:** planning complete；2026-09-29 已按用户“恢复运行”开始 Phase 26。

## Phase 26：恢复实施，S0a observed 与跨仓独占开工（2026-09-29）

- [x] 保全 company-wiki 此前 39 个源码/测试 WIP：`codex/narrative-gates-integration@db3ff32`，同时修复 hook/CI 的已删除 mypy 文件引用；主树 `master@c5ce72b` 与专用代码 worktree 均干净，原件未改。
- [x] 六仓只读 S0a 盘点及有效 WIP 归属；记录 [S0a 现场接口和七件只读试点输入](s0a_observed_interfaces_2026-09-29.md)。RF 旧 fcap 已在远端 main；ET FMP `/2` 与 CWP importer 存在 26/24 字段、MIME、URL 规则冲突，正式 S0b 前不得当兼容。
- [ ] 各仓 owner 在独占目录保存 WIP、写独立 RED、给出 producer golden；总指挥只写本计划目录与 CWP 专用代码 worktree，不跨目录改其他仓。
- [x] CWP SourceVersionReader P0：3 项聚焦 RED 确认旧人工门阻断；用户随后明确授权 pending proposal、prompt review 与 review-store 故障只作诊断。专用代码工作树 `d5162e5` 已让 RED 转绿，保留 open/verify 时真实字节 SHA、身份/期次/root/epoch 校验。G-0 聚焦批 84 passed（另 1 个旧静态断言已纠正，FC701 7 passed），原生四根真实字节 E2E 3 passed，narrative runtime E2E 4 passed，config doctor 14 passed，Ruff/mypy/全部 commit hooks 通过；测试根已恢复。尚需 formal producer golden 与 G-0 余项，不能以聚焦结果代签 G-0。
- [x] ET S0b 首批真实 serializer/CLI golden：本地 `main@4924d57`，FMP `/2` 26 字段与 Motley 24 字段分别冻结；offline 118 passed、合并后 41 passed、golden 10 matched。FMP 真实 200 权益仍未证实；CWP importer 目前不兼容 FMP 26 字段/JSON MIME/query URL，先写 consumer RED，再接 FF。
- [x] CWP 基础 S0b golden 与 G-0 增量：`3dd41e1` 已从真实 CLI 冻结 SourceRef/文本 span/SourceExport 正反 JSON 及 Windows LF（5 CLI tests passed）；`58e2f21` 增真实 P06 四根旧引用迁移、首选同尺寸损坏 fallback、全损坏具名拒绝，以及 P04 429 页/11.2 MB 流式 SHA 内存门。完整 G-0 指定批 **80 passed、0 skipped**，所有独立测试根已清。PDF span 当前合同不支持，真实 PDF locator 留 E5/G-C；G-0 仍需确认原生多根/实际消费者边界与剩余 hold。
- [x] RF 本地 main `8b11b0ce` 已整合严格 evidence SHA 与 review 诊断，197/197 closure exit 0；reader 旧 WIP `3b00b938` 保全但因人工 review 旧语义不直接 cherry-pick。用户随后明确授权自动发布门，RF 本地 main `88b3bda3` 已将人工 `issue-auth` 改为验证当前 HEAD/证据/catalog/容量/回退的自动门，13 个定向测试通过；新 opt-in reader 已基于 CWP golden 做 7 项预期 RED，正在同一 RF owner 实施，FF envelope 消费待汇合。
- [x] StockWiki W01、SourceExport v2 reader、engineering gate simplification 与 W02/W03 identity snapshot/mapping 已并入本地 master；独立整合提交 `c8cfb2e7`，聚焦 99 passed、无 skip，单次全量 `check_all.sh` 598 passed/exit 0。源 worktree 和 `.claude/` 保留。真实 CWP producer→StockWiki reader E2E 已由总指挥验证（3 passed）；G2b 仍缺 owner identity receipt/market-registry 数据，IQS 继续由现有 owner 实施。
- [ ] 用户确认 invest-quick-scan 正由其他项目运行；本任务仅只读对接其 2.2 合同，不再建议或派发第二个 IQS 写入 harness。等该 owner 交真实 schema/公开 CLI 时汇合；其约 500 项活动工作树状态不由本任务清理。
- [x] 基础 SourceExport G-B：StockWiki 真实跨仓 E2E 3 passed；CWP P06 四根真实字节/同尺寸损坏 fallback/全部副本不可用 E2E 1 passed。原件和临时目录均由测试做前后检查。selected narrative package 属 G-C，未在本次 G-B 中宣称完成。
- [ ] 按[总指挥计划](parallel_harness_orchestration_2026-09-29.md)推进 G-A/G2b/G-C/G-D；汇合时只验受影响合同与大节点真实 E2E，Worker 在 G-C 自动门前维持 paused，原始下载文档始终保留。

**Status:** in progress；S0a observed、CWP P0、基础 S0b、G-0 指定测试批、StockWiki 本地 reader/identity 并线与基础 SourceExport G-B 真实 E2E 已完成。G2b owner receipt/market-registry 仍待处理。G-0 的 PDF locator 明确移至 E5/G-C；RF reader、FMP 日期语义与跨仓门仍待汇合。

## Phase 27：StockWiki 已完成 lanes 主线整合卡（2026-09-30）

- [x] 只读核对 StockWiki 当前 refs/worktrees：本地 `master@8590b0e`；SourceExport v2 reader `codex/source-export-v2-reader@0b40683`、W02/W03 identity snapshot/mapping `codex/identity-snapshot-w02-w03@ae11135` 均已有提交且 worktree 干净；两条功能线改动文件无重叠，尚未进入 master。
- [x] 核对最新 IQS G2b handoff：StockWiki serializer 已产出真实 snapshot，但 IQS 正例还需要 owner identity receipt 和 market registry 实体记录；当前 snapshot 仅含 scope-attestation ID/source bindings，故不能将本地实现完成误记为 G2b 通过。
- [x] 新建[StockWiki lanes 主线整合施工卡](harness_lanes/stockwiki_mainline_integration.md)，限制为 StockWiki 单仓、新集成 worktree、两个既有完成分支正常并线、受影响回归和一次 `check_all.sh`；要求保留 `.claude/` 与两个源 worktree，不伪造 G2b 数据。
- [x] 独立 StockWiki harness 已完成主线整合：本地 `master@c8cfb2e7`，reader `0b40683` 与 identity W02/W03 `ae11135` 均已通过正常 merge 纳入；聚焦回归 99 passed、无 skip；单次 `bash scripts/check_all.sh` exit 0（598 passed、Ruff clean、TOTAL ≥73%、`ui.py` 75%、validate-framework 0 errors）。源分支/worktree 保留，根 `.claude/` 保持未跟踪且未触碰。真实 CWP producer G-B 与 IQS G2b owner-context 缺口仍 pending。

**Status:** StockWiki 主线整合已完成并经只读核实；StockWiki 主线为 `c8cfb2e7`，独立施工卡的范围与全套测试门均满足。总指挥随后完成基础 SourceExport G-B 真实 E2E；selected narrative G-C 与 G2b 仍待处理。当前 G2b 实施输入为 Phase 28 的 W04 卡。没有改动 StockWiki 产品代码或生产 source/catalog 数据。

## Phase 28：StockWiki G2b owner-context producer 派发计划（2026-09-30）

- [x] 复查当前 owner 数据模型与 IQS G2b handoff：StockWiki QuickScanStore 只存 receipt ID、没有 receipt 实体和 market registry；基础 W02/W03 snapshot 不输出 `trusted_context`，不能直接通过 IQS 2.2 public CLI。
- [x] 核实市场注册表权威来源：[ISO 20022 MIC list](https://www.iso20022.org/market-identifier-codes) 的官方 CSV 和发布日历可用于 ISO 10383 market→MIC owner projection；MIC 只证明市场/MIC 归属，不推导发行人同一性。
- [x] 新建[StockWiki W04 独立施工卡](harness_lanes/stockwiki_g2b_owner_context.md)，指定 StockWiki 单仓独占、新 worktree、TDD、owner receipt 与 registry 持久化/API、精确 IQS request exporter、真实官方 registry canary、IQS CLI 正反 E2E、生产库只读和测试根恢复。
- [x] 检查并行冲突：RF、FF、IQS 当前有未提交 owner 工作，不派第二写入者；ET 工具/供应商门已实现且本地无未完成的同范围任务；CWP E7 由本总指挥在不同仓库进行。W04 是目前确认可以独立派发的较大产品任务。
- [x] W04 已实现并正常并入 StockWiki：当前 `master@72531b5`，实现提交 `8bee364`，reader 模块大小拆分 `6f0c2c4`；只读确认原有 `.claude/` 保留。W04 聚焦包 64 passed；合并后 `bash scripts/check_all.sh` 651 passed/15 skipped/exit 0，Ruff、coverage 总门/`ui.py`、validate-framework 通过。
- [x] 在当前 IQS `master@65e96ba` 上运行 W04 跨仓 public CLI E2E：真实 StockWiki serializer 正例 exit 0/valid，17 个逐字段负例均 exit 2；真实 ISO MIC canary hash/记录数/辖区数及临时根清理结果见[W04 验收收据](harness_lanes/stockwiki_g2b_owner_context.md)。
- [x] W04 最终验收补强已在 Phase 31 收口：IQS owner 冻结 canonical request golden/SHA；StockWiki 的 OPRT/SGMT 父子关系 RED/GREEN 已合入本地主线并通过整仓门。17 个负例均返回稳定通用具名码 `semantic_validation_failed`；逐 mutation 更细的错误分类不作为本卡验收阻断。

**Status:** W04 实现已提交并进入 StockWiki 本地主线；Phase 31 记录的 golden、parser 关系和全量测试补强已通过。StockWiki 生产身份库未更改；company-wiki E7 与 Worker 状态另按总计划管理。

## Phase 29：StockWiki W04 交付验收（2026-09-30）

- [x] 只读核对 StockWiki merge HEAD `72531b598dcd80325e55e1e70527b7afb89b163f`、W04 commit `8bee364`、伴随的 reader module-size split `6f0c2c4`；保留 `.claude/` 与现有源 worktrees。
- [x] 在合并后 HEAD 运行 W04 聚焦测试 **64 passed** 和一次 `bash scripts/check_all.sh`：**651 passed / 15 skipped / exit 0**，Ruff/coverage/framework 门通过。
- [x] 使用 IQS 当前 `master@65e96ba` public CLI 跑 StockWiki producer E2E：1 个 serializer 正例 exit 0/valid，17 个单字段负例 exit 2；production `data/` 前后快照相同，唯一运行临时根和 coverage/Ruff 产物已清理。
- [x] 最终 W04 卡验收（收口见 Phase 31）：IQS owner 固定 canonical request SHA；StockWiki 补齐 ISO OPRT/SGMT `OPERATING MIC` 父项关系负测；公开 CLI 17 个负例均返回稳定具名错误码。更细的逐 mutation 错误分类不作为本卡阻断项。

**Status（Phase 29 当时记录；最终状态见 Phase 31）:** W04 实现已并线，完整测试门与 G2b 当前 public CLI 正反路径通过；当时仍缺 golden 与 MIC 关系保护。Phase 31 记录了补齐、并线和重跑整仓门结果。该线没有写 StockWiki 生产身份库；RF/FF/IQS 产品代码未由本线修改。

## Phase 30：E7 故障恢复与并发档位复测（2026-09-30）

- [x] R01 双进程同一 ready job 抢占、R04 旧租约晚完成 fencing，各重复 3 次；R09 provider 已接收但响应丢失后的重试/唯一可见 bundle；R11 34 份文档、102 个 DAG jobs 中断后重启恢复。组合回归 **8 passed**。
- [x] 对 45-job、P1/P2/P4 六轮交错 synthetic replay profile 做资源与吞吐试验（每档两轮）；**1 passed**。合成模型/短 handler 基准：P1/P2/P4 中位总耗时 15.31/10.91/6.65 秒；P2 对 P1 提升约 40.3%，P4 对 P2 提升约 64.1%，P4/P2 峰值 RSS 中位比约 1.50。它不含真实 catalog 锁争用，不能单独决定默认档位。
- [x] 用隔离根和显式来源路径复跑 E6 的 4 份真实 PDF/TXT + 1 份低价值跳过控制，P1/P2 各一轮：**1 passed**（输出指标复跑 94.23 秒）。真实文档 replay 配置下 P1/P2 墙钟 45.07/48.13 秒；P2 慢约 6.8%，峰值进程树 RSS 360.9/440.7 MiB；对象输出均 419,428 B / 原文 20,597,846 B = **2.04%**；DB 均 1,011,712 B、WAL 0、busy 错误 0。SQLite busy p95 和 catalog lock wait 未采集。
- [x] 运行器第一次按 worktree 邻接规则找不到电话会源目录；设置 `COMPANY_WIKI_E6_PROJECT_ROOT`、`COMPANY_WIKI_E6_COMPANIES_ROOT`、`EARNINGS_TRANSCRIPTS_E6_ROOT` 后通过。两次运行的隔离 `%TEMP%` 基准根最终均不存在；生产原件/hash 和 company-wiki 生产目录指纹由测试前后断言保持不变。
- [ ] E7 暂定策略：production Worker 保持 paused/default-off。单轮真实样本中 P2 未达到计划的 25% 提速门，故若继续做隔离试用，以 P1 为保守比较基线；合成基准中的 P2/P4 提速不外推到真实 workload。只有补充交错真实样本轮次并测 catalog/SQLite 锁等待后，才决定是否启用更高并发；P2M/P4 不作为默认候选。

**Status:** 进程争用、过期租约 fencing、丢响应重试、100+ job 重启恢复和 bounded synthetic profile 均已测试；真实 E6 P1/P2 样本指标已取得但只是一对、且使用 replay 模型。现有证据支持继续保持默认单 worker/生产 paused，不支持宣称并发已带来端到端提速。下一大节点仍是 E-B 集中集成验收与 runtime composition；RF/FF/IQS 未改，唯一原始文档未动。

## Phase 31：W04 MIC 关系补强与最终验收（2026-09-30）

- [x] 对 ISO 10383 Operating/Segment 关系先写 RED：旧解析器对空父项、缺失父项、OPRT 非自引用和环均未拒绝；4 个负测如预期失败。
- [x] 实现受约束关系校验：Operating MIC 必填且格式有效；OPRT 自引用；所有父项存在；SGMT 可嵌套，但引用链必须最终到 OPRT，环具名失败。允许合法跨市场父项，不引入 country 相等门。
- [x] 将补强提交 `afa9692` 合并进 StockWiki 本地 `master`，合并提交 `b4f3846bb3e331f5661edee974a7d0b76dbf9664`。变更只有 parser、对应测试和隔离 fixture；保留原有 `.claude/`，未写生产数据。
- [x] 实际官方 MIC CSV canary SHA `79de0f7704e260bd49b0d2439f3084891cabc93481da8bdbaa716e15a27211ed`：2,883 records / 149 jurisdictions，其中 8 条嵌套 SGMT、2 条跨市场引用均通过。
- [x] 合并前跨层聚焦测试 **57 passed**；合并后 StockWiki `bash scripts/check_all.sh` **686 passed**、Ruff clean、coverage 总门通过、`ui.py` 75%、validate-framework 0 errors（11 条既有 type warning）。全部临时根、coverage/Ruff 产物和精确官方 CSV canary 均复核后删除；生产库与原始公司文件保持不变。
- [x] 对照 IQS owner acceptance receipt：canonical SHA 已固定为 golden/断言；正反公开 CLI 路径通过。17 个负例采用稳定通用错误码 `semantic_validation_failed`；更细的逐 mutation 错误码不阻塞 W04 验收。
- [x] 按用户“手头工作做好就暂停”要求，完成本轮 W04 验收记录后暂停后续项目施工。

**Status:** W04 owner-context producer 与 MIC 关系补强均已本地合入并通过完整质量门；剩余 G2b capability 按 IQS owner 收尾范围跟踪。本轮暂停，不继续 E-B/G-C/G-D 或其它跨仓实现；恢复时先读取本阶段和各仓最新状态，避免重复或覆盖活动工作。

## Phase 32：E-B 集中测试验收与分支整合状态（2026-10-01）

- [x] CWP 专用 worktree 的 E-B 聚焦回归通过：`404 passed, 2 skipped, 695 deselected`。运行时设置 `PYTHONIOENCODING=utf-8`、`PYTHONUTF8=1`，覆盖此前 Windows 默认 CP936 与 pytest UTF-8 capture 的子进程输出编码冲突。
- [x] 增补并提交进程级恢复测试 `cba745a`：R05 pause-vs-finish、R07 ACK 后进程退出与恢复各重复 3 次；R08 使用真实 `CatalogOperationLock` 验证 AUTO ACK 持久后 artifact 保持 prepared/invisible，释放锁后 reconcile 只发布一个 visible version。相关焦点测试通过。
- [x] `pre-commit --all-files`、提交 hook 的 Ruff、config doctor、host guard 通过；contract mypy 在该提交仅包含测试文件时按配置跳过。
- [x] E6 最新四文档 P1/P2 隔离 replay 通过：P1 90.14 秒、159.8 narrative docs/h、RSS 401,235,968 B；P2 84.776 秒、169.9 docs/h、RSS 495,566,848 B。P2 墙钟改善约 5.95%，吞吐改善约 6.3%，RSS 高约 23.5%；raw 20,597,846 B、selected objects 419,428 B（2.04%）、skip artifact 1,441 B、5 visible、4 model calls、0 retries/SQLite busy errors、DB 约 1.0 MB、WAL 0。catalog lock wait 与 SQLite busy-wait p95 未测。
- [x] 生产 Worker 控制仍为 paused；未发现 runtime worker JSON、automation DB 或 operation lock。新增测试用根均已清理并复核原本不存在的目录恢复为不存在；生产原件未改。
- [x] 只读核对跨仓本地分支祖先关系：StockWiki 已知 W02/W03、SourceExport reader、W04、G2b 分支均并入 `master@b4f3846`；ET transcript adapter 与 `main@4924d57` 同 HEAD；IQS 本地 `master@091999d` 干净。CWP transcript-companion/fcap/r4b06 分支已是 `master@b0fd763` 的祖先，但 CWP master 本身比 `origin/master` 超前 44 个本地提交。
- [ ] RF 优先项部分收口：`fcap@ee0a82bf` 是本地 `main@3e03ce83` 的祖先（审计时为 `415d8eb3`）；reader 支线唯一提交 `3b00b938` 是旧原型，当前 main 后续已有 opt-in reader 实现，但原型还包含 main 未有的准备逻辑和跨仓测试，需评估后择要复用，不能整提交 cherry-pick。RF 审计卡报告已交付并复核（见[报告](harness_lanes/results/revenue_forecast_worktree_audit_2026-10-01.md)）：12 个 tracked 路径和可见 untracked 路径已分类；7 个 ACL/长路径不可见子树使 404 仅为下界，不能据此清理。报告没有无条件可删除项，最多约 40.3 MB 是 owner 核销后的 scratch/测试台架候选，对 46 GB 历史体量收益很小。用户 2026-10-01 后续裁定放宽缺 hash 的闭环门：evidence path 必须解析为仓库内可读普通文件；缺失/空白 `fixture_hash` 只计入 pending 诊断、不阻止闭环；一旦提供 hash，仍须为 64 位 SHA-256 且匹配实际字节。缺失/越界/不可读路径仍阻断。已在 RF main 按 TDD 实施，并由真实临时文件单测、三仓 summary 和双 CLI 共 33 项定向测试通过；整套目录测试因调用 CodeGraph 的 `prepare_source` 子进程未返回而停止，已清理测试根。dirty fcap 版本不直接 cherry-pick。另对 RF main 真实 197 项 registry 做只读核验；内存中移除 AR-01 的 hash、保留真实证据路径后 closure_ready=true、pending=1，registry SHA 不变。
- [ ] FF 本地 `main@c9799b7` 尚未包含 fcap、SourceRef v2 和 transcript companion 支线（各有 39、41、45 个仅分支提交）；专用工作树干净但未并线。暂由 FF owner 维护，不另开同仓 harness。
- [ ] CWP 主线整合未完成：专用分支 `cba745a` 的测试验收成立，但该工作树与 `master@b0fd763` 分叉；两侧分别有 9 与 13 个独有提交，整体差异 77 个文件。需按提交和文件逐块判定哪些有效后再整合，不能直接 fast-forward 或将分支整体视为已并线。

**Status（Phase 32 首次盘点时）：**这是 Phase 33 之前的状态快照；其中 E-B 未并线、RF/FF/ET/IQS/StockWiki HEAD 与完成度描述均已由 Phase 33 的 live audit 更新。不要据此重复启动 E-B 或 W04。

## Phase 33：跨线进展与 PWF 一致性复核（2026-10-01）

- [x] 核对 CWP、RF、FF、ET、StockWiki、IQS 当前 HEAD、分支/工作树状态及各自最新可读 PWF/交接收据；不读取凭据，不修改其他仓库，不清理任何外部目录。
- [x] 确认 CWP E-B 已并入 `master@00af53f` 的历史；StockWiki W01/W02/W03/SourceExport/W04/MIC 分支已全部成为 `master@b4f3846` 的祖先。保留旧 worktree；它们无分支独有提交，删除并非本次任务必要条件。
- [x] 确认 RF `fcap@ee0a82bf` 已提交历史在 `rf-impl main@3e03ce83` 内，main 比 origin 超前 4；dirty fcap 的旧审计仅能确认 404 个可见未跟踪项下界和 7 个不可见子树，当前仍不可整树提交、恢复或清理。已放宽的缺失 `fixture_hash` 规则已在 RF main 提交并通过 33 项定向测试。
- [x] 确认 FF 当前 `fcap@d35b6f5` 等于 origin main，命名为 `main` 的本地 ref 落后 39；SourceRef v2 与 transcript companion 位于两个独立、当前干净的 worktree，至少 4 个核心文件重叠，须保留单一 owner/集成分支，避免并行互相覆盖。
- [x] 确认 ET `/2` producer 在 `main@4924d57`，本地比 origin 超前 6；`.workbuddy-ai/` 与 `eval_results.json` 仍是未跟踪本地内容，既有 ET PWF 已将其归为旧工具记忆/评测产物，本次不打开正文、不删改。生产 FF companion 尚未整合。
- [x] 确认 IQS `master@e7fe99c` 当前有 owner 对 `task_plan.md` 的未提交编辑；不覆盖。provisional G2b E2E/五态 DTO 切片之外，IQS 最新 PWF 仍将 full G2b、QA-04 交付和 SW-IDENT 完整交付记为 partial/pending；DWA-03/04/05/06 后续事项没有形成新的独立写入线。
- [x] 对照 CWP PWF，发现并修复 live 状态快照漂移：master ahead 61→62、E-B 未合并→已合并、W04 可派发→已完成；同步本计划、CWP lane、总编排的当前状态，并把 Phase 32 标为历史快照。
- [x] 补清下一大节点合同：selected narrative 是 `NarrativeBundle /2.0`，与 raw `SourceRef 2.0`/`SourceExportBundleV2` 分开；先由 CWP 固定 pathless bundle reference、artifact SHA、source binding、as-of/locator golden 和真实 CLI 读回，再由 RF/StockWiki 各自接入已有查询入口。只有确有需要时才评估通用 artifact-role DAG；不把原文全文塞入 selected package。
- [x] 仅验证本轮文档：9 个已编辑 Markdown 的相对链接无缺失，`git diff --check` 通过。产品代码未改，因此未重复跑产品测试；已有 E-B/W04/RF 测试收据按原范围引用。
- [ ] G-0/G-A 仍按原顺序补完；随后推进 G-C selected narrative producer/consumer E2E，再进入 G-D 分批派生清理。当前无证据支持修改总顺序或启用生产并发。

**Status:** 盘点与 PWF 校准完成；实施计划保留原依赖顺序，仅补充 selected bundle transport 的具体边界和 owner 交接。Worker 仍 paused/default-off，原文保留。跨仓 E2E 与派生空间清理仍未完成。

## Next Step

按用户要求，完成本轮提交/远端发布后暂停。恢复时先复核 live owner 状态，解决 RF historical snapshot/live HEAD 的发布检查并正常推送，再完成 G-0 剩余真实 reader/locator 与 G-A（含 FMP JSON admission 和 publication 未知语义），不重复 E-B/W04。随后由 CWP 固定独立 `NarrativeBundle /2.0` pathless export/read CLI，RF/StockWiki 各自接入并跑 G-C，再按相关消费门和无引用事实进行 G-D 精确派生清理。Worker 保持 paused/default-off；不清理其他 owner 的 dirty tree。
