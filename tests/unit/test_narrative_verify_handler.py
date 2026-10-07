from __future__ import annotations

from dataclasses import replace
import hashlib
from typing import Any, Callable, Sequence

import pytest

from company_wiki.automation.execution_context import JobExecutionContext
from company_wiki.automation.models import (
    Attempt,
    EffectStatus,
    Event,
    HandlerMetrics,
    HandlerOutcome,
    HandlerResult,
    Job,
    JobStatus,
    RiskClass,
    canonical_json,
    canonical_json_hash,
    make_job_key,
)
from company_wiki.automation.narrative_contracts import (
    BUNDLE_MAX_BYTES,
    SKIP_BUNDLE_MAX_BYTES,
    NarrativeBundle,
    NarrativeSelectResult,
    NarrativeSummaryResult,
    PromptReviewValue,
    SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_model import NARRATIVE_PROMPT_VERSION
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_PARSER_NAME,
    NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_NAME,
    NARRATIVE_SELECTOR_VERSION,
    parse_pdf_bytes,
    parse_transcript_text,
    select_narrative_evidence,
)
from company_wiki.source_catalog.source_reader import (
    ReviewSnapshot,
    SourceReadError,
    SourceRef,
    VerifiedContent,
)
from company_wiki.source_catalog.transcript_text_extract import (
    TranscriptMaterial,
    extract_transcript_material,
)
from company_wiki.source_contract import EvidenceSpan, source_id_for_sha256


T0 = "2026-09-28T20:00:00Z"


def _sha(value: str | bytes) -> str:
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _pdf_bytes(text: str) -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def _review(source_sha: str) -> dict[str, object]:
    return {
        "status": "not_detected",
        "source_sha256": source_sha,
        "evidence_sha256": _sha("review-evidence"),
        "policy_hash": _sha("review-policy"),
        "reviewed_at": T0,
    }


def _selection_metrics(parsed, package) -> dict[str, object]:
    return {
        "status": package.status,
        "coverage_complete": package.coverage_complete,
        "source_units": package.source_units,
        "candidate_count": package.candidate_count,
        "selected_count": len(package.evidence_spans),
        "omitted_candidate_count": package.omitted_candidate_count,
        "dropped_financial_count": package.dropped_financial_count,
        "pages_total": parsed.page_count,
        "pages_read": parsed.pages_read,
        "lines_total": parsed.line_count,
        "tables_total": len(parsed.table_scan_pages) + len(parsed.deferred_table_pages),
        "tables_scanned": len(parsed.table_scan_pages),
    }


