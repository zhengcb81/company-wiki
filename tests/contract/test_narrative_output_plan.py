"""96 selected spans: compact planning, honest truncation and one settlement."""

import json
import time
import pytest
from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.automation.narrative_model import (
    NarrativeModelRequest,
    decode_model_draft,
)
from company_wiki.automation.narrative_model_caller import (
    BudgetedNarrativeCaller,
    NarrativeBudgetCallError,
)
from support.fresh_summary_fixture import grouped_selection, claim, draft_for
from unit.test_narrative_run_store import setup_run, claim as claim_job


def selected96():
    return grouped_selection(
        tuple(
            f"新產品{i // 3}已完成海外客户认证，订单和交付取得进展。片段{i}。"
            for i in range(96)
        ),
        tuple(f"g{i // 3}" for i in range(96)),
    )


class PlannedProvider(NarrativeHTTPModel):
    """Deterministic compliance stub, not proof a real model will obey the plan."""

    def __init__(self, *, force_truncate=False, **kw):
        super().__init__(
            model_id="model-one",
            endpoint="https://offline.invalid/chat/completions",
            api_key_env="UNUSED",
            **kw,
        )
        self.calls = 0
        self.force_truncate = force_truncate

    def generate(self, request):
        self.calls += 1
        body = json.loads(self.request_bytes(request))
        envelope = json.loads(body["messages"][1]["content"])
        plan = envelope.get("output_plan")
        truncated = self.force_truncate or not plan
        count = min(plan["target_claim_count"], 6) if plan else 96
        claims = [
            claim(
                f"新產品{i}已完成海外客户认证，订单和交付取得进展。",
                [f"e{3 * i + n}" for n in (1, 2, 3)],
                [f"g{i + 1}"],
                name=f"c{i + 1}",
            )
            for i in range(count)
        ]
        content = json.dumps(
            draft_for(selected96(), claims), ensure_ascii=False, separators=(",", ":")
        )
        self.returned_content_bytes = len(
            (content[:250] if truncated else content).encode("utf8")
        )
        payload = {
            "model": self.model_id,
            "choices": [
                {
                    "message": {"content": content[:250] if truncated else content},
                    "finish_reason": "length" if truncated else "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 2716,
                "completion_tokens": self.max_output_tokens if truncated else 1100,
            },
        }
        return self._response(request, json.dumps(payload).encode(), time.monotonic())


def test_96_span_compact_plan_is_material_excerpt_not_row_enumeration_and_preserves_every_source_row():
    selected = selected96()
    before = selected.to_dict()
    request = NarrativeModelRequest.from_selection(selected)
    model = PlannedProvider(max_output_tokens=8192)
    body = json.loads(model.request_bytes(request))
    envelope = json.loads(body["messages"][1]["content"])
    plan = envelope["output_plan"]
    assert plan["configured_output_tokens"] == body["max_tokens"] == 8192
    assert 1 <= plan["target_claim_count"] <= 8 < 96 and plan["max_claims"] == 20
    assert (
        plan["target_text_chars"] <= 180
        and plan["coverage"] == "selected_excerpts_only"
    )
    assert len(envelope["evidence"]) == 96 and len(envelope["evidence_groups"]) == 32
    response = model.generate(request)
    draft = decode_model_draft(response, selected=selected)
    assert (
        len(draft["claims"]) == 6
        and response.output_tokens == 1100
        and model.calls == 1
    )
    assert selected.to_dict() == before


@pytest.mark.parametrize("limit", [1200, 2400, 8192])
def test_compact_plan_uses_real_configured_cap_without_changing_model_or_generation_options(
    limit,
):
    request = NarrativeModelRequest.from_selection(selected96())
    model = PlannedProvider(
        max_output_tokens=limit, temperature=0.7, thinking="adaptive"
    )
    body = json.loads(model.request_bytes(request))
    plan = json.loads(body["messages"][1]["content"])["output_plan"]
    assert (
        body["max_tokens"] == plan["configured_output_tokens"] == limit
        and body["model"] == "model-one"
    )
    assert body["thinking"] == {"type": "adaptive"} and body["temperature"] == 0.7
    assert 1 <= plan["target_claim_count"] <= 8 and plan["max_claims"] == 20


def test_truncated_96_span_attempt_settles_once_with_safe_length_diagnostic_and_cannot_blindly_replay(
    tmp_path,
):
    from types import SimpleNamespace
    from company_wiki.automation.narrative_model import NARRATIVE_PROMPT_VERSION

    _module, auto, store, generation, a, _b = setup_run(
        tmp_path,
        max_tokens=200000,
        max_micro_usd=200000,
        max_output_bytes=200000,
        prompt_version=NARRATIVE_PROMPT_VERSION,
    )
    work = claim_job(auto, generation, a)
    context = SimpleNamespace(
        job=work.job, attempt=work.attempt, checkpoint=lambda: None
    )
    model = PlannedProvider(max_output_tokens=8192, force_truncate=True)
    caller = BudgetedNarrativeCaller(
        store=store,
        run_id="run-one",
        model=model,
        final_output_bytes_bound=100000,
        clock=lambda: "2026-10-03T10:01:00Z",
    )
    request = NarrativeModelRequest.from_selection(selected96())
    with pytest.raises(NarrativeBudgetCallError) as caught:
        caller.generate(context, request)
    error = caught.value
    assert (
        error.code == "MODEL_OUTPUT_TRUNCATED"
        and error.outcome is HandlerOutcome.TERMINAL_FAILURE
    )
    assert (
        error.finish_reason == "length"
        and error.content_bytes == model.returned_content_bytes
    )
    records = store.reservations_for_run("run-one")
    assert len(records) == 1
    record = records[0]
    assert record.usage_status == "known" and (
        record.input_tokens,
        record.output_tokens,
    ) == (2716, 8192)
    assert record.charged_tokens == 10908 and record.response_sha256 is None
    before = store.budget_snapshot("run-one")
    with pytest.raises(
        NarrativeBudgetCallError, match="MODEL_REQUEST_ALREADY_RESERVED"
    ):
        caller.generate(context, request)
    assert model.calls == 1 and store.budget_snapshot("run-one") == before


def test_truncation_reaches_handler_static_diagnostics_with_original_source_identity_and_no_success():
    from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
    from unit.test_narrative_summarize_handler import _context as handler_context
    from company_wiki.automation.models import HandlerMetrics

    selected = selected96()
    before = selected.to_dict()

    class Caller:
        def generate(self, ctx, request):
            raise NarrativeBudgetCallError(
                "MODEL_OUTPUT_TRUNCATED",
                HandlerOutcome.TERMINAL_FAILURE,
                HandlerMetrics(tokens=10908, cost_usd=0.011829, duration_ms=18),
                finish_reason="length",
                content_bytes=250,
            )

    result = NarrativeSummarizeHandler(model=None, model_caller=Caller())(
        handler_context(selected)
    )
    assert (
        result.outcome is HandlerOutcome.TERMINAL_FAILURE
        and result.result == {}
        and result.artifacts == ()
    )
    assert (
        result.metrics.tokens == 10908
        and "finish_reason=length" in result.error.detail
        and "content_bytes=250" in result.error.detail
    )
    assert selected.to_dict() == before
