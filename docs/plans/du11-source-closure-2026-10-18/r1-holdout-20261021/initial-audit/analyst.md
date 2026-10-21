# 药明康德收入预测独立模型审查（initial）

结论：**FAIL**。透明条件模型与部分来源可复核；资深买方收入研究质量未通过。3个P1研究缺口及2个P2缺口。

信息日 2026-10-21；2025基期；2026–2028；CNY million（人民币百万元）。execution_outcome=partial，executor_completion=partial。

真实独立四号审查；初稿未读取其他reviewer报告；亲自通过SourceRef只读打开已有年报/Q1/历史H1，免费只读打开官方最新H1；未调用付费模型、未下载新原件、未修改封存执行或CWP。

封存 manifest SHA-256：`ee08753799d7d2a849dd3fd9c811e7c0e83d20d7538f978218245fdf98dca458`；639个产物。正式终版为timed-final-*；另审timed-shared-shock-final-*。8份关键原产物实读hash均与manifest一致。初始scope646b6937/产品76a9440b；后续R5 a5214bda不能替代本initial。

## 实际读过的材料

- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\scope.json — as_of, periods, profile, frozen scope
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\manifest.json — final* pointers and partial declaration
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json — /parameters; /segments; /operating_research
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-forecast.json — /consolidated_forecast; /growth_driver_analysis; /confidence
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-support-diagnostics.json — /segments: 45 cells; /economic_truth_inferred
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-forecast.md — entire rendered formal report reviewed by section/underlying JSON
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-snapshot.json — metadata and frozen input/result references
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-shared-shock-final-input.json — /parameters shared_customer_funding_shock_pp_2026/2027; *_conditional_common_event_exposure_*; *_growth formulas
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-shared-shock-final-forecast.json — native segment paths and consolidated paths
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-original-reads.json — [0].selected_pages printed p7/13/14/16/17/26/29-32/119-120/183-184
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-original-reads.json — [1].selected_pages printed p2/4/5; SHA 379796e63b15a126aecb33509824a76197114ca3a43e0db368dd27e3508560a6
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-original-reads.json — [2]: first six pages identify reused 71582e... as 2025H1, not 2026H1; not used as current-period actual
- https://static.cninfo.com.cn/finalpage/2026-08-04/1225455027.PDF — 2026-08-04 official original; printed p7/11-12; web turn434view0, turn436view0/1, screenshot turn437view0/1
- https://www.wuxiapptec.cn/news/wuxi-news/wuxi-apptec-crdmo-model-delivers-strong-results — 2026-08-03 official release; web turn432view0 L19/26/57/60/66-68/85-94
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\annual-page-183.png — visually inspected timing table
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\risk-audit\20261021T215643Z-c817e556\report.json — /checkpoints; /findings; /actual_input_refs
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-cross-check.json — /scenario_checks; /segment_h2_checks; /chemistry_two_bucket_check

SourceRef年报SHA `7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`；原始发布日期2026-03-24。独立打开Q1 SHA `379796e63b15a126aecb33509824a76197114ca3a43e0db368dd27e3508560a6`，发布日期2026-04-28。71582e...原件实为2025H1，未当作2026H1。最新H1为官方2026-08-04巨潮PDF只读web，官网发布2026-08-03；完整相邻前瞻性条件已读。

## A01–A18

