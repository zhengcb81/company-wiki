# untyped numeric quality：独立复审 v2

## 结论

**有限检测/传播修复通过，预算拒绝的归因仍需修复，节点暂不整体签为 PASS。** 本审查不覆盖项目正文、完整年报选材或正式摘要。

现有正式测试15项、新增永久反控7项、独立公共输出probe11项合计 **33 PASS / 0 FAIL，pytest5.75s**。新旧来源绑定、quality section、has_unbound_numeric_cells函数及完整文件SHA均记录在execution-v2.json，运行前后完全相等。ROOT之后若改项目/qualification section，不能把这里的旧全文件SHA当新版审查；质量section hash可以独立说明未改的有限节点。

## UQ-01 已修并复验

v1对精确native range中的完整英文/中文句子误标：数字单独换行后，虽然之间有完整“customers last year and now has”“台设备，新增产线年产能达到”接续，两个裸数仍被当作数值格。

ROOT将形状判定收敛到连续source value-cell run，复用既有_is_value_cell。真实连续值、dash缺失格、尾部变化说明、百分比/货币格式/窄空格/脚注符号均保留未知归属；没有对native carrier统一豁免，没有数字转换，没有补币种/单位/期间，没有公司特判。原2条失败断言和其余正反控当前全绿。

永久新测试文件为test_reading_untyped_numeric_prose_controls.py。首次运行时ROOT修复已落盘，故reverse-red.txt实际7PASS，绝不能以文件名冒称这个文件跑过RED；真实同断言RED在review-v1.txt/xml为2FAIL/24PASS。正式旧15项断言不变。

## UQ-02 预算拒绝错误归因：OPEN

实际公共复现budget-risk.json：纯文本“Business review”和“The company delivered industrial equipment to customers for qualification.”完整运行均无flag；仅将同一WorkBudget置于quality预扣4833 +358 -1=5190，扫描未执行，标题和纯正文均被写table_structure_ambiguous，status虽partial但selection_diagnostics空。缺少检查不等于发现表格形状。

建议复用现有work_budget_exhausted延期结果最简单。若保留已完成bound表，应通过既有闭包重算其完整引用组，不能仅filter spans破坏依赖；保留未检正文也必须明确parser_warning/资源未检、禁止未检数字解释，而不能断言真实table ambiguity。无需新许可、schema、任务库或单位推断。本次只报告风险，没有改生产。

## 已验证边界

- 模块__file__在pytest内确认属于隔离worktree；原source ID、text、locator和元数据未变。
- ambiguity进入真实citation view和model fragment quality；其解释限制随constraints传播。
- 完全绑定native table正控无新ambiguity；同页另一parent的纯正文不污染，引用组不能跨source。
- 修改内存中table_shapes源码byte指纹（不改磁盘）会改变实际public decision dependencies；恢复后原指纹完全恢复，选中文本未变。
- 不超16M/96/48k；不靠提高预算换绿。
- 0真实原件读取/下载/副本、0模型/网络；无生产或Git写入。cleanup-v2.json再验所有实际重定位basetemp和请求目录均不存在。
