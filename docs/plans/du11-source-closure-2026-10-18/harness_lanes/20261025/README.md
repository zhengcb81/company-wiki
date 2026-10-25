# 2026-10-25 三张独立施工卡

状态：DISPATCHED_AWAITING_AUTHOR_HANDOFF。用户已确认三卡发出，ROOT保持作者工区只读并继续自己的主线。本批是新任务，不重开已接收的W13/W14/W15或IR/QA/MC卡。用户将三卡分别交给三个harness；ROOT不代替作者启动产品实施。

| 卡 | 负责的仓库 | 独占工作目录 | 固定代码基线 |
|---|---|---|---|
| [W16-RF-BASIS](W16-RF-BASIS.md) | revenue-forecast：历史收入与基数的可比口径 | C:/Users/郑曾波/Projects/revenue-forecast-w16-basis | 094d55ad884e4a886b1537c0e76f3a0bede16ca2 |
| [W17-AUDIT-COVERAGE](W17-AUDIT-COVERAGE.md) | revenue-forecast-audit：覆盖维度的报告型观察 | C:/Users/郑曾波/Projects/revenue-forecast-audit-w17-coverage | bb41d9beda94fead3aba4bc65ed8c6dce4314e97 |
| [W18-CWP-HOLDOUT](W18-CWP-HOLDOUT.md) | company-wiki：新真实材料的源侧金标与隔离回放工具；不改生产源码 | C:/Users/郑曾波/Projects/company-wiki-w18-holdout | ba8f8543c0351f6857e1ce24e943ad9da1b664ef |

基线完整SHA已由Git实读；三卡开工以各自工区START_HERE.md、施工卡和COMMON.md为准。

三个工作目录分别是独立Git工作树，不在原主工区切分支。RF主工区三份assurance运行WIP、CWP主工区pre-push mode变化及历史未跟踪产物均保留。Audit无remote，不猜公开地址。工区创建/文档seed的实际状态见dispatch.json。

## 可并行原因与ROOT责任

- W16仅写RF，使用冻结的现有输入/数量/来源契约；不等W17/W18，不调用金融API、不改CWP表格解析。
- W17仅写Audit，读取冻结的现有公开产物与审查报告；不依赖W16新增字段、不修改RF/CWP，不把诊断变成运行许可。
- W18仅写新测试工具、样本清单和自己的PWF，针对冻结CWP版本回放；不导入ROOT正在变化的工作区，不改生产选择器或摘要代码，不依赖W16/W17。
- ROOT继续CWP的ST-A02来源路线、annual14其余partial、正式摘要和缓存/RF真实采用验收。分包期间ROOT冻结W16/W17允许的生产路径；W18新目录归作者独占。只读冻结RF代码不受影响。
- ROOT接收后分别集成W16和W17，再把W18冻结样本用于候选版本泛化检查。组件通过不能关闭annual14的8通过/6部分，不能代签W12四审或公司循环。

## 共同交接

每卡A调查/源侧预期，B实施，C集中测试及独立agent完整审查。不为A/B增加人工签收。必须先修完独审发现的全部本范围问题，再复测、复审并交接。审查者不得只读作者总结，必须读本卡、完整diff和实际测试证据，独立执行关键行为并新增反例。详见[COMMON.md](COMMON.md)。

最终接口固定为各自`delivery/w16|w17|w18/handoff.md/json`，使用[handoff.template.json](handoff.template.json)。ROOT统一接收、并线和安装；作者只推自己的codex支线。没有remote如实报告，不能因此虚构CI或把本地结果说成远端通过。

空间约束：不复制原始资料库，不提交API响应全集或完整PDF/MD；新持久交付证据默认每卡不超过10MiB、测试fixture不超过2MiB。超出时先压缩重复日志、仅留必要失败/最终证据，仍需超出则说明精确字节和不可替代理由，交由ROOT集成时处理，不能偷偷新增大目录。测试临时数据与最终证据分开，临时目录前后恢复。
