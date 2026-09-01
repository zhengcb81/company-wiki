# Source Catalog Worker — 逐关键节点独立 Agent 审查协议

> 本文件落实用户要求：计划实施过程的**每个关键节点**都必须有独立 agent 审查。  
> 独立审查是阻断式 Gate，不是可选建议，也不能集中到最后一次性补做。

## 1. 什么叫“独立”

同一 Gate 的 reviewer 必须满足：

- 不是该 Work Package 的实施 agent；
- 没有为该 Work Package 写代码、改测试、生成 benchmark 或修复 findings；
- 使用明确的只读任务，禁止修改工作树；
- 优先以干净上下文开始，只接收计划、commit/diff、证据包和必要源码；
- 独立形成结论，在提交初版前不读取同 Gate 其他 reviewer 的结论；
- 报告必须能由文件、命令输出、测试或可复现推理支持；
- 不得以“实施者说已经验证”代替自己检查证据；
- 实施者不能担任自己的 reviewer，也不能代写 reviewer 报告。

本计划中的“独立”“不同”或“DAG-disjoint”严格指`gate_dag.v4.json`对该节点声明的
`reviewer_independence`、`forbidden_agent_sets`、`min_not_in`、exact role与cardinality。除非DAG
明确列出，不得把它扩张为“该agent从未参加过任何历史节点”的全局永久排除；反之也不得用
“换一份报告”冒充agent identity满足机器约束。

若平台无法提供满足以上条件的 agent，主流程把 Gate 状态设为 `BLOCKED`，原因记录为
`NO_INDEPENDENT_REVIEW`；不能降级为自审通过。

## 2. 每个关键节点的双审查节奏

每个会修改实现的WP至少有Design与Exit两个审查点；WP-01是唯一
`T01→D01→G01` TEST_BASELINE_ONLY例外且禁止产品变更。所有生产操作使用独立D→OP→G，
包括11A、条件11M/11M-L、11J、A1/A2/A3、每个BP/BFnn、12A、12B的ARM/CAS/LOGIN与
rollback、12C的pre/activation/rollback及每次reset实例。G12B-PRE是全链总pre-review，
不能替代每个D/G：

1. **Design Check（Dxx）**：失败测试已经建立、准备动实现之前。reviewer 检查问题边界、
   设计方向、禁区、验收和回退是否足够。Dxx 通过后才可改实现。
2. **Exit Gate（Gxx）**：实现与测试完成后。reviewer 只读审 diff、完整证据、mutation/
   fault tests 和风险，决定能否进入下一 WP。

正式ledger前先固定`T00L→D00L→I00L→G00L`；WP-00再走`D00→OP00→G00`；
G10C/G10R/G12C-PRE/G12C各使用machine DAG规定的恰好三路独立审计。任何A/B/12B/reset/activation子节点不得
合并/补签。高风险节点的reviewer数量见矩阵。

为节省篇幅，下方少数标题会把同一WP的D与G并列，但这**不表示可以合并审查**：每个D、
每个G都必须有独立evidence revision、原始review payload/hash、verdict和ledger record；
G10C与G10R也必须分别重新派发三名reviewer，不能复用一份结论。

失败测试必须处于test-only `Txx` commit；普通实现处于后续`Ixx`。D后任何test/fixture/
assertion变化使D失效。WP-01没有I01；生产OP没有I commit而必须绑定exact run/auth。状态只按
`gate_state_machine.md`。

## 3. 优先级和阻断规则

| 级别 | 定义 | Gate 处理 |
|---|---|---|
| P0 | 数据损失、源文件写入、生产配置污染、越权、秘密泄露、误杀无关进程 | 立即 `FAIL`，保持 paused，必须独立复审关闭 |
| P1 | 语义错误、恢复错误、无限重启、性能根因未修、测试不能捕获目标缺陷 | `FAIL`，禁止下一 WP |
| P2 | 有限条件下风险、可维护性/观测缺口、非关键性能问题 | 必须有 owner、截止 Gate、接受理由 |
| P3 | 文档、命名、小型改进 | 可记录，不阻断 |

Reviewer 结论：

- `PASS`：无开放 finding；
- `PASS_WITH_NONBLOCKING_FINDINGS`：只有已登记 P2/P3；
- `FAIL`：存在 P0/P1、证据缺失、范围越界或无法复现；

