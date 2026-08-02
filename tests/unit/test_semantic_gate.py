import json
from pathlib import Path

from semantic_gate import evaluate_gold_integrity


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def make_gold(tmp_path: Path) -> Path:
    gold = tmp_path / "gold"
    source = gold / "sources" / "Company" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nsource_id: S1\n---\nEvidence text", encoding="utf-8")
    full_text = source.read_text(encoding="utf-8")
    start = full_text.index("Evidence text")
    write_json(
        gold / "annotations" / "evidence_spans.json",
        {"spans": {"S1": [{"span_id": "E1", "start": start, "end": start + 13, "text": "Evidence text"}]}},
    )
    write_json(
        gold / "annotations" / "material_claims.json",
        {"claims": [{"claim_id": "C1", "source_id": "S1", "evidence_spans": ["E1"]}]},
    )
    write_json(
        gold / "annotations" / "routing_targets.json",
        {"routing": [{"source_id": "S1", "expected_targets": [{"entity_id": "Company"}]}]},
    )
    write_json(gold / "annotations" / "contradictions.json", {"contradictions": []})
    write_json(
        gold / "expected" / "quality_metrics.json",
        {"metrics": {"source_coverage": {"total_sources": 1, "actual": 1.0, "target": 1.0, "status": "pass"}}},
    )
    return gold


def test_valid_minimal_gold_is_computed_as_pass(tmp_path):
    gold = make_gold(tmp_path)
    result = evaluate_gold_integrity(gold, min_sources=1)
    assert result["result"] == "pass"
    assert result["counts"]["unique_sources"] == 1


def test_missing_routing_source_is_rejected(tmp_path):
    gold = make_gold(tmp_path)
    write_json(
        gold / "annotations" / "routing_targets.json",
        {"routing": [{"source_id": "MISSING", "expected_targets": [{"entity_id": "Company"}]}]},
    )
    result = evaluate_gold_integrity(gold, min_sources=1)
    assert any(item["id"] == "routing-source-missing" for item in result["violations"])


def test_handwritten_pass_cannot_override_failed_threshold(tmp_path):
    gold = make_gold(tmp_path)
    write_json(
        gold / "expected" / "quality_metrics.json",
        {
            "metrics": {
                "source_coverage": {"total_sources": 1, "actual": 1.0, "target": 1.0, "status": "pass"},
                "numeric_exactness": {"actual": 0.85, "target": 0.95, "status": "pass_with_notes"},
            }
        },
    )
    result = evaluate_gold_integrity(gold, min_sources=1)
    assert any(
        item["id"] == "handwritten-status-contradicts-threshold"
        for item in result["violations"]
    )


def test_minimum_source_count_is_hard_failure(tmp_path):
    gold = make_gold(tmp_path)
    result = evaluate_gold_integrity(gold, min_sources=2)
    assert any(item["id"] == "gold-source-count" for item in result["violations"])
