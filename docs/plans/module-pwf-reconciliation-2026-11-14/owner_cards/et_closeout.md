# ET-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts`。

**PWF 读取入口与交付落点：**读取根 `task_plan.md`、`progress.md`、`findings.md`，并对照 `docs/plans/mb11-et-2026-11-11/`、`docs/plans/du10-txt-fidelity-2026-10-17/` 与 DU9 legacy-comparison 的最终收据。最终交接固定写入 `docs/plans/module-pwf-reconciliation-2026-11-14/review/et-closeout-handoff.md` 和 `et-closeout-handoff.json`；独立审查报告写 `et-closeout-review.md`（目录不存在时创建）。

## 目标与边界

整理 ET 根计划与已完成 MB-ET / TXT handoff 的关系，盘清其 Projects 额外目录和 worktree，然后写清 ET 提供端与 FF/CWP 消费端后续任务的 owner 分界。不得改 FF/CWP 代码或代其集成；不得翻译电话会原文。

## 独立执行与交接约定

- 开工先读本仓 `AGENTS.md`（若存在）、上方列出的 PWF 入口和此卡；再用实时 Git 状态重核 branch、HEAD/remote、tracked/untracked、registered worktree 与 refs。本卡中的日期/HEAD/count 是调查快照，不是授权或删除依据；新状态不同则先更新快照，基于实时确认的本仓目标主线继续，不回滚新工作，也不假设主线名一定是 `main`。
- 只在本卡唯一写入仓做文件和 Git 修改。看到其他仓路径/分支时只记录归属，不能在那里 checkout、stage、restore、commit、merge、push、删除或移动。若本仓有在途改动与本卡写集合重叠，标 `UNCLASSIFIED_HOLD` 并交当前 owner 协调，不覆盖。
- 删除/吸收决定逐项写依据；名字像临时目录、dirty/untracked、branch 非祖先都不能单独证明可删/该并。没查清 owner/PWF/内容/配置引用时保持 `UNCLASSIFIED_HOLD`。
- disposition 统一用 `ACTIVE_KEEP`（仍在用/有后续任务）、`EVIDENCE_KEEP`（唯一审查、运行或用户资料）、`ABSORBED`（已由目标主线等价吸收，附 commit 和等价证据）、`UNCLASSIFIED_HOLD`（归属/用途/内容未查清，原样保留）、`DELETE_AFTER_OWNER_CONFIRMATION`（本卡指定模块 owner 已依据收据确认结案，且无唯一内容、dirty 工作或配置引用；这是该 owner 的分类结论，不要求 ROOT 再签一次。若实际属于其他 owner，则保留并标 `UNCLASSIFIED_HOLD`）。
- 在上方指定的固定位置交 `handoff.md` 与 `handoff.json`，不要写到其他仓或覆盖历史 handoff。至少包含：仓库路径、canonical PWF、base/final branch+HEAD、remote HEAD（或明确无 remote）、每个 branch/worktree/Projects候选的 disposition 和依据、未提交例外、精确清理路径/文件数/字节、测试命令及结果、独立 reviewer 结论与绑定 HEAD、剩余项及唯一下一步。
- `handoff.json` 必须是可解析的裸 JSON（不带 Markdown 围栏），`schema_version` 固定为 `1`，顶层键固定为 `schema_version`、`lane`、`repo_root`、`canonical_pwf`、`base`、`final`、`dispositions`、`dirty_exceptions`、`cleanup`、`tests`、`independent_review`、`remaining_items`、`next_step`；`base/final` 含 `branch/head/remote_head`（无 remote 时 `remote_head: null`），`dispositions` 每项含 `kind/path/status/reason/evidence`，`cleanup` 含 `paths/file_count/bytes`，`tests` 每项含 `command/result`，`independent_review` 含 `reviewer_agent/reviewed_head/result/report_path`。独立 review Markdown 记录审查范围、绑定 HEAD、发现及关闭状态、最终 PASS/FAIL。
- 最终大节点由未参与实施的另一名 agent/harness 审查完整变更和交接，结论绑定已提交的候选最终 HEAD。若发现问题，作者修复、复测并提交新 HEAD，再由 reviewer 复核该 HEAD；通过后才推送并确认远端等于已审 HEAD，再交接。只设这一个审查节点，必要修复后的复核除外。代码变更跑本卡指定回归；文档-only按 JSON/link/`git diff --check`检查。

## 起始事实

- `main@915f216` = `origin/main`，tracked clean；`.workbuddy-ai/` 保留。
- 12 个注册 worktree，0 个本地 non-ancestor refs；Projects 下有 ET 容器及 7 个带任务名目录。
- 根 `task_plan.md/progress.md/findings.md` 是总体入口，但仍把 Phase 3 标 in-progress，引用 2026-09-26 旧 RF 活动卡和锁/dirty计数；`docs/plans/mb11-et-2026-11-11/` 于 11-13 已收尾。
- Projects下7个额外候选：`earnings-transcripts-du10-txt-fidelity`、`earnings-transcripts-du6-ff-readonly`、`earnings-transcripts-du7-extraction`、`earnings-transcripts-du7-integration`、`earnings-transcripts-du9-legacy-comparison`、`earnings-transcripts-s3-deadline`、`earnings-transcripts-s3-runtime`。另有 `earnings-transcripts` 容器，其 Git repo 位于 `earnings-transcripts/earnings-transcripts`。

## 执行步骤

1. 将根 `task_plan.md` 固定为 ET 唯一 canonical 状态入口，在顶部写当前状态摘要和唯一 Next Step；根 `progress.md`/`findings.md` 只作历史记录并链接回该入口，不另建 `START_HERE`。刷新 MB-ET、DU10 TXT fidelity 和最新主线收据的 HEAD。
2. 明确 ET 已完成的电话会发现/下载/原语言文本合同，与 FF 的调用、CWP 的统一存储和切片摘要各自责任。只写开放 wire/协议与依赖，不直接修改邻仓。
3. 对 12 worktree 和 7 个额外 Projects 目录逐项匹配 PWF、分支、dirty 状态、handoff 与 unique files；无非祖先 ref 不能被误写为“所有目录可删”。
4. ET owner 在本仓清理已结束且可重建目录；保留原始 TXT/JSON、测试收据和 `.workbuddy-ai/`。
5. 用根 PWF 列出 ET 自身真实后续主线工作；FF/CWP 待办作为 external-owner dependency 单独列出。

## 完成条件与审查

根计划不再把已完成的 MB-ET 写成待做，也不把 FF/CWP 待办冒记为 ET 未完成；12 worktree、7 额外目录有处置证据。代码未改时做 PWF/link/JSON/`git diff --check`；若确需 ET 代码改动，只跑受影响测试并在最终节点跑相关 ET suite。ET owner 先提交候选版本，再由独立 reviewer 对该 HEAD 和交接核对；若修复则更新提交并复核，通过后推送并确认远端 SHA 一致，再交 handoff。
