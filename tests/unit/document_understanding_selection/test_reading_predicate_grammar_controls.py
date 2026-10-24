"""Predicate grammar controls: measured nouns and explicit hypotheses.

These assertions retain source text only; no order/project counts, financial
values, periods or actual achievements are manufactured by classification.
"""
from __future__ import annotations

import pytest

from company_wiki.source_catalog.narrative_business_policy import _source_measure_relations
from company_wiki.source_catalog.narrative_predicate_state import observe_metric_predicate


def observation(text: str, target: str):
    start = text.rindex(target)
    return observe_metric_predicate(text, start, start + len(target))


@pytest.mark.parametrize("text,target", [
    ("Our services revenue increased due to projects totaling 560 at year end.", "projects"),
    ("Our total project count stood at 240 during the year.", "project"),
    ("Our total project number stood at 240 during the year.", "project"),
    ("We served 240 projects during the year.", "projects"),
    ("Projects grew from 12 to 18 during the year.", "Projects"),
    ("The project has 619 customers.", "customers"),
])
def test_measured_project_noun_does_not_make_its_predicate_a_forecast(text, target):
    state = observation(text, target)
    assert state.observed
    assert not state.forward_outlook


@pytest.mark.parametrize("text,target", [
    ("We project that customers will reach 619 next year.", "customers"),
    ("Management projects 619 customers next year.", "customers"),
    ("Our company projects customer numbers of 619 next year.", "customer"),
    ("The company is projecting 619 customers next year.", "customers"),
    ("Our project will serve 619 customers next year.", "customers"),
    ("We project 619 customers.", "customers"),
    ("Management projects 619 new projects.", "projects"),
    ("Our company is projecting 619 projects.", "projects"),
])
def test_real_project_verb_and_future_auxiliary_keep_forward_modality(text, target):
    state = observation(text, target)
    assert not state.observed
    assert state.forward_outlook
    assert not _source_measure_relations(text)


@pytest.mark.parametrize("text,target", [
    ("Our service revenue grew due to an assumption that we have 619 customers.", "customers"),
    ("Assuming we have 619 customers, our services could grow.", "customers"),
    ("On the assumption that customers total 619, our service revenue would grow.", "customers"),
    ("This scenario uses an assumption of 619 customers.", "customers"),
])
def test_explicit_hypothesis_is_not_an_observed_customer_stock(text, target):
    state = observation(text, target)
    assert not state.observed
    assert state.has_condition or state.modality == "uncertain"
    assert not _source_measure_relations(text)


@pytest.mark.parametrize("text", [
    "We rejected an assumption that orders might fall, customers reached 619.",
    "The report explains assumptions. Customers reached 619.",
    "If the project succeeds, customers will reach 619 next year.",
    "In this scenario, under the assumption that orders stay stable, customers total 619.",
])
def test_hypothesis_scope_cannot_leak_between_independent_assertions(text):
    target = "Customers" if "Customers" in text else "customers"
    state = observation(text, target)
    if text.startswith("If"):
        assert not state.observed and state.forward_outlook and state.has_condition
    elif text.startswith("In this scenario"):
        assert not state.observed and state.has_condition
    else:
        assert state.observed and not state.has_condition
