# Phase E / M3：多文档并发 Worker 详细施工卡（2026-09-28）

> **状态：实施前冻结稿。** 本文件先于任何 Phase E 产品代码提交。只有本卡单独提交、工作树可解释后，才按本文顺序进入 TDD 实施。
>
> **生产边界：** Phase E 不启动生产 Worker，不扫描生产目录，不删除 raw，不真实调用付费 LLM，不修改 revenue-forecast、filing-fetch、StockWiki 或 earnings-transcripts。所有写入型测试只使用经校验的 `C:\cwt\m3-*` 独立根，测试结束在 `finally` 中恢复原状。

## 1. 本阶段解决什么

Phase E 把已经完成的来源读取、叙述证据选择和电话会议材料接入一个真正可恢复的多文档执行系统：

1. 不同文档可以并发；同一来源的 `select → summarize → verify/publish` 必须有序。
2. 领取、心跳、完成、Effect、Outbox 必须有原子事务和 lease token fencing。
3. 进程被杀、消息丢失、ACK 丢失、锁冲突、暂停或来源发生变化后，都能重试或明确终止，不能永久卡在 `leased/running/verifying`。
4. `LLMClient` 不在线程或进程之间共享；模型并发首版固定为 1。
5. 叙述流程直接从 `SourceVersionReader` 打开的已校验 raw 读取，不调用旧的全量 `normalize_catalog`，不为整份报告生成 Markdown 和全量切片。
6. 低价值文档也要留下小型 coverage/skip 收据，但不生成正文切片或摘要文件。
7. 最终只保存一份紧凑、内容寻址、可按 locator 回放的 narrative bundle；中间结果有大小上限，不建立第二套全文索引。

本阶段不启用物理清理。raw 处置和旧派生清理仍属于 Phase G。

## 2. 调查得到的当前事实

### 2.1 两套 Worker 必须分开处理

- `src/company_wiki/automation/worker.py::Worker` 是新的 job/attempt Worker，但目前仍是单执行者骨架。
- `src/company_wiki/source_catalog/worker.py::SourceCatalogWorker` 是旧的顺序批处理器，一次 cycle 串行执行 scan、normalize、fingerprint、sections、LLM summary、export，并且每周会调用 `prune_retired_evidence(..., apply=True)`。
- Phase E 的并发只建立在 `automation/` 之上。旧 Worker 保持 paused，只做安全收口和兼容状态查询，不作为并发执行内核。

### 2.2 现有 AutomationStore 不能安全并发

已在真实代码中确认：

1. `_try_claim()` 分三次事务完成 `READY→LEASED`、插入 attempt、`LEASED→RUNNING`，中途失败会留下半领取状态。
2. attempt 完成时重新调用 insert-only 的 `put_attempt()`；完成字段与旧行不同会冲突，异常又被吞掉，所以 attempt 实际仍是未完成状态。
3. 成功路径没有先插入 `Effect`，却直接插入引用它的 Outbox；有 effect 的结果会违反外键。
4. attempt、job 状态、effect 和 outbox 分开提交，无法证明“job 成功”和“副作用待投递”一致。
5. 没有 heartbeat 更新 API，没有验证“当前 attempt 是该 job 最新 attempt”的 fencing，也没有 pause generation。
6. `reap_expired()` 通过多次 list/transition 完成，旧执行者返回后仍可能覆盖新 attempt。
7. `Controller.shadow()` 只插入 `DETECTED` job，未落 `job_dependencies`，也没有正式的 DAG materialize/promote 路径。
8. Outbox 只有 CRUD，没有原子 claim、lease、ack、retry dispatcher。

因此实施顺序必须是“状态机原子性 → 暂停 fencing → 进程并发 → narrative handler → catalog projector”。禁止先加线程或进程再补事务。

### 2.3 现有测试为什么全绿仍漏掉缺陷

`tests/unit/test_automation_worker.py` 的 happy path 只断言 job 最终为 `SUCCEEDED`，没有断言：

- attempt 的 `finished_at/outcome/result_json` 已持久化；
- effect 与 outbox 同时存在；
- 两个 store/两个进程只能有一个 claim；
- 旧 token 在重领后不能 heartbeat/finish；
- pause 后旧 generation 不能提交；
- catalog 已提交但 ACK 丢失时可以幂等恢复。

Phase E 先写这些 RED 测试，再重构实现。

### 2.4 当前基线并非全绿，但属于测试夹具陈旧

2026-09-28 在独立 `C:\cwt\m3-plan-baseline-*` 根运行 150 项现有测试：`145 passed, 5 failed`。五项都在 `tests/contract/test_source_catalog_worker.py::_review_all()`，原因是生产 `record_prompt_injection_review()` 已要求 `evidence_payload` 与 `evidence_sha256` 绑定，而旧 helper 仍只传 hash。生产拒绝是正确的 fail-closed 行为；不能放松生产合同。

E0 只修测试 helper：按已通过的 GP-003 测试形状传入与 hash 相同的 `evidence_payload`。同类陈旧 helper `tests/contract/test_source_catalog_focus_admission.py::_review_documents()` 一并修正。缺 payload 必须继续被生产代码拒绝。

测试临时根已清理，`m3_plan_baseline_roots=0`。

### 2.5 复杂度基线

定向 `ruff --select C901` 当前报告 11 个既有超限点，其中旧 `SourceCatalogWorker.run_cycle` 为 34。Phase E 不把这些旧函数继续扩张：

- 新增函数圈复杂度必须 `<=10`；
- 新 AutomationStore 原子操作拆为短事务 helper；
- 新 Supervisor、Projector、handler 不导入旧 `run_cycle`；
- 旧高复杂度列表作为冻结基线，不允许新增或升高。

