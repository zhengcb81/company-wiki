# W07-AUDIT-ANALYST 大节点独立试读

日期：2026-10-11。角色：独立 reviewer。结论：需要修复后再做大节点复验；当前不能把作者的 59 项测试及 13 项 E2E 通过等同于观察契约已满足。

## 范围与方法

只读审查 `C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception` 中的脚本、analyst-risk-audit/reference、review-analyst、作者测试/fixtures、handoff/test-summary。读取当前实际安装的 revenue-forecast-audit/SKILL.md 和目标仓 AGENTS.md。未读取其他 reviewer 初稿，未修改产品、测试、git、安装目录；未跑全仓、网络、模型或 provider。唯一落盘产物为本报告。

在目标 tree 运行 `python -B -`，用 importlib 加载 `tests/test_w07_analyst_risk_audit.py` 中的合成 builder，然后只调用纯函数；不执行 unittest/pytest/CLI，不创建 attempt 或临时目录。下列反例均已实际运行，退出 0；输出是诊断报告 JSON，未伪造经济 PASS。

所审脚本 SHA-256：`f563cb802a538279bd933c68dc3f89a10afd3a53814ed7592409d1cddb92c04b`，与作者 handoff.json 一致。行号以下均指该版本。

## 已满足的边界

八 checkpoint 始终存在；诊断状态只有 OBSERVED/UNRESOLVED/NOT_CHECKED；顶层 `source_truth_verified=false`、`economic_reasonableness=not_evaluated` 保持固定。脚本没有调用 SourceReader/provider/LLM、RF validator/DAG/forecast，也没有重算公式。以上是技术边界观察，不是模型质量结论。

## 发现

### IR-01 [P1] A18 仅期间就可制造 actual coverage，未绑定 actual 的 WAPE 被发布

位置：`analyst_risk_audit.py:635`–`682`。

context actual_input 只读取 period；historical_accuracy_records 只读取 years/period。value、unit、实际值内容/实际输入引用是否存在完全不检查。提供 `[{'period':'FY2026'},{'period':'FY2027'}]` 及 `wape=0.0, observations=2`，A18 整体为 OBSERVED，`years_checked=['2026','2027']`，`years_unchecked=[]`，`wape=0.0`。只有 `{'period':'FY2026'}` 的 context 也会生成 `actuals_indexed` OBSERVED finding。

另一个实际反例：没有任何 actual records/context，只给 `wape=0.1, observations=2`，A18 为 NOT_CHECKED，却仍输出 `actual_input_refs.wape=0.1`；partial 检查依赖 checked_years 非空及列表长度，不能证明错误指标实际覆盖范围。

影响：不存在的未来 actual 可成为已检查年度，零误差仍可经该诊断传播。违背 A18 明确要求：缺 actual 保持 null，不能把 N/A 当零误差。

建议：分别索引“record 元数据存在”和“实际数据可观察”；actual 必须有合法数值（0 合法）、期间、单位及当前输入里可解析的实际数据内容/引用。原生 RF 的合法历史记录如仅有外部 actual 引用，保留记录引用并列缺口，不臆造 actual；不发起来源重采。WAPE 只在其自身声明的可观察 actual 范围可核对时作为已绑定值，否则 null 并列 unresolved。不要要求真实未来 actual，也不要添加人工许可门。

### IR-02 [P1] A02 全局字符串相交代替参数解析与分部收入路径绑定

位置：`analyst_risk_audit.py:158`–`209`。

`linked` 只判断 driver.parameter_ids 是否出现在全局 revenue_ids；不要求参数存在。`make_input(parameters=[])` 保留默认 driver/scenario，实际 A02 为 OBSERVED、missing_fields 空。年份还会从 ID 尾部推断，使缺失参数看起来拥有合法期间。revenue_ids 合并 input 与 forecast，且没有按 driver.segment_attribution 绑定到对应分部。

