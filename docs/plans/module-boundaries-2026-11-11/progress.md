# 规划进度

## 2026-11-25 S3/S4 开始实施

- CWP 在包入口复现定时摘要反向加载旧脚本。已迁移到包内运行配置并保留兼容入口，复验配置范围、原语言摘要与已保存结果恢复。FF、RF、StockQA 由各自 agent 在隔离工区推进。 [当前证据和余项](s3-s4-owner-rollout-20261125.md)
- 分仓首批覆盖 12 个模块。FF 离线矩阵 41/41。FF→RF 周测已切换到公开收据，RF 日跑和周测、MC 配置归属已发布且同版 CI 通过。Dashboard 的十个注册器已发布，实际 owner 组合读回 51 份原件和两份 RF 报告。StockWiki 身份修复事务已并本地主线，真实锁竞争和断点恢复通过独审，公开消费组合在验。CWP 来源身份修复已推送，四条跨仓复验通过。StockQA 正核实付费恢复相关纯值契约，RF 旧月测退役保留历史查回。S3/S4 完全验收后接续 F4。 [分仓版本与组合证据](s3-s4-owner-rollout-20261125.md)

## 2026-11-24 — 全 12 模块架构独立性与日志可复现性深度审计（只读，M4 规划补充）

- 严格只读完成全部 12 个生产仓（1,654 个生产 Python 文件、466,417 LOC + Dashboard 前端 `apps/web`）的 AST 全量扫描与四路独立源码逐行核验，未修改任何生产代码、配置或外仓文件。
- 已将完整核验清单、误报过滤记录、CWP 边界扫描器 6 处盲区分析及 S1–S4 分阶段解决方案落盘至 [full-12-module-architecture-logging-audit-20261124.md](review/full-12-module-architecture-logging-audit-20261124.md)，并作为补充更新到本计划 `task_plan.md`/`findings.md`、`feedback-loop-2026-11-17`（F5 日志与可复现性）及父计划 `du11-source-closure-2026-10-18/CURRENT_STATUS.md`。
- 本页保持原 M4 架构审计，日志当前状态见[S1 分仓发布台账](../feedback-loop-2026-11-17/s1-p0-blackhole-plan.md)和[S2 实施状态](../feedback-loop-2026-11-17/s2-unified-logging-plan.md)。

## 2026-11-16 — FF 正式 T3 与 RF 失败周跑

- RF 独立工区以远端 `f2215959` 为父提交，在 canonical `PLANNING_STATUS.md` 记录 `20261115T084227Z / not-ok`、四个实际失败和三仓版本。ROOT 已核原日志及 manifest SHA。提交 `220e5441` 已推远端主线，固定快测 12 项和同 SHA CI 通过。临时工区已清理。
- FF 已给正式下载请求和复用路径补齐限额，并修正旧 adapter 夹具。SID 另修正 CN 候选身份。最终四项正式 T3 通过，72.57 秒，临时来源库清理通过。FF `4c7f501b`、SID `fb8c8ba5` 已独审并发布，M3 收口。 [统一版本与验收](review/m3-formal-t3-20261116.md)

## 2026-11-16 — FF 与 CWP 有限下载离线组合

- CWP 修复一处合成候选缺证券 ID 和一处整体测试限时过短。针对性证明 FF 1.1 带齐限额可下载、重复请求零下载，以及 FF 2.0 路径无关复用和 CWP 原件验真。CN、HK 和 US 均通过。
- 组合 24 项及最终 3 项定向复验通过，独审通过，临时目录清理成功。FF 正式 T3 和 RF 周跑对账由各自 owner 接续。命令、覆盖范围和版本见 [验收记录](review/ff-cwp-bounded-offline-20261116.md)。

## 2026-11-14 — 并线责任按模块归属

- 按用户最新要求明确：各模块 owner 在各自仓库完成未提交改动归因、分支适配、测试、提交、并线和推送；company-wiki 总控只负责 CWP 本仓工作、维护交接、只读核对公开接口和组合结果，不跨仓写代码或改 Git。
- StockWiki 正由另一并行项目修改，当前不触碰其工作区、计划或分支；等其 owner 最终交接后，由 StockWiki owner 自己处理并线。旧记录中“ROOT 在 StockWiki 工区接收”的表述已由 dispatch 当前规则取代。
- Dashboard 文档交接的三个历史 merge 已在用户澄清前完成，提交 `0b31f48`、`8111194`、`63f6820`，只包含文档；此后不再代 Dashboard owner 并线。
- 本次只更新 CWP 的 PWF 责任边界，没有跨仓代码修改或 Git 操作，也没有运行测试。

