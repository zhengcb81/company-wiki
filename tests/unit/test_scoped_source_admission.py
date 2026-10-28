"""Summary material consumes source capability and priority without inventing facts."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

from company_wiki.automation import narrative_model_scoped as scoped
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_runtime import build_model_request, decode_model_draft
from tools.document_understanding_benchmark.phase_c_observer import gold_observation, gold_admission_missing
from unit.test_narrative_extractive_runtime import selected


def source_with_metadata(*rows):
    source = selected(len(rows))
    spans = []
    for span, metadata in zip(source.evidence_spans, rows, strict=True):
        metadata = dict(metadata)
        flags = tuple(metadata.pop('quality_flags', ()))
        spans.append(type(span).create(source_id=span.source_id, coordinates=span.coordinates,
            raw_text=span.raw_text, structured_value={**span.structured_value, **metadata,
                'text_sha256': hashlib.sha256((span.raw_text or '').encode()).hexdigest()},
            parser_name=span.parser_name, parser_version=span.parser_version,
            parse_status=span.parse_status, quality_flags=flags))
    return replace(source, evidence_spans=tuple(spans))


def envelope(source):
    return json.loads(build_model_request(source, reading_projection_version='reading-model-input/4').data_json)


def decode(source, rows):
    request = build_model_request(source, reading_projection_version='reading-model-input/4')
    response = NarrativeModelResponse('offline', 'configured', request.prompt_version,
                                     json.dumps({'drafts_by_task': rows}).encode())
    return decode_model_draft(response, selected=source, reading_projection_version='reading-model-input/4')


def clause(source, index):
    return {'text': source.evidence_spans[index].raw_text, 'basis_parts': ['p1'], 'modality': 'actual'}


@pytest.mark.parametrize('flag', ['table_structure_ambiguous'])
def test_unresolved_source_table_is_not_sent_as_a_rewritable_fact(flag):
    source = source_with_metadata({'quality_flags': [flag]}, {})
    before = deepcopy(source.to_dict())
    wire = envelope(source)
    assert [row['key'] for row in wire['material']['tasks']] == ['t2']
    assert wire['material']['available_task_count'] == 1
    assert source.to_dict() == before
    view = scoped.compile_scoped_model_view(source, max_claims=20)
    assert len(view.plan.tasks) == 2, 'original source plan must remain inspectable'
    assert view.to_binding()['source_admission']['t1']['reason'] == 'source_table_unresolved'


def test_known_incomplete_support_cannot_be_restored_by_uncertain_model_prose():
    source = source_with_metadata({'quality_flags': ['table_structure_ambiguous']}, {})
    bad = clause(source, 0)
    bad['modality'] = 'uncertain'
    draft = decode(source, {'t1': [bad], 't2': [clause(source, 1)]})
    assert len(draft['claims']) == 1
    assert draft['claims'][0]['evidence_ids'] == [source.evidence_spans[1].span_id]
    assert draft['status'] == 'needs_review'


def test_source_reading_decisions_reach_actual_model_tasks():
    source = source_with_metadata({'reading_priority': 2, 'reading_value_band': 'meaningful_fact',
        'reading_score': 9, 'reading_fact_purpose': 'operating_metric'})
    row = envelope(source)['material']['tasks'][0]
    assert row['reading'] == {'priority': 2, 'value_band': 'meaningful_fact',
                              'score': 9, 'purposes': ['operating_metric']}


def test_context_cannot_donate_reading_value_or_table_failure_to_support():
    source = source_with_metadata({'reading_priority': 0, 'reading_value_band': 'meaningful_fact',
        'reading_score': 99, 'reading_fact_purpose': 'operating_metric',
        'quality_flags': ['table_structure_ambiguous']},
        {'reading_priority': 4, 'reading_value_band': 'description', 'reading_score': 2,
         'reading_fact_purpose': 'unknown'})
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    digest = hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()
    wire['reading_context'].update(schema_version='du-production-reading/2', groups=[{
        'group_id': 'urn:company-wiki:reading-group:sha256:' + digest,
        'kind': 'business_progress', 'section_role': 'business', 'evidence_ids': ids,
        'citation_views': [{'support_evidence_ids': ids[1:], 'context_evidence_ids': ids[:1]}]}])
    source = NarrativeSelectResult.from_dict(wire)
    row = envelope(source)['material']['tasks'][0]
    assert row['reading']['priority'] == 4
    assert row['reading']['value_band'] == 'description'
    assert row['reading']['purposes'] == ['unknown']


def test_exact_source_scope_duplicates_do_not_take_multiple_summary_slots():
    source = selected(2)
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    wire['reading_context']['groups'] = [
        {'group_id': group, 'kind': 'business_progress', 'section_role': 'business',
         'evidence_ids': ids} for group in ('native-a', 'native-b')]
    source = NarrativeSelectResult.from_dict(wire)
    view = scoped.compile_scoped_model_view(source, max_claims=20)
    assert len(view.plan.tasks) == 2
    assert [row['key'] for row in view.to_model_dict()['tasks']] == ['t1']
    assert view.to_binding()['source_admission']['t2']['representative'] == 't1'


def test_different_source_increments_and_periods_are_not_scope_duplicates():
    source = selected(3)
    assert [row['key'] for row in envelope(source)['material']['tasks']] == ['t1', 't2', 't3']


def test_summary_target_is_not_a_requirement_to_fill_with_weak_material():
    request = build_model_request(selected(60), reading_projection_version='reading-model-input/4').with_output_budget(8192)
    wire = json.loads(request.data_json)
    assert wire['output_plan']['target_claim_count'] == 24
    assert wire['output_plan']['max_claims'] == 40
    assert wire['output_plan']['max_claims_per_task'] == 2
    assert 'exactly output_plan.target_claim_count' not in request.instruction
    assert 'stop once the target is reached' not in request.instruction
    assert 'up to output_plan.target_claim_count' in request.instruction
    assert len(decode(selected(3), {'t1': [clause(selected(3), 0)]})['claims']) == 1


def test_decoder_enforces_the_same_per_task_cap_as_the_actual_request():
    from company_wiki.automation.narrative_contracts import NarrativeContractError

    source = selected(2)
    cap = envelope(source)['output_plan']['max_claims_per_task']
    assert len(decode(source, {'t1': [clause(source, 0)] * cap})['claims']) == cap
    with pytest.raises(NarrativeContractError, match='per-task cap'):
        decode(source, {'t1': [clause(source, 0)] * (cap + 1), 't2': [clause(source, 1)]})


def test_filtered_full_request_is_not_mistaken_for_a_coverage_repair():
    source = source_with_metadata({'quality_flags': ['table_structure_ambiguous']}, {})
    gold = {'facts': [{'id': 'retained-business', 'target_kind': 'required_business',
        'any_support_sets': [[{'page': source.evidence_spans[1].coordinates.page_number,
                              'exact_quote': source.evidence_spans[1].raw_text}]]}]}
    observed = gold_observation(gold, source, envelope(source))
    assert observed['sent_tasks']['request_scope'] == 'full_request'
    assert observed['sent_tasks']['sent_task_keys'] == ['t2']
    assert gold_admission_missing(observed, attempt_no=1) == []


def test_deep_business_task_keeps_source_priority_and_complete_original_support():
    source = source_with_metadata(*([{}] * 59), {'reading_priority': 1,
        'reading_value_band': 'meaningful_fact', 'reading_score': 12,
        'reading_fact_purpose': 'operating_metric'})
    before = deepcopy(source.to_dict())
    wire = envelope(source)
    task = next(row for row in wire['material']['tasks'] if row['key'] == 't60')
    assert task['reading']['priority'] == 1
    assert task['parts'][0]['text'] == source.evidence_spans[-1].raw_text
    assert source.to_dict() == before


def test_only_declared_reading_annotations_are_excluded_from_original_field_identity():
    from company_wiki.automation.narrative_replay import _projection_span_identity
    from company_wiki.source_contract.selection_annotations import reading_annotations

    base = source_with_metadata({'unit_kind': 'official_json_field', 'field_value': 47}).evidence_spans[0]
    values = reading_annotations({'priority': 1, 'value_band': 'meaningful_fact',
                                  'fact_purpose': 'operating_metric'}, 9)

    def annotated(extra):
        return type(base).create(source_id=base.source_id, coordinates=base.coordinates,
            raw_text=base.raw_text, structured_value={**base.structured_value, **extra},
            parser_name=base.parser_name, parser_version=base.parser_version,
            parse_status=base.parse_status, quality_flags=base.quality_flags)

    assert _projection_span_identity(annotated(values)) == _projection_span_identity(base)
    assert _projection_span_identity(annotated({'reading_original_amount': 999})) != _projection_span_identity(base)
