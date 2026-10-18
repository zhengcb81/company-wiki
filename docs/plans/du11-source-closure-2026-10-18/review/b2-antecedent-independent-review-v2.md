# B2 有界先行词复审报告（v2）

- 复审对象：B2 修复后的代码提交 60fa1d26（请求时 HEAD 4045787f）
- 工作目录：C:\Users\郑曾波\Projects\company-wiki
- 复审时间：2026-10-18 10:05–10:45（本地）
- 复审性质：只读；未修改源码/测试/配置/gold，未执行 git 写操作
- 审查者：独立 reviewer（非作者）
- 绑定快照：B2 源码最终 SHA 见附录；复审期间 HEAD 被另一进程推进到 c78852e4（仅 pre-push gate/test，与本 B2 源码无关），B2 五个源码/两个测试 SHA 未变。

## 结论

**REJECT**（v1 的 P1-1/2/3/5 已验证关闭；P1-4 只部分关闭（furniture/separate-window 残留）；复审另发现 2 个新的 P1 和 6 个 P2，仍需修复后再签收）。

- 工程完整度：**7 / 10**（较 v1 的 6 提升：端到端 context、exact offset、envelope namespace、forward/ambiguous、单卡 deferral 状态均已修好）
- 合同一致性：**5 / 10**（较 v1 的 4 提升：v1 P1-1/2/3/5 关闭；但声明语法仍接受非具名短语，跨页 furniture 邻接仍错）

**一句话结论：** 上一轮 P1 的正向路径确实打通了，但“什么算一个具名产品声明”这一根语法仍把普通英文/中文短语当成声明，已经把真实 HK 2 张、US 10 张卡误 defer；另外 proven furniture 的跨页邻接比较了错误邻居，真实带页眉的跨页仍会失败。两者都属于 B2 的边界/语义根问题。

## 0. v1 问题逐条复核

| v1 编号 | v2 状态 | 复审证据 |
|---|---|---|
| P1-1 声明 context 端到端 | **FIXED** | 合成 [DECLARATION, TARGET]：target task 的 members=[declaration,target]，support=[target]，context=[declaration]；max_chars=60 时 target 被 SELECTION_BUDGET defer，未导出裸 deictic。 |
| P1-2 envelope carrier namespace | **FIXED** | 真实 CN unique 现在展开为 target 5 + context 1 + declaration 1 = 7 units、190 chars、6 blocks；返回 false 是因为真实 6 blocks > 4，而不是 carrier id 查不到。 |
| P1-3 declaration offset | **FIXED** | “公司持续投入研发\n公司推出Preforma Uniflash系列设备。” ref 起点 13，raw slice 精确以 “Preforma Uniflash系列” 开头。 |
| P1-4 跨页 carry | **PARTIAL** | 直接窗口测试：unproved → empty/complete=False/unproved_order；proven (p7,p8) → predecessor p7/complete=True。但 proven furniture 邻接有 P1-B，且 carries 只来自 continuity window（见 P2/P3）。 |
| P1-5 内部声明顺序/数量 | **FIXED** | forward declaration → missing；两个内部 family → ambiguous；单 family before deictic → not_applicable。 |
| P2-1 整篇状态降级 | **FIXED** | [PLAIN,PLAIN,TARGET,PLAIN,PLAIN] → status selected、coverage True、4 spans、deferred 含 REFERENCE_UNRESOLVED。 |
| P2-2 unread/unproved/cap | **FIXED** | unread → complete=False/stop_reason=unread；unproved → complete=False；cap → incomplete；windows 缺失/异常 → antecedents 默认 ((),False)。excluded 仍是 source_boundary complete=True（P3，见下）。 |
| P2-3 block key / carrier 展开 | **FIXED** | 同页同 block 4 个 paragraph → True；carrier expand 5 originals/5 blocks → False；block key 现为 (source, page, pdf_block)。 |
| P2-4 坐标缺失 | **FIXED (PDF)** | PDF require_adjacency_proof=True；缺坐标 → False。非 PDF 仍把缺坐标当相邻（P3）。 |
| P2-5 collective 句子范围 | **PARTIAL** | 跨句负例已修（“客户包括…。公司推出X系列” → collective False）；但同句无关 marker 仍误挂（P2-B）。 |
| P2-6 attribution | **PARTIAL** | “客户推出Alpha系列设备” → quoted，不捐赠；但“客户高度认可X系列产品”同样被判 quoted，合法 issuer 陈述被误杀（P2-C）。 |
| P2-7 第二套产品词典 | **PARTIAL** | 已改为 PRODUCT_SUFFIX 子集 + import 断言；但 deictic 仍匹配 系统/平台/方案，这些中文 head 已不在声明 alt，family 引用永远 missing（P2-A）。 |
| P2-8 REFERENCE_* 可见/模块绑定 | **PARTIAL** | CN 收据已见 REFERENCE_UNRESOLVED=3、REFERENCE_ENVELOPE=1；probe 已加入 3 个模块。但真实收据的 source_bindings 与最终代码 SHA 不一致，HK/US 当前 2/10 REFERENCE_UNRESOLVED 未出现在收据（P2-D）。 |
| P2-9 readiness 异常 | **FIXED** | charge 已移入 try；session catch ValueError/WorkBudgetExceeded；_candidates 调用点 catch → partial。未新增专门测试，但代码路径成立。 |
| P2-10 测试缺口 | **PARTIAL** | 90 个 du11 测试（较 v1 的 79 增加 11 个）；selection 634、w04 104 全绿。仍缺 generic 伪声明、furniture、unsupported head、同句 collective、attribution 正例、carrier 端到端（P2-E）。 |
| P2-11 project/body | **PARTIAL** | project_for/真实 section_key 已接线；无 project 边界测试；body_region_key/boundary_kind 仍未实现（P3）。 |

