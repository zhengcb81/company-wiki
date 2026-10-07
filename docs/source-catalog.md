# 来源目录、原文读取与有限叙述批次

> 当前接口说明（2026-10-06）。进度及存储迁移顺序见[主计划](plans/narrative-evidence-pilot-2026-09-26/task_plan.md)，接口定义见 `docs/contracts/`。历史实现可查 Git，不按旧常驻 Worker 的流程操作。

## 职责与存储

company-wiki 保存来源身份、不可变原件 SHA-256、来源版本与位置，提供资料检索、精确原文读取及来源叙述。不包含投资结论，不生成评级、目标价、仓位、估值或正式研究报告；这些由下游研究项目负责。

扫描只登记原件，不要求先转成整篇 Markdown。上层通过 SourceRef / SourceExport v2 访问来源；多个目录只是存储适配细节。相同字节归为一个 source，不把同内容的每个物理位置重复解析和摘要。原件保持原语言，不翻译。

默认配置 `config/source_catalog.yaml` 使用 `${PROJECT_ROOT}` 和 `${USER_PROFILE}` 定位公司资料、Dayu portfolio 与 Dropbox 来源。测试必须使用独立配置和临时根，不修改生产配置。外部根只读；新下载的 canonical 原件由本项目 acquisition writer 导入自己的公司目录，Dayu 源码与长期 workspace 不修改。

| 对象 | 含义 |
|---|---|
| sources / source manifest | 原件字节 SHA、身份、来源版本和公开日期等事实 |
| locations / roots | 受配置管理的物理位置；上层不依赖这些路径 |
| documents | 逻辑文档及其来源状态、类型、期间、实体 |
| EvidenceSpan | 绑定 source ID、locator、parser/version 和质量的可回放片段 |
| NarrativeRef / final 包 | 有限任务生成的精选片段和原语言来源摘要 |
| legacy artifacts / spans | 旧生成记录已退休，全量span已清除；不重建整篇派生 |

## 常用来源命令

以下命令使用同一配置入口。`scan --dry-run`、query、resolve 和原文读取可用于调查；明确下载请求还应提供公司、期间、as-of 及现有资源限制，详细参数以各命令 `--help` 为准。

```powershell
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan --dry-run
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml status
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml query "公司名"
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml resolve --help
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml ensure --help
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml export
```

`ensure` 先查询、发现、再查 provider 身份，下载到隔离 staging 后由 CWP 复核实际原件 SHA/MIME/字节数，去重后导入并登记。CNINFO 使用 StockInfoDLSimple 的有界接口；没有硬限额能力的 provider 不能冒称实现了该能力。原件已存在时复用 SourceRef，避免重复下载。

证券身份由已有官方身份快照匹配；有歧义时返回候选。来源 SHA、公司、期间和公开日/as-of 的一致性仍由各层自动验证，不新增人工签收文件。

## 有限叙述批次

年报、半年报、季报、招股书、增发/可转债、投资者关系记录和电话会按任务选择业务片段。财务表格及通用政策不要求生成全文切片；完整扫描确认没有业务叙述时可标记 `skipped_no_narrative`。未完整扫描或解析失败不能伪装为跳过成功。

正式入口读取一个明确的请求文件，任务限定来源、并行 profile、运行时间和 token/费用上限：

```powershell
python scripts/narrative_batch_configured.py --llm-provider mimo `
  --project-root . --catalog-config config/source_catalog.yaml `
  --automation-db .source_catalog/automation.sqlite3 `
  --work-dir .source_catalog/narrative-work --request request.json
