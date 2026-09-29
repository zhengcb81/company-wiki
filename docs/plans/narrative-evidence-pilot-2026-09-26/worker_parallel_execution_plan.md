# 多文档并发 Worker：可实施设计与验收手册

> **状态：PLAN ONLY；未实施、未启动、未解除暂停。** 本文件是本专题并发方案的实施入口；[worker_parallel_recovery.md](worker_parallel_recovery.md) 保留设计背景和故障分类。复用 [Worker v5](../source-catalog-worker-recovery-v5-2026-09-03/README.md) 和 [R4 C/D](../painpoint-outcome-audit-2026-09-05/simplified-execution-plan.md) 中仍适用的自动技术断言，不叠加人工签收、逐 job 权限 receipt 或同一测试重复跑。本专题按 [G0–G4](milestone_review_cadence.md) 的大节点运行端到端测试，N0–N6 不是七次独立审查。用户已授权的明确公司/期次任务覆盖其文档和电话会配套处理；运行次数/费用/字节上限是自动资源控制，不是再次索取人工授权。

## 0. 结论与边界

**目标**：在同一时间处理多个**不同文档**的解析和来源证据计算，提高完成文档/小时；保留同一文档的依赖顺序、来源身份、幂等性和 Worker 暂停。首版不做同一 PDF 的章节并行，不启动多个现有 `SourceCatalogWorker` 实例，不共享 `LLMClient` 或 SQLite connection。最终对 catalog 的写入仍由一个受控提交器串行执行短事务。

**可靠性承诺**：派发/心跳/ACK 可以丢，计算可能执行多次；同一 `job_key` 在同一来源与策略版本下**至多一个被接受的产物**。生产进程或 Windows 会话退出后，任务从持久 job/attempt 与 catalog 产物对账恢复。外部 LLM 调用无法保证恰好一次计费，超时后的未知调用记账并受预算上限约束。

**禁止捷径**：不能直接把现有 Worker 放进线程池/起多个副本；不能把 `processing_demand.py` 内存队列或 `producer_attempts` 审计当持久 job；不能另建第三套任务队列；不能在长 PDF 解析或 LLM 等待时持有 `CatalogOperationLock`；不能用一个正常路径测试声称“丢包可恢复”。

## 1. 与已有计划和代码的精确衔接

| 现有归属/代码 | 已核实事实 | 本计划交接点 |
|---|---|---|
| R4 C05 | 唯一持久 job/attempt 入口、source+角色+版本幂等键、lease/fencing、失败恢复；不建第三套队列 | 复用 `src/company_wiki/automation/` 的 `jobs/attempts/effects/outbox`。先运行其对应合同测试，再接 narrative handler；接口变化时只重跑受影响的映射测试。 |
| R4 C07 | 要求单写者/短事务，并在隔离真实数据上验证读写争用、崩溃与取消 | 本计划的计算进程不写 catalog；writer 的短提交与跨库恢复作为 C07 的 narrative 用例。 |
| R4 D01–D04 / Worker v5 | 禁止自动删除原始文档；任务持久化、取消/恢复和资源上限需有自动测试 | N0–N5 可在隔离目录实施。真实 Worker 仅在自动化 E2E 通过、操作命令限定公司/期次并具备资源上限后运行；不要求额外人工启动收据，也不允许 Worker 删除原始文档。 |
| `source_catalog/worker.py`, `service.py` | `run_cycle` 串行；`normalize`/`summarize_with_llm` 在整个调用期间持 `CatalogOperationLock` | 保留旧入口和暂停行为；新执行器在 feature flag 关闭时不接管。把“选任务→锁外计算→短提交”做成新路径，按公司/类型灰度，不直接删旧锁。 |
| `automation/migrations.py`, `store.py`, `worker.py` | 已有表、WAL、唯一 `job_key`；但 AUTO CLI 报 `not_configured`，目前未接生产 Worker。`_try_claim` 的状态转移/attempt 插入为多个事务；完成 attempt 的 `put_attempt` 与旧记录冲突后被忽略；outbox 是另一次事务 | 先修原有入口的原子 claim、续租、finish、outbox、reap；不能把表存在等同于并发安全。 |
| `source_catalog/store.py` | catalog 是另一 SQLite DB，`artifacts` 有 `UNIQUE(document_id,artifact_role,generator_name,generator_version)`；旧 normalized/summary 文件名可能被同文档重用 | 两库无法自然共享一个提交事务。新叙述产物走可回查的版本行和内容寻址文件；用 effect/对账完成跨库 saga，绝不静默覆盖旧产物。 |

