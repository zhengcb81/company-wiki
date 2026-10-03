from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from typing import Any

import pytest

from company_wiki.automation.execution_context import JobExecutionContext
from company_wiki.automation.models import (
    Attempt,
    Event,
    HandlerMetrics,
    HandlerOutcome,
    HandlerResult,
    Job,
    JobStatus,
    RiskClass,
    canonical_json,
    make_job_key,
)
from company_wiki.automation.narrative_contracts import (
    NarrativeSelectResult,
    NarrativeSummaryResult,
    PromptReviewValue,
    SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_model import (
    NARRATIVE_PROMPT_VERSION,
    ModelRateLimitError,
    ModelTimeoutError,
    NarrativeModelRequest,
    NarrativeModelResponse,
)
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.source_contract import (
    EvidenceCoordinates,
    EvidenceSpan,
    ParseStatus,
    source_id_for_sha256,
)


T0 = "2026-09-28T18:00:00Z"


def _sha(value: str | bytes) -> str:
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _review(source_sha: str, *, reviewed: bool = True) -> dict[str, object]:
    if not reviewed:
        return {
            "status": "not_reviewed",
            "source_sha256": None,
            "evidence_sha256": None,
            "policy_hash": None,
            "reviewed_at": None,
        }
    return {
        "status": "not_detected",
        "source_sha256": source_sha,
        "evidence_sha256": _sha("review-evidence"),
        "policy_hash": _sha("review-policy"),
        "reviewed_at": T0,
    }


def _selection(
    *,
    language: str = "zh",
    transcript: bool = False,
    skipped: bool = False,
    reviewed: bool = True,
    role: str = "company_filing",
    quality_flags: tuple[str, ...] = (),
) -> NarrativeSelectResult:
    source_bytes = (
        b"Full Conference Call Transcript\nCEO: new product launch\n"
        if transcript
        else b"verified filing bytes"
    )
    source_sha = _sha(source_bytes)
    source_id = source_id_for_sha256(source_sha)
    spans: list[dict[str, Any]] = []
    if not skipped:
        span = EvidenceSpan.create(
            source_id=source_id,
            coordinates=(
                EvidenceCoordinates(paragraph_index=1)
                if transcript
                else EvidenceCoordinates(page_number=1, paragraph_index=0)
            ),
            raw_text=(
                "Management launched a new product for overseas customers."
                if language == "en"
                else "管理层已启动面向海外客户的新产品。"
            ),
            structured_value={
                "language": language,
                "source_role": "management" if transcript else role,
                "selection_reasons": ["business_progress"],
                "line_start": 2 if transcript else None,
                "line_end": 2 if transcript else None,
            },
            parser_name="summary-test",
            parser_version="1.0.0",
            parse_status=ParseStatus.PARSED,
            quality_flags=quality_flags,
        )
        spans.append(span.to_dict())
    lineage = (
        {
            "schema_version": "transcript-material/2",
            "original_source_id": source_id,
            "original_sha256": source_sha,
            "original_mime_type": "text/plain",
            "original_byte_size": len(source_bytes),
            "text_sha256": _sha("normalized transcript"),
            "text_byte_size": 21,
            "extractor_version": "fixture-v1",
            "line_count": 2,
        }
        if transcript
        else None
    )
    bindings = (
        [
            {
                "evidence_id": spans[0]["span_id"],
                "material_line_start": 2,
                "material_line_end": 2,
                "source_byte_ranges": [{"start": 32, "end": 55}],
            }
        ]
        if transcript and spans
        else []
    )
    return NarrativeSelectResult.from_dict(
        {
            "schema_version": "narrative-select-result/2.0",
            "source_ref": {
                "schema_version": "2.0",
                "document_id": "doc-summary",
                "source_id": source_id,
                "content_sha256": source_sha,
                "byte_size": len(source_bytes),
                "mime_type": "text/plain" if transcript else "application/pdf",
            },
            "expected_read_policy_sha256": _sha("read-policy"),
            "source_metadata": {
                "source_class": "transcript" if transcript else "filing",
                "title": "ACME earnings call" if transcript else "ACME annual report",
                "document_kind": (
                    "earnings_call_transcript" if transcript else "annual_report"
                ),
                "language": language,
            },
            "parser": {"name": "fixture-parser", "version": "1.0.0"},
            "selector": {"name": "fixture-selector", "version": "1.0.0"},
            "selection": {
                "status": "skipped_no_narrative" if skipped else "selected",
                "coverage_complete": True,
                "source_units": 2,
                "candidate_count": len(spans),
                "selected_count": len(spans),
                "omitted_candidate_count": 0,
                "dropped_financial_count": 0,
                "pages_total": 0 if transcript else 1,
                "pages_read": 0 if transcript else 1,
                "lines_total": 2 if transcript else 0,
                "tables_total": 0,
                "tables_scanned": 0,
            },
            "evidence_spans": spans,
            "prompt_review": _review(source_sha, reviewed=reviewed),
            "transcript_lineage": lineage,
            "transcript_byte_bindings": bindings,
            "summary_scope": "selected_evidence_only",
        }
    )


def _event_payload(selected: NarrativeSelectResult) -> dict[str, object]:
    return {
        "schema_version": "source-revision-event/2.0",
        "source_ref": selected.source_ref.to_dict(),
        "expected_read_policy_sha256": selected.expected_read_policy_sha256,
        "source_metadata": selected.source_metadata.to_dict(),
    }


def _context(
    selected: NarrativeSelectResult,
    *,
    payload: dict[str, object] | None = None,
    checkpoints: list[int] | None = None,
) -> JobExecutionContext:
    event_payload = payload or _event_payload(selected)
    parsed = SourceRevisionEventPayload.from_dict(event_payload)
    event = Event(
        event_id="event-summary",
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
        job_id="job-summary",
        job_key=make_job_key(
            "source.narrative_summarize",
            event.subject_type,
            event.subject_id,
            event.input_hash,
            event.policy_version,
            "1.0.0",
        ),
        job_type="source.narrative_summarize",
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
        attempt_id="attempt-summary",
        job_id=job.job_id,
        attempt_no=1,
        worker_id="worker-summary",
        lease_token="lease-summary",
        lease_until="2026-09-28T18:05:00Z",
        started_at=T0,
        heartbeat_at=T0,
        finished_at=None,
        outcome=None,
        result_json=None,
        error_code=None,
        error_detail=None,
        runtime_generation=2,
    )
    dependency = HandlerResult(
        outcome=HandlerOutcome.SUCCEEDED,
        result=selected.to_dict(),
        artifacts=(),
        effects=(),
        metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=1),
        error=None,
    )
    seen = checkpoints if checkpoints is not None else []
    return JobExecutionContext(
        job,
        attempt,
        event,
        event_payload,
        {"source.narrative_select": dependency},
        parsed,
        lambda: seen.append(1),
    )


