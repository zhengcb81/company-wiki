# v5 baseline/plan Markdown 语义覆盖审计

日期：2026-09-04。覆盖执行：`filing_planning_audit`（README/task_plan 初始覆盖）与
`v5_baseline_full_read`（其余 11 份全文及最终交叉核对）。范围是
`docs/plans/source-catalog-worker-recovery-v5-2026-09-03/baseline/plan/` 的 13 份 Markdown，6,691 行。

这是只读状态/路由审计，**不是正式 v5 技术 PASS、不是 v4 候选复审通过、不是授权实施**。不读运行 JSON/源码来执行校验，不启动旧 checker，不修改 baseline 或 v5 版本合同；本审计只写此文件。

## 阅读覆盖（完成）

| 文件 | 行数 | 全文语义覆盖 |
|---|---:|---|
| README.md | 208 | 是，1–208，输出未截断 |
| task_plan.md | 829 | 是，1–280 / 281–560 / 561–829，输出未截断 |
| acceptance_thresholds.md | 336 | 是，1–170 / 171–336，输出未截断 |
| agent_review_gates.md | 567 | 是，1–200 / 201–400 / 401–567，输出未截断 |
| execution_playbook.md | 1171 | 是，1–220 / 221–440 / 441–660 / 661–880 / 881–1050 / 1051–1171，输出未截断 |
| findings.md | 768 | 是，1–200 / 201–400 / 401–600 / 601–768，输出未截断 |
| gate_state_machine.md | 453 | 是，1–180 / 181–360 / 361–453，输出未截断 |
| implementation_agent_prompts.md | 388 | 是，1–200 / 201–388，输出未截断 |
| ledger_validator_contract.md | 249 | 是，1–130 / 131–249，输出未截断 |
| plan_review_findings.md | 187 | 是，1–100 / 101–187，输出未截断 |
| rollout_rollback_runbook.md | 515 | 是，1–180 / 181–360 / 361–515，输出未截断 |
| test_acceptance_plan.md | 793 | 是，1–200 / 201–400 / 401–600 / 601–793，输出未截断 |
| traceability_matrix.md | 227 | 是，1–120 / 121–227，输出未截断 |

## 当前已确认的路由与状态差异

