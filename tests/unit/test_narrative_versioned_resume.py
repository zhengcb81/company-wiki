"""Versioned execution recovery preserves request intent and historical accounting."""

from __future__ import annotations

from dataclasses import replace
import importlib
import json
import sqlite3

import pytest

from company_wiki.automation.models import canonical_json, make_job_key
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.source_contract import source_id_for_sha256
from support.narrative_batch_fixtures import T0, prepare_source_catalog


def _request() -> NarrativeBatchRequest:
    return NarrativeBatchRequest.from_dict({
        "schema_version": "narrative-batch-request/1", "run_id": "versioned-run",
        "sources": [{"schema_version": "2.0", "document_id": "document-one",
                     "source_id": source_id_for_sha256("a" * 64), "content_sha256": "a" * 64,
                     "byte_size": 100, "mime_type": "text/plain"}],
        "profile": "P1", "max_seconds": 30, "max_tokens": 10000, "max_cost_usd": "0.1",
        "model": {"model_id": "offline-model", "endpoint": "https://fixtures.invalid/v1/chat/completions",
                  "api_key_env": "VERSIONED_RESUME_KEY"},
        "pricing": {"version": "fixture/1", "input_micro_usd_per_million_tokens": 300000,
                    "output_micro_usd_per_million_tokens": 1200000},
    })


def test_request_identity_is_independent_of_current_execution_code_versions(monkeypatch) -> None:
    request = _request()
    module = importlib.import_module("company_wiki.automation.narrative_batch_request")
    identity, execution = request.request_sha256, request.input_hash
    monkeypatch.setattr(module, "NARRATIVE_PROMPT_VERSION", "future-prompt")
    monkeypatch.setattr(module, "NARRATIVE_PARSER_VERSION", "future-parser")
    monkeypatch.setattr(module, "NARRATIVE_SELECTOR_VERSION", "future-selector")
    assert request.request_sha256 == identity
    assert request.input_hash != execution
    assert NarrativeBatchRequest.from_dict(request.to_dict()).request_sha256 == identity


@pytest.mark.parametrize("field,value", [
    ("max_tokens", 10001), ("max_micro_usd", 100001), ("max_seconds", 31),
    ("max_final_bytes", 100000), ("max_persistent_bytes", 1000000),
    ("max_scratch_bytes", 1000000), ("profile", "P2"), ("pricing_version", "fixture/2"),
])
def test_request_identity_detects_every_changed_request_limit(field: str, value: object) -> None:
    request = _request()
    assert replace(request, **{field: value}).request_sha256 != request.request_sha256


def test_request_identity_detects_changed_model_endpoint_and_source_version() -> None:
    request = _request()
    for field, value in [("model_id", "another-model"), ("endpoint", "https://another.invalid/chat/completions"),
                         ("temperature", 0.9), ("max_output_tokens", 8192)]:
        changed = replace(request, model_options_json=canonical_json({**request.model_options, field: value}))
        assert changed.request_sha256 != request.request_sha256
    changed_ref = replace(request.sources[0], document_id="another-document")
    assert replace(request, sources=(changed_ref,)).request_sha256 != request.request_sha256


@pytest.fixture
def frozen_run(tmp_path):
    """Real indexed source and scheduler membership; no worker or HTTP call."""
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation.narrative_run_store import NarrativeRunStore
    from company_wiki.automation.policy import PolicyConfig
    from company_wiki.automation.registry import create_default_registry
    from company_wiki.automation.scheduler import AutomationScheduler
    from company_wiki.automation.store import AutomationStore
    from dataclasses import asdict
    state = prepare_source_catalog(tmp_path, one_source=True, include_policy=False)
    try:
        ref, _language, _kind = next(iter(state.indexed.values()))
        request = NarrativeBatchRequest.from_dict({**_request().to_dict(), "sources": [asdict(ref)]})
        binding = batch.build_batch_events(request, state.reader, now=T0)
        store = AutomationStore(tmp_path / "auto.db")
        scheduler = AutomationScheduler(store, create_default_registry(),
                                        PolicyConfig(allow_llm=True, allow_network=True))
        for event in binding.events:
            store.put_event(event)
            scheduler.materialize_event(event)
        runs = NarrativeRunStore(store.db_path)
        run = runs.create_run(run_id=request.run_id, input_hash=binding.input_hash,
            job_ids=tuple(job.job_id for job in store.list_jobs()), model_id=request.model_options["model_id"],
            prompt_version=request.execution_versions["prompt"], pricing_version=request.pricing_version,
            input_micro_usd_per_million_tokens=request.input_micro_usd_per_million_tokens,
            output_micro_usd_per_million_tokens=request.output_micro_usd_per_million_tokens,
            max_tokens=request.max_tokens, max_micro_usd=request.max_micro_usd,
            max_output_bytes=request.max_final_bytes, created_at=T0,
            binding_json=batch._frozen_binding(request, binding))
        yield state, request, store, runs, run
    finally:
        state.catalog.close()


