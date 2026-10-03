"""Distinct batch publications share immutable bodies without rebinding pins."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import RuntimeState
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore,
    NarrativeArtifactStore,
)

from support.narrative_batch_fixtures import (
    KEY,
    KEY_ENV,
    T0,
    assert_originals_and_foreign_jobs_untouched,
    foreign_ready_jobs,
    isolated_batch_directory,
    prepare_source_catalog,
)


@pytest.fixture
def cross_run_model_server(monkeypatch, hermetic_runtime):
    """A/B return the same cited draft; C returns another cited English draft."""
    state = SimpleNamespace(requests=[], errors=[], alternate=False)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                assert self.path == "/v1/chat/completions"
                assert self.headers["Authorization"] == f"Bearer {KEY}"
                body = self.rfile.read(int(self.headers["Content-Length"]))
                assert KEY.encode() not in body
                request = json.loads(body)
                assert [message["role"] for message in request["messages"]] == ["system", "user"]
                data = json.loads(request["messages"][1]["content"])
                assert data["constraints"]["translate"] is False
                draft = json.loads(json.dumps(data["response_example"]))
                assert draft is not None and draft["draft"]["language"] == "en"
                if state.alternate:
                    claim = draft["draft"]["claims"][0]
                    assert "We launched a new product" in claim["text"]
                    claim["text"] = "We launched a new product"
                state.requests.append((data, draft))
                reply = json.dumps({
                    "model": "stub-model",
                    "choices": [{
                        "message": {"content": json.dumps(draft, ensure_ascii=False)},
                        "finish_reason": "stop",
                    }],
                    "usage": {"prompt_tokens": 73, "completion_tokens": 19},
                }, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
            except Exception as exc:
                state.errors.append(type(exc).__name__)
                reply = b'{"error":"invalid local test request"}'
                self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()
            self.wfile.write(reply)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = False
    thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01))
    thread.start()
    monkeypatch.setenv(KEY_ENV, KEY)
    state.endpoint = f"http://127.0.0.1:{server.server_port}/v1/chat/completions"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def _request(state, endpoint, run_id):
    ref, _language, _kind = next(iter(state.indexed.values()))
    request = NarrativeBatchRequest.from_dict({
        "schema_version": "narrative-batch-request/1",
        "run_id": run_id,
        "sources": [{
            "schema_version": ref.schema_version,
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "content_sha256": ref.content_sha256,
            "byte_size": ref.byte_size,
            "mime_type": ref.mime_type,
        }],
        "profile": "P2",
        "max_seconds": 25,
        "max_tokens": 200_000,
        "max_cost_usd": "2",
        "model": {
            "model_id": "stub-model",
            "endpoint": endpoint,
            "api_key_env": KEY_ENV,
            "max_output_tokens": 400,
            "timeout_seconds": 5,
            "allow_local_http": True,
        },
        "pricing": {
            "version": "fixture-price/1",
            "input_micro_usd_per_million_tokens": 1_000_000,
            "output_micro_usd_per_million_tokens": 2_000_000,
        },
    })
    path = state.root / f"{run_id}.json"
    path.write_text(json.dumps(request.to_dict(), ensure_ascii=False), encoding="utf-8")
    assert KEY not in path.read_text(encoding="utf-8")
    return path


def _invoke(state, request_path, run_id):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHON_DOTENV_DISABLED"] = "1"
    process = subprocess.run([
        sys.executable, "-m", "company_wiki.automation.narrative_batch_cli",
        "--project-root", str(state.root),
        "--catalog-config", str(state.config_path),
        "--automation-db", str(state.store.db_path),
        "--work-dir", str(state.root / f"work-{run_id}"),
        "--request", str(request_path),
    ], cwd=state.root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=45)
    assert KEY not in process.stdout + process.stderr
    assert process.stdout.strip(), process.stderr
    result = json.loads(process.stdout)
    assert isinstance(result, dict) and result["schema_version"] == "narrative-batch-result/1"
    assert result["run_id"] == run_id
    return process, result


def _exact(artifacts, pin):
    version, payload = artifacts.read_exact(
        artifact_version_id=pin["artifact_version_id"],
        document_id=pin["document_id"],
        source_id=pin["source_id"],
        source_sha256=pin["source_sha256"],
        expected_sha256=pin["content_sha256"],
        expected_size=pin["byte_size"],
    )
    return version, payload, NarrativeBundle.from_dict(json.loads(payload))


def test_three_runs_keep_exact_pins_share_identical_body_and_publish_changed_draft(
    tmp_path_factory, cross_run_model_server,
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True)
        try:
            state.store = AutomationStore(root / "automation.db")
            state.store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
            scheduler = AutomationScheduler(
                state.store, create_default_registry(),
                PolicyConfig(allow_llm=True, allow_network=True),
            )
            state.outside = foreign_ready_jobs(state, state.store, scheduler)
            state.store.set_runtime_gate(RuntimeState.PAUSED, updated_at=T0)
            originals = {
                path: path.read_bytes()
                for path in (root / "companies").rglob("*") if path.is_file()
            }
            originals[state.config_path] = state.config_path.read_bytes()
            requests = {
                name: _request(state, cross_run_model_server.endpoint, name)
                for name in ("cross-a", "cross-b", "cross-c")
            }
            outputs = []
            results = []
            for name in ("cross-a", "cross-b", "cross-c"):
                cross_run_model_server.alternate = name == "cross-c"
                process, result = _invoke(state, requests[name], name)
                outputs.append(process.stdout + process.stderr)
                results.append((process, result))
                if name == "cross-a":
                    assert process.returncode == 0 and result["status"] == "completed", result
                assert_originals_and_foreign_jobs_untouched(state, originals, output=outputs[-1])

            # Keep both B and C receipts in the failure to distinguish a cross-job
            # effect collision from a changed-body publication-key collision.
            statuses = [(process.returncode, result["status"]) for process, result in results]
            if statuses != [(0, "completed")] * 3:
                pytest.fail(json.dumps([
                    {
                        "run_id": result["run_id"], "exit_code": process.returncode,
                        "status": result["status"], "documents": result["documents"],
                        "budget": result["budget"],
                    }
                    for process, result in results
                ], ensure_ascii=False, indent=2))
            assert cross_run_model_server.errors == []
            assert len(cross_run_model_server.requests) == 3
            assert cross_run_model_server.requests[0][1] == cross_run_model_server.requests[1][1]
            assert cross_run_model_server.requests[0][1] != cross_run_model_server.requests[2][1]

            document_id = next(iter(state.indexed))
            pins = []
            for _process, result in results:
                assert len(result["documents"]) == 1
                document = result["documents"][0]
                assert document["document_id"] == document_id
                pins.append(document["artifact_ref"])
                assert result["budget"] == {
                    "tokens": 92, "estimated_micro_usd": 111,
                    "unknown_reservations": 0, "unsettled_reservations": 0,
                }

            artifacts = NarrativeArtifactStore(
                state.catalog.store, LocalNarrativeObjectStore(state.catalog.config.catalog_dir),
            )
            loaded = [_exact(artifacts, pin) for pin in pins]
            versions = [version for version, _payload, _bundle in loaded]
            assert len({version.artifact_version_id for version in versions}) == 3
            assert len({version.effect_id for version in versions}) == 3
            assert len({version.work_key for version in versions}) == 3
            assert loaded[0][1] == loaded[1][1] and loaded[0][1] != loaded[2][1]
            assert pins[0]["content_sha256"] == pins[1]["content_sha256"]
            assert pins[0]["content_sha256"] != pins[2]["content_sha256"]
            assert versions[0].object_key == versions[1].object_key
            assert versions[0].object_key != versions[2].object_key
            objects = list((state.catalog.config.catalog_dir / "objects" / "sha256").rglob("*.json"))
            assert {path.stem for path in objects} == {pin["content_sha256"] for pin in pins}
            assert len(objects) == 2
            for _version, _payload, bundle in loaded:
                assert bundle.summary.translate is False and bundle.summary.draft.language == "en"
                claim = bundle.summary.draft.claims[0]
                assert claim.text in " ".join(span.raw_text for span in bundle.evidence_spans)

            before_objects = {path: path.read_bytes() for path in objects}
            cross_run_model_server.alternate = False
            resumed, repeated = _invoke(state, requests["cross-b"], "cross-b")
            outputs.append(resumed.stdout + resumed.stderr)
            assert resumed.returncode == 0 and repeated["status"] == "completed", repeated
            assert len(cross_run_model_server.requests) == 3
            assert repeated["documents"][0]["artifact_ref"] == pins[1]
            assert repeated["budget"] == results[1][1]["budget"]
            assert {path: path.read_bytes() for path in objects} == before_objects
            assert len(list((state.catalog.config.catalog_dir / "objects").rglob("*.json"))) == 2
            for pin, (_version, payload, _bundle) in zip(pins, loaded):
                assert _exact(artifacts, pin)[1] == payload
            assert_originals_and_foreign_jobs_untouched(state, originals, output="\n".join(outputs))
            assert state.store.list_outbox_entries(status="pending") == ()
        finally:
            state.catalog.close()
