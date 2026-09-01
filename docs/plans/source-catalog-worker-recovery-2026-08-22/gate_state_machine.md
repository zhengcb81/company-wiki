# Source Catalog Worker — v4 唯一 Gate 状态机与执行 DAG

> `gate_dag.v4.json` 是机器可读的唯一节点/入边/reviewer-cardinality 来源；本文件是其规范性
> 人类可读解释。两者有任何不一致，semantic validator 必须 `DAG_CONTRACT_MISMATCH` 并停止。
> Phase 编号仅用于分组。实施者一次只能领取 validator 计算出的一个合法节点。

## 1. 节点、状态、独立审查

### 1.1 节点类型

| 前缀 | 含义 | 可做的事 | 独立审查 |
|---|---|---|---|
| `T` | test-only commit | 只改冻结白名单内的测试、fixture、test helper | 后续 `D` 必须由未参与 T 的 agent 审 |
| `D` | Design Review | 只读；冻结设计、测试、白名单、授权/操作合同、回滚、阈值 | 成功人数与角色必须恰好等于DAG；普通1名、高风险2名 |
| `I` | implementation commit | 只改该 WP 白名单；不得改 D 后测试 | 后续 `G` 必须由未参与 T/D/I 的 agent 审 |
| `OP` | 参数和授权均冻结的操作 | 只能产生该节点合同列出的状态变化 | 前置 D/G 与后置 G；operator 不能当 reviewer |
| `G` | 决策/Exit/Audit Gate | 只读；验证证据并决定是否开放唯一出边 | 成功人数与角色必须恰好等于DAG；G10C/G10R/G12C-PRE/G12C各3名 |

禁止裸 `G10`、`G02A/B`、泛称 `G11B`、`BF00`、未编号“子 Gate”或自造节点。`BFnn`
只表示模板；实例只能是 `BF01`–`BF99`。合法 `node_id` 以 `gate_dag.v4.json` 与
`gate_ledger.schema.json` 的交集为准。

“每个关键节点独立 agent 审查”的可执行含义：

1. 每个 T/I 对都有独立 D 和 G；每个生产 OP 都有独立 pre-review 与 post-review；
2. reviewer 的 `agent_id` 与 role 必须匹配DAG exact set、彼此不同，且不得等于
   T/I/OP agent/operator；DAG声明的跨节点disjoint/min-not-in也必须满足；
3. reviewer 只能只读，不能修改代码、测试、计划、证据或 ledger；
4. reviewer 必须原样输出符合`review_result.schema.json`的JSON与Markdown；落盘后由同一
   reviewer另出符合`review_confirmation.schema.json`的detached read-back confirmation；
   payload/report/confirmation actual hash全部一致，主agent不能自行把布尔值填成true；
5. 缺 reviewer、重复 agent、hash 未确认、开放 P0/P1 时，validator 不开放下一边。

### 1.2 状态和值域

```text
READY -> IN_PROGRESS -> PASSED | PASSED_WITH_P2 | BLOCKED
任一已通过节点 -- code/test/evidence/authorization/plan drift --> INVALIDATED
```

- v4 删除 `NOT_SELECTED`。未选分支没有 ledger record；决策只写在合法 ADR Gate 的
  `branch_decision`，validator 据此删除另一分支出边。
- Reviewer verdict 仅为 `PASS | PASS_WITH_NONBLOCKING_FINDINGS | FAIL`；
  `PASSED_WITH_P2` 只能含 P2/P3、owner 和 due node。
- `READY/IN_PROGRESS` 可以还没有 reviewer；不得携带完成 verdict/evidence/next edge。
- `PASSED` 必须所有 reviewer `PASS`、hash confirmed、无 open finding；`PASSED_WITH_P2`
  必须所有 reviewer 为 PASS/PASS_WITH、至少一个 PASS_WITH、且仅开放 P2/P3。
