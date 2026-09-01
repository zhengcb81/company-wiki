# Source Catalog Worker 恢复与性能治理 — 独立实施计划

> 计划目录：`docs/plans/source-catalog-worker-recovery-2026-08-22/`  
> 计划创建：2026-08-22（Europe/London）  
> 来源报告：`docs/worker-investigation-2026-08-20.md`  
> 当前用途：独立保留，供以后实施；**不并入现有主线计划，不修改主线计划索引**  
> 实施状态：尚未开始；worker 当前应保持持久暂停且登录自启动关闭

## 0. 目标、边界与成功定义

### 0.1 总目标

在不损害源文件、不污染生产配置、不破坏单线程安全约束的前提下，修复 Source Catalog worker 自 2026-08-12 起的正常化队列 SQL 性能回归及其控制面放大链，建立可验证的性能、恢复、回退和独立审查机制，最后通过受控 canary 决定是否恢复长期运行与登录自启动。

### 0.2 本计划必须解决

- [ ] 正常化队列相关子查询的近似二次复杂度与错误索引选择。
- [ ] 缺少生产规模性能回归测试的问题。
- [ ] 扫描成功但完整周期失败时 checkpoint 丢失、导致重复全盘扫描的问题。
- [ ] 长 SQL 无 heartbeat、无阶段计时、无法安全取消的问题。
- [ ] supervisor 仅凭 uptime 重置失败计数、导致永不退避的问题。
- [ ] 扫描器逐目录/逐分组效率与电池 gating 顺序问题。
- [ ] normalize batch 3 与 LLM batch 1 的长期生产/消费失衡。
- [ ] retention prune 属性错误、日志保留、catalog 容量与敏感数据边界。
- [ ] 修复后的单周期 canary、人工观察、回退和最终恢复自启动流程。

### 0.3 明确不在本计划中自动执行

- [ ] 不删除、移动或重写`companies/`及已登记外部portfolio/cloud-sync roots中的源文件。
- [ ] 不修改 StockWiki 或向 StockWiki 写入任何内容。
- [ ] 不直接在 46 GiB 生产数据库上试验 schema 或运行 `VACUUM`。
- [ ] 不删除 45.93 GiB remediation 备份，除非另有用户明确授权和恢复点审查。
- [ ] 不把现有非线程安全 `LLMClient` 直接放入多线程。
- [ ] 不修改 `config/source_catalog.yaml` 做测试；测试必须使用 tmp 配置与 tmp catalog。
- [ ] 不恢复登录自启动，除非所有恢复 Gate 均通过且用户明确批准。
- [ ] 不把本目录链接进任何现有计划索引或主线计划，直到用户以后决定合并。

### 0.4 全局成功标准

- [ ] 生产形状数据上 normalize queue warm-cache n≥30且P95<2秒，cold-ish新进程/连接n≥10且max<10秒。
- [ ] query plan 不再出现“全表 documents + 相关子查询按 `idx_locations_status` 重复扫描”。
- [ ] 队列语义、优先级、retry/terminal 行为与修复前业务意图一致。
- [ ] normalize 候选必须有 active `original_primary` 且其 `source_id` 与
  `documents.primary_source_id` 一致；locationless/source-mismatch 文档不得占据 batch。
- [ ] scan 成功后即使 normalize 被故意中断，重启也不会立即重复扫描。
- [ ] 连续至少 5 个完整周期成功，且 2 小时观察窗口无 heartbeat timeout。
- [ ] worker 空闲时不持续占用一个 CPU 核；没有无限重启循环。
- [ ] 源目录文件 hash/mtime 在受控 canary 前后保持不变。
- [ ] canary 对源目录的写操作由 OS/sandbox 权限主动拒绝，不能只靠事后 hash 发现。
- [ ] worker 保持单实例，pause/stop/resume/backoff/circuit-breaker 行为有测试覆盖。
- [ ] **每个关键节点**均完成独立 agent 审查；实施者不得批准自己的阶段。
- [ ] SQL、supervisor、端到端、生产 canary、恢复自启动等高风险节点至少由 2 名
  不同视角的独立 agent 审查；G10C、G10R、G12C-PRE 与 G12C 各恰好 3 名。
- [ ] Registry安装后先保持`ARMED_ON_PRELOGIN/ON` dormant；登录验证后保持
  `LOGIN_VALIDATED_PAUSED/ON`；只有独立D12C/G12C-PRE/OP12C/G12C与新用户授权才启用下次登录，且
  最终仍process0，不顺带启动当前session。
- [ ] 未经单独数据授权时，LLM 与所有 fallback provider 均保持 disabled，并有进程级
  network deny 证据；“运行/观察 worker”的授权不自动包含外发授权。
- [ ] 生产运行加载固定、受审的 release/worktree identity，而不是可被另一个任务实时
  修改的工作树；code root 与 config/catalog/runtime roots 明确分离。
- [ ] 登录启动的首段非 OS 代码使用独立 trust anchor，最终 release 对 worker identity 不可
  写/删/换名，完整 manifest 与 interpreter/lazy modules 都经 tamper/TOCTOU 测试。
- [ ] normalized/summary 的“current”同时绑定当前 primary source ID 与 content SHA；source
  rotation 后旧 artifact 不得抑制或被包装成新来源结果。
- [ ] circuit open 时 resume/session/arm/login/activate 全部 fail closed；每次reset只能通过唯一
  D05Rnn→OP05Rnn→G05Rnn，reset 后仍 paused、process0且没有直接resume出边。

## 1. 工作约定

### 1.1 实施隔离

- [ ] 每次实施前重新读取本文件、`findings.md` 和 `progress.md`。
- [ ] 重新核对实际代码；计划中的行号仅是 2026-08-22 基线，代码变化后不得盲信。
- [ ] 使用独立分支或独立 worktree；不得覆盖另一个任务的未提交改动。
- [ ] 实施前记录 `git status --short`，逐项归属已有改动。
- [ ] 本计划目录之外的任何修改都必须对应一个明确 Phase 和测试。
- [ ] 同一 plan revision 内不修改本文件、`findings.md` 或 `traceability_matrix.md` 的状态。
  实际节点、证据和审查只追加到 schema-valid `gate_ledger.jsonl`，叙事写 `progress.md`；只有
  规范语义变化才建立新 plan revision。

### 1.2 生产保护不变量

- [ ] `worker_control.json.desired_state` 在 canary 前保持 `paused`。
- [ ] `CompanyWikiSourceCatalog` HKCU Run 使用分阶段不变量：OP12B-CAS 前必须不存在；只有该
  节点可 atomic create exact dormant value；此后 launcher 在无有效 LOGIN_COMMITTED 或未取得
  G12C `RECOVERED` outcome 时零启动。除 OP12B-CAS 与显式 OP12B-RB 外禁止 registry 写。
- [ ] 测试不得写生产 `.source_catalog/catalog.sqlite3`。
- [ ] 不运行会修改生产配置的测试或调试命令。
- [ ] 对任何 lock 的处理必须核验 PID、creation time 和 executable，禁止按 PID 数字盲删。
- [ ] 所有迁移必须具备空间预算、失败回滚与幂等性证明。

### 1.3 证据要求

每个技术结论至少附：

- [ ] 代码定位；
- [ ] 可复现测试或最小实验；
- [ ] 修复前失败证据；
- [ ] 修复后通过证据；
- [ ] 对生产语义和安全边界的说明；
- [ ] 独立审查结论。

### 1.4 每个关键节点的独立 Agent 强制 Gate

以下规则适用于 Phase 0–12，优先级高于各 Phase 中较简略的 Gate 描述：

