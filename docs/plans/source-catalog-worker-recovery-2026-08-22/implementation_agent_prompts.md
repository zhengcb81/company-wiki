# Source Catalog Worker — 实施与独立审查 Agent 任务模板

> 目的：把每次派工变成边界明确、可验证、不会跨阶段漂移的封闭任务。  
> 使用时必须替换全部 `<PLACEHOLDER>`；留空则不得派工。

## 1. 派工前检查

任务发出者必须先填：

- `<WP_ID>`、`<DESIGN_GATE>`、`<EXIT_GATE>`；
- `<BASE_COMMIT>` 与 `<WORKTREE>`；
- `<PREVIOUS_GATE_REPORT>` + SHA-256；
- `<ALLOWED_FILES>`；
- `<FORBIDDEN_PATHS>`；
- `<FAIL_FIRST_TESTS>`；
- `<REQUIRED_TESTS>`；
- `<PERFORMANCE_OR_SLA>`；
- `<EVIDENCE_DIR>`；
- `<REVIEW_ROLES>`；
- `<STOP_CONDITIONS>`。
- `<NODE_ID>` 与（生产操作时）`<OP_ID>/<RUN_ID>`；
- `<PLAN_REVISION>/<PLAN_MANIFEST_PATH>/<PLAN_MANIFEST_SHA256>/<PREV_LEDGER_SHA256>`；
- `<AUTHORIZATION_MANIFEST_PATH>/<AUTHORIZATION_MANIFEST_SHA256>`，或静态catalog明确允许的
  `<CATALOG_NA_REASON>`；禁止自由文本N/A；
- `<TRUST_ANCHOR_RELEASE_MANIFEST>`、`<OPERATION_CONTRACT_PATH>/<OPERATION_CONTRACT_SHA256>`、
  `<REVIEW_ROLE>/<INPUT_LEDGER_HEAD>`（适用时）。

任务范围不能只写“修 worker 慢”。一个 agent 每次只执行一个 WP 或一个 reviewer 角色。

## 2. 实施 Agent 模板

```text
你是 <WP_ID> 的实施 agent。只完成这个 Work Package，不做相邻优化。

工作目录：<WORKTREE>
基线 commit：<BASE_COMMIT>
前一 Gate：<PREVIOUS_GATE_REPORT>（SHA-256: <HASH>）
计划目录：docs/plans/source-catalog-worker-recovery-2026-08-22/

开始前必须完整读取：
1. README.md
2. task_plan.md
3. findings.md
4. progress.md
5. execution_playbook.md 中 <WP_ID>
6. test_acceptance_plan.md 的相关测试
7. agent_review_gates.md 中 <DESIGN_GATE>/<EXIT_GATE>
8. gate_state_machine.md 中当前节点和唯一合法下一状态
9. gate_dag.v4.json及instance schema、ledger_validator_contract.md、gate_ledger.schema.json、
   review_result/review_confirmation schemas、operation catalog/dynamic contract/auth schemas、
   test_id_registry.v4.json及instance schema
10. acceptance_thresholds.md 中本 WP 的数值合同
11. traceability_matrix.md 中本 WP 的 requirements/risks
12. `<PLAN_MANIFEST_PATH>`与其全部hash；如已有gate_ledger.jsonl，必须先用G00L已通过validator
    验证最后有效record/hash chain并用`next`确认当前NODE_ID是唯一合法候选

允许修改的文件：
<ALLOWED_FILES>

绝对禁止：
- 修改上述白名单之外文件；
- 修改 config/source_catalog.yaml、生产 .source_catalog、真实源目录、StockWiki；
- 启动生产 worker/supervisor、恢复自启动、删除 lock/WAL/backup；
- reset/stash/覆盖不属于你的 dirty changes；
- 顺手重构、批量格式化、直接多线程 LLM；
- 在 Design Check 通过前修改实现。

固定步骤：
1. 记录 git status/HEAD、worker隔离、自启动、生产哨兵；发现 overlap 立即停止。
2. 使用 CodeGraph 核对目标符号/调用链/impact；旧行号只作线索。
3. 先实现并运行失败测试：<FAIL_FIRST_TESTS>，形成只含测试/fixture的`Txx`commit。WP-01是
   唯一TEST_BASELINE_ONLY例外：禁止产品代码/seam、没有I01；公开接口不足则D01 FAIL并把
   seam放I02A。
4. 把失败证据写入 <EVIDENCE_DIR>/design/，然后停止实现，等待 <DESIGN_GATE> 独立审查；
   Dxx后任何test/fixture/assertion变化都会使其失效。
5. 只有validator确认D节点为PASSED或PASSED_WITH_P2才做最小实现；后者必须只有P2/P3、
   owner与尚未越过的due node。口头“PASS”或Markdown文字不算授权。
6. 形成独立`Ixx`实现commit。运行：<REQUIRED_TESTS>；验收：<PERFORMANCE_OR_SLA>。
7. 做计划要求的 mutation/fault injection，证明测试会捕获回归。
8. 检查逐文件 diff、git diff --check、生产/config/source 哨兵。
9. 写<EVIDENCE_DIR>/manifest.md，包含命令、exit code、脱敏日志、性能、回滚。secret/token/
   cookie/credential永不采集；正文默认不采集。获批raw evidence只能进D Gate冻结的approved
   sink（SID ACL/加密/无reparse/7与30日TTL）；仓内记录opaque ID/脱敏统计/不可逆标识。
10. 不改冻结task_plan/findings/traceability，不自行标Gate PASS。把事实交给reviewer；主agent
    只在machine review JSON/Markdown与detached confirmation actual hash全部回读确认后，用validator append。
11. 若当前分支未被ADR/profile选择，不执行、不创建commit、不写ledger；未选分支任何record
    都是GLV-E021。LLM-off的高风险operation仍需stage-bound authorization manifest；仅provider
    scopes为空且egress DENY_ALL，不能把整个OP写成N/A。只有静态operation catalog枚举的安全
    N/A reason可用。

停止条件：
<STOP_CONDITIONS>

输出只报告：修改文件、红灯证据、绿灯证据、性能/故障证据、未决风险和 evidence path。
不要宣称下一 WP 可以开始；该决定属于独立 reviewer。
```

