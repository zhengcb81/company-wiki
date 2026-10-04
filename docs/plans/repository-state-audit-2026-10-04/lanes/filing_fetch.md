# Lane FF — filing-fetch 分支与未提交文件只读盘点

## 目标与边界

唯一目标仓：`C:\Users\郑曾波\Projects\filing-fetch`。只读当前 `fcap/main`、transcript-companion、FF-S3 worktree 及 SourceRef refs/PWF。不要读取其他仓库源码；跨仓依赖只记引用。

严禁 fetch/pull/切换分支/改索引/清理/合并/提交。**`config/FMP_API_KEY.txt` 是未跟踪凭据文件，严禁读取、复制、hash、输出内容或运行会用到它的程序。** 不运行测试、下载、FMP API 或 transcript CLI。

## 已知起点（审计时重查）

- root `fcap@e1eda607` 与 live `origin/main` 同 SHA。
- `codex/transcript-companion@29085f7` 对 origin/main 初查有 1 个 branch-only WIP commit，源代码差异包括 `scripts/transcript_companion.py` 和 FF CLI/contracts/skill。
- `codex/ff-s3-single-request-limits` checkout 相对自己的远端 tracking ref 显示 ahead 2；本轮相对 `origin/main` 没检出 branch-only commit，可能已集成但 tracking ref 落后。必须用 ancestry、`git cherry` 和当前 `ls-remote` 证实，不能报为待并线。
- `codex/cwp-source-ref-v2-20261004` 与当前主线 tip 相同（初查）；核实后归类为已同步，不要重复集成。
- root 有未跟踪 `config/FMP_API_KEY.txt`，只登记存在性。

## 必读记录顺序

1. 当前 active PWF 与根 `task_plan.md`/`progress.md`/`findings.md`。
2. `.planning/s3-ff-single-request-limits-20261003/` 与 `docs/implementation/s3-ff-limits-handoff.md`；对照 main 是否已包含 branch delivery commit。
3. transcript-companion branch 自身的 PWF、commit log、`git show --stat/name-status` 与测试报告；区分 prototype/WIP 是否实际完整交付。
4. CWP 计划卡在本仓的只读副本、FF v2 集成 handoff 与 ET/CWP consumer 测试收据（只读本仓内已有副本；不访问其他仓）。
5. `git worktree list --porcelain` 后对 `filing-fetch-s3-limits`、`filing-fetch-source-ref-v2-20261004`、`filing-fetch-transcript-companion`、review/detached trees 和所有可见路径逐个读取 status；记录临时 checkout 的来源，不能 prune。

## 只读核查

- 以 live `origin/main` 为比较线，重算所有本地/远端 refs 的左右差值，并分别记录 branch-only commit SHAs。
- 对 transcript companion 的唯一 WIP commit逐项描述变更行为、测试、handoff 缺口、和 main 现有能力的重合/差异；无需复制完整源码。
- 检查 staged/unstaged/untracked；密钥不进入 `git diff` 输出。其他疑似敏感配置也只报 path/status/size。
- 读现有测试报告/CI SHA；不得运行它们。

## 唯一交接

按 `../handoff_template.md` 写：

`C:\Users\郑曾波\Projects\company-wiki\docs\plans\repository-state-audit-2026-10-04\results\filing_fetch.md`

必须解释：FF-S3 是已并入 main 还是仍有独有提交；transcript-companion 的完整度/唯一价值；未跟踪 key 保留但本次不接触；所有 linked worktrees 是 active、historical 还是无法确认。
