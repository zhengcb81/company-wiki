"""SR-CWP: bounded local reading and summary state over exact sources.

The local tier must read with zero model requests; the summary tier reports
the source's existing formal products.  No HTTP model server runs in this
module: any model attempt would fail the read instead of silently passing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.source_catalog.incremental_read import (
    INCREMENTAL_READ_REQUEST_SCHEMA,
    INCREMENTAL_READ_SCHEMA,
    READING_LEVEL_LOCAL,
    READING_LEVEL_SUMMARY,
    IncrementalReadRequest,
    IncrementalReadService,
    ReadResultRef,
)

from support.sr_cwp_fixtures import (
    ANNUAL_PDF_TEXT,
    TEMPLATE_PDF_TEXT,
    TRANSCRIPT_BODY,
    sha256,
    sr_cwp_readable_catalog,
)


def _service(state):
    return IncrementalReadService(catalog=state.catalog)


def _request(state, name, *, level=READING_LEVEL_LOCAL, run_id="sr-read-1"):
    ref = state.refs[name]
    return IncrementalReadRequest.from_dict({
        "schema_version": INCREMENTAL_READ_REQUEST_SCHEMA,
        "run_id": run_id,
        "reading_level": level,
        "sources": [ref.to_dict()],
        "limits": None,
    })


def _ref_dict(state, name):
    return state.refs[name].to_dict()


def test_a4_local_read_returns_located_evidence_with_zero_model(sr_cwp_readable_catalog):
    """A4: an unprocessed registered original reads back located evidence."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    response = service.read(_request(state, "call-transcript.txt"))

    assert response.to_dict()["schema_version"] == INCREMENTAL_READ_SCHEMA
    assert response.usage["model_requests"] == 0
    item, = response.items
    assert item.state == "read"
    assert item.reused is False
    assert item.result_ref is not None
    assert item.result_ref.source_ref.document_id == (
        state.refs["call-transcript.txt"].document_id
    )
    payload = service.read_result_payload(item.result_ref)
    assert payload["schema_version"] == "cwp-read-result/1"
    assert payload["model_requests"] == 0
    assert payload["selection"]["status"] == "selected"
    spans = payload["evidence_spans"]
    assert spans, "a business transcript must select located evidence"
    joined = " ".join(span["raw_text"] for span in spans)
    assert "new product" in joined and "overseas capacity" in joined
    for span in spans:
        locator = span["locator"]
        assert isinstance(locator, str) and locator
        assert span["parse_status"] == "parsed"
        assert span["source_id"] == state.refs["call-transcript.txt"].source_id


def test_a4_pdf_reads_through_the_filing_path(sr_cwp_readable_catalog):
    """A4: PDF bytes go through the PDF owner; TXT never takes that path."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    response = service.read(_request(state, "annual-report.pdf"))

    item, = response.items
    assert item.state == "read"
    payload = service.read_result_payload(item.result_ref)
    assert payload["selection"]["selected_count"] >= 1
    joined = " ".join(span["raw_text"] for span in payload["evidence_spans"])
    assert ANNUAL_PDF_TEXT[:20] in joined
    assert payload["parser"]["name"], "the parser identity is persisted"


def test_a4_template_without_business_content_is_named_skipped(sr_cwp_readable_catalog):
    """A4: a real no-narrative document is a named skip, not a failure."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    response = service.read(_request(state, "ir-policy-template.pdf"))

    item, = response.items
    assert item.state == "skipped"
    assert item.result_ref is not None
    payload = service.read_result_payload(item.result_ref)
    assert payload["selection"]["status"] == "skipped_no_narrative"
    assert payload["evidence_spans"] == []