**可执行工作的所有权**：AUTO 基础事务归 R4 C05；writer/争用归 C07；暂停、Windows 生命周期、H01 归 v5/R4 D；本专题只拥有叙述型文档的 job DAG、handler、证据验证、吞吐试验和消费包。若别的计划已交付同一组件，先只读核对版本/测试，禁止重复实现。

## 2. 进程拓扑与职责

```text
现有 WorkerController（保持 paused；未来受 v5 监督）
    └─ narrative coordinator（唯一调度者，默认 disabled）
         ├─ AutomationStore：唯一 jobs/attempts/effects/outbox 真相源
         ├─ parser 子进程池：不同文档，原文只读，返回小型 manifest
         ├─ model 子进程池：不同文档，每进程独立 LLMClient
         ├─ verifier：确定性来源/locator/角色/时间校验
         └─ catalog commit actor：唯一 writer，短事务；导出由 outbox 驱动
```

Coordinator 只从 `jobs` 领取；在途数量受 `max_total_inflight` 控制，parser 与 model 分别占资源槽。每个子进程只收到固定 schema 的 `job_id / source_id / source_sha / input artifact hashes / stage / budget / stop token`，只读 allowlisted 原文路径，在隔离 temp 目录写内容寻址候选文件，返回 `{schema_version, job_id, attempt_id, lease_token, source_sha256, result_sha256, byte_size, temp_path, usage, error_code}`。不能把 429 页 PDF 全文经 IPC/JSON 管道复制。子进程不得直接写 catalog、job 状态、export 或其他仓库。

Windows 使用 `spawn` 与可 pickle 的模块级入口；parser 继承现有超时、父进程存活监测、Job Object 子孙清理机制。Model 子进程也须被同一 supervisor 生命周期约束，超时/暂停时先取消，再有界强杀；关闭句柄后无孤儿。`LLMClient` 每进程单独创建，但**共享供应商级预算与限流服务**必须在发请求前原子预留 token/费用；只靠每个 client 自己的 `_last_call_time` 会超额。Worker v5 已规划网络前持久 request ledger 和 cost reservation，本卡只消费届时通过审查的统一接口；若未实现，则 model 并发保持 1 且真实外发路由 blocked，不能另造私有预算表。预算不足时任务保留 `retry_wait`/blocked，不发请求。

首版资源配置（只用于隔离试验）：`max_total_inflight=2, max_parser=2, max_model=1, max_catalog_commit=1`。这是安全起步配置，**不是最终最优值**。R2 先比较下表中 P1/P2；统一预算与限流接口完成后才测试 P2M/P4。扫描、来源登记和最终导出仍串行。复杂文件多 agent 核验属于后续可选 R3，不是并发多文档的前置。

| profile | total | parser | model | commit | 目的 |
|---|---:|---:|---:|---:|---|
| P1 | 1 | 1 | 1 | 1 | 可靠性与吞吐基线 |
| P2 | 2 | 2 | 1 | 1 | 先验证解析与模型等待的流水线重叠 |
| P2M | 2 | 2 | 2 | 1 | 统一预算/限流通过后，测模型并发的增量 |
| P4 | 4 | 2 | 2 | 1 | 仅在 P2M 质量/资源门槛通过后测上限 |

每个 profile 限额计的是**同时执行的不同 job**；同一来源同阶段不得双执行。模型任务占用 model+total，解析任务占用 parser+total；排队不占资源槽，commit 有独立唯一 actor。最终是否用 P2/P2M/P4 取实测和审查结论。

## 3. Job DAG、身份与状态

### 3.1 每份文档的 DAG

```text
source manifest/scan（既有受控入口）
  → source.narrative_outline
  → source.narrative_select
  → source.narrative_summarize
  → source.narrative_verify
  → source.narrative_publish
```

