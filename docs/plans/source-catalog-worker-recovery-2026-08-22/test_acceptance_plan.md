# Source Catalog Worker — 测试与验收计划

> 原则：测试必须证明目标缺陷被捕获、修复语义未改变、生产边界未被触碰。  
> “pytest 全绿”本身不是 Gate 证据；必须同时有红灯、mutation、故障注入和独立审查。

## 1. 测试层级

| 层级 | 目的 | 数据/环境 | 典型耗时 | 每个 WP 是否必跑 |
|---|---|---|---:|---|
| L0 静态/差异 | 语法、格式、diff、敏感路径 | 工作树 | 秒级 | 是 |
| L1 单元 | 纯函数、状态转移、时间/错误分类 | 内存/tmp | 秒级 | 相关 WP 是 |
| L2 contract | 跨模块公开契约、schema、control、ledger validator | tmp DB/root/config | 秒至分钟 | 是 |
| L3 生产形状性能 | SQL/scan 的复杂度与 planner | 20k–60k tmp DB/files | 分钟 | WP-01/02/06/09 |
| L4 fault injection | crash、pause、磁盘满、写失败 | tmp 子进程 | 分钟 | WP-03/04/05/09 |
| L5 Windows control | PID、PowerShell、login chain | 隔离进程/tmp runtime | 分钟 | WP-05/09 |
| L6 tmp E2E | 完整 worker 单周期与恢复 | 全 tmp、LLM stub | 分钟 | WP-09 |
| L7 生产只读 | 实际分布的 plan/语义/空间 | `mode=ro`、worker paused | 有界 | Gate 11A |
| L8 生产 canary | 分阶段A与逐provider B | 人工授权、无自启动 | 有界 | G11B-A1/A2/A3、BP/BFnn |
| L9 观察 | 5 周期/2 小时稳定性 | 人工运行、无自启动 | ≥2h | Gate 12A |

低层测试不能替代高层 Gate；高层成功也不能豁免低层回归。

## 2. 全局测试隔离守卫

### 2.1 测试进程启动前

每个测试 session 应解析并拒绝以下路径：

- repository production `.source_catalog`；
- `config/source_catalog.yaml`；
- 真实 `companies/`；
- 报告中记录的已登记外部portfolio/cloud-sync source roots；
- StockWiki 路径；
- 用户 home 或 workspace root 作为递归删除/移动目标。

所有 test config 必须显式传入，不能依赖 cwd 向上发现生产 config。若被测代码没有安全的
依赖注入点，先在当前 WP 增加最小注入接口和 contract test，不能 monkeypatch 一个假的
安全结论。

### 2.2 测试前后哨兵

保存并比较：

- production config SHA-256/size/mtime；
- production DB/WAL/SHM size/mtime（不读取 secret）；
- worker control/runtime 的预期隔离字段；
- HKCU Run 是否符合当前 machine DAG 阶段：OP12B-CAS 前不存在；CAS 后只能是已批准 exact
  dormant value；除 OP12B-CAS/OP12B-RB 外任何测试造成变化均为 P0；
- 源目录抽样/全量 manifest（依 Gate 风险选择）。

完整路径、用户名、portfolio/持仓文件名、命令行和可逆 source manifest 不写入仓库；原始值
仅在另行批准后保存到repo外受限evidence。仓内只保存opaque ID、计数、脱敏摘要与
key在repo外的HMAC；禁止保存可被字典猜测的原始source/path SHA-256。

测试若导致生产文件元数据变化，即使所有断言通过也视为 P0。

### 2.3 清理规则

- pytest 只清理由自身 `tmp_path` 创建的精确路径；
- 不在 shell 中拼接递归删除命令；
- 失败时保留 tmp artifact 的路径和 hash供诊断，随后由测试框架回收；
- 测试绝不清理生产 lock、WAL、备份或日志。

### 2.4 全局安全 Test IDs

| ID | 断言 |
|---|---|
| SAFE-S01 | production config/worker config/.env hash与mtime无意外变化；session override不持久化 |
| SAFE-S02 | source写由OS/sandbox主动拒绝，content/size/mtime/ACL sentinel仍不变 |
| SAFE-S03 | 普通tests/retention/migration对生产backup删除/VACUUM/DROP调用数为0 |
| SAFE-S04 | one-shot结束后worker/supervisor/parser=0且无自动restart |
| SAFE-S05 | reset/resume/arm/login-commit/final-activation正交；每个生产控制动作只作用本次exact value/token，第三方值不变 |
| SAFE-S06 | 唯一T/D/I/OP/G DAG、machine review payload/hash、独立性、ledger chain与下游失效边完整 |
| SAFE-S07 | canary run ID、operation+PK+column/exact-file changeset、actual touched delta、RPO/RTO/reconcile逐项可重算 |
| SAFE-S08 | control/status预期diagnostic log写与DB/config/source零写被正确分类 |
| SAFE-S09 | secret永不采集；raw evidence approved sink/ACL/加密/TTL与仓内opaque标识符合合同 |

### 2.5 Ledger validator 与 Test-ID registry

T00L 在任何正式 ledger/worker 操作前实现并冻结：

- `GL-S01`、`GL-S02`、`GL-S03`、`GL-S04`、`GL-S05`、`GL-S06`、`GL-F01`、
  `GL-F02`、`GL-F03`、`GL-F04`、`GL-F05`、`GL-F06`、`GL-F07`、`GL-F08`、
  `GL-F09`、`GL-F10`、`GL-F11`、`GL-F12`，逐项定义见
  `ledger_validator_contract.md`/`gate_ledger_validator_vectors.v4.json`；
- DAG/vectors/test-registry/operation-catalog 各自专用 instance schema 的shape正/负例；canonical
  JSON、seq/prev/expected-head、review payload+detached confirmation actual hash、reviewer exact
  role/cardinality/disjoint、branch/join、production state、OP catalog/dynamic contract/auth/evidence/generation；
- mutation/property 序列≥200，存活 mutant=0；全 tmp、网络0、生产 DB/registry/config/source调用0；
- `TESTID-S01`：`test_id_registry.v4.json` 中每个 concrete ID 定义恰好一次，逐ID具有
  `introduced_at/variant_at/expected_red_at/required_green_at/revalidate_at/condition`；所有活动章节
  引用必须存在且按冻结 extraction grammar 提取。范围缩写、未定义/同义重复 ID、owner×due
  笛卡尔推导、template未按 frozen parser route manifest 展开均失败。
- `G10-PROMPT-S01`：六份G10C/G10R prompt的输入闭包、exact role/head/hash、禁止未来依赖、
  唯一successor和review JSON+Markdown+confirmation输出逐份通过；G10C不读取G06/G07/G08/A/B，
  G10R exact join必须含still-valid G09P/G09且不读取12A/12B，任何缺前驱、共享模板或伪循环失败。
- 冻结计划 revision 前先只读运行 `plan_consistency_check.py`；它必须验证10个schema的meta/shape、
  4组instance、固定DAG无环/无悬空、reviewer exact role/cardinality/disjoint、每个固定OP唯一catalog
  匹配、283个concrete test ID及活动引用闭包、18组vector及错误优先级。该预检PASS不豁免
  T00L的真实validator/property/mutation实现，也不替代独立agent审查。

