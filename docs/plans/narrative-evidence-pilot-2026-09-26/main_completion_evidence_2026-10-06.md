# MAIN当前完成证据与真实缺口

截至CWP已发布代码`4d019b5435b8b277c059f6d4abbe62cc09f684f3`（短摘要目标CI37511515796一次全绿/76秒；英文选择CI37510236806一次全绿/72秒）、RF main/真实远端`6e6b817a1a6e4567293a4dcb835815f3be508a03`。这是阶段核对，**不是整体完成签收**，不增加人工门或小节点复核。

| 原目标/责任 | 已有权威证据 | 当前边界/下一动作 |
|---|---|---|
| 选择有价值业务叙述，格式化资料可跳过 | N4-T2已合入`0657579d`；[N4真实run05](harness_lanes/results/n4c_live_2026-10-05_run05.json)、[run06](harness_lanes/results/n4c_live_2026-10-05_run06.json)、[run08](harness_lanes/results/n4c_live_2026-10-05_run08.json)均有policy skip/0model；selector0.3.2修复已完成相关TDD与真实原文测量 | 四类资料均有真实provider final，但旧电话会业务遗漏需真实修复复测。未证明所有类型全覆盖；[N5-DOCSET](harness_lanes/n5_document_quality_benchmark.md)独立质量实证，不以selector输出自行生成golden |
| 同原语言摘要、精确引用与来源质量 | run05年报20claims/96locators；run06 IR13/11、英文电话会14/14；run08招股25/160、238766 B final，RF公开reference/read0、replay verified、translate=false；source/locator校验未放松 | metadata来自隔离fixture、原文字节为真实原件，不宣称生产来源元数据已补齐。旧招股SUMMARY_INVALID规则未知；DeepSeek实际通过不证明MiMo旧响应问题已解决。电话会旧摘要14条中9条问题，合法引用与业务效果须分别验证 |
| 精选内容检索与精确读取 | [S5精选检索验收](harness_lanes/results/s5_selected_retrieval_acceptance_2026-10-05.json)，发布`1b0feb44`，102个不同case分次GREEN；真实微软TXT正式search/exact CLI、locator回放 | 该检索E2E模型为Replay；真实provider摘要与RF消费由run05/06另证，不能将两份证明混称一个模型检索全链。没有重新恢复全量legacy正文 |
| 多文档并发、失联恢复和持久预算 | N4 A/B已发布；本轮146相关Unit、14个CLI/cross-run/kill恢复case分两次全绿；[节点收据](harness_lanes/results/n4c_prompt_node_2026-10-06.json)、[精确CI](harness_lanes/results/n4c_prompt_ci_2026-10-06.json)37506642500 attempt1全部成功/83s | E6 P1/P2/P4真实字节+确定性模型实验已记录，不重复；paid run使用P4的compute并发3/model1，不能声称已测多provider同时外发或模型并发4。未知timeout照reserved计，预算不足外发前拒绝 |
| 跨项目解耦与来源虚拟化 | SourceRef/SourceExport v2；[FF正式合入](harness_lanes/results/p5_ff_main_acceptance_2026-10-05.json)main758e8f4；ET main63c4090；[RF默认v2正式合入](harness_lanes/results/p5_rf_main_acceptance_2026-10-06.json)main6e6b817a/精确CI绿；现有FF→ET→CWP离线CLI链 | RF读取的是自身已提交六模块导出的consumer，不修改owner树。Dayu零改；其不支持硬下载限额则请求前拒绝。FMP真实HTTP402是套餐能力边界，不能冒充电话会下载成功或强制增加付费provider |
| 降容、原件不丢、成功后清理临时材料 | [实际S5生产收据](harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)：7104旧文件/8191handle/1490530旧span退出，DB3055841280→222408704 B，净5659443210 B释放，17表digest与原件SHA保持 | 原件删除0，不将未测重复raw算已释放。新真实final的测得大小只是本样本结果；on-demand保存精选+一份final，不全库永久PDF→MD。所有paid试点根按要求清理，生产new final仍0。原件重复下一阶段只读[N5-RAW-DUP](harness_lanes/n5_raw_duplicate_audit.md)，不自动对象化/删原件 |
| 门禁/权限简化、日常测试不拖慢 | S0/G1与S6已发布；人工签收/TTL/旧whole-catalog入口退出；提交无pytest，推送精选12项、CI全Unit+同精选；本轮正常commit/push都GREEN | 保留字节SHA、来源身份/期间/公开日、引用回放、路径归属、lease/generation和资源预算自动校验。run07 document的legacy blocked_human标签不等于新增人工许可，真正停止原因为top-level budget_exhausted；不靠人工文件解锁 |

