# DU2-FAMILIES 覆盖矩阵

本表把 [strategy_matrix](../../strategy_matrix.md) 的文档形态逐一映射到本包规格、真实证据与缺口。
状态四列分开记录：**规格**（spec）、**真实样本**（evidence）、**接入**（integration）、**缺口**（gaps）。
“有规格”“读过样本”“正确召回”“摘要可靠”是四件不同的事；本包只交付前两者的可验证数据，
后两者需 ROOT 接线后的大节点模型验收（语义执行一律 NOT_RUN_ROOT_INTEGRATION）。

- 规格记录：[records/](records/)，索引与逐形态状态：[index.json](index.json)
- 真实/合成证据：[cases/](cases/)（真实摘录每 source 合计 ≤8KiB，实测远低于配额）
- 结构不变量测试：[tests/](tests/)（85 项，仅查结构；语义反例留给 ROOT 行为测试）

## P1 形态

| 形态（strategy_matrix 行） | 规格 id | spec | evidence | integration | 关键 case | 主要缺口 |
|---|---|---|---|---|---|---|
| A股年报 | cn_annual_report | implemented | real | not_integrated | case-cn-annual-business-model-01 / metrics-02 / outlook-03 | 行业集中；扫描件 OCR 未测 |
| A股半年报 | cn_interim_report | implemented | real | not_integrated | case-cn-interim-stage-01 | 缺“无预期变化”样本、摘要版本对 |
| A股季报 | cn_quarterly_report | implemented | real | not_integrated | case-cn-quarterly-business-01 / sparse-02 | 缺重大经营事件型季报 |
| 港股年报 | hk_annual_report | implemented | real | not_integrated | case-hk-annual-stores-01 / samestore-footnote-02 / postperiod-03 | 双栏阅读顺序归 LAYOUT/ROOT |
| 港股中期 | hk_interim_report | implemented | real | not_integrated | case-hk-interim-postperiod-01 | 更正/摘要版本对缺失 |
| SEC 10-K | sec_10k | implemented | real | not_integrated | case-sec-10k-segments-01 / rpo-02 / toc-vs-body-03 | Item 8 附注金标未建 |
| SEC 10-Q | sec_10q | implemented | real | not_integrated | case-sec-10q-parts-01 / revenue-mechanism-02 | 10-Q/A 版本对、银行类附注 |
| SEC 20-F | sec_20f | implemented | real | not_integrated | case-sec-20f-item-map-01 | 业务章节金标未建 |
| A股招股正文 | prospectus_cn | implemented | real | not_integrated | case-cn-ipo-offering-facts-01 / proceeds-02 | 注册稿/正式稿版本对 |
| 港股招股正文 | prospectus_hk | implemented | real | not_integrated | case-hk-ipo-chapters-01 / stores-02 | 繁/英版本逐段对照 |
| US S-1/F-1/最终 prospectus | prospectus_us | implemented | synthetic_only | not_integrated | case-synth-us-registration-01 | **缺本地原件（AR-01）**；仅官方表单结构研究 |
| 定增/配售募集说明书 | offering_cn_equity | implemented | real | not_integrated | case-cn-equity-project-phases-01 / forecast-disclaimer-02 | 发行结果/进展版本对 |
| 可转债 | offering_cn_convertible | implemented | real | not_integrated | case-cn-convertible-projects-01 / forecast-02 | 变更公告版本对 |
| 募投可研 | offering_feasibility | implemented | synthetic_only | not_integrated | case-synth-feasibility-01 | **缺独立可研原件（AR-03）** |
| 募投变更/延期/终止/进展 | project_change_notice | implemented | synthetic_only | not_integrated | case-synth-project-change-01 | **缺真实公告与旧版对（AR-04）** |
| 投资者调研/业绩说明会 | investor_qa_record | implemented | real | not_integrated | case-cn-ir-qa-binding-01 / title-mislead-02 | 说明会文字稿、港股记录 |
| 财报电话会 TXT/HTML | earnings_call_transcript | implemented | real | not_integrated | case-earnings-call-roles-01 | 缺公司原始发布版；问答跨轮未逐条核 |
| 业绩新闻稿/股东信 | results_release | implemented | real | not_integrated | case-us-release-highlights-01 / hk-release-segment-02 | 股东信形态（AR-09）；三件套重复事实对照 |
| 投资者演示 PDF/PPTX/图片 | investor_presentation | implemented | real | not_integrated | case-hk-deck-chart-01 | PPTX/图片原件；图表 OCR 归共享链 |
| 8-K/6-K 容器+附件 | container_attachment | implemented | synthetic_only | not_integrated | case-synth-container-8k-01 | **缺本地容器原件（AR-02）**；官方目录结构已核 |
| 摘要/修订/补充/更正（横切） | lifecycle_revision_overlay | implemented | synthetic_only | not_integrated | case-synth-revision-pair-01 | **缺真实版本对（AR-05）**；extent/revision 轴归 ROOT |
| 制度/通知/确认函（负例） | administrative_document | implemented | real | not_integrated | case-admin-scan-empty-01 / case-synth-admin-notice-01 | **缺真制度/通知负例（AR-06）**；OCR 路径未验 |
| 问询回复/重组收购/重大合同/经营事件 | event_response | implemented | synthetic_only | not_integrated | case-synth-event-response-01 | **缺真实样本（AR-07）** |