## 3. Design Check Reviewer 模板

```text
你是 <DESIGN_GATE> 的独立设计 reviewer。你没有参与 <WP_ID> 的实现。
这是严格只读任务：不要修改任何代码、测试、配置、计划或证据文件。

基线：<BASE_COMMIT>
计划目录：docs/plans/source-catalog-worker-recovery-2026-08-22/
待审失败测试/设计证据：<DESIGN_EVIDENCE_DIR>
Exact node/role：<NODE_ID> / <REVIEW_ROLE>
Input ledger head：<INPUT_LEDGER_HEAD>
Plan manifest / DAG / evidence hashes：<PLAN_MANIFEST_SHA256> / <DAG_SHA256> / <EVIDENCE_SHA256>

必须读取 README、task_plan、gate_state_machine、acceptance_thresholds、execution_playbook
对应 WP、test_acceptance_plan、agent_review_gates 对应 Dxx、traceability_matrix 相关
requirements/risks，以及目标源码/diff。

请独立检查：
1. 失败测试是否因目标缺陷而红，而非夹具/环境错误；
2. 测试是否穿过真实接口，能杀死目标 mutant；
3. 设计是否保持业务语义、安全和回退；
4. 是否遗漏边界/反例；
5. 是否超范围或可能触及生产路径；
6. 性能/时间方法是否稳健；
7. 允许文件白名单是否足够且不过宽。

主动提出并检查至少一个实施者未覆盖的反例。
按 P0/P1/P2/P3 写 findings，并给唯一结论：
PASS | PASS_WITH_NONBLOCKING_FINDINGS | FAIL。缺权限/证据/独立性时返回FAIL并说明；主流程
负责把Gate状态标为BLOCKED。

不要替实施者改代码。先原样输出一个符合`review_result.schema.json`的JSON object和一份完整
Markdown；node、role、head与上述注入值必须exact match。主 agent代存时必须保存原始payload
hash；收到actual JSON/Markdown path+hash后，你需亲自回读，并另行输出符合
`review_confirmation.schema.json`的detached confirmation。不要让主agent代填true。
```

## 4. Exit Gate Reviewer 模板

