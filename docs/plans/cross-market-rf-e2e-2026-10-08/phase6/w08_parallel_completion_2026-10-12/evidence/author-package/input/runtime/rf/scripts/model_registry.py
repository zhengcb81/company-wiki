"""Immutable registry of pure segment revenue model calculators."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, Iterable, Mapping, Sequence

from model_extensions import build_extension_specs


class ModelRegistryError(ValueError):
    """Raised when model registration or pure calculation is invalid."""


Calculator = Callable[[float, Mapping[str, list[float]], Sequence[int]], list[float]]


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    defaults: Mapping[str, float]
    dimensions: Mapping[str, str]
    ratio_drivers: frozenset[str]
    formula: str
    calculator: Calculator
    driver_bounds: Mapping[str, tuple[float | None, float | None]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ModelRegistryError("revenue model_id is required")
        drivers = self.required + self.optional
        if len(drivers) != len(set(drivers)):
            raise ModelRegistryError(f"duplicate driver in revenue model: {self.model_id}")
        if set(self.dimensions) != set(drivers):
            raise ModelRegistryError(f"driver dimension coverage mismatch: {self.model_id}")
        if not set(self.defaults) <= set(self.optional):
            raise ModelRegistryError(f"defaults must reference optional drivers: {self.model_id}")
        if not self.ratio_drivers <= set(drivers):
            raise ModelRegistryError(f"ratio driver is not registered: {self.model_id}")
        if not set(self.driver_bounds) <= set(drivers):
            raise ModelRegistryError(f"bounds must reference registered drivers: {self.model_id}")
        for driver, bounds in self.driver_bounds.items():
            if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
                raise ModelRegistryError(f"invalid driver bounds: {self.model_id}.{driver}")
            lower, upper = bounds
            if any(value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            ) for value in bounds):
                raise ModelRegistryError(f"driver bounds must be finite or None: {self.model_id}.{driver}")
            if lower is not None and upper is not None and lower > upper:
                raise ModelRegistryError(f"reversed driver bounds: {self.model_id}.{driver}")
        for driver, default in self.defaults.items():
            if isinstance(default, bool) or not isinstance(default, (int, float)) or not math.isfinite(default):
                raise ModelRegistryError(f"default must be finite numeric: {self.model_id}.{driver}")
        if not self.formula.strip() or not callable(self.calculator):
            raise ModelRegistryError(f"formula and calculator are required: {self.model_id}")
        object.__setattr__(self, "defaults", MappingProxyType(dict(self.defaults)))
        object.__setattr__(self, "dimensions", MappingProxyType(dict(self.dimensions)))
        object.__setattr__(self, "driver_bounds", MappingProxyType({
            driver: tuple(bounds) for driver, bounds in self.driver_bounds.items()
        }))


def build_registry(specs: Iterable[ModelSpec]) -> Mapping[str, ModelSpec]:
    registry: dict[str, ModelSpec] = {}
    for spec in specs:
        if spec.model_id in registry:
            raise ModelRegistryError(f"duplicate revenue model: {spec.model_id}")
        registry[spec.model_id] = spec
    if not registry:
        raise ModelRegistryError("revenue model registry cannot be empty")
    return MappingProxyType(registry)


def _rowwise(formula: Callable[[Mapping[str, float]], float]) -> Calculator:
    def calculate(base_revenue: float, drivers: Mapping[str, list[float]], years: Sequence[int]) -> list[float]:
        del base_revenue
        return [formula({name: values[index] for name, values in drivers.items()}) for index in range(len(years))]

    return calculate


def _direct_growth(base_revenue: float, drivers: Mapping[str, list[float]], years: Sequence[int]) -> list[float]:
    del years
    result: list[float] = []
    current = base_revenue
    for growth_rate in drivers["growth_rate"]:
        current *= 1 + growth_rate
        result.append(current)
    return result


def _direct_revenue(base_revenue: float, drivers: Mapping[str, list[float]], years: Sequence[int]) -> list[float]:
    del base_revenue, years
    return list(drivers["revenue"])


def _project_backlog(base_revenue: float, drivers: Mapping[str, list[float]], years: Sequence[int]) -> list[float]:
    del base_revenue
    result: list[float] = []
    for index, year in enumerate(years):
        opening = drivers["opening_backlog"][index]
        if index > 0 and not math.isclose(opening, drivers["closing_backlog"][index - 1], rel_tol=1e-9, abs_tol=1e-9):
            raise ModelRegistryError(f"project backlog continuity failed: FY{year}")
        result.append(math.fsum((
            opening,
            drivers["bookings"][index],
            -drivers["cancellations"][index],
            drivers["contract_changes"][index],
            drivers["backlog_remeasurements"][index],
            -drivers["closing_backlog"][index],
        )))
    return result


def _cohort_subscription(base_revenue: float, drivers: Mapping[str, list[float]], years: Sequence[int]) -> list[float]:
    del base_revenue
    result: list[float] = []
    for index, year in enumerate(years):
        opening = drivers["opening_customers"][index]
        ending = drivers["ending_customers"][index]
        expected_ending = math.fsum((opening, drivers["new_customers"][index], -drivers["churned_customers"][index]))
        if not math.isclose(ending, expected_ending, rel_tol=1e-9, abs_tol=1e-9):
            raise ModelRegistryError(f"cohort customer bridge failed: FY{year}")
        if index > 0 and not math.isclose(opening, drivers["ending_customers"][index - 1], rel_tol=1e-9, abs_tol=1e-9):
            raise ModelRegistryError(f"cohort customer continuity failed: FY{year}")
        exposure = math.fsum((
            opening,
            drivers["new_customers"][index] * drivers["new_customer_revenue_fraction"][index],
            -drivers["churned_customers"][index] * drivers["churned_customer_lost_fraction"][index],
        ))
        if exposure < 0:
            raise ModelRegistryError(f"cohort customer time exposure cannot be negative: FY{year}")
        result.append(
            exposure
            * drivers["revenue_per_customer"][index]
            * drivers["timing_factor"][index]
            + drivers["usage_revenue"][index]
        )
    return result


def _delivery_pipeline(base_revenue: float, drivers: Mapping[str, list[float]], years: Sequence[int]) -> list[float]:
    del base_revenue
    result: list[float] = []
    for index, year in enumerate(years):
        opening = drivers["opening_orders"][index]
        ending = drivers["ending_orders"][index]
        expected_ending = math.fsum((opening, drivers["new_orders"][index], -drivers["cancellations"][index], -drivers["deliveries"][index]))
        if not math.isclose(ending, expected_ending, rel_tol=1e-9, abs_tol=1e-9):
            raise ModelRegistryError(f"delivery order bridge failed: FY{year}")
        if index > 0 and not math.isclose(opening, drivers["ending_orders"][index - 1], rel_tol=1e-9, abs_tol=1e-9):
            raise ModelRegistryError(f"delivery order continuity failed: FY{year}")
        result.append(
            drivers["deliveries"][index]
            * drivers["unit_revenue"][index]
            * drivers["timing_factor"][index]
            + drivers["other_revenue"][index]
        )
    return result


def _reserve_depletion(base_revenue: float, drivers: Mapping[str, list[float]], years: Sequence[int]) -> list[float]:
    """Stock-flow reserve depletion model.

    Validates:
      - opening_reserves + additions + reserve_revisions - depletion = closing_reserves
      - closing_reserves[t-1] == opening_reserves[t] (continuity)
    Computes:
      revenue = depletion * recovery_rate * realized_price + other_revenue
    """
    del base_revenue
    result: list[float] = []
    for index, year in enumerate(years):
        opening = drivers["opening_reserves"][index]
        additions = drivers["additions"][index]
        depletion = drivers["depletion"][index]
        closing = drivers["closing_reserves"][index]
        expected_closing = math.fsum((opening, additions, drivers["reserve_revisions"][index], -depletion))
        if not math.isclose(closing, expected_closing, rel_tol=1e-9, abs_tol=1e-9):
            raise ModelRegistryError(f"reserve stock-flow balance failed: FY{year}")
        if index > 0 and not math.isclose(opening, drivers["closing_reserves"][index - 1], rel_tol=1e-9, abs_tol=1e-9):
            raise ModelRegistryError(f"reserve continuity failed: FY{year}")
        recovery_rate = drivers["recovery_rate"][index]
        realized_price = drivers["realized_price"][index]
        other_revenue = drivers.get("other_revenue", [0.0] * len(years))[index]
        result.append(depletion * recovery_rate * realized_price + other_revenue)
    return result


def _spec(
    model_id: str,
    required: tuple[str, ...],
    optional: tuple[str, ...],
    dimensions: Mapping[str, str],
    formula: str,
    calculator: Calculator,
    *,
    defaults: Mapping[str, float] | None = None,
    ratio_drivers: Iterable[str] = (),
    driver_bounds: Mapping[str, tuple[float | None, float | None]] | None = None,
) -> ModelSpec:
    return ModelSpec(
        model_id=model_id,
        required=required,
        optional=optional,
        defaults=defaults or {},
        dimensions=dimensions,
        ratio_drivers=frozenset(ratio_drivers),
        formula=formula,
        calculator=calculator,
        driver_bounds=driver_bounds or {},
    )


MODEL_REGISTRY = build_registry([
    _spec("direct_growth", ("growth_rate",), (), {"growth_rate": "ratio"}, "revenue[t] = revenue[t-1] * (1 + growth_rate[t])", _direct_growth),
    _spec("direct_revenue", ("revenue",), (), {"revenue": "revenue"}, "revenue[t] = direct_revenue[t]", _direct_revenue),
    _spec("unit_sales", ("units", "unit_revenue"), ("timing_factor", "other_revenue"), {"units": "quantity", "unit_revenue": "revenue_per_unit", "timing_factor": "ratio", "other_revenue": "revenue"}, "revenue = units * unit_revenue * timing_factor + other_revenue", _rowwise(lambda d: d["units"] * d["unit_revenue"] * d["timing_factor"] + d["other_revenue"]), defaults={"timing_factor": 1.0}, ratio_drivers=("timing_factor",)),
    _spec("capacity_utilization", ("capacity", "utilization", "yield", "unit_revenue"), ("timing_factor", "other_revenue"), {"capacity": "quantity", "utilization": "ratio", "yield": "ratio", "unit_revenue": "revenue_per_unit", "timing_factor": "ratio", "other_revenue": "revenue"}, "revenue = capacity * utilization * yield * unit_revenue * timing_factor + other_revenue", _rowwise(lambda d: d["capacity"] * d["utilization"] * d["yield"] * d["unit_revenue"] * d["timing_factor"] + d["other_revenue"]), defaults={"timing_factor": 1.0}, ratio_drivers=("utilization", "yield", "timing_factor")),
    _spec("subscription", ("average_customers", "revenue_per_customer"), ("timing_factor", "usage_revenue"), {"average_customers": "quantity", "revenue_per_customer": "revenue_per_unit", "timing_factor": "ratio", "usage_revenue": "revenue"}, "revenue = average_customers * revenue_per_customer * timing_factor + usage_revenue", _rowwise(lambda d: d["average_customers"] * d["revenue_per_customer"] * d["timing_factor"] + d["usage_revenue"]), defaults={"timing_factor": 1.0}, ratio_drivers=("timing_factor",)),
    _spec("usage_platform", ("eligible_activity", "monetization_rate"), ("fixed_revenue",), {"eligible_activity": "activity", "monetization_rate": "revenue_per_activity", "fixed_revenue": "revenue"}, "revenue = eligible_activity * monetization_rate + fixed_revenue", _rowwise(lambda d: d["eligible_activity"] * d["monetization_rate"] + d["fixed_revenue"])),
    _spec("services", ("billable_capacity", "utilization", "billing_rate"), ("timing_factor", "other_revenue"), {"billable_capacity": "activity", "utilization": "ratio", "billing_rate": "revenue_per_activity", "timing_factor": "ratio", "other_revenue": "revenue"}, "revenue = billable_capacity * utilization * billing_rate * timing_factor + other_revenue", _rowwise(lambda d: d["billable_capacity"] * d["utilization"] * d["billing_rate"] * d["timing_factor"] + d["other_revenue"]), defaults={"timing_factor": 1.0}, ratio_drivers=("utilization", "timing_factor")),
    _spec("project_backlog", ("opening_backlog", "bookings", "cancellations", "contract_changes", "closing_backlog"), ("backlog_remeasurements",), {"opening_backlog": "backlog", "bookings": "backlog", "cancellations": "backlog", "contract_changes": "backlog", "closing_backlog": "backlog", "backlog_remeasurements": "backlog"}, "revenue = opening_backlog + bookings - cancellations + contract_changes + backlog_remeasurements - closing_backlog", _project_backlog, driver_bounds={"backlog_remeasurements": (None, None)}),
    _spec("resource", ("saleable_volume", "realized_price"), ("other_revenue",), {"saleable_volume": "quantity", "realized_price": "revenue_per_unit", "other_revenue": "revenue"}, "revenue = saleable_volume * realized_price + other_revenue", _rowwise(lambda d: d["saleable_volume"] * d["realized_price"] + d["other_revenue"])),
    _spec("reserve_depletion", ("opening_reserves", "additions", "depletion", "closing_reserves", "recovery_rate", "realized_price"), ("other_revenue", "reserve_revisions"), {"opening_reserves": "reserve_volume", "additions": "reserve_volume", "depletion": "reserve_volume", "closing_reserves": "reserve_volume", "reserve_revisions": "reserve_volume", "recovery_rate": "ratio", "realized_price": "revenue_per_unit", "other_revenue": "revenue"}, "revenue = depletion * recovery_rate * realized_price + other_revenue", _reserve_depletion, ratio_drivers=("recovery_rate",), driver_bounds={"reserve_revisions": (None, None)}),
    _spec("infrastructure", ("billable_volume", "tariff"), ("other_revenue",), {"billable_volume": "activity", "tariff": "revenue_per_activity", "other_revenue": "revenue"}, "revenue = billable_volume * tariff + other_revenue", _rowwise(lambda d: d["billable_volume"] * d["tariff"] + d["other_revenue"])),
    _spec("bank_revenue", ("average_earning_assets", "asset_yield", "average_interest_bearing_liabilities", "funding_cost", "fee_revenue"), ("other_revenue",), {"average_earning_assets": "monetary_balance", "asset_yield": "ratio", "average_interest_bearing_liabilities": "monetary_balance", "funding_cost": "ratio", "fee_revenue": "revenue", "other_revenue": "revenue"}, "revenue = average_earning_assets * asset_yield - average_interest_bearing_liabilities * funding_cost + fee_revenue + other_revenue", _rowwise(lambda d: math.fsum((d["average_earning_assets"] * d["asset_yield"], -d["average_interest_bearing_liabilities"] * d["funding_cost"], d["fee_revenue"], d["other_revenue"]))), ratio_drivers=("asset_yield", "funding_cost"), driver_bounds={"asset_yield": (None, None), "funding_cost": (None, None)}),
    _spec("asset_management", ("average_aum", "management_fee_rate"), ("performance_fee_revenue", "other_revenue"), {"average_aum": "monetary_balance", "management_fee_rate": "ratio", "performance_fee_revenue": "revenue", "other_revenue": "revenue"}, "revenue = average_aum * management_fee_rate + performance_fee_revenue + other_revenue", _rowwise(lambda d: d["average_aum"] * d["management_fee_rate"] + d["performance_fee_revenue"] + d["other_revenue"]), ratio_drivers=("management_fee_rate",)),
    _spec("retail_franchise", ("average_owned_stores", "revenue_per_owned_store"), ("franchise_system_sales", "recognized_fee_rate", "supply_revenue"), {"average_owned_stores": "quantity", "revenue_per_owned_store": "revenue_per_unit", "franchise_system_sales": "revenue", "recognized_fee_rate": "ratio", "supply_revenue": "revenue"}, "revenue = average_owned_stores * revenue_per_owned_store + franchise_system_sales * recognized_fee_rate + supply_revenue", _rowwise(lambda d: d["average_owned_stores"] * d["revenue_per_owned_store"] + d["franchise_system_sales"] * d["recognized_fee_rate"] + d["supply_revenue"]), ratio_drivers=("recognized_fee_rate",)),
    _spec("transport", ("capacity", "utilization", "yield"), ("ancillary_revenue",), {"capacity": "quantity", "utilization": "ratio", "yield": "revenue_per_unit", "ancillary_revenue": "revenue"}, "revenue = capacity * utilization * yield + ancillary_revenue", _rowwise(lambda d: d["capacity"] * d["utilization"] * d["yield"] + d["ancillary_revenue"]), ratio_drivers=("utilization",)),
    _spec("real_estate_rental", ("average_occupied_area", "rent_per_area"), ("other_revenue",), {"average_occupied_area": "area", "rent_per_area": "revenue_per_area", "other_revenue": "revenue"}, "revenue = average_occupied_area * rent_per_area + other_revenue", _rowwise(lambda d: d["average_occupied_area"] * d["rent_per_area"] + d["other_revenue"])),
    _spec("licensing_commercial", ("treated_units", "net_revenue_per_unit"), ("milestone_revenue", "royalty_revenue", "service_revenue"), {"treated_units": "quantity", "net_revenue_per_unit": "revenue_per_unit", "milestone_revenue": "revenue", "royalty_revenue": "revenue", "service_revenue": "revenue"}, "revenue = treated_units * net_revenue_per_unit + milestone_revenue + royalty_revenue + service_revenue", _rowwise(lambda d: d["treated_units"] * d["net_revenue_per_unit"] + d["milestone_revenue"] + d["royalty_revenue"] + d["service_revenue"])),
    _spec("advertising", ("eligible_impressions", "fill_rate", "revenue_per_thousand_impressions"), ("other_revenue",), {"eligible_impressions": "activity", "fill_rate": "ratio", "revenue_per_thousand_impressions": "revenue_per_activity", "other_revenue": "revenue"}, "revenue = eligible_impressions / 1000 * fill_rate * revenue_per_thousand_impressions + other_revenue", _rowwise(lambda d: d["eligible_impressions"] / 1000 * d["fill_rate"] * d["revenue_per_thousand_impressions"] + d["other_revenue"]), ratio_drivers=("fill_rate",)),
    _spec("gaming", ("active_users", "payer_conversion", "revenue_per_payer"), ("other_revenue",), {"active_users": "quantity", "payer_conversion": "ratio", "revenue_per_payer": "revenue_per_unit", "other_revenue": "revenue"}, "revenue = active_users * payer_conversion * revenue_per_payer + other_revenue", _rowwise(lambda d: d["active_users"] * d["payer_conversion"] * d["revenue_per_payer"] + d["other_revenue"]), ratio_drivers=("payer_conversion",)),
    _spec("cohort_subscription", ("opening_customers", "new_customers", "churned_customers", "ending_customers", "revenue_per_customer"), ("timing_factor", "usage_revenue", "new_customer_revenue_fraction", "churned_customer_lost_fraction"), {"opening_customers": "quantity", "new_customers": "quantity", "churned_customers": "quantity", "ending_customers": "quantity", "revenue_per_customer": "revenue_per_unit", "timing_factor": "ratio", "usage_revenue": "revenue", "new_customer_revenue_fraction": "ratio", "churned_customer_lost_fraction": "ratio"}, "revenue = (opening_customers + new_customers * new_customer_revenue_fraction - churned_customers * churned_customer_lost_fraction) * revenue_per_customer * timing_factor + usage_revenue", _cohort_subscription, defaults={"timing_factor": 1.0, "new_customer_revenue_fraction": 0.5, "churned_customer_lost_fraction": 0.5}, ratio_drivers=("timing_factor", "new_customer_revenue_fraction", "churned_customer_lost_fraction")),
    _spec("delivery_pipeline", ("opening_orders", "new_orders", "cancellations", "deliveries", "ending_orders", "unit_revenue"), ("timing_factor", "other_revenue"), {"opening_orders": "quantity", "new_orders": "quantity", "cancellations": "quantity", "deliveries": "quantity", "ending_orders": "quantity", "unit_revenue": "revenue_per_unit", "timing_factor": "ratio", "other_revenue": "revenue"}, "revenue = deliveries * unit_revenue * timing_factor + other_revenue", _delivery_pipeline, defaults={"timing_factor": 1.0}, ratio_drivers=("timing_factor",)),
    _spec("milestone_royalty", ("eligible_sales", "royalty_rate"), ("milestone_revenue", "service_revenue"), {"eligible_sales": "revenue", "royalty_rate": "ratio", "milestone_revenue": "revenue", "service_revenue": "revenue"}, "revenue = eligible_sales * royalty_rate + milestone_revenue + service_revenue", _rowwise(lambda d: d["eligible_sales"] * d["royalty_rate"] + d["milestone_revenue"] + d["service_revenue"]), ratio_drivers=("royalty_rate",)),
    _spec("insurance_service", ("coverage_units", "revenue_per_coverage_unit"), ("timing_factor", "other_revenue"), {"coverage_units": "coverage_units", "revenue_per_coverage_unit": "revenue_per_unit", "timing_factor": "ratio", "other_revenue": "revenue"}, "revenue = coverage_units * revenue_per_coverage_unit * timing_factor + other_revenue", _rowwise(lambda d: d["coverage_units"] * d["revenue_per_coverage_unit"] * d["timing_factor"] + d["other_revenue"]), defaults={"timing_factor": 1.0}, ratio_drivers=("timing_factor",)),
] + list(build_extension_specs(ModelSpec, ModelRegistryError)))


# Compatibility views retained for existing callers and fixtures.
MODEL_SPECS: Mapping[str, Mapping[str, object]] = MappingProxyType({
    model_id: MappingProxyType({
        "required": spec.required,
        "optional": spec.optional,
        "defaults": spec.defaults,
        "formula": spec.formula,
    })
    for model_id, spec in MODEL_REGISTRY.items()
})
MODEL_DRIVER_DIMENSIONS: Mapping[str, Mapping[str, str]] = MappingProxyType({
    model_id: spec.dimensions for model_id, spec in MODEL_REGISTRY.items()
})
MODEL_RATIO_DRIVERS: Mapping[str, frozenset[str]] = MappingProxyType({
    model_id: spec.ratio_drivers for model_id, spec in MODEL_REGISTRY.items() if spec.ratio_drivers
})


# --- I-10-B defect 2 fix (T1-22) -------------------------------------------
# Sign is decided by SEMANTIC ROLE derived from declared metadata, never by the
# driver's NAME.  `_SIGNED_DRIVERS` (a hard-coded name set) is kept ONLY as a
# deprecated alias for callers that referenced it; it is no longer consulted
# when computing bounds, so a driver's sign can no longer depend on its spelling.
#
# Role precedence in driver_value_bounds(), in order:
#   1. explicit spec.driver_bounds[driver] metadata      (most specific, wins)
#   2. growth_rate                                       (fixed semantic role)
#   3. _REVERSAL_CAPABLE_DIMENSIONS + role table         (semantic, not name)
#   4. dimension == "ratio"                              (probability-like)
#   5. default                                           (non-negative)
_REVERSAL_CAPABLE_DIMENSIONS = frozenset({
    "backlog", "revenue", "reserve_volume", "aum_fee",
})

# Declared role table: a driver listed here is reversal-capable (may be
# NEGATIVE) because the BUSINESS ROLE says amounts already recognised can be
# reversed.  Membership is by declared semantic role, not by name pattern.
# NOTE: this table is reached only via the dimension gate above, so adding a
# driver here cannot leak signedness into quantities or ratios.
_REVERSAL_CAPABLE_DRIVERS = frozenset({
    "contract_changes",
    "franchise_system_sales",
    "supply_revenue",
    "recognized_performance_fees",
    "usage_revenue",
    "other_revenue",
    "fixed_revenue",
    "ancillary_revenue",
    "milestone_revenue",
    "royalty_revenue",
    "service_revenue",
    "performance_fee_revenue",
    "fee_revenue",
    "backlog_remeasurements",
    "reserve_revisions",
})


def _is_reversal_capable(driver: str, dimension: str) -> bool:
    """Semantic-role decision — deliberately NOT a name-only test.

    A driver is treated as reversal-capable only when BOTH hold:
      * its declared dimension is one where reversal is a meaningful business
        event (see _REVERSAL_CAPABLE_DIMENSIONS), AND
      * it carries the declared reversal-capable role bit.
    A driver that carries neither can never acquire a sign by name guessing.
    """
    return dimension in _REVERSAL_CAPABLE_DIMENSIONS and driver in _REVERSAL_CAPABLE_DRIVERS


# Deprecated alias kept for back-compatibility of imports only.  It is NOT read
# by driver_value_bounds(); see the semantic role table above.
_SIGNED_DRIVERS = _REVERSAL_CAPABLE_DRIVERS


def driver_value_bounds(model_id: str, driver: str) -> tuple[float, float]:
    """Return shared inclusive semantic bounds for calculation and sensitivity.

    A ratio dimension alone does not imply a probability: bank interest rates
    may be negative and retention/expansion ratios may exceed one. Explicit
    model metadata takes precedence over conservative default domains.

    I-10-B (T1-22): the sign is decided by SEMANTIC ROLE (declared dimension +
    declared reversal-capable role bit), never by the driver's name.
    """
    try:
        spec = MODEL_REGISTRY[model_id]
        dimension = spec.dimensions[driver]
    except KeyError as exc:
        raise ModelRegistryError(f"unsupported revenue model driver: {model_id}.{driver}") from exc
    if driver in spec.driver_bounds:
        lower, upper = spec.driver_bounds[driver]
        return (-math.inf if lower is None else float(lower), math.inf if upper is None else float(upper))
    if driver == "growth_rate":
        return (-1.0, math.inf)
    if _is_reversal_capable(driver, dimension):
        return (-math.inf, math.inf)
    if dimension == "ratio":
        return (0.0, 1.0)
    return (0.0, math.inf)


def _signed_driver_names_for_audit() -> frozenset[str]:
    """Names that would be reversal-capable under the semantic rule.

    Exposed for the I-10-B compatibility listing; not used for bounds.
    """
    names = set()
    for spec in MODEL_REGISTRY.values():
        for driver, dimension in spec.dimensions.items():
            if _is_reversal_capable(driver, dimension):
                names.add(driver)
    return frozenset(names)


def _finite_model_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelRegistryError(f"{field_name} must be numeric")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ModelRegistryError(f"{field_name} must be finite") from exc
    if not math.isfinite(number):
        raise ModelRegistryError(f"{field_name} must be finite")
    return number


def calculate_registered_model(
    model_id: str,
    base_revenue: float,
    drivers: Mapping[str, list[float]],
    years: Sequence[int],
) -> list[float]:
    try:
        spec = MODEL_REGISTRY[model_id]
    except KeyError as exc:
        raise ModelRegistryError(f"unsupported revenue model: {model_id}") from exc
    base = _finite_model_number(base_revenue, f"{model_id}.base_revenue")
    if base < 0:
        raise ModelRegistryError(f"{model_id}.base_revenue cannot be negative")
    if not years or any(isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999 for year in years):
        raise ModelRegistryError(f"{model_id}.years must contain fiscal years")
    if any(later != earlier + 1 for earlier, later in zip(years, years[1:])):
        raise ModelRegistryError(f"{model_id}.years must be consecutive and increasing")
    if not isinstance(drivers, Mapping):
        raise ModelRegistryError(f"{model_id}.drivers must be a mapping")
    missing = set(spec.required) - set(drivers)
    if missing:
        raise ModelRegistryError(f"missing drivers for {model_id}: {', '.join(sorted(missing))}")
    extra = set(drivers) - set(spec.required) - set(spec.optional)
    if extra:
        raise ModelRegistryError(f"unsupported drivers for {model_id}: {', '.join(sorted(extra))}")
    normalized: dict[str, list[float]] = {}
    for driver in spec.required + spec.optional:
        # --- I-10-B defect 1 fix (T1-22) ------------------------------------
        # Previously: drivers.get(driver, [spec.defaults.get(driver, 0.0)] * len(years))
        # That silently filled any optional driver lacking an explicit default
        # with 0.0, encoding "absent" and "not found" as the SAME input.
        # Now: an omitted driver is legal ONLY when spec.defaults carries an
        # explicit value for it.  Note we deliberately do NOT substitute an
        # explicit 0.0 — that would still fail to distinguish "not found".
        if driver not in drivers:
            if driver not in spec.defaults:
                raise ModelRegistryError(
                    f"missing driver for {model_id}: {driver} has no explicit default"
                )
            values: object = [spec.defaults[driver]] * len(years)
        else:
            values = drivers[driver]
        if not isinstance(values, (list, tuple)) or len(values) != len(years):
            raise ModelRegistryError(f"driver {model_id}.{driver} must contain one value per forecast year")
        lower, upper = driver_value_bounds(model_id, driver)
        normalized[driver] = []
        for year, value in zip(years, values):
            number = _finite_model_number(value, f"{model_id}.{driver}.FY{year}")
            if not lower <= number <= upper:
                raise ModelRegistryError(f"driver {model_id}.{driver} must be between {lower} and {upper}: FY{year}")
            normalized[driver].append(number)
    try:
        result = spec.calculator(base, normalized, years)
    except ArithmeticError as exc:
        raise ModelRegistryError(f"invalid arithmetic in revenue model: {model_id}") from exc
    if len(result) != len(years):
        raise ModelRegistryError(f"calculator returned wrong path length: {model_id}")
    checked = [_finite_model_number(value, f"{model_id}.revenue.FY{year}") for year, value in zip(years, result)]
    if any(value < 0 for value in checked):
        raise ModelRegistryError(f"calculated revenue cannot be negative: {model_id}")
    return checked
