"""Ordinary native prose must not require expensive table capture to stay whole."""
from hashlib import sha256
from types import SimpleNamespace

import pymupdf as fitz
import pytest

from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_contract import source_id_for_sha256
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
from company_wiki.document_understanding.observation_adapter import build_observation
from company_wiki.document_understanding.narrative_continuity import build_native_continuity


def pdf(lines, *, rotation=0):
    with fitz.open() as document:
        page = document.new_page(width=600, height=800)
        page.insert_text((60, 100), "\n".join(lines), fontsize=12)
        page.set_rotation(rotation)
        return document.tobytes()


def parse(raw, **kwargs):
    digest = sha256(raw).hexdigest()
    return parse_pdf_bytes(raw, source_id=source_id_for_sha256(digest),
                           source_sha256=digest, language="en", **kwargs)


def continuity(parsed):
    observation = build_observation(parsed.units, source_id=parsed.source_id,
                                    source_sha256=parsed.source_sha256)
    provenance = {unit.unit_id: {"source_id": unit.source_id,
        "paragraph_index": unit.coordinates.paragraph_index,
        **{key: unit.metadata.get(key) for key in
           ("pdf_block", "block_sha256", "block_char_start", "block_char_end")}}
        for unit in parsed.units}
    return build_native_continuity(observation["units"], provenance=provenance), observation


def test_default_prose_keeps_subject_action_and_number_without_table_capture(monkeypatch):
    calls = []
    textpages = []
    original_textpage = fitz.Page.get_textpage
    def counted_textpage(page, *args, **kwargs):
        textpages.append(page.number)
        return original_textpage(page, *args, **kwargs)
    def forbidden_finder(*args, **kwargs):
        calls.append("finder")
        raise AssertionError("prose does not need table discovery")
    monkeypatch.setattr(fitz.Page, "find_tables", forbidden_finder)
    monkeypatch.setattr(fitz.Page, "get_textpage", counted_textpage)
    raw = pdf(["Our new reactor received twelve repeat orders from customers",
               "and completed production verification; rollout is planned for next year."])
    parsed = parse(raw, selector_version="0.9.0", work_budget=new_document_work_budget())
    result, observation = continuity(parsed)
    assert not calls
    assert textpages == [0]
    assert len(result["windows"]) == 1
    assert result["windows"][0]["member_unit_ids"] == [unit.unit_id for unit in parsed.units]
    for unit in observation["units"]:
        assert unit["layout"]["coordinate_frame"] == "dict"
        assert unit["layout"]["rotation"] == 0
        assert unit["hints"]["font_runs"]
        assert unit["layout"]["granularity"] == "block"
        assert not unit["hints"].get("cells") and not unit["hints"].get("words")


def test_native_prose_adds_no_canonical_or_legacy_changes():
    raw = pdf(["The reactor entered customer production verification",
               "and received twelve orders; mass production is not yet approved."])
    legacy = parse(raw, selector_version="0.8.0", table_pages=[])
    current = parse(raw, selector_version="0.9.0")
    def identity(unit):
        return (unit.unit_id, unit.raw_text, unit.coordinates.locator(),
                unit.parser_name, unit.parser_version)
    assert list(map(identity, current.units)) == list(map(identity, legacy.units))
    assert not any("reading_layout" in unit.metadata for unit in legacy.units)
    assert all("reading_layout" in unit.metadata for unit in current.units)


@pytest.mark.parametrize('size',[9,12])
@pytest.mark.parametrize('rotation',[0,90])
def test_native_bullet_measurements_survive_default_parse_without_a_second_read(size,rotation,monkeypatch):
    with fitz.open() as document:
        page=document.new_page(width=600,height=800)
        page.insert_text((60,100),'- ',fontsize=size)
        page.insert_text((60+2.6*size,100),'Our service revenue increased from one hundred to',fontsize=size)
        page.insert_text((60+2.6*size,100+1.55*size),'one hundred twenty million because demand improved.',fontsize=size)
        page.set_rotation(rotation)
        raw=document.tobytes()
    calls=[]
    original=fitz.Page.get_textpage
    def counted(page,*args,**kwargs):
        calls.append(page.number)
        return original(page,*args,**kwargs)
    monkeypatch.setattr(fitz.Page,'get_textpage',counted)
    current=parse(raw,selector_version='0.9.0',table_pages=[])
    result,observation=continuity(current)
    assert calls==[0]
    proof=[edge for window in result['windows'] for edge in window['proof']
           if edge['basis']=='native_hanging_indent']
    assert len(proof)==1
    assert proof[0]['body_proof']['baseline']==100
    assert observation['units'][0]['layout']['bbox'][0]==60
    assert observation['units'][0]['hints']['spans'][0]['origin']==(60.0,100.0)


