"""Source-bound business scope, independent of issuer/product names or figures."""

import pytest

from company_wiki.source_catalog.narrative_business_policy import (
    detect_business_fact, detect_reading_business_fact,
)


@pytest.mark.parametrize("text", [
    "Our Research and Diagnostics segment consists of clinical instruments and technical support services.",
    "Our Managed Infrastructure segment comprises hosted computing, enterprise applications and support services.",
    "Our Consumer Experiences segment includes home devices, content subscriptions and online commerce.",
    "Our Agriculture segment included seed systems and crop advisory services during the comparative period.",
    "Our Advanced-Materials & Components segment will include sensor modules and customer-support services next year.",
    "The company's Commercial Operations segment comprises specialist distribution and aftermarket services.",
    "Our Connected Solutions segment does not include consumer devices; those products are reported separately.",
    "公司的智能服务分部包括算力服务与软件订阅业务。",
    "本集团数字产品分部由托管平台与技术支持业务组成。",
    "本集團企業解決方案分部包含託管服務及技術支援業務。",
    "本公司的醫療器械分部由診斷設備及耗材業務組成。",
])
def test_named_issuer_segment_has_a_real_business_composition_relation(text):
    before = text.encode()
    fact = detect_reading_business_fact(text)
    assert fact.eligible and fact.financial_exempt
    assert "business_reporting_scope" in fact.topics and "business_reporting_scope" in fact.reasons
    assert text.encode() == before


@pytest.mark.parametrize("text", [
    "We operate our business using four reportable segments: Diagnostics, Instruments, Data Services, and Field Support.",
    "We changed the composition of our reporting segments and moved customer-support services into Data Services.",
    "公司报告分部由设备、耗材和服务三个业务板块组成，比较期间按新分部口径重述。",
    "本集團報告分部由設備、耗材和服務三個業務板塊組成。",
])
def test_existing_source_reporting_scope_relationships_remain_meaningful(text):
    assert "business_reporting_scope" in detect_reading_business_fact(text).reasons


@pytest.mark.parametrize("text", [
    "A business segment consists of products with similar customers in a generic textbook example.",
    "In general, reportable segments comprise categories of revenue for accounting disclosure.",
    "A company's operating segment includes products with similar characteristics by definition.",
    "An operating segment is defined as a component that includes operations and financial information.",
    "业务板块是指由性质类似的产品与服务组成的通用分类。",
    "報告分部泛指由相似產品和服務組成的一般分類。",
])
def test_external_generic_definitions_are_not_issuer_reporting_scope(text):
    assert "business_reporting_scope" not in detect_reading_business_fact(text).reasons


@pytest.mark.parametrize("text", [
    "Our Research segment is named here. Elsewhere the glossary includes clinical products and technical services.",
    "Our Solutions segment is named here; a different company's operating segments comprise consumer products.",
    "Our Consumer segment was mentioned, while competitor segments include hosted computing services.",
    "We use our business glossary, which includes the word segments and the term commercial services.",
    "公司的智能服务分部在此列名。另一个章节包括其他产品与业务构成。",
    "本集團企業服務分部在此列名；外部報告分部包含一般產品分類。",
    "Our training guide says a reporting segment includes similar products and services.",
    "Our glossary defines business segments as categories that include products and services.",
    "公司资料说明报告分部由相似产品与服务组成的一般类别。",
])
def test_scope_and_relation_words_cannot_be_borrowed_from_another_subject_or_sentence(text):
    assert "business_reporting_scope" not in detect_reading_business_fact(text).reasons


@pytest.mark.parametrize("text", [
    "Our Cloud segment revenue increased to $12 billion and segment profit was $3 billion.",
    "Our Cloud segment includes revenue of $12 billion and profit of $3 billion.",
    "Our cash flow segment consists of financing cash movements and investing cash movements.",
    "Our tax segments include domestic tax accruals and foreign tax accruals.",
    "公司智能服务分部收入增长20%，分部利润为3亿元。",
    "公司的云服务分部包括营业收入12亿元和净利润3亿元。",
    "本集團稅項分部包含國內稅款及海外稅款。",
    "Our Cloud segment includes $12 billion of revenue and $3 billion of profit.",
    "公司的云服务分部包括12亿元营业收入和3亿元净利润。",
])
def test_financial_totals_are_not_business_composition(text):
    fact = detect_reading_business_fact(text)
    assert "business_reporting_scope" not in fact.reasons and not fact.financial_exempt


def test_new_segment_relation_does_not_modify_the_explicit_legacy_detector():
    text = "Our Research and Diagnostics segment consists of clinical instruments and technical support services."
    legacy = detect_business_fact(text)
    current = detect_reading_business_fact(text)
    assert "business_reporting_scope" not in legacy.reasons
    assert "business_reporting_scope" in current.reasons



