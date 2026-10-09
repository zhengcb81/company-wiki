"""Repair retries keep terminal evidence and debit earlier actual usage once."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


MODULE = Path(__file__).resolve().parents[2] / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/ocr_major_node/repair_origin.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("main_ocr_repair_origin", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inputs():
    prepared = {"attempt_id": "old-attempt", "source": {"original": {"sha256": "a" * 64}},
                "budget_baseline": {"cumulative_tokens": 100, "cumulative_estimated_micro_usd": 200,
                                    "effective_cap_tokens": 2_000_000, "effective_cap_micro_usd": 20_000_000,
                                    "fx_guard_micro_usd": 5, "historical_unknown_reservations": 7}}
    first = {"status": "read", "terminal": True, "active_attempts": 0,
             "execution_versions": {"selector": "0.4.2", "parser": "0.1.1"},
             "input_hash": "b" * 64,
             "budget": {"charged_tokens": 10, "charged_micro_usd": 20,
                        "unknown_reservations": 0, "unsettled_reservations": 0}}
    return prepared, {"first": first, "reuse": {"status": "not_created"}}, {"selector": "0.4.3", "parser": "0.1.1"}


def test_new_generation_carries_actual_usage_and_preserves_parent():
    prepared, ledgers, versions = inputs()
    before = deepcopy((prepared, ledgers, versions))
    proof = load_helper().derive_repair_baseline(prepared, ledgers, versions)
    assert (prepared, ledgers, versions) == before
    assert proof["parent_attempt_id"] == "old-attempt"
    assert proof["parent_input_hash"] == "b" * 64
    assert proof["budget_baseline"]["cumulative_tokens"] == 110
    assert proof["budget_baseline"]["cumulative_estimated_micro_usd"] == 220
    assert proof["budget_baseline"]["remaining_micro_usd_after_fx"] == 19_999_775
    assert proof["budget_baseline"]["historical_unknown_reservations"] == 7


@pytest.mark.parametrize("bad", ["unknown", "unsettled", "active", "unreadable", "missing_first", "same_version"])
def test_retry_cannot_hide_unfinished_or_unknown_origin(bad):
    prepared, ledgers, versions = inputs()
    if bad == "unknown":
        ledgers["first"]["budget"]["unknown_reservations"] = 1
    elif bad == "unsettled":
        ledgers["first"]["budget"]["unsettled_reservations"] = 1
    elif bad == "active":
        ledgers["first"]["terminal"] = False
        ledgers["first"]["active_attempts"] = 1
    elif bad == "unreadable":
        ledgers["first"]["status"] = "unavailable"
    elif bad == "missing_first":
        ledgers["first"] = {"status": "not_created"}
    else:
        versions["selector"] = "0.4.2"
    with pytest.raises(ValueError):
        load_helper().derive_repair_baseline(prepared, ledgers, versions)


def test_successful_earlier_reuse_usage_is_also_counted_without_refund():
    prepared, ledgers, versions = inputs()
    ledgers["reuse"] = deepcopy(ledgers["first"])
    ledgers["reuse"]["budget"].update(charged_tokens=2, charged_micro_usd=3)
    proof = load_helper().derive_repair_baseline(prepared, ledgers, versions)
    assert proof["budget_baseline"]["cumulative_tokens"] == 112
    assert proof["budget_baseline"]["cumulative_estimated_micro_usd"] == 223


def test_spent_origin_cannot_consume_another_unfunded_node():
    prepared, ledgers, versions = inputs()
    prepared["budget_baseline"]["effective_cap_tokens"] = 30_105
    with pytest.raises(ValueError):
        load_helper().derive_repair_baseline(prepared, ledgers, versions)
