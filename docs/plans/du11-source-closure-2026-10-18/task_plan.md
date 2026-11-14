# 主线实施计划

2026-11-14，[模块边界收口子计划](../module-boundaries-2026-11-11/README.md) 已完成。各仓发布、隔离测试及 E01–E09 见 [ROOT 组合记录](../module-boundaries-2026-11-11/review/root_composition_20261114.md)。当前按下表推进 R4/T4 及业务验收。

## 下一步

1. **R4 工作量。** 当前正式半年报回放 12/12，工作耗尽。见 [R4 公开回放](review/r4-public-replay-20261114.md)。过往 9/12 的分诊记录提供统一扫描预扣约 9.05M 的证据。先写与公司无关的 RED 及真实耗尽反控，再由实际扫描阶段扣同一账户，在原 16M 内复验召回、完整性与归属。
2. cn-h1 0.9 业务召回 10/10 的源码冻结结果已有独立收据。T4 父链和 SEM-QUAL-01 仍需现行输入/解码反控与真实独审，之后再做新版摘要、缓存恢复、RF 实际采用和公司循环。
3. 后续历史工区/资料核销按新子计划reconciliation.md的owner和清单执行；A1已做的约216MB测试清理、7空工区、重复源码/生成物不重做。原件、费用及独有证据保留；每卡接收完成后ROOT再回收对应旧工区。

实施细节、测试计数和两份半年报来源 SHA 在 review/current-main-replay-20261110/README.md。当前接口修复通过工程独审。后续每个大节点集中做测试与独审。

## P0-D — 六项解耦遗漏（D4 CLOSED）

**D4-01～D4-06 均 CLOSED。** 2026-11-02 的六项发现和原卡保持为历史输入，当前交接/结果由 [D4 closeout receipt](review/d4-closeout-20261104/README.md) 与 [机器状态](CURRENT_STATUS.json) 为准。D4-01～05 的包实现已分别合入对应主线；D4-06 由 ROOT 将两项 AUDIT 真实 producer/importer 测试归位，并运行一次明确包含 RF、FF、ET、StockWiki、AUDIT 的强制组合。

- 完整 CWP `--d4-final`：27 passed、0 skipped、0 failed，46.623 秒；五类消费者均有实际通过用例；AUDIT 两个必需测试 node id 均执行；scratch 恢复；六仓源码快照前后稳定。独立审查 PASS。
- ROOT runner 现在拒绝用 `--tests` 替换 D4 强制套件或只做 collect-only；路径按 ROOT 规范化；消费者覆盖从 JUnit 实际用例统计；每个必需文件都有通过用例；版本快照涵盖 Git 根级 Python 模块并比较运行前后。
- CWP D4 merge/root 测试 commit `e7469d68` 已推送，FF `bf7e1dab` 已推送。RF `96713029` 已与 origin 同步。StockWiki `23d84586` 和 AUDIT `2449df4a` 本地提交记录已核对；两个仓库无 remote。具体状态见 [PACKAGE_STATUS](PACKAGE_STATUS.md)。
- D4 关闭只说明本轮架构缺口的覆盖范围闭合；不把局部组合通过外推成全文档业务链、真实摘要或整家公司审查循环完成。P1–P3 真实产品责任继续 OPEN。

实施前置见 [原 D4 复核报告](review/decoupling-recheck-20261102/README.md) 和 [ROOT 最终组合契约](review/decoupling-recheck-20261102/harness_lanes/ROOT-D4-final-integration.md)；这些内容保留历史原要求，执行状态以 closeout receipt 为准。

## P0-E — D5冻结接口缺口（该范围ACCEPTED；全模块以新计划验收）

