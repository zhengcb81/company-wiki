"""Pure, stock/flow-aware revenue models for additional business archetypes.

The registry passes its spec constructor and error class into the factory. This
keeps the existing registry the single registration owner without circular imports.
All timing weights are explicit inputs, never silently assumed half-year factors.
"""

from __future__ import annotations

import math
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence


# (segment base-anchor field, first opening driver, parameter dimension).
# The forecast integration can consume these without model-specific dispatch.
EXTENSION_OPENING_BALANCES = MappingProxyType({
    "subscription_arr_bridge": ("base_arr_parameter_id", "opening_arr", "revenue"),
    "installed_base_aftermarket": ("base_installed_units_parameter_id", "opening_installed_units", "quantity"),
    "store_cohorts": ("base_stores_parameter_id", "opening_stores", "quantity"),
    "aum_fee_bridge": ("base_aum_parameter_id", "opening_aum", "monetary_balance"),
    "finite_adoption": ("base_unserved_market_parameter_id", "opening_unserved_market", "quantity"),
    "inventory_sellthrough": ("base_inventory_parameter_id", "opening_inventory", "quantity"),
})


def _equal(actual: float, expected: float, message: str, error: type[ValueError]) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
        raise error(message)


def _bridge(rows: list[dict[str, float]], index: int, year: int, opening: str,
            closing: str, expected_closing: float, error: type[ValueError]) -> None:
    _equal(rows[index][closing], expected_closing,
           f"{opening} stock-flow balance failed: FY{year}", error)
    if index:
        _equal(rows[index][opening], rows[index - 1][closing],
               f"{opening} continuity failed: FY{year}", error)


def _arr(rows: list[dict[str, float]], years: Sequence[int], error: type[ValueError]) -> list[float]:
    result = []
    for index, (d, year) in enumerate(zip(rows, years)):
        lost = d["opening_arr"] * (1 - d["gross_retention_rate"])
        if d["opening_arr"] * d["gross_retention_rate"] == 0 and d["expansion_arr"] > 0:
            raise error(f"expansion_arr requires retained opening ARR: FY{year}")
        _bridge(rows, index, year, "opening_arr", "closing_arr",
                d["opening_arr"] - lost + d["expansion_arr"] + d["new_arr"], error)
        result.append(d["opening_arr"] - lost * d["lost_arr_revenue_fraction"]
                      + d["expansion_arr"] * d["expansion_revenue_fraction"]
                      + d["new_arr"] * d["new_arr_revenue_fraction"] + d["usage_revenue"])
    return result


def _installed(rows: list[dict[str, float]], years: Sequence[int], error: type[ValueError]) -> list[float]:
    result = []
    for index, (d, year) in enumerate(zip(rows, years)):
        if d["retired_units"] > d["opening_installed_units"]:
            raise error(f"retired_units exceeds opening installed cohort: FY{year}")
        _bridge(rows, index, year, "opening_installed_units", "closing_installed_units",
                d["opening_installed_units"] + d["new_installed_units"] - d["retired_units"], error)
        exposure = (d["opening_installed_units"]
                    + d["new_installed_units"] * d["new_unit_revenue_fraction"]
                    - d["retired_units"] * d["retirement_lost_fraction"])
        result.append(exposure * d["attach_rate"] * d["annual_revenue_per_attached_unit"])
    return result


def _stores(rows: list[dict[str, float]], years: Sequence[int], error: type[ValueError]) -> list[float]:
    result = []
    for index, (d, year) in enumerate(zip(rows, years)):
        if d["closed_stores"] > d["opening_stores"]:
            raise error(f"closed_stores exceeds opening store cohort: FY{year}")
        _bridge(rows, index, year, "opening_stores", "closing_stores",
                d["opening_stores"] + d["new_stores"] - d["closed_stores"], error)
        mature_exposure = d["opening_stores"] - d["closed_stores"] * d["closure_lost_fraction"]
        new_exposure = d["new_stores"] * d["new_store_revenue_fraction"] * d["new_store_productivity"]
        result.append((mature_exposure + new_exposure) * d["annual_revenue_per_mature_store"])
    return result


