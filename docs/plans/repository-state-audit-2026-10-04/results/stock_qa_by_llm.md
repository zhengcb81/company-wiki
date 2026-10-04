# Repository State Audit — StockQAbyLLM 只读交接报告

## 0. 审计元信息（必填）

```yaml
audit_id: "RSA-StockQAbyLLM-20261004"
repository: "StockQAbyLLM"
repository_root: "C:\Users\郑曾波\Projects\StockQAbyLLM"
audit_status: "complete"
started_at_local: "2026-10-04 20:30 +01:00"
finished_at_local: "2026-10-04 20:46 +01:00"
current_branch: "master"
current_head: "5fdcc2c51a6fa959cdae6504aa4e7c67e9709d5e"
base_ref: "refs/heads/master"
base_sha: "5fdcc2c51a6fa959cdae6504aa4e7c67e9709d5e"
remote_live_check: "ls-remote success"
remote_checked_at: "2026-10-04 20:35 +01:00"
source_changes_made: false
tests_run: false
```

审计边界遵守情况：未 fetch、未运行任何测试/脚本/LLM/provider/安装工具、未写入仓库/工作树/refs/index。`pilot_runs/`、`.workbuddy-ai/`、`llm_apis.json`、`eval_results.json` 等敏感正文未读取；仅记录路径、文件名、计数、大小与时间戳。`eval_results.json` 实际不存在（`Test-Path` = false）。

---

## 1. 一页结论

- **branch-only commits 相对什么 base：** 相对 live `origin/master`（=本地 master，同为 `5fdcc2c`）：**0 个**。相对本地 `origin/gh-pages` 跟踪引用：`git rev-list --left-right --count master...origin/gh-pages` = **`22 2`**（左列 22 = master 全部历史独有；右列 2 = gh-pages 孤儿历史独有的 2 个 deploy commit）。gh-pages 与 master **无共同祖先**（`git merge-base` 无输出），不构成开发支线欠合。
- **tracked staged / unstaged 文件：** **0 / 0**。`git status --short --branch` 只有 `??` 行，无 `A/M/D` 与 unstaged 修改；审计窗口首末两次 status 一致。
- **untracked / ignored candidate（按目录汇总）：** untracked 顶层条目 **7 项**：`.codegraph/`、`.workbuddy-ai/`、`nul`、`pilot_runs/b2a_2026-10-03/`、`pilot_runs/g2b_alphabet_2026-10-04/`、`pilot_runs/l02_2026-10-04/`、`progress_update.txt`。另有 **完全 ignored、status 不可见** 的 `pilot_runs/g2b_c_alphabet_2026-10-04/`（4 个 .json，被 `.gitignore:89 *.json` 整目录吞掉）。各目录内还有大量 ignored 子项（`llm_apis.json` 副本、`logs/`、`out/`、`rejected_*`、`run-log.json` 等），见 §6。
- **linked worktrees：** **1 个**（主 checkout），clean（tracked 层面），非 detached，无 stale/用途不明 worktree；无 stash。
- **PWF 与 Git 的差异：** 本仓根 PWF（task_plan/progress/findings，内容停在 2026-03-24 的 Phase 10-15，全部 pending）**严重滞后于 Git**——Git 在 2026-10-02/03 有 Q02/Q04/Q05/decision-7a/L01-pilot 等 10+ 个功能与回执提交，根 PWF 完全未记录；反之无“PWF 称完成而 Git 未合”的反向差异（根 PWF 没有任何 complete 声明与这些工作对应）。IQS Phase 68-71 PWF（跨项目，未读取原仓）按 lane 卡提示提到这些 pilot 产物；本仓侧核验：4 个 pilot 目录存在，但**全部未提交**，仓内无任何文本引用或保留规则。
- **最大未决项：** ① `pilot_runs/l02_2026-10-04` 在审计期间**仍在实时写入**（文件数 53→64，最新 mtime 20:44:51，审计结束 20:46），疑似有活的 LLM 运行，任何处置必须等 owner 确认运行结束；② b2a/g2b/g2b_c/l02 四个 run 目录为本机**唯一**回执/验收证据（未提交、无 hash manifest、无保留规则）；③ 本地 `origin/gh-pages` 跟踪引用已过期（本地 b559f49，live 24950b3），live tip 对象不在本地，禁止 fetch 下无法核验。

---

## 2. 主线与远端识别

