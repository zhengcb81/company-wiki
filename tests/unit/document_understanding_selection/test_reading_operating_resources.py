"""Source-owned resources and plans, without market or document exceptions."""
from dataclasses import replace
from pathlib import Path

import pytest

from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog import narrative_reading as reading
from unit.document_understanding_selection.test_reading_native_carriers import source_fixture, selected


ACTUAL = {"operating_resource_stock", "operating_resource_allocation"}
NEW = ACTUAL | {"operating_plan"}


def project(text):
    return policy.project_reading_business_fact(text, {"relations": []})


STOCKS = (
    "截至报告期末，研发人员达1,237人。",
    "截至報告期末，研發人員達1,237人。",
    "截至上年末，研发中心员工总数（包括实习生和外包员工）已超过730人。",
    "At period end, our R&D team numbered 1,237 employees.",
    "Our research and development staff totaled 1,237 people at June 30.",
    "Our R&D staff count was 1,237 employees.",
    "We employed 1,237 software engineers at June 30.",
)
ALLOCATIONS = (
    "本期投入人民币37.2百万元用于技术研发。",
    "本期研發投入為人民幣37.2百萬元，主要用於研發平台建設。",
    "We invested USD 37.2 million in research and development during the period.",
)
PLANS = (
    "展望下半年，我们将持续投入技术研发，提升人工智能能力。",
    "展望下半年，我們將維持高質量發展戰略，不斷投資技術研發，並全面提升AI能力。",
    "In the second half we will continue investing in research and development and enhance our AI capabilities.",
    "We plan to allocate more resources to research and development next year.",
    "公司计划明年研发人员达到1,237人。",
    "We expect our research staff to reach 1,237 people next year.",
)


@pytest.mark.parametrize("text", STOCKS)
def test_actual_workforce_has_its_own_measured_subject_and_topic(text):
    fact = project(text)
    assert fact.eligible and "operating_resource_stock" in fact.reasons
    assert "operating_resources" in fact.topics
    assert "operating_plan" not in fact.reasons
    assert policy.reading_material_value(fact) == "meaningful_fact"


@pytest.mark.parametrize("text", ALLOCATIONS)
def test_allocation_needs_explicit_resource_use_not_an_expense_line(text):
    fact = project(text)
    assert "operating_resource_allocation" in fact.reasons
    assert "research_investment" in fact.topics


@pytest.mark.parametrize("text", PLANS)
def test_concrete_resource_plan_never_becomes_actual_stock_or_spend(text):
    fact = project(text)
    assert fact.eligible and "operating_plan" in fact.reasons
    assert "operating_plan" in fact.topics
    assert not ACTUAL.intersection(fact.reasons)
    assert policy.reading_material_value(fact) == "meaningful_fact"


@pytest.mark.parametrize("text", (
    "研发费用37.2百万元。",
    "Research and development expenses were USD 37.2 million.",
    "研发费用按照会计政策计入损益，金额为人民币37.2百万元。",
    "Research and development investment is capitalized under the accounting policy.",
    "Employee benefit liabilities were USD 37.2 million.",
    "研发人员培训手册第1237条介绍人工智能业务。",
    "Research staff training manual 1237 describes artificial intelligence services.",
    "研发人员是指参与研发活动的人；例如一家公司有1,237人。",
    "We are committed to sustainable development and creating value for all stakeholders.",
    "我们坚持高质量发展，为客户、股东、员工和社会创造价值。",
    "Our service platform aims to improve customer efficiency and reduce customer costs.",
    "If our R&D staff reaches 1,237 people, our costs may change.",
    "如果研发人员达到1,237人，费用可能变化。",
    "公司尚未将研发人员增加至1,237人。",
    "Our research staff did not reach 1,237 people.",
    "Will you increase R&D staff to 1,237 people next year?",
    "请问公司下半年是否计划增加研发人员至1,237人？",
    "Our research staff pension assets were USD 37.2 million.",
    "公司研发团队2027年度培训活动介绍。",
    "研发团队有很多经验，客户人数达到1,237人。",
    "We will publish our research staff count of 1,237 people.",
))
def test_financial_generic_question_and_unrealized_text_gets_no_new_resource_fact(text):
    fact = project(text)
    assert not NEW.intersection(fact.reasons)


