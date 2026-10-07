"""RR-12.2d-4: the evaluator itself must (a) ceiling on a perfect prediction and
(b) expose a stable receipt schema. Companion mutation controls live in
test_gold_mutations.py.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from helpers.gold_evaluator import (
    THRESHOLDS,
    evaluate,
    gold_to_perfect_predictions,
    load_gold,
    receipt_sha256,
)

CORPUS = Path(__file__).parent.parent / "fixtures" / "gold_corpus"


@pytest.fixture(scope="module")
def gold():
    return load_gold(CORPUS)


@pytest.fixture(scope="module")
def perfect_receipt(gold):
    return evaluate(gold_to_perfect_predictions(gold), gold)


# ── receipt schema ─────────────────────────────────


class TestReceiptSchema:
    def test_all_metrics_present(self, perfect_receipt):
        expected = set(THRESHOLDS) | {"material_claim_f1"}
        assert expected <= set(perfect_receipt["metrics"]), (
            f"缺少指标: {expected - set(perfect_receipt['metrics'])}"
        )

    def test_thresholds_block_present(self, perfect_receipt):
        assert perfect_receipt["thresholds"] == THRESHOLDS

    def test_counts_present(self, perfect_receipt):
        c = perfect_receipt["counts"]
        assert c["predicted_claims"] > 0
        assert c["gold_material_claims"] > 0
        assert c["gold_routes"] > 0

    def test_receipt_is_hashable_canonical(self, perfect_receipt):
        # the helper must produce a stable canonical hash (no nondeterminism)
        h1 = receipt_sha256(perfect_receipt)
        h2 = receipt_sha256(json.loads(json.dumps(perfect_receipt)))
        assert h1 == h2 and len(h1) == 64

    def test_receipt_has_frozen_input_identity(self, perfect_receipt):
        assert perfect_receipt["schema_version"] == 1
        assert perfect_receipt["evaluator_version"]
        for field in ("manifest_sha256", "thresholds_sha256", "predictions_sha256"):
            assert len(perfect_receipt[field]) == 64


# ── the release-signoff CLI is retired (G5-CWP-CHECKS) ─────────────────────


class TestRetiredGoldGateCli:
    """The gold gate CLI is a stdlib retirement shell, not a receipt service."""

    CLI = Path(__file__).parents[2] / "scripts" / "gold_gate.py"

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.CLI), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_help_reports_retirement_instead_of_usage(self):
        result = self._run("--help")
        assert result.returncode == 78, result.stdout + result.stderr
        assert "LEGACY_ENGINEERING_TOOL_RETIRED" in result.stdout
        assert "--corpus" not in result.stdout
        assert "usage:" not in result.stdout

    def test_run_writes_no_receipt_at_all(self, tmp_path):
        forbidden = tmp_path / "receipt.json"
        result = self._run(
            "--corpus",
            str(CORPUS),
            "--perfect",
            "--receipt",
            str(forbidden),
        )
        assert result.returncode == 78, result.stdout + result.stderr
        assert "LEGACY_ENGINEERING_TOOL_RETIRED" in result.stdout
        assert not forbidden.exists()
        assert list(tmp_path.iterdir()) == []


# ── perfect prediction ceilings every metric ─────────────────────────────────


class TestPerfectPrediction:
    def test_all_critical_pass(self, perfect_receipt):
        assert perfect_receipt["all_critical_pass"] is True, (
            f"perfect prediction 必须全绿，但出现 failures: {perfect_receipt['failures']}"
        )

    def test_no_failures(self, perfect_receipt):
        assert perfect_receipt["failures"] == []

    @pytest.mark.parametrize(
        "metric, expected",
        [
            ("material_claim_recall", 1.0),
            ("material_claim_precision", 1.0),
            ("material_claim_f1", 1.0),
            ("evidence_exactness", 1.0),
            ("provenance_coverage", 1.0),
            ("numeric_exactness", 1.0),
            ("routing_micro_precision", 1.0),
            ("routing_micro_recall", 1.0),
            ("routing_macro_f1", 1.0),
            ("irrelevant_rejection", 1.0),
            ("ambiguity_detection_recall", 1.0),
            ("correction_supersedes_accuracy", 1.0),
            ("as_of_leakage_rate", 0.0),
            ("aggregation_dedup_accuracy", 1.0),
        ],
    )
    def test_metric_at_ceiling(self, perfect_receipt, metric, expected):
        assert perfect_receipt["metrics"][metric] == expected, (
            f"{metric}={perfect_receipt['metrics'][metric]} != ceiling {expected}"
        )
