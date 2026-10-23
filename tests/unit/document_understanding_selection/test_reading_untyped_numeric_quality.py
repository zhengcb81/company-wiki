"""Untyped source value cells keep honest numeric quality through public views.

All sources are synthetic in-memory observations. No parser, original file,
network, provider, model, production configuration or catalog is used.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_model_scoped
from company_wiki.document_normalization import table_shapes
from company_wiki.resource_budget import DEFAULT_DOCUMENT_WORK_LIMIT, new_document_work_budget
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_native_ranges import build_native_page_view
from company_wiki.source_catalog.narrative_routing import DEFAULT_SELECTION_LIMIT
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

SHA = "6" * 64
SOURCE = source_id_for_sha256(SHA)
FLAG = "table_structure_ambiguous"

UNBOUND_ROWS = (
    ("zh-newline", "客户数量\n273\n198\n增加来自新渠道", "经营情况"),
    ("zh-tab", "客户数量\t273\t198\t增加来自新渠道", "经营情况"),
    ("trad-newline", "客戶數量\n164\n127\n增加源自海外渠道", "經營情況"),
    ("en-newline", "Active customers\n735\n626\nIncrease from new distribution channels", "Business review"),
    ("en-tab", "Active customers\t735\t626\tIncrease from new distribution channels", "Business review"),
    ("en-pipe", "Active customers | 735 | 626 | Increase from new distribution channels", "Business review"),
)
PROSE_CONTROLS = (
    ("label-one-value", "客户数量\n273", "经营情况"),
    ("single-year-heading", "International business development\n2024", "Business review"),
    ("prose-quantities", "公司客户达到273家，新增客户75家，均已完成验证。", "经营情况"),
    ("wrapped-prose", "公司客户达到273家，\n新增客户75家，均已完成验证。", "经营情况"),
    ("english-prose", "The company served 735 customers, including 109 new customers.", "Business review"),
)


def _unit(text, index, *, source=SOURCE, typed=False, row=None, column=None, metadata=None):
    return _make_unit(
        source_id=source,
        parser_version="0.1.1",
        coordinates=EvidenceCoordinates(
            page_number=1,
            paragraph_index=None if typed else index,
            table_index=0 if typed else None,
            row_index=row,
            column_index=column,
        ),
        raw_text=text,
        unit_kind="html_table_cell" if typed else "pdf_text_block",
        source_role="company_filing",
        language="en" if typed else "mixed",
        metadata=metadata or {},
    )


def _document(texts):
    units = tuple(_unit(text, i, metadata={"heading_level": 1} if i == 0 else {})
                  for i, text in enumerate(texts))
    return DocumentStructure(SOURCE, SHA, "mixed", units,
                             page_count=1, pages_read=1, mime_type="application/pdf")


def _snapshot(parsed):
    def plain(value):
        if isinstance(value, Mapping):
            return {str(k): plain(v) for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [plain(v) for v in value]
        return value

    values = [{"id": u.unit_id, "source": u.source_id, "text": u.raw_text,
               "locator": u.coordinates.locator(), "metadata": plain(u.metadata),
               "quality_flags": list(u.quality_flags)} for u in parsed.units]
    return json.dumps(values, sort_keys=True, ensure_ascii=False)


def _select(parsed):
    budget = new_document_work_budget()
    selected = reading.select_reading_evidence(
        parsed, title="Annual report", existing_kind="annual_report", work_budget=budget,
    )
    assert selected.selection_limit == DEFAULT_SELECTION_LIMIT == 96
    assert reading.MAX_READING_CHARS == 48_000
    assert budget.max_work_units == DEFAULT_DOCUMENT_WORK_LIMIT == 16_000_000
    assert not budget.exhausted
    assert selected.reading_context["schema_version"] == "du-production-reading/2"
    assert selected.summary_input()["schema_version"] == "narrative-summary-input/0.2.0"
    return selected


def _assert_quality_reaches_citation_and_model(selected, spans):
    assert spans, "Business text remains readable; its unbound numbers stay unknown."
    assert all(FLAG in span.quality_flags for span in spans)
    assert any(FLAG in text for text in selected.reading_context["constraints"])
    ids = {span.span_id for span in spans}
    assert any(ids.intersection(view["support_evidence_ids"])
               for group in selected.reading_context["groups"]
               for view in group["citation_views"])
    model = narrative_model_scoped.compile_scoped_model_view(
        SimpleNamespace(evidence_spans=selected.evidence_spans,
                        reading_context=selected.reading_context), max_claims=20,
    ).to_model_dict()
    assert model["schema_version"] == "source-scoped-model-view/1"
    parts = model["shared_fragments"] + [part for task in model["tasks"]
                                          for part in task["parts"] if "text" in part]
    texts = {span.raw_text for span in spans}
    actual = [part for part in parts if part["text"] in texts]
    assert actual and all(FLAG in part.get("quality_flags", model["fragment_defaults"]["quality_flags"])
                          for part in actual)


def _native_bound_document():
    cells = (
        ("Capacity (units)", 0, 0, True, "col"),
        ("As of December 31, 2024", 0, 1, True, "col"),
        ("Overseas plants", 1, 0, True, "row"),
        ("47", 1, 1, False, None),
    )
    units = tuple(_unit(text, i, typed=True, row=row, column=col,
                        metadata={"table_index": 0, "row_index": row, "column_index": col,
                                  "dom_path": f"/table/row/{row}/cell/{col}"})
                  for i, (text, row, col, _, _) in enumerate(cells))
    native_cells = []
    for unit, (_, row, col, is_header, scope) in zip(units, cells, strict=True):
        native_cells.append({
            "cell_id": f"cell-{row}-{col}", "row": row, "column": col,
            "row_span": 1, "column_span": 1, "presence": "present",
            "text_refs": [{"unit_id": unit.unit_id, "char_start": 0, "char_end": len(unit.raw_text)}],
            "is_header": is_header, "header_scope": scope,
            "html_id": None, "headers": [], "row_group": 0,
        })
    table = {"scope": {"parent_id": SOURCE, "table_id": "html:t0", "page": 1},
             "cells": native_cells, "header_rows": [0], "context_refs": [], "position_complete": True}
    units = tuple(replace(u, metadata={**u.metadata, "native_source_view": {"tables": [table]}})
                  for u in units)
    return DocumentStructure(SOURCE, SHA, "en", units, page_count=1, pages_read=1, mime_type="text/html")


def _native_carrier_document(parts, *, digest=SHA):
    source = source_id_for_sha256(digest)
    text = "\n".join(parts)
    box = (90, 120, 550, 150)
    view = build_native_page_view([(0, box, text)])
    units, start = [], 0
    for i, part in enumerate(parts):
        layout = {"bbox": list(box), "page_width": 600, "page_height": 800,
                  "coordinate_frame": "dict", "rotation": 0, "column": 0}
        fonts = [{"char_start": 0, "char_end": len(part), "font_size": 12,
                  "font_weight": "regular", "coordinate_frame": "dict",
                  "source": "pdf_native_single_textpage", "char_alignment": "exact"}]
        metadata = {"pdf_block": 0, "block_sha256": sha256(text.encode()).hexdigest(),
                    "block_char_start": start, "block_char_end": start + len(part),
                    "native_source_view": view,
                    "reading_layout": {"layout": layout, "upstream_hints": {"font_runs": fonts}}}
        original = _unit(part, i, source=source, metadata=metadata)
        units.append(replace(original, language="en"))
        start += len(part) + 1
    return DocumentStructure(source, digest, "en", tuple(units),
                             page_count=1, pages_read=1, mime_type="application/pdf")


def test_imports_are_owned_by_this_checkout_inside_pytest():
    root = Path(__file__).resolve().parents[3] / "src"
    for module in (reading, table_shapes, narrative_model_scoped):
        assert Path(module.__file__).resolve().is_relative_to(root)


@pytest.mark.parametrize("label,text,heading", UNBOUND_ROWS, ids=[case[0] for case in UNBOUND_ROWS])
def test_public_untyped_numeric_row_keeps_unknown_attribution_in_all_views(label, text, heading):
    parsed = _document([heading, text])
    before = _snapshot(parsed)
    selected = _select(parsed)
    spans = [span for span in selected.evidence_spans if span.raw_text == text]
    assert _snapshot(parsed) == before
    assert all(span.source_id == parsed.source_id and span.coordinates == parsed.units[-1].coordinates
               for span in spans)
    _assert_quality_reaches_citation_and_model(selected, spans)


@pytest.mark.parametrize("label,text,heading", PROSE_CONTROLS, ids=[case[0] for case in PROSE_CONTROLS])
def test_single_value_and_complete_prose_are_not_labelled_as_unbound_tables(label, text, heading):
    parsed = _document([heading, text])
    before = _snapshot(parsed)
    selected = _select(parsed)
    spans = [span for span in selected.evidence_spans if span.raw_text == text]
    assert spans and all(FLAG not in span.quality_flags for span in spans)
    assert _snapshot(parsed) == before


def test_complete_native_table_keeps_exact_numeric_identity_without_ambiguity():
    parsed = _native_bound_document()
    before = _snapshot(parsed)
    selected = _select(parsed)
    original = next(unit for unit in parsed.units if unit.raw_text == "47")
    numeric = [span for span in selected.evidence_spans if span.raw_text == "47"]
    assert numeric and all(FLAG not in span.quality_flags for span in numeric)
    assert numeric[0].source_id == original.source_id
    assert numeric[0].coordinates == original.coordinates
    assert _snapshot(parsed) == before


def test_exact_native_carrier_does_not_erase_ambiguous_original_numeric_cells():
    parts = ("The company expanded its customer network.",
             "Active customers\n735\n626\nIncrease from new distribution channels.")
    parsed = _native_carrier_document(parts)
    before = _snapshot(parsed)
    selected = _select(parsed)
    carriers = [span for span in selected.evidence_spans
                if span.structured_value.get("unit_kind") == "pdf_native_range"]
    assert len(carriers) == 1 and carriers[0].raw_text == "\n".join(parts)
    assert set(carriers[0].structured_value["native_range"]["source_unit_ids"]) == {
        unit.unit_id for unit in parsed.units
    }
    assert _snapshot(parsed) == before
    _assert_quality_reaches_citation_and_model(selected, carriers)


def test_one_parent_unknown_quality_cannot_contaminate_another_parent_prose():
    first = _native_carrier_document((
        "The company expanded its customer network.",
        "Active customers\n735\n626\nIncrease from new distribution channels.",
    ))
    second = _native_carrier_document((
        "The company commissioned a new manufacturing plant.",
        "The plant can produce 48 machines per year.",
    ), digest="7" * 64)
    parsed = replace(first, units=first.units + second.units)
    before = _snapshot(parsed)
    selected = _select(parsed)
    first_spans = [span for span in selected.evidence_spans if span.source_id == first.source_id]
    second_spans = [span for span in selected.evidence_spans if span.source_id == second.source_id]
    assert second_spans and all(FLAG not in span.quality_flags for span in second_spans)
    assert _snapshot(parsed) == before
    by_id = {span.span_id: span for span in selected.evidence_spans}
    for group in selected.reading_context["groups"]:
        assert len({by_id[sid].source_id for sid in group["evidence_ids"]}) == 1
    _assert_quality_reaches_citation_and_model(selected, first_spans)
