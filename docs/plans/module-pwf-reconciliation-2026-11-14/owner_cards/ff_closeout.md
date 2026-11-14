# FF-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\filing-fetch`；由 FF owner 完成本仓计划、代码和 Git 操作。

## 目标与边界

把 FF 的 canonical PWF、旧计划状态、支线/worktree 和 14 个 Projects 顶层候选目录对齐，再更新 FF 后续主线顺序。不得改 CWP/RF/ET 的文件或 Git；若发现跨仓问题只提交公开接口复现。

## 起始事实

- 快照 `main@d4f35ca` = `origin/main`，tracked clean。
- 35 个注册 worktree；3 个待归因候选 ref：`codex/dashboard-ff-b34-candidate@9be5587`、`codex/ff-job-facade-01@154c292`、`codex/transcript-companion@29085f7`。
- PWF冲突：根 `PLANNING_STATUS.md` 仍指 10-04 的 `fcap@eb0af13`；根 task/progress/findings 是 8 月旧档；MB-FF handoff 未记当前 `d4f35ca`；W20仍 READY 但有完成收据；DU10 `NEXT_HANDOFF.md` 的待办与最终接收收据冲突。
- Projects候选：`filing-fetch`、`filing-fetch-du10-41-matrix`、`filing-fetch-du11-local-transcript-reuse`、`filing-fetch-du6-portable`、`filing-fetch-du67-integration`、`filing-fetch-du8-integration`、`filing-fetch-du8-matrix`、`filing-fetch-r1-boundary`、`filing-fetch-r1-local-observation`、`filing-fetch-s3-limits`、`filing-fetch-source-ref-v2-20261004`、`filing-fetch-transcript-companion`、`filing-fetch-w19-sina-statements`、`filing-fetch-w20-replay`。
- `.ff_jobs/`、`.mimosa/`、`.workbuddy-ai/`、`config/FMP_API_KEY.txt` 保留；不读密钥。

## 执行步骤

1. 由 FF owner 明确一个当前 PWF landing（现有 `PLANNING_STATUS.md` 可保留作索引），刷新当前 HEAD/remote、唯一活动计划、已完成计划、阻塞与下一步；根 8 月文件标成历史并链接到此入口。
2. 把 MB-FF、W20、DU10 的冲突逐条对照最终 Git commit、handoff 和测试收据，标记 superseded/completed/in-progress；不复制旧计划，也不删历史证据。
3. 对 3 个候选 refs 与全部 35 worktree 逐项记录 branch、HEAD、dirty/untracked、PWF、独有路径和补丁等价。旧 transcript prototype 必须与当前 v2/DU11 处理比较后才决定适配/保留/清理；不能盲目 cherry-pick 整支。
4. FF owner 只在 FF 内决定哪些源码/测试要适配当前公开 API，运行受影响回归；可接收代码由 FF owner 自己合入 `main` 并推送。其余工区/直接目录仅在 clean、任务结束、有可追溯收据后清理。
5. 在唯一入口列出下一步 FF 主线任务、依赖和完成条件；不在本卡改 CWP/ET 实现。

## 完成条件与审查

最终 PWF 能从单一入口回答当前 HEAD、owner、已完成、未完成和下一步；3 refs、35 worktree、14 顶层目录逐项有处置，未跟踪敏感/运行状态按原样保留。代码改动时完成 FF 定向套件和一次相关完整 CI；纯文档时做 Markdown/JSON/link 与 `git diff --check` 检查。交给独立 reviewer 对最终 HEAD 与收据复核；问题修好再由 FF owner 提交、推送，并交 `handoff.md/json`。
