"""Neutral shared predicate/time controls beyond the frozen independent17."""
from pathlib import Path

import pytest

from company_wiki.automation.narrative_generation import current_reading_decision_matches
from company_wiki.source_catalog import narrative_predicate_state as state
from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog import narrative_revenue_guidance as guidance
from unit.document_understanding_selection.test_reading_guidance_condition_scope import (
    HEADING, _assert_premise_closed, _select, _source,
)
from unit.document_understanding_selection.test_reading_predicate_state_owner import ACTUAL


@pytest.mark.parametrize("verb", ("expect", "anticipate", "project", "forecast", "predict", "estimate"))
def test_one_modality_owner_prevents_actual_quantity_and_retains_forward_revenue(verb):
    quantity = f"We {verb} our reactor volume of 167 kL."
    start = quantity.index("volume")
    observation = state.observe_metric_predicate(quantity, start, start + len("volume"))
    assert not observation.observed and observation.modality == "expected"
    assert not ACTUAL.intersection(policy.detect_reading_business_fact(quantity).reasons)
    outlook = f"We {verb} subscription revenue of USD 167 million next year."
    assert guidance.revenue_guidance(outlook)
    assert "source_revenue_guidance" in policy.detect_reading_business_fact(outlook).reasons
    premise = "This revenue outlook assumes customers renew their subscriptions on time."
    parsed = _source([HEADING, outlook, premise])
    _assert_premise_closed(_select(parsed), parsed.units[1], parsed.units[2])


@pytest.mark.parametrize("verb", ("有望", "力争", "计划", "预期"))
def test_shared_chinese_goal_scope_is_not_an_observed_metric(verb):
    quantity = f"公司{verb}反应器总体积增加至217kL。"
    assert not ACTUAL.intersection(policy.detect_reading_business_fact(quantity).reasons)
    assert guidance.revenue_guidance(f"公司{verb}明年设备服务收入达到17亿元。")


@pytest.mark.parametrize("text,expected", (
    ("We expect software licensing revenue to have grown by 9% last year.", False),
    ("Our software licensing revenue is projected to have increased by 9% last quarter.", False),
    ("We anticipate new orders next year, but our software licensing revenue is USD 167 million.", False),
    ("We will announce our software licensing revenue of USD 167 million next month.", False),
    ("We expect software licensing revenue to have grown by 9% by the end of next year.", True),
    ("We expect software licensing revenue to increase by 9% next year compared with the previous year.", True),
    ("We project software licensing revenue of USD 167 million versus the prior year.", True),
    ("We will generate software licensing revenue of USD 167 million next year.", True),
))
def test_metric_period_and_action_ownership_are_shared_not_prefix_word_bags(text, expected):
    assert guidance.revenue_guidance(text) is expected
    assert ("source_revenue_guidance" in policy.detect_reading_business_fact(text).reasons) is expected


@pytest.mark.parametrize("text", (
    "Our project reactor volume is 167 kL.",
    "We anticipate new orders next year, but our reactor volume is 167 kL.",
    "We expect customer renewals to improve while our reactor volume has reached 167 kL.",
))
def test_an_independent_future_action_or_project_noun_does_not_erase_actual_quantity(text):
    assert "operating_quantity" in policy.detect_reading_business_fact(text).reasons


