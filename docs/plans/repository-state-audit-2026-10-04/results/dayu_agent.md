# Repository State Audit — Dayu agent（唯一结果）

按 `../handoff_template.md` v1 编写。所有结论均来自本轮只读命令；无法证明处写 `unknown`。**用户硬指令：Dayu 是纯外部项目，本审计不改其任意代码/配置/分支/文件/Git refs/worktree。**

## 0. 审计元信息（必填）

```yaml
audit_id: "RSA-dayuagent-20261004"
repository: "dayu-agent（本地目录 dayu-agent\\dayu-agent；GitHub 远端，按模板不粘贴 URL）"
repository_root: "C:\\Users\\郑曾波\\Projects\\dayu-agent\\dayu-agent"
audit_status: "complete"
started_at_local: "2026-10-04 约19:03 +01:00（约，分钟级精度）"
finished_at_local: "2026-10-04 19:15 +01:00"
current_branch: "main"
current_head: "2115c86d5a9027bb51cbbc8a4d0175080732e4e6"
base_ref: "refs/heads/main（与 refs/remotes/origin/main、live origin HEAD/main 一致）"
base_sha: "2115c86d5a9027bb51cbbc8a4d0175080732e4e6"
remote_live_check: "ls-remote success"
remote_checked_at: "2026-10-04 约19:07 +01:00（约）"
source_changes_made: false
tests_run: false
```

## 1. 一页结论

- **branch-only commits 相对什么 base：** 唯一含独有提交的分支是远端 `origin/opt/cn_score@76037b2`，相对 base `main@2115c86` 为 **1 个独有 commit**（`git rev-list --left-right --count main...origin/opt/cn_score` = `0\t1`：左列 base-only 0，右列 branch-only 1）。`git cherry -v` 输出 `+ 76037b2…`（**base 中无 patch-equivalent**）；`merge-base --is-ancestor` exit=0（main 是其祖先，分支基于 main tip）。本地**没有** `opt/cn_score` 本地分支，只有 remote-tracking ref；该 commit 仅包含于 `origin/opt/cn_score`（`branch -r --contains` 证实），**未进 main**。
- **tracked staged / unstaged 文件：** staged **0**、unstaged **0**（`git status --short --branch` 除分支行外仅 1 行 untracked；结束时复核一致）。
- **untracked / ignored candidate（按目录汇总）：** untracked **1** 个：`docs/architecture_report.html`（check-ignore exit=1，**未被忽略**）。ignored 按目录：根级 `.pytest_cache/`、`.venv/`、`dayu_agent.egg-info/`、`workspace/`，单文件 `uv.lock`，以及 `dayu/**`、`tests/**` 下共 **31 个 `__pycache__/`**；另有空目录 `.benchmarks/`（0 文件，`git status` 不列空目录，未出现在 ignored 输出）。
- **linked worktrees：** **1 个**（默认 checkout `C:\Users\郑曾波\Projects\dayu-agent\dayu-agent`，branch `main`）：tracked 全净 + 1 untracked；无 detached、无失效路径、无多余临时 worktree（未做也不需要 prune）。
- **PWF 称完成但 Git 未合、或 Git 已合但 PWF 仍待办的差异：** 本仓**完全没有 PWF**（无 `.planning/.active_plan`、无 `task_plan.md`/`progress.md`/`findings.md`/handoff/ledger——Glob+Test-Path 全空）。`docs/TODO.md` 只是 3 个无状态标题（最后提交 2026-04-22 `686718b` #20），不构成授权。因此仓内无可对照的 PWF↔Git 差异；远端侧存在 PR 证据（`refs/pull/159/head` == `76037b2`），PR 状态 unknown（本机无 gh CLI），见 §3/§7。
- **最大未决项：** ① `docs/architecture_report.html` 的 owner/生成命令/历史全查不到（全仓 0 引用）→ unknown，保留不触碰；② `opt/cn_score` 的 1 个独有 commit 对应 PR #159 的开/关/合状态与上游处置意图 unknown——**按用户指令不建议把该远端 commit 合并进 Dayu**，处置归上游维护者/总指挥另行决策。