`BLOCKED` 由主流程记录，不是第四种 reviewer verdict。

“测试未运行”“机器太慢”“另一个线程正在改文件”“生产环境不可用”不是自动通过理由；
应标记 blocked 并等待条件满足。

## 4. 审查证据不可变性

实施者提交 Gate 时冻结一个 evidence revision：

```text
Git commit:
Plan revision + manifest SHA-256:
Test-only T commit:
Implementation I commit:
OP run ID / authorization evidence ID（适用时）:
Dirty diff hash（如有，原则上应无）:
Evidence directory:
Evidence manifest SHA-256:
Test log SHA-256:
Benchmark raw-data SHA-256:
Production/config sentinel SHA-256 + source sentinel repo-safe HMAC（key在repo外）:
Ledger previous-record SHA-256:
Gate DAG SHA-256 / validator version:
Machine review payload path + SHA-256:
Machine review confirmation path + SHA-256:
Operation contract path + SHA-256（OP适用）:
Authorization manifest path + SHA-256 / catalog-approved N/A reason:
```

Reviewer 只针对该 revision 签字。之后任何代码、测试或证据变化都会使旧 `PASS` 失效；必须
生成新 revision 并至少复审受影响项。不得覆盖旧报告，应写 `review-v2.md` 等新文件。

若 reviewer 报告由主 agent代为落盘，必须保存原始 agent payload的 SHA-256；随后由同一
reviewer 重读 actual JSON/Markdown bytes并另发符合`review_confirmation.schema.json`的detached
confirmation。禁止主 agent改写措辞、代填`confirmed=true`或把自身摘要冒充原审查。

## 5. 逐节点审查矩阵

### T00L → D00L → I00L → G00L — ledger validator bootstrap

**D00L Reviewer：**1名schema/state-machine agent；**G00L Reviewers：**2名，分别为
ledger/cryptographic-chain与DAG/adversarial-test agent。全部只读且不能参与T/I。

**D00L 检查：**GL-S01、GL-S02、GL-S03、GL-S04、GL-S05、GL-S06、GL-F01、GL-F02、
GL-F03、GL-F04、GL-F05、GL-F06、GL-F07、GL-F08、GL-F09、GL-F10、GL-F11、GL-F12、
TESTID-S01与G10-PROMPT-S01是否先红；DAG/vectors/registry/catalog专用instance schema是否拒绝
empty/array/scalar；是否覆盖fake PASS/role/confirmation/branch/next/auth/contract/state/hash；所有路径是否tmp。

**G00L 必须亲验：**schema meta/instance validation、review JSON+confirmation actual hash、canonical
candidate transcript/head、validator release manifest、DAG next、exact 1/2/3 reviewer role/disjoint、
operation/auth/test-ID映射、200个property序列、全部mutant=0 survivor；validator网络/生产DB/
registry调用0。只有D00L review允许null head；G00L两人绑定同一I00L-terminal candidate head。
G00L通过前不存在可依赖的正式ledger；通过后用原候选字节一次性初始化再开放D00。

### D00 → OP00 → G00 — 基线与隔离

**Reviewer：**1 名基线/安全 agent。  
**输入：**进程、启动入口、Git、代码漂移、只读 catalog、空间快照。  
**必须反证：**

- 是否有被遗漏的 supervisor/parser/launcher 或第二启动入口；
- PID 是否只凭数字判断；
- read-only SQLite 是否可能因连接/migration helper 写库；
- dirty files 是否与另一个任务冲突；
- DB/WAL/SHM/config mtime 是否真的未变。

**阻断：**任何生产写、任何未归属 overlap、任何活跃 worker、空间未知。

### D01 — 夹具与红灯测试设计

**Reviewer：**1 名测试设计/性能方法 agent。  
**检查：**数据分布是否接近报告规模；oracle 是否独立；wall-clock 是否辅以 VM budget；
旧查询是否安全中止；parseable primary/source binding与force matrix是否覆盖；生产路径哨兵
是否能捕获误触；measurement mode、SQLite source-id、harness、`progress_n`(proxy)/PRAGMA/
params/fixture是否冻结；proxy没有声称exact step区间。D01不要求Phase4取消测试转绿，
但必须检查T01仅含测试/helper；若需production seam则FAIL并移交I02A。