@pytest.mark.parametrize("language,regime,family", (
    ("zh", "cninfo", "annual"), ("zh", "hkex", "interim"),
    ("en", "sec", "annual"), ("en", "sec", "quarterly"),
    ("zh", "cninfo", "investor_relations"), ("en", "sec", "transcript"),
))
def test_production_native_projection_uses_source_meaning_not_market_labels(language, regime, family):
    text = STOCKS[3] if language == "en" else STOCKS[0]
    parsed, pipeline = source_fixture([(text,)])
    parsed = replace(parsed, language=language, units=tuple(replace(u, language=language) for u in parsed.units))
    before = tuple(u.to_evidence_span(topics=(), selection_reasons=()) for u in parsed.units)
    for row in pipeline["reading_plan"]["unit_profiles"].values():
        row.update(regime=regime, family=family)
    candidates, metadata, _, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and len(candidates) == 1
    value = metadata[candidates[0].unit.unit_id]
    assert value["value_band"] == "meaningful_fact"
    assert "operating_resources" in value["topics"]
    assert before == tuple(u.to_evidence_span(topics=(), selection_reasons=()) for u in parsed.units)


def test_closed_native_paragraph_retains_dual_currency_persons_and_plan_qualifiers():
    bodies = [
        ("本期研发费用为人民币37.2百万元（5.1百万美元），", "截至报告期末，研发人员达1,237人。"),
        ("展望下半年，我们将持续投入技术研发，", "并提升人工智能能力。"),
    ]
    parsed, pipeline = source_fixture(bodies)
    candidates, metadata, _, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld and len(candidates) == 2
    assert all(metadata[c.unit.unit_id]["value_band"] == "meaningful_fact" for c in candidates)
    result = selected(parsed, pipeline, candidates, metadata, limit=2)
    assert [s.raw_text for s in result.evidence_spans] == ["\n".join(parts) for parts in bodies]
    assert sum(len(s.raw_text) for s in result.evidence_spans) == sum(len("\n".join(parts)) for parts in bodies)
    assert not selected(parsed, pipeline, candidates, metadata, limit=1, max_chars=3).evidence_spans


def test_source_proven_resource_and_plan_topics_survive_crowded_details_without_cap_change():
    noise = [f"本期客户数量达到{100+i}家。" for i in range(12)]
    bodies = [(text,) for text in (*noise, STOCKS[0], PLANS[0])]
    parsed, pipeline = source_fixture(bodies)
    candidates, metadata, _, complete, withheld = reading._candidates(parsed, pipeline)
    assert complete and not withheld
    result = selected(parsed, pipeline, candidates, metadata, limit=3)
    assert {STOCKS[0], PLANS[0]} <= {s.raw_text for s in result.evidence_spans}
    assert len(result.evidence_spans) == 3
    assert reading.READING_BUDGET_POLICY == "reading_plan/3" and reading.MAX_READING_CHARS == 48000


def test_new_production_meaning_does_not_change_legacy_text_projection():
    for text in (*STOCKS, *ALLOCATIONS, *PLANS):
        assert not ACTUAL.intersection(policy.detect_reading_business_fact(text).reasons)
    assert not policy.detect_reading_business_fact(STOCKS[0]).eligible
    assert not policy.detect_reading_business_fact(PLANS[1]).eligible


@pytest.mark.parametrize("text,expected", (
    ("We plan to maintain quality, and invest in research and development.", True),
    ("We plan to maintain quality, but invest in research and development.", False),
    ("公司尚未确定计划，持续投入技术研发。", False),
    ("If customers renew, we plan to invest in research and development next year.", True),
))
def test_plan_frame_is_local_to_a_concrete_coordinated_action(text, expected):
    fact = project(text)
    assert ("operating_plan" in fact.reasons) is expected
    assert not ACTUAL.intersection(fact.reasons)


