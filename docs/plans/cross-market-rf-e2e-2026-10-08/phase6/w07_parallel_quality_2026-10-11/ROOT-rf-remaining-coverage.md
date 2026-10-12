# W07-RF-MODEL：ROOT剩余组合覆盖（不是第二个引擎）

2026-10-11。已交付的16向量工具经ROOT共因修复后可用；整张施工卡仍为部分覆盖。本文属于ROOT接收后续，不要求作者重新签收、不增加日常CI全矩阵。主线W04→G2优先序保持；在G4/G5使用组合测试作为充分证据前完成这里的大节点。

## 写集和上下文

仓库：`C:/Users/郑曾波/Projects/revenue-forecast`。隔离ROOT工作树：`C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-rf-model-reception`。

只写现有`tools/model_generalization_matrix/**`、新增`tools/tests/**`的本包测试、自己handoff/PWF。原生scripts、原tests断言、config、安装、assurance/output只读。原16向量保持；扩展可用独立`COMBINATION_CASES`清单，避免修改原测试固定的16用例断言。入口合并运行两清单时，report的required manifest也必须消费同一个清单；不把缺类/未知/未执行算绿。

## A：先固定补充输入与独立期望

| 缺口 | 原生构造与要求 | 必须失败的反例 |
|---|---|---|
| M01 CNY/HKD | 读取`research.input_quantities.convert_input_quantity`已登记单位；分别固定人民币亿元、港币百万元、美元millions的同币种缩放。quantity×price金额与标签分开验证。使用已支持单位名，不自行假造别名/汇率 | 同币种量纲被错缩100/1000倍；跨币种自动改标签；缺币种不可声称金额等价 |
| M04 控制期与跨FY | 从W05 dated contribution已有helper构造真实控制日期、非12-31年结、覆盖区间跨日历年。明确确认收入来自哪个被引用period_flow；缺季度保留缺口；输入别名不能把同一流重复加一次 | 正确月数但错年收入；非控制期间收入被计入；缺Q被零补；全年+H1双计。必须比对实际模型年度结果及ancestry，不能只调用月份helper |
| M06 联合量价 | 用已登记量价原生模型及关联情景helper，冻结quantity/price同一shock的联合路径；比较baseline/stressed，手算quantity×price和一次压力传播 | 只变量不变价仍被称联合；两个环节重复施加shock；偷偷重排scenarios让数值通过 |
| M07 目标与净额 | 用management target已有helper补cumulative target；用recognition/forecast adjustment原生gross/net与cannibalization构造。期望由明确净额恒等式与输入期间推导 | 累计或期末目标冒充年度；gross/net混合；已计自身收入又全额加新增业务。若原生输入合同拒绝，记录实际合同原因；不能复制公式模拟支持 |
| M08 actual/WAPE | 用合法draft预测输入及原生历史误差接口，以未来年度缺actual为事实，检查实际draft输出对应actual/WAPE字段保持null/缺口语义；与经营校准支持scope独立 | future assumption被当actual；缺actual被0补；无误差样本却输出0 WAPE；一格校准被扩展到别的segment/year/scenario |

每行至少一个有意义合法向量和反例/未知向量。先读取已实现接口/原fixture，写CaseSpec与手算依据后才运行。真实接口不支持则报告NOT_SUPPORTED及最小复现，不改core。若暴露core缺陷，由ROOT另建有明确测试的修复阶段。

## B/C：两个大节点

1. B集中工具回归：保留原36项，加入“错误结果确实失败”测试、请求参数污染检查和新组合覆盖检查；不每个用例单独全仓回归。
2. C一次真实原生全清单＋合法/拒绝/support三个CLI。已有工具的异常分类、per-case请求/结果SHA、未知、readonly、清理与完整清单校验继续执行。由独立手算期待对实际结果验收，不从actual生成expected。output目录新建且不可覆盖旧证据；scratch原先absent或sentinel必须恢复。

## 接收接口

交`ROOT-reception.json/md`追加新attempt：implementation commit、required case IDs、每个缺口对应case/native entry/pointer/期望推导、集中回归、实际CLI退出与schema、cleanup、真实时间、压缩报告SHA/字节、remaining。未关闭缺口须继续PARTIAL。仅在所有已声明组合被实际运行且无遗漏时，母dispatch才可升级整卡ACCEPTED。工程通过不认证公司来源真值或买方预测质量。

原生报告只保留一份压缩JSON和小摘要；不要重复完整payload写进多个Git/PWF目录。不调用网络/LLM，本包费用为0。不增加安装、签收或权限门。
