# Source Catalog Worker — 灰度、观察与回滚 Runbook

> 只有 Phase 11–12 且取得相应授权时才执行本文件中的状态变更。  
> 当前预期状态仍是：`PAUSED / STOPPED / Supervisor NOT RUNNING / Auto-start OFF`。

## 1. 状态推进图

```text
持久暂停
  └─D11A→OP11A→G11A（worker仍停）
      ├─ADR-02=NO_INDEX ───────────────────────────────┐
      └─ADR-02=INDEX→D11M→OP11M→G11M ────────────────┤
                                                       v
        D11J→OP11J→G11J→D11B-A1→OP11B-A1→pause→G11B-A1
          →D11B-A2→OP11B-A2→pause→G11B-A2
          →D11B-A3→OP11B-A3→pause→G11B-A3
            ├─G07O（LLM_OFF，无B节点）──────────────────────────────┐
            └─G07E→G11M-L-ADR                                      │
              ├─NO_SCHEMA_DELTA ────────────────────────────────┐   │
              └─SCHEMA_DELTA→D11M-L→OP11M-L→G11M-L ────────────┤   │
                                                               v   │
                 D11B-BP→OP11B-BP→pause→G11B-BP                   │
                 →逐个D11B-BFnn→OP11B-BFnn→pause→G11B-BFnn ──────┤
                                                                  v
              exact release join（含still-valid G09P/G09）+ hardening→G10R→D12A→OP12A→pause→G12A
                →G12B-PRE→D12B-ARM→D12B-RB→OP12B-ARM→G12B-ARM
                →D12B-CAS→OP12B-CAS→ARMED_ON_PRELOGIN/ON→G12B-CAS
                →D12B-LOGIN→用户最终登录批准→OP12B-LOGIN
                →自动pause→LOGIN_VALIDATED_PAUSED/ON→G12B-POST
                →D12C冻结action/intent→用户最终长期激活批准该hash→G12C-PRE→OP12C→ENABLED_IDLE/ON→G12C
                →physical ENABLED_IDLE/ON + lifecycle RECOVERED（当前session仍process0）

ARM/CAS/登录/lease失败→OP12B-RB→G12B-RB→PAUSED/OFF或PAUSED/REGISTRY_CONFLICT
OP12C/G12C失败→OP12C-RB→G12C-RB→LOGIN_VALIDATED_PAUSED/ON或PAUSED/REGISTRY_CONFLICT
```

任何失败都回到“持久暂停”，而不是自动进入下一状态。G12B-POST只证明一次登录验证完成且
重新暂停；只有另行完整通过D12C→G12C-PRE→OP12C→G12C，才允许下次正常登录启动。
Gates只读，失败写操作只能由图中的显式compensation OP执行。OP12C不得启动
当前session。所有前驱和下一边以`gate_dag.v4.json`及validator计算为准；未选分支不创建
ledger record，不写假PASS或假跳过状态。

## 2. 人员/Agent 角色

- **Operator**：执行唯一被批准的命令；不能批准自己的 canary。
- **Live observer**：看 runtime、进程、资源、DB/log 增长；持有停止权限。
- **Evidence recorder**：记录时间线、命令、PID identity、hash；可与 observer 同一人/agent。
- **Independent reviewers**：按 `agent_review_gates.md` 审查，不能参与操作。
- **User approver**：授权生产 canary、真实 LLM（若有）和恢复自启动；agent Gate 不能替代。

Canary 前必须明确 Operator 和 Live observer；无人观察时不得启动。

## 3. 通用预检

### 3.1 代码与计划

- 当前 commit 正是当前阶段所需 G10C 或 G10R 审过的 revision；
- worktree clean，或只有本隔离目录中已解释的 evidence/review 文件；
- 所有早期 Gate 报告 hash 匹配，无开放 P0/P1；
- 另一个任务没有正在修改 worker 核心文件；
- 实际启动命令指向受审 revision，不从一个持续变化的工作树加载。

生产运行必须使用G09P/G10C审过的内容寻址、对worker identity不可写/删/换名的完整release；
首段非OS代码来自独立trust anchor，不允许被验证launcher自验。manifest覆盖VBS/PowerShell/
Python/lazy modules/interpreter，拒绝reparse与check-load TOCTOU；每次child restart重验。code
root与config/catalog/runtime/source roots分离。若任一代码仍从可写工作树加载，Gate BLOCKED。

