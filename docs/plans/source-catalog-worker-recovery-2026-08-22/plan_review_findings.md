# 计划 v1–v4 独立审查 Findings 与处置清单

> 历史审查对象：`plan_review_revision.md` v1、v2、v3；v4 尚未冻结  
> 审查角色：SQL/性能、生命周期/安全、测试完整性/弱模型清晰度  
> v1/v2/v3 三轮结论：每轮三份均为 `FAIL`  
> 当前状态：v4 草稿正在处置 PR-054–095；修订者不自行关闭任何 finding，须待 v4
> 不可变 manifest 冻结后由原领域独立 reviewer 明确关闭

## 1. 审查完整性

- 三名 reviewer 均声明只读、未修改文件或生产状态。
- 三名 reviewer 均逐项核验 v1 的 9 个核心文件 SHA-256。
- SQL reviewer 另核验来源报告 SHA-256
  `8e6166ba063bc281ca1fa5da3c0743b895e4d93b6f2957de3cbd0b6938a95be6`。
- 三份报告都独立发现 Phase 12A 可能绕过真实 LLM 数据授权，定级 P0。

## 2. 合并后的 Findings

| ID | 最高级别 | Finding | v2 计划处置 | 状态 |
|---|---|---|---|---|
| PR-001 | P0 | 12A 普通 `resume` 可能在未单独授权时向主/备 provider 外发真实正文 | 12A 默认 LLM-off + OS egress deny；真实 LLM 需独立持续授权、范围/字符/成本上限；扩展至 12B | accepted, pending re-review |
| PR-002 | P1 | normalize eligibility 未绑定 active location 的 `source_id == primary_source_id` | 明确 parseable-primary 关系；加入 mismatch、重复与 mutation 测试 | accepted, pending re-review |
| PR-003 | P1 | locationless 业务语义含糊/矛盾 | 明确无 active parseable primary 的文档不得返回，但性能夹具必须保留大量 outer rows | accepted, pending re-review |
| PR-004 | P1 | `force=True` 与 completed/retry/terminal 语义未分矩阵 | 为 force/non-force 建立完整 oracle 与 test IDs | accepted, pending re-review |
| PR-005 | P1 | checkpoint 未定义 `completed_with_errors`、per-root error 与配置漂移 | checkpoint 绑定 root/config/scanner fingerprint；定义 quarantine/offline/partial/interrupted 状态与 per-root retry | accepted, pending re-review |
| PR-006 | P1 | LLM 队列缺 current normalized input、summary version/status、dedupe-before-LIMIT 合同 | 新增 LLM queue oracle、old-version regeneration、stable dedupe tests | accepted, pending re-review |
| PR-007 | P1 | content-hash cache 可把不同标题/source/kind 的结果错绑 | cache exact canonical request digest；缓存 provider payload，逐 document 重新绑定 artifact | accepted, pending re-review |
| PR-008 | P1 | WP-01 取消测试到 WP-04 才能转绿，破坏 red/green 阶段 | WP-01 只建 SQL fixture/red tests；O-S tests 在 T04/D04 前红、G04 后绿 | accepted, pending re-review |
| PR-009 | P1 | one-shot、session-only override、固定 revision 可能 G10 后才实现 | 新增 WP-09P/D09P/G09P，必须在 G10C 前交付与 E2E | accepted, pending re-review |
| PR-010 | P1 | 需要索引时缺生产 migration Gate | 在 G11A 与 D11B 间增加条件 D11M/G11M；无索引 ADR 显式关闭分支 | accepted, pending re-review |
| PR-011 | P1 | Canary A 对生产 DB/派生路径写入范围与 delta 不明确 | 拆分 scan-only/normalize-only/full canary；冻结 IDs、table/path allowlist、最大 delta、禁用阶段和 run ID | accepted, pending re-review |
| PR-012 | P1 | canary 无当前可执行 RPO/RTO/changeset | D11B 前验证一致恢复点或 changeset/reconcile；定义逐表 rollback/disposition | accepted, pending re-review |
| PR-013 | P1 | 多个 Gate 没有数值阈值，P95 方法也不确定 | 新增 `acceptance_thresholds.md`；固定 nearest-rank、样本数、SLA、backoff、scanner、LLM SLO | accepted, pending re-review |
| PR-014 | P1 | 单线程长 SQL 时“缓存 control token”可能永不刷新 | 明确低频外部 control generation 读取或线程安全 watcher；真实子进程 pause test | accepted, pending re-review |
| PR-015 | P1 | VM activity/heartbeat/业务 milestone 可能混淆 | 定义三者字段与用途；只有完整 cycle success 清零全局失败预算 | accepted, pending re-review |
| PR-016 | P1 | disk-full/mutant 可能写满真实 C: 或污染候选源码 | 只用 faulting VFS/facade/硬配额 scratch；mutant 在 throwaway worktree/runtime injection；结束校验 hash | accepted, pending re-review |
| PR-017 | P1 | 固定受审 revision 与恢复原 live-worktree Run 值冲突 | 定义 pinned release/worktree 与独立 data root；或 launcher fingerprint fail-closed；Run 值变化需 ADR/授权 | accepted, pending re-review |
| PR-018 | P1 | 12A 后 paused，12B 登录验证缺少不会立即启动的 arm 状态 | WP-09P 提供 `arm-for-next-logon`/enable-only 原子状态；circuit reset 与 resume 分离 | accepted, pending re-review |
| PR-019 | P1 | backoff 可被部分里程碑、交替签名、supervisor/login 重启绕过 | 只有完整 cycle success 清零；持久化 per-signature + 全局滚动失败/无成功预算 | accepted, pending re-review |
| PR-020 | P1 | runtime/control 缺 session/attempt/token/sequence，损坏状态默认 enabled | 身份 envelope；缺失/损坏 control/circuit 在受管生产 fail-closed；显式 reset | accepted, pending re-review |
| PR-021 | P1 | source“只读”只有事后 sentinel，不是权限边界 | Canary 必须用受限身份/只读副本/受审写拒绝 sandbox；不可用则 BLOCKED | accepted, pending re-review |
| PR-022 | P2 | CatalogStore eager `_DDL` 会使“普通启动不建索引”要求落空 | 显式 operator migrator + verify-only open；DDL-denying authorizer test；fresh schema 分支 | accepted, pending re-review |
| PR-023 | P2 | 性能缺 N/2N scaling、cold-ish 定义、可重复 P95 | 加固定拓扑、样本与 quantile；多个规模的 VM-work scaling | accepted, pending re-review |
| PR-024 | P2 | scanner 46k 夹具缺 root/group/depth/sidecar 拓扑与 rehash SLA | 按现场 244/16,570/429/9,853 等拓扑建 profile；定义 full-audit cadence | accepted, pending re-review |
| PR-025 | P2 | LLM backlog 没有数量/年龄/drain/cost SLO | 定义 low/base/high arrival/service、oldest age、1/7/30-day drain 和 cost cap | accepted, pending re-review |
| PR-026 | P2 | Gate 编号/状态/verdict 不唯一 | 新增 `gate_state_machine.md`；`BLOCKED` 为 Gate 状态而非 reviewer verdict；条件分支显式 | accepted, pending re-review |
| PR-027 | P2 | traceability 使用非稳定 test ID、章节指针错误、D Gate 漏映射 | 分配正式 IDs、修报告章节、补 D/G 覆盖和 12A/12B LLM 映射 | accepted, pending re-review |
| PR-028 | P2 | D review 后测试仍可静默变化；review 代存缺原始 payload hash | 采用 T(test-only)→D→I(implementation)→G commits；测试 diff 使 D 失效；保存 reviewer payload/hash | accepted, pending re-review |
| PR-029 | P2 | P2 scanner/LLM/capacity 全串行阻塞核心验证 | 划分 Core Recovery 与 Hardening lanes；restricted canary 可先行，完整观察/自启动需 hardening 或功能明确禁用 | accepted, pending re-review |
| PR-030 | P2 | 120s delay 仍可能每次 child restart 重付 | 只在 logon/supervisor session 支付一次；增加 S-S13 | accepted, pending re-review |
| PR-031 | P2 | parser 没有按 HTML/PDF/Word/Excel 的独立 profile | 增加 WP-06P 与 P-FMT test IDs；不再把 parser 全部归入 queue timing | accepted, pending re-review |
| PR-032 | P2 | evidence 可泄露用户名、外部路径和持仓文件名 | secret永不采集；获批raw evidence仅进repo外ACL/加密/TTL sink；仓内仅opaque ID、脱敏统计与repo外key HMAC | accepted, pending re-review |
| PR-033 | P2 | supervisor 重构可能丢失 Job Object kill-on-close | 新增 RQ/test，保留 create/assign/kill-on-close 与 assign failure fail-closed | accepted, pending re-review |
| PR-034 | P2 | 注册表恢复无 compare-and-swap，注销授权隐含 | 写前确认缺失；撤回只删本次精确值；单独说明会注销并要求保存工作 | accepted, pending re-review |
| PR-035 | P3 | 多个原报告章节指针错误 | 随 PR-027 修正 | accepted, pending re-review |

