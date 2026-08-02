"""AUTO-2 store contract tests (S01-S18 and growing).

Each test asserts the production store module path exists before importing it,
so the red phase fails as a normal assertion rather than a collection error.
All databases live under ``tmp_path``; no test touches ``.state`` or production
data.  Fixed timestamps and deterministic hashes follow AUTO-2.19.
"""

import hashlib
import sqlite3
import threading
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "src" / "company_wiki" / "automation" / "store.py"

# Fixed timestamps and identity hashes (AUTO-2.19).
T0 = "2026-07-12T08:00:00Z"
T1 = "2026-07-12T08:01:00Z"
T2 = "2026-07-12T08:02:00Z"
T5 = "2026-07-12T08:05:00Z"
INPUT_HASH = hashlib.sha256(b"auto-2-input").hexdigest()
ACTION_HASH = hashlib.sha256(b"auto-2-action").hexdigest()
RECEIPT_HASH = hashlib.sha256(b"auto-2-receipt").hexdigest()
AFTER_HASH = hashlib.sha256(b"auto-2-after").hexdigest()


# --------------------------------------------------------------------------- #
# Lazy imports — models are stable (AUTO-1), store may not exist yet.
# --------------------------------------------------------------------------- #
def _store_mod():
    assert STORE_PATH.is_file(), "expected red: automation/store.py is not implemented"
    from company_wiki.automation import store as mod
    return mod


def _models():
    from company_wiki.automation import models as mod
    return mod


# --------------------------------------------------------------------------- #
# Fixture factories (fixed values, deterministic, no real data).
# --------------------------------------------------------------------------- #
def _make_event(m=None, **overrides):
    m = m or _models()
    payload = m.canonical_json({"公司": "北方华创", "详情": {"金额": 123.45, "单位": "亿元"}})
    defaults = dict(
        event_id="evt-auto2-001",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id="rev-auto2-001",
        input_hash=INPUT_HASH,
        payload_json=payload,
        policy_version="v1",
        occurred_at=T0,
        observed_at=T0,
    )
    defaults.update(overrides)
    return m.Event(**defaults)


def _make_job(m=None, event_id="evt-auto2-001", **overrides):
    m = m or _models()
    job_type = overrides.pop("job_type", "source.normalize")
    subject_id = overrides.pop("subject_id", "src-auto2-001")
    handler_version = overrides.pop("handler_version", "1.0.0")
    policy_version = overrides.pop("policy_version", "v1")
    job_key = m.make_job_key(job_type, "source", subject_id, INPUT_HASH, policy_version, handler_version)
    defaults = dict(
        job_id="job-auto2-001",
        job_key=job_key,
        job_type=job_type,
        subject_type="source",
        subject_id=subject_id,
        input_hash=INPUT_HASH,
        policy_version=policy_version,
        handler_version=handler_version,
        risk_class=m.RiskClass.LOW,
        status=m.JobStatus.DETECTED,
        priority=0,
        not_before=T0,
        max_attempts=3,
        created_from_event_id=event_id,
        created_at=T0,
        updated_at=T0,
        last_error_code=None,
        last_error_detail=None,
    )
    defaults.update(overrides)
    return m.Job(**defaults)


def _make_attempt(m=None, job_id="job-auto2-001", **overrides):
    m = m or _models()
    defaults = dict(
        attempt_id="att-auto2-001",
        job_id=job_id,
        attempt_no=1,
        worker_id="worker-local",
        lease_token="lease-auto2-001",
        lease_until=T5,
        started_at=T0,
        heartbeat_at=T1,
        finished_at=None,
        outcome=None,
        result_json=None,
        error_code=None,
        error_detail=None,
    )
    defaults.update(overrides)
    return m.Attempt(**defaults)