- [ ] “关键节点”以 `gate_dag.v4.json` 的每个T/D/I/OP/G为准，包括ledger bootstrap、三个
  ADR Gate、G09P、G10C、G10R、条件G11M/G11M-L、D11J/OP11J/G11J、A1/A2/A3、每个BP/BF
  provider、12B每个ARM/CAS/LOGIN及预审/执行rollback节点、D12C/G12C-PRE/OP12C/G12C与
  OP12C-RB/G12C-RB，以及每次D05Rnn/OP05Rnn/G05Rnn；
  不能只按Phase出口粗略合并。
- [ ] 实施 agent 在提交 Gate 前必须先生成不可变证据包：基线、diff、测试命令、完整
  测试结果、性能数据、失败注入结果、风险说明、回滚点和当前 Git commit/worktree。
- [ ] 审查agent必须满足`gate_dag.v4.json`为该节点声明的`reviewer_independence`、
  `forbidden_agent_sets`与`min_not_in`，并至少与本节点实施/OP agent不同；不得修改代码、测试、
  配置或被审查证据，只能提交书面findings。“独立/DAG-disjoint”只表示这些机器规则，不能
  擅自扩大为DAG未声明的全局“从未参加过任何旧节点”。
- [ ] 审查结论只能是 `PASS`、`PASS_WITH_NONBLOCKING_FINDINGS` 或 `FAIL`。
- [ ] P0（安全/数据损失/越权）或 P1（正确性/恢复/严重性能）发现未关闭时，Gate 必须
  为 `FAIL`，禁止开始下一 Phase。P2 必须有负责人、截止节点和明确处置；P3 可记录。
- [ ] 修复审查发现后，实施 agent 必须重新运行受影响测试并产生新证据包；原审查 agent
  或另一名同领域独立 agent 必须复审，禁止实施者自行宣布关闭。
- [ ] 每份审查同时返回`review_result.schema.json` machine payload与Markdown报告，包含Gate、
  role/agent/独立性、input ledger head、plan/DAG/evidence hashes、反例、findings、verdict；保存后
  同一 reviewer 必须另发 `review_confirmation.schema.json` detached 回读确认，主 agent 无权代填。
- [ ] 精确人数由`gate_dag.v4.json`决定：每个D/G至少1名；G00L、G02A/G02B-ADR/两个02B
  分支、D05/G05、G07-ADR、D07E/G07E、D09P/G09P、D09/G09、所有生产D/G、每次reset D/G
  至少2名；G10C/G10R/G12C-PRE/G12C各恰好3名。任何节点的实际人数与 role set 必须恰好
  等于 machine DAG，不能把“至少”解释为可多派 reviewer。
- [ ] 未来实施时，非敏感脱敏证据与审查记录只能写入本隔离计划目录下预留的
  `evidence/` 与 `reviews/`；含用户名、完整外部路径/portfolio名、命令行、正文的 raw
  evidence 仅在用户另行批准时进入 D Gate 冻结的 repo外 approved sink，并满足 SID ACL、
  加密、无reparse、7/30日TTL；secret/token/cookie/credential永不采集。仓内只写opaque ID/
  脱敏统计/不可逆验证标识，直到用户决定并入主线。
- [ ] 详细角色、模板和逐 Gate 清单以 `agent_review_gates.md` 为准；若两处冲突，采用
  更严格的要求。

### 1.5 唯一执行顺序与数值合同

- [ ] `gate_dag.v4.json` 是机器唯一DAG，`gate_state_machine.md`是人类可读等价解释；不一致
  必须GLV-E023并停止。Phase编号不等于线性执行顺序。
- [ ] 普通实现 WP 使用 `Txx→Dxx→Ixx→Gxx`；WP-01 是唯一
  `TEST_BASELINE_ONLY` 例外 `T01→D01→G01`，禁止产品代码/seam 变更；D 后测试变化必须重审。
- [ ] v4节点状态只有`READY/IN_PROGRESS/PASSED/PASSED_WITH_P2/BLOCKED/INVALIDATED`；reviewer只用
  `PASS/PASS_WITH_NONBLOCKING_FINDINGS/FAIL`。
- [ ] 未选分支完全不写ledger；选择只记录在G02B-ADR/G07-ADR/G11M-L-ADR的machine
  `branch_decision`。任何未选branch record都由validator拒绝。
- [ ] 所有性能/SLA/circuit/canary 数值按 `acceptance_thresholds.md`；放宽必须有 ADR 与
  独立 reviewer 批准，不能在测试失败后临场修改。
- [ ] 核心恢复 lane 可先到 restricted canary；scanner/parser/LLM/retention hardening lane
  在完整两小时观察与自启动前必须按启用功能通过，或功能以 fail-closed 方式明确禁用。

## Phase 00L（先实现 ledger fail-closed 控制面）— 状态：pending

### 00L.1 T00L → D00L → I00L → G00L

- [ ] T00L只创建tmp tests/fixtures，先以专用 instance schema 验证 DAG/vectors/test-registry/
  operation-catalog 并证明 `{}`、`[]`、scalar失败，再按`gate_ledger_validator_vectors.v4.json`逐项实现GL-S01、
  GL-S02、GL-S03、GL-S04、GL-S05、GL-S06、GL-F01、GL-F02、GL-F03、GL-F04、GL-F05、
  GL-F06、GL-F07、GL-F08、GL-F09、GL-F10、GL-F11、GL-F12与TESTID-S01；禁止生产读写。
- [ ] D00L一名独立agent审负例、canonical/hash/branch/reviewer语义；通过前不改validator实现。
- [ ] I00L实现stdlib-only deterministic validator、review JSON+detached confirmation核对、
  operation/auth/test-ID contract核对、expected-head exclusive append与只读`next`；不联网、
  不import业务代码、不执行节点。I00L另生成`validator_release_manifest.v1.json`；v4 plan
  manifest不得预先声称冻结未来脚本。
- [ ] G00L两名独立agent分别审hash-chain/schema与DAG/adversarial vectors；property序列≥200、
  mutant survivor=0、生产DB/registry/network调用0。
- [ ] 到I00L terminal为止先生成canonical bootstrap transcript候选与external head；只有D00L
  review可用null head，G00L两份review必须绑定同一候选head和validator release hash。G00L
  通过并完成detached confirmation后，才以候选原字节加G00L terminal record一次性初始化正式
  ledger；之前的review证据保存在D00L批准的只追加bootstrap sink。若控制面失败，不能人工编辑。

## Phase 0（实施前重新基线化）— 状态：pending

### 0.1 状态和漂移检查

- [ ] 先验证`plan_review_revision.md`指定的活动`plan_manifest.vN.json`自身SHA-256，再用该
  machine manifest逐项核验全部核心计划文件与来源报告；随后读取`progress.md`。禁止只读
  早期三份planning文件或用当前文件重新生成hash来冒充冻结值。
- [ ] 只有G00L有效后才允许ledger；使用validator核对schema、review payload actual hash、
  seq/prev/expected-head、manifest/DAG、branch/join与全部失效传播；不相信record自报next。
- [ ] 核对 worker 是否仍为 `PAUSED / STOPPED`。
- [ ] 核对 supervisor、worker、parser 相关进程为 0。
- [ ] 核对 HKCU Run、计划任务、服务没有自动启动入口。
- [ ] 核对关键 worker 文件当前 hash、Git HEAD 与报告基线差异。
- [ ] 核对另一个任务是否修改了 normalizer、worker、store、scanner、control 或 supervisor。
- [ ] 将`tests/contract/test_zr1002_reader_first.py`与
  `tests/contract/test_zr1003_shadow_assertions.py`列入Phase 0基线并保存当前通过/失败原因；这两项
  当前tmp夹具依赖missing DB触发`CatalogStore` eager init，不能把该测试假设当作产品合同。
