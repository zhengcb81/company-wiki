"""Extracted from revenue_core.py during the R9 split (behavior-locked by tests/test_golden_behavior_lock.py)."""

from __future__ import annotations

from typing import Any

from contracts.constants import RESEARCH_COVERAGE_STATUSES, RESEARCH_DIMENSIONS
from contracts.evidence import (
    require,
)
from forecast.calc import collect_parameter_roles


def validate_research_coverage(
    data: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
    parameter_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Validate the nine-dimension research gate without turning it into a score."""
    coverage = data.get("research_coverage")
    require(isinstance(coverage, list), "research_coverage must be a list")
    require(
        len(coverage) >= len(RESEARCH_DIMENSIONS),
        "research_coverage must contain at least nine core dimensions",
    )
    roles = collect_parameter_roles(data, parameter_index)
    normalized: dict[str, dict[str, Any]] = {}

    for position, record in enumerate(coverage):
        prefix = f"research_coverage[{position}]"
        require(isinstance(record, dict), f"{prefix} must be an object")
        dimension = record.get("dimension")
        require(
            dimension in RESEARCH_DIMENSIONS or dimension not in normalized,
            f"duplicate or unsupported research dimension: {dimension}",
        )
        require(
            dimension not in normalized, f"duplicate research dimension: {dimension}"
        )
        status = record.get("status")
        require(
            status in RESEARCH_COVERAGE_STATUSES,
            f"unsupported research coverage status for {dimension}: {status}",
        )
        for field in ("conclusion", "revenue_mechanism"):
            require(
                isinstance(record.get(field), str) and record[field].strip(),
                f"{dimension}.{field} is required",
            )

        parameter_ids = record.get("parameter_ids", [])
        source_ids = record.get("source_ids", [])
        require(
            isinstance(parameter_ids, list), f"{dimension}.parameter_ids must be a list"
        )
        require(isinstance(source_ids, list), f"{dimension}.source_ids must be a list")
        require(
            len(parameter_ids) == len(set(parameter_ids)),
            f"{dimension}.parameter_ids contains duplicates",
        )
        require(
            len(source_ids) == len(set(source_ids)),
            f"{dimension}.source_ids contains duplicates",
        )
        for parameter_id in parameter_ids:
            require(
                parameter_id in parameter_index,
                f"unknown research parameter_id {parameter_id} for {dimension}",
            )
            require(
                parameter_id in roles["used"],
                f"research parameter_id {parameter_id} for {dimension} is not used by the revenue model",
            )
        for source_id in source_ids:
            require(
                source_id in source_index,
                f"unknown research source_id {source_id} for {dimension}",
            )

        rationale = record.get("rationale")
        if status == "modeled_driver":
            require(
                bool(parameter_ids),
                f"{dimension} modeled_driver requires parameter_ids",
            )
            require(bool(source_ids), f"{dimension} modeled_driver requires source_ids")
            if dimension == "company_foundation":
                require(
                    bool(set(parameter_ids) & roles["foundation"]),
                    "company_foundation must map to a base or reported revenue parameter",
                )
            if dimension == "growth_curve":
                require(
                    bool(set(parameter_ids) & roles["forecast"]),
                    "growth_curve must map to a forecast driver, carry-in, or adjustment parameter",
                )
        elif status == "data_gap":
            require(
                isinstance(rationale, str) and rationale.strip(),
                f"{dimension} data_gap requires rationale",
            )
        else:
            require(
                not parameter_ids,
                f"{dimension} immaterial cannot map to model parameters",
            )
            require(
                isinstance(rationale, str) and rationale.strip(),
                f"{dimension} immaterial requires rationale",
            )

        item = {
            "dimension": dimension,
            "status": status,
            "conclusion": record["conclusion"].strip(),
            "revenue_mechanism": record["revenue_mechanism"].strip(),
            "parameter_ids": list(parameter_ids),
            "source_ids": list(source_ids),
        }
        if isinstance(rationale, str) and rationale.strip():
            item["rationale"] = rationale.strip()
        normalized[dimension] = item

    require(
        set(normalized) >= set(RESEARCH_DIMENSIONS),
        "research_coverage must include every core dimension",
    )
    records = [normalized[dimension] for dimension in RESEARCH_DIMENSIONS]
    for dimension in normalized:
        if dimension not in RESEARCH_DIMENSIONS:
            records.append(normalized[dimension])
    return {
        "records": records,
        "counts": {
            status: sum(record["status"] == status for record in records)
            for status in sorted(RESEARCH_COVERAGE_STATUSES)
        },
        "gap_messages": [
            f"{record['dimension']}: {record['conclusion']}"
            for record in records
            if record["status"] == "data_gap"
        ],
        "parameter_roles": roles,
    }