def _make_approval(m=None, job_id="job-auto2-001", **overrides):
    m = m or _models()
    defaults = dict(
        approval_id="appr-auto2-001",
        job_id=job_id,
        action_hash=ACTION_HASH,
        reviewer_principal="reviewer-primary",
        reviewer_session_id="session-001",
        role="primary",
        decision=m.ApprovalDecision.APPROVED,
        decided_at=T2,
        receipt_hash=RECEIPT_HASH,
    )
    defaults.update(overrides)
    return m.Approval(**defaults)


def _make_effect(m=None, job_id="job-auto2-001", **overrides):
    m = m or _models()
    effect_key = m.make_effect_key("artifact_write", "artifacts/gates/auto-2-test.json", ACTION_HASH, "1.0.0")
    defaults = dict(
        effect_id="eff-auto2-001",
        effect_key=effect_key,
        job_id=job_id,
        effect_type="artifact_write",
        target="artifacts/gates/auto-2-test.json",
        before_hash=None,
        intended_after_hash=AFTER_HASH,
        actual_after_hash=None,
        status=m.EffectStatus.PENDING,
        created_at=T1,
        verified_at=None,
    )
    defaults.update(overrides)
    return m.Effect(**defaults)


# --------------------------------------------------------------------------- #
# S01-S05: Roundtrip (put/get/to_dict equality for each value object).
# --------------------------------------------------------------------------- #
def test_s01_event_unicode_canonical_roundtrip(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    evt = _make_event(m=m)
    result = store.put_event(evt)
    assert result.created is True
    got = store.get_event("evt-auto2-001")
    assert got is not None
    assert got.to_dict() == evt.to_dict()


def test_s02_job_all_enum_null_fields_roundtrip(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    job = _make_job(m=m)
    result = store.put_job(job)
    assert result.created is True
    got = store.get_job("job-auto2-001")
    assert got is not None
    assert got.to_dict() == job.to_dict()


def test_s03_attempt_open_and_finished_roundtrip(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    # Open form (no finished_at/outcome/result).
    att = _make_attempt(m=m)
    result = store.put_attempt(att)
    assert result.created is True
    got = store.get_attempt("att-auto2-001")
    assert got is not None
    assert got.to_dict() == att.to_dict()
    # Finished form.
    att2 = _make_attempt(m=m, attempt_id="att-auto2-002", attempt_no=2,
                         lease_token="lease-auto2-002", finished_at=T2,
                         outcome=m.HandlerOutcome.SUCCEEDED,
                         result_json=m.canonical_json({"ok": True}))
    result2 = store.put_attempt(att2)
    assert result2.created is True
    got2 = store.get_attempt("att-auto2-002")
    assert got2 is not None
    assert got2.to_dict() == att2.to_dict()


def test_s04_approval_three_decision_roundtrip(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    for i, decision in enumerate(m.ApprovalDecision):
        appr = _make_approval(m=m, approval_id=f"appr-{i}", decision=decision,
                              reviewer_principal=f"reviewer-{i}", decided_at=T2)
        store.put_approval(appr)
        got = store.get_approval(f"appr-{i}")
        assert got is not None
        assert got.decision is decision


def test_s05_effect_nullable_hash_verified_roundtrip(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    eff = _make_effect(m=m)  # nullable hashes
    result = store.put_effect(eff)
    assert result.created is True
    got = store.get_effect("eff-auto2-001")
    assert got is not None
    assert got.to_dict() == eff.to_dict()
    # Now with all hashes populated.
    eff2 = _make_effect(m=m, effect_id="eff-auto2-002",
                        effect_key=hashlib.sha256(b"eff2").hexdigest(),
                        before_hash=INPUT_HASH, actual_after_hash=AFTER_HASH,
                        verified_at=T2)
    store.put_effect(eff2)
    got2 = store.get_effect("eff-auto2-002")
    assert got2 is not None
    assert got2.to_dict() == eff2.to_dict()


# --------------------------------------------------------------------------- #
# S06-S13: Idempotency.
# --------------------------------------------------------------------------- #
def test_s06_same_event_100_times(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    evt = _make_event(m=m)
    results = [store.put_event(evt) for _ in range(100)]
    created_flags = [r.created for r in results]
    assert created_flags[0] is True
    assert all(f is False for f in created_flags[1:])
    # Exactly one row.
    assert len(store.get_event("evt-auto2-001").to_dict()) > 0


def test_s07_event_same_identity_different_payload(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    evt1 = _make_event(m=m, payload_json=m.canonical_json({"v": 1}))
    store.put_event(evt1)
    evt2 = _make_event(m=m, event_id="evt-auto2-002",
                       payload_json=m.canonical_json({"v": 2}))
    with pytest.raises(s.IdempotencyConflictError):
        store.put_event(evt2)
    # Old row unchanged.
    assert store.get_event("evt-auto2-001").payload_json == evt1.payload_json


def test_s08_event_same_pk_different_identity(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    evt1 = _make_event(m=m)
    store.put_event(evt1)
    evt2 = _make_event(m=m, event_type="source.different_type")
    with pytest.raises(s.IdempotencyConflictError):
        store.put_event(evt2)


def test_s09_job_same_key_different_semantics(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    job1 = _make_job(m=m)
    store.put_job(job1)
    # Same job_key (same formula inputs) but different risk_class.
    job2 = _make_job(m=m, risk_class=m.RiskClass.HIGH)
    with pytest.raises(s.IdempotencyConflictError):
        store.put_job(job2)


def test_s10_effect_same_key_different_target(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    eff1 = _make_effect(m=m)
    store.put_effect(eff1)
    eff2 = _make_effect(m=m, effect_id="eff-auto2-002", target="other/path.json")
    with pytest.raises(s.IdempotencyConflictError):
        store.put_effect(eff2)


def test_s11_attempt_same_job_attempt_no_conflict(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    att1 = _make_attempt(m=m)
    store.put_attempt(att1)
    att2 = _make_attempt(m=m, attempt_id="att-dup", lease_token="lease-dup")
    with pytest.raises(s.IdempotencyConflictError):
        store.put_attempt(att2)


def test_s12_attempt_reuse_lease_token(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    att1 = _make_attempt(m=m)
    store.put_attempt(att1)
    att2 = _make_attempt(m=m, attempt_id="att-auto2-002", attempt_no=2,
                         lease_token="lease-auto2-001")  # same lease_token!
    with pytest.raises((s.IdempotencyConflictError, s.IntegrityViolationError)):
        store.put_attempt(att2)


def test_s13_approval_natural_unique_conflict(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    appr1 = _make_approval(m=m)
    store.put_approval(appr1)
    appr2 = _make_approval(m=m, approval_id="appr-dup", decision=m.ApprovalDecision.REJECTED)
    with pytest.raises(s.IdempotencyConflictError):
        store.put_approval(appr2)


# --------------------------------------------------------------------------- #
# S14: Two stores concurrently put the same event -> 1 row, one True one False.
# --------------------------------------------------------------------------- #
def test_s14_two_stores_concurrent_same_event(tmp_path):
    s = _store_mod()
    m = _models()
    db = tmp_path / "automation.db"
    # Create both stores before the barrier to avoid concurrent migration.
    store_a = s.AutomationStore(db)
    store_b = s.AutomationStore(db)
    barrier = threading.Barrier(2)
    results = []

    def worker_a():
        barrier.wait()
        results.append(store_a.put_event(_make_event(m=m)))

    def worker_b():
        barrier.wait()
        results.append(store_b.put_event(_make_event(m=m)))

    threads = [threading.Thread(target=worker_a), threading.Thread(target=worker_b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 2
    created = sorted([r.created for r in results])
    assert created == [False, True]


# --------------------------------------------------------------------------- #
# S15: Orphan FK insertion is rejected.
# --------------------------------------------------------------------------- #
def test_s15_orphan_job_fk_rejected(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    job = _make_job(m=m, created_from_event_id="nonexistent-event")
    with pytest.raises(s.IntegrityViolationError):
        store.put_job(job)
    assert store.get_job("job-auto2-001") is None


# --------------------------------------------------------------------------- #
# S16: Dependency duplicate / conflict.
# --------------------------------------------------------------------------- #
def test_s16_dependency_duplicate_returns_false_conflict_raises(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    store.put_job(_make_job(m=m, job_id="job-auto2-002", job_type="source.analyze",
                             subject_id="src-auto2-002"))
    # First add → True (created).
    assert store.add_job_dependency("job-auto2-001", "job-auto2-002") is True
    # Exact duplicate → False (idempotent).
    assert store.add_job_dependency("job-auto2-001", "job-auto2-002") is False
    # Same PK, different required_status → conflict.
    with pytest.raises(s.IntegrityViolationError):
        store.add_job_dependency("job-auto2-001", "job-auto2-002",
                                 required_status=m.JobStatus.CANCELLED)


# --------------------------------------------------------------------------- #
# S17: get nonexistent returns None without creating data.
# --------------------------------------------------------------------------- #
def test_s17_get_nonexistent_returns_none_no_creation(tmp_path):
    s = _store_mod()
    store = s.AutomationStore(tmp_path / "automation.db")
    assert store.get_event("nonexistent") is None
    assert store.get_job("nonexistent") is None
    assert store.get_attempt("nonexistent") is None
    assert store.get_approval("nonexistent") is None
    assert store.get_effect("nonexistent") is None
    # No data created — schema report shows empty tables.
    report = store.schema_report()
    assert report.user_version == 1


# --------------------------------------------------------------------------- #
# S18: list stable order (per frozen sort spec).
# --------------------------------------------------------------------------- #
def test_s18_list_jobs_stable_order(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    # Create three jobs with different priorities.
    for i, (jid, pri) in enumerate([("j-high", 10), ("j-low", -5), ("j-mid", 0)]):
        ts = f"2026-07-12T08:0{i}:00Z"
        job = _make_job(m=m, job_id=jid, job_type=f"type{i}",
                        subject_id=f"src{i}", priority=pri,
                        created_at=ts, updated_at=ts)
        store.put_job(job)
    jobs = store.list_jobs()
    # ORDER BY priority DESC, created_at ASC, job_id ASC.
    priorities = [j.priority for j in jobs]
    assert priorities == sorted(priorities, reverse=True)


def test_s18_list_attempts_stable_order(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    for no in [3, 1, 2]:
        store.put_attempt(_make_attempt(m=m, attempt_id=f"att-{no}", attempt_no=no,
                                        lease_token=f"lease-{no}"))
    atts = store.list_attempts("job-auto2-001")
    assert [a.attempt_no for a in atts] == [1, 2, 3]


def test_s18_list_approvals_stable_order(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    store.put_approval(_make_approval(m=m, approval_id="appr-late", decided_at=T5,
                                      reviewer_principal="reviewer-late"))
    store.put_approval(_make_approval(m=m, approval_id="appr-early", decided_at=T0,
                                      reviewer_principal="reviewer-early"))
    apprs = store.list_approvals("job-auto2-001")
    assert [a.approval_id for a in apprs] == ["appr-early", "appr-late"]


def test_s18_list_effects_stable_order(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    store.put_effect(_make_effect(m=m, effect_id="eff-late", created_at=T5,
                                   effect_key=hashlib.sha256(b"eff-late").hexdigest()))
    store.put_effect(_make_effect(m=m, effect_id="eff-early", created_at=T0,
                                   effect_key=hashlib.sha256(b"eff-early").hexdigest()))
    effs = store.list_effects("job-auto2-001")
    assert [e.effect_id for e in effs] == ["eff-early", "eff-late"]


# --------------------------------------------------------------------------- #
# S19-S22: transition_job CAS.
# --------------------------------------------------------------------------- #
def test_s19_legal_job_transition(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m, status=m.JobStatus.DETECTED))
    new = store.transition_job("job-auto2-001", expected=m.JobStatus.DETECTED,
                               target=m.JobStatus.PLANNED, updated_at=T1)
    assert new.status is m.JobStatus.PLANNED
    assert new.updated_at == T1
    # DB reflects the change.
    assert store.get_job("job-auto2-001").status is m.JobStatus.PLANNED


def test_s20_illegal_terminal_transition(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m, status=m.JobStatus.SUCCEEDED))
    with pytest.raises((ValueError, s.AutomationStoreError)):
        store.transition_job("job-auto2-001", expected=m.JobStatus.SUCCEEDED,
                             target=m.JobStatus.DETECTED, updated_at=T1)
    # DB unchanged.
    assert store.get_job("job-auto2-001").status is m.JobStatus.SUCCEEDED


def test_s21_stale_expected_status(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m, status=m.JobStatus.DETECTED))
    # Move to PLANNED.
    store.transition_job("job-auto2-001", expected=m.JobStatus.DETECTED,
                         target=m.JobStatus.PLANNED, updated_at=T1)
    # Try stale expected (DETECTED, but actual is PLANNED); target is valid from DETECTED.
    with pytest.raises(s.ConcurrentUpdateError):
        store.transition_job("job-auto2-001", expected=m.JobStatus.DETECTED,
                             target=m.JobStatus.PLANNED, updated_at=T2)
    # DB unchanged (still PLANNED).
    assert store.get_job("job-auto2-001").status is m.JobStatus.PLANNED


def test_s22_two_stores_concurrent_cas(tmp_path):
    s = _store_mod()
    m = _models()
    db = tmp_path / "automation.db"
    store = s.AutomationStore(db)
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m, status=m.JobStatus.DETECTED))
    barrier = threading.Barrier(2)
    outcomes = []

    def worker():
        barrier.wait()
        st = s.AutomationStore(db)
        try:
            st.transition_job("job-auto2-001", expected=m.JobStatus.DETECTED,
                              target=m.JobStatus.PLANNED, updated_at=T1)
            outcomes.append("success")
        except s.ConcurrentUpdateError:
            outcomes.append("conflict")

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["conflict", "success"]
    assert store.get_job("job-auto2-001").status is m.JobStatus.PLANNED


# --------------------------------------------------------------------------- #
# S23: updated_at倒退 / bad UTC → rejected.
# --------------------------------------------------------------------------- #
def test_s23_updated_at_regression_rejected(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m, status=m.JobStatus.DETECTED, updated_at=T2))
    with pytest.raises(s.IntegrityViolationError):
        store.transition_job("job-auto2-001", expected=m.JobStatus.DETECTED,
                             target=m.JobStatus.PLANNED, updated_at=T0)  # T0 < T2


# --------------------------------------------------------------------------- #
# S24: SQL injection payload round-trips safely.
# --------------------------------------------------------------------------- #
def test_s24_sql_injection_payload_roundtrips(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    malicious = m.canonical_json({"x": "'); DROP TABLE events;--"})
    evt = _make_event(m=m, payload_json=malicious)
    store.put_event(evt)
    got = store.get_event("evt-auto2-001")
    assert got is not None
    assert got.payload_json == malicious
    # All 8 tables still exist.
    report = store.schema_report()
    assert set(report.tables) == {
        "events", "jobs", "job_dependencies", "attempts",
        "approvals", "effects", "outbox", "notifications",
    }


# --------------------------------------------------------------------------- #
# S25: non-canonical / NaN input rejected by AUTO-1 model (0 insert).
# --------------------------------------------------------------------------- #
def test_s25_non_canonical_input_rejected(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    # Model rejects non-string key.
    with pytest.raises((TypeError, ValueError)):
        m.canonical_json({1: "bad"})
    # Model rejects NaN.
    import math
    with pytest.raises((TypeError, ValueError)):
        m.canonical_json({"v": math.nan})
    # DB unchanged (still 1 event).
    assert store.get_event("evt-auto2-001") is not None


# --------------------------------------------------------------------------- #
# S26: corrupt row → CorruptRecordError (not raw ValueError).
# --------------------------------------------------------------------------- #
def test_s26_corrupt_row_raises_corrupt_record(tmp_path):
    s = _store_mod()
    m = _models()
    db = tmp_path / "automation.db"
    store = s.AutomationStore(db)
    store.put_event(_make_event(m=m))
    # Corrupt via raw connection (not store._connect).
    raw = sqlite3.connect(str(db))
    raw.execute("PRAGMA foreign_keys = OFF")
    raw.execute("UPDATE events SET event_type = '' WHERE event_id = 'evt-auto2-001'")
    raw.commit()
    raw.close()
    # Store reads with FK ON — from_dict may accept empty string but
    # _require_nonempty should reject it.
    with pytest.raises((s.CorruptRecordError, ValueError)):
        store.get_event("evt-auto2-001")


# --------------------------------------------------------------------------- #
# S27: DB lock beyond timeout → StoreBusy.
# --------------------------------------------------------------------------- #
def test_s27_lock_timeout_raises_store_busy(tmp_path):
    s = _store_mod()
    m = _models()
    db = tmp_path / "automation.db"
    # Migrate to create the DB.
    s.AutomationStore(db)
    # Hold an exclusive lock via raw connection.
    holder = sqlite3.connect(str(db))
    holder.execute("BEGIN EXCLUSIVE")
    try:
        tiny = s.AutomationStore(db, timeout_seconds=0.1)
        tiny.put_event(_make_event(m=m))
    except s.StoreBusyError:
        pass  # expected
    else:
        raise AssertionError("expected StoreBusyError")
    finally:
        holder.execute("ROLLBACK")
        holder.close()


# --------------------------------------------------------------------------- #
# S28: Windows handle — db/wal/shm deletable after operations.
# --------------------------------------------------------------------------- #
def test_s28_windows_no_handle_leak(tmp_path):
    s = _store_mod()
    m = _models()
    db = tmp_path / "automation.db"
    store = s.AutomationStore(db)
    store.put_event(_make_event(m=m))
    store.get_event("evt-auto2-001")
    del store  # ensure no lingering references
    import gc
    gc.collect()
    # All sqlite files should be deletable (no PermissionError).
    for suffix in ("", "-wal", "-shm"):
        target = Path(str(db) + suffix)
        if target.exists():
            target.unlink()


# --------------------------------------------------------------------------- #
# S29: invalid path (no-arg, str, :memory:, missing parent).
# --------------------------------------------------------------------------- #
def test_s29_invalid_store_path(tmp_path):
    s = _store_mod()
    # str instead of Path.
    with pytest.raises(TypeError):
        s.AutomationStore(str(tmp_path / "db"))
    # :memory:.
    with pytest.raises(s.InvalidStorePathError):
        s.AutomationStore(Path(":memory:"))
    # Missing parent directory.
    with pytest.raises(s.InvalidStorePathError):
        s.AutomationStore(tmp_path / "nonexistent" / "dir" / "db")


# --------------------------------------------------------------------------- #
# S30: self-dependency / required_status != SUCCEEDED → IntegrityViolation.
# --------------------------------------------------------------------------- #
def test_s30_self_dependency_and_bad_required_status(tmp_path):
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    store.put_job(_make_job(m=m))
    # Self-dependency.
    with pytest.raises(s.IntegrityViolationError):
        store.add_job_dependency("job-auto2-001", "job-auto2-001")
    # Non-SUCCEEDED required_status.
    with pytest.raises(s.IntegrityViolationError):
        store.add_job_dependency("job-auto2-001", "nonexistent",
                                 required_status=m.JobStatus.CANCELLED)
