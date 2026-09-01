# Source Catalog Worker 恢复 — 详细实施手册

> 本手册描述未来如何实施，不授权现在实施。  
> 每次只执行一个 Work Package（WP）；不得跨包“顺手修复”。  
> 每个 WP 完成后必须通过对应独立 agent Gate，才能开始下一个 WP。

## 0. 通用实施协议

### 0.1 单个 Work Package 的固定输入

实施 agent 在开始前必须获得并记录：

- `WP ID` 与唯一目标；
- 上一 Gate 的通过记录及 evidence hash；
- 当前 Git HEAD、分支/worktree、dirty files 归属；
- worker、supervisor、parser、自启动入口的隔离状态；
- 本 WP 允许修改的文件白名单；
- 本 WP 禁止修改的文件和生产路径；
- 失败测试、预期实现、回归测试、性能预算和 reviewer 角色。
- 活动`plan_manifest.v4.json`外部预期hash、machine DAG/operation catalog/test registry hashes、
  G00L validator release manifest/version、ledger expected-head与validator计算的eligible node。

如果任务描述缺少任一项，实施 agent 只能补充计划证据，不能修改实现。

### 0.2 通用文件边界

允许修改的实现文件由各 WP 单独列出。始终禁止：

- 测试写入 `config/source_catalog.yaml`；
- 测试打开生产 `.source_catalog/catalog.sqlite3` 的可写连接；
- 写入真实`companies/`、已登记的外部portfolio/cloud-sync source roots或StockWiki；
- 删除 remediation 备份、WAL/SHM、lock 或历史日志；
- 在 OP12B-CAS 之外创建/覆盖 HKCU Run，或在 OP12B-RB 之外删除它；创建计划任务/服务或
  启动无限 supervisor；
- 把非线程安全 `LLMClient` 放到线程池；
- 大范围格式化、重命名或重构不属于当前 WP 的代码。

### 0.3 通用证据包

每个 `evidence/Gxx-<slug>/manifest.md` 至少包含：

1. 时间、agent、Git HEAD、Python/SQLite/PowerShell/Windows 版本；
2. 前置 Gate、worker 隔离和工作树检查；
3. 修改文件及每个文件的目的；
4. 失败测试命令与失败原因；
5. 修复后命令、exit code、耗时和脱敏日志/approved raw evidence opaque ID；
6. 性能原始样本、统计方法、query plan 或阶段计时；
7. mutation/故障注入及其预期失败；
8. 生产路径未变、生产配置未变、源文件未变的证明；
9. 回滚方法和当前可恢复点；
10. 开放风险与 reviewer 所需重点。

每个D/G另返回符合`review_result.schema.json`的machine JSON；落盘后同一 reviewer 再返回符合
`review_confirmation.schema.json`的detached回读确认。Markdown或主agent自填布尔值都不是机器授权来源。

日志过大时先按字段级规则脱敏，再在approved sink保存允许保留的完整日志并在manifest写
opaque ID/HMAC；不得只贴“tests passed”，也不得用“完整日志”绕过证据隐私规则。

secret/token/cookie/credential/`.env` value永不采集。正文默认不采集；必要时须先获用户批准。
其他敏感raw evidence只能放在D Gate冻结的repo外approved sink：无reparse/cloud-sync、精确SID
ACL、静态加密、密钥分离、Gate处置后7天/采集后30天TTL。本目录只写opaque ID、脱敏统计和
不可逆验证标识；可猜测manifest使用repo外key的HMAC。

除纯只读节点和WP-01唯一`TEST_BASELINE_ONLY`例外外，证据必须绑定test-only `Txx`与
implementation `Ixx` commit。D后测试变化会使设计审查失效，详见状态机。

---

## WP-00L：先交付 ledger validator（Gate 00L）

### 目标与边界

在创建正式ledger或执行任何worker预检前，先用全tmp测试交付确定性状态验证器。允许未来修改
`scripts/validate_gate_ledger.py`与对应tests；禁止打开生产DB、registry或网络，禁止执行任一
worker节点。bootstrap证据先进入D00L批准的只追加sink，G00L通过后再回填正式ledger。

### 固定链

```text
T00L -> D00L -> I00L -> G00L -> D00
```

1. T00L先用专用instance schema验证DAG/vectors/test-registry/operation-catalog，证明空object、
   array和scalar均被拒绝；再实现`gate_ledger_validator_vectors.v4.json`中GL-S01、GL-S02、GL-S03、GL-S04、GL-S05、
   GL-S06、GL-F01、GL-F02、GL-F03、GL-F04、GL-F05、GL-F06、GL-F07、GL-F08、GL-F09、
   GL-F10、GL-F11、GL-F12及TESTID-S01，先红；
2. D00L一名独立reviewer审schema、DAG、负例归因、stdlib/全tmp边界；D后vector/assertion不变；
3. I00L实现canonical JSON、seq/prev/expected-head、exclusive atomic append、review+confirmation
   actual hash、branch/join/cardinality/role/invalidation/auth/operation/state/test-ID与只读`next`；
   不信任record自报字段；另生成冻结未来脚本/tests/runtime的`validator_release_manifest.v1.json`；
4. G00L两名满足DAG角色/基数/disjoint规则且未参与T00L/I00L的reviewer各跑全量vectors和至少一个新反例；property sequence≥200、mutant
   survivor=0、production/network调用0；
5. I00L后先生成到I00L terminal的canonical bootstrap transcript候选和external head；只有D00L
   review可null head，G00L两份payload必须绑定该候选head与validator release hash。两人完成
   detached confirmation后，以候选原字节加G00L terminal record一次性初始化正式ledger并全链回读，
   再允许D00；不得在G00L后重新序列化历史。

详细命令、canonical bytes与GLV reason codes只能取自`ledger_validator_contract.md`。

---

## WP-00：重新基线化与隔离确认（Gate 0）

### 目标

证明开始实施时的代码、进程、配置、数据库容量和并行任务状态可控，并识别 2026-08-22
计划与实际代码之间的漂移。此 WP 只读，不修改实现。

### 前置条件

- 用户已经明确要求开始实施某一阶段；仅“阅读本计划”不算授权。
- 本计划仍未被另一个计划替代。
- 生产 worker 预期仍为 paused/stopped，自启动预期仍关闭。

### 执行步骤

1. 完整读取本目录全部计划文件并核验当前revision；不要修改冻结`task_plan.md`。G00L必须
   已通过；使用validator的`validate`与`next`重建状态，确认D00 eligible后才追加D00/OP00。
2. 记录 `git rev-parse HEAD`、`git status --short`、当前分支与 worktree 路径。
3. 对每个 dirty file 标出 owner；无法归属的文件禁止触碰。特别核对
   `normalizer.py`、`worker.py`、`store.py`、`scanner.py`、`control.py`、
   `scripts/source_catalog_worker.ps1` 和相关 tests。
4. 使用 CodeGraph 获取上述核心符号的定义、调用者、被调用者和影响面；记录相对报告
   基线新增/删除/重命名的符号。不得用旧行号直接编辑。
5. 只读核验 worker/supervisor/parser 进程、runtime/control JSON、operation lock 所指 PID
   的 executable 与 creation time。只记录 stale lock，不删除。
6. 只读核验 HKCU Run、相关计划任务、Windows 服务、Startup 文件夹；若出现新入口，
   立即停止并报告，不能自行删除。
7. 运行配置卫生检查。若 `config_doctor.py` 可能写文件，先审查代码并在 tmp 副本上跑；
   只有已证明只读时才指向生产配置。
8. 用 SQLite URI `mode=ro` 打开生产 catalog，并立即设置 `PRAGMA query_only=ON`；只获取
   schema version、page count/page size、表行数和状态分布。禁止执行旧慢队列查询，
   禁止 `ANALYZE`、`VACUUM`、DDL 或自动 migration。
9. 记录 DB、WAL、SHM、备份大小和卷剩余空间；不要创建生产 DB 的临时全量副本。
10. 对核心文件与原始调查报告记录的 commit/hash 做漂移表：未变、已变且相关、已变但
    无关、无法判断。相关漂移必须回到证据链重新验证。
11. 把`tests/contract/test_zr1002_reader_first.py`和
    `tests/contract/test_zr1003_shadow_assertions.py`纳入基线命令，记录其当前fixture依赖missing DB
    触发eager init的事实；只记录，不在WP-00改测试或产品。

### 必须产出

- `evidence/G00-baseline/manifest.md`；
- `git-status.txt`、`process-inventory.txt`、`autostart-inventory.txt`；
- `code-drift.md`、`catalog-readonly-baseline.md`、`space-budget.md`；
- 明确声明生产配置、DB 和源目录未被写入。

