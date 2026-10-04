# Earnings-transcripts — 只读盘点与 ET-DEADLINE 交接验收

## 0. 审计元信息

```yaml
audit_id: "RSA-earnings-transcripts-20261004"
repository: "earnings-transcripts"
repository_root: "C:\\Users\\郑曾波\\Projects\\earnings-transcripts\\earnings-transcripts"
audit_status: "complete"
started_at_local: "2026-10-04 18:16 BST"
finished_at_local: "2026-10-04 18:26 BST"
current_branch: "main"
current_head: "93fe52c450c79dded53fb8b1e466a2193546bb28"
base_ref: "origin/main"
base_sha: "93fe52c450c79dded53fb8b1e466a2193546bb28"
remote_live_check: "ls-remote success"
remote_checked_at: "2026-10-04 17:20 UTC"
source_changes_made: false
tests_run: false
```

## 1. 一页结论

- `codex/et-s3-deadline` 相对 `origin/main` 有 **1 个 branch-only commit**：`0017f24a999c5ecb224b646f47ebc8804769be73`。本地 tip 与 live `origin/codex/et-s3-deadline` 一致，尚未并入 main。
- `codex/et-s3-bounded-runtime` 和本地 `codex/transcript-companion-adapter` 分别落后 `origin/main` 1、3 个提交，branch-only 均为 0；前者 tip 已是 main 的祖先。没有额外未并主线的 ET-S3 runtime 改动。
- main 没有 tracked staged/unstaged 修改；有 3 个 untracked 文件（`.workbuddy-ai/memory/2026-09-03.md`、`.workbuddy-ai/memory/MEMORY.md`、`eval_results.json`），均未被 `.gitignore` 忽略。仅测元数据：前两项合计 2 个文件/5,970 bytes，`eval_results.json` 38,956 bytes。
- Git worktree 共 3 个：main 有上述 untracked 项；deadline 与 bounded-runtime 两个 linked worktree 均干净；没有 detached worktree。
- ET-DEADLINE PWF 的 Stage 1–4 和交接内容都称完成，但 progress 最后仍写“待 commit/push”。该待办已过期：`0017f24` 已在 live 远端支线可见。该分支并未合 main。
- 实施交接记录报告 92 项责任包测试、全量 172 passed、10 个 goldens 匹配、ruff 与 diff check 通过；审计没有重跑。报告和测试变更属于同一唯一 branch-only commit 的工作树快照，但 handoff 没有显式记下最终 SHA，独立 CI URL/原始测试日志也未提供。
- PWF 记录只证明测试用的 gitignored `config.json` 被复制到两个隔离 worktree；没有记录把真实电话会原件复制进这些目录。生产原件目录未被本审计遍历，因此不能据此断言任何目录之间绝无重复。
- 最大后续项：若将 ET-DEADLINE 并入主线，应由总指挥做一次 FF→ET→CWP 的离线契约联调；本施工包不合并、不清理、不修改任何 ET 内容。

## 2. 主线与远端

| 线索 | ref/值 | SHA/结果 | 证据 | 解释 |
|---|---|---|---|---|
| 远端默认线 | `origin/HEAD -> origin/main` | `93fe52c450c79dded53fb8b1e466a2193546bb28` | `git symbolic-ref refs/remotes/origin/HEAD` | 默认分支是 main |
| 本地主线 | `main` | 同上 | `git rev-parse main`、状态 | 与 tracking ref 相同 |
| live 远端主线 | `origin/main` | 同上 | 2026-10-04 `git ls-remote` | tracking ref 当前未过期 |
| deadline live 分支 | `origin/codex/et-s3-deadline` | `0017f24a999c5ecb224b646f47ebc8804769be73` | `git ls-remote` | 与本地 deadline tip 相同 |
| runtime live 分支 | `origin/codex/et-s3-bounded-runtime` | `53e1e60633e6e1fa225f308c2d0be84dea4cfeaa` | `git ls-remote` | 已无独有提交，tip 已在 main 历史中 |

## 3. Branch 矩阵

`git rev-list --left-right --count origin/main...<branch>` 的左列是 main-only，右列是 branch-only。

| branch | tip | merge-base | 左/右计数 | Patch/变更 | 判断 |
|---|---|---|---:|---|---|
| `main` | `93fe52c` | — | `0/0` | live `origin/main` 同 SHA | 主线 |
| `codex/et-s3-deadline` | `0017f24` | `93fe52c` | `0/1` | `git cherry` 为 `+`；唯一提交 `feat: enforce hard retrieval deadline via supervised worker subprocess`，作者时间 2026-10-04 17:11:39 +01:00；13 个路径，2,441 insertions / 328 deletions，包含实现、测试、PWF 与 handoff | `merge_candidate`；只在独立工作线，尚未并 main |
| `codex/et-s3-bounded-runtime` | `53e1e60` | `53e1e60` | `1/0` | branch tip 是 `origin/main` 祖先；无 branch-only patch | `already_in_base`；本地/远端旧 branch 可后续另行归档判断 |
| `codex/transcript-companion-adapter` | `4924d57` | `4924d57` | `3/0` | branch tip 是 `origin/main` 祖先；无 branch-only patch，未发现同名 live remote ref | `already_in_base`；本地旧 ref，无当前独有提交 |

deadline 提交变更路径：`.planning/s3-et-deadline-20261004/{findings,progress,task_plan}.md`、`README.md`、`docs/implementation/s3-et-deadline-handoff.md`、`retrieval_budget.py`、`retrieval_runtime.py`、`retrieval_worker.py`、`scraper.py`、`transcript_tool.py`、`tests/test_batch_runtime.py`、`tests/test_retrieval_cli_e2e.py`、`tests/test_retrieval_runtime.py`。

