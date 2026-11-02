"""Generated source-valid output is not licensed by prompt compression quotas."""
from dataclasses import replace
import json

import pytest

from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_contracts import NarrativeSelectResult, NarrativeSummaryResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_runtime import build_model_request, decode_model_draft
from company_wiki.automation import narrative_output_language as language_observer
from company_wiki.source_catalog.narrative_document import NarrativeEvidencePackage
from company_wiki.source_catalog.narrative_evidence import SourceSummaryDraft, SummaryClaim, validate_summary_draft
from unit import test_narrative_select_handler as selection_fixture
from unit import test_narrative_summarize_handler as summary_fixture
from unit.test_narrative_reading_transport import reading_context


@pytest.fixture(scope="module")
def actual_source():
    statements = [f"Company delivered {1001 + i} pumps in 2026." for i in range(45)]
    original = selection_fixture._pdf_bytes("\n".join(statements))
    event = selection_fixture._payload(original, title="Synthetic source", document_kind="annual_report",
                                       language="en", mime_type="application/pdf")

    def select(parsed, **_kwargs):
        spans = tuple(unit.to_evidence_span(topics=(), selection_reasons=("business_progress",))
                      for unit in parsed.units)
        return NarrativeEvidencePackage(
            source_id=parsed.source_id, source_sha256=parsed.source_sha256, document_kind="annual_report",
            status="selected", evidence_spans=spans, selection_limit=len(spans), candidate_count=len(spans),
            dropped_financial_count=0, source_units=len(parsed.units), omitted_candidate_count=0,
            coverage_complete=True,
        )

    result, _ = selection_fixture._run(event, original, selector=select)
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    selected = NarrativeSelectResult.from_dict(result.result)
    assert len(selected.evidence_spans) == 1
    assert all(text in selected.evidence_spans[0].raw_text for text in statements)
    return selected, statements


def _claims(source, texts):
    return [SummaryClaim(f"claim-{i}", text, (source.evidence_spans[0].span_id,),
                         "company_statement", "actual") for i, text in enumerate(texts)]


@pytest.mark.parametrize("form", ["long_qualified_quote", "twenty_one", "forty_one"])
def test_public_handler_preserves_source_valid_generated_claims(actual_source, form):
    source, statements = actual_source
    texts = [source.evidence_spans[0].raw_text] if form == "long_qualified_quote" else statements[:21 if form == "twenty_one" else 41]
    claims = _claims(source, texts)
    typed = SourceSummaryDraft(source.source_ref.source_id, source.source_ref.content_sha256, "en", tuple(claims))
    validate_summary_draft(typed, source_id=source.source_ref.source_id,
                          source_sha256=source.source_ref.content_sha256, language="en",
                          evidence_spans=source.evidence_spans)
    model = summary_fixture.ReplayModel(draft_overrides={"claims": [
        {"claim_id": claim.claim_id, "text": claim.text, "evidence_ids": list(claim.evidence_ids),
         "claim_type": claim.claim_type, "modality": claim.modality, "needs_review": False}
        for claim in claims
    ]})
    result, _, _ = summary_fixture._run(source, model=model)
    assert result.outcome is HandlerOutcome.SUCCEEDED, result.error
    summary = NarrativeSummaryResult.from_dict(result.result)
    summary.validate_against(source)
    assert summary.draft is not None
    assert [claim.text for claim in summary.draft.claims] == texts
    assert len(model.calls) == 1 and result.effects == ()


@pytest.mark.parametrize("projection", ["reading-model-input/4", "reading-model-input/6", "reading-model-input/7"])
@pytest.mark.parametrize("form", ["long_qualified_quote", "three_clauses", "forty_one"])
def test_actual_scoped_protocols_keep_valid_prose_without_decoder_quotas(actual_source, projection, form):
    source, statements = actual_source
    source = replace(source, reading_context=reading_context(source))
    texts = [source.evidence_spans[0].raw_text] if form == "long_qualified_quote" else statements[:3 if form == "three_clauses" else 41]
    request = build_model_request(source, reading_projection_version=projection)
    response = NarrativeModelResponse("synthetic", "configured", request.prompt_version,
        json.dumps({"drafts_by_task": {"t1": [{"text": text, "basis_parts": ["p1"], "modality": "actual"}
                                               for text in texts]}}).encode())
    draft = decode_model_draft(response, selected=source, reading_projection_version=projection)
    assert [claim["text"] for claim in draft["claims"]] == texts
    assert all(claim["evidence_ids"] == [source.evidence_spans[0].span_id] for claim in draft["claims"])


@pytest.mark.parametrize("projection", [None, "reading-model-input/4", "reading-model-input/6", "reading-model-input/7"])
def test_response_schema_has_no_compression_license(actual_source, projection):
    source = actual_source[0]
    if projection is not None:
        source = replace(source, reading_context=reading_context(source))
    wire = json.loads(build_model_request(source, reading_projection_version=projection).data_json)
    schema = wire["response_schema"]

    def visit(value):
        if isinstance(value, dict):
            assert not (value.get("type") == "string" and value.get("maxLength") == 280)
            assert not (value.get("type") == "array" and value.get("maxItems") in {2, 6, 20, 40})
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)


@pytest.mark.parametrize("form", ["many_claims", "many_spans", "long_claim", "long_original"])
def test_language_observer_does_not_downgrade_legal_output_for_static_size(form, monkeypatch):
    from types import SimpleNamespace
    text = "Our customers validated the new product and placed repeat orders during the quarter."
    raw = text * (700 if form == "long_original" else 1)
    prose = text * (80 if form == "long_claim" else 1)
    spans = tuple(SimpleNamespace(span_id=f"s{i}", raw_text=raw)
                  for i in range(97 if form == "many_spans" else 1))
    claims = tuple(SimpleNamespace(text=prose, evidence_ids=(spans[0].span_id,))
                   for _ in range(41 if form == "many_claims" else 1))
    monkeypatch.setattr(language_observer, "_get_identifier", lambda: SimpleNamespace(classify=lambda _: ("en", 1.0)))
    observed = language_observer.observe_summary_language(claims, evidence_spans=spans)
    assert observed.state == "compatible" and observed.prose_claims == len(claims)


def test_historical_projection_label_is_not_a_length_permission_or_execution_support():
    from company_wiki.automation.narrative_worker_factory import _reading_projection_identity
    from company_wiki.automation.narrative_model_runtime import resolve_model_boundary
    from company_wiki.automation.narrative_model import ModelResponseError
    future = "future-projection/" + "x" * 300
    assert _reading_projection_identity({"reading_model_projection": future}) == future
    with pytest.raises(ModelResponseError):
        resolve_model_boundary(future)