- `BLOCKED/INVALIDATED` 的下一节点集合必须为空。branch、reviewer 数量和下一边不能相信
  record 自报，必须由 semantic validator 从 DAG 与全部有效历史重算。

### 1.3 普通实现协议与唯一基线例外

普通实现 WP：

```text
Txx -> Dxx -> Ixx -> Gxx
```

`T01 -> D01 -> G01` 是唯一 `TEST_BASELINE_ONLY` 例外：T01 只能包含 fixture、test 和 test
helper；G01 时旧产品的目标性能红灯仍必须存在。若公开接口无法测，D01 `FAIL`，必要 seam
随 SQL 修复进入 I02A。D 后任何 test/fixture/assertion 变化使 D 与下游失效。

## 2. Ledger semantic validator bootstrap

任何 worker 预检、代码 WP、生产 OP 或正式 `gate_ledger.jsonl` 追加之前，先走：

```text
T00L -> D00L -> I00L -> G00L
  -> D00 -> OP00 -> G00
```

- T00L 冻结`GL-S01`、`GL-S02`、`GL-S03`、`GL-S04`、`GL-S05`、`GL-S06`、
  `GL-F01`、`GL-F02`、`GL-F03`、`GL-F04`、`GL-F05`、`GL-F06`、`GL-F07`、
  `GL-F08`、`GL-F09`、`GL-F10`、`GL-F11`、`GL-F12`、`G10-PROMPT-S01`及
  `gate_ledger_validator_vectors.v4.json`；同时验证DAG/vectors/test-registry/operation-catalog
  各自的instance schema，`{}`、`[]`、scalar等shape负例必须失败；只用tmp文件。
- D00L 由 1 名独立 reviewer 验证负例确实因控制面缺陷而红，且没有接触生产状态。
- I00L 实现 deterministic、只读 `validate_gate_ledger`；其输入只能是 frozen plan manifest、
  DAG、schema 和 append-only ledger，输出稳定 reason code；不能执行节点或修复 ledger。
- I00L产生独立`validator_release_manifest.v1.json`，冻结validator代码/tests及运行时hash；v4
  plan manifest只冻结实施合同，不可能预先冻结未来脚本。
- I00L后先生成canonical bootstrap transcript候选（到I00L为止）并预计算head；G00L两名
  reviewer的`input_ledger_head_sha256`必须绑定该head，各自逐个运行全部正负例、shape负例和
  mutation并回读确认。通过后才把同一transcript初始化为正式ledger、追加G00L并全链回读；
  只有D00L review允许null input head。
- 每次 append 前后都运行 validator。ledger schema不含任何next字段；出现
  `next_eligible_nodes`、`claimed_next_eligible_nodes`或同义字段即拒绝。下一节点只能由
  validator的只读`next`命令计算。

## 3. Core Recovery Lane

### 3.1 核心实现顺序

```text
G00
  -> T01 -> D01 -> G01
  -> T02A -> D02A -> I02A -> G02A
  -> G02B-ADR

G02B-ADR[branch_decision=NO_INDEX]
  -> T02B-NI -> D02B-NI -> I02B-NI -> G02B-NI

G02B-ADR[branch_decision=INDEX]
  -> T02B-IDX -> D02B-IDX -> I02B-IDX -> G02B-IDX

exactly_one(G02B-NI, G02B-IDX)
  -> T03 -> D03 -> I03 -> G03
  -> T04 -> D04 -> I04 -> G04
  -> T05 -> D05 -> I05 -> G05
  -> T09P -> D09P -> I09P -> G09P
  -> T09 -> D09 -> I09 -> G09
  -> G10C
  -> D11A -> OP11A -> G11A
```

`G02B-ADR` 是两名独立 reviewer 的只读决策 Gate。它基于 G02A 的语义、跨 SQLite 版本、
无 stats、N/2N、空间与写放大证据冻结 `ADR-02`、benchmark hashes、支持矩阵和唯一
`NO_INDEX|INDEX` 值；不得改测试或实现。只有选中的分支随后创建自己的 T commit。

