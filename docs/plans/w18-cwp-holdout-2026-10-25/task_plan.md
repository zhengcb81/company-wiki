# W18-CWP-HOLDOUT 独立施工计划

## Next Step

已 COMPLETE 并交付：delivery/w18/handoff.md/json + review + 冻结基线收据；分支已推送 origin。ROOT 接收：对修复后候选 commit 用 tools.holdout_replay 重跑对照冻结基线，处理产品 finding F1-F4。

## 目标

完成construction_card.md所有适用需求，关键行为真实执行，独立agent全面审查并修复全部本范围问题，测试恢复后交接。不能把工程组件通过说成主线公司内容验收通过。

## 大节点

- [x] A 完成：8原件/5公司/CN+HK+US全类型样本、96目标/113锚点全部独立重提取验证、manifest+gold先于任何候选输出冻结提交。
- [x] B 完成：tools/holdout_replay薄编排（manifest/producer/resolve/worker/runner/CLI）+19项中性边界测试全绿（65cbd9c2）。
- [x] C 完成：真实ba8f8543冻结baseline双attempt回放8/8 ok、双根+污染PYTHONPATH可移位收据、逐目标finding（F1-F4）。独立审查进行中。
- [x] 交付完成：独立审查四轮闭环（R1三agent/R2双PASS/R3双PASS），全部 finding 修复确认；handoff/review/收据齐全；faa488a7+28f06a9a。

每阶段变更更新本文件、findings/progress和唯一Next Step。外部阻塞具体记录，不重复盲跑失败，不加小节点审批。
