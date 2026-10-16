"""Actual structure work boundaries; inputs are synthetic, no original IO."""

from copy import deepcopy
from collections.abc import Mapping
import json
from pathlib import Path

import pytest

from company_wiki.document_understanding.structure import build_structure
from company_wiki.document_understanding.layout_hints.contract import WorkBudget


def observation(count=3):
    return {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": "s", "source_sha256": "a" * 64},
        "metadata": {},
        "coverage": {
            "native_scan": "complete",
            "opaque_pages": [],
            "deferred_pages": [],
        },
        "units": [
            {
                "unit_id": f"u{i}",
                "ordinal": i,
                "locator": f"loc:{i}",
                "page": 1,
                "text": "Business"
                if i == 0
                else "During the period we launched a product.",
                "kind": "heading" if i == 0 else "paragraph",
                "role": "company_filing",
                "language": "en",
                "layout": {},
                "hints": {"heading_level": 1} if i == 0 else {},
            }
            for i in range(count)
        ],
    }


class NoAccess(list):
    def __iter__(self):
        raise AssertionError("unpaid unit iteration")

    def __getitem__(self, key):
        raise AssertionError("unpaid unit index")


def test_zero_shared_budget_never_reads_units_and_keeps_source_state():
    raw = observation()
    raw["units"] = NoAccess(raw["units"])
    budget = WorkBudget(0)
    result = build_structure(raw, work_budget=budget)
    assert result["source_ref"] == raw["source_ref"]
    assert result["coverage"]["native_scan"] == "complete"
    assert result["coverage"]["complete"] is False
    assert result["coverage"]["source_unit_count"] == 3
    assert result["semantic_units"] == []
    assert budget.used == 0 and budget.exhausted


def test_shared_budget_is_not_reset_and_tiny_balance_cannot_finish():
    raw = observation(20)
    budget = WorkBudget(20)
    budget.charge(19)
    result = build_structure(raw, work_budget=budget)
    assert budget.used >= 19
    assert budget.exhausted
    assert result["coverage"]["complete"] is False
    assert any(item["code"] == "WORK_BUDGET_EXCEEDED" for item in result["diagnostics"])


def test_ample_shared_budget_preserves_existing_structure_and_input():
    raw = observation(8)
    before = deepcopy(raw)
    legacy = build_structure(raw)
    result = build_structure(raw, work_budget=WorkBudget(2_000_000))
    assert result == legacy
    assert raw == before


def test_standalone_zero_limit_remains_a_real_input_error():
    with pytest.raises(ValueError, match="strictly positive"):
        build_structure(observation(), limits={"max_work_units": 0})


class UnpaidText(str):
    def split(self, *args, **kwargs):
        raise AssertionError("long text was scanned without its character work")


def test_tiny_budget_stops_before_long_text_normalization():
    raw = observation(1)
    raw["units"][0]["text"] = UnpaidText("x" * 64_000)
    budget = WorkBudget(100)
    result = build_structure(raw, work_budget=budget)
    assert budget.exhausted
    assert result["coverage"]["complete"] is False
    assert result["semantic_units"] == []


class UnpaidMetadata(Mapping):
    def __len__(self):
        return 10_000

    def __iter__(self):
        raise AssertionError("metadata was copied before reservation")

    def __getitem__(self, key):
        raise AssertionError("metadata was copied before reservation")


def test_metadata_materialization_is_reserved_before_iterating():
    raw = observation(1)
    raw["metadata"] = UnpaidMetadata()
    budget = WorkBudget(100)
    result = build_structure(raw, work_budget=budget)
    assert budget.exhausted
    assert result["coverage"]["complete"] is False


def test_source_coverage_counts_survive_without_visiting_page_lists():
    raw = observation()
    raw["coverage"]["native_scan"] = "partial"
    raw["coverage"]["opaque_pages"] = NoAccess([2, 3])
    raw["coverage"]["deferred_pages"] = NoAccess([4])
    result = build_structure(raw, work_budget=WorkBudget(0))
    assert result["coverage"]["native_scan"] == "partial"
    assert result["coverage"]["source_opaque_page_count"] == 2
    assert result["coverage"]["source_deferred_page_count"] == 1
    assert result["coverage"]["unobserved_ids_limited"]


FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures/document_understanding_structure/inputs"
)


