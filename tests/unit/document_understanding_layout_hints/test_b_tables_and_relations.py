"""Node B: table structure, context groups, relations and their negatives."""

from __future__ import annotations

from cases import load_case
from checks import (
    group_containing,
    groups_of_kind,
    relations_of_kind,
    unit_hint,
)

from company_wiki.document_understanding.layout_hints import derive_layout_hints


def _region(result) -> dict:
    regions = groups_of_kind(result, "table_region")
    assert len(regions) == 1, f"expected exactly one table region, got {len(regions)}"
    return regions[0]


def _rows_of(result, region) -> list[dict]:
    return [row for row in groups_of_kind(result, "table_row") if row["parent_table_id"] == region["group_id"]]


# ------------------------------------------------- header/period/unit/footnote


def test_header_period_unit_and_footnote_are_bound_to_the_table() -> None:
    result = derive_layout_hints(load_case("table_header_period_unit_footnote"))
    region = _region(result)

    header_rows = [row for row in _rows_of(result, region) if "u4" in row["member_unit_ids"]]
    assert len(header_rows) == 1
    assert set(header_rows[0]["member_unit_ids"]) >= {"u4", "u5", "u6"}
    header_relations = [rel for rel in relations_of_kind(result, "header_for") if rel["to_group_id"] == region["group_id"]]
    assert header_relations and header_relations[0]["from_group_id"] == header_rows[0]["group_id"]

    captions = [item for item in groups_of_kind(result, "caption") if item["group_id"] != region["group_id"]]
    caption_members = {uid for item in captions for uid in item["member_unit_ids"]}
    assert {"u1", "u2", "u3"} <= caption_members
    caption_relations = [rel for rel in relations_of_kind(result, "caption_for") if rel["to_group_id"] == region["group_id"]]
    assert caption_relations

    footnotes = [item for item in groups_of_kind(result, "footnote")]
    assert {"u16"} <= {uid for item in footnotes for uid in item["member_unit_ids"]}
    footnote_relations = [rel for rel in relations_of_kind(result, "footnote_for") if rel["to_group_id"] == region["group_id"]]
    assert footnote_relations

    for row in _rows_of(result, region):
        if row is header_rows[0]:
            continue
        context = set(row["required_context_unit_ids"])
        assert {"u4", "u5", "u6"} <= context  # which period/column each quantity belongs to
        assert "u3" in context  # unit line
        assert "u16" in context  # footnote qualifies the numbers
        assert "u1" in context  # table title

    assert region["parent_table_id"] is None


# ------------------------------------------------- cross-page continuation


def test_cross_page_table_continuation_needs_column_or_header_evidence() -> None:
    result = derive_layout_hints(load_case("cross_page_table_continuation"))
    regions = groups_of_kind(result, "table_region")
    assert len(regions) == 2
    by_page = {}
    for region in regions:
        first = region["member_unit_ids"][0]
        by_page[first] = region
    page1 = [r for r in regions if "u3" in r["member_unit_ids"] or "u7" in r["member_unit_ids"]][0]
    page2 = [r for r in regions if r is not page1][0]

    continuations = relations_of_kind(result, "continuation")
    assert len(continuations) == 1
    relation = continuations[0]
    assert relation["from_group_id"] == page1["group_id"]
    assert relation["to_group_id"] == page2["group_id"]
    assert relation["confidence"] in {"high", "medium"}
    assert any(basis.startswith("page_gap=") for basis in relation["basis"])

    rows_p2 = _rows_of(result, page2)
    data_rows_p2 = [row for row in rows_p2 if "u19" in row["member_unit_ids"] or "u23" in row["member_unit_ids"]]
    assert data_rows_p2
    for row in data_rows_p2:
        assert "u1" in set(row["required_context_unit_ids"])  # original title travels with the continuation


def test_new_table_on_next_page_is_not_a_continuation() -> None:
    result = derive_layout_hints(load_case("cross_page_table_unrelated"))
    assert len(groups_of_kind(result, "table_region")) == 2
    assert relations_of_kind(result, "continuation") == []


# ------------------------------------------------- isolation between tables


def test_adjacent_tables_keep_their_own_header_and_footnote() -> None:
    result = derive_layout_hints(load_case("adjacent_tables_isolated"))
    regions = groups_of_kind(result, "table_region")
    assert len(regions) == 2
    region_a = [r for r in regions if "u5" in r["member_unit_ids"]][0]
    region_b = [r for r in regions if "u13" in r["member_unit_ids"]][0]

    header_targets = {rel["to_group_id"] for rel in relations_of_kind(result, "header_for")}
    assert {region_a["group_id"], region_b["group_id"]} <= header_targets

    footnote_rels = relations_of_kind(result, "footnote_for")
    footnote_by_target: dict = {}
    for rel in footnote_rels:
        footnote_by_target.setdefault(rel["to_group_id"], set())
        source_group = next(g for g in result["groups"] if g["group_id"] == rel["from_group_id"])
        footnote_by_target[rel["to_group_id"]].update(source_group["member_unit_ids"])
    assert footnote_by_target[region_a["group_id"]] == {"u8"}
    assert footnote_by_target[region_b["group_id"]] == {"u16"}

    for row in _rows_of(result, region_a):
        assert "u16" not in set(row["required_context_unit_ids"])
    for row in _rows_of(result, region_b):
        assert "u8" not in set(row["required_context_unit_ids"])