```

请求 schema 与恢复步骤见[N4施工细则](plans/narrative-evidence-pilot-2026-09-26/n4_production_batch_implementation.md)。此示例需要已有合法请求，不负责自动生成或无限循环下载。

模型、端点、凭证和生成参数必须经现有 `Config.load` 加载。当前 MiMo 为 `mimo-v2.6-flash`，DeepSeek 为 `deepseek-flash`；DeepSeek 使用环境变量密钥，`.env` 只补缺。`--llm-provider` 是显式选择，未实现的自动 failover 不能当成已有能力。API key 不写入请求、收据或 Git。

每个子 Worker 持有自己的模型客户端，模型并发与解析并发分别有界。持久预算在调用前预留，已知 usage 结算，未知响应保留最坏预留。任务按 run/generation 恢复；相同 run 重启复用已提交结果，ACK 丢失不生成第二份 final。成功后保留小型 final 与恢复事实，释放临时解析内容，不永久复制全文。

## 精确证据与质量读取

```powershell
python -m company_wiki.source_catalog.narrative_transport_cli --config config/source_catalog.yaml --help
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml extraction-quality --help
```

正式 `narrative_transport_cli` 使用已有NarrativeReadRequest从stdin读取，提供 `--operation evidence-list`、`evidence-lookup`、`evidence-search --query "海外"`。先验原件SHA并回放全部引用，再对固定NarrativeRef版本列片段、精确定位或用BM25搜索精选原文。lookup不做模糊匹配，list/search默认100、最多500，使用`--offset`分页；不建立磁盘全文索引。stdout是来源view，stderr小收据含该view SHA/size，消费者须验证。具体输入、输出、失败与示例边界见[精选检索v1](contracts/narrative-evidence-view-v1.md)。

`extraction-quality` 是只读来源/解析质量接口（v2）：优先校验有界精选叙述包，迁移期间兼容未退休的旧提取记录；未请求或已退役为 `metadata_only`，策略跳过为 `skipped_no_narrative`。不返回正文、摘要、路径或投资判断，不打开旧 normalized 文件，不触发全文转换。`review_required` 只是技术诊断；实际消费仍通过正式 reader/transport 验原件SHA并回放引用。详细边界见[Extraction Quality v2](contracts/extraction-quality-v2.md)。

## 重复、指纹与维护

- 字节 SHA 完全一致的位置为 exact copies；原件 canonical 必须保留。
- 归一化文本指纹相同而字节不同的 semantic copies 仅展示，不自动删原件。按需 `fingerprint-backfill` 从 raw 取文本后只保存小型指纹，不重建整篇 Markdown。
- `export` 按需生成可再生索引，不是常驻第二套库。
- archive/prune、focus-cleanup 和其他 legacy 维护命令仍以实际 CLI 为准，不列为新的日常运行流程。

## 已退役与迁移中

公开 CLI 不提供整库 `normalize`、`summarize`、`run`、旧 Worker 启动/恢复及安装登录任务。`SourceCatalog.normalize`、`summarize`、`summarize_with_llm`、`extract_sections` 也已退出；历史隔离测试通过 `tests/support` 准备旧产物，不能从生产代码导入该夹具。

旧source-catalog `evidence`、`evidence-list`、`sections-list`及公共EvidenceQueryService导出也已退出。明确历史backend仍能读隔离fixture；新运行精选检索不依赖旧SQLite全量span，生产旧数据已于2026-10-06清理。

`worker-status`、`worker-stop`、`startup-status`、`uninstall-startup` 仅用于检查和收尾既存旧进程/任务，不启动新常驻转换。旧全文generators已退出生产安装包；历史夹具只在tests/support准备，不能从生产代码恢复旧writer。

RF默认SourceRef v2迁移、CWP旧正文读者退出及质量语义已经完成。生产`.source_catalog/derived`的7104文件已清零、1490530旧span已删除，8191旧handle退休；来源库约222MB，原件及17表来源事实保持。见[正式结果](plans/narrative-evidence-pilot-2026-09-26/harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)。不要求把所有历史来源重新跑一次模型，N4C真实批次仍按主计划推进。

### 只登记指定原文

新增原件或修补已核实的来源元数据时，使用单根有限登记。它保留所选文件整个来源/sidecar组，只查询所选位置，不遍历外根，不将未选文件标missing，也不推进完整扫描水位。relative-path使用根内正斜线相对路径；不接受空范围或越界路径。完整根盘点仍使用原scan。

```powershell
python -B -m company_wiki.source_catalog.cli --config config/source_catalog.yaml register --root-id company_raw --relative-path "公司名/raw/文件.pdf"
```

canonical import自动使用此入口；消费者仍仅使用SourceRef，不操作物理路径。

### 结束历史灰度切换

当前来源库使用runtime-policy schema 2.0 `steady`：仅保存`schema_version`、`mode`、根配置`policy_hash`、`updated_at`和自身`snapshot_sha256`，没有六个灰度flag、epoch/cohort权限条件。用既有`runtime-policy apply --file <payload.json>`原子CAS迁移；原始assertion/location/activation审计不删除，配置hash与字节SHA复核仍保留。

steady读取已生效的active/legacy verified断言（hash须匹配当前来源），排除shadow/candidate/rejected。已验证断言字段优先，旧capture只补缺项；原件不因缺人工审查而不可读。历史schema 1.0仍可解释旧迁移测试/记录，生产不再以它控制新流程。

有限叙述批次在AUTO SQL层按event/job IDs查询；已完成的同run恢复验证原文/产物和费用，但不启动子进程或重发模型请求。一个文档的发现、登记与读取不触发全库盘点。
