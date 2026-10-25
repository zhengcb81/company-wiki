# ST-A13共因修复独立终审

**结论：本次工程与来源输入范围PASS，I1–I6全部闭环，范围内零未解问题。正式摘要响应NOT_REVIEWED，当前RF采用OPEN。**

最终实际模型payload SHA：`8c8aff82e78adda8040def163eb1bcb1eb824310358cd86ce637d1087ec833d8`。原件SHA `7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`；完整375份生产源码digest与attempt06收据一致。最终源码/测试/所有引用证据SHA见[final-review.json](final-review.json)。

## 六项独审问题闭环

| 问题 | 状态 | 最终修复及证据 |
|---|---|---|
| I1：Owned scope incorrectly included customer/supplier-owned services and generic core/primary nouns | CLOSED | narrative_recognition_scope._named_cn_scope + generic filters；final09-owner-binding.json: supplier/customer second possession and core/主营/核心 controls all retain false; actual 0.9 owner verified |
| I2：New helper implementation missing from existing semantic cache digest closure | CLOSED | decision_inventory._versions business_modules；final-probe02.json helper-only simulated source mutation invalidated business_algorithms; inventory/helper unchanged since that pass; final-attempt06-binding matches actual current business_algorithms to selected dependencies |
| I3：Quadratic remaining-tail reference scans exceeded linear work precharge | CLOSED | disjoint assertions/conditional state + unified READING_BUSINESS_SCAN_PASSES；final-contract-probes.json: 8 increasing-size controls include new helper regex and shared predicate boundary, sub counts actual input; max7.5789N<8N; source helper/predicate unchanged; actual final work12879238/16000000 |
| I4：Legitimate explicit customer-control construction alternative rejected | CLOSED | bounded continuation grammar for same-owned customer conditions；final09-owner-binding.json: explicit-conditional-reference and owned-construction-condition positive in actual 0.9 owner |
| I5：Comma/whereas assertion could donate another owner recognition rule | CLOSED | shared narrative_predicate_state.split_predicate_assertions + scoped state reset；final09-owner-binding.json: comma/whereas/unknown-owner/cross-sentence/other-owner payment controls all false |
| I6：New scope topic leaked to explicit 0.8 selector, changing historical EvidenceSpan identity | CLOSED | project_reading_business_fact(include_description=True) only; compatibility detector restored；legacy-final01.json: four legacy real selectors byte-equivalent to new-helper-disabled baseline; 0.8 span restored c12a3520...; actual0.9 selection still exposes new scope and 27 semantic controls pass |

## 实际验收范围

- 最终0.9实际`assess→project`入口27个独立正负例全通过；最终0.6/0.7/0.7.1/0.8原生选择产物逐字典与关闭新关系的旧语义基线一致。0.8的旧span `c12a3520...`已恢复，0.9仍保留新scope。
- 8组递增规模的扫描计量包含新helper正则、共享assertion边界及sub的真实输入参数，最高7.58N，低于8N预收；helper/predicate实现与该次计量一致，避免二次扫描。缓存helper字节变更反例已通过，最终live business_algorithms与选择依赖一致。
- 独立35项关键pytest链通过且自有测试目录恢复不存在；它属于I6之前的冻结版，本报告没有冒称它在最终policy重跑。最终I6只补实际旧入口与27个0.9源owner控制；ROOT另报最终108项通过，不与独审次数相加。
- attempt06为112span/9088字符/63任务、工作12,879,238/16M，源/字符/工作预算未放大。最终完整EvidenceSpan字典与已经逐原件核验的attempt05一致；当前编译实际payload亦完全一致，因此复用112条原件offset核真和旧10个PASS任务局部上下文保留证据，未反复解析或跑全套。

## 内容与发布边界

annual14当前源/输入仍10 PASS、4 PARTIAL、0 MISSING，原14目标及旧8/6/0报告均未改。A13公司具体时段业务归属已补回，但精确时段/时点金额未因此取得；A01/A05父级及A02/A13精确财务责任仍保留。模型语义NOT_REVIEWED、当前RF采用OPEN。

ROOT可以按正常检查发布本次已审工程变化；本报告不代签付费摘要质量、正式缓存生命周期、RF模型实际消费、全公司研究或主线目标完成。初审失败、后续反例和此前回放全部保留。审查0模型调用、0下载、0原件复制、0生产写入。

## 最终源码绑定

- `src/company_wiki/source_catalog/narrative_recognition_scope.py`：`f6efa0788fe698c9dccc7aa555916ea326f82736ef49813dac9db7f4e52243c9`
- `src/company_wiki/source_catalog/narrative_predicate_state.py`：`0f002d36ab8d4d32af1c2d62af54a4f02b7b986fd08216a5e41125f75d75d27b`
- `src/company_wiki/source_catalog/narrative_business_policy.py`：`72f3cad8cf9e1bfa13b3aa8d442f8c69d1d92b18c1685728cdd2ebe9668d5aed`
- `src/company_wiki/document_understanding/decision_inventory.py`：`d60bcdfd715615eea967b79f80fbc592d047f1ab85e66dfa57b66dc1eb05d46e`
- `tests/unit/document_understanding_selection/test_reading_recognition_scope.py`：`45c5c79e769720ea80537ea638dca6466c8114ae419623e6513443e66d7d9a04`
- `tests/unit/document_understanding_selection/test_reading_decision_inventory.py`：`cdd7fdfbc6d4eaab8af8d155a99c6b213fe5fc52cec2382550816a940a453096`

生产与测试最终SHA再次核对一致；未发生审查中源码漂移。
