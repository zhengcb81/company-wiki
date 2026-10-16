"""Card B-1: one preparation pass; multi table/page and same-id different parents.

Expectations are written from the construction card and the frozen contracts,
independently of the implementation: native table identities are scoped by
(parent, table_id, page) and never merged across sources, and one call prepares
every table from a single index of the input units.
"""

from __future__ import annotations

import json

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_normalization.pdf_table_observations import (
    build_pdf_table_observations,
)

from .builders import layout_hints, merge_layout_hints, observation, row_unit

PARENT_A = "urn:company-wiki:source:sha256:aaaa"
PARENT_B = "urn:company-wiki:source:sha256:bbbb"


def budget(n: int = 100_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


def _table_units(parent, table_id, page, rows, *, marker):
    units = []
    for row in rows:
        units.append(
            row_unit(
                f"{marker}-r{row}",
                [(0, f"{marker}行{row}"), (1, str(100 + row))],
                row=row,
                table_id=table_id,
                page=page,
                parent=parent,
                kind="table_header" if row == 0 else "table_row",
            )
        )
    return units


def _hints(units, *, header_row_units, data_rows, caption_units=()):
    return layout_hints(
        region_units=[u["unit_id"] for u in units],
        header_units=header_row_units,
        data_rows=data_rows,
        caption_units=caption_units,
    )


def test_multi_table_multi_page_and_same_id_across_parents_are_kept_apart():
    a_t0 = _table_units(PARENT_A, "p1:t0", 1, [0, 1], marker="a0")
    a_t1 = _table_units(PARENT_A, "p1:t1", 1, [0, 1], marker="a1")
    a_p2 = _table_units(PARENT_A, "p2:t0", 2, [0, 1], marker="a2")
    b_t0 = _table_units(PARENT_B, "p1:t0", 1, [0, 1], marker="b0")
    units = a_t0 + a_t1 + a_p2 + b_t0
    obs = observation(units, source_id=PARENT_A)

    def hints_for(rows):
        return _hints(rows, header_row_units=[rows[0]["unit_id"]], data_rows=[[rows[1]["unit_id"]]])

    merged = merge_layout_hints(*[hints_for(rows) for rows in (a_t0, a_t1, a_p2, b_t0)])

    result = build_pdf_table_observations(obs, merged, work_budget=budget())
    assert result["status"] == "partial"
    assert "ROW_LABEL_UNAVAILABLE" in {d["code"] for d in result["diagnostics"]}
    scopes = {
        (t["scope"]["parent_id"], t["scope"]["table_id"], t["scope"]["page"]): t
        for t in result["tables"]
    }
    assert set(scopes) == {
        (PARENT_A, "p1:t0", 1),
        (PARENT_A, "p1:t1", 1),
        (PARENT_A, "p2:t0", 2),
        (PARENT_B, "p1:t0", 1),
    }
    for key, table in scopes.items():
        marker = {
            (PARENT_A, "p1:t0", 1): "a0",
            (PARENT_A, "p1:t1", 1): "a1",
            (PARENT_A, "p2:t0", 2): "a2",
            (PARENT_B, "p1:t0", 1): "b0",
        }[key]
        texts = {
            table["units"][ref["unit_id"]]["text"][ref["char_start"]:ref["char_end"]]
            for cell in table["cells"]
            for ref in cell["text_refs"]
        }
        assert all(text.startswith(marker) or text.isdigit() for text in texts)
        assert table["scope"]["parent_id"] == key[0]


def test_one_call_prepares_every_table_from_a_single_index():
    t1 = _table_units(PARENT_A, "p1:t0", 1, [0, 1], marker="solo1")
    t2 = _table_units(PARENT_A, "p1:t1", 1, [0, 1], marker="solo2")

    def run(units):
        return build_pdf_table_observations(observation(units), None, work_budget=budget())

    first = run(t1)
    second = run(t2)
    combined = run(t1 + t2)
    assert [t["scope"] for t in combined["tables"]] == [
        t["scope"] for t in first["tables"] + second["tables"]
    ]
    # one shared index of the input units: the combined call pays the entry
    # charge once, and every per-element charge exactly once.
    assert combined["work_used"] == first["work_used"] + second["work_used"] - 1
    again = run(t1 + t2)
    assert json.dumps(again, sort_keys=True) == json.dumps(combined, sort_keys=True)
