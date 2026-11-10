"""Typed management comparisons over existing RF paths and quarter bridges."""
from __future__ import annotations

from copy import deepcopy
import math
import re

from contracts.constants import SCENARIOS
from contracts.evidence import finite_number, require, validate_claim_ids
from research.native_dependencies import scope_components

SCHEMA = "management-target-comparison/1"
METRICS = {"annual_revenue_level", "quarterly_revenue_level", "year_over_year_growth"}
_SCALES = {"unit": 1, "units": 1, "thousand": 1e3, "million": 1e6, "billion": 1e9,
           "trillion": 1e12, "万元": 1e4, "亿元": 1e8, "亿": 1e8}


def is_typed_target(target: dict) -> bool:
    return isinstance(target.get("comparison_basis"), dict)


def normalize_target_bounds(target: dict, data: dict) -> tuple[float, float]:
    """Convert stated units only; never synthesize a manager dollar target."""
    spec = target["comparison_basis"]
    raw = target.get("raw_target_value")
    low = target.get("raw_target_value_low") if raw is None else raw
    high = target.get("raw_target_value_high") if raw is None else raw
    low = finite_number(low, "target lower bound")
    high = finite_number(high, "target upper bound")
    if spec["metric_kind"] == "year_over_year_growth":
        basis = spec.get("raw_ratio_basis")
        require(basis in {"percent", "fraction", "level_multiple"}, "growth target requires explicit raw_ratio_basis")
        if basis == "percent":
            low, high = low / 100, high / 100
        elif basis == "level_multiple":
            low, high = low - 1, high - 1
    else:
        require(target["raw_unit"] == f"{target['raw_currency']} {target['raw_scale']}",
                "typed target raw unit must match currency/scale used for normalization")
        require(target["raw_currency"] == data["currency"], "typed target currency mismatch; reconcile first")
        require(target["raw_scale"] in _SCALES and data["unit"] in _SCALES, "typed target scale is unsupported")
        factor = _SCALES[target["raw_scale"]] / _SCALES[data["unit"]]
        low, high = low * factor, high * factor
    require(low <= high, "typed target range is inverted")
    return low, high


def validate_typed_target(target, data, parameters, claims, sources, used):
    spec = target["comparison_basis"]
    require(spec.get("schema_version") == SCHEMA, "unsupported typed management comparison")
    metric = spec.get("metric_kind")
    require(metric in METRICS, "unsupported management comparison metric_kind")
    period = spec.get("period")
    pattern = r"FY\d{4}(?:Q[1-4]|H[12])" if metric == "quarterly_revenue_level" else r"FY\d{4}"
    require(isinstance(period, str) and re.fullmatch(pattern, period) is not None, "typed comparison period is invalid")
    year = int(period[2:6])
    treatment = target["treatment"]
    modeled = treatment in {"modeled_scenario", "scenario_boundary", "independent_benchmark"}
    require(target["target_period"] == f"FY{year}", "typed comparison target period mismatch")
    require(bool(target.get("normalization_rationale")), "typed comparison requires normalization rationale")
    if metric != "quarterly_revenue_level":
        require(target["measurement_periods"] == [period], "typed comparison measurement periods mismatch")
    allowed = {"schema_version", "metric_kind", "period"}
    if metric == "year_over_year_growth":
        allowed |= {"base_period", "raw_ratio_basis"}
        base = spec.get("base_period")
        require(base is None or (isinstance(base, str) and re.fullmatch(r"FY\d{4}", base) is not None), "typed growth base_period is invalid")
        require(base is None or int(base[2:]) == year - 1, "year-over-year growth requires the previous fiscal period")
        require(target["measurement_basis"] == "annual_period", "growth measurement basis must be annual_period")
    elif metric == "quarterly_revenue_level":
        allowed.add("scenario_parameter_ids")
        require(target["measurement_basis"] == "quarterly_period" and target.get("target_quarter") == period[6:], "typed quarterly period mismatch")
        mapping = spec.get("scenario_parameter_ids")
        require(mapping is None and not modeled or isinstance(mapping, dict) and set(mapping) == set(SCENARIOS), "quarter bridge requires all scenario parameter paths")
        for scenario, ids in (mapping or {}).items():
            require(isinstance(ids, list) and bool(ids) and len(ids) == len(set(ids)), "quarter bridge parameter IDs must be unique")
            for pid in ids:
                require(pid in parameters and pid in used, "quarter bridge requires a used forecast parameter")
                p = parameters[pid]
                require(p["dimension"] == "revenue" and p.get("measurement_period") == period and p["period"] == f"FY{year}" and p.get("scenario") in {scenario, "all", "shared", None}, "quarter bridge parameter period/scenario/dimension mismatch")
                require(p["currency"] == data["currency"] and p["scale"] == data["unit"], "quarter bridge currency/scale mismatch")
                require(bool(p.get("claim_ids")), "quarter bridge requires checked input claims")
            components = scope_components(data, parameters, target["scope"], scenario, year)
            members = set().union(*components.values()) if components else set()
            require(set(ids) <= members and all(set(ids) & refs for refs in components.values()),
                    "quarter bridge target scope must match its native component ancestry")
    else:
        require(target["measurement_basis"] == "annual_period", "annual comparison measurement basis mismatch")
    require(set(spec) == allowed, "typed comparison fields are not exact")
    low, high = normalize_target_bounds(target, data) if modeled else (None, None)
    if modeled and low == high:
        require(target.get("comparison_value") is not None and math.isclose(finite_number(target["comparison_value"], "comparison_value"), low, rel_tol=1e-9, abs_tol=1e-9), "typed comparison normalization mismatch")
    else:
        require(target.get("comparison_value") is None, "range comparison cannot carry a synthetic point target")
    require(treatment in {"modeled_scenario", "scenario_boundary", "independent_benchmark", "unmodeled_data_gap", "out_of_horizon"}, "unsupported typed target treatment")
    if not modeled:
        require(not target["mapped_scenarios"], "unmodeled typed target cannot claim mapped scenarios")
    if modeled:
        require(year in data["forecast_years"], "typed benchmark must be inside forecast horizon")
        require(target["perimeter_status"] in {"matched", "reconciled"} and target["scope"]["type"] in {"company", "segment"}, "typed comparison perimeter remains unresolved")
        require(bool(target["mapped_parameter_ids"]) and bool(target["mapped_scenarios"]), "typed comparison requires mapped parameters/scenarios")
    source_ids = [claims[cid]["source_id"] for cid in target["claim_ids"]]
    if treatment == "independent_benchmark":
        require(set(target["mapped_scenarios"]) == set(SCENARIOS), "independent comparison requires all scenarios")
        require(bool(target.get("benchmark_rationale")), "independent comparison requires benchmark rationale")
        checked = validate_claim_ids(target.get("benchmark_claim_ids"), claims, "management_target", target["target_id"], target["target_id"], "rationale_support")
        source_ids.extend(c["source_id"] for c in checked)
    normalized = deepcopy(target)
    if metric == "year_over_year_growth" and spec.get("base_period") is None:
        normalized["comparison_status"] = "not_comparable"
        normalized["comparison_reason"] = "base_period_unknown"
    normalized["source_ids"] = list(dict.fromkeys(source_ids))
    normalized["source_publication_dates"] = {sid: sources[sid]["published_date"] for sid in normalized["source_ids"]}
    return normalized


