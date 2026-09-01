# Source Catalog Worker — 数值验收阈值与统计合同

> 这些是 v4 的默认最低标准。D Gate 可基于新基线提出更严格值；放宽必须有 ADR、全部
> 原始数据和独立 reviewer 批准。实施者不得在失败后临场改阈值或换分母。

## 1. 通用统计方法

- P50/P95 使用 nearest-rank：排序后取 `ceil(p × n)` 的 1-based 样本。
- 报告全部样本，不删除 outlier；按预声明环境规则作废的样本仍保留并解释。
- 性能比较固定机器、电源、Python/SQLite、fixture seed/schema/topology、instrumentation 与
  运行顺序；不能用历史单次生产日志替代同协议 baseline。
- SQL warm `n>=30`；cold-ish `n>=10` 且以 `max` 判定。Scanner 每情景 baseline/candidate
  各 `n>=10`。Windows 状态序列至少 20 个确定性序列或完整状态表。
- 样本合同不足时不能声称 P95 通过；只能 `BLOCKED` 或将对应功能 fail closed。

## 2. SQL queue

### 2.1 绝对与复杂度预算

- 25k documents/50k locations 生产形状 fixture：warm P95 `<2.0s`；
- cold-ish：新进程、新 connection、SQLite page cache冷但不声称 OS cache全冷，10 次
  `max<10.0s`；
- production read-only新查询正常deadline为`10s`。`NO_INDEX`在G11A首个超限即失败；`INDEX`
  在G11A仅可于预声明deadline内返回`INDEX_REQUIRED`（缺ADR-02冻结索引、语义由分块oracle/
  有界只读查询100%验证），该诊断不算性能PASS且只开放D11M；G11M后同一查询必须在`10s`
  内满足正常plan预算，首个超限即失败；
- 旧查询只在 tmp、受 progress handler 中止，最大 wall `2s` 或冻结 VM budget；
- N=5k/10k/20k/40k 同分布缩放：每次翻倍的 VM proxy `<=2.8x`、wall median `<=3.0x`；
- 任一规模出现 correlated status-index-per-document 坏 plan，直接失败。

### 2.2 SQL work 可比性合同

D01 必须冻结且只选择一个 `measurement_mode`：

1. `PROGRESS_PROXY_APPROX`：`approx_vm_work = callback_count × progress_n`。它只是 SQLite
   progress callback 的近似可比代理，禁止声称 `true_steps` 上下界或 exact instruction count；
2. `STMTSTATUS_VM_STEP_EXACT`：仅在使用可审计 native binding 读取
   `SQLITE_STMTSTATUS_VM_STEP`、完整消费结果、处理 >2^31-1 边界且能在中断后可靠读取时使用；
   否则必须回退 approximate mode。

两种模式都记录 Python/SQLite version+source-id、binding/harness hash、PRAGMAs、query params、
LIMIT、fixture digest、prepare/consume 边界。proxy 模式还记录 `progress_n` 和 handler 安装点；
old/new、全部 N、warm/cold-ish 必须使用同一 harness/n。复杂度结论必须同时依赖 plan、N/2N
scaling 与 wall samples；progress handler 可作 deadline/work guard，不能单独证明精确步骤数。

- 测量 callback 不读文件、不查 DB、不轮询 control；D04 的取消 callback 是另一套 harness。
- wall benchmark 分别报告有/无 measurement handler，防止 measurement overhead 污染。
- metadata 或 n 任一跨样本变化，Q-P01/Q-P05 必须失败；proxy evidence声称 exact 区间时
  Q-P06 必须失败。

### 2.3 语义与 source freshness

- ordered IDs 与独立 oracle 100% 一致；force/non-force、parseable primary、retry/terminal、
  generator/version、duplicate locations 零差异。
- current normalized artifact 必须同时匹配 document、generator/version/schema/status、
  `artifact.source_id=documents.primary_source_id`、
  `artifact.source_sha256=sources.content_sha256`，且 payload binding 一致。
- S1→S2 后旧 source 的 completed/terminal/retry artifact 不得抑制 S2；UPSERT 原子更新
  source ID/hash。旧记录可留审计，但不得充当 current。

