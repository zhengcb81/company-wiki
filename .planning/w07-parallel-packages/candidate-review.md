# W07 候选施工包只读评估

日期：2026-10-11。评估者：ROOT 的非施工子 agent。本文只为 ROOT 编写三张最终施工卡提供依据；没有启动代码实现、测试、下载、模型调用、Git 修改或安装。

## 结论与调整

三条线可分开，推荐保留 RF 与 Audit 两条，第三条改为 **FF 离线矩阵执行效率**。ET 正文质量诊断可有价值，但本轮暂缓；它不是当前阻断，且与已完成的 N5-ET-TXT 完整性检查有交集。

| 候选 | 推荐目标 | 与已交付的关系 | 独立性 |
|---|---|---|---|
| A / RF | 原生模型的组合压力矩阵与结果回归工具 | 不重做模型 registry 全覆盖、W05 期间语义或 P7 校准 | 只写 RF 新 tools 子目录和指定工具测试；生产 RF 与 Audit 均只读 |
| B / Audit | 把原生执行产物变为四号审查可逐项打开的风险诊断 | 不重做 W06 financial-measure 算术、WP06 研究规范、W05 循环状态 | 只写 Audit 新技能脚本/单独说明/测试/fixtures/E2E；不依赖 A 新工具 |
| C / FF | 系统减少离线联调重复准备与启动开销，完成原 41 案例 | 不重做已接收的 CaseSpec authority/恢复/截止边界 | 只写 FF 测试 runner 与指定快速工具测试；CaseSpec/原向量/oracle/三仓生产源码只读 |

共享接线、生产缺陷修复、固定依赖 SHA、并线、安装、共享 PWF 与累计账由 ROOT 管理。三条线不可借测试失败跨仓修生产代码；遇到真实生产缺陷，以精确 request/response/源码版本交 ROOT。

## 母 PWF 依据和实际缺口

实读当前入口：

- `docs/plans/cross-market-rf-e2e-2026-10-08/task_plan.md` 的 ROOT 入口指向 `phase6/w06_parallel_verification_2026-10-11/ROOT-reception-status.md`，旧状态是历史。
- `phase6/w04_post_pw03_common_roots_2026-10-11/task_plan.md` 已定义：G1/G3 工程及安装 → G2 真实叙述消费 → G4 原三家执行和四路独审 → G5 未用于修复的其他公司与池循环。
- `phase6/w04_post_pw03_common_roots_2026-10-11/work_packages/WP06.md` 已有 RF 研究规范责任，不能另派同一文档施工。
- 当前母计划仍开放 G2/G4/G5。这三包提供工程诊断与可复验支撑，**不能替代真实资料消费、独立四路研究审查，或宣布经济结论合格**。

ROOT 补充的最新 FF 观察：新 attempt 1 PASS / 27 PARTIAL / 13 NOT_RUN，184.54 秒；原 180 秒限额不变，fresh proofs 为空。此前 `.planning/w06-cross-period-acquisition/matrix-deadline-diagnosis.md` 已记录 264 次 Python guard 启动，以及最后集中 `_fresh_proofs` 被批次耗尽饿死。当前短板是工具执行安排，不能把由此产生的 PARTIAL 当成二十多个独立产品错误。

## A — RF 组合压力矩阵

### 已有能力，不要重复建设

RF 已有 `tests/test_models.py` 的 registry 公式全覆盖、`tests/test_industry_end_to_end.py` 的各模型 `run_forecast` 与输出校验。W05-RF-FLOW 已修期间类型/时间窗口/短贡献，共有作用域和 calibration 支持诊断已由 P7 完成。仅新增“行业列表逐个跑一次”价值不足。

本包有价值的范围是少量**组合**向量：收入确认、量纲、共享冲击、年度与短窗口、零基数、支持期覆盖交叉出现时，原生系统是否仍保持同一规则。矩阵必须调用原生实现，不能复制公式或重新实现类型推导器。

### 实际可调用接口

经只读 helper 实读 RF 当前明确文件：

