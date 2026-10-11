from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
EVIDENCE = Path(__file__).resolve().parent
prior = EVIDENCE / 'typed-boundary-pre-P1'
assert not prior.exists()
prior.mkdir()
for name in ('ROOT-fix-summary.md', 'root-product-inventory.json', 'final-engineering.log',
             'final-node.json', 'manifest.json'):
    shutil.copyfile(EVIDENCE / name, prior / name)
shutil.copyfile(ROOT / 'docs/handoffs/w05-rf-flow/ROOT-reception.md', prior / 'ROOT-reception.md')
source = EVIDENCE.parent / 'independent-final/original-and-independent-probes.json'
document = json.loads(source.read_text(encoding='utf-8'))
case = next(item for item in document['cases'] if item['case'] == 'independent_point_stock_cannot_be_annual_revenue_alias')
(EVIDENCE / 'typed-boundary-exact-independent-red.json').write_text(json.dumps({
    'origin': str(source), 'origin_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'case': case}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

path = ROOT / 'tests/test_w05_root_temporal_lineage.py'
body = path.read_text(encoding='utf-8')
assert 'test_nonflow_aliases_cannot_become_annual_revenue' not in body
body += '''\n\ndef typed_assumption(data, parameter_id, value, dimension, basis="annual"):
    from test_data_contract import apply_parameter_contract
    item = {"parameter_id": parameter_id, "kind": "analyst_assumption", "value": value,
            "unit": "ratio" if dimension == "ratio" else "USD million",
            "period": "FY2026", "definition": f"Typed synthetic {parameter_id}",
            "scenario": None, "source_ids": [], "rationale": "Synthetic typed test assumption"}
    apply_parameter_contract(data, item, dimension)
    item["time_basis"] = basis
    data["parameters"].append(item)
    return item


@pytest.mark.parametrize("dimension,basis,formula,value", [
    ("monetary_balance", "point_in_time", "x0", 20.0),
    ("monetary_balance", "annual", "x0", 20.0),
    ("quantity", "point_in_time", "x0", 20.0),
    ("ratio", "annual", "x0", 0.2),
    ("ratio", "annual", "100*x0", 20.0),
    ("ratio", "annual", "20", 20.0),
    ("revenue", "annual", "0*x0+20", 20.0),
])
def test_nonflow_aliases_cannot_become_annual_revenue(dimension, basis, formula, value):
    data = acquisition_document()
    source_value = 0.2 if dimension == "ratio" else 20.0
    typed_assumption(data, "typed_origin", source_value, dimension, basis)
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(time_basis="annual", formula=formula, input_parameter_ids=["typed_origin"], value=value,
                      rationale="Relabeling with an explanation must not change a type")
        target.pop("period_start")
        target.pop("period_end")
    with pytest.raises(ForecastInputError, match="typed flow"):
        run_forecast(data)


def test_nested_annual_aliases_do_not_erase_original_stock_type():
    data = acquisition_document()
    typed_assumption(data, "typed_balance", 20.0, "monetary_balance", "point_in_time")
    add_window_parameter(data, "renamed_balance", 20.0, None, None, 2026, time_basis="annual",
                         kind="derived_fact", claim=False, formula="x0", input_parameter_ids=["typed_balance"],
                         definition="Intermediate revenue renamed from receivables")
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(time_basis="annual", formula="x0", input_parameter_ids=["renamed_balance"], value=20.0)
        target.pop("period_start")
        target.pop("period_end")
    with pytest.raises(ForecastInputError, match="typed flow"):
        run_forecast(data)


def test_annual_derived_revenue_cannot_be_a_ratio_of_two_revenues():
    data = acquisition_document()
    typed_assumption(data, "annual_left", 20.0, "revenue")
    typed_assumption(data, "annual_right", 10.0, "revenue")
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(time_basis="annual", formula="x0/x1", input_parameter_ids=["annual_left", "annual_right"], value=2.0)
        target.pop("period_start")
        target.pop("period_end")
    with pytest.raises(ForecastInputError, match="typed flow"):
        run_forecast(data)


def test_point_quantity_times_annual_arpu_is_a_valid_typed_annual_revenue():
    data = acquisition_document()
    typed_assumption(data, "average_customers", 10.0, "quantity", "point_in_time")
    typed_assumption(data, "annual_arpu", 2.0, "revenue_per_unit")
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(time_basis="annual", formula="x0*x1", input_parameter_ids=["average_customers", "annual_arpu"], value=20.0)
        target.pop("period_start")
        target.pop("period_end")
    run_forecast(data)


@pytest.mark.parametrize("model,stocks", [
    ("subscription", {"average_customers"}),
    ("asset_management", {"average_aum"}),
    ("bank_revenue", {"average_earning_assets", "average_interest_bearing_liabilities"}),
])
def test_native_stock_price_and_fee_models_keep_explicit_business_roles(model, stocks):
    import copy
    from test_industry_end_to_end import model_document
    data = model_document(model)
    expected = run_forecast(copy.deepcopy(data))
    data["schema_version"] = "3.10"
    for scenario in data["segments"][0]["scenarios"].values():
        for driver in stocks:
            for identifier in scenario["driver_parameter_ids"][driver]:
                parameter(data, identifier)["time_basis"] = "point_in_time"
    result = run_forecast(data)
    assert result["consolidated_forecast"] == expected["consolidated_forecast"]


def test_standalone_annual_consumer_checks_derived_type_before_annual_label():
    from contracts.annual_consumption import validate_annual_consumption
    origin = {"parameter_id": "stock", "dimension": "monetary_balance", "time_basis": "point_in_time",
              "period": "FY2026", "kind": "reported_fact", "value": 20.0}
    alias = {"parameter_id": "alias", "dimension": "revenue", "time_basis": "annual", "period": "FY2026",
             "kind": "derived_fact", "value": 20.0, "formula": "x0", "input_parameter_ids": ["stock"]}
    data = {"schema_version": "3.10", "fiscal_year_end": "12-31", "segments": [],
            "forecast_adjustments": [{"scenario_parameter_ids": {"low": ["alias"]}}]}
    with pytest.raises(ForecastInputError, match="typed flow"):
        validate_annual_consumption(data, {"stock": origin, "alias": alias})
'''
path.write_text(body, encoding='utf-8')
print('Preserved pre-P1 freeze and independent exact RED; added generalized typed-boundary RED/positive controls')
