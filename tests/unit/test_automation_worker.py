"""AUTO-4 worker/retry/outbox contract tests.

Each test asserts the production module paths exist before importing them.
All tests use fixed values and tmp_path; no network, LLM or production data.
"""

import hashlib
from pathlib import Path



ROOT = Path(__file__).resolve().parents[2]
WORKER_PATH = ROOT / "src" / "company_wiki" / "automation" / "worker.py"
RETRY_PATH = ROOT / "src" / "company_wiki" / "automation" / "retry.py"
OUTBOX_PATH = ROOT / "src" / "company_wiki" / "automation" / "outbox.py"


def _worker_mod():
    assert WORKER_PATH.is_file()
    from company_wiki.automation import worker
    return worker


def _retry_mod():
    assert RETRY_PATH.is_file()
    from company_wiki.automation import retry
    return retry


def _store_mod():
    from company_wiki.automation import store
    return store


def _registry_mod():
    from company_wiki.automation import registry
    return registry


def _models():
    from company_wiki.automation import models
    return models


INPUT_HASH = hashlib.sha256(b"auto-4-input").hexdigest()


class FixedClock:
    def __init__(self, time_str: str):
        self._time = time_str
    def now(self) -> str:
        return self._time


class SequentialIDGen:
    def __init__(self, prefix: str = "id"):
        self._counter = 0
        self._prefix = prefix
    def new_id(self) -> str:
        self._counter += 1
        return f"{self._prefix}-{self._counter:04d}"


def _make_event(m=None, **overrides):
    m = m or _models()
    defaults = dict(
        event_id="evt-auto4-001",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id="rev-auto4-001",
        input_hash=INPUT_HASH,
        payload_json=m.canonical_json({"key": "value"}),
        policy_version="v1",
        occurred_at="2026-07-12T10:00:00Z",
        observed_at="2026-07-12T10:00:00Z",
    )
    defaults.update(overrides)
    return m.Event(**defaults)


def _make_job(m=None, store=None, status=None, **overrides):
    m = m or _models()
    status = status or m.JobStatus.READY
    defaults = dict(
        job_id="job-auto4-001",
        job_type="timer.execute_step",
        subject_type="source_revision",
        subject_id="rev-auto4-001",
        input_hash=INPUT_HASH,
        policy_version="v1",
        handler_version="1.0.0",
        risk_class=m.RiskClass.LOW,
        status=status,
        priority=0,
        not_before="2026-07-12T09:00:00Z",
        max_attempts=3,
        created_from_event_id="evt-auto4-001",
        created_at="2026-07-12T10:00:00Z",
        updated_at="2026-07-12T10:00:00Z",
        last_error_code=None,
        last_error_detail=None,
    )
    defaults.update(overrides)
    # Compute job_key from final values.
    defaults["job_key"] = m.make_job_key(
        defaults["job_type"], defaults["subject_type"], defaults["subject_id"],
        defaults["input_hash"], defaults["policy_version"], defaults["handler_version"],
    )
    return m.Job(**defaults)


def _setup_store_with_job(s, m, tmp_path, status=None):
    store = s.AutomationStore(tmp_path / "automation.db")
    store.set_runtime_gate(
        m.RuntimeState.ENABLED, updated_at="2026-07-12T10:00:30Z"
    )
    store.put_event(_make_event(m=m))
    job = _make_job(m=m, status=status or m.JobStatus.READY)
    store.put_job(job)
    return store


def _make_fake_handler(outcome, result=None, effects=(), error=None):
    m = _models()
    def handler(input_data):
        return m.HandlerResult(
            outcome=outcome,
            result=result or {},
            artifacts=(),
            effects=effects,
            metrics=m.HandlerMetrics(tokens=10, cost_usd=0.001, duration_ms=50),
            error=error,
        )
    return handler


# --------------------------------------------------------------------------- #
# Retry tests.
# --------------------------------------------------------------------------- #
def test_retry_delay_exponential_backoff():
    r = _retry_mod()
    d1 = r.compute_retry_delay(1, base_seconds=10, max_delay_seconds=1000, job_id="j1")
    d2 = r.compute_retry_delay(2, base_seconds=10, max_delay_seconds=1000, job_id="j1")
    d3 = r.compute_retry_delay(3, base_seconds=10, max_delay_seconds=1000, job_id="j1")
    assert d1 < d2 < d3


def test_retry_delay_capped_at_max():
    r = _retry_mod()
    d = r.compute_retry_delay(100, base_seconds=10, max_delay_seconds=60, job_id="j1")
    # Should be capped at max + jitter.
    assert d <= 60 + 10  # max + base (jitter range)


def test_retry_delay_deterministic_jitter():
    r = _retry_mod()
    d1 = r.compute_retry_delay(1, base_seconds=10, max_delay_seconds=1000, job_id="j1")
    d2 = r.compute_retry_delay(1, base_seconds=10, max_delay_seconds=1000, job_id="j1")
    assert d1 == d2  # same job_id → same jitter


