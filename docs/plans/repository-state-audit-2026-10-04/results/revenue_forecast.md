# Lane RF — revenue-forecast 只读盘点交接报告

## 0. 审计元信息（必填）

```yaml
audit_id: "RSA-revenue-forecast-20261004"
repository: "revenue-forecast"
repository_root: "C:\\Users\\郑曾波\\Projects\\revenue-forecast"
audit_status: "complete"
started_at_local: "2026-10-04 19:40 +01:00 (approx，未独立计时)"
finished_at_local: "2026-10-04 20:15 +01:00"
current_branch: "fcap"
current_head: "5319ee263c4af41ac255938c25bebd32cce56f66"
base_ref: "origin/main (本地 remote-tracking)；对照线 origin/fcap"
base_sha: "6fb2def709d13bda9cfada7ecf62bfc0e3744ae2 (origin/main)"
remote_live_check: "ls-remote success"
remote_checked_at: "2026-10-04 ~19:50 +01:00 (approx)"
source_changes_made: false
tests_run: false
```

已知起点复核结果（全部重新确认，均吻合）：

- 根 checkout `fcap@5319ee263c4af41ac255938c25bebd32cce56f66`；`git ls-remote --heads origin main fcap` 返回 `fcap=5319ee26…`、`main=6fb2def7…`，与本地 `origin/fcap`、`origin/main` 完全一致（未 fetch）。
- `fcap` 相对 `origin/main`：`git rev-list --left-right --count origin/main...fcap` = 左 14（base-only）/ 右 4（branch-only），与初查一致；4 个独有提交标题即 DWA-04R A–D。
- **更正**：「360 paths / 8 execution-run carriers」出自 **batch-A `9152528d`** 的标题与正文，不是 D。D（`5319ee26`）是 `.gitignore` 处置批。
- `codex/revenue-source-reader@3b00b938`：相对 origin/main **ahead 1 / behind 13**，1 个本地独有提交（`wip: preserve pathless source reader prototype`），确认。
- 根 fcap 两项 tracked 修改确认：`assurance/runs/weekly_alert.jsonl`（+1 行）、`assurance/runs/weekly_manifest.json`（6/6）——是 2026-10-04T03:30Z 真实周任务运行的追加账本，不是可随意丢弃的临时日志（见 §5）。
- `audit_review/README.md` §0 与 `state.json` 记 `plan_status=completed`、`current_next=CA-201`、`last_control_update=2026-08-31`，早于 fcap DWA-04R（2026-10-02）——归因见 §7。

## 1. 一页结论

