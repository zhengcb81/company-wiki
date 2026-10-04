# Lane FF — filing-fetch 分支与未提交文件只读盘点

## 0. 审计元信息（必填）

```yaml
audit_id: "RSA-filing-fetch-20261004"
repository: "filing-fetch"
repository_root: "C:\\Users\\郑曾波\\Projects\\filing-fetch"
audit_status: "complete"
started_at_local: "2026-10-04 19:00 +01:00"
finished_at_local: "2026-10-04 19:35 +01:00"
current_branch: "fcap"
current_head: "e1eda607f5536ebf7c498da2a128dedd2c7bd9f3"
base_ref: "origin/main"
base_sha: "e1eda607f5536ebf7c498da2a128dedd2c7bd9f3"
remote_live_check: "ls-remote success"
remote_checked_at: "2026-10-04 19:00-19:10 +01:00 (本 lane 会话内，仅 ls-remote，无 fetch)"
source_changes_made: false
tests_run: false
```

约束执行情况：全程只读；未 fetch/pull/切分支/改索引/prune/合并/提交；未运行测试、下载、FMP API 或 transcript CLI；**`config/FMP_API_KEY.txt` 仅登记存在性，未读取、未复制、未 hash、未输出内容，也未运行任何会用到它的程序**。

## 1. 一页结论

- **branch-only commits 相对 live `origin/main`：仅 1 个** —— `codex/transcript-companion` 上的 `29085f7 "WIP: preserve transcript companion prototype"`（唯一 branch-only 提交，`git cherry` 判定非 patch-equivalent）。其余全部本地分支（含 `main`、`fcap`、`codex/ff-s3-single-request-limits`、`codex/cwp-source-ref-v2-20261004`、两个 phase 分支）对 `origin/main` branch-only = 0，均为 base 的祖先。
- **tracked staged / unstaged 文件：0 / 0**（全部 13 个 worktree 的 porcelain 均无 staged/unstaged 条目）。
- **untracked / ignored candidate**：untracked 1 个（root `config/FMP_API_KEY.txt`，凭据，仅登记存在性）；ignored 按目录汇总 7 组（`e2e/.runs/` 2 run 目录 60 文件 ~26.7 MB、`.coverage`、`.pytest_cache`、`.ruff_cache`、`.mypy_cache` 171 文件、`.benchmarks`、`.codegraph`），均为 gitignore 覆盖的可再生工件。
- **linked worktrees：13 个（含 root）**。dirty 0；detached 8（Temp 1 + `.fcap-review` 7）；active 2（root `fcap`、`filing-fetch-transcript-companion`）；historical/已同步 10；意图无法完全确认 1（`filing-fetch-source-ref-v2-20261004`，建于审计当日、与主线完全同步，lane 指示按"已同步"归类）。
- **PWF 与 Git 差异（Git 已合但 PWF 仍待办）**：
  1. 根 `task_plan.md` 2026-10-03 addendum 未勾选项 "fast-forward to `origin/main`" —— 其关联提交 `cf05f7e`、`492f5d4` 经 `merge-base --is-ancestor` 证实**已在 `origin/main`**，checkbox 过期。
  2. `.planning/s3-ff-single-request-limits-20261003/progress.md` 记 "分支 … **未 push**"、PLANNING_STATUS 2026-10-03 记 "FF main 合并仍等待 …" —— live `ls-remote` 显示远端 `codex/ff-s3-single-request-limits` 已存在于 `5b9a8c1`，且 S3 全部交付提交（`8c340f8`→`776b69d`）**均已在 `origin/main`**，记录已过期。
  3. 反向差异不存在：没有"PWF 称完成但 Git 未合"的提交级案例。
- **最大未决项**：不是 Git 分支问题，而是文档中一致记录的跨仓集成缺口 —— CWP 生产适配器缺 `discover_bounded`/`fetch_bounded`、FF v1 `--allow-download` 与 `mode=latest_as_of` 的预算契约未定（handoff §8.1/§8.3，root 所有，需访问 company-wiki 仓才能核，本 lane 未越界）。仓内最大待决项是 `codex/transcript-companion` 分支的最终归属（见 §9）。

## 2. 主线与远端识别

