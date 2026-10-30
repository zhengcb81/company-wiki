"""Atomic recipe survives publication and terminal projections without downgrades."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.models import canonical_json_hash, make_effect_key
from company_wiki.automation.narrative_contracts import NarrativeBundle, NarrativeContractError, NarrativeSelectResult
from company_wiki.automation.narrative_generation import generation_manifest
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_runtime import build_model_request
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.narrative_summary_execution import extract_summary_execution, parse_summary_job_result, wrap_summary
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from unit.test_narrative_extractive_runtime import selected

VERSION = 'reading-model-input/7'
ASSESSOR = 'source-summary-assessment/1.1.0'


def materials(source=None, version=VERSION):
    source = source or selected(1, text_suffix='甲方正在完善海外服务网络。')
    request = build_model_request(source, reading_projection_version=version)
    response = NarrativeModelResponse('offline', 'synthetic', request.prompt_version, json.dumps({
        'drafts_by_task': {'t1': [{'text': '甲方正在完善海外服务网络。',
                                 'basis_parts': ['p1'], 'modality': 'planned'}]}
    }, ensure_ascii=False).encode())
    report = {}
    summary = NarrativeSummarizeHandler._completed_result(source, source.prompt_review, response,
        reading_projection_version=version, execution_report=report)
    return source, summary, report


@pytest.mark.parametrize('language_state', ['same', 'uncertain'])
def test_completed_language_projection_wrapper_and_terminal_keep_atomic_assessor_and_risk(monkeypatch, language_state):
    monkeypatch.setattr('company_wiki.automation.narrative_output_language.observe_summary_language',
                        lambda *args, **kwargs: SimpleNamespace(state=language_state))
    source, summary, report = materials()
    assert report['validator']['version'] == ASSESSOR
    assert summary.draft.claims[0].needs_review
    assert summary.draft.status == 'needs_review'
    assert 'possible_current_action_as_future' in {row['rule_code'] for row in report['diagnostics']}
    assert report['claims_sha256'] == canonical_json_hash(summary.to_dict()['draft']['claims'])
    wrapped = wrap_summary(summary, report)
    assert parse_summary_job_result(wrapped, selected=source) == summary
    assert extract_summary_execution(wrapped) == report
    terminal = {'schema_version': 'narrative-terminal-receipt/1.0', 'execution': report}
    assert extract_summary_execution(terminal) == report


@pytest.mark.parametrize('projected', [False, True])
def test_atomic_bundle_raw_or_projected_preserves_quality_and_assessment(projected):
    from unit.test_narrative_source_owned_model_boundary import official_reading
    source = official_reading() if projected else None
    source, summary, report = materials(source)
    bundle = NarrativeVerifyHandler._bundle(source, summary, source.prompt_review,
                                           reading_projection_version=VERSION)
    wire = bundle.to_dict()
    assert wire['schema_version'] == ('narrative-bundle/3.1' if projected else 'narrative-bundle/2.1')
    assert wire['summary_assessment']['validator']['version'] == ASSESSOR
    assert wire['summary_assessment'] == report
    assert wire['quality_status'] == 'needs_review'
    assert wire['summary_assessment']['semantic_status'] == 'not_evaluated'
    assert NarrativeBundle.from_dict(wire).to_dict() == wire
    context = SimpleNamespace(job=SimpleNamespace(job_id='atomic-verify'),
                              event=SimpleNamespace(observed_at='2026-10-30T12:00:00Z'))
    effect = NarrativeVerifyHandler._effect(context, bundle, generation_sha256='a' * 64)
    payload = canonical_json_hash({'verification_job_id': 'atomic-verify',
                                   'bundle_sha256': canonical_json_hash(wire)})
    assert effect.effect_key == make_effect_key(effect.effect_type, effect.target, payload, '1.1.0')


@pytest.mark.parametrize('projected', [False, True])
def test_atomic_skip_and_generation_choose_new_family_without_fake_assessment(projected):
    from unit.test_narrative_source_owned_model_boundary import official_reading
    source = official_reading() if projected else selected(1)
    raw = source.to_dict()
    raw['evidence_spans'] = []
    raw['selection'].update(status='skipped_no_narrative', selected_count=0)
    raw['reading_context']['groups'] = []
    source = NarrativeSelectResult.from_dict(raw)
    summary = NarrativeSummarizeHandler._skip_result(source)
    wire = NarrativeVerifyHandler._bundle(source, summary, source.prompt_review,
                                          reading_projection_version=VERSION).to_dict()
    assert wire['schema_version'] == ('narrative-bundle/3.1' if projected else 'narrative-bundle/2.1')
    assert wire['versions']['prompt'] == 'reading-source-scoped/4.3.0'
    assert wire['versions']['bundle_producer'] == '1.1.0'
    assert wire['summary_assessment'] is None and wire['summary']['model'] is None
    assert NarrativeBundle.from_dict(wire).to_dict() == wire
    from unit.test_narrative_batch import _request
    from unit.test_narrative_reading_projection_generation import payload
    request = replace(_request(), selector_version='0.9.0', reading_model_projection=VERSION)
    manifest = generation_manifest(request, payload(request), execution_versions=batch._execution_versions(request),
                                   reading_model_projection=VERSION)
    assert manifest['bundle_schema'] == 'narrative-bundle/2.1'
    assert manifest['bundle_producer'] == wire['versions']['bundle_producer']
    assert manifest['execution_versions']['prompt'] == wire['versions']['prompt']


@pytest.mark.parametrize('target', ['bundle', 'wrapper', 'terminal'])
def test_atomic_assessment_downgrade_or_quality_erasure_rejected(target):
    source, summary, report = materials()
    if target == 'bundle':
        wire = NarrativeVerifyHandler._bundle(source, summary, source.prompt_review,
                                              reading_projection_version=VERSION).to_dict()
        wire['summary_assessment']['validator']['version'] = 'source-summary-assessment/1.0.0'
        with pytest.raises(NarrativeContractError):
            NarrativeBundle.from_dict(wire)
    elif target == 'wrapper':
        wire = wrap_summary(summary, report)
        wire['assessment']['validator']['version'] = 'source-summary-assessment/1.0.0'
        with pytest.raises(NarrativeContractError):
            parse_summary_job_result(wire, selected=source)
    else:
        altered = deepcopy(report)
        altered['known_constraint_status'] = 'no_known_violation'
        with pytest.raises(NarrativeContractError):
            extract_summary_execution({'schema_version': 'narrative-terminal-receipt/1.0',
                                       'execution': altered})


def test_old_six_completed_result_still_uses_original_assessor_without_atomic_diagnostic():
    source, summary, report = materials(version='reading-model-input/6')
    assert report['validator']['version'] == 'source-summary-assessment/1.0.0'
    assert not report['diagnostics']
    assert parse_summary_job_result(wrap_summary(summary, report), selected=source) == summary

@pytest.mark.parametrize('target', ['bundle', 'wrapper'])
def test_atomic_risk_cannot_be_erased_by_rehashing_final_claims(target):
    source, summary, report = materials()
    if target == 'bundle':
        wire = NarrativeVerifyHandler._bundle(source, summary, source.prompt_review,
                                              reading_projection_version=VERSION).to_dict()
        claims = wire['summary']['draft']['claims']
        claims[0]['needs_review'] = False
        wire['summary']['draft']['status'] = 'draft'
        wire['quality_status'] = 'verified'
        wire['summary_assessment']['claims_sha256'] = canonical_json_hash(claims)
        with pytest.raises(NarrativeContractError):
            NarrativeBundle.from_dict(wire)
    else:
        wire = wrap_summary(summary, report)
        claims = wire['summary']['draft']['claims']
        claims[0]['needs_review'] = False
        wire['summary']['draft']['status'] = 'draft'
        wire['assessment']['claims_sha256'] = canonical_json_hash(claims)
        with pytest.raises(NarrativeContractError):
            parse_summary_job_result(wire, selected=source)
