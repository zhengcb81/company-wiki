# W09 经济研究重跑准备与验收检查表（2026-10-11）

**状态：readiness-only，不是三家公司研究通过。** 固定原公司：中微 CN688012、腾讯 HK00700、微软 USMSFT；as-of=2026-10-08；CN/HK请求2026–2028，US请求FY2027–FY2029。R16/R17/R18/W09仍open。RF主线47f497ad/4.2.1已正式接受，本文不再跑工程测试、下载或模型，也不修改旧sealed记录。

**给执行agent的范围：§1–7及§8的通用交付要求。§9只给MAIN/独立审查。** 独立executor只从最新eligible原件、真实summary/group和source-only方法形成新模型，不能读取旧forecast或审查答案来抄预测。§9旧反例及问题索引用于新attempt封存后的复验，不能变成新的参数事实来源。本表中的待核经营题目是阅读任务，历史报告里出现的数量也要由新run实际打开原件重新核，不把诊断报告代替公司披露。

## 1. 三家公司共同输入边界

| 项 | 执行动作及验收点 |
|---|---|
| 范围和期间 | 同as-of，记录实际财政年度及起止日；请求三年逐年显示支持期。H1/Q金额按新native period-flow口径，不给半年金额贴annual标签；原12月年度不能因季度增长年化。 |
| 当前工程版本 | 从实际installed入口记录源码/版本SHA、schema/emitter、source selector/parser及model generationpolicy；本轮RF 4.2.1支持旧4.2.0只读，不重签旧产物。CWP新运行用实际0.7，旧0.6保留真实历史语义。发布/安装依据MAIN接受回执，不重开完整工程套件。 |
| 原件复用 | 先用 [W08输入盘点](w08-readiness-20261011.md) 的actual SourceRef/ledger。32 refs已存在于原M3隔离scope；production未indexed或retired不等于没有原件。通过所属source层打开/登记实际bytes，不能SQL复活、重复GET或用文件名证明公开日期。 |
| 新执行隔离 | 独立company/attempt/run/catalog/AUTO/work/registry，旧sealed M3保持；共享资料以真实ref读取，不整湖复制。原件直到四审完成可打开。source/raw不翻译。 |
| 资料缺口 | SSE86小页已保存但尚待公开import成Ref，三流与issuer/parent/pointer/as-of分别保留；17目标命中页只是partial parent集，不能叫86页完整覆盖。403/204/entitlement/encoding取得失败必须区分。 |
| 资源 | 使用当前配置provider/purpose和profile/caps，不临时猜模型、不逐材料许可。累计USD20/2M承接旧unknown，付费前查当前原生母账；旧已知下界不是当前最终可用余额。公司单轮≤原120k/USD2及当前更小界，加总≤实余量。 |
| 未知 | 无原正文/无测量范围/交易控制日或认收关系未知，留具体unknown、影响年份和缺口，不能填0、拿summary补新事实或靠conditional标签称三年完成。 |

未知资料的具体来源处置沿W08；MSFT66,324B TXT工程fixture的provenance不能借另一个HTML补齐，正式研究优先已有合格官方call HTML。HK不具备ET call或US FMP entitlement未获正文，并不影响读取已经取得的独立官方原件；也不能据此声称ET抓取成功。

## 2. 最小经营事实库存：先读原文，后选参数

对每个重要经营项记录 `source/locator → 发布/观测期间 → 公司或业务scope → currency/unit → observation role → recognition trigger → 被哪个native parameter/driver消费`。需要明确区分：历史收入基线、机制方向、幅度范围、转换假设、反证、管理目标、认收政策、同业类比。无需每公司硬凑所有模型类型，也无需为每个helper建新JSON合同。