### 3.2 进程与启动入口

只读检查：

- worker、supervisor、parser 均为 0；
- operation lock 即使存在，也只记录 PID + creation time + executable，不盲删；
- 在OP12B-CAS前，HKCU Run `CompanyWikiSourceCatalog` 必须不存在；CAS后则必须与该节点受审的
  exact key/name/type/value bytes完全一致，任何其他值均为冲突；
- 没有同用途计划任务、服务或 Startup shortcut；
- control state 为 persistent pause，circuit 状态可解释。

可以复用下列现有 status 入口核对用户视图：

```powershell
$WorkerRecoveryProjectRoot = '<ABSOLUTE_PROJECT_ROOT>'
$WorkerRecoveryPythonExe = '<ABSOLUTE_PYTHON_EXE>'
& (Join-Path $WorkerRecoveryProjectRoot 'scripts/source_catalog_control.ps1') `
  -Action status `
  -PythonExe $WorkerRecoveryPythonExe `
  -ProjectRoot $WorkerRecoveryProjectRoot
```

注意：该脚本具备向 `.source_catalog/control_center.log` 写 diagnostic 的能力。Gate 证据必须
区分这一预期 control log 写入与 DB/config/source 零写；需要绝对只读盘点时直接读取状态
文件/进程/注册表，不调用可能写日志的 wrapper。

### 3.3 数据与空间

- 记录 production DB/WAL/SHM/现有备份大小、卷余量和 mtime；
- 记录 schema/index 和关键 row counts；
- 记录源文件不变性 manifest；高风险 root 至少全量 metadata，对 canary 实际触达文件记录
  content hash；
- 记录生产 config hash；
- 任何 migration 前使用恢复副本实测峰值空间。

源文件 sentinel 只是侦测层，不是保护层。生产 canary还必须使用专用低权限身份、只读
replica或受审 sandbox 让 source write得到 permission denied；无法建立该边界时 Gate blocked。
secret/token/cookie/credential/`.env` value永不采集；正文默认不采集。获批raw evidence只进D
Gate冻结的approved sink（repo/workspace/temp/cloud-sync之外、无reparse、SID ACL、加密/密钥
分离、7/30日TTL）；仓内仅opaque ID/脱敏统计/不可逆标识。未定义该sink时只能保存脱敏证据。

**不要自动再复制一份 46 GiB 数据库。** 2026-08-20 已有约 45.93 GiB remediation 备份且
卷余量当时约 98.9 GiB；新基线必须重算。先验证现有恢复点是否与当前 DB/schema 相符，再
决定是否需要新一致性备份。需要新增备份时必须满足空间公式并获得对应 Gate/授权。

### 3.4 停止条件和停止命令

Operator 与 observer 都必须能执行：

```powershell
$WorkerRecoveryProjectRoot = '<ABSOLUTE_PROJECT_ROOT>'
$WorkerRecoveryPythonExe = '<ABSOLUTE_PYTHON_EXE>'
& (Join-Path $WorkerRecoveryProjectRoot 'scripts/source_catalog_control.ps1') `
  -Action pause `
  -PythonExe $WorkerRecoveryPythonExe `
  -ProjectRoot $WorkerRecoveryProjectRoot
```

执行后验证 persistent pause、相关进程为 0、自启动仍 off。不得用裸 PID `Stop-Process`
作为首选；只有 control 失效且已核验 PID identity 的紧急情况才用进程终止，并记录原因。

## 4. 恢复点策略

### 4.1 代码恢复点

- 每个 WP 独立 commit；canary revision 打 tag/记录 commit hash；
- 回退使用明确的 revert commit 或切回已验证的固定 worktree；
- 禁止 `git reset --hard`、覆盖另一个任务的工作树或删除未归属变更；
- 回退代码后仍保持 persistent pause，先跑相应 tmp tests。

### 4.2 数据库恢复点

优先级：

