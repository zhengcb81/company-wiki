# Lane StockInfoDLSimple — provider 工作树只读盘点

## 目标与边界

唯一目标仓库根为 `C:\Users\郑曾波\Projects\StockInfoDLSimple`。审计默认 `v2-clean-rewrite` checkout、`cwp-cninfo-bounded-budget` linked worktree、所有该 Git common-dir 下的本地/远端 refs 和 worktrees。该仓是 CWP 选定的 A 股 provider。StockInfoDownloader 不属于本卡，也不要拿它作合并基线。

只读。严禁改源码/测试/config、恢复/删除文件、切换/更新/提交任何 branch/worktree 或改全局 git config。不要运行 downloader、真实 CNINFO 下载或测试；测试/CI 结果只读已有报告。

## 已知起点（每项需重查）

- `v2-clean-rewrite@1693045caeb5d72bfc83a4fa6d034802e80b0a3f` 与 live `origin/v2-clean-rewrite` 相同。
- `codex/cninfo-bounded-budget@8ed5fdd` 相对该基线有 2 个独有 commits；另有其 worktree `C:\Users\郑曾波\Projects\StockInfoDLSimple\cwp-cninfo-bounded-budget`。
- 默认 checkout 有多个 staged addition、staged+unstaged mixed changes、unstaged changes 和 untracked fixtures/source/test files（详见 `findings.md`）。务必分别记 index 与 worktree 两份 diff。
- CWP 本机 dirty `config/source_acquisition.yaml` 指向 `../StockInfoDLSimple/cwp-cninfo-bounded-budget` 的 `stockinfo-cninfo` 1.2.0 budget CLI。CWP PWF 记录过 62 个 provider tests、真实 BYD 10-K 端到端。这个跨仓证据只作线索；不要打开/改 CWP 仓库，报告中写“外部引用需总指挥核验”。
- 用户已明确选择 StockInfoDLSimple、排除 StockInfoDownloader 支线并入主线。

## 必读记录顺序

1. 本仓 `.planning/.active_plan`、根 `task_plan.md`/`progress.md`/`findings.md`（若不存在要写明），以及所有 `rg --files` 找到的 PWF/plan/handoff/CI 文件。
2. `git log --all --decorate` 与 bounded-budget 两个 commit 的 full stat/name-status；按 CWP integration 的 commit/测试收据核对计划声明。
3. 当前 checkout 中 `git diff --cached --stat`、`git diff --stat`、`git ls-files --others --exclude-standard`；再逐项查看非敏感的源代码/测试差异。
4. 明确文件的 staging 状态是否相互矛盾；找创建者/消费者、PWF 卡号、路径/接口是否被 CWP provider CLI 引用。类公司名单、fixture、运行日志和构建物分开分类。
5. 有其他 branch/worktree 时对每个逐项 `git status`；查其 tip 与默认线的左右计数、merge-base、`git cherry`/patch-id；区分已经并入的提交和 branch 上真正 unique commits。
6. 若要测尺寸只对已知 untracked 目录做文件数/字节汇总；不读出 source PDF/公告原文/密钥、不计算敏感内容 hash。
7. 只读取已经保存的 pytest/CI/E2E 报告；不要自己运行。

## 唯一交接

按 `../handoff_template.md` 写唯一结果：

`C:\Users\郑曾波\Projects\company-wiki\docs\plans\repository-state-audit-2026-10-04\results\stock_info_dl_simple.md`

结论要回答：哪些改动支撑当前 CWP adapter、哪些是其他下载器重构/资料、测试/fixtures 是否唯一证据、哪些 staged 与 unstaged 变化彼此对应、2 个 bounded commits 和 owner WIP 的关系、是否有内容已在 `v2-clean-rewrite` 或被 patch-equivalent 引入。只建议后续类别，不恢复/清理/合并。
