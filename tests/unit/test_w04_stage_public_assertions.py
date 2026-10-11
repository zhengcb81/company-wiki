"""Stage assertions must be consistent through the actual public selector.

Synthetic source structures exercise selection, not native PDF/transcript parsing.
Native-original replay is a separate major-node check.
"""
from __future__ import annotations

import hashlib
import pytest

from company_wiki.source_contract import EvidenceCoordinates
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_catalog.narrative_business_groups import _commercialization_milestone

MILESTONE = "new_product_commercialization_milestone"
CASES = [
    ("新型设备并未全部通过客户现场验证。", False),
    ("新型设备未能如期完成客户现场验证。", False),
    ("新型系统不是已经获得客户重复订单。", False),
    ("新型系统已交付100万元保证金给客户。", False),
    ("公司推出了系统，目前已交付100万元保证金给客户。", False),
    ("新型设备已完成客户验证前的准备工作。", False),
    ("新型设备根据既定计划已完成客户现场验证。", True),
    ("新型设备将用于海外市场且已完成客户现场验证。", True),
    ("新型设备已完成客户现场验证。", True),
    ("新型设备未通过客户现场验证。", False),
    ("公司此前推出了设备，目前已交付首批客户。", True),
    ("公司推出了系统，目前已交付保证金给客户。", False),
    ("新型设备计划通过客户现场验证。", False),
    ("若设备已通过客户验证，按合同结算货款。", False),
    ("The equipment has successfully completed customer validation according to plan.", True),
    ("The product will be shipped after validation.", False),
    ("The system has not fully completed customer validation.", False),
    ("The system has completed preparation for customer validation.", False),
    ("Our equipment will serve overseas markets and has passed customer validation.", True),
    ("The platform has delivered a USD 1 million deposit to customers.", False),
    ("新型系统已交付20套设备及100万元保证金给客户。", True),
    ("没有缺陷的设备已完成客户现场验证。", True),
    ("新型设备没有通过验证但已交付首批客户。", True),
]


def document(text, kind):
    digest = hashlib.sha256(text.encode()).hexdigest()
    source_id = "urn:company-wiki:source:sha256:" + digest
    lang = "en" if text.isascii() else "zh"
    units = (_make_unit(source_id=source_id, parser_version="0.3.1",
        coordinates=EvidenceCoordinates(page_number=1 if kind == "pdf_text_block" else None,
                                        paragraph_index=2, char_start=0, char_end=len(text)),
        raw_text=text, unit_kind=kind, source_role="management", language=lang,
        metadata={"bbox": [10., 20., 500., 45.], "pdf_block": 1, "block_sha256": digest}
        if kind == "pdf_text_block" else {"speaker": "Synthetic company officer"}),)
    return DocumentStructure(source_id=source_id, source_sha256=digest, language=lang,
                             units=units, line_count=3)


@pytest.mark.parametrize("text,expected", CASES)
def test_assertion_polarity_object_and_complement(text, expected):
    assert _commercialization_milestone(text) is expected


@pytest.mark.parametrize("kind", ["transcript_sentence", "pdf_text_block"])
@pytest.mark.parametrize("text,expected", CASES)
def test_public_selection_uses_same_assertion_for_all_candidate_paths(text, expected, kind):
    parsed = document(text, kind)
    package = select_narrative_evidence(parsed, title="Synthetic company business update",
        existing_kind="investor_call_transcript" if kind == "transcript_sentence" else "annual",
        selector_version="0.8.0", max_selected=10)
    seen = any(MILESTONE in span.structured_value["selection_reasons"]
               for span in package.evidence_spans)
    assert seen is expected
    assert all(span.raw_text == text for span in package.evidence_spans)
    assert parsed.units[0].raw_text == text


@pytest.mark.parametrize("text", [
    "新型设备计划通过客户现场验证，准备明年交付客户。",
    "新型设备没有完成现场验证，客户采用进度存在风险。",
])
def test_unrealized_stage_can_remain_useful_evidence_without_false_completion(text):
    parsed = document(text, "transcript_sentence")
    package = select_narrative_evidence(parsed, title="Synthetic company business update",
        existing_kind="investor_call_transcript", selector_version="0.8.0", max_selected=10)
    assert package.evidence_spans
    assert all(MILESTONE not in span.structured_value["selection_reasons"]
               for span in package.evidence_spans)
    assert {span.raw_text for span in package.evidence_spans} == {text}



@pytest.mark.parametrize("text,expected", [
    ("新型设备于2022年推出，目前已获得客户重复订单。", False),
    ("新型设备累计出货量突破300台。", True),
    ("新型设备累计出货量突破三百个反应台。", True),
])
def test_operating_quantity_is_attached_to_metric_not_any_date(text, expected):
    from company_wiki.source_catalog.narrative_business_groups import _operating_fact
    assert ("quantified_operating_status" in _operating_fact(text).reasons) is expected


@pytest.mark.parametrize("text", [
    "公司采用多供应商策略保障零部件供应，若上游产能紧张持续，将影响设备交期。",
    "Our cloud services remain compute constrained and GPU shortages delay customer deployments.",
])
def test_explicit_operating_constraint_preserves_causal_qualifications(text):
    from company_wiki.source_catalog.narrative_business_groups import _operating_fact
    assert "specific_operating_constraint" in _operating_fact(text).reasons


def test_generic_technical_limit_is_not_an_operating_supply_constraint():
    from company_wiki.source_catalog.narrative_business_groups import _operating_fact
    assert "specific_operating_constraint" not in _operating_fact("光刻设备受到波长限制，新工艺步骤增多。").reasons