## 3. 确定性数据夹具

### 3.1 两套规模

**Semantic-small**：几十至数百 documents，用于穷举状态组合、随机 property comparison 和
可读的失败 diff。

**Perf-production-shape**：默认 25,000 documents、50,000 locations；可通过显式参数扩至
报告规模以上。fixture metadata 必须记录 exact seed、row counts、分布和 schema hash。

### 3.2 状态覆盖

| 维度 | 必须值 |
|---|---|
| root | active、inactive、missing/orphan 防御样本 |
| location status | active、retired/非 active |
| role | original_primary、其他合法 role、重复 role |
| document location | 0、1、多个 |
| artifact | absent、completed、partial、unsupported、failed |
| failed | due retryable、not-due retryable、terminal |
| generator | current、old、不同 version |
| kind/priority | 每个真实分支至少一个，含 tie-break |
| time | 边界前、边界等于、边界后；固定 UTC |
| path | ASCII、中文、大小写差异、长路径、junction/symlink |

### 3.3 Fixture 质量检查

- 使用固定 seed 和批量事务；
- 生成后运行行数、唯一性、外键/预期孤儿、状态分布断言；
- 记录 schema SQL hash 与 fixture logical digest；
- 同 seed 两次 logical digest 相同；
- oracle 不调用被测 queue 函数或复制其 SQL；
- fixture build time 与 query time分开报告。

## 4. SQL 语义与性能测试

### 4.1 语义测试 ID

| ID | 断言 |
|---|---|
| Q-S01 | active `original_primary` 文档进入候选 |
| Q-S02 | location 必须同时 active、role=`original_primary`、`source_id=primary_source_id` |
| Q-S03 | locationless/source-mismatch 文档不得进入任何 batch，但必须保留在性能 outer fixture |
| Q-S04 | completed current-version artifact 被排除 |
| Q-S05 | old generator/version artifact 按原合同重新处理 |
| Q-S06 | retryable failed 仅在 due 后进入 |
| Q-S07 | terminal failed 永不自动重试 |
| Q-S08 | partial/unsupported 分支与旧意图一致 |
| Q-S09 | priority 全分支排序正确 |
| Q-S10 | 同 priority 以 document_id 稳定排序 |
| Q-S11 | LIMIT 前候选语义正确，不被 join duplication 改变 |
| Q-S12 | duplicate locations 不产生重复 document IDs |
| Q-S13 | orphan root/location 的行为由明确合同决定 |
| Q-S14 | 50 个以上固定随机 seed 与独立 oracle 完整有序一致 |
| Q-S15 | 多个 primary locations 时只要存在一个 source-matching active 关系即可且不重复 |
| Q-S16 | `force=False/True` 对 completed/retry/terminal/version 的完整矩阵符合现有合同 |
| Q-S17 | logical document S1→S2：旧source artifact不抑制S2/不继承terminal；UPSERT后source ID/hash=S2/H2 |

### 4.2 Plan guard

不要断言某个 SQLite 版本完整 plan 文本完全相同。应断言：

- 不存在对每个 outer document 执行、并只以 `location_status` 为访问路径的相关子查询；
- candidate locations/documents 使用一次性集合、document-oriented lookup 或等价低复杂度路径；
- 没有因 JOIN duplication 导致全量排序放大；
- 支持版本上使用了设计所依赖的索引，或无索引方案仍在 work budget 内；
- 缺少 `sqlite_stat1` 时也不退化回已知坏形状。

plan parser 应匹配必要 token/关系，不把自动索引名称或缩进作为稳定 API。

### 4.3 性能方法

1. 固定机器电源模式并记录 CPU/存储/SQLite version；不跨机器直接比较绝对秒数。
2. 构建 fixture 后关闭重开 connection；warm 与 cold-ish 分开。禁止声称真正 cold cache，
   除非有安全、可重复的 cache control。
3. warm 至少 30 次、cold-ish 至少 10 次；nearest-rank 计算 percentile。样本少于 20 时
   P95不作主判据，使用 max并标注不足；报告全部样本，不只取最快一次。
4. D01冻结 `PROGRESS_PROXY_APPROX` 或 `STMTSTATUS_VM_STEP_EXACT`；前者只作近似work guard，
   后者必须满足 `acceptance_thresholds.md` 的native binding合同；wall、plan、N/2N同时主判。
5. 旧查询只在有 progress 中止的 tmp DB 运行；绝不在生产运行 900 秒复现。
6. 性能阈值：warm P95 <2s、cold-ish 10次 max <10s；cold-ish定义为新进程/connection、
   SQLite page cache冷，OS cache不声称完全冷。
7. N=5k/10k/20k/40k 固定分布 VM-work scaling；翻倍 ratio ≤2.8、wall median ≤3.0，
   同时必须显著低于旧实现 work budget。
8. 统计失败时保存 raw CSV/JSON，不通过放宽阈值直接“修复”测试。

稳定性能ID：

| ID | 断言 |
|---|---|
| Q-P01 | measurement mode、SQLite source-id、binding/harness、`progress_n`(proxy)、PRAGMAs、params、LIMIT、fixture digest跨old/new/样本一致 |
| Q-P02 | 支持的SQLite版本矩阵均无已知灾难plan，语义oracle零差异 |
| Q-P03 | 5k/10k/20k/40k VM proxy与wall scaling满足阈值 |
| Q-P04 | 25k/50k warm n≥30、cold-ish n≥10的绝对预算满足 |
| Q-P05 | proxy模式改变 `progress_n`/handler安装点/prepare边界的mutant必须失败 |
| Q-P06 | proxy evidence若声称exact VM-step count或严格上下界必须失败 |
| Q-P07 | 仅exact模式：已知query的STMTSTATUS counter、完整消费/中断/overflow合同与harness一致 |

T02A mutation labels（不是 Test ID，必须由右侧稳定测试杀死）：

| Label | 注入 | killed_by |
|---|---|---|
| MUT-Q02A-01 | 删除active/role/source predicate | Q-S02,Q-S03,Q-S15,Q-S17 |
| MUT-Q02A-02 | 恢复correlated status scan/bad plan | Q-P01,Q-P02,Q-P03,Q-P04 |
| MUT-Q02A-03 | LIMIT在dedupe前 | Q-S11,Q-S12,Q-S14 |
| MUT-Q02A-04 | force/retry/terminal反转 | Q-S16 |
| MUT-Q02A-05 | stale S1抑制/绑定S2 | Q-S17 |

### 4.4 Store-open / migration 稳定 ID

两个 02B 分支各自的 T commit 都必须包含 shared lifecycle tests：

