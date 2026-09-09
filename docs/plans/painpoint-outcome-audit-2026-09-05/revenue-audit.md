# Revenue 原痛点结果审计（独立子审计）

状态：本子审计完成，供总审交叉复核；初审 2026-09-05，恢复与补审 2026-09-06。仅新增本文；不修改被审代码/测试/原计划，不执行生产入口、网络或发布。总计划见本目录 task_plan.md。

## 审计范围与证据纪律

P08/P09；ZR601–611、701–713、802/806、CA302。按实现、接线、真实结果、证据有效性分别判断；合成 fixture 可证明局部逻辑，不能替代真实公司 source→处理→事实→模型链。代码根为 `C:/Users/郑曾波/Projects/revenue-forecast`，下文路径相对该根。

## 已确认的初步反证（待全范围汇总）

1. `tests/test_ca302_three_journeys.py` 的 second-mining 先手写操作数调用 helper，随后实际 engine 仍调用 `_zijin_document()`；non-mining 也复用 `_zijin_document()` 后取 trading 段，并另测 direct_growth。不是三个真实公司的旅程。`reconcile_layer(net, net)`/`reconcile_layer(base_2026, base_2026)` 是自比较，不能证明与外部披露勾稽。`test_c4_formal_receipt_chain_complete` 中 `assert not isolated_registry.exists() or True` 恒真；测试文档称零 registry bytes，但 formal 测试实际要求写入 1/2 行。结论：CA302 的真实三公司和零副作用文字主张被本身测试反证，而非已完成。
2. `tests/test_zr609_zijin_pilot.py` 明示 synthetic-but-realistic；`tests/test_zr709_zijin_journey.py` 明示 hermetic T1、test-only shapes。这可作契约/回归证据，不是原要求的真实紫金+第二矿企数据验证。
3. `scripts/mine_year_operation.py` 模型只有 volume/grade/recovery/payable/product/period/scenario 七字段，无 volume/grade/output 单位；计算直接相乘。docstring 允许 grade 为 `%` 或 `g/t`，然而 `450×2.8×0.86×0.965` 在 ZR609 被断言为 1045.674，未把 2.8% 转成 0.028，也未显式约束调用者必须预归一化。计量口径不可安全用于真实矿山。
4. `scripts/commercial_terms.py` docstring 称 TC/RC/premium per-unit，但计算直接减 tc+rc/加 premium，而非乘各自计价数量；payability 被校验却完全未参与计算；没有币种/单位/计量基准字段。无法证明原商业条款痛点已解决。
5. `scripts/asset_ownership.py` 有 `fraction_for_period` 默认拒绝跨期持股变动，但 `apply_ownership_share` 实际只用 period end 的 `effective_group_share`，忽略 start_date；存在 A→B→A 时 `fraction_for_period` 首尾相同直接返回 A 的逻辑。年度持股变动可绕过显式按日或阻断契约。
6. `scripts/internal_flow.py` 的 `eliminate_internal_revenue(external_revenue,flows)` 返回 net 永远等于传入 external_revenue，只展示 external+internal→external 桥；输入必须已经是正确外部收入。不能作为从矿山/冶炼/贸易毛额真实消重的证据。

## 调查日志及限制

- 已完整读取 planning-with-files、总计划、上述五个模型源文件及 CA302 测试；合并读取 ZR609/709/802/806 测试输出发生截断，未声称那些大文件已全读，后续分块。
- CodeGraph context 查询可用但 broad query 仅命中旧 registry/backtest；mine symbol search 无目标结果。使用已由文件清单定位的具体文件读取，不据索引缺席推断生产不可达。
- 尚未运行测试；以上来自可定位静态代码，而非运行结果。

## 复审基线与方法

