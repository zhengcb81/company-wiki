"""Extracted from revenue_core.py during the R9 split (behavior-locked by tests/test_golden_behavior_lock.py)."""

from __future__ import annotations

import math
from typing import Any

from collections import defaultdict

from contracts.constants import FORECAST_SCHEMA_VERSION
from contracts.evidence import (
    parse_iso_date,
    require,
)
from contracts.document import validate_historical_accuracy_records


CONFIDENCE_CALCULATION_VERSION = "stable-fsum/1"
# Only unmarked legacy confidence may differ by final floating-point bits.
# 64 binary64 ULPs cover the observed positive-weight reductions; never use
# revenue reconciliation tolerance for dimensionless confidence scores.
LEGACY_CONFIDENCE_MAX_ULPS = 64


def parameter_revenue_weights(
    data: dict[str, Any], result: dict[str, Any]
) -> dict[str, float]:
    contributions: dict[str, list[float]] = defaultdict(list)
    segment_inputs = {segment["name"]: segment for segment in data["segments"]}
    for segment_result in result["segments"]:
        segment = segment_inputs[segment_result["name"]]
        base_output = segment_result["scenarios"]["base"]
        terminal = abs(
            float(
                list(
                    base_output.get(
                        "effective_revenue", base_output["recognized_revenue"]
                    ).values()
                )[-1]
            )
        )
        refs: set[str] = set()
        for ids in segment["scenarios"]["base"]["driver_parameter_ids"].values():
            refs.update(ids)
        recognition = segment["recognition"]
        for container in ("carry_in_parameter_ids", "progress_parameter_ids"):
            values = recognition.get(container, {})
            if isinstance(values, dict):
                refs.update(values.get("base", []))
        if refs:
            for parameter_id in sorted(refs):
                contributions[parameter_id].append(terminal / len(refs))
    for adjustment, bridge in zip(
        data.get("forecast_adjustments", []),
        result["consolidated_forecast"]["base"]["adjustment_bridge"],
    ):
        refs = adjustment["scenario_parameter_ids"]["base"]
        impact = abs(float(list(bridge["annual_adjustment"].values())[-1]))
        if refs:
            for parameter_id in refs:
                contributions[parameter_id].append(impact / len(refs))
    # Constraint parameters drive effective revenue when constraints are present;
    # include their absolute revenue impact so confidence weights stay aligned
    # with the growth-driver helper.
    for entry in result.get("constraint_audit", []):
        impact = math.fsum(sorted(abs(change["adjustment"]) for change in entry.get("changes", [])))
        param_ids = entry.get("parameter_ids", [])
        if param_ids and impact > 0:
            for parameter_id in param_ids:
                contributions[parameter_id].append(impact / len(param_ids))
    # Stable key order and compensated sums preserve small shared exposures.
    return {key: math.fsum(sorted(contributions[key])) for key in sorted(contributions)}


def _history_score(
    data: dict[str, Any], historical_wape: float | None,
    historical_observations: int,
) -> tuple[float, int]:
    history_score = (
        0.0
        if historical_wape is None
        else 15
        if historical_wape <= 0.05
        else 12
        if historical_wape <= 0.10
        else 8
        if historical_wape <= 0.20
        else 4
        if historical_wape <= 0.30
        else 0
    )
    records = data.get("historical_accuracy_records", [])
    usable_origins = sum(record.get("record_schema_version") == "1.1" for record in records)
    discounted = history_score * min(
        1.0, historical_observations / 5, usable_origins / 3,
    )
    return discounted, usable_origins


def _append_history_limitations(
    limitations: list[str], data: dict[str, Any],
    observations: int, usable_origins: int,
) -> None:
    limitations.append("Confidence is an evidence/workflow score, not a calibrated forecast probability")
    if usable_origins:
        limitations.append(
            "Historical accuracy summary hashes validate integrity, not source provenance; "
            "archived snapshot and evaluation artifacts require audit before treating the score as verified historical skill"
        )
    if observations and (observations < 5 or usable_origins < 3):
        limitations.append("Historical accuracy has fewer than five observations or three forecast origins; score is discounted")
    records = data.get("historical_accuracy_records", [])
    if any(record.get("record_schema_version") == "1.0" for record in records):
        limitations.append("Legacy accuracy records lack identity/date/denominator and are excluded from scoring")