def _renewable(rows: list[dict[str, float]], years: Sequence[int], error: type[ValueError]) -> list[float]:
    result = []
    for d, year in zip(rows, years):
        if d["period_hours"] <= 0:
            raise error(f"period_hours must be positive: FY{year}")
        delivered_mwh = (d["average_commissioned_mw"] * d["period_hours"]
                         * d["pre_curtailment_capacity_factor"] * (1 - d["curtailment_rate"]))
        blended_price = (d["contracted_share"] * d["contract_price_per_mwh"]
                         + (1 - d["contracted_share"]) * d["merchant_price_per_mwh"])
        result.append(delivered_mwh * blended_price + d["other_revenue"])
    return result


def _aum(rows: list[dict[str, float]], years: Sequence[int], error: type[ValueError]) -> list[float]:
    result = []
    for index, (d, year) in enumerate(zip(rows, years)):
        _bridge(rows, index, year, "opening_aum", "closing_aum",
                d["opening_aum"] + d["inflows"] - d["outflows"] + d["market_change"], error)
        average = (d["opening_aum"] + d["inflows"] * d["inflow_revenue_fraction"]
                   - d["outflows"] * d["outflow_lost_fraction"]
                   + d["market_change"] * d["market_change_revenue_fraction"])
        if average < 0:
            raise error(f"time-weighted AUM must be non-negative: FY{year}")
        result.append(average * d["management_fee_rate"] + d["recognized_performance_fees"])
    return result


def _launch(rows: list[dict[str, float]], years: Sequence[int], error: type[ValueError]) -> list[float]:
    del years, error
    return [min(d["eligible_units"] * d["adoption_rate"], d["annual_supply_capacity"])
            * d["commercial_year_fraction"] * d["net_revenue_per_unit"] for d in rows]


def _adoption(rows: list[dict[str, float]], years: Sequence[int], error: type[ValueError]) -> list[float]:
    result = []
    for index, (d, year) in enumerate(zip(rows, years)):
        _bridge(rows, index, year, "opening_unserved_market", "closing_unserved_market",
                d["opening_unserved_market"] + d["new_eligible_units"]
                - d["removed_eligible_units"] - d["adopted_units"], error)
        result.append(d["adopted_units"] * d["net_revenue_per_unit"])
    return result


def _inventory(rows: list[dict[str, float]], years: Sequence[int], error: type[ValueError]) -> list[float]:
    result = []
    for index, (d, year) in enumerate(zip(rows, years)):
        _bridge(rows, index, year, "opening_inventory", "closing_inventory",
                d["opening_inventory"] + d["saleable_production"] + d["purchased_units"]
                - d["scrapped_units"] - d["sold_units"], error)
        result.append(d["sold_units"] * d["net_revenue_per_unit"])
    return result


def _validate_driver_names(
    model_id: str, dimensions: Mapping[str, str], optional: tuple[str, ...],
    drivers: Mapping[str, list[float]], error: type[ValueError],
) -> None:
    unknown = set(drivers) - set(dimensions)
    missing = set(dimensions) - set(optional) - set(drivers)
    if unknown or missing:
        raise error(f"invalid drivers for {model_id}: missing={sorted(missing)}, unknown={sorted(unknown)}")


def _validate_numeric_driver(value: float, model_id: str, name: str,
                             error: type[ValueError]) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise error(f"driver must be finite numeric: {model_id}/{name}")


def _validate_driver_bound(value: float, lower: float | None, upper: float | None,
                           model_id: str, name: str, error: type[ValueError]) -> None:
    if (lower is not None and value < lower) or (upper is not None and value > upper):
        raise error(f"driver out of bounds: {model_id}/{name}")