## 当前真实业务效果缺口

P04已由run08 DeepSeek一次请求完成。MiMo run05两次MODEL_TIMEOUT后SUMMARY_INVALID、run07一次61秒MODEL_TIMEOUT无正文仍为真实历史；不将超时计成功、不推断旧失败规则。run08的25条招股业务摘要已实际返回并由RF核验。

旧T01电话会真实摘要遗漏新数据中心、GPU交付效率、模型发布、客户采用、付费席位和商业模式变化。MAIN已先写跨行业经营正例/财务套话反例TDD，再实现selector0.3.2通用规则，parser0.1.0与locator不变；92个不同责任case分步GREEN。原文六类管理层进展全部选中，46/46引用回放，[零外发测量](harness_lanes/results/n4c_english_selection_2026-10-06.json)给出旧/新数量及按Config的请求预留。此证据证明选择修复，还未证明新模型摘要覆盖。

run09已按已批准预算做过一次修复后T01复测：供应商finish_reason=length，input2305/output8192、MODEL_OUTPUT_TRUNCATED，系统拒绝发布半截摘要。失败不是人工许可，未知费也不是零。保护检查与隔离根清理全部通过，policy仍零模型。当前累计180884tokens/90649microUSD、unknown7/unsettled0；余19116tokens，扣FX2764后6587microUSD。结果见[run09](harness_lanes/results/n4c_live_2026-10-05_run09.json)。

当前提示词没有输出长度目标，增加证据后机械逐条输出存在膨胀风险；官方[模型说明](https://api-docs.deepseek.com/quick_start/pricing/)称Flash默认thinking。本次没有reasoning/content分项，不断言截断来自哪部分。已按TDD实现私有prompt1.5最多20条/280字符/8个alias，并优先管理层具体更新、去重；160段正文/角色/全部原文定位不减，公共reader/既有草案不加此硬门。2 RED→59相关Unit与2正式双语言CLI E2E GREEN，Ruff/mypy绿；不改Config、max_tokens、thinking、stream或超时。

兼容性直接验证：新增integration case建立独立原文/catalog，用25个管理层段落及每条超过280字符的模拟旧prompt1.4草案，经真实artifact prepare/activate和当前public transport读取，stdout bytes保持原样、全部locator replay verified、原件不变；1 passed/3.09s。首轮夹具把多句当完整span而StopIteration，改为单句原文，不改产品解析或校验。[小收据](harness_lanes/results/n4c_legacy_summary_read_2026-10-06.json)明确这是合成兼容测试，不是新真实模型验收。

[新真实请求测量](harness_lanes/results/n4c_short_summary_request_2026-10-06.json)零POST，body10435 B，预留18755tokens/14445microUSD；token足够、费用不足。已提出累计费用$0.12，当前尚待用户答复；未答不得外发，不使用临时off-peak折价绕过预算、不退旧未知账。费用代理仍不冒充供应商现金账单。

## 外线与交接

[N5总包](harness_lanes/n5_parallel_packages_2026-10-06.md)三卡可立即独立开工，写集不交叉，交付才验收/合入。现在未收到N5交付，不声称它们实现了质量基准、原件对象去重或ET本地收据。RF/IQS/StockWiki owner树不另写；总PWF与公共接口仍由MAIN维护。

短摘要代码发布/精确CI已完成；下一个大节点是费用获答后一次T01真实final→RF读取→业务内容/角色/全部引用/语言/预算/目录恢复，随后核对N4C。不重跑已绿长测，不建立第二任务库或人工门。**整体目标保持active。**