| 线索 | ref/值 | SHA/结果 | 证据命令/文件 | 解释 |
|---|---|---|---|---|
| `origin/HEAD` | `refs/remotes/origin/HEAD` → `origin/master` | `5fdcc2c51a6fa959cdae6504aa4e7c67e9709d5e` | `git rev-parse origin/HEAD` | 服务端/配置的默认线即 master |
| 本地目标主线 | `refs/heads/master` | `5fdcc2c51a6fa959cdae6504aa4e7c67e9709d5e` | `git rev-parse HEAD` / `git symbolic-ref -q HEAD` | 当前 checkout 所在分支 |
| live remote `ls-remote` | `refs/heads/master` | `5fdcc2c…9d5e`（与本地相同） | `git ls-remote --heads origin master gh-pages`（exit 0，未 fetch） | 本地 master 与 live 完全一致，无 ahead/behind |
| live remote `ls-remote` | `refs/heads/gh-pages` | `24950b3df0caaebeea5f01ae6ee314056474abab` | 同上 | live gh-pages 比本地跟踪引用新 |
| 工作 checkout | `master` | `5fdcc2c…9d5e` | `git status --short --branch` → `## master...origin/master` | `origin/master` 跟踪引用与 live 相同 → **master 跟踪引用未过期** |

- **remote-tracking refs 过期判定：** `refs/remotes/origin/gh-pages` = `b559f49`，而 live = `24950b3`（`git cat-file -e 24950b3…` exit 1，**对象不在本地**）→ `origin/gh-pages` 跟踪引用**已过期**；按约束未运行 fetch 刷新，live tip 的 commit 数/内容 = unknown。`origin/master` 与 live 相同，未过期。
- 远端 origin 为 GitHub https 地址（按模板不粘贴 URL）。`gh` CLI 本机不可用，未查询 Actions 运行记录。

---

## 3. Branch 矩阵

本仓本地分支仅 `master`；远端跟踪分支仅 `origin/master`、`origin/gh-pages`（+`origin/HEAD` 符号引用）。无 stash、无 tags、`git for-each-ref` 仅返回 4 条 ref。master 即 base（见 §2），下表列出唯一非主线分支：

| branch ref | tip SHA | merge-base | base-only commits | branch-only commits | patch-equivalent/ cherry | diff stat | PWF/交接关联 | 当前判断 |
|---|---|---|---:|---:|---|---|---|---|
| `refs/remotes/origin/gh-pages`（本地跟踪，**过期**） | `b559f4914464b832b53dd31a1f47ec6bf5a93eac` | **无**（`git merge-base master origin/gh-pages` 无输出，exit 1；孤儿/无关历史） | 22 | 2 | `git cherry -v master origin/gh-pages` → `+ e58a73c`、`+ b559f49`（两 deploy commit 的 patch 均不在 master） | `git diff --stat master...origin/gh-pages` → exit 128 `fatal: no merge base`；改用两点 `git diff --stat master origin/gh-pages` → 267 files, +61323/−55800（master 源码树 vs gh-pages 站点树的整树对比，非增量） | 与 `.github/workflows/docs.yml` 的 `peaceiris/actions-gh-pages@v3`（`publish_dir: ./site`）一一对应 | **deploy 分支，非开发支线**；“2 个 branch-only commits” 是 deploy 工件，不欠合 |

branch-only commit 明细（代码/测试/计划/唯一证据计数 = 0/0/0/0，全部为部署工件）：

| SHA | 标题 | 作者日期 | 改变路径 | 类型 |
|---|---|---|---|---|
| `e58a73c07a73af671a47e1abb9d86175828c206d`（孤儿根） | `deploy: 9da338b24c547efc9f2dd05839f2eb2c09e3700b` | zhengcb81, 2026-09-04 19:27:17 +0000 | 69 files, +61319（mkdocs 产物：`*.html`、`assets/`、`search/search_index.json`、`sitemap.xml`、`.nojekyll`、`objects.inv` 等） | 部署工件 |
| `b559f4914464b832b53dd31a1f47ec6bf5a93eac` | `deploy: bbbdadc1ac902a29658228f3ca527861dd6646d7` | zhengcb81, 2026-09-04 19:36:47 +0000 | 3 files: `api/providers/index.html`、`api/utils/index.html`、`search/search_index.json`（+28/−24） | 部署工件 |