### 2.6 当前生产暂停和跨仓边界

- `.source_catalog/worker_control.json` 当前为 `desired_state=paused`，且没有 `worker_runtime.json`。
- revenue-forecast 只读核查仍为 `fcap@ee0a82bfd`，`origin/main@3a69f9c5`，其 planning/assurance 工作树有既存未提交内容。Phase E 不读取其可变结果作为写入输入，不修改、不清理、不切分支。
- Phase E 复用 company-wiki 已完成的 `SourceVersionReader`、narrative selector、summary draft validator 和 locator replay；不复制 revenue-forecast 的 source 解析逻辑。

## 3. 冻结的架构决定

### 3.1 进程拓扑

```text
AutomationScheduler
        │  materialize deterministic DAG
        ▼
AutomationStore (SQLite/WAL, single durable queue)
        │
        ├── compute workers (spawn processes): select / verify
        ├── model worker   (one spawn process): summarize
        └── outbox projector (one process): publish compact bundle
                                      │
                                      ▼
                         Source Catalog + content-addressed object
```

- 不增加第三套 queue。
- Windows 一律使用 `multiprocessing` 的 `spawn` 语义；不能依赖 fork 继承状态。
- 每个进程自己构造 AutomationStore、SourceCatalog 和需要的 client。
- LLM client 只存在于 model worker 的主线程。
- 每个执行进程允许一个仅负责 AutomationStore heartbeat 的短线程；该线程不得接触 LLM、parser 或 catalog writer。
- projector 单执行者，catalog transaction 和跨进程 commit lock 内不做 PDF 解析或 LLM 调用。

首版 profile：

| profile | 同时在途 | compute | model | projector | 用途 |
|---|---:|---:|---:|---:|---|
| P1 | 1 | 1 个 mixed worker | 同一 worker | 1 | 可靠性/耗时基线 |
| P2 | 2 | 1 | 1 | 1 | 默认候选；让下一文档选择与上一文档摘要重叠 |
| P4 | 4 | 3 | 1 | 1 | 只做隔离压测；达到门槛才建议启用 |

生产推荐初值只能来自 Phase E benchmark；没有证据时保持 P1。Phase E 不把任何 profile 写成生产 enabled。

### 3.2 每份文档只有三个业务 job

```text
source.narrative_select
          ↓
source.narrative_summarize
          ↓
source.narrative_verify
          ↓ effect/outbox
single catalog projector
```

不再预建 outline、publish 等额外 job：

- `select` 内部使用 Phase C 已拆分的小模块完成 cheap structure scan、候选形成、预算和最终选择。
- `summarize` 只接收 `summary_scope=selected_evidence_only`；skip 输入返回 `summary_not_needed`，不调用模型。
- `verify` 校验 draft/source/language/evidence IDs，重新从 raw 回放 locators，生成唯一最终 bundle 和 publish effect。
- publication 是 effect projector 的职责，不是第四个业务 job。这样 ACK 丢失不会重跑 LLM。

三个 job 在 event 到来时一次性、确定性创建，下游初始为 `PLANNED`。前置 job `SUCCEEDED` 且 dependency result 可读后，scheduler 才把下游升为 `READY`。

### 3.3 中间结果与最终结果的存储

**中间结果：**

- `select` 和 `summarize` 的 canonical JSON 写入 attempt `result_json`。
- finish 时保存完整 `HandlerResult`，包含 result、artifact refs、effects、metrics 和 error，不再只保存 `result` 字段。
- `select` 结果最大 1 MiB；summary 最大 64 KiB；超过上限为 `RESULT_TOO_LARGE`，不能截断后假成功。
- skip 收据通常小于 8 KiB。

**最终结果：**

- `verify` 只生成一个 canonical JSON narrative bundle，包含选中 EvidenceSpan、summary draft、selection/coverage 状态、parser/selector/prompt/policy 版本、raw source identity 和 replay contract。
- 文件写入 `.source_catalog/objects/sha256/{prefix}/{content_sha256}.json`；catalog 内只存相对 `object_key`，对外接口不返回物理路径。
- 同内容 hash 复用；不再额外生成 `normalized.md`、`summary.md`、逐页 JSON 或持久化全文 BM25 索引。
- skipped 文档只写最小 coverage bundle，不含全文或空数组膨胀。

### 3.4 为什么保留独立的 narrative artifact version 表

现有 `artifacts` 的唯一约束是 `(document_id, artifact_role, generator_name, generator_version)`；同一 document 的新 source revision 或同版本重算会更新旧行。它适合 legacy current projection，不能证明不可变 narrative 版本历史。

Phase E 新增一个窄表 `narrative_artifact_versions`，不增加 generic head 表，也不复制旧 `artifacts`：

```sql
CREATE TABLE narrative_artifact_versions (
  artifact_version_id TEXT PRIMARY KEY,
  work_key TEXT NOT NULL UNIQUE,
  effect_id TEXT NOT NULL UNIQUE,
  document_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  artifact_role TEXT NOT NULL CHECK(artifact_role='narrative_bundle'),
  object_key TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  byte_size INTEGER NOT NULL CHECK(byte_size>=0),
  producer_name TEXT NOT NULL,
  producer_version TEXT NOT NULL,
  policy_sha256 TEXT NOT NULL,
  selection_status TEXT NOT NULL,
  quality_status TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('prepared','visible','retired','quarantined')),
  created_at TEXT NOT NULL,
  activated_at TEXT,
  FOREIGN KEY(document_id) REFERENCES documents(document_id),
  FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
```