| 公司 | 必须由新run原件回答的问题 | 未知时的处理 |
|---|---|---|
| CN688012 | 刻蚀/LPCVD/设备及其它业务的历史口径能否对账？销售、生产、库存chambers与收入是否同产品/同时间/同认收范围？订单→验收→收入跨期和关键客户/新品进展是否可观测？并购标的何时控制、历史基线是否已包含？ | 混合实现收入/腔只可交叉检查，不标ASP；历史产量不当未来capacity cap。分部mix、订单时点或cap缺证不造细分和年度转化。 |
| HK00700 | 国内/国际Games的活动、产品周期和FX如何影响收入？Social的app道具/音视频会员口径、FTB支付/云如何区分？Ximalaya交易是否真正交割/控制、何时计入、哪些收入已在baseline？Others定义与认收范围是什么？ | 未披露份额不造支付/云或Social拆分；整体因子需要明确未解释残差。收购措辞不是已控制证据，毛亏不是未来收入方向证据。 |
| USMSFT | Azure使用量/价格/mix和供给边界，M365 commercial/consumer与席位/ARPU的认收期间如何衔接？付费、注册、preview、消费计费、订单库存如何各自转收入？业务重分类与旧比较基线如何调整？ | 注册不能乘ASP当付费收入；机会/financing/purchase commitment/RPO不是新销售。不得用美元收入pool代替GPU/CPU物理算力，缺资源与分配信息留unknown。 |

库存沿 `operating-research/1.inventory` 既有 dispositions（modeled/included/subscope/unmodeled/materiality_skip/unknown）；included/subscope写真实parent，防循环和重复增收。重要IPO、融资/M&A审计和备考文件按业务内容价值处理，不能标题“审计/公告”就行政跳过；缺原文保留缺口。

## 3. 三年模型、独立幅度与经营校准

1. 以正式历史年基线和实际期间flow对账，独立经营机制/可比范围先于Low/Base/High。选择足够小的可证模型：量×净价×认收、席位×ARPU、用量×单价、订单/交付转化、同口径aggregate fallback均可；不强制所有公司units×ASP，不凭行业标签选默认增长率。
2. 每个重大未来幅度填写同口径观测范围、来源期间/scope/单位、转换公式、实际输入ID、适用FY与业务、反证和falsifier。方向证据不能替代未来区间；历史同比/季节比/历史delta只能作参考，其未来延续需独立解释。
3. 对每业务×年×scenario检查actual native revenue/recognition roots。一个driver支持不覆盖其它业务或后两年；公司级校准只有实际company scope关系才可共享。合法历史measurement/disclosure期、未入收入DAG的独立上端点仍允许；历史基准经真实跨期derived bridge转换到目标年，不伪改原始期间。
4. 后两年以需求/客户/产品生命周期、供给、价/mix和认收前提分别建立路径；与管理目标独立比较。Flat、历史系数或示意宽范围可另做benchmark/stress，不代替有证核心forecast。仅支持一年时主表明确partial和未完成年份，保持原请求三年而不改horizon=1冒称完成。
5. 现有 `economic-support-diagnostics/1` 输出逐segment×scenario×year支持/原因和calibration/parameter/claim ID，`economic_truth_inferred=false`。supported只表示范围/转换/DAG关系一致；unverified/conditional不新增许可或阻断旧无optional research。研究者仍要证明经济幅度合理。
6. 引用范围跨公司/全球市场须有显式可核转换，同行增速和globalSEMI等不自动成为本公司收入预算。缺范围减少自由参数、保留未解释项，不编synthetic分布或伪backtest。

## 4. Management target、控制/口径/认收桥

沿既有管理沟通六category记录 checked/not_available/not_applicable；checked需要真实opened source，index/notice/loading不是business_original全文。每个找到的相关目标在既有target ledger保原文、claim、source date、目标期间、guidance/goal/aspiration/capacity_plan、raw value/currency/scale/unit、measurement basis、主体scope、perimeter和具体treatment。

| 检查 | 经济验收点 |
|---|---|
| 独立判断 | 先形成独立经营路径，再与目标比较。可用有证independent_benchmark逐low/base/high显示偏离及原因；不强迫三情景达标，也不能把不利目标删掉。 |
| 期间 | annual、Q/H、TTM、period-end run-rate、cumulative不互换；quarter不乘四。比较引用实际该segment/scenario/FY的native桥，不能全局used参数借其它业务。 |
| 同口径转换 | 原值保留，FX/scale/认收暴露由有证参数与restricted native formula重算。表达式含x0并不证明经济依赖；x0-x0+x1等取消原目标的伪桥须审掉。 |
| 并购 | 控制时点、股权、购买前后、标的全年收入、集团购后并表、内部抵销分别列。营业收入不按持股比例缩；收购条款与全年业绩承诺不能直接加集团营收；2027/28按各年控制状态重判。 |
| Guidance口径 | CC/reported、prior-year recognition adjustment、commercial/consumer、季度/全年分别保留；FX指引只用于原适用期间，需有证剩余季度residual。 |
| 资源与库存 | RPO/订单库存的确认窗口和cancel/续约条件单列，不与已确认收入相加、不变保证floor；交易流量/GMV不直接是净佣金收入。 |
| 原文与推导 | exact quote、transcription、analyst_derived benchmark和conditional包络明确区分，原图/原段locator可打开。无一致期market consensus，不能把高于management目标叫市场超预期。 |