影响：不存在的参数，或其他分部/仅 input 的收入路径，可能被诊断为已连入当前 forecast。reference 明确写“resolve in input.parameters”“appear in forecast…revenue”。

建议：索引原生 forecast 的 segment/scenario/parameter 路径；参数必须存在，并用声明 period核范围。缺 period/horizon 或对应段路径应保留 unresolved，不以 opaque ID 年份后缀冒充期间。

### IR-03 [P1] A06 calibration 存在即被认为支持该 cell，输出与 segment/year/parameter 未绑定

位置：`analyst_risk_audit.py:305`–`344`。

给 default supported Segment A/base/FY2026 cell 关联一个 `scope='Segment Z'`、`scenario_output_parameter_ids={'base':'missing_2029'}` 的 calibration，实际该 A06 finding 仍为 OBSERVED。脚本只检查 calibration_id 能查到、formula/observed_period/output_unit/base-output 非空；不检查输出参数存在、输出期间、cell 的 supported_parameter_ids 或 calibration scope。部分 calibration ID 缺失也可能被过滤后忽略。

影响：其他段/其他年或不存在的 conversion output 可以覆盖当前 supported cell，违背 reference 的“resolvable scenario_output_parameter_ids”及逐 cell 粒度。

建议：逐引用诊断 calibration/output 参数缺口，绑定到 segment/scenario/year 和该 cell 原生 supported 参数；不重算 formula。保留合法 analyst_assumption，不扩大证据覆盖范围。

### IR-04 [P1] A08 缺 metadata/未审 target 可被一条 note 覆盖，字符串 false 被当 true

位置：`analyst_risk_audit.py:365`–`412`。

实现未按 `(target_type,target_id)` 分组，只合并 note 引用的 claim 的 source_id。实际复现：不同 target 的两个 claim 分别来自 filing/survey，加一个不存在的 claim，note 的 `source_ids=['unrelated']`、`independent='false'`，仍为 `independence_metadata_present` OBSERVED。另已单独复现：note 完全没有 source_ids，只引用两条不同来源 claim、independent=true，也会被观测为 metadata present。

再用 p1 的独立 claim 对并给其 note，加入 p2 两条同源 claim，没有 p2 的 independence metadata；整体 A08 仍 OBSERVED，p2 不进入缺口。management_targets 不涉及引用时生成 management_target_separated，这个附加 finding 不修复遗漏 target。

影响：不同命题/不同 target 的来源被混为同一命题的独立支持；缺失引用、错误 source metadata 或未审 scope 消失。reference 明确要求分组、note 命名 claim/source、无 metadata 保持未知。

建议：对相关 target 分组，严格 `independent is True`；所有引用 claim/source 必须在当前 native 文档里可核对且一致，遗漏 metadata 的组输出 independence_unknown_not_assumed。source_ids 不同只证明声明的源不同，不证明经济独立性；维持人工经济判断待办，不把它升为 PASS。

### IR-05 [P1] A10 “dated baseline”仅检查字符串非空，公告后基准及错误 driver 年度仍 OBSERVED

位置：`analyst_risk_audit.py:432`–`459`。

实际反例：baseline.as_of_date=`2027-01-01`，result.announced_date=`2026-07-12`，二者 period=`FY2026`、unit 相同，comparison driver=`0_base_2027`；A10 仍 OBSERVED，missing_fields 空。把 as_of_date 改成 `not-a-date` 仍 OBSERVED。

影响：后知的基准被索引为可用“超预期”基准，年度不相符的驱动可被认为解释当期差异。合法非空 `ref` 可以是外部说明，因此本审查不要求该 free ref 在 JSON 中一定能解成 pointer；但日期和参数自身期间都是当前文档可观察字段。

建议：解析 ISO 日期，检查基准在公告前可用且不超出 context/native 信息截止日；无法核对时报告 unresolved。comparison driver 期间/单位及适用范围应匹配声明，或显式记录桥接说明；不捏造基准数字或差异金额，不引入外部共识采集要求。

