# Source Catalog Worker 恢复计划 — 研究发现

> 本文件保存支撑实施计划的稳定事实、证据和待验证假设。  
> 来源：`docs/worker-investigation-2026-08-20.md`、2026-08-20 现场只读调查、2026-08-22
> 代码路由核验，以及 `plan_review_findings.md` 保存的 v1–v3 独立审查反例。代码基线为
> `26a6b22f80ae964892d3f3f44fab364e65276583`；任何后续实施会话开始时必须重新核对漂移。
> 本文件在同一 plan revision 内保持冻结；实施中新事实写 evidence/`gate_ledger.jsonl` 与
> `progress.md`，只有需要改变规范时才在下一 plan revision 更新本文件。

## 发现 1：主要根因是 normalize queue SQL 查询计划退化

- 日期：2026-08-12 起；2026-08-20 现场确认。
- 代码：`src/company_wiki/source_catalog/normalizer.py:1560-1587`。
- 变化提交：`0ee0d09dfcbc8d5bbac4f17666c09df910d17558`。
- 生产规模：23,530 documents、46,606 locations、25,046 active locations、16,989 active original_primary。
- planner：`SCAN d` + correlated subquery + `idx_locations_status` + temp B-tree sort。
- 缺失：`sqlite_stat1`；缺少 `(document_id, role, location_status[,root_id])` 匹配索引。
- 现场：真实 worker 902 秒未返回；非相关等价查询 0.231 秒返回相同前三行。
- 影响：单核长期满载，实际文档吞吐为零。

## 发现 2：parser 尚未启动

- runtime 一直是 `normalizing / selecting next document`。
- `parser_pid=null`，`current_path=null`。
- 最后成功周期中三个 HTML artifact 在约一秒内生成。
- 结论：不能把当前故障归咎于 parser；SQL 修复后仍需按发现26列出的每条实际
  route/profile（而非只以 PDF/Office 代称）分别 profile。

## 发现 3：控制面将慢查询放大成永久循环

- watchdog 900 秒；SQL 内无 heartbeat。
- scan checkpoint 只在完整周期末落盘。
- uptime >= 900 秒即重置 consecutive failures。
- 每轮重复支付 120 秒启动延迟。
- 结果：启动 → 重扫 → SQL 900 秒 → kill → 5 秒重启。

## 发现 4：重复扫描是第二大浪费

- 2026-08-20 暂停前完成 44 次 scan，累计 2.54 小时。
- 当日 scan 平均 208.1 秒，范围 148–588 秒。
- 一次现场完整 scan 为 427 秒。
- 46,600 files seen，46,599 reused，0 hashed。
- 主要成本是 company_raw 枚举、sidecar/metadata、文件观察和 DB 状态维护。

## 发现 5：现场资源瓶颈是 CPU，不是内存或物理磁盘

- 5 秒 CPU 样本：单核 96.8%。
- 工作集约 90.9 MiB，私有内存约 81.9 MiB。
- 进程逻辑读取约 1.61 GiB/5 秒，写入 0。
- 同期物理盘读约 0.1–1.3 MiB/s，disk time < 3%。
- 解释：SQLite 在 OS cache 中反复遍历，而非 SSD 饱和。

## 发现 6：SQL 修复后 LLM 会成为下一瓶颈

- 最后一次 LLM summary 约 42 秒/文档。
- normalize batch=3，LLM batch=1。
- normalize eligible 约 12,202；LLM immediate pending 122；permanent failure 650。
- 当前 `LLMClient` 非线程安全，不能直接多线程。

## 发现 7：worker 对源目录主要是读取，但存在外部数据发送

- 自动循环没有发现删除、移动或覆盖源文件的路径。
- 主要写 `.source_catalog`、派生物、索引和 `llm_cost_log.csv`。
- LLM summary 可发送最多约 120,000 字符规范化原文给外部 provider。
- 必须把数据授权和 provider 边界作为恢复 Gate。

## 发现 8：容量与维护风险独立存在

- 主库约 46.22 GiB。
- remediation 备份约 45.93 GiB。
- `.source_catalog` 总计约 92.16 GiB。
- C 盘余量约 98.9 GiB。
- evidence_spans rowid 高水位 27,178,737。
- retention prune 存在 `project_root`/`_project_root` 属性错误。
- 约 908 个 worker stdout/stderr 文件；总体积小但文件数持续增长。

## 发现 9：电池 gating 顺序不符合直觉

