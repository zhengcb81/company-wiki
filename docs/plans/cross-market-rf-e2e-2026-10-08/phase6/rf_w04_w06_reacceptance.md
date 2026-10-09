# RF W04–W06 同一重大节点独立复验

日期：2026-10-09。结论：**ENGINEERING_PASS，原 F1–F4 已关闭，可由 MAIN 并线该精确 HEAD**。此结论只覆盖原四项绑定修复和合法/兼容性对照，不替代真实 M2/M3 或两组三市场研究审查。

## 精确版本与范围

- 工作树：`C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/rf-inputs`。
- Branch：`codex/pool-rf-source-context-20261009`。
- 实际复验 HEAD：`a73705171bf9704b313e2f3ed8fff9fda33233e4`。
- 绑定修复 base / 原独立拒绝 HEAD：`b62161c81d5a343e08aab4bf7d0ca15dd2e8ab8c`。
- W04–W06 整包 diff base：`8b48a99f23a19b1fd71a7e051837a55e12bb7d30`。
- Functional repair commit：`36743282f39e9e6c4a958693a3f22a57380ccab5`。
- 只读复核 `docs/implementation/pool-w04-w06-binding-repair/HANDOFF.md`、`handoff.json`、4 个原责任文件的 diff、新 `research/native_dependencies.py` 和 17 项 binding tests。沿用已读取的 AGENTS 与主线 Next Step。RF CodeGraph 缺索引的既有状态未被修改，已知文件直接读。
- RF 开始和结束均 clean，最终 HEAD 没有漂移。交接清单 7 个 changed-path SHA-256 与实际字节全部一致。
- 原拒绝报告和最小复现保留在 [rf_w04_w06_acceptance.md](rf_w04_w06_acceptance.md) / [JSON](rf_w04_w06_acceptance.json)，没有覆盖旧结果。

## 四个原反例实际复验

原 synthetic fixture 和 mutation 保留，只把预期改为对应 `ForecastInputError`；每项尝试 native `run_forecast`，成功才调用 `validate_published_forecast(result, input)`。4 项均在 native input validation 的责任边界拒绝，异常类型和错误文本均被断言核对。

| Finding | 原触发条件 | 新 HEAD 实际错误 | 结果 |
|---|---|---|---|
| F1 / W05 | `quarter_document()` 的 target scope 改 Segment B，参数仍在 Segment A bridge | `quarter bridge target scope must match its native component ancestry` | PASS |
| F2 / W06 | `research_document()` 的 mechanism observation 改指 `1_high_2027`，claim target 仍 `0_base_2026` | `operating observation parameter binding mismatch` | PASS |
| F3 / W05 | quarterly numeric-range claim 改 `unit=EUR billion`、`period=FY2030` | `management target claim unit mismatch: five_year_revenue_goal` | PASS |
| F4 / W05 | YoY typed FY2027，但 `measurement_periods=[FY2026]` | `typed comparison measurement periods mismatch` | PASS |

共用根因修复已落实：quarter 参数经实际 segment/scenario/year driver ancestry 归属 scope；positive observation 经 parameter claim target/claim_ids 或确切 growth-driver evidence node 绑定真实 downstream DAG；numeric range 仅跳过单点数值核对，保留来源 unit/period 与显式 currency/scale/measurement_period；typed annual/YoY 和既有 annual measurement period 一致。

该 helper 使用现有参数、claim、driver 索引，没有新来源登记库、第二计算器、模型访问许可或人工签收。Unknown scope 不被提升为 supported；来源信息缺失只允许明确 unmodeled/out-of-horizon gap。没有把全部新字段变成许可门禁。

## 集中责任测试及合法 positives

实际命令（在上述 RF 工作树执行）：

```text
python -X utf8 -B -m pytest tests/test_native_research_bindings.py tests/test_target_measurement_comparison.py::test_yoy_uses_each_scenario_denominator_and_separate_derived_dollars tests/test_target_measurement_comparison.py::test_zero_denominator_stays_null_in_native_output tests/test_target_measurement_comparison.py::test_existing_annual_target_keeps_the_original_output_shape tests/test_research_evidence_roles.py::test_optional_diagnostic_separates_documentary_presence_and_unknown_magnitude tests/test_research_evidence_roles.py::test_calibration_recomputes_existing_formula_units_and_keeps_unknown_null tests/test_research_evidence_roles.py::test_declared_history_header_and_pc_weakness_cannot_be_positive_mechanism tests/test_research_evidence_roles.py::test_numeric_historical_baseline_keeps_history_role_without_future_support -q -p no:cacheprovider --basetemp C:/Users/郑曾波/AppData/Local/Temp/rRA-f0321618/p
```

