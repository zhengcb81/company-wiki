# CWP 模块边界只读审计

日期：2026-11-11。基线：`08dfe8bf1ae97dff34b28976d532b3482d3ba358`。已读项目 `AGENTS.md`；未运行测试、安装、下载或付费调用，未改生产代码。以下“已确认”表示从当前源代码确定的依赖或缺口，不表示本轮完成运行时复现。

本轮先用 CodeGraph 调查目录、公开符号、调用链，再深读关键文件。CodeGraph 报告 461 个 `src/company_wiki` Python 文件，但未返回实际存在的 `company_source_index_cli.py` 等文件；因此仅为补齐目录覆盖，使用 `rg --files` 得到 479 个 Python 文件。不能用索引数量宣称逐文件审计完成。本轮深审来源读取、处理文档、PDF 选择、叙述传输、AUTO 组装及发布链；补查新浪三表实际依赖和 CLI；其余采集供应商、全部 DU 语义算法只做包级清点。

## 1. 完整包级清单与责任

| 当前包（Python 文件数） | 责任与状态 owner | 应允许的依赖及现有入口 |
|---|---|---|
| `source_contract`（14） | SourceManifest、SourceRef、EvidenceSpan、版本化 export 和验证值；不拥有 catalog DB、采集任务 | 标准库/契约资源/必要共享值；`SourceVersionPort`、`SourceChunkSink`、`VerifiedContent`、`SourceExportBundleV2`。历史公告采集路径是受控兼容 shim |
| `document_model`（7） | 单篇文档的中立内存模型、turn grammar、表格/文本形态 | `source_contract`；`NarrativeUnit`、`DocumentStructure`、`NarrativeEvidencePackage`。旧 catalog 路径重导出同一类，不另建 DTO |
| `document_normalization`（29） | HTML/DOCX/PPTX 原文规范化、locator replay、局部 OCR；无 catalog/job 状态 | 契约、中立模型、共享预算/运行工具；`normalize_document`、`normalize_verified_document`、`replay_*`。子包：`layout_snapshots`（5）、`pdf_table_observations`（2，历史 shim） |
| `parser_adapters`（6） | PDF 原生字节/页面/旧解析结果转换 | 契约、`canonical_ingest.ParserResult`、底层解析依赖；`adapt_pdf_pages`、`adapt_pdf_extract_v3`、`validate_native_pdf`。不依赖 AUTO 或 catalog |
| `document_understanding`（81） | 只消费已解析单元，产出观察、路由、结构、选材依赖和摘要输入；不读取原件、不调模型 | 契约、中立模型、共享预算；`understand_units`、`build_observation`、`build_dependency_packages`、`build_summary_input`。子包：profiles、structure、layout_hints、geometry_intent、operating_states、source_signals、statement_grammar、table_measurements、decision_dependencies |
| `source_catalog`（241） | 原件发现/采集/保存、身份与版本、物理位置、目录 DB、可读字节、解析组合、来源选材及 artifact CAS | 下层五包及共享基础设施；不依赖 AUTO。公开路径含 lazy `SourceCatalog`/`SourceVersionReader`、采集与身份服务、`read_processed_document`、`RawNarrativeSelector`、`PdfReading`、`NarrativeArtifactReader/Store`。子包 adapters（7）、financial_statements（9） |
| `automation`（66） | 有限批次、job/attempt/lease/generation/outbox、模型调用和累计预算恢复 | 只通过来源/处理/发布契约调用上游；`register_narrative_handlers`、`run_batch`、`NarrativeTransportReader`、WorkerRuntime。子包 handlers（1）。AUTO DB 保持唯一任务状态 owner |
| 根模块（35） | 共享基础设施和历史兼容混置，不能一律视为“底层” | 中立：canonical_ingest、narrative_subject、wire_json、resource_budget、implementation_identity；I/O/process：atomic_file、bounded_process、file_mutex、process_tree、id_scope、file_usage 及旧 `_` shim；其余 config/model_config、domain/graph_adapter、ingest/legacy_research_ingest、scheduler/run_store/deployment/migration、question*/proposal/quality/routing/source_registry/wiki_repository 与包入口需分别登记 canonical/legacy 归属 |