class ReplayModel:
    def __init__(
        self,
        *,
        draft_overrides: dict[str, Any] | None = None,
        error: Exception | None = None,
        malformed: bytes | None = None,
    ) -> None:
        self.calls: list[NarrativeModelRequest] = []
        self.draft_overrides = draft_overrides or {}
        self.error = error
        self.malformed = malformed

    def generate(self, request: NarrativeModelRequest) -> NarrativeModelResponse:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        envelope = json.loads(request.data_json)
        evidence = envelope["evidence"]
        draft: dict[str, Any] = {
            "source_id": envelope["source"]["source_id"],
            "source_sha256": envelope["source"]["source_sha256"],
            "language": envelope["source"]["language"],
            "claims": [
                {
                    "claim_id": "claim-001",
                    "text": evidence[0]["raw_text"],
                    "evidence_ids": [evidence[0]["span_id"]],
                    "claim_type": "company_statement",
                    "modality": "actual",
                    "needs_review": False,
                }
            ],
            "status": "draft",
        }
        draft.update(self.draft_overrides)
        response = self.malformed or canonical_json({"draft": draft}).encode("utf-8")
        return NarrativeModelResponse(
            adapter_id="replay",
            model_id="fixture-v1",
            prompt_version=NARRATIVE_PROMPT_VERSION,
            response_bytes=response,
        )


class ReviewLoader:
    def __init__(self, value: PromptReviewValue | None):
        self.value = value
        self.calls: list[str] = []

    def __call__(self, document_id: str) -> PromptReviewValue | None:
        self.calls.append(document_id)
        return self.value


def _run(
    selected: NarrativeSelectResult,
    *,
    model: ReplayModel | None,
    review: PromptReviewValue | None = None,
    review_loader: ReviewLoader | None = None,
    payload: dict[str, object] | None = None,
) -> tuple[HandlerResult, ReviewLoader, list[int]]:
    loader = review_loader or ReviewLoader(review or selected.prompt_review)
    checkpoints: list[int] = []
    handler = NarrativeSummarizeHandler(model=model)
    return handler(_context(selected, payload=payload, checkpoints=checkpoints)), loader, checkpoints


