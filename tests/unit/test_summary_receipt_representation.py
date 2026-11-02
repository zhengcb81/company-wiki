"""The saved execution reader must accept the producer's full source report."""
from copy import deepcopy

import pytest

from company_wiki.automation.models import HandlerOutcome, canonical_json
from company_wiki.automation.narrative_contracts import NarrativeContractError, NarrativeSelectResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.narrative_summary_execution import parse_summary_job_result
from unit.test_narrative_extractive_runtime import selected, VERSION
from unit.test_narrative_summarize_handler import _context


def large_execution():
    source = selected(1)
    wire = source.to_dict()
    wire['reading_context']['groups'] = [
        {'group_id': f'native-{index}', 'kind': 'business_progress', 'section_role': 'business',
         'evidence_ids': [source.evidence_spans[0].span_id]} for index in range(400)]
    source = NarrativeSelectResult.from_dict(wire)

    class RankModel:
        def generate(self, request):
            return NarrativeModelResponse('offline', 'configured', request.prompt_version, b'{"decisions":[]}')

    result = NarrativeSummarizeHandler(model=RankModel(),
        reading_model_projection=lambda _subject: VERSION)(_context(source))
    assert result.outcome is HandlerOutcome.SUCCEEDED
    payload = result.to_dict()['result']
    assert len(canonical_json(payload['execution']).encode()) > 32 * 1024
    return source, payload


def test_actual_large_execution_report_survives_its_public_persisted_result_reader():
    source, result = large_execution()
    parsed = parse_summary_job_result(result, selected=source)
    assert parsed.draft.claims
    assert len(result['execution']['tasks']) == 400


def test_large_execution_does_not_relax_source_task_binding_validation():
    source, result = large_execution()
    invalid = deepcopy(result)
    invalid['execution']['plan_sha256'] = '0' * 64
    with pytest.raises(NarrativeContractError, match='plan|binding'):
        parse_summary_job_result(invalid, selected=source)
