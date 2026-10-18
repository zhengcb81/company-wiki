# B2 有界先行词/产品指代闭合 — 独立审查报告

- 审查对象：company-wiki 未提交改动（B2 有界先行词 + 产品指代闭合）
- 工作目录：C:\Users\郑曾波\Projects\company-wiki
- 审查时间：2026-10-18 09:30–10:05（本地）
- 审查性质：只读；未修改源码/测试/配置/gold，未执行 git 操作
- 最终审查快照：09:55 之后的 family-scope 版本（见附录 SHA）
- 审查者：独立 reviewer（非作者），依据 review/antecedent-source-interface-final.md 第 2–6 节与 review/harness-handoff.md 的 B2 顺序

> 工作区在审查期间被另一进程继续编辑：09:44–09:55 之间 relations.py、product_reference.py、两个测试文件和计划文档发生变化（早先版本没有 family-only 门禁，目录为 77 PASS；最终版本加入 _FAMILY_MARK/family 过滤，目录为 79 PASS）。本报告所有结论均在**最终 SHA** 上重新运行验证；早先版本独有的“单数 该设备 被误门禁”已从问题清单撤回。源码/测试/计划文档的最终 SHA 见附录。

## 结论

**REJECT**（可修复；P1 全部修复并重跑本报告的反例后再审，可转为 PASS_WITH_FIXES/PASS）。

- 工程完整度：**6 / 10**。责任层方向基本正确（纯语法模块、复用 OperatingRelationSession/WorkBudget、无第二 Store/预算、真实三源可跑、额度未超），但正向链路（声明作为 context 进入依赖卡）没有端到端打通，且真实 CN 上唯一成功的 unique 闭包被 envelope 名称空间错误丢弃。
- 合同一致性：**4 / 10**。P1 共 5 条，直接违反接口文档 §2、§3、§4.5、§6.6 的硬要求；另有 10 条 P2 影响边界、归属、证据绑定和回归范围。

**一句话结论：** 现在的实现能“安全地 defer”，但还不能“正确地闭合”；测试绿、额度绿、原件/gold 不变都不能替代 §4.5/§6.6 的 target=支撑、declaration=上下文的端到端要求。

## 0. 最关键的 5 个 P1（摘要）

1. **P1-1 声明没有进入依赖卡的 citation view / summary task。** 声明只加到 budget_packages，而 _context 用的是原始 eligible 包；最终 target 组的 context_evidence_ids=[]，summary task 只含 deictic 句。合同 §4.5/§6.6 要求“声明是 context、target 是 support”。
2. **P1-2 envelope 在 carrier/original 两套 namespace 之间混用，真实 CN 上唯一 unique 闭包被误判 REFERENCE_ENVELOPE。** needed 经 origins 映射成 carrier id，within_reference_envelope 却拿 original_units 查；真实 CN 回放出现 not_in_units=[b8117...]、ok=False。
3. **P1-3 声明 ref 的 offset 是在匹配文本（CJK 换行空白已压缩）上量的，却按原文字符返回。** 触发输入只需前驱含 CJK 换行空白；实测声明起始 12 而原文应为 13，raw_text[12:40] 左移一个字符。合同要求 exact source offsets。
4. **P1-4 现有的跨页 source-flow 证明没有接线；unproved_order 被当作 complete。** _candidates 调用 build_antecedent_windows 时没有传 page_carries/project_for，跨页必有前驱被截断；且 complete 只在 cap 时为 False，unproved_order 仍 complete=True → 输出 missing（从“未检查的尾部”推断缺失）。
5. **P1-5 “同一材料内已有声明”短路不检查声明顺序和数量。** 目标里 deictic 之后的声明、或两个竞争 family，都会返回 not_applicable；合同 §3/§6.2 要求 forward declaration = missing，两个无关声明 = ambiguous。

## 1. 逐条对照检查 1–10

### 1) 是否只扩展现有责任层（没有第二套 detector/Store/预算/产品词典）
**结论：PARTIAL。**
- 好的一面：没有新增 Store、没有第二条 WorkBudget、没有重新调用 detect_reading_business_fact；OperatingRelationSession 复用 unit/matching_text 缓存（relations.py:764-775），SourceOperatingSession 仍是唯一 source owner（narrative_operating_relations.py:44-65）；envelope 用同一个 work_budget（narrative_reading.py:468-470、491-492）。
- 问题：product_reference.py:17-32 新增了一份 product head 词典，和现有 patterns.py:404-410 的 PRODUCT_SUFFIX 重叠但不等价（现有词表有 材料/添加剂/试剂/药品/equipment/line/membrane/...，新表没有；新表有 平台/方案/技术/系列）。这属于“第二套产品词典”的风险（P2-7）。
- 问题：narrative_antecedent.py 自行重算 order/section/adjacency，未复用 _prose_reading_packages/build_native_continuity 已经证明的 window/page-flow（P1-4、P3-11）。接口文档 §2 明确要求 Reuse the already reserved _prose_reading_packages ... pass。

