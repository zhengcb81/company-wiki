# RF W04–W06 独立工程验收

验收日期：2026-10-09。结论：**RETURN_FOR_REPAIR，当前 HEAD 暂不可并线**。发现 4 个可复现的绑定缺陷；全部反例同时被 native `run_forecast` 和 `validate_published_forecast(result, input)` 接受。修复后在同一集中节点复验，不增加小节点审批或人工签收。

## 版本、范围与边界

- RF 工作树：`C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/rf-inputs`。
- Branch：`codex/pool-rf-source-context-20261009`。
- 实际 HEAD：`b62161c81d5a343e08aab4bf7d0ca15dd2e8ab8c`。
- 验收 diff base：`8b48a99f23a19b1fd71a7e051837a55e12bb7d30`。
- 开始时 RF `git status --short` 为空。只读 RF、安装与主线计划，未改 RF 代码、测试、配置、安装或共享 PWF。
- 已读 CWP `AGENTS.md`、主线 `task_plan.md` 的当前 Next Step，以及 W04/W05/W06 的 `HANDOFF.md`、`handoff.json`、对应变更、责任测试、CLI recipe 和新增参考契约。
- CodeGraph status 返回指定 RF 工作树未初始化。按本次只读范围继续阅读已知文件，未初始化索引。
- 所有运行输入均来自 RF 自带 synthetic engineering fixtures，经内存修改；没有读取或改变公司原件，没有供应商、模型或下载调用。没有新增 RF forecast 成品。报告只记录工程反例，不是商业公司四路审查。

## 已复核的工程实现

W04 保留 FF v2 完整机器结果、独立 transcript 失败状态、producer-owned calls/downloads 与 unknown/null；source-only API 保留兼容。Latest 使用 producer-resolved fiscal year，exact year 保持严格；原件经既有一次 reader receipt/manifest/SHA 路径核验。合法非财报 null fiscal year 与 financial-report 严格期间分开，registered pathless source 复用同一 SourceCapture builder。Narrative 仅选择已解析 span，加入现有 claim/parameter，再追踪至真实 driver formula；只读取、未绑定的摘要保持 `not_consumed`。

W05 typed quarter 使用季度参数，不乘四；YoY 使用各情景自己的前期路径，并将派生金额标为 `analyst_derived`。Communication scope 显式记录 selected/read/skip 与 interval；boundary-only filing 和 filing 冒充 earnings call 均有责任测试。Legacy 缺少 scope 可诊断为 `semantically_unverified`，没有增加模型访问许可。

W06 的 role、inventory、range-to-native-formula 与限定 Q4→next-Q1 stress bridge 均为可选扩展；旧 `stable-fsum/1` 权重、总分与 golden 行为保持原算法。`referenced_range` 与实证概率/预测准确率区分，缺范围保留 null/unverified，shared constraint 仍使用既有 engine。

交接记录分别给出 W04 146 项及合法非财报 follow-up 75 项，W05 66 项及 boundary follow-up 13 项，W06 105 项 + 167 subtests 的集中 GREEN。已读实际 CLI subprocess 测试：W05 native validate→compute/render→snapshot，W06 assembly→同一 native pipeline；对应工具实现将 publication registry 限定在 owned output。此处为**复核交接证据和测试实现**，本验收没有重复运行这些套件或 CLI，也没有将 synthetic CLI 成功升级为真实 M2 经济审查。

## 实际问题与合理修复

### F1 / P1：季度目标参数没有绑定目标分部

定位：`scripts/research/target_measurement.py:70–77, 151–153`。当前只检查参数全局 used、期间、scenario、dimension/currency/scale，然后直接把指定参数相加；没有验证它们进入目标 scope 对应的实际分部路径。

最小操作：使用 `tests/test_target_measurement_comparison.py::quarter_document()`，仅将第一个 target 的 `scope.name` 从 `Segment A` 改为 `Segment B`，其余输入不变。

实际：两次正式校验均通过。Quarter Base `modeled_value=108000.0` 来自 Segment A 的 `quarter_base`；目标却写为 Segment B。Segment B 实际年度 recognized path 只有 FY2026=55.00000000000001、FY2027=60.50000000000001。这不是输入无法解释的经济假设，而是已存在 DAG 与目标 scope 的结构矛盾。

影响：另一个分部的季度收入能被输出成目标分部的收入与达标情况。