### G01 — 夹具与红灯测试出口

**Reviewer：**同领域独立 agent，可与 D01 同一 reviewer，但仍不得参与实现。  
**必须亲自验证：**固定 seed 可重建；旧实现因目标问题红；测试不会挂900秒；warm≥30、
cold-ish≥10；Q-P01、Q-P02、Q-P03、Q-P04、Q-P05、Q-P06（exact mode另Q-P07）raw
metadata可比。G01时旧产品红灯仍在；
新SQL mutant留G02A/G09。

### D02A — SQL 改写设计

**Reviewer：**1 名 SQL 语义 agent。  
**检查：**旧查询每个条件的语义表；roots join 决策；`document_id+primary_source_id`关系；
force/non-force；candidate set；stable order；retry/terminal/generator/version；不得用 LIMIT、
删除locationless outer rows或跳数据伪优化；current normalized还绑定source ID/hash，Q-S17
覆盖S1→S2与UPSERT。

### G02A — SQL 改写出口

**Reviewers：**2 名，分别负责：

1. SQL 语义与 property oracle；
2. SQLite plan、复杂度与跨版本稳定性。

**必须反证：**倾斜数据、缺少 stats、小数据、无 location、source mismatch、多/重复
location、force matrix、同 priority和N/2N scaling。任一 reviewer `FAIL` 均阻断。

### G02B-ADR 与两个分支

**G02B-ADR Reviewers：**2名SQL/planner与migration/capacity agent。只读G02A evidence，冻结
ADR-02唯一`NO_INDEX|INDEX`、benchmark hashes、SQLite矩阵、空间/write-amplification；不得在
此Gate前创建任何branch T commit。

**选中后：**分别且只分别走T02B-NI→D02B-NI→I02B-NI→G02B-NI，或
T02B-IDX→D02B-IDX→I02B-IDX→G02B-IDX。每个D/G 2名reviewer。两个分支各含M-COM-S01、
M-COM-S02、M-COM-S03、M-COM-S04、M-COM-S05、M-COM-S06、M-COM-F01、M-COM-F02；
NI另审zero-index，IDX另审exact index/migrator/峰值。
特别检查eager `_DDL`、missing DB隐式创建和worker/login调用migrator；ZR1002/ZR1003必须先
由tmp fixture显式init/upgrade再reader open，并分别纳入M-COM-S05/M-COM-S06证据。若为让旧fixture
转绿而恢复产品reader eager DDL，D/G均FAIL。

### G02B-NI / G02B-IDX — 分支出口

**Reviewers：**SQL reviewer + migration/capacity reviewer，共 2 名。  
**必须反证：**NI的zero-DDL/no-index或IDX的中断/磁盘满/重复/同名错误/rollback/write amp。
未选branch从T节点起没有ledger record；任何未选branch record均使validator失败。

### D03 — Checkpoint 设计

**Reviewer：**1 名状态机/一致性 agent。  
**检查：**`scan_runs` 与 JSON 的事实源、commit 顺序、per-root outcome、
`completed_with_errors`分类、root/config/scanner fingerprint、对账、旧 schema、时钟回拨、
哪些失败应重扫/不应重扫。

### G03 — Checkpoint 出口

**Reviewer：**1 名未参与实现的恢复语义 agent。  
**必须亲自审阅：**每个 crash 窗口的新进程恢复证据；不能只看 mock 或同进程对象；DB/JSON
矛盾时 fail-safe 行为；必须包含 benign quarantine、root offline/partial、root增删和版本/
配置漂移。

### D04 — 取消/heartbeat/遥测设计

**Reviewer：**1 名 SQLite runtime agent。  
**检查：**progress handler 不在 callback 内执行 SQL；长SQL期间如何读取新的外部 control
generation；deadline/stop/pause taxonomy；finally清理；liveness/VM/business milestone区分；
日志最小化和数值开销/SLA。

### G04 — 取消/遥测出口

**Reviewer：**1 名可观测性/并发安全 agent。  
**必须反证：**handler 泄漏到下一查询、callback re-entrancy、runtime 写失败、假 heartbeat、
query开始后外部pause不可见、过高 callback 开销、敏感正文进入日志。

### D05 — Supervisor 状态机设计

