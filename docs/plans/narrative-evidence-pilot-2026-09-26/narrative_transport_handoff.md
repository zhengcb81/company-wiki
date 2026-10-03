# N3a producer 交接：RF / StockWiki selected 消费

## 当前能力

**已发布：**CWP `a640400af4bea0ce97944e99ac9cb6abc6813ae9`，origin/master 实读一致；[Actions 37113358995](https://github.com/zhengcb81/company-wiki/actions/runs/37113358995) 成功 / 单 job 57 秒。两张 consumer 卡现在可独占开工，无需等待额外人工签收。

company-wiki 提供独立的 `narrative-ref/1`、`narrative-read-request/1`、`narrative-read-receipt/1`；包仍为 `narrative-bundle/2.0`。原始 `SourceRef 2.0` 和 `SourceExportBundleV2` 不变。实现细节和边界见[施工细则](narrative_transport_implementation.md)。本仓验收完成后正常提交推送；精确发布 commit/Actions 见[progress.md](progress.md) 最新收据，不使用历史分支。

## 正式调用

部署注入可安装的 `company-wiki-narrative-read`，或配置 Python + module（`company_wiki.source_catalog.narrative_transport_cli`）入口。不要猜相邻 checkout、raw 目录或 object key。

```text
company-wiki-narrative-read --config <CWP配置> --operation reference
company-wiki-narrative-read --config <CWP配置> --operation read
```

- 两个操作的 stdin 均为有版本 JSON，最多 16 KiB。request/golden 在 `tests/fixtures/narrative_transport_v1/`。
- reference stdout 是 canonical reference，stderr `status=metadata_only`；它不意味着原文、摘要、时点已经核验。
- read stdout 是精确持久工件 bytes，无附加换行；stderr 是一行 receipt。必须同时核 exit 0、receipt `status=ok`、schema、请求 ref/as-of、实际 stdout SHA/size 和 bundle/source 绑定。非零时 stdout 为空；任何不一致均不得返回可用证据。
- read 最大正文 1,310,720 bytes，receipt 最大 16 KiB。保持现有 timeout/bounded subprocess；不要自动抓全文、翻译、触发新 LLM 或更新 source DB。
- consumer 的进程边界必须在读取期间计数限长；不能完整 `capture_output` 后才检查预算。overflow/timeout须结束并回收自己启动的进程，stdout/stderr同时读取避免堵塞，receipt只接受一行JSON。
- `expected_source` 的六个字段必须存在；null=未提出该字段约束。消费者有明确公司/证券/期次时必须填写真实约束，不能为了成功全置 null。
- unknown publication 的原始电话会可以保存/去重，但历史叙述 read 具名拒绝；call date 不得补作 publication。reference/read 是独立于原文 transport 的合同，不把其字段塞进原始 SourceRef。
- partial/needs_review/skipped_no_narrative 原样表达；skip 没有证据。可用片段依实际 locator/hash决定，无人工签收或 prompt-review receipt 门。投资语义和预测规则仍由各下游负责。

## Golden 和测试证据

六份 golden 约 9 KiB；`metadata.json` 记录各文件 SHA、真实 producer 路径和归一化字段。它们由真实 scheduler/三 handler/projector/reader 产生，仅部署 policy hash、随机 artifact ID、read_at 归一化，相应工件 hash/size 重算并测试；不是实际公司研究数据。

测试包：

- 最终受影响合同/handler/Store/CLI/集成节点包：109 passed（32.86s）；含四项持久摘要绑定RED→GREEN、TXT byte binding覆盖和golden再生。Ruff、7模块mypy、host guard通过。
- 真实 PDF 发现第三方提示污染 stdout，新增回归先 RED 后修复 CLI 独占流；输出回归+CLI+四原文节点：19 passed，120.36s。
- 真实 P01 年报：9,165,875 → 138,363 bytes / 96 locator；P04 招股：11,211,796 → 223,343 / 160；P07 IR：153,851 → 33,074 / 7，质量 `needs_review` 保留；T01 英文电话会：66,324 → 24,648 / 14。合计工件 419,428 / 原文 20,597,846 ≈ 2.04%。这是 replay 模型下的样本产物空间，不能外推全库或线上模型效果。
- 四原文完整 SHA/mtime 前后相同，生产 config/control/catalog fingerprint 未变；隔离 run roots 已清理。四份数据的 sidecar 是测试上下文，不宣称生产来源历史资格。

## 后续独占 owner

RF 和 StockWiki 可按以下卡在各自仓库并行实施，代码路径不重叠；CWP 总指挥维护 producer，不改他们的研究状态。producer 发布前先核最新发布收据，发布后由当前主线开始：

- [RF narrative consumer](harness_lanes/revenue_forecast_narrative_consumer.md)
- [StockWiki narrative consumer](harness_lanes/stockwiki_narrative_consumer.md)

下游本仓包各自一次验收；总指挥最后跑两条真实 consumer 入口汇合 G-C。不重复 G-A、E-B、W04，也不等无关 IQS full G2b。G-C 完成前 Worker 继续 paused；G-D 按实际派生引用批次进行。
