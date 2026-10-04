# MeetingConverter — tracked coverage 文件只读盘点

## 0. 审计元信息（必填）

```yaml
audit_id: "RSA-meetingconverter-20261004"
repository: "MeetingConverter"
repository_root: "C:\Users\郑曾波\Projects\MeetingConverter"
audit_status: "complete"
started_at_local: "2026-10-04 20:33 +01:00 (约)"
finished_at_local: "2026-10-04 20:45 +01:00"
current_branch: "master"
current_head: "3c0b0531637589b3c4b14b83da8e1b3c3e1adf9b"
base_ref: "refs/heads/master"
base_sha: "3c0b0531637589b3c4b14b83da8e1b3c3e1adf9b"
remote_live_check: "ls-remote success"
remote_checked_at: "2026-10-04 20:41 +01:00 (约)"
source_changes_made: false
tests_run: false
```

## 1. 一页结论

- branch-only commits 相对 base：**0**（`git rev-list --left-right --count master...origin/master` → `0	0`；全仓仅 `master` 一条开发线，与 live `origin/master` 同 SHA）。
- tracked staged / unstaged 文件：staged **0**；unstaged **1**（`.coverage`，` M`）。
- untracked / ignored candidate（按目录汇总）：untracked **0**；ignored **6 组**：`output/`、`config.json`、`__pycache__/`（root/core/engines/tests 共 4 处）、`.pytest_cache/`、`.ruff_cache/`、`.mimocode/`；另有空目录 `.benchmarks/`（0 文件，Git 不显示）。
- linked worktrees：**1**（主工作树）；dirty **1**（含 `.coverage` 修改）；detached 0；stale 0；用途不明 0。
- PWF 与 Git 差异：`task_plan.md`（v3）标 Phase 0 **pending**，但 Phase 0 三项已由提交 `ad73843` 实施入库 → **冲突**；HEAD 提交信息称“P0-P6 完成”与文件内 Phase 0 pending / Phase 5 in_progress 自相矛盾 → **冲突**；progress.md 的 v2 计划 P1–P8 完成与 Git 证据一致；Phase 5 in_progress 与 Git 一致（`engines/registry.py` 不存在、无 `pytest.mark.network`）。
- 最大未决项：① tracked 二进制 `.coverage` 的脏版本处置（可再生同类产物，但该次运行数据为工作树独有）；② HEAD 唯一 push CI 运行 0 job 即失败、HEAD 无通过测试收据；③ `task_plan.md` Phase 0/Phase 5 状态与提交信息的矛盾需裁定。

## 2. 主线与远端识别

| 线索 | ref/值 | SHA/结果 | 证据命令/文件 | 解释 |
|---|---|---|---|---|
| `origin/HEAD` | `refs/remotes/origin/HEAD -> refs/remotes/origin/master` | 3c0b053 | `git symbolic-ref refs/remotes/origin/HEAD` | 远端默认线为 master |
| 本地目标主线 | `refs/heads/master` | 3c0b0531637589b3c4b14b83da8e1b3c3e1adf9b | `git branch -vv` / `git for-each-ref` | 唯一本地分支，无 tag、无 stash |
| live remote `ls-remote` | `refs/heads/master`=3c0b053…、`HEAD`=3c0b053…；无 `refs/heads/main` | success | `git ls-remote origin refs/heads/master refs/heads/main HEAD`（exit 0） | 远端（GitHub，URL 不复制）live 值与本地完全一致 |
| 工作 checkout | 分支 `master`，与 `origin/master` 同步 | 3c0b053 | `git status --short --branch` → `## master...origin/master` | 唯一脏文件为 `.coverage` |

remote-tracking 过期判断：`ls-remote` 实测值与 `refs/remotes/origin/master` 值相同 → 检查时刻 tracking ref **不过期**（未执行 fetch，也未刷新任何本地 ref）。

## 3. Branch 矩阵

| branch ref | tip SHA | merge-base | base-only commits | branch-only commits | patch-equivalent/ cherry | diff stat | PWF/交接关联 | 当前判断 |
|---|---|---|---:|---:|---|---|---|---|
| `refs/heads/master`（= `refs/remotes/origin/master`） | 3c0b0531637589b3c4b14b83da8e1b3c3e1adf9b | 3c0b053（与 base 自身相同） | 0 | 0 | 不适用（无独有提交） | 无（工作树相对 HEAD 仅 `.coverage` Bin 53248→53248） | progress/task_plan 记录的全部工作均已入库 | `no_change`（分支本身无需动作） |

