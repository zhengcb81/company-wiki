"""Source-owned whole-card priority, independent of company words and model rank."""
from copy import deepcopy
from pathlib import Path

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation import narrative_model_extractive as owner
from company_wiki.source_contract import EvidenceSpan
from unit.test_narrative_extractive_runtime import selected


def policy(priority=10, band='description', score=0):
    return {'reading_priority': priority, 'reading_value_band': band, 'reading_score': score}


def source(texts, metadata):
    original = selected(len(texts))
    wire = original.to_dict()
    wire['evidence_spans'] = [EvidenceSpan.create(
        source_id=span.source_id, coordinates=span.coordinates, raw_text=text,
        structured_value={**span.structured_value, **observed},
        parser_name=span.parser_name, parser_version=span.parser_version,
        parse_status=span.parse_status, quality_flags=span.quality_flags,
    ).to_dict() for span, text, observed in zip(original.evidence_spans, texts, metadata)]
    return NarrativeSelectResult.from_dict(wire)


def one_card_cap(value):
    full = owner.compile_extractive_plan(value).draft
    return max(len(canonical_json({**full, 'claims': [claim]}).encode())
               for claim in full['claims'])


def allocated(value, cap=None):
    plan = owner.compile_extractive_plan(value, max_draft_bytes=cap or one_card_cap(value))
    return plan, [row['claim_id'] for row in plan.execution['tasks']
                  if row['source_disposition'] == 'admitted']


@pytest.mark.parametrize('texts', [
    ['Ordinary complete administrative description.' * 20,
     'Remaining performance obligations were375billion;40%is expected in12months.' * 12],
    ['一般業務描述。' * 90, '新產品已完成客戶驗證並計劃擴產。' * 60],
])
def test_late_important_source_card_survives_same_bounded_byte_capacity(texts):
    value = source(texts, [policy(90), policy(5, 'meaningful_fact', 20)])
    before = deepcopy(value.to_dict())
    plan, ids = allocated(value)
    assert ids == ['t2-source']
    assert plan.execution['tasks'][0]['reason'] == 'draft_byte_budget'
    assert plan.draft['claims'][0]['text'] == texts[1]
    assert plan.draft['claims'][0]['evidence_ids'] == [value.evidence_spans[1].span_id]
    assert value.to_dict() == before


@pytest.mark.parametrize('fields', [
    [policy(1, 'description', 1), policy(1, 'meaningful_fact', 0)],
    [policy(1, 'meaningful_fact', 1), policy(1, 'meaningful_fact', 2)],
    [policy(2, 'meaningful_fact', 999), policy(1, 'description', 0)],
])
def test_priority_then_value_band_then_score_are_source_tuple_order(fields):
    value = source(['A complete event.' * 50, 'B complete event.' * 50], fields)
    assert allocated(value)[1] == ['t2-source']


def test_source_text_company_words_and_task_position_do_not_create_priority():
    texts = ['Routine complete statement.' * 50, 'An independently important event.' * 50]
    first = source(texts, [policy(80), policy(1, 'meaningful_fact', 9)])
    reverse = source(texts[::-1], [policy(1, 'meaningful_fact', 9), policy(80)])
    assert allocated(first)[0].draft['claims'][0]['text'] == texts[1]
    assert allocated(reverse)[0].draft['claims'][0]['text'] == texts[1]


@pytest.mark.parametrize('bad', [
    {}, {'reading_priority': 0}, policy(True), policy(0, score=True),
    policy(0, score=-1), policy(0, band='model_high'), policy('0'), policy(0, score=1.5),
])
def test_unknown_or_invalid_policy_keeps_original_slot(bad):
    value = source(['Original first.' * 50, 'Unknown middle.' * 50, 'Important tail.' * 50],
                   [policy(90), bad, policy(1, 'meaningful_fact', 99)])
    # Two cards fit: known slots swap, unknown remains at index1 before low tail.
    full = owner.compile_extractive_plan(value).draft
    cap = max(len(canonical_json({**full, 'claims': [full['claims'][0], full['claims'][1]]}).encode()),
              len(canonical_json({**full, 'claims': [full['claims'][1], full['claims'][2]]}).encode()))
    plan, ids = allocated(value, cap)
    assert ids == ['t2-source', 't3-source']
    assert [row['task'] for row in plan.execution['tasks']] == ['t1', 't2', 't3']
    assert [claim['claim_id'] for claim in plan.draft['claims']] == ids


def test_all_legacy_metadata_absent_retains_native_first_fit():
    value = source(['A complete event.' * 50, 'B complete event.' * 50], [{}, {}])
    assert allocated(value)[1] == ['t1-source']


def test_equal_source_tuples_use_native_tie_and_complete_audit_order():
    value = source(['A complete event.' * 50, 'B complete event.' * 50], [policy(), policy()])
    plan, ids = allocated(value)
    assert ids == ['t1-source']
    assert [row['task'] for row in plan.execution['tasks']] == ['t1', 't2']