def test_classify_outcome_succeeded():
    r = _retry_mod()
    m = _models()
    status, code = r.classify_outcome(
        m.HandlerOutcome.SUCCEEDED, None, (), (), (), 1, 3
    )
    assert status is m.JobStatus.SUCCEEDED
    assert code is None


def test_classify_outcome_retryable_within_budget():
    r = _retry_mod()
    m = _models()
    status, code = r.classify_outcome(
        m.HandlerOutcome.RETRYABLE, "IO_TRANSIENT", ("IO_TRANSIENT",), (), (), 1, 3
    )
    assert status is m.JobStatus.RETRY_WAIT
    assert code == "IO_TRANSIENT"


def test_classify_outcome_retryable_exhausted():
    r = _retry_mod()
    m = _models()
    status, code = r.classify_outcome(
        m.HandlerOutcome.RETRYABLE, "IO_TRANSIENT", ("IO_TRANSIENT",), (), (), 3, 3
    )
    assert status is m.JobStatus.DEAD_LETTER


def test_classify_outcome_terminal():
    r = _retry_mod()
    m = _models()
    status, code = r.classify_outcome(
        m.HandlerOutcome.TERMINAL_FAILURE, "SCHEMA_INVALID", (), (), ("SCHEMA_INVALID",), 1, 3
    )
    assert status is m.JobStatus.DEAD_LETTER


def test_classify_legacy_blocked_outcome_is_machine_failure():
    r = _retry_mod()
    m = _models()
    status, code = r.classify_outcome(
        m.HandlerOutcome.BLOCKED_HUMAN, "REVIEW_PENDING", (), ("REVIEW_PENDING",), (), 1, 3
    )
    assert status is m.JobStatus.DEAD_LETTER


# --------------------------------------------------------------------------- #
# Worker tests.
# --------------------------------------------------------------------------- #
def test_worker_claims_and_executes_happy_path(tmp_path):
    w = _worker_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_job(s, m, tmp_path)
    reg = r.create_default_registry()
    executor = w.HandlerExecutor()
    executor.register("timer.execute_step", _make_fake_handler(m.HandlerOutcome.SUCCEEDED, result={"ok": True}))
    clock = FixedClock("2026-07-12T10:01:00Z")
    id_gen = SequentialIDGen()
    worker = w.Worker(store, reg, executor, clock=clock, id_gen=id_gen, lease_seconds=60)
    assert worker.process_one() is True
    job = store.get_job("job-auto4-001")
    assert job.status is m.JobStatus.SUCCEEDED


def test_worker_returns_false_when_no_ready_jobs(tmp_path):
    w = _worker_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_job(s, m, tmp_path, status=m.JobStatus.DETECTED)
    reg = r.create_default_registry()
    executor = w.HandlerExecutor()
    clock = FixedClock("2026-07-12T10:01:00Z")
    worker = w.Worker(store, reg, executor, clock=clock)
    assert worker.process_one() is False


def test_worker_retries_on_retryable_error(tmp_path):
    w = _worker_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_job(s, m, tmp_path)
    reg = r.create_default_registry()
    executor = w.HandlerExecutor()
    error = m.HandlerError(code="IO_TRANSIENT", detail="transient failure")
    executor.register("timer.execute_step", _make_fake_handler(
        m.HandlerOutcome.RETRYABLE, error=error
    ))
    clock = FixedClock("2026-07-12T10:01:00Z")
    id_gen = SequentialIDGen()
    worker = w.Worker(store, reg, executor, clock=clock, id_gen=id_gen, lease_seconds=60)
    # First attempt waits until its deterministic retry deadline.
    assert worker.process_one() is True
    job = store.get_job("job-auto4-001")
    assert job.status is m.JobStatus.RETRY_WAIT
    assert job.not_before > "2026-07-12T10:01:00Z"


def test_worker_dead_letters_on_terminal_error(tmp_path):
    w = _worker_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_job(s, m, tmp_path)
    reg = r.create_default_registry()
    executor = w.HandlerExecutor()
    error = m.HandlerError(code="SCHEMA_INVALID", detail="bad schema")
    executor.register("timer.execute_step", _make_fake_handler(
        m.HandlerOutcome.TERMINAL_FAILURE, error=error
    ))
    clock = FixedClock("2026-07-12T10:01:00Z")
    id_gen = SequentialIDGen()
    worker = w.Worker(store, reg, executor, clock=clock, id_gen=id_gen, lease_seconds=60)
    assert worker.process_one() is True
    job = store.get_job("job-auto4-001")
    assert job.status is m.JobStatus.DEAD_LETTER


def test_worker_legacy_review_error_is_machine_failure(tmp_path):
    w = _worker_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_job(s, m, tmp_path)
    reg = r.create_default_registry()
    executor = w.HandlerExecutor()
    error = m.HandlerError(code="REVIEW_PENDING", detail="needs review")
    executor.register("timer.execute_step", _make_fake_handler(
        m.HandlerOutcome.BLOCKED_HUMAN, error=error
    ))
    clock = FixedClock("2026-07-12T10:01:00Z")
    id_gen = SequentialIDGen()
    worker = w.Worker(store, reg, executor, clock=clock, id_gen=id_gen, lease_seconds=60)
    assert worker.process_one() is True
    job = store.get_job("job-auto4-001")
    assert job.status is m.JobStatus.DEAD_LETTER


