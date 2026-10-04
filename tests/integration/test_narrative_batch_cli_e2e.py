"""Actual finite batch CLI, spawned production workers and bounded local HTTP."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.automation.models import RuntimeState
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_projection import NarrativeBundleReader
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.narrative_artifact_store import LocalNarrativeObjectStore, NarrativeArtifactStore

from support import narrative_batch_fixtures as batch_fixtures
from support.narrative_batch_fixtures import (
    KEY, KEY_ENV, T0, assert_originals_and_foreign_jobs_untouched,
    foreign_ready_jobs, isolated_batch_directory, prepare_source_catalog,
)


loopback_model_server = batch_fixtures.loopback_model_server


def _prepare(
    root,
    endpoint,
    *,
    one_source=False,
    zero_budget=False,
    sparse_metadata=False,
    include_mixed=False,
    include_annual_pdf=False,
    include_policy=True,
):
    state = prepare_source_catalog(
        root,
        one_source=one_source,
        sparse_metadata=sparse_metadata,
        include_mixed=include_mixed,
        include_annual_pdf=include_annual_pdf,
        include_policy=include_policy,
    )
    try:
        state.store = AutomationStore(root / "automation.db")
        state.store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
        scheduler = AutomationScheduler(state.store, create_default_registry(),
                                        PolicyConfig(allow_llm=True, allow_network=True))
        state.outside = foreign_ready_jobs(state, state.store, scheduler)
        state.store.set_runtime_gate(RuntimeState.PAUSED, updated_at=T0)
        request = NarrativeBatchRequest.from_dict({
            "schema_version": "narrative-batch-request/1", "run_id": "cli-e2e",
            "sources": [{"schema_version": ref.schema_version, "document_id": ref.document_id,
                         "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                         "byte_size": ref.byte_size, "mime_type": ref.mime_type}
                        for ref, _language, _kind in state.indexed.values()],
            "profile": "P2", "max_seconds": 40, "max_tokens": 200_000,
            "max_cost_usd": "0" if zero_budget else "2",
            "model": {"model_id": "stub-model", "endpoint": endpoint, "api_key_env": KEY_ENV,
                      "max_output_tokens": 400, "timeout_seconds": 5, "allow_local_http": True},
            "pricing": {"version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1_000_000,
                        "output_micro_usd_per_million_tokens": 2_000_000},
        })
        state.request_path = root / "request.json"
        state.request_path.write_text(json.dumps(request.to_dict(), ensure_ascii=False), encoding="utf-8")
        assert KEY not in state.request_path.read_text(encoding="utf-8")
        return state
    except BaseException:
        state.catalog.close()
        raise


def _invoke(state):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHON_DOTENV_DISABLED"] = "1"
    process = subprocess.run([
        sys.executable, "-m", "company_wiki.automation.narrative_batch_cli",
        "--project-root", str(state.root), "--catalog-config", str(state.config_path),
        "--automation-db", str(state.store.db_path), "--work-dir", str(state.root / "run-work"),
        "--request", str(state.request_path),
    ], cwd=state.root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert KEY not in process.stdout + process.stderr
    assert process.stdout.strip(), process.stderr
    result = json.loads(process.stdout)
    assert isinstance(result, dict) and result["schema_version"] == "narrative-batch-result/1"
    assert result["run_id"] == "cli-e2e"
    return process, result


def _originals(state):
    return {path: path.read_bytes() for path in (state.root / "companies").rglob("*") if path.is_file()}


@pytest.mark.parametrize("sparse_metadata", [False, True])
def test_cli_p2_publishes_two_languages_and_skips_policy_without_model_call(
    tmp_path_factory, loopback_model_server, sparse_metadata
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(
            root,
            loopback_model_server.endpoint,
            sparse_metadata=sparse_metadata,
        )
        try:
            originals = _originals(state)
            process, result = _invoke(state)
            assert process.returncode == 0 and result["status"] == "completed", (process.stderr, result)
            assert loopback_model_server.errors == [] and len(loopback_model_server.requests) == 2
            assert {data["source"]["language"] for data, _body in loopback_model_server.requests} == {"en", "zh"}
            assert result["budget"]["tokens"] == 184 and result["budget"]["estimated_micro_usd"] == 222
            assert result["budget"]["unknown_reservations"] == 0
            assert result["budget"]["unsettled_reservations"] == 0
            documents = {item["document_id"]: item for item in result["documents"]}
            assert documents.keys() == state.indexed.keys()
            artifacts = NarrativeArtifactStore(state.catalog.store, LocalNarrativeObjectStore(state.catalog.config.catalog_dir))
            reader = NarrativeBundleReader(artifacts)
            artifact_refs = {}
            for document_id, (ref, language, kind) in state.indexed.items():
                item = documents[document_id]
                assert isinstance(item["status"], str) and item["status"]
                loaded = reader.read(document_id=document_id, source_id=ref.source_id, source_sha256=ref.content_sha256)
                artifact_ref = item["artifact_ref"]
                assert artifact_ref["artifact_version_id"] == loaded.artifact.artifact_version_id
                assert artifact_ref["content_sha256"] == loaded.artifact.content_sha256
                assert artifact_ref["byte_size"] == loaded.artifact.byte_size
                assert loaded.bundle.source_metadata.language == language and loaded.bundle.summary.translate is False
                if kind == "ir_policy":
                    assert loaded.bundle.selection.status == "skipped_no_narrative"
                    assert loaded.bundle.summary.status == "summary_not_needed"
                else:
                    assert loaded.bundle.summary.draft.language == language
                    claim = loaded.bundle.summary.draft.claims[0].text
                    assert claim in " ".join(span.raw_text for span in loaded.bundle.evidence_spans)
                    assert ("新产品" in claim) if language == "zh" else ("new product" in claim)
                artifact_refs[document_id] = artifact_ref
            again, repeated = _invoke(state)
            assert again.returncode == 0 and repeated["status"] == "completed", (again.stderr, repeated)
            assert len(loopback_model_server.requests) == 2
            assert {item["document_id"]: item["artifact_ref"] for item in repeated["documents"]} == artifact_refs
            assert repeated["budget"] == result["budget"]
            assert_originals_and_foreign_jobs_untouched(state, originals,
                output=process.stdout + process.stderr + again.stdout + again.stderr)
            # A completed-run resume must re-read the original bytes, and a
            # refusal must retain the real charge already paid by that run.
            path = state.raw_paths["call-en.txt"]
            path.write_bytes(path.read_bytes() + b"Changed after completed publication.\n")
            changed_originals = _originals(state)
            changed, refused = _invoke(state)
            assert changed.returncode == 2 and refused["status"] == "failed", (changed.stderr, refused)
            assert len(loopback_model_server.requests) == 2 and refused["budget"] == result["budget"]
            assert_originals_and_foreign_jobs_untouched(state, changed_originals, output=changed.stdout + changed.stderr)
        finally:
            state.catalog.close()


def test_cli_infers_sparse_languages_from_verified_pdf_and_transcript_bytes(
    tmp_path_factory, loopback_model_server
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(
            root,
            loopback_model_server.endpoint,
            sparse_metadata=True,
            include_mixed=True,
            include_annual_pdf=True,
            include_policy=False,
        )
        try:
            originals = _originals(state)
            process, result = _invoke(state)
            assert process.returncode == 0 and result["status"] == "completed", (process.stderr, result)
            assert loopback_model_server.errors == [] and len(loopback_model_server.requests) == 4
            assert {data["source"]["language"] for data, _body in loopback_model_server.requests} == {
                "en", "zh", "mixed",
            }
            assert all(data["constraints"]["translate"] is False for data, _body in loopback_model_server.requests)

            documents = {item["document_id"]: item for item in result["documents"]}
            assert documents.keys() == state.indexed.keys()
            artifacts = NarrativeArtifactStore(
                state.catalog.store,
                LocalNarrativeObjectStore(state.catalog.config.catalog_dir),
            )
            reader = NarrativeBundleReader(artifacts)
            for document_id, (ref, expected_language, kind) in state.indexed.items():
                loaded = reader.read(
                    document_id=document_id,
                    source_id=ref.source_id,
                    source_sha256=ref.content_sha256,
                )
                assert loaded.bundle.source_metadata.language == expected_language
                assert loaded.bundle.summary.translate is False
                if kind == "ir_policy":
                    assert loaded.bundle.selection.status == "skipped_no_narrative"
                else:
                    assert loaded.bundle.summary.draft.language == expected_language

            again, repeated = _invoke(state)
            assert again.returncode == 0 and repeated["status"] == "completed", (again.stderr, repeated)
            assert len(loopback_model_server.requests) == 4
            assert_originals_and_foreign_jobs_untouched(
                state,
                originals,
                output=process.stdout + process.stderr + again.stdout + again.stderr,
            )
        finally:
            state.catalog.close()


@pytest.mark.parametrize("failure", ["zero-budget", "changed-source-sha", "tiny-storage-cap"])
def test_cli_refuses_model_work_without_http_or_overwriting_originals(tmp_path_factory, loopback_model_server, failure):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True, zero_budget=failure == "zero-budget")
        try:
            if failure == "changed-source-sha":
                path = state.raw_paths["call-en.txt"]
                path.write_bytes(path.read_bytes() + b"Changed after the frozen source reference.\n")
            elif failure == "tiny-storage-cap":
                request = json.loads(state.request_path.read_text(encoding="utf-8"))
                request["max_persistent_bytes"] = 4096
                state.request_path.write_text(json.dumps(request), encoding="utf-8")
            originals = _originals(state)
            process, result = _invoke(state)
            expected = {"zero-budget": "budget_exhausted", "changed-source-sha": "failed",
                        "tiny-storage-cap": "storage_exhausted"}[failure]
            assert process.returncode == 2 and result["status"] == expected, (process.stderr, result)
            assert loopback_model_server.errors == [] and loopback_model_server.requests == []
            assert {item["document_id"] for item in result["documents"]} == state.indexed.keys()
            assert all(isinstance(item["status"], str) and item["status"] for item in result["documents"])
            assert all(item.get("artifact_ref") is None for item in result["documents"])
            assert result["budget"]["tokens"] == 0 and result["budget"]["estimated_micro_usd"] == 0
            assert result["budget"]["unknown_reservations"] == 0 and result["budget"]["unsettled_reservations"] == 0
            run_store = NarrativeRunStore(state.store.db_path)
            if run_store.get_run("cli-e2e") is not None:
                assert run_store.reservations_for_run("cli-e2e") == ()
            if failure == "tiny-storage-cap":
                assert {job.job_id for job in state.store.list_jobs()} == {job.job_id for job in state.outside}
            assert state.store.list_outbox_entries(status="pending") == ()
            assert_originals_and_foreign_jobs_untouched(state, originals, output=process.stdout + process.stderr)
        finally:
            state.catalog.close()


def test_cli_persists_safe_http_status_and_unknown_charge_without_provider_body(
    tmp_path_factory, loopback_model_server,
):
    sentinel = b"PROVIDER_ERROR_BODY_SENTINEL"
    loopback_model_server.response_status = 400
    loopback_model_server.error_body = sentinel + KEY.encode()
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True)
        try:
            originals = _originals(state)
            process, result = _invoke(state)
            assert process.returncode == 2 and result["status"] == "failed"
            assert len(loopback_model_server.requests) == 1
            assert loopback_model_server.errors == []
            run_store = NarrativeRunStore(state.store.db_path)
            reservations = run_store.reservations_for_run("cli-e2e")
            assert len(reservations) == 1
            record = reservations[0]
            assert record.error_code == "MODEL_HTTP_CLIENT_ERROR"
            assert record.usage_status == "unknown"
            assert record.charged_tokens == record.reserved_tokens > 0
            assert result["budget"]["tokens"] == record.reserved_tokens
            assert result["budget"]["unknown_reservations"] == 1
            assert record.output_bytes == 0 and record.response_sha256 is None
            attempt = state.store.get_attempt(record.attempt_id)
            assert attempt.error_code == "MODEL_HTTP_CLIENT_ERROR"
            assert attempt.error_detail == (
                "metered model attempt did not complete (http_status=400)"
            )
            assert sentinel.decode() not in process.stdout + process.stderr
            assert sentinel not in state.store.db_path.read_bytes()
            assert KEY.encode() not in state.store.db_path.read_bytes()
            assert_originals_and_foreign_jobs_untouched(
                state, originals, output=process.stdout + process.stderr,
            )
        finally:
            state.catalog.close()
