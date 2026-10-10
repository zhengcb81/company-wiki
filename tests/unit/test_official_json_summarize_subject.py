"""Projection summaries use the existing context/caller and strict subject wire."""

import json
from types import SimpleNamespace

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
    NarrativeSummaryResult,
    SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from unit.test_official_json_model_subject import binding, selection, claim

T0 = "2026-10-10T00:00:00Z"


def context(selected, *, subject=None):
    wire = {
        "schema_version": "source-revision-event/3.0",
        "subject_binding": subject or selected.subject.to_dict(),
        "source_metadata": selected.source_metadata.to_dict(),
    }
    parsed = SourceRevisionEventPayload.from_dict(wire)
    event = Event(
        "event-projection",
        "source.revision_registered",
        "narrative_subject",
        parsed.item_key,
        parsed.input_hash,
        canonical_json(wire),
        "narrative-v3",
        T0,
        T0,
    )
    job = Job(
        job_id="job-projection",
        job_key=make_job_key(
            "source.narrative_summarize",
            event.subject_type,
            event.subject_id,
            event.input_hash,
            event.policy_version,
            "3.0.0",
        ),
        job_type="source.narrative_summarize",
        subject_type=event.subject_type,
        subject_id=event.subject_id,
        input_hash=event.input_hash,
        policy_version=event.policy_version,
        handler_version="3.0.0",
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
        "attempt-projection",
        job.job_id,
        1,
        "worker-test",
        "lease-test",
        "2026-10-10T00:05:00Z",
        T0,
        T0,
        None,
        None,
        None,
        None,
        None,
        2,
    )
    dependency = HandlerResult(
        HandlerOutcome.SUCCEEDED,
        selected.to_dict(),
        (),
        (),
        HandlerMetrics(0, 0, 1),
        None,
    )
    return JobExecutionContext(
        job,
        attempt,
        event,
        wire,
        {"source.narrative_select": dependency},
        parsed,
        lambda: None,
    )


class ReplaySubjectModel:
    def __init__(self, **overrides):
        self.calls = []
        self.overrides = overrides

    def generate(self, request):
        self.calls.append(request)
        source = json.loads(request.data_json)["subject"]
        draft = {
            key: source[key] for key in ("subject_id", "subject_sha256", "language")
        }
        draft.update(claims=[claim()], **self.overrides)
        return NarrativeModelResponse(
            "fixture",
            "configured-flash",
            request.prompt_version,
            canonical_json({"draft": draft}).encode(),
            input_tokens=100,
            output_tokens=50,
        )


def test_projection_full_handler_uses_strict_subject_summary_without_fake_source():
    selected = selection()
    model = ReplaySubjectModel()
    result = NarrativeSummarizeHandler(model=model)(context(selected))
    assert result.outcome is HandlerOutcome.SUCCEEDED
    assert len(model.calls) == 1
    assert result.result["schema_version"] == "narrative-summary-result/3.0"
    assert canonical_json(
        result.to_dict()["result"]["subject_binding"]
    ) == canonical_json(selected.subject.to_dict())
    assert "source_ref" not in result.result and result.result["translate"] is False
    parsed = NarrativeSummaryResult.from_dict(result.to_dict()["result"])
    parsed.validate_against(selected)
    assert result.result["draft"]["subject_id"] == selected.subject.item_key
    assert result.result["model"]["prompt_version"] == "official-json/1.0.0"


@pytest.mark.parametrize("field", ["issuer", "as_of", "layout", "parent_two"])
def test_same_anchor_different_complete_subject_fails_before_model_or_fee(field):
    selected = selection()
    changed = binding()
    if field == "issuer":
        changed["issuer"]["provider_company_id"] = 902
    elif field == "as_of":
        changed["as_of_date"] = "2026-10-09"
    elif field == "layout":
        changed["adapter"]["layout_version"] = "1.0.2"
    else:
        changed["parent_source_refs"][1]["byte_size"] = 124
    model = ReplaySubjectModel()
    result = NarrativeSummarizeHandler(model=model)(context(selected, subject=changed))
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == "DEPENDENCY_INVALID" and model.calls == []
    assert result.metrics == HandlerMetrics(0, 0, 0)


@pytest.mark.parametrize("options", [{"empty": True}, {"language": "unknown"}])
def test_unavailable_model_input_has_typed_zero_call_zero_fee(options):
    selected = selection(**options)
    model = ReplaySubjectModel()
    result = NarrativeSummarizeHandler(model=model)(context(selected))
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == "SUMMARY_INPUT_UNAVAILABLE"
    assert model.calls == [] and result.metrics == HandlerMetrics(0, 0, 0)


def test_complete_skip_unknown_language_is_valid_without_model():
    selected = selection(skipped=True, language="unknown")
    model = ReplaySubjectModel()
    result = NarrativeSummarizeHandler(model=model)(context(selected))
    assert result.outcome is HandlerOutcome.SUCCEEDED and model.calls == []
    assert (
        result.result["status"] == "summary_not_needed"
        and result.result["draft"] is None
    )
    assert result.result["language"] == "unknown" and result.metrics == HandlerMetrics(
        0, 0, 0
    )


def test_existing_metered_caller_receives_same_context_once_and_metrics_preserved():
    selected = selection()
    ctx = context(selected)
    model = ReplaySubjectModel()
    seen = []
    expected = HandlerMetrics(150, 0.002, 14)

    def generate(actual, request):
        seen.append(actual)
        return model.generate(request), expected

    caller = SimpleNamespace(generate=generate)
    result = NarrativeSummarizeHandler(model=None, model_caller=caller)(ctx)
    assert result.outcome is HandlerOutcome.SUCCEEDED and seen == [ctx]
    assert len(model.calls) == 1 and result.metrics == expected


def test_global_response_identity_error_preserves_fee_and_static_rule():
    selected = selection()
    ctx = context(selected)
    model = ReplaySubjectModel(subject_id="secret-provider-value")
    expected = HandlerMetrics(150, 0.002, 14)
    caller = SimpleNamespace(
        generate=lambda actual, request: (model.generate(request), expected)
    )
    result = NarrativeSummarizeHandler(model=None, model_caller=caller)(ctx)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert (
        result.error.code == "SUMMARY_INVALID"
        and "rule=SUBJECT_IDENTITY" in result.error.detail
    )
    assert "secret-provider-value" not in result.error.detail
    assert len(model.calls) == 1 and result.metrics == expected