## 3. SQLite progress handler 与 pause

- 正常快查询相对无 handler：median overhead `<=max(5%,5ms)`；P95
  `<=max(10%,10ms)`；
- query 开始后由另一真实进程写新 pause/stop generation：P95 `<=5s`、max `<=10s` 中断；
- deadline/pause/stop reason 不混淆；callback 不执行 SQL，且能观察 query 开始后的状态；
- D04 冻结 instruction interval 与 control poll interval，默认 control poll `250ms–1s`；
- handler 在下一查询前 100% 清除，任一次泄漏为 P1。

## 4. Parser 格式与样本合同

### 4.1 路由清单、样本与 timeout

D06P 首先从候选 `_normalize_source` 生成 route digest；v4 基线必须逐项覆盖：

| Code | route/extension | S `<10MiB` | M `10–100MiB` | S目标/hard timeout |
|---|---|---:|---:|---:|
| 01 | plain text `.txt,.md,.csv` | 每extension≥5，总n≥20 | n≥10或显式禁用 | P95<10s / 30s |
| 02 | HTML `.html,.htm` | 每extension≥5，总n≥20 | n≥10或显式禁用 | P95<10s / 30s |
| 03H | MHT HTML part `.mht` | n≥20 | n≥10或显式禁用 | P95<10s / 30s |
| 03T | MHT text fallback `.mht` | n≥20 | n≥10或显式禁用 | P95<10s / 30s |
| 04P | PDF fallback/PyMuPDF `.pdf` | n≥20 | n≥10或显式禁用 | P95<60s / 120s |
| 04D | Docling artifact for PDF | n≥20 | n≥10或显式禁用 | P95<60s / 120s |
| 05 | python-docx `.docx` | n≥20 | n≥10或显式禁用 | P95<30s / 90s |
| 06 | antiword `.doc` | n≥20 | n≥10或显式禁用 | P95<30s / 120s |
| 07 | openpyxl `.xlsx` | n≥20 | n≥10或显式禁用 | P95<30s / 90s |
| 08 | xlrd `.xls` | n≥20 | n≥10或显式禁用 | P95<30s / 90s |
| 09 | python-pptx `.pptx` | n≥20 | n≥10或显式禁用 | P95<30s / 90s |
| 10J | structured JSON `.json` | n≥20 | n≥10或显式禁用 | P95<10s / 30s |
| 10X | structured XML `.xml,.xsd` | 每extension≥5，总n≥20 | n≥10或显式禁用 | P95<10s / 30s |
| 99 | unsupported suffix | ≥20 | n/a | parser启动数0 |

- S 用 nearest-rank P95；M 用 max 主判。若 M 禁用，`P-DIS-<code>-M` 至少 5 个边界样本证明
  parser 未启动；不能静默缺 bucket。O=`>100MiB`/结构上限以 `P-LIMIT-<code>-O` 每route≥5。
- 每个适用 route 的 corrupt=`P-ERR-<code>-C`、encrypted=`P-ERR-<code>-E`，各 n≥10；不适用
  也必须有 `P-NA-<code>-<class>` 理由。每个执行 route 的 `P-PAUSE-<code>` n≥20；antiword
  必须证明 grandchild 回收。cleanup 10s graceful、20s total。
- 重复文档不算独立样本；warm-up 不计 n。任何 enabled route 缺样本/超阈值，release profile
  必须禁用；`P-FMT00-ROUTE` 验证代码路由、测试 registry、enablement 三者完全一致。
- 每样本记录 size、页/sheet/cell/slide、wall/CPU/peak memory、exit/error class；不删 outlier。
- 无代表性 fixture 的格式不得 PASS，只能由 D06P 明确禁用并以 fail-closed 测试转绿。

## 5. Supervisor、backoff 与 circuit

- 只有完整 cycle success 清 active global/per-signature failure budget；scan checkpoint、
  heartbeat、VM activity、parser start 都不能清零；
