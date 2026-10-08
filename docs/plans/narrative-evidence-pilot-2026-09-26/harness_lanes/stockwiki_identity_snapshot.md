# StockWiki 独占施工卡：身份快照与四态映射（W02/W03）

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> **状态：W02/W03 实现和真实 serializer golden 已并入 StockWiki `master@c8cfb2e7`。**本文件是已完成实施记录，不要重复派发。它不等于 G2b 通过：IQS handoff 仍要求 owner identity receipt 与 market-registry 投影。后续 producer 工作见[W04 独立施工卡](stockwiki_g2b_owner_context.md)；不得伪造这些记录。

> 这条 W02/W03 线已经结束。W04 施工卡独占 StockWiki 写入范围；IQS、company-wiki、filing-fetch、revenue-forecast、earnings-transcripts 仍为只读依赖。

## 任务目标

实现 StockWiki 身份库的真实、可复现快照输出，以及下游可消费的四态 issuer/security/listing 映射 DTO。StockWiki 是身份库和名单的唯一生产写入者；IQS 提供 schema/参考校验器与公开 JSON CLI。身份映射只表达精确映射尝试的结果，不生成投资结论，也不改变已有 accepted/rejected 研究状态。

**唯一范围：**W02 身份快照 producer + W03 四态 mapping DTO。不要实现 SourceExport reader、selected evidence、full sync/weekly、生产批量回填或其他仓库的消费者。

## 派发时的已知状态和开始条件

- 2026-09-29 复核时，StockWiki `master` 为 `dd8912f` 且工作树干净；engineering gate simplification 已合入并通过审查。
- 已完成的 SourceExport reader 位于单独的干净 worktree `StockWiki-v2-reader`，HEAD `0b40683`，尚未成为 `master` 的祖先。不要改写、reset、合并或 cherry-pick 该 worktree；本任务从派发时的 StockWiki 当前主线创建另一独立 worktree。开工前确认 reader owner 已停写；若仍在写，先错开时间。
- IQS 施工卡第 1–4 步已由用户报告收尾；第 5 步 G2b 等本线的真实身份 DTO/golden。开工时仍只读核对 IQS 收尾报告、稳定的 identity package/schema `2.2.0`（Entity `2.1.0`、AnalysisSubject `1.0.0`）及公开 CLI 版本，不得写 IQS。若跨仓工具与合同确实可用，本线生成 producer golden 后即可交 IQS 做 G2b；若报告或 CLI 不可复现，记录具体阻塞并保持 pending，不伪称通过，也不要求重做已完成的本仓步骤。
- 开工重新记录 StockWiki HEAD、分支、tracked/untracked 状态和本仓 PWF；保留所有已有活动文件，不使用 `reset --hard` 或通配符清理。

## DTO 语义（必须固定并测试）

身份快照遵循已发布的 identity package 2.2.0：Entity 2.1.0 与 AnalysisSubject 1.0.0 分层表达 issuer、security、listing；按本仓真实身份数据库/serializer 生成，不手工伪造“成功 golden”。DTO 至少携带 schema/package version、稳定身份 ID、证券与上市地精确标识、as-of 语义、来源绑定和具名错误信息。不得带 `companies/`、dayu、Dropbox 等物理根路径、文件路径 hash、凭证或投资结论。

映射状态采用如下四态：

| `mapping_status` | 精确含义 | 允许输出 |
|---|---|---|
| JSON `null` | 尚未尝试映射 | 不得解释成未找到 |
| `unknown` | 已按请求中的精确证券/上市地/as-of 查询，结果为零候选 | 记录已尝试的查询身份与期间 |
| `ambiguous` | 精确查询得到多个候选 | 返回候选身份；不得自动合并或选第一个 |
| `mapped` | 唯一候选且 issuer、security、listing、as-of 和来源绑定全部一致 | 返回完整精确绑定 |

错误证券、市场/交易所、listing、期间或来源绑定必须返回稳定的具名失败，不得降级为 `unknown` 或 `mapped`。不允许用 truthiness/隐式 coercion 合并 JSON `null`、空字符串和 `unknown`。

## TDD 实施顺序

1. **基线与边界：**只读调查本仓真实身份表、serializer、W01 数据模型和现有测试。列出实现路径后先写测试；不得复用物理路径作为身份 key。测试数据库必须位于本仓独立临时根。
2. **W02 producer RED → 实现：**覆盖 issuer/security/listing 分层、AnalysisSubject 绑定、稳定排序/序列化、schema version、as-of、非法/缺失字段、重复身份和来源绑定失败。用当前 StockWiki serializer 从隔离测试数据库生成正例 golden，再验证它可重复生成相同规范 JSON/hash。
3. **W03 四态 RED → 实现：**对 `null/unknown/ambiguous/mapped` 各写正例；覆盖错误证券/上市地、错期/as-of、重复候选、候选集顺序变化、伪造 mapped、把未尝试写成 unknown 等负例。定义版本化 DTO；不要把四态冒充 identity package 2.2.0 已包含字段。
4. **跨仓合同：**若 IQS owner 已交付稳定公开 schema/CLI，使用该 CLI 对真实 StockWiki serializer golden 做成功与畸形输入校验，并记录 CLI 版本/退出码。若未交付，只运行本仓合同测试并把 G2b 标记 pending；不得导入 IQS 私有 Python 模块，也不得复制其未提交代码来绕过依赖。
5. **大节点验收：**开发期间跑受影响测试；W02/W03 一起完成后运行本仓 `scripts/check_all.sh` 一次。确认全部新增合同测试无 skip，StockWiki 生产数据库/身份状态无变化，唯一临时根已删除或恢复到原状态。

## 路径隔离与明确排除

- 只写 StockWiki 专用 worktree 中与身份 producer / mapping DTO / 对应测试 / 本仓 PWF 直接相关的文件。
- 不修改 `AGENTS.md`、`scripts/check_all.sh`、`tests/test_check_all_script.py`（engineering gate 已完成）；不修改 SourceExport reader 或其测试；不访问 IQS 的写入面。
- 不迁移、重命名或批量修复生产身份数据。若现有生产记录不能生成无损快照，先新增可复现失败测试并报告具体例子，不做隐式修复。
- 本线生成文件、数据库、日志与缓存都必须留在本仓测试临时根；测试前后生产根不变。

## 自动验收与交接

通过条件：真实 StockWiki serializer 可重复生成 identity snapshot golden；package/schema 版本精确；四态语义和全部负例通过；本仓完整检查通过；测试无 skip、临时根恢复；生产身份表和研究状态无改动。IQS 尚无稳定 CLI 时，仅跨仓校验保持 pending，不阻塞本仓 producer 交付。

交接只需报告：StockWiki base/branch/commit、改动路径、snapshot/package 与 mapping DTO 版本、由真实 serializer 生成的 golden 路径/SHA、测试命令/退出结果、隔离根前后状态、IQS CLI 是否稳定以及 G2b 是否仍 pending。总指挥只读核验并安排 IQS/G2b 汇合；不要求额外人工签收文件。
