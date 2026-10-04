# Lane IQS — invest-quick-scan 未提交状态只读盘点

## 目标与边界

唯一目标仓：`C:\Users\郑曾波\Projects\invest-quick-scan`。本卡只查分支/工作树/PWF/本机未提交文件，不能访问 StockWiki 或 StockQA 源仓（必要的交叉线索从 IQS 自己的 PWF/receipts 读取）。

只读：无 fetch/pull/分支切换/写配置/提交/删除/测试/API/LLM。未跟踪 `opencode.json` 可能含本机连接或 secret 配置，不读正文、不输出 hash；`nul` 只查元数据。

## 已知起点（重新确认）

- `master@a193821` 与 live `origin/master` 相同；未发现 branch-only development commits。
- untracked `nul`、`opencode.json`。
- PWF progress 已到 Phase 71，记录 B2a、G2b-A/C、真实 Alphabet 样本以及若干 owner pending；根 `task_plan.md` 是旧长期计划，不能代表 2026-10-04 活跃工作。

## 必读记录与检查步骤

1. 先检查本仓 `.planning/.active_plan`（若有）与当前执行计划入口；读取根/命名计划 `task_plan/progress/findings`、G2b handoff、最新 progress。
2. 把每个 PWF 最新提交 SHA 与当前 `git log --all`/live master 核对；识别 PWF 表中写“待 owner/审核/完成”的项目是否只对应未提交 artifacts。
3. 检查所有 branches/worktrees 对 main/master 的左右计数、merge-base、patch-equivalent；审计 `git status --porcelain=v2` 里未提交 paths。
4. 对 `nul` 与 `opencode.json` 仅查类型、大小、时间、是否 tracked/ignored、哪些工具/PWF 引用它们；绝不读取可能的 auth/endpoint value。
5. 不递归扫描公司原文/大数据；仅对状态行出现的特定目录做数量/总字节统计。不要把 owner 草案、拒绝/覆盖记录或唯一 golden 当成可清理输出。
6. 查现存 tests/CI/hash receipts，不运行测试/LLM。

## 唯一交接

按 `../handoff_template.md` 写：

`C:\Users\郑曾波\Projects\company-wiki\docs\plans\repository-state-audit-2026-10-04\results\invest_quick_scan.md`

报告至少回答：两个 untracked 项分别由什么工具/计划产生、是否曾被读取/提交策略明确排除、是否是可再生配置或用户设置；没有 branch-only 代码的证据；Phase 68–71 的唯一证据文件是否在 Git 中可恢复。
