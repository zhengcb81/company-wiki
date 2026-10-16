# DU8-RF-COMPARISON — 目标比较与报告校验的单一计算责任

## 开工信息

- 工作目录：`C:/Users/郑曾波/Projects/revenue-forecast-du8-comparison`
- 自有计划：`docs/plans/du8-comparison-2026-10-16/task_plan.md`
- 分支：`codex/du8-rf-comparison-20261016`；源码基线`0feea9b097747165a37009ad4a7ed5616cf46c38`，随后仅ROOT启动PWF种子。
- 先读本卡、INTERFACES.md、自己的三份PWF及仓AGENTS。可现在独立开工，不等待CWP、ET、FF或另外两包。

## 1. 立项依据与目标

DU6目标计量已接收，不重做其signed/quarterly/原生金额单位功能。真实已读代码仍有责任分化：`scripts/revenue_report.py`约953行typed分支委托compare_target_measurement，约960–1050行legacy分支独立重算路径、ratio和meets_target；`research/targets.py`也产生legacy比较；`target_measurement.py`持typed比较。旧approximately的legacy绝对容差max(1,abs(v))*t与typed max(abs(v),1e-12)*t不同，DU6交接已明确无法在其白名单内收敛report。

本卡将比较计算和报告重放的共同语义放回唯一owner，防止作者输出与report验证随未来修改分叉。**统一责任，不擅自统一有意不同的历史数值语义。** 若发现实际结果bug，先独立RED、给出数学/原合同依据；保持所有现正确gold/old wire。报告验证还必须能抓伪造结果，不能因为双方调同一函数就取消独立手工锚点/篡改测试。

## 2. 精确写范围

- `scripts/research/targets.py`：比较生成相关函数；管理沟通coverage和来源资格保持。
- `scripts/research/target_measurement.py`：统一比较薄端口/兼容委托，typed核心数值语义保持。
- 新可选` scripts/research/target_comparison.py`（实际路径无开头空格）：若需要独立纯owner，仅此一个，不再建影子计算器。
- `scripts/revenue_report.py`：仅management target comparison校验段委派/错误定位，不改其他财务/预测/quarterly/reconciliation逻辑。
- 新`tests/test_du8_target_comparison_owner.py`、`tests/test_du8_target_report_roundtrip.py`、`tests/fixtures/du8_comparison/`、自有PWF；必要`references/management-targets.md`与`references/money-unit-conversion.md`局部文档。

其他scripts/contracts、builder、forecast引擎、CLI入口、旧测试/gold、config、assurance/output/registry、CI、安装副本全部只读。ROOT原alert WIP不在工区。确需白名单外改动先提交反例，不阻碍独立部分。

## 3. 冻结接口与兼容

优先在现`add_management_target_analysis`/`compare_target_measurement`同owner提供可复用的单目标scenario比较，再让report只调用并检查字段。新内部签名由A依据真实结构冻结，写进handoff；不发明第二输入schema，不复制全forecast到第二registry。原typed `management-target-comparison/1`和legacy各scenario键集、unmodeled缺省、quarterly真实桥、数值乘除次序、strict运算、raw/statement值、FX证据责任保持。

报告可以做形状与独立输入绑定检查，不能重复一份目标计算公式。legacy/typed差异作为同owner的明确兼容路径，不能靠猜输入大小选分支。缺货币/单位/期间不补，增长与营收金额分开，unmodeled/out-of-horizon不伪造comparison_value；明确typed范围operator限制保持。0.8/旧schema默认语义不动。

## 4. TDD/集中测试

A冻结旧分支行为和独立手算期望，至少覆盖：正/零/负、极小值、点/区间、approximately两口径边界、严格大/小边界、默认及显式unmodeled、独立benchmark、annual/cumulative/quarterly、company/segment与ownership含义、CNY/RMB别名/同币万亿缩放、无FX不跨币。

B：源生成→report校验同一个实际model；篡改modeled_value、target_value、attainment、meets_target、measurement_periods每项必须拒绝；不得只比较两个同函数结果称独立。至少5个关键值用不导入生产模块的Decimal/手工算式锚定，浮点旧边界按原乘除顺序冻结，不刷新gold。先盘点仓内实际存在的DU5/DU6、typed targets、report/季度/范围相关测试，集中跑一次；日常只新快测。

C：复用现RF真实forecast/report CLI，至少3个合成完整model（annual、quarterly、growth），输出再validate/render；篡改拒绝与未建模保真。全程隔离registry/输出，正常/失败均恢复sentinel；不跑真实公司、不付费。scope输出要明示合成，不宣称买方模型质量通过。

## 5. 交付与ROOT接口

作者只交本仓代码/PWF/测试；ROOT可在CWP新原文摘要交付后继续调用相同RF公开接口，不需要本卡等待来源升级。handoff列出删掉的重复计算分支、保留的兼容差异、共享owner的签名、5个手算锚点和反篡改证据、所有不跑范围。完成commit后STOP，由ROOT独立验收/并线/同步技能。
