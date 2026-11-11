# RF / StockWiki / Audit / Dashboard 架构只读核查

日期：2026-11-11。角色：research_architecture。范围仅为架构、接口、状态归属、隔离证据和后续施工边界；本轮没有执行测试、网络、安装、收费调用、源码修改、配置修改或 Git 写操作。唯一新增文件为本报告。RF 预测质量、经济合理性、校准和业务样本完成度不作为模块解耦的退出条件。

## 结论

1. 当前主要业务边界已存在，不应重写成另一套框架。RF 来源准备通过 FF/CWP 子进程；StockWiki 默认公司来源通过可替换的来源 ports；Audit 消费执行包/已发布 narrative；Dashboard 通过 ports 和 owner CLI/API，计算结果仍由 owner 提供。
2. 已确认一个局部越界：RF 分发目录中的 `processed_artifact_canary.py` 直接查询外部 catalog 的 `artifacts` 表，并复制派生物重算关系。它是遗留诊断路径，不能据此宣称正常 RF 来源准备仍直读 CWP 数据库。
3. RF 历史 B34 research admission 认识 Audit 执行包目录和 CWP 特定代码 probe 的形状。它不是当前调用时任意导入 CWP，也不是直接读取 CWP 原文库；问题是特定兼容 profile 与实现布局耦合，适合版本化导出合同增量收敛。
4. RF runtime 兼做发布、可选签名和索引登记，report validator 又通过兼容聚合模块回取大量函数。责任边界可进一步明确，但没有本轮证据要求重写公式或把所有研究模块拆仓。
5. StockWiki、Audit 和 Dashboard 已有实质隔离测试。应先执行约束明确的黑盒验证，再决定是否需要实现卡。Dashboard 已有 owner 施工和 tracked WIP，本轮不另派竞争实现包。
6. 主仓 HEAD 与 Dashboard release code roots 不是同一件事。RF/StockWiki 主线没有部分 Dashboard 消费的新增入口；可见本地配置明确使用独立 release worktrees。不能把主线入口缺失误报成当前部署故障，也不能未经 owner 接续就合并这些树。

## 基线、适用指令与证据限制

| 仓库 | branch / HEAD | tracked 状态 | 说明 |
|---|---|---|---|
| revenue-forecast | main / `b005a179280ee19695578bdba9427b4dd44cdd73` | 4 项既有 WIP | `assurance/runs/daily_alert.jsonl`、`monthly_manifest.json`、`weekly_alert.jsonl`、`weekly_manifest.json`；不得覆盖 |
| StockWiki | master / `12c441e86282135b49120112dcf21c17509bbdd0` | tracked clean | 不等于未跟踪文件为空，也不等于 release worktree 与主线一致 |
| revenue-forecast-audit | main / `3589b69cb9d28d7395607ce4fe689025b9acee96` | tracked clean | 同上 |
| investment-dashboard | main / `b707473a1166d3f8740170dad77cb21aa09863ce` | 4 项既有 WIP | `backend/dashboard/application/service.py`、`ports/protocols.py`、`transport/http.py`、`tests/support/factory.py`；交给原 owner 接续 |

HEAD/branch 由本角色只读取得；本角色 sandbox 中 `git status` 返回 `this operation must be run in a work tree`，显式 work-tree 形式也未取得状态。表中的 tracked 状态来自 ROOT 经获准宿主只读 Git 的复核消息，不冒充本角色独立完成的状态扫描。未 fetch；不对 remote freshness 或所有 untracked 作结论。

已读 StockWiki、Audit、Dashboard 根 `AGENTS.md`；RF 未发现根或嵌套 `AGENTS.md`。相关约束是：StockWiki 默认维护可持续系统，完整检查走单一 `scripts/checks.py`；Audit 是编排/记录技能，不把记录正确当预测质量；Dashboard 总 PWF 归 D00，owner 仓只读、公共接口集成。RF/Audit `SKILL.md` 仅作为产品公开面文档审查，不在此启动任何公司研究或审计工作流。

CodeGraph 四仓均有索引（RF 246、StockWiki 262、Audit 106、Dashboard 52 个索引文件），先用 status/files/context/search。实际发现索引落后：RF 对 `scripts/*job*` 返回无文件，工作树已有 `rf_job_cli.py`；StockWiki 索引仍含已不存在的 `source_provider.py`；Dashboard 索引不含当前多个 adapter 文件。因此图用于初步导航，新增/失配区域用只读 `rg --files`、指定文件读取补足；未初始化、更新索引或把旧图行号作为当前证据。下文行号来自当前源码读取。