## 2. 主线与远端识别

| 线索 | ref/值 | SHA/结果 | 证据命令/文件 | 解释 |
|---|---|---|---|---|
| `origin/HEAD` 或服务端 default | 本地**已配置**：`refs/remotes/origin/HEAD` → `origin/main` | `2115c86d5a9027bb51cbbc8a4d0175080732e4e6` | `git branch -a -vv`（显示 `remotes/origin/HEAD -> origin/main`）、`git for-each-ref` | 远端默认分支是 `main` |
| 服务端 default（live HEAD） | `git ls-remote origin` 首行 `HEAD` | `2115c86d…`（与 live `refs/heads/main` 相同） | `git ls-remote origin`（只读，未 fetch、未写 FETCH_HEAD——`.git/FETCH_HEAD` 不存在） | 远端 HEAD == live main |
| 本地目标主线 | `refs/heads/main` | `2115c86d…` | `git branch -vv`：`* main 2115c86 [origin/main]`，无 ahead/behind 标记 | 工作 checkout 所在分支；lane 指定的审计基线 |
| live remote `ls-remote` | heads：`main=2115c86…`、`opt/cn_score=76037b2…`；tags `v0.1.0–v0.1.4` 与本地一致；另见 `refs/pull/159/head=76037b2…`、`refs/pull/159/merge=32592abe…` 及大量其它 PR refs | exit=0 | `git ls-remote origin` | 本地 `origin/main`、`origin/opt/cn_score` 与 live **精确相同**（remote-tracking **不过期**）；按禁令未 fetch |
| 工作 checkout | `main` | `2115c86d…`，tracked 全净 + 1 untracked | `git status --short --branch` → `## main...origin/main` | 无 ahead/behind；开始/结束各复核一次，输出一致 |

关键事实：

- clone/reflog：`git reflog show main` 仅 1 条——`2115c86 main@{0}: clone: from …`（`.git` 元数据 mtime 2026-05-30 22:42:41）。此后本地无任何 fetch/switch/commit 记录；`ORIG_HEAD` 不存在。
- 本地 ref 完整清单（`for-each-ref`）：`refs/heads/main`、`refs/remotes/origin/{HEAD,main,opt/cn_score}`、`refs/tags/v0.1.0…v0.1.4`。**本地分支只有 main**；`opt/cn_score` 仅存在于远端 + remote-tracking。
- 5 个 tag 均为发布标签（`v0.1.0`–`v0.1.4`），tip 都在 main 历史内（如 `v0.1.4` = `c13958d`，见 `main` log `ver/v0.1.4 (#147)`），无 branch-only 价值。

## 3. Branch 矩阵（每个本地/远端开发分支一行）

| branch ref | tip SHA | merge-base | base-only commits | branch-only commits | patch-equivalent/ cherry | diff stat | PWF/交接关联 | 当前判断 |
|---|---|---|---:|---:|---|---|---|---|
| `refs/heads/main`（= base） | `2115c86d5a9027bb51cbbc8a4d0175080732e4e6` | （自身） | 0 | 0 | n/a | n/a（tracked 无改动，1 untracked 见 §5） | 本仓无 PWF | 基线本身；`no_change` |
| `refs/remotes/origin/main` | `2115c86d…`（与本地 main 相同） | （自身） | 0 | 0 | n/a | n/a | 同上 | 与 live 精确一致；`no_change` |
| `refs/remotes/origin/opt/cn_score` | `76037b242d0b14a77281d7bc610429296123c5cb` | `2115c86d…`（= base tip，`git merge-base` 输出；`merge-base --is-ancestor main origin/opt/cn_score` exit=0 → main 是其祖先） | 0 | 1 | `git cherry -v main origin/opt/cn_score` → `+ 76037b242d0b… 优化港股A股财报提取`（**`+` = base 中无等价 patch**） | `git diff --stat main...origin/opt/cn_score`：5 files, **296 insertions(+), 9 deletions(-)** | 无 PWF；`docs/TODO.md`“A股/港股财报上传”标题与其主题相关但无状态、无 SHA 对应（仅线索） | **remote development commit，已 push**；见下方明细与 §9：按用户指令**不建议合并入 Dayu**，本地 `no_change` |
| `refs/tags/v0.1.0`…`v0.1.4`（release 标签，非开发分支） | 5 个 tag（annotated，`^{}` 解引用指向 main 历史内 commit） | 在 main 历史内 | — | 0 | n/a | n/a | CHANGELOG 有对应发布记录 | `no_change`（非开发线） |
| live `refs/pull/159/head` | `76037b242d0b14a77281d7bc610429296123c5cb`（与 `opt/cn_score` tip **同 SHA**） | n/a（PR ref 非开发分支） | n/a | n/a | 同一 commit | 同上 | **PR #159 存在**的直接证据；`refs/pull/159/merge=32592abe…` 为 GitHub 计算的 merge ref（存在≠已合并） | PR 开/关/合状态 **unknown**（无 gh CLI；按禁令未 fetch、未抓取网页） |