- README 和 task_plan 均为原 v4 候选计划，不是正式 v5 工作队列。目录名、来源报告、progress、plan_review_revision、plan_manifest.v4 及执行节点应按原历史位置解释；迁入 baseline 不使旧相对路径成为可运行入口。
- README 明言 v4 候选须三路冻结复审，task_plan Phase 00L–12 全为 pending。它们不能推翻当前 v5 的 `V5_BASELINE_READY / VERSION_CONTRACT_PENDING / NOT_IMPLEMENTATION_AUTHORIZED`，也不能直接领取 T00L/D00/OP 等节点。
- 当前只允许未来 v5 版本合同工作，import 完整性不是机械合同一致性或生产技术审查。不得运行 README 第6节的旧 plan_consistency_check 命令。
- 旧文档中 SQL P95、canary 5周期/2小时、生产规模/容量和运行开关均是验收要求或历史调查值，不是2026-09-04新鲜运行结果。
- 独立agent gate、单线程LLM、source只读、生产配置tmp隔离、secret不采集、真实provider分阶段单独授权、暂停优先、不得自动删Run等安全要求保留，不因只读搬迁或本次审计而放松。
- `acceptance_thresholds.md` 的数值是 **v4 默认最低标准/未来 D Gate 的冻结输入**，不是当前实测结果。其 SQL、parser、scanner、LLM、canary、Registry、两小时观察与最终激活阈值均不能被当作已通过；放宽阈值必须 ADR + 原始数据 + 独立 reviewer，样本不足只能 BLOCKED/fail closed。
- 该阈值文档保存了多项不可弱化的关键边界：真实 provider 各阶段新授权且含糊 post-send 不自动重试；生产写先有 exact typed-PK/文件 contract 和受保护 journal；Registry 不得 `Test/Get -> New-ItemProperty -Force`，任何既有同名值都是 ownership conflict，自动 rollback 不删 Run；最终激活须两次不同用户授权并经过独立 pre/post reviewer。迁移为 v5 时必须显式逐项承接，不能靠复制路径或默认值暗示继承。
- `agent_review_gates.md` 完整保留了“每个关键节点独立 agent 阻断审查”的用户要求：实现型 WP 至少 D/G 两次，生产动作必须 D→OP→G，部分节点恰好 2 或 3 名 reviewer，operator/实施者不得自审；证据、测试、diff 变更会使旧 PASS 失效。平台无法满足独立性时只能记 `NO_INDEPENDENT_REVIEW`/BLOCKED，不能降级为自审或集中到结尾补签。
- 未来 v5 合同必须重新生成自身 DAG/schema/hash 路由；该文档明确引用 `gate_dag.v4.json`、`operation_contracts.v4.json`、`reviews/<node>` 和旧节点名，迁入 baseline 后这些是 **v4 历史语义**，不能被当前执行器直接消费。可保留的原则包括：初版 reviewer 互不读结论、raw payload + detached confirmation、每 Gate 至少一项反例、P0/P1 由原 reviewer 复审关闭、G12B/G12C 不得绕过两次外部用户授权。
- `execution_playbook.md` 1–440 再次明确“描述未来如何实施，不授权现在实施”，并把每 WP 的 Git/dirty-file ownership、worker 隔离、文件白名单、T/I commit、D/G hash 作为固定输入。其命令和路径绑定旧 `plan_manifest.v4.json`、validator v2 与旧 evidence 路径，当前不能直接照跑；尤其 WP-00 中生产 SQLite、进程/Registry、配置体检等虽标称只读，仍须等正式 v5 合同和用户实施授权，不能由本次文档审计触发。
- 手册 441–880 的 WP-05～WP-10 仍是未实施设计：完整周期才可清失败预算、circuit/reset 分离且 reset 后仍 PAUSED；scanner benchmark 必须同拓扑同协议，历史 427 秒不得作速度分母；parser 各 route 单独验收或显式禁用；LLM 不得用直接多线程，post-send outcome unknown 不得自动重发；retention 不得删生产数据；E2E 必须 tmp、无网络、真实子进程并用 mutant 证明测试杀伤力。所有阶段仍要求各自独立 D/G reviewer，而非一次最终总审替代。
- 手册 881–1171 的生产部分同样只是 v4 候选流程：生产只读、条件 migration、journal 初始化、A/B canary、两小时观察、dormant Run 安装、登录验证和最终启用都需要逐阶段新授权与 reviewer。危险动作包括显式生产 DDL、Run CAS、logoff、生产 canary 写和最终 autostart activation；这些旧步骤当前全部不可执行。文末也明确旧计划“仍保持独立、并入主线是未来单独任务”，进一步证明 baseline 不能冒充 v5 当前队列。
- `findings.md` 1–400 是截至旧 v4 修订期的证据/设计演化记录，基线 commit、行号、DB 容量、队列规模、性能数字、隔离状态均是历史快照，必须重新基线化后才可用。它保留的根因证据链是：normalize queue 的 correlated SQL plan 退化导致单核 CPU 消耗与零吞吐；parser 当时尚未启动；900 秒 watchdog、重复 scan checkpoint 与启动延迟放大故障；LLM 约 42 秒/文档只是 SQL 修复后的下一瓶颈，不是当时卡死主因。
- 该 findings 同时明确 v1、v2、v3 三轮独立审查均 FAIL，v4 草稿在 runtime-template authorization、机器合同与 prose 同步方面也曾明确“内部不一致、不可冻结、不可实施”。它记录的后续 HEAD/ZR1005/ZR1006 与 `-I -S`/venv 冲突都是旧时间点的 drift 线索，不是当前 v5 已关闭事项。
- findings 401–768 记录了 v4 草稿继续发现并逐步修补的 checker 假绿、schema 闭包、rollback 分支、Windows Run 非原子删除、journal hash 环、四计数预算、双授权链、vector pointer 与 manifest 自证问题。即使末段称 checker 已覆盖固定 48 个文件，也只能说明该次 v4 候选的机械冻结准备；这些历史修补不能被解释为 v5 的合同已经完成或三路技术复审已 PASS。
- 末尾八项“待重新验证的假设”仍全部未勾选，包含当前代码漂移、生产规模/backlog、SQLite planner/index成本、provider条款、retention bug和 control/status 写行为。v5 V5-1 必须把它们按当前日期重新分类为已验证/仍阻断/不再适用，不能原样把旧假设转为当前事实。
- `gate_state_machine.md` 自称“v4 唯一 Gate 状态机”，且明确机器真相来自 `gate_dag.v4.json` 与 v4 ledger schema。它不能为 v5 计算 eligible node；当前也不存在可据此领取的 T00L/D00/OP 等节点。可迁移的安全语义是单节点领取、T/D/I/G 或 D/OP/G、reviewer hash/confirmation、漂移失效、分支 exactly-one、每次 reset 独立编号，以及每个关键节点缺独立 agent review 就没有合法下一边。
- 状态机中所有生产转换（schema migration、journal init、canary、Run CAS、logoff、最终 activation）都绑定旧 DAG、旧授权和旧证据 revision；这些是危险的未来操作说明，不是当前状态。其 zero-delete rollback、dormant prelogin、双用户批准、G12C 后逐 cycle 新合同等防护必须由 v5 新机器合同重新表达后才可能实施。
- `implementation_agent_prompts.md` 是 v4 派工模板而非可直接复制的当前任务：它硬编码已退休旧目录 `docs/plans/source-catalog-worker-recovery-2026-08-22/`，要求 v4 manifest/DAG/ledger/checker，并包含生产只读、migration、canary、Run CAS、注销与最终 activation reviewer 模板。未来 v5 必须重写所有路径、版本、node/schema 名并填尽 placeholder；留下任一 placeholder 或引用旧目录都应 fail closed。
- 模板中“一个 agent 一次只执行一个 WP/角色”、D 后不得改测试、reviewer 只读且需 detached confirmation、每个 G10C/G10R 角色独立、不在最后集中补签等审查结构应保留。任何实施 prompt 仍须显式携带 worker paused/autostart off、生产/config/source sentinel 与停止条件。
- `ledger_validator_contract.md` 开头明确这是 v4 未来实现合同、当前不得创建动态 ledger。文件内命令、schema closure、reason codes 与 bootstrap transcript 均绑定 `plan_manifest.v4.json`、`gate_dag.v4.json`、validator release v2；在 v5 新合同、实现和 G00L 类 bootstrap 审查完成前，不能运行旧 validator，也不能把旧 vector/checker PASS 当成当前执行授权。
- 其可保留的核心是外部 pre-entry 信任、closed schema registry、canonical append-only chain、protected head anchor、review payload/confirmation 实际 hash、稳定 fail-closed reason、分支/授权/操作/rollback/runtime-cycle 的语义验证。需要 v5 特别解决的是文内 29-schema/fixture/CLI 列表及 v4 node 编号是否仍完整，不能直接复制旧计数或文件名。
- `plan_review_findings.md` 是明确的 v1–v4 历史处置台账：v1/v2/v3 每轮三名 reviewer 均 FAIL；PR-001–105 中的 `accepted/addressed` 只代表修订者拟处置，**全部仍待冻结版本独立复审**。v4 正式关闭条件要求全新 manifest、三领域 reviewer 零信任重读，并由 reviewer 明确关闭 P0/P1；这在 baseline 文档中没有发生。
- 因此 v5 不能把 PR 表格的 “addressed in v4 draft” 批量改写成 CLOSED，也不能声称旧 v4 technical PASS。V5-1 应保留 ID/证据链，逐条映射到新的 v5 normative contract，并安排独立 reviewer 在新 hash 上重新判定；历史报告本身保持原字节更合适。
- `rollout_rollback_runbook.md` 自身限定只有旧 Phase 11–12 且取得相应授权才可执行状态变更，并写明当时预期 `PAUSED / STOPPED / Auto-start OFF`。它含可写日志的 status wrapper、pause 命令、显式生产 migration、canary、Run CAS、logoff、最终 activation 和事故恢复动作；当前一律视为危险历史命令示例，不应在 V5-1 审计或基线化时运行。
- Runbook 的回滚规则应保留为 v5 设计要求：不裸杀 PID、不 `git reset --hard`、不自动复制 46GiB DB、不临场 DROP/VACUUM/删 WAL、不覆盖第三方 Run，所有生产写先有 exact contract/RPO/RTO/journal，失败先持久暂停。所有数值、路径、旧 Run 模板和容量都需 fresh evidence，不能继承 2026-08-20 快照。
- `test_acceptance_plan.md` 1–400 将测试划为 L0–L9，并明确“pytest 全绿”不等于 Gate：还需 red→green、mutation、fault、生产边界哨兵和独立审查。其 29 schema/115 DAG nodes/315 test IDs、v4 vector与 parser route 计数是旧候选合同，v5 必须从新规范闭包重新推导，不能把这些计数当现状。
- 可迁移的测试原则包括：全 tmp/无网络、生产 config/DB/source/Run sentinel、测试不递归清理宽目录、SQL old-query 只在有中止预算的 tmp DB、性能报告全样本和同协议、checkpoint 需新进程恢复、supervisor 用注入时钟/RNG、scanner/parser 各形状/route 独立验收。旧 test IDs 可作映射输入，但需检查当前代码与 v5 schema 后才能沿用。
- 测试计划 401–793 覆盖 LLM、retention、生产封装、E2E、A/B canary、两小时观察、12B/12C 与 reset 的稳定 ID/验收。它再次要求真实 provider 只在逐 provider 授权节点、生产操作逐个 D/OP/G、每个 cycle 新合同、独立 agent 不合并补签。表中的 315 项、ZR1005/ZR1006 路由和 ACT/START/JRN/BUD/PROC IDs 仍需当前代码/测试存在性核对；历史表不是执行结果，所有 Gate 都未因此自动通过。
- `traceability_matrix.md` 明确是 v4 规范映射而非动态完成台账，E01–E30 为 2026-08-20/22/31 的证据或审查反例，RQ-001–060、RK-01–44、Gate 数量和 ADR-02/11/13 都绑定 v4 registry/DAG。该映射应作为不可变历史输入；v5 当前入口必须建立新的 source-evidence freshness、requirement/test/gate/risk 映射，逐项决定 carry-forward、superseded 或需 fresh validation。
- 矩阵最后的规则直接支持用户的审查要求：每个新 requirement 先有唯一稳定 Test ID；实际 evidence/review/auth/state 只进 append-only ledger；任一 P0/P1 由对应独立 reviewer 在冻结 revision 上明确 CLOSED；prose 与 DAG/schema/registry 冲突时 fail closed 并新建 revision。V5-1 应继承这些规则但使用 v5 路径和 hash。

