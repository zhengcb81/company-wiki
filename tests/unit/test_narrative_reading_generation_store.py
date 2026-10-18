"""Atomic final generation freezing on the existing AUTO selection boundary."""

from __future__ import annotations

from dataclasses import replace
import shutil
import sqlite3

import pytest

from company_wiki.automation import migrations, narrative_run_store, store as store_module
from company_wiki.automation.models import (
    Event, HandlerMetrics, HandlerOutcome, HandlerResult, Job, JobStatus, RiskClass,
    RuntimeState, canonical_json, canonical_json_hash, make_job_key,
)
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.automation.narrative_run_store import NarrativeRunStore, RunConflictError
from company_wiki.automation.narrative_selection_generation import reading_material_sha256
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.store import AutomationStore, LeaseLostError
from company_wiki.narrative_subject import NarrativeSubject
from support.narrative_model_request_fixture import selection


NOW = "2026-10-14T10:00:00Z"
END = "2026-10-14T10:01:00Z"


def _selected(*, reading=True, version="0.9.0", digest="a" * 64):
    result = selection().to_dict()
    result["selector"]["version"] = version
    if reading:
        result["reading_context"] = {
            "schema_version": "du-production-reading/1",
            "reading_policy_version": "du-sent-policy/1+" + digest,
            "reading_policies": [], "business_facets": [], "constraints": [],
            "groups": [], "unread": {
                "native_scan": "complete", "opaque_pages": [], "deferred_pages": [],
                "deferred_unit_ids": [], "unassigned_unit_ids": [],
                "structure_complete": True,
            }, "deferred": [], "layout_coverage": {},
        }
    return HandlerResult(HandlerOutcome.SUCCEEDED, result, (), (), HandlerMetrics(0, 0.0, 0), None)


def _state(tmp_path, *, version="0.9.0", bound=True):
    auto = AutomationStore(tmp_path / "auto.db")
    selected = _selected(version=version)
    document = selected.result["source_ref"]["document_id"]
    selected_wire = selected.to_dict()["result"]
    digest = canonical_json_hash(selected_wire["source_ref"])
    event = Event("event", "source.revision_registered", "source_revision", document,
                  digest, "{}", "fixture", NOW, NOW)
    auto.put_event(event)
    jobs = []
    for kind in ("select", "summarize", "verify"):
        job_type = "source.narrative_" + kind
        job = Job(
            "job-" + kind, make_job_key(job_type, "source_revision", document, digest,
                                       "fixture", "1.0.0"),
            job_type, "source_revision", document, digest, "fixture", "1.0.0",
            RiskClass.LOW, JobStatus.READY, 0, NOW, 3, event.event_id, NOW, NOW, None, None,
        )
        auto.put_job(job)
        jobs.append(job)
    manifest = {
        "schema_version": "narrative-generation/1",
        "source_ref": selected_wire["source_ref"],
        "source_metadata": selected_wire["source_metadata"],
        "parser_component": selected_wire["parser"],
        "execution_versions": {"selector": version},
        "model": {"model_id": "fixture", "endpoint": "https://model.invalid/v1/chat/completions",
                  "max_output_tokens": 200, "output_token_field": "max_tokens"},
    }
    common = {k: v for k, v in manifest.items() if k not in {"source_ref", "source_metadata", "parser_component"}}
    settings_hash = canonical_json_hash(common)
    binding = {
        "execution_versions": {"selector": version},
        "generation_settings": {settings_hash: common},
        "generation_manifests": {document: {
            "settings_sha256": settings_hash, "generation_sha256": canonical_json_hash(manifest),
            "source_inputs": {k: manifest[k] for k in ("source_ref", "source_metadata", "parser_component")},
        }},
    }
    runs = NarrativeRunStore(auto.db_path)
    runs.create_run(run_id="run", input_hash=digest, job_ids=tuple(j.job_id for j in jobs),
                    model_id="fixture", prompt_version="prompt", pricing_version="price",
                    input_micro_usd_per_million_tokens=1, output_micro_usd_per_million_tokens=1,
                    max_tokens=10000, max_micro_usd=10000, max_output_bytes=10000,
                    created_at=NOW, binding_json=canonical_json(binding) if bound else None)
    generation = auto.set_runtime_gate(RuntimeState.ENABLED, updated_at=NOW).control_generation
    return auto, runs, jobs, generation, selected, manifest


def _claim(auto, job, generation):
    return auto.claim_next_ready(worker_id="worker", attempt_id="attempt-" + job.job_id,
                                lease_token="lease-" + job.job_id, now=NOW, lease_until=END,
                                expected_generation=generation, allowed_job_ids=(job.job_id,))


def _finish(auto, work, result):
    return auto.finish_attempt(attempt_id=work.attempt.attempt_id,
                               lease_token=work.attempt.lease_token,
                               runtime_generation=work.attempt.runtime_generation,
                               finished_at=NOW, result=result)


