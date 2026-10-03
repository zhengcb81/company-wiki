"""Real production worker processes, bounded loopback HTTP and visible bundles."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import shutil
import time
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import JobStatus, RuntimeState, canonical_json, canonical_json_hash
from company_wiki.automation.narrative_model import NARRATIVE_PROMPT_VERSION
from company_wiki.automation.narrative_projection import NarrativeBundleReader, NarrativeEffectDispatcher
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from company_wiki.automation.supervisor import AutomationSupervisor, SupervisorConfig
from company_wiki.source_catalog.narrative_artifact_store import LocalNarrativeObjectStore, NarrativeArtifactStore

from support import narrative_batch_fixtures as batch_fixtures
from support.narrative_batch_fixtures import (
    KEY, KEY_ENV, T0, assert_originals_and_foreign_jobs_untouched,
    foreign_ready_jobs, prepare_source_catalog, source_event,
)


loopback_model_server = batch_fixtures.loopback_model_server


def _prepare(root, endpoint, *, zero_budget=False):
    prepared = prepare_source_catalog(root, one_source=zero_budget)
    catalog = prepared.catalog
    config_path = prepared.config_path
    indexed = prepared.indexed
    try:
        store = AutomationStore(root / "automation.db")
        store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
        scheduler = AutomationScheduler(store, create_default_registry(), PolicyConfig(allow_llm=True, allow_network=True))
        for number, (ref, language, kind) in enumerate(indexed.values()):
            manifest = prepared.reader.describe_version(ref)
            event = source_event(prepared.reader, ref, manifest["title"], language,
                                 manifest["document_kind"], f"e2e-{number}")
            store.put_event(event)
            scheduler.materialize_event(event)
        job_ids = tuple(job.job_id for job in store.list_jobs())
        run_store = NarrativeRunStore(store.db_path)
        input_hash = canonical_json_hash({"job_ids": list(job_ids), "prompt_version": NARRATIVE_PROMPT_VERSION, "model_id": "stub-model"})
        run_store.create_run(
            run_id="production-e2e", input_hash=input_hash, job_ids=job_ids,
            model_id="stub-model", prompt_version=NARRATIVE_PROMPT_VERSION, pricing_version="fixture-price/1",
            input_micro_usd_per_million_tokens=1_000_000, output_micro_usd_per_million_tokens=2_000_000,
            max_tokens=200_000, max_micro_usd=0 if zero_budget else 2_000_000,
            max_output_bytes=8 * 1024 * 1024, created_at=T0,
        )
        outside = foreign_ready_jobs(prepared, store, scheduler)
        options = {
            "project_root": str(root), "catalog_config_path": str(config_path), "run_id": "production-e2e",
            "expected_run_input_hash": input_hash,
            "model": {"model_id": "stub-model", "endpoint": endpoint, "api_key_env": KEY_ENV,
                      "max_output_tokens": 400, "timeout_seconds": 5, "allow_local_http": True},
        }
        assert KEY not in canonical_json(options)
        supervisor = AutomationSupervisor(SupervisorConfig(
            db_path=store.db_path, log_dir=root / "logs", profile="P2",
            runtime_factory_path="company_wiki.automation.narrative_worker_factory:create_runtime",
            runtime_options_json=canonical_json(options),
            compute_job_types=("source.narrative_select", "source.narrative_verify"),
            model_job_types=("source.narrative_summarize",), allowed_job_ids=job_ids,
            lease_seconds=30, heartbeat_interval_seconds=1, idle_sleep_seconds=0.03,
            maintenance_interval_seconds=0.03, stop_grace_seconds=2, child_log_max_bytes=16_384,
        ))
        return SimpleNamespace(catalog=catalog, store=store, run_store=run_store, supervisor=supervisor,
                               indexed=indexed, job_ids=job_ids, outside=outside, root=root)
    except BaseException:
        catalog.close()
        raise


def _wait(state, *, zero_budget=False):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        state.supervisor.maintain()
        jobs = [state.store.get_job(job_id) for job_id in state.job_ids]
        if zero_budget:
            summary = next(job for job in jobs if job.job_type == "source.narrative_summarize")
            if summary.status is JobStatus.DEAD_LETTER:
                assert summary.last_error_code == "MODEL_BUDGET_DENIED"
                return
        else:
            assert not any(job.status in {JobStatus.DEAD_LETTER, JobStatus.BLOCKED_HUMAN, JobStatus.CANCELLED} for job in jobs), [
                (job.job_type, job.status.value, job.last_error_code, job.last_error_detail) for job in jobs
            ]
            if all(job.status in {JobStatus.SUCCEEDED, JobStatus.VERIFYING} for job in jobs):
                return
        time.sleep(0.03)
    raise AssertionError("production narrative run did not reach its expected boundary")


@pytest.mark.parametrize("zero_budget", [False, True], ids=["two-languages-and-skip", "zero-budget-zero-http"])
def test_production_factory_http_to_published_bundle_restores_test_directory(tmp_path_factory, loopback_model_server, zero_budget):
    test_dir = tmp_path_factory.mktemp("np")
    keep = test_dir / "keep.txt"
    keep.write_bytes(b"preexisting test file")
    baseline = {path.name: path.read_bytes() for path in test_dir.iterdir()}
    root = test_dir / "run"
    root.mkdir()
    state = None
    try:
        state = _prepare(root, loopback_model_server.endpoint, zero_budget=zero_budget)
        originals = {path: path.read_bytes() for path in (root / "companies").rglob("*") if path.is_file()}
        state.supervisor.start()
        _wait(state, zero_budget=zero_budget)
        state.supervisor.stop()
        assert all(not child.alive for child in state.supervisor.children())
        assert loopback_model_server.errors == []
        records = state.run_store.reservations_for_run("production-e2e")
        if zero_budget:
            assert loopback_model_server.requests == [] and records == ()
            assert state.run_store.get_run("production-e2e").max_micro_usd == 0
            budget = state.run_store.budget_snapshot("production-e2e")
            assert budget.charged_tokens == 0 and budget.charged_micro_usd == 0
            assert state.store.list_outbox_entries(status="pending") == ()
        else:
            assert len(loopback_model_server.requests) == 2 and len(records) == 2
            assert {data["source"]["language"] for data, _body in loopback_model_server.requests} == {"en", "zh"}
            assert all(record.usage_status == "known" and (record.input_tokens, record.output_tokens) == (73, 19) for record in records)
            artifacts = NarrativeArtifactStore(state.catalog.store, LocalNarrativeObjectStore(state.catalog.config.catalog_dir))
            dispatcher = NarrativeEffectDispatcher(state.store, artifacts, allowed_job_ids=state.job_ids)
            now = datetime.now(UTC)
            for _ in range(3):
                receipt = dispatcher.dispatch_next(worker_id="e2e-projector", now=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    lease_until=(now + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    expected_generation=state.store.read_runtime_gate().control_generation)
                assert receipt.status == "visible"
            reader = NarrativeBundleReader(artifacts)
            bundles = {}
            for document_id, (ref, language, kind) in state.indexed.items():
                loaded = reader.read(document_id=document_id, source_id=ref.source_id, source_sha256=ref.content_sha256)
                assert loaded.artifact.status == "visible" and loaded.bundle.summary.translate is False
                assert loaded.bundle.source_metadata.language == language
                if kind == "ir_policy":
                    assert loaded.bundle.selection.status == "skipped_no_narrative"
                    assert loaded.bundle.summary.status == "summary_not_needed"
                else:
                    assert loaded.bundle.summary.draft.language == language
                    claim = loaded.bundle.summary.draft.claims[0].text
                    assert claim in " ".join(span.raw_text for span in loaded.bundle.evidence_spans)
                    assert ("新产品" in claim) if language == "zh" else ("new product" in claim)
                bundles[document_id] = loaded
            for record in records:
                loaded = bundles[state.store.get_job(record.job_id).subject_id]
                state.run_store.settle_output(run_id="production-e2e", attempt_id=record.attempt_id,
                    output_bytes=loaded.artifact.byte_size, output_sha256=loaded.artifact.content_sha256,
                    settled_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
            budget = state.run_store.budget_snapshot("production-e2e")
            assert budget.charged_tokens == 184 and budget.charged_micro_usd == 222
            assert budget.unknown_reservations == 0 and budget.unsettled_reservations == 0
            assert all(state.store.get_job(job_id).status is JobStatus.SUCCEEDED for job_id in state.job_ids)
            assert state.store.list_outbox_entries(status="pending") == ()
        assert_originals_and_foreign_jobs_untouched(state, originals)
    finally:
        if state is not None:
            state.supervisor.stop()
            state.catalog.close()
        assert root.resolve().parent == test_dir.resolve() and root.name == "run"
        shutil.rmtree(root)
        assert {path.name: path.read_bytes() for path in test_dir.iterdir()} == baseline
