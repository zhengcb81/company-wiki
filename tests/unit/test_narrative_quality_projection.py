"""G2-11 derives quality from evidence and claims, never redundant model labels."""

from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_contracts import (
    NarrativeSelectResult, SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_model import (
    NARRATIVE_PROMPT_VERSION, NarrativeModelRequest, NarrativeModelResponse,
)
from company_wiki.automation.narrative_summarize import (
    NarrativeSummarizeHandler, _SummaryFailure,
)
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_PARSER_NAME, NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_NAME, NARRATIVE_SELECTOR_VERSION,
    parse_pdf_bytes, select_narrative_evidence,
)
from company_wiki.source_contract import EvidenceSpan, source_id_for_sha256
from support.narrative_model_request_fixture import selection


def _claim(**overrides):
    return {"claim_id": "valid", "text": "公司新产品已完成海外客户认证。",
            "evidence_ids": ["e1"], "claim_type": "company_statement",
            "modality": "actual", **overrides}


def _complete(selected, claim, **labels):
    payload = {"draft": {"source_id": selected.source_ref.source_id,
                         "source_sha256": selected.source_ref.content_sha256,
                         "language": selected.source_metadata.language,
                         "claims": [claim], **labels}}
    response = NarrativeModelResponse("offline-g2", "offline-g2", NARRATIVE_PROMPT_VERSION,
                                      json.dumps(payload, ensure_ascii=False).encode())
    return NarrativeSummarizeHandler._completed_result(selected, selected.prompt_review, response)


@pytest.mark.parametrize("flags", [(), ("locator_unstable",)])
def test_valid_content_and_quality_do_not_depend_on_redundant_model_labels(flags):
    selected = selection(flags=flags)
    before = selected.to_dict()
    drafts = []
    for claim_review in (False, True):
        for draft_status in ("draft", "needs_review"):
            result = _complete(selected, _claim(needs_review=claim_review), status=draft_status)
            result.validate_against(selected)
            assert result.draft is not None
            drafts.append(result.to_dict()["draft"])
    assert all(draft == drafts[0] for draft in drafts)
    assert drafts[0]["claims"][0]["text"] == _claim()["text"]
    assert drafts[0]["claims"][0]["evidence_ids"] == [selected.evidence_spans[0].span_id]
    assert drafts[0]["claims"][0]["needs_review"] is bool(flags)
    assert drafts[0]["status"] == ("needs_review" if flags else "draft")
    assert selected.to_dict() == before


def test_model_may_omit_program_owned_quality_labels():
    selected = selection()
    result = _complete(selected, _claim())
    result.validate_against(selected)
    assert result.draft is not None and result.draft.status == "draft"
    assert result.draft.claims[0].needs_review is False
    request = NarrativeModelRequest.from_selection(selected)
    schema = json.loads(request.data_json)["response_schema"]["properties"]["draft"]
    assert "status" not in schema["required"]
    assert "needs_review" not in schema["properties"]["claims"]["items"]["required"]
    assert "requires needs_review=true" not in request.instruction


def test_exported_evidence_quality_is_visible_even_when_not_cited_by_retained_claim():
    selected = selection(2)
    selected = replace(selected, evidence_spans=(
        selected.evidence_spans[0],
        replace(selected.evidence_spans[1], quality_flags=("locator_unstable",)),
    ))
    result = _complete(selected, _claim())
    assert result.draft is not None and result.draft.status == "needs_review"
    claim = result.draft.claims[0]
    assert claim.needs_review is False
    assert claim.evidence_ids == (selected.evidence_spans[0].span_id,)


@pytest.mark.parametrize("claim_type,modality", [("uncertain", "actual"),
                                                ("company_statement", "uncertain")])
def test_model_uncertainty_remains_a_content_diagnostic(claim_type, modality):
    selected = selection()
    result = _complete(selected, _claim(claim_type=claim_type, modality=modality,
                                       needs_review=False), status="draft")
    assert result.draft is not None and result.draft.status == "needs_review"
    claim = result.draft.claims[0]
    assert claim.claim_type == claim_type and claim.modality == modality
    assert claim.text == _claim()["text"] and claim.needs_review is True