| 线索 | ref/值 | SHA/结果 | 证据命令/文件 | 解释 |
|---|---|---|---|---|
| `origin/HEAD`（服务端 default） | `refs/heads/main` | `e1eda607` | `git ls-remote origin`（输出含 `HEAD` 与 `refs/heads/main` 同 SHA） | 服务端默认线 = `main` |
| live remote `ls-remote` | `refs/heads/main` / `refs/heads/codex/ff-s3-single-request-limits` | `e1eda607…` / `5b9a8c1…` | `git ls-remote origin` | 远端**只有这两个分支**（无 `codex/transcript-companion`、无 `codex/cwp-source-ref-v2-20261004` 远端 ref） |
| 本地目标主线 | `refs/heads/fcap` | `e1eda607…` = live `origin/main` | `git rev-parse fcap origin/main`；root `git status -b` 显示 `## fcap` | `fcap` 是当前工作分支且与 live main 同 SHA（lane 起点核实成立）；`fcap` 未配 upstream（status 无 tracking 行） |
| 本地 `refs/heads/main` | `c9799b72` | 落后 live main **58** 个提交（自身为祖先） | `git rev-list --left-right --count origin/main...main` → `58 0` | 本地 `main` 只是**过期的本地 ref**，不是当前工作线；不得当作比较线 |
| remote-tracking `origin/main` | `e1eda607` | 与 live 同 SHA | 对比 `ls-remote` 与 `git rev-parse origin/main` | 本次检查时 remote-tracking **未过期**；按 lane 约束未 fetch 刷新 |
| remote-tracking `origin/codex/ff-s3-single-request-limits` | `5b9a8c1` | 与 live 同 SHA，但落后 live main 3 个提交 | `ls-remote` + `git rev-list --left-right --count origin/main...origin/codex/ff-s3-single-request-limits` → `3 0` | 该远端分支 ref **内容过期**（其 tip 已在 main 上，见 §3）；不得据此报"待并线" |
| 工作 checkout | root worktree | `HEAD = e1eda607`，branch `fcap` | `git worktree list --porcelain` | 当前唯一主工作树 |

## 3. Branch 矩阵（base = live `origin/main @ e1eda607`）

`git rev-list --left-right --count origin/main...<branch>` 原始解释：**左列 = base-only（main 有而分支没有），右列 = branch-only（分支有而 main 没有）**。

| branch ref | tip SHA | merge-base | base-only | branch-only | patch-equivalent / cherry | diff stat（base...branch） | PWF/交接关联 | 当前判断 |
|---|---|---|---:|---:|---|---|---|---|
| `fcap`（工作分支） | `e1eda607` | `e1eda607` | 0 | 0 | — | 空 | 根 PWF（历史存档） | 与 live main 同步，`no_change` |
| `main`（本地） | `c9799b72` | `c9799b72` | 58 | 0 | 祖先关系成立（`--is-ancestor` 过） | 空 | — | 过期本地 ref，全部提交已在 base → `already_in_base` |
| `codex/transcript-companion` | `29085f76` | `d35b6f5b`（2026-09-15） | 19 | **1** | `git cherry origin/main …` → `+ 29085f76…`（非 patch-equivalent，main 无等价补丁） | 5 files, +1043/-14 | 无自有 PWF/handoff（其 worktree 内三件套 = base 旧版）；根 `findings.md` 2026-10-03 记录"未整体并入"决定 | **唯一 branch-only 分支**，见 §9 与下文专项 |
| `codex/ff-s3-single-request-limits`（本地） | `1d0c73c2`（2026-10-04 07:20） | `1d0c73c2` | 1 | 0 | `git cherry origin/main origin/codex/…` → **空**（无独有补丁） | 空 | FF-S3 局部 PWF + `docs/implementation/s3-ff-limits-handoff.md` | **已并入 main，无独有提交**（见下方专项） |
| `codex/cwp-source-ref-v2-20261004` | `e1eda607` | `e1eda607`（与 tip 同） | 0 | 0 | — | 空 | lane 起点：与主线 tip 相同 | **已同步**，勿重复集成 → `no_change` |
| `codex/ff-source-companion-integration` | `c47c397c`（2026-10-03） | `c47c397c` | 10 | 0 | 祖先关系成立 | 空 | SourceRef v2 集成前的中间态 | `already_in_base` |
| `codex/ff-source-reader-v2-20260927` | `aaf35bc1`（2026-09-29，"WIP: preserve SourceRef v2 pathless candidate work"） | `aaf35bc1` | 17 | 0 | 祖先关系成立 | 空 | 其 WIP 内容已随后续 `bb84c9b`/`90771d8` 等进入 main | `already_in_base` |
| `phase-15-lock-retry` | `a9bf70b0`（2026-08-01） | `a9bf70b0` | 109 | 0 | 祖先关系成立 | 空 | 旧 Phase 16.4 时代 | `already_in_base` |
| `phase-19-ambiguous-candidates` | `fd95d30e`（2026-08-02） | `fd95d30e` | 107 | 0 | 祖先关系成立 | 空 | 旧 Phase 19.6 时代 | `already_in_base` |
| `origin/codex/ff-s3-single-request-limits`（远端 live） | `5b9a8c1`（2026-10-04 02:05） | `5b9a8c1` | 3 | 0 | cherry 空 | 空 | S3 分支的远端发布 ref | tip 已在 main；ref 落后 3 → `already_in_base`（ref 是否清理属 owner） |

无 tags、无 stash（`git tag`、`git stash list` 均为空）。