| 接口 | 使用约束 |
|---|---|
| `scripts/revenue_core.py` 中 `run_forecast(data: dict[str, Any], *, mode: str = "formal") -> dict[str, Any]` | 必须显式 `mode="draft"`；formal 会尝试 provider 签名与 registry 写入 |
| `scripts/contracts/document.py` 的 `validate_document(data: dict[str, Any], *, collector: Collector \| None = None) -> dict[str, Any]` | 由 `revenue_core` re-export；原生输入验证，矩阵不另造合同 |
| `scripts/forecast/segments.py` 的 `calculate_model_path(model, base_revenue, driver_ids, parameter_index, years, scenario) -> dict[str, Any]` | 可只读理解模型；完整案例仍以 `run_forecast` 实际消费为准 |
| `scripts/revenue_report.py` 的 `validate_forecast_output(result, data=None) -> None` | 强 formal 输出路径；不要把 draft 再冒充 formal 校验。run_forecast 的内部校验和 native 渲染用于 draft 正控 |
| `scripts/revenue_forecast.py INPUT --validate-only [--verbose]` | 已有真实零 registry 写入 CLI，内部走 draft；没有凭空新增的 `--mode` CLI flag |
| `scripts/research_support_diagnostics.py --input INPUT [--output NEW_FILE]` | 独立只读支持诊断；不预测，不认证经济真实性 |

正式卡应在 ROOT 固定基线后列出实际 fixtures/helper 路径，不让 worker 从记忆造 schema。已有 `model_document`、`forecast_document`、`finalize_contract`、`add_window_parameter` helper 可只读复用；其中 finalize 会原位更新输入，所以每案例先 deepcopy，不改冻结 fixture。

### 建议冻结的八个组合向量

每个限两年与 low/base/high，最多一个合法控与一个反例；它们是候选定义，尚未执行，最终输入由 ROOT 卡锁定。

| # | 组合 | 主要真实断言 |
|---|---|---|
| 1 | unit_sales + subscription 共用 quantity 假设 | 一个 shock 影响两段；独立小手算检验合计增量 |
| 2 | bank_revenue + capacity_utilization 共享 ratio | 两角色允许区间用交集；不能独自放宽边界 |
| 3 | subscription 的 lagged 确认 + 另一即时确认段 | 合计只计 recognized revenue，carry-in/tail 保留 |
| 4 | services over-time progress + 即时确认段 | progress 不越段；缺必要 progress 原生拒绝 |
| 5 | schema 3.10、FYE 06-30、10 日 contribution + 全年段 | 显式年度组合不重复年化；跨 FY 拒绝 |
| 6 | unit_sales + milestone_royalty，零基期 | 启动收入合法，CAGR=None，absolute shock 不除零 |
| 7 | 扩展 stock-flow 模型 + 共享祖先冲击 | 合法派生闭合；破坏闭合的冲击拒绝，输入保持 |
| 8 | 共享参数用于两个经济 scope，校准只覆盖一段 | 既有 support 只覆盖本段，另一段 reasons 保留 |

已有相关覆盖还包括 recognition_bridge/mixed_aggregate_recognition、sensitivity_dependency_dag、scenarios_confidence。不得将它们整套搬来重复验收。可只读复用 `apply_parameter_contract`、`update_parameter_value_and_claim` 等已有 helper；构造期 finalize 会重设 schema，3.10 案例应最后显式设版本。运行 CLI 消费版本化静态合成 fixture，输入生成器不成为第二套生产模型。`tools/tests` 不会自动获得 `tests/conftest.py` 的 registry 隔离，因此必须显式 draft、独立 cwd/env/path 恢复，不能靠 autouse 侥幸不写生产 registry。

### 推荐范围与交接

- 排他写集：`tools/model_generalization_matrix/`、`tools/tests/test_w07_model_generalization.py`、本线独立 PWF/交接。不写 `scripts/`、`assurance/`、config、CI、生产 output 或已安装技能。
- 先冻结小 registry；至少包含互相组合的合法与拒绝/未知正控，而不是大量公司特判。输入真实 native JSON，记录每次输入 bytes SHA、原生版本、实际 exit/结果、断言与耗时。
- 输出建议为 `model-generalization-matrix/1`：case id、vector、原生 input/result 引用、执行 mode、expected technical assertion、observed technical outcome、原生 diagnostics、scope；`source_truth_verified=false`、`economic_reasonableness=not_evaluated`。
- Oracle 预期由固定案例定义决定，不信运行 report 自填 expected；技术 INVALID、未运行与经济 unknown 分开。不能把“未来 actual 不存在”判模型错误，也不能补造 actual 来过检。
- 只测工具责任层的集中单元/集成，再用固定合成 native 输入通过真实 draft API/CLI 一次大节点；不重复已封存的全行业大套件、不纳入每 commit 的全矩阵。

