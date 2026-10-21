# 药明康德 initial — process 独立审查

结论：**FAIL**。执行包可复核但为 partial；manifest `ee08753799d7d2a849dd3fd9c811e7c0e83d20d7538f978218245fdf98dca458`。有效初轮CWP固定646b6937，RF 4.3.0/schema3.10；后续文档提交与R5不追溯冒充实际运行。未读取其他reviewer初稿。

639封存物hash全通过；48真实命令、50 frozen/consumed输入仍精确绑定。两版最终JSON/原生Markdown/快照一致。机器结构与算式通过不代表经济质量。

## 全量数字审查

97基线参数=6 reported+45 analyst assumption+46 derived；压力105参数新增6 exposure假设和2事件。85/85声明引文在原件声明页可找到，17独立摘录，395数字token（含重复引文/上下文坐标）全登记。10 extracted金额和2范围原文及变换核对。

两版输入/输出/快照六个JSON共3952 numeric leaves全分类：1276独立比较零算术差错；2676为复制绑定、声明和坐标等，不能算独立来源事实。90分部年度格、18公司年度格、CAGR、贡献及每版5项敏感性完整重算。未分类叶子0；经验幅度未验证的45未来条件率、6压力传导和2事件大小继续保留。

Typed ledger：242观察中238 PASS、4 INVALID；30关系全部PASS。4 INVALID为同一18–22%目标在两版的端点携带CNY，非4个独立经济错误。工具source_truth_verified=false。诊断：`C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\process\measure-diagnostics\20261021T215702Z-b285cb85\report.json`。

基期：45456.1657+0.00007418=45456.16577418 CNY million；差额74.18元。2028 Low/Base/High=49055.32540512/62006.81666051/74199.63473006399 CNY million；这是未经幅度校准的条件路径。

完整台账：`C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\process\independent-recalculation.json`；参数台账：`C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\process\parameter-numeric-ledger.json`；引用数字：`C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\process\quoted-numeric-token-ledger.json`。

## 检查点

