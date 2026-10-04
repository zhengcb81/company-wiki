"""Retired AUTO human approvals stay inert while their historic rows survive."""

import sqlite3
import hashlib

from company_wiki import automation
from company_wiki.automation import models
from company_wiki.automation.store import AutomationStore


def test_approval_models_and_store_crud_are_not_public():
    assert "Approval" not in automation.__all__
    assert "ApprovalDecision" not in automation.__all__
    assert not hasattr(automation, "Approval")
    assert not hasattr(automation, "ApprovalDecision")
    assert not hasattr(models, "Approval")
    assert not hasattr(models, "ApprovalDecision")
    assert not hasattr(AutomationStore, "put_approval")
    assert not hasattr(AutomationStore, "get_approval")
    assert not hasattr(AutomationStore, "list_approvals")


def test_opening_store_preserves_historical_approval_rows(tmp_path):
    db = tmp_path / "automation.db"
    store = AutomationStore(db)
    digest = hashlib.sha256(b"legacy-approval-fixture").hexdigest()
    event = models.Event(
        event_id="historic-event-1",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id="historic-source-1",
        input_hash=digest,
        payload_json=models.canonical_json({"source": "historic-source-1"}),
        policy_version="v1",
        occurred_at="2026-09-01T00:00:00Z",
        observed_at="2026-09-01T00:00:00Z",
    )
    store.put_event(event)
    store.put_job(models.Job(
        job_id="historic-job-1",
        job_key=models.make_job_key(
            "source.narrative_select", "source", "historic-source-1", digest,
            "v1", "1.0.0",
        ),
        job_type="source.narrative_select",
        subject_type="source",
        subject_id="historic-source-1",
        input_hash=digest,
        policy_version="v1",
        handler_version="1.0.0",
        risk_class=models.RiskClass.LOW,
        status=models.JobStatus.DETECTED,
        priority=0,
        not_before="2026-09-01T00:00:00Z",
        max_attempts=3,
        created_from_event_id=event.event_id,
        created_at="2026-09-01T00:00:00Z",
        updated_at="2026-09-01T00:00:00Z",
        last_error_code=None,
        last_error_detail=None,
    ))

    with sqlite3.connect(db) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "INSERT INTO approvals (approval_id, job_id, action_hash, "
            "reviewer_principal, reviewer_session_id, role, decision, "
            "decided_at, receipt_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "historic-approval-1",
                "historic-job-1",
                "a" * 64,
                "historic-reviewer",
                "historic-session",
                "primary",
                "approved",
                "2026-09-01T00:00:00Z",
                "b" * 64,
            ),
        )

    AutomationStore(db)

    with sqlite3.connect(db) as connection:
        row = connection.execute(
            "SELECT approval_id, reviewer_principal FROM approvals"
        ).fetchone()

    assert row == ("historic-approval-1", "historic-reviewer")
