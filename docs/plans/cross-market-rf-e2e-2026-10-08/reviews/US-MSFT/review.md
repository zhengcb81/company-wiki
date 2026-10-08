# Microsoft US-MSFT 独立全量审查

**结论：FAIL。** 审查版本 `2026-10-08-MSFT-v1`，as-of 2026-10-08；审查者 `/root/rf_us_independent_review`，执行者 `/root/rf_us_execution`。

历史收入、官方重述边界、原文身份与年度计算已通过独立复核。未来范围的证据、反证/证伪机制和敏感性单位不通过；新下载、最新年度政策、FF→ET 与 CWP 正式处理仍有真实缺口。formal strong gate 的 PASS 不构成经济审查 PASS。

## 审查范围与证据

- 全部122 claims、90 parameters、16条FY25/26收入流历史、11numeric目标、17项定性旁表、9维研究、6沟通类、4增长根、8敏感性均逐项审查。122 claims 中47项在明确历史/假设惯例范围内支持可接受，75项支持质量FAIL（72未来范围、2增长证据节点、1benchmark），并非75个历史数字错误。
- 42条命令 start/finish 配对、10次失败尝试、54 events、26进程记录、90份manifest产物hash检查；所有命令stdout/stderr完整读入审查replay，逐项失败原因保留。manifest41与最终42差异是seal命令完成时点，最终以ledger42为准。
- [完整机器审查清单](C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/reviews/US-MSFT/review.json)、[精确假设IDs/原文locators建议](C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/reviews/US-MSFT/support/assumption_support_recommendations.json)、[独立计算](C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/reviews/US-MSFT/support/independent_calculations.json)、[日志回放](C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/reviews/US-MSFT/support/execution_log_replay.json)。

## 必须修正的发现

### US-01 · P1 · sensitivity_units

All eight sensitivities are named ±5pp but use shock_value5.0 on ratio-valued annual growth. The runtime adds5.0, so it actually requests±500pp and down cases clamp to-100%. This changes terminal revenue ranges, rankings/concentration and confidence sensitivity component.

**复现：** C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/reviews/US-MSFT/support/independent_calculations.json#/sensitivity; Azure base0.38→requested-4.62/5.38. Actual company terminal290723.665482/1339111.142762 vs intended5pp509274.659962/525707.065562 USDmillion.

**要求：** Executor creates v2 with ratio-unit0.05 shocks under the current runtime, reruns full forecast/Markdown/confidence/strong/snapshot and preserves v1. Independently check all8 requested/effective/clamp values and terminal paths.

### US-02 · P2 · assumption_support

All72 future annual growth rationale_support claims cite only their FY26 dollar-base row on PPT17. The excerpt supports the base scale but not the history growth, operating-demand/supply thesis, scenario spread or FY28/29 fade/recovery. Transparent analyst_assumption labels are correct; checked-support coverage is materially overstated.

**复现：** Review any of these72 claims against the full slide17 annual table and slides18/21. A historical revenue number alone does not support a future causal assumption.

**要求：** Bind full pertinent histories, metric definitions, demand/delivery facts, contrary constraints, quarterly guidance with explicit perimeter limits and outside reference where supportable. Reopen and update each claim/target source list and rationale. Precise per-stream IDs and locators are in support/assumption_support_recommendations.json; do not relabel future scenario percentages as exact source values.

### US-03 · P2 · counterevidence_and_positive_support

consumer_cycle contrary claim110 repeats inventory levels from its supporting claim109; elevated inventory confirms the negative headwind. enterprise_migration positive claim105 cites only license decline, which supports cannibalization but does not establish service expansion.

**复现：** Fresh official call CFO full-year FY27 license/server decline and PC inventory paragraphs, plus CEO gaming FY27 return-to-growth paragraph.

**要求：** Consumer contrary: bind gaming return-to-growth expectation with scope/aspiration limits, and clearly state Windows stabilization evidence gap. Enterprise positive: separate ERP/healthcare/Frontier actual delivery/support history from license headwind; include CRM moderation/longer cycles as actual contrary evidence. Do not manufacture an independent source.

### US-04 · P2 · causal_chain_and_falsifiers