### 2) 状态语义 not_applicable/unique/collective/ambiguous/missing/partial；ambiguous 是否绝不 nearest-wins
**结论：PARTIAL/FAIL。**
- 六种状态都有返回（relations.py:806-813、829-876）；family 竞争时 len(families)>1 → ambiguous，没有按最近声明取唯一（relations.py:862-865），这一点符合“绝不 nearest-wins”。
- family-only 门禁已实现：_FAMILY_MARK/family（product_reference.py:67、101-116），any(item.family) 才进入门禁（relations.py:831-835）；单数 该设备/该产品 返回 not_applicable（实测 family=False）。这是计划 task_plan.md:13 声明的范围收敛，不是状态错误，但意味着单数产品指代仍走 legacy admission，合同 §6.2 的 Chinese unique product 是否覆盖单数需要作者/合同 owner 明确（P3 范围解释）。
- collective 判定不只看声明本身：_COLLECTIVE_MARK.search(text) 取整段文本里第一个“包括/包含/含”子句，然后给该文本所有声明都打上 collective（product_reference.py:151-157、54-64）。实测“公司客户包括华为、小米。公司推出X系列产品…”把 X系列 标成 collective，members 是 华为/小米（P2-5）。
- missing/partial 的边界语义有问题：source_boundary（含 excluded/unread/blocked）和 unproved_order 都保持 complete=True（narrative_antecedent.py:96-111），于是 missing 可能来自未检查的尾部；windows={} 的 WorkBudget 异常也会让 reference() 默认 ((), True) 返回 missing（P2-2）。
- P1-5 内部声明短路破坏了“forward declaration missing”和“两个声明 ambiguous”。

### 3) 额度：8 原 unit / 4 个 (source,page,pdf_block) / 2048 原文字符、同一 parent 预算；超限是否只 defer 受影响卡
**结论：FAIL。**
- 常量正确：MAX_WINDOW_UNITS=8、MAX_ENVELOPE_UNITS=8、MAX_ENVELOPE_BLOCKS=4、MAX_ENVELOPE_CHARS=2048（narrative_antecedent.py:14-17）。
- 计数错误：block key 是 (source_id, (page, paragraph_index), pdf_block)（narrative_antecedent.py:133-137），合同要求 (parent_id, physical_page, pdf_block)。同一页同一 pdf_block 的 4 个段落会被算成 4 个 block。实测 within_reference_envelope(["u0"], ["u1","u2","u3"], ["u4"], units) = False（应 True）；把 paragraph 都置 0 才 True。
- 计数错误：inverse_origins.get(uid, [uid])[0] 只取 carrier 的第一个 original（narrative_reading.py:522-527），carrier 覆盖的其余 original units/chars 未计入 8/2048（P2-3）。
- 名称空间错误：needed.update(origins.get(entry, entry) ...) 把声明 original 映射成 carrier（narrative_reading.py:512-513），envelope 却拿 original_units 查（526-527）；units.get(carrier) 为 None → 直接 False（narrative_antecedent.py:130-131）。真实 CN 的 unique 闭包正是死在这里（P1-2）。
- “只 defer 受影响卡”：包级是 skip deferred_packages（narrative_reading.py:567-569），但 withheld 会参与 processing_complete（893-910），导致整篇 status=partial/coverage_complete=False（P2-1）；且 withheld 的 REFERENCE_* 条目在 128 截断后常不可见（927-930、P2-8）。
- 测试只测了 8 units、5 blocks、3×1025 chars，没有 2048/2049 精确边界，也没有 paragraph_index 区分 scenario（P2-10）。

### 4) 原始/分析命名空间：声明 ref 是否留在原始 namespace、是否会被 _original_refs 错映
**结论：PARTIAL。**
- 好的一面：reference() 没有调用 _original_refs（narrative_operating_relations.py:147-192），声明 ref 不经过 target offsets 重映；声明 ref 用 self.units→self.originals 回退校验（194-211）。这一条比“直接复用 _original_refs”正确。
- 问题：offset 是 matching 文本坐标（relations.py:851、868-870），不是 original 坐标；_validate_original_refs 只查 0<=start<end<=len(text)（narrative_operating_relations.py:210），不查 parent/source/text identity。实测偏移 1 字符（P1-3）。
- 问题：analysis owner 的 reference_refs 是 analysis 文本坐标（relations.py:836-837、session 不重映），作为 OriginalRef 语义不正确；当前下游只用 required_original_unit_ids，暂未爆发，但 Schema 名不副实（P3）。
- P1-2 的 carrier/original 混淆同属命名空间问题。

### 5) 缓存键是否包含 target+有序 predecessor+window_complete
**结论：PARTIAL（engine 层 PASS，session 层不完整）。**
- engine：key = (unit_id, tuple(predecessor_unit_ids), bool(window_complete))（relations.py:796-798）；test_cache_separates_completeness_and_predecessor_order（test_reference_closure.py:153-158）覆盖 completeness；order 由 tuple 顺序天然区分。PASS。
- session：self.references 以 owner_for(uid) 为 key（narrative_operating_relations.py:154-157）。analysis group 的不同 anchor 共享同一 owner，第一次 anchor 的 predecessors/complete 被后续 anchor 复用；合同要求的 target+predecessor+completeness 在 session API 层没有完整表达（P3-8）。
- find_product_declarations 结果没有按 unit identity 缓存，每个 target × 每个 predecessor 重新扫描（relations.py:851-855）；实测 CN 只有 26 次声明扫描（见 §4），不构成性能问题，但仍是可避免重复（P3）。
- 合同 §6.5 要求 Grammar and source owner actual module bytes enter existing cache dependencies；真实回放的 source_bindings 没有绑定 product_reference.py/relations.py/narrative_antecedent.py（P2-8），运行期 selector version 仍是 0.9.0，未看到 module bytes 进入 cache 依赖；如果存在同 version+同 source 的旧 selection cache，B2 行为不会自动失效（未能验证运行期 cache，见 §5）。

