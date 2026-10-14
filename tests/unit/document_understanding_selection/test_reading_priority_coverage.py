"""Native outline identities control reading priority, without product guesses."""

from copy import deepcopy
from dataclasses import replace

import pytest

from company_wiki.document_understanding import understand_units
from company_wiki.document_understanding.strategy_binding import bind_reading_plan
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def _pipeline(texts, *, form="10-K", sources=None, native_metadata=None):
    source = source_id_for_sha256("a" * 64)
    units = tuple(_make_unit(source_id=source if sources is None else sources[index],
        parser_version="1.0.0", coordinates=EvidenceCoordinates(paragraph_index=index),
        raw_text=text, unit_kind="html_heading" if (native_metadata or {}).get(index, {}).get("heading_level") else "html_paragraph",
        source_role="company_filing", language="en",
        metadata={"dom_path": f"0.1.{index}.0", **(native_metadata or {}).get(index, {})}) for index, text in enumerate(texts))
    result = understand_units(units, source_id=source, source_sha256="a" * 64,
        mime_type="text/html", language="en", metadata={"form_type": "unknown"})
    assert result["route"].get("form_type") == form
    return units, result


def _view(units, pipeline, ordinal):
    return pipeline["reading_plan"]["unit_profiles"][units[ordinal].unit_id]


def _bind(heading, entries, *, form="10-K", part=None):
    units = [{"unit_id": "heading", "ordinal": 1, "text": heading},
             {"unit_id": "body", "ordinal": 2, "text": "The charges depend on resources consumed."}]
    sections = [{"section_id": "item", "parent_id": "part" if part else None,
                 "heading_unit_ids": ["heading"], "body_unit_ids": ["body"], "section_role": "unknown"}]
    if part:
        units.insert(0, {"unit_id": "part-heading", "ordinal": 0, "text": part})
        sections.insert(0, {"section_id": "part", "parent_id": None,
                           "heading_unit_ids": ["part-heading"], "body_unit_ids": [], "section_role": "unknown"})
    profile = {"profile_id": "supplied-scoped-profile", "form_type": form,
               "family": "annual", "regime": "sec", "section_rules": entries}
    original = {"units": units}
    before = deepcopy(original)
    result = bind_reading_plan(original, {"sections": sections}, route={}, profile=profile)
    assert original == before
    return result


def _rule(title, *, role="business", priority=1, part=None):
    path = [[part], [title]] if part else [[title]]
    return {"role": role, "aliases": [title], "heading_path": path, "priority": priority, "questions": []}


def test_actual_form_scoped_native_bare_item_reads_its_declared_business_section():
    texts = ["FORM 10-K", "PART I", "Item 1", "GENERAL",
             "Our service charges depend on resources the customers consume."]
    units, pipeline = _pipeline(texts)
    view = _view(units, pipeline, 4)
    assert view["section_role"] == "business"
    assert view["priority"] == 1
    assert tuple(unit.raw_text for unit in units) == tuple(texts)
    assert pipeline["observation"]["metadata"]["form_type"] == "unknown"


def test_repeated_bare_part_and_item_banners_do_not_reset_business_priority():
    texts = ["FORM 10-K", "PART I", "Item 1", "GENERAL", "Our products serve industrial customers.",
             "PART I", "Item 1", "OPERATING SEGMENTS", "Our segment charges depend on subscriptions.",
             "PART I", "Item 1", "An Arbitrary Service Group", "Our service charges depend on resources consumed."]
    units, pipeline = _pipeline(texts)
    for index in (4, 8, 12):
        assert _view(units, pipeline, index)["section_role"] == "business"
        assert _view(units, pipeline, index)["priority"] == 1


def test_split_native_number_and_real_title_keeps_the_original_ids():
    units, pipeline = _pipeline(["FORM 10-K", "PART I", "Item 1", "BUSINESS",
                                 "Our service charges depend on resources consumed."])
    assert _view(units, pipeline, 4)["section_role"] == "business"
    assert _view(units, pipeline, 4)["priority"] == 1
    assert {u["unit_id"] for u in pipeline["observation"]["units"]} == {u.unit_id for u in units}


@pytest.mark.parametrize("heading", ["Item 1A", "Item 10", "Item 11", "Item 01"])
def test_standard_item_identity_has_complete_number_and_letter_boundaries(heading):
    result = _bind(heading, [_rule("Item 1. Business")])
    assert result["unit_profiles"]["body"]["section_role"] == "unknown"
    assert result["unit_profiles"]["body"]["priority"] == 2


@pytest.mark.parametrize("form", [None, "unknown"])
def test_unresolved_form_cannot_assert_a_numbered_business_role(form):
    result = _bind("Item 1", [_rule("Item 1. Business")], form=form)
    assert result["unit_profiles"]["body"]["section_role"] == "unknown"


def test_different_explicit_title_is_diagnostic_and_never_overridden_by_item_number():
    result = _bind("Item 1. Legal Proceedings", [_rule("Item 1. Business")])
    assert result["unit_profiles"]["body"]["section_role"] == "unknown"
    assert any(row["code"] == "SECTION_TITLE_CONFLICT" for row in result["diagnostics"])