**Reviewers：**2 名：状态机 agent、Windows 进程安全 agent。  
**在写 PowerShell 前必须审：**只有完整cycle成功清零、per-signature+global滚动预算、失败
签名、退避/circuit、跨supervisor/login持久、pause、PID/runtime envelope、损坏control
fail-closed、Job Object、startup-delay-once。

### G05 — Supervisor 出口

**Reviewers：**同样两个独立角色。  
**必须亲自验证：**`>900s`/交替签名失败不清零、backoff中pause、login/reboot保持budget、
损坏control不启动、login+circuit不复活、PID reuse、旧attempt heartbeat、Job Object orphan、
startup delay只一次、S-S18三动作矩阵。特别反证open circuit+resume/session/arm不能清latch或
启动；reset-alone仍PAUSED/进程0/历史audit保留。两者都PASS。

### D06 — Scanner 优化设计

**Reviewer：**1 名文件系统/性能 agent。  
**检查：**exact baseline commit；必要instrumentation-only revision；旧/新topology/environment/
instrumentation hash相同且各n≥10；完整244/16,570/429/9,853 topology；30天rehash、junction、
offline、power gate。历史427s不得作SC-P02正式分母。

### G06 — Scanner 出口

**Reviewer：**1 名独立 scanner agent。  
**必须审原始分阶段样本和脱敏 source manifest HMAC（key在repo外）**；只看总秒数不够。P95≤120s且≥2×
基线、缓存失效、1% changed、10% churn、rehash、中断恢复、电池任一无证据即 `FAIL`。

### D06P 与 G06P — Parser 分格式设计与出口

**Reviewer：**1 名 parser reliability agent。  
**检查：**候选`_normalize_source` route digest与P-FMT00-ROUTE完全一致；plain text、HTML、MHT
HTML/MHT fallback、PDF fallback/Docling、DOCX、DOC、XLSX、XLS、PPTX、JSON、XML/XSD分别有
S/M或显式DIS、LIMIT、ERR/NA、PAUSE实例；S n≥20/P95，M n≥10/max，边界/异常样本满足数值
合同。不同fixture、raw outlier全保留；每route单独verdict，缺数据/未通过必须禁用。

### G07-ADR — LLM release mode只读决策

**Reviewers：**2名LLM privacy/cost与operations agent。冻结且只冻结LLM_OFF或LLM_ENABLED；
不调用provider。分支选择、用户意图、data class、长期能力边界必须写machine branch decision。
未选T07分支没有ledger record；G07E失败不能自动改写为OFF。

### D07E / G07E — LLM enabled

**Reviewers：**2 名 LLM reliability与privacy/cost agent。  
**检查：**current normalized/summary的version/status+当前source ID/hash+normalized ID/hash；
S1→S2、dedupe/cache逐document绑定；durable request ledger/OUTCOME_UNKNOWN；arrival/service；
全部主/备provider独立allowlist/caps、单线程。

**G07E反证：**S1正文错绑S2、old summary抑制、duplicate/batch错配、unknown自动重发、
fallback绕授权、未授权egress、日志泄露、直接多线程。不能无条件声称exactly-once billing。

### D07O / G07O — LLM 强制关闭

**Reviewer：**1名LLM安全agent。T07O/D07O/I07O独立于E分支；G07E失败不能自动转通过。
G07O还依赖G09P，必须亲验production config/session override/launcher应用层fail-closed、UI状态、
L-S17+PX-S07对全部主/备provider进程级egress deny。G07O没有Canary B出边。

### D08 — Retention/容量/安全设计

**Reviewer：**1 名数据安全/SQLite capacity agent。  
**检查：**只在tmp删除、路径resolve、dbstat fallback、空间公式、faulting ENOSPC、rotation；
secret永不采集；approved sink的SID ACL/加密/无reparse/7与30日TTL、EV-S01、EV-S02、EV-S03；生产cleanup不在范围。

### G08 — Retention/容量出口

**Reviewer：**1 名独立数据运维 agent。  
**必须反证：**symlink/path traversal、正在使用文件、磁盘满、自动 VACUUM/DROP/DELETE、备份
删除、真实卷被填满、secret/用户名/外部portfolio路径进入repo evidence。

### D09P 与 G09P — 生产执行封装

