# 模块 PWF、工区与主线整合计划

> **2026-11-15 状态校正：** 阶段 1/2 的“完成”仅指最初七条 owner lane 的交付，不代表九个范围模块的 PWF、在途任务和工作区已全部收口。总续办仍为 **IN_PROGRESS**：StockWiki/IQS 仍有 owner 任务；Dashboard 自身 START_HERE 未记最终 11-15 receipt carrier；RF 自身 PWF 尚未吸收最新 T3 工作区结果；FF 的 F-08 仍是待修产品问题。阶段 3 也未达成“物理上每模块只留一个目录”。本条以 2026-11-15 只读实查为准，详见本计划下方新增状态表与 `progress.md`；旧阶段快照保留为历史。

> **2026-11-15 后续：** CWP 的 M3 当前 HEAD 边界审查已完成首个 TDD 修复切片（动态执行扫描、NarrativeSubjectRef schema owner、pytest 默认长临时路径、Windows 硬链接拒绝的发布兼容）。119 项定向合同/集成测试与 1 项 CLI E2E 通过。该结果不代替其余仓源码差异审查，也不改变 StockWiki/IQS 的 owner 隔离；FF、RF、Dashboard 的 PWF 差异由各仓 owner 在其 canonical PWF 中收口，ROOT 只维护此总控快照。详见 `module-boundaries-2026-11-11/task_plan.md` 与本计划 `progress.md`。

## 目标

把各模块的 PWF 状态、仓库/工区数量、未提交改动、未并线分支及后续主线任务整理成一套可交接的总计划和互不重叠的 owner 施工卡。每个模块只保留一个明确的 Projects 主仓目录；额外临时目录经证据确认后由该模块 owner 清理。模块 owner 自己负责本仓代码修改、提交、并线、推送和本仓 PWF。ROOT/company-wiki 只负责 CWP 本仓工作、总计划、接口协调和只读组合验收。

StockWiki 当前由另一个项目施工：该仓源代码、计划、Git 状态及相关工作目录暂不写入、不合并、不清理；先完成其他模块计划整理，StockWiki 项目结束后再由其 owner 补充本仓状态和清理计划。

## 当前阶段

### 阶段 1 — 固定边界并盘点各模块现状
**状态：完成**

- [x] 明确模块 owner 在本仓完成代码清理、测试、commit、merge、push 和本仓 PWF。
- [x] 明确 StockWiki 与其他并行施工隔离。
- [x] 为 CWP、FF、RF、ET、SID、Dashboard、RFAudit 制定互不重叠的 owner 卡；StockWiki/IQS 明确暂缓，不覆盖现行在途计划。
- [x] 对 CWP、FF、RF、ET、SID、Dashboard、RFAudit 只读核对主线/远端、已知 branch/worktree 规模、PWF/handoff 入口及状态冲突。
- [x] 枚举 63 个模块名前缀匹配的 Projects 顶层候选目录；详细分类和清理由阶段3的每个模块 owner 执行。
- [x] 独立审查七条可执行 owner cards 的写集、起始证据、自包含路径、临时目录处置与大节点测试要求；修复所有发现，审查结论为 PASS。

> 2026-11-14 后续单卡检查进一步明确了七张卡的唯一 PWF 入口、handoff/review 文件落点和最终提交 HEAD 独审顺序。独立 reviewer 首轮发现四处入口歧义，修正后复核最新版七卡为 PASS；ROOT 另确认所列 PWF 入口存在。文档 `git diff --check` 通过。

### 阶段 2 — 清理并统一各模块 PWF
**状态：原七条 owner lane 的交付已完成；九模块总体状态统一仍进行中**

- [x] 每模块确定 canonical PWF 入口；历史/子计划保留并回链。
- [x] 统一核对状态词和状态冲突；handoff、review、Git 以各 owner 的最终提交证据为准。
- [x] 完成/待 owner/被取代/真实阻塞分别登记；没有把已列明的 active/evidence 分支误合并。
- [x] 各 owner 写明本仓后续主线和唯一下一步；ROOT 汇总见本文件、`dispatch.md` 和本次进度记录。
- [x] 所有模块只改自己的仓；ROOT 的修复限于本仓总控索引，RF/SID/Dashboard 的收据修正均在对应仓内。

