import sys
sys.path[:0] = ['src', 'tests']
from collections.abc import Mapping
import pytest
from unit.du11_production.test_qa_closed_scopes import case, admitted_cards, BUSINESS, FINANCIAL, GREETING
from unit.document_understanding_selection.test_reading_structured_qa import _unit, _select

def _joint_in_actual_cards(parts, answers, *, forbidden=()):
    _, selected = case(answers)
    cards = admitted_cards(selected)
    assert cards
    assert any(set(parts) <= members for _, members in cards)
    for card, members in cards:
        assert not set(parts).intersection(members) or set(parts) <= members
        quoted = {span.raw_text for span in card.support}
        assert not set(parts).intersection(quoted) or set(parts) <= quoted
        assert not set(forbidden).intersection(members)
        assert set(card.task.member_ids) == set(card.task.support_ids) | set(card.task.context_ids)

def test_reporting_subject_cannot_detach_postposed_restriction():
    restriction = '公司表示，该设备尚未完成量产认证。'
    _joint_in_actual_cards([BUSINESS, restriction], [BUSINESS, restriction, FINANCIAL], forbidden=[FINANCIAL])

def test_intervening_finance_cannot_hide_restriction_or_attach_to_it():
    restriction = '该设备尚未完成量产认证。'
    _joint_in_actual_cards([BUSINESS, restriction], [BUSINESS, FINANCIAL, restriction], forbidden=[FINANCIAL])

def test_reporting_subject_keeps_both_sides_of_an_explicit_cause():
    result = '公司催化材料业务收入下降。'
    cause = '公司认为，这一变化主要由于下游需求减少。'
    _joint_in_actual_cards([result, cause], [result, cause, GREETING], forbidden=[GREETING])

def test_plain_financial_and_thanks_are_absent_from_actual_card_cost():
    _, selected = case([BUSINESS, FINANCIAL, GREETING])
    cards = admitted_cards(selected)
    assert cards
    assert all({FINANCIAL, GREETING}.isdisjoint(members) for _, members in cards)

def test_qualified_question_never_donates_an_answer_actor_or_product():
    q = _unit('本公司专用设备是否已经完成客户认证？', 'investor_question', 0)
    a = _unit('已经完成客户认证。', 'management', 1)
    assert not admitted_cards(_select(q, a))

def test_another_record_cannot_donate_qualification():
    q1 = _unit('交付情况如何？', 'investor_question', 0, group='record-1')
    a1 = _unit(BUSINESS, 'management', 1, group='record-1')
    q2 = _unit('另一设备认证情况如何？', 'investor_question', 2, group='record-2')
    a2 = _unit('该设备尚未完成量产认证。', 'management', 3, group='record-2')
    for _, members in admitted_cards(_select(q1,a1,q2,a2)):
        assert not {a1.raw_text,a2.raw_text} <= members

def test_scope_registration_does_not_copy_unrelated_contexts_without_work():
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.resource_budget import new_document_work_budget
    class Contexts(Mapping):
        def __init__(self): self.visits=0
        def __len__(self): return 100
        def __iter__(self):
            for index in range(100):
                self.visits += 1
                yield 'irrelevant-scope-' + str(index)
        def __getitem__(self, key): return ()
    unit = _unit(BUSINESS,'management',0)
    contexts = Contexts()
    budget = new_document_work_budget()
    session = SourceOperatingSession({unit.unit_id:unit},work_budget=budget,contexts=contexts)
    before = budget.used
    session.support_owner((unit.unit_id,))
    assert contexts.visits <= budget.used-before

def test_different_meaning_context_has_distinct_immutable_prepared_scope():
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from company_wiki.resource_budget import new_document_work_budget
    items = [_unit(BUSINESS,'management',0),_unit('该设备尚未完成量产认证。','management',1)]
    budget = new_document_work_budget()
    session = SourceOperatingSession({u.unit_id:u for u in items},work_budget=budget)
    first = session.support_owner((items[0].unit_id,))
    second = session.support_owner((items[0].unit_id,),meaning_context=(items[1].unit_id,))
    assert first != second
    session.fact(first)
    before=budget.used
    assert session.support_owner((items[0].unit_id,)) == first
    session.fact(first)
    assert budget.used==before

def test_original_partial_qa_remains_readable_but_is_not_whole_support():
    selected = _select(_unit(BUSINESS, 'management', 0))
    assert BUSINESS in {s.raw_text for s in selected.evidence_spans}
    views = [v for g in selected.reading_context['groups'] for v in g['citation_views']]
    assert views and all(v['reading_support_use'] != 'support' for v in views)
    assert not admitted_cards(selected)

@pytest.mark.parametrize('courtesy', ('谢谢您的关注。', 'Thank you for your continued support.'))
def test_plain_polite_synonyms_do_not_enter_source_card_or_cost(courtesy):
    _, selected = case([BUSINESS, courtesy, FINANCIAL])
    cards = admitted_cards(selected)
    assert cards
    assert all(courtesy not in members and FINANCIAL not in members for _, members in cards)

def test_multiple_qualifications_on_the_same_bound_object_are_one_scope():
    restrictions = ['该设备尚未完成量产认证。', '该设备尚未完成客户认证。']
    _joint_in_actual_cards([BUSINESS, *restrictions],
        [BUSINESS, *restrictions, FINANCIAL, GREETING], forbidden=[FINANCIAL,GREETING])

def test_real_pipeline_freezes_declaration_context_before_scope_assessment(monkeypatch):
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    declaration = '公司推出Orion Nexa系列检测系统，包括ZX-2、ZX-3两类产品。'
    target = '该系列产品已交付多个客户。'
    observed=[]
    original=SourceOperatingSession.fact
    def traced(self, uid):
        owner=self.owner_for(uid)
        if owner.startswith('source-scope:'):
            observed.append((self.groups.get(owner), self.context_for(owner)))
        return original(self,uid)
    monkeypatch.setattr(SourceOperatingSession,'fact',traced)
    units, selected=case([declaration,target,FINANCIAL])
    question, decl, answer=units[:3]
    assert any(members==(answer.unit_id,) and decl.unit_id in contexts for members,contexts in observed)
    assert all(question.unit_id not in contexts for _,contexts in observed)
    cards=admitted_cards(selected)
    assert any(target in members and declaration in members for _,members in cards)

def test_two_actual_original_objects_still_have_ambiguous_qualification():
    _, selected=case([BUSINESS, '本公司已交付11台另一型号专用设备。', '该设备尚未完成客户认证。'])
    assert selected.status=='partial' and not selected.coverage_complete
    assert not admitted_cards(selected)

def test_exhaustion_after_package_index_stops_before_unpaid_member_read():
    from types import SimpleNamespace
    from company_wiki.source_catalog.narrative_qa_scopes import close_qa_packages
    from company_wiki.resource_budget import WorkBudget
    class NoRead(dict):
        def __iter__(self): raise AssertionError('unpaid source iteration')
        def __getitem__(self,key): raise AssertionError('unpaid source read')
        def __contains__(self,key): raise AssertionError('unpaid member test')
    session=SimpleNamespace(units=NoRead(),work_budget=WorkBudget(1),complete=True)
    package={'kind':'qa_exchange','package_id':'qa','member_unit_ids':['u'],
             'anchor_unit_ids':['u'],'required_context_unit_ids':[],'completeness':'complete'}
    source,material,withheld=close_qa_packages([package],[package],session)
    assert not source and not material and not session.complete
    assert withheld[0]['reason']=='OPERATING_WORK_BUDGET'