原始计数与解释：

- `git rev-list --left-right --count main...origin/opt/cn_score` → `0\t1`：**左列（base 侧）0 个独有，右列（branch 侧）1 个独有**。
- `git merge-base --is-ancestor main origin/opt/cn_score` → exit 0：main 是分支祖先（分支 = main + 1 commit，理论可 fast-forward——**但按 lane/用户禁令不执行任何合并**）。
- `git cherry -v main origin/opt/cn_score` → `+ 76037b2…`：patch-id 不在 base。结合 `branch -r --contains 76037b2` 仅输出 `origin/opt/cn_score`、main 近期 log 无同主题 squash（main 侧最近相关为 `8794bcd opt/cn score (#155)`，更早且不同 SHA/不同 patch）：该 commit **未以 merge/rebase/squash 任何形式进入 main**。

branch-only commit 明细（full message + name-status/stat；代码/测试/计划/唯一证据计数）：

1. **`76037b242d0b14a77281d7bc610429296123c5cb`** — `优化港股A股财报提取`，作者 `Leo Liu <leoliu2000@hotmail.com>`，AuthorDate = CommitDate `2026-05-05 21:05:08 +0800`。message 无 body、无测试收据、无计划文件。5 个文件全部为 M（修改既有文件）：
   - **代码 2**：`dayu/fins/processors/financial_enhancer.py`（+20/-0：新增港股现金流表体同义词，如 `來自經營業務之現金淨額`、`融資業務所得╱（所用）現金流量淨額` 等）、`dayu/fins/score_docling_ci.py`（约 +15/-4：新增 `market` 参数贯通 `_effective_financial_groups`/`_evaluate_hard_gate`；港股季度（HK quarterly）返回空 `FINANCIAL_GROUPS_QUARTERLY_HK` → 不再强制完整三大表 hard gate，A 股季度仍要求；mda/key_financials 同义词扩充“討論與分析/財務業績”等）。
   - **文档 1**：`dayu/fins/README.md`（2+/2-：同步上述评分边界与同义词说明）。
   - **测试 2**：`tests/fins/test_financial_enhancer_coverage.py`（+62：2 个港股现金流 caption 新用例）、`tests/fins/test_score_docling_ci.py`（约 +197/-3：`market` 参数、HK 季度无三大表 hard-gate 用例、同义词用例、HK quarterly snapshot fixture 构造器）。
   - **计划 0 / 唯一证据 0**：commit 无计划附件；其测试文件在 base 上已存在（属修改而非新增独有证据文件）。
- 内容性质：**CN/HK 财报提取/评分优化**（与 lane“已知起点”描述的“港股/A股财报改动”一致），是正常功能开发而非部署/杂项分支。
- 关联：`refs/pull/159/head` 与该 SHA 相同 → 该分支曾/正以 PR #159 面向 main；`ci-pr-extended.yml` 与 `ci-pr-required.yml` 的触发条件均为 `pull_request: branches: [main]`，若 PR 开启则会跑 CI——**PR 状态与 CI 运行结果本地无记录，unknown**。