两个分支共享 schema lifecycle 合同，但测试提交彼此独立：

```text
ordinary open:
  exact existing schema -> success, zero DDL
  missing DB            -> SCHEMA_INIT_REQUIRED, zero file creation
  old schema            -> SCHEMA_UPGRADE_REQUIRED, zero DDL

operator-only:
  schema init    --profile NO_INDEX|INDEX
  schema upgrade --profile NO_INDEX|INDEX --to <exact-version>
```

ordinary worker/login/canary 路径不得调用 init/upgrade。INDEX 生产迁移仍只能在 G11A 后的
`D11M→OP11M→G11M` 执行；I02B-IDX 只交付工具及 tmp/恢复副本证据。
Phase 0 必须把`tests/contract/test_zr1002_reader_first.py`和
`tests/contract/test_zr1003_shadow_assertions.py`纳入基线；选中02B分支的T/I提交把其tmp夹具改为
先显式init/upgrade再reader open，并由`M-COM-S05`、`M-COM-S06`证明产品ordinary reader没有
eager DDL。不得为了保留旧测试行为恢复隐式建库。

G10C 由三名互相独立、且未参与实现的 reviewer 分别审 Core SQL/性能、控制/安全、测试/
运维。它只开放 D11A，不授权 canary、真实 LLM、观察、reset、自启动或长期激活。

### 3.2 G09P 强制交付

G10C 前必须在全 tmp E2E 中验证：

- one-shot/max-cycles/stage-only、session-only overrides；
- 独立外部 trust anchor、不可写内容寻址完整 release/interpreter/lazy modules；
- reparse escape、check-load TOCTOU、child restart drift 全部 fail closed；
- code/data/config/catalog/runtime/source roots 分离，source OS/sandbox write deny；
- LLM-off 对 primary/fallback 的进程级 egress deny；
- `operation_contracts.v4.json`覆盖每个OP/family；`operation_contract.schema.json`、
  `authorization_manifest.schema.json`覆盖exact state/generation/auth/write/precommit/post-read；
- protected write-intent journal的显式init、ordinary mode=rw零DDL、ACL/fsync/hash-chain/crash reconcile；
- reset-only、resume-only、arm-only、login-commit、activation 五种动作分离；
- registry true create-if-absent/exact conditional-delete 双进程语义；
- `ARMED_ON_PRELOGIN`、分层ARM/dormant lease/LOGIN_COMMITTED token、显式12B/12C compensation、
  final activation pre/post review；
- approved evidence sink 的脱敏、ACL、加密、HMAC、TTL；safe fault/mutant helper。

这些代码/contract 在 G10C 后漂移会使 G09P、G09、G10C 及全部下游生产节点失效。

## 4. Canary A 与条件 index migration

G11A 后按已冻结 ADR-02 分流：

```text
G11A[NO_INDEX] -> D11J -> OP11J -> G11J -> D11B-A1
G11A[INDEX]    -> D11M -> OP11M -> G11M -> D11J -> OP11J -> G11J -> D11B-A1

D11B-A1 -> OP11B-A1 -> G11B-A1
  -> D11B-A2 -> OP11B-A2 -> G11B-A2
  -> D11B-A3 -> OP11B-A3 -> G11B-A3
  -> persistent PAUSED/OFF
```

G11A 的性能判定按分支不同但语义门相同：`NO_INDEX`必须在G11A直接满足生产只读新查询的
10秒deadline和正常plan预算；`INDEX`允许G11A在冻结deadline内返回受界、预声明的
`INDEX_REQUIRED`诊断，前提是缺少ADR-02冻结索引得到证明、没有语义差异，且独立分块oracle/
只读有界查询仍100%给出相同ordered IDs。它不是性能PASS或超时豁免，只开放D11M。G11M后必须
在同一生产只读协议下重新运行新查询并满足正常10秒deadline/plan预算，否则G11M FAIL，不能进入D11J。

