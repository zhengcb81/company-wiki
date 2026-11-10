"""R6-RF-INPUT I2: management-target construction with preserved semantics.

``build_management_target`` turns a management statement into a formal ledger
target plus its exact-value claim, preserving the verbatim wording, source
binding, period/quarter labels, range/qualitative tags, currency and
presentation basis. Quarterly, qualitative, range and undated targets are
retained by name; only an explicit, evidence-backed conversion may produce an
annual comparison value, and the original statement is never overwritten.
The engine re-validates every produced record; this builder fails fast on the
same contract so construction errors surface before validation.
"""

from __future__ import annotations

import math
from typing import Any

from contracts.constants import (
    MANAGEMENT_TARGET_COMPARISONS,
    MANAGEMENT_TARGET_CURRENCY_BASES,
    MANAGEMENT_TARGET_MEASUREMENT_BASES,
    MANAGEMENT_TARGET_PERIMETERS,
    MANAGEMENT_TARGET_PRESENTATION_BASES,
)
from contracts.evidence import (
    ForecastInputError,
    finite_number,
    require,
    text_sha256,
)
from forecast.calc import evaluate_derived_formula

_QUARTERS = {"Q1", "Q2", "Q3", "Q4", "H1", "H2"}
_COMMITMENT_STRENGTHS = {"guidance", "goal", "aspiration", "capacity_plan"}
# A capacity plan or aspiration is not a revenue promise: it may never force a
# scenario to attain it (the engine independently enforces the same rule).
_NON_BINDING_STRENGTHS = {"aspiration", "capacity_plan"}


