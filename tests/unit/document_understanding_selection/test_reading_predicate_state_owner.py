"""Promoted independent17 assertions: a metric owns its predicate and period.

The 17 input strings and expectations are copied byte for byte from the frozen
independent source-state probe. No dependency on a live author/mother folder.
"""
import pytest

from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog import narrative_revenue_guidance as guidance
from unit.document_understanding_selection.test_reading_guidance_condition_scope import (
    HEADING, _model, _select, _source, _spans_for,
)

MEASURE = (('actual-en', 'Our reactor volume reached 143 kL during the reporting period.', True), ('anticipate-en', 'We anticipate our reactor volume of 143 kL.', False), ('project-en', 'We project our reactor volume of 143 kL.', False), ('hope-cn', '公司有望将反应器总体积增加至143kL。', False), ('strive-cn', '公司力争反应器总体积增加至143kL。', False), ('actual-trad', '本公司反應器總體積已增加至143kL。', True))

GUIDANCE = (('future-en', 'We expect subscription revenue of USD 143 million in fiscal 2030.', True), ('future-trad', '本集團預計2030年維修服務營收達到14億港元。', True), ('actual-present-after-independent-expectation', 'We expect customer renewals to improve and our subscription revenue is USD 143 million.', False), ('actual-reached-after-independent-expectation', 'We expect customer renewals to improve while subscription revenue has reached USD 143 million.', False), ('past-completed-quantity', 'We expect subscription revenue to have grown by 14% last quarter.', False), ('past-future-disclosure', 'We will announce that subscription revenue increased by 14% last quarter.', False), ('positive-passive', 'Our software licensing revenue is expected to reach USD 143 million in fiscal 2030.', True))

PAIRS = (('own-en', 'We expect subscription revenue of USD 143 million in fiscal 2030.', 'This revenue outlook assumes customers renew their subscriptions on time.', True), ('third-actor-en', 'Our supplier expects subscription revenue of USD 143 million in fiscal 2030.', 'This revenue outlook assumes customers renew their subscriptions on time.', False), ('different-scope-en', 'We expect subscription revenue of USD 143 million in fiscal 2030.', 'This equipment rental revenue outlook assumes customers accept new equipment on time.', False), ('forward-en', 'We expect subscription revenue of USD 143 million in fiscal 2030.', 'The following revenue outlook assumes customers renew their subscriptions on time.', False))

ACTUAL = {"operating_quantity", "operating_metric_change", "business_revenue_measure",
          "operating_causal_driver", "product_operating_driver"}


@pytest.mark.parametrize("name,text,expected", MEASURE, ids=[x[0] for x in MEASURE])
def test_source_measure_owns_its_actual_or_future_predicate(name, text, expected):
    fact = policy.detect_reading_business_fact(text)
    assert bool(ACTUAL.intersection(fact.reasons)) is expected


@pytest.mark.parametrize("name,text,expected", GUIDANCE, ids=[x[0] for x in GUIDANCE])
def test_source_revenue_owns_its_forward_predicate_and_measured_period(name, text, expected):
    assert guidance.revenue_guidance(text) is expected
    fact = policy.detect_reading_business_fact(text)
    assert ("source_revenue_guidance" in fact.reasons) is expected
    parsed = _source([HEADING, text])
    selected = _select(parsed)
    spans = _spans_for(selected, parsed.units[1])
    assert any("source_revenue_guidance" in span.structured_value["selection_reasons"] for span in spans) is expected


@pytest.mark.parametrize("name,text,premise,expected", PAIRS, ids=[x[0] for x in PAIRS])
def test_issuer_guidance_reference_closes_only_the_actual_source_scope(name, text, premise, expected):
    parsed = _source([HEADING, text, premise])
    selected = _select(parsed)
    support = {span.span_id for span in _spans_for(selected, parsed.units[1])}
    context = {span.span_id for span in _spans_for(selected, parsed.units[2])}
    view, _ = _model(selected)
    tasks = [task for task in view.plan.tasks if support.intersection(task.support_ids)]
    actual = bool(tasks) and all(bool(context.intersection(task.member_ids)) for task in tasks)
    assert actual is expected