### 6) 是否绕过未读/不透明页、页眉页脚、表格/QA 边界
**结论：PARTIAL/FAIL。**
- 表格/QA：prose_ids 只取 _REFERENCE_KINDS（background/paragraph_event/risk/project/native_continuity），table/qa_exchange 成员不在其中；窗口遇到非 prose 单位即 source_boundary（narrative_antecedent.py:100-106）。表格/QA 不会被越过。PASS。
- 未读/不透明：blocked/excluded/non_selectable 都进 barriers（narrative_antecedent.py:82），遇到即停。PASS（停止本身），但停止后 complete 仍 True（P2-2），会把“尾部未读”说成 missing。
- 页眉页脚：non_selectable 也进 barriers，因此 proven running furniture 也会让窗口停住；合同 §2 说 Proven furniture may be skipped by existing source-flow proof，实现没有利用现有证明（P1-4 同源）。
- 跨页：没有 page_carries，任何 page+1 都被 _adjacent 判 False（narrative_antecedent.py:54-62），unproved_order 仍 complete=True（96-111）。实测 p7 声明 / p8 target 的窗口为 predecessors=(), complete=True, stop_reason="unproved_order"，闭包返回 missing。现有 _prose_reading_packages 的 native window 证明没有被使用（P1-4）。
- 未知坐标：_position 任一字段为 None 时 _adjacent 返回 True（45-62）；未证明顺序被当作相邻（P2-4）。

### 7) 是否会把“声明就在同一材料内”误判为 missing（内部闭合应 not_applicable，且只认 deictic 之前的声明）
**结论：PARTIAL/FAIL。**
- 不会误判为 missing：只要目标文本里有任意声明，就 not_applicable（relations.py:838-841）；test_deictic_closed_inside_its_own_package_is_not_applicable（test_reference_closure.py:94-98）覆盖“声明在 deictic 前面”的简单情况。PASS。
- 但“只认 deictic 之前的声明”没有实现：没有拿 deictic span 和 declaration span 比较先后；声明在 deictic 之后就 not_applicable。实测 "该系列产品已交付…。公司同时推出Alpha系列…" → not_applicable（应 missing）。两个内部 family → not_applicable（应 ambiguous）。P1-5。
- analysis group/大 carrier 里，声明可能在目标文本的后一个成员，也会被当成内部闭合；虽然同一张卡里能看到声明，但这仍然不是“之前”的证明，且会掩盖 ambiguous。

### 8) 是否引入对既有行为的大范围回归（尤其无指代的普通段落）
**结论：PARTIAL。**
- 无指代普通段落：reference() 返回 not_applicable（relations.py:834-835），不改变 selection。实测纯 PLAIN 文档 status=selected, coverage_complete=True；test_plain_statement... 通过（test_antecedent_wiring.py:132-135）。PASS。
- 但有 family deictic 且无法闭合时，withheld 让整篇变 partial/coverage_complete=False：实测 [PLAIN, PLAIN, TARGET, PLAIN, PLAIN] → status=partial, coverage_complete=False, spans=4。合同 §3/交接指南要求“只 defer 受影响的卡”，这是全篇状态级回归（P2-1）。
- 真实 CN 当前 family 版本：2,518 次 reference 调用中 1 missing（“该系列设备已付运”，SHA b554…）、1 partial（t34，SHA 8ff2…）、1 unique（被 envelope 误 defer）；共 3 个 REFERENCE_* deferral，相对 5,275 units 不大，但足以让整篇 partial（原本 source_coverage 也已 false，不能区分增量）。HK/US 全部 not_applicable，无 REFERENCE_* deferral（见 §3）。
- family-only 门禁本身是对早期单数误门禁的收敛（计划 task_plan.md:13），不构成回归；但它意味着单数指代仍是 legacy admission，不能宣称“所有产品指代已闭合”。

### 9) 测试是否真实覆盖 RED→GREEN，是否存在只测实现细节的假绿
**结论：FAIL（覆盖不足 + 2 个误导性绿测）。**
- 最终 tests/unit/du11_source_closure 79 passed（§3）；新增两个文件共 27 个测试（test_reference_closure 17、test_antecedent_wiring 10；其余 52 个为既有）。新测试对新 API/函数是真实 RED（旧代码 import/属性不存在），但没有证据显示作者保留了 RED→GREEN 的顺序（无法验证）。
- 假绿/名不副实：
  - test_resolved_deictic_attaches_the_original_declaration_as_context（test_antecedent_wiring.py:125-129）只断言 metadata[ids[1]]["required"] 含声明；实测最终 group/task 的 context 为空（P1-1）。
  - test_declaration_is_context_for_the_target_not_its_support（138-143）只看 metadata/reasons，不看 _context/citation view。
  - test_unresolved_deictic_defers_only_that_card（119-122）只断言 candidate 被排除，没有断言整篇状态/coverage；实测整篇 partial（P2-1）。
  - test_envelope_accepts_exactly_eight_units_four_blocks_and_2048_characters（95-102）没有 2048/2049 精确边界，也没有 9 units/5 blocks 的 exact first-excess；标题高于覆盖。
  - 没有测试：forward declaration、内部两个 family、matching→original offset（CJK 换行/Traditional）、carrier/original envelope namespace、cross-page proven carry、_context/build_summary_task_plan 的声明 context、attribution、document status。
