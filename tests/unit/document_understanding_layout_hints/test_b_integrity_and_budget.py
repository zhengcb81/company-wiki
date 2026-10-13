"""Node B: referential integrity, budget accounting and complexity trend."""

from __future__ import annotations

import json

from cases import load_case, scale_case
from checks import all_unit_ids, groups_of_kind

from company_wiki.document_understanding.layout_hints import derive_layout_hints

DEFAULT_LIMITS = {"max_units": 50000, "max_groups": 10000, "max_work_units": 2000000}


def _assert_integrity(observation: dict, result: dict) -> None:
    ids = all_unit_ids(observation)
    group_ids = {item["group_id"] for item in result["groups"]}
    assert len(group_ids) == len(result["groups"]), "group ids must be unique"

    for item in result["groups"]:
        assert set(item["member_unit_ids"]) <= ids
        assert len(item["member_unit_ids"]) == len(set(item["member_unit_ids"]))
        assert set(item["required_context_unit_ids"]) <= ids
        assert item["parent_table_id"] is None or item["parent_table_id"] in group_ids
        assert item["confidence"] in {"high", "medium", "low", "unknown"}
        assert isinstance(item["basis"], list)
        for cell in item["cells"]:
            assert set(cell["member_unit_ids"]) <= ids
            for key in ("row", "column", "row_span", "column_span"):
                assert cell[key] is None or isinstance(cell[key], int)

    for rel in result["relations"]:
        assert rel["from_group_id"] in group_ids
        assert rel["to_group_id"] in group_ids
        assert rel["from_group_id"] != rel["to_group_id"]
        assert rel["kind"] in {"header_for", "caption_for", "footnote_for", "continuation"}

    for entry in result["reading_order"]:
        assert set(entry["ordered_unit_ids"]) <= ids
        assert len(entry["ordered_unit_ids"]) == len(set(entry["ordered_unit_ids"]))

    coverage = result["coverage"]
    assert set(coverage["deferred_unit_ids"]) <= ids
    assert coverage["processed_unit_count"] + len(coverage["deferred_unit_ids"]) == len(ids)
    assert coverage["opaque_pages"] == observation["coverage"]["opaque_pages"]
    assert coverage["deferred_pages"] == observation["coverage"]["deferred_pages"]
    assert isinstance(coverage["complete"], bool)

    for diag in result["diagnostics"]:
        assert set(diag["unit_ids"]) <= ids
        assert isinstance(diag["code"], str) and diag["code"]
        assert isinstance(diag["detail"], str)


def test_referential_integrity_across_all_shapes() -> None:
    from cases import case_names

    for name in case_names():
        observation = load_case(name)
        result = derive_layout_hints(load_case(name))
        _assert_integrity(observation, result)


def test_structure_does_not_depend_on_company_names() -> None:
    base = load_case("table_header_period_unit_footnote")
    renamed = load_case("table_header_period_unit_footnote")
    replacements = {
        "表1 门店数量分布": "表1 甲公司乙项目",
        "中国内地": "甲公司",
        "海外": "乙公司",
        "注：数据来源于公司内部统计。": "注：数据来源于内部统计。",
    }
    for page in renamed["pages"]:
        for unit in page["units"]:
            unit["text"] = replacements.get(unit["text"], unit["text"])

    first = derive_layout_hints(base)
    second = derive_layout_hints(renamed)

    def shape(result):
        return {
            "groups": [(g["kind"], tuple(g["member_unit_ids"]), g["parent_table_id"]) for g in result["groups"]],
            "relations": [(r["kind"], r["from_group_id"], r["to_group_id"]) for r in result["relations"]],
            "unit_hints": [(h["unit_id"], h["heading_level"], h["text_column"]) for h in result["unit_hints"]],
        }

    assert shape(first) == shape(second)


def test_caller_limits_are_respected_and_never_raised() -> None:
    observation = scale_case(40)
    result = derive_layout_hints(observation, limits={"max_units": 10})
    assert result["coverage"]["processed_unit_count"] == 10
    assert len(result["coverage"]["deferred_unit_ids"]) == 30
    codes = {diag["code"] for diag in result["diagnostics"]}
    assert "UNIT_LIMIT_EXCEEDED" in codes
    assert result["coverage"]["complete"] is False

    # a caller cannot widen the built-in ceilings
    result_wide = derive_layout_hints(scale_case(40), limits={"max_units": 10 ** 9, "max_work_units": 10 ** 12})
    assert result_wide["coverage"]["processed_unit_count"] <= DEFAULT_LIMITS["max_units"]


def test_work_budget_stops_processing_and_reports_partial() -> None:
    observation = scale_case(400)
    result = derive_layout_hints(observation, limits={"max_work_units": 200})
    codes = {diag["code"] for diag in result["diagnostics"]}
    assert "WORK_BUDGET_EXCEEDED" in codes
    assert result["coverage"]["complete"] is False
    assert result["coverage"]["deferred_unit_ids"]
    _assert_integrity(observation, result)


def test_group_budget_is_reported_not_silently_dropped() -> None:
    observation = scale_case(200)
    result = derive_layout_hints(observation, limits={"max_groups": 3})
    codes = {diag["code"] for diag in result["diagnostics"]}
    assert "GROUP_LIMIT_EXCEEDED" in codes
    assert len(result["groups"]) <= 3


def test_work_units_grow_about_linearly() -> None:
    """Complexity guard: no all-pairs pass may hide in the geometry code.

    Wall-clock and RSS are recorded as observations elsewhere; CI only checks
    the deterministic work accounting.
    """
    sizes = [1000, 10000, 40000]
    work_per_unit = []
    for size in sizes:
        result = derive_layout_hints(scale_case(size))
        work = result["diagnostics"]
        counts = {diag["code"]: diag["detail"] for diag in work if diag["code"] == "WORK_UNITS"}
        total = int(counts["WORK_UNITS"]) if counts else None
        assert total is not None, "derive_layout_hints must report its accumulated work units"
        assert total <= DEFAULT_LIMITS["max_work_units"]
        work_per_unit.append(total / size)

    # linear-ish: doubling unit count may not double the per-unit cost
    assert work_per_unit[-1] <= 3.0 * work_per_unit[0], work_per_unit


def test_work_units_are_deterministic() -> None:
    first = derive_layout_hints(scale_case(1000))
    second = derive_layout_hints(scale_case(1000))
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert groups_of_kind(first, "table_region") == groups_of_kind(second, "table_region")