**“待合并”仅是分类事实陈述；本审计未合并、未 cherry-pick、未删除或移动任何分支。**

## 4. Worktree 矩阵

| worktree path | branch/detached | HEAD SHA | porcelain 状态 | PWF/owner/创建来源 | 可能用途 | 确定度 |
|---|---|---|---|---|---|---|
| `C:\Users\郑曾波\Projects\dayu-agent\dayu-agent` | `main` | `2115c86d5a9027bb51cbbc8a4d0175080732e4e6` | **tracked 全净** + 1 untracked（`?? docs/architecture_report.html`）；staged 0 / unstaged 0 | 无仓内 PWF；reflog：2026-05-30 22:42:41 `clone: from …`（此后无 switch/commit/fetch 记录） | 默认 checkout（本仓唯一工作树） | 高（命令直接观测） |

- `git worktree list --porcelain` 仅以上 1 条；无 linked/detached/临时/review 路径，无失效路径（未做也不需要 prune）。
- `git stash list` → 空。

## 5. 当前未提交文件

**staged（index）：0 个。unstaged（worktree vs index）：0 个。untracked：1 个。**

| 路径 | Git 状态 | staged diff | unstaged diff | 类型/可能用途 | PWF/commit/调用者证据 | 敏感性 | 推荐后续分类 |
|---|---|---|---|---|---|---|---|
| `docs/architecture_report.html` | `??`（untracked；`git check-ignore -v` exit=1 → **未被任何 ignore 规则覆盖**） | 无（未暂存） | 无（不在 index，无对比基线） | HTML 报告，162,845 B，mtime `2026-06-08 21:01:46`（晚于 5-30 checkout、早于 7 月测试运行）；`<title>` 为 `dayu-agent 架构分析报告`，结构为分节概览（首个 HTML 注释 `1. 概览`） | **生成者/命令/历史全 unknown**：全仓 Grep `architecture_report` 0 命中（含未跟踪未忽略文件）；无脚本、无文档引用、无 TODO 记录；`.claude/`/`.mimocode/` 等工具目录在本仓不存在 | 已做只读模式扫描（**未复制正文、未输出 value/hash**）：`secret`/`password`/`bearer`/`authorization`/`cookie`/`credential`/`private_key`/`sk-*`/`ghp_*`/`github_pat_*`/`AKIA*`/带凭据 URL/邮箱/手机号/身份证 全部 **0 命中**；`api_key` 唯一命中上下文为字段声明（`api_key: str` 型签名清单）；`token` 14 处均为“LLM token 估算 / CAS fence token”技术语境。判定：**无凭据、无私人内容**；项目自身的架构分析文档 | `owner_decision_needed`（生成器/owner unknown → 保留而不触碰；删除前需总指挥/owner 确认可再生性与消费者） |

未做：读取/复制报告正文、全仓递归扫描、对任何文件做内容 hash 输出。

## 6. 未跟踪/ignored 工件及空间线索