- 新增的 test_singular_product_deictic_keeps_legacy_admission（124-129）和 family 断言（42-46）是真实行为，不是假绿；但只覆盖 family 收敛，不覆盖 P1。

### 10) 性能/预算：CN 2,518 次 reference、HK 13.17M/16M，是否有明显重复扫描或可避免 O(N*K)
**结论：PASS（当前样本无额度风险；有可避免的小重复，不足以升级）。**
- 实测/复跑（最终 SHA，无 API、原件/gold 不变）：
  - CN：2,518 次 reference()，2,515 not_applicable + 1 missing + 1 unique + 1 partial；reference 自身 work 11,808；总 work 6,141,589 / 16,000,000。
  - HK：3,578 次，全部 not_applicable；reference work 18,658；总 work 13,171,440 / 16,000,000（82.3%）。
  - US：1,118 次，全部 not_applicable；reference work 7,073；总 work 7,993,452 / 16,000,000。
- 声明扫描次数很少：CN 26 次、HK 2 次、US 12 次；build_antecedent_windows 对每个目标 O(1) 前驱窗口，实测 CN 3,198 windows / 9,376 predecessors。没有观察到 O(N*K) 爆炸或整篇重复扫描。
- 但 HK 余量只有 2.83M；session.reference() 对 analysis group 先 _prepare_group 再判断 deictic（narrative_operating_relations.py:158-160），对无 deictic 的 group 也计费（多数会被后续 fact 复用，但被 budget/context 丢弃的 group 是浪费）；find_product_declarations 未按 unit 缓存（P3）。当前样本只增加约 1.2–1.9 万 work，不足以解释为额度风险。
- 没有基线（B2 之前同版本）work 对照，无法给出精确增量；只能证明当前三源未超 16M。

## 2. 发现的问题（P1/P2/P3）

### P1（必须修，未修不能通过 B2）

**P1-1 声明未进入依赖卡的 context（端到端断链）。**
- 位置：narrative_reading.py:533-536（只更新 budget_packages）、644（eligible_packages.append(packages[index])）、725（_context 用 entry 的 required）、926（_context(pipeline, result, eligible)）；summary_tasks.py:136-149（按 group/citation view 建 task）。
- 触发：text_case([DECLARATION, TARGET]) + select_reading_evidence；或任何“前驱声明 + 目标 family deictic”的已解决卡。
- 现象：reading_context["groups"] 两个 group 各 evidence_ids=1、citation_views=[(1,0)]；summary task 的 target context=[]。声明是“另一张 task”，不是 target 的 context。
- 影响：模型拿到裸 deictic 任务，B2 的正向价值（跨窗口先行词上下文）没有交付；与合同 §4.5/§6.6 和交接指南第 3/5 条直接冲突。
- 建议修法：在构造 eligible/_context 之前，把声明的 original ID 加到 target 原始包的 required_context_unit_ids（carrier 经 origins 反解或同时维护 carrier→originals）；让 _context 的 required 与 citation view 都包含声明；补一个 _candidates → finalize → _context → build_summary_task_plan 的端到端断言（target support/declaration context 同一 task）。

**P1-2 envelope carrier/original 名称空间混用，真实 CN unique 被误 defer。**
- 位置：narrative_reading.py:512-513（needed.update(origins.get(entry, entry))）、522-527（within_reference_envelope(..., original_units)）；narrative_antecedent.py:130-131（units.get(uid) is None → False）。
- 触发：声明 original 被 native_range_unit 合并为 carrier（真实 PDF native range 很常见），target 解析出 unique 后 needed 是 carrier id。
- 现象（真实 CN 实测）：unique 的 required = b5bf5b0c...，但 ENV ok=False，decl: b8117bd8...，not_in_units: b8117bd8...；于是唯一成功的 unique 闭包以 REFERENCE_ENVELOPE 被 defer。计划 task_plan.md:15 也自报 CN REFERENCE_ENVELOPE 1。
- 影响：B2 的真实正向样本被自身 envelope 误杀；原因也不是“真的超额”，而是 namespace 不同；修后仍可能真的超过 4 blocks/2048 chars（需要重新量），但当前证据不能得出“已超额”的结论。
- 建议修法：显式维护两套坐标；envelope 对 carrier 应计其全部 originals（unit 数、字符、blocks），或全部在 carrier 坐标上计并验证 carrier 的 source range；禁止把 carrier id 直接查 original_units；加一个 carrier 声明 + target 的回归测试（真实/SHA 固定夹具）。

**P1-3 declaration/member ref 的 offset 不是原文坐标。**
- 位置：relations.py:851（self.matching_text(predecessor).text）、868-870（declaration span 直接进 ref）、871-872（member span）；text_view.py:55-70（prepare_matching_text 压缩 CJK 间空白、\r\n→空格）；narrative_operating_relations.py:210（只查 bounds）。
- 触发：前驱文本在声明之前含 CJK 换行/空白，例如 "公司持续投入研发\n公司推出Preforma Uniflash系列..."。
- 现象：ref {char_start: 12, char_end: 40}，原文声明起点 13；raw_text[12:40] 左移一个字符（以“发Preforma…”开头），members 同样偏移。
- 影响：declaration_refs/member_refs 不能作为 exact source segment；合同 §4 preserving the existing exact source segment arithmetic、§6.4 Traditional/line-wrap offset replay remains exact 不成立；未来消费 ref 会拿到错字。
- 建议修法：在 raw_target/raw_predecessor 上直接匹配，或经 MatchingView.positions/to_original 映射；_validate_original_refs 增加 parent/source/text 重切校验；补 CJK wrap + Traditional 回放测试。

