"""Finite batches query only their jobs; no whole-store Python filtering."""

import sqlite3

from company_wiki.automation.models import Event, Job, JobStatus, RiskClass, make_job_key
from company_wiki.automation.store import AutomationStore


def _seed(tmp_path, monkeypatch):
    store = AutomationStore(tmp_path / "auto.sqlite3")
    now = "2026-07-12T08:00:00Z"
    digest = "a" * 64
    for index, status in enumerate((JobStatus.READY, JobStatus.RUNNING, JobStatus.RUNNING)):
        event_id = f"event-{index}"
        subject_id = f"source-{index}"
        store.put_event(Event(event_id=event_id, event_type="source.revision_registered",
            subject_type="source_revision", subject_id=subject_id, input_hash=digest,
            payload_json="{}", policy_version="v1", occurred_at=now, observed_at=now))
        store.put_job(Job(job_id=f"job-{index}",
            job_key=make_job_key("source.normalize", "source", subject_id, digest, "v1", "1"),
            job_type="source.normalize", subject_type="source", subject_id=subject_id,
            input_hash=digest, policy_version="v1", handler_version="1", risk_class=RiskClass.LOW,
            status=status, priority=index, not_before=now, max_attempts=3,
            created_from_event_id=event_id, created_at=now, updated_at=now,
            last_error_code=None, last_error_detail=None))
    queries = []
    connections = []
    connect = sqlite3.connect

    def traced(database, *args, **options):
        conn = connect(database, *args, **options)
        connections.append((database, options.get("uri", False)))
        conn.set_trace_callback(queries.append)
        return conn

    # Observe the actual SQLite connection, independent of the store's
    # read/write connection helpers.
    monkeypatch.setattr(sqlite3, "connect", traced)
    return store, queries, connections


def _assert_readonly(connections, expected_count):
    assert len(connections) == expected_count
    assert all(uri and database.endswith("?mode=ro") for database, uri in connections)


def test_job_and_event_scopes_are_intersected_in_sql_before_ordering(tmp_path, monkeypatch):
    store, queries, connections = _seed(tmp_path, monkeypatch)
    result = store.list_jobs(job_ids=("job-2", "job-1", "job-1"),
                             event_ids=("event-0", "event-1"), status=JobStatus.RUNNING)
    assert tuple(job.job_id for job in result) == ("job-1",)
    matching = [q for q in queries if "FROM jobs" in q]
    assert len(matching) == 1
    sql = matching[0]
    assert "job_id IN" in sql and "created_from_event_id IN" in sql and "status =" in sql
    assert sql.index("WHERE") < sql.index("ORDER BY")
    assert tuple(job.job_id for job in store.list_jobs()) == ("job-2", "job-1", "job-0")
    _assert_readonly(connections, 2)


def test_explicit_empty_scope_means_no_query_not_all_jobs(tmp_path, monkeypatch):
    store, queries, connections = _seed(tmp_path, monkeypatch)
    assert store.list_jobs(job_ids=()) == ()
    assert store.list_jobs(event_ids=()) == ()
    assert queries == []
    assert connections == []


def test_foreign_running_is_exists_query_and_honours_owner_scope(tmp_path, monkeypatch):
    store, queries, connections = _seed(tmp_path, monkeypatch)
    assert store.has_running_jobs_outside_scope(("job-1",)) is True
    assert store.has_running_jobs_outside_scope(("job-1", "job-2")) is False
    assert store.has_running_jobs_outside_scope(()) is True
    matching = [q for q in queries if "FROM jobs" in q]
    assert len(matching) == 3
    assert all("SELECT 1" in sql and "status = 'running'" in sql and "LIMIT 1" in sql for sql in matching)
    _assert_readonly(connections, 3)
