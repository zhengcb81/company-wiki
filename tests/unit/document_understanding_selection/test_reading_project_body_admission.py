"""Public selector regressions for independent prose under project headings.

The format/structure/package builders run normally.  Only source-owned IR is
synthetic; the tests never inject a prebuilt project or patch a selector phase.
"""

from pathlib import Path

import pytest

from company_wiki.resource_budget import DEFAULT_DOCUMENT_WORK_LIMIT, WorkBudget
from company_wiki.source_catalog import narrative_reading as reading
from unit.document_understanding_selection.test_reading_native_carriers import source_fixture


@pytest.fixture(autouse=True)
def own_checkout_is_imported():
    expected = Path(__file__).resolve().parents[3] / "src"
    assert Path(reading.__file__).resolve().is_relative_to(expected)


def project_source(heading="一、项目基本情况", *, qualifier=None, second=True):
    texts = [heading, "报告期内，公司已交付27台专用设备至客户进行生产验证。"]
    if qualifier is not None:
        texts.append(qualifier)
    if second:
        texts.append("公司新建制造基地已经投入运行，年产能达到360台。")
    texts.append("未来公司计划进一步完善内部流程。")
    parsed, _unused_private_pipeline = source_fixture([(text,) for text in texts])
    return parsed


def public_selection(parsed, *, max_selected=96, max_chars=48000):
    original = [(u.unit_id, u.raw_text, u.coordinates, repr(u.metadata)) for u in parsed.units]
    budget = WorkBudget(DEFAULT_DOCUMENT_WORK_LIMIT)
    result = reading.select_reading_evidence(
        parsed, title="示例企业2025年度报告", existing_kind="annual_report",
        max_selected=max_selected, max_chars=max_chars, work_budget=budget,
    )
    assert [(u.unit_id, u.raw_text, u.coordinates, repr(u.metadata)) for u in parsed.units] == original
    assert not budget.exhausted and 0 < budget.used <= 16_000_000
    assert result.selection_limit == max_selected
    assert sum(len(s.raw_text) for s in result.evidence_spans) <= max_chars
    assert len(result.evidence_spans) <= max_selected
    return result


def views_for(result, unit):
    spans = [span for span in result.evidence_spans
             if span.raw_text == unit.raw_text and span.coordinates == unit.coordinates
             and span.source_id == unit.source_id]
    assert len(spans) == 1, "the original complete operating fact must survive its generic project title"
    span_id = spans[0].span_id
    views = [view for group in result.reading_context["groups"]
             for view in group["citation_views"] if span_id in view["support_evidence_ids"]]
    assert views, "an independently complete source fact must be support, not only heading context"
    return views


def assert_unrelated_future_is_not_required(result, facts, future):
    by_id = {span.span_id: span.raw_text for span in result.evidence_spans}
    for fact in facts:
        for view in views_for(result, fact):
            ids = view["support_evidence_ids"] + view["context_evidence_ids"]
            assert future.raw_text not in [by_id[uid] for uid in ids], (
                "project membership is not proof of a dependency on an unrelated future paragraph"
            )


@pytest.mark.parametrize("heading", [
    "一、项目基本情况", "二、物流中心建设项目", "三、设备生产线扩建项目",
])
def test_generic_project_heading_does_not_hide_independent_source_facts(heading):
    parsed = project_source(heading)
    result = public_selection(parsed)
    assert_unrelated_future_is_not_required(result, parsed.units[1:3], parsed.units[-1])


@pytest.mark.parametrize("heading", ["一、项目基本情况", "一、设备生产线扩建项目"])
def test_two_complete_body_facts_and_one_shared_heading_fit_three_source_slots(heading):
    parsed = project_source(heading)
    result = public_selection(parsed, max_selected=3)
    assert_unrelated_future_is_not_required(result, parsed.units[1:3], parsed.units[-1])
    assert parsed.units[-1].raw_text not in [span.raw_text for span in result.evidence_spans]


def test_one_complete_body_fact_is_usable_under_two_slots_without_entire_project_cost():
    parsed = project_source()
    result = public_selection(parsed, max_selected=2)
    selected = {span.raw_text for span in result.evidence_spans}
    facts = [unit for unit in parsed.units[1:3] if unit.raw_text in selected]
    assert facts, "one independent source fact plus its real heading fits; the whole project is not atomic"
    assert_unrelated_future_is_not_required(result, facts, parsed.units[-1])
    assert parsed.units[-1].raw_text not in selected


@pytest.mark.parametrize("qualifier", [
    "该设备尚未完成量产认证，不代表已经形成批量销售。",
    "该设备仍需客户完成认证，预计下一期才能进入量产。",
])
def test_local_device_qualification_stays_with_fact_but_generic_future_does_not(qualifier):
    parsed = project_source(qualifier=qualifier, second=False)
    full = public_selection(parsed)
    facts = views_for(full, parsed.units[1])
    by_id = {span.span_id: span.raw_text for span in full.evidence_spans}
    for view in facts:
        ids = view["support_evidence_ids"] + view["context_evidence_ids"]
        assert qualifier in [by_id[uid] for uid in ids]
        assert parsed.units[-1].raw_text not in [by_id[uid] for uid in ids]
    tight = public_selection(parsed, max_selected=1)
    assert parsed.units[1].raw_text not in [span.raw_text for span in tight.evidence_spans], (
        "a lower selection cap must not detach an explicit local negative/future qualifier"
    )


def test_project_repair_obeys_actual_character_budget_without_rewriting_source():
    parsed = project_source()
    one_fact = parsed.units[1]
    result = public_selection(parsed, max_chars=len(one_fact.raw_text) - 1)
    assert one_fact.raw_text not in [span.raw_text for span in result.evidence_spans]
