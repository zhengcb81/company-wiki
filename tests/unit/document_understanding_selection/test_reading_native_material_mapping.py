"""Pure source-material mapping; carriers here are explicit synthetic DTOs.

Physical PDF provenance and range replay belong to the source-owner tests.
These cases exercise the production adapter, never claim real-PDF extraction.
"""
from dataclasses import replace

import pytest

from company_wiki.source_contract import EvidenceCoordinates
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_routing import DocumentRoute
from company_wiki.source_catalog.narrative_reading import _selected_unit_spans, _NEVER_HEADING
from company_wiki.source_catalog.narrative_reading import _native_layout_summary


def unit(index, text, *, source="a" * 64):
    return _make_unit(source_id="urn:company-wiki:source:sha256:" + source,
        parser_version="0.1.1", coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
        raw_text=text, unit_kind="pdf_text_block", source_role="company_filing",
        language="zh", metadata={})


def package(units):
    structure = DocumentStructure(units[0].source_id, units[0].source_id.rsplit(":", 1)[-1],
                                  "zh", tuple(units))
    selected = finalize_selection(structure, DocumentRoute("annual_report", 96, False),
        tuple(EvidenceCandidate(u, (), ("reading_plan",), 1) for u in units),
        group_ids={}, heading_pattern=_NEVER_HEADING, dropped_financial_count=0)
    return structure, selected


def carrier(first):
    return replace(first, unit_id="urn:company-wiki:narrative-unit:sha256:" + "e" * 64,
        parser_name="native_pdf_range_parser", parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=first.coordinates.paragraph_index,
                                        char_start=20, char_end=50),
        raw_text="报告期启动开发。下半年将送样验证。", unit_kind="pdf_native_range")


def test_original_policy_members_share_one_exact_sent_carrier():
    head, a, b = unit(0, "业务进展"), unit(1, "报告期启动开发。"), unit(2, "下半年将送样验证。")
    original, _ = package([head, a, b])
    merged = carrier(a)
    material, selected = package([head, merged])
    mapped = _selected_unit_spans(original, selected, {"_material_units": material.units,
        "_carrier_origins": {a.unit_id: merged.unit_id, b.unit_id: merged.unit_id}})
    assert mapped[a.unit_id] == mapped[b.unit_id] == selected.evidence_spans[1].span_id
    assert mapped[head.unit_id] == selected.evidence_spans[0].span_id
    assert len(selected.evidence_spans) == 2


def test_legacy_mapping_is_exact_and_unchanged():
    original, selected = package([unit(0, "业务进展"), unit(1, "公司已交付设备。")])
    assert _selected_unit_spans(original, selected, {}) == {
        u.unit_id: s.span_id for u, s in zip(original.units, selected.evidence_spans, strict=True)}


@pytest.mark.parametrize("change", ["text", "parser", "source"])
def test_unsourced_selected_material_is_rejected(change):
    original, selected = package([unit(0, "公司已交付设备。")])
    u = original.units[0]
    changed = replace(u, **{"raw_text": "公司尚未交付设备。"} if change == "text" else
                      {"parser_name": "foreign_parser"} if change == "parser" else
                      {"source_id": "urn:company-wiki:source:sha256:" + "f" * 64})
    with pytest.raises(ValueError, match="source-owned"):
        _selected_unit_spans(original, selected, {"_material_units": (changed,)})


def test_cross_source_origin_cannot_borrow_another_company_carrier():
    a, b = unit(0, "公司已交付设备。"), unit(1, "另一家公司正在开发。", source="b" * 64)
    original, _ = package([a, b])
    merged = carrier(a)
    material, selected = package([merged])
    with pytest.raises(ValueError, match="origin"):
        _selected_unit_spans(original, selected, {"_material_units": material.units,
            "_carrier_origins": {a.unit_id: merged.unit_id, b.unit_id: merged.unit_id}})


def test_native_range_coverage_is_compact_and_separate_from_fine_geometry():
    structure, _ = package([unit(0, "公司已交付设备。")])
    view_coverage = {"feature_version": "native-pdf-page-view/1", "complete": False,
        "captured_chars": 120, "deferred_page_count": 300, "deferred_pages": list(range(1, 129))}
    structure = replace(structure, layout_coverage={"feature_version": "pdf-reading-layout/1",
        "complete": True, "native_ranges": view_coverage})
    result = _native_layout_summary(structure)
    assert result["complete"] is True
    assert result["native_ranges"] == view_coverage
    assert "text" not in str(result)