**已修复的根因：** CWP 的通用解析/规范化结果此前没有作为结构化 pathless 公共接口提供给 StockWiki，StockWiki 三个默认业务入口因而会把 PDF/Office 原件交给自己的 parser。D5 将解析归属收敛到 CWP，并以固定跨仓套件验明 StockWiki 三入口消费 port；FF schema 2.0 继续走 V2/pathless，V1 只作为显式版本兼容入口。最终证据见 [ROOT D5 closeout](review/decoupling-recheck-20261104/root-d5-final/README.md) 和 [D5 外包卡](review/decoupling-recheck-20261104/harness_lanes/D5-CWP-STOCKWIKI-PROCESSED-READING.md)。

| 顺序 | Owner | 工作 | 大节点验收 |
|---|---|---|---|
| D5-A | ROOT（COMPLETE） | 冻结 producer-owned、pathless、带 parser/version/locator/partial 状态的合同；不另建缓存。 | 合同固化在施工卡与跨仓契约测试。 |
| D5-B | 外部单一 harness（COMPLETE） | CWP port 与 StockWiki 三个 provider 默认 consumer 在独立 worktree 同步实现；交付独审绑定 CWP `a28692a6`、StockWiki `6d1e40bc`。 | 两仓按快进进入主线；StockWiki 无 remote。 |
| D5-C | ROOT（COMPLETE） | FF schema 2.0 V2/pathless、V2 不进 V1 文件校验，显式 V1 隔离兼容的必需路由用例均通过。 | 3/3 通过；见 [FF 子节点收据](review/decoupling-recheck-20261104/root-d5-ff-route/README.md)。 |
| D5-D | ROOT + 独立审查（ACCEPTED） | CWP/StockWiki/FF 固定组合、真实本地样本原件稳定、生产 transport 配置绑定审查提交、测试 scratch 恢复。 | run-6 为 18 passed、0 skipped/failed/errors；独审 PASS。 |

**D5 完成定义：** 每个模块只负责自己的实现、状态和错误语义，并通过自己的独立契约测试；跨模块只经版本化公开合同组合，不依赖邻仓私有模块、物理路径或内部数据库。CWP 是通用文档解析唯一 owner；StockWiki 三个 provider 入口消费同一 pathless 规范化 reader，业务层可引用 locator 且不再解析 CWP PDF/Office 原件；FF schema 2.0 provider 主路径不暴露/消费 canonical_path，当前内部生产消费者使用 V2，旧 V1 若保留则作为版本显式、隔离且有测试的兼容接口。三仓独立测试与一个临时环境的 producer→consumer 实际 E2E 通过；原件 SHA 稳定、测试目录初始状态复原；最终独审绑定交付版本。这些条件定义D5冻结接口范围的ACCEPTED；当前全模块解耦以module-boundaries-2026-11-11的矩阵验收为准。

**当前恢复顺序（2026-11-14）：** 模块边界已验收，继续 R4 工作量、T4 source-note-parent + SEM-QUAL-01、新版真实摘要、付费中断及同跨 run 缓存恢复、RF 实际采用和固定公司循环。

**缓存范围说明：** D5 把通用解析 owner 收敛到 CWP，没有建立第二套缓存。验收没有证明 CWP 有可复用的通用持久化 normalized-unit cache；当前 port 按请求读取/解析。跨运行缓存恢复仍属于后续主线任务，不能据本次解耦验收标为通过。

## P0 — 已完成的CI根修

compact-frontier/lookahead、消费者和Windows嵌套夹具已根修、独审、正常发布及精确CI绿。保持轻量pre-commit/有界pre-push；仅新行为或失败需要新增回归，不重跑超时整仓或删重要断言换绿。

## 全模块代码质量整改 — 工程已独审/完整CI通过并线，真实C待验收

[2026-11-01审查](review/architecture-quality-20261101/README.md)和[实施细则](review/architecture-quality-20261101/implementation.md)是本计划质量责任的补充，不另立目标。408个源文件结构清单＋关键链详读＋三独立分工，14项归并（1P1/8P2/5P3）；不是逐行全仓功能验收。