def calculate_confidence(
    data: dict[str, Any],
    validated: dict[str, Any],
    result: dict[str, Any],
    sensitivities: list[dict[str, Any]],
) -> dict[str, Any]:
    parameters = validated["parameter_index"]
    claims = validated["claim_index"]
    weights = parameter_revenue_weights(data, result)
    total_weight = math.fsum(weights.values())
    covered_weight = math.fsum(
        weight
        for parameter_id, weight in weights.items()
        if parameters[parameter_id].get("claim_ids")
    )
    driver_coverage = 0 if total_weight == 0 else covered_weight / total_weight
    quality_terms: list[float] = []
    freshness_terms: list[float] = []
    as_of = validated["as_of_date"]
    for parameter_id, weight in weights.items():
        claim_ids = parameters[parameter_id].get("claim_ids", [])
        if not claim_ids:
            continue
        parameter_claims = [claims[claim_id] for claim_id in claim_ids]
        quality = math.fsum(
            1.0
            if claim["support_type"] == "exact_value"
            else 0.8
            if claim["support_type"] == "policy_support"
            else 0.7
            for claim in parameter_claims
        ) / len(parameter_claims)
        ages = [
            (
                as_of
                - parse_iso_date(
                    validated["source_index"][claim["source_id"]]["published_date"],
                    "published_date",
                )
            ).days
            for claim in parameter_claims
        ]
        freshness = math.fsum(
            1.0 if age <= 180 else 0.8 if age <= 365 else 0.5 if age <= 730 else 0.2
            for age in ages
        ) / len(ages)
        quality_terms.append(weight * quality)
        freshness_terms.append(weight * freshness)
    quality_numerator = math.fsum(quality_terms)
    freshness_numerator = math.fsum(freshness_terms)
    source_quality = 0 if covered_weight == 0 else quality_numerator / covered_weight
    freshness = 0 if covered_weight == 0 else freshness_numerator / covered_weight

    segment_total = math.fsum(
        abs(
            float(
                list(
                    segment["scenarios"]["base"]
                    .get(
                        "effective_revenue",
                        segment["scenarios"]["base"]["recognized_revenue"],
                    )
                    .values()
                )[-1]
            )
        )
        for segment in result["segments"]
    )
    explicit_total = math.fsum(
        abs(
            float(
                list(
                    segment["scenarios"]["base"]
                    .get(
                        "effective_revenue",
                        segment["scenarios"]["base"]["recognized_revenue"],
                    )
                    .values()
                )[-1]
            )
        )
        for segment in result["segments"]
        if segment["scenarios"]["base"]["model"]
        not in {"direct_growth", "direct_revenue"}
    )
    explicit_model_share = 0 if segment_total == 0 else explicit_total / segment_total

    historical_wape, historical_observations = validate_historical_accuracy_records(
        data
    )
    history_score, usable_origins = _history_score(
        data, historical_wape, historical_observations,
    )

    sensitivity_coverage = 0.0
    concentration = None
    if sensitivities:
        impacts = [item["max_absolute_terminal_impact"] for item in sensitivities]
        total_impact = math.fsum(sorted(impacts))
        concentration = 0 if total_impact == 0 else max(impacts) / total_impact
        tested = {item["parameter_id"] for item in sensitivities}
        sensitivity_coverage = (
            0
            if total_weight == 0
            else math.fsum(
                weight
                for parameter_id, weight in weights.items()
                if parameter_id in tested
            )
            / total_weight
        )

    components = {
        "verified_claim_quality": 20 * source_quality,
        "verified_claim_coverage": 25 * driver_coverage,
        "source_freshness": 10 * freshness,
        "revenue_weighted_explicit_models": 15 * explicit_model_share,
        "historical_accuracy": history_score,
        "revenue_weighted_sensitivity_coverage": 15 * sensitivity_coverage,
    }
    score = math.fsum(components.values())
    rating = "high" if score >= 80 else "medium" if score >= 55 else "low"
    quality_gates = {
        "base_reconciliation": True,
        "recognition_contract": True,
        "scenario_consistency": True,
        "research_coverage": True,
    }
    if data.get("schema_version") in {"3.1", "3.2", FORECAST_SCHEMA_VERSION}:
        quality_gates["management_target_coverage"] = True
    if data.get("schema_version") == FORECAST_SCHEMA_VERSION:
        quality_gates["growth_driver_tree"] = True
    limitations = [
        item
        for condition, item in (
            (
                covered_weight == 0,
                "No verified claims for revenue-weighted base drivers",
            ),
            (historical_wape is None, "No immutable historical backtest record"),
            (not sensitivities, "No deterministic sensitivity tests"),
            (
                explicit_model_share < 1,
                "One or more segments use a direct fallback model",
            ),
            (
                validated["research_coverage"]["counts"]["data_gap"] > 0,
                f"Research coverage contains {validated['research_coverage']['counts']['data_gap']} material data gap(s)",
            ),
        )
        if condition
    ]
    _append_history_limitations(
        limitations, data, historical_observations, usable_origins,
    )
    target_coverage = validated.get("management_target_coverage")
    if target_coverage and target_coverage["counts"]["targets_unmodeled"] > 0:
        limitations.append(
            f"Management target coverage contains {target_coverage['counts']['targets_unmodeled']} unmodeled material/contextual target(s)"
        )
    limitations.extend(validated.get("growth_driver_tree", {}).get("limitations", []))
    growth_analysis = result.get("growth_driver_analysis")
    if growth_analysis and not math.isclose(
        float(growth_analysis.get("unattributed_company_adjustments", 0)),
        0.0,
        rel_tol=0,
        abs_tol=1e-9,
    ):
        limitations.append(
            "Company-level forecast adjustments are disclosed separately from operating growth-driver ranking"
        )
    output = {
        "calculation_version": CONFIDENCE_CALCULATION_VERSION,
        "score": score,
        "rating": rating,
        "components": components,
        "driver_evidence_coverage": driver_coverage,
        "sensitivity_concentration": concentration,
        "historical_accuracy": {
            "wape": historical_wape,
            "observations": historical_observations,
        },
        "quality_gates": quality_gates,
        "limitations": limitations,
    }
    if data.get("operating_research") is not None:
        from research.evidence_roles import analyze_operating_research
        output["research_adequacy"] = analyze_operating_research(data, validated)
    return output