**P1-4 跨页 source-flow 证明未接线；unproved_order 被当作 complete。**
- 位置：narrative_reading.py:468-470（只传 prose_unit_ids/blocked/excluded/work_budget，没有 page_carries/project_for）；narrative_antecedent.py:54-62（page+1 无 carry → False）、96-111（只有 cap 置 complete=False）。
- 触发：声明在 p7、target 在 p8，同一 section/role，现有 _prose_reading_packages/build_native_continuity 已证明跨页 flow。
- 现象：窗口 {predecessor_unit_ids: (), complete: True, stop_reason: "unproved_order"}；reference_closure → missing（断言：p7 明明有声明）。
- 影响：B2 存在的首要场景“跨页后该系列产品”无法闭合；同时把“未证明物理顺序”的尾部说成 missing，违反 §2 最后一段/§3 never infer absence from an unexamined tail。
- 建议修法：从现有 continuity window/SourcePageFlow 抽取 page_carries（或直接复用 window membership），从 _candidates 传入；把 unproved_order 映射为 complete=False→partial；补两个物理页被证明 carry/未被证明 carry 的成对测试。

**P1-5 同一材料内的声明短路不检查顺序/数量。**
- 位置：relations.py:838-841（if find_product_declarations(raw_target): return not_applicable）。
- 触发 A："该系列产品已交付多个先进客户。公司同时推出Alpha系列刻蚀设备，已量产。" → not_applicable（应 missing：声明在 deictic 之后）。
- 触发 B："公司推出Alpha系列刻蚀设备。该系列产品已交付。公司推出Beta系列薄膜设备。" → not_applicable（应 ambiguous：两个内部 family）。
- 影响：forward declaration/内部竞争被当成已闭合，恰好是 B2 要防的“无先行词也放行”；合同 §3 one explicit named declaration … two unrelated declarations remain ambiguous、§6.2 forward declaration missing 不成立。
- 建议修法：先算 deictic spans，再只接受 declaration.span[1] <= deictic.span[0] 的声明；声明全在之后 → missing；之前的 >1 family → ambiguous；补 forward/ambiguous/heading-only 三个测试。

### P2（应修，影响合同边界/证据/回归）

**P2-1 一个 unresolved/envelope deferral 让整篇 status=partial、coverage_complete=False。**
- 位置：narrative_reading.py:893-910（processing_complete = ... and not withheld；结果 replace 为 partial/needs_review）、927-930（withheld 并入 deferred）。
- 触发/复现：text_case([PLAIN, PLAIN, TARGET, PLAIN, PLAIN]) + select_reading_evidence；输出 status=partial, coverage_complete=False, spans=4。纯 PLAIN 则 selected/True。
- 影响：任何含未闭合 family deictic 的文档都被标记为不完整；合同 §3 withholds only the affected package … no whole-document veto，且可能阻断下游 export/质量门。真实 CN 本身已 partial，无法区分增量；干净文档会被新增降级。
- 建议：区分“数据不完整”（native continuity/selection budget）与“单卡 reference deferral”；reference 用独立的 reference_deferred/diagnostics 通道，不参与 processing_complete；仅当 target 卡被跳过时记录；补文档状态测试。

**P2-2 未读/blocked/source_boundary 与 work 异常被当作“证明缺失”。**
- 位置：narrative_antecedent.py:96-111（boundary 分支不置 complete=False，只有 cap）；narrative_reading.py:468-472（WorkBudgetExceeded → windows={}）；narrative_operating_relations.py:170（self.antecedents.get(uid, ((), True))）。
- 影响：unread/opaque/excluded 尾部或窗口构建失败 → missing（确定缺失），而不是 partial；stop_reason 也没有 unread/work/unknown_scope。
- 建议：boundary 分类为 unread/unknown_scope/source_boundary，除真正的 section/parent 边界且已证明闭区间外一律 complete=False→partial；窗口异常显式传播为 partial；session 默认 complete=False。

**P2-3 envelope 计数：block key 错 + carrier 只算第一个 original。**
- 位置：narrative_antecedent.py:133-137（key 含 paragraph_index，用 source_id 而非 parent_id）；narrative_reading.py:522-527（[0]）。
- 复现：同页同 pdf_block、4 个不同 paragraph → within_reference_envelope False（应 True）；carrier 覆盖 4 个 original 只计 1 个 unit/字符。
- 影响：false deferral（或对 carrier 场景 undercount）；与合同 §2 的 (parent_id, physical_page, pdf_block) 不一致。
- 建议：key 改为 (parent_id, page, pdf_block)；carrier→全部 originals 的 union；补 same-page/block-different-paragraph、carrier 多 original 测试。

**P2-4 未知坐标被当作相邻。**
- 位置：narrative_antecedent.py:45-51、54-62（_position None → _adjacent True）。
- 复现：两个 unit 无 coordinates → _adjacent(...) = True。
- 影响：未证明物理顺序的 unit 可被借为前驱；合同 §2 unproved physical ordering 要停。
- 建议：未知 → False/partial；补无坐标测试。

**P2-5 collective/members 取到无关的“包括/含”子句。**
- 位置：product_reference.py:54-64、151-157（全文第一个 _COLLECTIVE_MARK 的结果复用于所有声明；裸 含 可匹配词内字）。
- 复现："公司客户包括华为、小米。公司推出X系列产品，已实现量产。" → X系列 collective=True，members 为 华为/小米。
- 影响：状态和 member_refs 错；未来若用 members 做“集体声明”，会把客户/非产品当成员。
- 建议：只在声明所在 clause/appositive 邻域找 collective marker；要求 members 是产品样式；每个声明独立算；补“客户/地区包括”负例。

