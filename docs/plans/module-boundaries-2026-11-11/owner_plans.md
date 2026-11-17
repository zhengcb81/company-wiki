# 各模块计划入口与交接

2026-11-17 工程反馈子计划已在各仓落地，当前可分发的三张独立卡及总控写范围见[反馈分工表](../feedback-loop-2026-11-17/dispatch.md)。下表为 11 月 16 日 M3 时点的在途业务和版本记录。

2026-11-16。表中入口相对于各自仓库根目录。Git 版本为本轮本机只读观察，`origin/*` 列出已知跟踪引用。历史组合仍按原收据版本证明。各 owner 维护本仓 PWF、实现和发布，ROOT 维护跨仓接口及组合记录。

## 当前生产链

| 模块 | 本仓计划入口与版本 | 谁负责什么 | 当前交接与下一步 |
|---|---|---|---|
| company-wiki | 父计划 `docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.md`，边界子计划 [task_plan.md](task_plan.md)。本轮代码为 `12e65fe7d` | 自有原件、版本、位置、来源验真和阅读摘要。对外提供 CLI/DTO | 请求隔离、目录投影与 PDF 适配器已通过定向测试和独审。证据见 [浏览边界验收](review/cwp-browse-owners-20261116.md)。FF 的调用方预算由 FF 接续 |
| filing-fetch | `PLANNING_STATUS.md`，`main@4c7f501b` 与远端一致 | 自有请求、复用/补齐编排和 job，调用 CWP 的公开来源与三表入口 | 正式 T3 四项通过，含三市场下载及复用和损坏件。Dashboard 候选信封交接单列 |
| revenue-forecast | `PLANNING_STATUS.md`，本地 `main@be0caa4b`，远端 `main@220e5441` | 自有经营模型、作业、计算与报告目录，通过 FF/CWP 的公开接口取资料 | `20261115T084227Z / not-ok` 和实际三仓版本已在远端 PWF 登记，同 SHA CI 通过。本地相对共同基线的九个提交及三份 assurance 跟踪改动留给现有并行项目后续同步 |
| StockWiki | `master@b4ca912`，当前入口为 `.planning/` 下 `2026-11-14-company-assessment-lineage-v2`、`2026-11-14-dashboard-owner-improvements` 和 `modularity-closeout-20261111`；研究交接 `54f72c9`，无 remote | 自有研究主体、公司池、身份公开证明和研究状态，以 CWP SourceRef、索引和资料 DTO 取证 | 药明康德已有三条关联，阿里和 MDB 的来源关联与发行人绑定由 owner 接续。根 `task_plan.md` 的最新提交是 11-08 的 `9baaf3d`，根进度和发现分别是 `b6511fa`、`780d495`。以当前子计划判断在途工作 |
| earnings-transcripts | **`earnings-transcripts/earnings-transcripts`** 内的 `task_plan.md`，`main@50d9190` 与 tracking 一致 | 自有电话会获取、原语言 TXT 和 provider 预算，CWP 负责登记 | MB-ET 有交付证据。ET owner 下一步修 `transcript_audit.py --write-receipts` 的冲突退出码，让已经存在的冲突状态按 CLI 合同报告 |
| StockInfoDLSimple | **`StockInfoDLSimple/v2-clean-rewrite`** 内的 `docs/plans/mb11-sid-2026-11-11/task_plan.md`，`v2-clean-rewrite@fb8c8ba5` 与远端一致 | 自有 CN provider、暂存与稳定错误，按公开合同交给 CWP | CNINFO 证券代码输出已通过独审，正式 FF A 股下载复用通过 |
| invest-quick-scan | `task_plan.md`，`master@3d9243c` 与 tracking 一致。活动 `codex/iqs-manifest-delivery-01@8d0888a` 有一份计划及两份 Dashboard 投影测试改动 | 自有筛选编排与 Dashboard 投影，经过 StockWiki 的版本化 membership/assessment 接口 | 11-16 本仓已启动九模块对账。owner 交付记录 35/36，混尺度 V2 进入 Dashboard 投影和 IQS_22 恢复归活动计划；I1–I7 历史通过保留 |
| investment-dashboard | `.planning/unified-dashboard-2026-10-26/START_HERE.md` 及 `DELIVERY_STATUS.md`。本机 `main@93b6357`，比 `origin/main@3f83bb5` 多 2 个文档提交，FF owner 交接文件有跟踪改动 | 自有 UI、用户交互状态和外仓适配器。issuer proof、原件、三表、研究和 job 状态均通过 owner CLI/DTO 获取 | 由 Dashboard owner 对齐 B-04、保留 FF 补充实测并验证 IQS mixed-rubric V2 的投影兼容。其用户整链和部署证据在 Dashboard 计划管理 |
| revenue-forecast-audit | `docs/plans/company-pool-cycle-2026-10-09/task_plan.md`，`main@50d8ab6`，本地无 remote | 自有运行与独立审查记录，消费各 owner 的公开命令和收据 | 运行时接收按现有收据保留，固定公司循环仍暂停。待业务前置后从现有 NVDA 线接续 |