@pytest.mark.parametrize("overrides,role", [
    ({"evidence_ids": ["e404"]}, "company_filing"),
    ({"claim_type": "company_statement", "modality": "actual"}, "analyst"),
    ({"claim_type": "analyst_question", "modality": "actual"}, "analyst"),
])
def test_quality_labels_cannot_rescue_unknown_citations_or_false_speaker_role(overrides, role):
    selected = selection(role=role)
    with pytest.raises(_SummaryFailure):
        _complete(selected, _claim(needs_review=True, **overrides), status="needs_review")


def _pdf_selection():
    fitz = pytest.importorskip("fitz")
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Company launched a new product for overseas customers.")
        data = document.tobytes()
    digest = hashlib.sha256(data).hexdigest()
    source_id = source_id_for_sha256(digest)
    parsed = parse_pdf_bytes(data, source_id=source_id, source_sha256=digest, language="en")
    package = select_narrative_evidence(parsed, title="ACME annual report", existing_kind="annual_report")
    assert package.evidence_spans
    base = selection().to_dict()
    base["source_ref"].update(source_id=source_id, content_sha256=digest, byte_size=len(data))
    base["source_metadata"].update(title="ACME annual report", language="en", document_kind="annual_report")
    base["parser"] = {"name": NARRATIVE_PARSER_NAME, "version": NARRATIVE_PARSER_VERSION}
    base["selector"] = {"name": NARRATIVE_SELECTOR_NAME, "version": NARRATIVE_SELECTOR_VERSION}
    base["evidence_spans"] = [span.to_dict() for span in package.evidence_spans]
    base["selection"].update(status=package.status, selected_count=len(package.evidence_spans),
                             source_units=package.source_units, candidate_count=package.candidate_count,
                             omitted_candidate_count=package.omitted_candidate_count,
                             pages_total=parsed.page_count, pages_read=parsed.pages_read)
    return data, NarrativeSelectResult.from_dict(base)


@pytest.mark.parametrize("bad_locator", [False, True])
def test_review_diagnostic_never_bypasses_actual_pdf_replay(bad_locator):
    data, selected = _pdf_selection()
    span = selected.evidence_spans[0]
    if bad_locator:
        span = EvidenceSpan.create(
            source_id=span.source_id, coordinates=replace(span.coordinates, page_number=999),
            raw_text=span.raw_text, structured_value=span.structured_value,
            parser_name=span.parser_name, parser_version=span.parser_version,
            parse_status=span.parse_status, quality_flags=span.quality_flags,
        )
    span = replace(span, quality_flags=("locator_unstable",))
    selected = replace(selected, evidence_spans=(span,))
    result = _complete(selected, _claim(needs_review=False), status="draft")
    assert result.draft is not None and result.draft.status == "needs_review"
    payload = SourceRevisionEventPayload.from_dict({
        "schema_version": "source-revision-event/2.0",
        "source_ref": selected.source_ref.to_dict(),
        "expected_read_policy_sha256": selected.expected_read_policy_sha256,
        "source_metadata": selected.source_metadata.to_dict(),
    })
    metadata = {**selected.source_metadata.to_dict(), **selected.source_ref.to_dict()}
    opened = SimpleNamespace(
        document_id=selected.source_ref.document_id, source_id=selected.source_ref.source_id,
        content_sha256=selected.source_ref.content_sha256, byte_size=len(data), data=data,
        source_read_policy_sha256=selected.expected_read_policy_sha256,
    )
    reader = SimpleNamespace(open_version=lambda *args, **kwargs: opened,
                             describe_version=lambda *args: metadata)
    def dependency(value):
        return SimpleNamespace(outcome=HandlerOutcome.SUCCEEDED,
                               error=None, effects=(), result=value)
    context = SimpleNamespace(
        checkpoint=lambda: None, job=SimpleNamespace(job_type="source.narrative_verify", job_id="job-g2"),
        source_revision=payload, event=SimpleNamespace(observed_at="2026-10-07T00:00:00Z"),
        dependency_results={"source.narrative_select": dependency(selected.to_dict()),
                            "source.narrative_summarize": dependency(result.to_dict())},
    )
    verified = NarrativeVerifyHandler(reader=reader)(context)
    if bad_locator:
        assert verified.outcome is HandlerOutcome.TERMINAL_FAILURE
        assert verified.error is not None and verified.error.code == "LOCATOR_REPLAY_FAILED"
        assert verified.effects == () and verified.result == {}
    else:
        assert verified.outcome is HandlerOutcome.SUCCEEDED
        assert len(verified.effects) == 1 and verified.result["quality_status"] == "needs_review"
