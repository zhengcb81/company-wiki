from __future__ import annotations

import hashlib

import pytest

from company_wiki.automation.models import canonical_json_hash
from company_wiki.automation.narrative_contracts import (
    BUNDLE_MAX_BYTES,
    SELECT_RESULT_MAX_BYTES,
    SKIP_BUNDLE_MAX_BYTES,
    SUMMARY_RESULT_MAX_BYTES,
    ContractSizeError,
    NarrativeBundle,
    NarrativeContractError,
    NarrativeSelectResult,
    NarrativeSummaryResult,
    PhysicalPathLeakError,
    SourceRevisionEventPayload,
    assert_no_physical_paths,
)
from company_wiki.source_contract import (
    EvidenceCoordinates,
    EvidenceSpan,
    ParseStatus,
    source_id_for_sha256,
)


def _sha(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _windows_path(*parts: str) -> str:
    separator = chr(92)
    return "Z" + chr(58) + separator + separator.join(parts)


def _unc_path(*parts: str) -> str:
    separator = chr(92)
    return separator * 2 + separator.join(parts)


def _source_ref(*, mime_type: str = "application/pdf") -> dict:
    digest = _sha("raw-source")
    return {
        "schema_version": "2.0",
        "document_id": "doc-001",
        "source_id": source_id_for_sha256(digest),
        "content_sha256": digest,
        "byte_size": 1234,
        "mime_type": mime_type,
    }


def _metadata(*, source_class: str = "filing", language: str = "zh") -> dict:
    return {
        "source_class": source_class,
        "title": None,
        "document_kind": "annual_report" if source_class == "filing" else "earnings_call_transcript",
        "language": language,
    }


def _event_payload(*, transcript: bool = False) -> dict:
    return {
        "schema_version": "source-revision-event/2.0",
        "source_ref": _source_ref(mime_type="text/plain" if transcript else "application/pdf"),
        "expected_read_policy_sha256": _sha("read-policy"),
        "source_metadata": _metadata(
            source_class="transcript" if transcript else "filing",
            language="en" if transcript else "zh",
        ),
    }


def _span(*, text: str = "公司正在推进海外新产线，并已取得首批客户订单。") -> EvidenceSpan:
    ref = _source_ref()
    return EvidenceSpan.create(
        source_id=ref["source_id"],
        coordinates=EvidenceCoordinates(page_number=8, paragraph_index=2),
        raw_text=text,
        structured_value={
            "language": "zh",
            "source_role": "company_filing",
            "selection_reasons": ["business_progress"],
        },
        parser_name="narrative-pdf",
        parser_version="1.0.0",
        parse_status=ParseStatus.PARSED,
        quality_flags=(),
    )


def _review() -> dict:
    return {
        "status": "not_detected",
        "source_sha256": _source_ref()["content_sha256"],
        "evidence_sha256": _sha("review-evidence"),
        "policy_hash": _sha("review-policy"),
        "reviewed_at": "2026-09-28T09:00:00Z",
    }


def _selection(*, status: str = "selected", evidence: list[dict] | None = None) -> dict:
    spans = [_span().to_dict()] if evidence is None else evidence
    selected_count = len(spans)
    return {
        "schema_version": "narrative-select-result/2.0",
        "source_ref": _source_ref(),
        "expected_read_policy_sha256": _sha("read-policy"),
        "source_metadata": _metadata(),
        "parser": {"name": "narrative-pdf", "version": "1.0.0"},
        "selector": {"name": "narrative-selector", "version": "1.0.0"},
        "selection": {
            "status": status,
            "coverage_complete": True,
            "source_units": 14,
            "candidate_count": selected_count,
            "selected_count": selected_count,
            "omitted_candidate_count": 0,
            "dropped_financial_count": 3,
            "pages_total": 10,
            "pages_read": 10,
            "lines_total": 0,
            "tables_total": 2,
            "tables_scanned": 2,
        },
        "evidence_spans": spans,
        "prompt_review": _review(),
        "transcript_lineage": None,
        "transcript_byte_bindings": [],
        "summary_scope": "selected_evidence_only",
    }


def _draft(*, evidence_id: str | None = None, language: str = "zh", text: str = "海外新产线已进入客户订单交付阶段。") -> dict:
    return {
        "source_id": _source_ref()["source_id"],
        "source_sha256": _source_ref()["content_sha256"],
        "language": language,
        "claims": [
            {
                "claim_id": "claim-001",
                "text": text,
                "evidence_ids": [evidence_id or _span().span_id],
                "claim_type": "company_statement",
                "modality": "actual",
                "needs_review": False,
            }
        ],
        "status": "draft",
    }


def _summary(*, status: str = "completed", draft: dict | None = None) -> dict:
    completed = status == "completed"
    return {
        "schema_version": "narrative-summary-result/2.0",
        "source_ref": _source_ref(),
        "language": "zh",
        "translate": False,
        "status": status,
        "draft": (draft or _draft()) if completed else None,
        "model": (
            {
                "adapter_id": "replay",
                "model_id": "fixture-v1",
                "prompt_version": "1.0.0",
                "response_sha256": _sha("model-response"),
            }
            if completed
            else None
        ),
        "prompt_review": _review(),
    }


def _bundle(*, quality_status: str = "verified", evidence: list[dict] | None = None) -> dict:
    spans = [_span().to_dict()] if evidence is None else evidence
    summary = _summary() if quality_status != "skipped_no_narrative" else _summary(status="summary_not_needed")
    return {
        "schema_version": "narrative-bundle/2.0",
        "source_ref": _source_ref(),
        "expected_read_policy_sha256": _sha("read-policy"),
        "source_metadata": _metadata(),
        "quality_status": quality_status,
        "selection": _selection(status="selected" if spans else "skipped_no_narrative", evidence=spans)["selection"],
        "evidence_spans": spans,
        "summary": {
            "status": summary["status"],
            "translate": summary["translate"],
            "draft": summary["draft"],
            "model": summary["model"],
        },
        "prompt_review": _review(),
        "transcript_lineage": None,
        "transcript_byte_bindings": [],
        "versions": {
            "parser": "1.0.0",
            "selector": "1.0.0",
            "material": None,
            "model": "fixture-v1" if spans else None,
            "prompt": "1.0.0" if spans else None,
            "bundle_producer": "1.0.0",
        },
        "replay": {"required": True, "locator_count": len(spans)},
    }


def test_source_revision_event_is_exact_and_hashes_canonical_payload() -> None:
    raw = _event_payload()
    payload = SourceRevisionEventPayload.from_dict(raw)

    assert payload.to_dict() == raw
    assert payload.input_hash == canonical_json_hash(raw)
    with pytest.raises(NarrativeContractError, match="unknown fields"):
        SourceRevisionEventPayload.from_dict({**raw, "unexpected": "must fail"})
    missing = dict(raw)
    missing.pop("source_ref")
    with pytest.raises(NarrativeContractError, match="missing fields"):
        SourceRevisionEventPayload.from_dict(missing)


def test_source_revision_event_has_no_provider_policy_field() -> None:
    filing = _event_payload()
    transcript = _event_payload(transcript=True)
    parsed = SourceRevisionEventPayload.from_dict(transcript)
    assert parsed.source_metadata.source_class == "transcript"
    with pytest.raises(NarrativeContractError, match="unknown fields"):
        SourceRevisionEventPayload.from_dict({**transcript, "transcript_policy": {}})
    bad_metadata = {**filing["source_metadata"], "language": "unknown"}
    with pytest.raises(NarrativeContractError, match="language"):
        SourceRevisionEventPayload.from_dict({**filing, "source_metadata": bad_metadata})


def test_physical_paths_are_rejected_but_evidence_locators_are_allowed() -> None:
    assert_no_physical_paths(
        {"locator": "page:12/paragraph:3", "byte_locator": "byte:100:220", "url": "https://example.test/a"}
    )
    for value in (
        {"file_path": "relative/report.pdf"},
        {"nested": {"value": _windows_path("Users", "person", "report.pdf")}},
        {"nested": ["file:///tmp/report.pdf"]},
        {"nested": _unc_path("server", "share", "report.pdf")},
    ):
        with pytest.raises(PhysicalPathLeakError):
            assert_no_physical_paths(value)


def test_select_result_roundtrips_without_duplicate_summary_or_full_line_map() -> None:
    raw = _selection()
    result = NarrativeSelectResult.from_dict(raw)

    assert result.to_dict() == raw
    assert result.encoded_size <= SELECT_RESULT_MAX_BYTES
    assert "summary_input" not in result.to_dict()
    with pytest.raises(NarrativeContractError, match="unknown fields"):
        NarrativeSelectResult.from_dict({**raw, "summary_input": {"text": "duplicate"}})


def test_select_result_rejects_incomplete_skip_and_unknown_transcript_binding() -> None:
    skipped = _selection(status="skipped_no_narrative", evidence=[])
    incomplete = {**skipped, "selection": {**skipped["selection"], "coverage_complete": False}}
    with pytest.raises(NarrativeContractError, match="complete coverage"):
        NarrativeSelectResult.from_dict(incomplete)

    transcript = _selection()
    transcript["source_ref"] = _source_ref(mime_type="text/plain")
    transcript["source_metadata"] = _metadata(source_class="transcript", language="en")
    transcript["transcript_lineage"] = {
        "schema_version": "transcript-material/2",
        "original_source_id": transcript["source_ref"]["source_id"],
        "original_sha256": transcript["source_ref"]["content_sha256"],
        "original_mime_type": "text/plain",
        "original_byte_size": 1234,
        "text_sha256": _sha("derived-text"),
        "text_byte_size": 640,
        "extractor_version": "transcript-original-text/1.0.0",
        "line_count": 20,
    }
    transcript["transcript_byte_bindings"] = [
        {
            "evidence_id": "urn:company-wiki:evidence:sha256:" + _sha("unknown"),
            "material_line_start": 2,
            "material_line_end": 3,
            "source_byte_ranges": [{"start": 10, "end": 30}],
        }
    ]
    with pytest.raises(NarrativeContractError, match="selected evidence"):
        NarrativeSelectResult.from_dict(transcript)


def test_select_result_enforces_encoded_byte_cap() -> None:
    oversized = _span(text="海" * (SELECT_RESULT_MAX_BYTES // 2)).to_dict()
    with pytest.raises(ContractSizeError, match="select"):
        NarrativeSelectResult.from_dict(_selection(evidence=[oversized]))


def test_summary_result_validates_language_citations_and_translate_flag() -> None:
    selected = NarrativeSelectResult.from_dict(_selection())
    result = NarrativeSummaryResult.from_dict(_summary())
    result.validate_against(selected)
    assert result.encoded_size <= SUMMARY_RESULT_MAX_BYTES

    bad_language = _summary(draft=_draft(language="en"))
    with pytest.raises(NarrativeContractError, match="language"):
        NarrativeSummaryResult.from_dict(bad_language).validate_against(selected)

    unknown = _summary(draft=_draft(evidence_id="urn:company-wiki:evidence:sha256:" + _sha("absent")))
    with pytest.raises(NarrativeContractError, match="evidence"):
        NarrativeSummaryResult.from_dict(unknown).validate_against(selected)

    with pytest.raises(NarrativeContractError, match="translate"):
        NarrativeSummaryResult.from_dict({**_summary(), "translate": True})


@pytest.mark.parametrize(
    ("field", "invalid", "message"),
    [
        ("claim_type", "investment_conclusion", "claim type"),
        ("modality", "guaranteed", "modality"),
        ("status", "accepted", "draft status"),
    ],
)
def test_summary_result_rejects_values_outside_literal_domains(
    field: str, invalid: str, message: str
) -> None:
    draft = _draft()
    if field == "status":
        draft[field] = invalid
    else:
        draft["claims"][0][field] = invalid

    with pytest.raises(NarrativeContractError, match=message):
        NarrativeSummaryResult.from_dict(_summary(draft=draft))


def test_summary_not_needed_requires_skip_and_no_model_payload() -> None:
    skipped = NarrativeSelectResult.from_dict(_selection(status="skipped_no_narrative", evidence=[]))
    summary = NarrativeSummaryResult.from_dict(_summary(status="summary_not_needed"))
    summary.validate_against(skipped)

    with pytest.raises(NarrativeContractError, match="model"):
        NarrativeSummaryResult.from_dict(
            {**_summary(status="summary_not_needed"), "model": _summary()["model"]}
        )
    with pytest.raises(NarrativeContractError, match="selection"):
        summary.validate_against(NarrativeSelectResult.from_dict(_selection()))


def test_summary_result_enforces_encoded_byte_cap() -> None:
    oversized = _summary(draft=_draft(text="A" * SUMMARY_RESULT_MAX_BYTES))
    with pytest.raises(ContractSizeError, match="summary"):
        NarrativeSummaryResult.from_dict(oversized)


def test_bundle_roundtrip_matches_dependencies_and_has_no_paths() -> None:
    selected = NarrativeSelectResult.from_dict(_selection())
    summary = NarrativeSummaryResult.from_dict(_summary())
    bundle = NarrativeBundle.from_dict(_bundle())

    bundle.validate_against(selected, summary)
    assert bundle.to_dict() == _bundle()
    assert bundle.encoded_size <= BUNDLE_MAX_BYTES

    leaked_span = _span().to_dict()
    leaked_span["structured_value"]["local_path"] = _windows_path("raw", "report.pdf")
    with pytest.raises(PhysicalPathLeakError):
        NarrativeBundle.from_dict(_bundle(evidence=[leaked_span]))


def test_skip_bundle_has_stricter_cap_and_no_evidence_or_model() -> None:
    selected = NarrativeSelectResult.from_dict(_selection(status="skipped_no_narrative", evidence=[]))
    summary = NarrativeSummaryResult.from_dict(_summary(status="summary_not_needed"))
    bundle = NarrativeBundle.from_dict(_bundle(quality_status="skipped_no_narrative", evidence=[]))

    bundle.validate_against(selected, summary)
    assert bundle.encoded_size <= SKIP_BUNDLE_MAX_BYTES
    assert bundle.to_dict()["evidence_spans"] == []
    assert bundle.to_dict()["summary"]["model"] is None


def test_bundle_enforces_full_byte_cap() -> None:
    oversized = _span(text="A" * BUNDLE_MAX_BYTES).to_dict()
    with pytest.raises(ContractSizeError, match="bundle"):
        NarrativeBundle.from_dict(_bundle(evidence=[oversized]))
