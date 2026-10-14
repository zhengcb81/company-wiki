# DU3-QUALITY：跨市场真实文档质量基准与独立泛化

## 直接启动

工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/quality`。
分支：`codex/du3-quality-20261014`。先读本卡与同级`../INTERFACES.md`，再读工作树`.planning/du3-quality/task_plan.md`的实际base。只在这个worktree施工，现在即可开始，不等另外两卡或ROOT。

本卡背景完整：CWP负责资料/原件/解析/来源型摘要，不做研究结论。共享DU模块已并master：24文档规格、14业务策略、实际章节范围与闭包；1135工程PASS/四PDF658span回放；正式新生产摘要未接线。ROOT正在实现生产选择/预算，本卡只能改善既有benchmark，不自行修生产selector或编造模型运行。

## 排他写范围

- `tools/document_understanding_benchmark/**`（已有唯一基准，继续扩展）；
- `.planning/du3-quality/**`：本卡PWF/小收据/本机bindings，不提交bindings；
- 不改任何src、根tests、gold交付包`review/deliverables`、ROOT总PWF/共享接口、安装技能、依赖/hook/CI、生产配置或其他工作树。原件只读。

## 任务与接口

1. 沿既有evaluate/oracle/native observer，补最终材料观测`observe_final_material`与同条件比较`compare_runs`；签名及wire完全按DU3/1。既有evaluate兼容，不建立第二评估器。
2. observer消费实际最终ModelRequest唯一evidence行/组alias及originals绑定，确认真实正文/原locator/角色；不能用gold或生成claim给observer补答案。缺正式产物可先用显式synthetic同形fixture，实物baseline使用已存在公开normalize/DU路径，未接生产如实记录。
3. 加全链风险检查：丢否定/阶段/期间/单位、币种和量级错、问题/编辑文字当管理层事实、跨主体/父源合包、共享正文重复、坏alias、未读当no_value、缩分母/预算变大假改善。
4. 建文档覆盖矩阵：A/H/US年/半/季、10-K/Q/20-F、IPO/S-1/F-1、增发/可转债/募资、IR、电话会、业绩发布/演示稿、8-K/6-K附件/修订、低业务/行政。真实/合成/缺样分别列，不能用schema通过认证语义。
5. 维护已看样本污染清单：原20份、旧六holdout及先前调过的原件都作回归。选择**新A/H/US各一家公司**的现有本地原件做真正新gold；先冻结业务事实支持集，再看选中新输出。每公司可选2种文档，原文摘录每文档≤8KiB。不需要ROOT或另两包新函数才能完成oracle、gold及当前基线。
6. gold组内AND/组间OR，重要性以原文和业务价值为准；微软旧关键业务4/8 FAIL保留，不降低critical或删失败换绿。财务API可替代的一般财务数值不应强制摘要，但经营量/表头/单位/风险限定不能随意降级。
7. native工具复用现有SourceRef/只读bindings/normalization，不自写PDF/HTML parser；真实无模型不认证摘要蕴含。为ROOT G2准备独立语义审查输入和小报告，不自己调用付费LLM/下载provider。

## A/B/C（只有三个大节点）

**A：TDD。** 在包内新增test_final_material/test_paired_comparison/test_fresh_split，先RED以上风险反例，保留旧测试/旧gold及baseline；不修改src来帮oracle通过。

**B：实现与工程节点。** 包原测试＋新增测试，一次集中运行；别名/闭包/支持集/来源角色有效，恶意变异不得假PASS；同源同范围同预算分母冻结，变化明确INCOMPARABLE。不读未知目录、不改输入、不写穿生产配置，输出/临时目录自身恢复。

**C：真实基线与交接。** 用指定只读原件跑既有公共入口，至少新A/H/US三公司真实gold/引文回开；缺确实可用新源则标UNAVAILABLE及具体缺口，不能拿旧样本伪新。记录旧/候选实际结果，不以未接线候选证明生产完成。C没有真实模型时语义保持NOT_EVALUATED，ROOT后续共用G2/G4/G5窗口。

资源：不复制原件/全文DOM/全篇MD；保存小汇总与失败证据。真实原件SHA/mtime/size、生产配置和预存sentinel不变；tmp成功/失败都清理。测实际读取范围、候选/选中、字符/bytes/耗时/产物体积，未测RSS/模型usage明确未测。不扩日常CI为真实网络/长性能套件。

## 交付与停止条件

按共享接口写handoff.json/md，实际代码commit SHA、测试命令/exit/耗时、真实/合成样本分母、污染清单、资源/恢复及ROOT所需接线列全。正常提交本分支即可，不并master或改默认。

达到本包A/B/C后STOP等ROOT接收。不能因ROOT新selector未落地而暂停本包能独立完成的工作；冻结fixture即可验证接口。ROOT负责把实际正式模型产物接到observer、集中跨仓验证、并线和主线推送。
