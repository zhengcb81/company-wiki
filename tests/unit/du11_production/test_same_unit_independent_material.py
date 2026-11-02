"""A local capability failure cannot veto a separately bound original clause."""
from unittest.mock import patch

import pytest

from company_wiki.document_understanding import statement_grammar as grammar
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
from unit.document_understanding_selection.test_reading_production_selection import _document, _unit


KNOWN = '公司已交付设备至客户开展生产验证，尚未完成量产认证。'
UNKNOWN = 'We aim to reopen coastal terminals.'


@pytest.mark.parametrize('first', [True, False])
def test_missing_goal_grammar_does_not_erase_independent_typed_material_in_the_same_unit(first):
    text = KNOWN + ' ' + UNKNOWN if first else UNKNOWN + ' ' + KNOWN
    parsed = _document(_unit(text, kind='html_paragraph'))
    with patch.object(grammar, '_english_tagger', side_effect=LookupError('missing local grammar model')):
        result = select_narrative_evidence(parsed, title='Annual report', existing_kind='annual_report',
                                           selector_version='0.9.0')
    assert {span.raw_text for span in result.evidence_spans} == {text}
    assert result.status == 'partial'
    assert result.reading_context['source_processing_complete'] is False
    assert any(row['code'] == 'source_grammar_unavailable' for row in result.selection_diagnostics)


@pytest.mark.parametrize('known', [
    '如果海外许可获批，公司将交付设备至客户开展生产验证。',
    '公司尚未完成设备客户认证。',
    '本公司供应商已交付设备至客户开展生产验证。',
    '公司表示，供应商尚未完成设备客户认证。',
])
def test_local_failure_cannot_change_the_known_clauses_actor_condition_or_negation(known):
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    def labels(session):
        return [(row['activity'], row['attribution'], row['modality'], row['polarity'], row['stage'])
                for row in session.relations(unit_id(0))['relations']]

    text = UNKNOWN + ' ' + known
    with patch.object(grammar, '_english_tagger', side_effect=LookupError('missing local grammar model')):
        baseline, _ = session_for([known])
        mixed, _ = session_for([text])
        assert labels(mixed) == labels(baseline)
        result = select_narrative_evidence(_document(_unit(text, kind='html_paragraph')),
                    title='Annual report', existing_kind='annual_report', selector_version='0.9.0')
    assert result.reading_context['source_processing_complete'] is False
    # A source quote is either unavailable or complete with all qualifiers. It
    # must never become the isolated positive phrase stripped of its context.
    assert all(span.raw_text == text for span in result.evidence_spans)