- 先在原P3来源修复中合并Q01陌生业务准入、Q02阅读recipe/缓存指纹，沿原R4 source owner根修，不加公司词库/额度。
- 存储查询、预算归属、CAS/legacy工具、跨层合同和边界测试按细则B；StockWiki输出流限额归其transport，CWP不跨层接管实现。
- 旧显式dry-shadow两轮/迁移CLI和无效helper清理，检查聚合到事实owner；必要身份/原文字节/as-of/预算/恢复仍保留。
- 仅大节点集中工程独审、受影响测试及真实E2E；不新增逐项许可。Q01–Q14工程10767b86已独审/完整CI通过并本地主线，Q09在StockWiki本地主线、Q11接收实读SHA经边界论证保留；完整CI63F/22F/70F历史不改。原70期待保留，R5纠正资料可用与现实核实混用；旧结构T3已并线。T4/SEM 实现和 H1 观察已在本地，正式接受仍待 member 差异解释与独审；新版真实摘要/C 仍 OPEN；D4/D5 已 ACCEPTED，原件/生产配置不改。

## P1/P2 — 历史有界摘要与采用已过，新runtime真实C仍OPEN

- 当前华利15完整卡/12业务原子、Berkshire73卡/10原子、各一次配置POST，activation/同跨run恢复已独审。Berkshire15余项与全文partial保持，不额外切碎support/context或提高额度。
- 华利新artifact真正进入used参数/公式及native报告/snapshot，v6独立45项验收；不是完整公司买方研究。原source-only/advisory排名能力边界不改写成生成式全文概述。
- 配置/终态和partial-cache根修已发布：同canonical source-select端口、每文档一次确定性重选证明等价；失败/unavailable不成为付费许可，旧partial/账/paid pin归属不改。
- 来源measurement、COMPOSITION范围与算术footnote共因、RF长卡证据合同已发布有界通过。当前局部新缺口另行修，不重复施工已关闭成果。

## P3 — R4四审完成，候选源层工程隔离，真实复验与其他共因OPEN

R4主/五压力/报告/snapshot和四审已封存。73检查、6P2，无新增已证实P0/P1；每项具体证据、根因确认程度、TDD命令/接口/失败清理/兼容与恢复在AUDIT同run/remediation/r1-remediation-04/implementation.md。它续接W08–W12，不是新外包卡。

### P3 已完成的 source_catalog 公共 owner-port 子节点

- Catalog owner 查询、Resolver/Reader public read ports、SourceCatalog 全包 AST sibling-boundary 契约及其 fast-CI 注册均已推送。扫描规则覆盖静态可解析的导入、别名、反射、`sys.modules`、wildcard、helper/method 参数、闭包/nonlocal、推导式和局部重绑定正反例；具体测试与独立审查记录在 11-10/11 收据及 `CURRENT_STATUS.json`。AST 规则不是 Python 运行时沙箱。
- 2026-11-11 stream/parser 子节点把 pathless `SourceProcessingDescriptor`、同一调用者预算、事务式 `SourceChunkSink`、public `SourceVersionPort.stream_version` 和 parser-owner port 接入生产 processed-document endpoint。处理层不访问目录/SQLite/原始 manifest/物理路径。旧固定 256 MiB 候选帽移除，仍由单一实际请求预算控制字节/候选/时间/取消。
- 先写失效边界与清理 RED 用例，再修复契约导出缺失、跨包动态 `getattr`、pytest 长临时路径测试夹具、session 清理异常遮盖主错误，以及旧 narrative 测试继续 spy 已删除私有 helper 等根因。最终组合 205 passed、1 个既有 skip；宿主 fast-gate 277/277、59.18 秒；Ruff/mypy 通过。独立只读审查最终 PASS。证据：`review/p3-public-stream-parser-20261111/README.md`。
- 子节点提交并推送到 `origin/master`：`54f8b470c36a7dd932bfe4ac6ba52ba4edbf01ca`。push hook 固定 18 项通过、3.78 秒。远端完整 CI 本次未核验，不声称已通过。
- **不外推结论：** 已完成的只是 CWP 来源流与解析边界子节点，不代表所有包/跨仓零耦合、P3 公司审查循环或全项目目标完成。历史候选重放及其他明确模块边界仍开放。

