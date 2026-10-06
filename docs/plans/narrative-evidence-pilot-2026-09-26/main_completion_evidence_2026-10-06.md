# MAIN当前完成证据与真实缺口

截至 CWP 已发布代码`4826ad9c67bce3d3e2b977173d283341d18bc141`（精确CI37514053091一次全绿/52秒）、RF main`6e6b817a1a6e4567293a4dcb835815f3be508a03`、ET本地/真实远端main`2b9fb84660f98ce27a05709a7e31342ab044b4d2`。S0–S6既有核心节点有收据；完成审计发现R6局部容错未实装，现已184责任测试、正式离线E2E/RF消费和eae2dd4精确CI59秒绿。N5-RAW-DUP已集中修正/51项与CLI绿、已合入master a41244a并推远端、精确CI37523080920/57秒绿，DOCSET交接2c3583e已到待MAIN验收；**不宣称全部扩展工作完成**，不增加人工门或小节点复核。

| 原目标/责任 | 已有权威证据 | 当前边界/下一动作 |
|---|---|---|
| 选择有价值业务叙述，格式化资料可跳过 | N4-T2已合入`0657579d`；[N4真实run05](harness_lanes/results/n4c_live_2026-10-05_run05.json)、[run06](harness_lanes/results/n4c_live_2026-10-05_run06.json)、[run08](harness_lanes/results/n4c_live_2026-10-05_run08.json)、[修复后run10](harness_lanes/results/n4c_live_2026-10-05_run10.json)均有policy skip/0model；selector0.3.2已TDD并真实复测 | 四类有限样本已有真实provider final。电话会六类重点业务主题均在精选证据、五类进入短摘要；不是所有类型/主题全覆盖。[N5-DOCSET](harness_lanes/n5_document_quality_benchmark.md)补更广实证，不以selector输出自行生成golden |
| 同原语言摘要、精确引用与来源质量 | run05年报20claims/96locators；run06 IR13/11；run08招股25/160、238766 B；run10电话会20/46、99479 B。各实际final RF公开reference/read0、replay verified、translate=false；[电话会业务与角色复核](harness_lanes/results/n4c_live_business_review_2026-10-06.json) | metadata来自隔离fixture、字节为真实原件，不宣称生产元数据补齐。旧MiMo SUMMARY_INVALID规则未知；DeepSeek成功不证明MiMo问题已解决。run06按收据实数为8问题/6管理层；run10为5/15，旧9/5粗读记录不是权威计数 |
| 精选内容检索与精确读取 | [S5精选检索验收](harness_lanes/results/s5_selected_retrieval_acceptance_2026-10-05.json)，发布`1b0feb44`，102个不同case分次GREEN；真实微软TXT正式search/exact CLI、locator回放 | 该检索E2E模型为Replay；真实provider摘要与RF消费由run05/06另证，不能将两份证明混称一个模型检索全链。没有重新恢复全量legacy正文 |
| 多文档并发、失联恢复和持久预算 | N4 A/B已发布；本轮146相关Unit、14个CLI/cross-run/kill恢复case分两次全绿；[节点收据](harness_lanes/results/n4c_prompt_node_2026-10-06.json)、[精确CI](harness_lanes/results/n4c_prompt_ci_2026-10-06.json)37506642500 attempt1全部成功/83s | E6 P1/P2/P4真实字节+确定性模型实验已记录，不重复；paid run使用P4的compute并发3/model1，不能声称已测多provider同时外发或模型并发4。未知timeout照reserved计，预算不足外发前拒绝 |
| 跨项目解耦与来源虚拟化 | SourceRef/SourceExport v2；[FF正式合入](harness_lanes/results/p5_ff_main_acceptance_2026-10-05.json)main758e8f4；[ET-TXT验收并线](harness_lanes/results/n5_et_text_main_acceptance_2026-10-06.json)main2b9fb84；[RF默认v2正式合入](harness_lanes/results/p5_rf_main_acceptance_2026-10-06.json)main6e6b817a/精确CI绿；FF→ET→CWP离线CLI链及ET10 goldens未变 | RF复用自身已提交六模块，不修改owner树；读取准备不是预测计算全部完成。ET43份旧TXT无下载收据，均legacy_unverified，不冒充完整性已证实。Dayu零改；缺硬限额请求前拒绝。FMP真实402为套餐限制，不能冒充下载成功 |
| 降容、原件不丢、成功后清理临时材料 | [实际S5生产收据](harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)：7104旧文件/8191handle/1490530旧span退出，DB3055841280→222408704 B，净5659443210 B释放，17表digest与原件SHA保持 | 原件删除0，不将未测重复raw算已释放。新真实final的测得大小只是本样本结果；on-demand保存精选+一份final，不全库永久PDF→MD。所有paid试点根按要求清理，生产new final仍0。原件重复下一阶段只读[N5-RAW-DUP](harness_lanes/n5_raw_duplicate_audit.md)，不自动对象化/删原件 |
| 门禁/权限简化、日常测试不拖慢 | S0/G1与S6已发布；人工签收/TTL/旧whole-catalog入口退出；提交无pytest，推送精选12项、CI全Unit+同精选；本轮正常commit/push都GREEN | 保留字节SHA、来源身份/期间/公开日、引用回放、路径归属、lease/generation和资源预算自动校验。run07 document的legacy blocked_human标签不等于新增人工许可，真正停止原因为top-level budget_exhausted；不靠人工文件解锁 |