1. 即使无schema变更，canary DML也必须有当前RPO/RTO、唯一run ID和机器可执行
   operation+exact PK+column/exact-file contract；commit前changeset拒绝越界，commit后独立重算。
   旧remediation备份未验证前不能当当前恢复点，恢复点也不能替代写前拒绝；
2. 有 schema migration 时，在恢复副本完成全流程演练；
3. 生产 migration 前取得一致性恢复点、校验可打开/schema/hash，并记录恢复时间；
4. 新代码应尽可能向后兼容，发生应用问题时允许退代码而保留无害附加索引；
5. 不在事故压力下直接 `DROP INDEX`、`VACUUM` 或手工删 WAL/SHM；
6. 每个D11B-A/B前把wrong operation/PK/column/file/touched delta处置冻结为：transaction
   rollback、带run ID隔离/reconcile，或经授权恢复。Operator不能临场DELETE/restore。

真正替换生产 DB 属破坏性恢复，必须另行获得用户批准。执行时应：停止全部相关进程，
核验绝对路径，把当前故障 DB 移入明确 quarantine 而非删除，原子放置已验证备份，处理
WAL/SHM 一致性，先以 read-only 打开验证，再决定是否运行。该动作不由本 runbook 自动授权。

### 4.3 配置与启动恢复点

- 记录 `config/source_catalog.yaml` 与 worker config hash；普通 canary 不改生产配置；
- 记录原 HKCU Run 值；OP12B-CAS前保持不存在，CAS后只允许本次受审exact value，最终激活
  不再改写该值；
- 不创建计划任务/服务作为“临时替代”；
- 恢复入口失败时只撤回同一个 HKCU Run value，不扩散修改。

## 5. D11A → OP11A → G11A：生产只读对照

### 5.1 操作

1. 完成通用预检并冻结 evidence revision。
2. 通过 SQLite URI `mode=ro` 打开，立即 `PRAGMA query_only=ON`；禁用任何自动 migration
   helper。WAL 存在时不要盲设 `immutable=1`。
3. 先运行 schema/index/row count 和 `EXPLAIN QUERY PLAN`。
4. 新 query 使用 progress/deadline、严格 batch limit 和资源监控。
5. 用分块的独立参考查询比较 ordered document IDs、priority、retry/terminal。
6. 不运行旧的无边界灾难查询；其语义由小夹具 oracle 与安全分块参考提供。
7. 关闭连接，复核 DB/WAL/SHM/config/source sentinel。
8. worker 仍 paused、自启动仍 off；提交两名 reviewer。
9. ADR-02=`NO_INDEX`时必须直接满足正常10秒deadline；`INDEX`只允许在预声明deadline内返回
   `INDEX_REQUIRED`，且必须证明缺少冻结索引并由分块oracle/有界只读查询100%验证ordered IDs。
   该诊断只允许进入D11M，不能当作性能PASS。

### 5.2 失败处理

任何 plan 回到灾难形状、超预算、语义不一致、mtime 改变或意外进程出现：停止 Gate，保留
只读证据，回到 WP-02/WP-00；不得“试跑一次 worker 看看”。

## 6. D11M → OP11M → G11M：条件生产 Migration

若ADR-02=NO_INDEX，不创建D11M ledger record，由validator从G11A开放D11J。
若ADR-02=INDEX：

1. D11M 两名 reviewer 在 DDL 前审核用户授权、当前一致恢复点、RPO/RTO、恢复演练、恢复
   副本实测峰值和显式 operator command；
2. 普通 store open必须用不会创建缺失文件的`mode=rw`语义verify-only：exact schema成功且零
   DDL；missing DB返回`SCHEMA_INIT_REQUIRED`且不创建文件；old schema返回
   `SCHEMA_UPGRADE_REQUIRED`且零DDL；不能通过 eager `_DDL`/login启动构建；
3. 空间满足 `acceptance_thresholds.md`，ENOSPC演练使用faulting VFS/硬quota scratch；
4. worker/supervisor/parser=0、autostart off后才执行显式 migrator；
5. 核对ledger、index SQL/xinfo、integrity、plan、DB/WAL/space和幂等；
6. 用G11A同一生产只读协议重跑新query，必须满足正常10秒deadline/plan预算；
7. G11M失败保持paused，不自动drop/vacuum/删WAL；通过只开放D11J。