1. **来源层优先**：旧T3与R7工程均已并线；实际H1独审仍发现peer note继承旧局部子标题。按[T4细则](review/architecture-quality-20261101/implementation-results/T4-source-note-parent-plan.md)冻结泛化正反例、同层根修和单例真实复验；保十二重点/原生成员，不加公司词库、额度或普遍bbox要求。
2. **共享语义合同**：完成ghost-formula kind与formula/input互斥预检，validate/lint薄复用；完成同口径signed temporal complement，保留alias/origin/provenance、重叠/空隙/跨期/口径反控；inverseYoY使用显式比较关系，禁止放宽日期冒通过。
3. **记录与技术质量**：新attempt从当前scope构建真实路径，冻结R4不改。复用测试入口、在付费前验证observer必需技术字段；审计报告已完成不重跑全部。已有CAS/日志重复观察只在原质量责任内处理，不迁移旧封存、建新任务库或造物理节省数字。
4. **有界真实复验**：在隔离新attempt仅复验受影响链；原件经CWP只读复用，缺资料才用FF正确provider；源材料改变才按配置预算准备新摘要，真实paid中断/same/cross恢复及8卡actual RF采用/主/压力/报告/snapshot要有新证据。失败保留、未知账不退。测试新增文件以初始清单/原件SHA恢复，不能删初始已有或他人文件。
5. **集中独审与边界**：单元覆盖责任层，集成覆盖接口，E2E覆盖真实链；只在大节点独审。scope描述修复不要求收费重放。算术正确不代独立经济范围；净客户暴露、未来经营幅度、ET能力及Q&A时点未知不编数，不强装provider。
6. **原第7/8步实际收尾**：按本节点专家quality-closeout/review-evolution方案改善硬编码/重复、模块化/泛化、买方反证和检测；正反例/独立试读、必要定点安装、下一有效attempt真实采用齐全后才记完成。当前这些仅计划。

本轮交付标准：六issue完整身份逐项处置，carry-forward不遗忘，原件不丢、既有正确边界不退化，实际受影响链复验及集中独审通过，正常提交推送/安装、隔离恢复可核。外限明确保留，不能以记录coverage或工具未评质量当公司PASS。

## 后续泛化与完整循环

- 本公司受影响责任闭合后，按既有顺序药明合联、Snowflake做新公司泛化；样本/检查点先冻结，不因结果换公司。
- 完成固定八家与旧NVDA/三市场责任；每家真实executor、四审、共因修复/复验、方法质量和检测演进实际落实。
- 固定责任完成后，同一有效版本连续三家不同公司无主要问题才满足抽样停止；关键外限不计clean，不能以三家跳过固定清单。
- W21 canonicalC2真实增强/严格成员对齐、新US监管/HK/US_RPO和长文公平性仍按原责任；W23 OCR R1工具根修已独审/候选完整CI通过并FF主线；实验仍PARTIAL、实际总耗时/1800合规未证，不替代生产OCR。

## 边界与发布

ROOT维护主状态/接口/集成，各仓owner维护本仓活动PWF；本次只拆既有未完责任，不扩新产品范围，不新增逐小节点签收、私有根分类、人工许可或第二身份/任务库。预算/模型按当前配置，原件不翻译，未知保留。Dayu/IQS/Dashboard与其他owner WIP不动；CWP不保存投资研究结论。测试只跑必要快速域/受影响集成与大节点E2E，不无故重复全量。

## 2026-11-02 — 整改清单逐项验收结果

原41正式项：40工程完成、Q11边界论证保留；8个T01实际入口全部对应。三新增漏项直接同owner修复，54CWP/33StockWiki/23ledger受影响测试通过，独审/精确CI以CURRENT_STATUS为准。2可选优化与真实公司验收不作已完成、不增微节点许可。详细表：review/architecture-quality-20261101/implementation-results/checklist-verification-20261102/checklist.md。
