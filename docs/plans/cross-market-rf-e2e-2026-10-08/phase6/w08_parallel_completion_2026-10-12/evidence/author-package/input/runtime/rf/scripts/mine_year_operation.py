"""ZR-605: MineYearOperation input contract for mining revenue models.

A MineYearOperation bundles the seven required inputs for one mine's
annual operating data:

  volume    — ore tonnes processed (kt, Mt, etc.)    > 0
  grade     — metal grade (g/t, %, etc.)             > 0
  recovery  — metallurgical recovery rate             ∈ (0, 1]
  payable   — payable percentage (smelter terms)      ∈ (0, 1]
  product   — what's produced (e.g. "copper concentrate", "gold doré")
  period    — fiscal year (e.g. "FY2026")
  scenario  — low / base / high

All seven are required; missing any field creates a gap (ForecastInputError)
— never silently defaulting to zero (the ADR §1 principle: per-mine
contributions are model estimates, not disclosure facts, and honest gaps
are preferable to fabricated defaults).

``saleable_volume = volume × grade × recovery × payable`` decomposes
the upstream production drivers into the resource model's single
``saleable_volume`` driver.  The unit of saleable_volume inherits from
volume × grade (e.g. kt × g/t = kg of contained metal).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.constants import SCENARIOS
from contracts.evidence import require


def _positive_numeric(value: Any, field: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"MineYearOperation.{field} must be numeric, got {value!r}",
    )
    require(float(value) > 0, f"MineYearOperation.{field} must be positive, got {value!r}")
    return float(value)


def _ratio(value: Any, field: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"MineYearOperation.{field} must be numeric, got {value!r}",
    )
    require(
        0.0 < float(value) <= 1.0,
        f"MineYearOperation.{field} must be in (0, 1], got {value!r}",
    )
    return float(value)


@dataclass(frozen=True)
class MineYearOperation:
    """One mine's annual operating data — all seven fields required."""

    volume: float
    grade: float
    recovery: float
    payable: float
    product: str
    period: str
    scenario: str


def validate_mine_year_operation(op: Any) -> MineYearOperation:
    """Validate and return a MineYearOperation; fail-closed on any gap.

    Missing or invalid fields raise ForecastInputError — never silently
    defaulting to zero (ADR §1: honest gaps over fabricated defaults).
    """
    require(isinstance(op, dict), "MineYearOperation must be an object")
    for field in ("volume", "grade", "recovery", "payable",
                  "product", "period", "scenario"):
        require(field in op, f"MineYearOperation.{field} is required (gap, not default 0)")

    volume = _positive_numeric(op.get("volume"), "volume")
    grade = _positive_numeric(op.get("grade"), "grade")
    recovery = _ratio(op.get("recovery"), "recovery")
    payable = _ratio(op.get("payable"), "payable")
    product = op["product"]
    require(
        isinstance(product, str) and product.strip(),
        "MineYearOperation.product must be a non-empty string",
    )
    period = op["period"]
    require(
        isinstance(period, str) and period.strip(),
        "MineYearOperation.period must be a non-empty string",
    )
    scenario = op["scenario"]
    require(
        scenario in SCENARIOS,
        f"MineYearOperation.scenario must be one of {SCENARIOS}, got {scenario!r}",
    )
    return MineYearOperation(
        volume=volume,
        grade=grade,
        recovery=recovery,
        payable=payable,
        product=product,
        period=period,
        scenario=scenario,
    )


def derive_saleable_volume(op: MineYearOperation) -> float:
    """Decompose upstream production into saleable_volume.

    saleable_volume = volume × grade × recovery × payable
    The unit inherits from volume × grade (e.g. kt × g/t = kg metal).
    """
    return op.volume * op.grade * op.recovery * op.payable


def to_resource_model_drivers(
    op: MineYearOperation,
    realized_price: float,
) -> dict[str, float]:
    """Map a MineYearOperation to resource model drivers.

    Returns {saleable_volume, realized_price} — ready for
    calculate_model_path with model="resource".
    """
    require(
        isinstance(realized_price, (int, float))
        and not isinstance(realized_price, bool)
        and float(realized_price) > 0,
        f"realized_price must be positive numeric, got {realized_price!r}",
    )
    return {
        "saleable_volume": derive_saleable_volume(op),
        "realized_price": float(realized_price),
    }