def _validate_driver_path(
    model_id: str, name: str, values: list[float], years: Sequence[int],
    dimension: str, bounds: Mapping[str, tuple[float | None, float | None]],
    error: type[ValueError],
) -> None:
    if len(values) != len(years):
        raise error(f"driver path length mismatch: {model_id}/{name}")
    lower, upper = bounds.get(
        name, (0.0, 1.0 if dimension == "ratio" else None),
    )
    for value in values:
        _validate_numeric_driver(value, model_id, name, error)
        _validate_driver_bound(value, lower, upper, model_id, name, error)


def _resolve_driver_paths(
    model_id: str, dimensions: Mapping[str, str], bounds: Mapping[str, tuple[float | None, float | None]],
    drivers: Mapping[str, list[float]], years: Sequence[int], error: type[ValueError],
) -> dict[str, list[float]]:
    resolved = {name: list(drivers.get(name, [0.0] * len(years))) for name in dimensions}
    for name, values in resolved.items():
        _validate_driver_path(model_id, name, values, years, dimensions[name], bounds, error)
    return resolved


def _validate_calculated_output(
    output: list[float], years: Sequence[int], model_id: str,
    error: type[ValueError],
) -> None:
    invalid = len(output) != len(years) or any(
        not math.isfinite(value) or value < 0 for value in output
    )
    if invalid:
        raise error(f"calculated revenue must be finite and non-negative: {model_id}")


def _validated_calculator(model_id: str, dimensions: Mapping[str, str], optional: tuple[str, ...],
                          bounds: Mapping[str, tuple[float | None, float | None]],
                          calculator: Callable[..., list[float]], error: type[ValueError]) -> Callable[..., list[float]]:
    """Keep public pure calculators safe even when called without the input engine."""
    def calculate(base_revenue: float, drivers: Mapping[str, list[float]], years: Sequence[int]) -> list[float]:
        del base_revenue
        _validate_driver_names(model_id, dimensions, optional, drivers, error)
        resolved = _resolve_driver_paths(model_id, dimensions, bounds, drivers, years, error)
        rows = [{name: values[index] for name, values in resolved.items()} for index in range(len(years))]
        output = calculator(rows, years, error)
        _validate_calculated_output(output, years, model_id, error)
        return output
    return calculate