| 检查 | 状态 | 独立判断 | Issue |
|---|---|---|---|
| A01 | FAIL | 三年合并历史及五分部基期核对闭合；业务是研发/开发生产服务，非一次性售股收入。原始p183揭示Testing/Biology确认时间已可量化，mixed时间元数据不准确；未来市场生命周期/趋势充分性另见A05/A09。 | ANALYST-005 |
| A02 | PASS | 原文项目推进、下游商业化、产能交付及履约到已确认收入的机制成立，三棵树均连接native Base收入参数；不是纯标签。PASS仅限机制与公式路径，数值幅度不因此通过。 | — |
| A03 | PASS | TIDES在Chemistry母分部内included，没有再次加成公司收入；Testing/Biology/Other/Discontinued互斥；2025已重述对照与处置对价未混入营业收入。2026全部退出是明确假设，Q1及H1已发生部分均为零，不冒称全年已证实。 | — |
| A04 | PASS | reported_fact、derived_fact、analyst_assumption区分明确；45个未来条件率非来源原值，观察范围null，falsifier与机制反证存在。正确标签仅证明诚实披露，不证明幅度合理。 | — |
| A05 | FAIL | 供给容量/员工/需求客户/价格/监管/FX没有互相约束；原文4,000kL、>100,000L和客户集中48.11%只支持风险与供给方向，不能约束三年收入。高收入幅度没有可用吞吐或客户预算桥。 | ANALYST-002 |
| A06 | FAIL | 没有把backlog总额错误直接加成收入，但42207.0646百万元2026预期确认子集、新签/取消与年内时序未建桥；保持gap不能完成该项。 | ANALYST-003 |
| A07 | FAIL | 三年三情景同一direct_growth公式、不交叉，算术成立；每个分部每年各给条件率，缺共同需求/价格/容量的校准与相关性机制，不能把合法conditional路径等同研究情景已通过。 | ANALYST-002 |
| A08 | FAIL | 已区分管理目标与独立预测、正证与价格/预算反证；但只有发行人年报，所谓independent_benchmark的判断依据仍是同一报告风险泛述，无独立经营范围。最新经营/目标未消费，所选反证无法解释量级。 | ANALYST-001, ANALYST-002 |
| A09 | FAIL | 独立复算段合计/CAGR/年度增量无实质算术差。经济检验失败：Chemistry贡献17445.26百万元、占净增量105.4%；Base隐含2026H2公司-10.3%、Testing-20.1%，转折未解释。无冻结历史回测，不能证明持续性或准确度。 | ANALYST-001, ANALYST-002 |
| A10 | N/A | 正式forecast没有市场共识beat/超预期主张，无需捏共识基准；管理目标比较不是beat。官网标题中的他人超预期措辞不纳入本报告结论。诊断NOT_CHECKED与本项N/A并不冲突。 | — |
| A11 | FAIL | TIDES确有业务、收入、订单及容量事实，并已放在母分部防重算；但2026最新TIDES约45%目标和半年真实交付遗漏，后两年无客户/订单/爬坡收入节奏。大故事与小事实在文字分开但主要未来幅度仍未落地。 | ANALYST-001, ANALYST-003 |
| A12 | FAIL | 单变量敏感性和低置信度披露诚实：化学2026/2028±5pp终值影响2246.30/2450.50百万元；score=0低且不等于概率。但2027化学、汇率、客户集中/订单取消及联合交付尾部没有经济范围，现有Low不足以证明风险覆盖。 | ANALYST-002, ANALYST-004 |
| A13 | FAIL | 15条calibration无观测区间、观察为空、45个cell均unsupported；独立cross-check揭示所需H2与TIDES/non-TIDES条件，未找到足以支持未来三年范围的独立量价/产能区间。未知保持null，不把当期历史或管理目标反推成范围。 | ANALYST-002 |
| A14 | PASS | 本input没有以季节性/delta/flat冒称未来数值校准；直接增长明确为未校准假设。我用H1/H2减法仅检验隐含条件，没有按过去季节性生成未来收入。 | — |
| A15 | FAIL | 旧指引的原币、亿元→百万元、总额/持续业务及日期区分正确；持续经营custom不强装含终止分母。但最新总额/持续/TIDES目标漏记，reported CNY/美元敞口与处置变化未形成独立桥。不能据旧指引判断as-of路径。 | ANALYST-001, ANALYST-002 |
| A16 | FAIL | 三年2026–2028条件数值均给出，未伪造未来actual或季度；但已可用Q1/H1没有进入正式时期桥，2025重述分部历史仅两年不能证明完整周期。缺期已披露为gap仍是本次最新公司预测的实质缺口。 | ANALYST-001 |
| A17 | FAIL | 已独立核另版shared shock，原生公式x0+x1*x2一次消费共同事件且全情景复算，不错误地称完全没做联合冲击；缺物理量、时间敞口、延期catch-up/取消及供需cap，A17尚不充分。 | ANALYST-004 |
| A18 | PASS | FY2026–2028完整未来actual不存在：historical_accuracy_records空，observations=0且WAPE=null；快照为当前封存，不是历史精度证明。已发生H1不是全年actual，不当作0误差。 | — |

