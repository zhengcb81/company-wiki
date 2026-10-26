# PDF-C3 运行器泛化独立工程复审

结论：**PASS，0 OPEN**。冻结四文件的泛化入口、临时目录生命周期、精确 SourceRef 内容读取接线已通过独立复核。仅审工程边界，不代签 C3 原件阅读质量、holdout、摘要/cache/RF 或正式财报资格。本次无外网、付费模型调用或生产配置写入。

## 已关闭的独立发现

- **C3-ENG-01（P2）日期来源误认证**：旧逻辑仅因 verified descriptor 非空，便把只修正 title 的样本日期标成官方已核，即便日期实际来自 observation 或为 None。现按实际贡献的 published_date/filing_date 字段标注 owner；无日期明确 unknown_public_availability。两个独立中性合成反例及仓库两例回归通过。
- **C3-ENG-02（P2）setup 异常泄漏临时湖**：旧 original fingerprint / gold JSON decode 位于 try/finally 之前；缺原件和坏 JSON 各留下一个已分配根。现公开 run_pair 用 TemporaryDirectory 覆盖所有 setup/执行，私有函数保留 accounting/protected-input 最终观测；context 唯一删除，退出后才观测 removed。独立两例保持原异常类型且零泄漏，仓库两例回归通过。

## 最终验证

最终 **18 passed（12.52s）**：metadata 14 项、exact-ref 新两项、默认注册→held CLI 一项，以及独立新增完整六字段拒绝/真实 exact-ref→held CLI 一项。四份冻结文件测试前后 LF SHA 一致，见 final-freeze.json/xml/log。独立四反例在最终 runner 352e… 上重跑通过，见 independent-after-fix-probe-v2.json。

独立额外探针分别篡改 SourceRef 的 document_id/source_id/SHA/byte_size/mime_type/schema_version，全部获得 named gap。真实合成原件登记后，公开 run_pair 接受显式准备的完整 Ref；通过同一 owner 的实际 query_ref、逐字段相等、open_version，再把真正 Ref 送到 public batch CLI，在模型前主动停止。unknown published_date 仍为 null，selection 明确 NOT_EVALUATED 财报身份/期间/asof；0 model POST，输入未变，临时湖已删除。见 independent-exact-ref.json。held probe receipt status=FAIL 是主动 source-setup/CLI sentinel 的预期停止，不是真实模型失败。

静态确认 live 路径无固定三样本公司/语言映射；primary 对全部描述字段一致覆盖；任意 sample_id 精确唯一选定 sample/provider，歧义在 preflight/output 创建前命名失败。缺 entity 可用显式 security_id 经过现有 resolver，匹配集合直接包含 metadata.security_id，无固定公司旁路；缺 language 保持 None。默认 registered-source 仍执行严格 SourceRequest query，不改变生产 SourceReader 或 FF 的历史资格过滤。

## 原件内容可读与历史财报资格

复核 ROOT 两份实际预检收据（只读 compact receipt，未读原件/holdout/gold 正文）：holdout-qualification-v1.json 两项均因 published_date unknown 得到 registered_source_not_found，historical eligible=false；同两份 source SHA 的 holdout-exact-registration-v2.json 均为 EXACT_CONTENT_REFERENCE_READABLE，published_date=null，财报身份/期间/asof 明确 NOT_EVALUATED，0 模型、0 原件复制、tmp 恢复不存在。它们支持内容读取组合的边界，不把原件可读升级为正式财报资格。该真实原件预检由 ROOT 执行，本独审没有重复执行或代签正式候选摘要。

## RED 证据边界与清理

初审静态 LF 为40072701e4f21ecfeb87798a579f1b2f2462be02bf31e400407344a8ec6948c2。并发修复前未保存精确字节；实际独立 RED 使用保存的已提交 HEAD 快照 dfdfcee660a56f37788cadfb7fea7b28c330b4b62f2599b71d1d56e842f375fe，见 baseline-runner-snapshot.py / independent-before-fix-probe-v2.json。相同缺陷路径在初审400727静态可见，但不声称精确重放400727。两个日期误标和两个 setup 泄漏都有实际 RED；仅泄漏自有测试根，之后均清理。

初次默认 AppContainer TEMP fixture setup 在进入运行器前失败；自有短 TEMP 重跑成功。该空残留已按精确路径清理。probe v1 有 harness 路径/参数错误，v2 才是产品依据。最终 .c3irfinal/.c3irfix/.c3irt/.c3irfreeze 均不存在。未改生产实现、原件、配置、无关 pre-push mode WIP 或作者工区。

## 冻结绑定

- `tools/document_understanding_benchmark/phase_c_runner.py`：LF SHA-256 `352e00f7c46266facef8f504ce831266138df464604b106f2e17d723c837cc7f`
- `tools/document_understanding_benchmark/phase_c_readonly_source.py`：LF SHA-256 `534cef13a299b506573fdaa54141793e9731c2ca6d6253869b8e85c77b63db34`
- `tests/test_phase_c_sample_metadata.py`：LF SHA-256 `285e2dc384337239025117fa8925ef3e6f104eb1f9c3958e80e04c1bfbed050e`
- `tests/test_phase_c_readonly_source.py`：LF SHA-256 `fc0bfc8b7b344347ad2be95f7340cd9c14068eb5826f9a46dccac31812391f16`

完整字节/LF 绑定、收据 hash 与范围见 review.json；review-progress 仅为先前等待增量时的历史状态，由本最终报告取代。
