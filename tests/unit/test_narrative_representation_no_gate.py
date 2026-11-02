"""Source material remains valid when only its JSON representation grows."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation.narrative_contracts import NarrativeSelectResult, NarrativeContractError
from company_wiki.automation.models import canonical_json
from unit.test_narrative_reading_transport import reading_context
from support.narrative_model_request_fixture import selection


def wire():
    selected = selection(3)
    result = selected.to_dict()
    result['reading_context'] = reading_context(selected)
    return result


@pytest.mark.parametrize('variant', ['bytes', 'array', 'policies', 'depth'])
def test_valid_optional_context_size_is_not_a_source_permission(variant):
    value = wire()
    context = value['reading_context']
    if variant == 'bytes':
        context['layout_coverage']['diagnostic_text'] = '原始观察' * 150_000
    elif variant == 'array':
        context['deferred'] = [{'package_id': f'p{i}', 'reason': 'observed'} for i in range(5000)]
    elif variant == 'policies':
        context['reading_policies'] = [deepcopy(context['reading_policies'][0]) for _ in range(129)]
    else:
        nested = False
        for _ in range(100):
            nested = {'child': nested}
        context['layout_coverage']['details'] = nested
    restored = NarrativeSelectResult.from_dict(value)
    assert restored.to_dict() == value
    assert restored.selection == selection(3).selection
    assert json.loads(canonical_json(restored.to_dict())) == value


@pytest.mark.parametrize('bad', ['cycle', 'nonfinite', 'wrong-reference'])
def test_representation_simplification_keeps_core_invalid_data_invalid(bad):
    value = wire()
    if bad == 'cycle':
        value['reading_context']['layout_coverage']['cycle'] = value['reading_context']
    elif bad == 'nonfinite':
        value['reading_context']['layout_coverage']['bad'] = float('nan')
    else:
        value['reading_context']['groups'][0]['evidence_ids'] = ['foreign-id']
    with pytest.raises((NarrativeContractError, ValueError, TypeError)):
        NarrativeSelectResult.from_dict(value)


def test_automatic_corrupt_cache_candidate_does_not_veto_next_healthy_candidate(monkeypatch, caplog):
    from company_wiki.automation import narrative_generation as owner
    from unit.test_shared_reading_cache_precheck import _base, _final, _version

    good = _version(_final())
    bad = SimpleNamespace(metadata_json='not-json', artifact_version_id='broken')
    class Artifacts:
        def visible_base_generation_candidates(self, **kwargs):
            return bad, good
    monkeypatch.setattr(owner.ReadingReuseVerifier, 'matches', lambda *args: True)
    reads = []
    monkeypatch.setattr(owner, 'read_reuse_pin', lambda *args, **kwargs: reads.append(args) or True)
    payload = SimpleNamespace(subject=SimpleNamespace(kind='raw'))
    pin = owner.find_reuse_pin(Artifacts(), None, payload, _base(), {})
    assert pin['artifact_version_id'] == good.artifact_version_id and len(reads) == 1
    assert 'CACHE_CANDIDATE_INVALID' in caplog.text


@pytest.mark.parametrize('reason', ['source_not_current', 'content_sha256_mismatch', 'source_after_as_of'])
def test_cache_discovery_cannot_convert_actual_source_failure_to_regeneration(reason):
    from company_wiki.automation.narrative_generation import discovered_cache_read
    from company_wiki.automation.narrative_transport_contracts import NarrativeTransportError

    def failure():
        raise NarrativeTransportError('blocked', reason)
    with pytest.raises(NarrativeTransportError) as raised:
        discovered_cache_read(failure)
    assert raised.value.reason == reason


def test_cache_discovery_never_swallows_unknown_fee_or_real_io_failure():
    from company_wiki.automation.narrative_generation import discovered_cache_read

    for error in (ValueError('MODEL_BUDGET_RESERVATION_UNKNOWN'), OSError('artifact read IO unavailable')):
        def failure():
            raise error
        with pytest.raises(type(error)):
            discovered_cache_read(failure)


def test_derived_artifact_integrity_failure_is_a_discovery_miss_only():
    from company_wiki.automation.narrative_generation import discovered_cache_read
    from company_wiki.automation.narrative_transport_contracts import NarrativeTransportError

    def failure():
        raise NarrativeTransportError('unavailable', 'narrative_artifact_corrupt')
    assert discovered_cache_read(failure) is False
    # Explicit readers do not enter the discovery adapter.
    with pytest.raises(NarrativeTransportError):
        failure()


def test_large_logical_artifact_reference_still_requires_valid_identity():
    from company_wiki.automation.narrative_transport_contracts import NarrativeRef
    value = {'schema_version': 'narrative-ref/1', 'artifact_version_id': 'narrative-large',
             'artifact_sha256': 'a' * 64, 'byte_size': 2_000_000,
             'source_ref': selection(1).source_ref.to_dict()}
    assert NarrativeRef.from_dict(value).byte_size == 2_000_000
    value['artifact_sha256'] = 'wrong'
    with pytest.raises(NarrativeContractError):
        NarrativeRef.from_dict(value)


@pytest.mark.parametrize('finish', ['stop', 'length'])
def test_observed_model_content_size_cannot_hide_configured_usage_or_finish(finish):
    import time
    from company_wiki.automation.narrative_http_model import NarrativeHTTPModel, ModelOutputTruncatedError
    from company_wiki.automation.narrative_model import NarrativeModelRequest

    content = '业务原文' * 20_000
    model = NarrativeHTTPModel(model_id='synthetic-model', endpoint='https://example.invalid/v1/chat/completions',
                               api_key_env='UNUSED_SYNTHETIC_KEY', max_response_bytes=1_000_000)
    request = NarrativeModelRequest('prompt/1', 'Only source data.', '{}', 'a' * 64)
    body = json.dumps({'model': 'synthetic-model', 'choices': [{'message': {'content': content},
                      'finish_reason': finish}], 'usage': {'prompt_tokens': 11, 'completion_tokens': 23}}).encode()
    if finish == 'length':
        with pytest.raises(ModelOutputTruncatedError) as truncated:
            model._response(request, body, time.monotonic(), http_status=200)
        assert truncated.value.output_tokens == 23 and truncated.value.content_bytes == len(content.encode())
    else:
        result = model._response(request, body, time.monotonic(), http_status=200)
        assert result.response_bytes == content.encode() and result.output_tokens == 23


def test_actual_handler_preserves_verified_material_with_large_optional_diagnostics():
    from dataclasses import replace
    from company_wiki.automation.models import HandlerOutcome
    from company_wiki.source_catalog.narrative_evidence import select_narrative_evidence
    from unit.test_narrative_select_handler import _run, _payload, _pdf_bytes

    data = _pdf_bytes('Company launched a new product.')
    payload = _payload(data, title='Annual Report.pdf', document_kind='annual_report',
                       language='en', mime_type='application/pdf')

    def selector(parsed, **kwargs):
        package = select_narrative_evidence(parsed, title='Annual Report', existing_kind='annual_report',
                                            selector_version='0.9.0')
        assert package.evidence_spans
        context = dict(package.reading_context)
        context['layout_coverage'] = {**context['layout_coverage'], 'diagnostic_text': 'observed' * 200_000}
        return replace(package, reading_context=context)

    result, _ = _run(payload, data, selector=selector)
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    selected = NarrativeSelectResult.from_dict(result.result)
    assert selected.evidence_spans and selected.encoded_size > 1_000_000
    assert selected.source_ref.content_sha256 == payload['source_ref']['content_sha256']
