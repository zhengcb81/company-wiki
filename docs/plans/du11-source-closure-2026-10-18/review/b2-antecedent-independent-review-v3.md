# B2 有界先行词三审报告（v3）

- 复审对象：B2 修复提交 1a774af0（HEAD 1a774af0）
- 工作目录：C:\Users\郑曾波\Projects\company-wiki
- 复审时间：2026-10-18 10:45–11:20（本地）
- 复审性质：只读；未修改源码/测试/配置/gold，未执行 git 写操作
- 聚焦范围：只复核 v2 的 P1-A/P1-B 与 P2-A..F，以及本轮修复可能引入的新问题；不评审正式 C。

## 结论

**REJECT**（工程完整度 **7/10**，合同一致性 **5/10**）。

v2 的两个 P1 中，P1-B furniture 邻接已修好；P1-A 只修好了拉丁泛称，**中文泛称/非专名声明仍被接受**，并把真实 CN 的 unique 8d73 变成 ambiguous。另发现一个独立的 P1：闭包从不比较 deictic 的 head 与声明 head，Omega设备 可以闭合 该系列产品。P2 的 P2-A/P2-D 已关闭，P2-B/P2-C/P2-E 仍有残留。

## 0. v2 问题逐条复核

| v2 编号 | v3 状态 | 证据 |
|---|---|---|
| P1-A 泛称伪声明 | **PARTIAL** | 拉丁泛称（We sell products / Our products / microproducts / internal control systems）已全部为空；但中文泛称仍产生声明：公司主要产品系列、各类产品、所有系列、上述系列产品、司开发的多款薄膜沉积产品、前道集成电路设备产品、可覆盖存储器件 都能闭合 该系列产品 为 unique。真实 CN 8d73（v2 的 unique）现在 ambiguous，family_count=4，其中 3 个是泛称。 |
| P1-B furniture 邻接 | **FIXED** | [p1(page1), header(page2), p2(page2)] + carry(p1,p2) → p1 被接受/complete=True；carry(p1,header) → 拒绝/complete=False；separate-window 不桥接。同页 furniture 也按 skipped 计数通过。 |
| P2-A 不支持 head | **FIXED** | 上述系统/这些平台/该等方案 现在 head 分别为 系统/平台/方案、family=False、closure=not_applicable（legacy 保留）；不再 false missing。 |
| P2-B 同句 collective | **PARTIAL** | 跨句/同句“客户包括…”负例已修（collective=False）；但合法的“包括…在内的 X系列”前置枚举被漏掉：公司推出包括SA/SU、SPTi在内的Preforma Uniflash系列产品 → collective=False；后置写法 → True。 |
| P2-C attribution | **PARTIAL** | 客户推出Alpha系列设备/客户高度认可X系列产品 → quoted（不捐赠，按作者政策）；公司表示客户高度认可… → issuer（正例通过）。但 公司客户高度认可X系列产品 → issuer/unique，实际 actor 是公司客户（quoted_related_party），仍会把第三方陈述当 issuer；同时 客户高度认可… 被整体丢弃，无法作为 quoted context。 |
| P2-D 收据/绑定 | **FIXED** | 新收据 b2-real-sources-v2-20261018/replay.json 的 bindings 与当前文件一致：product_reference a1300818、narrative_antecedent 41d42ef7、relations dce431d9、narrative_reading ddc36db5；HK 2、US 11、CN 5 的 REFERENCE_UNRESOLVED 均可见。旧 b2-real-sources-reviewed 仍是 stale，CN 收据无 bindings（P3）。 |
| P2-E 测试 | **PARTIAL** | 99 个 du11 测试通过；新增 9 个控制（generic 四句、plural missing、unsupported head、同句客户列表、issuer/customer voiced、furniture 正反、separate-window）。仍缺中文泛称、no-head、proper-name 假阴性、前置 collective、公司客户 attribution、generic English targets（P2-E）。 |
| P2-F separate-window | **DOCUMENTED/LIMITATION** | SourcePageFlow 只暴露汇总、不暴露边；实现只在已验证 continuity window 内跨页，separate window 不桥接；新增反例。属于如实保守，不再算 P2 代码错误（P3 记录）。 |

## 1. 仍需修的新 P1

### P1-A 中文泛称/非专名仍被当成具名声明（拉丁已修，中文未修）