## 待完成

本子任务已逐行全文读取 baseline/plan 的 13 份 Markdown，共 6,691 行；表中每段输出均未截断。主任务对当前 v5 四份入口、reviews/history/investigation 及机器 JSON/schema 的审计另行负责，不重复计入本表。

## 最终处置结论

### 不应修改的不可变历史

- `baseline/plan/**` 是从退休 v1–v4 目录导入的审查输入；其中旧路径、旧 commit、旧行号、旧统计、旧 checker/manifest/DAG/test-registry 名称和历史 FAIL/待复审状态，应保持原字节以维持证据链。
- 不能把 `addressed in v4 draft` 改成 `CLOSED`，不能把旧 checker 的机械 PASS、import review PASS 或 manifest hash 等同于技术审查 PASS，也不能在 baseline 里把 V5-1/V5-2 勾成完成。
- 不应就地修正旧危险命令。它们应由当前入口明确标成历史/禁止直接执行；真正可执行命令只能在新的 v5 normative 文档、机器合同和冻结 manifest 中重建。

### 必须由当前 v5 活动入口承接的事实/门禁

1. 当前唯一状态仍是 `V5_BASELINE_READY / VERSION_CONTRACT_PENDING / NOT_IMPLEMENTATION_AUTHORIZED`；Phase V5-1 版本合同、V5-2 正式冻结与三路独立审查均 pending。
2. v5 必须枚举并闭合所有 prose、schema、instance、DAG、test registry、vector、CLI、validator、evidence/approval/journal/budget/runtime 合同；拒绝 v4/v5 混用、退休路径、旧 manifest 和残留 placeholder。
3. 历史根因与性能数字只作假设来源。当前入口必须重新验证代码漂移、SQL plan/语义、scanner 拓扑、parser routes、LLM backlog/provider 条款、容量、retention 与 control/status 写行为，再决定 carry-forward。
4. 每个关键节点独立 agent 审查仍是阻断式要求：实施型节点至少 D/G，生产动作 D→OP→G，高风险节点按新 DAG 固定 2/3 名角色；实施者/operator 不自审，初版 reviewer 不互读，证据变更使旧 PASS 失效，缺独立 reviewer 只能 BLOCKED。
5. worker 保持暂停且自启动关闭。生产只读、migration、journal init、canary、真实 provider、两小时观察、Run CAS、logoff、最终 activation、circuit reset 等均不得由本基线直接触发；未来即使 v5 技术审查通过，也仍须相应的用户授权。
6. 安全边界继续保留：source/config/StockWiki 不写；测试全 tmp/无网络；LLM 单线程；post-send outcome unknown 不自动重发；生产写 exact contract + journal + RPO/RTO；Registry zero-delete rollback；最终 runtime-template 与 activation 两次不同用户批准；每个后续 cycle 重新密封合同和重验 cap/auth。