### 测试/检查点

- worker/supervisor/parser 数量均为 0；若不是 0，Gate 失败；
- `desired_state=paused`，或记录了更严格的停止状态；
- 没有未经解释的自启动入口；
- dirty files 全部有 owner，当前 WP 没有覆盖它们；
- 只读连接可查询，小心关闭后 DB/WAL/SHM mtime 未变化；
- 可用空间满足后续 tmp fixture，且未承诺生产索引空间。

### 独立审查

派出“基线与隔离审查 agent”。它必须重新检查进程/启动入口快照、文件归属、SQLite
只读方式和 mtime 证据。`PASS` 后才能进入 WP-01。

---

## WP-01：生产形状 tmp 夹具与红灯测试（Gate 1）

### 目标

构造能稳定重现相关子查询退化、又绝不接触生产数据的确定性测试资产。先证明旧实现
失败，再允许改 SQL。

### 允许修改

- 现有最贴近的 source-catalog SQL/worker contract test；
- 必要时新增一个明确命名的性能 fixture helper；
- **禁止修改production code或增加seam。** 若公开接口不足，D01必须FAIL；所需seam与SQL
  修复一起进入I02A。

优先扩展现有 `test_source_catalog_sql_pushdown.py`、`test_source_catalog_worker.py`、
`test_source_catalog_long_running_observable.py` 等契约；先核对实际内容，不得仅凭文件名。

### 夹具数据合同

1. 使用固定 seed；document IDs、timestamps 和 priorities 可预测。
2. 默认规模 25,000 documents、50,000 locations；另提供小规模语义夹具。
3. active/inactive root、active/retired location、`original_primary`/其他 role 均有覆盖。
4. 至少包含：无 location 文档、多个 location 文档、重复 location、缺失 root 防御样本。
5. 对 primary source 同时包含：active role/source 都匹配、role 匹配但 source 不匹配、
   source 匹配但 inactive、多个 location 中仅一个匹配、无任何 parseable primary。
6. artifact 覆盖 absent、completed、partial、unsupported、retryable failed（due/not due）、
   terminal failed，以及不同 generator/version。
7. document kind 与创建时间分布必须让 `ORDER BY priority, document_id` 可断言。
8. 所有 path 指向 `tmp_path` 下的占位文件；生产配置和源目录字符串也不得出现在 DB。
9. 构建应使用批量 insert 与单事务，避免 fixture 自身成为数分钟瓶颈；session cache 若被
   使用，必须只缓存不可变模板，每个测试从模板复制到独立 tmp DB。

### 测试先行步骤

1. 写小规模“语义 oracle”：用清晰但可慢的 Python/SQL 参考实现计算期望 document IDs。
2. 对旧队列接口断言返回集合、顺序、retry 和 terminal 语义。
3. 明确业务 oracle：没有 active、role=`original_primary` 且
   `location.source_id=document.primary_source_id` 的文档永不返回；但这些文档必须大量保留
   在 outer fixture，以捕获坏 plan，不得从数据集预删。
4. 对 `force=False/True` 分别定义 completed、retryable、terminal、generator/version；不把
   non-force 断言错误套在 force 模式。
5. 写生产形状 plan guard：不比较完整 plan 字符串；只拒绝已知灾难形状，并要求候选
   location 集合被物化/先筛选或使用 document-oriented lookup。
6. 写有界性能测试：
   - SQLite progress handler 计数 VM work 或设置严格中止预算；
   - 保留宽松 wall-clock 上限作为 smoke，而非唯一判据；
   - 旧实现超过预算时必须被中止，测试不能挂 900 秒。
   - D01冻结PROGRESS_PROXY_APPROX或STMTSTATUS_VM_STEP_EXACT。proxy保存`progress_n`、handler
     安装点、Python/SQLite source-id、PRAGMAs、params/LIMIT/fixture digest与callback count×n，
     只称近似proxy，禁止exact step区间；exact模式冻结native binding/consume/overflow合同。
     Q-P01、Q-P05、Q-P06（exact另Q-P07）对metadata/错误表述fail closed。
   - VM measurement callback不得读control/file/DB；D04取消handler使用独立harness。分别报告
     有/无measurement handler的wall time。
7. G01 只证明旧实现超过 work budget；把新查询回替旧 SQL 的正式 mutant 留给 G02A/G09，
   因为 G01 时新查询尚不存在。
8. 写路径哨兵：测试前后确认生产 config/catalog/source roots 的 size+mtime 不变。

### 通过本 WP 前必须证明

- 小型语义测试在旧实现上可运行且 oracle 本身正确；
- 至少一个性能/plan 测试在旧实现上因目标退化明确失败；
- 失败发生在限定时间内，测试进程可回收；
- fixture 两次生成的 row counts、关键 IDs 和 DB hash/逻辑摘要一致；
- warm样本至少30次、cold-ish至少10次，nearest-rank；样本不足20时用max而非P95主判，
  报告全部raw样本并区分 fixture build 与 query time。
- T01 diff只含fixture/test/test helper；没有I01。G01时旧产品性能红灯仍应稳定存在。

### 独立审查

“测试设计/性能方法审查 agent”必须检查代表性、可重复性、时间断言稳定性、oracle 独立性
和 mutation 杀伤力。没有 `PASS` 不得改 SQL。

---

## WP-02A：normalize queue SQL 等价改写（Gate 2 的第一部分）

### 目标

消除对 active locations 的相关重复扫描，同时保持候选资格、失败重试、生成器版本、
terminal 状态、优先级和稳定顺序完全一致。

### 允许修改

- `src/company_wiki/source_catalog/normalizer.py` 中实际队列选择函数；
- 只有查询参数/公开契约确有需要时才修改相邻 store helper；
- WP-01 的相关 tests。

### 明确禁止

- 在本 WP 同时优化 parser、scanner 或 LLM；
- 用缓存返回旧结果；
- 从outer fixture删除locationless/source-mismatch rows来降低扫描量，或改变priority伪造性能；
  队列结果本来就必须排除这些无parseable-primary rows；
- 仅运行 `ANALYZE`；
- 在启动路径自动创建大索引。

### 实施步骤

1. 从实际代码提取旧查询语义表：每个 JOIN/WHERE/NOT EXISTS/CASE/ORDER BY/LIMIT 条件
   各写一行，并映射到测试样本。
2. 对 roots join 做单独决策：
   - 若它只用于保证 location root 存在，先用外键/孤儿测试证明能否删除；
   - 若它承担 active root 或隔离语义，必须保留等价过滤；
   - 不允许因“似乎多余”直接删除。
3. 首选非相关 candidate set、semi-join 或 CTE，一次构造有资格的 document IDs，再关联
   documents/artifacts。不得让 locations 相关子查询对每个 document 重扫 status 索引。
4. parseable-primary candidate 必须连接 `(document_id, primary_source_id)`，不能只按 document
   检查 role/status；source mismatch 即使 role active 也排除。
5. force/non-force 分别实现并验证，不假设 terminal/completed 在 force 下仍被排除。
6. 保留 parameter binding，禁止字符串拼接 ID、状态或 version。
7. 保持稳定 `ORDER BY`；若 priority 表达式变化，用 oracle 对所有 kind 分支验证。
8. 使用现有索引在生产形状 tmp fixture 上跑 plan、VM budget、N/2N scaling 和 wall time。
9. 对修复前后小型随机数据做 property comparison；至少 50 个 seed，比较完整有序结果。
10. 对 retry 时间边界使用假时钟或固定时间，不依赖真实当前时间。
11. 定义current normalized为generator/version/schema/status与当前primary source ID/content SHA
    全匹配；S1→S2时旧completed/terminal/retry不能抑制S2，UPSERT原子更新source ID/hash。
12. Q-S17覆盖source rotation并在G09加入把S1 artifact错绑S2的集成mutant。

### 退出标准

- WP-01 红灯测试全部转绿；
- 参考 oracle、旧意图与新实现的 ordered IDs 完全一致；
- warm-cache n≥30且P95<2秒，cold-ish新进程/connection n≥10且max<10秒，并有plan、work proxy/
  exact counter、N/2N与wall一致改善证据；
- plan 不再含灾难形状；
- 小数据性能没有不可解释的大幅倒退；
- 未新增索引也能达到预算，或有证据进入 WP-02B 决策。

### 回滚点

SQL 改写必须是独立 commit。回滚该 commit 后，WP-01 的 mutation/performance test 应重新
失败，而原 contract tests 仍能运行。这一行为是测试有效性的证据，不要求在生产回滚。

---

## WP-02B：verify-only store 与索引/迁移分支（Gate 2 第二部分）