## 当前最小公开面与状态所有权

### RF 内部模块

| 模块 / owner | 应保留的最小公开面 | 输入 → 输出 / 状态 | 当前证据与边界 |
|---|---|---|---|
| 来源准备 | `prepare_source_result`、`prepare_registered_source_result`；`source_preparation.py` CLI | 请求/SourceRef + as-of + 可信 transport 配置 → `source-preparation-result/1`；不存第二来源库 | [source_preparation.py:379](C:/Users/郑曾波/Projects/revenue-forecast/scripts/source_preparation.py:379)、[source_preparation.py:401](C:/Users/郑曾波/Projects/revenue-forecast/scripts/source_preparation.py:401)。唯一默认是 pathless v2，配置缺失在 outbound 前报错；legacy helper 单独保留 |
| FF adapter | `resolve_filing_result`，只在此构造 FF CLI | 请求 → 完整 machine envelope / 明确 upstream failure；FF/CWP拥有采集和去重 | [filing_fetch_client.py:217](C:/Users/郑曾波/Projects/revenue-forecast/scripts/filing_fetch_client.py:217)。固定 `scripts/fetch_filing.py`，`shell=False`，可配置 FF root；使用 RF 进程的 Python，是部署约束而非跨仓 import |
| 原件 consumer | `open_source_version_v2`、`VerifiedOriginalRead` | exact SourceRef + as-of/期间 → immutable verified read | [company_wiki_source_reader_v2.py:136](C:/Users/郑曾波/Projects/revenue-forecast/scripts/company_wiki_source_reader_v2.py:136)、[:250](C:/Users/郑曾波/Projects/revenue-forecast/scripts/company_wiki_source_reader_v2.py:250)。支持独立 `reader_command`；默认才是 CWP `-m` 入口；schema 2.1 默认，2.2 显式可选 |
| narrative consumer | narrative reader / `consume_narrative_input` | 来源 span/context → RF claim/parameter 依赖映射 | 来源阅读、来源角色与模型使用分开；不让 narrative 接口决定预测接受。对应 [test_decoupled_source_port.py:69](C:/Users/郑曾波/Projects/revenue-forecast/tests/test_decoupled_source_port.py:69)、[test_architecture_dependency_uses.py:49](C:/Users/郑曾波/Projects/revenue-forecast/tests/test_architecture_dependency_uses.py:49) |
| evidence / input contract | `validate_sources`、`validate_document`；typed source/clock/period helpers | source/capture/claims/parameters → 校验值和命名错误；不负责抓取/目录寻找 | [contracts/document.py:268](C:/Users/郑曾波/Projects/revenue-forecast/scripts/contracts/document.py:268)、[:1106](C:/Users/郑曾波/Projects/revenue-forecast/scripts/contracts/document.py:1106)。该文件是输入编排器，调用研究覆盖与模型合同；不宜误称为纯 transport schema |
| research | coverage / growth-driver / targets / revenue-basis / native-dependencies 的领域 API | 已绑定证据 + native DAG → 研究覆盖、目标对照、解释和诊断 | [research/coverage.py:14](C:/Users/郑曾波/Projects/revenue-forecast/scripts/research/coverage.py:14)、[research/drivers.py:443](C:/Users/郑曾波/Projects/revenue-forecast/scripts/research/drivers.py:443)、[research/targets.py:42](C:/Users/郑曾波/Projects/revenue-forecast/scripts/research/targets.py:42)、[research/native_dependencies.py:9](C:/Users/郑曾波/Projects/revenue-forecast/scripts/research/native_dependencies.py:9)。复用真实 DAG，不另建研究图执行器 |
| model / calculation | `ModelSpec`、registry、`calculate_registered_model`；forecast dependency/calculation API | native inputs → deterministic scenario paths；不读库/网络 | [model_registry.py:21](C:/Users/郑曾波/Projects/revenue-forecast/scripts/model_registry.py:21)、[:75](C:/Users/郑曾波/Projects/revenue-forecast/scripts/model_registry.py:75)、[forecast/calc.py:10](C:/Users/郑曾波/Projects/revenue-forecast/scripts/forecast/calc.py:10)。扩展公式进 registry，不在 UI/adapter 再实现 |
| runtime | `run_forecast(data, mode)`；`revenue_forecast.py` CLI | 输入 → 自包含正式或 draft 结果；formal 可签名/登记 | [revenue_core.py:418](C:/Users/郑曾波/Projects/revenue-forecast/scripts/revenue_core.py:418)。这是应用编排入口，不是纯计算函数；formal 注册副作用见 [:477](C:/Users/郑曾波/Projects/revenue-forecast/scripts/revenue_core.py:477) |
| report / publication | `validate_published_forecast`、`render_markdown`、receipt API | frozen input/result → 验证/展示；与 model 同源计算 | [revenue_report.py:1446](C:/Users/郑曾波/Projects/revenue-forecast/scripts/revenue_report.py:1446)、[:1615](C:/Users/郑曾波/Projects/revenue-forecast/scripts/revenue_report.py:1615)。验证复算不是另一个 forecast owner；不能以解耦名义删除强校验 |
| publication registry | register / lookup / audit / rebuild | 已验证结果 → discovery index；索引 I/O 为诊断 | [publication_registry.py:144](C:/Users/郑曾波/Projects/revenue-forecast/scripts/publication_registry.py:144)、[:289](C:/Users/郑曾波/Projects/revenue-forecast/scripts/publication_registry.py:289)。与 report catalog 的 run/report 关系索引不是同一职责 |
| report catalog | `rf-report-catalog/1` 的 9 个 read commands；显式管理 admission/import 另行 | opaque IDs → frozen report/model/calculation/source snapshot，私有 artifact locators 不出 owner | [report_catalog.py:1](C:/Users/郑曾波/Projects/revenue-forecast/scripts/report_catalog.py:1)、[report_catalog_cli.py:57](C:/Users/郑曾波/Projects/revenue-forecast/scripts/report_catalog_cli.py:57)。公开查询不扫描 `delivery/output` 寻找成果 |
| jobs | `rf-job/1`: submit / get-status / act reconcile,resume / list-jobs | 业务 scope 与可信 deployment 分开；owner `artifacts/rf_jobs/jobs` 独占状态 | [rf_job_cli.py:1](C:/Users/郑曾波/Projects/revenue-forecast/scripts/rf_job_cli.py:1)、[rf_job_facade.py:28](C:/Users/郑曾波/Projects/revenue-forecast/scripts/rf_job_facade.py:28)。三个阶段 source/compute/publication；catalog import 在显式管理面，不让 Dashboard 建另一任务库 |