物理数据库/路径只能由其 owner 保持；这里的“只读端口”不是 Python 安全沙箱。`__all__`、下划线与 AST 规则表达维护契约，不能限制同进程反射。

### 新浪三表现役分支（Catalog 内部责任）

`financial_statements/contracts.py:17-35,103` 拥有 request/response/1、期间/intent 与请求验证；`normalize.py:1-19,345` 是无 I/O 的新浪 JSON→typed rows/JSON Pointer/版本 hash owner。`sina_provider.py:17-26,52-79` 通过 BudgetedHTTPTransport 和共享 AcquisitionBudget 获取有界分页；`provider_contracts.py:66-70` 已提供 StatementsProvider。

`service.py:87-114` 组合 catalog、CanonicalSourceWriter、provider、可注入 repository，并创建 SourceVersionReader；`repository.py:87-108,583` 拥有长表 SQL/只读查询，发布要求真实 CatalogStore。DDL 仍进入 `source_catalog/store.py:16` 的唯一迁移链，不是第二数据库。公开调用是 `python -m company_wiki.source_catalog.financial_statements.cli --wiki-root …`，stdin/out 使用三表 wire；`cli.py:174-223` 分离 committed-source replay、reuse_only、fetch，非 pyproject 中独立 console script。

已有 `tests/financial_statements/test_layer_ports.py:20-49` 的 writer 替身/零写 reuse，及 `test_cli_subprocess.py`、`test_offline_e2e_full.py`、provider 分页/预算测试。不得将它们重复建设。后续纳入阶段6/7：同一公开 CLI 的离线 fixture 与已存 source replay 加入安装验收；若需要非新浪实现替换，先处理 `service.py:469,635` 及 `FetchedPage.normalized()`（provider_contracts:28-32）直接调用新浪 normalize 的格式假设，再以第二种 provider wire 验证，不能只因存在 Protocol 宣称任意 provider 已可替换。本轮未审尽 PIT/观察顺序和所有报表数字，不作数据正确性结论。

## 2. 已完成能力，不能重新作为 P3 待办

- `source_catalog/__init__.py:139-277` 已延迟导出 runtime owner。`document_model/__init__.py` 与 `tests/unit/test_document_model_identity.py:45-141` 已保护旧路径的对象同一性、冻结属性和证据序列化身份。
- `source_contract/source_version.py:272-315` 已有事务式 chunk sink 和来源端口。`processed_document.py:111-139` 已注入 `ProcessedDocumentParserPort`，只用 descriptor/verified content/stream；`processed_document_parser.py:87-110` 已定义 parser session。不要再发明第二套处理服务。
- `source_catalog/reader.py:168-199` 使用 SQLite `mode=ro` 和 `query_only`；`service.py:754-780` 已分离 writer、reader 和 artifact session。`catalog_query_contract.py:15-85` 已提供 pathless 候选 DTO 与深冻结 metadata；CompanySourceIndex 已消费查询/可用性 owner 方法。
- `narrative_pdf_reading.py:41-60,147-190` 已有 parser/backend 替换口和整套 recipe/read/verify/replay owner；`tests/unit/test_pdf_reading_boundary.py:16-43` 已用替换 parser 检查同一预算及读取上下文，不能描述成“没有实现替换测试”。
- `automation/narrative_runtime.py:24-75` 已有显式 composition root、source/model 协议和共享 PDF owner。已有 DU 新进程隔离 probe、PDF 专用运行环境隔离及真实 SQLite 行为测试，不是只有 AST。
- `test_layer_public_boundaries.py:240-302` 已限定六条历史导入边并禁止正常消费者回用 shim；`test_source_catalog_legacy_cli_retirement.py:85-122` 已撤全目录 normalize/summarize 和 worker start/resume。`control.py:567-579` 的旧 launcher 字段不构成当前可执行启动缺陷，不能据此重新开放旧 worker。

## 3. 已确认的边界缺口

### CWP-01：传输 Reader 协议外反查 OCR 配置