- 2026-09-06 再核 `git rev-parse HEAD`：`2ff20d9b410d3498181f7258a23ed9625caab826`；`git status --short -- scripts tests` 无输出。Git 的用户 ignore 配置读取出现 Permission denied 警告，故不将该结果扩张为全仓无 dirty。其他线程修改仍须由总审使用文件 hash/最终 HEAD 再核。
- 已读取原 `audit_review/2026-08-13_zijin_data_lake_remediation_plan/work_unit_registry.md` 本范围全部验收条款；另读 ZR610 ADR/独立 reviewer JSON、ZR611 单元卡，以及本范围全部 implementer receipt 的命令/日期/triplet 字段。receipt 主要为 8 月历史提交，不能自然继承为当前 HEAD 全绿。
- 原 ZR601–604 owner 是 company-wiki，本报告评估其 revenue 消费及同号验收失真；上游 AssetFact/alias/extractor 的独立实现结论由总审补充，不把 revenue 同号单测替代 owner 实现。
- 全读：模型模块 mine_year_operation/commercial_terms/asset_ownership/internal_flow/reconciliation/schema_optin/mixed_recognition/confidence_policy/rolling_backtest/publication_registry/revenue_forecast/generate_input_template/schema_fields；production 核心入口与 document/analysis/segments 相关片段；测试601/602/604/701/702/703/704/705/706/708/712/713/802/CA302。大测试609/611/707/709/806按相关区块核读，并明确未声称全文覆盖所有行。
- 只执行一次无文件输出的 `python -B -c` 纯函数探针；未调用 source_preparation、worker、下载、run_forecast formal、任何数据库或 scheduler。没有运行整套 pytest：测试会 formal-register，部分声称纯的测试仅看无关 tmp_path；在当前“不得修改原目录”授权下不能直接全跑。
- 错误日志：一次默认 cwd 被 sandbox 映射为 `C:/Users/Default/.codex/.sandbox/cwd`，导致 sibling 相对路径不存在；改用绝对路径 + 显式 workdir 后读取成功。一次合并输出被截断；后续针对关键函数/验收条款分块读取，未将截断输出视为完整核验。

## 当前问题与证据链

### RF-A01（P0）真实三公司验收被合成自比较替代

原要求：ZR609/CA302 的真实紫金主要资产、另一种结构矿企、非矿企，经过真实来源→worker→事实→参数→模型→勾稽，且不得借合成数据把真实缺口报成完成。

证据：`test_ca302_three_journeys.py:test_c2_second_mining_journey` 手写一个金矿 operation 后，draft 仍用 `_zijin_document()`；`test_c3_non_mining_journey` 仍用同一文档的 trading 段 + helper direct_growth。`test_c1_zijin_canary_journey_full` 对铜收入自身调用 `reconcile_layer(base_2026,base_2026)`。两次独立来源输入、实际提取和不同公司的整份 forecast 输入不存在于这些验收路径。`test_zr609_zijin_pilot.py` 顶部公开声明 synthetic；implementer 的 RED 由“真实结构演示缺失”改成“演示旅程缺失非产品缺口”，与原 pilot 验收不等价。

`test_zr806_real_t2_samples.py` C3 仅检查原 PDF/sidecar 的 fiscal_year/entity/hash/byte_size，broker仅检查存在和无sidecar；未把任何样本交给矿山输入/forecast。其 C2 可以证明生产 resolver 的几个特定样本历史可读/诚实 MISSING，但不能证明三根已可复用、broker已处理或矿山预测已完成。把 published_date<=today 当“fresh”也不证明 provider latest/freshness SLA。

结论：CA302、ZR609、ZR806 的端到端完成主张 CONTRADICTED；不能据此说真实公司结果已正确。已有合成测试可以保留为 T1，不是毫无价值。

### RF-A02（P0）矿山量价的单位与商业基准没有形成可执行契约

`MineYearOperation` 没有 asset_id/commodity_id/source locator/basis/volume_unit/grade_unit/output_unit，只有七字段；`_positive_numeric` 用 `>0` 而非 finite 校验，正无穷可以通过。`derive_saleable_volume` 直接四项相乘，grade 的 % 与小数、g/t 与吨并未区分。ZR609 的铜例将2.8%当2.8乘入；ZR611 同样把注释0.5%当0.5。

`CommercialTerm` 仅 value/source任意非空文本/assumption/period；无source_id+locator、term计价币种、分母单位、TC干精矿数量、RC应付金属数量、湿干吨换算、费用期间和FX方向。`calculate_net_revenue` 直接减tc+rc、加premium+byproduct，虽docstring宣称per-unit。payability字段已暴露但计算完全忽略；若volume本来已payable，应拒绝重复输入或声明已应用，而不是接受一个无效旋钮。缺少这些语义时，增加敏感性次数不能修正公式。

纯函数实测：