All four roots reuse the same generic chain and leading indicators/falsifiers. Two successive quarters below low-case growth has no declared quarterly threshold in an annual-only model, and for a negative consumer thesis below-low growth reinforces headwinds. The field completeness gate does not make these operational falsifiers.

**复现：** Compare all four identical causal_chain/leading_indicators/falsifiers to each root annual growth parameters and recognition perimeter.

**要求：** Describe each actual mechanism and delivery/accounting bridge, acknowledge unavailable quantity/price data, and use matched annual reported thresholds or separately evidenced quarter thresholds. Make falsifier direction consistent with positive/negative thesis. Regenerate tree/report; weights must still reconcile.

### US-05 · P2 · independent_target_benchmark

claim122 is the only independent_benchmark support for company FY27 double-digit guidance and cites AWS Q237%. It confirms peer quarterly cloud demand, not the independently chosen eight-stream annual company range. All three scenarios mechanically clear the10% linguistic floor, but benchmark evidence does not support magnitude or full scope.

**复现：** Original Amazon opening highlights/AWS segment37% vs official Microsoft company consolidated annual scope.

**要求：** Keep AWS as analogical and bind independent Microsoft restated history and major non-management operating observations/constraints perstream; preserve actual benchmark comparison and management lower-bound interpretation without forcing attainment.

### US-06 · P2 · qualitative_target_semantics

The17-row sidecar keeps16 call passages plus one PPT summary, including annual Xbox recovery, license decline and Windows high-teens. Treatment is generic qualitative_context_or_explicit_data_gap with no per-target parameter/scenario IDs or comparison. Relevant operating promises such as Cobalt200 >25 datacenters by monthend, calendar-year healthcare ~100M encounters, and latest Copilot rollout/usage-billing timing are not individually tracked with revenue relevance/gap explanations. Formal numeric schema cannot represent qualitative targets; this remains a real workflow gap.

**复现：** Full official call CEO platform/healthcare/Frontier sections; CFO FY27 and Q1 guidance; Sep25 strategy communication product-availability paragraphs; PPT21 adjustment table.

**要求：** Executor extends the qualitative sidecar with exact primary locator/period/perimeter/commitment, concrete treatment and pertarget scenario/parameter mappings or an explicit unmodeled reason. Preserve words such as mid-single/high-teens without invented numeric midpoint. Clearly compare FY27 gaming growth expectation with Base-4% disagreement and label quarterly/new-perimeter statements.

### US-07 · P2 · workflow_coverage_blocked

Successful new filing download and subsequent0-download reuse, FY26 latest annual policy, integrated FF companion→ET successful original-language TXT/import, and CWP canonical narrative processing are not demonstrated. Legacy FY26 request removed companion; separate ET probes returned discovery unsupported and entitlement required. Bounded CWP ensure rejects Dayu before provider launch. BS4 temporary HTML is correctly disclosed as non-canonical.

**复现：** Actual42-command ledger: failed FY26 legacy ensure, successful existing FY24/25 reuse, standalone exactET probes only. CWP diagnostic: adapter dayu-sec-cli does not support bounded acquisition.

**要求：** Keep these BLOCKED/PARTIAL in E2E acceptance and distinguish prepared2.0 companion request from actually executed1.2 request. Resolve CWP-owned bounded transport/provider contract in separately scoped work before claiming full download/worker/ET E2E success; no uncapped or paid workaround.

### US-08 · P3 · quarterly_constant_currency_comparability

Azure rationale says annual reported Base38% is deliberately below full-year extrapolation of Q1 CC44-45%. Arithmetic percentage ordering is true, but quarter/annual/FX perimeters differ and this cannot establish a same-basis conservative bound. The formal Q1 targets correctly remain unmodeled and are not multiplied by4.

**复现：** PPT18 annual restated Azure growth vs PPT21 Q1 CC guidance and FX drag.

**要求：** Describe38% as a separate annual reported analyst assumption with capacity and FX uncertainty. Use quarterly CC guidance only as directional/context evidence unless a supported annual bridge exists.

## 独立通过项

