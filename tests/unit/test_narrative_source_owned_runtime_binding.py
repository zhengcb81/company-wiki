"""One frozen model boundary owns generation, execution and verification."""

from dataclasses import replace
import json

import pytest

from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_contracts import NarrativeSelectResult, NarrativeSummaryResult
from company_wiki.automation.narrative_model import NarrativeModelRequest, NarrativeModelResponse
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.source_catalog.narrative_evidence import NARRATIVE_SELECTOR_NAME
from support.narrative_model_request_fixture import selection
from unit.test_narrative_batch import _request
from unit.test_narrative_generation import manifest
from unit.test_narrative_reading_transport import with_reading
from unit.test_narrative_summarize_handler import _context


V2 = "reading-model-input/2"
PROMPT = "reading-source-owned/2.0.0"


def _selected():
    wire = with_reading(selection(3)).to_dict()
    wire["selector"] = {"name": NARRATIVE_SELECTOR_NAME, "version": "0.9.0"}
    return NarrativeSelectResult.from_dict(wire)


def _claims(selected):
    return {"draft": {"claims": [{
        "claim_id": "one", "text": "公司新产品已经完成海外客户认证，正在推进新业务。",
        "evidence_ids": ["e1"], "evidence_group_ids": [],
        "claim_type": "company_statement", "modality": "actual",
    }]}}


def test_new_reading_generation_uses_source_owned_boundary_only_for_new_reading_jobs():
    from company_wiki.automation.narrative_model_runtime import resolve_model_boundary

    reading = manifest(replace(_request(), selector_version="0.9.0"))
    legacy = manifest(replace(_request(), selector_version="0.8.0"))
    assert reading["reading_model_projection"] == "reading-model-input/4"
    assert reading["execution_versions"]["prompt"] == resolve_model_boundary("reading-model-input/4").prompt_version
    assert reading["execution_versions"]["model_request_schema"] == "narrative-model-request/5"
    assert "reading_model_boundary" in reading
    assert "reading_model_projection" not in legacy
    assert "reading_model_boundary" not in legacy
    assert legacy["execution_versions"]["prompt"] == "1.7.0"


def test_v2_causal_boundary_is_real_content_and_decoder_not_just_a_label(monkeypatch):
    from company_wiki.automation import narrative_model as model
    from company_wiki.automation.narrative_generation import generation_manifest
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
    from unit.test_narrative_batch import Reader, _module

    request = replace(_request(), selector_version="0.9.0")
    payload = SourceRevisionEventPayload.from_dict(json.loads(
        _module().build_batch_events(request, Reader(), now="2026-10-09T00:00:00Z").events[0].payload_json
    ))
    versions = _module()._execution_versions(request)
    original = generation_manifest(request, payload, execution_versions=versions, reading_model_projection=V2)
    boundary = original["reading_model_boundary"]
    assert boundary["prompt_version"] == PROMPT
    for name in ("instruction_sha256", "response_schema_sha256", "decoder_sha256"):
        assert len(boundary[name]) == 64 and set(boundary[name]) <= set("0123456789abcdef")
    actual = model.reading_model_boundary_identity

    def changed(version, *, projected=False):
        return {**actual(version, projected=projected), "decoder_sha256": "d" * 64}

    monkeypatch.setattr(model, "reading_model_boundary_identity", changed)
    revised = generation_manifest(request, payload, execution_versions=versions, reading_model_projection=V2)
    assert revised != original
    assert revised["execution_versions"] == original["execution_versions"]


@pytest.mark.parametrize("frozen", [None, "reading-model-input/1"])
def test_explicit_legacy_model_boundary_does_not_gain_new_causal_fields(frozen):
    from company_wiki.automation.narrative_generation import generation_manifest
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
    from unit.test_narrative_batch import Reader, _module

    request = replace(_request(), selector_version="0.9.0")
    payload = SourceRevisionEventPayload.from_dict(json.loads(
        _module().build_batch_events(request, Reader(), now="2026-10-09T00:00:00Z").events[0].payload_json
    ))
    original = generation_manifest(request, payload, execution_versions=_module()._execution_versions(request),
        reading_model_projection=frozen)
    assert "reading_model_boundary" not in original
    assert original["execution_versions"]["prompt"] == "1.7.0"
    if frozen is None:
        assert "reading_model_projection" not in original
    else:
        assert original["reading_model_projection"] == frozen