@pytest.mark.parametrize("field,value", [
    ("canonical_entity_id", "ent-other"), ("market", "HK"), ("security_id", "OTHER"),
    ("fiscal_year", 2025), ("fiscal_period", "Q2"), ("period_end", "2026-06-30"),
    ("published_date", "2026-05-03"), ("form_type", "10-K"),
])
def test_resume_rechecks_real_current_identity_and_period_without_rebinding(frozen_run, field, value):
    from company_wiki.automation import narrative_batch as batch
    state, request, store, runs, run = frozen_run
    document_id = request.sources[0].document_id
    with state.catalog.store.transaction() as connection:
        row = connection.execute("SELECT metadata_json FROM documents WHERE document_id=?", (document_id,)).fetchone()
        metadata = json.loads(row["metadata_json"])
        if field == "published_date":
            connection.execute("UPDATE documents SET published_date=? WHERE document_id=?", (value, document_id))
        else:
            metadata["acquisition"][field] = value
            connection.execute("UPDATE documents SET metadata_json=? WHERE document_id=?",
                               (canonical_json(metadata), document_id))
    # The responsible reader actually observes the changed assertion.
    ref = state.reader.query_ref(document_id, request.sources[0].source_id, request.sources[0].content_sha256)
    assert state.reader.describe_version(ref)[field] == value
    with pytest.raises(batch.BatchResumeError, match="BATCH_SOURCE_FACTS_CHANGED"):
        batch._resume_binding(request, state.reader, store, runs, run, deadline=None)
    assert runs.get_run(run.run_id) == run
    assert all(store.list_attempts(job_id) == () for job_id in run.job_ids)


@pytest.mark.parametrize("mutation", ["job_hash", "job_version", "membership_hash", "missing_member"])
def test_resume_rejects_changed_frozen_execution_membership(frozen_run, mutation):
    from company_wiki.automation import narrative_batch as batch
    state, request, store, runs, run = frozen_run
    connection = sqlite3.connect(store.db_path)
    try:
        job_id = run.job_ids[0]
        job = store.get_job(job_id)
        if mutation == "job_hash":
            key = make_job_key(job.job_type, job.subject_type, job.subject_id, "b" * 64,
                               job.policy_version, job.handler_version)
            connection.execute("UPDATE jobs SET input_hash=?,job_key=? WHERE job_id=?", ("b" * 64, key, job_id))
        elif mutation == "job_version":
            key = make_job_key(job.job_type, job.subject_type, job.subject_id, job.input_hash,
                               job.policy_version, "1.0.0")
            connection.execute("UPDATE jobs SET handler_version='1.0.0',job_key=? WHERE job_id=?", (key, job_id))
        elif mutation == "membership_hash":
            connection.execute("UPDATE narrative_run_jobs SET input_hash=? WHERE job_id=?", ("b" * 64, job_id))
        else:
            connection.execute("DELETE FROM narrative_run_jobs WHERE job_id=?", (job_id,))
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_MEMBERSHIP_INVALID"):
        batch._resume_binding(request, state.reader, store, runs, run, deadline=None)
    assert all(store.list_attempts(job_id) == () for job_id in run.job_ids)
