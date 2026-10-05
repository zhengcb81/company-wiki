from __future__ import annotations

from dataclasses import replace
import hashlib
from typing import Callable

import pytest

from company_wiki.automation.execution_context import JobExecutionContext
from company_wiki.automation.models import (
    Attempt,
    Event,
    HandlerOutcome,
    Job,
    JobStatus,
    RiskClass,
    canonical_json,
    make_job_key,
)
from company_wiki.automation.narrative_contracts import (
    NarrativeSelectResult,
    SELECT_RESULT_MAX_BYTES,
    SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.source_catalog.narrative_document import NarrativeEvidencePackage
from company_wiki.source_catalog.narrative_evidence import (
    parse_pdf_bytes,
    select_narrative_evidence,
    verify_pdf_evidence_spans_bytes,
)
from company_wiki.source_catalog.source_reader import (
    ReviewSnapshot,
    SourceRef,
    VerifiedContent,
)
from company_wiki.source_contract import (
    EvidenceCoordinates,
    EvidenceSpan,
    ParseStatus,
    source_id_for_sha256,
)


T0 = "2026-09-28T16:00:00Z"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pdf_bytes(text: str) -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text, fontname="china-s")
    data = document.tobytes()
    document.close()
    return data


def _quarterly_category_pdf_bytes() -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    for text in (
        "报告期内，行业景气度持续回升，带动公司主要产品需求稳定增长。",
        "报告期内，公司生产装置运行平稳，主要产品产销量同比增长。",
        "公司新设立精密零部件事业部，启动高纯材料新产品的工艺开发。",
        "报告期内，境外业务收入同比增长，成为公司重要的增长来源。",
        "本公司保证所披露的信息真实、准确、完整，不存在虚假记载或误导性陈述。",
        "第一节 重要提示 .......... 2",
    ):
        page = document.new_page()
        page.insert_text((72, 72), text, fontname="china-s")
    data = document.tobytes()
    document.close()
    return data


def _payload(
    data: bytes,
    *,
    title: str | None,
    document_kind: str,
    language: str,
    mime_type: str,
) -> dict[str, object]:
    digest = _sha(data)
    transcript = document_kind == "earnings_call_transcript"
    return {
        "schema_version": "source-revision-event/2.0",
        "source_ref": {
            "schema_version": "2.0",
            "document_id": "doc-select",
            "source_id": source_id_for_sha256(digest),
            "content_sha256": digest,
            "byte_size": len(data),
            "mime_type": mime_type,
        },
        "expected_read_policy_sha256": _sha(b"read-policy"),
        "source_metadata": {
            "source_class": "transcript" if transcript else "filing",
            "title": title,
            "document_kind": document_kind,
            "language": language,
        },
    }


def _context(
    payload: dict[str, object], checkpoint: Callable[[], None]
) -> JobExecutionContext:
    parsed = SourceRevisionEventPayload.from_dict(payload)
    event = Event(
        event_id="event-select",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id=parsed.source_ref.document_id,
        input_hash=parsed.input_hash,
        payload_json=canonical_json(payload),
        policy_version="narrative-v1",
        occurred_at=T0,
        observed_at=T0,
    )
    job = Job(
        job_id="job-select",
        job_key=make_job_key(
            "source.narrative_select",
            event.subject_type,
            event.subject_id,
            event.input_hash,
            event.policy_version,
            "1.0.0",
        ),
        job_type="source.narrative_select",
        subject_type=event.subject_type,
        subject_id=event.subject_id,
        input_hash=event.input_hash,
        policy_version=event.policy_version,
        handler_version="1.0.0",
        risk_class=RiskClass.LOW,
        status=JobStatus.RUNNING,
        priority=0,
        not_before=T0,
        max_attempts=3,
        created_from_event_id=event.event_id,
        created_at=T0,
        updated_at=T0,
        last_error_code=None,
        last_error_detail=None,
    )
    attempt = Attempt(
        attempt_id="attempt-select",
        job_id=job.job_id,
        attempt_no=1,
        worker_id="worker-select",
        lease_token="lease-select",
        lease_until="2026-09-28T16:05:00Z",
        started_at=T0,
        heartbeat_at=T0,
        finished_at=None,
        outcome=None,
        result_json=None,
        error_code=None,
        error_detail=None,
        runtime_generation=2,
    )
    return JobExecutionContext(
        job,
        attempt,
        event,
        payload,
        {},
        parsed,
        checkpoint,
    )


