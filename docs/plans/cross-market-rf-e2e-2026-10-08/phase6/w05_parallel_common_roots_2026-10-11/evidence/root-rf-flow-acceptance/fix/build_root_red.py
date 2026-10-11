from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
TARGET = ROOT / 'tests/test_w05_root_temporal_lineage.py'
assert ROOT.is_dir() and TARGET.resolve().is_relative_to(ROOT.resolve())
assert not TARGET.exists()
TARGET.write_text('''"""ROOT business regressions for temporal meaning through the actual RF DAG.

All amounts are synthetic test fixtures. Tests use native input/forecast readers.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from revenue_core import ForecastInputError, run_forecast
from test_w05_dated_contribution_contract import add_window_parameter, parameter, schema_3_10_document
from test_w05_dated_contribution_output import add_acquisition_adjustment


def acquisition_document():
    data = schema_3_10_document()
    add_acquisition_adjustment(data)
    return data


def test_partial_flow_cannot_become_full_year_by_derived_annual_alias():
    data = acquisition_document()
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(time_basis="annual", formula="x0", input_parameter_ids=["cmp_post_2026"], value=1.29190208)
        for field in ("period_start", "period_end", "rationale"):
            target.pop(field)
    with pytest.raises(ForecastInputError, match="composition"):
        run_forecast(data)


def test_rationale_cannot_relabel_existing_2026_amount_as_2027_flow():
    data = acquisition_document()
    data.pop("forecast_adjustments")
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(period="FY2027", period_start="2027-01-01", period_end="2027-12-31", rationale="explicit composition")
    with pytest.raises(ForecastInputError, match="composition"):
        run_forecast(data)


def test_same_perimeter_h1_and_its_q2_cannot_be_added_despite_rationale():
    data = acquisition_document()
    definition = "Segment A recognized revenue"
    add_window_parameter(data, "same_h1", 55.0, "2026-01-01", "2026-06-30", 2026, definition=definition)
    add_window_parameter(data, "same_q2", 30.0, "2026-04-01", "2026-06-30", 2026, definition=definition)
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(formula="x0+x1", input_parameter_ids=["same_h1", "same_q2"], value=85.0,
                      definition=definition, rationale="Q2 is a subset of H1; intentional overlap")
    with pytest.raises(ForecastInputError, match="composition"):
        run_forecast(data)


def test_zero_weight_full_year_input_does_not_fill_missing_flow_coverage():
    data = acquisition_document()
    add_window_parameter(data, "unused_full_year", 42.0, "2026-01-01", "2026-12-31", 2026)
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(formula="x0+0*x1", input_parameter_ids=["cmp_post_2026", "unused_full_year"], value=1.29190208)
        target.pop("rationale")
    with pytest.raises(ForecastInputError, match="composition"):
        run_forecast(data)
''', encoding='utf-8')
