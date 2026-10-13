"""Composable business-model mechanisms must not override each other.

The four mechanism records are pure content modifiers. They stay generic (no
company product lists), their mechanism axes are disjoint so composition cannot
double-bind one axis, and no two mechanism records redefine the same confusion,
which would silently override one meaning with another.
"""

from __future__ import annotations

from helpers import load_json, record_path

MECHANISM_RECORD_IDS = [
    "mechanism_subscription_consumption",
    "mechanism_store_network",
    "mechanism_manufacturing",
    "mechanism_biopharma_cdmo",
]

EXPECTED_MECHANISM_AXES = {
    "subscription",
    "consumption",
    "store_network",
    "manufacturing",
    "biopharma",
    "cdmo",
}


def test_four_mechanism_records_exist() -> None:
    for record_id in MECHANISM_RECORD_IDS:
        assert record_path(record_id).exists(), f"missing mechanism record {record_id}"


def test_mechanism_axes_are_disjoint_and_complete() -> None:
    seen: dict = {}
    for record_id in MECHANISM_RECORD_IDS:
        mechanisms = set(load_json(record_path(record_id))["applicable_mechanisms"])
        assert "generic" not in mechanisms, (
            f"{record_id} must bind concrete mechanism axes, not the generic catch-all"
        )
        for mechanism in mechanisms:
            assert mechanism not in seen, (
                f"mechanism axis {mechanism} claimed by both {seen.get(mechanism)} and "
                f"{record_id}; composition would override one of them"
            )
            seen[mechanism] = record_id
    assert set(seen) == EXPECTED_MECHANISM_AXES, (
        f"four mechanism records must cover exactly the six axes, got {sorted(seen)}"
    )


def test_mechanism_records_do_not_redefine_each_other() -> None:
    source_meanings: dict = {}
    assertions: dict = {}
    for record_id in MECHANISM_RECORD_IDS:
        record = load_json(record_path(record_id))
        for entry in record["confusions"]:
            meaning = entry["source_meaning"].strip()
            assert meaning not in source_meanings, (
                f"confusion source_meaning {meaning!r} redefined by {record_id} "
                f"(already defined by {source_meanings[meaning]})"
            )
            source_meanings[meaning] = record_id
        for entry in record["required_context"]:
            assertion = entry["assertion"].strip()
            assert assertion not in assertions, (
                f"required_context assertion {assertion!r} redefined by {record_id}"
            )
            assertions[assertion] = record_id


def test_mechanism_records_only_add_context_never_drop_slots() -> None:
    """A mechanism may deepen a fact; it may not tell the engine to omit a slot."""
    for record_id in MECHANISM_RECORD_IDS:
        record = load_json(record_path(record_id))
        for entry in record["required_context"]:
            assert entry["slots"], f"{record_id}: empty slots would silently drop context"
            assert entry["missing_behavior"] in {"unknown", "partial", "deferred"}
        for rule in record["absence_rules"]:
            assert "不必保留" not in rule and "无需保留" not in rule, (
                f"{record_id}: mechanisms must not instruct dropping required context"
            )


def test_mechanism_scope_is_modifier_not_classifier() -> None:
    for record_id in MECHANISM_RECORD_IDS:
        record = load_json(record_path(record_id))
        blob = " ".join(record["business_questions"] + record["summary_focus"])
        assert "分类" not in blob or "不是" in blob, (
            f"{record_id} must read as content modifier, not an industry classifier"
        )