def grouped(value, groups):
    wire = value.to_dict()
    wire['reading_context']['schema_version'] = 'du-production-reading/2'
    wire['reading_context']['groups'] = groups
    return NarrativeSelectResult.from_dict(wire)


def test_context_cannot_lend_high_priority_but_best_real_support_can():
    value = source(['Low actual support.' * 40, 'High context only.' * 40,
                    'Important actual support.' * 40],
                   [policy(90), policy(0, 'meaningful_fact', 999), policy(5)])
    ids = [span.span_id for span in value.evidence_spans]
    value = grouped(value, [
        {'group_id': 'with-context', 'kind': 'background', 'section_role': 'business',
         'evidence_ids': ids[:2], 'citation_views': [
             {'support_evidence_ids': ids[:1], 'context_evidence_ids': ids[1:2]}]},
        {'group_id': 'real-support', 'kind': 'background', 'section_role': 'business',
         'evidence_ids': ids[2:], 'citation_views': [
             {'support_evidence_ids': ids[2:], 'context_evidence_ids': []}]},
    ])
    plan, chosen = allocated(value)
    assert chosen == ['t2-source']
    assert plan.draft['claims'][0]['evidence_ids'] == ids[2:]


def test_best_complete_support_tuple_controls_indivisible_whole_group():
    value = source(['Native ordinary support.' * 40, 'Part one.' * 20, 'Part two.' * 20],
                   [policy(20), policy(90), policy(5, 'meaningful_fact', 7)])
    ids = [span.span_id for span in value.evidence_spans]
    value = grouped(value, [
        {'group_id': 'ordinary', 'kind': 'background', 'section_role': 'business',
         'evidence_ids': ids[:1], 'citation_views': [{'support_evidence_ids': ids[:1], 'context_evidence_ids': []}]},
        {'group_id': 'multi-support', 'kind': 'background', 'section_role': 'business',
         'evidence_ids': ids[1:], 'citation_views': [{'support_evidence_ids': ids[1:], 'context_evidence_ids': []}]},
    ])
    plan, chosen = allocated(value)
    assert chosen == ['t2-source']
    assert plan.draft['claims'][0]['text'] == '\n'.join(span.raw_text for span in value.evidence_spans[1:])
    assert plan.draft['claims'][0]['evidence_ids'] == ids[1:]


def test_oversized_high_priority_card_is_deferred_without_materializing_text(monkeypatch):
    from company_wiki.document_understanding.source_cards import SourceCard
    value = source(['Huge exact support.' * 500, 'Small exact support.'],
                   [policy(1), policy(90)])
    original = SourceCard.text.fget
    rendered = []
    def text(card):
        assert card.task.key != 't1', 'oversized rejected original must stay lazy'
        rendered.append(card.task.key)
        return original(card)
    monkeypatch.setattr(SourceCard, 'text', property(text))
    plan, chosen = allocated(value, 1000)
    assert chosen == ['t2-source'] and rendered == ['t2']
    assert len(canonical_json(plan.draft).encode()) <= 1000


def test_allocator_identity_and_actual_module_path_are_bound_to_worktree():
    expected = Path(__file__).resolve().parents[3] / 'src/company_wiki/automation/narrative_model_extractive.py'
    assert Path(owner.__file__).resolve() == expected
    assert owner.SOURCE_CARD_ALLOCATION_VERSION == 'source-card-allocation/1'


def test_default_fifty_six_kib_capacity_keeps_late_operating_fact_and_all_task_rows():
    texts = [('Ordinary source description.' * 200) + str(i) for i in range(12)]
    texts.append('Complete remaining obligations and conversion timing.' * 140)
    value = source(texts, [policy(80)] * 12 + [policy(2, 'meaningful_fact', 500)])
    plan = owner.compile_extractive_plan(value)
    assert len(canonical_json(plan.draft).encode()) <= 56 * 1024
    assert len(plan.execution['tasks']) == 13
    assert plan.execution['tasks'][-1]['source_disposition'] == 'admitted'
    assert any(row['source_disposition'] == 'deferred' for row in plan.execution['tasks'])
    assert any(claim['text'] == texts[-1] for claim in plan.draft['claims'])
    assert [row['task'] for row in plan.execution['tasks']] == ['t' + str(i) for i in range(1, 14)]


def test_allocator_semantics_participate_in_actual_boundary_identity(monkeypatch):
    from types import SimpleNamespace
    boundary = SimpleNamespace(reading_projection_version='reading-model-input/5',
        prompt_version=owner.EXTRACTIVE_PROMPT_VERSION, request_schema=owner.EXTRACTIVE_REQUEST_SCHEMA,
        decoder_version='test-frozen-decoder')
    before = owner.extractive_boundary_identity(boundary)
    monkeypatch.setattr(owner, 'SOURCE_CARD_ALLOCATION_VERSION', 'source-card-allocation/test-next')
    after = owner.extractive_boundary_identity(boundary)
    assert before['source_card_allocation_version'] == 'source-card-allocation/1'
    assert after['source_card_allocation_version'] == 'source-card-allocation/test-next'
    assert before != after