def test_a4_second_read_of_the_same_source_reuses_the_product(sr_cwp_readable_catalog):
    """A4: the same SHA reads back the same artifact without rework."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    first = service.read(_request(state, "call-transcript.txt", run_id="run-a"))
    second = service.read(_request(state, "call-transcript.txt", run_id="run-b"))

    first_item, = first.items
    second_item, = second.items
    assert second_item.reused is True
    assert second_item.result_ref == first_item.result_ref
    # The object store did not grow: the content-addressed write deduplicated.
    objects = state.root / "catalog" / "objects"
    assert len(list(objects.rglob("*.json"))) == 1


def test_source_ref_change_is_uncertain_not_a_rerun(sr_cwp_readable_catalog):
    """A changed original behind the same ref is uncertainty, not a new read."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    stale = dict(_ref_dict(state, "call-transcript.txt"))
    stale["byte_size"] = stale["byte_size"] + 3
    request = IncrementalReadRequest.from_dict({
        "schema_version": INCREMENTAL_READ_REQUEST_SCHEMA,
        "run_id": "sr-read-stale", "reading_level": READING_LEVEL_LOCAL,
        "sources": [stale], "limits": None,
    })
    item, = service.read(request).items
    assert item.state == "uncertain"
    assert "source_ref_changed" in item.reason_codes


def test_batch_of_sources_isolates_one_failure(sr_cwp_readable_catalog):
    """One unreadable source must not block its siblings in the same batch."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    good = _ref_dict(state, "call-transcript.txt")
    stale = dict(_ref_dict(state, "annual-report.pdf"))
    stale["byte_size"] = stale["byte_size"] + 3
    request = IncrementalReadRequest.from_dict({
        "schema_version": INCREMENTAL_READ_REQUEST_SCHEMA,
        "run_id": "sr-read-mixed", "reading_level": READING_LEVEL_LOCAL,
        "sources": [good, stale], "limits": None,
    })
    items = {item.source_ref.document_id: item for item in service.read(request).items}
    assert items[good["document_id"]].state == "read"
    assert items[stale["document_id"]].state == "uncertain"


def test_batch_survives_a_retired_read_result(sr_cwp_readable_catalog):
    """A retired/reused-conflict row is one item's failure, never the batch's."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    first, = service.read(_request(state, "call-transcript.txt")).items
    assert first.state == "read"
    # The owner retires the persisted read product (a normal action).
    with state.catalog.store.transaction() as connection:
        connection.execute(
            "UPDATE narrative_read_results SET status='retired' "
            "WHERE artifact_version_id=?",
            (first.result_ref.artifact_version_id,),
        )
    good = _ref_dict(state, "annual-report.pdf")
    request = IncrementalReadRequest.from_dict({
        "schema_version": INCREMENTAL_READ_REQUEST_SCHEMA,
        "run_id": "sr-read-retired", "reading_level": READING_LEVEL_LOCAL,
        "sources": [_ref_dict(state, "call-transcript.txt"), good],
        "limits": None,
    })
    items = {item.source_ref.document_id: item for item in service.read(request).items}
    assert items[good["document_id"]].state == "read"
    assert items[state.refs["call-transcript.txt"].document_id].state == "uncertain"
    assert "read_store_error" in items[
        state.refs["call-transcript.txt"].document_id].reason_codes


def test_summary_level_reports_deferred_then_summarized(sr_cwp_readable_catalog):
    """A4: summary state derives from existing formal products, never guesses."""
    from company_wiki.source_catalog.narrative_artifact_store import (
        NARRATIVE_BUNDLE_ROLE, NarrativeArtifactDraft,
    )

    state = sr_cwp_readable_catalog
    service = _service(state)
    deferred, = service.read(_request(
        state, "call-transcript.txt", level=READING_LEVEL_SUMMARY)).items
    assert deferred.state == "deferred"
    assert "summary_batch_required" in deferred.reason_codes

    # A formal summary product exists (published by the configured batch
    # engine, whose own tests cover its production).  Publishing it here uses
    # the same artifact store, so this stays one owner's storage.
    ref = state.refs["call-transcript.txt"]
    payload = json.dumps({"bundle": "fixture"}).encode("utf-8")
    import hashlib

    policy = "a" * 64
    draft = NarrativeArtifactDraft(
        effect_id="effect-fixture-bundle", work_key="b" * 64,
        document_id=ref.document_id, source_id=ref.source_id,
        source_sha256=ref.content_sha256,
        producer_name="company_wiki.narrative_bundle", producer_version="1.0.0",
        policy_sha256=policy, selection_status="selected", quality_status="verified",
        metadata_json=json.dumps({"bundle_schema": "narrative-bundle/3.0"}),
        created_at="2026-11-21T00:00:00Z", artifact_role=NARRATIVE_BUNDLE_ROLE,
    )
    version = service._artifacts.prepare(draft, payload)
    service._artifacts.activate(draft.effect_id,
                                verified_after_hash=version.content_sha256,
                                activated_at="2026-11-21T00:00:01Z")
    summarized, = service.read(_request(
        state, "call-transcript.txt", level=READING_LEVEL_SUMMARY,
        run_id="sr-read-2")).items
    assert summarized.state == "summarized"
    assert summarized.reused is True
    assert summarized.result_ref.role == NARRATIVE_BUNDLE_ROLE
    assert summarized.result_ref.artifact_sha256 == version.content_sha256


