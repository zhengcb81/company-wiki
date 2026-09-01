# Source Catalog Worker 恢复计划包

> 状态：**仅规划，未实施；v4 候选须经三路冻结版本复审后才可能成为实施输入**  
> 隔离目录：`docs/plans/source-catalog-worker-recovery-2026-08-22/`  
> 生产状态：worker 应保持 `paused/stopped`，登录自启动应保持关闭  
> 合并状态：不加入现有主线计划、索引或 roadmap；等待以后单独决定

## 1. 这个目录解决什么问题

本计划包把 `docs/worker-investigation-2026-08-20.md` 中已经建立的证据链，转换成可由
后续 agent 分阶段执行、测试、审查、回退的实施说明。它主要处理：

1. normalize queue SQL 从 2026-08-12 起发生的灾难性性能退化；
2. scan checkpoint、heartbeat、watchdog、restart reset 共同形成的无限慢循环；
3. 扫描器、LLM、容量和运维方面在主故障修复后会显现的后续瓶颈；
4. 在恢复生产运行及登录自启动前所需的安全、证据与人工授权链。

本目录本身不是修复提交。创建本目录不表示批准修改代码、生产数据库、生产配置、
自启动项或任何源文件。

## 2. 文档导航

| 文件 | 用途 | 实施者何时读取 |
|---|---|---|
| `task_plan.md` | 总目标、Phase、全局 Gate、状态 | 每次会话开始、每次阶段切换前 |
| `findings.md` | 已证实事实、基线和待验证假设 | 每次会话开始；代码漂移后重读 |
| `progress.md` | 跨会话进度、命令、错误和状态 | 做任何新工作前；结束会话前更新 |
| `execution_playbook.md` | 每个工作包的精确执行顺序、禁区与交付物 | 执行对应 Phase 前完整阅读该工作包 |
| `test_acceptance_plan.md` | 测试层级、数据夹具、性能统计、通过标准 | 写测试前；提交 Gate 前 |
| `agent_review_gates.md` | 每个关键节点的独立 agent 角色、清单和阻断规则 | 每个 Phase 开始和结束时 |
| `gate_state_machine.md` | 机器 DAG 的规范性人类可读投影、状态转换和条件分支 | 理解流程；不得据此替代机器计算 |
| `acceptance_thresholds.md` | P95 算法、SLA、circuit、scan/LLM/canary 数值阈值 | 写 assertion 或批准 Gate 前 |
| `rollout_rollback_runbook.md` | 只读生产对照、canary、观察、暂停与回滚 | Phase 11–12；此前仅作设计参考 |
| `traceability_matrix.md` | 报告证据 → 风险 → 变更 → 测试 → Gate | 每个 Gate 做覆盖率核对时 |
| `implementation_agent_prompts.md` | 给实施/测试/审查 agent 的封闭式任务模板 | 每次派工时复制并填满占位符 |
| `gate_dag.v4.json` | v4 唯一机器 DAG、前驱表达式、分支与 reviewer 人数 | 计算任何合法下一节点前 |
| `gate_dag.schema.json` | 机器 DAG instance 的严格 shape schema | 接受 DAG 前 |
| `gate_ledger.schema.json` | 动态 Gate 台账单记录的机器 schema；规范性、随计划 revision 冻结 | 创建/校验任何 ledger record 前 |
| `review_result.schema.json` | 独立 reviewer 的机器可读 payload 合同 | 派审与接收 verdict 前 |
| `review_confirmation.schema.json` | reviewer 对已保存 JSON/Markdown 的 detached 回读确认 | 把 review 写入 ledger 前 |
| `operation_contracts.v4.json` | 每个 OP/family 的静态授权、状态、写入、registry 与 egress 策略 | 冻结动态操作合同前 |
| `operation_contracts.schema.json` | 静态 operation catalog instance schema | 接受 catalog 前 |
| `operation_contract.schema.json` | 每次真实 OP/cycle/reset 的 sealed 动态合同 schema | D Gate 和 OP 前后 |
| `operation_intent_manifest.schema.json` | D Gate 先冻结的 exact action/registry bytes/generation/contract digest | 用户授权前及每个 OP/cycle 前 |
| `authorization_manifest.schema.json` | stage-bound 用户授权、范围、cap、expiry/revocation schema | 任何 REQUIRED OP 前 |
| `journal_manifest.schema.json` | protected intent/finalize journal 的路径、ACL、head 与恢复合同 | OP11J、每个 mutating OP/cycle/reset 前 |
| `evidence_manifest.schema.json` | machine-readable evidence 清单、artifact hash/HMAC、ACL/TTL 与敏感性合同 | 每个 terminal record 和 reviewer 前 |
| `validator_fixture_manifest.schema.json` | validator canonical fixture、typed mutation 和唯一 primary rule 清单 | T00L/D00L/I00L/G00L |
| `validator_release_manifest.schema.json` | validator 解释器、隔离 venv、依赖树、入口和测试 exact hash | I00L 生成、G00L 回读 |
| `parser_route_manifest.schema.json` | 当前 parser route 与实际展开测试 ID 的冻结合同 | parser 测试与 release join 前 |
| `ledger_validator_contract.md` | 隔离且依赖逐 hash 冻结的 validator、hash-chain、错误码、bootstrap 与 fail-closed 合同 | 创建首条 ledger 前；每次 append/next 前 |
| `gate_ledger_validator_vectors.v4.json` | validator 正负测试向量规格 | 实现 validator 与每次 self-test 时 |
| `gate_ledger_validator_vectors.schema.json` | validator vectors instance schema | 运行 vectors 前 |
| `test_id_registry.v4.json` | 唯一稳定测试 ID、owner、due Gate 与样本合同 | 写测试、映射 Gate 或验收前 |
| `test_id_registry.schema.json` | test registry instance、逐 ID 生命周期与引用语法 schema | 接受 registry 前 |
| `plan_manifest.schema.json` | v4 freeze manifest 的严格 shape、source hash、核心文件与预冻结检查合同 | 生成 `plan_manifest.v4.json` 前 |
| `plan_consistency_check.py` | 只读预冻结检查：JSON/schema、DAG、reviewer、OP catalog、test ID、vectors 与引用闭包 | 每次冻结候选、接收审查结论或核心文件变化后 |
| `plan_manifest.v4.json` | 仅由冻结步骤生成；冻结前不得预创建。冻结后列出 v4 核心文件/source hash，自身 hash 是 ledger 的 `plan_manifest_sha256` | `plan_review_revision.md` 明确 FROZEN 后每次领取节点、审查或重建状态前 |
| `plan_manifest.v3.json` | 已失败 v3 的不可变历史清单，不得覆盖或当作活动输入 | 审计历史时 |
| `plan_review_revision.md` | 当前计划独立审查的冻结 hash | 接收或复核计划审查前 |
| `plan_review_findings.md` | v1–v4 审查问题、处置和待复审状态 | 计划修订与复审时 |