## 外部依赖与独立消费链

| 模块 | 本仓证据入口 | 可单独推进的职责 |
|---|---|---|
| StockQAbyLLM | `task_plan.md` 与 `.planning/modularity-closeout-20261111/task_plan.md`。`master@9ffd566` 与 tracking 一致，活动 `codex/qa-content-filter-resolution-01@14f1a1c` 有跟踪修改 | 自有模型调用、付费结果和逐题状态。当前活动分支由本仓 owner 收口并为 IQS 提供稳定结果 DTO |
| industry-research | `.planning/modularity-closeout-20261111/task_plan.md`，`main@c7a04ed` 与 tracking 一致 | MC-IN 固定组合 I5 已完成，继续本仓业务研究，维持只读消费 StockWiki 快扫公开事实 |
| MeetingConverter | `task_plan.md` 与提交 `6c857a8` 的并线记录，`master` 与 tracking 一致，现场 `.coverage` 有变化 | 自有会议转录和产物完整性。对应历史施工已并线，独立演进自己的输出合同 |
| Dayu | `dayu-agent/dayu-agent` 外部 provider checkout | CWP 在自己的 adapter 上消化外部 provider 行为。Dayu 由外部维护 |

## 需要组合的交接

- **FF → CWP，有限下载。** FF 持有请求预算，CWP 负责下载、入库和验真。三市场真下载、零重复复用及损坏件拒读已验收。RF 旧周跑按实际失败及版本登记。 [M3 正式验收](review/m3-formal-t3-20261116.md)
- **StockWiki → IQS → Dashboard，跨尺度展示。** StockWiki 保存真实分组及来源归属。IQS owner 的交接确认 36 题含两套评分尺度，单一 `scale_version` 无法表达；Dashboard 的 `_map_company_result()` 当前会将缺单值尺度的结果降为 `lineage_unknown`。接续各 owner 已有计划，用同一份 producer 样例对照单尺度和混尺度。投影展示真实的尺度列表和组别证据，各组的比较继续按组处理。需要改公开协议时由 IQS 和 Dashboard owner 在现有协议分支协调兼容，业务完成度从实际题目发表状态读取。
- **CWP 原件、ET 及 SID。** ET 和 SID 只在各自 provider 构成原始数据和有界结果，CWP 通过 adapter 验真、登记和复用。ET 收据写入冲突由其 CLI 合同覆盖；SID 最新期次由其 provider 测试覆盖，组合只验证公开结果和已用预算。

当前 M3 的证据、接受范围与历史版本见 [boundary_matrix.json](boundary_matrix.json)。PWF 和 Git 状态、活动工区的处置见 [模块收尾计划](../module-pwf-reconciliation-2026-11-14/task_plan.md)。