新增 `source.narrative_*` handler 必须在 `automation/registry.py`、SourceOnlyStage 白名单、输入/结果 schema 和预算 policy 中显式登记；不得让旧 `source.analyze` 泛化为研究 writer。`outline` 必须直接按只读 raw 做全页廉价文本/质量扫描与页级目录，候选页再做表格/问答深解析；对未入选页按冻结抽样审计漏收。现存且 SHA/版本有效的 normalized artifact 可作为**可选只读缓存**，不得为了本 DAG 调用旧 `source.normalize`/`normalize_catalog`，也不得直接复用会因表格 bbox 相交而丢正文块的旧快照结果。旧路径会物化整份 `normalized.md` 并删除重建全部 `evidence_spans`，与选择性切片和空间目标冲突。新 DAG 的正负例都要断言没有新增旧全量 normalized/spans；selected locator 仍须回读 raw。一个文档的 `select` 输出 `selected`，或在全篇覆盖已核实完整时输出 `skipped_no_narrative/skipped_event_notice`；这些均为**成功的阶段结果**。若候选页不可读、OCR/表格不透明或扫描缺口越门槛，进入 `needs_review`/合法阻断态，不能用成功 skip 消化失败。`summarize` 对合格 skip 输出 `summary_not_needed`，`verify/publish` 仍登记覆盖账本，避免依赖 job 永久悬空。Source retired/新版替代时取消未完成下游 job，并产生撤回事件。不同文档的 DAG 可交错；同文档当前阶段未有可见且有效的阶段产物不能 claim 下游。

**下游放行门禁**：DAG 可预建 `job_dependencies`，但除首个 outline 外，下游初始为 `PLANNED`。前置 AUTO job `succeeded` 只是必要条件；catalog 对应版本包 `visible`、hash/role/来源当前有效且覆盖账本完整后，coordinator 才在 AUTO 事务内把下游升到 `READY`。AUTO finish 与 catalog activate 之间，下游保持 `PLANNED`；崩溃后 reconciler 先 activate 再补 READY。skip 路径也先发布可见的 coverage/skip 包，才可升后续阶段。claim 仅从 READY 取任务；子进程开始和 writer 提交前再次核上游包与来源，以覆盖两库检查之间的状态变化。来源退休时，`PLANNED/READY` 可按既有状态机取消；已运行 attempt 须先撤销租约并依合法状态转为阻断/死信，禁止绕过状态机直接改 `CANCELLED`，已发布版本另走撤回。不能把 `job_dependencies.required_status=succeeded` 单独当作可执行门禁。

### 3.2 稳定身份

遵守 `automation.models.make_job_key(job_type, subject_type, subject_id, input_hash, policy_version, handler_version)`。`subject_type='source'`，`subject_id=source_id`。`input_hash` 是以下 canonical JSON 的 SHA-256：`source_sha256, document_id, document_kind, stage, upstream_artifact_hashes, parser_version, selector_version, summary_policy_version, prompt_hash, model_id, config_hash, locator_schema_version`；无关字段按 stage 固定空值而非省略。W0 冻结 canonical 排序/编码、模型与提示词身份；任一实质变化产生新 job key，不能复用旧结果。job 仍引用触发 `event_id`，不以文件路径作为身份。

### 3.3 当前 AutomationStore 基线与 E5 缺口

E4 已实现原子 claim/finish 与基础 outbox，不得再按旧草案重做 API：

| 当前 API | 已有保证 | E5 要补的内容 |
|---|---|---|
| `claim_next_ready(...)` | 一个 AUTO 事务领取 job、创建下一 attempt/token 并应用 runtime generation | E5 不改；E7 才讨论多文档进程数 |
| `heartbeat_attempt(...)` / `reap_expired_attempts(...)` | 最新租约及 generation fencing；过期 attempt 回收 | E5 不改 |
| `finish_attempt(...)` | 一个 AUTO 事务保存 attempt `result_json`、effect 与 pending outbox；有 effect 时 job 进入 `VERIFYING` | 增加按 effect 精确读取该 attempt 结果的只读 API；不能重跑 handler/LLM |
| `claim_next_outbox(...)` / `ack_outbox(...)` / `retry_outbox(...)` | outbox lease、generation、intended/actual hash 与终态更新 | claim 增加可选 effect-type filter；新增只处理 `narrative_bundle.publish` 的 dispatcher/reconciler |

