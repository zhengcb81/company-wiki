# 模块 PWF、工区与主线整合计划

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
**状态：完成（七条 owner lane 均已交付；ROOT 修正并登记最终收据）**

- [x] 每模块确定 canonical PWF 入口；历史/子计划保留并回链。
- [x] 统一核对状态词和状态冲突；handoff、review、Git 以各 owner 的最终提交证据为准。
- [x] 完成/待 owner/被取代/真实阻塞分别登记；没有把已列明的 active/evidence 分支误合并。
- [x] 各 owner 写明本仓后续主线和唯一下一步；ROOT 汇总见本文件、`dispatch.md` 和本次进度记录。
- [x] 所有模块只改自己的仓；ROOT 的修复限于本仓总控索引，RF/SID/Dashboard 的收据修正均在对应仓内。

### 七条 lane 最终验收状态（2026-11-14）

| Lane | 本地目标分支 / 收尾 tip | 远端状态 | ROOT 结论 |
|---|---|---|---|
| CWP | `master`；收尾与总控 PWF 更新均已提交 | 最近一次成功核对 `origin/master=7361aad82`；本轮 `ls-remote` 因 `getaddrinfo() thread failed to start` 未刷新 | 本地提交均在 `master`，内容独审 PASS；平台 Mimosa L3 三次阻断 push，**唯一未发布 lane** |
| FF | `main@c2aec910b7b2dc210f60c687390b4da220decbbc` | live `origin/main` 相等 | 已推送；原始测试收据与后续 carrier 提交链有说明 |
| RF | `main@1ea5008290ab302bcfe6d935f3703244139c774f` | live `origin/main` 相等 | 已推送；修正 handoff final SHA 与过期 C4 状态，独审 PASS |
| ET | `main@c777bf1ca82ba7cadf783dee4d0c7341dd48ec7b` | live `origin/main` 相等 | 已推送；内容提交与后续 receipt carrier 已区分 |
| SID | `v2-clean-rewrite@85f39ec5a7358b9de676ad99a21b1ed205565db0` | live `origin/v2-clean-rewrite` 相等 | 已推送；把 `reviewed_head` 从首轮 CHANGES REQUIRED 改到最终 PASS 清单复核 |
| Dashboard | `main@4477eb9377a655a5dcbaf5bdcfbb52803b18561a` | live `origin/main` 相等 | 已推送；本地 follow-up 记录的 CWP 状态和远端 SHA 已修正并独审 |
| RFAudit | `main@50d8ab6fa99db8920358c97f63be4afff8299243` | owner card 明确无 remote | 本地 main 收口完成；交接与 PASS 复核位于 CWP central review |

FF、RF、ET、SID、Dashboard 的本卡新增/修复提交已进入对应目标主线并推送；RFAudit 按卡无 remote，在 `main` 本地收口；CWP 的本地提交尚未发布。既有 active/evidence/跨 owner branch 按收据保留；这不等于漏并线，也不授权把所有非祖先 refs 一律 merge。

### 阶段 3 — 每模块只留一个主要 Projects 目录
**状态：安全分类与可清理项完成；仍保留的目录均有 owner/证据理由，物理目录未全部收敛为一个**

- [x] 每个 owner 核清主仓、工区和 Projects 候选并记录 disposition。
- [x] 已确认可删且不含独有证据的路径按 owner 收据清理；未确认项目、活动工区、审计资料和用户资料保留。
- [x] 保留路径已说明 owner 与理由；StockWiki/IQS 因独立在途任务不触碰。
- [ ] 活动/证据/跨 owner 目录由其 owner 在对应任务完成后再评估；因此“Projects 物理上只剩一个目录”的目标尚未完成，不能对外声称已完成。

### 阶段 4 — 模块 owner 清理、并线与主线接续
**状态：除 CWP 远端发布外已完成本卡提交；CWP 被平台 push gate 阻断**

- [x] 七条 owner 卡按提交、PWF、handoff、测试和独审逐项验收；发现的 RF、SID、Dashboard 收据错误已在各自仓修正。
- [x] FF/RF/ET/SID/Dashboard 对应 closeout 主线已推送；RFAudit 按卡无 remote。
- [ ] CWP 本地收尾与总控 PWF 提交在 `master`，但 push 被平台 Mimosa L3 前置门三次拦截；不得绕过。平台当前阻断范围与未发布提交见 CWP handoff §11 和本次 `progress.md`。
- [ ] CWP 远端确认后，重新核对父计划 `du11-source-closure-2026-10-18` 状态；此时仍保持 paused，不自动恢复公司循环或跨模块组合测试。

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

唯一未完成的发布动作是 CWP 正常推送 `master` 上的本地收尾与 PWF 提交。前置平台 Mimosa L3 扫描阻断尚无本仓可安全修复/基线化的完整报告；待平台规则或扫描结果有变化后，执行一次正常 `git push origin master` 并核验 live SHA。不得改命令、停用 hook 或换通道绕过。其余目录保留项与业务后续按各 handoff 的 owner 顺序处理；父业务 goal 继续 paused。

## CWP lane 状态（2026-11-14）

CWP 本仓收口已按 [owner_cards/cwp_closeout.md](owner_cards/cwp_closeout.md) 执行完成：13 个非祖先 refs（11 `ABSORBED` + 2 `UNCLASSIFIED_HOLD`）、8 个 worktree、4 个额外 Projects 目录、1 个 stash 全部逐项归因，本轮清理为零（无一项满足四重移除条件，依据逐项见交接文件）。CWP 本仓无未归因 refs/工区/目录残留；涉及其他模块 owner 的剩余项列在交接文件 remaining_items。CWP 业务主线唯一下一步为 du11 P1 业务摘要质量修正，父计划公司循环保持 paused。交接与独审绑定：[review/cwp-closeout-handoff.md](review/cwp-closeout-handoff.md) / [cwp-closeout-handoff.json](review/cwp-closeout-handoff.json)。

阶段 2–4 的 owner 卡已全部提交查收。CWP 收尾及总控 PWF 更新均已提交到本地 `master`；最近成功观察到的远端仍为 `7361aad82`。平台 push gate 与本轮 DNS/线程错误使远端状态无法刷新，故仅将 CWP 记为 BLOCKED。其他 lane 的实际结果见上表；StockWiki/IQS 仍暂缓。