公司特定阅读任务：CN标的审计/备考/完整交易和H1购买日起并表桥；HK正式presentation中的Ximalaya及混合业务；US正式call/deck中的Azure/M365调整、Windows/Xbox/许可转折与RPO/lifecycle。答案须来自新run实际读取，不从本表默认数值。

## 5. 共用金额、币种、reconciliation和sensitivity

| 检查点 | 实际复查方法 |
|---|---|
| 基础数字与单位 | 全部历史、未来参数、targets、约束、图表/正文数字逐项Decimal与原件对照。billion→million×1000；1billion=10亿；1亿=100million；万元→million×0.01。percent/fraction/percentage_points分清。scale变化不能改变原币种。 |
| 币种 | 每事实保原currency，模型币种由真实披露而非上市地决定；必要FX写原配对、时期、rate/公式和来源。HK股票港币交易不能推出收入是HKD；US原USD值不无故FX。CC增长转reported需真实时期FX影响，不把百分点当倍数。 |
| 口径与公司对账 | 同一FY合并收入=各segment effective revenue+显式signed adjustments−重复/抵销。基期重分类、opening residual、半年度/剩余期间、年度桥逐项可复查。收入加总、Increment/CAGR、终年增量、driver allocation均同一native DAG，不建第二预测表。 |
| 归因 | 三至五重要driver可短展示，但底层有证节点完整；没有足够driver不造。allocation sum-to-one只保证净增量对账，不是测量因果贡献；负业务、净零抵消、company adjustment保真实解释。 |
| 敏感性 | 对实际parameter扰动重新走native DAG，检查所有受影响业务/年份、共享约束、认收和company adjustment。排序按真实金额变化，不靠故事热度。单参数敏感性不能直接相加当joint结果；joint需明确交互约定。 |
| 场景 | Low/Base/High由可解释边界组成，结果维持原真实结构；延期/共享cap导致交叉时保原拒绝或单列conditional stress，不默默sort改变语义。Low=Base时解释实际实现收入/剩余期间下限及反证，不宣称伪概率校准。 |
| Confidence/backtest | stable-fsum/1分数/权重/组件不改；research adequacy另列。分数不是准确概率，宽range不是置信区间。无真实冻结预测与matched actual时observations=0、WAPE=null，未来未披露不能回填历史成绩。 |

## 6. Joint pressure的最小真实桥（R17）

每个重要共因只施加一次shock，列实际physical exposure/unit/timing、需求相关/客户funding、capacity allocation、delivery延期/cancel及catchup。不同业务共享资源需有真实分配和收入映射；Azure consumption与M365 subscription不能因都以USD记账就硬共享一个纯收入池。数量/时点未披露可用有证简化并说明影响，不能默认0.90/0.95代表low概率。

已有透明跨年桥可表达：当期原收入−明确受影响Q4收入；下一期原收入+受影响Q4收入×明确catch-up fraction；取消额=受影响收入×(1−catch-up fraction)。必须有真实Q4暴露、两年、相同currency/scale和[0,1]catch-up前提；不能年度/4猜季度，不能把此有限helper当所有cohort/认收模型。压力仅示意时明确stress，不能升级calibrated。

## 7. 完整流程证据出入口：沿既有工具，不新增门禁

A. **scope/source preparation**：新的scope冻结actual repo/installedSHA、as-of/三年、配置目的/model options/pricing/profile/caps与实余量。RF实际source_preparation→FF→CWP查询/公开实读，必要missing才按现有CN StockInfoDLSimple/HK-US实际能力/ET路由下载。保存每document业务状态、call_id、原生usage和SourceRef到现有document_matrix/source_ledger；0GET reuse与旧失败原因分别记录。不要将exit0顶替所有材料状态。

