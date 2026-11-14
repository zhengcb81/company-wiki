# CWP-PLAN-WORKTREE-CLOSEOUT 交接（handoff）

- 卡片：[owner_cards/cwp_closeout.md](../owner_cards/cwp_closeout.md)
- 唯一写入仓：`C:\Users\郑曾波\Projects\company-wiki`
- canonical PWF：[task_plan.md](../task_plan.md)（本计划）；业务主线入口 [du11-source-closure-2026-10-18/CURRENT_STATUS.md](../../du11-source-closure-2026-10-18/CURRENT_STATUS.md) 与同名 `.json`
- 执行日期：2026-11-14。机器可读版：[cwp-closeout-handoff.json](cwp-closeout-handoff.json)

## 1. 实时 Git 基线（覆盖卡面快照）

| 项 | 卡面快照 | 本卡实时重核 |
|---|---|---|
| branch | master | master |
| 本地 HEAD | `1f9f3dcf3` | `7361aad82e86cf35310fc05ef51fd8c2c7320b8c`（其后新增 3 个 docs 提交：a23e73c70、f05e8a8ce、1f9f3dcf3→7361aad82 之间的 owner-card 修订；均为 PWF 文档） |
| origin/master | 对齐 | `7361aad82`（与本地一致） |
| tracked 工作区 | clean | clean（`git status --porcelain` 仅 266 条 `??` 未跟踪项，无 tracked 修改） |
| 注册 worktree | 8 | 8（含主仓） |
| master 非祖先本地 refs | 13 | 13（与卡面计数一致；`codex/mb11-cwp`、`codex/root-mb11-cwp-fix`、`codex/r1-final3-source-semantics` 等 6 个 ref 已在卡面快照之后并入 master 祖先，实时重算仍恰为 13 个非祖先） |
| stash | 2（2026-11-11 审计时） | 1：`stash@{0}` = `18ac0d0562`（`On ci-diag-0fb7152: br-ci-fix`；c3 semantic 的 `5b1415d6e` 已退休） |

未跟踪顶层四组（全部保留，见 §5 dirty exceptions）：`.mimosa/`、`.planning/`、`.workbuddy-ai/`、`docs/plans/du11-source-closure-2026-10-18/review/**` 历史审计材料。

## 2. 13 个非祖先 refs 逐项处置

归因方法：`git merge-base --is-ancestor` 实时重算 + [cwp_review.md](../../module-boundaries-2026-11-11/review/repo_reconciliation_20261111/cwp_review.md)（2026-11-11 基线 `46127c13` 的逐 ref 审计）+ [MB-CWP handoff/findings](../../mb11-cwp-2026-11-11/handoff.md) 的 T-* 移植记录 + 对 master 当前树的存在性核对（`git cat-file -e master:<path>` / `git ls-tree`）。

**关键事实**：MB-CWP 卡（`docs/plans/mb11-cwp-2026-11-11/`，已并线为 master 祖先，收口提交 `b9a4a646d`/`3ee8d0e85`）已把 cwp_review.md 第 3 节的全部六个 T-* 候选接收进 master：

- T-READ → `src/company_wiki/source_catalog/source_stream_cli.py` + `tests/contract/test_source_stream_cli.py` + `tests/contract/test_source_reader_exact_history.py`（提交 `f32fbabf8`；exact_history 9 项自 `89fd952a5` 恢复）
- T-CANON → `public_canonical_browser.py`(+CLI)、`cn_primary_issuer.py`、`tests/contract/test_public_canonical_browser.py`、`tests/contract/test_cn_primary_issuer.py`（提交 `eda1f4f9b`，101 项）
- T-B33 → `public_source_readiness.py`(+CLI)、`public_legacy_source_link.py`(+CLI)、`public_legacy_source_recovery.py`(+CLI) 及三个 contract 测试（提交 `566f4cc23`，118 项）
- T-B34 → `tests/unit/b34_cwp_diagnostic/test_unresolved_diagnostics.py`、`tests/unit/b34_cwp_prospectus/test_ipo_cover.py`、`record_unresolved`（无固定 8 条帽）、`_cn_ipo_prospectus_cover`（全前页扫描）（提交 `be85d9ddc`，33 项）
- T-N4 → NO_CHANGE_PROVEN 核销（findings.md「T-N4 核销的可复现证据」两条命令 9+78 passed；主线反向断言 `test_titleless_signal_free_quarterly_remains_reviewable`）
- T-CONFIG → 8 个严格类型反例 RED→GREEN（提交 `be85d9ddc`，72 项；不加第二 `load_llm`）
- T-W13 → 2026-11-11 ROOT reconciliation 已把历史完成事实补回 master `delivery/w13/handoff.md`（提交 `050c6d479`，注明被审版本 `852dff28`，不回退旧 gate 代码）