## 1. 仍需修的新 P1

### P1-A 声明语法把普通短语/泛称/指代当作“具名声明”

- 位置：product_reference.py:27-36（head 词表/alt）、74-76（_LATIN_NAME/_CJK_NAME/_DECLARATION）、190-212（find_product_declarations）。
- 触发/复现（均为最终 SHA 实测）：
  - find_product_declarations("We sell products and services.") → “We sell products and service”，family “wesellproductsand|service”；与 target “These products have been delivered…” → closure **unique**，declaration_refs 就是这个泛称句。
  - find_product_declarations("The company sells microproducts globally.") → “The company sells microproduct”（连 microproducts 词内 product 都匹配）。
  - find_product_declarations("The Company designs and maintains accounting and internal control systems.") → “accounting and internal control system”。
  - find_product_declarations("公司产品系列丰富，覆盖多个领域。") → “公司产品系列”，family “公司产品|series”；target “该系列产品…” → unique。
  - find_product_declarations("这些产品线已实现量产。") → “这些产品线”，family “这些|series”（把 deictic 本身当声明）。
- 端到端：["We sell products and services.", "These products have been delivered…"] 经 select_reading_evidence → target 组 support=target、context=泛称句，summary task context 也是该泛称句。
- 真实影响：最终代码 HK 有 2 个 ambiguous、US 有 10 个 ambiguous；复跑日志已观察到 These products/our products/services/system 等泛称 family 例子，当前收据却没有这些 REFERENCE_UNRESOLVED。
- 影响：不是“多 defer 一张卡”，而是可以把 deictic 解析到一个非具名、非产品的句子，并把错误 context 交给模型；直接违反合同 §3 “Recognize one explicit named declaration” 与 §6.2 的 forward/heading 反例精神。
- 建议修法：
  - 要求 name 有边界且是品牌/专名样式：Latin 只允许 1-3 个紧凑词、首词大写、拒绝 the/our/we/these/various/accounting… 等功能词或动词短语；拒绝 head 出现在更长词内部（product/products、service/services、microproducts、online/line）。
  - CJK name 拒绝 deictic/泛称前缀（该/这些/前述/上述/所有/公司产品/主要产品…）；只有 Latin 品牌、明确系列名或真正专名可作声明。
  - deictic 自身（这些产品线/上述系列）绝不能作为声明。
  - 补负例：generic English、microproducts、公司产品系列、这些产品线；并保留现有正例。
- 说明：该问题在 v1 语法里已潜伏（v1 未测），但最终 HK/US 真实回放已经把它暴露成 2/10 个 REFERENCE_UNRESOLVED；必须在本轮修，不能只当作“旧问题”。

### P1-B proven furniture 跳过后，邻接比较了错误邻居