这是 E5 唯一正式表形状：`object_key` 是逻辑键，绝不存物理路径；`effect_id` 让跨 AUTO/catalog 数据库的恢复器能找到对应发布结果。`work_key` 绑定 `document_id + source_id + source_sha256 + artifact_role + producer/version + policy_sha256`。同 work_key、同 content hash 是幂等重放；同 work_key、不同 hash 直接冲突并按自动重试/终态错误处理，不进入人工审查队列，不得 last-write-wins。

状态只允许：`prepared`（对象和 catalog 已登记、尚不可读）、`visible`（自动来源/locator/包校验通过）、`retired`（来源已退休或不再是当前主来源）、`quarantined`（hash、schema 或身份冲突）。从 `prepared` 到 `visible` 的切换必须重验当前源。`visible` 只表示来源身份、解析/locator 和包完整性通过，不表示投资结论成立。E5 的表/索引为 additive DDL，不重建旧 `artifacts/evidence_spans`，也不改变 catalog schema version；初始化时所有已支持版本都须执行幂等 additive DDL。

### 3.5 Automation DB v2

显式 v1→v2 migration：

1. 保留 v1 DDL snapshot 和 v1 drift validator。
2. v0 新库按 v1、v2 顺序在一个 transaction 内创建。
3. v1 先做一次 backup，再在一个 `BEGIN IMMEDIATE` 内升级；失败 rollback，原库不被半升级。
4. v2 增加：
   - `attempts.runtime_generation INTEGER NOT NULL DEFAULT 0`；
   - `runtime_gate` 单行表；
   - claim/attempt/outbox 必要索引。
5. v2 seed 为 `paused, generation=1`。旧 attempt 的 generation=0，因此不能被新 Worker 误完成。
6. v2、未来更高版本、unknown/drift schema 继续 fail closed。

运行门形状：

```sql
CREATE TABLE runtime_gate (
  singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),
  desired_state TEXT NOT NULL CHECK(desired_state IN ('paused','enabled')),
  control_generation INTEGER NOT NULL CHECK(control_generation>=1),
  updated_at TEXT NOT NULL
);
```

### 3.6 原子 Store API

Store 公开下列 application operations；Worker 不再自行拼多个 CRUD：

| API | 单事务必须完成的工作 |
|---|---|
| `materialize_dag(event, planned_dag)` | 幂等插入 jobs + dependencies；根 job 到 READY，下游留 PLANNED；不同内容同 job_key 冲突 |
| `promote_ready_jobs(now)` | 只把所有依赖已 SUCCEEDED、结果存在且 not_before 到期的 PLANNED/RETRY_WAIT job 升 READY |
| `claim_next_ready(...)` | 检查 gate=enabled/generation；按 priority/created/job_id 选一个满足依赖的 READY；创建下一 attempt；job 到 RUNNING；一次提交 |
| `heartbeat_attempt(...)` | token、generation、最新 attempt、unfinished、job RUNNING、gate enabled 全部匹配才续租 |
| `finish_attempt(...)` | fencing 后更新 attempt；无 effect 的 job 到最终状态；有 effect 时原子插 effect+outbox 并停在 VERIFYING |
| `reap_expired_attempts(now)` | 只处理最新且未完成的过期 attempt；写 `LEASE_EXPIRED`；按 attempt budget 重排或 dead-letter |
| `claim_next_outbox(...)` | 单条 pending/due outbox 原子租约；不重复给两个 projector |
| `ack_outbox(...)` | token/generation fencing；effect APPLIED/VERIFIED、outbox delivered、job VERIFYING→SUCCEEDED 一次提交 |
| `retry_outbox(...)` | 记录错误、attempt_count、not_before；超预算 effect FAILED、job DEAD_LETTER |
| `set_runtime_gate(...)` | 状态改变时 generation+1；读不到或非法时一律视为 paused |

Store busy、schema drift、token mismatch、generation mismatch 必须是具名错误；禁止 `except Exception: return None/pass`。

### 3.7 暂停的线性化边界

新 `AutomationWorkerController` 使用 `CatalogOperationLock` 形成短提交边界：

1. `pause` 获取 lock；AUTO gate 写 paused 并 generation+1；legacy JSON 写 paused；释放 lock；再停止子进程。
2. `enable` 只在 legacy worker 已 paused、无 live runtime、schema v2 健康时写 AUTO enabled；Phase E 测试只对临时根调用。
3. projector 获取同一 lock；在 lock 内重查 gate、generation、outbox token、source current/hash；再执行短 catalog transaction。
4. pause 返回后，旧 generation 不能 claim、heartbeat、finish 或 publish。
5. gate/legacy JSON 任一缺失、非法或不一致都 fail closed 为 paused。

旧 `WorkerController._read_control()` 的缺失/非法默认从 enabled 改为 paused。旧 `SourceCatalogWorker` 自动 prune 默认关闭；Phase E 不提供真实 apply 入口。

## 4. 详细 TDD 实施顺序

只在两个大节点做集中审查：E-A（事务与安全）和 E-B（完整 M3）。每一小步仍先写 RED 测试，但不为每个 helper 建人工复核点。

### E0：恢复可信基线

**先写/调整测试**

1. 修正两处陈旧 review helper，传入与 `evidence_sha256` 匹配的 `evidence_payload`。
2. 保留并运行“缺 payload 被拒绝”单元测试，证明没有放松生产 gate。
3. 新增一条 baseline assertion：旧 Worker 控制文件缺失/损坏时目标状态为 paused。

**验收**

- 本次 150 项 targeted baseline 全绿。
- production `record_prompt_injection_review()` 不改弱。
- production Worker 仍 paused、runtime 文件仍不存在。

### E1：Automation DB v2 和原子 Store

**RED 测试先行**

