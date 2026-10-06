# company-wiki

StockWiki 等研究项目的上游资料系统：保存原始文档和来源事实，按需提取业务叙述，提供可回放的证据和只读接口。

## 当前工作流

1. 登记或获取公司文档，原件保持原语言、不可变保存。
2. 根据文档类型选择主营业务、行业变化、新业务、出海、产能及项目进展。财务表格和通用格式化材料不全量切片。
3. 有限 Worker 批次临时解析，生成一份精选引用与来源摘要；已完成任务清除重复正文。
4. 下游用 SourceRef / SourceExport v2、NarrativeRef 读取；存在哪个目录由存储层处理。

company-wiki 不写 StockWiki 的目录或数据库，不生成评级、目标价、仓位、估值或正式研究报告。

## 安装与配置

需要 Python 3.10+；开发和 CI 使用 requirements 文件：

```powershell
python -m pip install -r requirements.txt -r requirements-test.txt
python -m pip install -e .
python scripts/config_doctor.py
```

来源根配置在 `config/source_catalog.yaml`，provider 配置在 `config/source_acquisition.yaml`。模型经现有 `Config.load` 加载，沿用 `config.yaml`、供应商配置和环境变量，不另造密钥文件。MiMo 使用 `mimo-v2.6-flash`，DeepSeek 使用 `deepseek-flash`；实际端点和生成参数由配置决定。API key 不写进请求、报告或 Git。无需模型的来源查询和原文读取不需要 LLM 凭证。

## 来源登记与读取

```powershell
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan --dry-run
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml status
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml query "中微公司"
python -m company_wiki.source_catalog.source_export_v2_cli --help
python -m company_wiki.source_catalog.source_reader_cli --help
```

`scan --dry-run` 是可选预览，`scan` 登记来源。上层使用逻辑 ID/hash，不直接遍历各存储目录。精确原文 reader 的 stdout 是字节，stderr 是收据；消费者检查 exit 0、SHA 和字节数。

下载优先通过 filing-fetch 的明确公司/期次请求，复用现有原件；A 股使用 StockInfoDLSimple，电话会调用 earnings-transcripts 并入库到公司目录。Dayu 是外部项目，不修改其代码。CWP 的 `ensure --help` 列出底层入口；`--allow-download` 选择获取模式，须同时给字节、时间、费用上限，不需要人工签收文件。

## 有限叙述处理与检索

```powershell
python scripts/narrative_batch_configured.py --llm-provider mimo --project-root . --catalog-config config/source_catalog.yaml --automation-db .source_catalog/automation.sqlite3 --work-dir .source_catalog/narrative-work --request request.json
python -m company_wiki.source_catalog.narrative_transport_cli --help
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml extraction-quality --help
```

批次需要符合已有 schema 的明确请求，限定 sources、并发 profile、时间和累计 token/费用。子 Worker 各持自己的客户端，共享持久预算；未知 usage 保留预留，重启复用已有 run，不重复生成 final。provider 通过 wrapper 参数显式选择；不能把配置里的备用模型当作已实现的自动 failover。

精选 list/lookup/search 在固定版本上验证原文 SHA 并回放 locator；搜索只建内存 BM25。未处理资料可以保持 `metadata_only`，完整检查确无业务叙述后才标记跳过，不把解析失败当成功。

详细请求、读取合同与恢复步骤见[来源目录说明](docs/source-catalog.md)、[运维说明](docs/OPERATIONS.md)、[架构](docs/ARCHITECTURE.md)和[主计划](docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md)。

## 测试与维护

commit 只做相关静态检查；push 跑一组快速行为测试，CI 跑全 Unit 与同组 smoke。完整集成、真实资料 E2E 在大的实施节点运行，测试根恢复原样；不要求 Reviewer、授权 JSON 或人工 lock。

2026-10-06 旧 derived 与全量 span 清理已完成，来源库降至约 222MB，原件保留。详情见[生产清理结果](docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)。不要求历史来源全部重跑模型。N4C 真实模型批次仍按主计划推进，不能把 Replay 或工具测试当作实际 LLM 验收。

旧 collect_news、ingest、研究 Wiki writer、全库 normalize/summarize、常驻 Worker 启动及旧 cron 包装器均不作为运行入口。旧 Source Export v1 合同供显式兼容；新消费者默认 v2。