fresh-empty 和 prior-version 只允许走已由选中02B分支交付并在tmp/恢复副本验证的显式
`schema init/upgrade --profile NO_INDEX|INDEX`。未知/partial schema、同名错误对象、重复执行与
ENOSPC必须fail closed。`I02B-IDX`只交付工具，绝不授权生产DDL；生产索引仍只在本节执行。

## 6J. D11J → OP11J → G11J：protected write-intent journal

NO_INDEX和INDEX两路在首个写canary前都汇合到D11J。D11J两名reviewer冻结exact path identity、
批准SID ACL、无reparse/cloud-sync、format/version、atomic append/replace、flush/fsync、hash-chain、
crash reconciliation、retention、RPO seconds=0与RTO seconds≤1800。OP11J只显式创建该journal，
不启动worker、不写catalog/source/config/registry。G11J两名按DAG与OP执行者disjoint的reviewer亲验半写/断电/ACL和
ordinary mode=`rw` zero DDL；通过才开放D11B-A1，并成为G10R的必要输入。

## 7. G11B-A1/A2/A3：分阶段生产 Canary A

### 7.1 必须具备的一次性运行入口

Canary必须使用G09P/G10C已审的真正one-shot/session override，不启动无限supervisor。每个
D11B-Ax重新冻结精确命令/授权/contract；若能力缺失或wrapper变化，必须回开
G09P/G09/G10C。**禁止拿 `resume` 后靠人工计时强杀来冒充单周期模式。**

### 7.2 Canary A 写入合同与子阶段

每个D先冻结唯一run ID、candidate/root IDs、数据库identity/schema、当前恢复点/RPO/RTO、
失败disposition，以及机器可执行write contract：table→operation→exact PK/predicate→columns→
before/after→max touched rows；exact file→operation→prior hash/absence→max bytes/files；禁止
DDL/ATTACH/unsafe PRAGMA/trigger。

1. A1 scan-only：normalize/export/prune/LLM off；
2. A2 normalize/persist-only：scan/export/prune/LLM off，固定3–10 IDs；
3. A3 full-cycle-no-LLM：仅前两步通过；仍one-shot、network deny。

SQLite authorizer只做table/op第一层；commit前changeset核对PK/columns/actual touched rows并在
违规时rollback+pause，commit后独立重算。文件guard解析reparse最终路径，默认exclusive create；
DELETE/覆盖/rename默认拒绝。所有source由OS/sandbox拒写，config/.env只读，主/备egress deny。

如这些行为只能通过修改生产 config 实现，先停止：实现安全的命令行/会话级 override，并
在 tmp contract tests 证明不持久化；不得临时编辑 `config/source_catalog.yaml`。

### 7.3 实时观察频率

每 5–15 秒记录：PID/creation time、stage、stage start、heartbeat、progress counter、current
path（可脱敏）、parser PID、CPU、working set、logical/physical I/O、DB/WAL size。观察本身
不得高频读取整个大 DB。

### 7.4 自动/人工停止阈值

- queue select 达既定 deadline；
- heartbeat 超 SLA，或 heartbeat 在写但 progress 在窗口内不变；
- 非预期第二实例；
- source sentinel 变化；
- source write attempt未被权限层拒绝；
- DB/WAL 增长超过预先预算；
- 非contract operation/PK/column/file、actual touched/byte超限、净零DELETE+INSERT或历史覆盖；
- 未授权网络连接；
- parser 路径/PID 与 runtime 不一致；
- cycle 超总时间预算或任何 P0/P1 事件。

停止后先走 `-Action pause`，验证进程退出。不得立即重启第二次“确认”。

### 7.5 每个子阶段后立即动作

1. 即使成功也执行 persistent pause；
2. 确认 worker/supervisor/parser 为 0，自启动 off；
3. 对账worker_runs/scan_runs/artifact/checkpoint/runtime/timing与precommit/post-read changeset；
4. 比较 source/config sentinel；
5. 归档日志与 hash，不复制源正文；
6. 派数据/source与runtime/rollback两名非operator reviewer签对应G11B-Ax；前一G通过才可下一D，
   G11B-A3不能补签A1/A2。

