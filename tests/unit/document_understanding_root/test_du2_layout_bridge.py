"""Real public parser -> one layout engine -> reference-preserving structure."""

from __future__ import annotations
import copy
import hashlib
from importlib import import_module
import pytest
from company_wiki.source_catalog import narrative_evidence as pdf
from company_wiki.document_understanding.observation_adapter import build_observation


def _bridge():
    return import_module("company_wiki.document_understanding.layout_bridge")


def _pdf_bytes():
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((70, 110), "Business Highlights", fontsize=24, fontname="hebo")
    page.insert_text(
        (70, 200),
        "We launched a new product in Europe during the quarter.",
        fontsize=11,
    )
    page.insert_text(
        (70, 280), "A note qualifies this operating disclosure.", fontsize=8
    )
    data = doc.tobytes()
    doc.close()
    return data


def test_real_pdf_scan_preserves_actual_fonts_sizes_and_source_identity(monkeypatch):
    fitz = pytest.importorskip("fitz")
    data = _pdf_bytes()
    sha = hashlib.sha256(data).hexdigest()
    source = "urn:company-wiki:source:sha256:" + sha
    calls = []
    original = fitz.Page.get_text

    def tracked(page, *args, **kwargs):
        if args and args[0] == "dict":
            calls.append(1)
        return original(page, *args, **kwargs)

    monkeypatch.setattr(fitz.Page, "get_text", tracked)
    parsed = pdf.parse_pdf_bytes(
        data, source_id=source, source_sha256=sha, language="en", table_pages=()
    )
    assert len(calls) == 1
    title = next(u for u in parsed.units if u.raw_text == "Business Highlights")
    assert title.metadata["font_size"] == pytest.approx(24)
    assert title.metadata["font_weight"] == "bold"
    assert title.metadata["page_width"] == pytest.approx(600)
    assert title.metadata["page_height"] == pytest.approx(800)
    assert title.metadata["geometry_granularity"] == "block"
    assert title.parser_version == pdf.NARRATIVE_PARSER_VERSION
    legacy = pdf._make_unit(
        source_id=title.source_id,
        parser_version=title.parser_version,
        coordinates=title.coordinates,
        raw_text=title.raw_text,
        unit_kind=title.unit_kind,
        source_role=title.source_role,
        language=title.language,
        metadata={
            k: v
            for k, v in title.metadata.items()
            if k
            in {
                "bbox",
                "block_char_end",
                "block_char_start",
                "block_sha256",
                "pdf_block",
            }
        },
    )
    assert legacy.unit_id == title.unit_id
    with fitz.open(stream=data, filetype="pdf") as doc:
        blocks = pdf._pdf_text_blocks(doc[0])
        assert all(len(row) == 3 for row in blocks)
        by_no = {no: text for no, _bbox, text in blocks}
        for unit in parsed.units:
            text = by_no[unit.metadata["pdf_block"]]
            assert (
                text[
                    unit.metadata["block_char_start"] : unit.metadata["block_char_end"]
                ]
                == unit.raw_text
            )
    observation = build_observation(
        parsed.units, source_id=source, source_sha256=sha, mime_type="application/pdf"
    )
    before = copy.deepcopy(observation)
    enriched, layout = _bridge().apply_layout_hints(observation)
    assert observation == before
    for raw, new in zip(before["units"], enriched["units"], strict=True):
        assert (new["unit_id"], new["locator"], new["text"], new["ordinal"]) == (
            raw["unit_id"],
            raw["locator"],
            raw["text"],
            raw["ordinal"],
        )
    heading = next(u for u in enriched["units"] if u["text"] == "Business Highlights")
    assert heading["hints"]["heading_level"] == 1
    assert heading["layout"]["page_width"] == 600
    assert (
        layout["coverage"]["complete"] is False
    )  # font is real; cells/span grain is not provided
    assert not any(group["cells"] for group in layout["groups"])


