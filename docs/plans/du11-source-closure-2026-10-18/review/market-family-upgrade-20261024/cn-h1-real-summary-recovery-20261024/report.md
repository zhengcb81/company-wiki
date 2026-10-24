# 中微公司 2026 H1 真实摘要与缓存恢复验收

**日期：** 2026-10-24 UTC
**范围：** 单一CN半年报、共享引擎0.9、MiMo正式原语言摘要；验收同run激活恢复、重启缓存、跨run缓存和公开artifact回读。
**机器收据：** [receipt.json](receipt.json)
**运行材料：** 本机隔离目录 `.planning/shared-reading-production/du11/live-cn-h1-mimo-v6-preflight-112-root-20261024/` 与 `live-cn-h1-mimo-v7-root-20261024/`；不把模型响应和完整临时lake提交到仓库。

## 样本与来源

- 公司/文种：中微公司 2026 半年度报告，CNINFO，原语言简体中文。
- SourceRef：`urn:company-wiki:document:sha256:182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe`。
- 原件 SHA-256：`182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe`，3,149,962 bytes；金标 SHA-256：`10d1dc12e251e57354599c58abd55d5ee3d010259a8bf04415a73fb55cb2a335`。
- 使用正式 `registered_readonly` SourceReader路径。原件、gold、配置和母预算文件在运行前后指纹一致；新下载数为0。

## 根因与策略修正

1. 默认96个span仅支持10项业务gold中的7项。三个缺失事实的精确原文已在同一SHA原件中，且进入候选池；不是原件缺失或PDF解析不到。
2. 128个span在离线封存候选池上能使gold支持达到10/10，但生产选择结果触发既有`SELECT_RESULT_MAX_BYTES = 1 MiB`，返回`RESULT_TOO_LARGE`。该次发生在预算预留和HTTP POST之前，0 POST、0新费用；没有扩大结果存储合同。
3. 改用112个span。它是当前已验证满足10/10 gold的最小离散预算档；实选112 spans / 8,203字符，仍有候选未选，`coverage_complete=false`。该规则只保证本样本结果，不代表其它报告都能全覆盖。
4. 财报选择上限仅在已有共享router中从96调整到112；非财报仍96、招股书仍160。Phase C runner将“金标/预算预留前明确拒绝”与“付费激活恢复”分开识别；无native usage、无POST且收据所有费用/unknown/unsettled计数为0才可分类成未付费拒绝。

## 正式摘要与恢复结果

- provider/model：配置中已启用的 `mimo-v2.6-flash`；按现有资源策略单次最多200,000 tokens / $1。本次模型HTTP请求1次，输入16,031 tokens、输出1,033 tokens，总计17,064；费用估算3,017 micro-USD（$0.003017，预算代理值，不是供应商账单）。保留原预留14,287 micro-USD和已结算usage，不重置unknown holds。
- HTTP request body：69,206 bytes，SHA-256 `a8b53c50e9d08629d0d877f86084059ee59feab3efd6ab9340206383b399ec3c`。响应SHA-256 `95e5032256c38b0010eb102d160fe3643e9f75052d4d904614e8c442ba18126c`。
- 生成摘要状态`completed`，artifact version `narrative-d31b7e3096954b018fed351a92764be7`，artifact SHA-256 `c8ba536b8c64fcdbae64e7eeb5162507f57caeb5bcaab7d952efd331ae65a6b5`，存储输出532,224 bytes；外层gzip回放包116,397 bytes。112个定位符均可从同一原文重放，公开读取`replay_status=verified`。
- 激活恢复：先进入`activation_pending`，再以同一run恢复。native attempt保持1→1，费用和响应身份不变，POST总数保持1→1。
- 已完成run重启：0新POST；新run跨run缓存：0 tokens、0 POST；两个路径均返回原有缓存输出。预检和真实运行的material SHA一致：`22a4342f750b3e471c60f82ce1a48b7ef837abbd9af1af86382c5f0da287358f`。
- 隔离临时lake删除成功；原件/配置/gold未变；模型请求未发送原件副本之外的配置或密钥。

## 质量边界与后续

这是**技术链路PASS**，不是内容业务质量PASS。当前bundle `selection_status=partial`、`quality_status=needs_review`；68条输出claim全部标为`uncertain`且`needs_review=true`。这批输出仍是带精确引用的抽取式证据卡，不能称为已经完成资深分析师式综合总结。gold 10/10只证明关键原文进入了选择包，不证明模型最终逐项表达正确或完整。

接口/代码独立审查已PASS，但68条摘要claim的内容质量仍待独立审查。随后已用完全相同的冻结artifact/hash通过RF离线真实消费：FF复用原件0下载，RF source+narrative与direct narrative均精确匹配来源和产物，112 spans、69 groups/69 citation views闭合，summary=`completed`、replay=`verified`；provider调用0、下载0、隔离catalog删除成功，见v6机器收据。上下文195,794/196,608字节，仅余814字节（约0.4%），当前样本能通过但应观察增长，不能据此放大通用上限。单份532KB artifact的全库空间影响仍未测量。


## 2026-10-24 RF真实消费与接口独立复核

离线正式store重建及FF→RF实际消费见[RF consumer v6收据](rf-consumer-e2e-official-store-v6/e2e-summary.json)：source/artifact SHA与冻结值完全匹配，reading context为`du-production-reading/3`，112个EvidenceSpan、69个group和69个citation view均闭合；RF adapter使用`source_owned_views`，RF narrative `completed/verified`。网络关闭，0次provider调用、0下载，临时catalog已清理。

该联调抓到的根因是RF消费者没有接收CWP已发布的`/3`上下文，并且诊断schema边界比producer更宽。两端现统一要求v3 trace、只接受producer支持的裸诊断码、拒绝`used > limit`；RF还拒绝非字符串schema版本。回归验证：CWP narrative transport 54 passed；RF相关测试85 passed；正常RF pre-push通过Ruff、mypy、host guard及595 passed/1 skipped/36 subtests；独立只读接口审查PASS，详见[审查记录](rf-interface-independent-review-20261024.md)。RF代码提交`c48f86bd0d56f0a2be67a71348cf05d8544b6cdd`已推送到`main`。

真实v3 context大小195,794字节，上限196,608字节，只余814字节（约0.4%）；这是需要监控的容量余量，不能因为这一例而扩大合同。真实摘要业务质量仍`partial/needs_review`，68条claims均为`uncertain/needs_review`，此接口验收不能替代内容审查。当前真实proof-bearing v3样本仅此CN H1一份，其他市场/文种仍需单独验证。