- backoff：base `5s`、multiplier `2`、cap `300s`、jitter `0–20%`，测试注入 RNG；
- 同一 signature 连续 3 次失败、任意 signature 30min 内 5 次失败，或首次 child start 后
  无完整成功超过 `max(30min,2×configured_cycle_budget)`：circuit open；
- latch/counters 跨 child/supervisor/login/reboot 持久。`resume`、`resume-session` 和 arm 永远
  不清 circuit；open 时三者返回 `CIRCUIT_OPEN` 且不启动。
- 只有单独 `reset-circuit` 可清 active latch/budgets；前置为完整 control、PAUSED、进程0、
  明确 operator 授权。reset 后仍 PAUSED，不启动、不 arm、不改自启/LLM，并保留历史 audit。
- pause 在 startup delay/backoff 中 P95 `<=5s`、max `<=10s`；120s logon delay 每 session
  最多一次；child restart增量 delay=0。
- Job Object create/assign失败 fail closed；supervisor异常退出后20s内无 orphan parser。

## 6. Scanner

### 6.1 Release topology

- 约244 company walks、16,570 group/sidecar单元、429 Dropbox-like dirs、9,853 groups、
  46,600 files；含层级、中文、长路径、sidecar、junction和 offline root。
- CI可按固定比例缩放；G06 release benchmark必须完整 topology，不能用 flat root。

### 6.2 同拓扑 baseline/candidate

- baseline 绑定 exact `BASE_COMMIT`；若需新埋点，先形成 instrumentation-only revision，再
  从它分叉旧/新机制。
- 两边 topology manifest/seed/logical digest/depth/sidecar/churn set、instrumentation hash、
  machine/power/Python/filesystem/AV/indexing 状态完全一致。
- 每场景旧/新各 `n>=10`，预声明 warm-up 与交替顺序；新进程运行，不删 outlier。
- `candidate_P95<=120s` 且 `baseline_P95/candidate_P95>=2.0`；历史427s仅作参考，不能作分母。
- 同时比较阶段计数、DB delta与source manifest，禁止靠跳目录/文件换性能。
- 1% changed、10% churn 分别报告 enumerate/sidecar/fetch/observe/hash/commit；阶段无未解释
  `>25%` 回归。battery disabled时昂贵 enumeration files_seen=0；offline root不批量retire。

### 6.3 Metadata tamper

- unchanged `(path,size,mtime_ns,sidecar-signature)`可按合同 reuse；
- 每日确定性审计 `>=3.34%` 内容 hash，保证每文件最长30天 rehash；高风险变化即时 hash；
- audit 不修改 source content/size/mtime/ACL。

## 7. LLM queue、请求账本、吞吐与授权

### 7.1 默认模式

- 所有自动测试、Canary A、未逐项授权的 OP：`LLM_DISABLED + NETWORK_DENY`；
- cost cap/provider allowlist/data scope 任一为空即 fail closed；fallback 不继承 primary 授权；
- G07O 只能进入 LLM_OFF release profile，不能执行 Canary B。

### 7.2 Queue/cache/current source

- 每 document 最多一个 current completed normalized input；除了版本/status，还必须匹配当前
  primary source ID/hash与 normalized artifact ID/hash；dedupe 在 LIMIT 前。
- summary 只有 source binding、normalized ID/hash、canonical request digest、generator/version/
  status 全匹配才抑制。S1 summary 不得抑制或被包装成 S2。
- cache key 是截断后 exact canonical request + system prompt + provider/model + generation params +
  routing contract digest；只复用已验证 provider payload，每 document 重新绑定 artifact/locator。

### 7.3 Durable request ledger

```text
PREPARED -> IN_FLIGHT
IN_FLIGHT -> RESPONSE_VALIDATED -> COMPLETED
IN_FLIGHT -> RETRYABLE_FAILED | PERMANENT_FAILED | OUTCOME_UNKNOWN
IN_FLIGHT found after restart -> OUTCOME_UNKNOWN
```

- 网络前 PREPARED 记录 request digest、document/source binding、provider/model、authorization hash、
  idempotency key与最大成本 reservation；正文/prompt不入账本。