### 分支选择

G02A后先派两名只读reviewer执行G02B-ADR，基于跨版本/无stats/倾斜、空间与write-amplification
冻结唯一ADR-02。ADR前不创建02B tests。之后只走一条完整链：

```text
NO_INDEX: T02B-NI -> D02B-NI -> I02B-NI -> G02B-NI
INDEX:    T02B-IDX -> D02B-IDX -> I02B-IDX -> G02B-IDX
```

未选分支不创建commit、不执行、不写ledger。两个选项各自的T commit都必须含M-COM-S01、
M-COM-S02、M-COM-S03、M-COM-S04、M-COM-S05、M-COM-S06、M-COM-F01、M-COM-F02。
选中分支还必须把ZR1002/ZR1003的tmp夹具迁移为显式`schema init/upgrade`后reader open：
`M-COM-S05`证明显式路径幂等，`M-COM-S06`证明reader/worker/login/canary没有eager DDL。
禁止通过恢复`CatalogStore`普通构造时建库来让旧fixture变绿。

只有查询改写仍不稳定，或索引有经量化的必要收益时选择IDX；不能因“可能更快”默认迁移。

### 候选比较

- 无新索引；
- 以 `document_id` 为首列、覆盖 role/status/root 条件的复合索引；
- 符合 SQLite 版本约束的部分索引；
- 已有索引重排/替代，但不得为了省空间直接 drop 生产索引。

对每个候选记录：query P50/P95、VM work、索引 bytes、构建时长、insert/update 写放大、
planner 稳定性、旧 SQLite 兼容性和 rollback 成本。

### 迁移安全设计

1. ordinary open合同：exact existing schema成功且零DDL；missing DB返回SCHEMA_INIT_REQUIRED且
   文件创建0；old schema返回SCHEMA_UPGRADE_REQUIRED且零DDL。
2. 只有operator命令`schema init --profile NO_INDEX|INDEX`与`schema upgrade --profile ... --to
   <exact-version>`可建/迁；先在生产规模tmp，再在生产DB恢复副本；不直接试生产。
3. schema migration显式、版本化、幂等；普通worker/login/canary不可达init/upgrade。
4. 当前 `CatalogStore.__init__` 会运行 `_DDL`/additive migrations；禁止只把新索引追加到
   eager `_DDL`。设计 operator-invoked migrator 与 verify-only normal open，并用 SQLite
   authorizer 拒绝 DDL 验证普通启动。
5. 预计算峰值空间：现有 DB + 现有 WAL/SHM + 新索引估计 + journal/WAL 峰值 + 备份 +
   固定安全余量。空间不足必须 fail closed。
6. 模拟partial init/upgrade、重复、已存在正确对象、同名错误对象、磁盘满；验证DB
   可重新打开且 schema ledger 一致。
7. 磁盘满只用 faulting VFS/facade 或硬 quota 独立 scratch，不填满真实 C:。
8. 迁移前后运行 `integrity_check`/适当轻量检查；完整检查在副本上完成。
9. 不把 `DROP INDEX` 作为自动 rollback；失败回到恢复策略并人工决策。

### G02B-NI / G02B-IDX 独立审查

必须同时派出：

- reviewer A：SQL 语义、priority、retry/terminal、随机 oracle；
- reviewer B：SQLite plan、索引列顺序、迁移幂等、空间与写放大。

每个分支D/G各两名reviewer；只有validator确认所选G为PASSED或合规PASSED_WITH_P2才进入T03。

---

## WP-03：扫描 checkpoint 与恢复事实源（Gate 3）

### 目标

scan 已成功提交后，即使 normalize/LLM/export 随后失败，下一次启动也不应立即重复全盘
扫描；同时不能把未完成 scan 错标为成功。

### 允许修改

- `worker.py` 中 scan due、scan 完成与周期 state 落盘逻辑；
- `store.py` 中现有 `scan_runs` 读取/事务 helper（如需要）；
- `control.py` 或 state schema helper（只限原子状态写与兼容读取）；
- worker/state/scan contract tests。

### 推荐状态合同

1. `scan_runs` 中已提交且按 per-root outcome 判定 checkpoint-eligible 的 run 是扫描事实；
2. JSON state 是快速调度 checkpoint，可从最新 committed scan run 重建；
3. 顺序必须是：扫描 DB 事务提交 → 读取/确认 committed scan ID 与完成时间 → 原子写 JSON；
4. 若 DB 已完成但 JSON 写失败，重启时从 DB 对账并修复 JSON，而不是重扫；
5. 若 JSON 声称完成但 DB 没有对应 completed run，视为不可信并 fail safe；
6. 时间同时记录 UTC wall clock 与进程内 monotonic duration；调度不用可回拨 wall clock
   计算当前操作超时；
7. state schema 增量向后兼容，未知字段保留或安全忽略，旧文件可读。
8. checkpoint 包含 root-set、相关 config、scanner schema/version fingerprint；变化时只让
   受影响 root due。
9. `completed_with_errors` 不做一刀切：benign per-file quarantine 可推进该 root；root offline、
   partial enumeration、权限错误保持该 root due/退避，不能拖累所有成功 root，也不能被
   误当全局完成。

### 测试步骤

1. 先写当前实现失败的测试：scan 成功后在 queue select 前抛出受控异常，重启后断言
   scan 不 due。
2. 在以下边界注入 crash：DB commit 前、DB commit 后/JSON 前、JSON temp write 后/rename 前、
   JSON 完成后、normalize 中、LLM 中、export/prune 中。
3. 每个 crash 后新进程读取真实落盘状态，而不是复用内存对象。
4. 测试损坏 JSON、旧 schema、未来未知字段、时钟回拨、重复 scan ID。
5. 测试真正未完成的 scan 会重试，不能因修复而永久跳过。
6. 测试 scan interval 边界：刚完成、恰好 due、明显 overdue。
7. 测试 `completed_with_errors` 的 benign quarantine、root access denied、partial enumeration、
   root增删、config/scanner version变化和 per-root retry。

### 退出证据

- 故障矩阵每一格都有预期与实际；
- DB/JSON 不一致窗口被显式对账；
- 原子写使用同目录 temp + flush/replace 的现有安全模式，不发明易损写法；
- 没有把“完整周期成功”与“扫描成功”混成一个时间戳；
- 独立恢复语义 reviewer `PASS`。

---

## WP-04：SQL 取消、heartbeat 与阶段遥测（Gate 4）

### 目标

让长 SQLite 操作可见、可限时、可响应 pause/stop，同时避免“只加 heartbeat 让坏查询
永久跑”的反修复。

### 设计约束

- 性能修复 WP-02 必须先通过；heartbeat 不能替代复杂度修复。
- SQLite progress callback 内不得用同一 connection 执行 SQL，不得做网络请求或重日志。
- callback 读取 monotonic deadline，并通过预先审查的低频外部 control-generation read，或
  由线程安全 watcher更新 event；禁止只捕获 query-start token 后永不刷新。
- handler 必须在 `finally` 中清除，避免泄漏到后续查询或 parser 持久化。
- pause、stop、deadline 应映射到可区分的内部错误/结果，不能伪装成 DB corruption。

### 实施步骤

1. 为 queue selection 建立明确操作上下文：stage、start monotonic、deadline、rows/attempt。
2. 给 SQLite connection 临时安装 progress handler；先 benchmark 不同 instruction interval，
   选择额外开销可测且低于验收阈值的频率。
3. callback 到达 heartbeat 周期时只调用非 SQL、原子且有节流的 control/runtime 路径。
4. 检测 stop/pause 或 deadline 后返回中断信号；上层捕获后记录标准 reason，并安全关闭
   transaction/connection。
5. runtime 增加 `stage_started_at`、`last_progress_at`、`progress_counter`、`stage_detail`；
   不记录文件正文、prompt、环境变量或 access token。
6. scan 记录 per-root enumerate/observe/commit；normalize 记录 queue_select/parse/persist；LLM、
   export、prune 各自计时。字段应有版本/兼容处理。
7. runtime 分离 `liveness_heartbeat`、`vm_activity_counter`、`business_milestone`；VM activity
   只说明查询在执行，不能证明业务推进或重置失败。

### 测试

- 人工构造慢 SQL，在 pause/stop 后于 SLA 内中断；
- 由另一真实进程在 query 开始后更新 control generation，避免只测预置 token；
- deadline 中断与 pause 中断原因不同；
- handler 异常也会在 finally 清除；
- 下一条正常 SQL 不继承旧 deadline/token；
- 快查询开销相对无 handler 基线低于既定阈值；
- heartbeat 只在真实操作存活时前进，冻结 callback 后 watchdog 仍能发现无进度；
- runtime 写失败不造成 DB transaction 半提交或进程无限异常循环；
- 日志隐私 snapshot 不含正文和 secrets。