- `allow_processing_on_battery=false`。
- 但 power eligibility 在 scan 之后判断。
- 所以电池模式仍可能完成一次全量扫描。

## 发现 10：当前隔离状态

- 2026-08-20 已执行持久 pause。
- worker 和 supervisor 已停止。
- launcher 原因 `persistent_pause`。
- HKCU Run 的 `CompanyWikiSourceCatalog` 已删除。
- 没有对应计划任务或服务。
- stale operation lock 指向已退出 PID；未盲目删除。

## 发现 11：实施触点与既有测试基础已经明确

- 根因与生命周期关键触点集中在：
  `normalizer.py`（队列选择）、`worker.py`（scan due、阶段与周期状态）、
  `store.py`（schema/index/transaction）、`scanner.py`（枚举与入库）、
  `control.py`（runtime heartbeat、pause/stop）和
  `scripts/source_catalog_worker.ps1`（watchdog、restart reset/backoff）。
- 登录链还包含 `scripts/source_catalog_worker_at_logon.vbs`、同名 PowerShell 启动脚本和
  `scripts/source_catalog_control.ps1`；计划不得另造第二套启动机制。
- 已存在 worker、control、operation lock、long-running observable、schema migration、
  SQL pushdown、scanner、parser liveness、background reliability 等 contract tests。
- 后续实施必须先扩展最贴近现有契约的测试文件；只有现有组织确实无法表达目标测试时
  才新建测试模块，避免弱模型平行创造重复框架。

## 发现 12：现有控制入口足以支撑受控恢复，不应另造启动链

- `scripts/source_catalog_control.ps1` 的公开 action 为
  `menu/status/start/pause/resume/stop/duplicates`，并显式接收 `PythonExe` 与 `ProjectRoot`。
- 原始报告已记录 `status` 与 `resume` 的精确调用形式，以及原 HKCU Run 值；恢复流程应
  复用这些入口。
- control 脚本会把 diagnostics 写入生产 `.source_catalog/control_center.log`，因此即使
  `-Action status` 也不能在“绝对零写”的 Gate 中未经核实地当作纯只读命令；执行前后
  必须把预期日志写入与 DB/config/source 零写区分记录。
- 未来 canary 不应新增计划任务、服务或另一套 supervisor；最终仍使用唯一 HKCU Run名称，
  但原值指向live worktree，只作历史参考。新值必须指向pinned release或由launcher在启动前
  校验受审fingerprint，并经用户批准。v2 lifecycle复审进一步证明“被验证launcher验证自身”
  仍不构成信任锚；首段非OS代码、verifier与release必须分离且对worker identity不可写。

## 发现 13：8 月 12 日还出现过独立的重复实例/锁噪声

- 8 月 12 日白天某个 supervisor 会话反复启动短命 child，并遇到另一实例持锁；当时另一个
  worker 仍能完成周期。
- 这不是晚间以后持续卡在 queue SQL 的主因，但证明启动链需要覆盖重复 launcher、resume
  race、单实例和 lock owner identity，不能只验证“正常启动一次”。
- WP-05、WP-09、G11B-A1、G11B-A2、G11B-A3、G12B-PRE、G12B-ARM、G12B-CAS、
  D12B-LOGIN/G12B-POST/12B-RB 与 D12C/G12C-PRE/G12C/12C-RB 已把这些场景列入测试与审查。

## 发现 14：队列资格与 parser 的 primary source 合同存在潜在裂缝

- v1 SQL reviewer 核对 2026-08-22 基线：queue eligibility 只检查 document/role/status；实际
  parser 还要求 `location.source_id == document.primary_source_id`。
- schema 的独立外键不能自动保证这两个 source ID 相等。
- source-mismatch 高优先级文档可能反复占据 LIMIT 后被 parser 拒绝，并饿死有效文档。
- v2 已把 `(document_id, primary_source_id)` parseable-primary 与 force matrix列为 SQL oracle。

## 发现 15：生产常见 scan 结果是 `completed_with_errors`

- 报告中的 44 次重复 scan 均可能包含已知 quarantine/空文件错误；scanner 可写
  `completed_with_errors`。
- 仅把字面 `completed` 当 checkpoint 会保留重复全扫；无条件接受
  `completed_with_errors` 又会掩盖 root offline/partial enumeration。
- v2 要求 per-root outcome/error taxonomy 与 root/config/scanner fingerprint。

## 发现 16：LLM queue 与 cache 需要先补 correctness contract

