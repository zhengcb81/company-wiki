# B2 最终独立复审 v3（2026-10-18，2a80acf6）

- 审查对象：2a80acf6 的 P1-DEFER-4096 修复、109 测试、三源 final 回放、CI 状态。
- 当前 HEAD：2c4dcfea（绑定回放的 docs 提交）；代码提交 2a80acf6。
- 审查方式：只读；查看 diff/源码/测试/receipts；运行 109 测试；对 >4096 名称、目标/前驱 clipped、partial 语义做定向探针；未改源码/测试/配置，未 git 写，未调供应商。

## 结论

**PASS**（代码层；CI 2a80acf6 仍进行中，是 release gate 的 P2，不是代码 P1）。

- 原 P1-PERF-LONG-NAME 已关闭：4 token >64 名称在文首/中文散文后均完整。
- P1-DEFER-4096 已关闭：scan_product_declarations 返回 clipped；目标 clipped、前驱 clipped 均返回 partial + antecedent_window_clipped，不再 missing。
- _latin_precedes 重复定义已删除，当前只有一处。
- 109 测试通过；三源 required 10/10、7/7、8/8；0 API、原件/gold 未变；source_bindings 全部匹配当前代码。
- 唯一未完成的发布证据是 2a80acf6 的 CI 尚未完成；c6e11921 CI success，但不能替代最终 HEAD 的 exact CI。

## 1. P1 关闭

| 检查 | 结果 | 证据 |
|---|---|---|
| 原长名称截断 P1 | CLOSED | 4 token >64 文首/中文散文后测试通过；直接 find 返回完整 family/span |
| P1-DEFER-4096 | CLOSED | DeclarationScan.clipped；目标 clipped 返回 partial；前驱 clipped 返回 partial + antecedent_window_clipped |
| _latin_precedes 重复 | CLOSED | 当前 product_reference.py 只有 218 一处 |
| 目标 clipped | CLOSED（代码） | 直接构造 clipped 目标 + 该系列产品，返回 partial |
| 前驱 clipped | CLOSED（测试） | test_clipped_predecessor_is_partial_not_missing |

## 2. 验证证据

- 测试：python -m pytest tests/unit/du11_source_closure -q -p no:cacheprovider → 109 passed in 5.32s。
- 自 2a80acf6 的 diff：product_reference.py +35/-?、relations.py +19、test_reference_closure.py +15；没有删测试/放宽断言。
- CN：b2-final3-20261018/cn-h1.json：status ENGINEERING_PASS_CONTENT_OPEN；selected_required=10/10；selected_count=96；actual_work.used=6,133,095；api_calls=0；raw_copies=0；original/gold unchanged；selected_gold 10 项 supported。
- HK：b2-real-sources-final2-20261018/hk-annual.json：7/7；work 13,157,181；0 API；original/gold unchanged。
- US：b2-real-sources-final2-20261018/us-10k.json：8/8；work 7,989,484；0 API；original/gold unchanged。
- replay.json：api_calls=0、raw_copies=0、source_unchanged=true；17 个 source_bindings 全部匹配当前文件，包括 product_reference 02657363、relations bed48781、narrative_antecedent 41d42ef7。
- CI：c6e11921 success；2a80acf6 进行中，尚无 exact final CI 收据。

## 3. P2 / 残余风险

- P2-1：2a80acf6 的 CI 尚未完成；最终发布前必须以 2a80acf6 exact run success 为准，不能用 c6e11921 替代。
- P2-2：find_product_declarations 仍是 lossy public view（忽略 clipped 状态）；生产 reference_closure 已用 scan_product_declarations，但外部/未来调用者若只看 find_product_declarations，仍可能把 clipped 当 absent。建议文档标注或让其返回 status。
- P2-3：没有“目标文本 clipped + deictic”测试；代码直接探针返回 partial，但建议补测试，覆盖目标 path 而不只是前驱 path。
- P2-4：任一前驱出现 clipped 声明都会让 closure 变 partial，即使该 clipped 名称与当前 deictic 无关；这是保守的安全行为，不是错误，但会过度 defer，建议在合同/测试中明确。
- P2-5：capitalized prose + short name 仍可能被 _name_before 误吞（如 Launched Alpha）；这是既有语法风险，不是 2a80 新引入；不判 P1。
- P3：v3 已记录的 same-page cross-column furniture、excluded complete=True、separate-window 不桥接仍是已知限制。

## 4. 红线

- 109 测试通过；未发现删测试、放宽断言、跳 hook、写生产 config/DB/原件/gold/key 的证据。
- 本次审查未改源码/测试/配置；未 git 写；未调供应商。

## 5. 结论摘要

- **PASS（代码层）**：P1-PERF-LONG-NAME 与 P1-DEFER-4096 均关闭；109 测试和三源回放当前代码绑定；没有新 P1。
- **发布前仍需**：2a80acf6 exact CI success；建议补目标 clipped 测试、标注 find_product_declarations 的 lossy 语义，并确认 over-defer 行为。
- P2 不阻止代码复审 PASS，但阻止发布终态。

## 附录

- src/company_wiki/document_understanding/operating_states/product_reference.py:218,360,382-435
- src/company_wiki/document_understanding/operating_states/relations.py:853-895
- tests/unit/du11_source_closure/test_reference_closure.py:90-105
- docs/plans/du11-source-closure-2026-10-18/b2-final3-20261018/
- docs/plans/du11-source-closure-2026-10-18/b2-real-sources-final2-20261018/
- docs/plans/du11-source-closure-2026-10-18/b2-final-20261018/ci-39123679375.json（c6e11921）

---

## 2026-10-18 追加（接收方，非审查结论）

- 复审后补了“目标文本 clipped + deictic”的 committed 测试，`tests/unit/du11_source_closure` 现为 **110 passed**；
- `2a80acf6` 的 CI 已完成 **success**（收据 `b2-final3-20261018/ci-39139605025.json`）；
- 本报告正文写于 CI 完成前，测试数 109 与“CI 进行中”以本追加为准。
