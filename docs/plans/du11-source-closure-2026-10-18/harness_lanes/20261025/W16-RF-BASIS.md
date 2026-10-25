# W16-RF-BASIS：历史收入、预测基数与持续经营可比口径

可以立即开工，不等ROOT或其他两卡。独占目录`C:/Users/郑曾波/Projects/revenue-forecast-w16-basis`；分支`codex/w16-rf-basis-20261025`；固定代码基线`094d55ad884e4a886b1537c0e76f3a0bede16ca2`。`PLAN_ID=w16-rf-basis-2026-10-25`，`PWF_PLAN_ROOT=docs/plans`。先读工区`docs/plans/w16-rf-basis-2026-10-25/START_HERE.md`、本卡和COMMON.md。

## 为什么要做

ROOT的annual14 ST-A02暴露出财务精确值与叙述摘要应分工。年报原表有终止经营业务，持续/终止、原披露/重述会影响历史基数与增长率；从不完整文字块猜金额不能补这个缺口。本卡不是修CWP表格或去下载数据，而是使RF能够在**显式收到有来源的结构化值时**保留这些口径，并在实际历史/基数/派生比较路径中使用它们。

只读调查发现：`scripts/contracts/document.py::validate_historical_revenue`现有year/value/source_ids等校验；`scripts/research/input_quantities.py`已提供DU5/DU6唯一Currency×Scale规则。DU5已合主线，USD/RMB(CNY)/HKD及亿/十亿转换不是待重做任务。持续/终止和重述在当前历史观测上未见对应处理；先以现有源码/测试核实，明确真正缺口再TDD。

## 允许写入与保留范围

允许所属RF责任层：`scripts/research/**`中与历史观测/收入口径有关的模块及新`revenue_basis.py`；`scripts/contracts/document.py`、`scripts/forecast/calc.py`、`scripts/revenue_report.py`、必要的`schema_fields.py`/已有输入构造入口；对应新`tests/test_w16_*.py`和直接受影响的既有历史/数量/报告测试；必要输入说明和本地PWF、`delivery/w16/**`。变更路径/理由逐项交接，不顺手改其他研究模块。

禁止改CWP/FF/Audit/Dayu/IQS、模型配置/凭证/费用账、CI/hooks、assurance运行WIP、output、source_preparation与company_wiki_source。禁止重做DU5注册表或引入全套新身份/审批机制；不安装技能。本卡0金融API/模型请求、0下载。

## 固定行为与接口

| ID | 要求与验收 |
|---|---|
| B01 | 先用现有真实入口说明哪些历史/基数比较缺口可复现；覆盖reported total、continuing、discontinued、as-reported/restated。若已有能力满足，则补实际采用证据，不另建同义实现 |
| B02 | 在既有历史观测/来源/数量结构上设计最小**可选**口径元数据。优先复用已有source/claim、period/source clock及quantity转换，记录原始数值/单位和标准化值，不新增第二金融数据库。缺可选元数据的旧输入继续旧兼容，同时不把未声明口径说成已经核实 |
| B03 | 同单位不等于同口径：持续/终止/合计、原表/重述、业务边界与期间必须分别处理。明确冲突不能静默混算成“可比增长”。保留观测值并标出不能比较的理由；确实依赖无效比较的模型给清晰数据错误，其他不依赖部分可继续。不要为unknown新增人工审查门 |
| B04 | 总额=持续+终止只有同期间、币种、单位、边界及明确关系证据才可复算。原表和重述不是凭字段名自动转换；重述桥/可比披露不存在时不能自造前期调整。复算使用既有数值责任层和适当Decimal/容差，不复制DU5货币表 |
| B05 | 必须接到现有公开RF输入验证/预测/报告链，不能只有独立lint脚本。结果说明实际采用哪个观测作为base或历史比较，以及转换/口径状态；来源引用沿用现有source_id/claim，不能以“helper通过”声称RF采用 |
| B06 | 用合成但有效的完整RF输入走公开CLI：同口径正常、持续经营替代总额、同比/环比或年累计混淆、as-reported/restated无桥、明确有桥、币种尺度转换、零/负比较基数、缺元数据legacy。分别断言结果/诊断或具体错误；不只断言退出码 |
| B07 | 至少两份不同公司/市场的既有公开原文小段或结构化来源作为只读语义校对（可用ROOT年报p235但不能只此一家）；记录准确locator/单位/期间。不得把截断片段/作者手写值当API实收或来源真值。此项是输入语义校对，不宣称新公司RF全流程通过 |
| B08 | 单一共享口径owner，删除本变更新引出的重复判断；无公司名/页码特判，不因未知字段添加全局旧输入阻断；已有数值和golden兼容测试保持通过 |

新字段设计在A写入自己的接口说明与正反例即可，不需等待ROOT再签字。ROOT用该设计接真实结构化数据；作者不改原表和原有SourceRef。

## A/B/C和测试

A读DU5/DU6与当前历史路径，冻结B01–B08和失败输入；B按责任层TDD、接入实际输出；C集中跑新测试、既有数量/历史相关回归、CLI E2E与仓内日常gate一次，然后独立agent完整审查并修完所有问题。审查者须独立构造另一组重述/币种/期间错配反例。

建议定向命令（新增文件按本卡命名）：

```powershell
python -m pytest -q tests/test_w16_revenue_basis.py tests/test_w16_revenue_basis_cli.py tests/test_input_quantity_conversion.py tests/test_du5_root_unit_boundaries.py
python tools/pre_push_gate.py
```

若现仓测试入口有明确要求，遵循实际入口并记录；不得把没安装pytest或缺文件写成测试PASS。直接CLI需用实际`revenue_forecast.py --help`确认参数，在两个独占临时目录执行；其中一个含中文/空格，记录输入、源码根和输出。失败后恢复测试根，原始来源SHA不变。

## 交接

`delivery/w16/handoff.md/json`、`review.md/json`；逐B01–B08对照，附schema可选变化、legacy兼容、实际CLI采用字段、原始/标准化口径、不能比较的行为、全部独审finding修复/复审及最终文件SHA。状态仅在独审无未解决问题且测试/恢复通过后COMPLETE。作者只推自己codex分支；ROOT负责并主线及定点安装。真实ST-A02金融来源和RF公司质量仍由ROOT验收，不因本卡组件通过而自动关闭。