CodeGraph 与现有调用图确认 `claim_next_outbox` 当前只有测试调用者，没有生产分发器；outbox payload 只序列化 Effect，不含 bundle 正文。E5 必须补 `result_for_effect(effect_id)` 的唯一性/完整性检查和窄 dispatcher，否则 job 会停留在 `VERIFYING`。其余 claim/lease/reap 测试已覆盖，不重复造队列，不在本阶段启用生产 Worker。并发阶段 E7 只协调多个文档 job，不让同一份文档跨进程并行；每个进程自建非线程安全 `LLMClient`，catalog 投影始终单 writer。

## 4. 两个数据库与文件的提交协议

AUTO DB 是 job/attempt/effect 真相源，catalog DB 是来源和叙述产物真相源；SQLite 的两个 WAL 数据库不承诺跨库原子事务。使用以下**可重放 saga**，每个步骤有确定性 key：

1. **AUTO handler finish**：`NarrativeVerifyHandler` 已在 locator 全回放后把严格 `NarrativeBundle` 放入 `HandlerResult.result` 并发出一个 effect。现有 `AutomationStore.finish_attempt` 在一个 AUTO 事务中保存 attempt result、pending effect 与 pending outbox，job 留在 `VERIFYING`；此时 bundle 尚不可读。
2. **读取已保存结果**：唯一 narrative outbox dispatcher 以 generation-fenced lease 只 claim `narrative_bundle.publish`；从该 effect 的已结束 attempt 精确读回 bundle。校验 effect id/job id、strict bundle schema、大小限制及 canonical bundle SHA=`intended_after_hash`。缺失/重复/不匹配拒绝，不调用模型；失败使用现有有界 outbox retry/dead-letter。
3. **内容寻址写入**：storage adapter 在 catalog lock 外把 canonical JSON 写到 `.source_catalog/objects/sha256/{prefix}/{sha}.json`，目标卷临时文件 fsync 后原子 rename；同 SHA 复用前重验 hash，异内容不覆盖。该 adapter 是唯一知道物理目录的层。
4. **catalog prepare**：automation 层 projector 持 `CatalogOperationLock` 只执行短检查/事务：重读当前 worker generation、source active/primary/source SHA 与 read policy；有效时调用下层 source_catalog repository，在 catalog `BEGIN IMMEDIATE` 插入 `narrative_artifact_versions(status='prepared')`。prepared 不进入普通 reader，也不写旧 `evidence_spans`。同 work_key+hash 幂等；同 work_key 异 hash fail closed。具体列、索引及 additive migration 唯一以 [Phase E §3.4/E5](phase_e_m3_worker_implementation_spec_2026-09-28.md) 为准，必须含 `effect_id` 与不含物理路径的 `object_key`。
5. **AUTO ACK 与 catalog activate**：prepare commit 后 `ack_outbox` 校验 intended/actual hash，在 AUTO 事务把 effect verified、outbox delivered、job succeeded。随后 automation 层 projector 再持短 catalog lock重验当前 generation、source 身份/策略和 AUTO verified effect，把同一版本切成 `visible`。pause 或进程退出可在中间留下 prepared；没有 `visible` 状态绝不能对下游呈现成功内容。
6. **可重放恢复**：outbox lease 未 ACK 就退出时，租约到期后再次 claim 会复用已落盘对象与同 prepared 行并 ACK；ACK 后、activate 前退出时，reconcile 按唯一 `effect_id` 找 prepared 行，确认 AUTO effect 已 verified 后 activate。generation/source 变更时旧 generation 不得提交；来源已 retired/不是当前 primary 记 `retired`，SHA/schema/身份/read-policy 冲突记 `quarantined`。这些状态都不可读；冲突直接产生机器可诊断的 retry/terminal error，不建人工审批队列。

`narrative_artifact_versions` 的唯一 DDL/状态枚举见 Phase E §3.4（必须为 additive `CREATE TABLE IF NOT EXISTS`，不重建旧 `artifacts/evidence_spans`）。只读 `automation.NarrativeArtifactReader` 只列/打开 visible 行，经 source_catalog object adapter 重验 object SHA/size、bundle schema 与当前 source SHA，返回已验证 bytes 和 source/hash/locator/quality，不返回物理路径。source_catalog repository 不导入 automation 类型；catalog `artifacts` v1 继续服务旧消费者，不在此迁移中删/改历史行。

若 package 的 selected EvidenceSpan 和摘要不能在同一个内容寻址文件/原子版本包中一起验证，N4 必须先改接口；不能先发布摘要再补定位。新表是版本化产物索引，不是第三套任务队列；清理历史 spans 仍归 W7 独立迁移。