- 位置：narrative_antecedent.py:121-143；跳过 furniture 在 123-125，邻接检查在 135-136 使用 units[order[cursor + 1]]。
- 触发/复现：order=[p1(page1), header(page2), p2(page2)]，prose_ids={p1,p2}，furniture={header}，page_carries={(p1,p2)}，require_adjacency_proof=True。
  - 期望：proven furniture 跳过，p1 成为 p2 的前驱，complete=True。
  - 实际：proven carry (p1,p2) → predecessors=()、complete=False、stop_reason=unproved_order；因为跳过 header 后，_adjacent 比较的是 p1 与 header，而不是 p1 与 p2。
  - 更危险：只给 (p1,header)（错误边）时，反而接受 p1、complete=True。
- 影响：真实 PDF 的页眉/页脚一出现，跨页 B2 仍然失败（或被错误 edge 证成）；直接违反合同 §2 “Proven furniture may be skipped by existing source-flow proof” 和 P1-4 的修复声明。
- 建议修法：维护 last_kept（最近被接受的前驱或 target），跳过 furniture 时不要改变邻接基准；_adjacent(last_kept, target) 使用真实窗口 carry。补 header/footer 跨页成对测试（proven furniture + proven p1→p2；wrong carry p1→header 不得接受）。

## 2. 仍需修的 P2

### P2-A family deictic 的 系统/平台/方案 永远无法闭合

- 位置：product_reference.py:60-64（_DEICTIC_CN 仍含 系統/系统/平台/方案）、27-34（_SUFFIX_HEADS 不含这些中文 head）、141-143（head 默认“产品”，supports_head 仍 true）。
- 复现：find_product_deictic("上述系统已交付客户。") → head=产品、family=True；“这些平台”“该等方案”同样；find_product_declarations("公司推出Omega系统，已量产。") → 空；closure → missing。
- 影响：family 引用被门禁，但声明永远找不到；原本可闭合的 Omega系统/平台/方案 被持续 defer；v1 词表包含这些 head，v2 反而退化。
- 建议：把 系统/平台/方案 映射到 system/platform/solution 或明确禁用其 family 标记（保留 legacy admission）；不要用 head 默认“产品”掩盖不支持的 head。补三例测试。

### P2-B 同句无关“包括/含”仍被当成 collective

- 位置：product_reference.py:202-204（_COLLECTIVE_MARK.search 在整句范围内，marker 可以在声明之前）、164-187（_members 接受该 marker）。
- 复现："公司客户包括华为、小米，公司推出X系列产品，已量产。" → X系列 collective=True，members=华为/小米/加?；跨句版本已正确为 False。
- 影响：collective 状态和 member_refs 错，未来成员可能被当产品；合同要求 collective enumeration 属于声明族。
- 建议：只接受在声明 head 之后（或紧邻 appositive）的 collective marker；拒绝声明句主语里的 客户/地区 包括列表；补同句负例。

### P2-C attribution 前缀启发式误杀合法 issuer 声明

- 位置：product_reference.py:205-209：prefix 中 THIRD_PARTY 且无 ISSUER_WORD → quoted_related_party；relations.py:867-868 直接跳过非 issuer 声明。
- 复现："客户高度认可X系列产品，已开始批量采购。" → declaration attribution=quoted_related_party；target 该系列产品 → missing。"据客户反馈，X系列产品性能优异。" → quoted → missing。
- 影响：这些句子是 issuer 对客户态度的陈述，不是客户声明；合法产品名被丢弃，卡片过度 defer。反过来，一句只要含“公司”就会判 issuer，仍可能把真正的客户引述当 issuer。
- 建议：按 clause 的 actor/subject 判 attribution（复用 _classify_np/NP grammar），而不是前缀关键词；非 issuer 声明可以保留 attribution 并作为 context，而不是直接丢弃；补“客户认可/客户采购/据客户反馈”正反例。

### P2-D 真实回放收据没有绑定最终代码