### 独立审查

取消/可观测性 reviewer 必须特别寻找 connection handler 泄漏、callback re-entrancy、
假 heartbeat、异常分类错误和日志敏感信息。`PASS` 后进入 WP-05。

---

## WP-05：supervisor 健康状态机、退避与熔断（Gate 5）

### 目标

消除“运行满 900 秒便清零失败计数”的逻辑，确保长命但无成果的 worker 会退避并最终
停止自动复活；pause 永远优先。

### 允许修改

- `scripts/source_catalog_worker.ps1` 中 watchdog、restart reset/backoff；
- 必要时 `control.py`/worker runtime 的健康里程碑字段；
- 已有 worker bootstrap/background reliability/control tests；
- Windows 专项测试 helper。

### 健康合同

- `uptime` 不是成功；
- 只有完整周期成功才能清零失败计数；其他里程碑只更新诊断/进度；
- heartbeat 表示“还活着”，progress counter 表示“有推进”，两者都不等于周期成功；
- 失败签名至少包含 stage、标准 reason、退出码/timeout 类型；敏感 detail 先规范化；
- 相同签名连续失败采用有上限指数退避；测试注入时钟与 RNG，避免真实等待；
- 同时记录全局滚动失败次数和无完整成功时长；交替签名、supervisor 重启、login/reboot
  不能重置。
- 达阈值后持久circuit latch并persistent pause。生产reset只能实例化一次性
  `D05R01`–`D05R99`→`OP05R01`–`OP05R99`→`G05R01`–`G05R99`；D冻结root cause、用户token、generation/TTL和return node；
- circuit open时resume/resume-session/arm/login/activate都返回CIRCUIT_OPEN且零副作用；OP05Rnn
  只清active latch/budget、generation+1，保留历史，仍PAUSED/process0且不写registry/LLM；
- pause/stop 在任何 backoff 或 launcher startup delay 中都能及时生效；
- PID 操作必须匹配 PID + creation time + expected executable/command identity。
- control/runtime 必须含 session/attempt/token/PID creation/code fingerprint/sequence；缺失或
  损坏 control/circuit 在受管生产 fail closed。
- 保留 Windows Job Object 的 create/assign/kill-on-close；assignment failure不降级裸启动。
- 120 秒登录 delay 移到每 supervisor/login session 只执行一次；child restart不重复支付。

### 实施步骤

1. 先用状态转移表描述 child start、heartbeat、progress、cycle success、timeout、exit、pause、
   control stop、circuit open；review 状态表后再写 PowerShell。
2. 把决策逻辑尽量抽成可在无真实进程情况下测试的纯函数/小 helper；不得引入第二套
   control state。
3. 失败计数只在成功里程碑递增/清零规则下变化；进程活 901 秒后失败仍算连续失败。
4. backoff 期间轮询/事件等待 control，不用不可中断长 sleep。
5. circuit open 时 supervisor 退出并留下可诊断状态；下次登录 launcher 看到 persistent
   pause 不启动 child。
6. 成功周期后验证active failure count、signature和backoff按合同清理且历史audit保留。
7. 实现五条互斥CLI路径：reset-only、resume-session-only、arm-only、login-commit-only、
   final-activation-only；禁止组合flag或隐式调用。生产reset入口强制校验D05Rnn token。

### 必测状态序列

1. `<900s` 快速失败三次；
2. `>900s` 无 progress 后失败三次；
3. 长 query 有 heartbeat 但 progress 不前进；
4. 五个正常周期；
5. 两次失败 → 一次成功 → 一次失败；
6. 两种不同失败签名交替；
7. backoff 中 pause；
8. startup delay 中 pause；
9. PID reuse：同 PID、不同 creation time/executable；
10. stale runtime、损坏 control JSON、clock rollback；
11. circuit open 后再次运行 login launcher；
12. D05R01→OP05R01→G05R01后20s进程仍0，G后只回冻结review node；直接resume仍拒绝。
    若未来需要session启动，必须另过对应生产D/OP/G；普通resume绝不清circuit（S-S18）。
13. 交替签名仍触发 global circuit；supervisor/reboot 保留 budget。
14. Job Object assignment failure 与 supervisor crash 后无 orphan parser。
15. 多次 child restart 只支付一次 login startup delay（S-S13）。

### Gate 5 独立审查

- reviewer A：状态机、failure signature、backoff/circuit 正确性；
- reviewer B：Windows 进程身份、pause 优先级、登录链与误杀风险。

两者都必须 `PASS`。禁止用一次手工成功启动代替状态序列测试。

---

## WP-06：扫描性能与电源调度（Gate 6）

### 目标

在不改变来源身份、去重、retire、安全边界和可恢复性的前提下，减少 46k 文件等价扫描
的枚举与逐文件元数据开销，并避免电池模式先全扫后 gate。

### 顺序要求

1. D06先冻结exact baseline commit与协议。若需埋点，先形成instrumentation-only revision，
   再从它分叉旧/新，保证topology/environment/instrumentation hash相同；
2. 再做一项优化；
3. 每项单独比较并通过语义 tests；
4. 不得把多种缓存/批处理合成一个无法归因的大提交。

### 基准拆分

每个 root 记录：enumerate、sidecar load、path normalization、DB existing-state fetch、observe、
hash、DB commit；同时记录 files seen/reused/hashed/new/retired/error。至少构造：

- 46k 全部 unchanged；
- 1% 修改；
- 10% 新增/删除；
- sidecar 少量变化；
- root 暂时不可达；
- junction/symlink、大小写、Unicode、长路径；
- 扫描中断并恢复。

release topology 必须接近现场结构，而非单 flat directory：约 244 company walks、16,570
groups/sidecars、429 Dropbox-like directories、9,853 groups、总计约 46,600 files。CI 可有
固定比例小档，但 Gate 6 使用完整档。

baseline/candidate每场景各n≥10，预声明warm-up与交替顺序，全部新进程、无outlier删除。
历史427秒只作外部参考；正式speedup只用同协议
`baseline_P95/candidate_P95`。SC-P04要求两边topology/environment/instrumentation hashes全匹配。

### 推荐优化顺序

1. 把 power eligibility 与用户活动策略移到昂贵 scan 之前；明确哪些轻量 control/health
   动作即使在电池上仍允许。
2. 一次批量读取现有 `(normalized_path,size,mtime_ns,identity/status)`，减少 N 次 DB 查询。
3. 使用现有路径规范化策略避免重复 resolve；不得因优化改变 Windows 大小写/UNC 语义。
4. sidecar JSON 以稳定签名缓存，但 sidecar 改变必须使相关观察失效。
5. 批量 observe/commit，测量 writer lock 持续时间，设置可取消边界。
6. 再评估增量扫描。**禁止只依赖顶层目录 mtime**，因为 Windows 嵌套变化不保证传播。
   增量方案必须有 per-file path/size/mtime_ns 或等价游标，并保留周期性全量校验。
7. 对 metadata 未变的内容 tamper 设置默认检测 SLA：每日确定性重 hash 至少 3.34%，调度覆盖
   全量不超过 30 天；高风险/identity 变化即时 hash。放宽需 ADR。

### 安全语义

- root 暂时不可达不得把所有文件误判 retired；
- junction/symlink 不得逃逸已注册 root 或写入目标；
- unchanged 文件不得重新 hash，changed 文件不得被错误复用；
- files_seen/reused/hashed 与最终 DB 状态能对账；
- 中断后的 `scan_runs` 明确 failed/interrupted，不能 completed；
- 所有源文件测试使用 tmp root，并在测试前后比较 hash/size/mtime。

### 退出标准

完整topology unchanged candidate P95≤120秒且`baseline_P95/candidate_P95≥2.0`；统计按
`acceptance_thresholds.md`。未达标不能用“明显改善”通过。独立 scanner reviewer 必须
复核缓存失效、30天 rehash SLA和源文件不变性后 `PASS`。

---

## WP-06P：Parser 分格式 Profile 与边界（Gate 6P）

### 目标

SQL真正出队后，按实际代码route而不是笼统格式验证性能、资源、timeout和cleanup。v4基线
route为plain text、HTML、MHT HTML/MHT fallback、PDF fallback/Docling、DOCX、DOC、XLSX、
XLS、PPTX、JSON、XML/XSD与unsupported；候选代码变化时以P-FMT00-ROUTE重新冻结digest。

### 步骤