RF 的 `sys.path.insert` 主要定位自身 `scripts`。`report_catalog_research_publication_sources.py:41/61` 动态构造/加载的是本 RF validator，且检查模块实际根；不能仅看到 `sys.path`/`importlib` 词就判为邻仓越界。需要区分“自己的兼容入口”“公共 subprocess deployment 参数”“消费者导入 owner 内部模块”三种情况。

### StockWiki 来源 consumer

默认公司流程通过 `CompanySourceProvider` 获取来源索引、原件与 processed documents；来源选择失败不能悄悄回退扫描 `doc_root`。本地目录导入是显式 adapter，不是默认来源路径。[company_sources.py:1](C:/Users/郑曾波/Projects/StockWiki/stockwiki/company_sources.py:1)、[sources.py:521](C:/Users/郑曾波/Projects/StockWiki/stockwiki/sources.py:521)、[services/company.py:188](C:/Users/郑曾波/Projects/StockWiki/stockwiki/services/company.py:188)。

| 公开面 | 职责 | 禁止下沉/上移 |
|---|---|---|
| Company source index / exact source read ports | `CompanyIdentity` + pagination / SourceRef → pathless listing / verified bytes；配置可给独立 argv | StockWiki 不解析 CWP catalog、storage roots、原件物理目录；CWP 不接受研究结论写回 |
| `source_reader_v2` façade | `load_bundle`、`VerifiedOpenTransport`、`replay_text_locator`、`project_source_identity` | 只处理 versioned JSON/bytes。公开 `__all__` 见 [source_reader_v2.py:63](C:/Users/郑曾波/Projects/StockWiki/stockwiki/source_reader_v2.py:63) |
| `company-wiki-processed-document/1` consumer | source identity + ordered units/locators/parser/quality → StockWiki 文档 view | 原件格式检测、通用解析归 CWP；投资语义归 StockWiki。见 [processed_documents.py:1](C:/Users/郑曾波/Projects/StockWiki/stockwiki/processed_documents.py:1) |
| narrative transport | narrative request → immutable context/span view | 不复制解析或模型请求；公共 `read_narrative` 见 [narrative_source.py:94](C:/Users/郑曾波/Projects/StockWiki/stockwiki/narrative_source.py:94) |