| 输入 | 当前输出 | 判读 |
|---|---|---|
| volume450, grade2.8, recovery0.86, payable0.965（测试注释grade=%） | 1045.674 | 2.8%未除100；若按kt ore且grade%，应为10.45674 kt payable metal；现契约无法表明单位 |
| saleable_volume100, price100, tc2, payability0.5 | gross10000, deductions2, net9998 | 不是按100单位乘TC的9800；payability也无效。实际应如何组合取决于明确的paid/unpaid basis，不可盲猜 |

结论：ZR605/606 的真实可用性 CONTRADICTED；“参数不缺/公式可重复”不等于计量正确。

### RF-A03（P0）权属、合并、内供、勾稽仍缺真实决策链

`apply_ownership_share` 循环拿到(start_date,end_date)，却只按期末做effective_group_share；`fraction_for_period`首尾相等直接返回，遗漏期内A→B→A。实测全年100，0.2于1月、0.8于7月，返回80；0.2→0.8→0.2默认不拒绝返回0.2。与ADR“期内变动默认拒绝”直接矛盾。合法0权益、停产0产量也被通用positive约束拒绝，不能完整表达退出/停产（后续设计须区分缺失与真实0）。

`internal_flow.eliminate_internal_revenue` 需要调用者先提供external_revenue，再算gross=external+internal, net=external。该函数可以合法用于显示既知external的桥，不会推断或消除未识别的矿山→冶炼→贸易重复额。没有合并范围、权益法排除、principal/agent判断、flow ID唯一/双边对账、资产至分部的绑定。

`reconciliation` 对两个任意数做容差比较，不绑定披露reference的source/locator/accounting basis/period/currency。`gap_report` docstring承诺不会接收伪volume×price，但代码只能识别finite，无法识别伪来源；CA302自比较将此能力放大成“已勾稽”。

结论：ZR603/607/608的局部helper存在，但原“集团外部收入”痛点未闭合；不能把equity-attribution相加直接充当合并收入。

### RF-A04（P1）新增schema/混合模型字段没有驱动主引擎

`contracts.document.validate_document` 调用 `validate_operating_units(data)` 后丢弃返回值；`revenue_core._build_forecast_draft`/`forecast.segments.calculate_segment_forecasts` 从已有segments/scenario driver_parameter_ids计算，不从operating_units生成量价、权属或internal flow。`test_zr709...test_j2_schema_38_operating_units_embedded_zero_numeric_drift` 要求新增units前后数值一样，证明兼容但不证明units被消费。更改units而segments不变仍可能只变input hash不变收入；需要新的变形测试区分“不影响旧3.7”与“3.8必须消费”。

`mixed_recognition.validate_commodity_matrix` 只拒绝重复segment name，不验证asset×commodity×product矩阵或重复base_revenue；同模块另两函数只检查枚举。不是实际混合计量/收入确认扩展。现主引擎已有segments和recognition能力不应丢弃，但不得宣称仅加helper就完成ZR707。

### RF-A05（P0）publication尚非prepare/commit事务，纯API默认反而写入

链条可逐行复核：`revenue_forecast.prepare_forecast(data,mode='formal')` → `revenue_core.run_forecast` → `register_publication` → registry append+fsync → 返回 → CLI才 `_atomic_write_text(output)` → 最后render/write markdown。任何output无权限/缺父目录、os.replace失败、markdown渲染/写失败、进程中断都可留下“已注册但交付物不存在或不全”的状态。单个文件temp+replace解决半文件，不解决多个交付物与registry跨资源一致性。未见prepared/committed事务ID、恢复journal和精确一次去重；测试`test_zr710...same_input_twice`明确预期2条append而非同一operation精确一次。

ZR710故障测试注入registry失败再确认无output，只覆盖“先失败”；直接对atomic-write helper注入replace错误，没有在真实CLI的registry成功之后注入错误。原最重要失败窗口仍漏测。

`prepare_forecast`首段称pure但默认formal。ZR701的pure测试调用默认formal，仅检查从未传入引擎的tmp_path为空；真实registry路径由环境/默认决定，与tmp_path无关。这是错误测试oracle，不是零写证明。`--validate-only`当前明确使用draft并提前return，已修复原“验证也formal注册”的狭义错误；但纯prepare默认契约仍CONTRADICTED，不能全项报完成。

