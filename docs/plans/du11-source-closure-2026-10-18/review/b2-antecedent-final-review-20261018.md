# B2 最终独立复审（2026-10-18）

## 结论

**REJECT**（一个 P1，可修）。

- v1–v3 的 P1 已在当前代码落地；最终三源回放 required 为 CN 10/10、HK 7/7、US 8/8，CN t32/t34 selected_matches=0，CI 6a2ee853 success，17 个 source_bindings 全部匹配当前文件。
- 新 P1：6a2ee853 的 64 字符有界回看会截断合法长产品名，导致 declaration.family 与原文不一致。这是性能修复引入的静默语义变化，105 测试没有覆盖。
- 缓存与 head 匹配未发现新 P1。

## 1. v1–v3 P1 关闭表

| 来源 | P1 | 状态 | 证据 |
|---|---|---|---|
| v1 | context 端到端 | CLOSED | v2 FIXED；test_antecedent_wiring 的 declaration/target context 断言 |
| v1 | envelope namespace | CLOSED | v2/v3 FIXED；within_reference_envelope 测试 |
| v1 | declaration offset | CLOSED | test_declaration_ref_starts_at_original_offset，CJK 换行 ref 起点精确 |
| v1 | cross-page/furniture | CLOSED | v3 P1-B furniture 复验；当前 header/footer 正反例测试 |
| v1 | forward/competing declarations | CLOSED | forward→missing、two families→ambiguous 测试 |
| v2 | 泛称伪声明 | CLOSED | 当前中文/英文泛称测试 |
| v2 | furniture 邻接 | CLOSED | last_kept/skipped 实现与 header 跨页正反例 |
| v3 | 中文泛称/非专名 | CLOSED | _proper_name 拒绝泛称/描述词；v3 七个样例直接复核为空 |
| v3 | head 匹配 | CLOSED | compatible() 用 head_class；Omega设备→该系列产品 missing、Alpha系列→These devices missing、generic products→unique |

当前 105 测试通过，且自 1a774af0 只增加测试（test_reference_closure +48 行），没有删测试/放宽断言。

## 2. 新 P1：64 字符回看截断合法长产品名

位置：src/company_wiki/document_understanding/operating_states/product_reference.py:361-365。

当前逻辑：

- window_start = max(0, match.start() - 64)
- name, offset = _name_before(text[window_start:match.start()])
- start = window_start + offset

合法输入（4 个长 token 的产品名，head=device）：

Company launched the ExtremelyLongProductNameAlpha ExtremelyLongProductNameBeta ExtremelyLongProductNameGamma ExtremelyLongProductNameDelta device.

结果：

- 完整前缀的 _name_before 返回完整四 token 名称。
- 当前 64 字符窗口只返回最后两个 token：
  ExtremelyLongProductNameGamma ExtremelyLongProductNameDelta
- find_product_declarations 的 family 因而变成
  extremelylongproductnamegammaextremelylongproductnamedelta|device
  而不是完整四 token 的 family；span 也只覆盖后两个 token。

影响：_name_before 允许最多 4 个 Latin token，合同没有 64 字符上限；截断后的名称仍被 _proper_name 接受，所以不是安全 defer，而是静默生成不同 family，后续 deictic 可能闭合到错误声明。现有 CN/HK/US 样本名称较短，未触发；105 测试也未覆盖该边界。

修复建议：

1. 有界回看覆盖最大合法名称长度（例如 256 字符），或先按 token/head 取名称，再只对不截断的窗口做性能优化。
2. 窗口起点切在名称中间时不要接受半截名称；扩大重试或安全 defer。
3. 新增 4 个长 token、总长 >64 的 Latin 名称测试，断言 family/span 完整；补一个中文边界测试。
4. 修复后重跑 105 测试与三源回放，并更新 source_bindings。

## 3. 性能修复的其余语义

- raw offset：窗口内名称的 start = window_start + offset，CJK 换行测试精确；长名称是唯一发现的截断问题。
- 声明顺序：_HEAD_ONLY.finditer 顺序不变；_declarations_for 返回 tuple，lru_cache 不改变顺序；未发现 P1。
- head 匹配：compatible()/head_class 在 6a2ee 之前已落地；现有测试覆盖 Omega/Alpha/generic；未发现 P1。
- 缓存：按完整 source text 的 str identity 缓存；str 不可变；未发现跨文本碰撞。缓存命中/未命中的等价性没有直接测试，属于 P2。
- maxsize=512 淘汰不影响返回值；未发现 P1。

## 4. 测试覆盖

- 当前 collect 105，实际运行 105 passed in 2.96s（python -m pytest tests/unit/du11_source_closure -q -p no:cacheprovider）。
- 覆盖：v1 context/envelope/offset/furniture/forward；v2 泛称/furniture；v3 中文泛称/head 匹配；family/collective/attribution；跨页 window；预算/envelope。
- 未覆盖：64 字符回看边界/长名称；缓存命中/未命中的等价性；窗口起点截断保护。长名称 P1 因此逃过 105 绿。

## 5. 最终三源回放与 CI

- CN：b2-final-20261018/cn-h1.json
  - ENGINEERING_PASS_CONTENT_OPEN；selected_required=10/10；canonical_required=10/10；selected_count=96；api_calls=0；raw_copies=0；original/gold unchanged。
  - selected_gold 10 项全部 supported=true/all_anchors=true。
  - t32/t34 selected_matches=0（incident_markers）。
- HK：b2-real-sources-final-20261018/hk-annual.json：7/7，0 API，original/gold unchanged。
- US：b2-real-sources-final-20261018/us-10k.json：8/8，0 API，original/gold unchanged。
- replay.json：api_calls=0、raw_copies=0、source_unchanged=true；17 个 source_bindings 全部与当前文件 SHA 匹配，包括 product_reference 8e742d71、relations 53f62e69、narrative_antecedent 41d42ef7。
- CI：b2-final-20261018/ci-39123679375.json，head_sha=6a2ee853…，status=completed，conclusion=success，run 358。
- 结论：最终回放/CI 证据齐全且绑定当前代码；唯一未覆盖的是长名称边界（真实样本未触发）。

## 6. P2 / P3

- P2-1：105 测试缺少 64 字符边界与缓存命中/未命中的等价性测试；长名称 P1 因此未被发现。
- P2-2：窗口起点若切在名称中间，没有 clipped 标记；建议加防御检查。
- P3-1：v3 已记录的 same-page cross-column furniture、excluded complete=True、separate-window 不桥接仍是已知限制，不是本轮新 P1。
- P3-2：缓存没有直接测试；按完整 text 缓存，未发现语义变化。

## 7. 红线

- 未修改源码/测试/配置/gold；未 git 写；未调供应商。
- 未发现删除测试、放宽断言、跳过 hook、写生产 config/DB/原件/gold/key 的证据。
- 测试使用 -p no:cacheprovider；不改源码。

## 8. 结论摘要

- REJECT：v1–v3 P1 已关闭，但 6a2ee853 的 64 字符回看引入新的 P1（长产品名截断、family 错误），105 测试未覆盖。
- 最终三源 required 10/10、7/7、8/8，t32/t34 selected_matches=0，CI success，source_bindings 全部匹配；这证明现有真实样本无回归，但不能证明长名称边界。
- 修复建议：扩大/安全化回看，拒绝 clipped 名称，补长名称测试，重跑 105 与三源回放；之后可复审 PASS。