- v1 reviewer 核对基线：LLM selection 可能连接多条 normalized artifacts，且旧 summary 的
  generator/version/status 抑制条件不够精确。
- 单纯按 normalized body hash复用会把不同 title/source/kind/locator 的 source-bound结果错绑。
- v2 要求 current completed input、dedupe-before-LIMIT、summary version/status和 exact canonical
  request payload cache + per-document artifact rebinding。
- v2 SQL复审核对基线后发现更深一层：current artifact 还未要求
  `artifact.source_id/source_sha256`等于logical document当前primary source/hash。S1→S2时，旧
  normalized可能抑制重生，LLM也可能把S1正文绑定成S2 summary；v3把source rotation列为
  Q-S17/L-S18与G09集成mutant。

## 发现 17：Store 普通打开路径目前会执行 eager DDL/migration

- `CatalogStore.__init__` 在基线中执行 `_DDL` 与 additive migration。
- 因此把大索引直接追加到 `_DDL` 会在普通 worker/login启动时隐式构建，违反空间与恢复 Gate。
- v4把该要求收紧为共享 schema lifecycle：ordinary open 必须使用不会创建缺失 DB 的只读
  验证语义（例如 SQLite URI `mode=rw`），missing/old schema 分别返回稳定的 init/upgrade-required
  错误且零 DDL；只有显式 operator `schema init/upgrade` 可以建库或迁移。NI/IDX 在
  `G02B-ADR` 后分别拥有 test-only/design/implementation/review 链；生产大索引仍另需
  `D11M→OP11M→G11M`。

## 发现 18：控制状态与 Windows containment 还有既有不变量

- v1 lifecycle reviewer 核对基线：Python/PowerShell 对缺失或损坏 control状态可能默认 enabled；
  这与受管生产 fail-closed目标冲突。
- supervisor已有 Windows Job Object kill-on-close 机制；任何状态机重构必须保留 create/assign/
  kill-on-close，assignment failure不能降级裸启动。
- runtime envelope 还需绑定 session/attempt/token/PID creation/code fingerprint/sequence，避免旧
  heartbeat串台。

## 发现 19：计划 v1 的独立审查未通过

- 三名 reviewer 均核验 v1 hashes并独立给出 `FAIL`。
- 共同 P0：12A普通 resume可能绕过真实LLM授权。
- 合并 findings 与处置记录见 `plan_review_findings.md`；在 v2 复审前没有任何项算关闭。

## 发现 20：计划 v2 的三路复审仍未通过

- 三名原reviewer均逐项核验v2的12个核心文件及来源报告hash，审查期间无revision drift。
- 共同阻断面包括：唯一DAG缺02B/G07O/A/B合法节点、12B长期LLM授权不完整、source
  freshness、circuit reset/resume歧义、canary写边界、release trust anchor和测试ID/统计合同。
- v3修订不自行关闭这些finding；只有冻结v3后原领域独立reviewer明确关闭才算通过。
- 上述关闭条件后来没有满足；v3 的三路最终结局均为 FAIL，详见发现24。此处保留 v2
  时点的历史措辞，不代表任何 finding 已关闭。

## 发现 21：provider crash 后不能无条件承诺 exactly-once billing

- provider可能已经接收并计费，但进程在response/cache/artifact落盘前崩溃。
- 若provider不支持可验证idempotency key或result lookup，本地代码无法证明安全自动重试，
  “本地成本计数幂等”也不能推出“外部绝不重复计费”。
- v3采用durable PREPARED/IN_FLIGHT/OUTCOME_UNKNOWN ledger；unknown不自动重发，最大预计费用
  继续占cap，需要人工reconcile或新授权。

## 发现 22：canary表/目录allowlist不足以约束同一对象内的错误写

- 仅限制table/path和净row-count，无法发现允许表内wrong-ID UPDATE、无WHERE UPDATE、
  DELETE+INSERT净零变化，或允许目录内覆盖历史派生文件。
- v3要求operation+exact PK+column/exact file contract、实际touched rows和pre-commit changeset；
  SQLite authorizer只作第一层，恢复点不能替代写前拒绝。

## 发现 23：scanner历史生产耗时不能作新拓扑基准的正式分母

- 报告中的427秒现场样本对定位浪费有价值，但没有与候选实现共用完全相同的topology、
  instrumentation、环境和重复样本合同。
- v3要求同一baseline commit、同topology/environment/instrumentation hash，旧/新每场景各
  n≥10；历史值仅作外部参考。