class FakeReader:
    def __init__(self, payload: dict[str, object], data: bytes):
        parsed = SourceRevisionEventPayload.from_dict(payload)
        ref = parsed.source_ref
        review = ReviewSnapshot(
            "not_detected",
            ref.content_sha256,
            _sha(b"review-evidence"),
            _sha(b"review-policy"),
            T0,
        )
        self.opened = VerifiedContent(
            document_id=ref.document_id,
            source_id=ref.source_id,
            content_sha256=ref.content_sha256,
            data=data,
            byte_size=len(data),
            read_at=T0,
            policy_sha256=_sha(b"catalog-policy"),
            source_read_policy_sha256=parsed.expected_read_policy_sha256,
            review=review,
        )
        self.metadata: dict[str, object] = {
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "content_sha256": ref.content_sha256,
            "byte_size": ref.byte_size,
            "mime_type": ref.mime_type,
            "title": parsed.source_metadata.title,
            "document_kind": parsed.source_metadata.document_kind,
            "language": parsed.source_metadata.language,
        }

    def open_version(
        self,
        ref: SourceRef,
        *,
        purpose: str,
        expected_read_policy_sha256: str | None = None,
    ) -> VerifiedContent:
        assert purpose == "narrative_derivation"
        assert expected_read_policy_sha256 is not None
        return self.opened

    def describe_version(self, ref: SourceRef) -> dict[str, object]:
        return dict(self.metadata)


def _run(
    payload: dict[str, object],
    data: bytes,
    *,
    reader: FakeReader | None = None,
    selector: Callable[..., NarrativeEvidencePackage] | None = None,
) -> tuple[object, int]:
    checkpoints: list[int] = []
    handler = NarrativeSelectHandler(
        reader=reader or FakeReader(payload, data),
        selector=selector,
    )
    result = handler(_context(payload, lambda: checkpoints.append(1)))
    return result, len(checkpoints)


@pytest.mark.parametrize(
    ("title", "document_kind"),
    [
        ("Acme 2025 Annual Report.pdf", "annual_report"),
        ("首次公开发行股票并上市招股说明书.pdf", "prospectus"),
        ("投资者关系活动记录表.pdf", "investor_relations"),
    ],
)
def test_select_handler_reads_pdf_bytes_for_high_value_document_types(
    title: str, document_kind: str
) -> None:
    data = _pdf_bytes(
        "Company launched a new product and expanded overseas capacity for new customers."
    )
    payload = _payload(
        data,
        title=title,
        document_kind=document_kind,
        language="en",
        mime_type="application/pdf",
    )

    raw, checkpoint_count = _run(payload, data)
    assert raw.outcome is HandlerOutcome.SUCCEEDED
    assert raw.effects == ()
    result = NarrativeSelectResult.from_dict(raw.result)
    assert result.evidence_spans
    assert result.source_ref.content_sha256 == _sha(data)
    assert checkpoint_count >= 4


@pytest.mark.parametrize("document_kind", ["quarterly_report", "investor_relations"])
def test_select_handler_recovers_titleless_quarterly_business_narrative_with_replay(
    document_kind: str,
) -> None:
    data = _quarterly_category_pdf_bytes()
    payload = _payload(
        data,
        title=None,
        document_kind=document_kind,
        language="zh",
        mime_type="application/pdf",
    )

    raw, _ = _run(payload, data)

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    result = NarrativeSelectResult.from_dict(raw.result)
    assert result.selection.status == "partial"
    assert result.selection.coverage_complete is False
    selected_text = [span.raw_text for span in result.evidence_spans]
    expected = (
        "行业景气度持续回升",
        "生产装置运行平稳",
        "新设立精密零部件事业部",
        "境外业务收入同比增长",
    )
    for fragment in expected:
        assert any(fragment in text for text in selected_text), fragment
    assert not any("保证所披露的信息" in text for text in selected_text)
    assert not any("重要提示" in text for text in selected_text)
    assert all(span.coordinates.page_number is not None for span in result.evidence_spans)
    assert all(span.source_id == result.source_ref.source_id for span in result.evidence_spans)
    verified, failed = verify_pdf_evidence_spans_bytes(
        data,
        source_id=result.source_ref.source_id,
        source_sha256=result.source_ref.content_sha256,
        evidence_spans=result.evidence_spans,
    )
    assert failed == ()
    assert verified == tuple(span.span_id for span in result.evidence_spans)