| ID | 状态 | 结论 |
|---|---|---|
| P00 | PASS | live scope遵从；初轮真实执行，审查阶段无付费/采集，CWP公开SourceRef只读。配置不改写；使用冻结initial有效版本。 |
| P01 | PASS | manifest已实开，639个文件全hash一致；打开scope/step/document/source/事实参数计算索引、最终输入/结果/快照、真实命令与两份原件。 |
| P02 | PASS | 信息日2026-10-21；FY2025 Dec31基年、2026–2028三年，CNY million。唯一正式来源annual published2026-03-24；另Q1 published2026-04-28未进入正式模型；均未跨cutoff。actual capture/checked为当前日，没有将FY改写为不同calendar年。 |
| P03 | FAIL | 非抽样全量：基线97+压力105参数、85claims、395引文数字token、两版六个JSON3952数字叶子全部登记；1276独立比较零算术差错，2676复制/声明项明确分类，0遗漏叶子。typed242观察中4端点因同一比例目标带币种INVALID，238观察与30关系PASS。45未来条件率的经验幅度仍未验证，不把声明或机器PASS写成source truth。 |
| P04 | PASS | fact→parameter→derived growth→真实路径消费可追溯；六reported+rounding闭合，45率经x0别名被消费，压力两事件及六exposure经18个受影响growth传播。公开narrative span→chem_base_2026_conditional_rate→growth→化学Base路径真实存在；仅为rationale，不证明20%量级。 |
| P05 | FAIL | 85/85原件摘录连续匹配声明页；17unique excerpts，重复引用不等于独立来源。10 extracted数值及两范围均原文存在并有显式归一化；元/万/亿→million无10倍错误、无USD/HKD混加。单一同比目标raw_currency=CNY与percent矛盾。 |
| P06 | PASS | 2023/24/25历史均追到原件p7；FY2025五分部45456.1657+0.00007418=45456.16577418 CNY million，74.18元舍入差有效。未把处置价款混入收入。 |
| P07 | PASS | 两版全部46派生值、90分部年度路径、18公司年度路径、年度增长、6 CAGR、增量和解释性分配均独立Decimal复算。五敏感性每版完整DAG重算、请求/有效值/pp/range/clamping核对；共享压力完整路径亦复算。 |
| P08 | N/A | 未要求beat或市场共识，正式结果无共识/beat数字。dated管理展望独立比较已按其本来用途审查。 |
| P09 | PASS | 96个已安装RF闭包文件hash与冻结versions相符；真实48命令/50输入保持SHA。两版canonical input anchors、同JSON原生renderer文本、snapshot完整forecast/input相等；schema3.10 engine4.3.0 receipt是unattested，结构PASS未冒充经济通过。 |
| P10 | FAIL | 完整技能0–11/1A/1B/1C/6A逐子步审查见workflow_steps；实际有产物但1A当前沟通/重大目标、1B独立参考及1C已得Q1消费不完整，持续目标比较未完。初轮partial表述诚实，仍未满足研究目标。 |
| P11 | BLOCKED | captured文本命令字节/输入/时点有记录，native token预算有记录；全网络wire bytes、早期web准确UTC/body未留，无法完成全部运行量核对。1905400验证GET bytes为小计。 |
| P12 | PASS | DeepSeek已知6149in+706out=6855 tokens，2992 microUSD price proxy；MiMo401实际usage/cash未知，保留32171tokens/6728microUSD hold。公司39026tokens及9720microUSD为proxy/hold，不是实际发票；actual cost=null。 |
| P13 | PASS | 真实RF lint/validate/compute/render/snapshot和support诊断由命令封存证明；未将本审查本地脚本称为真实预测重跑。 |
| P14 | N/A | 未来2026–2028全年actual尚未实现，未运行evaluate，未制造回测/历史准确性；两版immutable snapshot留存。 |
| P15 | N/A | 请求为公司三年收入预测，无特定theme反事实增量；theme_analysis=null符合范围。共同压力按步骤8另行检查。 |
| P16 | PASS | 直接模型以已确认收入为基数，无订单/容量/项目数直接加到收入。RPO5800478.75万元是期末合同存量，4220706.46万元是预计2026确认子集，均未再乘进度或加到total；TIDES留在化学父分部。 |
| P17 | PASS | 正式模型年度增长没有Q1/H1直接×4/×2，三年FY窗口一致；季度原件明确2026-01-01..03-31。已合格Q1遗漏属PROCESS-001，不能以此证据作annualize修正。 |
| P18 | FAIL | 事实、机制方向与条件幅度标注清楚，无未来actual冒造；但独立参考未建立，45条件率及8新增压力假设未经验校准，不能签经济质量通过。 |
| P19 | PASS | 原件同版本85摘录逐条核，issuer年报/季度报告actor清楚。表头、期间、原币种及原文条件保留；authoring transformations明确万元/元归一化，不冒充原文数值。没有伪造电话会问答/发言人。 |

## RF 全部步骤与子步

| 步骤 | 状态 | 核对 |
|---|---|---|
| 0 | partial | 九维齐全：2 modeled/7 material gap；不是九维经济质量合格。 |
| 1 | executed | 主体、信息日、币种、年限和收入范围冻结。 |
| 1A | partial | 1/6官方类别checked；Q1 TIDES目标遗漏，持续同比目标native比较未完成。 |
| 1B | not_completed | 内部按已确认收入×条件率；outside comparable numerical operating case未完成。 |
| 1C | partial | 来源发现/合格/summary/read/use已分开；one span真实消费，但已合格Q1和更新来源未消费。 |
| 2 | executed | 至少3年公司收入；五分部基期+74.18元舍入调节正确。 |
| 3 | partial | 唯一正式来源、85claims均可读；45未来率只作假设，Q1目标未登记。 |
| 4 | partial | 五个经济曲线与direct_growth回退合理低自由度；TIDES不重复；经营生命周期/量价/订单转化缺独立证据。 |
| 5 | executed_with_limitations | modeled_as_recognized避免重复确认；化学/其他时点时段混合。测试/生物学原件为时段，模型统一mixed有明确annual aggregate限制，未虚构时点份额。 |
| 6 | partial | 三情景×三年完整、无路径交叉；区间/尾部无经验范围。 |
| 6A | executed_with_limitations | 2正向主驱动+1headwind；5分部各weight=1，mechanism/counterevidence/falsifier齐；单发行人17unique excerpts无独立triangulation。 |
| 7 | executed | 所有公司路径/增长/CAGR/贡献闭合；舍入差退出未重复消除。 |
| 8 | executed_with_limitations | 两版5 sensitivities、两年度共同事件和6 transmission coefficients完整DAG重算；未实测exposure、未概率校准、非Q4延迟追赶。 |
| 9 | executed_with_limitations | native confidence0按其direct-alias算法可复算，非实现概率；祖先证据/敏感性未计weighted coverage，报告保留限制。 |
| 10 | executed_structurally | 正式JSON由4.3.0计算+强校验，Markdown同renderer；trust声明unattested/partial。 |
| 11 | snapshot_executed_evaluation_NA | 两版快照与输入/forecast精确一致；actual未实现，evaluate N/A。 |