## 发现 24：计划 v3 的三路冻结版本复审仍全部失败

- 三名原领域 reviewer 均从不可变 `plan_manifest.v3.json` 重算 13 个核心文件、来源报告及
  manifest 自身 hash，全部匹配；所以结论不是审查期间并发改动造成的误报。
- SQL/性能 reviewer 发现 02B 在 ADR 前共用 test commit、`G07E` 可提前直达生产
  request-ledger migration、SQLite progress callback 被当成精确 VM steps、parser route/稳定 ID
  不完整等问题。
- 生命周期/安全 reviewer 发现 Canary B 与 12A 缺逐 run/cycle exact write contract，registry
  CAS 到最终登录授权之间有意外重启启动窗口，生产 reset 不在正式 Gate DAG 内，且
  `G12B-POST` 与最终运行态语义冲突。
- 测试/可实施性 reviewer 用具体 JSON 反例证明 v3 ledger schema 可接受“节点 PASSED 但
  reviewer FAIL/open P1/hash 未确认”、必需 Gate 假 `NOT_SELECTED`、`BF00`；同时合法的
  READY D/G 会被拒绝。还发现 G10 共用 prompt 形成下游伪循环及稳定测试 ID 漂移。
- 完整反例与 PR-054–066 见 `plan_review_findings.md`。v3 不得实施；v4 修订者也无权自行
  将这些 finding 标为 CLOSED。

## 发现 25：SQLite progress callback 只能作为近似 work proxy

- Python `set_progress_handler(callback, n)` 表示在 SQLite VM 大约每 n 条指令调用 callback，
  不能从 `callback_count × n` 推出严格的真实 step 上下界。
- v4 要求 D01 明确二选一：`PROGRESS_PROXY_APPROX` 只作同 harness 的近似比较，或使用经审计
  binding 的 `SQLITE_STMTSTATUS_VM_STEP` 精确计数；无论哪种都要同时保留 query plan、N/2N
  scaling 与 wall-time 样本，不能只凭一个计数器宣称复杂度修复。

## 发现 26：当前 parser dispatch 比 v3 的格式模型更宽

- 2026-08-22 先用 CodeGraph 定位 `_normalize_source`，再只读核对
  `src/company_wiki/source_catalog/normalizer.py:1355-1387` 与 MHT 分支
  `normalizer.py:1045-1059`；未修改代码。
- 当前路由至少包括：plain text `.txt/.md/.csv`；HTML `.html/.htm`；MHT HTML part 与
  text fallback；PDF 的 Docling artifact 路径与 PyMuPDF/page-aware fallback；DOCX；legacy DOC
  via antiword；XLSX；legacy XLS；PPTX；JSON；XML/XSD；以及 unsupported suffix。
- 因为 parser family 的依赖、子进程、内存和超时完全不同，不能再用一个“HTML/text”或
  “Office”样本代表全部。v4 的 `test_id_registry.v4.json` 为每条实际 route 定义 S/M/oversize/
  corrupt/encrypted/pause 适用规则；任何缺样本 route 必须从 release profile 禁用而不是默许。

## 发现 27：prose Gate 约定不足以抵御伪记录与弱模型误派工

- v3 的单记录 JSON Schema 无法单独证明整条 DAG 的前驱、互斥分支、review payload 真值、
  external expected-head、BF 连续性、授权时效与生产状态转换。
- v4 因此先安排独立 bootstrap `T00L→D00L→I00L→G00L`，实现确定性、fail-closed 的 ledger
  semantic validator；正式 `D00` ledger 在 G00L 前不得创建。后续预冻结反例审查证明“仅标准库
  执行 Draft 2020-12 JSON Schema”不可实现，因此修正为独立 venv、解释器和 `jsonschema`/
  `referencing` 完整依赖闭包逐 hash 冻结；禁止 `-S`，保留 `-I` 并在入口核对 `sys.path` 与模块来源。
- 活动节点只能由 validator 根据 `gate_dag.v4.json` 计算。ledger schema 明确拒绝 authored
  next edge；reviewer verdict 必须来自经 hash 核验且符合 `review_result.schema.json` 的机器
  payload，并由 reviewer 另发 detached read-back confirmation；不能从 Markdown 摘要、主 agent
  自填布尔值或 operator 手抄。
- 每个 OP 还必须唯一匹配冻结 `operation_contracts.v4.json`，并绑定通过 schema 的动态 operation
  contract 与 stage-bound authorization manifest；否则 validator 无法区分合法读操作、真实写入、
  N/A 授权和预授权补偿。

