# CWP 工作区与未并线提交核销

审计基线：2026-11-11，`master = origin/master = 46127c13465552a18e4560d107b0e68ee28268ff`。范围为 C:/Users/郑曾波/Projects/company-wiki 的 62 个本地/远端跟踪 refs、8 个注册工区、2 个 stash。ROOT 已执行 fetch；本审随后核对 refs，没有网络调用。完整路径基线见同目录 [inventory_before.json.gz](C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11/review/repo_reconciliation_20261111/inventory_before.json.gz)。

本审只读 Git、源码差量、PWF 和交接文档；未运行测试、安装、产品入口、下载或付费操作，未读取密钥/原件内容，未改 Git 或生产文件。唯一额外机器文件由 ROOT 后续明确要求：[source_facts_cleanup.json](C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11/review/repo_reconciliation_20261111/source_facts_cleanup.json)。以下测试数字均为已有交接记录，不能当成本轮实测。

## 1. 可执行结论

1. **可立即接收的是 W13 历史审查文档，不是旧 gate 实现。** 主线 `delivery/w13/handoff.md` 仍为 `bf0cc52f5` 的待独审草稿；候选 `6efd4fccb` 已保存 COMPLETE 和独审 APPROVE、对 `852dff283` 的补审。取 `delivery/w13/review.md`、`review.json`，并把完成事实补回 handoff.md/json、原 progress，明确“2026-10-24 被审版本”；不得写成当前主线验收。主线 `67439d0ac` 已修相同 label/node 去重问题，`819cef31a` 又改为固定 smoke，故不合旧代码。
2. **41 refs 是主线精确祖先**（含 master、origin/master、origin/HEAD 三个基准）；其余有三个纯 `git cherry -` 功能/审计 refs，以及 DU11 文档最终树等效 ref。精确祖先只需核销引用，不需要重新合并或跑产品测试；有工区的先处理工区副本。
3. **detached source-facts 的 11 个 tracked 差量和 5 个 untracked 测试全部是主线可达精确 blob。** 可按机器清单复核后恢复/删除旧副本，保留 7 份 .planning 审计材料。它不是新的待接收源码。
4. M3 的 25 个源码/测试/CI/工具差量中 **21 个完整 blob 已在主线历史**；另 4 个是旧 `Config.load_llm` 设计。同根因已由 `0b61bcd13` 以 `Config.load(validation_scope="llm")` 实现，后有 `ad2d0f74a`、`ce1a603a8` 演进。不引入第二套 loader；只把候选仍有价值的严格参数反例纳入 CWP 卡。
5. R1-local-observation 基线的 **98 个 dirty JSON，经 clean filter 哈希全与自身 HEAD 完全相同**，`git diff --numstat` 无差量。是换行/状态观察，不是 98 个未接收行为修改；不要重写这些文件制造新提交。
6. **D00/E13、B33、B34、X-C04、N4T2 不能按 ahead 数字整链并入。** 其中有真实尚未主线化的 CLI/功能，也有已被当前公共读取/预算/解析端口替代的实现。保留为单张 CWP 卡的接收子项，先移植反例，再决定最小实现；下文给出有限关闭条件。
7. `stash@{0}` 的两个 post-image 已精确入主线，可退休。 `stash@{1}` 的两个测试修复已入主线，但夹带 39 个文件删除和未核销费用日志差量，不能整体 pop 或丢弃。

## 2. 证据方法与状态含义

- `git merge-base --is-ancestor <ref> master` 为 0：精确接收证据。表中“主线独有/ref独有”来自 `rev-list --left-right --count master...ref`。
- `git cherry master ref` 的“−”证明 patch-id 等效；“+”只表示整提交 patch-id 不同，**不证明功能缺失**。它不计 merge commit，因此 +/− 总数可小于 ref 独有数。
- DU11 的 `e6280e6e` 虽为“+”，其整个 `docs/plans/du11-source-closure-2026-10-18` 最终 tree 与主线 `b59e2141a` 相同；随后 `46c24a532` 为“−”。
- 旧工区使用不带 `-w` 的 `git hash-object --path=<git-path> <absolute-path>`，再查询 `git rev-list --objects master -- <git-path>`。已找到相同完整文件 blob 才标精确已接收；“历史 blob”不等于当前主线仍保持该版本，应保留后续演进。
- 本审曾对 B34 作 `git apply --check --reverse`，失败只能说明当前文本不支持原位反应用，不单独用它证明缺陷或缺失。
- 下列“可退休”指 refs/重复工作副本，**不包括随工区存放的独有审计材料、费用账、用户记忆或原件**。ROOT 是清理 owner；C0 入口为重新核 HEAD、可达性、精确路径/哈希，不运行产品测试。