| 目录/文件 | Git ignored/untracked 状态 | 文件数/总字节（低成本测量） | 创建/消费证据 | 是否唯一审查/测试证据 | 可再生证据 | 结论/未决 |
|---|---|---:|---|---|---|---|
| `docs/architecture_report.html` | **untracked（非 ignored）** | 1 / 162,845 B；mtime 2026-06-08 21:01:46 | 仓内无任何引用/生成线索（Grep 0 命中）→ unknown | 疑似唯一一份（无副本证据） | unknown | `owner_decision_needed`（见 §5） |
| `.pytest_cache/` | ignored（`.gitignore` `.pytest_cache/`） | 5 文件 ≈6.5 KB：`v/cache/nodeids` 6,093 B（**63 个 test id，全部 `tests/fins/*`**）、`v/cache/lastfailed` 2 B（内容 `{}`=无失败）+ 3 个说明文件；mtime 2026-07-18 19:33–20:13 | pytest 自动产物；**唯一本地测试运行痕迹** | **是**（唯一仓内 pytest 收据） | 重跑可再生，但 2026-07-18 的历史结果不可再生 | `unique_evidence_preserve`（至少保留到总指挥采纳本报告） |
| `workspace/` | ignored（`.gitignore` `workspace`/`workspace/`） | 仅列顶层名：`.dayu/`、`assets/`、`config/`、`output/`、`portfolio/`、`.dayu_init.lock`（mtime 2026-05-30/31）；**未递归、未读内容** | `dayu-cli init` 工作区（`.dayu_init.lock` 即初始化锁）；`portfolio`/`output` 疑似真实财报/运行数据 | 未取证（可能含真实数据/用户配置） | 下载数据理论上可重下但成本高 | `owner_decision_needed`（不因名字含 workspace/output 就认定可删；未读取正文） |
| `.venv/` | ignored | 目录存在，mtime 2026-07-20 23:32；**未逐文件统计**（避免全盘递归） | 本地虚拟环境（AGENTS.md 要求 `source .venv/bin/activate`） | 否 | 是（uv/pip 可重建） | `generated_candidate_review` |
| `dayu_agent.egg-info/` | ignored（`.gitignore` `*.egg-info/`） | 目录 mtime 2026-07-20 23:24；未逐文件统计 | `pip install -e .` 产物（CI 配置亦用 `-e .`） | 否 | 是 | `generated_candidate_review` |
| `uv.lock` | ignored（`.gitignore` 显式列 `uv.lock`） | 1 / 962,899 B；mtime 2026-07-18 19:40 | uv 锁文件；**项目策略选择不入库**（非本审计可改） | 否（但属环境重建输入） | 是（`uv lock` 可再生，内容随时间漂移） | `owner_decision_needed`（是否保留/入库属项目策略与 owner 决策） |
| 31 个 `__pycache__/`（`dayu/**` 29 处 + `tests/`、`tests/fins/`） | ignored（`.gitignore` `__pycache__/`） | 31 目录；**未统计字节**（避免全盘递归） | Python 字节码缓存 | 否 | 是 | `generated_candidate_review` |
| `.benchmarks/`（根目录） | **不在 git 输出中**（空目录，`git status` 不列无文件目录） | 0 文件（`Get-ChildItem -Recurse` 为空）；目录 mtime 2026-07-18 19:33（与 pytest 运行同时段） | 仓内无引用；pytest-benchmark 惯例命名仅为推测 | 否 | 空目录 | `owner_decision_needed`（用途 unknown；保留不触碰） |
| 仓库根外/工具状态 | `.claude/`、`.mimocode/`、`.obsidian/`、`.vscode/`、`.codegraph/`、`.workbuddy-ai/`、`htmlcov/`、`.coverage`、`.ruff_cache/`、`tests/screen/` **均不存在**（Test-Path 全 false；与 `git status --short --ignored` 输出一致） | — | — | — | — | 无此项 |

未做：全盘递归扫描、`workspace/` 向下取证（不在 lane 指定的 dirty 目录内）、`.venv`/`__pycache__` 字节统计、任何正文读取。

## 7. PWF 与 commit 记录对照