- [ ] 对已变化的计划项标记“已无效（代码已变更）”，重新取证后才能继续。

### 0.2 数据和空间基线

- [ ] 只读记录 production DB/WAL/SHM 大小、C 盘余量、schema version、row counts。
- [ ] 记录 locations 状态分布、normalize eligible、fingerprint pending、LLM pending。
- [ ] 只读获取当前 query plan，不运行无边界的慢查询。
- [ ] 为未来索引迁移计算最坏空间需求和失败时额外空间需求。

### 0.3 D00 → OP00 → G00

- [ ] worker 确认停止且自启动关闭。
- [ ] 工作树已有改动归属清楚，无文件冲突。
- [ ] 生产配置未变；`python scripts/config_doctor.py` 在安全的只读/预期行为下通过，或问题被记录并阻断后续。
- [ ] D00 冻结只读命令、预期 diagnostic writes 与路径；OP00 只执行该清单；G00 的独立
  “基线与隔离审查 agent”复核进程、自启动、工作树归属、生产路径写保护和容量数据，
  提交 `PASS`；否则禁止 T01。
- [ ] 只有满足以上条件才进入 Phase 1。

## Phase 1（生产规模回归夹具与基线测试）— 状态：pending

### 1.1 建立 tmp-only 性能夹具

- [ ] 创建 20k–30k documents、40k–60k locations 的确定性生成器。
- [ ] active location 占比 > 50%，active original_primary 与 locationless 文档混合。
- [ ] 包含 completed、partial、unsupported、failed retryable、failed terminal artifact。
- [ ] 包含多个 roots、重复 locations、孤儿防御场景和真实 document_kind 优先级。
- [ ] 包含大量 locationless、active location 绑定错误 `source_id`、正确 parseable primary
  以及 duplicate primary；这些 outer rows 不得为了提速从夹具预先删除。
- [ ] 所有文件、配置和 SQLite DB 位于 pytest `tmp_path`。

### 1.2 先写失败测试

- [ ] 功能测试：没有 active、source-matching `original_primary` 的文档不得进入任何返回
  batch，同时夹具保留它们以捕获 outer-scan 退化。
- [ ] 顺序测试：返回前三个 document ID 与 priority 规则一致。
- [ ] retry 测试：只有 due 且 non-terminal 的 failed artifact 可重新进入队列。
- [ ] force matrix：`force=False/True` 分别定义 completed、retry、terminal、version 行为。
- [ ] query-plan 测试：拒绝相关子查询使用 `idx_locations_status` 的灾难性计划。
- [ ] 性能测试：旧实现必须在严格预算或 SQLite progress budget 下失败，不能无限等待。
- [ ] 本 Phase 不要求 stop/pause 取消测试转绿；O-S 取消测试在 T04/D04 中先红、G04 后
  转绿，防止 WP-02 越界实现 Phase 4。
- [ ] D01选择PROGRESS_PROXY_APPROX或STMTSTATUS_VM_STEP_EXACT。proxy固定progress_n、handler
  安装点、Python/SQLite source-id/PRAGMAs/params/LIMIT/fixture digest，只把callback_count×n
  称为近似work proxy，禁止exact step区间；exact模式满足native binding/consume/overflow合同。
  Q-P01、Q-P05、Q-P06（exact另Q-P07）验证metadata与表述。
- [ ] T01 只改 fixture/test/test helper。公开接口不足时 D01 必须 FAIL；不得在 WP-01 给
  production code 增加注入 seam，必要 seam 放入 I02A。

### 1.3 Gate 1

- [ ] 证明测试在旧实现上因目标缺陷失败，而不是夹具错误。
- [ ] 测试运行不创建或修改生产文件。
- [ ] 记录 fixture build time、DB size、query wall/user time 和 plan。
- [ ] 独立“测试设计/性能方法审查 agent”验证夹具代表性、旧实现确实失败、时间断言
  不脆弱、旧 SQL 基线确实被 work-budget 杀死；G01 不提前审 Phase 4，也不要求在新查询
  尚不存在时完成回替 mutant。提交 `PASS` 后才能进入 Phase 2。

## Phase 2（修复 normalize queue SQL 与索引契约）— 状态：pending

### 2.1 查询改写

- [ ] 将相关 `EXISTS` 改为非相关 candidate set/semi-join/CTE。
- [ ] 明确 roots join 是否有业务语义；若删除，先加 orphan 防御测试。
- [ ] 保持 artifact generator/version/retry/terminal 条件完全一致。
- [ ] candidate relation 必须同时匹配 `document_id` 与 `primary_source_id`，不能只检查 role/
  status；force/non-force 条件必须分别保持合同。
- [ ] current normalized suppression还必须匹配 artifact/source 的当前 primary source ID 与
  content SHA；logical document S1→S2 后，旧 completed/terminal/retry artifact 不得阻断 S2，
  持久化必须原子更新 source binding。
- [ ] 保持 priority 和 document_id 的稳定排序。
- [ ] 避免 `LIMIT` 掩盖全量 filter/sort 成本。

### 2.2 索引方案决策

- [ ] 对“仅查询改写”“覆盖复合索引”“部分索引”分别 benchmark。
- [ ] 测量索引大小、构建时间、写放大和 planner 稳定性。
- [ ] 若增加索引，提供幂等 schema migration、版本标记和回滚说明。
- [ ] 不把 `ANALYZE` 当作唯一正确性或性能保障。
- [ ] G02B-ADR先由两名reviewer只读G02A evidence并冻结ADR-02。其后只创建选中分支：
  `T02B-NI→D02B-NI→I02B-NI→G02B-NI`或
  `T02B-IDX→D02B-IDX→I02B-IDX→G02B-IDX`；禁止共用一个T commit。
- [ ] 两分支T都含M-COM-S01、M-COM-S02、M-COM-S03、M-COM-S04、M-COM-S05、
  M-COM-S06、M-COM-F01、M-COM-F02：missing DB ordinary open不创建文件，outdated只报
  upgrade required，init/upgrade仅operator entry且幂等/可恢复。
- [ ] 选中分支的T02B/I02B把ZR1002/ZR1003的`tmp_path`夹具改成先调用显式init/upgrade，
  再通过reader-first入口；分别纳入`M-COM-S05`（显式init/upgrade幂等）与`M-COM-S06`
  （reader/worker/login/canary绝不隐式DDL）的证据。只能改测试夹具与显式operator入口，禁止
  为保留旧测试而恢复产品eager DDL。
- [ ] I02B-NI 也必须把 ordinary store open 改为 verify-only 并通过 DDL-denying test；不是
  “无代码直接签字”。I02B-IDX 另实现 operator-only migrator，禁止 eager startup DDL。

### 2.3 测试

- [ ] Phase 1 全部测试转绿。
- [ ] 小型现有 contract suite 不回归。
- [ ] 生产形状 warm/cold-ish 多轮基准满足预算。
- [ ] 返回集合与修复前意图、只读生产对照一致。
- [ ] source-mismatch、locationless、duplicate location 与 force matrix 的独立 oracle 和
  mutation tests 全部通过。
- [ ] Q-S17 source-rotation测试证明 S1 artifact 不抑制 S2，UPSERT 后 source ID/hash为 S2/H2。
- [ ] 使用 SQLite 多版本或项目支持的最低版本验证 plan 不依赖偶然优化。

### 2.4 G02A 与条件 G02B-NI / G02B-IDX