**Reviewers：**2 名：release/CLI agent、生产安全 agent。  
**检查：**registry中`introduced_at=T09P`且condition成立的全部concrete IDs，并按每ID的
required_green/revalidate节点执行；one-shot/session override；独立trust anchor、不可写完整
release/interpreter、verifier tamper/TOCTOU；operation+PK+column/exact-file precommit changeset；
OS source deny/主备egress deny；reset/resume/arm/login/final activation正交；dormant prelogin；
静态operation catalog、动态contract/auth、protected journal；真实atomic registry create/delete并发；evidence
lifecycle与safe mutant/ENOSPC。Facade/mutex/self-verification单独通过均不足。G10C后变化重开。

### D09 — E2E/故障矩阵设计

**Reviewers：**2 名：E2E contract agent、对抗/回滚 agent。  
**检查：**真实子进程、全tmp、LLM stub、source rotation、request ledger crash点、wrong-PK/
net-zero/file mutant、trust tamper/TOCTOU、registry race、source sentinel与mutant清单。

### G09 — E2E 出口

**Reviewers：**上述两个角色。  
**必须亲自审：**脱敏日志/approved evidence ID、DB/state/ledger对账、mutant红灯、新进程、无restart、无源
变化。Mutant必须throwaway/runtime注入且hash恢复；source-write还需permission denied。任何
只被mock覆盖的关键边界为P1。

### G10C / G10R — 核心与发布跨域审计

**Reviewers：**每个 Gate 恰好 3 名，互不先看结论：

1. SQL/性能；
2. 控制面/安全；
3. 测试/运维。

G10C三份prompt只审Core+G09P/G09，通过后只允许D11A，禁止读取未来G06/G07/G08/A/B。
G10R使用三名满足DAG exact role/cardinality/disjoint规则的reviewer，exact join显式包含仍有效的
G09P/G09/G10C/G11A/G11J、A1/A2/A3、exact LLM profile的G07O或G07E+每个BP/BF、G06/启用
route G06P/G08、条件migration与trust/release，只允许D12A。两者
分别审所有入边/hash/P2 disposition，不能补签早期Gate或互相制造循环依赖。

### D11A — 生产只读对照设计

**Reviewers：**2 名：SQL/数据语义 agent、生产只读安全 agent。  
**在打开生产库前检查：**拟执行的每一条 SQL、参数、LIMIT、progress/deadline、连接 URI、
WAL 处理、资源上限、参考结果算法和连接前后 sentinel。旧灾难查询出现在执行清单中即
`FAIL`。D11A 通过只授权列明的只读命令，不授权 worker 运行。

### G11A — 生产只读对照

**Reviewers：**2 名：SQL/数据语义 agent、生产只读安全 agent。  
**检查：**旧慢查询未运行；`mode=ro`/WAL 一致性；有界 deadline；ordered IDs；连接前后
DB/WAL/SHM/config 元数据；worker 与自启动仍关闭。`NO_INDEX`必须直接满足正常10秒deadline；
`INDEX`只能在预声明deadline内给出`INDEX_REQUIRED`，且需证明缺少冻结索引、语义仍由独立分块
oracle/有界只读查询100%验证。该诊断只开放D11M，不是性能PASS。

### D11M → OP11M → G11M — 条件生产 Migration

**Reviewers：**2 名：SQLite migration agent、capacity/recovery agent。  
**D11M：**只有ADR-02需索引时；审用户授权、当前恢复点、RPO/RTO、恢复演练、实测峰值、显式
migrator、DDL-denying normal open、ENOSPC/中断。  
**G11M：**审schema/index/integrity/query plan、幂等、空间和失败状态，并用G11A同协议确认迁移后
新查询满足正常10秒deadline/plan预算；否则FAIL。NO_INDEX分支没有
D11M ledger record。LLM request-ledger schema另在G11B-A3+G07E后由G11M-L-ADR两名reviewer
判断；SCHEMA_DELTA才走D11M-L→OP11M-L→G11M-L（D/G各2人），NO_SCHEMA_DELTA直接到BP。
缺任一前驱或出现早期`G07E→D11M-L`边均FAIL。

### D11J → OP11J → G11J — protected write-intent journal

**D/G各2名并按DAG disjoint：**storage/recovery与control/security。D核对exact path identity、SID ACL、
format/version、atomic append/replace、flush/fsync、hash-chain、crash reconcile、retention、RPO
seconds=0、RTO seconds≤1800；OP只显式初始化且worker/process0。G亲验半写/断电/reparse/ACL
反例、catalog/source/config/registry sentinel以及ordinary mode=`rw` zero DDL。NO_INDEX与INDEX
分支都必须经G11J，且G11J是A1/G10R前驱。