实际结果：**25 passed in 0.86s，exit 0**。其中新 binding file 17 项，原合法/兼容性对照 8 项。合法输入都实际完成 native compute 和 strong output validation：

- 同分部季度 derived ancestry、公司季度真实分部组成、缺一个 component 的拒绝。
- 真实跨年度 derived mechanism、exact growth-driver evidence-node 绑定、unknown product scope 留 unverified。
- 合法 USD billion→million range、来源 unit/period 缺失时明确 gap、显式 currency/scale/measurement-period 冲突拒绝。
- 正确 annual/YoY measurement period、各情景自身同比基期、零基期保持 null、legacy annual output shape。
- 中文/英文 history 与 weak-demand 角色边界、历史数值保持 history_base、referenced-range/native formula 和 null unknown。
- 可选 research adequacy 与同一输入去掉可选字段后的旧 `stable-fsum/1` score/components 一致，篡改 adequacy 被 strong validator 拒绝。

未重复 owner 的 201 项 + 167 subtests、全套 pytest、静态检查、CLI pipeline、供应商或真实公司四审。Owner 交接中的五个 golden hash 等证据已阅读，没有将其计入本次独立实际测试数量。

## 原四条 stdin 复验命令

实际为 PowerShell 单引号 here-string 经管道传入 `python -X utf8 -B -`，exit 0，0.724 秒。以下代码与实际四项验证一致，不包含原件，不产生 forecast 文件或缓存：

```python
import json
from pathlib import Path
import sys
root = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\cmrf-20261008\rf-inputs")
sys.path[:0] = [str(root / "scripts"), str(root / "tests")]
from revenue_core import ForecastInputError, run_forecast
from revenue_report import validate_published_forecast
from test_target_measurement_comparison import quarter_document, yoy_document
from test_research_evidence_roles import research_document

results = []
def check(case_id, data, expected):
    try:
        result = run_forecast(data)
        validate_published_forecast(result, data)
    except ForecastInputError as exc:
        assert expected in str(exc), str(exc)
        results.append({"id": case_id, "result": "PASS", "message": str(exc)})
    else:
        raise AssertionError(case_id + " original contradiction unexpectedly accepted")

d = quarter_document()
d["management_targets"][0]["scope"]["name"] = "Segment B"
check("F1", d, "quarter bridge target scope")
d, original_pid, claim = research_document()
other_pid = d["segments"][1]["scenarios"]["high"]["driver_parameter_ids"]["revenue"][1]
d["operating_research"]["observations"][0].update(
    parameter_ids=[other_pid], scope="Segment B", period="FY2027")
check("F2", d, "operating observation parameter binding")
d = quarter_document()
t = d["management_targets"][0]
c = next(c for c in d["evidence_claims"] if c["claim_id"] in t["claim_ids"])
c.update(unit="EUR billion", period="FY2030")
check("F3", d, "management target claim unit")
d = yoy_document()
d["management_targets"][0]["measurement_periods"] = ["FY2026"]
check("F4", d, "typed comparison measurement periods")
print(json.dumps(results, ensure_ascii=False, indent=2))
```

## 临时目录、环境与写入边界

Owned TEMP：`C:/Users/郑曾波/AppData/Local/Temp/rRA-f0321618`。创建前不存在；TEMP/TMP 与 process-only `REVENUE_PUBLICATION_REGISTRY` 指向该目录。`finally` 恢复环境，确认 resolved cleanup target 在系统 TEMP 内且 basename 为该唯一 `rRA-*`，随后仅删除这个根目录。

实际输出：`root_final_absent=true`、`temp_restored=true`、`tmp_restored=true`。Registry 的旧 absent 经 PowerShell `.NET SetEnvironmentVariable` 返回时，raw equality 检查输出 false；该设置只存在于随后退出的测试 shell，没有改 host/user/machine 环境。没有隐瞒该输出。单独复核 absent 的显式 `Remove-Item Env:\REVENUE_PUBLICATION_REGISTRY` 恢复方法后，实际 `initial_state=absent`、`final_state=absent`、`registry_restored=true`；未重跑任何测试，也未改项目文件。

供应商/模型/下载调用均 **0**；公司原件读取/改写/删除 **0**。未改 RF 代码、测试、生产配置、安装或共享 PWF；未提交、merge 或 push。此次仅新增本文件及同名 JSON。

最终判断：原四条已关闭，没有本轮 focused 范围内剩余可复现问题。MAIN 可继续既有并线与后续真实研究流程；工程 PASS 不意味着 current-company magnitude、预测准确率、真实 M2/M3 或两组独立研究验收已通过。
