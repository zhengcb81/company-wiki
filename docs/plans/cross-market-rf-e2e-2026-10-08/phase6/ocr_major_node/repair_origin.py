"""Pure accounting for a repaired generation; no old run or fee is reset."""
from __future__ import annotations

from copy import deepcopy


def derive_repair_baseline(prepared, ledgers, current_versions):
    first = ledgers.get("first", {})
    if first.get("status") != "read":
        raise ValueError("repair_requires_real_first_origin")
    previous = first.get("execution_versions")
    if (not isinstance(previous, dict) or not isinstance(current_versions, dict)
            or not current_versions
            or not any(previous.get(key) != value for key, value in current_versions.items())):
        raise ValueError("repair_requires_changed_execution_version")
    tokens = costs = 0
    for observation in ledgers.values():
        if observation.get("status") == "not_created":
            continue
        budget = observation.get("budget", {})
        if (observation.get("status") != "read" or observation.get("terminal") is not True
                or observation.get("active_attempts") != 0
                or budget.get("unknown_reservations") != 0
                or budget.get("unsettled_reservations") != 0):
            raise ValueError("repair_requires_terminal_settled_origin")
        for key in ("charged_tokens", "charged_micro_usd"):
            if type(budget.get(key)) is not int or budget[key] < 0:
                raise ValueError("repair_requires_actual_usage")
        tokens += budget["charged_tokens"]
        costs += budget["charged_micro_usd"]
    baseline = deepcopy(prepared["budget_baseline"])
    baseline["cumulative_tokens"] += tokens
    baseline["cumulative_estimated_micro_usd"] += costs
    baseline["remaining_tokens"] = baseline["effective_cap_tokens"] - baseline["cumulative_tokens"]
    baseline["remaining_micro_usd_after_fx"] = (baseline["effective_cap_micro_usd"]
                                              - baseline["cumulative_estimated_micro_usd"]
                                              - baseline["fx_guard_micro_usd"])
    if baseline["remaining_tokens"] < 30_000 or baseline["remaining_micro_usd_after_fx"] < 100_000:
        raise ValueError("repair_cumulative_budget_insufficient")
    return {"parent_attempt_id": prepared["attempt_id"], "parent_input_hash": first["input_hash"],
            "source_sha256": prepared["source"]["original"]["sha256"],
            "previous_execution_versions": deepcopy(previous),
            "current_execution_versions": deepcopy(current_versions),
            "parent_added_tokens": tokens, "parent_added_micro_usd": costs,
            "budget_baseline": baseline}
