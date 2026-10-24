"""A plan and its intrinsic limitation must survive the actual request seam."""
import json

import pytest

from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model_extractive import compile_extractive_plan
from company_wiki.automation.narrative_model_runtime import build_model_request
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.document_understanding.source_cards import source_cards
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from unit.test_narrative_select_handler import FakeReader, _context, _payload
from unit.document_understanding_root.test_native_anonymous_turns import MIME, docx

PLAN = 'Speaker 2 00:20 We plan to launch new products.'
LIMIT = 'But this launch plan has not been finalized and may change.'


def card_texts(selected):
    plan = build_summary_task_plan(selected.evidence_spans,
                                   reading_context=selected.reading_context, max_claims=40)
    return [card.text or '' for card in source_cards(
        plan, {span.span_id: span for span in selected.evidence_spans})]


def select(lines, mime):
    data = docx(lines) if mime == MIME else ('\n'.join([
        'Full Conference Call Transcript', *lines, 'End of transcript'])).encode()
    payload = _payload(data, title='Earnings conference call',
                       document_kind='investor_relations' if mime == MIME else 'earnings_call_transcript',
                       language='en', mime_type=mime)
    result = NarrativeSelectHandler(reader=FakeReader(payload, data), selector_version='0.9.0')(
        _context(payload, lambda: None))
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    parsed = NarrativeSelectResult.from_dict(result.result)
    return NarrativeSelectResult.from_dict(json.loads(json.dumps(parsed.to_dict())))


@pytest.mark.parametrize('mime', [MIME, 'text/plain'])
def test_same_turn_plan_limitation_is_model_material_and_card_support(mime):
    selected = select(['Speaker 1 00:00 When will production begin?', PLAN, LIMIT,
                       'Speaker 1 01:00 Is this final?'], mime)
    request = build_model_request(selected, reading_projection_version='reading-model-input/5')
    assert PLAN in request.data_json
    assert LIMIT in request.data_json
    assert any(PLAN in text and LIMIT in text for text in card_texts(selected))
    assert all(claim['modality'] != 'actual'
               for claim in compile_extractive_plan(selected).draft['claims'])


@pytest.mark.parametrize('mime', [MIME, 'text/plain'])
def test_other_speaker_limitation_does_not_become_plan_support(mime):
    selected = select(['Speaker 1 00:00 When will production begin?', PLAN,
                       'Speaker 1 00:40 ' + LIMIT], mime)
    assert not any(PLAN in text and LIMIT in text for text in card_texts(selected))


@pytest.mark.parametrize('mime', [MIME, 'text/plain'])
def test_chinese_plan_retains_uncertainty_without_promoting_unknown_speaker(mime):
    plan = '说话人2 00:20 公司计划更新产品。'
    limitation = '但具体计划尚未确定，可能会发生变化。'
    selected = select(['说话人1 00:00 请问产品何时发布？', plan, limitation], mime)
    assert any(plan in text and limitation in text for text in card_texts(selected))
    assert all(span.structured_value['source_role'] == 'unknown'
               for span in selected.evidence_spans)


@pytest.mark.parametrize('limitation', [
    'But another company has not finalized its plan.',
    'But this employee training plan has not been finalized.',
    'This year revenue increased and customer demand may change.',
])
def test_unrelated_caveat_cannot_become_plan_factual_support(limitation):
    selected = select(['Speaker 1 00:00 When?', PLAN, limitation], MIME)
    assert not any(PLAN in text and limitation in text for text in card_texts(selected))
