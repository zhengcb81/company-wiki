# DASHBOARD-D00-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\investment-dashboard`；产品和 Git 收尾均由 Dashboard D00 owner 执行。

**PWF 读取入口与交付落点：**读取 `.planning/unified-dashboard-2026-10-26/START_HERE.md`、`DELIVERY_STATUS.md`、`COMPLETION_PLAN.md`、`OWNERSHIP.md`、`INTERFACES.md`、`TESTING.md` 与 `status.json`。最终交接固定写入 `.planning/unified-dashboard-2026-10-26/handoffs/module-pwf-reconciliation-2026-11-14/dashboard-closeout-handoff.md` 和 `dashboard-closeout-handoff.json`；独立审查报告写 `dashboard-closeout-review.md`（该子目录不存在时创建）。

## 目标与边界

对齐 Dashboard D00 总状态、各模块 PWF、CWP 后续卡基线、未并线支线和 Projects 工区；写清 Dashboard 仍未完成的产品路线。不得改 CWP/FF/RF/StockWiki/IQS 代码；不得将旧集中式实现合并回 modular main。

## 独立执行与交接约定

- 开工先读本仓 `AGENTS.md`（若存在）、上方列出的 PWF 入口和此卡；再用实时 Git 状态重核 branch、HEAD/remote、tracked/untracked、registered worktree 与 refs。本卡中的日期/HEAD/count 是调查快照，不是授权或删除依据；新状态不同则先更新快照，基于实时确认的本仓目标主线继续，不回滚新工作，也不假设主线名一定是 `main`。
- 只在本卡唯一写入仓做文件和 Git 修改。看到其他仓路径/分支时只记录归属，不能在那里 checkout、stage、restore、commit、merge、push、删除或移动。若本仓有在途改动与本卡写集合重叠，标 `UNCLASSIFIED_HOLD` 并交当前 owner 协调，不覆盖。
- 删除/吸收决定逐项写依据；名字像临时目录、dirty/untracked、branch 非祖先都不能单独证明可删/该并。没查清 owner/PWF/内容/配置引用时保持 `UNCLASSIFIED_HOLD`。
- disposition 统一用 `ACTIVE_KEEP`（仍在用/有后续任务）、`EVIDENCE_KEEP`（唯一审查、运行或用户资料）、`ABSORBED`（已由目标主线等价吸收，附 commit 和等价证据）、`UNCLASSIFIED_HOLD`（归属/用途/内容未查清，原样保留）、`DELETE_AFTER_OWNER_CONFIRMATION`（本卡指定模块 owner 已依据收据确认结案，且无唯一内容、dirty 工作或配置引用；这是该 owner 的分类结论，不要求 ROOT 再签一次。若实际属于其他 owner，则保留并标 `UNCLASSIFIED_HOLD`）。
- 在上方指定的固定位置交 `handoff.md` 与 `handoff.json`，不要写到其他仓或覆盖历史 handoff。至少包含：仓库路径、canonical PWF、base/final branch+HEAD、remote HEAD（或明确无 remote）、每个 branch/worktree/Projects候选的 disposition 和依据、未提交例外、精确清理路径/文件数/字节、测试命令及结果、独立 reviewer 结论与绑定 HEAD、剩余项及唯一下一步。
- `handoff.json` 必须是可解析的裸 JSON（不带 Markdown 围栏），`schema_version` 固定为 `1`，顶层键固定为 `schema_version`、`lane`、`repo_root`、`canonical_pwf`、`base`、`final`、`dispositions`、`dirty_exceptions`、`cleanup`、`tests`、`independent_review`、`remaining_items`、`next_step`；`base/final` 含 `branch/head/remote_head`（无 remote 时 `remote_head: null`），`dispositions` 每项含 `kind/path/status/reason/evidence`，`cleanup` 含 `paths/file_count/bytes`，`tests` 每项含 `command/result`，`independent_review` 含 `reviewer_agent/reviewed_head/result/report_path`。独立 review Markdown 记录审查范围、绑定 HEAD、发现及关闭状态、最终 PASS/FAIL。
- 最终大节点由未参与实施的另一名 agent/harness 审查完整变更和交接，结论绑定已提交的候选最终 HEAD。若发现问题，作者修复、复测并提交新 HEAD，再由 reviewer 复核该 HEAD；通过后才推送并确认远端等于已审 HEAD，再交接。只设这一个审查节点，必要修复后的复核除外。代码变更跑本卡指定回归；文档-only按 JSON/link/`git diff --check`检查。

## 起始事实

- 主线 `main@50602dee7c6fbecaa744004a4184bdc6bc7b2765` = `origin/main`；tracked clean，`.workbuddy-ai/` 保留。
- D00 canonical入口为 `.planning/unified-dashboard-2026-10-26/START_HERE.md`；当前有 80 个注册 worktree、92 个 local branch refs。
- `START_HERE.md`、`DELIVERY_STATUS.md`、`COMPLETION_PLAN.md` 的状态快照为 11-04；CWP 三张 Dashboard 卡基线还写 `ff6e764f`，需先对齐 `50602dee` 并核实际代码状态。
- Dashboard仍 `PARTIALLY_IMPLEMENTED_NOT_COMPLETE`；真实 owner chain、E08、指标/三表映射、job executor、性能和用户验收仍有缺口；E14 为暂停项。
- Projects顶层目录候选：`investment-dashboard`、`investment-dashboard-e15`、`investment-dashboard-owner-adapters-20261109`；另有注册工区可能位于 `.worktrees`、`.codex/worktrees` 或其他 Projects 路径。

## 执行步骤

1. D00更新唯一主状态入口的 as-of、HEAD、完成/未完成、暂停项和下一步；模块 M0–M9 子PWF各自仍是子计划，不复制一份第二总状态。
2. 逐张核 CWP C01、B-real、B03 卡在当前 main 的实际状态、测试/独审与依赖；刷新基线和剩余工作，保留其 owner-only 写域。此前三份文档交接提交只作为历史，不据此认定卡已完成。
3. 对 92 refs、80 worktree 和其他两个 Projects候选逐项建立 disposition：branch/HEAD、独有提交/路径、dirty文件、PWF/handoff、运行配置引用、归属和保留/删除理由。不能因名字像旧任务就删除；dirty worktree先交当前 owner。
4. 由 Dashboard owner 在其 repo 内适配可用分支、跑模块回归并逐个 merge/push；任何 CWP/FF/RF接口变化各自给对应 owner 开明示 handoff，不跨仓实现。
5. 只删除已经验明无活动WIP、无唯一产物且已进入main/有完整收据的Dashboard工区；保留 `.workbuddy-ai/` 与所有用户/研究/业务数据。
6. 更新 Dashboard 剩余主线路线和最终用户验收点，使其可以独立交给后续 harness。

## 完成条件与审查

D00可从START_HERE定位唯一现状、每个模块子计划和下一步；旧11-04描述已标历史或更新；3张CWP卡基线对齐；92 refs、80 worktree、所有 Projects候选均有处理状态。代码改动运行相关Dashboard回归；PWF-only做链接/JSON/`git diff --check`。D00 owner 先提交候选版本，再由独立 reviewer 按该 HEAD 审查并要求修复所有发现；修复项重新提交并复核，通过后推送、确认远端 SHA 一致，再交 handoff。
