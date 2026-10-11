from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
path = ROOT / 'tests/test_w05_root_temporal_lineage.py'
body = path.read_text(encoding='utf-8')
body += '''\n\ndef rebind_annual_adjustment(data, formula, inputs, value):
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(time_basis="annual", formula=formula, input_parameter_ids=inputs, value=value)
        target.pop("period_start")
        target.pop("period_end")


@pytest.mark.parametrize("flow_value", [0.0, 10.0])
def test_money_stock_cannot_join_recognized_flow_even_with_real_annual_anchor(flow_value):
    data = acquisition_document()
    typed_assumption(data, "receivable_stock", 20.0, "monetary_balance", "point_in_time")
    typed_assumption(data, "annual_anchor", flow_value, "revenue")
    rebind_annual_adjustment(data, "x0+x1", ["receivable_stock", "annual_anchor"], 20.0 + flow_value)
    with pytest.raises(ForecastInputError, match="typed flow"):
        run_forecast(data)


def test_stock_divided_by_flow_then_multiplied_by_that_flow_stays_stock():
    data = acquisition_document()
    typed_assumption(data, "receivable_stock", 20.0, "monetary_balance", "point_in_time")
    typed_assumption(data, "annual_anchor", 10.0, "revenue")
    ratio = typed_assumption(data, "stock_to_flow", 2.0, "ratio")
    ratio.update(kind="derived_fact", formula="x0/x1", input_parameter_ids=["receivable_stock", "annual_anchor"])
    rebind_annual_adjustment(data, "x0*x1", ["annual_anchor", "stock_to_flow"], 20.0)
    with pytest.raises(ForecastInputError, match="typed flow"):
        run_forecast(data)


def test_actual_annual_turnover_ratio_can_convert_a_money_stock_with_its_flow_ancestry():
    data = acquisition_document()
    typed_assumption(data, "asset_stock", 20.0, "monetary_balance", "point_in_time")
    typed_assumption(data, "annual_anchor", 10.0, "revenue")
    ratio = typed_assumption(data, "annual_turnover", 0.5, "ratio")
    ratio.update(kind="derived_fact", formula="x0/x1", input_parameter_ids=["annual_anchor", "asset_stock"])
    rebind_annual_adjustment(data, "x0*x1", ["asset_stock", "annual_turnover"], 10.0)
    run_forecast(data)


@pytest.mark.parametrize("origin_dimension,origin_basis,expected", [
    ("revenue", "annual", "accept"),
    ("monetary_balance", "point_in_time", "reject"),
])
def test_derived_annual_price_keeps_its_actual_income_or_stock_origin(origin_dimension, origin_basis, expected):
    data = acquisition_document()
    typed_assumption(data, "original_money", 20.0, origin_dimension, origin_basis)
    typed_assumption(data, "operating_customers", 10.0, "quantity", "point_in_time")
    price = typed_assumption(data, "derived_annual_price", 2.0, "revenue_per_unit")
    price.update(kind="derived_fact", formula="x0/x1", input_parameter_ids=["original_money", "operating_customers"])
    rebind_annual_adjustment(data, "x0*x1", ["operating_customers", "derived_annual_price"], 20.0)
    if expected == "reject":
        with pytest.raises(ForecastInputError, match="typed flow"):
            run_forecast(data)
    else:
        run_forecast(data)
'''
assert 'test_actual_annual_turnover_ratio' not in path.read_text(encoding='utf-8')
path.write_text(body, encoding='utf-8')
print('Added actual temporal algebra RED and valid annual turnover/ARPU controls')
