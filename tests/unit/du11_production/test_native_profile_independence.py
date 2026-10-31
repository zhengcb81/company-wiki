"""Reading strategy annotations cannot split a measured physical sentence."""
from copy import deepcopy

import pytest

from unit.document_understanding_selection.test_reading_native_continuity import native, run


@pytest.mark.parametrize('right_profile', [
    {},
    {'reading_profile_key': None, 'section_role': 'questions'},
    {'reading_profile_key': 'fallback', 'section_role': 'unknown'},
])
@pytest.mark.parametrize('texts', [
    ('公司的排产将根据客户订单保留一定灵', '活性。'),
    ('Production is planned for next year, subject to customer', 'orders and regulatory approval.'),
])
def test_measured_sentence_does_not_depend_on_optional_reading_strategy(right_profile, texts):
    rows = [native(text, index) for index, text in enumerate(texts)]
    rows[0][2].update(reading_profile_key='investor_qa:rule-a', section_role='questions')
    rows[1] = (rows[1][0], rows[1][1], deepcopy(right_profile))
    before = deepcopy(rows)
    result = run(rows)
    assert len(result['windows']) == 1
    assert result['windows'][0]['member_unit_ids'] == [row[0]['unit_id'] for row in rows]
    assert result['complete']
    assert rows == before


@pytest.mark.parametrize('change', ['section', 'role', 'heading', 'source', 'finished'])
def test_original_source_boundaries_remain_authoritative(change):
    rows = [native('设备验证仍需客户', 0), native('批准。', 1)]
    rows[1] = (rows[1][0], rows[1][1], {})
    if change == 'section':
        rows[1][0]['hints']['section_key'] = 'new-observed-section'
    elif change == 'role':
        rows[1][0]['role'] = 'investor_question'
    elif change == 'heading':
        rows[1][0]['kind'] = 'heading'
    elif change == 'source':
        rows[1][1]['source_id'] = rows[1][0]['hints']['source_id'] = 'different-source'
    else:
        rows[0] = native('上一个陈述已经完成。', 0)
    assert not run(rows)['windows']


def test_a_new_physical_block_does_not_certify_a_dangling_sentence_tail():
    rows = [
        native('订单规划仍需保持一定灵', 0),
        native('活性。', 1, block=1, box=[90, 400, 550, 432]),
        native('后续项目仍待审批。', 2, block=1, start=3, box=[90, 400, 550, 432]),
    ]
    result = run(rows)
    # The large unproven gap cannot be repaired by pretending that the second
    # PDF block starts an independent sentence. A partial result is honest.
    assert all(rows[1][0]['unit_id'] not in w['member_unit_ids'] for w in result['windows'])
    assert rows[1][0]['unit_id'] in result['deferred_unit_ids']


@pytest.mark.parametrize('marker', ['Q:', 'Q：', 'Question:', '问：', 'A:', 'Answer:', '答：'])
def test_an_explicit_new_turn_cannot_complete_a_previous_dangling_statement(marker):
    rows = [native('A: The first project remains subject to', 0),
            native(marker + ' Please discuss a different project.', 1)]
    rows[1] = (rows[1][0], rows[1][1], {})
    assert not run(rows)['windows']


@pytest.mark.parametrize('question,answer', [('Q：如何排产？', 'A：根据客户订单排产。'),
                                           ('Question: How is output scheduled?', 'Answer: Output follows orders.')])
def test_shared_qa_structure_recognizes_source_markers_without_a_reading_profile(question, answer):
    from company_wiki.document_understanding.structure.qa import _is_question_start, _is_answer_start
    from types import SimpleNamespace
    def unit(text):
        return SimpleNamespace(text=text, kind='paragraph', role='company_filing', speaker=None,
                               turn_id=None, is_table_furniture=False, is_header_furniture=False)
    assert _is_question_start(unit(question))
    assert _is_answer_start(unit(answer))
    assert not _is_question_start(unit(answer))


def test_page_carry_cannot_absorb_a_new_question_even_with_positive_page_geometry():
    from company_wiki.document_understanding.narrative_continuity import build_native_continuity, SourcePageFlow
    rows = [native('The plant remains subject to', 0, box=[90, 740, 550, 752]),
            native('Q: What is the next project?', 1, page=8, box=[90, 60, 550, 72])]
    result = build_native_continuity([r[0] for r in rows],
        provenance={r[0]['unit_id']: r[1] for r in rows},
        source_page_flow=SourcePageFlow(frozenset(), lambda text: False))
    assert not result['windows']


@pytest.mark.parametrize('key', ['speaker', 'turn_id'])
def test_observed_speaker_or_turn_switch_is_not_a_reading_strategy_hint(key):
    rows = [native('The factory remains subject to', 0), native('customer approval.', 1)]
    rows[0][0]['hints'][key] = 'first'
    rows[1][0]['hints'][key] = 'second'
    assert not run(rows)['windows']


