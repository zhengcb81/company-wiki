# 市场×文档路径样本矩阵

这是2026-10-24实际核验/定向阅读与缺口清单，不是召回率/完成认证。首13份+DU5九份+补充三份共25份原件已核SHA并保留有界窗口；提取窗口不等于全文通读。均已进入本轮调查，后续不称fresh holdout。

| 文种 | A股 | 港股 | 美股 | 已有策略路径 |
|---|---|---|---|---|
| 年报 | cn-annual（中微）；可扩中芯 | hk-annual（名创）；可扩安踏/壁仞 | us-10k（微软）、us-20f（TAL）；10-K/20-F分别保留 | cn_annual_report / hk_annual_report / sec_10k / sec_20f |
| 半年报 | cn-h1（中微）；DU5科大讯飞已核SHA/关键页 | hk-interim（名创）；DU5金山云已核SHA/关键页并回放选择 | 新核VRSK2025-06-30 10-Q确有三个月/六个月两列及H1订阅机制；旧Q1仍不代签H1 | cn_interim_report / hk_interim_report；US按实际form与期间走sec_10q或6-K附件 |
| 电话会 | DU5吉比特DOCX已核SHA/段落；M2真实earnings_call、23条、unknown、后续计划和限定可进入真实模型请求/卡片，旧overall仍FAIL；广联达PDF候选 | 新找到腾讯2021Q2纪要，SHA及全文有限页提取；第三方记录不能冒充公司正式逐字稿，primary仍缺 | us-txt（微软），正文/完整多轮片段已补读；旧CC case错误已修订；中性TXT/DOCX计划限定正反例已独审 | earnings_call_transcript + speaker/QA/口径依赖 |
| 投资者关系 | cn-ir（万润6页）；制度反例另保留 | 旧腾讯官方Temp失效；新纪要仅secondary补充，正式results/deck仍需恢复SourceRef | DU5微软8-K/EX99.1已核SHA/窗口，附件选材回放仍漏指标定义/机械调整指引 | investor_qa_record / results_release / investor_presentation / container_attachment |
| 招股/发行 | cn-ipo（中微）、cn-equity（恒锋）、cn-convertible（金禾）；DU5中密已核SHA/关键页 | hk-ipo（名创）；阿里2019二次上市招股文件已核SHA/目录及186/191–193/400业务/募资页 | 本地未找到S-1/F-1；正式FF补采尝试在provider启动前budget_exceeded，0HTTP/0下载，精确触发限额待诊断 | prospectus_cn / prospectus_hk / prospectus_us / offering_* |

首批13份SHA匹配原件、46个PDF关键页/HTML/TXT定向片段的准确计数见inventory和targeted-reading；2个复杂PDF页已目视，临时PNG删除。每格最终争取两家公司/不同版式，一格缺样时如实登记且不推迟其他已具备格的改进。季度富业务/稀疏负例、修订/摘要/程序附件作为横向反控，继续复用DU-BENCH而非新增第二评测器。

DU5另外51个PDF页窗口、80个DOCX段落及两个HTML的源金标窗口清单见du5-inventory；补充三份见extra-inventory/extra-source-reading与alibaba-business-reading。BS4窗口是研究定位，HTML首部可能含隐藏iXBRL；生产输入依然由既有normalize_document输出，不能把原HTML头部隐藏token当正文证据。旧冻结gold中的金融职责/ASR歧义/替代support充分性问题由独审逐项记录，不静默改分母或要求模型复述错误。