附带静态缺陷：`publication_registry.audit` 的by_generation键是四元组(input,engine,schema,type)，但后续检查 `claimed not in by_generation` 用input字符串，故有效已登记artifact也被报unregistered。该分支须加入正例，不应只有伪造负例。并发append无跨进程锁/CAS，两个进程可读同prev后分别append断链；需与总发布事务统一设计，不能仅chmod当互斥。

### RF-A06（P1）generator闭环验收没有用generator，当前骨架仍内在不一致

`generate_input_template.build_template` 将场景model设direct_revenue/driver名revenue，却以dimension='ratio'创建该driver；`model_registry`规定direct_revenue.revenue维度必须revenue。其monetary parameters也没有currency/scale，而document validator要求与顶层严格相同；骨架默认as_of是base_year的6月30日却含该年度完整历史。仅“填写值/重算hash”不足，还要人工修结构和日期。没有矿业模板mode或units输入结构。

`test_zr702_schema_source_of_truth.test_c3_full_chain_lint_validate_draft_one_pass` 实际data=forecast_document()，不来自build_template；其他用build_template的测试只查键存在/FIXME被lint拒绝。故绿色不证明原最小+矿业模板真引擎闭环。`schema_fields`的四组required tuple只是linter字段表重定位；generator和runtime仍各自手写结构，不能扩大为所有schema单一机器真相。

`test_zr703...`主要搜旧schema 3.6字样和版本allowlist，未保留原要求的linter clean而engine fail反例/自动执行docs examples。版本号与capture10键的具体改进存在，但“字段齐”不足以防止上述dimension错误。

### RF-A07（P0）ProcessingDemand是本进程成功后内存队列，失败需求并未到worker

`source_preparation.py`顶层`_preparation_demands=DemandQueue()`；注释明确in-memory/persistence later。成功构造record后才 `_submit_preparation_demand(record)`，key优先source_id，enqueue now=0。失败/未找到源在此之前raise；CLI结束队列即消失。没有从真实缺失→持久需求→真实worker领取→结果返回的链。

ZR709 missing测试先看到CLI失败，再创建一个全新的本地DemandQueue，手动enqueue/claim/heartbeat/complete，不能证明失败请求自动提交。ZR706仅selector tests；`producer_events`来自DAG需要列表，不能单凭名称当已执行事件。ZR802第二次只断言download_calls0/source身份一样，未要求第二次parser/LLM/worker重复工作0；首次测试甚至`parser_calls>=1`，与docstring“精确预算”不一致。此处须与wiki journal/worker审计合流。

### RF-A08（P0）ConfidencePolicy与滚动回测没有兑现反博弈/真实历史含义

主引擎`analysis.confidence.calculate_confidence`仍内置20/25/10/15/15/15和80/55，历史分仅依据WAPE可达15；新`confidence_policy`未进入该计算。`detect_gaming_mutations`只检查record_sha非空，不重算；其wrong-record单测把hash改None，不是改内容保留hash。纯函数实测`record_sha256='not_a_hash'`且observations3得到rejected=[]。one-observation只写disclosure，不施加分数cap。注意：主旧`validate_historical_accuracy_records`确实会重算hash并拒绝重复backtest_id，不能误说全系统不校验hash；但只是自包含JSON内容hash，不核外部snapshot/actuals/evaluation是否存在、是否当前公司、是否在forecast as_of前已可知。

`rolling_backtest._mine_volume_window`只从actuals.operating_units推导saleable_volume，未读snapshot的预测矿量、wape始终None；这不是mine-volume误差回测。`run_rolling_backtest`按len(windows)解除cap，不检查窗口独立性/唯一origin/不同snapshot；测试使用同一forecast_document产生相同snapshot、相同actuals，只换as_of日期即可uncapped。也未把cap结果强制消费进最终confidence。缺mine units时静默跳过该层，仍可uncapped。

时间防线仅检查actuals.sources.published_date<=window.as_of，并未明确约束snapshot预测origin、input source/assumption已知时间、evaluation date三者。应分别定义forecast origin（禁止lookahead）与evaluation as_of（允许后来真实actual发布），不能用后移窗口日期绕过独立历史预测要求。现测试不存在真实紫金滚动source事实窗口。

## 逐项判定矩阵（覆盖27项）

I=实现，W=生产接线，O=原用户结果，E=证据有效性。PARTIAL代表可保留局部能力；CONTRADICTED代表存在足以推翻“整项已解决”的实质反证，而不是声称每行代码都错。