- [ ] G02A 至少两名独立 agent 分别从 SQL 语义/source freshness 与 SQLite planner/复杂度
  审查；被选的G02B-NI或G02B-IDX由SQL与migration/capacity两名reviewer审查；均须PASS。
- [ ] 无生产 DB 写入。
- [ ] 性能数据、plan、语义对照与 branch choice写入 evidence，并在 ledger追加记录；不得
  动态改写冻结的 `findings.md`。

## Phase 3（扫描 checkpoint 与周期恢复语义）— 状态：pending

### 3.1 状态持久化设计

- [ ] scan 成功后立即原子写入 last_scan checkpoint。
- [ ] 明确 `scan_runs` 与 `worker_state.json` 谁是恢复事实源。
- [ ] 明确定义 `completed`、`completed_with_errors`、`partial`、`interrupted`、root offline、
  benign quarantined-file error 哪些可推进全局/per-root checkpoint。
- [ ] checkpoint 绑定 root-set、相关 config、scanner schema/version fingerprint；root 增删或
  语义配置变化不能错误复用旧 checkpoint。
- [ ] 处理“DB scan completed、state 写入失败”的不一致窗口。
- [ ] state schema 保持向后兼容，增加版本和迁移测试。

### 3.2 故障注入测试

- [ ] scan 完成后、normalize 前崩溃。
- [ ] normalize queue select 中断。
- [ ] parser 运行中 pause。
- [ ] LLM 请求失败。
- [ ] export/prune 失败。
- [ ] 每种情况下重启后 scan due、重试和状态都符合预期。
- [ ] 增加 benign quarantine、单 root access denied、partial enumeration、root 增删、配置/
  scanner version变化；成功 root 可推进，失败 root 独立重试，不能全盘重扫或长期陈旧。

### 3.3 Gate 3

- [ ] 故障注入后不会重复全盘扫描。
- [ ] checkpoint 写入保持原子性。
- [ ] 旧 state 文件可以安全读取。
- [ ] 独立“恢复语义/状态一致性审查 agent”逐个复核故障注入、事实源优先级和不一致
  窗口，提交 `PASS` 后才能进入 Phase 4。

## Phase 4（SQL 可取消性、heartbeat 与阶段遥测）— 状态：pending

### 4.1 细粒度计时

- [ ] 增加 queue_select、parse、persist、LLM、export 的独立 wall time。
- [ ] scan 增加 per-root enumerate/observe/DB commit 时间。
- [ ] runtime 和周期日志记录行数、路径和阶段，不记录敏感正文。

### 4.2 SQLite progress handler

- [ ] 低频刷新 heartbeat。
- [ ] 检查 pause/stop token。
- [ ] 明确长 SQL 期间如何看到**新的** control generation：低频、异常安全地读取外部
  control 状态，或由明确线程安全 watcher 更新 event；禁止捕获一次后永不刷新。
- [ ] 超过 query budget 时主动 `interrupt` 并产出明确错误码。
- [ ] handler 调用频率有性能基准，避免可观测性本身成为瓶颈。

### 4.3 测试和 Gate 4

- [ ] T04 中 O-S01至O-S11逐项先在旧实现上因缺少取消/遥测能力失败，D04通过后才实现。
- [ ] 模拟慢查询仍能在 pause SLA 内退出。
- [ ] 由另一个真实子进程在 query 开始后切换 pause/stop，证明 callback 看见新 generation。
- [ ] 正常快查询不产生明显开销。
- [ ] watchdog 不会误杀仍有业务进度的健康操作。
- [ ] liveness heartbeat、SQLite VM activity 与业务 milestone 使用不同字段；只有完整 cycle
  success 能清零 supervisor failure budget。
- [ ] 日志中能区分 queue select 与 parser。
- [ ] 独立“SQLite 取消/可观测性审查 agent”检查 progress handler 的安装与清理、
  re-entrancy、heartbeat 真实性和日志隐私，提交 `PASS` 后才能进入 Phase 5。

## Phase 5（supervisor backoff、健康里程碑和熔断）— 状态：pending

### 5.1 状态机修复

- [ ] 只有完整 cycle success 才能清零连续失败；scan checkpoint、heartbeat、VM activity、
  parser start 等部分里程碑只能用于诊断，不能清零。
- [ ] 相同 `stage + detail + reason` 重复失败进入指数退避。
- [ ] 同时持久化 per-signature 与全局滚动失败/无成功预算；交替签名、supervisor 重启、
  login/reboot 都不能绕过 circuit。
- [ ] 达到阈值后停止无限重启并标记 degraded/needs-attention。
- [ ] persistent pause 必须优先于 restart。
- [ ] child 身份核验必须继续防止误杀无关 PID。
- [ ] runtime/control envelope 绑定 launcher session、attempt、worker token、PID creation、code
  fingerprint、monotonic sequence；旧 attempt heartbeat 不得使新 child 看似健康。
- [ ] 受管生产 control/circuit 缺失或损坏时 fail closed（不启动并报警），只能显式 reset。
- [ ] reset/resume/resume-session/arm/login-commit/final-activation均为不同CLI action。生产reset
  只允许每次唯一D05Rnn→OP05Rnn→G05Rnn；open circuit时其他动作返回CIRCUIT_OPEN且零副作用。
  reset仅清active latch/budget、generation+1、保留历史，仍PAUSED/process0且只回冻结review节点。
- [ ] 保留 Windows Job Object create/assign/kill-on-close；assign 失败 fail closed，supervisor
  crash 后不得留下 orphan parser。
- [ ] 120 秒登录延迟每个 supervisor/login session 只支付一次，child restart 不重复支付。

### 5.2 测试和 Gate 5

- [ ] 900 秒后失败不会被视作健康成功。
- [ ] 短命失败、长命无进度、正常周期、pause、control stop 分别覆盖。
- [ ] PowerShell 和 Python 侧的状态契约一致。
- [ ] Windows 专项测试覆盖 PID reuse 和 creation time。
- [ ] 覆盖交替 failure signature、supervisor/login 重启、损坏 control/circuit、旧 attempt
  heartbeat、Job Object assignment failure/orphan cleanup、startup-delay-once与三动作完整状态
  矩阵（S-S18）。
- [ ] 至少两名独立 agent 分别从“supervisor 状态机”和“Windows 进程安全/运维”视角
  审查，确认不会无限复活或误杀无关进程；两者 `PASS` 后按 `gate_state_machine.md` 分流到
  Core 的 WP-09P 与 Hardening lanes，不能按编号自行猜测。

## Phase 6（扫描性能与电源策略）— 状态：pending

### 6.1 Profile 驱动优化

- [ ] 先增加 per-root/per-phase benchmark，再优化。
- [ ] D06 冻结 exact baseline commit 与同拓扑协议；若需埋点，先建 instrumentation-only
  revision并从它分叉旧/新实现。两边使用相同 topology/environment/instrumentation hash，
  每场景各n≥10、预声明warm-up/交替顺序，不以历史427秒作synthetic分母（SC-P04）。
- [ ] release benchmark 的 topology 至少复现报告中的约 244 company walks、16,570 groups、
  429 Dropbox-like directories、9,853 groups 与约 46,600 files，禁止用单 flat root替代。
- [ ] 评估 sidecar 缓存 `(path,size,mtime)`。
- [ ] 减少逐文件 path resolve、JSON 解析和重复 DB 查询。
- [ ] 评估批量读写、commit batch 大小与 writer lock 时间。
- [ ] 设计增量扫描，但保留周期性完整校验和可恢复语义。
- [ ] 明确相同 path/size/mtime/sidecar signature 可复用的条件，并按默认“每日 ≥3.34% 且30天
  覆盖全量”的内容 rehash 审计 SLA 检测 metadata spoof/tamper。

