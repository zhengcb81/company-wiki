# 行业云来源就绪核对（只读，2026-10-26）

结论：**既有增强运行的来源选择已具备行业云完整闭合材料；正式摘要任务与结果尚未由这份证据验证。** 不应因为单切片找不到完整句子，再把该运行判成行业云未召回，也不能把来源就绪直接计为摘要通过。

本次只用 Python 标准库读取两个冻结文件，未读取正在修复的产品代码，未运行 PDF、Docling、LLM 或新 holdout，未修改 gold 和既有证据。

## 证据绑定

- `.planning/c3-20261026/hk-v2-source-check/diagnosis.json.gz`，SHA-256 `2670e6fa24291059ccccbf1b98ce109c2f4135c070bdba0d13edc7a45e93e351`。
- `docs/plans/du11-source-closure-2026-10-18/review/pdf-c3-20261026/hk-development-gold.json`，SHA-256 `2d6391a1f3f6d0c6e9bc7629e327f54c5bb4d2c651b202d38dd4f4364dbba568`。
- 样本 `c3-hk-kingsoft-h1-2025`，原文 SHA `4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36`；冻结事实 `facts[0].id = hk-industry-cloud-closure`。

## 实际闭合材料

JSON 位置 `/reading_context/groups/34`（索引从零开始），`kind=native_continuity`，组 ID：

`urn:company-wiki:reading-group:sha256:56e2b1d7dcdbb049a90f341fa6dbcb96212bf7550e5162767acf6c4f799c6180`

组的 `citation_views[0].support_evidence_ids` 恰含以下四个连续来源成员，另以第 13 页第 1 段“管理層討論與分析”为 context。这里按既有组记录核对成员，并未自行跨组拼接。

| 诊断位置 | locator | 来源内容与跨片关系 | span SHA 后缀 |
|---|---|---|---|
| `/selected_spans/28` | `loc:v1/page:13/paragraph:9` | 行业云收入人民币 1,340.4 百万元，基期人民币 1,245.4；基期单位与增幅在下一片 | `b95de2d665a45dddfe5171e61e11456330439a916576851380ce537db50848ce` |
| `/selected_spans/29` | `loc:v1/page:13/paragraph:10` | “百萬元增加7.6%。” | `05cba3725cb76decbb79e8d497779fce7670c854584d89c78ed41b003b4714cb` |
| `/selected_spans/30` | `loc:v1/page:13/paragraph:11` | 同比增加主要由于不断增长的 IT 需求及向垂直行业客户复制行业解决方案 | `c600d04527e36d93c8581ba689bd398f375279f70c68b324baec8dc44dbb3000` |
| `/selected_spans/31` | `loc:v1/page:13/paragraph:12` | “的能力。”，完成前一片因果 | `656fb5bb6387c1fc5d458544f9611700a4d4a8c856ee1a01258bf0992f57bb57` |

四片均存在于 selection、来源 ID 与 gold 原文 SHA 相符，`SHA256(raw_text UTF-8)` 均等于记录的 `structured_value.text_sha256`。按 support 顺序核对、仅消除版面空白后，四项 `must_preserve` 全部命中；错误增幅反例“增加23.0%”不在该 support 组。同比句跨 9/10、行业方案能力跨 11/12，因此单片全文匹配只会命中 2/4；组内完整匹配为 4/4。

该运行记录增强页 `[12,13,17]`、Docling 2.96.0、`accepted_groups=3`、`rejected_groups=128`，耗时 117.4022 秒；总选择 112 spans。全局 `budget_full` 和 `structure_complete=false` 不能推翻这个具体组已完整进入选择的事实，也不能据此宣称全文读取完整。既有 native-only 观察与本次 enhanced 缓存属于不同执行路径，不能互相替代。

## 与真实摘要的边界

此诊断明确 `model_calls=0`，只有 `selected_spans` 与 `reading_context`，没有实际 summary task、发送 prompt、模型输出或正式发布内容。因此尚不能证明该组经过后续任务装配、长度截断、组调度后仍完整送入模型，更不能证明最终摘要写对了同比和因果。人民币 1,340.4 百万元和括号中的 187.1 百万美元也是同一金额的不同币种表达，不能混作两个业务指标。

## 下一次一次正式执行应检查的位置

1. 作者语义 v2 通过独审后，沿正式生产路径运行既定开发样本，保持冻结 gold 和选材上限；记录实际 recipe、selection 与最终 material 身份，不把本次缓存冒充新版本执行证据。无需为重新确认上述旧缓存事实单独再跑一次增强。
2. 新执行的 selection / `reading_context.groups`：按原文 SHA、第 13 页 9–12 段及 citation support 找组（不要硬编码旧数组索引或旧 group ID），确认四成员完整、有序，1,340.4 / 1,245.4 / 7.6% 与两项原因属于同一组；失败先区分解析闭合与选择，不能靠增大预算绕过。
3. **实际 summary task 与最终发送材料**：在任务自己的 evidence ID 集合及 citation view 核对该完整组，检查两处跨片句子未被截断、分拆丢失或只作为无支撑 context；此处不能仅查看源 selection 便签收摘要输入。若正式路径未纳入该组，定位任务选择/组装边界，勿归咎 PDF 后盲目重读。
4. **正式摘要与引用**：核对行业云、2025 上半年相对 2024 同期、人民币百万元、7.6%、IT 需求与行业方案复制能力均正确，保留管理层披露的因果语气，不借用相邻公有云 23.0% 或总收入 17.8%；引用须落到真实 support 成员，跨片引用覆盖对应两片。
5. 缓存恢复复用同一正式材料：确认来源与发布内容验证仍通过，恢复后输出/引用一致且无新增模型调用。来源选择通过、真实摘要通过、缓存恢复通过分别留证；不重复跑整批解析来证明这三个不同边界。

本次审查人：`/root/c3_cache_independent_review`。仅新增本报告，原始文件与缓存证据不变。
