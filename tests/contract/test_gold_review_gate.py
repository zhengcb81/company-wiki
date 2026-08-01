"""Contracts for the RR-12.2e independent gold-review mechanism."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import gold_review_gate as review_gate

from gold_review_gate import (
    PRIMARY_CHECKS,
    SECOND_CHECKS,
    build_review_packet,
    build_review_template,
    canonical_sha256,
    select_second_review_ids,
    validate_review_receipt,
    write_artifact,
)


ROOT = Path(__file__).parents[2]
CORPUS = ROOT / "tests" / "fixtures" / "gold_corpus"
MANIFEST = CORPUS / "corpus_manifest.json"


@pytest.fixture(scope="module")
def packet():
    return build_review_packet(CORPUS, "implementer-test")


def _manifest_sha256() -> str:
    return hashlib.sha256(MANIFEST.read_bytes()).hexdigest()


def _valid_receipt(packet: dict) -> dict:
    receipt = build_review_template(packet)
    revisions = {item["revision_id"]: item for item in packet["revisions"]}
    primary_reviewer_by_id = {}
    for index, review in enumerate(receipt["primary_reviews"]):
        reviewer = f"primary-reviewer-{index % 3}"
        primary_reviewer_by_id[review["revision_id"]] = reviewer
        review.update(
            {
                "reviewer_id": reviewer,
                "reviewed_at": "2026-07-11T12:00:00Z",
                "decision": "accepted",
                "checks": {name: "pass" for name in PRIMARY_CHECKS},
                "notes": f"逐项核验 {review['revision_id']} 的来源、证据、声明和路由一致。",
            }
        )
    for index, review in enumerate(receipt["second_reviews"]):
        primary = primary_reviewer_by_id[review["revision_id"]]
        reviewer = f"second-reviewer-{index % 3}"
        if reviewer == primary:
            reviewer += "-independent"
        review.update(
            {
                "reviewer_id": reviewer,
                "reviewed_at": "2026-07-11T13:00:00Z",
                "decision": "accepted",
                "agrees_with_primary": True,
                "checks": {name: "pass" for name in SECOND_CHECKS},
                "notes": f"独立复核 {review['revision_id']}，结论与证据链一致。",
            }
        )
    receipt["review_summary"] = (
        f"独立审核 {len(revisions)} 个 revision，第二复核覆盖全部来源类型。"
    )
    return receipt


def _codes(result: dict) -> set[str]:
    return {finding["code"] for finding in result["findings"]}


def test_gold_review_gate_module_exists():
    assert (ROOT / "scripts" / "gold_review_gate.py").is_file()


def test_packet_matches_manifest_and_contains_no_body(packet):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert packet["revision_count"] == 40
    assert {item["revision_id"] for item in packet["revisions"]} == {
        item["revision_id"] for item in manifest["revisions"]
    }
    assert packet["corpus_manifest_sha256"] == _manifest_sha256()

    forbidden = {"body", "source_body", "raw_text", "content"}

    def walk(value):
        if isinstance(value, dict):
            assert not (forbidden & set(value))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(packet)


def test_packet_annotation_indexes_are_materialized(packet):
    claims = json.loads(
        (CORPUS / "annotations" / "material_claims.json").read_text(encoding="utf-8")
    )["claims"]
    span_groups = json.loads(
        (CORPUS / "annotations" / "evidence_spans.json").read_text(encoding="utf-8")
    )["spans"]
    assert {
        claim_id
        for item in packet["revisions"]
        for claim_id in item["claim_ids"]
    } == {claim["claim_id"] for claim in claims}
    assert {
        span_id
        for item in packet["revisions"]
        for span_id in item["span_ids"]
    } == {
        span["span_id"] for spans in span_groups.values() for span in spans
    }
    assert all(item["route_target_ids"] for item in packet["revisions"])
    assert any(item["relation_ids"] for item in packet["revisions"])
    assert any(item["has_numeric"] for item in packet["revisions"])
    assert any(item["has_temporal_relation"] for item in packet["revisions"])


def test_packet_binds_every_review_critical_input_file(packet):
    relative_paths = {
        "corpus_manifest.json",
        "annotations/evidence_spans.json",
        "annotations/material_claims.json",
        "annotations/routing_targets.json",
        "annotations/contradictions.json",
        "expected/quality_metrics.json",
    }
    expected = {
        relative_path: hashlib.sha256((CORPUS / relative_path).read_bytes()).hexdigest()
        for relative_path in sorted(relative_paths)
    }
    assert packet.get("review_input_sha256") == expected
    assert packet.get("review_input_bundle_sha256") == canonical_sha256(expected)


def test_annotation_content_drift_changes_packet_even_when_ids_do_not(packet, tmp_path):
    corpus_copy = tmp_path / "gold_corpus"
    shutil.copytree(CORPUS, corpus_copy)
    claims_path = corpus_copy / "annotations" / "material_claims.json"
    claims = json.loads(claims_path.read_text(encoding="utf-8"))
    claims["review_binding_probe"] = "same IDs, different reviewed annotation bytes"
    claims_path.write_text(
        json.dumps(claims, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rebuilt = build_review_packet(corpus_copy, "implementer-test")
    assert rebuilt.get("review_input_bundle_sha256") != packet.get(
        "review_input_bundle_sha256"
    )


def test_threshold_file_drift_changes_packet(packet, tmp_path):
    corpus_copy = tmp_path / "gold_corpus"
    shutil.copytree(CORPUS, corpus_copy)
    thresholds_path = corpus_copy / "expected" / "quality_metrics.json"
    thresholds_path.write_text(
        thresholds_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    rebuilt = build_review_packet(corpus_copy, "implementer-test")
    assert rebuilt.get("review_input_bundle_sha256") != packet.get(
        "review_input_bundle_sha256"
    )


def test_second_review_selection_is_deterministic_and_covers_kinds(packet):
    selected = select_second_review_ids(packet["revisions"])
    flagged = sorted(
        item["revision_id"]
        for item in packet["revisions"]
        if item["second_review_required"]
    )
    assert selected == flagged
    assert len(selected) == packet["second_review_minimum"] == 8
    by_id = {item["revision_id"]: item for item in packet["revisions"]}
    assert {by_id[revision_id]["source_kind"] for revision_id in selected} == set(
        packet["required_source_kinds"]
    )
    assert canonical_sha256(build_review_packet(CORPUS, "implementer-test")) == canonical_sha256(packet)


def test_template_is_entirely_pending(packet):
    template = build_review_template(packet)
    assert len(template["primary_reviews"]) == 40
    assert len(template["second_reviews"]) == 8
    assert all(item["reviewer_id"] is None for item in template["primary_reviews"])
    assert all(item["decision"] == "pending" for item in template["primary_reviews"])
    assert all(item["reviewer_id"] is None for item in template["second_reviews"])
    assert all(item["decision"] == "pending" for item in template["second_reviews"])
    assert template["packet_sha256"] == canonical_sha256(packet)


def test_pending_template_is_blocked_not_invalid(packet):
    result = validate_review_receipt(
        packet, build_review_template(packet), packet
    )
    assert result["status"] == "blocked_independent_review_pending"
    assert result["approved"] is False
    assert "PRIMARY_PENDING" in _codes(result)


def test_complete_independent_receipt_is_approved_in_memory(packet):
    result = validate_review_receipt(
        packet, _valid_receipt(packet), packet
    )
    assert result["status"] == "approved"
    assert result["approved"] is True
    assert result["findings"] == []
    assert result["counts"]["primary_accepted"] == 40
    assert result["counts"]["second_accepted"] == 8


@pytest.mark.parametrize(
    "reviewer_id",
    [None, "", "implementer-test", " implementer-test", "IMPLEMENTER-TEST"],
)
def test_primary_reviewer_must_be_independent(packet, reviewer_id):
    receipt = _valid_receipt(packet)
    receipt["primary_reviews"][0]["reviewer_id"] = reviewer_id
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "rejected_invalid_review"
    assert "PRIMARY_REVIEWER_NOT_INDEPENDENT" in _codes(result)


def test_primary_id_set_must_exactly_match_packet(packet):
    receipt = _valid_receipt(packet)
    receipt["primary_reviews"].pop()
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "rejected_invalid_review"
    assert "PRIMARY_ID_SET_MISMATCH" in _codes(result)


def test_packet_hash_drift_is_rejected(packet):
    receipt = _valid_receipt(packet)
    receipt["packet_sha256"] = "0" * 64
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "rejected_invalid_review"
    assert "PACKET_HASH_MISMATCH" in _codes(result)


def test_packet_and_receipt_cannot_be_synchronously_tampered(packet):
    mutated = copy.deepcopy(packet)
    numeric_revision = next(item for item in mutated["revisions"] if item["has_numeric"])
    numeric_revision["has_numeric"] = False
    receipt = _valid_receipt(mutated)
    receipt["packet_sha256"] = canonical_sha256(mutated)
    result = validate_review_receipt(
        mutated, receipt, packet
    )
    assert result["status"] == "rejected_invalid_review"
    assert "PACKET_CORPUS_MISMATCH" in _codes(result)


def test_current_manifest_drift_is_rejected(packet):
    current_packet = copy.deepcopy(packet)
    current_packet["corpus_manifest_sha256"] = "f" * 64
    result = validate_review_receipt(packet, _valid_receipt(packet), current_packet)
    assert result["status"] == "rejected_invalid_review"
    assert "MANIFEST_HASH_MISMATCH" in _codes(result)


@pytest.mark.parametrize(
    ("field", "value"),
    [("schema_version", 999), ("receipt_type", "forged_review_receipt")],
)
def test_receipt_schema_and_type_are_frozen(packet, field, value):
    receipt = _valid_receipt(packet)
    receipt[field] = value
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "rejected_invalid_review"
    assert "RECEIPT_SCHEMA_INVALID" in _codes(result)


def test_reviewed_at_must_be_a_real_calendar_timestamp(packet):
    receipt = _valid_receipt(packet)
    receipt["primary_reviews"][0]["reviewed_at"] = "2026-99-99T99:99:99Z"
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "rejected_invalid_review"
    assert "PRIMARY_REVIEWED_AT_INVALID" in _codes(result)


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("pending", "PRIMARY_PENDING"),
        ("failed_check", "PRIMARY_CHECK_FAILED"),
        ("missing_notes", "PRIMARY_NOTES_MISSING"),
        ("duplicated_notes", "PRIMARY_NOTES_DUPLICATED"),
    ],
)
def test_primary_incomplete_or_rubber_stamp_is_blocked(packet, mutation, expected_code):
    receipt = _valid_receipt(packet)
    if mutation == "pending":
        receipt["primary_reviews"][0]["decision"] = "pending"
    elif mutation == "failed_check":
        receipt["primary_reviews"][0]["checks"]["routing_accuracy"] = "fail"
    elif mutation == "missing_notes":
        receipt["primary_reviews"][0]["notes"] = ""
    else:
        for review in receipt["primary_reviews"]:
            review["notes"] = "完全相同的批量审核说明，不允许作为逐项复核。"
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "blocked_independent_review_pending"
    assert expected_code in _codes(result)


def test_not_applicable_only_allowed_for_absent_features(packet):
    receipt = _valid_receipt(packet)
    by_id = {item["revision_id"]: item for item in packet["revisions"]}
    optional = next(
        review
        for review in receipt["primary_reviews"]
        if not by_id[review["revision_id"]]["has_numeric"]
        and not by_id[review["revision_id"]]["has_temporal_relation"]
    )
    optional["checks"]["numeric_accuracy"] = "not_applicable"
    optional["checks"]["temporal_relations"] = "not_applicable"
    assert validate_review_receipt(
        packet, receipt, packet
    )["status"] == "approved"

    required = next(
        review
        for review in receipt["primary_reviews"]
        if by_id[review["revision_id"]]["has_numeric"]
    )
    required["checks"]["numeric_accuracy"] = "not_applicable"
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "blocked_independent_review_pending"
    assert "PRIMARY_CHECK_FAILED" in _codes(result)


def test_required_second_review_cannot_be_removed(packet):
    receipt = _valid_receipt(packet)
    receipt["second_reviews"].pop()
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "blocked_independent_review_pending"
    assert "SECOND_REQUIRED_ID_MISSING" in _codes(result)
    assert "SECOND_COVERAGE_BELOW_20_PERCENT" in _codes(result)


def test_second_reviewer_must_differ_from_primary(packet):
    receipt = _valid_receipt(packet)
    revision_id = receipt["second_reviews"][0]["revision_id"]
    primary = next(
        item for item in receipt["primary_reviews"] if item["revision_id"] == revision_id
    )
    receipt["second_reviews"][0]["reviewer_id"] = primary["reviewer_id"]
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "rejected_invalid_review"
    assert "SECOND_REVIEWER_NOT_INDEPENDENT" in _codes(result)


def test_second_disagreement_or_failed_check_blocks(packet):
    receipt = _valid_receipt(packet)
    receipt["second_reviews"][0]["agrees_with_primary"] = False
    receipt["second_reviews"][0]["checks"]["independent_routing_check"] = "fail"
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "blocked_independent_review_pending"
    assert {"SECOND_DISAGREES", "SECOND_CHECK_FAILED"} <= _codes(result)


def test_mutated_second_selection_in_packet_is_rejected(packet):
    mutated = copy.deepcopy(packet)
    selected = next(
        item for item in mutated["revisions"] if item["second_review_required"]
    )
    selected["second_review_required"] = False
    receipt = _valid_receipt(mutated)
    result = validate_review_receipt(
        mutated, receipt, packet
    )
    assert result["status"] == "rejected_invalid_review"
    assert "PACKET_SECOND_SELECTION_INVALID" in _codes(result)


def test_second_review_must_cover_every_source_kind(packet):
    receipt = _valid_receipt(packet)
    by_id = {item["revision_id"]: item for item in packet["revisions"]}
    kind_counts = {}
    for review in receipt["second_reviews"]:
        kind = by_id[review["revision_id"]]["source_kind"]
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    missing_kind = next(kind for kind, count in kind_counts.items() if count == 1)
    removed_index = next(
        index
        for index, review in enumerate(receipt["second_reviews"])
        if by_id[review["revision_id"]]["source_kind"] == missing_kind
    )
    replacement_id = next(
        revision_id
        for revision_id, revision in by_id.items()
        if revision["source_kind"] != missing_kind
        and revision_id not in {item["revision_id"] for item in receipt["second_reviews"]}
    )
    replacement = copy.deepcopy(receipt["second_reviews"][removed_index])
    replacement["revision_id"] = replacement_id
    replacement["reviewer_id"] = "extra-independent-second-reviewer"
    replacement["notes"] = f"独立复核替代样本 {replacement_id} 的证据链与路由。"
    receipt["second_reviews"][removed_index] = replacement
    result = validate_review_receipt(packet, receipt, packet)
    assert result["status"] == "blocked_independent_review_pending"
    assert "SECOND_SOURCE_KIND_MISSING" in _codes(result)


def test_packet_and_validation_do_not_modify_manifest(packet):
    before = _manifest_sha256()
    receipt = _valid_receipt(packet)
    validate_review_receipt(packet, receipt, packet)
    assert _manifest_sha256() == before
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert {item["review_status"] for item in manifest["revisions"]} == {"draft"}


def test_artifact_writer_rejects_outside_gate(tmp_path):
    target = tmp_path / "forbidden.json"
    with pytest.raises(ValueError, match="output path must stay below"):
        write_artifact(target, {"status": "test"})
    assert not target.exists()
    assert not target.with_suffix(".json.tmp").exists()


def test_cli_help_exposes_packet_and_validate_commands():
    script = ROOT / "scripts" / "gold_review_gate.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0
    assert "packet" in result.stdout
    assert "validate" in result.stdout


def test_cli_rebuilds_current_packet_and_rejects_synchronized_tamper(
    packet, tmp_path, monkeypatch
):
    mutated = copy.deepcopy(packet)
    numeric_revision = next(item for item in mutated["revisions"] if item["has_numeric"])
    numeric_revision["has_numeric"] = False
    receipt = _valid_receipt(mutated)
    receipt["packet_sha256"] = canonical_sha256(mutated)
    packet_path = tmp_path / "mutated-packet.json"
    receipt_path = tmp_path / "mutated-receipt.json"
    packet_path.write_text(json.dumps(mutated, ensure_ascii=False), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
    captured = {}

    def capture_artifact(path, value):
        captured["path"] = path
        captured["value"] = value
        return Path(path)

    monkeypatch.setattr(review_gate, "write_artifact", capture_artifact)
    exit_code = review_gate.main(
        [
            "validate",
            "--corpus",
            str(CORPUS),
            "--packet",
            str(packet_path),
            "--review-receipt",
            str(receipt_path),
            "--output",
            "artifacts/gates/pytest-r1-readiness.json",
        ]
    )
    assert exit_code == 2
    assert captured["value"]["status"] == "rejected_invalid_review"
    assert "PACKET_CORPUS_MISMATCH" in _codes(captured["value"])


def _build_case(packet, revision_id):
    builder = getattr(review_gate, "build_review_case", None)
    assert callable(builder), "build_review_case must exist"
    return builder(CORPUS, packet, revision_id)


def test_case_viewer_function_exists():
    assert callable(getattr(review_gate, "build_review_case", None))


def test_case_viewer_materializes_complete_positive_case(packet):
    revision = next(
        item
        for item in packet["revisions"]
        if item["claim_ids"] and item["span_ids"] and item["route_target_ids"]
    )
    case = _build_case(packet, revision["revision_id"])
    assert case["schema_version"] == 2
    assert case["case_type"] == "gold_corpus_revision_review"
    assert case["revision"] == revision
    assert case["source"]["body"]
    assert case["source"]["untrusted_content"] is True
    assert case["annotations"]["claims"]
    assert case["annotations"]["spans"]
    assert case["annotations"]["routing"]
    assert case["verification"]["all_passed"] is True


def test_case_viewer_preserves_empty_negative_annotations(packet):
    revision = next(
        item
        for item in packet["revisions"]
        if not item["claim_ids"] and not item["span_ids"]
    )
    case = _build_case(packet, revision["revision_id"])
    assert case["annotations"]["claims"] == []
    assert case["annotations"]["spans"] == []
    assert case["verification"]["packet_annotation_ids_exact"] is True


def test_case_viewer_includes_raw_relation_objects(packet):
    revision = next(item for item in packet["revisions"] if item["relation_ids"])
    case = _build_case(packet, revision["revision_id"])
    relations = case["annotations"]["relations"]
    assert set(relations) == {"contradictions", "corrections", "supersedes"}
    assert any(relations.values())
    assert case["verification"]["relation_ids_exact"] is True


def test_case_viewer_rejects_unknown_revision(packet):
    with pytest.raises(ValueError, match="unknown revision_id"):
        _build_case(packet, "gkr-does-not-exist-v1")


def test_case_viewer_rejects_packet_tampering_before_render(packet):
    mutated = copy.deepcopy(packet)
    mutated["revisions"][0]["has_numeric"] = not mutated["revisions"][0]["has_numeric"]
    with pytest.raises(ValueError, match="PACKET_CORPUS_MISMATCH"):
        _build_case(mutated, mutated["revisions"][0]["revision_id"])


def test_case_viewer_never_emits_review_decisions(packet):
    revision_id = packet["revisions"][0]["revision_id"]
    case = _build_case(packet, revision_id)
    forbidden = {"decision", "accepted", "reviewer_id", "reviewed_at", "promotion"}

    def walk(value):
        if isinstance(value, dict):
            assert not (forbidden & set(value))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(case)


def test_case_viewer_builds_all_forty_revisions(packet):
    cases = [
        _build_case(packet, revision["revision_id"])
        for revision in packet["revisions"]
    ]
    assert len(cases) == 40
    assert {case["revision"]["revision_id"] for case in cases} == {
        revision["revision_id"] for revision in packet["revisions"]
    }
    assert all(case["verification"]["all_passed"] for case in cases)


def test_case_cli_outputs_json_to_stdout_without_artifact(packet, tmp_path, capsys):
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    revision_id = packet["revisions"][0]["revision_id"]
    exit_code = review_gate.main(
        [
            "case",
            "--corpus",
            str(CORPUS),
            "--packet",
            str(packet_path),
            "--revision-id",
            revision_id,
        ]
    )
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["revision"]["revision_id"] == revision_id
    assert not (ROOT / "artifacts" / "gates" / "pytest-case.json").exists()