def test_new_actor_retains_its_actual_resource_instead_of_borrowing_a_plan():
    text = "We plan to maintain quality, but our supplier invested USD 21 million in research and development."
    fact = project(text)
    assert "operating_resource_allocation" in fact.reasons
    assert "operating_plan" not in fact.reasons
    parsed, pipeline = source_fixture([(text,)])
    candidates, metadata, _, _, _ = reading._candidates(parsed, pipeline)
    result = selected(parsed, pipeline, candidates, metadata, limit=1)
    assert [s.raw_text for s in result.evidence_spans] == [text]


@pytest.mark.parametrize("prefix", (
    "公司会计政策规定研发费用计入损益。",
    "Will you invest in research and development? ",
))
def test_separate_question_or_policy_does_not_erase_an_independent_resource_sentence(prefix):
    assert "operating_resource_stock" in project(prefix + STOCKS[0]).reasons


@pytest.mark.parametrize("role", ("analyst", "investor_question", "operator"))
def test_source_context_roles_cannot_assert_a_company_resource(role):
    parsed, pipeline = source_fixture([(STOCKS[0],)])
    parsed = replace(parsed, units=tuple(replace(u, source_role=role) for u in parsed.units))
    for row in pipeline["observation"]["units"]:
        row["role"] = role
    candidates, _, _, _, _ = reading._candidates(parsed, pipeline)
    assert not candidates


def test_work_exhausted_projection_does_not_restart_resource_scanning(monkeypatch):
    from company_wiki.source_catalog import narrative_operating_resources as resources
    def forbidden(*args, **kwargs):
        raise AssertionError("work-exhausted fallback must not restart source scans")
    monkeypatch.setattr(resources, "operating_resource_relations", forbidden)
    fact = policy.project_reading_business_fact(STOCKS[0], {"relations": []}, include_description=False)
    assert not fact.eligible


def test_new_resource_dependency_is_bound_to_current_decision_inventory(monkeypatch):
    from company_wiki.document_understanding import decision_inventory
    from company_wiki.source_catalog import narrative_operating_resources as resources
    before = decision_inventory._versions()
    original = Path.read_bytes
    resource_path = Path(resources.__file__).resolve()
    def changed(path):
        data = original(path)
        return data + b"\n# independent semantic rule change\n" if path.resolve() == resource_path else data
    monkeypatch.setattr(Path, "read_bytes", changed)
    assert decision_inventory._versions() != before


@pytest.mark.parametrize("text", (
    "We have no plans to invest in research and development.",
    "We have no current plans to invest in research and development.",
    "公司暂无计划投入技术研发。",
    "公司不计划投资技术研发。",
    "本集團暫無計劃投資技術研發。",
    "We will not invest USD 4 million in research and development.",
    "公司尚未确定计划投入技术研发。",
))
def test_negated_plan_never_asserts_positive_resource_or_plan(text):
    assert not (ACTUAL | {"operating_plan"}).intersection(project(text).reasons)


@pytest.mark.parametrize("text", (
    "Our research staff will number 2,400 people next year.",
    "Our R&D staff will reach 2,400 employees next year.",
    "公司研发人员将达到2,400人。",
    "本集團研發人員將達到2,400人。",
    "We expect our research staff to reach 2,400 people next year.",
))
def test_explicit_future_headcount_is_plan_only(text):
    fact = project(text)
    assert "operating_plan" in fact.reasons
    assert not ACTUAL.intersection(fact.reasons)


def test_negative_actor_does_not_poison_separate_actual_resource():
    text = ("We have no plans to invest in research and development, "
            "but our supplier employed 2,400 research engineers.")
    fact = project(text)
    assert "operating_resource_stock" in fact.reasons
    assert "operating_plan" not in fact.reasons
