"""Node A: frozen du2-layout-input/1 -> du2-layout-hints/1 contract and RED shapes.

Every assertion runs against the frozen fixtures in
``tests/fixtures/document_understanding_layout_hints/inputs``.  Nothing here
reads an owner original, a parser, a config, the network or the clock.
"""

from __future__ import annotations

import copy
import json

import pytest

from cases import load_case
from checks import (
    HINTS_SCHEMA,
    all_unit_ids,
    find_keys,
    group_containing,
    groups_of_kind,
    unit_hint,
    wire_keys,
)

from company_wiki.document_understanding.layout_hints import derive_layout_hints

WIRE_KEYS = {
    "schema_version",
    "source_ref",
    "unit_hints",
    "groups",
    "relations",
    "reading_order",
    "coverage",
    "diagnostics",
}


# ---------------------------------------------------------------- wire


def test_output_is_du_layout_hints_wire() -> None:
    observation = load_case("heading_unnumbered_vs_sentence")
    result = derive_layout_hints(observation)
    assert result["schema_version"] == HINTS_SCHEMA
    assert wire_keys(result) == WIRE_KEYS
    assert result["source_ref"] == observation["source_ref"]
    ids = all_unit_ids(observation)
    assert {hint["unit_id"] for hint in result["unit_hints"]} == ids
    for hint in result["unit_hints"]:
        assert set(hint.keys()) == {"unit_id", "heading_level", "text_column", "confidence", "basis"}
        assert hint["heading_level"] is None or isinstance(hint["heading_level"], int)
        assert hint["text_column"] is None or isinstance(hint["text_column"], int)
        assert hint["confidence"] in {"high", "medium", "low", "unknown"}


def test_output_never_allocates_source_locators() -> None:
    observation = load_case("table_header_period_unit_footnote")
    result = derive_layout_hints(observation)
    # no locator key anywhere in the hints wire, and no locator value leaks out
    assert find_keys(result, "locator") == []
    locator_values = {unit["locator"] for page in observation["pages"] for unit in page["units"]}
    encoded = json.dumps(result, ensure_ascii=False)
    for locator in locator_values:
        assert locator not in encoded


def test_input_mapping_is_not_modified() -> None:
    observation = load_case("cross_page_table_continuation")
    frozen = copy.deepcopy(observation)
    derive_layout_hints(observation)
    assert observation == frozen


def test_same_input_same_output() -> None:
    observation = load_case("bilingual_two_column")
    first = derive_layout_hints(load_case("bilingual_two_column"))
    second = derive_layout_hints(load_case("bilingual_two_column"))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert observation == load_case("bilingual_two_column")


def test_schema_version_is_enforced() -> None:
    observation = load_case("year_not_heading")
    observation["schema_version"] = "du2-layout-input/2"
    with pytest.raises(ValueError):
        derive_layout_hints(observation)


def test_duplicate_unit_id_is_rejected() -> None:
    observation = load_case("year_not_heading")
    observation["pages"][0]["units"][1]["unit_id"] = "u1"
    with pytest.raises(ValueError):
        derive_layout_hints(observation)


# ------------------------------------------------- positive/negative shapes


def test_unnumbered_heading_is_not_a_plain_short_sentence() -> None:
    result = derive_layout_hints(load_case("heading_unnumbered_vs_sentence"))
    styled = unit_hint(result, "u1")
    assert styled["heading_level"] is not None
    assert styled["confidence"] in {"high", "medium"}

    unstyled = unit_hint(result, "u4")  # unnumbered, not bold, but larger + isolated
    assert unstyled["heading_level"] is not None

    for sentence_id in ("u2", "u3", "u5"):  # ordinary short sentences
        hint = unit_hint(result, sentence_id)
        assert hint["heading_level"] is None
        assert hint["confidence"] != "high"
        assert group_containing(result, sentence_id, kind="heading") == []


def test_year_lines_are_never_headings() -> None:
    result = derive_layout_hints(load_case("year_not_heading"))
    assert unit_hint(result, "u1")["heading_level"] is not None
    for year_id in ("u2", "u3", "u5"):
        hint = unit_hint(result, year_id)
        assert hint["heading_level"] is None
        assert hint["confidence"] != "high"
        assert group_containing(result, year_id, kind="heading") == []


def test_cross_column_header_does_not_split_columns() -> None:
    result = derive_layout_hints(load_case("cross_column_header"))
    assert unit_hint(result, "u3")["text_column"] == 0
    assert unit_hint(result, "u5")["text_column"] == 0
    assert unit_hint(result, "u7")["text_column"] == 0
    assert unit_hint(result, "u4")["text_column"] == 1
    assert unit_hint(result, "u6")["text_column"] == 1
    assert unit_hint(result, "u8")["text_column"] == 1

    for furniture in ("u1", "u9"):
        assert unit_hint(result, furniture)["text_column"] is None

    lanes = groups_of_kind(result, "column_lane")
    assert len(lanes) == 4  # two lanes on each page (lane groups are per page)
    lane_members = {frozenset(lane["member_unit_ids"]) for lane in lanes}
    assert lane_members == {
        frozenset({"u3", "u5", "u7"}),
        frozenset({"u4", "u6", "u8"}),
        frozenset({"u11"}),
        frozenset({"u12"}),
    }

    assert unit_hint(result, "u11")["text_column"] == 0
    assert unit_hint(result, "u12")["text_column"] == 1
    assert unit_hint(result, "u10")["text_column"] is None
    assert unit_hint(result, "u13")["text_column"] is None


def test_bilingual_columns_and_cross_column_table() -> None:
    result = derive_layout_hints(load_case("bilingual_two_column"))
    for left in ("u1", "u3", "u5"):
        assert unit_hint(result, left)["text_column"] == 0
    for right in ("u2", "u4", "u6"):
        assert unit_hint(result, right)["text_column"] == 1
    for table_unit in ("u7", "u8", "u11", "u13", "u16"):
        assert unit_hint(result, table_unit)["text_column"] is None

    body_units = {"u1", "u2", "u3", "u4", "u5", "u6"}
    for kind in ("table_row", "table_region"):
        for item in groups_of_kind(result, kind):
            assert not body_units & set(item["member_unit_ids"])

    regions = groups_of_kind(result, "table_region")
    assert len(regions) == 1
    rows = [row for row in groups_of_kind(result, "table_row") if row["parent_table_id"] == regions[0]["group_id"]]
    assert len(rows) >= 3  # header block + two data rows


def test_isolated_numeric_row_stays_in_the_table() -> None:
    result = derive_layout_hints(load_case("table_isolated_numeric_row"))
    regions = groups_of_kind(result, "table_region")
    assert len(regions) == 1
    rows = [row for row in groups_of_kind(result, "table_row") if row["parent_table_id"] == regions[0]["group_id"]]
    numeric_row = [row for row in rows if set(row["member_unit_ids"]) == {"u8", "u9"}]
    assert len(numeric_row) == 1
    cells = numeric_row[0]["cells"]
    assert cells
    columns = {cell["column"] for cell in cells}
    assert columns >= {1, 2}  # not collapsed into a single column, not dropped