### D11B-A1→OP11B-A1→G11B-A1；D11B-A2→OP11B-A2→G11B-A2；D11B-A3→OP11B-A3→G11B-A3 — Canary A

每个D节点和每个G节点均2名reviewer且不得任operator；不得合并。每个D重新审用户授权、exact run、当前
恢复点/RPO/RTO、candidate/root、operation+PK+column/exact-file contract、actual touched
limits、precommit changeset、disposition、one-shot、OS source deny、主备network deny。

每个OP后先PAUSED/OFF与进程0，再分别审：

1. 数据完整性/source immutability与post-read changeset；
2. runtime/checkpoint/回退/单实例。

wrong-PK/无WHERE/net-zero/覆盖、source permission未拒绝或egress为P0。A3不能补签A1/A2。

### D11B-BP→OP11B-BP→G11B-BP 与逐个 D11B-BFnn→OP11B-BFnn→G11B-BFnn — Canary B

每个primary/fallback阶段D与G各2名非operator reviewer。D先验证G11B-A3+G07E+
G11M-L-ADR及条件G11M-L、新的
一次性provider-bound用户授权、exact docs/fields/character/token/cost/timeout/retention/
jurisdiction/destination、one-shot和fallback独立性，并冻结RPO/RTO、typed composite PK、列、
exact files/prior state、actual touched与precommit/post-read合同。G审request ledger/source binding/caps/
cost reservation与pause。G07O没有入口；未审fallback最终禁用；授权不延续12A/12B。

### D12A — 两小时/五周期观察设计

**Reviewers：**2 名：可靠性时间序列 agent、资源/backlog agent。  
**在OP12A前检查：**G10R exact profile、circuit closed、用户授权、默认LLM-off+network deny；
若真实LLM则12A专属全部主备provider/data/root/fields/字符/token/成本/destination/时限/
retention manifest；OBS-S01、OBS-S02、OBS-S03、OBS-S04、OBS-S05、OBS-S06、OBS-W01、
OBS-W02、OBS-W03、WRITE-F01、WRITE-F02、WRITE-F03、WRITE-F04、采样、资源、pause、
observer/stop、自启动off。每周期先密封合同、独立transaction；缺项即FAIL。

### G12A — 两小时/五周期观察

**Reviewers：**2 名：可靠性时间序列 agent、资源/backlog agent。  
**检查：**五个真正成功周期且连续；失败后窗口重置；LLM模式/egress证据；阶段P95、CPU/
内存/I/O、DB/log增长、backlog、pause、源/config sentinel；逐周期检查全部contract/hash并
重算至少一个完整changeset；结束先pause/进程归零。

### G12B-PRE — 恢复自启动前

**Reviewers：**2 名：最终安全 agent、运维恢复 agent。  
**检查：**所有profile-specific Gate/P0/P1；独立trust anchor与不可写完整release/interpreter、
tamper/TOCTOU；exact REG_SZ bytes；12B profile必须等于G12A；enabled模式全新的
G12B_LOGIN_AUTOSTART authorization hash/caps；arm token；真实atomic conditional create/delete；
不会新增入口。此Gate后用户只先批准exact value/auth hash；最终logout另在D12B-LOGIN后批准。

Reviewer 通过后只能向用户提出“可恢复”建议。没有用户明确批准不得执行。

### D12B-ARM → OP12B-ARM → G12B-ARM

**D/G各2名并满足DAG disjoint。**D冻结exact action、ARM token默认15min/硬30min；在任何
ARM state/token写之前，另由D12B-RB的2名rollback/startup reviewer seal exact OP12B-RB
compensation contract，不执行rollback；D12B-RB未PASS时OP12B-ARM不可eligible。OP先向G11J
protected journal写action intent、expected registry absence、desired bytes hash、ownership/run nonce、
generation与补偿目标，再写arm state并finalize。G检查circuit closed、PAUSED/OFF、进程0、
journal head；token绑定exact value/release/data/profile/auth/generation/SID/expiry/nonce且一次性；
arm未清counter、启动child或写registry。

### D12B-CAS → OP12B-CAS → G12B-CAS

