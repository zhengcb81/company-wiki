# Source Catalog Worker 恢复计划 — 进度日志

## 2026-09-03 22:17–22:22 UTC（续接：v4 字节漂移阻断）

- 三名正式reviewer（SQL/性能、生命周期/安全、测试/DAG）均因账户用量限制中止，没有任何
  完整verdict；全部记为`INCOMPLETE_USAGE_LIMIT`，绝不计PASS。提示重置时点过后准备复审前，
  主agent重新执行冻结检查，发现新的独立阻断项，因此尚未重新派审。
- `plan_manifest.v4.json`自身SHA-256仍是
  `c34b849475f1efeb0a3237af2d4a748a6e36c276f7c91b6ad07cae8ea3004711`，但当前检查器输出
  `FAIL: 27 error(s) after 7696 checks`，27项均为`MANIFEST-BYTES`。
- 27个不匹配文件的LastWriteTimeUtc集中在`2026-09-03T21:29:17.252–266Z`；本任务冻结后只编辑
  excluded进度/审查日志，未执行这些normative文件的写入。当前Git HEAD已从冻结时变为
  `a0c7629`；工作树另有其他任务文件变化，未读取、恢复或改写它们。
- 只读字节诊断发现：16个文件将当前CRLF转换为LF后可精确复现冻结SHA-256；另外11个文件
  既不能用统一LF、也不能用统一CRLF复现冻结hash，可能与原先混合换行有关，但当前证据不足
  以断言它们只有换行变化。所有原文件、原manifest都保持原样，没有为求PASS重算覆盖hash。
- 当前v4状态改为**INVALIDATED_FROZEN_BYTES / NOT_IMPLEMENTATION_AUTHORIZED**；无论是否只有
  换行变化，v4都不能以当前工作树作为正式审查输入。后续必须保留v4历史，查清漂移后另建v5。
- 先继续只读调查变更来源和原字节可恢复性；未启动worker，未实施修复，未改注册表/配置/数据库。
- 本轮诊断已完成并新增`reviews/v4-freeze-integrity-incident-2026-09-03.md`：保存27文件完整原/现hash、
  delta、16项LF复现、11项剩余不确定性、pre_commit源码定位/校验值、4份相同patch证据和v5续接步骤。
- 真实安装的pre_commit使用整仓checkout再apply未提交patch；最新patch与27文件写入仅相差约1秒。
  四份最近patch均552211 bytes、同一SHA-256；内存重建证明现状规范化内容匹配保存的patch。
- 独立forensic reviewer `/root/v4_test_dag_review`已完整返回并确认上述因果链证据与限制；该结论
  不是v4/v5正式PASS。它另指出前后hash相同不能排除阅读期间checkout又恢复，故.gitattributes
  单独不足以保护并发审查；新冻结必须使用不受共享hook影响的稳定快照或先协调暂停并行提交。
- 当前没有添加.gitattributes、转换EOL、恢复旧文件或生成v5；仅新增上述诊断记录并更新两个excluded
  日志。采用当前11份尚未证明等价内容作为新基线前，需明确新快照边界并从零独立审查。
- 本轮末重新只读核验：control=paused；精确HKCU Run值absent；覆盖Python module调用形式后的目标
  进程、计划任务、服务、StartupCommand均NONE。查询成功，不把权限错误误报为NONE。
- forensic reviewer已回读保存的诊断报告并返回`FAITHFUL`，无需纠正；它实际确认的报告SHA-256为
  `ede40ac40f7afa35fbc27d00fd7aff6441cc54a9875b041dd6b1d82dd3306a6d`。该回读只确认摘要忠实性，
  不是正式Gate detached confirmation。报告在此确认后不再修改。
- 续接需要明确选择稳定的新基线/快照边界：建议保留当前共享目录不动，在另一个新的隔离子目录
  建立不会被当前tracked-file hook触及的v5快照，并把11份尚未证明等价内容当新基线从零审查；
  不自行把它们宣布为v4恢复，不影响另一个任务的源码/主线计划或Git配置。

## 2026-09-03（v4 已冻结，正式独立审查待完成）

- v4 的48份normative文件已经停止修改，并生成不可变`plan_manifest.v4.json`；manifest外部
  SHA-256为`c34b849475f1efeb0a3237af2d4a748a6e36c276f7c91b6ad07cae8ea3004711`，大小9598 bytes。
- 冻结覆盖为115个固定DAG节点、29个schema、315个稳定测试ID、18组/140个vector case、
  60个requirement、44个risk、105个计划审查finding；冻结时Git HEAD仅记录为漂移线索
  `16ef042f40cc85375d0de5196c654a9c027a6ef2`。
- 冻结前输出保存为`plan_freeze_check.v4.txt`，SHA-256为
  `ca47be86a15d94c68787c637d08567cdf57b2be51e27ee67f2cdff84b9137af7`；manifest生成后再次运行
  checker，仍为`PASS: 7696 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315,
  "vectors": 18}`，且明确不访问生产数据库、注册表、进程、source、配置或网络。
- 历史`plan_manifest.v3.json`重算SHA-256仍为
  `9ee84acdbe65a294925de004125f37b62b9e4b1c95655a04cd2344bc6bd270cc`，没有被覆盖或追加。
- 当前状态为**FROZEN_FOR_INDEPENDENT_REVIEW / NOT_IMPLEMENTATION_AUTHORIZED**；后续只允许
  更新排除在冻结集合之外的`progress.md`、`plan_review_revision.md`和未来review记录。若任何正式
  reviewer发现需要修改normative字节，必须把v4永久记为FAIL并另建v5，禁止原地修补。
- 下一步是让SQL/性能、生命周期/安全、测试/DAG可实施性三类独立agent分别重算同一manifest
  和冻结文件哈希并给出PASS/FAIL。所有agent明确PASS且无开放P0/P1前，不得开始任何实现。
- 本轮仍只写本隔离计划子目录；没有改动项目实现、生产配置、数据库、既有主线计划或其他线程
  文件，也没有恢复worker或自启动。

## 2026-09-03（继续 v4 冻结前加固）

- 继续使用 `planning-with-files`，仍只修改本隔离目录；worker/registry/生产数据/主线项目均不动。
- checker 已新增 exact filename→`$id` 映射、禁止 `$dynamicRef/$recursiveRef`、对 662 个 `$ref`
  执行真实 resolver lookup 并拒绝 scalar target，以及固定核验不可变 v3 manifest SHA-256。
- 修复 scenario fixture 的 UTC `20–23` 小时误拒和 `GLV-E###` 错误码格式后，当前机械检查为
  `PASS: 6711 checks; 113 fixed nodes; 26 schemas; 286 tests; 18 vector groups`。该 PASS 仍不含
  materialized scenario 正例，不能作为冻结或实施许可。
- 一个最终授权审查 agent 因账户用量限制中断，已按失败记录且不计 verdict；本日重新派出只读
  auth-DAG、vector mapping、prose 三路审计，等待结果时主 agent 继续修正 checker/合同。