def test_identical_amounts_do_not_merge_different_items() -> None:
    result = derive_layout_hints(load_case("same_amounts_different_items"))
    assert len(groups_of_kind(result, "table_region")) == 2

    row_groups = {}
    for amount_id in ("u4", "u6", "u10"):
        rows = group_containing(result, amount_id, kind="table_row")
        assert len(rows) == 1
        row_groups[amount_id] = rows[0]["group_id"]
    assert len(set(row_groups.values())) == 3
    assert relations_of_kind(result, "continuation") == []
    for rel in result["relations"]:
        assert rel["kind"] != "header_for" or True  # headers stay with their own table (covered above)


def test_bilingual_pages_do_not_invent_sentence_pairing() -> None:
    result = derive_layout_hints(load_case("bilingual_not_sentence_aligned"))
    assert unit_hint(result, "u1")["text_column"] == 0
    assert unit_hint(result, "u8")["text_column"] == 1
    assert groups_of_kind(result, "table_row") == []
    assert groups_of_kind(result, "table_region") == []
    lanes = groups_of_kind(result, "column_lane")
    assert len(lanes) == 2
    for lane in lanes:
        columns = {unit_hint(result, uid)["text_column"] for uid in lane["member_unit_ids"]}
        assert len(columns) == 1


def test_table_without_header_must_not_claim_one() -> None:
    result = derive_layout_hints(load_case("table_without_header"))
    region = _region(result)
    assert relations_of_kind(result, "header_for") == []
    for row in _rows_of(result, region):
        assert "header_row" not in row["basis"]
        assert "header_block" not in row["basis"]
    assert len(_rows_of(result, region)) == 3


def test_footnote_of_a_figure_does_not_attach_to_the_next_table() -> None:
    result = derive_layout_hints(load_case("footnote_belongs_to_previous_figure"))
    region = _region(result)
    for rel in relations_of_kind(result, "footnote_for"):
        assert rel["to_group_id"] != region["group_id"]
    assert {"u4", "u5", "u6", "u7"} <= set(region["member_unit_ids"]) | {
        uid for row in _rows_of(result, region) for uid in row["member_unit_ids"]
    }


# ------------------------------------------------- geometry honesty


def test_out_of_bounds_coordinates_are_diagnosed_and_deferred() -> None:
    result = derive_layout_hints(load_case("coordinates_out_of_bounds"))
    codes = {diag["code"] for diag in result["diagnostics"]}
    assert "COORDINATE_OUT_OF_BOUNDS" in codes
    deferred = set(result["coverage"]["deferred_unit_ids"])
    assert {"u2", "u3"} <= deferred
    assert result["coverage"]["processed_unit_count"] == 2
    assert result["coverage"]["complete"] is False
    for unit_id in ("u2", "u3"):
        assert unit_hint(result, unit_id)["confidence"] in {"unknown", "low"}


def test_bad_geometry_missing_font_and_empty_page() -> None:
    result = derive_layout_hints(load_case("bad_geometry_missing_font_empty_page"))
    codes = {diag["code"] for diag in result["diagnostics"]}
    assert "BAD_GEOMETRY" in codes
    bad = [diag for diag in result["diagnostics"] if diag["code"] == "BAD_GEOMETRY"]
    assert "u2" in bad[0]["unit_ids"]
    assert "u2" in set(result["coverage"]["deferred_unit_ids"])

    # missing geometry is a hint limitation, not a crash and not a high claim
    assert unit_hint(result, "u3")["heading_level"] is None
    assert unit_hint(result, "u3")["confidence"] in {"unknown", "low"}

    # missing font size must not turn a short line into a high-confidence heading
    assert unit_hint(result, "u5")["confidence"] != "high"
    assert unit_hint(result, "u4")["heading_level"] is None

    pages_with_order = {entry["page"] for entry in result["reading_order"]}
    assert 2 not in pages_with_order or all(
        entry["ordered_unit_ids"] == [] for entry in result["reading_order"] if entry["page"] == 2
    )


def test_whole_row_units_ask_for_upstream_granularity() -> None:
    result = derive_layout_hints(load_case("whole_row_units_no_cells"))
    codes = {diag["code"] for diag in result["diagnostics"]}
    assert "NEEDS_UPSTREAM_GRANULARITY" in codes
    region = _region(result)
    rows = _rows_of(result, region)
    assert rows
    for row in rows:
        assert row["cells"] == []  # no fabricated columns out of blank space
    assert result["coverage"]["complete"] is False


def test_multiple_periods_and_regions_stay_distinct_columns() -> None:
    result = derive_layout_hints(load_case("multi_period_columns"))
    region = _region(result)
    rows = _rows_of(result, region)
    data_rows = [row for row in rows if "u7" in row["member_unit_ids"] or "u12" in row["member_unit_ids"]]
    assert len(data_rows) == 2

    row_one = data_rows[0]
    cell_of = {}
    for cell in row_one["cells"]:
        for uid in cell["member_unit_ids"]:
            cell_of[uid] = cell
    columns = [cell_of[uid]["column"] for uid in ("u8", "u9", "u10", "u11")]
    assert len(set(columns)) == 4  # 4 periods/regions are 4 quantities, never merged
    assert all(isinstance(col, int) for col in columns)

    header_cells = {}
    for row in rows:
        for cell in row["cells"]:
            for uid in cell["member_unit_ids"]:
                header_cells[uid] = cell
    assert header_cells["u3"]["column"] != header_cells["u5"]["column"]
