"""Hints never duplicate body text or grow without a bounded observation."""
import pytest

from company_wiki.automation import narrative_frame_hints as hints


def test_shared_source_is_framed_once_and_never_copied_into_hint_rows(monkeypatch):
    calls = []
    original = hints.source_assertion_frames

    def observe(text):
        calls.append(text)
        return original(text)

    monkeypatch.setattr(hints, 'source_assertion_frames', observe)
    source = '甲方正在完善服务网络。'
    value = hints.compact_frame_hints([('s1', source), ('s1', source)])
    assert calls == [source]
    assert value['sources']['s1'] == [{'ordinal': 0, 'ongoing': True}]
    assert not value['limited']


def test_duplicate_source_key_cannot_borrow_another_fragments_text():
    with pytest.raises(ValueError):
        hints.compact_frame_hints([('s1', 'first'), ('s1', 'another')])


def test_missing_observations_leave_source_tasks_unrestricted():
    value = hints.compact_frame_hints([('s1', 'A source sentence with unknown grammar.')])
    assert value['sources'] == {} and value['observed_count'] == 0
    assert not value['limited']
    assert 'admitted' not in value and 'rejected' not in value


def test_per_source_and_global_limits_remain_visible_without_removing_originals():
    source = '甲方正在完善服务网络。' * 100
    value = hints.compact_frame_hints([(f's{i}', source) for i in range(6)])
    assert value['observed_count'] == 600 and value['limited']
    assert all(len(rows) <= hints.MAX_HINTS_PER_SOURCE for rows in value['sources'].values())
    assert sum(map(len, value['sources'].values())) == hints.MAX_HINTS


def test_context_only_fragment_cannot_donate_source_hints_or_change_support():
    import hashlib
    import json
    from copy import deepcopy
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult
    from company_wiki.automation.narrative_model_runtime import build_model_request
    from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
    from unit.test_narrative_extractive_runtime import selected

    source = selected(2, text_suffix='甲方正在完善服务网络。')
    wire = source.to_dict()
    ids = [span.span_id for span in source.evidence_spans]
    digest = hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()
    wire['reading_context'].update(schema_version='du-production-reading/2', groups=[{
        'group_id': 'urn:company-wiki:reading-group:sha256:' + digest,
        'kind': 'business_progress', 'section_role': 'business', 'evidence_ids': ids,
        'citation_views': [{'support_evidence_ids': ids[1:], 'context_evidence_ids': ids[:1]}]}])
    source = NarrativeSelectResult.from_dict(wire)
    before = deepcopy(source.to_dict())
    view = compile_scoped_model_view(source, max_claims=40)
    material = json.loads(build_model_request(source, reading_projection_version='reading-model-input/7').data_json)['material']
    actual_hints = material['source_frame_hints']['sources']
    assert view._source_keys[ids[0]] not in actual_hints
    assert view._source_keys[ids[1]] in actual_hints
    assert view.model_tasks[0].support_ids == (ids[1],)
    assert view.model_tasks[0].context_ids == (ids[0],)
    assert source.to_dict() == before


def test_atomic_hint_bytes_are_inside_actual_http_budget_and_attempt_identity():
    import hashlib
    import json
    from types import SimpleNamespace
    from company_wiki.automation.models import canonical_json_hash
    from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
    from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller, NarrativeBudgetCallError
    from company_wiki.automation.narrative_model_runtime import build_model_request
    from unit.test_narrative_extractive_runtime import selected

    request = build_model_request(selected(2, text_suffix='甲方正在完善服务网络。'),
                                  reading_projection_version='reading-model-input/7').with_output_budget(8192)
    model = NarrativeHTTPModel(model_id='owned-no-post-fixture', endpoint='https://fixture.invalid/v1',
                               api_key_env='NO_REAL_KEY', max_output_tokens=8192)
    body = model.request_bytes(request)
    assert json.loads(json.loads(body)['messages'][1]['content'])['material']['source_frame_hints']['sources']
    captured = {}

    class RefusingStore:
        def get_run(self, run_id):
            return SimpleNamespace(pricing_version='synthetic-budget-only')

        def reserve_model_attempt(self, **kwargs):
            captured.update(kwargs)
            raise RuntimeError('owned refusal before HTTP')

    attempt = SimpleNamespace(attempt_id='owned-attempt', lease_token='owned-lease', runtime_generation=1)
    context = SimpleNamespace(checkpoint=lambda: None, attempt=attempt, job=SimpleNamespace(job_id='owned-job'))
    caller = BudgetedNarrativeCaller(store=RefusingStore(), run_id='owned-run', model=model)
    with pytest.raises(NarrativeBudgetCallError, match='MODEL_ADMISSION_INVALID'):
        caller.generate(context, request)
    assert captured['input_tokens_bound'] == len(body) + 128
    assert captured['request_sha256'] == canonical_json_hash({
        'schema_version': 'narrative-model-attempt/2', 'model_input_sha256': request.input_sha256,
        'http_body_sha256': hashlib.sha256(body).hexdigest()})
    assert captured['max_output_tokens'] == 8192