未来实施的**非敏感、已脱敏**证据只允许放入本目录下新建的：

- `evidence/Gxx-*/`：命令、测试、benchmark、diff、环境和 hash；
- `reviews/Gxx-*/`：独立 agent 的只读审查报告与复审结果；
- `decisions/`：只有 Gate 明确要求时才创建的 ADR。

secret、token、cookie、credential 和 `.env` value **永不采集或落盘**；“放在 repo 外”不构成
采集许可。正文默认也不采集；确有不可替代需要时，必须先取得用户对用途、最小范围和保留
期的单独批准。获批的敏感 raw evidence 只能写入 D Gate 冻结的 approved sink：绝对路径位于
repo/workspace/普通 `%TEMP%`/云同步目录之外，无 reparse escape；ACL 只允许批准的 SID，静态
加密密钥不与 evidence 同处。默认在 Gate 最终处置后 7 天删除，且采集日起硬上限 30 天；
未完成 Gate 到期即 `BLOCKED` 并重新取证，除非用户批准 audit hold。仓内只记录 opaque ID、
脱敏统计和不可逆验证标识；可猜测的敏感 manifest 使用 repo 外密钥的 HMAC，不公开原始
SHA-256。Reviewer 只能在获批环境中核验，不得把敏感内容复制回本目录。

在用户要求并入主线前，不得把这些内容链接进现有计划索引。

## 3. 约束优先级

发生冲突时按以下顺序处理，并采用更保守的解释：