- 实际CWP producer重新打开FY25 SEC HTML：8,158,067B，SHA `99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe`。FY June30/公司身份/Income Statements表头及Note1 pp55-57完整上下文核对；nullretrieved保留。自身RF→FF→CWP schema2.0 exact-year reuse返回同一ID，download0。
- 官方FY27 PPT重新取回4,016,522B，SHA `c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`；22页原图全部独立view_image，并逐图与重新下载OOXML内media匹配。第4/7-9/13/15/17/18/20-21页均实读，不凭历史记忆否认新两分部。
- Microsoft三网页字节hash随trace ID变化；独立归一化word diff仅一条动态trace token，其余实质财务/完整call/指标内容一致。AWS原件hash完全一致。9/25、9/28、10/1官方博客另行重新web打开核对。
- 所有公司/分部年度值与原强校验产物一致：8×3×3年度流、3×3公司路径、两组3×3、CAGR、increment、27排序、权重归因及排名。无RPO、Cloud或annualizedrun-rate重复入账；无季度×4转换。
- 在reviewer独占TEMP用真实installed CLI重新validate-only、forecast、Markdown、snapshot，并强校验、正式renderer相等和全部确定性字段比较。11份installed/repo/manifest runtime SHA一致。5条mixed流限于already-recognized direct_growth/direct_revenue、不带progress/lag/carry-in转换，认收入fallback完整披露。
- publication_registry.py 的实际audit CLI对原合法结果返回0；installed/repo SHA `55914762ef0abb6db37055cb21616162712a6559ecd7e6e324c3162bd7fb0b68`，forecast/registry/snapshot前后hash未变。现源码audit artifact循环仍仅核registered input anchor，因此此项只证明原合法结果审计通过，未认证tampered结果tuple拒绝；另行strong input-required已验证。
- baseline4配置hash、原input/result/md/snapshot before-after未变。无reviewer对config/runtime/raw/executor共享状态写入；工作仅review目录和独占TEMP。

## 独立收入流核对（USD million）

| 流 | FY25 | FY26 | 新报告组 |
|---|---:|---:|---|
| Azure | 72,610 | 101,938 | Agents and Infra |
| Microsoft 365 cloud | 84,605 | 100,299 | Agents and Infra |
| Productivity and server licensing | 35,391 | 37,285 | Agents and Infra |
| Industry solutions | 18,417 | 20,345 | Agents and Infra |
| Frontier and support services | 7,760 | 8,260 | Agents and Infra |
| Search and advertising | 22,171 | 24,835 | Devices and Consumer |
| XBOX | 23,455 | 21,790 | Devices and Consumer |
| Windows OEM and devices | 17,315 | 17,087 | Devices and Consumer |
| 合计 | 281,724 | 331,839 | |

公司FY24=245,122。FY25新两组218,783/62,941；FY26 268,127/63,712。PPT旧三组数与新两组均汇总至相同公司总额，移转并非新增收入。FY24新产品组历史没有伪造。

## 全路径独立复算（USD million）

| scenario | FY27 | FY28 | FY29 | 3年CAGR | terminal increment |
|---|---:|---:|---:|---:|---:|
| low | 367,291.970000 | 404,859.940000 | 439,422.284120 | 9.812442% | 107,583.284120 |
| base | 386,128.210000 | 450,353.070600 | 517,490.862762 | 15.964507% | 185,651.862762 |
| high | 403,614.120000 | 494,471.221000 | 593,733.118377 | 21.400726% | 261,894.118377 |

原基线终值517490.862762；增长分摊cloud_ai179713.612472、advertising5586.28556、enterprise_migration3447.72621、consumer_cycle-3095.76148，合计185651.862762。每流权重合计1；前三正向排序正确。此表验证分摊计算，未识别统计因果。

### 全8敏感性单位重算

| parameter FY27 | 原实际down/up terminal | 按名称±5pp应为down/up |
|---|---:|---:|
| azure_growth_base_2027 | 290,723.665482 / 1,339,111.142762 | 509,274.659962 / 525,707.065562 |
| microsoft_365_cloud_growth_base_2027 | 362,307.447570 / 1,180,667.850762 | 510,859.092882 / 524,122.632642 |
| productivity_and_server_licensing_growth_base_2027 | 483,819.897812 / 694,706.467762 | 515,718.706712 / 519,263.018812 |
| industry_solutions_growth_base_2027 | 491,385.216702 / 637,241.532762 | 516,293.356062 / 518,688.369462 |
| frontier_and_support_services_growth_base_2027 | 507,929.747562 / 562,590.462762 | 517,039.866762 / 517,941.858762 |
| search_and_advertising_growth_base_2027 | 487,069.577202 / 658,330.147762 | 516,082.469912 / 518,899.255612 |
| xbox_growth_base_2027 | 495,300.624042 / 633,065.022762 | 516,335.121162 / 518,646.604362 |
| windows_oem_and_devices_growth_base_2027 | 503,899.862962 / 600,362.812762 | 516,662.143262 / 518,319.582262 |

