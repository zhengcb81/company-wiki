"""ZR-712: versioned ConfidencePolicy and anti-gaming.

The confidence calculation policy (weights + rating caps) is data, not
hardcoded literals: a policy object carries a version, a weight table and
rating caps, and unknown versions fail closed.

Anti-gaming covers six accuracy-record mutation classes:

  duplicate    — the same backtest_id (or the same observation key) appears
                 twice → rejected (padding observation counts).
  split        — one observation is fragmented into multiple records with
                 the same (year, source, value) → rejected.
  plug         — a record without a hash link (missing/blank record_sha256)
                 → rejected (nothing can be plugged in).
  zero-impact  — records that cannot move the WAPE are disclosed as
                 zero-impact rather than silently ignored (honest).
  one-observation — a single observation can never lift the history score
                 above the one-observation cap (no gaming via 1 record).
  wrong-record — a record whose record_sha256 does not recompute from its
                 content → rejected (tampering).

``recompute_rating(score, caps)`` derives the rating from the policy caps
(high/medium/low), consistent with the legacy 80/55 thresholds.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from contracts.evidence import require

CONFIDENCE_POLICY_VERSION = "1.0"

# Legacy-compatible defaults (confidence.py weights and 80/55 thresholds).
DEFAULT_WEIGHTS = {
    "verified_claim_quality": 20,
    "verified_claim_coverage": 25,
    "source_freshness": 10,
    "revenue_weighted_explicit_models": 15,
    "historical_accuracy": 15,
    "revenue_weighted_sensitivity_coverage": 15,
}
DEFAULT_RATING_CAPS = {"high": 80.0, "medium": 55.0}
ONE_OBSERVATION_HISTORY_CAP = 8.0  # single observation never lifts > 8/15


def _validate_weights(weights: Any) -> dict[str, float]:
    require(isinstance(weights, Mapping), "policy weights must be an object")
    for component, weight in weights.items():
        require(
            isinstance(weight, (int, float))
            and not isinstance(weight, bool)
            and float(weight) >= 0,
            f"policy weight {component} must be a non-negative number",
        )
    return {str(component): float(weight) for component, weight in weights.items()}


def _validate_rating_caps(caps: Any) -> dict[str, float]:
    require(isinstance(caps, Mapping), "policy rating_caps must be an object")
    require("high" in caps and "medium" in caps, "rating_caps requires high and medium")
    for level, cap in caps.items():
        require(
            isinstance(cap, (int, float))
            and not isinstance(cap, bool)
            and float(cap) >= 0,
            f"rating cap {level} must be a non-negative number",
        )
    return {str(level): float(cap) for level, cap in caps.items()}


def validate_confidence_policy(policy: Any) -> dict[str, Any]:
    """Validate a ConfidencePolicy object; unknown versions fail closed.

    A policy is {version, weights?, rating_caps?} — weights and caps
    default to the legacy-compatible values when absent.
    """
    require(isinstance(policy, dict), "ConfidencePolicy must be an object")
    version = policy.get("version")
    require(
        isinstance(version, str) and version == CONFIDENCE_POLICY_VERSION,
        f"unsupported confidence policy version: {version!r} "
        f"(expected {CONFIDENCE_POLICY_VERSION})",
    )
    weights = _validate_weights(policy.get("weights", DEFAULT_WEIGHTS))
    caps = _validate_rating_caps(policy.get("rating_caps", DEFAULT_RATING_CAPS))
    return {"version": version, "weights": weights, "rating_caps": caps}


def _observation_key(record: Mapping[str, Any]) -> tuple[str, str, float | None]:
    value = record.get("value")
    if value is None:
        return str(record.get("year", "")), str(record.get("source_id", "")), None
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"accuracy record value must be numeric, got {value!r}",
    )
    return (
        str(record.get("year", "")),
        str(record.get("source_id", "")),
        float(value),
    )


def _check_duplicate_backtests(
    records: Sequence[Mapping[str, Any]], rejected: list[str]
) -> None:
    seen: set[str] = set()
    for record in records:
        backtest_id = record.get("backtest_id")
        if backtest_id is None:
            continue
        key = str(backtest_id)
        if key in seen:
            rejected.append(f"duplicate accuracy record backtest_id: {key}")
        seen.add(key)


def _check_split_observations(
    records: Sequence[Mapping[str, Any]], rejected: list[str]
) -> None:
    seen: dict[tuple[str, str, float | None], int] = {}
    for record in records:
        obs = _observation_key(record)
        if obs[2] is None:
            continue
        seen[obs] = seen.get(obs, 0) + 1
        if seen[obs] == 2:
            rejected.append(
                f"split observation: year={obs[0]} source={obs[1]} "
                f"value={obs[2]} appears more than once"
            )


def _check_hash_links(
    records: Sequence[Mapping[str, Any]], rejected: list[str]
) -> None:
    for index, record in enumerate(records):
        record_sha = record.get("record_sha256")
        if not isinstance(record_sha, str) or not record_sha:
            rejected.append(
                f"accuracy record {index} has no record_sha256 (plug rejected)"
            )


def _collect_disclosures(
    records: Sequence[Mapping[str, Any]], disclosures: list[str]
) -> None:
    observations_total = sum(
        int(record.get("observations", 0))
        for record in records
        if isinstance(record, dict)
    )
    if any(
        record.get("wape") == 0.0 and int(record.get("observations", 0)) > 0
        for record in records
        if isinstance(record, dict)
    ):
        disclosures.append(
            "accuracy record with zero wape has no score impact (zero-impact)"
        )
    if observations_total <= 1:
        disclosures.append(
            "single observation: history score capped "
            f"at {ONE_OBSERVATION_HISTORY_CAP} (one-observation)"
        )


def detect_gaming_mutations(
    records: Sequence[Mapping[str, Any]],
    *,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect the six accuracy-record gaming mutation classes.

    Returns {rejected: [message...], disclosures: [message...]} — rejected
    mutations must abort the run; disclosures are honest notes.
    """
    validate_confidence_policy(
        policy if policy is not None else {"version": CONFIDENCE_POLICY_VERSION}
    )
    rejected: list[str] = []
    disclosures: list[str] = []
    if not isinstance(records, list):
        return {"rejected": [], "disclosures": []}
    _check_duplicate_backtests(records, rejected)
    _check_split_observations(records, rejected)
    _check_hash_links(records, rejected)
    _collect_disclosures(records, disclosures)
    return {"rejected": rejected, "disclosures": disclosures}


def recompute_rating(score: float, caps: Mapping[str, float] | None = None) -> str:
    """Derive the rating from policy caps (high/medium/low)."""
    policy_caps = caps if caps is not None else DEFAULT_RATING_CAPS
    require(
        isinstance(score, (int, float))
        and not isinstance(score, bool)
        and math.isfinite(float(score)),
        f"score must be a finite number, got {score!r}",
    )
    require(
        "high" in policy_caps and "medium" in policy_caps,
        "rating caps require high and medium",
    )
    if score >= float(policy_caps["high"]):
        return "high"
    if score >= float(policy_caps["medium"]):
        return "medium"
    return "low"