| ID | 断言 |
|---|---|
| M-COM-S01 | exact existing schema ordinary open成功，DDL-denying authorizer记录0 DDL |
| M-COM-S02 | missing DB ordinary open返回SCHEMA_INIT_REQUIRED且文件创建数0（如mode=rw） |
| M-COM-S03 | explicit `schema init --profile` 建立exact fresh schema |
| M-COM-S04 | prior supported schema explicit upgrade；ordinary open只报SCHEMA_UPGRADE_REQUIRED |
| M-COM-S05 | init/upgrade重复执行幂等；未知/错误partial schema fail closed；ZR1002/ZR1003 tmp夹具先显式init/upgrade再reader open |
| M-COM-S06 | worker/login/canary/reader ordinary path对missing/outdated schema绝不调用init/upgrade；ZR1002/ZR1003不得靠产品eager DDL转绿 |
| M-COM-F01 | init/upgrade每个crash点只有old或完整new状态，可reconcile |
| M-COM-F02 | scratch hard-quota ENOSPC安全失败，真实卷不受影响 |
| M-NI-S01 | NO_INDEX exact schema/hash，无新增index |
| M-NI-S02 | eager startup DDL/index mutant被authorizer拒绝 |
| M-NI-P01 | 无stats/支持SQLite矩阵仍满足SQL plan/work预算 |
| M-IDX-S01 | INDEX exact SQL/xinfo/schema ledger/hash |
| M-IDX-S02 | migrator仅operator entry可调用，startup不可达 |
| M-IDX-S03 | index migration重复执行幂等 |
| M-IDX-F01 | DDL各crash点可恢复/对账 |
| M-IDX-F02 | 同名错误index definition被识别且不误报完成 |
| M-IDX-F03 | ENOSPC/空间guard在生产DDL前失败 |
| M-IDX-P01 | build峰值空间/时长/DB bytes/write amplification实测 |
| M-IDX-P02 | migration前后plan/性能收益，不依赖ANALYZE偶然结果 |
| M-IDX-M01 | eager-startup index mutant必须失败 |
| M-L-EDGE-S01 | 缺G11B-A3时D11M-L不可eligible |
| M-L-EDGE-S02 | 缺G07E时D11M-L不可eligible |
| M-L-EDGE-S03 | G07O profile无D11M-L/BP/BF出边 |
| M-L-S01 | ordinary open不隐式创建request-ledger schema |
| M-L-S02 | 显式迁移后source/auth/request状态schema精确匹配 |
| M-L-F01 | request-ledger migration crash/reconcile，不重复provider请求 |

## 5. Checkpoint 与恢复测试

### 5.1 状态模型断言

| ID | 场景 | 预期 |
|---|---|---|
| C-S01 | scan DB commit 前 crash | scan 未完成，重启应重扫 |
| C-S02 | DB commit 后、JSON 前 crash | 从 `scan_runs` 对账，不立即重扫 |
| C-S03 | JSON temp write 后 crash | 旧或新完整 JSON 可读，无半文件 |
| C-S04 | scan 后 queue select crash | checkpoint 保留，normalize 可重试 |
| C-S05 | parser 中 pause | artifact 不假成功，child 回收 |
| C-S06 | LLM/export/prune 失败 | scan 不重做，相应阶段按合同重试 |
| C-S07 | JSON 损坏 | 明确恢复/失败，不默默采用错误时间 |
| C-S08 | 旧 schema | 向后兼容读取并写新版本 |
| C-S09 | wall clock 回拨 | 不导致当前操作 timeout/负 duration 错误 |
| C-S10 | 假 completed JSON、DB 无记录 | 不信任 JSON，不跳过必要 scan |
| C-S11 | `completed_with_errors` + benign quarantine | 成功 root checkpoint推进，不全盘重扫 |
| C-S12 | 单 root offline/access denied | 该 root保持 due/退避，其他成功 root不重扫 |
| C-S13 | partial enumeration/interrupted | 不标全局完成，按 per-root恢复 |
| C-S14 | root set/config/scanner version变化 | fingerprint失配的 root重新 due |

每个测试必须销毁进程内对象并以新进程/新 connection 读取落盘状态，防止只验证内存。

## 6. 取消、heartbeat 与可观测性测试

| ID | 场景 | 验收 |
|---|---|---|
| O-S01 | 慢 SQL + pause | pause SLA 内 SQLite 中断，reason=`paused` |
| O-S02 | 慢 SQL + stop | stop SLA 内退出且无重启 |
| O-S03 | 慢 SQL + deadline | reason 与 pause/DB error 区分 |
| O-S04 | handler callback 抛错 | transaction 安全回滚，handler 清除 |
| O-S05 | 下一快 SQL | 不继承旧 handler/deadline/token |
| O-S06 | handler overhead | 快查询额外耗时低于 Gate 定义阈值 |
| O-S07 | heartbeat 前进、progress 冻结 | watchdog 仍识别无业务推进 |
| O-S08 | runtime 写失败 | 主事务不半提交、不产生 tight loop |
| O-S09 | 日志检查 | 无正文、prompt、secret、完整外部路径泄露 |
| O-S10 | query开始后另一真实进程更新 control generation | callback在≤5s P95/≤10s max看见新状态 |
| O-S11 | liveness/VM/business fields | VM activity不被当业务成功或清零 failure budget |

默认 SQL pause P95≤5s/max≤10s；快查询 handler median overhead≤max(5%,5ms)、P95≤
max(10%,10ms)。Parser 与 supervisor SLA 见 `acceptance_thresholds.md`；放宽需 D Gate ADR。

## 7. Supervisor/Windows 状态序列测试

用注入 clock/RNG/process facade，避免测试真实等待 120/900 秒。至少覆盖：

| ID | 输入序列 | 关键断言 |
|---|---|---|
| S-S01 | 三次快速同签名失败 | 连续计数、指数退避 |
| S-S02 | 三次 >900s 无成功失败 | 不能因 uptime 清零 |
| S-S03 | heartbeat 有、progress 无 | timeout/熔断而非假健康 |
| S-S04 | 两失败→完整成功→一失败 | 仅完整成功清零 |
| S-S05 | 交替失败签名 | global滚动预算仍触发 circuit，无 tight loop |
| S-S06 | backoff 中 pause | 及时退出，不再启动 child |
| S-S07 | startup delay 中 pause | 同上 |
| S-S08 | persistent pause + login | launcher 不启动 supervisor |
| S-S09 | circuit open + login/resume/resume-session/arm | 全部不复活，返回CIRCUIT_OPEN，latch/counters/generation不变 |
| S-S10 | PID reuse | 不终止不同 creation time/executable 进程 |
| S-S11 | stale/corrupt runtime | fail safe 且可诊断 |
| S-S12 | resume race | 最终只有一个 supervisor/worker |
| S-S13 | 多次 child restart | 120s login delay每 supervisor/login session只支付一次 |
| S-S14 | supervisor/reboot/login后继续失败 | global/per-signature counters不重置 |
| S-S15 | 缺失/损坏 control/circuit | 受管生产 fail closed，只能显式 reset |
| S-S16 | 旧 attempt heartbeat/sequence | 不能使新 child被误判健康 |
| S-S17 | Job Object assign failure/supervisor crash | fail closed，20s内无 orphan parser |
| S-S18 | 三动作全状态矩阵 | reset-alone仍PAUSED/进程0；resume不reset；reset→另一次resume才单实例；arm不启动/清counter |

真实 Windows 子进程 smoke test只能补充 facade tests，不能替代状态转移穷举。

## 8. Scanner 测试

