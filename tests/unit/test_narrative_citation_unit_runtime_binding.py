"""The one frozen citation-unit boundary owns runtime, language and causality."""

from dataclasses import replace
import hashlib
import json

import pytest

from company_wiki.automation.models import HandlerMetrics, HandlerOutcome
from company_wiki.automation.narrative_contracts import NarrativeSummaryResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from unit.test_narrative_batch import _request
from unit.test_narrative_generation import manifest
from unit.test_narrative_output_language_binding import EN, ES, manifests, selected_english
from unit.test_narrative_summarize_handler import _context


V3 = "reading-model-input/3"


def _run(*, text=EN):
    selected = selected_english()
    sent, finals = [], []
    metrics = HandlerMetrics(tokens=92, cost_usd=0.001, duration_ms=7)

    class Caller:
        def generate(self, context, request):
            sent.append(request)
            envelope = json.loads(request.data_json)
            assert envelope["schema_version"] == "narrative-model-request/4"
            assert envelope["citation_unit_columns"] == ["id", "evidence_ids", "support_evidence_ids"]
            unit_id = envelope["citation_units"][0][0]
            final = json.dumps({"claims": [{"claim_id": "one", "text": text,
                "citation_unit_ids": [unit_id], "claim_type": "company_statement",
                "modality": "actual"}]}, ensure_ascii=False).encode("utf-8")
            finals.append(final)
            return NarrativeModelResponse("offline", "fixture", request.prompt_version, final), metrics

    result = NarrativeSummarizeHandler(model=None, model_caller=Caller(),
        reading_model_projection=lambda subject: V3)(_context(selected))
    assert len(sent) == len(finals) == 1
    assert result.metrics == metrics
    return result, selected, sent[0], finals[0]


def test_new_reading_generation_selects_single_citation_units_and_preserves_legacy_default():
    reading = manifest(replace(_request(), selector_version="0.9.0"))
    legacy = manifest(replace(_request(), selector_version="0.8.0"))
    assert reading["reading_model_projection"] == V3
    assert reading["execution_versions"]["model_request_schema"] == "narrative-model-request/4"
    assert reading["execution_versions"]["prompt"] == reading["reading_model_boundary"]["prompt_version"]
    assert "summary_validation" in reading
    assert "reading_model_projection" not in legacy
    assert legacy["execution_versions"]["prompt"] == "1.7.0"


def test_single_unit_reply_is_canonicalized_using_only_its_pinned_source():
    result, selected, _, _ = _run()
    assert result.outcome is HandlerOutcome.SUCCEEDED
    canonical = NarrativeSummaryResult.from_dict(result.result)
    canonical.validate_against(selected)
    assert canonical.draft.source_id == selected.source_ref.source_id
    assert canonical.draft.source_sha256 == selected.source_ref.content_sha256
    assert canonical.draft.language == "en"
    assert canonical.draft.claims[0].evidence_ids == (selected.evidence_spans[0].span_id,)
    assert canonical.draft.claims[0].text == EN


def test_new_protocol_cannot_skip_actual_output_language_or_refund_paid_metrics():
    result, _, _, final = _run(text=ES)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == "SUMMARY_INVALID"
    assert "rule=OUTPUT_LANGUAGE" in result.error.detail
    assert result.result["failed_final"]["final_content_sha256"] == hashlib.sha256(final).hexdigest()
    assert result.artifacts == result.effects == ()


@pytest.mark.parametrize("state", ["uncertain", "unavailable"])
def test_new_protocol_observer_abstention_is_consumable_quality_metadata(monkeypatch, state):
    from company_wiki.automation import narrative_output_language as observer

    monkeypatch.setattr(observer, "observe_summary_language", lambda *args, **kwargs:
        observer.LanguageObservation(state, None, (), 0))
    result, selected, _, _ = _run()
    assert result.outcome is HandlerOutcome.SUCCEEDED
    canonical = NarrativeSummaryResult.from_dict(result.result)
    canonical.validate_against(selected)
    assert canonical.draft.status == "needs_review"
    assert canonical.draft.claims[0].needs_review


def test_frozen_new_validator_and_actual_model_boundary_are_both_checked_on_resume(monkeypatch):
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation import narrative_summarize as summarize
    from company_wiki.automation import narrative_worker_factory as worker
    from company_wiki.automation.narrative_model import ModelResponseError

    current = manifests(V3)
    assert current["summary_validation"] == summarize.reading_summary_validation_identity()
    frozen = json.dumps(batch._freeze_generations({"one": current}))
    assert worker._reading_projection_versions(frozen) == {"one": V3}
    actual = summarize.reading_summary_validation_identity
    monkeypatch.setattr(summarize, "reading_summary_validation_identity", lambda:
        {**actual(), "observer_sha256": "d" * 64})
    with pytest.raises(ModelResponseError, match="READING_SUMMARY_VALIDATION_UNAVAILABLE"):
        worker._reading_projection_versions(frozen)


def test_explicit_frozen_v2_keeps_its_own_prompt_and_request_schema():
    old = manifests("reading-model-input/2")
    assert old["reading_model_projection"] == "reading-model-input/2"
    assert old["execution_versions"]["prompt"] == "reading-source-owned/2.0.0"
    assert old["execution_versions"]["model_request_schema"] == "narrative-model-request/3"