def build_management_target(
    statement: str,
    *,
    target_id: str,
    metric_name: str,
    metric_definition: str,
    source_id: str,
    locator: str,
    excerpt: str,
    verified_by: str,
    verified_date: str,
    raw_unit: str,
    raw_currency: str,
    raw_scale: str,
    period_label: str,
    measurement_basis: str,
    measurement_periods: list[str] | None = None,
    target_period: str | None = None,
    target_quarter: str | None = None,
    commitment_strength: str = "guidance",
    materiality: str = "material",
    perimeter_status: str = "matched",
    comparison: str = "at_least",
    rationale: str,
    measurement_rationale: str,
    perimeter_notes: str,
    raw_value: float | None = None,
    raw_value_low: float | None = None,
    raw_value_high: float | None = None,
    raw_label: str | None = None,
    treatment: str | None = None,
    mapped_parameter_ids: list[str] | None = None,
    mapped_scenarios: list[str] | None = None,
    presentation_basis: str | None = None,
    currency_basis: str | None = None,
    conversion: dict[str, Any] | None = None,
    source_capture: dict[str, Any] | None = None,
    comparison_currency: str | None = None,
    comparison_scale: str | None = None,
    comparison_tolerance: float = 0.01,
) -> dict[str, Any]:
    """Return ``{"target", "claims", "notes"}`` for a formal ledger target."""
    for name, value in (
        ("statement", statement), ("target_id", target_id), ("metric_name", metric_name),
        ("metric_definition", metric_definition), ("source_id", source_id),
        ("locator", locator), ("excerpt", excerpt), ("verified_by", verified_by),
        ("verified_date", verified_date), ("raw_unit", raw_unit),
        ("raw_currency", raw_currency), ("raw_scale", raw_scale),
        ("period_label", period_label), ("rationale", rationale),
        ("measurement_rationale", measurement_rationale),
        ("perimeter_notes", perimeter_notes),
    ):
        require(
            isinstance(value, str) and value.strip(),
            f"{name} is required to build management target {target_id}",
        )
    require(
        10 <= len(excerpt.strip()) <= 500,
        f"excerpt for {target_id} must contain 10-500 characters",
    )
    require(
        measurement_basis in MANAGEMENT_TARGET_MEASUREMENT_BASES,
        f"invalid measurement basis for {target_id}: {measurement_basis}",
    )
    require(
        commitment_strength in _COMMITMENT_STRENGTHS,
        f"invalid commitment strength for {target_id}: {commitment_strength}",
    )
    require(
        perimeter_status in MANAGEMENT_TARGET_PERIMETERS,
        f"invalid perimeter status for {target_id}: {perimeter_status}",
    )
    require(comparison in MANAGEMENT_TARGET_COMPARISONS,
            f"invalid comparison for {target_id}: {comparison}")
    require(
        target_quarter in (None, *_QUARTERS),
        f"invalid target quarter for {target_id}: {target_quarter}",
    )
    require(
        presentation_basis in (None, *sorted(MANAGEMENT_TARGET_PRESENTATION_BASES)),
        f"invalid presentation basis for {target_id}: {presentation_basis}",
    )
    require(
        currency_basis in (None, *sorted(MANAGEMENT_TARGET_CURRENCY_BASES)),
        f"invalid currency basis for {target_id}: {currency_basis}",
    )
    require(materiality in {"material", "contextual"},
            f"invalid materiality for {target_id}: {materiality}")

    if raw_label is not None:
        raw_value_kind = "qualitative_range"
        require(raw_value is None and raw_value_low is None and raw_value_high is None,
                f"qualitative target {target_id} cannot carry numeric values")
    elif raw_value_low is not None or raw_value_high is not None:
        raw_value_kind = "numeric_range"
        require(raw_value_low is not None and raw_value_high is not None,
                f"numeric range target {target_id} requires both endpoints")
        low_number = finite_number(raw_value_low, f"{target_id}.raw_value_low")
        high_number = finite_number(raw_value_high, f"{target_id}.raw_value_high")
        require(low_number >= 0 and low_number <= high_number,
                f"invalid numeric range for {target_id}")
        require(raw_value is None,
                f"numeric range target {target_id} cannot carry a single point")
    else:
        raw_value_kind = "numeric"
        require(raw_value is not None, f"numeric target {target_id} requires raw_value")
        require(finite_number(raw_value, f"{target_id}.raw_value") >= 0,
                f"management target {target_id} cannot be negative")

    if measurement_basis == "quarterly_period":
        require(target_quarter is not None,
                f"quarterly target {target_id} requires target_quarter")

    resolved_treatment = treatment
    reject_reason = None
    converted = None
    if measurement_basis in {"quarterly_period", "run_rate_at_period_end"} or conversion is not None:
        converted = _evaluate_conversion(target_id, raw_value, conversion)
        if converted is None:
            reject_reason = "conversion_requires_evidence_backed_inputs"
            if resolved_treatment in {
                "modeled_scenario", "scenario_boundary", "independent_benchmark",
            }:
                raise ForecastInputError(
                    f"{target_id}: {measurement_basis} target cannot use treatment "
                    f"{resolved_treatment} without an evidence-backed annual conversion"
                )
            resolved_treatment = "unmodeled_data_gap"

    if commitment_strength in _NON_BINDING_STRENGTHS and resolved_treatment in {
        "modeled_scenario", "scenario_boundary",
    }:
        raise ForecastInputError(
            f"{commitment_strength} target {target_id} cannot be forced into a "
            f"numerical attainment treatment: {resolved_treatment}"
        )

    unmodeled_reason = None
    comparable = bool(converted) and resolved_treatment in {
        "modeled_scenario", "scenario_boundary", "independent_benchmark",
    } and perimeter_status in {"matched", "reconciled"} and raw_value_kind == "numeric"
    reason_code = None
    if resolved_treatment is None:
        resolved_treatment = "unmodeled_data_gap"
    if resolved_treatment == "unmodeled_data_gap":
        if measurement_basis == "quarterly_period":
            reason_code = "quarterly_basis_without_supported_annual_conversion"
            unmodeled_reason = (
                f"Preserved verbatim: {target_quarter} disclosure on a "
                f"{currency_basis or 'reported'} basis has no evidence-backed "
                "annual conversion; no pseudo-annualization was applied."
            )
        elif measurement_basis == "ambiguous":
            reason_code = "ambiguous_measurement_basis"
            unmodeled_reason = "No determinate measurement period; preserved verbatim."
        elif raw_value_kind in {"qualitative_range", "numeric_range"}:
            reason_code = f"{raw_value_kind}_has_no_single_point_value"
            unmodeled_reason = (
                "Preserved verbatim label/range; no midpoint or point was invented."
            )
        elif measurement_basis == "run_rate_at_period_end":
            reason_code = "run_rate_without_supported_annual_conversion"
            unmodeled_reason = (
                "Run-rate disclosure preserved; no evidence-backed annual "
                "recognized revenue conversion available."
            )

    target: dict[str, Any] = {
        "target_id": target_id,
        "statement": statement,
        "metric_name": metric_name,
        "metric_definition": metric_definition,
        "target_period": target_period or period_label,
        "period_label": period_label,
        "raw_unit": raw_unit,
        "raw_currency": raw_currency,
        "raw_scale": raw_scale,
        "raw_value_kind": raw_value_kind,
        "measurement_basis": measurement_basis,
        "measurement_periods": list(measurement_periods or []),
        "measurement_rationale": measurement_rationale,
        "materiality": materiality,
        "commitment_strength": commitment_strength,
        "scope": {"type": "company", "name": "company"},
        "perimeter_status": perimeter_status,
        "perimeter_notes": perimeter_notes,
        "comparison": comparison,
        "treatment": resolved_treatment,
        "rationale": rationale,
        "mapped_parameter_ids": list(mapped_parameter_ids or []),
        "mapped_scenarios": list(mapped_scenarios or []),
        "comparison_tolerance": comparison_tolerance,
    }
    if target_quarter is not None:
        target["target_quarter"] = target_quarter
    if presentation_basis is not None:
        target["presentation_basis"] = presentation_basis
    if currency_basis is not None:
        target["currency_basis"] = currency_basis
    if raw_label is not None:
        target["raw_label"] = raw_label
    if raw_value_kind == "numeric":
        target["raw_target_value"] = raw_value
    if raw_value_kind == "numeric_range":
        target["raw_target_value_low"] = raw_value_low
        target["raw_target_value_high"] = raw_value_high
    if unmodeled_reason is not None:
        target["unmodeled_reason"] = unmodeled_reason
    if converted is not None:
        target.update({
            "comparison_basis": converted["comparison_basis"],
            "normalization_formula": converted["formula"],
            "normalization_parameter_ids": list(converted["parameter_ids"]),
            "normalization_rationale": converted["rationale"],
            "comparison_value": converted["comparison_value"],
        })
        if comparison_currency is not None:
            target["comparison_currency"] = comparison_currency
        if comparison_scale is not None:
            target["comparison_scale"] = comparison_scale
        comparable = True

    claim_id = f"claim_{target_id}"
    target["claim_ids"] = [claim_id]
    claim: dict[str, Any] = {
        "claim_id": claim_id,
        "source_id": source_id,
        "target_type": "management_target",
        "target_id": target_id,
        "support_type": "exact_value",
        "locator": locator,
        "excerpt": excerpt,
        "excerpt_sha256": text_sha256(excerpt),
        "verification_status": "opened_and_checked",
        "verified_by": verified_by,
        "verified_date": verified_date,
    }
    if source_capture is not None:
        require(isinstance(source_capture, dict), "source_capture must be an object")
        claim["content_sha256"] = source_capture["snapshot_sha256"]
        claim["capture_receipt_sha256"] = source_capture["receipt_sha256"]
    if raw_value_kind == "numeric":
        claim.update({
            "extracted_value": raw_value,
            "unit": raw_unit,
            "period": target["target_period"],
        })

    notes: dict[str, Any] = {
        "comparable": comparable,
        "raw_value_kind": raw_value_kind,
    }
    if reason_code is not None:
        notes["reason_code"] = reason_code
    if reject_reason is not None:
        notes["reject_reason"] = reject_reason
    return {"target": target, "claims": [claim], "notes": notes}