## 3. 未并线能力：归属和有限关闭条件

| 包 | 已确认事实 / 不能误判的风险 | owner 与下一步 / 结束条件 |
|---|---|---|
| T-CANON：D00/E13 `62602102a` | 主线无 `public_canonical_browser.py`、`cn_primary_issuer.py` 路径历史。addendum 明确 owner 合同 64、browser/reader 21 项为历史通过，但 Dashboard HTTP/range/cancellation/最终独审仍 pending。含另一条 current-reader stream 兼容补丁，不能全链当纯 canonical。 | CWP source_catalog owner，归原 CWP 卡公开入口/根与预算边界；Dashboard 只消费。先保留 `test_public_canonical_browser.py`、`test_cn_primary_issuer.py`、`test_canonical_as_of_calendar.py` 的契约反例；按现有 reader、issuer 与实际预算端口实现，无第二事实库。关闭于明确可支持/不可支持命名空间、当前公共 CLI + 下游精确版本证明通过；外部组合仍由 ROOT。 |
| T-B33：`385cee72b` / `dc837a21f` | readiness、legacy_source_link、legacy_source_recovery 为真实未合路径；handoff 明确 AUTHOR_IMPLEMENTED_PENDING_INDEPENDENT_REVIEW，CWP-001/002 复核和生产 apply 未完成。安全外观不能替代身份/原件/retirement observation 证明。 | CWP storage/source reader owner。先接 branch 中 `test_public_source_readiness.py`、`test_public_legacy_source_link.py`、`test_public_legacy_source_recovery.py` 的独立反例；仅复用现有 restore_document_facts，不增 writer。关闭于 current owner 接口证明及原 reviewer 条目逐项结论；本次不生产恢复。 |
| T-B34：diagnostic `db6fd6cb`、IPO 最终 `925b0ad3` | 8 提交均非 patch-id 等效。最终 handoff 记录独审 25 cases、IPOR001–005 闭合；真实 sourceprep 仍 unresolved，不可声称季度来源已解决。主线 local_reconcile 自分叉后有 7 个修改提交/250 行差异，含 `ef3d92a26/fef24418a/729a78764/e5dd29b1f` 的预算/owner 演进。旧 diagnostic 固定 8 条、旧 cover 只看既定前页，须按现行 R7 核对，不原样恢复任意表示门。 | CWP local intake/source fact owner。用 `tests/unit/b34_cwp_diagnostic/test_unresolved_diagnostics.py`、`tests/unit/b34_cwp_prospectus/test_ipo_cover.py` 建当前 RED；沿现有抽取/身份 owner 移植最小缺口。关闭于未绑定 issuer/冲突 cover 保持拒绝、可证 cover 通过、诊断不冒充来源事实；不以真实研究目标替代这组接受标准。 |
| T-READ：exact/history 与 X-C04 | `89fd952a` 曾增加非 primary 回开，历史独审通过；当前 X-C04 compat 提交 `3199adab` 又明确“Non-primary fallback admission is NOT restored”。旧 stream CLI/byte-lock 路径在主线缺失，但主线 `54f8b470c` 已有公共 `stream_version` / parser owner 端口，不能另做读取/预算 owner。 | CWP reader/normalization owner（原 CWP 卡同一作者）。复用主线 `tests/contract/test_source_version_reader.py` 的 stream/resettable budget/cancellation/sink-failure/fallback 用例；历史 `test_source_reader_exact_history.py` 先映射合法 admission，再决定增补 CLI。关闭于所有消费者走现有 verified stream、同一预算、每次读一次；若新 CLI 不再有消费者，明确撤销该能力并保留历史证据。 |
| T-N4：`2b5bec914` | 六个 post-image 均未找到主线精确 blob；不能标完全等效。主线 `ea9dd266f` 已独立实现 current-business-progress，`7a0b702a0`/后续 DU 源语义又演进。旧方案还改变“signal-free” skipped_no_narrative 判定，不能靠同名描述认定全被覆盖。 | CWP source material owner。仅提取仍独有的 CN quarterly/IR、空扫描/financial-row 反例，映射当前 `test_narrative_evidence.py`、`test_narrative_select_handler.py`、`test_narrative_selection_architecture.py`；通过即核销旧实现，失败才最小修复。不恢复旧大文件或旧 eligibility 语义。 |
| T-W13：`6efd4fccb` | 文档独有，历史已独审的状态在主线仍写待审；代码职责已由后续 gate 替代。 | ROOT 可立即接历史 review/handoff 完成更正；现有工程入口 `tests/unit/test_daily_push_policy.py` 仅在代码改变时使用。本次纯文档核对无需运行测试。 |
| 旧 FC802 rejected | `ec00a0280` 两个首轮 rejected 文档不在主线；主线仅 r2/r3，最终 r3 是补丁等效。 | 保留 `origin/codex/history/fc802-rejected-20261003` 为审计历史，不能覆盖当前 r2/r3，也不能仅因“rejected”删除。无生产接收任务。 |

