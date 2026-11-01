"""Long source QA is bounded by closed components, not whole-record length."""
from types import SimpleNamespace
import pytest

from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
from company_wiki.source_catalog.narrative_qa_scopes import close_qa_packages
from unit.document_understanding_selection.test_reading_structured_qa import _unit


def run_answers(texts, *, budget=None, question="请说明产品进展？"):
    units = [_unit(question, 'investor_question', 0),
             *[_unit(t, 'management', i+1) for i, t in enumerate(texts)]]
    ids = [u.unit_id for u in units]
    session = SourceOperatingSession(dict(zip(ids, units)), work_budget=budget or WorkBudget(2_000_000))
    package = {'kind':'qa_exchange', 'package_id':'qa', 'member_unit_ids':ids,
        'anchor_unit_ids':ids[1:], 'required_context_unit_ids':ids[:1], 'completeness':'complete'}
    result = close_qa_packages([package], [package], session)
    return result, units, session


def support_sets(packages, units):
    text = {u.unit_id:u.raw_text for u in units}
    return [{text[i] for i in p['anchor_unit_ids']} for p in packages
            if p.get('_qa_scope_complete') is not False]


@pytest.mark.parametrize('count', [9,12,16])
def test_many_independent_closed_statements_are_not_whole_answer_partial(count):
    texts = [f'本公司已交付{i+1}台专用设备。' for i in range(count)]
    (source,material,withheld), units, _ = run_answers(texts)
    assert not withheld
    assert len(source) == len(material) == count
    assert set().union(*support_sets(source,units)) == set(texts)
    assert all(len(p['anchor_unit_ids']) <= 8 for p in source)


def test_twelve_native_fragments_form_four_closed_source_statements():
    parts = [t for i in range(4) for t in
        [f'本公司已交付{i+1}台', '专用设备至客户，', '客户正在进行生产验证。']]
    (source,_,withheld),units,_ = run_answers(parts)
    assert not withheld
    assert len(source) == 4
    assert all(len(p['anchor_unit_ids']) == 3 for p in source)
    assert set().union(*support_sets(source,units)) == set(parts)


def test_middle_postposed_negation_cannot_be_dropped_from_positive_support():
    business='本公司已交付27台专用设备至客户进行生产验证。'
    restriction='该设备尚未完成量产认证，不代表已经形成批量销售。'
    texts=[*[f'公司已启动第{i+1}期材料项目建设。' for i in range(5)], business, restriction,
           *[f'公司已启动第{i+1}期材料项目建设。' for i in range(5)]]
    (source,_,_),units,_=run_answers(texts)
    scopes=support_sets(source,units)
    assert any({business,restriction} <= scope for scope in scopes)
    assert all(restriction in scope for scope in scopes if business in scope)


def test_one_long_unclosed_component_is_not_truncated_or_falsely_complete():
    texts=['本公司正在根据客户的要求' for _ in range(10)]
    (source,_,withheld),units,_=run_answers(texts)
    assert withheld
    assert all(p.get('_qa_scope_complete') is False for p in source)
    assert set(source[0]['anchor_unit_ids']) == {u.unit_id for u in units[1:]}


def test_oversized_closed_component_does_not_hide_later_independent_statement():
    texts=['本公司正在根据客户的要求'+('持续验证'*60), *[('持续推进相关验证'*30) for _ in range(8)],
           '并准备交付。', '公司已启动材料项目建设。']
    (source,_,withheld),units,_=run_answers(texts)
    assert withheld
    assert any({'公司已启动材料项目建设。'} == scope for scope in support_sets(source,units))
    assert any(p.get('_qa_scope_complete') is False and len(p['anchor_unit_ids']) == 10 for p in source)


def test_long_qa_cannot_use_question_as_product_predecessor():
    from unit.du11_source_closure.test_reference_closure import CN_DECLARATION, CN_TARGET
    financial='公司2025年营业收入为37.17亿元，净利润为2.84亿元。'
    texts=[*[financial for _ in range(9)],CN_TARGET]
    (source,_,withheld),units,session=run_answers(texts,question=CN_DECLARATION+'进展如何？')
    question=units[0].unit_id
    assert withheld
    assert all(question not in p['anchor_unit_ids'] for p in source)
    assert all(question not in session._support_contexts.get(p.get('_source_scope_owner'), ()) for p in source)
    target=units[-1].unit_id
    assert all(p.get('_qa_scope_complete') is False for p in source if target in p['anchor_unit_ids'])


def test_long_qa_pair_matching_is_bounded_not_all_prefix_pairs(monkeypatch):
    calls=[]
    original=SourceOperatingSession._qualification_pair
    def observed(self,*args,**kwargs):
        calls.append(1)
        return original(self,*args,**kwargs)
    monkeypatch.setattr(SourceOperatingSession,'_qualification_pair',observed)
    texts=[f'本公司已交付{i+1}台专用设备。' for i in range(32)]
    (source,_,withheld),_,_=run_answers(texts)
    assert not withheld and len(source)==32
    assert 0 < len(calls) <= 32*8


def test_zero_budget_reads_no_source_units():
    class NoRead(dict):
        def __getitem__(self,key):
            pytest.fail('unpaid source read')
        def __iter__(self):
            pytest.fail('unpaid source iteration')
    session=SimpleNamespace(units=NoRead(),work_budget=WorkBudget(0),complete=True)
    p={'kind':'qa_exchange','package_id':'qa','member_unit_ids':['x']}
    source,material,withheld=close_qa_packages([p],[p],session)
    assert not source and not material and withheld[0]['reason']=='OPERATING_WORK_BUDGET'