原始计数与解释：

- `git rev-list --left-right --count master...origin/master` → `0	0`：左列 = master 独有提交 **0**，右列 = origin/master 独有提交 **0**。
- `git merge-base --is-ancestor origin/master master` exit 0；`git merge-base master origin/master` = 3c0b053。
- 全仓 refs 仅 3 条：`refs/heads/master`、`refs/remotes/origin/HEAD`、`refs/remotes/origin/master`，tips 全为 3c0b053；无 tag、无 stash（`git stash list` 空）。
- branch-only commit SHA/标题/路径计数：**不适用（0 条）**。

## 4. Worktree 矩阵

| worktree path | branch/detached | HEAD SHA | porcelain 状态 | PWF/owner/创建来源 | 可能用途 | 确定度 |
|---|---|---|---|---|---|---|
| `C:/Users/郑曾波/Projects/MeetingConverter` | `master`（非 detached） | 3c0b0531637589b3c4b14b83da8e1b3c3e1adf9b | dirty：staged 0 / unstaged 1（`.coverage`）/ untracked 0 | owner 自有 checkout；配置 `user.name=Zheng Zengbo`（local config） | 主开发/使用工作树 | 高 |

`git worktree list` 仅返回本工作树一条；无 linked/detached/临时路径；未做任何 prune/remove。

## 5. 当前未提交文件

| 路径 | Git 状态 | staged diff | unstaged diff | 类型/可能用途 | PWF/commit/调用者证据 | 敏感性 | 推荐后续分类 |
|---|---|---|---|---|---|---|---|
| `.coverage` | `M`（仅 unstaged；staged 空、无 untracked） | 无 | `Bin 53248 -> 53248 bytes`（同尺寸，不展示内容/哈希） | coverage.py SQLite 数据文件：meta `version=7.12.0`、`has_arcs=0`（只读 URI 打开）；pytest-cov 默认数据产物 | tracked（`git ls-files -s` 显示 mode 100644，blob id 按模板不复制）；入库两次：`8826aed`(07-09 19:25 引入)、`ad73843`(07-09 21:37 更新)；工作树 mtime 2026-07-09 21:59:58，与 `.pytest_cache/v/cache/nodeids`（200 条 node id）同一秒 → 该文件由 07-09 21:59:58 的本地 pytest 运行产生；再生方法有文档/配置证据（见 §6/§8） | 二进制覆盖率：仅报告存在性/状态/大小/时间，不输出内容与哈希 | `generated_candidate_review`（见 §9 注：tracked 入库决策与丢弃该次运行数据须 owner 裁决；**不建议直接删除**） |

## 6. 未跟踪/ignored 工件及空间线索

| 目录/文件 | Git ignored/untracked 状态 | 文件数/总字节 | 创建/消费证据 | 是否唯一审查/测试证据 | 可再生证据 | 结论/未决 |
|---|---|---:|---|---|---|---|
| `output/` | ignored（`.gitignore:45 output/`） | 9 / 57,025 | progress.md「2026-07-09 端到端测试通过」列出同名三音频（DRG/上峰水泥/中密控股），与 9 个产出文件一一对应；源音频在 depth≤2 内未找到，`input/` 不存在 | **是**：真实会议原文 + LLM 翻译产出的唯一现存文本证据（内容未细读，仅元数据） | 否（缺源音频；且需 API 重跑） | `unique_evidence_preserve` |
| `config.json` | ignored（`.gitignore:59 config.json`，注释 “Config with API keys”） | 1 / 597（mtime 2026-07-09 19:33:57） | 由 `config.example.json` 模式生成的本机配置 | 否 | 不适用 | `no_change`（正确忽略；内容未读取） |
| `__pycache__/` ×4（root/core/engines/tests） | ignored（`.gitignore:2 __pycache__/`） | 38 / 382,647 | Python 字节码缓存 | 否 | 是（任意一次 import/pytest） | `generated_candidate_review` |
| `.pytest_cache/` | ignored（自带 `.gitignore`=`*`） | 5 / 17,363 | `v/cache/nodeids`（200 条，mtime 2026-07-09 21:59:58，与 `.coverage` 同刻）；`v/cache/lastfailed`（mtime 21:50:42，记录 1 个失败：`tests/test_translator.py::TestTranslateParagraphRetry::test_returns_failure_marker_after_max_retries`） | **是**（本地运行记录；要点已摘录进本报告 §8） | 是（重跑覆盖） | `generated_candidate_review` |
| `.ruff_cache/` | ignored（自带 `.gitignore`） | 5 / 1,057 | ruff lint 缓存 | 否 | 是 | `generated_candidate_review` |
| `.mimocode/` | ignored（自带 `.gitignore`：node_modules/package.json/scheduled_tasks.json 等） | 2 / 133（`.cron-lock` 38B、`.gitignore` 95B） | agent 工具运行状态 | 否 | 不适用 | `no_change` |
| `.benchmarks/` | 非 ignored 也非 untracked（空目录，Git 不显示；`git check-ignore -v .benchmarks` 未命中） | 0（创建/修改 2026-07-08 22:59:26） | 无消费证据 | 否 | 不适用 | `no_change`（空目录；成因 unknown） |

