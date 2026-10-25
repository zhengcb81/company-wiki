# W18-CWP-HOLDOUT 独立施工计划

## Next Step

A：核对冻结版本和写范围，读取construction_card.md全部需求，复用既有owner与测试，冻结实际缺口、输入与正反例。随后直接进入B/C；不等ROOT额外签收。

## 目标

完成construction_card.md所有适用需求，关键行为真实执行，独立agent全面审查并修复全部本范围问题，测试恢复后交接。不能把工程组件通过说成主线公司内容验收通过。

## 大节点

- [ ] A 真实边界/既有PWF与代码调查；先冻结独立预期和接口。
- [ ] B 根因TDD、共享owner实现或薄编排；兼容与实际入口接线。
- [ ] C 集中相关单元/集成/CLI端到端，独立agent完整审查，全部修复/复测/复审。
- [ ] 提交代码与独立审查证据，handoff.md/json、恢复/空间收据齐全。

每阶段变更更新本文件、findings/progress和唯一Next Step。外部阻塞具体记录，不重复盲跑失败，不加小节点审批。