- v0→v2、v1→v2、v2 no-op、backup failure、DDL failure rollback、future/drift refusal。
- 两个独立 AutomationStore 同时 claim 一条 job：恰好一个成功、一个 attempt。
- claim 任意故障点 rollback 后 job/attempt 数量完全不变。
- attempt finish 字段真实更新，不再 insert-only 冲突。
- success+effects+outbox 或全部存在，或全部不存在。
- stale token、旧 generation、非最新 attempt、过期 lease 全部不能 heartbeat/finish。
- retry `not_before` 未到不能 claim；到期后只升一次 READY。
- reaper 与慢 Worker 竞争，慢 Worker 最终 finish 被拒绝。
- Outbox claim/ack/retry 同样做双 store race 和 token fencing。

**实现文件**

- `src/company_wiki/automation/migrations.py`
- `src/company_wiki/automation/models.py`
- `src/company_wiki/automation/store.py`
- `src/company_wiki/automation/worker.py`
- `src/company_wiki/automation/outbox.py`
- `tests/unit/test_automation_migrations.py`
- `tests/unit/test_automation_store.py`
- `tests/unit/test_automation_worker.py`
- 新 `tests/integration/test_automation_store_races.py`

**实现限制**

- 所有 transaction 在 Store 内部。
- handler 执行、sleep、PDF/LLM、文件 hash 不得在 SQLite transaction 中。
- store method 不导入 source_catalog、LLM 或 provider。

**E1 实施收据（2026-09-28）**

- v2 migration、runtime gate、attempt generation、claim indexes 和 v1 backup/rollback/drift 路径已实现；v1→v2 没有显式 backup hook 时 fail closed。
- claim、heartbeat、finish、promote、reap、outbox claim/ack/retry 已成为 Store 单事务 application operations；Worker 只负责编排与事务外 handler execution。
- RED 收据：首组 18 failed / 2 passed；Worker 4 failed / 13 passed；多 effect/hash 2 failed / 1 passed；实现后 automation 合并门为 193 passed。
- Store/Worker/migration 新改函数显式 C901 `<=10`；production control paused、runtime absent、测试根 0。E2/E-A 前未新增 Supervisor 或 narrative handler。

### E2：DAG materialization、依赖结果和运行门

**RED 测试先行**

- 同一 event materialize 两次只得到一组 jobs/deps。
- 不同 payload 复用同 job_key 必须冲突。
- 下游在前置成功前不能 READY；前置完成但 result_json 缺失也不能 READY。
- 前置 dead-letter/cancelled 时下游保持可解释的 blocked 诊断，不静默运行。
- paused/missing/corrupt gate 不能 claim。
- pause 与 claim/finish 并发时，以 lock 和 generation 得到线性结果。

**实现文件**

- 新 `src/company_wiki/automation/scheduler.py`
- 新 `src/company_wiki/automation/runtime_control.py`
- `src/company_wiki/automation/controller.py`
- `src/company_wiki/automation/planner.py`
- `src/company_wiki/source_catalog/control.py`（只做 fail-closed 默认和 legacy interlock）
- `src/company_wiki/source_catalog/worker.py`（只关闭自动 apply prune）

**E2 实施收据（2026-09-28）**

- 同一 event 重复 materialize 只保留一组 jobs/dependencies；event payload 或不可变 job 内容漂移复用 job key 时具名冲突，部分写入整体 rollback。
- root 初始 READY、downstream 初始 PLANNED；前置完成但无成功 result JSON 时不提升，cancelled/dead-letter 时下游写入可解释的 `DEPENDENCY_TERMINAL` blocked 诊断。
- runtime gate 缺失/损坏时 claim 失败关闭；pause 与 finish 的真实双线程竞争只产生“finish 先提交”或“pause 先 fencing”两种线性结果。
- AUTO/legacy 采用双向互斥：AUTO enable 先写 legacy `automation_enabled` 标记再开 DB gate；legacy `resume/start/open_session` 在同一 operation lock 下拒绝该标记；重复 enable 幂等；真实两类 controller 的临时根集成 **2 passed**。
- `dag_persistence.py` 只接收调用方 transaction connection，Store 继续独占 BEGIN/COMMIT；scheduler/controller 不执行 handler。旧 Worker 的自动 retired-evidence apply 已不可达，只保留确定性 dry-run 报告。

### 大节点 E-A：事务与安全审查

集中运行：

```powershell
python -m pytest -q -p no:cacheprovider --basetemp C:\cwt\m3-gate-a `
  tests/unit/test_automation_migrations.py `
  tests/unit/test_automation_store.py `
  tests/unit/test_automation_worker.py `
  tests/unit/test_automation_controller.py `
  tests/integration/test_automation_store_races.py `
  tests/contract/test_source_catalog_operation_lock.py `
  tests/contract/test_source_catalog_ensure_paused_guard.py