- `git rev-list --left-right --count master...origin/gh-pages` 原始结果：`22	2` —— 左列 22 = 仅 master 可达（即 master 全部 22 个 commit，因无共同祖先全属“base-only”）；右列 2 = 仅 gh-pages 可达（上表两个 deploy commit）。
- live gh-pages = `24950b3`（本地无此对象）→ live 至少还有 1 个未见的 deploy commit，内容 unknown。
- **不在审计中合并/cherry-pick/删除/移动任何分支。**

---

## 4. Worktree 矩阵

| worktree path | branch/detached | HEAD SHA | porcelain 状态 | PWF/owner/创建来源 | 可能用途 | 确定度 |
|---|---|---|---|---|---|---|
| `C:/Users/郑曾波/Projects/StockQAbyLLM` | `master`（跟踪 `origin/master`） | `5fdcc2c51a6fa959cdae6504aa4e7c67e9709d5e` | clean（tracked staged=0/unstaged=0）+ 7 项 untracked 顶层条目 + 多项 ignored | 本仓唯一 owner checkout；HEAD reflog 末 3 条均为正常 commit（decision-7a / pilot F8 / pilot F4），无 reset/checkout 异常 | 主开发与运行目录（pilot 运行在此工作树内进行） | 高（`git worktree list` 仅此 1 行） |

无 linked/detached/临时 review worktree；无 stash（`git stash list` 空）。不存在已失效的 worktree 路径，故无 prune/remove 需求记录。

---

## 5. 当前未提交文件

**staged：0；unstaged（tracked 修改）：0。** 以下全部为 untracked（`git status --short` 原样）：

| 路径 | Git 状态 | staged diff | unstaged diff | 类型/可能用途 | PWF/commit/调用者证据 | 敏感性 | 推荐后续分类 |
|---|---|---|---|---|---|---|---|
| `.codegraph/` | `??`（内部 `codegraph.db/-shm/-wal/config.json` 为 ignored，自带 .gitignore） | 无 | 无 | 环境：CodeGraph 代码索引（5 文件，10.6 MB，2026-09-19→10-01） | 本机开发工具产物；无 PWF 引用 | 低（可再生索引） | `generated_candidate_review` |
| `.workbuddy-ai/` | `??`（未被 ignore 规则覆盖） | 无 | 无 | 环境/草案：agent memory（`memory/MEMORY.md` 1668B、`memory/2026-09-20.md` 4201B，均为 2026-09-20） | 无 PWF/commit 引用；按 lane 未读正文 | 中（可能含用户/agent 笔记文本） | `owner_decision_needed` |
| `nul` | `??` | 无 | 无 | 环境噪声：0 字节文件，2026-10-01 21:09（Windows 保留设备名，`Get-Item` 无法按常规路径打开，大小/时间取自目录列表） | 疑似 `> nul` 式重定向误建；无任何引用 | 低 | `generated_candidate_review` |
| `pilot_runs/b2a_2026-10-03/` | `??`（目录内多数 .json/logs/out/rejected_* 为 ignored） | 无 | 无 | LLM 运行输出+回执（334 文件，11.46 MB） | 本仓 PWF 无引用；IQS Phase 68-71 据 lane 提及（跨项目，未核验原文） | 高：含 `llm_apis.json` 副本（未读）、真实模型/研究文本（未读） | `unique_evidence_preserve` |
| `pilot_runs/g2b_alphabet_2026-10-04/` | `??`（2 个 .json ignored，`import-stderr.txt` 可见） | 无 | 无 | LLM 运行回执（3 文件，5411B，10:09） | 文件名含 `import-receipt`；仓内无其他引用 | 中：json 含运行正文（未读） | `unique_evidence_preserve` |
| `pilot_runs/l02_2026-10-04/` | `??`（内部 json/logs/out/rejected 等 ignored） | 无 | 无 | LLM 运行输出，**审计时仍在写入**（19:00→20:44，53→64 文件，≥14.7 MB） | 本仓 PWF 无引用；IQS 侧引用未核验 | 高：`llm_apis.json` 副本+运行正文（未读） | `preserve_active_work` |
| `progress_update.txt` | `??` | 无 | 无 | 草案/陈旧进度笔记（1005B，2026-02-12，按约束未打开正文） | 与根 progress.md（2026-03-24）不衔接 | 低-中 | `owner_decision_needed` |

**status 不可见但实际存在的 ignored 条目**（`git status --ignored` 核出，正文未读）：