- A1=`scan-only`；A2=`normalize/persist-only` 且 3–10 个冻结 document IDs；
  A3=`full-cycle-no-LLM`。
- 每个 D 单独冻结 run ID、授权、候选/root、operation/PK/column/exact-file、实际 touched 上限、
  RPO/RTO、恢复点、one-shot 命令、失败 disposition；每个 OP 后先 PAUSED/OFF、进程归零并
  changeset 对账；每个 G 由 2 名非 operator reviewer 审，不能事后合并签字。
- A lane 永远 `LLM_DISABLED + NETWORK_DENY`。
- `D11J→OP11J→G11J` 必须在第一个生产写 canary 前初始化独立、受保护的 write-intent
  journal。D11J 冻结 exact path identity、ACL SID、格式/version、atomic append/replace、fsync、
  hash-chain、crash reconciliation、retention 和恢复合同；OP11J 只创建该对象；G11J 以两个
  按DAG `reviewer_independence`/`min_not_in`/`forbidden_agent_sets`约束且与OP执行者
  disjoint的 reviewer 核对 ordinary mode=`rw` 时仍为 zero DDL。禁止把 journal lazy-create 混进
  worker startup、Canary A 或生产 catalog DB。

## 5. Hardening lanes 与 Canary B convergence

G05 后可以在隔离 worktree 准备；运行项目测试仍为单线程：

```text
Lane H6: T06  -> D06  -> I06  -> G06
         T06P -> D06P -> I06P -> G06P
Lane H7: G07-ADR[LLM_ENABLED] -> T07E -> D07E -> I07E -> G07E
         G07-ADR[LLM_OFF]     -> T07O -> D07O -> I07O; I07O + G09P -> G07O
Lane H8: T08 -> D08 -> I08 -> G08
```

`G07-ADR` 由 2 名独立 reviewer 冻结且只冻结一个 release mode；它只读、不得调用 provider。
`exactly_one(G07E,G07O)`。G07O 没有到真实 provider canary 或 LLM migration 的出边。

LLM-enabled 路径只有在 Canary A 完成后才判断 request-ledger schema：

```text
G11B-A3 + G07E -> G11M-L-ADR

G11M-L-ADR[branch_decision=NO_SCHEMA_DELTA] -> D11B-BP
G11M-L-ADR[branch_decision=SCHEMA_DELTA]
  -> D11M-L -> OP11M-L -> G11M-L -> D11B-BP
```

`G11M-L-ADR` 由 2 名独立 reviewer 核对 G07E 冻结 schema contract 与 G11B-A3 的真实生产
schema；只有二者同时有效才有入口。任何 `G07E -> D11M-L` 直接边非法。schema 变化不得
进入 eager startup DDL。

Canary B：

```text
D11B-BP -> OP11B-BP -> G11B-BP
  -> [D11B-BF01 -> OP11B-BF01 -> G11B-BF01]
  -> [D11B-BF02 -> OP11B-BF02 -> G11B-BF02] ...
  -> persistent PAUSED/OFF
```

- BP 为 primary；每个最终启用 fallback 按冻结顺序实例化 BF01–BF99。未实例化节点没有
  ledger record，未通过节点从 release profile 禁用。
- 每个 D 取得新的 stage/provider-bound 一次性授权，并冻结 provider/model、opaque roots/
  data/fields/document IDs、字符/token/费用、retention/jurisdiction/destination、RPO/RTO 和
  exact `CanaryWriteContract`（operation/PK/columns/files/touched/precommit/post-read）。
- 每个 OP 一次性运行后立即 PAUSED/OFF；primary 授权不能传 fallback，B 授权不能传 12A/12B。

## 6. Release Join 与 12A