def test_summarize_uses_same_frozen_boundary_to_send_and_decode_claims_only():
    selected = _selected()
    sent = []

    class Model:
        def generate(self, request):
            sent.append(request)
            return NarrativeModelResponse("offline", "fixture", request.prompt_version,
                json.dumps(_claims(selected), ensure_ascii=False).encode("utf-8"))

    result = NarrativeSummarizeHandler(model=Model(), reading_model_projection=lambda subject: V2)(_context(selected))
    assert result.outcome is HandlerOutcome.SUCCEEDED
    assert len(sent) == 1 and sent[0].prompt_version == PROMPT
    assert NarrativeModelRequest.from_selection(selected, reading_projection_version=V2) == sent[0]
    canonical = NarrativeSummaryResult.from_dict(result.result)
    canonical.validate_against(selected)
    assert canonical.source_ref == selected.source_ref
    assert canonical.draft.source_id == selected.source_ref.source_id
    assert canonical.draft.source_sha256 == selected.source_ref.content_sha256
    assert canonical.draft.language == selected.source_metadata.language


def test_wrong_response_prompt_retains_post_call_diagnostic_and_does_not_build_artifact():
    selected = _selected()
    calls = []

    class Model:
        def generate(self, request):
            calls.append(request)
            return NarrativeModelResponse("offline", "fixture", "1.7.0",
                json.dumps(_claims(selected), ensure_ascii=False).encode("utf-8"))

    result = NarrativeSummarizeHandler(model=Model(), reading_model_projection=lambda subject: V2)(_context(selected))
    assert len(calls) == 1
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == "MODEL_RESPONSE_INVALID"
    assert "failed_final" in result.result
    assert result.artifacts == result.effects == ()


def test_verify_dependency_uses_frozen_boundary_prompt_instead_of_current_global(monkeypatch):
    from company_wiki.automation import narrative_verify as verify
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
    from company_wiki.automation.narrative_model import decode_model_draft

    selected = _selected()
    request = NarrativeModelRequest.from_selection(selected, reading_projection_version=V2)
    response = NarrativeModelResponse("offline", "fixture", request.prompt_version,
        json.dumps(_claims(selected), ensure_ascii=False).encode("utf-8"))
    summary = NarrativeSummaryResult.from_dict({
        "schema_version": "narrative-summary-result/2.0", "source_ref": selected.source_ref.to_dict(),
        "language": selected.source_metadata.language, "translate": False, "status": "completed",
        "draft": decode_model_draft(response, selected=selected, reading_projection_version=V2),
        "model": {"adapter_id": response.adapter_id, "model_id": response.model_id,
            "prompt_version": response.prompt_version, "response_sha256": response.response_sha256},
        "prompt_review": selected.prompt_review.to_dict(),
    })
    payload = SourceRevisionEventPayload.from_dict({
        "schema_version": "source-revision-event/2.0", "source_ref": selected.source_ref.to_dict(),
        "expected_read_policy_sha256": selected.expected_read_policy_sha256,
        "source_metadata": selected.source_metadata.to_dict(),
    })
    # This focused test isolates per-job prompt ownership; media replay has its
    # own production-DAG tests and is not forged into a source proof here.
    monkeypatch.setattr(verify, "parser_component", lambda *args, **kwargs: (selected.parser.name, selected.parser.version))
    verify._validate_dependency_identity(payload, selected, summary, selector_version="0.9.0",
        reading_projection_version=V2)
    with pytest.raises(verify._VerifyFailure, match="component version"):
        verify._validate_dependency_identity(payload, selected, summary, selector_version="0.9.0",
            reading_projection_version="reading-model-input/1")