1. T06P生成candidate route digest，与`test_id_registry.v4.json`/release enablement三方对照。
2. 每route实例化S bucket（n≥20/P95；多extension各≥5）；M启用则n≥10/max，不启用则
   `P-DIS-<code>-M`≥5且parser启动0；重复文档不算独立样本。
3. 每route实例化P-LIMIT oversized≥5、适用P-ERR corrupt/encrypted各≥10或明确P-NA，执行
   route的P-PAUSE n≥20；antiword还核验grandchild。
4. 记录route/extension/digest、queue exit→child start、parse wall/CPU/peak memory、结构量、
   persist、timeout/error；raw outlier全保留。
5. >100MiB或结构上限默认deferred/unsupported；任何配置放宽使G06P/G10R失效。
6. 每route/bucket单独通过或禁用；缺fixture不能PASS，HTML与plain-text不得合并分母。

### Gate 6P

独立 parser reviewer 检查代表性、timeout、memory、child cleanup 和错误持久化。只启用已通过
格式；未通过格式的 fail-closed 必须在状态/UI 可见。

---

## WP-07：LLM 吞吐、失败策略与隐私（Gate 7）

### 目标

在 SQL/扫描恢复后避免 LLM 成为不可控 backlog，并明确真实文本外发授权。此 WP 不允许
用“直接多线程”解决非线程安全 client。

### 分析步骤

1. 用脱敏历史 timing 或 stub 分布建立 queue model：arrival rate、service rate、batch、
   retry、permanent failure、每日运行窗口；输出 1/7/30 天 backlog 情景。
2. 分类 650 条 permanent failure：输入不可解析、provider policy、schema validation、超长、
   非重试 HTTP、历史 bug；分类过程不得把正文复制进报告。
3. 明确current normalized同时匹配generator/version/schema/status、当前primary source ID/hash；
   summary还匹配normalized artifact ID/hash与request digest。S1→S2时旧结果不能抑制或被绑成S2。
4. 先定义queue oracle：每文档只选一个上述current artifact；旧/失败/stale-source summary可
   重生；LIMIT前稳定dedupe。L-S18覆盖source rotation。
5. cache key 改为截断后 exact canonical request（正文、title、kind、source、system prompt、
   provider/model、generation params、routing contract）digest。仅缓存验证过的 provider payload，
   每个 document 重新渲染/绑定 artifact 与 locator。
6. 比较单文档、批量多文档、公平调度。批处理必须逐文档验证输出映射，
   一个坏结果不能污染整个 batch。
7. 只有先把 client 重构成独立无状态请求上下文并证明限流/成本记录线程安全，才允许另开
   并发 WP；本计划默认保持单线程。
8. 建立 provider/fallback allowlist、最大字符、字段最小化、timeout、rate limit、成本上限和明确
   failure taxonomy。任何新增 provider 或真实全文 canary 需用户另行批准。
9. 数值 SLO：base completion≥1.2×arrival、backlog≤7天清零、oldest正常≤24h/high≤72h；
   1/7/30-day queue与成本模型。cost cap未填则不能启用 provider。
10. 在网络前持久化request ledger：PREPARED(request/source/provider/auth hash/cost reservation)
    →IN_FLIGHT；随后只允许RESPONSE_VALIDATED→COMPLETED、RETRYABLE_FAILED、
    PERMANENT_FAILED或OUTCOME_UNKNOWN。只有能证明未接受，或provider支持同一idempotency
    key/result lookup时，才可进入可自动重试路径；普通post-send timeout/含糊5xx不得如此。
    重启发现IN_FLIGHT转OUTCOME_UNKNOWN且不自动重发；无法lookup时只能人工处置。
11. OUTCOME_UNKNOWN最大预计费用继续占cap；响应先验证并不可变落盘再对账artifact/cache/usage。
    RESPONSE_VALIDATED后的本地commit可幂等重放，但不得再次调用provider。
    ledger不存正文/prompt。G07E只冻结schema contract，不能触发生产DDL；必须等待G11B-A3，
    再由G11M-L-ADR两名reviewer判断。SCHEMA_DELTA才走D11M-L/OP11M-L/G11M-L。

### 测试

- 全部自动测试使用 deterministic LLM stub，禁止网络；
- stub 覆盖 42s 等价延迟（用假时钟）、timeout、429、5xx、invalid JSON、partial batch、
  permanent rejection 和进程中断；
- 验证retry budget、terminal、source/cache invalidation、L-S20六个crash点与L-S21支持/不支持
  idempotency两类provider；不再无条件宣称exactly-once外部计费；
- 检查日志、runtime、review evidence 不含正文、prompt secrets 或 token；
- 模拟 normalize batch 3 / LLM batch 1，证明新策略达到 drain 目标或显式限制生产率。

### 生产 canary 约束

Canary A始终LLM off+network deny。只有G11B-A3+G07E及条件G11M-L通过，才可按状态机对primary
BP与每个fallback BFnn分别做D/OP/G；每个provider使用新的单次stage-bound授权，primary授权不
传fallback，完成立即pause。

12A/12B各使用新的授权，Canary B不沿用。LLM off必须走T07O/D07O/I07O，并在G09P有效后
G07O审production/session/launcher强制off、应用层fail-closed和主/备egress deny；G07E失败不能
自动视为G07O通过。

### 独立审查

G07E reviewer检查source freshness、吞吐、request ledger/outcome_unknown、失败、单线程、
数据最小化、provider独立授权与成本；G07O reviewer检查L-S17/PX-S07和UI状态。任一未授权
外发为P0。两分支exactly-one且分别使用独立T/D/I/G证据。

---

## WP-08：retention、容量与运维安全（Gate 8）

### 目标

修复已知 retention 属性错误并建立容量可见性，但不在本 WP 删除任何生产数据或备份。

### 子任务 A：retention bug

1. 在 tmp project root 与假时钟中重现 `_project_root`/`project_root` 异常；
2. 覆盖无日志、边界日期、保留中、过期、文件被占用、权限拒绝、路径逃逸；
3. 修复必须先 resolve 目标并验证位于明确日志目录；不得递归处理宽目录；
4. dry-run 与实际 tmp 删除分别测试；生产默认只报告候选，不自动清理。

### 子任务 B：SQLite 容量报告

1. 复用/扩展 `catalog_size_report.py` 前先检查现有契约；
2. 首选只读 PRAGMA、page/freelist、index metadata；`dbstat` 缺失时不能失败或偷偷安装扩展；
3. 逐表精确 bytes 若只能通过副本/支持 dbstat 的环境获得，报告必须标注估算而非伪精确；
4. 对新索引只在 tmp fixture/恢复副本测构建与大小；
5. 报告 DB、WAL、SHM、备份和卷余量，但不自动 `VACUUM`/DELETE/DROP。
6. 所有 ENOSPC tests 使用 faulting VFS/facade 或硬 quota 独立 scratch，禁止填满真实卷。

### 子任务 C：日志与敏感配置

1. 设计 worker stdout/stderr/JSONL 的 rotation、max files、max age 与正在使用文件保护；
2. rotation 测试只在 tmp 日志目录；
3. 审计 `.env` ACL 时只记录权限主体与风险，不读取或复制 secret values；
4. ACL 修改属于独立授权操作，不在此 WP 自动执行；
5. 记录 evidence raw_text/span_json 重复占用的测量方法，任何压缩/去重另立 migration WP。
6. secret/token/cookie/credential/`.env` value永不采集；正文默认不采集。获批raw evidence只进
   D08冻结的approved sink，要求SID allowlist ACL、加密/密钥分离、无reparse/cloud-sync、
   7/30日TTL与inventory精确清理；仓内只存opaque ID/脱敏统计/不可逆标识。
7. EV-S01、EV-S02、EV-S03验证secret注入零明文、非法root/宽ACL/未加密fail closed，以及TTL/audit hold；
   到30天未结案的Gate BLOCKED并重新取证，不能静默延长。

### 独立审查

容量/安全 reviewer 必须确认无隐含 destructive action、路径验证充分、空间估算保守、
`.env` 证据未泄密。`PASS` 完成 H8；下一节点按 `gate_state_machine.md`，不得按编号跳转。

---

## WP-09P：生产执行封装与安全边界（Gate 9P）

### 目标

在最终核心审计前，把生产 canary 所需的 one-shot、session override、固定代码身份、写入
精确mutation contract、网络/源写拒绝、外部trust anchor和登录arm/CAS实现为可测试产品能力；
禁止G10C后临时补脚本。

### T09P 失败测试

- `max_cycles=1` 精确退出，不依赖计时 kill；
- session override 不修改 production config/worker config；
- trust anchor独立于被验证release；首段非OS代码不在可写worktree。完整release manifest覆盖
  VBS/PowerShell/Python/lazy modules/interpreter，worker identity无write/delete/rename；