### 8.1 正确性稳定ID

| ID | 断言 |
|---|---|
| SC-S01 | unchanged按合同reuse，seen/reused/hashed计数与DB对账 |
| SC-S02 | size/mtime/identity/sidecar变化即时reobserve/hash并使缓存失效 |
| SC-S03 | 每日确定性rehash≥3.34%，每文件最长30天覆盖 |
| SC-S04 | same-size/same-mtime内容变化在detection SLA内发现 |
| SC-S05 | rehash/audit不修改source content/size/mtime/ACL |
| SC-S06 | offline/access-denied root不批量retire；online roots独立完成 |
| SC-S07 | delete/restore/rename/case/Unicode保持identity合同 |
| SC-S08 | junction/symlink/reparse不逃逸registered root |
| SC-S09 | scan interrupt后scan_runs/checkpoint/per-root due对账 |
| SC-S10 | full source manifest在每种scan后不变 |
| SC-S11 | battery-disabled在昂贵enumeration前gate，files_seen=0 |
| SC-S12 | AC恢复只执行一次due scan，不补跑多次 |
| SC-S13 | power API unavailable按配置fail-safe且可诊断 |

### 8.2 性能

对完整生产 topology（约244 company walks/16,570 groups、429 Dropbox-like dirs/9,853 groups、
46.6k files）分别报告 enumerate、sidecar、existing-state fetch、observe、hash、commit。测试
unchanged、1% changed、10% churn。unchanged P95≤120s 且至少2×同机基线。优化提交每次只
改变一个主要机制，以便归因。

- SC-P01：full topology分阶段raw timing与计数完整；
- SC-P02：同协议candidate P95≤120s且baseline_P95/candidate_P95≥2.0；
- SC-P03：1% changed/10% churn各阶段无未解释>25%回归。
- SC-P04：baseline/candidate exact commit、topology/environment/instrumentation hashes完全一致，
  每场景各n≥10且历史427s不作正式分母。

### 8.3 电源策略

- `allow_processing_on_battery=false` 时昂贵 scan 前即 gate；
- 插电恢复后按 due 规则运行一次，不补跑多次；
- power API unavailable 时行为符合配置默认且可诊断；
- 轻量 control/heartbeat 不被错误 gate。

### 8.4 Metadata tamper 与重 hash

由SC-S01、SC-S02、SC-S03、SC-S04、SC-S05覆盖；不得再使用未编号的“metadata tests”代替。

## 8P. Parser 分格式测试

`P-FMT00-ROUTE` 先核对候选代码 route digest、以下 registry 和 release enablement 完全一致；
任何新增/删除 extension/parser 都使 D06P/G06P/G10R 失效。

| Code | Route | Extensions/branch | S/M稳定ID |
|---|---|---|---|
| 01 | plain_text | `.txt,.md,.csv` | `P-FMT01-S`,`P-FMT01-M` |
| 02 | html_markdownify | `.html,.htm` | `P-FMT02-S`,`P-FMT02-M` |
| 03H | MHT HTML part | `.mht`有HTML | `P-FMT03H-S`,`P-FMT03H-M` |
| 03T | mht_text fallback | `.mht`无HTML | `P-FMT03T-S`,`P-FMT03T-M` |
| 04P | PyMuPDF/page-aware fallback | `.pdf` | `P-FMT04P-S`,`P-FMT04P-M` |
| 04D | dayu_docling | `.pdf`+docling artifact | `P-FMT04D-S`,`P-FMT04D-M` |
| 05 | python-docx | `.docx` | `P-FMT05-S`,`P-FMT05-M` |
| 06 | antiword | `.doc` | `P-FMT06-S`,`P-FMT06-M` |
| 07 | openpyxl | `.xlsx` | `P-FMT07-S`,`P-FMT07-M` |
| 08 | xlrd | `.xls` | `P-FMT08-S`,`P-FMT08-M` |
| 09 | python-pptx | `.pptx` | `P-FMT09-S`,`P-FMT09-M` |
| 10J | structured JSON | `.json` | `P-FMT10J-S`,`P-FMT10J-M` |
| 10X | structured XML | `.xml,.xsd` | `P-FMT10X-S`,`P-FMT10X-M` |
| 99 | unsupported | 其他suffix | `P-FMT99-U` |

每个 `P-FMT<code>-S` 按 `acceptance_thresholds.md` 每route n≥20；多extension每extension≥5。
每个启用 M bucket n≥10/max主判；若禁用则必须实例化 `P-DIS-<code>-M` 并以≥5个边界样本
证明parser启动数0。每route另实例化：

- `P-LIMIT-<code>-O`：>100MiB/结构上限，n≥5，deferred/unsupported；
- `P-ERR-<code>-C`：适用route的corrupt，n≥10；
- `P-ERR-<code>-E`：适用容器的encrypted，n≥10；
- `P-NA-<code>-C|E`：不适用时的明确理由与零silent skip；
- `P-PAUSE-<code>`：执行route n≥20，10s graceful/20s total；antiword含grandchild。

每样本记录route digest、extension、size/结构量、wall/CPU/peak memory/exit/error。重复文档不算
独立样本，不删outlier。每个enabled route/bucket单独通过；缺fixture或未通过只能禁用，不能
被其他格式带过，不能把HTML与plain-text样本合成一个统计桶。

## 9. LLM 测试

所有自动测试设置 network deny/stub。测试 ID：

- L-S01 content hash + prompt/model/schema 相同才复用；
- L-S02 任一版本变化使缓存失效；
- L-S03 batch 输出乱序/缺项/重复项被逐文档拒绝；
- L-S04：只有明确未接受的429/失败，或支持同一idempotency key/result lookup的provider，才按
  预算重试；普通post-send timeout/含糊5xx进入OUTCOME_UNKNOWN且零自动重发；
- L-S05 permanent failure 不再自动重试；
- L-S06 中断后不自动新建第二外部请求、不把半结果标completed，本地成本按最大reservation
  保守记账；不声称所有provider exactly-once billing；
- L-S07 arrival/service simulation 满足 drain 或显式 backlog 上限；
- L-S08 日志与 evidence 不含全文/secret；
- L-S09 新 provider 未授权时 fail closed；
- L-S10 单线程 client 没有并发调用。
- L-S11 每 document 只选一个 current completed normalized input，dedupe在LIMIT前；
- L-S12 old/failed summary version不会永久抑制 current generator/version；
- L-S13 同正文不同 title/source/kind 不复用 source-bound artifact；
- L-S14 exact canonical request digest相同只复用 provider payload，逐文档重新绑定locator；
- L-S15 fallback provider未逐项授权时不可调用；
- L-S16 base completion≥1.2×arrival、≤7天drain、oldest 24h/72h与1/7/30天成本SLO；
- L-S17 观察/自启动未获持续授权时强制 LLM off + egress deny。
- L-S18 source rotation：S1 normalized/summary不抑制S2，LLM不得把S1正文绑定成S2 artifact；
- L-S19 stage-bound authorization：错误stage、旧Canary/12A manifest、过期/撤销、release/
  config/provider drift、fallback scope或cap为空全部零外发并pause；