def test_shared_predicate_source_bytes_are_in_the_actual_complete_cache(monkeypatch):
    from company_wiki.document_understanding import decision_inventory as inventory
    from company_wiki.document_understanding.decision_dependencies import freeze_decision_dependencies
    from unit.document_understanding_selection.test_reading_decision_inventory import _real_interim_pipeline

    observed = _real_interim_pipeline()
    observed["observation"]["metadata"]["mime_type"] = "text/html"
    dependencies = freeze_decision_dependencies(inventory.build_decision_trace(observed))
    assert dependencies["status"] == "complete"
    manifest = {"reading_dependencies": dependencies,
                "selection_generation": {"decision_digest": dependencies["decision_digest"]}}
    assert current_reading_decision_matches(manifest)
    target = Path(state.__file__).resolve()
    assert target.is_relative_to(Path(__file__).resolve().parents[3] / "src")
    actual_read = Path.read_bytes
    with monkeypatch.context() as patch:
        def changed(path):
            raw = actual_read(path)
            return raw + b"\n# changed source predicate owner\n" if path.resolve() == target else raw
        patch.setattr(Path, "read_bytes", changed)
        assert not current_reading_decision_matches(manifest)
    assert current_reading_decision_matches(manifest)


@pytest.mark.parametrize("text", (
    "We expect subscription revenue of USD 167 million next year if customers renew their contracts on time.",
    "公司预计明年技术服务收入达到17亿元，假设客户订单按期完成验收。",
))
def test_an_explicit_forward_outlook_keeps_its_inline_condition_without_becoming_actual(text):
    assert guidance.revenue_guidance(text)
    assert "source_revenue_guidance" in policy.detect_reading_business_fact(text).reasons
    assert not ACTUAL.intersection(policy.detect_reading_business_fact(text).reasons)
    parsed = _source([HEADING, text])
    selected = _select(parsed)
    assert any(span.raw_text == text and "source_revenue_guidance" in span.structured_value["selection_reasons"]
               for span in selected.evidence_spans)


@pytest.mark.parametrize("text", (
    "If subscription revenue reaches USD 167 million, the company will expand the factory.",
    "如果技术服务收入达到17亿元，公司将扩建厂房。",
))
def test_a_hypothetical_metric_without_a_revenue_forecast_predicate_is_neither_actual_nor_guidance(text):
    assert not guidance.revenue_guidance(text)
    assert not ACTUAL.intersection(policy.detect_reading_business_fact(text).reasons)


@pytest.mark.parametrize("text", (
    "We anticipate our reactor volume of 143 kL.",
    "We project our reactor volume of 143 kL.",
    "公司有望将反应器总体积增加至143kL。",
    "公司力争反应器总体积增加至143kL。",
    "We anticipate our active user count of 217 next year.",
    "公司力争明年客户数量达到217家。",
))
def test_a_source_capacity_or_business_quantity_target_remains_exact_model_evidence_not_actual(text):
    from unit.document_understanding_selection.test_reading_guidance_condition_scope import (
        CURRENT_REASONS, _model, _spans_for,
    )

    fact = policy.detect_reading_business_fact(text)
    assert not ACTUAL.intersection(fact.reasons)
    assert "operating_plan" in fact.reasons
    parsed = _source([HEADING, text])
    selected = _select(parsed)
    spans = _spans_for(selected, parsed.units[1])
    assert spans and all(span.raw_text == text for span in spans)
    assert all("operating_plan" in span.structured_value["selection_reasons"] for span in spans)
    assert all(not CURRENT_REASONS.intersection(span.structured_value["selection_reasons"]) for span in spans)
    support = {span.span_id for span in spans}
    assert all(span.source_id == parsed.source_id for span in spans)
    view, texts = _model(selected)
    tasks = [task for task in view.plan.tasks if support.intersection(task.support_ids)]
    assert tasks and all(any(text == raw for raw in texts[task.key]) for task in tasks)


@pytest.mark.parametrize("outlook,premise", (
    ("We expect subscription revenue will increase by 9% next year.",
     "This revenue outlook assumes existing customers renew their contracts on time."),
    ("公司有望将明年设备服务收入提升至17亿元。",
     "上述收入展望以现有客户按期完成验收为前提。"),
))
def test_nested_future_auxiliary_keeps_the_outer_forecast_actor_in_the_real_closure(outlook, premise):
    parsed = _source([HEADING, outlook, premise])
    _assert_premise_closed(_select(parsed), parsed.units[1], parsed.units[2])
