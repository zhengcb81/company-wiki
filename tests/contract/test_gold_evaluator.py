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
    THRESHOLDS, evaluate, gold_to_perfect_predictions, load_gold, receipt_sha256,
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
            f"缺少指标: {expected - set(perfect_receipt['metrics'])}")

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

    def test_fixed_cli_exists_and_has_help(self):
        cli = Path(__file__).parents[2] / "scripts" / "gold_gate.py"
        assert cli.exists(), "计划冻结的 scripts/gold_gate.py 尚未实现"
        result = subprocess.run(
            [sys.executable, str(cli), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "--corpus" in result.stdout
        assert "--predictions" in result.stdout
        assert "--receipt" in result.stdout

    def test_cli_rejects_receipt_outside_artifact_gate(self, tmp_path):
        cli = Path(__file__).parents[2] / "scripts" / "gold_gate.py"
        forbidden = tmp_path / "receipt.json"
        result = subprocess.run(
            [
                sys.executable,
                str(cli),
                "--corpus",
                str(CORPUS),
                "--perfect",
                "--receipt",
                str(forbidden),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert result.returncode == 2
        assert "receipt path must stay below" in result.stderr
        assert not forbidden.exists()


# ── perfect prediction ceilings every metric ─────────────────────────────────


class TestPerfectPrediction:
    def test_all_critical_pass(self, perfect_receipt):
        assert perfect_receipt["all_critical_pass"] is True, (
            f"perfect prediction 必须全绿，但出现 failures: {perfect_receipt['failures']}")

    def test_no_failures(self, perfect_receipt):
        assert perfect_receipt["failures"] == []

    @pytest.mark.parametrize("metric, expected", [
        ("material_claim_recall", 1.0), ("material_claim_precision", 1.0),
        ("material_claim_f1", 1.0), ("evidence_exactness", 1.0),
        ("provenance_coverage", 1.0), ("numeric_exactness", 1.0),
        ("routing_micro_precision", 1.0), ("routing_micro_recall", 1.0),
        ("routing_macro_f1", 1.0), ("irrelevant_rejection", 1.0),
        ("ambiguity_detection_recall", 1.0), ("correction_supersedes_accuracy", 1.0),
        ("as_of_leakage_rate", 0.0), ("aggregation_dedup_accuracy", 1.0),
    ])
    def test_metric_at_ceiling(self, perfect_receipt, metric, expected):
        assert perfect_receipt["metrics"][metric] == expected, (
            f"{metric}={perfect_receipt['metrics'][metric]} != ceiling {expected}")
