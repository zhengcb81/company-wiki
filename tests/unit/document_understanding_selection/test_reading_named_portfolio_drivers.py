"""Source-subject and driver relations; no issuer/product-name allowlist."""
import pytest

from company_wiki.source_catalog.narrative_business_policy import detect_business_fact, detect_reading_business_fact
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


@pytest.mark.parametrize('text', [
    '本集團的多品牌組合包括甲品牌、乙品牌及丙品牌。',
    '本集团的多品牌组合包括甲品牌、乙品牌及丙品牌。',
    'Our brand portfolio comprises Alpha, Beta and Gamma.',
    '本公司的品牌包括甲、乙及丙，面向运动鞋及服饰市场。',
])
def test_issuer_owned_named_portfolio_is_concrete_business_structure(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible and 'brand_portfolio_structure' in fact.reasons


@pytest.mark.parametrize('text', [
    '本集團為Delta Sports, Inc. 的最大股東，該公司在紐約獨立上市。',
    '本集团为Delta Sports, Inc. 的最大股东，该公司在纽约独立上市。',
    'Our company is the largest shareholder of the independently listed Delta Holdings.',
    'Alpha集團亦為Delta Sports, Inc. 的最大股東。',
])
def test_actual_named_shareholder_relationship_is_source_scope_not_consolidation(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible and 'business_ownership_scope' in fact.reasons
    assert 'consolidated' not in fact.reasons


@pytest.mark.parametrize('text', [
    '净利润增长主要是由于晶圆销量增加、产能利用率上升及产品组合变动所致。',
    '淨利潤增長主要是由於晶圓銷量增加、產能利用率上升及產品組合變動所致。',
    '主要是由于晶圆销量增加、产能利用率上升及产品组合变动所致。',
    'Regional earnings rose due to higher unit volumes and improved capacity utilization.',
    'Delta region net sales decreased during 2026 compared to 2025 primarily due to lower net sales of product Alpha, partially offset by higher net sales of product Beta.',
    'Delta region net sales decreased primarily due to lower net sales of Alpha, partially offset by higher net sales of Beta.',
])
def test_actual_operating_cause_does_not_depend_on_a_financial_or_product_headline(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible and 'operating_causal_driver' in fact.reasons


@pytest.mark.parametrize('text', [
    '甲品牌、乙品牌、丙品牌。',
    'A brand portfolio is defined as a set of brands.',
    'Our brand portfolio comprises products, services and solutions.',
    '假如本集团成为Delta公司的最大股东。',
    '本集团尚未成为Delta公司的最大股东，未来可能增持股份。',
    'Our company is not the largest shareholder of Delta Holdings.',
    'Our company may become the largest shareholder of Delta Holdings.',
    '股东权益同比增长20%。',
    '净利润增长主要是由于汇兑收益和所得税下降所致。',
    '净利润同比增长20%。产品列表在另一个术语表中。',
    'Net sales declined by 20%. Product Alpha is defined in an unrelated glossary.',
    'Net sales declined because of an accounting policy change.',
    'Revenue rose due to lower taxes and higher interest income.',
    '净利润同比增长，主要原因尚不确定。',
    '公司2026年度拟不进行利润分配。',
])
def test_unanchored_hypothetical_glossary_and_financial_causes_are_not_new_business_relations(text):
    assert not detect_reading_business_fact(text).eligible


def test_causal_relation_never_borrows_operating_words_from_an_independent_sentence():
    text = 'Revenue increased due to higher interest income. Unit volumes and capacity are terms in a separate glossary.'
    assert not detect_reading_business_fact(text).eligible


def test_legacy_detector_remains_unextended_for_named_relationships():
    text = 'Our brand portfolio comprises Alpha, Beta and Gamma.'
    assert not detect_business_fact(text).eligible
    assert detect_reading_business_fact(text).eligible


def test_existing_native_line_admission_is_not_erased_by_a_long_wrapped_tail():
    text = 'Our products are supplied through distributors\n' + 'descriptive background ' * 80
    assert detect_business_fact(text).eligible
    assert detect_reading_business_fact(text).eligible


@pytest.mark.parametrize('text', [
    '本集團為Delta Sports, Inc. 的最大股東，該公司為獨立上市公司，並非本集團合併分部。',
    '净利润上升并非因为价格上涨，而是由于销量增加及产能利用率提高。',
    'Delta region net sales decreased due to lower net sales of Alpha, partially offset by higher net sales of Beta.',
])
def test_selected_relationship_preserves_native_negation_unit_and_qualifiers(text):
    source=source_id_for_sha256('b'*64)
    unit=_make_unit(source_id=source,parser_version='0.1.1',coordinates=EvidenceCoordinates(paragraph_index=0),
        raw_text=text,unit_kind='html_paragraph',source_role='company_filing',language='mixed',metadata={})
    parsed=DocumentStructure(source,'b'*64,'mixed',(unit,),mime_type='text/html',line_count=1)
    selected=select_narrative_evidence(parsed,title='Company update',selector_version='0.9.0',max_selected=8)
    assert [s.raw_text for s in selected.evidence_spans] == [text]
    assert selected.evidence_spans[0].coordinates == unit.coordinates