`company_sources.py:327` 和 `_source_reader_v2_transport.py:206` 的 SHA 是各自公开字节入口验证，不是已证明的同一 buffer 重复校验缺陷；是否两条入口在某个完整流程被重复调用仍需行为计数验证。当前没有充分证据要求把它们合成新共享 SDK。

来源配置中的 CWP module 名 / `PYTHONPATH` 是子进程部署手段。`_explicit_commands` 支持替换命令，`_module_commands` 是默认实现适配，见 [company_sources.py:114](C:/Users/郑曾波/Projects/StockWiki/stockwiki/company_sources.py:114)。本次指定来源模块未发现 import CWP Python 包或打开 CWP SQLite；不能将此结论扩大到所有 StockWiki 历史脚本。

### Audit 组合器

最小公开面是版本化执行请求、capture/event/status 记录、review-evidence、summary-review-import/packet 和 numeric/financial-measure 诊断。Audit 自己拥有 `run.json`、角色日志、captures、冻结输入与 review artifacts，不拥有原件 catalog、RF publication 或业务调度库。

- `audit_run.capture` 包装用户显式传入的有界 CLI，保存真实开始/结束、退出和完整度；它不启动 agents、不证明模型正确。实际 `Popen` 在 [audit_run.py:815](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_run.py:815)。CLI 能发起哪个 owner 动作由任务与输入命令决定，不能把“审计器通常只读”误写成 capture 永远无副作用。
- `execution_request.py` 对 `revenue-forecast/business/1`、`filing-fetch/1`、`company-wiki/narrative-batch/1` 绑定请求与预算，见 [execution_request.py:156](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/execution_request.py:156)。它是既有 owner 请求的控制观察，不应复制 owner 下载/重试/计算。
- 已发布 `narrative-bundle/2.0` 或 `/3.0` → `summary-review-map/1` 的导入保留原 IDs、locator、原语言、support/context；不重新证明 CWP 原件身份或语义，见 [summary_review_import.py:1](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/summary_review_import.py:1)。
- `review_evidence` 只读显式 execution root 与允许的证据根，未知 locator 留 UNVERIFIABLE，当前 SHA 不冒充历史完整性，见 [review_evidence.py:1](C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/review_evidence.py:1)。这是读声明的审查附件，不等于任意扫描邻仓内部库。
- 指定 runtime scripts 的 literal scan 未发现 SQLite 连接、跨仓 Python dynamic import；`sys.path` 都指自身 skill scripts。没有 actual code finding 支持为 Audit 新建任务引擎或统一来源库。固定表示额度等历史行为可另列质量治理，不作为本轮模块解耦实现的前提。

### Dashboard 组合器及 IQS 只读接口清单

Dashboard 公开内部面已由 `ports/protocols.py` 描述：Identity、Universe、Source、Research、Forecast、Statement、QuickScan、Job。当前 ports 文件是既有 WIP，作为观察证据，不派新作者修改。业务层保留 Dashboard 自己的 saved views，见 [application/service.py:81](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/application/service.py:81)；未观察到另建 RF/CWP 业务状态数据库。