失败 DML按预先冻结的run-ID changeset/reconcile/restore disposition处理；不得临场DELETE。

## 8. G11B-BP 与逐个 G11B-BFnn：逐 provider 真实 LLM Canary

只有`G11B-A3 + G07E`先进入只读`G11M-L-ADR`；若ADR-11为`SCHEMA_DELTA`，还必须完成
`D11M-L→OP11M-L→G11M-L`，若为`NO_SCHEMA_DELTA`则不创建这些记录。任何单独
`G07E→D11M-L`边非法。G07O没有B入口。Primary走
`D11B-BP→OP11B-BP→G11B-BP`，每个最终
启用fallback按BF01/BF02…分别D/OP/G。每个D取得新的单次stage/provider授权：provider/model、
opaque roots/data、exact docs、fields/exclusions、per-doc/total字符/token/成本、timeout、
retention/jurisdiction/terms、destination、release/config/routing、issued/expiry/revocation/hash。
Primary授权不传fallback，未通过BFnn的provider最终禁用。

每个 BP/BF 的 D Gate 还必须冻结一个不可跨阶段复用的 `CycleWriteContract`：当前
plan/release/config/routing/auth/database/schema/recovery-point/control generation，exact document/
source ID+SHA，DB operation+typed composite PK+allowed columns+prior row version，file
operation+canonical exact path+prior hash/absence，以及 touched-row/file/byte上限。若最终文件名
依赖响应hash，D先冻结确定性路径函数，响应验证后、首次文件写前只允许密封不扩范围的exact
path supplement。request ledger、artifact、cache、usage/cost、runtime/checkpoint写入也必须列入。

每个OP仍one-shot：只读物化候选→密封合同/hash→outer DB transaction→run-private不可见文件
staging→写前changeset/inventory核对→bounded commit→exclusive/expected-hash publish→独立
post-read。任何operation/PK/column/prior state/path/row/byte越界都必须在commit/publish前
rollback+pause。DB/file不能原子提交时使用append-only intent/finalize ledger，所有crash点只做
安全reconcile，不重调provider。完成后立即pause并由两名非operator reviewer审合同、request
ledger/source binding/caps/cost/post-read。429/5xx/timeout不以无限重试完成；IN_FLIGHT crash→
OUTCOME_UNKNOWN且不自动重发。

Canary B授权只覆盖本次一次性run，不自动延续到两小时观察或登录自启动。

## 9. D12A → OP12A → G12A：无自启动人工观察

### 9.1 启动

只有G10R后由D12A冻结exact release/profile/命令/observer/limits，OP12A才执行resume-session。
circuit open时必须CIRCUIT_OPEN；不能顺带reset。默认LLM off+network deny，HKCU Run不存在。

G11B-A1/A2/A3已审的低权限身份/只读replica/sandbox source写拒绝必须在整个观察窗口生效；若
切换运行身份、release或root mapping，先重开G09P/G10R，不能只靠事后sentinel。

若真实LLM，须使用12A专属stage-bound manifest重新授权全部主/备provider/model、data/roots/
fields、文档/字符/token、destination、时间/成本、retention/jurisdiction及release/config/routing；
BP/BF授权不沿用。

### 9.2 观察窗口

- 至少 2 小时；
- 至少连续 5 个完整 cycle success；
- 每个 cycle 开始前先只读物化 exact document/source 集并密封独立 `CycleWriteContract`；周期
  开始后新到达document延后至下个cycle，合同不得扩展；
- 每个cycle使用独立bounded transaction、intent/finalize与post-read，禁止一个持续两小时的
  大事务；任何cycle缺contract/hash时整个G12A失败；
- 任何失败、circuit、意外 restart 都使连续窗口清零；
- scan 应按配置 interval，而不是每周期重复；
- backlog 报 arrival/completion/斜率，不只报当前值；
- 资源每分钟采样，阶段转换处加密采样；
- 结束时主动 pause 并测量 SLA。
- 未授权模式保存进程级 egress deny 证据；任何连接尝试为P0并立即pause。

### 9.3 成功后