## 3. v2 关闭条件

1. 上表每项映射到至少一个具体文档修订和 test/Gate ID；
2. 所有核心文件重新计算 v2 hash；
3. 三名原 reviewer 分别复审受影响领域；
4. PR-001–021 中任何一项未被 reviewer 明确关闭，v2 不得用于实施；
5. P2 若未完全关闭，必须有明确 owner、阻断范围和最迟 Gate，不能静默延期。

## 4. v2 三路复审结果

- 三名原reviewer均逐项重算12个v2核心文件及来源报告hash，全部MATCH；无revision drift。
- SQL/性能、生命周期/安全、测试完整性三份结论均为`FAIL`；没有reviewer修改文件或生产状态。
- v2不能作为实施输入。下表只记录v3拟处置；状态一律是`pending independent v3 re-review`。

| ID | 级别 | v2 finding/反例 | v3计划处置 | 状态 |
|---|---|---|---|---|
| PR-036 | P0 | 12B只批准“LLM mode”，可复用短期Canary/12A配置长期外发 | 12B默认off；enabled必须新`G12B_LOGIN_AUTOSTART` manifest，逐项provider/data/fields/caps/retention/destination/expiry，arm绑定hash且profile等于G12A；L-S19/PX-S18 | addressed in v3, pending independent re-review |
| PR-037 | P1 | normalized/summary“current”未绑定当前source ID/hash；S1可抑制/错绑S2 | Q-S17/L-S18；normalized UPSERT与summary suppression均绑定primary source ID/SHA及normalized ID/hash；G09 source-rotation mutant | addressed in v3, pending independent re-review |
| PR-038 | P1 | 普通resume仍可被解释为清circuit | reset-only/resume-only/arm-only三动作；open时resume/session/arm零副作用；S-S09/S-S18/PX-S08 | addressed in v3, pending independent re-review |
| PR-039 | P1 | canary只限table/path/max net delta，允许表内wrong-PK或净零污染可通过 | `CanaryWriteContract`精确operation/PK/column/file，actual touched rows与precommit/post-read changeset；PX-S12、PX-S13及CAN-A1/A2/A3/BP/BF稳定ID | addressed in v3, pending independent re-review |
| PR-040 | P1 | 可写launcher自验fingerprint，无外部trust root且有check-load TOCTOU | 独立trust anchor+不可写内容寻址完整release/interpreter；tamper/reparse/TOCTOU/restart测试PX-S03/14/15 | addressed in v3, pending independent re-review |
| PR-041 | P1 | 唯一DAG跳过T02B/I02B、G10C/G10R循环，WP-01可暗改production seam | 状态机完整重写；WP-01唯一T-D-G例外且禁止产品改动；02B NI/IDX均有T/D/I/G；G10C只到D11A、G10R只到D12A | addressed in v3, pending independent re-review |
| PR-042 | P1 | G07-OFF与A1/A2/A3/Canary B无正式独立节点/合法边 | 正式T07O/D07O/I07O/G07O；每个A与BP/BF均D/OP/G、pause、独立review；G07O无B出边 | addressed in v3, pending independent re-review |
| PR-043 | P2 | registry“CAS”只是check/facade，竞态可覆盖第三方值 | 真实atomic create-if-absent/exact conditional delete；mutex仅辅助；PX-S09、PX-S16、PX-S17真实双进程disposable-key测试；无法证明则G12B-PRE必须FAIL | addressed in v3, pending independent re-review |
| PR-044 | P2 | “完整日志”与“evidence无正文/secret”冲突，repo外未定义保护 | secret永不采集；正文默认不采集；approved sink SID ACL/加密/无reparse/7与30日TTL/HMAC；EV-S01–03 | addressed in v3, pending independent re-review |
| PR-045 | P1 | “禁止跳过locationless”可被解释为让locationless进入结果 | 明确仅禁止从outer fixture预删；队列结果仍排除无parseable-primary rows | addressed in v3, pending independent re-review |
| PR-046 | P2 | parser P95无每格式/size bucket最小n | S bucket每格式≥20/P95，M≥10/max，异常/oversized/pause固定n；P-FMT稳定bucket ID | addressed in v3, pending independent re-review |
| PR-047 | P2 | traceability仍引用no-stats/battery/disk-full/raw-series等非稳定名 | 重写矩阵；新增Q-P、M-、SC-S/P、OBS-S、CAN-A1/A2/A3/BP/BF、EV-S稳定ID，Requirement逐项引用已定义ID | addressed in v3, pending independent re-review |
| PR-048 | P2 | 出现第四种reviewer verdict`FAIL_EVIDENCE_DRIFT` | 统一`verdict=FAIL; reason_code=EVIDENCE_DRIFT`；schema只允许三种verdict | addressed in v3, pending independent re-review |
| PR-049 | P2 | 实施中更新task/findings/trace会立刻破坏已审核心hash | 新`gate_ledger.schema.json`；动态JSONL append-only/hash-chain，核心冻结；progress仅叙事 | addressed in v3, pending independent re-review |
| PR-050 | P2 | provider send后crash无法证明exactly-once billing | durable PREPARED/IN_FLIGHT/OUTCOME_UNKNOWN ledger；unknown不自动重发且占cost cap；L-S20/21 | addressed in v3, pending independent re-review |
| PR-051 | P2 | SQL VM proxy未冻结progress handler n，old/new不可比 | T01冻结progress_n/PRAGMA/params/fixture；保存count×n区间；Q-P01 | addressed in v3, pending independent re-review |
| PR-052 | P2 | scanner“≥2×”用历史427s而非同拓扑旧/新样本 | exact baseline commit与同topology/environment/instrumentation hashes，旧/新各n≥10；SC-P04 | addressed in v3, pending independent re-review |
| PR-053 | P2 | 第四种动态状态/分支写法及裸G10/D-G缩写仍会造成弱模型歧义 | 节点类型只允许T/D/I/OP/G与schema合法node ID；主流程状态含BLOCKED/INVALIDATED/NOT_SELECTED，绝不冒充reviewer verdict；核心DAG清理自造缩写 | addressed in v3, pending independent re-review |

