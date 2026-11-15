# 公开接口责任与并行协作

这是实现前的行为合同说明。现有协议版本和字段以所属repo已发布定义为准；本计划不发明第二套DTO或共用运行时仓库。M0已固定本表、boundary_matrix.json中的owner/声明位置和五卡写集合。五张卡直接从本仓现有合同/fixture开始A，再连续做B/C；缺少本地fixture时由该lane在自己的tests内补充，不等待ROOT交新fixture。ROOT实际多仓组合样本在M2运行前冻结，不能成为五卡的启动门槛。

| ID | Producer → Consumer | 最小合同与禁止泄漏 | 测试归属 |
|---|---|---|---|
| I01 | CWP来源 → CWP parser/reading | SourceRef/SourceProcessingDescriptor + SourceVersionPort；字节通过SourceChunkSink provisional写入，来源owner验真后commit；失败discard，预算调用者提供 | CWP真实source owner契约+纯协议替身 |
| I02 | parser → DU | NarrativeUnit/规范化文档、locator、parser/version、quality/partial；OCR选项由入口注入；不得让DU依赖parser SDK/磁盘来源 | CWP parser和DU各自单元+替换实现 |
| I03 | CWP → FF/RF/StockWiki | query/ensure/source-read/processed-document/narrative-read/source-index，保持现行SourceExport v2等wire；来源与挂牌市场、期间/as-of由字段表达，不能按目录猜 | CWP producer examples；消费者各自adapter测试；ROOT黑盒 |
| I04 | FF → RF/Dashboard | 现行fetch_filing/fetch_statements/ff-job请求和结果；source candidate/structured gap/error保持可区分；FF不再次创建来源身份/状态 | FF owner，RF/Dashboard只改各自decoder |
| I05 | ET/SID → CWP | provider已下载staging或原语言TXT及元数据、稳定error_code/retryable/usage；producer不入库CWP；staging由明确调用生命周期清理 | provider typed contract；CWP adapter；ROOT首取/复用 |
| I06 | CWP statements → FF/RF | financial-statements request/result，provider数据快照、单位/日期/版本/来源；缓存复用无额外HTTP，不能从PDF补造三表 | CWP financial_statements；FF薄适配；RF消费 |
| I07 | RF → Dashboard/AUDIT/StockWiki | RF作业、报告目录/报告版本、公开证据和研究结果；接受外部artifact时通过RF公开入口；code root和data root可不同 | RF owner；消费者公开CLI/API |
| I08 | 各owner → Audit/日志 | 业务终态、稳定错误、可选诊断；日志存储/格式失败独立记录，不触发已成功业务重跑 | 各owner隔离反控；Audit组合 |
| I09 | 公共配置/进程工具 → 各模块 | 显式配置值、唯一实际预算、可取消调用；派生算法版本由算法owner公开提供 | 工具owner；调用计数/关闭/恢复测试 |

## M3 后发现的公共 API / owner wire

以下是 M2 冻结后确认的 CWP 层间公开 API 和已进入 owner 主线的新协议，只登记真实所有权和消费关系，不把它们倒算为 M2 已验收范围，也不由 ROOT 改写其他模块实现。

| ID | Producer → Consumer | 最小合同与禁止泄漏 | 现有证明与剩余验收 |
|---|---|---|---|
| I10 | invest-quick-scan → StockWiki owner | `stockwiki.company_assessment/2`、schema `2.0.0`。输入保留原 `source_release` 字节语义，并用独立 hash 绑定 `lineage_provenance` 与 `lineage_groups`；每题只归入一个 lineage group，不跨组聚合。StockWiki 验证并持有发布/读取状态；不得导入 IQS 私有模块 | StockWiki `tests/test_public_company_assessments.py` 与 golden fixture 107 passed、独立 ACCEPT；IQS 当前 active package 生成 53 题 envelope 并在隔离 StockWiki workspace publish/readback。I10 wire 互操作已有证据；C06 真实历史覆盖仍 OPEN，属于 owner 业务验收，不把它误报成接口失败 |
| I11 | StockWiki membership CLI → IQS owner → Dashboard adapter | `stockwiki.membership_request/1.0.0`。成功的 `apply`、`lookup`、`history` 均返回 `protocol`；错误继续使用 `schema_version` 与稳定 `error_code`。消费者使用 JSON/CLI 合同，不导入 StockWiki 私有 store | StockWiki `test_public_cli_apply_lookup_and_history` 覆盖公开 CLI 的查找/历史版本字段；IQS 11-14 PWF 记录当前公开 CLI 接线及隔离 C38 回归 **120 passed**、固定核心组合 **296 passed**，Dashboard 的 adapter 位于 `backend/dashboard/adapters/iqs/universe.py`。该证据覆盖 I11 的当前 consumer 链，不重复做整套 E08 |
| I12 | CWP document_understanding → CWP source_catalog | `document_understanding.assertion_frames` 公开模块的 `source_assertion_frames`，以及 `statement_grammar` façade 的 `english_question_start`；只提供局部语法/限定观察，不读来源目录、不分配业务身份、不产生研究结论。调用者传入文本与由 owner 提供的 WorkBudget | `document_understanding/__init__.py` 显式导出 `assertion_frames`，`statement_grammar.__all__` 显式导出函数；CWP `test_layer_public_boundaries.py` 纳入依赖方向合同，当前 M3 定向组 119 passed。CodeGraph caller 查询未解析出这些符号的调用边；该图谱跨文件解析为 best-effort，不据此否定显式导出或合同测试，也不把它当作运行时封锁 |

Dashboard 的公司评估页面仍通过 IQS 的 `iqs.dashboard.company_assessment/1` 投影；不把 I10 的 StockWiki V2 owner 输入协议误记为 Dashboard 的直接消费协议。Python package/facade 与静态边界合同定义的是模块协作边界，不声称能把同一解释器中的私有符号变成运行时访问控制。

## 各lane对接口的处理

- 工区使用现有版本和本仓已有contract fixture。缺少对应fixture时由该lane在自己的tests补齐。先跑自己consumer/producer的合同，正常用例已绿则保留；ROOT在M2汇总真实producer/consumer组合。
- 卡内改造限内部依赖、稳定错误传递、隔离测试和已声明兼容性；不擅自变更公开CLI参数、必需字段或schema major。
- 如果当前接口不足以描述真正职责，owner在自己的PWF写最小变更建议和失败用例，ROOT对接相关owner，一次决定兼容新增/新版本及顺序。无需用户逐项许可，也不先写邻仓代码。
- consumer测试使用公开wire fixture或自己的端口替身，不导入provider私有模块；producer必须跑同一正负样例证明真实实现符合，不能两边各自造一个不一致的mock。
- code root/命令路径是启动配置；owner data root是owner私有状态定位。可以引用公开交付artifact或传输staging，不能把其路径推导成DB/源码地址。路径字段不一刀切禁用，按用途归属。

## 已固定的附件与M2组合输入

ROOT维护的 `boundary_matrix.json` 已给owner、公开声明位置、兼容范围和现有证明入口。各lane交接时补实际producer/consumer case和交付版本；ROOT为M2汇总选择，不要求所有lane等同一个新文件。实现源文件只归所属lane。现有协议样例不足才补小fixture到owner测试；不复制整仓、原PDF、密钥、生产DB或其他人的run。

冻结是记录本轮测试输入与版本；它不增加hash授权文件或人工签收。后续生产结果仍按实际公开协议验证。
