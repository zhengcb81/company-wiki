"""General source guidance/premise controls through the actual public ports."""
from pathlib import Path

import pytest

from company_wiki.automation.narrative_generation import current_reading_decision_matches
from company_wiki.source_catalog import narrative_revenue_guidance as grammar
from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact
from unit.document_understanding_selection.test_reading_guidance_condition_scope import (
    HEADING, _assert_premise_closed, _model, _select, _source, _spans_for,
)
from unit.document_understanding_selection.test_reading_native_carriers import source_fixture

CASES = (
    ("For fiscal 2029, we anticipate network access revenue of EUR 175 to 190 million.",
     "This revenue outlook is conditional on customer acceptance before the year end."),
    ("We forecast annual net sales between GBP 730 and 755 million for 2029.",
     "This revenue forecast assumes delivery of the contracted customer orders before year end."),
    ("本集团预期2029年医疗服务收入同比增长8%至11%。",
     "上述收入展望取决于新增客户订单按期交付。"),
    ("本集團預計2029年航運服務營收介於18億至22億港元。",
     "上述營收展望以新航線按期取得經營許可為前提。"),
    ("Our software licensing revenue is projected to reach USD 92 million in fiscal 2029.",
     "This revenue guidance is based on customer licence renewals in the next fiscal year."),
    ("Our company expects equipment rental revenue of USD 125 million in fiscal 2029.",
     "This equipment rental revenue outlook assumes customers accept new equipment on time."),
)


@pytest.mark.parametrize("guidance,premise", CASES)
def test_neutral_revenue_word_order_and_units_reach_true_source_closure(guidance, premise):
    source = _source([HEADING, guidance, premise])
    selected = _select(source)
    _assert_premise_closed(selected, source.units[1], source.units[2])
    spans = _spans_for(selected, source.units[1])
    assert spans and all("source_revenue_guidance" in span.structured_value["selection_reasons"] for span in spans)
    assert detect_reading_business_fact(guidance).purpose == "operating_guidance"


def test_referenced_full_year_performance_outlook_closes_its_explicit_premise():
    guidance = "本集团预计2030年服务收入达到60亿元。"
    premise = (
        "上述提及的2030年全年经营业绩展望以目前订单为基础预测，并以行业发展平稳、"
        "贸易与监管环境稳定为前提；不构成管理层对年度业绩的实质承诺，存在较大不确定性。"
    )
    source = _source([HEADING, guidance, premise])
    selected = _select(source)
    _assert_premise_closed(selected, source.units[1], source.units[2])


def test_forecast_marker_before_year_and_issuer_closes_referenced_premise():
    guidance = "预计2026年公司整体收入达到513-530亿元，持续经营业务收入同比增长18%-22%。"
    premise = (
        "上述提及的2026年全年经营业绩展望以公司目前在手订单情况为基础预测，并以全球医药行业发展平稳、"
        "国际贸易环境和主要运营所在地国家监管环境稳定等为前提基础，并不代表公司管理层对2026年度全年经营业绩的盈利预测，"
        "不构成公司对投资者的实质承诺，能否实现取决于内外部环境变化等多种因素影响，存在较大的不确定性。"
    )
    assert grammar.revenue_guidance(guidance, issuer_only=True)
    source = _source([HEADING, guidance, premise])
    _assert_premise_closed(_select(source), source.units[1], source.units[2])


def test_explicit_reference_year_must_match_the_nearby_revenue_outlook():
    forecast = "预计2027年公司整体收入达到500亿元。"
    premise = "上述提及的2026年全年经营业绩展望以在手订单为基础预测。"
    assert not grammar.revenue_guidance_premise(forecast, premise, follows=True)


def test_explicit_reference_year_matches_the_nearby_revenue_outlook():
    forecast = "预计2026年公司整体收入达到500亿元。"
    premise = "上述提及的2026年全年经营业绩展望以在手订单为基础预测。"
    assert grammar.revenue_guidance_premise(forecast, premise, follows=True)


def test_backward_guidance_premise_prefilter_keeps_only_explicit_references():
    assert grammar.is_explicit_backward_revenue_guidance_premise(
        "上述提及的2026年全年经营业绩展望以公司目前在手订单为基础预测。"
    )
    assert not grammar.is_explicit_backward_revenue_guidance_premise(
        "下述2026年全年经营业绩展望假设订单按期交付。"
    )
    assert not grammar.is_explicit_backward_revenue_guidance_premise(
        "公司目前在手订单充足。"
    )


def test_another_company_after_forecast_marker_is_not_the_local_issuer():
    assert not grammar.revenue_guidance(
        "预计2026年合作伙伴公司整体收入达到500亿元。", issuer_only=True
    )


@pytest.mark.parametrize("text", (
    "分析师预计2026年公司整体收入达到500亿元。",
    "市场预计2026年公司整体收入达到500亿元。",
    "外部顾问预计2026年本集团收入达到500亿元。",
))
def test_external_forecaster_cannot_lend_issuer_identity_after_its_forecast_cue(text):
    assert not grammar.revenue_guidance(text, issuer_only=True)


@pytest.mark.parametrize("text", (
    "预计2026年公司整体收入达到500亿元。",
    "2026年预计公司整体收入达到500亿元。",
))
def test_year_before_forecast_cue_does_not_count_as_another_actor(text):
    assert grammar.revenue_guidance(text, issuer_only=True)


