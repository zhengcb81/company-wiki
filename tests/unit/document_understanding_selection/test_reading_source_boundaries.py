"""Original parent identity survives one shared reading engine."""
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def test_equal_text_and_locator_in_two_original_parents_remain_distinct():
    originals = []
    for digest in ("a" * 64, "b" * 64):
        originals.append(_make_unit(source_id=source_id_for_sha256(digest),
            parser_version="0.1.0", coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
            raw_text="Our service expanded into a new operating region.",
            unit_kind="pdf_text_block", source_role="company_filing", language="en", metadata={}))
    parsed = DocumentStructure(source_id=originals[0].source_id, source_sha256="a" * 64,
                               language="en", units=tuple(originals), page_count=1, pages_read=1)
    selected = select_narrative_evidence(parsed, title="Annual report", selector_version="0.9.0")
    assert len(selected.evidence_spans) == 2
    by_id = {span.span_id: span for span in selected.evidence_spans}
    groups = selected.reading_context["groups"]
    assert {uid for group in groups for uid in group["evidence_ids"]} == set(by_id)
    assert all(len({by_id[uid].source_id for uid in group["evidence_ids"]}) == 1 for group in groups)
