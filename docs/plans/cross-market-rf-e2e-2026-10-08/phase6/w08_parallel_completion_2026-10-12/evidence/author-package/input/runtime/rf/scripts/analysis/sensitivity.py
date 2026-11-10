"""Extracted from revenue_core.py during the R9 split (behavior-locked by tests/test_golden_behavior_lock.py)."""

from __future__ import annotations

import math
from typing import Any

import copy

from contracts.constants import SCENARIOS
from contracts.evidence import (
    finite_number,
    period_year,
    require,
)
from forecast.calc import (
    parameter_driver_roles, referenced_parameter_ids, refresh_derived_descendants,
    scenario_forecast_parameter_ids, sensitivity_domain_bounds,
)
from forecast.segments import _run_forecast_core
from model_registry import MODEL_REGISTRY, driver_value_bounds
from research.input_quantities import validate_input_quantity_record


def _sensitivity_bounds(
    parameter: dict[str, Any], roles: set[tuple[str, str]], *, ancestor: bool = False
) -> tuple[float, float]:
    domain = sensitivity_domain_bounds(parameter)
    require(not (ancestor and parameter["dimension"] == "ratio" and domain is None),
            "ancestor ratio sensitivity requires explicit sensitivity_domain")
    model_bounds = [driver_value_bounds(model, driver) for model, driver in roles
                    if model in MODEL_REGISTRY]
    if model_bounds:
        lower = max(bound[0] for bound in model_bounds)
        upper = min(bound[1] for bound in model_bounds)
        require(lower <= upper, "sensitivity parameter has incompatible driver bounds")
        if domain is not None:
            lower, upper = max(lower, domain[0]), min(upper, domain[1])
        require(lower <= upper, "sensitivity_domain conflicts with driver bounds")
        return lower, upper
    if domain is not None and parameter["dimension"] == "ratio":
        return domain
    if parameter["dimension"] == "ratio":
        return (0.0, 1.0)
    if parameter["dimension"] in {
        "quantity",
        "activity",
        "monetary_balance",
        "area",
        "backlog",
        "coverage_units",
        "revenue_per_unit",
        "revenue_per_activity",
        "revenue_per_area",
    }:
        if domain is not None:
            require(domain[1] >= 0, "sensitivity_domain conflicts with physical bounds")
            return max(0.0, domain[0]), domain[1]
        return (0.0, math.inf)
    if parameter["dimension"] == "revenue" and roles:
        return (0.0, math.inf)
    return domain if domain is not None else (-math.inf, math.inf)


def _requested_sensitivity_values(
    test: dict[str, Any], original: float, name: str, dimension: str
) -> tuple[float, float, float | None]:
    shock_type = test.get("shock_type")
    require(
        shock_type
        in {
            "percent",
            "percentage_point",
            "basis_point",
            "absolute",
            "range",
            "discrete",
        },
        f"unsupported sensitivity shock_type for {name}: {shock_type}",
    )
    if shock_type in {"range", "discrete"}:
        down = finite_number(test.get("down_value"), f"{name}.down_value")
        up = finite_number(test.get("up_value"), f"{name}.up_value")
        require(down <= up, f"{name} requires down_value <= up_value")
        return down, up, None
    shock = finite_number(test.get("shock_value"), f"{name}.shock_value")
    require(shock > 0, f"{name}.shock_value must be positive")
    if shock_type == "percent":
        require(
            original != 0,
            f"percent sensitivity cannot be applied to zero parameter: {test.get('parameter_id')}",
        )
        delta = abs(original) * shock
        return original - delta, original + delta, shock
    if shock_type == "percentage_point":
        require(
            dimension == "ratio",
            f"percentage_point sensitivity requires ratio dimension: {test.get('parameter_id')}",
        )
        return original - shock, original + shock, shock
    if shock_type == "basis_point":
        require(
            dimension == "ratio",
            f"basis_point sensitivity requires ratio dimension: {test.get('parameter_id')}",
        )
        delta = shock / 10000
        return original - delta, original + delta, shock
    return original - shock, original + shock, shock