## 最新进展（2026-11-14）

- E01–E09 已关闭。发布最终 Dashboard `main@e1d1f92`，原件中断测试 3 项、独立审查通过。四个本轮测试工作树与四个测试目录已移除。父计划恢复半年报 R4 及后续业务验收。
- CWP 将来源目录状态留在读取 owner 中，消费端只拿所需能力。原件流只在实际字节验真与事务锁定后发出。独立审查通过后推送 `master@9e76592e1`。
- StockWiki C38/B03 与安装态公开来源读取进入本地 `master@21cf4891`。Dashboard 消费端移除了对 CWP 私有符号及源码布局的依赖。现有安装验收覆盖浏览、原件和摘要证据。
- 实跑 D4 跨仓 30/30、摘要缓存和恢复 36/36、真实募集说明书四根位置替换。RF → FF → CWP 三表新入口已由实际技能安装副本跑通，中微冻结快照两次复用均为零 HTTP，独立审查通过并推送 RF `fab819c2`。
- 当前版本及 E01–E09 验收见 [ROOT 组合记录](review/root_composition_20261114.md)。
- 续核本地改动时按实际 SHA 纠正了旧 Dashboard B-real 统计：120 条 staged path（108 同 blob、10 不同、2 个旧 UI 路径已迁移），没有整包合入。新增 C01证据、B-real模块适配、B03独审收据三张不重叠卡；R1的占位符及 `PENDING_ROUND4` 被登记为未完成，未冒称验收。RF `rf-impl` 历史工区已精确快进到当前 main；其他活跃证据、原件和 StockWiki remediation 保留。详见 [对账表](reconciliation.md) 和 [派发矩阵](dispatch.md)。
- CWP `.p3r-g3check-20261111` 精确回收16个派生夹具/DB文件（435,503字节）；MB-SID原11文件差异以SHA可复核gzip归档从53,423压至15,327字节；`revenue-forecast-audit` 两个已配套工具已本地提交 `fa0564f`，仓库无remote。CWP 本轮只改计划/交接和只读WIP归档，没有修改产品代码。

## A1核销交付（2026-11-11，历史）

- 用户新增授权后，三路独立agent逐模块审查Git refs、worktrees、dirty、PWF/交接/等价补丁；ROOT fetch六个有origin仓。StockWiki/Audit没有remote，未猜建。
- FF B34修复先复现当前main错误拒绝，独立候选保留当前市场/期次/issuer约束，相关回归176 passed/2 skip/38 subtests；追加4例后B34最终23 passed。独审PASS，d563b63快进main并推origin；候选工区回收。
- Dashboard既有4项WIP及边界测试整理，修同名收集冲突和过宽dynamic-import限制；189项平台/文档/预览与29项adapter/70subtests通过，独审PASS，2049356入main并推。审查期间另一harness接收的3个不重叠提交已观察保留，不冒称ROOT作者。24条真实owner stream setup仍缺CWP旧CLI，登记为未通过。
- 清理4个CWP、3个FF测试目录（4971文件/215903376字节）、7个空旧Temp工区、CWP source-facts 11+5重复源码、已吸收stash、ET旧eval、FF空placeholder。RF4生成文件完整保留原字节证据后restore。原始财报、费用stash、真实业务状态保留。
- 五张原卡加入A0逐项接收与测试边界；FF基线更新d563b63。RF B37、SW C38/B03、CWP历史端口差额明确分给对应owner/ROOT，SID有价值WIP先修再收。不新增重叠作者或逐步人工门。
- 完整30.17MB Git元数据快照无损压成1.54MB，字段/记录未裁，未复制任何源码树/原件。记录A1完成时M1/M2及原业务循环未启动；后续进度见下方新增条目。最终发布与清理结果看本轮review收据及Git记录。

以下为M0早先的历史进度，涉及“未测试/未改代码/未建工区”的描述仅对当时成立。

