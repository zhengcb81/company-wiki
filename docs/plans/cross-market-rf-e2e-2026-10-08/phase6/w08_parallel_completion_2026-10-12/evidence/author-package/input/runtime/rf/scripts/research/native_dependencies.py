"""Relationships over the existing native parameter/segment/driver DAG.

This module preserves scope, scenario and period when following IDs. It does
not revalidate sources, infer business semantics or create another registry.
"""
from __future__ import annotations
from typing import Any
from forecast.calc import _expand_derived_inputs


def ancestry(parameter_ids, parameters):
    return _expand_derived_inputs(set(parameter_ids), parameters)


def _period_ids(mapping, scenario, year, years):
    ids = mapping.get(scenario, []) if isinstance(mapping, dict) else []
    return [ids[years.index(year)]] if year in years and len(ids) == len(years) else []


def segment_roots(data, segment, scenario, year):
    """Unexpanded revenue roots (driver and recognition IDs) of one segment cell.

    These are the revenue-bearing parameters of that segment/scenario/year; the
    expanded ancestry is available through :func:`segment_ancestry`.
    """
    years = data["forecast_years"]
    if year not in years:
        return []
    drivers = segment.get("scenarios", {}).get(scenario, {}).get("driver_parameter_ids", {})
    roots = [ids[years.index(year)] for ids in drivers.values() if len(ids) == len(years)]
    recognition = segment.get("recognition", {})
    roots.extend(_period_ids(recognition.get("progress_parameter_ids", {}), scenario, year, years))
    roots.extend(_period_ids(recognition.get("carry_in_parameter_ids", {}), scenario, year, years))
    return roots


def direct_parameter_cells(
    data: dict[str, Any], parameter_id: str, *, scope: str, scenario: str
) -> list[tuple[str, str, str]]:
    """Actual direct revenue/recognition consumers, without flattening a bridge.

    A downstream derived FY2027 node may legitimately consume an FY2026
    intermediate. Only a direct root claims to describe that cell itself;
    preserve explicit cross-period ancestry rather than equating all dates.
    """
    cells = []
    for segment in data.get("segments", []):
        if scope not in {data.get("company_name"), segment["name"]}:
            continue
        for year in data["forecast_years"]:
            if parameter_id in segment_roots(data, segment, scenario, year):
                cells.append((segment["name"], scenario, f"FY{year}"))
    return cells


def segment_ancestry(data, parameters, segment, scenario, year):
    return ancestry(segment_roots(data, segment, scenario, year), parameters)


def scope_components(data, parameters, scope, scenario, year):
    segments = [s for s in data.get("segments", [])
                if scope["type"] == "company" or s["name"] == scope["name"]]
    components = {s["name"]: segment_ancestry(data, parameters, s, scenario, year) for s in segments}
    if scope["type"] == "company":
        for adjustment in data.get("forecast_adjustments", []):
            roots = _period_ids(adjustment.get("scenario_parameter_ids", {}), scenario, year, data["forecast_years"])
            if roots:
                components["adjustment:" + adjustment["name"]] = ancestry(roots, parameters)
    return components


def parameter_scopes(data, parameters, pid):
    scopes = set()
    for segment in data.get("segments", []):
        for scenario in segment.get("scenarios", {}):
            for year in data.get("forecast_years", []):
                if pid in segment_ancestry(data, parameters, segment, scenario, year):
                    scopes.add(segment["name"])
    return scopes


def claim_parameter_anchors(claim, parameters, drivers):
    if claim["target_type"] == "parameter":
        pid = claim["target_id"]
        if pid in parameters and claim["claim_id"] in parameters[pid].get("claim_ids", []):
            return {pid}
    elif claim["target_type"] == "growth_driver":
        roots = set()
        for driver in drivers.values():
            if any(n.get("evidence_id") == claim["target_id"]
                   and claim["claim_id"] in n.get("claim_ids", [])
                   for n in driver.get("evidence_nodes", [])):
                roots.update(driver.get("parameter_ids", []))
        return ancestry(roots, parameters)
    return set()


def observation_binding(row, claim, data, parameters, drivers):
    role = claim["evidence_role"]
    if role in {"counterevidence", "counter_comparison", "peer_analogy"}:
        return "related_not_positive_support"
    anchors = claim_parameter_anchors(claim, parameters, drivers)
    if not anchors and claim["target_type"] == "historical_revenue" and role == "history_base":
        return "historical_context"
    if not anchors:
        return "unverified_claim_binding"
    from contracts.evidence import require
    for pid in row["parameter_ids"]:
        require(bool(anchors & ancestry([pid], parameters)), "operating observation parameter binding mismatch")
    for driver_id in row["driver_ids"]:
        require(bool(anchors & ancestry(drivers[driver_id].get("parameter_ids", []), parameters)),
                "operating observation driver binding mismatch")
    status = "bound"
    for pid in row["parameter_ids"]:
        parameter = parameters[pid]
        if row["period"] != parameter.get("measurement_period", parameter["period"]):
            require(role != "mechanism_direction", "operating observation period binding mismatch")
            status = "unverified_period"
        scopes = parameter_scopes(data, parameters, pid)
        if row["scope"] not in {data.get("company_name"), *scopes}:
            if row["scope"] in {s["name"] for s in data.get("segments", [])} and scopes:
                require(role != "mechanism_direction", "operating observation scope binding mismatch")
            status = "unverified_scope"
    return status