`.coverage` 可再生性证据（仅查记录，未运行生成命令）：

- `pytest.ini` `addopts` 含 `--cov=…`；`pyproject.toml` `[tool.pytest.ini_options] addopts="-v --cov=. --cov-report=term-missing"`、`[tool.coverage.run] source=["."]` → 任意本地 `pytest` 即在工作目录重写 `.coverage`。
- `README.md:195`、`CONTRIBUTING.md:220` 记载命令 `pytest tests/ --cov=. --cov-report=term-missing`；`ci.yml:36` 同命令（runner 上执行，`coverage.xml` 仅上传 codecov，仓内不存在 `coverage*.xml`/`*.html` 报告文件）。
- 结论：**同类产物可再生**；但工作树这份（07-09 21:59:58 那次运行的精确数据）不可逐字节复现，其覆盖率结论已以文字形式记录在 progress.md。据此给 `generated_candidate_review`，不给“直接删除”建议。

## 7. PWF 与 commit 记录对照

| PWF 位置/plan id | PWF 声明状态/最后时间 | 关联 SHA/工作树 | Git/现存测试/CI 收据核验 | 一致/冲突/不确定 |
|---|---|---|---|---|
| PWF 活动 selector | `.planning/` 不存在、无 `PLAN_ID`、无 ledger/handoff 文件（`Test-Path .planning`=False；`*handoff*/*ledger*` 0 命中） | — | 按 PWF 解析链回退 legacy 根文件 | 活动计划入口 = 根目录 `task_plan.md` + `progress.md` + `findings.md` |
| 根 `task_plan.md`（v3，`0f5584c` 2026-07-09 21:26 引入、`3c0b053` 2026-07-10 20:19 更新） | Phase 0 **pending**；Phase 1/2/3/4/6 **complete**；Phase 5 **in_progress** | 已入库于 HEAD；工作树无改动（`git status` 仅 `.coverage`） | Phase 0 三项实际已由 `ad73843`（07-09 21:37）实施：company.py 死代码 -6 行、text_merger 常量 -1 行、audio_utils 临时文件处理 +15、fallback 全捕获 +7 | **冲突**：Phase 0 已提交但文件仍 pending |
| 同上 Phase 5 | in_progress（5.1/5.3 未勾） | HEAD | `engines/registry.py` 不存在；tests 中无 `pytest.mark.network`；`metrics.py`（5.2）存在 | **一致** |
| HEAD 提交信息 `3c0b053`「refactor: 架构改进计划 v3 完成 (P0-P6)」 | 2026-07-10 20:19 | 3c0b053 | 与文件内 Phase 0 pending / Phase 5 in_progress 直接矛盾 | **冲突**（提交信息 vs 计划文件） |
| 根 `progress.md` | v2 计划 **P1–P8 完成**（2026-07-08~07-09），另记 e2e 通过、v3 制定待执行 | `8826aed`…`c09f6cc` 区间 | `tests/`（17 个 py 文件）、`pytest.ini`、`.github/workflows/ci.yml` 均存在 | **一致**（v2 编号体系） |
| 根 `findings.md` | F1–F15，2026-07-09 | — | 与 v3 计划问题表逐条对应 | 一致 |
| lane 卡 known-start：master@3c0b053 与 live origin/master 同 SHA | — | ls-remote 实测 | 相同 | 一致 |
| lane 卡 known-start：`.coverage` 53,248 B、mtime 2026-07-09 | — | 53,248 B、mtime 2026-07-09 21:59:58 | — | 一致 |
| lane 卡 known-start：「root task_plan 保留 Phase10–15 pending」 | — | — | 当前文件仅 Phase 0–6；`git grep "Phase 1[0-5]"` 0 命中；`git log -S 'Phase 10'/'Phase10' --all` 0 命中（全历史） | **不成立**：任何提交版本均无 Phase 10–15；记为已知起点笔误/unknown |