- 复核不可变 `plan_manifest.v3.json`：它是旧 schema_version 1 格式，不应套用 v4 manifest 的
  `normative_files` 语义；只固定原字节 hash。未来 `plan_manifest.v4.json` 生成后必须走 v4 schema
  和独立的 count/path/hash/reparse 语义校验。
- 已把 vector fixture contract 升级为 composite scenario/materialized mutation v2，并修正 F04-G/H
  到 `/base_scenarios/*`。首次加 checker 断言时误写局部变量名 `vectors_doc`（实际为
  `vectors_document`），运行立即以 `NameError` fail closed；已按 traceback 精确修正，不掩盖错误。
- 修正后机械检查为 `PASS: 6712`。已从当前 schemas 提取准确字段图用于迁移 stale vectors：
  operation 使用 `db_writes.expected_prior_state/before_invariants/after_invariants/max_actual_touched_rows`、
  `path_supplement_policy`、外部 head anchor/commitment；auth/process/registry 均使用新 generation/
  ownership/branch tuple 字段。下一批不再沿用旧 pointer 名称。
- 已提取 bootstrap/registry/auth-revalidation/journal record/head/execution receipt/budget/scenario 的
  当前 root/def 字段，用于新增 GLV-E035+ 负例。读取 test registry 尾部时误把实际字段 `id` 写成
  `test_id`，只读脚本在输出首项后 `KeyError` 退出；未写文件。该次输出再次确认 G11A、G11J 的
  due test 均为 0，后续改用真实 `id` 字段补齐。
- vectors 已新增 materialization、bootstrap closure、schema registry、auth revalidation、journal
  record/head/execution receipt、atomic budget/settlement、process generation 的明确 reason codes/cases；
  当前 checker 为 `PASS: 6752`。这些是 T00L 必须物化的测试蓝图，不是伪造的现成 PASS fixture。
- 已核对当前 reset/provider/evidence 结构：reset 使用 `active_latch`、四类 provider
  `budget_states` 与 `history_state`，provider/data scope 为结构化数组，evidence secret 只能是
  `secret_scan_result=PASS_NO_SECRETS`。后续将据此替换旧 reset/scope/secret pointers。
- stale-case 替换表已落到当前字段：`db_writes`/typed `canonical_value`、registry
  `subject_user_sid/expected_prior_state/conflict_outcome/ownership_record_*`、journal
  `head_anchor_before_sha256/terminal_payload_template_commitment_sha256`、evidence
  `storage_kind/acl_snapshot_sha256/contains_secret`、reset nested latch/budget/history，以及 runtime
  cycle 直接使用 operation-contract root。exact-owned rollback 仍明确为 preserve，绝不恢复 delete。
- 已迁移上述 stale vectors，并按独立审计再修 primary-key tuple 层级、journal manifest 字段、held
  head anchor、bootstrap anchor、compensation receipt、schema-valid auth/cap mismatch；机械检查仍为
  `PASS: 6752`。两路审计随后因账户用量限制未返回正式 verdict，已保留其已发证据但不计 PASS。
- 双授权 DAG 的现有 reviewer override 已核对：D12C/G12C-PRE/G12C 角色明确，可无歧义插入
  `D12C-RT(2: llm_data_governance,runtime_operations)` 与
  `G12C-RT(3: llm_data_governance,control_security,release_security)`，并声明相邻 Gate reviewer
  disjointness。下一步同步 DAG、ledger node regex、证据与 dual-binding schema。
- 首次同时新增 approval schema/checker/README 的多文件 patch 因 hunk 分隔写法错误被
  `apply_patch` 整体拒绝，未产生部分写入；改为先单独新增文件、再精确更新映射与 README。
- 已新增严格 `user_approval_receipt.schema.json`：两种 purpose 条件互斥，runtime receipt 绑定
  D12C-RT/template/runtime auth/scope-cap，final receipt 绑定 D12C exact intent/contract/compensation、
  G12C-RT evidence 与前一 receipt，并要求 distinct approval IDs。尚待 DAG/OP/evidence 接线。
- 新 schema 纳入 exact-ID/README closure 后 checker 为 `PASS: 6805; schemas=27`。首次修改 DAG
  reviewer override 时按 pretty-printed 审计输出猜测多行格式，实际源文件该区是单行对象，patch
  上下文不匹配而整体拒绝；已读取真实字节，改用精确单行上下文，不重复同一失败方式。
- `gate_dag.v4.json` 已插入 `D12C-RT/G12C-RT`、两份不同 external approval prerequisite、精确
  reviewer roles/disjointness 和三条 dual-approval global invariants；D12C 现在只在 G12C-RT 通过后
  冻结 final exact intent。checker 的旧单授权断言尚未同步，下一次运行应先红。
- checker 同步后如预期先红，仅报 ledger node regex 拒绝两个新节点；已扩展 node/cardinality 规则，
  将 G12C-RT 固定为 3 reviewers、D12C-RT 固定为 2 reviewers，并增加相邻状态不变约束。
- 同时关闭独立 prose 审计发现的机器冲突：rollback Gate 不再共用错误枚举；G12B-RB 允许
  `PAUSED/OFF|PAUSED/ON|PAUSED/REGISTRY_CONFLICT`，G12C-RB 允许
  `LOGIN_VALIDATED_PAUSED/ON|PAUSED/OFF|PAUSED/REGISTRY_CONFLICT`。当前 checker 为
  `PASS: 6828; fixed_nodes=115; schemas=27`，但 evidence/OP dual binding 尚未接完。
- JSON 全域搜索确认剩余机器漂移集中在 evidence node regex、intent-template 的旧“D12C冻结”说明、
  authorization/operation/evidence 的 dual binding，而不是 DAG 本身。`evidence_manifest` 当前 artifact
  enum 也缺 `USER_APPROVAL_RECEIPT` 与 `OPERATION_INTENT_TEMPLATE`；下一步将它们变成显式路径/hash
  对并按 D12C-RT/G12C-RT/D12C/G12C-PRE/OP12C 条件收紧。
- evidence schema 已接入两个新 node ID、两个 artifact 类型和 `activation_authority_chain`，可分别
  承载 runtime template/auth/revalidation/approval、G12C-RT evidence、final exact intent/contract/
  auth/revalidation/approval 及 distinctness。当前 meta/closure checker 为 `PASS: 6852`；仍需把各节点
  的 null/present 阶段矩阵变成机器条件，并让 intent/contract 复述同一链。

## 2026-09-02（续接：v4 冻结前闭环继续）

- 已按 `planning-with-files` 重新完整读取技能说明，并重读 `task_plan.md`、`progress.md`、
  `findings.md`；当前仍是 **DRAFT_NOT_FROZEN / NOT_IMPLEMENTABLE**，没有开始项目实现。