保持 paused 和 autostart off，交两名 reviewer。Reviewer 通过只生成“可以考虑恢复自启动”
建议，不恢复入口。G12A必须枚举并核验全部cycle contract/hash，至少独立重算一个完整
changeset；任一cycle有unexpected operation/PK/column/file/touched-row/byte，结果为FAIL。

## 10. G12B-PRE → ARM/CAS/LOGIN → G12B-POST

### 10.1 授权前

两名PRE reviewer确认profile-specific Gate、外部trust anchor、不可写完整release/interpreter、
tamper/TOCTOU、exact REG_SZ bytes、真实registry条件机制、arm schema与回退。12B profile必须
等于G12A；enabled时使用全新`G12B_LOGIN_AUTOSTART` authorization，BP/BF/12A不可复用，
逐项含主/备provider、data/fields、per-doc/daily/monthlydocuments/characters/tokens/cost、
destination、retention/jurisdiction、expiry/revocation、release/config/routing；off时仍需要完整
12B operation authorization，只是provider scopes为空且egress=`DENY_ALL`，不能把整个OP标N/A。
PRE只证明可以准备后续节点；它不批准写registry、注销或最终长期激活。

### 10.2 D12B-ARM 与唯一候选入口

原始调查记录的精确值只在符合approved sink/ACL/加密/TTL合同的raw evidence中核验；仓内
使用脱敏模板：

```text
Name: CompanyWikiSourceCatalog
Path: HKCU\Software\Microsoft\Windows\CurrentVersion\Run
Value template: "<WSCRIPT_EXE>" //B //Nologo "<TRUST_ANCHOR_ROOT>\source_catalog_trust_launcher.vbs" "<PINNED_RELEASE_ROOT>" "<PINNED_RELEASE_MANIFEST>" "<PYTHON_EXE>" "<EXPLICIT_DATA_PROJECT_ROOT>"
```

模板中的`TRUST_ANCHOR_ROOT`必须与`PINNED_RELEASE_ROOT`分离，并由OS ACL/签名构成独立信任
根；两者都对worker identity无write/delete/rename/write-DAC。Run执行的首段非OS代码是trust
launcher，而不是release内待验证的VBS。trust launcher验证内容寻址release manifest后，直接从
同一不可写snapshot加载；release manifest覆盖PowerShell/Python/lazy modules/interpreter，拒绝
reparse/check-load TOCTOU且每次restart重验。无法建立该边界则BLOCKED；仍只用同一Run名称，
不新增其他入口。

D12B-ARM由两名满足DAG exact角色/基数/disjoint规则的reviewer冻结exact value bytes、plan/PRE review/release/config/routing/data root/
12B auth/control+circuit generation/user SID、single-use nonce、回退合同与TTL（默认15分钟、硬
上限30分钟）。OP12B-ARM只在circuit closed、PAUSED/OFF、进程0时写arm token；不启动、不清
counter、不写registry。在任何arm token/control state写之前，D12B-RB先由2名满足DAG
rollback/startup角色与disjoint规则的reviewer预审并seal exact OP12B-RB compensation；未PASS时
OP12B-ARM没有合法入口。OP12B-ARM先向G11J protected journal写入expected registry absence、
desired bytes hash、ownership/run nonce、generation与补偿intent，再写arm state并finalize。
G12B-ARM随后由两名按DAG与OP执行者disjoint的reviewer核对hash、TTL、journal head、状态与零副作用。

### 10.3 D12B-CAS 与 dormant prelogin

D12B-CAS由满足该节点DAG exact角色/基数/disjoint规则的两名reviewer重新核对G12B-ARM、exact value、真实atomic primitive、并发与所有
power-loss回退。OP12B-CAS只能用目标Windows上已证明的atomic create-if-absent写exact REG_SZ，
在提交点一次性消费ARM token，并以control-generation CAS进入`ARMED_ON_PRELOGIN/ON`；随后
建立默认24小时、硬上限72小时的dormant lease。禁止check-then-force；named mutex只能
辅助；任何同名值都按冲突处理，不能覆盖。

