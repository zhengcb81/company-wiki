"""Automatic run/generation association; no process or human authority receipt."""

from dataclasses import fields, replace
import hashlib
from pathlib import Path
import shutil
import sqlite3

import pytest

from company_wiki.automation import migrations, narrative_run_store as ledger
from company_wiki.automation.models import (
    Attempt, Event, Job, JobStatus, RiskClass, RuntimeState,
    canonical_json_hash, make_job_key,
)
from company_wiki.automation.store import AutomationStore, ConcurrentUpdateError


T0 = "2026-10-03T10:00:00Z"
T1 = "2026-10-03T10:01:00Z"
T2 = "2026-10-03T10:02:00Z"
T3 = "2026-10-03T10:03:00Z"
SHA = hashlib.sha256(b"ownership-input").hexdigest()


def _source_job(name):
    event = Event(f"event-{name}", "source.revision_registered", "source_revision",
                  name, SHA, "{}", "ownership-test", T0, T0)
    job = Job(
        job_id=f"job-{name}",
        job_key=make_job_key("source.narrative_summarize", "source_revision", name,
                             SHA, "ownership-test", "1.0.0"),
        job_type="source.narrative_summarize", subject_type="source_revision",
        subject_id=name, input_hash=SHA, policy_version="ownership-test",
        handler_version="1.0.0", risk_class=RiskClass.MEDIUM,
        status=JobStatus.READY, priority=0, not_before=T0, max_attempts=3,
        created_from_event_id=event.event_id, created_at=T0, updated_at=T0,
        last_error_code=None, last_error_detail=None,
    )
    return event, job


def _run_values(name, job):
    return dict(run_id=f"run-{name}", input_hash=SHA, job_ids=(job.job_id,),
                model_id="model-one", prompt_version="prompt-one", pricing_version="price-one",
                input_micro_usd_per_million_tokens=300_000,
                output_micro_usd_per_million_tokens=1_200_000,
                max_tokens=1000, max_micro_usd=100_000, max_output_bytes=1000, created_at=T0)


def _setup(tmp_path):
    auto = AutomationStore(tmp_path / "auto.db")
    runs = ledger.NarrativeRunStore(auto.db_path)
    jobs = []
    for name in ("a", "b"):
        event, job = _source_job(name)
        auto.put_event(event)
        auto.put_job(job)
        runs.create_run(**_run_values(name, job))
        jobs.append(job)
    return auto, runs, jobs