def _bindings(
    material: TranscriptMaterial,
    spans: Sequence[EvidenceSpan],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for span in spans:
        start = span.structured_value["line_start"]
        end = span.structured_value["line_end"]
        lines = [line for line in material.lines if start <= line.line_number <= end]
        output.append(
            {
                "evidence_id": span.span_id,
                "material_line_start": start,
                "material_line_end": end,
                "source_byte_ranges": [
                    {"start": line.source_byte_start, "end": line.source_byte_end}
                    for line in lines
                ],
            }
        )
    return output


def _selected(
    *,
    transcript: bool = False,
    skipped: bool = False,
) -> tuple[bytes, NarrativeSelectResult]:
    if transcript:
        data = (
            b"Full Conference Call Transcript\n"
            b"CEO: We launched a new product and expanded overseas capacity.\n"
            b"Questions & Answers\n"
            b"Analyst: Is commercial launch on schedule?\n"
        )
    elif skipped:
        data = _pdf_bytes("This policy describes meeting administration procedures.")
    else:
        data = _pdf_bytes(
            "Company launched a new product and expanded overseas capacity for customers."
        )
    source_sha = _sha(data)
    source_id = source_id_for_sha256(source_sha)
    material: TranscriptMaterial | None = None
    if transcript:
        material = extract_transcript_material(data, mime_type="text/plain")
        parsed = parse_transcript_text(
            material.text_utf8,
            source_id=source_id,
            source_sha256=source_sha,
            language="en",
        )
        title = "ACME earnings call"
        kind = "earnings_call_transcript"
        language = "en"
    else:
        parsed = parse_pdf_bytes(
            data,
            source_id=source_id,
            source_sha256=source_sha,
            language="en",
        )
        title = "投资者关系管理办法（2025年8月）.pdf" if skipped else "ACME annual report"
        kind = "ir_policy" if skipped else "annual_report"
        language = "en"
    package = select_narrative_evidence(parsed, title=title, existing_kind=kind)
    if skipped and not package.evidence_spans and parsed.deferred_table_pages:
        parsed = parse_pdf_bytes(
            data,
            source_id=source_id,
            source_sha256=source_sha,
            language=language,
            full_table_scan=True,
        )
        package = select_narrative_evidence(parsed, title=title, existing_kind=kind)
    if skipped:
        assert package.status == "skipped_no_narrative"
    else:
        assert package.evidence_spans
    value = {
        "schema_version": "narrative-select-result/2.0",
        "source_ref": {
            "schema_version": "2.0",
            "document_id": "doc-verify",
            "source_id": source_id,
            "content_sha256": source_sha,
            "byte_size": len(data),
            "mime_type": "text/plain" if transcript else "application/pdf",
        },
        "expected_read_policy_sha256": _sha("read-policy"),
        "source_metadata": {
            "source_class": "transcript" if transcript else "filing",
            "title": title,
            "document_kind": kind,
            "language": language,
        },
        "parser": {"name": NARRATIVE_PARSER_NAME, "version": NARRATIVE_PARSER_VERSION},
        "selector": {
            "name": NARRATIVE_SELECTOR_NAME,
            "version": NARRATIVE_SELECTOR_VERSION,
        },
        "selection": _selection_metrics(parsed, package),
        "evidence_spans": [span.to_dict() for span in package.evidence_spans],
        "prompt_review": _review(source_sha),
        "transcript_lineage": material.lineage_dict() if material is not None else None,
        "transcript_byte_bindings": (
            _bindings(material, package.evidence_spans) if material is not None else []
        ),
        "summary_scope": "selected_evidence_only",
    }
    return data, NarrativeSelectResult.from_dict(value)


def _summary(
    selected: NarrativeSelectResult,
    *,
    prompt_version: str = NARRATIVE_PROMPT_VERSION,
) -> NarrativeSummaryResult:
    skipped = selected.selection.status == "skipped_no_narrative"
    draft = None
    model = None
    if not skipped:
        span = selected.evidence_spans[0]
        draft = {
            "source_id": selected.source_ref.source_id,
            "source_sha256": selected.source_ref.content_sha256,
            "language": selected.source_metadata.language,
            "claims": [
                {
                    "claim_id": "claim-verify",
                    "text": span.raw_text,
                    "evidence_ids": [span.span_id],
                    "claim_type": "company_statement",
                    "modality": "actual",
                    "needs_review": False,
                }
            ],
            "status": "draft",
        }
        model = {
            "adapter_id": "replay",
            "model_id": "fixture-v1",
            "prompt_version": prompt_version,
            "response_sha256": _sha("response"),
        }
    result = NarrativeSummaryResult.from_dict(
        {
            "schema_version": "narrative-summary-result/2.0",
            "source_ref": selected.source_ref.to_dict(),
            "language": selected.source_metadata.language,
            "translate": False,
            "status": "summary_not_needed" if skipped else "completed",
            "draft": draft,
            "model": model,
            "prompt_review": selected.prompt_review.to_dict(),
        }
    )
    result.validate_against(selected)
    return result


def _payload(selected: NarrativeSelectResult) -> dict[str, object]:
    return {
        "schema_version": "source-revision-event/2.0",
        "source_ref": selected.source_ref.to_dict(),
        "expected_read_policy_sha256": selected.expected_read_policy_sha256,
        "source_metadata": selected.source_metadata.to_dict(),
    }


def _dependency(value: dict[str, Any]) -> HandlerResult:
    return HandlerResult(
        outcome=HandlerOutcome.SUCCEEDED,
        result=value,
        artifacts=(),
        effects=(),
        metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=1),
        error=None,
    )


