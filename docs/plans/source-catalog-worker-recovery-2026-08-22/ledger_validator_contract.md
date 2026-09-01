# Gate ledger deterministic validator — v4 实施合同

> 本文件只定义未来实施合同，不是当前实现。当前规划阶段不得创建动态 `gate_ledger.jsonl`。
> validator 必须在 T00L/D00L/I00L/G00L 中先完成并独立审查，之后才允许 D00。

## 1. 信任边界与文件

未来实施白名单：

- `scripts/validate_gate_ledger.py`：除下述冻结的 JSON Schema 运行时外只使用 Python 标准库；
  无网络、插件、动态 import、项目业务 import；
- 独立 validator venv 中只允许固定版本的 `jsonschema`、`referencing` 及其闭包依赖；解释器绝对路径、
  Python 版本、每个 wheel/安装文件 SHA-256、导入模块实际路径、`sys.path` 精确集合与依赖树都写入
  `validator_release_manifest.v1.json`。启动时发现多一个路径、包、版本或 hash 漂移即失败；
- `tests/test_gate_ledger_validator.py`：只用 tmp ledger/review/evidence；
- 本计划冻结的 `gate_ledger.schema.json`、`review_result.schema.json`、
  `review_confirmation.schema.json`、`gate_dag.v4.json`、`operation_contracts.v4.json`、
  `operation_contract.schema.json`、`authorization_manifest.schema.json`、
  `operation_intent_manifest.schema.json`、`journal_manifest.schema.json`、
  `evidence_manifest.schema.json`、`validator_fixture_manifest.schema.json`、
  `validator_release_manifest.schema.json`、
  `parser_route_manifest.schema.json`、`test_id_registry.v4.json`、
  `gate_ledger_validator_vectors.v4.json` 及每个 instance schema；
- 动态 `gate_ledger.jsonl`、`reviews/`、`evidence/` 只在实施开始后按权限合同创建。

启动顺序：

```text
B0 使用 OS/stdlib SHA-256 核对 plan_manifest.v4.json 的外部预期 hash
B1 逐项核对计划 manifest 中的 schema、DAG、catalog、registry、vectors 与 prose contract hash；
   v4 manifest 不得声称冻结尚未实现的 validator 文件
B2 I00L 完成后生成独立 `validator_release_manifest.v1.json`，由 OS/stdlib SHA-256 冻结
   validator、其 tests、运行时和依赖；G00L reviewer 把该 manifest 的 actual hash 作为输入
B3 <冻结venv-python绝对路径> -I scripts/validate_gate_ledger.py self-test ...；只对tmp ledger执行；
   禁止 `-S`（它会移除已冻结的 schema runtime）；入口先核对解释器、sys.path、依赖文件和模块来源
B4 tmp init只允许创建T00L genesis READY；所有其他genesis负例必须失败
B5 在tmp证明append使用expected-head + exclusive lock + 全链校验 + atomic append + flush/fsync + 回读
B6 生成到 I00L terminal 为止的 canonical bootstrap transcript 候选并预计算 external head；
   G00L两名reviewer各自重算全部vectors、至少一个额外负例、该head及validator release hash
B7 两人PASS并完成detached read-back confirmation后，才把“同一候选 transcript + G00L terminal
   record”一次性初始化为正式ledger；全链、payload/report/confirmation回读后再开放D00
```

Bootstrap 期间 reviewer 的原始 payload、Markdown 与 confirmation 暂存在已批准、只追加的
bootstrap evidence 目录；G00L 通过后才初始化正式 ledger。只有 D00L review 因正式链尚未存在
可使用 `input_ledger_head_sha256=null`；G00L 两份 payload 必须绑定到 I00L terminal 为止的同一
canonical candidate head。candidate 每一字节、D00L payload hash、validator release manifest、
G00L payload/confirmation hash 都在 bootstrap evidence 中预计算并由 reviewer 回读。禁止先使用
未经验证的正式 ledger 来“证明 validator 已通过”，也禁止在 G00L 后重序列化候选记录。

## 2. Canonical serialization 与链

- UTF-8、无 BOM、LF；每行恰好一个 JSON object；不允许空行或尾随空白。
- canonical bytes：`json.dumps(obj, sort_keys=True, separators=(",", ":"),
  ensure_ascii=False)` 的 UTF-8；拒绝 float、NaN、Infinity、重复 key。
