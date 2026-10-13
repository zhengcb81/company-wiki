"""Tests for the mutation suite, fixtures and offline CLI behaviour.

These lock the node-B contract: every injected defect must be detected, the
suite must not silently count an inapplicable mutation as a hit, and the
offline CLI must stay inside its byte budget and the output directory.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.document_understanding_benchmark import evaluate
from tools.document_understanding_benchmark.fixtures import (
    OFFLINE_FIXTURE_BUDGET,
    all_fixtures,
    fixture_bytes,
)
from tools.document_understanding_benchmark.mutations import run_mutation_suite
from tools.document_understanding_benchmark.records import validate_gold, validate_observed

REPO_ROOT = Path(__file__).resolve().parents[3]


def _pairs():
    for fixture in all_fixtures():
        yield fixture["fixture_id"], validate_gold(fixture["gold"]), validate_observed(fixture["observed"])


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def test_offline_fixtures_stay_within_budget():
    assert fixture_bytes() <= OFFLINE_FIXTURE_BUDGET


def test_every_fixture_declares_a_route_and_scope():
    for fixture_id, gold, _observed in _pairs():
        assert gold["expected_route_families"], fixture_id
        assert gold["facts"], fixture_id


@pytest.mark.parametrize("fixture_id,gold,observed", list(_pairs()))
def test_healthy_fixture_never_fails(fixture_id, gold, observed):
    """A correct observation must not FAIL; PARTIAL/UNAVAILABLE is honest."""

    result = evaluate(observed, gold)
    assert result["status"] != "FAIL", [
        (row["check_id"], row["observed"]) for row in result["checks"] if row["status"] == "FAIL"
    ]


# ---------------------------------------------------------------------------
# mutation suite
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_id,gold,observed", list(_pairs()))
def test_all_applicable_mutations_are_detected(fixture_id, gold, observed):
    report = run_mutation_suite(observed, gold)
    misses = [
        (row["mutation_id"], row["result_status"], row["detail"])
        for row in report["rows"]
        if row["outcome"] == "NOT_DETECTED"
    ]
    assert not misses, f"{fixture_id} undetected: {misses}"


@pytest.mark.parametrize("fixture_id,gold,observed", list(_pairs()))
def test_not_applicable_mutations_are_not_counted_as_hits(fixture_id, gold, observed):
    report = run_mutation_suite(observed, gold)
    assert report["mutations_applicable"] + report["mutations_not_applicable"] == report["mutations_total"]
    for row in report["rows"]:
        if row["outcome"] == "NOT_APPLICABLE":
            assert row["detected"] is False
            assert row["failing_checks"] == []


def test_aggregate_detection_covers_every_injected_defect():
    applicable = 0
    detected = 0
    for _fixture_id, gold, observed in _pairs():
        report = run_mutation_suite(observed, gold)
        applicable += report["mutations_applicable"]
        detected += report["mutations_detected"]
    assert applicable > 0
    assert detected == applicable, f"{detected}/{applicable} detected"


# ---------------------------------------------------------------------------
# offline CLI
# ---------------------------------------------------------------------------


def test_offline_cli_runs_and_writes_only_its_own_directory(tmp_path):
    output = tmp_path / "bench-out"
    output.mkdir()
    preexisting = output / "sentinel.txt"
    preexisting.write_text("keep me", encoding="utf8")

    completed = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "tools.document_understanding_benchmark",
            "--mode",
            "offline",
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    # Exit 3 = PARTIAL present (the opaque fixture), which is an honest result.
    assert completed.returncode in {0, 3}, completed.stdout + completed.stderr

    summary_path = output / "offline" / "summary.json"
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf8"))
    assert summary["mode"] == "offline"
    assert summary["network_calls"] == 0
    assert summary["model_calls"] == 0
    assert summary["paid_calls"] == 0
    assert summary["fixture_bytes"] <= OFFLINE_FIXTURE_BUDGET

    # A pre-existing unrelated file outside the owned child is untouched.
    assert preexisting.read_text(encoding="utf8") == "keep me"


def test_cli_refuses_to_delete_an_unowned_container(tmp_path):
    from tools.document_understanding_benchmark.recovery import cleanup_owned

    unowned = tmp_path / "not-ours"
    unowned.mkdir()
    (unowned / "data.txt").write_text("important", encoding="utf8")

    report = cleanup_owned(unowned)
    assert report["removed"] is False
    assert (unowned / "data.txt").read_text(encoding="utf8") == "important"