- 位置：product_reference.py:82-99（_GENERIC_CJK/_GENERIC_LATIN/_ISSUER_PREFIX）、100-102（_LATIN_NAME/_CJK_NAME/_DECLARATION）、149-166（_proper_name）。
- 机制：CJK name 只要 2-10 个汉字、去掉 issuer 前缀后不等于 _GENERIC_CJK 的精确单词，就通过；_GENERIC_CJK 只有“产品/业务/客户/市场/行业/公司/技术/平台/系统/方案/系列/这些/该/上述/前述…”等有限词，无法阻止“主要产品/各类/所有/多款/前道集成电路/可覆盖存储”等短语。
- 复现（最终 SHA）：
  - 公司主要产品系列包括多个型号。 → 声明 公司主要产品系列，family 公司主要产品|series；target 该系列产品 → unique。
  - 各类产品均已量产。 → 各类产品，family 各类|product；target 该系列产品 → unique。
  - 所有系列均已交付。 → 所有系列，family 所有|series；unique。
  - 上述系列产品已交付客户。 → 上述系列产品（把 deictic 前缀也当 name），unique。
  - 公司开发的多款薄膜沉积产品已推向市场。 → 司开发的多款薄膜沉积产品，unique。
  - 可覆盖存储器件所需应用。 → 可覆盖存储器件，unique。
- 真实影响：CN 8d73（v2 的 unique）现在 ambiguous；2,513 NA + 2 partial + 3 ambiguous = 5 unresolved；3 个 ambiguous 的核心 families 是 司开发的多款薄膜沉积产品、薄膜沉积产品、可覆盖存储器件 等泛称，另有一个可能是真声明的 中微公司钨系列，因此 unique 被泛称挤成 ambiguous。
- 影响：这不是“多 defer 一张卡”，而是泛称可以闭合/污染 该系列；也可能把错误的声明上下文交给模型，违反合同 §3 explicit named declaration。
- 修复建议：CJK 非 family head 要么回到 v2 的保守规则（仅 系列/产品线 等 family head），要么要求声明的上下文证据（如推出/发布/量产/上市/销售 + 明确的名称边界），不能只凭“2-10 个汉字 + 非精确黑名单”就接受；“上述/这些/所有/各类/主要/多款/所有”等起首必须拒绝。补上述反例。

### P1-B 闭包不比较 deictic head 与声明 head（任何声明都能闭合任何家族指代）

- 位置：relations.py:830-855（只判断 family deictic 是否存在/是否在内部）、856-891（families 只按 declaration.family 聚合；从未与 ProductDeictic.head 或 target 的 family class 比较）。
- 复现：
  - 公司推出Omega设备，已量产。 + target 该系列产品已交付… → declaration Omega设备，status unique，context 是设备声明。
  - 各类产品均已量产。 + target 该系列产品… → unique（产品 head 闭合系列）。
  - 公司推出Alpha系列设备。 + target 这些设备已交付… → unique（系列 head 闭合设备，反向也成立）。
- 影响：错误 head 的声明可作为 deictic 的先行词；这正是“有声明但 family/head 不对”的误闭，合同要求 family 指代对应系列/族，而不是任意产品。
- 修复建议：把 ProductDeictic.head/family class 与声明 head class/_FAMILY_MARKERS 对齐；无匹配 → missing（或 legacy not_applicable），不要用任意声明凑 unique；internal 声明也用同一匹配规则。补 device/product/series 交叉测试。

## 2. 仍需修的 P2

### P2-A 专名过滤误杀/切错合法产品名

- 位置：product_reference.py:100-102（_LATIN_NAME 要求每词大写开头）、35-36（_HEAD_ALT 大小写敏感）、102（CJK name 贪心 + head 顺序）。
- 复现：
  - iPhone 15 series has shipped. → 无声明，target These products… → missing（小写品牌）。
  - Model 3 系列已量产。 → 无声明（空格+数字尾）。
  - Preforma uniflash系列已量产。 → 无声明（第二词小写）。
  - Acme Products are sold./ACME Systems are deployed. → 无声明（head 首字母大写；_HEAD_ALT 只有小写 product/system）。
  - 3M系列已量产。 → 声明切片 M系列（丢掉 3M，name 从 M 起），target unique 但 ref 是错子串。
  - 小米系列产品已交付客户。 → 声明 小米系列产品，family 小米系列|product（贪心把系列吃进 name，head 变成产品），与 该系列产品 的 series family 不一致；单独时仍 unique，但与另一系列并存会误 ambiguous。
  - 好的对照：华为设备、XD-RIE设备、Galaxy S24系列、S24系列、Acme products 都能识别（中文 2 字、全大写缩写、数字/连字符在 name 内可行）。