```text
你是 <EXIT_GATE> 的 <REVIEW_ROLE> 独立 reviewer。你未参与该 WP 的代码、测试或证据生成。
只读审查，严禁修改任何文件。

基线/候选 commit：<BASE_COMMIT> / <CANDIDATE_COMMIT>
Evidence manifest：<EVIDENCE_MANIFEST>（SHA-256: <HASH>）
Design review：<DESIGN_REVIEW>
允许修改文件：<ALLOWED_FILES>
Exact node/role/head：<NODE_ID> / <REVIEW_ROLE> / <INPUT_LEDGER_HEAD>
Plan manifest / DAG hashes：<PLAN_MANIFEST_SHA256> / <DAG_SHA256>

先核对plan/evidence/ledger hash与commit；不一致输出`verdict=FAIL; reason_code=EVIDENCE_DRIFT`，
不得发明第四种verdict。
然后：
1. 通过 CodeGraph/diff 检查实际影响面和范围越界；
2. 审语义、错误路径、资源、隐私、恢复和兼容性；
3. 审红灯→绿灯、mutation/fault，以及证据合同允许保留的完整测试输出；raw输出只从D Gate
   批准的repo外受限sink读取，secret/token/cookie/credential永不采集；
4. 重算至少一个关键结果或性能指标；
5. 主动构造至少一个新反例；
6. 核对生产/config/source sentinel、worker paused、自启动 off；
7. 检查回滚可执行且不会覆盖其他任务。

本角色专项清单：
<ROLE_SPECIFIC_CHECKLIST>

每条 finding 必须含 priority、文件/符号或证据定位、复现/推理、影响和要求处置。
P0/P1 或关键证据缺失时必须 FAIL。不要用 LGTM、看起来合理或测试全绿代替审查。
原样输出符合`review_result.schema.json`的JSON与完整Markdown，node/role/head/hash必须exact；给
唯一 verdict（PASS/PASS_WITH_NONBLOCKING_FINDINGS/FAIL）并写明复审条件。主agent保存后，
你必须回读actual bytes并另发`review_confirmation.schema.json` payload。不要修改文件。
```

## 5. Finding 修复 Agent 模板

```text
你只处理 <GATE_ID> review 中列出的 findings：<FINDING_IDS>。
不要继续下一 WP，不修改无关文件。

原 review：<REVIEW_PATH_AND_HASH>
原 evidence revision：<REVISION>
允许文件：<ALLOWED_FILES>

逐项：
1. 复现 finding；无法复现则保存证据，不直接拒绝；
2. 做最小修复；
3. 新增/强化能捕获该 finding 的测试；
4. 重跑原 Gate 全部受影响 tests 和 sentinel；
5. 生成新的 evidence revision，不覆盖旧文件；
6. 给出 accepted 或 rejected-with-evidence 响应；
7. 等原 reviewer/同领域独立 reviewer 复审。

你无权自行关闭 P0/P1。
```

## 6. G10C/G10R 六份互不循环的独立审计模板

六份分别派给满足各节点DAG exact role/cardinality/disjoint规则的agent；不得共用一个prompt或
把未来节点加入G10C。“独立”不额外扩大为DAG未声明的全局永久排除。每份开头都追加：

```text
你的exact node/role/head/manifest/DAG/evidence hash由任务头注入；任一placeholder或不匹配立即FAIL。
先用validator next/replay核对本Gate exact input node set及hash。若包含未来节点、缺前驱、
hash不匹配或Gate ID错误：verdict=FAIL; reason_code=EVIDENCE_DRIFT。不得等待未来证据或补签。
原样返回schema-valid JSON+Markdown；主agent保存后另发detached confirmation。
```

### 6.1 G10C-SQL

```text
只读输入仅限G00、G01、G02A、selected(G02B-NI,G02B-IDX)、G03、G04、G05、G09P、G09。
抽查G01、G02A、选中的精确G02B节点、G09。审queue语义/source freshness、measurement mode、
planner/无stats/跨版本、ordinary-open与选中migration分支、生产只读前风险。禁止要求G06、
G07、G08、A/B、12A、12B。唯一computed next=[D11A]。
```

### 6.2 G10C-CONTROL

```text
输入仅为与G10C-SQL相同Core集合。抽查G03、G04、G05、G09P、G09；审checkpoint、SQLite
cancel、circuit、Job Object、one-shot、source deny、trust/write/registry/dormant-login tmp E2E。
禁止要求任何生产canary或hardening未来证据。唯一computed next=[D11A]。
```

### 6.3 G10C-TESTOPS

```text
输入仅为Core集合；抽查G00、G09P、G09。审red→D→I→G、fault/mutation、tmp隔离、rollback、
machine review JSON与ledger validator。禁止G06/G08/A/B证据。唯一computed next=[D11A]。
```

### 6.4 G10R-SQL-PERFORMANCE

