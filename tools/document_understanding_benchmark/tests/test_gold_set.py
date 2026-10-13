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
# the card's required minimum critical set
# ---------------------------------------------------------------------------

# label -> (sample_id, token groups); a group is satisfied by any alternative.
CARD_MINIMUM_SET = (
    ("名创门店总量", "hk-annual", (("7504", "7,504"),)),
    ("名创经营模式", "hk-annual", (("直營店", "Retail Partner", "名創合夥人", "代理門店"),)),
    ("名创年份", "hk-annual", (("2024",), ("2023",))),
    ("名创TOP TOY海外", "hk-annual", (("TOP TOY",), ("overseas", "海外"))),
    ("恒锋两期建设", "cn-equity", (("两期",), ("一期",), ("二期",))),
    ("恒锋投资", "cn-equity", (("35300", "35,300"), ("28678", "28,678"))),
    ("中微产品验证阶段", "cn-q-business", (("量产验证",), ("晶圆验证",), ("验证成功",))),
    ("万润不生产VC", "cn-ir", (("无生产VC",),)),
    ("万润提问前提", "cn-ir", (("带量采购", "提问"),)),
    ("扫描确认函", "cn-ipo-confirmation", (("确认意见",),)),
    ("财务季报负例", "cn-q-sparse", (("其他提醒事项",), ("不适用",))),
    ("微软消费制Azure", "us-10k", (("consumption-based",),)),
    ("电话会角色", "us-txt", (("CALL PARTICIPANTS",), ("Operator",), ("analyst",))),
    ("TAL监管业务约束", "us-20f", (("Alleviating Burden", "prohibited", "shall not"),)),
)


def test_card_minimum_critical_set_is_covered():
    """The card names nine required elements across these samples.

    If a gold record is renamed, dropped, or hollowed out, this fails rather
    than the gap silently reopening.
    """

    have = {record["sample_id"]: record for record in load_gold_dir()}
    gaps: list[str] = []
    for label, sample_id, groups in CARD_MINIMUM_SET:
        record = have.get(sample_id)
        if record is None:
            gaps.append(f"{label}: no gold for {sample_id}")
            continue
        corpus = " ".join(
            str(token)
            for fact in record["facts"]
            for token in (fact.get("must_preserve") or [])
            + [
                anchor.get("exact_quote") or ""
                for support in fact.get("any_support_sets") or []
                for anchor in support
            ]
            + [fact.get("reason") or "", fact.get("role") or "", fact.get("modality") or ""]
        ).casefold()
        unmet = [
            group
            for group in groups
            if not any(alt.casefold() in corpus for alt in group)
        ]
        if unmet:
            gaps.append(f"{label} ({sample_id}): unmet {unmet}")
    assert not gaps, "card minimum critical set has gaps: " + "; ".join(gaps)


def test_card_minimum_set_samples_all_have_gold():
    """Every sample the card names must exist as a gold record."""

    have = {record["sample_id"] for record in load_gold_dir()}
    required = {sample_id for _label, sample_id, _groups in CARD_MINIMUM_SET}
    assert required <= have, f"missing gold for {sorted(required - have)}"


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
            "critical_fact_recall_denominator_declared": total,
            "critical_fact_unavailable": 0,
            "fact_recall": (passed / total) if total else None,
            "fact_recall_denominator": total,
        },
    }


