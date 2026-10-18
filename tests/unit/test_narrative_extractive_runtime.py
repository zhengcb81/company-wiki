"""Facts remain complete source extracts; model decisions only order cards."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_runtime import build_model_request, decode_model_draft
from support.narrative_model_request_fixture import selection
from unit.test_narrative_reading_transport import reading_context


VERSION = 'reading-model-input/5'


def selected(count=3, **kwargs):
    original = selection(count, **kwargs)
    wire = original.to_dict()
    context = reading_context(original)
    context['groups'] = []  # Genuine independent singleton source scopes.
    wire['reading_context'] = context
    return NarrativeSelectResult.from_dict(wire)


def reply(source, decisions):
    request = build_model_request(source, reading_projection_version=VERSION)
    response = NarrativeModelResponse('offline', 'configured', request.prompt_version,
        canonical_json({'decisions': decisions}).encode())
    return decode_model_draft(response, selected=source, reading_projection_version=VERSION)


def test_sparse_model_cannot_drop_sixty_four_admitted_source_tasks():
    source = selected(64)
    before = deepcopy(source.to_dict())
    draft = reply(source, [{'task': 't64', 'priority': 'high', 'disposition': 'consider'}])
    assert len(draft['claims']) == 64
    assert draft['claims'][0]['evidence_ids'] == [source.evidence_spans[-1].span_id]
    assert {row['text'] for row in draft['claims']} == {span.raw_text for span in source.evidence_spans}
    assert draft['status'] == 'needs_review'  # Missing decisions are not complete processing.
    assert source.to_dict() == before


@pytest.mark.parametrize('decision', [
    {'task': 't1', 'priority': 'high', 'disposition': 'consider', 'text': '伪造产品已实现100亿美元销售'},
    {'task': 't999', 'priority': 'high', 'disposition': 'consider'},
    {'task': 't1', 'priority': 'high', 'disposition': 'delete'},
])
def test_invalid_rank_falls_back_to_source_order_never_importing_model_facts(decision):
    source = selected()
    draft = reply(source, [decision])
    assert [row['text'] for row in draft['claims']] == [span.raw_text for span in source.evidence_spans]
    assert draft['status'] == 'needs_review'


def test_redundancy_opinion_cannot_delete_different_original_events():
    source = selected()
    draft = reply(source, [{'task': 't1', 'priority': 'low', 'disposition': 'redundant'}])
    assert len(draft['claims']) == 3
    assert all(row['modality'] == 'uncertain' for row in draft['claims'])


def test_complete_original_negation_and_long_passage_cannot_be_substring_rewritten():
    source = selected(1, text_suffix='该产品尚未量产，2028年拟验证；客户反馈不是订单。' * 25)
    draft = reply(source, [{'task': 't1', 'priority': 'high', 'disposition': 'consider'}])
    assert draft['claims'][0]['text'] == source.evidence_spans[0].raw_text
    assert len(draft['claims'][0]['text']) > 280
    assert draft['claims'][0]['modality'] == 'uncertain'


def test_unknown_source_role_is_preserved_not_silently_dropped():
    source = selected(role='unknown')
    draft = reply(source, [])
    assert len(draft['claims']) == 3
    assert all(row['claim_type'] == 'uncertain' and row['needs_review'] for row in draft['claims'])


def test_questions_remain_questions_without_invented_management_answers():
    source = selected(role='investor_question')
    draft = reply(source, [])
    assert all(row['claim_type'] == 'analyst_question' and row['modality'] == 'question'
               for row in draft['claims'])


def test_request_and_execution_report_account_for_every_task_without_free_prose_schema():
    from company_wiki.automation.narrative_model_extractive import decode_extractive_result
    source = selected(64)
    request = build_model_request(source, reading_projection_version=VERSION)
    data = json.loads(request.data_json)
    assert data['schema_version'] == 'narrative-model-request/6'
    assert data['output_plan']['available_task_count'] == 64
    assert 'text' not in data['response_schema']['properties']['decisions']['items']['properties']
    response = NarrativeModelResponse('offline', 'configured', request.prompt_version, b'{"decisions":[]}')
    decoded = decode_extractive_result(response, selected=source)
    assert len(decoded.execution['tasks']) == 64
    assert {row['source_disposition'] for row in decoded.execution['tasks']} == {'admitted'}
    assert {row['model_disposition'] for row in decoded.execution['tasks']} == {'unprocessed'}
    assert decoded.execution['model_coverage_complete'] is False
    assert len(canonical_json(decoded.execution).encode()) <= 32 * 1024


def test_real_frozen_inventory_uses_source_cards_and_retains_all_budget_admitted_tasks():
    fixture = Path(__file__).parents[1] / 'fixtures/narrative_claim_grounding/cn_h1_unit3.json.gz'
    source = NarrativeSelectResult.from_dict(json.loads(gzip.decompress(fixture.read_bytes()))['selected'])
    from company_wiki.automation.narrative_model_extractive import decode_extractive_result
    request = build_model_request(source, reading_projection_version=VERSION)
    response = NarrativeModelResponse('offline', 'configured', request.prompt_version, b'{"decisions":[]}')
    decoded = decode_extractive_result(response, selected=source)
    admitted = [row for row in decoded.execution['tasks'] if row['source_disposition'] == 'admitted']
    assert len(decoded.execution['tasks']) == 64
    assert len(admitted) > 20
    assert {row['claim_id'] for row in admitted} == {row['claim_id'] for row in decoded.draft['claims']}
    assert all(row['modality'] != 'actual' for row in decoded.draft['claims'])


def test_capacity_defers_complete_cards_instead_of_cutting_them():
    from company_wiki.automation.narrative_model_extractive import compile_extractive_plan
    source = selected(3, text_suffix='完整且不可截断的不同业务描述。' * 50)
    plan = compile_extractive_plan(source, max_draft_bytes=4000)
    assert any(row['source_disposition'] == 'deferred' for row in plan.execution['tasks'])
    assert len(canonical_json(plan.draft).encode()) <= 4000
    assert all(row['text'] in {span.raw_text for span in source.evidence_spans} for row in plan.draft['claims'])


def test_v4_still_rejects_twenty_two_clauses_instead_of_reinterpreting_paid_failure():
    source = selected(1)
    request = build_model_request(source, reading_projection_version='reading-model-input/4')
    response = NarrativeModelResponse('offline', 'configured', request.prompt_version,
        canonical_json({'drafts_by_task': {'t1': [
            {'text': '旧协议条款', 'basis_parts': ['p1'], 'modality': 'uncertain'}] * 22}}).encode())
    with pytest.raises(ValueError, match='twenty'):
        decode_model_draft(response, selected=source, reading_projection_version='reading-model-input/4')


def test_native_support_and_context_are_preserved_without_promoting_question_to_answer():
    source = selected()
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    wire['reading_context']['schema_version'] = 'du-production-reading/2'
    wire['reading_context']['groups'] = [{
        'group_id': 'qa-original', 'kind': 'business_progress', 'section_role': 'business',
        'evidence_ids': ids, 'citation_views': [
            {'support_evidence_ids': ids[1:], 'context_evidence_ids': ids[:1]}]}]
    source = NarrativeSelectResult.from_dict(wire)
    draft = reply(source, [])
    assert len(draft['claims']) == 1
    claim = draft['claims'][0]
    assert claim['evidence_ids'] == ids[1:]
    assert claim['context_evidence_ids'] == ids[:1]
    assert claim['text'] == '\n'.join(span.raw_text for span in source.evidence_spans[1:])


def test_duplicate_native_scope_is_accounted_without_repeating_the_card():
    from company_wiki.automation.narrative_model_extractive import decode_extractive_result
    source = selected()
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    wire['reading_context']['groups'] = [
        {'group_id': group, 'kind': 'business_progress', 'section_role': 'business',
         'evidence_ids': ids} for group in ('native-a', 'native-b')]
    source = NarrativeSelectResult.from_dict(wire)
    request = build_model_request(source, reading_projection_version=VERSION)
    response = NarrativeModelResponse('offline', 'configured', request.prompt_version, b'{"decisions":[]}')
    decoded = decode_extractive_result(response, selected=source)
    assert len(decoded.draft['claims']) == 1
    assert [row['source_disposition'] for row in decoded.execution['tasks']] == ['admitted', 'duplicate']
    assert decoded.execution['tasks'][1]['claim_id'] == decoded.draft['claims'][0]['claim_id']


def test_execution_capacity_includes_all_future_rank_fields_before_any_paid_request():
    from company_wiki.automation.narrative_model_extractive import compile_extractive_plan
    source = selected(1)
    wire = source.to_dict()
    ids = [source.evidence_spans[0].span_id]
    wire['reading_context']['groups'] = [
        {'group_id': 'native-' + str(index), 'kind': 'business_progress',
         'section_role': 'business', 'evidence_ids': ids} for index in range(137)]
    source = NarrativeSelectResult.from_dict(wire)
    with pytest.raises(ValueError, match='execution report exceeds'):
        compile_extractive_plan(source)


def test_oversized_repeated_scopes_are_lazy_and_never_render_rejected_text(monkeypatch):
    import inspect
    from company_wiki.document_understanding.source_cards import SourceCard, source_cards
    from company_wiki.automation.narrative_model_extractive import compile_extractive_plan
    assert inspect.isgeneratorfunction(source_cards)
    source = selected(2, text_suffix='A' * 180000)
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    wire['reading_context']['groups'] = [
        {'group_id': 'native-' + str(index), 'kind': 'business_progress',
         'section_role': 'business', 'evidence_ids': ids} for index in range(400)]
    source = NarrativeSelectResult.from_dict(wire)
    def forbidden_render(_self):
        raise AssertionError('oversized deferred source text must never be joined')
    monkeypatch.setattr(SourceCard, 'text', property(forbidden_render))
    with pytest.raises(ValueError, match='execution report exceeds'):
        compile_extractive_plan(source)


def test_actual_summary_handler_records_bounded_execution_and_keeps_public_summary_exact():
    from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
    from company_wiki.automation.narrative_summary_execution import parse_summary_job_result
    from company_wiki.automation.models import HandlerOutcome
    from unit.test_narrative_summarize_handler import _context
    source = selected(64)
    calls = []
    class RankModel:
        def generate(self, request):
            calls.append(request)
            return NarrativeModelResponse('offline', 'configured', request.prompt_version,
                                          b'{"decisions":[]}')
    result = NarrativeSummarizeHandler(model=RankModel(),
        reading_model_projection=lambda _subject: VERSION)(_context(source))
    assert result.outcome is HandlerOutcome.SUCCEEDED
    assert len(calls) == 1
    assert result.result['schema_version'] == 'narrative-summary-execution/1'
    assert len(result.result['execution']['tasks']) == 64
    inner = parse_summary_job_result(result.result, selected=source)
    assert len(inner.draft.claims) == 64
    assert 'execution' not in inner.to_dict()
    assert inner.encoded_size <= 64 * 1024


def test_actual_handler_returns_typed_preflight_failure_for_oversized_plan_without_calling_model():
    from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
    from company_wiki.automation.models import HandlerOutcome
    from unit.test_narrative_summarize_handler import _context
    source = selected(1)
    wire = source.to_dict()
    wire['reading_context']['groups'] = [
        {'group_id': 'native-' + str(index), 'kind': 'business_progress',
         'section_role': 'business', 'evidence_ids': [source.evidence_spans[0].span_id]}
        for index in range(137)]
    source = NarrativeSelectResult.from_dict(wire)
    class ForbiddenModel:
        def generate(self, _request):
            pytest.fail('no model request is allowed for an unrepresentable source plan')
    result = NarrativeSummarizeHandler(model=ForbiddenModel(),
        reading_model_projection=lambda _subject: VERSION)(_context(source))
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == 'SUMMARY_PLAN_INVALID'
    assert result.metrics.tokens == 0 and result.artifacts == result.effects == ()