| 路径 | 状态 | 说明 | 敏感性 |
|---|---|---|---|
| `pilot_runs/g2b_c_alphabet_2026-10-04/` | `!!`（整目录被 `*.json` 规则忽略，普通 status 完全不可见） | 4 个 .json（4185B，16:45-16:46），文件名含 `alphabet_subject_draft/signed(.provenance).json`，即带 `decision_ref: owner-2026-10-04-g2b-c-alphabet-signoff` 的草案+签署件 | 高：签署/决策回执（未读正文） |
| `pilot_runs/{b2a,l01,l02}/llm_apis.json`、根 `llm_apis.json`（1544B, 2026-09-04） | `!!` | API 配置副本存在于 3 个 run 目录 + 根目录（`llm_apis.json.example` 为 tracked 模板） | **极高（疑含 API key）：仅记录存在，未读取/未哈希** |
| `pilot_runs/{b2a,l01,l02}/{logs/,out/,run-log.json,questions_*.json,…}`、`pilot_runs/b2a_2026-10-03/rejected_*`（5 个被拒子目录） | `!!` | 被拒/覆盖/重排批次与日志、运行清单（文件名级识别） | 高（真实运行文本，未读） |
| 根 `q04_handoff.json`（14253B, 2026-10-02 10:55）、`config.json`（7706B, 2026-01-04） | `!!` | Q04 交接回执 / 本机配置 | 中（交接件未读） |

---

## 6. 未跟踪/ignored 工件及空间线索

（计数/字节/时间 = 只读元数据；无任何 manifest/hash 文件按文件名发现，故“哈希是否已有 manifest”列均为 **无**。）