### IR-06 [P1] A13 range 不需要实测期间、合法 source claim 或 scope；derived_from=observation 直接免来源

位置：`analyst_risk_audit.py:486`–`556`。

实际反例：calibration `observed_period=None, scope='Segment Z', source_claim_ids=['missing']`，有 default lower/upper/formula，support 无 cell；A13 整体 OBSERVED、missing_fields 空。脚本对 native calibration 不检查 observed_period/unit/已知 segment/claim 解析；context 若 `derived_from='observation'` 还允许 source_claim_ids 空。coverage declared 集合包含 unresolved range，而且 scenario 不参与覆盖比较。

影响：没有实测出处/支持期的区间可被报为独立 operating range；错误 range 声明还可能遮住 cell gap。reference 明确要求 observed_period、来源、转换和实际支持期。

建议：仅把证据及 scope 可解析的 range 用于覆盖 cell；缺来源/期间/单位保持 null 或 unresolved，逐 scenario/output period 绑定。不能因为写了 observation 就猜来源真实，也不能因看不到实际范围反推出目标范围。

### IR-07 [P1] A17 acting scope 非空即可，虚构段/年/scenario/参数误 OBSERVED

位置：`analyst_risk_audit.py:577`–`603`。

实际反例：joint=true、cross_exposure_declared=true、parameter_ids=['missing']、segments=['Segment Z']、years=[2099]、scenarios=['no_scenario']，A17 整体 OBSERVED。该函数只接收 forecast/context，没有 native parameter 索引；scope 不校验任何成员，finding 的 segment/year/scenario 全为 null。

影响：作用域不存在的“联合压力”声明可让原生单参数 sensitivities 缺口消失（valid=True 后跳过单冲击 finding）。

建议：增加只读 native scope/参数索引用于 ref 解析，严格布尔值和参数组；真实联合作用声明仍可观察，但缺 scope 绑定应 unresolved，单冲击只作为索引保留。不要运行/加总 sensitivities，不要求新模型运行或人工签收。

### IR-08 [P2] A05 约束参数只从 ID 后缀提年份，未知参数也被认为 scope resolved

位置：`analyst_risk_audit.py:217`–`276`。

实际反例：constraint segments=['Segment A']、scenario_parameter_ids={'base':['missing_2026']}，A05 OBSERVED。参数不存在，时期只有字符串后缀。相反，一个合法 opaque ID 没有年份后缀但 input.parameter.period 是 FY2026，会被误当 scope unresolved。context scope.years 同样没有和本次 requested/forecast 年份对齐。

建议：从可解析 native 参数期间索引年份，核适用 segment/scenario/本次范围；不解析未知 ID 作为证据，不创造 CAGR cap，范围不明只报告缺口。

### IR-09 [P2] 文档及交接承诺的 native_evidence_refs 实际不存在

位置：`_finding` 行 132 起；reference “Per-checkpoint observation rules”；handoff “接口”。

reference 与 handoff 声明每个 finding 带 `native_evidence_refs`，但 `_finding` 无该字段。实际 default report 11 个 finding 中此字段出现 0 次。指向外层 driver/calibration/context 的 pointer 可解析，并不证明 claim_ids/parameter_ids/source_ids 等内层引用可解析。

建议：明确 report 字段契约；如需要 native refs，应生成真实解析结果与未解析缺口，不能空填伪引用。measure_check_ids 深度 join 在 handoff 已注明 deferred，可维持该已知边界；不要宣传已消费了未实现的证据 join。

## 可复现入口

在目标 tree 执行以下内存程序即可复现关键高风险路径（无需写夹具、无需网络）：