### 3.1 FF-S3 专项结论（lane 必答）

**FF-S3 已并入 main，本地分支没有任何独有提交。** 三重证据：

1. **ancestry**：`git merge-base --is-ancestor codex/ff-s3-single-request-limits origin/main` → 通过（ahead=0）；`git rev-list --left-right --count origin/main...<branch>` = `1 0`（右列 branch-only = 0）。
2. **`git cherry`**：`git cherry origin/main origin/codex/ff-s3-single-request-limits` 输出为空 —— 远端分支所有提交在 base 中既有 SHA 也在（无 cherry-pick/squash 差异）。
3. **live `ls-remote`**：远端 `codex/ff-s3-single-request-limits = 5b9a8c1`，且 `git log origin/main --oneline --grep=…` 显示 S3 全部交付提交 `8c340f8`（实现主体）、`0f27606`（补记 head）、`820624c`（worker 契约）、`bd6d053`（行尾守卫）、`776b69d`（blocked-push 记录）**全部出现在 `origin/main` 历史中**（快进合并，`git log --merges` 为空，无 merge commit）。

**"ahead 2" 的真实含义**：本地分支 tip `1d0c73c2` 相对其 *tracking ref*（`origin/codex/ff-s3-single-request-limits = 5b9a8c1`）领先 2 个提交（`2936ad1`、`1d0c73c`），但这两个提交本身是 mainline 提交且都在 `origin/main` 上。这是 **tracking ref 落后**，不是分支领先 —— 不得报为待并线（与 lane 起点提示一致）。

### 3.2 transcript-companion 唯一 branch-only 提交专项（lane 必答）

`29085f76ed60b9fc756b613c870288670566f720` — "WIP: preserve transcript companion prototype"，作者 `zhengcb81`，2026-09-29 18:41:15 +0100，父提交 `d35b6f5b`（2026-09-15）。`git show --name-status`：

| 路径 | 状态 | 变更 |
|---|---|---|
| `scripts/transcript_companion.py` | A | +589 行（新模块） |
| `tests/test_transcript_companion.py` | A | +253 行（新测试） |
| `scripts/fetch_filing.py` | M | +68/-…（CLI 与编排接线） |
| `scripts/filing_contracts.py` | M | +76/-…（schema 校验） |
| `SKILL.md` | M | +71/-…（v1.5.0 与 companion 章） |

合计 5 files, +1043/-14。按类型计数：**代码 4 / 测试 1 / 计划 0 / 文档 1**。

**变更行为（来自提交 diff 与分支文件读取，未复制全文）**：

- 引入**请求 schema 1.3** 与 `companion_transcript` 子对象（`mode: reuse_only|fetch_if_missing`、`fiscal_year`、`fiscal_quarter`、`provider`、`download_authorized`、`max_body_bytes` 默认 4 MiB 上限 10 MiB、可选 `discovery_url`）。
- 新 CLI 旗标：`--allow-transcript-download`（独立授权）、`--transcript-tool PATH`（**默认值为 sibling checkout 猜测路径** `parents[2]/earnings-transcripts/earnings-transcripts/transcript_tool.py`）、`--transcript-wiki-src PATH`。
- 直接以子进程调用 `earnings-transcripts/transcript_tool.py` 的 `discover`/`fetch-candidate` JSON 接口（schema `earnings-transcript-discovery-result/1`、`earnings-transcript-result/2`），含 company-wiki rights preflight（`rights_policy_sha256`、`provider_use_policy_denied`）、`discovery_url` 端点核验（Motley Fool URL 与 ticker/exchange 清单精确匹配）、有界输出（24 MiB/2 MiB/16 KiB）、单总 deadline、base64 原文搬运与 importer 落盘。
- 响应侧新增顶层 `transcript` 子结果（`not_requested/not_applicable/reused/downloaded/rights_blocked/not_authorized/not_found/ambiguous/upstream_error/validation_error/persist_error`），transcript 失败不影响 filing handle（exit 0）。

**测试**：分支仅新增测试文件本身，**没有任何该分支的执行报告/收据**（worktree 内无 PWF、无 handoff、无 run 记录；`git status` 干净）。

**与 main 现有能力的重合/差异**：