def test_summarize_handler_replay_is_canonical_and_selected_only() -> None:
    selected = _selection(language="zh")
    first_model = ReplayModel()
    second_model = ReplayModel()

    first, _, checkpoints = _run(selected, model=first_model)
    second, _, _ = _run(selected, model=second_model)

    assert first.outcome is HandlerOutcome.SUCCEEDED
    assert first.result == second.result
    assert first.effects == ()
    assert checkpoints == [1, 1, 1]
    summary = NarrativeSummaryResult.from_dict(first.result)
    summary.validate_against(selected)
    assert summary.translate is False
    assert first_model.calls[0].input_sha256 == second_model.calls[0].input_sha256
    prompt = first_model.calls[0].data_json
    assert selected.evidence_spans[0].raw_text in prompt
    assert "unselected full document text" not in prompt
    assert "summary_input" not in prompt
    assert "absolute_path" not in prompt


def test_summarize_handler_does_not_require_prompt_review_receipt() -> None:
    selected = _selection(reviewed=False)
    model = ReplayModel()

    raw, _, _ = _run(selected, model=model)

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    assert len(model.calls) == 1
    summary = NarrativeSummaryResult.from_dict(raw.result)
    assert summary.prompt_review.status == "not_reviewed"


def test_summarize_handler_skip_uses_no_model_policy_or_review_lookup() -> None:
    selected = _selection(skipped=True, reviewed=False)
    model = ReplayModel()
    loader = ReviewLoader(None)
    policy_calls: list[int] = []
    handler = NarrativeSummarizeHandler(model=model)

    raw = handler(_context(selected))

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    result = NarrativeSummaryResult.from_dict(raw.result)
    result.validate_against(selected)
    assert result.status == "summary_not_needed"
    assert model.calls == []
    assert loader.calls == []
    assert policy_calls == []


@pytest.mark.parametrize("language", ["zh", "en", "mixed"])
def test_summarize_handler_preserves_source_language(language: str) -> None:
    selected = _selection(language=language)
    raw, _, _ = _run(selected, model=ReplayModel())

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    result = NarrativeSummaryResult.from_dict(raw.result)
    assert result.language == language
    assert result.translate is False
    assert result.draft is not None and result.draft.language == language


def test_summarize_handler_missing_model_blocks_before_external_work() -> None:
    selected = _selection()
    raw, loader, _ = _run(selected, model=None)

    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "MODEL_NOT_CONFIGURED"
    assert loader.calls == []
    assert raw.effects == ()


@pytest.mark.parametrize("case", ["missing", "not_reviewed", "drift"])
def test_summarize_handler_does_not_require_current_prompt_review(case: str) -> None:
    selected = _selection(reviewed=case != "not_reviewed")
    current: PromptReviewValue | None = selected.prompt_review
    if case == "missing":
        current = None
    elif case == "drift":
        current = replace(selected.prompt_review, policy_hash=_sha("new-policy"))
    model = ReplayModel()

    current_loader = ReviewLoader(current)
    raw, loader, _ = _run(
        selected,
        model=model,
        review_loader=current_loader,
    )

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    assert raw.error is None
    assert loader.calls == []
    assert len(model.calls) == 1
    assert raw.effects == ()


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ModelTimeoutError("timeout"), "MODEL_TIMEOUT"),
        (ModelRateLimitError("429"), "MODEL_RATE_LIMIT"),
    ],
)
def test_summarize_handler_transient_model_failures_are_single_attempt_retryable(
    error: Exception, code: str
) -> None:
    selected = _selection()
    model = ReplayModel(error=error)

    raw, _, _ = _run(selected, model=model)

    assert raw.outcome is HandlerOutcome.RETRYABLE
    assert raw.error is not None and raw.error.code == code
    assert len(model.calls) == 1
    assert raw.effects == ()


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(b"not-json", id="invalid-json"),
        pytest.param(b'{"draft":{},"draft":{}}', id="duplicate-key"),
        pytest.param(b"x" * (128 * 1024 + 1), id="over-cap"),
    ],
)
def test_summarize_handler_malformed_model_response_is_not_retried(
    response: bytes,
) -> None:
    selected = _selection()
    model = ReplayModel(malformed=response)

    raw, _, _ = _run(selected, model=model)

    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "MODEL_RESPONSE_INVALID"
    assert len(model.calls) == 1
    assert raw.effects == ()


def test_summarize_handler_rejects_model_path_leak_and_keeps_only_hash() -> None:
    selected = _selection()
    model = ReplayModel(
        draft_overrides={
            "claims": [
                {
                    "claim_id": "claim-path",
                    "text": (
                        chr(67)
                        + ":"
                        + chr(92)
                        + "private"
                        + chr(92)
                        + "source.pdf"
                    ),
                    "evidence_ids": [selected.evidence_spans[0].span_id],
                    "claim_type": "company_statement",
                    "modality": "actual",
                    "needs_review": False,
                }
            ]
        }
    )

    raw, _, _ = _run(selected, model=model)

    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "MODEL_RESPONSE_INVALID"
    assert len(model.calls) == 1
    assert "response_bytes" not in raw.result
    assert raw.effects == ()