def test_select_success_freezes_actual_result_once_and_reads_for_all_same_subject_jobs(tmp_path):
    auto, runs, jobs, generation, selected, base = _state(tmp_path)
    assert runs.final_generations("run") == {}
    work = _claim(auto, jobs[0], generation)
    _finish(auto, work, selected)
    expected = {**base, "selection_generation": {
        "schema_version": "narrative-selection-generation/1",
        "select_result_sha256": canonical_json_hash(selected.to_dict()["result"]),
        "reading_policy_version": selected.result["reading_context"]["reading_policy_version"],
        "evidence_sha256": canonical_json_hash(selected.to_dict()["result"]["evidence_spans"]),
        "material_sha256": reading_material_sha256(NarrativeSelectResult.from_dict(selected.to_dict()["result"])),
    }}
    assert runs.final_generations("run") == {jobs[0].subject_id: expected}
    assert all(runs.final_generation_for_job(job.job_id) == expected for job in jobs)
    assert runs.final_generation_for_job("missing") is None


@pytest.mark.parametrize("bound,version", [(True, "0.8.0"), (False, "0.9.0")])
def test_legacy_or_unbound_handlers_do_not_create_a_final_generation(tmp_path, bound, version):
    auto, runs, jobs, generation, _, _ = _state(tmp_path, version=version, bound=bound)
    _finish(auto, _claim(auto, jobs[0], generation), _selected(reading=False, version=version))
    assert runs.final_generations("run") == {}


def test_bound_new_select_missing_reading_context_rolls_back_attempt_and_status(tmp_path):
    auto, runs, jobs, generation, _, _ = _state(tmp_path)
    work = _claim(auto, jobs[0], generation)
    with pytest.raises(RunConflictError, match="reading context"):
        _finish(auto, work, _selected(reading=False))
    assert auto.get_job(jobs[0].job_id).status is JobStatus.RUNNING
    assert auto.get_attempt(work.attempt.attempt_id).finished_at is None
    assert runs.final_generations("run") == {}


def test_lease_failure_cannot_freeze_generation(tmp_path):
    auto, runs, jobs, generation, selected, _ = _state(tmp_path)
    work = _claim(auto, jobs[0], generation)
    with pytest.raises(LeaseLostError):
        _finish(auto, replace(work, attempt=replace(work.attempt, lease_token="wrong")), selected)
    assert runs.final_generations("run") == {}


def test_later_transaction_failure_rolls_back_final_generation_and_select_result(tmp_path, monkeypatch):
    auto, runs, jobs, generation, selected, _ = _state(tmp_path)
    work = _claim(auto, jobs[0], generation)
    def fail(*args, **kwargs):
        raise RuntimeError("injected after freeze")
    monkeypatch.setattr(store_module, "_transition_finished_job", fail)
    with pytest.raises(RuntimeError, match="injected"):
        _finish(auto, work, selected)
    assert runs.final_generations("run") == {}
    assert auto.get_attempt(work.attempt.attempt_id).finished_at is None
    with sqlite3.connect(auto.db_path) as connection:
        assert connection.execute("SELECT final_generation_json FROM narrative_run_jobs WHERE job_id=?",
                                  (jobs[0].job_id,)).fetchone()[0] is None


def test_preconstructed_resolver_refreshes_generation_after_select_freeze(tmp_path):
    from company_wiki.automation.narrative_worker_factory import _generation_resolver
    auto, runs, jobs, generation, selected, base = _state(tmp_path)
    resolve = _generation_resolver(runs, "run", {jobs[0].subject_id: canonical_json_hash(base)},
                                   selector_version="0.9.0")
    subject = NarrativeSubject.from_raw(selected.to_dict()["result"]["source_ref"])
    with pytest.raises(ValueError, match="SELECTION_NOT_FROZEN"):
        resolve(subject)
    _finish(auto, _claim(auto, jobs[0], generation), selected)
    assert resolve(subject) == canonical_json_hash(runs.final_generation_for_job(jobs[2].job_id))
    assert resolve(subject) != canonical_json_hash(base)