def test_worker_reaps_expired_leases(tmp_path):
    w = _worker_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_job(s, m, tmp_path)
    reg = r.create_default_registry()
    executor = w.HandlerExecutor()
    executor.register("timer.execute_step", _make_fake_handler(m.HandlerOutcome.SUCCEEDED))
    # First worker claims with short lease.
    clock1 = FixedClock("2026-07-12T10:01:00Z")
    id_gen1 = SequentialIDGen("w1")
    worker1 = w.Worker(store, reg, executor, clock=clock1, id_gen=id_gen1, lease_seconds=1)
    worker1.process_one()
    job = store.get_job("job-auto4-001")
    assert job.status is m.JobStatus.SUCCEEDED
    # For reap test, create a job stuck in RUNNING with an expired lease.
    store.put_event(_make_event(m=m, event_id="evt-reap", subject_id="rev-reap"))
    job2 = _make_job(m=m, job_id="job-reap", job_type="timer.execute_step",
                      subject_id="src-reap", status=m.JobStatus.READY,
                      created_from_event_id="evt-reap")
    store.put_job(job2)
    # Claim through the fenced Store API so this lease belongs to the current
    # runtime generation. A manually constructed Attempt defaults to generation
    # zero and would test generation invalidation instead of lease expiry.
    clock2 = FixedClock("2026-07-12T10:02:00Z")
    id_gen2 = SequentialIDGen("w2")
    worker2 = w.Worker(store, reg, executor, clock=clock2, id_gen=id_gen2, lease_seconds=1)
    gate = store.read_runtime_gate()
    claimed = store.claim_next_ready(
        worker_id="w2", attempt_id="att-reap", lease_token="token-reap",
        now=clock2.now(), lease_until="2026-07-12T10:02:01Z",
        expected_generation=gate.control_generation,
        allowed_job_types=("timer.execute_step",), allowed_job_ids=("job-reap",),
    )
    assert claimed is not None
    assert claimed.attempt.runtime_generation == gate.control_generation
    assert worker2.reap_expired() == 0
    # Now reap with a clock past the lease_until.
    clock3 = FixedClock("2026-07-12T10:05:00Z")
    worker3 = w.Worker(store, reg, executor, clock=clock3, id_gen=SequentialIDGen("w3"), lease_seconds=1)
    reaped = worker3.reap_expired()
    assert reaped == 1
    job2_after = store.get_job("job-reap")
    assert job2_after.status is m.JobStatus.RETRY_WAIT
    attempt_after = store.get_attempt("att-reap")
    assert attempt_after.finished_at == "2026-07-12T10:05:00Z"
    assert attempt_after.error_code == "LEASE_EXPIRED"


def test_worker_handler_exception_dead_letters(tmp_path):
    w = _worker_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_job(s, m, tmp_path)
    reg = r.create_default_registry()
    executor = w.HandlerExecutor()
    def bad_handler(input_data):
        raise RuntimeError("handler crashed")
    executor.register("timer.execute_step", bad_handler)
    clock = FixedClock("2026-07-12T10:01:00Z")
    id_gen = SequentialIDGen()
    worker = w.Worker(store, reg, executor, clock=clock, id_gen=id_gen, lease_seconds=60)
    assert worker.process_one() is True
    job = store.get_job("job-auto4-001")
    assert job.status is m.JobStatus.DEAD_LETTER


def test_worker_uses_only_atomic_store_operations_for_claim_and_finish(
    tmp_path, monkeypatch
):
    w = _worker_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_job(s, m, tmp_path)
    executor = w.HandlerExecutor()
    executor.register(
        "timer.execute_step",
        _make_fake_handler(m.HandlerOutcome.SUCCEEDED, result={"ok": True}),
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Worker must not compose legacy CRUD operations")

    for name in ("list_jobs", "transition_job", "put_attempt", "put_outbox_entry"):
        monkeypatch.setattr(store, name, forbidden)

    worker = w.Worker(
        store,
        r.create_default_registry(),
        executor,
        clock=FixedClock("2026-07-12T10:01:00Z"),
        id_gen=SequentialIDGen(),
        lease_seconds=60,
    )
    assert worker.process_one() is True


def test_worker_fails_closed_while_runtime_gate_is_paused(tmp_path):
    w = _worker_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_job(s, m, tmp_path)
    store.set_runtime_gate(
        m.RuntimeState.PAUSED, updated_at="2026-07-12T10:00:45Z"
    )
    executor = w.HandlerExecutor()
    executor.register(
        "timer.execute_step", _make_fake_handler(m.HandlerOutcome.SUCCEEDED)
    )
    worker = w.Worker(
        store,
        r.create_default_registry(),
        executor,
        clock=FixedClock("2026-07-12T10:01:00Z"),
        id_gen=SequentialIDGen(),
    )

    assert worker.process_one() is False
    assert store.get_job("job-auto4-001").status is m.JobStatus.READY
    assert store.list_attempts("job-auto4-001") == ()