P0–P8 与 task_plan 状态的时间/计划关系（lane 卡步骤 4 的解释）：

1. **两套计划、两套编号**：progress.md 记录的是 v2 计划（8 阶段 P1–P8，2026-07-08~09 执行完毕，其 task_plan 旧版见 `8826aed:task_plan.md`）；根 `task_plan.md` 现存内容是 v3 计划（P0 快修 + P1–P6，2026-07-09 21:26 起）。v2 的“P5=代码清理”与 v3 的“P5=扩展性”编号相同、内容不同，不能互相对照。
2. 因此 “progress 记 P0–P8 完成” 与 “task_plan Phase 0 pending” **不是同编号冲突**：前者是 v2 的历史完成记录（且 progress 未单列 P0，P0 快修见提交 `ad73843`），后者是 v3 的状态字段。
3. **真实冲突有两处**：(a) v3 Phase 0 实际已在 `ad73843` 入库，文件却仍 pending；(b) HEAD 提交信息自称 “P0-P6 完成”，与文件 Phase 0 pending + Phase 5 in_progress 矛盾。
4. “Phase 10–15” 在全历史不存在，无法建立时间关系 → unknown（很可能是 lane 卡誊写错误）。
5. Git 侧无任何未合工作：唯一分支与远端等同，所有计划执行结果均已入库；剩余只是**文档状态字段**与提交信息的矛盾，不是未提交代码。

## 8. 已有测试、CI、E2E 证据（仅查记录，不运行）