| 维度 | 分支原型（29085f7） | `origin/main` 现状 | 关系 |
|---|---|---|---|
| companion 功能本体 | `transcript_companion.py` 直连 ET 工具 | `cf05f7e "feat: integrate transcript companion with SourceRef"` + `492f5d4` 落地：`transcript_companion.py`（Protocol 化重写）、`transcript_tool_transport.py`（`EarningsTranscriptsTransport`）、`et_v2_contract.py`（ET `/2` 绑定）、CWP `/3` pathless SourceRef 导入、`source_reader_cli` 重开与 `unknown_publication` 去重 | **能力已被 main 交付**，但架构不同（main 走 v2 envelope + transport，非 schema 1.3 直连） |
| `companion_transcript` 请求字段 | 有（schema 1.3） | 有（`filing_contracts.py::_validate_companion_request`：`intent/fiscal_year/fiscal_quarter/provider/acquisition_limits`） | 概念重合；字段从 `mode` 改为 `intent`，schema 常量 `COMPANION_*` **未**被采纳（main 仍为 1.2/1.1/2.0） |
| 工具路径配置 | 猜测 sibling checkout 默认路径 + `--transcript-tool` | `EARNINGS_TRANSCRIPTS_TOOL` 环境变量（`transcript_tool_transport.py:48`），未配置 → `transcript_tool_not_configured` | main **有意替换**了猜测路径（`findings.md` 记为不整体并入的理由之一） |
| `--allow-transcript-download` / `--transcript-wiki-src` / `discovery_url` 权利预检 | 有 | `git grep` 均无 | **仅存在于原型**（未采纳，也未见等价替代；`discovery_url` 端点核验是原型独有设计） |
| `max_body_bytes` | 原型自带 | main 由 `acquisition_limits.max_bytes` 经 `transcript_tool_transport.py:301` 提供 | 等价能力，来源不同 |
| 测试 | 原型 253 行 | `tests/test_transcript_companion.py`（与原型 diff：+232/-173，已大幅演化）+ `test_transcript_companion_transport.py`（新增） | main 测试独立演化，**原型测试未原样保留** |

**完整度/唯一价值结论**：这是一个**有意留存的原型快照（commit 标题即 "preserve … prototype"），不是待交付分支** —— 无自有 PWF、无 handoff、无测试执行记录，base 落后 main 19 个提交，其 schema 1.3/猜测路径设计与 main 已交付的 v2 契约**直接冲突**，整体并入会构成回退。**唯一价值**是历史设计档案：`discovery_url` 权利端点核验、独立 transcript 授权旗标、schema 1.3 原始契约与原始 253 行测试，均只在这一个提交里可考。仓内 `findings.md` 2026-10-03 条目已明确记录"standalone companion branch was not merged wholesale"的决定，与 Git 状态一致。

## 4. Worktree 矩阵

来源命令：`git worktree list --porcelain`（13 行）+ 每树 `git status --porcelain=v1 -b`。**全部 13 棵树 porcelain 无任何 staged/unstaged/untracked 条目**（root 除外，见 §5）；按 lane 约束未 prune、未移除、未切换。

| worktree path | branch/detached | HEAD SHA | porcelain 状态 | PWF/owner/创建来源 | 可能用途 | 确定度 |
|---|---|---|---|---|---|---|
| `C:\Users\郑曾波\Projects\filing-fetch`（root） | `fcap` | `e1eda607` | clean（+1 untracked 见 §5） | 根 PWF 三件套 + `.planning/s3-…/` + `PLANNING_STATUS.md` | **active**：主工作树，= live main | 高 |
| `…\Projects\filing-fetch-s3-limits` | `codex/ff-s3-single-request-limits` | `1d0c73c2` | clean | FF-S3 局部 PWF 所指"唯一写入工作目录"，建于 2026-10-03 | **historical**：S3 交付已完成并入 main；无未提交工作 | 高 |
| `…\Projects\filing-fetch-source-ref-v2-20261004` | `codex/cwp-source-ref-v2-20261004` | `e1eda607` | clean | 目录建于 2026-10-04（审计当日）；分支 = main tip | **已同步/idle**（lane 指示按已同步归类，勿重复集成）；当日创建的真实意图本仓无证据 | 中（按 lane 指示归类） |
| `…\Projects\filing-fetch-transcript-companion` | `codex/transcript-companion` | `29085f76` | clean | 目录建于 2026-09-27、末改 2026-09-29（WIP 提交日）；worktree 内 PWF 三件套 = base `d35b6f5` 旧版（非分支自有） | **active（唯一 branch-only 分支的唯一 checkout）**，原型留存处 | 高 |
| `…\AppData\Local\Temp\ff-source-reader-v2-20260927` | `codex/ff-source-companion-integration` | `c47c397c` | clean | 路径名标注 2026-09-27 source-reader v2；建 09-27、末改 10-03 | **historical**：临时集成 checkout，tip 已在 main | 高 |
| `…\AppData\Local\Temp\filing-fetch` | detached | `89c8bdb2`（2026-09-02） | clean | Temp 临时 checkout，建/末改 2026-10-03；HEAD = 文档多次引用的 9 月基线 `89c8bdb` | **historical**：净基线对照 checkout（如 S3 环境红灯复现） | 中高 |
| `…\Projects\.fcap-review\fc-1003-fil` | detached | `7745eb19`（2026-08-12） | clean | FC-1003 评审会话，建 2026-08-12 | **historical** review 树 | 高 |
| `…\.fcap-review\fc-1101-fil` | detached | `592fae61`（2026-08-12） | clean | FC-1101 评审会话，建 2026-08-12 | **historical** review 树 | 高 |
| `…\.fcap-review\fc-1204\base-filing` | detached | `b7ef9cca`（2026-08-12） | clean | FC-1204 评审基线，建 2026-08-13 | **historical** review 树 | 高 |
| `…\.fcap-review\fc-1204\layout\filing-fetch` | detached | `93aa5ad1`（2026-08-13） | clean | FC-1204 layout 变体 | **historical** review 树 | 高 |
| `…\.fcap-review\fc-1204\r2\filing-fetch` | detached | `83c638e7`（2026-08-13） | clean | FC-1204 r2 | **historical** review 树 | 高 |
| `…\.fcap-review\fc-1205\filing-fetch` | detached | `83c638e7`（同上） | clean | FC-1205 评审，与 r2/130x 同一 tip | **historical** review 树 | 高 |
| `…\.fcap-review\fc-130x\filing-fetch` | detached | `83c638e7`（同上） | clean | FC-130x 评审，与 r2/1205 同一 tip | **historical** review 树 | 高 |

