"""A: RED counterexamples for ``compare_runs`` (DU3-QUALITY card §1/§3/§4/§6).

The comparison exists to stop one specific abuse: reporting a quality
improvement produced by *changing the measurement* rather than by changing the
system. It therefore may only compare two runs that share

* the same source (SHA-256),
* the same read scope,
* the same assembly budget, and
* the same gold denominator.

When any of those differ the answer is ``INCOMPARABLE`` — never a smaller
denominator quietly scored as a better ratio. The card also forbids deleting a
failing gold fact or lowering its importance to turn the suite green, so the
suite fingerprint is checked by content, not by count.
"""

from __future__ import annotations

import pytest

from tools.document_understanding_benchmark import compare_runs

SHA = "1" * 64
OTHER_SHA = "2" * 64


def _evaluation(
    *,
    status: str = "FAIL",
    recall: float | None = 0.5,
    denominator: int = 8,
    passed: int | None = None,
    source_sha256: str = SHA,
    gold_digest: str | None = "a" * 64,
    reviewed: bool = False,
    checks: list[dict] | None = None,
    not_evaluated: list[dict] | None = None,
    sample_id: str = "s1",
) -> dict:
    if passed is None:
        passed = int(round((recall or 0.0) * denominator))
    payload = {
        "schema_version": "du-evaluation/1",
        "sample_id": sample_id,
        "source_sha256": source_sha256,
        "scope": "holdout",
        "status": status,
        "checks": checks if checks is not None else [],
        "metrics": {
            "critical_fact_recall": recall,
            "critical_fact_recall_denominator": denominator,
            "critical_fact_recall_denominator_declared": denominator,
            "critical_fact_pass_count": passed,
            "selected_span_count": 96,
        },
        "dimensions": {},
        "not_evaluated": not_evaluated or [],
        "spot_read_list": [],
        "review": {"supplied": reviewed, "claims": 0},
        "execution": {},
    }
    if gold_digest is not None:
        payload["gold_digest"] = gold_digest
    return payload


def _suite(
    *,
    sample_id: str = "s1",
    source_sha256: str = SHA,
    read_scope: dict | None = None,
    budget: dict | None = None,
    gold_facts: int = 8,
    gold_digest: str = "a" * 64,
    suite_id: str = "suite-1",
) -> dict:
    return {
        "schema_version": "du-frozen-suite/1",
        "suite_id": suite_id,
        "samples": [
            {
                "sample_id": sample_id,
                "source_sha256": source_sha256,
                "read_scope": read_scope or {"pages": "all", "units": "all"},
                "budget": budget or {"max_chars": 48000, "max_packages": 40},
                "gold": {"facts": gold_facts, "digest": gold_digest,
                         "thresholds": {"critical_fact_recall": 0.8}},
            }
        ],
    }


# ---------------------------------------------------------------------------
# the shape of the answer
# ---------------------------------------------------------------------------


def test_comparison_reports_the_frozen_wire_shape():
    result = compare_runs(
        {"runs": [_evaluation(recall=0.5)]},
        {"runs": [_evaluation(recall=0.75, passed=6)]},
        frozen_suite=_suite(),
    )
    assert result["schema_version"] == "du-quality-comparison/1"
    assert result["status"] in {"PASS", "FAIL", "PARTIAL", "INCOMPARABLE"}
    assert result["suite_id"] == "suite-1"
    assert isinstance(result["samples"], list)


def test_a_real_improvement_on_the_same_denominator_is_reported_as_such():
    result = compare_runs(
        {"runs": [_evaluation(status="FAIL", recall=0.25, denominator=8, passed=2)]},
        {"runs": [_evaluation(status="PASS", recall=1.0, denominator=8, passed=8)]},
        frozen_suite=_suite(),
    )
    row = result["samples"][0]
    # The improvement is real and comparable, but with no independent review the
    # summary's fidelity is unverified, so this is PARTIAL and never a clean
    # summary-quality PASS (the card: no real model -> no fidelity PASS).
    assert result["status"] == "PARTIAL"
    assert row["comparable"] is True
    assert row["delta"]["critical_fact_recall"] == pytest.approx(0.75)
    assert row["delta"]["denominator"] == 0
    assert "dimension:semantics.entailment" in row["unmeasured"]