def test_titleless_signal_free_quarterly_remains_reviewable() -> None:
    data = _pdf_bytes("本报告仅说明财务数据列报规则，未描述具体业务动态。")
    digest = _sha(data)
    source_id = source_id_for_sha256(digest)
    parsed = parse_pdf_bytes(
        data,
        source_id=source_id,
        source_sha256=digest,
        language="zh",
        full_table_scan=True,
    )

    package = select_narrative_evidence(
        parsed,
        title="",
        existing_kind="quarterly_report",
    )

    assert package.status == "needs_review"
    assert package.coverage_complete is True
    assert package.evidence_spans == ()


def test_select_handler_does_not_require_prompt_review_receipt() -> None:
    data = _pdf_bytes("Company expanded its new business overseas.")
    payload = _payload(
        data,
        title="ACME annual report.pdf",
        document_kind="annual_report",
        language="en",
        mime_type="application/pdf",
    )
    reader = FakeReader(payload, data)
    reader.opened = replace(reader.opened, review=None)

    raw, _ = _run(payload, data, reader=reader)

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    assert NarrativeSelectResult.from_dict(raw.result).prompt_review.status == "not_reviewed"


@pytest.mark.parametrize("mime_type", ["text/plain", "text/html"])
def test_select_handler_transcript_keeps_only_selected_original_byte_bindings(
    mime_type: str,
) -> None:
    text = (
        "Full Conference Call Transcript\n"
        "CEO: We launched a new product and expanded overseas capacity.\n"
        "Questions & Answers\n"
        "Analyst: Is the new product ready for commercial launch?\n"
        "CEO: Customer validation continues and commercial launch is planned.\n"
    )
    data = (
        text.encode("utf-8")
        if mime_type == "text/plain"
        else "".join(f"<p>{line}</p>" for line in text.splitlines()).encode("utf-8")
    )
    payload = _payload(
        data,
        title="ACME Q2 2026 earnings call",
        document_kind="earnings_call_transcript",
        language="en",
        mime_type=mime_type,
    )

    raw, _ = _run(payload, data)
    assert raw.outcome is HandlerOutcome.SUCCEEDED
    result = NarrativeSelectResult.from_dict(raw.result)
    assert result.evidence_spans
    assert {item.evidence_id for item in result.transcript_byte_bindings} == {
        span.span_id for span in result.evidence_spans
    }
    assert result.transcript_lineage is not None
    assert "text_utf8" not in result.transcript_lineage.to_dict()
    assert all(item.material_line_start > 1 for item in result.transcript_byte_bindings)
    assert "summary_input" not in result.to_dict()


def test_select_handler_complete_low_value_pdf_emits_small_skip() -> None:
    data = _pdf_bytes("This policy describes meeting administration and filing procedures.")
    payload = _payload(
        data,
        title="投资者关系管理办法（2025年8月）.pdf",
        document_kind="ir_policy",
        language="zh",
        mime_type="application/pdf",
    )

    raw, _ = _run(payload, data)
    assert raw.outcome is HandlerOutcome.SUCCEEDED
    result = NarrativeSelectResult.from_dict(raw.result)
    assert result.selection.status == "skipped_no_narrative"
    assert result.selection.coverage_complete is True
    assert result.evidence_spans == ()
    assert result.encoded_size < 8 * 1024