def calculate_sensitivities(
    data: dict[str, Any], result: dict[str, Any]
) -> list[dict[str, Any]]:
    tests = copy.deepcopy(data.get("sensitivity_tests", data.get("sensitivities", [])))
    require(isinstance(tests, list), "sensitivity_tests must be a list")
    for _test in tests:
        if isinstance(_test, dict) and "name" not in _test and "parameter_id" in _test:
            _test["name"] = _test["parameter_id"]
    if not tests:
        return []
    parameter_index = {p["parameter_id"]: p for p in data["parameters"]}
    base_refs = scenario_forecast_parameter_ids(data, "base", parameter_index)
    direct_refs = referenced_parameter_ids(data, "base")
    baseline_terminal = result["consolidated_forecast"]["base"]["terminal_revenue"]
    parameter_positions = {
        parameter["parameter_id"]: index
        for index, parameter in enumerate(data["parameters"])
    }
    outputs: list[dict[str, Any]] = []
    names: set[str] = set()
    tested_parameters: set[str] = set()
    roles = parameter_driver_roles(data, "base")
    for test in tests:
        require(isinstance(test, dict), "every sensitivity test must be an object")
        name = test.get("name")
        parameter_id = test.get("parameter_id")
        require(
            isinstance(name, str) and name.strip(), "sensitivity test name is required"
        )
        require(name not in names, f"duplicate sensitivity test name: {name}")
        names.add(name)
        require(
            parameter_id not in tested_parameters,
            f"duplicate sensitivity parameter_id: {parameter_id}",
        )
        tested_parameters.add(parameter_id)
        require(
            parameter_id in base_refs,
            f"sensitivity parameter is not referenced by the base scenario: {parameter_id}",
        )
        require(
            parameter_id in parameter_positions,
            f"unknown sensitivity parameter_id: {parameter_id}",
        )
        parameter = data["parameters"][parameter_positions[parameter_id]]
        require(
            parameter["kind"] in {"analyst_assumption", "scenario_stress"},
            f"sensitivity parameter must be an assumption or stress: {parameter_id}",
        )
        original = float(parameter["value"])
        requested_down, requested_up, shock = _requested_sensitivity_values(
            test, original, name, parameter["dimension"]
        )
        input_quantity = test.get("input_quantity")
        if input_quantity is not None:
            require(
                input_quantity.get("engine_value") == shock,
                f"{name}.input_quantity.engine_value does not match shock_value: "
                f"{input_quantity.get('engine_value')} != {shock}",
            )
            validate_input_quantity_record(
                input_quantity, field=f"{name}.input_quantity"
            )
        lower, upper = _sensitivity_bounds(
            parameter, roles.get(parameter_id, set()), ancestor=parameter_id not in direct_refs
        )
        effective_down = min(max(requested_down, lower), upper)
        effective_up = min(max(requested_up, lower), upper)
        terminals: dict[str, float] = {}
        refreshed_values: dict[str, dict[str, float]] = {}
        affected: list[str] = []
        for direction, shocked_value in (
            ("down", effective_down),
            ("up", effective_up),
        ):
            shocked = copy.deepcopy(data)
            shocked["parameters"][parameter_positions[parameter_id]]["value"] = (
                shocked_value
            )
            shocked_index = {p["parameter_id"]: p for p in shocked["parameters"]}
            affected = refresh_derived_descendants(shocked_index, parameter_id)
            refreshed_values[direction] = {pid: float(shocked_index[pid]["value"]) for pid in affected}
            shocked.pop("sensitivity_tests", None)
            shocked_result = _run_forecast_core(shocked)
            terminals[direction] = shocked_result["consolidated_forecast"]["base"][
                "terminal_revenue"
            ]
        impact = max(
            abs(terminals["down"] - baseline_terminal),
            abs(terminals["up"] - baseline_terminal),
        )
        output = {
            "name": name,
            "parameter_id": parameter_id,
            "shock_type": test["shock_type"],
            "shock_value": shock,
            "requested_values": {"down": requested_down, "up": requested_up},
            "effective_values": {"down": effective_down, "up": effective_up},
            "clamped": {
                "down": not math.isclose(requested_down, effective_down),
                "up": not math.isclose(requested_up, effective_up),
            },
            "baseline_terminal_revenue": baseline_terminal,
            "down_terminal_revenue": terminals["down"],
            "up_terminal_revenue": terminals["up"],
            "max_absolute_terminal_impact": impact,
            "max_relative_terminal_impact": None
            if baseline_terminal == 0
            else impact / baseline_terminal,
        }
        if affected or parameter_id not in direct_refs or "sensitivity_domain" in parameter:
            output["dependency_recalculation"] = {
                "affected_derived_parameter_ids": affected,
                "derived_values": refreshed_values,
                "basis": "native derived_fact formula DAG",
                "sensitivity_domain": copy.deepcopy(parameter.get("sensitivity_domain")),
            }
        if input_quantity is not None:
            output["input_quantity"] = input_quantity
        outputs.append(output)
    return outputs


