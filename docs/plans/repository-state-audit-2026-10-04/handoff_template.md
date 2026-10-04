# Repository State Audit — 交接接口 v1

**目的：** 让独立 harness 交回可复核、可用于后续清理/并线决策的只读事实。复制本模板到该 lane 的唯一结果文件。任何无法证明的字段写 `unknown`，不得空缺后猜测。

## 0. 审计元信息（必填）

```yaml
audit_id: "RSA-<repo>-20261004"
repository: "<repo id>"
repository_root: "<absolute path>"
audit_status: "complete | partial | blocked"
started_at_local: "YYYY-MM-DD HH:MM TZ"
finished_at_local: "YYYY-MM-DD HH:MM TZ"
current_branch: "<name or detached>"
current_head: "<full sha>"
base_ref: "<exact local base ref>"
base_sha: "<full sha>"
remote_live_check: "ls-remote success | unavailable | not configured"
remote_checked_at: "<timestamp or unknown>"
source_changes_made: false
tests_run: false
```

## 1. 一页结论

- 有多少 branch-only commits 相对什么 base：
- 有多少 tracked staged / unstaged 文件：
- 有多少 untracked / ignored candidate（按目录汇总）：
- 有多少 linked worktrees；其中 dirty/ detached/ stale/用途不明各多少：
- PWF 称完成但 Git 未合、或 Git 已合但 PWF 仍待办的差异：
- 最大未决项：

## 2. 主线与远端识别

列出证据，不能只按 `main` / `master` 名字猜默认线。

| 线索 | ref/值 | SHA/结果 | 证据命令/文件 | 解释 |
|---|---|---|---|---|
| `origin/HEAD` 或服务端 default | | | | |
| 本地目标主线 | | | | |
| live remote `ls-remote` | | | | |
| 工作 checkout | | | | |

标出 remote-tracking refs 可能过期的情况。不得运行 `fetch` 刷新它。

## 3. Branch 矩阵（每个本地/远端开发分支一行）

| branch ref | tip SHA | merge-base | base-only commits | branch-only commits | patch-equivalent/ cherry | diff stat | PWF/交接关联 | 当前判断 |
|---|---|---|---:|---:|---|---|---|---|
| | | | | | | | | |

至少附带：

- `git rev-list --left-right --count <base>...<branch>` 原始结果，并正确解释左右两列。
- branch-only commit 的 SHA、标题、作者日期、改变路径；代码/测试/计划/唯一证据分别计数。
- `git merge-base --is-ancestor` / `git cherry -v` 或等价 patch-id 证据；已 cherry-pick 或 squash 的差异要写明。
- `git diff --stat <base>...<branch>`，对不适合逐行暴露的敏感文件仅写路径/统计。
- “待合并”只是分类建议；不得在审计中合并、cherry-pick、删除或移动分支。

## 4. Worktree 矩阵（包括 linked、detached、临时/review 路径）

| worktree path | branch/detached | HEAD SHA | porcelain 状态 | PWF/owner/创建来源 | 可能用途 | 确定度 |
|---|---|---|---|---|---|---|
| | | | clean/dirty + 计数 | | | |

逐个运行只读 `git status --short --branch`。若路径已不存在或不可访问，记录原样，不做 prune/remove。

## 5. 当前未提交文件

分别报告 staged、unstaged、untracked；同一文件可同时 staged 与 unstaged。不得把 `A/M/D` 状态合并成“有改动”。

| 路径 | Git 状态 | staged diff | unstaged diff | 类型/可能用途 | PWF/commit/调用者证据 | 敏感性 | 推荐后续分类 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

对于 key/secret/token、用户本机配置、真实公司原文、LLM 输出、数据库、二进制覆盖率、巨大生成目录：报告存在性、Git 状态、大小/时间/文件数等最小元数据即可；不读取正文、不输出 value/hash。

## 6. 未跟踪/ignored 工件及空间线索

| 目录/文件 | Git ignored/untracked 状态 | 文件数/总字节（若可低成本测量） | 创建/消费证据 | 是否唯一审查/测试证据 | 可再生证据 | 结论/未决 |
|---|---|---:|---|---|---|---|
| | | | | | | |

仅从 dirty 文件所在目录与计划明示的运行目录向下取证；不得全盘递归扫描或因为名字含 `temp/cache/output/run` 就认定可删除。

## 7. PWF 与 commit 记录对照

| PWF 位置/plan id | PWF 声明状态/最后时间 | 关联 SHA/工作树 | Git/现存测试/CI 收据核验 | 一致/冲突/不确定 |
|---|---|---|---|---|
| | | | | |

必须明确读取 active plan selector / 计划入口；搜索 `task_plan.md`、`progress.md`、`findings.md`、handoff、execution run ledger。把旧 plan、冻结计划、镜像状态与唯一权威入口分开。Session catch-up 不属于本任务，不运行。

## 8. 已有测试、CI、E2E 证据（仅查记录，不运行）

| 命令/Workflow/报告 | 绑定 SHA | 结果与日期 | 是否覆盖 branch-only / dirty 行为 | 限制 |
|---|---|---|---|---|
| | | | | |

## 9. 建议的后续处置类别（不执行）

每个 branch/worktree/dirty/untracked 项只选一个初步类别，并给出证据：

- `already_in_base`（提交/patch 已在 base；可能只剩过时 branch ref）
- `merge_candidate`（仍有独有价值，合入前需集成测试）
- `preserve_active_work`（owner 正在用或有未提交工作）
- `unique_evidence_preserve`（评审/实验/唯一审计证据）
- `generated_candidate_review`（疑似可再生，但删除前要验证来源/消费者）
- `owner_decision_needed`（归属/意图无证据）
- `deploy_or_archive_branch`（不是 development mainline）
- `no_change`（证据确认无需动作）

不得输出“现在删除/恢复/合并”命令。后续施工应由总指挥制定新计划。

## 10. 检查命令与结果（脱敏）

列出实际执行的关键命令、退出码、只读属性和因权限/网络/工具失败跳过的项目。不粘贴远端 URL、凭据、敏感正文或长日志。

## 11. 交接声明

- 我只读取 lane 指定的仓库，没有改动工作树、索引、Git refs、全局配置或其他项目：`yes/no`。
- 我没有运行会写文件的测试、构建、下载或 provider/LLM：`yes/no`。
- 本报告结论覆盖的 HEAD SHA：
- 需要总指挥复核的唯一事项（如无写 `none`）：