def _annual_value(result, target, scenario, period):
    if period is None:
        return None
    year = period[2:]
    if target["scope"]["type"] == "company":
        if int(year) == result["base_year"]:
            return result["base_revenue"]
        return result["consolidated_forecast"][scenario]["annual_revenue"].get(year)
    segment = next(item for item in result["segments"] if item["name"] == target["scope"]["name"])
    if int(year) == result["base_year"]:
        return segment["base_revenue"]
    output = segment["scenarios"][scenario]
    return output.get("effective_revenue", output["recognized_revenue"]).get(year)


def _meets(observed, low, high, op, tolerance):
    if low != high:
        return low <= observed <= high
    if op == "greater_than":
        return observed > low
    if op == "less_than":
        return observed < low
    if op == "at_least":
        return observed >= low * (1 - tolerance)
    if op == "at_most":
        return observed <= low * (1 + tolerance)
    return math.isclose(observed, low, rel_tol=tolerance, abs_tol=max(abs(low), 1e-12) * tolerance)


def compare_target_measurement(target: dict, result: dict, parameters: dict | None = None) -> dict:
    spec = target["comparison_basis"]
    metric = spec["metric_kind"]
    index = parameters if parameters is not None else {p["parameter_id"]: p for p in result["parameter_trace"]}
    tolerance = finite_number(target.get("comparison_tolerance", 0.01), "comparison_tolerance")
    require(0 <= tolerance <= 0.25, "comparison tolerance outside 0..0.25")
    comparisons = {}
    if target["treatment"] not in {"modeled_scenario", "scenario_boundary", "independent_benchmark"}:
        return comparisons
    low, high = normalize_target_bounds(target, result)
    for scenario in target.get("mapped_scenarios", []):
        denominator = None
        numerator = None
        reason = None
        if metric == "quarterly_revenue_level":
            ids = spec["scenario_parameter_ids"][scenario]
            observed = math.fsum(float(index[pid]["value"]) for pid in ids)
        else:
            numerator = _annual_value(result, target, scenario, spec["period"])
            observed = numerator
            if numerator is None:
                reason = "missing_numerator_period"
        if metric == "year_over_year_growth":
            denominator = _annual_value(result, target, scenario, spec.get("base_period"))
            if numerator is None:
                reason = "missing_numerator_period"
            elif denominator is None:
                reason = "missing_base_period"
            elif denominator <= 0:
                reason = "nonpositive_base_revenue"
            observed = None if reason else numerator / denominator - 1
        row = {"metric_kind": metric, "period": spec["period"], "unit": "ratio" if metric == "year_over_year_growth" else f"{result['currency']} {result['unit']}",
               "modeled_value": observed, "target_value": low if low == high else None,
               "target_low": low, "target_high": high, "comparison": target["comparison"],
               "comparison_status": "not_comparable" if observed is None else "comparable", "reason": reason,
               "meets_target": None if observed is None else _meets(observed, low, high, target["comparison"], tolerance),
               "attainment_ratio": None if observed is None or low == 0 or low != high else observed / low}
        if metric == "year_over_year_growth":
            row.update(base_value=denominator, base_period=spec.get("base_period"), numerator_value=numerator,
                       difference_percentage_points=None if observed is None or low != high else (observed - low) * 100)
            row["derived_revenue_benchmark"] = None if reason or denominator is None or low != high else {
                "origin": "analyst_derived", "value": denominator * (1 + low), "unit": f"{result['currency']} {result['unit']}",
                "formula": "scenario_base_revenue * (1 + normalized_growth_target)",
                "difference": None if numerator is None else numerator - denominator * (1 + low)}
        else:
            row["difference"] = None if observed is None or low != high else observed - low
        if target["treatment"] in {"modeled_scenario", "scenario_boundary"}:
            require(row["meets_target"] is True, "mapped scenario does not satisfy typed management target")
        comparisons[scenario] = row
    return comparisons
