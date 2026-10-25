"""Paragraph hints may add boundaries, never source text or guessed members."""
from dataclasses import replace
from hashlib import sha256

import pytest

from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeUnit
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256
from company_wiki.source_catalog.narrative_pdf_paragraphs import (
    ParagraphProposal, align_paragraphs, triage_paragraph_gaps,
)


def document(texts=("The new product generated revenue of 12.4", "million dollars; rollout is not yet approved.")):
    digest = "a" * 64
    sid = source_id_for_sha256(digest)
    units = []
    for index, text in enumerate(texts):
        units.append(NarrativeUnit(
            "urn:company-wiki:narrative-unit:sha256:" + sha256(str(index).encode()).hexdigest(),
            sid, "selective_narrative_parser", "0.1.1",
            EvidenceCoordinates(page_number=1, paragraph_index=index), text,
            "pdf_text_block", "company_filing", "en",
            metadata={"pdf_block": index, "block_char_start": 0,
                      "block_char_end": len(text), "block_sha256": sha256(text.encode()).hexdigest(),
                      "reading_layout": {"layout": {"bbox": [60, 100 + index * 20, 500, 115 + index * 20],
                          "page_width": 600, "page_height": 800, "coordinate_frame": "dict", "rotation": 0}}}))
    return DocumentStructure(sid, digest, "en", tuple(units), page_count=1, pages_read=1,
                             mime_type="application/pdf")


def proposal(parsed, **changes):
    values = dict(source_id=parsed.source_id, source_sha256=parsed.source_sha256,
                  page=1, text=" ".join(u.raw_text for u in parsed.units),
                  bbox=(60, 100, 500, 135), page_width=600, page_height=800,
                  rotation=0, coordinate_frame="dict")
    return ParagraphProposal(**(values | changes))


def test_align_retains_source_bytes_ids_and_locators_and_linear_compact_proof():
    parsed = document()
    result = align_paragraphs(parsed, [proposal(parsed)], work_budget=WorkBudget(10000))
    assert result.accepted_groups == 1
    for old, new in zip(parsed.units, result.parsed.units, strict=True):
        assert (old.unit_id, old.raw_text, old.coordinates) == (new.unit_id, new.raw_text, new.coordinates)
        proof = new.metadata["reading_layout"]["paragraph_membership"]
        assert proof["count"] == 2
        assert not any(key in proof for key in ("text", "members", "font_size"))
        assert "reading_layout" not in new.to_evidence_span(topics=(), selection_reasons=()).structured_value


@pytest.mark.parametrize("changes", [
    {"source_sha256": "b" * 64}, {"source_id": source_id_for_sha256("b" * 64)},
    {"page": 2}, {"rotation": 90}, {"coordinate_frame": "bottom_left"},
    {"page_width": 601}, {"bbox": (60, 100, 500, 114)},
    {"text": "The new product generated revenue of 12.5 million dollars; rollout is not yet approved."},
    {"text": "million dollars; rollout is not yet approved. The new product generated revenue of 12.4"},
    {"bbox": (float("nan"), 100, 500, 135)},
    {"bbox": (279, 107, 281, 128)},
])
def test_wrong_source_frame_geometry_or_characters_is_rejected(changes):
    parsed = document()
    result = align_paragraphs(parsed, [proposal(parsed, **changes)], work_budget=WorkBudget(10000))
    assert result.accepted_groups == 0
    assert result.parsed.units == parsed.units


def test_overlap_conflicts_and_skipped_or_table_members_are_rejected():
    parsed = document()
    assert align_paragraphs(parsed, [proposal(parsed)] * 2, work_budget=WorkBudget(10000)).accepted_groups == 0
    for bad in (replace(parsed.units[1], unit_kind="table_row"),
                replace(parsed.units[1], source_role="investor_question")):
        changed = replace(parsed, units=(parsed.units[0], bad))
        assert align_paragraphs(changed, [proposal(changed)], work_budget=WorkBudget(10000)).accepted_groups == 0


def test_nfkc_whitespace_and_explicit_leading_bullet_only_are_auxiliary():
    parsed = document(("• Revenue grew by １２．４", "million dollars, but not from production."))
    hint = proposal(parsed, text="Revenue grew by 12.4 million dollars, but not from production.")
    result = align_paragraphs(parsed, [hint], work_budget=WorkBudget(10000))
    assert result.accepted_groups == 1
    assert result.parsed.units[0].raw_text.startswith("• Revenue grew by １２．４")


def test_triage_is_bounded_deduplicated_and_not_missing_punctuation_alone():
    parsed = document()
    assert triage_paragraph_gaps(parsed, work_budget=WorkBudget(10000)).pages == (1,)
    assert triage_paragraph_gaps(document(("Unfinished heading", "Another heading")),
                                 work_budget=WorkBudget(10000)).pages == ()
    assert triage_paragraph_gaps(parsed, work_budget=WorkBudget(10000), max_pages=0).pages == ()
