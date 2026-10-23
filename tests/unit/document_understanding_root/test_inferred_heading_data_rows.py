"""Native data rows do not become source section titles through numbering/font."""
from pathlib import Path

import pytest

from company_wiki.document_understanding.observation_adapter import _heading_level
from company_wiki.document_understanding.structure.contract import ObservationUnit
from company_wiki.document_understanding.structure.layout import is_heading
from company_wiki.document_understanding.layout_hints.contract import Unit
from company_wiki.document_understanding.layout_hints.headings import heading_evidence


ROWS = [
    '7. Inventories\n$1,200\n$1,100',
    '3. 現金\n1,234.50*\n900.00*',
    '8. Revenue\n(1,200)\n2,500\n15.0%¹',
    '2. Revenue\n€12,300\n€10,100',
    '5. 期末餘額\n1 234,50\n2 345,60',
    "7.Ending balance\n-\n-\n1,234.50\n50.00\n1,284.50",
    "3.营业收入\n12,345.67\n8,765.43\n40.85",
    "4.本期期末结余\n(1,000.00)\n—\n900.00",
    "8.Capacity\t120\t240\t50.00%",
]


@pytest.fixture(autouse=True)
def verify_source_checkout():
    from company_wiki.document_understanding.structure import layout
    assert Path(layout.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[3] / "src")


def wire(text, native=False):
    return {"unit_id": "value-row", "ordinal": 0, "locator": "original-row",
            "text": text, "kind": "paragraph", "page": 1, "layout": {},
            "hints": {"heading_level": 2, "heading_level_source": "native"} if native else {}}


def font_unit(text):
    # Strong font/numbering is still weaker evidence than visible value cells.
    return Unit("value-row", 0, "original-row", text, (0., 0., 200., 20.),
                30., "bold", True, "paragraph", {}, 1, 0, 600., 800.)


@pytest.mark.parametrize("text", ROWS)
def test_numbered_value_row_is_not_an_inferred_observation_heading(text):
    assert _heading_level(text, {}) is None
    assert _heading_level(text, {"heading_like": True}) is None


@pytest.mark.parametrize("text", ROWS)
def test_numbered_value_row_is_not_an_inferred_structure_heading(text):
    assert not is_heading(ObservationUnit(wire(text), 0))


@pytest.mark.parametrize("text", ROWS)
def test_numbered_value_row_is_not_promoted_by_font_hints(text):
    assert heading_evidence(font_unit(text), {"value-row": (20., 20.)}, 15.)["level"] is None


@pytest.mark.parametrize("text", ROWS)
def test_source_declared_native_heading_is_retained(text):
    assert _heading_level(text, {"heading_level": 2}) == 2
    assert is_heading(ObservationUnit(wire(text, native=True), 0))


@pytest.mark.parametrize("text", ["1.2 Operating progress", "一、主营业务", "3.1 Operating outlook 2026"])
def test_real_heading_with_number_remains_inferred(text):
    assert _heading_level(text, {}) is not None
    assert is_heading(ObservationUnit(wire(text), 0))
    assert heading_evidence(font_unit(text), {"value-row": (20., 20.)}, 15.)["level"] is not None


@pytest.mark.parametrize("source", [None, "numbering", "layout"])
def test_actual_table_region_overrides_fallback_not_native_heading(source):
    text = "2. Capital reserve\n(or share capital)\n-\n-\n-"
    payload = wire(text)
    payload["hints"] = {"table_region": True}
    if source:
        payload["hints"].update(heading_level=2, heading_level_source=source)
        payload["kind"] = "heading"
    assert not is_heading(ObservationUnit(payload, 0))


def test_layout_negative_table_evidence_survives_bridge_without_inventing_table(monkeypatch):
    from copy import deepcopy
    from company_wiki.document_understanding import layout_bridge
    payload = wire("2. Capital reserve\n(or share capital)\n-\n-\n-")
    original = {"source_ref": {"source_id": "source", "source_sha256": "sha"},
                "metadata": {}, "coverage": {}, "units": [payload]}
    before = deepcopy(original)
    def layout_engine(*args, **kwargs):
        return {"unit_hints": [{"unit_id": "value-row", "heading_level": None,
                  "text_column": None, "basis": ["in_table_region"]}],
                "coverage": {"complete": True}, "diagnostics": []}
    monkeypatch.setattr(layout_bridge, "derive_layout_hints", layout_engine)
    enhanced, _ = layout_bridge.apply_layout_hints(original)
    actual = enhanced["units"][0]
    assert actual["hints"]["table_region"] is True
    assert not is_heading(ObservationUnit(actual, 0))
    assert "table_id" not in actual["hints"]
    assert actual["text"] == payload["text"] and actual["locator"] == payload["locator"]
    assert original == before


@pytest.mark.parametrize("kind,hints", [
    ("paragraph", {"heading_level": 2, "heading_level_source": "native"}),
    ("html_heading", {}),
    ("heading", {}),
])
def test_explicit_native_heading_remains_authoritative_in_a_table_region(kind, hints):
    payload = wire("2. Capital reserve\n(or share capital)\n-\n-\n-")
    payload.update(kind=kind, hints={**hints, "table_region": True})
    assert is_heading(ObservationUnit(payload, 0))


@pytest.mark.parametrize("word", ["AGE", "NEW", "DAY", "TOP"])
def test_literal_words_are_not_interpreted_as_currency_codes(word):
    from company_wiki.document_normalization.table_shapes import has_tabular_value_tail
    text = f"1.2 Comparison\n{word} 10\n{word} 20"
    assert not has_tabular_value_tail(text)
