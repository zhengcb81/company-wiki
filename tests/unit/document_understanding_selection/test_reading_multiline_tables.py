"""Shared operating-table reading contracts; all synthetic cases are labelled.

The format frontend supplies actual table IDs and typed rows.  A leading
period/date row is context, not proof that the table has no business purpose.
The structure output must bind the original rows, without inventing fine cells.
"""

from __future__ import annotations

from copy import deepcopy
import json

import pytest

from company_wiki.document_understanding.structure import build_structure


def _unit(uid, text, *, kind="table_row", page=1, table="one", row=None):
    return {"unit_id": uid, "ordinal": 0, "locator": "original:" + uid,
            "page": page, "text": text, "kind": kind, "language": "und",
            "role": "company_filing", "layout": {},
            "hints": {"table_id": table, "row": row}}


def _observation(*units, source="synthetic-source-a"):
    return {"schema_version": "du-input/1",
            "source_ref": {"source_id": source, "source_sha256": "a" * 64},
            "metadata": {"language": "und", "title": "Synthetic operating table"},
            "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
            "units": [{**deepcopy(unit), "ordinal": index} for index, unit in enumerate(units)]}


def _tables(observation, *, limits=None):
    return [entry for entry in build_structure(observation, limits=limits)["semantic_units"]
            if entry["kind"] == "operating_table"]


def _outlet_table(*, page=1, table="one", prefix=""):
    return [
        _unit(prefix + "date-en", "As of December 31,", kind="table_header", page=page, table=table, row=0),
        _unit(prefix + "date-zh", "截至12月31日", page=page, table=table, row=1),
        _unit(prefix + "years-en", "2021 | 2022", page=page, table=table, row=2),
        _unit(prefix + "years-zh", "2021年 | 2022年", page=page, table=table, row=3),
        _unit(prefix + "labels", "Number of stores / 門店數量", page=page, table=table, row=4),
        _unit(prefix + "domestic", "Domestic network / 國內網點 | 310 | 420", page=page, table=table, row=5),
        _unit(prefix + "abroad", "International network / 海外網點 | 70 | 90", page=page, table=table, row=6),
        _unit(prefix + "note", "Note: temporary outlets are excluded; the planned sites are not open.",
              kind="footnote", page=page, table=table, row=7),
    ]


def test_period_first_bilingual_table_binds_business_labels_and_actual_body_rows():
    observation = _observation(*_outlet_table())
    tables = _tables(observation)
    assert len(tables) == 1
    table = tables[0]
    assert set(table["member_unit_ids"]) == {unit["unit_id"] for unit in observation["units"]}
    assert set(table["anchor_unit_ids"]) == {"domestic", "abroad"}
    assert set(table["required_context_unit_ids"]) == {
        "date-en", "date-zh", "years-en", "years-zh", "labels", "note"
    }


def test_numeric_typed_rows_need_no_repeated_operating_keyword():
    units = _outlet_table()
    units[5]["text"] = "420"
    units[6]["text"] = "90"
    tables = _tables(_observation(*units))
    assert len(tables) == 1
    assert set(tables[0]["anchor_unit_ids"]) == {"domestic", "abroad"}
    assert {"date-en", "years-en", "labels", "note"} <= set(tables[0]["required_context_unit_ids"])


@pytest.mark.parametrize("body", (
    "Paid users | 2021 | 2022",
    "Projects delivered per year | 70 | 90",
    "2021",
))
def test_body_quantities_are_not_reclassified_as_year_headers(body):
    observation = _observation(
        _unit("header", "Service orders | 2021 | 2022", kind="table_header", row=0),
        _unit("body", body, row=1),
    )
    tables = _tables(observation)
    assert len(tables) == 1
    assert tables[0]["anchor_unit_ids"] == ["body"]
    assert tables[0]["required_context_unit_ids"] == ["header"]


def test_unrelated_capacity_table_uses_same_multiline_engine_and_unit_caption():
    observation = _observation(
        _unit("period", "Period ended June 30", kind="table_header", row=0),
        _unit("years", "2021 | 2022", row=1),
        _unit("caption", "Unit: tonnes per year", kind="table_caption", row=2),
        _unit("purpose", "Installed capacity", row=3),
        _unit("series-one", "Series Q | 1,200 | 1,600", row=4),
        _unit("series-two", "Series R | 400 | 600", row=5),
        _unit("note", "Note: capacity is designed capacity and is not actual output.", kind="footnote", row=6),
    )
    tables = _tables(observation)
    assert len(tables) == 1
    assert set(tables[0]["anchor_unit_ids"]) == {"series-one", "series-two"}
    assert set(tables[0]["required_context_unit_ids"]) == {"period", "years", "caption", "purpose", "note"}


