"""ZR-608: asset→segment→group reconciliation with honest fallback.

Per-mine contributions are model estimates (ADR §1); they must reconcile
to segment / group disclosed revenue within tolerance to be labelled
``modeled``.  When a layer does not close, the system falls back to a
side-by-side segment listing with an explicit gap — it never fabricates
the difference and never outputs fake revenue.

  reconcile_layer(asset_total, reference_total, tolerance) — within
      |diff| ≤ max(1.0, |reference|) × tolerance → "reconciled_modeled",
      else → "gap" (fallback).  Values must be finite (finite_number) —
      NaN/inf can never silently "close" a layer.

  fallback_segment_listing(segment_revenues, group_reported) — side-
      by-side listing {segment: revenue} plus {gap, group_reported};
      unclosed difference is reported as gap, never as revenue.

  gap_report(asset_revenues, reference_total, tolerance) — per-asset
      contribution status: reconciled vs gap; assets without a derivable
      contribution (missing/fabricated) are gaps, never revenue
      (no volume×price pseudo revenue).
"""

from __future__ import annotations

from typing import Any, Mapping

from contracts.evidence import finite_number, require


def reconcile_layer(
    asset_total: float,
    reference_total: float,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Reconcile a modeled asset total to a disclosed reference.

    Within |diff| ≤ max(1.0, |reference|) × tolerance → reconciled_modeled;
    otherwise → gap (honest fallback, never fabricated difference).
    """
    asset = finite_number(asset_total, "asset_total")
    reference = finite_number(reference_total, "reference_total")
    tolerance_value = finite_number(tolerance, "tolerance")
    require(tolerance_value >= 0, "tolerance cannot be negative")
    allowed = max(1.0, abs(reference)) * tolerance_value
    difference = asset - reference
    status = "reconciled_modeled" if abs(difference) <= allowed else "gap"
    return {
        "status": status,
        "asset_total": asset,
        "reference_total": reference,
        "difference": difference,
        "tolerance": allowed,
    }


def fallback_segment_listing(
    segment_revenues: Mapping[str, float],
    group_reported: float,
) -> dict[str, Any]:
    """Side-by-side segment listing with an explicit gap when unclosed.

    The unclosed difference is reported as ``gap`` — never as revenue.
    """
    require(isinstance(segment_revenues, Mapping), "segment_revenues must be an object")
    segments: dict[str, float] = {}
    total = 0.0
    for name, value in segment_revenues.items():
        require(isinstance(name, str) and name.strip(), "segment name must be non-empty")
        revenue = finite_number(value, f"segment {name} revenue")
        segments[name] = revenue
        total += revenue
    reference = finite_number(group_reported, "group_reported")
    return {
        "segments": segments,
        "segment_total": total,
        "group_reported": reference,
        "gap": reference - total,
        "closed": abs(reference - total) <= max(1.0, abs(reference)) * 1e-6,
    }


def gap_report(
    asset_revenues: Mapping[str, float],
    reference_total: float,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Per-asset contribution status: reconciled vs gap.

    Assets without a derivable contribution (missing, NaN/inf, or
    fabricated volume×price numbers) are gaps — never revenue.
    """
    require(isinstance(asset_revenues, Mapping), "asset_revenues must be an object")
    reference = finite_number(reference_total, "reference_total")
    contributions: dict[str, float] = {}
    for name, value in asset_revenues.items():
        require(isinstance(name, str) and name.strip(), "asset name must be non-empty")
        contributions[name] = finite_number(value, f"asset {name} contribution")
    total = sum(contributions.values())
    verdict = reconcile_layer(total, reference, tolerance)
    return {
        "contributions": contributions,
        "total": total,
        "reference_total": reference,
        "status": verdict["status"],
        "difference": verdict["difference"],
    }
