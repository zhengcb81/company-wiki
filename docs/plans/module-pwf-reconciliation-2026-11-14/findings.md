# 调查发现

## 七条 owner lane 最终查收（2026-11-14）

- closeout 的“内容提交”和“后续只写收据的 carrier commit”可能是不同 SHA。RF 和 SID handoff 需明确这两类 SHA，避免把首轮候选、基线或历史提交写成最终主线 tip；Dashboard 的 D00 closeout 与其后 owner-acceptance 记录也需分开记。
- ROOT 找到并修复三项可确认的收据错位：RF final 错留 base 且 C4 pending；SID `independent_review.reviewed_head` 错留 CHANGES REQUIRED 初轮；Dashboard 汇总报告把 CWP push 写成已闭环并引用过期远端 SHA。对应内容已在 owner 仓修正、独立复核，并在各自主线发布。
- CWP 未发布的原因不是本卡代码测试失败：平台 PreToolUse 的 Mimosa L3 对全仓历史扫描，阻断三次正常 push；被标记文件在 lane delta 外、delta 仅为 PWF 文档。完整报告没有落盘，已枚举 12 条 high，不完整列出其余 197 high 与 45 medium/low。仓库约定禁止用 `--no-verify`、换 shell/协议或停 hook 绕过；这需要平台/扫描策略处置，不得伪装为项目门禁通过。
- 本轮最新 `git ls-remote` 对 CWP 因 `getaddrinfo() thread failed to start` 失败；最后一次成功远端观察仍是 `7361aad82`。因此本地 master 上的收尾与总控 PWF 提交虽已进入主线，远端状态仍 BLOCKED/未确认。
- RF `assurance/runs/daily_alert.jsonl` 新增的 2026-11-14 运行记录属于实时运行账本，与 handoff 修复无关，已排除在 stage/commit/push 范围外并保留。不要将 tracked diff 误当作本卡 WIP 或清理掉。
- owner closeout 的清理目标是逐项归因并清除已证实可删材料，不是把所有非祖先 refs、活动工区、证据目录一律合并或删除。各 handoff 中 `ACTIVE_KEEP`、`EVIDENCE_KEEP`、`UNCLASSIFIED_HOLD` 仍按 owner 依赖处理；StockWiki/IQS 仍隔离。

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

## CWP lane 收口发现（2026-11-14，cwp_closeout 卡）

- 实时基线推进到 `master@7361aad82`（= origin/master）：卡面快照之后并入的 `codex/mb11-cwp`、`codex/root-mb11-cwp-fix` 等已使 6 个 ref 转为主线祖先，实时重算非祖先 ref 恰为 13 个，计数与卡面一致但成员已更新。
- 13 个非祖先 refs 中 11 个已 `ABSORBED`：cwp_review.md（2026-11-11）第 3 节指认的全部 T-\* 候选能力均由 MB-CWP 卡移植进 master（`source_stream_cli`、`public_canonical_browser`、readiness/link/recovery 六模块、B34 诊断/IPO 封面、T-N4 核销、T-CONFIG 严格类型反例），本卡用 `git ls-tree master` 逐一实测了移植模块/CLI/测试路径存在。T-W13 历史完成事实已在 `delivery/w13/handoff.md`（提交 `050c6d479`）。
- ABSORBED ≠ 可删 ref：这些分支的原始提交携带主线没有的历史 handoff 文档（`docs/handoffs/dashboard-*` 等路径只在对应 refs 可达），删除会使独有历史不可达；退休 refs 须先归档这些提交内容。
- 两个 Dashboard 物理工区（`b34-cwp-prospectus`、`return5-cwp-audit`）tracked 均 clean、各含 1 个 untracked 证据目录；按卡步骤 2 保持 `UNCLASSIFIED_HOLD`，CWP 侧仅记录 branch/HEAD/dirty。
- 清理为零的直接原因：所有 CWP 侧工区都含唯一证据（.planning 审计材料、M3/W04 未归档 WIP、R1 resume 记录）或 clean-filter 伪差量；三个非 git 的 Projects 目录（et-live、gates、storage-audit）都是唯一历史证据，gates 的 9,700 文件/262,499,631 B 观测产物可重建性未经证实。
- stash 仅剩 `18ac0d0562`（br-ci-fix）：c3 semantic 的 `5b1415d6e` 已退休；剩余 stash 含 llm_cost_log 独有差量，归账 owner 处置。
- CWP 业务主线唯一下一步未变：du11 P1 业务摘要质量修正（partial 来源；66 条 claim、26 个冗余任务、载体/承诺人混用），其后复验缓存恢复与 RF 采用；公司循环 paused。
