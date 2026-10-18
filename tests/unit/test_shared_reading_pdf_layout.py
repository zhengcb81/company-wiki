"""Opt-in PDF layout reuses one native text read and real table results."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
from importlib import import_module
from types import SimpleNamespace
import unicodedata

import pytest

from company_wiki.source_catalog import narrative_evidence as pdf
from company_wiki.source_contract import source_id_for_sha256


def _bytes(*, pages=1, rotation=0, crop=False, table=False):
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    for number in range(pages):
        page = document.new_page(width=600, height=800)
        page.insert_text((75, 100), "Operating update", fontsize=20, fontname="hebo")
        page.insert_text(
            (75, 150),
            "Our services depend on metered consumption rather than paid seats.",
        )
        page.insert_text((75, 205), "Repeated word and repeated word remain distinct.")
        if table:
            for x in (70, 250, 420):
                page.draw_line((x, 320), (x, 380))
            for y in (320, 350, 380):
                page.draw_line((70, y), (420, y))
            for y, first, second in (
                (341, "Service units", "FY 2026"),
                (371, "Active devices", "19,400"),
            ):
                page.insert_text((80, y), first)
                page.insert_text((260, y), second)
        if crop:
            page.set_cropbox(fitz.Rect(20, 30, 580, 770))
        page.set_rotation(rotation)
    raw = document.tobytes()
    document.close()
    return raw


def _parse(raw, *, version="0.9.0", **kwargs):
    sha = hashlib.sha256(raw).hexdigest()
    return pdf.parse_pdf_bytes(
        raw,
        source_id=source_id_for_sha256(sha),
        source_sha256=sha,
        language="en",
        selector_version=version,
        table_pages=kwargs.pop("table_pages", ()),
        **kwargs,
    )


def _identity(parsed):
    return [
        (
            u.unit_id,
            u.source_id,
            u.raw_text,
            u.coordinates.locator(),
            u.parser_name,
            u.parser_version,
            u.unit_kind,
            u.source_role,
        )
        for u in parsed.units
    ]


def _fine(parsed, kind):
    return [
        item
        for unit in parsed.units
        for item in unit.metadata.get("reading_layout", {})
        .get("upstream_hints", {})
        .get(kind, ())
    ]


def test_same_source_text_ids_locators_and_parser_versions_survive_rich_layout():
    raw = _bytes(table=True)
    legacy = _parse(raw, version="0.8.0", table_pages=(1,))
    rich = _parse(raw, table_pages=(1,))
    assert _identity(rich) == _identity(legacy)
    assert legacy.layout_coverage is None and legacy.layout_diagnostics == ()
    assert not _fine(legacy, "words") and not _fine(legacy, "cells")
    assert _fine(rich, "words") and _fine(rich, "cells")


def test_one_textpage_supplies_dict_and_native_words_without_a_second_page_text_read(
    monkeypatch,
):
    fitz = pytest.importorskip("fitz")
    raw = _bytes(pages=2)
    calls = {"page_text": [], "textpage": [], "native_words": []}
    original_text = fitz.Page.get_text
    original_textpage = fitz.Page.get_textpage
    original_words = fitz.TextPage.extractWORDS

    def tracked_text(page, *args, **kwargs):
        calls["page_text"].append((args, kwargs))
        return original_text(page, *args, **kwargs)

    def tracked_textpage(page, *args, **kwargs):
        calls["textpage"].append(kwargs)
        return original_textpage(page, *args, **kwargs)

    def tracked_words(textpage, *args, **kwargs):
        words = original_words(textpage, *args, **kwargs)
        calls["native_words"].append(deepcopy(words))
        return words

    monkeypatch.setattr(fitz.Page, "get_text", tracked_text)
    monkeypatch.setattr(fitz.Page, "get_textpage", tracked_textpage)
    monkeypatch.setattr(fitz.TextPage, "extractWORDS", tracked_words)
    parsed = _parse(raw)
    assert (
        len(calls["page_text"])
        == len(calls["textpage"])
        == len(calls["native_words"])
        == 2
    )
    assert all(
        args == ("dict",) and kwargs["textpage"] is not None
        for args, kwargs in calls["page_text"]
    )
    assert all(kwargs["flags"] == fitz.TEXTFLAGS_DICT for kwargs in calls["textpage"])
    assert _fine(parsed, "words")
    native = {
        (tuple(word[:4]), word[4])
        for page_words in calls["native_words"]
        for word in page_words
    }
    assert all(
        (tuple(word["bbox"]), word["text"]) in native for word in _fine(parsed, "words")
    )


def test_find_tables_and_extract_are_reused_once_and_cells_have_real_separate_columns(
    monkeypatch,
):
    fitz = pytest.importorskip("fitz")
    calls = []
    original = fitz.Page.find_tables

    def tracked(page, *args, **kwargs):
        calls.append(page.number)
        return original(page, *args, **kwargs)

    monkeypatch.setattr(fitz.Page, "find_tables", tracked)
    parsed = _parse(_bytes(table=True), table_pages=(1,))
    assert calls == [0]
    rows = [unit for unit in parsed.units if unit.unit_kind == "pdf_table_row"]
    assert rows
    cells = _fine(parsed, "cells")
    assert {cell["column"] for cell in cells} == {0, 1}
    assert len({tuple(cell["bbox"]) for cell in cells}) == len(cells)
    assert all(cell["table_id"] == "p1:t0" for cell in cells)
    for row in rows:
        for cell in row.metadata["reading_layout"]["upstream_hints"]["cells"]:
            assert cell["bbox"] != list(row.metadata["bbox"])
            assert row.raw_text[cell["char_start"] : cell["char_end"]] == cell["text"]


def test_spaces_and_inline_numbers_never_become_fine_cells():
    parsed = _parse(_bytes())
    assert _fine(parsed, "words")
    assert not _fine(parsed, "cells")
    assert all(
        unit.metadata["reading_layout"]["upstream_hints"]["geometry_granularity"]
        == "word"
        for unit in parsed.units
    )


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_native_unrotated_coordinates_keep_rotation_and_actual_page_frame(rotation):
    parsed = _parse(_bytes(rotation=rotation))
    assert parsed.layout_coverage["complete"]
    for unit in parsed.units:
        layout = unit.metadata["reading_layout"]["layout"]
        assert layout["coordinate_frame"] == "dict"
        assert layout["rotation"] == rotation
        assert layout["page_width"] == 600
        assert layout["page_height"] == 800
        assert all(
            0 <= word["bbox"][0] < word["bbox"][2] <= 600
            for word in unit.metadata["reading_layout"]["upstream_hints"]["words"]
        )


def test_cropbox_origin_is_carried_without_shifting_native_coordinates():
    parsed = _parse(_bytes(crop=True, rotation=90))
    assert parsed.layout_coverage["complete"]
    for unit in parsed.units:
        layout = unit.metadata["reading_layout"]["layout"]
        assert layout["cropbox"] == [20.0, 30.0, 580.0, 770.0]
        assert layout["cropbox_position"] == [20.0, 30.0]
        assert layout["page_width"] == 560
        assert layout["page_height"] == 740
    title = next(unit for unit in parsed.units if unit.raw_text == "Operating update")
    assert title.metadata["reading_layout"]["upstream_hints"]["words"][0]["bbox"][
        0
    ] == pytest.approx(55)


@pytest.mark.parametrize(
    "limits",
    [
        {"max_work_units": 0},
        {"max_fine_elements": 0},
        {"max_units": 0},
        {"max_pages": 0},
    ],
)
def test_zero_geometry_budget_preserves_every_source_unit_and_marks_partial(limits):
    raw = _bytes()
    old = _parse(raw, version="0.8.0")
    new = _parse(raw, layout_limits=limits)
    assert _identity(new) == _identity(old)
    assert not new.layout_coverage["complete"]
    assert new.layout_coverage["processed_unit_count"] == 0
    assert new.layout_coverage["deferred_unit_count"] == len(new.units)
    assert new.layout_diagnostics


def test_geometry_limits_are_global_across_pages_not_restarted_for_each_page(monkeypatch):
    fitz = pytest.importorskip("fitz")
    word_reads = []
    original_words = fitz.TextPage.extractWORDS

    def tracked_words(textpage, *args, **kwargs):
        word_reads.append(1)
        return original_words(textpage, *args, **kwargs)

    monkeypatch.setattr(fitz.TextPage, "extractWORDS", tracked_words)
    parsed = _parse(_bytes(pages=2), layout_limits={"max_pages": 1})
    assert not parsed.layout_coverage["complete"]
    assert parsed.layout_coverage["processed_page_count"] == 1
    assert any(unit.coordinates.page_number == 2 for unit in parsed.units)
    assert len(word_reads) == 1
    assert any(unit.metadata.get("reading_layout", {}).get("upstream_hints", {}).get("words")
               for unit in parsed.units if unit.coordinates.page_number == 1)
    for unit in parsed.units:
        if unit.coordinates.page_number == 2:
            hints = unit.metadata.get("reading_layout", {}).get("upstream_hints", {})
            # Coarse bbox/font observations reuse the original DICT read and
            # do not spend or renew the separately bounded fine geometry.
            assert not hints.get("words") and not hints.get("cells")
            assert hints.get("geometry_granularity") == "block"


def test_unit_and_fine_limits_defer_geometry_without_truncating_source_text():
    parsed = _parse(_bytes(), layout_limits={"max_units": 1, "max_fine_elements": 2})
    assert len(parsed.units) == 3
    assert parsed.layout_coverage["processed_unit_count"] <= 1
    assert parsed.layout_coverage["fine_element_count"] <= 2
    assert not parsed.layout_coverage["complete"]


def test_shared_deadline_exhaustion_keeps_native_originals_and_does_not_claim_complete():
    raw = _bytes(pages=2)
    parsed = _parse(raw, layout_max_seconds=0)
    assert _identity(parsed) == _identity(_parse(raw, version="0.8.0"))
    assert not parsed.layout_coverage["complete"]
    assert any(
        item["code"] == "LAYOUT_DEADLINE_EXCEEDED" for item in parsed.layout_diagnostics
    )
    assert not _fine(parsed, "words")


def test_repeated_words_are_bound_to_their_own_native_occurrences():
    parsed = _parse(_bytes())
    unit = next(
        unit for unit in parsed.units if unit.raw_text.startswith("Repeated word")
    )
    repeats = [
        word
        for word in unit.metadata["reading_layout"]["upstream_hints"]["words"]
        if word["text"].casefold() == "word"
    ]
    assert len(repeats) == 2
    assert repeats[0]["char_start"] != repeats[1]["char_start"]
    assert repeats[0]["native_index"] != repeats[1]["native_index"]
    for word in repeats:
        assert unit.raw_text[word["char_start"] : word["char_end"]] == word["text"]


def test_feature_identity_is_explicit_and_no_entire_page_snapshot_is_persisted():
    module = import_module("company_wiki.source_catalog.narrative_pdf_layout")
    assert module.PDF_READING_LAYOUT_FEATURE_VERSION
    parsed = _parse(_bytes())
    assert (
        parsed.layout_coverage["feature_version"]
        == module.PDF_READING_LAYOUT_FEATURE_VERSION
    )
    assert all("snapshot" not in unit.metadata for unit in parsed.units)
    assert all(
        unit.metadata["reading_layout"]["feature_version"]
        == module.PDF_READING_LAYOUT_FEATURE_VERSION
        for unit in parsed.units
    )
    assert all(
        unit.metadata["geometry_feature_version"] == pdf.PDF_GEOMETRY_FEATURE_VERSION
        for unit in parsed.units
    )


def test_rich_layout_preserves_all_old_metadata_and_durable_evidence_identity():
    import json
    from types import MappingProxyType

    from company_wiki.automation.narrative_contracts import (
        NarrativeBundle,
        NarrativeSelectResult,
    )
    from company_wiki.automation.narrative_model import NarrativeModelRequest
    from company_wiki.source_catalog.narrative_native_ranges import (
        NATIVE_PAGE_VIEW_FEATURE_VERSION,
    )
    from support.narrative_model_request_fixture import selection
    from unit.test_narrative_job_contracts import _bundle

    raw = _bytes(table=True)
    legacy = _parse(raw, version="0.8.0", table_pages=(1,))
    rich = _parse(raw, table_pages=(1,))
    shared_views = {}
    durable = []
    for old, new in zip(legacy.units, rich.units, strict=True):
        transient = {"reading_layout"}
        if new.unit_kind == "pdf_text_block":
            transient.add("native_source_view")
            view = new.metadata["native_source_view"]
            assert isinstance(view, MappingProxyType)
            assert set(view) == {"schema_version", "text", "page_view_sha256", "blocks", "by_block"}
            assert view["schema_version"] == NATIVE_PAGE_VIEW_FEATURE_VERSION
            assert view["page_view_sha256"] == hashlib.sha256(view["text"].encode()).hexdigest()
            page = new.coordinates.page_number
            if page in shared_views:
                assert view is shared_views[page]
            else:
                shared_views[page] = view
            with pytest.raises(TypeError):
                view["text"] = "forbidden mutation"
            with pytest.raises(TypeError):
                view["blocks"][0]["source_text"] = "forbidden mutation"
        # Only these defined transient fields may differ. Every old field and
        # any unexpected new field remain part of the exact metadata contract.
        assert not set(old.metadata).intersection(transient)
        assert set(new.metadata) == set(old.metadata) | transient
        assert {k: v for k, v in new.metadata.items() if k not in transient} == dict(
            old.metadata
        )
        options = {
            "topics": ("business_progress",),
            "selection_reasons": ("business_fact",),
        }
        old_span, new_span = (
            old.to_evidence_span(**options),
            new.to_evidence_span(**options),
        )
        assert old_span == new_span
        assert old.unit_id == new.unit_id
        assert "reading_layout" not in new_span.structured_value
        assert "native_source_view" not in new_span.structured_value
        durable.append(new_span)
        drifting = deepcopy(new.metadata["reading_layout"])
        drifting["upstream_hints"]["words"] = [
            {"bbox": [1, 2, 3, 4], "text": "irrelevant fine drift"}
        ]
        altered = replace(new, metadata=dict(new.metadata, reading_layout=drifting))
        assert altered.to_evidence_span(**options).span_id == old_span.span_id
        if "native_source_view" in transient:
            changed_view = replace(new, metadata=dict(new.metadata, native_source_view={
                "text": "private-transient-canary-never-export",
            }))
            assert changed_view.to_evidence_span(**options) == old_span
        unknown = replace(new, metadata=dict(new.metadata, unknown_metadata="must-remain-durable"))
        unknown_span = unknown.to_evidence_span(**options)
        assert unknown_span.structured_value["unknown_metadata"] == "must-remain-durable"
        assert unknown_span.span_id != old_span.span_id

    assert sum(unit.unit_kind == "pdf_text_block" for unit in rich.units) >= 2
    assert len(shared_views) == 1
    # Exercise actual public selection/model/Bundle serialization, without a
    # supplier, so a private page view cannot silently escape via a wire port.
    wire = selection(count=len(durable)).to_dict()
    wire["source_ref"] = {"schema_version": "2.0", "document_id": "synthetic-layout-document",
        "source_id": rich.source_id, "content_sha256": rich.source_sha256,
        "byte_size": len(raw), "mime_type": "application/pdf"}
    wire["source_metadata"] = {"source_class": "filing", "title": "Synthetic annual report",
                               "document_kind": "annual_report", "language": "en"}
    wire["parser"] = {"name": durable[0].parser_name, "version": durable[0].parser_version}
    wire["selector"] = {"name": "selective-narrative-selector", "version": "0.9.0"}
    wire["evidence_spans"] = [span.to_dict() for span in durable]
    wire["selection"].update(status="selected", source_units=len(rich.units),
        candidate_count=len(durable), omitted_candidate_count=0, dropped_financial_count=0,
        pages_total=1, pages_read=1, tables_total=1, tables_scanned=1)
    selected = NarrativeSelectResult.from_dict(wire)
    model_wire = NarrativeModelRequest.from_selection(selected).data_json
    bundle_wire = _bundle(evidence=wire["evidence_spans"])
    for field in ("source_ref", "source_metadata", "selection", "prompt_review"):
        bundle_wire[field] = wire[field]
    bundle_wire["versions"].update(parser=wire["parser"]["version"],
                                    selector=wire["selector"]["version"])
    bundle_wire["summary"]["draft"].update(source_id=rich.source_id,
        source_sha256=rich.source_sha256, language="en")
    support = next(span for span in durable if "metered consumption" in span.raw_text)
    bundle_wire["summary"]["draft"]["claims"][0].update(
        text=support.raw_text, evidence_ids=[support.span_id])
    bundle = NarrativeBundle.from_dict(bundle_wire)
    for encoded in (json.dumps(selected.to_dict()), model_wire, json.dumps(bundle.to_dict())):
        for private in ("native_source_view", "reading_layout", "page_view_sha256", "source_text",
                        "private-transient-canary-never-export"):
            assert private not in encoded


def test_production_default_parser_gets_opt_in_but_legacy_custom_parser_keeps_its_interface():
    from company_wiki.automation.narrative_select import NarrativeSelectHandler

    raw = _bytes()
    sha = hashlib.sha256(raw).hexdigest()
    payload = SimpleNamespace(
        source_ref=SimpleNamespace(
            source_id=source_id_for_sha256(sha), content_sha256=sha
        ),
        source_metadata=SimpleNamespace(language="en", title="Annual Report", document_kind="annual_report"),
    )
    default = NarrativeSelectHandler(reader=None, selector_version="0.9.0")
    assert default._parse_pdf(payload, raw).layout_coverage is not None
    calls = []

    def custom(data, *, source_id, source_sha256, language, full_table_scan=False):
        calls.append(True)
        return pdf.parse_pdf_bytes(
            data,
            source_id=source_id,
            source_sha256=source_sha256,
            language=language,
            full_table_scan=full_table_scan,
        )

    compatible = NarrativeSelectHandler(
        reader=None, pdf_parser=custom, selector_version="0.9.0"
    )
    parsed = compatible._parse_pdf(payload, raw)
    assert calls == [True]
    assert parsed.layout_coverage is None


def _native_page(text, words, *, spans=None, image_before=False, crop=True):
    """Native API-shaped observations for absent/malformed capability controls."""
    spans = spans or [
        {
            "text": text,
            "bbox": (10, 10, 390, 25),
            "size": 11,
            "flags": 0,
            "font": "Regular",
        }
    ]
    block = {"type": 0, "bbox": (10, 10, 390, 25), "lines": [{"spans": spans}]}
    snapshot = {
        "width": 600,
        "height": 800,
        "blocks": ([{"type": 1}] if image_before else []) + [block],
    }
    attrs = {
        "get_text": lambda *a, **k: deepcopy(snapshot),
        "get_textpage": lambda *a, **k: SimpleNamespace(
            extractWORDS=lambda: deepcopy(words)
        ),
        "rotation": 0,
        "rect": SimpleNamespace(width=600, height=800),
    }
    if crop:
        attrs.update(
            cropbox=(0, 0, 600, 800), cropbox_position=SimpleNamespace(x=0, y=0)
        )
    return SimpleNamespace(**attrs)


def _native_parse(page, **kwargs):
    document = [page]
    sha = "a" * 64
    return pdf._parse_pdf_document(
        document,
        source_id=source_id_for_sha256(sha),
        source_sha256=sha,
        language="en",
        table_pages=(),
        selector_version="0.9.0",
        **kwargs,
    )


def test_nfc_character_ranges_still_refer_to_the_original_unit_not_a_rewritten_shadow():
    page = _native_page(
        "cafe\u0301 operators",
        [
            (10, 10, 45, 25, "cafe\u0301", 0, 0, 0),
            (50, 10, 105, 25, "operators", 0, 0, 1),
        ],
    )
    parsed = _native_parse(page)
    assert parsed.layout_coverage["complete"]
    assert parsed.units[0].raw_text == "café operators"
    for word in _fine(parsed, "words"):
        assert parsed.units[0].raw_text[
            word["char_start"] : word["char_end"]
        ] == unicodedata.normalize("NFC", word["text"])
        assert word["char_alignment"] == "exact"


def test_source_block_line_indices_bind_distinct_fragments_without_copying_whole_block():
    page = _native_page(
        "alpha! beta!",
        [(10, 10, 50, 25, "alpha!", 0, 0, 0), (60, 10, 100, 25, "beta!", 0, 0, 1)],
        image_before=True,
    )
    parsed = _native_parse(page)
    assert [unit.raw_text for unit in parsed.units] == ["alpha!", "beta!"]
    assert parsed.layout_coverage["complete"]
    words = [_fine(replace(parsed, units=(unit,)), "words") for unit in parsed.units]
    assert [[word["text"] for word in group] for group in words] == [
        ["alpha!"],
        ["beta!"],
    ]
    assert words[0][0]["bbox"] != words[1][0]["bbox"]
    for unit in parsed.units:
        span = unit.metadata["reading_layout"]["upstream_hints"]["spans"][0]
        assert span["block"] == 1 and span["partial_span"]
        assert (span["char_start"], span["char_end"]) == (0, len(unit.raw_text))


def test_native_word_crossing_sentence_boundary_is_not_given_a_fake_subword_box():
    parsed = _native_parse(
        _native_page("alpha!beta!", [(10, 10, 100, 25, "alpha!beta!", 0, 0, 0)])
    )
    assert [unit.raw_text for unit in parsed.units] == ["alpha!", "beta!"]
    assert not _fine(parsed, "words")
    assert not parsed.layout_coverage["complete"]
    assert _fine(parsed, "font_runs")  # real intersecting style spans remain usable


@pytest.mark.parametrize(
    "words",
    [
        [],
        [(10, 10, 50, 25, "not-the-source", 0, 0, 0)],
        [(10, 10, 50, 25, "alpha", 9, 0, 0)],
    ],
)
def test_missing_or_wrong_native_word_provenance_is_partial_without_guessing(words):
    parsed = _native_parse(_native_page("alpha", words))
    assert parsed.units[0].raw_text == "alpha"
    assert not parsed.layout_coverage["complete"]
    assert not _fine(parsed, "words")


def test_missing_crop_origin_is_diagnosed_instead_of_assuming_zero():
    parsed = _native_parse(
        _native_page("alpha", [(10, 10, 50, 25, "alpha", 0, 0, 0)], crop=False)
    )
    assert not parsed.layout_coverage["complete"]
    assert any(
        row["code"] == "CROPBOX_FRAME_UNAVAILABLE" for row in parsed.layout_diagnostics
    )
    assert (
        parsed.units[0].metadata["reading_layout"]["layout"]["cropbox_position"] is None
    )


def test_exact_native_font_runs_keep_measured_span_boxes_and_mixed_style_ranges():
    spans = [
        {
            "text": "alpha ",
            "bbox": (10, 10, 50, 25),
            "size": 11,
            "flags": 0,
            "font": "Regular",
        },
        {
            "text": "beta",
            "bbox": (60, 10, 100, 25),
            "size": 16,
            "flags": 16,
            "font": "Bold",
        },
    ]
    parsed = _native_parse(
        _native_page(
            "alpha beta",
            [(10, 10, 50, 25, "alpha", 0, 0, 0), (60, 10, 100, 25, "beta", 0, 0, 1)],
            spans=spans,
        )
    )
    assert parsed.layout_coverage["complete"]
    runs = _fine(parsed, "font_runs")
    assert [
        (r["char_start"], r["char_end"], r["font_size"], r["font_weight"]) for r in runs
    ] == [(0, 6, 11, "regular"), (6, 10, 16, "bold")]
    actual_spans = _fine(parsed, "spans")
    assert [tuple(r["bbox"]) for r in actual_spans] == [span["bbox"] for span in spans]


def test_optional_projection_failure_cannot_discard_original_text_or_tables(
    monkeypatch,
):
    module = import_module("company_wiki.source_catalog.narrative_pdf_layout")

    def unavailable(*args, **kwargs):
        raise ValueError("native optional capability unavailable")

    monkeypatch.setattr(module, "project_layout_snapshot", unavailable)
    monkeypatch.setattr(module.PdfLayoutCollector, "capture_table", unavailable)
    raw = _bytes(table=True)
    new, old = (
        _parse(raw, table_pages=(1,)),
        _parse(raw, version="0.8.0", table_pages=(1,)),
    )
    assert _identity(new) == _identity(old)
    assert new.errors == old.errors == ()
    assert not new.layout_coverage["complete"]
    assert {d["code"] for d in new.layout_diagnostics} >= {
        "NATIVE_TABLE_LAYOUT_CAPTURE_FAILED",
        "LAYOUT_PROJECTION_FAILED",
    }


def test_native_capture_fine_cap_is_document_wide_before_any_page_projection(
    monkeypatch,
):
    module = import_module("company_wiki.source_catalog.narrative_pdf_layout")
    instances = []
    original = module.PdfLayoutCollector.__init__

    def tracked(instance, **kwargs):
        original(instance, **kwargs)
        instances.append(instance)

    monkeypatch.setattr(module.PdfLayoutCollector, "__init__", tracked)
    parsed = _parse(_bytes(pages=3), layout_limits={"max_fine_elements": 12})
    collector = instances[0]
    assert collector.captured_fine <= 12
    assert parsed.layout_coverage["fine_element_count"] <= 12
    assert not parsed.layout_coverage["complete"]
    assert collector.pages == {}  # native transient records released on all paths


def test_deadline_is_shared_between_capture_and_projection_not_reset(monkeypatch):
    module = import_module("company_wiki.source_catalog.narrative_pdf_layout")
    clock = [10.0]
    monkeypatch.setattr(module, "monotonic", lambda: clock[0])
    collector = module.PdfLayoutCollector(max_seconds=2)
    page = _native_page("alpha", [(10, 10, 50, 25, "alpha", 0, 0, 0)])
    collector.read_snapshot(page, 1)
    clock[0] = 12.0
    original = _native_parse(page)
    assert collector.project_page(1, original.units) == original.units
    coverage, diagnostics = collector.summary(original.units)
    assert not coverage["complete"] and coverage["processed_unit_count"] == 0
    assert any(d["code"] == "LAYOUT_DEADLINE_EXCEEDED" for d in diagnostics)


def test_real_native_image_blocks_do_not_shift_words_onto_the_wrong_source_paragraph():
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page(width=600, height=800)
    page.insert_text((75, 100), "Repeated word before image.")
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 3, 3), False)
    pixmap.clear_with(100)
    page.insert_image(fitz.Rect(50, 120, 90, 160), pixmap=pixmap)
    page.insert_text((75, 200), "Repeated word after image.")
    raw = document.tobytes()
    document.close()
    parsed = _parse(raw)
    assert parsed.layout_coverage["complete"]
    assert [u.metadata["pdf_block"] for u in parsed.units] == [0, 2]
    for unit in parsed.units:
        words = unit.metadata["reading_layout"]["upstream_hints"]["words"]
        assert " ".join(w["text"] for w in words) == unit.raw_text
        assert all(
            unit.raw_text[w["char_start"] : w["char_end"]] == w["text"] for w in words
        )
    before_word = _fine(replace(parsed, units=(parsed.units[0],)), "words")[1]
    after_word = _fine(replace(parsed, units=(parsed.units[1],)), "words")[1]
    assert before_word["bbox"][1] < 100 < after_word["bbox"][1]


def _native_table_rows(rows, boxes):
    module = import_module("company_wiki.source_catalog.narrative_pdf_layout")
    collector = module.PdfLayoutCollector()
    collector.read_snapshot(
        _native_page("context", [(10, 10, 50, 25, "context", 0, 0, 0)]), 1
    )
    sha = "b" * 64
    state = pdf._PdfParseState(
        source_id_for_sha256(sha),
        sha,
        pdf.NARRATIVE_PARSER_VERSION,
        "zh",
        layout_collector=collector,
    )
    state.page_geometry[1] = {"page_width": 600, "page_height": 800}
    table = SimpleNamespace(
        extract=lambda: rows,
        bbox=(10, 30, 300, 90),
        rows=[SimpleNamespace(cells=row) for row in boxes],
    )
    pdf._emit_pdf_table(state, 1, 0, table)
    units = collector.project_page(1, state.units)
    coverage, diagnostics = collector.summary(units)
    return units, coverage, diagnostics


def test_a_missing_earlier_cell_box_cannot_relocate_a_later_cell_character_range():
    units, coverage, diagnostics = _native_table_rows(
        [["Product", "Orders", "Units"], ["Service A", "840", "1,940"]],
        [
            [(10, 30, 100, 60), (100, 30, 200, 60), (200, 30, 300, 60)],
            [None, (100, 60, 200, 90), (200, 60, 300, 90)],
        ],
    )
    row = units[1]
    cells = row.metadata["reading_layout"]["upstream_hints"]["cells"]
    assert [cell["column"] for cell in cells] == [1, 2]
    assert [cell["char_start"] for cell in cells] == [12, 18]
    assert all(
        row.raw_text[c["char_start"] : c["char_end"]] == c["text"]
        and c["char_alignment"] == "exact"
        for c in cells
    )
    assert not coverage["complete"]
    assert any(d["code"] == "NATIVE_CELL_GEOMETRY_UNAVAILABLE" for d in diagnostics)


def test_qa_fragments_keep_actual_parent_cell_offsets_without_inventing_fragment_boxes():
    cell = "问：产品交付有何变化？答：客户订单交付增加。"
    units, coverage, _diagnostics = _native_table_rows([[cell]], [[(10, 30, 300, 90)]])
    assert {unit.source_role for unit in units} == {"investor_question", "management"}
    assert coverage["complete"]
    for unit in units:
        fine = unit.metadata["reading_layout"]["upstream_hints"]["cells"][0]
        assert fine["bbox"] == [10, 30, 300, 90]
        assert fine["row"] == 0 and fine["column"] == 0 and fine["table_id"] == "p1:t0"
        assert fine["partial_cell"] is True
        assert fine["native_cell_char_start"] == unit.metadata["cell_fragment_start"]
        assert fine["native_cell_char_end"] == unit.metadata["cell_fragment_end"]
        assert (
            unicodedata.normalize(
                "NFC",
                cell[fine["native_cell_char_start"] : fine["native_cell_char_end"]],
            ).strip()
            == unit.raw_text
        )


def test_legacy_page_without_new_textpage_keywords_uses_original_text_and_marks_partial():
    page = _native_page("alpha", [])
    page.get_textpage = lambda: None
    parsed = _native_parse(page)
    assert parsed.errors == () and [u.raw_text for u in parsed.units] == ["alpha"]
    assert not parsed.layout_coverage["complete"]
    assert any(
        d["code"] == "NATIVE_TEXT_PAGE_UNAVAILABLE" for d in parsed.layout_diagnostics
    )


def test_geometry_work_exhaustion_cannot_restart_on_a_later_small_charge():
    module = import_module("company_wiki.source_catalog.narrative_pdf_layout")
    collector = module.PdfLayoutCollector(limits={"max_work_units": 4})
    assert collector._take(3)
    assert not collector._take(2)
    assert not collector._take(1)
    assert collector.work == 3