def test_plain_one_line_operating_header_anchors_body_and_keeps_all_qualifiers():
    observation = _observation(
        _unit("caption", "单位：台/年", kind="table_caption", row=0),
        _unit("header", "产品名称 | 2021年产能 | 2022年产能", kind="table_header", row=1),
        _unit("body", "系列Q | 1,200 | 1,600", row=2),
        _unit("note", "注：规划产能，尚未投产。", kind="footnote", row=3),
    )
    table = _tables(observation)[0]
    assert table["anchor_unit_ids"] == ["body"]
    assert set(table["required_context_unit_ids"]) == {"caption", "header", "note"}


@pytest.mark.parametrize("finance_label", (
    "Cash and cash equivalents | Total assets | Total liabilities",
    "货币资金 | 资产总计 | 负债合计",
    "Revenue | Net income | EPS",
    "Lease liabilities for stores",
    "門店租賃負債",
))
def test_financial_table_with_operating_words_in_note_is_not_promoted(finance_label):
    observation = _observation(
        _unit("date", "As of December 31,", kind="table_header", row=0),
        _unit("years", "2021 | 2022", row=1),
        _unit("labels", finance_label, row=2),
        _unit("money", "1,200 | 1,600", row=3),
        _unit("note", "Note: the number of stores increased; monetary values use USD million.",
              kind="footnote", row=4),
    )
    assert _tables(observation) == []


def test_two_explicit_tables_on_same_page_keep_their_own_periods_and_notes():
    first = _outlet_table(table="one", prefix="a-")
    second = [
        _unit("b-period", "2023 | 2024", kind="table_header", table="two", row=0),
        _unit("b-purpose", "Active customers", table="two", row=1),
        _unit("b-body", "Subscription channel | 12 | 18", table="two", row=2),
        _unit("b-note", "Note: free users are excluded.", kind="footnote", table="two", row=3),
    ]
    tables = _tables(_observation(*first, *second))
    assert len(tables) == 2
    memberships = [set(table["member_unit_ids"]) for table in tables]
    assert memberships[0] == {unit["unit_id"] for unit in first}
    assert memberships[1] == {unit["unit_id"] for unit in second}
    assert not memberships[0] & memberships[1]


def test_operating_purpose_does_not_leak_to_neighbor_financial_table():
    operating = _outlet_table(table="one")
    finance = [
        _unit("f-period", "2021 | 2022", kind="table_header", table="two", row=0),
        _unit("f-purpose", "Total assets | Net income", table="two", row=1),
        _unit("f-body", "1,200 | 1,600", table="two", row=2),
    ]
    tables = _tables(_observation(*operating, *finance))
    assert len(tables) == 1
    assert not set(tables[0]["member_unit_ids"]) & {unit["unit_id"] for unit in finance}


def test_reused_local_table_id_on_next_page_does_not_inherit_previous_purpose():
    first = _outlet_table(page=1, table="one")
    orphan_next_page = _unit("unrelated-next-page", "1,200 | 1,600", page=2, table="one", row=1)
    tables = _tables(_observation(*first, orphan_next_page))
    assert len(tables) == 1
    assert "unrelated-next-page" not in tables[0]["member_unit_ids"]


def test_headers_from_one_table_cannot_supply_purpose_to_a_period_only_table():
    source = _observation(
        _unit("first-purpose", "Number of stores", kind="table_header", table="one", row=0),
        _unit("first-body", "Channel Q | 300 | 420", table="one", row=1),
        _unit("other-period", "2021 | 2022", kind="table_header", table="two", row=0),
        _unit("other-body", "1,200 | 1,600", table="two", row=1),
    )
    tables = _tables(source)
    assert len(tables) == 1
    assert set(tables[0]["member_unit_ids"]) == {"first-purpose", "first-body"}


def test_separate_source_calls_share_no_table_buffers_or_original_ids():
    first = _observation(*_outlet_table(prefix="first-"), source="synthetic-source-a")
    second = _observation(*_outlet_table(prefix="second-"), source="synthetic-source-b")
    one = _tables(first)
    two = _tables(second)
    assert len(one) == len(two) == 1
    assert not set(one[0]["member_unit_ids"]) & set(two[0]["member_unit_ids"])
    assert _tables(first) == one


def test_multiline_table_projection_is_pure_and_does_not_create_text_or_cells():
    observation = _observation(*_outlet_table())
    before = deepcopy(observation)
    first = _tables(observation)
    second = _tables(deepcopy(observation))
    assert first, "The actual table scope must be processed before asserting purity"
    assert first == second
    assert observation == before
    allowed_ids = {unit["unit_id"] for unit in before["units"]}
    for table in first:
        assert set(table["member_unit_ids"]) <= allowed_ids
        assert "text" not in table and "cells" not in table
    json.dumps(first, ensure_ascii=False)