def _evaluate_conversion(
    target_id: str, raw_value: float | None, conversion: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Evaluate an explicit conversion; a literal formula with no evidence-backed
    inputs is rejected (the x0*4 pseudo-annualization pattern)."""
    if not isinstance(conversion, dict):
        return None
    parameter_ids = conversion.get("parameter_ids")
    formula = conversion.get("formula")
    if (
        conversion.get("comparison_basis") != "annual_recognized_revenue"
        or not isinstance(parameter_ids, list)
        or not parameter_ids
        or not isinstance(formula, str)
        or not formula.strip()
    ):
        return None
    values = conversion.get("parameter_values")
    require(
        isinstance(values, list) and len(values) == len(parameter_ids),
        f"conversion for {target_id} requires parameter_values aligned with parameter_ids",
    )
    inputs = [finite_number(v, f"{target_id}.conversion value") for v in values]
    comparison_value = evaluate_derived_formula(
        formula, [finite_number(raw_value, f"{target_id}.raw_value")] + inputs
    )
    require(
        math.isfinite(comparison_value) and comparison_value >= 0,
        f"conversion for {target_id} produced an invalid comparison value",
    )
    return {
        "comparison_basis": conversion["comparison_basis"],
        "formula": formula,
        "parameter_ids": list(parameter_ids),
        "rationale": conversion.get("rationale", ""),
        "comparison_value": comparison_value,
    }
