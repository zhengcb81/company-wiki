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