### 本审计的结论边界

结论是 **BASELINE_MARKDOWN_SEMANTIC_COVERAGE_COMPLETE**。这只证明 13 份 Markdown 已完整阅读、历史与当前路由已分类；**不是 v5 技术 PASS，不是 v4 复审关闭，不是 plan freeze，也不是实施/恢复 worker 授权**。

## 主任务补充覆盖封板（2026-09-05）

下列不属于 `baseline/plan` 13份的 v5 当前入口、review、history 与 investigation 也已由主任务全文读取，并在封板时重新核对行数/SHA-256；它们均与本次 inventory 基线一致：

| 路径 | 行数 | SHA-256（前12位） | 处置 |
|---|---:|---|---|
| `README.md` | 48 | `23290db748a7` | 当前非实施入口；V5-1/V5-2 pending |
| `task_plan.md` | 65 | `ae2a8670f346` | 当前计划游标；不改本轮并行计划正文 |
| `findings.md` | 52 | `0021ec59b006` | 当前发现摘要；与基线分类一致 |
| `progress.md` | 60 | `24052c0e5cd7` | 当前进度；未宣称技术冻结 |
| `reviews/old-plan-retirement-result.md` | 54 | `b27a428ff32e` | 旧目录回收审查记录，只读 |
| `reviews/import-review-2026-09-03.md` | 48 | `baa64f7b4749c` | import机械完整性审查，只读 |
| `baseline/investigation/worker-investigation-2026-08-20.md` | 875 | `8e6166ba063b` | 历史根因/性能证据，不当作当前实测 |
| `baseline/history/v4-freeze-integrity-incident-2026-09-03.md` | 178 | `ede40ac40f7a` | v4冻结事故记录，只读 |
| `baseline/history/progress.v4.md` | 526 | `6c34d6da0162` | v4历史进度，只读 |
| `baseline/history/plan_review_revision.v4.md` | 147 | `7b489b8fb81e` | v4复审修订历史，只读 |

因此 v5 的 Markdown 语义覆盖由两部分闭合：本报告上文 `baseline/plan` 13份共6,691行，以及本节10份共2,053行。机器 JSON/schema/manifest 的完整性由 `verify_import.py` 与 import manifest 的54/54文件校验承担；机械校验不提升为技术评审或实施授权。
