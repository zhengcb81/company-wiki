# 公开来源接口组合验收

本目录由 company-wiki 的 ROOT 维护。RF、FF、StockWiki、ET、AUDIT 的普通测试只使用本仓公开协议、便携样例和可替换端口；它们的 CI 不检出 company-wiki，不读取它的库或配置布局。真实组合在这里单独执行。

## 当前入口

```powershell
python tools/run_source_system_tests.py --rf-root ../revenue-forecast --ff-root ../filing-fetch --et-root ../earnings-transcripts/earnings-transcripts --stockwiki-root ../StockWiki --output-dir .planning/source-system/current
```

所有 checkout 均显式提供。没有配置 StockWiki 时报告明确只验证 RF，不将它冒充双消费者通过。StockWiki 当前没有 remote，所以云端组合不虚构该仓的检出或测试。

默认清单只含当前公开链：RF 准备 → FF 查询/复用/采集 → CWP；真实 ET CLI/worker 与假 HTTP → CWP 原文入库 → verified-open；原文/摘要端点替换；当前生产者和上一便携样例的协议正反例。实际网络仅允许测试自建 loopback，provider 由夹具替代，不调用模型。22MiB 请求允许大于17MiB的合法原件，并验证实际16MiB超额、SHA/身份错误、未知发布日期和再次零下载。

`report.json` 记录参与 HEAD、源代码工作差异、实际测试清单、消费者集合、结果和清理状态。`pytest.log`/`junit.xml` 记录失败位置。临时湖、下载原件、缓存都在唯一短临时根内，成功或失败后删除。`--tests` 可只复验受影响节点；不反复重跑超时全批。

## 旧断言的去向

RF 的25个整文件迁移表在 [revenue_forecast/migration.json](revenue_forecast/migration.json)；FF 整文件和混合文件拆出的真实节点分别在 [filing_fetch/migration.json](filing_fetch/migration.json) 和 [moved_optional_integration_tests.json](moved_optional_integration_tests.json)。独立审查已比对25文件全部断言 AST，内容与顺序保持一致。测试搬迁是责任归位，不是取消断言。

- `CURRENT_TESTS` 中列明的当前v2节点必须在ROOT组合实际运行，不能因缺依赖skip。
- FC505、FC1001–1004、ZR709、ZR802–804、旧preparation成功链是旧derived-role/历史旅程与模型平台兼容重放，保留原断言，按需要显式指定文件运行；不冒充当前v2验收。
- CA202/203/302/304、FC1102/1105/1302、ZR1004/1103/1104/805/806含冻结现场语料、旧canary/观察窗口/发布签收。原规则作为历史记录保留，**不作为新的运行许可或当前解耦门禁，也不默认扫描或修改生产库**。重放前先确认所需历史输入和只读边界，不能用当前生产状态冒充冻结输入。

不要直接对整个 `integration/` 运行全量 pytest。默认入口有清晰的当前清单；历史现场套件需显式选择。普通提交继续使用各仓的小范围本地检查，组合只在接口变化和大节点执行。

## 部署接口

FF 的 `WikiConnection` 将 cwd、公开命令前缀和可选采集配置集中在 `ff_company_wiki_connection.py`；六操作为 catalog/query/local_prepare/open/transcript_import/financial_statements。旧 `company_wiki_root` 配置通过同一适配器保兼容，只有该适配器知道旧目录布局。配置明确选择 connection 后，缺操作报清晰配置错误，不偷偷回退到另一套部署。

RF 的原文 `source_reader_command` 和摘要 `narrative_reader_command` 分别可替换；CLI 对应 `--source-reader-command-json`、`--narrative-reader-command-json`。`catalog_config` 对显式外部端点是绝对的不透明句柄，消费者不检查其内部结构；默认本地CLI仍由生产者验证自己的配置。

原始字节 SHA/大小、来源身份、期次、as-of 和核心协议版本有各自责任方。可选诊断放在 `extensions` 对象；JSON排版不构成许可。消费者仍核对收到的实际字节，拒绝重复键、NaN和核心身份冲突。原文预算来自请求；JSON/base64传输额度从原文预算推导，入库不重复扣网络流量。日志、人工签收、canary不增加业务许可。
