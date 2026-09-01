# Source Catalog Worker 恢复计划 — 进度日志

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

## 测试/检查结果

| 检查 | 结果 |
|---|---|
| 新目录预先存在 | 否；避免覆盖已有计划 |
| 来源报告存在 | 是 |
| 实施代码变更 | 无 |
| 生产配置变更 | 无 |
| worker 恢复运行 | 未执行，应继续保持暂停 |
| 现有项目/主线计划被修改 | 否；所有写入均位于新隔离目录 |
| 逐关键节点独立 agent Gate 覆盖 | v4草稿113个固定节点；每个D/G及两个family实例均有exact role/cardinality，等待冻结版正式复审 |
| 稳定Test ID→活动引用完整性 | 283/283唯一；5个template；活动来源无未解析ID或范围缩写 |
| JSON Schema/instance | 10/10 meta+shape PASS；4/4 instance PASS |
| 只读跨文件一致性 | PASS 3901 checks；脚本声明且实测不访问生产资源 |
| 必需计划文件存在性 | 当前31个文件；`plan_manifest.v4.json`按合同在冻结前故意不存在；动态ledger同样不应创建 |
| v3 core/source manifest核验 | 13/13 MATCH；source MATCH；manifest SHA已写入revision记录 |
| v3独立复审 verdict | SQL/性能 FAIL；生命周期/安全 FAIL；测试/可实施性 FAIL；v3禁止实施 |
| v4修订状态 | 进行中；只改本隔离计划目录，尚未冻结或送正式复审 |
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