## 缺陷、影响与复测

### PROCESS-001 P1 已合格 Q1 原件未消费，遗漏全年 TIDES 约40%增长目标。

责任类别：operator_research_gap。

预期：RF 1A/1C/3：所有重大已读/可得收入目标须登记；先消化已合格原件，缺摘要不应阻止使用原文。

实际：Q1已通过native source preparation且可公开读，最终只用年报。Q1 p4明确预计全年TIDES收入约增长40%；最终3项目标均来自年报，无该目标。

影响：现有年度目标集不完整；Q1收入12435.77656829 CNY million及化学/测试/生物学最新路径未约束2026条件率。不能用Q1×4修正。公司净收入影响未能识别，不能把TIDES目标再加到化学。

根因推测：operator/research omission: qualification succeeded but facts/targets were not inventoried before authoring. Not explained by H1 provider failure.

建议：重新从合格Q1提取本期事实、年内/全年目标、业务边界及反证，保留Q1真实3个月窗口；TIDES置于化学父分部，单独登记或透明unmodeled，不重复加总。

复测：新attempt保留Q1原件/quote/target/parameter lineage；验证40%目标完整登记和TIDES父子包含关系；全三情景重算。

证据：
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\process\q1-source-pages.json` — `/pages/4`，SHA `45b518bae5e24eb66759aed0f9d8fce033808db43980b8c0cfca705549640983`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\source_ledger.json` — `/sources/1`，SHA `63d550f5d196ad2b37b79ddcda057455a53a4cfee8465950737a7c1e20a1c74e`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json` — `/management_targets`，SHA `dde8dce38b0c0b203eb4a0a9facaaa981debeea61559a9cab3e7be8285526150`。

### PROCESS-002 P1 截至as-of的最新半年业绩、演示、策略和融资材料未进入合格原文集。

责任类别：engineering_candidate_plus_research_gap。

预期：RF1A/1C按latest-filing到as-of完整读取六类沟通及重大公告；来源不能准备时保留具体阻塞，不可称研究完成。

实际：六类仅annual checked，其他5类not_available且coverage_complete=false。已有官方H1、Q1、JPM、融资线索；H1 native CWP blocked/local_metadata_gap/publication_date_unknown，FF invalid_producer_schema。最终以2026-03-24旧展望作dated benchmark。

影响：2026–2028预测未反映可能更新的guidance/产能/并表；方向和金额unknown。该问题不同于PROCESS-001的已合格Q1未消费。

根因推测：Candidate engineering/data seam: CWP source metadata qualification and FF failure envelope prevent current source acquisition; exact common root to be diagnosed by expert. Other IR/financing reads also remain research work, not proven external entitlement denial.

建议：由owner定位native失败及metadata资格处理/FF封装；用既有授权与预算补缺后新attempt采集/读取，不手造来源记录，也不把发现索引当已读原件。

复测：同公司最新H1真实source preparation及IR/融资原文读取；目标新旧版本并存、真实publish/as-of；四路复审。

证据：
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\document_matrix.json` — `/documents/1,/documents/3..10`，SHA `74a7bad4523d6a4e0bdf8da30c4682975218070631f343a385893cde8550ed72`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\discovery.json` — `/records`，SHA `9767a5aec5756a9d569acb6afb41fee6e9807abf9f2f2e42a5d598e9b3780663`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json` — `/management_communication_coverage/1..5`，SHA `dde8dce38b0c0b203eb4a0a9facaaa981debeea61559a9cab3e7be8285526150`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\remaining_items.json` — `/remaining/0..1`，SHA `f8b1fbf1d524c6dca59d0aabbcc26ca88077f5c7a2746bb53bd4ec0ea0a80fb3`。

### PROCESS-003 P1 45个未来条件增长率及共同压力传导均无独立量级基准；1B未完成。

责任类别：research_gap。

预期：RF0/1B/4/6/8：从观察到的范围和同口径历史/外部参考建立最小充分桥，保留替代解释和可检验失效条件；conditional fallback允许但不能等同经济质量通过。

实际：97参数中45 analyst_assumption增长率、45 x0 derived aliases、6reported和1rounding。全部future numeric ranges unknown。压力另有2个未校准年度冲击及6个未实测exposure。outside operating case、failed/delayed peers、客户预算/净价/利用率范围未完成。

影响：最终2028 Low/Base/High分别49055.32540512/62006.81666051/74199.63473006399 CNY million；未校准跨度25144.30932494399。Base相对Low高12951.49125539，不能解释为可信区间或实现概率。压力Base2028下降3429.631723805 CNY million亦只是选定条件。

根因推测：Research gap rather than a numeric hallucination: direction and magnitude are correctly disclosed separately, but narrative x0 aliases supply no independent calibration and 1B was not substantively completed.

建议：先消费已合格最新事实，建立可核查的最小经营/历史桥和独立参考；减少无法区分的自由参数，逐年说明尾部条件，保留范围未知，不以模板或正向发行人段落充当量级证据。

复测：新attempt证明每个material segment×year×scenario条件的观察/转换/反证；未验证剩余数继续明确；独立analyst审查，不以engine PASS替代。

证据：
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json` — `/parameters,/operating_research/calibrations`，SHA `dde8dce38b0c0b203eb4a0a9facaaa981debeea61559a9cab3e7be8285526150`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-shared-shock-final-input.json` — `/parameters/97..104`，SHA `e20109b1a1d9d1fc2b924cc0abb3854f8e3f847687256df23542130c2066b241`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-forecast.json` — `/confidence/research_adequacy/magnitude_adequacy`，SHA `21ac4e6c9a409b90a1b43fc03d13dd0b9341ba04e0bdedfd9486f72abcf31c96`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\step_ledger.json` — `/steps[step_id=1B,6,8]`，SHA `d283fba76f4de55f0a327d06e66d2031f0e78faaf6df7dfb7dee7e3fad22dd5e`。

### PROCESS-004 P2 早期web/原件验证未完整封装，网络wire bytes及部分准确时点不可验证。

责任类别：operator_observability_gap。

预期：P11及artifact contract：有界记录真实输入/输出/UTC/bytes，未知不得按0或小计冒充总量。

实际：48 captured commands和50 frozen/consumed inputs均保持exact binding；但初始preview/exact-SHA GET未outer capture，web早期UTC/body bytes、模型wire total未知。1905400 bytes仅验证GET小计。

影响：不能完成所有网络bytes/最早工具时点全量核对；未观察超预算，不据此断言发生费用为0。

根因推测：Observability gap in initial operator recording; later timed query and captured reads do not reconstruct earlier exact requests or all wire totals.

建议：保留旧缺口，后续对真实有界入口记录实际请求、输出与资源；使用既有预算producer数据，不补造历史日志，不无限重试。

复测：新attempt应有有界完整日志；现有unknown与hold继续保留，不能覆盖原initial。

证据：
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\remaining_items.json` — `/recording_limitations`，SHA `f8b1fbf1d524c6dca59d0aabbcc26ca88077f5c7a2746bb53bd4ec0ea0a80fb3`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\source_ledger.json` — `/network_observation`，SHA `63d550f5d196ad2b37b79ddcda057455a53a4cfee8465950737a7c1e20a1c74e`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\discovery.json` — `/query_time_precision`，SHA `9767a5aec5756a9d569acb6afb41fee6e9807abf9f2f2e42a5d598e9b3780663`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\process\execution-review.json` — `/calls`，SHA `05da0d3b2ba7a97d669f3de2020eb7f7b2c5cf02071f7b0f44dff89a6bb82382`。

### PROCESS-005 P2 无量纲18%–22%同比目标携带raw_currency=CNY，与typed金融口径冲突。

责任类别：engineering_candidate_or_authoring_contract_gap。

预期：比例/增长应currency=null；percent/decimal/percentage_points与货币金额分开。

实际：原生字段raw_unit=percent、raw_scale=unit、raw_currency=CNY；typed映射保留原始声明而不静默纠正，基线/压力共4端点均currency_on_dimensionless INVALID。30关系重算全部PASS。

影响：同一个逻辑目标在两版重复出现；rendered percent显示正确，目标当前unmodeled，未发现由此导致收入数值变化或FX混加。

根因推测：Native target schema or authoring template uses currency-bearing generic target metadata for ratio target; exact schema restriction versus operator choice requires owner confirmation.

建议：统一ratio target的原生口径与下游typed合同；保留18/22原值和percent，审查模板/validator是否迫使无量纲目标填币种，增加跨边界回归。

复测：包含ratio/CNY、percent/decimal/pp的portable测试；原件值、native schema、renderer与typed ledger应一致且不猜币种。

证据：
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json` — `/management_targets/1/raw_currency,raw_unit,raw_target_value_low,raw_target_value_high`，SHA `dde8dce38b0c0b203eb4a0a9facaaa981debeea61559a9cab3e7be8285526150`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-shared-shock-final-input.json` — `/management_targets/1`，SHA `e20109b1a1d9d1fc2b924cc0abb3854f8e3f847687256df23542130c2066b241`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\process\measure-diagnostics\20261021T215702Z-b285cb85\report.json` — `/observation_checks[check_id contains target:1]`，SHA `74f975046413c97fb6485ba6cbb1bbb87d95e04e39dcaf573ded373c08a30822`。

