# W20-AUDIT-CHECKPOINTS 原包返工单 R1（2026-10-29）

> 已完成：本包最终修复/独审/并线结束，本文件为历史返工记录，勿重新实施；见[最新完成入口](../w20-reception-r3-20261029/README.md)。

> 本轮后续返工已交付并复验，部分问题已关闭；本文件为第一轮历史。请改用[第二轮当前入口](../w20-reception-r2-20261029/RETURN_AUDIT.md)，不重复实施已关闭任务。

这不是新施工卡。在原工区原分支续改，保留已有有效进展。ROOT结论RETURN_FOR_IMPROVEMENT，暂不并线/安装，主线循环仍暂停。

- 工作目录：`C:/Users/郑曾波/Projects/revenue-forecast-audit-w20-checkpoints`
- 分支：`codex/w20-audit-checkpoints-20261028`
- 本轮HEAD：`7ac295ffe9582533eb004ad10a8afc97f1bebc24`
- PLAN_ID：`w20-audit-checkpoints-2026-10-28`；PWF_PLAN_ROOT：`docs/plans`。
- 必读：[ROOT报告](audit-review.md)、[机器报告](audit-review.json)、原卡construction_card.md、[7条独立断言](evidence/audit/test_independent_expectations.py)、[真实RED](evidence/audit/independent-red.txt)。17个交接SHA均匹配，不是拒绝整个已完成框架。

## 两个共同责任点

1. **AUDIT-R1/P2：typed锚点观察。** 金额0.1元和10%被scale_equivalent；-5与+5被literal_match；2024H1和H2只因共享2024判full match；日元因bare元误认CNY。按显式类型/量纲/符号/完整期间判断能否比较，复用已有numeric checker的兼容约束，不只拿SCALES重写换算。未知币种/口径保持unknown或partial，不能把共享词片段提升为完整匹配。取消bare元推人民币，不要求无限币种新词典；保留合法12.5亿换算、同期间正例。只改原allowlist的共同观察owner及必要测试，不能按公司/页码/整句加例外。
2. **AUDIT-R2/P2：资料可观察性。** 明确reading_state=unread却保留文本时，四个锚点仍给literal_match。共同入口一次计算availability，standalone和既有packet使用同一结果。unread的支持锚点not_observed，metadata/context可以展示，缺观察不能靠文字非空推成read；不反复打开原件、不增加授权/人工门禁。

## 验收要点

现有26项和11步CLI全绿，但ROOT新增7断言5RED/2控制通过，证明现有绿测遗漏类型冲突及显式unread。把这些中性反例加入本卡测试，覆盖各个锚点和两个入口，修好后仅跑W20与受影响numeric/period兼容短包、一次离线CLI。机械标签准确不等于语义验真，继续保留四独审职责和unknown；现有生产claim字段缺声明的followup仍单列，不假称本卡已经完成真实数字审查。

## 收尾与交接

原卡隔离/allowlist/三大节点约定继续有效，不需要ROOT逐小步签收。先保存有效RED，再修共同owner；只跑相关短包和必要代表CLI，不新增收费/下载/生产资料修改，不为了全绿提高额度或重复全仓/完整矩阵。测试根记录sentinel并恢复初态。

完成后调用真正独立agent复审原卡与本轮返工项，范围内所有问题修复、OPEN为空。保留原独审和旧失败，新增本轮review与修复证据，在原delivery/handoff.md/json更新最终实现、受测/受审commit、对应SHA、实际命令结果、清理及局限。有既有remote正常commit/push原分支；无remote只提交本地并说明，不创建公开remote。不自行并主线或全局安装。然后STOP交ROOT，不等待其他两包，不向其他项目扩写。