## P2 / 按需形态

| 形态 | 规格 id | spec | evidence | integration | 关键 case | 主要缺口 |
|---|---|---|---|---|---|---|
| 研报/新闻/政策/ESG | secondary_research | implemented | synthetic_only | not_integrated | case-synth-secondary-01 | **缺样本（AR-08）**；回链未验证 |
| 股东信 | （并入 results_release） | proposed | missing | not_integrated | — | AR-09 |
| 港股配售/供股公告 | — | proposed | missing | not_integrated | — | AR-10 |
| A股年报/半年报摘要件 | （正交修饰 lifecycle_revision_overlay） | proposed | missing | not_integrated | — | AR-11 |
| 40-F/6-K 正文 | — | proposed | missing | not_integrated | — | AR-12 |

## 跨市场与生命周期变体（显式差异，见 tests/test_cross_market_counterexamples.py）

| 变体轴 | 落在哪些规格 | 显式差异（反例/结构） |
|---|---|---|
| 定期报告章节体系 | cn_annual_report / hk_annual_report / sec_10k / sec_20f / sec_10q | A股“管理层讨论与分析” vs 港股“業務回顧+MD&A” vs 10-K Item 7 vs 20-F Item 5 vs 10-Q Part I Item 2 |
| Part/Item 不可混 | sec_10k / sec_10q / sec_20f | 10-Q Part 内 Item 重号；20-F Item 7=主要股东 ≠ 10-K Item 7=MD&A |
| 招股三市场 | prospectus_cn / prospectus_hk / prospectus_us | A股确认意见反例、港股全球發售/繁简英别名、US 注册表单/转售募资归属 |
| 融资工具 | offering_cn_equity / offering_cn_convertible / offering_feasibility | 定增≠可转债≠可研；项目独立成包、测算≠实际 |
| 生命周期 | lifecycle_revision_overlay | extent（full/summary）与 revision（original/amended/supplement）为正交修饰，不复制各 family 策略 |
| 行政负例 | administrative_document | 不按文件名/标题/空 OCR 跳过；cn-ir-policy 实为活动记录正例 |

## 可复用规则的两家公司验证

同一规则（存量vs净增、计划≠承诺、测算≠实际、期后≠期内、问句≠事实）在 A 股半导体设备公司
（中微公司：年报/半年报/季报/招股）与 H 股零售公司（名创优品：年报/中报/招股）上分别由真实引文验证；
另有美股（10-K/10-Q/20-F/电话会/新闻稿）、港股（新闻稿/演示）佐证。执行信号只用短语与元数据，
不含公司名或固定页码（测试强制）。