`automation/narrative_transport.py:76-83` 的来源协议只有 query/open/availability；`_read:365-368` 却默认调用 `NarrativeNormalization.from_reader(self._reader)`。后者在 `source_catalog/narrative_normalization.py:79-84` 读取 `reader.catalog.config.project_root`，再从项目配置目录加载 OCR；无 `catalog` 的合规替身静默变为无 OCR。当前 CLI 在 `narrative_transport_cli.py:194-199` 没有传已有的 normalization 参数，因此这不是孤立的未调用 helper。

影响：两个均满足来源协议的实现，在 PPTX OCR replay 上可能得到不同能力；替换来源后还需知道实现的配置布局。整改只需在现有 CLI/composition root 显式构造并传入 normalization，核心传输不探查 Reader 身份。纯 helper 的删改和兼容窗口由同一作者完成，不新增 service 包。

建议先红测试：`test_transport_replays_ocr_with_protocol_only_source`，替身仅实现三个协议方法，访问 `catalog/config/path` 立即报错；提供显式 normalization，与实际 source reader 路径得到相同 locator/receipt。再测无 OCR 配置时的既有具名失败，不允许静默猜测配置。

### CWP-02：PDF 选择的预算配置仍是隐藏环境输入

`source_catalog/narrative_selection.py:101-117` 在 `_select_pdf` 内部调用无参 `new_document_work_budget()`；`resource_budget.py:49-67,89-94` 默认通过环境变量或 `__file__.parents[2]/config/resource_budget.yaml` 读配置。`RawNarrativeSelector` 构造器（45-52）只有解析/规范化/selector 参数，外层不能把已解析预算直接传入此调用。

这是已确认的隐藏配置依赖；独立安装失败尚未在本轮复现。它还使完全替换 PDF backend 的调用仍依赖本仓配置文件。应由已有 composition root 解析配置并注入 WorkBudget 工厂或已确定策略，保留真实累计预算，不建立任意新门槛。

建议先红测试：`test_raw_selector_uses_injected_work_budget_without_config_io`、`test_two_runtime_configs_do_not_share_implicit_budget`。覆盖 parser 与 selector 共用同一账户、耗尽后不执行下一阶段；不得仅 patch `new_document_work_budget` 后断言被调用。

### CWP-03：中立类型经具体实现路径导入

`automation/narrative_source_guard.py:9-12` 为 `SourceRef/VerifiedContent` 导入 `source_catalog.source_reader`；该模块 `source_reader.py:20-34` 随即引入 resolver、service、store。真正类型 owner 已在 `source_contract`（source_reader 自己在39-43重导出）。边界扫描允许公开重导出，但“公开”仍不能使它成为轻量契约依赖。

整改：直接从已有契约 owner 导入值，沿同类调用点逐个迁移；真正创建 `SourceVersionReader` 的 composition root 继续使用具体实现。先红测试 `test_source_guard_imports_without_catalog_runtime`，在新进程中拒绝加载 catalog 的 resolver/service/store，然后构造协议替身完成 guard。该测试只验证依赖，不做全局运行时防反射。

### CWP-04：产品安装契约缺少执行验收

`pyproject.toml:18-29` 声明11个 console scripts；`test_packaging_contract.py:14-38` 只检查 TOML、src layout 和文件存在。CI `.github/workflows/ci.yml:48-50` 安装 requirements，`tests/conftest.py:54-58` 将 scripts/src 加入 sys.path。已检索 tests、tools、CI 的 wheel/安装关键词，未发现构建并安装 company-wiki wheel 后运行这些入口的验收；PDF 专用环境部署不是该验收的替代品。

需验收而不能凭静态断言判为已失败的点：`model_config.py:34-43`、上述预算的仓库配置路径；`document_normalization/__init__.py` 急切导入 DOCX parser，`docx_parser.py:15` 直接需要 lxml，而产品依赖将相关能力放在 catalog extra；哪些 base/extra 入口应该可启动必须写明。`scripts/narrative_batch_configured.py:9,27-36` 从脚本 Config 组装有限批次，尚未成为包内 console 能力；canonical AUTO 使用 `NarrativeHTTPModel`，没有发现 src 直接 import 旧 `scripts/llm_client.py`。