```

Gate 条件：原子性与 fencing 全绿；legacy 默认 paused；自动 destructive prune 不可达；无生产 DB/控制文件变化。通过后才写进程并发和 narrative handler。

**E-A 结果（2026-09-28）**

- 首轮集中门 227 passed 后，人工审查发现 legacy resume 仍可在 AUTO enable 之后单独启动；补双向 interlock 红测并修复后，最终集中门 **229 passed in 69.23s**。
- Ruff 全绿；新增/重构 automation 模块显式 C901 `<=10`；全部 automation 单测加 store boundary 回归另有 **195 passed in 19.14s**。旧 `control.py`/`worker.py` 的既存高复杂函数未扩大为并发内核。
- production `worker_control.json` 仍为 paused；`worker_runtime.json`、`automation.db`、`operation.lock` 均不存在；全部本轮 `C:/cwt/m3-e2-*` 与 `m3-gate-a*` 根已精确清理。
- E-A 已放行 E3；Supervisor、narrative handler、projector 和 production enable 仍未实现或启动。

### E3：Supervisor 与真正的多进程执行

**RED 测试先行**

- `spawn` 的两个子进程能并发处理两个不同 source；同 source 下游不越过依赖。
- 子进程在 claim 后、handler 中、finish 前被杀，lease 到期后可以恢复。
- heartbeat 活跃时 reaper 不抢占；heartbeat 停止后可重领。
- 父进程退出会终止/回收自己创建的子进程；重启 supervisor 后 DB job 可继续。
- P2 模式 model worker 永远不超过 1 个；compute worker 不持有或共享 LLMClient。
- 进程 stdout/stderr 有上限并落测试根，不能无限占盘。

**实现文件**

- 新 `src/company_wiki/automation/supervisor.py`
- 新 `src/company_wiki/automation/worker_process.py`
- 新 `src/company_wiki/automation/heartbeat.py`
- 新 `tests/integration/test_automation_multiprocess.py`

Supervisor 不使用内存 queue 保存唯一任务事实；进程退出后以 DB lease 恢复。

**E3 实施收据（2026-09-28）**

- 新增 `supervisor.py`、`worker_process.py`、`heartbeat.py`：Supervisor 只管理固定进程槽并周期执行 promote/reap；子进程按 importable factory 在 `spawn` 后自建 Store、registry、executor 和可选 model client，进程间不传 client 或内存任务队列。
- P1 为一个 mixed slot，P2 为一个 compute + 一个 model，P4 为三个 compute + 一个 model；所有 profile 最多一个可持有 model client 的 slot。compute 若持有 model client 或接收 `llm=True` job、model 若接收非 LLM job，均在 claim 前拒绝。
- Worker 新增显式 allowed job types、attempt heartbeat 和 lifecycle observation seam；heartbeat 线程只调用 Store lease API，handler 仍在主线程执行。另有一个不接触 Store、handler 或 LLM 的 parent watchdog，仅检查父进程存活；真实测试证明没有它时，父进程在 child 处于 handler 时被强杀会留下 orphan，因此该线程作为进程治理例外保留。
- 三个确定性强杀窗口（claim 后、handler 中、finish 前）均由 lease expiry → reap → 新 Supervisor/新 attempt 恢复；active heartbeat 防止误 reap，停止后可回收。父 Supervisor 自身被强杀时，处于 handler 的 child 会自退出。
- 子进程 stdout/stderr 是固定字节上限的 tail log，重启保留旧 tail 而不清空；Supervisor restart budget 有界，normal stop 先 signal/join，再只终止自己创建且仍存活的 child。
- 最终聚焦单元/真实进程测试 **29 passed in 13.79s**；全部 automation 单元、Store race、真实 multiprocess 与 store boundary 回归 **209 passed in 32.07s**。Ruff 通过，三个新边界模块 strict mypy 通过；全部 `C:/cwt/m3-e3-*` 根精确清理后 remaining=0。
- production legacy control 仍 paused；本阶段没有创建 production Automation DB/runtime，没有接 narrative handler、projector 或真实 LLM，也没有修改 raw/catalog/RF。

### E4：Narrative handlers

本节的逐字段合同、错误分类、TDD 次序和测试根清理细则由 [E4 Narrative handlers 详细实施规格](phase_e_e4_narrative_handler_implementation_spec_2026-09-28.md) 冻结。下方为阶段摘要；实施时如有歧义，以详细规格为准。详细规格明确取消重复持久化 `summary_input` 正文，只从 selected EvidenceSpans 临时构造模型输入，并且 transcript 只保留已选证据对应的原始 byte bindings。

**注册 job**

- `source.narrative_select`：`llm=False`，retryable `IO_TRANSIENT/STORE_BUSY/LEASE_LOST`，terminal `SOURCE_HASH_MISMATCH/POLICY_DENIED/RESULT_TOO_LARGE`。
- `source.narrative_summarize`：`llm=True`，model pool only，保留 provider timeout/429 retry budget；禁止翻译。
- `source.narrative_verify`：`llm=False`，回放 locator，生成 bundle/effect。

**handler 边界**

- 只接受 `JobExecutionContext`：job identity、source ref、dependency results、heartbeat/cancel callback。
- raw 只能通过 `SourceVersionReader.open_version()` 获得 bytes；handler 不接收永久路径。
- PDF、TXT/HTML transcript 分别复用 Phase C/Phase D parser；不重新实现选择规则。
- 一般性制度文档、会议通知等只有在完整低成本扫描覆盖成立时才可 `skipped_no_narrative`；解析失败不能伪装 skip。
- summary 与原文语言一致；`translate=false` 是冻结默认。
- optional LLM adapter 每个 model process 自建；测试用 deterministic fake/replay。无凭证时返回具名配置状态，不能调用未知外部服务。

**测试**

- 单元：三类 handler 输入/输出 schema、size cap、skip、语言、引用、hash drift。
- 集成：dependency result 传递、SourceVersionReader 拒绝、LLM 429/timeout、重复执行确定性。
- Phase C 现有 annual/prospectus/IR/transcript locator tests 保持绿。

### E5：内容寻址 bundle 与单 writer projector

**RED 测试先行**

- bundle 写一半崩溃：没有 catalog visible 行；临时文件可清理。
- object rename 后、catalog insert 前崩溃：重试复用同 hash object。
- AUTO `finish_attempt` 原子保存 attempt result/effect/outbox；outbox 只含 effect 身份，E5 必须增加只读 `result_for_effect(effect_id)`，精确找回同一已完成 attempt 的 bundle；缺失/多重/不匹配都拒绝。
- 分发器只 claim `narrative_bundle.publish`，校验 bundle SHA 与 effect `intended_after_hash`，把 effect 交给 projector；当前没有 outbox 生产分发器，这一层必须实现并供 E7 调用。
- catalog `prepared` 登记后、outbox ACK 前崩溃：lease 重试发现同 work_key/hash，完成 ACK，不生成第二行或重跑模型。
- outbox ACK 后、catalog activate 前崩溃：恢复器用 `effect_id` 找到 `prepared` 行，发现 AUTO effect 已 verified 后幂等 activate。
- pause 在 ACK 与 activate 之间成功：旧 generation 不得把 `prepared` 变成 `visible`；恢复器在 gate 仍 paused 时保持隐藏，下一次明确 enable 后才恢复。
- 同 work_key 不同 hash：冲突并 fail closed。
- pause 在 compute 后、project 前发生：旧 generation 不产生 visible 行。
- source retired、primary source/hash 或 read policy 改变：project 拒绝。
- CatalogOperationLock busy：有界 retry，不长期占 AUTO transaction。
- locator 回放失败或 summary citation 不合法：无 effect/outbox/visible artifact。

**实现文件**

- 新 `src/company_wiki/automation/narrative_projection.py`（窄 effect dispatcher、pathless reader、lease/retry、prepared reconciliation）
- `src/company_wiki/automation/store.py`（按 effect 读取已完成 handler result；claim 支持 effect type 过滤）
- 新 `src/company_wiki/source_catalog/narrative_artifact_store.py`
- `src/company_wiki/source_catalog/store.py`（幂等 additive DDL）
- 新 `src/company_wiki/automation/narrative_artifact_reader.py`（typed/pathless reader）
- `src/company_wiki/source_catalog/store.py`（前述窄表与索引、additive DDL）
- 不修改旧 `artifact_dag.py`/generic `artifacts`：narrative bundle 由 AUTO DAG 的 `source.narrative_verify` effect 发布；混入旧 normalized/sections DAG 会制造第二套职责和迁移面。
- `src/company_wiki/automation/narrative_verify.py` 仅在 RED 证明 payload 绑定不足时改；解析/LLM 不得进入 projector。
- 新 `tests/contract/test_narrative_artifact_layering.py`、`tests/unit/test_narrative_artifact_store.py`、`tests/unit/test_narrative_outbox_store.py` 与 `tests/integration/test_narrative_runtime_e2e.py`。最后一项使用真实隔离 PDF/TXT 运行 handler/outbox/reader，并覆盖 ACK 崩溃恢复与 pause-generation 竞态。

分层合同：`source_catalog/narrative_artifact_store.py` 只接 canonical bytes、SHA 和 primitive version metadata，负责 object adapter 与窄 SQL repository；它不得 import `automation`、Effect 或 NarrativeBundle。automation projector/outbox/reader 作为上层，负责 strict NarrativeBundle/effect 校验并调用该 repository。storage adapter 以外不读取/拼接 object 物理路径。

**固定数据流（不跨两个 WAL 数据库假设原子性）**

1. Worker `finish_attempt` 在一个 AUTO 事务中写成功 attempt result、pending effect 与 pending outbox，job 留在 `VERIFYING`。
2. narrative dispatcher 用 generation-fenced lease 只 claim `narrative_bundle.publish`，读取并严格解析那一个 attempt result；canonical bundle SHA 必须等于 effect hash。投影错误走有界 retry/dead-letter，不调用模型。
3. content-addressed object adapter 在 catalog lock 外原子写/复用对象；catalog projector 随后持 `CatalogOperationLock` 短锁，重验 Worker generation、来源当前 active/primary/source SHA 和 read policy，在一个 catalog 事务插入 `prepared`。
4. dispatcher ACK AUTO outbox；ACK 成功后再持短锁重验上述状态和已 verified effect，把该行原子变成 `visible`。pause 可在线性化边界阻止旧 generation；ACK 后崩溃由 prepared reconciler 恢复。
5. automation 层 `NarrativeArtifactReader` 只按逻辑身份读取 `visible` 版本，经 source_catalog adapter 取得 bytes 并重验 byte size、SHA、strict bundle schema 与当前来源 SHA；不返回 object path。来源退休记 `retired`，内容/身份/策略冲突记 `quarantined`，二者均不可读。

Object adapter 是本阶段唯一接触 `.source_catalog/objects/sha256/{prefix}/{sha}.json` 物理布局的层；store/projector/reader/consumer 只见 `object_key` 或 verified bytes。临时与目标同卷，fsync 后原子 rename，已有对象必须重验 hash，不覆盖异 hash 对象。孤儿对象留待后续有引用账的清理阶段，E5 不自行猜测删除。

automation 层 projector 是唯一 narrative catalog writer。它只依赖下层 source_catalog storage port；source_catalog 不反向导入 automation。pause/catalog operation lock 只包短时校验与事务，不包 I/O/解析/LLM；内容写完至 catalog 提交之间崩溃时只留下可复用的孤儿对象。自动事实决定是否继续，不使用授权文件、人工 review receipt 或人工队列。

### E6：关键真实数据端到端

测试根结构：

```text
<configured-e6-test-root>\m3-e2e-<nonce>\
  input\              # 从 frozen 样本复制的只读原件
  project\            # 临时 company-wiki/config/catalog
  automation\         # 临时 AUTO DB
  process-logs\       # 有界 stdout/stderr
  receipts\           # 测试收据
