"""Actual prose observation is a v2 summary responsibility, with frozen causality."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from company_wiki.automation import narrative_summarize as summarize
from company_wiki.automation.models import HandlerMetrics, HandlerOutcome
from company_wiki.automation.narrative_contracts import NarrativeSelectResult, NarrativeSummaryResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_output_language import LanguageObservation
from company_wiki.source_catalog.narrative_evidence import NARRATIVE_SELECTOR_NAME
from company_wiki.source_contract import EvidenceSpan
from support.narrative_model_request_fixture import selection
from unit.test_narrative_reading_transport import with_reading
from unit.test_narrative_summarize_handler import _context


V2 = "reading-model-input/2"
EN = "We expanded production capacity and added new customers in overseas markets. The new facility has begun commercial deliveries and the team is developing additional products."
ES = "La empresa amplió su capacidad de producción y añadió nuevos clientes en mercados internacionales. La nueva planta ha comenzado las entregas comerciales y el equipo desarrolla nuevos productos."


def selected_english():
    wire = selection(1).to_dict()
    original = wire["evidence_spans"][0]
    wire["evidence_spans"] = [EvidenceSpan.create(
        source_id=original["source_id"], coordinates=selection(1).evidence_spans[0].coordinates,
        raw_text=EN, structured_value={**original["structured_value"], "language": "en"},
        parser_name=original["parser_name"], parser_version=original["parser_version"],
        parse_status="parsed", quality_flags=(),
    ).to_dict()]
    wire["source_metadata"]["language"] = "en"
    wire["selector"] = {"name": NARRATIVE_SELECTOR_NAME, "version": "0.9.0"}
    return with_reading(NarrativeSelectResult.from_dict(wire))


def run_summary(selected, *, text=EN, projection=V2):
    calls = []
    finals = []
    metrics = HandlerMetrics(tokens=92, cost_usd=0.001, duration_ms=7)

    class Caller:
        def generate(self, context, request):
            calls.append(request)
            draft = {"claims": [{"claim_id": "one", "text": text, "evidence_ids": ["e1"],
                "claim_type": "company_statement", "modality": "actual", "needs_review": False}]}
            if projection != V2:
                draft.update(source_id=selected.source_ref.source_id,
                    source_sha256=selected.source_ref.content_sha256,
                    language=selected.source_metadata.language, status="draft")
            final = json.dumps({"draft": draft}, ensure_ascii=False).encode("utf-8")
            finals.append(final)
            return NarrativeModelResponse("offline", "fixture", request.prompt_version, final), metrics

    result = summarize.NarrativeSummarizeHandler(model=None, model_caller=Caller(),
        reading_model_projection=lambda subject: projection)(_context(selected))
    assert len(calls) == len(finals) == 1
    assert result.metrics == metrics
    return result, finals[0]


def test_actual_spanish_body_cannot_pass_an_english_pinned_header():
    result, final = run_summary(selected_english(), text=ES)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == "SUMMARY_INVALID"
    assert "rule=OUTPUT_LANGUAGE" in result.error.detail
    assert result.artifacts == result.effects == ()
    observed = result.result["failed_final"]
    assert observed["final_content_sha256"] == hashlib.sha256(final).hexdigest()
    assert observed["final_content_bytes"] == len(final)


def test_actual_original_english_prose_remains_source_bound():
    selected = selected_english()
    result, _ = run_summary(selected)
    assert result.outcome is HandlerOutcome.SUCCEEDED
    canonical = NarrativeSummaryResult.from_dict(result.result)
    canonical.validate_against(selected)
    assert canonical.draft.status == "draft"
    assert not canonical.draft.claims[0].needs_review


@pytest.mark.parametrize("state", ["uncertain", "unavailable"])
def test_observation_abstention_is_quality_metadata_and_not_permission(monkeypatch, caplog, state):
    from company_wiki.automation import narrative_output_language as observer

    monkeypatch.setattr(observer, "observe_summary_language", lambda *args, **kwargs:
        LanguageObservation(state, None, (), 0))
    selected = selected_english()
    result, _ = run_summary(selected)
    assert result.outcome is HandlerOutcome.SUCCEEDED
    canonical = NarrativeSummaryResult.from_dict(result.result)
    canonical.validate_against(selected)
    assert canonical.draft.status == "needs_review"
    assert all(claim.needs_review for claim in canonical.draft.claims)
    assert f"SUMMARY_LANGUAGE_{state.upper()}" in caplog.text
    assert EN not in caplog.text


@pytest.mark.parametrize("legacy", [None, "reading-model-input/1"])
def test_frozen_legacy_summary_is_not_reinterpreted_by_new_observer(monkeypatch, legacy):
    from company_wiki.automation import narrative_output_language as observer

    def forbidden(*args, **kwargs):
        raise AssertionError("legacy bytes must not enter the new observation boundary")

    monkeypatch.setattr(observer, "observe_summary_language", forbidden)
    result, _ = run_summary(selected_english(), text=ES, projection=legacy)
    assert result.outcome is HandlerOutcome.SUCCEEDED
    assert NarrativeSummaryResult.from_dict(result.result).draft.status == "draft"


def manifests(projection=V2):
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
    from company_wiki.automation.narrative_generation import generation_manifest
    from unit.test_narrative_batch import Reader, _request

    request = replace(_request(), selector_version="0.9.0")
    event = batch.build_batch_events(request, Reader(), now="2026-10-14T00:00:00Z").events[0]
    payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
    return generation_manifest(request, payload, execution_versions=batch._execution_versions(request),
        reading_model_projection=projection)


def test_v2_freezes_actual_summary_validator_without_resigning_core_decoder_or_legacy(monkeypatch):
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation import narrative_worker_factory as worker
    from company_wiki.automation.narrative_model import ModelResponseError

    original = manifests()
    actual = summarize.reading_summary_validation_identity
    assert original["summary_validation"] == actual()
    core = dict(original["reading_model_boundary"])
    frozen = json.dumps(batch._freeze_generations({"one": original}))
    assert worker._reading_projection_versions(frozen) == {"one": V2}
    monkeypatch.setattr(summarize, "reading_summary_validation_identity", lambda:
        {**actual(), "observer_sha256": "d" * 64})
    changed = manifests()
    assert changed["summary_validation"] != original["summary_validation"]
    assert changed["reading_model_boundary"] == core
    with pytest.raises(ModelResponseError, match="READING_SUMMARY_VALIDATION_UNAVAILABLE"):
        worker._reading_projection_versions(frozen)
    for legacy in (None, "reading-model-input/1"):
        assert "summary_validation" not in manifests(legacy)


def test_summary_validator_fingerprint_is_pathless_lf_normalized_and_actual_content(tmp_path, monkeypatch):
    from company_wiki.automation import narrative_output_language as observer

    original_file = observer.__file__
    original = summarize.reading_summary_validation_identity()
    copied = tmp_path / "observer.py"
    copied.write_bytes(Path(original_file).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    monkeypatch.setattr(observer, "__file__", str(copied))
    assert summarize.reading_summary_validation_identity() == original
    copied.write_bytes(copied.read_bytes() + b"\n# material behavior changes must invalidate\n")
    revised = summarize.reading_summary_validation_identity()
    assert revised["observer_sha256"] != original["observer_sha256"]
    assert revised["summary_handler_sha256"] == original["summary_handler_sha256"]
    assert revised["detector_distribution"] == "py3langid/0.4.0"
    assert str(tmp_path) not in json.dumps(revised)


def test_actual_observer_resource_identity_invalidates_frozen_v2_without_changing_core(monkeypatch):
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation import narrative_worker_factory as worker
    from company_wiki.automation import narrative_output_language as observer
    from company_wiki.automation.narrative_model import ModelResponseError

    original = manifests()
    identity = observer.language_observer_identity()
    assert original["summary_validation"]["language_observer"] == identity
    frozen = json.dumps(batch._freeze_generations({"one": original}))
    monkeypatch.setattr(observer, "language_observer_identity", lambda: {
        **identity, "py3langid": {**identity["py3langid"],
            "model": {"status": "unavailable"}}})
    changed = manifests()
    assert changed["summary_validation"] != original["summary_validation"]
    assert changed["reading_model_boundary"] == original["reading_model_boundary"]
    with pytest.raises(ModelResponseError, match="READING_SUMMARY_VALIDATION_UNAVAILABLE"):
        worker._reading_projection_versions(frozen)
