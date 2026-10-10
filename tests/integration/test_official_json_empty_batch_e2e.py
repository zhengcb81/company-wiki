"""Complete empty-native official JSON runs real CLI workers without an LLM."""

from __future__ import annotations

import json
import subprocess
import sys

from company_wiki.automation.models import JobStatus
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import (
    build_projection_from_refs,
    persist_projection,
)
from support import official_json_batch_fixture as fixtures
from support.official_json_batch_fixture import (
    encoded,
    invoke_batch,
    invoke_read,
    official_batch_state,
    request_for,
    sha,
    subprocess_env,
)

official_json_loopback_model = fixtures.official_json_loopback_model


def empty_subject(state):
    original = encoded({
        "success": True, "code": 200,
        "datas": [{"current": 1, "size": 1, "pages": 1, "total": 1,
                   "records": [{"id": 901, "companyId": 47,
                                "content": "", "questionContent": "", "isAnswered": True,
                                "crtTime": "2026-09-01 10:00:00",
                                "updTime": "2026-09-02 10:00:00"}]}],
    })
    captured = import_official_json_source(state.catalog, original=original, request={
        "schema_version": "official-source-import-request/2",
        "request_id": "empty-native-page", "max_bytes": 1048576,
        "content_sha256": sha(original), "mime_type": "application/json",
        "document_kind": "investor_relations",
        "source_subject": {"kind": "multi_issuer_event",
                           "event_namespace": "offline-empty-fixture", "event_id": "901",
                           "issuer_refs": [], "attribution_status": "partial"},
        "capture_receipt": {"capture_method": "local_document", "tool_name": "offline-fixture",
                            "tool_call_id": "empty-page-1", "captured_at": "2026-10-10T00:00:00Z",
                            "response_bytes": len(original), "content_sha256": sha(original)},
    })
    projection = build_projection_from_refs(
        state.catalog, refs=[captured["source_ref"]], layout_id="official-paged-qa",
        issuer={"provider_company_id": 47}, as_of_date="2026-10-08")
    persist_projection(state.catalog, projection)
    subject = NarrativeSubject.from_projection(projection)
    # Extend the fixture's immutable-byte exit checks to this lane's own original.
    state.originals.update({p: p.read_bytes() for p in (state.root / "companies").rglob("*")
                            if p.is_file()})
    originals = [p for p in state.originals if not p.name.endswith(".source.json")
                 and sha(state.originals[p]) == sha(original)]
    assert len(originals) == 1
    return subject, originals[0], original


def assert_zero_budget(state, run_id, receipt):
    assert receipt["budget"] == {"tokens": 0, "estimated_micro_usd": 0,
                                 "unknown_reservations": 0, "unsettled_reservations": 0}
    ledger = NarrativeRunStore(state.automation_db)
    assert ledger.reservations_for_run(run_id) == ()
    snapshot = ledger.budget_snapshot(run_id)
    assert snapshot.charged_tokens == snapshot.charged_micro_usd == 0
    assert snapshot.unknown_reservations == snapshot.unsettled_reservations == 0


def assert_terminal(state, subject, reference):
    run = NarrativeRunStore(state.automation_db).get_run("empty-first")
    assert run is not None and len(run.job_ids) == 3
    store = AutomationStore(state.automation_db)
    jobs = store.list_jobs(job_ids=run.job_ids)
    assert {job.job_type for job in jobs} == {
        "source.narrative_select", "source.narrative_summarize", "source.narrative_verify"}
    for job in jobs:
        assert job.subject_id == subject.item_key and job.status is JobStatus.SUCCEEDED
        attempts = store.list_attempts(job.job_id)
        assert len(attempts) == 1
        body = json.loads(attempts[0].result_json)
        assert body["metrics"]["tokens"] == 0 and body["metrics"]["cost_usd"] == 0
        result = body["result"]
        assert result["schema_version"] == "narrative-terminal-receipt/2.0"
        assert "summary" not in result and "evidence_spans" not in result
        pin = result["final_artifact"]
        assert pin["subject_binding"] == subject.to_dict()
        assert pin["generation_sha256"] == reference["generation_sha256"]
        assert pin["artifact_version_id"] == reference["artifact_version_id"]
        assert "source_id" not in pin and "document_id" not in pin


