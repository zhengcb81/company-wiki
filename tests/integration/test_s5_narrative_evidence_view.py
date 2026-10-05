"""Public selected retrieval uses pinned final bytes and verifies immutable raw.

Real handlers/projector and subprocess protocol; no external model or network.
Every fixture removes its scratch lake, including downloaded-source copies.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactDraft
from support.narrative_transport_fixture import published_fixture


REPO = Path(__file__).resolve().parents[2]
VIEW_SCHEMA = "narrative-evidence-view/1"
RECEIPT_SCHEMA = "narrative-evidence-read-receipt/1"
RECEIPT_KEYS = {
    "schema_version", "status", "view_sha256", "byte_size", "narrative_ref",
    "as_of_date", "source_read_policy_sha256", "replay_status", "locator_count",
}


def _persistent_files(root):
    # Live SQLite SHM read marks coordinate readers; every persistent byte stays.
    return tuple((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                 for path in sorted(root.rglob("*")) if path.is_file() and not path.name.endswith("-shm"))


def _request(fixture, *, as_of_date="2026-09-01"):
    reference = NarrativeTransportReader(fixture.artifacts, fixture.reader).reference(
        fixture.source_ref,
    )
    return fixture.read_request(reference, as_of_date=as_of_date)


def _cli(config_path, request, operation, *options):
    return subprocess.run(
        [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli",
         "--config", str(config_path), "--operation", operation, *options],
        input=canonical_json(request).encode("utf-8"), capture_output=True,
        cwd=config_path.parent, timeout=40,
        env=dict(os.environ, PYTHONPATH=str(REPO / "src"),
                 PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1",
                 COMPANY_WIKI_NETWORK="blocked"),
    )


def _success(result, request, operation, locator_count):
    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert result.stderr.count(b"\n") == 1
    view, receipt = json.loads(result.stdout), json.loads(result.stderr)
    assert view["schema_version"] == VIEW_SCHEMA
    assert view["operation"] == operation
    assert view["narrative_ref"] == request["narrative_ref"]
    assert set(receipt) == RECEIPT_KEYS
    assert receipt["schema_version"] == RECEIPT_SCHEMA
    assert receipt["narrative_ref"] == request["narrative_ref"]
    assert receipt["status"] == "ok"
    assert receipt["replay_status"] == "verified"
    assert receipt["locator_count"] == locator_count  # All final locators, not the page.
    assert receipt["view_sha256"] == hashlib.sha256(result.stdout).hexdigest()
    assert receipt["byte_size"] == len(result.stdout)
    assert b"absolute_path" not in result.stdout + result.stderr
    assert b"root_path" not in result.stdout + result.stderr
    assert "summary" not in view
    return view


@pytest.mark.parametrize("kind", ["txt", "pdf", "skip", "chinese"])
def test_final_list_lookup_and_search_work_without_legacy_spans(tmp_path, kind):
    spec = None
    if kind == "chinese":
        spec = {"data": ("Full Conference Call Transcript\n"
                         "CEO: 公司新产品已完成客户验证，海外业务新增量产订单。\n"
                         "Questions & Answers\n").encode("utf-8"), "language": "zh"}
    with published_fixture(tmp_path, kind="txt" if kind == "chinese" else kind,
                           source_spec=spec) as fixture:
        assert fixture.catalog.store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"] == 0
        request = _request(fixture)
        bundle = json.loads(fixture.payload)
        spans = bundle["evidence_spans"]
        before = _persistent_files(fixture.root)
        listed = _success(_cli(fixture.config_path, request, "evidence-list"), request,
                          "evidence-list", len(spans))
        assert listed["items"] == spans
        assert listed["total"] == len(spans)
        assert listed["selection"] == bundle["selection"]
        assert listed["quality_status"] == bundle["quality_status"]
        assert listed["versions"] == bundle["versions"]
        assert listed["manifest"]["source_id"] == fixture.source_ref.source_id
        query = "海外" if kind == "chinese" else "overseas capacity"
        searched = _success(_cli(fixture.config_path, request, "evidence-search", "--query", query),
                            request, "evidence-search", len(spans))
        if kind == "skip":
            assert not spans
            assert listed["selection"]["status"] == "skipped_no_narrative"
            assert searched["total"] == 0 and searched["items"] == []
        else:
            assert spans and searched["items"]
            anchors = {span["span_id"]: span["locator"] for span in spans}
            for item in searched["items"]:
                assert item["source_id"] == fixture.source_ref.source_id
                assert item["source_sha256"] == fixture.source_ref.content_sha256
                assert item["selection_status"] == bundle["selection"]["status"]
                assert item["coverage_complete"] == bundle["selection"]["coverage_complete"]
                assert all(anchors[eid] == locator for eid, locator in
                           zip(item["evidence_ids"], item["locators"], strict=True))
            for flag, field in (("--span-id", "span_id"), ("--locator", "locator")):
                found = _success(_cli(fixture.config_path, request, "evidence-lookup",
                                      flag, spans[0][field]), request, "evidence-lookup", len(spans))
                assert found["items"] == [spans[0]] and found["total"] == 1
        assert not (fixture.catalog.config.catalog_dir / "derived").exists()
        assert _persistent_files(fixture.root) == before


def test_pagination_is_stable_and_search_empty_result_is_explicit(tmp_path):
    text = ("Full Conference Call Transcript\n"
            "CEO: We launched a new product for industrial customers.\n\n"
            "CEO: We expanded overseas capacity with new customer orders.\n\n"
            "CEO: We launched a second product and opened a new factory.\n\n"
            "CEO: Customer validation of our new business is complete.\n"
            "Questions & Answers\n")
    with published_fixture(tmp_path, source_spec={"data": text.encode()}) as fixture:
        request = _request(fixture)
        spans = json.loads(fixture.payload)["evidence_spans"]
        assert len(spans) >= 2
        first = _success(_cli(fixture.config_path, request, "evidence-list", "--limit", "1"),
                         request, "evidence-list", len(spans))
        second = _success(_cli(fixture.config_path, request, "evidence-list", "--limit", "1",
                              "--offset", "1"), request, "evidence-list", len(spans))
        assert first["items"] == spans[:1]
        assert second["items"] == spans[1:2]
        assert second["offset"] == 1 and second["limit"] == 1
        beyond = _success(_cli(fixture.config_path, request, "evidence-list", "--offset", "999"),
                          request, "evidence-list", len(spans))
        assert beyond["items"] == [] and beyond["total"] == len(spans)
        no_hit = _success(_cli(fixture.config_path, request, "evidence-search", "--query", "xyzunmatched"),
                          request, "evidence-search", len(spans))
        assert no_hit["total"] == 0 and no_hit["items"] == []


def test_old_reference_remains_pinned_when_new_partial_version_is_visible(tmp_path):
    with published_fixture(tmp_path) as fixture:
        old_request = _request(fixture)
        changed = json.loads(fixture.payload)
        changed["quality_status"] = "needs_review"
        changed["selection"]["status"] = "partial"
        changed["selection"]["coverage_complete"] = False
        changed["selection"]["candidate_count"] += 1
        changed["selection"]["omitted_candidate_count"] += 1
        old = fixture.version
        draft = NarrativeArtifactDraft(
            effect_id="view-second", work_key="d" * 64,
            document_id=old.document_id, source_id=old.source_id,
            source_sha256=old.source_sha256, producer_name=old.producer_name,
            producer_version=old.producer_version, policy_sha256=old.policy_sha256,
            selection_status="partial", quality_status="needs_review", metadata_json=old.metadata_json,
            created_at="2026-10-01T00:00:00Z",
        )
        version = fixture.artifacts.prepare(draft, canonical_json(changed).encode())
        fixture.artifacts.activate(draft.effect_id, verified_after_hash=version.content_sha256,
                                   activated_at="2026-10-01T00:00:01Z")
        new_request = _request(fixture)
        assert new_request["narrative_ref"]["artifact_version_id"] != old_request["narrative_ref"]["artifact_version_id"]
        n = len(changed["evidence_spans"])
        old_view = _success(_cli(fixture.config_path, old_request, "evidence-list"),
                            old_request, "evidence-list", n)
        new_view = _success(_cli(fixture.config_path, new_request, "evidence-search", "--query", "overseas"),
                            new_request, "evidence-search", n)
        assert old_view["selection"] == json.loads(fixture.payload)["selection"]
        assert new_view["selection"] == changed["selection"]
        assert new_view["quality_status"] == "needs_review"
        assert new_view["items"]
        assert all(hit["selection_status"] == "partial" and not hit["coverage_complete"]
                   for hit in new_view["items"])


@pytest.mark.parametrize("operation,options", [
    ("reference", ["--limit", "1"]), ("read", ["--query", "sales"]),
    ("evidence-list", ["--query", "sales"]),
    ("evidence-list", ["--limit", "0"]), ("evidence-list", ["--limit", "501"]),
    ("evidence-list", ["--offset", "-1"]),
    ("evidence-lookup", []),
    ("evidence-lookup", ["--span-id", "a", "--locator", "loc:v1/page:1"]),
    ("evidence-lookup", ["--span-id", "a", "--limit", "1"]),
    ("evidence-search", []), ("evidence-search", ["--query", "  "]),
    ("evidence-search", ["--query", "x" * 4097]),
])
def test_invalid_operation_filters_refuse_before_catalog_or_raw_read(tmp_path, operation, options):
    before = tuple(tmp_path.iterdir())
    result = _cli(tmp_path / "missing.yaml", {}, operation, *options)
    assert result.returncode == 2
    assert result.stdout == b""
    assert json.loads(result.stderr)["reason"] == "invalid_request"
    assert tuple(tmp_path.iterdir()) == before


@pytest.mark.parametrize("fault,reason", [
    ("raw_bytes", "no_verified_location"), ("final_bytes", "narrative_artifact_corrupt"),
    ("reference_hash", "artifact_reference_mismatch"),
    ("reference_version", "narrative_artifact_not_visible"),
    ("as_of", "source_after_as_of"), ("identity", "source_identity_mismatch"),
    ("unknown_locator", "narrative_evidence_not_found"),
])
def test_query_keeps_source_replay_and_exact_version_refusals(tmp_path, fault, reason):
    with published_fixture(tmp_path) as fixture:
        request = _request(fixture, as_of_date="2026-01-01" if fault == "as_of" else "2026-09-01")
        object_path = fixture.catalog.config.catalog_dir / fixture.version.object_key
        if fault == "raw_bytes":
            fixture.raw_path.write_bytes(b"X" * len(fixture.raw_bytes))
        elif fault == "final_bytes":
            object_path.write_bytes(b"X" * len(fixture.payload))
        elif fault == "reference_hash":
            request["narrative_ref"]["artifact_sha256"] = "0" * 64
        elif fault == "reference_version":
            request["narrative_ref"]["artifact_version_id"] = "unknown-version"
        elif fault == "identity":
            request["expected_source"]["canonical_entity_id"] = "another-entity"
        options = ["--locator", "loc:v1/page:999/paragraph:999"] if fault == "unknown_locator" else []
        operation = "evidence-lookup" if fault == "unknown_locator" else "evidence-list"
        try:
            result = _cli(fixture.config_path, request, operation, *options)
            assert result.returncode == 2 and result.stdout == b""
            assert json.loads(result.stderr)["reason"] == reason
            if fault == "raw_bytes":
                assert json.loads(result.stderr)["status"] == "unavailable"
        finally:
            fixture.raw_path.write_bytes(fixture.raw_bytes)
            object_path.write_bytes(fixture.payload)


def test_real_transcript_search_lookup_and_directory_restoration(tmp_path):
    original = (REPO.parent / "earnings-transcripts/earnings-transcripts/transcripts/MSFT"
                / "MSFT_Q4_2026_earnings_call.txt")
    data = original.read_bytes()
    digest = "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a"
    assert hashlib.sha256(data).hexdigest() == digest
    before = tuple(tmp_path.iterdir())
    with published_fixture(tmp_path, source_spec={"data": data, "title": "MSFT Q4 2026 earnings call"}) as fixture:
        request = _request(fixture)
        spans = json.loads(fixture.payload)["evidence_spans"]
        search = _success(_cli(fixture.config_path, request, "evidence-search", "--query", "Azure",
                              "--limit", "2"), request, "evidence-search", len(spans))
        assert search["items"] and search["limit"] == 2
        hit = search["items"][0]
        for evidence_id, locator in zip(hit["evidence_ids"], hit["locators"], strict=True):
            lookup = _success(_cli(fixture.config_path, request, "evidence-lookup", "--span-id", evidence_id),
                              request, "evidence-lookup", len(spans))
            assert lookup["items"][0]["locator"] == locator
            assert any(span["span_id"] == evidence_id and span == lookup["items"][0] for span in spans)
        assert hashlib.sha256(fixture.raw_path.read_bytes()).hexdigest() == digest
    assert tuple(tmp_path.iterdir()) == before
    assert hashlib.sha256(original.read_bytes()).hexdigest() == digest