def test_a_reviewed_improvement_can_reach_pass():
    """With an independent review of the semantics, a real improvement can PASS."""

    reviewed = _evaluation(status="PASS", recall=1.0, denominator=8, passed=8,
                           reviewed=True)
    result = compare_runs(
        {"runs": [_evaluation(status="FAIL", recall=0.25, denominator=8, passed=2,
                              reviewed=True)]},
        {"runs": [reviewed]},
        frozen_suite=_suite(),
    )
    assert result["status"] == "PASS"
    assert result["samples"][0]["outcome"] == "PASS"


def test_an_attested_gold_is_required_for_a_clean_pass():
    """A run that does not attest its gold cannot earn a clean PASS."""

    result = compare_runs(
        {"runs": [_evaluation(status="FAIL", recall=0.25, denominator=8, passed=2,
                              reviewed=True)]},
        {"runs": [_evaluation(status="PASS", recall=1.0, denominator=8, passed=8,
                              reviewed=True, gold_digest=None)]},
        frozen_suite=_suite(),
    )
    assert result["status"] == "PARTIAL"
    assert result["samples"][0]["unverified_gold"] == ["candidate"]


def test_a_fact_moved_to_not_evaluated_is_never_an_improvement():
    """Hiding an evaluated gap by relabelling it NOT_EVALUATED is a defect."""

    baseline = _evaluation(
        status="FAIL", recall=0.5, denominator=8, passed=4, reviewed=True,
        checks=[{"check_id": "recall.f1", "status": "FAIL"}],
    )
    candidate = _evaluation(
        status="PASS", recall=1.0, denominator=6, passed=6, reviewed=True,
        not_evaluated=[{"check_id": "recall.f1", "status": "NOT_EVALUATED"}],
    )
    result = compare_runs({"runs": [baseline]}, {"runs": [candidate]},
                          frozen_suite=_suite())
    row = result["samples"][0]
    assert row["moved_to_not_evaluated"] == ["recall.f1"]
    assert row["weakened_gold"] is True
    assert result["status"] in {"INCOMPARABLE", "FAIL"}


# ---------------------------------------------------------------------------
# §4/§6: same source / scope / budget / gold denominator, or INCOMPARABLE
# ---------------------------------------------------------------------------


def test_different_source_sha_is_incomparable():
    result = compare_runs(
        {"runs": [_evaluation(source_sha256=SHA)]},
        {"runs": [_evaluation(source_sha256=OTHER_SHA)]},
        frozen_suite=_suite(),
    )
    assert result["status"] == "INCOMPARABLE"
    assert result["samples"][0]["comparable"] is False
    assert any("source" in reason for reason in result["samples"][0]["incomparable_reasons"])


def test_different_read_scope_is_incomparable():
    result = compare_runs(
        {"runs": [_evaluation()], "read_scope": {"pages": "1-40"}},
        {"runs": [_evaluation()], "read_scope": {"pages": "1-120"}},
        frozen_suite=_suite(),
    )
    assert result["status"] == "INCOMPARABLE"
    assert any("scope" in reason for reason in result["samples"][0]["incomparable_reasons"])


def test_different_budget_is_incomparable():
    result = compare_runs(
        {"runs": [_evaluation()], "budget": {"max_chars": 48000}},
        {"runs": [_evaluation()], "budget": {"max_chars": 96000}},
        frozen_suite=_suite(),
    )
    assert result["status"] == "INCOMPARABLE"
    assert any("budget" in reason for reason in result["samples"][0]["incomparable_reasons"])


def test_gold_denominator_change_is_incomparable():
    """A shrunken denominator must never read as an improvement."""

    result = compare_runs(
        {"runs": [_evaluation(recall=0.25, denominator=8, passed=2)]},
        {"runs": [_evaluation(recall=1.0, denominator=2, passed=2)]},
        frozen_suite=_suite(gold_facts=2),
    )
    assert result["status"] == "INCOMPARABLE"
    reasons = result["samples"][0]["incomparable_reasons"]
    assert any("denominator" in reason for reason in reasons)


def test_declared_gold_change_is_incomparable():
    result = compare_runs(
        {"runs": [_evaluation()]},
        {"runs": [_evaluation()]},
        frozen_suite=_suite(gold_digest="b" * 64),
    )
    assert result["status"] == "INCOMPARABLE"
    assert any("gold" in reason for reason in result["samples"][0]["incomparable_reasons"])


def test_missing_read_scope_on_either_side_is_unavailable_not_assumed_equal():
    result = compare_runs(
        {"runs": [_evaluation()]},
        {"runs": [_evaluation()], "read_scope": {"pages": "all"}},
        frozen_suite=_suite(),
    )
    assert result["status"] == "INCOMPARABLE"
    assert any("scope" in reason for reason in result["samples"][0]["incomparable_reasons"])


