# W19 已知调查

新浪公开JSON接口真实可用；完整调查及18份175785B夹具在CWP本计划inputs/research。中微三表36/33/36期，9729源行，不等于全部经过财务审计的事实。publish_date可能是后来更新日期；不能用当前快照冒充过去PIT。FF薄调用、CWP唯一provider/存储，不建新身份库/人工许可或LLM流程。当前没有产品实施/验收。

## 2026-10-25 A节点勘察（作者实测，均可复核）

### 夹具验证（已完成）

- 18份 `.json.gz` 的**解压后字节 SHA-256 与 `inputs/research/capture/observations.json` 逐条记录的 `sha256` 全部一致（18 OK / 0 bad）**；`.gz` 文件字节 SHA 与 W19-setup.json seed_files 一致（18 OK）。解压总字节 2,572,006。
- `sh688012-lrb-type0-page5` 与 `sh999999-lrb-type0-page1-num1` 是同一空页形状：`{"result":{"status":{"code":0},"data":null}}`（61字节gz）。

### 新浪响应精确形状（normalize 的输入契约）

- 顶层 `result.status.code`（int，0 不充分）；`result.data` 可为 null。
- `data.report_count` 是**字符串**（如 "33"）；`data.report_date` 为 `[{date_value:"20260630",date_description:"2026半年报",date_type:2}]`；`data.report_list` 为 dict：period(YYYYMMDD) → `{rType:"合并期末",rCurrency:"CNY",data_source,is_audit,audit_opinion,publish_date:"20260820",update_time:1787134205(int),is_exist_yoy,data:[...]}`。
- 行：`{item_field,item_title,item_value,item_display_type,item_display,item_precision,item_group_no,item_source,item_tongbi}`；`item_value` 是十进制字符串、null 或空字符串；`item_tongbi` 是 float 或 ""（同比，非数值主数据）。
- fzb 每期 141 行，其中 **5 行 item_field=""（分组行，item_value 同为 ""）**；lrb 77 行；llb 64 行。美的 lrb 77 行、平安 76 行、招行 fzb 144 行——行数因公司而异，不能硬编码。
- `item_precision` 观察到 `f2`/`ps4`；**ps4 同时出现在 BASICEPS/DILUTEDEPS（真每股）和 MINYSHARINCO（少数股东其他综合收益，CNY 金额）**——精度绝不是单位信号；单位只能按字段+标签证据小映射，其余 unknown。
- type=4 num=2 实测返回最近 2 个年报（20251231/20241231），report_count=10。
- JSON Pointer 例：`/result/data/report_list/20251231/data/7/item_value`。

### CWP 接缝事实（基线 243993d2 + seed a3083502）

- `store.py:26` `_UPGRADEABLE_SCHEMA_VERSIONS = {"1.0.0","1.1.0"}`；`models.py:11` `CATALOG_SCHEMA_VERSION="1.2.0"`。升级链：`_initialize`（store.py:1174）BEGIN IMMEDIATE → `_execute_catalog_ddl`（按行 execute，不 executescript）→ `_apply_additive_migrations`（store.py:1213，fail-closed 未知版本）→ bump。加 1.3.0：两表进 `_DDL` + 1.2.0 加入 upgradeable 集合即可；`_expected_catalog_structure` 内存编译自动覆盖新表。`read_pipeline_status`（store.py:576）是**只读不建库**查询先例（mode=ro + query_only）。
- `canonical_writer.py`：`import_shared_original_staged`（:393）是"已验证元数据+原始字节"第三方入口先例——staged 在 staging_root 内、SHA/size 校验、`_commit_staged` 唯一提交算法（dedup by content SHA、`_existing_original`、原子 copy、`.source.json` 不可变 sidecar、`register_catalog_sources`）。新入口照此加 `_ThirdPartyOriginal` + intent（带 entity 属性），`reactivate_retired=False`，provider 绝不 official。`_destination_subdirectory`（:99）需加 `financial_statement_dataset → financial_statements`。
- `document_kinds.py SIDECAR_KIND_MAP`：scanner `_classification`（scanner.py:126-131）**只认映射内 sidecar kind**，否则走关键词启发。必须登记 `"financial_statement_dataset": (SourceType.OTHER, ...)`（source_contract SourceType 有 OTHER，无需新家族）。`PERIODIC_DOCUMENT_KINDS` 不加（多期间数据集无单一 FY）。
- 公司识别唯一 owner：`security_identity.py` `SecurityIdentityResolver.identify` + `load_identity_master`；CLI 子命令 `cli.py identify`（cli.py:1010，输出 IdentityResult.to_dict()）。CN 快照（生产 cn.json，6137 条）：exchange ∈ {SSE,SZSE,BSE}，security_id=6位码 → Sina paperCode 映射 **SSE→sh / SZSE→sz / BSE→bj**；BJ 未实测（A节点补有界真实样本或 named gap）。
- 预算/有界HTTP：`download_budget.py AcquisitionBudget.from_limits(max_response_bytes,max_seconds,max_cost_usd)`（deadline 单调钟、ensure_new_request、record_reported_usage）；`bounded_http.py BudgetedHTTPTransport(httpx transport,budget)`（identity 编码、逐块计数、ProviderBudgetStop 命名停止；MockTransport 测试先例 tests/unit/test_bounded_http.py）。
- `SourceRef`（source_reader.py:78）：document_id/source_id/content_sha256/byte_size/mime_type/schema_version="2.0"；`SourceVersionReader.query_ref(document_id,source_id,sha)` 纯 SELECT。SHA 验真属 reader 责任层。
- 配置：`config.py load_catalog_config(path)` 读 yaml（schema_version '1.0'、catalog_dir、roots）；CatalogConfig.database_path = catalog_dir/catalog.sqlite3；security_master 默认在 catalog_dir/security_master。
- 测试先例：`tests/contract/test_source_catalog_schema_migration.py`（回退版本再重开断言升级+旧数据保留+未知版本 fail-closed）；subprocess CLI 测试 `test_source_version_reader_cli.py`（PYTHONPATH=src、`python -m company_wiki.source_catalog.<mod>`、路径不泄漏断言）；`import_shared_original_staged` 测试 `tests/integration/test_official_json_capture_provenance.py:226`。根 conftest autouse 封网（socket.connect 阻断），真实外网测试需显式解封并走 `real_data`/自有标记。

