# 当前交接

**当前执行入口为 [主线实施计划](task_plan.md) 的业务摘要内容。** 五条模块交付及 M2 组合已验收完成。StockWiki C38/B03 与 Dashboard 通过公开接口接入，验收版本见 [ROOT 组合记录](../module-boundaries-2026-11-11/review/root_composition_20261114.md)。

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