| 项 | 原验收对照与当前I/W | O/E与结论 |
|---|---|---|
| ZR601 | 原owner AssetFact schema/type/alias；revenue测试只测resource/reserve stock-flow，模型算术确有实现 | 上游schema/alias待总审；收入侧未显示source资产绑定。PARTIAL，不能由同号算术tests关闭原卡 |
| ZR602 | 原basis必填/单位归一；收入validate_parameter_basis是可选加性，缺basis放行；MineYearOperation也不补强 | RF-A02，PARTIAL；错单位可能通过七字段入口 |
| ZR603 | timeline/链式份额/geography helper已实现，但年度apply只用期末 | RF-A03实测反证；CONTRADICTED |
| ZR604 | 保留多parameter+status、最多1 accepted；all pending也通过，parameter_index仍全保留 | 缺提取/人工review来源与被消费参数accepted门；PARTIAL，待上游合流 |
| ZR605 | 七字段校验+乘积helper；schema3.8验证后丢弃结果 | RF-A02/A04：单位/finite/basis/主引擎消费缺口；CONTRADICTED |
| ZR606 | 商业条款helper可复算，但TC/RC单位/FX基础/payability语义缺失 | RF-A02实测；CONTRADICTED |
| ZR607 | internal gross/net显示桥存在；非真实合并/双边消重算法 | RF-A03；PARTIAL，不能宣称集团外部收入已正确 |
| ZR608 | 容差与gap helper存在；没有强制source-bound独立reference | RF-A03+自比较验收；PARTIAL |
| ZR609 | synthetic Zijin shapes+匿名pure-gold helper | 真实主要资产/第二真实矿企未验证；CONTRADICTED |
| ZR610 | 独立accounting reviewer JSON存在且accepted；ADR正文§9仍accepted待确认；明确单位转换和内供移交后续 | HISTORICAL_ONLY/PARTIAL；不否认独立review存在，但未验收后续实际模型且ADR期内变动已违背 |
| ZR611 | 合成8类helper组合符合T1方向，数据明确合成 | 不要求真实本身合理，但单位/内供错误被复用oracle锁绿；PARTIAL |
| ZR701 | version/capture常量若干统一，四组linter字段表已迁移；同号测试实际跑draft/formal与memory demand | 原“所有schema machine truth”未完整实现；PARTIAL |
| ZR702 | build_template存在但维度/monetary结构错、无矿业模板 | full-chain测试换用forecast_document；CONTRADICTED |
| ZR703 | 旧版本字样清理/allowlist已有 | 未证明linter子集负例和docs示例自动执行；PARTIAL |
| ZR704 | CLI validate-only走draft/提前return，历史专测registry bytes不变；prepare默认formal仍注册 | 狭义CLI改进真实，整卡纯prepare不满足；PARTIAL |
| ZR705 | draft可render路径/receipt mode+payload防篡改专测存在；formal注册 | 局部可用，历史T1未重跑当前；N/N-1与后续事务链未独立复验。PARTIAL/HISTORICAL_ONLY |
| ZR706 | 来源链消费envelope+selector，但失败RuntimeError、仅成功后memory demand | RF-A07；CONTRADICTED |
| ZR707 | mixed_recognition模块只枚举/name uniqueness；既有segment引擎仍主路径 | 不等于mine×commodity×product/accounting bridge；PARTIAL |
| ZR708 | snapshot/hash/metric→historical_accuracy→confidence接线真实存在，主校验会重算record hash | 仅合成历史专测；公司/日期/外部链真实性仍不足，PARTIAL |
| ZR709 | 五年合成F2+fixture三进程各子旅程存在 | J1 company_release代替broker_research；missing后另造队列；J2数据非J1抽取，非真正连续链。CONTRADICTED |
| ZR710 | 单文件atomic-write已实现，registry先append | 多资源事务/恢复/精确一次未实现，RF-A05；CONTRADICTED |
| ZR711 | 3.7↔3.8 converter可逆，加空units不猜数正确 | units仅校验不进计算，consolidation结构未体现；PARTIAL |
| ZR712 | 新policy纯helper可测，但主confidence没有消费；伪hash/one-observation门无效 | RF-A08；CONTRADICTED |
| ZR713 | 多窗口包装与hash存在；mine仅actual分解、重复窗口解除cap | 真实rolling-origin/no-lookahead与评分接线不满足；CONTRADICTED |
| ZR802 | 真实三进程fixture覆盖状态，有价值T1 | 再次parser/LLM0和精确预算未测，失败stage链仍字符串；PARTIAL |
| ZR806 | 真生产raw/sidecar/resolver样本T2历史证据 | artifact/mine/forecast没消费；当前全旅程不成立，CONTRADICTED |
| CA302 | 真实三公司要求被同一合成document替代 | RF-A01，CONTRADICTED |