## 发现 28：生产写入与登录恢复需要按时间窗口建模

- Canary B 每个 BP/BF 与 12A 每个 cycle 都可能在“允许表/目录”内写错 PK、column、历史文件，
  或在 provider crash 后不安全重发。v4 要求 candidate 集合先只读物化、合同密封、DB/files
  precommit 校验、bounded transaction、post-read 重算；合同不得在周期内扩展。
- 首个生产写 canary 前必须另走 `D11J→OP11J→G11J` 初始化 protected write-intent journal；
  普通 worker/canary 打开 journal 或 catalog DB 均不得 lazy DDL。
- `OP12B-CAS` 后只能进入 dormant `ARMED_ON_PRELOGIN/ON`：没有短 TTL、single-use、绑定
  generation/release/auth/user 的 `LOGIN_COMMITTED` 时，任何登录都必须 child/network/DB/source
  零活动。登录验证一个冻结周期后自动 pause，`G12B-POST` 只确认
  `LOGIN_VALIDATED_PAUSED/ON`。
- CAS 后任何失败或 dormant lease 到期都只能走预审过的 `OP12B-RB→G12B-RB`；Gate 只读，
  不得自己删除 Run。第三方值冲突时保持并进入 `PAUSED/REGISTRY_CONFLICT`。
- 最终激活必须另走 `D12C→G12C-PRE→OP12C→G12C`。OP12C 只解除下一次正常登录所需
  persistent pause，当前 session 保持 process0；G12C 只写 lifecycle outcome，不改变物理状态。
  OP/G失败走`OP12C-RB→G12C-RB`。若要当前 session 运行，必须另建新的 D/OP/G。
- 每次 production circuit reset 使用唯一 `D05Rnn→OP05Rnn→G05Rnn`，只清 active latch/budget、
  保留历史并保持 PAUSED；reset 本身不产生 resume/arm/registry/LLM 权限。

## 发现 29：v4 草稿的动态操作 schema 曾允许“结构合法但语义危险”的合同

- 预冻结测试/schema reviewer 构造出可通过旧 schema 的反例：INTEGER 用 string、NULL 带值、
  BLOB/REAL 无 canonical encoding；复合主键列数与 tuple arity 不同；声明 EXACT hash 却把 prior
  hash 写 null；path supplement 开启但 function hash 为空；invariant 为空、max touched=999。
- 更严重的是 `candidate_document_ids` 与 `source_bindings` 两个平行数组可以把 document A 错绑到
  source B。v4 修订改成不可拆分的 `candidate_sources[{document_id, source_id, source_sha256,
  opaque_root_id}]`，DB/file write 只能引用这里的 document ID；A1 的 root-only 变体必须显式声明。
- 能由 JSON Schema 表达的 type/conditional 约束直接封闭；PK arity、case-fold 唯一性、catalog cap
  等跨字段关系列入 `x-semantic-rules` 和 validator typed-mutation vectors，不能只写在 prose。

## 发现 30：Windows Run value 没有可假定的原生 value-level CAS

- “先读不存在，再写 REG_SZ”以及仅靠进程内 mutex 都不能证明两个进程或第三方工具竞争时的
  create-if-absent 线性化；existing-same-bytes 也可能属于第三方，不能算本次创建成功。
- 每个 registry operation 必须冻结 hive、current-user SID、32/64-bit view、key/value/name/type、
  prior absence/value hash、desired exact bytes/hash/length、实现/证明 hash、ownership/run nonce、
  touched 上限与 post-read。只有 exact value + ownership nonce 可删除；第三方替换一律保留并进入
  `PAUSED/REGISTRY_CONFLICT`。
- 实施时若不能在 disposable key 上通过两进程竞争、same-bytes 已存在、第三方替换和 crash partial
  测试，`G12B-PRE` 必须 BLOCKED；本计划不预先声称某个未证明 primitive 已满足 CAS。

## 发现 31：authorization、intent、contract 和 journal 必须形成无循环的 hash 链

- 旧草稿能把 `CIRCUIT_RESET` 授权误用于 OP12C，或让 compensation 缺 parent authorization；也
  没有把用户批准绑定到 exact Run bytes、action、generation 与 contract digest。