`skipped_*` 只关闭本来源的业务切片/摘要依赖链，不能成为删除 raw 的 Worker handler。Worker 可以为[原文处置 D0–D5](raw_disposition_plan.md)生成可审计候选及覆盖证据；独立的单执行者在冻结候选清单、消费者状态和精确路径经复核后才处理物理删除。同 SHA 正在解析、验证、导出或被旧证据引用时不得进入 D4；删除 intent/receipt 的重放与本 DAG 的重试账本分别对账。

## 5. Pause/stop 的线性化与旧入口隔离

现有 `WorkerController.pause()` 先写 `worker_control.json` 再 stop，生产入口仍需保留。新协调器还需要 AUTO DB v2 中单行**运行门禁**（不是任务队列）；v1→v2 的显式迁移需备份、schema 指纹、旧 v1 拒绝未知字段测试。最低形状为 `runtime_gate(singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1), desired_state TEXT CHECK(desired_state IN ('paused','enabled')), control_generation INTEGER NOT NULL CHECK(control_generation>=0), updated_at TEXT NOT NULL)`，迁移默认 `paused`。新 claim/finish 必须在各自 AUTO 事务里检查它。

`WorkerController.pause`、新 job claim 和 catalog prepare/activate 共用一个短时跨进程提交互斥锁：pause 获取锁→写 AUTO `paused + generation+1`→写 legacy JSON paused→释放锁→停止子进程；claim/commit 获取同锁并重查 AUTO gate、legacy JSON、generation/token。这样 pause 成功返回后，旧代际不能再领取或发布产物。任一步失败，AUTO gate/legacy JSON 有一方 paused 或不可读即 fail closed，不能自动回 enabled；恢复只能走 v5 的精确授权与双状态核查。共享锁持有时间必须由 R4 C07 隔离测量并设上限，不能在锁内跑解析/LLM。AUTO job 已 succeeded 但 catalog 尚 prepared 时，查询返回 `pending_publication`，不能假报已可消费。

安全前置：旧 `run_cycle` 有 `prune_retired_evidence(..., apply=True)` 可达路径。R4 D01/D02/H01 的“安全修复或独立证明硬禁用”未通过前，不能使新/旧 Worker 真正运行；即使并发任务本身通过测试也不例外。初始 feature flag 默认 `off`，配置缺失/未知/错误时 fail closed，不能让登录脚本或旧 supervisor 因新增代码自动拉起新协调器。

## 6. 任务调度、限流和背压

- **优先级**：filing-fetch/下游显式需求 > 新到来源 > 旧库回填；同级按创建时间，按公司/类型做轮转，防止一份 429 页招股书或单公司堵住队列。只有 DAG 前置 accepted 的 job 可入 ready。
- **资源槽**：三个 semaphore：parser、model、total；catalog writer 固定 1。LLM 供应商/模型共享 token/费用预算使用经 v5/R4 验收的**同一持久 request ledger/预算服务**原子预留；模型未知计费占用保留，人工或 provider 事实核清后结算。`429` 触发全供应商冷却而非每进程各自猛重试。该统一接口未就绪时只做 replay 仿真，真实模型并发不得放行。
- **内存/磁盘**：W0 测每类文档廉价全页扫描与候选页深解析各自的峰值 RSS、页数、暂存字节和漏收率；按可用 RAM、保留空间与最坏单件估算并发槽；不足时降槽或暂停该类型，不尝试靠更高并发提速。解析结果上限沿用现有 `parser_result_max_bytes` 并另测模型输入预算。若廉价扫描漏掉业务表/问答的概率越 W0 门槛，就扩大深解析窗口，不以牺牲召回换吞吐。
- **观察项**：每分钟记录 ready/running/retry_wait/dead_letter、最老按需任务年龄、每类 docs/h、阶段 p50/p95、claim/commit 锁等待、续租失败、孤儿文件、重复提交抑制、模型 token/费用/unknown、CPU/RSS、DB/WAL 与 temp 字节。日志只有 ID/hash/错误码/耗时，不落全文或密钥。

## 7. 故障注入：不能缺的 20 个断点