## 给总修复计划的详细输入（建议，不是实施授权）

此处提供工作包素材；总审完成全部仓库后再在总计划冻结顺序/验收，不在本子审计中提前执行任何修复。共同规则：每包都须独立agent先审原痛点/RED，再审契约/设计，再审实现与突变，再审真实旅程证据；implementer不得自签关闭。任何真实下载/LLM/worker启动/生产写、安装同步、发布、定时任务修改须单独授权。

### WP-R1：纠正验收对象，建立三公司连续链

1. 新建（获授权后）manifest列真实公司ID、结构差异、原始source SHA/locator、每个事实ID/参数ID/模型节点ID、worker demand/attempt ID、独立reference。允许缺口但逐字段标blocked/assumed，不以synthetic替真实。
2. 保留现T1并重命名声明为synthetic；替换恒真/自比较oracle；每个测试记录实际入口与输入来源，不能`forecast_document`偷换`build_template`。
3. 故意换第二公司/源hash/一个矿山单位、删除broker artifact、修改提取事实；验收必须被独立oracle察觉，并且只失效相关节点。
4. 真实三公司都从独立来源得到完整input；不满足输入的公司输出明确gap且不得计为forecast成功。每个成功必须独立手算至少一个矿、一个segment、公司external收入。
5. Exit：第三方reviewer可从manifest在新triplet复演；T1/T2/T3各自标记，不以raw文件存在抵扣实际消费。

### WP-R2：矿山单位、商业量价与basis契约

1. 独立会计/计量reviewer冻结asset/commodity/product、ore/contained/payable、wet/dry、单位/scale、source_id+locator、currency/FX方向、period、basis。明确resource事实≠名为resource的收入模型，禁止仅以model名替事实类型。
2. RED包含kt ore×%到t metal、kt ore×g/t到kg gold、0产量/0股权、NaN/inf、未知单位、source日期越界、TC干吨/RC应付金属单位差异、premium每单位/总额、副产品重复、重复payability。
3. 定义输入层显式归一化，保留原值/原单位/换算版本；数字转换不能只strip+lower，也不能临时凭公司名分支。每项商业fee必须声明amount或rate及计价basis，缺失即gap。
4. 集成到3.8 actual operating graph，units改变必须改变对应收入；不相关矿不重算。保留3.7数值/hashgolden但不以兼容性禁止3.8实际消费。
5. Exit：双独立实现的Decimal手算与生产浮点误差门一致；以上RED全部转绿，删除单位/改basis/改FX方向突变全部失败，真实三公司抽样单位可追溯。

### WP-R3：权属、合并、内供与外部收入勾稽

1. 冻结control/associate/joint-operation边界及acquisition-effective，分别输出100% operational、equity attribution、consolidated external views，不允许视图相混。
2. 年度权属默认任何期内change都blocked，显式pro-rata须说明仅模型近似；多级链按同一日对齐，A→B→A、退出到0、缺timeline、年中收购都要测试。
3. internal flow需唯一ID、seller/buyer、数量/品种/单位/币种、双边值、period/scenario及合并范围；从毛额输入做消重，不预先要求caller给正确external。未知内部/外部状态不默认external。
4. reference必须来自独立披露source/locator且同currency/unit/period/basis，不能将模型输出作为reference。reconcile分asset→external segment→company，并明确unallocated residual是gap不是收入plug。
5. 独立review每节点检查equity法和control的报表含义。Exit：内部成交价变化不应凭空改变集团external收入；重复flow/错单位/错控制判断/自比较reference都会被拒绝。

### WP-R4：真正纯prepare、原子发布与恢复