def build_extension_specs(spec_factory: Callable[..., Any], error_type: type[ValueError]) -> tuple[Any, ...]:
    """Return immutable ModelSpecs; the caller owns duplicate checking/registration."""
    def make(model_id: str, groups: Mapping[str, tuple[str, ...]], formula: str,
             calculator: Callable[..., list[float]], *, optional: tuple[str, ...] = (),
             bounds: Mapping[str, tuple[float | None, float | None]] | None = None) -> Any:
        dimensions = {name: dimension for dimension, names in groups.items() for name in names}
        driver_bounds = dict(bounds or {})
        kwargs = dict(model_id=model_id, required=tuple(name for name in dimensions if name not in optional),
                      optional=optional, defaults={}, dimensions=dimensions,
                      ratio_drivers=frozenset(name for name, dim in dimensions.items() if dim == "ratio"),
                      formula=formula,
                      calculator=_validated_calculator(model_id, dimensions, optional, driver_bounds, calculator, error_type))
        if driver_bounds:
            kwargs["driver_bounds"] = driver_bounds
        return spec_factory(**kwargs)

    return (
        make("subscription_arr_bridge", {
            "revenue": ("opening_arr", "expansion_arr", "new_arr", "closing_arr", "usage_revenue"),
            "ratio": ("gross_retention_rate", "lost_arr_revenue_fraction", "expansion_revenue_fraction", "new_arr_revenue_fraction"),
        }, "revenue = opening_arr - opening_arr*(1-gross_retention_rate)*lost_arr_revenue_fraction + expansion_arr*expansion_revenue_fraction + new_arr*new_arr_revenue_fraction + usage_revenue",
             _arr, optional=("usage_revenue",)),
        make("installed_base_aftermarket", {
            "quantity": ("opening_installed_units", "new_installed_units", "retired_units", "closing_installed_units"),
            "ratio": ("new_unit_revenue_fraction", "retirement_lost_fraction", "attach_rate"),
            "revenue_per_unit": ("annual_revenue_per_attached_unit",),
        }, "revenue = (opening_installed_units + new_installed_units*new_unit_revenue_fraction - retired_units*retirement_lost_fraction) * attach_rate * annual_revenue_per_attached_unit", _installed),
        make("store_cohorts", {
            "quantity": ("opening_stores", "new_stores", "closed_stores", "closing_stores"),
            "ratio": ("new_store_revenue_fraction", "closure_lost_fraction", "new_store_productivity"),
            "revenue_per_unit": ("annual_revenue_per_mature_store",),
        }, "revenue = (opening_stores - closed_stores*closure_lost_fraction + new_stores*new_store_revenue_fraction*new_store_productivity) * annual_revenue_per_mature_store", _stores,
             bounds={"new_store_productivity": (0.0, None)}),
        make("renewable_generation", {
            "quantity": ("average_commissioned_mw",), "activity": ("period_hours",),
            "ratio": ("pre_curtailment_capacity_factor", "curtailment_rate", "contracted_share"),
            "revenue_per_unit": ("contract_price_per_mwh", "merchant_price_per_mwh"), "revenue": ("other_revenue",),
        }, "revenue = average_commissioned_mw * period_hours * pre_curtailment_capacity_factor * (1-curtailment_rate) * (contracted_share*contract_price_per_mwh + (1-contracted_share)*merchant_price_per_mwh) + other_revenue",
             _renewable, optional=("other_revenue",),
             bounds={"contract_price_per_mwh": (None, None), "merchant_price_per_mwh": (None, None),
                     "other_revenue": (None, None)}),
        make("aum_fee_bridge", {
            "monetary_balance": ("opening_aum", "inflows", "outflows", "market_change", "closing_aum"),
            "ratio": ("inflow_revenue_fraction", "outflow_lost_fraction", "market_change_revenue_fraction", "management_fee_rate"),
            "revenue": ("recognized_performance_fees",),
        }, "revenue = (opening_aum + inflows*inflow_revenue_fraction - outflows*outflow_lost_fraction + market_change*market_change_revenue_fraction) * management_fee_rate + recognized_performance_fees",
             _aum, optional=("recognized_performance_fees",),
             bounds={"market_change": (None, None), "recognized_performance_fees": (None, None)}),
        make("commercial_launch", {
            "quantity": ("eligible_units", "annual_supply_capacity"),
            "ratio": ("adoption_rate", "commercial_year_fraction"),
            "revenue_per_unit": ("net_revenue_per_unit",),
        }, "conditional_revenue = min(eligible_units*adoption_rate, annual_supply_capacity) * commercial_year_fraction * net_revenue_per_unit", _launch),
        make("finite_adoption", {
            "quantity": ("opening_unserved_market", "new_eligible_units", "removed_eligible_units", "adopted_units", "closing_unserved_market"),
            "revenue_per_unit": ("net_revenue_per_unit",),
        }, "revenue = adopted_units * net_revenue_per_unit; closing_unserved_market = opening_unserved_market + new_eligible_units - removed_eligible_units - adopted_units", _adoption),
        make("inventory_sellthrough", {
            "quantity": ("opening_inventory", "saleable_production", "purchased_units", "scrapped_units", "sold_units", "closing_inventory"),
            "revenue_per_unit": ("net_revenue_per_unit",),
        }, "revenue = sold_units * net_revenue_per_unit; closing_inventory = opening_inventory + saleable_production + purchased_units - scrapped_units - sold_units", _inventory),
    )
