"""R6-RF-INPUT I1: explicit human-unit conversion for input quantities.

The cross-market US failure built a 5-percentage-point shock as
``shock_value=5.0`` on a ratio parameter. The engine's arithmetic on that
input is self-consistent, so the fix belongs to the construction half: an
explicit, auditable conversion from the unit a human source uses to the
engine's contract unit. This module is that shared responsibility layer; the
engine re-derives and enforces every stored record (see
``analysis/sensitivity.py``), so a forged conversion cannot pass validation.
"""

from __future__ import annotations

import math
from typing import Any

from contracts.evidence import finite_number, require


INPUT_QUANTITY_SCHEMA_VERSION = "rf-input-quantity/1"

# Share-of-total units (dimensionless fractions and their point spellings).
_SHARE_UNITS = {"pp", "percent", "ratio", "basis_point"}
# Aliases authors actually type; normalized before lookup.
_UNIT_ALIASES = {
    "pp": "pp",
    "percentage_point": "pp",
    "percentage_points": "pp",
    "pct": "percent",
    "percent": "percent",
    "%": "percent",
    "ratio": "ratio",
    "fraction": "ratio",
    "bp": "basis_point",
    "basis_point": "basis_point",
    "basis_points": "basis_point",
    # Absolute money scales (scale conversion only, never currency conversion).
    "usd_million": "usd_million",
    "usd_thousand": "usd_thousand",
    "usd_billion": "usd_billion",
    "rmb_million": "rmb_million",
    "rmb_billion": "rmb_billion",
    "rmb_100m": "rmb_100m",
    # Count scales.
    "units": "units",
    "thousand_units": "thousand_units",
    "million_units": "million_units",
}
# Conversion family of each canonical unit: share units never mix with
# absolute money/count units.
_UNIT_FAMILY = {
    "pp": "share",
    "percent": "share",
    "ratio": "share",
    "basis_point": "share",
    "usd_million": "money_usd",
    "usd_thousand": "money_usd",
    "usd_billion": "money_usd",
    "rmb_million": "money_rmb",
    "rmb_billion": "money_rmb",
    "rmb_100m": "money_rmb",
    "units": "count",
    "thousand_units": "count",
    "million_units": "count",
}
# Scale of each unit expressed in the family's base unit (usd, rmb, one unit).
_UNIT_SCALE = {
    "usd_million": 1_000_000.0,
    "usd_thousand": 1_000.0,
    "usd_billion": 1_000_000_000.0,
    "rmb_million": 1_000_000.0,
    "rmb_billion": 1_000_000_000.0,
    "rmb_100m": 100_000_000.0,
    "units": 1.0,
    "thousand_units": 1_000.0,
    "million_units": 1_000_000.0,
}


def _normalize_unit(unit: Any, field: str) -> str:
    require(
        isinstance(unit, str) and bool(unit.strip()),
        f"{field} must be a non-empty unit string",
    )
    normalized = unit.strip().lower()
    canonical = _UNIT_ALIASES.get(normalized)
    require(canonical is not None, f"unknown {field}: {unit}")
    return canonical


def convert_input_quantity(
    value: Any, *, input_unit: str, engine_unit: str
) -> dict[str, Any]:
    """Convert *value* from an explicit human unit to an engine contract unit.

    Returns an audit record preserving the original value/unit and the applied
    conversion; it never silently reinterprets semantics (``ratio`` stays a
    factor, not a percent) and never converts across incompatible unit
    families (a share cannot become money, USD cannot become RMB).
    """
    number = finite_number(value, "value")
    source = _normalize_unit(input_unit, "input_unit")
    target = _normalize_unit(engine_unit, "engine_unit")
    if source != target:
        require(
            _UNIT_FAMILY[source] == _UNIT_FAMILY[target],
            f"incompatible unit conversion: {input_unit} -> {engine_unit}",
        )
    family = _UNIT_FAMILY[source]
    if source == target:
        engine_value = number
        expression = (
            f"{_plain(number)} {source} is already the engine unit {target} (identity)"
        )
    elif family == "share":
        engine_value = _convert_share(number, source, target)
        expression = (
            f"{_plain(number)} {source} = {_format_share(target, engine_value)} "
            f"({_describe_share(source, target)})"
        )
    else:
        factor = _UNIT_SCALE[source] / _UNIT_SCALE[target]
        engine_value = number * factor
        expression = (
            f"{_plain(number)} {source} x {factor:g} = {_plain(engine_value)} {target}"
        )
    require(math.isfinite(engine_value), "converted value must be finite")
    return {
        "schema_version": INPUT_QUANTITY_SCHEMA_VERSION,
        "value": number,
        "input_unit": str(input_unit).strip(),
        "engine_unit": str(engine_unit).strip(),
        "engine_value": engine_value,
        "conversion": expression,
    }


def _plain(number: float) -> str:
    if float(number).is_integer():
        return str(int(number))
    return f"{number:g}"


