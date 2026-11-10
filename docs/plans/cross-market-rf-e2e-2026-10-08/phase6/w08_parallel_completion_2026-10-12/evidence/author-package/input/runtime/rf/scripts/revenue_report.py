"""Output validation and Markdown rendering for revenue-only forecasts."""

from __future__ import annotations

import copy
import math
from typing import Any

from revenue_core import (
    ForecastInputError,
    RESEARCH_COVERAGE_STATUSES,
    RESEARCH_DIMENSIONS,
    SCENARIOS,
    ENGINE_VERSION,
    SUPPORTED_FORECAST_SCHEMA_VERSIONS,
    MANAGEMENT_COMMUNICATION_CATEGORIES,
    MANAGEMENT_COMMUNICATION_STATUSES,
    MANAGEMENT_TARGET_MEASUREMENT_BASES,
    MANAGEMENT_TARGET_TREATMENTS,
    calculate_model_path,
    calculate_cagr,
    calculate_confidence,
    calculate_growth_driver_analysis,
    calculate_sensitivities,
    build_workflow_compliance_receipt,
    canonical_sha256,
    parse_iso_date,
    period_year,
    require,
    validate_growth_driver_tree,
    validate_source_capture,
)
from analysis.confidence import validate_confidence_recomputation
from contracts.annual_consumption import validate_annual_consumption
from forecast.calc import opening_base_bridge, scenario_forecast_parameter_ids
from research.target_measurement import is_typed_target, compare_target_measurement
from research.targets import validate_management_target_coverage, add_management_target_analysis
from revenue_constraints import RevenueConstraintError, apply_revenue_constraints
from revenue_publication import (
    VerificationContext,
    expected_publication_gates,
    validate_publication_receipt,
)
from schema_compatibility import (
    BOUND_INPUT_SCHEMA_VERSIONS, require_validating_engine, requires_bound_input_schema,
)
from trust_anchor import verify_input_binding


PROHIBITED_OUTPUT_KEYS = {
    "stock_price",
    "share_price",
    "target_price",
    "valuation",
    "pe",
    "ps",
    "dcf",
    "profit",
    "profit_margin",
    "gross_margin",
    "net_margin",
    "cash_flow",
    "free_cash_flow",
    "investment_rating",
    "investment_recommendation",
    "expected_return",
    "position_size",
    "portfolio_weight",
}