- `RETRYABLE_FAILED`只允许用于可证明请求未被接受的失败，或provider支持同一idempotency key
  的安全retry/result lookup；普通post-send timeout、连接中断、含糊5xx不得自动标retryable。
- 遗留或结果不确定的IN_FLIGHT一律OUTCOME_UNKNOWN，不自动重发。只有provider可验证同一
  idempotency key/result lookup时可reconcile；否则人工处置，再发需新授权。
- RESPONSE_VALIDATED后的本地artifact/cache commit可以幂等重放，但不得再次调用provider。
- OUTCOME_UNKNOWN 的最大预计费用继续占 cap；响应先验证并不可变落盘，再对账 artifact/cache/
  usage。不能承诺 provider 不支持时 exactly-once billing。

### 7.4 吞吐 SLO

- D07E 冻结 low/base/high arrival/service；base completion `>=1.2×arrival`；base backlog
  `<=7days` 清零；oldest正常 `<=24h`、high `<=72h`；
- 1/7/30-day backlog、失败、字符、token、成本数值化；daily/monthly cap 用户未填不得启用；
- 以成功 artifact/真实 wall clock计吞吐，不以 batch ratio代替。

### 7.5 Stage-bound authorization manifest

Canary BP/BF、12A、12B 各使用全新、不可复用的 manifest。LLM_OFF 的这些生产 OP 仍需要
stage-bound operation authorization；只是provider scopes为空、egress=`DENY_ALL`，不得把整个
OP写成N/A。只有`operation_contracts.v4.json`为安全操作枚举的N/A reason才合法。12B schema至少包含：

```text
authorization_id/schema/hash; stage=G12B_LOGIN_AUTOSTART; issued/expiry/revocation;
release/config/routing fingerprints; primary and each fallback provider/model;
opaque roots/data classes/fields/exclusions; per-doc/daily/monthly document/character/token/cost caps;
retention/jurisdiction/terms; egress destinations
```

stage/hash/release/config/provider/cap/expiry/revocation任一不匹配即零外发、pause并使 Gate失败。
Arm、runtime、request ledger和post evidence只记录 authorization hash，不记录正文/secret。
LLM_OFF 保留主/备 egress deny。

## 8. Retention、容量与 migration

- ENOSPC 只用 faulting VFS/file facade或硬quota独立scratch；禁止填满 C:/共享temp；
- migration free space `>=1.25×恢复副本实测峰值额外空间 + max(20GiB,卷容量15%)`；现有
  恢复点不计可删除空间；
- 普通 store open在DDL-denying authorizer下verify-only；大索引/ledger schema只能显式迁移；
- ZR1002/ZR1003的tmp fixture必须先显式init/upgrade再reader open；`M-COM-S05`/`M-COM-S06`
  分别证明显式路径幂等和普通reader/worker/login/canary零DDL，禁止恢复产品eager init；
- destructive retention默认0个生产删除；另行用户授权前不执行。

## 9. CanaryWriteContract

每个 A/B D 节点及 12A 每个 cycle 在任何 transaction 前冻结机器可执行 contract：

```text
contract_schema_version/contract_id/parent_run_id/stage/cycle_id/control_generation
plan_manifest/release/config/routing/auth hashes; database_identity/schema_hash/recovery_point_id
DB: table -> INSERT|UPDATE|DELETE -> exact typed composite-PK set -> allowed columns
    -> expected prior row version/hash/absence -> before/after invariants -> max_actual_touched_rows
files: canonical exact path/template -> CREATE|REPLACE|DELETE|RENAME
       -> expected prior hash/absence/root identity -> max actual bytes/files
candidate document IDs + source_id/source_sha256; RPO/RTO; rollback/reconcile disposition
forbidden DDL/ATTACH/unsafe PRAGMA/trigger/source/config/.env writes
```

- 默认拒绝；SQLite authorizer只作table/op第一层，不能验证WHERE/PK。
- PK 是规范化、类型化 composite-key 集合，不能用 `WHERE status=...` 等开放 predicate。
  `max_actual_touched_rows`是实际触达行，不是净变化。A2/A3/B/12A绑定exact documents及source；
  A1绑定root IDs；DELETE/覆盖默认禁止。