**P2-6 attribution 恒为 issuer，第三方/问答归属没有保留。**
- 位置：relations.py:806-813（默认 attribution="issuer"）、846-853（只按 role 和“请问”跳过）；现有 p.THIRD_PARTY/p.ISSUER_WORD/_classify_np（relations.py:417-433）未用于声明句。
- 影响：竞对/关联方/客户句中的声明可被当作 issuer 声明；合同 §3 Preserve third-party/question attribution … rival/question source cannot become issuer。
- 建议：复用既有 NP/attribution 分类，对声明所在 clause 判 issuer/quoted_related_party/other/unknown；missing/partial 时 attribution=unknown；补竞对/客户/问题三例。

**P2-7 第二套产品 head 词典，与既有 PRODUCT_SUFFIX 分叉。**
- 位置：product_reference.py:17-32 vs patterns.py:404-410。
- 影响：合同 §1/检查 1 要求 No … product dictionary；两表覆盖不同（新表缺 材料/添加剂/试剂/药品/equipment/line/膜/树脂…，旧表缺 系列/平台/方案/技术），后续维护会漂移。
- 建议：复用 PRODUCT_SUFFIX 或从它派生 head；family marker 与 product head 分离。

**P2-8 REFERENCE_* 在 128 截断后不可见；收据没有绑定 3 个新语法模块。**
- 位置：narrative_reading.py:927-930（先 extend 再 [:128]）；真实 CN family 收据 deferral_reasons 只有 SELECTION_BUDGET:128，但实测有 2 unresolved + 1 envelope；docs/plans/du11-source-priority-2026-10-18/real-source-probe/probe.py:48-63 的 MODULES 不含 product_reference.py、relations.py、narrative_antecedent.py。
- 影响：计划 task_plan.md:15 的“CN withheld 137（2 unresolved, 1 envelope）”和“t34 显式 defer”无法从收据复核；3 个语法模块的字节变化不会改变 source_bindings，收据不能绑定被审版本；计划 task_plan.md:17 说 78 PASS，当前 79。
- 建议：截断前记录 deferred_count 和完整 reason/status 直方图（或单独 reference 诊断字段）；把 3 个模块加入 bindings；计划/收据更新到 79 和当前 SHA。

**P2-9 readiness 路径的 WorkBudget/ValueError 可能直接抛出，而不是 defer。**
- 位置：relations.py:828（self.work_budget.charge(len(predecessors)+1) 在 try 外）；narrative_operating_relations.py:158-160（只 catch WorkBudgetExceeded，_prepare_group 的 ValueError 不 catch）；narrative_reading.py:498-532（readiness 循环无 try）。
- 触发：预算接近 16M 或 group 跨 parent（ValueError）；_candidates 的 readiness 会让 select_reading_evidence 直接异常，而不是返回 partial。
- 影响：HK 已用 82.3%，接近上限的文档可能硬失败；合同要求“超限只 defer”。
- 建议：charge 放进 try；reference() catch WorkBudgetExceeded/ValueError 返回 partial；_candidates 对每个 package 的 reference 包 try，异常→defer。

**P2-10 测试覆盖不足/名不副实（详见检查 9）。**
- 位置：test_antecedent_wiring.py:119-129、138-143；test_reference_closure.py:94-98、95-102（wiring）、124-129；无 forward/internal ambiguity/offset/carrier/cross-page/task/status 测试。
- 影响：P1-1/P1-2/P1-3/P1-4 全部能通过现有 GREEN；CI 绿不能证明合同。
- 建议：按本报告 P1 的复现逐条加 RED 测试，再修；保留 RED→GREEN 记录。

**P2-11（P3 级）project/body 边界没有按合同描述符接线。**
- 位置：narrative_reading.py:469（未传 project_for）；narrative_antecedent.py:92-103（fallback tuple(sorted(str(section_key))) 是字符多重集，不是 project tuple）；body_region_key/boundary_kind/predecessor_unit_id 未实现。
- 影响：合同 §2 的 project_key/body_region_key 边界只能靠 hints.section_key 间接表达；同 section 但不同 project 时可能借到前一个 project 的声明（取决于 hints 是否带 projects）。
- 建议：从 prose ownership 传真实 project tuple；补 project 边界测试；或明确记录“section_key 已包含 project”的替代证明。

### P3（可后续修/记录）