## 2026-11-11

- 用户要求先做完整模块路线图，再支持多个独立 harness。
- 已读父计划和当前收尾记录，选择本目录作为专门架构收口子计划；父计划仍保留业务主线责任。
- 调查和计划编制中；没有恢复源码实施。

### 调查与完整草案

- 三独立agent已完成只读CWP、采集侧、研究/消费者侧调查；ROOT核Git状态、现有测试/包边界与过期PWF口径。
- 当前CWP实际源清单479项已保存，旧索引461项缺口不冒逐文件审计。已证实缺口与仅需验证的风险分开列入boundary_matrix。
- 完成architecture/interfaces/acceptance/dispatch/handoff/runtime_verification、五张独立卡与source_inventory；没有建worktree、启动源码施工、网络/模型或全量测试。
- 方案独审提出fixture等待与旧B34可移动语义两问题，ROOT已改；canonical安装参数补清。等待最终复核。
- 父PWF CURRENT_STATUS/md/json、task_plan、HANDOFF、长期目标已转向本子计划优先，旧D4/D5/P3证据保留并限定范围。

### 规划交付

- 方案独审最终PASS，无未关闭本范围问题；两原阻断及三建议已修复并复核。报告review/plan_independent_review.md。
- 所有JSON解析、文档相对链接、五工区唯一性及14项责任唯一owner检查通过；git diff --check通过。没有运行pytest或生产端到端。
- 五卡状态READY_TO_DISPATCH_NOT_STARTED；M0完成，M1/M2待实施。原生goal经get_goal确认为paused，本轮未恢复源码实施。
- 本次只提交该子计划和父PWF的对齐文档；无源码/配置/原件修改，没有建工区、下载、模型调用或全局技能同步。提交/远端版本由Git记录，避免在文档中嵌入自身HEAD。


CI接线补记：FF `ac798a250b2310e0c2714053b08246ad94fffd0c` 已推main，将B34回归加入既有显式CI清单（原日常smoke不变）；CI清单+B34共38 passed/1.25s。首轮把scratch放在CWP内导致pytest根/JUnit前缀污染，仓外新Temp复验通过，未放宽断言。MB-FF基线采用该最终提交。完整远端CI尚未核验。

## 2026-11-11 — ROOT并入MB-RF可安全接收的B37切片

- 以RF最新main `33d880826` 为基线解决MB-RF PWF重叠，不改RF生产代码；部署及publication-source回归提交 `058be4fd6`，独立审查PASS后推送分支并快进RF main。
- 合并后B37相关suite为171 passed、1 skipped；部署用例38 passed；两次push smoke均12 passed、Ruff通过。最终PWF提交 `6341759b9` 已同步到 `codex/mb11-rf` 与 `origin/main`。
- 不合入B37 scope候选：发现私有跨模块调用、固定IFRS/12-31/单分部和无配置依据的结果上限，并会移除既有`import-rf-job`。已将根因、公开DTO及跨财年/多分部TDD范围记入MB-RF卡；不把未通过的scope测试标绿。
- 四张其他MB卡没有启动，ROOT仍负责StockWiki公开合同差额与最终跨模块组合；原业务主线goal保持paused。


## 2026-11-13 — 五条 owner 施工卡已并线

- MB-CWP：master 代码并线 ref 3ee8d0e；owner 138、exact history/stream 16、readiness history 4 均通过；root 修复 0a03b588 独审 PASS。Dashboard adapter 22/24，2项为消费端引用不存在于 CWP baseline 的私有名称。
- MB-FF：main 代码并线 ref 41acdc8；真实主线隔离套件 26 passed；包级 CI 1012 passed/2 skipped；独审 PASS。
- MB-RF：main 代码并线 ref 6b045b7；完整卡 561 passed、2 failed、3 skipped、31 subtests。两失败已在基线 6341759 复现，分别为历史 subprocess allowlist 和 B34 identity fixture；独审 PASS，不放宽断言。
- MB-ET：main 已包含交付；主线受影响测试 174 passed。包级唯一失败在 baseline 003c1c0 可复现；独审 PASS。
- MB-SID：v2-clean-rewrite 代码并线 ref 53b9358；集成单测 340 passed；独审 PASS。后续 PWF 收尾 commit 为 6742eda。
- 五条线的测试日志、主线ref和WIP处置均已进入各自PWF；原始业务/用户资料仍按各仓清单保留。
- 剩余不是交付包：StockWiki C38/B03 ROOT intake、E01-E09 public-interface composition，以及两个 Dashboard adapter 的 private-import compatibility failures。完整组合仍 NOT_RUN，不冒称模块阶段全结束。


