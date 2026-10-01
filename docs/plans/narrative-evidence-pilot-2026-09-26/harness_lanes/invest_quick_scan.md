# IQS 独占施工卡：身份包与工程签收简化

> **交给已在运行的 invest-quick-scan 项目 owner，勿另开同仓写入线。**唯一写入目录：`C:\Users\郑曾波\Projects\invest-quick-scan` 的指定集成 worktree；StockWiki/CWP/RF/FF/ET 均只读。IQS 负责自己的 issuer/security/listing 与 AnalysisSubject 合同，不读取或管理 CWP 原始财报，也不写 StockWiki 研究状态。

> **2026-10-01 当前状态：**IQS `master@56ff421` 已提交三份 PWF 盘点；当前 V02/scoring 的四个未跟踪路径由 owner 管理，本总控不提交或覆盖。IQS 仓内施工卡步骤 1–4 已完成；provisional Entity 与四态 mapping golden 经 public CLI 正反验证，最新复验的 StockWiki→IQS 聚焦包为 113 passed。完整 G2b 仍 partial：verified/multi-listing/AnalysisSubject 与有效期历史等 owner 真实样例未齐，W01–W03 的完整生产入口/名单扫描接线也未关闭。QA-04 行为回归通过但交付 handoff 仍 partial；DWA-03/04/05/06 有审计跟进。只由现有 IQS owner 收尾，不派第二个 IQS 写入 harness。下方 2026-09-29 状态段是当时交接快照。

**2026-09-29 交接增量：**用户报告 IQS 施工卡的仓内步骤 1–4 已收尾并写入收尾报告；第 5 步 G2b 只等 StockWiki 提供真实身份 DTO/golden。此状态尚未由本仓只读核对 IQS 收尾报告，因此跨仓验收时仍需核实其 commit、公开 CLI/schema 版本与报告路径。不得要求 IQS 重做步骤 1–4，也不得新开同仓写入 harness；StockWiki W02/W03 是当前唯一 producer 前置，须由真实身份数据库/serializer 产生 golden，不能伪造。IQS 收到 golden 后只执行第 5 步的真实跨仓验证，包含成功 golden 和身份/期间/来源绑定反例；G2b 在此之前保持 pending。StockWiki W01 本地 `master@5bb68f6` 已独立验收（QuickScanStore 18/18、定向 Ruff 通过），不要为旧递归 receipt 阻断该工程结果。CWP 基础 SourceRef/SourceExport golden 在独立代码分支 `822a43a`，身份合同只引用其逻辑 ID/hash，不需读 CWP 原件。

开工输入包：本卡、S0a observed 接口表、本仓 2.2 schema/合同夹具、活动证据清单；StockWiki 真实 identity snapshot/mapping golden 尚未产时标 pending，本仓可先做 schema/校验 CLI 和门禁清理。

## 已知状态与接口

2026-09-29 审计时本地 `master@25b8d14`，活动工作树有约 485 条状态；此前按不同受限环境观察的计数不同，开工前重新做完整状态和 PWF 路径清单，不把未提交文件一律当临时垃圾。IQS 的**契约包**是 `2.2.0`，其中发行人 Entity `2.1.0`，新增 AnalysisSubject `1.0.0`；旧跨仓总计划写“C01 v2.1”只覆盖其中一层。当前 schema/规则见本仓 `docs/implementation/contracts/identity.md` 与 `schemas/quick_scan/identity.schema.json`。

IQS 向 StockWiki 交付：版本化 issuer/security/listing、AnalysisSubject、source-binding 的**schema、参考校验器、合同夹具和公开 JSON 校验 CLI**。当前 `scripts/contract_validation.py` 只有 Python 函数，没有该 CLI，须新建薄入口，例如 `scripts/identity_contract_cli.py --input <snapshot.json> --schema-version 2.2.0`：stdout 一行 JSON `status=valid|invalid`、结构化 error code/JSON pointer，valid 退出 0、内容无效退出 2、未知版本退出 3；输入文件只读、文件大小有界。StockWiki 运行时按 schema 本地验，总指挥在 G2b 用本 CLI 交叉验，不要求 StockWiki 导入本仓内部模块。按本仓 `docs/implementation/cross-project-delivery.md`，StockWiki 是身份库/名单的唯一生产写入者；真实 identity snapshot golden 必须由 StockWiki 的 DB/serializer 生成，再由 IQS 校验。四态跨仓映射 DTO **尚未存在**，由 StockWiki 定义/生产 status、issuer/security/listing、as-of、来源绑定、错误码；其中 JSON `null` 表示未请求/未尝试，`unknown` 表示已尝试但无精确匹配，`ambiguous` 是多候选，`mapped` 是唯一精确绑定。IQS 补校验规则和各态反例，不能把它算作现成 identity 2.2 功能。CWP SourceRef/SourceExport 提供来源 ID/hash，不替 StockWiki 判定证券和上市地。

