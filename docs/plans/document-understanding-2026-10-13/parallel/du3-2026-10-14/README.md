# DU3 三条独立施工线 — 2026-10-14

ROOT继续主线Phase A：source_catalog候选/预算/最终选择、DU orchestration/selection_bridge/summary_input；随后正式AUTO接线。以下三线只交付各自排他模块与测试，现在可开始，不等待ROOT实现或彼此交付。

| 卡 | 独立工作目录（同CWP的不同稀疏worktree） | 排他代码目录 |
|---|---|---|
| [DU3-QUALITY](cards/DU3-QUALITY.md)：跨市场真实文档质量基准与泛化 | `C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/quality` | `tools/document_understanding_benchmark/` |
| [DU3-DEPENDENCIES](cards/DU3-DEPENDENCIES.md)：选择决策依赖与局部失效 | `C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/dependencies` | `src/company_wiki/document_understanding/decision_dependencies/` |
| [DU3-GEOMETRY](cards/DU3-GEOMETRY.md)：真实版面快照与原文单元绑定 | `C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/geometry` | `src/company_wiki/document_normalization/layout_snapshots/` |

每卡另拥有自己的tests/fixtures和`.planning/du3-<lane>/`，详卡。ROOT独占母PWF、共享接口、已有profiles/structure/layout_hints/生产adapter/存储/AUTO。三worker不在主仓或别的worker目录改文件；不修改pyproject、依赖、hook/CI、生产配置或安装技能。

共同技术接口：[INTERFACES.md](INTERFACES.md)；ROOT [统一PWF](../../task_plan.md) / [施工细则](../../completion_implementation.md)。接口是数据约定，不是许可或签收链。每卡先TDD，再A/B/C三个大节点；worker交本分支，ROOT验收接线/并master/推主线，不能自己改生产默认。

目录创建时不复制companies/数据湖、数据库、整篇MD或作者bindings；本机原件使用未提交的只读绑定。代码worktree共享Git对象。各自base/branch记录在工作树`.planning/du3-<lane>/task_plan.md`，恢复时以那份为准。

ROOT接收顺序：DEPENDENCIES→GEOMETRY→QUALITY（只是最终接线次序，三线可同时施工）。纯组件/基准通过不等于生产已接线或真实摘要已通过；ROOT集中接线和母G2/G4/G5窗口验证，不给每个helper增审查。

## 已准备的启动基线

三工作树已实际创建，共同base `195aba20b0aecc2d661d7d04c5ba72f982bc02d0`；各自约15.52MB，合计约46.56MB，只检出代码/测试/相关文档，没有companies/原件/数据库复制。三份独立PWF已放各自`.planning/du3-<lane>/`。清单见[worktrees.json](worktrees.json)，当前READY_NOT_STARTED。