| consumer → owner | 当前调用面 | 状态/语义边界 |
|---|---|---|
| Source → CWP | source reader、public document/canonical browser、narrative transport CLI | 原件/解析/来源定位归 CWP；Dashboard 只作 wire 验证和传输。见 [adapters/cwp.py:60](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/cwp.py:60)、[:101](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/cwp.py:101)、[narrative.py:183](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/narrative.py:183) |
| Research / identity → StockWiki | `stockwiki.public_research_view_cli`、`dashboard_identity_bridge_cli.py` | 固定 argv，entity/listing/analysis-subject 绑定；见 [research.py:75](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/research.py:75)、[identity.py:117](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/identity.py:117) |
| Forecast → RF | report catalog read；comparison / verified-comparison CLI | owner 计算差额/可比口径，Dashboard 核对 exact report/lineage；[forecast.py:63](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/forecast.py:63)、[:219](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/forecast.py:219)、[forecast_common.py:124](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/forecast_common.py:124) |
| Statement → FF | `scripts/fetch_statements.py`，普通 browse 强制 reuse_only | schema/period/unit 显示映射不是下载引擎；未知语义不猜；[filing_fetch.py:352](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/filing_fetch.py:352)、[:386](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/filing_fetch.py:386) |
| Job → FF / RF / IQS | `ff-job/1`、`rf-job/1` 及 IQS 已有 job façade | command 的实际预算/恢复在 owner；Dashboard 不查询 owner job 目录；[m8_owner_jobs/rf_job.py:1](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/m8_owner_jobs/rf_job.py:1) |

`domain/metrics.py` 是对 owner 已发布 metric records 的 Dashboard 表达式功能，不是发现了第二套 RF forecast calculator。需要保留它对单位/口径/缺失值的合同测试，而不是见到 Decimal 运算便移入 RF。

IQS 本轮不审内部、不改代码，仅从 Dashboard adapter 记录已消费面：

- 协议：`iqs.dashboard.owner/1.0.0`、`stockwiki_w09_read_primitives` + `quick_scan_profiles/1.1.0`、`stockwiki.membership_request/1.0.0`、`iqs.dashboard.member_request/1.0.0`、`iqs.dashboard.company_assessment/1` + `company_assessment/1.0.0`，来源 [iqs/_shared.py:17](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/iqs/_shared.py:17)。
- GET：`/api/product/status`、`link`、`results`、`entity`、`history`、`company/result`、`company/history`、`universe`、`universe/request`、`universe/history`。
- 显式名单命令：POST `/api/product/universe/preview` 和 `/api/product/universe/apply`；这是 StockWiki canonical pool 的 IQS façade，不在 Dashboard 建另一名单 authority。调用定位 [iqs/universe.py:271](C:/Users/郑曾波/Projects/investment-dashboard/backend/dashboard/adapters/iqs/universe.py:271)。
- 以上只是 consumer 所用 subset，不是对 IQS 完整 API、运行可用性或当前服务版本的认证。

## 主仓与配置中的部署矩阵

主 RF 当前目录不存在 `scripts/report_catalog_compare_cli.py`、`report_catalog_verified_compare_cli.py`；主 StockWiki 不存在 Dashboard 使用的 `dashboard_identity_bridge_cli.py`。这仅表示上述主仓快照未提供全部 Dashboard 面。

只读选取 `config/b37-main.local.json` / `b35-main.local.json` 的 root/workspace/python/config 字段，未读取 `.env` 或输出凭证；观察到：

| 配置文件 | RF code / data | StockWiki code / workspace | CWP code / config |
|---|---|---|---|
| b37-main.local.json | Dashboard `.worktrees/b37-rf-release` / 主 RF | Dashboard `.worktrees/b34-sw-id-repair` / 主 StockWiki | Dashboard `.worktrees/b33-cwp-source-proof` / 主 CWP `config/source_catalog.yaml` |
| b35-main.local.json | Dashboard `.worktrees/b35-rf-lineage` / 主 RF | 同上 | 同上 |

该事实与 [Dashboard HANDOFF.md:58](C:/Users/郑曾波/Projects/investment-dashboard/.planning/unified-dashboard-2026-10-26/HANDOFF.md:58) / [:68](C:/Users/郑曾波/Projects/investment-dashboard/.planning/unified-dashboard-2026-10-26/HANDOFF.md:68) 一致。没有启动服务、测试这些 release roots、探测当前进程参数或审核其全量源码，因此**当前使用哪份配置、实际 release HEAD/安装 manifest、兼容性和当前服务健康仍未验证**。下一步由 ROOT/既有 D00 取一份准确部署 tuple，再通过公开接口做黑盒验证；不合并、清理或重新生成历史报告来凑主仓一致。

## 已确认发现、设计风险与未验证事项

