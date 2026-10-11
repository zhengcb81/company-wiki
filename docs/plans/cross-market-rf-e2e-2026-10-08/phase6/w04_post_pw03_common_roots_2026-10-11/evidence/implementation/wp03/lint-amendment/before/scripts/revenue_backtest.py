#!/usr/bin/env python3
"""Immutable revenue forecast snapshots and source-traceable backtests."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from revenue_core import (
    ForecastInputError,
    ENGINE_VERSION,
    FORECAST_SCHEMA_VERSION,
    SUPPORTED_FORECAST_SCHEMA_VERSIONS,
    calculate_cagr,
    canonical_sha256,
    finite_number,
    parse_iso_date,
    require,
    run_forecast,
    text_sha256,
    validate_sources,
)
from revenue_report import validate_published_forecast
from schema_compatibility import require_validating_engine
from trust_anchor import verify_input_binding


def create_snapshot(data: dict[str, Any], forecast_version: str) -> dict[str, Any]:
    require(
        isinstance(forecast_version, str) and forecast_version.strip(),
        "forecast_version is required",
    )
    frozen_input = copy.deepcopy(data)
    frozen_input["forecast_version"] = forecast_version
    result = run_forecast(frozen_input)
    validate_published_forecast(result, frozen_input)
    actual_schema = frozen_input["schema_version"]
    require(result["schema_version"] == actual_schema, "snapshot input/result schema mismatch")
    require_validating_engine(actual_schema, result["engine_version"], "formal")
    input_hash = canonical_sha256(frozen_input)
    result_hash = canonical_sha256(result)
    identity = {
        "company_name": frozen_input["company_name"],
        "as_of_date": frozen_input["as_of_date"],
        "forecast_version": forecast_version,
        "input_sha256": input_hash,
        "forecast_result_sha256": result_hash,
        "engine_version": result["engine_version"],
        "forecast_schema_version": actual_schema,
        "snapshot_schema_version": "2.0",
    }
    snapshot = {
        **identity,
        "snapshot_id": canonical_sha256(identity),
        "forecast_version": forecast_version,
        "input_document": frozen_input,
        "forecast_result": result,
    }
    # R1.2: snapshots are published artifacts too — register their anchor so a
    # snapshot's input can be audited against the same external authority.
    from publication_registry import RegistryError, register_snapshot

    try:
        register_snapshot(snapshot)
    except RegistryError as exc:
        raise ForecastInputError(
            f"snapshot creation failed: registry unavailable: {exc}"
        ) from exc
    return snapshot


def write_new_json(path: Path, data: dict[str, Any]) -> None:
    """Write once. Existing forecast history must never be overwritten."""
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        handle.write("\n")


def snapshot_schema_diagnostic(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Report historical header differences without changing frozen IDs or anchors."""
    header = snapshot.get("forecast_schema_version")
    input_schema = snapshot.get("input_document", {}).get("schema_version")
    result_schema = snapshot.get("forecast_result", {}).get("schema_version")
    known = all(isinstance(version, str) for version in (header, input_schema, result_schema))
    status = ("consistent" if header == input_schema == result_schema else "metadata_mismatch") if known else "unknown"
    return {"schema_version": "snapshot-schema-diagnostic/1",
        "status": status,
        "header_schema_version": header, "input_schema_version": input_schema,
        "result_schema_version": result_schema, "snapshot_rewritten": False}


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    for key in (
        "snapshot_schema_version",
        "snapshot_id",
        "forecast_version",
        "company_name",
        "as_of_date",
        "input_sha256",
        "forecast_result_sha256",
        "engine_version",
        "forecast_schema_version",
        "input_document",
        "forecast_result",
    ):
        require(key in snapshot, f"snapshot missing field: {key}")
    require(
        snapshot["snapshot_schema_version"] == "2.0",
        "unsupported snapshot schema version",
    )
    require(
        snapshot["forecast_schema_version"] in SUPPORTED_FORECAST_SCHEMA_VERSIONS,
        "snapshot forecast_schema_version mismatch",
    )
    require_validating_engine(
        snapshot["forecast_schema_version"], snapshot["engine_version"], "snapshot"
    )
    # R1.1: reuse the shared binding invariant instead of a local copy so the
    # snapshot path can never drift from the output validator's rule.
    verify_input_binding(snapshot)
    validate_published_forecast(snapshot["forecast_result"], snapshot["input_document"])
    expected_result_hash = canonical_sha256(snapshot["forecast_result"])
    require(
        expected_result_hash == snapshot["forecast_result_sha256"],
        "snapshot forecast result fingerprint mismatch",
    )
    require(
        snapshot["company_name"]
        == snapshot["input_document"]["company_name"]
        == snapshot["forecast_result"]["company_name"],
        "snapshot company identity mismatch",
    )
    require(
        snapshot["as_of_date"]
        == snapshot["input_document"]["as_of_date"]
        == snapshot["forecast_result"]["as_of_date"],
        "snapshot as_of_date identity mismatch",
    )
    require(
        snapshot["forecast_version"]
        == snapshot["input_document"]["forecast_version"]
        == snapshot["forecast_result"]["forecast_version"],
        "snapshot forecast_version identity mismatch",
    )
    require(
        snapshot["forecast_result"]["input_sha256"] == snapshot["input_sha256"],
        "forecast result input fingerprint mismatch",
    )
    identity = {
        key: snapshot[key]
        for key in (
            "company_name",
            "as_of_date",
            "forecast_version",
            "input_sha256",
            "forecast_result_sha256",
            "engine_version",
            "forecast_schema_version",
            "snapshot_schema_version",
        )
    }
    require(
        canonical_sha256(identity) == snapshot["snapshot_id"], "snapshot_id mismatch"
    )