def _facts(path):
    with sqlite3.connect(path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return {table: connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
                for (table,) in tables}


def _assert_owner_denied(auto, runs, run_id, generation):
    before = _facts(auto.db_path)
    with pytest.raises(ledger.NarrativeRunError) as error:
        runs.activate_run(run_id, expected_generation=generation, updated_at=T2)
    assert error.value.code == "run_ownership_conflict"
    assert _facts(auto.db_path) == before


def test_creation_does_not_claim_an_enabled_generation(tmp_path):
    auto, runs, _ = _setup(tmp_path)
    gate = auto.set_runtime_gate(RuntimeState.ENABLED, updated_at=T1)
    _assert_owner_denied(auto, runs, "run-a", gate.control_generation)


def test_another_run_cannot_adopt_current_enabled_owner(tmp_path):
    auto, runs, _ = _setup(tmp_path)
    gate = runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    _assert_owner_denied(auto, runs, "run-b", gate.control_generation)


def test_same_run_recovers_enabled_owner_before_any_claim(tmp_path):
    auto, runs, _ = _setup(tmp_path)
    before = _facts(auto.db_path)
    gate = runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    assert gate.desired_state is RuntimeState.ENABLED and gate.control_generation == 2
    assert runs.get_run("run-a").last_runtime_generation == 2
    assert runs.get_run("run-b").last_runtime_generation is None
    reopened = ledger.NarrativeRunStore(auto.db_path)
    recovered = reopened.activate_run("run-a", expected_generation=2, updated_at=T2)
    assert recovered.control_generation == 3
    assert reopened.get_run("run-a").last_runtime_generation == 3
    after = _facts(auto.db_path)
    assert after["attempts"] == []
    for table in before.keys() - {"runtime_gate", "narrative_runs"}:
        assert after[table] == before[table]
    assert reopened.create_run(**_run_values("a", _source_job("a")[1])) == reopened.get_run("run-a")


def test_explicit_pause_allows_another_run_without_adopting_previous_owner(tmp_path):
    auto, runs, _ = _setup(tmp_path)
    first = runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    paused = auto.set_runtime_gate(RuntimeState.PAUSED, expected_generation=first.control_generation,
                                   updated_at=T2)
    second = runs.activate_run("run-b", expected_generation=paused.control_generation, updated_at=T3)
    assert second.control_generation == paused.control_generation + 1
    assert runs.get_run("run-a").last_runtime_generation == first.control_generation
    assert runs.get_run("run-b").last_runtime_generation == second.control_generation


def test_generic_reenable_does_not_revive_an_old_run_binding(tmp_path):
    auto, runs, _ = _setup(tmp_path)
    first = runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    auto.set_runtime_gate(RuntimeState.PAUSED, expected_generation=first.control_generation, updated_at=T2)
    unbound = auto.set_runtime_gate(RuntimeState.ENABLED, updated_at=T2)
    _assert_owner_denied(auto, runs, "run-a", unbound.control_generation)


def test_stale_activation_cas_cannot_modify_an_enabled_owner(tmp_path):
    auto, runs, _ = _setup(tmp_path)
    runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    before = _facts(auto.db_path)
    with pytest.raises(ConcurrentUpdateError):
        runs.activate_run("run-a", expected_generation=1, updated_at=T2)
    assert _facts(auto.db_path) == before


def test_failed_run_binding_rolls_back_the_gate_update(tmp_path):
    auto, runs, _ = _setup(tmp_path)
    with sqlite3.connect(auto.db_path) as connection:
        connection.execute("""CREATE TRIGGER refuse_run_binding BEFORE UPDATE ON narrative_runs
                            BEGIN SELECT RAISE(ABORT,'injected binding failure'); END""")
    before = _facts(auto.db_path)
    with pytest.raises(sqlite3.IntegrityError, match="injected binding failure"):
        runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    assert _facts(auto.db_path) == before
    assert auto.read_runtime_gate().desired_state is RuntimeState.PAUSED


def test_recovery_keeps_unknown_paid_reservation_and_foreign_facts(tmp_path):
    auto, runs, (job, _) = _setup(tmp_path)
    first = runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    claimed = auto.claim_next_ready(worker_id="old-model", attempt_id="attempt-a", lease_token="lease-a",
                                    now=T1, lease_until="2026-10-03T10:10:00Z",
                                    expected_generation=first.control_generation, allowed_job_ids=(job.job_id,))
    runs.reserve_model_attempt(run_id="run-a", job_id=job.job_id, attempt_id=claimed.attempt.attempt_id,
                               lease_token="lease-a", runtime_generation=first.control_generation,
                               request_sha256=SHA, model_id="model-one", prompt_version="prompt-one",
                               pricing_version="price-one", input_tokens_bound=100,
                               max_output_tokens=50, output_bytes_bound=100, now=T1)
    runs.settle_model_usage(run_id="run-a", attempt_id="attempt-a", usage=None,
                            response_sha256=None, error_code="MODEL_TRANSPORT_UNKNOWN", settled_at=T1)
    before_budget = runs.budget_snapshot("run-a")
    before_reservations = runs.reservations_for_run("run-a")
    foreign = auto.get_job("job-b")
    runs.activate_run("run-a", expected_generation=first.control_generation, updated_at=T2)
    assert auto.reap_expired_attempts(now=T2, allowed_job_ids=(job.job_id,)) == ("attempt-a",)
    assert auto.get_attempt("attempt-a").error_code == "RUNTIME_GENERATION_CHANGED"
    assert runs.budget_snapshot("run-a") == before_budget
    assert runs.reservations_for_run("run-a") == before_reservations
    assert auto.get_job("job-b") == foreign


def test_finished_worker_reservation_becomes_unknown_without_refund(tmp_path):
    auto, runs, (job, _) = _setup(tmp_path)
    first = runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    claimed = auto.claim_next_ready(worker_id="old-model", attempt_id="attempt-a", lease_token="lease-a",
                                    now=T1, lease_until="2026-10-03T10:10:00Z",
                                    expected_generation=first.control_generation, allowed_job_ids=(job.job_id,))
    reserved = runs.reserve_model_attempt(run_id="run-a", job_id=job.job_id,
        attempt_id=claimed.attempt.attempt_id, lease_token="lease-a",
        runtime_generation=first.control_generation, request_sha256=SHA,
        model_id="model-one", prompt_version="prompt-one", pricing_version="price-one",
        input_tokens_bound=100, max_output_tokens=50, output_bytes_bound=100, now=T1).record

    recovered = runs.activate_run("run-a", expected_generation=first.control_generation, updated_at=T2)
    assert auto.reap_expired_attempts(now=T2, allowed_job_ids=(job.job_id,)) == ("attempt-a",)
    assert runs.settle_finished_attempt_reservations(run_id="run-a", settled_at=T3) == ("attempt-a",)

    settled = runs.get_reservation("run-a", "attempt-a")
    assert settled.usage_status == "unknown" and settled.usage_settled_at == T3
    assert settled.error_code == "MODEL_WORKER_LOST"
    assert settled.charged_tokens == reserved.reserved_tokens
    assert settled.charged_micro_usd == reserved.reserved_micro_usd
    assert settled.response_sha256 is None
    budget = runs.budget_snapshot("run-a")
    assert budget.unknown_reservations == 1 and budget.unsettled_reservations == 0
    assert runs.settle_finished_attempt_reservations(run_id="run-a", settled_at=T3) == ()
    assert runs.get_run("run-a").last_runtime_generation == recovered.control_generation


def test_active_attempt_reservation_is_never_reconciled(tmp_path):
    auto, runs, (job, _) = _setup(tmp_path)
    gate = runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    claimed = auto.claim_next_ready(worker_id="model", attempt_id="attempt-active", lease_token="lease-active",
                                    now=T1, lease_until="2026-10-03T10:10:00Z",
                                    expected_generation=gate.control_generation, allowed_job_ids=(job.job_id,))
    runs.reserve_model_attempt(run_id="run-a", job_id=job.job_id,
        attempt_id=claimed.attempt.attempt_id, lease_token="lease-active",
        runtime_generation=gate.control_generation, request_sha256=SHA,
        model_id="model-one", prompt_version="prompt-one", pricing_version="price-one",
        input_tokens_bound=100, max_output_tokens=50, output_bytes_bound=100, now=T1)
    assert runs.settle_finished_attempt_reservations(run_id="run-a", settled_at=T2) == ()
    assert runs.get_reservation("run-a", "attempt-active").usage_status == "reserved"


def test_reservation_reconciliation_tolerates_lost_commit_acknowledgement(tmp_path, monkeypatch):
    auto, runs, (job, _) = _setup(tmp_path)
    gate = runs.activate_run("run-a", expected_generation=1, updated_at=T1)
    claimed = auto.claim_next_ready(worker_id="old-model", attempt_id="attempt-ack", lease_token="lease-ack",
                                    now=T1, lease_until="2026-10-03T10:10:00Z",
                                    expected_generation=gate.control_generation, allowed_job_ids=(job.job_id,))
    runs.reserve_model_attempt(run_id="run-a", job_id=job.job_id,
        attempt_id=claimed.attempt.attempt_id, lease_token="lease-ack",
        runtime_generation=gate.control_generation, request_sha256=SHA,
        model_id="model-one", prompt_version="prompt-one", pricing_version="price-one",
        input_tokens_bound=100, max_output_tokens=50, output_bytes_bound=100, now=T1)
    runs.activate_run("run-a", expected_generation=gate.control_generation, updated_at=T2)
    auto.reap_expired_attempts(now=T2, allowed_job_ids=(job.job_id,))
    write = runs._write
    lost_ack = True

    def commit_then_lose_ack(operation):
        nonlocal lost_ack
        result = write(operation)
        if lost_ack:
            lost_ack = False
            raise TimeoutError("injected lost commit acknowledgement")
        return result

    monkeypatch.setattr(runs, "_write", commit_then_lose_ack)
    with pytest.raises(TimeoutError, match="lost commit acknowledgement"):
        runs.settle_finished_attempt_reservations(run_id="run-a", settled_at=T3)
    # The caller cannot tell whether the first transaction committed. Retrying
    # reads the durable state and does not charge or settle the attempt again.
    assert runs.get_reservation("run-a", "attempt-ack").usage_status == "unknown"
    assert runs.settle_finished_attempt_reservations(run_id="run-a", settled_at=T3) == ()
    assert runs.budget_snapshot("run-a").unknown_reservations == 1


def test_run_record_new_field_is_defaulted_after_the_old_positional_fields():
    record = ledger.RunRecord("run", SHA, SHA, "model", "prompt", "price", 1, 1,
                              100, 100, 100, "open", None, T0, T0, ())
    assert record.last_runtime_generation is None
    assert fields(record)[-1].name == "last_runtime_generation"


def _insert(connection, table, values):
    names = tuple(values)
    connection.execute(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
                       tuple(values.values()))


def _v3_with_paid_facts(path: Path):
    """Frozen v3 history, built without invoking the current migration algorithm."""
    with sqlite3.connect(path) as connection:
        # Historical AUTO connections use WAL before beginning a migration.
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        for sql in migrations._DDL_V1_STATEMENTS + migrations._DDL_V2_STATEMENTS + migrations._DDL_V3_STATEMENTS:
            connection.execute(sql)
        connection.execute("PRAGMA user_version=3")
        connection.execute("UPDATE runtime_gate SET desired_state='enabled',control_generation=2,updated_at=?", (T1,))
        event, job = _source_job("legacy")
        _insert(connection, "events", event.to_dict())
        _insert(connection, "jobs", replace(job, status=JobStatus.RUNNING).to_dict())
        attempt = Attempt("legacy-attempt", job.job_id, 1, "legacy-model", "legacy-token",
                          "2026-10-03T10:10:00Z", T1, T1, None, None, None, None, None, 2)
        _insert(connection, "attempts", attempt.to_dict())
        options = _run_values("legacy", job)
        options.pop("job_ids")
        options.update(scope_sha256=canonical_json_hash([job.job_id]), state="open", block_reason=None, updated_at=T0)
        _insert(connection, "narrative_runs", options)
        _insert(connection, "narrative_run_jobs", dict(run_id="run-legacy", job_id=job.job_id,
                                                       input_hash=SHA, handler_version=job.handler_version))
        _insert(connection, "narrative_model_reservations", dict(
            attempt_id="legacy-attempt", run_id="run-legacy", job_id=job.job_id, request_sha256=SHA,
            input_tokens_bound=100, max_output_tokens=50, output_bytes_bound=100,
            reserved_micro_usd=90, usage_status="unknown", input_tokens=None, output_tokens=None,
            estimated_micro_usd=None, response_sha256=None, error_code="MODEL_TRANSPORT_UNKNOWN",
            output_bytes=None, output_sha256=None, reserved_at=T1, usage_settled_at=T1, output_settled_at=None,
        ))


def test_v3_upgrade_preserves_all_facts_and_leaves_old_owner_unbound(tmp_path):
    database = tmp_path / "legacy.db"
    _v3_with_paid_facts(database)
    before = _facts(database)
    original_bytes = database.read_bytes()
    calls = []

    def backup(source, old, new):
        calls.append((old, new))
        return shutil.copy2(source, tmp_path / "before-v3.db")

    report = migrations.migrate_database(database, backup_hook=backup)
    assert report.to_version == 4 and report.applied_versions == (4,)
    assert calls == [(3, 4)]
    assert (tmp_path / "before-v3.db").read_bytes() == original_bytes
    after = _facts(database)
    assert after.keys() == before.keys()
    for table in before.keys() - {"narrative_runs"}:
        assert after[table] == before[table]
    assert [row[:-1] for row in after["narrative_runs"]] == before["narrative_runs"]
    assert after["narrative_runs"][0][-1] is None
    auto = AutomationStore(database)
    runs = ledger.NarrativeRunStore(database)
    _assert_owner_denied(auto, runs, "run-legacy", 2)


def test_v3_readonly_classification_requires_explicit_upgrade_for_run_store(tmp_path):
    database = tmp_path / "legacy.db"
    _v3_with_paid_facts(database)
    before = database.read_bytes()
    assert migrations.validate_database(database).user_version == 3
    with pytest.raises(ledger.NarrativeRunError, match="explicitly migrated"):
        ledger.NarrativeRunStore(database)
    with pytest.raises(migrations.BackupError):
        migrations.migrate_database(database)
    assert database.read_bytes() == before


def test_failed_v4_ddl_restores_exact_v3_database(tmp_path, monkeypatch):
    database = tmp_path / "legacy.db"
    _v3_with_paid_facts(database)
    before = database.read_bytes()
    execute = migrations._execute_statement

    def fail(connection, sql):
        if "last_runtime_generation" in sql:
            raise sqlite3.OperationalError("injected v4 failure")
        return execute(connection, sql)

    monkeypatch.setattr(migrations, "_execute_statement", fail)
    with pytest.raises(migrations.MigrationExecutionError, match="injected v4 failure"):
        migrations.migrate_database(database, backup_hook=lambda source, old, new: shutil.copy2(source, tmp_path / "backup.db"))
    assert database.read_bytes() == before
    assert migrations.validate_database(database).user_version == 3