- 本轮继续只修改本隔离计划目录；不接触并行线程的项目文件、现有主线计划、生产配置或数据。
- worker 继续维持上次已核验的暂停/禁自启动目标状态；本轮不执行 resume、registry 写入、任务/
  服务变更或任何实现动作。
- 当前优先闭环：真实 `$ref` registry 的 validator、规范文件闭包、复合 fixture/vector、双层最终授权、
  新增测试 ID 与 prose 同步；这些通过后才允许生成候选 v4 manifest 并启动固定字节独立审查。
- 已记录错误：首次追加本段时误用通用标题 `# 进度日志` 作为 patch 上下文，实际文件标题不同，
  `apply_patch` 因上下文不匹配而拒绝；随后读取实际标题并改用精确上下文，未产生部分写入。
- 闭包复核：目录现有 26 个 schema，旧 checker 只登记 16 个；另确认三个相对 external `$ref`。
  本机 `jsonschema 4.26.0` 与 `referencing.Registry/Resource/DRAFT202012` API 可用，下一步将以同一
  内存 registry 执行 meta/ref/instance 验证，不再用文件名模拟 URN 解析。
- 首次运行升级后的 checker 得到预期的先红结果：`5359 checks / 2 errors`；真实 registry 本身成功，
  暴露的是 `operation_contracts.schema.json` 仍要求旧 `JOURNAL_HEAD_BEFORE/EXACT_EGRESS/
  FOUR_DURABLE_BUDGET_RESERVATIONS`，而 instance 已使用 head anchor、exact request plan 和原子四计数
  bundle。已把 schema 常量同步到新的单向 journal/预算合同，待复跑确认。
- 同步后 checker 为 `PASS: 5360`（26 schemas）；已把 README schema 表扩为同一 26 项并加入集合
  相等断言。该 PASS 仍明确标为预冻结机械检查，不代表 vectors 或 prose 审查通过。
- vector 盘点得到 18 组、122 cases；其中大量 case 仍指向旧 intent/auth/registry/journal/runtime 字段，
  fixture contract 还写不存在的 `validator_fixture_manifest.v1.json`。已记录为 finding 58；下一步先
  升级 fixture/vector 的消费合同和基础错误码/时间格式，再按当前 schema 修复或替换 stale cases。

## 2026-08-22 — 计划编制启动

- 完成：读取用户明确指定的 `planning-with-files` 技能全文。
- 完成：确认新目录 `docs/plans/source-catalog-worker-recovery-2026-08-22/` 原先不存在。
- 完成：确认来源报告 `docs/worker-investigation-2026-08-20.md` 存在。
- 完成：创建独立的 `task_plan.md`、`findings.md`、`progress.md`。
- 边界：没有修改任何已有计划、代码、配置或主线文档。
- 当前阶段：计划编制，尚未开始任何修复实施。
- 完成：重新读取 `task_plan.md`、`findings.md` 和原始调查报告全文，并完成证据对齐。
- 用户澄清：不只是本次计划文档需要独立审查；实施计划中的**每个关键节点**都必须
  安排独立 agent 审查，并作为进入下一节点的强制 Gate。
- 决策：每个关键 Gate 至少指定审查角色、输入证据、审查清单、阻断级别、问题关闭
  规则和复审要求；实施 agent 不得兼任同一 Gate 的最终批准 agent。
- 下一步：整理详细文件级实施指南、逐节点审查矩阵、测试矩阵、canary/回退 runbook、
  追踪矩阵和弱模型任务提示模板。
- 完成：根据用户澄清，将逐关键节点独立 agent 审查写入 `task_plan.md` 的全局强制
  Gate；高风险节点要求至少两名不同视角 reviewer，最终审计至少三名。
- 完成：从原始报告与文件清单核对核心代码触点、启动链和可复用 contract tests；
  记录于 `findings.md`，尚未打开或修改这些实现文件。
- 完成：核对原报告恢复 runbook 与 `source_catalog_control.ps1` 的公开参数；发现 status
  路径可能写 control diagnostic log，已在 findings 中记录，后续 Gate 不会把它误称为
  对整个 `.source_catalog` 的绝对零写检查。
- 完成：新增本隔离目录的导航、详细实施手册、测试验收计划、逐节点独立 agent 审查
  协议、灰度/回滚 runbook、证据追踪矩阵和弱模型派工模板。
- 完成：对目录文件数、行数与 Gate 关键词做机械核对；当前共 10 份 Markdown、约 2,840
  行，Phase/WP 0–12、G11A/G11B/G12A/G12B 均有显式独立审查要求。
- 当前阶段：计划初稿完成，准备进行三路独立只读审查；仍未开始任何修复实施。
- 完成：机械一致性检查确认 10 个必需文档均存在、13 个 Phase、16 个细分 WP、全部
  production exit Gate 与 reviewer verdict 规则均可定位。
- 发现：Design Check 标题目前覆盖实施 WP 01–09，但生产 11A/11B/12A 的执行前独立审查
  还需要显式命名，以免“每个 WP 两个审查点”的规则被弱模型误读；列为初稿修订项。
- 工作树观察：除本新目录外还有 `.claude/settings.local.json` 删除、`llm_cost_log.csv`
  修改、`.coverage`、`coverage.json` 和来源报告等既有/其他线程状态；本次没有触碰，未来
  实施必须继续按 owner 隔离。Git 还报告用户级 ignore 与 `.pytest_cache` 权限警告。
- 修订：为生产只读对照、单周期 canary、两小时观察分别增加 D11A/D11B/D12A 执行前
  独立 Design Check；自启动继续使用 G12B-pre/post 两次审查。
- 修订：删除“在生产直接跑新旧查询”的歧义，明确旧灾难查询只允许在可中止的 tmp DB
  中用于红灯证据；生产仅运行有界新查询和独立分块参考实现。
- 检查：逐项列举 review 节点后，D00/G00、D01–D09/G01–G09、G10、D/G11A、D/G11B、
  D/G12A、G12B-pre/post 均存在。
- 检查：将来源报告章节与 traceability rows 对照；补入 8 月 12 日独立的重复实例/锁
  噪声证据 E20，并映射到 PID identity、resume race 和单实例测试，明确它不是 SQL 主因。
- 审查控制：SQL/性能 reviewer 发现初读后文件发生并发修订。已冻结 9 个核心计划文件为
  `plan_review_revision.md` v1；三路 reviewer 必须按 v1 hash 重读并签字。后续若修订核心
  文件，将生成 v2 并复审，避免 verdict 漂移。
- 完成：三路独立只读审查均核验 v1 hash 并返回 `FAIL`。共同 P0 是 Phase 12A 可能绕过
  真实 LLM 数据授权；另有 SQL primary-source 绑定、checkpoint 状态、生产 one-shot/
  migration/canary 写入、固定 revision、fail-closed control 和数值 SLO 等 P1/P2。
