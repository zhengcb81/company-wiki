"""Spawn and source-boundary tests for the production narrative factory."""

from __future__ import annotations

from dataclasses import replace
import importlib
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import Event, RuntimeState, canonical_json, canonical_json_hash
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.narrative_model import NARRATIVE_PROMPT_VERSION
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from company_wiki.automation.worker_process import WorkerProcessSpec
from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.source_reader import SourceVersionReader


T0 = "2026-09-28T22:00:00Z"
FACTORY = "company_wiki.automation.narrative_worker_factory:create_runtime"
KEY_ENV = "NARRATIVE_FACTORY_TEST_KEY"
KEY = "synthetic-not-a-live-key"


def _factory():
    return importlib.import_module("company_wiki.automation.narrative_worker_factory")


def _spec(state, *, role="compute", options=None, scope="default"):
    if options is None:
        options = state.options
    job_types = {
        "compute": ("source.narrative_select", "source.narrative_verify"),
        "model": ("source.narrative_summarize",),
        "mixed": ("source.narrative_select", "source.narrative_summarize", "source.narrative_verify"),
    }[role]
    return WorkerProcessSpec(
        worker_id="factory-" + role, role=role, db_path=str(state.store.db_path),
        log_dir=str(state.root / "logs"), runtime_factory_path=FACTORY,
        runtime_options_json=canonical_json(options), allowed_job_types=job_types,
        lease_seconds=30, heartbeat_interval_seconds=5, idle_sleep_seconds=0.05,
        child_log_max_bytes=4096,
        allowed_job_ids=state.job_ids if scope == "default" else scope,
    )


