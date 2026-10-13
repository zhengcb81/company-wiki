"""Tests for the semantic-review negative controls.

These prove the review layer is load-bearing rather than decorative: there are
defects no deterministic check catches, and the review stage closes exactly
those, while never rescuing a defect the deterministic layer already caught.
"""

from __future__ import annotations

from tools.document_understanding_benchmark.controls import (
    run_rescue_controls,
    run_review_controls,
)
from tools.document_understanding_benchmark.records import validate_gold, validate_observed
from tools.document_understanding_benchmark.tests.synthetic import GOLD, good_observed


def _pairs():
    gold = validate_gold(GOLD)
    observed = validate_observed(good_observed())
    return gold, observed


def test_controls_run_and_report_their_counts():
    gold, observed = _pairs()
    report = run_review_controls(observed, gold)
    assert report["controls_total"] == 3
    assert len(report["rows"]) == 3
    assert report["interpretation"]


def test_there_exist_defects_no_deterministic_check_catches():
    """If this fails, the review layer is redundant and should be re-justified."""

    gold, observed = _pairs()
    report = run_review_controls(observed, gold)
    assert report["deterministic_blind_count"] > 0, (
        "every injected semantic defect was caught deterministically; "
        "the review layer's justification needs revisiting"
    )


def test_review_layer_catches_every_semantic_only_defect():
    gold, observed = _pairs()
    report = run_review_controls(observed, gold)
    missed = [row["control_id"] for row in report["rows"] if not row["review_caught"]]
    assert not missed, f"review failed to catch: {missed}"
    assert report["review_caught_all"] is True


def test_review_control_records_the_mutated_text_for_audit():
    gold, observed = _pairs()
    report = run_review_controls(observed, gold)
    for row in report["rows"]:
        assert row["mutated_text"]
        assert row["note"]


def test_review_cannot_rescue_a_deterministic_failure():
    gold, observed = _pairs()
    report = run_rescue_controls(observed, gold)
    assert report["controls"], "the rescue control did not run"
    assert report["all_rescues_blocked"] is True
    for row in report["controls"]:
        assert row["unaided_status"] == "FAIL"
        assert row["with_review_status"] == "FAIL"