- commit 前核验 changeset的operation/PK/changed columns/脱敏before-after digest/run ID；违规
  rollback+pause。文件guard解析reparse最终路径并用exclusive create/expected hash防覆盖。
- 文件先写 run-private 不可见 staging；DB changeset+staged inventory验证后才commit/exclusive publish。
  DB/file不能原子提交时用append-only intent/finalize ledger；crash只能reconcile，不重调provider。
- commit 后用独立读取路径重算；`rpo_seconds=0`（pre-run已提交数据零丢失/未授权改变），默认
  `rto_seconds≤1800`；放宽需D Gate+用户批准。恢复点不能替代pre-commit拒绝。
- 首个生产写canary前，`D11J→OP11J→G11J`必须建立受保护write-intent journal；exact path/
  ACL/version、atomicity、fsync、hash-chain、crash reconcile均通过。ordinary mode=`rw`打开
  catalog/journal时DDL数必须为0。
- 任一 unexpected operation/PK/column/file/delta、第二实例、未授权egress/query timeout立即
  pause，Gate失败。source write必须被OS/sandbox permission拒绝。
- G12C后的每个普通登录/cycle也必须在任何DB/file/network前实例化同一严格度的runtime
  operation contract，并额外绑定action-intent、process identity、journal head与持久daily/monthly
  caps；每cycle重验authorization expiry/revocation。前一cycle或G12C的PASS不得复用为合同。

## 10. Release identity 与 Registry

### 10.1 外部 trust anchor

- HKCU Run的首段非OS代码不得位于普通可写worktree；trust anchor独立于被验证release，
  G12B-PRE冻结absolute path、hash/signature、ACL和exact Run value。
- 禁止被验证代码自验。release内容寻址且对worker identity无write/delete/rename/write-DAC；
  manifest覆盖完整启动链、interpreter与lazy modules，拒绝reparse escape。
- check后必须从同一不可写快照加载；每次child restart重验。tamper/TOCTOU/drift→不启动、
  persistent pause、按exact value条件回退。无法建立该边界则G12B-PRE必须FAIL，主流程
  记BLOCKED。

### 10.2 Registry conditional create/delete

- 禁止`Get/Test -> New-ItemProperty -Force`；named mutex只能辅助，不能冒充原子CAS。
- 条件创建在提交点仅当目标name缺失才写exact key/name/REG_SZ/value/arm digest；并发 loser
  不覆盖。任何既有同名值（即使bytes相同）都是ownership conflict，不得接管。条件删除仅当
  提交点exact bytes与ownership/run nonce仍匹配本次值。
- ARM token绑定release/data root/LLM profile/authorization hash/value/generation/user SID/expiry/
  nonce；默认15min、硬上限30min，并在CAS提交点一次性消费。CAS后建立默认24h/硬72h的
  dormant lease，状态必须是`ARMED_ON_PRELOGIN/ON`：没有另一个有效
  LOGIN_COMMITTED token时，任何boot/login只能让trust launcher零child、零DB/config/source/
  registry额外写、零egress后退出。
- LOGIN_COMMITTED 只能在D12B-LOGIN两名reviewer与最终保存工作/注销批准后创建；默认5min、
  硬上限10min，绑定review hashes、final approval、expected SID、machine/boot generation、
  previous session与该SID“下一次新logon”关系，不预知future session/LUID；一次原子消费。重放/
  漂移/过期100% fail closed。
- conflict、异常、用户取消、ARM/lease过期、login timeout：只能进入预审的
  `OP12B-RB→G12B-RB`；OP pause/invalidate token，本次值仍精确匹配才删，第三方值不同则
  不碰并进入`PAUSED/REGISTRY_CONFLICT`；Gate/launcher不写registry，禁止自动重试。
- D12B-RB必须在任何ARM state/token写前PASS。OP12B-ARM先向G11J journal写入action intent、
  expected absence、desired bytes hash、ownership/run nonce、generation与补偿目标，再写arm state
  并finalize；从该点起任一失败/crash partial均按journal reconcile后走OP12B-RB，G12B-RB继承
  OP exact terminal state，不得事后把REGISTRY_CONFLICT重写成OFF。
