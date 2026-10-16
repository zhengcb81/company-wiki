"""Source-owner controls: requested deep pages, not a rich prefix of the PDF."""

from __future__ import annotations

import hashlib
from importlib import import_module
import pytest

from company_wiki.source_catalog import narrative_evidence as pdf
from company_wiki.source_contract import source_id_for_sha256


def _bytes(pages=80, table_pages=(75, 76)):
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    for physical in range(1, pages + 1):
        page = doc.new_page(width=600, height=800)
        page.insert_text((70, 70), f"Ordinary source paragraph {physical}.")
        if physical in table_pages:
            page.insert_text((70, 110), "ROOT_TABLE_TARGET")
            for x in (70, 260, 430):
                page.draw_line((x, 180), (x, 240))
            for y in (180, 210, 240):
                page.draw_line((70, y), (430, y))
            for y, label, value in (
                (200, "Metric", "FY2025"),
                (230, "Production", "18"),
            ):
                page.insert_text((80, y), label)
                page.insert_text((270, y), value)
    data = doc.tobytes()
    doc.close()
    return data


def _parse(data, **kwargs):
    digest = hashlib.sha256(data).hexdigest()
    return pdf.parse_pdf_bytes(
        data,
        source_id=source_id_for_sha256(digest),
        source_sha256=digest,
        language="en",
        selector_version=kwargs.pop("selector_version", "0.9.0"),
        **kwargs,
    )


def _identity(parsed):
    return [
        (
            u.unit_id,
            u.raw_text,
            u.coordinates.locator(),
            u.parser_name,
            u.parser_version,
            u.unit_kind,
            u.source_role,
        )
        for u in parsed.units
    ]


def _fine(parsed, physical):
    return [
        cell
        for u in parsed.units
        if u.coordinates.page_number == physical
        for cell in u.metadata.get("reading_layout", {})
        .get("upstream_hints", {})
        .get("cells", ())
    ]


def test_explicit_deep_targets_have_fine_cells_without_capture_of_a_prefix():
    raw = _bytes()
    rich = _parse(raw, table_pages=(75, 76))
    legacy = _parse(raw, table_pages=(75, 76), selector_version="0.8.0")
    assert _identity(rich) == _identity(legacy)
    assert _fine(rich, 75) and _fine(rich, 76)
    assert not _fine(rich, 1)
    capture = rich.layout_coverage["capture"]
    assert capture["schema_version"] == "pdf-layout-capture/1"
    assert capture["strategy"] == "requested-pages/1"
    assert (
        capture["requested_pages"]
        == capture["captured_pages"]
        == capture["projected_pages"]
        == [75, 76]
    )
    assert capture["requested_page_count"] == 2 and capture["deferred_page_count"] == 0
    assert rich.layout_coverage["processed_page_count"] == 2
    assert rich.pages_read == 80


def test_auto_source_triage_captures_deep_candidate_and_real_neighbours(monkeypatch):
    registry = import_module("company_wiki.document_understanding.profiles.registry")
    monkeypatch.setattr(
        registry, "configured_table_signal", lambda text: "ROOT_TABLE_TARGET" in text
    )
    raw = _bytes(table_pages=(75,))
    parsed = _parse(raw)
    assert parsed.table_scan_pages == (74, 75, 76)
    assert _fine(parsed, 75)
    assert parsed.layout_coverage["capture"]["requested_pages"] == [74, 75, 76]
    assert parsed.layout_coverage["capture"]["captured_pages"] == [74, 75, 76]


@pytest.mark.parametrize(
    "limit,value",
    [
        ("max_pages", 0),
        ("max_units", 0),
        ("max_fine_elements", 0),
        ("max_work_units", 0),
    ],
)
def test_zero_geometry_limits_keep_original_units_and_explicit_deferred_targets(
    limit, value
):
    raw = _bytes(pages=3, table_pages=(3,))
    parsed = _parse(raw, table_pages=(3,), layout_limits={limit: value})
    legacy = _parse(raw, table_pages=(3,), selector_version="0.8.0")
    assert _identity(parsed) == _identity(legacy)
    assert not _fine(parsed, 3)
    capture = parsed.layout_coverage["capture"]
    assert capture["requested_pages"] == [3]
    assert capture["captured_pages"] == [] and capture["deferred_pages"] == [3]
    assert not capture["complete"]


def test_deep_target_count_cap_is_not_a_physical_page_number_cap():
    raw = _bytes(table_pages=(74, 75, 76))
    parsed = _parse(raw, table_pages=(74, 75, 76), layout_limits={"max_pages": 2})
    capture = parsed.layout_coverage["capture"]
    assert capture["requested_pages"] == [74, 75, 76]
    assert capture["captured_pages"] == capture["projected_pages"] == [74, 75]
    assert capture["deferred_pages"] == [76] and capture["deferred_page_count"] == 1
    assert _fine(parsed, 74) and _fine(parsed, 75) and not _fine(parsed, 76)


