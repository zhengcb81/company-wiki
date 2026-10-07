"""One real CLI completion, then versioned read-only recovery and refusals."""

from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from company_wiki.automation.models import RuntimeState, canonical_json
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from support import narrative_batch_fixtures as fixtures


loopback_model_server = fixtures.loopback_model_server


def _dump(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        return tuple(connection.iterdump())


def _invoke(state, launcher=None):
    entry = ([sys.executable, str(launcher)] if launcher else
             [sys.executable, "-B", "-m", "company_wiki.automation.narrative_batch_cli"])
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1")
    process = subprocess.run([
        *entry, "--project-root", str(state.root), "--catalog-config", str(state.config_path),
        "--automation-db", str(state.store.db_path), "--work-dir", str(state.root / "run-work"),
        "--request", str(state.request_path),
    ], cwd=state.root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert fixtures.KEY not in process.stdout + process.stderr
    return process, json.loads(process.stdout)


def _write_request(state, value):
    state.request_path.write_text(canonical_json(value), encoding="utf-8")


def test_actual_completed_cli_survives_execution_upgrade_without_rework_or_ledger_changes(
    tmp_path_factory, loopback_model_server,
):
    with fixtures.isolated_batch_directory(tmp_path_factory) as root:
        state = fixtures.prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            state.store = AutomationStore(root / "automation.db")
            state.store.set_runtime_gate(RuntimeState.ENABLED, updated_at=fixtures.T0)
            scheduler = AutomationScheduler(state.store, create_default_registry(),
                                            PolicyConfig(allow_llm=True, allow_network=True))
            state.outside = fixtures.foreign_ready_jobs(state, state.store, scheduler)
            state.store.set_runtime_gate(RuntimeState.PAUSED, updated_at=fixtures.T0)
            request = NarrativeBatchRequest.from_dict({
                "schema_version": "narrative-batch-request/1", "run_id": "version-resume",
                "sources": [ref.to_dict() if hasattr(ref, "to_dict") else {
                    "schema_version": ref.schema_version, "document_id": ref.document_id,
                    "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                    "byte_size": ref.byte_size, "mime_type": ref.mime_type,
                } for ref, _language, _kind in state.indexed.values()],
                "profile": "P2", "max_seconds": 40, "max_tokens": 200000, "max_cost_usd": "2",
                "model": {"model_id": "stub-model", "endpoint": loopback_model_server.endpoint,
                          "api_key_env": fixtures.KEY_ENV, "allow_local_http": True,
                          "max_output_tokens": 400, "timeout_seconds": 5},
                "pricing": {"version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1000000,
                            "output_micro_usd_per_million_tokens": 2000000},
            })
            state.request_path = root / "request.json"
            intent = request.to_dict()
            _write_request(state, intent)
            originals = {path: path.read_bytes() for path in state.raw_paths.values()}
            first_process, first = _invoke(state)
            assert first_process.returncode == 0 and first["status"] == "completed", first
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            runs = NarrativeRunStore(state.store.db_path)
            run = runs.get_run(request.run_id)
            assert run is not None
            before_auto, before_catalog = _dump(state.store.db_path), _dump(state.catalog.config.database_path)
            objects = {p: p.read_bytes() for p in (root / "catalog/objects").rglob("*") if p.is_file()}
            baseline = (root / "run-work/storage-baseline.json").read_bytes()
            launcher = root / "upgraded.py"
            launcher.write_text('''from dataclasses import replace
import company_wiki.automation.narrative_batch as batch
import company_wiki.automation.narrative_batch_request as request
import company_wiki.automation.registry as registry
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.narrative_batch_cli import main
from company_wiki.source_catalog.store import CatalogStore
request.NARRATIVE_PROMPT_VERSION = "9.0.0"
request.MODEL_REQUEST_SCHEMA = "narrative-model-request/9"
request.NARRATIVE_PARSER_VERSION = "9.0.0"
request.NARRATIVE_SELECTOR_VERSION = "9.0.0"
batch.NARRATIVE_PROMPT_VERSION = "9.0.0"
registry._KNOWN_SPECS = tuple(replace(s, handler_version="9.0.0")
    if s.job_type.startswith("source.narrative_") else s for s in registry._KNOWN_SPECS)
def forbidden(*args, **kwargs):
    raise AssertionError("completed resume attempted work/accounting mutation")
batch.AutomationScheduler.materialize_event = forbidden
batch.AutomationSupervisor.__init__ = forbidden
batch.compact_terminal_narrative_jobs = forbidden
NarrativeRunStore.activate_run = forbidden
NarrativeRunStore.settle_output = forbidden
NarrativeRunStore.settle_finished_attempt_reservations = forbidden
CatalogStore.__init__ = forbidden
batch.AutomationStore.has_running_jobs_outside_scope = lambda *args, **kwargs: True
raise SystemExit(main())
''', encoding="utf-8")
            process, resumed = _invoke(state, launcher)
            assert process.returncode == 0 and resumed["status"] == "completed", resumed
            assert resumed["documents"] == first["documents"] and resumed["budget"] == first["budget"]
            assert (_dump(state.store.db_path), _dump(state.catalog.config.database_path)) == (before_auto, before_catalog)
            assert {p: p.read_bytes() for p in objects} == objects
            assert (root / "run-work/storage-baseline.json").read_bytes() == baseline
            frozen = json.loads(run.binding_json)
            assert frozen["request_sha256"] == request.request_sha256
            assert frozen["read_policy_schema_version"] == "2.0"
            assert frozen["execution_versions"]["prompt"] == "1.6.0"
            assert frozen["execution_versions"]["model_request_schema"] == "narrative-model-request/1.3"
            assert set(frozen["execution_versions"]["handlers"].values()) == {"1.1.0"}

            def refused(code, *, entrypoint=launcher):
                auto, catalog = _dump(state.store.db_path), _dump(state.catalog.config.database_path)
                call, receipt = _invoke(state, entrypoint)
                assert call.returncode == 2 and receipt["error"] == code, receipt
                assert (_dump(state.store.db_path), _dump(state.catalog.config.database_path)) == (auto, catalog)
                assert len(loopback_model_server.requests) == 1

            # Limits, model, prices and sources remain the original intent.
            for change in ({"max_tokens": 200001}, {"max_seconds": 41},
                           {"profile": "P1"}, {"max_cost_usd": "3"},
                           {"model": {**intent["model"], "model_id": "another-model"}},
                           {"pricing": {**intent["pricing"], "version": "another-price"}}):
                _write_request(state, {**intent, **change})
                refused("BATCH_REQUEST_CHANGED")
            _write_request(state, intent)
            raw = next(iter(originals))
            raw.write_bytes(b"X" + originals[raw][1:])
            refused("no_verified_location")
            raw.write_bytes(originals[raw])
            # An actual read admission limit changed, not just code versions.
            config = state.config_path.read_bytes()
            changed = json.loads(config)
            changed["roots"][0]["max_file_size"] = 4096
            state.config_path.write_text(json.dumps(changed), encoding="utf-8")
            refused("BATCH_READ_POLICY_CHANGED")
            state.config_path.write_bytes(config)
            # A migration must not silently manufacture evidence for old pins.
            for legacy in (None, canonical_json({**frozen, "read_policy_schema_version": "1.0"})):
                with closing(sqlite3.connect(state.store.db_path, isolation_level=None)) as connection:
                    connection.execute("UPDATE narrative_runs SET binding_json=? WHERE run_id=?",
                                       (legacy, request.run_id))
                refused("BATCH_LEGACY_BINDING_UNVERIFIABLE")
            with closing(sqlite3.connect(state.store.db_path, isolation_level=None)) as connection:
                connection.execute("UPDATE narrative_runs SET binding_json=? WHERE run_id=?",
                                   (run.binding_json, request.run_id))
                connection.execute("UPDATE jobs SET status='ready' WHERE job_id=?", (run.job_ids[0],))
            refused("BATCH_EXECUTION_VERSION_UNAVAILABLE_NEW_RUN_REQUIRED")
            foreign = root / "foreign.py"
            foreign.write_text('''from company_wiki.automation.store import AutomationStore
from company_wiki.automation.narrative_batch_cli import main
AutomationStore.has_running_jobs_outside_scope = lambda *args, **kwargs: True
raise SystemExit(main())
''', encoding="utf-8")
            refused("NARRATIVE_BATCH_ValueError", entrypoint=foreign)
            with closing(sqlite3.connect(state.store.db_path, isolation_level=None)) as connection:
                connection.execute("UPDATE jobs SET status='succeeded' WHERE job_id=?", (run.job_ids[0],))
                # Historical unknown paid attempts stay charged, never resettled.
                connection.execute("UPDATE narrative_model_reservations SET usage_status='unknown',"
                                   "input_tokens=NULL,output_tokens=NULL,estimated_micro_usd=NULL,"
                                   "error_code='MODEL_TIMEOUT' WHERE run_id=?", (request.run_id,))
            unknown_before = _dump(state.store.db_path)
            unknown_budget = runs.budget_snapshot(request.run_id)
            call, unknown = _invoke(state, launcher)
            assert call.returncode == 0 and unknown["status"] == "completed", unknown
            assert unknown["budget"]["unknown_reservations"] == 1
            assert unknown["budget"]["tokens"] == unknown_budget.charged_tokens
            assert _dump(state.store.db_path) == unknown_before
            assert len(loopback_model_server.requests) == 1
            fixtures.assert_originals_and_foreign_jobs_untouched(state, originals,
                output=first_process.stdout + first_process.stderr + process.stdout + process.stderr)
        finally:
            state.catalog.close()