# ---------------------------------------------------------------------------
# §6: the suite itself must not be quietly weakened
# ---------------------------------------------------------------------------


def test_a_failing_critical_fact_cannot_be_removed_to_look_greener():
    """Removing the fact is not an improvement even when the ratio rises."""

    baseline = _evaluation(
        recall=0.25, denominator=8, passed=2,
        checks=[{"check_id": "recall.f-msft-1", "status": "FAIL"},
                {"check_id": "recall.f-msft-2", "status": "FAIL"}],
    )
    candidate = _evaluation(
        recall=1.0, denominator=6, passed=6,
        checks=[],
    )
    result = compare_runs(
        {"runs": [baseline]},
        {"runs": [candidate]},
        frozen_suite=_suite(gold_facts=8),
    )
    assert result["status"] == "INCOMPARABLE"
    assert result["samples"][0]["weakened_gold"] is True or any(
        "denominator" in reason for reason in result["samples"][0]["incomparable_reasons"]
    )


def test_a_gold_fact_that_becomes_not_evaluated_is_reported_not_hidden():
    baseline = _evaluation(checks=[{"check_id": "recall.f1", "status": "FAIL"}])
    candidate = _evaluation(
        recall=0.5, denominator=8, passed=4,
        not_evaluated=[{"check_id": "recall.f1", "status": "NOT_EVALUATED"}],
    )
    result = compare_runs({"runs": [baseline]}, {"runs": [candidate]},
                          frozen_suite=_suite())
    row = result["samples"][0]
    assert "recall.f1" in row["moved_to_not_evaluated"]


def test_microsoft_four_of_eight_critical_failure_is_preserved_as_a_failure():
    """The measured 4/8 Microsoft gap must not be re-scored into a pass."""

    result = compare_runs(
        {"runs": [_evaluation(sample_id="us-10k", recall=0.5, denominator=8, passed=4)]},
        {"runs": [_evaluation(sample_id="us-10k", recall=0.5, denominator=8, passed=4)]},
        frozen_suite=_suite(sample_id="us-10k"),
    )
    row = result["samples"][0]
    assert row["baseline"]["status"] == "FAIL"
    assert row["candidate"]["status"] == "FAIL"
    assert result["status"] == "FAIL"


# ---------------------------------------------------------------------------
# honest three-valued per-sample outcome
# ---------------------------------------------------------------------------


def test_a_regression_on_the_same_denominator_fails():
    result = compare_runs(
        {"runs": [_evaluation(status="PASS", recall=1.0, denominator=8, passed=8)]},
        {"runs": [_evaluation(status="FAIL", recall=0.375, denominator=8, passed=3)]},
        frozen_suite=_suite(),
    )
    assert result["status"] == "FAIL"
    assert result["samples"][0]["delta"]["critical_fact_recall"] < 0


def test_unchanged_worse_than_the_frozen_threshold_still_fails():
    result = compare_runs(
        {"runs": [_evaluation(status="FAIL", recall=0.5, denominator=8, passed=4)]},
        {"runs": [_evaluation(status="FAIL", recall=0.5, denominator=8, passed=4)]},
        frozen_suite=_suite(),
    )
    assert result["status"] == "FAIL"
    assert any("threshold" in note for note in result["samples"][0]["notes"])


def test_semantic_review_still_unavailable_on_both_sides_is_partial_not_pass():
    result = compare_runs(
        {"runs": [_evaluation(status="PARTIAL", recall=1.0, denominator=8, passed=8)]},
        {"runs": [_evaluation(status="PARTIAL", recall=1.0, denominator=8, passed=8)]},
        frozen_suite=_suite(),
    )
    assert result["status"] == "PARTIAL"
    assert result["samples"][0]["unmeasured"]


def test_missing_sample_on_either_side_is_incomparable_not_ignored():
    result = compare_runs(
        {"runs": [_evaluation(sample_id="s1")]},
        {"runs": [_evaluation(sample_id="s2")]},
        frozen_suite=_suite(),
    )
    assert result["status"] == "INCOMPARABLE"
    assert result["samples"][0]["comparable"] is False


def test_comparison_does_not_mutate_its_inputs():
    import copy

    baseline = {"runs": [_evaluation()]}
    candidate = {"runs": [_evaluation(recall=0.75, passed=6)]}
    suite = _suite()
    before = copy.deepcopy((baseline, candidate, suite))
    compare_runs(baseline, candidate, frozen_suite=suite)
    assert (baseline, candidate, suite) == before