### PROCESS-006 P1 已识别且可比的持续经营18%–22%收入目标因custom聚合不支持而留unmodeled。

责任类别：engineering_capability_gap。

预期：RF1A：comparable in-horizon material target需有效scenario treatment或三个情景independent benchmark；不能仅以原生scope不支持结束可比目标处理。

实际：目标perimeter_status=matched、scope=custom四个持续业务，但treatment=unmodeled_data_gap，映射参数/情景为空。原件可用分母43420.8237 CNY million，reviewer独立求得2026持续YoY Low9.2915697682%、Base17.4843708458%、High25.1857687168%。

影响：Base持续经营17.48437%比18%下端低0.515629个百分点；原生合并同比12.223899%使用不同分母，不能替代。四持续业务2026较18%下端少223.890426 CNY million（边界四舍五入另见来源）。

根因推测：Engineering capability seam: target comparison supports company or one segment, not selected group of segments. Input correctly discloses mismatch in capability, but mandatory comparable target remains incomplete.

建议：通过已有DAG表达可审计的持续业务聚合/目标比较，保留终止业务在历史合并总额的桥；不改为含终止业务的公司同比，不强迫Base达到目标。

复测：用四段聚合目标、含退出分部的company YoY、三个情景差异和FX/范围不一致作通用回归；同公司新attempt输出native目标比较。