@pytest.mark.parametrize('texts', [
    ['Q: First question still unfinished', 'Q: What is the new factory schedule?', 'A: It is planned for next year.'],
    ['问：第一个尚未说完的问题', '问：新工厂何时投产？', '答：新工厂计划明年投产。'],
])
def test_explicit_question_overrides_unmarked_tail_continuation(texts):
    from company_wiki.document_understanding.structure.contract import ObservationUnit
    from company_wiki.document_understanding.structure.layout import Ordering
    from company_wiki.document_understanding.structure.qa import build_qa_exchanges
    units = tuple(ObservationUnit({'unit_id': f'u{i}', 'text': text, 'kind': 'paragraph',
                                  'role': 'company_filing'}, i) for i, text in enumerate(texts))
    drafts, _ = build_qa_exchanges(units, Ordering(units, frozenset(), frozenset(), frozenset(), ()),
                                  {}, limits={'max_group_members': 64}, consumed=set())
    assert len(drafts) == 2
    assert drafts[0].completeness == 'partial' and not drafts[0].answer_ids
    assert drafts[1].question_ids == ['u1'] and drafts[1].answer_ids == ['u2']
    assert 'u0' not in drafts[1].member_ids


@pytest.mark.parametrize('key', ['speaker', 'turn_id'])
def test_missing_middle_hint_cannot_bridge_two_observed_turns(key):
    rows = [native('The factory remains subject to', 0),
            native('further review and', 1), native('approval.', 2)]
    rows[0][0]['hints'][key] = 'first'
    rows[2][0]['hints'][key] = 'second'
    result = run(rows)
    assert all(not {rows[0][0]['unit_id'], rows[2][0]['unit_id']} <= set(w['member_unit_ids'])
               for w in result['windows'])


@pytest.mark.parametrize('label', ['附件一：', '附錄二：參與人員', 'Appendix A: Participants', 'Annex 2'])
def test_explicit_appendix_is_a_source_heading_and_ends_an_answer(label):
    from company_wiki.document_understanding.structure.contract import ObservationUnit
    from company_wiki.document_understanding.structure.layout import Ordering, is_heading
    from company_wiki.document_understanding.structure.qa import build_qa_exchanges
    texts = ['Q: What is the production plan?', 'A: Production is planned for next year.', label, 'List of meeting attendees']
    units = tuple(ObservationUnit({'unit_id': f'u{i}', 'text': text, 'kind': 'paragraph',
                                  'role': 'company_filing'}, i) for i, text in enumerate(texts))
    assert is_heading(units[2])
    drafts, _ = build_qa_exchanges(units, Ordering(units, frozenset(), frozenset(), frozenset(), ()),
                                  {}, limits={'max_group_members': 64}, consumed=set())
    assert len(drafts) == 1 and drafts[0].answer_ids == ['u1']


@pytest.mark.parametrize('after_question', [False, True])
def test_source_side_column_label_cannot_become_an_answer_fragment(after_question):
    from company_wiki.document_understanding.structure.contract import ObservationUnit
    from company_wiki.document_understanding.structure.layout import Ordering
    from company_wiki.document_understanding.structure.qa import build_qa_exchanges
    texts = (['Q: What is the production plan?', 'Activity record', 'A: Production depends on', 'customer approval.']
             if after_question else
             ['Q: What is the production plan?', 'A: Production depends on', 'Activity record', 'customer approval.'])
    label_index = 1 if after_question else 2
    units = tuple(ObservationUnit({'unit_id': f'u{i}', 'text': text, 'kind': 'paragraph',
        'role': 'company_filing', 'page': 1, 'layout': {'bbox': [50, 120, 130, 130] if i == label_index
            else [145, 100 + i * 20, 545, 110 + i * 20]}}, i) for i, text in enumerate(texts))
    drafts, _ = build_qa_exchanges(units, Ordering(units, frozenset(), frozenset(), frozenset(), ()),
                                  {}, limits={'max_group_members': 64}, consumed=set())
    assert len(drafts) == 1 and drafts[0].answer_ids == (['u2', 'u3'] if after_question else ['u1', 'u3'])


def test_long_observed_continuations_do_not_pay_for_unused_language_fallback():
    rows = []
    for i in range(128):
        text = 'The next phase is subject to' if i % 2 == 0 else ('further customer review and ' * 16) + 'approval.'
        rows.append(native(text, i, page=7 + i // 20,
                           box=[90, 100 + (i % 20) * 20, 550, 112 + (i % 20) * 20]))
    result = run(rows, max_work_units=200_000)
    assert result['complete']
    assert result['observed_unit_count'] == len(rows)
    assert len(result['windows']) == 64
    assert result['work_units'] < 200_000