## 机制与幅度分列的关键假设

| 分部/条件 | 2025基数 | Low / Base / High的2026,2027,2028率 | 机制 | 数值范围与限制 |
|---|---:|---|---|---|
| 化学业务 | 36465.8469 | low: 12%,4%,0% / base: 20%,12%,10% / high: 28%,20%,16% | 项目/交付及TIDES供给 | unverified / 独立观测范围未知；不是事实或管理指引数值；合理经营范围=null |
| 测试业务 | 4041.7010 | low: -5%,0%,0% / base: 4%,5%,5% / high: 10%,10%,8% | 新分子服务/客户导流；竞争价格反证 | unverified / 独立观测范围未知；不是事实或管理指引数值；合理经营范围=null |
| 生物学业务 | 2677.1750 | low: -3%,0%,0% / base: 6%,7%,7% / high: 12%,12%,10% | 新分子服务/客户导流；竞争价格反证 | unverified / 独立观测范围未知；不是事实或管理指引数值；合理经营范围=null |
| 其他业务 | 236.1008 | low: -25%,-10%,-10% / base: -10%,0%,0% / high: 0%,3%,3% | 非核心业务范围 | unverified / 独立观测范围未知；不是事实或管理指引数值；合理经营范围=null |
| 终止经营业务 | 2035.3420 | low: -100%,0%,0% / base: -100%,0%,0% / high: -100%,0%,0% | 2025部分处置完成；2026Q1/H1已发生为零；全年仍须边界核对 | unverified / 独立观测范围未知；不是事实或管理指引数值；合理经营范围=null |
| Chemistry内TIDES：tides_subscope | — | — | 2025收入11370百万元；新增产能爬坡，订单及服务分子增长；2026H1已交付收入可观察 | 45%FY2026为最新管理目标，不能当独立范围；2027/28无范围；45%管理比较对应FY2026收入16486.5、增量5116.5百万元；非TIDES须另解释。 |
| 持续经营：rpo_conversion | — | — | 年末58004.7875百万元合同存量，披露42207.0646百万元预计2026确认子集 | 有来源的预期时点，不是无取消硬下限；新增订单及净变化未知；Base总收入扣该子集尚需8805.61694百万元；取消/延迟对收入方向为负，实际金额未知。 |
| Chemistry/Testing/Biology：shared_event | — | {'shock_2026_pp': -5, 'shock_2027_pp': -2, 'exposures': [1, 0.5, 0.5]} | 客户研发融资/预算风险原文可读；跨段共用事件只记一次 | 幅度/系数未实测，时间与取消未知；Base2028减少3429.6317百万元，只是条件压力。 |
| 持续经营/处置：currency_and_perimeter | — | — | p32主要美元结算；p16境外客户地域收入较大；p26处置交割 | 无精确美元净暴露或as-of FX假设；地域不是币种；完整处置实体桥未做；金额未知；禁止以境外收入占比直接冒充USD敞口。 |

全部45个条件率和15条calibration已核；observed_range全null、source_claim_ids全空、observations空。历史/机制能支持方向，不能支持未来数值。原年报反证包括测试/生物学价格压力、研发预算与并购整合、竞争和监管/扩产延误、美元结算风险。没有将反证转成正增长支持。

## 独立cross-check

所有复算保存在 C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-cross-check.json；不是新formal forecast。

1. 基期：五分部合计45,456.1657，加舍入0.00007418=45,456.16577418。2023/2024/2025为40,340.80687704 / 39,241.43135988 / 45,456.16577418。原始2024分部已按处置重述；不将收入出售对价纳入。
2. 全年收入=已发生H1流量+待确认H2流量。2025H2=45,456.16577418−20,799.28188246=24,656.88389172；2026H1=28,897.47871836。下表只揭示各情景需要的H2，不将过去季节性用于未来校准。