- v4 以 `operation_intent_manifest` 打破循环：D Gate 先冻结 canonical action/intent；用户授权只
  批准其 hash；dynamic contract 再同时绑定 intent 和 authorization。compensation 绑定 parent
  auth id/hash；严格 UTC 时间还需满足 `issued <= checked <= now < expires`，scope/provider 去重且
  allowed/excluded 不相交。
- DB、文件、registry、control 跨资源不可能依靠一句“原子”保证。OP11J 初始化的 protected
  journal 必须先写 intent/head-before，再执行受界副作用并 finalize/head-after；crash 后先 reconcile
  半提交记录。每个 mutating OP/cycle/reset 都绑定同一 journal manifest/head。

## 发现 32：Markdown evidence 与自由文本 vector 不能作为机器信任根

- ledger 曾把 `manifest.md` 当 evidence manifest，但 E014 又要求精确 node/commit/run/ACL/TTL；
  Markdown 无法可靠执行这些约束。v4 改为 schema 验证的 `manifest.json` 加人类 `report.md`，分别
  hash；artifact 逐项记录 repo-relative/approved-sink、SHA/HMAC、size/type/sensitivity、ACL、
  encryption、reparse、created/expires，且 secret 必须为 false。
- validator vectors 需要 canonical base fixture、typed mutation、validation stage、pointer 和唯一
  primary reason rule；否则一个“复制 executor”mutation 可能实际只复制 null，并错误测试 E002。
  T00L 产生 fixture 候选，D00L 冻结 exact hash，I00L 实现，G00L 每人重算并另造未预告反例。

## 发现 33：12B/12C 的补偿和最终批准顺序必须按实际写入窗口排列

- 旧 v4 DAG 到 `G12B-ARM` 后才审 D12B-RB，导致 ARM token 已写但 compensation 尚未通过；ARM
  失败、G12B-ARM 失败和 D12B-CAS 失败也没有一致的 failure edge。
- 修订顺序为 `D12B-ARM→D12B-RB→OP12B-ARM→G12B-ARM→D12B-CAS`；从 ARM 写入起每个失败点
  均可达统一 `OP12B-RB→G12B-RB`，rollback Gate 继承 OP 的 exact OFF/CONFLICT terminal state。
- 最终激活必须先由 D12C 冻结 exact proposed intent，再由用户批准该 hash，G12C-PRE 重验；
  用户尚未批准时保持 `SAFE_PAUSED_WAITING_USER`，不能先取得泛化批准再补动作细节。

## 发现 34：INDEX 分支若在 G11A 强制同一 10 秒门会形成迁移死锁

- INDEX 决策的目的可能正是需要生产索引；若 G11A 迁移前必须满足索引后的 10 秒阈值，而 D11M
  又依赖 G11A，就没有合法前进路径。
- NO_INDEX 在 G11A 必须满足正常预算；INDEX 在 G11A 只允许 bounded read-only `INDEX_REQUIRED`
  诊断，同时以 chunked oracle 证明语义并以 query plan 证明索引必要。`G11M` 后必须恢复正常
  10 秒门，仍超时就阻断 G10R。

## 发现 35：G12C 不是长期 worker cycle 的永久授权

- 旧草稿只在 ordinary autostart transition 重验少量全局项，没有规定第二次及之后 cycle 的 exact
  candidate/write/egress、journal、授权过期撤销和 daily/monthly durable cap。
- v4 静态 catalog 增加 `runtime_cycle_policy`：每 cycle 在任何 DB/file/network 副作用前封存新的
  intent + operation contract，绑定 process/control generation、release/config/routing/data、source
  identity、DB/file/egress、journal head 与 budget generations；失败 circuit+pause、process=0，
  preflight 失败不得写 registry/config/source/catalog/normalized output。

## 发现 36：2026-08-31 的新增 ZR contract tests 改变了未来 reader-first 迁移的基线

- 调查 HEAD 之后新增 `tests/contract/test_zr1002_reader_first.py` 与
  `tests/contract/test_zr1003_shadow_assertions.py`；目标 worker/store 文件本身未漂移。
- 这两项当前利用 missing DB 触发 `CatalogStore` eager init。未来把 ordinary reader 改成 verify-only
  时，测试 fixture 必须先显式 init/upgrade tmp DB，再以 reader open；不得为了保住旧 fixture 而
  恢复产品 eager DDL。Phase 0 先记录当前行为，T02B-NI/IDX 在 test-only commit 中迁移 fixture，
  映射到 `M-COM-S05`/`M-COM-S06` 并在两分支及 G10C 复验。