def _recompute_consolidated_paths(
    consolidated: Any, years: Any, segment_index: Any, base: Any,
    effective_path: Any,
) -> None:
    """Recompute consolidated annual/CAGR/bridge paths per scenario (FC-1204-b)."""
    for scenario in SCENARIOS:
        forecast = consolidated[scenario]
        annual = forecast["annual_revenue"]
        require(list(annual) == years, f"annual revenue years mismatch in {scenario}")
        values = [float(annual[year]) for year in years]
        require(
            math.isclose(
                float(forecast["terminal_revenue"]),
                values[-1],
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            f"terminal revenue mismatch in {scenario}",
        )
        expected_cagr = calculate_cagr(base, values[-1], len(years))
        require(
            (expected_cagr is None and forecast["cagr"] is None)
            or math.isclose(
                float(forecast["cagr"]),
                float(expected_cagr),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            f"CAGR mismatch in {scenario}",
        )
        for year in years:
            previous = (
                base
                if year == years[0]
                else float(annual[years[years.index(year) - 1]])
            )
            expected_growth = (
                None if previous == 0 else float(annual[year]) / previous - 1
            )
            observed_growth = forecast["annual_growth"][year]
            require(
                (expected_growth is None and observed_growth is None)
                or math.isclose(
                    float(observed_growth),
                    float(expected_growth),
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                ),
                f"annual growth mismatch in {scenario}/{year}",
            )
            segment_sum = sum(
                float(segment["annual_revenue"][year])
                for segment in forecast["segment_bridge"]
            )
            adjustment_sum = sum(
                float(adjustment["annual_adjustment"][year])
                for adjustment in forecast["adjustment_bridge"]
            )
            require(
                math.isclose(
                    segment_sum + adjustment_sum,
                    float(annual[year]),
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                ),
                f"company bridge mismatch in {scenario}/{year}",
            )
            for bridge in forecast["segment_bridge"]:
                require(
                    math.isclose(
                        float(bridge["annual_revenue"][year]),
                        float(
                            effective_path(segment_index[bridge["name"]], scenario)[
                                year
                            ]
                        ),
                        rel_tol=1e-9,
                        abs_tol=1e-9,
                    ),
                    f"segment bridge cross-check mismatch in {scenario}/{bridge['name']}/{year}",
                )
        contribution = forecast["incremental_contribution"]
        require(
            math.isclose(
                float(contribution["total"]),
                float(forecast["incremental_revenue"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            f"incremental contribution mismatch in {scenario}",
        )


def _validate_segment_opening_bases(
    result: Any, parameter_index: Any, years: Any, data: Any = None  # noqa: ARG001
) -> None:
    """Bind opening identity, signed adjustments and tolerance to authored input.

    The strong path also recomputes the opening residual and each increment
    contribution. This residual explains the reported opening denominator; it
    is never an annual revenue adjustment. Legacy reads retain their old gate.
    """
    segments = result.get("segments")
    require(isinstance(segments, list) and segments, "segments must be a non-empty list")
    base_year = result.get("base_year")
    for position, segment in enumerate(segments):
        require(
            isinstance(segment, dict), f"segments[{position}] must be an object"
        )
        require(
            "base_revenue" in segment,
            f"segments[{position}].base_revenue is required",
        )
        observed = float(segment["base_revenue"])
        parameter_id = segment.get("base_revenue_parameter_id")
        if data is not None:
            authored = next((s for s in data["segments"] if s["name"] == segment.get("name")), None)
            require(authored is not None and parameter_id == authored["base_revenue_parameter_id"],
                    f"segment base revenue identity mismatch: {segment.get('name')}")
        if parameter_id is None:
            continue
        name = segment.get("name")
        parameter = parameter_index.get(parameter_id)
        require(
            isinstance(parameter, dict),
            "segment base revenue mismatch: "
            f"{name} references unknown base_revenue_parameter_id {parameter_id!r}",
        )
        require(
            parameter.get("dimension") == "revenue",
            "segment base revenue mismatch: "
            f"{parameter_id} must use the revenue dimension",
        )
        require(
            period_year(parameter.get("period"), f"{parameter_id}.period") == base_year,
            "segment base revenue mismatch: "
            f"{parameter_id} must be a FY{base_year} parameter",
        )
        require(
            math.isclose(
                float(parameter["value"]),
                observed,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            "segment base revenue mismatch: "
            f"{name} opening base {observed} does not match {parameter_id} "
            f"({parameter['value']})",
        )
    reported_base = float(result["base_revenue"])
    opening_total = sum(
        float(segment["base_revenue"])
        for segment in segments
        if isinstance(segment.get("base_revenue"), (int, float))
        and not isinstance(segment.get("base_revenue"), bool)
    )
    if data is not None:
        expected = opening_base_bridge(data, parameter_index)
        needed = (data.get("base_adjustment_parameter_ids")
                  or expected["reconciliation_tolerance"] != 1e-6
                  or expected["reconciliation_difference"] != 0)
        if needed or "opening_base_bridge" in result:
            require(result.get("opening_base_bridge") == expected,
                    "opening base bridge recomputation mismatch")
        opening_total += expected["base_adjustment_total"]
        tolerance = expected["reconciliation_tolerance"]
        for scenario in SCENARIOS:
            forecast = result["consolidated_forecast"][scenario]
            contribution = forecast["incremental_contribution"]
            expected_segments = [{"name": s["name"], "terminal_incremental_revenue":
                float(list(s["scenarios"][scenario].get("effective_revenue",
                           s["scenarios"][scenario]["recognized_revenue"]).values())[-1])
                - float(s["base_revenue"])} for s in segments]
            expected_adjustment = (float(list(forecast["adjustment_total"].values())[-1])
                                   - expected["base_adjustment_total"]
                                   + expected["reconciliation_difference"])
            require(contribution["segments"] == expected_segments
                    and math.isclose(float(contribution["adjustments"]), expected_adjustment,
                                     rel_tol=1e-9, abs_tol=1e-9)
                    and math.isclose(float(contribution["total"]),
                        sum(s["terminal_incremental_revenue"] for s in expected_segments) + expected_adjustment,
                        rel_tol=1e-9, abs_tol=1e-9),
                    f"opening base bridge incremental contribution mismatch: {scenario}")
    else:
        tolerance = float(result.get("reconciliation_tolerance", 1e-6))
    allowed = max(1.0, abs(reported_base)) * tolerance
    require(
        abs(opening_total - reported_base) <= allowed,
        "segment opening base does not reconcile: "
        f"segments={opening_total}, reported={reported_base}",
    )


def _validate_confidence_block(confidence: Any) -> None:
    """Recompute confidence score/rating/gates (FC-1204-b)."""
    require(
        math.isclose(
            sum(float(value) for value in confidence["components"].values()),
            float(confidence["score"]),
            rel_tol=1e-9,
            abs_tol=1e-9,
        ),
        "confidence component total mismatch",
    )
    expected_rating = (
        "high"
        if confidence["score"] >= 80
        else "medium"
        if confidence["score"] >= 55
        else "low"
    )
    require(confidence["rating"] == expected_rating, "confidence rating mismatch")
    require(
        all(confidence.get("quality_gates", {}).values()),
        "confidence quality gate failed",
    )


def _validate_theme_analysis(
    theme: Any, segment_index: Any, parameter_index: Any, base: Any,
    effective_path: Any,
) -> None:
    """Recompute theme terminal/counterfactual/increment/elasticity (FC-1204-b)."""
    for scenario in SCENARIOS:
        values = theme["scenarios"][scenario]
        expected_theme_terminal = sum(
            float(list(effective_path(segment_index[name], scenario).values())[-1])
            for name in theme["segment_names"]
        )
        require(
            math.isclose(
                expected_theme_terminal,
                float(values["theme_terminal_revenue"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            f"theme terminal mismatch: {scenario}",
        )
        counterfactual_parameter = parameter_index[
            values["counterfactual_parameter_id"]
        ]
        require(
            math.isclose(
                float(counterfactual_parameter["value"]),
                float(values["counterfactual_terminal_revenue"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            f"theme counterfactual mismatch: {scenario}",
        )
        expected_increment = float(values["theme_terminal_revenue"]) - float(
            values["counterfactual_terminal_revenue"]
        )
        require(
            math.isclose(
                expected_increment,
                float(values["theme_incremental_revenue"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            f"theme increment mismatch: {scenario}",
        )
        expected_elasticity = None if base == 0 else expected_increment / base
        require(
            (
                expected_elasticity is None
                and values["theme_elasticity_to_company_base"] is None
            )
            or math.isclose(
                float(expected_elasticity),
                float(values["theme_elasticity_to_company_base"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            f"theme elasticity mismatch: {scenario}",
        )


def _validate_receipt_blocks(result: Any, hash_payload: Any) -> None:
    """Recompute workflow/publication receipt + result hash (FC-1204-b)."""
    if requires_bound_input_schema(result["schema_version"]):
        expected_receipt = build_workflow_compliance_receipt(
            result["input_sha256"],
            result["sources"],
            result["evidence_claims"],
            result["parameter_trace"],
            result.get("data_gaps", []),
        )
        require(
            result["workflow_compliance_receipt"] == expected_receipt,
            "workflow compliance receipt mismatch",
        )
        if "publication_receipt" in result:
            validate_publication_receipt(result)
    if "result_sha256" in result:
        require(
            result["result_sha256"] == canonical_sha256(hash_payload),
            "forecast result hash mismatch",
        )


def _walk_keys(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            # A prohibited key with a structured value (dict / list / number)
            # is a formal investment conclusion and must be rejected.  A
            # prohibited key whose value is a plain string is legitimate
            # evidence vocabulary (e.g. a source excerpt containing "profit").
            if normalized in PROHIBITED_OUTPUT_KEYS and not isinstance(child, str):
                raise ForecastInputError(
                    f"prohibited non-revenue output key: {path}.{key}"
                )
            _walk_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_keys(child, f"{path}[{index}]")


def _validate_forecast_output(
    result: dict[str, Any], data: dict[str, Any] | None
) -> None:
    if isinstance(result.get("input_document"), dict):
        # R1.1 (N-01): an embedded input document must hash to the claimed
        # anchor — it can never be silently swapped for a different input.
        verify_input_binding(result)
    if data is not None:
        # R6.2 (mutation patrol): parameter_trace order is semantic (consumers
        # index it); it must match the validated input's parameters exactly.
        require(
            result.get("parameter_trace") == data.get("parameters"),
            "parameter_trace must match the validated input parameters",
        )
    for key in result:
        if key == "input_document":
            continue
        require(
            str(key).strip().lower() not in PROHIBITED_OUTPUT_KEYS,
            f"prohibited non-revenue output key: root.{key}",
        )
    for key, value in result.items():
        if key not in ("result_sha256", "publication_receipt", "input_document"):
            _walk_keys(value, f"root.{key}")
    required = (
        "company_name",
        "as_of_date",
        "currency",
        "unit",
        "fiscal_year_end",
        "base_year",
        "forecast_years",
        "historical_revenue",
        "base_revenue",
        "segments",
        "consolidated_forecast",
        "confidence",
        "research_coverage",
        "parameter_trace",
        "sources",
        "evidence_claims",
        "schema_version",
        "engine_version",
        "input_sha256",
    )
    for key in required:
        require(key in result, f"forecast output missing field: {key}")
    require(
        result["schema_version"] in SUPPORTED_FORECAST_SCHEMA_VERSIONS,
        "forecast output schema_version mismatch",
    )
    # R6.2 (mutation patrol): the historical sequence is ordered and semantic —
    # a shuffled year list must be rejected, matching the input-side contract.
    history = result["historical_revenue"]
    require(isinstance(history, list), "historical_revenue must be a list")
    history_years = [
        record.get("year") for record in history if isinstance(record, dict)
    ]
    require(
        history_years == sorted(history_years),
        "historical_revenue must be ordered by year",
    )
    require_validating_engine(
        result["schema_version"], result["engine_version"], "output"
    )
    if data is not None and requires_bound_input_schema(result["schema_version"]):
        # W05 (mutation patrol): against a frozen bound input the identity and
        # denotation fields cannot drift — a rehashed output with a rewritten
        # currency, unit, fiscal calendar or period label still fails here.
        for _field in (
            "company_name",
            "as_of_date",
            "currency",
            "unit",
            "fiscal_year_end",
            "base_year",
            "forecast_years",
            "schema_version",
        ):
            require(
                result.get(_field) == data.get(_field),
                f"forecast output {_field} does not match the bound input",
            )
    if requires_bound_input_schema(result["schema_version"]):
        require(
            "management_target_coverage" in result,
            "forecast output missing field: management_target_coverage",
        )
        require(
            "growth_driver_analysis" in result,
            "forecast output missing field: growth_driver_analysis",
        )
        require(
            "workflow_compliance_receipt" in result,
            "forecast output missing field: workflow_compliance_receipt",
        )
        # R6.2 (mutation patrol): every engine-produced key is part of the
        # artifact contract — deleting any of them must be rejected.
        for _engine_key in (
            "data_gaps",
            "disconfirming_indicators",
            "forecast_version",
            "historical_accuracy_records",
            "probability_weighted_forecast",
            "scenario_probabilities",
            "sensitivities",
            "theme_analysis",
        ):
            require(
                _engine_key in result,
                f"forecast output missing field: {_engine_key}",
            )
    elif result["schema_version"] == "3.4":
        require(
            "management_target_coverage" in result,
            "forecast output missing field: management_target_coverage",
        )
        require(
            "growth_driver_analysis" in result,
            "forecast output missing field: growth_driver_analysis",
        )
        require(
            "workflow_compliance_receipt" in result,
            "forecast output missing field: workflow_compliance_receipt",
        )
    elif result["schema_version"] == "3.5":
        require(
            "management_target_coverage" in result,
            "forecast output missing field: management_target_coverage",
        )
        require(
            "growth_driver_analysis" in result,
            "forecast output missing field: growth_driver_analysis",
        )
        require(
            "workflow_compliance_receipt" in result,
            "forecast output missing field: workflow_compliance_receipt",
        )
    elif result["schema_version"] == "3.3":
        require(
            "management_target_coverage" in result,
            "forecast output missing field: management_target_coverage",
        )
        require(
            "growth_driver_analysis" in result,
            "forecast output missing field: growth_driver_analysis",
        )
    elif result["schema_version"] == "3.2":
        require(
            "management_target_coverage" in result,
            "forecast output missing field: management_target_coverage",
        )
    elif result["schema_version"] == "3.1":
        require(
            "management_target_coverage" in result,
            "forecast output missing field: management_target_coverage",
        )
    hash_payload = {
        key: value for key, value in result.items() if key != "result_sha256"
    }
    years = list(map(str, result["forecast_years"]))
    base = float(result["base_revenue"])
    consolidated = result["consolidated_forecast"]
    parameter_index = {
        parameter["parameter_id"]: parameter for parameter in result["parameter_trace"]
    }
    if data is not None:
        validate_annual_consumption(data, parameter_index)
    segment_index = {segment["name"]: segment for segment in result["segments"]}
    require(
        len(segment_index) == len(result["segments"]),
        "forecast output contains duplicate segment names",
    )
    for segment in result["segments"]:
        for scenario in SCENARIOS:
            output = segment["scenarios"][scenario]
            recalculated = calculate_model_path(
                output["model"],
                float(segment["base_revenue"]),
                output["driver_parameter_ids"],
                parameter_index,
                list(map(int, result["forecast_years"])),
                scenario,
            )
            require(
                recalculated["annual_revenue"] == output["modeled_activity"],
                f"segment modeled activity mismatch: {segment['name']}/{scenario}",
            )
            modeled = list(output["modeled_activity"].values())
            recognition = segment["recognition"]
            if recognition["timing"] == "over_time":
                progress = list(output["progress_values"].values())
                expected_recognized = [
                    value * factor for value, factor in zip(modeled, progress)
                ]
            elif recognition["mode"] == "lagged_activity":
                lag = recognition["lag_years"]
                expected_recognized = list(output["carry_in_revenue"]) + modeled[:-lag]
            else:
                expected_recognized = modeled
            observed_recognized = list(output["recognized_revenue"].values())
            require(
                all(
                    math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)
                    for left, right in zip(expected_recognized, observed_recognized)
                ),
                f"segment recognized revenue mismatch: {segment['name']}/{scenario}",
            )
        for year in years:
            require(
                segment["scenarios"]["low"]["recognized_revenue"][year]
                <= segment["scenarios"]["base"]["recognized_revenue"][year]
                <= segment["scenarios"]["high"]["recognized_revenue"][year],
                f"segment scenario ordering mismatch: {segment['name']}/{year}",
            )

    # Opening presentation and incremental denominators must use the same
    # authored foundation as the forecast calculation.
    _validate_segment_opening_bases(result, parameter_index, years, data)

    current_constraint_contract = requires_bound_input_schema(result["schema_version"]) or (
        result["schema_version"],
        result["engine_version"],
    ) in {
        ("3.2", "3.3.0"),
        ("3.3", "3.4.0"),
        ("3.5", ENGINE_VERSION),
    }
    if current_constraint_contract:
        require(
            isinstance(result.get("revenue_constraints"), list),
            "forecast output missing revenue_constraints",
        )
        require(
            isinstance(result.get("constraint_audit"), list),
            "forecast output missing constraint_audit",
        )
        try:
            expected_segments, expected_audit = apply_revenue_constraints(
                result["segments"],
                result["revenue_constraints"],
                parameter_index,
                list(map(int, result["forecast_years"])),
            )
        except RevenueConstraintError as exc:
            raise ForecastInputError(str(exc)) from exc
        require(
            expected_audit == result["constraint_audit"],
            "constraint audit recomputation mismatch",
        )
        expected_index = {segment["name"]: segment for segment in expected_segments}
        for segment in result["segments"]:
            for scenario in SCENARIOS:
                require(
                    segment["scenarios"][scenario].get("effective_revenue")
                    == expected_index[segment["name"]]["scenarios"][scenario][
                        "effective_revenue"
                    ],
                    f"segment effective revenue mismatch: {segment['name']}/{scenario}",
                )
    else:
        require(
            not result.get("revenue_constraints"),
            "legacy forecast cannot contain revenue_constraints",
        )

    def effective_path(segment: dict[str, Any], scenario: str) -> dict[str, Any]:
        output = segment["scenarios"][scenario]
        return output.get("effective_revenue", output["recognized_revenue"])

    for segment in result["segments"]:
        for year in years:
            require(
                effective_path(segment, "low")[year]
                <= effective_path(segment, "base")[year]
                <= effective_path(segment, "high")[year],
                f"segment effective scenario ordering mismatch: {segment['name']}/{year}",
            )
    require(
        set(consolidated) == set(SCENARIOS),
        "consolidated_forecast must contain low/base/high",
    )
    _recompute_consolidated_paths(consolidated, years, segment_index, base, effective_path)
    for year in years:
        require(
            consolidated["low"]["annual_revenue"][year]
            <= consolidated["base"]["annual_revenue"][year]
            <= consolidated["high"]["annual_revenue"][year],
            f"scenario ordering mismatch in output/{year}",
        )
    weighted = result.get("probability_weighted_forecast")
    probabilities = result.get("scenario_probabilities")
    require(
        (weighted is None) == (probabilities is None),
        "probability output is inconsistent",
    )
    if probabilities is not None:
        require(
            isinstance(probabilities, dict), "scenario_probabilities must be an object"
        )
        require(
            set(probabilities.keys()) == set(SCENARIOS),
            "scenario_probabilities must contain exactly low/base/high",
        )
        for scenario in SCENARIOS:
            prob_value = probabilities[scenario]
            require(
                isinstance(prob_value, (int, float))
                and not isinstance(prob_value, bool),
                f"scenario_probabilities.{scenario} must be a number",
            )
            require(
                math.isfinite(float(prob_value)),
                f"scenario_probabilities.{scenario} must be finite",
            )
            require(
                float(prob_value) >= 0,
                f"scenario_probabilities.{scenario} cannot be negative",
            )
        prob_sum = sum(float(probabilities[s]) for s in SCENARIOS)
        require(
            math.isclose(prob_sum, 1.0, rel_tol=1e-9, abs_tol=1e-9),
            f"scenario_probabilities must sum to 1, got {prob_sum}",
        )
    if weighted is not None:
        for year in years:
            expected = sum(
                float(probabilities[scenario])
                * consolidated[scenario]["annual_revenue"][year]
                for scenario in SCENARIOS
            )
            require(
                math.isclose(
                    expected,
                    float(weighted["annual_revenue"][year]),
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                ),
                f"probability-weighted revenue mismatch in {year}",
            )
        terminal = float(weighted["annual_revenue"][years[-1]])
        require(
            math.isclose(
                terminal,
                float(weighted["terminal_revenue"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            "probability-weighted terminal mismatch",
        )
        expected_cagr = calculate_cagr(base, terminal, len(years))
        require(
            (
                expected_cagr is None
                and weighted["expected_terminal_implied_cagr"] is None
            )
            or math.isclose(
                float(expected_cagr),
                float(weighted["expected_terminal_implied_cagr"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            "probability-weighted CAGR mismatch",
        )
        require(
            math.isclose(
                terminal - base,
                float(weighted["incremental_revenue"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            "probability-weighted increment mismatch",
        )
    require(
        isinstance(result["sources"], list) and result["sources"],
        "forecast output requires sources",
    )
    require(
        isinstance(result["parameter_trace"], list) and result["parameter_trace"],
        "forecast output requires parameter trace",
    )
    require(
        isinstance(result["evidence_claims"], list) and result["evidence_claims"],
        "forecast output requires evidence claims",
    )
    if requires_bound_input_schema(result["schema_version"]):
        as_of = parse_iso_date(result["as_of_date"], "as_of_date")
        source_capture_index = {}
        for source in result["sources"]:
            capture = validate_source_capture(source, as_of)
            source_capture_index[source["source_id"]] = capture
        for claim in result["evidence_claims"]:
            capture = source_capture_index.get(claim.get("source_id"))
            require(
                isinstance(capture, dict),
                f"claim source capture is missing: {claim.get('claim_id')}",
            )
            require(
                claim.get("capture_receipt_sha256") == capture["receipt_sha256"],
                f"claim capture receipt mismatch: {claim.get('claim_id')}",
            )
            require(
                claim.get("content_sha256") == capture["snapshot_sha256"],
                f"claim/source snapshot mismatch: {claim.get('claim_id')}",
            )
    coverage = result["research_coverage"]
    require(isinstance(coverage, dict), "research_coverage output must be an object")
    dimensions = coverage.get("dimensions")
    require(
        isinstance(dimensions, list) and len(dimensions) >= len(RESEARCH_DIMENSIONS),
        "research_coverage output must contain at least nine dimensions",
    )
    observed_dims = [record.get("dimension") for record in dimensions]
    require(
        observed_dims[: len(RESEARCH_DIMENSIONS)] == list(RESEARCH_DIMENSIONS),
        "research_coverage core dimensions are missing or out of order",
    )
    parameter_ids = {
        parameter["parameter_id"] for parameter in result["parameter_trace"]
    }
    source_ids = {source["source_id"] for source in result["sources"]}
    recomputed_counts = {status: 0 for status in RESEARCH_COVERAGE_STATUSES}
    seen_dims: set[str] = set()
    for record in dimensions:
        dim_name = record.get("dimension")
        require(
            isinstance(dim_name, str) and dim_name.strip(),
            "research_coverage dimension must be a non-empty string",
        )
        require(dim_name not in seen_dims, f"duplicate research dimension: {dim_name}")
        seen_dims.add(dim_name)
        status = record.get("status")
        require(
            status in RESEARCH_COVERAGE_STATUSES,
            f"invalid research coverage status: {status}",
        )
        recomputed_counts[status] += 1
        require(
            isinstance(record.get("conclusion"), str) and record["conclusion"].strip(),
            f"research coverage conclusion is required for {dim_name}",
        )
        require(
            isinstance(record.get("revenue_mechanism"), str)
            and record["revenue_mechanism"].strip(),
            f"research coverage revenue mechanism is required for {dim_name}",
        )
        require(
            set(record.get("parameter_ids", [])) <= parameter_ids,
            f"research coverage contains unknown parameter for {dim_name}",
        )
        require(
            set(record.get("source_ids", [])) <= source_ids,
            f"research coverage contains unknown source for {dim_name}",
        )
        if status == "data_gap":
            expected_gap = f"{dim_name}: {record['conclusion']}"
            require(
                expected_gap in result.get("data_gaps", []),
                f"research data gap missing from output: {dim_name}",
            )
    require(
        coverage.get("counts") == recomputed_counts, "research_coverage counts mismatch"
    )
    if result["schema_version"] in ({"3.1", "3.2", "3.3"} | BOUND_INPUT_SCHEMA_VERSIONS):
        target_coverage = result["management_target_coverage"]
        require(
            isinstance(target_coverage, dict),
            "management_target_coverage output must be an object",
        )
        communications = target_coverage.get("communications")
        targets = target_coverage.get("targets")
        counts = target_coverage.get("counts")
        require(
            isinstance(communications, list)
            and len(communications) == len(MANAGEMENT_COMMUNICATION_CATEGORIES),
            "management communication output is incomplete",
        )
        require(
            [record.get("category") for record in communications]
            == list(MANAGEMENT_COMMUNICATION_CATEGORIES),
            "management communication categories are missing or out of order",
        )
        if data is not None and (data.get("audit_communication_coverage") or
                                 any(is_typed_target(t) for t in data.get("management_targets", [])) or
                                 any(c.get("checked_scope") is not None for c in data.get("management_communication_coverage", []))):
            checked = validate_management_target_coverage(
                data, {s["source_id"]: s for s in result["sources"]}, parameter_index,
                {c["claim_id"]: c for c in result["evidence_claims"]}, parse_iso_date(result["as_of_date"], "as_of_date"),
            )
            expected = add_management_target_analysis({"management_target_coverage": checked,
                                                       "parameter_index": parameter_index}, result)
            require(target_coverage == expected, "typed management coverage/input binding mismatch")
        observed_target_ids: set[str] = set()
        for record in communications:
            require(
                record.get("status") in MANAGEMENT_COMMUNICATION_STATUSES,
                f"invalid management communication status: {record.get('category')}",
            )
            require(
                isinstance(record.get("conclusion"), str)
                and record["conclusion"].strip(),
                f"management communication conclusion is required: {record.get('category')}",
            )
            require(
                set(record.get("source_ids", [])) <= source_ids,
                f"management communication contains unknown source: {record.get('category')}",
            )
            observed_target_ids.update(record.get("material_revenue_target_ids", []))
        require(isinstance(targets, list), "management target output must be a list")
        target_ids = {target.get("target_id") for target in targets}
        require(
            len(target_ids) == len(targets) and None not in target_ids,
            "management target IDs must be unique",
        )
        require(
            target_ids == observed_target_ids,
            "management communication and target output IDs do not match",
        )
        recomputed_target_counts = {
            "communications_checked": sum(
                record["status"] == "checked" for record in communications
            ),
            "targets_total": len(targets),
            "targets_modeled": sum(
                target.get("treatment") in {"modeled_scenario", "scenario_boundary"}
                for target in targets
            ),
            "targets_unmodeled": sum(
                target.get("treatment") not in {"modeled_scenario", "scenario_boundary", "independent_benchmark"}
                for target in targets
            ),
        }
        benchmark_count = sum(target.get("treatment") == "independent_benchmark" for target in targets)
        if benchmark_count:
            recomputed_target_counts["targets_independent_benchmarks"] = benchmark_count
        require(
            counts == recomputed_target_counts,
            "management target coverage counts mismatch",
        )
        for target in targets:
            target_id = target["target_id"]
            require(
                target.get("treatment") in MANAGEMENT_TARGET_TREATMENTS,
                f"invalid management target treatment: {target_id}",
            )
            comparisons = target.get("scenario_comparison")
            require(
                isinstance(comparisons, dict),
                f"management target scenario comparison must be an object: {target_id}",
            )
            if result["schema_version"] in ({"3.2", "3.3"} | BOUND_INPUT_SCHEMA_VERSIONS):
                require(
                    target.get("measurement_basis")
                    in MANAGEMENT_TARGET_MEASUREMENT_BASES,
                    f"invalid management target measurement basis: {target_id}",
                )
                require(
                    isinstance(target.get("measurement_periods"), list),
                    f"invalid management target measurement periods: {target_id}",
                )
            if is_typed_target(target):
                require(comparisons == compare_target_measurement(target, result),
                        f"typed management target comparison recomputation mismatch: {target_id}")
                continue
            if target["treatment"] in {"modeled_scenario", "scenario_boundary", "independent_benchmark"}:
                require(
                    set(comparisons) == set(target.get("mapped_scenarios", [])),
                    f"management target scenario comparison mismatch: {target_id}",
                )
                for scenario, comparison in comparisons.items():
                    if target["scope"]["type"] == "company":
                        revenue_path = result["consolidated_forecast"][scenario][
                            "annual_revenue"
                        ]
                    else:
                        revenue_path = effective_path(
                            segment_index[target["scope"]["name"]], scenario
                        )
                    if result["schema_version"] == "3.1":
                        year = str(int(target["target_period"][2:]))
                        modeled_value = float(revenue_path[year])
                    else:
                        periods = target["measurement_periods"]
                        period_values = {
                            period: float(revenue_path[period[2:]])
                            for period in periods
                        }
                        require(
                            comparison.get("measurement_basis")
                            == target["measurement_basis"],
                            f"management target comparison basis mismatch: {target_id}/{scenario}",
                        )
                        require(
                            comparison.get("measurement_periods") == periods,
                            f"management target comparison periods mismatch: {target_id}/{scenario}",
                        )
                        require(
                            comparison.get("modeled_period_values") == period_values,
                            f"management target period values mismatch: {target_id}/{scenario}",
                        )
                        modeled_value = (
                            sum(period_values.values())
                            if target["measurement_basis"] == "cumulative_periods"
                            else period_values[periods[0]]
                        )
                    require(
                        math.isclose(
                            modeled_value,
                            float(comparison["modeled_value"]),
                            rel_tol=1e-9,
                            abs_tol=1e-9,
                        ),
                        f"management target modeled value mismatch: {target_id}/{scenario}",
                    )
                    target_value = float(target["comparison_value"])
                    require(
                        math.isclose(
                            target_value,
                            float(comparison["target_value"]),
                            rel_tol=1e-9,
                            abs_tol=1e-9,
                        ),
                        f"management target comparison value mismatch: {target_id}/{scenario}",
                    )
                    expected_ratio = (
                        None if target_value == 0 else modeled_value / target_value
                    )
                    require(
                        (
                            expected_ratio is None
                            and comparison["attainment_ratio"] is None
                        )
                        or math.isclose(
                            expected_ratio,
                            float(comparison["attainment_ratio"]),
                            rel_tol=1e-9,
                            abs_tol=1e-9,
                        ),
                        f"management target attainment mismatch: {target_id}/{scenario}",
                    )
                    comparison_op = target.get("comparison", "at_least")
                    tolerance_val = float(target.get("comparison_tolerance", 0.01))
                    if comparison_op == "at_least":
                        expected_meets = modeled_value >= target_value * (1 - tolerance_val)
                    elif comparison_op == "at_most":
                        expected_meets = modeled_value <= target_value * (1 + tolerance_val)
                    else:
                        expected_meets = math.isclose(
                            modeled_value,
                            target_value,
                            rel_tol=tolerance_val,
                            abs_tol=max(1.0, abs(target_value)) * tolerance_val,
                        )
                    require(
                        comparison.get("meets_target") is expected_meets,
                        f"management target meets_target recomputation mismatch: {target_id}/{scenario}",
                    )
            else:
                require(
                    not comparisons,
                    f"unmodeled management target cannot contain scenario comparisons: {target_id}",
                )
                expected_gap_prefix = f"management_target:{target_id}:"
                require(
                    any(
                        str(gap).startswith(expected_gap_prefix)
                        for gap in result.get("data_gaps", [])
                    ),
                    f"unmodeled management target gap missing from output: {target_id}",
                )
    for sensitivity in result.get("sensitivities", []):
        baseline = float(sensitivity["baseline_terminal_revenue"])
        impact = max(
            abs(float(sensitivity["down_terminal_revenue"]) - baseline),
            abs(float(sensitivity["up_terminal_revenue"]) - baseline),
        )
        require(
            math.isclose(
                impact,
                float(sensitivity["max_absolute_terminal_impact"]),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            f"sensitivity impact mismatch: {sensitivity['name']}",
        )
        expected_relative = None if baseline == 0 else impact / baseline
        observed_relative = sensitivity["max_relative_terminal_impact"]
        require(
            (expected_relative is None and observed_relative is None)
            or math.isclose(
                float(expected_relative),
                float(observed_relative),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ),
            f"sensitivity relative impact mismatch: {sensitivity['name']}",
        )
    # When input data is available, independently re-run each sensitivity shock
    # and verify the stored terminals match the model output.  This prevents
    # forged terminals from passing even after all hashes are recomputed.
    if data is not None and result.get("sensitivities"):
        expected_sensitivities = calculate_sensitivities(data, result)
        expected_by_param = {
            item["parameter_id"]: item for item in expected_sensitivities
        }
        for sensitivity in result["sensitivities"]:
            expected = expected_by_param.get(sensitivity["parameter_id"])
            require(expected is not None, f"unexpected sensitivity parameter: {sensitivity['parameter_id']}")
            for field in ("requested_values", "effective_values", "clamped", "dependency_recalculation"):
                require(sensitivity.get(field) == expected.get(field),
                        f"sensitivity {field} recomputation mismatch: {sensitivity['name']}")
            require(
                math.isclose(
                    float(sensitivity["down_terminal_revenue"]),
                    float(expected["down_terminal_revenue"]),
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                ),
                f"sensitivity down terminal recomputation mismatch: {sensitivity['name']}",
            )
            require(
                math.isclose(
                    float(sensitivity["up_terminal_revenue"]),
                    float(expected["up_terminal_revenue"]),
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                ),
                f"sensitivity up terminal recomputation mismatch: {sensitivity['name']}",
            )
    # Sensitivity completeness gate (opt-in via data["require_sensitivity_completeness"]):
    # every base-scenario assumption/stress parameter that drives revenue must be
    # either sensitivity-tested or carry a structured exclusion.  Host approval
    # of exclusions is a Phase 8 trust boundary; here we enforce completeness and
    # the exclusion structure (reason + rationale).
    if data is not None and data.get("require_sensitivity_completeness"):
        param_kinds = {p["parameter_id"]: p["kind"] for p in result["parameter_trace"]}
        eligible = {
            pid
            for pid in scenario_forecast_parameter_ids(data, "base", parameter_index)
            if param_kinds.get(pid) in {"analyst_assumption", "scenario_stress"}
        }
        tested = {s["parameter_id"] for s in result.get("sensitivities", [])}
        excluded_ids: set[str] = set()
        for exclusion in data.get("sensitivity_exclusions", []):
            require(
                isinstance(exclusion, dict),
                "sensitivity_exclusions entry must be an object",
            )
            ex_param = exclusion.get("parameter_id")
            require(
                isinstance(ex_param, str) and ex_param.strip(),
                "sensitivity_exclusion parameter_id is required",
            )
            require(
                ex_param not in excluded_ids,
                f"duplicate sensitivity exclusion: {ex_param}",
            )
            excluded_ids.add(ex_param)
            require(
                isinstance(exclusion.get("reason"), str)
                and exclusion["reason"].strip(),
                f"sensitivity exclusion reason is required: {ex_param}",
            )
            require(
                isinstance(exclusion.get("rationale"), str)
                and exclusion["rationale"].strip(),
                f"sensitivity exclusion rationale is required: {ex_param}",
            )
        uncovered = eligible - tested - excluded_ids
        require(
            not uncovered,
            f"sensitivity completeness required: untested parameter(s) without exclusion: {sorted(uncovered)}",
        )
    confidence = result["confidence"]
    _validate_confidence_block(confidence)
    reconstructed_segments = []
    for segment in result["segments"]:
        reconstructed_segments.append(
            {
                "name": segment["name"],
                "recognition": segment["recognition"],
                "scenarios": {
                    scenario: {
                        "model": segment["scenarios"][scenario]["model"],
                        "driver_parameter_ids": segment["scenarios"][scenario][
                            "driver_parameter_ids"
                        ],
                    }
                    for scenario in SCENARIOS
                },
            }
        )
    reconstructed_adjustments = []
    for base_adjustment in consolidated["base"]["adjustment_bridge"]:
        reconstructed_adjustments.append(
            {
                "name": base_adjustment["name"],
                "category": base_adjustment["category"],
                "scenario_parameter_ids": {
                    scenario: next(
                        item
                        for item in consolidated[scenario]["adjustment_bridge"]
                        if item["name"] == base_adjustment["name"]
                    )["parameter_ids"]
                    for scenario in SCENARIOS
                },
            }
        )
    reconstructed_data = {
        "company_name": result["company_name"],
        "currency": result["currency"],
        "unit": result["unit"],
        "fiscal_year_end": result["fiscal_year_end"],
        "as_of_date": result["as_of_date"],
        "schema_version": result["schema_version"],
        "segments": reconstructed_segments,
        "forecast_adjustments": reconstructed_adjustments,
        "historical_accuracy_records": result.get("historical_accuracy_records", []),
    }
    reconstructed_validated = {
        "parameter_index": parameter_index,
        "claim_index": {
            claim["claim_id"]: claim for claim in result["evidence_claims"]
        },
        "source_index": {source["source_id"]: source for source in result["sources"]},
        "as_of_date": parse_iso_date(result["as_of_date"], "as_of_date"),
        "research_coverage": {"counts": coverage["counts"]},
    }
    if result["schema_version"] in ({"3.1", "3.2", "3.3"} | BOUND_INPUT_SCHEMA_VERSIONS):
        reconstructed_validated["management_target_coverage"] = {
            "counts": result["management_target_coverage"]["counts"]
        }
    if result["schema_version"] in ({"3.3"} | BOUND_INPUT_SCHEMA_VERSIONS):
        analysis = result["growth_driver_analysis"]
        require(
            isinstance(analysis, dict),
            "growth_driver_analysis output must be an object",
        )
        status = analysis.get("status")
        require(
            status in {"modeled", "data_gap"},
            f"invalid growth_driver_analysis status: {status}",
        )
        # Formal-mode driver-tree gate: a modeled segment with positive terminal
        # revenue cannot have a data-gap driver tree unless an explicit exception
        # is registered.  (Phase 8 — host-approval of exceptions is a trust
        # boundary; here we enforce structural completeness.)
        pub_receipt = result.get("publication_receipt")
        if (
            pub_receipt is not None
            and pub_receipt.get("formal_output_mode") == "formal"
        ):
            if status == "data_gap":
                has_positive_revenue = any(
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
                    > 0
                    for segment in result["segments"]
                    if segment["scenarios"]["base"]["model"]
                    not in {"direct_growth", "direct_revenue"}
                )
                if has_positive_revenue and not (data or {}).get(
                    "driver_tree_exclusion"
                ):
                    raise ForecastInputError(
                        "formal publication requires a modeled growth-driver tree "
                        "or a driver_tree_exclusion for every modeled segment with positive revenue"
                    )
        normalized_drivers = []
        for driver in analysis.get("drivers", []):
            require(
                isinstance(driver, dict),
                "growth_driver_analysis driver must be an object",
            )
            normalized_drivers.append(
                {
                    key: value
                    for key, value in driver.items()
                    if key
                    not in {
                        "terminal_increment_by_segment",
                        "estimated_base_terminal_increment",
                        "share_of_positive_driver_increment",
                    }
                }
            )
        growth_tree = {"status": status, "drivers": normalized_drivers}
        if status == "data_gap":
            growth_tree["rationale"] = analysis.get("rationale")
        growth_data = {
            "schema_version": result["schema_version"],
            "forecast_years": result["forecast_years"],
            "segments": reconstructed_segments,
            "forecast_adjustments": reconstructed_adjustments,
            "revenue_constraints": result.get("revenue_constraints", []),
            "growth_driver_tree": growth_tree,
        }
        validated_growth_tree = validate_growth_driver_tree(
            growth_data,
            reconstructed_validated["source_index"],
            parameter_index,
            reconstructed_validated["claim_index"],
        )
        reconstructed_validated["growth_driver_tree"] = validated_growth_tree
        expected_growth_analysis = calculate_growth_driver_analysis(
            reconstructed_validated, result
        )
        require(
            expected_growth_analysis == analysis,
            "growth driver analysis recomputation mismatch",
        )
    research_input = data if data is not None else result.get("input_document", {})
    if research_input.get("operating_research") is not None:
        reconstructed_data.update({key: research_input[key] for key in
                                   ("operating_research", "growth_driver_tree") if key in research_input})
        reconstructed_data["base_year"] = result["base_year"]
        reconstructed_data["forecast_years"] = result["forecast_years"]
    if data is not None:
        reconstructed_data = copy.deepcopy(data)
    expected_confidence = calculate_confidence(
        reconstructed_data,
        reconstructed_validated,
        result,
        result.get("sensitivities", []),
    )
    validate_confidence_recomputation(expected_confidence, confidence)
    theme = result.get("theme_analysis")
    if theme is not None:
        _validate_theme_analysis(theme, segment_index, parameter_index, base, effective_path)
    _validate_receipt_blocks(result, hash_payload)


def validate_published_forecast(
    result: dict[str, Any], data: dict[str, Any] | None
) -> VerificationContext:
    """Strong, formal-only entry point for published forecast output.

    Requires the original input document so every input-gated gate (sensitivity
    shock recomputation, completeness, driver-tree exclusion) is re-run from the
    model, not trusted from stored fields.  Returns the ``VerificationContext``
    that ``build_publication_receipt`` requires; a forged artifact cannot obtain
    one because the strong validation rejects it first (RED for F-01/F-02).
    """
    if data is None:
        raise TypeError(
            "validate_published_forecast requires the original input document"
        )
    # R1.1 (N-01): bind the validator to the input it actually re-runs — the
    # anchor must be the hash of this exact document, not a self-reported one.
    verify_input_binding(result, data)
    _validate_forecast_output(result, data)
    return VerificationContext(
        result["input_sha256"],
        expected_publication_gates(result),
        ENGINE_VERSION,
    )


def validate_legacy_output(result: dict[str, Any]) -> None:
    """Restricted legacy read-only entry point (schema <= current read-only).

    Runs the structural and output-only recomputation gates without the original
    input.  It never claims the input-gated gates (sensitivity shocks /
    completeness), so consumers must use ``validate_published_forecast`` for
    formal, invest-consumable artifacts.
    """
    if requires_bound_input_schema(result["schema_version"]):
        # R1.1 (N-01): a current-schema artifact carries no input at all —
        # there is nothing to bind, so it cannot be validated, only rejected.
        raise ForecastInputError(
            "current-schema artifact without a bound input cannot be validated"
        )
    _validate_forecast_output(result, None)


def validate_forecast_output(
    result: dict[str, Any], data: dict[str, Any] | None = None
) -> None:
    """Backward-compatible dispatcher.

    With the original input (or the self-contained ``input_document`` embedded
    by ``run_forecast``) the strong formal path runs; otherwise the restricted
    legacy read-only path runs.
    """
    if data is None:
        data = result.get("input_document")
    if data is not None:
        validate_published_forecast(result, data)
    else:
        validate_legacy_output(result)


def _num(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value):,.2f}"


def _pct(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.1f}%"


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(result: dict[str, Any]) -> str:
    # REV-06 (ZR-705): a draft result may be rendered without publishing.
    # Draft receipts skip the formal-only strong validation (which requires
    # the formal gate set) — the draft was already strongly validated inside
    # run_forecast before the draft receipt was built.
    if result.get("publication_receipt", {}).get("formal_output_mode") != "draft":
        validate_forecast_output(result)
    years = list(map(str, result["forecast_years"]))
    lines: list[str] = [
        f"# {_escape(result['company_name'])}营收预测",
        "",
        f"- 信息截止日：{result['as_of_date']}",
        f"- 财年截止日：{result['fiscal_year_end']}",
        f"- 币种与单位：{result['currency']} {result['unit']}",
        f"- 基期营收：{_num(result['base_revenue'])}",
        f"- 预测版本：{_escape(result.get('forecast_version', '—'))}",
        "",
        "## 核心营收结论",
        "",
        "| 情景 | 终值营收 | CAGR | 营收增量 |",
        "|---|---:|---:|---:|",
    ]
    for scenario in SCENARIOS:
        forecast = result["consolidated_forecast"][scenario]
        lines.append(
            f"| {scenario} | {_num(forecast['terminal_revenue'])} | {_pct(forecast['cagr'])} | {_num(forecast['incremental_revenue'])} |"
        )
    if result.get("probability_weighted_forecast") is not None:
        weighted = result["probability_weighted_forecast"]
        lines.extend(
            [
                "",
                "### 概率加权路径",
                "",
                f"- 概率：Low {_pct(result['scenario_probabilities']['low'])}；Base {_pct(result['scenario_probabilities']['base'])}；High {_pct(result['scenario_probabilities']['high'])}。",
                f"- 加权终值：{_num(weighted['terminal_revenue'])}；隐含CAGR：{_pct(weighted['expected_terminal_implied_cagr'])}。",
                f"- 校准理由：{_escape(weighted['probability_rationale'])}",
            ]
        )

    driver_analysis = result.get("growth_driver_analysis")
    if driver_analysis is not None:
        lines.extend(["", "## 未来收入主要驱动力", ""])
        if driver_analysis["status"] == "data_gap":
            lines.append(
                f"- 尚未形成可审计驱动树：{_escape(driver_analysis['rationale'])}"
            )
        elif driver_analysis["top_drivers"]:
            for driver in driver_analysis["top_drivers"]:
                lines.append(
                    f"{driver['rank']}. **{_escape(driver['title'])}** — {_escape(driver['thesis'])} "
                    f"（Base终年增量 {_num(driver['estimated_base_terminal_increment'])}；"
                    f"占正向驱动 {_pct(driver['share_of_positive_driver_increment'])}；"
                    f"证据 {_escape(driver['evidence_status'])}）"
                )
        else:
            lines.append("- Base情景未识别出正向终年营收增量；详见下方驱动树与逆风项。")
        if driver_analysis.get("headwinds"):
            lines.extend(["", "### 主要收入逆风", ""])
            for driver in driver_analysis["headwinds"]:
                lines.append(
                    f"- **{_escape(driver['title'])}** — {_escape(driver['thesis'])} "
                    f"（Base终年影响 {_num(driver['estimated_base_terminal_increment'])}）"
                )

    lines.extend(["", "## 历史营收", "", "| 年度 | 营收 | 来源ID |", "|---:|---:|---|"])
    for record in result["historical_revenue"]:
        lines.append(
            f"| {record['year']} | {_num(record['value'])} | {_escape(', '.join(record['source_ids']))} |"
        )

    coverage = result["research_coverage"]
    counts = coverage["counts"]
    lines.extend(
        [
            "",
            "## 九维研究覆盖",
            "",
            f"- 进入模型：{counts['modeled_driver']}；数据缺口：{counts['data_gap']}；当前不重要：{counts['immaterial']}。",
            "- 本表用于防止研究漏项，不直接给CAGR或置信度加分。",
            "",
            "| 维度 | 状态 | 结论 | 营收传导 | 参数ID | 来源ID | 理由 |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for record in coverage["dimensions"]:
        lines.append(
            f"| {_escape(record['dimension'])} | {_escape(record['status'])} | {_escape(record['conclusion'])} | "
            f"{_escape(record['revenue_mechanism'])} | {_escape(', '.join(record['parameter_ids']) or '—')} | "
            f"{_escape(', '.join(record['source_ids']) or '—')} | {_escape(record.get('rationale', '—'))} |"
        )

    if result.get("management_target_coverage") is not None:
        target_coverage = result["management_target_coverage"]
        target_counts = target_coverage["counts"]
        lines.extend(
            [
                "",
                "## 管理层沟通与营收目标覆盖",
                "",
                f"- 已检查官方沟通类别：{target_counts['communications_checked']}/{len(MANAGEMENT_COMMUNICATION_CATEGORIES)}；重大/相关目标：{target_counts['targets_total']}；已进入情景：{target_counts['targets_modeled']}；独立基准比较：{target_counts.get('targets_independent_benchmarks', 0)}；未建模：{target_counts['targets_unmodeled']}。",
                "",
                "| 沟通类别 | 状态 | 结论 | 目标ID | 来源ID |",
                "|---|---|---|---|---|",
            ]
        )
        for record in target_coverage["communications"]:
            lines.append(
                f"| {_escape(record['category'])} | {_escape(record['status'])} | {_escape(record['conclusion'])} | "
                f"{_escape(', '.join(record['material_revenue_target_ids']) or '—')} | {_escape(', '.join(record['source_ids']) or '—')} |"
            )
        for record in target_coverage["communications"]:
            diagnostic = record.get("coverage_diagnostic")
            if diagnostic is not None:
                lines.extend(["", f"- {_escape(record['category'])} coverage: {_escape(diagnostic['status'])}; {_escape(diagnostic.get('start_date') or 'unknown')}–{_escape(diagnostic.get('end_date') or 'unknown')}; {_escape(diagnostic.get('reason') or 'complete')}."])
        lines.extend(
            [
                "",
                "| 目标 | 强度 | 原始目标 | 来源期间 | 测量口径/模型期间 | 业务口径 | 处理 | 映射情景 | 模型兑现度 |",
                "|---|---|---:|---|---|---|---|---|---|",
            ]
        )
        for target in target_coverage["targets"]:
            attainment = (
                ", ".join(
                    f"{scenario}:{_pct(values['attainment_ratio'])}"
                    for scenario, values in target["scenario_comparison"].items()
                )
                or "—"
            )
            raw_value = target.get("raw_target_value")
            if raw_value is None and target.get("raw_target_value_low") is not None:
                raw_value = target["raw_target_value_low"]
            raw_cell = (
                _escape(target["raw_label"])
                if target.get("raw_label")
                else _num(raw_value)
            )
            if target.get("raw_target_value_high") is not None:
                raw_cell = f"{raw_cell}–{_num(target['raw_target_value_high'])}"
            basis_cell = _escape(target.get("measurement_basis", "legacy_unspecified"))
            basis_tags = [
                tag for tag in (
                    target.get("target_quarter"),
                    target.get("currency_basis"),
                    target.get("presentation_basis"),
                ) if tag
            ]
            if basis_tags:
                basis_cell = f"{basis_cell} [{_escape(', '.join(basis_tags))}]"
            basis_cell = (
                f"{basis_cell}: {_escape(', '.join(target.get('measurement_periods', [])) or '—')}"
            )
            lines.append(
                f"| {_escape(target['target_id'])} | {_escape(target['commitment_strength'])} | "
                f"{raw_cell} {_escape(target['raw_unit'])} | {_escape(target['target_period'])} | "
                f"{basis_cell} | "
                f"{_escape(target['perimeter_status'])}: {_escape(target['perimeter_notes'])} | {_escape(target['treatment'])} | "
                f"{_escape(', '.join(target['mapped_scenarios']) or '—')} | {_escape(attainment)} |"
            )
        for target in target_coverage["targets"]:
            if is_typed_target(target):
                dates = ", ".join(f"{sid}:{published}" for sid, published in target.get("source_publication_dates", {}).items())
                lines.extend(["", f"- {_escape(target['target_id'])} 原文：{_escape(target['statement'])}；来源日期：{_escape(dates)}。",
                              "", "| Scenario | Metric / period | Modeled / unit | Target / range | Base / period | Difference | Status / reason |",
                              "|---|---|---:|---:|---|---|---|"])
                if not target["scenario_comparison"]:
                    lines.append(f"- {_escape(target['treatment'])}: {_escape(target['rationale'])}; {_escape(target.get('comparison_reason') or 'comparison dependencies unavailable')}.")
                for scenario, row in target["scenario_comparison"].items():
                    difference = row.get("difference_percentage_points", row.get("difference"))
                    difference_unit = "percentage_points" if row["metric_kind"] == "year_over_year_growth" else row["unit"]
                    lines.append(f"| {_escape(scenario)} | {_escape(row['metric_kind'])} / {_escape(row['period'])} | {_num(row['modeled_value'])} {_escape(row['unit'])} | {_num(row['target_low'])}–{_num(row['target_high'])} ({_escape(row['comparison'])}) | {_num(row.get('base_value'))} / {_escape(row.get('base_period') or '—')} | {_num(difference)} {_escape(difference_unit)} | {_escape(row['comparison_status'])} / {_escape(row.get('reason') or '—')} |")
                    derived = row.get("derived_revenue_benchmark")
                    if derived is not None:
                        lines.append(f"- {_escape(scenario)} analyst_derived revenue benchmark: {_num(derived['value'])} {_escape(derived['unit'])}; difference {_num(derived['difference'])}. Formula: {_escape(derived['formula'])}.")
            if target["treatment"] == "independent_benchmark":
                lines.extend(["", f"- {_escape(target['target_id'])} 独立判断：{_escape(target['benchmark_rationale'])}；证据：{_escape(', '.join(target['benchmark_claim_ids']))}。"])
            if target.get("normalization_formula"):
                lines.extend(["", f"- {_escape(target['target_id'])} 年化运行率转换：{_escape(target['normalization_formula'])}；x0 为原始目标，其余输入依次为 {_escape(', '.join(target['normalization_parameter_ids']))}；比较收入 {_num(target['comparison_value'])}；{_escape(target['normalization_rationale'])}。"])

    lines.extend(
        [
            "",
            "## 年度情景路径",
            "",
            "| 年度 | Low | Base | High | Base同比 |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for year in years:
        lines.append(
            f"| {year} | {_num(result['consolidated_forecast']['low']['annual_revenue'][year])} | "
            f"{_num(result['consolidated_forecast']['base']['annual_revenue'][year])} | "
            f"{_num(result['consolidated_forecast']['high']['annual_revenue'][year])} | "
            f"{_pct(result['consolidated_forecast']['base']['annual_growth'][year])} |"
        )

    lines.extend(
        [
            "",
            "## 三情景经营驱动",
            "",
            "| 分部 | 情景 | 驱动 | 年度 | 参数ID | 数值 |",
            "|---|---|---|---:|---|---:|",
        ]
    )
    for segment in result["segments"]:
        for scenario in SCENARIOS:
            output = segment["scenarios"][scenario]
            for driver, values in output["driver_values"].items():
                ids = output["driver_parameter_ids"].get(driver, [])
                for index, year in enumerate(years):
                    parameter_id = ids[index] if index < len(ids) else "default"
                    lines.append(
                        f"| {_escape(segment['name'])} | {scenario} | {_escape(driver)} | {year} | {_escape(parameter_id)} | {_num(values[year])} |"
                    )

    lines.extend(
        [
            "",
            "## 分部驱动与收入确认",
            "",
            "| 分部 | 模型 | 基期营收 | 确认时点 | 触发条件 | 列报 |",
            "|---|---|---:|---|---|---|",
        ]
    )
    for segment in result["segments"]:
        recognition = segment["recognition"]
        model = segment["scenarios"]["base"]["model"]
        lines.append(
            f"| {_escape(segment['name'])} | {_escape(model)} | {_num(segment['base_revenue'])} | "
            f"{_escape(recognition['timing'])} | {_escape(recognition['trigger'])} | {_escape(recognition['presentation'])} |"
        )

    lines.extend(
        ["", "## Base情景增量归因", "", "| 项目 | 终值营收增量 |", "|---|---:|"]
    )
    contribution = result["consolidated_forecast"]["base"]["incremental_contribution"]
    for item in contribution["segments"]:
        lines.append(
            f"| {_escape(item['name'])} | {_num(item['terminal_incremental_revenue'])} |"
        )
    lines.append(f"| 公司级调整 | {_num(contribution['adjustments'])} |")
    lines.append(f"| 合计 | {_num(contribution['total'])} |")

    if driver_analysis is not None:
        lines.extend(["", "## 收入增长驱动树", ""])
        if driver_analysis["status"] == "data_gap":
            lines.append(f"- 数据缺口：{_escape(driver_analysis['rationale'])}")
        else:
            for driver in driver_analysis["drivers"]:
                lines.extend(
                    [
                        f"### {_escape(driver['title'])}",
                        "",
                        f"- 结论：{_escape(driver['thesis'])}",
                        f"- 因果链：{_escape(' → '.join(driver['causal_chain']))}",
                        f"- Base终年增量：{_num(driver['estimated_base_terminal_increment'])}；正向增量占比：{_pct(driver['share_of_positive_driver_increment'])}",
                        f"- 归因分部：{_escape(', '.join(item['segment_name'] + '=' + _pct(item['weight']) for item in driver['segment_attribution']))}",
                        f"- 模型参数：{_escape(', '.join(driver['parameter_ids']))}",
                        f"- 持续性：{_escape(driver['persistence'])}；{_escape(driver['persistence_rationale'])}",
                        f"- 领先指标：{_escape('；'.join(driver['leading_indicators']))}",
                        f"- 可证伪条件：{_escape('；'.join(driver['falsifiers']))}",
                        f"- 反证检索：{_escape(driver['counterevidence_status'])}；{_escape(driver['counterevidence_rationale'])}",
                        f"- 证据状态：{_escape(driver['evidence_status'])}",
                        "- 支撑证据：",
                    ]
                )
                for node in driver["evidence_nodes"]:
                    lines.append(
                        f"  - [{_escape(node['evidence_type'])}/{_escape(node['inference_distance'])}] "
                        f"{_escape(node['conclusion'])}（Claim: {_escape(', '.join(node['claim_ids']))}；"
                        f"来源: {_escape(', '.join(node['source_ids']))}）"
                    )
                lines.append("")
            reconciliation = driver_analysis["reconciliation"]
            lines.extend(
                [
                    "### 驱动归因对账",
                    "",
                    f"- 驱动归因的分部增量：{_num(reconciliation['driver_attributed_segment_increment'])}",
                    f"- 分部增量合计：{_num(reconciliation['segment_increment_total'])}",
                    f"- 未归入经营驱动排名的公司级调整：{_num(reconciliation['unattributed_company_adjustments'])}",
                    f"- 与公司总增量差额：{_num(reconciliation['difference'])}",
                ]
            )

    lines.extend(["", "## 敏感性", ""])
    if result["sensitivities"]:
        lines.extend(
            [
                "| 参数 | 冲击类型 | 请求值(下/上) | 有效值(下/上) | 截断 | 下行终值 | 基准终值 | 上行终值 | 最大相对影响 |",
                "|---|---|---|---|---|---:|---:|---:|---:|",
            ]
        )
        for item in result["sensitivities"]:
            lines.append(
                f"| {_escape(item['parameter_id'])} | {_escape(item['shock_type'])} | {_num(item['requested_values']['down'])}/{_num(item['requested_values']['up'])} | "
                f"{_num(item['effective_values']['down'])}/{_num(item['effective_values']['up'])} | {_escape(item['clamped'])} | {_num(item['down_terminal_revenue'])} | "
                f"{_num(item['baseline_terminal_revenue'])} | {_num(item['up_terminal_revenue'])} | {_pct(item['max_relative_terminal_impact'])} |"
            )
    else:
        lines.append("未配置确定性敏感性测试。")

    confidence = result["confidence"]
    lines.extend(
        [
            "",
            "## 预测置信度",
            "",
            f"- 等级：{confidence['rating']}",
            f"- 分数：{confidence['score']:.1f}/100",
            f"- 驱动证据覆盖率：{_pct(confidence['driver_evidence_coverage'])}",
            "",
            "| 组成 | 得分 |",
            "|---|---:|",
        ]
    )
    for name, score in confidence["components"].items():
        lines.append(f"| {_escape(name)} | {score:.1f} |")
    adequacy = confidence.get("research_adequacy")
    if adequacy is not None:
        lines.extend(["", "### 经营内容与证据充分性", "",
                      "旧置信度总分衡量证据与流程；方向和量级按以下独立诊断披露。",
                      f"- Documentary presence: {adequacy['documentary_presence']['checked_claim_count']} checked claims",
                      f"- Mechanism direction: {', '.join(adequacy['mechanism_adequacy']['supported_parameter_ids']) or 'unknown'}",
                      f"- 量级支持: {adequacy['magnitude_adequacy']['status']}", "",
                      "| 内容 | 主题 | 处理 | 包含于 | 收入确认与缺口 |", "|---|---|---|---|---|"])
        for item in adequacy["inventory"]:
            lines.append(f"| {_escape(item['item_id'])} | {_escape(item['topic'])} | {_escape(item['disposition'])} | {_escape(item['included_in'])} | {_escape(item['recognition_note'])}; {_escape(item['rationale'])} |")
        for calibration in adequacy["calibrations"]:
            lines.extend(["", f"- 校准 {_escape(calibration['calibration_id'])}: {_escape(calibration['adequacy_status'])}; {_escape(calibration['scope'])}, {_escape(calibration['observed_period'])}; observed_range={_escape(calibration['observed_range'])}; formula={_escape(calibration['conversion_formula'])}"])
            for scenario, row in calibration["scenario_conversion"].items():
                lines.append(f"  - {scenario}: {_escape(row['input_parameter_ids'])} → {_escape(row['output_parameter_id'])} = {_num(row['formula_value'])} {_escape(row['output_unit'])}; native={_num(row['native_value'])}")
            lines.append(f"  - 限制: {_escape(calibration['reasons'] + calibration['limitations'])}")
        lines.extend(f"- {_escape(item)}" for item in adequacy["limitations"])
    lines.extend(["", "### 质量硬门", ""])
    lines.extend(
        [
            f"- {_escape(name)}：{'通过' if passed else '失败'}"
            for name, passed in confidence["quality_gates"].items()
        ]
    )

    if result.get("theme_analysis") is not None:
        lines.extend(
            [
                "",
                "## 主题反事实",
                "",
                "| 情景 | 主题终值 | 反事实终值 | 主题增量 | 占公司终值 |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for scenario in SCENARIOS:
            item = result["theme_analysis"]["scenarios"][scenario]
            lines.append(
                f"| {scenario} | {_num(item['theme_terminal_revenue'])} | {_num(item['counterfactual_terminal_revenue'])} | {_num(item['theme_incremental_revenue'])} | {_pct(item['theme_share_of_company_terminal'])} |"
            )

    lines.extend(["", "## 反证指标与数据缺口", ""])
    indicators = result.get("disconfirming_indicators", [])
    gaps = result.get("data_gaps", [])
    lines.append("### 反证指标")
    lines.extend([f"- {_escape(item)}" for item in indicators] or ["- 未提供。"])
    lines.extend(["", "### 数据缺口"])
    lines.extend([f"- {_escape(item)}" for item in gaps] or ["- 未记录数据缺口。"])

    lines.extend(
        [
            "",
            "## 参数—证据claim映射",
            "",
            "| 参数ID | 身份 | 数值 | 期间 | 维度 | Claim ID | 来源ID | 支持类型 | 定位 | 短摘录 |",
            "|---|---|---:|---|---|---|---|---|---|---|",
        ]
    )
    claims = {claim["claim_id"]: claim for claim in result["evidence_claims"]}
    for parameter in result["parameter_trace"]:
        claim_ids = parameter.get("claim_ids", [])
        displayed_period = parameter["period"]
        if parameter.get("time_basis") == "period_flow":
            displayed_period = (
                f"{displayed_period} / period_flow "
                f"{parameter['period_start']}..{parameter['period_end']}"
            )
        if not claim_ids:
            lines.append(
                f"| {_escape(parameter['parameter_id'])} | {_escape(parameter['kind'])} | {_num(parameter['value'])} | {_escape(displayed_period)} | {_escape(parameter['dimension'])} | — | — | — | — | — |"
            )
        for claim_id in claim_ids:
            claim = claims[claim_id]
            lines.append(
                f"| {_escape(parameter['parameter_id'])} | {_escape(parameter['kind'])} | {_num(parameter['value'])} | {_escape(displayed_period)} | {_escape(parameter['dimension'])} | {_escape(claim_id)} | {_escape(claim['source_id'])} | {_escape(claim['support_type'])} | {_escape(claim['locator'])} | {_escape(claim['excerpt'])} |"
            )

    lines.extend(
        [
            "",
            "## 参数来源",
            "",
            "| ID | 等级 | 类型 | 发布方 | 日期 | 定位 | 标题 |",
            "|---|---:|---|---|---|---|---|",
        ]
    )
    for source in result["sources"]:
        lines.append(
            f"| [{_escape(source['source_id'])}]({_escape(source['url'])}) | {_escape(source.get('source_rank', '—'))} | "
            f"{_escape(source['source_type'])} | {_escape(source['publisher'])} | {_escape(source['published_date'])} | "
            f"{_escape(source['page_or_section'])} | {_escape(source['title'])} |"
        )
    lines.append("")
    return "\n".join(lines)