- `record_sha256 = SHA256(canonical bytes)`，不包含 LF。
- seq=1 的 `prev_record_sha256=null`；之后 seq 严格 +1，prev 等于前一 canonical hash。
- append 调用必须带外部保存的 `--expected-head`；整链被重写即使内部自洽，只要 head 不符即失败。
- `supersedes_seq` 只能引用同 revision、更早、存在的 record；不删除/覆盖原记录。下游失效按
  DAG 传递，直到相关 T/D/I/G/authorization 重新完成。
- 正式 ledger 的 genesis 是 T00L READY；任何别的首节点或多个 genesis 都失败。

## 3. 命令接口

```text
<validator-venv-python> -I scripts/validate_gate_ledger.py self-test
  --manifest <plan_manifest.v4.json> --dag <gate_dag.v4.json>
  --ledger-schema <gate_ledger.schema.json>
  --review-schema <review_result.schema.json>
  --review-confirmation-schema <review_confirmation.schema.json>
  --operation-catalog <operation_contracts.v4.json>
  --operation-contract-schema <operation_contract.schema.json>
  --operation-intent-schema <operation_intent_manifest.schema.json>
  --authorization-schema <authorization_manifest.schema.json>
  --journal-manifest-schema <journal_manifest.schema.json>
  --evidence-manifest-schema <evidence_manifest.schema.json>
  --validator-fixture-manifest-schema <validator_fixture_manifest.schema.json>
  --parser-route-manifest-schema <parser_route_manifest.schema.json>
  --test-registry <test_id_registry.v4.json>
  --vectors <gate_ledger_validator_vectors.v4.json>

<validator-venv-python> -I scripts/validate_gate_ledger.py init
  --candidate <record.json> --expected-head NONE ...

<validator-venv-python> -I scripts/validate_gate_ledger.py validate
  --ledger <gate_ledger.jsonl> --expected-head <sha> ...

<validator-venv-python> -I scripts/validate_gate_ledger.py append
  --ledger <gate_ledger.jsonl> --candidate <record.json>
  --expected-head <sha|NONE> ...

<validator-venv-python> -I scripts/validate_gate_ledger.py next
  --ledger <gate_ledger.jsonl> --expected-head <sha> ...
```

`next` 只向 stdout 输出 validator 计算的 eligible node IDs、缺失条件和 reason；不得写回 ledger。
ledger schema 使用 `additionalProperties=false`，因此任何 authored `next_eligible_nodes` 或同义
字段直接失败。

## 4. 固定验证顺序与 reason code

所有输入先完成 JSON 解析与 schema 检查。Schema error 按冻结的
`(artifact, instance-pointer, schema-pointer, keyword) -> primary reason code` 表稳定排序并重分类；
能确定属于状态、review、branch、operation 等领域的结构错误必须返回对应领域 code，只有未知
形状/无法重分类的纯结构错误才返回 E002。随后按下表顺序检查；首个确定的 primary failure
非零退出，stderr 只输出稳定 code、seq/node/case 和脱敏摘要。同一 vector case 必须恰有一个
`expected_primary_code`，不能用无 subcase 对应的 code 数组掩盖顺序歧义：