| 目录/文件 | Git 状态 | 文件数/总字节 | 创建/消费证据 | 是否唯一审查/测试证据 | 可再生证据 | 结论/未决 |
|---|---|---:|---|---|---|---|
| `pilot_runs/l01_2026-10-02/` | **tracked 干净**（18 文件已提交；ignored：`llm_apis.json`、`logs/`） | 盘上 20 文件 / 370,430 B（03 03:30→04:22） | commit `7a40a98`（L01 pilot package）+ `a8650c0/cea6efc/1f04a8f`（报告修订）；含 tracked `pilot-report.md`、`run-log.json`、`_score-rows.json` | **回执链已入 Git**（例外：run 正文 .json 是否全部入库以 ls-files 18 件为准，logs/ 与 key 副本未入库） | 否（真实 10 公司真实搜索运行） | 代码/回执类；已是线内证据，`no_change`（ignored 部分除外） |
| `pilot_runs/b2a_2026-10-03/` | `??` + 大量 ignored 子项 | 334 文件 / 11,459,750 B（10-04 01:32→08:53） | `runner.py`、`run-log.json`、`budget-final.json`、`stratification-{draft,final}.{md,json}`、`out/`、`logs/`；5 个 `rejected_*` 被拒批次子目录 | **是（本机唯一）**：无任何 commit/PWF 引用，未提交即丢失无副本 | 否（真实 API 运行，含被拒批次） | **唯一证据→preserve**；被拒/草案/正式层级需 owner 归档判定；含 key 副本需隔离 |
| `pilot_runs/g2b_alphabet_2026-10-04/` | `??`（2 json ignored） | 3 文件 / 5,411 B（10-04 10:09） | `alphabet_payload.json`、`import-receipt.json`、`import-stderr.txt`（输入+回执+stderr 三件套） | 是 | 否（导入运行） | `unique_evidence_preserve` |
| `pilot_runs/g2b_c_alphabet_2026-10-04/` | **`!!` 整目录 ignored，status 不可见** | 4 文件 / 4,185 B（10-04 16:45-16:46） | `alphabet_subject_draft/signed(.provenance).json`，`decision_ref: owner-2026-10-04-g2b-c-alphabet-signoff` | **是（签署决策回执，唯一）** | 否 | `unique_evidence_preserve`；**“不可见”本身是未决风险** |
| `pilot_runs/l02_2026-10-04/` | `??` + 大量 ignored | 审计中 53→64 文件 / ≥14,735,528 B（10-04 19:00→**20:44:51 仍在增长**） | `runner.py`、`run-log.json`、`companies.json`、约 39 个 `questions_*` 分层文件、`repeat_subset.json`、`out/`、`logs/` | 是（且为**进行中的唯一捕获**） | 否 | **`preserve_active_work`：运行疑似进行中，禁止任何清理动作** |
| `.codegraph/` | `??`（db/config ignored） | 5 文件 / 10,633,481 B（09-19→10-01 19:22） | CodeGraph 工具（`.codegraph/` 惯例 + 本机 CLAUDE.md 约定） | 否 | 是（重建索引） | `generated_candidate_review` |
| `.workbuddy-ai/` | `??` | 2 文件 / 5,869 B（均 2026-09-20） | agent 记忆目录 | 否（对仓库审计而言） | 否（笔记类） | `owner_decision_needed`（正文未读） |
| `progress_update.txt` | `??` | 1005 B（2026-02-12） | 陈旧进度笔记（文件名推断，正文未读） | 可能已被 progress.md 取代 → 不确定 | 否 | `owner_decision_needed` |
| `nul` | `??` | 0 B（2026-10-01 21:09） | 疑似 shell 重定向误建 | 否 | 是（空物） | `generated_candidate_review` |
| `pilot_runs/l01_2026-10-02/llm_apis.json`、`b2a/…/llm_apis.json`、`l02/…/llm_apis.json`、根 `llm_apis.json` | `!!` | 存在（大小未逐个测量，未读取） | 运行需要 key 配置的本机副本 | — | — | **敏感残留：仅登记存在，处置需 owner 单独计划** |
| `q04_handoff.json`（根） | `!!` | 14,253 B（2026-10-02 10:55） | Q04 功能交接（对应 commit `fe11f63` 一带） | 可能与 IQS 侧交接镜像 → 不确定 | 否 | `unique_evidence_preserve`（若镜像不存在则升级为唯一） |
| `htmlcov/` | ignored（`.gitignore:107`） | 56 文件 / 5,049,946 B（max 10-03 22:39） | pytest-cov HTML 输出，与 HEAD 提交时间（22:35:29）仅隔 4 分钟 | 本地测试证据（SHA 绑定无 manifest，见 §8） | 是（重跑测试） | `generated_candidate_review` |
| `coverage.xml`、`.coverage`、`bandit-report.json`（根，均 ignored） | `!!` | 227,756 / 53,248 / 16,377 B（10-03 22:36-22:39） | 同上一窗；bandit 对应 security 扫描 | 同上 | 是 | `generated_candidate_review` |
| `coverage.json`（根，ignored） | `!!` | 175,803 B（2026-02-12） | 陈旧覆盖率快照 | 否 | 是 | `generated_candidate_review` |
| `logs/`（根，ignored） | `!!` | 24 文件 / 77,799,288 B（max 10-04 01:37，落在 b2a 运行时段） | 日志；消费者未知（未深读） | 可能含运行日志 → 不确定 | 部分 | `owner_decision_needed`（77.8 MB，是本仓最大单目录之一） |
| `outputs/`（根，ignored） | `!!` | 174 文件 / 20,748,993 B（max 2026-01-11） | 旧输出 | 否 | 是（多为生成物） | `generated_candidate_review` |
| `reports/`（根，ignored） | `!!` | 47 文件 / 566,229 B（max 2026-02-11） | 旧报告 | 否 | 是 | `generated_candidate_review` |
| `site/`（根，ignored） | `!!` | 69 文件 / 5,080,787 B（max 2026-09-04 20:18，与 gh-pages deploy 同日） | `mkdocs build` 输出（docs.yml 消费 `./site`） | 否 | 是（mkdocs build） | `generated_candidate_review` |
| `.benchmarks/`、`testsbenchmarks/`（根） | 不出现在 status（**空目录**，0 文件） | 0 / 0（2026-02-12） | 空壳残留 | 否 | — | `generated_candidate_review` |
| `.mypy_cache/`、`.pytest_cache/`、`.ruff_cache/`、`__pycache__/`、`htmlcov` 等标准缓存 | 均不出现在 status（按 ignored 记录；未逐条跑 check-ignore，未深入测量） | 未测量 | 工具缓存 | 否 | 是 | `generated_candidate_review` |
| `eval_results.json` | **不存在**（`Test-Path` = false；`.gitignore:89` 仍可匹配其名） | — | — | — | — | `no_change`（无此项） |

**保留规则：** 全仓 md 检索（`保留/清理/retention/删除` + `pilot_runs` 全文）未发现任何针对 pilot 运行目录/回执的保留或清理规则；`pilot_runs` 字样在本仓所有 .md/.py/.yml 中**仅出现在 run 目录自身内部**。→ 结论：本仓**没有**明文保留规则；b2a/g2b/g2b_c/l02 的处置完全依赖 IQS 侧（跨项目）与 owner 裁定。

