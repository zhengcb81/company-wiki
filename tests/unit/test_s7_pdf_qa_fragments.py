"""Version-bound investor Q&A keeps actual cell offsets and discourse."""

from dataclasses import replace
import hashlib

import pytest

from company_wiki.source_catalog import narrative_evidence as n
from company_wiki.source_catalog.narrative_replay import verify_replayed_pdf_spans
from company_wiki.source_contract import EvidenceSpan, source_id_for_sha256


CELL = ('答：工业设备。\n4：高端设备产品结构一直在变化吗？\n'
        '答：目前高端设备占比在15%-20%，其他产品占比在80%-85%。\n'
        '5：海外订单比往年增长了吗？\n答：是的。\n'
        '各方还就新产品进行了交流，可参阅前次活动记录。\n'
        '接待过程中，公司严格按照信息披露管理制度保证信息公平，没有泄露重大信息。')


def emitted(text=CELL, *, version='0.1.1', page=1, row=0, digest='d'):
    state = n._PdfParseState(source_id_for_sha256(digest * 64), digest * 64, version, 'zh')
    n._emit_pdf_row(state, page, 0, row, ('问答记录', text), ('项目', '内容'), (40, 80, 520, 700))
    return tuple(u for u in state.units if u.unit_kind == 'pdf_table_qa_fragment')


def test_numeric_questions_and_sentence_answers_have_exact_cell_ranges():
    parts = n._pdf_qa_parts(CELL, group_prefix='p1:t0:r0:c1', parser_version='0.1.1')
    questions = [p for p in parts if p['role'] == 'investor_question']
    assert [p['question_number'] for p in questions] == ['4', '5']
    assert len({p['qa_group_id'] for p in questions}) == 2
    assert all(CELL[p['start']:p['end']] == p['text'] for p in parts)
    answers = [p for p in parts if p['role'] == 'management']
    assert len(answers) == 5  # prefix, real fact, yes, cross-reference, disclosure
    assert all(not ('占比' in p['text'] and '信息披露' in p['text']) for p in answers)


def test_legacy_parser_keeps_the_original_whole_orphan_cell():
    parts = n._pdf_qa_parts(CELL, group_prefix='p1:t0:r0:c1', parser_version='0.1.0')
    assert len(parts) == 1 and parts[0]['text'] == CELL
    old = n._link_cross_page_qa(emitted(version='0.1.0'))
    assert len(old) == 1 and old[0].metadata['qa_state'] == 'orphan_answer_needs_review'
    assert old[0].metadata['cell_fragment_start'] == 0
    assert old[0].metadata['cell_fragment_end'] == len(CELL)


@pytest.mark.parametrize('marker', ['问：', '问题：', '1、问：', '2. 问：', '6：', '6：问：'])
def test_explicit_and_numeric_markers_preserve_planned_and_negated_answers(marker):
    text = f'  {marker} 新产线何时投产？\n 答：新产线尚未投产，预计明年启动。  '
    parts = n._pdf_qa_parts(text, group_prefix='cell', parser_version='0.1.1')
    assert [p['role'] for p in parts] == ['investor_question', 'management']
    assert parts[1]['text'] == '答：新产线尚未投产，预计明年启动。'
    assert all(text[p['start']:p['end']] == p['text'] for p in parts)


@pytest.mark.parametrize('text', ['2026：年度营业收入100万元', '14:30 开始现场参观',
                                  '1:2 产品配比，3:4 原料比例', '1：设备生产线建设项目。\n2：研发中心建设项目。',
                                  '202：主要会计指标如下。'])
def test_dates_ratios_and_numbered_projects_are_not_questions(text):
    assert n._pdf_qa_parts(text, group_prefix='cell', parser_version='0.1.1') == []


def test_same_answer_in_two_questions_has_two_distinct_unit_identities():
    units = emitted('4：新产品是否完成验证？\n答：公司新产品已通过客户验证。\n'
                    '5：另一个新产品是否完成验证？\n答：公司新产品已通过客户验证。')
    answers = [u for u in units if u.source_role == 'management']
    assert len(answers) == 2 and answers[0].raw_text == answers[1].raw_text
    assert answers[0].unit_id != answers[1].unit_id
    assert answers[0].metadata['qa_group_id'] != answers[1].metadata['qa_group_id']