## 2026-11-13 — 专用工区与 scratch 回收

- 已回收五个 MB delivery worktree 与三个 ROOT integration worktree。移除前逐一核实 clean；本轮仅回收这些精确命名工区，分支引用保留。
- FF handoff 指定的 mb11-ff-scratch 已核对仅含 pytest/review/runtime 测试产物后删除，共 5,030 个文件 / 18,119,347 字节；仓内最终日志与 manifest 保留。
- 原主仓数据、用户输入名单、业务状态、密钥文件、工具记忆、其他历史 PWF/未跟踪证据均保留。
- 当前 MB lane 文档的 worktree 字段表示历史交付路径；最新回收状态见 boundary_matrix.json。

## 2026-11-15 — CWP current-head identity repair and publication

- Reviewed all current CWP source deltas in the finite M3 slice. `master@5ae4a60b6` is the source/test head; 36 `src/` paths differ from M2 baseline `c6189c623`, and 12 paths differ from the earlier scanner head `b1e948276`. The complete classification and boundary limits are in `boundary_matrix.json`.
- Fixed CWP1's false identity equivalence across distinct legal forms and an alias-mediated fuzzy auto-resolution bypass. The TDD regressions, Article 7 form pairs, independent reviewer, exact hashes, and scope are recorded in `review/cwp1-legal-form-identity-20261115.md`.
- Final six-file suite 69/69 (20.62s), Ruff passed, pre-commit mypy passed across 490 source files, config doctor passed, cleanup receipt removed=true. Independent review PASS; three focused cases passed.
- Published source commit `5ae4a60b6`; server confirmed `e74840d22..5ae4a60b6 master -> master`; push fixed smoke 18/18 in 6.23s. Full GitHub CI remains unverified. Global M3 remains open for FF, RF and StockWiki owner PWF/ref reconciliation.

## 2026-11-15 17:58 UTC — M3 external refs rechecked without writes

- FF now reads local main@dd716217 and local origin/main tracking ref at the same SHA; the current source delta since M2 is 0 `src/` files, with four test paths and one verifier-tool path. No root FF PWF receipt for finite acquisition limits or a fresh T3 rerun was found. The worktree status command remains unusable.
- RF now reads local main@88892536 versus local origin/main@f2215959, seven commits behind the local branch. Weekly run `20261115T084227Z` remains `ok=false` on its historical triplet; it is absent from root canonical `PLANNING_STATUS.md` (last commit 11-14). Status cannot be confirmed.
- StockWiki now reads local master@e1f9f559 with no remote. Root progress/findings include the 11-15 research run, but task_plan's last commit is 11-08; both status commands still fail.
- No external repository was modified. M3 remains open for those owner PWF/ref/worktree actions; CWP identity fix is complete and published. Matrix records exact snapshots and their limits.


## 2026-11-15 18:13 UTC — elevated read-only M3 owner status and live refs

- Fresh git ls-remote confirms FF origin/main@dd716217; local main matches and tracked files are clean under elevated read-only git status --untracked-files=no. FF still owes finite request-owned acquisition limits and a passing T3 rerun.
- Fresh git ls-remote confirms RF origin/main@f2215959; local main@88892536 is eight commits ahead, with tracked modifications in assurance/runs/weekly_alert.jsonl and weekly_manifest.json. The weekly run remains not-ok and absent from canonical root PWF. ROOT leaves RF untouched.
- StockWiki master@e1f9f559 has no remote and is tracked-clean under elevated read-only status. Its root task_plan still requires owner reconciliation; ROOT leaves its worktree untouched.
- Elevated status succeeded where restricted-sandbox status had failed. The error is attributed to execution context, not repository health. Untracked files were not enumerated because status used --untracked-files=no. Matrix and parent current status now carry the corrected facts.