def test_missing_geometry_preserves_real_dom_heading_and_all_text():
    observation = {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": "s", "source_sha256": "h"},
        "metadata": {"mime_type": "text/html"},
        "coverage": {
            "native_scan": "complete",
            "opaque_pages": [],
            "deferred_pages": [],
        },
        "units": [
            {
                "unit_id": "h",
                "ordinal": 0,
                "locator": "original-h",
                "page": None,
                "text": "Business",
                "kind": "heading",
                "language": "en",
                "role": "company_filing",
                "layout": {},
                "hints": {"heading_level": 2, "dom_path": "0.0.1"},
            },
            {
                "unit_id": "p",
                "ordinal": 1,
                "locator": "original-p",
                "page": None,
                "text": "A new business is operating.",
                "kind": "paragraph",
                "language": "en",
                "role": "company_filing",
                "layout": {},
                "hints": {},
            },
        ],
    }
    before = copy.deepcopy(observation)
    enriched, layout = _bridge().apply_layout_hints(observation)
    assert observation == before
    assert enriched["units"][0]["hints"]["heading_level"] == 2
    assert enriched["units"][1]["text"] == observation["units"][1]["text"]
    assert all(
        u["page"] is None and not u["layout"].get("page_width")
        for u in enriched["units"]
    )
    assert layout["coverage"]["complete"] is False
    assert any(
        d["code"] == "LAYOUT_GEOMETRY_UNAVAILABLE" for d in layout["diagnostics"]
    )


def test_bind_layout_context_adds_existing_raw_references_without_new_semantic_units():
    structure = {
        "schema_version": "du-structure/1",
        "source_ref": {"source_id": "s", "source_sha256": "h"},
        "sections": [
            {
                "section_id": "s1",
                "heading_unit_ids": ["title"],
                "body_unit_ids": ["unit", "header", "row", "note"],
            }
        ],
        "semantic_units": [
            {
                "semantic_id": "m1",
                "kind": "operating_table",
                "member_unit_ids": ["row"],
                "anchor_unit_ids": ["row"],
                "required_context_unit_ids": [],
                "completeness": "complete",
                "diagnostics": [],
            }
        ],
        "relations": [],
        "coverage": {
            "complete": True,
            "unassigned_unit_ids": ["title", "unit", "header", "note"],
            "deferred_unit_ids": [],
            "limits": {"max_work_units": 2000000, "max_relations": 100000},
        },
        "diagnostics": [],
    }
    layout = {
        "schema_version": "du2-layout-hints/1",
        "source_ref": structure["source_ref"],
        "unit_hints": [
            {"unit_id": x} for x in ["title", "unit", "header", "row", "note"]
        ],
        "groups": [
            {
                "group_id": "g1",
                "kind": "table_region",
                "member_unit_ids": ["row"],
                "required_context_unit_ids": ["title", "unit", "header", "note"],
                "cells": [],
                "confidence": "medium",
                "basis": [],
            }
        ],
        "relations": [],
        "coverage": {"complete": True},
        "diagnostics": [],
    }
    before = copy.deepcopy(structure)
    result = _bridge().bind_layout_context(structure, layout)
    assert structure == before
    assert [u["semantic_id"] for u in result["semantic_units"]] == ["m1"]
    assert result["semantic_units"][0]["required_context_unit_ids"] == [
        "title",
        "unit",
        "header",
        "note",
    ]
    assert result["source_ref"] == structure["source_ref"]


def test_bind_rejects_foreign_source_or_unknown_unit_instead_of_fabricating_context():
    structure = {
        "schema_version": "du-structure/1",
        "source_ref": {"source_id": "s", "source_sha256": "h"},
        "sections": [],
        "semantic_units": [
            {
                "semantic_id": "m1",
                "kind": "paragraph_event",
                "member_unit_ids": ["p"],
                "anchor_unit_ids": [],
                "required_context_unit_ids": [],
                "completeness": "complete",
                "diagnostics": [],
            }
        ],
        "relations": [],
        "coverage": {"complete": True},
        "diagnostics": [],
    }
    layout = {
        "schema_version": "du2-layout-hints/1",
        "source_ref": {"source_id": "other", "source_sha256": "h"},
        "unit_hints": [],
        "groups": [],
        "relations": [],
        "coverage": {"complete": True},
        "diagnostics": [],
    }
    with pytest.raises(ValueError, match="source"):
        _bridge().bind_layout_context(structure, layout)
    layout["source_ref"] = structure["source_ref"]
    layout["groups"] = [
        {
            "group_id": "g",
            "kind": "table_region",
            "member_unit_ids": ["p"],
            "required_context_unit_ids": ["alien"],
            "cells": [],
        }
    ]
    with pytest.raises(ValueError, match="unit"):
        _bridge().bind_layout_context(structure, layout)


def _html_structure(body):
    from company_wiki.document_normalization import normalize_document
    from company_wiki.document_understanding.structure import build_structure

    raw = ("<html><body>" + body + "</body></html>").encode()
    sha = hashlib.sha256(raw).hexdigest()
    normalized = normalize_document(
        raw,
        source_id="urn:company-wiki:source:sha256:" + sha,
        source_sha256=sha,
        mime_type="text/html",
    )
    observation = build_observation(
        normalized.units,
        source_id=normalized.source_id,
        source_sha256=sha,
        mime_type="text/html",
    )
    return observation, build_structure(observation)