## B — Audit 分析师风险诊断

### 已有能力和正确包路径

Audit 仓的可安装脚本位置是 **`skills/revenue-forecast-audit/scripts/`**，不是仓库根 `scripts/`。当前已有：`audit_run.py`、`audit_contracts.py`、`numeric_audit.py`、`financial_measure_audit.py`、`authoring_provenance.py`、`document_status_join.py`、`review_protocol.py`、`pool_progress.py`。

`references/review-analyst.md` 已有 A01–A18。W06 数字口径工具已覆盖币种/scale、百分比/百分点、存量/流量、窗口、派生关系、零基数及缺上下文；它始终不认证 source truth 与 economic reasonableness。新卡不要再建第二套 typed ledger/计算 DAG/范围校准器，也不要把原来的审查表换名重写。

### 真正需要补的可观测性

把既有产物整理成可定位的分析师风险索引，服务 A02/A05/A06/A08/A10/A13/A17/A18，例如：

- 最大收入贡献所对应的实际 native 参数/claim/calibration 与支持窗口；只能以结果已有贡献或明示关系比较，不能重新跑预测填缺项。
- 订单/产能/用户/GMV 转收入所需的确认/转换/时间支持是否在已有产物明确出现；缺项给具体 JSON pointer/parameter id，不能猜一个 conversion。
- 需求/供给/资本/员工/预算等交叉约束是否已记录，正反证是否指向同一重复引用；信息缺失不能用通用行业阈值判经济不合理。
- “超预期”的基准/截至日/币种/收入定义/差异数量是否有现成产物；没有基准就诊断 `benchmark_not_supplied`，不提供共识或编 beat。
- 独立 operating range 与目标反推、历史 seasonality 与未来幅度、联合冲击与单因素灵敏度的区分：可检查可见字段与关联，无法证实机制时给 `not_evaluated`。
- 无未来 actual 时误差/WAPE 保持 null；真实历史已观察与未来假设分开。不能把没有 actual 改成 0 误差。

### 可复用接口和稳定输入

建议纯接口 `audit_analyst_risks(native_input, native_result, support_diagnostics=None, review_context=None) -> report`；CLI 显式给 native input/result 与可选已有 support JSON，写新 attempt。`review_context` 仅引用执行包已存在的观察/基准/约束及其 JSON pointer；不是第二套模型，也不是人工许可文件。

RF 已存在 `economic-support-diagnostics/1`：

```text
input_sha256 = 原 native input 文件 bytes 的 SHA（不是 canonical JSON SHA）
requested_years: string[]
company
segments: [{segment, entries: [{scenario, year, status,
  reasons, supported_parameter_ids, unsupported_parameter_ids,
  calibration_ids, claim_ids}]}]
status = supported | conditional | unsupported
economic_truth_inferred = false
```

B **消费已有诊断 JSON**，不在审查消费层再次调用 `run_forecast`、validator、analyze_operating_research 或 build_support_diagnostics。核本次 input bytes 绑定和所引用 native year/segment/scenario/parameter/claim，再转述原 reasons。缺诊断为 `not_supplied`；错绑为 `invalid_binding`；supported 只指既有范围支持，不能升级买方研究 PASS。新的诊断由原 RF CLI 的责任层产生。

native result 使用当前真实版本字段，不要求它新增一个工具臆造的 input_hash。若原生结果/执行记录未提供输入消费关联，只报告 `result_input_binding_not_observed`；对两个文件分别计算 SHA 不能证明预测执行真的消费过该输入。不能为了“审计绿”自动补造关联或再跑一遍预测。

Audit 已有真实公用函数：

- `audit_contracts.resolve_json_pointer(document, pointer)`：已打开 JSON 的有界 RFC6901 定位。
- `audit_contracts.write_attempt(tool, out_root, payload_name, document, inputs=())`：实际新 attempt、输入/输出 bytes SHA，复用原子写。
- `audit_contracts.clean` / `audit_run.Redactor`：复用脱敏，不重新收集真实密钥。
- `financial_measure_audit.audit_measures(ledger)` 与其已有报告：需要声明口径/算式时复用责任层，不重新造公式。

推荐输出 `analyst-risk-audit/1`，包含检查点、status（observed_gap / not_supplied / invalid_binding / observed_consistent / not_evaluated）、输入/结果/诊断 SHA、native pointers/ids、numerator/denominator 及明确的覆盖范围。不要设置自动“economic PASS”或把缺字段自动当不合格授权门；原四 reviewer 最终结论仍由独立审查负责。