以上 master 路径均已在本卡用 `git ls-tree -r master -- src/ tests/` 逐一核实存在。

| # | ref | tip | 处置 | 依据 |
|---|---|---|---|---|
| 1 | `codex/d00-e13-owner-integration-20261107` | `62602102a` | **ABSORBED**（ref 保留） | T-CANON 能力由 MB-CWP `eda1f4f9b` 移植；master 存在 canonical browser 模块/CLI/测试 |
| 2 | `codex/d00-return5-cwp-audit` | `ffd67580a` | **UNCLASSIFIED_HOLD**（ref 保留） | 卡步骤 2 明确：该 ref 的工区物理位于 `Projects/investment-dashboard/.worktrees/return5-cwp-audit`，dirty/owner 归因未完整收口；T-B33 家族能力虽已移植，但按卡不得据此推断可删；branch 被注册工区 pin 住，禁止物理目录操作 |
| 3 | `codex/dashboard-b33-cwp-source-proof` | `dc837a21f` | **ABSORBED**（ref 保留） | T-B33 由 `566f4cc23` 移植；master 存在 readiness/link/recovery 六模块+CLI+contract 测试 |
| 4 | `codex/dashboard-cwp-b34-diagnostic` | `7f5f50f8f` | **ABSORBED**（ref 保留） | T-B34 由 `be85d9ddc` 移植；master 存在 `tests/unit/b34_cwp_diagnostic/` |
| 5 | `codex/dashboard-cwp-b34-prospectus` | `29b562dac` | **UNCLASSIFIED_HOLD**（ref 保留） | 同 #2：工区物理位于 `Projects/investment-dashboard/.worktrees/b34-cwp-prospectus`，按卡步骤 2 禁止推断 |
| 6 | `codex/dashboard-cwp-canonical` | `97d55a2dc` | **ABSORBED**（ref 保留） | T-B33/T-CANON 家族；共享历史大量重叠（cwp_review：不能把每个 "+" 重复当新任务） |
| 7 | `codex/dashboard-cwp-exact-reader` | `671149011` | **ABSORBED**（ref 保留） | T-READ：exact_history 9 项历史移植测试与 ref 逐字节相同（MB-CWP review.md 核对），stream CLI 已接当前 `stream_version` owner |
| 8 | `codex/dashboard-cwp-return4-d00-fix` | `b04e9a80d` | **ABSORBED**（ref 保留） | T-B33 家族 |
| 9 | `codex/n4t2-selective-narrative-coverage` | `2b5bec914` | **ABSORBED**（ref 保留） | T-N4 NO_CHANGE_PROVEN：反例已被主线满足，核销证据可复现（MB-CWP findings.md） |
| 10 | `codex/w13-cwp-gates-20261024` | `6efd4fccb` | **ABSORBED**（ref 保留） | T-W13 历史审查/交接文档已补回 master（`delivery/w13/handoff.md` 状态 COMPLETE，提交 `050c6d479`） |
| 11 | `codex/x-c04-current-main-compat-01` | `3199adab0` | **ABSORBED**（ref 保留） | T-READ：stream CLI 薄传输接当前 owner 端口（`f32fbabf8`）；卡内「Non-primary fallback admission 未恢复」的约束已在 MB-CWP owner 级 pair 精确读取中按公开合同处理 |
| 12 | `codex/x-c04-cwp-original-stream-01` | `6b32163ec` | **ABSORBED**（ref 保留） | T-READ 同上 |
| 13 | `codex/x-c04-integrity-repair-01` | `1664c55f1` | **ABSORBED**（ref 保留） | T-READ 同上 |