- 完成：将三份审查合并为 `plan_review_findings.md` 的 PR-001–035；全部先标为 accepted、
  pending re-review，尚无 finding 被自行关闭。
- 当前阶段：开始 v2 修订；生产 worker 和自启动状态不变，仍未实施修复。
- v2 修订进展：已新增唯一 Gate DAG、数值阈值合同；已把 primary-source/force、per-root
  checkpoint、LLM queue/cache、one-shot/pinned release、条件迁移、canary write/RPO、source
  权限拒写、global circuit、Job Object、LLM逐阶段授权、arm/CAS等写入核心计划。
- v2 机械搜索发现一处遗留“性能样本至少7次”，已统一为warm≥30/cold-ish≥10和
  nearest-rank/max合同；未发现旧的第四 reviewer verdict 或生产旧慢查询指令。
- v2 文件检查：本隔离目录现有14份Markdown、约3,850行；唯一Gate DAG明确包含G09P、
  条件G11M、G10R、arm-for-next-logon与registry CAS。
- v1遗留短语扫描只命中“禁止普通resume”的新安全说明、历史finding和progress记录；未
  发现仍把普通resume当12A入口、仍要求原live-worktree Run值、或仍保留第四reviewer verdict。
- v2 traceability机械检查：矩阵中51个显式test/performance ID均能在测试或阈值文档找到
  定义；14/14必需Markdown全部存在且非空。
- 修正内部一致性：每日1%无法在30天覆盖全量，已改为每日≥3.34%并保留30天最长rehash
  SLA；长期观察继续沿用OS/sandbox source写拒绝，不只做事后sentinel。
- 隐私修订：v2核心runbook不再硬编码本机用户名/项目绝对路径/原Run完整值，改为D Gate
  必填占位符与受限evidence核验；没有改动原始调查报告。
- v2安全控制覆盖扫描确认：核心计划均能定位primary-source、completed_with_errors、
  DDL-denying、Job Object、source permission deny、network deny与arm/CAS；敏感路径扫描只
  命中progress中的历史修订说明，核心文档已脱敏。
- 审查控制：12个核心文件已冻结为`plan_review_revision.md` v2并记录SHA-256；来源报告hash
  与v1相同。接下来只更新progress/manifest，不修改核心，等待三名原reviewer复审。
- 完成：三名原 reviewer 均逐项核验 v2 的 12 个核心文件和来源报告 hash，且均给出
  `FAIL`；审查期间没有 revision drift，也没有 reviewer 修改文件或生产状态。
- v2 阻断项：12B 长期真实 LLM 授权仍不完整；normalized/summary artifact 未与当前
  primary source/hash 绑定；`resume` 仍可能被误解为清除 circuit；canary allowlist 未收紧到
  operation/PK/column/exact file；pinned release 的 verifier 缺外部不可变信任锚；唯一 DAG
  对 WP-02B、G07-OFF、A1/A2/A3、Canary B 仍有缺边或矛盾。
- v2 其他清晰度/方法问题：WP-01 仍允许生产 seam；parser P95 缺按格式/size bucket 样本
  合同；若干需求仍使用非稳定 test 名；证据隐私规则冲突；registry 的“CAS”缺真实并发
  机制；SQL VM proxy 与 scanner 旧/新同拓扑基线不足；外部 provider crash 后不能声称
  exactly-once billing；核心计划与动态实施台账的 hash 冻结规则冲突。
- 决策：保持 v2 冻结直至三份结论收齐后再一次性创建 v3；v3 将修正全部开放项并重新
  进行三路独立只读复审，任何 P0/P1 未关闭都不交付为可实施计划。
- v3规范层完成：重写唯一Gate DAG；WP-01固定为无产品改动的T01→D01→G01；WP-02B拆成
  NI/IDX两条真实T/D/I/G分支；G07E/G07O互斥；A1/A2/A3与每个BP/BF provider均独立D/OP/G；
  G10C只到D11A，G10R只到D12A，12B增加PRE/ARM/CAS/POST审查。
- v3状态治理：新增`gate_ledger.schema.json`；规范性核心在revision内冻结，实施状态与证据
  仅进append-only/hash-chain ledger，`progress.md`只叙事，不再要求动态改task/findings/trace。
- v3安全/正确性：加入current source ID/SHA绑定和S1→S2测试；circuit三动作正交；canary
  operation+PK+column/exact-file precommit changeset；外部trust anchor+不可写完整release；
  真实registry条件并发；raw evidence approved sink/ACL/加密/TTL与secret永不采集。
- v3方法/性能：冻结SQL progress_n/PRAGMA/fixture；scanner同拓扑旧/新各n≥10；parser按格式/
  size bucket样本合同；provider crash使用OUTCOME_UNKNOWN ledger，不虚称exactly-once billing；
  12B启用LLM需全新stage-bound长期authorization且profile必须与G12A相同。
- v3追踪层：重写Requirement→稳定Test ID→精确Gate矩阵，新增Q-P、M-*、SC-S/P、P-FMT
  bucket、L-S18–21、PX-S12–19、EV-S、CAN-A1/A2/A3/BP/BF、OBS-S IDs；合并v2复审为PR-036–053，全部
  保持pending independent v3 re-review。
- v3机械一致性：拆分DOCX/XLSX/PPTX小/中bucket及corrupt/encrypted合并编号；当前189个稳定
  Test ID均被traceability引用，且矩阵没有未定义ID；RQ-001–046、RK-01–30、PR-001–053连续。
- v3账本：schema加入合法node ID、node type绑定、D/G reviewer下限、NOT_SELECTED分支状态、
  evidence path/hash配对与path traversal拒绝；Draft 2020-12 meta-schema和8个正/负样例全PASS。
- v3安全细化：Run模板改为先执行与release分离的trust anchor；request ledger把普通post-send
  timeout/含糊5xx归入OUTCOME_UNKNOWN，只有可证明未接受或同idempotency key才自动retry。
- v3冻结方案：活动revision将生成不可覆盖的`plan_manifest.v3.json`；ledger中的
  `plan_manifest_sha256`定义为该文件自身字节hash，避免以后向human manifest追加v4时破坏v3锚。
- v3已冻结：`plan_manifest.v3.json`列出13个核心文件并逐项MATCH；其文件SHA-256为
  `9ee84acdbe65a294925de004125f37b62b9e4b1c95655a04cd2344bc6bd270cc`，来源报告hash仍为
  `8e6166ba063bc281ca1fa5da3c0743b895e4d93b6f2957de3cbd0b6938a95be6`。
- v3独立复审已分别派给原SQL/性能、生命周期/安全、测试/DAG清晰度reviewer；三者必须从
  machine manifest重读、逐PR关闭并给唯一verdict，期间核心文件保持冻结。

## 2026-08-22 — v3 复审失败与 v4 草稿