- 位置：docs/plans/du11-source-closure-2026-10-18/b2-real-sources-reviewed-20261018/replay.json 的 source_bindings；probe.py:48-63 已加 3 个模块，但收据里的 SHA 是旧值。
- 实测对比：product_reference 收据 8df50019 vs 当前 d222ff06；relations 41f86a80 vs 当前 dce431d9；narrative_reading 24b2542b vs 当前 ddc36db5。其余 13 个模块一致。
- 行为对比：当前代码 HK 2 个 REFERENCE_UNRESOLVED、US 10 个；收据 replay.json 的 HK/US deferral_reasons 仍只有 SELECTION_BUDGET:128。CN 收据的 work 6,133,095 与 3/1/124 与当前一致，但 b2-reviewed-final 的 CN 收据不含 source_bindings。
- 影响：收据不能证明最终提交的代码；HK/US 的真实 reference deferral 在收据中不可见，且收据里的旧语法 SHA 与当前语法不同。计划 task_plan.md:10 还声称 proven furniture 可跳过，与 P1-B 相反。
- 建议：用最终 SHA 重跑三源并生成含 3 个模块 bindings 的收据；CN 收据也加 bindings；保留当前 2/10 REFERENCE_UNRESOLVED 的真实原因（generic 伪声明）再修。

### P2-E 测试仍缺关键负例（90 绿不等于合同）

- 位置：tests/unit/du11_source_closure/test_reference_closure.py、test_antecedent_wiring.py。
- 缺失：generic English/CJK 伪声明、microproducts 词内匹配、deictic 自身作声明、furniture 跨页、unsupported 中文 head、同句 collective、attribution 正例（客户认可/据客户反馈）、carrier 端到端 context、max_chars 下 target+declaration 原子性（已有 60 字符手工验证但无测试）。
- 影响：P1-A/P1-B 和 P2-A/B/C 都能通过 90 绿；selection 738 全绿也不覆盖这些新语法反例。
- 建议：每条 P1/P2 先补 RED 再修；保留 RED→GREEN 记录。

### P2-F carries 只来自 continuity window，separate-window/SourcePageFlow 未接线

- 位置：narrative_reading.py:485-491：只有同一 continuity window 内相邻成员跨页时加入 carries。
- 影响：若声明在窗口 A、target 在窗口 B，但两窗口之间的页间流动由现有 SourcePageFlow/其他 proof 证明，B2 仍不会借；反之，单独的窗口证明可能比应有的 page-flow 窄。真实 CN t34 仍是 cap partial，无法用样本区分；没有测试。
- 建议：从现有 page-flow owner 导出 carries（或说明 continuity window 就是唯一的 proven edge 并补 separate-window 反例）；补窗口 A/B 跨页测试。

## 3. 逐条对照检查 1–10（v2）

### 1) 只扩展现有责任层
**PARTIAL。** 没有第二 Store/预算/detector；head 词表已改为 PRODUCT_SUFFIX 子集 + import 断言（product_reference.py:27-36、56-58），这一点修好。仍有两类问题：声明语法不是“具名”语法（P1-A）；窗口/邻接逻辑仍是新的一套，未完全复用 continuity 的 furniture/page-flow proof（P1-B、P2-F）。

### 2) 状态语义 / ambiguous 不 nearest-wins
**PARTIAL。** 六状态齐全；family 竞争 → ambiguous（relations.py:886-891），无 nearest-wins；内部 forward/ambiguous 已修（relations.py:843-851）。但 generic 伪声明会制造错误的 ambiguous/unique（P1-A）；unsupported head 产生 false missing（P2-A）。

### 3) 8/4/2048 + 同 parent + 只 defer 受影响卡
**PASS（核心）。** block key 改为 (source,page,pdf_block)（narrative_antecedent.py:177-178）；carrier 展开为全部 originals（narrative_reading.py:467-469、556-562），CN unique 的 6 blocks 被正确判为超限；envelope 仍是同一 WorkBudget。单卡 deferral 不再降级整篇（narrative_reading.py:937-939）。剩余：inverse_origins 展开已修复；test 仍无 2048/2049 精确边界（P3）。

### 4) 原始/分析命名空间
**PARTIAL/PASS。** 声明/成员 ref 在 raw 上匹配（relations.py:858-870），不再经 matching 压缩；session 只做 bounds 校验（narrative_operating_relations.py:194-211）。analysis 的 reference_refs 仍是 analysis 坐标（P3）；_validate_original_refs 仍未校验 parent/source（P3）。

### 5) 缓存键 target+ordered predecessor+window_complete
**PARTIAL。** engine 键正确（relations.py:786-798）；session references 改为按 uid 缓存（narrative_operating_relations.py:154-157），修了 v1 的 owner 折叠；声明扫描仍未按 unit 缓存（relations.py:867）。收据/模块绑定仍不完整（P2-D）。