- verifier/VBS/module tamper、junction/reparse和check-load TOCTOU fail closed；每次restart重验；
- canary/cycle contract限定schema/run/stage/cycle/generation、release/config/routing/auth、DB identity/
  schema/recovery point、document+source binding、typed composite PK/columns/prior state、exact file/
  root/prior hash、actual touched、RPO/RTO；DB commit/file publish前拒绝wrong-PK/无WHERE/净零/覆盖；
- 每个OP唯一匹配`operation_contracts.v4.json`，动态contract/auth manifest通过对应schema且path/hash/
  stage/expiry/revocation绑定；任意N/A、高风险OP缺授权、wrong operation/state/generation均失败；
- protected write-intent journal显式init；exact path/ACL/version、atomic append/replace、flush/fsync、
  hash-chain、crash reconcile、retention可验证，ordinary catalog/journal open为zero DDL；
- source write在受限 identity/只读 replica/sandbox 中得到 permission denied；
- LLM off 时主/备 provider egress 均被进程级 network deny；
- circuit open时resume/session/arm/login/activate全部拒绝；生产reset必须D05Rnn token且仍paused；
  arm不启动/reset/写registry；CAS后ARMED_ON_PRELOGIN且无LOGIN_COMMITTED时任何login零child；
- ARM token默认15min硬30min且CAS时消费；CAS后dormant lease默认24h硬72h；login commit默认
  5min硬10min，绑定review/user/SID/machine+boot generation/previous session/下一次新logon关系/
  generation/nonce、一次消费；final activation只ENABLED_IDLE/ON且不启动当前session；
- 用disposable test hive验证真实atomic create-if-absent与exact conditional delete，两进程barrier
  竞争只能一个成功；third-party replace/取消/异常回PAUSED且不覆盖；mutex单独不合格；
- evidence先脱敏并执行approved sink/ACL/加密/TTL；mutant/ENOSPC不污染真实卷或候选源码。

### 实现与 Gate

I09P只实现上述能力及registry中`introduced_at=T09P`且condition成立的全部concrete tests；
Gate按逐ID`required_green_at/revalidate_at`选择，不做owner×due笛卡尔推导。G09P由生产封装、安全
两个独立agent审查。G10C 后这些能力或命令
任一变化都会使 G09P/G09/G10C 失效。

---

## WP-09：tmp 端到端恢复演练（Gate 9）

### 目标

在完全隔离的环境中证明各 WP 组合后仍保持正确、可恢复、可暂停、无无限重启、无源文件
写入。不得以单元测试拼盘替代真实子进程演练。

### 环境

- 新 tmp project root、tmp config、tmp catalog、tmp runtime/control/log；
- 只包含合成源文件，测试前保存全量 hash/size/mtime manifest；
- deterministic parser fixtures；
- LLM stub，无网络；
- 注入 clock、故障点和短 timeout，使测试分钟级完成；
- PowerShell 测试优先复用现有 harness，不无故引入新框架。
- 使用 WP-09P 的真实 one-shot/override/release identity/allowlist 路径，而非测试专用旁路。

### 正常路径

`start once → scan → normalize queue → parse → persist → fingerprint/sections → LLM stub → export
→ cycle checkpoint → pause → clean exit`。

断言：单实例、阶段顺序、artifact 数量、worker_runs、scan_runs、runtime、checkpoint、export
版本、日志字段、源文件 manifest 和退出码。

### 故障矩阵

至少在以下位置逐一中断并以新进程恢复：

- scan enumerate 中；
- scan DB commit 前/后；
- queue select 中；
- parser child 启动前/运行中/退出后；
- artifact persist 中；
- fingerprint/section 中；
- LLM timeout/invalid output 中；
- provider请求PREPARED前/后、send后、response后、cache后、artifact commit前；
- export 中；
- retention 中；
- runtime write 中；
- supervisor backoff 与 circuit open 中。

每次恢复断言“不重复不该重复的 scan、不跳过必须重试的工作、不产生半成品成功状态、不
修改源文件、不无限重启”。

### 对抗验证

- 把 SQL 改回旧形状，性能测试必须失败；
- 去掉 scan 早期 checkpoint，crash recovery 必须失败；
- 恢复 uptime reset 逻辑，supervisor sequence test 必须失败；
- 去掉 progress handler finally clear，handler leak test 必须失败；
- 把 power gate 放回 scan 后，battery test 必须失败；
- 允许 source write，权限层拒绝与 immutability sentinel 必须同时捕获。
- logical document S1→S2时保留旧normalized/summary，source-rotation测试必须阻止旧结果抑制/
  错绑新source；
- 在允许table内wrong-PK更新3行、无WHERE更新、净零DELETE+INSERT、覆盖历史派生文件，
  CanaryWriteContract必须在commit前拒绝；
- tamper trust verifier/lazy module、在check-load间替换reparse target，以及两个真实进程竞争
  registry create，PX-S14、PX-S15、PX-S16、PX-S17必须fail closed且不执行候选/覆盖第三方值。
- 在CAS后无commit token模拟意外login/reboot、双进程消费、token replay/drift；START-S01、
  START-S02、START-S03、START-S04、START-S05、START-S06、START-S07、START-S08、START-S09、
  START-S10必须杀死启动窗口；
- 注入reset+resume组合、wrong exact-D return、缺12B/12C compensation和final activation启动当前
  session；RST-S/ACT-S concrete
  registry IDs必须失败。DB/file各crash边界由WRITE-F01、WRITE-F02、WRITE-F03、WRITE-F04捕获。
- 所有 mutant 在 throwaway worktree或运行时注入；结束核对 candidate commit、源码 hash 与
  clean diff。ENOSPC 只用 faulting VFS/facade 或硬 quota scratch。

### Gate 9 独立审查

- reviewer A 审计端到端脱敏证据、获批raw evidence ID/HMAC和状态对账；
- reviewer B 对抗式检查故障注入、mutant 杀伤力、rollback 与生产隔离。

两者都 `PASS` 后才允许 G10C。自动测试通过但源 manifest 有变化，直接 P0。

---

## WP-10：核心与发布跨域独立审计（Gate 10C / 10R）

### 目标

G10C在接触生产前以三个reviewer审Core+G09P/G09，通过后只允许D11A。G10R在A1/A2/A3、
最终LLM profile所需G07O或G07E+每个BP/BF、scanner/parser/retention与条件migration后审
exact release profile，通过后只允许D12A。两者均不能替代早期逐节点审查，也不存在
“G10R先通过才可生产只读”的循环。

### 六份独立 Reviewer 任务

- G10C-SQL、G10C-CONTROL、G10C-TESTOPS只接收G00/G01/G02A/selected exact G02B/G03/G04/
  G05/G09P/G09；禁止G06/G07/G08/A/B/12A/12B，唯一computed next=D11A。
- G10R-SQL-PERFORMANCE、G10R-CONTROL-LIFECYCLE、G10R-TESTOPS使用三名满足DAG exact
  role/cardinality/disjoint规则的agent，只接收exact release join：still-valid
  G09P/G09/G10C/G11A/G11J、条件G11M、A1/A2/A3、G06/enabled route G06P/G08、
  exact G07 mode、条件G11M-L，以及enabled时BP与连续BF；禁止12A/12B，唯一next=D12A。
- 六份prompt全文见`implementation_agent_prompts.md`；发现future/missing/hash drift立即FAIL，
  不等待未来证据。每人分别返回machine review JSON+Markdown，初版前不读同Gate其他结论。

### 退出标准

- 三份结论至少 `PASS_WITH_NONBLOCKING_FINDINGS`；
- P0/P1 为零；
- P2 均有 owner 和最迟关闭 Gate；
- evidence manifest 的 hash 与实际文件一致；
- 生产 worker 和自启动仍保持关闭。

G10R还要求still-valid G09P/G09/G10C/G11A/G11J、G06、每个enabled parser route/bucket G06P、
exactly-one(G07E,G07O)、G08、A1/A2/A3、enabled profile的BP与所有连续启用BF、条件G11M/
G11M-L全部满足；任何G10C后对one-shot/contract/trust/
source-network guard/arm/registry的变化会重开G09P/G09/G10C/G10R。

---

## WP-11A：D11A → OP11A → G11A 生产只读语义/性能对照

### 目标

在不运行 worker、不写生产 DB 的情况下，确认 tmp 结论适用于实际数据分布。

### 执行步骤

1. 再做 WP-00 隔离检查；任何进程运行都先停止本 Gate，而不是由 agent擅自终止。
2. 使用 `mode=ro` + `query_only=ON`。如果 WAL 存在，不盲用 `immutable=1`，避免忽略
   committed WAL；必要时由操作员制作一致性只读副本。