| ID / 性质 | 证据与影响 | 有限处置 |
|---|---|---|
| R-01 已确认越界，局部 | [processed_artifact_canary.py:58](C:/Users/郑曾波/Projects/revenue-forecast/scripts/processed_artifact_canary.py:58) 打开传入 SQLite，并查 `artifacts` 私表；[:39](C:/Users/郑曾波/Projects/revenue-forecast/scripts/processed_artifact_canary.py:39) 复制 role-DAG；[installation_manifest.py:13](C:/Users/郑曾波/Projects/revenue-forecast/scripts/installation_manifest.py:13) / [:27](C:/Users/郑曾波/Projects/revenue-forecast/scripts/installation_manifest.py:27) 将 scripts 整体纳入 runtime 分发。不是 canonical 来源准备当前直读库的证据 | RF 独立卡：核对唯一调用面后，将工程诊断退出 runtime closure，或只消费 CWP 已有公开 diagnostic projection。不要在 RF 添加新 catalog/recompute owner。旧审查附件只读保留 |
| R-02 已确认表示耦合，兼容 profile | [report_catalog_research_attempt.py:256](C:/Users/郑曾波/Projects/revenue-forecast/scripts/report_catalog_research_attempt.py:256) / [:443](C:/Users/郑曾波/Projects/revenue-forecast/scripts/report_catalog_research_attempt.py:443) 读取 `roles/executor/events.jsonl` / captures；[research_identity.py:23](C:/Users/郑曾波/Projects/revenue-forecast/scripts/report_catalog_research_identity.py:23)、[:150](C:/Users/郑曾波/Projects/revenue-forecast/scripts/report_catalog_research_identity.py:150)、[:203](C:/Users/郑曾波/Projects/revenue-forecast/scripts/report_catalog_research_identity.py:203) 要求保留的 CWP native probe 与 `src/company_wiki/source_catalog` 形状。改文件布局会影响此 profile 的新 admission | 先给现有历史 profile 明确兼容标签。新 generalized admission 只在真实需求出现时走版本化 execution/export receipt，保留旧 reader；不篡改历史 bytes/hash，不把旧 profile 全面迁移作为解耦完成条件 |
| R-03 已确认内部责任混合，非运行缺陷 | [revenue_core.py:442](C:/Users/郑曾波/Projects/revenue-forecast/scripts/revenue_core.py:442) 运行时依赖 report validator，而 [revenue_report.py:9](C:/Users/郑曾波/Projects/revenue-forecast/scripts/revenue_report.py:9) 从 core 聚合导入领域函数；[revenue_forecast.py:38](C:/Users/郑曾波/Projects/revenue-forecast/scripts/revenue_forecast.py:38) docstring 同时声称 pure/zero-IO 和 formal 注册；formal 实际登记见 core:477 | 先补接口职责与副作用合同。若本轮用户确实要求内部独立测试，可在 RF 同一 owner 卡中把 report 对 core 聚合依赖改为已有 leaf API，保留 core 兼容 re-export；不改公式、schema、预测值，不新造第二 runtime |
| R-04 检测覆盖风险，未证实当前业务绕过 | RF [test_single_owner_guard.py:43](C:/Users/郑曾波/Projects/revenue-forecast/tests/test_single_owner_guard.py:43) 限 subprocess import/特定符号，却不覆盖外部 sqlite/storage；Dashboard [test_module_boundaries.py:10](C:/Users/郑曾波/Projects/investment-dashboard/tests/integration/test_module_boundaries.py:10) 的外部模块集只有 stockwiki/src，私库路径正则也只列部分 owner；当前 literal scan 没有发现 Dashboard 实际直读 owner 数据 | 先加真正能失败的正反例与 denied-storage 黑盒，不扩大成复杂静态安全分析。外部 API/opaque handles 允许，邻仓包导入/私库读取要可检测 |
| R-05 版本组合风险，运行未验证 | Dashboard source code 与主仓 owner HEAD 的公开面不同，但两份可见配置指定 release code roots | ROOT 记录 selected code root/HEAD/contract/state-root tuple，依既有 D00 卡验证；不报主仓缺入口等于生产失效 |

本次没有证明：当前 deployed runtime 能全部成功运行、所有历史/工具脚本零越界、Windows/Unix 两平台控制树恢复无缺陷、完整三市场业务验收、RF 预测有经济正确性。没有运行测试，以下仅是测试设计和已有测试源码证据。

