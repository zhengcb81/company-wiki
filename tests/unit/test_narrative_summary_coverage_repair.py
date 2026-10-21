"""Retired paid repair never creates a second scoped model operation.

Historical partial DTOs remain readable and retain their original summary;
they are not silently published as complete or charged for another request.
"""
from dataclasses import replace

import pytest

from company_wiki.automation import narrative_model as legacy
from company_wiki.automation.models import (
    HandlerError, HandlerMetrics, HandlerOutcome, HandlerResult, canonical_json,
)
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from unit.test_narrative_reading_transport import with_reading, reading_context
from unit.test_narrative_summarize_handler import _context
from unit.test_official_json_model_subject import selection as official_selection

V4 = "reading-model-input/4"


class _Caller:
    def __init__(self):
        self.requests = []

    def generate(self, context, request):
        self.requests.append(request)
        key = "t2" if context.source_revision.subject.kind == "official_json" else "t1"
        text = ("公司新产品已完成海外客户认证。" if context.source_revision.source_metadata.language == "zh"
                else "New overseas product qualification is progressing.")
        return (legacy.NarrativeModelResponse("offline", "configured", request.prompt_version,
            canonical_json({"drafts_by_task": {key: [{
                "text": text,
                "basis_parts": ["p1"], "modality": "uncertain",
            }]}}).encode()), HandlerMetrics(tokens=1, cost_usd=0.0, duration_ms=1))


def _handler(caller):
    return NarrativeSummarizeHandler(model=None, model_caller=caller, reading_model_projection=lambda _: V4)


@pytest.mark.parametrize("projected", [False, True], ids=["raw", "official-json"])
def test_retired_env_never_creates_paid_coverage_retry(monkeypatch, projected):
    monkeypatch.setenv("CW_SUMMARY_COVERAGE_REPAIR", "1")
    if projected:
        from company_wiki.automation.narrative_contracts import NarrativeSelectResult
        selected = official_selection()
        wire = selected.to_dict()
        strategy = reading_context(selected)
        strategy["groups"] = [{"group_id": f"p{i}", "kind": "business_progress", "section_role": "business",
                               "evidence_ids": [span.span_id]} for i, span in enumerate(selected.evidence_spans)]
        wire["reading_context"] = strategy
        selected = NarrativeSelectResult.from_dict(wire)
        from unit.test_official_json_summarize_subject import context as projection_context
        context = projection_context(selected)
    else:
        selected = with_reading()
        context = _context(selected)
    caller = _Caller()
    result = _handler(caller)(context)
    assert result.outcome is HandlerOutcome.SUCCEEDED, result
    assert len(caller.requests) == 1
    assert "coverage_partial" not in result.result
    assert [claim["claim_id"] for claim in result.result["draft"]["claims"]] == ["t2-1" if projected else "t1-1"]
    assert result.result["draft"]["status"] == "needs_review"


def _legacy_partial(selected):
    from unit.test_narrative_reading_transport import summary
    return HandlerResult(HandlerOutcome.RETRYABLE,
        {"coverage_partial": True, "summary": summary(selected).to_dict(),
         "uncovered_task_keys": ["t2"], "execution": {}}, (), (),
        HandlerMetrics(tokens=92, cost_usd=0.000045, duration_ms=1),
        HandlerError("SUMMARY_COVERAGE_PARTIAL", "historical fixture"))


@pytest.mark.parametrize("uncovered", [["t2"], []])
def test_legacy_partial_remains_available_without_new_call_or_false_completion(uncovered):
    selected = with_reading()
    partial = _legacy_partial(selected)
    wire = partial.to_dict()
    wire["result"]["uncovered_task_keys"] = uncovered
    partial = HandlerResult.from_dict(wire)
    caller = _Caller()
    context = replace(_context(selected), prior_partial_result=partial,
        attempt=replace(_context(selected).attempt, attempt_no=2))
    before = partial.to_dict()
    result = _handler(caller)(context)
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == "LEGACY_PARTIAL_SUMMARY_AVAILABLE"
    assert result.result == partial.result
    assert not result.effects and not caller.requests
    assert partial.to_dict() == before
    assert result.metrics.tokens == 0  # old charge stays in its old reservation


def test_malformed_legacy_partial_never_falls_through_to_a_new_paid_call():
    selected = with_reading()
    partial = _legacy_partial(selected).to_dict()
    partial["result"]["summary"]["model"]["response_sha256"] = "invalid"
    caller = _Caller()
    result = _handler(caller)(replace(_context(selected),
        prior_partial_result=HandlerResult.from_dict(partial)))
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == "LEGACY_PARTIAL_SUMMARY_INVALID"
    assert not caller.requests