测试使用临时 AUTO DB、临时 catalog DB、临时 raw、固定时钟、假 LLM/下载器，Windows 真子进程测试另跑。每个断点记录 `job/attempt/effect/outbox` 行、catalog 行与文件 hash，**不是只断言函数返回值**。

| ID | 注入点 | 必须观察 |
|---|---|---|
| F01 | ready 查询后两个执行者同时 claim | 一个 token 获得 job，另一个无 claim；attempt_no 不重复 |
| F02 | claim 提交后派发消息丢失 | lease 到期重领，原 job_key 不新增逻辑 job |
| F03 | 子进程启动前/解析中强杀父进程 | Windows 子孙回收；lease 到期可恢复，raw 无变 |
| F04 | LLM 已发请求但响应丢失 | usage unknown 记账，预算不被无界重发；结果不假成功 |
| F05 | 心跳丢失且慢执行者随后返回 | 新 token 接管；旧 token 被 fencing 拒绝 |
| F06 | 结果写临时文件中断/截断 | hash/size 不符拒提交、可重算 |
| F07 | 结果 fsync 后、effect prepare 前崩溃 | temp 可复用或重算，无可见产物 |
| F08 | effect pending 后、内容寻址 rename 前崩溃 | 对账重试，不重复模型调用若可信文件仍在 |
| F09 | rename 后、catalog BEGIN 前崩溃 | 孤儿内容文件可复用；catalog 不误显示已完成 |
| F10 | catalog 事务中间掉电/异常 | narrative 版本索引与同事务投影一起回滚；AUTO pending 可重试，prepared 不外露 |
| F11 | catalog prepared COMMIT 后、AUTO finish 前崩溃 | prepared 不可见；对账以 work_key+hash 补 finish/activate，不重跑模型 |
| F12 | AUTO finish 后、catalog activate 前或 outbox 发送/ACK 丢失 | 未 activate 不发送；对账补 activate，再重放 outbox；消费者按 package ID/hash 去重 |
| F13 | pause 与 claim/commit 三个交错点竞争 | pause 返回后无新 claim/产物提交；旧 token 无效 |
| F14 | source 在计算后 retired/换主源 SHA | commit 拒绝旧候选，触发撤回/新 job |
| F15 | SQLite busy、磁盘满、Windows rename PermissionError | 不把 job 记成功；有界重试/停止，原文与旧包可读 |
| F16 | 同 job_key 不同结果 hash/无源句/错误 speaker | 自动拒绝当前候选并记录原因，绝不覆盖第一 accepted 包；不建立人工 review 队列 |
| F17 | AUTO finish 后、catalog activate 前协调器尝试放行下游 | 下游保持 PLANNED，零 claim/零网络；activate 后才 READY，重启漏升可补 |
| F18 | AUTO finish 后、activate 前来源退休/换 SHA | prepared 进入 quarantined，outbox 撤回，下游保持不可运行；已运行租约按状态机封存 |
| F19 | Windows temp/raw 路径检查后被 junction/symlink/reparse 替换 | 句柄身份或组件检查拒绝提交；不得写出受控根，也不将 job 标成功 |
| F20 | temp 与目标跨卷或 rename 中断 | 目标卷暂存复制、flush、hash 重验后才原子 rename；失败无可见包和残缺正式文件 |

G3 集中运行 F01–F20：每个断点先有一次可复现的确定性注入，不能因测试数量减少而删失效模式；F01/F03/F05/F11–F13/F17–F20 这些依赖调度或 Windows 文件系统的竞争点，再用真实进程重复 3 次，并跑一轮至少 100 个混合 job 的有界中断/重启负载。每次恢复断言最终状态为成功、可恢复重试或明确 dead_letter；无永久 `leased/running` 悬挂；原始文件和旧 v1 导出未变；同 work_key 的 accepted 计数 ≤1。失败只修复并复测相应断点及直接依赖，不重跑所有 20 项十遍。

## 8. 吞吐试验与放行门槛

**样本**：使用本专题 12 件探索集检查已知问题；另用 W0 冻结的至少 36 件留出集做盲测。性能样本需覆盖短季报/IR/TXT、长年报/招股/再融资、负例，固定 manifest SHA。不能以单个 429 页 PDF 推断整体吞吐，也不能把首次缓存预热与多次复用混比。

