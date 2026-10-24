"""Physical same-page PDF continuations stay closed as original evidence units."""

from hashlib import sha256

from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


SOURCE_SHA = sha256(b"hk-interim-continuity-fixture").hexdigest()


def pdf_unit(text: str, paragraph: int, bbox: tuple[float, float, float, float]):
    return _make_unit(
        source_id=source_id_for_sha256(SOURCE_SHA),
        parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=13, paragraph_index=paragraph),
        raw_text=text,
        unit_kind="pdf_text_block",
        source_role="company_filing",
        language="zh",
        metadata={
            "bbox": bbox,
            "pdf_block": paragraph,
            "block_sha256": sha256(text.encode("utf-8")).hexdigest(),
        },
    )


def test_same_page_chinese_causal_sentence_keeps_both_original_pdf_blocks():
    left = pdf_unit(
        "人工智能及行業雲業務客戶增加帶動收入上升，惟部分升幅被主動減少向",
        3,
        (99.20, 183.58, 538.49, 194.03),
    )
    right = pdf_unit(
        "內容分發網絡（「CDN」）客戶提供服務所抵銷。",
        4,
        (99.19, 197.58, 286.98, 208.03),
    )
    parsed = DocumentStructure(
        source_id_for_sha256(SOURCE_SHA),
        SOURCE_SHA,
        "zh",
        (left, right),
        page_count=1,
        pages_read=1,
        mime_type="application/pdf",
    )

    selected = select_narrative_evidence(
        parsed,
        title="2025 interim report",
        existing_kind="ir",
        selector_version="0.8.0",
    )
    left_span = next((span for span in selected.evidence_spans if span.raw_text == left.raw_text), None)
    right_span = next((span for span in selected.evidence_spans if span.raw_text == right.raw_text), None)

    assert left_span is not None and right_span is not None
    assert left_span.structured_value["selection_group_id"] == right_span.structured_value["selection_group_id"]