- 完成：三名原领域reviewer均重算`plan_manifest.v3.json`自身、13个core及来源报告hash，
  全部MATCH；SQL/性能、生命周期/安全、测试/DAG可实施性三份verdict均为FAIL。v3已在
  `plan_review_revision.md`标为`REVIEW_COMPLETE_FAIL / HISTORICAL_ONLY`，永久禁止实施。
- 完成：将v3阻断反例登记为PR-054–066；在持续变化的v4草稿上进行第一轮只读预检，
  又登记PR-067–078。草稿预检不是正式verdict，修订者没有自行关闭任何finding。
- v4 DAG：建立`gate_dag.v4.json`及专用instance schema；现有113个固定T/D/I/OP/G节点、
  三个exactly-one ADR、两个实例family。未选分支不写ledger；固定依赖无悬空、无环。
- v4 review合同：每个固定D/G及family均有exact人数和role set；跨节点disjoint规则、机器
  `review_result`与detached `review_confirmation`均进入冻结输入。G自身保持只读。
- v4 operation合同：新增静态`operation_contracts.v4.json`、动态`operation_contract.schema.json`
  和`authorization_manifest.schema.json`；每个固定OP唯一匹配catalog，状态序列、generation、
  DB/file/registry/egress边界及REQUIRED/N_A_ALLOWED/BOUND_COMPENSATION可机器校验。
- v4生命周期：在首个生产写canary前加入`D11J→OP11J→G11J` protected write-intent journal；
  12B拆ARM/CAS/LOGIN，失败显式走预授权`OP12B-RB→G12B-RB`；12C先pre-review再OP，失败走
  `OP12C-RB→G12C-RB`。G12C不改变物理state，只记录`RECOVERED` lifecycle outcome。
- v4 circuit：每次reset仅走唯一`D05Rnn→OP05Rnn→G05Rnn`，绑定failure generation、exact
  ancestor D return与全部下游失效；reset不授予resume/arm/login/activation。
- v4测试控制：`test_id_registry.v4.json`现有283个唯一concrete ID和5个parser expansion
  template；活动文档引用按冻结regex提取，已消除范围缩写和未解析ID。validator规格含
  GL-S01..GL-S06、GL-F01..GL-F12共18组、每subcase唯一primary code。
- v4 schema：10个schema均通过Draft 2020-12 meta-check，并拒绝`{}`、`[]`、scalar；DAG、
  operation catalog、vectors、test registry四个instance均通过各自专用schema。
- 新增只读`plan_consistency_check.py`，不打开生产DB、不读写registry、不启动进程、不联网；
  最新运行PASS 3901 checks（113 fixed nodes、283 tests、18 vectors、10 schemas）。它不代替
  T00L未来validator实现或三路独立语义复审。
- 当前阶段：v4仍为`DRAFT_NOT_FROZEN`，`plan_manifest.v4.json`尚不存在。已向三名原reviewer
  派出第二轮只读预冻结反例检查；只有草稿阻断项清零后才生成一次性manifest并正式复审。
- 隔离边界：所有写入仍仅在本新目录；未修改产品代码、测试、生产配置、生产DB、自启动
  或worker状态，也未触碰其他线程的既有工作树变化。

## 2026-08-31 — 恢复计划编制会话

- 只读漂移核验：Git HEAD已由调查时`26a6b22f80ae964892d3f3f44fab364e65276583`前进到
  `9a00df609c16e99d153dbfbd3c41b4d5097f7c48`；区间内仅新增
  `tests/contract/test_zr1002_reader_first.py`与`tests/contract/test_zr1003_shadow_assertions.py`，
  没有目标worker/normalizer/store/scanner/control/supervisor文件差异。未来实施仍必须在Phase 0
  按当时HEAD重做symbol/impact/baseline，不得把本次观察当永久豁免。
- 来源与历史锚未漂移：调查报告SHA-256仍为
  `8e6166ba063bc281ca1fa5da3c0743b895e4d93b6f2957de3cbd0b6938a95be6`；不可变v3 manifest
  SHA-256仍为`9ee84acdbe65a294925de004125f37b62b9e4b1c95655a04cd2344bc6bd270cc`。
- v4计划目录自2026-08-22最后编辑后没有外部字节变化；`plan_manifest.v4.json`仍按合同不存在。
  重新运行只读一致性检查仍PASS 3901 checks。
- 只读安全复核：`worker_control.json.desired_state=paused`；精确进程查询未发现生产worker、
  supervisor或logon VBS进程；HKCU Run的`CompanyWikiSourceCatalog`值不存在；未发现匹配的
  Scheduled Task或Windows Service。首次受限CIM查询被拒且自匹配检查命令，随后经只读权限
  使用进程名+精确命令形态并排除自身复核为零；未停止或修改任何进程/入口。
- 已重新派出SQL/性能、生命周期/安全、测试/schema三名只读agent进行v4预冻结反例检查。
  在三份结果返回前保持核心草稿字节不变，不生成v4 manifest。

## 2026-08-31 — 用户要求在记录续接点后暂停

- 三名辅助 agent 在写入部分草稿后均因账户用量上限中断；它们没有提交可信完成结论，也没有
  获得 PASS。主 agent 已接管实际文件逐字节复核；这些草稿必须继续视为未审计输入。
- 中断前最近一次完整一致性运行曾为 `PASS: 5246 checks`（113 个固定节点、16 个 schema、
  286 个测试、18 组 vector）；其后又修改了授权语义，所以该 PASS 已失效，不能作为冻结证据。
- 新发现：长期 autostart 不可能在 G12C 时预先绑定未来每轮 exact intent。已把
  `authorization_manifest.schema.json` 首轮改为 `EXACT_INTENT` /
  `RUNTIME_TEMPLATE_SPECIALIZATION` 双模式，加入 runtime template、严格特化、per-cycle maxima、
  durable budget IDs、每轮 revocation check 和 drift reauthorization 触发器；JSON 语法检查为
  `JSON_OK`，当前文件 SHA-256 为
  `1a70f1de3fd8774697d4a04b7144b7a3afad4a0fdec453569bfe262b839de87a`。
- 重要未完成项：动态 operation contract、静态 runtime catalog、budget reservation、journal /
  evidence schema、validator vectors、prose 和 consistency checker 尚未与新授权模式完全对齐。
  当前 v4 是 `DRAFT_NOT_FROZEN / NOT_IMPLEMENTABLE`；没有生成 `plan_manifest.v4.json`，也没有
  开始正式独立复审。
- 基线再次前进至 HEAD `3713c9beaf7474c3746b84aae7215084179db743`；相对调查基线新增范围
  已包含 ZR1002、ZR1003、ZR1005、ZR1006 及 `TERMINAL_NOTICE.json`。均未触碰；下次先重做
  drift audit。
- 下次严格续接顺序：①重做只读 drift/worker 状态核验；②同步 exact/template 授权语义并增加
  durable budget reservation；③逐项审计 journal/evidence/fixture/vector/prose；④重跑完整 JSON、
  schema、instance 与跨文件检查；⑤只有全绿才一次性冻结 v4 manifest；⑥再由未参与编写的三名
  独立 agent 做零信任正式复审。任一 FAIL 则封存 v4 并进入 v5，绝不覆盖历史版本。
