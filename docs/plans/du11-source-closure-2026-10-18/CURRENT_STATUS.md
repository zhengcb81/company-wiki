# 当前项目状态与接手入口

更新日期：2026-10-21。**这是本项目 PWF 当前状态、剩余任务和下一步的唯一入口。**

总计划：`document-understanding-2026-10-13`；当前子计划：`du11-source-closure-2026-10-18`，均位于 `docs/plans/`。机器可读状态见 [CURRENT_STATUS.json](CURRENT_STATUS.json)。历史计划、交接、审查和运行收据保留发生时的结论；其中“当前”“Next Step”“待推送”不能覆盖本页。

## 当前执行状态与唯一下一步

**代码实施暂停。** 用户本轮只要求整理文档、审查、提交推送，完成后继续暂停；不启动代码重构、测试实验、模型调用、下载或公司审查循环。

用户恢复实施后的下一主线节点是：**冻结独立新公司样本、来源与检查点，利用已有 C 基线准备并开展 holdout 和 revenue-forecast 审查循环。** 先复用现存证据、核对当前接口；样本必须区别于开发过程中反复调试的 CN/HK/US 三源。B2、类型清零和已接收施工卡均不重新派工；不为 CN 最后两条遗漏继续付费实验。

## 已完成及验收边界

| 事项 | 已完成结果 | 证据及适用范围 |
|---|---|---|
| 共享引擎、阅读策略和 B2 来源闭合 | 已实现并发布；最终代码复审 PASS | [B2 终审](review/b2-antecedent-final-review-20261018-v3.md)。终审当次109项；补充回归后工程记录110项，不能写成一次110项独审 |
| B2 真实来源回放 | CN 10/10、HK 7/7、US 8/8；原件/gold 不变，0 API | [CN 回放](b2-final3-20261018/cn-h1.json)、[HK/US 回放](b2-real-sources-final2-20261018/replay.json)；历史代码 `2a80acf6`，不是新公司 holdout |
| C 普通工程链路 | 三家真实运行有恢复、跨 run 缓存、FF 复用和 RF 读取通过记录 | [已提交的核心收据摘要](receipts/c-live-receipts-20261018.md)及 [JSON](receipts/c-live-receipts-20261018.json)。完整子收据在本机运行树；未对最新类型修复代码重新做真实 C |
| RF/FF DU11 交付与 P1–P4 四包 | 已接收、合入主线并发布 | [历史发布收尾](review/du11-reception-closeout.md)、[10月18日交付快照](review/final-handoff-report-20261018.md)。不代表所有相关仓库的所有分支均已清空 |
| 模型配置单一化 | provider/model/endpoint/key 环境变量名收敛到生产模型表 | [config/models.yaml](../../../config/models.yaml)；使用时读取配置，历史收据不随新模型改写 |
| 类型与代码质量节点 | `mypy src` 335条→366文件0错误；ruff、compileall 通过；单测7033通过/24跳过，相关 contract113通过 | [专项交接](HANDOFF-2026-10-21.md)。这是既有检查结果，本次文档整理未重跑全量套件；全体 contract 并非全部通过 |

### 内容验收采用的口径

用户允许正确近似数字，禁止错误数字；允许 CN 按8/10收尾。该决定不代表其他样本获得完整覆盖验收。

| 样本 | 可引用结论 | 保留的缺口 |
|---|---|---|
| CN | 8/10，critical5/7，按用户决定收尾 | 缺两条完整事实；不记为10/10，不继续为这两条反复付费试验。见[第三轮审查](review/c-content-review-20261018-cn-v3.md) |
| HK | PASS 7/7，critical6/6 | 正确约数被认可；标题式空 claim、重复描述仍是质量瑕疵。逐gold[独立审查已提交](review/c-content-review-hk-20261018.md)，不再列作缺项 |
| US | 所绑定独审为2/8，另1条 partial | 后续汇总2–4/8来自不同实验，不合并为一个最终分数；漏事实问题保留，不能用CN收尾决定代签。见[原审查](review/c-content-review-20261018.md) |

## 剩余任务