3. 先只跑 `EXPLAIN QUERY PLAN` 和 row-count probes；旧灾难查询不得在生产运行。
4. 新查询设置 progress/deadline，只取计划所需小 batch；记录 plan、VM/wall time 和有序 IDs。
5. 用独立、只读参考查询分块计算语义对照；不得为了比较运行无边界旧查询。
6. 检查 orphan roots/locations、状态倾斜、无统计信息、索引存在性和空间预算。
7. 只读统计normalized/summary中source ID/hash与当前primary不匹配的stale bindings；不修改。
8. 连接关闭后验证 DB/WAL/SHM mtime、size 与 hash/元数据没有因本 Gate 改变。
9. `NO_INDEX`分支必须在本Gate满足正常10秒production deadline。`INDEX`分支可在预声明deadline
   内输出受界`INDEX_REQUIRED`，但必须由plan证明缺少ADR-02冻结索引，且分块oracle/有界只读
   查询仍100%匹配ordered IDs；它只能开放D11M，不能记作性能PASS。

### 独立审查

- reviewer A：生产数据上的语义、顺序和性能推断；
- reviewer B：只读连接、WAL 一致性、资源上限和零写证据。

两者对OP11A冻结证据`PASS`后才按ADR-02进入D11M或D11B-A1；仍不代表授权启动。

---

## WP-11M：条件 D11M → OP11M → G11M

### 条件

仅当G02B-ADR=INDEX且G02B-IDX有效；NO_INDEX分支不实例化D11M、不写ledger，从G11A进入
D11J；INDEX分支从G11M进入D11J。两个分支均不得直接进入D11B-A1。

### D11M

在任何 DDL 前冻结：用户授权、生产 DB identity、当前一致恢复点、RPO/RTO、恢复演练、恢复
副本上的实测 build 峰值、卷空间公式、显式 operator command、kill/ENOSPC处置。

### OP11M 与 G11M

worker/supervisor/parser停、autostart off。运行显式 migrator，不通过普通 store open。完成后
核对 schema ledger、index SQL/xinfo、integrity、query plan、DB/WAL/space；重复运行证明幂等。
再用G11A相同生产只读协议重跑新查询，必须满足正常10秒deadline和plan预算。失败保持paused，
不自动DROP/VACUUM/删WAL；没有迁移后性能PASS就不能进入D11J。

---

## WP-11J：D11J → OP11J → G11J protected write-intent journal

D11J两名storage/control reviewer在任何生产写canary前冻结动态operation contract：exact absolute
path identity、批准SID ACL、无reparse/cloud-sync、format/version、atomic append/replace、flush/fsync、
hash-chain、crash reconciliation、retention、RPO seconds=0与RTO seconds≤1800。若采用生产DB表而
非独立文件，必须另建显式migration节点；不得把DDL藏进本节点。

OP11J只执行一次显式journal init，不打开worker、不写catalog/source/config/registry。G11J两名
按DAG与OP11J执行者disjoint的reviewer以断电/半写/ACL/identity反例和sentinel核对结果，并证明之后ordinary mode=`rw`打开catalog
与journal都zero DDL。通过后D11B-A1才eligible；G11J也是G10R必要输入。

---

## WP-11B-A：Canary A 三个独立 D/OP/G

### 每个 D 节点的冻结输入

`D11B-A1`、`D11B-A2`、`D11B-A3`分别使用新的evidence revision与run ID，并冻结：

1. 当前数据库identity/schema、恢复点、数值RPO/RTO、reconcile/restore disposition；
2. 用户授权是否覆盖本阶段、operator/observer/stop authority与exact one-shot命令；
3. candidate document IDs或root IDs；stage flags；生产config/.env/source只读；
4. 机器可执行`CanaryWriteContract`：table→operation→exact typed composite-PK set→allowed
   columns→prior row/version→before/after invariants→max actual touched rows；exact file/root→
   operation→prior hash/absence→max bytes/files；
5. 禁止DDL/ATTACH/unsafe PRAGMA/trigger、source OS/sandbox拒写、主/备provider network deny。

SQLite authorizer只能做table/op第一层。所有DB写须处于可回滚外层transaction，commit前读取
changeset核对operation/PK/changed columns/脱敏before-after digest/run ID；违规rollback并pause。
文件guard解析最终reparse target，默认只允许exclusive CREATE；DELETE/REPLACE/RENAME默认
拒绝。commit后再由独立只读路径重算changeset，恢复点不能代替写前拒绝。

### 固定操作链

```text
D11B-A1 -> OP11B-A1(scan-only) -> PAUSED/OFF -> G11B-A1
 -> D11B-A2 -> OP11B-A2(normalize/persist-only, 3–10 IDs) -> PAUSED/OFF -> G11B-A2
 -> D11B-A3 -> OP11B-A3(full-cycle-no-LLM) -> PAUSED/OFF -> G11B-A3
```

- A1关闭normalize/export/prune/LLM；A2关闭scan/export/prune/LLM；A3仍one-shot且LLM off。
- 每个OP后先验证worker/supervisor/parser=0、自启动off，再交两名非operator reviewer。
- 每个G分别审数据/source与runtime/rollback；G11B-A3不能补签A1/A2。
- A2/A3至少3个冻结candidate artifact正常增加；scan/checkpoint/runs/runtime逐项对账。

### 停止条件

queue deadline、progress冻结、第二实例、重复scan、无progress高CPU、DB/WAL超预算、任何
unexpected operation/PK/column/file/touched delta、source write未被权限拒绝、未授权egress、
parser cleanup超时均立即persistent pause。wrong-PK、无WHERE、错误列、净零DELETE+INSERT、
历史文件覆盖/reparse escape视P0；不得重启补证据或临场DELETE/restore。

## WP-11B-B：真实 LLM 逐 provider Canary

只有`G11B-A3 + G07E -> G11M-L-ADR`后存在入口：NO_SCHEMA_DELTA直接到D11B-BP；
SCHEMA_DELTA必须D11M-L→OP11M-L→G11M-L后到D11B-BP。G07O没有合法边。

```text
D11B-BP -> OP11B-BP(primary one-shot) -> PAUSED/OFF -> G11B-BP
 -> [D11B-BF01 -> OP11B-BF01 -> PAUSED/OFF -> G11B-BF01]
 -> [D11B-BF02 -> OP11B-BF02 -> PAUSED/OFF -> G11B-BF02] ...
```

BP及每个最终启用BFnn分别取得一次性stage/provider-bound授权manifest：provider/model、opaque
root/data classes、exact documents、fields/exclusions、per-document/total character/token/cost cap、
timeout、retention/jurisdiction/terms、destination、issued/expiry/revocation、release/config/routing
fingerprint与hash。Primary授权不传fallback；未通过G11B-BFnn的fallback必须最终禁用。

每个D另冻结独立RPO/RTO与CanaryWriteContract：request-ledger/artifact/cache/usage/runtime/
checkpoint的operation、typed PK、columns、prior row；exact file/root/prior hash、actual touched、
precommit/post-read与crash reconcile。BP合同不能给BF，BF合同不能跨实例复用。

每次OP都是真正one-shot，完成立即pause并由两名非operator reviewer审查authorization hash、
request ledger、成本reservation、artifact/source binding和零越界。Canary B授权不延续到12A/12B。

---

## WP-12A：D12A → OP12A → G12A 无自启动人工观察

### 目标

G10R后，D12A冻结exact release/profile/命令、observer/stop authority和数值limits；OP12A以
相同profile手工运行至少2小时和5个完整周期。仍不恢复登录自启。默认LLM off+network deny。
若circuit open，resume-session必须返回CIRCUIT_OPEN；只能先完成独立D05Rnn→OP05Rnn→
G05Rnn并返回D12A重新审查，观察命令不能顺带reset。

OP12A每个cycle先只读选出exact document/source集合，再密封CycleWriteContract（cycle/run/
generation、release/config/routing/auth、typed PK/columns/files/prior state、actual touched、RPO/RTO）
才开始独立transaction；cycle中到达文档延后，禁止一个持续两小时的大transaction。DB/file
跨提交用intent/finalize ledger，crash只reconcile、不重调provider。

### 观察项

- 每阶段 duration 与 P50/P95；
- completed cycles、failure signatures、backoff/circuit 状态；
- CPU/working set/logical reads/physical I/O；
- DB/WAL/SHM/日志增长；
- normalize、LLM、permanent failure backlog；
- scan due 与实际扫描次数；
- pause SLA、parser child 回收、单实例；
- 源文件 manifest 与生产配置 hash。