- 全部 8 棵 detached 树的 HEAD 经 `merge-base --is-ancestor` 证实**均为 `origin/main` 祖先**（历史评审/基线快照，无未合并内容）。
- 路径均存在且可访问；无失效链接；**未执行任何 prune/remove**。
- 分类汇总：active 2、historical 10、已同步 1、dirty 0、无法确认 0（`filing-fetch-source-ref-v2-20261004` 的"创建于当日"动机无法从本仓取证，但其状态已按 lane 指示确定归类）。

## 5. 当前未提交文件

| 路径 | Git 状态 | staged diff | unstaged diff | 类型/可能用途 | PWF/commit/调用者证据 | 敏感性 | 推荐后续分类 |
|---|---|---|---|---|---|---|---|
| `config/FMP_API_KEY.txt`（root） | **untracked**（`??`；未被 .gitignore 覆盖） | 无 | 无（untracked 无 diff） | 本地 FMP API 凭据，供真实下载/ET 测试使用 | lane 文档明示存在；`tools/sync_installs_b3.py` 安装面已以凭据命名闸排除（S3 handoff §9）；`.planning` 记录测试用假 key 临时创建/删除 | **敏感：凭据**。按 lane 约束**仅登记存在性**：未读取、未复制、未 hash、未输出内容/大小 | `preserve_active_work`（保留原地、本次不接触；是否补 `.gitignore` 等后续动作由 owner 决定） |

- staged 条目：全仓 0；unstaged 条目：全仓 0。
- 其他疑似敏感文件（仅 path/status/size 级排查）：`tests/fixtures/et_s0b/fmp_v2.credentials_missing.json` —— **tracked 测试夹具**（负面用例），非未提交凭据，不属本节处置。
- 所有 `git diff` 输出均未包含密钥文件（untracked 不进入 diff）。

## 6. 未跟踪/ignored 工件及空间线索

| 目录/文件 | Git ignored/untracked 状态 | 文件数/总字节 | 创建/消费证据 | 是否唯一审查/测试证据 | 可再生证据 | 结论/未决 |
|---|---|---:|---|---|---|---|
| `config/FMP_API_KEY.txt` | **untracked** | 未测量（lane 约定仅登记存在性） | owner 本地凭据 | 是（本机唯一 key 副本，不可再生） | 否 | 保留原地，本 lane 不接触 |
| `e2e/.runs/`（2 个 run 目录：`biren-e2e-v1-08154ff2c106`、`biren-e2e-v1-9fb7f4276ba1`） | ignored（`.gitignore` 注明 "E2E run artifacts (regenerable)"） | 60 文件 / 26,715,102 B | run 目录 mtime 2026-08-07 / 2026-08-18；`e2e/run_companies_reuse_only_e2e.py` 消费；S3 handoff §11 记 CI 已改用 `e2e/test_source_ref_v2_cli.py` 替代持久 `.runs` harness | 否（synthetic T1 夹具，历史运行残留） | 是（重跑 harness 可再生） | `generated_candidate_review`（删除前确认无脚本仍读取；本 lane 不动） |
| `.coverage` | ignored | 98,304 B，mtime 2026-08-16 | 旧 coverage 运行产物 | 否 | 是 | `generated_candidate_review` |
| `.pytest_cache/`（5 文件）、`.ruff_cache/`（14）、`.mypy_cache/`（171）、`.benchmarks/`（0）、`__pycache__/` | ignored | 低 | 工具缓存 | 否 | 是 | `generated_candidate_review` |
| `.codegraph/` | ignored（注明 regenerable） | 5 文件 | CodeGraph MCP 索引 | 否 | 是 | `generated_candidate_review` |

未做全盘递归扫描；取证仅限 dirty/计划明示目录与其下级。无"名字含 temp/cache 即删"的判定。