```text
RELEASE_CANARY = G11B-A1 + G11B-A2 + G11B-A3
  + exactly_one(
      LLM_OFF: G07O,
      LLM_ENABLED:
        G07E + G11M-L-ADR[NO_SCHEMA_DELTA] + G11B-BP + every enabled G11B-BFnn
        | G07E + G11M-L-ADR[SCHEMA_DELTA] + G11M-L + G11B-BP + every enabled G11B-BFnn
    )

RELEASE_HARDENING = G06 + G06P for every enabled parser route + G08
  + still-valid G09P + G09 + G10C + G11J
  + G11M when ADR-02=INDEX

RELEASE_CANARY + RELEASE_HARDENING
  -> G10R
  -> D12A -> OP12A -> G12A
```

G10R 的exact join必须显式包含仍有效的`G09P`与`G09`。三名reviewer分别审
release/performance/lifecycle，并严格满足DAG声明的角色、基数和disjoint约束；不能复用G10C报告，
但也不得把“全新”解释成DAG没有声明的全局永久排除。
它只开放 D12A。D12A 冻结 exact release/profile、观察窗口、停止权限、资源/成本 envelope、
初始恢复点和 RPO/RTO。OP12A 每个 cycle 在任何 transaction 前必须物化并 hash 绑定
`CycleWriteContract`：cycle/run、candidate IDs、operation/PK/columns/files、touched limits、
RPO/RTO、authorization hash。未物化、漂移或错 PK 必须 precommit rollback + pause。

G12A 只接受连续至少 5 个完整周期且 wall≥2h；任一失败窗口从零重算。结束必须
PAUSED/OFF、进程 0。通过不授权 Run、自启动、注销或长期运行。

## 7. 12B dormant login canary 与 12C 最终激活

### 7.1 12B 唯一链

```text
G12A
  -> G12B-PRE
  -> explicit user approval of exact Run value + 12B profile/auth
  -> D12B-ARM
  -> D12B-RB  (pre-review and seal exact compensation contract before any ARM state write)
  -> OP12B-ARM -> G12B-ARM
  -> D12B-CAS -> OP12B-CAS -> G12B-CAS
  -> D12B-LOGIN
  -> user confirms saved work and explicitly authorizes immediate logoff
  -> OP12B-LOGIN -> G12B-POST
  -> LOGIN_VALIDATED_PAUSED/ON

after OP12B-ARM, any ARM/CAS/post-review/login/lease failure, conflict or cleanup request
  -> OP12B-RB -> G12B-RB
  -> PAUSED/OFF | PAUSED/REGISTRY_CONFLICT
```

- 12B 默认 LLM off。enabled 时必须有全新 `G12B_LOGIN_AUTOSTART` authorization；Canary B/
  12A 不可复用。它绑定 exact release/config/routing、每个 provider/model、opaque data/fields、
  per-doc/daily/monthly caps、retention/jurisdiction/destination、issued/expiry/revocation/hash。
- D12B-ARM、D12B-CAS、D12B-LOGIN 各由 2 名非 operator reviewer 预审 exact operation、
  rollback 与授权边界；各G的reviewer必须满足DAG声明的角色/基数/disjoint规则，不把“不同”
  扩张成DAG未声明的全局排除。
- D12B-RB 由 2 名独立 rollback/startup reviewer 在任何ARM状态写之前冻结并 hash 绑定补偿合同；它不执行
  rollback。OP12B-RB 才能 invalidate token、按 exact prior bytes conditional-delete，随后
  G12B-RB 只读核对并逐字继承OP终态。目标值在CAS时已存在（即使bytes相同）或之后被第三方
  替换时都不得删除或覆盖，终态为 `PAUSED/REGISTRY_CONFLICT`。
