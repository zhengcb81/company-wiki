"""S7 operating semantics compete under a fixed evidence budget."""
import pytest
from dataclasses import replace

from company_wiki.source_catalog.n6_candidate_operating_facts import detect_operating_fact
from company_wiki.source_catalog.narrative_candidates import assess_unit
from company_wiki.source_catalog.narrative_evidence import _candidate_rules, _make_unit
from company_wiki.source_catalog.narrative_budget import BudgetItem, select_budget_items
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256
from company_wiki.source_catalog.narrative_group_candidates import _merge_fact_windows


def fragment(index, text):
    return _make_unit(source_id=source_id_for_sha256('c' * 64), parser_version='0.1.0',
                      coordinates=EvidenceCoordinates(page_number=2, paragraph_index=index),
                      raw_text=text, unit_kind='pdf_text_block', source_role='company_filing',
                      language='zh', metadata={})


def test_adjacent_fact_windows_keep_one_unfinished_sentence_atomic():
    members = (fragment(0, '进口设备占比由37%下降至31%，一定'),
               fragment(1, '程度上说明自主供应能力增强，进口替代速度加快。'))
    assert _merge_fact_windows(((0, 0), (1, 1)), members=members) == ((0, 1),)


def test_adjacent_complete_facts_are_independent():
    members = (fragment(0, '进口设备占比下降。'), fragment(1, '另一新产品完成验证。'))
    assert _merge_fact_windows(((0, 0), (1, 1)), members=members) == ((0, 0), (1, 1))


@pytest.mark.parametrize('field,value', [('language', 'en'), ('source_role', 'management'),
                                       ('parser_version', 'next'), ('metadata', {'speaker': 'another'})])
def test_fact_window_completion_does_not_cross_identity_or_discourse(field, value):
    members = (fragment(0, '未完的产品描述，'), replace(fragment(1, '后续业务描述。'), **{field: value}))
    assert _merge_fact_windows(((0, 0), (1, 1)), members=members) == ((0, 0), (1, 1))


@pytest.mark.parametrize('count,size', [(9, 20), (2, 900)])
def test_fact_window_completion_retains_member_and_character_limits(count, size):
    members = tuple(fragment(i, '业' * size + '，') for i in range(count))
    merged = _merge_fact_windows(tuple((i, i) for i in range(count)), members=members)
    assert all(end - start + 1 <= 8 for start, end in merged)
    assert all(sum(len(m.raw_text) for m in members[start:end + 1]) <= 1600 for start, end in merged)


@pytest.mark.parametrize(('text', 'reason'), [
    ('工业机器人设备已应用于客户汽车生产线，已经实现批量销售。', 'applied_operating_milestone'),
    ('公司拟通过发行股份及支付现金收购一家工业软件企业控股权，以扩展业务产品组合。', 'corporate_development'),
    ('公司已完成收购新型材料企业，形成上下游生产业务协同。', 'corporate_development'),
    ('据行业协会预测，全球储能设备市场销售额今年将达1800亿元，同比增长15%。', 'quantified_industry_outlook'),
    ('2018—2023年进口机床占总消费的比重从37.5%下降至31.2%，自主供应能力增强。', 'quantified_industry_change'),
    ('本次募集资金拟用于高端设备生产线建设项目和材料研发中心建设项目。', 'concrete_fundraising_project'),
    ('本次募投项目达产后，预计新增动力电池产品50万套和工业设备140万台。', 'incremental_project_capacity'),
])
def test_concrete_operating_facts_keep_their_semantic_category(text, reason):
    fact = detect_operating_fact(text)
    assert fact.eligible
    assert reason in fact.reasons


def test_existing_generic_progress_cannot_hide_new_specific_fact_reasons():
    body = _make_unit(source_id=source_id_for_sha256('b' * 64), parser_version='0.1.0',
                      coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
                      raw_text='公司新设备已应用于客户生产线并实现批量销售。',
                      unit_kind='pdf_text_block', source_role='company_filing', language='zh', metadata={})
    candidate = assess_unit(body, _candidate_rules()).candidate
    assert candidate is not None
    assert 'applied_operating_milestone' in candidate.reasons


@pytest.mark.parametrize('text', [
    '公司预计明年营业收入将达1800万元。',
    '募集资金总额预计新增50亿元。',
    '募集资金投资于以下项目。',
])
def test_financial_amounts_or_an_introduction_alone_are_not_concrete_projects(text):
    fact = detect_operating_fact(text)
    assert 'concrete_fundraising_project' not in fact.reasons
    assert 'incremental_project_capacity' not in fact.reasons
    assert 'quantified_industry_outlook' not in fact.reasons


@pytest.mark.parametrize('text', [
    '公司计划通过股权投资、并购等方式进行布局，以拓展公司业务领域。',
    '在进行投资和并购项目实施过程中，将面临投资风险及并购风险。',
    '虽然公司未来并购时将继续秉承审慎原则，相应制定整合计划，防范并购风险。',
])
def test_generic_merger_strategy_or_risk_is_not_a_concrete_transaction(text):
    assert 'corporate_development' not in detect_operating_fact(text).reasons


def test_operating_milestones_and_named_projects_are_not_generic_event_filler():
    def item(name, page, reason, score):
        return BudgetItem(item_id=name, group_id=None, page_key=('page', page),
                          locator=f'loc:v1/page:{page}', order_key=(page,),
                          reasons=(reason,), score=score, is_heading=False, payload=name)
    filler = tuple(item(f'filler-{i}', i + 1, 'specific_business_event', 50) for i in range(30))
    rare = (item('applied', 90, 'applied_operating_milestone', 3),
            item('acquisition', 91, 'corporate_development', 3),
            item('named-project', 92, 'concrete_fundraising_project', 3),
            item('capacity', 93, 'incremental_project_capacity', 3),
            item('industry-outlook', 94, 'quantified_industry_outlook', 3))
    chosen = select_budget_items((*filler, *rare), limit=16)
    assert {r.item_id for r in rare} <= {r.item_id for r in chosen}
    assert len(chosen) == 16
    assert chosen == select_budget_items(tuple(reversed((*filler, *rare))), limit=16)


def test_quantified_industry_facts_are_not_drowned_by_many_background_pages():
    def item(name, page, reasons, score):
        return BudgetItem(item_id=name, group_id=None, page_key=('page', page),
                          locator=f'loc:v1/page:{page}', order_key=(page,),
                          reasons=reasons, score=score, is_heading=False, payload=name)
    items = tuple(item(f'background-{i}', i + 1, ('current_industry_context',), 50)
                  for i in range(30)) + (
        item('forecast', 1, ('quantified_industry_outlook', 'current_industry_context'), 3),
        item('trend', 2, ('quantified_industry_change', 'current_industry_context'), 3),
        item('project', 50, ('project_plan_or_status',), 3),
        item('event', 51, ('specific_business_event',), 3),
    )
    selected = select_budget_items(items, limit=8)
    assert {'forecast', 'trend'} <= {i.item_id for i in selected}
    assert len(selected) == 8
