# Lane StockQA — StockQAbyLLM 本机输出与分支只读盘点

## 目标与边界

唯一目标仓：`C:\Users\郑曾波\Projects\StockQAbyLLM`。只审计本仓，不访问 IQS/StockWiki 原仓；跨项目 owner/phase 从本仓计划和产物元数据取证。

严禁对仓库/工作树/refs/index 写入或运行任何 runner、测试、LLM、provider、安装工具。`pilot_runs/`、`.workbuddy-ai/`、`eval_results.json` 等内容可能含真实研究/用户/模型文本，报告只给路径、计数、大小与哈希是否已有 manifest；**不要读取/复制/哈希原文或 API key**。

## 已知起点（重新确认）

- `master@5fdcc2c` 与 live `origin/master` 相同。
- `gh-pages@b559f49` 相对 master 有 2 个 branch-only commits；这是部署分支候选，不得默认当产品代码欠合。
- root 有 `.codegraph/`、`.workbuddy-ai/`、`nul`、`pilot_runs/b2a_2026-10-03/`、`pilot_runs/g2b_alphabet_2026-10-04/`、`progress_update.txt` 未跟踪。
- IQS Phase 68/69/70/71 PWF/进度提到这些运行产物，但报告仍要验证它们是否是唯一验收/交接证据、是否有明确保留规则。

## 必读记录与检查步骤

1. 当前活动 PWF selector、根 task_plan/progress/findings 与最近阶段记录；核对 Phase 68–71 引用路径和 SHA。
2. `git ls-remote --heads origin master gh-pages`（不 fetch）；判定 gh-pages 是 deploy/workflow 输入还是开发支线。看 `.github/workflows`、部署文档和 branch history，不合并。
3. 按目录记录 untracked/ignored status、文件计数/总字节/最晚最早时间、是否有 manifest/receipt/seed input 对照；只读文件名和 manifest schema，真实正文不打开。
4. 对 `eval_results.json`、`.workbuddy-ai`、`nul` 若存在，按文件类型/大小/状态/来源记录，不打印内容。`pilot_runs` 的被拒/被覆盖/草案/正式报告分别识别，不按“run”命名删除。
5. 检查其它本地 refs/worktrees、patch-equivalence、已存在 CI/test 报告的 SHA；不运行测试或脚本。

## 唯一交接

按 `../handoff_template.md` 写：

`C:\Users\郑曾波\Projects\company-wiki\docs\plans\repository-state-audit-2026-10-04\results\stock_qa_by_llm.md`

至少说明每个目录是代码、环境、草案、回执、LLM 运行输出或部署工件；哪些是唯一证据、能否按输入重建；gh-pages 单独归类；不出清理操作命令。