B. **CWP实际初级处理**：原字节→正确格式parser→0.7选择/语义组→按配置真实有限摘要→verify/publication→public read。SSE走official import/project/replay/export/AUTO同一流程，Ref1原件与Ref2投影artifact区别；每个claim保正确parent、issuer、source role、as-of、locator及限定。partially read与skipped不冒充全文已用；首次真实失败保W04受界final诊断与实际费，恢复不重复计费。原H1/IPO/UScall等旧失败必须有新的真实原生结果，loopback不算配置供应商验收。

C. **独立研究输入**：用公开verified read形成claims，author native input、operating_research及management targets；按实际可证范围处理所有重要资料，used / not_used_with_reason / exact covered_by，读取但未进依赖为not_consumed。先确定事实/范围/转换与反证，再scenario假设，不照旧预测填数。source-only系统不保存投资结论，不跨写StockWiki/IQS/Dayu。

D. **已有实际assembly/计算入口**（只给真输入，不执行本文样例）：

```text
python -X utf8 -B tools/build_auditable_case.py
  --company <实际标签> --input <author-native-input.json>
  --research <operating-research.json> --preparation <实际source-preparation-result>
  --discovery <实际bounded discovery receipt> --as-of 2026-10-08
  --output-root <新的absent-owned-dir>
python -X utf8 -B tools/run_target_measurement_e2e.py
  --input <assembled>/linked-input.json --output-root <新的native-output>
python -X utf8 -B scripts/research_support_diagnostics.py
  --input <同一真实native input> --output <新的diagnostics.json>
```

实参按当前已安装入口/help/既有公开recipe，不猜callback/ENGINE_VERSION字段。每个run_forecast/snapshot子进程的REVENUE_PUBLICATION_REGISTRY明确指向本owned scope，finally恢复环境。既有步骤完成 native lint/hash/validate→compute/render→strong recompute→registry/snapshot，保存精确argv/exit/stdout/stderr/actualsourceSHA/time/version；输出JSON/Markdown/snapshot是同一输入和DAG。支持诊断不启动provider/compute、不覆盖原输入或已有output。

E. **封存与独立四审**：完成新execution manifest后四个不同上下文agent分别storage、fetch、process、buy-side analyst逐项审新attempt，executor不自审，不能拿旧报告当新PASS。process核全部数据/单位/公式/目标/敏感性；analyst核幅度、三年、控制/认收/共因/反证。差错归type和真正根因，写新attempt复验链，不改旧sealed。

F. **交付/恢复**：formal native result +同renderer Markdown +registry/snapshot +可打开TRUST_BOUNDARY/source链接；所有关键来源在四审完成前可读。结束关闭DB/process，核初始保护项，删除仅本次解析出的owned TEMP/新测试产物，保必要小回执与最终结果/来源引用。不能把来源清掉导致审查缺证，不能全湖backup/recovery。

## 8. 接受边界与现代码已修/待证明

| 责任 | 当前证据 | 新真实研究仍需证明 |
|---|---|---|
| W07期间/证据角色 | 已接受显式half/quarter period-flow与future角色分离；旧emitter只读兼容。 | 输入真实H1/Q/FY语义、证据范围是否支持未来机制/幅度；两个source不能自动triangulate历史/融资。 |
| P7-RF calibration | 已发布4.2.1/47f497ad：observation binding、scope→actual native output、conversion applicability period→实际FY cell；shared PID per segment×scenario×year、多校准顺序独立、真实company scope和跨期桥；未知仅诊断、无新许可。 | 可比范围和转换参数的经济真实性、各年三情景未来幅度、管理目标和joint压力。结构supported不是买方质量认证。 |
| W03/MAIN来源选择 | 真实public3已证明raw/official统一版本、正确native parent/role/locator、真实0.6历史只读、新0.7generation不旧误reuse及TXT完整双指纹。 | 全重要材料业务recall/限定与真实配置供应商摘要质量；原三家公司真实runtime和四审，不以计数/tag覆盖研究。 |
| W04/06 | 已有有界failed-final/计量与真实来源成功失败usage共用接线接受。 | 真实配置模型输出/费用/恢复、逐document正确状态；未知收费继续母账。 |
| W08 | 已盘点现存原件和真实正文缺口，避免重复下载。 | 当前source实读资格/原文、SSE真正import及全部范围、交易/控制/benchmark原正文；403/204/entitlement不能由工程复原。 |
| W05/P7-AUDIT | 当前MAIN记录P7-AUDIT未交；其独占源码不动。 | 实际executor/checkscope及四review完整落盘，不能假定未交付的audit更新已安装。可使用已有正式流程，由MAIN按排他边界接线。 |

