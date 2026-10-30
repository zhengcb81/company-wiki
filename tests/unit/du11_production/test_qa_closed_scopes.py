"""Frozen next-node expectations: actual public reading, no model calls."""
import pytest
from hashlib import sha256
from unit.document_understanding_selection.test_reading_structured_qa import _unit, _select
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.document_understanding.source_cards import source_cards, source_task_admission

BUSINESS = '本公司已交付27台专用设备至客户进行生产验证。'
RESTRICTION = '该设备尚未完成量产认证，不代表已经形成批量销售。'
FINANCIAL = '公司2025年营业收入为37.17亿元，归属于上市公司股东的净利润为2.84亿元。'
GREETING = '感谢您对公司的关注！'

def case(answers, *, pdf=False):
    question = _unit('请介绍公司的主要业务与产品进展？', 'investor_question', 0)
    units = [question, *(_unit(text, 'management', i+1) for i, text in enumerate(answers))]
    if not pdf:
        return units, _select(*units)
    from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
    from company_wiki.source_catalog.narrative_document import DocumentStructure
    from company_wiki.source_contract import EvidenceCoordinates
    cell = '\n'.join(u.raw_text for u in units)
    offset, physical = 0, []
    for unit in units:
        physical.append(_make_unit(source_id=unit.source_id, parser_version='0.1.1',
            coordinates=EvidenceCoordinates(page_number=1, table_index=0, row_index=0,column_index=0),
            raw_text=unit.raw_text, unit_kind='pdf_table_qa_fragment', source_role=unit.source_role, language='zh',
            metadata={'qa_group_id':'p1:t0:r0:c0:q1', 'qa_question_number':'1',
                'qa_state':'question_paired' if unit.source_role=='investor_question' else 'answer_paired',
                'cell_sha256':sha256(cell.encode()).hexdigest(), 'cell_fragment_start':offset,
                'cell_fragment_end':offset+len(unit.raw_text), 'row_cells':(cell,), 'table_headers':(cell,)}))
        offset += len(unit.raw_text)+1
    parsed=DocumentStructure(units[0].source_id, 'a'*64, 'zh', tuple(physical),
        page_count=1,pages_read=1,mime_type='application/pdf')
    selected=select_narrative_evidence(parsed,title='投资者关系问答',existing_kind='investor_relations',selector_version='0.9.0')
    return physical, selected

def supports(selected):
    texts = {span.span_id: span.raw_text for span in selected.evidence_spans}
    return [{texts[eid] for eid in view['support_evidence_ids']} for group in selected.reading_context['groups']
            for view in group['citation_views'] if view['reading_support_use'] == 'support']

def admitted_cards(selected):
    plan = build_summary_task_plan(selected.evidence_spans,
        reading_context=selected.reading_context, max_claims=64)
    spans = {s.span_id: s for s in selected.evidence_spans}
    cards = tuple(source_cards(plan, spans))
    status = source_task_admission(cards)
    return [(card, {spans[eid].raw_text for eid in card.task.member_ids})
            for card in cards if status[card.task.key]['status'] == 'admitted']

@pytest.mark.parametrize('pdf', (False,True))
@pytest.mark.parametrize('answers', (
    [BUSINESS, FINANCIAL, GREETING],
    [FINANCIAL, BUSINESS, GREETING],
))
def test_financial_and_thanks_do_not_borrow_business_support_or_prompt_membership(answers,pdf):
    units, selected = case(answers,pdf=pdf)
    assert BUSINESS in {s.raw_text for s in selected.evidence_spans}
    assert {FINANCIAL, GREETING}.isdisjoint(s.raw_text for s in selected.evidence_spans)
    forbidden = {FINANCIAL, GREETING}
    assert supports(selected) and all(not (scope & forbidden) for scope in supports(selected))
    tasks = admitted_cards(selected)
    assert tasks and all(not (members & forbidden) for _, members in tasks)
    for card, members in tasks:
        assert set(card.task.member_ids) == set(card.task.support_ids) | set(card.task.context_ids)
        assert units[0].raw_text in members

def test_later_restriction_cannot_be_detached_to_offer_a_smaller_positive_fact():
    units, selected = case([BUSINESS, RESTRICTION, FINANCIAL])
    for scope in supports(selected):
        if BUSINESS in scope:
            assert RESTRICTION in scope
    assert {BUSINESS, RESTRICTION} <= {s.raw_text for s in selected.evidence_spans}