排他写集：新增包内 `scripts/analyst_risk_audit.py`、单独 `references/analyst-risk-audit.md`、指定单元/CLI tests、独立 fixtures、`tools/run_analyst_risk_e2e.py`、本线 PWF/交接。既有 SKILL/workflow/review-analyst/review-process、pool/W06 工具、RF/CWP/FF/安装均只读；ROOT 最后接线。

测试覆盖错误 input/support 绑定、dangling pointers、零覆盖、缺经营约束、重复证据、无共识 beat、跨币种基准、未来 actual 缺失、partial 年窗、已有合法支持仍不升经济 PASS；集中一次纯工具节点及三个合成包真实 CLI E2E。离线测试不启动 agent/provider/LLM，不自称完成 G4/G5。

## C — FF 矩阵执行效率系统修复

### 当前真实入口与可保留接口

实读 `C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root/tools/offline_contract_matrix/`：

- `run.py`：`Context(..., deadline=None)`、`child_env`、`begin_case`、`warm_seed(identity, kind, year, period)`、`scan()`、`run_ff(request, *, case_id, run_label="run1", with_fmp_key=True, timeout=CASE_TIMEOUT)`。
- `runtime.py`：`Deadline.remaining()` / `case()`、`run_process(command, *, env, cwd, deadline, input=None)`、`OwnedAttempt.create(...).cleanup()`、`synthetic_env(...)` 与 network/translation guard。已有接口足够，不能再建第二 deadline/任务库/许可链。
- `matrix_cases.seed_all`：3 市场×3 类周期报告 + US2025 年报，**10 次真实独立 warm ensure**；再落一条显式 legacy local TXT + scan。不能把 warm 变成扫描 sidecar 来省时间，也不能将缺失 fetch 文档预先塞入库。
- `cli_main`：代码绑定/依赖记录 → seed → 按 CaseSpec 顺序逐例 → 末尾 `_fresh_proofs` → 恢复/报告/oracle。
- `source_proofs.py`：真实 `SourceVersionReader.open_version` 回开原字节、物理原件去重、版本/位置/期间/主体元数据与原语言正文 digest。不能因超时省去这一步或信原 response 的自报 SHA。
- 当前默认快速工具测试是 `tests/test_w06_contract_matrix.py`、`tests/test_w06_matrix_runtime.py`、`tests/test_w06_case_authority.py`；不存在默认的 `tools/tests/`，新卡须选实际指定路径，不凭空写旧路径。

### 先测量，后减重复；不得绕三层

1. **一次测量节点**：记录 runner 一级启动、CWP warm/scan、每个 FF CLI、ET supervisor/worker、fixture supplier、fresh reader 的实际时间/次数与 wait 分类。264 guard boots 不是“264 个可删重复”：很多是生产隔离与每请求语义，先归因再减。
2. 首选减少**准备开销**：将同一组合成 warm seed 安排在一个有界 helper 进程内逐项调用实际公开 CWP ensure/writer，仍生成每条 request/response/exit/source-ref/fixture provider 计数和相同最终 warm state。不能手写 prior SQL、可信 fact patch、伪原文或直接把既有 receipt 当真实 ensure 返回；只允许同样的 10 个 warm 请求。
3. 复用一次建立的 guard/env/config 路径与已经验证的固定 code binding；过程计量应在 `run_process` 层可选记录，不改变 CompletedProcess 兼容返回或吞掉实际 exit/usage。
4. 给 **fresh proof 工作量保留批次时间**：可以在保持原字节回开语义的前提下更早取得证明并做最后必要再开，或调整准备安排使末尾证明不被饿死。若后续案例会改变同文档/版本/位置，早期 proof 不能替最后状态证明；不能提前清 scratch、排除 proof 耗时、另开额外 180 秒窗口。
5. 若测量确认仍需要并发，先列 CaseSpec 之间的状态依赖；固定有限并发，各执行域独立 Context/wiki/proxy state/counters/artifacts，仅协调员归集。链 A 下载→第二次复用等必须同域顺序。禁止多个 case 共写当前 `proxy/state.json` 或共享 catalog writer；禁止复制浮动生产状态。不要在卡里预定“并发肯定更快”。
6. 固定 seed 业务内容、41 CaseSpec、原请求/期望、fixture 响应向量、usage unknown/cutoff/type/period/SHA 断言以及 oracle 均只读。性能测试不得由 report 自填 expected 掩盖覆盖，不删除尾部案例凑绿，不缓存上次生产 FF/ET 结果作本次 response，不绕 FF CLI 或替换 ET supervisor/worker/CWP writer/reader。

