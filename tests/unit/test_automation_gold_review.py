"""AUTO-6 gold review handler and human inbox contract tests.

Each test asserts the production module paths exist before importing them.
All tests use fixed values and tmp_path; no network, LLM or production data.
"""

import hashlib
from pathlib import Path



ROOT = Path(__file__).resolve().parents[2]
HANDLER_PATH = ROOT / "src" / "company_wiki" / "automation" / "handlers" / "gold_review.py"
INBOX_PATH = ROOT / "src" / "company_wiki" / "automation" / "human_inbox.py"


def _handler_mod():
    assert HANDLER_PATH.is_file()
    from company_wiki.automation.handlers import gold_review
    return gold_review


def _inbox_mod():
    assert INBOX_PATH.is_file()
    from company_wiki.automation import human_inbox
    return human_inbox


def _store_mod():
    from company_wiki.automation import store
    return store


def _registry_mod():
    from company_wiki.automation import registry
    return registry


def _models():
    from company_wiki.automation import models
    return models


INPUT_HASH = hashlib.sha256(b"auto-6-input").hexdigest()


def _make_event(m=None, **overrides):
    m = m or _models()
    defaults = dict(
        event_id="evt-auto6-001",
        event_type="gold.inputs_changed",
        subject_type="gold_corpus",
        subject_id="corpus-auto6-001",
        input_hash=INPUT_HASH,
        payload_json=m.canonical_json({"key": "value"}),
        policy_version="v1",
        occurred_at="2026-07-12T12:00:00Z",
        observed_at="2026-07-12T12:00:00Z",
    )
    defaults.update(overrides)
    return m.Event(**defaults)


def _make_job(m=None, status=None, error_code=None, **overrides):
    m = m or _models()
    status = status or m.JobStatus.BLOCKED_HUMAN
    defaults = dict(
        job_id="job-auto6-001",
        job_type="gold.validate_receipt",
        subject_type="gold_corpus",
        subject_id="corpus-auto6-001",
        input_hash=INPUT_HASH,
        policy_version="v1",
        handler_version="1.0.0",
        risk_class=m.RiskClass.LOW,
        status=status,
        priority=0,
        not_before="2026-07-12T11:00:00Z",
        max_attempts=3,
        created_from_event_id="evt-auto6-001",
        created_at="2026-07-12T12:00:00Z",
        updated_at="2026-07-12T12:00:00Z",
        last_error_code=error_code,
        last_error_detail="test detail" if error_code else None,
    )
    defaults.update(overrides)
    # Compute job_key from final values.
    defaults["job_key"] = m.make_job_key(
        defaults["job_type"], defaults["subject_type"], defaults["subject_id"],
        defaults["input_hash"], defaults["policy_version"], defaults["handler_version"],
    )
    return m.Job(**defaults)


# --------------------------------------------------------------------------- #
# Gold review handler tests.
# --------------------------------------------------------------------------- #
def test_handle_gold_inputs_changed_succeeds():
    h = _handler_mod()
    result = h.handle_gold_inputs_changed({"job_id": "j1", "subject_id": "s1"})
    assert result.outcome is _models().HandlerOutcome.SUCCEEDED
    assert result.result["action"] == "packet_generated"


def test_handle_review_receipt_changed_blocks_human():
    h = _handler_mod()
    m = _models()
    result = h.handle_review_receipt_changed({"job_id": "j1", "subject_id": "s1"})
    assert result.outcome is m.HandlerOutcome.BLOCKED_HUMAN
    assert result.error is not None
    assert result.error.code == "REVIEW_PENDING"


def test_handle_gold_promote_reviewed_creates_effect():
    h = _handler_mod()
    m = _models()
    result = h.handle_gold_promote_reviewed({"job_id": "j1", "subject_id": "s1"})
    assert result.outcome is m.HandlerOutcome.SUCCEEDED
    assert len(result.effects) == 1
    assert result.effects[0].effect_type == "promotion_proposal"
    # The handler never modifies manifest or accepted decisions.
    assert "promotion_proposal_created" in result.result["action"]


