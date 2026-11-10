"""Pure eligibility of parameters actually consumed by annual business roles.

This contract never annualizes amounts, infers dates or checks permissions.
Schema 3.10 derived annual-flow roots reuse the actual formula dimension/period
ancestry before accepting an outer annual label. Schema 3.9 retains its direct
window eligibility; old schemas retain legacy behavior. Partial flows remain
legal supporting facts but cannot directly serve a full-year consumer. Explicit
native stock/rate roles stay distinct from recognized amounts.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from contracts.constants import DATED_CONTRIBUTION_SCHEMA_VERSION, PERIOD_FLOW_SCHEMA_VERSIONS, PERIOD_FLOW_TIME_BASIS
from contracts.evidence import parse_iso_date, period_year, require
from contracts.period_flow import fiscal_year_window, validate_derived_flow_ancestry
from model_registry import MODEL_DRIVER_DIMENSIONS
from revenue_constraints import constraint_parameter_ids


# Dimension alone cannot distinguish stocks from flows in stock-flow bridges.
# These are declared business roles, never substring/name-pattern inference.
_STOCK_DRIVER_ROLES = frozenset({
    ("project_backlog", "opening_backlog"), ("project_backlog", "closing_backlog"),
    ("reserve_depletion", "opening_reserves"), ("reserve_depletion", "closing_reserves"),
    ("cohort_subscription", "opening_customers"), ("cohort_subscription", "ending_customers"),
    ("delivery_pipeline", "opening_orders"), ("delivery_pipeline", "ending_orders"),
    ("subscription_arr_bridge", "opening_arr"), ("subscription_arr_bridge", "closing_arr"),
    ("installed_base_aftermarket", "opening_installed_units"),
    ("installed_base_aftermarket", "closing_installed_units"),
    ("store_cohorts", "opening_stores"), ("store_cohorts", "closing_stores"),
    ("aum_fee_bridge", "opening_aum"), ("aum_fee_bridge", "closing_aum"),
    ("finite_adoption", "opening_unserved_market"), ("finite_adoption", "closing_unserved_market"),
    ("inventory_sellthrough", "opening_inventory"), ("inventory_sellthrough", "closing_inventory"),
    ("subscription", "average_customers"), ("retail_franchise", "average_owned_stores"),
    ("gaming", "active_users"), ("insurance_service", "coverage_units"),
    ("bank_revenue", "average_earning_assets"),
    ("bank_revenue", "average_interest_bearing_liabilities"),
    ("asset_management", "average_aum"),
    ("real_estate_rental", "average_occupied_area"),
    ("renewable_generation", "average_commissioned_mw"),
    ("commercial_launch", "eligible_units"),
})
_STOCK_OR_RATE_DIMENSIONS = frozenset({
    "ratio", "revenue_per_unit", "revenue_per_activity",
    "revenue_per_area",
})


def validate_annual_consumption(
    data: dict[str, Any], parameter_index: dict[str, dict[str, Any]]
) -> None:
    """Validate temporal coverage once at an input/output contract boundary.

    Only direct annual consumer roots are checked. H1/H2 ancestors of an
    explicitly authored annual derived parameter remain valid supporting facts.
    Structural validation and formula evaluation retain their existing owners.
    """
    if data.get("schema_version") not in PERIOD_FLOW_SCHEMA_VERSIONS:
        return
    roles: dict[str, set[str]] = defaultdict(set)
    flow_roles: set[str] = set()

    def add(parameter_id: Any, role: str, *, flow: bool = True) -> None:
        if isinstance(parameter_id, str) and parameter_id in parameter_index:
            roles[parameter_id].add(role)
            if flow:
                flow_roles.add(parameter_id)

    def add_ids(ids: Any, role: str, *, flow: bool = True) -> None:
        if isinstance(ids, list):
            for parameter_id in ids:
                add(parameter_id, role, flow=flow)

    def add_map(values: Any, role: str, *, flow: bool = True) -> None:
        if isinstance(values, dict):
            for ids in values.values():
                add_ids(ids, role, flow=flow)

    add(data.get("reported_total_revenue_parameter_id"), "company annual base")
    add_ids(data.get("base_adjustment_parameter_ids", []), "annual base adjustment")
    segments = data.get("segments", [])
    for segment in segments if isinstance(segments, list) else []:
        if not isinstance(segment, dict):
            continue
        add(segment.get("base_revenue_parameter_id"), "segment annual base")
        scenarios = segment.get("scenarios", {})
        for scenario in scenarios.values() if isinstance(scenarios, dict) else []:
            if not isinstance(scenario, dict):
                continue
            model = scenario.get("model")
            dimensions = MODEL_DRIVER_DIMENSIONS.get(model, {}) if isinstance(model, str) else {}
            driver_map = scenario.get("driver_parameter_ids", {})
            if not isinstance(driver_map, dict):
                continue
            for driver, ids in driver_map.items():
                stock_or_rate = ((isinstance(model, str) and (model, driver) in _STOCK_DRIVER_ROLES) or
                                 dimensions.get(driver) in _STOCK_OR_RATE_DIMENSIONS)
                add_ids(ids, f"annual model {model}.{driver}", flow=not stock_or_rate)
        recognition = segment.get("recognition", {})
        if isinstance(recognition, dict):
            add_map(recognition.get("carry_in_parameter_ids", {}), "annual recognition carry-in")
            add_map(recognition.get("progress_parameter_ids", {}), "annual recognition progress", flow=False)
    adjustments = data.get("forecast_adjustments", [])
    for adjustment in adjustments if isinstance(adjustments, list) else []:
        if isinstance(adjustment, dict):
            add_map(adjustment.get("scenario_parameter_ids", {}), "annual forecast adjustment")
    constraints = data.get("revenue_constraints", [])
    for parameter_id in constraint_parameter_ids(constraints if isinstance(constraints, list) else []):
        parameter = parameter_index.get(parameter_id, {})
        add(parameter_id, "annual revenue constraint", flow=parameter.get("dimension") == "revenue")

    for parameter_id in sorted(roles):
        parameter = parameter_index[parameter_id]
        basis = parameter.get("time_basis")
        if basis == "annual":
            if (data.get("schema_version") == DATED_CONTRIBUTION_SCHEMA_VERSION
                    and parameter_id in flow_roles and parameter.get("kind") == "derived_fact"):
                validate_derived_flow_ancestry(parameter_id, parameter, parameter_index)
            continue
        if basis == "point_in_time" and parameter_id not in flow_roles:
            continue
        role = ", ".join(sorted(roles[parameter_id]))
        require(basis == PERIOD_FLOW_TIME_BASIS,
                f"{parameter_id}: {role} requires annual flow coverage, not {basis}")
        if basis != PERIOD_FLOW_TIME_BASIS:
            continue  # collect-all already recorded the owning temporal error
        year = period_year(parameter.get("period"), f"{parameter_id}.period")
        window = fiscal_year_window(data["fiscal_year_end"], year)
        dates = (parse_iso_date(parameter.get("period_start"), f"{parameter_id}.period_start"),
                 parse_iso_date(parameter.get("period_end"), f"{parameter_id}.period_end"))
        require(dates == window,
                f"{parameter_id}: {role} requires annual flow coverage "
                f"{window[0].isoformat()}..{window[1].isoformat()}; partial flows "
                "must first form an explicitly modeled annual parameter")
