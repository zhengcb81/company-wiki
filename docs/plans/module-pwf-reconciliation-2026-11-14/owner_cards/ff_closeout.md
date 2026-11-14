# FF-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\filing-fetch`；由 FF owner 完成本仓计划、代码和 Git 操作。

**PWF 读取入口与交付落点：**读取根 `PLANNING_STATUS.md`、`task_plan.md`、`progress.md`、`findings.md`，并对照 `docs/plans/mb11-ff-2026-11-11/` 与 `docs/plans/du11-root-reception-2026-10-18/` 的最终收据。最终交接固定写入 `docs/plans/module-pwf-reconciliation-2026-11-14/review/ff-closeout-handoff.md` 和 `ff-closeout-handoff.json`；独立审查报告写 `ff-closeout-review.md`（目录不存在时创建）。

## 目标与边界

把 FF 的 canonical PWF、旧计划状态、支线/worktree 和 14 个 Projects 顶层候选目录对齐，再更新 FF 后续主线顺序。不得改 CWP/RF/ET 的文件或 Git；若发现跨仓问题只提交公开接口复现。

## 独立执行与交接约定

- 开工先读本仓 `AGENTS.md`（若存在）、上方列出的 PWF 入口和此卡；再用实时 Git 状态重核 branch、HEAD/remote、tracked/untracked、registered worktree 与 refs。本卡中的日期/HEAD/count 是调查快照，不是授权或删除依据；新状态不同则先更新快照，基于实时确认的本仓目标主线继续，不回滚新工作，也不假设主线名一定是 `main`。
- 只在本卡唯一写入仓做文件和 Git 修改。看到其他仓路径/分支时只记录归属，不能在那里 checkout、stage、restore、commit、merge、push、删除或移动。若本仓有在途改动与本卡写集合重叠，标 `UNCLASSIFIED_HOLD` 并交当前 owner 协调，不覆盖。
- 删除/吸收决定逐项写依据；名字像临时目录、dirty/untracked、branch 非祖先都不能单独证明可删/该并。没查清 owner/PWF/内容/配置引用时保持 `UNCLASSIFIED_HOLD`。
- disposition 统一用 `ACTIVE_KEEP`（仍在用/有后续任务）、`EVIDENCE_KEEP`（唯一审查、运行或用户资料）、`ABSORBED`（已由目标主线等价吸收，附 commit 和等价证据）、`UNCLASSIFIED_HOLD`（归属/用途/内容未查清，原样保留）、`DELETE_AFTER_OWNER_CONFIRMATION`（本卡指定模块 owner 已依据收据确认结案，且无唯一内容、dirty 工作或配置引用；这是该 owner 的分类结论，不要求 ROOT 再签一次。若实际属于其他 owner，则保留并标 `UNCLASSIFIED_HOLD`）。
- 在上方指定的固定位置交 `handoff.md` 与 `handoff.json`，不要写到其他仓或覆盖历史 handoff。至少包含：仓库路径、canonical PWF、base/final branch+HEAD、remote HEAD（或明确无 remote）、每个 branch/worktree/Projects候选的 disposition 和依据、未提交例外、精确清理路径/文件数/字节、测试命令及结果、独立 reviewer 结论与绑定 HEAD、剩余项及唯一下一步。
- `handoff.json` 必须是可解析的裸 JSON（不带 Markdown 围栏），`schema_version` 固定为 `1`，顶层键固定为 `schema_version`、`lane`、`repo_root`、`canonical_pwf`、`base`、`final`、`dispositions`、`dirty_exceptions`、`cleanup`、`tests`、`independent_review`、`remaining_items`、`next_step`；`base/final` 含 `branch/head/remote_head`（无 remote 时 `remote_head: null`），`dispositions` 每项含 `kind/path/status/reason/evidence`，`cleanup` 含 `paths/file_count/bytes`，`tests` 每项含 `command/result`，`independent_review` 含 `reviewer_agent/reviewed_head/result/report_path`。独立 review Markdown 记录审查范围、绑定 HEAD、发现及关闭状态、最终 PASS/FAIL。
- 最终大节点由未参与实施的另一名 agent/harness 审查完整变更和交接，结论绑定已提交的候选最终 HEAD。若发现问题，作者修复、复测并提交新 HEAD，再由 reviewer 复核该 HEAD；通过后才推送并确认远端等于已审 HEAD，再交接。只设这一个审查节点，必要修复后的复核除外。代码变更跑本卡指定回归；文档-only按 JSON/link/`git diff --check`检查。

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

最终 PWF 能从单一入口回答当前 HEAD、owner、已完成、未完成和下一步；3 refs、35 worktree、14 顶层目录逐项有处置，未跟踪敏感/运行状态按原样保留。代码改动时完成 FF 定向套件和一次相关完整 CI；纯文档时做 Markdown/JSON/link 与 `git diff --check` 检查。FF owner 先提交候选版本，再由独立 reviewer 对该 HEAD 与收据复核；修复项重新提交并复核，通过后推送并确认远端 SHA 一致，再交 handoff。