```python
import importlib.util
from pathlib import Path
s = importlib.util.spec_from_file_location('t', Path('tests/test_w07_analyst_risk_audit.py'))
t = importlib.util.module_from_spec(s)
s.loader.exec_module(t)
def status(cp, **kw):
    r = t.run(**kw)
    return t.checkpoint(r, cp), t.findings(r, cp), r['actual_input_refs']

print(status('A02', native_input=t.make_input(parameters=[])))
print(status('A05', forecast=t.make_forecast(constraints=[
    {'segments':['Segment A'], 'scenario_parameter_ids':{'base':['missing_2026']}}])))
print(status('A06', native_input=t.make_input(calibrations=[
    t.calibration(scope='Segment Z', scenario_outputs={'base':'missing_2029'})])))
print(status('A13', native_input=t.make_input(calibrations=[
    t.calibration(observed_period=None,scope='Segment Z',source_claim_ids=['missing'])]),
    support=t.make_support({})))
print(status('A17', context=t.context_doc(t.statement('stress_declaration',
    {'joint':True, 'cross_exposure_declared':True, 'parameter_ids':['missing'],
     'scope':{'segments':['Segment Z'],'years':[2099],'scenarios':['no_scenario']}},
    checkpoint_id='A17'))))
print(status('A18', forecast=t.make_forecast(
    accuracy_records=[{'period':'FY2026'},{'period':'FY2027'}],
    wape=0.0,wape_observations=2)))

claims = [t.claim('c1','filing',target_id='p1'), t.claim('c2','survey',target_id='p2'),
          t.claim('management','filing',target_type='management_target',target_id='mt')]
print(status('A08', native_input=t.make_input(claims=claims,
    management_targets=[{'claim_ids':['management']}]),
    context=t.context_doc(t.statement('independence_note',
    {'claim_ids':['c1','c2','missing'],'source_ids':['unrelated'],'independent':'false'},
    checkpoint_id='A08'))))
beat = {'baseline':{'kind':'consensus','ref':'feed','as_of_date':'2027-01-01',
                    'period':'FY2026','unit':'USD million'},
        'result':{'period':'FY2026','unit':'USD million','announced_date':'2026-07-12'},
        'comparison_driver_parameter_ids':['0_base_2027']}
print(status('A10',context=t.context_doc(t.statement('beat_claim',beat,checkpoint_id='A10'))))
```

Windows 可以将这段文本通过 here-string 输给 `python -B -`。本轮已运行同构反例（以及上文的 metadata/partial WAPE 变体），不是仅静态推断。

## 作者测试与交接的实际覆盖边界

作者测试覆盖了空字段、同源两 claim、缺 baseline 日期、unit/period 明显不等、unsupported cell、单参数 shock、wape=0 且 observations=0 等路径。它没有覆盖 opaque ID 与真正 period、悬空 ref、不同 target 混合、遗漏 scope、日期格式/公告前后关系、period-only actual、只有 positive observations 但无 actual 的 WAPE。fixture 中的“supported”上下文和测试 builder 允许引用不在 input 中的 claim，因此现有全绿不能建立 reference 中声称的 ref 解析。

修复建议是集中补齐当前原生字段的只读索引、逐引用缺口和 scope 绑定，再用以上反例作为大节点行为验收；维护诊断用途及固定顶层非经济状态。无需增加小节点签收、许可、provider 调用、经济 PASS 或 CWP 研究写入。

## ROOT 修复接收复审（2026-10-11）

所审修复脚本 SHA-256：`11283a4d613e944850be3bdd7f3ed1debcb3bed23ef684a0d1fa4c73197b9340`。

只读复核当前脚本、reference、作者 builder 和新增 `tests/test_root_w07_analyst_scope.py`；仅运行一次有限纯函数内存反例包（退出 0）。未重跑 84 tests、E2E 或全仓；ROOT 报告的 `84+4 subtests PASS`、`13 E2E COMPLETE`、技能结构绿均属 ROOT 的验证记录，本 reviewer 未重复验证。没有网络/模型/provider/产品/测试/git/安装写入。