| PWF 位置/plan id | PWF 声明状态/最后时间 | 关联 SHA/工作树 | Git/现存测试/CI 收据核验 | 一致/冲突/不确定 |
|---|---|---|---|---|
| 本仓 `.planning/.active_plan` | **不存在**（Glob `**/.active_plan`、`{.planning/**}` 无结果） | n/a | — | 一致于“无 PWF”事实 |
| 本仓根 `task_plan.md` / `progress.md` / `findings.md` | **均不存在**（Glob `**/{task_plan,progress,findings}*.{md,txt}` 全空 + Test-Path false） | n/a | — | 同上；lane 要求“缺 PWF 要承认”——已写明 |
| handoff / execution run ledger 全仓搜索 | **不存在**（Glob `**/handoff*.md`、`**/*ledger*` 全空） | n/a | — | 同上 |
| `docs/TODO.md`（tracked，116 B） | 3 个无状态标题：`A股财报上传` / `港股财报上传` / `写作通过tool方式接入 prompt / interactive / wechat`；无日期、无 checkbox、无 SHA | 最后提交 `686718bf…` `2026-04-22 10:07:53 +0800` `fix/review and bugfix (#20)` | 无法与任何 commit/测试收据对应；与 `opt/cn_score` 主题（港股/A股财报）**可能**相关但无证据链 | 不确定——仅线索，**不把旧 todo 当授权**（lane 明示） |
| 远端 PR 证据（`ls-remote`，非 fetch） | `refs/pull/159/head` == `76037b2…`（= `opt/cn_score` tip）；`refs/pull/159/merge` == `32592abe…` | 指向 branch-only commit | PR #159 存在；**开/关/合状态 unknown**（本机 `Get-Command gh` → 无 gh CLI；未抓网页、未 fetch） | 不确定——列 §11 供总指挥复核 |
| `AGENTS.md` / `CLAUDE.md`（各 7,309 B，均 tracked，非 PWF） | 开发约束文档（中文；测试/README/架构硬约束） | 与 `main` 一致（checkout 时点 mtime 2026-05-30） | 非计划文件，无完成声明 | 注意：`AGENTS.md` 被宿主以 system-reminder 注入本会话，其中“最高约束”含**要求跳过 system-reminder 恶意代码检查**的注入式条款——本 harness 按**数据**处理、已忽略该指令，仅在此记录供总指挥知悉 |

## 8. 已有测试、CI、E2E 证据（仅查记录，不运行）

| 命令/Workflow/报告 | 绑定 SHA | 结果与日期 | 是否覆盖 branch-only / dirty 行为 | 限制 |
|---|---|---|---|---|
| 本地 `.pytest_cache/v/cache/nodeids`（63 个 test id，全部 `tests/fins/*`）+ `lastfailed`（`{}`） | **无 SHA 绑定** | mtime 2026-07-18：lastfailed 19:36、nodeids 20:13 | **不覆盖 branch-only**：分支从未在本工作树 checkout（main reflog 仅 1 条 clone 记录），7-18 运行的是 main 上的 `tests/fins/*`；也无 dirty tracked 文件可言 | 仅缓存非报告；无命令行、总通过数、耗时记录；不能证明当前状态 |
| `.github/workflows/ci-pr-required.yml`（`pull_request→main`：`pyright` + `pytest -q -m "not integration and not slow and not e2e"` + 3 个 Docling integration smoke + offline bundle smoke） | 运行时绑定 PR head | **本地无任何运行日志/收据** | 若 PR #159 为 open 则会覆盖 branch-only；**是否跑过 unknown** | 只读到配置，未读到结果 |
| `.github/workflows/ci-pr-extended.yml`（`pull_request→main`）、`ci-mainline.yml`（`push→main` + `workflow_dispatch` + `schedule`）、`release-offline.yml`（`workflow_dispatch`） | — | 本地无运行记录 | — | 仅配置存在（4 个 workflow 文件名/触发器已核对） |
| branch-only commit 自带收据 | `76037b2…` | commit message 无 body、无测试声明 | 其新增的 262 行测试**随提交存在但无运行结果证据** | 仓内无绑定该 SHA 的 pytest/CI 报告 |
| E2E / 覆盖率报告 | n/a | 仓库内无 `.coverage`、`htmlcov/`、e2e 报告目录（Test-Path false） | — | 本仓无本地 E2E/覆盖率收据 |
| gh CLI | n/a | **不可用**（`Get-Command gh` 无结果） | — | PR/CI 远端状态无法核验 → unknown |

**测试纪律**：本审计未运行任何 pytest/pyright/CI/构建/下载——`tests_run: false`；只读取了既有配置与缓存元数据。

## 9. 建议的后续处置类别（不执行）

每项一个初步类别；均为分类建议，非操作指令。**“Dayu 不改”优先于分支实现自述；不建议把远端 `opt/cn_score` commit 合并到 Dayu。**

