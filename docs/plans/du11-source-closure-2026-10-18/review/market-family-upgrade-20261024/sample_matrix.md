# 市场×文档路径样本矩阵

这是2026-10-24实际抽读和缺口清单，不是覆盖率/完成认证。样本均已用于旧调查，当前不称fresh holdout。

| 文种 | A股 | 港股 | 美股 | 已有策略路径 |
|---|---|---|---|---|
| 年报 | cn-annual（中微）；可扩中芯 | hk-annual（名创）；可扩安踏/壁仞 | us-10k（微软）、us-20f（TAL）；10-K/20-F分别保留 | cn_annual_report / hk_annual_report / sec_10k / sec_20f |
| 半年报 | cn-h1（中微）；待本轮核DU5科大讯飞 | hk-interim（名创）；待本轮核DU5金山云 | 缺半年累计实样；现us-10q为Q1不能代签H1 | cn_interim_report / hk_interim_report；US按实际form与期间走sec_10q或6-K附件 |
| 电话会 | 待本轮核DU5吉比特DOCX；已有广联达PDF候选 | 本轮缺真实可复验绑定 | us-txt（微软） | earnings_call_transcript + speaker/QA/口径依赖 |
| 投资者关系 | cn-ir（万润6页）；制度假负例另保留 | 旧腾讯Temp失效，需沿CWP找现存SourceRef或补采 | DU5微软8-K/ex99.1绑定存在尚未本轮核/读 | investor_qa_record / results_release / investor_presentation / container_attachment |
| 招股/发行 | cn-ipo（中微）、cn-equity（恒锋）、cn-convertible（金禾） | hk-ipo（名创）；阿里2019可作另一公司 | 缺S-1/F-1真实绑定，不拿schema/synthetic冒充 | prospectus_cn / prospectus_hk / prospectus_us / offering_* |

首批13份SHA匹配原件、46个PDF关键页/HTML/TXT定向片段的准确计数见inventory和targeted-reading；2个复杂PDF页已目视，临时PNG删除。每格最终争取两家公司/不同版式，一格缺样时如实登记且不推迟其他已具备格的改进。季度富业务/稀疏负例、修订/摘要/程序附件作为横向反控，继续复用DU-BENCH而非新增第二评测器。
