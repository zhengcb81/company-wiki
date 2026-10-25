"""Page furniture needs source, physical-page and stable edge observations."""
from __future__ import annotations

import pytest

from company_wiki.document_understanding.structure.contract import ObservationUnit
from company_wiki.document_understanding.structure.layout import order_units


def _unit(page, text, *, source="source-a", top=False, body=False, table=False, geometry=True):
    y = 300 if body else 10 if top else 780
    return ObservationUnit({"unit_id": f"{source}:{page}:{text}", "page": page,
        "text": text, "kind": "paragraph", "layout": {
            "bbox": [280, y, 340, y + 12], "page_width": 600, "page_height": 800,
        } if geometry else {}, "hints": {"source_id": source,
            **({"table_id": "table-a", "row": 1, "column": 1} if table else {})}}, page)


@pytest.mark.parametrize("template", ["{p} / 249", "Page {p} of 249",
    "第{p}页 / 共249页", "{p}", "— {p} —"])
@pytest.mark.parametrize("top", [False, True])
def test_varying_page_counter_is_furniture_only_with_same_source_edge_sequence(template, top):
    units = [_unit(p, template.format(p=p), top=top) for p in (13, 14)]
    before = [(u.unit_id, u.text, u.page, u.bbox) for u in units]
    ordering = order_units(units)
    assert ordering.running_header_ids == {u.unit_id for u in units}
    assert ordering.page_numbers == {13, 14}
    assert [(u.unit_id, u.text, u.page, u.bbox) for u in units] == before


@pytest.mark.parametrize("mode", ["body", "wrong_page", "conflicting_total",
    "single_page", "different_source", "different_edge", "missing_geometry", "table"])
def test_ratio_or_unproven_counter_is_never_promoted_to_page_furniture(mode):
    units = [_unit(13, "13 / 249", body=mode == "body", geometry=mode != "missing_geometry",
                   table=mode == "table"),
             _unit(14, "24 / 249" if mode == "wrong_page" else
                   "14 / 250" if mode == "conflicting_total" else "14 / 249",
                   source="source-b" if mode == "different_source" else "source-a",
                   top=mode == "different_edge", body=mode == "body",
                   geometry=mode != "missing_geometry", table=mode == "table")]
    if mode == "single_page":
        units = units[:1]
    assert not order_units(units).running_header_ids


def test_total_conflict_does_not_certify_a_majority_template():
    units = [_unit(13, "13 / 249"), _unit(14, "14 / 249"), _unit(15, "15 / 250")]
    assert not order_units(units).running_header_ids


@pytest.mark.parametrize("mode", ["duplicate_candidate", "duplicate_across_edges",
    "duplicate_across_formats", "horizontal_drift", "vertical_drift"])
def test_page_edge_band_alone_does_not_prove_a_stable_page_counter(mode):
    units = [_unit(13, "13 / 249"), _unit(14, "14 / 249")]
    if mode in {"duplicate_candidate", "duplicate_across_edges", "duplicate_across_formats"}:
        for page in (13, 14):
            extra = _unit(page, f"Page {page} of 249" if mode == "duplicate_across_formats" else f"{page} / 249")
            extra.unit_id += ":body-ratio"
            extra.bbox = (20, 750, 60, 762) if mode == "duplicate_candidate" else (20, 10, 60, 22)
            units.append(extra)
    elif mode == "horizontal_drift":
        units[1].bbox = (20, 780, 60, 792)
    else:
        units[1].bbox = (280, 710, 340, 722)
    assert not order_units(units).running_header_ids


def test_counter_position_is_local_to_observed_page_sequence_not_the_whole_document():
    units = [_unit(page, f"{page} / 249") for page in (13, 14, 101, 102)]
    for unit in units[2:]:
        unit.bbox = (20, 780, 60, 792)
    assert order_units(units).running_header_ids == {u.unit_id for u in units}


def test_nonadjacent_position_matches_do_not_invent_a_counter_sequence():
    units = [_unit(page, f"{page} / 249") for page in (13, 15)]
    assert not order_units(units).running_header_ids