```

首个 E6 cohort 由**四份真实样本 + 一个合成低价值控制样本**组成，不下载新文件：

- P01 年报；
- P04 招股说明书；
- P07 投资者关系活动记录；
- T01 或等价已登记 transcript TXT。
- 合成 `投资者关系管理办法（2025年8月）.pdf`：只验证已知 `ir_policy` 路由完整扫描后生成小型 skip，不计入四份真实样本的空间比率。

P1 和 P2 各自使用独立 automation DB、catalog 和对象目录，防止上一 profile 的 visible artifact 污染下一组测量；每个 profile 都拷贝相同四份真实原件与同一 skip 控制样本。执行链：临时 catalog register → materialize 5 个 DAG → P1/P2 worker → select → deterministic replay summarize（skip 不调用模型）→ locator verify → outbox project → pathless narrative reader → 再次 materialize/运行应零新增逻辑 artifact。

必须断言：

1. 每个 profile 下四份 copied raw 与 skip 控制文件的 before/after SHA-256 完全相同；每份复制件先与 frozen production sample SHA 比对。
2. 原 production raw、catalog、control JSON、runtime 均未变化。
3. 五个 source 的 job 按 DAG 依赖顺序；至少两个不同 source 在 P2 有重叠执行区间；P1 单 mixed worker 的作业区间无重叠。
4. 最终每个 work_key 的 visible count `<=1`。
5. P01/P04/P07/T01 冻结 anchor 可从 bundle locator 回放。
6. 低价值 `ir_policy` fixture 产生 `skipped_no_narrative`、完整 coverage、零 evidence、零模型调用；skip bundle `<=16 KiB` 且不含全文。
7. 没有新增旧 `normalized.md`、`summary.md` 或全量 evidence_spans。
8. 分别对 P1、P2 四份真实样本计算最终对象总字节 / 原始字节，均 `<=3%`；skip bundle 单独按 `<=16 KiB` 验收。
9. 测试根由 `COMPANY_WIKI_E6_TEST_BASE` 显式指定；未设置时使用 pytest 创建的 `tmp_path`。测试开始记录 test-root 的直接子项快照，只在该根下创建唯一 `m3-e2e-<nonce>` 子目录；结束时确认该子目录在根内，再只删除该精确路径，并确认 test-root 子项恢复快照。

**E6 实施收据（2026-09-30）：**真实样本 P1/P2 已完成。真实年报/半年报/季报/transcript 的标准选择上限设为 96 spans，招股书/增发/可转债为 160 spans；旧默认 160/320 使首轮对象/原文比达到 3.55%。降额后 P01 年报仍覆盖新业务、研发产品、产能、订单客户、主营业务、行业动态；P04 招股书仍覆盖新业务、研发产品、产能、订单客户、主营业务、出海。真实 P1/P2 E2E 通过（1 passed），覆盖跨文档重叠、skip、不重复生成、locator 回放、原件与生产状态指纹不变、各 profile 空间比不超过 3%，测试根恢复。测试输入与 production/test root 从仓库/env 动态解析，不依赖开发机固定绝对路径。E7 故障恢复/重启/吞吐测试仍未实施。

### E7：恢复矩阵、吞吐与空间收据

将旧 F01–F20 合并为 11 个可执行场景，减少重复但不丢关键失效模式：

| 场景 | 覆盖 |
|---|---|
| R01 双进程同 job claim | race、attempt_no、唯一 token |
| R02 claim 后派发/父进程丢失 | lease 恢复、job_key 幂等 |
| R03 handler 执行中强杀 | heartbeat 停止、reap、子进程回收 |
| R04 慢旧执行者在新 attempt 后返回 | latest-attempt/token fencing |
| R05 pause 与 finish/project 竞争 | generation + commit lock |
| R06 finish transaction 任一点失败 | attempt/job/effect/outbox 全有或全无 |
| R07 object/catalog/ACK 三个崩溃窗 | projector 幂等、不重跑 LLM |
| R08 catalog lock/SQLite busy | 有界退避、无吞异常/死锁 |
| R09 model 429、timeout、响应丢失 | 单模型槽、预算、有界 retry |
| R10 source/hash/policy/locator 漂移 | publish 前重验并拒绝 |
| R11 100 个混合 job 中断重启 | 无永久悬挂、无重复 visible、日志有界 |

并发 benchmark：

1. 先用 deterministic delay handler 比较 P1/P2/P4，每个 profile 两轮，交错顺序。
2. 再用 E6 四份真实文档比较 P1/P2；模型使用相同 replay 响应，排除远程速率噪声。
3. 记录完成文档/小时、wall time、job wait/run、SQLite busy time、catalog lock wait、峰值 RSS、对象/DB/WAL 新增字节、retry 数。
4. P2 相对 P1 吞吐提升 `>=25%` 且无质量、重复、内存/锁预算退化，才成为建议默认。
5. P4 只有相对 P2 再提升 `>=15%`，且峰值 RSS `<= P2 的 1.8 倍`、SQLite busy p95 `<250ms` 才建议使用；否则保持 P2 或 P1。
6. Phase E 不测多模型并发；model workers 始终为 1。

空间门：

- 单文档 selection result `<=1 MiB`；summary result `<=64 KiB`；最终 bundle `<=1.25 MiB`。
- skipped bundle `<=16 KiB`。
- E6 四份真实文档最终对象总字节 / raw 总字节目标 `<=3%`；Phase C 12 文档实测 `1.0533%` 作为参考，不把 tiny synthetic 比率当容量证据。
- 测试完成后临时文件为 0；长期只保留 AUTO DB 审计记录和一个 content-addressed final object。
- Phase G 再定义 attempt result 压缩/保留期和旧 46 GiB 派生删除；Phase E 不删除 raw。

### 大节点 E-B：M3 集中验收

只在 E3–E7 完成后做一次集中审查：

- 新/改模块单元与 integration 全绿；
- R01–R10 各一次确定性故障注入全绿；R01/R03/R04/R05/R07 用真实进程重复 3 次；
- R11 一次 100-job bounded run 全绿；
- E6 真实四文档链全绿且 test root 恢复；
- P1/P2/P4 与空间 receipt 生成；
- pre-commit Ruff、scoped mypy、config doctor、host guard 全绿；
- `git status` 每个变化都可解释；
- production Worker 仍 paused，未新增 runtime，production raw/catalog hash 不变。

不要求在每个 helper、每个 job stage 做人工复核，也不做 72 小时 soak。失败时只修对应场景及直接依赖，再在 E-B 统一复跑。

**2026-10-01 执行收据：**专用分支 `codex/narrative-gates-integration@cba745a` 上 E-B 聚焦回归通过 **404 passed, 2 skipped, 695 deselected**；UTF-8 parent/child 环境通过此前默认 CP936 与 pytest capture 的编码冲突。R05 pause-vs-finish 与 R07 ACK 后进程退出/恢复各重复 3 次；R08 以真实 catalog lock 验证 prepared 不提前 visible、解锁后 reconcile 唯一发布。E6 最新四文档 P1/P2 为 90.14/84.776 秒、159.8/169.9 docs/h、峰值 RSS 401,235,968/495,566,848 B；P2 提速约 6.3%、RSS 高约 23.5%，锁等待 p95 尚无数据。生产 Worker 保持 paused/default-off。

此收据证明专用分支上的 E-B 测试门通过，不证明该分支已集成到 CWP master。当前 `master@b0fd763` 与该分支分叉，主线整合须先按 Phase 32 完成提交/文件差异审查，再以整合后的主线版本运行相应测试。

## 5. 精确文件变更表

| 文件 | 计划动作 | 禁止事项 |
|---|---|---|
| `automation/migrations.py` | v1/v2 snapshot、备份、rollback、drift validation | 不静默修 schema |
| `automation/models.py` | claim/gate/outbox lease 类型，完整 HandlerResult 序列化 | 不引入 source_catalog 类型 |
| `automation/store.py` | 原子 application operations | 不把多步事务留给 Worker |
| `automation/dag_persistence.py` | connection-local DAG SQL 与幂等比较 | 不拥有 transaction、不执行 handler |
| `automation/worker.py` | 薄 orchestration、具名错误、heartbeat 生命周期 | 不吞异常、不共享 client |
| `automation/scheduler.py` | 新建；DAG materialize/promote | 不执行 handler |
| `automation/runtime_control.py` | 新建；gate generation | 不启动 production |
| `automation/supervisor.py` | 新建；spawn/profile/restart | 不以内存 queue 作事实源 |
| `automation/worker_process.py` | 新建；子进程 entry point | 不继承父进程 client/connection |
| `automation/registry.py` | 登记 3 个 narrative job | 不泛化旧 research writer |
| `automation/planner.py` | source event → 3-stage DAG | 不建立跨仓 job |
| `source_catalog/narrative_jobs.py` | 新建；Phase C adapter | 不做全文 normalized |
| `source_catalog/narrative_artifact_store.py` | 新建；immutable version registry | 不覆写同 work_key 不同 hash |
| `automation/narrative_projector.py` | 新建；唯一 typed bundle writer/orchestrator | 不让底层 storage 依赖 automation |
| `automation/narrative_artifact_reader.py` | 新建；strict/pathless verified read | 不泄露物理路径 |
| `automation/narrative_outbox.py` | 新建；effect lease/dispatch/reconcile | 不重跑已完成 handler/LLM |
| `source_catalog/store.py` | narrative version table migration | 不改 raw/source identity |
| `source_catalog/control.py` | legacy default paused/interlock | 不自动恢复 enabled |
| `source_catalog/worker.py` | destructive prune default disabled | 不重写旧 run_cycle |

## 6. 回退与兼容

1. Phase E 新能力默认 paused；回退只需保持 gate paused，旧 raw/source catalog 读取仍可用。
2. Automation v2 迁移前有备份；不执行自动 downgrade。回退代码只读 v2 不安全，因此必须保留对应代码 commit 或从备份恢复临时测试库。
3. narrative object 和 version row 是新增面，不替换旧 `artifacts`、export 或 reader；Phase F 完成消费者 adapter 前不宣称跨仓可用。
4. 旧 SourceCatalogWorker 保持 paused。Phase E 不删除其代码；完成 E-B 后另立退役卡，避免两套执行器同时运行。
5. 任何 E-B 失败都不需要删除 raw；只清理测试根和未 visible 的测试 object。

## 7. 实施收据模板

Phase E 完成时在 `progress.md` 记录：

- implementation commits；
- migration/store/supervisor/projector/handler test counts；
- 150 项旧基线的最终结果；
- R01–R11 结果；
- E6 四文档 source hash、anchor、visible count、重复运行结果；
- P1/P2/P4 吞吐、RSS、锁等待；
- AUTO DB、WAL、object、临时目录各自新增字节；
- production pause/raw/catalog 不变证明；
- RF 只读 boundary check；
- 未完成项只进入 Phase F/G，不扩大“完成”语义。

## 8. 开始实施前检查

- [x] 本施工卡已单独 commit（`77b1229`）。
- [x] company-wiki 开始实施时除已知不可访问临时目录外干净。
- [x] revenue-forecast 每阶段只读核查，无修改对方文件。
- [x] production legacy Worker 仍 paused、无 runtime。
- [x] 先完成 E0 RED/green，再进入 Store。
- [x] E-A 通过前未新增 Supervisor/narrative handler 产品代码。
- [x] E-B 测试门已在专用分支通过；由于尚未完成主线整合、G-C/G-D 未关闭且真实并发提速证据不足，production Worker 继续 paused/default-off。