接收结论：**主要反例已闭合，九项发现尚未全部闭合**。共用引用索引和若干 cell 绑定有实质修复；尚有原报告范围内的四项残余。该结论仅指报告型诊断与 reference 一致性，不构成经济 PASS，也不要求新增小节点许可。

| 原 issue | 本轮复核 |
|---|---|
| IR-01 A18 | 原核心反例闭合：period-only 两年记录、wape=0/count=2 → UNRESOLVED，years_checked=[]，两年 unchecked，wape=null；无 records 但 wape=0.1/count=2 也为 UNRESOLVED、wape=null。有限值/布尔检查及原生 1.1 aggregate 识别已实现。 |
| IR-02 A02 | 缺定义、他段路径和缺 horizon 的主要修复可见；本轮 parameters=[] → UNRESOLVED。仍有 input-only 路径与缺 period 的残余，见 R-01。 |
| IR-03 A06 | 原 wrong scope/missing_2029 output 反例 → UNRESOLVED；已检查 scope、输出参数存在/period/unit及支持 cell 对应参数；缺 calibration refs 不再被过滤后隐去。原核心反例闭合。 |
| IR-04 A08 | 分 target、严格布尔、source_ids 一致性及缺组 metadata 检查已实现；原 string false/混合 target/缺 ref 复合例 → UNRESOLVED。原核心发现闭合。 |
| IR-05 A10 | 日期真实解析、晚于公告诊断、comparison period与 measure_check refs 检查已实现；晚基准+FY2027 driver 对 FY2026 声明 → UNRESOLVED。原核心发现闭合。 |
| IR-06 A13 | 缺 observed_period、无效数值界限、源 claim 查找及仅有效 range 进入 coverage 的修复可见；原 missing period 例 → UNRESOLVED。range scope/output ref 仍不完整，见 R-02。 |
| IR-07 A17 | 虚构 parameter/segment/scenario/year及字符串布尔已不能成为 OBSERVED；原 ghost scope → UNRESOLVED。参数实际年度与声明年度未绑定，见 R-03。 |
| IR-08 A05 | missing_2026 → UNRESOLVED，合法 opaque-cap 能读取声明 period。缺 period 后缀回退及超出 requested horizon 的 scope 仍 OBSERVED，见 R-04。 |
| IR-09 输出字段 | 原字段缺失闭合：本轮所有 finding 带 native_evidence_refs；resolved 标记与已解析 pointer 已实现。顶层 truth=false/economics=not_evaluated 保持。 |

### R-01 [P1，IR-02 残余] 收入路径仍合并 input 和 forecast，缺期间仍从 ID 猜

当前 `_native_paths` 行 85 起仍遍历 `(native_input, forecast)` 并合并角色路径。实际 `t.run(forecast=t.make_forecast(segments=[]))` 的 A02 为 OBSERVED，虽然 reference 要求路径出现于当前 forecast。这会把原始 input 已声明但 draft 没有采用的驱动报为当前结果路径。

另实际删除默认 native_input.parameters 每个参数的 period，A02 仍 OBSERVED：`_param_year` 行 59 起在没有声明期间时继续使用 ID 尾部年份。这里引用确实存在，但 horizon 的期间依据不存在，不能叫可解析的 timing。

建议：明确当前预测结果路径与 input 参数角色的用途，结果路径缺失时报告缺口；禁止在 timing 判定中用 opaque ID 补 period。若 native RF 有合法无 period 参数，应按明确角色规则给 N/A/未知，而不是猜年。

### R-02 [P1，IR-06 残余] A13 range 的 segment 与输出 ref 尚未核对

当前 native calibration 分支行 605–637 检查 bounds、observed_period 非空、claim存在、formula，但不检查 cal.scope 是已知段，也不把 scenario_output_parameter_ids 加入 finding 参数引用。`_calibration_support_years` 仍对未知输出 ID 从尾部取年。