### 第一轮七条 lane 验收快照（2026-11-14；历史状态，续办结果见下表）

以下表格是本轮续办开始前的第一批七卡验收快照，不是当前所有模块的最终 HEAD；FF、ET、RF、SID、Dashboard 与 StockWiki/IQS 的续办状态以后文“续办 owner lane 最新结果”和对应 owner PWF 为准。

| Lane | 本地目标分支 / 收尾 tip | 远端状态 | ROOT 结论 |
|---|---|---|---|
| CWP | `master`；收尾与总控 PWF 更新均已提交 | 最近一次成功核对 `origin/master=7361aad82`；本轮 `ls-remote` 因 `getaddrinfo() thread failed to start` 未刷新 | 本地提交均在 `master`，内容独审 PASS；平台 Mimosa L3 三次阻断 push，**唯一未发布 lane** |
| FF | `main@c2aec910b7b2dc210f60c687390b4da220decbbc` | live `origin/main` 相等 | 已推送；原始测试收据与后续 carrier 提交链有说明 |
| RF | `main@f2215959d33abc76778342a95d39a8e38191da75` | live `origin/main` 相等 | 3ca6192 的选择性接收与 f2215959 收据载体均经独立复核 PASS；carrier 只更新审查报告/handoff/README，不含产品代码 |
| ET | `main@c777bf1ca82ba7cadf783dee4d0c7341dd48ec7b` | live `origin/main` 相等 | 已推送；内容提交与后续 receipt carrier 已区分 |
| SID | `v2-clean-rewrite@26704a0` | live `origin/v2-clean-rewrite` 相等 | 已推送；本轮 PWF-only 状态更新已提交，用户公司名单保留 |
| Dashboard | `main@8cd2d9477b60a6391dc5b1a4e3d0c94fb66dc6d0` = `origin/main` | 普通 push 后 fresh `ls-remote` 与本地 HEAD 一致；tracked clean | 初审 7 项均修复；全量独审 PASS@fc6dbe7；8cd post-push 收据对齐已独审 PASS，现仅将该 PASS 报告追加提交/推送为 receipt-only carrier；保留 E14 与 WorkBuddy |
| RFAudit | `main@50d8ab6fa99db8920358c97f63be4afff8299243` | owner card 明确无 remote | 本地 main 收口完成；交接与 PASS 复核位于 CWP central review |

FF、RF、ET、SID 的本卡新增/修复提交已进入对应目标主线并推送；Dashboard 新候选已在本地主线但须修复独审发现后再推送；RFAudit 按卡无 remote，在 `main` 本地收口；CWP 的本地提交尚未发布。既有 active/evidence/跨 owner branch 按收据保留；这不等于漏并线，也不授权把所有非祖先 refs 一律 merge。

### 阶段 3 — 每模块只留一个主要 Projects 目录
**状态：一周界线临时目录批次已完成；活动/未并线/独有证据路径仍保留**

- [x] 每个 owner 核清主仓、工区和 Projects 候选并记录 disposition。
- [x] 已确认可删且不含独有证据的路径按 owner 收据清理；未确认项目、活动工区、审计资料和用户资料保留。
- [x] 保留路径已说明 owner 与理由；StockWiki/IQS 因独立在途任务不触碰。
- [x] 处理 2026-11-15 发现的 28 个过期 no-Git 测试/临时目录：先归档全部 19,746 个文件并逐项校验 SHA-256，再按标准路径删除原目录。归档位置、hash、释放空间和自动审批首轮拒绝的原因见 `progress.md` 和 `projects_directory_inventory.md`。
- [ ] 活动/证据/跨 owner 目录由其 owner 在对应任务完成后再评估；因此“Projects 物理上只剩一个目录”的目标尚未完成，不能对外声称已完成。

### 阶段 4 — 模块 owner 清理、并线与主线接续
**状态：FF、ET、RF/RFAudit、SID、Dashboard 的本轮收尾已完成；CWP 收尾序列已由普通推送发布；StockWiki/IQS 保持 owner 在途隔离**

