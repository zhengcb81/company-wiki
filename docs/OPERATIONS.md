# 当前运维说明

> 2026-10-06。参数以实际 CLI help 为准；旧流水线和人工签收流程不再适用。

## 来源与获取

运行现有来源配置，不修改外部 Dayu 或下游研究库。独立测试使用临时配置，不写生产配置。

```powershell
python scripts/config_doctor.py
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml status
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan --dry-run
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml resolve --help
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml ensure --help
```

`scan` 登记原件；dry-run 是可选预览。明确下载通过 filing-fetch 请求公司、市场、期次和 as-of，并给 acquisition_limits。底层 CWP 示例：

```powershell
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml ensure --entity "公司名" --document-kind annual_report --as-of-date YYYY-MM-DD --fiscal-year 2025 --source-ref-v2 --allow-download --max-download-bytes 20000000 --max-download-seconds 60 --max-download-cost-usd 0
```

示例占位公司/日期须换成实际值；上限是示例，不会自动修改生产预算。未给 `--allow-download` 的 exact 查询只复用/返回缺口；latest_as_of 提供元数据缺口计划。开关选择操作模式，资源上限约束执行，不是第二次人工审批。来源有歧义返回候选，不能猜身份或公开日期。

CNINFO 使用 StockInfoDLSimple。电话会经 earnings-transcripts，原始 TXT/JSON 由 CWP 校验后统一入库，不翻译。无 provider 权益或硬预算能力时如实返回失败，不伪造 live 成功。

## 原文、导出与精选读取

```powershell
python -m company_wiki.source_catalog.source_export_v2_cli --help
python -m company_wiki.source_catalog.source_reader_cli --help
python -m company_wiki.source_catalog.narrative_transport_cli --help
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml extraction-quality --help
```

SourceRef / SourceExport v2 不暴露物理路径。原文 reader 输出真实字节；Narrative transport 输入版本化请求，返回固定来源/摘要版本，先验原件 SHA 和 locator。调用者同时检查退出码、收据、stdout hash/size。精选 list/search 支持分页，lookup 精确匹配，不创建持久全文索引。

## 处理、恢复与空间

有限叙述批次的真实命令和配置规则见[来源目录说明](source-catalog.md)，请求字段、共享预算和恢复步骤见[N4实施细则](plans/narrative-evidence-pilot-2026-09-26/n4_production_batch_implementation.md)。

不要共享旧 LLMClient 到多个线程。新 Worker 用隔离子进程，每个子进程持自己的客户端；Store 统一租约、generation、预算预留和 outbox。恢复时使用原 run 和原请求，不为逃避 unknown usage 新建预算账。只在 final 可见且恢复材料已无需要后清临时正文。

已选来源用`SourceVersionReader.read_policy_sha256(ref)`生成schema3精确读取pin：只绑定该文档来源事实和相关根有效读取规则，不绑定资料库/原件的物理路径或无关根。移动既有DB/objects及同SHA原件后，当前配置仍须指向正确位置；每次open重新核验路径包含、准入、实际SHA和长度。新批次保存binding/2的逐document pin，终态恢复复用原事件、摘要、费用与storage baseline，零新模型调用。

无参数`read_policy_sha256()`仍是schema2全局选源身份；旧binding/1只有不可逆全局SHA，当前全局规则相等时按原绑定读取，改变时返回`BATCH_READ_POLICY_CHANGED`。旧记录不自动改签/重跑/重置费用；没有binding或schema1旧pin则明确不可验证。查询候选与exact读取的两种身份不能混用。

旧 derived/span 与生产库收缩已经完成，见[正式结果](plans/narrative-evidence-pilot-2026-09-26/harness_lanes/results/s5_production_storage_acceptance_2026-10-06.json)。不要重新执行旧清理脚本或全库解析。原件、来源版本/撤回事实、新 final 保留。维护工具说明在 [legacy_storage](../tools/legacy_storage/README.md)，未知对象不自动删除。

`worker-status`、`worker-stop`、`startup-status`、`uninstall-startup` 只清理既存旧任务，不启动常驻转换。旧 cron 包装器已删除。

## 验证与发布

Store 日常打开只验证当前版本、必要表/列/键及 AUTO singleton，不对所有业务数据做深检，也不把结构通过表述为整库健康。新建和真实升级在同一事务提交前做一次 integrity/FK 检查；升级失败回滚。当前来源库打开不执行DDL或全量fingerprint seed，无state的新文档仍按pending选择并在自身事务UPSERT。账目读取只校验当前run的字段，再做精确计算；损坏记录失败，不能转为零费用。

显式AUTO数据库体检使用`company_wiki.automation.migrations.validate_database(path)`或`AutomationStore.schema_report()`；只查版本/结构使用`inspect_schema(path)`，返回值没有integrity_ok字段。体检放在相关大节点或确实怀疑损坏时，不放进每个Worker构造、预算查询或终态恢复。

- commit：相关 Ruff、类型/配置和路径静态检查，不跑 pytest。
- push：`python tools/pre_push_gate.py --fast-contracts-only`，与 CI 同一快速集合。
- CI：全 Unit、同组 smoke 和静态检查，单 Python 环境。
- 大节点：一次有关集成/真实资料 E2E；临时根结束恢复原样，真实 LLM/API 使用配置及已有预算。

不需要独立 Reviewer、授权文件、签收锁或每个 helper 的审查。自动检查仍覆盖实际 SHA、来源身份/期间/as-of、引用、原件不可变、资源上限及任务恢复。Source-only 职责是产品边界，不能用旧 research writer 绕过。