关闭条件：使用离线预备 wheelhouse，分别在非仓库 cwd 的 base 与声明 extras 环境安装 wheel；不设置源码 PYTHONPATH，逐个运行 console `--help` 和本地 fixture 请求，校验包内 schema/profile 资源和有限子进程入口。配置显式传入；缺失可选依赖须具名失败。此轮不执行安装。

## 4. 设计风险与未验证项

1. **源目录包过宽，非新确认循环。** 241 个文件中混合采集、存储、解析、选材、传输值。`SourceCatalog.store/reader` 仍公开具体 CatalogStore/ReadOnlyCatalogReader（service:754-766）；Reader 协议含 SQL 和 sqlite3.Row（reader:58-85）。这些是同一存储 owner 内部接口，不能把它们当跨服务替换契约。优先按实际外部消费者收窄方法，不给每个内部文件造接口。
2. **持久化读者仍以具体类表达边界。** `NarrativeTransportReader.__init__:170`、`NarrativeBundleReader.__init__:73` 标注具体 artifact reader/store。已有 owner 封装有价值；若要独立替换存储，应先冻结所用方法和错误语义，再用只实现这些方法的内存替身与 SQLite 实现运行同一 suite，不能只把注解改 Protocol。
3. **不可变程度需明确。** `document_model/narrative.py:51` 仅浅拷贝 metadata 并套 MappingProxyType；`test_document_model_identity:106-121` 测顶层赋值和序列化。嵌套 metadata 的所有权尚未验证，且其中可能有故意借用的 native context；不能直接全量深复制/冻结。先区分 owned wire 值与 borrowed transient 值，再测试输入别名修改是否影响输出身份。
4. **历史边继续限范围。** 已知 upward shim 不等于 canonical 循环；本轮没有确认新的跨层循环。未完成全图 SCC/动态 import 证明，不宣称无环。`__all__` 中新增名字本身不足以证明职责封装，须补行为替身与安装后导入验证。

## 5. 一张 CWP 主卡，七责任按阶段关闭

同仓 src、边界 AST、契约测试由一个作者统一；ROOT 在该卡交付后接组合 runner，避免并发写同一测试文件。

| 阶段/责任 | 先锁定的红测试与有限完成条件 |
|---|---|
| 1 契约 | 保留 SourceRef/EvidenceSpan/export wire 与兼容类同一性；修 CWP-03。只消费旧 owner，禁止第二 DTO 家族 |
| 2 中立模型 | 明确 nested metadata 的 owned/borrowed 约定；增加一次别名变异测试，旧 locator/span 身份不变 |
| 3 规范化 | 修 CWP-01；将已有 normalization 注入传到 CLI，协议替身不可触达配置和路径 |
| 4 PDF adapter/reading | 修 CWP-02；复用完整 PdfReadingBackend；替代实现覆盖 recipe/read/verify/replay 与预算耗尽，不只 parser callback |
| 5 DU | 保留现有新进程隔离；以同一输入/预算验证公开输出，禁止借重构重做来源语义规则。只提取与阶段4有直接关系的接口 |
| 6 Catalog | 延续单 DB/CAS owner；查询/可用性/已验证内容以 DTO 输出。artifact 端口跑 memory/SQLite 同一 suite；保持 unknown paid recovery、pin、原件漂移与事务语义 |
| 7 AUTO/发布 | 保留单 AUTO ledger/outbox；协议替身跑 select→summarize→verify→publish→read；故障恢复不重复付费；执行 CWP-04 安装验收 |

现有 AST 测试用于防止已知反例回归，不能扩展成无限 Python 别名解析工程。`test_normalizer_public_ports`、`test_source_reader_public_port_boundaries` 的签名/调用形状断言继续作为辅助；`test_processed_document_owner_boundary:121-155` 已有真实替身错误优先级测试，应扩展而非重写。

安全拆包顺序：先完成上述逻辑依赖闭合和 wheel 验收，再按 contract/model → normalization/adapters → DU → source runtime → AUTO 建内部发布边界；先保持同一 distribution、同一数据库和兼容导入路径。只有某边界具备独立安装、协议替身、至少一个完整实现替换及真实 owner 回归四项证据后，才讨论独立 distribution/repository。当前报告不建议立即拆仓，也不增加第二任务库、全局反射拦截或新的许可链。