@pytest.mark.parametrize(
    "path", sorted(FIXTURES.glob("*.json")), ids=lambda path: path.stem
)
def test_shared_budget_preserves_all_frozen_structure_shapes(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    before = deepcopy(raw)
    legacy = build_structure(raw)
    result = build_structure(raw, work_budget=WorkBudget(2_000_000))
    assert result == legacy
    assert raw == before


def test_exhaustion_preserves_closed_qa_but_not_an_open_question():
    raw = observation(4)
    for index, (text, role, turn) in enumerate(
        [
            ("Business", "company_filing", None),
            ("Will this product launch?", "investor_question", "t1"),
            ("We have not launched the product.", "management", "t1"),
            ("What about the next product?", "investor_question", "t2"),
        ]
    ):
        raw["units"][index].update(text=text, role=role)
        if turn is not None:
            raw["units"][index]["hints"].update(turn_id=turn)
    full_budget = WorkBudget(2_000_000)
    full = build_structure(raw, work_budget=full_budget)
    assert any(unit["kind"] == "qa_exchange" for unit in full["semantic_units"])
    # Stop the same actual execution just before it can finish the final
    # result, exercising stage retention without hardcoding operation counts.
    budget = WorkBudget(full_budget.used - 1)
    stopped = build_structure(raw, work_budget=budget)
    assert budget.exhausted and not stopped["coverage"]["complete"]
    assert stopped["sections"]
    exchanges = [u for u in stopped["semantic_units"] if u["kind"] == "qa_exchange"]
    assert len(exchanges) == 1
    assert exchanges[0]["anchor_unit_ids"] == ["u2"]
    assert exchanges[0]["required_context_unit_ids"] == ["u1"]
    assert "u3" not in exchanges[0]["member_unit_ids"]
    assert raw["units"][2]["text"] == "We have not launched the product."


def test_pairwise_language_work_stops_before_unpaid_candidate_expansion():
    from company_wiki.document_understanding.structure.relations import _pair_lanes
    from company_wiki.document_understanding.layout_hints.contract import (
        WorkBudgetExceeded,
    )

    class Observed(list):
        visits = 0

        def __iter__(self):
            for value in super().__iter__():
                self.visits += 1
                yield value

    values = Observed([object()] * 100)
    budget = WorkBudget(25)
    with pytest.raises(WorkBudgetExceeded):
        _pair_lanes(None, values, values, allow_self=True, work_budget=budget)
    assert budget.exhausted
    assert values.visits <= 2


def test_empty_input_cannot_copy_unpaid_source_coverage_tail():
    raw = observation(0)
    raw["coverage"]["opaque_pages"] = NoAccess(list(range(10_000)))
    budget = WorkBudget(100)
    result = build_structure(raw, work_budget=budget)
    assert budget.exhausted and not result["coverage"]["complete"]
    assert result["coverage"]["source_opaque_page_count"] == 10_000


def test_six_thousand_mixed_fixture_units_fit_unchanged_two_million_budget():
    """Representative synthetic expansion, not a claim of live corpus coverage."""
    fixtures = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(FIXTURES.glob("*.json"))
    ]
    raw = deepcopy(fixtures[0])
    raw["units"] = []
    raw["coverage"] = {
        "native_scan": "complete",
        "opaque_pages": [],
        "deferred_pages": [],
    }
    block = 0
    while len(raw["units"]) < 6000:
        for original in fixtures[block % len(fixtures)]["units"]:
            if len(raw["units"]) == 6000:
                break
            unit = deepcopy(original)
            unit.update(
                unit_id=f"{block}:{unit['unit_id']}",
                ordinal=len(raw["units"]),
                locator=f"scale:{len(raw['units'])}",
                page=block * 100 + (unit.get("page") or 0),
            )
            for field in ("table_id", "turn_id"):
                if unit.get("hints", {}).get(field):
                    unit["hints"][field] = f"{block}:{unit['hints'][field]}"
            raw["units"].append(unit)
        block += 1
    legacy = build_structure(raw)
    budget = WorkBudget(2_000_000)
    result = build_structure(raw, work_budget=budget)
    assert not budget.exhausted
    assert result == legacy
    assert len(result["semantic_units"]) > 1000
    assert len(result["relations"]) > 1000
