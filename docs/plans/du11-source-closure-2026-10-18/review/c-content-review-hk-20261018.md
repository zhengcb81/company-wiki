# DU11 正式 C 内容审查：香港样本（2026-10-18）

- 审查对象：`live-hk-annual-deepseek-20261018`（DeepSeek `deepseek-flash`，Windows 用户级有效密钥）
- 收据：status=PASS、1 POST、16,813 tokens / $0.00742、activation_recovery PASS、errors=[]
- 审查方式：只读；claims 来自 `phaseC-*.bundle.json.gz` 的 `summary.draft.claims`（24 条），金标来自 `tools/document_understanding_benchmark/gold/hk-annual.json`（7 条 facts，critical 6）
- 口径（用户 2026-10-18）：**数字可以近似，但不能写错**（例：`>7,500` 可以，`<7,000` 不行）

## 逐条

| fact id | importance | 判定 | 依据 |
|---|---|---|---|
| f-store-total-2024 | critical | COVERED（近似正确） | t21-1「超過7,500家」，真值 7,504 |
| f-store-mainland-overseas | critical | COVERED（近似正确） | t21-1「近4,400 / 超過3,100」，真值 4,386 / 3,118 |
| f-store-operating-model | critical | COVERED | t23-1 直營/代理/合夥人三分 |
| f-top-toy-total | critical | COVERED | t10-1 276 家（存量，非净增） |
| f-top-toy-mainland | critical | COVERED | t10-1 272 家位於中國內地 |
| f-top-toy-overseas-commenced | critical | COVERED | t10-1 自 2024 年起拓展海外 |
| f-store-network-approximate | normal | COVERED | t21-1 超過 7,500 |

## 结论

- **7/7，critical 6/6：PASS**（数字只有正确近似，无一条与金标矛盾；无 `must_not_assert` 命中）。
- 质量问题（不改变 PASS）：t7-1 是只有标题、无数值的空 claim；t49-1 与 t50-1 重复同一组毛利数字。
- 三家对照：CN 8/10（缺 2 条 critical 事实）、US 2–4/8（缺多条事实）、HK 7/7（通过）；**三份摘要均无单位/换算错误、无投资结论**。
- 后续改进方向：把表格事实做成独立任务、禁止只有标题的 claim，而不是提高数字精度。
