# 来源目录、原文读取与有限叙述批次

> 当前接口说明（2026-10-05）。进度及存储迁移顺序见[主计划](plans/narrative-evidence-pilot-2026-09-26/task_plan.md)，接口定义见 `docs/contracts/`。历史实现可查 Git，不按旧常驻 Worker 的流程操作。

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
| legacy artifacts / spans | 旧 normalized、summary、sections 与全量 span；仍有读者时保留 |

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

旧source-catalog `evidence`、`evidence-list`、`sections-list`及公共EvidenceQueryService导出也已退出。明确历史backend仍能读隔离fixture；新运行精选检索不依赖旧SQLite全量span，实际旧数据尚待S6处置。

`worker-status`、`worker-stop`、`startup-status`、`uninstall-startup` 仅用于检查和收尾既存旧进程/任务，不启动新常驻转换。低层 legacy generators 和读者尚在迁移；本页不声称这些模块全部删除。

`.source_catalog/derived` 和旧全量 EvidenceSpan 尚未清理。RF 默认消费切换、CWP 旧正文读者退出、artifact 退休状态和质量语义完成后才删旧物理产物；数据库 span 与压缩单独验收。不删除原件，不保留指向已删文件的 completed 句柄，不要求把所有历史来源重新跑一次模型。