**为什么 ABSORBED 的 ref 不删除**：这些分支的原始提交携带主线没有的历史 handoff 文档（cwp_review 第 3 节列出的 `docs/handoffs/dashboard-*/…` 等路径只存在于对应 refs，master 未合并）。删除 ref 会使这些独有历史提交不可达。吸收证明覆盖"能力等价"，不等于"原提交无独有内容"；卡要求删除须"无唯一内容"，故全部保留 ref 并记录吸收证据。此结论同时满足"未并线 refs 收敛"：每条 ref 都有明确处置与证据，不再是未知项。

## 3. 8 个注册 worktree 逐项处置

| # | worktree（物理路径） | branch / HEAD | 实时 dirty 摘要 | 处置 | 依据 |
|---|---|---|---|---|---|
| 1 | `C:\Users\郑曾波\Projects\company-wiki` | master @ `7361aad82` | 266 untracked（4 顶层组），无 tracked 修改 | **ACTIVE_KEEP** | 主仓主线；未跟踪项为 .mimosa 工具状态、.planning 历史、.workbuddy-ai、du11 审计证据，卡明确保留 |
| 2 | `C:\Users\郑曾波\.codex\worktrees\du11-extractive-runtime\company-wiki` | `codex/r1-narrative-availability` @ `510193979`（master 祖先） | 65 untracked `.planning/du11-*` 日志，tracked clean | **EVIDENCE_KEEP** | cwp_review：分支可退休，但审计材料未逐文件去重；不得按"未跟踪"批量删 |
| 3 | `C:\Users\郑曾波\.codex\worktrees\du11-source-facts\company-wiki` | detached @ `fcee443ef`（master 祖先） | 7 untracked `.planning/` 审计 JSON，tracked clean | **EVIDENCE_KEEP** | 11 个 tracked 旧副本已按 [source_facts_cleanup_result.json](../../module-boundaries-2026-11-11/review/repo_reconciliation_20261111/source_facts_cleanup_result.json) 恢复（11 restored / 5 redundant removed）；余 7 份为唯一审计材料，工区因"有唯一证据"不满足移除条件 |
| 4 | `C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki` | `codex/main-auto-official-json-20261010` @ `35a9a6459`（master 祖先） | 22 tracked M（13 源码/CI/工具/测试 + 9 docs）+ 37 untracked | **EVIDENCE_KEEP** | cwp_review 归因：21 个 blob 已在主线历史；T-CONFIG 四文件反例已由 MB-CWP `be85d9ddc` 接收（旧 loader 设计被有意取代）；6 份 dirty PWF（cross-market 根三份、phase6/main_auto_official_json 三份）为主线没有的独有过程记录。恢复/归档是后续精确定点动作，本卡不销毁未提交字节 |
| 5 | `C:\Users\郑曾波\.codex\worktrees\w04-narrative-semantics-20261011\company-wiki` | `codex/w04-narrative-semantics-20261011` @ `32a412bb5`（master 祖先） | 3 tracked M + 5 untracked（含 test_w04_narrative_semantics.py） | **EVIDENCE_KEEP** | cwp_review：三文件未证明 blob 等效；旧 HANDOFF 为 STOP_PARTIAL，主线 `7a0b702a0`/`4e58e347e` 已完成更深 owner 修复；scoped negation 反例差集待映射后才能核销退休 |
| 6 | `C:\Users\郑曾波\Projects\company-wiki-r1-local-observation` | `codex/r1-final3-source-semantics` @ `ef49ae3e8`（master 祖先） | 98 M（clean-filter 伪差量，`git diff` 空）+ 260 untracked（R1 resume 记录等） | **EVIDENCE_KEEP** | cwp_review：98 个 dirty JSON 经 clean filter 哈希与自身 HEAD 完全相同，不是行为修改；552+ 份 R1 resume 记录为独有观察证据，勿覆盖勿删 |
| 7 | `C:\Users\郑曾波\Projects\investment-dashboard\.worktrees\b34-cwp-prospectus` | `codex/dashboard-cwp-b34-prospectus` @ `29b562dac`（非祖先） | tracked clean，1 untracked `.test-runs/` | **UNCLASSIFIED_HOLD** | 卡步骤 2 + 独占范围：物理目录属 Dashboard 仓，本卡禁止删除/移动/checkout/清理；只记录 CWP branch/HEAD/dirty 摘要，目录处置由 Dashboard owner 协调 |
| 8 | `C:\Users\郑曾波\Projects\investment-dashboard\.worktrees\return5-cwp-audit` | `codex/d00-return5-cwp-audit` @ `ffd67580a`（非祖先） | tracked clean，1 untracked `.d00-audit/` | **UNCLASSIFIED_HOLD** | 同 #7 |