- L-S20 在PREPARED前/后、send后、response后、cache后、artifact commit前逐点crash，以新进程
  恢复并验证ledger/artifact/cost reservation；
- L-S21 支持idempotency lookup的provider只以同key reconcile；不支持者停OUTCOME_UNKNOWN且
  零自动重发，再发必须新授权。

真实provider测试不属于普通CI，只能在G11B-BP及每个G11B-BFnn的独立授权/操作节点执行。

## 10. Retention、容量和 migration 测试

- R-S01 tmp log 按 age/count/size dry-run 列候选；
- R-S02 实际删除仅限 resolved tmp log root；
- R-S03 symlink/junction/path traversal 被拒绝；
- R-S04 正在使用、权限拒绝和并发 rotation 可诊断；
- R-S05 `_project_root`/`project_root` 回归测试先红后绿；
- R-S06 `dbstat` 不可用时容量报告降级且标注估算；
- R-S07 报告命令只读，不触发 migration/VACUUM；
- R-S08 retention/capacity报告在空间低于安全线时只告警/阻断，不执行destructive action；
- R-S10 `.env` ACL 审计不打印 values。
- R-S11 ENOSPC 仅由 faulting VFS/facade/硬quota scratch触发，真实卷 free space不下降到风险线；
- R-S12 backup guard：任何普通 retention/migration test对生产备份删除调用数为0；
- R-S14 repo evidence扫描不含用户名、完整外部路径/portfolio名/命令行/正文。

旧 `M-S*`/`M-F*`/`M-P*` 编号在 v4 被 shared `M-COM-*`、branch-specific `M-NI-*`/
`M-IDX-*` 与 request-ledger `M-L-*` 取代；旧编号不得重新创建或作为别名引用。

### 10.1 Evidence lifecycle稳定ID

- EV-S01：注入secret/token/cookie/credential后，repo与获批raw evidence均无明文；误捕获触发P0；
- EV-S02：非approved root、workspace/temp/cloud-sync、宽ACL、未加密或reparse path全部fail closed；
- EV-S03：Gate disposition+7日、采集+30日、audit hold和inventory精确清理；30日未结案BLOCKED。

任何生产 cleanup、backup 删除或 ACL 修改没有自动验收步骤，因为它们不在本计划默认授权
范围；未来若需要必须新建独立 destructive runbook 和用户批准 Gate。

## 10P. 生产执行封装测试

| ID | 场景 | 验收 |
|---|---|---|
| PX-S01 | one-shot/max_cycles=1 | 恰好一个周期/指定stage后退出，不靠计时kill |
| PX-S02 | session overrides | scan/export/prune/LLM/batch仅本进程生效，production config hash不变 |
| PX-S03 | release identity | 外部trust anchor与完整release/interpreter/lazy-module manifest匹配；worker identity不可写 |
| PX-S04 | roots分离 | code root不会隐式成为catalog/config/source root |
| PX-S05 | operation/write contract基础层 | OP须唯一匹配静态catalog并绑定sealed动态contract；未列operation/PK/column/file/DDL写入被拒绝并触发rollback+pause |
| PX-S06 | source guard | 写操作由OS/sandbox permission拒绝，source sentinel仍不变 |
| PX-S07 | network deny | LLM off时主/备provider均无法egress |
| PX-S08 | circuit/reset/resume/arm | open circuit时arm失败；成功arm不启动/清counter/写registry；三动作正交 |
| PX-S09 | registry条件语义 | 真实API在提交点create-if-absent/conditional-delete；不能只测facade或mutex |
| PX-S10 | evidence redaction | repo内无用户名、完整命令行、外部path/portfolio名 |
| PX-S11 | safe mutant/ENOSPC | throwaway worktree/fault facade后candidate hash/磁盘状态恢复 |
| PX-S12 | exact DB mutation | allowed table内wrong-PK、无WHERE、错误列UPDATE在commit前失败 |
| PX-S13 | net-zero/file mutation | DELETE+INSERT净零、历史文件覆盖、reparse escape均失败；actual touched可重算 |
| PX-S14 | verifier/start-chain tamper | verifier、VBS、PowerShell、lazy module任一篡改均fail closed |
| PX-S15 | check-load TOCTOU | junction/reparse替换、check后换module、restart漂移均不能执行candidate |
| PX-S16 | registry create race | disposable key中两真实进程barrier竞争，只一个成功，loser不覆盖 |
| PX-S17 | registry rollback race | 第三方替换、CAS异常、取消/ARM或lease过期只经OP12B-RB；exact值删除，第三方值保留并PAUSED/REGISTRY_CONFLICT |
| PX-S18 | 12B authorization arm binding | 只接受G12B-PRE后用户批准的exact auth hash/release/value；任一drift零LLM启动 |
| PX-S19 | Canary B legal edge | 缺G07E/G11B-A3/条件migration/一次性auth/one-shot任一项时BP/BF命令拒绝 |

写入、prelogin、reset 与 activation 稳定 ID：

| ID | 验收 |
|---|---|
| CAN-BP-W01 | BP wrong-PK/wrong-column/net-zero/file-overwrite在DB commit/file publish前拒绝 |
| CAN-BF-W01 | 每个BF独立contract；复用BP/其他BF合同失败 |
| CAN-B-W02 | request-ledger/artifact/cache/usage/cost/runtime/checkpoint写全部在合同内 |
| WRITE-F01 | DB commit前crash：pre-run数据RPO seconds=0、staging可精确清理；journal半写不可伪finalize |
| WRITE-F02 | DB commit后/file publish前crash：受保护intent journal可reconcile且不重调provider，ordinary open零DDL |
| WRITE-F03 | publish中crash/reparse/third-party replace：无未授权覆盖，进入pause |
| WRITE-F04 | post-read mismatch：pause/reconcile，零自动provider重发 |
| START-S01 | CAS后/G12B-CAS前意外login：launcher退出，child/egress/DB写=0 |
| START-S02 | G12B-CAS后/最终用户批准前意外login：同上 |
| START-S03 | ARM token到期或CAS后dormant lease到期：零启动，只触发OP12B-RB→G12B-RB，不原地续期/由launcher删registry |
| START-S04 | LOGIN_COMMITTED缺失/过期/replay：零启动 |
| START-S05 | generation/release/auth/Run任一drift：零启动 |
| START-S06 | logoff取消/失败：commit token撤销并PAUSED |
| START-S07 | commit后进程崩溃：token最多消费一次，不自动重试 |
| START-S08 | 两真实进程消费race，≥20 interleavings每次恰好一个成功 |
| START-S09 | 第三方替换Run：不删除、不覆盖、报告 |
| START-S10 | CAS/login各边界power-loss/reboot矩阵均fail closed |
| RST-S01 | 无D05Rnn/用户授权的reset拒绝 |
| RST-S02 | 非PAUSED或process非0时reset拒绝 |
| RST-S03 | stale generation/replayed token零副作用 |
| RST-S04 | reset crash只有old或完整reset两种状态 |
| RST-S05 | reset+resume/arm/login/activate组合flag或隐式调用拒绝 |
| RST-S06 | reset后20s进程仍0 |
| RST-S07 | history/audit完整，active budget精确清理，generation只+1 |
| RST-S08 | reset return只接受失败节点合法祖先中的exact D并失效全部下游；G/OP/占位符或G05Rnn失败时return/resume均不eligible |
| RST-S09 | reset后另行resume仍需其独立生产D/OP/G授权 |
| ACT-S01 | D12C未先冻结action/intent或缺G12B-POST/user auth/G12C-PRE或有P0/P1时OP12C拒绝；用户未批准冻结intent时保持SAFE_PAUSED_WAITING_USER而非BLOCKED |
| ACT-S02 | release/auth/Run/generation drift时拒绝 |
| ACT-S03 | final token replay/expiry拒绝 |
| ACT-S04 | OP12C token/control跨资源写有journal intent/finalize/crash reconcile；完成后20s process=0，DB/config/source/registry/egress零变化 |
| ACT-S05 | OP12C不得调用reset/resume/arm或启动当前session |
| ACT-S06 | OP12C/G12C失败只经OP12C-RB→G12C-RB；owned Run未漂移回LOGIN_VALIDATED_PAUSED/ON，第三方Run冲突不动registry且为PAUSED/REGISTRY_CONFLICT；Gate继承OP终态且不写状态 |
| ACT-S07 | 下一正常login重验G12C outcome/circuit/release/auth/config/routing/data/Run/SID/Job/single-instance；失败零child并PAUSED/ON |
| ACT-S08 | G12C后的第二及每个后续cycle在DB/file/network前各自密封新runtime operation contract，不能复用首cycle或前一cycle合同 |
| ACT-S09 | 任一cycle的authorization expiry/revocation或持久daily/monthly document/character/token/cost cap不足时，egress/DB/file前拒绝、circuit open并persistent pause |
| ACT-S10 | runtime contract的journal head、document/source tuple、DB typed PK/column或exact file任一错误时precommit失败；registry/config/source零写且不自动扩大合同 |