## 已有隔离测试及后续 TDD 最小套件

| 范围 | 已有有价值的测试 | 仍需补证 / Red → Green 方式 |
|---|---|---|
| RF raw/narrative ports | [test_decoupled_source_port.py:16](C:/Users/郑曾波/Projects/revenue-forecast/tests/test_decoupled_source_port.py:16) 独立 argv，[:32](C:/Users/郑曾波/Projects/revenue-forecast/tests/test_decoupled_source_port.py:32) 不读取 producer config；`test_p5_source_default_v2.py` 默认 v2/legacy tripwire；`test_source_preparation_deadline.py`；`test_r1_source_boundary.py` 真实子进程 failure envelope | 新进程，仅安装 RF runtime，CWP 包不可 import、CWP data root 不可读；独立 stub port 返回有效/损坏 bytes，证明成功/命名失败，统计只调用一次 owner reader。配置入口 opaque 时不要求本地存在；actual caller budgets 保留 |
| RF runtime / model | `test_model_registry_contract.py`、`test_golden_behavior_lock.py`、`test_architecture_dependency_uses.py`；`test_source_consumption.py` | 不改算法的 split 先锁同一 frozen input 的 output、receipt、schema、error 分类；pure leaf 运行禁止网络/外部库/写文件；formal runtime 只允许自己指定 registry 写入。仅在改了责任依赖时加这些测试 |
| RF jobs / catalog | `test_rf_job_boundary_regression.py` 锁 9 reads/管理写面分离；`test_rf_job_recovery.py`、`test_rf_job_concurrency.py`、`test_rf_job_status_contract.py`、`test_report_catalog_rf_job_import.py` | owner-root 与 code-root 分离的新进程；read 不创建 job/catalog；resume 不重复已完成 source/download；未知付费完成不盲目重跑。现有语义不因解耦改写 |
| R-01 遗留诊断 | 单 owner guard 没有封住 SQLite 残余 | Red：安装 runtime closure 不应包含跨库 canary；或公开 diagnostic adapter 下 monkeypatch/禁止 sqlite3.connect，仍完成投影。Green：移出安装闭包或委托 owner。若无实际消费者，不新建公开服务 |
| StockWiki source | [test_company_source_wiring.py:1](C:/Users/郑曾波/Projects/StockWiki/tests/test_company_source_wiring.py:1) 真实 CLI + 独立 producer + 不存在 doc_root + scanner tripwire；`test_company_sources.py`、`test_processed_documents.py`、`test_source_export_v2_reader.py` | 先运行这些 focused suites。新增只在缺证时：provider 未配置/返回坏 schema 后不能退回邻仓目录；未知 optional observation 不提升为已审核；无改变则无需实现卡 |
| StockWiki 跨仓实物 | [tests/e2e/test_cwp_processed_document.py:1](C:/Users/郑曾波/Projects/StockWiki/tests/e2e/test_cwp_processed_document.py:1) 在 tmp 建真实 CWP catalog/fixtures，producer 只读，原件/输出在 tmp；缺环境时 skip 明确 | 一次大节点显式选择 producer code/interpreter/config，核实真实执行而不是 skip；保留 config/hash/dirty before-after。源码存在不代表本轮已通过 |
| Audit | `test_du6_summary_review_import.py` 保留 locator/原语言/support/context、同载体只读一次；`test_scope_request_binding.py` exact request/frozen input；`test_w08_root_evidence_boundaries.py` 事件和证据边界 | 自包含执行包被移动后仍能审查；未声明根 deny，未知 scheme 诊断；summary importer 禁 producer imports/DB/network；对于 R-02 先合同卡、后引入可替换 execution export，不先改 Audit 引擎 |
| Dashboard | AST [test_module_boundaries.py:192](C:/Users/郑曾波/Projects/investment-dashboard/tests/integration/test_module_boundaries.py:192) 和别名反例；`test_public_wire_boundaries.py`；`test_public_source_research.py`、`test_public_forecast_iqs.py`；`b35_lineage/test_read_boundary.py`；`preview_isolation/test_original_boundary.py` | 续既有 owner：补 company_wiki / revenue_* / filing_fetch 直接导入、动态文件导入和 sibling sys.path 反例；provider 根不可直接读时所有 browse 仍通过 stub ports；browse 调用计数 download=0/model=0/import=0；不得触碰现有 WIP |

