# 当前交接

**当前唯一执行入口是 [模块边界 M3 计划](../module-boundaries-2026-11-11/task_plan.md)。** M2/E01–E09 只在冻结版本范围内验收完成。GitHub CI #537 通过 SHA `1391ae81`；当前远端 `master@3e7b7231` 还包括其后的 CN 期报登记代码 `707efe814`，因此 CI #537 不是当前远端的 exact-head 证明。CN issuer proof 的重复预算上限已根因修复，62 项受影响契约测试和独审通过；代码与PWF待发布，发布后须验证精确 head。M3 未关闭：FF/RF owner 事项仍在；StockWiki 根计划已于 17:30 UTC 更新并经 ROOT 只读核对。

当前 CWP 另完成一项独立的 push/测试清理修复：四个根级 PWF 文档不会再触发运行时 fixed smoke；pytest 退出时能清理 Windows Git 只读对象，并拒绝对链接/reparse 路径改权限。独审 PASS，57 passed/1 host-dependent skip，cleanup `removed=true`；`56f9cc73d` 已推送并由远端确认，完整 GitHub CI 仍未核验。哈希绑定证据见[独审报告](../module-boundaries-2026-11-11/review/pre-push-classification-and-temp-cleanup-20261115.md)。此项不改变下列 M3 外仓 owner 前置条件。

CWP CI run `43749426185` / job `132919838860` 的回归根因已修复：joined reference predecessor scope、大表 prose-group 错误路由、planned-PDF mock alias、旧 work-budget fixture、paid-response 当前诊断期望。原注释汇总 32 个失败实例。修复提交 `895f66f57ce2346c8eb2102c9bd475a828b3e8c8` 已推送；其完整 CI run `43755195576` 有 4 项失败：新增日常回归未登记到父固定清单；Windows rename 回退测试误在 Linux 执行。follow-up 独立复审 PASS（审查绑定 `895f66f57`，仅覆盖两份 follow-up 代码文件），提交 `1391ae81d8126b5026209e26ae56a7d9bb0a9f0c` 已推送，push smoke 23 passed。GitHub CI #537 / run `43757282611` 已在该精确 SHA 上通过，耗时 7m52s；仅有上游 Node/runner 迁移提示，无失败项。详见[CI根因记录](review/ci-failure-root-cause-20261115.md)。

1. ROOT 将已复审通过的 CWP 共享读取预算根因修复与PWF记录合成一个净提交并推送，然后核验这个最终 head 的 GitHub CI。此前未推送的 512MB 中间提交不单独发布；详细测试与独审见 [CN shared-read-budget review](../module-boundaries-2026-11-11/review/cwp-cn-issuer-read-budget-20261115.md)。注意：GitHub CI #537 只覆盖 `1391ae81`；远端 `3e7b723` 已包含后续产品提交 `707efe814`，不能外推旧 CI。
2. FF owner 为四个下载型 T3 请求补有限 `acquisition_limits` 并在当前主线复跑 T3。FF `main@dd716217` 与本地 tracking ref 一致、tracked-clean；已通过的 S3 BYD E2E 是另一条测试，不能替代此项。
3. RF owner 将 `20261115T084227Z / not-ok`、历史 FF/RF/CWP 三元版本和失败归因写入 canonical PWF，并按 owner 对账 local `main@be0caa4` 相对 tracking `origin/main@f2215959` 超前 9 个提交及三份 tracked assurance 修改（`daily_alert.jsonl`、`weekly_alert.jsonl`、`weekly_manifest.json`）。ROOT 不改 RF；用户确认这些是另一项目的并行进展，原样保留。
4. StockWiki 根 `task_plan.md`/`progress.md` 已在 `5f79e7b`（11-15 17:30 UTC）更新，最新 handoff 于 `master@54f72c9` 更新；ROOT 已只读核对，不再要求重复更新。它无 remote，tracked-clean；不改 StockWiki。
5. 收齐 FF/RF owner 记录后 ROOT 再刷新精确 refs 并出有限 M3 最终报告。只读 status 未枚举外仓 untracked。

不要重复运行已通过的 I10/I11 互操作回放。M3 关闭后才回到本文件所述业务摘要 P1；固定公司循环继续暂停。M2 原始组合记录见 [ROOT 组合记录](../module-boundaries-2026-11-11/review/root_composition_20261114.md)。

R4 统一预扣已迁回执行阶段。已有覆盖缺口时，选材末尾复用已准备的观察并保留部分状态。从正式入口回放冻结半年报，12/12 和选材 SHA 一致，工作账户使用 10,753,620 / 16,000,000。见 [来源会话与覆盖回放](review/r4-source-session-20261114.md)。[T4 与 SEM 验收](review/t4-sem-20261114.md) 已独审通过。