def validate_actuals(
    actuals: dict[str, Any], snapshot: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    for key in (
        "actuals_schema_version",
        "company_name",
        "actuals_as_of_date",
        "currency",
        "unit",
        "sources",
        "evidence_claims",
        "actual_company_revenue",
    ):
        require(key in actuals, f"actuals missing field: {key}")
    require(
        actuals["actuals_schema_version"] == "2.0", "actuals_schema_version must be 2.0"
    )
    require(
        actuals["company_name"] == snapshot["company_name"],
        "actuals company_name does not match snapshot",
    )
    require(
        actuals["currency"] == snapshot["forecast_result"]["currency"]
        and actuals["unit"] == snapshot["forecast_result"]["unit"],
        "actuals currency/unit mismatch",
    )
    actuals_as_of = parse_iso_date(actuals["actuals_as_of_date"], "actuals_as_of_date")
    snapshot_as_of = parse_iso_date(snapshot["as_of_date"], "snapshot.as_of_date")
    require(
        actuals_as_of >= snapshot_as_of,
        "actuals_as_of_date cannot precede forecast as_of_date",
    )
    source_index = validate_sources(actuals, actuals_as_of, require_capture=True)
    claim_index = _validate_actual_claims(actuals, source_index, actuals_as_of)
    forecast_years = set(snapshot["forecast_result"]["forecast_years"])
    fiscal_month, fiscal_day = map(
        int, snapshot["forecast_result"]["fiscal_year_end"].split("-")
    )

    company_actuals = actuals["actual_company_revenue"]
    require(
        isinstance(company_actuals, dict) and company_actuals,
        "actual_company_revenue must be a non-empty object",
    )
    for year_text, record in company_actuals.items():
        require(
            year_text.isdigit() and int(year_text) in forecast_years,
            f"actual year is outside forecast horizon: {year_text}",
        )
        _validate_actual_record(
            record,
            source_index,
            claim_index,
            "actual_revenue",
            f"company:{year_text}",
            f"actual_company_revenue.{year_text}",
            actuals,
        )
        for claim_id in record["claim_ids"]:
            source = source_index[claim_index[claim_id]["source_id"]]
            require(
                parse_iso_date(source["published_date"], "actual published_date") > snapshot_as_of,
                f"actual was already published at forecast origin: {year_text}",
            )
            require(
                parse_iso_date(
                    source["published_date"], f"{source['source_id']}.published_date"
                )
                >= date(int(year_text), fiscal_month, fiscal_day),
                f"actual source predates fiscal year end: {year_text}",
            )

    segment_actuals = actuals.get("actual_segment_revenue", {})
    require(
        isinstance(segment_actuals, dict), "actual_segment_revenue must be an object"
    )
    forecast_segments = {
        segment["name"] for segment in snapshot["forecast_result"]["segments"]
    }
    for segment_name, records in segment_actuals.items():
        require(
            segment_name in forecast_segments, f"unknown actual segment: {segment_name}"
        )
        require(
            isinstance(records, dict),
            f"actual segment records must be an object: {segment_name}",
        )
        for year_text, record in records.items():
            require(
                year_text.isdigit() and int(year_text) in forecast_years,
                f"actual segment year is outside forecast horizon: {segment_name}/{year_text}",
            )
            _validate_actual_record(
                record,
                source_index,
                claim_index,
                "actual_revenue",
                f"segment:{segment_name}:{year_text}",
                f"actual_segment_revenue.{segment_name}.{year_text}",
                actuals,
            )
            for claim_id in record["claim_ids"]:
                source = source_index[claim_index[claim_id]["source_id"]]
                require(
                    parse_iso_date(source["published_date"], "actual published_date") > snapshot_as_of,
                    f"actual was already published at forecast origin: {segment_name}/{year_text}",
                )
                require(
                    parse_iso_date(
                        source["published_date"],
                        f"{source['source_id']}.published_date",
                    )
                    >= date(int(year_text), fiscal_month, fiscal_day),
                    f"actual segment source predates fiscal year end: {segment_name}/{year_text}",
                )
    return source_index


def _validate_actual_claims(
    actuals: dict[str, Any], source_index: dict[str, dict[str, Any]], as_of: date
) -> dict[str, dict[str, Any]]:
    claims = actuals["evidence_claims"]
    require(
        isinstance(claims, list) and claims,
        "actual evidence_claims must be a non-empty list",
    )
    index: dict[str, dict[str, Any]] = {}
    for position, claim in enumerate(claims):
        require(
            isinstance(claim, dict),
            f"actual evidence_claims[{position}] must be an object",
        )
        claim_id = claim.get("claim_id")
        require(
            isinstance(claim_id, str) and claim_id and claim_id not in index,
            "actual claim_id must be unique",
        )
        require(
            claim.get("source_id") in source_index,
            f"unknown actual claim source: {claim_id}",
        )
        require(
            claim.get("target_type") == "actual_revenue",
            f"actual claim target_type mismatch: {claim_id}",
        )
        require(
            claim.get("support_type") == "exact_value",
            f"actual claim must use exact_value: {claim_id}",
        )
        for field in ("target_id", "locator", "excerpt", "verified_by"):
            require(
                isinstance(claim.get(field), str) and claim[field].strip(),
                f"actual claim {claim_id}.{field} is required",
            )
        excerpt = claim["excerpt"].strip()
        require(
            10 <= len(excerpt) <= 500
            and claim.get("excerpt_sha256") == text_sha256(excerpt),
            f"actual claim excerpt/hash mismatch: {claim_id}",
        )
        require(
            isinstance(claim.get("content_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", claim["content_sha256"]),
            f"actual claim content_sha256 must be lowercase SHA-256: {claim_id}",
        )
        source_capture = source_index[claim["source_id"]].get("capture")
        require(
            isinstance(source_capture, dict),
            f"actual claim source capture is missing: {claim_id}",
        )
        require(
            claim.get("capture_receipt_sha256") == source_capture["receipt_sha256"],
            f"actual claim capture receipt mismatch: {claim_id}",
        )
        require(
            claim["content_sha256"] == source_capture["snapshot_sha256"],
            f"actual claim/source snapshot mismatch: {claim_id}",
        )
        require(
            claim.get("verification_status") == "opened_and_checked",
            f"actual claim must be opened_and_checked: {claim_id}",
        )
        verified = parse_iso_date(
            claim.get("verified_date"), f"{claim_id}.verified_date"
        )
        published = parse_iso_date(
            source_index[claim["source_id"]]["published_date"],
            f"{claim_id}.published_date",
        )
        require(
            published <= verified <= as_of,
            f"actual claim verification date is invalid: {claim_id}",
        )
        index[claim_id] = claim
    return index


def _validate_actual_record(
    record: Any,
    source_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
    target_type: str,
    target_id: str,
    field: str,
    actuals: dict[str, Any],
) -> None:
    require(isinstance(record, dict), f"{field} must be an object")
    value = finite_number(record.get("value"), f"{field}.value")
    require(value >= 0, f"{field}.value cannot be negative")
    source_ids = record.get("source_ids")
    require(
        isinstance(source_ids, list) and source_ids, f"{field}.source_ids is required"
    )
    for source_id in source_ids:
        require(source_id in source_index, f"unknown actual source_id: {source_id}")
    claim_ids = record.get("claim_ids")
    require(isinstance(claim_ids, list) and claim_ids, f"{field}.claim_ids is required")
    for claim_id in claim_ids:
        require(claim_id in claim_index, f"unknown actual claim_id: {claim_id}")
        claim = claim_index[claim_id]
        require(
            claim["target_type"] == target_type and claim["target_id"] == target_id,
            f"actual claim target mismatch: {claim_id}",
        )
        require(
            claim["source_id"] in source_ids,
            f"actual claim source is not registered on record: {claim_id}",
        )
        require(
            math.isclose(
                float(claim.get("extracted_value")), value, rel_tol=0, abs_tol=1e-9
            ),
            f"actual claim value mismatch: {claim_id}",
        )
        year = target_id.rsplit(":", 1)[-1]
        require(
            claim.get("period") == f"FY{year}",
            f"actual claim period mismatch: {claim_id}",
        )
        require(
            claim.get("unit") == f"{actuals['currency']} {actuals['unit']}",
            f"actual claim unit mismatch: {claim_id}",
        )


def _error_record(
    forecast: float, actual: float, lower: float, upper: float, scale_base: float
) -> dict[str, Any]:
    absolute_error = abs(forecast - actual)
    signed_error = None if actual == 0 else (forecast - actual) / actual
    smape_denominator = abs(forecast) + abs(actual)
    return {
        "forecast": forecast,
        "actual": actual,
        "absolute_error": absolute_error,
        "signed_error_amount": forecast - actual,
        "squared_error": (forecast - actual) ** 2,
        "signed_error": signed_error,
        "absolute_percentage_error": None
        if signed_error is None
        else abs(signed_error),
        "smape": 0.0
        if smape_denominator == 0
        else 2 * absolute_error / smape_denominator,
        "base_scaled_error": None
        if scale_base == 0
        else absolute_error / abs(scale_base),
        "within_interval": lower <= actual <= upper,
        "low_case": lower,
        "high_case": upper,
        "scenario_width": upper - lower,
    }


def _summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    absolute_errors = [float(record["absolute_error"]) for record in records]
    actual_denominator = sum(abs(float(record["actual"])) for record in records)
    signed = [
        float(record["signed_error"])
        for record in records
        if record.get("signed_error") is not None
    ]
    scaled = [
        float(record["base_scaled_error"])
        for record in records
        if record.get("base_scaled_error") is not None
    ]
    directions = [
        bool(record["direction_correct"])
        for record in records
        if record.get("direction_correct") is not None
    ]
    return {
        "observations": len(records),
        "sum_absolute_error": sum(absolute_errors),
        "sum_absolute_actual": actual_denominator,
        "bias_amount": None if not records else sum(
            float(record["forecast"]) - float(record["actual"]) for record in records
        ) / len(records),
        "rmse": None if not records else math.sqrt(sum(
            (float(record["forecast"]) - float(record["actual"])) ** 2
            for record in records
        ) / len(records)),
        "mean_scenario_width": None if not records else sum(
            float(record["high_case"]) - float(record["low_case"]) for record in records
        ) / len(records),
        "mae": None if not records else sum(absolute_errors) / len(records),
        "wape": None
        if actual_denominator == 0
        else sum(absolute_errors) / actual_denominator,
        "mean_signed_error": None if not signed else sum(signed) / len(signed),
        "mean_smape": None
        if not records
        else sum(float(record["smape"]) for record in records) / len(records),
        "mean_base_scaled_error": None if not scaled else sum(scaled) / len(scaled),
        "direction_accuracy": None
        if not directions
        else sum(directions) / len(directions),
        "interval_coverage": None
        if not records
        else sum(bool(record["within_interval"]) for record in records) / len(records),
    }


def _accuracy_record(evaluation: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "record_schema_version": "1.1",
        **{key: evaluation[key] for key in (
            "company_name", "currency", "unit", "fiscal_year_end",
            "forecast_as_of_date", "actuals_as_of_date",
        )},
        "backtest_id": evaluation["backtest_id"],
        "snapshot_id": evaluation["snapshot_id"],
        "observations": evaluation["summary"]["observations"],
        "wape": evaluation["summary"]["wape"],
        "mae": evaluation["summary"]["mae"],
        "mean_smape": evaluation["summary"]["mean_smape"],
        "sum_absolute_error": evaluation["summary"]["sum_absolute_error"],
        "sum_absolute_actual": evaluation["summary"]["sum_absolute_actual"],
        "evaluation_sha256": evaluation["evaluation_sha256"],
    }
    return {**payload, "record_sha256": canonical_sha256(payload)}


def _benchmark_diagnostics(forecast: dict[str, Any], records: dict[str, Any]) -> dict[str, Any]:
    """Use only frozen training history; scenario bounds are not quantiles."""
    history = forecast["historical_revenue"]
    values = [float(row["value"]) for row in history]
    differences = [right - left for left, right in zip(values, values[1:])]
    absolute_scale = None if not differences else sum(map(abs, differences)) / len(differences)
    square_scale = None if not differences else sum(d * d for d in differences) / len(differences)
    base = float(forecast["base_revenue"])
    growth = None
    if len(history) >= 2 and values[0] > 0:
        growth = calculate_cagr(values[0], values[-1], history[-1]["year"] - history[0]["year"])
    flat_errors = []
    growth_errors = []
    for record in records.values():
        record["mase"] = None if not absolute_scale else record["absolute_error"] / absolute_scale
        record["squared_scaled_error"] = None if not square_scale else record["squared_error"] / square_scale
        record["flat_base_forecast"] = base
        record["flat_base_absolute_error"] = abs(base - record["actual"])
        flat_errors.append(record["flat_base_absolute_error"])
        if growth is not None:
            benchmark = base * (1 + growth) ** record["horizon_years"]
            record["historical_cagr_forecast"] = benchmark
            record["historical_cagr_absolute_error"] = abs(benchmark - record["actual"])
            growth_errors.append(record["historical_cagr_absolute_error"])
    model_error = sum(row["absolute_error"] for row in records.values())
    count = len(records)
    return {
        "training_observations": len(history),
        "naive_training_mae": absolute_scale,
        "naive_training_mse": square_scale,
        "mase": None if not absolute_scale else model_error / count / absolute_scale,
        "rmsse": None if not square_scale else math.sqrt(
            sum(row["squared_error"] for row in records.values()) / count / square_scale
        ),
        "flat_base_mae": sum(flat_errors) / count,
        "mae_skill_vs_flat_base": None if sum(flat_errors) == 0 else 1 - model_error / sum(flat_errors),
        "historical_cagr_mae": None if not growth_errors else sum(growth_errors) / count,
        "mae_skill_vs_historical_cagr": None if not growth_errors or sum(growth_errors) == 0
        else 1 - model_error / sum(growth_errors),
        "scenario_coverage_interpretation": "descriptive low/high scenario coverage; no nominal probability",
    }


def evaluate_snapshot(
    snapshot: dict[str, Any], actuals: dict[str, Any]
) -> dict[str, Any]:
    validate_snapshot(snapshot)
    validate_actuals(actuals, snapshot)
    forecast = snapshot["forecast_result"]
    company_actuals = actuals["actual_company_revenue"]
    base_path = forecast["consolidated_forecast"]["base"]["annual_revenue"]
    low_path = forecast["consolidated_forecast"]["low"]["annual_revenue"]
    high_path = forecast["consolidated_forecast"]["high"]["annual_revenue"]
    base_revenue = float(forecast["base_revenue"])
    base_year = int(forecast["base_year"])

    year_results: dict[str, Any] = {}
    previous_forecast = base_revenue
    previous_actual = base_revenue
    previous_year = base_year
    ordered_years = sorted(int(year) for year in company_actuals)
    for year in ordered_years:
        year_text = str(year)
        actual = float(company_actuals[year_text]["value"])
        predicted = float(base_path[year_text])
        record = _error_record(
            predicted,
            actual,
            float(low_path[year_text]),
            float(high_path[year_text]),
            base_revenue,
        )
        if year == previous_year + 1:
            forecast_direction = (
                0
                if math.isclose(predicted, previous_forecast)
                else 1
                if predicted > previous_forecast
                else -1
            )
            actual_direction = (
                0
                if math.isclose(actual, previous_actual)
                else 1
                if actual > previous_actual
                else -1
            )
            record["direction_correct"] = forecast_direction == actual_direction
        else:
            record["direction_correct"] = None
        record["horizon_years"] = year - base_year
        record["source_ids"] = company_actuals[year_text]["source_ids"]
        record["claim_ids"] = company_actuals[year_text]["claim_ids"]
        year_results[year_text] = record
        previous_forecast = predicted
        previous_actual = actual
        previous_year = year

    latest_year = ordered_years[-1]
    latest_actual = float(company_actuals[str(latest_year)]["value"])
    latest_forecast = float(base_path[str(latest_year)])
    horizon = latest_year - base_year
    forecast_cagr = calculate_cagr(base_revenue, latest_forecast, horizon)
    actual_cagr = calculate_cagr(base_revenue, latest_actual, horizon)

    segment_results: dict[str, Any] = {}
    segment_forecasts = {segment["name"]: segment for segment in forecast["segments"]}
    for segment_name, records in actuals.get("actual_segment_revenue", {}).items():
        result_by_year: dict[str, Any] = {}
        segment = segment_forecasts[segment_name]
        for year_text, actual_record in records.items():
            predicted = float(
                segment["scenarios"]["base"].get(
                    "effective_revenue",
                    segment["scenarios"]["base"]["recognized_revenue"],
                )[year_text]
            )
            lower = float(
                segment["scenarios"]["low"].get(
                    "effective_revenue",
                    segment["scenarios"]["low"]["recognized_revenue"],
                )[year_text]
            )
            upper = float(
                segment["scenarios"]["high"].get(
                    "effective_revenue",
                    segment["scenarios"]["high"]["recognized_revenue"],
                )[year_text]
            )
            result_by_year[year_text] = _error_record(
                predicted,
                float(actual_record["value"]),
                lower,
                upper,
                float(segment["base_revenue"]),
            )
            result_by_year[year_text]["source_ids"] = actual_record["source_ids"]
            result_by_year[year_text]["claim_ids"] = actual_record["claim_ids"]
        segment_results[segment_name] = result_by_year

    company_records = list(year_results.values())
    benchmark_diagnostics = _benchmark_diagnostics(forecast, year_results)
    summary = _summarize_records(company_records)
    summary.update(
        {
            "forecast_cagr_to_latest_actual_year": forecast_cagr,
            "actual_cagr_to_latest_actual_year": actual_cagr,
            "cagr_error": None
            if forecast_cagr is None or actual_cagr is None
            else forecast_cagr - actual_cagr,
        }
    )
    segment_summaries = {
        name: _summarize_records(list(records.values()))
        for name, records in segment_results.items()
    }
    horizon_summaries = {
        str(horizon): _summarize_records(
            [record for record in company_records if record["horizon_years"] == horizon]
        )
        for horizon in sorted({record["horizon_years"] for record in company_records})
    }
    actuals_hash = canonical_sha256(actuals)
    backtest_id = canonical_sha256(
        {"snapshot_id": snapshot["snapshot_id"], "actuals_sha256": actuals_hash}
    )
    evaluation = {
        "backtest_schema_version": "2.0",
        "backtest_id": backtest_id,
        "snapshot_id": snapshot["snapshot_id"],
        "forecast_version": snapshot["forecast_version"],
        "company_name": snapshot["company_name"],
        "currency": forecast["currency"],
        "unit": forecast["unit"],
        "fiscal_year_end": forecast["fiscal_year_end"],
        "forecast_as_of_date": snapshot["as_of_date"],
        "actuals_as_of_date": actuals["actuals_as_of_date"],
        "actuals_sha256": actuals_hash,
        "nonconsecutive_actual_years": bool(
            ordered_years and ordered_years[0] != base_year + 1
        )
        or any(
            right - left != 1 for left, right in zip(ordered_years, ordered_years[1:])
        ),
        "company_year_results": year_results,
        "segment_year_results": segment_results,
        "segment_summaries": segment_summaries,
        "horizon_summaries": horizon_summaries,
        "summary": summary,
        "benchmark_diagnostics": benchmark_diagnostics,
    }
    evaluation["evaluation_sha256"] = canonical_sha256(evaluation)
    evaluation["accuracy_record"] = _accuracy_record(evaluation)
    return evaluation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create immutable revenue forecasts or evaluate them against actual revenue"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("input", type=Path)
    create.add_argument("--version", required=True)
    create.add_argument("--output", type=Path, required=True)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("snapshot", type=Path)
    evaluate.add_argument("actuals", type=Path)
    evaluate.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "create":
            data = json.loads(args.input.read_text(encoding="utf-8"))
            write_new_json(args.output, create_snapshot(data, args.version))
        else:
            snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
            actuals = json.loads(args.actuals.read_text(encoding="utf-8"))
            rendered = evaluate_snapshot(snapshot, actuals)
            if args.output:
                write_new_json(args.output, rendered)
            else:
                print(json.dumps(rendered, ensure_ascii=False, indent=2))
    except (OSError, json.JSONDecodeError, ForecastInputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