## 本仓实施顺序

**当前状态（用户于 2026-09-29 报告）：**第 1–4 步已完成；仅第 5 步 G2b 等 StockWiki 的真实身份 DTO/golden。下列步骤 1–4 是交付范围和已完成工作的记录，不是要求 IQS 再执行一遍。收到 producer golden 后，先核实报告/commit/CLI 版本，再跑 G2b 并更新状态。

1. 按 PWF/当前 Git 分类本仓活动文件：有效 schema/代码/测试、证据、一次性运行日志与已被 main 覆盖的副本分别列清；有效内容先进入本仓分支，不批量 reset/clean，不删被研究记录引用的证据。
2. 冻结 identity package 2.2 的现行 schema/参考校验器/合同夹具，补 issuer/security/listing/AnalysisSubject/来源绑定错配测试；新建上述公开 JSON 校验 CLI 并给正反例、退出码 golden。把版本、字段、错误和夹具 SHA 交总指挥。StockWiki producer 实际产生的 snapshot golden 返回后，本仓用公开 CLI 校验并记录兼容结果。四态 mapping DTO 由 StockWiki 新建后，本仓按其版本补校验夹具；不得自行编造 StockWiki 的生产者正例。
3. 退役工程任务闭环 `scripts/task_receipts.py` 与 `docs/implementation/contracts/task-receipts.md` 规定的逐 assertion 日志/hash、递归依赖收据、实现快照、独立复审和 P01 两次人工签收。历史记录保留只读；当前每个提交只报告 HEAD、受影响测试、样本 SHA、测试根恢复与未解事项。`tests/test_task_receipts.py` 中仅保留适用于新简短交接的少量行为测试，其余旧 verifier 专属测试按历史归档或删除，不为迁移测试而重造签收系统。原工具的“不能登记 company-wiki 原文根”是工程签收路径策略，随工具退出；实际路径逃逸和原件完整性仍由各自 owner 保证。
4. `scripts/deployment_contract.py` 的未见生产调用的 `explicit_user_confirmation`/`approval_ref` 改成明确外部请求与有限预算；保留发布集合、策略版本和 provider 失败。`scripts/contract_validation.py` 的 trusted identity/check/search/ingest/content 结果不能批量删：逐字段证明同一事实已有 owner 记录+来源证据/修订/hash，然后只删重复证明；保留错公司、错证券、错期间、伪造高等级等拒绝。
5. 本仓提交后由总指挥与 StockWiki harness 对接。G2b 用 StockWiki **真实 DB/serializer golden**经 IQS schema/校验器测身份映射和来源绑定，不读取叙述包；IQS 不进入 CWP Worker DAG。

## 独立测试包

- `tests/test_identity_contract.py`、`tests/test_identity_bound_work_observation.py`、`tests/test_g0_regressions.py` 及新增 CLI 子进程测试：identity package 2.2 schema/参考校验器/公开 CLI 正例、错证券/上市地/期间、来源 hash 不符、未知版本非零退出；四态 mapping 测试等 StockWiki 新 DTO/golden 后才新增，先标 pending。
- `tests/test_task_receipts.py`：只保留新简短交接的直接行为断言；旧递归 hash/reviewer 专属测试可随工具归档/删除，历史收据仍只读。
- `scripts/contract_validation.py` 的现行受影响测试及 deployment contract 测试：trusted 证据字段简化后同样拒绝伪造或越界，预算失败仍失败。
- 本仓用独立测试根/fixture，不改 CWP 或 StockWiki 原件；真实 IQS→StockWiki consumer golden E2E 由总指挥在 G2b 运行。

交接提供本仓 base/branch/commit、契约包 2.2/Entity 2.1/AnalysisSubject 1.0 的 schema/参考校验器/合同夹具 SHA、对 StockWiki 真实 producer golden 的验证结果、改动路径、测试命令/退出、活动证据保留清单及未解 hold。IQS 合同字段变化先升本仓 schema/夹具版本，再由总指挥协调 StockWiki producer；StockWiki 映射结果变化先由 StockWiki 升 DTO/golden 版本，再交 IQS 更新校验。双方均不得跨仓代写。

**本线自动验收：**2.2 现有 schema/校验器和身份错配负例通过；工程签收工具退役后不再需要 reviewer/hash 链，trusted evidence 错配仍拒绝；四态 mapping 校验在 StockWiki 真 DTO/golden 到达前保持 pending。新测试零 skip，只用本仓可写短临时根，生产证据及测试树前后相同；G2b 的跨仓真实消费由总指挥另验。