## 发现 37：长期 autostart 授权不能伪装成“预先绑定未来每轮 exact intent”

- 有限 D→OP 操作可以先冻结 exact intent，再取得绑定该 hash 的用户授权；但最终启用时，未来
  每轮的候选文档、source hash、DB/file effects、provider 消耗和 budget generation 尚不存在。
  因此旧语义 `AUTH_ACTION_AND_INTENT_HASH_MATCH` 对长期 worker 不是严格安全，而是不可实现：
  实现者最终只能绕过检查、重复请求人工批准，或虚构未来 exact hash。
- v4 草稿开始显式拆分 `EXACT_INTENT` 与 `RUNTIME_TEMPLATE_SPECIALIZATION`。后者只批准
  `OP-RUNTIME-CYCLE` 的冻结模板、允许根/字段/provider/destination、per-cycle maxima、四个
  durable budget ID、release/config/routing/data-root/control/circuit 代际和失效触发器；每轮仍须
  在任何副作用前生成 fresh exact intent，并由 cycle contract 绑定其 canonical hash。
- “严格特化”只允许收窄：ROOT_ONLY 必须在处理或外发前替换成 exact DOCUMENT tuple，单轮上限
  不得超过模板/provider scope，daily/monthly 可用量只会进一步减少授权。release、配置、路由、
  data root、control/circuit generation、模板 hash、授权 expiry/revocation 任一漂移都必须阻断并
  重新授权，不能现场补丁式扩权。
- 暂停点只完成了 `authorization_manifest.schema.json` 的首轮结构修订并通过 JSON 语法解析；
  `operation_contract.schema.json` 第 566 条 exact-intent 语义、静态 catalog 的
  `AUTH_ACTION_AND_INTENT_HASH_MATCH`、durable budget reservation 结构、相关负向 vector 与 prose
  尚未同步。因此当前 v4 仍是**内部不一致草稿，不可冻结、不可实施**。

## 发现 38：并行线程的基线继续前进，暂停时已不止 ZR1002/ZR1003

- 2026-08-31 暂停前复核到当前 HEAD
  `3713c9beaf7474c3746b84aae7215084179db743`；相对调查基线除 ZR1002/ZR1003 外，又出现
  `tests/contract/test_zr1005_artifact_backfill.py`、`tests/contract/test_zr1006_broker_cohort.py`
  和 `TERMINAL_NOTICE.json`。这些均属于其他线程/提交，本任务没有修改或接管。
- 下次续接必须重新计算 `baseline..HEAD`，逐项判断是否触及 worker/store/scanner/control、计划的
  fixture 或验收语义；不得沿用本次“目标实现未漂移”的旧结论。任何新基线都只记录在本隔离
  目录，不能修改或回滚并行线程文件。

## 发现 39：跨会话重读暴露出 prose 与新版机器合同的两处明确漂移

- `task_plan.md` Phase 00L 仍要求 I00L 实现 “stdlib-only deterministic validator”，但当前
  `ledger_validator_contract.md` 已选择隔离模式下的 pinned interpreter + frozen venv/dependency
  manifest；强行使用 `-I -S` 会同时屏蔽已冻结的 JSON Schema validator 依赖。活动 prose 必须
  改成与 `validator_release_manifest.schema.json` 相同的 hermetic runtime，不能让弱模型二选一。
- Phase 0 和 Phase 2 仍只显式纳入 ZR1002/ZR1003；当前基线还包含 ZR1005 artifact backfill
  与 ZR1006 broker cohort。续接时须先阅读这两项测试的实际合同，再决定它们映射到既有
  M-COM/ZR test IDs 还是增加稳定 ID；不得仅在 progress 中提到而遗漏实施 checklist。
- 这两项在 prose、test registry、traceability 与 checker 全部同步并通过前，v4 继续保持
  `NOT_IMPLEMENTABLE`。

## 发现 40：2026-09-01 漂移未继续扩大，但受限系统查询不能证明“无进程/任务/服务”

- 当前 HEAD 仍为 `3713c9beaf7474c3746b84aae7215084179db743`；相对调查基线仍恰好是
  `TERMINAL_NOTICE.json` 与 ZR1002/ZR1003/ZR1005/ZR1006 五个新增文件，没有新增
  worker/normalizer/store/scanner/control/supervisor 实现差异。
- `.source_catalog/worker_control.json` 的 `desired_state` 仍为 `paused`；HKCU Run 的
  `CompanyWikiSourceCatalog` 仍为 absent。
