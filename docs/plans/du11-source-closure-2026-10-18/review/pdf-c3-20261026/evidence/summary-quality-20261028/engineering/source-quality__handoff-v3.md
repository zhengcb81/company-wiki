# A 共享指标 owner 效率根修：源码冻结，待定向复审

2026-10-28。本轮仅改 `narrative_business_policy.py` 与新 `test_summary_source_metric_work.py`；v2其余来源/51条admission测试及B均未写。当前完整6文件 raw/LF SHA、原v2 SHA、集中范围见 handoff-v3.json。

独审冻结反例 `quality-review/test_independent_quality.py::test_result_subject_metric_work_is_linear` 在修改前真实 **1 FAIL**，来源主体结果仍True但regex输入随N近平方：16/32/64指标为97,159 / 353,415 / 1,345,159字符。原独审subject-scan-red-v2和本轮RED XML/log保留，没有提高1.15增长阈或计量替身。

根因不止逐metric调用单次compatibility predicate API：`before=full_prefix` / `after=full_tail` 的其它regex同样重复扫描。现在共享metric owner只准备一次既有PreparedPredicateContext，revenue子owner和source_result_subject复用同一个scope/observe索引；每个指标的数量/方向语法只看其断言及相邻指标范围，保留下一指标head以便它作为本数量单位。模态查询仍使用完整原assertion，返回偏移始终为原source坐标。收入值/变化的尾窗也按相邻原匹配有界，开头的比较frame只解析一次。

| 实际工作负载 | 16指标 | 32指标 | 64指标 |
| --- | ---: | ---: | ---: |
| 多assertion（and our）regex输入 | 11,753 | 22,921 | 45,257 |
| 真正单assertion（无our）regex输入 | 12,581 | 24,677 | 48,869 |

两组每次BOUNDARY和SENTENCE均只扫描len(text)一次；保持真实True主体结果。新增中性测试另核所有N个quantity和最后唯一direction及其原span仍完整产出，不能用提前return/漏识别换线性。完整per-pattern复制在本目录 metric-scan-*.json。

最终集中 **308 PASS / 10.18秒pytest、11.758秒runner**：独审两计量负载、作者两计量负载、v2原51条admission、ROOT指定operating_measure_variants / measure_scope / order_metric_language_parity / named_segment_scope / portfolio_disclosure兼容例及既有prepared predicate控制均通过。Ruff和1源码mypy通过，diff-check通过，短TEMP `.c3sqa` 恢复不存在。旧661/180保留为当时范围，本版不自动重签旧SHA。

本轮扫描预留常数、work/选材/字符/token/费用cap全部未变；无API/PDF/网络/下载/holdout/原件配置写入，未提交。源码已冻结，等待独审只复核此共享metric效率根因与原语义正反例，不扩新范围。作者运行独审反例不代表独立验收。