连续 5 周期的定义是五次真正 cycle success，不是五次进程启动或 heartbeat。任何失败后
重新计观察窗口；不能把失败前的周期拼接凑数。

若启用真实LLM，必须取得12A专属stage-bound manifest：所有主/备provider/model、opaque
data/root、fields/exclusions、文档/字符/token/费用、destination、时限、retention/jurisdiction、
release/config/routing与expiry/revocation。Canary B授权不延续。结束后先persistent pause、
进程0，再开始G12A。

### 独立审查

可靠性 reviewer 与数据/资源 reviewer 分别审查原始时间序列、逐cycle全部contract/hash并
重算至少一个changeset、日志和不变性。通过只表示
可以向用户提出恢复自启动建议，不表示 agent 获得授权。

---

## WP-12B：dormant Run 安装与一次登录验证

### 前置条件

- G12A有效、P0/P1为零、circuit closed、process0；
- G12B-PRE两名reviewer冻结exact Run bytes、独立trust anchor path/hash/signature/ACL、内容
  寻址且对worker identity不可写/删/换名的完整release/interpreter/lazy modules，以及reparse/
  TOCTOU证据；自验launcher或普通可写worktree直接BLOCKED；
- 12B profile与G12A相同。enabled使用全新`G12B_LOGIN_AUTOSTART` authorization；Canary B/
  12A不可复用。off也必须有完整12B operation authorization，只是provider scopes为空且全部
  provider egress=`DENY_ALL`；不得把整个OP标为N/A；
- 不新增计划任务、服务或第二launcher。

### 12B.1 ARM

1. G12B-PRE后用户先批准exact Run value、12B auth hash与release/data roots；尚不批准注销；
2. D12B-ARM由2名reviewer冻结exact arm、ARM token默认15min/硬30min；
3. 在任何ARM state/token写入前，D12B-RB由2名满足DAG rollback/startup角色与disjoint规则的
   reviewer预审并seal exact OP12B-RB compensation contract；失败则OP12B-ARM不可eligible；
4. OP12B-ARM先向G11J protected journal追加intent，绑定plan/review/Run/trust/release/config/
   routing/data/auth、circuit+control generation、expected registry absence、desired bytes hash、
   ownership/run nonce、SID/expiry与预期补偿，再写arm state并finalize；不启动/reset/写registry；
5. G12B-ARM由2名按DAG与OP执行者disjoint的reviewer确认PAUSED/OFF、process0、counter/registry
   不变和journal head一致。

### 12B.2 CAS 后必须 dormant

1. D12B-CAS由2名reviewer审目标API、两进程barrier、exact conditional rollback与power-loss；
2. OP12B-CAS使用真实atomic create-if-absent写exact REG_SZ并在提交点一次性消费ARM token，
   禁止check-then-force；mutex只辅助；成功后创建默认24h/硬72h dormant lease；
3. 成功状态只能`ARMED_ON_PRELOGIN/ON`。trust launcher可以被Windows Run调用，但在加载release
   前若无有效LOGIN_COMMITTED必须退出：child/DB/config/source/额外registry写/egress均0；
4. G12B-CAS由2名满足DAG角色/基数/disjoint规则的reviewer亲验START-S01、START-S02、
   START-S03、START-S08、START-S09、START-S10。从OP12B-ARM起的任一ARM/CAS/post-review/
   login失败、crash partial、ARM/lease到期或用户取消只能触发已预审的OP12B-RB→G12B-RB；
   Gate/launcher不写registry。OP按journal intent/finalize与ownership nonce reconcile，仅在current
   bytes exact match时conditional delete；CAS遇到任意既有同名值（即使同bytes）或之后第三方
   替换都不接管/不碰并进入PAUSED/REGISTRY_CONFLICT，不自动重试；G继承OP exact终态。

### 12B.3 最终登录批准与 bounded login-validation

1. D12B-LOGIN由2名满足DAG角色/基数/disjoint规则的reviewer核对G12B-CAS、Run/trust/release/auth/generation无漂移，冻结
   LOGIN_COMMITTED默认5min/硬10min、D review hashes、最终用户批准、expected SID、machine/boot
   generation、previous session与“该SID下一次新logon”关系、nonce及logoff取消rollback；不得
   预知或硬编码尚未创建的future session/LUID；
2. D通过后用户再次确认已保存工作，并明确批准立即注销；否则停止在dormant状态；
3. OP12B-LOGIN重验circuit/process/Run/hash/TTL，原子写一次性LOGIN_COMMITTED后立即logoff。
   logoff失败/取消立即撤销token、pause并触发OP12B-RB；
4. trust launcher在加载release前原子消费token；缺失/过期/replay/drift/race零启动。只运行一个
   冻结login-validation cycle，随后自动persistent pause；
5. G12B-POST由2名满足DAG角色/基数/disjoint规则的reviewer审单链、首cycle、pause、source/write/egress/cap、全部START测试。
   成功终态只为`LOGIN_VALIDATED_PAUSED/ON`且process0；不得标记RECOVERED。

---

## WP-12C：独立最终启用下次登录

1. 用户阅读G12B-POST摘要后先进入D12C；2名满足DAG exact role/cardinality/disjoint规则的
   reviewer核对circuit closed、process0、无drift/P0/P1，并seal OP12C/OP12C-RB同一final/
   compensation contract与唯一proposed action/intent hash；此时不存在可供其审查的final授权；
2. 用户再另行批准`G12C_FINAL_AUTOSTART_ACTIVATION`，授权逐字绑定上述intent hash、action ID、
   exact Run/release/auth/control generation/expiry；拒绝或不回应时保持
   `SAFE_PAUSED_WAITING_USER`，不是BLOCKED；
3. G12C-PRE由恰好3名不同角色且按DAG与D12C disjoint的reviewer重读actual user authorization、contract、
   release与ledger head；只有全PASS才唯一开放OP12C；
4. OP12C唯一action为`activate-autostart-final`：generation CAS到ENABLED_IDLE/ON、只增1、消费
   token；在token/control跨资源写前向protected journal追加绑定intent/auth/generation/expected
   state/ownership nonce的intent，完成后finalize，crash只由OP12C-RB reconcile；不启动当前
   session、不reset/resume/arm、不写registry/config/DB/source、不改LLM；
5. G12C由恰好3名满足DAG exact角色/基数/disjoint规则的reviewer分别审control/circuit、release/auth/security、operations，
   观察至少20s process0与sentinel零变化；ACT-S01、ACT-S02、ACT-S03、ACT-S04、ACT-S05、
   ACT-S06、ACT-S07全部通过时物理state前后均为`ENABLED_IDLE/ON`，只记录
   `lifecycle_outcome=RECOVERED`；OP/G失败只能触发`OP12C-RB→G12C-RB`。owned Run未漂移时回
   `LOGIN_VALIDATED_PAUSED/ON`；第三方Run冲突时不碰registry并进`PAUSED/REGISTRY_CONFLICT`；
   G继承OP exact终态且自己不写状态；
6. 以后普通新登录还必须重验G12C outcome、release/auth/config/routing/data/Run、SID、circuit、
   Job Object与单实例才可`RUNNING_AUTOSTART/ON`；失败零child并PAUSED/ON；
7. 每个后续cycle在任何DB/file/network前都依`runtime_cycle_policy`密封独立operation contract，
   绑定action-intent/auth、generation/process、journal head、exact document/source tuples、DB/file
   write set、egress和持久daily/monthly caps，并重验expiry/revocation。ACT-S08、ACT-S09、
   ACT-S10分别覆盖第二/后续cycle、授权/cap失效和wrong PK/file/journal head；任一失败circuit
   open+persistent pause，registry/config/source零写；
8. 若用户还要当前session立刻运行，必须另建新的D→OP(resume-session)→G任务，不得顺带执行。

---

## Production circuit reset side lane

每次circuit open使用下一未用`05R01`–`05R99`：D05Rnn两名reviewer冻结root cause、用户reset token、
failure generation/TTL、exact `D` return node与全部downstream invalidation；return必须是失败节点
合法祖先，G/OP/占位符均非法。OP05Rnn只清active latch/budget、generation+1、保留历史且
仍PAUSED/process0；G05Rnn由2名按DAG与OP执行者disjoint的reviewer核对20s process0及registry/config/DB/source/release/
auth不变。RST-S01、RST-S02、RST-S03、RST-S04、RST-S05、RST-S06、RST-S07、RST-S08、
RST-S09全部通过。G后只回冻结exact D，没有直接resume/arm/login/activate边。

本计划仍保持独立；是否并入主线是未来单独任务，必须先做冲突、重复、状态迁移和时效审查。
