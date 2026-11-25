"""Kill real processes at the AUTO commit and native observation boundaries."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import sysconfig
import time

import pytest

from company_wiki.automation import models
from company_wiki.automation.store import AutomationStore


START = "2026-11-25T09:00:00Z"
CLAIM = "2026-11-25T09:01:00Z"
EXPIRE = "2026-11-25T09:02:00Z"
AFTER = "2026-11-25T09:03:00Z"
PROJECT = Path(__file__).resolve().parents[2]

CHILD = """\
import errno, os, sys, time
from pathlib import Path
from company_wiki import runtime_feedback
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.store import AutomationStore
from company_wiki.automation.worker import HandlerExecutor, Worker, reap_worker_attempts

mode, boundary, database, job_id, now = sys.argv[1:]
original_atomic = runtime_feedback._atomic

def wait_until_killed():
    temporary = Path('paused.tmp')
    temporary.write_text(str(os.getpid()), encoding='ascii')
    temporary.replace('paused')
    while True:
        time.sleep(0.04)

def atomic(path, content):
    if boundary == 'database-commit' and path.name.endswith('.diagnostic.json'):
        wait_until_killed()
    original_atomic(path, content)
    if boundary == 'ready-published' and path.suffix == '.ready':
        wait_until_killed()

runtime_feedback._atomic = atomic
store = AutomationStore(Path(database))
if mode == 'reap':
    reap_worker_attempts(store, now=now, allowed_job_ids=(job_id,))
else:
    class Clock:
        def now(self):
            return now

    def fail(_):
        with open('business-calls', 'a', encoding='ascii') as stream:
            stream.write('executed\\n')
        try:
            raise OSError(errno.EIO, 'original fixture read failure')
        except OSError as error:
            raise ValueError('api_key=synthetic-private-fixture') from error

    executor = HandlerExecutor()
    executor.register('timer.execute_step', fail)
    Worker(store, create_default_registry(), executor, clock=Clock(),
           allowed_job_types=('timer.execute_step',), allowed_job_ids=(job_id,)).process_one()