def _context(
    selected: NarrativeSelectResult,
    summary: NarrativeSummaryResult,
    *,
    payload: dict[str, object] | None = None,
    checkpoints: list[int] | None = None,
) -> JobExecutionContext:
    event_payload = payload or _payload(selected)
    parsed = SourceRevisionEventPayload.from_dict(event_payload)
    event = Event(
        event_id="event-verify",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id=parsed.source_ref.document_id,
        input_hash=parsed.input_hash,
        payload_json=canonical_json(event_payload),
        policy_version="narrative-v1",
        occurred_at=T0,
        observed_at=T0,
    )
    job = Job(
        job_id="job-verify",
        job_key=make_job_key(
            "source.narrative_verify",
            event.subject_type,
            event.subject_id,
            event.input_hash,
            event.policy_version,
            "1.0.0",
        ),
        job_type="source.narrative_verify",
        subject_type=event.subject_type,
        subject_id=event.subject_id,
        input_hash=event.input_hash,
        policy_version=event.policy_version,
        handler_version="1.0.0",
        risk_class=RiskClass.LOW,
        status=JobStatus.RUNNING,
        priority=0,
        not_before=T0,
        max_attempts=2,
        created_from_event_id=event.event_id,
        created_at=T0,
        updated_at=T0,
        last_error_code=None,
        last_error_detail=None,
    )
    attempt = Attempt(
        attempt_id="attempt-verify",
        job_id=job.job_id,
        attempt_no=1,
        worker_id="worker-verify",
        lease_token="lease-verify",
        lease_until="2026-09-28T20:05:00Z",
        started_at=T0,
        heartbeat_at=T0,
        finished_at=None,
        outcome=None,
        result_json=None,
        error_code=None,
        error_detail=None,
        runtime_generation=2,
    )
    seen = checkpoints if checkpoints is not None else []
    return JobExecutionContext(
        job,
        attempt,
        event,
        event_payload,
        {
            "source.narrative_select": _dependency(selected.to_dict()),
            "source.narrative_summarize": _dependency(summary.to_dict()),
        },
        parsed,
        lambda: seen.append(1),
    )


class FakeReader:
    def __init__(
        self,
        selected: NarrativeSelectResult,
        data: bytes,
        *,
        review: PromptReviewValue | None = None,
    ) -> None:
        source = selected.source_ref
        current = review or selected.prompt_review
        self.opened = VerifiedContent(
            document_id=source.document_id,
            source_id=source.source_id,
            content_sha256=source.content_sha256,
            data=data,
            byte_size=len(data),
            read_at=T0,
            policy_sha256=_sha("catalog-policy"),
            source_read_policy_sha256=selected.expected_read_policy_sha256,
            review=ReviewSnapshot(
                current.status,
                current.source_sha256,
                current.evidence_sha256,
                current.policy_hash,
                current.reviewed_at,
            ),
        )
        self.metadata = {
            "document_id": source.document_id,
            "source_id": source.source_id,
            "content_sha256": source.content_sha256,
            "byte_size": source.byte_size,
            "mime_type": source.mime_type,
            "title": selected.source_metadata.title,
            "document_kind": selected.source_metadata.document_kind,
            "language": selected.source_metadata.language,
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
    data: bytes,
    selected: NarrativeSelectResult,
    summary: NarrativeSummaryResult,
    *,
    reader: FakeReader | None = None,
    payload: dict[str, object] | None = None,
    pdf_replayer: Callable[..., tuple[tuple[str, ...], tuple[str, ...]]] | None = None,
) -> HandlerResult:
    handler = NarrativeVerifyHandler(
        reader=reader or FakeReader(selected, data),
        pdf_replayer=pdf_replayer,
    )
    return handler(_context(selected, summary, payload=payload))


