"""Frozen pre-implementation bilingual expectations plus independent counterexamples."""
import gzip
import json
from pathlib import Path

import pytest

from unit.du11_production.test_source_information_binding import session_for, unit_id, observed_use


_CASES_PATH = (Path(__file__).resolve().parents[3] /
    "docs/plans/du11-source-closure-2026-10-18/review/pdf-c3-20261026/evidence/"
    "pause-closeout-20261028/source-specificity-design/cases.json.gz")
_CASES = json.loads(gzip.decompress(_CASES_PATH.read_bytes()))


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case["id"])
def test_frozen_bilingual_information_contract(case):
    session, _ = session_for([case["text"]])
    assert observed_use(session, unit_id(0))[0] == case["expected_use"], case["why"]


@pytest.mark.parametrize("repeats", [1, 5])
def test_bounded_argument_cannot_certify_unread_tail_as_generic(repeats):
    text = ("Our software supports " +
            "customer engagement and business development and digital transformation and customer satisfaction and " * repeats +
            "order processing.")
    session, _ = session_for([text])
    assert session.source_assertions(unit_id(0)).independent_payload is not False
    assert observed_use(session, unit_id(0))[1] != "source_generic_objective"
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence
    parsed, _ = source_fixture([(text,)])
    selected = select_reading_evidence(parsed, title="Business review", existing_kind="semi_annual_report")
    assert selected.status != "skipped_no_narrative"


def test_restricted_cash_collateral_purpose_is_not_plain_cash_background():
    text = "本集团受限制现金主要指就担保若干银行贷款抵押的现金及若干应付供应商款项。"
    session, _ = session_for([text])
    assert observed_use(session, unit_id(0))[0] == "support"


def test_goal_inflections_are_planned_in_the_shared_predicate_owner():
    from company_wiki.source_catalog.narrative_predicate_state import observe_metric_predicate
    for cue in ("aim", "aims", "aimed", "aiming"):
        text = f"We are {cue} to improve production volumes."
        start = text.index("improve")
        observed = observe_metric_predicate(text, start, start+len("improve"))
        assert observed.modality == "planned" and not observed.observed


@pytest.mark.parametrize("suffix", ["订单处理业务。", "尚未理解的技术业务。"])
def test_bounded_cn_scope_cannot_certify_unread_tail_as_generic(suffix):
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence
    text = "本公司主要从事" + "产品及服务" * 20 + suffix
    session, _ = session_for([text])
    assert session.source_assertions(unit_id(0)).independent_payload is not False
    parsed, _ = source_fixture([(text,)])
    assert select_reading_evidence(parsed, title="Business review").status != "skipped_no_narrative"


def test_actual_current_financing_terms_do_not_require_a_new_signing_event():
    text = "Our term loans bear fixed interest and are secured by machinery used in production."
    session, _ = session_for([text])
    assert observed_use(session, unit_id(0))[0] == "support"


def test_production_of_financial_statements_is_not_a_physical_operating_effect():
    text = "Restrictions delayed production of the annual financial statements."
    session, _ = session_for([text])
    assert session.source_assertions(unit_id(0)).independent_payload is not True
    assert observed_use(session, unit_id(0))[0] != "support"


def test_financial_governing_object_cannot_borrow_abstract_purpose_metric():
    session, _ = session_for(["Our platform supports service costs to improve customer engagement."])
    assert observed_use(session, unit_id(0))[0] != "support"
    assert session.source_assertions(unit_id(0)).independent_payload is not True
    assert not session.fact(unit_id(0)).financial_exempt


def test_prepared_purpose_controls_its_metrics_without_changing_main_assertion():
    from company_wiki.source_catalog.narrative_predicate_state import prepare_predicate_context
    text = "Orders grew to 40 units to improve customer engagement."
    prepared = prepare_predicate_context(text)
    for token, expected in [("Orders", "actual"), ("customer", "planned")]:
        start = text.index(token)
        assert prepared.observe(start, start+len(token)).modality == expected
    actual = "We continued to improve customer engagement."
    start = actual.index("customer")
    assert prepare_predicate_context(actual).observe(start, start+len("customer")).observed
    causal = "Our services revenue increased due to lower pricing."
    start = causal.index("pricing")
    assert prepare_predicate_context(causal).observe(start, start+len("pricing")).observed