（dirty 计数为实时 `git status --porcelain=v1 | wc -l`；与 cwp_review 2026-11-11 基线的差异来源：du11-source-facts 的定点恢复收据已执行、m3/w04 部分材料变化，均已按实时值记录。）

## 4. 四个额外 Projects 顶层目录处置

| 目录 | 实测规模 | Git | 处置 | 依据 |
|---|---|---|---|---|
| `Projects/company-wiki-et-live-20261004` | 1 文件 / 4 KB（`report.md`：2026-10-04 ET-LIVE acceptance result，基线 CWP 6b93481 / FF e1eda60 / ET 93fe52c） | 非 git 仓 | **EVIDENCE_KEEP** | 唯一历史验收记录，无副本 |
| `Projects/company-wiki-gates` | 9,700 文件 / ~279 MB（ctrl-\*、ctrl03-candidate-\* 等 gate 观测输出） | 非 git 仓 | **EVIDENCE_KEEP** | 架构 gate 历史观测产物；可重建性未经证实（产物绑定当时基线/配置），卡要求"确认纯可重建产物并列出收据"才可删，现无收据 |
| `Projects/company-wiki-r1-local-observation` | 即 §3 worktree #6 | CWP 注册工区 | **EVIDENCE_KEEP** | 见 §3 #6 |
| `Projects/company-wiki-storage-audit-20261003` | 26 文件 / 940 KB（`.planning/s5-storage-audit-20261003/` + `results/*_raw.json` 6 份原始扫描） | 非 git 仓 | **EVIDENCE_KEEP** | S5 存储审计原始证据（db/dup/inventory 扫描），唯一出处 |

## 5. 未提交例外（dirty exceptions，全部保留）

| 范围 | 内容 | 保留原因 |
|---|---|---|
| 主仓 `.planning/`（主体） | 历史运行/审计材料（cwp_review 记录约 1.3 万件） | PWF 历史证据；逐内容去重无当前任务授权 |
| 主仓 `.mimosa/`、`.workbuddy-ai/` | 工具状态/记忆 | 卡明确保留 |
| 主仓 `docs/plans/du11-source-closure-2026-10-18/review/**` 未跟踪件 | 审计脚本、run 输出、证据 JSON/MD | 历史验收证据 |
| stash `18ac0d0562`（br-ci-fix） | 含 llm_cost_log.csv 16 行独有差量 + 39 项旧删除 + 2 个已吸收测试修复 | reconciliation.md：ROOT 账目归档——独有费用差量须由账 owner 核销/归档；39 项删除无当前任务理由，不整体 pop/drop |
| §3 #2–#6 各工区 dirty/untracked | 见 §3 | 唯一证据或伪差量，均不销毁 |
| §3 #7–#8（Dashboard 物理目录） | `.test-runs/`、`.d00-audit/` 各 1 项 untracked | 本卡禁写该物理目录 |

## 6. 清理执行

**本轮清理：无（0 路径 / 0 文件 / 0 字节）。**

