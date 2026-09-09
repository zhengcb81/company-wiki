# 117项完成主张逐项审计索引

观测时间：2026-09-05～06。原机器状态117项均accepted；下列是对原始目标的独立只读审计结论，不改旧机器账本。每项均有分报告逐项核对；本表不表示117项都做过当前生产重跑，也不表示每一行源码逐字审完。HISTORICAL_ONLY/UNVERIFIED保留后续验证义务，不能被计成成功。涉及多个仓的不同结论按维度并列，较强反证不能被另一仓的局部通过抵消。

原验收：revenue-forecast/audit_review/2026-08-13_three_repo_completion_rebaseline_plan/completion_assurance_registry.md 与 2026-08-13_zijin_data_lake_remediation_plan/work_unit_registry.md。主要收据rawSHA与场景原登记见 evidence-inventory.json。具体实现、入口、结果、证据局限均在链接行对应的表与发现章节。

|单元|原痛点|本次结论|逐项证据入口|
|---|---|---|---|
|CA-001|P01/P10|HISTORICAL_ONLY|[assurance-audit.md §表](assurance-audit.md)（行62）|
|CA-002|P01/P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行63）|
|CA-003|P01/P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行64）|
|CA-004|P01/P10|HISTORICAL_ONLY|[assurance-audit.md §表](assurance-audit.md)（行65）|
|CA-101|P01/P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行66）|
|CA-102|P01/P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行67）|
|CA-103|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行68）|
|CA-104|P01/P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行69）|
|CA-105|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行70）|
|CA-106|P01/P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行71）|
|CA-107|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行72）|
|CA-108|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行73）|
|CA-109|P01/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行74）|
|CA-201|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行75）|
|CA-202|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行76）|
|CA-203|P01/P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行77）|
|CA-204|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行78）|
|CA-205|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行79）|
|CA-206|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行80）|
|CA-301|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行81）|
|CA-302|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行82）；[revenue-audit.md §表](revenue-audit.md)（行140）|
|CA-303|P01/P11|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行83）|
|CA-304|P01/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行84）|
|CA-305|P01/P10|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行85）|
|CA-306|P01/P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行86）|
|ZR-001|P01/P11|HISTORICAL_ONLY|[assurance-audit.md §表](assurance-audit.md)（行92）|
|ZR-002|P01/P11|HISTORICAL_ONLY|[assurance-audit.md §表](assurance-audit.md)（行93）|
|ZR-003|P01/P11|HISTORICAL_ONLY|[assurance-audit.md §表](assurance-audit.md)（行94）|
|ZR-004|P01/P11|HISTORICAL_ONLY|[assurance-audit.md §表](assurance-audit.md)（行95）|
|ZR-1001|P01/P10/P11|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行111）|
|ZR-1002|P01/P10/P11|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行117）|
|ZR-1003|P01/P10/P11|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行118）|
|ZR-1004|P01/P10/P11|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行119）|
|ZR-1005|P01/P10/P11|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行120）|
|ZR-1006|P01/P10/P11|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行121）|
|ZR-1007|P01/P10/P11|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行122）|
|ZR-1008|P01/P10/P11|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行123）|
|ZR-1009|P01/P10/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行112）|
|ZR-101|P01/P11|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行96）|
|ZR-102|P01/P11|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行97）|
|ZR-103|P01/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行98）|
|ZR-104|P01/P11|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行99）|
|ZR-105|P01/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行100）|
|ZR-1101|P01/P10/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行113）|
|ZR-1102|P01/P10/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行114）|
|ZR-1103|P01/P10/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行115）|
|ZR-1104|P01/P10/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行116）|
|ZR-1105|P01/P10/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行117）|
|ZR-201|P02|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行94）；[filing-audit.md §表](filing-audit.md)（行35）|
|ZR-202|P02|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行95）；[filing-audit.md §表](filing-audit.md)（行36）|
|ZR-203|P02|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行96）；[filing-audit.md §表](filing-audit.md)（行37）|
|ZR-204|P02|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行97）；[filing-audit.md §表](filing-audit.md)（行38）|
|ZR-205|P02|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行98）；[filing-audit.md §表](filing-audit.md)（行39）|
|ZR-206|P02|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行99）；[filing-audit.md §表](filing-audit.md)（行40）|
|ZR-301|P05/P06|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行100）|
|ZR-302|P05/P06|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行101）|
|ZR-303|P05/P06|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行102）|
|ZR-304|P05/P06|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行103）|
|ZR-305|P05/P06|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行104）|
|ZR-306|P05/P06|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行105）|
|ZR-307|P05/P06|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行106）|
|ZR-401|P03/P04|CONTRADICTED|[filing-audit.md §表](filing-audit.md)（行41）|
|ZR-402|P03/P04|PARTIAL|[filing-audit.md §表](filing-audit.md)（行42）|
|ZR-403|P03/P04|CONTRADICTED|[filing-audit.md §表](filing-audit.md)（行43）|
|ZR-404|P03/P04|CONTRADICTED|[filing-audit.md §表](filing-audit.md)（行44）|
|ZR-405|P03/P04|PARTIAL|[filing-audit.md §表](filing-audit.md)（行45）|
|ZR-406|P03/P04|CONTRADICTED|[filing-audit.md §表](filing-audit.md)（行46）|
|ZR-407|P03/P04|CONTRADICTED|[filing-audit.md §表](filing-audit.md)（行47）|
|ZR-408|P03/P04|PARTIAL|[filing-audit.md §表](filing-audit.md)（行48）|
|ZR-409|P03/P04|PARTIAL|[filing-audit.md §表](filing-audit.md)（行49）|
|ZR-501|P07|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行107）|
|ZR-502|P07|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行108）|
|ZR-503|P07|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行109）|
|ZR-504|P07|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行110）|
|ZR-505|P07|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行111）|
|ZR-506|P07|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行112）|
|ZR-507|P07|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行113）|
|ZR-508|P07|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行114）|
|ZR-509|P07|PARTIAL|[wiki-audit.md §表](wiki-audit.md)（行115）|
|ZR-510|P07|CONTRADICTED|[wiki-audit.md §表](wiki-audit.md)（行116）|
|ZR-601|P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行114）|
|ZR-602|P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行115）|
|ZR-603|P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行116）|
|ZR-604|P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行117）|
|ZR-605|P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行118）|
|ZR-606|P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行119）|
|ZR-607|P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行120）|
|ZR-608|P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行121）|
|ZR-609|P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行122）|
|ZR-610|P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行123）|
|ZR-611|P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行124）|
|ZR-701|P08/P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行125）|
|ZR-702|P08/P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行126）|
|ZR-703|P08/P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行127）|
|ZR-704|P08/P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行128）|
|ZR-705|P08/P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行129）|
|ZR-706|P08/P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行130）|
|ZR-707|P08/P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行131）|
|ZR-708|P08/P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行132）|
|ZR-709|P08/P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行133）|
|ZR-710|P08/P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行134）|
|ZR-711|P08/P09|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行135）|
|ZR-712|P08/P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行136）|
|ZR-713|P08/P09|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行137）|
|ZR-801|P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行101）|
|ZR-802|P10|PARTIAL|[revenue-audit.md §表](revenue-audit.md)（行138）|
|ZR-803|P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行102）|
|ZR-804|P10|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行103）|
|ZR-805|P10|CONTRADICTED|[filing-audit.md §表](filing-audit.md)（行50）|
|ZR-806|P10|CONTRADICTED|[revenue-audit.md §表](revenue-audit.md)（行139）|
|ZR-901|P10/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行104）|
|ZR-902|P10/P11|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行105）|
|ZR-903|P10/P11|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行106）|
|ZR-904|P10/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行107）|
|ZR-905|P10/P11|CONTRADICTED|[assurance-audit.md §表](assurance-audit.md)（行108）|
|ZR-906|P10/P11|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行109）|
|ZR-907|P10/P11|PARTIAL|[assurance-audit.md §表](assurance-audit.md)（行110）|

## 覆盖检查

ZR601–604另见[上游owner补审](upstream-asset-audit.md)：不能由revenue同号算术测试关闭company-wiki事实提取目标。其命名检索缺失不单独作为无实现证明，已结合真实extractor和receipt限制结论。

117个唯一注册ID，117项均有至少一个逐项审计表行，无漏项。相同单元跨仓行不是重复完成数。25CA+92ZR；旧71FC含5closure及10waves见legacy-inheritance.md，额外GP10与历史独立项目见gp-audit.md、historical-projects-audit.md。此项检查只是索引覆盖，不是产品通过门。
