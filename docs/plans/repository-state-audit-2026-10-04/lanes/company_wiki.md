# Lane CWP — company-wiki 自身状态只读盘点

## 目标与边界

唯一目标仓：`C:\Users\郑曾波\Projects\company-wiki`。本 lane 只读，重点核对 G1、RF-state、FC-802 history refs，所有 linked/review/detached worktrees，以及用户未提交 provider 配置。

由于总计划和审计包自身就写在 CWP，报告**只能通过 harness 最终回复完整返回**，不得写入 CWP 的任何文件或临时目录。这样不会把审计包文件算入被审计工作树。不得操作或读取 StockInfoDownloader、Dayu、RF 等其他 source repos；只看 CWP 内已有副本/报告。

严禁 fetch/pull/切 branch/写任何文件/索引/refs、删除/恢复配置或运行测试。`config/source_acquisition.yaml` 是用户本机已有的 3 行修改，**只报路径和状态，不显示 diff 内容**。

## 已知起点（重新确认）

- `master@0c259cce` 与 live `origin/master` 同 SHA。
- `codex/g1-legacy-entry-retirement@c3209ee` 相对 master 有 2 个 branch-only doc commits；main 的另一目录已有 G1 report，需检查内容重复和哪份是交接真源。
- `codex/rf-state-audit@447d1c7` 有 2 个本地 branch-only commits，含 CWP 内 RF worktree audit report；远端是否存在该分支要用 `ls-remote` 检查。
- `codex/history/fc802-r3-accepted-20261003` 与 `...rejected...` 各有一个 branch-only receipt/report；它们是互相冲突的历史审查结论，不可简单合并成同一事实。
- 主工作树有 `config/source_acquisition.yaml` dirty；本轮计划也会在该仓新增文件，审计报告必须通过回复返回，不写 `results`。
- 本仓有多个 `.codex/worktrees` 和 `Temp`/preb/review worktrees，其中一些 detached checkout 显示大量删除状态；须查创建和执行记录，不能据表面删除恢复/清理。

## 必读记录与检查步骤

1. 本计划之外的 CWP current active `.planning/.active_plan` 与对应三件套只读核对；也读 `docs/plans/narrative-evidence-pilot-2026-09-26/{task_plan,progress,findings}.md`。
2. 读取 G1 lane/handoff、RF-state audit lane/handoff、FC-802 两个 competing reviewer reports 及其关联 commit SHA；区分结果文档、实现是否早已集成、重复拷贝与未提交记录。
3. 对 `git worktree list --porcelain` 的每个路径分别查 status、HEAD、branch、path existence；优先找到 PWF `execution_runs`/snapshot provenance。对删空/不可访问目录只记现状，不跑恢复脚本。
4. base 取 live `origin/master`；`git ls-remote --heads origin` 按精确 refs 查询，不 fetch。按 base...branch、cherry/patch-id、diff name status区分 branch-only 与已集成变化。
5. 用户 config 仅记有 1 个 modified tracked path，不展示内容。其他结果里本计划文件属于审计自身，忽略，不纳入 2026-10-04 初始 dirty baseline。
6. 不运行 CWP 测试；只对已有 PWF 中的测试/CI receipts与 SHA。

## 唯一交接

将 `../handoff_template.md` 全文结构用于最终回复，不写任何文件。完整回复中需回答：哪些分支仍携带独有内容；G1 两个 docs commits 与主线 report 的关系；RF-state audit 是否 push/重复；FC-802 accepted/rejected 的正确历史边界；Temp/preb worktrees 的来历/dirty 类型；用户配置的安全保留建议。