def test_failed_native_capture_does_not_erase_or_regenerate_originals(monkeypatch):
    module = import_module("company_wiki.source_catalog.narrative_pdf_layout")
    raw = _bytes(pages=3, table_pages=(3,))
    legacy = _parse(raw, table_pages=(3,), selector_version="0.8.0")

    def fail(*args, **kwargs):
        raise ValueError("controlled unavailable native capture")

    monkeypatch.setattr(module.PdfLayoutCollector, "_capture", fail)
    parsed = _parse(raw, table_pages=(3,))
    assert _identity(parsed) == _identity(legacy)
    assert not _fine(parsed, 3)
    assert not parsed.layout_coverage["capture"]["complete"]
    assert parsed.layout_coverage["capture"]["deferred_pages"] == [3]


def test_request_digest_is_order_independent_but_distinguishes_source_intent():
    raw = _bytes(pages=4, table_pages=(3, 4))
    first = _parse(raw, table_pages=(3, 4)).layout_coverage["capture"]
    reverse = _parse(raw, table_pages=(4, 3)).layout_coverage["capture"]
    smaller = _parse(raw, table_pages=(4,)).layout_coverage["capture"]
    assert len(first["request_sha256"]) == 64
    assert first["request_sha256"] == reverse["request_sha256"]
    assert first["request_sha256"] != smaller["request_sha256"]


def test_full_table_scan_requests_all_physical_pages_and_empty_table_request_retains_text_fine():
    raw = _bytes(pages=3, table_pages=(3,))
    full = _parse(raw, full_table_scan=True, table_pages=(3,))
    assert full.table_scan_pages == (1, 2, 3)
    assert full.layout_coverage["capture"]["requested_pages"] == [1, 2, 3]
    empty = _parse(raw, table_pages=())
    assert empty.table_scan_pages == ()
    assert empty.layout_coverage["capture"]["requested_pages"] == [1, 2, 3]
    assert any(
        u.metadata.get("reading_layout", {}).get("upstream_hints", {}).get("words")
        for u in empty.units
    )


def test_one_native_textpage_and_at_most_two_pending_page_materials(monkeypatch):
    fitz = pytest.importorskip("fitz")
    module = import_module("company_wiki.source_catalog.narrative_pdf_layout")
    original_textpage = fitz.Page.get_textpage
    original_snapshot = module.PdfLayoutCollector.read_snapshot
    seen = []
    pending = []

    def native(page, *args, **kwargs):
        if kwargs.get("flags") == fitz.TEXTFLAGS_DICT:
            seen.append(page.number + 1)
        return original_textpage(page, *args, **kwargs)

    def snapshot(collector, *args, **kwargs):
        result = original_snapshot(collector, *args, **kwargs)
        pending.append(len(collector.pending_pages))
        return result

    monkeypatch.setattr(fitz.Page, "get_textpage", native)
    monkeypatch.setattr(module.PdfLayoutCollector, "read_snapshot", snapshot)
    parsed = _parse(_bytes(), table_pages=(75, 76))
    assert len(seen) == 80 and set(seen) == set(range(1, 81))
    assert max(pending) <= 2
    assert parsed.layout_coverage["capture"]["projected_pages"] == [75, 76]


def test_same_deadline_is_not_restarted_when_a_deep_target_is_reached(monkeypatch):
    module = import_module("company_wiki.source_catalog.narrative_pdf_layout")
    original = module.PdfLayoutCollector.read_snapshot
    clock = [10.0]
    monkeypatch.setattr(module, "monotonic", lambda: clock[0])

    def delayed(collector, page, number):
        if number == 3:
            clock[0] = 25.0
        return original(collector, page, number)

    monkeypatch.setattr(module.PdfLayoutCollector, "read_snapshot", delayed)
    parsed = _parse(_bytes(pages=3, table_pages=(3,)), table_pages=(3,))
    capture = parsed.layout_coverage["capture"]
    assert not _fine(parsed, 3) and capture["deferred_pages"] == [3]
    assert not capture["complete"]


def test_actual_capture_survives_production_summary_and_causal_inventory():
    from copy import deepcopy
    from company_wiki.source_catalog.narrative_reading import _native_layout_summary, _understand
    from company_wiki.document_understanding import decision_inventory
    from company_wiki.document_understanding.layout_hints.contract import WorkBudget

    parsed = _parse(_bytes(pages=3, table_pages=(3,)), table_pages=(3,))
    summary = _native_layout_summary(parsed)
    assert summary['capture'] == parsed.layout_coverage['capture']
    pipeline = _understand(parsed, title='Operating capacity update', kind='unknown',
                           mime_type='application/pdf', work_budget=WorkBudget(2_000_000))
    before = decision_inventory.build_decision_trace(pipeline)
    assert any(c['component_id'].startswith('pdf-capture-used|') for c in before['components'])
    assert decision_inventory.current_decision_trace(before) == before
    other = deepcopy(pipeline['native_layout_frontend'])
    other['capture']['request_sha256'] = 'f' * 64
    assert decision_inventory.build_decision_trace({**pipeline, 'native_layout_frontend': other}) != before