def test_rotated_prose_records_actual_unrotated_dict_frame():
    parsed = parse(pdf(["The reactor received twelve customer orders",
                        "but commercial rollout remains conditional."], rotation=90),
                   selector_version="0.9.0")
    _, observation = continuity(parsed)
    for unit in observation["units"]:
        layout = unit["layout"]
        assert layout["coordinate_frame"] == "dict"
        assert layout["rotation"] == 90
        assert (layout["page_width"], layout["page_height"]) == (600, 800)
        assert 0 <= layout["bbox"][0] < layout["bbox"][2] <= 600


@pytest.mark.parametrize("boundary", ["paragraph", "page", "heading", "table"])
def test_real_source_boundaries_do_not_join_unrelated_material(boundary):
    with fitz.open() as document:
        page = document.new_page(width=600, height=800)
        page.insert_text((60, 100), "The first product entered customer verification", fontsize=12)
        if boundary == "page":
            page = document.new_page(width=600, height=800)
            y = 100
        elif boundary == "heading":
            page.insert_text((60, 130), "Item 2. New business", fontsize=12)
            y = 160
        elif boundary == "table":
            page.insert_text((60, 130), "Product", fontsize=12)
            page.insert_text((300, 130), "Capacity", fontsize=12)
            page.insert_text((60, 150), "Unrelated device", fontsize=12)
            page.insert_text((300, 150), "twelve units", fontsize=12)
            y = 210
        else:
            y = 220
        page.insert_text((60, y), "Another product is still experimental.", fontsize=12)
        raw = document.tobytes()
    parsed = parse(raw, selector_version="0.9.0")
    result, _ = continuity(parsed)
    by_id = {u.unit_id: u for u in parsed.units}
    for window in result["windows"]:
        texts = [by_id[uid].raw_text for uid in window["member_unit_ids"]]
        assert not (any("first product" in text for text in texts)
                    and any("Another product" in text for text in texts))
        assert len({by_id[uid].coordinates.page_number for uid in window["member_unit_ids"]}) == 1


def test_prose_producer_is_a_current_pdf_only_cache_dependency(monkeypatch):
    from company_wiki.document_understanding import decision_inventory as inventory
    from company_wiki.source_catalog import narrative_evidence as source

    before = inventory._versions(pdf_frontend=True, mime_type="application/pdf")
    other = inventory._versions(pdf_frontend=False, mime_type="text/html")
    assert before["pdf_native_prose"] == source.PDF_PROSE_LAYOUT_FEATURE_VERSION
    monkeypatch.setattr(source, "PDF_PROSE_LAYOUT_FEATURE_VERSION", "pdf-native-prose-layout/test")
    assert inventory._versions(pdf_frontend=True, mime_type="application/pdf") != before
    assert inventory._versions(pdf_frontend=False, mime_type="text/html") == other


def normalized_style_fragments():
    """A combining accent has a different measured native style than its base."""
    from company_wiki.source_catalog import narrative_evidence as source
    from company_wiki.source_catalog.narrative_native_ranges import native_range_limits

    spans = [{"text": "e", "size": 12, "flags": 0},
             {"text": "\u0301", "size": 20, "flags": 16},
             {"text": "x; stable sentence.", "size": 12, "flags": 0}]
    snapshot = {"width": 600, "height": 800, "blocks": [{"type": 0,
        "bbox": [60, 100, 350, 120], "lines": [{"spans": spans}]}]}
    page = SimpleNamespace(rotation=0, rect=SimpleNamespace(width=600, height=800),
                           get_text=lambda *args, **kwargs: snapshot)
    digest = "a" * 64
    state = source._PdfParseState(source_id_for_sha256(digest), digest,
                                  source.NARRATIVE_PARSER_VERSION, "en")
    state.native_view_limits = native_range_limits()
    state.prose_work_budget = new_document_work_budget()
    geometry = {}
    blocks = source._pdf_text_blocks(page, geometry_out=geometry)
    state.page_geometry[1] = geometry
    source._record_pdf_native_view(state, 1, blocks)
    source._emit_pdf_text_units(state, 1, blocks)
    return state.units, source._project_native_prose(state, 1, state.units)


def test_nfc_combining_across_native_styles_does_not_invent_exact_regular_font():
    original, projected = normalized_style_fragments()
    assert original[0].raw_text == "\u00e9x;"
    assert projected[0].unit_id == original[0].unit_id
    assert projected[0].coordinates == original[0].coordinates
    layout = projected[0].metadata["reading_layout"]
    assert layout["layout"]["bbox"] == [60, 100, 350, 120]
    assert layout["upstream_hints"]["font_runs"] == []


def test_nfc_elsewhere_in_block_does_not_drop_unchanged_fragment_font():
    original, projected = normalized_style_fragments()
    assert original[1].raw_text == "stable sentence."
    fonts = projected[1].metadata["reading_layout"]["upstream_hints"]["font_runs"]
    assert fonts and all(run["font_size"] == 12 and run["font_weight"] == "regular"
                         and run["char_alignment"] == "exact" for run in fonts)
