"""Extracted from revenue_core.py during the R9 split (behavior-locked by tests/test_golden_behavior_lock.py)."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import date
from typing import Any

from contracts.constants import (
    ASSET_FACT_BASIS_REQUIRED,
    ASSET_FACT_OWNERSHIP_BASES,
    ASSERTION_STATUSES,
    DATED_CONTRIBUTION_SCHEMA_VERSION,
    DIRECTIONAL_EVIDENCE_ROLES,
    FORECAST_SCHEMA_VERSION,
    GROWTH_DRIVER_EVIDENCE_ROLES,
    MONETARY_DIMENSIONS,
    OPT_IN_SCHEMA_VERSION,
    PARAMETER_DIMENSIONS,
    PARAMETER_KINDS,
    PERIOD_EVIDENCE_SCHEMA_VERSION,
    PERIOD_FLOW_SCHEMA_VERSIONS,
    PERIOD_FLOW_TIME_BASIS,
    RESOLUTION_STATUSES,
    SCENARIOS,
    SOURCE_RANKS,
    TIME_BASES,
)
from contracts.evidence import (
    Collector,
    ForecastInputError,
    MultiValidationError,
    canonical_sha256,
    collect_mode,
    finite_number,
    parse_iso_date,
    period_year,
    require,
    text_sha256,
    validate_claim_ids,
    validate_source_capture,
    valid_source_url,
)
from asset_ownership import (
    validate_segment_geography,
    validate_segment_ownership,
)
from mine_year_operation import validate_mine_year_operation
from contracts.period_flow import validate_period_flow_fields, validate_windowed_composition
from contracts.recognition import validate_recognition_metadata
from contracts.annual_consumption import validate_annual_consumption
from forecast.calc import (
    _parse_fiscal_year,
    evaluate_derived_formula,
    parameter_values,
    sensitivity_domain_bounds,
)
from contracts.source_clock import SourceClockError, source_information_eligibility, validate_source_events
from research.coverage import validate_research_coverage
from research.drivers import validate_growth_driver_tree
from research.targets import validate_management_target_coverage
from revenue_constraints import RevenueConstraintError, validate_revenue_constraints


def validate_top_level(data: dict[str, Any]) -> tuple[list[int], date]:
    required = (
        "schema_version",
        "company_name",
        "as_of_date",
        "currency",
        "unit",
        "fiscal_year_end",
        "base_year",
        "forecast_years",
        "historical_revenue",
        "sources",
        "parameters",
        "segments",
        "reported_total_revenue_parameter_id",
        "research_coverage",
        "growth_driver_tree",
        "management_communication_coverage",
        "management_targets",
        "evidence_claims",
    )
    for key in required:
        require(key in data, f"missing required field: {key}")

    require(
        data["schema_version"]
        in (FORECAST_SCHEMA_VERSION, OPT_IN_SCHEMA_VERSION,
            PERIOD_EVIDENCE_SCHEMA_VERSION, DATED_CONTRIBUTION_SCHEMA_VERSION),
        f"schema_version must be {FORECAST_SCHEMA_VERSION}, "
        f"{OPT_IN_SCHEMA_VERSION} (opt-in), {PERIOD_EVIDENCE_SCHEMA_VERSION} "
        f"(period evidence opt-in) or {DATED_CONTRIBUTION_SCHEMA_VERSION} "
        "(dated contribution opt-in)",
    )

    require(
        isinstance(data["company_name"], str) and data["company_name"].strip(),
        "company_name is required",
    )
    as_of = parse_iso_date(data["as_of_date"], "as_of_date")
    require(
        isinstance(data["currency"], str) and data["currency"].strip(),
        "currency is required",
    )
    require(isinstance(data["unit"], str) and data["unit"].strip(), "unit is required")
    require(
        isinstance(data["fiscal_year_end"], str)
        and re.fullmatch(r"\d{2}-\d{2}", data["fiscal_year_end"]),
        "fiscal_year_end must use MM-DD",
    )
    try:
        date(2000, int(data["fiscal_year_end"][:2]), int(data["fiscal_year_end"][3:]))
    except ValueError as exc:
        raise ForecastInputError("fiscal_year_end is not a valid month-day") from exc
    require(isinstance(data["base_year"], int), "base_year must be an integer")

    years = data["forecast_years"]
    require(
        isinstance(years, list) and years, "forecast_years must be a non-empty list"
    )
    require(
        all(isinstance(year, int) for year in years),
        "forecast_years must contain integers",
    )
    require(
        years == sorted(years) and len(years) == len(set(years)),
        "forecast_years must be unique and increasing",
    )
    require(
        years[0] == data["base_year"] + 1, "forecast_years must start after base_year"
    )
    require(
        all(right - left == 1 for left, right in zip(years, years[1:])),
        "forecast_years must be consecutive",
    )
    for field in ("data_gaps", "disconfirming_indicators"):
        if field in data:
            values = data[field]
            require(isinstance(values, list), f"{field} must be a list of strings")
            require(
                all(isinstance(value, str) and value.strip() for value in values),
                f"{field} must contain non-empty strings",
            )
            require(
                len(values) == len(set(values)), f"{field} must not contain duplicates"
            )
    return years, as_of


def validate_historical_revenue(
    data: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
    parameter_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
) -> None:
    history = data["historical_revenue"]
    require(isinstance(history, list), "historical_revenue must be a list")
    pre_revenue = bool(data.get("pre_revenue", False))
    require(
        pre_revenue or len(history) >= 2,
        "historical_revenue requires at least two observations unless pre_revenue=true",
    )
    years: set[int] = set()
    normalized: list[tuple[int, float]] = []
    for position, record in enumerate(history):
        require(
            isinstance(record, dict),
            f"historical_revenue[{position}] must be an object",
        )
        year = record.get("year")
        require(
            isinstance(year, int),
            f"historical_revenue[{position}].year must be an integer",
        )
        require(
            year <= data["base_year"],
            f"historical revenue year cannot exceed base_year: {year}",
        )
        require(year not in years, f"duplicate historical revenue year: {year}")
        years.add(year)
        value = finite_number(
            record.get("value"), f"historical_revenue[{position}].value"
        )
        require(value >= 0, f"historical revenue cannot be negative: {year}")
        source_ids = record.get("source_ids")
        require(
            isinstance(source_ids, list) and source_ids,
            f"historical_revenue[{position}].source_ids is required",
        )
        for source_id in source_ids:
            require(
                source_id in source_index,
                f"unknown historical revenue source_id: {source_id}",
            )
        claims = validate_claim_ids(
            record.get("claim_ids"),
            claim_index,
            "historical_revenue",
            f"historical_revenue:{year}",
            f"historical_revenue[{position}]",
            "exact_value",
        )
        require(
            any(
                math.isclose(float(extracted), value, rel_tol=0, abs_tol=1e-9)
                for claim in claims
                if isinstance(
                    (extracted := claim.get("extracted_value")), (int, float, str)
                )
            ),
            f"historical revenue claim value mismatch: {year}",
        )
        require(
            all(claim.get("period") == f"FY{year}" for claim in claims),
            f"historical revenue claim period mismatch: {year}",
        )
        require(
            all(
                claim.get("unit") == f"{data['currency']} {data['unit']}"
                for claim in claims
            ),
            f"historical revenue claim unit mismatch: {year}",
        )
        normalized.append((year, value))
    require(
        normalized == sorted(normalized), "historical_revenue must be ordered by year"
    )
    require(
        all(right[0] - left[0] == 1 for left, right in zip(normalized, normalized[1:])),
        "historical_revenue years must be consecutive",
    )
    total = float(parameter_index[data["reported_total_revenue_parameter_id"]]["value"])
    base_records = [value for year, value in normalized if year == data["base_year"]]
    if pre_revenue and not normalized:
        require(
            math.isclose(total, 0.0),
            "pre-revenue company without history must use zero reported base revenue",
        )
        return
    require(
        len(base_records) == 1,
        "historical_revenue must contain exactly one base_year observation",
    )
    tolerance = max(1.0, abs(total)) * float(data.get("reconciliation_tolerance", 1e-6))
    require(
        abs(base_records[0] - total) <= tolerance,
        "historical base-year revenue does not match reported total revenue",
    )


def validate_sources(
    data: dict[str, Any],
    as_of: date,
    *,
    require_capture: bool = False,
) -> dict[str, dict[str, Any]]:
    sources = data["sources"]
    require(isinstance(sources, list) and sources, "sources must be a non-empty list")
    index: dict[str, dict[str, Any]] = {}
    for position, source in enumerate(sources):
        prefix = f"sources[{position}]"
        require(isinstance(source, dict), f"{prefix} must be an object")
        source_id = source.get("source_id")
        require(
            isinstance(source_id, str) and source_id.strip(),
            f"{prefix}.source_id is required",
        )
        require(source_id not in index, f"duplicate source_id: {source_id}")
        source_type = source.get("source_type")
        require(
            source_type in SOURCE_RANKS,
            f"unsupported source_type for {source_id}: {source_type}",
        )
        require(
            valid_source_url(source.get("url")),
            f"invalid, search-page, or placeholder URL for {source_id}",
        )
        for field in ("title", "publisher", "page_or_section"):
            require(
                isinstance(source.get(field), str) and source[field].strip(),
                f"{source_id}.{field} is required",
            )
        try:
            information = source_information_eligibility(source, as_of)
        except SourceClockError as exc:
            raise ForecastInputError(f"{source_id}: {exc}") from exc
        if source.get("accessed_date") is not None:
            parse_iso_date(source["accessed_date"], f"{source_id}.accessed_date")
        if require_capture:
            validate_source_capture(source, as_of, information_eligibility=information)
        enriched = dict(source)
        enriched["source_rank"] = SOURCE_RANKS[source_type]
        index[source_id] = enriched
    return index


def validate_parameter_basis(parameter_id: str, basis: Any) -> None:
    """ZR-602: validate an additive asset-fact ``basis`` key.

    When a parameter carries ``basis`` it must be a complete, valid basis:
    ownership_basis from the enum, non-empty reporting_standard, and an ISO
    measurement_date. Half-baked or invalid basis fails closed; a missing
    basis (None) is valid (additive contract, legacy parameters unaffected).
    """
    if basis is None:
        return
    require(isinstance(basis, dict), f"{parameter_id}.basis must be an object")
    for basis_field in ASSET_FACT_BASIS_REQUIRED:
        require(
            basis_field in basis,
            f"{parameter_id}.basis.{basis_field} is required",
        )
    require(
        isinstance(basis["ownership_basis"], str)
        and basis["ownership_basis"] in ASSET_FACT_OWNERSHIP_BASES,
        f"unsupported ownership_basis for {parameter_id}: {basis['ownership_basis']}",
    )
    require(
        isinstance(basis["reporting_standard"], str)
        and basis["reporting_standard"].strip(),
        f"{parameter_id}.basis.reporting_standard is required",
    )
    parse_iso_date(basis["measurement_date"], f"{parameter_id}.basis.measurement_date")


def _validate_parameter_status_fields(
    parameter_id: str, parameter: dict[str, Any]
) -> None:
    """ZR-604: validate additive assertion_status / resolution_status keys.

    ``None`` (key absent) passes — both keys are additive.
    """
    assertion = parameter.get("assertion_status")
    if assertion is not None:
        require(
            assertion in ASSERTION_STATUSES,
            f"unsupported assertion_status for {parameter_id}: {assertion}",
        )
    resolution = parameter.get("resolution_status")
    if resolution is not None:
        require(
            resolution in RESOLUTION_STATUSES,
            f"unsupported resolution_status for {parameter_id}: {resolution}",
        )


def _validate_conflict_resolution(
    group: list[dict[str, Any]], key: tuple[str, ...]
) -> None:
    """ZR-604: dual-assertion conflict resolution.

    When parameters with the same semantic key carry different values,
    ALL must carry ``resolution_status`` and at most one is ``accepted``
    — otherwise the original hard-fail applies (no silent overwrite).
    """
    all_resolved = all("resolution_status" in item for item in group)
    if not all_resolved:
        ids = ", ".join(item["parameter_id"] for item in group)
        raise ForecastInputError(
            f"unresolved conflicting parameters for {key}: {ids}"
        )
    accepted = [
        item for item in group if item["resolution_status"] == "accepted"
    ]
    if len(accepted) > 1:
        ids = ", ".join(item["parameter_id"] for item in accepted)
        raise ForecastInputError(
            f"multiple accepted assertions for {key}: {ids}"
        )


def validate_parameters(
    data: dict[str, Any], source_index: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    parameters = data["parameters"]
    require(
        isinstance(parameters, list) and parameters,
        "parameters must be a non-empty list",
    )
    index: dict[str, dict[str, Any]] = {}
    semantic_groups: dict[tuple[str, ...], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    # M3-FLOW: the dated-flow basis exists only in the period-flow schema
    # family (3.9, 3.10). On 3.7/3.8 (and any older pin) period_flow fails
    # closed, and period dates on a non-flow basis are rejected in every
    # schema so the new fields can never ride along on legacy documents.
    allowed_time_bases = (
        TIME_BASES | {PERIOD_FLOW_TIME_BASIS}
        if data["schema_version"] in PERIOD_FLOW_SCHEMA_VERSIONS
        else TIME_BASES
    )

    for position, parameter in enumerate(parameters):
        prefix = f"parameters[{position}]"
        require(isinstance(parameter, dict), f"{prefix} must be an object")
        parameter_id = parameter.get("parameter_id")
        require(
            isinstance(parameter_id, str) and parameter_id.strip(),
            f"{prefix}.parameter_id is required",
        )
        require(parameter_id not in index, f"duplicate parameter_id: {parameter_id}")
        kind = parameter.get("kind")
        require(
            kind in PARAMETER_KINDS,
            f"unsupported parameter kind for {parameter_id}: {kind}",
        )
        value = finite_number(parameter.get("value"), f"{parameter_id}.value")
        sensitivity_domain_bounds(parameter)
        for field in ("unit", "period", "definition"):
            require(
                isinstance(parameter.get(field), str) and parameter[field].strip(),
                f"{parameter_id}.{field} is required",
            )
        period_year(parameter["period"], f"{parameter_id}.period")
        dimension = parameter.get("dimension")
        require(
            dimension in PARAMETER_DIMENSIONS,
            f"unsupported dimension for {parameter_id}: {dimension}",
        )
        time_basis = parameter.get("time_basis")
        require(
            time_basis in allowed_time_bases,
            f"unsupported time_basis for {parameter_id}: {time_basis}",
        )
        if "period_start" in parameter or "period_end" in parameter:
            require(
                time_basis == PERIOD_FLOW_TIME_BASIS,
                f"{parameter_id}: period_start/period_end require "
                f"time_basis {PERIOD_FLOW_TIME_BASIS}",
            )
        if time_basis == PERIOD_FLOW_TIME_BASIS:
            validate_period_flow_fields(
                parameter_id, parameter, data["fiscal_year_end"],
                schema_version=data["schema_version"],
            )
        if dimension in MONETARY_DIMENSIONS:
            require(
                parameter.get("currency") == data["currency"],
                f"currency mismatch for {parameter_id}",
            )
            require(
                parameter.get("scale") == data["unit"],
                f"scale mismatch for {parameter_id}",
            )
        else:
            require(
                parameter.get("currency") in (None, ""),
                f"non-monetary parameter {parameter_id} cannot carry currency",
            )

        source_ids = parameter.get("source_ids", [])
        require(
            isinstance(source_ids, list), f"{parameter_id}.source_ids must be a list"
        )
        require(
            len(source_ids) == len(set(source_ids)),
            f"duplicate source reference in {parameter_id}",
        )
        for source_id in source_ids:
            require(
                source_id in source_index,
                f"unknown source_id {source_id} referenced by {parameter_id}",
            )

        # ZR-602: asset fact basis — additive key; when present it must be a
        # complete, valid basis (ownership basis / reporting standard /
        # measurement date). Half-baked or invalid basis fails closed.
        validate_parameter_basis(parameter_id, parameter.get("basis"))

        # ZR-604: additive assertion_status / resolution_status — validated
        # when present; absent keys unaffected (legacy compatible).
        _validate_parameter_status_fields(parameter_id, parameter)

        if kind in {"reported_fact", "management_guidance"}:
            require(
                bool(source_ids), f"{kind} {parameter_id} requires at least one source"
            )
        if kind in {"analyst_assumption", "scenario_stress"}:
            require(
                isinstance(parameter.get("rationale"), str)
                and parameter["rationale"].strip(),
                f"{kind} {parameter_id} requires rationale",
            )
        if kind == "derived_fact":
            require(
                isinstance(parameter.get("formula"), str)
                and parameter["formula"].strip(),
                f"derived_fact {parameter_id} requires formula",
            )
            inputs = parameter.get("input_parameter_ids")
            require(
                isinstance(inputs, list) and inputs,
                f"derived_fact {parameter_id} requires input_parameter_ids",
            )

        normalized = dict(parameter)
        normalized["value"] = value
        index[parameter_id] = normalized
        scenario = str(parameter.get("scenario", "none"))
        key: tuple[str, ...] = (
            parameter["definition"].strip().lower(),
            parameter["period"],
            parameter["unit"],
            scenario,
        )
        if data.get("schema_version") in PERIOD_FLOW_SCHEMA_VERSIONS:
            # FY labels alone do not identify a fact: H1, H2 and full-year
            # amounts are distinct observations, even with the same business
            # definition. Conflict resolution applies within the same window.
            key += (
                parameter.get("time_basis", "annual"),
                parameter.get("period_start", ""),
                parameter.get("period_end", ""),
            )
        semantic_groups[key].append(normalized)

    for parameter_id, parameter in index.items():
        if parameter["kind"] == "derived_fact":
            for input_id in parameter["input_parameter_ids"]:
                require(
                    input_id in index,
                    f"unknown input_parameter_id {input_id} referenced by {parameter_id}",
                )
                require(
                    input_id != parameter_id,
                    f"derived parameter {parameter_id} cannot reference itself",
                )
            if (
                data["schema_version"] == DATED_CONTRIBUTION_SCHEMA_VERSION
                and parameter.get("time_basis") in {"annual", PERIOD_FLOW_TIME_BASIS}
            ):
                validate_windowed_composition(
                    parameter_id, parameter, index, data["fiscal_year_end"]
                )

    resolved: dict[str, float] = {}

    def resolve_value(parameter_id: str, stack: set[str]) -> float:
        require(
            parameter_id not in stack,
            f"derived parameter cycle detected at {parameter_id}",
        )
        if parameter_id in resolved:
            return resolved[parameter_id]
        parameter = index[parameter_id]
        if parameter["kind"] != "derived_fact":
            resolved[parameter_id] = float(parameter["value"])
            return resolved[parameter_id]
        inputs = [
            resolve_value(input_id, stack | {parameter_id})
            for input_id in parameter["input_parameter_ids"]
        ]
        calculated = evaluate_derived_formula(parameter["formula"], inputs)
        tolerance = max(1.0, abs(calculated)) * float(
            data.get("reconciliation_tolerance", 1e-6)
        )
        require(
            math.isclose(
                float(parameter["value"]), calculated, rel_tol=0, abs_tol=tolerance
            ),
            f"derived_fact value mismatch for {parameter_id}",
        )
        resolved[parameter_id] = calculated
        return calculated

    for parameter_id in index:
        resolve_value(parameter_id, set())

    for key, group in semantic_groups.items():
        if len(group) <= 1:
            continue
        values = {item["value"] for item in group}
        if len(values) > 1:
            _validate_conflict_resolution(group, key)
    return index


def validate_evidence_claims(
    data: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
    parameter_index: dict[str, dict[str, Any]],
    as_of: date,
) -> dict[str, dict[str, Any]]:
    claims = data.get("evidence_claims")
    require(
        isinstance(claims, list) and claims, "evidence_claims must be a non-empty list"
    )
    index: dict[str, dict[str, Any]] = {}
    allowed_target_types = {
        "parameter",
        "historical_revenue",
        "recognition_policy",
        "scenario_probability",
        "management_target",
        "growth_driver",
    }
    allowed_support_types = {"exact_value", "rationale_support", "policy_support"}
    assert isinstance(claims, list)  # narrow; require() above enforced
    for position, claim in enumerate(claims):
        prefix = f"evidence_claims[{position}]"
        require(isinstance(claim, dict), f"{prefix} must be an object")
        claim_id = claim.get("claim_id")
        require(
            isinstance(claim_id, str) and claim_id.strip(),
            f"{prefix}.claim_id is required",
        )
        require(claim_id not in index, f"duplicate claim_id: {claim_id}")
        source_id = claim.get("source_id")
        require(source_id in source_index, f"unknown claim source_id: {source_id}")
        target_type = claim.get("target_type")
        support_type = claim.get("support_type")
        require(
            target_type in allowed_target_types,
            f"unsupported claim target_type for {claim_id}: {target_type}",
        )
        require(
            support_type in allowed_support_types,
            f"unsupported claim support_type for {claim_id}: {support_type}",
        )
        target_id = claim.get("target_id")
        require(
            isinstance(target_id, str) and target_id.strip(),
            f"{claim_id}.target_id is required",
        )
        for field in ("locator", "excerpt", "verified_by"):
            require(
                isinstance(claim.get(field), str) and claim[field].strip(),
                f"{claim_id}.{field} is required",
            )
        excerpt = claim["excerpt"].strip()
        require(
            10 <= len(excerpt) <= 500,
            f"{claim_id}.excerpt must contain 10-500 characters",
        )
        require(
            claim.get("excerpt_sha256") == text_sha256(excerpt),
            f"claim excerpt hash mismatch: {claim_id}",
        )
        require(
            isinstance(claim.get("content_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", claim["content_sha256"]),
            f"{claim_id}.content_sha256 must be lowercase SHA-256",
        )
        require(
            claim.get("verification_status") == "opened_and_checked",
            f"claim {claim_id} must be opened_and_checked",
        )
        source_capture = source_index[source_id].get("capture")
        if data["schema_version"] in (
            FORECAST_SCHEMA_VERSION,
            OPT_IN_SCHEMA_VERSION,
            PERIOD_EVIDENCE_SCHEMA_VERSION,
            DATED_CONTRIBUTION_SCHEMA_VERSION,
        ):
            require(
                isinstance(source_capture, dict),
                f"claim source capture is missing: {claim_id}",
            )
            assert isinstance(source_capture, dict)  # narrow; require() enforced
            require(
                claim.get("capture_receipt_sha256") == source_capture["receipt_sha256"],
                f"claim capture receipt mismatch: {claim_id}",
            )
            require(
                claim["content_sha256"] == source_capture["snapshot_sha256"],
                f"claim/source snapshot mismatch: {claim_id}",
            )
        verified_date = parse_iso_date(
            claim.get("verified_date"), f"{claim_id}.verified_date"
        )
        try:
            information = source_information_eligibility(source_index[source_id], as_of)
            validate_source_events(eligibility=information,
                capture_date=source_capture.get("captured_date") if isinstance(source_capture, dict) else None,
                claim_verified_date=verified_date.isoformat())
        except SourceClockError as exc:
            raise ForecastInputError(f"{claim_id}: {exc}") from exc

        # R6-RF-INPUT I3: additive evidence role. Optional; when present it
        # must be a known role consistent with the support type and the
        # presence/absence of a numeric value.
        evidence_role = claim.get("evidence_role")
        if evidence_role is not None:
            require(
                evidence_role in GROWTH_DRIVER_EVIDENCE_ROLES,
                f"unsupported evidence_role for {claim_id}: {evidence_role}",
            )
            factual_history = (
                evidence_role == "history_base" and support_type == "exact_value" and
                (target_type == "historical_revenue" or
                 (target_type == "parameter" and parameter_index.get(target_id, {}).get("kind") == "reported_fact"))
            )
            if evidence_role in DIRECTIONAL_EVIDENCE_ROLES and not factual_history:
                require(
                    claim.get("extracted_value") is None,
                    f"directional evidence_role {evidence_role} cannot carry extracted_value: {claim_id}",
                )
            if evidence_role == "value_range":
                require(
                    support_type == "exact_value"
                    and claim.get("extracted_value") is not None,
                    f"value_range evidence_role requires an exact value claim: {claim_id}",
                )
            if evidence_role == "recognition_policy":
                require(
                    support_type == "policy_support",
                    f"recognition_policy evidence_role requires policy_support: {claim_id}",
                )

        if target_type == "parameter":
            require(
                target_id in parameter_index,
                f"unknown claim parameter target: {target_id}",
            )
            parameter = parameter_index[target_id]
            require(
                source_id in parameter.get("source_ids", []),
                f"claim source {source_id} is not registered on parameter {target_id}",
            )
            if support_type == "exact_value":
                extracted = finite_number(
                    claim.get("extracted_value"), f"{claim_id}.extracted_value"
                )
                require(
                    math.isclose(
                        extracted, float(parameter["value"]), rel_tol=0, abs_tol=1e-9
                    ),
                    f"claim value mismatch for parameter {target_id}",
                )
                require(
                    claim.get("unit") == parameter["unit"],
                    f"claim unit mismatch for parameter {target_id}",
                )
                require(
                    claim.get("period") == parameter["period"],
                    f"claim period mismatch for parameter {target_id}",
                )
        index[claim_id] = dict(claim)

    for parameter_id, parameter in parameter_index.items():
        claim_ids = parameter.get("claim_ids", [])
        require(isinstance(claim_ids, list), f"{parameter_id}.claim_ids must be a list")
        require(
            len(claim_ids) == len(set(claim_ids)),
            f"duplicate claim reference in {parameter_id}",
        )
        linked: list[dict[str, Any]] = []
        for claim_id in claim_ids:
            require(
                claim_id in index,
                f"unknown claim_id {claim_id} referenced by {parameter_id}",
            )
            claim = index[claim_id]
            require(
                claim["target_type"] == "parameter"
                and claim["target_id"] == parameter_id,
                f"claim {claim_id} does not support parameter {parameter_id}",
            )
            linked.append(claim)
        if parameter["kind"] in {"reported_fact", "management_guidance"}:
            require(
                any(claim["support_type"] == "exact_value" for claim in linked),
                f"{parameter['kind']} {parameter_id} requires an exact-value claim",
            )
        if parameter["kind"] in {
            "analyst_assumption",
            "scenario_stress",
        } and parameter.get("source_ids"):
            require(
                any(c["support_type"] == "rationale_support" for c in linked),
                f"source-linked assumption {parameter_id} requires a rationale-support claim",
            )
            # A historical base is a fact about the past; alone it never
            # supports a future assumption's mechanism or range.
            roled = [c for c in linked if c.get("evidence_role")]
            if roled:
                require(
                    any(c.get("evidence_role") != "history_base" for c in roled),
                    f"history_base claims alone cannot support assumption {parameter_id}",
                )
            require(
                all(c.get("evidence_role") != "counterevidence" for c in linked),
                f"counterevidence claim cannot support parameter {parameter_id}",
            )
    return index


def validate_scenario_probabilities(
    data: dict[str, Any], validated: dict[str, Any]
) -> dict[str, float] | None:
    probabilities = data.get("scenario_probabilities")
    if probabilities is None:
        return None
    require(
        isinstance(probabilities, dict) and set(probabilities) == set(SCENARIOS),
        "scenario_probabilities must contain low/base/high",
    )
    normalized: dict[str, float] = {}
    for scenario in SCENARIOS:
        value = finite_number(
            probabilities[scenario], f"scenario_probabilities.{scenario}"
        )
        require(value >= 0, "scenario probabilities must be non-negative")
        normalized[scenario] = value
    require(
        math.isclose(sum(normalized.values()), 1.0, rel_tol=0, abs_tol=1e-9),
        "scenario probabilities must sum to 1",
    )
    require(
        isinstance(data.get("probability_rationale"), str)
        and data["probability_rationale"].strip(),
        "scenario probabilities require probability_rationale",
    )
    claims = validate_claim_ids(
        data.get("probability_claim_ids"),
        validated["claim_index"],
        "scenario_probability",
        "scenario_probability",
        "scenario probabilities",
        "rationale_support",
    )
    data["probability_source_ids"] = sorted({claim["source_id"] for claim in claims})
    return normalized


def validate_historical_accuracy_records(
    data: dict[str, Any],
) -> tuple[float | None, int]:
    records = data.get("historical_accuracy_records", [])
    require(isinstance(records, list), "historical_accuracy_records must be a list")
    total_error = 0.0
    total_actual = 0.0
    observations = 0
    ids: set[str] = set()
    origins: set[str] = set()
    snapshots: set[str] = set()
    for record in records:
        require(
            isinstance(record, dict), "historical accuracy record must be an object"
        )
        require(
            record.get("record_schema_version") in {"1.0", "1.1"},
            "unsupported historical accuracy record schema",
        )
        backtest_id = record.get("backtest_id")
        require(
            isinstance(backtest_id, str) and backtest_id and backtest_id not in ids,
            "historical accuracy backtest_id must be unique",
        )
        ids.add(backtest_id)
        provided_hash = record.get("record_sha256")
        payload = {
            key: value for key, value in record.items() if key != "record_sha256"
        }
        require(
            provided_hash == canonical_sha256(payload),
            f"historical accuracy record hash mismatch: {backtest_id}",
        )
        count = record.get("observations")
        require(
            isinstance(count, int) and not isinstance(count, bool) and count > 0,
            f"historical accuracy observations must be positive: {backtest_id}",
        )
        wape = record.get("wape")
        if wape is not None:
            value = finite_number(wape, f"historical accuracy WAPE {backtest_id}")
            require(
                value >= 0,
                f"historical accuracy WAPE cannot be negative: {backtest_id}",
            )
        # Legacy summaries have no identity, availability date or WAPE denominator.
        # They remain readable but cannot establish point-in-time forecast skill.
        if record["record_schema_version"] == "1.0":
            continue
        for field in ("backtest_id", "snapshot_id", "evaluation_sha256"):
            identifier = record.get(field)
            require(
                isinstance(identifier, str) and re.fullmatch(r"[0-9a-f]{64}", identifier) is not None,
                f"historical accuracy {field} must be a 64-character lowercase hex identifier: {backtest_id}",
            )
        for field in ("company_name", "currency", "unit", "fiscal_year_end"):
            require(record.get(field) == data.get(field) and field in data,
                    f"historical accuracy {field} mismatch: {backtest_id}")
        origin = parse_iso_date(record.get("forecast_as_of_date"), "historical forecast_as_of_date")
        available = parse_iso_date(record.get("actuals_as_of_date"), "historical actuals_as_of_date")
        cutoff = parse_iso_date(data.get("as_of_date"), "as_of_date")
        require(origin < available <= cutoff,
                f"historical accuracy future information leak: {backtest_id}")
        origin_key = origin.isoformat()
        require(origin_key not in origins,
                f"duplicate historical forecast origin: {origin_key}")
        origins.add(origin_key)
        snapshot_id = record["snapshot_id"]
        require(snapshot_id not in snapshots,
                f"duplicate historical forecast snapshot: {snapshot_id}")
        snapshots.add(snapshot_id)
        numerator = finite_number(record.get("sum_absolute_error"), "sum_absolute_error")
        denominator = finite_number(record.get("sum_absolute_actual"), "sum_absolute_actual")
        require(numerator >= 0 and denominator >= 0, "historical error totals must be non-negative")
        expected = None if denominator == 0 else numerator / denominator
        require((expected is None and wape is None) or (
            expected is not None and wape is not None
            and math.isclose(float(wape), expected, rel_tol=1e-9, abs_tol=1e-12)
        ), f"historical accuracy WAPE totals mismatch: {backtest_id}")
        mae = finite_number(record.get("mae"), "historical accuracy MAE")
        require(math.isclose(mae * count, numerator, rel_tol=1e-9, abs_tol=1e-9),
                f"historical accuracy MAE totals mismatch: {backtest_id}")
        total_error += numerator
        total_actual += denominator
        observations += count
    return (None if total_actual == 0 else total_error / total_actual, observations)


def validate_source_coverage(
    data: dict[str, Any],
    parameter_index: dict[str, dict[str, Any]],
    source_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Audit whether each forecast-year parameter has source coverage.

    Returns a list of coverage gaps: parameters whose forecast year exceeds
    the coverage horizon of their referenced sources.
    """
    gaps: list[dict[str, Any]] = []
    for parameter_id, parameter in parameter_index.items():
        period_str = parameter.get("period", "")
        year = None
        if period_str.startswith("FY") and len(period_str) == 6:
            try:
                year = int(period_str[2:])
            except ValueError:
                pass
        if year is None:
            continue
        scenario = parameter.get("scenario")
        if scenario not in SCENARIOS:
            continue
        for source_id in parameter.get("source_ids", []):
            source = source_index.get(source_id)
            if source is None:
                continue
            covers_until = source.get("covers_until")
            if covers_until is None:
                continue
            until_year = _parse_fiscal_year(covers_until)
            if until_year is not None and year > until_year:
                gaps.append(
                    {
                        "parameter_id": parameter_id,
                        "forecast_year": year,
                        "source_id": source_id,
                        "covers_until": covers_until,
                    }
                )
    return gaps