def test_a4_two_processes_read_once_and_reuse_across_processes(
    sr_cwp_readable_catalog, tmp_path,
):
    """A4: a fresh process reads back the same product with zero new writes."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    first, = service.read(_request(state, "call-transcript.txt")).items
    assert first.state == "read"

    launcher = tmp_path / "read_worker.py"
    launcher.write_text(
        "\n".join([
            "import json, sys",
            "from pathlib import Path",
            "sys.path.insert(0, sys.argv[1])",
            "from company_wiki.source_catalog.config import load_catalog_config",
            "from company_wiki.source_catalog.service import SourceCatalog",
            "from company_wiki.source_catalog.incremental_read import (",
            "    IncrementalReadRequest, IncrementalReadService)",
            "request = IncrementalReadRequest.from_dict(json.loads(sys.argv[4]))",
            "catalog = SourceCatalog(load_catalog_config(",
            "    Path(sys.argv[3]), project_root=Path(sys.argv[2])))",
            "try:",
            "    receipt = IncrementalReadService(catalog=catalog).read(request)",
            "    print(json.dumps(receipt.to_dict()))",
            "finally:",
            "    catalog.close()",
        ]),
        encoding="utf-8",
    )
    request = _request(state, "call-transcript.txt", run_id="run-child")
    repo = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=str(repo / "src"), PYTHONUTF8="1")
    process = subprocess.run(
        [sys.executable, str(launcher), str(repo / "src"), str(state.root),
         str(state.config_path), json.dumps(request.to_dict())],
        capture_output=True, text=True, encoding="utf-8", timeout=120, env=env,
    )
    assert process.returncode == 0, process.stderr
    receipt = json.loads(process.stdout)
    child_item, = receipt["items"]
    assert child_item["state"] == "read"
    assert child_item["reused"] is True
    assert child_item["result_ref"] == json.loads(json.dumps(
        first.result_ref.to_dict()))
    assert receipt["usage"]["model_requests"] == 0
    objects = state.root / "catalog" / "objects"
    assert len(list(objects.rglob("*.json"))) == 1


def test_result_ref_roundtrip_from_wire(sr_cwp_readable_catalog):
    """The compact ref survives its wire form and re-reads the same product."""
    state = sr_cwp_readable_catalog
    service = _service(state)
    item, = service.read(_request(state, "call-transcript.txt")).items
    wire = json.loads(json.dumps(item.result_ref.to_dict()))
    restored = ReadResultRef.from_dict(wire)
    assert restored == item.result_ref
    payload = service.read_result_payload(restored)
    assert payload["selection"]["status"] == "selected"


def test_txt_transcript_bytes_are_the_parsed_original(sr_cwp_readable_catalog):
    """The transcript TXT keeps its original bytes and language."""
    state = sr_cwp_readable_catalog
    path = state.root / "companies" / "Acme" / "raw" / "call-transcript.txt"
    assert path.read_bytes() == TRANSCRIPT_BODY
    assert sha256(path.read_bytes()) == (
        state.refs["call-transcript.txt"].content_sha256
    )
    service = _service(state)
    item, = service.read(_request(state, "call-transcript.txt")).items
    payload = service.read_result_payload(item.result_ref)
    assert payload["source_metadata"]["language"] == "en"
