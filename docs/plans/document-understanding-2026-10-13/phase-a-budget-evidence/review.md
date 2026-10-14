# reading_plan/1 独立验证

结论：最后冻结版本的 38 个公开 API 断言全部通过，未发现遗留 P1/P2 阻断。

验证对象：`src/company_wiki/source_catalog/narrative_budget.py`，SHA-256：
`ae9e69f4c6d1bb51b47a2f23913924e3cbf9d2e5259f2e06efbb711265602814`。

范围仅为纯 planner 的 `BudgetItem`、`select_budget_items`、`budget_diagnostics`。此收据不验证生产选择接线或完整 Phase A。

## 反例与修复回放

- 共享 header 的 span/字符成本只计唯一 ID；两个独立项目未被合并成一个原子包。
- 原子依赖的传递闭包、环、缺失节点均保持整包语义，字符预算的精确边界和 `reading_priority=4` 通过。
- 正常预算以及零工作量的全部 24 种输入排列均得到唯一结果/诊断；全局工作停止诊断不冒用具体 item 身份。
- 真实 whole-group CoverageSignature 的比较计数反例最初为 133,000 次调用 / 22,000 工作上限，并选入全部 200 项。最终回放为 743 次调用 / 22,000 上限，完整保留 10 项后停止。
- 不再按新添证据的数量漏计共享 closure 的遍历。全互依赖 20 项场景只进行首轮所需的 20 次 offer closure 扫描，已完整入选的 closure 跳过后续 offer。
- 12 类非法签名元数据被拒绝：非 Signature 对象、非 tuple/生成器/超长序列、非法字符串、stage shape/布尔类型、complete 类型。8 类阅读字段边界亦通过。
- 已由依赖完整入选的 value 不再收到排除诊断。新增两项反例证明该 value 的主题与签名各计入一次，随后第三 slot 选择 novel，而不是重复的 duplicate。
- legacy 与 semantic_coverage/1 在修改阅读专属字段后保持相同输出。

## 收据

- `probe_budget.py`：独立反例，直接使用公开 API；签名计数只包装既有比较函数，closure 计数使用运行时 trace。
- `probe_receipt.json`、`probe_run_final.txt`：最后版本 38/38，通过源 hash 固定对象。
- `probe_receipt_first_freeze.json`：第一次冻结版本 36/36。
- `probe_receipt_coverage_regression.json`、`probe_run_first_freeze_extended.txt`：第一次冻结版本新增两项覆盖反例后的 36/38。
- `probe_receipt_before.json` 是源码修复过程中的快照，不能作为最初 133,000 次调用的原始基线；最初反例数据已在工具输出及发给 ROOT 的审查消息中记录。

独立探针没有修改 src，写入均在本 independent 目录内。