- 暂停边界：没有修改产品代码、项目测试、生产配置、数据库、注册表、自启动或 worker 状态；
  所有写入仍仅位于本隔离计划目录。worker 保持上次只读核验所得的 paused / no-autostart 状态，
  本次没有恢复它。

## 2026-09-01 — 从授权模型暂停点续接

- 已按 `planning-with-files` 跨会话规则重新读取技能全文，并确认只在本隔离目录继续。
- 尚未接受昨日任何中间 PASS：`authorization_manifest.schema.json` 的双模式修订还没有与
  dynamic contract、static catalog、budget reservation、vectors、prose 和 checker 完成对齐。
- 当前安全状态沿用最后一次只读观察，仍需在本会话重新验证；本条记录本身没有读取或修改
  worker、注册表、数据库、配置、项目代码或并行线程文件。
- 当前状态继续是 `DRAFT_NOT_FROZEN / NOT_IMPLEMENTABLE`；恢复后的首要工作是完整重读
  `task_plan.md`、`findings.md`、`progress.md`，随后执行 drift audit，而不是直接冻结。
- 分段重读已完成 `task_plan.md` 1–808 行及 `findings.md` 1–210 行。确认 Phase 12 的
  runtime-cycle prose 也仍按 future exact-intent 授权表述，属于发现37的同步修订范围；此外
  Phase 00L 的 stdlib-only 与 Phase 0/2 漏列 ZR1005/ZR1006 已登记为发现39。
- 已继续读完 `findings.md` 至 EOF，并重读 `progress.md` 1–160 行；历史 v1/v2/v3 FAIL、
  v4 不得自行关闭 finding、CAS/rollback/journal/source-binding 等约束均继续有效。
- 已读完 `progress.md` 至 EOF。首次 2026-09-01 drift check 确认 HEAD 与五文件差异未变、
  control=paused、HKCU Run absent；进程/计划任务/服务因权限拒绝而仍是 UNKNOWN，不能把空结果
  当作 NONE。下一步只读提权复核，不执行停止、注册表写入或任何项目修改。
- 获准的只读 Windows 复核已把上述 UNKNOWN 关闭：目标 worker/supervisor/logon 进程、匹配
  Scheduled Task、匹配 Service 均为 `NONE`；未执行停止或系统写入。普通 `git status --short`
  另显示并行线程新增 `.tmp-build-registry.py`，以及既有 `.claude`/cost/coverage/report 状态；
  本任务不读取、不修改、不归属这些文件。
- 原 checker 在新授权补丁后仍返回 `PASS: 5246`，但定向扫描同时证实 static catalog、dynamic
  contract 和 task prose 保留三处旧语义；该 PASS 已登记为覆盖不足而继续失效。发现41要求先
  新增会对当前草稿失败的跨文件断言，再完成同步修订并重跑。
- 首轮机器修订已新增 `operation_intent_template.schema.json`，将 per-cycle exact intent 与长期
  template authorization 分开，并在 dynamic contract/static catalog 加入四类 durable budget
  reservation、pre-egress durability 与 OUTCOME_UNKNOWN 保留最大费用的 settlement 规则。
  checker 仍显示16 schema/5246 checks，证明新文件未进入其闭包；已登记发现42，当前结果无效。
- 第二轮机器修订补入：fresh authoritative revocation receipt、runtime 唯一 action/禁止动作/
  固定状态序列、parent `preauthorized_compensations` 与 child selection、action canonical hash
  projection、process generation、read-only effect-empty profile、RESET 反向 node/auth 约束与
  provider-budget preserve 规则、provider request/retry/currency 和授权 TTL。22 个 JSON 文件均
  通过原始 JSON 解析；尚未完成 meta-schema、跨文件 checker、vector/prose 同步，不能视为通过。
- 继续补入 typed specialization receipt（避免 final-contract 自哈希循环）与 action projection hash；
  预审还确认 rollback 缺写前 no-op 和失败窗口 discriminator，已登记发现43，下一步补 static/
  dynamic branch machine contract。
- 2026-09-02 从保存点恢复：补入 `compensation_details` 的七个显式分支、registry
  `VERIFY_CONFLICT_PRESERVE`/`EXACT_OBSERVED_CONFLICT` DSL 与 bound-compensation 的副作用约束；
  当前22个 JSON 文件全部通过原始 JSON 解析。此结果只证明语法有效，不代表 schema、跨文件
  语义或安全性通过。
- 冻结前 prose/test 预审 agent 在额度中止前交付了三项可用发现：D12C 缺第二份 runtime-template
  用户授权 Gate、OP12B-ARM 的 prose post-state 与 catalog 不一致、G11A/G11J 测试绑定为空。
  该 agent 未形成完整最终审查，故这些仅作为待修订输入，绝不计作 PASS。
- 2026-09-02 启动三名新的只读独立预审 agent；启动/evidence 与授权/补偿两路已先报 P0。
  已将 bootstrap deadlock、入口前 `site` 执行、复合 fixture/journal schema 缺口、evidence/release
  closure、grant 笛卡尔积、budget reset、process generation、revocation freshness 等登记为发现44–47。
- 当前机器修订已为 OP12B/OP12C rollback 增加 pre-effect no-op static state、0/1 generation 选择、
  parent grant binding 和 branch discriminator；dynamic contract 增加 branch-selection receipt、
  forward-effect status、parent grant ID/hash、逐分支 trigger/state/generation/registry/control 约束；
  authorization 草稿增加 typed compensation grant 与 derived child source。三份已编辑 JSON 均再次
  通过原始 JSON 解析，但 grant 仍需从平行数组改为逐分支 tuple，不能视为安全闭环。
- 已把 static 多分支状态改为显式 `state_transition_options` tuple，修复 schema 重复 `oneOf`；旧
  checker 从 15 个 state/delta 错误回到 `PASS 5251`。该 PASS 仍是已知假绿，因为 schema closure、
  composite fixtures 与 stale vectors 尚未修复。
- compensation grant 已改为“一份 grant 只授权一个 branch contract”，不再把 trigger/branch/
  state 做非法笛卡尔积；新增第三方删除 Run value 后的 12B/12C absent-safe-off 分支。下一步必须
  取消或证明 atomic compare-and-delete，并把同一 grant 定义由 intent/auth 共享完整 URN ref。
- 三路预审新增的 journal hash cycle、budget atomic bundle、vector pointer 漂移、evidence auth/
  journal 缺口和 external head anchor 问题已登记为发现48–52；v4 仍是 `NOT_IMPLEMENTABLE`。