def test_same_number_with_ambiguous_declared_rules_does_not_pick_a_role():
    result = _bind("Item 1", [_rule("Item 1. Business"),
                              _rule("Item 1. Legal Proceedings", role="administrative", priority=3)])
    assert result["unit_profiles"]["body"]["section_role"] == "unknown"
    assert any(row["code"] == "SECTION_NUMBER_AMBIGUOUS" for row in result["diagnostics"])


@pytest.mark.parametrize("part,role,priority", [("PART I", "financial_notes", 2),
                                               ("PART II", "administrative", 3)])
def test_quarterly_repeated_item_number_retains_its_actual_part_scope(part, role, priority):
    entries = [_rule("Item 1. Financial Statements", role="financial_notes", priority=2, part="PART I"),
               _rule("Item 1. Legal Proceedings", role="administrative", priority=3, part="PART II")]
    result = _bind("Item 1", entries, form="10-Q", part=part)
    assert result["unit_profiles"]["body"]["section_role"] == role
    assert result["unit_profiles"]["body"]["priority"] == priority


def test_native_quarterly_item_scope_switches_parts_without_title_or_prose_guessing():
    units, pipeline = _pipeline(["FORM 10-Q", "PART I", "Item 1", "1.1 Notes", "The accounting numbers are described here.",
                                 "PART II", "Item 1", "The legal matter is described here."], form="10-Q")
    assert _view(units, pipeline, 4)["section_role"] == "financial_notes"
    assert _view(units, pipeline, 7)["section_role"] == "administrative"
    assert _view(units, pipeline, 7)["priority"] == 3


def test_number_matching_does_not_drop_a_required_configured_child_path():
    units, pipeline = _pipeline(["FORM 10-Q", "PART I", "Item 1", "The accounting numbers are described here."], form="10-Q")
    # The installed 10-Q notes policy requires an actual Notes child; a bare
    # financial-statement number cannot silently supply that missing layer.
    assert _view(units, pipeline, 3)["section_role"] == "unknown"


def test_inferred_numbering_is_distinct_from_native_dom_depth():
    _, inferred = _pipeline(["FORM 10-Q", "PART I", "Item 1", "1.1 Notes", "An accounting description."], form="10-Q")
    assert inferred["observation"]["units"][3]["hints"].get("heading_level_source") == "numbering"
    units, native = _pipeline(["FORM 10-Q", "PART I", "Item 1", "1.1 Notes", "An accounting description."],
                              form="10-Q", native_metadata={3: {"tag_name": "h2", "heading_level": 2}})
    assert native["observation"]["units"][3]["hints"].get("heading_level_source") == "native"
    assert _view(units, native, 4)["section_role"] == "unknown", "actual h2 keeps the Notes a sibling of the Item"


def test_legacy_heading_wire_without_origin_keeps_existing_dom_level_interpretation():
    from company_wiki.document_understanding.structure import build_structure

    observation = {"schema_version": "du-input/1", "source_ref": {"source_id": "source-one", "source_sha256": "a" * 64},
        "metadata": {}, "coverage": {"native_scan": "complete"}, "units": [
            {"unit_id": "part", "ordinal": 0, "text": "PART I", "kind": "heading", "hints": {"heading_level": 1, "dom_path": "part"}},
            {"unit_id": "item", "ordinal": 1, "text": "Item 1", "kind": "heading", "hints": {"heading_level": 2, "dom_path": "item"}},
            {"unit_id": "notes", "ordinal": 2, "text": "1.1 Notes", "kind": "heading", "hints": {"heading_level": 2, "dom_path": "notes"}}]}
    result = build_structure(observation)
    part = next(s for s in result["sections"] if s["heading_unit_ids"] == ["part"])
    notes = next(s for s in result["sections"] if s["heading_unit_ids"] == ["notes"])
    assert notes["parent_id"] == part["section_id"]