def test_bare_postposed_condition_travels_with_preceding_statement_in_long_answer():
    business='本公司已启动材料产线建设。'
    restriction='但尚未获得试生产批准。'
    texts=[*[f'公司已交付{i+1}台普通设备。' for i in range(5)],business,restriction,
           *[f'公司已启动第{i+1}期仓库建设。' for i in range(5)]]
    (source,_,_),units,_=run_answers(texts)
    scopes=support_sets(source,units)
    assert all(restriction in scope for scope in scopes if business in scope)
    # Unknown construction/approval binding must remain partial, not complete
    # merely because the condition immediately follows a period.
    raw_support={u.unit_id for u in units if u.raw_text in {business,restriction}}
    assert any(raw_support <= set(p['anchor_unit_ids']) for p in source)


def test_closed_small_qa_support_can_have_more_fragments_than_antecedent_window():
    texts=['本公司已交付专用设备，', *['客户正在按不同工序逐项' for _ in range(10)],
           '进行生产验证。']
    (source,_,withheld),units,_=run_answers(texts)
    assert not withheld
    assert len(source)==1 and len(source[0]['anchor_unit_ids'])==12
    assert set(source[0]['anchor_unit_ids']) == {u.unit_id for u in units[1:]}


@pytest.mark.parametrize('restriction', [
    '该生产线尚未取得批准，实际投产时间以审批结果为准。',
    '但是，实际投产仍须取得审批。',
    '实际投产时间以审批结果为准。',
])
def test_distant_plan_restriction_is_not_lost_or_attached_to_last_delivery(restriction):
    plan='本公司计划新建专用设备生产线。'
    deliveries=[f'公司已交付{i+1}台常规检测设备。' for i in range(9)]
    (source,_,withheld),units,_=run_answers([plan,*deliveries,restriction])
    scopes=support_sets(source,units)
    assert not any(plan in scope and restriction not in scope for scope in scopes)
    assert all(not (restriction in scope and any(text in scope for text in deliveries)) for scope in scopes)
    assert all(any({text} == scope for scope in scopes) for text in deliveries)
    assert withheld or any({plan,restriction} <= scope for scope in scopes)


def test_explicit_other_business_condition_is_not_borrowed_by_original_plan_or_delivery():
    plan='本公司计划新建专用设备生产线。'
    other='另一家子公司的生产线尚未取得批准。'
    deliveries=[f'公司已交付{i+1}台常规检测设备。' for i in range(9)]
    (source,_,_),units,_=run_answers([plan,*deliveries,other])
    scopes=support_sets(source,units)
    assert any({plan} == scope for scope in scopes)
    assert all(not (other in scope and any(text in scope for text in [plan,*deliveries])) for scope in scopes)


def test_sparse_known_object_qualification_can_close_beyond_eight_without_widening_search():
    business='本公司已交付27台专用设备至客户进行生产验证。'
    restriction='该设备尚未完成量产认证，不代表已经形成批量销售。'
    unrelated=[f'公司已启动第{i+1}期仓库建设。' for i in range(9)]
    (source,_,_),units,_=run_answers([business,*unrelated,restriction])
    scopes=support_sets(source,units)
    assert any({business,restriction} <= scope for scope in scopes)
    assert all(restriction in scope for scope in scopes if business in scope)
    assert all(not (restriction in scope and text in scope) for text in unrelated for scope in scopes)


@pytest.mark.parametrize('restriction', [
    'That membrane line has not yet received approval.',
    'However, actual production is still subject to approval.',
])
def test_english_distant_unsupported_plan_is_partial_instead_of_false_closure(restriction):
    plan='The company plans to build a new membrane line.'
    other=[f'The company has delivered {i+1} diagnostic devices.' for i in range(9)]
    (source,_,withheld),units,_=run_answers([plan,*other,restriction])
    scopes=support_sets(source,units)
    assert withheld
    assert all(restriction in scope for scope in scopes if plan in scope)
    assert all(not (restriction in scope and text in scope) for scope in scopes for text in other)
    assert all(any({text} == scope for scope in scopes) for text in other)


def test_many_same_head_candidates_stay_bounded_and_do_not_hide_other_business(monkeypatch):
    calls=[]
    original=SourceOperatingSession._qualification_pair
    def observed(self,*args,**kwargs):
        calls.append(1)
        return original(self,*args,**kwargs)
    monkeypatch.setattr(SourceOperatingSession,'_qualification_pair',observed)
    plans=[f'本公司计划新建第{i+1}条生产线。' for i in range(10)]
    unrelated='公司已启动仓库建设。'
    restrictions=['该生产线尚未取得批准。' for _ in range(10)]
    (source,_,withheld),units,_=run_answers([*plans,unrelated,*restrictions])
    scopes=support_sets(source,units)
    assert withheld
    assert any({unrelated} == scope for scope in scopes)
    assert not any(any(plan in scope for plan in plans) for scope in scopes)
    assert len(calls) <= 16*len(units)


def test_bare_condition_cannot_jump_back_over_explicit_other_business_frame():
    plan='本公司计划新建专用设备生产线。'
    other='另一家子公司的生产线尚未取得批准。'
    bare='但是，实际投产仍须取得审批。'
    deliveries=[f'公司已交付{i+1}台常规检测设备。' for i in range(9)]
    (source,_,withheld),units,_=run_answers([plan,*deliveries,other,bare])
    scopes=support_sets(source,units)
    assert any({plan} == scope for scope in scopes)
    assert all(not(plan in scope and bare in scope) for scope in scopes)
    assert withheld
