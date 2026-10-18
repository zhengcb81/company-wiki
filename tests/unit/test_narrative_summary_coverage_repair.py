"""Coverage repair: a scoped summary retries once to cover the remaining tasks."""
from dataclasses import replace
import json

from company_wiki.automation import narrative_model as legacy
from company_wiki.automation.models import HandlerMetrics, HandlerOutcome, canonical_json
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from unit.test_narrative_reading_transport import with_reading
from unit.test_narrative_summarize_handler import _context

V4 = "reading-model-input/4"


def _response(prompt_version, drafts):
    return legacy.NarrativeModelResponse(
        "offline", "configured", prompt_version,
        canonical_json({"drafts_by_task": drafts}).encode())


class _Caller:
    def __init__(self, drafts):
        self.drafts = list(drafts)
        self.requests = []

    def generate(self, context, request):
        self.requests.append(request)
        return (_response(request.prompt_version, self.drafts.pop(0)),
                HandlerMetrics(tokens=1, cost_usd=0.0, duration_ms=1))


def _handler(caller):
    return NarrativeSummarizeHandler(
        model=None, model_caller=caller,
        reading_model_projection=lambda subject: V4,
    )


def _clause():
    return {"text": "公司新产品已完成海外客户认证。", "basis_parts": ["p1"],
            "modality": "actual"}


def test_partial_summary_retries_and_the_repair_call_only_sends_uncovered_tasks(monkeypatch):
    monkeypatch.setenv("CW_SUMMARY_COVERAGE_REPAIR", "1")
    selected = with_reading()
    first = _handler(_Caller([{"t1": [_clause()]}]))
    partial = first(_context(selected))
    assert partial.outcome is HandlerOutcome.RETRYABLE
    assert partial.result["coverage_partial"] is True
    assert list(partial.result["uncovered_task_keys"]) == ["t2"]
    assert partial.error is not None and partial.error.code == "SUMMARY_COVERAGE_PARTIAL"

    caller = _Caller([{"t2": [_clause()]}])
    repair = _handler(caller)
    context = _context(selected)
    context = replace(
        context,
        attempt=replace(context.attempt, attempt_no=2),
        prior_partial_result=partial,
    )
    completed = repair(context)

    assert completed.outcome is HandlerOutcome.SUCCEEDED
    request = json.loads(caller.requests[0].data_json)
    assert [task["key"] for task in request["material"]["tasks"]] == ["t2"]
    claims = completed.result["draft"]["claims"]
    assert [claim["claim_id"] for claim in claims] == ["t1-1", "t2-r1"]
    assert completed.result["draft"]["status"] == "needs_review"