def _explicit_scope_fixture(*, reverse=False):
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture

    scopes = ["（一）检测服务", "（二）技术服务"]
    if reverse:
        scopes.reverse()
    parsed, pipeline = source_fixture([
        (scopes[0],), ("新产品收入占比超过30%。",),
        (scopes[1],), ("新产品收入占比超过30%。",),
    ], heading=True)
    ids = [unit.unit_id for unit in parsed.units]
    for index in (1, 3):
        pipeline["observation"]["units"][index]["kind"] = "heading"
    pipeline["structure"]["sections"] = [
        {"section_id": "root", "parent_id": None,
         "heading_unit_ids": [ids[0]], "body_unit_ids": []},
        {"section_id": "scope-a", "parent_id": "root",
         "heading_unit_ids": [ids[1]], "body_unit_ids": []},
        {"section_id": "leaf-a", "parent_id": "scope-a",
         "heading_unit_ids": [], "body_unit_ids": [ids[2]]},
        {"section_id": "scope-b", "parent_id": "root",
         "heading_unit_ids": [ids[3]], "body_unit_ids": []},
        {"section_id": "leaf-b", "parent_id": "scope-b",
         "heading_unit_ids": [], "body_unit_ids": [ids[4]]},
    ]
    return parsed, pipeline


@pytest.mark.parametrize("reverse", [False, True])
def test_explicit_business_ancestors_follow_their_own_original_branch(reverse):
    from company_wiki.source_catalog import narrative_reading as reading
    from unit.document_understanding_selection.test_reading_native_carriers import selected

    parsed, pipeline = _explicit_scope_fixture(reverse=reverse)
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    ids = [unit.unit_id for unit in parsed.units]
    for anchor, parent, sibling in ((2, 1, 3), (4, 3, 1)):
        assert set(metadata[ids[anchor]]["required"]) == {ids[0], ids[parent]}
        assert ids[sibling] not in metadata[ids[anchor]]["required"]
    assert complete and not withheld
    result = selected(parsed, pipeline, candidates, metadata, limit=5)
    repeated = [span for span in result.evidence_spans if span.raw_text == parsed.units[2].raw_text]
    assert len(repeated) == 2 and len({span.span_id for span in repeated}) == 2
    assert {span.coordinates for span in repeated} == {
        parsed.units[2].coordinates, parsed.units[4].coordinates,
    }



@pytest.mark.parametrize("broken", ["missing", "cycle", "foreign-parent"])
def test_unproven_business_parent_cannot_borrow_another_branch_or_source(broken):
    from dataclasses import replace
    from company_wiki.source_catalog import narrative_reading as reading
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture

    parsed, pipeline = _explicit_scope_fixture()
    ids = [unit.unit_id for unit in parsed.units]
    sections = pipeline["structure"]["sections"]
    if broken == "missing":
        sections.remove(sections[1])
    elif broken == "cycle":
        sections[1]["parent_id"] = "leaf-a"
    else:
        foreign, other = source_fixture([("其他来源的业务标题",)], source_sha="e" * 64)
        parsed = replace(parsed, units=(*parsed.units, *foreign.units))
        pipeline["observation"]["units"].extend(other["observation"]["units"])
        pipeline["reading_plan"]["unit_profiles"].update(other["reading_plan"]["unit_profiles"])
        sections[1]["heading_unit_ids"] = [foreign.units[0].unit_id]
    candidates, metadata, packages, complete, withheld = reading._candidates(parsed, pipeline)
    assert ids[2] not in {candidate.unit.unit_id for candidate in candidates}
    assert ids[4] in metadata and set(metadata[ids[4]]["required"]) == {ids[0], ids[3]}
    assert not complete and withheld


def test_changed_original_parent_edge_changes_context_without_nearest_heading_fallback():
    from company_wiki.source_catalog import narrative_reading as reading

    parsed, pipeline = _explicit_scope_fixture()
    ids = [unit.unit_id for unit in parsed.units]
    pipeline["structure"]["sections"][2]["parent_id"] = "scope-b"
    _, metadata, _, complete, withheld = reading._candidates(parsed, pipeline)
    assert set(metadata[ids[2]]["required"]) == {ids[0], ids[3]}
    assert ids[1] not in metadata[ids[2]]["required"]
    assert complete and not withheld



def test_own_parent_context_reaches_public_groups_without_becoming_factual_support(monkeypatch):
    from company_wiki.source_catalog import narrative_reading as reading

    parsed, supplied = _explicit_scope_fixture()
    actual = reading._understand(parsed, title="年度报告", kind="annual_report", mime_type="application/pdf")
    actual["packages"] = supplied["packages"]
    actual["structure"]["sections"] = supplied["structure"]["sections"]
    actual["reading_plan"]["unit_profiles"] = supplied["reading_plan"]["unit_profiles"]
    monkeypatch.setattr(reading, "_understand", lambda *a, **k: actual)
    result = reading.select_reading_evidence(parsed, title="年度报告", existing_kind="annual_report", max_selected=5)
    by_locator = {span.coordinates: span.span_id for span in result.evidence_spans}
    ids = [by_locator[unit.coordinates] for unit in parsed.units]
    views = [view for group in result.reading_context["groups"] for view in group["citation_views"]]
    for anchor, parent, sibling in ((2, 1, 3), (4, 3, 1)):
        relevant = [view for view in views if view["support_evidence_ids"] == [ids[anchor]]]
        assert relevant and all(set(view["context_evidence_ids"]) == {ids[0], ids[parent]} for view in relevant)
        assert all(ids[sibling] not in view["context_evidence_ids"] for view in relevant)
    assert all(not {ids[0], ids[1], ids[3]}.intersection(view["support_evidence_ids"]) for view in views)