| 顺序 | Code | 必查 |
|---:|---|---|
| 1 | `GLV-E001 MANIFEST_HASH` | manifest 自身外部 hash、全部 core/source hash |
| 2 | `GLV-E002 STRUCTURAL_SCHEMA` | ledger/review JSON Schema、additionalProperties、BF01–99 |
| 3 | `GLV-E003 NON_CANONICAL_JSON` | encoding/LF/duplicate key/float/canonical bytes |
| 4 | `GLV-E004 SEQUENCE` | genesis、seq、单行完整性 |
| 5 | `GLV-E005 PREV_RECORD_HASH` | prev 与 expected external head |
| 6 | `GLV-E006 ILLEGAL_NODE_ID` | node 在 DAG，type 与 prefix 一致 |
| 7 | `GLV-E007 ILLEGAL_STATUS_TRANSITION` | READY→IN_PROGRESS→terminal；无 NOT_SELECTED |
| 8 | `GLV-E008 MISSING_PREDECESSOR` | 所有前驱、join、仍有效 Gates |
| 9 | `GLV-E009 ILLEGAL_BRANCH` | ADR exactly-one、未选分支无 record、G07O 无 B |
| 10 | `GLV-E010 REVIEWER_CARDINALITY` | DAG 精确 1/2/3 人数、agent/role 唯一、非 executor/operator |
| 11 | `GLV-E011 REVIEW_PAYLOAD_HASH` | machine payload、原 payload、stored report 实际 hash与回读确认 |
| 12 | `GLV-E012 REVIEW_VERDICT_MISMATCH` | ledger 值逐字段等于 review JSON；PASS/PASS_WITH/FAIL 合法 |
| 13 | `GLV-E013 OPEN_P0_P1` | P0/P1 必 BLOCKED；P2/P3 有 owner/due node |
| 14 | `GLV-E014 EVIDENCE_HASH` | evidence path/hash、节点/commit/run binding、ACL/TTL metadata |
| 15 | `GLV-E015 MISSING_AUTHORIZATION` | 每个 OP 的 stage/user/auth/expiry/hash；安全 OP 也写带原因的 NOT_APPLICABLE |
| 16 | `GLV-E016 ILLEGAL_PRODUCTION_STATE` | before/after、process、circuit、registry、generation 合同 |
| 17 | `GLV-E017 INVALID_SUPERSEDES` | 引用/同 revision/下游 invalidation |
| 18 | `GLV-E018 AUTHORED_NEXT_EDGE` | ledger 含任何自报 next 字段，或调用者尝试跳过 `next` |
| 19 | `GLV-E019 BF_SEQUENCE` | BF 从 01 连续、无 00/跳号/重复、只实例化启用项 |
| 20 | `GLV-E020 REVIEWER_NOT_INDEPENDENT` | reviewer 与 T/I/OP agent重合或 independence=false |
| 21 | `GLV-E021 BRANCH_RECORD_FOR_UNSELECTED` | 未选 branch 任一节点被写入 ledger |
| 22 | `GLV-E022 OP_BINDING` | run/auth/evidence/contract/generation/operation state 缺失或漂移 |
| 23 | `GLV-E023 DAG_CONTRACT_MISMATCH` | prose/schema/DAG/review schema revision/hash不一致 |
| 24 | `GLV-E024 TEST_ID_MAPPING` | registry逐ID owner/red/green/revalidate/condition、引用提取与route expansion |
| 25 | `GLV-E025 OPERATION_CONTRACT` | OP唯一catalog匹配、dynamic contract schema/hash、write set/RPO/RTO/状态差分 |
| 26 | `GLV-E026 REVIEW_ROLE_POLICY` | exact role set、跨节点disjoint/min-not-in、重复或额外 reviewer |
| 27 | `GLV-E027 BOOTSTRAP_HEAD` | null head例外、candidate transcript、validator release manifest与正式初始化 |
| 28 | `GLV-E028 ROLLBACK_PATH` | 12B/12C compensation可达性、reset exact D return、失效传播 |
| 29 | `GLV-E029 OPTIONAL_WAIT` | 缺可选最终用户批准时保持声明的安全 waiting outcome而非伪BLOCKED/前进 |
| 30 | `GLV-E030 INTENT_BINDING` | D冻结的 action/intent hash、OP stage/generation、授权和合同逐字节绑定 |
| 31 | `GLV-E031 JOURNAL_BINDING` | journal manifest/head-before/intent/finalize/head-after、半提交恢复与ACL |
| 32 | `GLV-E032 REGISTRY_CAS` | hive/SID/view/key/name/type/bytes、原值、CAS证明、ownership nonce和冲突终态 |
| 33 | `GLV-E033 RUNTIME_CYCLE` | G12C后逐cycle合同、授权/预算重验、journal、process generation和失败暂停 |
| 34 | `GLV-E034 VALIDATOR_FIXTURE` | canonical fixture hash、typed mutation、唯一primary rule和reclassification表 |

Validator 不得根据 progress、checkbox、Markdown中的“PASS”或 record 自报值推断下一节点。

## 5. Reviewer 与 evidence 语义

- 每个执行节点必须先产出符合 `evidence_manifest.schema.json` 的 `manifest.json`，并附人类可读
  `report.md`；ledger 分别绑定二者实际 hash。machine manifest 必须绑定 node/type、plan/DAG/
  validator release、base/test/implementation commit、OP run/auth/intent/contract/journal，以及每个
  artifact 的位置类别、实际 hash 或批准 sink 的 HMAC、大小、媒体类型、敏感级别、ACL、加密、
  reparse-point 检查和创建/过期时间；`secret_present` 必须为 false。reviewer 以 machine JSON 为
  验证入口并阅读 report，不得把 Markdown 当权威清单。