### 6.2 电池和空闲策略

- [ ] 将 power gating 移到 scan 之前，或明确设计例外。
- [ ] 测试电池模式下不发生意外全量扫描。
- [ ] 测试用户活动策略与默认配置一致。

### 6.3 Gate 6

- [ ] 完整 topology unchanged candidate P95 ≤120 秒，且同协议
  `baseline_P95/candidate_P95≥2.0`；若需
  放宽，必须 ADR + 独立 reviewer，不能用“明显改善”主观批准。
- [ ] files_seen/reused/hashed、身份、sidecar 和去重语义不回归。
- [ ] 中断后 scan_runs 状态正确。
- [ ] 独立“文件系统扫描/性能审查 agent”检查基准方法、缓存失效、源文件只读不变量、
  电池 gating 和恢复语义。`PASS` 仅完成 H6，不自动授权 H7、生产观察或自启动。

### 6.4 Parser 分格式 Profile 与 Gate 6P

- [ ] P-FMT00-ROUTE冻结实际dispatch：plain text、HTML、MHT HTML/fallback、PDF fallback/
  Docling、DOCX、DOC、XLSX、XLS、PPTX、JSON、XML/XSD、unsupported；保存route digest。
- [ ] 每route按registry实例化S（n≥20）、M（n≥10/max）或显式DIS、LIMIT（n≥5）、适用ERR
  C/E（n≥10）或NA、PAUSE（n≥20）；多extension每extension≥5。不得合并HTML与text样本。
- [ ] 各格式按 `acceptance_thresholds.md` 的 P-FMT budgets；未通过格式明确 deferred/
  unsupported 并 fail closed，不允许无边界运行。
- [ ] 独立 parser reviewer 检查样本代表性、child cleanup 和错误分类；G06P 只批准已验证
  格式，不能用 HTML 结果概括 Office/PDF。

## Phase 7（LLM 吞吐、失败策略与隐私）— 状态：pending

### 7.1 生产消费建模

- [ ] 用真实延迟分布计算 normalize/fingerprint/LLM drain time。
- [ ] 明确 batch 3:1 是否允许 backlog 暂时增长。
- [ ] 设计独立阶段时间预算和公平调度。
- [ ] 定义 LLM queue eligibility：每文档唯一 current completed normalized input、summary
  generator/version/status、old-version regeneration、stable dedupe-before-LIMIT；normalized和
  summary还必须绑定当前 primary source ID/hash、normalized artifact ID/hash 与request digest。
- [ ] source S1→S2时旧normalized/summary只可留作审计，不能抑制S2、进入LLM输入或被包装
  成S2 artifact（L-S18）。

### 7.2 方案评估

- [ ] cache 使用截断后 exact canonical request（正文、title、kind、source binding、system
  prompt、provider/model、generation params、routing contract）digest；只复用验证过的 provider
  payload，每个 document 重新绑定独立 artifact/locator，禁止只按正文 hash 跨文档复用。
- [ ] 单请求多文档批处理及逐文档输出校验。
- [ ] 无状态 client 重构后再评估有限并发。
- [ ] permanent failure 650 条分类和不可重试契约。
- [ ] provider 超时、限流、fallback、成本和隐私记录。
- [ ] 所有 fallback provider 与主 provider分别授权；provider/cost/data scope 任一为空时
  `LLM_DISABLED + NETWORK_DENY`，不得隐式 fallback。
- [ ] 建立durable request ledger：PREPARED→IN_FLIGHT；其后只允许RESPONSE_VALIDATED→
  COMPLETED、RETRYABLE_FAILED、PERMANENT_FAILED或OUTCOME_UNKNOWN。重启发现IN_FLIGHT转
  OUTCOME_UNKNOWN且不自动重发；只有能证明请求未被接受，或provider支持可验证
  idempotency/result lookup时才允许安全retry/reconcile。否则人工处置，最大预计费用继续占cap
  （L-S20/L-S21）；RESPONSE_VALIDATED后的本地commit不得再调用provider。
- [ ] request-ledger schema只在G11B-A3+G07E后进入两人G11M-L-ADR；SCHEMA_DELTA才走
  D11M-L→OP11M-L→G11M-L，NO_SCHEMA_DELTA直接到BP。禁止任何G07E→D11M-L早期边；禁止
  追加到eager `_DDL`。M-L-EDGE-S01、M-L-EDGE-S02、M-L-EDGE-S03必须杀死非法路径。

### 7.3 互斥的 G07E / G07O

- [ ] 不违反单线程/线程安全约束。
- [ ] 不把未授权全文发送给新增 provider。
- [ ] G07-ADR由两名reviewer冻结且只冻结一个分支：enabled走`T07E→D07E→I07E→G07E`；off走
  `T07O→D07O→I07O`，并在G09P同时有效后审`G07O`。G07E失败不能自动视为G07O通过。
- [ ] G07E满足数值SLO：base completion≥1.2×arrival、base backlog≤7天清零、oldest正常
  ≤24h/high≤72h、1/7/30-day backlog/cost与用户填写cap；审source freshness、request ledger、
  provider独立授权和单线程。
- [ ] G07O证明production/session/launcher都强制LLM disabled、应用层routing fail closed、UI可见，
  且主/备provider进程级network deny；G07O没有到Canary B的合法边。

## Phase 8（retention、容量与运维安全）— 状态：pending

### 8.1 修复与分析

- [ ] 修复 `_project_root`/`project_root` retention prune 属性错误。
- [ ] 建立逐表/逐索引容量分析工具，缺少 `dbstat` 时有安全替代方案。
- [ ] 审计 evidence `raw_text` 与 `span_json` 的重复存储。
- [ ] 设计 stdout/stderr/JSONL 轮转和保留策略。
- [ ] 审计 `.env` ACL 与外部 LLM 数据边界。
- [ ] disk-full 只用 faulting VFS/facade 或硬 quota 独立 scratch 注入，禁止填满 C: 或共享
  temp volume。
- [ ] secret/token/cookie/credential/`.env` value永不采集。正文默认不采集；获批raw evidence
  只进D Gate冻结的approved sink，具备精确SID ACL、静态加密、无reparse/cloud-sync、Gate
  disposition后7天且采集日起30天TTL；仓内只存opaque ID/脱敏统计/不可逆验证标识。

### 8.2 Gate 8

- [ ] 不自动删除旧 DB 备份。
- [ ] 所有 destructive cleanup 单独列出并等待用户授权。
- [ ] retention 测试只使用 tmp 目录和假时钟。
- [ ] EV-S01、EV-S02、EV-S03覆盖secret注入、非法root/宽ACL/未加密/reparse与TTL/audit-hold/精确清理；
  “保存完整日志”不能绕过先脱敏和证据生命周期规则。
- [ ] 独立“数据容量/安全审查 agent”确认没有隐含 cleanup、索引空间预算充分、ACL 与
  日志策略可执行。`PASS` 完成 H8；下一合法节点由唯一 DAG决定。

## Phase 9（集成测试与端到端恢复演练）— 状态：pending

### 9P 生产执行封装（必须在任何 G10C 前完成）

- [ ] `T09P/D09P/I09P/G09P` 实现并验证真正 one-shot/max_cycles=1；禁止以 resume 后计时
  强杀冒充。
- [ ] 提供 session-only、非持久化的 stage/batch/LLM/scan/export/prune overrides；生产
  config hash 前后不变。