`ARMED_ON_PRELOGIN/ON`是强制 dormant 状态：Run可以调用trust launcher，但没有有效
`LOGIN_COMMITTED`时，launcher必须在加载release、启动supervisor/worker/parser、打开DB/source
或建网前退出；child/DB/config/source/registry额外写/LLM请求全部为0，只允许最小脱敏安全审计。
意外logoff/reboot/login不能改变为运行态。ARM token在CAS前过期或CAS后的dormant lease到期
都不得原地延长；从OP12B-ARM起任一failure/crash partial只能产生预授权OP12B-RB trigger。
OP按journal intent/finalize与ownership nonce reconcile，执行exact conditional delete并回
`PAUSED/OFF`；CAS遇到任意既有同名值（即使同bytes）或之后第三方替换都不得接管/删除，
并进`PAUSED/REGISTRY_CONFLICT`。G12B-CAS由两名满足DAG角色/基数/disjoint规则的reviewer核验exact bytes、token、
20组双进程竞争恰一胜、loser未覆盖、START-S01、START-S02、START-S03、START-S04、START-S05、
START-S06、START-S07、START-S08、START-S09、START-S10与仍无child。

### 10.4 D12B-LOGIN 与一次登录验证

1. D12B-LOGIN由两名满足DAG角色/基数/disjoint规则的reviewer重新验证circuit closed、process0、Run exact bytes、dormant lease、
   generation/release/config/routing/data/auth未漂移，冻结LOGIN_COMMITTED默认5分钟/硬10分钟、
   expected SID、machine/boot generation、previous session、该SID的“下一次新logon”关系、
   single-use nonce、review payload hashes与取消/失败回退；不得预知尚未创建的future session/LUID；
2. 只有G12B-CAS PASS后，用户看到exact value/auth摘要并再次确认已保存工作、明确批准本次
   logoff，OP12B-LOGIN才可以原子写一次性`LOGIN_COMMITTED`并立即执行这一次注销；早先批准、
   沉默或operator判断不能替代；
3. logoff调用失败或取消时立即CAS撤销commit token、persistent pause，并触发OP12B-RB；
4. trust launcher在加载release前原子消费token；缺失、过期、replay、generation/release/auth/
   Run/SID任一漂移都零启动、零外发并回pause；两进程竞争必须恰好一个成功；
5. 成功时只启动bounded `login-validation` profile，核对唯一launcher→supervisor→worker、PID
   identity、首个冻结cycle、scan due、queue timing、无storm/未授权LLM；周期结束自动persistent
   pause，状态为`LOGIN_VALIDATED_PAUSED/ON`且process0；
6. G12B-POST由两名满足DAG exact角色/基数/disjoint规则的reviewer审查，结果只证明登录验证通过并重新暂停，
   不得记录RECOVERED或顺带解除persistent pause。

### 10.5 登录失败回退

若出现任何失败，只能执行已由D12B-RB预审的`OP12B-RB→G12B-RB`：

1. 先 persistent pause；
2. OP invalidate arm/commit/lease tokens；只有提交点current key/name/type/value exact bytes仍匹配本次值才
   conditional delete；若第三方值不同则不碰并报告；
3. 验证 worker/supervisor/parser 为 0；
4. 不删除其他 Run values，不创建替代启动项；
5. G12B-RB由两名未参与OP的reviewer只读核对后归档事件、PID、runtime、日志、DB/source sentinel；
6. CAS conflict/异常、用户取消、token过期/login timeout、意外登录或launcher crash同样执行
   以上流程；不自动重试；
7. 回到对应WP/Gate，不在同次登录反复尝试。

G12B-RB必须逐字继承OP terminal state；它不能把`REGISTRY_CONFLICT`重新标为`OFF`。跨registry/
control/token/journal的任何partial state只能按本次ownership nonce和journal head恢复，禁止猜测性覆盖。

## 11. D12C → G12C-PRE → OP12C → G12C：最终长期激活