---

## 7. PWF 与 commit 记录对照

计划入口核查：仓内与 PWF 相关的文件只有根 `task_plan.md`、`progress.md`、`findings.md`（三者均 tracked、clean）、`docs/IMPLEMENTATION_PLAN.md`（2026-01-04，旧）、根 `q04_handoff.json`（ignored）、`.workbuddy-ai/memory/*`（agent 记忆，非计划）、`progress_update.txt`（2026-02-12）。**未发现** active plan selector 文件或 execution run ledger；按 planning-with-files 惯例，根 `task_plan.md` 是 PWF 计划入口，但其内容已冻结。

| PWF 位置/plan id | PWF 声明状态/最后时间 | 关联 SHA/工作树 | Git/现存测试/CI 收据核验 | 一致/冲突/不确定 |
|---|---|---|---|---|
| 根 `task_plan.md`（Phase 10-13 计划，Current Phase = Phase 10 pending） | 内容日期 2026-03-24；文件 mtime/最后 commit `11ff34e` 2026-09-04（行尾规范化，非内容更新） | 无关联 SHA；同工作树 | 无任何 commit/收据与 “Phase 10 pending” 对应 | **冲突（滞后）**：Git 已有 2026-10-02/03 的 q02/q04/q05/decision-7a/L01 共 10+ 提交，PWF 零记录 |
| 根 `progress.md` | “最后更新 2026-03-24（Phase 10-15 计划创建）”；21 子任务 0/21 | 无 | 同上 | **冲突（滞后）**，同上 |
| 根 `findings.md` | “最后更新 2026-03-24（Phase 10-15）” | 无 | 同上 | **冲突（滞后）**，同上 |
| IQS Phase 68/69/70/71 PWF（跨项目，按 lane 不访问原仓） | lane 卡声明其 PWF/进度提到 b2a/g2b/l02 等运行产物 | 本仓侧：4 个 pilot 目录路径**全部存在** | 本仓内无引用文本、无 SHA/manifest 对照；runs 未提交 | **不确定**：本仓侧只能证明“产物在且唯一”；引用原文与验收结论需 IQS 侧复核 |
| `q04_handoff.json`（2026-10-02） | Q04 功能交接（对应 `fe11f63` Q04 ordered model policy 提交时段） | 工作树 ignored 文件 | 未提交；与 commit 时段吻合（间接） | 不确定（镜像是否存在于 IQS 侧 unknown） |
| `pilot_runs/l01_2026-10-02/pilot-report.md`（tracked） | 报告经 3 个修订 commit（`a8650c0/cea6efc/1f04a8f`，2026-10-03） | `master@5fdcc2c` 系列 | 与 Git 完全一致 | **一致**（本仓唯一被 Git 记录的 pilot 验收报告） |
| `.workbuddy-ai/memory/`（2026-09-20） | agent 记忆快照 | 无 | 无 | 不确定（非 PWF 权威入口，正文未读） |

**Phase 68-71 引用路径/SHA 核对（本仓侧能做的部分）：** lane 已知的 4 个 run 目录（b2a、g2b、g2b_c、l02）路径全部存在；**没有任何一个 run 目录或其报告被提交**；仓内（含 commit message 之外的全部文本）检索不到 Phase 68-71 字样；无 SHA/哈希清单。→ “是否唯一验收/交接证据”：对 b2a/g2b/g2b_c/l02 = **是（本机唯一，且 g2b_c 连 status 都不可见）**；对 l01 = 否（已提交）。“是否有明确保留规则”：**否（仓内无）**。

---

## 8. 已有测试、CI、E2E 证据（仅查记录，不运行）

