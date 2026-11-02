# R7 ROOT / invest 大节点独立审查 R1

结论：**NEEDS_ROOT_FIX_STAGED_CONTENT**。绑定原 17 文件 manifest SHA `5abbd678ca4a6f40816235d73265031c389e650c51915603090539c5ccfff9b5`；不审自己的工具线 30 文件，不修改 ROOT 源码/测试/主 PWF/Git。

实际独立合成域 **10 例：9P/1F，1.26s**。完整探针、case、JUnit、实际快检收据和 17 SHA 在同名 JSON。

## P2 / R7-ROOT-A01：暂存与工作树版本混淆

`invest-skills/tools/pre_push_gate.py` 的 `_staged_python` 读取 index 文件名，但 `main --commit` 的 compile 与 Ruff 读取工作树内容。真实临时 Git 中 stage `def staged_invalid(:`，随后工作树改成 `valid_worktree=True`，实际 syntax path 返回 0；只将 Ruff stub 为 0 隔离语法 owner，未模拟 Git 或编译。

因此坏的将提交字节可被另一份工作树内容冒充通过，反向也会误挡好提交。应按 `git show :0:relative` 读取 index 字节编译，并用自有暂存快照运行一次 Ruff、保留实际项目配置；不 stash、不修改真实 index/worktree、不增加 whole-tree clean 许可。ROOT 已确认并接手修复。

## 已通过的本轮范围

- 大于 1MB 的新记录保全部正文/可选 trace/必需引用及 False/None，不变成完整/verified。
- 新 173 层父树完整，真实 cycle 明确不完整；语义与物理 proof 重叠不丢角色，forbidden 仅命中 meaning/heading，未知诊断保留且不自动 actor PASS。
- fsync 真 I/O 故障保前 checkpoint；异常编码保 RESULT_READY 与未知/False 状态；两个 late foreign writer 控制不覆盖外来文件。
- 实际 invest `_run` 对大日志 child 保真实 0/23，不因体积否决。
- 一次真实 invest fast gate：**exit0，总2.716s，smoke21P1skip/1.82s + Ruff**。80 份 RF scripts Python SHA 前后全同，4 WIP 与已有基线一致且未变；caller index 哨兵未动，自动 smoke 临时 index 结束不存在。没有部署全局技能、运行整套 suite 或读取真实原件/模型。

RF 稳定窗口已经及时释放，不因等待报告继续占用作者。

## P3 非阻断建议

`invest_contracts.validate_revenue_forecast` 先 `verify_input_binding` 再调用强 `validate_published_forecast`；后者当前已经内部做 binding 和完整输出重算。同事务可薄成强 owner 一次调用。完整输入、身份/币种/单位/期间、重算和 artifact hash 校验不是人工权限，不能随此建议删除。

本轮不签真实 H1/摘要/cache/RF 经济采用或全目标完成。保留这份 R1 FAIL，ROOT 返修冻结后只增量复验 staged 缝；不重复以上通过范围。自有 UUID tmp 初始 absent，暂用于 R2，证据已嵌 JSON，结束统一恢复 absent。