G12B-POST成功后仍是`LOGIN_VALIDATED_PAUSED/ON`、Run存在、process0。D12C先由两名满足DAG
exact角色/基数/disjoint规则的reviewer核对所有P0/P1为零、circuit closed、Run/release/auth/config/
routing/data/control generation未漂移，并冻结默认15分钟/硬30分钟的一次性final-activation
token、OP12C/OP12C-RB sealed contract及唯一proposed action/intent hash。D12C不得审查尚未产生
的final授权。用户查看POST摘要后必须单独批准该exact intent hash/action ID下的
`G12C_FINAL_AUTOSTART_ACTIVATION`；登录批准不能复用。拒绝/沉默时保持
`SAFE_PAUSED_WAITING_USER`，不是BLOCKED。G12C-PRE由恰好三名与D12C disjoint的不同角色
reviewer重验actual授权、contract、release与ledger head；只有全PASS才开放OP12C。

OP12C唯一允许的动作是`activate-autostart-final`：CAS把状态改为`ENABLED_IDLE/ON`、generation
恰好+1并消费token。token/control跨资源写前必须向protected journal写入绑定intent/auth/
generation/expected state/ownership nonce的intent，完成后finalize，crash只由OP12C-RB按journal
reconcile。它不得启动当前session worker，不得调用reset/resume/arm，不得写registry/
config/DB/source或改变LLM profile/auth。执行后观察至少20秒，相关进程、DB/config/source/
registry/egress均零变化。

G12C由control/circuit、release/auth/security、runtime operations三名独立reviewer检查ACT-S01、
ACT-S02、ACT-S03、ACT-S04、ACT-S05、ACT-S06、ACT-S07及全部sentinel。三者PASS后物理state前后仍为`ENABLED_IDLE/ON`，只记录
`lifecycle_outcome=RECOVERED`。以后下次正常登录仍须重验release/auth/config/routing/data/Run、
SID、circuit、Job Object与单实例；失败零child并PAUSED/ON。OP12C或G12C失败只能触发
`OP12C-RB→G12C-RB`。owned Run未漂移时OP回`LOGIN_VALIDATED_PAUSED/ON`；第三方Run冲突时
不删除registry并进`PAUSED/REGISTRY_CONFLICT`。两名按DAG与OP执行者disjoint的reviewer继承并
核对OP exact终态；G自身不执行CAS。若用户要当前session立即运行，必须创建另一条新的
D→OP(resume-session)→G；本计划不授权。

G12C通过不等于以后无限运行获得空白授权。每个普通登录与每个后续cycle在DB/file/network前
都必须按`runtime_cycle_policy`密封新operation contract，绑定action-intent/auth、generation/process、
journal head、exact document/source tuples、DB/file write set、egress与持久daily/monthly caps，
并重验expiry/revocation。ACT-S08、ACT-S09、ACT-S10任何一项失败都circuit open+persistent pause，
registry/config/source零写。

## 12. D05Rnn → OP05Rnn → G05Rnn：production circuit reset side lane

每次circuit open使用下一个未用`05R01`–`05R99`，ID/token不得复用。D05Rnn由两名reviewer冻结active
latch identity/generation、脱敏failure signatures、root cause/disposition、用户exact reset token
（TTL≤15分钟）、failure generation、失败节点合法祖先中的exact pending D node与全部downstream
invalidation；G/OP/占位符return均非法。前提是persistent PAUSED、process0、无运行OP、原
release/auth未漂移且不存在未处置P0/P1。

OP05Rnn只能通过control-generation CAS清本次授权列明的active latch/budgets、generation恰好
+1并保留全部历史；状态仍PAUSED、process0。禁止组合reset+resume/arm，禁止registry/LLM/
config/DB/source/release副作用。stale generation、token replay或crash只能得到old/fully-reset两种
状态。G05Rnn由control/circuit与Windows/operations两名reviewer核验RST-S01、RST-S02、RST-S03、
RST-S04、RST-S05、RST-S06、RST-S07、RST-S08、RST-S09。PASS只返回
冻结的pending D node，不直接授权resume。

## 13. 事故证据时间线模板

```markdown
# Incident / Canary timeline

- Revision / Gate:
- Operator / observer:
- Approved scope:
- Start time (UTC + local):
- Initial process/control/autostart state:
- Initial DB/WAL/source/config sentinels:

| Time | PID identity | Stage/progress | CPU/I/O | DB/WAL | Event/action |
|---|---|---|---|---|---|

## Stop trigger

## Pause/stop result and latency

## Data/source/config comparison

## Recovery point retained

## Required WP to reopen
```