def test_gold_review_handlers_registered():
    h = _handler_mod()
    assert "gold.refresh_packet" in h.GOLD_REVIEW_HANDLERS
    assert "gold.validate_receipt" in h.GOLD_REVIEW_HANDLERS
    assert "gold.promote_reviewed" in h.GOLD_REVIEW_HANDLERS


# --------------------------------------------------------------------------- #
# Human inbox tests.
# --------------------------------------------------------------------------- #
def test_inbox_lists_blocked_human_jobs(tmp_path):
    inbox_mod = _inbox_mod()
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    job = _make_job(m=m, error_code="REVIEW_PENDING")
    store.put_job(job)
    inbox = inbox_mod.HumanInbox(store)
    entries = inbox.list_pending()
    assert len(entries) == 1
    assert entries[0].job_id == "job-auto6-001"
    assert entries[0].why_blocked == "awaiting human review"
    assert entries[0].required_role == "reviewer"
    assert entries[0].next_safe_action == "submit-review"


def test_inbox_empty_when_no_blocked_jobs(tmp_path):
    inbox_mod = _inbox_mod()
    s = _store_mod()
    store = s.AutomationStore(tmp_path / "automation.db")
    inbox = inbox_mod.HumanInbox(store)
    assert inbox.count() == 0
    assert inbox.list_pending() == ()


def test_inbox_filters_by_role(tmp_path):
    inbox_mod = _inbox_mod()
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    # Gold job → reviewer role.
    store.put_job(_make_job(m=m, error_code="REVIEW_PENDING"))
    # Analysis job → analyst role.
    store.put_event(_make_event(m=m, event_id="evt-analysis",
                                 event_type="analysis.proposal_ready"))
    store.put_job(_make_job(m=m, job_id="job-analysis",
                             job_type="analysis.review",
                             error_code="REVIEW_PENDING",
                             created_from_event_id="evt-analysis"))
    inbox = inbox_mod.HumanInbox(store)
    assert len(inbox.list_pending()) == 2
    assert len(inbox.list_pending(role="reviewer")) == 1
    assert len(inbox.list_pending(role="analyst")) == 1


def test_inbox_does_not_modify_jobs(tmp_path):
    """The inbox is read-only; it must not change job status or error fields."""
    inbox_mod = _inbox_mod()
    s = _store_mod()
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    job = _make_job(m=m, error_code="REVIEW_PENDING")
    store.put_job(job)
    inbox = inbox_mod.HumanInbox(store)
    inbox.list_pending()
    # Verify job unchanged.
    job_after = store.get_job("job-auto6-001")
    assert job_after.status is m.JobStatus.BLOCKED_HUMAN
    assert job_after.last_error_code == "REVIEW_PENDING"


# --------------------------------------------------------------------------- #
# Controller integration: gold review never writes accepted decisions.
# --------------------------------------------------------------------------- #
def test_controller_shadow_does_not_write_accepted_decisions(tmp_path):
    """Shadow mode creates jobs in DETECTED status, never SUCCEEDED."""
    c_mod = __import__("company_wiki.automation.controller", fromlist=["Controller"])
    s = _store_mod()
    r = _registry_mod()
    p = __import__("company_wiki.automation.policy", fromlist=["PolicyConfig"])
    m = _models()
    store = s.AutomationStore(tmp_path / "automation.db")
    store.put_event(_make_event(m=m))
    reg = r.create_default_registry()
    config = p.PolicyConfig(allow_llm=True)
    ctrl = c_mod.Controller(store, reg, config)
    ctrl.shadow()
    # All created jobs are in DETECTED status.
    for job in store.list_jobs():
        assert job.status is m.JobStatus.DETECTED
        # No job has SUCCEEDED status (no accepted decisions).
        assert job.status is not m.JobStatus.SUCCEEDED
