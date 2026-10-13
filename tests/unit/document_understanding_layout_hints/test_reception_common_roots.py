"""Lock reception failure roots without company or fixed production-page cases."""

from __future__ import annotations
import copy
from cases import load_case, scale_case
from company_wiki.document_understanding.layout_hints import derive_layout_hints
from company_wiki.document_understanding.layout_hints.contract import WorkBudget, Unit


def test_unread_upstream_pages_preclude_complete_coverage():
    observation = load_case("table_header_period_unit_footnote")
    observation["coverage"] = {"opaque_pages": [3], "deferred_pages": [4]}
    result = derive_layout_hints(observation)
    assert result["coverage"]["complete"] is False
    assert result["coverage"]["opaque_pages"] == [3]
    assert result["coverage"]["deferred_pages"] == [4]


def test_late_budget_exhaustion_has_named_deferred_work():
    observation = scale_case(40)
    result = derive_layout_hints(observation, limits={"max_work_units": 230})
    assert any(
        d["code"] == "WORK_BUDGET_EXCEEDED" and d["unit_ids"]
        for d in result["diagnostics"]
    )
    assert result["coverage"]["deferred_unit_ids"]
    assert result["coverage"]["complete"] is False
    assert not any(g["confidence"] == "high" for g in result["groups"])


def test_work_failure_cannot_be_ignored_by_any_stage(monkeypatch):
    events = []
    original = WorkBudget.charge

    def counted(self, n=1):
        events.append((n, self.exhausted))
        return original(self, n)

    monkeypatch.setattr(WorkBudget, "charge", counted)
    result = derive_layout_hints(scale_case(40), limits={"max_work_units": 120})
    assert not any(exhausted_before for _, exhausted_before in events)
    work = int(
        next(d["detail"] for d in result["diagnostics"] if d["code"] == "WORK_UNITS")
    )
    assert work <= 120
    assert result["coverage"]["deferred_unit_ids"]


def test_single_page_neighbours_do_not_scan_all_unit_pairs(monkeypatch):
    n = 400
    observation = {
        "schema_version": "du2-layout-input/1",
        "source_ref": {},
        "coverage": {"opaque_pages": [], "deferred_pages": []},
        "pages": [
            {
                "page": 1,
                "width": 595,
                "height": 10000,
                "units": [
                    {
                        "unit_id": f"u{i}",
                        "ordinal": i,
                        "locator": None,
                        "text": "业务经营进展",
                        "bbox": [60, 200 + i * 20, 300, 210 + i * 20],
                        "font_size": 10,
                        "font_weight": "regular",
                        "kind": "paragraph",
                        "upstream_hints": {},
                    }
                    for i in range(n)
                ],
            }
        ],
    }
    inspected = []
    old = Unit.__getattribute__

    def counted(unit, name):
        if name == "bbox":
            inspected.append(1)
        return old(unit, name)

    monkeypatch.setattr(Unit, "__getattribute__", counted)
    result = derive_layout_hints(observation)
    assert len(inspected) < 80 * n
    assert result["coverage"]["complete"] is True


def test_original_context_reaches_the_third_continuation_page():
    observation = load_case("cross_page_table_continuation")
    observation["pages"][0]["units"].append(
        {
            "unit_id": "source-note",
            "ordinal": 50,
            "locator": None,
            "text": "注：部分项目尚未投产。",
            "bbox": [80, 720, 280, 733],
            "font_size": 9,
            "font_weight": "regular",
            "kind": "footnote",
            "upstream_hints": {},
        }
    )
    p2 = observation["pages"][1]
    p3 = copy.deepcopy(p2)
    p3["page"] = 3
    p2["units"] = [u for u in p2["units"] if u["unit_id"] != "u27"]
    row = [u for u in p2["units"] if u["unit_id"] in {"u23", "u24", "u25", "u26"}]
    ordinal = 100
    for y in range(155, 770, 20):
        for original in row:
            u = copy.deepcopy(original)
            u["unit_id"] = f"fill-{ordinal}"
            u["ordinal"] = ordinal
            ordinal += 1
            u["bbox"][1] = y
            u["bbox"][3] = y + 13
            p2["units"].append(u)
    for u in p3["units"]:
        u["unit_id"] = "p3-" + u["unit_id"]
        u["ordinal"] = ordinal
        ordinal += 1
    observation["pages"].append(p3)
    result = derive_layout_hints(observation)
    continuations = [r for r in result["relations"] if r["kind"] == "continuation"]
    assert len(continuations) == 2
    regions = [
        g
        for g in result["groups"]
        if g["kind"] == "table_region"
        and any(u.startswith("p3-") for u in g["member_unit_ids"])
    ]
    assert len(regions) == 1
    assert {"u1", "u2", "u3", "u4", "u5", "u6", "source-note"} <= set(
        regions[0]["required_context_unit_ids"]
    )
    for row_group in result["groups"]:
        if (
            row_group["kind"] == "table_row"
            and row_group["parent_table_id"] == regions[0]["group_id"]
        ):
            assert {"u1", "u2", "source-note"} <= set(
                row_group["required_context_unit_ids"]
            )


def test_ambiguous_continuation_never_joins_two_different_tables():
    observation = load_case("cross_page_table_continuation")
    second = observation["pages"][1]
    second["units"] = [u for u in second["units"] if u["unit_id"] != "u27"]
    copies = []
    for i, original in enumerate(second["units"]):
        u = copy.deepcopy(original)
        u["unit_id"] = "other-" + u["unit_id"]
        u["ordinal"] = 100 + i
        u["bbox"][1] += 100
        u["bbox"][3] += 100
        copies.append(u)
    second["units"].extend(copies)
    result = derive_layout_hints(observation)
    assert not any(r["kind"] == "continuation" for r in result["relations"])
    assert any(d["code"] == "CONTINUATION_AMBIGUOUS" for d in result["diagnostics"])
    assert result["coverage"]["complete"] is False
    for region in result["groups"]:
        if region["kind"] == "table_region" and any(
            u.startswith("other-") for u in region["member_unit_ids"]
        ):
            assert "u1" not in region["required_context_unit_ids"]


def test_zero_work_budget_keeps_source_refs_and_deferred_identity():
    observation = load_case("whole_row_units_no_cells")
    before = copy.deepcopy(observation)
    result = derive_layout_hints(observation, limits={"max_work_units": 0})
    ids = {u["unit_id"] for p in observation["pages"] for u in p["units"]}
    assert set(result["coverage"]["deferred_unit_ids"]) == ids
    assert result["source_ref"] == observation["source_ref"]
    assert result["groups"] == [] and result["relations"] == []
    assert observation == before


def test_parser_declared_coarse_row_geometry_cannot_prove_cells():
    observation = load_case("table_header_period_unit_footnote")
    for page in observation["pages"]:
        for unit in page["units"]:
            unit["upstream_hints"]["geometry_granularity"] = "row"
    result = derive_layout_hints(observation)
    assert any(d["code"] == "NEEDS_UPSTREAM_GRANULARITY" for d in result["diagnostics"])
    assert not any(group["cells"] for group in result["groups"])
    assert result["coverage"]["complete"] is False