def validate_base_reconciliation(
    data: dict[str, Any], parameter_index: dict[str, dict[str, Any]]
) -> None:
    total_id = data["reported_total_revenue_parameter_id"]
    require(
        total_id in parameter_index,
        f"unknown reported_total_revenue_parameter_id: {total_id}",
    )
    total_parameter = parameter_index[total_id]
    require(
        total_parameter["kind"] in {"reported_fact", "derived_fact"},
        "reported total revenue must be a fact",
    )
    require(
        total_parameter["dimension"] == "revenue",
        "reported total revenue must use revenue dimension",
    )
    require(
        period_year(total_parameter["period"], f"{total_id}.period")
        == data["base_year"],
        "reported total revenue must use base year",
    )
    total = float(total_parameter["value"])

    segments = data["segments"]
    require(
        isinstance(segments, list) and segments, "segments must be a non-empty list"
    )
    names: set[str] = set()
    segment_total = 0.0
    for position, segment in enumerate(segments):
        require(isinstance(segment, dict), f"segments[{position}] must be an object")
        name = segment.get("name")
        require(
            isinstance(name, str) and name.strip(),
            f"segments[{position}].name is required",
        )
        require(name not in names, f"duplicate segment name: {name}")
        names.add(name)
        base_id = segment.get("base_revenue_parameter_id")
        require(
            base_id in parameter_index,
            f"unknown base_revenue_parameter_id for {name}: {base_id}",
        )
        base_parameter = parameter_index[base_id]
        require(
            base_parameter["dimension"] == "revenue",
            f"base revenue must use revenue dimension for {name}",
        )
        require(
            period_year(base_parameter["period"], f"{base_id}.period")
            == data["base_year"],
            f"base revenue must use base year for {name}",
        )
        require(
            base_parameter["value"] >= 0, f"base revenue cannot be negative for {name}"
        )
        segment_total += float(base_parameter["value"])

        # ZR-603: additive ownership timeline / geography keys on segments —
        # validated when present; absent keys unaffected (legacy compatible).
        validate_segment_ownership(name, segment.get("ownership"))
        validate_segment_geography(name, segment.get("geography"))

    adjustment_ids = data.get("base_adjustment_parameter_ids", [])
    require(
        isinstance(adjustment_ids, list), "base_adjustment_parameter_ids must be a list"
    )
    require(
        len(adjustment_ids) == len(set(adjustment_ids)),
        "duplicate base_adjustment_parameter_id",
    )
    for parameter_id in adjustment_ids:
        require(
            parameter_id in parameter_index,
            f"unknown base_adjustment_parameter_id: {parameter_id}",
        )
        require(
            parameter_index[parameter_id]["dimension"] == "revenue",
            f"base adjustment must use revenue dimension: {parameter_id}",
        )
    adjustment_total = sum(parameter_values(parameter_index, adjustment_ids))
    tolerance = finite_number(
        data.get("reconciliation_tolerance", 1e-6), "reconciliation_tolerance"
    )
    require(tolerance >= 0, "reconciliation_tolerance cannot be negative")
    difference = segment_total + adjustment_total - total
    allowed = max(1.0, abs(total)) * tolerance
    require(
        abs(difference) <= allowed,
        f"base revenue does not reconcile: segments+adjustments={segment_total + adjustment_total}, reported={total}",
    )