每包先最小会失败的边界测试，再改唯一责任层，再复用已有受影响 tests；跨仓真实隔离套件在大节点执行一次。不要每个小 helper 变更都加全链研究、部署或人工签收。禁止把 mock 通过当真实 deployment 通过；同样禁止把研究质量缺口塞入架构退出条件。

## 可派发路线与互斥写集合

本轮只制定卡，不启动实现。原则：各仓独立 worktree，保护主仓已有 WIP；跨仓 contract 由 ROOT 顺序冻结，消费者并行实现时不得改 owner 合同。目录互斥不等于全仓同时无限测试。

| 卡 | 是否建议立刻建立实现卡 | 独占可写集合 / 互斥 | 依赖与退出 |
|---|---|---|---|
| RF-BOUNDARY-01 | 是，范围小 | RF `scripts/processed_artifact_canary.py`、`scripts/installation_manifest.py`、相关 runtime closure/单 owner guard tests、对应 references。只允许一个 RF packaging owner；不写 assurance/runs WIP | 确认使用者后移出 runtime 或公共委托；安装闭包不再认识 CWP SQL/DAG。无新数据服务，无来源结果变化 |
| RF-API-02 | 条件卡；先 API 清单/依赖合同，用户确需内部独立测试时实施 | RF `scripts/revenue_core.py`、`revenue_report.py`、`revenue_forecast.py`、受影响 tests；不得与其他 core/report 修改并行。不能与 RF-BOUNDARY-01 同时改 `test_single_owner_guard.py` | leaf/calculation 与运行副作用明确；旧公开 imports/CLI 保持；golden 值/receipt/schema 不变。预测质量另行 |
| RF-AUDIT-CONTRACT-03 | 先设计卡，不立即造 export | RF `report_catalog_research_*` 的兼容 profile 描述与 Audit execution-export reference；真实 generalized admission 需求确认后，先 ROOT 固定 schema，再 RF/Audit 各自一包 | 历史 B34 仍可读取；新合同不要求 CWP内部模块/安装布局；不给旧 bytes 重新签收或迁移。`report_catalog.py` / CLI 归 RF catalog owner 串行整合 |
| SW-SOURCE-CHECK | 当前只需 ROOT 黑盒验证 | 不改 StockWiki；如 focused suite 暴露实际问题，再开 source consumer 卡，范围 `company_sources`、`sources`、`processed_documents`、`source_reader_v2*`、对应 tests；避开 quick_scan/IQS 共享模块 | 证明 provider 可替换、无目录 fallback、source identity/locator 保持；现有测试足够且通过即可无代码退出 |
| AUDIT-CHECK | 当前只需 ROOT 黑盒验证 | 不改 Audit；若发现 export 耦合新需求，另开 `execution export` 薄适配卡，不动整套 `audit_run.py` 作为默认方案 | 自包含审查附件搬迁可读、无 producer imports/DB、unknown 不升级；没有 actual finding 就交付无改动理由 |
| DASHBOARD-OWNER-CONTINUE | 否，不派竞争包 | 接续 D00/既有 owner 卡；本轮无 write set。尤其不改既有 4 个 tracked WIP；ports/schema/shared factory 由既有合同 owner 串行 | 精确部署 tuple 和公共黑盒验证。需要补 AST guard 也交既有 owner，不建立第二 Dashboard 计划 |
| IQS | 无 | 零源码/配置写；仅接口清单 | 本轮不做 IQS 内部解耦、合并、测试或新的验收门 |

建议顺序：ROOT 固定仓库/部署 baseline 和公开面 → RF-BOUNDARY-01 与各仓只读黑盒准备可并行 → 大节点执行已选公开合同/隔离 tests → 有实际失败才开 SW/Audit 实现卡 → Dashboard 由既有 owner 提交接续结果 → ROOT 独立复核“跨仓不可读时仍可经公开面工作、owner 状态不被消费者写、旧兼容可读”。

最终完成判定限于：职责可说明、公开面可替换、私有状态不可被邻层直接读写、schema/error/budget/recovery 保持、该次涉及代码的必要测试通过、WIP 未被覆盖。代码行数、空目录拆分、文档数量、全仓统一 SDK、生产部署和 RF 预测准确率都不是本次解耦的替代标准。