合理修复：在同一 typed target 责任层，从原生 segment/scenario/year driver DAG 构造参数祖先关系，核对季度参数进入指定 scope 的实际路径；company scope 按其已声明组成处理。全局 used 不能代替 scope 归属。明显矛盾应拒绝，无法证明归属则保持不可比/gap，不推断季度值或增加人工许可。

Owner test：在 `tests/test_target_measurement_comparison.py` 增加上述跨分部反例，保留正确 Segment A quarter、company 合法组成与 legacy annual 行为。

### F2 / P1：mechanism observation 可重指向无 claim 绑定的参数

定位：`scripts/research/evidence_roles.py:45–55, 183`。Observation 仅核对 claim ID/role 和参数 ID 是否存在；positive mechanism support 集合直接取 observation 声明的 parameter IDs，没有核对 claim 的既有 target 关系。

最小操作：使用 `tests/test_research_evidence_roles.py::research_document()`，将 observation 的 `parameter_ids` 改为 Segment B high FY2027 的 `1_high_2027`，`scope="Segment B"`、`period="FY2027"`。Claim 保持 `target_type="parameter"`、`target_id="0_base_2026"`，仍实际绑定 Segment A Base FY2026。

实际：两次正式校验均通过；`confidence.research_adequacy.mechanism_adequacy.supported_parameter_ids=["1_high_2027"]`。原 claim 没有支持这个新参数。

影响：一个已检查 claim 的机制角色能转移到另一个分部/情景/年度，输出虚假的结构支持；旧 confidence score 没有因此改动，也不能消除该诊断错误。

合理修复：校验 positive observation 与原 claim target/parameter claim_ids 或明确的 native derived dependency 的关系，并核对声明的期间/scope 与目标关系。Growth-driver claim 按其真实 driver 关系处理，counterevidence 仍允许相关性表达；不能把所有研究观察强行限定为 direct exact-value claim。关系不明只保留 unverified，不能列为 supported。复用现有 claim/parameter/driver 索引，不新增 source registry 或访问门禁。

Owner test：在 `tests/test_research_evidence_roles.py` 增加上述无绑定重指向反例，保留正确机制、历史基准与 counterevidence、已声明 derived bridge、旧总分与 golden。

### F3 / P1：typed numeric range 绕过来源 claim 的期间与单位绑定

定位：`scripts/research/targets.py:417–425` 以及 typed dispatch `468–474`。`raw_value is None` 的 range 分支只要求 `extracted_value` 为 null，随即跳过 unit/period 核对；typed validator 没有补回这些来源约束。

最小操作：使用 `quarter_document()`，把该 target 的原始 exact-value claim 改为 `unit="EUR billion"`、`period="FY2030"`，其他内容和 raw target 保持不变。

实际：两次正式校验均通过；输出 target period `FY2026Q3`、comparison unit `USD million`、`comparison_status="comparable"`、`meets_target=true`。Claim 的 FY2030/EUR 与 raw target 的 FY2026/USD 已发生显式矛盾。

影响：来源支持与 target 元数据的期间/币种/scale 不一致时，仍可生成规范化范围和达标判断。

合理修复：numeric range 仍须核对 claim 的原单位与 raw_unit、财政期间与 target_period，以及新 typed measurement period 可获得的明确绑定。只有点数值校验应由 range 端点规则替代，不能取消已有 unit/period 约束。缺少可比期间或单位时保留原文和 gap；不凭文本关键词填币种、端点或季度，不改 qualitative legacy 的兼容语义。

Owner test：在 `tests/test_target_measurement_comparison.py` 分别覆盖 wrong unit 与 wrong period 的 numeric range，保留合法 billion→million 转换、range 两端点、unmodeled_data_gap。

### F4 / P2：typed annual/YoY 留下两套互相矛盾的 measurement period

定位：`scripts/research/target_measurement.py:50–64, 78–80`。实现核对 `target_period` 与 typed period，却不核对 legacy `measurement_periods` 与 typed annual period；比较和重算只使用 typed period。

最小操作：使用 `tests/test_target_measurement_comparison.py::yoy_document()`，只把 target 的 `measurement_periods` 改为 `["FY2026"]`；`target_period` 和 `comparison_basis.period` 仍为 `FY2027`。

实际：两次正式校验均通过；同一输出 target 仍携带 `measurement_periods=["FY2026"]`，`scenario_comparison.base.period="FY2027"`。

影响：一份 validated target 携带两种期间，其他消费者使用 legacy 字段可与原生比较结果产生不同语义。