**D/G各2名并满足DAG disjoint。**检查D12B-RB有效、真实create-if-absent、ARM token在提交点消费、
exact type/value、并发loser不覆盖；CAS后
只能ARMED_ON_PRELOGIN/ON。亲验START-S01、START-S02、START-S03：无LOGIN_COMMITTED的
unexpected login/reboot为child/DB/config/source/egress 0。CAS后dormant lease默认24h/硬72h；
从OP12B-ARM起的failure/conflict/crash partial/lease到期只触发OP12B-RB→G12B-RB，Gate/
launcher不写registry；CAS遇到既有同名值（即使同bytes）或third-party replacement均不接管/
不删并PAUSED/REGISTRY_CONFLICT；RB按journal intent/finalize与ownership nonce reconcile，
G继承OP exact终态。不能只审facade。

### D12B-LOGIN → OP12B-LOGIN → G12B-POST

**D12B-LOGIN：**2名满足DAG exact角色/基数/disjoint规则的reviewer核对G12B-CAS、exact Run/release/auth/generation、LOGIN_COMMITTED
默认5min/硬10min、review hash/最终批准/SID/machine+boot generation/previous session/“下一次
新logon”关系/nonce绑定、logoff取消补偿。禁止硬编码尚不存在的future session。D通过后用户
才再次确认已保存工作并批准立即注销。

**G12B-POST Reviewers：**2名，严格满足DAG对`min_not_in`/`forbidden_agent_sets`声明的exact
集合和数量；不得用自然语言扩大或缩小排除范围。  
**检查：**trust/release/auth hash、单launcher/supervisor/worker、首周期、pause、无storm/未授权
egress、入口唯一性。失败只发出预授权OP12B-RB trigger；G本身不写。G12B-RB两名按DAG与OP执行者disjoint的reviewer
核对仅current exact bytes被conditional delete；不同值不碰并报告。成功只能
LOGIN_VALIDATED_PAUSED/ON、process0；不能宣称RECOVERED。

### D12C → 用户授权冻结intent → G12C-PRE → OP12C → G12C — 最终启用下一登录

**D12C：**2名满足DAG exact角色/基数/disjoint规则的reviewer先审circuit closed、exact
Run/release/auth/generation、token TTL，并seal OP12C/OP12C-RB合同和唯一proposed action/intent
hash；不得声称审过尚未生成的final用户授权。用户随后只能授权该exact intent hash/action ID；
不批准时保持safe waiting，不是BLOCKED。**G12C-PRE：**恰好3名按DAG与D12C disjoint的reviewer
分别负责control、release/auth、rollback，重验actual authorization/contract/ledger head后才开放OP12C。
**G12C：**恰好3名按DAG角色/基数/disjoint规则分别负责control/circuit、release/auth/security、runtime operations。
OP12C只能CAS为ENABLED_IDLE/ON且process0；
ACT-S01、ACT-S02、ACT-S03、ACT-S04、ACT-S05、ACT-S06、ACT-S07全部通过才可记录
`lifecycle_outcome=RECOVERED`，G前后物理state不变。reviewer还须核对token/control写前journal
intent、写后finalize及crash reconcile；OP/G失败只触发OP12C-RB→G12C-RB；
后者2名按DAG与OP执行者disjoint的reviewer继承并核对OP exact terminal state：owned Run未漂移时
为LOGIN_VALIDATED_PAUSED/ON，第三方Run冲突时不碰registry并为PAUSED/REGISTRY_CONFLICT。
当前session启动不在本节点权限内。G12C通过后每个普通登录/cycle仍必须先密封
`runtime_cycle_policy` operation contract，绑定auth/intent/generation/process/journal head、exact
document/source、write set、egress与持久daily/monthly caps。reviewer必须亲验ACT-S08、ACT-S09、
ACT-S10；缺逐cycle合同、授权/上限失效或wrong PK/file/journal head均circuit open+pause，且
registry/config/source零写。

### D05Rnn → OP05Rnn → G05Rnn — 每次独立 reset