@pytest.mark.parametrize(
    ("status", "reason", "code", "outcome"),
    [
        ("unavailable", "catalog_unavailable", "IO_TRANSIENT", HandlerOutcome.RETRYABLE),
        ("not_indexed", "document_not_indexed", "SOURCE_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE),
        ("not_indexed", "source_version_not_indexed", "SOURCE_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE),
        ("unavailable", "no_indexed_location", "SOURCE_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE),
        ("unavailable", "no_verified_location", "SOURCE_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE),
        ("unavailable", "expected_version_mismatch", "SOURCE_HASH_MISMATCH", HandlerOutcome.TERMINAL_FAILURE),
        ("unavailable", "source_ref_changed", "SOURCE_HASH_MISMATCH", HandlerOutcome.TERMINAL_FAILURE),
        ("blocked", "read_policy_mismatch", "POLICY_DENIED", HandlerOutcome.TERMINAL_FAILURE),
    ],
)
def test_verify_handler_machine_read_error_semantics(
    monkeypatch, status: str, reason: str, code: str, outcome: HandlerOutcome,
) -> None:
    from company_wiki.automation.registry import create_default_registry
    from company_wiki.automation.retry import classify_outcome

    data, selected = _selected(transcript=True)
    summary = _summary(selected)
    reader = FakeReader(selected, data)

    def unavailable(*_args, **_kwargs):
        raise SourceReadError(status, reason)

    monkeypatch.setattr(reader, "open_version", unavailable)
    raw = _run(data, selected, summary, reader=reader)
    assert raw.outcome is outcome
    assert raw.error is not None and (raw.error.code, raw.error.detail) == (code, reason)
    assert raw.effects == () and raw.metrics.tokens == 0
    spec = create_default_registry().get("source.narrative_verify")
    statuses = [classify_outcome(raw.outcome, raw.error.code, spec.retryable_errors,
                                spec.human_errors, spec.terminal_errors, attempt, 2)[0]
                for attempt in (1, 2)]
    assert statuses == ([JobStatus.RETRY_WAIT, JobStatus.DEAD_LETTER]
                        if outcome is HandlerOutcome.RETRYABLE else [JobStatus.DEAD_LETTER] * 2)


def test_verify_handler_pdf_replays_and_emits_one_deterministic_pending_effect() -> None:
    data, selected = _selected()
    summary = _summary(selected)

    first = _run(data, selected, summary)
    second = _run(data, selected, summary)

    assert first.outcome is HandlerOutcome.SUCCEEDED
    assert first.result == second.result
    assert first.effects == second.effects
    bundle = NarrativeBundle.from_dict(first.result)
    bundle.validate_against(selected, summary)
    assert bundle.encoded_size < BUNDLE_MAX_BYTES
    assert first.artifacts == ()
    assert len(first.effects) == 1
    effect = first.effects[0]
    assert effect.status is EffectStatus.PENDING
    assert effect.intended_after_hash == canonical_json_hash(bundle.to_dict())
    assert effect.target.startswith("urn:company-wiki:narrative-bundle:")
    assert "/" not in effect.target and chr(92) not in effect.target
    assert effect.actual_after_hash is None and effect.verified_at is None


def test_verify_handler_skip_bundle_stays_under_small_cap() -> None:
    data, selected = _selected(skipped=True)
    summary = _summary(selected)

    raw = _run(data, selected, summary)

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    bundle = NarrativeBundle.from_dict(raw.result)
    assert bundle.quality_status == "skipped_no_narrative"
    assert bundle.encoded_size < SKIP_BUNDLE_MAX_BYTES
    assert bundle.replay.locator_count == 0
    assert len(raw.effects) == 1


def test_same_bundle_from_distinct_jobs_has_distinct_publication_effects() -> None:
    data, selected = _selected()
    summary = _summary(selected)
    context = _context(selected, summary)
    other_job = replace(context.job, job_id="job-verify-next-run")
    other = replace(context, job=other_job,
                    attempt=replace(context.attempt, job_id=other_job.job_id))
    handler = NarrativeVerifyHandler(reader=FakeReader(selected, data))

    first = handler(context)
    second = handler(other)

    assert first.outcome is second.outcome is HandlerOutcome.SUCCEEDED
    assert first.result == second.result
    assert first.effects[0].intended_after_hash == second.effects[0].intended_after_hash
    assert first.effects[0].job_id != second.effects[0].job_id
    assert first.effects[0].effect_id != second.effects[0].effect_id
    assert first.effects[0].effect_key != second.effects[0].effect_key
    assert handler(other).effects == second.effects


def test_verify_handler_transcript_replays_bytes_without_provider_policy() -> None:
    data, selected = _selected(transcript=True)
    summary = _summary(selected)

    raw = _run(
        data,
        selected,
        summary,
        payload=_payload(selected),
    )

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    bundle = NarrativeBundle.from_dict(raw.result)
    assert bundle.replay.locator_count == len(selected.evidence_spans)


def test_verify_handler_rejects_transcript_byte_binding_mismatch_with_zero_effect() -> None:
    data, selected = _selected(transcript=True)
    changed = selected.to_dict()
    changed["transcript_byte_bindings"][0]["source_byte_ranges"][0]["start"] += 1
    drifted = NarrativeSelectResult.from_dict(changed)
    summary = _summary(drifted)

    raw = _run(
        data,
        drifted,
        summary,
        payload=_payload(drifted),
    )

    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "LOCATOR_REPLAY_FAILED"
    assert raw.effects == ()


def test_verify_handler_any_pdf_locator_failure_has_zero_effect() -> None:
    data, selected = _selected()
    summary = _summary(selected)

    def fail_replay(*_args, **_kwargs):
        return (), tuple(span.span_id for span in selected.evidence_spans)

    raw = _run(data, selected, summary, pdf_replayer=fail_replay)

    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "LOCATOR_REPLAY_FAILED"
    assert raw.effects == ()


@pytest.mark.parametrize("case", ["drift", "missing"])
def test_verify_handler_review_metadata_does_not_gate_effect(case: str) -> None:
    data, selected = _selected()
    summary = _summary(selected)
    current = replace(selected.prompt_review, policy_hash=_sha("new-review-policy"))
    reader = FakeReader(selected, data, review=current)
    if case == "missing":
        reader.opened = replace(reader.opened, review=None)

    raw = _run(
        data,
        selected,
        summary,
        reader=reader,
    )

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    assert raw.error is None
    assert len(raw.effects) == 1


@pytest.mark.parametrize("case", ["event", "parser", "prompt"])
def test_verify_handler_rejects_dependency_identity_and_version_drift(case: str) -> None:
    data, selected = _selected()
    payload = _payload(selected)
    if case == "event":
        payload["expected_read_policy_sha256"] = _sha("new-read-policy")
    elif case == "parser":
        changed = selected.to_dict()
        changed["parser"]["version"] = "9.9.9"
        selected = NarrativeSelectResult.from_dict(changed)
    summary = _summary(
        selected,
        prompt_version=("9.9.9" if case == "prompt" else NARRATIVE_PROMPT_VERSION),
    )

    raw = _run(data, selected, summary, payload=payload)

    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "DEPENDENCY_INVALID"
    assert raw.effects == ()


def test_verify_handler_source_metadata_drift_blocks_before_replay() -> None:
    data, selected = _selected()
    summary = _summary(selected)
    reader = FakeReader(selected, data)
    reader.metadata["language"] = "mixed"

    raw = _run(data, selected, summary, reader=reader)

    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "INPUT_SCHEMA_INVALID"
    assert raw.effects == ()