| 命令/Workflow/报告 | 绑定 SHA | 结果与日期 | 是否覆盖 branch-only / dirty 行为 | 限制 |
|---|---|---|---|---|
| 本地 pytest 产物：`coverage.xml`(227,756B)+`htmlcov/`(56 文件)+`.coverage` | **推定 HEAD `5fdcc2c`，无 manifest 可证**（产物 10-03 22:36-22:39，HEAD commit 22:35:29，相隔 1-4 分钟） | 结果值未读取（覆盖率数字 unknown）；同窗 `bandit-report.json` 16,377B | 覆盖当时工作树（=当前 HEAD，因为此后 tracked 层零改动）；branch-only=0 所以无遗漏分支 | 无 SHA 绑定收据；按约束未读正文 |
| 本地 `coverage.json` | unknown | 2026-02-12 旧快照 | 否（过期） | 未读 |
| `.github/workflows/ci.yml`（tracked） | 配置于 master/main/develop 的 push/PR | `pytest tests/ -v --cov… --cov-fail-under=87` + mypy job + codecov | 设计上覆盖 master push（含 10 个新提交） | **5fdcc2c 的实际运行结果 unknown**：gh CLI 不可用，未调 API；README badge 仍是 `yourusername` 占位（无效） |
| `.github/workflows/docs.yml`（tracked） | push master → `mkdocs build` + `peaceiris/actions-gh-pages@v3`（`publish_dir: ./site`） | 与 gh-pages deploy commit（2026-09-04）机制吻合 | 不涉及 | 证明 gh-pages 为 workflow **输出** |
| `.github/workflows/security.yml`、`release.yml`（tracked） | 配置存在 | 未核验运行记录 | unknown | 同上（无 gh） |
| `tests/live/test_live_quick_scan.py`（tracked，701 行） | 随 `master@5fdcc2c` | E2E 测试代码在位 | 覆盖 live quick-scan 行为（若被触发） | 本次未运行；是否在 CI 中触发未核验 |
| branch-only / dirty 覆盖 | branch-only=0；dirty（untracked pilot 运行） | — | **无任何测试/CI 覆盖 untracked pilot 目录**（它们不属于代码层） | — |

---

## 9. 建议的后续处置类别（不执行）

每个条目只选一个初步类别（依据列于前文各节）：

| 对象 | 类别 | 证据 |
|---|---|---|
| `refs/heads/master` = live `origin/master` | `no_change` | ls-remote 与本地同 SHA；`0 0` 左右计数 |
| `origin/gh-pages`（本地跟踪 b559f49） | `deploy_or_archive_branch` | 孤儿历史、2 个 deploy commit、docs.yml peaceiris 机制、树内容=mkdocs 站点；**跟踪引用过期**属信息项，不构成欠合 |
| 主 worktree | `no_change` | tracked 全干净，HEAD=live mainline |
| `pilot_runs/l01_2026-10-02/`（tracked 部分） | `no_change` | 已入库且经 4 个 commit 修订 |
| `pilot_runs/b2a_2026-10-03/` | `unique_evidence_preserve` | 未提交、无副本、含被拒批次分层与回执；仓内无保留规则 |
| `pilot_runs/g2b_alphabet_2026-10-04/` | `unique_evidence_preserve` | import 回执三件套，未提交 |
| `pilot_runs/g2b_c_alphabet_2026-10-04/` | `unique_evidence_preserve` | owner 签署决策回执；整目录 ignored 不可见 |
| `pilot_runs/l02_2026-10-04/` | `preserve_active_work` | 审计期间文件 53→64、mtime 持续推进至 20:44:51 → 运行疑似进行中 |
| 3× run 目录内 `llm_apis.json` + 根 `llm_apis.json` | `owner_decision_needed` | 疑含 API key 的散落副本；仅登记存在，需单独安全计划 |
| `q04_handoff.json` | `unique_evidence_preserve` | Q04 交接回执，未提交；镜像是否存在 unknown |
| `.workbuddy-ai/`、`progress_update.txt`、`logs/` | `owner_decision_needed` | 归属/正文/消费者未核验（正文按约束未读） |
| `.codegraph/`、`nul`、`htmlcov/`、`coverage.*`、`bandit-report.json`、`coverage.json`、`outputs/`、`reports/`、`site/`、`.benchmarks/`、`testsbenchmarks/`、`__pycache__` 等缓存 | `generated_candidate_review` | 均有确定生成器/工具；删除前仍需按施工包规则验证消费者 |
| 根 `config.json`、`llm_apis.json`、`.env.example` | `no_change` | 本机运行配置，ignored（模板/示例 tracked）；`dbc458b` 已做历史 key 清理 |
| `eval_results.json` | `no_change` | 文件不存在 |

**未发现任何可归为 `already_in_base` 或 `merge_candidate` 的开发提交**（相对 live 主线 branch-only = 0）。本节不给出任何删除/恢复/合并命令；后续施工由总指挥另开“清理与并线”计划。

---

## 10. 检查命令与结果（脱敏）