可以保持 `run_ff`/`Deadline`/`OwnedAttempt` 对既有工具 tests 的兼容；新增单一执行阶段 measurement 记录足够，避免设计复杂的可恢复调度服务。C 是显式手动联调工具，不是常驻 worker 或生产提速项目。

### 交接与验收

- ROOT 先提供已 commit 的 FF5/ET3 修复和只读 CWP dependency root/代码 SHA；worker 从该固定 baseline 建排他树，不读浮动 WIP，不安装或写另两仓。
- 排他产品写集建议：`tools/offline_contract_matrix/runtime.py`、`cli_main.py`、`run.py` 的 Context 执行安排、`matrix_cases.py` 的 seed 段/新增小 seed helper，以及明确指定快速工具 tests、本线 PWF/交接。不要给整个目录泛写权；`case_specs.py`、oracle/outcome、fixture 真值、实际 case handler、`scripts/`、ET/CWP、CI/生产 config/密钥只读。
- TDD 先锁：初始化失败/timeout 只清自身、绝对截止不能 reset、seed 等价、固定案例请求/次数不漂移、proof 不被安排在必然过期之后、故障不得假记 PASS。用工具层假进程/可控时间验证调度，不用反复完整矩阵寻找参数。
- 集中快测绿后一次原 41 **真实公开 FF CLI→ET supervisor/worker→CWP ensure/import/reader** 大节点，CaseSpec/oracle 原样，30 秒/例和 180 秒/批次。记录完整各阶段/启动次数、wall time、source_proofs、restore、各例真正业务结果。180 秒内完成且所有原业务/证据断言通过，才是本包 COMPLETE；否则诚实给部分改善与残余共因，不抬限额或改期望。
- 非作者最终复核使用固定原 authority 反例与本次 41 产物，不重复已接受 195/全矩阵，也不把手动矩阵加入每次 commit/CI。

## 三包共同恢复和输出边界

1. 默认只用合成资料；固定输入只读。真实文件引用经明确用户任务和 ROOT 后续 G2/G4/G5 管理，不扫描 company 原件湖，不读取真实 FMP/LLM 密钥，不继承真实 credentials。
2. 测试执行仅用唯一短 owned scratch。运行前记录 parent 的存在/空目录形态和已有 sentinel/entries；成功、失败、初始化异常、超时都仅删除本次创建项。已存在空目录、旧文件/旧报告不能误清；初始缺席的自有根与新增空 parent 回收。输出证据放单独新 attempt，明确保留，不伪称“所有测试目录均恢复”而偷偷留报告。
3. 三条线各自 PWF、测试数据、日志、报告、交接和小 manifest 分离。持久内容以小输入、引用、日志/计量为主，不复制全湖或生产大响应，不完整备份恢复演练。
4. 交接最少字段：lane/base/delivery SHA、精确修改集、read-only dependency SHA、native 接口/命令、输入与输出 refs、RED/GREEN/E2E actual、恢复 initial/final、原件/config 影响、未执行/unknown/残余问题、ROOT 接线候选。只能给真正跑过的结果，不提前给未来工程/研究 PASS。
5. A 不依赖 B 新脚本；B 不调用 A 新矩阵；C 不修改 RF/Audit。ROOT 集中选一次大节点接受、正常 commit/merge/同步/push，工程结论与研究验收分开，无逐小节点人工许可。

## 本次评估的限制

- 没有运行未来测试、CLI、41 矩阵、provider 或模型。文中建议是可施工范围，不是性能或质量验收结果。
- 曾查错 Audit 仓根脚本路径、RF 根 support 文件路径，已经由实际 `skills/.../scripts/` 与 RF `scripts/...` 文件纠正；这不是产品失败证据。
- 只读 Git head 获取能读 Audit main `9cd5ff8a`；沙箱下 Audit status 报 “must be run in a work tree”，没有据此断言 dirty/clean，更没有修改 Git。
- 最终 cards、冻结 case 列表、基线、worktree、输入 refs 与三份 PWF 的创建仍归 ROOT。本文作者写完即 STOP，不开展外包任务。