| 情景 | 2026全年 | 隐含H2 | H2同比 | 对最新指引下限58,500的差 | 2028全年 / CAGR |
|---|---:|---:|---:|---:|---:|
| low | 47455.2998 | 18557.8211 | -24.74% | -11044.7002 | 49055.3254 / 2.57% |
| base | 51012.6815 | 22115.2028 | -10.31% | -7487.3185 | 62006.8167 / 10.90% |
| high | 54356.6919 | 25459.2132 | 3.25% | -4143.3081 | 74199.6347 / 17.74% |

最新指引是条件管理比较。偏离它可以合理；本包没有解释Base公司H2−10.31%、化学−6.90%、测试−20.09%、生物学+1.43%、其他+16.04%的相互机制。不能直接把所有情景抬到指引。

3. 存量→确认：2025年末RPO58,004.7875中42,207.0646预计2026确认，不含2026新增单。Low/Base/High高于该子集的差分别5,248.2352 / 8,805.6169 / 12,149.6273。缺取消、延期、FX/范围变化与新单桥；该子集不是硬下限，且不能再加到已确认收入。
4. 互斥经营桥：Chemistry2025= TIDES11,370 + non-TIDES25,095.8469。最新TIDES约45%管理比较意味着2026 TIDES16,486.5、H2 9,226.5（H1 7,260，约+27.09%顺序差）；Base Chemistry43,759.01628则要求non-TIDES27,272.51628、同比+8.67%。这是待解释的条件组合，未把管理目标充作独立需求预测；2027/28仍无范围。
5. 供给量纲：100,000L固相釜或4,000kL小分子釜是期末体积存量，需批次/年×利用率×收率×净单价才成年度收入；没有这些数据，不能给物理收入上限。客户母公司地域收入不等于USD结算净敞口。
6. 共享压力：另版各情景/分部按原生增长率独立连乘，最大算术差0；Base2028为58,577.18494，比未冲击少3,429.63172。2026/27共同-5/-2pp×[1,0.5,0.5]只记一次，未包含交付延迟、取消与追赶，属于未校准条件演示。
7. 加总/CAGR：段合计与公司年度值最大浮点差7.28e-12；CAGR按(2028/2025)^(1/3)−1重算。算术成立不能证明情景合理。

## 缺陷与复测

### ANALYST-001 · P1 · 截至as-of已公开的2026Q1/H1经营资料和上调指引未进入正式信息集；全年路径没有解释隐含H2拐点

**预期**：按RF最新沟通与目标覆盖要求，消费截至2026-10-21的可用原文、登记全部重大收入目标并用同口径H1+H2桥形成独立经营预测；偏离指引可接受，但须有独立反证、金额和时间桥。

**实际**：正式input只有2025年报一个source；latest_results_release等5类not_available且coverage_complete=false。已合格2026Q1原件未入模；官方8月3日发布/H1报告已将全年收入从513–530亿元提高至585–605亿元、持续经营增速35–39%，并披露TIDES约45%全年增长。正式目标账仍只列旧年度总额/旧持续增速/RPO子集。

**影响**：{"unit": "CNY million", "base_2026_minus_new_guidance_lower": -7487.31846, "high_2026_minus_new_guidance_lower": -4143.308068, "base_implied_h22026_yoy": -0.1030820067, "chemistry_base_implied_h22026_yoy": -0.0690032008, "testing_base_implied_h22026_yoy": -0.2008668895, "direction": "新信息指向更高当期交付；现有低路径可由独立下行机制支持，但本包没有该机制的量级桥。2027/2028也承接遗漏的2026起点。", "not_a_target_fill": "上述差额是与管理层条件指引的比较，不是已证明的预测误差或应机械补足的收入。"}

**证据**：
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json — /parameters; /segments; /operating_research
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-original-reads.json — [1].selected_pages printed p2/4/5; SHA 379796e63b15a126aecb33509824a76197114ca3a43e0db368dd27e3508560a6
- https://static.cninfo.com.cn/finalpage/2026-08-04/1225455027.PDF — 2026-08-04 official original; printed p7/11-12; web turn434view0, turn436view0/1, screenshot turn437view0/1
- https://www.wuxiapptec.cn/news/wuxi-news/wuxi-apptec-crdmo-model-delivers-strong-results — 2026-08-03 official release; web turn432view0 L19/26/57/60/66-68/85-94
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-cross-check.json — /scenario_checks; /segment_h2_checks; /chemistry_two_bucket_check
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\web-read-observations.json — /sources; original official dates and native web refs