def _numeric_match(expected: Any, observed: Any, *, legacy: bool) -> bool:
    if expected is None or observed is None:
        return expected is observed
    if type(expected) not in (int, float) or type(observed) not in (int, float):
        return False
    if not math.isfinite(expected) or not math.isfinite(observed):
        return False
    if expected == observed:
        return True
    return legacy and abs(expected - observed) <= LEGACY_CONFIDENCE_MAX_ULPS * max(
        math.ulp(float(expected)), math.ulp(float(observed))
    )


def validate_confidence_recomputation(
    expected: dict[str, Any], observed: dict[str, Any]
) -> None:
    """Exact stable revision; bounded legacy roundoff, never semantic slack.

    Old signed/hashed bytes stay untouched. Unknown or null revision markers
    are rejected. Counts/history and categorical values remain exact; only
    the named dimensionless reducers admit legacy ULP noise. New emissions
    always carry a revision marker and are checked bit-for-bit.
    """
    legacy = "calculation_version" not in observed
    require(
        legacy or observed.get("calculation_version") == CONFIDENCE_CALCULATION_VERSION,
        "unknown confidence calculation version",
    )
    components = observed.get("components")
    require(
        isinstance(components, dict) and components.keys() == expected["components"].keys()
        and all(_numeric_match(value, components[key], legacy=legacy)
                for key, value in expected["components"].items()),
        "confidence components recomputation mismatch",
    )
    for key in ("driver_evidence_coverage", "sensitivity_concentration", "score"):
        require(_numeric_match(expected.get(key), observed.get(key), legacy=legacy),
                f"confidence {key} recomputation mismatch")
    history = observed.get("historical_accuracy")
    require(
        isinstance(history, dict)
        and type(history.get("observations")) is int
        and (history.get("wape") is None or type(history.get("wape")) in (int, float))
        and expected.get("historical_accuracy") == history,
        "confidence historical_accuracy recomputation mismatch",
    )
    require(expected.get("research_adequacy") == observed.get("research_adequacy"),
            "confidence research adequacy recomputation mismatch")
    require(expected.get("rating") == observed.get("rating"),
            "confidence rating recomputation mismatch")