def validate_operating_units(data: dict[str, Any]) -> list[dict[str, Any]]:
    """ZR-711: additive ``operating_units`` key (schema 3.8 opt-in).

    Each entry must be a complete mine-year operation (ZR-605 seven-field
    contract — fail-closed on gaps, never defaults). An absent key passes
    (additive; 3.7 documents are unaffected).
    """
    units = data.get("operating_units")
    if units is None:
        return []
    require(isinstance(units, list), "operating_units must be a list")
    return [vars(validate_mine_year_operation(unit)) for unit in units]


def _validate_optional_operating_research(data, parameter_index, claim_index):
    if data.get("operating_research") is not None:
        from research.evidence_roles import analyze_operating_research
        return analyze_operating_research(data, {"parameter_index": parameter_index, "claim_index": claim_index})
    return None


def validate_recognition_contracts(data: dict[str, Any], source_index: dict[str, dict[str, Any]], claim_index: dict[str, dict[str, Any]]) -> None:
    # Legacy structural/draft validation accepts an omitted recognition
    # contract; the forecast execution layer still requires it. Once authors
    # supply metadata, validate its structure before any DAG dependency walker
    # indexes timing-specific fields. Do not invent carry-in defaults.
    for segment in data["segments"]:
        if "recognition" in segment:
            validate_recognition_metadata(segment, source_index, claim_index)


