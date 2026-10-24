# M3 R5 独立审查：PASS（限定源码与来源材料行为）

## 绑定

- HEAD：`3bcfc202e1657cdd9d5e3797c4b76cd40b8b8c57`，本轮工作树源码待ROOT提交。
- R5回放收据SHA：`91595d633cdea86b8d9f3877551eb2af7e72ddb4bd53e7e0af559c5e107f4fff`。
- 375份生产文件逐项SHA与收据一致，原件回放结束仍一致；生产树聚合SHA：`c8da20402eb12cc96b4478b12b283c35b523cce5385e24b054151c50f2825074`。
- `narrative_business_disclosures.py` 文件SHA为 `5679a8b7faa7153d9a44aaebb6ac38a5e3673f712ec298e6a7478e8b6aa52dfb`，与聚合树SHA含义不同。六份涉及源码及四份审阅测试逐文件SHA见report.json。

## 两个P2关闭

独立11项断言全部通过：7条原始/标题大小写审计培训负例不生成eligible指标定义；逗号和无逗号的真实paid-seats increased保留实际变化；纯公式及`, which represents...`解释性从句都只保留定义，不冒充实际增长。

代码现按候选指标主体后直接绑定有限谓词，不再从任意后文借词。真实MSFT p10/p12定义也可读且不带observed-growth标签，p19/p20机械调整指引全文仍可达。当前审查范围无未修发现。

## 实际核验的五份原件

| 来源 | 已选跨度 / 实际卡片 | 关键结果 |
|---|---:|---|
| Microsoft EX99.1 HTML | 12 / 12 | 定义与实际增长区分，机械指引保留 |
| 金山云2025中期PDF | 96 / 52 | p13完整CDN抵销因果，p15投资限制、p50单分部 |
| 珀莱雅2026Q1 PDF | 4 / 1 | 两个模板消失，p3收款/推广费解释保留 |
| 吉比特交流会DOCX | 23 / 23 | 原语言与unknown角色保持 |
| 中微公司/AMEC IPO PDF | 160 / 81 | 来源/任务绑定有效；不是SMIC样本 |

每个选中跨度都直接用真实PDF verifier或Normalization从原件回放；task binding、每张card SHA与availability独立重算匹配。五份原件SHA前后不变。Proya4条关系正反控和简体CN/HK全球发售路由反正控通过。

## 不超出证据

此PASS不代表完整原文业务覆盖、正式LLM摘要质量或RF通过。没有独立重新生成全选择；只重放实际选中原文并重算任务卡片。HK/Proya/Gbits/AMEC均仍partial，96/160跨度与16M工作上限、结构缺口如实保留；MSFT的selection coverage_complete也不是内容gold签收。仅检查显式0.9，生产默认0.8切换与完整发布/缓存生命周期另行验收。

未跑全量、未调用模型/下载、未改源码/旧测试/配置/原件/生产数据、未提交。只写本独立报告；此前失败历史原样保留。
