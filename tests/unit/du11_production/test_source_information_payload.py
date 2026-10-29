"""Prepared information content is separate from grammatical completeness."""
import pytest

from company_wiki.document_understanding.operating_states.assertion_roles import prepare_source_assertions
from company_wiki.source_catalog.narrative_support_use import source_narrative_relevance
from company_wiki.source_catalog.narrative_business_disclosures import reading_material_value
from unit.du11_production.test_source_information_binding import session_for, unit_id, observed_use


@pytest.mark.parametrize("text", (
    "Our software supports customer engagement.",
    "Our platform supports business development and innovation.",
    "我们持续以丰富的产品及优质的服务支持行业的数字化转型升级。",
    "我们的技术平台作为产品开发和创新的基础。",
))
def test_complete_abstract_objective_is_observed_as_no_independent_payload(text):
    roles = prepare_source_assertions(text)
    assert roles.operating  # complete grammar remains complete
    assert roles.independent_payload is False
    session, _ = session_for([text])
    assert observed_use(session, unit_id(0))[0] == "context_only"
    prepared = session.source_assertions(unit_id(0))
    fact = session.fact(unit_id(0))
    assert prepared.independent_payload is False
    assert not source_narrative_relevance(fact=fact, source_roles=prepared)
    assert reading_material_value(fact, source_roles=prepared) == "description"


@pytest.mark.parametrize("text", (
    "Our software supports customer order processing.",
    "Our platform processes genomic sequencing workloads.",
    "Our equipment is used by hospitals to sterilise surgical tools.",
    "我们的软件支持客户订单处理。",
    "本公司的服务范围包括远程工厂维护。",
    "本公司已与客户签订供货合同。",
    "We signed a supply agreement with Northwind.",
    "本公司的设备尚未完成客户认证。",
    "未来公司计划建设新的服务平台。",
    "本集团签订固定利率贷款协议，并以电子设备作为抵押。",
    "本集团主要从事提供云服务。",
    "本集团主要通过境外子公司开展业务。",
    "本公司目前并无涉及重大诉讼或仲裁。",
    "The group is not involved in material litigation.",
    "The solution's components are highly interdependent.",
))
def test_specific_function_plan_negative_contract_or_financing_retains_payload(text):
    session, budget = session_for([text])
    assert observed_use(session, unit_id(0))[0] == "support"
    roles = session.source_assertions(unit_id(0))
    assert roles.independent_payload is True, text
    assert source_narrative_relevance(fact=session.fact(unit_id(0)), source_roles=roles)
    assert reading_material_value(session.fact(unit_id(0)), source_roles=roles) == "meaningful_fact"
    charged = budget.used
    assert session.source_assertions(unit_id(0)) is roles
    assert observed_use(session, unit_id(0))[0] == "support"
    assert budget.used == charged


def test_unparsed_is_unknown_not_proved_boilerplate():
    roles = prepare_source_assertions("Novel technical disclosure awaiting interpretation.")
    assert roles.independent_payload is None


def test_real_function_after_generic_clause_is_not_lost_or_donated():
    generic = "Our software supports customer engagement."
    specific = "Our equipment is used by hospitals to sterilise surgical tools."
    session, _ = session_for([generic, specific, generic + " " + specific])
    assert session.source_assertions(unit_id(0)).independent_payload is False
    assert session.source_assertions(unit_id(1)).independent_payload is True
    assert session.source_assertions(unit_id(2)).independent_payload is True
    assert observed_use(session, unit_id(0))[0] == "context_only"
    assert observed_use(session, unit_id(2))[0] == "support"


def test_partial_unknown_tail_is_not_certified_as_all_generic():
    roles = prepare_source_assertions(
        "Our software supports customer engagement. Novel technical disclosure awaiting interpretation.")
    assert roles.independent_payload is None


@pytest.mark.parametrize("text,empty_outcome", (
    ("Our software supports customer engagement.", True),
    ("Novel technical disclosure awaiting interpretation.", False),
))
def test_only_proved_generic_full_document_may_skip(text, empty_outcome):
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    from company_wiki.source_catalog import narrative_reading as reading
    parsed, _ = source_fixture([(text,)])
    result = reading.select_reading_evidence(parsed, title="Business review", existing_kind="semi_annual_report")
    assert not result.evidence_spans
    assert (result.status == "skipped_no_narrative") is empty_outcome, result.status


def test_generic_cannot_occupy_the_business_slot_and_specific_function_is_meaningful():
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture, selected
    from company_wiki.source_catalog import narrative_reading as reading
    generic = "Our software supports customer engagement."
    specific = "Our software supports customer order processing."
    parsed, pipeline = source_fixture([(generic,), (specific,)])
    candidates, metadata, _, _, _ = reading._candidates(parsed, pipeline)
    anchors = [uid for uid, item in metadata.items() if not item.get("context_only")]
    assert anchors == [parsed.units[1].unit_id]
    assert metadata[anchors[0]]["value_band"] == "meaningful_fact"
    result = selected(parsed, pipeline, candidates, metadata, limit=1)
    assert [span.raw_text for span in result.evidence_spans] == [specific]


@pytest.mark.parametrize("text", (
    "Our software supports strategic aspirations.",
    "Our platform supports outstanding goals.",
    "我们的平台支持宏伟愿景。",
    "We provide best-in-class products.",
    "Our platform supports outstanding services.",
))
def test_unrecognised_function_target_does_not_become_positive_by_exclusion(text):
    session, _ = session_for([text])
    roles = session.source_assertions(unit_id(0))
    assert roles.operating
    assert roles.independent_payload is None
    assert observed_use(session, unit_id(0))[0] == "unresolved"
    assert reading_material_value(session.fact(unit_id(0)), source_roles=roles) == "description"