- 每个 reviewer 必须提供符合 `review_result.schema.json` 的 JSON payload 和只读 Markdown报告；
  保存后由同一 reviewer 重读 actual bytes，再提供符合 `review_confirmation.schema.json` 的
  detached confirmation。ledger 只复制全部三类 artifact 经 hash 校验的机器字段。
- validator 重读 payload，核对 node、input head、plan/DAG/evidence hashes、verdict、findings、
  counterexample、independence、exact assigned role、actual path/hash 与 confirmation。任何手抄
  差异、fake node/due、非 bootstrap null head或主 agent 自填确认都失败。
- D/G `PASSED`：精确 reviewer 人数、全部 PASS、hash confirmed=true、independence=true、
  counterexample_attempted=true、open_findings=[]。
- `PASSED_WITH_P2`：只允许 D/G；全部 reviewer PASS/PASS_WITH，至少一个 PASS_WITH；open
  finding 仅 P2/P3，均有 owner/due node。due node 必须是 machine DAG 中从当前节点可达、且未在
  当前节点之前完成的 exact 节点。
- BLOCKED 可因 reviewer FAIL、环境或授权不足产生；没有下一节点。INVALIDATED 必须引用被
  supersede 的旧 record并传播失效。

## 6. Branch、join 与 reset

- G02B-ADR 冻结 NO_INDEX 或 INDEX；另一分支从 T 节点开始完全不存在 ledger record。G11A 在
  NO_INDEX 分支必须达到 10 秒生产查询预算；INDEX 分支在迁移前只允许受界、只读、计划证据充分的
  `INDEX_REQUIRED` 诊断，同时必须以分块 oracle 证明语义等价。G11M 后必须达到正常 10 秒预算，
  否则 G11M/G10R 失败；不得用“尚未建索引”让 G11A 与 D11M 互相死锁。
- G07-ADR 冻结 LLM_OFF 或 LLM_ENABLED；OFF 永远没有 D11M-L/BP/BF 出边。
- G11M-L-ADR 必须同时有 G11B-A3 与 G07E；NO_SCHEMA_DELTA 直接到 BP，SCHEMA_DELTA 必须
  D11M-L→OP11M-L→G11M-L 后到 BP。
- D11J→OP11J→G11J 必须在首个 Canary A 写入前完成；G10R 也要求仍有效 G11J。
- G10C 的 computed next 只能为 D11A；G10R 只能为 D12A。
- 每个 D05Rnn/OP05Rnn/G05Rnn 使用一次性连续 nn；reset contract 除 failure generation、exact D
  return 与完整 downstream invalidation 外，还必须逐 hash 绑定 active latch、全部 durable budget
  状态和 append-only history 的 before/after，绑定一次性 reset auth token，并明确禁止组合
  RESUME/ARM/LOGIN/ACTIVATE。history 删除、预算重置扩大、占位符、G/OP返回或直接推进均失败。
- 所有 OP 先绑定 `operation_intent_manifest.json`。D gate 冻结 canonical intent（exact action IDs、
  exact Run bytes/registry operation、control/circuit generation 与合同摘要），用户授权再绑定该
  intent hash；OP 合同必须绑定同一 intent/action/auth hash。`BOUND_COMPENSATION` 还必须绑定 parent
  authorization id/hash；kind、stage、action、generation、scope、provider、时间窗任一漂移均失败。
- 授权时间只能是严格 UTC `Z`；使用已启用 FormatChecker 后再语义检查
  `issued_at <= checked_at <= now < expires_at`。allowed/excluded scope 必须不相交，provider/scope
  标识不得重复。
- 12B 的 Run value/12B 用户授权在 D12B-ARM 前完成；D12B-RB 必须在任何 ARM 写入前独立审查并
  冻结可执行 compensation。12C 则由 D12C 先冻结“拟执行 action + intent hash”，用户只批准该
  hash，G12C-PRE 再核对 TTL/revocation/drift，不能先取得模糊批准再补合同。
