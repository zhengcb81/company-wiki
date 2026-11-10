"""Shared recognition contract: validate shape before consumers traverse it."""
from __future__ import annotations
from typing import Any
from contracts.constants import PRESENTATIONS, RECOGNITION_MODES, RECOGNITION_TIMING, SCENARIOS
from contracts.evidence import require, validate_claim_ids

def validate_recognition_metadata(
    segment: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    name = segment["name"]
    recognition = segment.get("recognition")
    require(isinstance(recognition, dict), f"{name} requires recognition metadata")
    if not isinstance(recognition, dict):
        return {}  # collect-all recorded the real shape error; never traverse None
    mode = recognition.get("mode")
    timing = recognition.get("timing")
    presentation = recognition.get("presentation")
    require(
        mode in RECOGNITION_MODES, f"unsupported recognition mode for {name}: {mode}"
    )
    require(
        timing in RECOGNITION_TIMING,
        f"unsupported recognition timing for {name}: {timing}",
    )
    require(
        presentation in PRESENTATIONS,
        f"unsupported presentation for {name}: {presentation}",
    )
    require(
        recognition.get("modeled_presentation") == presentation,
        f"{name} modeled_presentation must match accounting presentation",
    )
    require(
        isinstance(recognition.get("trigger"), str) and recognition["trigger"].strip(),
        f"{name} requires a revenue-recognition trigger",
    )
    if timing == "mixed" or presentation == "mixed":
        # These values describe a published aggregate, not an activity-level
        # recognition algorithm. Never invent one uniform timing/principal
        # policy for a segment whose component policies differ.
        require(
            mode == "modeled_as_recognized",
            f"{name} mixed accounting requires already recognized revenue",
        )
        scenarios = segment.get("scenarios")
        require(
            isinstance(scenarios, dict) and set(scenarios) == set(SCENARIOS)
            and all(isinstance(item, dict)
                    and item.get("model") in {"direct_growth", "direct_revenue"}
                    for item in scenarios.values()),
            f"{name} mixed accounting requires direct_growth/direct_revenue",
        )
        boundary = recognition.get("aggregation_boundary")
        require(
            isinstance(boundary, str) and bool(boundary.strip()),
            f"{name} mixed accounting requires aggregation_boundary",
        )
        transforms = {"progress_measure", "progress_parameter_ids", "lag_years",
                      "carry_in_parameter_ids"} & recognition.keys()
        require(
            not transforms,
            f"{name} mixed accounting cannot contain recognition transforms: "
            f"{', '.join(sorted(transforms))}",
        )
    if timing == "over_time":
        require(
            isinstance(recognition.get("progress_measure"), str)
            and recognition["progress_measure"].strip(),
            f"{name} over-time recognition requires progress_measure",
        )
        require(
            mode != "lagged_activity",
            f"{name} cannot combine over_time with lagged_activity",
        )
        progress = recognition.get("progress_parameter_ids")
        require(
            isinstance(progress, dict) and set(progress) == set(SCENARIOS),
            f"{name} over-time recognition requires low/base/high progress_parameter_ids",
        )
    basis_claims = validate_claim_ids(
        recognition.get("basis_claim_ids"),
        claim_index,
        "recognition_policy",
        f"recognition:{name}",
        f"{name}.recognition",
        "policy_support",
    )
    basis_source_ids = sorted({claim["source_id"] for claim in basis_claims})
    require(bool(basis_source_ids), f"{name} recognition requires policy evidence")
    recognition = dict(recognition)
    recognition["basis_source_ids"] = basis_source_ids
    if mode == "lagged_activity":
        lag_years = recognition.get("lag_years")
        require(
            isinstance(lag_years, int) and lag_years > 0,
            f"{name} lagged_activity requires positive integer lag_years",
        )
        carry_in = recognition.get("carry_in_parameter_ids")
        require(
            isinstance(carry_in, dict) and set(carry_in) == set(SCENARIOS),
            f"{name} lagged_activity requires low/base/high carry_in_parameter_ids",
        )
    return recognition