- [ ] 定义外部 trust anchor 与内容寻址、对worker identity不可写的release；首段非OS代码不在
  live worktree，被验证代码不能自验。manifest覆盖VBS/PowerShell/Python/lazy modules/
  interpreter，拒绝reparse、verifier tamper和check-load TOCTOU；code/data roots分离。
- [ ] 定义机器可执行Canary/CycleWriteContract：schema/contract/run/stage/cycle/generation、plan/
  release/config/routing/auth、DB identity/schema/recovery point、candidate+source ID/hash、RPO/RTO；
  每operation的typed composite PK/columns/prior row、exact file/prior hash/root、actual touched上限。
  DB commit与file publish前验证changeset+staging inventory，违规rollback+pause。
- [ ] 交付并测试静态`operation_contracts.v4.json`消费、动态`operation_contract.schema.json`、
  `authorization_manifest.schema.json`与review confirmation；每个OP必须唯一匹配catalog，N/A只能
  使用该operation枚举reason，高风险/写操作必须REQUIRED或BOUND_COMPENSATION。
- [ ] 交付 protected write-intent journal：显式 init、exact path/ACL/version、atomic append/replace、
  flush/fsync、hash-chain、crash reconcile和retention；ordinary worker/canary打开为zero DDL。
- [ ] source写由OS/sandbox拒绝；LLM-off主/备provider network deny；RPO/RTO不能替代写前拒绝。
- [ ] 提供正交reset/resume-session/arm/LOGIN_COMMITTED/final activation；CAS后dormant launcher
  无commit token零启动，final activation不启动当前session。
- [ ] Registry实现真实atomic create-if-absent与exact conditional delete；普通check-then-set或
  mutex单独都不合格。两个真实进程竞争、第三方替换和取消注销必须测试；无法证明则
  G12B-PRE必须FAIL，主流程记BLOCKED。
- [ ] T09P必须从`test_id_registry.v4.json`逐ID解析`introduced_at=T09P`及其condition，执行该节点
  全部concrete IDs；后续 Gate 按每ID的`required_green_at/revalidate_at`选择。禁止owner×due
  笛卡尔推导或手写prefix范围替代test selection。
- [ ] 以上任一代码/测试/wrapper 在 G10C 后变化，必须重开 G09P、G09、G10C。

### 9.1 测试矩阵

- [ ] unit、contract、performance、fault-injection、Windows control tests。
- [ ] config doctor 与生产配置只读校验。
- [ ] 源目录不变性快照测试。
- [ ] pause/resume/stop/start、stale lock、PID reuse。
- [ ] 数据库 migration 幂等、失败回滚、空间不足。
- [ ] mutant 只在 throwaway worktree/运行时注入；结束验证 candidate commit、源码 SHA 和
  clean diff。ENOSPC 不得通过填满真实卷模拟。

### 9.2 端到端演练

- [ ] 完全 tmp 环境完成：启动 → scan → normalize → fingerprint → sections → LLM stub → export → pause。
- [ ] 故意中断各阶段并恢复。
- [ ] 证明没有无限重启、重复扫描或源文件写入。

### 9.3 Gate 9

- [ ] 全套测试通过且结果归档。
- [ ] 没有无法解释的 config 或 production catalog 变更。
- [ ] 所有已知高风险项有 disposition。
- [ ] 至少两名独立 agent 分别进行“端到端证据审计”和“对抗式故障/回滚审查”；必须
  证明测试能捕获目标回归且所有 P0/P1 已关闭，才能进入 G10C。

## Phase 10（核心与发布两次跨域独立 Agent 审计）— 状态：pending

### 10.1 G10C 三份 Core-only prompt

- [ ] G10C-SQL只读G00/G01/G02A/selected exact G02B/G03/G04/G05/G09P/G09，抽查G01、
  G02A、selected G02B、G09；禁止G06/G07/G08/A/B/12A/12B输入。
- [ ] G10C-CONTROL读取同一集合，抽查G03/G04/G05/G09P/G09；审checkpoint/circuit/Job/
  wrapper/trust/dormant-login tmp E2E，不要求生产canary。
- [ ] G10C-TESTOPS读取同一集合，抽查G00/G09P/G09；审red→D→I→G、fault/mutation/tmp/
  ledger。三份唯一computed next均为D11A。

### 10.2 G10R 三份 Release-only prompt

- [ ] G10R-SQL-PERFORMANCE、G10R-CONTROL-LIFECYCLE、G10R-TESTOPS使用满足DAG exact
  role/cardinality/disjoint规则的三名agent与同一exact release join：still-valid
  G09P/G09/G10C/G11A/G11J、条件G11M、A1/A2/A3、G06、enabled route G06P、G08、exact
  G07E或G07O、条件G11M-L、enabled时BP与连续BF实例。
- [ ] 三份都禁止D12A/G12A/12B输入，唯一computed next为D12A；详细独立prompt见
  `implementation_agent_prompts.md`，不得退回G10C/G10R共享模板。

### 10.4 审查 Gate

- [ ] 每个Gate三个 Agent 均提交machine review JSON与书面findings，带文件/行号/优先级。
- [ ] 实施者逐项响应：接受、拒绝并说明理由、或延期并定义风险。
- [ ] 至少一名 Agent 在修订后进行二次复核。
- [ ] 不允许实施者自己替代独立审查角色。
- [ ] `G10C` 在G09P/G09后审核Core Recovery；三名reviewer通过后**只允许D11A**，不能
  直接批准canary、真实LLM、观察或自启动。
- [ ] `G10R`只在still-valid G09P/G09/G10C/G11A/G11J、A1/A2/A3、exact LLM profile所需
  G07E+各provider canary或G07O、G06/启用格式G06P、G08及条件migration全部通过后进行；
  三名reviewer通过后**只允许D12A**。
- [ ] 两次审计都是对逐节点审查的追加总审计，不能替代任何较早 Gate。
- [ ] G10C/G10R分别保存独立证据revision；禁止写“两个审计都通过后才可任何生产对照”
  形成循环依赖。P0/P1为零且对应审计三人通过后，只走唯一DAG的下一条边。

## Phase 11（生产只读对照与单周期 Canary）— 状态：pending

### 11.1 D11A → OP11A → G11A 只读对照

- [ ] worker 继续 paused、自启动继续 off。
- [ ] 新查询与独立、可分块且有资源上限的参考实现比较 document IDs 和顺序；禁止在
  生产库运行旧的无边界灾难查询。
- [ ] 获取 warm/cold-ish 性能与query plan。ADR-02=`NO_INDEX`时G11A必须直接满足正常10秒
  production deadline；ADR-02=`INDEX`时只允许在预声明deadline内得到`INDEX_REQUIRED`，且必须
  证明缺少冻结索引、没有语义差异，并用独立分块oracle/有界只读查询得到100%一致ordered IDs。
  `INDEX_REQUIRED`不是性能PASS，只能开放D11M。
- [ ] 核对 orphan root/location、DB 空间和 migration 前置条件。
- [ ] D11A先冻结每条SQL/参数/deadline/connection/sentinel；OP11A只执行该清单；G11A至少
  两名独立agent分别复核SQL语义/source freshness与生产只读安全。任一FAIL禁止后续分支。

### 11M 条件 D11M → OP11M → G11M

- [ ] 仅ADR-02=INDEX时实例化；NO_INDEX从G11A进入D11J，D11M没有ledger record；INDEX在
  G11M后也必须进入D11J。两个分支都不得直接进入D11B-A1。
- [ ] `D11M` 在任何 DDL 前审核用户授权、当前一致恢复点、RPO/RTO、实测峰值空间、显式
  operator migrator 和失败命令。
- [ ] 普通 `CatalogStore` open 是 verify-only；`_DDL`/additive migration 不得在 login/
  worker startup偷偷构建大索引，使用 DDL-denying authorizer 测试。