- validator 对每个 OP 先在 `operation_contracts.v4.json` 做唯一 exact/pattern match，再核对
  dynamic contract path/hash。`REQUIRED` 必须有同 stage、未过期/撤销且字段全绑定的 authorization
  manifest；`N_A_ALLOWED` 只接受 catalog 枚举 reason；`BOUND_COMPENSATION` 必须复用 parent D
  已封存的 compensation/auth hash。任何自由文本 `NOT_APPLICABLE:*` 均失败。每个 mutating OP
  还必须绑定受保护 journal manifest、head-before、intent record、expected finalize/head-after；
  crash 后先 reconcile 半提交记录，不能静默重跑。
- registry contract 必须列出 HKCU、current-user SID、32/64-bit view、exact key/value/name/type、
  expected prior absence/value hash、desired REG_SZ exact bytes/hash/length、CAS primitive implementation/
  proof hash、run ownership nonce、max touched count 与 post-read。发现 existing-same-bytes 也不是
  “创建成功”；只有精确 owner nonce 可条件删除。若无法在两个竞争进程和第三方替换测试中证明
  CAS 线性化，G12B-PRE 必须 BLOCKED，禁止退化成普通 read-then-write。
- OP12B-ARM/G12B-ARM/D12B-CAS 及其后直到 G12B-POST 的失败、token/lease expiry 或用户取消都只能
  走 `OP12B-RB→G12B-RB`；OP12C 或 G12C 失败只能走 `OP12C-RB→G12C-RB`。若第三方替换 Run 值，
  compensation 必须保留第三方值并进入 `PAUSED/REGISTRY_CONFLICT`。rollback G 只读，并从 OP 合同
  继承 exact terminal state，不得自报固定状态。
- G12B-POST 后 D12C 可以只读冻结拟执行 intent；缺 final activation 用户批准时在 D12C 后保持
  `SAFE_PAUSED_WAITING_USER`，`next` 返回等待原因和空 eligible set，不能写 BLOCKED/前进。新批准
  必须逐 hash 绑定 D12C intent，再由 G12C-PRE 重验。
- G12C 后每个普通 autostart cycle 都必须在任何 DB/file/network side effect 前封存新的 cycle
  intent + dynamic operation contract，绑定 process/control generation、release/config/routing/data、
  exact candidate source→source identity、DB/file/egress、journal head 与 durable daily/monthly budget；
  每 cycle 重验授权 expiry/revocation 和 caps。失败必须 circuit+pause、process=0，preflight 失败时
  registry/config/source/catalog/normalized write count 全为 0；第三方 Run 漂移进入 REGISTRY_CONFLICT。

## 7. T00L/G00L 稳定测试

`gate_ledger_validator_vectors.v4.json` 是最小集合；T00L 必须再实现 property/mutation：

- `GL-S01`：合法 READY/IN_PROGRESS 空 reviewer；
- `GL-S02`：合法 D/G PASS 与 1/2/3 reviewer cardinality；
- `GL-S03`：合法 PASS_WITH，仅 P2/P3；
- `GL-S04`：合法 OP run/auth/evidence/generation/state；
- `GL-S05`：canonical bytes、seq、prev、expected head；
- `GL-S06`：INVALIDATED/supersedes 使下游失效；
- `GL-F01`：PASSED + reviewer FAIL；
- `GL-F02`：PASSED/PASS_WITH + open P0/P1；
- `GL-F03`：reviewer 数不足、重复 agent/role、与 executor 相同；
- `GL-F04`：READY/IN_PROGRESS 带 completed review/evidence；
- `GL-F05`：NOT_SELECTED、BF00、非法 node/type；
- `GL-F06`：双选 02B、ADR 后领取另一分支；
- `GL-F07`：仅 G07E 后提前领取 D11M-L、或绕过 G11J 提前生产写入；
- `GL-F08`：authored next、非法 reset return、或把可选用户等待写成BLOCKED；
- `GL-F09`：OP 缺 run/auth/evidence/contract/generation、任意N/A、跨stage/过期授权；
- `GL-F10`：review payload/confirmation/evidence hash漂移、fake node/role/null head；
- `GL-F11`：seq/prev/expected-head/supersedes或bootstrap head异常；
- `GL-F12`：生产 before/after、缺compensation、operation catalog/state非法。

G00L 必须由 2 名独立 reviewer，各自运行全部 vectors；至少一人另写一个未预告负例。任何
vector 未被杀死、错误码不稳定或 validator 接触生产路径，G00L 必须 FAIL。
