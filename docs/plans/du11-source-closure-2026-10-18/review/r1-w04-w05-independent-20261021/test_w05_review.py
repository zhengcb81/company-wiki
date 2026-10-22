"""Independent subset/perimeter and amount/rate metamorphic controls."""
import os
from pathlib import Path
import sys
from copy import deepcopy

import pytest

WT = Path(os.environ["W05_REVIEW_ROOT"])
sys.path.insert(0, str(WT/"scripts"))
sys.path.insert(0, str(WT/"tests"))
from test_r1_target_scope import result_fixture, measured_target, group_document
from research.target_measurement import compare_target_measurement
from revenue_core import run_forecast, ForecastInputError


def test_group_measurement_is_permutation_invariant_and_does_not_mutate_input():
    result = result_fixture()
    target = measured_target()
    before = deepcopy((result,target))
    expected = compare_target_measurement(target,result)
    assert (result,target) == before
    result["segments"].reverse()
    target["scope"]["segment_names"].reverse()
    assert compare_target_measurement(target,result) == expected


def test_forward_base_period_uses_same_group_not_company_or_historical_base():
    result = result_fixture()
    target = measured_target()
    target["comparison_basis"].update(period="FY2027", base_period="FY2026")
    for segment in result["segments"]:
        for scenario, output in segment["scenarios"].items():
            output["effective_revenue"]["2027"] = output["effective_revenue"]["2026"]*1.1
    result["consolidated_forecast"]["base"]["annual_revenue"]["2027"] = 9999
    rows = compare_target_measurement(target,result)
    assert all(row["modeled_value"] == pytest.approx(.1) for row in rows.values())
    assert rows["base"]["base_value"] == 120
    assert rows["base"]["numerator_value"] == 132


def test_excluded_segment_and_company_aggregate_cannot_change_group_target():
    data = group_document()
    original = run_forecast(data)
    selected = deepcopy(original["management_target_coverage"])
    # The result itself remains native; an excluded segment's path must not
    # leak into group measurement even if its amount changes radically.
    altered = deepcopy(original)
    for output in altered["segments"][2]["scenarios"].values():
        for key in ("effective_revenue","recognized_revenue"):
            if key in output:
                output[key] = {year:value*100 for year,value in output[key].items()}
    target = selected["targets"][0]
    assert compare_target_measurement(target,altered) == target["scenario_comparison"]


def test_group_annual_amount_scales_billions_without_changing_member_scope():
    result = result_fixture()
    target = measured_target()
    target.update(raw_target_value=0.12, raw_target_value_low=None, raw_target_value_high=None,
                  raw_currency="USD", raw_scale="billion", raw_unit="USD billion")
    target["comparison_basis"] = {"schema_version":"management-target-comparison/1", "metric_kind":"annual_revenue_level", "period":"FY2026"}
    rows = compare_target_measurement(target,result)
    assert rows["base"]["modeled_value"] == 120
    assert rows["base"]["target_value"] == 120
    assert rows["base"]["unit"] == "USD million"


def test_group_does_not_silently_convert_foreign_target_money():
    result = result_fixture()
    target = measured_target()
    target.update(raw_target_value=120, raw_currency="CNY", raw_scale="million", raw_unit="CNY million")
    target["comparison_basis"] = {"schema_version":"management-target-comparison/1", "metric_kind":"annual_revenue_level", "period":"FY2026"}
    with pytest.raises(ForecastInputError, match="currency mismatch"):
        compare_target_measurement(target,result)


def test_group_new_forecast_ancestry_rejects_baseline_only_parameter_mapping():
    data = group_document()
    data["management_targets"][0]["mapped_parameter_ids"] = [s["base_revenue_parameter_id"] for s in data["segments"][:2]]
    with pytest.raises(ForecastInputError):
        run_forecast(data)
