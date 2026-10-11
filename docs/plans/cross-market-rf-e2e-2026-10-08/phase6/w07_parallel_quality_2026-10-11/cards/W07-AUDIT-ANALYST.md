# W07-AUDIT-ANALYST：买方模型风险诊断包

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