| 命令/Workflow/报告 | 绑定 SHA | 结果与日期 | 是否覆盖 branch-only / dirty 行为 | 限制 |
|---|---|---|---|---|
| GitHub Actions push run（run_id 29117635443，`.github/workflows/ci.yml`） | 3c0b053 | completed/**failure**，2026-07-10T19:20:00Z 创建并于同秒结束，`jobs total_count=0`（无任何 step 执行记录） | 覆盖 HEAD；branch-only=0 不适用；不覆盖 dirty `.coverage` | 失败原因 unknown（未拉取日志）；HEAD **无通过收据** |
| GitHub Actions run（event=dynamic） | 08309f5（Initial commit） | success，2026-07-08T21:29:47Z–21:30:39Z | 否（旧 SHA，不覆盖当前代码） | 触发方式/细节 unknown |
| 本地 pytest 运行记录（`.pytest_cache` + `.coverage` mtime） | 无 SHA 绑定（介于 `ad73843` 与 `3c0b053` 之间的工作树状态） | 2026-07-09 21:59:58：nodeids 收集 200 条、同刻生成 `.coverage`；21:50:42 的 lastfailed 记录 1 个失败（translator retry 标记测试） | 本地行为；不覆盖最终 HEAD（07-10 还有提交） | 是否全绿 unknown；按 lane 卡未运行 pytest/coverage 复验 |
| progress.md 文字记录 | 无（文本声明） | 2026-07-08/09：“138→194 测试全绿”“覆盖率 80–88%”；e2e 三音频成功 | 否（无 SHA/无产物文件） | 仅文本，无 junit/coverage 产物落盘 |
| 命令文档 `pytest tests/ --cov=. --cov-report=term-missing` | — | `README.md:195`、`CONTRIBUTING.md:220`、`ci.yml:36` | 再生 `.coverage` 的方法证据 | 本审计未执行 |
| codecov 上传（`ci.yml` 仅 Python 3.13 步骤） | — | `fail_ci_if_error: false`；本地无 `coverage.xml` | — | 上传状态 unknown（未查 codecov） |

## 9. 建议的后续处置类别（不执行）

| 项 | 类别 | 证据 |
|---|---|---|
| `refs/heads/master` / `origin/master` | `no_change` | left-right `0 0`，live ls-remote 同 SHA，无独有提交 |
| 工作树（唯一 dirty 文件 `.coverage`） | `generated_candidate_review` | pytest-cov 配置 + README/CONTRIBUTING/CI 命令记录证明同类产物可再生；**注意**：该文件是 tracked 的（入库两次），覆盖/恢复 HEAD 版本将丢弃 07-09 21:59:58 运行数据，且改变入库决策属 owner 权限 → 不建议直接删除，处置由总指挥/owner 裁决 |
| `output/`（9 文件） | `unique_evidence_preserve` | e2e 唯一文本产出，源音频未找到，重跑需 API + 音频；内容为真实公司原文/LLM 输出（敏感，仅报元数据） |
| `config.json` | `no_change` | 含 API key（按 `.gitignore` 注释），已正确忽略，内容未读取 |
| `__pycache__/`、`.pytest_cache/`、`.ruff_cache/` | `generated_candidate_review` | 工具再生产物；`.pytest_cache` 内运行记录已摘录进本报告 §8 |
| `.mimocode/` | `no_change` | agent 工具状态（2 文件 133B），有自有 ignore 规则 |
| `.benchmarks/`（空） | `no_change` | 0 文件；成因无证据但无内容可处置 |
| `task_plan.md` Phase 0/Phase 5 状态字段、HEAD 提交信息 | `owner_decision_needed` | 三处互相矛盾（见 §7），属计划文档裁定，不属本只读审计 |

## 10. 检查命令与结果（脱敏）

均只读；远端仅 `ls-remote` 与 GitHub REST GET，未 fetch/pull/push；未复制远端 URL 与凭据。

| 命令（关键参数） | 退出码/结果 |
|---|---|
| `git status --short --branch` / `--porcelain --untracked-files=all` / `--short --ignored` | 0；` M .coverage`；ignored 8 条目；untracked 0 |
| `git rev-parse HEAD`、`git branch -vv`、`git branch -a`、`git for-each-ref` | 0；单分支 master=3c0b053，refs 共 3 条 |
| `git worktree list` | 0；仅主工作树 |
| `git ls-files -s -- .coverage` | 0；tracked、mode 100644（blob id 按模板不输出） |
| `git check-ignore -v <8 路径>` | 命中 `output/`、`__pycache__/`、`config.json`；`.coverage`/`.benchmarks` 未命中（单测 exit 1） |
| `git rev-list --left-right --count master...origin/master` | 0；输出 `0	0` |
| `git merge-base --is-ancestor origin/master master` | 0（是祖先） |
| `git log`（`--follow -- .coverage`、`-- task_plan.md`、`-S` pickaxe `Phase 10`/`Phase10`） | 0；`.coverage` 2 次入库；Phase 10–15 全历史 0 命中 |
| `git show --stat ad73843` / `3c0b053` | 0；P0 修改 8 文件；HEAD 25 文件 |
| `git stash list` | 0；空 |
| `git ls-remote origin refs/heads/master refs/heads/main HEAD` | 0；成功，无 `main` |
| 只读打开 `.coverage`（sqlite3 `mode=ro&immutable=1` 读 meta） | 0；`version=7.12.0`、`has_arcs=0`；未写文件 |
| `Get-Content`/`Get-ChildItem` 盘点配置与 ignored 目录 | 0；按最小元数据读取 |
| GitHub REST `actions/runs` + `jobs`（GET ×3） | 0；见 §8 |
| `gh run list` | 跳过：gh CLI 不存在（CommandNotFoundException） |
| pytest / coverage / ruff / fetch / switch / commit | **未执行**（lane 卡禁止） |

## 11. 交接声明

- 我只读取 lane 指定的仓库（及本施工包模板/卡），没有改动目标仓工作树、索引、Git refs、全局配置或其他项目：`yes`（唯一写入为本结果文件）。
- 我没有运行会写文件的测试、构建、下载或 provider/LLM：`yes`（仅只读 git/文件检查、sqlite 只读打开与 GitHub REST GET）。
- 本报告结论覆盖的 HEAD SHA：`3c0b0531637589b3c4b14b83da8e1b3c3e1adf9b`（= live `origin/master`，ls-remote 实测同刻一致）。
- 需要总指挥复核的唯一事项：`task_plan.md` Phase 0/Phase 5 状态、HEAD 提交信息「P0-P6 完成」与 `ad73843` 实施证据三方矛盾的裁定；连带裁定 dirty `.coverage` 的保留方式（本报告仅给 `generated_candidate_review` 分类，不授权删除）与 HEAD CI 0-job 失败的补验。

## 总指挥收据（2026-10-04）

本报告已收到并验收。tracked `.coverage` 作为唯一测试运行数据保留，ignored `output/` 不做清理；这项验收只确认交接内容，不代表项目代码或计划矛盾已修复，也不授权删除任何 MeetingConverter 文件。
