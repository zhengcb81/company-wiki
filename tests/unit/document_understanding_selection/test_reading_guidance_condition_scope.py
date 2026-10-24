"""Source-authored revenue outlook and its explicitly linked local premises.

All inputs are synthetic native observations. Public structure/selection and
model-view compilation run normally, without a prebuilt pipeline or model call.
The current contract has no OperatingFact.modality or model-input forecast
field: these tests use existing source text, reason codes and citation/task
membership instead of inventing one.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from company_wiki.resource_budget import DEFAULT_DOCUMENT_WORK_LIMIT, WorkBudget
from company_wiki.source_catalog import narrative_reading as reading
from unit.document_understanding_selection.test_reading_native_carriers import source_fixture

HEADING = "三、未来经营展望"
FUTURE_PROCESS = "未来公司计划改善内部管理。"
FORECASTS = (
    ("cn-equipment", "公司预计2027年设备服务业务收入为24至27亿元，同比增长12%至18%。",
     "上述收入指引以新增客户按期完成验收为前提。"),
    ("trad-logistics", "公司預計2028年度物流服務收入介於65億至72億港元，同比增長9%至14%。",
     "上述收入指引以兩名海外客戶的訂單按期完成驗收為前提。"),
    ("en-subscription", "We expect subscription revenue of USD 410 to 435 million in fiscal 2027, representing growth of 13% to 19%.",
     "This revenue outlook assumes the overseas customers complete acceptance of their orders before year end."),
    ("cn-materials", "公司预计2027年新材料业务收入达到18至21亿元。",
     "上述收入指引以海外工厂按期取得经营许可为前提。"),
)
CURRENT_REASONS = {
    "operating_current_state", "operating_milestone", "applied_operating_milestone",
    "customer_adoption_milestone", "new_product_commercialization_milestone",
}


@pytest.fixture(autouse=True)
def current_checkout_import_is_used():
    root = Path(__file__).resolve().parents[3] / "src"
    assert Path(reading.__file__).resolve().is_relative_to(root)


def _source(texts, *, digest="c" * 64):
    source, _ = source_fixture([(text,) for text in texts], source_sha=digest)
    return source


def _select(parsed, *, max_selected=96, max_chars=48000):
    original = [(u.unit_id, u.source_id, u.raw_text, u.coordinates, repr(u.metadata), u.quality_flags)
                for u in parsed.units]
    budget = WorkBudget(DEFAULT_DOCUMENT_WORK_LIMIT)
    result = reading.select_reading_evidence(parsed, title="Neutral annual report",
        existing_kind="annual_report", max_selected=max_selected, max_chars=max_chars, work_budget=budget)
    assert original == [(u.unit_id, u.source_id, u.raw_text, u.coordinates, repr(u.metadata), u.quality_flags)
                        for u in parsed.units]
    assert not budget.exhausted and 0 < budget.used <= 16_000_000
    assert DEFAULT_DOCUMENT_WORK_LIMIT == 16_000_000 and reading.MAX_READING_CHARS == 48000
    assert result.selection_limit == max_selected and len(result.evidence_spans) <= max_selected
    assert sum(len(s.raw_text or "") for s in result.evidence_spans) <= max_chars
    assert result.reading_context["schema_version"] == "du-production-reading/3"
    return result


def _spans_for(selected, original):
    matches = []
    for span in selected.evidence_spans:
        if span.source_id != original.source_id:
            continue
        if span.raw_text == original.raw_text and span.coordinates == original.coordinates:
            matches.append(span)
        elif original.unit_id in span.structured_value.get("native_range", {}).get("source_unit_ids", ()):
            assert original.raw_text in span.raw_text
            matches.append(span)
    return matches


def _model(selected):
    view = compile_scoped_model_view(SimpleNamespace(evidence_spans=selected.evidence_spans,
                                     reading_context=selected.reading_context), max_claims=20)
    data = view.to_model_dict()
    assert data["schema_version"] == "source-scoped-model-view/1"
    shared = {part["source_key"]: part for part in data["shared_fragments"]}
    texts_by_task = {task["key"]: [shared[part["shared_ref"]]["text"] if "shared_ref" in part else part["text"]
                                  for part in task["parts"]] for task in data["tasks"]}
    return view, texts_by_task


def _assert_premise_closed(selected, guidance, condition, *, require_guidance=True):
    support = _spans_for(selected, guidance)
    if require_guidance:
        assert support, "A source-authored future revenue outlook is useful narrative, not a historical total."
    if not support:
        return
    premise = _spans_for(selected, condition)
    assert premise, "An explicitly linked local premise cannot disappear while its forecast remains."
    support_ids, premise_ids = {s.span_id for s in support}, {s.span_id for s in premise}
    groups = [v for g in selected.reading_context["groups"] for v in g["citation_views"]
              if support_ids.intersection(v["support_evidence_ids"])]
    assert groups and all(premise_ids.intersection([*v["support_evidence_ids"], *v["context_evidence_ids"]])
                          for v in groups), "Citation closure, not merely separate selection, must retain the premise."
    view, model_texts = _model(selected)
    tasks = [task for task in view.plan.tasks if support_ids.intersection(task.support_ids)]
    assert tasks and all(premise_ids.intersection(task.member_ids) for task in tasks)
    for task in tasks:
        assert any(guidance.raw_text in text for text in model_texts[task.key])
        assert any(condition.raw_text in text for text in model_texts[task.key])


@pytest.mark.parametrize("label,guidance,condition", FORECASTS, ids=[c[0] for c in FORECASTS])
def test_future_revenue_range_and_growth_are_preserved_without_current_achievement_labels(label, guidance, condition):
    parsed = _source([HEADING, guidance, FUTURE_PROCESS])
    selected = _select(parsed)
    spans = _spans_for(selected, parsed.units[1])
    assert spans, "Do not drop future segment guidance as a financial historical-number row."
    assert all(not CURRENT_REASONS.intersection(span.structured_value.get("selection_reasons", ())) for span in spans)
    view, texts = _model(selected)
    tasks = [task for task in view.plan.tasks if {s.span_id for s in spans}.intersection(task.support_ids)]
    assert tasks and all(any(guidance in text for text in texts[task.key]) for task in tasks)


@pytest.mark.parametrize("label,guidance,condition", FORECASTS, ids=[c[0] for c in FORECASTS])
def test_explicit_local_guidance_premise_reaches_public_citation_and_model_task(label, guidance, condition):
    parsed = _source([HEADING, guidance, condition, FUTURE_PROCESS])
    selected = _select(parsed)
    _assert_premise_closed(selected, parsed.units[1], parsed.units[2])
    future = {s.span_id for s in _spans_for(selected, parsed.units[-1])}
    support = {s.span_id for s in _spans_for(selected, parsed.units[1])}
    view, _ = _model(selected)
    assert all(not future.intersection(task.member_ids) for task in view.plan.tasks if support.intersection(task.support_ids))


def test_explicit_following_outlook_reference_can_bind_its_preceding_local_premise():
    guidance = FORECASTS[0][1]
    condition = "以下设备服务收入展望假设新增客户的订单在年末前完成验收。"
    parsed = _source([HEADING, condition, guidance, FUTURE_PROCESS])
    _assert_premise_closed(_select(parsed), parsed.units[2], parsed.units[1])


@pytest.mark.parametrize("cap", (1, 2))
def test_lower_source_slot_budget_never_makes_the_guidance_cheaper_by_dropping_its_premise(cap):
    _, guidance, condition = FORECASTS[0]
    parsed = _source([HEADING, guidance, condition, FUTURE_PROCESS])
    _assert_premise_closed(_select(parsed, max_selected=cap), parsed.units[1], parsed.units[2], require_guidance=False)


@pytest.mark.parametrize("label,guidance,condition", FORECASTS[:3], ids=[c[0] for c in FORECASTS[:3]])
def test_condition_already_in_original_guidance_body_is_not_removed_or_rewritten(label, guidance, condition):
    body = guidance + " " + condition
    parsed = _source([HEADING, body, FUTURE_PROCESS])
    selected = _select(parsed)
    spans = _spans_for(selected, parsed.units[1])
    assert spans and all(body in span.raw_text for span in spans)
    assert all(not CURRENT_REASONS.intersection(span.structured_value.get("selection_reasons", ())) for span in spans)
    _, texts = _model(selected)
    assert any(body in text for parts in texts.values() for text in parts)


@pytest.mark.parametrize("neighbour", (
    "如果极端天气持续，部分物流线路可能延误。",
    "未来公司计划改善内部管理。",
    "供应商已表示，其收入指引以钢材价格稳定为前提。",
))
def test_nearby_risk_future_or_other_party_outlook_is_not_this_guidance_premise(neighbour):
    guidance = "公司预计2027年物流服务业务收入为24至27亿元，同比增长12%至18%。"
    parsed = _source([HEADING, guidance, neighbour])
    selected = _select(parsed)
    support = {s.span_id for s in _spans_for(selected, parsed.units[1])}
    assert support
    unrelated = {s.span_id for s in _spans_for(selected, parsed.units[2])}
    view, _ = _model(selected)
    assert all(not unrelated.intersection(task.member_ids) for task in view.plan.tasks if support.intersection(task.support_ids))


def test_another_parent_cannot_supply_an_explicit_sounding_guidance_condition():
    _, guidance, condition = FORECASTS[0]
    first, second = _source([HEADING, guidance]), _source([condition], digest="d" * 64)
    parsed = replace(first, units=first.units + second.units)
    selected = _select(parsed)
    support = {s.span_id for s in _spans_for(selected, first.units[1])}
    assert support
    foreign = {s.span_id for s in _spans_for(selected, second.units[0])}
    view, _ = _model(selected)
    assert all(not foreign.intersection(task.member_ids) for task in view.plan.tasks if support.intersection(task.support_ids))
    assert all(len({next(s.source_id for s in selected.evidence_spans if s.span_id == sid) for sid in task.member_ids}) == 1
               for task in view.plan.tasks)


def test_another_section_cannot_reuse_the_previous_outlook_subject_by_adjacency():
    _, guidance, condition = FORECASTS[0]
    parsed = _source([HEADING, guidance, "四、另一业务经营风险", condition])
    selected = _select(parsed)
    support = {s.span_id for s in _spans_for(selected, parsed.units[1])}
    assert support
    other_scope = {s.span_id for s in _spans_for(selected, parsed.units[-1])}
    view, _ = _model(selected)
    assert all(not other_scope.intersection(task.member_ids) for task in view.plan.tasks if support.intersection(task.support_ids))


def test_actual_character_cap_does_not_silently_detach_a_true_guidance_premise():
    _, guidance, condition = FORECASTS[0]
    parsed = _source([HEADING, guidance, condition, FUTURE_PROCESS])
    cap = len(HEADING) + len(guidance) + len(condition) - 1
    _assert_premise_closed(_select(parsed, max_chars=cap), parsed.units[1], parsed.units[2], require_guidance=False)