def test_real_part_item_display_table_hierarchy_keeps_both_heading_ids():
    obs, structure = _html_structure(
        "<p>PART I — FINANCIAL INFORMATION</p><table><tr><td>Item 2.</td><td>Management Discussion and Analysis</td></tr></table><p>We launched a product.</p><p>PART II — OTHER INFORMATION</p><table><tr><td>Item 2.</td><td>Unregistered Sales of Equity Securities</td></tr></table><p>No shares were sold.</p>"
    )
    texts = {u["unit_id"]: u["text"] for u in obs["units"]}
    parts = [
        s
        for s in structure["sections"]
        if any(texts.get(x, "").startswith("PART ") for x in s["heading_unit_ids"])
    ]
    assert len(parts) == 2
    headings = [
        s
        for s in structure["sections"]
        if any(texts.get(x) == "Item 2." for x in s["heading_unit_ids"])
    ]
    assert len(headings) == 2 and all(len(s["heading_unit_ids"]) == 2 for s in headings)
    assert [s["parent_id"] for s in headings] == [s["section_id"] for s in parts]
    assert all(u["page"] is None for u in obs["units"])


def test_toc_multiline_and_currency_table_do_not_become_item_sections():
    obs, structure = _html_structure(
        "<p>Table of Contents</p><table><tr><td>PART I — FINANCIAL INFORMATION</td><td>3</td></tr><tr><td>Item 2.</td><td>Management Discussion</td><td>8</td></tr></table><p>PART I — FINANCIAL INFORMATION</p><table><tr><td>Item 2.</td><td>USD 1000</td></tr></table><table><tr><td>Item 4.</td><td>Revenue</td></tr><tr><td>Category</td><td>50</td></tr></table><p>Party participation is growing.</p>"
    )
    texts = {u["unit_id"]: u["text"] for u in obs["units"]}
    part_sections = [
        s
        for s in structure["sections"]
        if any(texts.get(x, "").startswith("PART ") for x in s["heading_unit_ids"])
    ]
    assert len(part_sections) == 1
    assert not any(
        texts.get(x, "").startswith("Item ")
        for s in structure["sections"]
        for x in s["heading_unit_ids"]
    )
    assert not any(
        texts.get(x, "").startswith("Party")
        for s in structure["sections"]
        for x in s["heading_unit_ids"]
    )


def test_part_i_boundary_and_legacy_item_depth_with_real_dom_priority():
    from company_wiki.document_understanding.observation_adapter import _heading_level

    assert _heading_level("PART I — FINANCIAL INFORMATION", {}) == 1
    assert _heading_level("PART II — OTHER INFORMATION", {}) == 1
    assert _heading_level("Party participation", {}) is None
    assert _heading_level("Part I of a partnership arrangement.", {}) is None
    assert _heading_level("Item 1. Business", {}) == 1
    assert _heading_level("Item 1. Business", {"heading_level": 3}) == 3


@pytest.mark.parametrize(
    "text",
    ["2030 and thereafter", "545 Washington Boulevard", "325 stores were operating"],
)
def test_plain_year_address_quantity_is_not_numbered_heading(text):
    from company_wiki.document_understanding.structure.contract import ObservationUnit
    from company_wiki.document_understanding.structure.layout import is_heading

    for kind in ("paragraph", "table_row"):
        unit = ObservationUnit(
            {
                "unit_id": "x",
                "ordinal": 0,
                "locator": "original",
                "page": None,
                "text": text,
                "kind": kind,
                "layout": {},
                "hints": {},
            },
            0,
        )
        assert is_heading(unit) is False


def test_explicit_outline_and_real_heading_stay_headings():
    from company_wiki.document_understanding.structure.contract import ObservationUnit
    from company_wiki.document_understanding.structure.layout import is_heading

    for text, hints in [
        ("1.2 Operating progress", {}),
        ("一、主营业务", {}),
        ("2030 outlook", {"heading_level": 2}),
    ]:
        assert (
            is_heading(
                ObservationUnit(
                    {
                        "unit_id": "x",
                        "ordinal": 0,
                        "locator": "original",
                        "page": None,
                        "text": text,
                        "kind": "paragraph",
                        "layout": {},
                        "hints": hints,
                    },
                    0,
                )
            )
            is True
        )