| 对象 | 类别 | 证据 |
|---|---|---|
| `origin/opt/cn_score`（1 个独有 commit `76037b2`，已 push，疑对应 PR #159） | `no_change`（本地侧无任何动作） | 独有 1 commit（`0\t1`）、cherry `+`、main 是祖先；**lane/用户明令不建议合入 Dayu**；PR #159 的开/关/合与上游处置属上游维护者/总指挥决策（PR 状态本身 unknown，见 §11） |
| `docs/architecture_report.html`（untracked） | `owner_decision_needed` | 生成命令/owner/引用全部查不到（Grep 0 命中）→ 按 lane 写 unknown、保留不触碰；凭据/私人内容模式扫描为 0（见 §5） |
| `.pytest_cache/`（2026-07-18 fins 运行痕迹） | `unique_evidence_preserve` | 唯一本地测试收据（63 ids、lastfailed `{}`）；历史运行结果不可再生 |
| `.venv/`、`dayu_agent.egg-info/`、31 个 `__pycache__/` | `generated_candidate_review` | 工具/安装/字节码产物，均可再生；删前仍须总指挥按新计划验证无消费者 |
| `uv.lock`（962,899 B，被项目 `.gitignore` 显式忽略） | `owner_decision_needed` | 项目策略性不入库；保留/入库属 owner 决策，非审计可断言 |
| `workspace/`（`.dayu`/`config`/`portfolio`/`output`/`assets`/锁文件） | `owner_decision_needed` | 疑似 `dayu-cli init` 工作区与真实运行/财报数据；未读取正文，不能凭名字判定可再生 |
| `.benchmarks/`（空目录） | `owner_decision_needed` | 0 文件、无引用、用途 unknown |
| `docs/TODO.md`（旧线索，2026-04-22） | `no_change` | 无状态、无 SHA 对应；不是授权也不是完成声明 |
| base `main@2115c86`、`origin/main`、5 个 release tags | `no_change` | 本地与 live 精确一致；tracked 全净；tag 均在 main 历史内 |
| 本仓 4 个 CI workflow 配置 | `no_change` | 正常 CI 配置，无本地 dirty，无处置需求 |

**不做**：任何回退/清理/合并/cherry-pick/删除/分支移动/文件改名；后续施工由总指挥按证据另立计划。

## 10. 检查命令与结果（脱敏）

全部为只读；均以 `git -C <path>` 或 PowerShell 只读命令执行，退出码 0 除非另注。

