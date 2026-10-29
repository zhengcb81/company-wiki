# W20-FF-REPLAY 原包返工单 R1（2026-10-29）

> 已完成：本包最终修复/独审/并线结束，本文件为历史返工记录，勿重新实施；见[最新完成入口](../w20-reception-r3-20261029/README.md)。

> 本轮后续返工已交付并复验，部分问题已关闭；本文件为第一轮历史。请改用[第二轮当前入口](../w20-reception-r2-20261029/RETURN_FF.md)，不重复实施已关闭任务。

这不是新施工卡。在原工区原分支续改，不重开A调查、不回退进度。ROOT结论CHANGES_REQUESTED，尚未并线；主线循环仍暂停。

- 工作目录：`C:/Users/郑曾波/Projects/filing-fetch-w20-replay`
- 分支：`codex/w20-ff-replay-20261028`
- 本轮HEAD：`e81953dd8d122381265b7ba46c35117c3395cf1b`
- PLAN_ID：`w20-ff-replay-2026-10-28`；PWF_PLAN_ROOT：`docs/plans`。
- 必读：[ROOT报告](ff-review.md)、[机器报告](ff-review.json)、[最小复现说明](evidence/ff/README.md)、原卡construction_card.md。

## 修复范围

1. **FF-R1/P2：durable后故障不得由未durable分支代签。** 留存4份kill_after_import PASS均为not_durable，恢复首次GET1。保留历史报告及实际含义，纠正R3已完成声明。在既有测试边界做独立、确定性的durable后丢回执/返回中断：杀树前本请求来源可经CWP公开接口实读，恢复首次0额外GET，Ref/SHA相同，再次复用也0GET。未durable路径单列，不能任选一个分支即签durable后通过；可增加明确phase覆盖字段。原卡要求的两阶段都要证明，但不承诺并发exactly-once。
2. **FF-R2/P2：故障触发绑定本请求。** 当前任意旧sidecar即可触发kill_when。使用本case实际身份期次/Ref和实际新增持久状态；旧的其他期次、前序case sidecar不得误触发。复用既有公开owner接口，不在FF复制存储实现。加旧sidecar控制反例，以及本case单独/前序case后两种有限运行的阶段一致性。
3. **FF-R3/P3：如实更正机器交接。** 一份run-receipts SHA落后；全仓1462P13F被填exit_code0。若真实退出码不能找回可填null并解释，不编0；保留13项基线失败及归因，不要求顺带修复或重跑404秒全仓。受审实现13份SHA均匹配，不是源码未审。

## 复验边界

当前ROOT定向183项/6.78秒通过；最小反例只证明现有断言及触发器错误，不假称新的真实E2E。修复后先回归断言，再仅执行新durable后故障、原before_durable和隔离对照的代表真链场景。原41权威全集不改、selected/supplemental如实标注，30秒/case、180秒批次、workers≤2沿原配置，不再整批反复跑。

冻结依赖沿原卡CWP618df929、ET2584b7ee完整manifest，只读构建最小代码视图，不跟ROOT可变HEAD，不跨仓改CWP/ET/Dayu。如果真实durable测试确需跨仓新接缝，给ROOT最小counterexample和接口要求并明确NOT_PROVEN，不能偷改依赖源码或把控制流mock当真链。新场景仍需实际进程/HTTP次数/来源实读/清理收据。

## 收尾与交接

原卡隔离/allowlist/三大节点约定继续有效，不需要ROOT逐小步签收。先保存有效RED，再修共同owner；只跑相关短包和必要代表CLI，不新增收费/下载/生产资料修改，不为了全绿提高额度或重复全仓/完整矩阵。测试根记录sentinel并恢复初态。

完成后调用真正独立agent复审原卡与本轮返工项，范围内所有问题修复、OPEN为空。保留原独审和旧失败，新增本轮review与修复证据，在原delivery/handoff.md/json更新最终实现、受测/受审commit、对应SHA、实际命令结果、清理及局限。有既有remote正常commit/push原分支；无remote只提交本地并说明，不创建公开remote。不自行并主线或全局安装。然后STOP交ROOT，不等待其他两包，不向其他项目扩写。