**实验**：同一机器、电源模式、Python/SQLite/模型和输入预算；G3 先测 P1 与 P2 各 2 轮且交错顺序，只有 P2 达标才测 P2M/P4 各 2 轮。记录原始每文档开始/完成时间、阶段时长/队列等待、token/费用、峰值 RSS、CPU、磁盘、锁等待和失败；波动导致结论不稳时仅为相邻候选追加一轮。P2M/P4 的真实模型请求必须先有统一预算接口。远程模型速率/费用波动不可控时先用可重放的延迟/429 仿真比较调度能力，再在**明确允许外发**的有限真实 cohort 复测；仿真结果不能当真实生产提速。

N5 必须交付 `scripts/benchmark_narrative_parallel.py`（或经 W0 固定的同等入口），显式参数 `--fixture-manifest`、`--scratch-root`、`--total-inflight {1,2,4}`、`--model-mode replay|live`、`--round-id`、`--output-json`。在导入任何生产配置/打开 DB 前验证：scratch/root/output 的 resolved path 位于隔离根、fixture manifest SHA 对应 W0 冻结值。`replay` 为默认；`live` 需要命令行显式选择，并配置单轮费用上限和文档数上限。用户已授权来源内容外发，不再要求重复的授权 receipt。输出 JSON 至少含每 job 时间线、三类资源槽占用、成功/重试/死信、accepted package ID/hash、token/费用、每阶段 RSS/锁等待/磁盘占用、fixture 与代码 SHA。以同一分析脚本计算吞吐和 p95，不手工摘最佳轮。

**建议预先固定的自动判据**（以下是设计目标，**不是已测结果**）：

- F01–F20 全过；13 张探索卡全过；盲测质量不低于 W0 冻结的召回/精确率/locator 门槛；0 个 P0/P1，0 个重复 accepted artifact，0 个暂停后提交或未 visible 提前导出；新 DAG 不新增长期全量 normalized/spans。
- 在同等质量/输入下，P2 或 P2M 相对 P1 的完成文档/小时至少提高 **25%**；P4 仅在相对最佳 2 在途 profile 再提高至少 **15%** 且锁等待/峰值内存/失败不越预算时启用。达不到即采用更低并发，不把“开多进程”本身视为完成。
- 同批文档的 LLM token/可归因费用较单执行者最多增加 **5%**；未知收费单列且不能被排除在预算之外。按需任务 p95 完成时间与排队时龄不得越 W0 冻结的消费方时限；磁盘剩余和最坏暂存必须大于 W0 的安全保留量。
- F03/F11/F13 等竞争恢复已按 §7 真进程 3 轮通过；再用一轮至少 100 个混合 job、30–60 分钟的有界隔离负载覆盖重启、429、失败重试和磁盘增长，没有 stuck lease、孤儿子进程或无限重试。本专题不额外要求 72 小时隔离 soak；若 v5/R4 当时正式生产门禁要求更长观察，直接遵守或复用其同版本通过收据。

阈值按当前实现前已知预算固定在配置中，不能看到测试结果后再改。样本不足或真实 provider/费用不可用时，自动报告未覆盖项并保持该能力关闭；不要求人工签字，也不能把未测项目描述为已验证。

## 9. 分卡实施顺序与可运行测试入口