任何 PX 代码/测试在 G10C 后变化都要重开 G09P/G09/G10C。

## 11. 端到端验收场景

### E2E-S01 — NORMAL

tmp 环境完成一次全周期，验证 artifact、fingerprint、sections、LLM stub、export、state、
worker_runs、scan_runs、runtime、pause 和源 manifest。

### E2E-F01 — CRASH MATRIX

在 execution playbook WP-09 的每个边界 crash，以新进程恢复并对账。

### E2E-F02 — CIRCUIT

重复同签名无进度失败直到 circuit open；再次模拟 login，确认不启动；只能通过
D05R01→OP05R01→G05R01 reset，之后仍PAUSED且进程0。直接resume仍拒绝；只有重新经过冻结的
生产pre-review/authorization节点后，独立resume操作才可能eligible。

### E2E-M01 — MUTANTS

逐一注入并绑定杀死它的稳定测试：旧SQL/bad-plan→Q-P02/Q-P03/Q-P04；晚checkpoint→C-S02/
C-S04；uptime reset→S-S02；handler leak→O-S05；scan后power gate→SC-S11；source write/
egress→PX-S06/PX-S07/SAFE-S02；source rotation→Q-S17/L-S18；post-send crash/resend→
L-S20/L-S21；wrong-PK/net-zero→PX-S12/PX-S13；trust tamper/TOCTOU→PX-S14/PX-S15；
registry/prelogin race→PX-S09/PX-S16/PX-S17/START-S01/START-S02/START-S03/START-S04/
START-S05/START-S06/START-S07/START-S08/START-S09/START-S10；reset组合→PX-S08/RST-S01/
RST-S02/RST-S03/RST-S04/RST-S05/RST-S06/RST-S07/RST-S08/RST-S09。
Mutant只在throwaway worktree/运行时注入；结束核对candidate commit、源码SHA、clean diff。

### 11.1 生产操作稳定 Test IDs

| ID | 验收 |
|---|---|
| CAN-A1-S01 | scan-only stage flags与root IDs精确；normalize/export/prune/LLM零调用 |
| CAN-A1-S02 | root-key/column/touched-row changeset符合contract，source/config/egress不变 |
| CAN-A1-S03 | OP后PAUSED/OFF、进程0、checkpoint/RPO disposition与两份review hash齐全 |
| CAN-A2-S01 | exact 3–10 document IDs；scan/export/prune/LLM零调用 |
| CAN-A2-S02 | artifact/status/derived写只触达candidate PK/columns/files，至少3个预期artifact |
| CAN-A2-S03 | precommit/post-read changeset一致，OP后PAUSED/OFF与两份review hash齐全 |
| CAN-A3-S01 | one-shot full-cycle-no-LLM；前两个G均有效，第二cycle/egress调用数0 |
| CAN-A3-S02 | 全阶段write contract/delta/checkpoint/source guard通过 |
| CAN-A3-S03 | OP后PAUSED/OFF、进程0与独立G11B-A3 evidence齐全，不能补签A1/A2 |
| CAN-BP-S01 | G07E/G11B-A3/条件migration与primary专属一次性authorization hash齐全 |
| CAN-BP-S02 | provider/model/docs/fields/characters/tokens/cost/destination不越界，request ledger对账 |
| CAN-BP-S03 | one-shot后PAUSED/OFF、artifact/source binding与两份G11B-BP review hash齐全 |
| CAN-BF-S01 | 每个BFnn有独立授权；primary或前一fallback授权不能复用 |
| CAN-BF-S02 | 每个BFnn caps/routing/destination/ledger独立，失败provider最终禁用 |
| CAN-BF-S03 | 每个OP后pause并独立G11B-BFnn；未审fallback没有release出边 |

### 11.2 观察稳定 Test IDs

| ID | 验收 |
|---|---|
| OBS-S01 | exact G10R profile连续≥5 cycle且wall≥2h |
| OBS-S02 | 任一失败/circuit/restart后窗口归零，不拼接旧周期 |
| OBS-S03 | CPU/memory/I/O/DB/WAL/log均低于D12A冻结限额，原始时间序列完整 |
| OBS-S04 | pause SLA、worker/supervisor/parser归零与自启动off |
| OBS-S05 | source/config不变；LLM-off egress deny或12A auth hash逐请求一致 |
| OBS-S06 | backlog arrival/completion/oldest/drain/cost趋势满足profile SLO |
| OBS-W01 | 每周期transaction前物化并密封exact documents/source IDs/PK/files/RPO/RTO合同 |
| OBS-W02 | 周期中到达的新document只能进入下一周期，当前合同不可扩展 |
| OBS-W03 | 任一周期缺contract/hash，或一个两小时长事务，整个G12A失败 |

## 12. 生产 Gate 验收

### D11A → OP11A → G11A：只读生产对照

- worker/supervisor/parser 为 0，自启动关闭；
- `mode=ro`、`query_only=ON`，旧慢查询未执行；
- ordered IDs 与独立参考结果一致；
- `NO_INDEX`的新query满足正常10秒预算且plan无坏形状；`INDEX`可在预声明deadline内返回
  `INDEX_REQUIRED`，但必须证明缺少ADR-02冻结索引且分块oracle/有界只读查询仍100%匹配ordered
  IDs；它只开放D11M，不能记作性能PASS；
