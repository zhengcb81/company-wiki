"""Discourse qualification is independent of a PDF's physical table container."""
from dataclasses import replace
from hashlib import sha256

import pytest

from company_wiki.source_catalog import narrative_evidence as native
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_contract import EvidenceCoordinates
from unit.document_understanding_selection.test_reading_structured_qa import (
    SOURCE_ID, _unit,
)


def selection(question, answer, *, pdf):
    units = [_unit(question, 'investor_question', 0), _unit(answer, 'management', 1)]
    if pdf:
        cell = question + '\n' + answer
        offset = 0
        for index, unit in enumerate(units):
            units[index] = native._make_unit(source_id=SOURCE_ID, parser_version='0.1.1',
                coordinates=EvidenceCoordinates(page_number=1, table_index=0,
                    row_index=0, column_index=0), raw_text=unit.raw_text,
                unit_kind='pdf_table_qa_fragment', source_role=unit.source_role, language='zh',
                metadata={'qa_group_id':'p1:t0:r0:c0:q1',
                    'qa_state':'question_paired' if index == 0 else 'answer_paired',
                    'qa_question_number':'1', 'cell_sha256':sha256(cell.encode()).hexdigest(),
                    'cell_fragment_start':offset, 'cell_fragment_end':offset+len(unit.raw_text),
                    'row_cells':(cell,), 'table_headers':(cell,)})
            offset += len(unit.raw_text) + 1
    parsed = DocumentStructure(SOURCE_ID, 'a'*64, 'zh', tuple(units),
        page_count=1 if pdf else 0, pages_read=1 if pdf else 0,
        mime_type='application/pdf' if pdf else 'application/json')
    return native.select_narrative_evidence(parsed, title='投资者关系问答',
        existing_kind='investor_relations', selector_version='0.9.0'), units


@pytest.mark.parametrize('answer', (
    '公司现无生产ZX-9材料的情况。',
    '公司已与渠道合作伙伴签署供货合同，但尚未交付设备。',
    '公司新产品完成客户验证，第四季度开始批量交付，海外订单持续增长。',
))
def test_native_qa_table_does_not_need_operating_table_headers(answer):
    question = '请介绍当前情况。'
    expected, _ = selection(question, answer, pdf=False)
    result, units = selection(question, answer, pdf=True)
    assert {s.raw_text for s in expected.evidence_spans} == {question, answer}
    assert {s.raw_text for s in result.evidence_spans} == {question, answer}
    by_text = {s.raw_text:s.span_id for s in result.evidence_spans}
    for group in result.reading_context['groups']:
        for view in group['citation_views']:
            assert by_text[question] not in view['support_evidence_ids']
            assert by_text[answer] in view['support_evidence_ids']
            assert by_text[question] in view['context_evidence_ids']
    assert {s.locator for s in result.evidence_spans} == {
        u.to_evidence_span(topics=(), selection_reasons=()).locator for u in units}


@pytest.mark.parametrize('answer', (
    '公司感谢投资者的关注，未来将继续努力提升综合实力。',
    '本期营业收入为12亿元，净利润为1亿元。',
))
def test_qa_in_a_table_does_not_exempt_finance_or_boilerplate(answer):
    result, _ = selection('新业务是否已经投产？', answer, pdf=True)
    assert not result.evidence_spans


def test_orphan_question_in_a_table_cannot_become_business_support():
    question = '公司已量产新产品的说法属实吗？'
    unit = _unit(question, 'investor_question', 0)
    unit = replace(unit, unit_kind='pdf_table_qa_fragment',
        coordinates=EvidenceCoordinates(page_number=1, table_index=0, row_index=0, column_index=0),
        metadata={'qa_group_id':'p1:t0:r0:c0:q1', 'qa_state':'question_unanswered'})
    parsed = DocumentStructure(SOURCE_ID, 'a'*64, 'zh', (unit,), page_count=1,
        pages_read=1, mime_type='application/pdf')
    result = native.select_narrative_evidence(parsed, title='投资者关系问答',
        existing_kind='investor_relations', selector_version='0.9.0')
    assert not result.evidence_spans


@pytest.mark.parametrize('pdf', (False, True))
def test_self_contained_orphan_answer_stays_readable_but_not_complete_qa(pdf):
    text = '答：公司现无生产ZX-9材料的情况。'
    unit = _unit(text, 'management', 0, group=None)
    unit = replace(unit, parser_version='0.1.1',
        unit_kind='pdf_table_qa_fragment' if pdf else 'official_json_field',
        coordinates=EvidenceCoordinates(page_number=1, table_index=0, row_index=0, column_index=0)
            if pdf else unit.coordinates,
        metadata={'qa_state':'orphan_answer_needs_review'})
    parsed = DocumentStructure(SOURCE_ID, 'a'*64, 'zh', (unit,), page_count=1,
        pages_read=1, mime_type='application/pdf' if pdf else 'application/json')
    result = native.select_narrative_evidence(parsed, title='投资者关系问答',
        existing_kind='investor_relations', selector_version='0.9.0')
    assert {s.raw_text for s in result.evidence_spans} == {text}
    assert result.status == 'partial' and not result.coverage_complete
    assert any(d['reason'] == 'QA_CONTEXT_PARTIAL'
               for d in result.reading_context['deferred'])