@pytest.mark.parametrize("case", ["unknown_evidence", "role", "blank", "unstable"])
def test_summarize_handler_rejects_invalid_summary_claims(case: str) -> None:
    role = "analyst" if case == "role" else "company_filing"
    flags = ("locator_unstable",) if case == "unstable" else ()
    selected = _selection(role=role, quality_flags=flags)
    overrides: dict[str, Any] = {}
    if case == "unknown_evidence":
        overrides["claims"] = [
            {
                "claim_id": "claim-bad",
                "text": "unsupported",
                "evidence_ids": ["urn:company-wiki:evidence:sha256:" + _sha("absent")],
                "claim_type": "company_statement",
                "modality": "actual",
                "needs_review": False,
            }
        ]
    elif case == "blank":
        overrides["claims"] = [
            {
                "claim_id": "claim-bad",
                "text": " ",
                "evidence_ids": [selected.evidence_spans[0].span_id],
                "claim_type": "company_statement",
                "modality": "actual",
                "needs_review": False,
            }
        ]
    model = ReplayModel(draft_overrides=overrides)

    raw, _, _ = _run(selected, model=model)

    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "SUMMARY_INVALID"
    assert len(model.calls) == 1
    assert raw.effects == ()


def test_summarize_handler_summarizes_transcript_without_provider_policy() -> None:
    selected = _selection(transcript=True)
    model = ReplayModel()

    raw, _, _ = _run(selected, model=model)

    assert raw.outcome is HandlerOutcome.SUCCEEDED
    assert raw.error is None
    assert model.calls
    assert raw.effects == ()


def test_summarize_handler_rejects_dependency_identity_drift_before_model() -> None:
    selected = _selection()
    model = ReplayModel()
    payload = _event_payload(selected)
    payload["expected_read_policy_sha256"] = _sha("new-read-policy")

    raw, _, _ = _run(selected, model=model, payload=payload)

    assert raw.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert raw.error is not None and raw.error.code == "DEPENDENCY_INVALID"
    assert model.calls == []
    assert raw.effects == ()


def test_model_prompt_teaches_wire_schema_to_an_unconfigured_model() -> None:
    import jsonschema

    selected = _selection()
    request = NarrativeModelRequest.from_selection(selected)
    envelope = json.loads(request.data_json)
    schema = envelope["response_schema"]
    response = json.loads(ReplayModel().generate(request).response_bytes)
    jsonschema.validate(response, schema)
    response["draft"]["claims"][0]["modality"] = "buy"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(response, schema)
    assert request.prompt_version != "1.0.0"
    assert "source_role" in request.instruction
    assert "locator_unstable" in request.instruction
    assert "needs_review" in request.instruction


@pytest.mark.parametrize("language,role,flags", [("zh", "company_filing", ()), ("en", "analyst", ()), ("zh", "unknown", ("locator_unstable",))])
def test_prompt_wire_example_passes_the_actual_summary_contract(language, role, flags) -> None:
    selected = _selection(language=language, role=role, quality_flags=flags)
    envelope = json.loads(NarrativeModelRequest.from_selection(selected).data_json)
    response = NarrativeModelResponse(
        "example", "shape-only", NARRATIVE_PROMPT_VERSION,
        canonical_json(envelope["response_example"]).encode("utf-8"),
    )
    result = NarrativeSummarizeHandler._completed_result(selected, selected.prompt_review, response)
    result.validate_against(selected)


@pytest.mark.parametrize("case", ["valid", "bad_json", "bad_claim"])
def test_summarize_keeps_paid_attempt_metrics_after_output_validation(case) -> None:
    selected = _selection()
    model = ReplayModel(
        malformed=b"not JSON" if case == "bad_json" else None,
        draft_overrides={"claims": []} if case == "bad_claim" else None,
    )
    expected = HandlerMetrics(tokens=123, cost_usd=0.002, duration_ms=17)

    class Caller:
        def generate(self, context, request):
            assert context.attempt.attempt_id
            return model.generate(request), expected

    result = NarrativeSummarizeHandler(model=model, model_caller=Caller())(_context(selected))
    assert result.metrics == expected
    assert result.outcome is (HandlerOutcome.SUCCEEDED if case == "valid" else HandlerOutcome.TERMINAL_FAILURE)


def test_skipped_document_never_reserves_or_calls_paid_model() -> None:
    class Caller:
        def generate(self, *arguments):
            raise AssertionError("skipped document must use zero budget and HTTP")

    result = NarrativeSummarizeHandler(model=None, model_caller=Caller())(_context(_selection(skipped=True)))
    assert result.outcome is HandlerOutcome.SUCCEEDED
    assert result.metrics.tokens == 0