- 真实并发测试只用 disposable test hive/key。API无法证明条件语义则G12B-PRE必须FAIL，
  主流程记BLOCKED。

## 11. Raw evidence lifecycle

- secret/token/cookie/credential/`.env` value永不采集。正文默认不采集；必要时先获用户批准。
- approved sink必须在repo/workspace/普通temp/云同步之外、无reparse escape；ACL为批准SID
  allowlist，无宽泛继承；静态加密密钥与evidence分离。ACL变更需另行授权。
- repo只存opaque ID、脱敏统计、不可逆验证标识；敏感manifest用repo外key的HMAC。
- 默认Gate处置后7天删除，采集日起30天硬上限；到期未结案则BLOCKED并重新采集。audit
  hold只有用户可批准。清理只按inventory精确文件，不用recursive glob。
- 意外捕获secret为P0：停止、隔离、通知和凭据轮换；不能只移动到“受限目录”。

## 12. 两小时观察

- 连续`>=5`完整cycle且wall`>=2h`；任一失败从零重算；
- exact release/profile与G10R一致。默认LLM off；真实模式使用12A专属完整authorization；
- 无progress时单核CPU`>80%`连续5min停止；有milestone短burst可接受；
- DB/WAL/log growth、memory上限在D12A按A/B canary实测+25%余量冻结；
- pause/进程归零、source/config/egress sentinel与backlog age/drain/cost全部通过；
- OP12A 每周期独立 transaction；周期开始前先物化 exact document/source/write contract/hash，
  新到达文档延后到下周期，禁止一个两小时长事务。缺任一周期合同使G12A失败。
- 观察后先PAUSED/OFF再G12A。12B必须维持同一LLM profile，并使用新的12B授权。

## 13. Reset、登录验证与最终激活阈值

- 每次production reset使用唯一`05R01`–`05R99`对应D/OP/G与一次性token（TTL≤15min）；合同绑定
  failure generation、失败节点合法祖先中的exact D return及全部下游失效；仅清 active
  latch/budget，generation恰好+1，历史保留，进程0，状态仍PAUSED；reset后20s仍进程0。
- Dormant prelogin、LOGIN_COMMITTED drift/replay/expiry、unexpected login 各进行至少20个真实
  双进程/状态 interleaving；成功消费者恰好1，其余全部零启动。
- G12B-POST成功终态只为`LOGIN_VALIDATED_PAUSED/ON`、process0，不是RECOVERED。
- Final activation先由D12C两名reviewer冻结exact proposed action/intent hash及final/rollback
  contracts，再由用户授权该hash/action ID，最后由G12C-PRE恰好三名pre-reviewer核对actual
  authorization；顺序不可颠倒。OP12C是唯一operator动作且不接review verdict，G12C恰好三名
  post-reviewer；OP12C只CAS为
  `ENABLED_IDLE/ON`，20s内进程始终0、generation仅+1、除control state外sentinel零变化。
  token/control跨资源写必须有protected journal intent/finalize和ownership nonce，crash只按journal
  reconcile。G12C前后物理state不变，只把`lifecycle_outcome`记为`RECOVERED`；失败走
  `OP12C-RB→G12C-RB`。owned Run未漂移时回
  `LOGIN_VALIDATED_PAUSED/ON`；第三方Run冲突不碰registry并进`PAUSED/REGISTRY_CONFLICT`，G继承
  OP exact终态。当前session运行需另建D/OP/G。
- 下一普通登录只有重新验证G12C outcome、release/auth/config/routing/data/Run、SID、circuit、
  Job Object和单实例后才可`RUNNING_AUTOSTART/ON`；任一失败零child并`PAUSED/ON`。
- `ACT-S08`要求第二及每个后续cycle有新runtime contract；`ACT-S09`要求authorization过期/
  撤销或持久daily/monthly cap不足在egress/write前失败；`ACT-S10`要求错误journal head、
  document/source、typed PK/column/file在precommit失败。三者任一失败都circuit open+persistent
  pause，registry/config/source零写。
