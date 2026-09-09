# revenue-forecast 旧 data-lake ADR 全文审计

审计日期：2026-09-05  
审计范围：`revenue-forecast/audit_review/2026-08-09_data_lake_refactor_plan/adr/` 下 WU-201～WU-205 五份 ADR。  
操作边界：只读 `revenue-forecast`；本文件是 `company-wiki` 当前 planning 同步审计的旁路记录，不回写、解冻或改写历史 ADR。

## 覆盖与完整性

以下五份文件均已按 UTF-8 **全文读取至 EOF**，不是标题扫描、关键词抽样或截断摘要。行数为 `Get-Content` 返回的物理内容行（文件末尾换行不另算空白行）；SHA-256 按原始文件字节计算。

| 文件 | 字节 | 行数 | SHA-256 | 读取结果 |
|---|---:|---:|---|---|
| `WU-201-architecture.md` | 3455 | 48 | `bc6a583f10328b6ce6ed14639bfdf7885452ed6e58512c7c39e0e5b2971c39d2` | 全文至 EOF |
| `WU-202-normalized-metadata.md` | 1604 | 35 | `da91864e5026a167485439005bdf9a0ef1a47f3b97b10869ca4d3e1e4b3c8551` | 全文至 EOF |
| `WU-203-reuse-latest.md` | 1209 | 19 | `3e6bac750eb08f832a7448d52a9bcfda8eaa7162f4b506038dac4255e473ae98` | 全文至 EOF |
| `WU-204-bundle-dag.md` | 1118 | 33 | `38c707ddda35456c5b317bbf0fb2d5055f5e09ad05d77baaa5b52790e27c3463` | 全文至 EOF |
| `WU-205-blueprint.md` | 1435 | 29 | `d351cec83dad21b9cb0a0f471b5a83b37ce981501eac443d9501b3900e557d58` | 全文至 EOF |

## 文档性质

五份文件都自述为 `2.1-full-refactor-execution-cards` 的 `contract_frozen` ADR，是 2026-08-09 data-lake 重构计划包的历史规范证据。它们定义的是职责边界、元数据契约、复用/latest 状态机、artifact DAG 和架构 fitness functions；其中测试命令后的 passed 数只代表该历史包当时记录的局部契约测试，不是 2026-09-05 对现有三仓代码、生产任务或 worker 的重新验证。

> 当前处理原则：保持原文件字节不变。后续实现或主线计划只能引用、显式继承或以新 ADR 正式取代这些约束，不能靠修改历史 ADR 抹平漂移。

## 当前一致性判断

### 1. 历史文件冻结与契约验收不是一回事

该包的 `TERMINAL_NOTICE.json` 将整个计划标为 `closed_superseded_incomplete`，并指向后继 `assurance/unified_completion/state.json`；所以这五份 ADR 应作为**冻结历史规范**保留，不能作为今日可领取的 WU 或现状证明。

同时，旧包内部存在明确的验收链缺口：

- 五份 ADR 页眉/标题把状态写成 `contract_frozen`；
- `task_plan.md` 的 Phase 2 仍为 `pending`，其放行门要求三仓 owner 和独立 reviewer 签字；
- `receipts/WU-202.json`～`WU-205.json` 的 reviewer 都是 `pending`，状态仍为 `pending independent review` 或 `pending review`，`admission_decision` 也均为 `pending`；
- 同包不存在 `receipts/WU-201.json`；
- WU-205 回执列出的 architecture tool 实跑参数只包含 company-wiki 与 revenue，不能替代“三仓 owner + 独立 reviewer”放行门。

因此，应使用两个不同表述：文件字节因历史封存而冻结；但该旧包自身没有形成足以证明“Phase 2 契约正式 accepted”的完整证据链。不得把 ADR 自述状态或局部 `passed` 注释升级成正式验收结论。

### 2. 与当前职责边界没有发现规范性正面冲突