- 完成第一批 P0 机器合同重构：新增 bootstrap verifier、schema registry、authorization revalidation
  receipt、journal record、ledger head anchor、operation execution receipt、budget reservation bundle、
  budget settlement receipt、composite scenario fixture 共9份 schema；validator release/evidence/
  journal manifest/fixture manifest 升级为闭合版本。
- operation contract 已拆除 future journal hash 环、改用原子预算 bundle、修正 RESET provider budget
  守恒、为 read-only 强制 journal N/A，并取消不安全的 compare-then-delete。12B exact-owned rollback
  现在保留 Run value、禁用 control、终态 `PAUSED/ON` 等待显式人工 cleanup。
- 当前31个 JSON 文件全部通过原始解析；26个 schema 全部通过 Draft 2020-12 meta-schema 与 duplicate-key
  检查。外部 URN registry 实际解析、跨文件语义、vectors、prose 和 test registry 尚未同步，故仍
  不能冻结。

- 继续 v4 冻结前 P0 加固：把 evidence activation chain 改成四个机器可判定 phase，逐节点强制
  present/null 矩阵；D12C-RT/G12C-RT/D12C/G12C-PRE/OP12C/G12C 无法跳级或用未来工件填充。
- user approval receipt 已补 final authorization ID/path/hash 与 final subject digest；operation intent、
  authorization proposal、receipt、dynamic contract、evidence 和 post-operation receipt 形成单向、无环
  hash dependency。authorization manifest 明确不保存未来 user receipt hash。
- operation catalog/contract/runtime cycle 已要求 runtime-template approval、G12C-RT evidence 与 OP12C
  两份 purpose-bound receipt；ordinary autostart provenance 也必须含 dual chain。
- 新增 `gate_ledger_transcript.schema.json` 与 `validator_request.schema.json`，修复 `/records` 与 authored
  next-eligible 的无类型/不可物化问题；scenario roles 可区分双授权六类工件。
- vectors 保持 18 个固定 group，但新增 GLV-E044、2 个正例与5个双授权负例；修复 `/reviewers/-`、
  `/reviewers/0` 和 `/next_eligible_nodes` 失效 pointer，独立 reviewer reuse 覆盖 G12C-RT。
- test registry 从286增至315：新增 bootstrap/schema/fixture/auth-revalidation/journal/budget/process/
  dual-activation/startup 16项，逐函数纳入 ZR1005/1006 共13项；允许既有基线明确
  `expected_red_at=[]`，并为 G11A/G11J 建立 due obligations。
- 本批最终机械检查：`PASS: 7455 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315,
  "vectors": 18}`；仍是 `DRAFT_NOT_FROZEN / NOT_IMPLEMENTABLE`，因为 active prose 尚未全部同步、
  materialized fixtures 仍须由 T00L 生成、正式固定字节独立复审尚未开始。
- 双授权 schema 独立复核 agent 在重审时触发账户额度而中止；中止前发现并促成无环 proposal→receipt
  模型，但不记为 completed/PASS，冻结前必须另行完成正式固定字节审查。

## 文件变更记录

| 文件 | 操作 | 原因 |
|---|---|---|
| `docs/plans/source-catalog-worker-recovery-2026-08-22/task_plan.md` | 新增 | Phase、Gate、边界和全局验收标准 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/findings.md` | 新增 | 固化报告证据和待验证假设 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/progress.md` | 新增 | 跨会话进度、错误和测试记录 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/task_plan.md` | 更新 | 将每个关键节点的独立 agent 审查升级为强制 Gate |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/findings.md` | 更新 | 记录实施触点与既有测试基础 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/README.md` | 新增 | 隔离边界、文档导航和弱模型固定执行循环 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/execution_playbook.md` | 新增 | WP-00 至 WP-12B 的文件级执行手册 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/test_acceptance_plan.md` | 新增 | 测试层级、fixture、性能、故障和生产验收标准 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/agent_review_gates.md` | 新增 | 每个关键节点的 Design Check、Exit Gate 与 reviewer 清单 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/rollout_rollback_runbook.md` | 新增 | 生产只读、canary、观察、自启动与回退顺序 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/traceability_matrix.md` | 新增 | Evidence→Requirement→Test→Gate→Risk 追踪 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/implementation_agent_prompts.md` | 新增 | 实施、设计审查、退出审查和复审派工模板 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/plan_review_revision.md` | 新增 | 冻结独立计划审查的文件 hash revision |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/plan_review_findings.md` | 新增 | 三路 v1 审查 findings、优先级、处置和复审状态 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/gate_ledger.schema.json` | 新增 | 冻结动态Gate账本的node/verdict/hash-chain记录合同 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/acceptance_thresholds.md` | 新增 | 冻结统计、SLA、安全、授权和canary数值合同 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/gate_state_machine.md` | 新增 | 冻结唯一执行DAG与合法节点/分支状态 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/plan_manifest.v3.json` | 新增 | v3 13个核心文件与来源报告的不可变machine manifest |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/plan_review_findings.md` | 更新 | 固化三路 v3 FAIL 及 PR-054–066；开始 v4 修订，未自行关闭 finding |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/gate_dag.v4.json` | 新增 | v4唯一机器DAG、分支、family与exact reviewer规则 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/gate_dag.schema.json` | 新增 | 严格验证DAG instance shape |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/review_result.schema.json` | 新增 | 独立reviewer exact node/role/head/hash/verdict合同 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/review_confirmation.schema.json` | 新增 | reviewer回读已存JSON/Markdown的detached确认 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/operation_contracts.v4.json` | 新增 | 每个固定/族OP的静态授权、状态与副作用策略 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/operation_contracts.schema.json` | 新增 | 静态operation catalog instance schema |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/operation_contract.schema.json` | 新增 | 每次OP/cycle/reset的sealed动态合同 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/authorization_manifest.schema.json` | 新增 | stage-bound用户授权、provider/data/cap/expiry/revocation合同 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/ledger_validator_contract.md` | 新增 | fail-closed validator、bootstrap、hash-chain与稳定错误码 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/gate_ledger_validator_vectors.v4.json` | 新增 | 18组validator正负向量与逐case primary code |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/gate_ledger_validator_vectors.schema.json` | 新增 | validator vector instance schema |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/test_id_registry.v4.json` | 新增 | 283个逐ID lifecycle映射、parser template与引用语法 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/test_id_registry.schema.json` | 新增 | test registry instance schema |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/parser_route_manifest.schema.json` | 新增 | 实际parser route/profile hash与展开ID合同 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/plan_consistency_check.py` | 新增 | 无副作用的预冻结跨文件一致性检查器 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/gate_ledger_transcript.schema.json` | 新增 | 固定可物化ledger transcript instance合同 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/validator_request.schema.json` | 新增 | 固定validator入口请求、双授权与head-anchor参数合同 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/plan_freeze_check.v4.txt` | 新增 | 保存冻结前只读检查器的精确UTF-8/LF标准输出 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/plan_manifest.v4.json` | 新增 | 冻结48份normative文件及覆盖计数的一次性machine manifest |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/plan_review_revision.md` | 更新 | 记录v4 manifest外部hash、冻结后复核与正式审查状态 |
| `docs/plans/source-catalog-worker-recovery-2026-08-22/progress.md` | 更新 | 记录v4冻结事实与后续只读正式审查进度 |