研究GREEN需要重要未来幅度/时点/转换和falsifier能从原件复查，请求三年实质支持。工程通过、计划交付、预算耗尽、confidence0或“全部typed checked”不替代此结论。真实无法取得的数据列证据/影响/合法替代/未完成责任，保持overall partial；不靠输入调整绕门、不额外添加逐条人工审签。原三家实质问题复验后才按既定新A/H/US三家泛化，再NVDA/池loop；本只读准备不激活新目标。

## 9. 仅MAIN/独立审查：封存问题索引与旧反证

R16映射16项、R17 7项、R18 17项，因重叠合35去重（新M3 23、旧fresh 12），都在原157 coverage内。它们不是本次新发现，也未因4.2.1工程接受关闭。索引取冻结root_causes/coverage，而不是人工另造问题集。

| 共因 | 旧sealed反证，用新原件/模型逐项推翻或如实保留partial |
|---|---|
| R16 horizon/幅度 | CN只一年且H126×FY25/H125机械Base增长34.8886%；HK15个H2因子无独立幅度并将FY26复制FY27/28；US只FY27且FY26历史delta×0.5/1/1.5未有量价转换。未来flat/conditional不是补齐三年。 |
| R17 joint | CN全1ratio joint等于Low；HK0.90/0.05和US需求90%/供应95%/reserve10%仅示意。需真实曝光/时点/分配、延期/取消/catchup，不以USD池代物理资源。 |
| R18 最小经营/目标桥 | CN产品/chambers混口径、众硅交易/控制/全年承诺vs集团购后；HK Ximalaya控制与混合收入；US guidance转折、CC/adjusted/FX、付费/注册/preview/RPO的阶段。 |

**特别纠正旧口径而不改旧报告：** W09/SKILL_CHECKPOINTS依据原图p21（`execution/deck_images/p21-image21.png` SHA `fa3b238c348236c19d17948f68815f56250a946a3bbe93d755a207441c12bddf`）确认原文Azure Q1 **44–45% constant currency**；FX减少报告收入少于1point。**43–45% reported仅analyst有端点的conditional包络，不是另一原文reported指引**。新执行须实际打开原图/来源重新核；不要把本附录包络塞成官方claim。M36517%CC/18%prior-year recognition adjusted及commercial范围分别保留，RPO total/commercial/next12m conversion不混加。

**已记录经营数值仅为复核定位，不能成为新预测默认参数：** CN披露刻蚀9832/LPCVD506/设备10527百万元；销售1240/生产1660/库存1010腔，10527/1240≈8.4895百万元/腔只是mixed proxy。众硅交易64.69%、期末77%、2026-05-31控制、购后至6/30收入1.29190208百万元、标的2026/27/28全年承诺280/430/580百万元分别复读/对账。HK原审查751766 CNYmillion=7517.66亿元，不能由股价币种改成HKD。US原审查RPO total684b/commercial678b/约30%next12m及30m paid Copilot、E7新增millions、Fabric40000paid、Agent36540m registered、Perception preview保各自unit/stage，不制造conversion。原Decimal检查CN197/HK806/US778基本算术均无金额失败，故当前核心缺口是经济输入/解释，不能无依据重写算术引擎。

以下报告位置均 `C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/<run_id>/reports/<role>.json`；每项pointer定位旧finding，来源原文件SHA在inventory完整列明：