证据：
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json` — `/management_targets/1`，SHA `dde8dce38b0c0b203eb4a0a9facaaa981debeea61559a9cab3e7be8285526150`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\process\execution-review.json` — `/target_comparison_independent_only`，SHA `05da0d3b2ba7a97d669f3de2020eb7f7b2c5cf02071f7b0f44dff89a6bb82382`。
- `C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\process\source-pages.json` — `/pages/13,/pages/14`，SHA `c8d06dd2c38a93d362be3f88ba9ebd6f2ac55ec91f32a4f24096580615a2fcb1`。

## 原件、成本与限制

通过CWP SourceRef只读打开annual（1608226 bytes，SHA7f1431...）与Q1（297174 bytes，SHA379796...），原始PDF未另存；具体成功/初次unsupported_purpose探针均保留在roles/process。年度原件p7/11–16/26/31/119–120/184等逐条语义核对；Q1 p1–5亲读。无电话会转录伪装原文。

DeepSeek已知6149 input+706 output=6855 tokens，2992 microUSD仅价格代理。MiMo401保留32171tokens/6728microUSD未知hold，公司39026tokens/9720microUSD含hold；实际费用USD unknown，不记0。母级预算引用原native ledger，不重建权威费用库。

所有FAIL/BLOCKED均有finding；N/A均写明任务不适用或未来actual尚不存在。审查未修改执行包、产品、生产配置、其他角色报告。初轮不可用于宣称无主要问题。
