"""ZR-607: internal-flow / consolidation accounting bridge.

Group companies often sell concentrate or metal to an internal smelter or
trading arm. Those internal sales must be traceable and eliminated from
group revenue — otherwise the same tonne gets counted twice.

  InternalFlow  — one internal sale, fully traceable:
      flow_id        — unique identifier for the flow
      source         — selling entity (mine, plant, trading arm)
      destination    — buying entity
      product        — what moved (concentrate, metal, doré...)
      volume         — quantity (finite, > 0)
      transfer_price — internal price (finite, > 0)
      period, scenario — which period/outlook the flow belongs to

  internal_revenue(flow)      = volume × transfer_price
  eliminate_internal_revenue(external_revenue, flows) → {gross,
      internal_total, net}: net = external_revenue + Σ internal flows
      reversed — internal sales are added into the external figure at
      their transfer value, then fully eliminated from group revenue
      (never double counted).

gross-vs-net bridge: gross = external + internal (as sold); net = external
only (internal eliminated). Composes with the ZR-606 commercial layer
(terms applied to internal flows) and the ZR-603 ownership semantics
(internal sales must be eliminated under both equity and consolidation
views).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.constants import SCENARIOS
from contracts.evidence import finite_number, require


@dataclass(frozen=True)
class InternalFlow:
    """One traceable internal sale."""

    flow_id: str
    source: str
    destination: str
    product: str
    volume: float
    transfer_price: float
    period: str
    scenario: str


def _non_empty_text(value: Any, field: str, flow_id: str) -> str:
    require(
        isinstance(value, str) and value.strip(),
        f"{field} must be a non-empty string for internal flow {flow_id}",
    )
    return value


def validate_internal_flow(flow: Any) -> InternalFlow:
    """Validate an internal flow; fail-closed on any gap (never default 0)."""
    require(isinstance(flow, dict), "InternalFlow must be an object")
    for field in ("flow_id", "source", "destination", "product", "volume",
                  "transfer_price", "period", "scenario"):
        require(
            field in flow,
            f"InternalFlow.{field} is required (gap, not default 0)",
        )
    flow_id = _non_empty_text(flow["flow_id"], "flow_id", "<unknown>")
    source = _non_empty_text(flow["source"], "source", flow_id)
    destination = _non_empty_text(flow["destination"], "destination", flow_id)
    product = _non_empty_text(flow["product"], "product", flow_id)
    volume = finite_number(flow["volume"], f"InternalFlow.{flow_id}.volume")
    require(volume > 0, f"InternalFlow.{flow_id}.volume must be positive")
    transfer_price = finite_number(
        flow["transfer_price"], f"InternalFlow.{flow_id}.transfer_price"
    )
    require(
        transfer_price > 0,
        f"InternalFlow.{flow_id}.transfer_price must be positive",
    )
    period = _non_empty_text(flow["period"], "period", flow_id)
    scenario = flow["scenario"]
    require(
        scenario in SCENARIOS,
        f"InternalFlow.{flow_id}.scenario must be one of {SCENARIOS}",
    )
    return InternalFlow(
        flow_id=flow_id,
        source=source,
        destination=destination,
        product=product,
        volume=volume,
        transfer_price=transfer_price,
        period=period,
        scenario=scenario,
    )


def internal_revenue(flow: InternalFlow) -> float:
    """Transfer value of one internal flow: volume × transfer_price."""
    return flow.volume * flow.transfer_price


def eliminate_internal_revenue(
    external_revenue: float,
    flows: list[InternalFlow],
    *,
    period: str | None = None,
    scenario: str | None = None,
) -> dict[str, float]:
    """Gross/net bridge: internal sales are eliminated from group revenue.

    Returns {gross, internal_total, net} where:
      gross         = external + Σ internal transfer values (as sold)
      internal_total = Σ internal transfer values
      net           = external (internal eliminated — never double counted)

    ``period``/``scenario`` filters restrict which flows are eliminated.
    """
    external = finite_number(external_revenue, "external_revenue")
    applicable = [
        flow for flow in flows
        if (period is None or flow.period == period)
        and (scenario is None or flow.scenario == scenario)
    ]
    internal_total = sum(internal_revenue(flow) for flow in applicable)
    gross = external + internal_total
    net = external
    return {"gross": gross, "internal_total": internal_total, "net": net}
