"""Tests for the development/holdout split, scope reporting and real gold integrity.

These lock the property that matters most for a benchmark: development and
holdout must never be merged into one headline number, and every packaged gold
record must be internally consistent and SHA-bound to a real original when one
is available.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from tools.document_understanding_benchmark.__main__ import _scope_summary
from tools.document_understanding_benchmark.gold import (
    GOLD_DIR,
    GoldError,
    load_bindings,
    load_gold_dir,
)
from tools.document_understanding_benchmark.records import validate_gold

REPO_ROOT = Path(__file__).resolve().parents[3]
BINDINGS_CANDIDATES = (
    Path.home() / ".du-bench" / "bindings.local.json",
    REPO_ROOT / ".du-bench-out" / "bindings.local.json",
)


def _bindings() -> dict[str, str]:
    for candidate in BINDINGS_CANDIDATES:
        if candidate.is_file():
            try:
                return load_bindings(candidate)
            except GoldError:
                continue
    return {}


# ---------------------------------------------------------------------------
# gold set integrity (offline)
# ---------------------------------------------------------------------------


def test_gold_set_loads_and_has_both_scopes():
    records = load_gold_dir()
    scopes = {record["scope"] for record in records}
    assert "development" in scopes
    assert "holdout" in scopes, "a benchmark with no holdout cannot measure generalisation"


def test_every_gold_record_has_facts_and_expected_families():
    for record in load_gold_dir():
        assert record["facts"], record["sample_id"]
        assert record["expected_route_families"], record["sample_id"]


def test_gold_quote_budget_per_document():
    """The card bounds quoted text at 8KiB per document."""

    for record in load_gold_dir():
        assert record["gold_quote_chars"] <= 8 * 1024, (
            f"{record['sample_id']} quotes {record['gold_quote_chars']} bytes"
        )


def test_holdout_records_are_marked_holdout_not_development():
    for record in load_gold_dir():
        if record["sample_id"].startswith("holdout-"):
            assert record["scope"] == "holdout", record["sample_id"]


def test_development_seeds_are_not_claiming_holdout():
    """The 20 survey samples were used for tuning, so none may claim holdout."""

    development_expected = {
        "cn-h1",
        "cn-annual",
        "cn-ipo",
        "cn-q-business",
        "cn-q-sparse",
        "cn-convertible",
        "cn-equity",
        "cn-ipo-confirmation",
        "cn-ir",
        "cn-ir-policy",
        "hk-annual",
        "hk-interim",
        "hk-ipo",
        "hk-release",
        "hk-deck",
        "us-10k",
        "us-10q",
        "us-20f",
        "us-release",
        "us-txt",
    }
    for record in load_gold_dir():
        if record["sample_id"] in development_expected:
            assert record["scope"] == "development", record["sample_id"]


def test_gold_facts_declare_modality_and_role():
    """Without a declared modality, plan-vs-actual errors are undetectable."""

    for record in load_gold_dir():
        for fact in record["facts"]:
            assert fact["modality"] in {
                "actual",
                "plan",
                "negation",
                "question",
                "third_party",
                "conditional",
                "unknown",
            }, f"{record['sample_id']}/{fact['id']}"
            assert fact["role"], f"{record['sample_id']}/{fact['id']}"


def test_gold_json_files_are_the_only_scope_source():
    """No stray non-gold JSON may sit in the gold directory."""

    for path in GOLD_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf8"))
        assert data["schema_version"] == "du-gold/1", path.name
        validate_gold(data)


# ---------------------------------------------------------------------------
# scope summary
# ---------------------------------------------------------------------------


def _fake_result(sample_id: str, scope: str, status: str, passed: int, total: int):
    return {
        "sample_id": sample_id,
        "scope": scope,
        "status": status,
        "checks": [],
        "not_evaluated": [],
        "metrics": {
            "critical_fact_recall": (passed / total) if total else None,
            "critical_fact_recall_denominator": total,
            "critical_fact_unavailable": 0,
            "fact_recall": (passed / total) if total else None,
            "fact_recall_denominator": total,
        },
    }


def test_scope_summary_never_merges_development_and_holdout():
    results = [
        _fake_result("dev-a", "development", "PASS", 4, 4),
        _fake_result("hol-a", "holdout", "FAIL", 0, 5),
    ]
    summary = _scope_summary(results)
    assert set(summary) == {"development", "holdout"}
    assert summary["development"]["critical_facts_total"] == 4
    assert summary["holdout"]["critical_facts_total"] == 5
    assert summary["holdout"]["critical_fact_recall"] == 0.0


def test_scope_summary_reports_denominator_when_nothing_recalled():
    summary = _scope_summary([_fake_result("hol", "holdout", "FAIL", 0, 7)])
    assert summary["holdout"]["critical_facts_passed"] == 0
    assert summary["holdout"]["critical_facts_total"] == 7
    assert summary["holdout"]["critical_fact_recall"] == 0.0


def test_scope_summary_is_none_not_zero_when_no_denominator():
    summary = _scope_summary([_fake_result("empty", "holdout", "UNAVAILABLE", 0, 0)])
    assert summary["holdout"]["critical_fact_recall"] is None


# ---------------------------------------------------------------------------
# SHA binding (opt-in against real originals)
# ---------------------------------------------------------------------------


@pytest.mark.real_data
def test_every_gold_record_binds_to_its_declared_sha():
    """Each packaged gold must match the SHA of the original it claims."""

    if os.environ.get("DU_BENCH_ALLOW_REAL_DATA") != "1":
        pytest.skip("set DU_BENCH_ALLOW_REAL_DATA=1 to verify real originals")
    bindings = _bindings()
    checked = 0
    for record in load_gold_dir():
        bound = bindings.get(record["sample_id"])
        if not bound:
            continue
        path = Path(bound)
        if not path.is_file():
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == record["source_sha256"], record["sample_id"]
        checked += 1
    assert checked > 0, "no gold record had a usable local binding"
