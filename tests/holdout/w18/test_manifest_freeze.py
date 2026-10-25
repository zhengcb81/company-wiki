# -*- coding: utf-8 -*-
"""Frozen-manifest structural acceptance for the W18 three-market holdout set.

These checks run against the committed manifest/gold only: no original file,
no network, no model call.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.holdout_replay.manifest import (
    ManifestError,
    load_manifest,
    verify_manifest_gold,
)

MANIFEST = Path(__file__).resolve().parents[3] / "tools" / "holdout_replay" / "manifest.json"


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(MANIFEST)


def test_manifest_loads_and_gold_matches(manifest):
    rows = verify_manifest_gold(manifest, MANIFEST)
    assert len(rows) == manifest["sample_count"] == 8
    assert all(row["facts"] >= 4 for row in rows)


def test_manifest_not_marked_frozen_refuses(tmp_path):
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))
    record["frozen_before_candidate_output"] = False
    broken = tmp_path / "manifest.json"
    broken.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(broken)


def test_duplicate_original_sha_refuses(tmp_path):
    # one material cannot impersonate two independent originals (review D3)
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))
    twin = json.loads(json.dumps(record["samples"][0]))
    twin["sample_id"] = "w18-duplicate-original"
    twin["gold_file"] = record["samples"][0]["gold_file"]
    record["samples"] = [record["samples"][0], twin]
    broken = tmp_path / "manifest.json"
    broken.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(broken)


def test_h01_three_markets_and_minimum_counts(manifest):
    samples = manifest["samples"]
    assert len(samples) >= 6
    markets = {s["market"] for s in samples}
    assert {"CN", "HK", "US"} <= markets
    companies = {s["identity_evidence"]["entity"] for s in samples}
    assert len(companies) >= 3
    # one physical original per sample: distinct source SHAs, no double roles
    shas = [s["source_ref"]["content_sha256"] for s in samples]
    assert len(set(shas)) == len(shas)


def test_h01_document_type_coverage(manifest):
    kinds = {s["document_kind"] for s in samples} if (samples := manifest["samples"]) else set()
    assert "annual_report" in kinds
    assert {"semi_annual_report", "quarterly_report"} & kinds
    assert "investor_call_transcript" in kinds
    assert "investor_relations" in kinds
    assert "prospectus" in kinds
    # the governance/procedural negative example
    negatives = [s for s in manifest["samples"] if s["document_kind"] == "ir_policy"]
    assert len(negatives) == 1
    assert "负例" in negatives[0]["designated_trap"]


def test_h01_two_carriers_minimum(manifest):
    carriers = {s["carrier"] for s in manifest["samples"]}
    assert {".pdf", ".docx", ".html"} <= carriers


def test_h02_prior_use_recorded_for_every_sample(manifest):
    for sample in manifest["samples"]:
        prior = sample["prior_use"]
        assert prior["status"] in {"fresh", "local-unseen", "development"}
        assert prior.get("known_prior_sightings"), sample["sample_id"]
    statuses = {s["prior_use"]["status"] for s in manifest["samples"]}
    # honest split: at least one explicit local-unseen, none claimed blindly
    assert "local-unseen" in statuses


def test_h05_identity_never_from_directory_name(manifest):
    for sample in manifest["samples"]:
        identity = sample["identity_evidence"]
        assert identity.get("method")
        assert identity.get("evidence")
        assert identity.get("security_id") and identity.get("entity")
        # no physical path may leak into the manifest
        assert "companies/" not in json.dumps(sample)


def test_h03_reading_scope_is_explicit(manifest):
    for sample in manifest["samples"]:
        scope = sample["reading_scope"]
        assert scope, sample["sample_id"]
        assert any(key.startswith("fully_read") for key in scope)


def test_h04_gold_fact_obligations():
    gold_dir = MANIFEST.parent / "gold"
    from tools.document_understanding_benchmark.records import validate_gold

    total = 0
    for path in sorted(gold_dir.glob("w18-*.json")):
        gold = validate_gold(json.loads(path.read_text(encoding="utf-8")))
        facts = gold["facts"]
        total += len(facts)
        if path.stem.endswith("charter"):
            assert len(facts) >= 3  # governance negative may carry fewer targets
        else:
            assert 8 <= len(facts) <= 15, f"{path.stem}: {len(facts)} facts outside 8-15"
        for fact in facts:
            assert fact["target_kind"] in {
                "required_business", "disposition_context", "correctness_if_emitted"}
            assert fact["must_preserve"], fact["id"]
            assert fact["must_not_assert"], fact["id"]
            assert fact["modality"] != "unknown" or fact["quantity_basis"] != "unknown"
        kinds = {f["target_kind"] for f in facts}
        # business samples must carry mandatory business targets; the
        # governance negative sample legitimately has none of them
        if not path.stem.endswith("charter"):
            assert "required_business" in kinds
    assert total >= 90