def test_context_binding_charges_members_even_without_required_context():
    structure = {
        "schema_version": "du-structure/1",
        "source_ref": {"source_id": "s", "source_sha256": "h"},
        "sections": [],
        "semantic_units": [
            {
                "semantic_id": "m1",
                "member_unit_ids": ["p"],
                "required_context_unit_ids": [],
                "completeness": "complete",
            }
        ],
        "relations": [],
        "coverage": {"complete": True, "limits": {"max_work_units": 0}},
        "diagnostics": [],
    }
    layout = {
        "schema_version": "du2-layout-hints/1",
        "source_ref": structure["source_ref"],
        "groups": [
            {
                "group_id": "g",
                "kind": "heading",
                "member_unit_ids": ["p"],
                "required_context_unit_ids": [],
                "cells": [],
            }
        ],
        "coverage": {"complete": True},
        "diagnostics": [],
    }
    result = _bridge().bind_layout_context(structure, layout)
    assert result["coverage"]["complete"] is False
    assert any(
        d["code"] == "LAYOUT_BIND_WORK_BUDGET_EXCEEDED" for d in result["diagnostics"]
    )
    assert result["semantic_units"][0]["completeness"] == "partial"
    assert result["semantic_units"][0]["required_context_unit_ids"] == []
    assert structure["coverage"]["complete"] is True


def test_numeric_notes_stay_under_item_before_next_item_returns_to_part():
    obs, structure = _html_structure(
        "<p>PART I — FINANCIAL INFORMATION</p><table><tr><td>Item 1.</td><td>Financial Statements</td></tr></table><p>1. Organization:</p><p>Company description.</p><p>2. Accounting policies:</p><p>A policy description.</p><p>3. Subsequent events:</p><p>A later event description.</p><table><tr><td>Item 2.</td><td>Management Discussion and Analysis</td></tr></table><p>New business progress.</p>"
    )
    texts = {u["unit_id"]: u["text"] for u in obs["units"]}
    sections = structure["sections"]
    part = next(
        s
        for s in sections
        if any(texts.get(x, "").startswith("PART I") for x in s["heading_unit_ids"])
    )
    item1 = next(
        s
        for s in sections
        if any(texts.get(x) == "Item 1." for x in s["heading_unit_ids"])
    )
    item2 = next(
        s
        for s in sections
        if any(texts.get(x) == "Item 2." for x in s["heading_unit_ids"])
    )
    notes = [
        s
        for s in sections
        if any(
            texts.get(x, "").startswith(
                ("1. Organization", "2. Accounting", "3. Subsequent")
            )
            for x in s["heading_unit_ids"]
        )
    ]
    assert len(notes) == 3 and all(s["parent_id"] == item1["section_id"] for s in notes)
    assert (
        item1["parent_id"] == part["section_id"]
        and item2["parent_id"] == part["section_id"]
    )


def test_rotated_pdf_dimensions_share_the_original_text_coordinate_frame():
    fitz = pytest.importorskip("fitz")
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=800)
        page.insert_text((70, 700), "Measured frame", fontsize=20)
        page.set_rotation(90)
        data = doc.tobytes()
    sha = hashlib.sha256(data).hexdigest()
    parsed = pdf.parse_pdf_bytes(
        data, source_id="urn:sha256:" + sha, source_sha256=sha, table_pages=()
    )
    unit = next(u for u in parsed.units if u.raw_text == "Measured frame")
    assert unit.metadata["page_width"] == 600
    assert unit.metadata["page_height"] == 800
    assert unit.metadata["bbox"][3] > 600
    assert unit.metadata["bbox"][3] <= unit.metadata["page_height"]


def test_fragment_font_lookup_uses_indexed_runs_instead_of_rescanning_a_block():
    class Counted(list):
        reads = 0

        def __getitem__(self, key):
            self.reads += 1
            return super().__getitem__(key)

    runs = Counted([(n * 10, n * 10 + 9, 10 + n % 2, "regular") for n in range(10000)])
    ends = Counted([run[1] for run in runs])
    state = pdf._PdfParseState(
        source_id="s", source_sha256="0" * 64, parser_version="p", language="en"
    )
    state.page_geometry[1] = {"block_fonts": {0: {"runs": runs, "ends": ends}}}
    measured = pdf._pdf_geometry_metadata(
        state, 1, block_no=0, char_start=50000, char_end=50009
    )
    assert measured["font_size"] == 10
    assert runs.reads + ends.reads < 30
