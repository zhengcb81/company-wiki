# Lane ET — earnings-transcripts 支线与运行文件只读盘点

## 目标与边界

唯一 Git 仓库根：`C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts`；并检查该仓 linked worktree `earnings-transcripts-s3-deadline`、`earnings-transcripts-s3-runtime`。不要审计/修改其他项目。

只读：不 fetch/pull、切换分支、改文件/refs/index、删目录或运行 provider/测试/LLM。未跟踪 `.workbuddy-ai/`、`eval_results.json` 只查最小元数据，不输出可能含正文或调用数据的内容。

## 已知起点（重新确认）

- `main@93fe52c` 与 live `origin/main` 同 SHA；bounded-runtime 已 merge。
- `codex/et-s3-deadline@0017f24` 对 main 有 1 个独有提交，且 live remote ref 同 SHA。
- deadline 分支的 PWF `task_plan/progress` 曾把 “commit/push 分支”记为待办，但 SHA 已远端可见。这是计划文本过期，不等于代码还未交付。
- 根 main 工作树 untracked `.workbuddy-ai/` 与 `eval_results.json`。

## 必读记录与检查步骤

1. main 的 `.planning/s3-et-bounded-runtime-20261003/{task_plan,progress,findings}.md`、`docs/implementation/s3-et-runtime-handoff.md`。
2. deadline worktree 的 `.planning/s3-et-deadline-20261004/{task_plan,progress,findings}.md` 和 `docs/implementation/s3-et-deadline-handoff.md`；对照 remote/main branch refs、branch-only commit、交接 SHA，查是否只差合 main。
3. `git worktree list --porcelain` 加逐 worktree status；识别以前复制真实 transcript 文件的重复工作树是否还存在。只报 PWF 有证据支持的存储目录，不遍历/输出 transcript 正文。
4. 对每个 branch 相对 `origin/main` 重算左右数、merge-base、commit log、diff stat、patch-equivalent。runtime 分支已合不代表 deadline branch 也已合。
5. untracked `.workbuddy-ai/`、`eval_results.json` 查询 ignore 状态、文件/字节数、计划引用和修改时间；内容可能包含用户/模型记录时不读正文。
6. 查看 PWF 所引用已有的测试数字和 run receipt；不重新跑测试。

## 唯一交接

按 `../handoff_template.md` 写：

`C:\Users\郑曾波\Projects\company-wiki\docs\plans\repository-state-audit-2026-10-04\results\earnings_transcripts.md`

报告需回答：deadline 实现已提交/已推远端但未并 main 的事实是否由 PWF 证明；已有测试和 handoff 是否绑定 `0017f24`；main/旧 runtime/deadline 目录是否仍重复存文档、重复量由何记录证明；两个 untracked 根项的用途、可再生性和保留级别。