真实 `/5` 来源卡的同 run 与跨 run 恢复、两条 RF 经营假设的实际采用已验收。摘要内容独审要求修正。先用[冻结运行与 RF 结果](review/phase-c-h1-formal-20261114.md)核对问题，避免重复同一排名 POST。用已验证的 support/context 和现有摘要协议做内容根因修复。历史 `/7` 的四个主要改写缺陷是反例。新版本完成后用同原件和跨文种样本核对摘要，保留既有缓存恢复。随后回到 8 家固定公司循环。RF 总览反证条件与分部不一致，归 RF 展示层修复。

## 已发布的前一子节点（历史快照）

截至 2026-11-11 08:25 UTC，先读 `CURRENT_STATUS.md/json`，再按 `task_plan.md` 执行。当前子节点“SourceCatalog 流式读取 + parser owner 接线”已完成、独立审查通过、提交并推送：源码提交 `54f8b470c36a7dd932bfe4ac6ba52ba4edbf01ca`。其后有 PWF-only 收尾提交及状态更正提交，均未改生产代码。工作区跟踪文件干净；其他历史未跟踪产物未纳入本次提交，也未清理。

## 已完成节点

- pathless source-processing descriptor、公开流式读取端口、单一 caller-owned 读取预算、事务式 parser sink 与 parser-owner port 已接入 processed-document endpoint。
- endpoint 不访问 source catalog 私有状态、SQLite、`SourceManifest` 或物理原件路径。失败候选不提交；临时 staging cleanup 失败会保留主错误并留下诊断。
- 定向组合 205 passed/1 skipped；宿主 fast-gate 277/277（59.18 秒）；push hook 固定 smoke 18/18（3.78 秒）；Ruff、mypy 通过。独立审查最终 PASS。详见 `review/p3-public-stream-parser-20261111/README.md`。
- 本次 PWF 状态更正推送后核对 `master` 与 `origin/master` 一致。远端完整 CI 未核验，不应把本地 fast-gate 说成远端完整 CI。

## 前一节点的剩余责任（由新路线图归并）

P3与全局模块边界仍OPEN。旧stream/canonical候选如命中新矩阵的具体缺口，才由对应owner对当前main复现并纳入；其余保留为历史工区核销，不替代或扩展本次有限架构退出标准。R4工作量、T4/SEM、新版真实摘要、真实缓存恢复、RF实际采用与固定公司循环继续沿父计划。

## 交接约束

各 owner 只改自己的实现与状态；跨层只走公开接口。保留原始文件。测试记录中的旧“下一步/待提交”段落是当时的历史快照，当前状态只以本节及 `CURRENT_STATUS.md/json` 为准。

## 2026-11-10 发布历史（后续状态见上文）

源码28e18043ccad06495a0843760ea46c79e0d2222c已推master，CI42914407976于2026-11-10 22:31:23 UTC成功。首轮729a78764的2个身份用例失败和修复过程保留在当前replay报告。R4工作量分诊已经完成，下一步直接使用r4-work-profile.json核对统一预扣与下层计费重叠。

## 2026-11-11 SourceCatalog boundary pre-publication snapshot (historical)

At this checkpoint the SourceCatalog owner-port/static-boundary milestone was locally green but not yet published; it was later pushed at `e7fc2238c177b39dcc91d901a9ac3ac91263830a`. Its then-planned stream/parser node is now completed at the commit recorded at the top of this handoff. Whole-project decoupling remains OPEN.

## 2026-11-11 Commit-hook failure repaired by owner contract

- The first commit-hook run correctly stopped publication. Ruff and mypy found that the PDF version-identity refactor had removed two sibling module aliases while `_pdf_versions()` still read constants through those names; the existing PDF cache-identity regression reproduced the `NameError` (RED).
- Replaced those references with explicit public constants from the owning modules and exported `PDF_PROSE_LAYOUT_FEATURE_VERSION` from `narrative_evidence.__all__`. The same cache-identity regression plus the source_catalog boundary contract pass 7/7; assertion-owner port and cache-identity targeted checks pass 2/2; targeted Ruff passes.
- Ruff also found one unused local in the new assertion owner-port test; removed it. No hook was bypassed. The full commit hooks have not yet been rerun after these repairs.

## 2026-11-11 SourceCatalog boundary milestone local commit snapshot (historical)

SourceCatalog owner ports, package-wide static sibling-boundary contract, fast-CI registration, hook fixes, and corresponding tests were committed locally as `e5dd29b1f` before a later documentation/publication update moved the published mainline to `e7fc2238c177b39dcc91d901a9ac3ac91263830a`. Commit hooks passed Ruff, mypy runtime-source checks, and config doctor. This was the point-in-time status only; the stream/parser implementation is now published as recorded above.

## 2026-11-11 P3 published

The SourceCatalog owner-port and static module-boundary milestone was pushed to `origin/master` at `e7fc2238c177b39dcc91d901a9ac3ac91263830a`. The push fast gate passed its fixed 18-case smoke in 3.88 seconds. The local commit hooks passed Ruff, mypy runtime-source checks, and config doctor. Exact-head remote CI was not verified at that checkpoint. The planned stream/parser node was subsequently implemented and is recorded at the top of this handoff.
