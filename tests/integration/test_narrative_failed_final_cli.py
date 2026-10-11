"""One isolated public CLI chain; local length response never becomes a bundle."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from company_wiki.automation.models import JobStatus, RuntimeState
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from support import narrative_batch_fixtures as fixtures

loopback_model_server = fixtures.loopback_model_server


def _invoke(root, state):
    repo = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(repo / "src"), str(repo / "scripts"))),
        PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1")
    call = subprocess.run([sys.executable, "-B", "-m", "company_wiki.automation.narrative_batch_cli",
        "--project-root", str(root), "--catalog-config", str(state.config_path),
        "--automation-db", str(root / "automation.db"), "--work-dir", str(root / "run-work"),
        "--request", str(root / "request.json")], cwd=root, env=env, capture_output=True, text=True,
        encoding="utf-8", timeout=60)
    assert fixtures.KEY not in call.stdout + call.stderr
    assert call.stdout.strip(), call.stderr
    return call, json.loads(call.stdout)


def _dump(db):
    connection = sqlite3.connect(db)
    try:
        return tuple(connection.iterdump())
    finally:
        connection.close()


@pytest.mark.parametrize("content", ["营" * 317, "", None], ids=["951", "empty", "unobserved"])
def test_failed_final_public_cli_persists_terminal_and_two_resumes_without_model_or_artifact(
    tmp_path_factory, loopback_model_server, content,
):
    # Deliberately no reasoning field: final diagnostics cannot depend on it.
    body = json.dumps({"model": "stub-model", "choices": [{"finish_reason": "length",
        "message": {"content": content, "reasoning_content": "NEVER_PERSIST_HIDDEN_REASONING"}}],
        "usage": {"prompt_tokens": 73, "completion_tokens": 8194}}, ensure_ascii=False).encode()
    loopback_model_server.response_body = body
    with fixtures.isolated_batch_directory(tmp_path_factory) as root:
        state = fixtures.prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            state.store = AutomationStore(root / "automation.db")
            state.store.set_runtime_gate(RuntimeState.PAUSED, updated_at=fixtures.T0)
            ref, _, _ = next(iter(state.indexed.values()))
            request = {"schema_version": "narrative-batch-request/1", "run_id": "w04-failed-final",
                "sources": [{"schema_version": ref.schema_version, "document_id": ref.document_id,
                    "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                    "byte_size": ref.byte_size, "mime_type": ref.mime_type}], "profile": "P2",
                "max_seconds": 40, "max_tokens": 200000, "max_cost_usd": "2",
                "model": {"model_id": "stub-model", "endpoint": loopback_model_server.endpoint,
                    "api_key_env": fixtures.KEY_ENV, "max_output_tokens": 8192,
                    "timeout_seconds": 5, "allow_local_http": True},
                "pricing": {"version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1000000,
                    "output_micro_usd_per_million_tokens": 2000000}}
            (root / "request.json").write_text(json.dumps(request), encoding="utf-8")
            originals = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in (root / "companies").rglob("*") if p.is_file()}
            first, result = _invoke(root, state)
            assert first.returncode == 2, (first.stderr, result)
            assert len(loopback_model_server.requests) == 1 and loopback_model_server.errors == []
            observation, = result["documents"][0]["model_diagnostics"]
            diagnostic = observation["failed_final"]
            assert diagnostic["provider_response_sha256"] == hashlib.sha256(body).hexdigest()
            assert diagnostic["provider_response_bytes"] == len(body)
            if content is None:
                assert diagnostic["final_content_bytes"] is None and diagnostic["final_content_sha256"] is None
                assert diagnostic["final_prefix"] is None
            else:
                assert diagnostic["final_content_bytes"] == len(content.encode())
                assert diagnostic["final_content_sha256"] == hashlib.sha256(content.encode()).hexdigest()
                assert diagnostic["final_prefix"] == content
            assert diagnostic["clipped"] is False
            assert observation["usage_status"] == "known" and observation["reasoning_tokens"] is None
            assert observation["input_tokens"] == 73 and observation["output_tokens"] == 8194
            assert result["budget"] == {"tokens": 8267, "estimated_micro_usd": 16461,
                "unknown_reservations": 0, "unsettled_reservations": 0}
            assert result["documents"][0]["artifact_ref"] is None
            assert result["status"] == "budget_exhausted"
            ledger = NarrativeRunStore(state.store.db_path)
            run = ledger.get_run("w04-failed-final")
            assert run.blocked and run.block_reason == "MODEL_USAGE_EXCEEDS_RESERVATION"
            assert state.store.read_runtime_gate().desired_state is RuntimeState.PAUSED
            all_jobs = state.store.list_jobs(job_ids=run.job_ids)
            verify, = [j for j in all_jobs if j.job_type == "source.narrative_verify"]
            # Maintenance may have already marked a failed dependency dead;
            # preserve the actual job snapshot in either scheduling order.
            assert verify.status in {JobStatus.PLANNED, JobStatus.DEAD_LETTER}
            summary, = [j for j in all_jobs
                if j.job_type == "source.narrative_summarize"]
            assert summary.status is JobStatus.DEAD_LETTER and summary.last_error_code == "MODEL_OUTPUT_TRUNCATED"
            if verify.status is JobStatus.PLANNED:
                assert verify.last_error_code is None and verify.last_error_detail is None
            else:
                assert verify.last_error_code == "DEPENDENCY_TERMINAL"
                assert summary.job_id + "=dead_letter" in verify.last_error_detail
            assert state.store.list_attempts(verify.job_id) == ()
            assert state.store.list_effects(verify.job_id) == ()
            attempt, = state.store.list_attempts(summary.job_id)
            saved = json.loads(attempt.result_json)
            assert len(attempt.result_json.encode()) < 16384
            assert saved["result"]["failed_final"] == diagnostic
            assert saved["outcome"] == "terminal_failure" and saved["error"]["code"] == "MODEL_OUTPUT_TRUNCATED"
            assert not saved["artifacts"] and not saved["effects"]
            assert "NEVER_PERSIST_HIDDEN_REASONING" not in attempt.result_json
            reservation, = ledger.reservations_for_run(run.run_id)
            assert (reservation.input_tokens, reservation.output_tokens) == (73, 8194)
            assert reservation.output_bytes == 0 and reservation.output_sha256 is None
            assert reservation.response_sha256 == diagnostic["final_content_sha256"]
            before = (_dump(state.store.db_path), _dump(state.catalog.config.database_path))
            for _ in range(2):
                resumed_call, resumed = _invoke(root, state)
                assert resumed_call.returncode == 2, (resumed_call.stderr, resumed)
                assert resumed["documents"] == result["documents"] and resumed["budget"] == result["budget"]
                assert (_dump(state.store.db_path), _dump(state.catalog.config.database_path)) == before
                assert resumed["status"] == "budget_exhausted"
                assert state.store.list_jobs(job_ids=run.job_ids) == all_jobs
                assert len(loopback_model_server.requests) == 1
            assert {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in originals} == originals
            assert ledger.reservations_for_run(run.run_id) == (reservation,)
        finally:
            state.catalog.close()
