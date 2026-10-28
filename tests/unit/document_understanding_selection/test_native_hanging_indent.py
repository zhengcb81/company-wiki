"""Measured bullet geometry must not make a native body wrap disappear."""

from copy import deepcopy

import pytest

from unit.document_understanding_selection.test_reading_native_continuity import (
    native,
    run,
)


def case(
    *,
    size=9,
    marker="• ",
    body="本期行业服务收入由去年同期100增加至120",
    tail="百万元，同比增长20%，由于客户需求增长。",
):
    text = marker + "\n" + body
    left = native(text, 0, box=[60, 100, 500, 100 + size * 1.15])
    right = native(
        tail, 1, box=[60 + 2.6 * size, 100 + 1.55 * size, 500, 100 + 2.7 * size]
    )
    split = len(marker) + 1
    spans = [
        {
            "char_start": 0,
            "char_end": len(marker),
            "bbox": [60, 100, 60 + size, 100 + size],
            "origin": [60, 100 + size],
            "direction": [1, 0],
            "line": 0,
        },
        {
            "char_start": split,
            "char_end": len(text),
            "bbox": [60 + 2.6 * size, 100, 500, 100 + 1.15 * size],
            "origin": [60 + 2.6 * size, 100 + size],
            "direction": [1, 0],
            "line": 1,
        },
    ]
    for span in spans:
        span.update(
            page=7,
            coordinate_frame="dict",
            source="pdf_dict_native_span",
            char_alignment="exact",
            partial_span=False,
        )
    left[0]["hints"]["spans"] = spans
    for row in (left, right):
        row[0]["layout"]["font_size"] = size
        row[0]["hints"]["font_runs"][0]["font_size"] = size
    return [left, right]


@pytest.mark.parametrize("size", [7, 9, 12, 16])
@pytest.mark.parametrize("marker", ["• ", "● ", "▪ ", "- "])
def test_observed_marker_is_not_the_body_left_margin(size, marker):
    rows = case(size=size, marker=marker)
    before = deepcopy(rows)
    windows = run(rows)["windows"]
    assert len(windows) == 1
    assert windows[0]["proof"][0]["basis"] == "native_hanging_indent"
    assert windows[0]["member_unit_ids"] == [r[0]["unit_id"] for r in rows]
    assert rows == before


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "baseline",
        "frame",
        "page",
        "direction",
        "partial",
        "alignment",
        "gap",
        "outside",
        "overlap",
        "new_bullet",
        "terminal",
        "column",
        "heading",
        "word_marker",
    ],
)
def test_unknown_or_new_boundary_is_not_repaired(fault):
    rows = case()
    left, right = rows[0][0], rows[1][0]
    spans = left["hints"]["spans"]
    if fault == "missing":
        left["hints"].pop("spans")
    elif fault == "baseline":
        spans[1]["origin"][1] += 9
    elif fault == "frame":
        spans[1]["coordinate_frame"] = "words"
    elif fault == "page":
        spans[1]["page"] = 8
    elif fault == "direction":
        spans[1]["direction"] = [0, 1]
    elif fault == "partial":
        spans[1]["partial_span"] = True
    elif fault == "alignment":
        spans[1]["char_alignment"] = "unknown"
    elif fault == "gap":
        spans[1]["char_start"] += 2
    elif fault == "outside":
        spans[1]["bbox"][2] = 700
    elif fault == "overlap":
        spans[1]["bbox"][0] = 61
    elif fault == "new_bullet":
        right["text"] = "• " + right["text"]
    elif fault == "terminal":
        left["text"] = left["text"][:-1] + "。"
    elif fault == "column":
        right["layout"]["column"] = 2
    elif fault == "heading":
        right["kind"] = "heading"
    elif fault == "word_marker":
        left["text"] = "X " + left["text"][2:]
    assert run(rows)["windows"] == []


def test_english_body_and_independent_next_bullet_remain_distinct():
    rows = case(
        body="Revenue from our service increased from 100 to 120",
        tail="million because enterprise demand improved.",
    )
    assert len(run(rows)["windows"]) == 1
    rows[1][0]["text"] = "- Our other service launched a new product."
    rows[1][0]["hints"]["font_runs"][0]["char_end"] = len(rows[1][0]["text"])
    assert not run(rows)["windows"]


def test_work_exhaustion_does_not_invent_geometry():
    result = run(case(), max_work_units=3)
    assert not result["windows"]
    assert not result["complete"]


def test_small_indent_new_item_is_a_statement_boundary_but_keeps_physical_adjacency():
    rows = case()
    rows[1][0]["layout"]["bbox"][0] = 60
    rows[1][0]["text"] = "- Our other service launched a new product."
    rows[1][0]["hints"]["font_runs"][0]["char_end"] = len(rows[1][0]["text"])
    rows[1][1]["block_char_end"] = len(rows[1][0]["text"])
    result = run(rows)
    assert not result["windows"]
    assert result["adjacency_edges"]