def test_transient_pdf_layout_reaches_the_existing_shared_engine_without_changing_source(monkeypatch, tmp_path):
    from company_wiki.document_understanding import layout_bridge
    from company_wiki.document_understanding.observation_adapter import build_observation
    from company_wiki.document_normalization.layout_snapshots import project_layout_snapshot

    source = source_id_for_sha256("a" * 64)
    native = _make_unit(source_id=source, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0),
        raw_text="Product 8 units", unit_kind="pdf_text_block", source_role="company_filing", language="en",
        metadata={"bbox": [0, 0, 400, 400], "geometry_granularity": "block"})
    snapshot = {"schema_version": "du-layout-snapshot/1", "pages": [
        {"page": 1, "width": 600, "height": 800, "coordinate_frame": "text", "rotation": 0,
         "bindings": [{"unit_id": native.unit_id, "bbox": [10, 20, 160, 40],
                       "words": [{"text": "Product", "bbox": [10, 20, 60, 40], "native_index": 0, "char_start": 0, "char_end": 7}],
                       "font_runs": [{"char_start": 0, "char_end": 15, "font_size": 10, "font_weight": "normal"}]}]}]}
    patch = project_layout_snapshot(snapshot, [{"unit_id": native.unit_id, "page": 1, "text": native.raw_text}])["unit_metadata"][native.unit_id]
    native = replace(native, metadata={**native.metadata,
        "reading_layout": {"feature_version": "pdf-reading-layout/1", **patch,
                           "raw_text": "must not migrate", "path": str(tmp_path / "must-not-copy.pdf")}})
    before = deepcopy(dict(native.metadata))
    observation = build_observation((native,), source_id=source, source_sha256="a" * 64,
                                    mime_type="application/pdf", language="en")
    projected = observation["units"][0]
    assert projected["layout"]["bbox"] == patch["layout"]["bbox"]
    assert projected["hints"]["words"] == patch["upstream_hints"]["words"]
    assert projected["hints"]["font_runs"] == patch["upstream_hints"]["font_runs"]
    assert projected["hints"]["geometry_granularity"] == "word"
    assert "raw_text" not in projected["hints"] and "path" not in projected["hints"]
    assert native.metadata == before and native.metadata["bbox"] == [0, 0, 400, 400]
    observed = []
    original = layout_bridge.derive_layout_hints

    def same_engine(value, **options):
        observed.append(value)
        return original(value, **options)

    monkeypatch.setattr(layout_bridge, "derive_layout_hints", same_engine)
    layout_bridge.apply_layout_hints(observation)
    assert len(observed) == 1
    assert observed[0]["pages"][0]["units"][0]["upstream_hints"]["words"] == patch["upstream_hints"]["words"]


def test_outline_interpreter_version_is_an_actual_decision_dependency(monkeypatch):
    from company_wiki.document_understanding import decision_inventory, strategy_binding

    _, pipeline = _pipeline(["FORM 10-K", "PART I", "Item 1", "Our service charges depend on resources consumed."])
    frozen = decision_inventory.build_decision_trace(pipeline)
    assert frozen["versions"].get("strategy_binding") == strategy_binding.STRATEGY_BINDING_VERSION
    monkeypatch.setattr(strategy_binding, "STRATEGY_BINDING_VERSION", strategy_binding.STRATEGY_BINDING_VERSION + "/next")
    assert decision_inventory.current_decision_trace(frozen) != frozen


def test_outline_scope_does_not_cross_to_another_actual_parent_source():
    first = source_id_for_sha256("a" * 64)
    second = source_id_for_sha256("b" * 64)
    units, pipeline = _pipeline(["FORM 10-K", "PART I", "Item 1. Business",
                                 "Our service charges depend on resources consumed."],
                                sources=[first, first, first, second])
    assert _view(units, pipeline, 3)["section_role"] == "unknown"


def test_toc_label_and_numeric_page_are_not_promoted_to_body_business_evidence():
    from company_wiki.document_understanding.structure import build_structure

    observation = {"schema_version": "du-input/1", "source_ref": {"source_id": "source-one", "source_sha256": "a" * 64}, "metadata": {},
        "coverage": {"native_scan": "complete"}, "units": [
            {"unit_id": "number", "ordinal": 0, "text": "Item 1.", "kind": "toc_entry"},
            {"unit_id": "title", "ordinal": 1, "text": "Business", "kind": "toc_entry"},
            {"unit_id": "page", "ordinal": 2, "text": "3", "kind": "toc_entry"},
            {"unit_id": "body", "ordinal": 3, "text": "An unrelated source description.", "kind": "paragraph"}]}
    result = build_structure(observation)
    assert all(not ({"number", "title", "page"} & set(s["heading_unit_ids"])) for s in result["sections"])
    assert all("body" not in s["body_unit_ids"] or s["section_role"] == "unknown" for s in result["sections"])


def test_pdf_partial_cell_parent_range_reaches_the_existing_layout_engine(monkeypatch):
    from company_wiki.document_understanding import layout_bridge
    from company_wiki.document_understanding.observation_adapter import build_observation

    source = source_id_for_sha256("f" * 64)
    cell = {"bbox": [10, 10, 80, 30], "char_start": 0, "char_end": 2,
            "native_cell_char_start": 0, "native_cell_char_end": 8, "partial_cell": True,
            "page": 1, "coordinate_frame": "page", "native_index": 0}
    native = _make_unit(source_id=source, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0), raw_text="15",
        unit_kind="pdf_table_row", source_role="company_filing", language="en",
        metadata={"reading_layout": {"feature_version": "pdf-reading-layout/1",
            "layout": {"bbox": [10, 10, 80, 30], "page_width": 100, "page_height": 100},
            "upstream_hints": {"cells": [cell]}}})
    observation = build_observation((native,), source_id=source, source_sha256="f" * 64)
    assert observation["units"][0]["hints"]["cells"] == [cell]
    observed = []
    original = layout_bridge.derive_layout_hints

    def same_engine(value, **options):
        observed.append(value)
        return original(value, **options)

    monkeypatch.setattr(layout_bridge, "derive_layout_hints", same_engine)
    layout_bridge.apply_layout_hints(observation)
    assert len(observed) == 1
    assert observed[0]["pages"][0]["units"][0]["upstream_hints"]["cells"] == [cell]