1. 用户在实施当时给出的明确指令；
2. 仓库根 `AGENTS.md` 与安全/权限规则；
3. 活动 `plan_manifest.vN.json` 所冻结的机器合同：machine DAG/instance schema、ledger/review/
   confirmation schema、operation catalog/dynamic contract、intent/authorization/journal/evidence、
   validator release/fixture、test registry、vectors 与 `ledger_validator_contract.md`；
4. `task_plan.md` 的范围、不变量和强制 Gate；
5. `gate_state_machine.md` 对机器 DAG 的人类可读解释；
6. `agent_review_gates.md` 的独立审查与阻断规则；
7. `acceptance_thresholds.md` 和 `rollout_rollback_runbook.md` 的数值/生产保护规则；
8. `execution_playbook.md` 与 `test_acceptance_plan.md`；
9. 本计划中的示例命令和 2026-08-22 文件定位。

机器合同与 prose 若不一致，不得自行选择“较像正确”的一方；validator 必须返回稳定错误码，
当前节点转 `BLOCKED`，由新的计划 revision 修复并重新独立复审。

代码和配置可能变化。示例路径可用于定位，但实施者必须在每个 Phase 0 重新检查实际
符号、调用链、Git 状态与并行任务；不得仅凭旧行号编辑。

## 4. 弱模型也必须遵守的单阶段执行循环

后续 agent 每次只领取一个 Work Package，不得跨 Phase 顺手修改。固定循环如下：

1. 完整读取 `task_plan.md`、`findings.md`、`progress.md` 和当前 Work Package；先用操作系统
   原生 SHA-256 验证活动 `plan_manifest.vN.json` 自身 hash 及其列出的每个核心文件/source
   report hash。
2. 若尚未完成 `T00L→D00L→I00L→G00L`，只能执行 validator bootstrap；不得创建正式
   `D00` ledger。完成后，每次 append/next 都必须由 validator 校验整链、external expected-head、
   review payload 与 DAG，不得信任 ledger 自报下一边或手抄 verdict。
3. 验证 ledger 记录的 `plan_revision/plan_manifest_sha256`、上一个 Gate 签字与证据 hash 匹配，
   且没有开放 P0/P1。
4. 记录 Git HEAD、分支/worktree、`git status --short`、时间和 worker 隔离状态。
5. 检查另一个任务是否正在改同一文件；有重叠时停止，不覆盖、不 stash、不 reset。
6. 用 CodeGraph 核对符号、调用者、被调用者和影响面；用 `rg` 只查字面文本或日志。
7. 在 tmp 配置、tmp root、tmp catalog 中先补能重现问题的失败测试，形成 test-only `Txx`
   commit；不得把实现混入。WP-01 是唯一 `TEST_BASELINE_ONLY` 例外，合法链为
   `T01→D01→G01`，不得改产品代码；需要的 production seam 归入 `I02A`。
8. 运行最小测试，证明它因本阶段目标缺陷失败，并通过 Dxx 独立审查；Dxx 后测试变化会
   使审查失效。
9. 只做当前 Work Package 列出的最小实现，形成 `Ixx` commit；禁止搭便车重构或格式化
   无关文件。
10. 运行最小测试、相关 contract tests、mutation/故障注入和必要的完整回归。
11. 检查 `git diff --check`、`git diff --stat` 和逐文件 diff；解释每一行变更。
12. 检查生产配置、生产 catalog、源目录、worker 状态和自启动状态均未意外变化。
13. 在 `evidence/Gxx-*` 生成通过 `evidence_manifest.schema.json` 的 `manifest.json` 和人类可读
    `report.md`；raw evidence 必须遵守上面的 approved sink/
    ACL/加密/TTL 规则，secret 永不采集。
14. 派出该 Gate 规定的独立审查 agent；reviewer 只读，不得替实施者改代码。
15. 若有 P0/P1，停止推进；修复后重跑受影响测试并要求独立复审。
16. 规范性核心计划在 revision 内保持不可变。Gate 事实只追加到符合
    `gate_ledger.schema.json` 的 `gate_ledger.jsonl`，叙事写 `progress.md`；不得更新
    `task_plan.md`、`findings.md` 或 `traceability_matrix.md` 的状态。只有计划语义变化才创建
    新 revision、写入新的`plan_manifest.vN.json`（不得覆盖旧manifest），并让下游Gate失效。
17. 会话结束前写明下一步、剩余风险、开放 P2/P3、可恢复点和禁止事项。