```text
只读exact release join：still-valid G09P、G09、G10C、G11A、G11J、ADR-02条件G11M、G11B-A1/A2/A3、G06、
enabled route/bucket的G06P、G08、exact G07E或G07O、ADR-13条件G11M-L；enabled模式还含
G11B-BP和连续G11B-BF01..最后启用编号。审scanner/parser性能、A delta、迁移、LLM ledger/
throughput；禁止D12A/G12A/12B证据。唯一computed next=[D12A]。
```

### 6.5 G10R-CONTROL-LIFECYCLE

```text
读取与G10R-SQL相同exact release join。核验G05/G09P仍有效、A1/A2/A3各自write/source/pause、
exact G07 mode、每个BP/BF授权、trust/release/control/registry/dormant-login/final-activation
contract；不得审尚未发生的12A/12B运行结果。唯一computed next=[D12A]。
```

### 6.6 G10R-TESTOPS

```text
读取同一exact release join。审G06/G06P/G08、A1/A2/A3各自review、BP及每个连续BF各自review、
migration/fault/rollback/evidence/ledger；禁止最后集中补签。不得要求12A/12B。唯一computed
next=[D12A]。
```

## 7. 生产 Gate Agent 模板附加条款

### 7.0 G09P Reviewer

```text
只读审`test_id_registry.v4.json`中`introduced_at=T09P`且condition成立的全部concrete IDs，并按
逐IDrequired_green/revalidate映射核对，不做owner×due展开：
one-shot/session override、外部trust anchor/不可写完整release/
tamper-TOCTOU、operation+PK+column/exact-file changeset、OS source deny、主备egress deny、
三动作正交、静态operation catalog/动态contract/auth、protected journal、真实registry条件并发、
safe mutant/ENOSPC与evidence lifecycle。不要运行生产。
```

### 7.1 G11A Reviewer

```text
只读审查生产对照。确认 worker/supervisor/parser=0、自启动off；SQLite mode=ro/query_only；
WAL 一致性；旧无边界查询未运行；deadline/资源上限；ordered IDs；连接前后 DB/WAL/SHM/
config/source sentinel。NO_INDEX必须直接满足正常10秒deadline；INDEX可在预声明deadline内返回
INDEX_REQUIRED，但须证明缺冻结索引且分块oracle/有界只读查询仍100%匹配ordered IDs；该结果
只开放D11M。任何写入或证据不完整直接 FAIL。不要运行 worker，不修改文件。
```

### 7.1M G11M Reviewer

```text
仅ADR-02需要schema时审。DDL前核验用户授权、当前恢复点、RPO/RTO、恢复演练、实测峰值、
显式migrator与DDL-denying normal open；DDL后核验ledger/index/integrity/plan/幂等/空间，并用
G11A同协议证明新查询满足正常10秒deadline/plan预算。不要
自行执行migration。NO_INDEX分支没有D11M record；选择只来自G02B-ADR machine payload。
request-ledger migration只有G11B-A3+G07E→G11M-L-ADR[SCHEMA_DELTA]后可审。
```

### 7.1J G11J Reviewer

```text
只读审一个明确的D11J或G11J。核对两条ADR-02分支都经该节点；exact journal path identity、SID
ACL、无reparse/cloud-sync、format/version、atomic append/replace、flush/fsync、hash-chain、crash
reconcile、retention、RPO seconds=0/RTO seconds≤1800。G11J必须亲验半写/断电/ACL反例、所有
production sentinel与ordinary mode=rw zero DDL。Reviewer不得自行初始化journal。
```

### 7.2 G11B-A1/A2/A3、G11B-BP 与逐个 G11B-BFnn Reviewer

```text
你不是operator，只审一个明确节点；开始时必须PAUSED/OFF且进程0。A节点检查独立run/auth、
candidate/root、operation+PK+column/exact-file precommit/post-read changeset、RPO/RTO、runs/
checkpoint/runtime、OS source deny/egress；不能替其他A签字。BP/BF检查G07E前置、该provider
专属一次性authorization/request ledger/source binding/caps/cost，以及stage独立RPO/RTO、
typed PK/columns/files/prior state/touched limits、precommit/post-read。primary授权/contract不传fallback。
不要重启补证据。
```

### 7.3 G12A Reviewer