def validate_document(
    data: dict[str, Any], *, collector: Collector | None = None
) -> dict[str, Any]:
    """Validate and return indexes used by the forecast engine.

    With ``collector`` set, gates append violations instead of failing fast and a
    :class:`~contracts.evidence.MultiValidationError` is raised at the end
    carrying every collected violation. Collection is best-effort: a gate that
    crashes on bad downstream data is recorded, and dependent later gates are
    skipped. The default path (``collector=None``) is unchanged.
    """
    if collector is None:
        years, as_of = validate_top_level(data)
        source_index = validate_sources(data, as_of, require_capture=True)
        parameter_index = validate_parameters(data, source_index)
        validate_annual_consumption(data, parameter_index)
        source_coverage_gaps = validate_source_coverage(
            data, parameter_index, source_index
        )
        if source_coverage_gaps:
            gap = source_coverage_gaps[0]
            raise ForecastInputError(
                f"source {gap['source_id']} covers only until {gap['covers_until']} "
                f"but parameter {gap['parameter_id']} requires FY{gap['forecast_year']}"
            )
        claim_index = validate_evidence_claims(
            data, source_index, parameter_index, as_of
        )
        validate_historical_revenue(data, source_index, parameter_index, claim_index)
        validate_base_reconciliation(data, parameter_index)
        validate_operating_units(data)
        _validate_optional_operating_research(data, parameter_index, claim_index)
        try:
            revenue_constraints = validate_revenue_constraints(
                data.get("revenue_constraints", []),
                [
                    segment.get("name")
                    for segment in data.get("segments", [])
                    if isinstance(segment, dict)
                ],
                parameter_index,
                years,
            )
        except RevenueConstraintError as exc:
            raise ForecastInputError(str(exc)) from exc
        research_coverage = validate_research_coverage(
            data, source_index, parameter_index
        )
        validate_recognition_contracts(data, source_index, claim_index)
        growth_driver_tree = validate_growth_driver_tree(
            data, source_index, parameter_index, claim_index
        )
        management_target_coverage = validate_management_target_coverage(
            data, source_index, parameter_index, claim_index, as_of
        )
        return {
            "years": years,
            "as_of_date": as_of,
            "source_index": source_index,
            "parameter_index": parameter_index,
            "claim_index": claim_index,
            "revenue_constraints": revenue_constraints,
            "research_coverage": research_coverage,
            "growth_driver_tree": growth_driver_tree,
            "management_target_coverage": management_target_coverage,
        }

    with collect_mode(collector):
        top = _run_gate(collector, "top_level", validate_top_level, data)
        if top is None:
            raise MultiValidationError(collector.errors)
        years, as_of = top
        source_index = _run_gate(
            collector, "sources", validate_sources, data, as_of, require_capture=True
        )
        if source_index is None:
            raise MultiValidationError(collector.errors)
        parameter_index = _run_gate(
            collector, "parameters", validate_parameters, data, source_index
        )
        if parameter_index is None:
            raise MultiValidationError(collector.errors)
        _run_gate(collector, "annual_consumption", validate_annual_consumption,
                  data, parameter_index)
        collector.gate = "source_coverage"
        try:
            for gap in validate_source_coverage(data, parameter_index, source_index):
                collector.add(
                    f"source {gap['source_id']} covers only until {gap['covers_until']} "
                    f"but parameter {gap['parameter_id']} requires FY{gap['forecast_year']}"
                )
        except (
            Exception
        ) as exc:  # best-effort collect-all must not abort the whole pass
            collector.add(f"gate could not complete: {type(exc).__name__}: {exc}")
        claim_index = _run_gate(
            collector,
            "evidence_claims",
            validate_evidence_claims,
            data,
            source_index,
            parameter_index,
            as_of,
        )
        if claim_index is None:
            raise MultiValidationError(collector.errors)
        _run_gate(
            collector,
            "historical_revenue",
            validate_historical_revenue,
            data,
            source_index,
            parameter_index,
            claim_index,
        )
        _run_gate(
            collector, "operating_units", validate_operating_units, data
        )
        _run_gate(collector, "operating_research", _validate_optional_operating_research,
                  data, parameter_index, claim_index)
        _run_gate(
            collector,
            "base_reconciliation",
            validate_base_reconciliation,
            data,
            parameter_index,
        )
        collector.gate = "revenue_constraints"
        try:
            revenue_constraints = validate_revenue_constraints(
                data.get("revenue_constraints", []),
                [
                    segment.get("name")
                    for segment in data.get("segments", [])
                    if isinstance(segment, dict)
                ],
                parameter_index,
                years,
            )
        except (
            Exception
        ) as exc:  # best-effort collect-all must not abort the whole pass
            collector.add(f"gate could not complete: {type(exc).__name__}: {exc}")
        research_coverage = (
            _run_gate(
                collector,
                "research_coverage",
                validate_research_coverage,
                data,
                source_index,
                parameter_index,
            )
            or []
        )
        _run_gate(collector, "recognition", validate_recognition_contracts,
                  data, source_index, claim_index)
        growth_driver_tree = (
            _run_gate(
                collector,
                "growth_driver_tree",
                validate_growth_driver_tree,
                data,
                source_index,
                parameter_index,
                claim_index,
            )
            or {}
        )
        management_target_coverage = (
            _run_gate(
                collector,
                "management_targets",
                validate_management_target_coverage,
                data,
                source_index,
                parameter_index,
                claim_index,
                as_of,
            )
            or {}
        )

    if collector.errors:
        raise MultiValidationError(collector.errors)
    return {
        "years": years,
        "as_of_date": as_of,
        "source_index": source_index,
        "parameter_index": parameter_index,
        "claim_index": claim_index,
        "revenue_constraints": revenue_constraints,
        "research_coverage": research_coverage,
        "growth_driver_tree": growth_driver_tree,
        "management_target_coverage": management_target_coverage,
    }


def _run_gate(
    collector: Collector, gate: str, fn: Any, *args: Any, **kwargs: Any
) -> Any:
    """Run one validation gate under collect-all; record a gate-level note on crash."""
    collector.gate = gate
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # best-effort collect-all must not abort the whole pass
        collector.add(f"gate could not complete: {type(exc).__name__}: {exc}")
        return None