- DB/WAL/SHM/config/source 元数据未变；
- 两名 reviewer `PASS`。

### D11M → OP11M → G11M：INDEX分支迁移后性能门

- 只在G11A得到合规`INDEX_REQUIRED`且ADR-02=`INDEX`时存在；
- OP11M只执行冻结显式migrator，ordinary reader open仍zero DDL；
- G11M使用G11A同一生产只读协议重跑新query，必须满足正常10秒deadline、plan预算和100%
  ordered-ID语义；不满足即FAIL，不得进入D11J；
- ZR1002/ZR1003 tmp fixture通过显式init/upgrade准备，产品reader eager DDL调用数0。

### D11J → OP11J → G11J：protected write-intent journal

- ADR-02两分支在G11A或G11M后均先进入D11J，不能直接进入A1；
- D11J冻结exact path/ACL/version/atomicity/fsync/hash-chain/crash-reconcile/TTL与数值RPO/RTO；
- OP11J只显式初始化该对象，production catalog/source/config/registry写0、process0；
- G11J两名按DAG与OP11J执行者disjoint的reviewer验证WRITE-F01/WRITE-F02、半写/断电、ACL/reparse和ordinary mode=`rw`
  zero DDL；通过后才开放D11B-A1，并成为G10R必要输入。

### G11B-A1/A2/A3：Canary A

- 明确用户授权与停止人；
- 无无限 supervisor、无登录自启；
- 条件索引先通过D11M→OP11M→G11M；无索引走G02B-NI ADR分支且不创建假Gate；两者随后
  都必须通过D11J→OP11J→G11J；
- 每个D11B-Ax重新冻结恢复点/RPO/RTO、run ID、candidate/root IDs、operation+PK+column/
  exact-file contract、actual touched delta与disposition；
- A1/A2/A3分别执行D→OP→PAUSED/OFF→G；每个G两名非operator reviewer，不能合并；
- Canary A 默认 LLM off且对主/备provider network deny；
- source写由权限层主动拒绝，不只事后sentinel；
- 至少 3 个预期 normalize artifact 成功（A2/A3）；
- scan 不无故重复，阶段计时和 checkpoint 对账；
- 源 manifest 不变，未授权网络为零；
- 结束后 persistent pause，进程为 0；
- CAN-A1-S01、CAN-A1-S02、CAN-A1-S03、CAN-A2-S01、CAN-A2-S02、CAN-A2-S03、
  CAN-A3-S01、CAN-A3-S02、CAN-A3-S03全部通过，且各自对应的两名reviewer PASS。

### G11B-BP 与逐个 G11B-BFnn：Canary B

- 只有G11B-A3+G07E+条件G11M-L有入口；G07O分支禁止执行；
- primary与每个fallback分别有D/OP/G、一次性stage/provider-bound授权、one-shot与pause；
- CAN-BP-S01、CAN-BP-S02、CAN-BP-S03、CAN-BP-W01、CAN-B-W02，以及每个启用fallback的
  CAN-BF-S01、CAN-BF-S02、CAN-BF-S03、CAN-BF-W01、CAN-B-W02通过；每阶段 exact
  write contract冻结RPO/RTO、typed PK、columns、files、prior state和precommit/post-read；
- 未通过G11B-BFnn的fallback在release profile禁用；B授权不沿用12A/12B。

### D12A → OP12A → G12A：观察

- G10R 已通过，最终启用 hardening lanes有明确配置；
- 连续 5 个真正完整周期、总观察 ≥2 小时；
- 任何失败后窗口重置；
- 默认 LLM off + network deny；真实模式另行批准全部主/备provider、data/roots、字符、成本、
  时限和retention/jurisdiction；Canary B授权不沿用；
- OBS-S01、OBS-S02、OBS-S03、OBS-S04、OBS-S05、OBS-S06、OBS-W01、OBS-W02、OBS-W03
  及WRITE-F01、WRITE-F02、WRITE-F03、WRITE-F04全部通过；真实LLM使用12A
  专属auth hash且source freshness正确；
- 两名 reviewer `PASS`。

### G12B-PRE → D/ARM → D/RB → OP/ARM/G → D/CAS/G → D/LOGIN/G12B-POST：dormant 登录验证

- 用户单独批准；
- G12B-PRE审外部trust anchor、不可写完整release、12B exact profile/auth/value与真实registry
  conditional create/delete；
- D12B-ARM后、任何ARM state/token写之前，D12B-RB两名满足DAG rollback/startup角色与
  disjoint规则的reviewer先seal补偿合同；未PASS时OP12B-ARM不可执行。OP12B-ARM先向protected
  journal写expected registry absence/desired bytes hash/ownership nonce/generation/补偿intent，再
  写arm state并finalize，之后G12B-ARM；
  D12B-CAS与G12B-CAS分别由满足各自DAG exact角色/基数/disjoint规则的两名reviewer；ARM token在CAS消费，之后仅有
  默认24h/硬72h dormant lease；
  CAS后必须ARMED_ON_PRELOGIN/ON，无LOGIN_COMMITTED时任何登录child/egress/DB写=0；
- D12B-LOGIN两名reviewer后，用户再次批准exact注销且确认已保存工作；
- OP12B-LOGIN后trust/release/auth hash、单实例、首周期、pause、无storm/未授权egress；
- 从OP12B-ARM起的ARM/CAS/post-review/login失败、crash partial、取消或lease到期只允许
  OP12B-RB→G12B-RB；按journal+ownership nonce reconcile，exact current bytes才删除；CAS遇到
  任意同名既有值（即使同bytes）或第三方替换都不接管，并进入PAUSED/REGISTRY_CONFLICT。
  Gate/launcher不写registry，G12B-RB继承OP exact终态；
- START-S01、START-S02、START-S03、START-S04、START-S05、START-S06、START-S07、
  START-S08、START-S09、START-S10全部通过；12B profile等于G12A profile；
- G12B-POST唯一成功状态为LOGIN_VALIDATED_PAUSED/ON、process0，不得宣称RECOVERED。

### D12C → 用户授权冻结intent → G12C-PRE → OP12C → G12C：最终启用下次登录

- 用户看到G12B-POST摘要后先由D12C两名满足DAG规则的reviewer seal final/rollback contract与
  唯一proposed action/intent hash；随后用户单独批准`G12C_FINAL_AUTOSTART_ACTIVATION`并绑定
  exact intent hash/action ID，未批准为安全等待。G12C-PRE恰好三名按DAG与D12C disjoint、不同角色reviewer核对exact
  Run/release/auth/generation/circuit/ledger head并唯一开放OP12C；
- OP12C只CAS为ENABLED_IDLE/ON，generation+1、process0；不得启动当前session或调用reset/
  resume/arm，不写registry/config/DB/source，不改LLM profile；token/control写前journal intent、
  写后finalize，crash只由OP12C-RB reconcile；
- ACT-S01、ACT-S02、ACT-S03、ACT-S04、ACT-S05、ACT-S06、ACT-S07、ACT-S08、ACT-S09、
  ACT-S10全部通过；