实际单独使用 `t.calibration(scope='Segment Z')`（来源/实测期间保持有效）、`support=t.make_support({})`，A13 整体 OBSERVED；使用 `t.calibration(scenario_outputs={'base':'ghost_2026'})` 同样 A13 整体 OBSERVED。后者 native_evidence_refs 只核来源/calibration，自身输出参数悬空因此不可见。

建议：range 可以作为已登记记录被索引，但 OBSERVED 应要求声明的 segment/output/period/unit 范围可核对；未知 output 加入 unresolved 原生引用并避免进入覆盖集合。没有支持 cell 时也应保留该记录自身的 ref/scope 缺口。

### R-03 [P1，IR-07 残余] joint scope year 与参数的真实作用年未绑定

当前行 720–725 只检查 scope years 都存在于预测年集合、parameter 属于某段/scenario路径。实际声明 parameter_ids=['0_base_2027']，scope years=[2026]、Segment A/base，joint=true/cross=true，A17 整体 OBSERVED。参数 period=FY2027，因此无法证明它对声明 FY2026 有作用。原报告要求 acting scope 与 year 实际绑定，不能仅分别属于同一个更大的预测范围。

建议：将当前已声明参数期间或明确 conversion/exposure bridge 对应到 joint 的 acting years；没有适用说明则 joint_stress_scope_unresolved。不重算模型、不要求付费联合压力运行。

### R-04 [P2，IR-08 残余] A05 年份仍允许 ID 猜测与超出本次预测范围

实际删除参数 `0_base_2026` 的 period，并在 constraint 中引用它，A05 仍 OBSERVED；这继续依赖 `_param_year` 的后缀回退。另 context constraint_note scope Segment A/year 2099，在本次 forecast_years=[2026,2027] 时，A05 仍 OBSERVED、year='2099'。reference 要求可解析适用 scope；这个 scope 不属于本次待审范围。

建议：期间来源为 native parameter.period；context/constraint 的范围和 requested/forecast 范围求交，纯外围范围作为登记信息或 N/A/缺口明确列出，不报当前待审 scope 已观察。

### 单次反例包的关键复现片段

沿用上文 importlib 的 t builder，只调用 t.run；以下本轮均已实际复算，无文件写入：

```python
print(t.checkpoint(t.run(forecast=t.make_forecast(segments=[])), 'A02'))
n = t.make_input()
for p in n['parameters']:
    p.pop('period')
print(t.checkpoint(t.run(native_input=n), 'A02'))
print(t.checkpoint(t.run(calibrations=[t.calibration(scope='Segment Z')],
    support=t.make_support({})), 'A13'))
print(t.checkpoint(t.run(calibrations=[t.calibration(scenario_outputs={'base':'ghost_2026'})],
    support=t.make_support({})), 'A13'))
ctx = t.context_doc(t.statement('stress_declaration',
    {'joint':True,'cross_exposure_declared':True,'parameter_ids':['0_base_2027'],
     'scope':{'segments':['Segment A'],'years':[2026],'scenarios':['base']}}))
print(t.checkpoint(t.run(context=ctx), 'A17'))
n = t.make_input()
n['parameters'][0].pop('period')
fc = t.make_forecast(constraints=[{'segments':['Segment A'],
     'scenario_parameter_ids':{'base':['0_base_2026']}}])
print(t.checkpoint(t.run(native_input=n,forecast=fc), 'A05'))
ctx = t.context_doc(t.statement('constraint_note',
    {'scope':{'segments':['Segment A'],'years':[2099]}}))
print(t.checkpoint(t.run(context=ctx), 'A05'))
```

注意作者 builder 现在会补齐 calibration/driver 默认 source claims，故需要测试“来源缺失”时应在生成后明确移除 evidence_claims；不能仅传一个自命名 source_claim_ids 就假设它不存在。本轮将这个改变作为夹具语义处理，未新增来源真实要求。
