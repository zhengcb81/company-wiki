"""Schema extensions must not widen AUTO persistence reads or change recovery."""
from __future__ import annotations

import hashlib

import pytest

from company_wiki.automation.models import (
    HandlerError, HandlerMetrics, HandlerOutcome, HandlerResult, JobStatus,
)
from unit.test_terminal_narrative_receipts import T3, terminal_fixture
from unit.du11_paid_response.test_paid_response import (
    REQUEST, T1, caller, http as http, seed_owned,
)


FUTURE_COLUMN = "r5_future_private_column"


def _extend_and_guard(auto, table, monkeypatch):
    assert table in {"narrative_runs", "narrative_model_reservations", "jobs"}
    auto._write_transaction(lambda connection: connection.execute(
        f"ALTER TABLE {table} ADD COLUMN {FUTURE_COLUMN} TEXT DEFAULT 'private-extension'"
    ))
    connect = auto._connect
    inspected = []

    class Connection:
        def __init__(self):
            self.inner = connect()

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def execute(self, sql, parameters=()):
            cursor = self.inner.execute(sql, parameters)
            if cursor.description:
                names = tuple(column[0] for column in cursor.description)
                assert FUTURE_COLUMN not in names, f"schema extension leaked into read: {sql}"
                inspected.append(names)
            return cursor

    monkeypatch.setattr(auto, "_connect", Connection)
    return inspected


def test_terminal_compaction_does_not_read_future_run_columns(tmp_path, monkeypatch):
    with terminal_fixture(tmp_path) as state:
        original_hash = hashlib.sha256(state.payload).hexdigest()
        inspected = _extend_and_guard(state.auto, "narrative_runs", monkeypatch)
        result = state.auto.compact_terminal_narrative_jobs(
            job_ids=state.job_ids, final_artifact=state.pin, compacted_at=T3,
        )
        assert result.attempts_compacted == 3
        repeat = state.auto.compact_terminal_narrative_jobs(
            job_ids=state.job_ids, final_artifact=state.pin, compacted_at=T3,
        )
        assert repeat.already_compacted and repeat.attempts_compacted == 0
        assert hashlib.sha256(state.payload).hexdigest() == original_hash
        assert inspected


@pytest.mark.parametrize("table", ["narrative_model_reservations", "jobs"])
def test_paid_requeue_projects_stable_columns_and_preserves_paid_attempt(
    tmp_path, http, monkeypatch, table,
):
    state = seed_owned(tmp_path, http, dependent=True)
    caller(state).generate(state.context(), REQUEST)
    paid = state.runs.get_reservation("run", "paid")
    state.auto.finish_attempt(
        attempt_id="paid", lease_token="lease", runtime_generation=state.generation,
        finished_at=T1,
        result=HandlerResult(
            HandlerOutcome.TERMINAL_FAILURE, {}, (), (), HandlerMetrics(92, 0.001, 1),
            HandlerError("SUMMARY_INVALID", "synthetic decode failure"),
        ),
    )
    original_attempt = state.auto.get_attempt("paid")
    original_reservations = state.runs.reservations_for_run("run")
    inspected = _extend_and_guard(state.auto, table, monkeypatch)
    changed = state.auto.retry_paid_narrative_summary(
        run_id="run", job_id="job", request_sha256=paid.request_sha256,
        now=T1, expected_generation=state.generation,
    )
    assert changed == ("job", "verify")
    assert state.auto.get_job("job").status is JobStatus.READY
    verify = state.auto.get_job("verify")
    assert verify.status is JobStatus.PLANNED and verify.last_error_code is None
    assert not state.auto.list_attempts("verify")
    assert state.auto.get_attempt("paid") == original_attempt
    assert state.runs.reservations_for_run("run") == original_reservations
    assert state.http.calls == 1
    assert inspected


@pytest.mark.parametrize("reader", [
    "get_reservation", "budget_snapshot", "model_attempts_for_job", "reservations_for_run",
])
def test_reservation_readers_ignore_added_internal_column(tmp_path, http, reader):
    state = seed_owned(tmp_path, http)
    caller(state).generate(state.context(), REQUEST)

    def read():
        if reader == "get_reservation":
            return state.runs.get_reservation("run", "paid")
        if reader == "model_attempts_for_job":
            return state.runs.model_attempts_for_job(run_id="run", job_id="job")
        return getattr(state.runs, reader)("run")

    before = read()
    # A nullable internal accounting field may be added by the schema owner;
    # public reservation DTOs and conservative fee calculations stay exact.
    state.auto._write_transaction(lambda connection: connection.execute(
        f"ALTER TABLE narrative_model_reservations ADD COLUMN {FUTURE_COLUMN} TEXT"
    ))
    assert read() == before