每次使用唯一`05R01`–`05R99`；D/G各2名且operator不参与。D审root cause、open latch/generation、
process0、用户reset token、failure generation、exact ancestor `D` return node与完整downstream
invalidation；G/OP/占位符return均FAIL。OP只清active latch/budget、generation+1、仍PAUSED；
G审历史保留、20s进程0、registry/config/DB/source/release/auth hash不变。RST-S01、RST-S02、
RST-S03、RST-S04、RST-S05、RST-S06、RST-S07、RST-S08、RST-S09全部通过；G后无直接resume边。

## 6. Reviewer 固定工作步骤

1. 读取 `README.md`、`task_plan.md`、`gate_state_machine.md`、`gate_dag.v4.json`及其instance schema、
   `operation_contracts.v4.json`、动态operation/auth schema、`acceptance_thresholds.md`、
   `gate_ledger.schema.json`、review/confirmation schemas、test registry、当前WP、
   测试计划和本协议。
2. 核对plan/evidence/ledger revision/hash；不匹配则输出`verdict=FAIL`、
   `reason_code=EVIDENCE_DRIFT`，禁止自造verdict。
3. 查看 Git diff/commit 与 CodeGraph impact；检查是否超出文件白名单。
4. 阅读失败测试与修复测试，确认它们穿过实际代码路径。
5. 从脱敏raw data或获批approved evidence重算至少一个指标/状态；secret永不采集，reviewer
   不把正文/路径复制回repo。
6. 主动构造至少一个实施者未写出的反例；无法执行时写出原因和静态推理。
7. 检查生产/config/source sentinel、worker paused/autostart off（适用时）。
8. 按 P0–P3 写 findings，每条带文件/符号/证据定位、风险、复现和建议。
9. 给出唯一结论，不使用“看起来可以”“大概没问题”。
10. 同时返回符合`review_result.schema.json`的machine JSON与完整Markdown报告；路径分别为
   `reviews/<node>/<role>-review-vN.json|md`。reviewer 不编辑文件；若主 agent代存，保存原始
   payload hash。保存完成后由同一reviewer重读actual bytes并单独返回符合
   `review_confirmation.schema.json`的confirmation；无confirmation不得写PASSED ledger。

## 7. 审查报告模板

```markdown
# <Gate ID> <Role> Independent Review

- Reviewer agent:
- Review time/timezone:
- Independence statement:
- Git commit/worktree:
- Evidence manifest path + SHA-256:
- Scope reviewed:
- Commands/checks independently run:

## Counterexample attempted

## Findings

### [P0|P1|P2|P3] Title
- Evidence:
- Reproduction/reasoning:
- Impact:
- Required disposition:

## Coverage gaps

## Verdict

`PASS | PASS_WITH_NONBLOCKING_FINDINGS | FAIL`

## Reason code（PASS时为null）

`EVIDENCE_DRIFT | NO_INDEPENDENT_REVIEW | MISSING_AUTHORIZATION | ENVIRONMENT_UNAVAILABLE |
OPEN_P0_P1 | SCOPE_DRIFT | null`

## Re-review requirements
```

没有 findings 时也必须写 attempted counterexample 和 coverage gaps，禁止只交一行 `LGTM`。

## 8. Finding 关闭协议

1. 实施者在独立文件中逐条响应：`accepted`、`rejected-with-evidence` 或 `deferred-P2/P3`。
2. `accepted`：做最小修复，更新 tests/evidence revision；
3. `rejected-with-evidence`：必须提供可复现证据，不能只表达意见；
4. reviewer 对新 revision 复审并写关闭/仍开放；
5. P0/P1 只有 reviewer 明确 `closed` 才算关闭；
6. 改动影响早期 Gate 时，回溯失效范围并重开对应 Gate；
7. 不得删除、覆盖或静默降级原 finding。

## 9. 防止“审查形式化”的规则

- 同一个 agent 不得连续承担实施与下一 Gate reviewer，以免间接审自己设计；
- 多 reviewer Gate 要分别派工，初版前不互相引用；
- reviewer 必须检查原始数据，不能只读汇总；
- 每个 Gate 至少有一个 attempted counterexample；
- mutation/fault evidence 缺失时，相关正确性 Gate 不能 `PASS`；
- reviewer 无法访问 Windows/SQLite/生产只读证据时，应缩小结论或 `BLOCKED`，不能猜测；
- G10C/G10R 各随机抽查至少三个早期 Gate 的 hash 与原始脱敏日志；
- 任何 reviewer 建议直接恢复自启动而跳过用户授权，按 P0 处理。