def assert_public_empty_read(state, subject, reference):
    wire, receipt = invoke_read(state, reference, issuer=subject.issuer)
    bundle = NarrativeBundle.from_dict(wire)
    assert bundle.subject == subject
    assert bundle.source_metadata.language == "unknown"
    assert bundle.summary.status == "summary_not_needed" and bundle.summary.draft is None
    assert bundle.summary.translate is False
    assert bundle.selection.status == "skipped_no_narrative"
    assert bundle.selection.coverage_complete and bundle.selection.selected_count == 0
    assert not bundle.evidence_spans
    assert receipt["replay_status"] == "verified"
    request = {"schema_version": "narrative-read-request/2", "narrative_ref": reference,
               "as_of_date": "2026-10-08", "expected_issuer": {"provider_company_id": 47}}
    listed = subprocess.run(
        [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli",
         "--config", str(state.config_path), "--operation", "evidence-list"],
        input=encoded(request), cwd=state.root, env=subprocess_env(),
        capture_output=True, timeout=30)
    assert listed.returncode == 0, listed.stderr.decode(errors="replace")
    view, list_receipt = json.loads(listed.stdout), json.loads(listed.stderr)
    assert view["total"] == 0 and view["items"] == []
    assert list_receipt["locator_count"] == 0 and list_receipt["replay_status"] == "verified"
    assert list_receipt["view_sha256"] == sha(listed.stdout)
    assert b"absolute_path" not in listed.stdout + listed.stderr


def test_complete_empty_native_projection_cli_skips_model_publishes_reads_compacts_and_reuses(
    tmp_path, official_json_loopback_model
):
    before = tuple(tmp_path.iterdir())
    server = official_json_loopback_model
    with official_batch_state(tmp_path) as state:
        subject, original_path, original = empty_subject(state)
        items = [{"kind": "official_json", "projection_id": subject.item_key,
                  "projection_sha256": subject.subject_sha256}]
        first_path = request_for(state, server.endpoint, "empty-first", items=items)
        process, first = invoke_batch(state, first_path, "empty-first")
        assert process.returncode == 0 and first["status"] == "completed", (first, process.stderr)
        assert len(first["items"]) == 1
        item = first["items"][0]
        assert item["item_key"] == subject.item_key and item["kind"] == "official_json"
        assert item["status"] == "completed" and item["errors"] == []
        reference = item["artifact_ref"]
        assert reference["schema_version"] == "narrative-ref/2"
        assert reference["subject_binding"] == subject.to_dict()
        assert_zero_budget(state, "empty-first", first)
        assert_terminal(state, subject, reference)
        assert_public_empty_read(state, subject, reference)
        assert server.requests == [] and server.errors == []
        assert original_path.read_bytes() == original

        reuse_path = request_for(state, server.endpoint, "empty-reuse", items=items)
        reuse_process, reused = invoke_batch(state, reuse_path, "empty-reuse")
        assert reuse_process.returncode == 0 and reused["status"] == "completed", reused
        assert len(reused["items"]) == 1 and reused["items"][0]["artifact_ref"] == reference
        assert_zero_budget(state, "empty-reuse", reused)
        run = NarrativeRunStore(state.automation_db).get_run("empty-reuse")
        assert run is not None and run.job_ids == (), "reuse must not spawn another document DAG"
        assert_public_empty_read(state, subject, reference)
        assert_terminal(state, subject, reference)
        assert server.requests == [] and server.errors == []
        assert {p: p.read_bytes() for p in state.originals} == state.originals
    assert tuple(tmp_path.iterdir()) == before
