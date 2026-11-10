"""Deterministic cross-segment revenue constraints owned by revenue-forecast."""

from __future__ import annotations

import copy
import math
from typing import Any, Iterable


SCENARIOS = ("low", "base", "high")
CONSTRAINT_TYPES = {"sum_cap", "linked_ratio", "elimination"}


class RevenueConstraintError(ValueError):
    """Raised when a constraint definition or application is invalid."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RevenueConstraintError(message)


def _series(
    ids: Any,
    *,
    field: str,
    scenario: str,
    years: list[int],
    parameter_index: dict[str, dict[str, Any]],
    dimension: str,
) -> tuple[list[float], list[str]]:
    _require(isinstance(ids, list) and len(ids) == len(years), f"{field} must contain one parameter_id per forecast year")
    _require(len(ids) == len(set(ids)), f"{field} contains duplicate parameter_ids")
    values: list[float] = []
    normalized_ids: list[str] = []
    for year, parameter_id in zip(years, ids):
        _require(isinstance(parameter_id, str) and parameter_id in parameter_index, f"unknown constraint parameter_id: {parameter_id}")
        parameter = parameter_index[parameter_id]
        _require(parameter.get("scenario") in {scenario, "all", "shared", None}, f"constraint parameter scenario mismatch: {parameter_id}")
        _require(parameter.get("period") == f"FY{year}", f"constraint parameter period mismatch: {parameter_id}")
        _require(parameter.get("dimension") == dimension, f"constraint parameter dimension mismatch: {parameter_id} must be {dimension}")
        value = parameter.get("value")
        _require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)), f"invalid constraint parameter value: {parameter_id}")
        values.append(float(value))
        normalized_ids.append(parameter_id)
    return values, normalized_ids


def _scenario_series(
    value: Any,
    *,
    field: str,
    years: list[int],
    parameter_index: dict[str, dict[str, Any]],
    dimension: str,
) -> dict[str, tuple[list[float], list[str]]]:
    _require(isinstance(value, dict) and set(value) == set(SCENARIOS), f"{field} must contain exactly low/base/high")
    return {
        scenario: _series(
            value[scenario],
            field=f"{field}.{scenario}",
            scenario=scenario,
            years=years,
            parameter_index=parameter_index,
            dimension=dimension,
        )
        for scenario in SCENARIOS
    }


def _reject_extra_keys(constraint: dict[str, Any], allowed: Iterable[str]) -> None:
    extra = sorted(set(constraint) - set(allowed))
    _require(not extra, f"unsupported constraint fields for {constraint.get('constraint_id')}: {', '.join(extra)}")


def validate_revenue_constraints(
    constraints: Any,
    segment_names: Iterable[str],
    parameter_index: dict[str, dict[str, Any]],
    years: list[int],
) -> list[dict[str, Any]]:
    _require(isinstance(constraints, list), "revenue_constraints must be a list")
    known_segments = set(segment_names)
    normalized: list[dict[str, Any]] = []
    constraint_ids: set[str] = set()
    for position, constraint in enumerate(constraints):
        prefix = f"revenue_constraints[{position}]"
        _require(isinstance(constraint, dict), f"{prefix} must be an object")
        constraint_id = constraint.get("constraint_id")
        _require(isinstance(constraint_id, str) and constraint_id.strip(), f"{prefix}.constraint_id is required")
        _require(constraint_id not in constraint_ids, f"duplicate revenue constraint_id: {constraint_id}")
        constraint_ids.add(constraint_id)
        constraint_type = constraint.get("type")
        _require(constraint_type in CONSTRAINT_TYPES, f"unsupported revenue constraint type: {constraint_type}")
        _require(isinstance(constraint.get("rationale"), str) and constraint["rationale"].strip(), f"constraint rationale is required: {constraint_id}")

        if constraint_type == "sum_cap":
            _reject_extra_keys(constraint, {
                "constraint_id", "type", "segments", "allocation", "scenario_parameter_ids",
                "weight_parameter_ids", "rationale",
            })
            segments = constraint.get("segments")
            _require(isinstance(segments, list) and len(segments) >= 2 and len(segments) == len(set(segments)), f"sum_cap segments must contain at least two unique segments: {constraint_id}")
            unknown = sorted(set(segments) - known_segments)
            _require(not unknown, f"unknown constraint segment: {', '.join(unknown)}")
            allocation = constraint.get("allocation")
            _require(allocation in {"proportional", "fixed_weights"}, f"unsupported sum_cap allocation: {constraint_id}")
            caps = _scenario_series(
                constraint.get("scenario_parameter_ids"), field=f"{constraint_id}.scenario_parameter_ids",
                years=years, parameter_index=parameter_index, dimension="revenue",
            )
            for scenario, (values, _) in caps.items():
                _require(all(value >= 0 for value in values), f"sum_cap cannot be negative: {constraint_id}/{scenario}")
            weights: dict[str, dict[str, tuple[list[float], list[str]]]] | None = None
            if allocation == "fixed_weights":
                raw_weights = constraint.get("weight_parameter_ids")
                _require(isinstance(raw_weights, dict) and set(raw_weights) == set(segments), f"fixed_weights must cover every constrained segment: {constraint_id}")
                weights = {
                    segment: _scenario_series(
                        raw_weights[segment], field=f"{constraint_id}.weight_parameter_ids.{segment}",
                        years=years, parameter_index=parameter_index, dimension="ratio",
                    )
                    for segment in segments
                }
                for scenario in SCENARIOS:
                    for index, year in enumerate(years):
                        annual = [weights[segment][scenario][0][index] for segment in segments]
                        _require(all(value >= 0 for value in annual), f"fixed weight cannot be negative: {constraint_id}/{scenario}/FY{year}")
                        _require(math.isclose(sum(annual), 1.0, rel_tol=0, abs_tol=1e-9), f"fixed weights must sum to one: {constraint_id}/{scenario}/FY{year}")
            else:
                _require("weight_parameter_ids" not in constraint, f"proportional sum_cap cannot contain weight_parameter_ids: {constraint_id}")
            normalized.append({**copy.deepcopy(constraint), "_caps": caps, "_weights": weights})

        elif constraint_type == "linked_ratio":
            _reject_extra_keys(constraint, {
                "constraint_id", "type", "source_segment", "target_segment", "relation",
                "scenario_parameter_ids", "rationale",
            })
            source = constraint.get("source_segment")
            target = constraint.get("target_segment")
            _require(source in known_segments, f"unknown constraint segment: {source}")
            _require(target in known_segments, f"unknown constraint segment: {target}")
            _require(source != target, f"linked_ratio source and target must differ: {constraint_id}")
            _require(constraint.get("relation") in {"exact", "maximum"}, f"linked_ratio relation must be exact or maximum: {constraint_id}")
            ratios = _scenario_series(
                constraint.get("scenario_parameter_ids"), field=f"{constraint_id}.scenario_parameter_ids",
                years=years, parameter_index=parameter_index, dimension="ratio",
            )
            for scenario, (values, _) in ratios.items():
                _require(all(value >= 0 for value in values), f"linked ratio cannot be negative: {constraint_id}/{scenario}")
            normalized.append({**copy.deepcopy(constraint), "_ratios": ratios})

        else:
            _reject_extra_keys(constraint, {
                "constraint_id", "type", "segment_adjustment_parameter_ids", "rationale",
            })
            raw_adjustments = constraint.get("segment_adjustment_parameter_ids")
            _require(isinstance(raw_adjustments, dict) and raw_adjustments, f"elimination must identify at least one segment: {constraint_id}")
            unknown = sorted(set(raw_adjustments) - known_segments)
            _require(not unknown, f"unknown constraint segment: {', '.join(unknown)}")
            adjustments = {
                segment: _scenario_series(
                    raw_adjustments[segment], field=f"{constraint_id}.segment_adjustment_parameter_ids.{segment}",
                    years=years, parameter_index=parameter_index, dimension="revenue",
                )
                for segment in raw_adjustments
            }
            for segment, scenario_values in adjustments.items():
                for scenario, (values, _) in scenario_values.items():
                    _require(all(value <= 0 for value in values), f"elimination must be non-positive: {constraint_id}/{segment}/{scenario}")
            normalized.append({**copy.deepcopy(constraint), "_adjustments": adjustments})
    return normalized


def apply_revenue_constraints(
    segments: list[dict[str, Any]],
    constraints: Any,
    parameter_index: dict[str, dict[str, Any]],
    years: list[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result = copy.deepcopy(segments)
    by_name = {segment["name"]: segment for segment in result}
    _require(len(by_name) == len(result), "duplicate segment name while applying constraints")
    normalized = validate_revenue_constraints(constraints, by_name, parameter_index, years)
    for segment in result:
        for scenario in SCENARIOS:
            segment["scenarios"][scenario]["effective_revenue"] = copy.deepcopy(
                segment["scenarios"][scenario]["recognized_revenue"]
            )

    audit: list[dict[str, Any]] = []
    for constraint in normalized:
        constraint_id = constraint["constraint_id"]
        constraint_type = constraint["type"]
        for scenario in SCENARIOS:
            for index, year in enumerate(years):
                year_key = str(year)
                changes: list[dict[str, Any]] = []
                parameter_ids: list[str] = []
                if constraint_type == "sum_cap":
                    names = constraint["segments"]
                    before = {name: float(by_name[name]["scenarios"][scenario]["effective_revenue"][year_key]) for name in names}
                    cap = constraint["_caps"][scenario][0][index]
                    parameter_ids.append(constraint["_caps"][scenario][1][index])
                    before_total = sum(before.values())
                    after = dict(before)
                    if before_total > cap + 1e-9:
                        if constraint["allocation"] == "proportional":
                            _require(before_total > 0, f"cannot proportionally allocate zero revenue: {constraint_id}/{scenario}/FY{year}")
                            after = {name: value * cap / before_total for name, value in before.items()}
                        else:
                            after = {}
                            for name in names:
                                weight_values, weight_ids = constraint["_weights"][name][scenario]
                                after[name] = cap * weight_values[index]
                                parameter_ids.append(weight_ids[index])
                    for name in names:
                        by_name[name]["scenarios"][scenario]["effective_revenue"][year_key] = after[name]
                        changes.append({"segment": name, "before": before[name], "adjustment": after[name] - before[name], "after": after[name]})

                elif constraint_type == "linked_ratio":
                    source = constraint["source_segment"]
                    target = constraint["target_segment"]
                    source_value = float(by_name[source]["scenarios"][scenario]["effective_revenue"][year_key])
                    before_value = float(by_name[target]["scenarios"][scenario]["effective_revenue"][year_key])
                    ratio = constraint["_ratios"][scenario][0][index]
                    parameter_ids.append(constraint["_ratios"][scenario][1][index])
                    linked_value = source_value * ratio
                    after_value = linked_value if constraint["relation"] == "exact" else min(before_value, linked_value)
                    by_name[target]["scenarios"][scenario]["effective_revenue"][year_key] = after_value
                    changes.append({"segment": target, "before": before_value, "adjustment": after_value - before_value, "after": after_value})

                else:
                    for name, values_by_scenario in constraint["_adjustments"].items():
                        before_value = float(by_name[name]["scenarios"][scenario]["effective_revenue"][year_key])
                        adjustment = values_by_scenario[scenario][0][index]
                        parameter_ids.append(values_by_scenario[scenario][1][index])
                        after_value = before_value + adjustment
                        _require(after_value >= -1e-9, f"elimination makes segment revenue negative: {constraint_id}/{name}/{scenario}/FY{year}")
                        after_value = max(0.0, after_value)
                        by_name[name]["scenarios"][scenario]["effective_revenue"][year_key] = after_value
                        changes.append({"segment": name, "before": before_value, "adjustment": adjustment, "after": after_value})

                audit.append({
                    "constraint_id": constraint_id,
                    "type": constraint_type,
                    "scenario": scenario,
                    "year": year,
                    "parameter_ids": parameter_ids,
                    "changes": changes,
                    "before_total": sum(change["before"] for change in changes),
                    "after_total": sum(change["after"] for change in changes),
                })

    return result, audit


def constraint_parameter_ids(constraints: Any) -> set[str]:
    """Collect declared parameter references before full validation."""
    result: set[str] = set()
    if not isinstance(constraints, list):
        return result

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.endswith("parameter_ids"):
                    collect(child)
                elif isinstance(child, (dict, list)):
                    collect(child)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    result.add(item)
                elif isinstance(item, (dict, list)):
                    collect(item)

    collect(constraints)
    return result