- OP12B-ARM 先向G11J冻结的protected journal追加绑定action-intent hash、control generation、
  expected registry absence、exact desired bytes hash、ownership/run nonce与预期补偿的intent记录，
  再创建prelogin arm state；不启动、不 reset、不写 registry。ARM token 默认
  TTL 15min、硬上限 30min，并在 OP12B-CAS 的提交点一次性消费；到期进入显式 OP12B-RB，
  不能原地延期。CAS 后改用 dormant lease（默认24h、硬上限72h）；lease 到期只触发零启动、
  persistent pause 与 OP12B-RB，不允许 launcher 自删 registry 或自动重试。
- OP12B-CAS 用真实 atomic create-if-absent 写 exact Run value；随后状态只能是
  `ARMED_ON_PRELOGIN/ON`。launcher 在没有有效 `LOGIN_COMMITTED` 时必须零启动，因此 CAS 后到
  用户保存工作之间不存在意外 reboot/login 启动窗口。
- `LOGIN_COMMITTED` 只能由 OP12B-LOGIN 在 D12B-LOGIN 及最终用户批准后创建；默认 TTL
  5min、硬上限 10min，绑定 exact generation、release/Run/auth hash、用户 SID、machine/boot
  generation、上一个 session identity、该 SID 的“下一次新 logon”关系、D12B-LOGIN review
  hashes、最终批准记录与 nonce；不得假装预知尚未创建的 future session/LUID。token 一次原子消费，随后立即
  发起获批 logout。缺失、过期、漂移、重放、并发消费或未获批 login 一律零启动。
- login canary 只运行一个冻结 cycle，随后 persistent pause，保留 exact Run entry，状态
  `LOGIN_VALIDATED_PAUSED/ON`。G12B-POST 由 2 名 reviewer 审；不得写 `RECOVERED`。
- ARM token、registry value、control state与journal不是一个原子资源，因此每次状态写前必须有
  durable intent、写后必须有finalize；crash恢复只能按ownership/run nonce、expected prior bytes和
  journal head重放幂等reconcile。OP12B-ARM、G12B-ARM、D12B-CAS及其后的任一失败边都只能进入
  已预审的OP12B-RB；禁止无journal的猜测性删除、覆盖或原地继续。

### 7.2 12C 独立长期激活

```text
G12B-POST
  -> D12C
  -> freeze exact proposed action/intent hash + OP12C/OP12C-RB contracts
  -> explicit user authorization bound to that exact intent hash
  -> G12C-PRE
  -> OP12C
  -> G12C
  -> physical state ENABLED_IDLE/ON + lifecycle outcome RECOVERED

OP12C or G12C failure after any state write
  -> OP12C-RB -> G12C-RB
  -> LOGIN_VALIDATED_PAUSED/ON | PAUSED/REGISTRY_CONFLICT
  -> lifecycle outcome ROLLED_BACK
```

- D12C 由2名满足DAG角色/基数/disjoint规则的reviewer核对G12B全链、无drift、circuit closed、
  exact release/profile/Run value、资源/成本cap与rollback，并先冻结OP12C/OP12C-RB同一sealed
  contract及唯一proposed action/intent hash；D12C不假装审查尚未产生的授权。随后用户授权必须
  逐字绑定该intent hash、action ID、generation和expiry。G12C-PRE由3名不同角色reviewer对已落盘的exact user
  authorization、contract、release 与 ledger head 做最后只读预审；它才唯一开放 OP12C。
- OP12C 的唯一 CLI action 为 `activate-autostart-final`：以 generation CAS 将
  `LOGIN_VALIDATED_PAUSED/ON` 改为 `ENABLED_IDLE/ON` 并消费一次性 activation token；进程仍为
  0。token/control跨资源提交前先向protected journal追加绑定action-intent/auth/generation/
  expected state/ownership nonce的intent，完整提交后finalize；crash只能由OP12C-RB按journal
  reconcile。它不得启动当前 session、reset、resume、arm、写 registry/config/DB/source 或改变 LLM。