- G12C由恰好三名满足DAG exact角色/基数/disjoint规则的reviewer全PASS后，物理state仍为ENABLED_IDLE/ON，只记
  `lifecycle_outcome=RECOVERED`。失败走OP12C-RB→G12C-RB并由两名按DAG与OP执行者disjoint的
  reviewer核对exact OP终态；第三方Run冲突时必须PAUSED/REGISTRY_CONFLICT。G12C后每个cycle
  必须密封runtime contract、重验auth/cap/journal/write/egress；若需当前
  session运行，另建新D/OP/G，不属于本计划的隐含步骤。

## 13. 每个 WP 的 Red→Design→Implementation→Gate 映射

| WP | Test-only commit 先红 | Design | Implementation后转绿 | Exit |
|---|---|---|---|---|
| 00L | T00L: GL-S01、GL-S02、GL-S03、GL-S04、GL-S05、GL-S06、GL-F01、GL-F02、GL-F03、GL-F04、GL-F05、GL-F06、GL-F07、GL-F08、GL-F09、GL-F10、GL-F11、GL-F12、TESTID-S01、G10-PROMPT-S01 | D00L | I00L deterministic validator | G00L（2人） |
| 01 | T01: `test_id_registry.v4.json` 中 `introduced_at=T01` 且condition成立的全部 concrete Q IDs | D01 | 无I01；旧产品红灯仍在 | G01 |
| 02A | T02A: Q-S02、Q-S03、Q-S11、Q-S12、Q-S14、Q-S15、Q-S16、Q-S17、Q-P01、Q-P02、Q-P03、Q-P04、Q-P05、Q-P06（exact模式另Q-P07） | D02A | I02A含必要production seam；MUT-Q02A-01、MUT-Q02A-02、MUT-Q02A-03、MUT-Q02A-04、MUT-Q02A-05均被列明Q测试杀死 | G02A |
| 02B ADR | 无测试/代码改动；只读G02A evidence | G02B-ADR两人冻结ADR-02 | 无 | 只有选中分支T节点eligible |
| 02B-NI | T02B-NI: M-COM-S01、M-COM-S02、M-COM-S03、M-COM-S04、M-COM-S05、M-COM-S06、M-COM-F01、M-COM-F02、M-NI-S01、M-NI-S02、M-NI-P01 | D02B-NI | I02B-NI verify-only/no index | G02B-NI |
| 02B-IDX | T02B-IDX: M-COM-S01、M-COM-S02、M-COM-S03、M-COM-S04、M-COM-S05、M-COM-S06、M-COM-F01、M-COM-F02、M-IDX-S01、M-IDX-S02、M-IDX-S03、M-IDX-F01、M-IDX-F02、M-IDX-F03、M-IDX-P01、M-IDX-P02、M-IDX-M01 | D02B-IDX | I02B-IDX explicit migrator | G02B-IDX |
| 03 | T03: C-S01、C-S02、C-S03、C-S04、C-S05、C-S06、C-S07、C-S08、C-S09、C-S10、C-S11、C-S12、C-S13、C-S14 | D03 | I03 | G03 |
| 04 | T04: O-S01、O-S02、O-S03、O-S04、O-S05、O-S06、O-S07、O-S08、O-S09、O-S10、O-S11 | D04 | I04 | G04 |
| 05 | T05: S-S01、S-S02、S-S03、S-S04、S-S05、S-S06、S-S07、S-S08、S-S09、S-S10、S-S11、S-S12、S-S13、S-S14、S-S15、S-S16、S-S17、S-S18、RST-S01、RST-S02、RST-S03、RST-S04、RST-S05、RST-S06、RST-S07、RST-S08、RST-S09的tmp实现 | D05 | I05 | G05 |
| 06 | T06: SC-S01、SC-S02、SC-S03、SC-S04、SC-S05、SC-S06、SC-S07、SC-S08、SC-S09、SC-S10、SC-S11、SC-S12、SC-S13、SC-P01、SC-P02、SC-P03、SC-P04 | D06 | I06 | G06 |
| 06P | T06P: P-FMT00-ROUTE；每个候选enabled route实例化S/M或DIS/LIMIT/ERR/NA/PAUSE模板ID | D06P | I06P或逐route fail-closed | G06P |
| 07E | T07E: L-S01、L-S02、L-S03、L-S04、L-S05、L-S06、L-S07、L-S08、L-S09、L-S10、L-S11、L-S12、L-S13、L-S14、L-S15、L-S16、L-S17、L-S18、L-S19、L-S20、L-S21 | D07E | I07E | G07E |
| 07O | T07O: L-S09、L-S15、L-S17、PX-S07 | D07O | I07O | G07O（另需G09P） |
| 08 | T08: R-S01、R-S02、R-S03、R-S04、R-S05、R-S06、R-S07、R-S08、R-S10、R-S11、R-S12、R-S14、EV-S01、EV-S02、EV-S03 | D08 | I08 | G08 |
| 09P | T09P: `test_id_registry.v4.json` 中 `introduced_at=T09P` 且condition成立的全部 concrete IDs | D09P | I09P | G09P |
| 09 | T09: E2E-S01、E2E-F01、E2E-F02、E2E-M01 | D09 | I09仅集成修复 | G09 |

生产节点没有implementation commit，但必须使用独立pre-review→OP→post-review：
D11A/OP11A/G11A、条件D11M/OP11M/G11M、D11J/OP11J/G11J、每个A1/A2/A3与BP/BFnn、
D12A/OP12A/G12A、G12B-PRE→D12B-ARM→D12B-RB→OP12B-ARM/G→D12B-CAS/OP/G→D12B-LOGIN/OP/
G12B-POST及OP12B-RB/G12B-RB、D12C/G12C-PRE/OP12C/G12C及OP12C-RB/G12C-RB，
以及每次唯一D05Rnn/OP05Rnn/G05Rnn。每个D/G按DAG重新派独立agent，禁止合并补签。

D后任何test/fixture assertion变化自动使D失效。G10C/G10R后production wrapper/contract/trust/
authorization变化会使G09P/G09和相应审计/生产节点失效。

## 14. Flaky 与失败处理

- 第一次失败：保存脱敏日志；获批raw内容只进approved sink并记录opaque ID/HMAC；同时保存
  seed、环境和tmp artifact摘要，先判断产品缺陷还是测试问题。
- 第二次同类失败：固定 seed/clock，缩小最小复现，禁止直接 rerun 到绿。
- 第三次仍无新证据：停止，写入 `progress.md` 的 Errors Encountered，按三次失败协议更换
  方法或请求明确决策。
- 性能偶发失败不得通过无限重跑、提高阈值或删除 P95 样本解决。
- reviewer 发现测试只验证 mock 而未穿过实际边界时，按 P1 处理。

## 15. 每个 Gate 的测试签字格式

```text
Gate ID:
Git commit / worktree:
Fixture seed + schema hash:
Commands and exit codes:
Fail-before evidence:
Pass-after evidence:
Mutation/fault evidence:
Performance raw data + method:
Production/config/source sentinel:
Open findings by priority:
Independent reviewer report(s):
Decision: PASS | PASS_WITH_NONBLOCKING_FINDINGS | FAIL
```