@pytest.mark.parametrize("guidance,premise", (
    ("We expect online services revenue of USD 265 million in fiscal 2029.",
     "The following online services revenue outlook assumes customer orders are accepted before year end."),
    ("本集团预计2029年技术服务收入为9至12亿元。",
     "下述技术服务收入展望假设新客户验收在年末前完成。"),
))
def test_explicit_forward_reference_keeps_the_preceding_original_premise(guidance, premise):
    source = _source([HEADING, premise, guidance])
    _assert_premise_closed(_select(source), source.units[2], source.units[1])


@pytest.mark.parametrize("guidance,premise", (
    ("We expect subscription revenue of USD 525 million in fiscal 2029.",
     "This equipment rental revenue outlook assumes customer orders are accepted before year end."),
    ("公司预计2029年物流服务收入为18亿元。",
     "上述材料服务收入展望以新客户按期验收为前提。"),
    ("We expect subscription revenue of USD 525 million in fiscal 2029.",
     "The following revenue guidance assumes customer orders are accepted before year end."),
    ("Our supplier expects subscription revenue of USD 525 million in fiscal 2029.",
     "This revenue guidance assumes customer orders are accepted before year end."),
    ("本公司的客户预计2029年物流服务收入为18亿元。",
     "上述收入展望以新客户按期验收为前提。"),
    ("We expect subscription revenue of USD 525 million in fiscal 2029.",
     "This revenue guidance does not assume that new customer orders will be delivered."),
))
def test_reference_direction_scope_and_other_actor_cannot_borrow_the_local_issuer(guidance, premise):
    source = _source([HEADING, guidance, premise])
    selected = _select(source)
    support = {span.span_id for span in _spans_for(selected, source.units[1])}
    assert support
    unrelated = {span.span_id for span in _spans_for(selected, source.units[2])}
    view, _ = _model(selected)
    assert all(not unrelated.intersection(task.member_ids) for task in view.plan.tasks
               if support.intersection(task.support_ids))


@pytest.mark.parametrize("text", (
    "Our revenue was USD 182 million in fiscal 2028, below the revenue guidance of USD 190 million.",
    "We expect customer retention to improve and our revenue was USD 182 million in fiscal 2028.",
    "Our customer revenue was USD 182 million in fiscal 2028; we expect higher profits next year.",
    "We expect new orders for equipment 330 and internally label the new revenue process as 2029.",
))
def test_source_forecast_reason_cannot_be_borrowed_by_an_actual_value_or_identifier(text):
    assert not grammar.revenue_guidance(text)
    assert "source_revenue_guidance" not in detect_reading_business_fact(text).reasons


def test_wrapped_guidance_native_carrier_uses_its_complete_source_body_for_external_premise():
    first = "We expect subscription revenue of USD"
    last = "610 to 650 million in fiscal 2029."
    premise = "This revenue outlook assumes customers renew their subscriptions before the year end."
    source, _ = source_fixture([(HEADING,), (first, last), (premise,)])
    selected = _select(source)
    for fragment in source.units[1:3]:
        _assert_premise_closed(selected, fragment, source.units[3])


def test_actual_guidance_module_bytes_invalidate_the_real_complete_cache_and_restore(monkeypatch):
    from company_wiki.document_understanding import decision_inventory as inventory
    from company_wiki.document_understanding.decision_dependencies import freeze_decision_dependencies
    from unit.document_understanding_selection.test_reading_decision_inventory import _real_interim_pipeline

    # This synthetic PDF fixture has no real frontend identity. Use the existing
    # actual native interim pipeline's complete text/HTML interpretation rather
    # than forging a complete PDF inventory just to test cache comparison.
    pipeline = _real_interim_pipeline()
    pipeline["observation"]["metadata"]["mime_type"] = "text/html"
    dependencies = freeze_decision_dependencies(inventory.build_decision_trace(pipeline))
    manifest = {"reading_dependencies": dependencies,
                "selection_generation": {"decision_digest": dependencies["decision_digest"]}}
    assert dependencies["status"] == "complete"
    assert current_reading_decision_matches(manifest)
    target = Path(grammar.__file__).resolve()
    assert target.is_relative_to(Path(__file__).resolve().parents[3] / "src")
    original_read = Path.read_bytes
    with monkeypatch.context() as patch:
        def changed(path):
            raw = original_read(path)
            return raw + b"\n# changed source-guidance policy\n" if path.resolve() == target else raw
        patch.setattr(Path, "read_bytes", changed)
        assert not current_reading_decision_matches(manifest)
    assert current_reading_decision_matches(manifest)


@pytest.mark.parametrize("text", (
    "Our project revenue of USD 83 million was recorded in the prior year.",
    "We will report the prior year revenue of USD 83 million next month.",
))
def test_project_noun_or_future_reporting_action_is_not_a_revenue_forecast(text):
    assert not grammar.revenue_guidance(text)


@pytest.mark.parametrize("guidance,premise", (
    ("The company's maintenance services revenue is expected to reach USD 74 million in fiscal 2030.",
     "This revenue guidance assumes the existing customers renew the maintenance contracts."),
    ("本公司的技术服务收入预期达到25亿元。",
     "上述收入展望以现有客户按期完成验收为前提。"),
))
def test_actual_issuer_possessive_retains_its_passive_forecast_and_premise(guidance, premise):
    source = _source([HEADING, guidance, premise])
    _assert_premise_closed(_select(source), source.units[1], source.units[2])
