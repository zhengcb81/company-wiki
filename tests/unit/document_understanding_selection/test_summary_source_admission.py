"""Source admission/value and reference closure before summary presentation.

Neutral in-memory sources; no PDF parser, model, catalog, or paid transport.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
from company_wiki.source_catalog.narrative_antecedent import build_antecedent_windows
from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
from unit.document_understanding_selection.test_reading_native_carriers import source_fixture


UNKNOWN = {"relations": [{"polarity": "positive", "stage": "unknown",
    "attribution": "unknown", "modality": "uncertain", "activity": "production"}]}


@pytest.mark.parametrize("text", (
    "Revenue increased by 12% during the reporting period.",
    "本期营业收入增长12%。",
    "本期營業收入增長12%。",
))
def test_unbound_unknown_state_cannot_manufacture_operating_eligibility(text):
    fact = policy.project_reading_business_fact(text, UNKNOWN, description=OperatingFact())
    # Raw readability is owned by original storage. Arbitrary serialized state
    # metadata has no typed source proof and cannot create a business offer.
    plain = policy.project_reading_business_fact(text, {"relations": []}, description=OperatingFact())
    assert fact == plain
    assert not fact.eligible and "operating_state_unknown" not in fact.reasons
    assert not fact.financial_exempt
    assert policy.reading_material_value(fact) == "description"


@pytest.mark.parametrize("reason", ("operating_state_unknown", "operating_description_unknown"))
def test_unresolved_grammar_is_not_scarce_material_even_with_a_legacy_score(reason):
    unknown = OperatingFact(True, ("core_business",), (reason,), 3)
    assert policy.reading_material_value(unknown) == "description"
    specific = replace(unknown, reasons=(reason, "business_revenue_measure"))
    assert policy.reading_material_value(specific) == "meaningful_fact"


@pytest.mark.parametrize("text", (
    "本期淨虧損為人民幣93百萬元。",
    "本期净亏损为人民币93百万元。",
    "Net loss was USD 12 million.",
    "經營虧損為人民幣163.2百萬元。",
    "Operating loss was USD 24 million.",
    "销售费用为人民币123百万元。",
    "融資活動所得現金淨額\n1,234\n2,345\n337",
    "經調整淨虧損（非公認會計準則財務指標）",
    "Adjusted EBITDA (non-GAAP financial measure)",
    "償還短期借款\n(71,200)\n(83,100)\n(11,800)",
    "Repayment of short-term borrowings\n(71,200)\n(83,100)\n(11,800)",
))
def test_source_financial_totals_and_labels_do_not_enter_business_tasks(text):
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, _ = reading._candidates(parsed, pipeline)
    assert not {uid for uid, row in metadata.items() if not row.get("context_only")}
    assert not packages


@pytest.mark.parametrize("text", (
    "截至报告期末，研发人员达1,237人。",
    "截至報告期末，研發人員達1,237人。",
    "At period end, our R&D team numbered 1,237 employees.",
    "報告期內，研發費用為人民幣37.2百萬元；截至六月三十日，研發人員達1,237人。",
    "展望下半年，我們將持續投資技術研發，全面提升AI能力。",
    "In the second half we will continue investing in research and development and enhance our AI capabilities.",
    "本期毛利率下降主要是由于服务器成本增加，以支持AI业务扩张。",
    "Regional earnings rose due to higher unit volumes and improved capacity utilization.",
    "來自行業雲服務的收入為人民幣2,140.4百萬元，較上年同期人民幣1,945.4百萬元增加10%。"
    "該同比增加主要是由於不斷增長的IT需求及我們向垂直行業客戶複製行業解決方案的能力。",
))
def test_complete_resources_plans_segment_revenue_and_financial_note_business_causes_survive(text):
    parsed, pipeline = source_fixture([(text,)])
    _, metadata, packages, _, withheld = reading._candidates(parsed, pipeline)
    assert any(not row.get("context_only") for row in metadata.values()), withheld
    assert packages
    assert any(row.get("value_band") == "meaningful_fact" for row in metadata.values())


def reference_case(texts, *, other_source=False, other_section=False, gap=False):
    parsed, pipeline = source_fixture([(text,) for text in texts])
    ids = [u.unit_id for u in parsed.units]
    if other_source:
        parsed = replace(parsed, units=(replace(parsed.units[0], source_id="different-source"), *parsed.units[1:]))
    if other_section:
        pipeline["structure"]["sections"] = [
            {"section_id": "first", "body_unit_ids": ids[:-1]},
            {"section_id": "second", "body_unit_ids": ids[-1:]},
        ]
    if gap:
        parsed = replace(parsed, units=(*parsed.units[:-1], replace(parsed.units[-1],
            coordinates=replace(parsed.units[-1].coordinates, paragraph_index=99))))
    windows = build_antecedent_windows(parsed, pipeline, prose_unit_ids=set(ids),
                                       require_adjacency_proof=True)
    session = SourceOperatingSession({u.unit_id: u for u in parsed.units},
        work_budget=WorkBudget(100000),
        antecedents={uid: (row["predecessor_unit_ids"], row["complete"])
                     for uid, row in windows.items()})
    return session, ids


@pytest.mark.parametrize("text", (
    "有关增加主要由于客户需求增长。",
    "有關增加主要由於客戶需求增長。",
    "This increase was primarily due to higher customer demand.",
))
def test_orphan_causal_result_requires_a_source_antecedent(text):
    session, ids = reference_case([text])
    assert session.reference(ids[-1])["status"] in {"missing", "partial"}


@pytest.mark.parametrize("before,after", (
    ("本公司云服务收入同比增加12%。", "有关增加主要由于客户需求增长。"),
    ("本公司雲服務收入同比增加12%。", "有關增加主要由於客戶需求增長。"),
    ("Our cloud service revenue increased by 12%.", "This increase was due to higher customer demand."),
    ("Our paid subscribers increased to 2,370.", "This increase was due to higher customer demand."),
    ("本公司客户数量增加至2,370家。", "有关增加主要由于客户需求增长。"),
))
def test_one_observed_adjacent_result_keeps_its_original_support(before, after):
    session, ids = reference_case([before, after])
    result = session.reference(ids[-1])
    assert result["status"] == "unique"
    assert result["required_original_unit_ids"] == (ids[0],)
    assert {ref["unit_id"] for ref in result["declaration_refs"]} == {ids[0]}


@pytest.mark.parametrize("changes", ({"other_source": True}, {"other_section": True}, {"gap": True}))
def test_causal_result_cannot_borrow_across_unproved_source_boundaries(changes):
    session, ids = reference_case([
        "Our cloud service revenue increased by 12%.",
        "This increase was due to higher customer demand.",
    ], **changes)
    result = session.reference(ids[-1])
    assert result["status"] in {"missing", "partial"}
    assert not result["required_original_unit_ids"]


@pytest.mark.parametrize("before", (
    "Our revenue increased by 12% and our costs increased by 8%.",
    "Our cloud service revenue may increase next year.",
    "Our cloud service revenue did not increase this year.",
    "Our cloud service revenue declined by 12%.",
))
def test_ambiguous_unobserved_or_opposite_result_never_donates_a_subject(before):
    session, ids = reference_case([before, "This increase was due to higher customer demand."])
    result = session.reference(ids[-1])
    assert result["status"] in {"missing", "partial", "ambiguous"}
    assert not result["required_original_unit_ids"]


def test_actual_source_selection_defers_orphan_result_without_rewriting_it():
    text = "有关增加主要由于经营亏损增加及利息费用增加。"
    parsed, pipeline = source_fixture([(text,)])
    original = parsed.units[0]
    _, metadata, packages, _, withheld = reading._candidates(parsed, pipeline)
    assert not packages and not metadata
    assert any(row["reason"] == "REFERENCE_UNRESOLVED" for row in withheld)
    assert parsed.units[0] == original


def test_actual_source_package_carries_result_subject_as_support_not_only_context():
    before = "本公司云服务收入同比增加12%。"
    after = "有关增加主要由于客户需求增长。"
    parsed, pipeline = source_fixture([(before,), (after,)])
    ids = [unit.unit_id for unit in parsed.units]
    _, _, packages, _, withheld = reading._candidates(parsed, pipeline)
    result_packages = [p for p in packages if ids[-1] in p.get("anchor_unit_ids", ())]
    assert result_packages, withheld
    assert all(any(set(ids) <= set(view) for view in p.get("citation_support_views", ()))
               for p in result_packages)
    assert all(ids[0] in p.get("required_context_unit_ids", ()) for p in result_packages)


@pytest.mark.parametrize("text", (
    "Our cloud service revenue increased by 12%. This increase was due to higher customer demand.",
    "The increase in our cloud service revenue was due to higher customer demand.",
))
def test_self_contained_result_is_not_forced_to_find_a_different_statement(text):
    session, ids = reference_case([text])
    assert session.reference(ids[-1])["status"] == "not_applicable"


def test_naked_direction_predicate_cannot_become_an_antecedent_subject():
    session, ids = reference_case(["Increased by 12%.", "This increase was due to higher customer demand."])
    result = session.reference(ids[-1])
    assert result["status"] == "missing"
    assert not result["required_original_unit_ids"]


@pytest.mark.parametrize("before", (
    "There was an increase of 12%.",
    "An increase of 12% was reported.",
    "It increased by 12%.",
    "本期同比增加12%。",
    "Our paid subscribers totaled 2,370. It increased by 12%.",
    "An increase of 12% was reported. Cloud service revenue is a glossary label.",
))
def test_frozen_review_unidentified_change_cannot_supply_a_result_subject(before):
    session, ids = reference_case([before, "This increase was due to higher customer demand."])
    result = session.reference(ids[-1])
    assert result["status"] in {"missing", "partial"}
    assert not result["required_original_unit_ids"]
    assert not result["support_original_unit_ids"]


@pytest.mark.parametrize("cause", (
    "該同比增加主要是由於擴展我們的雲服務。",
    "该环比增长主要由于增加云服务客户。",
    "This year-on-year increase was due to expanding our cloud services.",
))
def test_comparison_qualifier_does_not_turn_an_orphan_result_into_a_fact(cause):
    parsed, pipeline = source_fixture([("There was an increase of 12%.",), (cause,)])
    _, _, packages, _, withheld = reading._candidates(parsed, pipeline)
    uid = parsed.units[-1].unit_id
    assert not [p for p in packages if uid in p.get("anchor_unit_ids", ())]
    assert any(row["reason"] == "REFERENCE_UNRESOLVED" for row in withheld)


@pytest.mark.parametrize("cause", (
    "該同比增加主要是由於擴展我們的雲服務。",
    "该环比增长主要由于增加云服务客户。",
    "This year-on-year increase was due to expanding our cloud services.",
))
def test_comparison_qualified_result_keeps_the_same_source_subject_contract(cause):
    session, ids = reference_case(["Our cloud service revenue increased by 12%.", cause])
    result = session.reference(ids[-1])
    assert result["status"] == "unique"
    assert result["support_original_unit_ids"] == (ids[0],)


@pytest.mark.parametrize("before,cause,closes", (
    ("Our cloud service revenue increased by 12% year-over-year.",
     "This quarter-over-quarter increase was due to higher customer demand.", False),
    ("Our cloud service revenue declined by 12% quarter-over-quarter.",
     "This year-over-year decline was due to lower customer demand.", False),
    ("Our cloud service revenue increased by 12% year-over-year.",
     "This year-on-year increase was due to higher customer demand.", True),
    ("The glossary mentions year-on-year trends. Our cloud service revenue increased by 12% quarter-over-quarter.",
     "This qoq increase was due to higher customer demand.", True),
    ("Our cloud service revenue increased by 12% quarter-over-quarter.",
     "This qoq increase was due to higher customer demand. The glossary mentions year-over-year trends.", True),
))
def test_result_comparison_identity_is_bound_to_the_direction_assertion(before, cause, closes):
    session, ids = reference_case([before, cause])
    result = session.reference(ids[-1])
    if closes:
        assert result["status"] == "unique"
        assert result["support_original_unit_ids"] == (ids[0],)
    else:
        assert result["status"] in {"missing", "partial", "ambiguous"}
        assert not result["support_original_unit_ids"]