| ID | 任务与当前状态 | 后续实施要求 |
|---|---|---|
| R1 主线 | 独立公司 holdout 与 RF 审查循环未启动 | 冻结新样本/检查点；运行完整流程和独立审查，发现共同根因再修复。已有三源只能叫 development regression |
| R2 实验性补写 | `CW_SUMMARY_COVERAGE_REPAIR` 默认关闭，关闭改动已发布；两次 attempt 路径仍有 `activation-resume` / `ReservationConflictError` | 作为独立课题修复或移除；普通单次恢复已通过与此不矛盾。不得默认开启或把它算已验收 |
| R3 证据可复现性 | 核心 C 摘要、HK 报告、B2 回放已在 Git；完整 live 响应/consumer/recovery 子收据仍为本机材料 | R1 准备时核对复现所需材料和代码绑定，补足必要索引/可移植证据；不宣称 fresh clone 已可复验全过程，不提交密钥或整棵临时湖 |
| R4 工程改进候选 | 复杂度基线 C901=292、PLR0912=173、PLR0915=111；lint扩面、大模块、配置解析去重、异常卫生、覆盖率基线未完成 | 详见[专项交接第7节](HANDOFF-2026-10-21.md#7-未完成--下一步路线按性价比)。计数是既有审计基线；按实测收益安排，不自动新增覆盖率阈值或一批阻断门禁，不抢占R1 |
| R5 已知测试债 | 两项旧本地 contract 失败：`test_automation_store_boundary.py`、`test_narrative_transport_cli.py` | 后续在相应环境单独分诊契约与实现；不把113项相关 contract通过说成全体 contract通过，不以删测自动收尾 |
| R6 跨仓及清理边界 | RF/FF自身完整套件未在本机当前组合复跑；旧RF临时目录清理曾被平台拒绝 | 跨仓后续按各自环境及实际变更做大节点验证；旧未清理状态未重新核验，不声称已全清、不换通道重试旧拒绝操作 |

## 代码、发布和 CI 基线

- 文档整理前主线：`44d4e1a4a3e1ce1b95445ceb2519ef020f6f85bc`。2026-10-21已 fetch，`master` 与 `origin/master` 一致；tracked 文件干净，历史 `.planning` 未跟踪材料保留。
- 最后代码提交：`76a9440b9a580889460db0b7b545135060f1ce2d`。公开 Actions API 已核对 [CI 39662983951](https://github.com/zhengcb81/company-wiki/actions/runs/39662983951) 为 `completed/success`，相同完整 SHA。
- RF DU11记录：`9669c4d7` / CI `39095818018`；FF DU11记录：`e8740748` / CI `39095654355`。本次未联网重查这两个仓库，不把历史pin写成它们实时HEAD。
- 后续文档提交不改变上述代码基线；当前 workflow 忽略本轮文档路径，正常 pre-push 仍运行变更选择与既有 smoke。文档提交不要求再追一个不会产生的行为 CI，不递归更新跨仓兼容pin。

## 模型与预算

当前模型表：MiMo `mimo-v2.6-flash`、DeepSeek `deepseek-flash`、MiniMax `MiniMax-M3.1-Flash`。10月18日 US 收据使用的是当时的 `MiniMax-M3`；这属于历史事实，不是当前运行配置。

费用口径采用10月18日 ledger 按 database+attempt_id 去重的快照：56 attempts、1,091,219 tokens / $0.278311，**包含**69,046 tokens / $0.031208 unknown hold，不重复加总，也不当作供应商结算金额。上限仍为累计2,000,000 tokens / $20。以后调用前读实际配置和母账；本轮无新调用、无费用。本页不替代运行账本。

## 文档导航及状态规则

- 本页负责整体当前状态；[task_plan](task_plan.md)负责当前行动和历史阶段，[progress](progress.md)记录过程，[findings](findings.md)记录原因与发现。
- [10月21日专项交接](HANDOFF-2026-10-21.md)保留类型质量节点细节和验证命令；旧 [harness-handoff](review/harness-handoff.md)只作重定向入口。
- [10月18日最终交付MD/JSON](review/final-handoff-report-20261018.md)属于被取代快照；状态以本页/JSON为准，原运行与审查证据不重签、不改写。
- 后续完成节点时先更新本页/JSON及当前 `Next Step`，再追加过程；旧正文置于历史区，不再把旧任务标作当前。独立质量审查放在大节点结束，发现问题修完后交接，不添加小节点许可。
- 本轮文档一致性独立复核见[审查记录](review/status-consolidation-review-20261021.md)及[绑定SHA的JSON](review/status-consolidation-review-20261021.json)。提交/推送结果由本轮Git记录确认，不替换历史代码CI。
