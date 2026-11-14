# ET-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts`。

## 目标与边界

整理 ET 根计划与已完成 MB-ET / TXT handoff 的关系，盘清其 Projects 额外目录和 worktree，然后写清 ET 提供端与 FF/CWP 消费端后续任务的 owner 分界。不得改 FF/CWP 代码或代其集成；不得翻译电话会原文。

## 起始事实

- `main@915f216` = `origin/main`，tracked clean；`.workbuddy-ai/` 保留。
- 12 个注册 worktree，0 个本地 non-ancestor refs；Projects 下有 ET 容器及 7 个带任务名目录。
- 根 `task_plan.md/progress.md/findings.md` 是总体入口，但仍把 Phase 3 标 in-progress，引用 2026-09-26 旧 RF 活动卡和锁/dirty计数；`docs/plans/mb11-et-2026-11-11/` 于 11-13 已收尾。
- Projects下7个额外候选：`earnings-transcripts-du10-txt-fidelity`、`earnings-transcripts-du6-ff-readonly`、`earnings-transcripts-du7-extraction`、`earnings-transcripts-du7-integration`、`earnings-transcripts-du9-legacy-comparison`、`earnings-transcripts-s3-deadline`、`earnings-transcripts-s3-runtime`。另有 `earnings-transcripts` 容器，其 Git repo 位于 `earnings-transcripts/earnings-transcripts`。

## 执行步骤

1. ET owner 在根 PWF 设一个当前状态摘要和唯一 Next Step，保留旧进度作为历史；刷新 MB-ET、DU10 TXT fidelity 和最新主线收据的 HEAD。
2. 明确 ET 已完成的电话会发现/下载/原语言文本合同，与 FF 的调用、CWP 的统一存储和切片摘要各自责任。只写开放 wire/协议与依赖，不直接修改邻仓。
3. 对 12 worktree 和 7 个额外 Projects 目录逐项匹配 PWF、分支、dirty 状态、handoff 与 unique files；无非祖先 ref 不能被误写为“所有目录可删”。
4. ET owner 在本仓清理已结束且可重建目录；保留原始 TXT/JSON、测试收据和 `.workbuddy-ai/`。
5. 用根 PWF 列出 ET 自身真实后续主线工作；FF/CWP 待办作为 external-owner dependency 单独列出。

## 完成条件与审查

根计划不再把已完成的 MB-ET 写成待做，也不把 FF/CWP 待办冒记为 ET 未完成；12 worktree、7 额外目录有处置证据。代码未改时做 PWF/link/JSON/`git diff --check`；若确需 ET 代码改动，只跑受影响测试并在最终节点跑相关 ET suite。独立 reviewer 对最终 HEAD 和交接核对后由 ET owner 提交/推送，交 `handoff.md/json`。
