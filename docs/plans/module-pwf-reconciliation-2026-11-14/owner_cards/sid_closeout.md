# SID-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\StockInfoDLSimple\v2-clean-rewrite`。

**PWF 读取入口与交付落点：**读取 `docs/plans/mb11-sid-2026-11-11/task_plan.md` 与同目录 handoff/review，另读 `.planning/g5-sid-runtime/task_plan.md`、handoff 和依赖图以确认 G4 后的路由状态。最终交接固定写入 `docs/plans/module-pwf-reconciliation-2026-11-14/review/sid-closeout-handoff.md` 和 `sid-closeout-handoff.json`；独立审查报告写 `sid-closeout-review.md`（目录不存在时创建）。

## 目标与边界

对齐 SID 的 MB11 与 G4 PWF 状态、清点本仓 worktree/备份并保留用户名单；完成后明确 SID 本仓后续主线。只写 SID 仓，不改 CWP/FF 的 provider adapter。

## 独立执行与交接约定

- 开工先读本仓 `AGENTS.md`（若存在）、上方列出的 PWF 入口和此卡；再用实时 Git 状态重核 branch、HEAD/remote、tracked/untracked、registered worktree 与 refs。本卡中的日期/HEAD/count 是调查快照，不是授权或删除依据；新状态不同则先更新快照，基于实时确认的本仓目标主线继续，不回滚新工作，也不假设主线名一定是 `main`。
- 只在本卡唯一写入仓做文件和 Git 修改。看到其他仓路径/分支时只记录归属，不能在那里 checkout、stage、restore、commit、merge、push、删除或移动。若本仓有在途改动与本卡写集合重叠，标 `UNCLASSIFIED_HOLD` 并交当前 owner 协调，不覆盖。
- 删除/吸收决定逐项写依据；名字像临时目录、dirty/untracked、branch 非祖先都不能单独证明可删/该并。没查清 owner/PWF/内容/配置引用时保持 `UNCLASSIFIED_HOLD`。
- disposition 统一用 `ACTIVE_KEEP`（仍在用/有后续任务）、`EVIDENCE_KEEP`（唯一审查、运行或用户资料）、`ABSORBED`（已由目标主线等价吸收，附 commit 和等价证据）、`UNCLASSIFIED_HOLD`（归属/用途/内容未查清，原样保留）、`DELETE_AFTER_OWNER_CONFIRMATION`（本卡指定模块 owner 已依据收据确认结案，且无唯一内容、dirty 工作或配置引用；这是该 owner 的分类结论，不要求 ROOT 再签一次。若实际属于其他 owner，则保留并标 `UNCLASSIFIED_HOLD`）。
- 在上方指定的固定位置交 `handoff.md` 与 `handoff.json`，不要写到其他仓或覆盖历史 handoff。至少包含：仓库路径、canonical PWF、base/final branch+HEAD、remote HEAD（或明确无 remote）、每个 branch/worktree/Projects候选的 disposition 和依据、未提交例外、精确清理路径/文件数/字节、测试命令及结果、独立 reviewer 结论与绑定 HEAD、剩余项及唯一下一步。
- `handoff.json` 必须是可解析的裸 JSON（不带 Markdown 围栏），`schema_version` 固定为 `1`，顶层键固定为 `schema_version`、`lane`、`repo_root`、`canonical_pwf`、`base`、`final`、`dispositions`、`dirty_exceptions`、`cleanup`、`tests`、`independent_review`、`remaining_items`、`next_step`；`base/final` 含 `branch/head/remote_head`（无 remote 时 `remote_head: null`），`dispositions` 每项含 `kind/path/status/reason/evidence`，`cleanup` 含 `paths/file_count/bytes`，`tests` 每项含 `command/result`，`independent_review` 含 `reviewer_agent/reviewed_head/result/report_path`。独立 review Markdown 记录审查范围、绑定 HEAD、发现及关闭状态、最终 PASS/FAIL。
- 最终大节点由未参与实施的另一名 agent/harness 审查完整变更和交接，结论绑定已提交的候选最终 HEAD。若发现问题，作者修复、复测并提交新 HEAD，再由 reviewer 复核该 HEAD；通过后才推送并确认远端等于已审 HEAD，再交接。只设这一个审查节点，必要修复后的复核除外。代码变更跑本卡指定回归；文档-only按 JSON/link/`git diff --check`检查。

## 起始事实

- `v2-clean-rewrite@d084c4a` = `origin/v2-clean-rewrite`；tracked clean；未跟踪 `a_share_companies.txt`、`companies.txt` 是用户名单，必须保留。
- 3 个注册 worktree、0 个 non-ancestor refs。Projects顶层仅一个 `StockInfoDLSimple` 容器，内含 `cwp-cninfo-bounded-budget` 注册工区与 `lineage-cleanup-backup-20261004` 备份目录。
- MB11 SID 卡已收尾；G4 latest 也标完成，但仍遗留“主线待做 1.3.0 路由升级”，需核对当前 HEAD 后决定完成或开放。

## 执行步骤

1. 将 `docs/plans/mb11-sid-2026-11-11/task_plan.md` 固定为 SID 唯一 canonical 状态入口，在顶部更新最新目标分支 HEAD、G4状态和唯一下一步；同目录 `progress.md`/`findings.md`/handoff 与 `.planning/g5-sid-runtime/` 只作历史证据或子计划并链接回该入口，不另建第二个 START_HERE。
2. 按当前源码与G4 handoff核对1.3.0路由是否已进入主线；已完成则追加收据并把旧待办标成 superseded，未完成则保留为明确任务。
3. 对3个worktree、bounded-budget工区和backup逐项查看关联PWF/branch/dirty/内容；用户名单、真实返回数据和唯一测试证据保留。
4. 只由 SID owner 删除已结案、clean、可重建的本仓工区；为每条 Projects 目录记录 keep/delete 与字节收据。
5. 更新 SID 下个主线任务和与 CWP/FF 的公开 wire 依赖；跨仓差异只开 owner handoff，不直接修改邻仓。

## 完成条件与审查

最新ref、G4下一步、MB11完成状态一致；3工区和额外目录都有归属；用户名单仍在；最多一个长期主仓目录。代码改动跑SID定向suite和最终相关整套回归；纯文档用JSON/link/`git diff --check`检查。SID owner 先提交候选版本，再由独立 reviewer 按该 HEAD 核对；修复项更新提交并复核，通过后推送并确认远端 SHA 一致，再交 handoff。