- [ ] OP11M只执行冻结migrator；G11M审核幂等、中断、磁盘不足、schema/index与恢复证据；
  通过后必须用与G11A相同的生产只读协议重跑新查询，并满足正常10秒deadline/plan预算；否则
  G11M FAIL。通过后才进入D11J，不能直接进入D11B-A1。

### 11J D11J → OP11J → G11J protected write-intent journal

- [ ] D11J两名 reviewer 在首个写 canary 前冻结 exact journal path identity、批准 SID ACL、
  schema/version、append/replace原子性、flush/fsync、hash-chain、crash reconciliation、TTL与恢复。
- [ ] OP11J只执行一次显式初始化，不写生产catalog/source/config/registry、不启动worker；动态
  operation contract必须列exact created object和RPO seconds=0、RTO seconds≤1800。
- [ ] G11J两名按DAG声明与OP执行者disjoint的reviewer核对sentinel、ACL、reparse/cloud-sync排除、断电/半写恢复，以及普通
  mode=`rw`的catalog/journal open仍zero DDL。G11J失败时A1没有合法入口。

### 11.2 Canary A：三个独立 D/OP/G

- [ ] 先做数据库级可恢复快照/备份策略审查。
- [ ] 分别执行`D11B-A1→OP11B-A1→G11B-A1`、`D11B-A2→OP11B-A2→G11B-A2`、
  `D11B-A3→OP11B-A3→G11B-A3`；A1 scan-only，A2 normalize/persist-only(3–10 IDs)，
  A3 full-cycle-no-LLM。每个D使用新run ID/授权/contract/evidence revision。
- [ ] 每个`CanaryWriteContract`冻结当前恢复点/RPO/RTO、candidate/root IDs、DB operation+
  exact PK+columns+before/after+max touched rows、exact file operation/prior hash/max bytes、
  禁止DDL/ATTACH/unsafe PRAGMA/trigger与失败disposition；未列即拒绝。
- [ ] SQLite authorizer只作table/op第一层；commit前验证changeset。wrong-PK、无WHERE、错误列、
  净零DELETE+INSERT、历史文件覆盖和reparse escape全部必须rollback+pause；commit后独立重算。
- [ ] 人工启动真正 one-shot，不启动无限 supervisor；scan/export/prune/LLM 按子阶段显式
  off，不能由完整周期意外触发大范围写入。
- [ ] 源目录必须由受限身份、只读副本或受审 sandbox 主动拒写；只有事后 sentinel 时
  `BLOCKED`。
- [ ] A1/A2/A3始终`LLM_DISABLED + NETWORK_DENY`；没有任何到真实provider的隐式出边。
- [ ] 监控 queue_select、parser、LLM、state checkpoint、源文件不变性。
- [ ] 失败立即保持 paused，收集证据，不自动反复重试。
- [ ] 每个OP结束后先persistent pause、进程0，再由两名未参与操作的独立agent分别审
  数据/source与runtime/rollback；前一G未PASS不得进入下一D，A3不能补签A1/A2。

### 11.3 Canary A 出口

- [ ] 对应阶段 one-shot成功；A2/A3至少3个冻结candidate normalize artifact正常增加。
- [ ] state 和 worker_runs 落盘。
- [ ] scan 不无故重复。
- [ ] 无 heartbeat timeout、无源文件修改、无不可解释 DB 异常。
- [ ] 每个阶段结束后persistent pause、进程0、独立review payload/hash写ledger。
- [ ] unexpected operation/PK/column/file/touched delta、未授权egress或source write未被权限
  拒绝均为P0。

### 11.4 Canary B：每个 provider 单独 D/OP/G

- [ ] 只有G11B-A3+G07E及条件G11M-L通过才可进入primary
  `D11B-BP→OP11B-BP→G11B-BP`；G07O没有到B的合法边。
- [ ] 每个最终启用fallback依序走`D11B-BFnn→OP11B-BFnn→G11B-BFnn`；未通过者最终禁用。
- [ ] BP/BF每阶段都取得新的、仅一次run的授权manifest：provider/model、opaque roots/data、
  document IDs、fields、per-document/total字符/token/费用、timeout、retention/jurisdiction、
  destination、issued/expiry/revocation；primary授权不传fallback。
- [ ] 每个D另冻结stage独立write contract与恢复点：typed composite PK/columns/prior state、
  exact file/root/prior hash、request-ledger/artifact/cache/usage/runtime/checkpoint写、actual touched、
  RPO seconds=0、exact RTO seconds≤1800及precommit/post-read。CAN-BP-W01、CAN-BF-W01、
  CAN-B-W02与WRITE-F测试均通过。
- [ ] 每次OP真正one-shot，结束立即pause并由两名非operator reviewer签对应G；任何B授权
  不延续到12A或12B。

## Phase 12（人工观察与恢复决策）— 状态：pending

### 12.1 D12A → OP12A → G12A 暂不启用自启动的观察

- [ ] 只有G10R后才可D12A；D冻结exact release/profile/命令/observer/stop authority/limits。
  OP12A使用`resume-session`运行同一profile至少2小时；circuit open时命令必须拒绝，不能
  顺带reset。
- [ ] 若启用真实 LLM，必须在 12A 重新取得持续处理授权：全部主/备 provider、数据类别/
  roots、fields、文档/字符/token、时间、费用、destination与retention/jurisdiction；它是12A
  stage-bound新manifest，Canary B授权不沿用。默认profile为LLM off+network deny。
- [ ] 连续至少 5 个完整周期。
- [ ] 每周期在transaction前物化exact documents/source/write contract/hash；周期内新文档延后，
  每周期独立transaction，禁止两小时长事务。G12A逐周期审全部合同并重算至少一个changeset；
  OBS-W01、OBS-W02、OBS-W03与WRITE-F测试全部通过。
- [ ] CPU、内存、I/O、backlog、scan interval 和日志正常。
- [ ] pause 能在 SLA 内生效。
- [ ] 观察结束先 persistent pause、worker/supervisor/parser=0、自启动 off，再开始 G12A。
- [ ] **Gate 12A：**至少两名独立 agent 审查完整观察窗口、资源曲线、backlog 趋势、
  五个周期和 pause SLA；通过仅表示“可提出恢复自启动建议”，不构成授权。

### 12.2 G12B-PRE → 逐操作D/OP/G → G12B-POST

- [ ] 所有前置 Gate 通过。
- [ ] 独立审查关闭所有 P0/P1。
- [ ] G12B-PRE两名reviewer核验exact profile、外部trust anchor、不可写内容寻址release、完整
  manifest/interpreter、code/data roots、Run exact bytes、registry条件机制与回退。自验launcher、
  verifier tamper或check-load TOCTOU未关闭时FAIL。
- [ ] 12B的LLM profile必须与G12A相同。默认off；enabled需全新
  `stage=G12B_LOGIN_AUTOSTART`授权manifest，逐项含主/备provider、data/fields、per-doc/daily/
  monthly documents/characters/tokens/cost、retention/jurisdiction/destination、expiry/revocation，
  并绑定release/config/routing。Canary B/12A授权不得复用；G07O只能off。
- [ ] 用户先批准exact Run value与完整12B authorization manifest hash；LLM-off仍需该stage
  operation授权，只是provider scopes为空且egress=`DENY_ALL`，不得把整个OP写成N/A。此时
  尚不批准注销。先由D12B-ARM两人冻结arm action，再由D12B-RB两名满足DAG
  rollback/startup角色与disjoint约束的reviewer冻结并hash绑定exact compensation；补偿合同未PASS
  时OP12B-ARM没有合法入口。之后才可OP12B-ARM→G12B-ARM，token默认15min/硬30min，绑定
  value/release/data/profile/auth/generation/SID/nonce；arm不启动/reset/写registry。
