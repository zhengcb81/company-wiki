# Lane Dayu — Dayu agent 分支/未跟踪文件只读盘点

## 硬边界

唯一目标仓：`C:\Users\郑曾波\Projects\dayu-agent\dayu-agent`。用户已明确：Dayu 是纯外部项目，不能有任何代码变更，相关本地修改全部回退。**本施工包只盘点，绝不修改/回退 Dayu 任意代码、配置、Git refs、worktree 或生成物。**结果写回 CWP 指定文件。

禁止 fetch/pull/switch/checkout/restore/reset/stash/clean/merge/rebase/cherry-pick/commit/push、`git config`（包括命令级以外的持久改动）、测试/构建/下载。不要写 `.pyc`/缓存或 HTML 报告。

## 已知起点（重新确认）

- `main@2115c86` 与 live `origin/main` 相同；live `origin/opt/cn_score@76037b2` 比 main 有 1 个独有提交（港股/A股财报提取改动）。
- 根工作树有 untracked `docs/architecture_report.html`。
- 该仓没有常规 PWF `task_plan/progress/findings`；`docs/TODO.md` 等只是线索，需承认缺 PWF，不把旧 todo 当授权。

## 只读盘点步骤

1. 查根 status、all local/remote branch refs、worktree list；逐项算 opt/cn_score 对 main 的 unique commits、patch-id 和具体文件 diff stat。
2. 读该分支 commit 记录、相关 TODO/README/实现注释，以及已有 test/CI 配置和输出（如已存在）。不执行 branch 里的功能代码。
3. `architecture_report.html` 仅查 Git ignore 状态、字节数、修改时间、生成命令/被引用链接；除非已确认无公司/凭据/私人内容才可读局部。禁止复制正文。
4. 分类清楚：remote development commit、local dirty/untracked、历史计划、已有消费者、文件可再生性。用户已给的“Dayu 不改”优先于 branch 实现自述；不建议把远端 opt commit 合并到 Dayu。
5. 查不到 owner/生成器/历史时写 unknown，保留而不触碰。

## 唯一交接

按 `../handoff_template.md` 写：

`C:\Users\郑曾波\Projects\company-wiki\docs\plans\repository-state-audit-2026-10-04\results\dayu_agent.md`

结论明确保证审计过程中 Dayu 工作树与 Git metadata 没有变化。对每项只建议后续分类，不生成回退命令。
