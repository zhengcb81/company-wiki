# 当前交接

截至 2026-11-11 08:25 UTC，先读 `CURRENT_STATUS.md/json`，再按 `task_plan.md` 执行。当前子节点“SourceCatalog 流式读取 + parser owner 接线”已完成、独立审查通过、提交并推送：`54f8b470c36a7dd932bfe4ac6ba52ba4edbf01ca`。工作区跟踪文件干净；其他历史未跟踪产物未纳入本次提交，也未清理。

## 已完成节点

- pathless source-processing descriptor、公开流式读取端口、单一 caller-owned 读取预算、事务式 parser sink 与 parser-owner port 已接入 processed-document endpoint。
- endpoint 不访问 source catalog 私有状态、SQLite、`SourceManifest` 或物理原件路径。失败候选不提交；临时 staging cleanup 失败会保留主错误并留下诊断。
- 定向组合 205 passed/1 skipped；宿主 fast-gate 277/277（59.18 秒）；push hook 固定 smoke 18/18（3.78 秒）；Ruff、mypy 通过。独立审查最终 PASS。详见 `review/p3-public-stream-parser-20261111/README.md`。
- `master` 与 `origin/master` 都是 `54f8b470c36a7dd932bfe4ac6ba52ba4edbf01ca`。本次未核验远端完整 CI，不应把本地 fast-gate 说成远端完整 CI。

## 下次恢复时

用户要求当前子节点完成后暂停，故现在不继续开下一节点。恢复后先把历史 stream/canonical 候选声明与当前主线逐条对照并重放，只对能在当前 main 复现的问题决定迁移；之后继续其他模块及跨仓 owner 边界。P3、全局模块化/解耦仍 OPEN。随后按父计划处理 R4 工作量归属、T4/SEM 真实验收、新版真实摘要、缓存恢复、RF 实际采用和固定公司审查循环，不把本地接口测试当成业务验收。

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