- [ ] OP12B-ARM在写control/token前先向G11J protected journal写入action intent、expected registry
  absence、exact desired bytes hash、ownership/run nonce、generation与预期补偿，写后finalize；
  G12B-ARM之后再走
  D12B-CAS两人→OP12B-CAS→G12B-CAS两人。使用真实atomic create-if-absent写exact
  REG_SZ。CAS后必须`ARMED_ON_PRELOGIN/ON`；没有有效LOGIN_COMMITTED时任何意外login/reboot
  child/DB/config/source/egress为0。mutex或check-then-set单独不合格。
- [ ] ARM token在CAS提交点一次性消费；CAS后使用默认24h/硬72h dormant lease。从OP12B-ARM
  起，ARM/lease过期、ARM/CAS/post-review/login异常、crash partial或用户取消都只触发已预审的
  `OP12B-RB→G12B-RB`：按journal intent/finalize与ownership nonce reconcile、pause+invalidate token，且仅
  current exact bytes匹配本次值才conditional delete；第三方值不碰并进入
  `PAUSED/REGISTRY_CONFLICT`。CAS时同名值即使bytes相同也算冲突，不得接管。只读Gate和launcher
  不得自行rollback，禁止自动重试；G12B-RB必须继承OP exact terminal state。
- [ ] 不新增计划任务或服务。G12B-CAS通过后先D12B-LOGIN两人审LOGIN_COMMITTED默认5min/
  硬10min、review hashes/final approval/SID/machine+boot generation/previous session/“该SID下一次
  新logon”关系/generation绑定与取消rollback；不得预填尚不存在的future session ID。然后用户再次
  确认已保存工作并批准立即注销，才允许OP12B-LOGIN。
- [ ] login validation仅一冻结周期后自动persistent pause；两名post reviewer审G12B-POST。
  成功状态只为LOGIN_VALIDATED_PAUSED/ON、process0；失败只触发OP12B-RB→G12B-RB；不得RECOVERED。

### 12.3 D12C → 用户授权冻结intent → G12C-PRE → OP12C → G12C 最终启用下一登录

- [ ] 用户看到G12B-POST摘要后先进入D12C；两名满足DAG role/cardinality/disjoint规则的reviewer
  核验只读前置并冻结OP12C/OP12C-RB sealed contract与唯一proposed action/intent hash，不能审查
  尚不存在的授权。之后用户另行批准`G12C_FINAL_AUTOSTART_ACTIVATION`，授权逐字绑定该intent
  hash、action ID、generation/Run/release/auth/expiry。未批准时保持`SAFE_PAUSED_WAITING_USER`，
  不是BLOCKED。G12C-PRE由恰好3名DAG-disjoint、不同角色reviewer重验actual授权/ledger head，
  无P0/P1且circuit closed才唯一开放OP12C。
- [ ] OP12C只CAS control state为ENABLED_IDLE/ON并generation+1、消费一次性token；process0，
  token/control写前先向protected journal写action-intent/auth/generation/expected state/ownership
  nonce，完成后finalize，crash只由OP12C-RB reconcile；不启动当前session、不reset/resume/arm、
  不写registry/config/DB/source、不改LLM。
- [ ] G12C由恰好3名满足DAG exact角色/基数/disjoint规则的reviewer审control/circuit、release/auth/security、operations；
  ACT-S01、ACT-S02、ACT-S03、ACT-S04、ACT-S05、ACT-S06、ACT-S07全通过时物理state前后均为`ENABLED_IDLE/ON`，只新增
  `lifecycle_outcome=RECOVERED`。OP12C或G12C失败只能走`OP12C-RB→G12C-RB`，两名按DAG与
  OP执行者disjoint的reviewer继承并核对OP终态：owned Run未漂移时回
  `LOGIN_VALIDATED_PAUSED/ON`；第三方Run冲突时不碰registry并进`PAUSED/REGISTRY_CONFLICT`。
  当前session运行需未来另建D/OP/G。
- [ ] 此后普通下次登录只有在重新验证G12C outcome、release/auth/config/routing/data/Run、SID、
  circuit、Job Object和单实例后才能`ENABLED_IDLE→RUNNING_AUTOSTART`；任一失败零child并PAUSED/ON。
- [ ] G12C以后每个cycle在任何DB/file/network前都按`runtime_cycle_policy`密封新的operation
  contract：绑定action-intent/auth、generation/process、journal head、exact document/source tuples、
  DB/file write set、egress与持久daily/monthly caps，并重验expiry/revocation。`ACT-S08`验证第二/
  后续cycle不复用旧合同，`ACT-S09`验证过期/撤销/超cap拒绝，`ACT-S10`验证wrong PK/file/
  journal head在commit/egress前失败。任一失败circuit open+persistent pause，且registry/config/
  source零写；G12C的历史PASS不能豁免逐cycle合同。

### 12.4 Circuit reset side lane

- [ ] 任何生产circuit open只能实例化下一个未用`05R01`–`05R99`：D05Rnn两人→OP05Rnn→G05Rnn
  两人。D冻结root cause、用户token、failure generation、TTL、exact `D` return node与全部
  downstream invalidation；return不能是G/OP/占位符，必须是失败节点合法祖先。
- [ ] OP只清active latch/budget、generation+1并保留历史，仍PAUSED/process0；G确认20s进程0、
  registry/config/DB/source/release/auth不变。G之后只能回冻结的exact D，无直接resume/arm/login边。

### 12.5 延后并入主线

- [ ] 本计划在用户明确要求前保持独立。
- [ ] 未来并入主线时先做去重、冲突和状态迁移审查。
- [ ] 不直接复制已过时行号或结论；重新验证代码现状。

## Errors Encountered

| 日期 | 错误 | 尝试 | 处理 |
|---|---|---:|---|
| 2026-08-22 | 计划编制期间若干补丁上下文/读取参数不匹配 | 各1次 | 未产生越界写；逐项记录在`progress.md`后按精确上下文完成 |
| 2026-08-22 | ledger schema首轮负例未拒绝`evidence/../manifest.md` | 1 | 收紧path segment regex；8个正/负schema样例与meta-schema随后全部PASS |

## 计划状态总览

| Phase | 名称 | 状态 |
|---:|---|---|
| 00L | ledger validator bootstrap | pending |
| 0 | 实施前重新基线化 | pending |
| 1 | 生产规模回归夹具与基线测试 | pending |
| 2 | normalize queue SQL 与索引 | pending |
| 3 | 扫描 checkpoint | pending |
| 4 | SQL 可取消性与遥测 | pending |
| 5 | supervisor backoff 与熔断 | pending |
| 6 | 扫描性能与电源策略 | pending |
| 6P | Parser 分格式 profile | pending |
| 7E/7O | LLM enabled / 强制 off 互斥分支 | pending |
| 8 | retention、容量与运维安全 | pending |
| 9P | 生产 one-shot/override/pinned-release 封装 | pending |
| 9 | 集成测试与恢复演练 | pending |
| 10C/10R | 核心/发布跨域独立审计 | pending |
| 11A/11M/11M-L/11J | 生产只读、条件迁移与protected journal | pending |
| 11B-A1/A2/A3/BP/BFnn | 分阶段/逐provider canary | pending |
| 12A/12B-PRE/ARM/RB/CAS/LOGIN/POST/12C | 人工观察、dormant登录验证、补偿与最终激活 | pending |