```text
只读审OBS-S01、OBS-S02、OBS-S03、OBS-S04、OBS-S05、OBS-S06、OBS-W01、OBS-W02、OBS-W03
及WRITE-F01、WRITE-F02、WRITE-F03、WRITE-F04原始至少2小时时间序列。确认G10R exact
profile、5连续cycle、失败重置；逐周期contract/hash与独立transaction；
默认LLM-off+主备deny，真实模式使用12A专属完整authorization hash。计算资源/DB/log/scan/
backlog/pause；结束先PAUSED/进程0。通过不批准自启动。
```

### 7.4 G12B 与 12C Reviewer

```text
PRE：确认profile-specific Gate/P0/P1=0、外部trust anchor/不可写完整release/interpreter、exact
Run bytes、12B profile与G12A相同、新12B authorization hash、arm schema、真实atomic registry
create/delete；此时只批准value/auth，logout须稍后重新批准。
D12B-ARM先冻结arm action；任何ARM state/token写前，D12B-RB两名满足DAG rollback/startup角色与
disjoint规则的reviewer只seal compensation contract。未PASS不得执行OP12B-ARM。OP先向protected
journal写intent（expected registry absence、desired bytes hash、ownership/run nonce、generation、
补偿目标）再写arm state并finalize；G审不启动/reset/写registry、ARM token默认15min硬30min及exact binding。
D12B-CAS/G：审ARM token在CAS消费、exact REG_SZ与两进程竞争；CAS后ARMED_ON_PRELOGIN/ON且
dormant lease默认24h硬72h，无LOGIN_COMMITTED时任何login/reboot child/egress=0，第三方值不覆盖。
从OP12B-ARM起任何失败/过期/crash partial只触发OP12B-RB→G12B-RB，按journal+ownership nonce
reconcile；同名既有值即使bytes相同也冲突，第三方值不接管，终态PAUSED/REGISTRY_CONFLICT；
G继承OP终态，Gate/launcher不得写registry。
D12B-LOGIN：审5min默认/10min硬上限commit token、review/user/SID/machine+boot generation/
previous session/下一次新logon关系/generation绑定，不预知future session；
随后用户确认保存工作才可OP。POST：审首cycle后LOGIN_VALIDATED_PAUSED/ON、process0；不得RECOVERED。
D12C/G12C-PRE/OP/G：D12C先seal final+rollback合同及唯一proposed action/intent hash，用户随后
只授权该hash/action ID；未批准是safe waiting。G12C-PRE恰好三名按DAG与D12C disjoint的reviewer
预审actual授权，OP只变ENABLED_IDLE/ON且process0，G12C恰好三人通过后物理state
仍不变、只记lifecycle_outcome=RECOVERED。token/control写前必须有protected journal intent、
写后finalize，crash只由RB reconcile。失败只走OP12C-RB→G12C-RB。不要自行改registry、
logout、Gate state或启动当前session。Run被第三方替换时RB不碰registry，终态必须
PAUSED/REGISTRY_CONFLICT。G12C后每个cycle仍先密封runtime contract并重验auth/cap/journal/
write/egress；亲验ACT-S08、ACT-S09、ACT-S10，失败circuit open+pause且registry/config/source零写。
```

### 7.5 D05Rnn / G05Rnn Reviewer

```text
只审一个唯一`05R01`–`05R99`实例。D确认circuit open、PAUSED/process0、root cause/disposition、用户
reset token、failure generation/TTL、失败节点合法祖先中的exact D return node及全部downstream
invalidation；G/OP/占位符return均FAIL。G确认只清active latch/budget、generation+1、
历史保留，20s进程0且registry/config/DB/source/release/auth不变。任何resume/arm/login/activate
副作用或直接后继均FAIL。Reviewer不得执行reset。
```

## 8. Ledger/Progress 更新模板

每次agent返回后，主agent先保存符合`review_result.schema.json`的machine payload、Markdown
报告及原payload/hash，把actual path/hash发回同一reviewer；只有收到schema-valid detached
`review_confirmation`并验证其actual hash后，才用G00L validator向`gate_ledger.jsonl`追加。
禁止手抄verdict/findings或自报next edge。`progress.md`只写以下叙事；
不得改冻结的task_plan/findings/traceability：

```markdown
### <date/time> — <WP/Gate>

- Base/candidate commit:
- Plan revision/manifest + previous ledger hash:
- Exact node ID / OP run ID / authorization evidence ID:
- Agent role and independence:
- Actions performed:
- Files changed (implementation agent only):
- Tests/benchmarks/faults:
- Evidence revision/hash:
- Review verdict:
- Reason code:
- Open findings:
- Worker/autostart final state:
- Next allowed action:
- Explicitly forbidden next action:
```