- **branch-only commits**：相对 `origin/main`，本地 12 个分支中仅 2 个有独有提交——`fcap` 4 个（DWA-04R A–D）、`codex/revenue-source-reader` 1 个；其余 10 个本地分支与全部 remote-tracking 分支（除 `origin/fcap` 镜像同 4 个）branch-only=0。合计**全仓可见 branch-only 提交 = 5**（已推送到 `origin/fcap` 的 4 个 + 仅本地的 1 个）。
- **tracked staged / unstaged**（全 16 个 worktree 逐个统计）：staged 合计 **238**（全部在 `rf-impl`，含 8 M + 230 A）；unstaged 合计 **47,186**（根 2 个 M；`rf-impl` 4 个 M；`rf-merge-review` 47,173 个 D——48,743 个 tracked 文件中 47,173 在磁盘缺失；`rfv2-tdd` 6 D + 1 M）。
- **untracked / ignored**：全部 worktree 非忽略 untracked **= 0**（`git ls-files --others --exclude-standard`）；根 worktree ignored 在盘约 **150,445** 个文件（`.planning` 145,710 主导，另有 3 个目录 Permission denied 无法枚举）。batch-D 提交称「Post state: 1985 untracked entries remain」与今日实测 0 **不符，差异未解**（见 §6）。
- **worktrees**：共 **16** 个（1 root + 15 linked）。dirty **4**（root / rf-impl / rf-merge-review / rfv2-tdd）；detached **10**（`.fcap-review/*`，全部 clean 且 HEAD 均在 main 与 fcap 内）；clean linked **2**（narrative / source-ref-v2）；用途异常 **1**（rf-merge-review 磁盘仅剩 1,530 文件）。
- **PWF ↔ Git 差异**：①「PWF 称完成但 Git 未合」——DWA-04R 4 提交已推 `origin/fcap` 但**未进 origin/main**；②「Git 已合但 PWF 待提交」——`rf-impl` 索引里 staged 238 个文件（DWA-04R 的不完整早期快照）从未提交；③「证据只在工作树」——OWNER_DECISIONS **§四十四（2026-10-03 裁定）仅存在于 rf-impl 的索引/工作树**，以及根两份 dirty 周账本；④ 6 个 codex/* 分支 + phase-* 的 tip 已全部在 main 内（过时 ref）。
- **最大未决项**：`fcap`（4 个已推未并的 DWA-04R 提交）与 `origin/main` 在 **UC closure 门实现（`uc/scenarios.py`/`closure.py`）上双向分叉**（main 侧另有 3 个相关提交），并线需要 owner 定策略；叠加 `rf-impl` 的半份 staged 快照与 `rf-merge-review` 的掏空 worktree，归属与处置均无仓内证据，需总指挥裁定。

## 2. 主线与远端识别

| 线索 | ref/值 | SHA/结果 | 证据命令/文件 | 解释 |
|---|---|---|---|---|
| `origin/HEAD` | `refs/remotes/origin/HEAD` → `refs/remotes/origin/main` | — | `git symbolic-ref refs/remotes/origin/HEAD` | 服务端/本地认定默认线为 `main` |
| 服务端 live | `refs/heads/main` | `6fb2def709d13bda9cfada7ecf62bfc0e3744ae2` | `git ls-remote --heads origin main`（无 fetch） | 与本地 `origin/main` 一致，remote-tracking **不过期** |
| 服务端 live | `refs/heads/fcap` | `5319ee263c4af41ac255938c25bebd32cce56f66` | `git ls-remote --heads origin fcap` | 与本地 `origin/fcap`、根 HEAD 一致 |
| 本地目标主线 | `main` @ `6fb2def7` | 与 origin/main 同 | `git branch -v` | 被 `rf-impl` worktree 检出（该树另有 238 个 staged） |
| 工作 checkout（根） | `fcap` @ `5319ee26` | upstream `origin/fcap`，`+0 -0` | `git status --porcelain=v2 --branch` | 根树即 fcap 头；2 个 unstaged M |
| 终局提交自述 | `b3dee268`（2026-08-31） | "revenue d0c4be7->origin/main …" | `git log -- audit_review/README.md` | 历史终局把 `origin/main` 当主线推 |
| 异常本地分支 | `origin` @ `6fb2def7` | 与 main tip 相同 | `git log -1 origin` | 存在一个**名为 `origin` 的本地分支**（疑命令误建），无独有提交 |

remote-tracking 过期风险：`origin/main`/`origin/fcap` 与服务端逐字节一致（刚校验）；`origin/phase-14-input-build-tools@02d89137` 与本地 `phase-14-input-build-tools@cbb1dd40` 不同，但两者相对 origin/main 均 branch-only=0（都已含于主线历史），差异仅为 ref 指位，非内容风险。未运行 fetch。

## 3. Branch 矩阵

左列 = base-only（在 `origin/main` 而不在分支），右列 = branch-only（在分支而不在 `origin/main`），来自 `git rev-list --left-right --count origin/main...<branch>`。

| branch ref | tip SHA | merge-base(vs main) | base-only | branch-only | patch-equivalent/cherry | diff stat (vs main) | PWF/交接关联 | 当前判断 |
|---|---|---|---:|---:|---|---|---|---|
| `fcap`（= `origin/fcap`） | `5319ee26` | `ee0a82bf` | 14 | **4** | `git cherry -v`：4 个全为 `+`（**无** patch 等价，未被 cherry/squash 进 main） | 363 files, +44583/-35485 | DWA-04R A–D；REM-54/收尾台账 | **merge_candidate**（UC 门与 main 双向分叉，需集成测试与冲突策略） |
| `codex/revenue-source-reader` | `3b00b938` | 同上 | 13 | **1** | `+ 3b00b938 wip: preserve pathless source reader prototype` | 75 files, +1724/-4223 | 10 文件中 7 与 main 内容 DIFF、3 个测试文件 main 缺失 | **owner_decision_needed**（大部分被 main 演进取代，仍留独有测试与 WIP） |
| `main`（= `origin/main`） | `6fb2def7` | — | 0 | 0 | — | — | 默认主线 | `no_change`（基线本身） |
| `codex/rf-assurance-merge-20260927` | `3a69f9c5` | 自身即 main 内提交 | 13 | 0 | tip ∈ main（`3a69f9c5` 是 main 的 base-only 列成员） | 无独有 diff | 对应 Temp worktree（已掏空） | `already_in_base`（过时 ref） |
| `codex/rf-evidence-20260929` | `8b11b0ce` | 同 | 12 | 0 | tip ∈ main | 无独有 diff | — | `already_in_base` |
| `codex/rf-reader-v2-20260929` | `415d8eb3` | 同 | 10 | 0 | tip ∈ main | 无独有 diff | source reader 正式实现 | `already_in_base` |
| `codex/rf-release-readiness-20260929` | `88b3bda3` | 同 | 11 | 0 | tip ∈ main | 无独有 diff | — | `already_in_base` |
| `codex/rf-source-ref-v2-integration-20261003` | `0573c40c` | 同 | 3 | 0 | tip ∈ main | 无独有 diff | 对应 Temp worktree（clean） | `already_in_base` |
| `codex/rf-narrative-consumer-20261003` | `6fb2def7` | = main tip | 0 | 0 | 与 origin/main 完全同位 | 0 | 对应 Temp worktree（clean） | `already_in_base` |
| `phase-14-input-build-tools` | `cbb1dd40` | 早期历史 | 953 | 0 | tip ∈ main 历史 | 无独有 diff | — | `already_in_base`（远古 ref） |
| `phase-19-tooling-docs` | `c0571d8b` | 早期历史 | 945 | 0 | tip ∈ main 历史 | 无独有 diff | — | `already_in_base`（远古 ref） |
| `origin`（本地同名分支） | `6fb2def7` | = main tip | 0 | 0 | 与 main 同位 | 0 | 疑误建 | `owner_decision_needed`（命名异常，无独有内容） |
| `origin/phase-14-input-build-tools`（rt） | `02d89137` | 早期历史 | 954 | 0 | tip ∈ main 历史 | 无独有 diff | 与本地 phase-14 指位不同 | `already_in_base` |

### 3.1 `fcap` 的 4 个 branch-only 提交明细

全部作者 `zhengcb81`，作者时间 2026-10-02T22:14–22:20+01:00，均已推送至 `origin/fcap`。

**A — `9152528d`「planning: DWA-04R batch-A — audit ledgers + eight execution-run carriers as evidence (360 paths; owner decision 2026-10-02)」**

- 变更 **360 个路径 = 355 新增(A) + 5 修改(M)**。
- 5 个 M = 2026-09-19 审计五台账：`OWNER_DECISIONS.md`(46+/1-)、`REMEDIATION_REGISTER.md`(68+/1-)、`findings.md`(22+/0)、`progress.md`(37+/0)、`task_plan.md`(2+/2-)。
- 355 个 A = 8 个从未入库的 execution-run 载体目录，逐目录实测：`DEF-I00C-GATE-NEG` 167、`DEF-MSFT-CANONICAL-DUP` 100、`RATCHET-FIX-A` 24、`RATCHET-FIX-B` 24、`RATCHET-FIX-C` 17、`RATCHET-FIX-REVIEW` 12、`RATCHET-FIX-ARCHIVE` 4（五者合计 81）、`T3-DIAG` 7。
- 分类计数：计划/台账 5；唯一证据载体 355（reviewer 报告、oracle、handoff、变异/负例 JSON、pre/post image 等）；**产品路径 0**（与提交正文自述一致）。
- 正文引 `core.longpaths` 本地启用（两条 >260 字符夹具路径），Linux CI 不受影响。

**B — `23ac4357`「uc: DWA-04R batch-B — unified-completion closure/scenarios evidence-integrity checks」**

- 3 个文件，全部 M：`assurance/unified_completion/uc/scenarios.py`(62+/6-)、`uc/closure.py`(13+/0)、`tests/test_scenarios.py`(71+/0)。
- 用途：给 UC closure 门增加 `evidence_path` / `required_capability` / oracle 非空校验及回归测试。提交正文声明「gate/tests run BEFORE this product commit」（测试先于产品提交运行）、定向 uc suite 17 passed、全 tests 目录（除 concurrency）绿——**仓内未发现独立 receipt 文件承载该次运行，仅有提交正文自述**。
- 与 main 关系见 §7 冲突分析：main 侧 `3a69f9c5`/`8b11b0ce`/`3e03ce83` 同改这两文件且行数更多（main 的 `scenarios.py` 关键词命中 32/`fixture_hash`×8，fcap 23/×3），**非 patch 等价，需语义级并线**。

**C — `a00211ee`「assurance: DWA-04R batch-C — alert/manifest ledgers kept tracked as evidence」**

- 4 个文件全 M：`daily_alert.jsonl`(+1)、`monthly_manifest.json`(6/6)、`weekly_alert.jsonl`(+1)、`weekly_manifest.json`(5/5)。
- 用途：按仓库 `.gitignore` 政策（runtime ledgers 保持 tracked）把 daily/monthly alert+manifest 账本作为证据入库；weekly 的 `weekly-run-*.log` 留给 batch-D 以 ignore 处理。

**D — `5319ee26`「chore: DWA-04R batch-D — ignore mutation-scratch/backup/weekly-log artifacts, drop zero-byte h2 logs」**

- 仅 1 个文件 M：`.gitignore` +11 行（`2f2009e2`，与 `rf-impl` staged 版本字节相同）。
- 处置：`.tmp-r41-mutation/` 留盘不提交（正文称 45 文件中 7 个含唯一变异内容、不可重建，弃删风险更高故选 ignore）；`plan_inputs.json.bak` 保留（历史内容不可再生）；`weekly-run-*.log` 扩展 ignore；`h2.log`/`h2.log.err` 删除（0 字节，盘上确认已不存在）。
- 正文自称「Post state: 1985 untracked entries remain」——**2026-10-04 实测非忽略 untracked=0，该数字无法复现**（见 §6）。

### 3.2 360 paths 的精确定义（必答问题 2）

**360 = 提交 `9152528d`（batch-A）自身的 git 文件变更计数**：`git show --name-status 9152528d` 返回 360 行（A=355、M=5、D=0）。它是「commit file count」，**不是** artifact registry 计数、不是全审计路径总数（该审计全文审 766 份 Markdown）、也不是 execution_runs 下的文件总数（fcap 上 `execution_runs` tracked 250 目录 + 8 个 `_tmp_*` 文件）。提交正文「Staged count reconciled to the audit's 360 exactly」指的就是把 staged 文件数与该 commit 文件数对平的自校验。

### 3.3 `codex/revenue-source-reader` 独有提交（必答问题 5）

`3b00b938`（2026-09-29T18:38+01:00，`wip: preserve pathless source reader prototype`）：10 文件 +1560/-2。

- 与 `origin/main` 逐文件 blob 比对：7 个同名文件两边都有但内容 **DIFF**（`scripts/company_wiki_source.py`、`company_wiki_source_reader_v2.py`、`source_preparation.py`、`filing_fetch_client.py` 及 4 个测试）；**3 个文件仅分支独有**：`tests/test_source_preparation_v2.py`(48 行)、`tests/test_source_preparation_v2_cross_repo.py`(221 行)、`tests/test_source_ref_candidate_preparation.py`(217 行)。
- main 侧经 `415d8eb3`（09-29 19:46，晚分支 1 小时）与 `89e43c29`（10-03）演进出正式 source reader；分支原型大概率**功能上被取代**，但字节级不等价且带独有测试。
- 所在 worktree `rfv2-tdd-20260927` 另有未提交 WIP：`tests/test_source_ref_v2_three_repo_e2e.py` +10 行（unstaged M），6 个文件被从磁盘删除（`.coveragerc`、`.pre-commit-config.yaml`、4 个 `__init__.py`）。
- **结论：主线外仍有独特内容（3 个测试文件 + WIP + 原型差异），但主体实现已被 main 取代；定性 owner_decision_needed（测试部分可评估 merge_candidate），不实施。**

## 4. Worktree 矩阵

| worktree path | branch/detached | HEAD SHA | porcelain 状态 | PWF/owner/创建来源 | 可能用途 | 确定度 |
|---|---|---|---|---|---|---|
| `…\Projects\revenue-forecast`（根） | `fcap` | `5319ee26` | 2 unstaged M（两份周账本） | 仓库主 checkout；DWA-04R A–D 的提交点 | 主工作树 | 高 |
| `…\Projects\rf-impl` | `main` | `6fb2def7` | **238 staged**(8M+230A) + 4 unstaged M | 名称暗示实现用树；staged 内容 = DWA-04R 的**部分**早期快照 | 曾在此暂存 DWA-04R，后在 fcap 完成提交，索引残留 | 中（owner 无证据） |
| `…\Temp\rf-merge-review-20260927` | `codex/rf-assurance-merge-20260927` | `3a69f9c5` | **47,173 unstaged D**（tracked 48,743，盘上仅 1,530 文件；顶层目录在、内容缺失） | 09-27 并线复审树 | 复审后被清空/半删除的审查树；tip 已在 main | 中 |
| `…\Temp\rf-narrative-consumer-20261003` | `codex/rf-narrative-consumer-20261003` | `6fb2def7` | clean | 10-03 叙事消费者集成 | 与 origin/main 同位的临时检出 | 高 |
| `…\Temp\rf-source-ref-v2-integration-20261003` | `codex/rf-source-ref-v2-integration-20261003` | `0573c40c` | clean | 10-03 source-ref 集成 | tip 已在 main 的临时检出 | 高 |
| `…\Temp\rfv2-tdd-20260927` | `codex/revenue-source-reader` | `3b00b938` | 6 D + 1 M（+10 行测试） | 09-27 TDD 会话 | 原型分支的活跃开发树 | 中高（有未提交改动） |
| `…\.fcap-review\fc-1003-rev` | detached | `26bdfb27` | clean | FCAP 复审 | FC-1003 卡复审快照 | 高（HEAD∈main 且∈fcap） |
| `…\.fcap-review\fc-1101-rev` | detached | `1b41d62f` | clean | 同上 | FC-1101 复审 | 高（同上） |
| `…\.fcap-review\fc-1204\base-revenue` | detached | `9315ddf3` | clean | 同上 | FC-1204 系列基线 | 高（同上） |
| `…\.fcap-review\fc-1204\layout\revenue-forecast` | detached | `4750fecd` | clean | 同上 | FC-1204-b | 高（同上） |
| `…\.fcap-review\fc-1204\r2\revenue-forecast` | detached | `387e6ac5` | clean | 同上 | FC-1204 r2 | 高（同上） |
| `…\.fcap-review\fc-1204\r3\revenue-forecast` | detached | `91cbc137` | clean | 同上 | FC-1204 r3 | 高（同上） |
| `…\.fcap-review\fc-1205\revenue-base` | detached | `91cbc137` | clean | 同上 | FC-1205 基线 | 高（同上） |
| `…\.fcap-review\fc-1205\revenue-forecast` | detached | `58db9486` | clean | 同上 | FC-1205 | 高（同上） |
| `…\.fcap-review\fc-130x\revenue-base` | detached | `4a4c1089` | clean | 同上 | FC-130x 基线 | 高（同上） |
| `…\.fcap-review\fc-130x\revenue-forecast` | detached | `a9f1ff18` | clean | 同上 | FC-130x | 高（同上） |

全部 10 个 detached HEAD 经 `git merge-base --is-ancestor` 验证**同时是 origin/main 与 fcap 的祖先**（提交时间 2026-08-12/13，FCAP 卡系列），无独有提交。未做任何 prune/remove。

## 5. 当前未提交文件

| 路径 | Git 状态 | staged diff | unstaged diff | 类型/可能用途 | PWF/commit/调用者证据 | 敏感性 | 推荐后续分类 |
|---|---|---|---|---|---|---|---|
| `assurance/runs/weekly_alert.jsonl`（根） | unstaged M | 无 | +1 行（numstat 1/0）：`2026-10-04T03:30:23Z` run `20261004T033000Z`，`exit_code=1 reason="T3 suite exit 1"` | 周任务追加告警账本 | 写入方 `tools/weekly_t3_schedule.py:63-64`；测试 `tests/test_zr903_weekly_t3.py`；batch-C 政策「runtime ledgers stay tracked」 | 无凭据；仅 run_id/时间/退出码 | `unique_evidence_preserve`（真实运行的精确字节，不可再生） |
| `assurance/runs/weekly_manifest.json`（根） | unstaged M | 无 | 6/6：latest_run_id→`20261004T033000Z`、report_path、started_at、triplet 更新（revenue=`5319ee26`=fcap HEAD，filing=`2936ad10`，wiki=`a815c592`） | 周任务最新清单 | 同上；其 `report_path` 指向已被 batch-D ignore 的 `weekly-run-20261004T033000Z.log`（盘上 2856 B） | 无凭据；triplet SHA 非敏感 | `unique_evidence_preserve`（同上；提交前需 CRLF 归一注意——git 已警告将 LF 化） |
| `rf-impl` 索引 238 项（8 M + 230 A） | staged | 与 fcap 提交大部同字节：`.gitignore`、`weekly_*` blob 与 fcap HEAD **相同**；`OWNER_DECISIONS.md` **不同**（staged 版多出 §四十四，见 §7）；carrier 仅 230/355（DEF-I00C 147/167、MSFT 2/100、RATCHET 81/81、T3-DIAG 0/7；5 台账缺 task_plan/REMEDIATION_REGISTER） | — | DWA-04R 的**不完整早期暂存**残留 | 与 fcap `9152528d`/`a00211ee`/`5319ee26` 内容重叠 | 同台账性质，无凭据 | `preserve_active_work` + `owner_decision_needed`（含全仓唯一证据 §四十四，见 §7） |
| `rf-impl` 4 个 unstaged M | unstaged M | 无 | 小改动：`I-04-D/…/r2_corrections.md`(16/16)、`RF-RATCHET-REST-A/…/probe_new.json`(1/1)、`probe_orig.json`(1/1)、`TTL-30D-POLICY/…/hashes.json`(8/8)（CRLF 警告） | 审计证据文件的本地修订 | 无提交引用 | 无凭据 | `owner_decision_needed`（疑似行尾/微调，未验内容语义） |
| `rf-merge-review` 47,173 个 D | unstaged D | 无 | tracked 文件在磁盘缺失（顶层 23 项目录框架在） | 被掏空的 worktree | tip 已在 main；树不可用 | — | `owner_decision_needed`（**不得 prune**；先查明是迁移/磁盘清理还是有意弃置） |
| `rfv2-tdd` 7 项 | unstaged | 无 | 6 D + `test_source_ref_v2_three_repo_e2e.py` +10 | 原型 TDD 未提交改动 | 分支唯一提交 `3b00b938`；§3.3 | 无凭据 | `preserve_active_work` |

对两个 dirty JSON 的专项结论（必答问题 3）：**二者是唯一证据，不是可再生缓存**。内容为 2026-10-04 真实周运行的精确记录（run_id/时间戳含运行时随机性，重跑不能得到相同字节），且按仓库自身政策（batch-C 正文、`.gitignore` 注释）runtime ledgers 应保持 tracked。无访问凭据/私人内容（仅运行元数据与仓库 SHA）。其明细日志 `weekly-run-20261004T033000Z.log` 按 owner 2026-10-02 裁定被 ignore（称可由重跑再生），但**该次失败明细本身仅此一份**——JSON 两行必须保留，log 是否补录属 owner 决定。

## 6. 未跟踪/ignored 工件及空间线索

| 目录/文件 | Git 状态 | 文件数/总字节 | 创建/消费证据 | 是否唯一审查/测试证据 | 可再生证据 | 结论/未决 |
|---|---|---:|---|---|---|---|
| 根全树 ignored | ignored | 150,445 文件（`ls-files --others --ignored --exclude-standard`） | 各工具产物 | 多数否 | 多数是 | `generated_candidate_review`（只按目录取证，不全盘删除） |
| `.planning/**`（ignored 部分） | ignored | 145,710 | pytest/镜像/夹具缓存（含 iso_ctl 镜像副本） | 否 | 是 | `generated_candidate_review` |
| `.tmp-r41-mutation/` | ignored（batch-D） | 88 文件 | batch-D 正文：45 文件中 **7 个含唯一变异内容、不可重建** | 部分是（那 7 个） | 部分否 | 混合：7 个 `unique_evidence_preserve`，其余 `generated_candidate_review`；owner 已裁定留盘 |
| `assurance/unified_completion/manifests/plan_inputs.json.bak` | ignored（batch-D） | 11,916 B，mtime 2026-09-27 | batch-D 正文「historical content, unreproducible」 | 是（09-27 前历史快照） | 否 | `unique_evidence_preserve`（owner 已裁定保留） |
| `assurance/runs/weekly-run-20261004T033000Z.log` 等 5 个周 log | ignored（batch-D 第 45 行） | 最新 2,856 B（2026-10-04 04:30）；另有 4 个历史 log | `weekly_t3_schedule.py` 生成，manifest `report_path` 指向 | 最新一份为当次唯一明细 | 按 owner 政策称可重跑再生 | `generated_candidate_review`（与配对 JSON 分开处置） |
| `h2.log` / `h2.log.err` | 已按 batch-D 删除 | 盘上不存在（实测 False/False） | batch-D：0 字节 | 否 | 否 | `no_change`（已完成处置） |
| 3 个 Permission denied 目录（`…/reviews/filing/tests/pytest_tmp/`、`.review-zr407-20260818/company-wiki/.pytest_cache/`、`.review-zr407-20260818/tmp-wiki-focused/`） | 均被 ignore（`.planning/.gitignore:**/pytest_tmp/`、`.gitignore:32 .review-zr407-20260818/`） | 无法枚举（ACL 拒绝） | pytest/审查临时区 | 未知 | 未知 | 记录为访问受限；**未读取、未删除**；其内部是否藏有 batch-D 所称 1985 untracked 的一部分 = unknown |
| batch-D「1985 untracked」声称 | — | 实测非忽略 untracked=0 | `5319ee26` 提交正文 | — | — | **对账失败，unknown**；可能与权限受限目录或计数口径（-unormal 目录级）有关，需 owner 复核 |

## 7. PWF 与 commit 记录对照

| PWF 位置/plan id | PWF 声明状态/最后时间 | 关联 SHA/工作树 | Git/现存测试/CI 收据核验 | 一致/冲突/不确定 |
|---|---|---|---|---|
| `audit_review/README.md` §0（`plan_id=TRI-REPO-COMPLETION-2026-08-13-R1`） | `plan_status=completed`、`current_phase=J_final_verification`、`current_next=CA-201`、`last_control_update=2026-08-31` | 最后一次提交 `b3dee268`（2026-08-31 22:47 终局 push）；README blob `5bb5bf3d`，SHA-256=`2f6302be…` | 与 state.json 同读 | **一致（历史终局）** |
| `assurance/unified_completion/state.json` | `completed`/117 units 全 `accepted`；`updated_at=2026-08-31T21:47:05Z`；CA-201 closure `terminal=True, next=CA-201` | 绑定 `control_page_sha256=a7affbb5…`、`base_triplet`（filing 83c638e…/revenue c3a0519…/wiki ef125ed…） | **`a7affbb5` ≠ 当前 README 实测 `2f6302be`**；`plan_inputs.json`（built 2026-09-21）记录的是 `2f6302be`（=当前值） | **不确定（记录漂移）**：state 最后写于 21:47，README 于 22:47 终局提交再改（补 `plan_status: completed` 行），state 未再刷新；后由 plan_inputs 接续记录。非语义矛盾，但 state 的 control-page 哈希已过期 |
| `TERMINAL_NOTICE.json`（根） | `closed_superseded_incomplete`，superseded_by=state.json，written 2026-08-31T23:00Z | 覆盖根 `task_plan/progress/findings` | 三根文件头（08-18 ZR-408 停点）确为历史层 | 一致 |
| 根 `task_plan.md`/`progress.md`/`findings.md` | 自述历史归档；跨仓游标=README+state.json | 未再更新（mtime 2026-09-20 为镜像拷贝时间） | 按其自身说明只读 | 一致（历史材料，未越权使用） |
| `PLANNING_STATUS.md` | 活动计划索引停在 2026-09-08/09-11（R4 等 19 项） | 未登记 2026-09-19 审计包 | 索引内 19 项均指向 company-wiki R4 线 | **不确定（路由缺口）**：`.planning/2026-09-19-three-project-history-audit` 未出现在该索引，也未出现在 README §5 权威层级 |
| `.planning/2026-09-19-three-project-history-audit/README.md` | 「历史审查+新实施计划完成；**产品修复尚未执行**」（2026-09-19/20） | 读取 `audit_report.md`→`implementation_plan.md`→`execution_v2/START_HERE.md` | execution_v2：**所有产品卡 `planned`**、「产品实施未开始」 | 一致（新阶段的起点声明） |
| 同包 `REMEDIATION_REGISTER.md` / `progress.md` / `findings.md` | 追加至 2026-09-27（收尾三件 accepted_scoped、双仓推送状态、REM-54..58 登记） | REM-54（`B5-plan-level-remediation` 整目录未跟踪）状态「本轮已按 T1-27 授权提交」 | `B5-plan-level-remediation` 在 fcap **已 tracked**（1,160 文件；添加于 `b9433dee`/`3861f08d`，2026-09-22） | 一致（REM-54 处置与 git 相符；batch-A 正文再称「Closes the REM-54 carrier-risk finding」指其把同型载体风险一并收口） |
| DWA-04R A–D（fcap） | 提交正文逐批引用「owner decision 2026-10-02 / re-audit batch table」 | `9152528d`→`23ac4357`→`a00211ee`→`5319ee26`，均在 `origin/fcap` | **仓内 `.planning` 任何 .md 均检索不到 `DWA-04R` 或 `2026-10-02` 裁定条目**（OWNER_DECISIONS 止于 §四十二/09-27） | **不确定（裁定原文缺失）**：2026-10-02 owner 裁定只存在于 4 条提交正文；「re-audit batch table」在本仓未定位到（可能在跨仓——未读取，仅记录可能性） |
| `rf-impl` staged §四十四 | 无提交 | `OWNER_DECISIONS` staged blob `1bc275bd` = main 版 + §四十四（2026-10-03，「缺 hash 仅作诊断」，提到「当前 main 的 scenarios.py 已实现…29 passed」） | 全根 worktree `rg`/Grep 无 §四十四；`origin/main` 的 OWNER_DECISIONS 也无（只有 §四十三）；fcap 版连 §四十三都没有 | **冲突/唯一证据**：§四十四是**全仓唯一、未提交**的 owner 裁定记录；同时暴露 fcap 的 OWNER_DECISIONS 落后 main 9 行（缺 §四十三） |
| fcap `uc/scenarios.py`+`closure.py`（batch-B） vs main 同文件 | fcap：+evidence_path/required_capability/oracle 门（17 passed 自述） | main 侧 3 提交：`3a69f9c5`（关九负例）、`8b11b0ce`（场景字节校验）、`3e03ce83`（**allow pending evidence hashes**，即 §四十四所述放宽） | `git diff --stat origin/main fcap`：5 文件 +48/-368（相对 main，fcap 缺 main 的 368 行） | **语义冲突（已证实分叉）**：fcap batch-B 走 09-27 §四十二「放宽」之前的严格路线补丁；main 已按 §四十二/§四十四 演进。并线不能裸合 |
| `audit_review/README.md`「唯一入口」vs 新阶段 | README：只能领 `current_next`；旧计划只读 | fcap DWA-04R 属 09-19 审计线，README 完全未提 | — | **不确定（治理层）**：两代控制页并存——README/state 管 TRI-REPO 终局，09-19 审计线管后续；**不是相互否定的矛盾**（时间上先后、范围上不同计划），但新线未登记进任一权威索引（必答问题 4 结论） |

### 必答问题 4：旧 `completed/CA-201` 与 fcap 实际状态是否冲突

**不构成直接冲突，是两个先后相接的计划代际**：`state.json`/README 的 `completed` + `current_next=CA-201` 是 2026-08-31 的 **TRI-REPO-COMPLETION** 计划终局（117/117 accepted，CA-201 closure `terminal=True` 的回写游标，不是待办卡）；fcap 的 DWA-04R（2026-10-02）与 09-19 审计包是**其后新开的证据修复线**（execution_v2 全部 `planned`、产品实施未开始），既未宣称旧计划未完成，也未被旧控制页登记。需要处置的是三处**陈旧/缺口指针**，而非状态互斥：① state.json 的 `control_page_sha256` 已过期（`a7affbb5`→当前 `2f6302be`）；② README §0/PLANNING_STATUS 均未登记 09-19 新线（路由缺口）；③ README §0 正文仍留有 bootstrap 语汇（「现在只能领取 CA-001」）与 `current_next=CA-201` 并存，阅读者若不看 terminal 标记会误读。

### PWF ↔ Git 四分类汇总（核查步骤 6）

- **完成但未合**：DWA-04R A–D（4 commits，已推 `origin/fcap`，未进 `origin/main`）；B5 载体等 09-22 台账提交（在 fcap 分叉线上，同样未进 main 的对应树——注意其父链经 `ee0a82bf` 与 main 分叉）。
- **已合但待提交**：`rf-impl` 索引 238 项（内容多与 fcap 提交相同，属残留暂存）；rf-impl 4 个 unstaged 小修。
- **证据只在工作树**：OWNER_DECISIONS **§四十四**（rf-impl index+worktree）；两份 dirty 周账本与 `weekly-run-20261004T033000Z.log`（root）；`rfv2-tdd` +10 行测试。
- **branch 已被 main 包含**：6 个 `codex/rf-*` 分支、`phase-14`/`phase-19`（本地）、`origin/phase-14`（rt）、本地 `origin` 分支；10 个 `.fcap-review` detached HEAD。

## 8. 已有测试、CI、E2E 证据（仅查记录，不运行）

| 命令/Workflow/报告 | 绑定 SHA | 结果与日期 | 是否覆盖 branch-only / dirty 行为 | 限制 |
|---|---|---|---|---|
| 周 T3 运行 `20261004T033000Z`（`weekly_manifest.json`，dirty） | triplet revenue=`5319ee26`（=fcap HEAD）、filing=`2936ad10`、wiki=`a815c592` | **ok=false，exit 1（"T3 suite exit 1"）**，2026-10-04T03:30:23Z | 覆盖 **fcap HEAD**；发生在两 dirty JSON 写入时 | 明细 log 被 ignore（盘上 2,856 B 未读全文）；非本审计运行 |
| 周 T3 历史（`weekly_alert.jsonl` tracked+dirty） | 各次运行时 triplet | 09-13/09-20/09-27 三次均 exit 1（not-ok）；仓内账本自 09-13 起连续 not-ok | 否（早于 DWA-04R） | 仅元数据 |
| batch-B 提交正文自述 | `23ac4357` 前置运行 | 「targeted 17 passed；full tests minus concurrency green」 | 覆盖 branch-only 改动 | **无独立 receipt 文件**，仅提交正文（限制） |
| `.github/workflows/quality.yml`（push/PR 触发；ubuntu+windows） | 无固定 SHA（事件触发） | 本地无运行结果收据；mtime 2026-09-20 | 取决于推送 | 未查远端 Actions（不 fetch/不外呼）；`on:` 无 schedule（周跑为本地调度） |
| `assurance/unified_completion/receipts/`（117 个单元收据） | 样例 ZR-907 closure：绑 `state_sha256`/`control_page_sha256`/`manifest_sha256`（schema 1，2026-08-23） | 与 117/117 accepted 对应 | 否（2026-08 代收据） | 文件哈希绑定，非 git SHA；抽样 1 个 |
| DWA-04R 相关执行收据 | — | **未找到**（`.planning` 内无 DWA-04R 命名的 execution_run） | 否 | 测试证据仅提交正文自述 |

## 9. 建议的后续处置类别（不执行）

| 对象 | 类别 | 证据 |
|---|---|---|
| `fcap` 分支（4 DWA-04R 提交） | `merge_candidate` | 唯一含 355 载体 + UC 门补丁 + 账本证据；已推 origin/fcap；与 main 的 `uc/*` 双向分叉 → 并线前必须集成测试与冲突策略 |
| `codex/revenue-source-reader`（1 WIP 提交） | `owner_decision_needed` | 主体被 main 演进取代，但 3 个测试文件 + 分支差异 + rfv2-tdd 未提交测试改动为独有；测试部分可另评 `merge_candidate` |
| 6 个 `codex/rf-*` 分支中除上述外的 5 个 + `phase-14`/`phase-19`（本地）+ `origin/phase-14`(rt) | `already_in_base` | branch-only=0，tip ∈ origin/main（仅 ref 过时） |
| 本地分支 `origin`（@6fb2def7） | `owner_decision_needed` | 疑误建、命名冲突风险；无独有内容 |
| `rf-impl` worktree（238 staged + 4 unstaged + §四十四） | `preserve_active_work` | 索引含全仓唯一 §四十四 裁定与未提交小修；在裁定归属前不得动 |
| `rf-merge-review` worktree（47,173 D） | `owner_decision_needed` | 磁盘内容缺失 97%，tip 已在 main；**禁止 prune/remove**，先查明成因 |
| `rfv2-tdd` worktree（6 D + 1 M） | `preserve_active_work` | 活跃原型 TDD 未提交改动 |
| `rf-narrative-consumer` / `rf-source-ref-v2-integration` worktrees | `no_change` | clean 且分支 tip ∈ main |
| 10 个 `.fcap-review/*` detached worktrees | `already_in_base` | 全部 HEAD 同时 ∈ main 与 fcap，clean，无独有提交（后续可 `deploy_or_archive_branch` 类归档，属总指挥计划） |
| 两份 dirty 周账本（root） | `unique_evidence_preserve` | 真实运行精确字节不可再生；仓库政策 ledger 保持 tracked |
| `weekly-run-20261004T033000Z.log` 等周 log | `generated_candidate_review` | owner 2026-10-02 裁定 ignore+可重跑再生（最新一份是否补录由 owner 决定） |
| `.tmp-r41-mutation/`（88 文件，其中 7 唯一） | 混合 `unique_evidence_preserve`(7) + `generated_candidate_review`(其余) | batch-D 正文明示 |
| `plan_inputs.json.bak` | `unique_evidence_preserve` | batch-D：历史内容不可再生，owner 已裁定保留 |
| 3 个 Permission denied 目录 | `owner_decision_needed` | ACL 拒绝，内容未知；均已 ignore |
| batch-D「1985 untracked」对账差异 | `owner_decision_needed` | 实测 0，声称 1985，口径未知 |
| `h2.log`/`h2.log.err` 删除 | `no_change` | 已按 owner 裁定完成（0 字节） |

## 10. 检查命令与结果（脱敏）

全部为只读命令，无一写入 refs/索引/工作树：

| 命令（摘要） | 退出码/结果 |
|---|---|
| `git status --porcelain=v2 --branch --untracked-files=all`（根） | 0；2 个 `.M` |
| `git worktree list --porcelain` | 0；16 worktree |
| 各 worktree `git status --porcelain [-uall]` ×16 | 0（见 §1/§4 计数） |
| `git ls-remote --heads origin main fcap`（无 fetch） | 0；SHA 与本地一致 |
| `git symbolic-ref refs/remotes/origin/HEAD` | 0 → `refs/remotes/origin/main` |
| `git rev-list --left-right --count origin/main...<b>` ×12 本地分支 + ×4 rt | 0（见 §3） |
| `git log origin/main..fcap`、`git merge-base`、`merge-base --is-ancestor` | 0；merge-base=`ee0a82bf` |
| `git cherry -v origin/main fcap` / `… codex/revenue-source-reader` | 0；全部 `+`（无 patch 等价） |
| `git show --numstat/--name-status/--stat`（4 DWA-04R + `3b00b938`） | 0；360/3/4/1 与 +1560/-2 |
| `git diff --numstat/--stat`（dirty 2 文件；fcap↔main；blob 间 diff） | 0（CRLF 警告 ×2，无害） |
| `git rev-parse :path`、`cat-file -p/-s/-e`（blob 对比） | 0 |
| `git ls-files --others [--ignored --exclude-standard]`、`ls-tree`、`check-ignore -v` | 0；3 目录 Permission denied 警告（已记录） |
| PowerShell `Get-Item/Get-ChildItem/Get-FileHash/ConvertFrom-Json`（元数据） | 0；一次 `ConvertFrom-Json` 转义失败→改用原始文本读取 |
| `rg` 调用 | **失败：本机无 rg** → 改用内置 Grep 工具 |
| 递归列举 `.planning` 目录 | **超时 120s（目录过大）** → 改为 git ls-tree/定向读取 |
| 未执行 | fetch/pull/checkout/restore/reset/stash/清理/merge/rebase/commit/push、任何测试/构建/LLM、session catch-up、跨仓（company-wiki/filing-fetch/StockWiki）读取 |

## 11. 交接声明

- 我只读取 lane 指定的仓库，没有改动工作树、索引、Git refs、全局配置或其他项目：**yes**（唯一写入为本报告文件，位于 company-wiki 的 lane 指定输出路径——这是任务显式要求的唯一交接产物）。
- 我没有运行会写文件的测试、构建、下载或 provider/LLM：**yes**（git 只读命令与文件元数据读取；一次 `ls-files` 枚举触发 3 处权限警告，未修改）。
- 本报告结论覆盖的 HEAD SHA：根 `5319ee263c4af41ac255938c25bebd32cce56f66`（fcap）；并行观察 `origin/main@6fb2def709d13bda9cfada7ecf62bfc0e3744ae2` 及 §4 全部 16 个 worktree HEAD。
- 需要总指挥复核的唯一事项（如无写 `none`）：
  1. **fcap↔main 的 UC 门分叉并线策略**（batch-B 严格补丁 vs main 已按 §四十二/§四十四 放宽演进——不能裸合，需指定唯一实现 owner）。
  2. **`rf-impl` 索引中 §四十四（2026-10-03 owner 裁定）的唯一副本**——先决定其入库路径再动 rf-impl。
  3. **`rf-merge-review` 掏空 worktree** 的成因与处置（47,173 D，禁止直接 prune）。
  4. **batch-D「1985 untracked」与实测 0 的对账差异**（含 3 个权限受限目录）。
  5. 「owner decision 2026-10-02 / re-audit batch table」裁定原文**不在本仓**（跨仓可能性未验证——本 lane 禁止读取他仓）。

## 12. 总指挥并线实施附记（2026-10-04）

`fcap` 有价值的 DWA-04R 载体和账本通过稀疏集成树并入 main，采用 merge commit `8a153f3387ae75fb172e70f8ab63ffd38100779a`，并已推送 `origin/main`。45 个同路径 execution-run carrier 保持 main 版本，原 branch 对象由 merge parent 保留；UC 实现按 main 已接受的 §四十四规则，不回退为缺 hash 阻断。UC 聚焦测试 29 passed。稀疏工作树没有 `tools/pre_push_gate.py`，钩子明确跳过，所以该项不是完整 pre-push gate 收据。该附记记录总指挥后续实施，不改变原只读审计报告正文。