- 影响：false negative（合法声明被漏，卡片 missing/over-defer）与 wrong slice（3M/M系列）。合同要求 exact source segment；专名过滤不能误杀。
- 建议：允许小写品牌词/首字母小写（至少 iPhone/eBay 类）或单独规则；允许 digit-separated model（Model 3）与 digit-leading（3M）作为 name token；English head 做大小写不敏感匹配（保留原文 span）；CJK 解析优先把 family marker 当 head（小米 + 系列，而不是 小米系列 + 产品）；补上述正反例。

### P2-B collective 只从声明后找，漏掉“包括…在内”的前置合法枚举

- 位置：product_reference.py:253：_COLLECTIVE_MARK.search(text, match.end(), bounds[1])。
- 复现：公司推出包括SA/SU、SPTi在内的Preforma Uniflash系列产品。 → collective=False，members=()；后置 …系列产品，包括SA/SU、SPTi。 → collective=True，members 3。
- 影响：前后置是同一集体枚举；前置形式（中文常见“包括…在内的X系列”）丢 members，后续若用 member_refs 会不完整；合同要求明确 collective enumeration。
- 建议：允许紧邻声明前的 包括/包含…在内/等 包裹式枚举，但必须与声明同一 clause 且 body 以“在内/等”收束；不要回退到 v2 的任意前置 marker。补前置/后置成对测试。

### P2-C attribution 仍是前缀关键词：客户 actor 被当 issuer，客户 subject 被整体丢弃

- 位置：product_reference.py:255-259（prefix 中 THIRD_PARTY 且无 ISSUER_WORD → quoted）；relations.py:867-868（非 issuer 声明直接跳过）。
- 复现：
  - 客户高度认可X系列产品。 → quoted_related_party，target → missing（v2 的 false negative 保留；作者新增测试把它当预期 negative）。
  - 公司客户高度认可X系列产品。 → prefix 含“公司”，判 issuer → unique；实际 actor 是公司客户（quoted_related_party），把第三方陈述当 issuer。
  - 公司表示客户高度认可X系列产品。 → issuer（这个正例合理，因为主语是公司“表示”）。
- 影响：第三方客户 statement 可作为 issuer 声明（违反 attribution），或合法产品名被丢弃（over-defer）；说明仍是前缀关键词，不是 clause actor。
- 建议：按 clause 主语/actor 判定（复用现有 NP/_classify_np）；公司客户… 应为 quoted_related_party，不是 issuer；客户高度认可… 可以保留为 quoted context（带 attribution），而不是整体跳过；补 actor 正反例。

### P2-D 泛称英文 target 仍被门禁/过度 defer

- 位置：product_reference.py:60-72（_DEICTIC_EN 含 such systems/products/services，family 判断不区分普通名词）与 relations.py:834（有 family deictic 即进入 readiness）。
- 真实回放（最终 SHA）：HK 2 unresolved（1 missing + 1 partial）、US 11 unresolved（7 missing + 4 partial），文本全部是 internal control systems / products or services / accounting systems / platforms 等普通财务/内控散文，不是产品族声明；例如 “The Board acknowledges…internal control systems… Such systems are designed…”、“The Company designs and maintains accounting and internal control systems…”、“In instances where SSP… products or services…”。
- 影响：这些卡被 missing/partial defer；gold 仍 7/7、8/8，但这是普通英文散文的过度门禁，违反合同 §3 “Check actual product-deictic subject/object… incidental words do not automatically create a product dependency”。
- 建议：在 _reference_closure 前检查 deictic 是否处于产品 NP 的主/宾语位置（现有 NP grammar），或至少要求 surface 有产品专名/品牌上下文；不要在 internal control/accounting/system 普通名词上触发 family gating。补 HK/US 文本级反例。
- 注意：这不是 P1-A 的泛称声明（声明已过滤），而是 target deictic 的语义范围；它使 HK/US 的 REFERENCE_UNRESOLVED 看起来“合理”，实际是 over-defer。

### P2-E 测试仍缺关键反例

- 位置：du11 99 个测试通过；新增 9 个控制，但缺：
  - 中文泛称声明（公司主要产品系列/各类产品/所有系列/上述系列产品/多款薄膜沉积产品/前道集成电路设备产品/可覆盖存储器件）；
  - deictic head 与声明 head 不匹配（Omega设备 → 该系列产品；Alpha系列 → 这些设备）；
  - proper-name 假阴性（iPhone 15/Model 3/3M/Acme Products/ACME Systems/Preforma uniflash/小米系列产品 family 切分）；
  - 前置 collective（包括…在内的X系列）；
  - 公司客户… attribution 假 issuer；
  - 普通英文 internal control/accounting target over-deferral。
