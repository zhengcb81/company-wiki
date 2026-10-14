"""Native geometry coverage stays separate from readable source evidence."""
from __future__ import annotations

from dataclasses import replace
import json

from company_wiki.source_catalog import narrative_evidence as selector
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def _document():
    digest = "b" * 64
    source = source_id_for_sha256(digest)
    unit = selector._make_unit(source_id=source, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text="Our platform launched a new product for overseas customers.",
        unit_kind="pdf_text", source_role="company_filing", language="en", metadata={})
    return DocumentStructure(source, digest, "en", (unit,), page_count=1,
                             pages_read=1, mime_type="application/pdf")


def _select(document):
    return selector.select_narrative_evidence(document, title="Annual report",
        existing_kind="annual_report", selector_version="0.9.0")


def test_geometry_gap_does_not_reclassify_read_original_as_unread():
    document = replace(_document(), layout_coverage={
        "feature_version": "pdf-reading-layout/1", "complete": False,
        "processed_unit_count": 1, "processed_page_count": 1,
        "deferred_unit_count": 0, "deferred_unit_ids": [],
        "deferred_limited": False, "fine_element_count": 2, "work_units": 7,
    }, layout_diagnostics=({"code": "NO_FINE_GEOMETRY", "unit_ids": []},))
    result = _select(document)
    assert document.coverage_complete
    assert result.evidence_spans
    native = result.reading_context["layout_coverage"]["native_frontend"]
    assert native["complete"] is False
    assert native["fine_element_count"] == 2
    assert native["diagnostics"] == [{"code": "NO_FINE_GEOMETRY", "count": 1, "unit_count": 0}]


def test_absent_native_snapshot_is_not_fabricated_as_complete():
    result = _select(_document())
    assert "native_frontend" not in result.reading_context["layout_coverage"]


def test_native_diagnostics_are_compact_counts_not_second_all_unit_inventory():
    identifiers = ["unit-" + str(index) for index in range(5000)]
    document = replace(_document(), layout_coverage={
        "feature_version": "pdf-reading-layout/1", "complete": False,
        "processed_unit_count": 0, "processed_page_count": 0,
        "deferred_unit_count": len(identifiers), "deferred_unit_ids": identifiers,
        "deferred_limited": False, "fine_element_count": 0, "work_units": 0,
    }, layout_diagnostics=tuple({"code": "UNREAD_PAGE", "unit_ids": identifiers,
                                 "unit_count": len(identifiers)} for _ in range(200)))
    result = _select(document)
    native = result.reading_context["layout_coverage"]["native_frontend"]
    assert native["deferred_unit_count"] == 5000
    assert len(native["deferred_unit_ids"]) == 128
    assert native["deferred_limited"] is True
    assert native["diagnostics"] == [{"code": "UNREAD_PAGE", "count": 200, "unit_count": 1000000}]
    assert len(json.dumps(native)) < 6000
    assert "reading_layout" not in json.dumps(result.evidence_spans[0].to_dict())