def test_independent_business_answers_remain_distinct_closed_support_scopes():
    other = '公司已启动电子材料项目建设，项目产能为200吨每年。'
    units, selected = case([BUSINESS, FINANCIAL, other, GREETING])
    scopes = supports(selected)
    assert any(BUSINESS in scope and other not in scope for scope in scopes)
    assert any(other in scope and BUSINESS not in scope for scope in scopes)
    assert all(FINANCIAL not in scope and GREETING not in scope for scope in scopes)

@pytest.mark.parametrize('parts', (
    ['本公司已交付27台专用设备，', '客户尚未完成量产认证，不代表已经形成批量销售。'],
    ['本公司已交付27台专用设备。', '但该设备尚未完成量产认证。'],
    ['公司催化材料业务收入下降。', '这一变化主要由于下游需求减少。'],
))
def test_unfinished_or_dependent_answer_fragments_travel_together_to_actual_tasks(parts):
    _, selected = case([*parts, FINANCIAL, GREETING])
    cards = admitted_cards(selected)
    assert cards
    assert any(set(parts) <= members for _, members in cards)
    assert all(not set(parts).intersection(members) or set(parts) <= members for _, members in cards)
    assert all(FINANCIAL not in members and GREETING not in members for _, members in cards)

def test_question_premise_does_not_qualify_a_financial_answer():
    _, selected = case([FINANCIAL, GREETING])
    assert not admitted_cards(selected)

def test_a_business_unit_with_embedded_thanks_keeps_its_exact_original_bytes():
    text = BUSINESS + GREETING
    _, selected = case([text])
    assert text in {s.raw_text for s in selected.evidence_spans}

def test_an_internal_connective_in_a_new_subject_does_not_join_financial_results_to_business():
    finance = '公司收入和利润均增长，其中收入为12亿元，净利润为1亿元。'
    _, selected = case([BUSINESS, finance, GREETING])
    assert finance not in {s.raw_text for s in selected.evidence_spans}
    assert all(finance not in members for _, members in admitted_cards(selected))

def test_scope_owner_is_immutable_and_includes_meaning_context_in_cache_identity():
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.resource_budget import new_document_work_budget
    units = [_unit(BUSINESS, 'management', 0), _unit(RESTRICTION, 'management', 1)]
    budget = new_document_work_budget()
    session = SourceOperatingSession({u.unit_id:u for u in units}, work_budget=budget)
    support = (units[0].unit_id,)
    first = session.support_owner(support)
    contextual = session.support_owner(support, meaning_context=(units[1].unit_id,))
    assert first != contextual
    assert session.owner_for(units[0].unit_id) == units[0].unit_id
    session.fact(first)
    before = budget.used
    assert session.support_owner(support) == first
    session.fact(first)
    assert budget.used == before

def test_required_source_heading_outside_qa_members_is_preserved_in_the_same_projection():
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.source_catalog.narrative_qa_scopes import close_qa_packages
    from company_wiki.resource_budget import new_document_work_budget
    units = [_unit('新产品进展', 'company_filing', 0, group=None),
             _unit('业务如何？', 'investor_question', 1), _unit(BUSINESS, 'management', 2)]
    ids = [u.unit_id for u in units]
    session = SourceOperatingSession(dict(zip(ids, units)), work_budget=new_document_work_budget())
    package = {'package_id':'record-1','kind':'qa_exchange','member_unit_ids':ids[1:],
        'anchor_unit_ids':ids[2:], 'required_context_unit_ids':ids[:2], 'completeness':'complete'}
    source, material, withheld = close_qa_packages([package], [package], session)
    assert not withheld and len(source) == len(material) == 1
    assert source == material
    assert source[0]['member_unit_ids'] == ids
    assert source[0]['required_context_unit_ids'] == ids[:2]

@pytest.mark.parametrize('question_only', (False, True))
def test_missing_product_declaration_never_borrows_from_question_or_another_record(question_only):
    from unit.du11_source_closure.test_reference_closure import CN_DECLARATION, CN_TARGET
    question = _unit(CN_DECLARATION+'进展如何？' if question_only else '进展如何？',
                     'investor_question', 0, group='record-2')
    answer = _unit(CN_TARGET, 'management', 1, group='record-2')
    prior = _unit(CN_DECLARATION, 'management', 2, group='record-1')
    selected = _select(question, answer) if question_only else _select(prior, question, answer)
    assert not any(CN_TARGET in {s.raw_text for s in card.support}
                   for card, _ in admitted_cards(selected))
    assert selected.status == 'partial' and not selected.coverage_complete