### FF 接缝事实（基线 e0d9642 + seed c8b0e40）

- CWP 子进程命令构造：`fetch_filing.py:1212` `[sys.executable,"-m","company_wiki.source_catalog.cli","--config",str(root/"config"/"source_catalog.yaml"), <subcommand>...]`，cwd=root、PYTHONUTF8=1、`_run_bounded_json`（ff_process_transport.run_bounded_json：单 deadline、stdout cap 32MiB、UTF-8 严格）。identity 走同一 cli.py `identify --query [--market --exchange]`。
- 配置：`ff_configuration.load_connection_root(config_path)` → company_wiki_root（要求含 config/source_catalog.yaml）；company_wiki.json 仅 schema_version/company_wiki_root/可选两项。
- 错误/信封：`filing_contracts.FilingFetchError(code,stage,...)`；ff_v2_envelope 纯序列化。fetch_statements 用自己的 `financial-statements-request|response/1`，不碰 filing 信封。
- FF 测试先例：stub `_run_bounded_json`（tests/support.bounded_side_effect）；fake CWP 真子进程 `tests/fixtures/s3_fake_cwp/` + PYTHONPATH 指向临时包；真 CLI e2e `e2e/test_source_ref_v2_cli.py`（PYTHONPATH 指真实 CWP src、自建合成 wiki、--config launcher）。pyproject：pythonpath=["scripts","tests"]，无 markers。
- SKILL.md 结构：Command/Request/Response/Exit codes 分节 + bash 示例风格（SKILL.md:103-253 模板）。

### 设计决定（A节点冻结）

1. 每个新浪分页响应=一份不可变 canonical 原件（JSON），dedup by content SHA；报表版本引用其所在页的 source_id/document_id。全历史中微=12页→12原件（首次），同内容刷新不再新增。
2. 业务版本 canonical hash 覆盖：规范化行+period_end+statement_type+consolidation+currency+provider publish_date/is_audit/data_source；**不含 update_time/HTTP时戳/retrieved_at**——仅 update_time 变化时更新既有版本行的 provider observation 列（last_checked/provider_update_time），不新建版本；内容变化保留旧版本新增新行。
3. value_kind：`numeric|null|empty|non_numeric|group`（fzb 分组行=group，空field+空值）；unit 默认 `unknown`，仅证据字段（BASICEPS/DILUTEDEPS→`CNY/share`, scale=1）标注；scale 未证明=NULL。Decimal 全程字符串，SQLite TEXT。
4. period_kind 由 period_end 月日推导（0331→q1,0630→semi_annual,0930→q3,1231→annual）；balance_sheet 语义 instant，income/cash 为 duration 且 **period_start=NULL**（provider 未声明起始日，不猜年初累计）；provider date_type/date_description 原样保留。
5. consolidation 由 rType 映射：含"合并"→consolidated；含"母公司"→parent；否则 unknown。修订/口径不同不得同键覆盖（unique 约束含 consolidation+hash）。
6. 查询只读路径绝不构造 CatalogStore（不建库不迁移）：sqlite mode=ro+query_only，缺库/缺表→named gap；写路径（采集/重放）才初始化 store（触发 1.2→1.3 迁移）。
7. CWP CLI：`python -m company_wiki.source_catalog.financial_statements.cli --wiki-root <root>`，stdin 请求 JSON、stdout 单响应 JSON；识别在 CWP 内一次完成（复用 security_identity + catalog security_master 快照）。
8. FF：`scripts/fetch_statements.py --config <company_wiki.json> [--request-file f]`（stdin 可选），薄转发+请求校验+响应透传（校验 schema_version/status 词汇），退出码 0=有信封（complete/partial/not_found/unavailable），2=request/config 错。
9. 留 provider 边界：provider registry 只含 sina_finance；不为其他市场/供应商扩。
