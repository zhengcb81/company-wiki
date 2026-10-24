"""Independent reverse controls: native prose wrapping is not a value-cell run."""
from pathlib import Path

import pytest

from company_wiki.document_normalization import table_shapes
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_routing import FINANCIAL_REPORT_SELECTION_LIMIT
from unit.document_understanding_selection.test_reading_untyped_numeric_quality import (
    FLAG, _assert_quality_reaches_citation_and_model, _document,
    _native_carrier_document, _snapshot,
)


@pytest.fixture(autouse=True)
def checkout_binding():
    root = Path(__file__).resolve().parents[3] / "src"
    for module in (reading, table_shapes):
        assert Path(module.__file__).resolve().is_relative_to(root)


def select(parsed):
    original = _snapshot(parsed)
    budget = WorkBudget(16_000_000)
    result = reading.select_reading_evidence(
        parsed, title="Annual report", existing_kind="annual_report", work_budget=budget,
    )
    assert not budget.exhausted and 0 < budget.used <= 16_000_000
    assert result.selection_limit == FINANCIAL_REPORT_SELECTION_LIMIT
    assert sum(len(span.raw_text) for span in result.evidence_spans) <= 48_000
    assert _snapshot(parsed) == original
    return result


@pytest.mark.parametrize("parts", [
    ("The company served", "735", "customers last year and now has", "900", "customers."),
    ("公司已交付", "27", "台设备，新增产线年产能达到", "360", "台。"),
])
def test_complete_prose_quantity_tokens_split_by_native_wrapping_are_not_table_cells(parts):
    parsed = _native_carrier_document(parts)
    result = select(parsed)
    spans = [span for span in result.evidence_spans
             if span.structured_value.get("unit_kind") == "pdf_native_range"]
    assert len(spans) == 1 and spans[0].raw_text == "\n".join(parts)
    assert FLAG not in spans[0].quality_flags
    assert set(spans[0].structured_value["native_range"]["source_unit_ids"]) == {
        unit.unit_id for unit in parsed.units
    }


@pytest.mark.parametrize("row", [
    "Active customers\n735\n—\n626\nIncrease from new distribution channels",
    "Active customers\t735\t-\t626\tIncrease from new distribution channels",
    "客戶數量 | 164 | – | 127 | 增加源自海外渠道",
    "Active customers\n735\n626\nIncrease from new distribution channels\nService outlets\n45\n39",
])
def test_genuine_consecutive_value_cells_keep_unknown_even_with_missing_cell_and_trailing_prose(row):
    parsed = _document(["Business review", row])
    result = select(parsed)
    spans = [span for span in result.evidence_spans if span.raw_text == row]
    _assert_quality_reaches_citation_and_model(result, spans)
    assert spans[0].coordinates == parsed.units[-1].coordinates
    assert not {"unit", "currency", "period"}.intersection(spans[0].structured_value)


def test_one_observed_value_plus_missing_markers_does_not_invent_two_numbers():
    row = "Active customers\n—\n735\n–\nIncrease from new distribution channels"
    result = select(_document(["Business review", row]))
    spans = [span for span in result.evidence_spans if span.raw_text == row]
    assert spans and all(FLAG not in span.quality_flags for span in spans)


def test_refused_numeric_quality_scan_is_work_deferred_without_fabricated_table_shape(monkeypatch):
    parsed = _document([
        "Business review",
        "The company delivered industrial equipment to customers for qualification.",
    ])
    original = _snapshot(parsed)
    full_budget = WorkBudget(16_000_000)
    active_budget = full_budget
    scans = []
    detector = reading.has_unbound_numeric_cells

    def observed_detector(text):
        # Observe the actual public-path port after its real shared-account
        # precharge. No assumed phase position, fixed cost or reset budget.
        scans.append((active_budget.used, text))
        return detector(text)

    monkeypatch.setattr(reading, "has_unbound_numeric_cells", observed_detector)
    full = reading.select_reading_evidence(
        parsed, title="Annual report", existing_kind="annual_report", work_budget=full_budget,
    )
    assert full.evidence_spans and scans and not full_budget.exhausted
    assert all(FLAG not in span.quality_flags for span in full.evidence_spans)
    first_scan_used = scans[0][0]
    assert first_scan_used > 1
    active_budget = limited = WorkBudget(first_scan_used - 1)
    scans.clear()
    deferred = reading.select_reading_evidence(
        parsed, title="Annual report", existing_kind="annual_report", work_budget=limited,
    )
    assert not scans, "the refused precharge must prevent the actual quality scan"
    assert limited.exhausted and limited.used <= limited.max_work_units
    assert deferred.status == "needs_review" and not deferred.coverage_complete
    assert not deferred.evidence_spans
    diagnostics = [item.get("code") for item in deferred.selection_diagnostics]
    reasons = [item.get("reason") for item in (deferred.reading_context or {}).get("deferred", ())]
    assert "work_budget_exhausted" in diagnostics or "OPERATING_WORK_BUDGET" in reasons
    assert _snapshot(parsed) == original