## 5. v3 复审关闭条件

1. 不可变`plan_manifest.v3.json`冻结v3全部核心文件（含`gate_ledger.schema.json`）与来源
   报告hash；`plan_review_revision.md`记录该machine manifest自身SHA-256；
2. 三名原领域reviewer各自从v3 hash重读，不沿用v2内存结论；
3. PR-001–021及PR-036–045中任何P0/P1未被相应reviewer明确关闭，v3不得用于实施；
4. P2必须closed或在计划内有owner、最迟Gate与不危及当前路径的理由；
5. Reviewer报告仍为只读；修订者不得自行把状态改为closed。

## 6. v3 三路复审结果

- 三名原 reviewer 均从 `plan_manifest.v3.json` 重新读取并逐项计算 13 个核心文件、来源报告及
  manifest 自身 hash；全部 `MATCH`，没有 revision drift。
- SQL/性能、生命周期/安全、测试/可实施性三份 verdict 均为 `FAIL`；v3 不得作为实施输入。
- 下表只登记 v4 拟处置。任何 `addressed` 都是修订者陈述，不等于 reviewer 关闭；统一等待
  v4 不可变 manifest 冻结后的独立复审。

| ID | 级别 | v3 finding/可执行反例 | v4 计划处置 | 状态 |
|---|---|---|---|---|
| PR-054 | P1 | 单一 `T02B` 在 ADR 分支前，却被要求同时承载 NI/IDX 两套互斥红测；ADR 后改测试又会使设计审查失效 | 改为 `G02B-ADR` 先只读选择并冻结 ADR-02；之后分别走 `T02B-NI→D02B-NI→I02B-NI→G02B-NI` 或 `T02B-IDX→D02B-IDX→I02B-IDX→G02B-IDX`；未选分支不创建 ledger record | addressed in v4, pending independent re-review |
| PR-055 | P1 | `G07E→D11M-L` 允许在 Canary A/G10R 之前迁生产 request-ledger schema | 新增只读 `G11M-L-ADR`；只有 `G11B-A3 + G07E` 后才能判定，schema-delta 分支才进入 `D11M-L→OP11M-L→G11M-L` | addressed in v4, pending independent re-review |
| PR-056 | P1 | JSON Schema 接受 reviewer FAIL/open P1 的伪 `PASSED`、非法 next edge、`G10C=NOT_SELECTED`、`BF00`，也拒绝合法未审 READY | 移除 `NOT_SELECTED`；增加跨字段 schema；新增 `T00L→D00L→I00L→G00L` deterministic semantic validator bootstrap；DAG 决定下一边，ledger 只能声明并由 validator 比对 | addressed in v4, pending independent re-review |
| PR-057 | P1 | Canary B 与 12A 没有逐 provider/逐 cycle 冻结 exact write set、RPO/RTO 与 precommit | BP/BF 每阶段新增不可变 `CanaryWriteContract`；12A 每周期先物化并 hash 绑定 `CycleWriteContract`；机器合同统一走 `operation_contract.schema.json`，首写前另建 `D11J→OP11J→G11J` protected journal | addressed in v4, pending independent re-review |
| PR-058 | P1 | Registry CAS 后、用户最终确认保存工作前存在意外重启即启动窗口 | CAS 后状态改为 `ARMED_ON_PRELOGIN/ON`；ARM token 在CAS消费，之后dormant lease；无短 TTL、generation/release/auth/user/next-logon绑定且一次性消费的 `LOGIN_COMMITTED` 时 launcher 零启动；另设LOGIN链与显式RB | addressed in v4, pending independent re-review |
| PR-059 | P1 | 生产 `reset-circuit` 可在 DAG 外清 latch，绕过独立授权/审计 | 每次生产 reset 只允许唯一 `D05Rnn→OP05Rnn→G05Rnn`；合同绑定failure generation、exact ancestor D return与全部失效；reset-only、保持 PAUSED且不产生resume/arm/registry/LLM权限 | addressed in v4, pending independent re-review |
| PR-060 | P1 | `G12B-POST→RECOVERED` 与“每个 canary OP 后暂停”冲突，且没有长期激活的独立授权链 | `G12B-POST` 只到 `LOGIN_VALIDATED_PAUSED/ON`；另走 `D12C→G12C-PRE→OP12C→G12C`。G12C只记录`lifecycle_outcome=RECOVERED`且物理state不变；失败走`OP12C-RB→G12C-RB`，当前session process0 | addressed in v4, pending independent re-review |
| PR-061 | P1 | G10C/G10R 共用 prompt 要求 G10C 检查其下游 Canary/Hardening，形成伪循环 | 拆成 Core/SQL/安全三份 G10C 模板与 Release/性能/生命周期三份 G10R 模板；各自只读其合法前置 | addressed in v4, pending independent re-review |
| PR-062 | P2 | NI 分支没有 fresh-empty 显式 bootstrap/普通 open 零 DDL 合同 | 两分支共享 `M-COM-S01–S06/M-COM-F01–F02`：ordinary `mode=rw`、missing/old schema fail closed、显式 init/upgrade、幂等及 crash/ENOSPC；NI 与 IDX 都先满足该基线 | addressed in v4, pending independent re-review |
| PR-063 | P2 | `callback_count × progress_n` 被写成精确 VM step 区间，但 SQLite progress callback 只提供近似进度 | 全部改称 `vm_work_proxy` 近似可比指标；同环境/同 n 重复统计，不再推断 true steps 或严格区间 | addressed in v4, pending independent re-review |
| PR-064 | P2 | parser 格式 ID 漏掉实际启用的 MHT/DOC/XLS/JSON/XML/XSD 等，且 HTML/text 合桶、无中型或硬上限 | D06P 先冻结运行时代码实际 dispatch 清单；按 PDF、TXT/MD/CSV、HTML/HTM、MHT、DOCX、DOC、XLSX、XLS、PPTX、JSON/XML/XSD 分族；每族 S 样本，支持 M 的族测 M，否则验证显式硬上限 | addressed in v4, pending independent re-review |
| PR-065 | P2 | T02A/T08/T09 与 RK-12/RK-28 使用含糊集合或引用已删除 `R-S09/R-S13` | 为 SQL mutation、E2E mutation、ledger validator、parser family 建稳定 ID；T08 明列现存 R-S ID；Requirement/Risk 逐项列 ID | addressed in v4, pending independent re-review |
| PR-066 | P2 | schema/prompt 仍允许 `BF00`、非法 `G02A/B`、伪 `NOT_APPLICABLE ADR`，并把 Design Gate 限成只能 PASS | BF 仅 `BF01–BF99`；全部改为精确节点；branch 进入 `branch_decision`；D/G 同样允许 `PASS_WITH_NONBLOCKING_FINDINGS`，但只容 P2/P3 | addressed in v4, pending independent re-review |