| 卡/依赖 | 精确产物与建议落点 | 最小测试和停止点 |
|---|---|---|
| N0 契约与基线（W0、R4 C05/C07 当前状态） | 只读盘点 AUTO DB 是否配置、v5/H01 状态、catalog artifact identity；冻结 DAG、input_hash schema、阈值、fixture。仅改本计划/临时测试记录 | 任何 owner/接口已变化时重审映射；不得写生产 DB |
| N1 AUTO 原子 job（N0；交给 R4 C05） | `automation/store.py,worker.py,models.py,migrations.py`：claim/heartbeat/finish/reap 同事务、token fencing、outbox；向后兼容旧 job | `tests/unit/test_automation_{store,worker,migrations}.py` + F01/F02/F05/F12；未通过不得接 source handler |
| N2 受控进程/暂停（N1；v5/R4 D） | `source_catalog/control.py,worker.py,normalizer.py` 与新 coordinator：Windows 子进程、共享提交锁、运行 gate、default-off 配置；prune 危险入口先关闭 | 既有 control/parser/operation-lock 合同测试 + F03/F13；H01 未关时只能 temp |
| N3 叙述 DAG 与只读计算（N1/N2、W1–W4） | `automation/registry.py,planner.py` 和独立 source handler；PDF/TXT 结构、选择、摘要、验证只在 temp 产物；不自动触发旧全量 normalize | 13 卡、盲测合同、F04/F06/F07/F16/F17；LLM 独立进程，共享预算 |
| N4 catalog writer/对账（N2/N3；R4 C07） | 新 `narrative_artifact_versions` 索引、commit actor/reconciler、版本化包输出；旧 `artifacts` 不重建；visible 后才升下游 READY | F08–F11/F14/F15/F18–F20、跨库恢复与旧 v1 消费回归；任一 accepted 产物无 locator 即阻断 |
| N5 并发试验（N4） | temp benchmark harness、数据与图表、1/2/4 配置收据；先仿真后有限真实 provider | §8 全部质量/效率/成本判据；未达保留单执行者 |
| N6 灰度/回退（N5 + v5/R4 技术不变量） | bounded cohort、一个本地运行配置、指标/回滚说明；不改其他仓库数据库 | 1→3→7 文档按 R4 C09 自动扩大 cohort；G3 一次集中验收、每批由指标自动决定继续/降并发/暂停；不逐批人工签名，其他计划若有更高层系统边界仍适用 |

测试命令以未来实现后的具体文件名为准，先用已有隔离单测基线：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$testRoot = Join-Path $env:LOCALAPPDATA 'Temp\cw-pytest-basetemp'
$caseBase = Join-Path $testRoot ('narrative-plan-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $caseBase) { throw 'temporary test path already exists' }
python -m pytest -p no:cacheprovider -q --basetemp $caseBase tests/unit/test_automation_store.py tests/unit/test_automation_worker.py tests/unit/test_automation_migrations.py
$caseBase = Join-Path $testRoot ('narrative-plan-' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $caseBase) { throw 'temporary test path already exists' }
python -m pytest -p no:cacheprovider -q --basetemp $caseBase tests/contract/test_source_catalog_operation_lock.py tests/contract/test_source_catalog_parser_liveness.py tests/contract/test_source_catalog_worker.py tests/contract/test_source_catalog_ensure_paused_guard.py
```

新故障/吞吐测试必须通过 `tmp_path` 注入两个临时 DB 与 raw 根；测试入口在打开数据库或启动子进程前先 assert resolved path 不在生产 `.source_catalog`/真实 `companies/`，且当控制状态 paused 时不得启动生产服务。Windows 默认 `%TEMP%` 在当前沙箱可能拒绝创建 pytest 临时根：若出现 basetemp PermissionError，指定**经 resolved-path 验证**的隔离 `--basetemp`，不能将权限故障记成代码失败。2026-09-26 的只读基线复测：首次默认路径 9 passed/61 setup errors；显式隔离 basetemp 后 **70 passed**。G3 集中记录关键命令、退出码、版本、故障/吞吐结果；审查者抽跑一个 claim 竞争、一个跨库恢复、一个暂停竞争与一次 2 在途 benchmark，不逐卡另起完整测试。

## 10. 最小运营手册与回退

1. `status` 只读展示 feature flag、双暂停 gate、进程数、job 各状态、最老年龄、当前租约与预算、最近 24h 失败、catalog/temporary 文件字节。健康检查不可触发迁移或下载。
2. `pause` 必须先 fence 新 claim/commit 再停止子进程；在途 job 到期后由下一次**经授权**运行对账，不因暂停自动重启。`drain` 不领取新 job，待有界时间后把未完任务留持久状态。
3. `recover --dry-run` 在离线 temp/隔离副本列待补 finish、待重试、孤儿文件和冲突。正式 `recover` 按持久账本确定性重放可安全恢复的任务并输出汇总；身份/hash 冲突自动保持不可见并给出可读错误，不需要逐 job 人工批准。不能直接删除 lock、WAL、attempt 或旧 artifact 来“解卡”。
4. 并发异常先把 `max_total_inflight` 降为 1 或关闭新 route，等待已有提交完成/暂停；已 accepted 的版本包按撤回合同处理。原文、attempt/effect 历史与旧 v1 导出不可回滚删除。生产 Worker 的启动/恢复使用同一配置运行档及 v5/R4 技术不变量，不对每个 job 重复索要用户批准。