- 影响：99 绿不能覆盖上述 P1/P2；P1-A 的真实 CN ambiguous 就是测试缺口。
- 建议：按上述逐条补 RED→GREEN，保留证据。

## 3. 逐条对照检查 1–10（v3）

### 1) 只扩展现有责任层
**PARTIAL。** 无第二 Store/预算/detector；head 词表仍是 PRODUCT_SUFFIX 子集；但新增的 CJK proper-name 黑名单是纯词表启发式，挡不住泛称短语（P1-A）；闭包新增了 deictic head 字段却未用于匹配（P1-B）。

### 2) 状态语义 / ambiguous 不 nearest-wins
**PARTIAL。** 六状态齐全；内部 forward/ambiguous 正确；family 竞争 ambiguous 不 nearest-wins。但泛称中文制造 ambiguous（真实 CN 3 个）或 unique（合成），且任意 head 可闭合任意 deictic。P1-A/P1-B。

### 3) 8/4/2048 + 同 parent + 只 defer 受影响卡
**PASS（代码）。** block key、carrier 展开、envelope 仍正确；CN v3 没有 envelope deferral，是因为 unique 8d73 先被泛称搞成 ambiguous（不是 envelope 回归）。单卡 deferral 不降级整篇（v2 已验证，当前 reading SHA 未变）。测试仍无 exact 2048/2049（P3）。

### 4) 原始/分析命名空间
**PASS（核心）。** 声明 ref 在 raw 上匹配，起点/切片正；session bounds 校验；analysis reference_refs 仍是 analysis 坐标（P3）。

### 5) 缓存键 target+predecessor+complete
**PASS（核心）。** engine/session 键正确；收据 bindings 现与最终文件一致；声明扫描仍按 predecessor 重扫（性能小，P3）。

### 6) 未读/不透明/页眉页脚/表格 QA
**PARTIAL/PASS。** unread/blocked/cap/unproved 正确；furniture 跨页修复（P1-B v2 closed）；same-page 跨列 furniture 仍只看 ordinal+skipped，不看 column（P3）；separate-window 不桥接（P3/如实限制）；excluded 仍 complete=True（P3）。

### 7) 内部声明：同材料、只认 before
**PASS（结构）。** forward→missing、内部两 family→ambiguous、单 family 前置→not_applicable。但泛称中文/错误 head 仍可作为内部声明；P1-A/P1-B 同源。

### 8) 既有行为回归
**PARTIAL。** 纯 PLAIN 仍 selected/coverage True；reference deferral 不降级整篇。真实 CN 5（2 partial + 3 ambiguous，其中 8d73 unique→ambiguous）；HK 2、US 11（普通英文内控/会计 target over-defer）；gold 仍 10/10、7/7、8/8，但不能掩盖卡级损失。

### 9) 测试是否真实 RED→GREEN
**PARTIAL。** du11 99 PASS；selection 634 PASS；w04 104 PASS（selection+w04=738）。v2 假绿已真断言（context/status/offset/forward/furniture）；但 P1-A/P1-B/P2-A..D 的上述反例没有测试，99 绿不能证明合同。

### 10) 性能/预算
**PASS。** 最终代码实测：CN 6,133,095/16M（2,513 NA + 2 partial + 3 ambiguous；ref work 3,314）；HK 13,157,181/16M（3,576 NA + 1 missing + 1 partial；ref work 4,399）；US 7,993,449/16M（1,107 NA + 7 missing + 4 partial；ref work 7,070）。原件/gold 不变，0 API；无 O(N*K) 爆炸；HK 余量 2.84M。

## 4. 实际运行的命令与结果

