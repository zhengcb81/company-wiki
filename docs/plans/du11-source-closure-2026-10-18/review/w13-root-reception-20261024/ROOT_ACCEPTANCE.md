# W13 ROOT 验收与并线记录

## 验收结论

接收 ROOT 修正后的 W13 推送调度改造。作者冻结候选 `a804541661f73cd035fc25179b116ba9a51c5e55` 独立审查为 FAIL；ROOT 修正版独立审查为 `PASS_ROOT_INTEGRATED_FIXES`，详见同目录 `independent/report.md` 和 `independent/report.json`。本记录绑定 ROOT 审查的八个文件完整 SHA-256，见 `independent/root-final-source-bindings.json`。审查器后来观察到作者工区又前进到 `852dff283ed9f18dd4e0dd1376c4ca89a52b1795`，并有未提交 review 文件；这些内容不属于本次接收，也没有被 ROOT 改写。

ROOT 修复后的最终验证为 154 项通过（125.60 秒；含并行审查的 CPU 争用）、18 个独立执行策略探针通过、5 项真实本地 Git ref/推送端到端检查通过、Ruff 通过。没有重跑 8 千余项全量单测。测试原始 XML、实际目标清单、完整 stdout/stderr、独立夹具清理和源码绑定均在 `independent/`。合成夹具验证的是 hook 拒绝/放行行为，不代表生产业务测试性能。

## 修复的共因

- 对受影响文件数超过 32 的封闭测试范围整体延后给 CI；不截断前 32 个文件。目录、动态或未知范围也走固定快速集。
- 测试开始前只打印计划范围；完整列出目标与延后原因。只有 pytest 成功结束后才打印 `local_fast_pass`。
- runner 缺失、启动异常、测试失败和非零退出码都阻止 push。
- 固定快速集 29 个成员、完整本地模式、CI 命令/执行器保持既有定义。

## 发现但本卡未修的事项

- 旧全量模式 19 条 atomic-temp 失败并非随机 xdist/杀毒波动：Windows 路径长度探针在 259 字符成功、260 及更长失败，旧失败路径为 261/263/264。共因尚未修复，列入 ROOT 后续测试隔离/短路径修复任务。
- 冻结作者基线上的 B10 ratchet 仍为 3 失败/13 通过；相关生产源、CI 树及测试 helper 不属于 W13 改动。保留原断言，不将其登记成已修复。
- 新 worktree 的 `config_doctor` 缺运行目录、实际远端 CI、真实受影响文件耗时和 selector AST 规划开销仍待单独处理/观察。
- 作者 handoff 的 `sha256_prefix` 实为 Git blob ID，不是文件 SHA-256。ROOT 本次只使用完整物理字节 SHA-256 绑定，原交接照历史保留。

## 发布状态

本记录创建时，W13 的作者祖先已在 ROOT 的 pending merge 中，ROOT 修复、验收记录和 PWF 待提交。必须使用常规 merge commit、正常 pre-push 和正常远端推送；完整 suite 留给现有 CI。提交后更新本节、`CURRENT_STATUS.md/json` 及精确 CI 收据。全量 Windows 长路径和 B10 问题不阻止 W13 有界调度接收，但不能标为解决。
