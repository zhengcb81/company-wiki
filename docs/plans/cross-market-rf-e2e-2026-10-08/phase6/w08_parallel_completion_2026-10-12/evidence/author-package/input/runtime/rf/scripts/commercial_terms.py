"""ZR-606: commercial terms layer for mining revenue models.

Each commercial variable (price / payability / TC-RC / premium /
byproduct credit / FX / royalty) carries full provenance:

  value      — finite numeric value (never inf/NaN — ZR-605 REV-001 fix)
  source     — where the value came from (filing, index, contract...)
  assumption — the modeling assumption behind the value
  period     — which period the value applies to

Net revenue derivation (no double counting):

  gross            = saleable_volume × price
  deductions       = TC + RC (per unit) + royalty_rate × gross
  additions        = premium (per unit) + byproduct_credit (independent
                     addition — byproduct revenue is NEVER included in
                     the primary product volume × price path)
  net              = (gross − TC − RC + premium + byproduct_credit −
                     royalty_rate × gross) × FX_rate

The calculation is a pure function of (saleable_volume, terms), so
sensitivity recomputation is deterministic and idempotent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.evidence import finite_number, require


@dataclass(frozen=True)
class CommercialTerm:
    """One commercial variable with full provenance."""

    value: float
    source: str
    assumption: str
    period: str


@dataclass(frozen=True)
class CommercialTerms:
    """The commercial layer for one product path.

    price is required; TC/RC/premium/byproduct_credit/FX_rate/royalty_rate
    are optional (None is legal — absent means no such term).
    """

    price: CommercialTerm
    payability: CommercialTerm | None = None
    tc: CommercialTerm | None = None
    rc: CommercialTerm | None = None
    premium: CommercialTerm | None = None
    byproduct_credit: CommercialTerm | None = None
    fx_rate: CommercialTerm | None = None
    royalty_rate: CommercialTerm | None = None


def _validate_term(term: Any, name: str) -> CommercialTerm:
    require(
        isinstance(term, dict),
        f"commercial term {name} must be an object with value/source/assumption/period",
    )
    for field in ("value", "source", "assumption", "period"):
        require(field in term, f"commercial term {name}.{field} is required")
    value = finite_number(term["value"], f"commercial term {name}.value")
    for field in ("source", "assumption", "period"):
        require(
            isinstance(term[field], str) and term[field].strip(),
            f"commercial term {name}.{field} must be a non-empty string",
        )
    return CommercialTerm(
        value=value,
        source=term["source"],
        assumption=term["assumption"],
        period=term["period"],
    )


def validate_commercial_terms(terms: Any) -> CommercialTerms:
    """Validate a commercial-terms object; fail-closed on gaps.

    price is required; every other term is validated only when present.
    """
    require(
        isinstance(terms, dict),
        "CommercialTerms must be an object",
    )
    require("price" in terms, "commercial terms price is required (gap)")
    price = _validate_term(terms["price"], "price")
    optional = {}
    for name in ("payability", "tc", "rc", "premium", "byproduct_credit",
                 "fx_rate", "royalty_rate"):
        term = terms.get(name)
        if term is not None:
            optional[name] = _validate_term(term, name)
    return CommercialTerms(price=price, **optional)


def calculate_net_revenue(
    saleable_volume: float,
    terms: CommercialTerms,
) -> dict[str, float]:
    """Derive net revenue from saleable volume and commercial terms.

    Pure function of (saleable_volume, terms) — deterministic, idempotent,
    and sensitivity-recomputable (change any term value, recompute).

    Returns {gross, deductions, additions, net} in the same currency as
    price (FX applied when fx_rate present).
    """
    volume = finite_number(saleable_volume, "saleable_volume")
    price = terms.price.value
    gross = volume * price

    tc = terms.tc.value if terms.tc is not None else 0.0
    rc = terms.rc.value if terms.rc is not None else 0.0
    premium = terms.premium.value if terms.premium is not None else 0.0
    byproduct = terms.byproduct_credit.value if terms.byproduct_credit is not None else 0.0
    royalty_rate = terms.royalty_rate.value if terms.royalty_rate is not None else 0.0

    deductions = tc + rc + royalty_rate * gross
    additions = premium + byproduct
    net_before_fx = gross - deductions + additions

    fx = terms.fx_rate.value if terms.fx_rate is not None else 1.0
    net = net_before_fx * fx

    return {
        "gross": gross,
        "deductions": deductions,
        "additions": additions,
        "net": net,
    }