def test_selector_keeps_business_fact_and_its_question_without_tail_boilerplate():
    units = n._link_cross_page_qa(emitted())
    parsed = n.NarrativeParseResult(units[0].source_id, 'd' * 64, 'zh', units,
                                   page_count=1, pages_read=1)
    result = n.select_narrative_evidence(parsed, title='投资者关系活动记录表', existing_kind='investor_relations')
    assert any('占比在15%-20%' in (s.raw_text or '') for s in result.evidence_spans)
    assert any(s.structured_value['source_role'] == 'investor_question' for s in result.evidence_spans)
    assert not any('参阅' in (s.raw_text or '') or '信息披露' in (s.raw_text or '') for s in result.evidence_spans)
    for unit in units:
        assert unit.metadata['cell_sha256'] == hashlib.sha256(CELL.encode()).hexdigest()
        assert CELL[unit.metadata['cell_fragment_start']:unit.metadata['cell_fragment_end']] == unit.raw_text


def test_cross_cell_continuation_links_every_answer_sentence_to_one_question():
    question = emitted('7：新产线项目计划怎样？', page=1, row=3)
    answers = emitted('答：新产线尚未投产。预计明年启动。', page=2)
    linked = n._link_cross_page_qa((*question, *answers))
    assert len(linked) == 3
    assert len({u.metadata['qa_group_id'] for u in linked}) == 1
    assert all(u.metadata['qa_question_number'] == '7' for u in linked)
    assert all('cross_page' in u.metadata['qa_state'] for u in linked)


@pytest.mark.parametrize('change', [{'source_id': source_id_for_sha256('e' * 64)},
                                    {'parser_version': '0.1.0'}, {'language': 'en'}])
def test_new_qa_linker_never_borrows_a_question_from_another_identity(change):
    question = emitted('7：新产线项目计划怎样？', page=1, row=3)
    answers = tuple(replace(u, **change) for u in emitted('答：新产线尚未投产。', page=2))
    linked = n._link_cross_page_qa((*question, *answers))
    assert linked[-1].metadata['qa_group_id'] is None
    assert linked[-1].metadata['qa_state'] == 'orphan_answer_needs_review'


def test_new_qa_linker_rejects_a_distant_page_and_does_not_leak_to_next_cell():
    question = emitted('7：新产线项目计划怎样？', page=1, row=3)
    distant = n._link_cross_page_qa((*question, *emitted('答：预计明年启动。', page=4)))
    assert distant[-1].metadata['qa_group_id'] is None
    first = emitted('答：新产线尚未投产。预计明年启动。', page=2)
    next_cell = emitted('答：公司新产品已通过客户验证。', page=2, row=1)
    linked = n._link_cross_page_qa((*question, *first, *next_cell))
    assert linked[-1].metadata['qa_group_id'] is None
    assert linked[-1].metadata['qa_state'] == 'orphan_answer_needs_review'


@pytest.mark.parametrize('key,value', [('cell_fragment_start', 1), ('cell_fragment_end', 1),
                                      ('cell_sha256', 'f' * 64), ('cell_fragment_sha256', 'f' * 64),
                                      ('qa_group_id', 'wrong-question'), ('qa_question_number', '99')])
def test_new_fragment_replay_detects_a_tampered_origin_or_question(key, value):
    unit = next(u for u in emitted() if '占比' in u.raw_text)
    span = unit.to_evidence_span(topics=(), selection_reasons=())
    assert verify_replayed_pdf_spans((span,), (unit,)) == ((span.span_id,), ())
    structured = dict(span.structured_value)
    structured[key] = value
    changed = EvidenceSpan.create(source_id=span.source_id, coordinates=span.coordinates,
                                  raw_text=span.raw_text, structured_value=structured,
                                  parser_name=span.parser_name, parser_version=span.parser_version,
                                  parse_status=span.parse_status, quality_flags=span.quality_flags)
    assert verify_replayed_pdf_spans((changed,), (unit,)) == ((), (changed.span_id,))


@pytest.mark.parametrize('change', [{'parser_version': '0.1.0'},
                                    {'parser_name': 'another-parser'}, {'source_role': 'investor_question'}])
def test_new_fragment_replay_rejects_changed_parser_identity_or_role(change):
    unit = next(u for u in emitted() if '占比' in u.raw_text)
    span = unit.to_evidence_span(topics=(), selection_reasons=())
    structured = dict(span.structured_value)
    structured['source_role'] = change.get('source_role', structured['source_role'])
    changed = EvidenceSpan.create(source_id=span.source_id, coordinates=span.coordinates,
                                  raw_text=span.raw_text, structured_value=structured,
                                  parser_name=change.get('parser_name', span.parser_name),
                                  parser_version=change.get('parser_version', span.parser_version),
                                  parse_status=span.parse_status, quality_flags=span.quality_flags)
    assert verify_replayed_pdf_spans((changed,), (unit,)) == ((), (changed.span_id,))