1. git status/日志：B2 源码/测试 tracked 干净；HEAD 1a774af0（B2 修复提交）。
2. pytest tests/unit/du11_source_closure -q：**99 passed in 2.12s**。
3. pytest tests/unit/document_understanding_selection -q：**634 passed in 24.18s**。
4. pytest tests/unit/test_w04_narrative_semantics.py -q：**104 passed in 1.97s**（与 selection 合计 738）。
5. 合成反例（最终 SHA，Python stdin）：
   - 拉丁泛称全部 []（P1-A 拉丁问题关闭）。
   - 中文泛称仍声明并 unique：公司主要产品系列、各类产品、所有系列、上述系列产品、司开发的多款薄膜沉积产品、前道集成电路设备产品、可覆盖存储器件（P1-A）。
   - Omega设备 + 该系列产品 → unique（P1-B）；Alpha系列 + 这些设备 → unique。
   - iPhone 15/Model 3/Preforma uniflash/Acme Products/ACME Systems → 无声明/missing；3M → M系列；小米系列产品 → family 小米系列|product（P2-A）。
   - 前置 collective 包括SA/SU、SPTi在内的Preforma Uniflash系列 → collective=False；后置→True（P2-B）。
   - 客户高度认可… → quoted/missing；公司客户高度认可… → issuer/unique（P2-C）。
   - furniture 跨页 carry(p1,p2) 通过、carry(p1,header) 拒绝；same-page gap mismatch 拒绝；same-page cross-column 仍接受（P3）。
6. 真实回放（最终 SHA，probe.py，socket 阻断、REAL_LLM=0、temp）：CN/HK/US 数值见检查 10；gold 10/10、7/7、8/8；原件/gold unchanged，0 API；新收据 bindings OK；旧 b2-real-sources-reviewed stale。

## 5. 无法验证 / 未复核

1. 全量 unit/142 合同/CI/发布：未运行；作者称 c78852e4 CI 39116527863 success，1a774af0 的 CI 未在本轮复核。
2. 正式内容 C/provider/摘要质量/FF-RF 消费：按要求不评审。
3. 真实 CN 8d73 在只修泛称后能否通过：它原本 unique 但 envelope 6 blocks > 4（v2），即便泛称过滤后预计仍合法 defer；当前先被 ambiguous 吞掉。
4. 中文专名与泛称的边界没有形式化标准；公司主要产品系列/各类产品 是否可算 named declaration 需要合同 owner 规则；本报告按 explicit named 判定为否。
5. 普通英文 target 是否应 not_applicable 而非 missing：取决于产品 NP 判定，实现未做 subject/object 检查；需要合同 owner 确认。
6. 运行期 selection cache 是否因语法模块字节变化失效：未找到 module-hash key，selector version 仍 0.9.0。
7. same-page 跨列 furniture 的 reading-order 合法性：未证明；当前只看 ordinal+skipped，P3。
8. CN 收据没有 source_bindings；旧收据 stale；新 HK/US bindings OK。

## 6. 建议修复顺序

1. P1-A 中文泛称/非专名（先补现有反例，RED 后修；可回到 CJK 仅 family head，或增加 declaration context 证据）。
2. P1-B deictic head 与声明 head 匹配（同族/同 head class；无匹配 → missing/legacy）。
3. P2-A proper-name 假阴性（小写/数字/大写 head/CJK 贪心切分）；P2-B 前置 collective；P2-C actor attribution；P2-D 普通英文 target 的 subject/object 检查。
4. P2-E 测试补齐；旧收据标记 stale；CN 收据加 bindings。
5. 之后再请独立 reviewer 对最终 SHA 复审；不要用 99/738 绿替代上述反例。

## 附录：最终审查快照

| 文件 | SHA256 |
|---|---|
| src/company_wiki/document_understanding/operating_states/product_reference.py | a13008183fba6039d06ca938577ed50aba0778e87554a5c0e6aeb465ff386be5 |
| src/company_wiki/document_understanding/operating_states/relations.py | dce431d9074daa35d927094b1524df2d1641c76926e46e004d6b2131e242245c |
| src/company_wiki/source_catalog/narrative_antecedent.py | 41d42ef7d43822715a5b35f59246f41e3a8fb4a61ef84969819d23bc5b371237 |
| src/company_wiki/source_catalog/narrative_operating_relations.py | 3b43270c572fd19949c54f1bf28dbbbf9d6d28bf1ebe2c141c3a05a8347f8f85 |
| src/company_wiki/source_catalog/narrative_reading.py | ddc36db5cfcd028ed0f94b7fc900e09bd64ca256975dd75495badcb2180eaad3 |
| tests/unit/du11_source_closure/test_reference_closure.py | 7df78be5682738c00d18bead888b0e587f420f62fe9b017e285023817941748f |
| tests/unit/du11_source_closure/test_antecedent_wiring.py | b0a676a2deb8cf098d841caa9232c3a8104551e78e581affc533ea51ad53a3ae |

- HEAD：1a774af0；代码提交即 B2 修复提交。
- 只读复审；未修改源码/测试/配置/gold，未做 git 写操作；真实回放输出只写系统临时目录。