## 2026-11-15 18:30 UTC — root PWF entrypoints redirected

- Marked the root PLANNING_STATUS.md September snapshot and root progress.md/findings.md October logs as historical, with links to the selected current PWF and M3 records. Existing entries and evidence were preserved.
- This avoids treating stale approval/status text as current without creating another plan or rewriting historical logs. Root status, M3 plan, matrix, README, and handoff now agree on the owner work remaining.

## 2026-11-15 18:58 UTC — root-PWF push classification and pytest scratch cleanup repaired and published

- Root `PLANNING_STATUS.md`, `progress.md`, `findings.md`, and `task_plan.md` were missing from the positive documentation-only range. Before the fix, RED regression tests reproduced the extra fixed smoke and the inaccurate “runtime or configuration” label. The exact four PWF paths now skip tests as documentation; unknown, mixed, runtime, and configuration ranges retain the fixed smoke.
- Real local bare-Git push regression, pre-push classifier tests, and short-basetemp contract ran together: **57 passed, 1 skipped in 13.04s**. The skipped real-symlink case is unsupported by this host; an always-running synthetic Windows reparse test proves chmod is not called. Pytest's final fallback cleanup receipt is `removed=true`.
- Root cause: Git loose objects on Windows carry the ReadOnly attribute; `rmtree(ignore_errors=True)` swallowed 441 PermissionErrors and stranded owned scratch. Cleanup now clears the bit and retries only after `lstat` rejects symlinks/reparse points. Independent source/test review PASS, bound hashes and limits are in [the review record](review/pre-push-classification-and-temp-cleanup-20261115.md); Ruff and `git diff --check` pass.
- Published in CWP `master@56f9cc73dfb8a7f8e84ef30476ffdceef96851bf`; push hook fixed smoke **18/18 in 3.57s**, and the server `ls-remote` confirms the same SHA. Local tracked status is clean. The next PWF-only publication will exercise the documentation-only skip path; this mixed implementation push correctly retained smoke.
- This bounded push/cleanup correction does not alter the M3 owner exit criteria or CWP product source delta. M3 still awaits FF finite T3 limits/rerun, RF canonical weekly-run reconciliation, and StockWiki root PWF reconciliation. Full GitHub CI remains unverified.
- Latest read-only owner refresh: FF local/server `main@dd716217` matches; its current root status records FF1 envelope lane C merged but still contains no finite-limit/T3 rerun receipt. RF remains `main@88892536`, eight commits ahead of server `main@f2215959`, with the two weekly assurance files modified; `20261115T084227Z` is still absent from canonical PLANNING_STATUS.md. StockWiki remains `master@e1f9f559`, no remote, and root `task_plan.md` last changed 2026-11-08. No external repo was modified; status still uses `--untracked-files=no`.

## 2026-11-15 19:50 UTC — full-CI regression causes repaired locally

- CI source: run `43749426185`, job `132919838860`. Anonymous log access returned 403; root causes were established with focused local reproduction, not credential reuse.
- Fixed joined-group predecessor ownership, qualified large-table candidate handling, a planned-PDF test mock that missed the public alias, a stale work-budget fixture, and the saved-response replay's stale diagnostic expectation. The table route remains downstream of table qualification/row filtering and upstream of ordinary fact/semantic admission.
- Added five exact regressions to the existing fixed daily push list (14 total exact nodes, 180s cap); no changed-file fan-out or full suite added to the hook. Pre-commit remains static by design, which is why it did not catch runtime pytest failures.
- Local validation: affected set 236 passed/19.96s on Python 3.13.9; mypy 490 source files passed; Ruff and diff check passed; push smoke 23 passed/12.11s; pytest cleanup `removed=true`. Independent read-only review found no blocker. It did not run tests.
- Local Python 3.14 had one grammar scanner environment mismatch that passed under Python 3.13; Python 3.12 is unavailable locally. No full suite was run locally.
- At 19:50 UTC, publication and exact-head CI were still pending. This checkpoint was superseded by the 20:01 UTC publication entry below; the exact run remains in progress there. See [CI root-cause review](../du11-source-closure-2026-10-18/review/ci-failure-root-cause-20261115.md).

## 2026-11-15 20:01 UTC — CI fix published; exact-head run active