- 当前受限 shell 对 `Win32_Process`、Scheduled Tasks 和 Win32 Services 返回“拒绝访问”。
  PowerShell 随后把未赋值 `$targets` 显示成 `NONE`，但该值不具证据资格；必须以获准的只读
  查询重新核验后，才能声称目标进程/任务/服务为零。
- 随后使用获准的只读系统查询重新执行三项检查，均返回 `NONE`，且没有调用停止/删除/写注册表
  命令。因此 2026-09-01 当前完整状态为：control `paused`、目标进程 0、Run absent、匹配计划
  任务 0、匹配服务 0。该结论只代表此次观察时点，未来实施前仍须重验。

## 发现 41：5246 项一致性 PASS 仍会漏掉已知的跨文件授权矛盾

- 2026-09-01 原样运行 `plan_consistency_check.py` 返回 `PASS: 5246 checks`；但同一字节集仍有
  三个已确认冲突：static catalog 要求 `AUTH_ACTION_AND_INTENT_HASH_MATCH`，dynamic contract
  宣称所有授权都绑定 exact intent，`task_plan.md` 仍要求 stdlib-only validator。
- 因此该检查器当前只证明已有形状/引用规则通过，不能证明活动授权模型或 hermetic runtime
  语义一致。冻结前必须增加明确的 negative assertions：禁止旧 exact-cycle token、禁止活动
  stdlib-only/`-I -S`措辞，并要求 runtime operation ID、template mode、budget IDs/reservations、
  refresh triggers 在 auth/intent/contract/catalog/prose 中完全对齐。
- 在这些新断言能先对当前草稿报错、修订后再转绿之前，5246 PASS 不得出现在冻结证据中。

## 发现 42：新增规范文件若不进入 checker 的显式信任清单，会成为未验证孤岛

- 已新增 `operation_intent_template.schema.json`，并让 static runtime catalog 指向它；但随后
  checker 仍报告 `schemas=16`，总检查数也仍为 5246。说明 checker 不是安全地发现全部活动
  schema，而是显式/间接漏掉了新依赖。
- 冻结前 checker 必须从 catalog、各 `$ref`、README normative list 和 plan-manifest schema
  计算闭包，并要求集合完全相等：缺文件、孤儿规范、未声明额外 schema、同 `$id`、未解析外部
  ref 都要失败。仅对旧列表逐个 meta-check 不能构成完整性证据。
- 新 template schema、预算 reservation 和 exact/template 语义尚未进入 checker 之前，本次
  5246 PASS 仍为预期的假绿，不得计入测试结果。

## 发现 43：rollback 必须冻结“失败窗口→观测事实→动作→终态”的分支判别器

- DAG 从 OP12B-ARM/OP12C 的首个写入前失败也能进入 rollback；但旧 static catalog 只有从
  ARMED/ENABLED 状态回退的路径，没有 `PAUSED/OFF→PAUSED/OFF` 或
  `LOGIN_VALIDATED_PAUSED/ON→LOGIN_VALIDATED_PAUSED/ON` 幂等 no-op。
- OP12B-RB 又泛化允许 VERIFY_ABSENT 或 conditional delete，却没有机器字段说明失败发生在
  pre-CAS、post-CAS-owned 还是第三方冲突窗口。仅靠 operator 临场选择可能把第三方值删除、
  把未发生的写当已发生，或让 state 与 registry 事实分离。
- 动态 compensation contract 必须有冻结 branch discriminator，至少区分：pre-effect no-op、
  pre-CAS absence verify、post-CAS exact-owned delete、third-party conflict preserve，以及 12C
  pre-control-write no-op/post-control-write rollback。每个分支唯一映射 source state、registry
  operation、允许 touched count、token/control effect 和 exact terminal state；不匹配即 fail closed。

## 待重新验证的假设

- [ ] 另一个任务是否已修改根因 SQL或相关控制代码。
- [ ] 当前数据库规模、location 分布和 backlog 是否变化。
- [ ] 外键完整性是否允许安全删除 roots join。
- [ ] 目标 SQLite 最低版本和不同版本 planner 行为。
- [ ] 复合/部分索引实际空间成本。
- [ ] LLM provider 当前延迟、成本和数据条款。
- [ ] retention prune bug 是否已由其他任务修复。
- [ ] 上述文件和测试在实施开始时是否被另一个任务改动或重命名。
- [ ] 实施时 control/status 是否仍保留相同参数、是否仍可能写 diagnostics。
