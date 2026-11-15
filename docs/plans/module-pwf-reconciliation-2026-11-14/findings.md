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

## 各仓起始盘点快照（2026-11-14；不是续办后的最新状态）

本表记录七张 owner 卡开工前的基线；StockWiki/IQS 的后续只读实时快照见本文件“本轮只读 hold 的最新现场”，其他模块以续办表与各仓 owner 最终收据为准。

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

## 本轮只读 hold 的最新现场（2026-11-14）

- StockWiki 已有本地 owner commit `0450506`，无 remote；现场是 28 个注册 worktree、39 个分支、41 个主仓 untracked 状态项。IQS `master@dab8724` 与 `origin/master` 一致，13 个注册 worktree/13 个分支，主仓有 22,658 个 untracked 状态项。两仓 PWF 仍有开放并行实现/组合验收；这些差异与测试材料保持 owner 持有，不由 ROOT 删除或整支并线。
- CWP 自身根 `.mypy_cache`、`.pytest_cache`、`.ruff_cache`、`__pycache__` 是明确可再生的测试/静态检查缓存，已清理 1,682 文件/36,929,089 B；`.codegraph` 索引和 `.venv` 保留。CWP `.planning`、`.mimosa` 与历史 review 文件远大于本轮缓存，但分别承载会话/执行、平台 hook 状态及审查材料；未对它们做 bulk 清理。后续由只读分类决定是否存在可精确删除的冗余副本。
- FF/ET/RF/SID 的 owner PWF+Git 已分别在主线提交并推送；RF 内容与 receipt carrier 都经独立复核 PASS。Dashboard 已修复初审发现并形成 `4d2def1` 候选，等待最终复审后推送。详见 `progress.md` 的时间顺序记录；本计划保持 `进行中`，不能把 StockWiki/IQS hold 或 CWP 未发布的提交写成完成。

## RF / Dashboard 最终 closeout 独审发现（2026-11-14）

- RF 内容提交 `3ca619283411cf2a48afa57a449c44e2aa907768` 已通过独立复核；只含 146 个 `.planning/`、5 个 `assurance/` 文件及 `PLANNING_STATUS.md`，不含产品源码。审查核对原支线/ledger SHA、排除的 470,806 字节 MDB 摘录仍在源 ref、真实 `daily_alert.jsonl`、测试和 `.pytest_cache` 未删除状态。receipt-only carrier `f2215959d33abc76778342a95d39a8e38191da75` 推送后也经独立复核 PASS：仅四个收据文件变更，旧报告字节前缀保留，handoff/JSON/README 指针一致。
- Dashboard 初次独审绑定 `9cb67502c8943a4857e48c50d8c2022049ce2a65`，结论 CHANGES_REQUIRED：错误码 `constructor` 触发原型继承并向 React 返回函数；新增 pytest-asyncio 未锁入 `uv.lock`；handoff 最终/审查/远端 SHA 过期；E14 暂停包未记为保留例外；review 报告路径、`schema_version` 类型与 owner-requests 索引不符合施工卡。owner 声明已修复这 7 项，形成 `4d2def1c5dc0a774a0609543a6bcce4d98680518`，相关前端/后端/E2E、构建及锁定安装检查均通过；最终复审尚未完成，未推送。
- Dashboard 第二轮独审确认 4d2def1 中代码、测试、依赖锁、E14 保留和其余索引/收据问题已修复；先后发现 `handoff.json.final.head` 错指产品提交 `e8eaa85`、e58 的额外顶层键违反卡片固定 schema。owner 的 `fc6dbe7` 修正后独审 PASS，carrier `2e8320e` 推送后发现 status/delivery 与远端字段滞后；最新 docs-only carrier `8cd2d9477b60a6391dc5b1a4e3d0c94fb66dc6d0` 已正常推送，fresh remote SHA 等于本地，等待最终 receipt-only 复核；E14 与 WorkBuddy 均保留。

## Dashboard 最终收据更新（2026-11-15）

- 先前记录的“等待 8cd 最终 receipt-only 复核”已完成并被新状态取代：独立 reviewer 对 `8cd2d9477b60a6391dc5b1a4e3d0c94fb66dc6d0` 的 post-push 状态收据复核为 PASS，审查报告追加后由 docs-only carrier `3f83bb518ca782cb1bff495f7119fda7f3154097` 推送；fresh remote SHA 与本地 HEAD 一致。
- Dashboard owner 报告 tracked worktree clean，E14 用户暂停 handoff 与 `.workbuddy-ai/` 仍保留。无产品代码修改、未重跑产品测试；最终内容代码测试仍按此前实现证据及最终完整审查记录引用。
- 本轮总控 PWF 已更新为最终 `3f83bb5`，不再把 Dashboard 报告追加 carrier 写作待办。CWP 的本地提交/远端门禁与 StockWiki/IQS 的 owner hold 是独立未结项。

## StockWiki / IQS 只读状态复核（2026-11-15）

- 两仓 canonical PWF 可读，均显示 owner 工作未闭合：StockWiki Phase 40 的真实数据与 owner-shape release 终验仍 OPEN；IQS 的跨仓组合复跑、主体 bundle 核验、真实付费样本和独立终审仍 OPEN。
- 本次尝试刷新两仓 Git HEAD/remote/worktree 均因当前文件系统权限返回 `Permission denied`，没有写入。`master@0450506`（StockWiki）与 `master@dab8724`（IQS）及工区计数只能引用 2026-11-14 上次已知快照，不得称本轮实时核验；权限可读且对应 owner 交付后再继续收尾。

## 全模块收尾续办现场（2026-11-14）

- 用户本轮明确要求重新逐模块更新 PWF、归因并清理未提交项、把有效提交并入主线、移除确认无用的临时材料。ROOT 只改 CWP；FF/ET、RF/RFAudit、SID/Dashboard 由互斥 owner lane 并行。StockWiki/IQS 实时 PWF 仍有在途 owner 工作；两仓暂时只读，不碰活动 worktree，待 owner 交接后续办。
- CWP untracked 不是一种“垃圾”：提交四份新增收据后，2026-11-15 复测为 23,334 项：`.mimosa` hook-state 10,010、`.planning` 执行/审查记录 13,180、`docs/` PWF 与审查证据 143、`.workbuddy-ai` memory 1。全量删除会丢当前平台 hook 状态、历史测试/审查依据或用户笔记。
- 已安全删除 CWP 根下 37 个空旧测试目录、7 个已无引用的旧 `.tmp_*.json`（16,301 B）、两个 11-02 测试遗留 `tmp/osred/**/race.json`（20 B），以及无生产引用的一次性 `.tmp-build-registry.py`（1,019 B）。本轮释放 17,340 B，另删 37 个空目录；删除均在 CWP 根内逐项验路径/mtime/文件清单。
- CWP 当前 tracked 代码未改；`master` 仅增加本任务的文档/临时脚本删除记录。`origin/master` 最近成功 live 观察仍是 `7361aad82`，三次 Mimosa L3 正常 push 阻断继续有效，不绕过。
