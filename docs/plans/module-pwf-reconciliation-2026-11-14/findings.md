# 调查发现

## 当前已知约束

- 模块并线必须由各仓 owner 在各自仓内完成；company-wiki 总控只做 CWP 本仓工作和只读组合协调。
- StockWiki 有另一个并行项目正在修改；其写入、merge 和临时工区清理暂缓。
- 当前主线 goal `du11-source-closure-2026-10-18` 状态为 paused；本任务只整理计划与交接，不自动恢复该代码实施目标。
- CWP 当前 owner 边界更新已在 commit `1f9f3dcf3` 推送。此前移除的 CWP 临时测试 SDK/cache 目录有逐路径清理证据；其他未跟踪 `.planning`、`.mimosa` 或 handoff 不可按临时目录一概删除。

## 各仓现状（2026-11-14 只读快照）

Projects 顶层模块名目录已枚举：CWP 5 个，FF 14 个，RF core 14 个，RFAudit 9 个，ET family 8 个，SID 容器 1 个，Dashboard 3 个，IQS 1 个，StockWiki family 8 个，共 63 个候选路径。具体名字见 [顶层目录清单](projects_directory_inventory.md)。这是命名清单，不是垃圾目录清单。

| 模块 | canonical PWF / 主仓 | Git 快照 | 已发现的 PWF 问题 | 处置 owner |
|---|---|---|---|---|
| company-wiki | 本计划为总控；`Projects/company-wiki` | `master@1f9f3dcf3`；8 个注册 worktree；tracked clean；13 个非祖先候选 refs 待本仓处理 | 旧 module-boundaries 记录含已完成历史与当前状态，已新增 owner 并线规则；父业务目标仍 paused | ROOT 负责本仓与总控 |
| filing-fetch | 根 `PLANNING_STATUS.md` 自称全量入口；`Projects/filing-fetch` | `main@d4f35ca` = `origin/main`；tracked clean；35 个注册 worktree；3 个候选 ref | 根状态指向 10-04 的 `fcap` 旧 HEAD；根 PWF 是 8 月记录；MB-FF handoff 未更新 11-14 HEAD；W20 READY 与完成收据冲突；DU10 NEXT_HANDOFF 与接收收据冲突 | FF owner |
| revenue-forecast | 需 RF owner 核定 canonical landing page；`Projects/revenue-forecast` | `main@ec5ba004` = `origin/main`；ROOT 提权读取 tracked 状态 clean；61 个注册 worktree；19 个本地非祖先 refs | MB-RF `task_plan.md` 与 `handoff.md` 互相写“未合并/已合并”；W20 是否已接收需核实；旧 report dirty 报告已被当前 HEAD 吸收 | RF owner |
| earnings-transcripts | 根 `task_plan.md`、`progress.md`、`findings.md`；repo 在 `Projects/earnings-transcripts/earnings-transcripts` | `main@915f216` = `origin/main`；tracked clean；`.workbuddy-ai/` 未跟踪；12 worktree；0 non-ancestor ref | 根计划仍将 Phase 3 标 in-progress、引用 9 月过期 RF 依赖；MB-ET 子卡 11-13 已关闭 | ET owner |
| StockInfoDLSimple | `docs/plans/mb11-sid-2026-11-11/`；repo `Projects/StockInfoDLSimple/v2-clean-rewrite` | `v2-clean-rewrite@d084c4a` = origin；tracked clean；3 worktree；0 non-ancestor ref；两个人工名单文件未跟踪 | G4 卡称整体完成，但保留旧 1.3.0 路由待办；需同当前 HEAD 核实并校正 | SID owner |
| investment-dashboard | D00 的 `.planning/unified-dashboard-2026-10-26/START_HERE.md`；`Projects/investment-dashboard` | `main@50602de` = `origin/main`；tracked clean；80 worktree；92 local branch refs；`.workbuddy-ai/` 保留 | 总状态页面停在 11-04；CWP 三张卡基线仍为 `ff6e764f`；Dashboard 产品仍部分完成 | Dashboard D00 owner |
| StockWiki | 暂缓；`Projects/StockWiki` | 本次未核 Git | 另一项目正在施工；既有旧观察不作为当前接收状态 | StockWiki owner，暂缓 |
| invest-quick-scan | 暂缓；`Projects/invest-quick-scan` | 本次未核 Git | 等当前 owner/并行项目交接后确定 canonical PWF 与清理范围 | IQS owner，暂缓 |
| revenue-forecast-audit | `docs/plans/company-pool-cycle-2026-10-09/task_plan.md` 是循环主计划；`Projects/revenue-forecast-audit` | `main@fa0564fb`；clean；无 remote；0 non-ancestor refs；18 worktrees，其中 17 clean，W08 有未跟踪 PWF 数据 | skill-build 与 W20-AUDIT 已完成；company-pool-cycle 未完成且含多段覆盖状态；需加唯一 START_HERE/status 指针 | RFAudit owner |

Git 状态只读报告分别来自模块 agent 和 ROOT 命令。每个模块 owner 在写入状态前仍须用本仓最终 HEAD 与在途工作复核；不能将 worktree 数、非祖先 ref 或顶层目录名直接解释为“要删/要并”。

## 目录清理原则

“一个主要目录”按一个模块一个长期主仓理解；短期内可保留必需的隔离 worktree，但它们必须有 owner、PWF 和截止/清理动作。可清理目录只包括已确认可重建的测试 scratch、空旧 worktree 或已被正式交接吸收的副本。真实原件、业务输出、未提交源码、尚未交付的 worker worktree、PWF 历史证据、密钥、`.mimosa`/工具记忆和不清楚用途的目录默认保留并标 owner。

## 待确认

- IQS 和 StockWiki 暂不检查，以免与在途 owner 工作重叠；需等最终交接。
- 每仓顶层额外目录的 dirty/handoff/config 引用尚未全部逐项映射；只有 owner 卡收据齐备后才可删除。