- [x] 七张 owner 卡初轮交付已查收；RF/SID 旧收据修正已验证。Dashboard 本轮最终候选复核结果与发布见下方续办表。
- [x] FF/RF/ET/SID 对应 closeout 主线已推送，RF 内容与收据 carrier 均经独立复核 PASS（[RF review](review/rf-closeout-review.md)）；RFAudit 按卡无 remote 已收口（[handoff](review/rfaudit-closeout-handoff.md)、[独立审查](review/rfaudit-closeout-review.md)）。
- [x] Dashboard 初审发现已修复，最终独审 PASS；最终 post-push receipt-only review 绑定 `8cd2d9477b60a6391dc5b1a4e3d0c94fb66dc6d0`，报告追加 carrier `3f83bb518ca782cb1bff495f7119fda7f3154097` 已推送且 fresh remote 与本地一致。
- [x] CWP 收尾序列和后续 PWF 状态 carrier 均经普通 `git push origin master` 发布：GitHub 响应依次确认 `7361aad82..0e741063f`、`0e741063f..f58011ddd`；推送后本地 `origin/master` 与 `HEAD` 同为 `f58011ddd`。首轮 fixed smoke 18/18 通过（6.58 秒）；最终 docs-only carrier 按配置未跑产品测试。一次独立 `ls-remote` 失败记录在 handoff §12。此前 Mimosa 三次拦截保留为历史记录，本次推送未被拦截。
- [x] 远端接受推送后复核父计划 `du11-source-closure-2026-10-18`，主业务循环仍保持 paused；不因此自动恢复公司循环或跨模块组合测试。

## 大节点审查与测试

1. **盘点收口**：审查每个模块的 canonical PWF、唯一 owner、主仓目录、活动工区、未提交/未并线清单和保留/删除分类是否完整。
2. **模块交付**：每个模块 owner 在其本仓运行针对本模块的完整相关回归一次，完成一次独立审查，提交并线后记录最终 HEAD 和远端 ref。
3. **Projects 目录收尾**：对照删除清单逐项确认目录为空或仅含已批准可重建材料；检查源仓/原件/业务数据/活动 worktree 均未误删。
4. **组合验收**：ROOT 在 CWP 执行有限的公开接口集成场景，复核失败归属和恢复能力；不在每个小步骤重复审批/全量测试。

## 写入与交接规则

- 唯一代码 owner：每个模块一个负责施工和本仓 merge 的 owner；其他 agent 只有明确卡片分支和路径范围。
- 写集合：各卡只写一个仓的指定 PWF 目录和代码路径；总控只写 company-wiki 的本计划及 CWP 路径。
- StockWiki / IQS 当前并行任务：总控不改写其源码、PWF、Git 状态或临时目录；由该任务 owner 完成后交最终 ref 与状态。
- 所有卡交付 `handoff.md` 与 `handoff.json`：记录仓库/分支/最终 HEAD、改动路径、测试命令与结果、独审绑定版本、剩余项、清理路径和保留原因。
- 不接受“分支不在主线=垃圾”或“untracked=临时文件”的推断；必须先关联 PWF、Git、内容及 owner。

## 下一步

当前收尾按用户 2026-11-14 指令逐模块核对 PWF、未提交内容、分支并线和临时目录；2026-11-15 又按用户指示以 2026-11-08 为一周界线清理旧目录。7 个提交已进入各自主线的旧施工 worktree 已移除；28 个无 Git 的旧测试/临时目录先归档并逐 SHA 校验，再删除原目录，归档保留在 Projects 根，净释放约 453 MB。因活动施工、未并线代码、原件或独有证据仍有其它目录保留，故不能宣称 Projects 只剩模块主仓。细节见 `progress.md`。StockWiki/IQS 活动施工保持只读；RF weekly T3 `not-ok` 运行记录保留。父业务 goal 继续 paused。

## 续办：全模块工作区与主线收尾（2026-11-14）

**状态：进行中。** 用户要求每个模块把 PWF 更新到实时状态、清理可解释的未提交残留、把相关提交合到本仓主线并清理确认无用的临时目录/文件。范围为 CWP、FF、RF、ET、SID、Dashboard、RFAudit、StockWiki、IQS；Dayu 是外部项目，不改。

### 写集与并行安排