### 6) 未读/不透明页、页眉页脚、表格/QA 边界
**PARTIAL/FAIL。** unread/blocked → partial；cap/unproved → partial；table/QA 不进入 prose_ids；但 proven furniture 跳过时的邻接错误（P1-B）；excluded 仍 complete=True（P3）；非 PDF 缺坐标仍 adjacent（P3）；separate-window carries 未证明（P2-F）。

### 7) 内部声明：同材料、只认 deictic 之前
**PASS（结构），但受语法污染。** forward → missing；两个内部 family → ambiguous；单 family 前置 → not_applicable。generic/泛称句仍可作为内部声明（P1-A），但这是语法问题，不是顺序逻辑问题。

### 8) 既有行为回归（尤其无指代普通段落）
**PARTIAL。** 纯 PLAIN 仍 selected/coverage True；reference deferral 不再整篇 partial。但当前 HK/US 分别 2/10 张卡因 generic 伪声明被 REFERENCE_UNRESOLVED（P1-A），这是对真实文档的新增过度 defer；gold 仍 7/7、8/8，不能掩盖卡级损失。

### 9) 测试真实覆盖 / 假绿
**PARTIAL。** du11 90 PASS；selection 634 PASS；w04 104 PASS（合计 738）；v1 的假绿已部分修复（端到端 context、文档状态、offset、forward/ambiguous 都有真断言）。但 P1-A/P1-B/P2-A/B/C 都没有测试，且 test_envelope... 仍无 2048/2049 exact（P3）。

### 10) 性能/预算
**PASS。** 最终代码实测：CN 6,133,095/16M（2,514 NA + 3 partial + 1 unique；ref work 3,314）；HK 13,157,180/16M（3,576 NA + 2 ambiguous；ref work 4,398）；US 7,987,497/16M（1,108 NA + 10 ambiguous；ref work 1,118）。原件/gold 前后不变，0 API。没有 O(N*K) 爆炸；HK 余量 2.84M。generic 伪声明增加了少量 ambiguous，不是性能问题。

## 4. 实际运行的命令与结果

1. git status --porcelain：B2 源码/测试无 tracked 修改；工作区有既存未跟踪计划目录。HEAD 复审开始时 4045787f，结束时 c78852e4（仅 pre-push gate 两文件，与本 B2 源码无关）；B2 文件 SHA 未变。
2. pytest tests/unit/du11_source_closure -q：**90 passed in 5.34s**。
3. pytest tests/unit/document_understanding_selection -q：**634 passed in 49.53s**。
4. pytest tests/unit/test_w04_narrative_semantics.py -q：**104 passed in 1.56s**（合计 738，与作者声明一致）。
5. 合成反例（Python stdin，无文件写入）：
   - forward → missing；内部两个 family → ambiguous；单 family 前置 → not_applicable。
   - 换行 offset：ref 起点 13，raw slice 以 “Preforma Uniflash系列” 开头。
   - 同页同 block 四段 → True；carrier 5 originals/5 blocks → False。
   - 跨页 unproven → empty/complete=False/unproved_order；proven → predecessor/complete=True。
   - furniture 跨页：carries (p1,p2) → empty/False；carries (p1,header) → 接受 p1/True（P1-B）。
   - generic EN：“We sell products and services.” + “These products…” → unique，context 为泛称句（P1-A）。
   - generic CJK：“公司产品系列丰富” + “该系列产品…” → unique；“这些产品线” 本身是声明（P1-A）。
   - unsupported head：“上述系统/这些平台/该等方案” → family=True，但 Omega系统/平台/方案声明为空，closure missing（P2-A）。
   - 同句 collective：“公司客户包括华为、小米，公司推出X系列产品” → collective，members 华为/小米（P2-B）。
   - attribution：“客户高度认可X系列产品” → quoted → missing（P2-C）；“公司向客户交付X系列产品” → issuer → unique。
