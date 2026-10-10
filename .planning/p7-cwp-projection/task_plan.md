# P7-CWP-PROJECTION 独立实施计划

## Goal

完整实施 IMPLEMENTATION_CARD.md 所定义的通用责任包。只修改该卡允许写集，保护原件/config/邻仓ownerWIP/旧sealed。按TDD建立真实失败，再实现共用修复，最后集中离线E2E和独立大节点复核。不开真实下载/付费模型，不改安装或主线。

## 基线与唯一计划

- repository：company-wiki
- workspace：C:/Users/郑曾波/Projects/_harness_worktrees/p7/cwp
- branch：codex/p7-cwp-projection-identity
- source base：f8956d299b52849a4beb06e4071816ec72ddc6a3（bootstrap文档提交的祖先，不要求HEAD==base）
- PLAN_ID：p7-cwp-projection；PWF_PLAN_ROOT为本工作目录。
- 唯一施工细则 IMPLEMENTATION_CARD.md；接口/交接格式就在本PWF。

## 大节点

| 节点 | 内容 | 状态 |
|---|---|---|
| 准备 | 工作树/源码基线、独立PWF与施工卡/公共交接副本 | complete |
| M1 | 读实际接口、固定输入输出样例、责任RED与真实日志 | pending |
| M2 | 共用实现与集中GREEN、旧兼容、边界内静态检查 | pending |
| M3 | 自有TEMP离线公共E2E、恢复、独立关键不变量审查、正常commit与交接 | pending |

只有三个施工大节点，技术断言/诊断不是额外人工审批。分支CI未触发记录not_triggered，无remote记录no_remote，不伪造green。不关闭MAIN真实公司研究。

## Next Step

开始M1：读本卡与实际项目约束/代码/现有测试，写最小契约RED并保存真实命令、exit和日志。先保留失败，再实现。