- WU-201 的 company-wiki 上游来源/catalog 所有权、filing-fetch reuse-first、revenue source-preparation 与纯计算分离，和当前三仓状态入口所描述的职责方向一致。
- WU-202 的来源身份、hash、逐字段 evidence、fail-closed，以及把 root/path 等非语义位置属性留在 location/source 层，与 company-wiki 当前 SourceRecord/EvidenceSpan/immutable provenance 边界同向。
- WU-203 的 exact 不擅自 discovery/download、latest 只补 gap、外部 root 只读、下载需绑定授权，与当前 filing-fetch reuse-only/显式授权边界同向。
- WU-204/205 的 artifact 输入绑定、stale/unknown fail-closed、跨仓只走版本化 contract、calculator 不做 I/O，也未与当前状态页出现正面冲突。
- 当前 company-wiki worker v5 是独立的性能/恢复规划，仍为 `V5_BASELINE_READY / VERSION_CONTRACT_PENDING / NOT_IMPLEMENTATION_AUTHORIZED`；它强调单线程、source/artifact 绑定、只读保护与分阶段独立审查，没有证据表明已经正式取代上述 ADR。

这里的“一致”只表示**规范方向未见冲突**，不表示模块、schema、CLI、生产调度或三仓 E2E 已按 ADR 全部实现。旧 `release_manifest.json` 当时仍把所有 v2 feature flag 设为 false；当前 GP-006/008/009/010 又存在真实 roots CI、任务 Action、自然观察窗口和生产 sections 等开放项。它们主要是实现/运行证据不足，不是推翻这五份 ADR 的新架构裁决。

### 3. 当前需要覆盖的过时含义

- 不得从 WU-201～205 或旧 task_plan 的 pending 状态重开 74-WU 队列；当前入口应先看三仓 `PLANNING_STATUS.md`、后继统一机器账本与 remaining-gap-closure GP 组。
- ADR 内 `14 passed`、`11 passed` 等是历史参考工具的局部测试记录，本次未重跑，不能证明 2026-09-05 当前代码或生产环境仍通过。
- 未来计划若要继续采用这些约束，应显式写“继承的规范条款 + 当前实现证据 + 未满足项”；若要改变任一职责边界、metadata 字段、exact/latest 状态机、artifact DAG 或 fitness function，必须新建带版本/hash 的 successor ADR，而不是编辑这五份历史文件。
- 旧包未被当前 44 项 `plan_inputs.json` 以这五个 ADR 路径逐文件收录；不能借“后继账本已完成”反推旧 ADR 的独立 reviewer 缺口自动补齐。

## 独立 agent 审查要求

本报告是一次独立只读补审，但不能自我批准其写入后的最终文本。合并当前 planning 同步结果前，应由**另一名未参与本文件编写的 agent**执行关键节点复核，并留下明确 verdict：

1. 重新按原始字节计算五个 SHA-256，核对文件大小、行数和 EOF 覆盖；发现并发变化即停止，不沿用本表。
2. 核对 `TERMINAL_NOTICE.json`、旧 task_plan Phase 2 放行门、WU-202～205 receipts 以及 WU-201 receipt 缺失，确认没有把“历史文件冻结”误写成“契约 accepted”。
3. 对照三仓当前 `PLANNING_STATUS.md` 和活动 GP/v5 入口，检查本报告没有复活旧 WU、没有把历史测试外推为当前/生产通过，也没有把实现缺口误判为新架构裁决。
4. 核对 Git diff：`revenue-forecast` 不得因本补审发生任何修改；company-wiki 本任务只应新增本报告，且不得触碰 v5 baseline/import/review、现有主线计划或其他线程文件。
5. 输出 `PASS`、`CHANGES_REQUIRED` 或 `BLOCKED`，逐条列证据。只有 `PASS` 才可把本项计入全局“规划文档已完整审阅”的覆盖结论；`PASS` 仍不构成产品实现、worker 恢复、生产部署或旧 ADR 正式追认。

未来实施这些 ADR 的任一关键节点时，还应沿用用户要求的阶段性独立 agent gate：设计/RED、实现、focused/repo/cross-repo 验证、迁移/切流、rollback/删除分别由与实施者不同的 agent 审查；跨仓契约变化需三仓 owner 范围复核，不能用单仓测试或同一 agent 的自证替代。

## 审计方法与限制

- 本次仅做本地只读文本、hash 与现有状态证据交叉核对；未运行 ADR 所列 pytest/architecture 命令，未扫描生产 root、未查询外部 provider、未启动 worker、未写 catalog/配置/任务。
- 首次 PowerShell 元数据命令因 `foreach` 后直接接管道触发 `empty pipe element` ParserError；该调用无写入。随后改为先累计 `$rows` 再格式化，成功取得表中数据，没有重复原失败方式。
- “当前无规范性正面冲突”不是全代码结构审计结论；若进入实施，应在固定 revision 上重新运行 architecture/contract tests 与 CodeGraph/AST 边界检查，并由独立 agent 复核结果。