## 7. PWF 与 commit 记录对照

活动计划 selector：`PLANNING_STATUS.md`（Current checkpoint 2026-10-03）指定**当前施工入口 = `.planning/s3-ff-single-request-limits-20261003/`**，跨仓总计划在 company-wiki 仓（只读引用，未访问）。根 `task_plan.md`/`progress.md`/`findings.md` 被 `TERMINAL_NOTICE.json` 标为 `closed_superseded_incomplete`（历史存档，非活动队列）。

| PWF 位置/plan id | PWF 声明状态/最后时间 | 关联 SHA/工作树 | Git/现存测试/CI 收据核验 | 一致/冲突/不确定 |
|---|---|---|---|---|
| `.planning/s3-ff-single-request-limits-20261003/`（活动入口） | 2026-10-03：实现+责任测试已交付；"分支…**未 push**"；"跨仓 producer 限额及 v1/latest_as_of 仍由 root 收敛" | 分支 `codex/ff-s3-single-request-limits`，worktree `filing-fetch-s3-limits` | S3 全部提交（`8c340f8`…`776b69d`）**已在 origin/main**；远端分支已存在（live `5b9a8c1`）→ push/merge 语句**过期**；跨仓缺口（§8.1/§8.3）本仓无法核验 | **部分冲突**：Git 已合 vs 记录称未 push；跨仓待办 = 不确定（需 company-wiki 仓） |
| `docs/implementation/s3-ff-limits-handoff.md` | 交付交接 + §10 root 动作清单（4. 重跑 hermetic 再 push；5. 合 main） | 同上 | 动作 4/5 的结果 Git 已体现（分支内容在 main）；§8.1 "producer pending" 与 §8.3 三问仍无仓内闭环证据 | 部分过期（§10）/ 部分待 root（§8，不确定） |
| 根 `task_plan.md`（历史存档）2026-10-03 addendum | 未勾选 "Finish the required full pre-push gate and fast-forward to `origin/main`" | `cf05f7e`、`492f5d4` | `git merge-base --is-ancestor`：两者**均在 origin/main**；`8f17cbd "ci: simplify FF regression and push gates"` 亦在 | **冲突（checkbox 过期）**：Git 已合但 PWF 仍待办 |
| 根 `progress.md`（历史存档）2026-10-03 末条 | "Final full pre-push gate and remote fast-forward are **pending**" | 同上 | 同上，已被 main 后续提交推翻 | **冲突（记录过期）** |
| `PLANNING_STATUS.md` checkpoint 2026-10-03 | "FF main 合并仍等待 CWP 真实 provider 限额能力和 v1/latest_as_of 契约收敛" | S3 提交当时未合 | 截至审计时 S3 提交**已在 main**（其后 2026-10-04 又有 `2936ad1/1d0c73c/e1eda607` 落地）→ 合并已发生；但"跨仓能力未收敛"陈述无仓内反证 | **部分冲突**（合并句过期）/ 跨仓句不确定 |
| `codex/transcript-companion` 分支自身 PWF | **不存在**（worktree 内三件套 = base `d35b6f5` 版本，与 main 仅差 44 行主线新增，无分支特有内容） | `29085f76` | 无 handoff、无测试执行报告；根 `findings.md` 2026-10-03 明确记录不整体并入的决定 | 一致（"WIP 留存"意图与 Git 状态相符）；但分支自身缺计划记录 = 不确定其未来处置 |
| `assurance/fc/FC-903/`（change contract + 两 receipt） | 历史审查证据，保持原字节 | 旧 triplet 时代 | `PLANNING_STATUS` §66 记载 `receipt_binding_mismatch`（SHA256 不匹配，CRLF 归一化后仍不符），未复核 | 历史证据，冲突已知且已登记；本 lane 不重验 |
| CWP 计划卡本仓只读副本 / FF v2 集成独立 handoff | **不存在独立副本** | — | `docs/` 全历史仅 `implementation/s3-ff-limits-handoff.md` 一个文件；CWP 计划卡在本仓只有**指针**（`.planning/…/task_plan.md` 第 3 行指向 company-wiki `docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/s3_…`；`PLANNING_STATUS` 第 5 行同指）。FF v2 集成证据 = 提交序列 `aaf35bc→90771d8→bb84c9b→be1f375→37d2258→5532ce0→cf05f7e→492f5d4` + fixtures | 不确定/缺失：按 lane"只读本仓内已有副本"，如实记为**本仓无副本，仅有跨仓引用** |
| ET/CWP consumer 测试收据（本仓内已有） | `tests/fixtures/cwp_source_v2/`（SourceRef + verified_open receipt 夹具 4 件）、`tests/fixtures/et_s0b/`（ET v2 契约 6 件 + manifest）、`tests/fixtures/s3_fake_cwp/` | tracked 夹具，随 main | 与 `.planning` 记录的责任包/CI 精选回归（含 `test_transcript_companion*`、`test_source_ref_v2*`）对应 | 一致（夹具在 main 上；执行数字见 §8） |

