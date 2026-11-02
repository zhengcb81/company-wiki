# 来源观察工具关键节点独审

结论：**NEEDS_ROOT_FIX_ATOMIC_FIRST_PUBLICATION**。新有界检查 **8 项：1 failed /7 passed，2.23 秒**，发现一个原子首次发布的 P2。当前不签观察工具发布或再次真实 H1；旧 v3 无 durable 收据的失败仍保持未验收，不能补造通过。

审查人 `/root/rectification_review_a`，2026-11-02；范围为 ROOT 主工区新增 5 文件及 CI/pre-commit 两文件，开始/结束 7 SHA 一致。5 文件精确绑定 `.planning/architecture-quality-20261101/r6-publication/source-observer-final-tests.json`；每文件 SHA、原始 JUnit 与复现源见同名 JSON。未修改代码、原测试、Git 或主 PWF。

## P2：首次写入的所有权检查与实际提交之间可覆盖他方结果

`tools/source_case_runner.py::atomic_owned_write` 在开头做 `path.exists()`/owned hash 检查，之后写 pending、flush/fsync，再无条件 `os.replace(pending, path)`。它保证写入原子性，却没有保证首次提交“不覆盖已出现的他方结果”。

独立最小 RED：目标初始 absent；在 pending fsync 后模拟独立 writer 创建目标，内容 `foreign-winner`；工具没有抛 FileExistsError，而将文件覆盖成 `own-result` 并认领所有权。现有“foreign 文件事先存在”测试没有覆盖 check→commit 窗口。

应在**首次发布**使用原子 no-clobber/不存在才提交的原语；已有本轮 owned 文件的替换仍保持原子性和失败保留旧 checkpoint。无需人工许可、ACL 修改或原件重放。不可仅增加一次普通 exists 检查，那会留下同类竞态。演示仅触及 self-owned 观察文件，不涉及生产原件、DB 或真实 H1。

精确 probe：`test_atomic_first_publication_does_not_overwrite_a_foreign_file_created_after_preflight`。原始完整脚本/SHA 已嵌入 JSON；ROOT 可直接据此固化真正发布阶段的反控。

## 通过的限定证据

- 多字节大重复 span 压缩在 300k 内，required/context/view 证据和 producer 的 False/partial 状态保持，UTF-8 长度/SHA 正确，结果确定、输入未改。
- 必需多字节 excerpt 超限明确 OBSERVATION_INCOMPLETE，source_status 不升级，字段列为 unretained；不保一段截断正文冒充完整 excerpt。
- 必需字段含不可 JSON 对象时，不调用其 `repr/str` 或暴露 body，incomplete 保留 source_status 与 False integrity 状态。
- 真正独立新子进程运行 canonical `-m tools.source_case_runner`，只给不存在的合成 config；核对 receipt 中三个工具的真实 ROOT SHA，返回 FAILED，after proof 为未知，没有 source/模型/下载。
- 选取三条原必要控制：编码器异常保 RESULT_READY＋incomplete，parent 超时不覆盖已有完整结果，已有 owned 文件 replace 失败保旧 checkpoint。未重跑原 29 例。

## 架构和字段边界

工具为 manifest 驱动，单次 fresh child/SourceVersionReader/handler，不含公司/市场样本硬码，不采集、不跑模型或 AUTO writer。原 context checker 的 no-match/missing-lineage 保持 OPEN，不把“没发现旧错配”当新主体归属证明。DB/WAL/原件严格前后对比，SHM 仅 byte/existence 不变时允许 mtime。

编码层保强制索引/摘录或明确 incomplete，表示 complete/compacted 不改变来源处理状态；trace omission 有身份与状态。四阶段 checkpoint 与三工具 code before/after identity 保持。此次问题是首次写入的原子所有权边界，不是取消 300k 或再读真实源。

CI/pre-commit 仅在既有 Ruff 范围加入三个工具路径，没有新增 job/test 阶段。旧 ignored 入口只是 canonical CLI 的薄兼容 shim。

## 复现保全与处置

唯一 owned `C:/Users/郑曾波/Projects/company-wiki/tmp/o3` 初态 absent；完整源码/hash/JUnit 已在报告。ROOT 已实际读取最小 RED 并确认不依赖临时路径，随后仅清理该准确目录并补恢复收据；不操作其他历史未跟踪产物。

ROOT 已确认 P2 并解冻返修。它另指出固定 9 个原始 target 即使未被 selector 选中，也须保留既有 structure 的 parent/required-context 观察；当前 view-only 摘录不足以判定这部分归属。ROOT 将补纯投影与未选 target/缺失父节点/循环父链反控，不重复 source 或模型。本 R1 不把这份尚未实施的能力写成已验收；当前 SHA 只绑定原测试窗口。失败历史另存 `R6-source-observer-independent-r1.md/json`，不回写为修复后通过。

已将 P2 和最小证伪交 ROOT 同 owner 直接修复。当前 **STOP**，不扩大检查，不读取真实原件/模型，不签 source、缓存、RF 或总目标完成。