**根因推测**：来源资格处理/消费在年报回退后停止，研究作者在可运行条件模型上完成发布；根因需专家追溯，不能仅解释为不可得未来actual。

**建议**：在新版本中合格读取2026H1、最新演示/电话会及重大公告；登记新目标和完整限定；锁定已发生H1，解释各分部H2量价/项目/确认桥，再独立比较最新指引，不按目标倒推Base。

**复测**：新input应含真实最新原文及日期/期间、Q1/H1 period_flow；新目标账含总额/持续经营/TIDES；三情景H1+H2可重算且每个偏离均有独立机制，保留本initial。

### ANALYST-002 · P1 · 45个增长率虽透明但无独立经营范围校准；最大增量驱动缺需求、供给、净价与FX相互约束

**预期**：以最小充分经营桥建立独立参考，支持需求/供应/价格/期间的范围；三情景幅度应由同一机制和相关约束产生，未知区间可保持null但不能当经济质量PASS。

**实际**：15条calibration全部observed_range=null、source_claim_ids=[]、status=unverified，operating observations为空；5分部×3年×3情景均为直接增长，未来45个条件率的native公式仅x0。Chemistry 2026/27/28 Low为12/4/0%，Base20/12/10%，High28/20/16%；同源2025项目/收入事实提供机制，不能决定这些幅度。无客户预算/取消、新单、可计费吞吐/利用率/周期、净价格、美元结算/FX独立桥或约束。

**影响**：{"unit": "CNY million", "chemistry_base_terminal_increment": 17445.26115696, "company_base_terminal_net_increment": 16550.65088633, "chemistry_share_of_company_net_increment": 1.0540528754, "chemistry_share_of_positive_driver_increment": 0.9374, "terminal_high_low_spread": 25144.309324944, "chemistry_2027_plusminus_5pp_terminal_effect": 2406.7458954, "direction": "主要幅度未知且双向；Base化学增量大于公司净增量，无法以小分部免责声明降低主要风险。海外客户收入≠美元货币敞口，不能据地域表杜撰FX金额。"}

**证据**：
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json — /parameters; /segments; /operating_research
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-forecast.json — /consolidated_forecast; /growth_driver_analysis; /confidence
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-original-reads.json — [0].selected_pages printed p7/13/14/16/17/26/29-32/119-120/183-184
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-support-diagnostics.json — /segments: 45 cells; /economic_truth_inferred
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\risk-audit\20261021T215643Z-c817e556\report.json — /checkpoints; /findings; /actual_input_refs
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-cross-check.json — /scenario_checks; /segment_h2_checks; /chemistry_two_bucket_check

**根因推测**：研究侧把聚合conditional fallback当最终数值尾部，尚未完成独立基准与范围；诊断已正确保持unverified，不能据此要求代码强拒合法假设。

**建议**：优先拆Chemistry内小分子D&M/TIDES/余项互斥桥，用客户商业化、订单转换、产能节奏及净价约束；补可比外部/客户原文作为支持或反证。减少可调自由参数，将无法校准的尾部明确保留为条件暴露；不制造行业通用CAGR阈值。FX与范围变动单列。

**复测**：新版本逐个重要segment/year/scenario给可复查参考与转化，独立范围不得由管理目标反推；复核支持与反证的方向及参数绑定；三年三情景仍同模型且不交叉。

### ANALYST-003 · P1 · RPO与TIDES收入确认时序缺少存量、新单、交付和取消桥，最大驱动只分配了母分部净增量

**预期**：backlog/TIDES产能/项目数必须通过转换率、交付/履约时间与会计确认进入收入；至少用公开RPO预期确认和业务子项作独立金额核对，不把订单或容量直接当收入。