## 8. 已有测试、CI、E2E 证据（仅查记录，不运行）

| 命令/Workflow/报告 | 绑定 SHA | 结果与日期 | 是否覆盖 branch-only / dirty 行为 | 限制 |
|---|---|---|---|---|
| `quality.yml`（唯一 workflow，push/PR 触发） | checkout 为触发时 SHA（本地无法定值） | 步骤：ruff/compileall/import smoke → scoped mypy → 唯一符号门 → **精选回归一次性**（含 `test_transcript_companion{,_transport}`、S3 12+6、`e2e/test_source_ref_v2_cli.py` 等 19 文件）→ config doctor → plan verifier | 覆盖 main 上的 companion/S3 行为；**不覆盖** `29085f7` 分支本身 | 只读 workflow 文件；**未查询 GitHub Actions 在线状态**（lane 禁网络操作外推） |
| 记录：CI 全绿快照 | `bb8d485` 时代 | `progress.md` 2026-09-09："quality.yml … 最近一次推送全绿" | 否（早于 companion/S3） | 历史记录 |
| 记录：S3 责任包 | `8c340f8` 后 | `337 passed, 3 skipped, 78 subtests`（60.96s），RED 18 failed | 是（S3 branch 交付内容） | 本地记录，未重跑 |
| 记录：全量 hermetic | 同上 | `450 passed, 8 skipped, 2 failed`（2 环境红灯：行尾守卫 + worker 退役，均净基线可复现） | 部分 | 本地记录 |
| 记录：root review 精选回归 | 2026-10-03 | `358 passed, 4 skipped, 78 subtests`（62.99s）+ SourceRef CLI E2E `1 passed`（11.45s，隔离合成 wiki、0 下载） | 是（S3 + v2 契约） | 本地记录 |
| 记录：CWP/ET 集成节点 | `cf05f7e`/`492f5d4` | `191 passed, 1 skipped`（50.40s，唯一 skip 为既有生产 opt-in）+ lookup/E2E `18 passed` + CWP 侧 `16 passed`；Ruff/mypy 绿 | 是（companion 集成主线） | 本地记录；RF consumer G-A E2E **明确未做**（跨仓，仓外） |
| 记录：push 尝试（被拦，未绕过） | S3 分支推送时 | `10 failed, 442 passed, 8 skipped` → `PUSH BLOCKED by pre-push gate`（2026-10-03，后经简化门禁） | 是 | 历史失败记录，已登记根因 |
| 覆盖率记录（同 CI 命令） | 净基线 `c47c397` → S3 交付 | `81.66% → 82.22%`，`--cov-fail-under=90` 两端本地均红（既有状态） | 部分 | 既有缺口，非本 lane 处置 |
| `e2e/.runs/` 运行残留 | 2026-08-07 / 08-18 | 目录存在，无汇总报告文件 | 否（synthetic T1） | 可再生 |
| `codex/transcript-companion@29085f7` 自身测试执行 | — | **无任何记录**（分支无报告/无 CI ref——远端不存在该分支） | **branch-only 行为从未有执行收据** | 本 lane 未运行 |

## 9. 建议的后续处置类别（不执行）

| 对象 | 类别 | 证据 |
|---|---|---|
| `fcap` / `origin/main` @ `e1eda607` | `no_change` | 工作线与 live main 同 SHA，树净 |
| `codex/ff-s3-single-request-limits`（本地） | `already_in_base` | ancestry + cherry + ls-remote 三证：0 独有提交；仅本地 ref 指针待 owner 归整 |
| `origin/codex/ff-s3-single-request-limits`（远端 ref） | `already_in_base` | tip `5b9a8c1` 已在 main；ref 落后 3；是否删远端分支属 owner 决定 |
| `codex/cwp-source-ref-v2-20261004` + worktree | `no_change` | 0/0 与主线同 tip、树净；lane 指示"已同步，勿重复集成" |
| `codex/transcript-companion` + worktree | `unique_evidence_preserve` | 唯一 branch-only 提交是原型唯一存档（discovery_url 权利预检、独立授权旗标、schema 1.3、原始测试）；**不是 merge_candidate**（与 main v2 契约冲突，整体并入=回退）；最终归档/放弃需 owner 定 |
| 本地 `main` / `codex/ff-source-companion-integration` / `codex/ff-source-reader-v2-20260927` / `phase-15-lock-retry` / `phase-19-ambiguous-candidates` | `already_in_base` | 全部为 `origin/main` 祖先，branch-only = 0 |
| root `config/FMP_API_KEY.txt` | `preserve_active_work` | owner 凭据，本 lane 未接触；处置（含是否 gitignore）归 owner |
| `e2e/.runs/`、`.coverage`、各工具缓存、`.codegraph/` | `generated_candidate_review` | gitignore 注明 regenerable；`.runs` 消费者为旧 harness（CI 已替代）；删除前仍需验证无脚本引用 |
| `.fcap-review/*`（7 棵）与 Temp 两棵 | `no_change` | 全净、HEAD 均为祖先、来源可考（FC 评审会话/基线对照）；空间清理属后续总指挥计划，本 lane 不提议删除命令 |
| `filing-fetch-s3-limits` worktree | `no_change` | 树净、分支已并入；其 PWF 为 tracked 内容（main 上同样存在），worktree 本身无独有状态 |
| `filing-fetch-transcript-companion` worktree | `unique_evidence_preserve` | 与所驻分支同结论 |
| 过期 PWF 记录（§7 冲突行：未 push/未合并 checkbox） | `owner_decision_needed` | 事实已由 Git 证实，但**修订 PWF 文档**超出本 lane 只读边界，须由总指挥另行授权 |