def test_final_generation_cas_accepts_equal_and_rejects_different_result(tmp_path):
    auto, runs, jobs, generation, selected, _ = _state(tmp_path)
    _finish(auto, _claim(auto, jobs[0], generation), selected)
    freeze = getattr(narrative_run_store, "_freeze_select_generation_in_transaction", None)
    assert callable(freeze), "same-transaction generation CAS must exist"
    connection = migrations._open_connection(auto.db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        freeze(connection, jobs[0], selected)
        original = runs.final_generations("run")
        with pytest.raises(RunConflictError, match="final generation"):
            freeze(connection, jobs[0], _selected(digest="b" * 64))
        connection.rollback()
        assert runs.final_generations("run") == original
    finally:
        connection.close()


def test_model_reservation_requires_final_freeze_before_any_accounting(tmp_path):
    auto, runs, jobs, generation, selected, _ = _state(tmp_path)
    summary = _claim(auto, jobs[1], generation)
    options = dict(run_id="run", job_id=jobs[1].job_id, attempt_id=summary.attempt.attempt_id,
                   lease_token=summary.attempt.lease_token, runtime_generation=generation,
                   request_sha256="f" * 64, model_id="fixture", prompt_version="prompt",
                   pricing_version="price", input_tokens_bound=100, max_output_tokens=200,
                   output_bytes_bound=100, now=NOW)
    with pytest.raises(RunConflictError, match="MODEL_SELECTION_NOT_FROZEN"):
        runs.reserve_model_attempt(**options)
    assert runs.reservations_for_run("run") == ()
    _finish(auto, _claim(auto, jobs[0], generation), selected)
    assert runs.reserve_model_attempt(**options).may_send_http


def test_stored_final_cannot_change_the_immutable_model_settings(tmp_path):
    auto, runs, jobs, generation, selected, _ = _state(tmp_path)
    _finish(auto, _claim(auto, jobs[0], generation), selected)
    frozen = runs.final_generation_for_job(jobs[0].job_id)
    frozen["model"]["max_output_tokens"] += 1
    with sqlite3.connect(auto.db_path) as connection:
        connection.execute("UPDATE narrative_run_jobs SET final_generation_json=? WHERE job_id=?",
                           (canonical_json(frozen), jobs[0].job_id))
    with pytest.raises(RunConflictError, match="stored final generation"):
        runs.final_generations("run")


def test_schema_v5_migration_is_additive_preserves_data_and_rolls_back_failure(tmp_path, monkeypatch):
    database = tmp_path / "v5.db"
    statements = (migrations._DDL_V1_STATEMENTS + migrations._DDL_V2_STATEMENTS
                  + migrations._DDL_V3_STATEMENTS + migrations._DDL_V4_STATEMENTS
                  + migrations._DDL_V5_STATEMENTS)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        for statement in statements:
            connection.execute(statement)
        connection.execute("PRAGMA user_version=5")
        connection.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
                           ("historical", "source.revision_registered", "source_revision", "old-document",
                            "a" * 64, "{}", "old-policy", NOW, NOW))
    before = database.read_bytes()
    original = migrations._execute_statement
    def fail(connection, statement):
        original(connection, statement)
        if "final_generation_json" in statement:
            raise sqlite3.OperationalError("injected v6")
    monkeypatch.setattr(migrations, "_execute_statement", fail)
    with pytest.raises(migrations.MigrationExecutionError):
        migrations.migrate_database(database, backup_hook=lambda path, old, new: shutil.copy2(path, tmp_path / "backup.db"))
    assert database.read_bytes() == before
    monkeypatch.setattr(migrations, "_execute_statement", original)
    report = migrations.migrate_database(database, backup_hook=lambda path, old, new: shutil.copy2(path, tmp_path / "backup.db"))
    assert report.from_version == 5 and report.to_version == migrations.SCHEMA_VERSION
    assert report.applied_versions == tuple(range(6, migrations.SCHEMA_VERSION + 1))
    with sqlite3.connect(database) as connection:
        columns = {row[1]: row for row in connection.execute("PRAGMA table_info(narrative_run_jobs)")}
        assert columns["final_generation_json"][3] == 0
        assert connection.execute("SELECT payload_json FROM events WHERE event_id='historical'").fetchone() == ("{}",)
    assert migrations.migrate_database(database).applied_versions == ()


@pytest.mark.parametrize("field,value", [
    ("endpoint", "https://different.invalid/v1/chat/completions"),
    ("max_output_tokens", 201), ("thinking", "disabled"),
    ("reasoning_effort", "high"), ("temperature", 0.7),
    ("reasoning_split", True), ("output_token_field", "max_completion_tokens"),
])
def test_constructed_model_effective_spec_must_match_frozen_generation(field, value):
    from company_wiki.automation import narrative_worker_factory as factory
    verify = getattr(factory, "_verify_effective_model", None)
    assert callable(verify), "constructed model effective spec verifier must exist"
    options = {"model_id": "fixture", "endpoint": "https://model.invalid/v1/chat/completions",
               "api_key_env": "UNREAD_TEST_KEY", "max_output_tokens": 200}
    frozen = {"model_id": "fixture", "endpoint": options["endpoint"],
              "max_output_tokens": 200, "output_token_field": "max_tokens"}
    verify(NarrativeHTTPModel(**options), [frozen])
    options[field] = value
    with pytest.raises(ValueError, match="NARRATIVE_RUN_MODEL_CONFIG_MISMATCH"):
        verify(NarrativeHTTPModel(**options), [frozen])