## 测试/检查结果

| 检查 | 结果 |
|---|---|
| 新目录预先存在 | 否；避免覆盖已有计划 |
| 来源报告存在 | 是 |
| 实施代码变更 | 无 |
| 生产配置变更 | 无 |
| worker 恢复运行 | 未执行，应继续保持暂停 |
| 现有项目/主线计划被修改 | 否；所有写入均位于新隔离目录 |
| 逐关键节点独立 agent Gate 覆盖 | v4冻结版115个固定节点；每个D/G及两个family实例均有exact role/cardinality，等待正式独立复审 |
| 稳定Test ID→活动引用完整性 | 315/315唯一；5个template；活动来源无未解析ID或范围缩写 |
| JSON Schema/instance | 29个 schema 全部 Draft 2020-12 meta PASS、`$id`/real `$ref` registry 闭合；4/4 static instance PASS |
| 只读跨文件一致性 | 冻结时7696 PASS；本轮末7696项中27个MANIFEST-BYTES失败，v4已失效 |
| 必需计划文件存在性 | v4 manifest精确冻结48份normative文件；动态ledger/evidence/reviews/decisions尚不应创建 |
| v3 core/source manifest核验 | 13/13 MATCH；source MATCH；manifest SHA已写入revision记录 |
| v3独立复审 verdict | SQL/性能 FAIL；生命周期/安全 FAIL；测试/可实施性 FAIL；v3禁止实施 |
| v4修订状态 | INVALIDATED_FROZEN_BYTES / HISTORICAL_ONLY；三路正式审查均额度中止，forensic预审完成但不计正式PASS |
| 当前工作树仅含本任务变更 | 否；有明确不属于本计划的既有/并行变更，未触碰 |

## Errors Encountered

| 错误 | 尝试 | 处理 |
|---|---:|---|
| 首次更新 `progress.md` 时补丁上下文与实际文件不一致 | 1 | 读取实际内容后使用精确上下文更新；未影响其他文件 |
| 为生产节点补 Design Check 时首次补丁尾部上下文不匹配 | 1 | 读取精确段落后更新；未影响实现或其他计划 |
| 批量修订 execution playbook 时一个尾部上下文与实际文本不匹配 | 1 | 整个补丁未应用；分段读取并逐块精确更新 |
| 批量修订 review Gate 时 G01 上下文格式不匹配 | 1 | 整个补丁未应用；读取精确段落后更新 |
| 批量修订 rollout canary 时停止条件上下文顺序不匹配 | 1 | 整个补丁未应用；读取精确段落后分块更新 |
| 批量修订 agent prompt 时目标句与实际措辞不一致 | 1 | 整个补丁未应用；读取精确段落后更新 |
| 并行读取 `rollout_rollback_runbook.md` 时单个 PowerShell range 被展开为标量，`Math.Min` 参数类型不匹配 | 1 | 该读取未产生写入；后续改用显式起止范围单独读取 |
| 同一 `apply_patch` 同时Delete/Add `gate_state_machine.md`被拒绝为重复target | 1 | 无修改发生；随后用两个apply_patch调用删除旧版并立即新增完整v3 |
| execution playbook补丁误把显示行号`50:`写入匹配上下文 | 1 | 整个补丁未应用；去除行号后按实际文本成功更新 |
| WP-10批量补丁第二段实际措辞与预期不一致 | 1 | 整个补丁未应用；读取精确段落后重新更新 |
| ledger schema首轮负例没有拒绝`evidence/../manifest.md` | 1 | 将path segment改为必须以字母/数字开头；复跑8个正负样例全部PASS |
| 两次编辑`gate_ledger.schema.json`时漏配对闭合括号，JSON解析失败 | 2 | 每次均仅影响v4草稿；补齐括号并重跑全部JSON/meta/instance检查 |
| `rg`默认regex不支持look-ahead | 1 | 未写文件；后续需要时改用`--pcre2`或无look-ahead表达式 |
| Windows把路径尾部`*.md`当非法文件名 | 2 | 未写文件；改用`rg -g '*.md' <directory>` |
| 首个DAG检查脚本假设节点键为`node_id`，实际为`id` | 1 | 未写文件；读取instance shape后修正只读检查 |
| 原子替换traceability草稿期间reviewer短暂看到文件缺失 | 1 | 文件立即由`apply_patch`恢复；未冻结该瞬时版本，reviewer按后续稳定字节重读 |
| 外部`$ref`检查命令被PowerShell展开`$id`/旧RefResolver接口干扰 | 2 | 未写文件；最终在只读Python检查器中按JSON pointer直接核验本地ref |
| PowerShell`[Math]::Min`收到数组导致只读取行失败 | 2 | 未写文件；改用显式整数范围 |
| vector探查脚本误假设顶层字段`purpose` | 1 | 未写文件；先打印真实keys，再按`id/kind/cases`核验 |
| 长内联Python一致性命令被PowerShell quoting解析失败 | 1 | 未写文件；改为本隔离目录内可审计、只读的`plan_consistency_check.py` |
| lifecycle默认值补丁上下文不匹配 | 1 | 整补丁未应用；读取compact JSON精确上下文后成功 |
| test ID extraction regex的`\\d`被JSON过度转义为字面反斜杠 | 1 | 反例仅匹配`P-FMT01-S`；改为真实`\d`并加入固定三token自测，现PASS |
| 拆分Canary A operation policy的首次补丁未匹配compact JSON | 1 | 无修改发生；读取精确片段后拆为A1/A2/A3三个exact catalog项 |
| 2026-09-01 合并读取三份跨会话planning文件超过工具输出上限 | 1 | 只读输出被截断、文件未受影响；改为按固定行段逐份读至EOF，不重复整包读取 |
| `git -c core.excludesFile=NUL status --short` 在 Windows 拒绝 NUL | 1 | 未写文件；后续使用普通 `git status --short` 并单独解释用户级 ignore 权限警告 |
| 受限会话读取 Win32 Process/Scheduled Task/Service 被拒绝，空变量误显示 NONE | 1 | 明确把三项状态记为 UNKNOWN；改用只读授权查询，禁止引用该 NONE 行作证据 |
| 2026-09-01 一次性加入 registry/compensation branch 的大补丁末段上下文错误 | 1 | `apply_patch` 整包未应用、JSON 未半改；改为 registry DSL、compensation def、node conditions 三个小补丁并逐次解析 |
| 2026-09-01 冻结前 prose/test 预审 agent 因账户额度中止 | 1 | 保留其中止前已返回的三项具体发现；不把该 agent 计为完成或通过，修订后重新派独立 agent 全量审查 |