## 4. Worktree 矩阵

| 路径 | 分支 / HEAD | 状态 | PWF / 来源 | 判断 |
|---|---|---|---|---|
| `C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts` | `main` / `93fe52c` | tracked clean；3 个 untracked 文件 | owner checkout；runtime handoff 说明这两类本机资料未复制或清理 | 保留 owner 状态，不清理 |
| `C:\Users\郑曾波\Projects\earnings-transcripts-s3-deadline` | `codex/et-s3-deadline` / `0017f24` | clean | `.planning/s3-et-deadline-20261004/` 与交接文档 | 独有实现分支；供总指挥决定后续联调/并线 |
| `C:\Users\郑曾波\Projects\earnings-transcripts-s3-runtime` | `codex/et-s3-bounded-runtime` / `53e1e60` | clean | `.planning/s3-et-bounded-runtime-20261003/` | branch tip 已在 main 历史中 |

## 5. 未提交文件与空间线索

| 路径 | 状态 / 元数据 | 用途证据 | 建议分类 |
|---|---|---|---|
| `.workbuddy-ai/`（当前含 2 个 memory 文件） | untracked、not ignored；2 files / 5,970 bytes；目录最后修改 2026-09-03 | handoff 只说明它是 owner 本机旧笔记；未说明其内容/消费者，本审计未读正文 | `owner_decision_needed`，保留；不根据目录名删除 |
| `eval_results.json` | untracked、not ignored；38,956 bytes；最后修改 2026-07-07 | handoff 称为基线 owner 未跟踪项；无 PWF 证据证明唯一性或可再生性，本审计未读正文 | `owner_decision_needed`，保留；不据文件名推断可删 |
| worktree 私有 `config.json` | Git 忽略的本地配置，deadline/runtime PWF 称复制用于既有 translator 测试、不入 Git | 不同 PWF 有明确记录；内容含本机 LLM key，本审计未打开 | `preserve_active_work`；不读取、不复制、不处理 |

关于原件重复：所读 PWF 明确表示不复制生产 transcript/output，测试输出隔离在临时根；没有实际原件复制的正面证据。未扫描真实文档目录，故是否存在历史重复仍为 `unknown`。

## 6. PWF / 提交 / 测试证据

| 记录 | 声明与核对 | 判断 |
|---|---|---|
| `.planning/s3-et-bounded-runtime-20261003/{task_plan,progress,findings}.md` + `docs/implementation/s3-et-runtime-handoff.md` | handoff 报告 bounded runtime 已并入 main；本地 `codex/et-s3-bounded-runtime@53e1e60` 相对 origin/main branch-only=0，main 比它多 1 个提交 | Git 证据相符 |
| `.planning/s3-et-deadline-20261004/{task_plan,progress,findings}.md` + `docs/implementation/s3-et-deadline-handoff.md` | Stage 1–4 标 Complete；progress 的最后 todo 仍为 commit/push。Git 与 live 远端显示 `0017f24` 已推至 deadline 分支，且相对 main 仍独有 1 个提交 | PWF commit/push 状态过期；实际尚未并 main |
| ET-DEADLINE 责任包测试收据 | progress/handoff 记录 92 项定向测试、全量 172 passed、10 goldens matched、ruff clean、`git diff --check` clean 和零外发 CLI smoke | 仅接受为交接记录的已有证据；未由本审计重跑。handoff 未显式绑定最终 full SHA，也未附 CI run URL |
| E2E/生产数据边界 | ET handoff 声明使用 fake transport、pytest 临时根，无 live provider/LLM 请求；生产原件、CWP 配置、catalog 未读写 | 与只读交接目标一致；跨仓 FF→ET→CWP 联调仍待总指挥决定 |

## 7. 后续处置建议（未执行）

- `codex/et-s3-deadline`：`merge_candidate`。提交与远端一致、分支干净、计划/实现/测试/交接齐全。并线前做一次 FF→ET→CWP 离线契约联调，重点验证 transcript_tool 生产路径、请求/响应 hash 与错误码兼容；不要重复跑整个 ET 测试套件作为审计门。
- `codex/et-s3-bounded-runtime` 与 `codex/transcript-companion-adapter`：`already_in_base`，没有需并入的新提交。
- `.workbuddy-ai/` 与 `eval_results.json`：`owner_decision_needed`，保持不动。
- 是否存在真实 transcript 原件副本：`unknown`；如要审空间，应由独立只读清单比较路径/文件大小和存储证据，不打开正文，不在本卡执行删除。

## 8. 命令与交接声明

执行了只读的 `git status`、`git worktree list`、`git for-each-ref`、`git ls-remote`、`git rev-list`、`git merge-base`、`git cherry`、`git show --stat`、`git diff --check`、`git check-ignore`，以及计划文件读取和 untracked 文件元数据统计。remote live check 成功；一次普通沙箱 GitHub 访问失败后，以命令级正常网络权限重试成功。deadline/runtime 起初因 linked-worktree ownership 被拒读，随后使用每个 worktree 的命令级 `safe.directory` 参数重试；没有修改全局 Git 配置。

- 仅读取 lane 指定的 earnings-transcripts 仓库；没有修改 ET 工作树、索引、refs 或全局配置：**yes**。
- 本审计没有运行测试、构建、下载、provider 或 LLM：**yes**。
- 本报告结论覆盖的主线 SHA：`93fe52c450c79dded53fb8b1e466a2193546bb28`；deadline 交付 SHA：`0017f24a999c5ecb224b646f47ebc8804769be73`。
- 总指挥需复核：ET-DEADLINE 的既有测试记录没有独立 CI URL / 原始日志，且 branch 仍待 FF→ET→CWP 联调与并线决策。