- Commit `895f66f57ce2346c8eb2102c9bd475a828b3e8c8` is pushed; independent `git ls-remote` confirms `origin/master` at the same SHA. Push hook's fixed smoke: 23 passed in 10.71s.
- The original run annotations reported 32 failed instances, broader than the five initial local targets. Re-ran the annotation-driven twelve-file suite as a set: **469 passed in 24.62s**, cleanup `removed=true`.
- Full GitHub run `43755195576` / CI #536 for the exact commit was in progress at this checkpoint and later completed with four failures, recorded below. No claim of full CI success.

## 2026-11-15 20:11 UTC — exact-head run narrowed residual to two test contracts

- GitHub run `43755195576` for `895f66f57` completed with four failed instances: three parameter cases of a Windows-only no-replace rename fallback test running on Linux, and one assertion that the daily list remains a strict subset of the fixed fast inventory.
- Production behavior was already platform-guarded. The Windows test now declares its platform; a platform-proxy companion asserts POSIX hard-link denial propagates and cannot overwrite a concurrent object. The five new daily unit nodes are also recorded in `FAST_CONTRACT_CASES`; `CI_CONTRACT_CASES` still removes unit nodes because full Unit CI owns them.
- TDD/verification: exact CI provided RED for the inventory contract and platform mismatch. The annotation-driven 13-file local suite passed **500/500 in 44.44s**; daily smoke 23/23 in 19.72s; Ruff and diff check passed. Local OS is Windows/Python 3.13.9; real POSIX execution awaits the next GitHub run.
- Scoped independent review passed at baseline `895f66f57`, covering the two follow-up code files. Follow-up edits and PWF are not yet committed. The next exact-head CI must be observed before this issue is closed.

## 2026-11-15 20:19 UTC — follow-up published; exact CI active

- Commit `1391ae81d8126b5026209e26ae56a7d9bb0a9f0c` is pushed to `master`; its pre-push fixed smoke passed 23/23 in 14.31s.
- GitHub Actions run `43757282611` / CI #537 is running on this exact SHA (job `132944030549`). This PWF checkpoint records the run as active; await its complete result before closing the CI repair.

## 2026-11-15 20:27 UTC — exact-head CI passed

- GitHub Actions CI #537 / run `43757282611` passed on `1391ae81d8126b5026209e26ae56a7d9bb0a9f0c`; job `132944030549` completed in 7m52s.
- The run showed one Node.js deprecation warning and one Ubuntu runner migration notice, with no failing annotations. The CI incident follow-up is closed; continue with finite M3 owner reconciliations.


## 2026-11-15 20:52 UTC — current owner snapshot and CI status reconciled (superseded by 21:28 snapshot)

- CWP code SHA `1391ae81` passed exact GitHub CI #537; current `master@3e7b723` is a PWF-only descendant. This closes the CI incident, not M3.
- FF local/server `main@dd716217` matches and is tracked-clean. Its PWF records another S3 BYD bounded-provider E2E and FF-1 merge, but not the current-main rerun for the four RF weekly T3 requests. Those requests omitted finite `acquisition_limits`; FF owner action remains.
- RF local `main@be0caa4` is 9 commits ahead of fresh live `origin/main@f2215959`, with two tracked weekly-assurance files modified. `20261115T084227Z` remains not-ok, pinned to historical FF/RF/CWP refs, and absent from canonical root PWF.
- StockWiki local `master@235ac72` has no remote and is tracked-clean. Latest commit added three CWP source links and updated the `SW-RESEARCH-PRODUCTION-01` handoff; the root task plan remains to be aligned by its owner.
- The CWP working tree also contains an uncommitted source/test candidate changing CN issuer proof cap 64MB→512MB. This is not reviewed, tested, published, or included in the 37-path accepted M3 source snapshot. ROOT will review its root cause before accepting it. No external repo was modified; external untracked files were not enumerated.

## 2026-11-15 21:28 UTC — shared budget root fix and fresh owner alignment (superseded by 21:54 update)