def test_one_answer_product_family_closes_with_its_actual_answer_predecessor():
    from unit.du11_source_closure.test_reference_closure import CN_DECLARATION, CN_TARGET
    _, selected = case([CN_DECLARATION, CN_TARGET, FINANCIAL, GREETING])
    cards = admitted_cards(selected)
    assert any({CN_DECLARATION, CN_TARGET} <= members for _, members in cards)
    assert all(FINANCIAL not in members and GREETING not in members for _, members in cards)

def test_unknown_manufacturing_argument_is_readable_but_qa_does_not_upgrade_its_use():
    text = '本公司现无生产QX-7（甲基环氧乙烷）的情况。'
    _, selected = case([text, GREETING])
    assert text in {s.raw_text for s in selected.evidence_spans}
    assert not admitted_cards(selected)

def test_missing_pdf_fragment_or_wrong_order_is_partial_and_not_an_admitted_whole_answer():
    from dataclasses import replace
    from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
    from company_wiki.source_catalog.narrative_document import DocumentStructure
    units, _ = case([BUSINESS, FINANCIAL, GREETING], pdf=True)
    bad = units[2]
    units[2] = replace(bad, metadata={**bad.metadata,
        'cell_fragment_start':0,'cell_fragment_end':len(bad.raw_text)})
    parsed=DocumentStructure(units[0].source_id,'a'*64,'zh',tuple(units),
        page_count=1,pages_read=1,mime_type='application/pdf')
    selected=select_narrative_evidence(parsed,title='投资者关系',existing_kind='investor_relations',selector_version='0.9.0')
    assert selected.status == 'partial' and not selected.coverage_complete
    assert not admitted_cards(selected)

def test_zero_work_stops_before_any_qa_source_read_or_iteration():
    from types import SimpleNamespace
    from company_wiki.source_catalog.narrative_qa_scopes import close_qa_packages
    from company_wiki.resource_budget import WorkBudget
    class NoRead(dict):
        def __iter__(self):
            pytest.fail('unpaid source iteration')
        def __getitem__(self, _):
            pytest.fail('unpaid source read')
    session=SimpleNamespace(units=NoRead(),work_budget=WorkBudget(0),complete=True)
    package={'package_id':'qa','kind':'qa_exchange','member_unit_ids':['x']}
    source, material, withheld=close_qa_packages([package],[package],session)
    assert not source and not material
    assert not session.complete
    assert withheld[0]['reason']=='OPERATING_WORK_BUDGET'

def test_qa_expansion_keeps_non_qa_source_material_indexes_aligned():
    from company_wiki.source_catalog.narrative_qa_scopes import close_qa_packages
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.resource_budget import new_document_work_budget
    units=[_unit('进展如何？','investor_question',0),_unit(BUSINESS,'management',1),
           _unit(FINANCIAL,'management',2),_unit('公司已启动材料项目建设。','management',3)]
    ids=[u.unit_id for u in units]
    first={'kind':'project','package_id':'before','member_unit_ids':[]}
    last={'kind':'background','package_id':'after','member_unit_ids':[]}
    qa={'kind':'qa_exchange','package_id':'qa','member_unit_ids':ids,
        'anchor_unit_ids':ids[1:],'required_context_unit_ids':ids[:1],'completeness':'complete'}
    session=SourceOperatingSession(dict(zip(ids,units)),work_budget=new_document_work_budget())
    source,material,withheld=close_qa_packages([first,qa,last],[first,qa,last],session)
    assert not withheld and len(source)==len(material)==5
    assert source[0] is material[0] is first
    assert source[-1] is material[-1] is last
    assert [p['package_id'] for p in source]==[p['package_id'] for p in material]

def test_multiple_qualifiers_of_the_same_bound_source_object_keep_one_reference_identity():
    restrictions = ['该设备尚未完成量产认证。','该设备尚未完成客户认证。']
    _, selected = case([BUSINESS,*restrictions,FINANCIAL,GREETING])
    cards=admitted_cards(selected)
    assert cards and any({BUSINESS,*restrictions} <= members for _,members in cards)
    for card,members in cards:
        if BUSINESS in members:
            assert {BUSINESS,*restrictions} <= {s.raw_text for s in card.support}
            assert not {FINANCIAL,GREETING}.intersection(members)

def test_two_distinct_bound_source_objects_do_not_become_one_reference_identity():
    _,selected=case([BUSINESS,'本公司已交付13台第二型号专用设备。','该设备尚未完成客户认证。'])
    assert selected.status=='partial' and not selected.coverage_complete
    assert not admitted_cards(selected)