6. 端到端： [DECLARATION,TARGET] → target task members=[decl,target]，support=target，context=decl；max_chars 60 → target SELECTION_BUDGET，无裸 deictic。
7. 真实回放（当前 SHA，probe.py，socket 阻断、REAL_LLM=0、输出系统 temp；原件/gold unchanged，0 API）：
   - CN 6,133,095/16M；2,514 NA + 3 partial + 1 unique；REFERENCE_UNRESOLVED=3、REFERENCE_ENVELOPE=1、SELECTION_BUDGET=124；unique 的 target 5 + ctx 1 + decl 1 = 7 units/190 chars/6 blocks → 合法 defer；t34 8ff2… partial。
   - HK 13,157,180/16M；3,576 NA + 2 ambiguous；REFERENCE_UNRESOLVED=2、SELECTION_BUDGET=126；7/7 gold。
   - US 7,987,497/16M；1,108 NA + 10 ambiguous；REFERENCE_UNRESOLVED=10、SELECTION_BUDGET=118；8/8 gold。
8. 收据对比：b2-real-sources-reviewed/replay.json 的 source_bindings 有 3 个模块 SHA 与当前不一致（product_reference 8df50019 vs d222ff06；relations 41f86a80 vs dce431d9；narrative_reading 24b2542b vs ddc36db5）；HK/US 的 deferral_reasons 只有 SELECTION_BUDGET:128，当前代码有 2/10 REFERENCE_UNRESOLVED。

## 5. 无法验证

1. 全量 unit / 142 合同 / CI / 发布：未运行；作者称 6834 passed/4 环境失败，我无法在本轮复核。
2. 正式内容 C / provider / 摘要质量 / FF/RF 真实消费：未运行。
3. carrier target 的端到端 context：当前 CN unique 被 envelope 合法 defer，合成夹具（text/plain）不创建 carrier；代码逻辑看似接通，但无真实“carrier target + 声明 context”通过样本。
4. separate-window 跨页 / SourcePageFlow 是否能导出更宽的 carries：未验证；当前只从 continuity window 取。
5. 非 PDF 缺坐标相邻、excluded boundary complete=True：未证明是否符合合同意图，倾向 P3。
6. 运行期 selection cache 是否因 3 个语法模块字节变化而失效：未找到 module-hash cache key，selector version 仍 0.9.0。
7. 收据与最终代码的绑定：已确认不一致（P2-D），无法用现有收据证明最终 SHA 的 HK/US reference 行为。
8. generic 伪声明是否影响 gold：当前 gold 仍 10/10、7/7、8/8；无法证明未来不误选，但合成已证明可产生错误 unique context。

## 6. 建议修复顺序

1. P1-A 语法具名化（先写 generic EN/CJK/deictic 负例，RED 后修）。
2. P1-B furniture 邻接（last_kept 基准，补 header/footer 跨页成对测试）。
3. P2-A unsupported heads、P2-B 同句 collective、P2-C attribution 正例。
4. P2-D 用最终 SHA 重跑并重生成三源收据（含 bindings 和完整 reasons）。
5. P2-E 补测试；最后再请独立 reviewer 对新 SHA 复审。
6. 完成后才进入正式 C；现有 90/738 绿不能替代以上反例。

## 附录：最终审查快照（2026-10-18 10:45）

| 文件 | SHA256 |
|---|---|
| src/company_wiki/document_understanding/operating_states/product_reference.py | d222ff06e767f6de14bca33ba8b10a4d8282ecd164a4a4bcc37b2417623bf126 |
| src/company_wiki/document_understanding/operating_states/relations.py | dce431d9074daa35d927094b1524df2d1641c76926e46e004d6b2131e242245c |
| src/company_wiki/source_catalog/narrative_antecedent.py | 16f2a67d02faa3c47aa861ed1cbb817a37574e8510caff8da5db7b6afef06247 |
| src/company_wiki/source_catalog/narrative_operating_relations.py | 3b43270c572fd19949c54f1bf28dbbbf9d6d28bf1ebe2c141c3a05a8347f8f85 |
| src/company_wiki/source_catalog/narrative_reading.py | ddc36db5cfcd028ed0f94b7fc900e09bd64ca256975dd75495badcb2180eaad3 |
| tests/unit/du11_source_closure/test_reference_closure.py | f13f55941005597e190fd7d118758ece49c62606ebb0e2254b1fc73cad0ce334 |
| tests/unit/du11_source_closure/test_antecedent_wiring.py | 815065db682f06c8b338b42f6ad027821b3d4b9b471c57c79d4ebd31f5366d60 |

- 代码提交：60fa1d26；复审结束时 HEAD：c78852e4（仅 pre-push gate/test，不涉及 B2 源码）。
- 本报告只读复审；未修改源码/测试/配置/gold，未执行 git 写操作；真实回放输出仅写系统临时目录。
