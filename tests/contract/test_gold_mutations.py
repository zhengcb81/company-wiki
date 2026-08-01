"""RR-12.2d-4R mutation controls for the independent gold evaluator.

Every corpus mutation runs in a temporary copy.  Prediction mutations operate
on a deep copy of the perfect prediction artifact.  A mutation is useful only
when the evaluator rejects it or lowers the metric that owns the defect.
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from helpers.gold_evaluator import evaluate, gold_to_perfect_predictions, load_gold


CORPUS = Path(__file__).parent.parent / "fixtures" / "gold_corpus"


@pytest.fixture(scope="module")
def gold():
    return load_gold(CORPUS)


@pytest.fixture()
def predictions(gold):
    return copy.deepcopy(gold_to_perfect_predictions(gold))


def _copy_corpus(tmp_path: Path) -> Path:
    target = tmp_path / "gold_corpus"
    shutil.copytree(CORPUS, target)
    return target


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _assert_metric_failed(receipt: dict, metric: str) -> None:
    assert receipt["metrics"][metric] < receipt["thresholds"][metric]
    assert metric in {failure["metric"] for failure in receipt["failures"]}
    assert receipt["all_critical_pass"] is False


class TestCorpusIntegrityMutations:
    def test_missing_manifest_source_is_rejected(self, tmp_path):
        corpus = _copy_corpus(tmp_path)
        manifest = _read_json(corpus / "corpus_manifest.json")
        (corpus / manifest["revisions"][0]["path"]).unlink()

        with pytest.raises(ValueError, match="manifest source"):
            load_gold(corpus)

    def test_unregistered_source_is_rejected(self, tmp_path):
        corpus = _copy_corpus(tmp_path)
        extra = corpus / "sources" / "未登记" / "extra.md"
        extra.parent.mkdir(parents=True)
        extra.write_text("---\nsynthetic: true\n---\n未登记来源\n", encoding="utf-8")

        with pytest.raises(ValueError, match="unregistered source"):
            load_gold(corpus)

    def test_duplicate_revision_id_is_rejected(self, tmp_path):
        corpus = _copy_corpus(tmp_path)
        path = corpus / "corpus_manifest.json"
        manifest = _read_json(path)
        duplicate = copy.deepcopy(manifest["revisions"][1])
        duplicate["revision_id"] = manifest["revisions"][0]["revision_id"]
        manifest["revisions"].append(duplicate)
        _write_json(path, manifest)

        with pytest.raises(ValueError, match="duplicate revision_id"):
            load_gold(corpus)

    def test_source_hash_drift_is_rejected(self, tmp_path):
        corpus = _copy_corpus(tmp_path)
        manifest = _read_json(corpus / "corpus_manifest.json")
        source = corpus / manifest["revisions"][0]["path"]
        source.write_text(source.read_text(encoding="utf-8") + "篡改", encoding="utf-8")

        with pytest.raises(ValueError, match="content_sha256"):
            load_gold(corpus)

    @pytest.mark.parametrize("broken_side", ["claim", "span"])
    def test_broken_claim_span_reference_is_rejected(self, tmp_path, broken_side):
        corpus = _copy_corpus(tmp_path)
        if broken_side == "claim":
            path = corpus / "annotations" / "material_claims.json"
            document = _read_json(path)
            document["claims"][0]["evidence_spans"] = ["S-NOT-FOUND"]
        else:
            path = corpus / "annotations" / "evidence_spans.json"
            document = _read_json(path)
            first_group = next(iter(document["spans"].values()))
            first_group[0]["claim_id"] = "C-NOT-FOUND"
        _write_json(path, document)

        with pytest.raises(ValueError, match="reference"):
            load_gold(corpus)

    def test_span_offset_shift_is_rejected(self, tmp_path):
        corpus = _copy_corpus(tmp_path)
        path = corpus / "annotations" / "evidence_spans.json"
        document = _read_json(path)
        first_group = next(iter(document["spans"].values()))
        first_group[0]["start"] += 1
        _write_json(path, document)

        with pytest.raises(ValueError, match="span offset"):
            load_gold(corpus)


class TestPredictionMutations:
    def test_evidence_offset_shift_fails_exactness(self, gold, predictions):
        # One error is correctly measured but remains above the frozen 0.95
        # aggregate threshold.  Mutate the full cohort so this negative control
        # proves the gate fails without changing the reviewer-owned threshold.
        for claim in predictions["claims"]:
            if claim.get("evidence"):
                claim["evidence"]["start"] += 1

        _assert_metric_failed(evaluate(predictions, gold), "evidence_exactness")

    def test_missing_numeric_payload_fails_numeric_exactness(self, gold, predictions):
        claim = next(item for item in predictions["claims"] if item.get("numeric"))
        claim["numeric"] = None

        _assert_metric_failed(evaluate(predictions, gold), "numeric_exactness")

    @pytest.mark.parametrize(
        ("field", "bad_value"),
        [("unit", "万元"), ("currency", "USD"), ("period", "2025Q4")],
    )
    def test_numeric_field_mutation_fails_exactness(
        self, gold, predictions, field, bad_value
    ):
        claim = next(item for item in predictions["claims"] if item.get("numeric"))
        claim["numeric"][field] = bad_value

        _assert_metric_failed(evaluate(predictions, gold), "numeric_exactness")

    def test_opinion_or_prediction_mislabeled_fact_is_rejected(self, gold, predictions):
        claim = next(
            item
            for item in predictions["claims"]
            if item.get("claim_type") in {"opinion", "prediction"}
        )
        claim["claim_type"] = "fact"

        receipt = evaluate(predictions, gold)
        assert receipt["all_critical_pass"] is False
        assert "claim_type_accuracy" in {
            failure["metric"] for failure in receipt["failures"]
        }

    def test_deleted_correction_edge_fails(self, gold, predictions):
        claim = next(
            item
            for item in predictions["claims"]
            if item.get("corrects") or item.get("supersedes")
        )
        claim["corrects"] = None
        claim["supersedes"] = None

        _assert_metric_failed(
            evaluate(predictions, gold), "correction_supersedes_accuracy"
        )

    def test_future_claim_fails_as_of_gate(self, gold, predictions):
        predictions["claims"][0]["published_at"] = "2099-01-01"

        receipt = evaluate(predictions, gold, as_of="2098-12-31")
        assert receipt["metrics"]["as_of_leakage_rate"] > 0
        assert "as_of_leakage_rate" in {
            failure["metric"] for failure in receipt["failures"]
        }

    def test_ambiguous_route_wrong_entity_fails_detection(self, gold, predictions):
        route = next(item for item in predictions["routes"] if item["has_ambiguity"])
        route["targets"] = [{"entity_id": "错误实体", "confidence": "high"}]

        _assert_metric_failed(
            evaluate(predictions, gold), "ambiguity_detection_recall"
        )

    def test_irrelevant_requires_explicit_rejection_flag(self, gold, predictions):
        route = next(item for item in predictions["routes"] if item["is_irrelevant"])
        route["is_irrelevant"] = False
        route["targets"] = []

        _assert_metric_failed(evaluate(predictions, gold), "irrelevant_rejection")

    def test_aggregation_without_canonical_source_fails_dedup(self, gold, predictions):
        route = next(
            item
            for item in predictions["routes"]
            if item.get("canonical_source_id")
        )
        route["canonical_source_id"] = None

        _assert_metric_failed(
            evaluate(predictions, gold), "aggregation_dedup_accuracy"
        )

    def test_dropping_required_fanout_fails_routing_recall(self, gold, predictions):
        for route in predictions["routes"]:
            if not route["is_irrelevant"] and route["targets"]:
                route["targets"] = route["targets"][:1]

        _assert_metric_failed(evaluate(predictions, gold), "routing_micro_recall")

    def test_hallucinated_source_fails_provenance(self, gold, predictions):
        hallucination = copy.deepcopy(predictions["claims"][0])
        hallucination["source_id"] = "not-in-manifest"
        hallucination["text"] = "无来源的幻觉声明"
        hallucination["numeric"] = None
        predictions["claims"].append(hallucination)

        _assert_metric_failed(evaluate(predictions, gold), "provenance_coverage")


def test_threshold_file_is_definition_only():
    document = _read_json(CORPUS / "expected" / "quality_metrics.json")
    serialized = json.dumps(document, ensure_ascii=False)
    for forbidden in ("actual", "status", "ready_for_canary"):
        assert f'"{forbidden}"' not in serialized