def calculate_theme_analysis(
    data: dict[str, Any], validated: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any] | None:
    theme = data.get("theme_analysis")
    if theme is None:
        return None
    require(isinstance(theme, dict), "theme_analysis must be an object")
    require(
        isinstance(theme.get("name"), str) and theme["name"].strip(),
        "theme_analysis.name is required",
    )
    segment_names = theme.get("segment_names")
    require(
        isinstance(segment_names, list) and segment_names,
        "theme_analysis.segment_names is required",
    )
    available = {segment["name"] for segment in result["segments"]}
    require(
        set(segment_names) <= available, "theme_analysis contains an unknown segment"
    )
    counterfactual_ids = theme.get("counterfactual_terminal_parameter_ids")
    require(
        isinstance(counterfactual_ids, dict)
        and set(counterfactual_ids) == set(SCENARIOS),
        "theme counterfactual requires low/base/high parameter IDs",
    )
    output = {"name": theme["name"], "segment_names": segment_names, "scenarios": {}}
    parameter_index = validated["parameter_index"]
    for scenario in SCENARIOS:
        parameter_id = counterfactual_ids[scenario]
        require(
            parameter_id in parameter_index,
            f"unknown theme counterfactual parameter_id: {parameter_id}",
        )
        parameter = parameter_index[parameter_id]
        require(
            parameter.get("scenario") in (None, "all", scenario),
            f"theme counterfactual scenario mismatch: {parameter_id}",
        )
        require(
            parameter["kind"] in {"analyst_assumption", "scenario_stress"},
            f"theme counterfactual must be an explicit assumption: {parameter_id}",
        )
        require(
            parameter["dimension"] == "revenue",
            f"theme counterfactual must use revenue dimension: {parameter_id}",
        )
        require(
            period_year(parameter["period"], f"{parameter_id}.period")
            == validated["years"][-1],
            f"theme counterfactual must use terminal forecast year: {parameter_id}",
        )
        require(
            float(parameter["value"]) >= 0,
            f"theme counterfactual cannot be negative: {parameter_id}",
        )
        theme_revenue = sum(
            list(
                segment["scenarios"][scenario]
                .get(
                    "effective_revenue",
                    segment["scenarios"][scenario]["recognized_revenue"],
                )
                .values()
            )[-1]
            for segment in result["segments"]
            if segment["name"] in segment_names
        )
        counterfactual = float(parameter["value"])
        increment = theme_revenue - counterfactual
        company_terminal = result["consolidated_forecast"][scenario]["terminal_revenue"]
        output["scenarios"][scenario] = {
            "theme_terminal_revenue": theme_revenue,
            "counterfactual_terminal_revenue": counterfactual,
            "theme_incremental_revenue": increment,
            "theme_elasticity_to_company_base": None
            if result["base_revenue"] == 0
            else increment / result["base_revenue"],
            "theme_share_of_company_terminal": None
            if company_terminal == 0
            else theme_revenue / company_terminal,
            "counterfactual_parameter_id": parameter_id,
        }
    return output
