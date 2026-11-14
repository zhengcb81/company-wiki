# CWP-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\company-wiki`。这是 ROOT 本仓责任。

**PWF 读取入口与交付落点：**先读本计划 `task_plan.md`、`progress.md`、`findings.md`，再核对业务主线 `docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md` 与同名 `.json`。最终交接固定写入本计划 `review/cwp-closeout-handoff.md` 与 `review/cwp-closeout-handoff.json`；独立审查报告写 `review/cwp-closeout-review.md`。

## 目标

收敛 company-wiki 自己的 PWF 状态、未提交/未并线 refs 和多余 Projects 工区；保留模块边界。完成后明确 CWP 当前唯一下一步并链回父计划。不得操作 StockWiki、Dashboard、FF、RF、ET、SID 或 IQS 仓库。

## 独立执行与交接约定

- 开工先读本仓 `AGENTS.md`（若存在）、上方列出的 PWF 入口和此卡；再用实时 Git 状态重核 branch、HEAD/remote、tracked/untracked、registered worktree 与 refs。本卡中的日期/HEAD/count 是调查快照，不是授权或删除依据；新状态不同则先更新快照，基于实时确认的本仓目标主线继续，不回滚新工作，也不假设主线名一定是 `main`。
- 只在本卡唯一写入仓做文件和 Git 修改。看到其他仓路径/分支时只记录归属，不能在那里 checkout、stage、restore、commit、merge、push、删除或移动。若本仓有在途改动与本卡写集合重叠，标 `UNCLASSIFIED_HOLD` 并交当前 owner 协调，不覆盖。
- 删除/吸收决定逐项写依据；名字像临时目录、dirty/untracked、branch 非祖先都不能单独证明可删/该并。没查清 owner/PWF/内容/配置引用时保持 `UNCLASSIFIED_HOLD`。
- disposition 统一用 `ACTIVE_KEEP`（仍在用/有后续任务）、`EVIDENCE_KEEP`（唯一审查、运行或用户资料）、`ABSORBED`（已由目标主线等价吸收，附 commit 和等价证据）、`UNCLASSIFIED_HOLD`（归属/用途/内容未查清，原样保留）、`DELETE_AFTER_OWNER_CONFIRMATION`（本卡指定模块 owner 已依据收据确认结案，且无唯一内容、dirty 工作或配置引用；这是该 owner 的分类结论，不要求 ROOT 再签一次。若实际属于其他 owner，则保留并标 `UNCLASSIFIED_HOLD`）。
- 在上方指定的固定位置交 `handoff.md` 与 `handoff.json`，不要写到其他仓或覆盖历史 handoff。至少包含：仓库路径、canonical PWF、base/final branch+HEAD、remote HEAD（或明确无 remote）、每个 branch/worktree/Projects候选的 disposition 和依据、未提交例外、精确清理路径/文件数/字节、测试命令及结果、独立 reviewer 结论与绑定 HEAD、剩余项及唯一下一步。
- `handoff.json` 必须是可解析的裸 JSON（不带 Markdown 围栏），`schema_version` 固定为 `1`，顶层键固定为 `schema_version`、`lane`、`repo_root`、`canonical_pwf`、`base`、`final`、`dispositions`、`dirty_exceptions`、`cleanup`、`tests`、`independent_review`、`remaining_items`、`next_step`；`base/final` 含 `branch/head/remote_head`（无 remote 时 `remote_head: null`），`dispositions` 每项含 `kind/path/status/reason/evidence`，`cleanup` 含 `paths/file_count/bytes`，`tests` 每项含 `command/result`，`independent_review` 含 `reviewer_agent/reviewed_head/result/report_path`。独立 review Markdown 记录审查范围、绑定 HEAD、发现及关闭状态、最终 PASS/FAIL。
- 最终大节点由未参与实施的另一名 agent/harness 审查完整变更和交接，结论绑定已提交的候选最终 HEAD。若发现问题，作者修复、复测并提交新 HEAD，再由 reviewer 复核该 HEAD；通过后才推送并确认远端等于已审 HEAD，再交接。只设这一个审查节点，必要修复后的复核除外。代码变更跑本卡指定回归；文档-only按 JSON/link/`git diff --check`检查。

## 起始事实

- `master@1f9f3dcf3`，远端已对齐；本仓 tracked 工作区干净。
- 已观测 8 个注册 worktree、13 个 `master` 非祖先 refs。
- Projects 顶层候选目录：`company-wiki`、`company-wiki-et-live-20261004`、`company-wiki-gates`、`company-wiki-r1-local-observation`、`company-wiki-storage-audit-20261003`。
- 当前唯一总控清理计划为 `docs/plans/module-pwf-reconciliation-2026-11-14/`；业务主线入口为 `docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md/json`，native goal 仍 paused。

## 独占范围

只写 CWP 仓自己的 `docs/plans/`、本仓源码/测试（确需适配 CWP 自身支线时）及本仓精确列出的工区。保留 `.ff_jobs`、`.mimosa`、`.workbuddy-ai`、API keys、原件、用户数据和历史 PWF 证据。不得用 `git clean -fdx`、整仓 reset、目录通配删除；不得重建或覆盖其他模块的内部实现。

## 步骤与验收

1. 对 13 个非祖先 refs、8 个 worktree 与四个额外 Projects 目录逐项关联 PWF、handoff、owner、HEAD、dirty paths、与 `master` 的独有路径/补丁；已在 CWP `master` 等价吸收的只记 `ABSORBED`。
2. `d00-return5` 与 `b34-prospectus` 的 dirty/owner 状态尚未完整归因，先标 `UNCLASSIFIED_HOLD`，不推断为活动或可删。两者物理目录位于 `Projects/investment-dashboard/.worktrees/`，本卡禁止删除、移动、checkout 或清理这两个物理目录；CWP owner 只记录其 CWP Git branch、HEAD 和 dirty 摘要，后续由 Dashboard owner 协调目录处置，或双方 owner 正式交接后再处理。CWP 仓内以 CWP 代码路径为准。
3. 仅在确认 owner 已完成、最终源码在 CWP 主线、无唯一证据且工区 clean 后，逐路径移除物理位于 CWP 所有目录内的 CWP 工区/目录。保留 `.planning` 历史、独有审查和原始材料，除非确认纯可重建产物并列出收据。
4. 更新当前总控 PWF：列明 CWP 自己已完成和未完成内容，并明确真正下一项 CWP 主线工作；父计划公司循环保持 paused，不提前执行。
5. 若本仓代码改变，运行关联单测和本仓边界 suite；若仅 PWF 更新，跑 `git diff --check`、校验新增/修改 JSON 和相对链接即可。
6. 完成检查后先提交候选最终版本；再由独立 reviewer 按该 HEAD 检查 13 refs、8 worktrees 与 5 顶层路径均有状态、清理路径无未解释 WIP、模块 owner 边界未破坏。若需修复，修复后重新提交并复核新 HEAD；通过后推送当前目标主线并确认远端 SHA 等于审查 SHA。

## 交接

交付 `docs/plans/module-pwf-reconciliation-2026-11-14/review/cwp-closeout-handoff.md/json`，包含每个 ref/worktree/目录的唯一处置、diff/dirty 摘要、测试、独审 SHA、释放的文件数/字节、最终本地/远端 SHA、CWP 下一步及尚待其他模块 owner 的公开接口依赖。