"""


def _seed(store, job_id, *, max_attempts):
    digest = "f" * 64
    event = models.Event("evt-" + job_id, "timer.fired", "source", job_id,
                         digest, "{}", "v1", START, START)
    store.put_event(event)
    store.put_job(models.Job(
        job_id=job_id,
        job_key=models.make_job_key("timer.execute_step", "source", job_id, digest, "v1", "1.0.0"),
        job_type="timer.execute_step", subject_type="source", subject_id=job_id,
        input_hash=digest, policy_version="v1", handler_version="1.0.0",
        risk_class=models.RiskClass.LOW, status=models.JobStatus.READY, priority=0,
        not_before=START, max_attempts=max_attempts, created_from_event_id=event.event_id,
        created_at=START, updated_at=START, last_error_code=None, last_error_detail=None,
    ))


def _snapshot(folder):
    return {path.name: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in folder.glob("feedback-*")}


def _environment(root):
    paths = sysconfig.get_paths()
    search_path = os.pathsep.join(dict.fromkeys((str(PROJECT / "src"), paths["purelib"], paths["platlib"])))
    env = dict(os.environ, PYTHONPATH=search_path, PYTHONDONTWRITEBYTECODE="1",
               RESEARCH_FEEDBACK_DIR=str(root / "observations"),
               LOCALAPPDATA=str(root / "state"), XDG_STATE_HOME=str(root / "state"))
    env.pop("RESEARCH_FEEDBACK_OUT", None)
    return env


def _flush(root, database, job_id, *, env=None, exit_code=0):
    process = subprocess.run(
        [sys.executable, "-B", "-m", "company_wiki.automation.cli", "feedback-flush",
         "--db", str(database), "--job-id", job_id],
        cwd=root, env=env or _environment(root), capture_output=True, check=False, timeout=15,
    )
    assert process.returncode == exit_code, process.stderr.decode(errors="replace")
    return json.loads(process.stdout)


@pytest.mark.parametrize("mode", ["reap", "handler"])
@pytest.mark.parametrize("boundary", ["database-commit", "ready-published"])
def test_hard_stop_after_commit_or_ready_repairs_original_attempt(tmp_path, mode, boundary):
    store = AutomationStore(tmp_path / "AUTO.sqlite")
    job_id = "original"
    _seed(store, job_id, max_attempts=3)
    _seed(store, "sibling", max_attempts=3)
    gate = store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=CLAIM)
    if mode == "reap":
        assert store.claim_next_ready(
            worker_id="lost-worker", attempt_id="first-attempt", lease_token="lost-lease",
            now=CLAIM, lease_until=EXPIRE, expected_generation=gate.control_generation,
            allowed_job_ids=(job_id,),
        ) is not None

    # The Windows venv redirector creates a second process. Launch the same
    # base interpreter directly so the retained Popen handle owns this worker.
    worker_python = sys._base_executable if os.name == "nt" else sys.executable
    child = subprocess.Popen(
        [worker_python, "-B", "-c", CHILD, mode, boundary, str(store.db_path), job_id, AFTER],
        cwd=tmp_path, env=_environment(tmp_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        marker = tmp_path / "paused"
        end = time.monotonic() + 12
        while not marker.is_file() and child.poll() is None and time.monotonic() < end:
            time.sleep(0.03)
        assert marker.is_file(), child.stderr.read().decode(errors="replace") if child.poll() is not None else boundary
        assert marker.read_text(encoding="ascii") == str(child.pid)
        attempt, = store.list_attempts(job_id)
        assert attempt.finished_at == AFTER
        state = store.get_job(job_id)
        assert state.status.value == ("retry_wait" if mode == "reap" else "dead_letter")
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)
    assert child.returncode != 0

    inbox = tmp_path / "observations"
    existing = _snapshot(inbox)
    assert len(existing) == (3 if boundary == "ready-published" else 0)
    # Owner observation-only recovery is independent of enabling the worker.
    store.set_runtime_gate(models.RuntimeState.PAUSED, updated_at=AFTER)
    assert _flush(tmp_path, store.db_path, "sibling")["published"] == 0
    assert _snapshot(inbox) == existing
    assert _flush(tmp_path, store.db_path, job_id)["published"] == 1
    recovered = _snapshot(inbox)
    if existing:
        assert recovered == existing
    marker, = inbox.glob("feedback-*.ready")
    packet = json.loads(marker.with_suffix(".jsonl").read_bytes())
    assert (packet["run_id"], packet["attempt_id"], packet["actual"]) == (
        job_id, attempt.attempt_id, state.status.value,
    )
    details = json.loads((inbox / packet["details_ref"]).read_bytes())
    assert details["reason"] == attempt.error_code
    if mode == "handler":
        assert [item["type"] for item in details["exceptions"]] == ["ValueError", "OSError"]
        assert details["exceptions"][1]["messages"] == ["original fixture read failure"]
        assert "synthetic-private-fixture" not in json.dumps(details)

    assert _flush(tmp_path, store.db_path, job_id)["published"] == 0
    assert _snapshot(inbox) == recovered
    assert store.get_job(job_id) == state
    assert store.list_attempts(job_id) == (attempt,)
    assert not store.list_attempts("sibling") and not store.list_effects(job_id)
    with closing(sqlite3.connect(store.db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM narrative_model_reservations").fetchone() == (0,)
    calls = tmp_path / "business-calls"
    assert calls.read_text() == "executed\n" if mode == "handler" else not calls.exists()


def test_recovery_defers_when_native_sinks_fail_then_acknowledges_after_consumption(tmp_path):
    store = AutomationStore(tmp_path / "AUTO.sqlite")
    job_id = "original"
    _seed(store, job_id, max_attempts=1)
    gate = store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=CLAIM)
    assert store.claim_next_ready(
        worker_id="lost-worker", attempt_id="first-attempt", lease_token="lost-lease",
        now=CLAIM, lease_until=EXPIRE, expected_generation=gate.control_generation,
        allowed_job_ids=(job_id,),
    ) is not None
    store.reap_expired_attempt_outcomes(now=AFTER, allowed_job_ids=(job_id,))
    original, = store.pending_worker_feedback(allowed_job_ids=(job_id,))
    impossible = tmp_path / "blocked-directory"
    impossible.touch()
    explicit = tmp_path / "supervised.jsonl"
    env = _environment(tmp_path) | {
        "RESEARCH_FEEDBACK_DIR": str(impossible), "RESEARCH_FEEDBACK_OUT": str(explicit),
        "LOCALAPPDATA": str(impossible), "XDG_STATE_HOME": str(impossible),
    }
    failed = _flush(tmp_path, store.db_path, job_id, env=env, exit_code=1)
    assert failed == {"published": 0, "deferred": 1, "unavailable": False}
    assert store.pending_worker_feedback() == (original,) and not explicit.exists()
    assert store.pending_worker_feedback(allowed_job_ids=()) == ()
    assert not store.ack_worker_feedback("wrong-job", original[1], original[2])

    # The intake can remove .ready before AUTO's publisher gets its DB ack.
    # Simulate just that consumer action after a real atomic publication.
    env = _environment(tmp_path)
    producer = subprocess.run(
        [sys.executable, "-B", "-c", "import sys; from company_wiki.runtime_feedback "
         "import publish_worker_failure; raise SystemExit(not publish_worker_failure("
         "sys.stdin.read(), job_id=sys.argv[1], attempt_id=sys.argv[2]))", *original[:2]],
        input=original[2].encode("ascii"), cwd=tmp_path, env=env,
        capture_output=True, timeout=15, check=False,
    )
    assert producer.returncode == 0, producer.stderr.decode(errors="replace")
    inbox = tmp_path / "observations"
    marker, = inbox.glob("*.ready")
    marker.unlink()
    before = _snapshot(inbox)
    assert _flush(tmp_path, store.db_path, job_id)["published"] == 1
    assert _snapshot(inbox) == before
    assert store.pending_worker_feedback() == ()


def test_worker_feedback_preserves_existing_schema_and_other_notification_channels(tmp_path):
    store = AutomationStore(tmp_path / "AUTO.sqlite")
    job_id = "original"
    _seed(store, job_id, max_attempts=1)
    gate = store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=CLAIM)
    claimed = store.claim_next_ready(
        worker_id="old-worker", attempt_id="original-attempt", lease_token="old-lease",
        now=CLAIM, lease_until=EXPIRE, expected_generation=gate.control_generation,
        allowed_job_ids=(job_id,),
    )
    assert claimed is not None
    before = store.schema_report()
    with closing(sqlite3.connect(store.db_path)) as conn:
        conn.execute(
            "INSERT INTO notifications (notification_id,notification_key,job_id,channel,severity,payload_json,"
            "status,created_at) VALUES ('older','older',?,'historical','warning','{}','pending',?)",
            (job_id, CLAIM),
        )
        conn.commit()

    store.reap_expired_attempt_outcomes(now=AFTER, allowed_job_ids=(job_id,))
    observation, = store.pending_worker_feedback()
    assert observation[:2] == (job_id, claimed.attempt.attempt_id)
    assert _flush(tmp_path, store.db_path, job_id)["published"] == 1
    assert store.pending_worker_feedback() == ()
    assert store.schema_report() == before
    with closing(sqlite3.connect(store.db_path)) as conn:
        assert conn.execute("SELECT notification_id, channel, payload_json, status FROM notifications").fetchall() == [
            ("older", "historical", "{}", "pending"),
        ]


def test_feedback_flush_does_not_create_a_missing_owner_database(tmp_path):
    missing = tmp_path / "missing.sqlite"
    result = _flush(tmp_path, missing, "job", exit_code=1)
    assert result["unavailable"] is True and result["reason"] == "automation_database_missing"
    assert list(tmp_path.iterdir()) == []


def _queue_expired(store, job_id, attempt_id):
    _seed(store, job_id, max_attempts=1)
    gate = store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=CLAIM)
    assert store.claim_next_ready(
        worker_id="worker", attempt_id=attempt_id, lease_token="lease", now=CLAIM,
        lease_until=EXPIRE, expected_generation=gate.control_generation, allowed_job_ids=(job_id,),
    ) is not None
    store.reap_expired_attempt_outcomes(now=AFTER, allowed_job_ids=(job_id,))
    original, = store.pending_worker_feedback(allowed_job_ids=(job_id,))
    return original


def test_frozen_packet_must_match_the_original_attempt_selected_by_the_queue(tmp_path):
    from company_wiki.runtime_feedback_values import freeze_worker_failure

    store = AutomationStore(tmp_path / "AUTO.sqlite")
    job_id, attempt_id = "original internal id", "attempt with space"
    original = _queue_expired(store, job_id, attempt_id)
    wrong = freeze_worker_failure("other-job", "other-attempt", "dead_letter", "LEASE_EXPIRED")
    with closing(sqlite3.connect(store.db_path)) as conn, conn:
        conn.execute("UPDATE notifications SET payload_json=? WHERE channel='worker-feedback'", (wrong,))

    failed = _flush(tmp_path, store.db_path, job_id, exit_code=1)
    assert failed == {"published": 0, "deferred": 1, "unavailable": False}
    assert store.pending_worker_feedback() == ((job_id, attempt_id, wrong),)
    assert not (tmp_path / "observations").exists()
    with closing(sqlite3.connect(store.db_path)) as conn, conn:
        conn.execute("UPDATE notifications SET payload_json=? WHERE channel='worker-feedback'", (original[2],))
    assert _flush(tmp_path, store.db_path, job_id)["published"] == 1
    assert store.pending_worker_feedback() == ()


def test_replay_does_not_replace_a_divergent_existing_diagnostic(tmp_path):
    store = AutomationStore(tmp_path / "AUTO.sqlite")
    original = _queue_expired(store, "original", "original-attempt")
    frozen = json.loads(original[2])
    inbox = tmp_path / "observations"
    inbox.mkdir()
    details = inbox / frozen["row"]["details_ref"]
    details.write_text('{"reason":"previous diagnostic evidence"}\n', encoding="utf-8")
    before = _snapshot(inbox)

    result = _flush(tmp_path, store.db_path, original[0], exit_code=1)
    assert result["deferred"] == 1 and result["published"] == 0
    assert store.pending_worker_feedback() == (original,)
    assert _snapshot(inbox) == before

    details.unlink()
    assert _flush(tmp_path, store.db_path, original[0])["published"] == 1
    assert store.pending_worker_feedback() == ()