- ROOT 只写 CWP 与本总计划；FF/ET、RF/RFAudit、SID/Dashboard 分别由三个互斥 agent lane 处理各自仓库。每仓 owner 更新该仓 canonical PWF，归因后再清理/并线/发布。
- StockWiki、IQS 的最新 PWF 与当前工区记录显示另有在途施工（StockWiki 多个注册 worktree；IQS 11-14 的多条 agent 线仍有 OPEN 项）。这次先只读盘点，不清理或合并在途 worktree；待其 owner 最终交接后纳入同一收尾，避免覆盖并行改动。
- 不因文件未跟踪、分支未祖先或目录名含 `tmp` 就直接删除/合并。credential、原件、运行/业务数据、有效 PWF/审查证据和在途 worktree 必须先归因；仅清理确认无文件或已证明可重建且无活动引用的临时产物。每个仓的最终交付做一次集中相关测试和独立复核。

### CWP 当前现场

- 本计划启动续办时，`master` 基线 HEAD 为 `66c97834`（当时相对缓存 `origin/master` ahead 6）；之后正常 push 响应确认收尾提交序列先到 `0e741063f`、状态 carrier 再到 `f58011ddd`。推送后本地 `origin/master` 与 HEAD 同步。首轮 push fast feedback 固定 smoke 18/18 通过；独立 `ls-remote` 曾因本机 `getaddrinfo() thread failed to start` 失败，不能把它称为 fresh-read。11-14 的三次 Mimosa L3 拦截是历史记录；11-15 本次 push 未被该门拦截。
- 初次 closeout 清理快照中 tracked 源码无已知产品代码差异；当时 tracked 改动仅为本计划的 `dispatch.md`、`task_plan.md`、`progress.md`、`findings.md` 与移除过时的一次性 `.tmp-build-registry.py`。提交四份新增收据后，2026-11-15 复测 `git ls-files -o --exclude-standard` 共 23,334 项：`.mimosa/` 10,010、`.planning/` 13,180、`docs/` 143、`.workbuddy-ai/` 1。按用途逐组分类，不能整体 `git clean`。后续五份 PWF/交接状态更新的提交和推送见本计划 `progress.md` 最新记录。
- 已删除 37 个位于 CWP 根目录、内容及嵌套均为空、mtime 早于 2026-11-01 且不是注册 worktree 的旧 `.tmp*`/`.t*`/长度探测目录，合计释放 0 字节。
- 已清理 7 个无引用的旧 `.tmp_*.json` 诊断输出（16,301 B）、2 个 11-02 集成测试遗留 `tmp/osred/**/race.json`（20 B），以及 `.tmp-build-registry.py` 一次性 catalog 检查脚本（1,019 B；仅历史审计文档提到，无生产引用）。本次累计释放 17,340 B，另移除空目录 37 个。工具缓存、Mimosa hook 状态、PWF/审查材料和用户数据未批量清理。
- 后续清理根目录可重建缓存 `.mypy_cache`、`.pytest_cache`、`.ruff_cache`、`__pycache__` 共 1,682 文件/36,929,089 B，以及空 `tmp/pdfs`、`tmp` 两级目录；复查均已不存在。保留 222 MB `.codegraph` 索引、`.venv`、Mimosa 当前状态、历史 PWF/审查证据及用户数据。
- `.planning` 二次只读审计未找到兼具明确可重建、无 PWF/审查引用且释放量值得清理的候选；保留所有未归因历史/运行记录。`.planning/r1-w09-root-integration-20261023/v3/outputs`（4 JSON/3,495,374 B）有 PWF 明确保留要求；`.planning/du8-ff41-root-20261016/**/artifacts`（205 文件/约 462,525 B）仍需精确收据映射；`shared-reading-production` 与当前缓存/DB/WAL 是活跃生产恢复状态。
- CWP 对 StockWiki/IQS 的接线与临时目录写入保持隔离；若 PWF 显示活跃 owner 任务，不代替其 owner 改写。

### 续办 owner lane 最新结果