| 新M3 issue key | 原报告 pointer |
|---|---|
| `m3-20261009T184946-cn-688012/storage/M3-CN-STORAGE-006` | `/findings/5` |
| `m3-20261009T184946-cn-688012/process/CN688012-PROCESS-001` | `/findings/0` |
| `m3-20261009T184946-cn-688012/analyst/ANALYST-CN688012-001` | `/findings/0` |
| `m3-20261009T184946-cn-688012/analyst/ANALYST-CN688012-002` | `/findings/1` |
| `m3-20261009T184946-cn-688012/analyst/ANALYST-CN688012-003` | `/findings/2` |
| `m3-20261009T184946-cn-688012/analyst/ANALYST-CN688012-004` | `/findings/3` |
| `m3-20261009T184946-cn-688012/analyst/ANALYST-CN688012-006` | `/findings/5` |
| `m3-20261009T184946-hk-00700/process/M3-HK-PROCESS-001` | `/findings/0` |
| `m3-20261009T184946-hk-00700/process/M3-HK-PROCESS-002` | `/findings/1` |
| `m3-20261009T184946-hk-00700/analyst/HK-ANALYST-001` | `/findings/0` |
| `m3-20261009T184946-hk-00700/analyst/HK-ANALYST-002` | `/findings/1` |
| `m3-20261009T184946-hk-00700/analyst/HK-ANALYST-003` | `/findings/2` |
| `m3-20261009T184946-hk-00700/analyst/HK-ANALYST-004` | `/findings/3` |
| `m3-20261009T184946-hk-00700/analyst/HK-ANALYST-006` | `/findings/5` |
| `m3-20261009T184946-us-msft/storage/MSFT-STORAGE-007` | `/findings/6` |
| `m3-20261009T184946-us-msft/process/M3-US-PROCESS-001` | `/findings/0` |
| `m3-20261009T184946-us-msft/process/M3-US-PROCESS-002` | `/findings/1` |
| `m3-20261009T184946-us-msft/analyst/ANALYST-001` | `/findings/0` |
| `m3-20261009T184946-us-msft/analyst/ANALYST-002` | `/findings/1` |
| `m3-20261009T184946-us-msft/analyst/ANALYST-003` | `/findings/2` |
| `m3-20261009T184946-us-msft/analyst/ANALYST-004` | `/findings/3` |
| `m3-20261009T184946-us-msft/analyst/ANALYST-005` | `/findings/4` |
| `m3-20261009T184946-us-msft/analyst/ANALYST-007` | `/findings/6` |

旧fresh12项完整ID沿冻结root_causes/coverage，不在执行safe包复制旧forecast。新问题签收以新run/role/issue compositekey建立supersedes/复验链，工程/runtime/研究/外部分开，全部P1/P2/P3保处置；不删历史反证。

## 10. 本次只读依据与冻结回执

已完整读取W09、MAJOR_NODE、I02/I05、SKILL_CHECKPOINTS及MAIN当前计划/P7_RF_ACCEPTANCE/W08-readiness；已读RF已接受当前evidence-role-calibration/economic-support-diagnostics/management-targets/target-measurement-comparison/growth-driver-tree的实际reference。CodeGraph canonical index结果未覆盖新P7；隔离RF索引返回not initialized，故按已知文件读取，不初始化或改索引。未运行工程/研究测试、任何forecast/runtime/API/LLM、provider、secret读或Git/install操作。

12份M3四审JSON实际byteSHA全部与report_inventory匹配；下表冻结专家6文件与12sealed报告前后字节保持。当前共享PWF由MAIN维护，只作为本时点状态读取，本文不改它们。只新增本文件，无其它写入；无新TEMP、网络、下载、模型或费用。

| 原冻结依据 | SHA-256 |
|---|---|
| `m3_root_remediation_2026-10-09/root_causes.json` | `4881a4fa5966e068b8d05ef1fe65f2cd2e0ce1a5b16da924a411604a95496d90` |
| `m3_root_remediation_2026-10-09/coverage.json` | `bf523eaa37bb28b1e414ae3e6d6c09e38e0ba2d65638bf25ef6776fb134df64a` |
| `m3_root_remediation_2026-10-09/report_inventory.json` | `a172ba7f27bd555a90a88b156431dfb159c19ffd9caedde6a5bde857cfe3db0e` |
| `m3_root_remediation_2026-10-09/work_packages/W09.md` | `818cb26ef7b8bc7e92af1db26cad38306cc5c3a391732149d03f8cb3ae5153da` |
| `m3_root_remediation_2026-10-09/MAJOR_NODE.md` | `b56be25141e555b63c9a8bd543db373da45f3399c569247cb16bf5ae2eb3aac1` |
| `m3_root_remediation_2026-10-09/SKILL_CHECKPOINTS.md` | `01011bb7cfdc927e5691e52cd69e4ace6cf8f1d90f592c10819e49edd0b6784c` |

12报告具体SHA及byte size见inventory；本次全部读取并匹配，未重写seal。本文只是新重跑的经济输入/质量检查表，不是新research产物或经济接受签收。
