"""AUTO-5 controller/event_sources/plan CLI contract tests.

Each test asserts the production module paths exist before importing them.
All tests use fixed values and tmp_path; no network, LLM or production data.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path



ROOT = Path(__file__).resolve().parents[2]
CONTROLLER_PATH = ROOT / "src" / "company_wiki" / "automation" / "controller.py"
EVENT_SOURCES_PATH = ROOT / "src" / "company_wiki" / "automation" / "event_sources.py"
CLI_PATH = ROOT / "src" / "company_wiki" / "automation" / "cli.py"


def _controller_mod():
    assert CONTROLLER_PATH.is_file()
    from company_wiki.automation import controller
    return controller


def _event_sources_mod():
    assert EVENT_SOURCES_PATH.is_file()
    from company_wiki.automation import event_sources
    return event_sources


def _store_mod():
    from company_wiki.automation import store
    return store


def _registry_mod():
    from company_wiki.automation import registry
    return registry


def _policy_mod():
    from company_wiki.automation import policy
    return policy


def _models():
    from company_wiki.automation import models
    return models


INPUT_HASH = hashlib.sha256(b"auto-5-input").hexdigest()


def _make_event(m=None, **overrides):
    m = m or _models()
    defaults = dict(
        event_id="evt-auto5-001",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id="rev-auto5-001",
        input_hash=INPUT_HASH,
        payload_json=m.canonical_json({"key": "value"}),
        policy_version="v1",
        occurred_at="2026-07-12T11:00:00Z",
        observed_at="2026-07-12T11:00:00Z",
    )
    defaults.update(overrides)
    return m.Event(**defaults)


def _setup_store_with_events(s, m, tmp_path, events):
    store = s.AutomationStore(tmp_path / "automation.db")
    for evt in events:
        store.put_event(evt)
    return store


def run_cli(*args):
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["MINIMAX_API_KEY"] = "must-not-be-read"
    env["MIMO_API_KEY"] = "must-not-be-read"
    return subprocess.run(
        [sys.executable, "-m", "company_wiki.automation.cli", *args],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )


# --------------------------------------------------------------------------- #
# Event sources tests.
# --------------------------------------------------------------------------- #
def test_event_source_reads_all_events(tmp_path):
    es = _event_sources_mod()
    s = _store_mod()
    m = _models()
    store = _setup_store_with_events(s, m, tmp_path, [
        _make_event(m=m),
        _make_event(m=m, event_id="evt-2", subject_id="rev-2"),
    ])
    source = es.EventSource(store)
    events = source.get_all_events()
    assert len(events) == 2


def test_event_source_filters_by_type(tmp_path):
    es = _event_sources_mod()
    s = _store_mod()
    m = _models()
    store = _setup_store_with_events(s, m, tmp_path, [
        _make_event(m=m, event_type="source.revision_registered"),
        _make_event(m=m, event_id="evt-2", event_type="timer.due",
                    subject_id="timer-1"),
    ])
    source = es.EventSource(store)
    source_events = source.get_events_by_type("source.revision_registered")
    assert len(source_events) == 1
    assert source_events[0].event_type == "source.revision_registered"


# --------------------------------------------------------------------------- #
# Controller observe tests.
# --------------------------------------------------------------------------- #
def test_observe_returns_planned_dags_no_side_effects(tmp_path):
    c = _controller_mod()
    s = _store_mod()
    r = _registry_mod()
    p = _policy_mod()
    m = _models()
    store = _setup_store_with_events(s, m, tmp_path, [_make_event(m=m)])
    reg = r.create_default_registry()
    config = p.PolicyConfig(allow_llm=True)
    ctrl = c.Controller(store, reg, config)
    result = ctrl.observe()
    assert result.events_processed == 1
    assert len(result.planned_dags) == 1
    # No jobs created.
    assert store.list_jobs() == ()
    assert result.jobs_would_create > 0


def test_observe_deterministic_across_restarts(tmp_path):
    """The same store state produces the same observe result across restarts."""
    c = _controller_mod()
    s = _store_mod()
    r = _registry_mod()
    p = _policy_mod()
    m = _models()
    store = _setup_store_with_events(s, m, tmp_path, [_make_event(m=m)])
    reg = r.create_default_registry()
    config = p.PolicyConfig(allow_llm=True)
    results = []
    for _ in range(3):
        ctrl = c.Controller(store, reg, config)
        results.append(ctrl.observe())
    # All three results should be identical.
    assert results[0].events_processed == results[1].events_processed == results[2].events_processed
    assert results[0].jobs_would_create == results[1].jobs_would_create == results[2].jobs_would_create
    assert len(results[0].planned_dags) == len(results[1].planned_dags) == len(results[2].planned_dags)


def test_observe_handles_unknown_events_gracefully(tmp_path):
    c = _controller_mod()
    s = _store_mod()
    r = _registry_mod()
    m = _models()
    store = _setup_store_with_events(s, m, tmp_path, [
        _make_event(m=m, event_type="unknown.event"),
    ])
    reg = r.create_default_registry()
    ctrl = c.Controller(store, reg)
    result = ctrl.observe()
    # Unknown events are skipped (not planned).
    assert result.events_processed == 1
    assert len(result.planned_dags) == 0


# --------------------------------------------------------------------------- #
# Controller shadow tests.
# --------------------------------------------------------------------------- #
def test_shadow_creates_jobs_no_handler_execution(tmp_path):
    c = _controller_mod()
    s = _store_mod()
    r = _registry_mod()
    p = _policy_mod()
    m = _models()
    store = _setup_store_with_events(s, m, tmp_path, [_make_event(m=m)])
    reg = r.create_default_registry()
    config = p.PolicyConfig(allow_llm=True)
    ctrl = c.Controller(store, reg, config)
    result = ctrl.shadow()
    assert result.events_processed == 1
    assert result.jobs_created > 0
    # Jobs were created in the store.
    jobs = store.list_jobs()
    assert len(jobs) > 0
    # All jobs are in DETECTED status (not executed).
    for job in jobs:
        assert job.status is m.JobStatus.DETECTED


def test_shadow_idempotent_on_duplicate_events(tmp_path):
    c = _controller_mod()
    s = _store_mod()
    r = _registry_mod()
    p = _policy_mod()
    m = _models()
    store = _setup_store_with_events(s, m, tmp_path, [_make_event(m=m)])
    reg = r.create_default_registry()
    config = p.PolicyConfig(allow_llm=True)
    ctrl = c.Controller(store, reg, config)
    result1 = ctrl.shadow()
    result2 = ctrl.shadow()
    # Second run should not create new jobs (already exist).
    assert result1.jobs_created > 0
    assert result2.jobs_created == 0
    assert result2.jobs_already_existed > 0


# --------------------------------------------------------------------------- #
# CLI plan command tests.
# --------------------------------------------------------------------------- #
def test_plan_cli_requires_db_argument():
    result = run_cli("plan")
    assert result.returncode == 2  # argparse error


def test_plan_cli_outputs_planned_dag(tmp_path):
    s = _store_mod()
    m = _models()
    _setup_store_with_events(s, m, tmp_path, [_make_event(m=m)])
    db_path = tmp_path / "automation.db"
    result = run_cli("plan", "--db", str(db_path), "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["events_planned"] == 1
    assert len(data["dags"]) == 1


def test_plan_cli_with_event_id(tmp_path):
    s = _store_mod()
    m = _models()
    _setup_store_with_events(s, m, tmp_path, [_make_event(m=m)])
    db_path = tmp_path / "automation.db"
    result = run_cli("plan", "--db", str(db_path), "--event-id", "evt-auto5-001", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["events_planned"] == 1


def test_plan_cli_nonexistent_event(tmp_path):
    s = _store_mod()
    m = _models()
    _setup_store_with_events(s, m, tmp_path, [_make_event(m=m)])
    db_path = tmp_path / "automation.db"
    result = run_cli("plan", "--db", str(db_path), "--event-id", "nonexistent", "--json")
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert "error" in data


def test_plan_cli_no_side_effects(tmp_path):
    """Plan CLI should not create jobs or modify the store."""
    s = _store_mod()
    m = _models()
    store = _setup_store_with_events(s, m, tmp_path, [_make_event(m=m)])
    jobs_before = len(store.list_jobs())
    db_path = tmp_path / "automation.db"
    result = run_cli("plan", "--db", str(db_path), "--json")
    assert result.returncode == 0
    jobs_after = len(store.list_jobs())
    assert jobs_before == jobs_after