def _describe_share(source: str, target: str) -> str:
    pair = {
        ("pp", "ratio"): "1 pp = 0.01 ratio fraction",
        ("percent", "ratio"): "1 percent = 0.01 ratio fraction",
        ("basis_point", "ratio"): "1 bp = 0.0001 ratio fraction",
        ("pp", "basis_point"): "1 pp = 100 bp",
        ("ratio", "percent"): "ratio x 100 = percent",
        ("pp", "percent"): "1 pp = 1 percent",
        ("percent", "pp"): "1 percent = 1 pp",
        ("basis_point", "pp"): "100 bp = 1 pp",
        ("ratio", "basis_point"): "ratio x 10000 = bp",
    }
    return pair.get((source, target), f"{source} -> {target}")


def _format_share(unit: str, value: float) -> str:
    plain = _plain(value)
    if unit == "ratio":
        return plain
    return f"{plain} {unit}"


def _convert_share(number: float, source: str, target: str) -> float:
    # Everything funnels through the fraction representation.
    as_ratio = {
        "pp": lambda v: v / 100.0,
        "percent": lambda v: v / 100.0,
        "ratio": lambda v: v,
        "basis_point": lambda v: v / 10_000.0,
    }
    from_ratio = {
        "pp": lambda v: v * 100.0,
        "percent": lambda v: v * 100.0,
        "ratio": lambda v: v,
        "basis_point": lambda v: v * 10_000.0,
    }
    return from_ratio[target](as_ratio[source](number))


def validate_input_quantity_record(record: Any, *, field: str) -> dict[str, Any]:
    """Re-derive a stored ``input_quantity`` record; any drift fails closed.

    Used by the engine and the linter so the stored conversion lineage is
    machine-checked rather than decorative.
    """
    require(isinstance(record, dict), f"{field} must be an object")
    require(
        set(record)
        >= {
            "schema_version", "value", "input_unit", "engine_unit",
            "engine_value", "conversion",
        },
        f"{field} is missing required keys",
    )
    require(
        record.get("schema_version") == INPUT_QUANTITY_SCHEMA_VERSION,
        f"unsupported {field}.schema_version",
    )
    expected = convert_input_quantity(
        record["value"], input_unit=record["input_unit"], engine_unit=record["engine_unit"]
    )
    require(
        math.isclose(
            finite_number(record.get("engine_value"), f"{field}.engine_value"),
            expected["engine_value"],
            rel_tol=0,
            abs_tol=1e-12,
        ),
        f"{field}.engine_value does not match the recorded units: "
        f"{record.get('engine_value')} != {expected['engine_value']}",
    )
    require(
        isinstance(record.get("conversion"), str) and record["conversion"].strip(),
        f"{field}.conversion is required",
    )
    return expected


# Engine contract-unit aliases accepted on sensitivity tests and parameters.
_ENGINE_UNIT_BY_SHOCK = {
    "percentage_point": "ratio",
    "basis_point": "basis_point",
    "percent": "ratio",
    "absolute": None,  # the parameter's own declared unit/scale
}
_SHOCK_SEMANTICS = {
    "additive": {"pp", "basis_point"},
    "multiplicative": {"percent"},
    "absolute": {"usd_million", "usd_thousand", "usd_billion", "rmb_million",
                 "rmb_billion", "rmb_100m", "units", "thousand_units", "million_units"},
}


def build_sensitivity_test(
    *,
    parameter_id: str,
    value: Any,
    input_unit: str,
    shock_semantics: str,
    name: str | None = None,
) -> dict[str, Any]:
    """Build a sensitivity test whose shock unit is explicit and auditable.

    ``shock_semantics`` states how the shock acts on the parameter
    (additive on a ratio, multiplicative, or an absolute amount in the
    parameter's own unit); it must be compatible with ``input_unit`` — the
    wrong pairing (5 percent treated as 5 percentage points) fails loudly
    instead of producing a self-consistent wrong number.
    """
    require(
        isinstance(parameter_id, str) and parameter_id.strip(),
        "parameter_id is required",
    )
    require(shock_semantics in _SHOCK_SEMANTICS, f"unsupported shock semantics: {shock_semantics}")
    unit = _normalize_unit(input_unit, "input_unit")
    require(
        unit in _SHOCK_SEMANTICS[shock_semantics],
        f"input_unit {input_unit} cannot act as a {shock_semantics} shock",
    )
    resolved_shock_type = {
        ("additive", "pp"): "percentage_point",
        ("additive", "basis_point"): "basis_point",
        ("multiplicative", "percent"): "percent",
    }.get((shock_semantics, unit), "absolute")
    # An absolute shock is expressed in the parameter's own declared unit, so
    # the engine unit is the input unit itself (identity record, still audited).
    engine_unit = (
        _ENGINE_UNIT_BY_SHOCK[resolved_shock_type] or str(input_unit).strip()
    )
    record = convert_input_quantity(value, input_unit=input_unit, engine_unit=engine_unit)
    require(record["engine_value"] > 0, "shock magnitude must be positive")
    return {
        "name": name or parameter_id,
        "parameter_id": parameter_id,
        "shock_type": resolved_shock_type,
        "shock_value": record["engine_value"],
        "input_quantity": record,
    }