## 10. 检查命令与结果（脱敏）

| 命令（均为只读） | 退出码/结果 |
|---|---|
| `git -C <root> status --porcelain=v1 -b` | 0；`## fcap` + 1 untracked |
| `git worktree list --porcelain` | 0；13 worktree |
| 每树 `git status --porcelain=v1 -b`（12 次） | 0；全部仅输出分支头 |
| `git ls-remote origin` | 0；2 分支 + HEAD（唯一网络操作，只读） |
| `git for-each-ref refs/heads refs/remotes` | 0；9 本地分支 + 3 远端 ref |
| `git rev-list --left-right --count origin/main...<ref>`（10 次） | 0；见 §3 |
| `git merge-base --is-ancestor <c> origin/main`（逐分支 + 8 棵 detached HEAD） | 0/1 如实记录；除 `transcript-companion` 外全过 |
| `git cherry origin/main codex/transcript-companion` | 输出 `+ 29085f76…` |
| `git cherry origin/main origin/codex/ff-s3-single-request-limits` | 输出空 |
| `git show --stat/--name-status 29085f76` | 0；5 files +1043/-14 |
| `git diff --stat origin/main...codex/transcript-companion` | 0；同上（单提交） |
| `git log --merges origin/main` | 空（全部快进） |
| `git grep -e <pattern> origin/main -- scripts SKILL.md tests`（十余模式） | 0；结果见 §3.2 |
| `git tag` / `git stash list` | 空 / 空 |
| `Get-ChildItem`（PWF/docs/fixtures/ignored 目录计数） | 0 |

**跳过项**：`fetch`/`pull`、分支切换、`gc/prune`、任何写操作（lane 禁止）；测试执行与 CI 在线查询（lane 禁止运行/网络外推）；key 正文及 hash（lane 禁止）；company-wiki / earnings-transcripts / revenue-forecast 等他仓源码（lane 禁止，跨仓只记引用）。

## 11. 交接声明

- 我只读取 lane 指定的仓库，没有改动工作树、索引、Git refs、全局配置或其他项目：`yes`。（他仓仅读取本 lane 文件指定的 company-wiki 计划文档两份：本 lane 定义文件与 handoff 模板，未读其他仓源码。）
- 我没有运行会写文件的测试、构建、下载或 provider/LLM：`yes`。（唯一网络操作为 `git ls-remote`，只读。）
- 本报告结论覆盖的 HEAD SHA：`e1eda607f5536ebf7c498da2a128dedd2c7bd9f3`（root = `fcap` = live `origin/main`，2026-10-04 12:28:30 +0100，"fix: keep partial capture metadata diagnostic for SourceRef v2"）。
- 需要总指挥复核的唯一事项：**§7 中三处"Git 已合但 PWF 仍记待办/未 push"的过期记录修订授权**（涉及 `.planning/s3-…`、`PLANNING_STATUS.md`、根 `task_plan/progress` addendum——后者为 TERMINAL_NOTICE 存档，是否改写须另定）；以及 `codex/transcript-companion` 的最终归档/放弃决策（本 lane 仅建议 `unique_evidence_preserve`，不代决）。

## 并线与 PWF 收尾附记（2026-10-04）

复核确认 FF-S3 与 SourceRef v2 companion 已在 main；旧 `codex/transcript-companion` branch-only 原型不整笔合并。随后仅修订过期 PWF 状态并提交 `d4d2fac4c690bfb8b1368d2ca140fd75150fd288`，已推送 `fcap:main`。计划声明校验通过，push 精选门中的 Ruff、compileall、import smoke、mypy、测试唯一性检查、host assumption、config doctor、plan claims 与 BOM 检查均为 GREEN。`config/FMP_API_KEY.txt` 全程未读、未暂存、未推送。该附记是后续集成记录，不改变本报告的只读审计范围。
