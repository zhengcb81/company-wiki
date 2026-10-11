"""Scoped read uses actual outbox/effect foreign keys before applying LIMIT."""
from dataclasses import replace
import hashlib
import sqlite3

import pytest

from company_wiki.automation.models import (
    Effect, EffectStatus, Event, Job, JobStatus, RiskClass, make_effect_key, make_job_key,
)
from company_wiki.automation.store import AutomationStore

T0, T1 = "2026-10-11T00:00:00Z", "2026-10-11T00:01:00Z"
SHA = hashlib.sha256(b"outbox read fixture").hexdigest()


def _seed(store, name, *, status, due):
    event = Event("event-" + name, "source.revision_registered", "source_revision", name, SHA,
        "{}", "fixture", T0, T0)
    store.put_event(event)
    job = Job("job-" + name, make_job_key("source.narrative_verify", "source_revision", name, SHA, "fixture", "1.0.0"),
        "source.narrative_verify", "source_revision", name, SHA, "fixture", "1.0.0", RiskClass.LOW,
        JobStatus.VERIFYING, 0, T0, 3, event.event_id, T0, T0, None, None)
    store.put_job(job)
    effect = Effect("effect-" + name, make_effect_key("artifact_write", name, SHA, "1.0.0"), job.job_id,
        "artifact_write", name, None, SHA, None, EffectStatus.PENDING, T0, None)
    store.put_effect(effect)
    # Opaque identity deliberately has no derivable relationship to job/effect.
    store.put_outbox_entry("opaque-" + name, effect.effect_id, "{}", status, due)
    return job, effect


def _dump(store):
    connection = sqlite3.connect(store.db_path)
    try:
        return tuple(connection.iterdump())
    finally:
        connection.close()


@pytest.mark.parametrize("status", [None, "pending", "leased", "failed", "delivered"])
def test_outbox_read_scope_filters_real_fk_before_limit_without_writing(tmp_path, status):
    store = AutomationStore(tmp_path / "automation.db")
    foreign, _ = _seed(store, "foreign", status="pending" if status is None else status, due=T0)
    target, effect = _seed(store, "target", status="pending" if status is None else status, due=T1)
    before = _dump(store)
    assert store.list_outbox_entries(status=status, limit=1)[0]["outbox_id"] == "opaque-foreign"
    rows = store.list_outbox_entries(status=status, limit=1, allowed_job_ids=(target.job_id,))
    assert len(rows) == 1 and rows[0]["outbox_id"] == "opaque-target"
    assert rows[0]["effect_id"] == effect.effect_id
    assert store.list_outbox_entries(status=status, limit=1, allowed_job_ids=()) == ()
    assert store.list_outbox_entries(status=status, allowed_job_ids=("missing",)) == ()
    assert store.list_outbox_entries(status=status, allowed_job_ids=None) == store.list_outbox_entries(status=status)
    assert len(store.list_outbox_entries(status=status, allowed_job_ids=(target.job_id, foreign.job_id))) == 2
    other = "delivered" if status != "delivered" else "pending"
    assert store.list_outbox_entries(status=other, allowed_job_ids=(target.job_id,)) == ()
    assert _dump(store) == before


def test_multiple_effects_same_job_keep_full_opaque_rows_and_delivered_state(tmp_path):
    store = AutomationStore(tmp_path / "automation.db")
    target, effect = _seed(store, "target", status="pending", due=T1)
    second = replace(effect, effect_id="separate-effect", effect_key=make_effect_key("artifact_write", "second", SHA, "1.0.0"), target="second")
    store.put_effect(second)
    store.put_outbox_entry("another-unrelated-id", second.effect_id, "{}", "delivered", T0)
    before = _dump(store)
    old_rows = store.list_outbox_entries()
    assert store.list_outbox_entries(allowed_job_ids=(target.job_id,)) == old_rows
    rows = store.list_outbox_entries(status="delivered", allowed_job_ids=(target.job_id,))
    assert len(rows) == 1 and rows[0]["effect_id"] == second.effect_id
    assert _dump(store) == before


@pytest.mark.parametrize("scope", [["job"], ("",), (1,) ], ids=["list", "blank", "non-string"])
def test_outbox_read_scope_rejects_invalid_ids_without_writes(tmp_path, scope):
    store = AutomationStore(tmp_path / "automation.db")
    before = _dump(store)
    with pytest.raises((TypeError, ValueError)):
        store.list_outbox_entries(allowed_job_ids=scope)
    assert _dump(store) == before
