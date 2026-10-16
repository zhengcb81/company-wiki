"""Concrete source-described portfolios, without repeated issuer identity."""
import pytest

from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


@pytest.mark.parametrize("text", [
    "透過多元化的品牌組合，包括NorthPeak、HarborSport及CedarActive，Delta集團服務不同消費群體。",
    "透过多元化的品牌组合，包括NorthPeak、HarborSport及CedarActive，Delta集团服务不同消费群体。",
    "本集團的品牌組合，包括NorthPeak、HarborSport及CedarActive。",
    "本集团的品牌组合，包括甲品牌、乙品牌及丙品牌。",
    "Delta集團的品牌組合包括NorthPeak、HarborSport及CedarActive。",
    "品牌組合包括NorthPeak、HarborSport及CedarActive。",
    "Its brand portfolio includes NorthPeak, HarborSport and CedarActive.",
    "Through a diverse brand portfolio, including NorthPeak, HarborSport and CedarActive, Delta serves different markets.",
    "品牌組合，包括NorthPeak、\nHarborSport及CedarActive。",
])
def test_observed_concrete_portfolio_does_not_need_repeated_issuer_pronoun(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible and "brand_portfolio_structure" in fact.reasons


@pytest.mark.parametrize("text", [
    "NorthPeak、HarborSport及CedarActive。",
    "品牌組合定義為企業採用的品牌集合，例如NorthPeak、HarborSport。",
    "術語表例句：品牌組合，包括NorthPeak、HarborSport及CedarActive。",
    "Glossary example: Our brand portfolio includes NorthPeak and HarborSport.",
    "定义：本集团品牌包括甲、乙和丙。",
    "A brand portfolio is defined as a set of brands including NorthPeak and HarborSport.",
    "假如透過品牌組合，包括NorthPeak、HarborSport及CedarActive。",
    "本集團尚未建立品牌組合，包括NorthPeak、HarborSport及CedarActive。",
    "If a brand portfolio includes NorthPeak, HarborSport and CedarActive.",
    "Our brand portfolio, including products, services and solutions.",
    "品牌組合，包括產品、服務及方案。",
    "品牌組合，包括、以及。",
    "Our portfolio does not include NorthPeak, HarborSport and CedarActive.",
    "The brand portfolio may include NorthPeak and HarborSport.",
    "品牌組合仍在規劃中。另一段定義NorthPeak、HarborSport及CedarActive。",
])
def test_glossary_generic_list_hypothetical_and_separate_names_do_not_become_actual_portfolio(text):
    assert not detect_reading_business_fact(text).eligible


def test_source_disclosed_foreign_actor_is_preserved_without_issuer_or_consolidation_inference():
    text = "Independent Delta集團的品牌組合，包括NorthPeak、HarborSport及CedarActive，該集團為獨立上市公司，並非本公司合併分部。"
    source = source_id_for_sha256("c" * 64)
    unit = _make_unit(source_id=source, parser_version="0.1.1", coordinates=EvidenceCoordinates(paragraph_index=0),
        raw_text=text, unit_kind="html_paragraph", source_role="company_filing", language="mixed", metadata={})
    parsed = DocumentStructure(source, "c" * 64, "mixed", (unit,), mime_type="text/html", line_count=1)
    selected = select_narrative_evidence(parsed, title="Company update", selector_version="0.9.0", max_selected=8)
    assert [span.raw_text for span in selected.evidence_spans] == [text]
    assert selected.evidence_spans[0].coordinates == unit.coordinates
    assert "brand_portfolio_structure" in detect_reading_business_fact(text).reasons
    assert "consolidated" not in detect_reading_business_fact(text).reasons


def test_real_decision_inventory_reads_current_business_policy_version(monkeypatch):
    from company_wiki.document_understanding.decision_inventory import _versions
    from company_wiki.source_catalog import narrative_business_policy

    assert _versions()["business_policy"] == "reading-business-policy/7"
    monkeypatch.setattr(narrative_business_policy, "READING_BUSINESS_POLICY_VERSION", "reading-business-policy/test-next")
    assert _versions()["business_policy"] == "reading-business-policy/test-next"