def test_select_handler_invalid_verified_pdf_blocks_without_effect() -> None:
    data = b"%PDF-1.7\nverified hash but structurally invalid\n"
    payload = _payload(
        data,
        title="Annual Report.pdf",
        document_kind="annual_report",
        language="en",
        mime_type="application/pdf",
    )

    raw, _ = _run(payload, data)
    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "PARSER_INCOMPLETE"
    assert raw.effects == ()


def test_select_handler_transcript_parser_incomplete_cannot_become_skip() -> None:
    data = b"CEO: This omits the required transcript start marker.\n"
    payload = _payload(
        data,
        title="ACME Q2 call",
        document_kind="earnings_call_transcript",
        language="en",
        mime_type="text/plain",
    )

    raw, _ = _run(payload, data)
    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "PARSER_INCOMPLETE"
    assert raw.effects == ()


def test_select_handler_does_not_require_provider_policy_for_transcript() -> None:
    data = b"Full Conference Call Transcript\nCEO: We launched a new product.\n"
    payload = _payload(
        data,
        title="ACME call",
        document_kind="earnings_call_transcript",
        language="en",
        mime_type="text/plain",
    )

    raw, _ = _run(payload, data)
    assert raw.outcome is HandlerOutcome.SUCCEEDED
    assert raw.error is None
    assert NarrativeSelectResult.from_dict(raw.result).evidence_spans


@pytest.mark.parametrize("drift", ["source_hash", "read_policy", "metadata"])
def test_select_handler_rejects_source_identity_and_metadata_drift(drift: str) -> None:
    data = b"Full Conference Call Transcript\nCEO: We launched a new product.\n"
    payload = _payload(
        data,
        title="ACME call",
        document_kind="earnings_call_transcript",
        language="en",
        mime_type="text/plain",
    )
    reader = FakeReader(payload, data)
    if drift == "source_hash":
        reader.opened = replace(reader.opened, content_sha256=_sha(b"wrong"))
    elif drift == "read_policy":
        reader.opened = replace(
            reader.opened, source_read_policy_sha256=_sha(b"new-read-policy")
        )
    elif drift == "metadata":
        reader.metadata["language"] = "mixed"

    raw, _ = _run(payload, data, reader=reader)
    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None
    assert raw.error.code in {
        "POLICY_DENIED",
        "SOURCE_HASH_MISMATCH",
        "INPUT_SCHEMA_INVALID",
    }
    assert raw.effects == ()


def _oversized_package(parsed, *, path_leak: bool) -> NarrativeEvidencePackage:
    text = (
        "Z:" + chr(92) + "private" + chr(92) + "source.pdf"
        if path_leak
        else "海" * (SELECT_RESULT_MAX_BYTES // 2)
    )
    span = EvidenceSpan.create(
        source_id=parsed.source_id,
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text=text,
        structured_value={
            "language": parsed.language,
            "source_role": "company_filing",
            "selection_reasons": ["business_progress"],
        },
        parser_name="select-test",
        parser_version="1.0.0",
        parse_status=ParseStatus.PARSED,
        quality_flags=(),
    )
    return NarrativeEvidencePackage(
        source_id=parsed.source_id,
        source_sha256=parsed.source_sha256,
        document_kind="annual_report",
        status="selected",
        evidence_spans=(span,),
        selection_limit=1,
        candidate_count=1,
        dropped_financial_count=0,
        source_units=1,
        omitted_candidate_count=0,
        coverage_complete=True,
    )


@pytest.mark.parametrize(
    ("path_leak", "error_code"),
    [(False, "RESULT_TOO_LARGE"), (True, "INPUT_SCHEMA_INVALID")],
)
def test_select_handler_cap_and_path_leak_fail_with_zero_effect(
    path_leak: bool, error_code: str
) -> None:
    data = _pdf_bytes("Company launched a new product.")
    payload = _payload(
        data,
        title="Annual Report.pdf",
        document_kind="annual_report",
        language="en",
        mime_type="application/pdf",
    )

    def selector(parsed, **_kwargs):
        return _oversized_package(parsed, path_leak=path_leak)

    raw, _ = _run(payload, data, selector=selector)
    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == error_code
    assert raw.effects == ()