def test_unreadable_facts_leave_the_recall_denominator():
    """UNAVAILABLE means 'not read', not 'searched and not found'.

    An unreadable document must not be reported as a recall of 0.000, because
    that reads as a total miss rather than a coverage gap. The unavailable count
    is reported separately and the overall status still degrades to PARTIAL.
    """

    observed = {
        "schema_version": "du-observed/1",
        "sample_id": "unreadable",
        "source_sha256": "a" * 64,
        "route": None,
        "selected_locators": [],
        "selected_text": "",
        "selected_evidence": [],
        "semantic_units": [],
        "claims": [],
        "coverage": {
            "native_scan": "unavailable",
            "complete": False,
            "opaque_pages": [],
            "deferred_unit_ids": [],
            "unassigned_unit_ids": [],
        },
        "metrics": {},
        "execution": {"mode": "native", "calls": 0},
    }
    gold = {
        "schema_version": "du-gold/1",
        "sample_id": "unreadable",
        "source_sha256": "a" * 64,
        "scope": "holdout",
        "expected_route_families": ["annual"],
        "facts": [
            {
                "id": "f1",
                "importance": "critical",
                "any_support_sets": [[{"page": 1, "exact_quote": "x"}]],
            },
            {
                "id": "f2",
                "importance": "critical",
                "any_support_sets": [[{"page": 2, "exact_quote": "y"}]],
            },
        ],
    }
    from tools.document_understanding_benchmark import evaluate

    result = evaluate(observed, gold)
    metrics = result["metrics"]
    assert metrics["critical_fact_unavailable"] == 2
    assert metrics["critical_fact_recall_denominator_declared"] == 2
    assert metrics["critical_fact_recall_denominator"] == 0
    assert metrics["critical_fact_recall"] is None, (
        "an unreadable document must not report a recall figure at all"
    )
    assert metrics["critical_fact_coverage"] == 0.0
    assert result["status"] != "PASS"


def test_partially_unreadable_denominator_counts_only_readable_facts():
    """One readable miss plus one unreadable fact must not average together."""

    observed = {
        "schema_version": "du-observed/1",
        "sample_id": "partial",
        "source_sha256": "a" * 64,
        "route": None,
        "selected_locators": [],
        "selected_text": "",
        "selected_evidence": [],
        "semantic_units": [],
        "claims": [],
        "coverage": {
            "native_scan": "partial",
            "complete": False,
            "opaque_pages": [2],
            "deferred_unit_ids": [],
            "unassigned_unit_ids": [],
        },
        "metrics": {},
        "execution": {"mode": "native", "calls": 0},
    }
    gold = {
        "schema_version": "du-gold/1",
        "sample_id": "partial",
        "source_sha256": "a" * 64,
        "scope": "development",
        "expected_route_families": ["annual"],
        "facts": [
            {
                "id": "f-readable",
                "importance": "critical",
                "any_support_sets": [[{"page": 1, "exact_quote": "x"}]],
            },
            {
                "id": "f-unreadable",
                "importance": "critical",
                "any_support_sets": [[{"page": 2, "exact_quote": "y"}]],
            },
        ],
    }
    from tools.document_understanding_benchmark import evaluate

    result = evaluate(observed, gold)
    metrics = result["metrics"]
    assert metrics["critical_fact_unavailable"] == 1
    assert metrics["critical_fact_recall_denominator"] == 1
    assert metrics["critical_fact_recall"] == 0.0
    assert metrics["critical_fact_coverage"] == 0.5


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


def test_make_bindings_preserves_entries_absent_from_the_manifest(tmp_path):
    """A rebuild must not silently drop holdout bindings.

    The manifest lists only the 20 survey samples. Holdout records are not in it,
    so an overwriting rebuild would lose them, and a lost binding is
    indistinguishable from a missing original: the run reports UNAVAILABLE
    instead of reporting that its own configuration was clobbered.
    """

    import json as _json

    from tools.document_understanding_benchmark.make_bindings import main as make_main

    original = tmp_path / "orig.bin"
    original.write_bytes(b"original bytes")
    digest = hashlib.sha256(b"original bytes").hexdigest()

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        _json.dumps(
            {
                "samples": [
                    {"id": "survey-a", "path": str(original), "sha256": digest},
                ]
            }
        ),
        encoding="utf8",
    )

    out = tmp_path / "bindings.json"
    out.write_text(
        _json.dumps({"holdout-x": "C:/some/holdout.pdf", "survey-a": "C:/stale.pdf"}),
        encoding="utf8",
    )

    assert make_main(["--manifest", str(manifest), "--out", str(out)]) == 0
    written = _json.loads(out.read_text(encoding="utf8"))
    assert "holdout-x" in written, "holdout binding was dropped by a manifest rebuild"
    assert written["survey-a"] == str(original), "manifest entry must win on conflict"

    # --replace is the explicit opt-out
    assert make_main(["--manifest", str(manifest), "--out", str(out), "--replace"]) == 0
    replaced = _json.loads(out.read_text(encoding="utf8"))
    assert replaced == {"survey-a": str(original)}