**实际**：年报p184披露58004.7875百万元剩余履约义务，其中42207.0646百万元预计2026确认；模型保留gap但没有open+new–recognized–cancellation+FX=close桥。TIDES年报11370百万元已包含Chemistry，2024新增产能爬坡、2025-09固相釜>100000L支持供给机制；项目阶段和体积不能解释每年可计费产出。正式driver按Chemistry全额增量分配，未拆TIDES与小分子/余项确认。

**影响**：{"unit": "CNY million", "rpo_expected_2026_recognition": 42207.0646, "base_2026_residual_above_rpo_expected_recognition": 8805.61694, "base_rpo_cover_fraction": 0.8273837666601519, "latest_tides_guidance_comparator_fy2026": 16486.5, "latest_tides_guidance_comparator_increment_vs2025": 5116.5, "base_non_tides_yoy_required_if_tides_comparator_holds": 0.08673424685, "direction": "取消、延期、新签确认和产品mix均未知；RPO不是硬收入下限，45%TIDES管理目标也不是独立预测。上述桥揭示需解释的金额，未补写执行成功。"}

**证据**：
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-original-reads.json — [0].selected_pages printed p7/13/14/16/17/26/29-32/119-120/183-184
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json — /parameters; /segments; /operating_research
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-forecast.json — /consolidated_forecast; /growth_driver_analysis; /confidence
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-cross-check.json — /scenario_checks; /segment_h2_checks; /chemistry_two_bucket_check
- https://static.cninfo.com.cn/finalpage/2026-08-04/1225455027.PDF — 2026-08-04 official original; printed p7/11-12; web turn434view0, turn436view0/1, screenshot turn437view0/1

**根因推测**：aggregate recognized-revenue fallback没有把可用公开stock/flow与母分部经营子项接入研究桥；不是要求复杂模型本身。

**建议**：先做年度订单/履约义务及TIDES最小桥：已签2026交付子集、当年新单可确认部分、取消/范围/FX变化，TIDES和非TIDES互斥；无法观测转化率保持未知，并用多期实际交付检查。

**复测**：新版本对stock与flow、年度与期末容量、外部与内部收入逐项对齐；核对交付时点/履约进度不重复乘；按公开子项重算Chemistry增量并核完整限定。

### ANALYST-004 · P2 · 共享资金需求冲击已在同一DAG去重，但缺物理量×时间×敞口的联合交付/取消压力

**预期**：A17要求关键经营量、冲击发生/延迟时间和实际敞口联合压力，含交叉弹性、恢复/取消及供应约束；不能仅把一个共同百分比映射各增长率后称已完成。

**实际**：独立复算确认2026共用-5pp、2027-2pp冲击，化学系数1、测试/生物学0.5各只消费一次，2028保留原增长率；并非单纯遗漏联合冲击。但系数明确未实测，无受影响客户/订单/季度金额、延迟到下一期的catch-up与取消，亦无capacity/demand瓶颈。

**影响**：{"unit": "CNY million", "published_shared_shock_base_terminal": 58577.18493670501, "difference_to_unstressed_base_terminal": -3429.631723805, "stress_recompute_max_absolute_difference": 0.0, "direction": "数字是条件演示；实际风险尾部可能大于或小于此值，不能解释为校准的下限/概率。"}

**证据**：
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-shared-shock-final-input.json — /parameters shared_customer_funding_shock_pp_2026/2027; *_conditional_common_event_exposure_*; *_growth formulas
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-shared-shock-final-forecast.json — /consolidated_forecast; /segments
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-cross-check.json — /scenario_checks; /segment_h2_checks; /chemistry_two_bucket_check
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\risk-audit\20261021T215643Z-c817e556\report.json — /checkpoints; /findings; /actual_input_refs

**根因推测**：共享shock实现可复核，经营校准与时间暴露尚未完成，属于研究边界缺口。

**建议**：以可证据化客户/项目的受影响收入、季度交付、监管/融资时间和恢复/取消假设建独立stress版本；共享瓶颈只计一次。保留原情景与本演示，不把不存在的Q4金额设为全年/4。

