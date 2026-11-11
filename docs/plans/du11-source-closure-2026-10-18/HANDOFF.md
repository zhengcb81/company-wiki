# 当前交接

**当前执行入口：[module-boundaries-2026-11-11](../module-boundaries-2026-11-11/README.md)**，父计划只归总。M0完整规划和A1逐模块Git审查已完成，最新实际接收/清理/余项见 [reconciliation.md](../module-boundaries-2026-11-11/reconciliation.md)。FF与Dashboard有限修复已受测、独审、入main并推送；五张架构卡仍未派发，不把这两次有限接收当作M1/M2完成。

下次从子计划dispatch.md选择更新后的独立卡：CWP/FF/RF/ET/SID各一个作者，先A0再A/B/C；ROOT统管接口、StockWiki C38/B03接收、最终组合与并线。Audit只验证，Dashboard接续原owner。SID11项WIP不能原样接收，RF/CWP旧release不能全树覆盖新main；各自已写精确范围与测试。原R4/真实摘要/缓存/RF循环保留，在模块边界CLOSED后恢复。

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