- G12C 由3名满足DAG exact role/cardinality/disjoint约束的reviewer（control/circuit、
  release/auth/security、operations）观察至少20s，
  核对 process=0、generation只增1、Run与全部sentinel不变。G12C 是只读 Gate，记录前后物理
  状态都必须是 `ENABLED_IDLE/ON`；它只把 `lifecycle_outcome` 记为 `RECOVERED`。任何失败由
  预授权`OP12C-RB`执行generation CAS，`G12C-RB`两名DAG-disjoint reviewer再核对并继承OP
  exact terminal state，Gate自己不写状态。若Run已被第三方替换，RB不得改registry，终态必须为
  `PAUSED/REGISTRY_CONFLICT`而不是伪报`LOGIN_VALIDATED_PAUSED/ON`。
- 用户不批准长期激活时，安全终态就是 `LOGIN_VALIDATED_PAUSED/ON`，不是 blocker。若未来
  还要求当前 session 立即运行，必须另建新的 D→OP(resume-session)→G 任务，本计划不顺带做。
- G12C之后每次普通登录及每个后续cycle都受`runtime_cycle_policy`约束：在任何DB/file/network
  操作前密封本cycle operation contract，绑定authorization/action-intent、control generation、
  process identity、journal head、exact document/source tuples、DB/file write set、egress与daily/
  monthly caps；逐cycle重验expiry/revocation和持久cap。`ACT-S08`、`ACT-S09`、`ACT-S10`必须覆盖
  第二/后续cycle、授权或cap失效、wrong PK/file/journal head。任一失败均circuit open并persistent
  pause，不写registry/config/source；不得因G12C曾PASS而沿用旧合同。

## 8. Circuit reset 的唯一生产路径

生产 `reset-circuit` 禁止在 DAG 外调用。只在 circuit open、进程 0、persistent PAUSED 时：

```text
... production failure + circuit open
  -> D05Rnn -> OP05Rnn -> G05Rnn
  -> reset manifest 冻结且 validator 验证的 exact D return_node
```

- 每次实例化唯一`05R01`–`05R99`，同一ID/token不得复用。D05Rnn由2名独立reviewer审
  root-cause/failure generation、修复或撤回 release、历史预算、
  exact reset manifest、用户授权与回归目标；不能审完就 resume。
- OP05Rnn 只清 active latch/budget、generation+1并保留全部历史；最终仍 PAUSED，进程0；
  不启动、不 arm、不写/删 registry、不创建 LOGIN_COMMITTED、不改 LLM 或 release。
- G05Rnn由2名满足DAG exact角色/基数/disjoint规则的reviewer核对reset-only差分；它只把控制权送回需重新执行的exact D，
  永远没有到 OP12A/OP12B/OP12C 或 resume 的直接边。
- reset manifest 必须绑定 failure generation、唯一 `D` return node、全部 downstream
  invalidation、token expiry 和用户授权 hash。return node 必须是失败节点的合法祖先；任何
  `G`/`OP` 返回值、占位符或无法从 DAG 重算的返回值都由 validator 拒绝。
- 普通 resume/resume-session/arm/login/activate 遇 open circuit 必须 `CIRCUIT_OPEN` 且状态、
  generation、latch、registry 不变。

## 9. 生产控制状态转换

