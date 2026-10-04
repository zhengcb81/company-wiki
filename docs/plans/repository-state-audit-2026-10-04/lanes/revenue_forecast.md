# Lane RF — Revenue Forecast 分支/工作树只读盘点

## 目标与边界

目标仓库唯一为 `C:\Users\郑曾波\Projects\revenue-forecast`。只读盘点 `fcap`、本地原型分支、RF 的 active PWF/执行记录和 fcap 根工作树的两项 tracked 修改。不要读取或修改 company-wiki、filing-fetch 或 StockWiki；发现跨仓引用时只记录路径/提交号。

禁止一切写操作：不 fetch/pull/switch/checkout/restore/reset/stash/clean/merge/rebase/cherry-pick/commit/push；不改 RF 的 `.git`、active-plan pointer、配置、运行记录或测试产物。不运行 RF 测试/构建/预测/LLM。

## 已知起点（审计时必须重新确认）

- checkout `fcap@5319ee263c4af41ac255938c25bebd32cce56f66`，live `origin/fcap` 同 SHA；live `origin/main@6fb2def709d13bda9cfada7ecf62bfc0e3744ae2`。
- `fcap` 相对 `origin/main` 初查为 4 branch-only / 14 base-only commits，4 个独有提交标题为 DWA-04R A–D；DWA-04R-D 的标题称记录 360 paths / 8 execution-run carriers。
- `codex/revenue-source-reader` 有 1 个本地独有原型提交，相对 origin/main 落后 13。
- 根 fcap 有两项 tracked 修改：`assurance/runs/weekly_alert.jsonl`、`assurance/runs/weekly_manifest.json`。不要先假定它们是可丢弃运行日志。
- RF `audit_review/README.md`、`assurance/unified_completion/state.json` 曾记 `plan_status=completed`、`current_next=CA-201`、控制更新时间 2026-08-31；比 fcap DWA-04R 提交早。需厘清这是不是新阶段、历史镜像或相互矛盾的状态。

## 必读记录顺序

1. RF 仓库当前 active plan 指针、`audit_review/README.md`、`assurance/unified_completion/state.json` 与 `assurance/unified_completion/manifests/plan_inputs.json`（只读）。
2. 根 `task_plan.md`/`progress.md`/`findings.md`，但按其自身说明把根计划视为历史材料，不越过唯一入口。
3. `.planning/2026-09-19-three-project-history-audit/` 中 current implementation/execution/handoff 索引，以及 DWA-04R 对应的最小文件集合；用 `rg -l` 先定位 carrier，不要把整个 execution_runs 倒进上下文。
4. `git log` 中四个 DWA-04R SHA 的 `--name-status`、commit message、作者时间；核对 360 path claim 是 commit file count、artifact registry 还是其他统计。
5. `codex/revenue-source-reader` 的 WIP 源码/计划/receipt，确认与 fcap 是否重复、被替代或仍有独立用途。

## 只读核查步骤

1. 复查 `git status --porcelain=v2 --branch --untracked-files=all`、`git worktree list --porcelain`；对每个 linked/detached/review worktree 单独读取 status，计数不要只看根 checkout。
2. 以 live `origin/main` 和 `origin/fcap` 为基线，重算所有本地、remote-tracking branch 的左右提交计数。可用 `git ls-remote --heads origin main fcap` 校验服务端 SHA；**不要 fetch**。
3. 对每个 branch-only SHA 附 `git show --stat --oneline`、`git show --name-status`、有限文件级 diff；用 `git cherry -v` / patch-id 检查是否已经 cherry-picked/squashed。
4. 将 DWA-04R A–D 每个实现/规划/执行产物映射到 PWF：作者和生成者、完成结论、引用 SHA/hash、唯一证据与是否在主线 tree 中存在。不得把“不在主线”直接推成“应丢弃”。
5. 对两个 modified JSON 只查 `git diff --numstat`、文件大小/时间和被哪些 PWF/工具引用。可读非敏感字段以判断内容用途，但先确认不含访问凭据或私人内容；如不确定只报 metadata。不要格式化/重写。
6. 汇总 PWF completion claims 与 Git refs：完成但未合、已合但待提交、证据只在工作树、branch 已被 main 包含分别列出。
7. 只查看现有测试/CI receipts 与其 SHA 绑定；不运行测试。交接中给每个事项附 `merge_candidate` / `unique_evidence_preserve` 等类别，但不实施。

## 唯一交接

按 `../handoff_template.md` 输出完整报告到：

`C:\Users\郑曾波\Projects\company-wiki\docs\plans\repository-state-audit-2026-10-04\results\revenue_forecast.md`

报告必须回答：RF 4 个 DWA-04R commit 的具体路径/用途；360 paths 的精确定义；两项 dirty JSON 是否唯一证据或可再生；旧 `completed/CA-201` 和 fcap 实际状态是否冲突；`revenue-source-reader` 是否仍有主线外独特功能；所有分支/工作树的处置类别和证据。