## 5. 立即停止的条件

遇到以下任一条件，当前 agent 必须停止实施、保持 worker paused，并把事实写入
`progress.md`，不得自行猜测继续：

- 找不到或无法验证上一个 Gate 的独立审查；
- 生产 worker、supervisor 或 parser 意外运行；
- HKCU Run、计划任务或服务出现未经解释的启动入口；
- 目标文件有无法归属的未提交改动，或与另一个任务发生重叠；
- 测试触及 `config/source_catalog.yaml`、生产 `.source_catalog` 或真实源目录；
- C 盘空间低于当前阶段预先计算的安全下限；
- 需要删除备份、运行 `VACUUM`、创建大索引、改 ACL、发送真实全文给外部 LLM，
  但没有对应 Gate 和用户授权；
- 同一失败连续三次仍无新证据；此时按 planning-with-files 的三次失败协议升级；
- 任何 P0/P1 审查发现尚未由独立 reviewer 关闭。
- validator 根据 `gate_dag.v4.json` 未开放当前节点，或数值阈值尚未在 D Gate 冻结；
- canary 无 OS/sandbox 级 source 写拒绝、无当前 RPO/RTO，或真实 LLM/备选 provider 未获
  单独授权；
- canary 写合同没有精确限定 operation、PK、column、exact file 与 pre-commit changeset，
  或只能用净 row-count/事后备份发现越界；
- 登录入口的首段非 OS 代码或 verifier 位于可写 worktree、被验证代码自行验证自身，或
  无法排除 verifier tamper/check-load TOCTOU；
- `resume`/`resume-session`/`arm-for-next-logon` 在 circuit open 时未 fail closed，或任一动作
  可顺带清 circuit；
- 12B 的 LLM 模式与 G12A 已观察 profile 不同，或启用模式缺该阶段全新的、绑定 release/
  provider/data/cap/expiry 的 authorization manifest；
- control/circuit 状态缺失或损坏；受管生产必须 fail closed，不能按 enabled 猜测。
- validator/schema/DAG/test registry 任一 hash、JSON、语义或 expected-head 校验失败；不得手工
  编辑 ledger 使其“看起来通过”。
- Canary B 任一 run 或 12A 任一 cycle 缺 exact write contract/precommit/post-read，或合同在
  周期中扩展 document、PK、column、path、provider、字符/成本范围。
- `ARMED_ON_PRELOGIN/ON` 在没有一次性 `LOGIN_COMMITTED` 时启动任何 child、访问 DB/source、
  建立网络连接，或 `OP12C` 在当前 session 启动 worker。
- 任一 OP 无法在静态 catalog 中唯一匹配、动态 operation contract/auth manifest 未通过 schema
  与 hash/expiry/revocation 检查，或 12B/12C 失败没有进入显式 OP compensation + 只读 G。
- operation intent、authorization、dynamic contract、journal head 和 evidence machine manifest
  不能逐 hash 闭合，或 authorization kind/action/stage/generation/scope 有任一漂移。
- Windows Run value 的 create-if-absent 无法用两进程竞争、第三方替换和 crash 注入证明线性化；
  existing-same-bytes 不得冒充本次成功，read-then-write/mutex 推测不得代替证据。
- G12C 后任一登录 cycle 在副作用前没有新的 sealed cycle contract，或没有重验授权、daily/monthly
  durable cap、journal head、Run ownership 和 process/control generation。

## 6. 本次计划编制的完成标准

- `python docs/plans/source-catalog-worker-recovery-2026-08-22/plan_consistency_check.py` 只读运行并
  `PASS`；它只证明机械合同自洽，不能替代三类独立 agent 的语义/反例审查；
- 所有规划文档只存在于本新目录；
- 没有修改代码、测试、配置、生产数据、现有计划或计划索引；
- 每个关键节点都具有独立 agent 审查安排；
- A1/A2/A3、每个真实 LLM provider canary、12A、12B ARM/CAS/LOGIN/POST、最终激活以及每次
  production circuit reset 都有独立且唯一的 D/OP/G（或只读 G）节点，不能事后合并签字；
- 各工作包都有前置条件、精确动作、测试、证据、停止条件、回滚点与 Gate；
- 后续可以由低上下文或较弱模型一次领取一个任务安全执行。
