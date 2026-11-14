# RF-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\revenue-forecast`；由 RF owner 完成本仓计划、代码和 Git 操作。

**PWF 读取入口与交付落点：**读取根 `PLANNING_STATUS.md`、`task_plan.md`、`progress.md`、`findings.md`，并对照 `docs/plans/mb11-rf-2026-11-11/`、`docs/plans/du11-root-reception-2026-10-18/` 与 W20 收据。最终交接固定写入 `docs/plans/module-pwf-reconciliation-2026-11-14/review/rf-closeout-handoff.md` 和 `rf-closeout-handoff.json`；独立审查报告写 `rf-closeout-review.md`（目录不存在时创建）。

## 目标与边界

统一 RF 的活动 PWF 入口、合并历史状态冲突、对账分支/worktree 和 Projects 顶层路径；完成后更新 RF 主线次序。不得改 CWP、Dashboard、StockWiki 或其他仓；不重跑公司预测来证明文档状态。

## 独立执行与交接约定

- 开工先读本仓 `AGENTS.md`（若存在）、上方列出的 PWF 入口和此卡；再用实时 Git 状态重核 branch、HEAD/remote、tracked/untracked、registered worktree 与 refs。本卡中的日期/HEAD/count 是调查快照，不是授权或删除依据；新状态不同则先更新快照，基于实时确认的本仓目标主线继续，不回滚新工作，也不假设主线名一定是 `main`。
- 只在本卡唯一写入仓做文件和 Git 修改。看到其他仓路径/分支时只记录归属，不能在那里 checkout、stage、restore、commit、merge、push、删除或移动。若本仓有在途改动与本卡写集合重叠，标 `UNCLASSIFIED_HOLD` 并交当前 owner 协调，不覆盖。
- 删除/吸收决定逐项写依据；名字像临时目录、dirty/untracked、branch 非祖先都不能单独证明可删/该并。没查清 owner/PWF/内容/配置引用时保持 `UNCLASSIFIED_HOLD`。
- disposition 统一用 `ACTIVE_KEEP`（仍在用/有后续任务）、`EVIDENCE_KEEP`（唯一审查、运行或用户资料）、`ABSORBED`（已由目标主线等价吸收，附 commit 和等价证据）、`UNCLASSIFIED_HOLD`（归属/用途/内容未查清，原样保留）、`DELETE_AFTER_OWNER_CONFIRMATION`（本卡指定模块 owner 已依据收据确认结案，且无唯一内容、dirty 工作或配置引用；这是该 owner 的分类结论，不要求 ROOT 再签一次。若实际属于其他 owner，则保留并标 `UNCLASSIFIED_HOLD`）。
- 在上方指定的固定位置交 `handoff.md` 与 `handoff.json`，不要写到其他仓或覆盖历史 handoff。至少包含：仓库路径、canonical PWF、base/final branch+HEAD、remote HEAD（或明确无 remote）、每个 branch/worktree/Projects候选的 disposition 和依据、未提交例外、精确清理路径/文件数/字节、测试命令及结果、独立 reviewer 结论与绑定 HEAD、剩余项及唯一下一步。
- `handoff.json` 必须是可解析的裸 JSON（不带 Markdown 围栏），`schema_version` 固定为 `1`，顶层键固定为 `schema_version`、`lane`、`repo_root`、`canonical_pwf`、`base`、`final`、`dispositions`、`dirty_exceptions`、`cleanup`、`tests`、`independent_review`、`remaining_items`、`next_step`；`base/final` 含 `branch/head/remote_head`（无 remote 时 `remote_head: null`），`dispositions` 每项含 `kind/path/status/reason/evidence`，`cleanup` 含 `paths/file_count/bytes`，`tests` 每项含 `command/result`，`independent_review` 含 `reviewer_agent/reviewed_head/result/report_path`。独立 review Markdown 记录审查范围、绑定 HEAD、发现及关闭状态、最终 PASS/FAIL。
- 最终大节点由未参与实施的另一名 agent/harness 审查完整变更和交接，结论绑定已提交的候选最终 HEAD。若发现问题，作者修复、复测并提交新 HEAD，再由 reviewer 复核该 HEAD；通过后才推送并确认远端等于已审 HEAD，再交接。只设这一个审查节点，必要修复后的复核除外。代码变更跑本卡指定回归；文档-only按 JSON/link/`git diff --check`检查。

## 起始事实

- `main@ec5ba0044b3252d2fc58c4a50c2fe9bc234cf5ad` = `origin/main`；ROOT 已提权读到 tracked clean。先重新核一次真实状态。
- 61 个注册 worktree、19 个本地非祖先 refs。`dashboard-rf-*` 分支虽然名字含 Dashboard，仍由 RF owner 在 RF 仓内处理；涉及 Dashboard 合同的差异交给双方协调，不跨仓改 Dashboard。
- MB-RF `task_plan.md` 与 `handoff.md` 同时写“未合入/已合入”；W20状态待对照实际收据。先前所报 `revenue_report.py`、`test_output_report.py`、`input-schema.md` dirty 已被 `ec5ba004` 吸收，不得重复报告为未提交。
- Projects的14个 RF core 候选目录：`revenue-forecast`、`revenue-forecast-dashboard-owner-release-20261109`、`revenue-forecast-du11-citation-closure`、`revenue-forecast-du5-units`、`revenue-forecast-du6-targets`、`revenue-forecast-du67-integration`、`revenue-forecast-du8-comparison`、`revenue-forecast-r1-boundary`、`revenue-forecast-r1-local-observation`、`revenue-forecast-r1-research`、`revenue-forecast-r1-targets`、`revenue-forecast-w14-clean-chain`、`revenue-forecast-w16-basis`、`revenue-forecast-w20-adoption`。9个 `revenue-forecast-audit*` 路径属于独立 RFAudit，不归本卡清理。

## 执行步骤

1. 将根 `PLANNING_STATUS.md` 固定为 RF 唯一 canonical 状态入口，在文件顶部更新当前 `main@HEAD`、活动计划、关闭收据、依赖和唯一下一步；根 `task_plan.md`、`progress.md`、`findings.md` 及 MB-RF/W20 只作为历史或子计划，并链接回该入口，不另建 `START_HERE`。冲突按提交和 handoff 绑定的 ref 对齐。
2. 对 19 refs、61 worktree 和 RF 专属顶层目录建逐项账目：归属、branch/HEAD、dirty/untracked、提交差异、PWF/handoff、配置或测试引用、最终分类。
3. 按当前 RF 公开模块接口，owner 本仓适配可用分支；不按 `not merged` 机械合并，不覆盖当前 main、不重新跑预测、不把历史执行输出当代码。代码并线由 RF owner 完成。
4. 只删除经确认结案且无唯一源代码、测试证据、用户资料、运行状态或配置引用的 RF-owned 工区；逐路径记录空间收据。RFAudit 目录全部留给其独立 owner。
5. 更新 RF 未来主线计划，把本仓未完成的模型/报告/来源职责按依赖排序；依赖其他 owner 的事项写成公开接口等待项，不由 RF 跨界修复。

## 完成条件与审查

MB-RF 与 W20 状态无冲突；19 refs、61 worktree、RF core 顶层路径全部有 owner 处置；保留/清理证据可追踪；当前 main/remote HEAD明确。若改代码，运行受影响回归和一次相关 RF 大套件；纯文档改动做 PWF/JSON/link/`git diff --check`。RF owner 先提交候选版本，再由独立 reviewer 绑定该 HEAD；修复项重新测试、提交并复核，通过后推送并确认远端 SHA 一致，再交 handoff。