- The 64MB CN issuer proof cap was a duplicate resource owner. `PublicCanonicalBrowser` now passes one request `ReadBudget` into `SourceVersionReader.open_described_version()`; actual bytes/candidates and exact SHA/size are handled by the existing catalog verifier. Removed both `_MAX_CN_PROOF_BYTES` and the local duplicate byte counter; per-PDF/page/text bounds remain.
- TDD evidence: the 36×3.5MB (126MB) browse behavior test, real shared-budget SourceVersionReader test, and affected contracts passed **62/62 in 171.67s**, exit 0, with cleanup `removed=true`; Ruff/JSON/diff-check passed. The first 62-assertion run had teardown exit 1 because an existing root-admission test left its second SQLite catalog open; the `finally` repair now passes standalone and in the full affected pair. Independent review PASS, hash-bound; no production blocker, with a non-blocking note that a CN-browser max-candidate-exhaustion envelope lacks a direct test.
- CI evidence binding corrected: current remote `3e7b7231` contains later product commit `707efe814` after CI-tested `1391ae81`; GitHub #537 is not exact CI for `3e7b7231`. Local `7fd7f248` is an unpublished 512MB intermediate. The final shared-budget change will replace that unpublished commit, be pushed, then receive exact-head CI.
- Read-only owner refresh: FF `main@dd716217` tracked-clean; RF `main@be0caa4` is 9 commits ahead and has three tracked assurance changes; StockWiki `master@54f72c9` has no remote, is tracked-clean, and its root plan/progress updated at `5f79e7b` 17:30 UTC. User confirmed those external changes come from another active project; ROOT preserves them. M3 now waits on FF/RF owner evidence, not a stale StockWiki task-plan date.

## 2026-11-15 21:54 UTC — CWP shared-budget fix published and exact CI passed

- Published `56d10f269b7c67845c7af66b33083f62d46cde4d` to `origin/master`; fresh `git ls-remote` confirmed the same server SHA. Commit hooks passed Ruff, mypy and config doctor; fixed push feedback passed **23/23 in 35.86s**.
- GitHub Actions run `43765642890`, job `132969996667`, passed on the exact `56d10f2` SHA with Python 3.12 in **7m13s**. It reported one warning and one runner migration notice, with no failures. This supersedes older #537 evidence for `1391ae81`; intervening product commit `707efe814` is included in the exact-tested ancestry.
- Source/test contents match the four hashes in [the independent review](review/cwp-cn-issuer-read-budget-20261115.md). The former local `7fd7f248d` 512MB candidate was replaced by the shared request-budget fix. StockWiki's parallel handoff references that earlier state as historical; no StockWiki, FF or RF files were changed.
- Fresh live refs at 21:55 UTC: FF local/live `main@dd716217` still matches and is tracked-clean; RF local `main@be0caa4` remains nine commits ahead of live `origin/main@f2215959`, with three tracked assurance files modified; StockWiki remains local-only `master@54f72c9`, tracked-clean, with root PWF at `5f79e7b`. M3 remains open only for FF's finite-limit/current-main T3 receipt and RF's canonical weekly-run/ref reconciliation. External untracked files remain unenumerated.

## 2026-11-16 分仓 PWF 对账与 CWP 发布

- 九个主模块和四条独立依赖链的入口、版本和各自下一步已核对，记录在 [owner_plans.md](owner_plans.md)。StockWiki 新子计划和 IQS/Dashboard 的活动改动已按 owner 记录。
- CWP 三项根因先复现再修复。普通浏览最终 21 项、边界和日历等 39 项通过；canonical、原件与 parser 的其它通过项及故障复现按原测试批次见 [验收](review/cwp-browse-owners-20261116.md)。独立审查 PASS。各批次临时根已恢复。
- `12e65fe7d` 已推送到 `origin/master` 并读回服务端 SHA。推送快测 23 项通过（33.68 秒）。同一 SHA 的 GitHub CI Run 43962477938 成功，Python 3.12 作业 4 分 42 秒。M3 的开放项为 FF 当前主线 T3 和 RF 周跑/版本对账。 [GitHub Actions](https://github.com/zhengcb81/company-wiki/actions/runs/43962477938)

## 2026-11-24
- 日志补修和正式发布线见[S1 分仓发布台账](../feedback-loop-2026-11-17/s1-p0-blackhole-plan.md)。S2 状态见[实施计划](../feedback-loop-2026-11-17/s2-unified-logging-plan.md)。