| 当前状态 | 合法节点/动作 | 唯一允许结果 | 失败/禁止 |
|---|---|---|---|
| PAUSED + circuit open | OP05Rnn（已通过同编号D05Rnn） | PAUSED、generation+1、历史保留 | 无resume/arm/registry/LLM副作用 |
| PAUSED + circuit open | 其他 resume/arm/login/activate | 原状态；`CIRCUIT_OPEN` | 绝不顺带reset |
| PAUSED/OFF + closed | OP12B-ARM | ARMED_PRELOGIN/OFF | 不启动、不写registry |
| ARMED_PRELOGIN/OFF | OP12B-CAS | ARMED_ON_PRELOGIN/ON | conflict→PAUSED/REGISTRY_CONFLICT；即使同bytes也不接管，不覆盖第三方 |
| ARMED_ON_PRELOGIN/ON，无commit | 任意boot/login | 不启动、保持dormant | 不消费旧token、不自动重试 |
| ARMED_ON_PRELOGIN/ON | OP12B-LOGIN | LOGIN_COMMITTED/ON→一次login canary | token TTL/绑定/原子消费失败则零启动 |
| login canary完成 | persistent pause | LOGIN_VALIDATED_PAUSED/ON | 不自动长期运行 |
| LOGIN_VALIDATED_PAUSED/ON | OP12C | ENABLED_IDLE/ON且process=0 | 只在D12C冻结intent→用户授权该hash→G12C-PRE后；不启动当前session |
| ENABLED_IDLE/ON + `RECOVERED` | 下一次正常登录/每个cycle | RUNNING_AUTOSTART/ON | 每cycle先密封runtime contract并重验auth/cap/journal/write/egress；失败→circuit open+PAUSED/ON且零未授权副作用 |
| ARM后任一失败/lease到期 | OP12B-RB→G12B-RB | PAUSED/OFF或PAUSED/REGISTRY_CONFLICT | 只能按journal+ownership exact conditional-delete；Gate继承OP终态且不写状态 |
| OP12C/G12C失败 | OP12C-RB→G12C-RB | LOGIN_VALIDATED_PAUSED/ON或PAUSED/REGISTRY_CONFLICT | generation CAS；第三方Run不动；Gate继承OP终态 |
| 任一运行态 | persistent pause | PAUSED；按合同保留/撤回Run | 禁止裸PID误杀 |

Registry mutex 只能辅助；不能冒充 create-if-absent/conditional-delete。平台不能证明真实原子
语义时 G12B-PRE 必须 FAIL。所有 control state 写使用 generation CAS、atomic replace 和故障恢复。

## 10. 漂移、ledger 与下一状态算法

- `plan_manifest.v4.json`、`gate_dag.v4.json`、三个 instance schema、`test_id_registry.v4.json`、
  `operation_contracts.v4.json`、`operation_contract.schema.json`、`authorization_manifest.schema.json`、
  `gate_ledger.schema.json`、`review_result.schema.json` 与 `review_confirmation.schema.json` 是冻结
  控制面；新 revision 新文件名，禁止覆盖历史 manifest。
- 正式 ledger 为 append-only JSONL，`seq + prev_record_sha256 + supersedes_seq`；更正只追加。
- 每条记录先过 JSON Schema，再由 G00L 交付的 validator 校验：manifest/DAG hash、node/type、
  branch、全入边、reviewer 数量/独立性/hash、finding 级别、commit/evidence/auth binding、
  production state、hash chain、漂移和唯一下一边。
- reviewer 不写 ledger；主 agent 保存原 payload/hash，reviewer 回读确认后才 append。
- authorization 过期/撤销/stage/hash drift 使依赖 OP/G 失效；不得沿用早期授权。
- implementation 中的动态事实只进 evidence、ledger 与非规范性 progress；不得回写冻结核心。

弱模型固定算法：

1. 校验 v4 manifest 自身 hash及全部核心/source hashes；
2. 使用 G00L 已通过的 validator 重放 ledger；失败立即停止；
3. 只接受 validator 输出的唯一 `eligible_nodes`，不能信任 progress/checkbox/自报 next；
4. 核对 branch、全部前驱、用户授权、reviewer payload/hash与 production state；
5. 一次领取一个 T/D/I/OP/G；D 后不改测试，OP 后按合同先 pause（仅 OP12C 除外）；
6. 只有 `optional_external_successor` 的用户授权尚未给出时保持声明的安全 waiting outcome，
   不追加伪 `BLOCKED`；其他无合法边或 drift 才追加 BLOCKED/INVALIDATED，禁止猜测或跳 Gate；
7. 任一关键节点缺独立 agent review，就没有下一条合法边。