| 命令（只读） | 退出码/结果 |
|---|---|
| `git status --short --branch`（审计首、末各一次） | 0；两次一致：`## master...origin/master` + 7 行 `??` |
| `git rev-parse HEAD` / `git symbolic-ref -q HEAD` | 0；`5fdcc2c…9d5e` / `refs/heads/master` |
| `git ls-remote --heads origin master gh-pages` | 0；master=5fdcc2c、gh-pages=24950b3（**未 fetch**） |
| `git rev-parse origin/HEAD`、`git remote -v`、`git for-each-ref`、`git branch -a -v` | 0；4 refs；origin URL 已脱敏不入报告 |
| `git worktree list` / `git stash list` | 0；1 worktree / 空 |
| `git rev-list --left-right --count master...origin/gh-pages` | 0；`22 2` |
| `git rev-list --left-right --count master...origin/master` | 0；`0 0` |
| `git merge-base master origin/gh-pages` | 1；无输出（无共同祖先） |
| `git cat-file -e <live gh-pages sha>` | 1；对象不在本地（live tip 不可核验） |
| `git log --left-right master...origin/gh-pages` / `git cherry -v` / `git show --stat` ×2 | 0；见 §3 |
| `git diff --stat master...origin/gh-pages` | 128；`fatal: no merge base`（按预期，改两点 diff 成功） |
| `git ls-files <各类>` / `git status --short -- <路径>` / `git status --ignored --short -- <路径>` / `git check-ignore -v <路径>` | 0；结果见 §5-§7 |
| `git log -1 --format` / `git log --name-only -8` / `git reflog -3` / `git log -- task_plan.md…` | 0；HEAD 22:35:29+01:00；近 8 commit 无 PWF 文件；reflog 无异常 |
| PowerShell：`Get-ChildItem/Get-Item/Measure-Object` 元数据扫描（pilot_runs、.codegraph、.workbuddy-ai、htmlcov、logs、outputs、reports、site） | 0；仅文件名/计数/字节/时间，未读正文 |
| `Select-String` 全仓检索（pilot_runs/Phase 65-71/保留规则） | 0；结果见 §6-§7（`rg` 本机不可用，已换 PowerShell） |
| `Test-Path eval_results.json` | false |
| `gh` Actions 查询 | **跳过**：gh CLI 本机不可用；未改用 API（避免凭据/网络面扩大） |
| `git fetch` / 测试 / 脚本 / LLM / 安装 | **未执行**（按 lane 禁止） |

失败/勘误记录：初次组合命令因 PowerShell 5.1 不支持 `||` 语法报错（0 影响，改写后重跑）；`git cat-file -e …^{commit}` 的 `^{}` 在 PowerShell 中被吞参（改用裸 SHA 成功）。

---

## 11. 交接声明

- 我只读取 lane 指定的仓库，没有改动工作树、索引、Git refs、全局配置或其他项目：**yes**（写集仅 `results/stock_qa_by_llm.md` 一个文件，位于 company-wiki 施工包内）。
- 我没有运行会写文件的测试、构建、下载或 provider/LLM：**yes**（仅 ls-remote 只读查询远端；未 fetch）。
- 本报告结论覆盖的 HEAD SHA：`5fdcc2c51a6fa959cdae6504aa4e7c67e9709d5e`（审计首末各确认一次，期间未变化；untracked 目录内容变化不影响该结论）。
- 需要总指挥复核的唯一事项：
  1. `pilot_runs/l02_2026-10-04` 在 20:44 仍在写入——先确认运行归属与结束状态，再谈任何处置；
  2. live `gh-pages@24950b3` 比本地跟踪新且对象缺失——需要授权 fetch 才能核验（本 lane 未做）；
  3. `pilot_runs/g2b_c_alphabet_2026-10-04`（签署回执）被 `*.json` 规则整目录吞掉，常规 status 不可见；
  4. 3 个 run 目录内的 `llm_apis.json` 副本（疑含 API key）建议纳入独立安全清理计划；
  5. 根 PWF（Phase 10 全 pending，2026-03-24）与 10 月功能提交完全脱节——权威计划入口需重新指定。

## 总指挥收据（2026-10-04）

本报告已收到并验收。`pilot_runs/l02_2026-10-04` 审计时仍在增长，连同其他唯一运行资料继续保留；疑似 API key 的配置副本未读取，后续若清理必须单独分类。该验收只针对报告和交接格式，不授权清理 StockQAbyLLM 仓库文件，也不处理 IQS 仓库。
