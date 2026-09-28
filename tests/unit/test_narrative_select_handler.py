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
from company_wiki.source_catalog.provider_use_policy import ProviderUsePolicy
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
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def _policy_payload(
    *, permitted_actions: tuple[str, ...], revoked: bool = False
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "provider-use-policy/1",
        "policy_id": "select-handler-policy",
        "rules": [
            {
                "provider_id": "fixture_provider",
                "origin_host": "fixtures.invalid",
                "path_prefix": "/transcripts",
                "content_class": "earnings_call_transcript",
                "rights_evidence_ref": "offline fixture",
                "rights_evidence_sha256": _sha(b"fixture-rights"),
                "reviewer": "unit-test",
                "reviewed_at": "2026-09-01",
                "valid_from": "2026-09-01",
                "valid_until": "2026-09-30",
                "permitted_actions": sorted(permitted_actions),
                "retention_scope": "company_wiki_local",
                "export_scope": "stockwiki_readonly_excerpt",
                "revoked": revoked,
            }
        ],
    }
    payload["policy_sha256"] = _sha(canonical_json(payload).encode("utf-8"))
    return payload


def _policy(
    *,
    permitted_actions: tuple[str, ...] = ("derive_text", "select_evidence"),
    revoked: bool = False,
) -> ProviderUsePolicy:
    return ProviderUsePolicy.from_dict(
        _policy_payload(permitted_actions=permitted_actions, revoked=revoked)
    )


def _payload(
    data: bytes,
    *,
    title: str,
    document_kind: str,
    language: str,
    mime_type: str,
    transcript_policy_sha256: str | None = None,
) -> dict[str, object]:
    digest = _sha(data)
    transcript = transcript_policy_sha256 is not None
    return {
        "schema_version": "source-revision-event/1.0",
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
        "transcript_policy": (
            {
                "provider_id": "fixture_provider",
                "source_url": "https://fixtures.invalid/transcripts/2026/q2.html",
                "content_class": "earnings_call_transcript",
                "expected_provider_policy_sha256": transcript_policy_sha256,
            }
            if transcript
            else None
        ),
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
    policy: ProviderUsePolicy | None = None,
    selector: Callable[..., NarrativeEvidencePackage] | None = None,
) -> tuple[object, int]:
    checkpoints: list[int] = []
    handler = NarrativeSelectHandler(
        reader=reader or FakeReader(payload, data),
        provider_policy_loader=(lambda: policy) if policy is not None else None,
        current_date=lambda: "2026-09-28",
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
    policy = _policy()
    payload = _payload(
        data,
        title="ACME Q2 2026 earnings call",
        document_kind="earnings_call_transcript",
        language="en",
        mime_type=mime_type,
        transcript_policy_sha256=policy.policy_sha256,
    )

    raw, _ = _run(payload, data, policy=policy)
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
    assert result.transcript_action_policy is not None
    assert result.transcript_action_policy.actions == {
        "derive_text",
        "select_evidence",
    }


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
    assert raw.outcome is HandlerOutcome.BLOCKED_HUMAN
    assert raw.error is not None and raw.error.code == "PARSER_INCOMPLETE"
    assert raw.effects == ()


def test_select_handler_transcript_parser_incomplete_cannot_become_skip() -> None:
    data = b"CEO: This omits the required transcript start marker.\n"
    policy = _policy()
    payload = _payload(
        data,
        title="ACME Q2 call",
        document_kind="earnings_call_transcript",
        language="en",
        mime_type="text/plain",
        transcript_policy_sha256=policy.policy_sha256,
    )

    raw, _ = _run(payload, data, policy=policy)
    assert raw.outcome is HandlerOutcome.BLOCKED_HUMAN
    assert raw.error is not None and raw.error.code == "PARSER_INCOMPLETE"
    assert raw.effects == ()


@pytest.mark.parametrize(
    "permitted_actions",
    [("derive_text",), ("select_evidence",)],
)
def test_select_handler_requires_each_transcript_action(
    permitted_actions: tuple[str, ...]
) -> None:
    data = b"Full Conference Call Transcript\nCEO: We launched a new product.\n"
    policy = _policy(permitted_actions=permitted_actions)
    payload = _payload(
        data,
        title="ACME call",
        document_kind="earnings_call_transcript",
        language="en",
        mime_type="text/plain",
        transcript_policy_sha256=policy.policy_sha256,
    )

    raw, _ = _run(payload, data, policy=policy)
    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "POLICY_DENIED"
    assert raw.effects == ()


def test_select_handler_rejects_revoked_transcript_policy() -> None:
    data = b"Full Conference Call Transcript\nCEO: We launched a new product.\n"
    policy = _policy(revoked=True)
    payload = _payload(
        data,
        title="ACME call",
        document_kind="earnings_call_transcript",
        language="en",
        mime_type="text/plain",
        transcript_policy_sha256=policy.policy_sha256,
    )

    raw, _ = _run(payload, data, policy=policy)
    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "POLICY_DENIED"
    assert raw.effects == ()


@pytest.mark.parametrize("drift", ["provider_policy", "source_hash", "read_policy", "metadata"])
def test_select_handler_rejects_source_and_policy_drift(drift: str) -> None:
    data = b"Full Conference Call Transcript\nCEO: We launched a new product.\n"
    policy = _policy()
    expected_policy_sha = policy.policy_sha256
    if drift == "provider_policy":
        expected_policy_sha = _sha(b"old-policy")
    payload = _payload(
        data,
        title="ACME call",
        document_kind="earnings_call_transcript",
        language="en",
        mime_type="text/plain",
        transcript_policy_sha256=expected_policy_sha,
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

    raw, _ = _run(payload, data, reader=reader, policy=policy)
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
