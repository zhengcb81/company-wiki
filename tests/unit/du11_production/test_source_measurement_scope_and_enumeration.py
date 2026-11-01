"""A weak cause recognizer cannot erase a separately observed source payload.

These use the actual shared source owner, not company names, requested summary
answers, numeric thresholds, injected role proofs or a permissive consumer.
"""
import pytest

from company_wiki.document_understanding.operating_states.assertion_roles import (
    prepare_source_assertions,
)
from company_wiki.source_catalog.narrative_business_disclosures import (
    reading_material_value,
)
from company_wiki.source_catalog.narrative_business_policy import (
    prepare_reading_business_assessment,
)
from unit.du11_production.test_source_information_binding import session_for, unit_id


@pytest.mark.parametrize("text", (
    "得益于工艺升级、队列向后期推进，2026年上半年精密材料业务收入人民币12.3亿元，同比增长22.4%。",
    "得益于业务模式引流项目、管线向后期推进及前瞻性产能布局，精密材料业务收入人民币12.3亿元，同比增长22.4%。",
    "ii.\n得益于业务模式引流项目、管线向后期推进及前瞻性产\n能布局，精密材料业务收入人民币12.3\n亿元，同比增长22.4%。",
))
def test_explicit_business_measure_survives_unproven_causal_prelude(text):
    session, budget = session_for([text])
    uid = unit_id(0)
    fact = session.fact(uid)
    passage = session.source_passage(uid)
    assert fact.eligible and "business_revenue_measure" in fact.reasons
    assert passage.use == "support" and passage.relevant
    assert session.source_text(uid) == text
    # Reading a cached source assessment must not charge another full pass.
    used = budget.used
    assert session.fact(uid) is fact
    assert session.source_passage(uid) is passage
    assert budget.used == used


def test_revenue_fact_does_not_manufacture_a_causal_proof(monkeypatch):
    from company_wiki.source_catalog import narrative_business_policy as policy

    original = policy.prepare_source_statement_scope
    scopes = []

    def observe(*args, **kwargs):
        result = original(*args, **kwargs)
        scopes.append(result)
        return result

    monkeypatch.setattr(policy, "prepare_source_statement_scope", observe)
    monkeypatch.setattr(policy, "_observed_causal_relation", lambda *_, **__: False)
    text = "得益于未核实的因素，精密材料业务收入人民币12.3亿元，同比增长22.4%。"
    result = prepare_reading_business_assessment(text, {"relations": []})
    assert result.fact.eligible and "business_revenue_measure" in result.fact.reasons
    assert result.passage.use == "support"
    assert len(scopes) == 1
    assert not scopes[0].business_causal_keys
    assert len(scopes[0].text) == len(text)


def test_scope_and_fact_reuse_the_same_metric_observation(monkeypatch):
    from company_wiki.source_catalog import narrative_business_policy as policy

    original = policy._source_metric_relations
    calls = []

    def observe(clause, **kwargs):
        calls.append(clause)
        return original(clause, **kwargs)

    monkeypatch.setattr(policy, "_source_metric_relations", observe)
    text = "得益于未核实的因素，精密材料业务收入人民币12.3亿元，同比增长22.4%。"
    result = prepare_reading_business_assessment(text, {"relations": []})
    assert result.passage.use == "support"
    assert calls.count(text[:-1]) == 1


@pytest.mark.parametrize("text", (
    "得益于会计估计变更，公司净利润为人民币12.3亿元，同比增长22.4%。",
    "因为财务表现良好，公司营业利润增长22.4%。",
    "Operating income rose 8% because of excellent financial performance.",
    "请问精密材料业务收入人民币12.3亿元，同比增长22.4%吗？",
    "模板示例：精密材料业务收入人民币12.3亿元，同比增长22.4%。",
))
def test_nonbusiness_results_and_nonassertions_do_not_gain_fact_support(text):
    result = prepare_reading_business_assessment(text, {"relations": []})
    assert result.passage.use != "support" and not result.passage.relevant


@pytest.mark.parametrize("text", (
    "公司的服务覆盖铸造、研磨与涂层。",
    "公司的服务涵盖口服及注射剂。",
    "Our services cover miralon, tressiq and zovren.",
    "Our services include forging, polishing and coating.",
    "公司提供端到端服务，涵盖铸造及涂层。",
    "Our services, cover miralon, tressiq and zovren.",
))
def test_closed_named_service_scope_has_material_payload_without_a_type_dictionary(text):
    roles = prepare_source_assertions(text)
    assert roles.independent_payload is True
    assert any(clause.material_payload for clause in roles.clauses)
    session, _ = session_for([text])
    uid = unit_id(0)
    assert session.source_passage(uid).use == "support"
    assert reading_material_value(session.fact(uid), source_roles=session.source_assertions(uid)) == "meaningful_fact"
    assert session.source_text(uid) == text


@pytest.mark.parametrize("text", (
    "公司的服务覆盖高质量发展与美好未来。",
    "Our services cover value and success.",
    "公司的服务覆盖铸造、",
    "Our services cover miralon, tressiq and",
    "公司的服务覆盖煅烧、压延和烧结，并",
    "Our services cover miralon, while",
    "Our services cover miralon, tressiq while",
    "Our services cover miralon, tressiq...",
    "Our services cover miralon, Riverton is unavailable.",
    "公司的服务覆盖煅烧，远山公司尚未答复。",
))
def test_abstract_or_unclosed_service_list_does_not_supply_member_identity(text):
    roles = prepare_source_assertions(text)
    assert roles.independent_payload is not True
    assert not any(clause.material_payload for clause in roles.clauses)


@pytest.mark.parametrize("text", (
    "模板示例：公司的服务覆盖铸造、研磨与涂层。",
    "请问公司的服务是否覆盖铸造、研磨与涂层？",
))
def test_named_members_cannot_turn_a_template_or_question_into_current_service_scope(text):
    result = prepare_reading_business_assessment(text, {"relations": []})
    assert result.passage.use != "support" and not result.passage.relevant


@pytest.mark.parametrize("text", (
    "注：上表中单项之和与合计不等为四舍五入造成。",
    "由于四舍五入，本表各项加总与总数可能存在差异。",
    "Figures in this table may not sum to the total due to rounding.",
    "Due to rounding, the amounts shown may not add to the total.",
))
def test_arithmetic_presentation_note_is_context_not_a_business_quote(text):
    result = prepare_reading_business_assessment(text, {"relations": []})
    assert result.passage.use == "context_only"
    assert not result.passage.relevant


@pytest.mark.parametrize("text", (
    "Our software processes reports whose totals differ because of rounding.",
    "Tables software processes reports whose totals differ because of rounding.",
    "The figures our software processes may differ in the totals due to rounding.",
    "Figures may not sum to totals due to rounding, and our services cover miralon and zovren.",
    "注：上表各项加总有四舍五入差异，公司已经完成工厂建设。",
))
def test_real_business_proof_is_not_erased_by_rounding_vocabulary(text):
    session, _ = session_for([text])
    passage = session.source_passage(unit_id(0))
    assert passage.use == "support" and passage.relevant
