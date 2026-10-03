# 多余门禁、权限与工程签收统一清理方案（2026-09-29）

> **2026-10-03当前状态覆盖：**本页保留09-29历史施工基线；P0主来源链已实施，P1/P2尚有明确残留。当前逐项裁定以[46项门禁现状](gate_permission_inventory_2026-10-03.md)为准：旧人工reviewer/工程工具尚未全退役，不能把本页当全部未开始或全部完成。RF缺fixture hash已按用户10-01裁定降诊断且允许闭环，下表旧“缺hash不ready/回填197hash”不得执行。本文以下是当时方案。调查基于 2026-09-29 可见工作树；并行 harness 开工前总指挥重新记录各仓 HEAD、未提交文件与当前调用图。用户已授权本项目已配置文档用于外部 LLM，已授权明确公司/期次采集任务及匹配电话会议；原始下载文档及其 SHA/来源事实必须保留。此页先完成清理裁定，再由[并行总计划](parallel_harness_orchestration_2026-09-29.md)分仓施工。

## 1. 裁定口径

| 类别 | 处理 | 判定例子 |
|---|---|---|
| 人工许可和工程签收 | 移除运行阻断与重复字段；历史记录保留只读 | 每文档/每期授权、reviewer 身份、approval_ref、rights-policy hash、独立 B.AR、递归任务 receipt |
| 数据正确性 | 保留并自动测试 | 公司/证券/期间、as-of、来源状态、原文字节和 SHA、locator、引用、版本、同 key 不同 hash、路径逃逸 |
| 资源与外部副作用 | 用一次明确请求和配置上限约束 | provider 开关、凭证、单次文件/字节/时间/费用预算、并发和退避；Worker pause 是运行状态 |
| 证据与研究语义 | 按 owner 合同保留，简化重复证明 | RF 有 `evidence_path` 必须有实际文件 SHA；StockWiki 投资结论 accepted/rejected；IQS 身份错配拒绝 |
| 质量诊断 | 可记录，不挡普通处理 | prompt injection 扫描状态、低质量解析标志、人工草稿 review 状态；正文始终作为不可信数据 |