依据：卡步骤 3 的移除条件为"owner 已完成 + 最终源码在 CWP 主线 + 无唯一证据 + 工区 clean"四者同时满足。逐一核对后无一项满足——所有 CWP 侧工区均含唯一证据或伪差量证据，两个非祖先 ref 工区物理位于 Dashboard 目录被卡禁止，ABSORBED refs 携带主线没有的历史 handoff 提交。历史清理（du11-source-facts 11 tracked 恢复、测试 scratch 约 216 MB/18.1 MB 回收、空工区回收等）已有收据存于 [module-boundaries-2026-11-11 review 目录](../../module-boundaries-2026-11-11/review/repo_reconciliation_20261111/)，不在本卡重复执行。

## 7. 模块边界核查

- 未写任何其他仓：StockWiki、Dashboard、FF、RF、ET、SID、IQS、RFAudit 的源码/Git/PWF 均未触碰；仅对 Dashboard 内两个 CWP 工区做了只读 `git status`（卡步骤 2 授权的"记录 dirty 摘要"）。
- 未执行 `git clean -fdx`、整仓 reset、目录通配删除；未删除/移动/checkout 任何 Dashboard 物理目录。
- 写集合仅限：`docs/plans/module-pwf-reconciliation-2026-11-14/`（本计划 PWF + 本 handoff）。

## 8. CWP 已完成 / 未完成与下一步

**已完成（CWP 本仓）**：13 个非祖先 refs 全部归因（11 ABSORBED + 2 UNCLASSIFIED_HOLD）；8 个 worktree 全部归因；4 个额外 Projects 目录全部归因；stash 归因；无满足条件的删除项（记录为零）；本 handoff 与 JSON 交付。

**未完成（移交后续 owner/协调）**：
1. 两个 Dashboard 物理工区目录的处置（Dashboard owner 协调，CWP 侧已提供 branch/HEAD/dirty 摘要）。
2. m3-acceptance 工区 6 份独有 PWF 归档 + 22 tracked WIP 定点恢复（cwp_review 已给逐 blob 依据；需归档收据先行）。
3. w04 工区 scoped negation 反例差集与主线 stage tests 的映射（cwp_review T-W04 关闭条件）。
4. du11-extractive-runtime 工区 65 份 `.planning` 材料逐文件去重后再退休工区。
5. stash `18ac0d0562` 费用差量由账 owner 核销/归档。
6. r1-local-observation 98 个 clean-filter 伪差量文件的可选核销（勿覆盖证据）。

**CWP 当前唯一下一步（业务主线）**：du11 `P1` 业务摘要质量修正——当前来源状态 `partial`，66 条原文均以 claim 展示，含 26 个模型标为冗余的任务与披露载体/具体承诺人混用问题；按 [du11 task_plan.md](../../du11-source-closure-2026-10-18/task_plan.md) 业务摘要段推进"去套话、保归属和计划"，通过后复验付费缓存恢复与 RF 实际采用。父计划公司循环保持 **paused**，本卡不提前执行。

## 9. 测试

文档-only 变更（本卡未改源码/测试/配置），按卡步骤 5 执行：
1. `git diff --check` — 结果见 §10（通过，无空白错误）。
2. handoff.json 可解析裸 JSON 校验 — `python -I json.load` 通过（见 §10）。
3. 新增/修改文档相对链接核验 — 通过（见 §10）。

## 10. 独立审查

- reviewer：未参与实施的独立 agent（见 [cwp-closeout-review.md](cwp-closeout-review.md)）。
- 审查绑定 HEAD 与结论：见 review 报告与 [cwp-closeout-handoff.json](cwp-closeout-handoff.json) `independent_review` 字段。
- 审查范围：13 refs、8 worktrees、4 顶层路径均有状态；清理路径无未解释 WIP；模块 owner 边界未破坏。

## 11. 推送记录

最终推送 SHA 与远端确认：见 [cwp-closeout-handoff.json](cwp-closeout-handoff.json) `final` 字段（本文件定格于候选版本，推送后由 final JSON 为准）。
