"""Capability failure remains deferred through the real public selector."""
from contextlib import nullcontext
from unittest.mock import patch

import pytest

from company_wiki.document_understanding import statement_grammar as grammar
from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment
from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
from unit.document_understanding_selection.test_reading_production_selection import _document, _unit


BUSINESS = 'Our vessels transport liquefied gas between coastal terminals.'
MIXED = BUSINESS + ' Net income was $20 million.'
OVER_SCOPE = 'Our vessels transport ' + 'liquefied ' * (grammar.MAX_STATEMENT_CHARS // 10 + 3) + 'gas between coastal terminals.'


def _select(parsed, budget=None):
    return select_narrative_evidence(parsed, title='Annual report', existing_kind='annual_report',
                                     selector_version='0.9.0', work_budget=budget)


@pytest.mark.parametrize(('text', 'missing_resource', 'reason'), (
    pytest.param(BUSINESS, True, 'source_grammar_unavailable', id='pure-business-missing-resource'),
    pytest.param(MIXED, True, 'source_grammar_unavailable', id='mixed-missing-resource'),
    pytest.param(OVER_SCOPE, False, 'source_grammar_scope_limit', id='actual-observer-scope-limit'),
))
def test_capability_failure_is_explicit_public_source_processing_deferral(text, missing_resource, reason):
    parsed = _document(_unit(text, kind='html_paragraph'))
    with patch.object(grammar, '_english_tagger', side_effect=LookupError('missing model')) if missing_resource else nullcontext():
        assessment = prepare_reading_business_assessment(text, {'relations': []})
        result = _select(parsed)
    assert result.reading_context.get('source_processing_complete') is False, (result.status, assessment.passage)
    assert result.status == 'needs_review' and not result.evidence_spans
    assert assessment.passage.use == 'unresolved' and assessment.passage.reason == reason
    assert not assessment.passage.relevant
    assert not assessment.passage.assessment_complete and assessment.financial_only is None
    assert any(row['code'] == reason for row in result.selection_diagnostics)
    context = result.reading_context
    assert any(row['reason'] == reason for row in context['deferred'])
    assert any(row['reason'] == reason and parsed.units[0].unit_id in row['known_unit_ids']
               for row in context['selection_trace']['withheld']['samples'])
    assert context['selection_trace']['admission']['rejection_counts'].get(reason, 0) > 0
    assert result.reading_dependencies['status'] == 'partial'
    # Physical parsing is fully observed; source processing is the partial axis.
    assert result.coverage_complete and parsed.coverage_complete


@pytest.mark.parametrize(('failed', 'healthy', 'missing_resource', 'reason'), (
    pytest.param(OVER_SCOPE, 'Our clinicians treat rare diseases at regional clinics.', False,
                 'source_grammar_scope_limit', id='long-scope-does-not-stop-another-scope'),
    pytest.param(BUSINESS, '公司已交付设备至客户开展生产验证，尚未完成量产认证。', True,
                 'source_grammar_unavailable', id='missing-resource-keeps-typed-proof'),
))
def test_one_deferred_scope_does_not_stop_an_independent_healthy_scope(failed, healthy, missing_resource, reason):
    parsed = _document(_unit(failed, kind='html_paragraph'), _unit(healthy, paragraph=1, kind='html_paragraph'))
    budget = new_document_work_budget()
    with patch.object(grammar, '_english_tagger', side_effect=LookupError('missing model')) if missing_resource else nullcontext():
        result = _select(parsed, budget)
    assert result.status == 'partial'
    assert result.reading_context.get('source_processing_complete') is False
    assert {span.raw_text for span in result.evidence_spans} == {healthy}
    assert result.coverage_complete and parsed.coverage_complete
    assert any(row['code'] == reason for row in result.selection_diagnostics)
    assert not any(row['code'] == 'work_budget_exhausted' for row in result.selection_diagnostics)
    assert not budget.exhausted
    assert result.reading_dependencies['status'] == 'partial'


@pytest.mark.parametrize('text', (BUSINESS, MIXED))
def test_available_business_and_mixed_scopes_select_normally(text):
    parsed = _document(_unit(text, kind='html_paragraph'))
    assessment = prepare_reading_business_assessment(text, {'relations': []})
    result = _select(parsed)
    assert assessment.passage.assessment_complete and assessment.passage.use == 'support'
    assert assessment.financial_only is False
    assert result.status == 'selected' and result.coverage_complete
    assert result.reading_context['source_processing_complete']
    assert {span.raw_text for span in result.evidence_spans} == {text}
    assert not result.reading_context['selection_trace']['withheld']['count']


def test_known_pure_finance_does_not_require_grammar_or_become_deferred():
    text = 'Net income was $20 million.'
    with patch.object(grammar, '_english_tagger', side_effect=LookupError('missing model')) as tagger:
        assessment = prepare_reading_business_assessment(text, {'relations': []})
        result = _select(_document(_unit(text, kind='html_paragraph')))
    assert assessment.passage.assessment_complete
    assert assessment.passage.use == 'context_only' and assessment.financial_only is True
    assert result.status == 'skipped_no_narrative' and result.coverage_complete
    assert result.reading_context['source_processing_complete']
    assert not result.reading_context['selection_trace']['withheld']['count']
    assert not result.selection_diagnostics
    tagger.assert_not_called()


def test_known_partial_source_reuses_prepared_dispositions_without_an_extra_scan(monkeypatch):
    from company_wiki.source_catalog import narrative_reading as reading
    from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
    from unit.document_understanding_selection.test_reading_production_selection import _package

    business = _unit('公司已交付设备至客户开展生产验证，尚未完成量产认证。', language='zh')
    background = _unit('Unclassified passage awaiting a separate source read.', paragraph=1)
    parsed = _document(business, background, opaque=(2,), language='zh')
    understood = reading._understand(parsed, title='Annual report', kind='annual_report',
                                     mime_type='application/pdf', work_budget=new_document_work_budget())
    understood['packages'].update(packages=[_package('qualified', business)], package_count=1)
    monkeypatch.setattr(reading, '_understand', lambda *_args, **_kwargs: understood)
    original = SourceOperatingSession.fact

    def assess(self, uid):
        assert uid != background.unit_id, 'full disposition scan cannot turn this source complete'
        return original(self, uid)

    monkeypatch.setattr(SourceOperatingSession, 'fact', assess)
    result = _select(parsed)
    assert result.status == 'partial' and not result.reading_context['source_processing_complete']
    assert {span.raw_text for span in result.evidence_spans} == {business.raw_text}
    assert not any(row['code'] == 'work_budget_exhausted' for row in result.selection_diagnostics)
    assert not result.dropped_financial_count


def test_clear_fragment_is_rejected_without_capability_deferral():
    text = 'Our vessels that are transporting gas.'
    assessment = prepare_reading_business_assessment(text, {'relations': []})
    result = _select(_document(_unit(text, kind='html_paragraph')))
    assert assessment.passage.assessment_complete and not assessment.passage.relevant
    assert not result.evidence_spans and result.coverage_complete
    assert result.reading_context['source_processing_complete']
    assert not result.reading_context['selection_trace']['withheld']['count']
    assert not any(row.get('phase') == 'source_readability' for row in result.selection_diagnostics)


@pytest.mark.parametrize('text', ('农户购买新鲜的蔬菜。', '农户购买蔬菜的村庄。'))
def test_language_ambiguity_is_readable_unresolved_not_a_capability_failure(text):
    assessment = prepare_reading_business_assessment(text, {'relations': []})
    result = _select(_document(_unit(text, kind='html_paragraph')))
    assert assessment.passage.assessment_complete and assessment.passage.relevant
    assert not assessment.fact.eligible
    assert result.status == 'selected' and result.coverage_complete
    assert result.reading_context['source_processing_complete']
    assert {span.raw_text for span in result.evidence_spans} == {text}
    assert not result.reading_context['selection_trace']['withheld']['count']
    views = [view for group in result.reading_context['groups'] for view in group['citation_views']]
    assert views and all(view['reading_support_use'] == 'unresolved' and
                         view['reading_support_reason'] == 'source_grammar_ambiguous' for view in views)


def test_capability_failure_is_cached_per_session_without_stopping_other_work():
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    with patch.object(grammar, '_english_tagger', side_effect=LookupError('missing model')) as tagger:
        session, budget = session_for([MIXED])
        uid = unit_id(0)
        fact = session.fact(uid)
        passage = session.source_passage(uid)
        used, calls = budget.used, tagger.call_count
        assert not passage.assessment_complete and session.financial_only(uid) is None
        assert session.complete and not budget.exhausted  # a per-scope deferral, not a work stop
        assert session.fact(uid) is fact and session.source_passage(uid) is passage
        assert budget.used == used and tagger.call_count == calls


def test_a_new_selection_can_recover_when_the_resource_is_available_again():
    parsed = _document(_unit(MIXED, kind='html_paragraph'))
    with patch.object(grammar, '_english_tagger', side_effect=LookupError('missing model')):
        deferred = _select(parsed)
    recovered = _select(parsed)
    assert deferred.status == 'needs_review'
    assert deferred.reading_dependencies['status'] == 'partial'
    assert recovered.status == 'selected' and recovered.reading_context['source_processing_complete']
    assert {span.raw_text for span in recovered.evidence_spans} == {MIXED}
    assert parsed.units[0].raw_text == MIXED
