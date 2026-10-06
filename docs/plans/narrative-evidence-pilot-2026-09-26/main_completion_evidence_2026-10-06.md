# MAIN当前完成证据与真实缺口

截至CWP代码`891dd414e1277823c029a5db77833917041723ec`、RF main/真实远端`6e6b817a1a6e4567293a4dcb835815f3be508a03`。这是阶段核对，**不是整体完成签收**，不增加人工门或小节点复核。以可重放行为、已发布代码和真实结果区分完成与未完成。

| 原目标/责任 | 已有权威证据 | 当前边界/下一动作 |
|---|---|---|
| 选择有价值业务叙述，格式化资料可跳过 | N4-T2已合入`0657579d`；selector0.3.1；[N4真实run05](harness_lanes/results/n4c_live_2026-10-05_run05.json)、[run06](harness_lanes/results/n4c_live_2026-10-05_run06.json)、[run07](harness_lanes/results/n4c_live_2026-10-05_run07.json)均有policy skip/0model | 年报、IR、英文电话会有真实模型final；招股尚无合法final。未证明所有文档类型的业务覆盖率；[N5-DOCSET](harness_lanes/n5_document_quality_benchmark.md)是独立质量实证，不改当前runtime、不能用selector输出自行生成golden |
| 同原语言摘要、精确引用与来源质量 | run05年报20claims/96locators；run06 IR13/11、英文电话会14/14，RF公开reference/read返回0、replay verified、translate=false；source/locator校验未放松 | metadata来自隔离fixture、原文字节为真实原件，不宣称生产来源元数据已补齐。旧招股SUMMARY_INVALID具体规则未知；新诊断仅固定rule、不保存未知provider字段 |
| 精选内容检索与精确读取 | [S5精选检索验收](harness_lanes/results/s5_selected_retrieval_acceptance_2026-10-05.json)，发布`1b0feb44`，102个不同case分次GREEN；真实微软TXT正式search/exact CLI、locator回放 | 该检索E2E模型为Replay；真实provider摘要与RF消费由run05/06另证，不能将两份证明混称一个模型检索全链。没有重新恢复全量legacy正文 |
| 多文档并发、失联恢复和持久预算 | N4 A/B已发布；本轮146相关Unit、14个CLI/cross-run/kill恢复case分两次全绿；[节点收据](harness_lanes/results/n4c_prompt_node_2026-10-06.json)、[精确CI](harness_lanes/results/n4c_prompt_ci_2026-10-06.json)37506642500 attempt1全部成功/83s | E6 P1/P2/P4真实字节+确定性模型实验已记录，不重复；paid run使用P4的compute并发3/model1，不能声称已测多provider同时外发或模型并发4。未知timeout照reserved计，预算不足外发前拒绝 |
| 跨项目解耦与来源虚拟化 | SourceRef/SourceExport v2；[FF正式合入](harness_lanes/results/p5_ff_main_acceptance_2026-10-05.json)main758e8f4；ET main63c4090；[RF默认v2正式合入](harness_lanes/results/p5_rf_main_acceptance_2026-10-06.json)main6e6b817a/精确CI绿；现有FF→ET→CWP离线CLI链 | RF读取的是自身已提交六模块导出的consumer，不修改owner树。Dayu零改；其不支持硬下载限额则请求前拒绝。FMP真实HTTP402是套餐能力边界，不能冒充电话会下载成功或强制增加付费provider |
| 降容、原件不丢、成功后清理临时材料 | [实际S5生产收据](harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)：7104旧文件/8191handle/1490530旧span退出，DB3055841280→222408704 B，净5659443210 B释放，17表digest与原件SHA保持 | 原件删除0，不将未测重复raw算已释放。新真实final的测得大小只是本样本结果；on-demand保存精选+一份final，不全库永久PDF→MD。所有paid试点根按要求清理，生产new final仍0。原件重复下一阶段只读[N5-RAW-DUP](harness_lanes/n5_raw_duplicate_audit.md)，不自动对象化/删原件 |
| 门禁/权限简化、日常测试不拖慢 | S0/G1与S6已发布；人工签收/TTL/旧whole-catalog入口退出；提交无pytest，推送精选12项、CI全Unit+同精选；本轮正常commit/push都GREEN | 保留字节SHA、来源身份/期间/公开日、引用回放、路径归属、lease/generation和资源预算自动校验。run07 document的legacy blocked_human标签不等于新增人工许可，真正停止原因为top-level budget_exhausted；不靠人工文件解锁 |

## 当前唯一真实模型缺口

P04招股：run05两次MODEL_TIMEOUT后SUMMARY_INVALID；run07只有一次61秒MODEL_TIMEOUT，无模型正文返回，下一attempt被MODEL_BUDGET_DENIED拦在POST前。不能说prompt精简修复了旧无效草案，也不能将超时算摘要通过。

累计159907tokens/68560microUSD，unknown7/unsettled0，原160000上限只剩93tokens；费用仍上限100000microUSD，历史FX预留2764后剩28676。新增200000tokens及同一P04精选片段向DeepSeek`https://api.deepseek.com`/`deepseek-flash`的一次原语言复测已经询问、尚待答复。没有答案不得提高cap、换资料目的地、清旧账或POST；不按Token Plan估计值冒充现金账单。

## 外线与交接

[N5总包](harness_lanes/n5_parallel_packages_2026-10-06.md)三卡可立即独立开工，写集不交叉，交付才验收/合入。现在未收到N5交付，不声称它们实现了质量基准、原件对象去重或ET本地收据。RF/IQS/StockWiki owner树不另写；总PWF与公共接口仍由MAIN维护。

下一个大节点仍是招股真实final→RF读取→引用/语言/预算/目录恢复，不重跑已绿长测，也不建立第二套任务库、人工合同或权限层。**整体目标保持active。**