| 模块 | 当前主线与远端 | 本轮清理/并线结果 | 剩余事项 |
|---|---|---|---|
| filing-fetch | `main@1dfd818` = `origin/main` | 12 个已结案 clean worktree 删除，9,902 文件/138,465,789 B；PWF 提交已推送；push hook 的 Ruff 与 11 项 fast tests 全通过 | 保留 23 个活动/证据/跨 owner worktree 与 3 条证据 refs；保留运行态、密钥和 Mimosa/WorkBuddy 状态 |
| earnings-transcripts | `main@50d9190` = `origin/main` | 47 个 Python/test 缓存文件删除，815,153 B；PWF 提交已推送 | 8 个 Mimosa/WorkBuddy 未跟踪状态保留；既有 `transcript_audit --write-receipts` 冲突退出码 defect 是业务后续项 |
| revenue-forecast / RFAudit | RF `main@f221595` = `origin/main`；RFAudit `main@50d8ab6`，无 remote，clean | RF 两条大幅分歧支线仅选择性接收 PWF/证据；37+45 定向测试通过，3ca 内容与 f221 收据载体独审均 PASS；临时 worktree 已处理。RFAudit 17 个工区/4,264 文件/67,449,856 B 清理，最终独审 PASS | 外部 pytest cache 因 Access Denied 保留；真实 `daily_alert.jsonl` 运行记录保留 |
| SID / Dashboard | SID `v2-clean-rewrite@26704a0` = origin；Dashboard `main@3f83bb5` = origin/main | SID 用户公司名单保留；Dashboard 初审 7 项修复，定向测试/锁/临时E2E恢复收据齐备；最终 post-push receipt-only review PASS（绑定 `8cd2d947`），报告追加 carrier `3f83bb5` 已推送并 fresh 核对远端 | 两仓本轮收尾完成；E14 用户暂停包与 WorkBuddy 用户资料保留 |
| StockWiki / IQS | Last-known 11-14: StockWiki `master@0450506`，无 remote，28 worktrees/39 refs/41 untracked；IQS `master@dab872` = `origin/master`，13 worktrees/13 refs/22,658 untracked。11-15 fresh Git read 均被 Permission denied | PWF 只读复核显示 SW Phase 40 真实数据/owner-shape release 终验仍 OPEN；IQS 11-14 计划仍有跨仓复跑、主体 bundle、真实付费样本及独审 OPEN。无写入、清理或并线 | 维持只读 hold。旧 SHA/数量不代表实时状态；待权限环境可读且 owner 提交最终交接/HEAD 后续做。不能把 `.tmp-*` 或 untracked 直接判垃圾 |

### 完成条件

1. 每个可执行模块的 canonical PWF 明确记录当前 mainline SHA、tracked/untracked 归因、非祖先 ref 的处理决定、保留/删除目录及原因、测试/独审和远端状态。
2. 只有确认属于该模块且产品变更有效的已提交工作才进入本模块指定主线；已吸收、过时或仅承载唯一历史收据的分支按 PWF 归档，不制造空合并。
3. 清理仅针对本仓内或明确授权的该模块临时目录；清单、字节数、边界校验和删除收据入该仓 PWF。原件、用户数据和并行任务材料保留。
4. StockWiki/IQS 完成条件以其并行 owner 正式交付和最终 HEAD 为前置；其在途期间维持只读，不算已收尾。

## CWP lane 状态（2026-11-14）

CWP 本仓收口已按 [owner_cards/cwp_closeout.md](owner_cards/cwp_closeout.md) 执行完成：13 个非祖先 refs（11 `ABSORBED` + 2 `UNCLASSIFIED_HOLD`）、8 个 worktree、4 个额外 Projects 目录、1 个 stash 全部逐项归因，本轮清理为零（无一项满足四重移除条件，依据逐项见交接文件）。CWP 本仓无未归因 refs/工区/目录残留；涉及其他模块 owner 的剩余项列在交接文件 remaining_items。CWP 业务主线唯一下一步为 du11 P1 业务摘要质量修正，父计划公司循环保持 paused。交接与独审绑定：[review/cwp-closeout-handoff.md](review/cwp-closeout-handoff.md) / [cwp-closeout-handoff.json](review/cwp-closeout-handoff.json)。

FF/ET/RF/SID/Dashboard owner 收尾提交已推送；RF 内容提交与 receipt carrier 独立审查 PASS，Dashboard 最终 review PASS 并由 `3f83bb5` receipt-only carrier 推送；RFAudit 按卡无 remote。CWP 收尾序列与最终 PWF carrier 已正常推送至 `f58011ddd`，本地 `origin/master` 与 HEAD 匹配；一次 `ls-remote` 失败不重复尝试。StockWiki/IQS 仍因 owner 在途任务暂缓。
