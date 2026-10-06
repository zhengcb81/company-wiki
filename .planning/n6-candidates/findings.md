# N6-CANDIDATE Findings

## 已核签名（基线 58b74d0 / HEAD 81d4524，工作树干净）

- 4模块公开API与卡一致：`assess_unit(unit, rules) -> CandidateAssessment`、`build_section_context(document_kind, groups, rules) -> SectionContext`、`enrich_context_groups(groups, *, initial_candidates, initial_group_ids, project_scores, business_scores, rules) -> GroupEnrichmentResult`、`enrich_neighbor_context(units, *, initial_candidates, initial_group_ids, rules) -> NeighborEnrichmentResult`。无新DTO需求。
- 共享只读：`narrative_evidence._candidate_rules()`构造CandidateRules；`select_narrative_evidence`内联构造ContextRules/GroupCandidateRules/NeighborRules；`finalize_selection`按(text,page,role)去重、first-wins；`build_pdf_context_groups`按页聚类、同role、不查source/language。
- `NarrativeUnit`无source_sha256；`_make_unit`可用（既有测试惯例）。EvidenceCoordinates支持page/paragraph/table/row/char_start/char_end。

## 基线实测（production `_candidate_rules()` 逐条跑 required golden quotes，2026-10-06）

- 基线HIT：G-S01-01/02/04、G-S02-01、G-S03-01/02/04、G-S04-01/04、G-S05-01、G-S06-02/03、G-S07-02/03、G-S09-02。
- 基线MISS（本线目标，合成等价表达进RED）：G-S01-03(并购计划)、G-S01-05/G-S02-02(行业预测)、G-S02-03(已应用)/G-S02-04(投用+产能)、G-S03-03(新引擎)、G-S04-03(募集资金投资于项目)、G-S05-02(认证周期——certification信号不在`_pre_signal`导致topics空被早退)、G-S05-03(市场空间)、G-S06-04(进口替代/产销)、G-S07-01(境内收入占比)、G-S07-04(启动建设项目+产能)、G-S08-01(克重/一口价占比)、G-S09-01/05(EN demand continuing to exceed available capacity，topics与event都不命中)。
- 基线MISS且按卡**不修**：G-S06-01纯融资总额（卡反例）、G-S09-03/04收入指引（卡未列）。
- 反例基线全部MISS/落选（须保持）：损益行/合计/产品名财务行(dropped_financial=True)、融资总额、目录、承诺、空泛持续推进、孤立"是的"、程序性标签、募资专款专用。

## 关键结构事实

- `_expand_general`：组内已有initial命中且不在章节上下文时返回False → 整组不补全（卡点名的`_has_initial_member`缺陷）。
- `_add_general_members`/窗口adder对group_ids直接赋值 → 可静默覆盖既有不同组；成员不查source/language/页同质性。
- `_unit_by_location`键为(page,paragraph)，不含source_id → 可跨源连接；`_valid_previous`不查language。
- `narrative_context._scan_page`：超出剩余窗口长度的组仍被打分 → 单个巨组可吞掉整个上下文窗口。
- 财务排除在`assess_unit`中最先执行 → 经营对象+动作/状态定量表格行先被`financial_table`吞掉。

## 词汇决策

- reason复用：specific_business_event、project_plan_or_status、current_industry_context、direct_capacity_constraint、new_product_commercialization_milestone、current_business_progress；新增仅 `quantified_operating_status`（预算按other降级）。
- topics回落不产生overseas（S07境内口径断言）。
- fact仅在baseline `_eligible(signals)`不成立时加score，避免改动已命中候选的排序；reasons去重后追加。

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| 无PYTHONPATH时import到源仓editable安装的company_wiki | 1 | 测试内断言module __file__位于本worktree src；命令固定PYTHONPATH=$PWD/src |