**复测**：完整重算联合stress，复核跨年存量流量、一次敞口计量、取消与catch-up、供给cap及情景交叉；报告条件与未知，不仅核OBSERVED。

### ANALYST-005 · P2 · 已存年报p183有确认时点/时段金额，模型将测试与生物学timing笼统标mixed且称比例未分拆

**预期**：利用完整相邻注释表区分年度已确认收入及确认时间，未知只保留真正未知项；不得将抽取窗口缺失称披露缺失。

**实际**：p183清楚列Chemistry时段5181.01495430/时点31284.83192867百万元；Testing时段4041.70103067、时点0；Biology时段2677.17503051、时点0；Others时段225.62782287/时点10.47297181。正式段识别使用p119/120/184并给Testing/Biology timing=mixed；终止经营列是跨行合并，未推断其分拆。

**影响**：{"unit": "CNY million", "testing_biology_base_exposure": 6718.87606118, "current_direct_growth_revenue_arithmetic_change": 0, "direction": "当前年度聚合direct_growth数值不直接改变；确认元数据/未来时序压力的依据错误且漏用了可用证据。presentation为gross/net的mixed不由该时间表推翻。"}

**证据**：
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\independent-original-reads.json — [0].selected_pages[pdf_page_1based=183]
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\annual-page-183.png — visual check: revenue table, CNY yuan, timing rows and segment columns
- C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution\forecast\timed-final-input.json — /parameters; /segments; /operating_research

**根因推测**：选择p184政策而漏读相邻p183数值表，属于研究读取范围；尚未证明parser错误。

**建议**：在新版本中补p183表及准确时间口径；保留年度聚合fallback边界，勿对已确认收入再乘progress；gross/net与时点/时段分别说明。

**复测**：原件视觉表和字段一致；Testing/Biology timing反映全时段已披露事实，保留其他真实混合与终止业务未知，不要求重写封存产物。

## 诊断、置信度与未知

C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\roles\analyst\risk-audit\20261021T215643Z-c817e556\report.json

| 诊断检查点 | 状态 | Reason |
|---|---|---|
| A02 | OBSERVED | driver_linked_to_revenue_path |
| A05 | NOT_CHECKED | no_checkable_constraint_recorded |
| A06 | UNRESOLVED | conversion_relationship_missing |
| A08 | UNRESOLVED | independence_unknown_not_assumed, management_target_separated |
| A10 | NOT_CHECKED | no_beat_claim_declared |
| A13 | UNRESOLVED | operating_range_unknown, support_period_gap |
| A17 | UNRESOLVED | single_parameter_shock_not_joint |
| A18 | NOT_CHECKED | future_actual_absent_not_zero_error |

工具只索引声明。A02 OBSERVED不接受幅度，A18 NOT_CHECKED符合不存在未来actual；A10无beat可N/A。工具初始A17只读主forecast单敏感性，不包含另版shared shock；审查已独立读取并复算另版，最终A17失败因经营时间敞口不足。A06/RPO与direct_growth均未把stock直接当收入，UNRESOLVED是范围缺口而非已证明造数。

native confidence=0 / low，observations=0，WAPE=null；这是真实证据局限，既不是达成概率，也不免除经济审查。没有正式beat主张，A10 N/A。完整年度未来actual不存在，A18通过；本次快照不是历史回测。

- 新指引可偏乐观；与其偏离本身不是错误，须独立机制解释。
- 当前新信息缺失使2026及其后年度起点方向可能偏低；不存在已知未来全年actual，不能把guidance差额说成实际误差。
- 没有独立客户预算/同行失败样本/净价与可计费产能范围，未来收入幅度和联合尾部保持未知。
- 最新电话会完整Q&A、策略及重大公告窗口未穷尽；不把本审查的免费原文阅读算作executor合格消费。
- 年报p183可确认Testing/Biology已披露历史时段金额；gross/net比例和Discontinued时点分拆仍未知。

审查没有调用付费LLM、没有保存新公司原件；web transport bytes及平台工具费用未提供，保持unknown。原件/生产配置/封存执行与其他reviewer初稿未改。报告只有收入研究，不含评级、目标价、估值或仓位建议。