1. 分离纯compute+validate与明确commit；默认prepare禁止registry/sign/network/subprocess/文件写，可对所有写API设deny-spy证明。CLI --validate-only即使传output/markdown也不产生文件；前后全允许域tree/hash一致。
2. 设计publication operation_id、prepared/committed/aborted、所有artifact哈希、staging目录、append-only事务journal。明确registry为committed authority、恢复顺序、同operation重试只一次committed。不得删除/重写历史registry以假装没有孤儿。
3. 故障矩阵逐点注入：计算→验证→render→sign→stage/fsync→rename output→rename md→registry commit→返回；每点正常异常和进程被终止都复演。成功前不得宣称published，失败后可以机器恢复或明确pending。
4. 多进程同operation/不同operation并发、Windows共享锁/文件只读/长路径、磁盘满、输出父目录不存在、stdout broken-pipe都要有定义。registry audit已登记正例、未登记负例和同代冲突分开测试。
5. Exit：真正CLI在每故障点无静默孤儿，rerun恢复恰一次commit；独立agent从磁盘状态而非程序summary判断，不触生产registry。

### WP-R5：generator与schema可执行闭环

1. 从版本化contract定义生成字段/维度/required/recognition形状；至少minimal与mining模板。monetary字段包括currency/scale，direct_revenue与growth_rate不得错配。
2. 值填充fixture只能填写值/source证据和允许的假设，不得改结构/key/model/维度，随后lint→hash/capture验证→validate_document→draft→render。明确默认as_of与base-year完整历史合法日期。
3. 保存linter clean但engine fail的负例，输出说明lint不等价engine；文档所有可执行示例用同一流水线测试，capture计数与真实required一致。
4. Exit：生成物确实经引擎而不是test helper替代；删除currency、错dimension、错timebasis、错管理覆盖每个mutation都失败。独立agent审模板输出全字段而非仅版本号。

### WP-R6：持久ProcessingDemand与最小重算

1. 明确source_preparation失败stage envelope的数据结构；not_found、safety pending、artifact pending都保留upstream成功收据；不要截到800字符丢掉结构因果链。
2. 收敛到wiki唯一持久demand API/库，绑定source SHA/role/parser/model/prompt/policy/input bundle等键；先核权属禁止跨仓共享可变DB/直接写入。提交真实now，成功无缺角色不提交空需求。
3. 跨进程A提交退出→B worker领取→C读取完成；重复提交/lease失效/崩溃重启/版本失效测试。队列能重启恢复，失败请求需真的被提交，不得在测试另造队列。
4. 观测actual attempts而不是DAG planned list，首次缺什么做什么；二次exact zero download/parser/LLM，污染一个role只重算必要子图。获授权后只用锁定小cohort真实运行。
5. Exit：独立agent通过持久journal/实际artifact hash证明submission→worker→consumer闭环，预算与真实事件一致。

### WP-R7：历史真实性与confidence反博弈

1. 定义独立forecast_origin、evaluation_as_of、actual publication date、company/model/period identity；快照要证明在当时冻结，不能事后用同input换as_of制造多个窗口。
2. 实现外部snapshot→actuals→evaluation→accuracy链验证，WAPE从底层观测重算，不接收只有自签JSON hash的任意metric。observation按company/segment/mine/period/source identity去重，禁止split/duplicate/跨公司plug。
3. mine-volume必须有同mine/product/unit的预测与真实量配对，缺配对输出gap且level coverage cap；不可将actual decomposition算作误差测试。
4. 把ConfidencePolicy真正注入主confidence与输出验证重算，policy版本/hash入receipt；one-observation cap是数值约束而不只是disclosure；不足unique windows或缺关键level必须传播限制到最终评分。
5. RED包含同snapshot换日期、假record_sha非空、改WAPE重hash、future source/actual泄漏、跨公司record、重复观测拆分、单观测0误差、无mine预测。独立审查oracle不调用同一评分函数。
6. Exit：真实历史窗口不足就诚实capped；不为达标伪造旧快照。至少两独立真实origin与可核实当时来源证据才能解除相应cap。

## 子审计结论

原“骨架/契约测试通过”与“解决真实痛点”之间存在实质缺口，不只是计划文档未同步。最优先是阻止错误完成保证继续放行：真实验收替身、量价单位、publication事务、持久worker需求、confidence/回测五类都应重新开工，但本次只记录和计划。确实已有的局部能力（CLI draft验证、单文件atomic-write、source selector、基础snapshot/hash、segment引擎）应保留，并在独立RED/真实消费链上逐步补齐，不应因发现问题无差别重写。