关键交接 Git 路径（从对应 refs 读取，不是主线已存在的声明）：
- E13：`docs/handoffs/dashboard-G-CWP-CANONICAL-01/d00-e13-integration.md`。
- B33：`docs/handoffs/dashboard-B33-source-proof/README.md`。
- B34：`docs/handoffs/dashboard-B34-prospectus-cover/handoff.md`。
- exact：`docs/handoffs/dashboard-G-CWP-EXACT-01/handoff.md`。
- W13 接收源：`6efd4fccb:delivery/w13/{handoff.md,handoff.json,review.md,review.json}` 与其 `docs/plans/w13-cwp-gates-2026-10-24/progress.md`；`measurement_caveat` 在 `852dff283:delivery/w13/scope-report.json`。新文档标明历史被审 SHA，不回退源码。

## 4. 完整 refs 核销清单

62 行逐 ref；主线独有/ref 独有不是合并建议。C0=仅引用核销；T-* 见上表。远端 ref 退休建议不等于本审已删除远端分支。

| ref | tip | 主线/ref独有；证据 | 状态 / owner入口 |
|---|---|---|---|
| `refs/heads/codex/d00-e13-owner-integration-20261107` | `62602102a` | 39/10；+6/−3 | 保留候选，待当前端口接收；T-CANON |
| `refs/heads/codex/d00-return5-cwp-audit` | `ffd67580a` | 253/29；+25/−3 | 待复核，勿整链并入；T-B33 |
| `refs/heads/codex/dashboard-b33-cwp-source-proof` | `dc837a21f` | 253/31；+27/−3 | 保留候选，待复核；T-B33 |
| `refs/heads/codex/dashboard-cwp-b34-diagnostic` | `7f5f50f8f` | 146/2；+2/−0 | 保留候选，待移植；T-B34 |
| `refs/heads/codex/dashboard-cwp-b34-prospectus` | `29b562dac` | 146/8；+8/−0 | 保留候选，待移植；T-B34 |
| `refs/heads/codex/dashboard-cwp-canonical` | `97d55a2dc` | 253/28；+24/−3 | 待复核，勿整链并入；T-B33 |
| `refs/heads/codex/dashboard-cwp-exact-reader` | `671149011` | 253/7；+4/−3 | 待判定历史admission契约；T-READ |
| `refs/heads/codex/dashboard-cwp-return4-d00-fix` | `b04e9a80d` | 253/25；+21/−3 | 待复核，勿整链并入；T-B33 |
| `refs/heads/codex/main-auto-official-json-20261010` | `35a9a6459` | 863/0；祖先 | 精确祖先可退休；C0 |
| `refs/heads/codex/n4t2-selective-narrative-coverage` | `2b5bec914` | 1218/2；+1/−1 | 未证完全等效，保留反例；T-N4 |
| `refs/heads/codex/r1-final3-source-semantics` | `ef49ae3e8` | 413/0；祖先 | 精确祖先可退休；C0 |
| `refs/heads/codex/r1-narrative-availability` | `510193979` | 449/0；祖先 | 精确祖先可退休；C0 |
| `refs/heads/codex/w04-narrative-semantics-20261011` | `32a412bb5` | 868/0；祖先 | 精确祖先可退休；C0 |
| `refs/heads/codex/w13-cwp-gates-20261024` | `6efd4fccb` | 375/2；+2/−0 | 接收历史文档；T-W13 |
| `refs/heads/codex/x-c04-current-main-compat-01` | `3199adab0` | 41/1；+1/−0 | 旧实现保留，接现有stream端口；T-READ |
| `refs/heads/codex/x-c04-cwp-original-stream-01` | `6b32163ec` | 253/32；+28/−3 | 旧实现保留，接现有stream端口；T-READ |
| `refs/heads/codex/x-c04-integrity-repair-01` | `1664c55f1` | 253/34；+30/−3 | 旧实现保留，接现有stream端口；T-READ |
| `refs/heads/master` | `46127c134` | 0/0；祖先 | 保持主线；ROOT |
| `refs/remotes/origin/HEAD` | `46127c134` | 0/0；祖先 | 保持主线；ROOT |
| `refs/remotes/origin/codex/architecture-dashboard-browse-20261109` | `e2a448cc9` | 32/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/architecture-fast-feedback-20261102` | `819cef31a` | 116/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/architecture-module-quality-20261109` | `f5cba7dd0` | 37/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/architecture-rectification-20261101` | `6668bc978` | 142/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/architecture-rectification-r2-20261101` | `10767b863` | 106/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/architecture-t3-source-scope-20261102` | `fa8ef38ee` | 102/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/architecture-w23-repair-20261101` | `6b70394b3` | 118/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/company-pool-source-fixes-20261009` | `d79231919` | 1001/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/d00-e13-owner-integration-20261107` | `62602102a` | 39/10；+6/−3 | 保留候选，待当前端口接收；T-CANON |
| `refs/remotes/origin/codex/d4-03-document-model` | `79abab69d` | 73/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/d4-04-transcript-wire` | `904b1a04e` | 72/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/d5-cwp-processed-port` | `a28692a6c` | 42/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/dashboard-p2-cwp-market-20261109` | `0fc56b25b` | 21/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/g1-legacy-entry-retirement` | `c3209eee0` | 1245/2；+0/−2 | 补丁等效可退休；C0 |
| `refs/remotes/origin/codex/g3-cwp-maint` | `34d020f44` | 1072/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/history/fc802-r3-accepted-20261003` | `29abc878d` | 1589/1；+0/−1 | 补丁等效可退休；C0 |
| `refs/remotes/origin/codex/history/fc802-rejected-20261003` | `ec00a0280` | 1592/1；+1/−0 | 保留历史拒绝审计；C0 |
| `refs/remotes/origin/codex/m3-acquisition-usage-20261010` | `704c374fb` | 900/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/m3-generation-policy-20261009` | `62770fea7` | 904/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/m3-http-source-20261009` | `6cc9959fd` | 912/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/m3-official-json-20261010` | `4fc9ee1b1` | 898/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/m3-transcript-role-20261009` | `3f3f55c1c` | 913/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/n4t1-model-transport-diagnostics` | `4a53080b7` | 1218/1；+0/−1 | 补丁等效可退休；C0 |
| `refs/remotes/origin/codex/n4t2-selective-narrative-coverage` | `2b5bec914` | 1218/2；+1/−1 | 未证完全等效，保留反例；T-N4 |
| `refs/remotes/origin/codex/n5-document-quality` | `2c3583e08` | 1149/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/n6-budget` | `18dbd0e20` | 1126/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/n6-candidates` | `f31cc0d4f` | 1125/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/n6-footprint` | `7f27f633d` | 1126/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/p5-storage-integration` | `9fa216677` | 1180/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/p7-cwp-projection-identity` | `4f2c05c92` | 883/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/r1-final3-source-semantics` | `1712ed10e` | 422/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/r1-w11-source-recovery-20261023` | `e808404ed` | 420/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/w13-cwp-gates-20261024` | `6efd4fccb` | 375/2；+2/−0 | 接收历史文档；T-W13 |
| `refs/remotes/origin/codex/w18-cwp-holdout-20261025` | `b697bcf9b` | 312/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/w19-sina-statements-20261025` | `22ab7a419` | 303/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/w22-atomic-io-20261030` | `d19bda045` | 210/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/w22-pdf-deploy-20261030` | `dc423843e` | 204/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/w23-ocr-r1-20261031` | `d2f6e6f01` | 154/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/codex/w23-xiaomi-ocr-20261030` | `a517213cc` | 188/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/du11-close-docs` | `46c24a532` | 533/2；+1/−1 | 最终树等效可退休；C0 |
| `refs/remotes/origin/du11-repair-flag` | `09cb49ad7` | 532/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/fcap` | `8665c8c47` | 1370/0；祖先 | 精确祖先可退休；C0 |
| `refs/remotes/origin/master` | `46127c134` | 0/0；祖先 | 保持主线；ROOT |

同名 local/remote 中 R1-final3 不同 tip（local ef49ae3e8，remote 1712ed10e），两者仍都是主线精确祖先。D00 / return4 / canonical / B33 / X-C04 共享大量历史提交，不能把每个“+”重复当新任务；exact-reader 的独立 review docs 也不能因代码提交共享而丢掉。

## 5. 八个工区和未提交材料

本节绝对根固定；具体全部路径可由 inventory_before.json.gz 对应 worktree_details 重放。只有下述已证明范围可定点处理。

| 工区 | 基线状态与归因 | 处置与 owner测试 |
|---|---|---|
| C:/Users/郑曾波/Projects/company-wiki | 唯一 tracked 变动是 ROOT 本轮 `docs/plans/module-boundaries-2026-11-11/task_plan.md`；没有未提交 src/scripts/tests/tools/config。14934 个 untracked 主要为 .planning 13123、.p3r 710、.p5 461、.p3 362、DU11 review 143、pytest root127、g3check7、workbuddy memory1。 | ROOT A1 保留。ROOT 已通知四个旧测试根完成清理，见其清理收据；本审未执行，不将 before 数量冒充 after。大量 .planning/143 DU11 审计材料、.workbuddy-ai memory 不按“未跟踪”批量删除。 |
| C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki | HEAD 510193979 精确祖先，tracked clean，81 个 .planning 未跟踪材料。 | 分支可退休；审计材料尚未逐文件去重，保留或归档后再拆工区。无源码接收测试。 |
| C:/Users/郑曾波/.codex/worktrees/du11-source-facts/company-wiki | detached fcee443e 是主线祖先；11 dirty + 5 untracked 完整 blob 全已接收。7 份 .planning 另保留。 | 按 source_facts_cleanup.json 定点恢复到自身 HEAD/删除 exact untracked，不改 index，不覆盖 master。C0 哈希复核即足够，源/测试不重新执行。 |
| C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki | HEAD35a9a645 精确祖先；22 dirty（13源码/CI/工具/测试+9 docs），317 untracked（193跨市场PWF、112.planning、12源码/测试）。 | 下节 21个精确blob可清旧副本；4个配置差量与6个独有PWF先保留交接。不整包 restore/delete。CWP config owner T-CONFIG。 |
| C:/Users/郑曾波/.codex/worktrees/w04-narrative-semantics-20261011/company-wiki | HEAD32a412bb 精确祖先；3 dirty +1 untracked test，另91材料。业务组/证据/新test未找到相同完整 blob；已有 test_narrative_business_recall 与 master 相同。 | 旧stage交接明确 STOP_PARTIAL，保留两条未正确否定的真实失败；主线7a0b702a/4e58e347已完成更深owner修复。不直接合旧实现；仅剩反例差集纳入CWP，核销后退休。 |
| C:/Users/郑曾波/Projects/company-wiki-r1-local-observation | HEADef49ae3e 精确祖先；inventory 98 dirty JSON clean-filtered 后98/98与HEAD相同，diff空；566 untracked中552是R1 resume记录、13.planning、1 pytest输出。 | 无源码WIP；保留独有失败/复核/trace材料。可先核销98个伪差量，勿把新测试运行覆盖旧证据。 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/b34-cwp-prospectus | HEAD29b562dac 非祖先，tracked clean，5个 .test-runs。 | T-B34候选保留；测试输出是否由handoff引用未完整去重，暂不随工区整体删。 |
| C:/Users/郑曾波/Projects/investment-dashboard/.worktrees/return5-cwp-audit | HEADffd67580 非祖先，tracked clean，8个 .d00-audit（CLI/SHM probe和结果）。 | T-B33/CANON历史审计保留；脚本不是当前生产入口。 |

### source-facts 精确副本（机器清单的可读索引）

根为 C:/Users/郑曾波/.codex/worktrees/du11-source-facts/company-wiki。完整 blob 在 JSON；此表缩写只用于阅读。

| Git路径 | 状态 | post-image blob | 结论 |
|---|---|---|---|
| `src/company_wiki/document_understanding/decision_inventory.py` | tracked | `00d9de349b87` | 主线历史精确blob；可清副本 |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | tracked | `9d3823e3966c` | 主线历史精确blob；可清副本 |
| `src/company_wiki/source_catalog/narrative_evidence.py` | tracked | `711aba1adb5b` | 主线历史精确blob；可清副本 |
| `src/company_wiki/source_catalog/resolver.py` | tracked | `84659ad4ff69` | 主线历史精确blob；可清副本 |
| `src/company_wiki/source_catalog/source_reader.py` | tracked | `c9560c261c5e` | 主线历史精确blob；可清副本 |
| `tests/test_phase_c_readonly_source.py` | tracked | `7ca6bbecdcb0` | 主线历史精确blob；可清副本 |
| `tests/unit/document_understanding_selection/test_reading_portfolio_disclosure.py` | tracked | `5fb74bee94cb` | 主线历史精确blob；可清副本 |
| `tools/changed_unit_tests.py` | tracked | `d341b386ce63` | 主线历史精确blob；可清副本 |
| `tools/document_understanding_benchmark/phase_c_observer.py` | tracked | `9032eeb4770d` | 主线历史精确blob；可清副本 |
| `tools/document_understanding_benchmark/phase_c_readonly_source.py` | tracked | `6cf7e52504ae` | 主线历史精确blob；可清副本 |
| `tools/document_understanding_benchmark/phase_c_runner.py` | tracked | `51a1ab36eec0` | 主线历史精确blob；可清副本 |
| `tests/test_phase_c_activation_recovery.py` | untracked | `3998e09ef3a3` | 主线历史精确blob；可清副本 |
| `tests/unit/du11_production/test_business_coverage_relations.py` | untracked | `1ffd71f63f02` | 主线历史精确blob；可清副本 |
| `tests/unit/du11_production/test_native_prose_continuity.py` | untracked | `2a8466e88f57` | 主线历史精确blob；可清副本 |
| `tests/unit/test_changed_resource_scope.py` | untracked | `5b820703bc5c` | 主线历史精确blob；可清副本 |
| `tests/unit/test_source_fact_entity_projection.py` | untracked | `6d677079da30` | 主线历史精确blob；可清副本 |

相关已接收主线提交包括 `ae9a2fbba`（coverage）、`54c4c2f2b`（source facts/recovery）、`ec80b0c56`（scope）、`7a84f47b7`（source-extractive/recovery）等；hash 在历史存在是本次清理证据，后续修改这些文件的提交不能误写成首次引入。

### M3 与 W04 的精确路径边界

M3 已接收的21个源码/测试/CI/工具完整blob：
- tracked：`.github/workflows/ci.yml`；`src/company_wiki/source_catalog/{narrative_budget,narrative_business_groups,narrative_candidates,narrative_evidence,narrative_finalize,narrative_group_candidates}.py`；`tests/unit/{test_ci_push_selection,test_narrative_business_recall}.py`；`tools/changed_unit_tests.py`。
- untracked：`src/company_wiki/source_catalog/{narrative_semantic_coverage,narrative_stage_assertions}.py`；`tests/integration/{test_w04_novelty_finalize,test_w04_quality_band_budget,test_w04_semantic_budget_finalize}.py`；`tests/unit/{test_w04_narrative_semantics,test_w04_novelty_budget,test_w04_selector_version_dispatch,test_w04_semantic_budget,test_w04_stage_predicate_scope,test_w04_stage_public_assertions}.py`。
- 主线 `7a0b702a0` 接收8源/10测试，后有 `4e58e347e` 等修复。可达 blob 保证不是遗漏，不能把旧文件覆盖主线。
- M3 `docs/plans/narrative-evidence-pilot-2026-09-26/{findings,progress,task_plan}.md` 三个post-image也存在主线历史。其余六个 dirty PWF（cross-market根三份及 phase6/main_auto_official_json 三份）未找到精确 blob，属于独有过程记录，保留归档。

**T-CONFIG：四个尚非字节等效的 M3 文件**：
`scripts/config.py`、`scripts/narrative_batch_configured.py`、`tests/unit/test_narrative_model_config.py`、未跟踪 `tests/unit/test_w04_llm_config_scope.py`。旧 `.planning/w04-g2-config/handoff.md` 明确 STOP、四文件共同交付、102项/本机假HTTP为历史记录，未commit。主线 [scoped_llm_configuration_implementation.md](C:/Users/郑曾波/Projects/company-wiki/docs/plans/document-understanding-2026-10-13/review/scoped_llm_configuration_implementation.md) 记同根因、selected-profile修复、真实CLI和最终74项/隔离E2E。旧严格 bool/NaN/max_document_chars 等反例与当前行为是否应一致尚未验证；保留反例给配置owner判断，不能宣称已全覆盖或直接删除独有test。入口为现有 `tests/unit/test_narrative_config_scope.py`、`tests/unit/test_narrative_model_config.py`、`tests/integration/test_narrative_config_scope_e2e.py`。结束于差集反例已移植/明确不属当前契约，旧loader撤销，不增加第二默认值表。

W04 未证明完整blob等效的三文件为 `src/company_wiki/source_catalog/narrative_business_groups.py`、`narrative_evidence.py`、untracked `tests/unit/test_w04_narrative_semantics.py`；`tests/unit/test_narrative_business_recall.py` 与当前master相同。旧 HANDOFF 的 scoped negation 两条失败不是新施工指令，先与主线 stage tests 比对；原报告/失败日志留作历史，不能重标绿。

主工区可选清理补充：`.p3r-g3check-20261111` 的7个untracked路径为测试scratch命名，尚未由本审证实完整目录清理条件；.planning包含真实运行/审计材料，不给 blanket delete 建议。ROOT已核验并删除的 `.p3/.p3r/.p5/.pytest-p3-20261110-r2` 不再列待办。

## 6. 两个 stash

| stash | 精确证据 | 建议 |
|---|---|---|
| `stash@{0}` =5b1415d6e，c3 semantic WIP | 只改 decision_inventory 与 narrative_business_policy。post-image `bc0a0481caf939df3883a4356bcee2e93a835f10`、`14d399feca51b9866862411a12fdad04c30ede9d` 均可达主线；`0da0ca6c1`引入，`74d98a573`后续演进。 | 已等效可退休；drop前用stash SHA而非漂移序号核对。无产品重测。 |
| `stash@{1}` =18ac0d0562，br-ci-fix | 两测试post-image `49003a03ffebad6d0f4d411d6d0ce3b7034e92a6`、`52ec5d81902068cb27970373acc3e30886b32293` 已由`d92f8bf86`接收。另删 .tmp-build-registry.py 及38个 source-catalog-worker-recovery 计划/协议文件；这些路径现master仍存在。另有 llm_cost_log.csv 16行增量，blob未在主线历史，本审未读账内容。 | 测试修复不用再合；39项删除无当前任务理由，不应用。费用差量交原账owner核销/归档前保留stash，不整体pop、不把账目作无用数据删除。测试入口仅历史两contract文件；账务内容不属于本次MB实现。 |

## 7. 接回原 MB 卡的顺序

CWP保持**一个作者**，不因历史分支多就并发修改同一 reader/local_reconcile/config/test 文件。ROOT先完成已证明等效副本/ref/文档核销；原CWP作者按现有A→B→C顺序，在公开来源端口阶段统一处理 T-READ/CANON/B33/B34，在来源材料与配置阶段处理 T-N4/T-CONFIG。每项先登记反例是否仍失败，若已由主线满足则仅核销，不制造空重构。ROOT只在稳定交付后接组合runner。

本轮可关闭：纯精确祖先/补丁等效 refs 的接收疑问、source-facts源码残留、R1伪差量、stash0、W13历史文档缺口。仍未验证：上述旧功能对当前公开契约的行为差集、独有费用日志与约1.3万.planning材料的逐内容去重、实时运行进程/最终删除后状态、任何当前测试结果。未验证项有明确owner和有限关闭条件，不据此保留无限施工或重做已完成P3。