## N4C 当前结果与保留边界

零网络准备已按显式额度验证四份raw、RF六模块与目录恢复；[离线收据](harness_lanes/results/n4c_explicit_limits_preflight_2026-10-06.json)。工具不再默用旧60000，5项预算/CLI回归通过。用户随后明确批准累计200000 tokens/$0.12；下面真实run10已执行，离线准备不冒充模型效果。

P04已由run08 DeepSeek一次请求完成。MiMo run05两次MODEL_TIMEOUT后SUMMARY_INVALID、run07一次61秒MODEL_TIMEOUT无正文仍为真实历史；不将超时计成功、不推断旧失败规则。run08的25条招股业务摘要已实际返回并由RF核验。

旧T01摘要遗漏具体经营进展。MAIN先写跨行业经营正例/财务套话反例TDD，再实现selector0.3.2通用规则，parser0.1.0与locator不变；92个不同责任case分步GREEN。[零外发测量](harness_lanes/results/n4c_english_selection_2026-10-06.json)证明选择修复，真实摘要效果单独由run10验证。

run09曾返回finish_reason=length/input2305/output8192、MODEL_OUTPUT_TRUNCATED，系统未发布半截摘要；[失败收据](harness_lanes/results/n4c_live_2026-10-05_run09.json)保留，旧费用照计。不能将失败归因于人工许可或伪造为零费。

已按TDD实现私有prompt1.5最多20条/280字符/8个alias，优先具体管理层更新、去重；160段正文/角色/全部原文定位不减，公共reader/既有草案不加此门。2 RED→59相关Unit与2正式双语言CLI E2E GREEN，Ruff/mypy绿；Config、max_tokens、thinking、stream及超时不改。run09未保留reasoning/content分项，不推断截断来自哪部分。

兼容性直接验证：新增integration case建立独立原文/catalog，用25个管理层段落及每条超过280字符的模拟旧prompt1.4草案，经真实artifact prepare/activate和当前public transport读取，stdout bytes保持原样、全部locator replay verified、原件不变；1 passed/3.09s。首轮夹具把多句当完整span而StopIteration，改为单句原文，不改产品解析或校验。[小收据](harness_lanes/results/n4c_legacy_summary_read_2026-10-06.json)明确这是合成兼容测试，不是新真实模型验收。

run10只做一次DeepSeek T01+零模型policy：batch35.217秒/总42.828秒，20条摘要（15管理层/5分析师问题）、46个locator全回放、RF reference/read0、英文且translate=false，99479 B final。新数据中心、模型发布、Fabric客户采用、Copilot席位及usage商业模式进入短摘要；GPU dock-to-live效率在精选证据中，未在20条短摘要单列。六类精选覆盖与五类短摘要覆盖分别记录，**摘要非穷尽**，不以所有引用合法代替语义评估。生产new final仍0，试点根恢复absent，原件/配置/生产/RF owner保持。

本次9151tokens/9853microUSD、新unknown0/unsettled0；累计190035tokens/100502microUSD，历史unknown7/FX2764不退，余9965tokens/16734microUSD。费用为代理估算；剩余token不够同配置完整请求预留，不自动再POST。N4C有限样本节点已达到原计划的生产入口、真实final/消费者/计量/隔离/恢复/占用要求；不因此宣称供应商从不超时、多provider同时外发已实测或全库已处理。

## 外线与交接

[N5总包](harness_lanes/n5_parallel_packages_2026-10-06.md)已分派，ET-TXT已验收并线，DOCSET/RAW-DUP尚待完整交接。不要重派或提前声称已完成质量基准/原件去重；metadata估计不计空间释放，不删原件。RF/IQS/StockWiki owner树不另写，总PWF与共享接口仍由MAIN维护。

下一动作只取总task_plan：接收下一份N5完整交接后集中验收/并线，不重跑已绿长测，不建立第二任务库或人工门。S0–S6核心完成，**含未交付扩展的整体目标仍active**。

## R6补齐

[R6实施卡](r6_partial_summary_implementation_2026-10-06.md)与[集中节点](harness_lanes/results/r6_partial_summary_node_2026-10-06.json)记录局部坏引用只丢该claim、未知扩展不落盘、其余严格来源绑定不放松。184责任测试与实际原件字节/loopback模型正式CLI E2E、RF消费通过；不完整质量可读，无人工签收。新代码eae2dd4精确CI37521679387一次全绿/59秒，已关闭此缺口；不重复付费run10。

## N5-RAW-DUP接收边界

[MAIN集中验收](harness_lanes/n5_raw_duplicate_main_acceptance_2026-10-06.md)与[小收据](harness_lanes/results/n5_raw_duplicate_main_acceptance_2026-10-06.json)：51项/9.09秒，原件0删除、测试根恢复absent；逻辑候选上界7.27GiB，只有3组151MiB实际SHA复核，3528组未实读。历史Windows物理指标无效，不算释放；跨company_raw/Dropbox/Dayu的登记字节不是CWP目录磁盘占用。可选原件去重不阻核心完成、现不自动实施。