## 6.1 v4 冻结前草稿预检（非正式 verdict）

以下由三名独立领域 agent 对仍在变化的 v4 草稿只读预检得出。它们不构成 v4 PASS/FAIL，
但在正式冻结前必须进入处置清单；“addressed”仍须冻结版本 reviewer 复验：

| ID | 级别 | 草稿反例 | v4 草稿处置 | 状态 |
|---|---|---|---|---|
| PR-067 | P1 | DAG/vectors/test registry 把instance data伪装成JSON Schema，因而可接受任意值 | 新增三个专用instance schema；data只写`schema_id`；T00L加empty/array/scalar shape负例 | addressed in v4 draft, pending frozen review |
| PR-068 | P1 | Schema先失败导致vector声明的领域primary code不可达，且一例多code无确定性 | 每个subcase独立`case_id/expected_primary_code`；冻结schema-pointer重分类规则，未知形状才E002 | addressed in v4 draft, pending frozen review |
| PR-069 | P1 | 主agent可合成fake reviewer PASS/确认；role/cardinality/disjoint不足 | exact role overrides/disjoint进入DAG；新增`review_confirmation.schema.json`；reviewer原样JSON+MD并亲自回读 | addressed in v4 draft, pending frozen review |
| PR-070 | P1 | group-level owner×due映射产生错误测试笛卡尔积 | `test_id_registry.v4.json`改为283个逐ID生命周期映射，加`G10-PROMPT-S01`与冻结引用提取语法 | addressed in v4 draft, pending frozen review |
| PR-071 | P1 | OP状态/写入/授权只在prose，任意`NOT_APPLICABLE:*`可绕过 | 新增静态operation catalog、动态operation contract与authorization schema；每OP唯一匹配，N/A仅枚举安全reason | addressed in v4 draft, pending frozen review |
| PR-072 | P1 | plan manifest不可能预先冻结I00L未来validator，bootstrap review head又不闭合 | v4只冻结实施合同；I00L生成独立validator release manifest；G00L绑定I00L-terminal candidate head，仅D00L可null | addressed in v4 draft, pending frozen review |
| PR-073 | P1 | 12B/12C失败要求rollback但DAG无合法写节点，迫使只读Gate改状态 | CAS前D12B-RB seal；失败走OP12B-RB→G12B-RB；final失败走OP12C-RB→G12C-RB | addressed in v4 draft, pending frozen review |
| PR-074 | P1 | G12C被建模成改变物理状态，且下次正常登录无重验转换 | OP12C完成ENABLED_IDLE；G12C前后物理state相同，仅写RECOVERED outcome；普通登录另有全hash/circuit/Job/single-instance重验 | addressed in v4 draft, pending frozen review |
| PR-075 | P1 | reset return是不可计算占位符且允许返回G | 动态reset contract绑定failure generation、exact ancestor D、全部下游失效和expiry；validator E028 | addressed in v4 draft, pending frozen review |
| PR-076 | P1 | “最终Gate前Run必须不存在”与12B CAS正面冲突 | 改为分阶段Run不变量；只有OP12B-CAS创建exact dormant value、OP12B-RB条件删除 | addressed in v4 draft, pending frozen review |
| PR-077 | P1 | 12A intent/finalize journal无存储/迁移/ACL/fsync合同 | 首个写canary前新增D11J→OP11J→G11J；独立protected file journal，ordinary open zero DDL | addressed in v4 draft, pending frozen review |
| PR-078 | P2 | parser expansion、Test-ID提取与若干prose/vector映射不精确 | parser route manifest schema绑定实际expanded IDs；active-section grammar；matrix按GL vector当前语义重排 | addressed in v4 draft, pending frozen review |
| PR-079 | P1 | D12B-RB 在 ARM 写入后才审，且 ARM/G/D-CAS 早期失败无 compensation edge | 改为 D12B-ARM→D12B-RB→OP12B-ARM；从首个写入点起每个失败边进入统一 OP12B-RB，G 继承 exact terminal state | addressed in v4 draft, pending frozen review |
| PR-080 | P1 | dynamic contract 可接受错误 typedValue、PK arity/hash/null 组合及 document/source 错绑 | typedValue 条件化；候选改为原子 `candidate_sources`；write 反向引用 document；跨字段语义进 validator vectors | addressed in v4 draft, pending frozen review |
| PR-081 | P1 | OP12B-CAS 可在 registry 细节为空时通过，且误把 read-then-write/same bytes 当 CAS | registry_operations 冻结 hive/SID/view/key/name/type/bytes/prior/CAS proof/nonce/post-read；双进程和第三方负例；无法证明即 BLOCKED | addressed in v4 draft, pending frozen review |
| PR-082 | P1 | auth kind/action/stage/generation 无 exact 绑定；compensation 可缺 parent auth | 新 operation intent schema；D先冻结 intent，用户批准 hash，contract 三方绑定；compensation parent id/hash；严格 UTC/scope 语义 | addressed in v4 draft, pending frozen review |
| PR-083 | P1 | write journal identity 是自由文本，无法证明跨 DB/file/registry/control crash recovery | journal manifest + head-before/intent/finalize/head-after；每个 mutating OP/cycle/reset 必绑；半提交先 reconcile | addressed in v4 draft, pending frozen review |
| PR-084 | P1 | reset 只列 generation/return/descendants/expiry，不能证明 latch/budget/history 未被扩大或删除 | reset contract 增加 latch/budget/history exact before/after hash、reset token 与禁止组合动作；typed negative vectors | addressed in v4 draft, pending frozen review |
| PR-085 | P1 | G12C 后第二次及以后普通 cycle 无 exact write/auth/cap/journal 合同 | static runtime_cycle_policy；每 cycle 副作用前 seal、重验 auth/daily/monthly caps、绑定 source/write/egress/journal/generation，失败 circuit+pause | addressed in v4 draft, pending frozen review |
| PR-086 | P1 | parser route array 可重复同一路由并遗漏其余 route，enabled 样本数还可为零 | routes 改 exactly-14 keyed object；各 bucket 下限；expanded IDs 必须由 route policy 精确推导且唯一 | addressed in v4 draft, pending frozen review |
| PR-087 | P1 | test registry 的自由文本 condition 使互斥 NI/IDX 与 LLM profile lifecycle 可被“all/any”错误解释 | condition_definitions 闭集 + condition_id；每分支列 exact lifecycle case；checker 验证 union/选择语义 | addressed in v4 draft, pending frozen review |
| PR-088 | P1 | validator vector 没有冻结 base fixture/mutation DSL/reason mapping，部分 mutation 实际复制 null | validator fixture manifest、typed mutation、stage/pointer/reason_rule；每 base 必须 OK，每 mutation 只触发唯一 primary rule | addressed in v4 draft, pending frozen review |
| PR-089 | P1 | `manifest.md` 无法机器证明 E014 的 artifact/ACL/TTL/敏感信息约束 | `manifest.json` schema + `report.md` 分别 hash；artifact 明确 repo/sink、SHA/HMAC、size/type/classification/ACL/encryption/reparse/TTL | addressed in v4 draft, pending frozen review |
| PR-090 | P1 | “stdlib-only + python -I -S”无法执行 Draft 2020-12 schema，信任合同自相矛盾 | 独立 venv；冻结解释器、jsonschema/referencing 闭包、wheel/tree/module/sys.path hash；用 -I 不用 -S；tamper负例 | addressed in v4 draft, pending frozen review |
| PR-091 | P1 | INDEX 分支若 G11A 迁移前强制10秒则 D11M 永远不可达 | G11A/INDEX 允许受界只读 INDEX_REQUIRED + semantic oracle/plan；NO_INDEX 当场10秒；G11M后必须10秒 | addressed in v4 draft, pending frozen review |
| PR-092 | P1 | machine G10R 需要 G09P/G09，但多份 prompt/join prose 遗漏，可让弱模型早签 release | 所有 G10R join/prompt 补 exact G09P/G09；G10-PROMPT-S01 校验 machine/prose 同集 | addressed in v4 draft, pending frozen review |
| PR-093 | P1 | 新增 ZR1002/1003 测试依赖 missing DB eager init，未来 reader-first 会被误判回归 | Phase0 纳入；T02B fixture 先显式 init/upgrade 再 reader open；产品 ordinary open 仍 zero DDL；映射 M-COM-S05/S06 | addressed in v4 draft, pending frozen review |
| PR-094 | P1 | checker token regex 漏 `P-FMT00-ROUTE`，反引号范围与 R01–R99 缩写可漏检 | 扩展 token grammar；按相邻 token/generic backtick range 检出；GL/F与reset ID全部展开为 exact IDs | addressed in v4 draft, pending frozen review |
| PR-095 | P2 | prose 的“new reviewer”比 DAG disjoint 更强且不可执行；final approval 顺序与 DAG 不同 | 统一为 exact DAG-disjoint/min_not_in；D12C 先冻结 proposed intent、用户后批准 hash、G12C-PRE 再验 | addressed in v4 draft, pending frozen review |

## 7. v4 复审关闭条件

1. 生成全新、不可覆盖的 `plan_manifest.v4.json`，冻结全部 v4 核心文件、
   `gate_dag.v4.json`、`gate_ledger.schema.json` 与来源报告 hash；
2. 三名原领域 reviewer 分别从 v4 manifest 零信任重读并回报逐项 hash；结论只对该 hash 有效；
3. PR-001–095 中任一 P0/P1 未被对应 reviewer 明确标记 `CLOSED`，v4 不得实施；
4. P2 必须关闭，或由 reviewer 明确接受 owner、due node、隔离理由；不得由修订者自批；
5. 任一 reviewer `FAIL` 后冻结该 revision 为失败历史，修复必须生成 v5 或更高的新 manifest。
