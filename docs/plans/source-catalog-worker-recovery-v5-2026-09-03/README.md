# Worker 恢复计划 v5 — 独立工作目录

> 2026-09-08跨计划衔接：当前由[R4数据湖收敛计划](../painpoint-outcome-audit-2026-09-05/simplified-execution-plan.md)C/D协调持久任务、安全、性能与恢复；本目录独占worker版本合同/正式冻结，不被替代或并入主线。R3的95门不再叠加；适用的v5安全/版本/恢复要求仍必须满足，A/B本地读取不等v5。D.SAFE不是恢复许可；真正worker仍需本候选隔离验证、持久领取/失败恢复、v5适用前置和精确授权。V5-1/2/3仍pending，baseline/import/reviews原字节不改。本轮只更新规划，不实施/恢复worker。

本目录由用户明确同意后于 2026-09-03 新建，是当前唯一继续维护的 worker 恢复计划目录。
原 `source-catalog-worker-recovery-2026-08-22/`（v1–v4）已按用户最新要求移入 Windows 回收站，
不再作为活动目录。**本目录不并入主线计划**，已核验的基线副本与原调查报告保留。

当前状态：**V5_BASELINE_READY / VERSION_CONTRACT_PENDING / NOT_IMPLEMENTATION_AUTHORIZED**。

## 使用顺序

1. 先读本文件、`task_plan.md`、`findings.md`、`progress.md`。
2. `baseline/plan/` 已保存原目录当前内容的逐字节副本，作为用户批准的**新审查输入**，
   不表示恢复了原 v4 冻结字节，也不表示原 v4 审查通过。
3. `baseline/history/` 保存原 v3/v4 manifest、旧进度/审查记录和冻结漂移诊断。
4. `baseline/investigation/` 保存原 worker 调查报告。
5. `import_manifest.v5.json` 只证明来源、复制完整性与导入时状态；
   **它不是正式 `plan_manifest.v5.json`，不得被当作实施或恢复授权**。
6. 旧文件中的 v4 名称、schema 常量和相对路径作为历史输入保留，不从新位置直接执行旧 checker、
   Gate 或 worker 命令。真正的 v5 版本合同、checker 和活动入口须另行闭合后才能冻结。

## 安全边界

- worker 继续保持暂停和禁自启动；本目录创建不授权实施、运行、登录测试、外发或数据库写入。
- 除用户明确授权退役旧v1–v4目录外，计划工作只写本目录；不改源码、配置、根级Git属性、hook或主线计划。
- 当前新目录未被 Git 跟踪，因此现有 pre-commit 的 tracked-file checkout 不会碰到它。
  这不是永久保证：其他任务若将其加入 index，必须重新确认审查边界。
- 本目录的 `.gitattributes` 只为本目录禁用 Git EOL/filter/encoding 转换；不能独自提供文件锁或
  对抗共享工作树的修改。正式审查前必须再次验证 index 状态与稳定输入。
- 不运行 `git add`、commit、stash、checkout 或 pre-commit；不自动修改权限或设置。

详细原改进步骤见[原实施计划副本](baseline/plan/task_plan.md)与[执行手册副本](baseline/plan/execution_playbook.md)，
仅供迁移和复审参考。每个关键节点的独立 agent Gate 要求继续保留，不能因迁入新目录而删减。

## 导入完成情况

- 54份基线文件（1,267,598 bytes）全部逐字节核对通过。
- 独立agent给出`IMPORT_REVIEW_PASS`，并回读确认[保存的导入审查记录](reviews/import-review-2026-09-03.md)。
- 导入manifest SHA-256：`da7d116e8c692d6311411c7390bec4278b59666a771823672f53e9b0f6567e4a`。
- manifest与baseline不再就地修改；它们不是正式v5计划冻结。下一步严格按[工作计划](task_plan.md)
  的V5-1版本合同阶段继续，不直接执行baseline里的旧checker或worker命令。
- 旧目录已可恢复移除，详见[退役记录](reviews/old-plan-retirement-result.md)。import manifest中的旧source
  路径只保留历史来源含义；只读导入校验不依赖这些旧路径存在。

从仓库根目录可重复执行仅检查本次导入的只读命令：

```powershell
python -B docs/plans/source-catalog-worker-recovery-v5-2026-09-03/verify_import.py
```