`receipt` 一词本身不构成删除依据。下载结果/verified read/Worker attempt 是机器产生的来源或恢复事实；人工审批回执和每步骤重复签名才属于本次清理。清理代码前先用当前调用者、数据库持久状态和真实入口判断是否执行，不能只靠历史 PWF 文本或搜索命中。provider 的实际接口和条款仍受约束：例如 [The Motley Fool 官方规则](https://www.fool.com/legal/terms-and-conditions/fool-rules/)限制脚本抓取，自动采集保持 disabled；[FMP 官方条款](https://site.financialmodelingprep.com/terms-of-service)由账户和套餐决定使用范围。两者都没有要求项目建立逐文档人工 rights receipt。

## 2. 清理范围与代码级施工卡

### P0：先消除真实产品链的阻断

| Owner / 现行位置 | 已查明的行为 | 要实施的最小新规则 | TDD 与验收 |
|---|---|---|---|
| CWP `source_catalog/resolver.py:1350,1423`、`source_reader.py:464-537,589`、`remediation.py` | 仅因 `remediation_proposals.status='proposed'` 即拒绝复用/导出/叙述读取；`capture_ready` 又要求 `review_status='not_detected'`，review store 故障会抛 `review_unavailable`。proposal 创建/批准无生产调用者，可能无限等待 reviewer。 | proposal 与 prompt-review 只作独立诊断；metadata-only `query_local` 的 `capture_ready` 仅看捕获/provenance/身份元数据，**不在查询阶段读全文**。缺 review receipt 或 review store 故障不阻候选查询；`open_version/verify_version` 使用前必须验实际字节 SHA，错原文仍拒绝。仅已证实的身份冲突、`quarantined` 等实际不可用状态阻断。真实修复走隔离构建→自动验证→原子发布。 | 先写“pending proposal/无 review receipt/review store 故障仍可查询、open 正常字节”和“篡改后 metadata 查询仍可返回候选、open 因 raw SHA 错拒绝”；改 `test_source_version_reader.py`、`test_source_version_reader_cli.py`（含旧无 receipt=>false 断言）、`test_remediation_workflow_fc403.py`，加真实字节 E2E。 |
| CWP `source_catalog/close_gap.py:218,266`、`authorization.py`、`acquisition.py:426`、`cli.py:1230`、`runtime_policy.py:102-139`、`source_reader.py:152-174` | `runtime_policy.json` hash、binding、程序生成的 `DownloadAuthorization`、expiry/receipt hash 层层绑定；普通 ensure 又可走 `allow_download`，不是统一权限语义。 | 一个精确 `RequestPlan` 携 request/gap 身份、provider、候选 accession、有限项目/字节/时间预算；下载前验证一次，导入时验证实际 URL、MIME、长度和 SHA。**保留当前 root/config/activation epoch 的即时复核**：计划后配置或可见性改变，则零 fetch 或重规划。只删多余 approval receipt hash 与重复 policy-hash 字段，不删真正的当前可见性校验。 | `test_close_gap_fc801.py`、`test_close_gap_concurrency_fc804.py`、`test_source_catalog_download_authorization.py`、`test_runtime_policy.py` 改为新合同；保留 stale gap、计划后 root/config/epoch 改变时 0 fetch、未明确请求 0 fetch、超额、并发 single-flight、原文不变反例。先发布 CWP producer/golden，再改 FF consumer。 |
| FF `scripts/fetch_filing.py:720-790,881-1010`、`scripts/filing_contracts.py:109-201,395-500` | `--allow-download` 与请求内五字段 `authorization` 双门；还重复传 `policy_export`/`policy_hash` 并复核 N-1 fallback。 | 一次明确公司/期次请求决定联网意图；FF 仅传 CWP 精确 request/candidate 和资源上限，保持 v1 默认响应兼容。CWP 决定 canonical 保存和来源身份；FF 不读写 CWP 内部数据库。 | FF v1 golden 退出码/JSON、v2 SourceRef 正反例、latest 与 close-gap 真实 CLI、未请求 0 网络、重复 0 下载、超限/错期拒绝；跨仓 FF→CWP→RF 由总指挥验。 |
| ET `transcript_api.py:75-130,546,690,868`、`transcript_tool.py:28-75` | `download_authorized` 与 `--allow-download` 叠加，工具可覆盖为 false；Motley 当前双开关为真仍能发请求。 | 一个明确的精确 FY+Q 网络请求；保留 HTTPS/host/redirect、候选绑定、字节/时限和未翻译原文。运行时 provider 配置默认禁用 Motley，fake HTTP 证明即使收到明确请求仍零抓取；FMP 缺 key/402/无权益返回具名 unavailable。两者不可用时 FF companion 具名降级。 | `tests/test_transcript_api.py`、`tests/test_translation_controls.py`：精确期次、无翻译、默认禁用 0 网络、redirect/超限/错误身份；ET CLI 需有测试 transport 注入后，ET→FF→CWP fake-provider E2E 在 G-A 跑。 |
| RF `scripts/source_preparation.py:182-206`、`scripts/company_wiki_source.py:418-440`、`scripts/contracts/evidence.py:380-445`、`scripts/revenue_core.py:524`，以及 FF `filing_contracts.py:249-382` | FF 缺 review 字段时置 `not_reviewed`，RF 的准备、source adapter、证据合同和 core 消费层仍把它当拒绝理由；这与已简化的 CWP 无人工 review receipt 链冲突。 | review 状态仅可作诊断；来源处理按 verified bytes、SHA、期间、parser 结果和可回放证据决定。调用计数继续记录，缺数字不得凭空写 0。 | CWP producer→FF envelope→RF `prepare_source` 真入口 E2E：无 review receipt 正常处理、错 SHA/期间拒绝、恶意正文不执行指令。迁移 `test_fc905b_trusted_receipt.py`、`test_message_contract_pins.py`、`test_source_preparation.py`、`test_company_wiki_source.py`；保留 schema/引用核验。 |
| RF `assurance/unified_completion/uc/scenarios.py`、`uc/cli.py`、`uc/closure.py`、`scenario_registry.json` | 197/197 passed 行有 `evidence_path`，0/197 有 `fixture_hash`；未提交放宽实现让缺 hash 仍 `closure_ready=true`。现行 `closure_report(payload)` 无根参数、scenario verify CLI 在不 ready 时仍返回 0、三仓报告只数 `passed`；`cmd_closure_report` 退出码也只看旧 `old_plan_verdict`，坏 hash 可能打印后返回 0。 | 按用户已裁定的规则自动计算并保存每个现存证据 SHA；设计唯一权威 `verify_evidence(registry, repo_root)`，逐项做根目录约束和实际字节 SHA，给 scenario/三仓报告复用；缺/错/越界均不 ready，两个相关 CLI 都非零退出。旧 plan incomplete 可继续作为独立诊断，不掩盖 hash 失败。197 个文件合计约 50.8 KB，自动回填成本很小。 | `assurance/unified_completion/tests/test_scenarios.py`、`test_closure.py`、两个 CLI 子进程正反例，`tests/test_ca301_clean_checkout.py` 和 manifest 测试；覆盖无 hash、文件缺失/篡改/越界和 CLI 非零；不得改动原证据内容。 |

### P1：缩减运行时影子门与人工审批状态

| Owner / 位置 | 处理 | 保留测试和数据 |
|---|---|---|
| CWP `automation/models.py`、`migrations.py`、`store.py` 的 Approval 表/API；`human_inbox.py`、`handlers/gold_review.py`、`planner.py` | 核对当前 handler 注册后退役无人使用的人工 approval CRUD、占位 `gold.validate_receipt` 和由它造成的 `BLOCKED_HUMAN`。历史 SQLite 表保留只读，不做破坏性 DROP；通用失败、重试、lease/dead-letter 仍保留。 | `test_automation_planner.py`、`test_automation_gold_review.py`、`test_automation_models.py`、`test_automation_store.py`、`test_automation_worker.py`；默认正常叙述 job 无人工队列，异常有终态/重试。 |
| CWP `automation/policy.py`、`registry.py`、`controller.py`、`scheduler.py` | `allow_llm` 已默认 true，但 network 默认 false 可使注册为 `network=True,llm=True` 的 `source.narrative_summarize` 编排失败。模型 API 调用也是联网，不能假标成本地无网络任务。 | 将已授权叙述任务的模型网络能力单独纳入费用/速率/并发预算；采集正文网络仍只由明确精确请求/provider 配置开启。不要靠把 summarize `network` 假设为 false 过门。 | `max_fan_out`、费用/并发上限和 Worker pause/recovery；测试默认 `plan_jobs` 能排 summarize、实际模型调用受预算/限流、未请求采集为 0 fetch。 |
| CWP `source_lifecycle.py`、`readiness_graph.py`、`prompt_injection.py`、`prompt_injection_guard.py` | 当前强制 review receipt 的 readiness 为 shadow/read-only；删人工 reviewer/TTL/receipt 才 ready 的语义，或将遗留字段降为可选诊断。`source_reader.py` 的 review metadata 不得使 verified open/LLM 摘要失败。 | `test_source_lifecycle.py`、`test_readiness_graph.py`、`test_prompt_injection_guard.py`、`test_source_version_reader.py`、`test_gp003_llm_exit_receipt_privacy_gate.py`；无 receipt 可处理、错 hash 时 0 LLM 调用、模型输出只按引用/结构接受。 |
| CWP `activation.py`、`restore.py`、相关 CLI | `reviewer` 当前必填；由本地 actor/run ID 自动记操作来源，移除第二人签收要求和强制 CLI flag。 | assertion verified、policy snapshot/CAS、epoch、单文档 SHA/provenance 与原子回滚；`test_activation_transaction.py`、`test_restore_flow.py`、reader 相关合同。 |
| IQS `scripts/task_receipts.py` 与 `docs/implementation/contracts/task-receipts.md` | 每 assertion log/hash、独立 reviewer、递归依赖 receipt 和 P01 两次人工审查退出新的工程闭环；旧文档/收据只读保留。 | 每仓简短运行记录：HEAD、测试命令/退出、样本 SHA、测试根恢复、未解问题。旧 verifier 专属测试按历史归档或删除，仅为新的交接格式写少量直接行为测试；G2b 做身份真消费。 |
| IQS `scripts/deployment_contract.py:224` | 尚无生产调用者的 `explicit_user_confirmation`/`approval_ref` 退役；未来实际外部调用依明确请求和单次预算。 | 发布集合、策略版本、费用上限、实际 provider 错误保留；用定向单测确认。 |
| RF `tools/release_readiness.py:116-148` | 仅独立 readiness 工具要求人工 `release_authorization.json`，生产/CI 调用未发现；改为自动 integrity/capacity/rollback 结果，退役签发字段。 | `tests/test_zr1001_release_readiness.py`；保持坏原件/容量不足/回退不可用负例。 |

### P2：合同、配置和历史文档收口

| Owner / 位置 | 处理与顺序 | 不得误删 |
|---|---|---|
| CWP `config.py`、`models.py`、`policy_2x.py`、`policy_3x.py` 的 `privacy_class` | 当前不控制 LLM 外发，却进入 RootPolicy 3.0 导出 hash。先列读/写 consumer、发布新 schema/golden 并迁移 FF/RF/StockWiki；显式版本切换后再删字段，不静默改变旧 hash。 | root containment、read-only root 的写入归属、不可变 raw 和路径逃逸检测。 |
| CWP `scripts/deletion_manifest.py:168,234-240` | 派生清理清单不再强制 `user_authorized`/`independent_review_required` 工程签收；用户已授权清可重建派生。 | HEAD/精确路径、类别、非原文、文件 hash、无引用、重建及净空间差异。`test_deletion_manifest.py` 加原文拒删负例。 |
| CWP `dropbox_governance.py`、`scripts/gold_review_gate.py`、`scripts/reviewer_gate.py`、旧 Wiki review queue | 先核实无生产调用；历史/只读盘点和硬编码个案退出默认命令，必要的同 SHA 多位置证据并入通用 locator 报告。 | 不用“未调用”推断可删来源；原始文件/manifest 均保留。 |
| RF `scripts/contracts/evidence.py` host receipt、`scripts/revenue_publication.py` formal publication receipt | 这两处仍属于活跃预测产物链，先用真实 producer/consumer 判别哪些字段证明来源与版本，哪些只是人工签名；只删后者。 | 模型输入证据 hash、期间/as-of、不可变预测快照、可追溯发表版本。 |
| IQS `scripts/contract_validation.py` trusted receipts | 按身份、检查等级、并表范围、搜索/导入内容逐项做字段等价测试，再用 owner 记录+来源证据/修订/hash 替换重复人工证明。 | 母子公司错合、证券/上市地错配、期次漂移、伪造高等级证据仍拒绝。 |
| StockWiki `AGENTS.md`、`scripts/check_all.sh` | 开发中只跑受影响测试；跨仓大节点跑一次全量与覆盖率，去掉同一次提交重复运行 pytest。 | `review_workflow.py` 的 accepted/rejected 是下游投资研究状态，不能按工程签收删除。 |
| 现行 PWF 与各仓历史记录 | 以本页和并行总计划为当前入口；将 `task_plan.md`、跨仓总计划、`test_acceptance_plan.md` 中仍写独立 B.AR、rights-policy、人工 reviewer 的**未来动作**改成自动验证。旧结果保留日期和历史标记，不重写既有实验收据。统一当前节点名 G-0/G-A/G-B/G-C/G-D，旧 G0–G4 仅作历史别名。 | 原件退役收据、历史测试失败事实、Git 证据仍可追溯。 |

## 3. 执行顺序与共享接口

1. **冻结基线**：各仓 owner 在可完整访问的环境记录 HEAD、活动脏树和生产入口；CWP 当前简化改动尚未提交，StockWiki W01 未跟踪，IQS/RF/FF/ET 各有 WIP。先归属/保存有效改动，再建立仓库独占 worktree。不得在活动脏树上整体 reset/clean。
2. **先测真实 P0 阻断**：先固定当前 producer 的只读基线并写 G-0/P0 的 RED 测试，再修 CWP remediation、`capture_ready`/review-store、close-gap 与 RF review/hash；修复后跑正式 G-0 验收，再允许 FF/RF 依赖消费者切换。ET、FF、CWP 各自给出一次精确请求接口。外部 provider 全用 fake HTTP，原文仅复制到隔离根。
3. **再收 P1/P2**：删除无人调用人工状态，迁移配置 hash 和消费者，历史表/收据只读留存。每个改动只跑受影响单元/合同测试；版本兼容只为真实持久消费者提供，旧 `/1.0` 试点对象不凭空维持。
4. **集中跨仓验收**：G-0 验 CWP 四根 verified reader；G-A 验 FF→CWP→RF 与 FF→ET→CWP；G-B 验 StockWiki 来源读，G2b 独立验 StockWiki 身份 producer/IQS 校验；G-C 验 selected bundle/Worker 故障恢复；G-D 按清理批次的实际消费者引用选择相关前置并验可重建派生/受控发布。每个节点一次真实样本 E2E，失败只回退受影响路由。不另要独立 reviewer 或人工签收。

## 4. 统一测试包和停止条件

- **单元/合同**：新规则先写反例，分别证明“无人工 receipt 正常”“错误 SHA/身份仍失败”“超预算仍失败”；删除旧测试时必须由同一产品行为的新测试替代，不以删测制造绿灯。
- **集成**：真实 producer 序列化正例；consumer 对版本未知、字段漂移、路径泄露、错期、撤回、损坏 bytes 给具名失败。人工手写 JSON 只用于畸形反例。
- **端到端**：12 件代表性 PDF/TXT 的相关小集合，G-A 的真实 FF/ET/CWP/RF 入口，G-B 的 StockWiki CLI 与 IQS 身份，G-C 的 1/2/4 文档并发，G-D 的派生重建/同卷净字节。每组使用独立测试根；结束核原件路径/大小/SHA 与本次测试树前后相同，清理本次生成的 DB/WAL/cache/下载。
- **停止**：原件或 manifest 变化、来源身份/期间/哈希/locator 错、未请求联网、费用/字节超限、同 key 两份不同内容、测试树无法恢复。仅暂停该能力；不生成审批队列。provider 实际条款或套餐不清时只关闭那个 provider，离线开发继续。

完成定义：六仓的**来源采集、解析、叙述摘要与工程发布链**无需逐文档人工批准、reviewer、双重授权布尔或递归工程签收；自动正确性/预算测试和跨仓真实样本门通过；用户可从一个总计划看到实际可用能力及尚未验证的 provider。StockWiki 投资研究的 accepted/rejected 决策状态继续由 StockWiki 独占。此定义是未来实施验收标准，不表示本次规划已完成代码清理。