- **P3-1** member_refs 在多个同 family 声明时取 entries[-1]（最近的），是 family 内部的 nearest-wins（relations.py:867、871-872）；虽然状态仍 unique/collective，但 member 归属可能不是最早/完整声明。
- **P3-2** analysis owner 的 reference_refs 是 analysis 文本坐标，不是 OriginalRef（relations.py:836-837）；当前未消费，但 Schema 名不副实。
- **P3-3** 纯 CJK、无“系列”的声明被丢弃（product_reference.py:154；"新一代刻蚀设备" → ()）；对 family 门禁影响有限，但 Chinese unique product 覆盖不完整。
- **P3-4** reference_closure(..., window_complete=True) 默认 True（relations.py:787）；API 调用方可以误称完整，建议设为必填或默认 False。
- **P3-5** analysis_groups 构造重复两遍（narrative_reading.py:484-490、543-552）；不影响行为，增加漂移风险。
- **P3-6** stop_reason 只有 beginning/source_boundary/cap/unproved_order，合同枚举的 unread/work/unknown_scope 没有（narrative_antecedent.py:96-111）。
- **P3-7** _validate_original_refs 不校验 parent/source（narrative_operating_relations.py:199-211）；目前前驱在 engine 已验 parent，但 defense-in-depth 不足。
- **P3-8** session references 以 owner 为 key（narrative_operating_relations.py:154-157），不同 anchor 的 antecedents 被折叠；换 anchor 不一定换结果。
- **P3-9** test_envelope... 的标题声称 2048 精确边界，实际用 3×1025，且没有 9/5/2049 first-excess（test_antecedent_wiring.py:95-102）。
- **P3-10** 声明扫描未按 unit 缓存（relations.py:851-855）；实测 CN 26/HK 2/US 12 次，无性能风险，但可避免重复。

## 3. 实际运行的命令与结果

所有命令在 C:\Users\郑曾波\Projects\company-wiki 下执行；Python 为 .venv\Scripts\python.exe；未执行 git 写操作，未修改源码/测试/配置/gold。

1. git status --porcelain
   - 变更集：3 个 M（relations.py、narrative_operating_relations.py、narrative_reading.py）+ 4 个 ??（product_reference.py、narrative_antecedent.py、两个新测试）。
   - 工作区还有大量与本任务无关的既存未跟踪计划/临时目录；未触碰。
2. git diff --stat -- src/company_wiki
   - 3 files changed, 271 insertions(+), 11 deletions(-)（最终快照）。
3. Get-FileHash ... -Algorithm SHA256（7 个文件；见附录）。
4. .venv\Scripts\python.exe -m pytest tests/unit/du11_source_closure -q
   - 最终：**79 passed in 3.67s**（17 reference_closure + 10 antecedent_wiring + 52 既有）。
   - 审查早期（09:30 快照）：77 passed；09:51–09:55 作者进程加入 family 过滤/2 个测试后为 79。未跑全量 unit（按要求，另有进程在跑）。
5. 合成反例（Python stdin，无文件写入；WorkBudget(DEFAULT_LIMITS["max_work_units"])）：
   - forward declaration → not_applicable（期望 missing）。
   - 两个内部 family → not_applicable（期望 ambiguous）。
   - CJK 换行空白前驱声明 → ref char_start=12，原文声明起点 13；raw_text[12:40] 左移。
   - p7 声明 / p8 target → window predecessors=(), complete=True, stop_reason="unproved_order"；closure missing。
   - 无坐标 _adjacent(...) = True。
   - 同页同 block 4 个 paragraph → within_reference_envelope=False；同 page+block+paragraph → True。
   - "公司客户包括华为、小米。公司推出X系列产品…" → X系列 collective，members 华为/小米。
   - 纯 CJK "新一代刻蚀设备" → find_product_declarations() 为空。
   - 单数 该设备 family=False（not_applicable），该等产品 family=True（进入门禁）——family 收敛在最终版本生效。
6. 端到端合成（text_case → select_reading_evidence → build_summary_task_plan）：
   - [DECLARATION, TARGET]：status selected、coverage True、2 spans；两个 group 各 evidence_ids=1、citation_views=(1,0)；target task context=[]。
   - [PLAIN, PLAIN, TARGET, PLAIN, PLAIN]：status partial、coverage False、4 spans、deferred REFERENCE_UNRESOLVED。
   - [PLAIN, PLAIN]：selected、coverage True、deferred []。
7. 真实源只读回放（复用 docs/plans/du11-source-priority-2026-10-18/real-source-probe/probe.py；socket.connect 阻断、COMPANY_WIKI_REAL_LLM=0、输出到系统临时目录，未写仓库；original_unchanged=True、gold_unchanged=True、api_calls=0）：
   - CN：reference() 2,518 次 = 2,515 not_applicable + 1 missing（“该系列设备已付运”，SHA b554…，antecedent_missing）+ 1 unique（SHA 8d73…）+ 1 partial（t34，SHA 8ff2…，antecedent_window_incomplete）；reference work 11,808；总 work 6,141,589 / 16,000,000；deferral_reasons 仅 SELECTION_BUDGET:128。
   - CN envelope：unique 的 required b5bf5b0c...；ENV ok=False，decl=[b8117bd8...]，not_in_units=[b8117bd8...]；即 P1-2 的实锤。
   - HK：3,578 次全部 not_applicable；reference work 18,658；总 work 13,171,440 / 16,000,000；withheld 无 REFERENCE_*。
   - US：1,118 次全部 not_applicable；reference work 7,073；总 work 7,993,452 / 16,000,000；withheld 无 REFERENCE_*。
   - 与仓库收据 b2-family-scope/cn-h1.json（6,141,589）、b2-real-sources-family/hk-annual.json（13,171,440）、us-10k.json（7,993,452）一致。

## 4. 与计划/收据的一致性（独立观察）