@pytest.fixture
def run_state(tmp_path_factory, request):
    from company_wiki.automation.narrative_run_store import NarrativeRunStore

    root = tmp_path_factory.mktemp("nf")
    directory = root / "companies" / "Acme" / "raw" / "investor_relations" / "transcripts"
    directory.mkdir(parents=True)
    raw = directory / "2026Q1.txt"
    data = (
        "Full conference call transcript\n"
        "Operator: Welcome to Acme's quarterly business update.\n\n"
        "Jane Li -- Chief Executive Officer:\n"
        "Acme launched a new product and expanded overseas sales in 2026. "
        "We signed pilot agreements with three customers and plan to launch service next quarter.\n"
    ).encode("utf-8")
    raw.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    raw.with_name(raw.name + ".source.json").write_text(json.dumps({
        "schema_version": "1.0", "canonical_entity_id": "ent-acme",
        "display_name": "Acme", "market": "US", "security_id": "ACME",
        "document_kind": "investor_call_transcript", "fiscal_year": 2026,
        "fiscal_period": "Q1", "period_end": "2026-03-31", "filing_date": "2026-05-01",
        "provider": "fixture", "provider_document_id": "2026Q1",
        "content_sha256": digest, "source_url": "https://fixtures.invalid/2026Q1",
        "source_title": "Acme 2026 Q1 earnings call", "language": "en",
        "retrieved_at": "2026-05-02T00:00:00Z", "collector_name": "factory_fixture",
        "collector_version": "1.0.0",
    }), encoding="utf-8")
    config_path = root / "catalog.json"
    config_path.write_text(json.dumps({
        "schema_version": "1.0", "catalog_dir": "catalog",
        "roots": [{"root_id": "company_raw", "path": "companies", "kind": "company_raw",
                   "adapter_id": "company_raw_v1", "read_only": True, "reusable_for_filing": True}],
    }), encoding="utf-8")
    catalog = SourceCatalog(load_catalog_config(config_path, project_root=root))
    request.addfinalizer(catalog.close)
    catalog.scan()
    reader = SourceVersionReader(catalog)
    row = catalog.reader.fetchone(
        "SELECT d.document_id,d.primary_source_id AS source_id FROM documents d "
        "JOIN sources s ON s.source_id=d.primary_source_id WHERE s.content_sha256=?",
        (digest,),
    )
    assert row is not None
    ref = reader.query_ref(row["document_id"], row["source_id"], digest)
    payload = {
        "schema_version": "source-revision-event/2.0",
        "source_ref": {"schema_version": ref.schema_version, "document_id": ref.document_id,
                       "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                       "byte_size": ref.byte_size, "mime_type": ref.mime_type},
        "expected_read_policy_sha256": reader.read_policy_sha256(),
        "source_metadata": {"source_class": "transcript", "title": "Acme 2026 Q1 earnings call",
                            "document_kind": "investor_call_transcript", "language": "en"},
    }
    parsed = SourceRevisionEventPayload.from_dict(payload)
    event = Event("factory-event", "source.revision_registered", "source_revision", ref.document_id,
                  parsed.input_hash, canonical_json(payload), "narrative-v1", T0, T0)
    store = AutomationStore(root / "automation.db")
    store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
    store.put_event(event)
    AutomationScheduler(store, create_default_registry(), PolicyConfig(allow_llm=True, allow_network=True)).materialize_event(event)
    job_ids = tuple(job.job_id for job in store.list_jobs())
    assert len(job_ids) == 3
    run_store = NarrativeRunStore(store.db_path)
    prompt_version = getattr(request, "param", NARRATIVE_PROMPT_VERSION)
    input_hash = canonical_json_hash({"job_ids": list(job_ids), "model_id": "fixture-model", "prompt_version": prompt_version})
    run_store.create_run(
        run_id="factory-run", input_hash=input_hash, job_ids=job_ids,
        model_id="fixture-model", prompt_version=prompt_version, pricing_version="fixture-price/1",
        input_micro_usd_per_million_tokens=1_000_000, output_micro_usd_per_million_tokens=2_000_000,
        max_tokens=20_000, max_micro_usd=2_000_000, max_output_bytes=4_194_304, created_at=T0,
    )
    state = SimpleNamespace(root=root, raw=raw, data=data, store=store, run_store=run_store, job_ids=job_ids)
    state.options = {
        "project_root": str(root), "catalog_config_path": str(config_path), "run_id": "factory-run",
        "expected_run_input_hash": input_hash,
        "model": {"model_id": "fixture-model", "endpoint": "https://model.example.invalid/v1/chat/completions",
                  "api_key_env": KEY_ENV, "max_output_tokens": 200},
    }
    yield state


def test_compute_constructs_no_model_or_budget_caller_and_reads_no_credentials(run_state, monkeypatch):
    factory = _factory()
    seen = []
    original = type(os.environ).__getitem__

    def read_env(environ, name):
        seen.append(name)
        assert name != KEY_ENV, "compute worker cannot read an LLM credential"
        return original(environ, name)

    def forbidden(*args, **kwargs):
        pytest.fail("compute worker constructed a model or budget caller")

    monkeypatch.setattr(type(os.environ), "__getitem__", read_env)
    monkeypatch.setattr(factory, "NarrativeHTTPModel", forbidden)
    monkeypatch.setattr(factory, "BudgetedNarrativeCaller", forbidden)
    runtime = factory.create_runtime(_spec(run_state))
    assert runtime.model_client is None and KEY_ENV not in seen
    assert runtime.registry.get("source.narrative_select").llm is False


@pytest.mark.parametrize("role", ["model", "mixed"])
def test_model_roles_wire_one_child_local_http_model_and_budget_caller(run_state, monkeypatch, role):
    monkeypatch.setenv(KEY_ENV, KEY)
    factory = _factory()
    captured = []
    register = factory.register_narrative_handlers

    def capture(registrar, dependencies):
        captured.append(dependencies)
        register(registrar, dependencies)

    monkeypatch.setattr(factory, "register_narrative_handlers", capture)
    spec = _spec(run_state, role=role)
    runtime = factory.create_runtime(spec)
    assert len(captured) == 1
    dependencies = captured[0]
    assert dependencies.model is runtime.model_client
    assert isinstance(dependencies.model, factory.NarrativeHTTPModel)
    assert isinstance(dependencies.model_caller, factory.BudgetedNarrativeCaller)
    assert KEY not in spec.runtime_options_json and KEY not in repr(runtime.model_client)


@pytest.mark.parametrize("field,value", [
    ("expected_run_input_hash", "0" * 64), ("run_id", "missing-run"),
])
def test_run_identity_mismatch_rejects_before_model_construction(run_state, monkeypatch, field, value):
    options = json.loads(canonical_json(run_state.options))
    options[field] = value
    factory = _factory()

    def forbidden(*args, **kwargs):
        pytest.fail("run identity must be checked before model construction")

    monkeypatch.setattr(factory, "NarrativeHTTPModel", forbidden)
    with pytest.raises(ValueError, match="NARRATIVE_RUN_"):
        factory.create_runtime(_spec(run_state, role="model", options=options))


@pytest.mark.parametrize("scope", [None, (), ("not-in-this-run",)])
def test_factory_requires_exact_nonempty_run_job_scope(run_state, scope):
    with pytest.raises(ValueError, match="NARRATIVE_RUN_SCOPE"):
        _factory().create_runtime(_spec(run_state, scope=scope))


def test_factory_model_identity_is_pinned_to_the_run(run_state):
    options = json.loads(canonical_json(run_state.options))
    options["model"]["model_id"] = "other-model"
    with pytest.raises(ValueError, match="NARRATIVE_RUN_MODEL"):
        _factory().create_runtime(_spec(run_state, role="model", options=options))


def test_factory_never_initializes_a_missing_database(run_state):
    path = run_state.root / "missing-automation.db"
    with pytest.raises(ValueError, match="NARRATIVE_RUN_STORE_UNAVAILABLE"):
        _factory().create_runtime(replace(_spec(run_state), db_path=str(path)))
    assert not path.exists()


@pytest.mark.parametrize("run_state", ["outdated-prompt"], indirect=True)
def test_factory_rejects_run_with_outdated_prompt(run_state):
    with pytest.raises(ValueError, match="NARRATIVE_RUN_PROMPT_MISMATCH"):
        _factory().create_runtime(_spec(run_state))


def test_blocked_run_rejects_model_but_keeps_compute_available(run_state):
    run_state.run_store.block_run("factory-run", error_code="TEST_LIMIT", updated_at=T0)
    with pytest.raises(ValueError, match="NARRATIVE_RUN_BLOCKED"):
        _factory().create_runtime(_spec(run_state, role="model"))
    assert _factory().create_runtime(_spec(run_state)).model_client is None


def test_secret_options_are_not_accepted_or_echoed(run_state):
    options = json.loads(canonical_json(run_state.options))
    options["model"]["api_key"] = KEY
    with pytest.raises(ValueError, match="NARRATIVE_RUNTIME_OPTIONS_INVALID") as error:
        _factory().create_runtime(_spec(run_state, role="model", options=options))
    assert KEY not in str(error.value)


def _spawn_compute_probe(spec, connection):
    from company_wiki.automation.worker import Worker

    def no_network(*args, **kwargs):
        raise AssertionError("compute child attempted network access")

    original = type(os.environ).__getitem__

    def no_credentials(environ, name):
        if name == KEY_ENV:
            raise AssertionError("compute child read a model credential")
        return original(environ, name)

    socket.socket.connect = no_network
    socket.create_connection = no_network
    type(os.environ).__getitem__ = no_credentials
    try:
        runtime = _factory().create_runtime(spec)
        worker = Worker(AutomationStore(Path(spec.db_path)), runtime.registry, runtime.executor,
                        worker_id=spec.worker_id, allowed_job_types=spec.allowed_job_types,
                        allowed_job_ids=spec.allowed_job_ids)
        processed = worker.process_one()
        connection.send({
            "pid": os.getpid(), "model_client": runtime.model_client, "processed": processed,
            "test_support_loaded": any(name.startswith(("support.", "tests.support")) for name in sys.modules),
        })
    except Exception as exc:
        connection.send({"error": type(exc).__name__, "message": str(exc)})
    finally:
        connection.close()


def test_spawned_production_factory_reads_original_source_with_zero_network(run_state, monkeypatch):
    monkeypatch.setenv(KEY_ENV, KEY)
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_spawn_compute_probe, args=(_spec(run_state), sender))
    process.start()
    sender.close()
    try:
        assert receiver.poll(20), "compute factory child did not return"
        result = receiver.recv()
        process.join(timeout=5)
        assert result == {"pid": process.pid, "model_client": None, "processed": True, "test_support_loaded": False}
        assert process.exitcode == 0 and process.pid != os.getpid()
        selected = next(job for job in run_state.store.list_jobs() if job.job_type == "source.narrative_select")
        assert selected.status.value == "succeeded", (selected.last_error_code, selected.last_error_detail)
        assert run_state.raw.read_bytes() == run_state.data
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
        process.close()


def test_factory_module_is_importable_without_test_support():
    factory = importlib.import_module("company_wiki.automation.narrative_worker_factory")
    assert callable(factory.create_runtime)
    assert factory.create_runtime.__module__ == "company_wiki.automation.narrative_worker_factory"