合理修复：typed annual/YoY 要求既有 single annual measurement period 与 typed period 一致；quarter 分支继续明确自身期间并保持原有不 annualize 的规则。需要迁移时使用明确版本/规范化，不能保留冲突字段或把 quarterly 缺失值改成年度。

Owner test：在 `tests/test_target_measurement_comparison.py` 增加上述 annual/YoY period disagreement，保留 legacy annual 输出形状、typed 正确同比及 null denominator。

## 可复制的集中最小复现

以下脚本不包含原件，可在指定 RF 工作树用 `python -X utf8 -B -` 从 stdin 执行；RF fixtures 是 synthetic engineering inputs。脚本仅在内存中修改输入，不生成 forecast 文件或缓存。不安装、不调用供应商。修复前 4 个 `unexpectedly_accepted` 均为 true；修复后应拒绝明确矛盾或返回语义正确的 unverified/not_comparable。

```python
import json
from pathlib import Path
import sys

root = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\cmrf-20261008\rf-inputs")
sys.path[:0] = [str(root / "scripts"), str(root / "tests")]
from revenue_core import run_forecast
from revenue_report import validate_published_forecast
from test_target_measurement_comparison import quarter_document, yoy_document
from test_research_evidence_roles import research_document

results = []
def run_case(case_id, data, select):
    try:
        result = run_forecast(data)
        validate_published_forecast(result, data)
        results.append({"id": case_id, "unexpectedly_accepted": True,
                        "observed": select(result)})
    except Exception as exc:
        results.append({"id": case_id, "unexpectedly_accepted": False,
                        "exception": type(exc).__name__, "message": str(exc)})

d = quarter_document()
d["management_targets"][0]["scope"]["name"] = "Segment B"
run_case("F1", d, lambda r: r["management_target_coverage"]["targets"][0])

d, original_pid, claim = research_document()
other_pid = d["segments"][1]["scenarios"]["high"]["driver_parameter_ids"]["revenue"][1]
d["operating_research"]["observations"][0].update(
    parameter_ids=[other_pid], scope="Segment B", period="FY2027")
run_case("F2", d, lambda r: r["confidence"]["research_adequacy"]["mechanism_adequacy"])

d = quarter_document()
t = d["management_targets"][0]
c = next(c for c in d["evidence_claims"] if c["claim_id"] in t["claim_ids"])
c.update(unit="EUR billion", period="FY2030")
run_case("F3", d, lambda r: r["management_target_coverage"]["targets"][0]["scenario_comparison"])

d = yoy_document()
d["management_targets"][0]["measurement_periods"] = ["FY2026"]
run_case("F4", d, lambda r: {
    "measurement_periods": r["management_target_coverage"]["targets"][0]["measurement_periods"],
    "comparison_period": r["management_target_coverage"]["targets"][0]["scenario_comparison"]["base"]["period"]})
print(json.dumps(results, ensure_ascii=False, indent=2))
```

## 实际运行记录与停止条件

1. 只读版本/diff 检查：exit 0，实际 HEAD/branch 与派单一致，RF 工作树干净。
2. 第一批内存 probes：exit 0、1.250 秒。F3、F4 均意外通过 native compute 和 strong output validation。该批还包含一个同 SHA/不同 synthetic trace 的探索；未计为本次签收缺陷。F2 该批结果打印访问缺失的 `claim.period` 导致 KeyError，**不是 native 拒绝或有效 RED**。
3. 第二批内存 probes：exit 0、0.894 秒。F1、F2 均意外通过两次正式校验，返回值如上。F2 改用 `claim.get("period")` 后实际 claim period 为 null。另一个 range-reference 探索在 fixture 重建后 role 矛盾而拒绝，未计为缺陷或签收测试。
4. 所有 4 个最终 findings 都有成功完成 compute/strong validator 的实际结果；总共 4 个工程 false-negative，不把 Python process exit 0 称为工程通过。
5. MAIN 在收到 4 个绑定问题后明确要求停止扩大可选测试、交回原 owner 修复。未重复全套或追加门禁；未运行供应商、模型、下载、真实公司四审、M2/M3、安装、merge/push。

下一步由原 RF owner 在同一 W04–W06 责任包根治绑定关系，保留正常 legacy 兼容与旧稳定算法，然后提交精确新 HEAD供同一集中工程节点复验。**本次工程结果不替代真实两组三市场研究验收，也不等于真实 M2 经济审查。**
