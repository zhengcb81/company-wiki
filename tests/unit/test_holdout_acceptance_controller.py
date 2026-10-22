"""Fast contract checks; subprocess lifecycle E2E lives in integration/."""
from dataclasses import replace
import hashlib
import json

import pytest

from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.automation.narrative_model_runtime import build_model_request
from tools.document_understanding_benchmark.holdout_acceptance import ControllerError, _validate
from tools.document_understanding_benchmark.holdout_acceptance_contracts import request_preflight
from unit.test_narrative_extractive_runtime import selected


@pytest.mark.parametrize('output_limit', [8192, 31])
@pytest.mark.parametrize('output_field', ['max_tokens', 'max_completion_tokens'])
def test_preflight_counts_actual_utf8_body_and_configured_output(output_limit, output_field):
    request = build_model_request(selected(), reading_projection_version='reading-model-input/5')
    request = replace(request, instruction=request.instruction + ' 中文边界')
    model = NarrativeHTTPModel(model_id='configured-unit', endpoint='https://configured.invalid/v1/chat/completions',
        api_key_env='UNREAD_UNIT_KEY', max_output_tokens=output_limit, output_token_field=output_field)
    body, observed = request_preflight(model, request)
    assert body == model.request_bytes(request)
    assert len(body) > len(body.decode('utf-8'))
    assert observed['http_body_sha256'] == hashlib.sha256(body).hexdigest()
    assert observed['conservative_token_bound'] == len(body) + 128 + output_limit
    assert json.loads(body)[output_field] == output_limit
    assert observed['output_token_field'] == output_field
    assert observed['model_request_schema'] == 'narrative-model-request/6'


def test_invalid_spec_is_rejected_before_creating_any_store(tmp_path):
    with pytest.raises(ControllerError, match='HOLDOUT_INVALID_SPEC'):
        _validate({'receipt_dir': str(tmp_path/'absent')})
    assert not list(tmp_path.iterdir())