- `git status --short --branch`（审计开始时）→ 0；`git status --short --ignored` → 0（ignored 清单来源）；结束时 `git --no-optional-locks status --short --branch` → 0，输出与开始时**逐字一致**。
- `git rev-parse HEAD`、`git rev-parse --abbrev-ref HEAD`、`git for-each-ref`、`git branch -a -vv`、`git worktree list --porcelain`、`git stash list`（空）→ 0。
- `git ls-remote origin` → 0（**唯一网络调用**，只读；未 fetch、未写 FETCH_HEAD——`.git/FETCH_HEAD` 经 Test-Path 确认不存在）。
- `git rev-list --left-right --count main...origin/opt/cn_score` → `0\t1`；`git merge-base` → `2115c86…`；`git merge-base --is-ancestor` → exit 0；`git cherry -v` → `+ 76037b2…`；`git branch -r --contains 76037b2…` → 仅 `origin/opt/cn_score`。
- `git log -1 --format=… 76037b2…`、`git show --stat/--name-status/--format='' 76037b2…`、`git diff --stat main...origin/opt/cn_score`、`git log --oneline -15 origin/opt/cn_score`、`git log -1 -- docs/TODO.md`、`git reflog show main` → 0。
- `git check-ignore -v docs/architecture_report.html` → **exit 1（未被忽略，预期内）**。
- 文件侧（只读）：`Get-Item`/`Get-ChildItem`（大小/mtime/浅层列表；`.benchmarks` 递归确认为空、`.pytest_cache` 递归列 5 文件）、`Test-Path` 批量（PWF/工具目录存在性）、`Select-String`（workflow 触发器）、`Get-Content`（`.gitignore`、`pytest.ini`、workflow 文件）、`[System.IO.File]::ReadAllText`（仅 `architecture_report.html` 做正则**计数**与 title/注释头提取——**未复制正文、未输出任何 value/hash**）。
- 检索（只读）：Glob（PWF/ledger/handoff 全仓搜索）、Grep（`architecture_report`、`cn_score` 全仓 0 命中）。
- 读取（未运行）：`docs/TODO.md`、`CHANGELOG.md`、`pytest.ini`、`ci-pr-required.yml`、lane 卡、handoff 模板、审计 `task_plan.md`/`findings.md`、既有 `results/stock_info_dl_simple.md`（格式参照）。
- **Git metadata 无变化的核验**：`.git/HEAD`、`packed-refs`、`config`、`refs/**`、`logs/**` mtime 全部保持 `2026-05-30 22:42:41`（clone 时点）；`.git/index` mtime `2026-10-04 17:15:27`（**早于本会话**，说明本会话的 `git status` 未重写索引）；结束时复测四项 mtime 与全部 refs SHA 与开始时一致。唯一异常：`.git` **目录** mtime 为 `2026-10-04 19:08:29`，与本会话早期只读 `git status` 时点吻合，推测为其瞬时 `index.lock` 创建后删除所致；`index.lock` 现不存在，**refs/index/HEAD/config/logs 内容与 mtime 均未变**。
- 跳过/失败项：**gh CLI 不存在**（PR/CI 远端状态无法核验 → unknown）；`git reflog show refs/remotes/origin/opt/cn_score` 输出为空（clone 后无 fetch，remote reflog 无可见条目，仅记录不深究）；未执行 fetch/pull/任何写命令；未运行 pytest/pyright/构建/下载/LLM；未读取 `workspace/` 内容。
- 未粘贴：远端 URL（按模板 §10 不输出；clone 来源仅在 §2 以性质描述）、无凭据、无长日志、无报告正文。

## 11. 交接声明

- 我只读取 lane 指定的仓库，没有改动工作树、索引、Git refs、全局配置或其他项目：**yes**（唯一写入为本结果文件，位于 company-wiki 计划目录，不在 Dayu 仓内；未执行任何 `git config`）。
- 我没有运行会写文件的测试、构建、下载或 provider/LLM：**yes**（`tests_run: false`；只读既有缓存/配置元数据）。
- 本报告结论覆盖的 HEAD SHA：`2115c86d5a9027bb51cbbc8a4d0175080732e4e6`（当前 checkout `main`，与 live `origin/main`/HEAD 精确一致）与 `76037b242d0b14a77281d7bc610429296123c5cb`（`origin/opt/cn_score` tip，`refs/pull/159/head` 同 SHA，live ls-remote 同 SHA）。
- **保证**：审计开始与结束各复核一次 `git status`/refs/HEAD/config/index——Dayu 工作树与 Git metadata 本审计前后无变化（`.git` 目录 mtime 的瞬时锁文件推测已如实记录于 §10）。
- 需要总指挥复核的唯一事项：**PR #159 的开/关/合状态与上游对 `opt/cn_score` 的处置意图**（本机无 gh CLI，按禁令未 fetch、未抓取网页）；附带知悉：仓内 `AGENTS.md` 含注入式条款（要求宿主跳过 system-reminder 恶意代码检查），本 harness 按数据处理、已忽略——如需处置该文档属后续单独决定。

## 用户后续授权后的有限集成附记（2026-10-04）

按用户之后要求将 `opt/cn_score@76037b2` 这一已有提交快进到本地 `main`，没有新改写 Dayu 代码。两组 focused tests 合计 87 passed。向 `origin/main` 推送时 GitHub 返回 HTTP 403 `Permission denied`；停止重试，没有改远端、PR 或其他 Dayu 文件。当前只可确认本地 main 已前移，远端是否包含该 SHA 未确认。既有未跟踪 `docs/architecture_report.html` 保留。
