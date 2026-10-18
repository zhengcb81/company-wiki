# B2 最终独立复审 v2（2026-10-18，c6e11921）

- 审查对象：c6e11921 的 P1 修复、107 测试、CN final2 回放。
- 审查方式：只读；查看 diff/源码/测试/receipts；运行 107 测试；对长名称、4096 上限、defer 语义做定向探针；未改源码/测试/配置，未 git 写，未调供应商。
- 当前 HEAD：c6e119215dde3a9519a359a9167b845754849d17。

## 结论

**REJECT**（一个 P1，可修）。

- 原 P1-PERF-LONG-NAME 的 4 token >64 字符截断已关闭：名称在文首、以及前面有中文散文时都能恢复完整 family/span。
- **新 P1**：到达 4096 窗口上限仍被截断时，代码只是 continue、不产出声明；下游 reference_closure 因看不到声明返回 missing，而不是 partial。也就是说，代码注释称的 defer 没有传播到闭包状态，违反“截断/未知不得推断缺失”的合同。
- P2：_latin_precedes 被定义了两次（完全相同）；HK/US 最终回放仍是旧 product_reference 绑定，c6e11921 只重跑了 CN，且没有 c6e 的 CI 收据；107 测试没有覆盖 4096 上限/defer。

## 1. 原 P1 是否关闭

| 检查 | 结果 | 证据 |
|---|---|---|
| 4 token、总长 >64、名称在文首 | CLOSED | test_long_latin_name_is_never_truncated_by_the_lookbehind；直接运行 find_product_declarations 返回完整四 token family |
| 4 token、>64、前面有中文散文 | CLOSED | test_long_latin_name_after_prose_is_extended_not_truncated；直接运行返回完整 family/span |
| 64→256→1024→4096 放宽 | 实现存在 | product_reference.py:382-397 的 for width 循环 |
| 到 4096 仍截断时 defer | **未真正关闭** | 代码 continue，不产出声明；下游返回 missing，见下 |

原 P1 的“名称截断”本身关闭；但“defer 语义”是新的 P1。

## 2. 新 P1：4096 上限截断被当成 missing，而不是 partial

### 复现

构造一个 4 token、总长约 4112 字符的合法产品名，然后：

- 声明文本："公司推出 " + huge_name + " 系列产品。"
- 目标："该系列产品已交付客户。"

结果：

- find_product_declarations 在 64/256/1024/4096 都因窗口切在名称中间而 continue，最终返回空。
- reference_closure("t", ("d",), window_complete=True) 返回：
  - status = "missing"
  - diagnostics = [{"code": "antecedent_missing", ...}]
  - declaration_refs = []

也就是说，声明确实存在，但被窗口上限截断后，下游把“没找到”当成“没有声明”。

### 为什么是 P1

- 合同要求截断/未知 → partial，不得从“未检查的尾部”推断缺失。
- 当前代码没有 clipped/truncated 标志，也没有让 find_product_declarations 返回 partial/defer；continue 只是静默省略。
- 这会让受影响卡进入 missing（或 not_applicable），而不是显式 defer；这是安全边界错误。
- 107 测试没有覆盖此路径；新增的两个测试只覆盖 64 字符被成功放宽的情况，不覆盖放宽到 4096 仍不够。

### 修复建议

1. 让 find_product_declarations 暴露 clipped/truncated 状态（或单独返回 declaration + status）。
2. 当任一必要声明在 4096 上限被截断时，reference_closure 返回 partial，并记录 antecedent_window_clipped 诊断；不能返回 missing。
3. 测试：>4096 字符的 4 token 名称、目标为 deictic，断言 partial 而不是 missing。
4. 如果产品名长度可被合同上限约束，应显式写入合同并在超限时 defer，而不是静默省略。

## 3. 其他问题

### P2-1：_latin_precedes 重复定义

当前 product_reference.py:218 与 :229 有完全相同的 _latin_precedes 定义；第二个覆盖第一个，行为相同但属于重复代码。删除一个。

### P2-2：HK/US 最终回放未绑定 c6e11921

- 旧 b2-real-sources-final 的 product_reference 绑定是 8e742d71。
- 当前 c6e11921 的 product_reference 是 fdbf58db。
- final2 只有 CN（b2-final2-20261018/cn-h1.json，10/10，work 6,133,095）；没有 HK/US 的 c6e 绑定回放。
- 需要重跑 HK/US，或明确说明修复只影响长名称、并以测试证明；当前没有该证据。

### P2-3：c6e11921 没有 CI 收据

- b2-final-20261018/ci-39123679375.json 的 head 是 6a2ee853，不是 c6e11921。
- 需要 c6e 的 exact CI run，或明确 B2 final 不要求该提交 CI。

### P2-4：107 测试的边界缺口

- 没有 4096 上限/defer 测试。
- 没有缓存命中/未命中的等价性测试。
- 没有 _latin_precedes 重复定义的静态检查。
- 现有 107 测试仍覆盖 v1–v3 P1 与长名称 64 边界，且全部通过（107 passed in 3.27s）。

### P2-5：capitalized prose + short name 的既有误吞

The Company Launched Alpha device 仍得到 launchedalpha|device，而不是 alpha|device。这不是 c6e 新引入（64 窗口也会捕获），但说明 _name_before 的 Latin proper-name 语法仍会把大写动词并入名称；补充 P2 记录，不在本轮判 P1。

## 4. CN final2 证据

- b2-final2-20261018/cn-h1.json：
  - status ENGINEERING_PASS_CONTENT_OPEN
  - selected_required=10/10
  - selected_count=96
  - claims=63
  - actual_work.used=6,133,095，limit=16,000,000
  - api_calls=0，raw_copies=0，original_unchanged=true，gold_unchanged=true
  - selected_gold 10 项全部 supported=true
- b2-final2-20261018/page-scope.json 的 source_bindings 中 product_reference=fdbf58db，与当前文件一致。
- cn-h1.json 本身不带 source_bindings；绑定证据在 page-scope。若要作为 final receipt，建议在 cn-h1 也写入 bindings。

## 5. 红线和测试

- 107 测试通过：python -m pytest tests/unit/du11_source_closure -q -p no:cacheprovider → 107 passed in 3.27s。
- 自 c6e 的 diff：product_reference.py +39/-3，test_reference_closure.py +22；没有删测试/放宽断言。
- 未改源码/测试/配置/gold，未 git 写，未调供应商。

## 6. 结论摘要

- **REJECT**：原长名称截断 P1 已关闭；新 P1 是 4096 上限截断被静默省略并返回 missing，而不是 partial。
- 修复：传播 clipped/defer 状态；加 >4096 测试；重跑 CN/HK/US 或明确影响范围；提供 c6e CI；删除重复 _latin_precedes。
- 通过条件：P1 修复并有测试 + 三源/CI 证据更新后，可复审 PASS。

## 附录：证据路径

- src/company_wiki/document_understanding/operating_states/product_reference.py:218,229,382-397
- tests/unit/du11_source_closure/test_reference_closure.py 新增两个长名称测试
- docs/plans/du11-source-closure-2026-10-18/b2-final2-20261018/cn-h1.json
- docs/plans/du11-source-closure-2026-10-18/b2-final2-20261018/page-scope.json
- docs/plans/du11-source-closure-2026-10-18/b2-final-20261018/ci-39123679375.json（head 6a2ee，不是 c6e）