每条stored5.0加在ratio上，down全部clamp至-1；原score50.217211的sensitivity项3.108606及concentration0.379300受影响。verifiedclaim覆盖/质量分也需要对应真实证据质量；low评级和非概率解释本身正确。explicit模型与historical accuracy分0正确。

## 管理目标与沟通完整性

数值原文/范围通过：公司Q1 89.85–90.95B，Agents75.15–75.75B，Devices14.7–15.2B，Azure44–45%CC，M365commercial17%CC/18%CCadjusted；10条端点/KPI均保留为unmodeled_data_gap，无同口径季度到年度转换。年度double-digit仅解释为≥10%语言下限（365022.9），非官方10%点预测。3个FY27情景均高于该下限；benchmark支撑仍不足。

17项定性旁表每行与重新打开call/PPT检查；保留了年度gaming回增、products/server中single下滑、Windows high-teens、FX<1pp、bookings、M365商业/消费、LinkedIn/Dynamics、Azure供应约束、onprem、ex-TAC及Xbox季度guidance。仍需US06的逐目标映射与缺项说明。后续季度actual尚未公开，不能把指引当实际。

六类：results/call/presentation/strategy/material announcements已重新打开；latestannual无法在bounded mandatory chain取得，不能盖成checked。9维基础分部/行业AWS方向/能力客户/paidseat口径有实际来源；policy量化桥缺失明确。sourceid挂到增长参数不代替完整支持。

## 工作流与边界

| 步骤 | 独立状态 |
|---|---|
| 0 | FAIL |
| 1 | PASS |
| 1A | FAIL |
| 1B | FAIL |
| 2 | PASS |
| 3 | BLOCKED |
| 4 | PASS |
| 5 | BLOCKED |
| 6 | FAIL |
| 6A | FAIL |
| 7 | PASS |
| 8 | FAIL |
| 9 | FAIL |
| 10 | PASS |
| 11 | PASS |

- FY24/25 existing reuse真实运行；新FY26调用失败，MAIN directCWP ensure错误为`adapter dayu-sec-cli does not support bounded acquisition`。provider未启动，不能称Dayu成功，也无下载后reuse链证明。
- schema2.0 companion request已准备，但实际fetch命令用了去掉companion的1.2legacy。两个ET进程是独立discovery/fetch探测，分别unsupported与entitlementrequired；官方call网页是另一路，不是ET originalTXT/import证明。
- 临时BS4全文不等于CWP canonical worker。未跑正式解析selection/quality/LLM产物；原reuse receiptparser_calls/llm_calls为null，不应改称0。
- 无付费升级、额外history大批次或翻译/外部叙述LLM运行。providerHTTP次数未暴露，保持unknown；self-generatedcaptureunsigned证明hash完整性，不证明密码学host身份。
- 配置及明确原产物SHA核对通过；全局store/其他agentWIP基线由MAIN持有，本review没有独立全系统baseline，不能替MAIN认证。
- Future actual backtest不适用；已冻结v1，原重复snapshot写入被拒，不能覆盖以掩盖错单位。

## 修复交接与复查范围

执行者应创建v2并修正US01–06/08，对本次可修的模型证据闭包重新输出input/result/report/registry/snapshot/manifest及完整命令账。US07保留BLOCKED，除非后续有真正bounded下载、FFcompanion、CWP正式处理成功证据。独立review随后检查改动claims/parameters/targets/tree/sensitivity/confidence/report/strong/hash及snapshot绑定。原v1及此审查作为历史保留，不由reviewer修自己签收。

registry audit职责补充：MAIN确认该工具只审计chain/同代冲突/anchor是否登记。本次实际SHA为预期部署SHA；其局限不构成新增缺陷，也不代替strong验真。
