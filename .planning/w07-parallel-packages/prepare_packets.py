"""Prepare exactly three standalone W07 packets; no worker implementation."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
CENTRAL = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w07_parallel_quality_2026-10-11'
prepared = json.loads((HERE / 'prepared-roots.json').read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

COMMON = '''# W07 共用交接契约（每包内有独立副本）

## 工作方式
在 START_HERE 指定的独立目录工作，只读自己的固定输入，写自己的 allowlist。三个包可同时启动，不相互等待，也不读取彼此未交付代码。ROOT 独占母计划、共享安装与主线并线；不向主仓覆盖文件，不启动真实下载/LLM，不改 Dayu、IQS、原件或生产配置。

PWF 固定为本包 `.planning/<plan-id>/` 的 task_plan/findings/progress；若 harness 支持，设 PLAN_ID 为该 id、PWF_PLAN_ROOT 为当前工作目录。未提交的本包输入是 ROOT 准备的材料，不是无主垃圾；保留它们。别用 git add -A，不启用整库恢复演练。工作目录初始存在与 SHA 见 INPUTS.json；这些是工程可复现记录，不是人工许可。

## 只有三个大节点
**A 定义与 TDD：**核对现有 API，冻结用例预期，先写能暴露行为缺陷的测试；仅 import 缺模块不算有价值的 RED。必要时先最小 stub，再取得行为失败证据。记录实际 RED 命令/退出/原因一次，不逐用例签收。

**B 实现与集中测试：**按卡的唯一写集实现共用方案，运行一个集中快测包，包含成功、反例、未知和错误/恢复路径。不能改原期望迎合实现；若查明旧期望错误，给 ROOT 具体合同/输入/反例，由 ROOT 处理边界外变更。

**C 离线端到端与收尾：**一次有限完整 E2E 验证实际公开入口、报告和临时目录恢复。失败只为具体共因修复重跑；不要每个 commit 跑全矩阵。保留失败证据，不把 PARTIAL/NOT_CHECKED/unknown 改为 PASS。

## 临时目录与空间
临时路径必须是当前工作目录下新建的短路径（如 `.tmp/w07-<uuid8>`）；记录开始前 absent 或 sentinel 内容。成功、异常、timeout 都关闭子进程与 SQLite，删除本次新增文件并恢复原 baseline；只删除自己创建的路径。未存在的测试下载必须回到不存在，不做整份原件备份恢复。保留的小报告放独立 handoff 目录，不能散入生产公司目录。代码快照/固定 inputs 是初始材料，worker 不删。

报告默认总持久体积不超过 8MiB，scratch 目标不超过 64MiB（不含 checkout/已提供 code-only 输入）；这是防膨胀目标，确需超出说明实测原因，不新建审批文件。日志保留摘要、失败片段及指向完整压缩证据的引用，禁止完整环境变量/API key/原文湖复制。真实成本 0；未测峰值/不可知计量填 null，禁止编造。

## 输出接口
在自己的 `docs/handoffs/<plan-id>/` 输出 `handoff.md`、`handoff.json`、测试摘要与必要的小证据。JSON schema 为 `w07-lane-handoff/1`，必含：

```json
{
  "schema": "w07-lane-handoff/1",
  "lane": "W07-...",
  "status": "COMPLETE|PARTIAL|BLOCKED",
  "repository": "absolute path", "workdir": "absolute path",
  "branch": "codex/...", "base_commit": "sha", "implementation_commit": "sha",
  "changed_files": [{"path": "relative", "purpose": "why", "sha256": "bytes sha"}],
  "readonly_inputs": [{"path": "relative", "sha256": "sha"}],
  "interfaces": [{"name": "public entry/schema", "compatibility": "before/after"}],
  "tests": [{"node": "A|B|C", "command": "exact command", "exit_code": 0,
             "counts": {}, "seconds": 0, "evidence": "relative report/log"}],
  "issues": [{"root_cause": "mechanism", "evidence": "input/output refs", "scope": "affected cases", "resolution": "fixed or ROOT request"}],
  "cleanup": {"baseline": "ref", "final": "ref", "restored": true, "nonowned_preserved": true},
  "cost": {"real_provider_calls": 0, "real_llm_calls": 0, "dollars": 0},
  "space": {"persist_bytes": 0, "scratch_peak_bytes": null},
  "source_truth_verified": false, "economic_reasonableness": "not_evaluated",
  "residuals": [], "root_next_action": "receive/integrate or repair"
}
```

模板中的数值是字段说明，必须换实际测量；非零退出和未检查项如实填写。实现先正常 commit，报告后正常 commit，可用 implementation_commit 指向前一提交，避免自引用 hash。只提交自己的确切路径与小输入；不绕 hooks、不 force push、不并 main、不同步用户技能安装目录。RF/FF 若 remote 可用可正常推自己的分支；Audit 当前无 remote，不新建。完成 STOP，给用户卡号、commit、交接报告绝对路径和剩余问题。

ROOT 接收时只做：写集/固定输入边界、一个集中独立反例包、该卡大节点 E2E 留证，随后正常并线/安装及 exact HEAD CI。不新增小节点人工许可；真实公司执行与四路独审仍属母计划。
'''

RF_CARD = '''# W07-RF-MODEL：原生模型组合压力测试包

## 可以现在开工
工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/w07/rf-model-quality`
分支：`codex/w07-rf-model-quality`；基线：`30ddae8ed2a457c418e63b182e7d8c9230fbf3ff`。
独立 PWF：`.planning/w07-rf-model-quality/`。先读本卡、同目录 HANDOFF_CONTRACT.md、INPUTS.json。ROOT 已准备稀疏 checkout；不要 disable sparse-checkout，旧 tracked .planning 约 846MB 与本包无关，不要拉入。主仓 assurance/output 的其他改动不属于本包。

## 为什么做
单模型与期间测试已经完成，本包补跨机制组合缺口，形成可重复工具，给母 G4/G5 的新公司预测提供数学边界证据。不要再搭第二个预测引擎，不要据合成测试宣布买方结论准确。

## 唯一写集
- 新 `tools/model_generalization_matrix/**`（run/cases/oracle/report/README 等）。
- 新 `tools/tests/test_w07_model_generalization.py`。
- 自己 `.planning/w07-rf-model-quality/**`，但 `input/**` 初始内容只读。
- 自己 `docs/handoffs/w07-rf-model-quality/**`。

其他一律只读：scripts、已有 tests/fixtures、config、CI/hooks、SKILL、安装、assurance/output。发现 core 缺陷给 ROOT 完整最小复现，不越界修；工具可交 PARTIAL，不能掩盖产品失败。

## 已确认的原生接口与上下文
- `scripts/revenue_core.py:run_forecast(data, *, mode="formal")`：工程全程显式 `mode="draft"`，不要求发布签名/供应商；不假造不存在的 CLI --mode。
- 现有 CLI：`python -B scripts/revenue_forecast.py INPUT --validate-only`，内部是 draft。选择一个合法、一个拒绝样本实际调用；不能只测自己 wrapper。
- `scripts/research_support_diagnostics.py --input INPUT --output NEWFILE` 返回 `economic-support-diagnostics/1`，按 segment/year/scenario 报支持缺口。
- formal 的 validate_published_forecast 不适用于 draft；draft 不给 invest 消费者，不伪造 publication receipt。
- 从现有 `tests/test_lifecycle_forecasts.py`、`test_industry_end_to_end.py` 的 model_document、`test_data_contract.py` 的 finalize_contract/apply_parameter_contract、`test_research_evidence_roles.py` 的 calibrated_document、scoped_calibration_support/target_measurement_comparison/M3 period/model extensions 取合法工程构造。每 case deepcopy，已有 helper 会变异输入。
- 本包 input/native-* 是 ROOT 用原生 helper、draft 与 support API 实际生成的合成样本（约178KB），只演示输入输出形状；不代表真实公司或来源真值。

## A：先固定 8 类组合及独立 oracle
每类至少一个合法可算向量与一个有意义反例/未知向量，合计至少 16 个小输入；不要生成数百同义用例。期望来自固定 CaseSpec/手算守恒式，不从被测结果生成 expected。可延用原 fixture 单位与期间校验。

| 类 | 组合 | 必查边界 |
|---|---|---|
| M01 | quantity×price×currency/unit | 同维缩放不改经济金额；CNY亿/HKD百万/USD million标签显式，不自动换汇；混单位必须拒绝或明确转换 |
| M02 | ARR stock→recognition＋late contract/churn | closing ARR 不直接当全年收入，收入按承诺的期间和确认方式进入；不能用缺数据零补 |
| M03 | capacity/demand/launch fraction | 0/有限产能、需求约束限制收入，启动比例只算一次，无无限增长 |
| M04 | dated acquisition/control＋cross-FY partial windows | 部分期间按实际原生覆盖与控制口径；缺季度不能当0，有别名不能双算年度 |
| M05 | zero-base commercial launch＋CAGR | 0基数合法启动收入可算，CAGR undefined=null；不能把 null 解释为坏预测或0增长 |
| M06 | shared shock＋joint scenarios | 共用压力一次传播；volume/price 的相关压力有联合路径，不能重复施加 shock；不强迫所有经济结构 Low≤Base≤High |
| M07 | management annual/runrate/cumulative target＋gross/net/cannibalization | 不可比目标留缺口；累计/期末不冒充当年；自身增量扣已包括收入，防双计 |
| M08 | optional operating support＋segment/year/scenario＋future actual | 某一期间有校准不推定其余支持；合法未来假设与缺actual分离，actual/WAPE未知保持null |

结合现有原生模型实际支持范围制定准确输入。接口确实不支持的组合报告 NOT_SUPPORTED 与 ROOT 建议，不能编造 API/复制公式让测试看似绿。完整预期清单在实现前写入 cases.json 或等价 CaseSpec；保存 A 的行为 RED。

## B：实现可复用有限工具
实现公开入口 `python -B tools/model_generalization_matrix/run.py --owned-root ABS_NEW --out-root ABS_NEW`，无需网络、source DB或其他新包。每个 case 实际调用原生 draft 引擎（拒绝向量可实际验证入口）；记录 native request/result、异常与 JSON pointer。用例期望/数学 oracle 和实际结果分开，未执行不能 PASS。

产出 `model-generalization-matrix/1`：case_id/vector/mode/expected/observed/assertions/status/native_refs/diagnostics，顶层计数、实际时间、恢复与残留。`source_truth_verified=false`，`economic_reasonableness=not_evaluated`。只产 source/model 工程报告，不正式研究报告。多例共用一个 fixture/setup，不每条另建任务数据库或身份审查。

集中快测命令：`python -B -m pytest -q tools/tests/test_w07_model_generalization.py`。覆盖 oracle 被错误结果欺骗、未知处理、native异常、timeout/cleanup、输入被污染；可用 monkeypatch 验证 wrapper，但 C 必须真引擎。开发过程中不重复全仓数千测试。

## C：实际离线 E2E 与验收
一次跑完固定≥16输入，附一次现有 CLI 合法/拒绝与 support CLI 的实际结果。合法结果满足手算/守恒，拒绝有合同原因，未知没有0替代；不存在未经运行的通过。全过程隔离临时目录，最终 absent/sentinel 恢复；固定 input 和只读目录 SHA 保持。

完整报告是手动大节点，不加入每次 commit/CI。交 handoff.md/json、fixture schema/CaseSpec/报告、测试记录。正常 commit，STOP 等 ROOT。预估为中等工作量，若暴露 core 缺陷先准确记录，不耗费模型调用尝试。
'''

AUDIT_CARD = '''# W07-AUDIT-ANALYST：买方模型风险诊断包

## 可以现在开工
工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/w07/audit-analyst-quality`
分支：`codex/w07-audit-analyst-quality`；基线：`9cd5ff8a2c8f9c1726c4047785164e3263673614`。
独立 PWF：`.planning/w07-audit-analyst-quality/`。先读本卡、HANDOFF_CONTRACT.md、INPUTS.json。Audit 目前无 remote，只本地正常 commit；不创建远端。无需等 W07-RF-MODEL，ROOT 已提供原生合成 input/draft/support 三文件。

## 为什么做
W06 已解决数字单位、pp、stock/flow与度量来源的算术诊断，本包补第四号买方 reviewer 最容易漏的“故事到可实现收入”风险。只生成可观察证据索引与缺口，不自称取代资深分析师或四路独立审查。

## 唯一写集
- 新 `skills/revenue-forecast-audit/scripts/analyst_risk_audit.py` 与必要的新 analyst_risk_* helper。
- 新 `skills/revenue-forecast-audit/references/analyst-risk-audit.md`。
- 新 `tests/test_w07_analyst_risk_audit.py`、`tests/fixtures/w07_analyst_risk/**`。
- 新 `tools/run_analyst_risk_e2e.py`。
- 自己 `.planning/w07-audit-analyst-quality/**`（初始 input 只读）与 `docs/handoffs/w07-audit-analyst-quality/**`。

只读现有 review-analyst.md/SKILL/workflow/contracts/redactor、loop、cost/pool/installed副本、RF/CWP/FF。脚本位于 skills/revenue-forecast-audit/scripts，别误放仓根 scripts。ROOT 收后连接 reviewer 文档和安装，worker 不改共享文档。

## 已有 API 和固定消费边界
- 读现有 references/review-analyst.md 的 A01–A18；聚焦下面8项。不要再实现 financial_measure_audit 的算术/单位检查、RF模型或 validator。
- 复用现有 `audit_contracts.resolve_json_pointer`、`write_attempt` 和 `audit_run.Redactor`，确保新鲜 attempt、原子小报告与日志脱敏。
- 新工具**纯消费**已打开的原生 RF input/result JSON、`economic-support-diagnostics/1`，可选 `financial-measure-audit/1`；不在工具里再次运行 RF validator/DAG/forecast、SourceReader、provider或LLM。
- native support 的 segments[].entries[] 含 scenario/year/status/reasons/supported_parameter_ids/unsupported_parameter_ids/calibration_ids/claim_ids；必须保留同一 segment/year/scenario粒度，不能一个支持覆盖所有年。
- input/native-* 由 RF30ddae8e 的 calibrated_document、run_forecast(mode=draft)、build_support_diagnostics 实际生成；manifest明确 synthetic。只读形状来源，不把合成 claim/hash 当真实原文证明。

## A：定义观察规则和先写测试
每项至少：证据齐全的观察、关键字段缺失未知、看似齐全但口径错的反例。支持 JSON 原始 pointer 与 parameter/claim/driver id，不凭自然语言关键词断言公司好坏。

| 检查点 | 输出的可观察问题 | 未知/反例 |
|---|---|---|
| A02 | 驱动连到原生收入路径、节奏和参数 | 只有主题标签，或有claim但不连收入：UNRESOLVED |
| A05 | supply/demand/监管等约束及适用范围 | 无实际可查约束：NOT_CHECKED；不可自设行业CAGR上限 |
| A06 | TAM/backlog/ARR等到收入有时间与转换关系 | 总存量/市场规模直接等全年收入，或转换未知需列缺口；不重算RF公式 |
| A08 | 管理目标与独立正反证区分，来源独立性信息 | 同一来源重复不同措辞不能当独立证据；未知独立性不可假定独立 |
| A10 | beat 结论对应基准、日期、期间、单位与比较驱动 | 无基准/口径不可比不能称超预期；列需要review而不捏共识数据 |
| A13 | operating range 来源、转换、支持期与target分离 | 从target反推的区间不能当独立参考；未知范围保留null |
| A17 | 联合压力路径/作用范围与交叉敞口已声明 | 各参数单独±X%不自动等联合压力；只索引原生stress，不重算 |
| A18 | 未来actual与预测误差的检查范围 | 缺actual意味着NOT_CHECKED/null，而非WAPE=0或模型失败 |

有输入才可查；未提供 context/独立基准等以清晰 missing_fields 和 unresolved_scope 输出，不能新增必签收合同或拒绝整个预测。合法 analyst_assumption 可存在。TDD 要取得行为 RED；不能测试照抄实现。

## B：实现只读函数、CLI 与报告
公开函数建议 `audit_model_risks(native_input, forecast, support, context=None, measure_report=None)`。
公开 CLI 必须兼容独立运行：

```powershell
python -B skills/revenue-forecast-audit/scripts/analyst_risk_audit.py --input .planning/w07-audit-analyst-quality/input/native-input.json --forecast .planning/w07-audit-analyst-quality/input/native-draft.json --support .planning/w07-audit-analyst-quality/input/native-support.json --out-root ABS_NEW
```

optional --context/--measure-report 格式在新 reference 定义并给小例子；未知 schema清楚报错，已有合法 RF字段不因工具自造 identity 规则被拒。context是 reviewer陈述/引用元数据，不是人工许可证。

输出 `analyst-risk-audit/1`：checkpoints/findings with checkpoint_id/status/reasons/segment/year/scenario/parameter_ids/claim_ids/JSON pointers/native evidence refs，remaining_review、actual input refs与范围。确定性检查可 OBSERVED/UNRESOLVED/NOT_CHECKED；没有足够原生证据不PASS。顶层 `source_truth_verified=false`、`economic_reasonableness=not_evaluated` 永远保留，别输出 overall economic PASS。敏感信息走现有 Redactor，身份 id 当 opaque 引用。

集中快测：`python -B -m pytest -q tests/test_w07_analyst_risk_audit.py`（先检查本仓约定，若 unittest则提供等价确定命令）。涵盖8检查点、分期支持缺口、无context、future null、redaction、既有输入不变、输出碰撞/失败恢复。工具保持报告型，不加阻断预测/发布门禁。

## C：纯离线真实 CLI E2E
实现 `python -B tools/run_analyst_risk_e2e.py --owned-root ABS_NEW --out-root ABS_NEW`，实际启动新 CLI 消费固定原生三个JSON + 2–3组小 context（支持/缺基准/反例），读取产物核对指针/粒度/缺口/脱敏，测失败恢复；不 import 另一个 W07包或临时主仓代码。无任何网络/付费调用。

报告确认未来缺actual未变成零误差、缺证据未变为模型好、support一个scope不扩大，input保持、scratch恢复。交新 reference 的集成建议/接口、小fixtures、实际 A/B/C证据和 handoff，正常 commit并 STOP。ROOT后续把诊断接入四号 reviewer；本包不能替代真正经济判断。
'''

FF_CARD = '''# W07-FF-PERF：固定 41 场景联调效率根因修复

## 可以现在开工（本批优先）
工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/w07/ff-matrix-efficiency`
分支：`codex/w07-ff-matrix-efficiency`；基线：`2d380a054c658ce3b5f0763523e49a0ab34acf78`。
独立 PWF：`.planning/w07-ff-matrix-efficiency/`。先读本卡、HANDOFF_CONTRACT.md、INPUTS.json。ET/CWP code-only 已固定在本包 input/runtime，不读取另一 harness 浮动代码。无需等其他包。

## 已发生的问题（不要再盲目重跑）
原来的 CaseSpec/oracle 195测试与非作者28/28已绿。原41是40PASS/1FAIL、164.6232秒；cutoff修复后39PASS/3FAIL独审揭露 malformed stdout 抹掉已测 stderr usage，此共因已修，最终7PASS。

两个最新完整尝试分别：2PASS/31PARTIAL/8NOT_RUN、182.8623秒；1PASS/27PARTIAL/13NOT_RUN、184.54秒。没有把这些当作31个产品错误：180秒到期使尾部未跑、最终 fresh-source-proofs 没时间运行，oracle正确把缺最终证明的条目降为PARTIAL。保持失败记录；本包定位启动/准备/多层进程共因，让同一证据链在原预算内走完。

本基线含尚未并main的cutoff/usage修复；worker只动工具编排，ROOT负责FF/ET生产修复与发布。不能修正旧失败记录或把工程绿描述为全链完成。

## 唯一写集
- `tools/offline_contract_matrix/runtime.py`：实测阶段计时、兼容进程编排。
- `tools/offline_contract_matrix/cli_main.py`：现有单一deadline内编排。
- `tools/offline_contract_matrix/run.py`：仅 Context 执行安排/计时；不改请求/返回/期望语义。
- `tools/offline_contract_matrix/matrix_cases.py`：**只准 seed_all**；其余 case handler不改。
- 新 `tools/offline_contract_matrix/seed_batch.py`/measurement_* helper，如确需。
- 新 `tests/test_w07_matrix_efficiency.py`。
- 自己 `.planning/w07-ff-matrix-efficiency/**`（初始input只读）与 `docs/handoffs/w07-ff-matrix-efficiency/**`。

其余只读：CaseSpec/RunSpec、oracle*.py、matrix_outcome.py、source_proofs.py、fixture内容、所有case handler及现有测试期待、scripts生产逻辑、ET/CWP/config/key/CI/hooks。输入 manifest 对只读文件及除seed_all外的函数单独留证。不可删除原case/降低预期/跳过proof/加审批/第二计时器。

## 已准备的运行依赖（只读）
ET：`.planning/w07-ff-matrix-efficiency/input/runtime/et`，commit d0ac42c60dcca992db78860b8469cfed3dd527e5。
CWP：`.planning/w07-ff-matrix-efficiency/input/runtime/cwp`，commit d75f0d42e0fc11caa50d5030d16fa238c0e02d55，src/pyproject code-only。
依赖 manifest SHA f8e17feda1f540948521f595d7e4fd2697b39b6b3867cdb2bd04107eea27a00f。
两份只含代码共约3.6MB，不含原件/生产config/密钥。输入runtime已忽略，不提交复制代码；需要重建时按 dependency-manifest 的固定commit/path用 git archive导出，而非复制主仓WIP。gitless依赖HEAD可能unknown，报告用manifest固定commit和实测module SHA，不伪造git证据。

## A：测量与 TDD
先用已有 deadline/runtime/OwnedAttempt 接口建立阶段计时：binding、seed、FFCLI、ET supervisor/worker、fixture、fresh source proof、cleanup、总时长与实际启动数。计时不改变deadline起点/限额；unknown的阶段不能瞎估。

诊断只需小样本/已有完整日志，不先耗180秒重跑同一个失败。重点检查 seed_all 现有10次独立CWP CLI ensure（CN/HK/US年/半年/季报＋US2025年报）和扫描的重复准备。先用受控时钟/小假进程做调度行为RED，例如准备重复、计时遗漏、最终proof饿死、异常遗留进程；假进程只用于工具unit，最终真链保留。

## B：根因实现，保留真实链
优先把**同样10个真实CWP ensure写入**收敛为一个有界 helper进程顺序调用同一实际服务，每个request/response/receipt/source-ref/计数留下；不能直接造SQLite或假source-record替代原writer，不能预种本该触发新下载的文件。

复用单一 Deadline/OwnedAttempt 和已有synthetic env，减少重复启动/扫描/准备。每个需要检验的真实FF公开CLI、ET supervisor/worker、CWP writer/Reader仍按场景实际执行；不能把264次启动一概删掉。最终实字节/locator proof必须在所有相关变更后运行，早期proof不可替代最终状态，也不能移出预算或使用旧run缓存。

若测量证明需最多2并发worker，先给有向依赖与所有权：每组独立Context/wiki/proxy/counters，首次download→reuse链保持顺序，不能共享catalog并发写或把provider计数混合。不为并发而并发，先消除准备共因。保留CaseSpec/RunSpec权威、当前30s/case及180s/batch原值与起点，禁止重置remaining时间或增加timeout。

集中快测：`python -B -m pytest -q tests/test_w07_matrix_efficiency.py`，另跑与实际修改接口有关的既有matrix runtime/seed测试（具体文件名由当前tests确定），不改旧期望。检查超时仍拒绝、seed每请求真实记录、最终proof顺序、多个owned上下文不混、初始化/异常/timeout恢复。记录改前/改后计时，别据小fake计时宣称41通过。

## C：原41完整离线 E2E（仅大节点）
在当前工作目录运行，ABS_NEW_SCRATCH与ABS_NEW_REPORT是不同的新短路径：

```powershell
python -B tools/offline_contract_matrix/run.py --cwp-project .planning/w07-ff-matrix-efficiency/input/runtime/cwp --et-project .planning/w07-ff-matrix-efficiency/input/runtime/et --owned-root ABS_NEW_SCRATCH --out-root ABS_NEW_REPORT
```

实际预期：原41全部执行且PASS，oracle无冲突；各跨市场/不同文档/首次下载与复用/补TXT/cutoff/identity/失败恢复原期望保持；最终fresh实字节/SourceRef/locator证明完成，恢复absent/sentinel，production只读baseline保持，原30/180约束未变。计时包括原批次已有setup/执行/proof与恢复安排，不移阶段来隐藏时间。

首次完整run失败，只为证实共因修复后再跑；如仍PARTIAL准确交最慢阶段、依赖、剩余方案与失败报告，不声称交付目标达成。不加每commit41CI。每条真provider/LLM成本为0，synthetic请求单列。

交完整41报告、oracle结果、fresh proof、before/after阶段与启动测量、CaseSpec/oracle/case handler不变证据、小快测与恢复证据，正常提交STOP。ROOT独立接收后并线FF/ET；worker不写ROOT生产修复工区。
'''

META = {
    'W07-RF-MODEL': ('w07-rf-model-quality', RF_CARD),
    'W07-AUDIT-ANALYST': ('w07-audit-analyst-quality', AUDIT_CARD),
    'W07-FF-PERF': ('w07-ff-matrix-efficiency', FF_CARD),
}

def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError(f'Preserve existing file: {path}')
    if isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    path.write_text(value, encoding='utf-8')

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args]).decode('utf-8').strip()

assert not CENTRAL.exists(), 'One-shot packet preparation; preserve old packet'
summary = []
for lane, (plan_id, card) in META.items():
    record = prepared['lanes'][lane]
    work = Path(record['workdir'])
    assert git(work, 'branch', '--show-current') == record['branch']
    assert git(work, 'rev-parse', 'HEAD') == record['base_commit']
    plan = work / '.planning' / plan_id
    central_card = CENTRAL / 'cards' / (lane + '.md')
    write_new(central_card, card)
    write_new(plan / 'START_HERE.md', card)
    write_new(plan / 'HANDOFF_CONTRACT.md', COMMON)
    if lane != 'W07-FF-PERF':
        for p in (HERE / 'native-input').glob('*.json'):
            dest = plan / 'input' / p.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            assert not dest.exists()
            shutil.copyfile(p, dest)
    # Boundary records: code/fixture inputs only; no raw lake/key/production config.
    readonly = []
    tracked = git(work, 'ls-files').splitlines()
    for rel in tracked:
        if lane == 'W07-RF-MODEL':
            include = rel.startswith(('scripts/', 'tests/'))
        elif lane == 'W07-AUDIT-ANALYST':
            include = rel.startswith(('skills/revenue-forecast-audit/scripts/', 'skills/revenue-forecast-audit/references/'))
        else:
            include = rel.startswith(('scripts/', 'tests/', 'tools/offline_contract_matrix/'))
            if rel in {'tools/offline_contract_matrix/runtime.py', 'tools/offline_contract_matrix/cli_main.py',
                       'tools/offline_contract_matrix/run.py', 'tools/offline_contract_matrix/matrix_cases.py'}:
                include = False
        p = work / rel
        if include and p.is_file():
            readonly.append({'path': rel, 'sha256': sha(p), 'bytes': p.stat().st_size})
    if lane == 'W07-FF-PERF':
        import ast
        rel = 'tools/offline_contract_matrix/matrix_cases.py'
        module = ast.parse((work / rel).read_text(encoding='utf-8'))
        handlers = [{'name': n.name, 'ast_sha256': hashlib.sha256(ast.dump(n, include_attributes=False).encode()).hexdigest()}
                    for n in module.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name != 'seed_all']
        write_new(plan / 'input' / 'case-handler-baseline.json', {'path': rel, 'functions': handlers})
        write_new(plan / '.gitignore', 'input/runtime/\n')
    # Worker needs a bounded, reproducible input manifest; local dependencies already recorded.
    local_inputs = [{'path': str(p.relative_to(plan)), 'sha256': sha(p), 'bytes': p.stat().st_size}
                    for p in sorted((plan / 'input').rglob('*')) if p.is_file() and 'runtime' not in p.relative_to(plan).parts]
    info = dict(record, lane=lane, plan_id=plan_id, readonly_code=readonly,
                local_inputs=local_inputs, real_calls=0, status='READY_NOT_STARTED')
    write_new(plan / 'INPUTS.json', info)
    write_new(CENTRAL / 'inputs' / (lane + '.json'), info)
    write_new(plan / 'task_plan.md', f'''# {lane} 独立计划

## 目标
实施 START_HERE.md 指定的任务，保持唯一写集与离线成本0。

## 大节点
- A 待开始：现有接口/固定预期/行为RED。
- B 待开始：共用实现与集中快测。
- C 待开始：真实离线E2E、恢复、交接、正常commit、STOP。

## Next Step
读取 START_HERE.md、HANDOFF_CONTRACT.md、INPUTS.json，核对固定输入后开始节点A。

## 责任边界
本包只写本卡allowlist。母PWF/主线/安装由ROOT负责，不等其他包、不读取其WIP、不改生产配置/原件/Dayu/IQS。
''')
    write_new(plan / 'findings.md', '# 初始事实\n\nROOT已准备独立worktree与固定输入；详见INPUTS.json。未实现、未运行未来测试，不能预填PASS。\n')
    write_new(plan / 'progress.md', '# 准备记录 — 2026-10-11\n\nREADY_NOT_STARTED：ROOT准备施工卡和固定输入，worker尚未开工。真实provider/LLM成本0。\n')
    summary.append({'lane': lane, 'plan_id': plan_id, 'card': str(central_card), 'workdir': str(work),
                    'start_here': str(plan / 'START_HERE.md'), 'base': record['base_commit'],
                    'branch': record['branch'], 'card_sha256': sha(central_card),
                    'input_manifest_sha256': sha(plan / 'INPUTS.json'), 'readonly_file_count': len(readonly)})

write_new(CENTRAL / 'handoff_contract.md', COMMON)
write_new(CENTRAL / 'dispatch.json', {'schema': 'w07-root-dispatch/1', 'state': 'READY_NOT_STARTED', 'lanes': summary,
    'root_only': ['mother PWF', 'CWP W04 integration', 'FF/ET production cutoff publication', 'G2 real summaries', 'G4/G5 forecast/reviews', 'main merge/skill install/exact CI']})
write_new(CENTRAL / 'README.md', '''# W07 三条独立施工线

三包工作目录已经准备，均可现在同时开工。每包的独立卡包括已有上下文、明确写集、固定API/输入、A/B/C大节点测试和交接格式；自己的 `.planning/<id>/START_HERE.md` 是本地副本。

| 包 | 工作内容 | 独立施工卡 | 工作目录 |
|---|---|---|---|
| W07-FF-PERF（优先） | 原41场景不减，修准备/进程/proof共同超时 | [卡](cards/W07-FF-PERF.md) | C:/Users/郑曾波/Projects/_harness_worktrees/w07/ff-matrix-efficiency |
| W07-RF-MODEL | 8类原生模型组合反例矩阵 | [卡](cards/W07-RF-MODEL.md) | C:/Users/郑曾波/Projects/_harness_worktrees/w07/rf-model-quality |
| W07-AUDIT-ANALYST | 买方模型8类风险的只读诊断 | [卡](cards/W07-AUDIT-ANALYST.md) | C:/Users/郑曾波/Projects/_harness_worktrees/w07/audit-analyst-quality |

## 接口与调度
不等彼此：Audit直接消费ROOT固定native JSON，不依赖RF新工具；FF直接消费ET/CWP固定code-only，不依赖ROOT浮动工区。三包不同仓/不同目录；共享安装和main只由ROOT写。输入记录是可复現工程证据，不增加许可/签收门。只在A/B/C三大节点测试。

ROOT同步推进W04原生召回并线→G2真实摘要/RF消费；FF包完成后ROOT接收固定41全链并发布FF/ET；RF/Audit包接收后辅助G4原三公司和G5新三/指定八公司独审，不能替代真实公司执行。W04/G2/G4/G5仍开放。

母计划入口：[ROOT接收状态](../w06_parallel_verification_2026-10-11/ROOT-reception-status.md)。接口格式：[交接契约](handoff_contract.md)。分发清单与commit/输入固定信息：[dispatch.json](dispatch.json)。

```
                     ROOT（母计划 / 主线 / 安装）
                     │ W04 → G2 → G4 → G5
        ┌────────────┼────────────────┐
        ↓            ↓                ↓
   FF固定41提速   RF组合测试      Audit风险诊断
        └────────────┴────────────────┘
                     ↓
                ROOT接收与集成
```
''')
write_new(CENTRAL / 'task_plan.md', '''# W07 分包总计划

## 状态
准备完成，三个包READY_NOT_STARTED。用户尚未报告开工，禁止标记实现完成。

## 阶段
1. 完成：只读调查、实际独立worktree、固定接口/输入/唯一写集。
2. 完成：三个独立卡、独立PWF、共用交接格式、本地副本。
3. 待实施：各worker A/B/C → ROOT一次集中接收 → 正常主线/安装/精确CI。

## Next Step
用户分发三卡；ROOT继续W04集成与G2，等待交付后依照卡范围接收。

## 不增加门禁
不创建授权JSON/逐材料许可、私人/public分类、重复来源身份合同、每小节点签收或第二任务库。保留原件、配置资源限额、所属层实际字节/期间和大节点质量测试。
''')
write_new(CENTRAL / 'findings.md', (HERE / 'findings.md').read_text(encoding='utf-8'))
write_new(CENTRAL / 'progress.md', '# 2026-10-11\n\n三个独立worktree/卡/PWF/输入已准备；母接口固定，worker尚未开工。0付费调用。ROOT仍负责W04/G2/G4/G5与主线接收。\n')
write_new(HERE / 'dispatch-record.json', {'central_root': str(CENTRAL), 'lanes': summary})
print(json.dumps({'prepared': len(summary), 'central_root': str(CENTRAL),
                  'readonly_files': {r['lane']: r['readonly_file_count'] for r in summary}}, ensure_ascii=False))