- task_plan.md:15 自报 “CN 6,141,589、HK 13,171,440、US 7,993,452；CN withheld 137（REFERENCE_UNRESOLVED 2、REFERENCE_ENVELOPE 1）”。我用 instrumentation 复现了 2 unresolved + 1 envelope，但仓库收据的 deferral_reasons 只显示 SELECTION_BUDGET:128；deferred_count 未写入收据，128 截断把 REFERENCE_* 隐藏了。P2-8。
- task_plan.md:17 说 78 PASS；当前目录 79 PASS（作者在 09:55 又加了一个测试/改了测试文件）。这不是代码缺陷，但说明计划/收据没有绑定最终 SHA。
- task_plan.md:5 说“没有第二套 … 产品词典”，但 product_reference.py:17-32 与 patterns.py:404-410 是两套产品 head 表（P2-7）。
- task_plan.md:9 说 envelope 按 (source,page,pdf_block)，代码实际 key 含 paragraph_index（P2-3）。
- replay.json/b2-*-family 的 source_bindings 不含 product_reference.py、relations.py、narrative_antecedent.py（probe.py:48-63），无法证明收据对应哪个语法版本（P2-8）。
- t34：我的 instrumentation 确认其 target 文本 SHA 8ff2eacd4cfb23f277697cea3e0f61701df95b2d7fd5527828b808b42092c107，状态 partial（antecedent_window_incomplete）。这是“明确 defer”，符合交接要求；但仓库收据没有把该 reason 暴露出来，不能用收据本身证明。

## 5. 无法验证的点

1. 全量 unit / 142 合同 / CI / 发布：未运行（按用户要求，另有进程在跑）；只能引用作者历史的 release 数据。
2. 正式内容 C：未调用任何 provider/model（本节点不应调用）；语义闭合、摘要质量、FF/RF 真实消费均未验证。
3. P1-2 修好 namespace 后，真实 CN 的 unique 是否仍超过 4 blocks/2048 chars：未修，无法判定；当前只能证明“因 namespace 缺失而失败”，不能证明“额度确实不够”。
4. P1-4 的 page_carries 是否可以从现有 continuity proof 完整导出、以及现有证明是否覆盖真实 t34 的跨页块：未改代码，未验证；CN t34 当前是 cap partial，不是 cross-page 路径。
5. 3 个新语法模块的字节是否进入运行期 selection cache：未找到 module-hash cache key；READING_SELECTOR_VERSION 仍 0.9.0；若存在同 version+同 source 的旧 cache，B2 行为可能不失效（未能定位/验证）。
6. task_plan.md:13 的 family-only 收敛是否符合合同 owner 对 Chinese unique product 的解释：计划声称是既有 selection 测试逼出的范围，接口文档 §6.2 仍写 Chinese unique product；需要合同 owner 裁决，我无法代替。
7. 作者是否真的保留了 RED→GREEN 顺序：只能看到最终测试全绿；未看到 RED 日志/提交历史（未做 git 操作）。
8. 收据 b2-family-scope/b2-real-sources-family 是否由当前 3 个语法模块 SHA 产生：模块未绑定，无法确认；只能确认 work/total 与我的独立复跑一致。
9. HK 13.17M/16M 的增量中 B2 占多少：没有 B2 之前的同源基线，只有当前绝对值。

## 6. 建议的修复顺序（不实施，仅供作者）

1. P1-1/P1-2/P1-3/P1-4/P1-5 各自先写 RED（本报告 §3 的复现即是），再修；修完重跑 79+ 聚焦测试。
2. 先修 envelope namespace 与 exact offset，因为它们决定“正向闭合”是否存在；再修 context 接线（否则 unique 也无意义）；再修 cross-page（否则真实场景仍 missing）；最后修内部顺序/数量。
3. 把 P2-1/P2-2 的“整篇 partial / false missing”降到卡级/partial，再跑 CN/HK/US 并核对 t34 的 reason 在收据中可见。
4. 补 P2-8 的收据字段 + 模块 bindings，重新生成 b2-* 收据并绑定最终 SHA；之后再请独立 reviewer 对最终 SHA 复审（旧 SHA 的报告不能签给新代码）。

## 附录：最终审查快照（2026-10-18 09:55–10:05）

| 文件 | SHA256 | 最后写入 |
|---|---|---|
| src/company_wiki/document_understanding/operating_states/product_reference.py | 75ba4128e7c73c294f8181ad407192835b7caac9b01693d5feedcbf3961c4f69 | 09:51:29 |
| src/company_wiki/document_understanding/operating_states/relations.py | 919fdc52f05b8a25aefffdcb96d45120e8a71c975f29d33aade76c51c313c55e | 09:51:29 |
| src/company_wiki/source_catalog/narrative_antecedent.py | da6723ce8f6bad008294312c77110a2d8333204a6effa179173d629ebfc15aa0 | 09:29:18 |
| src/company_wiki/source_catalog/narrative_operating_relations.py | 4ff59eda06cd65a4c564b2312759f6c28dc4fd66a4c27405f79830e203fd63d1 | 09:30:39 |
| src/company_wiki/source_catalog/narrative_reading.py | e5ff0ced9b8007174fc9a5a8557b1b5aaee2df977b989530e0c1edd004968280 | 09:30:04 |
| tests/unit/du11_source_closure/test_reference_closure.py | aa5085ed3e067fd8ad0b9225bbcea69ba41bb007f00329f777687d99dad8763b | 09:55:26 |
| tests/unit/du11_source_closure/test_antecedent_wiring.py | 2fd9981a5c38955e0bb0b1a1d394ac1202a71b3e3b48eb41bf6650ea49e43d36 | 09:44:48 |

HEAD：710f0de1（git log --oneline -3 的首行；审查未做 git 写操作）。工作区在本报告写入前仍有作者进程的未提交改动；本表是审查绑定的代码快照，报告不绑定后续新 SHA。
